"""
Loop Prevention System - Prevents infinite loops in flow execution

This module implements comprehensive loop prevention mechanisms including
execution counting, method tracking, timeout guards, and pattern detection.
"""

import time
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Callable, Set
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum
import logging

from ..models.flow_stage import FlowStage


logger = logging.getLogger(__name__)


class LoopRiskLevel(str, Enum):
    """Risk levels for loop detection."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ExecutionRecord:
    """Record of method/function execution."""
    
    method_name: str
    stage: Optional[FlowStage]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    execution_time_seconds: Optional[float] = None
    thread_id: int = field(default_factory=threading.get_ident)
    call_stack_depth: int = 0
    arguments_hash: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization to set call stack depth."""
        import inspect
        self.call_stack_depth = len(inspect.stack())


@dataclass 
class LoopPattern:
    """Detected loop pattern."""
    
    pattern_type: str
    method_names: List[str]
    execution_count: int
    time_span_seconds: float
    risk_level: LoopRiskLevel
    first_occurrence: datetime
    last_occurrence: datetime
    stage: Optional[FlowStage] = None
    recommendation: str = ""


class LoopPreventionSystem:
    """
    Comprehensive system for preventing infinite loops in flow execution.
    
    Features:
    - Execution counting per method/stage
    - Pattern detection for cyclic calls
    - Timeout enforcement
    - Memory usage monitoring
    - Emergency circuit breakers
    """
    
    def __init__(
        self,
        max_executions_per_method: int = 50,
        max_executions_per_stage: int = 10,
        max_total_execution_time_minutes: int = 30,
        pattern_detection_window_minutes: int = 5,
        enable_stack_trace_analysis: bool = True
    ):
        """
        Initialize loop prevention system.
        
        Args:
            max_executions_per_method: Maximum executions per method
            max_executions_per_stage: Maximum executions per stage
            max_total_execution_time_minutes: Total execution timeout
            pattern_detection_window_minutes: Window for pattern detection
            enable_stack_trace_analysis: Whether to analyze call stacks
        """
        self.max_executions_per_method = max_executions_per_method
        self.max_executions_per_stage = max_executions_per_stage
        self.max_total_execution_time = timedelta(minutes=max_total_execution_time_minutes)
        self.pattern_detection_window = timedelta(minutes=pattern_detection_window_minutes)
        self.enable_stack_trace_analysis = enable_stack_trace_analysis
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Execution tracking
        self._execution_records: List[ExecutionRecord] = []
        self._method_counts: Dict[str, int] = {}
        self._stage_counts: Dict[FlowStage, int] = {}
        self._start_time = datetime.now(timezone.utc)
        
        # Emergency controls
        self._emergency_stop = False
        self._blocked_methods: Set[str] = set()
        self._blocked_stages: Set[FlowStage] = set()
        
        # Pattern detection
        self._detected_patterns: List[LoopPattern] = []
        self._last_pattern_check = datetime.now(timezone.utc)
    
    def track_execution(
        self,
        method_name: str,
        stage: Optional[FlowStage] = None,
        arguments: Optional[Dict[str, Any]] = None
    ) -> ExecutionRecord:
        """
        Track a method execution.
        
        Args:
            method_name: Name of the method being executed
            stage: Flow stage if applicable
            arguments: Method arguments for pattern detection
            
        Returns:
            ExecutionRecord for this execution
            
        Raises:
            RuntimeError: If execution limits are exceeded
        """
        with self._lock:
            # Check emergency stop
            if self._emergency_stop:
                raise RuntimeError("Emergency stop activated - loop prevention system halted execution")
            
            # Check blocked methods/stages
            if method_name in self._blocked_methods:
                raise RuntimeError(f"Method {method_name} is blocked due to loop detection")
            
            if stage and stage in self._blocked_stages:
                raise RuntimeError(f"Stage {stage.value} is blocked due to loop detection")
            
            # Check execution limits
            method_count = self._method_counts.get(method_name, 0)
            if method_count >= self.max_executions_per_method:
                self._block_method(method_name, "execution limit exceeded")
                raise RuntimeError(
                    f"Method {method_name} exceeded execution limit ({self.max_executions_per_method})"
                )
            
            if stage:
                stage_count = self._stage_counts.get(stage, 0)
                if stage_count >= self.max_executions_per_stage:
                    self._block_stage(stage, "execution limit exceeded")
                    raise RuntimeError(
                        f"Stage {stage.value} exceeded execution limit ({self.max_executions_per_stage})"
                    )
            
            # Check total execution time
            total_time = datetime.now(timezone.utc) - self._start_time
            if total_time > self.max_total_execution_time:
                self._trigger_emergency_stop("total execution time exceeded")
                raise RuntimeError(f"Total execution time exceeded ({self.max_total_execution_time})")
            
            # Create execution record
            arguments_hash = None
            if arguments:
                arguments_hash = str(hash(frozenset(arguments.items())))
            
            record = ExecutionRecord(
                method_name=method_name,
                stage=stage,
                arguments_hash=arguments_hash
            )
            
            # Update counters
            self._method_counts[method_name] = method_count + 1
            if stage:
                self._stage_counts[stage] = self._stage_counts.get(stage, 0) + 1
            
            # Store record
            self._execution_records.append(record)
            
            # Check for patterns periodically
            if (datetime.now(timezone.utc) - self._last_pattern_check > 
                timedelta(seconds=30)):  # Check every 30 seconds
                self._detect_patterns()
                self._last_pattern_check = datetime.now(timezone.utc)
            
            logger.debug(
                f"Tracked execution: {method_name} "
                f"(count: {self._method_counts[method_name]}, stage: {stage})"
            )
            
            return record
    
    def complete_execution(self, record: ExecutionRecord) -> None:
        """
        Mark an execution as complete with timing information.
        
        Args:
            record: ExecutionRecord to complete
        """
        with self._lock:
            execution_time = (datetime.now(timezone.utc) - record.timestamp).total_seconds()
            record.execution_time_seconds = execution_time
            
            logger.debug(
                f"Completed execution: {record.method_name} "
                f"(duration: {execution_time:.2f}s)"
            )
    
    def _block_method(self, method_name: str, reason: str) -> None:
        """Block a method from further execution."""
        self._blocked_methods.add(method_name)
        logger.error(f"BLOCKED METHOD: {method_name} - {reason}")
    
    def _block_stage(self, stage: FlowStage, reason: str) -> None:
        """Block a stage from further execution."""
        self._blocked_stages.add(stage)
        logger.error(f"BLOCKED STAGE: {stage.value} - {reason}")
    
    def _trigger_emergency_stop(self, reason: str) -> None:
        """Trigger emergency stop of all execution."""
        self._emergency_stop = True
        logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
    
    def with_loop_protection(self, stage: Optional[FlowStage] = None):
        """
        Decorator to add loop protection to methods.
        
        Args:
            stage: Flow stage this method belongs to
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                method_name = f"{func.__module__}.{func.__qualname__}"
                
                # Start tracking
                record = self.track_execution(
                    method_name=method_name,
                    stage=stage,
                    arguments=kwargs if len(str(kwargs)) < 1000 else None  # Limit arg size
                )
                
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    # Complete tracking
                    self.complete_execution(record)
            
            return wrapper
        return decorator
    
    def _detect_patterns(self) -> List[LoopPattern]:
        """
        Detect loop patterns in recent execution history.
        
        Returns:
            List of detected patterns
        """
        cutoff_time = datetime.now(timezone.utc) - self.pattern_detection_window
        recent_records = [
            r for r in self._execution_records
            if r.timestamp >= cutoff_time
        ]
        
        patterns = []
        
        # Pattern 1: Same method called repeatedly
        method_patterns = self._detect_method_repetition_patterns(recent_records)
        patterns.extend(method_patterns)
        
        # Pattern 2: Cyclic method calls
        cycle_patterns = self._detect_cyclic_patterns(recent_records)
        patterns.extend(cycle_patterns)
        
        # Pattern 3: Stage oscillation
        stage_patterns = self._detect_stage_oscillation_patterns(recent_records)
        patterns.extend(stage_patterns)
        
        # Update detected patterns
        with self._lock:
            self._detected_patterns.extend(patterns)
            
            # Take action on critical patterns
            for pattern in patterns:
                if pattern.risk_level == LoopRiskLevel.CRITICAL:
                    logger.error(f"CRITICAL LOOP PATTERN DETECTED: {pattern}")
                    # Block the problematic methods/stages
                    for method_name in pattern.method_names:
                        self._blocked_methods.add(method_name)
                    if pattern.stage:
                        self._blocked_stages.add(pattern.stage)
        
        return patterns
    
    def _detect_method_repetition_patterns(
        self, 
        records: List[ExecutionRecord]
    ) -> List[LoopPattern]:
        """Detect methods called too frequently."""
        patterns = []
        method_counts = {}
        
        for record in records:
            method_counts[record.method_name] = method_counts.get(record.method_name, 0) + 1
        
        for method_name, count in method_counts.items():
            if count > 20:  # More than 20 calls in detection window
                method_records = [r for r in records if r.method_name == method_name]
                time_span = (method_records[-1].timestamp - method_records[0].timestamp).total_seconds()
                
                risk_level = LoopRiskLevel.HIGH if count > 50 else LoopRiskLevel.MEDIUM
                
                patterns.append(LoopPattern(
                    pattern_type="method_repetition",
                    method_names=[method_name],
                    execution_count=count,
                    time_span_seconds=time_span,
                    risk_level=risk_level,
                    first_occurrence=method_records[0].timestamp,
                    last_occurrence=method_records[-1].timestamp,
                    recommendation=f"Method {method_name} called {count} times - possible infinite loop"
                ))
        
        return patterns
    
    def _detect_cyclic_patterns(self, records: List[ExecutionRecord]) -> List[LoopPattern]:
        """Detect cyclic method call patterns."""
        patterns = []
        
        # Look for A -> B -> A patterns
        for i in range(len(records) - 2):
            current = records[i]
            next_record = records[i + 1]
            after_next = records[i + 2]
            
            if (current.method_name == after_next.method_name and 
                current.method_name != next_record.method_name):
                
                # Found potential A -> B -> A pattern
                cycle_methods = [current.method_name, next_record.method_name]
                time_span = (after_next.timestamp - current.timestamp).total_seconds()
                
                patterns.append(LoopPattern(
                    pattern_type="cyclic_calls",
                    method_names=cycle_methods,
                    execution_count=3,  # Minimum for A->B->A
                    time_span_seconds=time_span,
                    risk_level=LoopRiskLevel.MEDIUM,
                    first_occurrence=current.timestamp,
                    last_occurrence=after_next.timestamp,
                    recommendation=f"Cyclic pattern detected: {' -> '.join(cycle_methods)}"
                ))
        
        return patterns
    
    def _detect_stage_oscillation_patterns(
        self, 
        records: List[ExecutionRecord]
    ) -> List[LoopPattern]:
        """Detect stage oscillation patterns."""
        patterns = []
        
        # Group by stage
        stage_records = {}
        for record in records:
            if record.stage:
                if record.stage not in stage_records:
                    stage_records[record.stage] = []
                stage_records[record.stage].append(record)
        
        # Look for stages with too many executions
        for stage, stage_record_list in stage_records.items():
            if len(stage_record_list) > 10:  # More than 10 executions in window
                time_span = (
                    stage_record_list[-1].timestamp - stage_record_list[0].timestamp
                ).total_seconds()
                
                risk_level = LoopRiskLevel.CRITICAL if len(stage_record_list) > 20 else LoopRiskLevel.HIGH
                
                patterns.append(LoopPattern(
                    pattern_type="stage_oscillation",
                    method_names=[r.method_name for r in stage_record_list],
                    execution_count=len(stage_record_list),
                    time_span_seconds=time_span,
                    risk_level=risk_level,
                    first_occurrence=stage_record_list[0].timestamp,
                    last_occurrence=stage_record_list[-1].timestamp,
                    stage=stage,
                    recommendation=f"Stage {stage.value} executed {len(stage_record_list)} times - check for loops"
                ))
        
        return patterns
    
    def get_status_report(self) -> Dict[str, Any]:
        """
        Get comprehensive status report.
        
        Returns:
            Dictionary with system status and metrics
        """
        with self._lock:
            total_time = (datetime.now(timezone.utc) - self._start_time).total_seconds()
            
            return {
                'system_status': 'EMERGENCY_STOP' if self._emergency_stop else 'ACTIVE',
                'total_execution_time_seconds': total_time,
                'total_executions': len(self._execution_records),
                'method_counts': dict(self._method_counts),
                'stage_counts': {k.value: v for k, v in self._stage_counts.items()},
                'blocked_methods': list(self._blocked_methods),
                'blocked_stages': [s.value for s in self._blocked_stages],
                'detected_patterns': len(self._detected_patterns),
                'recent_patterns': [
                    {
                        'type': p.pattern_type,
                        'risk_level': p.risk_level.value,
                        'execution_count': p.execution_count,
                        'methods': p.method_names[:3],  # First 3 methods
                        'recommendation': p.recommendation
                    }
                    for p in self._detected_patterns[-5:]  # Last 5 patterns
                ],
                'limits': {
                    'max_executions_per_method': self.max_executions_per_method,
                    'max_executions_per_stage': self.max_executions_per_stage,
                    'max_total_execution_minutes': self.max_total_execution_time.total_seconds() / 60
                }
            }
    
    def reset_system(self) -> None:
        """Reset the loop prevention system."""
        with self._lock:
            self._execution_records.clear()
            self._method_counts.clear()
            self._stage_counts.clear()
            self._blocked_methods.clear()
            self._blocked_stages.clear()
            self._detected_patterns.clear()
            self._emergency_stop = False
            self._start_time = datetime.now(timezone.utc)
            
            logger.info("Loop prevention system reset")
    
    def cleanup_old_records(self, max_age_minutes: int = 60) -> int:
        """
        Clean up old execution records.
        
        Args:
            max_age_minutes: Maximum age of records to keep
            
        Returns:
            Number of records removed
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
        
        with self._lock:
            initial_count = len(self._execution_records)
            self._execution_records = [
                r for r in self._execution_records
                if r.timestamp >= cutoff_time
            ]
            
            removed_count = initial_count - len(self._execution_records)
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old execution records")
            
            return removed_count
    
    def should_stop_execution(self) -> bool:
        """
        Check if execution should be stopped due to loop prevention
        
        Returns:
            True if execution should be stopped
        """
        with self._lock:
            # Check if emergency stop is active
            if self._emergency_stop:
                return True
            
            # Check if we have exceeded maximum execution time
            if (datetime.now(timezone.utc) - self._start_time) > self.max_total_execution_time:
                return True
            
            # Check if any methods are blocked
            if self._blocked_methods or self._blocked_stages:
                return True
            
            return False
    
    def force_stop(self) -> None:
        """Force stop execution - for emergency situations"""
        with self._lock:
            self._emergency_stop = True
            logger.critical("🚨 Loop prevention system force stopped")

    def get_status(self) -> Dict[str, Any]:
        """Lightweight status used by health checks."""
        with self._lock:
            return {
                'emergency_stop': self._emergency_stop,
                'blocked_methods_count': len(self._blocked_methods),
                'blocked_stages_count': len(self._blocked_stages),
                'total_executions': len(self._execution_records),
                'uptime_seconds': (datetime.now(timezone.utc) - self._start_time).total_seconds(),
            }