"""
Comprehensive unit tests for CircuitBreaker - Phase 3, Task 21.2

This test suite provides 100% coverage for CircuitBreaker including:
- Initialization and state management
- State transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
- Failure threshold handling
- Recovery timeout behavior
- Thread safety
- Integration with FlowControlState
- Async support
- Decorator pattern
- Edge cases and error scenarios
"""

import pytest
import threading
import time
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from ai_writing_flow.utils.circuit_breaker import (
    CircuitBreaker, StageCircuitBreaker, CircuitBreakerError
)
from ai_writing_flow.models.flow_control_state import FlowControlState, CircuitBreakerState
from ai_writing_flow.models.flow_stage import FlowStage


class TestCircuitBreakerInitialization:
    """Test CircuitBreaker initialization and configuration"""
    
    def test_default_initialization(self):
        """Test circuit breaker with default parameters"""
        cb = CircuitBreaker("test_service")
        
        assert cb.name == "test_service"
        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 60
        assert cb.expected_exception == Exception
        assert cb.flow_state is None
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.is_closed
        assert not cb.is_open
        assert not cb.is_half_open
        
    def test_custom_initialization(self):
        """Test circuit breaker with custom parameters"""
        flow_state = FlowControlState()
        cb = CircuitBreaker(
            name="custom_service",
            failure_threshold=3,
            recovery_timeout=30,
            expected_exception=ValueError,
            flow_state=flow_state
        )
        
        assert cb.name == "custom_service"
        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 30
        assert cb.expected_exception == ValueError
        assert cb.flow_state == flow_state
        
    def test_initial_metrics(self):
        """Test initial metric values"""
        cb = CircuitBreaker("metrics_test")
        status = cb.get_status()
        
        assert status['name'] == "metrics_test"
        assert status['state'] == CircuitBreakerState.CLOSED.value
        assert status['failure_count'] == 0
        assert status['total_calls'] == 0
        assert status['total_successes'] == 0
        assert status['total_failures'] == 0
        assert status['success_rate'] == 0
        assert status['time_since_failure_seconds'] is None


class TestCircuitBreakerStateTransitions:
    """Test circuit breaker state transitions"""
    
    def test_closed_to_open_on_threshold(self):
        """Test transition from CLOSED to OPEN when failure threshold is reached"""
        cb = CircuitBreaker("test", failure_threshold=3)
        
        # Function that always fails
        def failing_func():
            raise Exception("Test failure")
        
        # Fail 3 times to open circuit
        for i in range(3):
            with pytest.raises(Exception):
                cb.call(failing_func)
        
        assert cb.is_open
        assert not cb.is_closed
        assert cb._failure_count == 3
        
    def test_open_blocks_calls(self):
        """Test that OPEN state blocks all calls"""
        cb = CircuitBreaker("test", failure_threshold=2)
        
        # Open the circuit
        cb.force_open()
        
        # Try to make a call
        with pytest.raises(CircuitBreakerError) as exc_info:
            cb.call(lambda: "test")
        
        assert "is OPEN - calls are blocked" in str(exc_info.value)
        
    def test_open_to_half_open_after_timeout(self):
        """Test transition from OPEN to HALF_OPEN after recovery timeout"""
        cb = CircuitBreaker("test", recovery_timeout=1)
        
        # Open the circuit
        cb.force_open()
        assert cb.is_open
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        # State should transition to HALF_OPEN on next check
        assert cb.state == CircuitBreakerState.HALF_OPEN
        assert cb.is_half_open
        
    def test_half_open_to_closed_on_success(self):
        """Test transition from HALF_OPEN to CLOSED on successful call"""
        cb = CircuitBreaker("test", recovery_timeout=0.1)
        
        # Set to HALF_OPEN state
        cb.force_open()
        time.sleep(0.2)  # Wait for recovery timeout
        
        # Successful call should close the circuit
        result = cb.call(lambda: "success")
        
        assert result == "success"
        assert cb.is_closed
        assert cb._failure_count == 0
        
    def test_half_open_to_open_on_failure(self):
        """Test transition from HALF_OPEN back to OPEN on failure"""
        cb = CircuitBreaker("test", recovery_timeout=0.1)
        
        # Set to HALF_OPEN state
        cb.force_open()
        time.sleep(0.2)  # Wait for recovery timeout
        assert cb.is_half_open
        
        # Failed call should reopen the circuit
        with pytest.raises(Exception):
            cb.call(lambda: 1/0)
        
        assert cb.is_open
        assert not cb.is_half_open


class TestCircuitBreakerFunctionExecution:
    """Test function execution through circuit breaker"""
    
    def test_successful_call(self):
        """Test successful function execution"""
        cb = CircuitBreaker("test")
        
        def add(a, b):
            return a + b
        
        result = cb.call(add, 2, 3)
        assert result == 5
        
        status = cb.get_status()
        assert status['total_calls'] == 1
        assert status['total_successes'] == 1
        assert status['total_failures'] == 0
        assert status['success_rate'] == 1.0
        
    def test_failed_call(self):
        """Test failed function execution"""
        cb = CircuitBreaker("test")
        
        def failing_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            cb.call(failing_func)
        
        status = cb.get_status()
        assert status['total_calls'] == 1
        assert status['total_successes'] == 0
        assert status['total_failures'] == 1
        assert status['failure_count'] == 1
        
    def test_expected_vs_unexpected_exceptions(self):
        """Test handling of expected vs unexpected exceptions"""
        cb = CircuitBreaker("test", expected_exception=ValueError)
        
        # Expected exception should be counted
        with pytest.raises(ValueError):
            cb.call(lambda: exec('raise ValueError()'))
        
        assert cb._failure_count == 1
        
        # Unexpected exception should not be counted
        with pytest.raises(TypeError):
            cb.call(lambda: exec('raise TypeError()'))
        
        # Failure count should not increase for unexpected exception
        assert cb._failure_count == 1
        
    def test_decorator_pattern(self):
        """Test using circuit breaker as decorator"""
        cb = CircuitBreaker("test", failure_threshold=2)
        
        @cb
        def protected_function(x):
            if x < 0:
                raise ValueError("Negative value")
            return x * 2
        
        # Successful calls
        assert protected_function(5) == 10
        
        # Failed calls
        with pytest.raises(ValueError):
            protected_function(-1)
        with pytest.raises(ValueError):
            protected_function(-2)
        
        # Circuit should be open now
        with pytest.raises(CircuitBreakerError):
            protected_function(5)


class TestCircuitBreakerAsync:
    """Test async function support"""
    
    @pytest.mark.asyncio
    async def test_async_successful_call(self):
        """Test successful async function execution"""
        cb = CircuitBreaker("test")
        
        async def async_add(a, b):
            await asyncio.sleep(0.01)
            return a + b
        
        result = await cb.call_async(async_add, 3, 4)
        assert result == 7
        
        status = cb.get_status()
        assert status['total_successes'] == 1
        
    @pytest.mark.asyncio
    async def test_async_failed_call(self):
        """Test failed async function execution"""
        cb = CircuitBreaker("test")
        
        async def async_fail():
            await asyncio.sleep(0.01)
            raise ValueError("Async error")
        
        with pytest.raises(ValueError):
            await cb.call_async(async_fail)
        
        assert cb._failure_count == 1
        
    @pytest.mark.asyncio
    async def test_async_circuit_open(self):
        """Test async calls blocked when circuit is open"""
        cb = CircuitBreaker("test")
        cb.force_open()
        
        async def async_func():
            return "test"
        
        with pytest.raises(CircuitBreakerError):
            await cb.call_async(async_func)


class TestFlowStateIntegration:
    """Test integration with FlowControlState"""
    
    def test_update_flow_state_on_success(self):
        """Test that flow state is updated on successful calls"""
        flow_state = FlowControlState()
        cb = CircuitBreaker("research", flow_state=flow_state)
        
        # Successful call
        cb.call(lambda: "success")
        
        # Check flow state was updated
        assert flow_state.circuit_breaker_failures.get(FlowStage.RESEARCH.value, 0) == 0
        
    def test_update_flow_state_on_failure(self):
        """Test that flow state is updated on failed calls"""
        flow_state = FlowControlState()
        # Use flow state's threshold for consistency
        threshold = flow_state.CIRCUIT_BREAKER_FAILURE_THRESHOLD
        cb = CircuitBreaker("research", flow_state=flow_state, failure_threshold=threshold)
        
        # Failed calls to reach threshold
        for i in range(threshold):
            with pytest.raises(Exception):
                cb.call(lambda: 1/0)
        
        # Check flow state was updated
        assert flow_state.is_circuit_breaker_open(FlowStage.RESEARCH)
        
    def test_stage_name_mapping(self):
        """Test mapping of circuit breaker names to flow stages"""
        flow_state = FlowControlState()
        
        # Test exact matches
        cb1 = CircuitBreaker("research", flow_state=flow_state)
        cb1._on_failure(Exception())
        assert FlowStage.RESEARCH.value in flow_state.circuit_breaker_failures
        
        # Test aliases
        cb2 = CircuitBreaker("draft", flow_state=flow_state)
        cb2._on_failure(Exception())
        assert FlowStage.DRAFT_GENERATION.value in flow_state.circuit_breaker_failures


class TestStageCircuitBreaker:
    """Test StageCircuitBreaker integration"""
    
    def test_stage_circuit_breaker_initialization(self):
        """Test StageCircuitBreaker initialization"""
        flow_state = FlowControlState()
        scb = StageCircuitBreaker(FlowStage.RESEARCH, flow_state)
        
        assert scb.stage == FlowStage.RESEARCH
        assert scb.name == FlowStage.RESEARCH.value
        assert scb.flow_state == flow_state
        assert scb.failure_threshold == flow_state.CIRCUIT_BREAKER_FAILURE_THRESHOLD
        assert scb.recovery_timeout == flow_state.CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS
        
    def test_stage_circuit_breaker_custom_thresholds(self):
        """Test StageCircuitBreaker with custom thresholds"""
        flow_state = FlowControlState()
        scb = StageCircuitBreaker(
            FlowStage.DRAFT_GENERATION,
            flow_state,
            failure_threshold=2,
            recovery_timeout=30
        )
        
        assert scb.failure_threshold == 2
        assert scb.recovery_timeout == 30
        
    def test_sync_from_flow_state(self):
        """Test syncing state from FlowControlState"""
        flow_state = FlowControlState()
        
        # Open circuit breaker in flow state
        for i in range(flow_state.CIRCUIT_BREAKER_FAILURE_THRESHOLD):
            flow_state.update_circuit_breaker(FlowStage.RESEARCH, success=False)
        
        # Create StageCircuitBreaker - should sync state
        scb = StageCircuitBreaker(FlowStage.RESEARCH, flow_state)
        assert scb.is_open


class TestThreadSafety:
    """Test thread safety of circuit breaker"""
    
    def test_concurrent_calls(self):
        """Test concurrent calls are handled safely"""
        cb = CircuitBreaker("test", failure_threshold=10)
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                # Mix of successful and failing calls
                if worker_id % 2 == 0:
                    result = cb.call(lambda: f"success_{worker_id}")
                    results.append(result)
                else:
                    cb.call(lambda: 1/0)
            except Exception as e:
                errors.append((worker_id, type(e).__name__))
        
        # Launch concurrent threads
        threads = []
        for i in range(20):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Verify results
        assert len(results) + len(errors) == 20
        status = cb.get_status()
        assert status['total_calls'] == 20
        
    def test_concurrent_state_transitions(self):
        """Test state transitions are thread-safe"""
        cb = CircuitBreaker("test", failure_threshold=5, recovery_timeout=0.1)
        
        def failing_worker():
            for _ in range(10):
                try:
                    cb.call(lambda: 1/0)
                except:
                    pass
                time.sleep(0.01)
        
        # Multiple threads causing failures
        threads = []
        for _ in range(5):
            t = threading.Thread(target=failing_worker)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Circuit should be open after threshold failures
        assert cb.is_open


class TestManualControl:
    """Test manual control methods"""
    
    def test_manual_reset(self):
        """Test manual reset to closed state"""
        cb = CircuitBreaker("test")
        
        # Open the circuit
        cb.force_open()
        assert cb.is_open
        
        # Manual reset
        cb.reset()
        assert cb.is_closed
        assert cb._failure_count == 0
        assert cb._last_failure_time is None
        
    def test_force_open(self):
        """Test forcing circuit to open state"""
        cb = CircuitBreaker("test")
        
        assert cb.is_closed
        
        # Force open
        cb.force_open()
        assert cb.is_open
        assert cb._last_failure_time is not None
        
        # Calls should be blocked
        with pytest.raises(CircuitBreakerError):
            cb.call(lambda: "test")


class TestMetricsAndStatus:
    """Test metrics and status reporting"""
    
    def test_detailed_status(self):
        """Test detailed status reporting"""
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=30)
        
        # Mix of successful and failed calls
        cb.call(lambda: "success1")
        cb.call(lambda: "success2")
        
        with pytest.raises(Exception):
            cb.call(lambda: 1/0)
        
        status = cb.get_status()
        
        assert status['name'] == "test"
        assert status['state'] == CircuitBreakerState.CLOSED.value
        assert status['failure_count'] == 1
        assert status['failure_threshold'] == 3
        assert status['total_calls'] == 3
        assert status['total_successes'] == 2
        assert status['total_failures'] == 1
        assert status['success_rate'] == 2/3
        assert status['recovery_timeout_seconds'] == 30
        assert status['time_since_failure_seconds'] is not None
        assert status['last_failure_time'] is not None
        assert status['last_success_time'] is not None
        
    def test_status_when_no_calls(self):
        """Test status when no calls have been made"""
        cb = CircuitBreaker("test")
        status = cb.get_status()
        
        assert status['success_rate'] == 0
        assert status['time_since_failure_seconds'] is None
        assert status['last_failure_time'] is None
        assert status['last_success_time'] is None


class TestEdgeCases:
    """Test edge cases and error scenarios"""
    
    def test_recovery_without_failure_time(self):
        """Test recovery check when no failure time is set"""
        cb = CircuitBreaker("test")
        cb._state = CircuitBreakerState.OPEN
        cb._last_failure_time = None
        
        # Should return True when no failure time
        assert cb._should_attempt_reset()
        
    def test_nested_exceptions(self):
        """Test handling of nested exceptions"""
        cb = CircuitBreaker("test")
        
        def nested_fail():
            try:
                raise ValueError("Inner error")
            except ValueError:
                raise RuntimeError("Outer error")
        
        with pytest.raises(RuntimeError):
            cb.call(nested_fail)
        
        assert cb._failure_count == 1
        
    def test_circuit_breaker_with_return_none(self):
        """Test circuit breaker with functions returning None"""
        cb = CircuitBreaker("test")
        
        def return_none():
            return None
        
        result = cb.call(return_none)
        assert result is None
        assert cb._success_count == 1
        
    def test_very_short_recovery_timeout(self):
        """Test with very short recovery timeout"""
        cb = CircuitBreaker("test", recovery_timeout=0.001)
        
        cb.force_open()
        time.sleep(0.01)
        
        # Should be in HALF_OPEN state
        assert cb.is_half_open


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])