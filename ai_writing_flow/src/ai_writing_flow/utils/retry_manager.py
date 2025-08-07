"""
RetryManager - Handles retry logic with exponential backoff

This module implements retry management for stage executions,
including exponential backoff, jitter, and max retry limits.
"""

import asyncio
import random
import time
from datetime import datetime
from typing import Optional, Callable, Any, Dict, TypeVar, Union
from functools import wraps
import logging

from ..models.flow_stage import FlowStage
from ..models.flow_control_state import FlowControlState


logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay_seconds: float = 1.0,
        max_delay_seconds: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_on_exceptions: tuple = (Exception,),
        should_retry: Optional[Callable[[Exception], bool]] = None
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay_seconds: Initial delay between retries
            max_delay_seconds: Maximum delay between retries
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
            retry_on_exceptions: Tuple of exception types to retry on
            should_retry: Optional callable to determine if exception should trigger retry
        """
        self.max_attempts = max_attempts
        self.initial_delay_seconds = initial_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on_exceptions = retry_on_exceptions
        self.should_retry = should_retry or (lambda e: True)


class RetryManager:
    """
    Manages retry logic for flow stage executions.
    
    Provides exponential backoff, jitter, and integration with FlowControlState
    for tracking retry attempts and preventing infinite loops.
    """
    
    def __init__(self, flow_state: FlowControlState):
        """
        Initialize RetryManager with flow state.
        
        Args:
            flow_state: FlowControlState instance for tracking retries
        """
        self.flow_state = flow_state
        self.default_configs: Dict[FlowStage, RetryConfig] = self._init_default_configs()
    
    def _init_default_configs(self) -> Dict[FlowStage, RetryConfig]:
        """Initialize default retry configurations for each stage."""
        return {
            FlowStage.INPUT_VALIDATION: RetryConfig(max_attempts=1),  # No retry for validation
            FlowStage.RESEARCH: RetryConfig(
                max_attempts=2,
                initial_delay_seconds=2.0,
                max_delay_seconds=10.0
            ),
            FlowStage.AUDIENCE_ALIGN: RetryConfig(
                max_attempts=2,
                initial_delay_seconds=1.0
            ),
            FlowStage.DRAFT_GENERATION: RetryConfig(
                max_attempts=3,
                initial_delay_seconds=3.0,
                max_delay_seconds=30.0
            ),
            FlowStage.STYLE_VALIDATION: RetryConfig(
                max_attempts=2,
                initial_delay_seconds=1.0
            ),
            FlowStage.QUALITY_CHECK: RetryConfig(
                max_attempts=2,
                initial_delay_seconds=2.0
            ),
            FlowStage.FINALIZED: RetryConfig(max_attempts=1),
            FlowStage.FAILED: RetryConfig(max_attempts=1)
        }
    
    def get_config(self, stage: FlowStage) -> RetryConfig:
        """
        Get retry configuration for a stage.
        
        Args:
            stage: Stage to get config for
            
        Returns:
            RetryConfig for the stage
        """
        return self.default_configs.get(stage, RetryConfig())
    
    def set_config(self, stage: FlowStage, config: RetryConfig) -> None:
        """
        Set custom retry configuration for a stage.
        
        Args:
            stage: Stage to configure
            config: RetryConfig to use
        """
        self.default_configs[stage] = config
        logger.info(f"Updated retry config for {stage}: max_attempts={config.max_attempts}")
    
    def can_retry(self, stage: FlowStage) -> bool:
        """
        Check if a stage can be retried.
        
        Args:
            stage: Stage to check
            
        Returns:
            True if stage can be retried
        """
        return self.flow_state.can_retry_stage(stage)
    
    def calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """
        Calculate delay for next retry attempt.
        
        Args:
            attempt: Current attempt number (0-based)
            config: Retry configuration
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = min(
            config.initial_delay_seconds * (config.exponential_base ** attempt),
            config.max_delay_seconds
        )
        
        # Add jitter if enabled
        if config.jitter:
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)  # Ensure non-negative
    
    def retry_sync(
        self,
        func: Callable[..., T],
        stage: FlowStage,
        *args,
        **kwargs
    ) -> T:
        """
        Execute a function with retry logic (synchronous).
        
        Args:
            func: Function to execute
            stage: Stage being executed
            *args: Arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of successful execution
            
        Raises:
            Last exception if all retries fail
        """
        config = self.get_config(stage)
        last_exception = None
        
        for attempt in range(config.max_attempts):
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Success - log if this was a retry
                if attempt > 0:
                    logger.info(f"Stage {stage} succeeded after {attempt} retries")
                
                return result
                
            except config.retry_on_exceptions as e:
                last_exception = e
                
                # Check if we should retry this specific exception
                if not config.should_retry(e):
                    logger.error(f"Stage {stage} failed with non-retryable error: {e}")
                    raise
                
                # Increment retry count before checking limits
                self.flow_state.increment_retry_count(stage)
                
                # Check if we've exceeded global retry limit
                if not self.can_retry(stage):
                    logger.error(
                        f"Stage {stage} exceeded global retry limit "
                        f"({self.flow_state.get_stage_retry_count(stage)} attempts)"
                    )
                    raise
                
                # Check if this was our last attempt for this execution
                if attempt >= config.max_attempts - 1:
                    logger.error(
                        f"Stage {stage} failed after {config.max_attempts} attempts: {e}"
                    )
                    raise
                
                # Calculate delay and wait before retry
                delay = self.calculate_delay(attempt, config)
                logger.warning(
                    f"Stage {stage} failed (attempt {attempt + 1}/{config.max_attempts}), "
                    f"retrying in {delay:.1f}s: {e}"
                )
                
                time.sleep(delay)
        
        # Should never reach here
        if last_exception:
            raise last_exception
        raise RuntimeError(f"Unexpected retry loop exit for stage {stage}")
    
    async def retry_async(
        self,
        func: Callable[..., Any],
        stage: FlowStage,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic (asynchronous).
        
        Args:
            func: Async function to execute
            stage: Stage being executed
            *args: Arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of successful execution
            
        Raises:
            Last exception if all retries fail
        """
        config = self.get_config(stage)
        last_exception = None
        
        for attempt in range(config.max_attempts):
            try:
                # Execute the async function
                result = await func(*args, **kwargs)
                
                # Success - log if this was a retry
                if attempt > 0:
                    logger.info(f"Stage {stage} succeeded after {attempt} retries")
                
                return result
                
            except config.retry_on_exceptions as e:
                last_exception = e
                
                # Check if we should retry this specific exception
                if not config.should_retry(e):
                    logger.error(f"Stage {stage} failed with non-retryable error: {e}")
                    raise
                
                # Increment retry count before checking limits
                self.flow_state.increment_retry_count(stage)
                
                # Check if we've exceeded global retry limit
                if not self.can_retry(stage):
                    logger.error(
                        f"Stage {stage} exceeded global retry limit "
                        f"({self.flow_state.get_stage_retry_count(stage)} attempts)"
                    )
                    raise
                
                # Check if this was our last attempt for this execution
                if attempt >= config.max_attempts - 1:
                    logger.error(
                        f"Stage {stage} failed after {config.max_attempts} attempts: {e}"
                    )
                    raise
                
                # Calculate delay and wait before retry
                delay = self.calculate_delay(attempt, config)
                logger.warning(
                    f"Stage {stage} failed (attempt {attempt + 1}/{config.max_attempts}), "
                    f"retrying in {delay:.1f}s: {e}"
                )
                
                await asyncio.sleep(delay)
        
        # Should never reach here
        if last_exception:
            raise last_exception
        raise RuntimeError(f"Unexpected retry loop exit for stage {stage}")
    
    def with_retry(self, stage: FlowStage):
        """
        Decorator for adding retry logic to functions.
        
        Args:
            stage: Stage the decorated function executes
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args, **kwargs) -> T:
                return self.retry_sync(func, stage, *args, **kwargs)
            return wrapper
        return decorator
    
    def get_retry_stats(self, stage: FlowStage) -> Dict[str, Any]:
        """
        Get retry statistics for a stage.
        
        Args:
            stage: Stage to get stats for
            
        Returns:
            Dictionary of retry statistics
        """
        current_retries = self.flow_state.get_stage_retry_count(stage)
        config = self.get_config(stage)
        
        return {
            'current_attempt': current_retries + 1,
            'max_attempts': config.max_attempts,
            'can_retry': self.can_retry(stage),
            'retries_remaining': max(0, config.max_attempts - current_retries - 1),
            'total_retries': current_retries
        }