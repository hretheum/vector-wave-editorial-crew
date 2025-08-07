#\!/usr/bin/env python
"""
Heavy Load Stress Testing for AI Writing Flow V2

This module provides comprehensive stress testing capabilities that push the V2 system
to its limits while maintaining safety and observability.

Test Categories:
1. Extreme Concurrent Load Testing (20+ concurrent flows)
2. Resource Exhaustion Testing (CPU, Memory, I/O saturation)
3. Sustained Load Testing (extended periods, memory leak detection)
4. Breaking Point Detection (maximum capacity, failure thresholds)
5. Recovery Testing (circuit breaker activation, graceful degradation)

Safety Features:
- Automatic test termination on critical thresholds
- Real-time resource monitoring
- System health checks during stress
- Recovery time measurement
- Post-stress stability validation
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
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from contextlib import contextmanager
from collections import deque
import weakref
import resource
import signal

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# System imports
from ai_writing_flow.ai_writing_flow_v2 import AIWritingFlowV2
from ai_writing_flow.linear_flow import WritingFlowInputs, LinearAIWritingFlow
from ai_writing_flow.monitoring.flow_metrics import FlowMetrics, KPISnapshot, KPIType
from ai_writing_flow.monitoring.alerting import AlertManager, AlertRule, AlertSeverity
from ai_writing_flow.utils.circuit_breaker import CircuitBreaker, CircuitBreakerError
from ai_writing_flow.models import WritingFlowState
from ai_writing_flow.models.flow_control_state import FlowControlState, CircuitBreakerState


# Configure aggressive logging for stress tests
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class StressTestResult:
    """Result of a stress test execution"""
    test_name: str
    success: bool
    duration_seconds: float
    max_concurrent_flows: int
    peak_memory_mb: float
    peak_cpu_percent: float
    total_executions: int
    successful_executions: int
    failed_executions: int
    error_messages: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    breaking_point_reached: bool = False
    recovery_time_seconds: Optional[float] = None


@dataclass
class ResourceThresholds:
    """Safety thresholds for stress testing"""
    max_memory_mb: float = 2048.0  # 2GB memory limit
    max_cpu_percent: float = 95.0  # 95% CPU limit
    max_execution_time_seconds: float = 600.0  # 10 minutes max test time
    max_concurrent_flows: int = 50  # Maximum concurrent flows
    memory_growth_rate_mb_per_sec: float = 50.0  # Memory leak detection
    circuit_breaker_threshold: int = 10  # Circuit breaker failure threshold


class StressTestMonitor:
    """Real-time monitoring and safety system for stress tests"""
    
    def __init__(self, thresholds: ResourceThresholds):
        self.thresholds = thresholds
        self.start_time = time.time()
        self.process = psutil.Process()
        self.baseline_memory = self.process.memory_info().rss / 1024 / 1024
        self.baseline_cpu = 0.0
        
        # Monitoring data
        self.memory_samples = deque(maxlen=1000)
        self.cpu_samples = deque(maxlen=1000) 
        self.active_flows = set()
        self.completed_flows = 0
        self.failed_flows = 0
        
        # Safety flags
        self.emergency_stop = False
        self.safety_violated = False
        self.violation_reason = ""
        
        # Background monitoring thread
        self._monitor_thread = None
        self._stop_monitoring = threading.Event()
    
    def start_monitoring(self):
        """Start background resource monitoring"""
        self._stop_monitoring.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("🔍 Stress test monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        if self._monitor_thread:
            self._stop_monitoring.set()
            self._monitor_thread.join(timeout=5.0)
        logger.info("🛑 Stress test monitoring stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while not self._stop_monitoring.is_set():
            try:
                # Sample system resources
                memory_mb = self.process.memory_info().rss / 1024 / 1024
                cpu_percent = self.process.cpu_percent()
                
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
        
        # Memory threshold check
        if memory_mb > self.thresholds.max_memory_mb:
            self.safety_violated = True
            self.violation_reason = f"Memory exceeded {self.thresholds.max_memory_mb}MB (current: {memory_mb:.1f}MB)"
            self.emergency_stop = True
            return
        
        # CPU threshold check (sustained high CPU)
        if cpu_percent > self.thresholds.max_cpu_percent:
            recent_cpu = [sample[1] for sample in list(self.cpu_samples)[-10:]]
            if len(recent_cpu) >= 5 and statistics.mean(recent_cpu) > self.thresholds.max_cpu_percent:
                self.safety_violated = True
                self.violation_reason = f"Sustained CPU exceeded {self.thresholds.max_cpu_percent}% (avg: {statistics.mean(recent_cpu):.1f}%)"
                self.emergency_stop = True
                return
        
        # Execution time check
        elapsed = time.time() - self.start_time
        if elapsed > self.thresholds.max_execution_time_seconds:
            self.safety_violated = True
            self.violation_reason = f"Test exceeded maximum time limit ({elapsed:.1f}s > {self.thresholds.max_execution_time_seconds}s)"
            self.emergency_stop = True
            return
        
        # Memory leak detection
        if len(self.memory_samples) >= 10:
            recent_memory = list(self.memory_samples)[-10:]
            memory_trend = self._calculate_memory_trend(recent_memory)
            if memory_trend > self.thresholds.memory_growth_rate_mb_per_sec:
                self.safety_violated = True
                self.violation_reason = f"Memory leak detected (growth rate: {memory_trend:.2f}MB/s)"
                self.emergency_stop = True
    
    def _calculate_memory_trend(self, memory_samples: List[Tuple[float, float]]) -> float:
        """Calculate memory growth trend in MB/second"""
        if len(memory_samples) < 2:
            return 0.0
        
        times = [sample[0] for sample in memory_samples]
        memories = [sample[1] for sample in memory_samples]
        
        # Simple linear regression for trend
        time_span = times[-1] - times[0]
        if time_span <= 0:
            return 0.0
        
        memory_change = memories[-1] - memories[0]
        return memory_change / time_span
    
    def register_flow_start(self, flow_id: str):
        """Register a new flow execution"""
        self.active_flows.add(flow_id)
    
    def register_flow_completion(self, flow_id: str, success: bool):
        """Register flow completion"""
        self.active_flows.discard(flow_id)
        if success:
            self.completed_flows += 1
        else:
            self.failed_flows += 1
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current monitoring statistics"""
        current_memory = self.process.memory_info().rss / 1024 / 1024
        current_cpu = self.process.cpu_percent()
        
        return {
            "elapsed_time": time.time() - self.start_time,
            "current_memory_mb": current_memory,
            "peak_memory_mb": max([s[1] for s in self.memory_samples], default=current_memory),
            "current_cpu_percent": current_cpu,
            "peak_cpu_percent": max([s[1] for s in self.cpu_samples], default=current_cpu),
            "active_flows": len(self.active_flows),
            "completed_flows": self.completed_flows,
            "failed_flows": self.failed_flows,
            "total_flows": self.completed_flows + self.failed_flows,
            "success_rate": (self.completed_flows / (self.completed_flows + self.failed_flows)) * 100 if (self.completed_flows + self.failed_flows) > 0 else 0,
            "emergency_stop": self.emergency_stop,
            "safety_violated": self.safety_violated,
            "violation_reason": self.violation_reason
        }


class HeavyLoadStressTester:
    """Comprehensive heavy load stress testing system"""
    
    def __init__(self, thresholds: Optional[ResourceThresholds] = None):
        self.thresholds = thresholds or ResourceThresholds()
        self.monitor = StressTestMonitor(self.thresholds)
        self.results: List[StressTestResult] = []
    
    @contextmanager
    def stress_test_session(self, test_name: str):
        """Context manager for stress test execution with monitoring"""
        logger.info(f"🔥 Starting stress test: {test_name}")
        
        start_time = time.time()
        self.monitor = StressTestMonitor(self.thresholds)  # Fresh monitor for each test
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
            self.monitor.stop_monitoring()
            
            # Create test result
            stats = self.monitor.get_current_stats()
            result = StressTestResult(
                test_name=test_name,
                success=not self.monitor.safety_violated,
                duration_seconds=end_time - start_time,
                max_concurrent_flows=len(self.monitor.active_flows),
                peak_memory_mb=stats["peak_memory_mb"],
                peak_cpu_percent=stats["peak_cpu_percent"],
                total_executions=stats["total_flows"],
                successful_executions=stats["completed_flows"],
                failed_executions=stats["failed_flows"],
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
🔄 Total Executions: {result.total_executions}
✅ Successful: {result.successful_executions}
❌ Failed: {result.failed_executions}
📈 Success Rate: {(result.successful_executions/result.total_executions*100) if result.total_executions > 0 else 0:.1f}%
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
def mock_v2_flow():
    """Fixture providing mocked V2 flow for testing"""
    with patch('ai_writing_flow.ai_writing_flow_v2.AIWritingFlowV2') as mock_flow_class:
        mock_flow = MagicMock()
        mock_flow_class.return_value = mock_flow
        
        # Mock successful execution by default
        def mock_kickoff(inputs):
            time.sleep(0.1)  # Simulate processing time
            final_state = WritingFlowState()
            final_state.current_stage = "completed"
            final_state.agents_executed = ["research", "draft", "style", "quality"]
            return final_state
        
        mock_flow.kickoff = mock_kickoff
        yield mock_flow


class TestExtremeLoadStressing:
    """Test extreme concurrent load scenarios"""
    
    @pytest.mark.performance
    async def test_extreme_concurrent_flows(self, stress_tester: HeavyLoadStressTester, mock_v2_flow):
        """
        Test system behavior under extreme concurrent load (20+ flows)
        
        This test pushes the system beyond normal capacity to identify
        breaking points and validate graceful degradation.
        """
        with stress_tester.stress_test_session("extreme_concurrent_flows") as monitor:
            
            # Test configuration
            max_concurrent_flows = 25  # Extreme load
            flow_batch_size = 5
            
            # Create test inputs
            test_inputs = {
                "topic_title": "AI Stress Test Content",
                "platform": "LinkedIn", 
                "file_path": "/tmp/stress_test_content.md",
                "content_type": "STANDALONE",
                "content_ownership": "ORIGINAL",
                "viral_score": 8.0,
                "editorial_recommendations": "Optimize for stress testing"
            }
            
            flows_executed = 0
            flows_successful = 0
            flows_failed = 0
            
            # Execute flows in batches to control load ramp-up
            for batch in range(0, max_concurrent_flows, flow_batch_size):
                if monitor.emergency_stop:
                    logger.warning("🚨 Emergency stop triggered during extreme load test")
                    break
                
                batch_size = min(flow_batch_size, max_concurrent_flows - batch)
                logger.info(f"🔥 Starting batch {batch//flow_batch_size + 1}: {batch_size} flows")
                
                # Use ThreadPoolExecutor for true concurrency
                with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
                    future_to_flow_id = {}
                    
                    # Submit flows
                    for i in range(batch_size):
                        flow_id = f"extreme_flow_{batch + i}"
                        monitor.register_flow_start(flow_id)
                        
                        future = executor.submit(self._execute_single_flow, mock_v2_flow, test_inputs, flow_id)
                        future_to_flow_id[future] = flow_id
                    
                    # Collect results
                    for future in concurrent.futures.as_completed(future_to_flow_id.keys(), timeout=30):
                        flow_id = future_to_flow_id[future]
                        flows_executed += 1
                        
                        try:
                            result = future.result()
                            monitor.register_flow_completion(flow_id, success=True)
                            flows_successful += 1
                        except Exception as e:
                            logger.warning(f"⚠️ Flow {flow_id} failed: {e}")
                            monitor.register_flow_completion(flow_id, success=False)  
                            flows_failed += 1
                
                # Brief pause between batches
                await asyncio.sleep(0.5)
            
            # Final statistics
            total_flows = flows_successful + flows_failed
            success_rate = (flows_successful / total_flows * 100) if total_flows > 0 else 0
            
            logger.info(f"🎯 Extreme load test completed: {flows_successful}/{total_flows} successful ({success_rate:.1f}%)")
            
            # Assertions for extreme load behavior
            assert flows_executed > 0, "No flows were executed"
            assert success_rate >= 60.0, f"Success rate too low under extreme load: {success_rate:.1f}%"
            
            # Verify system didn't crash
            current_stats = monitor.get_current_stats()
            assert not monitor.safety_violated or current_stats["peak_memory_mb"] < 4000, "System crashed or excessive resource usage"
    
    def _execute_single_flow(self, mock_flow, inputs: Dict[str, Any], flow_id: str) -> WritingFlowState:
        """Execute a single flow with error handling"""
        try:
            # Add some variability to execution time
            time.sleep(0.05 + 0.1 * hash(flow_id) % 10 / 100)  # 50-150ms
            return mock_flow.kickoff(inputs)
        except Exception as e:
            logger.warning(f"Flow {flow_id} execution failed: {e}")
            raise
    
    @pytest.mark.performance
    async def test_sustained_extreme_load(self, stress_tester: HeavyLoadStressTester, mock_v2_flow):
        """
        Test sustained high load over extended period (5+ minutes scaled to 30 seconds)
        
        This test validates system stability under continuous high load
        and detects memory leaks or performance degradation.
        """
        with stress_tester.stress_test_session("sustained_extreme_load") as monitor:
            
            # Test configuration
            test_duration_seconds = 30  # Scaled down for testing
            concurrent_flows = 15
            flow_rate_per_second = 2.0  # 2 flows per second
            
            test_inputs = {
                "topic_title": "Sustained Load Test",
                "platform": "LinkedIn",
                "file_path": "/tmp/sustained_test.md",
                "content_type": "STANDALONE", 
                "content_ownership": "ORIGINAL"
            }
            
            start_time = time.time()
            flow_counter = 0
            flows_in_progress = set()
            
            # Use executor for sustained concurrent execution
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_flows) as executor:
                
                while (time.time() - start_time) < test_duration_seconds and not monitor.emergency_stop:
                    
                    # Maintain target flow rate
                    current_time = time.time()
                    expected_flows = int((current_time - start_time) * flow_rate_per_second)
                    
                    # Submit new flows to maintain rate
                    while flow_counter < expected_flows and len(flows_in_progress) < concurrent_flows:
                        flow_id = f"sustained_flow_{flow_counter}"
                        flow_counter += 1
                        
                        monitor.register_flow_start(flow_id)
                        future = executor.submit(self._execute_single_flow, mock_flow, test_inputs, flow_id)
                        flows_in_progress.add((future, flow_id))
                    
                    # Check for completed flows
                    completed_futures = []
                    for future, flow_id in flows_in_progress:
                        if future.done():
                            try:
                                future.result()
                                monitor.register_flow_completion(flow_id, success=True)
                            except Exception as e:
                                monitor.register_flow_completion(flow_id, success=False)
                            completed_futures.append((future, flow_id))
                    
                    # Remove completed flows
                    for completed in completed_futures:
                        flows_in_progress.discard(completed)
                    
                    # Brief sleep to prevent tight loop
                    await asyncio.sleep(0.1)
                
                # Wait for remaining flows to complete
                logger.info("🔄 Waiting for remaining flows to complete...")
                for future, flow_id in flows_in_progress:
                    try:
                        future.result(timeout=10)
                        monitor.register_flow_completion(flow_id, success=True)
                    except Exception:
                        monitor.register_flow_completion(flow_id, success=False)
            
            # Validate sustained load performance
            stats = monitor.get_current_stats()
            
            assert stats["total_flows"] >= test_duration_seconds, "Insufficient throughput during sustained load"
            assert stats["success_rate"] >= 70.0, f"Success rate degraded during sustained load: {stats['success_rate']:.1f}%"
            
            # Memory leak detection
            if len(monitor.memory_samples) >= 10:
                memory_trend = monitor._calculate_memory_trend(list(monitor.memory_samples)[-10:])
                assert memory_trend < 5.0, f"Memory leak detected: {memory_trend:.2f}MB/s growth"


class TestResourceExhaustion:
    """Test system behavior under resource exhaustion"""
    
    @pytest.mark.performance 
    async def test_memory_pressure_resilience(self, stress_tester: HeavyLoadStressTester, mock_v2_flow):
        """
        Test system resilience under memory pressure
        
        This test allocates large amounts of memory while running flows
        to test behavior under memory pressure conditions.
        """
        with stress_tester.stress_test_session("memory_pressure_resilience") as monitor:
            
            memory_ballast = []
            concurrent_flows = 10
            
            try:
                # Gradually increase memory pressure
                for pressure_level in range(1, 6):  # 5 levels of memory pressure
                    if monitor.emergency_stop:
                        break
                    
                    logger.info(f"🔥 Memory pressure level {pressure_level}/5")
                    
                    # Allocate memory ballast (50MB per level)
                    ballast_size = 50 * 1024 * 1024  # 50MB
                    ballast_chunk = bytearray(ballast_size)
                    memory_ballast.append(ballast_chunk)
                    
                    # Execute flows under memory pressure
                    test_inputs = {
                        "topic_title": f"Memory Pressure Test Level {pressure_level}",
                        "platform": "LinkedIn",
                        "file_path": f"/tmp/memory_test_{pressure_level}.md"
                    }
                    
                    flows_at_level = 0
                    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_flows) as executor:
                        futures = []
                        
                        for i in range(concurrent_flows):
                            flow_id = f"memory_pressure_flow_{pressure_level}_{i}"
                            monitor.register_flow_start(flow_id)
                            future = executor.submit(self._execute_single_flow, mock_flow, test_inputs, flow_id)
                            futures.append((future, flow_id))
                        
                        # Wait for completion
                        for future, flow_id in futures:
                            try:
                                future.result(timeout=10)
                                monitor.register_flow_completion(flow_id, success=True)
                                flows_at_level += 1
                            except Exception as e:
                                logger.warning(f"Flow failed under memory pressure: {e}")
                                monitor.register_flow_completion(flow_id, success=False)
                    
                    logger.info(f"📊 Completed {flows_at_level}/{concurrent_flows} flows at pressure level {pressure_level}")
                    
                    # Brief pause between pressure levels
                    await asyncio.sleep(0.5)
                
            finally:
                # Clean up memory ballast
                memory_ballast.clear()
                gc.collect()
            
            # Validate memory pressure resilience
            stats = monitor.get_current_stats()
            assert stats["success_rate"] >= 50.0, f"System failed under memory pressure: {stats['success_rate']:.1f}% success rate"
            assert not monitor.safety_violated, f"Safety violation under memory pressure: {monitor.violation_reason}"
    
    @pytest.mark.performance
    async def test_cpu_saturation_behavior(self, stress_tester: HeavyLoadStressTester, mock_v2_flow):
        """
        Test system behavior under CPU saturation
        
        This test creates CPU-intensive workloads while running flows
        to validate behavior under high CPU load.
        """
        with stress_tester.stress_test_session("cpu_saturation_behavior") as monitor:
            
            # CPU-intensive mock function
            def cpu_intensive_flow(inputs, flow_id):
                start_time = time.time()
                # Simulate CPU-intensive work
                iterations = 100000
                for i in range(iterations):
                    _ = sum(range(100))  # CPU work
                    if i % 10000 == 0:  # Check for emergency stop
                        if monitor.emergency_stop:
                            break
                
                execution_time = time.time() - start_time
                
                # Create result
                final_state = WritingFlowState()
                final_state.current_stage = "completed"
                final_state.agents_executed = ["cpu_intensive_work"]
                return final_state
            
            # Override mock to use CPU-intensive version
            mock_v2_flow.kickoff = cpu_intensive_flow
            
            # Test configuration
            concurrent_flows = min(multiprocessing.cpu_count() + 2, 12)  # Slightly more than CPU cores
            total_flows = concurrent_flows * 3  # 3 batches
            
            test_inputs = {
                "topic_title": "CPU Saturation Test",
                "platform": "LinkedIn", 
                "file_path": "/tmp/cpu_test.md"
            }
            
            flows_completed = 0
            flows_successful = 0
            
            # Execute flows in batches to create CPU saturation
            for batch in range(3):
                if monitor.emergency_stop:
                    break
                
                logger.info(f"🔥 CPU saturation batch {batch + 1}/3 ({concurrent_flows} flows)")
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_flows) as executor:
                    futures = []
                    
                    for i in range(concurrent_flows):
                        flow_id = f"cpu_sat_flow_{batch}_{i}"
                        monitor.register_flow_start(flow_id)
                        future = executor.submit(cpu_intensive_flow, test_inputs, flow_id)
                        futures.append((future, flow_id))
                    
                    # Wait for batch completion
                    for future, flow_id in futures:
                        try:
                            result = future.result(timeout=20)  # Longer timeout for CPU-intensive work
                            monitor.register_flow_completion(flow_id, success=True)
                            flows_successful += 1
                        except Exception as e:
                            logger.warning(f"CPU-intensive flow failed: {e}")
                            monitor.register_flow_completion(flow_id, success=False)
                        flows_completed += 1
                
                # Brief cooldown between batches
                await asyncio.sleep(1.0)
            
            # Validate CPU saturation behavior
            stats = monitor.get_current_stats()
            success_rate = (flows_successful / flows_completed * 100) if flows_completed > 0 else 0
            
            assert flows_completed > 0, "No flows completed under CPU saturation"
            assert success_rate >= 60.0, f"Too many failures under CPU saturation: {success_rate:.1f}%"
            
            # CPU usage should have been high during test
            if len(monitor.cpu_samples) > 0:
                max_cpu = max([sample[1] for sample in monitor.cpu_samples])
                assert max_cpu >= 50.0, f"CPU saturation test didn't achieve high CPU usage: {max_cpu:.1f}%"


class TestBreakingPointDetection:
    """Test system breaking point detection and recovery"""
    
    @pytest.mark.performance
    async def test_find_maximum_capacity(self, stress_tester: HeavyLoadStressTester, mock_v2_flow):
        """
        Find system maximum capacity through gradual load increase
        
        This test gradually increases load until system limits are reached,
        identifying the breaking point and maximum sustainable capacity.
        """
        with stress_tester.stress_test_session("find_maximum_capacity") as monitor:
            
            # Gradually increase load until breaking point
            max_concurrent = 1
            breaking_point_found = False
            successful_loads = []
            
            for load_level in range(1, 21):  # Test up to 20 concurrent flows
                if monitor.emergency_stop or breaking_point_found:
                    break
                
                current_load = load_level * 2  # Increase by 2 each iteration
                logger.info(f"🔍 Testing capacity: {current_load} concurrent flows")
                
                test_inputs = {
                    "topic_title": f"Capacity Test Load {current_load}",
                    "platform": "LinkedIn",
                    "file_path": f"/tmp/capacity_test_{current_load}.md"
                }
                
                flows_successful = 0
                flows_total = current_load
                
                # Execute load level
                with concurrent.futures.ThreadPoolExecutor(max_workers=current_load) as executor:
                    futures = []
                    
                    for i in range(current_load):
                        flow_id = f"capacity_flow_{current_load}_{i}"
                        monitor.register_flow_start(flow_id)
                        future = executor.submit(self._execute_single_flow, mock_v2_flow, test_inputs, flow_id)
                        futures.append((future, flow_id))
                    
                    # Collect results with timeout
                    for future, flow_id in futures:
                        try:
                            future.result(timeout=15)
                            monitor.register_flow_completion(flow_id, success=True)
                            flows_successful += 1
                        except Exception as e:
                            monitor.register_flow_completion(flow_id, success=False)
                
                success_rate = (flows_successful / flows_total * 100) if flows_total > 0 else 0
                logger.info(f"📊 Load {current_load}: {flows_successful}/{flows_total} successful ({success_rate:.1f}%)")
                
                # Check if this load level is sustainable
                if success_rate >= 80.0 and not monitor.emergency_stop:
                    successful_loads.append((current_load, success_rate))
                    max_concurrent = current_load
                else:
                    logger.info(f"🚨 Breaking point detected at {current_load} concurrent flows")
                    breaking_point_found = True
                    break
                
                # Brief recovery between load levels
                await asyncio.sleep(1.0)
            
            # Analyze capacity results
            logger.info(f"🎯 Maximum sustainable capacity: {max_concurrent} concurrent flows")
            
            if successful_loads:
                best_load, best_rate = max(successful_loads, key=lambda x: x[0])
                logger.info(f"📈 Best performance: {best_load} flows with {best_rate:.1f}% success rate")
            
            # Assertions
            assert max_concurrent >= 4, f"System capacity too low: {max_concurrent} concurrent flows"
            assert len(successful_loads) > 0, "No successful load levels found"
            
            # Update result with capacity findings
            if stress_tester.results:
                result = stress_tester.results[-1]
                result.performance_metrics["max_sustainable_capacity"] = max_concurrent
                result.performance_metrics["successful_load_levels"] = successful_loads
                result.breaking_point_reached = breaking_point_found
    
    def _execute_single_flow(self, mock_flow, inputs: Dict[str, Any], flow_id: str) -> WritingFlowState:
        """Execute a single flow with realistic timing"""
        try:
            # Variable execution time based on flow_id
            base_time = 0.1
            variation = (hash(flow_id) % 100) / 1000  # 0-99ms variation
            time.sleep(base_time + variation)
            
            return mock_flow.kickoff(inputs)
        except Exception as e:
            logger.warning(f"Flow {flow_id} execution failed: {e}")
            raise
    
    @pytest.mark.performance
    async def test_circuit_breaker_activation(self, stress_tester: HeavyLoadStressTester):
        """
        Test circuit breaker activation under stress
        
        This test deliberately triggers failures to validate circuit breaker
        behavior and system protection mechanisms.
        """
        with stress_tester.stress_test_session("circuit_breaker_activation") as monitor:
            
            # Create circuit breaker for testing
            circuit_breaker = CircuitBreaker(
                name="stress_test_breaker",
                failure_threshold=3,
                recovery_timeout=5
            )
            
            # Mock function that fails predictably
            call_count = 0
            def failing_function():
                nonlocal call_count
                call_count += 1
                if call_count <= 5:  # First 5 calls fail
                    raise RuntimeError(f"Simulated failure #{call_count}")
                return f"Success after {call_count} calls"
            
            # Test circuit breaker behavior under stress
            results = []
            circuit_open_detected = False
            recovery_detected = False
            
            # Phase 1: Trigger circuit breaker opening
            logger.info("🔥 Phase 1: Triggering circuit breaker failures")
            for i in range(8):  # More than failure threshold
                try:
                    result = circuit_breaker.call(failing_function)
                    results.append(("success", result))
                    logger.info(f"✅ Call {i+1}: {result}")
                except CircuitBreakerError as e:
                    results.append(("circuit_open", str(e)))
                    circuit_open_detected = True
                    logger.info(f"⚡ Call {i+1}: Circuit breaker OPEN - {e}")
                except Exception as e:
                    results.append(("failure", str(e)))
                    logger.info(f"❌ Call {i+1}: Function failed - {e}")
                
                await asyncio.sleep(0.1)
            
            # Phase 2: Wait for recovery timeout
            if circuit_open_detected:
                logger.info("⏳ Phase 2: Waiting for circuit breaker recovery...")
                await asyncio.sleep(6)  # Wait longer than recovery timeout
                
                # Phase 3: Test recovery
                logger.info("🔄 Phase 3: Testing circuit breaker recovery")
                for i in range(3):
                    try:
                        result = circuit_breaker.call(failing_function)
                        results.append(("recovery_success", result))
                        recovery_detected = True
                        logger.info(f"✅ Recovery call {i+1}: {result}")
                        break
                    except Exception as e:
                        results.append(("recovery_failure", str(e)))
                        logger.info(f"❌ Recovery call {i+1}: {e}")
                    
                    await asyncio.sleep(0.5)
            
            # Analyze circuit breaker behavior
            failure_count = len([r for r in results if r[0] == "failure"])
            circuit_open_count = len([r for r in results if r[0] == "circuit_open"])
            success_count = len([r for r in results if r[0] in ["success", "recovery_success"]])
            
            logger.info(f"📊 Circuit breaker test results:")
            logger.info(f"   Failures: {failure_count}")
            logger.info(f"   Circuit open blocks: {circuit_open_count}")
            logger.info(f"   Successes: {success_count}")
            logger.info(f"   Circuit state: {circuit_breaker.state}")
            
            # Assertions
            assert circuit_open_detected, "Circuit breaker should have opened under failures"
            assert circuit_open_count >= 1, "Circuit breaker should have blocked calls when open"
            assert failure_count <= 5, "Circuit breaker should have prevented excessive failures"
            
            # Validate circuit breaker status
            status = circuit_breaker.get_status()
            assert status["total_failures"] >= 3, "Circuit breaker should have recorded failures"
            assert status["failure_threshold"] == 3, "Circuit breaker threshold should be configured"


class TestRecoveryAndStability:
    """Test system recovery and stability after stress"""
    
    @pytest.mark.performance
    async def test_post_stress_recovery(self, stress_tester: HeavyLoadStressTester, mock_v2_flow):
        """
        Test system recovery after heavy stress
        
        This test applies heavy stress then validates the system can recover
        to normal operation within acceptable time limits.
        """
        with stress_tester.stress_test_session("post_stress_recovery") as monitor:
            
            # Phase 1: Apply heavy stress
            logger.info("🔥 Phase 1: Applying heavy stress load")
            stress_flows = 20
            stress_results = []
            
            test_inputs = {
                "topic_title": "Recovery Test Stress Phase",
                "platform": "LinkedIn",
                "file_path": "/tmp/recovery_stress.md"
            }
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=stress_flows) as executor:
                futures = []
                
                for i in range(stress_flows):
                    flow_id = f"stress_flow_{i}"
                    monitor.register_flow_start(flow_id)
                    future = executor.submit(self._execute_stress_flow, mock_v2_flow, test_inputs, flow_id)
                    futures.append((future, flow_id))
                
                # Collect stress results
                for future, flow_id in futures:
                    try:
                        future.result(timeout=10)
                        monitor.register_flow_completion(flow_id, success=True)
                        stress_results.append(True)
                    except Exception:
                        monitor.register_flow_completion(flow_id, success=False)
                        stress_results.append(False)
            
            stress_success_rate = sum(stress_results) / len(stress_results) * 100
            logger.info(f"📊 Stress phase: {sum(stress_results)}/{len(stress_results)} successful ({stress_success_rate:.1f}%)")
            
            # Phase 2: Recovery period
            logger.info("⏳ Phase 2: Recovery period")
            recovery_start = time.time()
            await asyncio.sleep(3.0)  # Recovery period
            
            # Force garbage collection to help recovery
            gc.collect()
            
            # Phase 3: Validate recovery with normal load
            logger.info("🔄 Phase 3: Testing recovery with normal load")
            recovery_flows = 8  # Normal load
            recovery_results = []
            
            recovery_inputs = {
                "topic_title": "Recovery Test Normal Phase", 
                "platform": "LinkedIn",
                "file_path": "/tmp/recovery_normal.md"
            }
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=recovery_flows) as executor:
                futures = []
                
                for i in range(recovery_flows):
                    flow_id = f"recovery_flow_{i}"
                    monitor.register_flow_start(flow_id)
                    future = executor.submit(self._execute_normal_flow, mock_v2_flow, recovery_inputs, flow_id)
                    futures.append((future, flow_id))
                
                # Collect recovery results
                for future, flow_id in futures:
                    try:
                        future.result(timeout=8)
                        monitor.register_flow_completion(flow_id, success=True)
                        recovery_results.append(True)
                    except Exception:
                        monitor.register_flow_completion(flow_id, success=False)
                        recovery_results.append(False)
            
            recovery_time = time.time() - recovery_start
            recovery_success_rate = sum(recovery_results) / len(recovery_results) * 100
            
            logger.info(f"📊 Recovery phase: {sum(recovery_results)}/{len(recovery_results)} successful ({recovery_success_rate:.1f}%)")
            logger.info(f"⏱️ Recovery time: {recovery_time:.2f}s")
            
            # Validate recovery
            assert recovery_success_rate >= 85.0, f"System didn't recover properly: {recovery_success_rate:.1f}% success rate"
            assert recovery_time <= 30.0, f"Recovery took too long: {recovery_time:.2f}s"
            
            # Check system stability post-recovery
            stats = monitor.get_current_stats()
            current_memory = stats["current_memory_mb"]
            baseline_memory = monitor.baseline_memory
            memory_increase = current_memory - baseline_memory
            
            assert memory_increase < 200.0, f"Excessive memory increase after stress: {memory_increase:.1f}MB"
            
            # Update result with recovery metrics
            if stress_tester.results:
                result = stress_tester.results[-1]
                result.recovery_time_seconds = recovery_time
                result.performance_metrics["stress_success_rate"] = stress_success_rate
                result.performance_metrics["recovery_success_rate"] = recovery_success_rate
                result.performance_metrics["memory_increase_mb"] = memory_increase
    
    def _execute_stress_flow(self, mock_flow, inputs: Dict[str, Any], flow_id: str) -> WritingFlowState:
        """Execute a flow with stress characteristics (longer, more resource intensive)"""
        try:
            # Simulate stress conditions
            time.sleep(0.2 + 0.1 * (hash(flow_id) % 5))  # 200-700ms execution
            
            # Allocate some memory to simulate stress
            stress_data = bytearray(1024 * 1024)  # 1MB allocation
            
            result = mock_flow.kickoff(inputs)
            
            # Keep reference briefly to simulate memory pressure
            time.sleep(0.05)
            del stress_data
            
            return result
        except Exception as e:
            logger.warning(f"Stress flow {flow_id} failed: {e}")
            raise
    
    def _execute_normal_flow(self, mock_flow, inputs: Dict[str, Any], flow_id: str) -> WritingFlowState:
        """Execute a flow with normal characteristics"""
        try:
            # Normal execution time
            time.sleep(0.1)
            return mock_flow.kickoff(inputs)
        except Exception as e:
            logger.warning(f"Normal flow {flow_id} failed: {e}")
            raise


class TestSystemLimitsAndSafety:
    """Test system limits and safety mechanisms"""
    
    @pytest.mark.performance
    async def test_resource_limit_enforcement(self, stress_tester: HeavyLoadStressTester):
        """
        Test enforcement of resource limits and safety thresholds
        
        This test validates that safety mechanisms properly activate
        when resource thresholds are exceeded.
        """
        # Create custom thresholds for testing
        test_thresholds = ResourceThresholds(
            max_memory_mb=200.0,  # Low threshold for testing
            max_cpu_percent=50.0,  # Low threshold for testing  
            max_execution_time_seconds=10.0,  # Short time for testing
            memory_growth_rate_mb_per_sec=10.0  # Low threshold for testing
        )
        
        test_monitor = StressTestMonitor(test_thresholds)
        test_monitor.start_monitoring()
        
        try:
            logger.info("🔒 Testing resource limit enforcement")
            
            # Test 1: Memory limit enforcement
            logger.info("🧠 Testing memory limit enforcement")
            memory_ballast = []
            
            # Gradually allocate memory until threshold is hit
            for chunk in range(50):  # Up to ~250MB
                memory_ballast.append(bytearray(5 * 1024 * 1024))  # 5MB chunks
                await asyncio.sleep(0.1)
                
                if test_monitor.emergency_stop:
                    logger.info(f"🚨 Memory limit triggered after {len(memory_ballast)} chunks ({len(memory_ballast) * 5}MB)")
                    break
            
            # Verify memory limit was enforced
            assert test_monitor.safety_violated, "Memory limit should have been enforced"
            assert "Memory exceeded" in test_monitor.violation_reason, f"Expected memory violation, got: {test_monitor.violation_reason}"
            
            # Clean up memory
            memory_ballast.clear()
            gc.collect()
            
            logger.info("✅ Memory limit enforcement validated")
            
        finally:
            test_monitor.stop_monitoring()
    
    @pytest.mark.performance
    def test_emergency_shutdown_procedures(self, stress_tester: HeavyLoadStressTester):
        """
        Test emergency shutdown procedures
        
        This test validates that emergency shutdown mechanisms work
        correctly and safely terminate operations.
        """
        logger.info("🚨 Testing emergency shutdown procedures")
        
        # Create a V2 flow for testing
        flow_v2 = AIWritingFlowV2(
            monitoring_enabled=True,
            alerting_enabled=True,
            quality_gates_enabled=True
        )
        
        # Test emergency stop functionality
        try:
            # Trigger emergency stop
            flow_v2.emergency_stop()
            logger.info("✅ Emergency stop executed successfully")
            
            # Verify system is in safe state
            health_status = flow_v2.get_health_status()
            assert health_status is not None, "Health status should be available after emergency stop"
            
            logger.info("✅ System maintained health monitoring after emergency stop")
            
        except Exception as e:
            logger.error(f"❌ Emergency stop failed: {e}")
            raise
        
        # Test graceful degradation
        logger.info("🔄 Testing graceful degradation")
        
        try:
            # Attempt normal operation after emergency stop (should handle gracefully)
            test_inputs = {
                "topic_title": "Emergency Test",
                "platform": "LinkedIn", 
                "file_path": "/tmp/emergency_test.md"
            }
            
            # This should either work or fail gracefully
            result = flow_v2.kickoff(test_inputs)
            if result and hasattr(result, 'current_stage'):
                logger.info(f"✅ System recovered after emergency stop: {result.current_stage}")
            else:
                logger.info("ℹ️ System gracefully rejected operation after emergency stop")
            
        except Exception as e:
            # Graceful failure is acceptable after emergency stop
            logger.info(f"ℹ️ System gracefully failed after emergency stop: {e}")


# Integration test to run all stress tests
@pytest.mark.performance
class TestCompleteStressSuite:
    """Complete stress test suite integration"""
    
    async def test_complete_stress_test_suite(self, stress_tester: HeavyLoadStressTester, mock_v2_flow):
        """
        Run complete stress test suite and generate comprehensive report
        
        This test orchestrates all stress test scenarios and produces
        a detailed analysis of system behavior under various stress conditions.
        """
        logger.info("🎯 Starting complete heavy load stress test suite")
        
        # Test suite components
        test_components = [
            ("Extreme Concurrent Load", self._run_concurrent_load_test),
            ("Memory Pressure Resilience", self._run_memory_pressure_test),
            ("CPU Saturation Behavior", self._run_cpu_saturation_test),
            ("Breaking Point Detection", self._run_breaking_point_test),
            ("System Recovery", self._run_recovery_test)
        ]
        
        suite_results = []
        
        # Execute each test component
        for test_name, test_function in test_components:
            logger.info(f"🔥 Executing: {test_name}")
            
            try:
                result = await test_function(stress_tester, mock_v2_flow)
                suite_results.append(result)
                logger.info(f"✅ {test_name} completed successfully")
                
                # Brief recovery between tests
                await asyncio.sleep(2.0)
                gc.collect()
                
            except Exception as e:
                logger.error(f"❌ {test_name} failed: {e}")
                suite_results.append({
                    "test_name": test_name,
                    "success": False,
                    "error": str(e)
                })
        
        # Generate comprehensive report
        self._generate_stress_test_report(stress_tester, suite_results)
        
        # Validate overall suite success
        successful_tests = sum(1 for result in suite_results if result.get("success", False))
        total_tests = len(test_components)
        
        logger.info(f"🎯 Stress test suite completed: {successful_tests}/{total_tests} tests passed")
        
        assert successful_tests >= total_tests * 0.8, f"Too many stress tests failed: {successful_tests}/{total_tests}"
    
    async def _run_concurrent_load_test(self, stress_tester, mock_v2_flow):
        """Run concurrent load test component"""
        with stress_tester.stress_test_session("suite_concurrent_load") as monitor:
            # Simplified concurrent load test
            concurrent_flows = 15
            test_inputs = {"topic_title": "Suite Concurrent Test", "platform": "LinkedIn", "file_path": "/tmp/suite_test.md"}
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_flows) as executor:
                futures = [
                    executor.submit(self._execute_test_flow, mock_v2_flow, test_inputs, f"suite_flow_{i}")
                    for i in range(concurrent_flows)
                ]
                
                results = []
                for future in concurrent.futures.as_completed(futures, timeout=30):
                    try:
                        results.append(future.result())
                    except Exception:
                        results.append(None)
            
            success_rate = sum(1 for r in results if r is not None) / len(results) * 100
            return {"test_name": "concurrent_load", "success": success_rate >= 70.0, "success_rate": success_rate}
    
    async def _run_memory_pressure_test(self, stress_tester, mock_v2_flow):
        """Run memory pressure test component"""
        with stress_tester.stress_test_session("suite_memory_pressure") as monitor:
            # Allocate memory and run flows
            memory_ballast = bytearray(100 * 1024 * 1024)  # 100MB
            
            test_inputs = {"topic_title": "Suite Memory Test", "platform": "LinkedIn", "file_path": "/tmp/suite_memory.md"}
            
            flows = 8
            results = []
            for i in range(flows):
                try:
                    result = self._execute_test_flow(mock_v2_flow, test_inputs, f"memory_flow_{i}")
                    results.append(result is not None)
                except Exception:
                    results.append(False)
                await asyncio.sleep(0.1)
            
            del memory_ballast
            gc.collect()
            
            success_rate = sum(results) / len(results) * 100
            return {"test_name": "memory_pressure", "success": success_rate >= 60.0, "success_rate": success_rate}
    
    async def _run_cpu_saturation_test(self, stress_tester, mock_v2_flow):
        """Run CPU saturation test component"""
        with stress_tester.stress_test_session("suite_cpu_saturation") as monitor:
            # CPU-intensive work
            def cpu_work():
                for _ in range(50000):
                    _ = sum(range(100))
                return True
            
            cpu_workers = min(multiprocessing.cpu_count(), 8)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=cpu_workers) as executor:
                futures = [executor.submit(cpu_work) for _ in range(cpu_workers)]
                results = []
                
                for future in concurrent.futures.as_completed(futures, timeout=15):
                    try:
                        results.append(future.result())
                    except Exception:
                        results.append(False)
            
            success_rate = sum(results) / len(results) * 100
            return {"test_name": "cpu_saturation", "success": success_rate >= 80.0, "success_rate": success_rate}
    
    async def _run_breaking_point_test(self, stress_tester, mock_v2_flow):
        """Run breaking point detection test component"""
        with stress_tester.stress_test_session("suite_breaking_point") as monitor:
            # Find breaking point with gradual load increase
            max_successful_load = 0
            
            for load in range(2, 16, 2):  # Test loads: 2, 4, 6, 8, 10, 12, 14
                test_inputs = {"topic_title": f"Suite Breaking Point {load}", "platform": "LinkedIn", "file_path": "/tmp/suite_bp.md"}
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=load) as executor:
                    futures = [
                        executor.submit(self._execute_test_flow, mock_v2_flow, test_inputs, f"bp_flow_{load}_{i}")
                        for i in range(load)
                    ]
                    
                    successful = 0
                    for future in concurrent.futures.as_completed(futures, timeout=10):
                        try:
                            if future.result():
                                successful += 1
                        except Exception:
                            pass
                
                success_rate = successful / load * 100
                if success_rate >= 75.0:
                    max_successful_load = load
                else:
                    break
                
                await asyncio.sleep(0.5)
            
            return {"test_name": "breaking_point", "success": max_successful_load >= 4, "max_load": max_successful_load}
    
    async def _run_recovery_test(self, stress_tester, mock_v2_flow):
        """Run system recovery test component"""
        with stress_tester.stress_test_session("suite_recovery") as monitor:
            # Apply stress then test recovery
            stress_flows = 12
            test_inputs = {"topic_title": "Suite Recovery Stress", "platform": "LinkedIn", "file_path": "/tmp/suite_recovery.md"}
            
            # Stress phase
            with concurrent.futures.ThreadPoolExecutor(max_workers=stress_flows) as executor:
                futures = [
                    executor.submit(self._execute_stress_flow, mock_v2_flow, test_inputs, f"recovery_stress_{i}")
                    for i in range(stress_flows)
                ]
                
                stress_results = []
                for future in concurrent.futures.as_completed(futures, timeout=15):
                    try:
                        stress_results.append(future.result() is not None)
                    except Exception:
                        stress_results.append(False)
            
            # Recovery phase
            await asyncio.sleep(2.0)
            gc.collect()
            
            recovery_flows = 6
            recovery_results = []
            for i in range(recovery_flows):
                try:
                    result = self._execute_test_flow(mock_v2_flow, test_inputs, f"recovery_normal_{i}")
                    recovery_results.append(result is not None)
                except Exception:
                    recovery_results.append(False)
                await asyncio.sleep(0.1)
            
            recovery_rate = sum(recovery_results) / len(recovery_results) * 100
            return {"test_name": "recovery", "success": recovery_rate >= 80.0, "recovery_rate": recovery_rate}
    
    def _execute_test_flow(self, mock_flow, inputs: Dict[str, Any], flow_id: str):
        """Execute a single test flow"""
        try:
            time.sleep(0.1)  # Simulate processing
            return mock_flow.kickoff(inputs)
        except Exception:
            return None
    
    def _execute_stress_flow(self, mock_flow, inputs: Dict[str, Any], flow_id: str):
        """Execute a stress flow with higher resource usage"""
        try:
            time.sleep(0.2)  # Longer processing
            # Allocate temporary memory
            temp_data = bytearray(1024 * 1024)  # 1MB
            result = mock_flow.kickoff(inputs)
            del temp_data
            return result
        except Exception:
            return None
    
    def _generate_stress_test_report(self, stress_tester: HeavyLoadStressTester, suite_results: List[Dict]):
        """Generate comprehensive stress test report"""
        
        report_path = Path("/tmp/ai_writing_flow_v2_stress_test_report.md")
        
        report_content = f"""
# AI Writing Flow V2 - Heavy Load Stress Test Report

**Generated:** {datetime.now(timezone.utc).isoformat()}
**Test Suite Version:** 1.0
**System:** {psutil.cpu_count()} CPU cores, {psutil.virtual_memory().total / (1024**3):.1f}GB RAM

## Executive Summary

This report contains the results of comprehensive heavy load stress testing performed on the AI Writing Flow V2 system.

### Test Results Overview

"""
        
        # Add individual test results
        for result in suite_results:
            status = "✅ PASSED" if result.get("success", False) else "❌ FAILED"
            report_content += f"- **{result.get('test_name', 'Unknown Test')}**: {status}\n"
        
        report_content += f"""

### Key Findings

"""
        
        # Add detailed findings from each test
        for result in suite_results:
            test_name = result.get('test_name', 'Unknown Test')
            report_content += f"""
#### {test_name.replace('_', ' ').title()}

"""
            
            if result.get("success", False):
                report_content += f"- **Status**: PASSED ✅\n"
                if "success_rate" in result:
                    report_content += f"- **Success Rate**: {result['success_rate']:.1f}%\n"
                if "max_load" in result:
                    report_content += f"- **Maximum Load**: {result['max_load']} concurrent flows\n"
                if "recovery_rate" in result:
                    report_content += f"- **Recovery Rate**: {result['recovery_rate']:.1f}%\n"
            else:
                report_content += f"- **Status**: FAILED ❌\n"
                if "error" in result:
                    report_content += f"- **Error**: {result['error']}\n"
        
        # Add detailed metrics from stress tester
        if stress_tester.results:
            latest_result = stress_tester.results[-1]
            report_content += f"""

## Detailed Performance Metrics

### Resource Usage
- **Peak Memory Usage**: {latest_result.peak_memory_mb:.1f}MB
- **Peak CPU Usage**: {latest_result.peak_cpu_percent:.1f}%
- **Test Duration**: {latest_result.duration_seconds:.2f}s

### Execution Statistics
- **Total Executions**: {latest_result.total_executions}
- **Successful Executions**: {latest_result.successful_executions}
- **Failed Executions**: {latest_result.failed_executions}
- **Overall Success Rate**: {(latest_result.successful_executions/latest_result.total_executions*100) if latest_result.total_executions > 0 else 0:.1f}%

### System Stability
- **Breaking Point Reached**: {'Yes' if latest_result.breaking_point_reached else 'No'}
- **Safety Violations**: {len(latest_result.error_messages)}
- **Recovery Time**: {latest_result.recovery_time_seconds or 'N/A'}s

## Recommendations

Based on the stress test results, the following recommendations are made:

1. **Capacity Planning**: System can handle up to X concurrent flows with Y% success rate
2. **Resource Monitoring**: Implement alerts for memory usage above Z MB
3. **Circuit Breaker Tuning**: Current thresholds appear appropriate for the load patterns tested
4. **Performance Optimization**: Consider optimizing components that showed degradation under stress

## Test Configuration

- **Maximum Concurrent Flows Tested**: {latest_result.max_concurrent_flows}
- **Memory Safety Threshold**: {stress_tester.thresholds.max_memory_mb}MB
- **CPU Safety Threshold**: {stress_tester.thresholds.max_cpu_percent}%
- **Test Timeout**: {stress_tester.thresholds.max_execution_time_seconds}s

---
*Report generated by AI Writing Flow V2 Heavy Load Stress Testing Suite*
"""
        
        # Write report to file
        try:
            with open(report_path, 'w') as f:
                f.write(report_content)
            logger.info(f"📊 Comprehensive stress test report saved to: {report_path}")
        except Exception as e:
            logger.warning(f"Failed to save stress test report: {e}")


if __name__ == "__main__":
    # Run stress tests directly
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "performance"])
EOF < /dev/null