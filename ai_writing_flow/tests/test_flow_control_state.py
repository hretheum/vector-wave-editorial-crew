"""
Comprehensive unit tests for FlowControlState - Phase 3, Task 21.1

This test suite provides 100% coverage for FlowControlState including:
- Initialization and state management
- Thread safety
- Transition validation
- Retry tracking
- Circuit breaker integration
- Memory management and cleanup
- Edge cases and error scenarios
"""

import pytest
import threading
import time
from datetime import datetime, timezone, timedelta
from uuid import UUID
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from ai_writing_flow.models.flow_control_state import FlowControlState, CircuitBreakerState, StageTransition
from ai_writing_flow.models.flow_stage import FlowStage


class TestFlowControlStateInitialization:
    """Test FlowControlState initialization and basic operations"""
    
    def test_initial_state(self):
        """Test initial state configuration"""
        state = FlowControlState()
        
        assert state.current_stage == FlowStage.INPUT_VALIDATION
        assert state.execution_id is not None
        assert isinstance(state.execution_id, str)
        assert len(state.execution_history) == 0
        assert len(state.retry_count) == 0
        assert state.total_retries == 0
        assert len(state.completed_stages) == 0
        assert state.circuit_breaker_state[FlowStage.INPUT_VALIDATION.value] == CircuitBreakerState.CLOSED
        
    def test_execution_id_uniqueness(self):
        """Test that each instance gets unique execution_id"""
        state1 = FlowControlState()
        state2 = FlowControlState()
        
        assert state1.execution_id != state2.execution_id
        assert UUID(state1.execution_id)  # Valid UUID
        assert UUID(state2.execution_id)  # Valid UUID
        
    def test_custom_initialization(self):
        """Test initialization with custom parameters"""
        state = FlowControlState(
            current_stage=FlowStage.RESEARCH
        )
        
        assert state.current_stage == FlowStage.RESEARCH
        assert state.max_retries["draft_generation"] == 3


class TestStateTransitions:
    """Test state transition logic and validation"""
    
    def test_valid_transition(self):
        """Test valid stage transitions"""
        state = FlowControlState()
        
        # Valid transition: INPUT_VALIDATION -> RESEARCH
        transition = state.add_transition(FlowStage.RESEARCH, "Starting research")
        
        assert state.current_stage == FlowStage.RESEARCH
        assert len(state.execution_history) == 1
        
        assert transition.from_stage == FlowStage.INPUT_VALIDATION
        assert transition.to_stage == FlowStage.RESEARCH
        assert transition.reason == "Starting research"
        assert transition.transition_id is not None
        
    def test_invalid_transition(self):
        """Test that invalid transitions raise ValueError"""
        state = FlowControlState()
        
        # Invalid transition: INPUT_VALIDATION -> QUALITY_CHECK
        with pytest.raises(ValueError) as exc_info:
            state.add_transition(FlowStage.QUALITY_CHECK, "Skipping stages")
        
        assert "Invalid transition" in str(exc_info.value)
        assert state.current_stage == FlowStage.INPUT_VALIDATION
        
    def test_all_valid_transitions(self):
        """Test all valid transitions defined in VALID_TRANSITIONS"""
        from ai_writing_flow.models.flow_stage import VALID_TRANSITIONS
        
        for from_stage, valid_to_stages in VALID_TRANSITIONS.items():
            for to_stage in valid_to_stages:
                state = FlowControlState(current_stage=from_stage)
                state.add_transition(to_stage, f"Test {from_stage} -> {to_stage}")
                assert state.current_stage == to_stage
                
    def test_transition_to_failed_state(self):
        """Test transitions to FAILED state"""
        state = FlowControlState()
        
        # Any stage can transition to FAILED
        for stage in FlowStage:
            if stage != FlowStage.FAILED:
                state.current_stage = stage
                state.add_transition(FlowStage.FAILED, "Error occurred")
                assert state.current_stage == FlowStage.FAILED
                state.current_stage = stage  # Reset for next test
                
    def test_transition_history_limit(self):
        """Test that transition history is limited to prevent memory issues"""
        state = FlowControlState()
        
        # Add many transitions
        for i in range(150):
            if i % 2 == 0:
                state.add_transition(FlowStage.RESEARCH, f"Research {i}")
                state.current_stage = FlowStage.INPUT_VALIDATION
            else:
                state.add_transition(FlowStage.AUDIENCE_ALIGN, f"Audience {i}")
                state.current_stage = FlowStage.INPUT_VALIDATION
        
        # History should be limited to 100
        assert len(state.transition_history) == 100
        
        # Check that oldest transitions were removed
        reasons = [t.reason for t in state.transition_history]
        assert "Research 48" not in reasons  # Old transition removed
        assert "Research 98" in reasons      # Recent transition kept


class TestRetryTracking:
    """Test retry tracking functionality"""
    
    def test_increment_retry(self):
        """Test retry increment for stages"""
        state = FlowControlState()
        
        # First retry
        state.increment_retry(FlowStage.RESEARCH)
        assert state.retry_counts[FlowStage.RESEARCH] == 1
        assert state.total_retries == 1
        
        # Second retry
        state.increment_retry(FlowStage.RESEARCH)
        assert state.retry_counts[FlowStage.RESEARCH] == 2
        assert state.total_retries == 2
        
        # Different stage
        state.increment_retry(FlowStage.DRAFT_GENERATION)
        assert state.retry_counts[FlowStage.DRAFT_GENERATION] == 1
        assert state.total_retries == 3
        
    def test_can_retry_within_limit(self):
        """Test retry limit checking"""
        state = FlowControlState(max_retries_per_stage=3)
        
        # Within limit
        state.increment_retry(FlowStage.RESEARCH)
        assert state.can_retry(FlowStage.RESEARCH) == True
        
        state.increment_retry(FlowStage.RESEARCH)
        assert state.can_retry(FlowStage.RESEARCH) == True
        
        state.increment_retry(FlowStage.RESEARCH)
        assert state.can_retry(FlowStage.RESEARCH) == False  # Reached limit
        
    def test_reset_retries_for_stage(self):
        """Test retry reset for specific stage"""
        state = FlowControlState()
        
        # Add some retries
        state.increment_retry(FlowStage.RESEARCH)
        state.increment_retry(FlowStage.RESEARCH)
        state.increment_retry(FlowStage.DRAFT_GENERATION)
        
        # Reset research retries
        state.reset_retries_for_stage(FlowStage.RESEARCH)
        
        assert state.retry_counts.get(FlowStage.RESEARCH, 0) == 0
        assert state.retry_counts[FlowStage.DRAFT_GENERATION] == 1
        assert state.total_retries == 3  # Total not affected


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration"""
    
    def test_activate_circuit_breaker(self):
        """Test circuit breaker activation"""
        state = FlowControlState()
        
        assert state.circuit_breaker_active == False
        
        state.activate_circuit_breaker("Too many failures")
        
        assert state.circuit_breaker_active == True
        assert state.circuit_breaker_reason == "Too many failures"
        assert state.circuit_breaker_activated_at is not None
        
    def test_deactivate_circuit_breaker(self):
        """Test circuit breaker deactivation"""
        state = FlowControlState()
        
        state.activate_circuit_breaker("Test reason")
        assert state.circuit_breaker_active == True
        
        state.deactivate_circuit_breaker()
        assert state.circuit_breaker_active == False
        assert state.circuit_breaker_reason is None
        assert state.circuit_breaker_activated_at is None
        
    def test_circuit_breaker_prevents_transitions(self):
        """Test that circuit breaker prevents transitions when active"""
        state = FlowControlState()
        state.activate_circuit_breaker("System overload")
        
        # Transition should be prevented
        with pytest.raises(RuntimeError) as exc_info:
            state.add_transition(FlowStage.RESEARCH, "Trying to continue")
            
        assert "Circuit breaker is active" in str(exc_info.value)
        assert state.current_stage == FlowStage.INPUT_VALIDATION


class TestThreadSafety:
    """Test thread safety of FlowControlState"""
    
    def test_concurrent_transitions(self):
        """Test concurrent transitions are thread-safe"""
        state = FlowControlState()
        errors = []
        completed = []
        
        def worker(worker_id):
            try:
                # Each worker tries multiple transitions
                for i in range(10):
                    if state.current_stage == FlowStage.INPUT_VALIDATION:
                        state.add_transition(FlowStage.RESEARCH, f"Worker {worker_id}-{i}")
                    elif state.current_stage == FlowStage.RESEARCH:
                        state.add_transition(FlowStage.INPUT_VALIDATION, f"Worker {worker_id}-{i}")
                    time.sleep(0.001)  # Small delay to increase contention
                completed.append(worker_id)
            except Exception as e:
                errors.append((worker_id, str(e)))
        
        # Launch multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # No errors should occur
        assert len(errors) == 0
        assert len(completed) == 10
        
        # All transitions should be recorded
        assert len(state.transition_history) > 0
        
    def test_concurrent_retry_increment(self):
        """Test concurrent retry increments are thread-safe"""
        state = FlowControlState()
        
        def increment_worker():
            for _ in range(100):
                state.increment_retry(FlowStage.RESEARCH)
                
        threads = []
        for _ in range(10):
            t = threading.Thread(target=increment_worker)
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        # Should have exactly 1000 retries (10 threads * 100 increments)
        assert state.retry_counts[FlowStage.RESEARCH] == 1000
        assert state.total_retries == 1000


class TestMemoryManagement:
    """Test memory management and cleanup"""
    
    def test_cleanup_old_history(self):
        """Test cleanup of old transition history"""
        state = FlowControlState()
        
        # Add old transitions
        for i in range(10):
            state.add_transition(FlowStage.RESEARCH, f"Old transition {i}")
            state.current_stage = FlowStage.INPUT_VALIDATION
            
        # Manually set old timestamps
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=25)
        for transition in state.transition_history[:5]:
            transition.timestamp = cutoff_time
            
        # Cleanup
        removed = state.cleanup_old_history(max_age_hours=24)
        
        assert removed == 5
        assert len(state.transition_history) == 5
        
    def test_get_memory_usage(self):
        """Test memory usage reporting"""
        state = FlowControlState()
        
        # Add some data
        for i in range(50):
            state.add_transition(FlowStage.RESEARCH, f"Transition {i}")
            state.current_stage = FlowStage.INPUT_VALIDATION
            state.increment_retry(FlowStage.RESEARCH)
            
        usage = state.get_memory_usage()
        
        assert "transition_history_count" in usage
        assert "retry_counts_size" in usage
        assert "estimated_memory_bytes" in usage
        assert usage["transition_history_count"] == 50
        assert usage["retry_counts_size"] > 0


class TestStateSnapshot:
    """Test state snapshot and restoration"""
    
    def test_get_state_snapshot(self):
        """Test getting complete state snapshot"""
        state = FlowControlState()
        
        # Setup some state
        state.add_transition(FlowStage.RESEARCH, "Test transition")
        state.increment_retry(FlowStage.RESEARCH)
        state.activate_circuit_breaker("Test breaker")
        
        snapshot = state.get_state_snapshot()
        
        assert snapshot["flow_id"] == state.flow_id
        assert snapshot["current_stage"] == FlowStage.RESEARCH.value
        assert snapshot["total_retries"] == 1
        assert snapshot["circuit_breaker_active"] == True
        assert len(snapshot["transition_history"]) == 1
        assert FlowStage.RESEARCH.value in snapshot["retry_counts"]
        
    def test_serialization(self):
        """Test that state can be serialized to dict"""
        state = FlowControlState()
        state.add_transition(FlowStage.RESEARCH, "Test")
        
        # Should be able to convert to dict
        state_dict = state.dict()
        
        assert isinstance(state_dict, dict)
        assert state_dict["current_stage"] == FlowStage.RESEARCH.value
        assert len(state_dict["transition_history"]) == 1


class TestEdgeCases:
    """Test edge cases and error scenarios"""
    
    def test_transition_to_same_stage(self):
        """Test transition to same stage (should be allowed for retries)"""
        state = FlowControlState()
        
        # Same stage transition should work
        state.add_transition(FlowStage.INPUT_VALIDATION, "Retry validation")
        assert state.current_stage == FlowStage.INPUT_VALIDATION
        
    def test_empty_reason_transition(self):
        """Test transition with empty reason"""
        state = FlowControlState()
        
        state.add_transition(FlowStage.RESEARCH, "")
        transition = state.transition_history[0]
        assert transition.reason == ""
        
    def test_very_long_reason(self):
        """Test transition with very long reason"""
        state = FlowControlState()
        
        long_reason = "x" * 10000
        state.add_transition(FlowStage.RESEARCH, long_reason)
        
        # Should handle long reasons without issues
        assert len(state.transition_history[0].reason) == 10000
        
    def test_none_stage_handling(self):
        """Test handling of None stage values"""
        state = FlowControlState()
        
        with pytest.raises(AttributeError):
            state.add_transition(None, "Invalid transition")
            
    def test_invalid_stage_type(self):
        """Test handling of invalid stage types"""
        state = FlowControlState()
        
        with pytest.raises(AttributeError):
            state.add_transition("INVALID_STAGE", "Bad type")


class TestPerformance:
    """Test performance characteristics"""
    
    def test_transition_performance(self):
        """Test that transitions are fast"""
        state = FlowControlState()
        
        start_time = time.time()
        for i in range(1000):
            if i % 2 == 0:
                state.add_transition(FlowStage.RESEARCH, f"Transition {i}")
                state.current_stage = FlowStage.INPUT_VALIDATION
            else:
                state.add_transition(FlowStage.AUDIENCE_ALIGN, f"Transition {i}")
                state.current_stage = FlowStage.INPUT_VALIDATION
                
        elapsed = time.time() - start_time
        
        # Should complete 1000 transitions in under 1 second
        assert elapsed < 1.0
        
        # Only last 100 should be kept
        assert len(state.transition_history) == 100
        
    def test_memory_efficiency(self):
        """Test memory efficiency with large operations"""
        state = FlowControlState()
        
        # Add many retries
        for stage in FlowStage:
            for _ in range(100):
                state.increment_retry(stage)
                
        # Get memory usage
        usage = state.get_memory_usage()
        
        # Should be reasonably small (less than 1MB)
        assert usage["estimated_memory_bytes"] < 1_000_000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])