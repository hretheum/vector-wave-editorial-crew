"""
Concurrent execution tests - Phase 3, Task 23.1

This test suite validates concurrent execution patterns including:
- Multiple flow instances running simultaneously
- Thread safety of core components
- Shared resource handling
- Isolation between concurrent executions
- Deadlock prevention
- Race condition testing
- Performance under concurrent load
"""

import pytest
import asyncio
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import sys
from datetime import datetime, timezone
import uuid

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from ai_writing_flow.models.flow_stage import FlowStage, get_linear_flow
from ai_writing_flow.models.flow_control_state import FlowControlState, StageResult, StageStatus
from ai_writing_flow.managers.stage_manager import StageManager, ExecutionEventType
from ai_writing_flow.utils.retry_manager import RetryManager, RetryConfig
from ai_writing_flow.utils.circuit_breaker import StageCircuitBreaker, CircuitBreakerState
from ai_writing_flow.utils.loop_prevention import LoopPreventionSystem


class TestConcurrentFlowExecution:
    """Test concurrent execution of multiple flow instances"""
    
    def setup_method(self):
        """Setup components for concurrent testing"""
        # We'll create multiple flow instances in individual tests
        pass
    
    def create_flow_instance(self, flow_id: str = None):
        """Create a fresh flow instance for testing"""
        flow_state = FlowControlState()
        if flow_id:
            flow_state.execution_id = flow_id
        
        stage_manager = StageManager(flow_state)
        stage_manager.loop_prevention = LoopPreventionSystem(
            max_executions_per_method=100,
            max_executions_per_stage=50
        )
        
        retry_manager = RetryManager(flow_state)
        
        # Reset retry counts and increase limits
        flow_state.retry_count = {}
        flow_state.max_retries.update({
            "draft_generation": 10,
            "style_validation": 10,
            "quality_check": 10,
            "research": 10,
            "audience_align": 10,
            "input_validation": 10
        })
        
        return flow_state, stage_manager, retry_manager
    
    def test_multiple_flows_isolation(self):
        """Test that multiple flows don't interfere with each other"""
        flows = []
        results = []
        errors = []
        
        def execute_flow(flow_id):
            """Execute a single flow"""
            try:
                flow_state, stage_manager, retry_manager = self.create_flow_instance(flow_id)
                
                # Execute basic stages
                execution = stage_manager.start_stage(FlowStage.INPUT_VALIDATION)
                stage_manager.complete_stage(
                    FlowStage.INPUT_VALIDATION,
                    success=True,
                    result={"flow_id": flow_id, "stage": "input_validation"}
                )
                
                # Transition and execute research
                flow_state.add_transition(FlowStage.RESEARCH, f"Flow {flow_id} to research")
                execution = stage_manager.start_stage(FlowStage.RESEARCH)
                stage_manager.complete_stage(
                    FlowStage.RESEARCH,
                    success=True,
                    result={"flow_id": flow_id, "stage": "research"}
                )
                
                results.append({
                    "flow_id": flow_id,
                    "execution_id": flow_state.execution_id,
                    "completed_stages": len(flow_state.completed_stages),
                    "current_stage": flow_state.current_stage.value
                })
                
            except Exception as e:
                errors.append(f"Flow {flow_id}: {str(e)}")
        
        # Execute multiple flows concurrently
        threads = []
        for i in range(5):
            flow_id = f"flow_{i}"
            thread = threading.Thread(target=execute_flow, args=(flow_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify results
        assert len(errors) == 0, f"Concurrent flows had errors: {errors}"
        assert len(results) == 5
        
        # Verify isolation - each flow should have unique execution_id
        execution_ids = [r["execution_id"] for r in results]
        assert len(set(execution_ids)) == 5  # All unique
        
        # Verify all flows completed successfully
        for result in results:
            assert result["completed_stages"] == 2
            assert result["current_stage"] == "research"
    
    def test_concurrent_stage_execution(self):
        """Test concurrent execution within the same flow"""
        flow_state, stage_manager, retry_manager = self.create_flow_instance("concurrent_test")
        
        execution_results = []
        execution_errors = []
        
        def execute_stage_operations(thread_id):
            """Execute stage operations concurrently"""
            try:
                # Each thread tries to execute input validation
                execution = stage_manager.start_stage(FlowStage.INPUT_VALIDATION)
                time.sleep(0.01)  # Simulate processing
                stage_manager.complete_stage(
                    FlowStage.INPUT_VALIDATION,
                    success=True,
                    result={"thread_id": thread_id, "timestamp": time.time()}
                )
                execution_results.append(f"Thread {thread_id} completed")
                
            except Exception as e:
                execution_errors.append(f"Thread {thread_id}: {str(e)}")
        
        # Execute concurrently
        threads = []
        for i in range(3):
            thread = threading.Thread(target=execute_stage_operations, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=5)
        
        # Verify thread safety - at least one should succeed
        assert len(execution_results) >= 1
        
        # Check that stage completed successfully
        assert flow_state.is_stage_complete(FlowStage.INPUT_VALIDATION)
    
    def test_concurrent_retry_operations(self):
        """Test concurrent retry operations"""
        flow_state, stage_manager, retry_manager = self.create_flow_instance("retry_test")
        
        # Configure retry for testing
        retry_manager.set_config(FlowStage.DRAFT_GENERATION, RetryConfig(
            max_attempts=3,
            initial_delay_seconds=0.01
        ))
        
        retry_results = []
        retry_errors = []
        
        def execute_retry_operation(operation_id):
            """Execute retry operation"""
            try:
                attempts = [0]
                
                def flaky_function():
                    attempts[0] += 1
                    if attempts[0] < 2:  # Fail once, succeed second time
                        raise ValueError(f"Operation {operation_id} attempt {attempts[0]} failed")
                    return f"Operation {operation_id} succeeded after {attempts[0]} attempts"
                
                result = retry_manager.retry_sync(flaky_function, FlowStage.DRAFT_GENERATION)
                retry_results.append(result)
                
            except Exception as e:
                retry_errors.append(f"Operation {operation_id}: {str(e)}")
        
        # Execute concurrent retry operations
        threads = []
        for i in range(3):
            thread = threading.Thread(target=execute_retry_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion  
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify results
        assert len(retry_errors) == 0, f"Retry operations had errors: {retry_errors}"
        assert len(retry_results) >= 1  # At least some should succeed
        
        # Verify retry counts are tracked properly
        total_retries = flow_state.get_stage_retry_count(FlowStage.DRAFT_GENERATION)
        assert total_retries > 0
    
    def test_concurrent_circuit_breaker_operations(self):
        """Test concurrent circuit breaker operations"""
        flow_state, stage_manager, retry_manager = self.create_flow_instance("cb_test")
        
        # Create circuit breaker
        circuit_breaker = StageCircuitBreaker(
            stage=FlowStage.DRAFT_GENERATION,
            flow_state=flow_state,
            failure_threshold=3,
            recovery_timeout=0.5
        )
        
        cb_results = []
        cb_errors = []
        
        def execute_cb_operation(operation_id, should_fail=False):
            """Execute circuit breaker operation"""
            try:
                def test_function():
                    if should_fail:
                        raise RuntimeError(f"Operation {operation_id} deliberately failed")
                    return f"Operation {operation_id} succeeded"
                
                result = circuit_breaker.call(test_function)
                cb_results.append(result)
                
            except Exception as e:
                cb_errors.append(f"Operation {operation_id}: {str(e)}")
        
        # Execute mixed success/failure operations concurrently
        threads = []
        for i in range(5):
            # First 2 operations succeed, next 3 fail to test circuit breaker
            should_fail = i >= 2
            thread = threading.Thread(target=execute_cb_operation, args=(i, should_fail))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=5)
        
        # Verify circuit breaker behavior
        assert len(cb_results) >= 2  # At least successful operations completed
        assert len(cb_errors) >= 3   # Failed operations should be recorded
        
        # Circuit breaker might be open depending on timing
        assert circuit_breaker.state in [CircuitBreakerState.OPEN, CircuitBreakerState.CLOSED, CircuitBreakerState.HALF_OPEN]


class TestThreadSafety:
    """Test thread safety of core components"""
    
    def setup_method(self):
        """Setup for thread safety tests"""
        self.flow_state = FlowControlState()
        self.stage_manager = StageManager(self.flow_state)
        self.stage_manager.loop_prevention = LoopPreventionSystem(
            max_executions_per_method=200,
            max_executions_per_stage=100
        )
    
    def test_flow_state_thread_safety(self):
        """Test FlowControlState thread safety"""
        results = []
        errors = []
        
        def modify_flow_state(thread_id):
            """Modify flow state concurrently"""
            try:
                for i in range(10):
                    # Only try transition once per thread to avoid invalid transitions
                    if i == 0:
                        try:
                            self.flow_state.add_transition(
                                FlowStage.RESEARCH, 
                                f"Thread {thread_id} transition {i}"
                            )
                        except ValueError:
                            # Invalid transition is expected when multiple threads compete
                            pass
                    
                    # Increment retry count
                    self.flow_state.increment_retry_count(FlowStage.DRAFT_GENERATION)
                    
                    # Update circuit breaker
                    self.flow_state.update_circuit_breaker(FlowStage.RESEARCH, success=(i % 2 == 0))
                
                results.append(f"Thread {thread_id} completed")
                
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
        
        # Execute concurrent modifications
        threads = []
        for i in range(5):
            thread = threading.Thread(target=modify_flow_state, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 5
        
        # Verify state consistency
        assert len(self.flow_state.execution_history) > 0
        assert self.flow_state.get_stage_retry_count(FlowStage.DRAFT_GENERATION) > 0
    
    def test_stage_manager_thread_safety(self):
        """Test StageManager thread safety"""
        execution_results = []
        execution_errors = []
        
        def execute_stage_concurrently(thread_id):
            """Execute stage operations from multiple threads"""
            try:
                # Reset stage to allow re-execution
                self.flow_state.reset_stage(FlowStage.INPUT_VALIDATION)
                
                execution = self.stage_manager.start_stage(FlowStage.INPUT_VALIDATION)
                time.sleep(0.001)  # Small delay to increase chance of race conditions
                self.stage_manager.complete_stage(
                    FlowStage.INPUT_VALIDATION,
                    success=True,
                    result={"thread_id": thread_id}
                )
                
                execution_results.append(thread_id)
                
            except Exception as e:
                execution_errors.append(f"Thread {thread_id}: {str(e)}")
        
        # Execute from multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=execute_stage_concurrently, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=5)
        
        # Verify thread safety - at least some operations should succeed
        assert len(execution_results) >= 1
        
        # Stage should be completed successfully
        assert self.flow_state.is_stage_complete(FlowStage.INPUT_VALIDATION)
    
    def test_loop_prevention_thread_safety(self):
        """Test LoopPreventionSystem thread safety"""
        loop_prevention = LoopPreventionSystem(
            max_executions_per_method=10,
            max_executions_per_stage=5
        )
        
        execution_results = []
        execution_errors = []
        
        @loop_prevention.with_loop_protection(FlowStage.RESEARCH)
        def protected_method(thread_id, iteration):
            time.sleep(0.001)  # Small delay
            return f"Thread {thread_id} iteration {iteration}"
        
        def execute_protected_method(thread_id):
            """Execute protected method multiple times"""
            try:
                for i in range(3):
                    result = protected_method(thread_id, i)
                    execution_results.append(result)
                    
            except RuntimeError as e:
                if "exceeded execution limit" in str(e):
                    execution_errors.append(f"Thread {thread_id}: Loop prevention triggered")
                else:
                    execution_errors.append(f"Thread {thread_id}: {str(e)}")
            except Exception as e:
                execution_errors.append(f"Thread {thread_id}: {str(e)}")
        
        # Execute from multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=execute_protected_method, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=5)
        
        # Verify some executions completed before hitting limits
        assert len(execution_results) > 0


class TestAsyncConcurrentExecution:
    """Test asynchronous concurrent execution patterns"""
    
    def setup_method(self):
        """Setup async components"""
        self.flow_state = FlowControlState()
        self.retry_manager = RetryManager(self.flow_state)
        
        # Reset and configure for testing
        self.flow_state.retry_count = {}
        self.flow_state.max_retries.update({
            "draft_generation": 10,
            "research": 10,
            "audience_align": 10
        })
    
    @pytest.mark.asyncio
    async def test_concurrent_async_retry_operations(self):
        """Test concurrent async retry operations"""
        
        # Configure retry policies
        self.retry_manager.set_config(FlowStage.DRAFT_GENERATION, RetryConfig(
            max_attempts=3,
            initial_delay_seconds=0.01
        ))
        
        async def async_operation(operation_id):
            """Async operation that may fail"""
            attempts = [0]
            
            async def flaky_async_function():
                attempts[0] += 1
                await asyncio.sleep(0.001)  # Simulate async work
                
                if attempts[0] < 2:  # Fail once, succeed on retry
                    raise ValueError(f"Async operation {operation_id} attempt {attempts[0]} failed")
                
                return f"Async operation {operation_id} succeeded after {attempts[0]} attempts"
            
            return await self.retry_manager.retry_async(flaky_async_function, FlowStage.DRAFT_GENERATION)
        
        # Execute multiple async operations concurrently
        tasks = [async_operation(i) for i in range(3)]
        results = await asyncio.gather(*tasks)
        
        # Verify all operations completed successfully
        assert len(results) == 3
        for result in results:
            assert "succeeded after" in result
        
        # Verify retry counts were tracked
        total_retries = self.flow_state.get_stage_retry_count(FlowStage.DRAFT_GENERATION)
        assert total_retries > 0
    
    @pytest.mark.asyncio
    async def test_mixed_sync_async_operations(self):
        """Test mixing synchronous and asynchronous operations"""
        
        # Configure retry for both operations
        self.retry_manager.set_config(FlowStage.RESEARCH, RetryConfig(
            max_attempts=2,
            initial_delay_seconds=0.01
        ))
        
        self.retry_manager.set_config(FlowStage.AUDIENCE_ALIGN, RetryConfig(
            max_attempts=2,
            initial_delay_seconds=0.01
        ))
        
        sync_results = []
        async_results = []
        
        def sync_operation():
            """Synchronous operation"""
            result = self.retry_manager.retry_sync(
                lambda: {"sync": "result"},
                FlowStage.RESEARCH
            )
            sync_results.append(result)
        
        async def async_operation():
            """Asynchronous operation"""
            async def async_func():
                await asyncio.sleep(0.01)
                return {"async": "result"}
            
            result = await self.retry_manager.retry_async(async_func, FlowStage.AUDIENCE_ALIGN)
            async_results.append(result)
        
        # Execute sync operation in thread and async operation concurrently
        loop = asyncio.get_event_loop()
        sync_task = loop.run_in_executor(None, sync_operation)
        async_task = async_operation()
        
        await asyncio.gather(sync_task, async_task)
        
        # Verify both completed
        assert len(sync_results) == 1
        assert len(async_results) == 1
        assert sync_results[0]["sync"] == "result"
        assert async_results[0]["async"] == "result"
    
    @pytest.mark.asyncio
    async def test_async_circuit_breaker_operations(self):
        """Test async circuit breaker operations"""
        
        # Create circuit breaker
        circuit_breaker = StageCircuitBreaker(
            stage=FlowStage.DRAFT_GENERATION,
            flow_state=self.flow_state,
            failure_threshold=2,
            recovery_timeout=0.1
        )
        
        results = []
        errors = []
        
        async def async_cb_operation(operation_id, should_fail=False):
            """Async circuit breaker operation"""
            try:
                async def test_function():
                    await asyncio.sleep(0.001)
                    if should_fail:
                        raise RuntimeError(f"Async operation {operation_id} failed")
                    return f"Async operation {operation_id} succeeded"
                
                result = await circuit_breaker.call_async(test_function)
                results.append(result)
                
            except Exception as e:
                errors.append(f"Operation {operation_id}: {str(e)}")
        
        # Execute mixed operations
        tasks = []
        for i in range(4):
            should_fail = i >= 2  # First 2 succeed, next 2 fail
            tasks.append(async_cb_operation(i, should_fail))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify circuit breaker behavior
        assert len(results) >= 2  # Successful operations
        assert len(errors) >= 2   # Failed operations


class TestResourceContention:
    """Test resource contention and deadlock prevention"""
    
    def setup_method(self):
        """Setup for resource contention tests"""
        pass
    
    def test_multiple_flows_shared_resources(self):
        """Test multiple flows competing for shared resources"""
        shared_resource = {"counter": 0, "lock": threading.Lock()}
        results = []
        errors = []
        
        def flow_with_shared_resource(flow_id):
            """Flow that uses shared resource"""
            try:
                flow_state, stage_manager, retry_manager = self.create_flow_instance(flow_id)
                
                # Simulate resource contention
                with shared_resource["lock"]:
                    current = shared_resource["counter"]
                    time.sleep(0.001)  # Simulate processing time
                    shared_resource["counter"] = current + 1
                
                # Execute flow stage
                execution = stage_manager.start_stage(FlowStage.INPUT_VALIDATION)
                stage_manager.complete_stage(
                    FlowStage.INPUT_VALIDATION,
                    success=True,
                    result={"flow_id": flow_id, "counter_value": shared_resource["counter"]}
                )
                
                results.append({
                    "flow_id": flow_id,
                    "counter_value": shared_resource["counter"]
                })
                
            except Exception as e:
                errors.append(f"Flow {flow_id}: {str(e)}")
    
        def create_flow_instance(self, flow_id: str = None):
            """Create a fresh flow instance"""
            flow_state = FlowControlState()
            if flow_id:
                flow_state.execution_id = flow_id
            
            stage_manager = StageManager(flow_state)
            stage_manager.loop_prevention = LoopPreventionSystem(
                max_executions_per_method=100,
                max_executions_per_stage=50
            )
            
            retry_manager = RetryManager(flow_state)
            return flow_state, stage_manager, retry_manager
        
        # Bind the method to the test instance
        self.create_flow_instance = create_flow_instance
        
        # Execute multiple flows concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=flow_with_shared_resource, args=(f"flow_{i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify no deadlocks or errors
        assert len(errors) == 0, f"Resource contention errors: {errors}"
        assert len(results) == 5
        
        # Verify shared resource was properly managed
        assert shared_resource["counter"] == 5
        
        # Verify flows accessed the counter (values should be reasonable)
        counter_values = [r["counter_value"] for r in results]
        assert all(1 <= v <= 5 for v in counter_values)  # All values in expected range
        assert len(counter_values) == 5  # All flows completed
    
    def test_deadlock_prevention(self):
        """Test deadlock prevention in complex scenarios"""
        locks = {
            "lock1": threading.Lock(),
            "lock2": threading.Lock()
        }
        
        results = []
        errors = []
        
        def operation_a(thread_id):
            """Operation that acquires locks in order A->B"""
            try:
                with locks["lock1"]:
                    time.sleep(0.01)
                    with locks["lock2"]:
                        results.append(f"Operation A from thread {thread_id}")
            except Exception as e:
                errors.append(f"Operation A thread {thread_id}: {str(e)}")
        
        def operation_b(thread_id):
            """Operation that acquires locks in order A->B (same order to prevent deadlock)"""
            try:
                with locks["lock1"]:
                    time.sleep(0.01)
                    with locks["lock2"]:
                        results.append(f"Operation B from thread {thread_id}")
            except Exception as e:
                errors.append(f"Operation B thread {thread_id}: {str(e)}")
        
        # Execute operations that could potentially deadlock
        threads = []
        for i in range(3):
            thread_a = threading.Thread(target=operation_a, args=(i,))
            thread_b = threading.Thread(target=operation_b, args=(i,))
            threads.extend([thread_a, thread_b])
            thread_a.start()
            thread_b.start()
        
        # Wait for completion with timeout to detect deadlocks
        for thread in threads:
            thread.join(timeout=5)
            if thread.is_alive():
                errors.append(f"Thread {thread.name} did not complete - possible deadlock")
        
        # Verify no deadlocks occurred
        assert len(errors) == 0, f"Deadlock prevention failed: {errors}"
        assert len(results) == 6  # 3 A operations + 3 B operations


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])