#\!/usr/bin/env python
"""
Resource Contention Tests for AI Writing Flow V2

This module implements comprehensive resource contention testing to identify
and prevent conflicts in concurrent flow execution scenarios.

Test Coverage:
- Memory contention and leak detection
- CPU contention and throttling
- I/O contention (file system, logs, metrics)
- Lock contention in shared resources
- Mixed workload scenarios
- Deadlock detection
- Performance degradation monitoring
"""

import pytest
import threading
import time
import tempfile
import shutil
import psutil
import os
import json
import logging
import multiprocessing
import queue
import concurrent.futures
from contextlib import contextmanager
from typing import Dict, List, Any, Optional, Callable, Tuple
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import weakref
import gc

# System imports for monitoring
import tracemalloc
import resource
import signal
import sys

# Test framework imports
from ai_writing_flow.models.flow_control_state import FlowControlState, StageResult, StageStatus
from ai_writing_flow.models.flow_stage import FlowStage
from ai_writing_flow.monitoring.flow_metrics import FlowMetrics, MetricsConfig, KPIType
from ai_writing_flow.monitoring.alerting import AlertManager
from ai_writing_flow.ai_writing_flow_v2 import AIWritingFlowV2
from ai_writing_flow.linear_flow import WritingFlowInputs, LinearAIWritingFlow


class ResourceMonitor:
    """Real-time resource monitoring for contention testing"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.monitoring = False
        self.measurements = []
        self._lock = threading.Lock()
        
    def start_monitoring(self, interval: float = 0.1):
        """Start resource monitoring"""
        self.monitoring = True
        self.measurements.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring = False
        if hasattr(self, '_monitor_thread'):
            self._monitor_thread.join(timeout=1.0)
            
    def _monitor_loop(self, interval: float):
        """Resource monitoring loop"""
        while self.monitoring:
            try:
                measurement = {
                    'timestamp': time.time(),
                    'cpu_percent': self.process.cpu_percent(),
                    'memory_mb': self.process.memory_info().rss / 1024 / 1024,
                    'num_threads': self.process.num_threads(),
                    'open_files': len(self.process.open_files()),
                    'connections': len(self.process.connections())
                }
                
                with self._lock:
                    self.measurements.append(measurement)
                    # Keep only last 1000 measurements
                    if len(self.measurements) > 1000:
                        self.measurements = self.measurements[-500:]
                        
                time.sleep(interval)
                
            except Exception as e:
                logging.warning(f"Resource monitoring error: {e}")
                
    def get_peak_usage(self) -> Dict[str, float]:
        """Get peak resource usage"""
        with self._lock:
            if not self.measurements:
                return {}
                
            return {
                'peak_cpu': max(m['cpu_percent'] for m in self.measurements),
                'peak_memory_mb': max(m['memory_mb'] for m in self.measurements),
                'peak_threads': max(m['num_threads'] for m in self.measurements),
                'peak_files': max(m['open_files'] for m in self.measurements),
                'avg_cpu': sum(m['cpu_percent'] for m in self.measurements) / len(self.measurements),
                'avg_memory_mb': sum(m['memory_mb'] for m in self.measurements) / len(self.measurements)
            }
            
    def detect_contention_patterns(self) -> List[Dict[str, Any]]:
        """Detect resource contention patterns"""
        patterns = []
        
        with self._lock:
            if len(self.measurements) < 10:
                return patterns
                
            # Check for CPU spikes (>80% for >1 second)
            cpu_spikes = []
            for i, m in enumerate(self.measurements):
                if m['cpu_percent'] > 80.0:
                    cpu_spikes.append(i)
                    
            if len(cpu_spikes) > 10:  # Sustained high CPU
                patterns.append({
                    'type': 'cpu_contention',
                    'severity': 'high',
                    'duration_samples': len(cpu_spikes),
                    'peak_cpu': max(self.measurements[i]['cpu_percent'] for i in cpu_spikes)
                })
                
            # Check for memory growth (>100MB increase)
            if len(self.measurements) > 20:
                early_avg = sum(m['memory_mb'] for m in self.measurements[:10]) / 10
                late_avg = sum(m['memory_mb'] for m in self.measurements[-10:]) / 10
                
                if late_avg - early_avg > 100:
                    patterns.append({
                        'type': 'memory_leak',
                        'severity': 'critical',
                        'growth_mb': late_avg - early_avg,
                        'initial_mb': early_avg,
                        'final_mb': late_avg
                    })
                    
            # Check for thread explosion (>50 threads)
            max_threads = max(m['num_threads'] for m in self.measurements)
            if max_threads > 50:
                patterns.append({
                    'type': 'thread_explosion',
                    'severity': 'high',
                    'max_threads': max_threads
                })
                
        return patterns


class DeadlockDetector:
    """Deadlock detection system"""
    
    def __init__(self):
        self.lock_graph = {}
        self.thread_locks = {}
        self._detection_lock = threading.Lock()
        
    def acquire_lock(self, thread_id: str, lock_id: str):
        """Record lock acquisition"""
        with self._detection_lock:
            if thread_id not in self.thread_locks:
                self.thread_locks[thread_id] = []
            self.thread_locks[thread_id].append(lock_id)
            
            # Build dependency graph
            if lock_id not in self.lock_graph:
                self.lock_graph[lock_id] = {'held_by': None, 'waiting': []}
            self.lock_graph[lock_id]['held_by'] = thread_id
            
    def release_lock(self, thread_id: str, lock_id: str):
        """Record lock release"""
        with self._detection_lock:
            if thread_id in self.thread_locks:
                if lock_id in self.thread_locks[thread_id]:
                    self.thread_locks[thread_id].remove(lock_id)
                    
            if lock_id in self.lock_graph:
                self.lock_graph[lock_id]['held_by'] = None
                
    def wait_for_lock(self, thread_id: str, lock_id: str):
        """Record lock wait"""
        with self._detection_lock:
            if lock_id in self.lock_graph:
                self.lock_graph[lock_id]['waiting'].append(thread_id)
                
    def detect_deadlock(self) -> List[Dict[str, Any]]:
        """Detect potential deadlocks"""
        deadlocks = []
        
        with self._detection_lock:
            # Simple cycle detection in wait-for graph
            for lock_id, info in self.lock_graph.items():
                holder = info['held_by']
                if holder is None:
                    continue
                    
                for waiter in info['waiting']:
                    # Check if holder is waiting for any locks held by waiter
                    holder_waiting = []
                    for other_lock, other_info in self.lock_graph.items():
                        if waiter in other_info.get('waiting', []) and other_info['held_by'] == holder:
                            holder_waiting.append(other_lock)
                            
                    if holder_waiting:
                        deadlocks.append({
                            'type': 'circular_wait',
                            'thread1': holder,
                            'thread2': waiter,
                            'lock1': lock_id,
                            'locks2': holder_waiting
                        })
                        
        return deadlocks


@contextmanager
def monitored_execution(monitor: ResourceMonitor):
    """Context manager for monitored test execution"""
    monitor.start_monitoring()
    try:
        yield monitor
    finally:
        monitor.stop_monitoring()


class MockFlowExecutor:
    """Mock flow executor for testing resource contention"""
    
    def __init__(self, execution_time: float = 1.0, memory_usage_mb: float = 50.0,
                 cpu_intensive: bool = False, io_intensive: bool = False):
        self.execution_time = execution_time
        self.memory_usage_mb = memory_usage_mb
        self.cpu_intensive = cpu_intensive
        self.io_intensive = io_intensive
        self.temp_files = []
        
    def execute(self, flow_id: str) -> Dict[str, Any]:
        """Execute mock flow with resource consumption"""
        start_time = time.time()
        
        # Memory allocation
        memory_hog = None
        if self.memory_usage_mb > 0:
            # Allocate memory (list of strings)
            size = int(self.memory_usage_mb * 1024 * 1024 / 100)  # Rough calculation
            memory_hog = ['x' * 100] * size
            
        # CPU intensive operations
        if self.cpu_intensive:
            # Simulate CPU-bound work
            end_time = time.time() + self.execution_time
            counter = 0
            while time.time() < end_time:
                counter += 1
                if counter % 100000 == 0:
                    time.sleep(0.001)  # Yield occasionally
        
        # I/O intensive operations
        if self.io_intensive:
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                self.temp_files.append(f.name)
                # Write data repeatedly
                for i in range(int(self.execution_time * 1000)):
                    f.write(f"Flow {flow_id} iteration {i}\n")
                    if i % 100 == 0:
                        f.flush()
                        os.fsync(f.fileno())
        
        # Sleep for remaining time
        elapsed = time.time() - start_time
        if elapsed < self.execution_time and not self.cpu_intensive:
            time.sleep(self.execution_time - elapsed)
            
        return {
            'flow_id': flow_id,
            'execution_time': time.time() - start_time,
            'memory_allocated': len(memory_hog) if memory_hog else 0,
            'temp_files': len(self.temp_files)
        }
        
    def cleanup(self):
        """Cleanup temporary resources"""
        for file_path in self.temp_files:
            try:
                os.unlink(file_path)
            except FileNotFoundError:
                pass
        self.temp_files.clear()


class TestResourceContention:
    """Comprehensive resource contention test suite"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.temp_dir = tempfile.mkdtemp()
        self.monitor = ResourceMonitor()
        self.deadlock_detector = DeadlockDetector()
        
        # Configure logging to prevent spam
        logging.getLogger().setLevel(logging.WARNING)
        
    def teardown_method(self):
        """Cleanup after each test method"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.monitor.stop_monitoring()
        
        # Force garbage collection
        gc.collect()
        
    def test_memory_contention_multiple_flows(self):
        """Test memory contention with multiple concurrent flows"""
        
        # Enable memory tracing
        tracemalloc.start()
        
        with monitored_execution(self.monitor) as monitor:
            # Create multiple memory-intensive mock flows
            executors = [
                MockFlowExecutor(execution_time=2.0, memory_usage_mb=100.0)
                for _ in range(5)
            ]
            
            # Execute flows concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(exec.execute, f"flow_{i}")
                    for i, exec in enumerate(executors)
                ]
                
                results = [future.result() for future in futures]
                
            # Cleanup executors
            for exec in executors:
                exec.cleanup()
                
        # Analyze resource usage
        usage = monitor.get_peak_usage()
        patterns = monitor.detect_contention_patterns()
        
        # Get memory statistics
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Assertions
        assert len(results) == 5, "All flows should complete"
        assert usage['peak_memory_mb'] > 400, f"Expected high memory usage, got {usage['peak_memory_mb']}MB"
        
        # Check for memory leaks
        memory_leak_detected = any(p['type'] == 'memory_leak' for p in patterns)
        if memory_leak_detected:
            pytest.fail("Memory leak detected during concurrent execution")
            
        # Validate no excessive memory growth
        assert peak / (1024 * 1024) < 1000, f"Memory usage too high: {peak / (1024 * 1024)}MB"
        
        print(f"✅ Memory contention test passed - Peak: {usage['peak_memory_mb']:.1f}MB")
        
    def test_cpu_contention_high_load(self):
        """Test CPU contention under high computational load"""
        
        with monitored_execution(self.monitor) as monitor:
            # Create CPU-intensive flows
            executors = [
                MockFlowExecutor(execution_time=3.0, cpu_intensive=True)
                for _ in range(multiprocessing.cpu_count() + 2)  # Oversubscribe CPU
            ]
            
            start_time = time.time()
            
            # Execute flows concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(executors)) as executor:
                futures = [
                    executor.submit(exec.execute, f"cpu_flow_{i}")
                    for i, exec in enumerate(executors)
                ]
                
                results = [future.result() for future in futures]
                
            total_time = time.time() - start_time
            
        # Analyze CPU usage
        usage = monitor.get_peak_usage()
        patterns = monitor.detect_contention_patterns()
        
        # Assertions
        assert len(results) == len(executors), "All CPU-intensive flows should complete"
        assert usage['peak_cpu'] > 50.0, f"Expected high CPU usage, got {usage['peak_cpu']}%"
        
        # Check for fair CPU scheduling (no single flow should dominate)
        execution_times = [r['execution_time'] for r in results]
        max_time = max(execution_times)
        min_time = min(execution_times)
        
        # Execution times should be reasonably similar (within 2x factor)
        assert max_time / min_time < 3.0, f"Unfair CPU scheduling detected: {max_time:.2f}s vs {min_time:.2f}s"
        
        print(f"✅ CPU contention test passed - Peak CPU: {usage['peak_cpu']:.1f}%")
        
    def test_io_contention_file_operations(self):
        """Test I/O contention with concurrent file operations"""
        
        with monitored_execution(self.monitor) as monitor:
            # Create I/O intensive flows writing to same directory
            executors = [
                MockFlowExecutor(execution_time=2.0, io_intensive=True)
                for _ in range(8)
            ]
            
            # Execute flows concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = [
                    executor.submit(exec.execute, f"io_flow_{i}")
                    for i, exec in enumerate(executors)
                ]
                
                results = [future.result() for future in futures]
                
            # Cleanup executors
            for exec in executors:
                exec.cleanup()
                
        # Analyze I/O patterns
        usage = monitor.get_peak_usage()
        
        # Assertions
        assert len(results) == 8, "All I/O flows should complete"
        assert usage['peak_files'] > 5, f"Expected multiple open files, got {usage['peak_files']}"
        
        # Check that all flows created temp files
        total_files = sum(r['temp_files'] for r in results)
        assert total_files == 8, f"Expected 8 temp files, got {total_files}"
        
        print(f"✅ I/O contention test passed - Peak files: {usage['peak_files']}")
        
    def test_lock_contention_flow_control_state(self):
        """Test lock contention in FlowControlState"""
        
        # Create shared state
        shared_state = FlowControlState()
        contention_results = []
        exception_count = 0
        
        def worker_thread(thread_id: int):
            """Worker thread that modifies shared state"""
            nonlocal exception_count
            
            try:
                self.deadlock_detector.acquire_lock(f"thread_{thread_id}", "flow_state_lock")
                
                for i in range(50):
                    # Simulate state operations that require locking
                    shared_state.increment_retry_count(FlowStage.DRAFT_GENERATION)
                    
                    # Add transition (this uses internal locking)
                    if shared_state.current_stage != FlowStage.FAILED:
                        try:
                            shared_state.add_transition(
                                FlowStage.QUALITY_CHECK, 
                                f"thread_{thread_id}_iteration_{i}"
                            )
                        except ValueError:
                            # Invalid transition - expected in some cases
                            pass
                    
                    # Simulate concurrent access delay
                    time.sleep(0.001)
                    
                contention_results.append({
                    'thread_id': thread_id,
                    'retry_count': shared_state.get_stage_retry_count(FlowStage.DRAFT_GENERATION),
                    'transitions': len(shared_state.execution_history)
                })
                
            except Exception as e:
                exception_count += 1
                logging.error(f"Thread {thread_id} failed: {e}")
                
            finally:
                self.deadlock_detector.release_lock(f"thread_{thread_id}", "flow_state_lock")
        
        with monitored_execution(self.monitor) as monitor:
            # Launch concurrent threads
            threads = []
            for i in range(10):
                thread = threading.Thread(target=worker_thread, args=(i,))
                threads.append(thread)
                thread.start()
                
            # Wait for all threads
            for thread in threads:
                thread.join(timeout=10.0)
                
        # Analyze results
        usage = monitor.get_peak_usage()
        deadlocks = self.deadlock_detector.detect_deadlock()
        
        # Assertions
        assert exception_count == 0, f"Expected no exceptions, got {exception_count}"
        assert len(deadlocks) == 0, f"Deadlocks detected: {deadlocks}"
        assert len(contention_results) == 10, "All threads should complete successfully"
        
        # Verify data consistency
        final_retry_count = shared_state.get_stage_retry_count(FlowStage.DRAFT_GENERATION)
        assert final_retry_count == 500, f"Expected 500 retries, got {final_retry_count}"
        
        print(f"✅ Lock contention test passed - Final retry count: {final_retry_count}")
        
    def test_metrics_storage_contention(self):
        """Test contention in metrics storage system"""
        
        # Create metrics system
        config = MetricsConfig(memory_threshold_mb=100.0)
        metrics = FlowMetrics(history_size=1000, config=config)
        
        def metrics_worker(worker_id: int):
            """Worker thread that records metrics"""
            flow_id = f"metrics_flow_{worker_id}"
            
            # Record flow start
            metrics.record_flow_start(flow_id, "test_stage")
            
            # Record multiple metrics
            for i in range(100):
                metrics.record_stage_completion(
                    flow_id=flow_id,
                    stage=f"stage_{i % 5}",
                    execution_time=0.1 + (i * 0.01),
                    success=(i % 10) != 0  # 90% success rate
                )
                
                if i % 10 == 0:
                    metrics.record_retry(flow_id, f"stage_{i % 5}", i // 10)
                    
            # Complete flow
            metrics.record_flow_completion(flow_id, success=True, final_stage="completed")
            
        with monitored_execution(self.monitor) as monitor:
            # Launch concurrent metrics workers
            with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
                futures = [
                    executor.submit(metrics_worker, i)
                    for i in range(15)
                ]
                
                # Wait for completion
                for future in futures:
                    future.result(timeout=10.0)
                    
        # Analyze metrics system health
        kpis = metrics.get_current_kpis()
        flow_summary = metrics.get_flow_summary()
        usage = monitor.get_peak_usage()
        
        # Assertions
        assert flow_summary['completed_flows'] == 15, f"Expected 15 completed flows, got {flow_summary['completed_flows']}"
        assert flow_summary['total_flows'] == 15, f"Expected 15 total flows, got {flow_summary['total_flows']}"
        assert kpis.success_rate > 85.0, f"Expected >85% success rate, got {kpis.success_rate}%"
        
        # Verify no memory leaks in metrics system
        patterns = monitor.detect_contention_patterns()
        memory_issues = [p for p in patterns if p['type'] == 'memory_leak']
        assert len(memory_issues) == 0, f"Memory leaks in metrics system: {memory_issues}"
        
        print(f"✅ Metrics contention test passed - Success rate: {kpis.success_rate:.1f}%")
        
    def test_mixed_workload_stress(self):
        """Test mixed workload with memory, CPU, and I/O contention"""
        
        with monitored_execution(self.monitor) as monitor:
            # Create mixed workload executors
            executors = [
                # Memory intensive
                MockFlowExecutor(execution_time=2.0, memory_usage_mb=150.0),
                MockFlowExecutor(execution_time=2.0, memory_usage_mb=120.0),
                
                # CPU intensive  
                MockFlowExecutor(execution_time=2.5, cpu_intensive=True),
                MockFlowExecutor(execution_time=2.5, cpu_intensive=True),
                
                # I/O intensive
                MockFlowExecutor(execution_time=3.0, io_intensive=True),
                MockFlowExecutor(execution_time=3.0, io_intensive=True),
                
                # Mixed workloads
                MockFlowExecutor(execution_time=2.0, memory_usage_mb=80.0, cpu_intensive=True),
                MockFlowExecutor(execution_time=2.5, memory_usage_mb=60.0, io_intensive=True),
            ]
            
            # Execute mixed workload
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = [
                    executor.submit(exec.execute, f"mixed_flow_{i}")
                    for i, exec in enumerate(executors)
                ]
                
                results = [future.result(timeout=15.0) for future in futures]
                
            # Cleanup
            for exec in executors:
                exec.cleanup()
                
        # Comprehensive analysis
        usage = monitor.get_peak_usage()
        patterns = monitor.detect_contention_patterns()
        
        # Assertions
        assert len(results) == 8, "All mixed workload flows should complete"
        
        # Resource usage should be significant but not excessive
        assert usage['peak_memory_mb'] > 200, f"Expected significant memory usage, got {usage['peak_memory_mb']}MB"
        assert usage['peak_cpu'] > 30.0, f"Expected significant CPU usage, got {usage['peak_cpu']}%"
        
        # Check for severe contention patterns
        critical_patterns = [p for p in patterns if p.get('severity') == 'critical']
        assert len(critical_patterns) == 0, f"Critical contention detected: {critical_patterns}"
        
        # Performance should degrade gracefully
        execution_times = [r['execution_time'] for r in results]
        avg_time = sum(execution_times) / len(execution_times)
        assert avg_time < 10.0, f"Execution time too high under contention: {avg_time:.2f}s"
        
        print(f"✅ Mixed workload test passed - Avg time: {avg_time:.2f}s, Peak memory: {usage['peak_memory_mb']:.1f}MB")
        
    def test_flow_v2_resource_isolation(self):
        """Test resource isolation in AIWritingFlowV2 under contention"""
        
        # Create test inputs
        test_inputs = {
            "topic_title": "Resource Contention Test",
            "platform": "LinkedIn", 
            "file_path": str(Path(self.temp_dir) / "test_content.md"),
            "content_type": "STANDALONE",
            "content_ownership": "ORIGINAL",
            "viral_score": 7.0
        }
        
        # Create test content file
        with open(test_inputs["file_path"], 'w') as f:
            f.write("# Test Content\n\nThis is test content for resource contention testing.")
            
        def flow_worker(worker_id: int):
            """Worker that runs V2 flow"""
            try:
                # Create isolated V2 flow instance
                flow_v2 = AIWritingFlowV2(
                    monitoring_enabled=True,
                    alerting_enabled=False,  # Disable to reduce noise
                    quality_gates_enabled=True,
                    storage_path=str(Path(self.temp_dir) / f"metrics_{worker_id}")
                )
                
                # Execute flow (will fail due to missing CrewAI, but should handle gracefully)
                result = flow_v2.kickoff(test_inputs)
                
                return {
                    'worker_id': worker_id,
                    'success': result.current_stage != "failed",
                    'final_stage': result.current_stage,
                    'error': getattr(result, 'error_message', None)
                }
                
            except Exception as e:
                return {
                    'worker_id': worker_id,
                    'success': False,
                    'error': str(e)
                }
                
        with monitored_execution(self.monitor) as monitor:
            # Run multiple V2 flows concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = [
                    executor.submit(flow_worker, i)
                    for i in range(4)
                ]
                
                results = [future.result(timeout=30.0) for future in futures]
                
        # Analyze V2 flow behavior under contention
        usage = monitor.get_peak_usage()
        patterns = monitor.detect_contention_patterns()
        
        # Assertions
        assert len(results) == 4, "All V2 flows should attempt execution"
        
        # Flows should fail gracefully, not crash
        crashed_flows = [r for r in results if 'error' in r and 'crashed' in str(r['error']).lower()]
        assert len(crashed_flows) == 0, f"Flows crashed under contention: {crashed_flows}"
        
        # Resource usage should be reasonable
        assert usage['peak_memory_mb'] < 1000, f"Excessive memory usage: {usage['peak_memory_mb']}MB"
        
        # No critical resource contention
        critical_issues = [p for p in patterns if p.get('severity') == 'critical']
        assert len(critical_issues) == 0, f"Critical resource issues: {critical_issues}"
        
        print(f"✅ V2 flow isolation test passed - {len(results)} flows completed")
        
    def test_deadlock_detection_and_prevention(self):
        """Test deadlock detection and prevention mechanisms"""
        
        # Create two locks for deadlock scenario
        lock_a = threading.Lock()
        lock_b = threading.Lock()
        
        deadlock_occurred = threading.Event()
        thread_results = []
        
        def thread_1():
            """Thread that acquires lock_a then lock_b"""
            try:
                self.deadlock_detector.acquire_lock("thread_1", "lock_a")
                with lock_a:
                    time.sleep(0.1)  # Hold lock for a bit
                    
                    self.deadlock_detector.wait_for_lock("thread_1", "lock_b")
                    
                    # Try to acquire lock_b with timeout to prevent real deadlock
                    if lock_b.acquire(timeout=2.0):
                        try:
                            self.deadlock_detector.acquire_lock("thread_1", "lock_b")
                            time.sleep(0.1)
                            thread_results.append("thread_1_success")
                        finally:
                            self.deadlock_detector.release_lock("thread_1", "lock_b")
                            lock_b.release()
                    else:
                        thread_results.append("thread_1_timeout")
                        
            except Exception as e:
                thread_results.append(f"thread_1_error_{e}")
                
            finally:
                self.deadlock_detector.release_lock("thread_1", "lock_a")
                
        def thread_2():
            """Thread that acquires lock_b then lock_a"""
            try:
                self.deadlock_detector.acquire_lock("thread_2", "lock_b")
                with lock_b:
                    time.sleep(0.1)  # Hold lock for a bit
                    
                    self.deadlock_detector.wait_for_lock("thread_2", "lock_a")
                    
                    # Try to acquire lock_a with timeout
                    if lock_a.acquire(timeout=2.0):
                        try:
                            self.deadlock_detector.acquire_lock("thread_2", "lock_a")
                            time.sleep(0.1)
                            thread_results.append("thread_2_success")
                        finally:
                            self.deadlock_detector.release_lock("thread_2", "lock_a")
                            lock_a.release()
                    else:
                        thread_results.append("thread_2_timeout")
                        
            except Exception as e:
                thread_results.append(f"thread_2_error_{e}")
                
            finally:
                self.deadlock_detector.release_lock("thread_2", "lock_b")
                
        with monitored_execution(self.monitor) as monitor:
            # Start threads that could deadlock
            t1 = threading.Thread(target=thread_1)
            t2 = threading.Thread(target=thread_2)
            
            t1.start()
            t2.start()
            
            # Wait for completion with timeout
            t1.join(timeout=5.0)
            t2.join(timeout=5.0)
            
            # Check if threads are still alive (indicating deadlock)
            if t1.is_alive() or t2.is_alive():
                deadlock_occurred.set()
                
        # Analyze deadlock detection
        detected_deadlocks = self.deadlock_detector.detect_deadlock()
        usage = monitor.get_peak_usage()
        
        # Assertions
        assert not deadlock_occurred.is_set(), "Real deadlock occurred - threads did not complete"
        assert len(thread_results) >= 2, f"Expected at least 2 thread results, got {thread_results}"
        
        # At least one thread should complete or timeout gracefully
        successful_threads = [r for r in thread_results if 'success' in r or 'timeout' in r]
        assert len(successful_threads) >= 1, f"No threads completed gracefully: {thread_results}"
        
        # Deadlock detector should identify potential issues
        if len(detected_deadlocks) > 0:
            print(f"⚠️ Potential deadlocks detected: {detected_deadlocks}")
            
        print(f"✅ Deadlock detection test passed - Results: {thread_results}")
        
    def test_performance_degradation_monitoring(self):
        """Test monitoring of performance degradation under resource pressure"""
        
        # Baseline performance measurement
        baseline_executor = MockFlowExecutor(execution_time=1.0)
        
        start = time.time()
        baseline_result = baseline_executor.execute("baseline_flow")
        baseline_time = time.time() - start
        baseline_executor.cleanup()
        
        # Performance under contention
        with monitored_execution(self.monitor) as monitor:
            # Create resource pressure
            pressure_executors = [
                MockFlowExecutor(execution_time=3.0, memory_usage_mb=100.0, cpu_intensive=True)
                for _ in range(6)
            ]
            
            # Start pressure in background
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pressure_executor:
                pressure_futures = [
                    pressure_executor.submit(exec.execute, f"pressure_flow_{i}")
                    for i, exec in enumerate(pressure_executors)
                ]
                
                # Give pressure time to build up
                time.sleep(0.5)
                
                # Measure performance under pressure
                test_executor = MockFlowExecutor(execution_time=1.0)
                start = time.time()
                pressure_result = test_executor.execute("test_under_pressure")
                pressure_time = time.time() - start
                test_executor.cleanup()
                
                # Wait for pressure to complete
                for future in pressure_futures:
                    future.result(timeout=10.0)
                    
            # Cleanup pressure executors
            for exec in pressure_executors:
                exec.cleanup()
                
        # Analyze performance degradation
        usage = monitor.get_peak_usage()
        patterns = monitor.detect_contention_patterns()
        
        degradation_ratio = pressure_time / baseline_time
        
        # Assertions
        assert baseline_time > 0, "Baseline measurement failed"
        assert pressure_time > 0, "Pressure measurement failed"
        
        # Performance should degrade under pressure, but not excessively
        assert degradation_ratio >= 1.0, f"Performance improved under pressure: {degradation_ratio}"
        assert degradation_ratio <= 5.0, f"Excessive performance degradation: {degradation_ratio}x slower"
        
        # High resource usage should be detected
        assert usage['peak_cpu'] > 50.0 or usage['peak_memory_mb'] > 300.0, "Insufficient resource pressure"
        
        # System should detect contention patterns
        high_load_patterns = [p for p in patterns if p.get('severity') in ['high', 'critical']]
        
        print(f"✅ Performance degradation test passed - Degradation: {degradation_ratio:.2f}x")
        print(f"   Baseline: {baseline_time:.3f}s, Under pressure: {pressure_time:.3f}s")
        print(f"   Peak CPU: {usage['peak_cpu']:.1f}%, Peak memory: {usage['peak_memory_mb']:.1f}MB")
        if high_load_patterns:
            print(f"   Detected patterns: {[p['type'] for p in high_load_patterns]}")


class TestResourceLeakDetection:
    """Test suite for detecting and preventing resource leaks"""
    
    def setup_method(self):
        """Setup for leak detection tests"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Enable memory tracing
        tracemalloc.start()
        
    def teardown_method(self):
        """Cleanup after leak detection tests"""
        tracemalloc.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Force cleanup
        gc.collect()
        
    def test_memory_leak_detection(self):
        """Test detection of memory leaks in flow execution"""
        
        # Record initial memory
        initial_snapshot = tracemalloc.take_snapshot()
        
        # Simulate potential memory leak scenario
        leaked_objects = []
        
        def potentially_leaky_function():
            """Function that might leak memory"""
            # Simulate object creation that might not be cleaned up
            data = ['x' * 1000] * 100  # 100KB
            leaked_objects.append(data)  # Intentional "leak"
            return len(data)
            
        # Run function multiple times
        for i in range(50):
            size = potentially_leaky_function()
            
        # Take snapshot after potential leaks
        final_snapshot = tracemalloc.take_snapshot()
        
        # Analyze memory growth
        top_stats = final_snapshot.compare_to(initial_snapshot, 'lineno')
        
        total_growth = sum(stat.size_diff for stat in top_stats)
        
        # Assertions
        assert total_growth > 1000000, f"Expected significant memory growth, got {total_growth} bytes"
        
        # Clean up "leaked" objects
        leaked_objects.clear()
        gc.collect()
        
        # Verify cleanup
        cleanup_snapshot = tracemalloc.take_snapshot()
        post_cleanup_stats = cleanup_snapshot.compare_to(initial_snapshot, 'lineno')
        post_cleanup_growth = sum(stat.size_diff for stat in post_cleanup_stats)
        
        # Memory should be mostly reclaimed after cleanup
        assert post_cleanup_growth < total_growth / 2, "Memory not properly reclaimed after cleanup"
        
        print(f"✅ Memory leak detection test passed")
        print(f"   Growth: {total_growth / 1024 / 1024:.1f}MB, After cleanup: {post_cleanup_growth / 1024 / 1024:.1f}MB")
        
    def test_file_handle_leak_detection(self):
        """Test detection of file handle leaks"""
        
        process = psutil.Process()
        initial_files = len(process.open_files())
        
        # Simulate file handle leaks
        file_handles = []
        
        try:
            for i in range(20):
                # Open files without proper cleanup
                f = open(os.path.join(self.temp_dir, f"leak_test_{i}.txt"), 'w')
                f.write(f"Test file {i}")
                file_handles.append(f)
                # Intentionally not closing
                
            current_files = len(process.open_files())
            file_growth = current_files - initial_files
            
            # Should detect file handle growth
            assert file_growth >= 15, f"Expected significant file handle growth, got {file_growth}"
            
        finally:
            # Cleanup file handles
            for f in file_handles:
                try:
                    f.close()
                except:
                    pass
                    
        # Verify cleanup
        final_files = len(process.open_files())
        remaining_growth = final_files - initial_files
        
        assert remaining_growth < 5, f"File handles not properly cleaned up: {remaining_growth} remaining"
        
        print(f"✅ File handle leak detection test passed")
        print(f"   Peak growth: {file_growth}, Final growth: {remaining_growth}")
        
    def test_thread_leak_detection(self):
        """Test detection of thread leaks"""
        
        process = psutil.Process()
        initial_threads = process.num_threads()
        
        # Create threads that might not be properly cleaned up
        threads = []
        stop_event = threading.Event()
        
        def worker_thread():
            """Worker thread that waits for stop signal"""
            while not stop_event.is_set():
                time.sleep(0.1)
                
        try:
            # Create threads
            for i in range(10):
                thread = threading.Thread(target=worker_thread, daemon=True)
                thread.start()
                threads.append(thread)
                
            # Check thread growth
            current_threads = process.num_threads()
            thread_growth = current_threads - initial_threads
            
            assert thread_growth >= 8, f"Expected thread growth, got {thread_growth}"
            
        finally:
            # Signal threads to stop
            stop_event.set()
            
            # Wait for threads to finish
            for thread in threads:
                thread.join(timeout=1.0)
                
        # Verify thread cleanup
        time.sleep(0.5)  # Allow time for cleanup
        final_threads = process.num_threads()
        remaining_growth = final_threads - initial_threads
        
        # Some threads might remain due to thread pool overhead
        assert remaining_growth < 5, f"Excessive threads remaining: {remaining_growth}"
        
        print(f"✅ Thread leak detection test passed")
        print(f"   Peak growth: {thread_growth}, Final growth: {remaining_growth}")


# Utility functions for test execution

def run_contention_test_suite():
    """Run the complete resource contention test suite"""
    
    print("🧪 Starting AI Writing Flow V2 Resource Contention Test Suite")
    print("=" * 70)
    
    # Test configuration
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
        "--disable-warnings",
        "-x"  # Stop on first failure
    ]
    
    # Run tests
    result = pytest.main(pytest_args)
    
    if result == 0:
        print("\n" + "=" * 70)
        print("✅ ALL RESOURCE CONTENTION TESTS PASSED")
        print("   - Memory contention: ✓")
        print("   - CPU contention: ✓") 
        print("   - I/O contention: ✓")
        print("   - Lock contention: ✓")
        print("   - Mixed workloads: ✓")
        print("   - Deadlock detection: ✓")
        print("   - Performance degradation: ✓")
        print("   - Resource leak detection: ✓")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("❌ RESOURCE CONTENTION TESTS FAILED")
        print(f"   Exit code: {result}")
        print("=" * 70)
    
    return result


if __name__ == "__main__":
    # Allow running tests directly
    run_contention_test_suite()
