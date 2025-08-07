#\!/usr/bin/env python
"""
Basic Resource Contention Tests for AI Writing Flow V2

This is a simplified version that tests core resource contention patterns
without depending on full V2 implementation or CrewAI.
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
import concurrent.futures
from contextlib import contextmanager
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path
import weakref
import gc
import tracemalloc


class BasicResourceMonitor:
    """Simplified resource monitoring for contention testing"""
    
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
                }
                
                with self._lock:
                    self.measurements.append(measurement)
                    # Keep only last 500 measurements
                    if len(self.measurements) > 500:
                        self.measurements = self.measurements[-250:]
                        
                time.sleep(interval)
                
            except Exception as e:
                logging.warning(f"Resource monitoring error: {e}")
                break
                
    def get_peak_usage(self) -> Dict[str, float]:
        """Get peak resource usage"""
        with self._lock:
            if not self.measurements:
                return {'peak_cpu': 0.0, 'peak_memory_mb': 0.0, 'peak_threads': 0, 'peak_files': 0}
                
            return {
                'peak_cpu': max(m['cpu_percent'] for m in self.measurements),
                'peak_memory_mb': max(m['memory_mb'] for m in self.measurements),
                'peak_threads': max(m['num_threads'] for m in self.measurements),
                'peak_files': max(m['open_files'] for m in self.measurements),
                'avg_cpu': sum(m['cpu_percent'] for m in self.measurements) / len(self.measurements),
                'avg_memory_mb': sum(m['memory_mb'] for m in self.measurements) / len(self.measurements)
            }
            
    def detect_resource_issues(self) -> List[str]:
        """Detect basic resource issues"""
        issues = []
        usage = self.get_peak_usage()
        
        if usage['peak_cpu'] > 90.0:
            issues.append(f"High CPU usage: {usage['peak_cpu']:.1f}%")
        if usage['peak_memory_mb'] > 1000.0:
            issues.append(f"High memory usage: {usage['peak_memory_mb']:.1f}MB")
        if usage['peak_threads'] > 50:
            issues.append(f"Thread explosion: {usage['peak_threads']} threads")
            
        return issues


class BasicLockTester:
    """Basic lock contention testing"""
    
    def __init__(self):
        self.shared_counter = 0
        self.lock = threading.RLock()
        self.operations_log = []
        
    def concurrent_operation(self, thread_id: int, operations: int = 100):
        """Perform concurrent operations with locking"""
        for i in range(operations):
            with self.lock:
                old_value = self.shared_counter
                # Simulate some work
                time.sleep(0.001)
                self.shared_counter = old_value + 1
                
                self.operations_log.append({
                    'thread_id': thread_id,
                    'operation': i,
                    'value': self.shared_counter,
                    'timestamp': time.time()
                })
                
    def validate_consistency(self, expected_total: int) -> bool:
        """Validate that operations were consistent"""
        return self.shared_counter == expected_total


class BasicWorkloadSimulator:
    """Simulate different types of workloads"""
    
    def __init__(self, workload_type: str = "cpu", duration: float = 1.0, intensity: float = 1.0):
        self.workload_type = workload_type
        self.duration = duration
        self.intensity = intensity
        self.temp_files = []
        
    def run_workload(self, worker_id: str) -> Dict[str, Any]:
        """Run the specified workload"""
        start_time = time.time()
        
        if self.workload_type == "cpu":
            return self._cpu_workload(worker_id, start_time)
        elif self.workload_type == "memory":
            return self._memory_workload(worker_id, start_time)
        elif self.workload_type == "io":
            return self._io_workload(worker_id, start_time)
        else:
            return self._mixed_workload(worker_id, start_time)
            
    def _cpu_workload(self, worker_id: str, start_time: float) -> Dict[str, Any]:
        """CPU-intensive workload"""
        end_time = start_time + self.duration
        iterations = 0
        
        while time.time() < end_time:
            # CPU-bound calculation
            for i in range(int(10000 * self.intensity)):
                iterations += 1
                result = i ** 2 + i ** 0.5
                
            if iterations % 100000 == 0:
                time.sleep(0.001)  # Yield occasionally
                
        return {
            'worker_id': worker_id,
            'workload_type': 'cpu',
            'duration': time.time() - start_time,
            'iterations': iterations
        }
        
    def _memory_workload(self, worker_id: str, start_time: float) -> Dict[str, Any]:
        """Memory-intensive workload"""
        memory_blocks = []
        
        # Allocate memory blocks
        block_size = int(1024 * 1024 * self.intensity)  # MB
        for i in range(int(self.duration * 10)):
            block = bytearray(block_size)
            # Write some data to ensure allocation
            for j in range(0, len(block), 1024):
                block[j] = (i + j) % 256
            memory_blocks.append(block)
            time.sleep(0.1)
            
        # Hold memory for remaining duration
        remaining_time = self.duration - (time.time() - start_time)
        if remaining_time > 0:
            time.sleep(remaining_time)
            
        memory_used = len(memory_blocks) * block_size / 1024 / 1024
        
        return {
            'worker_id': worker_id,
            'workload_type': 'memory',
            'duration': time.time() - start_time,
            'memory_allocated_mb': memory_used
        }
        
    def _io_workload(self, worker_id: str, start_time: float) -> Dict[str, Any]:
        """I/O-intensive workload"""
        files_created = 0
        bytes_written = 0
        
        while time.time() - start_time < self.duration:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, prefix=f"io_test_{worker_id}_") as f:
                self.temp_files.append(f.name)
                
                # Write data
                data_size = int(1024 * self.intensity)  # KB
                data = "test data " * (data_size // 10)
                
                for i in range(10):
                    f.write(f"{i}: {data}\n")
                    f.flush()
                    os.fsync(f.fileno())
                    
                files_created += 1
                bytes_written += len(data) * 10
                
            time.sleep(0.1)
            
        return {
            'worker_id': worker_id,
            'workload_type': 'io',
            'duration': time.time() - start_time,
            'files_created': files_created,
            'bytes_written': bytes_written
        }
        
    def _mixed_workload(self, worker_id: str, start_time: float) -> Dict[str, Any]:
        """Mixed CPU, memory, and I/O workload"""
        # Allocate some memory
        memory_block = bytearray(int(1024 * 1024 * self.intensity))
        
        # Create a file
        temp_file = None
        with tempfile.NamedTemporaryFile(mode='w', delete=False, prefix=f"mixed_{worker_id}_") as f:
            temp_file = f.name
            self.temp_files.append(temp_file)
        
        operations = 0
        while time.time() - start_time < self.duration:
            # CPU work
            for i in range(1000):
                result = i ** 2
                memory_block[i % len(memory_block)] = result % 256
                operations += 1
                
            # I/O work
            with open(temp_file, 'a') as f:
                f.write(f"Operation {operations} at {time.time()}\n")
                
            time.sleep(0.01)
            
        return {
            'worker_id': worker_id,
            'workload_type': 'mixed',
            'duration': time.time() - start_time,
            'operations': operations,
            'memory_used_mb': len(memory_block) / 1024 / 1024
        }
        
    def cleanup(self):
        """Clean up temporary resources"""
        for file_path in self.temp_files:
            try:
                os.unlink(file_path)
            except FileNotFoundError:
                pass
        self.temp_files.clear()


@contextmanager
def monitored_execution(monitor: BasicResourceMonitor):
    """Context manager for monitored test execution"""
    monitor.start_monitoring()
    try:
        yield monitor
    finally:
        monitor.stop_monitoring()


class TestBasicResourceContention:
    """Basic resource contention test suite"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.temp_dir = tempfile.mkdtemp()
        self.monitor = BasicResourceMonitor()
        
        # Suppress non-critical logging
        logging.getLogger().setLevel(logging.ERROR)
        
    def teardown_method(self):
        """Cleanup after each test method"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.monitor.stop_monitoring()
        gc.collect()
        
    def test_cpu_contention_basic(self):
        """Test basic CPU contention with multiple threads"""
        
        with monitored_execution(self.monitor) as monitor:
            # Create CPU-intensive workloads
            simulators = [
                BasicWorkloadSimulator("cpu", duration=2.0, intensity=1.0)
                for _ in range(multiprocessing.cpu_count())
            ]
            
            # Run workloads concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(simulators)) as executor:
                futures = [
                    executor.submit(sim.run_workload, f"cpu_worker_{i}")
                    for i, sim in enumerate(simulators)
                ]
                
                results = [future.result(timeout=10.0) for future in futures]
                
        # Analyze results
        usage = monitor.get_peak_usage()
        issues = monitor.detect_resource_issues()
        
        # Assertions
        assert len(results) == len(simulators), "All CPU workloads should complete"
        assert usage['peak_cpu'] > 20.0, f"Expected significant CPU usage, got {usage['peak_cpu']}%"
        
        # Check fairness - no worker should be starved
        iterations = [r['iterations'] for r in results]
        if len(iterations) > 1:
            max_iter = max(iterations)
            min_iter = min(iterations)
            fairness_ratio = max_iter / min_iter if min_iter > 0 else float('inf')
            assert fairness_ratio < 5.0, f"Unfair CPU scheduling: {fairness_ratio:.2f}x difference"
            
        print(f"✅ CPU contention test passed - Peak CPU: {usage['peak_cpu']:.1f}%")
        if issues:
            print(f"   Issues detected: {issues}")
            
    def test_memory_contention_basic(self):
        """Test basic memory contention"""
        
        # Enable memory tracing
        tracemalloc.start()
        initial_snapshot = tracemalloc.take_snapshot()
        
        with monitored_execution(self.monitor) as monitor:
            # Create memory-intensive workloads
            simulators = [
                BasicWorkloadSimulator("memory", duration=1.5, intensity=50.0)  # 50MB each
                for _ in range(4)
            ]
            
            # Run workloads concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = [
                    executor.submit(sim.run_workload, f"mem_worker_{i}")
                    for i, sim in enumerate(simulators)
                ]
                
                results = [future.result(timeout=10.0) for future in futures]
                
        # Analyze memory usage
        final_snapshot = tracemalloc.take_snapshot()
        usage = monitor.get_peak_usage()
        issues = monitor.detect_resource_issues()
        
        # Calculate memory growth
        top_stats = final_snapshot.compare_to(initial_snapshot, 'lineno')
        total_growth = sum(stat.size_diff for stat in top_stats if stat.size_diff > 0)
        
        tracemalloc.stop()
        
        # Assertions
        assert len(results) == 4, "All memory workloads should complete"
        assert usage['peak_memory_mb'] > 100.0, f"Expected significant memory usage, got {usage['peak_memory_mb']}MB"
        
        # Check that memory was actually allocated
        total_allocated = sum(r['memory_allocated_mb'] for r in results)
        assert total_allocated > 150.0, f"Expected >150MB allocated, got {total_allocated:.1f}MB"
        
        print(f"✅ Memory contention test passed - Peak: {usage['peak_memory_mb']:.1f}MB")
        print(f"   Total allocated: {total_allocated:.1f}MB, Growth: {total_growth / 1024 / 1024:.1f}MB")
        
    def test_io_contention_basic(self):
        """Test basic I/O contention"""
        
        with monitored_execution(self.monitor) as monitor:
            # Create I/O-intensive workloads
            simulators = [
                BasicWorkloadSimulator("io", duration=2.0, intensity=5.0)
                for _ in range(6)
            ]
            
            # Run workloads concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                futures = [
                    executor.submit(sim.run_workload, f"io_worker_{i}")
                    for i, sim in enumerate(simulators)
                ]
                
                results = [future.result(timeout=15.0) for future in futures]
                
            # Cleanup
            for sim in simulators:
                sim.cleanup()
                
        # Analyze I/O patterns
        usage = monitor.get_peak_usage()
        issues = monitor.detect_resource_issues()
        
        # Assertions
        assert len(results) == 6, "All I/O workloads should complete"
        
        # Check that files were created and data written
        total_files = sum(r['files_created'] for r in results)
        total_bytes = sum(r['bytes_written'] for r in results)
        
        assert total_files > 20, f"Expected >20 files created, got {total_files}"
        assert total_bytes > 100000, f"Expected >100KB written, got {total_bytes} bytes"
        
        print(f"✅ I/O contention test passed - Files: {total_files}, Bytes: {total_bytes}")
        if usage['peak_files'] > 10:
            print(f"   Peak open files: {usage['peak_files']}")
            
    def test_lock_contention_basic(self):
        """Test basic lock contention"""
        
        lock_tester = BasicLockTester()
        
        with monitored_execution(self.monitor) as monitor:
            # Run concurrent operations with shared lock
            num_threads = 8
            operations_per_thread = 50
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [
                    executor.submit(lock_tester.concurrent_operation, i, operations_per_thread)
                    for i in range(num_threads)
                ]
                
                # Wait for all operations to complete
                for future in futures:
                    future.result(timeout=10.0)
                    
        # Analyze lock contention results
        usage = monitor.get_peak_usage()
        expected_total = num_threads * operations_per_thread
        
        # Assertions
        assert lock_tester.validate_consistency(expected_total), (
            f"Lock contention caused inconsistency: expected {expected_total}, "
            f"got {lock_tester.shared_counter}"
        )
        
        # Check that all operations were logged
        assert len(lock_tester.operations_log) == expected_total, (
            f"Missing operations in log: expected {expected_total}, "
            f"got {len(lock_tester.operations_log)}"
        )
        
        # Verify operations from all threads
        thread_ids = set(op['thread_id'] for op in lock_tester.operations_log)
        assert len(thread_ids) == num_threads, f"Not all threads participated: {thread_ids}"
        
        print(f"✅ Lock contention test passed - {expected_total} operations completed consistently")
        print(f"   Final counter: {lock_tester.shared_counter}, Threads: {len(thread_ids)}")
        
    def test_mixed_workload_stress(self):
        """Test mixed workload stress scenario"""
        
        with monitored_execution(self.monitor) as monitor:
            # Create varied workload mix
            simulators = [
                # CPU workers
                BasicWorkloadSimulator("cpu", duration=3.0, intensity=0.8),
                BasicWorkloadSimulator("cpu", duration=3.0, intensity=0.8),
                
                # Memory workers  
                BasicWorkloadSimulator("memory", duration=2.5, intensity=30.0),
                BasicWorkloadSimulator("memory", duration=2.5, intensity=25.0),
                
                # I/O workers
                BasicWorkloadSimulator("io", duration=3.5, intensity=3.0),
                BasicWorkloadSimulator("io", duration=3.5, intensity=3.0),
                
                # Mixed workers
                BasicWorkloadSimulator("mixed", duration=3.0, intensity=1.5),
                BasicWorkloadSimulator("mixed", duration=3.0, intensity=1.5),
            ]
            
            # Execute all workloads concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = [
                    executor.submit(sim.run_workload, f"mixed_worker_{i}")
                    for i, sim in enumerate(simulators)
                ]
                
                results = [future.result(timeout=20.0) for future in futures]
                
            # Cleanup
            for sim in simulators:
                sim.cleanup()
                
        # Comprehensive analysis
        usage = monitor.get_peak_usage()
        issues = monitor.detect_resource_issues()
        
        # Assertions
        assert len(results) == 8, "All mixed workloads should complete"
        
        # Resource usage should be significant but manageable
        assert usage['peak_cpu'] > 10.0, f"Expected CPU activity, got {usage['peak_cpu']}%"
        assert usage['peak_memory_mb'] > 50.0, f"Expected memory activity, got {usage['peak_memory_mb']}MB"
        
        # System should handle mixed load without critical issues
        critical_issues = [issue for issue in issues if "High" in issue or "explosion" in issue]
        
        # Check execution times are reasonable
        execution_times = [r['duration'] for r in results]
        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)
        
        assert max_time < 25.0, f"Execution time too high under mixed load: {max_time:.2f}s"
        
        print(f"✅ Mixed workload stress test passed")
        print(f"   Peak CPU: {usage['peak_cpu']:.1f}%, Peak memory: {usage['peak_memory_mb']:.1f}MB")
        print(f"   Avg execution time: {avg_time:.2f}s, Max: {max_time:.2f}s")
        
        if critical_issues:
            print(f"   Critical issues: {critical_issues}")
        elif issues:
            print(f"   Minor issues: {issues}")
            
    def test_resource_cleanup_validation(self):
        """Test that resources are properly cleaned up after contention"""
        
        # Record initial state
        initial_process = psutil.Process()
        initial_memory = initial_process.memory_info().rss / 1024 / 1024
        initial_threads = initial_process.num_threads()
        initial_files = len(initial_process.open_files())
        
        # Run resource-intensive operations
        simulators = [
            BasicWorkloadSimulator("mixed", duration=1.0, intensity=2.0)
            for _ in range(4)
        ]
        
        with monitored_execution(self.monitor) as monitor:
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = [
                    executor.submit(sim.run_workload, f"cleanup_worker_{i}")
                    for i, sim in enumerate(simulators)
                ]
                
                results = [future.result(timeout=10.0) for future in futures]
                
            # Explicit cleanup
            for sim in simulators:
                sim.cleanup()
                
        # Force garbage collection
        gc.collect()
        time.sleep(0.5)  # Allow system cleanup
        
        # Check final state
        final_process = psutil.Process()
        final_memory = final_process.memory_info().rss / 1024 / 1024
        final_threads = final_process.num_threads()
        final_files = len(final_process.open_files())
        
        # Analyze cleanup effectiveness
        memory_growth = final_memory - initial_memory
        thread_growth = final_threads - initial_threads
        file_growth = final_files - initial_files
        
        # Assertions - some growth is acceptable, but not excessive
        assert memory_growth < 100.0, f"Excessive memory growth: {memory_growth:.1f}MB"
        assert thread_growth < 10, f"Thread leak detected: {thread_growth} extra threads"
        assert file_growth < 5, f"File handle leak detected: {file_growth} extra files"
        
        print(f"✅ Resource cleanup test passed")
        print(f"   Memory growth: {memory_growth:.1f}MB")
        print(f"   Thread growth: {thread_growth}")
        print(f"   File handle growth: {file_growth}")


def run_basic_contention_tests():
    """Run the basic resource contention test suite"""
    
    print("🧪 Running Basic Resource Contention Tests")
    print("=" * 60)
    
    # Run tests using pytest
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
        "--disable-warnings"
    ]
    
    result = pytest.main(pytest_args)
    
    if result == 0:
        print("\n" + "=" * 60)
        print("✅ ALL BASIC RESOURCE CONTENTION TESTS PASSED")
        print("   - CPU contention: ✓")
        print("   - Memory contention: ✓") 
        print("   - I/O contention: ✓")
        print("   - Lock contention: ✓")
        print("   - Mixed workload stress: ✓")
        print("   - Resource cleanup: ✓")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ BASIC RESOURCE CONTENTION TESTS FAILED")
        print(f"   Exit code: {result}")
        print("=" * 60)
    
    return result


if __name__ == "__main__":
    run_basic_contention_tests()
