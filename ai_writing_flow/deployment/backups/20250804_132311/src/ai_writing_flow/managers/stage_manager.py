"""StageManager - Manages flow stage execution and completion tracking.

This module provides centralized stage management for CrewAI Flow,
including completion tracking, result storage, and reset functionality.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import threading
import json

from ..models.flow_stage import FlowStage, get_linear_flow, is_valid_transition
from ..models.flow_control_state import FlowControlState
from ..models.stage_execution import StageExecution
from ..utils.loop_prevention import LoopPreventionSystem


logger = logging.getLogger(__name__)


class ExecutionEventType(str, Enum):
    """Types of execution events in the history log."""
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    STAGE_FAILED = "stage_failed"
    STAGE_SKIPPED = "stage_skipped"
    STAGE_RETRIED = "stage_retried"
    STAGE_TIMEOUT = "stage_timeout"
    FLOW_STARTED = "flow_started"
    FLOW_COMPLETED = "flow_completed" 
    FLOW_FAILED = "flow_failed"
    TRANSITION_ATTEMPTED = "transition_attempted"
    TRANSITION_BLOCKED = "transition_blocked"


@dataclass
class ExecutionEvent:
    """Individual event in the execution history log."""
    
    event_type: ExecutionEventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stage: Optional[FlowStage] = None
    execution_id: Optional[str] = None
    duration_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_details: Optional[str] = None
    previous_stage: Optional[FlowStage] = None
    next_stage: Optional[FlowStage] = None
    retry_attempt: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'stage': self.stage.value if self.stage else None,
            'execution_id': self.execution_id,
            'duration_seconds': self.duration_seconds,
            'metadata': self.metadata,
            'error_details': self.error_details,
            'previous_stage': self.previous_stage.value if self.previous_stage else None,
            'next_stage': self.next_stage.value if self.next_stage else None,
            'retry_attempt': self.retry_attempt
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionEvent':
        """Create event from dictionary."""
        return cls(
            event_type=ExecutionEventType(data['event_type']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            stage=FlowStage(data['stage']) if data.get('stage') else None,
            execution_id=data.get('execution_id'),
            duration_seconds=data.get('duration_seconds'),
            metadata=data.get('metadata', {}),
            error_details=data.get('error_details'),
            previous_stage=FlowStage(data['previous_stage']) if data.get('previous_stage') else None,
            next_stage=FlowStage(data['next_stage']) if data.get('next_stage') else None,
            retry_attempt=data.get('retry_attempt', 0)
        )


@dataclass
class StageConfig:
    """Configuration for a specific stage."""
    
    stage: FlowStage
    required: bool = True
    timeout_seconds: int = 300  # 5 minutes default
    max_retries: int = 3
    skip_conditions: Optional[List[Callable[[FlowControlState], bool]]] = None
    
    def should_skip(self, state: FlowControlState) -> bool:
        """Check if stage should be skipped based on conditions.
        
        Args:
            state: Current flow state
            
        Returns:
            True if stage should be skipped
        """
        if not self.skip_conditions:
            return False
        
        return any(condition(state) for condition in self.skip_conditions)


class StageManager:
    """Manages flow stage execution and completion tracking.
    
    The StageManager provides centralized control over stage execution,
    including completion tracking, result storage, and reset functionality.
    It works with FlowControlState to maintain consistent flow state.
    """
    
    def __init__(self, flow_state: FlowControlState):
        """Initialize StageManager with flow state.
        
        Args:
            flow_state: FlowControlState instance to manage
        """
        self.flow_state = flow_state
        self.stage_configs: Dict[FlowStage, StageConfig] = {}
        self._current_execution: Optional[StageExecution] = None
        self._stage_executions: List[StageExecution] = []
        self._lock = threading.RLock()  # Add thread safety
        
        # Advanced execution history tracking
        self._execution_events: List[ExecutionEvent] = []
        self._flow_start_time: Optional[datetime] = None
        
        # Task 8.2: Method execution tracking with loop prevention
        self.loop_prevention = LoopPreventionSystem(
            max_executions_per_method=100,  # Higher limit for stage manager
            max_executions_per_stage=flow_state.MAX_STAGE_EXECUTIONS,
            max_total_execution_time_minutes=60  # 1 hour max for entire flow
        )
        
        # Initialize default stage configurations
        self._initialize_default_configs()
        
        # Log flow initialization
        self._log_event(
            ExecutionEventType.FLOW_STARTED,
            metadata={'flow_id': flow_state.execution_id}
        )
    
    def _initialize_default_configs(self) -> None:
        """Initialize default configurations for all stages."""
        linear_flow = get_linear_flow()
        
        for stage in linear_flow:
            # Default configuration for all stages
            config = StageConfig(
                stage=stage,
                required=True,
                timeout_seconds=300,
                max_retries=3
            )
            
            # Stage-specific configurations
            if stage == FlowStage.RESEARCH:
                config.skip_conditions = [self._has_existing_research]
            # Skip human review condition removed - stage doesn't exist in our enum
            
            self.stage_configs[stage] = config
    
    def _has_existing_research(self, state: FlowControlState) -> bool:
        """Check if research already exists and is valid.
        
        Args:
            state: Flow state to check
            
        Returns:
            True if research can be skipped
        """
        research_result = state.stage_results.get('research')
        return research_result is not None and len(str(research_result)) > 100
    
    def _log_event(
        self,
        event_type: ExecutionEventType,
        stage: Optional[FlowStage] = None,
        execution_id: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error_details: Optional[str] = None,
        previous_stage: Optional[FlowStage] = None,
        next_stage: Optional[FlowStage] = None,
        retry_attempt: int = 0
    ) -> ExecutionEvent:
        """
        Log an execution event to the history.
        
        Args:
            event_type: Type of event
            stage: Stage involved in the event
            execution_id: ID of the execution
            duration_seconds: Duration if applicable
            metadata: Additional metadata
            error_details: Error information if applicable
            previous_stage: Previous stage for transitions
            next_stage: Next stage for transitions
            retry_attempt: Retry attempt number
            
        Returns:
            Created ExecutionEvent
        """
        with self._lock:
            event = ExecutionEvent(
                event_type=event_type,
                stage=stage,
                execution_id=execution_id or self.flow_state.execution_id,
                duration_seconds=duration_seconds,
                metadata=metadata or {},
                error_details=error_details,
                previous_stage=previous_stage,
                next_stage=next_stage,
                retry_attempt=retry_attempt
            )
            
            self._execution_events.append(event)
            
            # Log to standard logger as well
            log_level = logging.ERROR if event_type in [
                ExecutionEventType.STAGE_FAILED, 
                ExecutionEventType.FLOW_FAILED,
                ExecutionEventType.TRANSITION_BLOCKED
            ] else logging.INFO
            
            logger.log(
                log_level,
                f"Execution event: {event_type.value} - Stage: {stage.value if stage else 'N/A'} - "
                f"Metadata: {metadata}"
            )
            
            return event
    
    
    def configure_stage(self, stage: FlowStage, config: StageConfig) -> None:
        """Configure a specific stage.
        
        Args:
            stage: Stage to configure
            config: Configuration for the stage
        """
        self.stage_configs[stage] = config
        logger.info(f"Configured stage {stage} with timeout {config.timeout_seconds}s")
    
    def is_stage_completed(self, stage: FlowStage) -> bool:
        """Check if a stage has been completed successfully.
        
        Args:
            stage: Stage to check
            
        Returns:
            True if stage is completed
        """
        return stage in self.flow_state.completed_stages
    
    def should_skip_stage(self, stage: FlowStage) -> bool:
        """Check if a stage should be skipped.
        
        Args:
            stage: Stage to check
            
        Returns:
            True if stage should be skipped
        """
        if stage not in self.stage_configs:
            return False
        
        config = self.stage_configs[stage]
        
        # Skip if already completed and not required to re-run
        if self.is_stage_completed(stage):
            return True
        
        # Skip if stage-specific conditions are met
        return config.should_skip(self.flow_state)
    
    def start_stage(self, stage: FlowStage) -> StageExecution:
        """Start execution of a stage.
        
        Args:
            stage: Stage to start
            
        Returns:
            StageExecution instance for tracking
            
        Raises:
            ValueError: If stage cannot be started
        """
        # Task 8.2: Track method execution for loop prevention
        loop_record = self.loop_prevention.track_execution(
            method_name="StageManager.start_stage",
            stage=stage,
            arguments={'stage': stage.value}
        )
        
        try:
            if self.should_skip_stage(stage):
                logger.info(f"Skipping stage {stage} - conditions met")
                # Create a fake execution that's already completed
                execution = StageExecution(
                    stage=stage,
                    execution_id=self.flow_state.execution_id,
                    retry_attempt=0
                )
                execution.complete(success=True, result={'skipped': True})
                
                # Log skip event
                self._log_event(
                    ExecutionEventType.STAGE_SKIPPED,
                    stage=stage,
                    metadata={'reason': 'stage_conditions_met'}
                )
                
                return execution
            
            # Check if stage is valid for current flow position
            if not is_valid_transition(self.flow_state.current_stage, stage):
                # Allow starting the current stage
                if stage != self.flow_state.current_stage:
                    # Log blocked transition
                    self._log_event(
                        ExecutionEventType.TRANSITION_BLOCKED,
                        stage=stage,
                        previous_stage=self.flow_state.current_stage,
                        next_stage=stage,
                        error_details=f"Invalid transition from {self.flow_state.current_stage.value}"
                    )
                    raise ValueError(f"Cannot start stage {stage} from current stage {self.flow_state.current_stage}")
            
            # Start stage execution tracking
            with self._lock:  # Thread safety
                self._current_execution = self.flow_state.start_stage_execution(stage)
                self._stage_executions.append(self._current_execution)
            
            # Log execution event
            self._log_event(
                ExecutionEventType.STAGE_STARTED,
                stage=stage,
                execution_id=self._current_execution.execution_id,
                metadata={
                    'stage_config': {
                        'timeout_seconds': self.stage_configs.get(stage, StageConfig(stage)).timeout_seconds,
                        'max_retries': self.stage_configs.get(stage, StageConfig(stage)).max_retries
                    },
                    'retry_attempt': self._current_execution.retry_attempt
                }
            )
            
            logger.info(f"Started stage {stage} execution")
            return self._current_execution
            
        finally:
            # Complete loop prevention tracking
            self.loop_prevention.complete_execution(loop_record)
    
    def complete_stage(self, stage: FlowStage, success: bool = True, 
                      result: Optional[Dict[str, Any]] = None, 
                      error: Optional[str] = None) -> None:
        """Mark a stage as completed.
        
        Args:
            stage: Stage to complete
            success: Whether stage completed successfully
            result: Stage execution result
            error: Error message if failed
        """
        # Task 8.2: Track method execution for loop prevention
        loop_record = self.loop_prevention.track_execution(
            method_name="StageManager.complete_stage",
            stage=stage,
            arguments={'stage': stage.value, 'success': success}
        )
        
        try:
            execution = None
            duration_seconds = None
            
            with self._lock:  # Thread safety
                # Find the execution in our tracking
                for exec_item in reversed(self._stage_executions):
                    if exec_item.stage == stage and exec_item.end_time is None:
                        execution = exec_item
                        break
                
                if execution:
                    execution.complete(success=success, result=result, error=error)
                    duration_seconds = execution.duration_seconds
                    # Also update flow state with the result
                    stage_result = execution.to_stage_result()
                    self.flow_state.mark_stage_complete(stage, stage_result)
            
            # Log completion event
            event_type = ExecutionEventType.STAGE_COMPLETED if success else ExecutionEventType.STAGE_FAILED
            self._log_event(
                event_type,
                stage=stage,
                execution_id=execution.execution_id if execution else None,
                duration_seconds=duration_seconds,
                metadata={
                    'result_size': len(str(result)) if result else 0,
                    'retry_attempt': execution.retry_attempt if execution else 0
                },
                error_details=error
            )
            
            if success:
                logger.info(f"Completed stage {stage} successfully")
            else:
                logger.error(f"Stage {stage} failed: {error}")
                
        finally:
            # Complete loop prevention tracking
            self.loop_prevention.complete_execution(loop_record)
    
    def get_stage_result(self, stage: FlowStage) -> Optional[Dict[str, Any]]:
        """Get the result of a completed stage.
        
        Args:
            stage: Stage to get result for
            
        Returns:
            Stage result or None if not completed
        """
        return self.flow_state.stage_results.get(stage.value)
    
    def reset_stage(self, stage: FlowStage) -> None:
        """Reset a stage for re-execution.
        
        Args:
            stage: Stage to reset
        """
        self.flow_state.reset_stage(stage)
        logger.info(f"Reset stage {stage} for re-execution")
    
    def get_execution_history(self, stage: Optional[FlowStage] = None) -> List[StageExecution]:
        """Get execution history for stages.
        
        Args:
            stage: Specific stage to filter by, or None for all
            
        Returns:
            List of StageExecution objects
        """
        if stage is None:
            return self._stage_executions
        
        return [exec_item for exec_item in self._stage_executions 
                if exec_item.stage == stage]
    
    def get_stage_metrics(self, stage: FlowStage) -> Dict[str, Any]:
        """Get metrics for a specific stage.
        
        Args:
            stage: Stage to get metrics for
            
        Returns:
            Dictionary of stage metrics
        """
        executions = self.get_execution_history(stage)
        
        if not executions:
            return {'executions': 0}
        
        successful = [e for e in executions if e.success]
        failed = [e for e in executions if not e.success]
        
        total_duration = sum(
            e.duration_seconds or 0 for e in executions if e.duration_seconds
        )
        
        return {
            'executions': len(executions),
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': len(successful) / len(executions) if executions else 0,
            'total_duration_seconds': total_duration,
            'average_duration_seconds': total_duration / len(executions) if executions else 0,
            'completed': self.is_stage_completed(stage)
        }
    
    def get_overall_metrics(self) -> Dict[str, Any]:
        """Get overall flow execution metrics.
        
        Returns:
            Dictionary of overall metrics
        """
        all_executions = self._stage_executions
        completed_stages = len(self.flow_state.completed_stages)
        total_stages = len(get_linear_flow())
        
        return {
            'total_executions': len(all_executions),
            'completed_stages': completed_stages,
            'total_stages': total_stages,
            'completion_percentage': (completed_stages / total_stages) * 100 if total_stages else 0,
            'total_retries': self.flow_state.total_retry_count,
            'execution_duration_seconds': self.flow_state.get_execution_duration(),
            'current_stage': self.flow_state.current_stage.value,
            'is_completed': self.flow_state.is_completed()
        }
    
    def cleanup_history(self, keep_last_n: int = 100) -> None:
        """Clean up execution history to prevent memory bloat.
        
        Args:
            keep_last_n: Number of recent executions to keep
        """
        # Task 7.3: Enhanced history cleanup with memory management
        with self._lock:
            initial_exec_count = len(self._stage_executions)
            initial_event_count = len(self._execution_events)
            
            # Clean up stage executions
            if len(self._stage_executions) > keep_last_n:
                self._stage_executions = self._stage_executions[-keep_last_n:]
            
            # Clean up execution events (keep more events for analysis)
            max_events = keep_last_n * 3  # Keep 3x more events than executions
            if len(self._execution_events) > max_events:
                # Keep recent events and important milestone events
                recent_events = self._execution_events[-max_events//2:]
                
                # Keep important milestone events from older history
                older_events = self._execution_events[:-max_events//2]
                milestone_events = [
                    e for e in older_events
                    if e.event_type in [
                        ExecutionEventType.FLOW_STARTED,
                        ExecutionEventType.FLOW_COMPLETED,
                        ExecutionEventType.FLOW_FAILED,
                        ExecutionEventType.STAGE_FAILED  # Keep failure events for debugging
                    ]
                ]
                
                # Combine and sort
                self._execution_events = milestone_events + recent_events
                self._execution_events.sort(key=lambda e: e.timestamp)
            
            logger.info(
                f"Cleaned up execution history: "
                f"stage_executions {initial_exec_count} → {len(self._stage_executions)}, "
                f"events {initial_event_count} → {len(self._execution_events)}"
            )
    
    def cleanup_old_events(self, max_age_hours: int = 24) -> int:
        """
        Clean up events older than specified age.
        
        Args:
            max_age_hours: Maximum age of events to keep
            
        Returns:
            Number of events removed
        """
        from datetime import timedelta
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        with self._lock:
            initial_count = len(self._execution_events)
            
            # Keep recent events and important milestones regardless of age
            self._execution_events = [
                e for e in self._execution_events
                if (e.timestamp >= cutoff_time or 
                    e.event_type in [
                        ExecutionEventType.FLOW_STARTED,
                        ExecutionEventType.FLOW_COMPLETED,
                        ExecutionEventType.FLOW_FAILED
                    ])
            ]
            
            removed_count = initial_count - len(self._execution_events)
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old events (older than {max_age_hours}h)")
            
            return removed_count
    
    def export_execution_history(self, filename: Optional[str] = None) -> str:
        """
        Export execution history to JSON file.
        
        Args:
            filename: Optional filename, auto-generated if not provided
            
        Returns:
            Path to exported file
        """
        import os
        
        with self._lock:
            history_data = {
                'flow_id': self.flow_state.execution_id,
                'export_timestamp': datetime.now(timezone.utc).isoformat(),
                'total_events': len(self._execution_events),
                'events': [e.to_dict() for e in self._execution_events],
                'flow_state_summary': {
                    'current_stage': self.flow_state.current_stage.value,
                    'completed_stages': [s.value for s in self.flow_state.completed_stages],
                    'total_retries': self.flow_state.total_retry_count,
                    'execution_duration': self.flow_state.get_execution_duration()
                }
            }
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"execution_history_{self.flow_state.execution_id}_{timestamp}.json"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(history_data, f, indent=2, default=str)
        
        logger.info(f"Exported execution history to {filename}")
        return filename
    
    def get_memory_usage_report(self) -> Dict[str, Any]:
        """
        Get memory usage report for history tracking.
        
        Returns:
            Dictionary with memory usage metrics
        """
        import sys
        
        with self._lock:
            stage_exec_size = sys.getsizeof(self._stage_executions)
            events_size = sys.getsizeof(self._execution_events)
            
            # Estimate size of individual objects
            avg_exec_size = (
                sum(sys.getsizeof(e) for e in self._stage_executions) / len(self._stage_executions)
                if self._stage_executions else 0
            )
            
            avg_event_size = (
                sum(sys.getsizeof(e) for e in self._execution_events) / len(self._execution_events)
                if self._execution_events else 0
            )
            
            total_size = stage_exec_size + events_size
            
            return {
                'total_memory_bytes': total_size,
                'total_memory_mb': total_size / (1024 * 1024),
                'stage_executions': {
                    'count': len(self._stage_executions),
                    'memory_bytes': stage_exec_size,
                    'avg_size_bytes': avg_exec_size
                },
                'execution_events': {
                    'count': len(self._execution_events),
                    'memory_bytes': events_size,
                    'avg_size_bytes': avg_event_size
                },
                'recommendations': self._get_memory_recommendations(total_size)
            }
    
    def _get_memory_recommendations(self, total_bytes: int) -> List[str]:
        """Get memory usage recommendations."""
        recommendations = []
        
        mb_size = total_bytes / (1024 * 1024)
        
        if mb_size > 50:
            recommendations.append("Consider running cleanup_history() - memory usage > 50MB")
        
        if len(self._execution_events) > 10000:
            recommendations.append("Large number of events - consider cleanup_old_events()")
        
        if len(self._stage_executions) > 1000:
            recommendations.append("Many stage executions - consider reducing keep_last_n in cleanup")
        
        return recommendations
    
    # Task 8.3: Timeout guards implementation
    def check_flow_timeout(self) -> bool:
        """
        Check if the flow has exceeded its total timeout.
        
        Returns:
            True if flow has timed out
        """
        if not self._flow_start_time:
            self._flow_start_time = self.flow_state.start_time
        
        execution_time = datetime.now(timezone.utc) - self._flow_start_time
        max_flow_time = timedelta(hours=2)  # 2 hour absolute max
        
        if execution_time > max_flow_time:
            logger.error(f"Flow timeout exceeded: {execution_time} > {max_flow_time}")
            self._log_event(
                ExecutionEventType.FLOW_FAILED,
                metadata={
                    'timeout_reason': 'total_flow_timeout',
                    'execution_time_seconds': execution_time.total_seconds(),
                    'max_time_seconds': max_flow_time.total_seconds()
                },
                error_details=f"Flow exceeded maximum execution time of {max_flow_time}"
            )
            return True
        
        return False
    
    def check_stage_timeout(self, stage: FlowStage, start_time: datetime) -> bool:
        """
        Check if a stage has exceeded its timeout.
        
        Args:
            stage: Stage to check
            start_time: When the stage started
            
        Returns:
            True if stage has timed out
        """
        stage_timeout = self.get_stage_timeout(stage)
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        if execution_time > stage_timeout:
            logger.error(f"Stage {stage.value} timeout: {execution_time}s > {stage_timeout}s")
            self._log_event(
                ExecutionEventType.STAGE_TIMEOUT,
                stage=stage,
                duration_seconds=execution_time,
                metadata={
                    'timeout_seconds': stage_timeout,
                    'exceeded_by_seconds': execution_time - stage_timeout
                },
                error_details=f"Stage {stage.value} exceeded timeout of {stage_timeout}s"
            )
            return True
        
        return False
    
    def get_stage_timeout(self, stage: FlowStage) -> int:
        """Get timeout for a stage in seconds."""
        config = self.stage_configs.get(stage)
        if config:
            return config.timeout_seconds
        
        # Default timeouts per stage
        default_timeouts = {
            FlowStage.INPUT_VALIDATION: 30,
            FlowStage.RESEARCH: 300,  # 5 minutes for research
            FlowStage.AUDIENCE_ALIGN: 60,
            FlowStage.DRAFT_GENERATION: 600,  # 10 minutes for generation
            FlowStage.STYLE_VALIDATION: 120,
            FlowStage.QUALITY_CHECK: 180,
            FlowStage.FINALIZED: 30,
            FlowStage.FAILED: 30
        }
        
        return default_timeouts.get(stage, 300)  # Default 5 minutes
    
    def start_stage_with_timeout(self, stage: FlowStage) -> StageExecution:
        """
        Start a stage with timeout monitoring.
        
        Args:
            stage: Stage to start
            
        Returns:
            StageExecution instance
            
        Raises:
            RuntimeError: If flow or stage timeout exceeded
        """
        # Check flow timeout first
        if self.check_flow_timeout():
            raise RuntimeError("Flow execution timeout exceeded")
        
        # Start the stage normally
        execution = self.start_stage(stage)
        
        # Schedule timeout check (this would normally be done with a timer or background task)
        # For now, we'll just record the start time for manual checking
        execution._timeout_start = datetime.now(timezone.utc)
        
        return execution
    
    def complete_stage_with_timeout_check(
        self, 
        stage: FlowStage, 
        success: bool = True,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Complete a stage with timeout checking.
        
        Args:
            stage: Stage to complete
            success: Whether completed successfully
            result: Stage result
            error: Error message if failed
        """
        # Find the execution to check timeout
        execution = None
        with self._lock:
            for exec_item in reversed(self._stage_executions):
                if exec_item.stage == stage and exec_item.end_time is None:
                    execution = exec_item
                    break
        
        # Check if stage timed out
        if execution and hasattr(execution, '_timeout_start'):
            if self.check_stage_timeout(stage, execution._timeout_start):
                # Override success to False if timed out
                success = False
                error = f"Stage {stage.value} timed out after {self.get_stage_timeout(stage)}s"
        
        # Complete the stage normally
        self.complete_stage(stage, success=success, result=result, error=error)
    
    def get_timeout_status(self) -> Dict[str, Any]:
        """
        Get current timeout status for flow and active stages.
        
        Returns:
            Dictionary with timeout information
        """
        status = {
            'flow_timeout_status': 'OK',
            'flow_execution_time_seconds': 0.0,
            'flow_max_time_seconds': 7200,  # 2 hours
            'active_stages': [],
            'warnings': []
        }
        
        # Check flow timeout
        if self._flow_start_time:
            execution_time = (datetime.now(timezone.utc) - self._flow_start_time).total_seconds()
            status['flow_execution_time_seconds'] = execution_time
            
            if execution_time > 6000:  # 100 minutes warning
                status['flow_timeout_status'] = 'WARNING'
                status['warnings'].append('Flow approaching timeout limit')
            elif execution_time > 7200:  # 2 hours critical
                status['flow_timeout_status'] = 'CRITICAL'
                status['warnings'].append('Flow exceeded maximum execution time')
        
        # Check active stage timeouts
        with self._lock:
            for execution in self._stage_executions:
                if execution.end_time is None and hasattr(execution, '_timeout_start'):
                    stage_time = (
                        datetime.now(timezone.utc) - execution._timeout_start
                    ).total_seconds()
                    stage_timeout = self.get_stage_timeout(execution.stage)
                    
                    stage_status = {
                        'stage': execution.stage.value,
                        'execution_time_seconds': stage_time,
                        'timeout_seconds': stage_timeout,
                        'timeout_status': 'OK',
                        'time_remaining_seconds': max(0, stage_timeout - stage_time)
                    }
                    
                    if stage_time > stage_timeout * 0.8:  # 80% warning
                        stage_status['timeout_status'] = 'WARNING'
                    elif stage_time > stage_timeout:  # Exceeded
                        stage_status['timeout_status'] = 'EXCEEDED'
                        status['warnings'].append(f"Stage {execution.stage.value} exceeded timeout")
                    
                    status['active_stages'].append(stage_status)
        
        return status
    
    def force_timeout_stage(self, stage: FlowStage, reason: str = "Manual timeout") -> None:
        """
        Force timeout a stage.
        
        Args:
            stage: Stage to timeout
            reason: Reason for forcing timeout
        """
        logger.warning(f"Forcing timeout for stage {stage.value}: {reason}")
        
        # Find and complete the execution with timeout
        with self._lock:
            for execution in self._stage_executions:
                if execution.stage == stage and execution.end_time is None:
                    execution.complete(
                        success=False, 
                        error=f"Forced timeout: {reason}"
                    )
                    break
        
        # Log timeout event
        self._log_event(
            ExecutionEventType.STAGE_TIMEOUT,
            stage=stage,
            metadata={'forced': True, 'reason': reason},
            error_details=f"Manually forced timeout: {reason}"
        )
        
        # Complete stage with timeout
        self.complete_stage(
            stage, 
            success=False, 
            error=f"Forced timeout: {reason}"
        )
    
    # Task 7.2: History analysis methods
    def get_execution_events(
        self, 
        event_type: Optional[ExecutionEventType] = None,
        stage: Optional[FlowStage] = None,
        limit: Optional[int] = None
    ) -> List[ExecutionEvent]:
        """
        Get execution events from history.
        
        Args:
            event_type: Filter by event type
            stage: Filter by stage
            limit: Limit number of results
            
        Returns:
            List of ExecutionEvent objects
        """
        with self._lock:
            events = self._execution_events.copy()
        
        # Apply filters
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if stage:
            events = [e for e in events if e.stage == stage]
        
        # Sort by timestamp (newest first)
        events.sort(key=lambda e: e.timestamp, reverse=True)
        
        # Apply limit
        if limit:
            events = events[:limit]
        
        return events
    
    def get_execution_timeline(self) -> List[Dict[str, Any]]:
        """
        Get chronological timeline of all execution events.
        
        Returns:
            List of event dictionaries sorted by timestamp
        """
        with self._lock:
            events = [e.to_dict() for e in self._execution_events]
        
        # Sort by timestamp
        events.sort(key=lambda e: e['timestamp'])
        
        return events
    
    def analyze_stage_performance(self, stage: FlowStage) -> Dict[str, Any]:
        """
        Analyze performance metrics for a specific stage.
        
        Args:
            stage: Stage to analyze
            
        Returns:
            Dictionary with performance analysis
        """
        stage_events = self.get_execution_events(stage=stage)
        
        # Filter to completion events
        completed_events = [
            e for e in stage_events 
            if e.event_type in [ExecutionEventType.STAGE_COMPLETED, ExecutionEventType.STAGE_FAILED]
            and e.duration_seconds is not None
        ]
        
        if not completed_events:
            return {
                'stage': stage.value,
                'total_executions': 0,
                'success_rate': 0.0,
                'average_duration_seconds': 0.0,
                'min_duration_seconds': 0.0,
                'max_duration_seconds': 0.0,
                'total_failures': 0
            }
        
        successful = [e for e in completed_events if e.event_type == ExecutionEventType.STAGE_COMPLETED]
        failed = [e for e in completed_events if e.event_type == ExecutionEventType.STAGE_FAILED]
        
        durations = [e.duration_seconds for e in completed_events if e.duration_seconds]
        
        return {
            'stage': stage.value,
            'total_executions': len(completed_events),
            'successful_executions': len(successful),
            'failed_executions': len(failed),
            'success_rate': len(successful) / len(completed_events) if completed_events else 0.0,
            'average_duration_seconds': sum(durations) / len(durations) if durations else 0.0,
            'min_duration_seconds': min(durations) if durations else 0.0,
            'max_duration_seconds': max(durations) if durations else 0.0,
            'total_retries': sum(e.retry_attempt for e in completed_events),
            'last_execution': completed_events[0].timestamp.isoformat() if completed_events else None
        }
    
    def detect_execution_loops(self, lookback_minutes: int = 60) -> List[Dict[str, Any]]:
        """
        Detect potential execution loops in recent history.
        
        Args:
            lookback_minutes: How far back to analyze
            
        Returns:
            List of detected loop patterns
        """
        from datetime import timedelta
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
        
        # Get recent events
        recent_events = [
            e for e in self._execution_events 
            if e.timestamp >= cutoff_time and e.stage is not None
        ]
        
        # Look for patterns where stages are executed too frequently
        stage_counts = {}
        for event in recent_events:
            if event.event_type == ExecutionEventType.STAGE_STARTED:
                stage_counts[event.stage] = stage_counts.get(event.stage, 0) + 1
        
        # Detect potential loops (more than expected executions)
        loops = []
        for stage, count in stage_counts.items():
            expected_max = 3  # Normal stage should not execute more than 3 times in an hour
            if count > expected_max:
                # Analyze the pattern
                stage_events = [e for e in recent_events if e.stage == stage]
                time_span = (stage_events[-1].timestamp - stage_events[0].timestamp).total_seconds()
                
                loops.append({
                    'stage': stage.value,
                    'execution_count': count,
                    'time_span_seconds': time_span,
                    'frequency_per_minute': count / (time_span / 60) if time_span > 0 else 0,
                    'first_occurrence': stage_events[0].timestamp.isoformat(),
                    'last_occurrence': stage_events[-1].timestamp.isoformat(),
                    'risk_level': 'HIGH' if count > 10 else 'MEDIUM'
                })
        
        return loops
    
    def get_flow_health_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive flow health report.
        
        Returns:
            Dictionary with health metrics and recommendations
        """
        total_events = len(self._execution_events)
        
        # Count different event types
        event_counts = {}
        for event in self._execution_events:
            event_counts[event.event_type.value] = event_counts.get(event.event_type.value, 0) + 1
        
        # Calculate success rates
        completed = event_counts.get(ExecutionEventType.STAGE_COMPLETED.value, 0)
        failed = event_counts.get(ExecutionEventType.STAGE_FAILED.value, 0)
        total_stage_executions = completed + failed
        
        # Detect issues
        loops = self.detect_execution_loops()
        
        # Flow duration
        flow_duration = None
        if self._flow_start_time:
            flow_duration = (datetime.now(timezone.utc) - self._flow_start_time).total_seconds()
        
        health_status = "HEALTHY"
        warnings = []
        
        if loops:
            health_status = "WARNING"
            warnings.append(f"Detected {len(loops)} potential execution loops")
        
        if total_stage_executions > 0 and (failed / total_stage_executions) > 0.2:
            health_status = "CRITICAL"
            warnings.append(f"High failure rate: {(failed/total_stage_executions)*100:.1f}%")
        
        return {
            'health_status': health_status,
            'warnings': warnings,
            'total_events': total_events,
            'event_breakdown': event_counts,
            'stage_completion_rate': (completed / total_stage_executions) if total_stage_executions > 0 else 0.0,
            'flow_duration_seconds': flow_duration,
            'detected_loops': loops,
            'active_stages': len(set(e.stage for e in self._execution_events if e.stage)),
            'last_activity': self._execution_events[-1].timestamp.isoformat() if self._execution_events else None
        }
