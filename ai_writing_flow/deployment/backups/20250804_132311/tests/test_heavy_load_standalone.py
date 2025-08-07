#\!/usr/bin/env python
"""
Heavy Load Stress Testing for AI Writing Flow V2 - Standalone Version

This module provides comprehensive stress testing capabilities without external dependencies.
It creates realistic stress scenarios to test system limits, memory management, and recovery.

Test Categories:
1. Extreme Concurrent Load Testing (20+ concurrent operations)
2. Resource Exhaustion Testing (CPU, Memory, I/O saturation)  
3. Sustained Load Testing (extended periods, memory leak detection)
4. Breaking Point Detection (maximum capacity, failure thresholds)
5. Recovery Testing (system recovery after stress)

Key Features:
- No external dependencies (CrewAI-free)
- Real-time resource monitoring
- Automatic safety thresholds
- Comprehensive reporting
- Memory leak detection
- Circuit breaker simulation
"""

import pytest
import asyncio
import time
import psutil
import os
import sys
import threading
import gc
import statistics
import concurrent.futures
import multiprocessing
import logging
import json
from typing import Dict, List, Any, Optional, Tuple, Callable
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from contextlib import contextmanager
from collections import deque
import weakref
import random
import signal


# Configure logging for stress tests
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class StressTestResult:
    """Result of a stress test execution"""
    test_name: str
    success: bool
    duration_seconds: float
    max_concurrent_operations: int
    peak_memory_mb: float
    peak_cpu_percent: float
    total_operations: int
    successful_operations: int
    failed_operations: int
    throughput_ops_per_sec: float
    error_messages: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    breaking_point_reached: bool = False
    recovery_time_seconds: Optional[float] = None


@dataclass
class ResourceThresholds:
    """Safety thresholds for stress testing"""
    max_memory_mb: float = 1024.0  # 1GB memory limit
    max_cpu_percent: float = 90.0  # 90% CPU limit
    max_execution_time_seconds: float = 300.0  # 5 minutes max test time
    max_concurrent_operations: int = 50  # Maximum concurrent operations
    memory_growth_rate_mb_per_sec: float = 10.0  # Memory leak detection threshold


class MockAIWritingFlowV2:
    """Mock implementation of AI Writing Flow V2 for stress testing"""
    
    def __init__(self, processing_time_base: float = 0.1, failure_rate: float = 0.05):
        self.processing_time_base = processing_time_base
        self.failure_rate = failure_rate
        self.execution_count = 0
        self.lock = threading.Lock()
        
        # Simulate system components
        self.circuit_breaker_open = False
        self.circuit_breaker_failures = 0
        self.circuit_breaker_threshold = 5
        
        # Performance tracking
        self._execution_times = deque(maxlen=1000)
        self._memory_allocations = []
    
    def kickoff(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate flow execution with realistic processing characteristics"""
        
        with self.lock:
            self.execution_count += 1
            execution_id = self.execution_count
        
        start_time = time.time()
        
        try:
            # Simulate circuit breaker
            if self.circuit_breaker_open:
                raise RuntimeError("Circuit breaker is open - service unavailable")
            
            # Simulate variable processing time
            processing_time = self.processing_time_base + random.uniform(0, self.processing_time_base)
            
            # Simulate memory allocation during processing
            memory_allocation = bytearray(random.randint(100_000, 1_000_000))  # 100KB-1MB
            self._memory_allocations.append(memory_allocation)
            
            # Simulate CPU work
            for _ in range(int(processing_time * 10000)):
                _ = sum(range(10))
            
            time.sleep(processing_time * 0.5)  # I/O simulation
            
            # Simulate random failures
            if random.random() < self.failure_rate:
                self.circuit_breaker_failures += 1
                if self.circuit_breaker_failures >= self.circuit_breaker_threshold:
                    self.circuit_breaker_open = True
                    logger.warning(f"Circuit breaker opened after {self.circuit_breaker_failures} failures")
                raise RuntimeError(f"Simulated failure in operation {execution_id}")
            
            # Clean up memory allocation (simulate garbage collection)
            if len(self._memory_allocations) > 10:
                self._memory_allocations.pop(0)
            
            execution_time = time.time() - start_time
            self._execution_times.append(execution_time)
            
            # Reset circuit breaker on success
            if self.circuit_breaker_failures > 0:
                self.circuit_breaker_failures = max(0, self.circuit_breaker_failures - 1)
            
            return {
                "execution_id": execution_id,
                "success": True,
                "execution_time": execution_time,
                "current_stage": "completed",
                "agents_executed": ["research", "draft", "style", "quality"],
                "memory_used": len(memory_allocation)
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._execution_times.append(execution_time)
            raise
    
    def reset_circuit_breaker(self):
        """Reset circuit breaker for testing"""
        self.circuit_breaker_open = False
        self.circuit_breaker_failures = 0
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        with self.lock:
            if not self._execution_times:
                return {"avg_execution_time": 0, "total_executions": 0}
            
            return {
                "avg_execution_time": statistics.mean(self._execution_times),
                "min_execution_time": min(self._execution_times),
                "max_execution_time": max(self._execution_times),
                "total_executions": self.execution_count,
                "circuit_breaker_open": self.circuit_breaker_open,
                "circuit_breaker_failures": self.circuit_breaker_failures
            }


class SystemResourceMonitor:
    """Real-time system resource monitoring with safety thresholds"""
    
    def __init__(self, thresholds: ResourceThresholds):
        self.thresholds = thresholds
        self.start_time = time.time()
        self.process = psutil.Process()
        
        # Baseline measurements
        self.baseline_memory = self.process.memory_info().rss / 1024 / 1024
        self.baseline_cpu = 0.0
        
        # Monitoring data
        self.memory_samples = deque(maxlen=1000)
        self.cpu_samples = deque(maxlen=1000)
        self.active_operations = set()
        self.completed_operations = 0
        self.failed_operations = 0
        
        # Safety flags
        self.emergency_stop = False
        self.safety_violated = False
        self.violation_reason = ""
        
        # Background monitoring
        self._monitor_thread = None
        self._stop_monitoring = threading.Event()
        self._lock = threading.Lock()
    
    def start_monitoring(self):
        """Start background resource monitoring"""
        self._stop_monitoring.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("🔍 Resource monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        if self._monitor_thread:
            self._stop_monitoring.set()
            self._monitor_thread.join(timeout=5.0)
        logger.info("🛑 Resource monitoring stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while not self._stop_monitoring.is_set():
            try:
                # Sample system resources
                memory_mb = self.process.memory_info().rss / 1024 / 1024
                cpu_percent = self.process.cpu_percent()
                
                with self._lock:
                    self.memory_samples.append((time.time(), memory_mb))
                    self.cpu_samples.append((time.time(), cpu_percent))
                
                # Check safety thresholds
                self._check_safety_thresholds(memory_mb, cpu_percent)
                
                # Sleep before next sample
                time.sleep(0.5)  # Sample every 500ms
                
            except Exception as e:
                logger.warning(f"⚠️ Monitoring error: {e}")
                time.sleep(1.0)
    
    def _check_safety_thresholds(self, memory_mb: float, cpu_percent: float):
        """Check if safety thresholds are violated"""
        if self.safety_violated:
            return
        
        with self._lock:
            # Memory threshold check
            if memory_mb > self.thresholds.max_memory_mb:
                self.safety_violated = True
                self.violation_reason = f"Memory exceeded {self.thresholds.max_memory_mb}MB (current: {memory_mb:.1f}MB)"
                self.emergency_stop = True
                return
            
            # CPU threshold check (sustained high CPU)
            if cpu_percent > self.thresholds.max_cpu_percent:
                recent_cpu = [sample[1] for sample in list(self.cpu_samples)[-5:]]
                if len(recent_cpu) >= 3 and statistics.mean(recent_cpu) > self.thresholds.max_cpu_percent:
                    self.safety_violated = True
                    self.violation_reason = f"Sustained CPU exceeded {self.thresholds.max_cpu_percent}% (avg: {statistics.mean(recent_cpu):.1f}%)"
                    self.emergency_stop = True
                    return
            
            # Execution time check
            elapsed = time.time() - self.start_time
            if elapsed > self.thresholds.max_execution_time_seconds:
                self.safety_violated = True
                self.violation_reason = f"Test exceeded time limit ({elapsed:.1f}s > {self.thresholds.max_execution_time_seconds}s)"
                self.emergency_stop = True
                return
            
            # Memory leak detection
            if len(self.memory_samples) >= 20:
                recent_memory = list(self.memory_samples)[-20:]
                memory_trend = self._calculate_memory_trend(recent_memory)
                if memory_trend > self.thresholds.memory_growth_rate_mb_per_sec:
                    self.safety_violated = True
                    self.violation_reason = f"Memory leak detected (growth: {memory_trend:.2f}MB/s)"
                    self.emergency_stop = True
    
    def _calculate_memory_trend(self, memory_samples: List[Tuple[float, float]]) -> float:
        """Calculate memory growth trend in MB/second"""
        if len(memory_samples) < 2:
            return 0.0
        
        times = [sample[0] for sample in memory_samples]
        memories = [sample[1] for sample in memory_samples]
        
        time_span = times[-1] - times[0]
        if time_span <= 0:
            return 0.0
        
        memory_change = memories[-1] - memories[0]
        return memory_change / time_span
    
    def register_operation_start(self, operation_id: str):
        """Register a new operation"""
        with self._lock:
            self.active_operations.add(operation_id)
    
    def register_operation_completion(self, operation_id: str, success: bool):
        """Register operation completion"""
        with self._lock:
            self.active_operations.discard(operation_id)
            if success:
                self.completed_operations += 1
            else:
                self.failed_operations += 1
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current monitoring statistics"""
        with self._lock:
            current_memory = self.process.memory_info().rss / 1024 / 1024
            current_cpu = self.process.cpu_percent()
            
            return {
                "elapsed_time": time.time() - self.start_time,
                "current_memory_mb": current_memory,
                "peak_memory_mb": max([s[1] for s in self.memory_samples], default=current_memory),
                "current_cpu_percent": current_cpu,
                "peak_cpu_percent": max([s[1] for s in self.cpu_samples], default=current_cpu),
                "active_operations": len(self.active_operations),
                "completed_operations": self.completed_operations,
                "failed_operations": self.failed_operations,
                "total_operations": self.completed_operations + self.failed_operations,
                "success_rate": (self.completed_operations / (self.completed_operations + self.failed_operations)) * 100 if (self.completed_operations + self.failed_operations) > 0 else 0,
                "emergency_stop": self.emergency_stop,
                "safety_violated": self.safety_violated,
                "violation_reason": self.violation_reason
            }


class HeavyLoadStressTester:
    """Comprehensive heavy load stress testing system"""
    
    def __init__(self, thresholds: Optional[ResourceThresholds] = None):
        self.thresholds = thresholds or ResourceThresholds()
        self.monitor = None
        self.results: List[StressTestResult] = []
    
    @contextmanager
    def stress_test_session(self, test_name: str):
        """Context manager for stress test execution with monitoring"""
        logger.info(f"🔥 Starting stress test: {test_name}")
        
        start_time = time.time()
        self.monitor = SystemResourceMonitor(self.thresholds)
        self.monitor.start_monitoring()
        
        # Force garbage collection before test
        gc.collect()
        
        try:
            yield self.monitor
            
        except Exception as e:
            logger.error(f"❌ Stress test {test_name} failed: {e}")
            raise
            
        finally:
            end_time = time.time()
            if self.monitor:
                self.monitor.stop_monitoring()
                
                # Create test result
                stats = self.monitor.get_current_stats()
                throughput = stats["total_operations"] / (end_time - start_time) if (end_time - start_time) > 0 else 0
                
                result = StressTestResult(
                    test_name=test_name,
                    success=not self.monitor.safety_violated,
                    duration_seconds=end_time - start_time,
                    max_concurrent_operations=len(self.monitor.active_operations),
                    peak_memory_mb=stats["peak_memory_mb"],
                    peak_cpu_percent=stats["peak_cpu_percent"],
                    total_operations=stats["total_operations"],
                    successful_operations=stats["completed_operations"],
                    failed_operations=stats["failed_operations"],
                    throughput_ops_per_sec=throughput,
                    error_messages=[self.monitor.violation_reason] if self.monitor.safety_violated else [],
                    performance_metrics=stats,
                    breaking_point_reached=self.monitor.safety_violated
                )
                
                self.results.append(result)
                logger.info(f"✅ Stress test {test_name} completed in {result.duration_seconds:.2f}s")
                self._log_test_summary(result)
    
    def _log_test_summary(self, result: StressTestResult):
        """Log comprehensive test summary"""
        logger.info(f"""
📊 STRESS TEST SUMMARY: {result.test_name}
{'='*60}
🎯 Status: {'PASSED' if result.success else 'FAILED'}
⏱️  Duration: {result.duration_seconds:.2f}s
🔄 Total Operations: {result.total_operations}
✅ Successful: {result.successful_operations}
❌ Failed: {result.failed_operations}
📈 Success Rate: {(result.successful_operations/result.total_operations*100) if result.total_operations > 0 else 0:.1f}%
⚡ Throughput: {result.throughput_ops_per_sec:.2f} ops/sec
🧠 Peak Memory: {result.peak_memory_mb:.1f}MB
🔥 Peak CPU: {result.peak_cpu_percent:.1f}%
🚨 Breaking Point: {'YES' if result.breaking_point_reached else 'NO'}
{'='*60}
        """)


@pytest.fixture
def stress_tester():
    """Fixture providing configured stress tester"""
    return HeavyLoadStressTester()


@pytest.fixture  
def mock_flow_v2():
    """Fixture providing mock AI Writing Flow V2"""
    return MockAIWritingFlowV2(processing_time_base=0.1, failure_rate=0.05)


class TestExtremeLoadStressing:
    """Test extreme concurrent load scenarios"""
    
    @pytest.mark.performance
    def test_extreme_concurrent_operations(self, stress_tester: HeavyLoadStressTester, mock_flow_v2: MockAIWritingFlowV2):
        """
        Test system behavior under extreme concurrent load (25+ operations)
        
        This test pushes the system beyond normal capacity to identify
        breaking points and validate graceful degradation.
        """
        with stress_tester.stress_test_session("extreme_concurrent_operations") as monitor:
            
            # Test configuration
            max_concurrent_ops = 25  # Extreme load
            batch_size = 5
            
            # Create test inputs
            test_inputs = {
                "topic_title": "Extreme Load Stress Test",
                "platform": "LinkedIn",
                "file_path": "/tmp/extreme_load_test.md",
                "content_type": "STANDALONE",
                "viral_score": 8.0
            }
            
            operations_executed = 0
            operations_successful = 0
            
            # Execute operations in batches to control load ramp-up
            for batch in range(0, max_concurrent_ops, batch_size):
                if monitor.emergency_stop:
                    logger.warning("🚨 Emergency stop triggered during extreme load test")
                    break
                
                current_batch_size = min(batch_size, max_concurrent_ops - batch)
                logger.info(f"🔥 Batch {batch//batch_size + 1}: {current_batch_size} operations")
                
                # Use ThreadPoolExecutor for true concurrency
                with concurrent.futures.ThreadPoolExecutor(max_workers=current_batch_size) as executor:
                    future_to_op_id = {}
                    
                    # Submit operations
                    for i in range(current_batch_size):
                        op_id = f"extreme_op_{batch + i}"
                        monitor.register_operation_start(op_id)
                        
                        future = executor.submit(self._execute_single_operation, mock_flow_v2, test_inputs, op_id)
                        future_to_op_id[future] = op_id
                    
                    # Collect results
                    for future in concurrent.futures.as_completed(future_to_op_id.keys(), timeout=30):
                        op_id = future_to_op_id[future]
                        operations_executed += 1
                        
                        try:
                            result = future.result()
                            monitor.register_operation_completion(op_id, success=True)
                            operations_successful += 1
                        except Exception as e:
                            logger.warning(f"⚠️ Operation {op_id} failed: {e}")
                            monitor.register_operation_completion(op_id, success=False)
                
                # Brief pause between batches
                time.sleep(0.5)
            
            # Final statistics
            total_ops = operations_successful + (operations_executed - operations_successful)
            success_rate = (operations_successful / total_ops * 100) if total_ops > 0 else 0
            
            logger.info(f"🎯 Extreme load test: {operations_successful}/{total_ops} successful ({success_rate:.1f}%)")
            
            # Assertions for extreme load behavior
            assert operations_executed > 0, "No operations were executed"
            assert success_rate >= 60.0, f"Success rate too low under extreme load: {success_rate:.1f}%"
            
            # Verify system didn't crash
            current_stats = monitor.get_current_stats()
            assert not monitor.safety_violated or current_stats["peak_memory_mb"] < 2000, "System crashed or excessive resource usage"
    
    def _execute_single_operation(self, mock_flow, inputs: Dict[str, Any], op_id: str) -> Dict[str, Any]:
        """Execute a single operation with error handling"""
        try:
            # Add some variability to execution time
            time.sleep(0.01 + 0.05 * (hash(op_id) % 10) / 10)  # 10-60ms base delay
            return mock_flow.kickoff(inputs)
        except Exception as e:
            logger.debug(f"Operation {op_id} execution failed: {e}")
            raise
    
    @pytest.mark.performance
    def test_sustained_high_load(self, stress_tester: HeavyLoadStressTester, mock_flow_v2: MockAIWritingFlowV2):
        """
        Test sustained high load over extended period (scaled to 60 seconds)
        
        This test validates system stability under continuous high load
        and detects memory leaks or performance degradation.
        """
        with stress_tester.stress_test_session("sustained_high_load") as monitor:
            
            # Test configuration
            test_duration_seconds = 60  # 1 minute sustained load
            concurrent_ops = 12
            ops_per_second = 3.0  # Target rate
            
            test_inputs = {
                "topic_title": "Sustained Load Test", 
                "platform": "LinkedIn",
                "file_path": "/tmp/sustained_test.md"
            }
            
            start_time = time.time()
            op_counter = 0
            ops_in_progress = set()
            
            # Sustained load execution
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_ops) as executor:
                
                while (time.time() - start_time) < test_duration_seconds and not monitor.emergency_stop:
                    
                    # Maintain target operation rate
                    current_time = time.time()
                    expected_ops = int((current_time - start_time) * ops_per_second)
                    
                    # Submit new operations to maintain rate
                    while op_counter < expected_ops and len(ops_in_progress) < concurrent_ops:
                        op_id = f"sustained_op_{op_counter}"
                        op_counter += 1
                        
                        monitor.register_operation_start(op_id)
                        future = executor.submit(self._execute_single_operation, mock_flow_v2, test_inputs, op_id)
                        ops_in_progress.add((future, op_id))
                    
                    # Check for completed operations
                    completed_futures = []
                    for future, op_id in ops_in_progress:
                        if future.done():
                            try:
                                future.result()
                                monitor.register_operation_completion(op_id, success=True)
                            except Exception:
                                monitor.register_operation_completion(op_id, success=False)
                            completed_futures.append((future, op_id))
                    
                    # Remove completed operations
                    for completed in completed_futures:
                        ops_in_progress.discard(completed)
                    
                    # Brief sleep to prevent tight loop
                    time.sleep(0.1)
                
                # Wait for remaining operations to complete
                logger.info("🔄 Waiting for remaining operations...")
                for future, op_id in ops_in_progress:
                    try:
                        future.result(timeout=10)
                        monitor.register_operation_completion(op_id, success=True)
                    except Exception:
                        monitor.register_operation_completion(op_id, success=False)
            
            # Validate sustained load performance
            stats = monitor.get_current_stats()
            
            expected_min_ops = int(test_duration_seconds * ops_per_second * 0.8)  # 80% of target
            assert stats["total_operations"] >= expected_min_ops, f"Insufficient throughput: {stats['total_operations']} < {expected_min_ops}"
            assert stats["success_rate"] >= 70.0, f"Success rate degraded: {stats['success_rate']:.1f}%"
            
            # Memory leak detection
            if len(monitor.memory_samples) >= 10:
                memory_trend = monitor._calculate_memory_trend(list(monitor.memory_samples)[-10:])
                assert memory_trend < 5.0, f"Memory leak detected: {memory_trend:.2f}MB/s growth"


class TestResourceExhaustion:
    """Test system behavior under resource exhaustion"""
    
    @pytest.mark.performance
    def test_memory_pressure_handling(self, stress_tester: HeavyLoadStressTester, mock_flow_v2: MockAIWritingFlowV2):
        """
        Test system resilience under memory pressure
        
        This test allocates increasing amounts of memory while running operations
        to test behavior under memory pressure conditions.
        """
        with stress_tester.stress_test_session("memory_pressure_handling") as monitor:
            
            memory_ballast = []
            concurrent_ops = 8
            
            try:
                # Gradually increase memory pressure
                for pressure_level in range(1, 6):  # 5 levels
                    if monitor.emergency_stop:
                        logger.info(f"🚨 Emergency stop at pressure level {pressure_level}")
                        break
                    
                    logger.info(f"🔥 Memory pressure level {pressure_level}/5")
                    
                    # Allocate memory ballast (25MB per level)
                    ballast_size = 25 * 1024 * 1024  # 25MB
                    ballast_chunk = bytearray(ballast_size)
                    memory_ballast.append(ballast_chunk)
                    
                    # Execute operations under memory pressure
                    test_inputs = {
                        "topic_title": f"Memory Pressure L{pressure_level}",
                        "platform": "LinkedIn"
                    }
                    
                    ops_at_level = 0
                    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_ops) as executor:
                        futures = []
                        
                        for i in range(concurrent_ops):
                            op_id = f"memory_pressure_op_{pressure_level}_{i}"
                            monitor.register_operation_start(op_id)
                            future = executor.submit(self._execute_single_operation, mock_flow_v2, test_inputs, op_id)
                            futures.append((future, op_id))
                        
                        # Wait for completion
                        for future, op_id in futures:
                            try:
                                future.result(timeout=15)
                                monitor.register_operation_completion(op_id, success=True)
                                ops_at_level += 1
                            except Exception as e:
                                logger.debug(f"Operation failed under memory pressure: {e}")
                                monitor.register_operation_completion(op_id, success=False)
                    
                    logger.info(f"📊 Level {pressure_level}: {ops_at_level}/{concurrent_ops} operations successful")
                    
                    # Brief pause between pressure levels
                    time.sleep(1.0)
                
            finally:
                # Clean up memory ballast
                memory_ballast.clear()
                gc.collect()
            
            # Validate memory pressure resilience
            stats = monitor.get_current_stats()
            assert stats["success_rate"] >= 50.0, f"System failed under memory pressure: {stats['success_rate']:.1f}%"
    
    def _execute_single_operation(self, mock_flow, inputs: Dict[str, Any], op_id: str):
        """Execute single operation for resource testing"""
        try:
            return mock_flow.kickoff(inputs)
        except Exception as e:
            logger.debug(f"Operation {op_id} failed: {e}")
            raise
    
    @pytest.mark.performance  
    def test_cpu_saturation_resilience(self, stress_tester: HeavyLoadStressTester, mock_flow_v2: MockAIWritingFlowV2):
        """
        Test system behavior under CPU saturation
        
        This creates CPU-intensive workloads while running operations
        to validate behavior under high CPU load.
        """
        with stress_tester.stress_test_session("cpu_saturation_resilience") as monitor:
            
            # Override mock to use CPU-intensive version
            def cpu_intensive_operation(inputs, op_id):
                start_time = time.time()
                
                # CPU-intensive work
                iterations = 50000  # Reduced for reasonable test time
                for i in range(iterations):
                    _ = sum(range(50))  # CPU work
                    if i % 5000 == 0 and monitor.emergency_stop:
                        break
                
                # Simulate regular processing
                time.sleep(0.05)
                
                return {
                    "execution_id": op_id,
                    "success": True,
                    "execution_time": time.time() - start_time,
                    "current_stage": "completed"
                }
            
            # Test configuration  
            concurrent_ops = min(multiprocessing.cpu_count() + 1, 8)  # Slightly more than CPU cores
            total_ops = concurrent_ops * 2  # 2 batches
            
            test_inputs = {
                "topic_title": "CPU Saturation Test",
                "platform": "LinkedIn"
            }
            
            ops_completed = 0
            ops_successful = 0
            
            # Execute operations in batches
            for batch in range(2):
                if monitor.emergency_stop:
                    break
                
                logger.info(f"🔥 CPU saturation batch {batch + 1}/2 ({concurrent_ops} operations)")
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_ops) as executor:
                    futures = []
                    
                    for i in range(concurrent_ops):
                        op_id = f"cpu_sat_op_{batch}_{i}"
                        monitor.register_operation_start(op_id)
                        future = executor.submit(cpu_intensive_operation, test_inputs, op_id)
                        futures.append((future, op_id))
                    
                    # Wait for batch completion
                    for future, op_id in futures:
                        try:
                            result = future.result(timeout=30)  # Longer timeout for CPU work
                            monitor.register_operation_completion(op_id, success=True)
                            ops_successful += 1
                        except Exception as e:
                            logger.debug(f"CPU-intensive operation failed: {e}")
                            monitor.register_operation_completion(op_id, success=False)
                        ops_completed += 1
                
                # Brief cooldown between batches
                time.sleep(2.0)
            
            # Validate CPU saturation behavior
            stats = monitor.get_current_stats()
            success_rate = (ops_successful / ops_completed * 100) if ops_completed > 0 else 0
            
            assert ops_completed > 0, "No operations completed under CPU saturation"
            assert success_rate >= 60.0, f"Too many failures under CPU saturation: {success_rate:.1f}%"
            
            # CPU usage should have been elevated during test
            if len(monitor.cpu_samples) > 0:
                max_cpu = max([sample[1] for sample in monitor.cpu_samples])
                logger.info(f"📊 Peak CPU usage during test: {max_cpu:.1f}%")


class TestBreakingPointDetection:
    """Test system breaking point detection and capacity limits"""
    
    @pytest.mark.performance
    def test_find_system_capacity_limits(self, stress_tester: HeavyLoadStressTester, mock_flow_v2: MockAIWritingFlowV2):
        """
        Find system maximum capacity through gradual load increase
        
        This test gradually increases load until system limits are reached,
        identifying the breaking point and maximum sustainable capacity.
        """
        with stress_tester.stress_test_session("find_system_capacity_limits") as monitor:
            
            # Gradually increase load until breaking point
            max_sustainable_load = 0
            breaking_point_found = False
            successful_loads = []
            
            for load_level in range(2, 26, 2):  # Test loads: 2, 4, 6, ..., 24
                if monitor.emergency_stop or breaking_point_found:
                    break
                
                logger.info(f"🔍 Testing capacity: {load_level} concurrent operations")
                
                test_inputs = {
                    "topic_title": f"Capacity Test Load {load_level}",
                    "platform": "LinkedIn"
                }
                
                ops_successful = 0
                ops_total = load_level
                
                # Execute load level
                with concurrent.futures.ThreadPoolExecutor(max_workers=load_level) as executor:
                    futures = []
                    
                    for i in range(load_level):
                        op_id = f"capacity_op_{load_level}_{i}"
                        monitor.register_operation_start(op_id)
                        future = executor.submit(self._execute_capacity_test_operation, mock_flow_v2, test_inputs, op_id)
                        futures.append((future, op_id))
                    
                    # Collect results with timeout
                    for future, op_id in futures:
                        try:
                            future.result(timeout=20)
                            monitor.register_operation_completion(op_id, success=True)
                            ops_successful += 1
                        except Exception:
                            monitor.register_operation_completion(op_id, success=False)
                
                success_rate = (ops_successful / ops_total * 100) if ops_total > 0 else 0
                logger.info(f"📊 Load {load_level}: {ops_successful}/{ops_total} successful ({success_rate:.1f}%)")
                
                # Check if this load level is sustainable
                if success_rate >= 75.0 and not monitor.emergency_stop:
                    successful_loads.append((load_level, success_rate))
                    max_sustainable_load = load_level
                else:
                    logger.info(f"🚨 Breaking point detected at {load_level} concurrent operations")
                    breaking_point_found = True
                    break
                
                # Brief recovery between load levels
                time.sleep(2.0)
                gc.collect()
            
            # Analyze capacity results
            logger.info(f"🎯 Maximum sustainable capacity: {max_sustainable_load} concurrent operations")
            
            if successful_loads:
                best_load, best_rate = max(successful_loads, key=lambda x: x[0])
                logger.info(f"📈 Best performance: {best_load} operations with {best_rate:.1f}% success rate")
            
            # Assertions
            assert max_sustainable_load >= 4, f"System capacity too low: {max_sustainable_load} concurrent operations"
            assert len(successful_loads) > 0, "No successful load levels found"
            
            # Update result with capacity findings
            if stress_tester.results:
                result = stress_tester.results[-1]
                result.performance_metrics["max_sustainable_capacity"] = max_sustainable_load
                result.performance_metrics["successful_load_levels"] = successful_loads
                result.breaking_point_reached = breaking_point_found
    
    def _execute_capacity_test_operation(self, mock_flow, inputs: Dict[str, Any], op_id: str):
        """Execute operation for capacity testing"""
        try:
            # Variable execution time for realistic testing
            base_time = 0.1
            variation = (hash(op_id) % 50) / 1000  # 0-49ms variation
            time.sleep(base_time + variation)
            
            return mock_flow.kickoff(inputs)
        except Exception as e:
            logger.debug(f"Capacity test operation {op_id} failed: {e}")
            raise
    
    @pytest.mark.performance
    def test_circuit_breaker_behavior(self, stress_tester: HeavyLoadStressTester, mock_flow_v2: MockAIWritingFlowV2):
        """
        Test circuit breaker activation and recovery under stress
        
        This test deliberately triggers failures to validate circuit breaker
        behavior and system protection mechanisms.
        """
        with stress_tester.stress_test_session("circuit_breaker_behavior") as monitor:
            
            # Configure mock for high failure rate initially
            mock_flow_v2.failure_rate = 0.8  # 80% failure rate to trigger circuit breaker
            mock_flow_v2.reset_circuit_breaker()
            
            logger.info("🔥 Phase 1: Triggering circuit breaker with high failure rate")
            
            # Phase 1: Trigger circuit breaker opening
            phase1_ops = 10
            phase1_results = []
            
            test_inputs = {"topic_title": "Circuit Breaker Test", "platform": "LinkedIn"}
            
            for i in range(phase1_ops):
                op_id = f"cb_trigger_op_{i}"
                monitor.register_operation_start(op_id)
                
                try:
                    result = mock_flow_v2.kickoff(test_inputs)
                    monitor.register_operation_completion(op_id, success=True)
                    phase1_results.append("success")
                except Exception as e:
                    monitor.register_operation_completion(op_id, success=False)
                    phase1_results.append("failure")
                    if "Circuit breaker" in str(e):
                        logger.info(f"⚡ Circuit breaker activated at operation {i+1}")
                
                time.sleep(0.1)
            
            # Check circuit breaker status
            cb_stats = mock_flow_v2.get_performance_stats()
            circuit_breaker_activated = cb_stats.get("circuit_breaker_open", False)
            
            logger.info(f"📊 Phase 1 results: {phase1_results.count('success')}/{len(phase1_results)} successful")
            logger.info(f"🔌 Circuit breaker open: {circuit_breaker_activated}")
            
            # Phase 2: Reduce failure rate and test recovery
            if circuit_breaker_activated:
                logger.info("⏳ Phase 2: Testing circuit breaker recovery")
                
                # Reset to low failure rate
                mock_flow_v2.failure_rate = 0.1  # 10% failure rate
                time.sleep(2.0)  # Wait for potential recovery timeout
                
                # Test recovery operations
                recovery_ops = 5
                recovery_results = []
                
                for i in range(recovery_ops):
                    op_id = f"cb_recovery_op_{i}"
                    monitor.register_operation_start(op_id)
                    
                    try:
                        result = mock_flow_v2.kickoff(test_inputs)
                        monitor.register_operation_completion(op_id, success=True)
                        recovery_results.append("success")
                        logger.info(f"✅ Recovery operation {i+1} successful")
                    except Exception as e:
                        monitor.register_operation_completion(op_id, success=False)  
                        recovery_results.append("failure")
                        logger.info(f"❌ Recovery operation {i+1} failed: {e}")
                    
                    time.sleep(0.2)
                
                recovery_rate = recovery_results.count("success") / len(recovery_results) * 100
                logger.info(f"🔄 Recovery phase: {recovery_results.count('success')}/{len(recovery_results)} successful ({recovery_rate:.1f}%)")
                
                # Validate recovery
                assert recovery_rate >= 70.0, f"Circuit breaker recovery failed: {recovery_rate:.1f}% success rate"
            
            # Validate circuit breaker behavior
            stats = monitor.get_current_stats()
            total_ops = stats["total_operations"]
            
            assert total_ops >= phase1_ops, "Not all operations were attempted"
            assert circuit_breaker_activated, "Circuit breaker should have activated with high failure rate"


class TestSystemRecovery:
    """Test system recovery and stability after stress"""
    
    @pytest.mark.performance
    def test_post_stress_system_recovery(self, stress_tester: HeavyLoadStressTester, mock_flow_v2: MockAIWritingFlowV2):
        """
        Test system recovery after heavy stress periods
        
        This test applies heavy stress then validates the system can recover
        to normal operation within acceptable time limits.
        """
        with stress_tester.stress_test_session("post_stress_system_recovery") as monitor:
            
            # Phase 1: Apply heavy stress
            logger.info("🔥 Phase 1: Applying heavy stress load")
            
            stress_ops = 20
            stress_results = []
            
            # Increase processing time and failure rate for stress
            original_processing_time = mock_flow_v2.processing_time_base
            original_failure_rate = mock_flow_v2.failure_rate
            
            mock_flow_v2.processing_time_base = 0.2  # Slower processing
            mock_flow_v2.failure_rate = 0.15  # Higher failure rate
            
            test_inputs = {
                "topic_title": "Recovery Test Stress Phase",
                "platform": "LinkedIn"
            }
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=stress_ops) as executor:
                futures = []
                
                for i in range(stress_ops):
                    op_id = f"stress_op_{i}"
                    monitor.register_operation_start(op_id)
                    future = executor.submit(self._execute_stress_operation, mock_flow_v2, test_inputs, op_id)
                    futures.append((future, op_id))
                
                # Collect stress results
                for future, op_id in futures:
                    try:
                        future.result(timeout=15)
                        monitor.register_operation_completion(op_id, success=True)
                        stress_results.append(True)
                    except Exception:
                        monitor.register_operation_completion(op_id, success=False)
                        stress_results.append(False)
            
            stress_success_rate = sum(stress_results) / len(stress_results) * 100
            logger.info(f"📊 Stress phase: {sum(stress_results)}/{len(stress_results)} successful ({stress_success_rate:.1f}%)")
            
            # Phase 2: Recovery period
            logger.info("⏳ Phase 2: System recovery period")
            recovery_start = time.time()
            
            # Restore normal operating parameters
            mock_flow_v2.processing_time_base = original_processing_time
            mock_flow_v2.failure_rate = original_failure_rate
            mock_flow_v2.reset_circuit_breaker()
            
            # Recovery wait period
            time.sleep(3.0)
            gc.collect()  # Force cleanup
            
            # Phase 3: Validate recovery with normal load
            logger.info("🔄 Phase 3: Testing recovery with normal operations")
            
            recovery_ops = 10
            recovery_results = []
            
            recovery_inputs = {
                "topic_title": "Recovery Test Normal Phase",
                "platform": "LinkedIn"
            }
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=recovery_ops) as executor:
                futures = []
                
                for i in range(recovery_ops):
                    op_id = f"recovery_op_{i}"
                    monitor.register_operation_start(op_id)
                    future = executor.submit(self._execute_normal_operation, mock_flow_v2, recovery_inputs, op_id)
                    futures.append((future, op_id))
                
                # Collect recovery results
                for future, op_id in futures:
                    try:
                        future.result(timeout=10)
                        monitor.register_operation_completion(op_id, success=True)
                        recovery_results.append(True)
                    except Exception:
                        monitor.register_operation_completion(op_id, success=False)
                        recovery_results.append(False)
            
            recovery_time = time.time() - recovery_start
            recovery_success_rate = sum(recovery_results) / len(recovery_results) * 100
            
            logger.info(f"📊 Recovery phase: {sum(recovery_results)}/{len(recovery_results)} successful ({recovery_success_rate:.1f}%)")
            logger.info(f"⏱️ Total recovery time: {recovery_time:.2f}s")
            
            # Validate recovery
            assert recovery_success_rate >= 85.0, f"System didn't recover properly: {recovery_success_rate:.1f}% success rate"
            assert recovery_time <= 60.0, f"Recovery took too long: {recovery_time:.2f}s"
            
            # Check system stability post-recovery
            stats = monitor.get_current_stats()
            current_memory = stats["current_memory_mb"]
            baseline_memory = monitor.baseline_memory
            memory_increase = current_memory - baseline_memory
            
            logger.info(f"📊 Memory usage: {current_memory:.1f}MB (baseline: {baseline_memory:.1f}MB, increase: {memory_increase:.1f}MB)")
            assert memory_increase < 150.0, f"Excessive memory increase after stress: {memory_increase:.1f}MB"
            
            # Update result with recovery metrics
            if stress_tester.results:
                result = stress_tester.results[-1]
                result.recovery_time_seconds = recovery_time
                result.performance_metrics["stress_success_rate"] = stress_success_rate
                result.performance_metrics["recovery_success_rate"] = recovery_success_rate
                result.performance_metrics["memory_increase_mb"] = memory_increase
    
    def _execute_stress_operation(self, mock_flow, inputs: Dict[str, Any], op_id: str):
        """Execute operation with stress characteristics"""
        try:
            # Allocate extra memory during stress
            stress_memory = bytearray(2 * 1024 * 1024)  # 2MB allocation
            
            result = mock_flow.kickoff(inputs)
            
            # Keep memory allocated briefly
            time.sleep(0.05)
            del stress_memory
            
            return result
        except Exception as e:
            logger.debug(f"Stress operation {op_id} failed: {e}")
            raise
    
    def _execute_normal_operation(self, mock_flow, inputs: Dict[str, Any], op_id: str):
        """Execute operation with normal characteristics"""
        try:
            return mock_flow.kickoff(inputs)
        except Exception as e:
            logger.debug(f"Normal operation {op_id} failed: {e}")
            raise


class TestComprehensiveStressSuite:
    """Complete stress test suite with reporting"""
    
    @pytest.mark.performance
    def test_complete_heavy_load_stress_suite(self, stress_tester: HeavyLoadStressTester, mock_flow_v2: MockAIWritingFlowV2):
        """
        Execute complete heavy load stress test suite
        
        This test orchestrates all stress test scenarios and produces
        a comprehensive analysis of system behavior under stress.
        """
        logger.info("🎯 Starting complete heavy load stress test suite")
        
        # Test suite components
        test_components = [
            ("Extreme Concurrent Load", self._run_concurrent_load_component),
            ("Memory Pressure Handling", self._run_memory_pressure_component),
            ("CPU Saturation Resilience", self._run_cpu_saturation_component),
            ("System Capacity Limits", self._run_capacity_limits_component),
            ("Recovery and Stability", self._run_recovery_component)
        ]
        
        suite_results = []
        suite_start_time = time.time()
        
        # Execute each test component
        for test_name, test_function in test_components:
            logger.info(f"🔥 Executing suite component: {test_name}")
            
            try:
                component_result = test_function(stress_tester, mock_flow_v2)
                suite_results.append(component_result)
                logger.info(f"✅ {test_name} completed: {component_result.get('status', 'unknown')}")
                
                # Recovery period between components
                time.sleep(3.0)
                gc.collect()
                
            except Exception as e:
                logger.error(f"❌ {test_name} failed: {e}")
                suite_results.append({
                    "component_name": test_name,
                    "status": "failed",
                    "error": str(e)
                })
        
        suite_duration = time.time() - suite_start_time
        
        # Generate comprehensive report
        self._generate_comprehensive_report(stress_tester, suite_results, suite_duration)
        
        # Validate overall suite success
        successful_components = sum(1 for result in suite_results if result.get("status") == "passed")
        total_components = len(test_components)
        
        logger.info(f"🎯 Heavy load stress test suite completed: {successful_components}/{total_components} components passed")
        
        assert successful_components >= total_components * 0.6, f"Too many components failed: {successful_components}/{total_components}"
    
    def _run_concurrent_load_component(self, stress_tester, mock_flow_v2):
        """Run concurrent load test component"""
        try:
            concurrent_ops = 15
            test_inputs = {"topic_title": "Suite Concurrent Load", "platform": "LinkedIn"}
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_ops) as executor:
                futures = [
                    executor.submit(self._execute_suite_operation, mock_flow_v2, test_inputs, f"concurrent_{i}")
                    for i in range(concurrent_ops)
                ]
                
                results = []
                for future in concurrent.futures.as_completed(futures, timeout=30):
                    try:
                        results.append(future.result() is not None)
                    except Exception:
                        results.append(False)
            
            success_rate = sum(results) / len(results) * 100
            return {
                "component_name": "concurrent_load",
                "status": "passed" if success_rate >= 70.0 else "failed",
                "success_rate": success_rate,
                "operations_executed": len(results)
            }
        except Exception as e:
            return {"component_name": "concurrent_load", "status": "failed", "error": str(e)}
    
    def _run_memory_pressure_component(self, stress_tester, mock_flow_v2):
        """Run memory pressure test component"""
        try:
            memory_ballast = bytearray(50 * 1024 * 1024)  # 50MB pressure
            
            ops = 8
            results = []
            test_inputs = {"topic_title": "Suite Memory Pressure", "platform": "LinkedIn"}
            
            for i in range(ops):
                try:
                    result = self._execute_suite_operation(mock_flow_v2, test_inputs, f"memory_{i}")
                    results.append(result is not None)
                except Exception:
                    results.append(False)
                time.sleep(0.1)
            
            del memory_ballast
            gc.collect()
            
            success_rate = sum(results) / len(results) * 100
            return {
                "component_name": "memory_pressure",
                "status": "passed" if success_rate >= 50.0 else "failed",
                "success_rate": success_rate,
                "operations_executed": len(results)
            }
        except Exception as e:
            return {"component_name": "memory_pressure", "status": "failed", "error": str(e)}
    
    def _run_cpu_saturation_component(self, stress_tester, mock_flow_v2):
        """Run CPU saturation test component"""
        try:
            def cpu_work():
                for _ in range(25000):
                    _ = sum(range(50))
                return True
            
            cpu_workers = min(multiprocessing.cpu_count(), 6)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=cpu_workers) as executor:
                futures = [executor.submit(cpu_work) for _ in range(cpu_workers)]
                results = []
                
                for future in concurrent.futures.as_completed(futures, timeout=20):
                    try:
                        results.append(future.result())
                    except Exception:
                        results.append(False)
            
            success_rate = sum(results) / len(results) * 100
            return {
                "component_name": "cpu_saturation",
                "status": "passed" if success_rate >= 80.0 else "failed",
                "success_rate": success_rate,
                "operations_executed": len(results)
            }
        except Exception as e:
            return {"component_name": "cpu_saturation", "status": "failed", "error": str(e)}
    
    def _run_capacity_limits_component(self, stress_tester, mock_flow_v2):
        """Run capacity limits test component"""
        try:
            max_capacity = 0
            test_inputs = {"topic_title": "Suite Capacity Test", "platform": "LinkedIn"}
            
            for load in range(4, 17, 4):  # Test 4, 8, 12, 16
                with concurrent.futures.ThreadPoolExecutor(max_workers=load) as executor:
                    futures = [
                        executor.submit(self._execute_suite_operation, mock_flow_v2, test_inputs, f"capacity_{load}_{i}")
                        for i in range(load)
                    ]
                    
                    successful = 0
                    for future in concurrent.futures.as_completed(futures, timeout=15):
                        try:
                            if future.result():
                                successful += 1
                        except Exception:
                            pass
                
                success_rate = successful / load * 100
                if success_rate >= 75.0:
                    max_capacity = load
                else:
                    break
                
                time.sleep(1.0)
            
            return {
                "component_name": "capacity_limits",
                "status": "passed" if max_capacity >= 8 else "failed",
                "max_capacity": max_capacity,
                "operations_executed": sum(range(4, max_capacity + 1, 4))
            }
        except Exception as e:
            return {"component_name": "capacity_limits", "status": "failed", "error": str(e)}
    
    def _run_recovery_component(self, stress_tester, mock_flow_v2):
        """Run recovery test component"""
        try:
            # Stress phase
            original_failure_rate = mock_flow_v2.failure_rate
            mock_flow_v2.failure_rate = 0.3  # High failure rate
            
            stress_ops = 8
            test_inputs = {"topic_title": "Suite Recovery Test", "platform": "LinkedIn"}
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=stress_ops) as executor:
                futures = [
                    executor.submit(self._execute_stress_suite_operation, mock_flow_v2, test_inputs, f"recovery_stress_{i}")
                    for i in range(stress_ops)
                ]
                
                stress_results = []
                for future in concurrent.futures.as_completed(futures, timeout=20):
                    try:
                        stress_results.append(future.result() is not None)
                    except Exception:
                        stress_results.append(False)
            
            # Recovery phase
            mock_flow_v2.failure_rate = original_failure_rate
            mock_flow_v2.reset_circuit_breaker()
            time.sleep(2.0)
            
            recovery_ops = 6
            recovery_results = []
            for i in range(recovery_ops):
                try:
                    result = self._execute_suite_operation(mock_flow_v2, test_inputs, f"recovery_normal_{i}")
                    recovery_results.append(result is not None)
                except Exception:
                    recovery_results.append(False)
                time.sleep(0.1)
            
            recovery_rate = sum(recovery_results) / len(recovery_results) * 100
            return {
                "component_name": "recovery",
                "status": "passed" if recovery_rate >= 75.0 else "failed",
                "recovery_rate": recovery_rate,
                "operations_executed": len(stress_results) + len(recovery_results)
            }
        except Exception as e:
            return {"component_name": "recovery", "status": "failed", "error": str(e)}
    
    def _execute_suite_operation(self, mock_flow, inputs: Dict[str, Any], op_id: str):
        """Execute standard suite operation"""
        try:
            time.sleep(0.05)  # Brief processing simulation
            return mock_flow.kickoff(inputs)
        except Exception:
            return None
    
    def _execute_stress_suite_operation(self, mock_flow, inputs: Dict[str, Any], op_id: str):
        """Execute stress suite operation"""
        try:
            time.sleep(0.1)  # Longer processing
            temp_data = bytearray(512 * 1024)  # 512KB allocation
            result = mock_flow.kickoff(inputs)
            del temp_data
            return result
        except Exception:
            return None
    
    def _generate_comprehensive_report(self, stress_tester: HeavyLoadStressTester, suite_results: List[Dict], suite_duration: float):
        """Generate comprehensive stress test report"""
        
        timestamp = datetime.now(timezone.utc).isoformat()
        report_path = Path("/tmp/ai_writing_flow_v2_heavy_load_stress_report.json")
        
        # System information
        system_info = {
            "cpu_count": multiprocessing.cpu_count(),
            "total_memory_gb": psutil.virtual_memory().total / (1024**3),
            "platform": os.uname().sysname if hasattr(os, 'uname') else 'unknown'
        }
        
        # Aggregate statistics
        total_operations = sum(result.get("operations_executed", 0) for result in suite_results)
        passed_components = sum(1 for result in suite_results if result.get("status") == "passed")
        
        # Compile comprehensive report
        report = {
            "metadata": {
                "test_suite": "AI Writing Flow V2 Heavy Load Stress Test",
                "version": "1.0",
                "timestamp": timestamp,
                "duration_seconds": suite_duration,
                "system_info": system_info
            },
            "executive_summary": {
                "total_components": len(suite_results),
                "passed_components": passed_components,
                "failed_components": len(suite_results) - passed_components,
                "overall_success_rate": (passed_components / len(suite_results)) * 100 if suite_results else 0,
                "total_operations_executed": total_operations
            },
            "component_results": suite_results,
            "detailed_metrics": []
        }
        
        # Add detailed metrics from individual tests
        for result in stress_tester.results:
            report["detailed_metrics"].append({
                "test_name": result.test_name,
                "success": result.success,
                "duration_seconds": result.duration_seconds,
                "peak_memory_mb": result.peak_memory_mb,
                "peak_cpu_percent": result.peak_cpu_percent,
                "total_operations": result.total_operations,
                "success_rate": (result.successful_operations / result.total_operations * 100) if result.total_operations > 0 else 0,
                "throughput_ops_per_sec": result.throughput_ops_per_sec,
                "breaking_point_reached": result.breaking_point_reached
            })
        
        # Recommendations based on results
        recommendations = []
        
        if passed_components / len(suite_results) >= 0.8:
            recommendations.append("System demonstrates excellent stress resilience")
        elif passed_components / len(suite_results) >= 0.6:
            recommendations.append("System shows good stress handling with room for improvement")
        else:
            recommendations.append("System requires optimization for better stress resilience")
        
        # Resource-specific recommendations
        max_memory = max([result.peak_memory_mb for result in stress_tester.results], default=0)
        if max_memory > 500:
            recommendations.append(f"Monitor memory usage - peaked at {max_memory:.1f}MB during testing")
        
        max_cpu = max([result.peak_cpu_percent for result in stress_tester.results], default=0)
        if max_cpu > 80:
            recommendations.append(f"CPU usage reached {max_cpu:.1f}% - consider load balancing")
        
        report["recommendations"] = recommendations
        
        # Save report
        try:
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"📊 Comprehensive stress test report saved to: {report_path}")
            
            # Also create a human-readable summary
            self._create_human_readable_summary(report, report_path.with_suffix('.txt'))
            
        except Exception as e:
            logger.warning(f"Failed to save stress test report: {e}")
    
    def _create_human_readable_summary(self, report: Dict, summary_path: Path):
        """Create human-readable summary of stress test results"""
        
        summary_content = f"""
AI Writing Flow V2 - Heavy Load Stress Test Summary
================================================

Generated: {report['metadata']['timestamp']}
Duration: {report['metadata']['duration_seconds']:.2f} seconds
System: {report['metadata']['system_info']['cpu_count']} CPUs, {report['metadata']['system_info']['total_memory_gb']:.1f}GB RAM

EXECUTIVE SUMMARY
================
Overall Success Rate: {report['executive_summary']['overall_success_rate']:.1f}%
Components Passed: {report['executive_summary']['passed_components']}/{report['executive_summary']['total_components']}
Total Operations: {report['executive_summary']['total_operations_executed']}

COMPONENT RESULTS
================
"""
        
        for component in report['component_results']:
            status_icon = "✅" if component.get('status') == 'passed' else "❌"
            summary_content += f"{status_icon} {component.get('component_name', 'Unknown')}: {component.get('status', 'unknown').upper()}\n"
            
            if 'success_rate' in component:
                summary_content += f"   Success Rate: {component['success_rate']:.1f}%\n"
            if 'max_capacity' in component:
                summary_content += f"   Max Capacity: {component['max_capacity']} concurrent operations\n"
            if 'recovery_rate' in component:
                summary_content += f"   Recovery Rate: {component['recovery_rate']:.1f}%\n"
        
        summary_content += f"""

PERFORMANCE HIGHLIGHTS
====================
"""
        
        if report['detailed_metrics']:
            best_throughput = max(report['detailed_metrics'], key=lambda x: x.get('throughput_ops_per_sec', 0))
            peak_memory = max(report['detailed_metrics'], key=lambda x: x.get('peak_memory_mb', 0))
            
            summary_content += f"Best Throughput: {best_throughput['throughput_ops_per_sec']:.2f} ops/sec ({best_throughput['test_name']})\n"
            summary_content += f"Peak Memory Usage: {peak_memory['peak_memory_mb']:.1f}MB ({peak_memory['test_name']})\n"
        
        summary_content += f"""

RECOMMENDATIONS
===============
"""
        
        for rec in report['recommendations']:
            summary_content += f"• {rec}\n"
        
        summary_content += f"""

---
Generated by AI Writing Flow V2 Heavy Load Stress Testing Suite
"""
        
        try:
            with open(summary_path, 'w') as f:
                f.write(summary_content)
            logger.info(f"📄 Human-readable summary saved to: {summary_path}")
        except Exception as e:
            logger.warning(f"Failed to save summary: {e}")


if __name__ == "__main__":
    # Run heavy load stress tests
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "performance"])
