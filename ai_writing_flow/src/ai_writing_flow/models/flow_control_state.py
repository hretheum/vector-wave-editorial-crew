"""
Flow Control State - Core state management for AI Writing Flow

This module implements the FlowControlState model with proper state tracking,
retry management, and execution history to prevent infinite loops.
"""

from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple, Optional, Any
from uuid import uuid4
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum
import threading
import logging

from .flow_stage import FlowStage, can_transition, is_terminal_stage


class StageStatus(str, Enum):
    """Status of stage execution."""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class StageResult(BaseModel):
    """Result of a single stage execution."""
    stage: FlowStage
    status: StageStatus
    output: Optional[Any] = None
    execution_time_seconds: float
    retry_count: int = 0
    error_details: Optional[str] = None
    agent_executed: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StageTransition(BaseModel):
    """Immutable record of stage transition."""
    from_stage: FlowStage
    to_stage: FlowStage
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    transition_id: str = Field(default_factory=lambda: str(uuid4()))


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class FlowControlState(BaseModel):
    """
    Central state management for flow execution.
    
    Tracks current stage, history, retries, and circuit breaker states
    to ensure stable and predictable flow execution without loops.
    """
    
    # Constants
    MAX_HISTORY_SIZE: int = 1000
    MAX_STAGE_EXECUTIONS: int = 10
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS: int = 300
    
    # Core flow state
    current_stage: FlowStage = FlowStage.INPUT_VALIDATION
    completed_stages: Set[FlowStage] = Field(default_factory=set)
    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Thread safety (using private attribute instead of field)
    # Note: _lock is a private attribute, not a Pydantic field
    
    # Retry management
    retry_count: Dict[str, int] = Field(default_factory=dict)
    max_retries: Dict[str, int] = Field(default_factory=lambda: {
        "draft_generation": 3,
        "style_validation": 2,
        "quality_assessment": 2,
        "research": 1
    })
    
    # Execution history
    execution_history: List[StageTransition] = Field(default_factory=list)
    stage_results: Dict[str, StageResult] = Field(default_factory=dict)
    
    # Circuit breaker states
    circuit_breaker_state: Dict[str, CircuitBreakerState] = Field(
        default_factory=lambda: {stage.value: CircuitBreakerState.CLOSED for stage in FlowStage}
    )
    circuit_breaker_failures: Dict[str, int] = Field(default_factory=dict)
    circuit_breaker_last_failure: Dict[str, datetime] = Field(default_factory=dict)
    
    # Timeouts (in seconds)
    stage_timeouts: Dict[str, int] = Field(default_factory=lambda: {
        FlowStage.INPUT_VALIDATION.value: 30,
        FlowStage.RESEARCH.value: 120,
        FlowStage.AUDIENCE_ALIGN.value: 60,
        FlowStage.DRAFT_GENERATION.value: 180,
        FlowStage.STYLE_VALIDATION.value: 90,
        FlowStage.QUALITY_CHECK.value: 60,
        FlowStage.FINALIZED.value: 30,
        FlowStage.FAILED.value: 30
    })
    
    # Performance metrics
    total_execution_time: float = 0.0
    total_retry_count: int = 0
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
    
    def __init__(self, **data):
        """Initialize FlowControlState with thread lock."""
        super().__init__(**data)
        self._lock = threading.RLock()
        
    def add_transition(self, to_stage: FlowStage, reason: str = "") -> StageTransition:
        """Record a stage transition with loop prevention and validation."""
        logger = logging.getLogger(__name__)
        
        # Validate transition is allowed
        if not self.validate_transition(self.current_stage, to_stage):
            allowed = self.get_next_valid_stages()
            raise ValueError(
                f"Invalid transition: {self.current_stage.value} → {to_stage.value}. "
                f"Allowed transitions: {[s.value for s in allowed]}"
            )
        
        # Check if trying to transition from terminal state
        if is_terminal_stage(self.current_stage):
            raise ValueError(f"Cannot transition from terminal stage: {self.current_stage.value}")
        
        # Check execution limit
        if self.has_exceeded_execution_limit(to_stage):
            raise ValueError(f"Stage {to_stage.value} exceeded execution limit of {self.MAX_STAGE_EXECUTIONS}")
        
        # Log transition
        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        logger.info(
            f"Flow {self.execution_id}: {self.current_stage.value} → {to_stage.value} "
            f"(elapsed: {elapsed:.2f}s, reason: {reason})"
        )
        
        with self._lock:
            transition = StageTransition(
                from_stage=self.current_stage,
                to_stage=to_stage,
                reason=reason
            )
            self.execution_history.append(transition)
            
            # Prevent memory leak
            if len(self.execution_history) > self.MAX_HISTORY_SIZE:
                self.execution_history = self.execution_history[-self.MAX_HISTORY_SIZE//2:]
                logger.debug(f"Trimmed execution history to {len(self.execution_history)} entries")
            
            self.current_stage = to_stage
            return transition
    
    def mark_stage_complete(self, stage: FlowStage, result: StageResult) -> None:
        """Mark a stage as completed with its result."""
        with self._lock:
            self.completed_stages.add(stage)
            self.stage_results[stage.value] = result
            self.total_execution_time += result.execution_time_seconds
            self.total_retry_count += result.retry_count
    
    def is_stage_complete(self, stage: FlowStage) -> bool:
        """Check if a stage has been completed."""
        return stage in self.completed_stages
    
    def get_stage_retry_count(self, stage: FlowStage) -> int:
        """Get current retry count for a stage."""
        return self.retry_count.get(stage.value, 0)
    
    def increment_retry_count(self, stage: FlowStage) -> int:
        """Thread-safe increment and return retry count for a stage."""
        with self._lock:
            current = self.retry_count.get(stage.value, 0)
            self.retry_count[stage.value] = current + 1
            return current + 1
    
    def can_retry_stage(self, stage: FlowStage) -> bool:
        """Check if stage can be retried based on max retry limit."""
        current_retries = self.get_stage_retry_count(stage)
        max_allowed = self.max_retries.get(stage.value, 0)
        return current_retries < max_allowed
    
    def get_stage_timeout(self, stage: FlowStage) -> int:
        """Get timeout for a specific stage in seconds."""
        return self.stage_timeouts.get(stage.value, 60)  # Default 60s
    
    def update_circuit_breaker(self, stage: FlowStage, success: bool) -> None:
        """Update circuit breaker state based on execution result."""
        stage_key = stage.value
        
        if success:
            # Reset failures on success
            self.circuit_breaker_failures[stage_key] = 0
            if self.circuit_breaker_state[stage_key] != CircuitBreakerState.CLOSED:
                self.circuit_breaker_state[stage_key] = CircuitBreakerState.CLOSED
        else:
            # Increment failures
            failures = self.circuit_breaker_failures.get(stage_key, 0) + 1
            self.circuit_breaker_failures[stage_key] = failures
            self.circuit_breaker_last_failure[stage_key] = datetime.now(timezone.utc)
            
            # Open circuit breaker after threshold failures
            if failures >= self.CIRCUIT_BREAKER_FAILURE_THRESHOLD:
                self.circuit_breaker_state[stage_key] = CircuitBreakerState.OPEN
    
    def is_circuit_breaker_open(self, stage: FlowStage) -> bool:
        """Check if circuit breaker is open for a stage."""
        return self.circuit_breaker_state.get(stage.value) == CircuitBreakerState.OPEN
    
    def should_attempt_circuit_recovery(self, stage: FlowStage) -> bool:
        """
        Check if circuit breaker should attempt recovery.
        
        Args:
            stage: Stage to check
            
        Returns:
            True if recovery should be attempted
        """
        stage_key = stage.value
        if self.circuit_breaker_state.get(stage_key) != CircuitBreakerState.OPEN:
            return False
        
        last_failure = self.circuit_breaker_last_failure.get(stage_key)
        if not last_failure:
            return True
        
        elapsed = (datetime.now(timezone.utc) - last_failure).total_seconds()
        return elapsed > self.CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS
    
    def get_circuit_breaker_state(self, stage: FlowStage) -> CircuitBreakerState:
        """Get circuit breaker state for a stage."""
        return self.circuit_breaker_state.get(stage.value, CircuitBreakerState.CLOSED)
    
    def get_stage_result(self, stage: FlowStage) -> Optional[StageResult]:
        """Get result for a specific stage."""
        return self.stage_results.get(stage.value)
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of flow execution."""
        return {
            "execution_id": self.execution_id,
            "current_stage": self.current_stage.value,
            "completed_stages": [s.value for s in self.completed_stages],
            "total_execution_time": self.total_execution_time,
            "total_retry_count": self.total_retry_count,
            "transitions": len(self.execution_history),
            "circuit_breakers_open": [
                stage for stage, state in self.circuit_breaker_state.items()
                if state == CircuitBreakerState.OPEN
            ]
        }
    
    def has_exceeded_execution_limit(self, stage: FlowStage) -> bool:
        """Check if stage has been executed too many times."""
        executions = sum(1 for t in self.execution_history if t.to_stage == stage)
        return executions >= self.MAX_STAGE_EXECUTIONS
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        now = datetime.now(timezone.utc)
        execution_time = (now - self.start_time).total_seconds()
        
        return {
            "is_healthy": not any(
                self.circuit_breaker_state[s] == CircuitBreakerState.OPEN 
                for s in self.circuit_breaker_state
            ),
            "execution_time_seconds": execution_time,
            "stages_completed": len(self.completed_stages),
            "total_retries": self.total_retry_count,
            "open_circuit_breakers": [
                stage for stage, state in self.circuit_breaker_state.items()
                if state == CircuitBreakerState.OPEN
            ],
            "potential_loops": self._detect_potential_loops()
        }
    
    def _detect_potential_loops(self) -> List[str]:
        """Detect potential infinite loops in execution history."""
        warnings = []
        
        # Check for rapid back-and-forth transitions
        recent_transitions = self.execution_history[-10:] if len(self.execution_history) >= 10 else self.execution_history
        
        for i in range(len(recent_transitions) - 3):
            t1, t2, t3 = recent_transitions[i:i+3]
            if t1.from_stage == t3.from_stage and t1.to_stage == t3.to_stage:
                warnings.append(f"Potential loop detected: {t1.from_stage.value} ↔ {t1.to_stage.value}")
        
        return list(set(warnings))  # Unique warnings only
    
    @field_validator('current_stage')
    @classmethod
    def validate_current_stage(cls, v):
        """Validate current stage is a valid FlowStage."""
        if not isinstance(v, FlowStage):
            raise ValueError(f"Invalid stage type: {type(v)}")
        return v
    
    @model_validator(mode='after')
    def validate_state_consistency(self):
        """Validate internal state consistency."""
        # Check if completed stages are valid
        for stage in self.completed_stages:
            if not isinstance(stage, FlowStage):
                raise ValueError(f"Invalid completed stage: {stage}")
        
        # Check circuit breaker consistency
        valid_stages = {s.value for s in FlowStage}
        for stage_key in self.circuit_breaker_state:
            if stage_key not in valid_stages:
                raise ValueError(f"Invalid circuit breaker stage: {stage_key}")
        
        return self
    
    def validate_transition(self, from_stage: FlowStage, to_stage: FlowStage) -> bool:
        """
        Validate if a transition from one stage to another is allowed.
        
        Returns:
            True if transition is valid, False otherwise
        """
        return can_transition(from_stage, to_stage)
    
    def get_next_valid_stages(self) -> List[FlowStage]:
        """
        Get list of valid next stages from current stage.
        
        Returns:
            List of FlowStage enums that are valid transitions
        """
        from .flow_stage import get_allowed_transitions
        return get_allowed_transitions(self.current_stage)
    
    def force_transition_to_failed(self, reason: str) -> None:
        """
        Force transition to FAILED state from any stage.
        
        This is used for emergency stops and unrecoverable errors.
        
        Args:
            reason: Reason for failure
        """
        logger = logging.getLogger(__name__)
        logger.warning(f"Forcing transition to FAILED state: {reason}")
        
        with self._lock:
            transition = StageTransition(
                from_stage=self.current_stage,
                to_stage=FlowStage.FAILED,
                reason=f"FORCED FAILURE: {reason}"
            )
            self.execution_history.append(transition)
            self.current_stage = FlowStage.FAILED
    
    def start_stage_execution(self, stage: FlowStage) -> 'StageExecution':
        """
        Start execution of a stage.
        
        Args:
            stage: Stage to start executing
            
        Returns:
            StageExecution instance to track execution
        """
        from .stage_execution import StageExecution
        
        return StageExecution(
            stage=stage,
            execution_id=self.execution_id,
            retry_attempt=self.get_stage_retry_count(stage)
        )
    
    def reset_stage(self, stage: FlowStage) -> None:
        """
        Reset a stage's retry count and remove from completed stages.
        
        Args:
            stage: Stage to reset
        """
        with self._lock:
            self.retry_count.pop(stage.value, None)
            self.completed_stages.discard(stage)
            self.stage_results.pop(stage.value, None)
    
    def get_execution_duration(self) -> float:
        """
        Get total execution duration in seconds.
        
        Returns:
            Duration since flow started
        """
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()
    
    def is_completed(self) -> bool:
        """
        Check if flow has reached a terminal state.
        
        Returns:
            True if current stage is FINALIZED or FAILED
        """
        return is_terminal_stage(self.current_stage)
    
    @property
    def global_context(self) -> Dict[str, Any]:
        """
        Get global context for sharing between stages.
        
        Returns:
            Dictionary of global context data
        """
        # For now, return empty dict. Can be extended to include shared data.
        return {}
    
    @property
    def last_update(self) -> datetime:
        """
        Get timestamp of last state update.
        
        Returns:
            Last transition timestamp or start time
        """
        if self.execution_history:
            return self.execution_history[-1].timestamp
        return self.start_time
    
    @property
    def total_retries(self) -> int:
        """
        Get total number of retries across all stages.
        
        This is an alias for total_retry_count for API compatibility.
        
        Returns:
            Total retry count
        """
        return self.total_retry_count