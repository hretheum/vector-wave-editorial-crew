"""
CircuitBreaker - Implements circuit breaker pattern for fault tolerance

This module provides circuit breaker functionality to prevent cascading failures
and provide graceful degradation when external services or components fail.
"""

import time
from datetime import datetime, timedelta
from typing import Optional, Callable, Any, Dict, TypeVar
from functools import wraps
from enum import Enum
import threading
import logging

from ..models.flow_stage import FlowStage
from ..models.flow_control_state import FlowControlState, CircuitBreakerState


logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open and calls are blocked."""
    pass


class CircuitBreaker:
    """
    Implements the circuit breaker pattern for fault tolerance.
    
    The circuit breaker has three states:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Calls are blocked due to failures
    - HALF_OPEN: Testing if service has recovered
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        flow_state: Optional[FlowControlState] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Name of the circuit breaker (usually stage name)
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
            flow_state: Optional FlowControlState for integration
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.flow_state = flow_state
        
        # Thread safety
        self._lock = threading.RLock()
        
        # State tracking
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._state = CircuitBreakerState.CLOSED
        
        # Metrics
        self._call_count = 0
        self._success_count = 0
        self._failure_count_total = 0
        self._last_success_time: Optional[datetime] = None
        # Track how the breaker entered OPEN to tune transitions
        self._opened_manually: bool = False
    
    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        with self._lock:
            # Lazily update state on access to reflect time-based transitions
            # Only allow OPEN -> HALF_OPEN on read if it was manually forced open.
            self._update_state_on_check()
            return self._state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitBreakerState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking calls)."""
        return self.state == CircuitBreakerState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self.state == CircuitBreakerState.HALF_OPEN
    
    def _update_state_on_check(self) -> None:
        """Update state when merely checking status (non-intrusive)."""
        if self._state == CircuitBreakerState.OPEN and self._opened_manually:
            if self._should_attempt_reset():
                self._state = CircuitBreakerState.HALF_OPEN
                logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN state (check)")

    def _update_state_on_call(self) -> None:
        """Update state right before attempting a protected call."""
        if self._state == CircuitBreakerState.OPEN and self._should_attempt_reset():
            self._state = CircuitBreakerState.HALF_OPEN
            logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN state (call)")
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self._last_failure_time:
            return True
        
        elapsed = (datetime.now() - self._last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def _get_stage_from_name(self, name: str) -> Optional[FlowStage]:
        """Map circuit breaker name to FlowStage."""
        try:
            # Try exact match first
            return FlowStage(name.lower())
        except ValueError:
            # Try mapping common aliases
            stage_mapping = {
                'research': FlowStage.RESEARCH,
                'draft': FlowStage.DRAFT_GENERATION,
                'style': FlowStage.STYLE_VALIDATION,
                'quality': FlowStage.QUALITY_CHECK,
                'input': FlowStage.INPUT_VALIDATION,
                'audience': FlowStage.AUDIENCE_ALIGN
            }
            return stage_mapping.get(name.lower())
    
    def _on_success(self) -> None:
        """Handle successful call."""
        with self._lock:
            self._success_count += 1
            self._last_success_time = datetime.now()
            
            if self._state == CircuitBreakerState.HALF_OPEN:
                # Success in half-open state means we can close the circuit
                self._state = CircuitBreakerState.CLOSED
                self._failure_count = 0
                logger.info(f"Circuit breaker '{self.name}' closed after successful recovery")
            
            # Update flow state if available
            if self.flow_state:
                stage = self._get_stage_from_name(self.name)
                if stage:
                    self.flow_state.update_circuit_breaker(stage, success=True)
    
    def _on_failure(self, exception: Exception) -> None:
        """Handle failed call."""
        with self._lock:
            self._failure_count += 1
            self._failure_count_total += 1
            self._last_failure_time = datetime.now()
            
            if self._state == CircuitBreakerState.HALF_OPEN:
                # Failure in half-open state means service is still down
                self._state = CircuitBreakerState.OPEN
                self._opened_manually = False
                logger.warning(
                    f"Circuit breaker '{self.name}' reopened after failure in HALF_OPEN state"
                )
            elif self._failure_count >= self.failure_threshold:
                # Too many failures, open the circuit
                self._state = CircuitBreakerState.OPEN
                self._opened_manually = False
                logger.error(
                    f"Circuit breaker '{self.name}' opened after {self._failure_count} failures"
                )
            
            # Update flow state if available
            if self.flow_state:
                stage = self._get_stage_from_name(self.name)
                if stage:
                    self.flow_state.update_circuit_breaker(stage, success=False)
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Function to execute
            *args: Arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Result of function execution
            
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If function fails
        """
        with self._lock:
            self._call_count += 1
            
            # Check state and potentially update
            self._update_state_on_call()
            if self._state == CircuitBreakerState.OPEN:
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN - calls are blocked"
                )
        
        # Execute the function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure(e)
            raise
    
    async def call_async(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Execute async function through circuit breaker.
        
        Args:
            func: Async function to execute
            *args: Arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Result of function execution
            
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If function fails
        """
        with self._lock:
            self._call_count += 1
            
            # Check state
            self._update_state_on_call()
            if self._state == CircuitBreakerState.OPEN:
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN - calls are blocked"
                )
        
        # Execute the async function
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure(e)
            raise
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator to wrap functions with circuit breaker.
        
        Args:
            func: Function to wrap
            
        Returns:
            Wrapped function
        """
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return self.call(func, *args, **kwargs)
        
        return wrapper
    
    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        with self._lock:
            self._state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            self._opened_manually = False
            logger.info(f"Circuit breaker '{self.name}' manually reset to CLOSED")
    
    def force_open(self) -> None:
        """Manually force the circuit breaker to open state."""
        with self._lock:
            self._state = CircuitBreakerState.OPEN
            self._last_failure_time = datetime.now()
            self._opened_manually = True
            logger.warning(f"Circuit breaker '{self.name}' manually forced to OPEN")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get detailed status of circuit breaker.
        
        Returns:
            Dictionary with circuit breaker metrics
        """
        with self._lock:
            success_rate = (
                self._success_count / self._call_count 
                if self._call_count > 0 else 0
            )
            
            time_since_failure = None
            if self._last_failure_time:
                time_since_failure = (
                    datetime.now() - self._last_failure_time
                ).total_seconds()
            
            return {
                'name': self.name,
                'state': self._state.value,
                'failure_count': self._failure_count,
                'failure_threshold': self.failure_threshold,
                'total_calls': self._call_count,
                'total_successes': self._success_count,
                'total_failures': self._failure_count_total,
                'success_rate': success_rate,
                'time_since_failure_seconds': time_since_failure,
                'recovery_timeout_seconds': self.recovery_timeout,
                'last_failure_time': self._last_failure_time.isoformat() if self._last_failure_time else None,
                'last_success_time': self._last_success_time.isoformat() if self._last_success_time else None
            }


class StageCircuitBreaker(CircuitBreaker):
    """
    Circuit breaker specifically for CrewAI Flow stages.
    
    Integrates with FlowControlState for centralized monitoring.
    """
    
    def __init__(
        self,
        stage: FlowStage,
        flow_state: FlowControlState,
        failure_threshold: Optional[int] = None,
        recovery_timeout: Optional[int] = None
    ):
        """
        Initialize stage-specific circuit breaker.
        
        Args:
            stage: Flow stage to protect
            flow_state: FlowControlState for integration
            failure_threshold: Override default failure threshold
            recovery_timeout: Override default recovery timeout
        """
        # Use flow state's configuration if not overridden
        if failure_threshold is None:
            failure_threshold = flow_state.CIRCUIT_BREAKER_FAILURE_THRESHOLD
        if recovery_timeout is None:
            recovery_timeout = flow_state.CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS
        
        super().__init__(
            name=stage.value,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            flow_state=flow_state
        )
        
        self.stage = stage
        
        # Sync initial state from flow state
        self._sync_from_flow_state()
    
    def _sync_from_flow_state(self) -> None:
        """Synchronize state with FlowControlState."""
        if self.flow_state.is_circuit_breaker_open(self.stage):
            self._state = CircuitBreakerState.OPEN
        elif self.flow_state.should_attempt_circuit_recovery(self.stage):
            self._state = CircuitBreakerState.HALF_OPEN
        else:
            self._state = CircuitBreakerState.CLOSED