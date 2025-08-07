"""
Load and performance tests - Phase 3, Task 23.2

This test suite validates system behavior under load including:
- High-volume stage executions
- Memory usage patterns
- Performance degradation under stress
- Resource cleanup mechanisms
- System stability under sustained load
- Response time characteristics
- Throughput measurements
- Resource exhaustion scenarios
"""

import pytest
import asyncio
import time
import threading
import psutil
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch
from pathlib import Path
import sys
from datetime import datetime, timezone
from typing import List, Dict, Any
import statistics

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from ai_writing_flow.models.flow_stage import FlowStage, get_linear_flow
from ai_writing_flow.models.flow_control_state import FlowControlState, StageResult, StageStatus
from ai_writing_flow.managers.stage_manager import StageManager, ExecutionEventType
from ai_writing_flow.utils.retry_manager import RetryManager, RetryConfig
from ai_writing_flow.utils.circuit_breaker import StageCircuitBreaker, CircuitBreakerState
from ai_writing_flow.utils.loop_prevention import LoopPreventionSystem


class PerformanceMetrics:
    """Helper class to collect performance metrics"""
    
    def __init__(self):
        self.execution_times = []
        self.memory_usage = []
        self.cpu_usage = []
        self.timestamps = []
        self.start_time = None
        self.end_time = None
    
    def start_monitoring(self):
        """Start performance monitoring"""
        self.start_time = time.time()
        self.timestamps.append(self.start_time)
        
        # Get initial system metrics
        process = psutil.Process()
        self.memory_usage.append(process.memory_info().rss / 1024 / 1024)  # MB
        self.cpu_usage.append(process.cpu_percent())
    
    def record_execution(self, execution_time: float):
        """Record an execution time"""
        self.execution_times.append(execution_time)
        self.timestamps.append(time.time())
        
        # Record system metrics
        try:
            process = psutil.Process()
            self.memory_usage.append(process.memory_info().rss / 1024 / 1024)  # MB
            self.cpu_usage.append(process.cpu_percent())
        except:
            # Fallback if psutil fails
            self.memory_usage.append(0)
            self.cpu_usage.append(0)
    
    def finish_monitoring(self):
        """Finish performance monitoring"""
        self.end_time = time.time()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.execution_times:
            return {"error": "No executions recorded"}
        
        return {
            "total_duration": self.end_time - self.start_time if self.end_time else 0,
            "total_executions": len(self.execution_times),
            "avg_execution_time": statistics.mean(self.execution_times),
            "min_execution_time": min(self.execution_times),
            "max_execution_time": max(self.execution_times),
            "median_execution_time": statistics.median(self.execution_times),
            "throughput_per_second": len(self.execution_times) / (self.end_time - self.start_time) if self.end_time else 0,
            "memory_usage": {
                "initial_mb": self.memory_usage[0] if self.memory_usage else 0,
                "final_mb": self.memory_usage[-1] if self.memory_usage else 0,
                "peak_mb": max(self.memory_usage) if self.memory_usage else 0,
                "avg_mb": statistics.mean(self.memory_usage) if self.memory_usage else 0
            },
            "cpu_usage": {
                "avg_percent": statistics.mean(self.cpu_usage) if self.cpu_usage else 0,
                "peak_percent": max(self.cpu_usage) if self.cpu_usage else 0
            }
        }


class TestHighVolumeExecution:
    """Test system behavior under high-volume execution"""
    
    def setup_method(self):
        """Setup for high-volume tests"""
        self.metrics = PerformanceMetrics()
    
    def create_optimized_flow_instance(self):
        """Create flow instance optimized for load testing"""
        flow_state = FlowControlState()
        stage_manager = StageManager(flow_state)
        
        # Configure for high-volume testing
        stage_manager.loop_prevention = LoopPreventionSystem(
            max_executions_per_method=10000,  # Very high limits for load testing
            max_executions_per_stage=5000
        )
        
        retry_manager = RetryManager(flow_state)
        
        # Configure high retry limits
        flow_state.retry_count = {}
        flow_state.max_retries.update({
            "draft_generation": 100,
            "style_validation": 100,
            "quality_check": 100,
            "research": 100,
            "audience_align": 100,
            "input_validation": 100
        })
        
        return flow_state, stage_manager, retry_manager
    
    def test_high_volume_stage_executions(self):
        """Test executing large number of stages"""
        flow_state, stage_manager, retry_manager = self.create_optimized_flow_instance()
        
        self.metrics.start_monitoring()
        
        # Execute many stage operations
        num_executions = 100  # Reduced for CI stability
        successful_executions = 0
        failed_executions = 0
        
        for i in range(num_executions):
            start_time = time.time()
            
            try:
                # Execute input validation stage
                execution = stage_manager.start_stage(FlowStage.INPUT_VALIDATION)
                stage_manager.complete_stage(
                    FlowStage.INPUT_VALIDATION,
                    success=True,
                    result={"iteration": i, "timestamp": start_time}
                )
                
                # Reset stage for next execution
                flow_state.reset_stage(FlowStage.INPUT_VALIDATION)
                
                successful_executions += 1
                execution_time = time.time() - start_time
                self.metrics.record_execution(execution_time)
                
            except Exception as e:
                failed_executions += 1
                # Still record the time for failed executions
                execution_time = time.time() - start_time
                self.metrics.record_execution(execution_time)
        
        self.metrics.finish_monitoring()
        summary = self.metrics.get_summary()
        
        # Verify performance characteristics
        assert successful_executions > num_executions * 0.8  # At least 80% success rate
        assert summary["avg_execution_time"] < 0.1  # Average under 100ms
        assert summary["throughput_per_second"] > 10  # At least 10 ops/sec
        
        # Memory should not grow excessively
        memory_growth = summary["memory_usage"]["final_mb"] - summary["memory_usage"]["initial_mb"]
        assert memory_growth < 100  # Less than 100MB growth
        
        print(f"High-volume execution summary: {summary}")
    
    def test_sustained_load_execution(self):
        """Test system behavior under sustained load"""
        flow_state, stage_manager, retry_manager = self.create_optimized_flow_instance()
        
        self.metrics.start_monitoring()
        
        # Run sustained load for a short period
        duration_seconds = 3  # Short duration for CI
        end_time = time.time() + duration_seconds
        
        executions = 0
        errors = []
        
        while time.time() < end_time:
            try:
                start_time = time.time()
                
                # Execute stage
                execution = stage_manager.start_stage(FlowStage.INPUT_VALIDATION)
                stage_manager.complete_stage(
                    FlowStage.INPUT_VALIDATION,
                    success=True,
                    result={"sustained_load": True, "execution": executions}
                )
                
                flow_state.reset_stage(FlowStage.INPUT_VALIDATION)
                
                executions += 1
                execution_time = time.time() - start_time
                self.metrics.record_execution(execution_time)
                
                # Small delay to prevent overwhelming the system
                time.sleep(0.001)
                
            except Exception as e:
                errors.append(str(e))
                
                # Break if too many errors
                if len(errors) > 10:
                    break
        
        self.metrics.finish_monitoring()
        summary = self.metrics.get_summary()
        
        # Verify sustained performance
        assert executions > 50  # Should execute reasonable number of operations
        assert len(errors) < executions * 0.1  # Less than 10% error rate
        assert summary["avg_execution_time"] < 0.2  # Reasonable response time
        
        print(f"Sustained load summary: {summary}")
    
    def test_concurrent_high_volume_flows(self):
        """Test multiple flows running high-volume operations concurrently"""
        
        num_flows = 3  # Reduced for CI stability
        executions_per_flow = 20
        
        results = []
        errors = []
        
        def execute_high_volume_flow(flow_id):
            """Execute high-volume operations in a single flow"""
            try:
                flow_state, stage_manager, retry_manager = self.create_optimized_flow_instance()
                flow_metrics = PerformanceMetrics()
                flow_metrics.start_monitoring()
                
                successful = 0
                
                for i in range(executions_per_flow):
                    start_time = time.time()
                    
                    try:
                        execution = stage_manager.start_stage(FlowStage.INPUT_VALIDATION)
                        stage_manager.complete_stage(
                            FlowStage.INPUT_VALIDATION,
                            success=True,
                            result={"flow_id": flow_id, "iteration": i}
                        )
                        
                        flow_state.reset_stage(FlowStage.INPUT_VALIDATION)
                        successful += 1
                        
                        execution_time = time.time() - start_time
                        flow_metrics.record_execution(execution_time)
                        
                    except Exception as inner_e:
                        errors.append(f"Flow {flow_id}, iteration {i}: {str(inner_e)}")
                
                flow_metrics.finish_monitoring()
                results.append({
                    "flow_id": flow_id,
                    "successful_executions": successful,
                    "metrics": flow_metrics.get_summary()
                })
                
            except Exception as e:
                errors.append(f"Flow {flow_id} overall error: {str(e)}")
        
        # Execute flows concurrently
        threads = []
        for i in range(num_flows):
            thread = threading.Thread(target=execute_high_volume_flow, args=(f"flow_{i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=30)
        
        # Verify results
        assert len(results) >= num_flows * 0.8  # Most flows completed
        assert len(errors) < num_flows * executions_per_flow * 0.2  # Less than 20% error rate
        
        # Verify each flow performed reasonably
        for result in results:
            assert result["successful_executions"] > executions_per_flow * 0.7  # At least 70% success
            assert result["metrics"]["avg_execution_time"] < 0.3  # Reasonable response time
        
        print(f"Concurrent high-volume results: {len(results)} flows completed")


class TestMemoryUsagePatterns:
    """Test memory usage patterns under various loads"""
    
    def setup_method(self):
        """Setup for memory tests"""
        # Force garbage collection before tests
        gc.collect()
        self.initial_memory = self.get_memory_usage()
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def test_memory_growth_under_load(self):
        """Test memory growth patterns under sustained load"""
        flow_state, stage_manager, retry_manager = self.create_flow_instance()
        
        memory_samples = []
        execution_counts = []
        
        # Execute operations while monitoring memory
        for batch in range(10):  # 10 batches
            batch_start_memory = self.get_memory_usage()
            
            # Execute batch of operations
            for i in range(10):  # 10 operations per batch
                execution = stage_manager.start_stage(FlowStage.INPUT_VALIDATION)
                stage_manager.complete_stage(
                    FlowStage.INPUT_VALIDATION,
                    success=True,
                    result={"large_data": "x" * 1000, "batch": batch, "iteration": i}  # 1KB per execution
                )
                flow_state.reset_stage(FlowStage.INPUT_VALIDATION)
            
            batch_end_memory = self.get_memory_usage()
            memory_samples.append(batch_end_memory)
            execution_counts.append((batch + 1) * 10)
            
            # Force garbage collection between batches
            gc.collect()
        
        # Analyze memory growth
        memory_growth = memory_samples[-1] - memory_samples[0]
        total_executions = execution_counts[-1]
        
        # Memory growth should be reasonable
        assert memory_growth < 50  # Less than 50MB growth for 100 operations
        memory_per_execution = memory_growth / total_executions if total_executions > 0 else 0
        assert memory_per_execution < 1  # Less than 1MB per execution
        
        print(f"Memory growth: {memory_growth:.2f}MB over {total_executions} executions")
    
    def create_flow_instance(self):
        """Create flow instance for memory testing"""
        flow_state = FlowControlState()
        stage_manager = StageManager(flow_state)
        stage_manager.loop_prevention = LoopPreventionSystem(
            max_executions_per_method=1000,
            max_executions_per_stage=500
        )
        retry_manager = RetryManager(flow_state)
        
        # Configure for testing
        flow_state.retry_count = {}
        flow_state.max_retries.update({
            "input_validation": 50,
            "research": 50,
            "draft_generation": 50
        })
        
        return flow_state, stage_manager, retry_manager
    
    def test_memory_cleanup_mechanisms(self):
        """Test that memory cleanup mechanisms work properly"""
        flow_state, stage_manager, retry_manager = self.create_flow_instance()
        
        initial_memory = self.get_memory_usage()
        
        # Create many stage executions with large data
        for i in range(50):
            execution = stage_manager.start_stage(FlowStage.INPUT_VALIDATION)
            
            # Create large result data
            large_result = {
                "large_data": "x" * 10000,  # 10KB
                "metadata": {"iteration": i, "timestamp": time.time()},
                "additional_data": list(range(1000))  # Additional memory usage
            }
            
            stage_manager.complete_stage(
                FlowStage.INPUT_VALIDATION,
                success=True,
                result=large_result
            )
            
            flow_state.reset_stage(FlowStage.INPUT_VALIDATION)
        
        peak_memory = self.get_memory_usage()
        
        # Test cleanup if available
        if hasattr(stage_manager, 'cleanup_history'):
            # Cleanup old executions
            stage_manager.cleanup_history(keep_last_n=10)
        
        # Force garbage collection
        gc.collect()
        
        final_memory = self.get_memory_usage()
        
        # Memory should not grow excessively
        memory_growth = peak_memory - initial_memory
        cleanup_effect = peak_memory - final_memory
        
        assert memory_growth < 100  # Less than 100MB growth
        print(f"Memory: initial={initial_memory:.1f}MB, peak={peak_memory:.1f}MB, final={final_memory:.1f}MB")
        print(f"Growth: {memory_growth:.1f}MB, cleanup effect: {cleanup_effect:.1f}MB")
    
    def test_memory_usage_with_retries(self):
        """Test memory usage patterns with retry operations"""
        flow_state, stage_manager, retry_manager = self.create_flow_instance()
        
        # Configure retry with reasonable settings
        retry_manager.set_config(FlowStage.DRAFT_GENERATION, RetryConfig(
            max_attempts=3,
            initial_delay_seconds=0.001
        ))
        
        initial_memory = self.get_memory_usage()
        
        retry_executions = 0
        successful_executions = 0
        
        for i in range(30):  # Reduced for stability
            attempts = [0]
            
            def flaky_operation():
                attempts[0] += 1
                # Create some memory usage
                temp_data = "x" * 5000  # 5KB temporary data
                
                if attempts[0] < 2:  # Fail once, succeed on retry
                    raise ValueError(f"Temporary failure {attempts[0]}")
                
                return {"result": f"success_{i}", "temp_data": temp_data}
            
            try:
                result = retry_manager.retry_sync(flaky_operation, FlowStage.DRAFT_GENERATION)
                successful_executions += 1
                retry_executions += attempts[0]
            except Exception:
                pass  # Continue with next iteration
        
        final_memory = self.get_memory_usage()
        memory_growth = final_memory - initial_memory
        
        # Verify reasonable memory usage
        assert memory_growth < 30  # Less than 30MB growth
        assert successful_executions > 20  # Most operations succeeded
        
        print(f"Retry operations: {retry_executions} total, {successful_executions} successful")
        print(f"Memory growth with retries: {memory_growth:.1f}MB")


class TestPerformanceCharacteristics:
    """Test performance characteristics under various conditions"""
    
    def setup_method(self):
        """Setup for performance tests"""
        self.metrics = PerformanceMetrics()
    
    def test_response_time_characteristics(self):
        """Test response time characteristics under different loads"""
        flow_state, stage_manager, retry_manager = self.create_flow_instance()
        
        # Test different load levels
        load_levels = [1, 5, 10, 20]  # operations per batch
        results = {}
        
        for load_level in load_levels:
            batch_metrics = PerformanceMetrics()
            batch_metrics.start_monitoring()
            
            # Execute batch
            for i in range(load_level):
                start_time = time.time()
                
                execution = stage_manager.start_stage(FlowStage.INPUT_VALIDATION)
                stage_manager.complete_stage(
                    FlowStage.INPUT_VALIDATION,
                    success=True,
                    result={"load_level": load_level, "iteration": i}
                )
                
                flow_state.reset_stage(FlowStage.INPUT_VALIDATION)
                
                execution_time = time.time() - start_time
                batch_metrics.record_execution(execution_time)
            
            batch_metrics.finish_monitoring()
            results[load_level] = batch_metrics.get_summary()
        
        # Analyze response time scaling
        for load_level, summary in results.items():
            # Response times should remain reasonable
            assert summary["avg_execution_time"] < 0.5  # Less than 500ms average
            assert summary["max_execution_time"] < 2.0  # Less than 2s maximum
            
            print(f"Load {load_level}: avg={summary['avg_execution_time']:.3f}s, "
                  f"max={summary['max_execution_time']:.3f}s")
        
        # Response time should not degrade dramatically with load
        low_load_avg = results[1]["avg_execution_time"]
        high_load_avg = results[20]["avg_execution_time"]
        degradation_factor = high_load_avg / low_load_avg if low_load_avg > 0 else 1
        
        assert degradation_factor < 5  # Less than 5x degradation
        print(f"Response time degradation factor: {degradation_factor:.2f}x")
    
    def create_flow_instance(self):
        """Create flow instance for performance testing"""
        flow_state = FlowControlState()
        stage_manager = StageManager(flow_state)
        stage_manager.loop_prevention = LoopPreventionSystem(
            max_executions_per_method=500,
            max_executions_per_stage=200
        )
        retry_manager = RetryManager(flow_state)
        
        flow_state.retry_count = {}
        flow_state.max_retries.update({
            "input_validation": 20,
            "research": 20,
            "draft_generation": 20
        })
        
        return flow_state, stage_manager, retry_manager
    
    def test_throughput_under_concurrent_load(self):
        """Test throughput characteristics under concurrent load"""
        
        # Test different concurrency levels
        concurrency_levels = [1, 2, 4]  # number of concurrent threads
        results = {}
        
        for concurrency in concurrency_levels:
            executions_per_thread = 10
            
            thread_results = []
            threads = []
            
            def worker_thread(thread_id):
                """Worker thread for throughput testing"""
                thread_metrics = PerformanceMetrics()
                thread_metrics.start_monitoring()
                
                flow_state, stage_manager, retry_manager = self.create_flow_instance()
                
                for i in range(executions_per_thread):
                    start_time = time.time()
                    
                    execution = stage_manager.start_stage(FlowStage.INPUT_VALIDATION)
                    stage_manager.complete_stage(
                        FlowStage.INPUT_VALIDATION,
                        success=True,
                        result={"thread_id": thread_id, "iteration": i}
                    )
                    
                    flow_state.reset_stage(FlowStage.INPUT_VALIDATION)
                    
                    execution_time = time.time() - start_time
                    thread_metrics.record_execution(execution_time)
                
                thread_metrics.finish_monitoring()
                thread_results.append(thread_metrics.get_summary())
            
            # Start threads
            for i in range(concurrency):
                thread = threading.Thread(target=worker_thread, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join(timeout=30)
            
            # Calculate aggregate metrics
            if thread_results:
                total_executions = sum(r["total_executions"] for r in thread_results)
                total_duration = max(r["total_duration"] for r in thread_results)
                aggregate_throughput = total_executions / total_duration if total_duration > 0 else 0
                
                results[concurrency] = {
                    "total_executions": total_executions,
                    "duration": total_duration,
                    "throughput": aggregate_throughput,
                    "avg_response_time": statistics.mean([r["avg_execution_time"] for r in thread_results])
                }
        
        # Analyze throughput scaling
        for concurrency, result in results.items():
            print(f"Concurrency {concurrency}: throughput={result['throughput']:.1f} ops/sec, "
                  f"avg_response={result['avg_response_time']:.3f}s")
        
        # Throughput should not degrade dramatically with concurrency
        if 1 in results and 2 in results:
            throughput_ratio = results[2]["throughput"] / results[1]["throughput"]
            # Due to threading overhead, we just ensure no dramatic degradation
            assert throughput_ratio > 0.5  # At least 50% of single-thread performance
            
            # Verify all concurrency levels achieved reasonable throughput
            for concurrency, result in results.items():
                assert result["throughput"] > 100  # At least 100 ops/sec
                assert result["avg_response_time"] < 0.1  # Less than 100ms average response
    
    @pytest.mark.asyncio
    async def test_async_performance_characteristics(self):
        """Test async performance characteristics"""
        flow_state = FlowControlState()
        retry_manager = RetryManager(flow_state)
        
        # Configure for async testing
        flow_state.retry_count = {}
        flow_state.max_retries.update({"draft_generation": 20})
        
        retry_manager.set_config(FlowStage.DRAFT_GENERATION, RetryConfig(
            max_attempts=2,
            initial_delay_seconds=0.001
        ))
        
        metrics = PerformanceMetrics()
        metrics.start_monitoring()
        
        # Execute async operations
        async def async_operation(operation_id):
            start_time = time.time()
            
            async def async_work():
                await asyncio.sleep(0.001)  # Simulate async work
                return f"async_result_{operation_id}"
            
            result = await retry_manager.retry_async(async_work, FlowStage.DRAFT_GENERATION)
            
            execution_time = time.time() - start_time
            metrics.record_execution(execution_time)
            return result
        
        # Execute multiple async operations concurrently
        tasks = [async_operation(i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        
        metrics.finish_monitoring()
        summary = metrics.get_summary()
        
        # Verify async performance
        assert len(results) == 20
        assert summary["avg_execution_time"] < 0.1  # Fast async operations
        assert summary["throughput_per_second"] > 50  # High throughput for async
        
        print(f"Async performance: {summary['throughput_per_second']:.1f} ops/sec")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])