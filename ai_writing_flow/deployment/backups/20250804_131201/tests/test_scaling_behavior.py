"""
Scaling Behavior Tests for AI Writing Flow V2

Tests system scaling characteristics, identifies bottlenecks,
and provides production capacity planning data.

Comprehensive test suite covering:
- Linear scaling validation (1→2→4→8→10 flows)
- Resource usage scaling patterns  
- Performance degradation detection
- Bottleneck identification
- Capacity planning metrics
"""

import asyncio
import gc
import logging
import os
import psutil
import pytest
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from unittest.mock import AsyncMock, Mock, patch

import structlog

from src.ai_writing_flow.adapters.knowledge_adapter import (
    KnowledgeAdapter,
    SearchStrategy,
    KnowledgeResponse
)

# Configure test logging
logger = structlog.get_logger(__name__)


@dataclass
class ScalingMetrics:
    """Metrics for scaling behavior analysis"""
    flow_count: int
    
    # Performance metrics
    total_duration_ms: float
    average_response_time_ms: float
    throughput_ops_per_sec: float
    
    # Resource metrics
    memory_usage_mb: float
    memory_delta_mb: float
    cpu_percent: float
    thread_count: int
    
    # Efficiency metrics
    efficiency_ratio: float  # throughput per flow
    resource_efficiency: float  # ops per MB
    
    # Quality metrics
    success_rate: float
    error_count: int
    
    def __post_init__(self):
        """Calculate derived metrics"""
        if self.flow_count > 0:
            self.efficiency_ratio = self.throughput_ops_per_sec / self.flow_count
            if self.memory_usage_mb > 0:
                self.resource_efficiency = self.throughput_ops_per_sec / self.memory_usage_mb
            else:
                self.resource_efficiency = 0.0
        else:
            self.efficiency_ratio = 0.0
            self.resource_efficiency = 0.0


@dataclass 
class ScalingTestResult:
    """Complete scaling test results"""
    test_name: str
    metrics: List[ScalingMetrics] = field(default_factory=list)
    bottlenecks: List[str] = field(default_factory=list)
    scaling_efficiency: float = 0.0
    max_sustainable_flows: int = 0
    capacity_recommendations: List[str] = field(default_factory=list)
    
    def analyze_scaling_characteristics(self):
        """Analyze scaling patterns and identify bottlenecks"""
        if len(self.metrics) < 2:
            return
            
        # Calculate scaling efficiency
        throughputs = [m.throughput_ops_per_sec for m in self.metrics]
        flow_counts = [m.flow_count for m in self.metrics]
        
        # Linear scaling would have constant efficiency ratio
        efficiency_ratios = [m.efficiency_ratio for m in self.metrics]
        efficiency_variance = statistics.variance(efficiency_ratios) if len(efficiency_ratios) > 1 else 0
        
        # Good scaling: low variance in efficiency
        self.scaling_efficiency = max(0, 1.0 - (efficiency_variance / efficiency_ratios[0]**2))
        
        # Find bottlenecks
        self._identify_bottlenecks()
        
        # Determine capacity
        self._calculate_capacity_limits()
    
    def _identify_bottlenecks(self):
        """Identify system bottlenecks from metrics"""
        self.bottlenecks = []
        
        for i, metric in enumerate(self.metrics[1:], 1):
            prev_metric = self.metrics[i-1]
            
            # Memory bottleneck: >2x memory growth
            memory_growth_ratio = metric.memory_usage_mb / prev_metric.memory_usage_mb
            if memory_growth_ratio > 2.0:
                self.bottlenecks.append(f"Memory bottleneck at {metric.flow_count} flows: {memory_growth_ratio:.1f}x growth")
            
            # CPU bottleneck: >90% utilization
            if metric.cpu_percent > 90:
                self.bottlenecks.append(f"CPU bottleneck at {metric.flow_count} flows: {metric.cpu_percent:.1f}% utilization")
            
            # Thread bottleneck: exponential thread growth
            thread_growth_ratio = metric.thread_count / prev_metric.thread_count
            if thread_growth_ratio > 1.5:
                self.bottlenecks.append(f"Thread bottleneck at {metric.flow_count} flows: {thread_growth_ratio:.1f}x threads")
            
            # Performance cliff: >50% efficiency drop
            efficiency_drop = (prev_metric.efficiency_ratio - metric.efficiency_ratio) / prev_metric.efficiency_ratio
            if efficiency_drop > 0.5:
                self.bottlenecks.append(f"Performance cliff at {metric.flow_count} flows: {efficiency_drop:.1%} efficiency drop")
    
    def _calculate_capacity_limits(self):
        """Calculate maximum sustainable flow capacity"""
        # Find last metric with >80% efficiency
        for metric in reversed(self.metrics):
            if metric.efficiency_ratio > (self.metrics[0].efficiency_ratio * 0.8):
                self.max_sustainable_flows = metric.flow_count
                break
        
        # Generate capacity recommendations
        if self.max_sustainable_flows > 0:
            self.capacity_recommendations.append(
                f"Maximum sustainable concurrent flows: {self.max_sustainable_flows}"
            )
        
        last_metric = self.metrics[-1]
        self.capacity_recommendations.extend([
            f"Peak memory usage: {last_metric.memory_usage_mb:.1f} MB",
            f"Peak CPU utilization: {last_metric.cpu_percent:.1f}%",
            f"Scaling efficiency: {self.scaling_efficiency:.1%}",
            f"Resource efficiency: {last_metric.resource_efficiency:.2f} ops/MB"
        ])


class ScalingTestHarness:
    """Test harness for scaling behavior validation"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.baseline_memory = None
        self.test_adapters: List[KnowledgeAdapter] = []
    
    async def setup_test_environment(self, flow_count: int) -> List[KnowledgeAdapter]:
        """Setup test environment with specified number of flows"""
        adapters = []
        
        for i in range(flow_count):
            adapter = KnowledgeAdapter(
                strategy=SearchStrategy.HYBRID,
                kb_api_url=f"http://localhost:808{i % 3 + 2}",  # Distribute across mock endpoints
                timeout=5.0,
                max_retries=2
            )
            adapters.append(adapter)
        
        self.test_adapters.extend(adapters)
        return adapters
    
    async def cleanup_test_environment(self):
        """Cleanup test resources"""
        for adapter in self.test_adapters:
            try:
                await adapter.close()
            except Exception as e:
                logger.warning("Error closing adapter", error=str(e))
        
        self.test_adapters.clear()
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.1)  # Allow cleanup
    
    def capture_baseline_metrics(self):
        """Capture baseline system metrics"""
        self.baseline_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        logger.info("Baseline metrics captured", baseline_memory_mb=self.baseline_memory)
    
    def capture_system_metrics(self, flow_count: int, duration_ms: float, 
                             throughput: float, success_rate: float, error_count: int) -> ScalingMetrics:
        """Capture comprehensive system metrics"""
        current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        memory_delta = current_memory - (self.baseline_memory or 0)
        
        return ScalingMetrics(
            flow_count=flow_count,
            total_duration_ms=duration_ms,
            average_response_time_ms=duration_ms / max(1, throughput),
            throughput_ops_per_sec=throughput,
            memory_usage_mb=current_memory,
            memory_delta_mb=memory_delta,
            cpu_percent=self.process.cpu_percent(),
            thread_count=threading.active_count(),
            efficiency_ratio=0.0,  # Calculated in post_init
            resource_efficiency=0.0,  # Calculated in post_init
            success_rate=success_rate,
            error_count=error_count
        )


@pytest.fixture
async def scaling_harness():
    """Fixture providing scaling test harness"""
    harness = ScalingTestHarness()
    harness.capture_baseline_metrics()
    yield harness
    await harness.cleanup_test_environment()


class TestLinearScalingValidation:
    """Test linear scaling characteristics: 1→2→4→8→10 flows"""
    
    @pytest.mark.asyncio
    @pytest.mark.performance 
    async def test_progressive_flow_scaling(self, scaling_harness):
        """Test scaling behavior with progressive flow count increase"""
        flow_counts = [1, 2, 4, 8, 10]
        result = ScalingTestResult(test_name="progressive_flow_scaling")
        
        for flow_count in flow_counts:
            logger.info("Testing scaling", flow_count=flow_count)
            
            # Setup adapters
            adapters = await scaling_harness.setup_test_environment(flow_count)
            
            # Mock successful responses
            mock_response = {
                "results": [
                    {
                        "content": f"Test content for flow {i}",
                        "score": 0.95,
                        "metadata": {"source": f"test-{i}.md"}
                    } for i in range(3)
                ]
            }
            
            success_count = 0
            error_count = 0
            
            with patch('aiohttp.ClientSession.post') as mock_post:
                mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
                mock_post.return_value.__aenter__.return_value.status = 200
                
                start_time = time.time()
                
                # Execute concurrent searches
                tasks = []
                for adapter in adapters:
                    task = adapter.search(f"scaling test query {len(tasks)}")
                    tasks.append(task)
                
                # Wait for completion and count results
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                
                # Count successes and errors
                for result_item in results:
                    if isinstance(result_item, Exception):
                        error_count += 1
                    else:
                        success_count += 1
                
                # Calculate metrics
                total_operations = len(tasks)
                throughput = total_operations / ((end_time - start_time) or 0.001)
                success_rate = success_count / total_operations if total_operations > 0 else 0
                
                metrics = scaling_harness.capture_system_metrics(
                    flow_count, duration_ms, throughput, success_rate, error_count
                )
                
                result.metrics.append(metrics)
                
                logger.info("Scaling test completed",
                           flow_count=flow_count,
                           duration_ms=duration_ms, 
                           throughput=throughput,
                           success_rate=success_rate,
                           memory_mb=metrics.memory_usage_mb)
            
            # Cleanup before next iteration
            await scaling_harness.cleanup_test_environment()
            await asyncio.sleep(0.1)  # Brief pause between tests
        
        # Analyze results
        result.analyze_scaling_characteristics()
        
        # Assertions for linear scaling
        assert len(result.metrics) == len(flow_counts)
        assert result.scaling_efficiency > 0.8, f"Poor scaling efficiency: {result.scaling_efficiency:.2%}"
        assert result.max_sustainable_flows >= 8, f"Low sustainable capacity: {result.max_sustainable_flows}"
        
        # Log results for capacity planning
        logger.info("Scaling analysis complete",
                   scaling_efficiency=result.scaling_efficiency,
                   max_flows=result.max_sustainable_flows,
                   bottlenecks=result.bottlenecks)


class TestResourceScalingPatterns:
    """Test resource usage patterns with increasing load"""
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_memory_scaling_pattern(self, scaling_harness):
        """Test memory usage scaling with concurrent flows"""
        flow_counts = [1, 3, 6, 10]
        memory_usage = []
        
        for flow_count in flow_counts:
            adapters = await scaling_harness.setup_test_environment(flow_count)
            
            # Create memory pressure with multiple operations
            tasks = []
            for adapter in adapters:
                for i in range(3):  # 3 operations per adapter
                    task = adapter.search(f"memory test query {i}")
                    tasks.append(task)
            
            with patch('aiohttp.ClientSession.post') as mock_post:
                mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={"results": []})
                mock_post.return_value.__aenter__.return_value.status = 200
                
                await asyncio.gather(*tasks, return_exceptions=True)
            
            current_memory = scaling_harness.process.memory_info().rss / 1024 / 1024
            memory_usage.append((flow_count, current_memory))
            
            await scaling_harness.cleanup_test_environment()
            gc.collect()
            await asyncio.sleep(0.2)
        
        # Analyze memory scaling
        memory_growth_rates = []
        for i in range(1, len(memory_usage)):
            prev_flows, prev_memory = memory_usage[i-1]
            curr_flows, curr_memory = memory_usage[i]
            
            flow_ratio = curr_flows / prev_flows
            memory_ratio = curr_memory / prev_memory
            growth_rate = memory_ratio / flow_ratio
            memory_growth_rates.append(growth_rate)
        
        # Memory should scale sub-linearly (growth rate < 1.5)
        avg_growth_rate = statistics.mean(memory_growth_rates)
        assert avg_growth_rate < 1.5, f"Memory scaling too aggressive: {avg_growth_rate:.2f}"
        
        logger.info("Memory scaling validated",
                   memory_usage=memory_usage,
                   avg_growth_rate=avg_growth_rate)
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cpu_utilization_scaling(self, scaling_harness):
        """Test CPU utilization patterns under increasing load"""
        flow_counts = [2, 5, 8, 12]
        cpu_metrics = []
        
        for flow_count in flow_counts:
            adapters = await scaling_harness.setup_test_environment(flow_count)
            
            # Create CPU-intensive workload
            with patch.object(KnowledgeAdapter, '_search_local_files') as mock_search:
                # Simulate file I/O work
                def cpu_intensive_search(query, limit=5):
                    # Simulate computational work
                    result = ""
                    for i in range(1000):
                        result += f"Line {i}: {query}\n"
                    return result
                
                mock_search.side_effect = cpu_intensive_search
                
                start_time = time.time()
                
                tasks = []
                for adapter in adapters:
                    task = adapter.search(f"cpu test {len(tasks)}")
                    tasks.append(task)
                
                await asyncio.gather(*tasks, return_exceptions=True)
                
                cpu_percent = scaling_harness.process.cpu_percent()
                duration = time.time() - start_time
                
                cpu_metrics.append((flow_count, cpu_percent, duration))
            
            await scaling_harness.cleanup_test_environment()
        
        # Analyze CPU scaling
        for flow_count, cpu_percent, duration in cpu_metrics:
            # CPU should scale reasonably (not > 95% until high flow counts)
            if flow_count <= 8:
                assert cpu_percent < 95, f"CPU maxed out at {flow_count} flows: {cpu_percent}%"
        
        logger.info("CPU scaling validated", cpu_metrics=cpu_metrics)


class TestPerformanceDegradationPoints:
    """Test system limits and performance cliff detection"""
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_performance_cliff_detection(self, scaling_harness):
        """Test system behavior at performance limits"""
        result = ScalingTestResult(test_name="performance_cliff_detection")
        
        # Test increasing loads until degradation
        flow_counts = [1, 3, 6, 10, 15, 20]
        
        for flow_count in flow_counts:
            try:
                adapters = await scaling_harness.setup_test_environment(flow_count)
                
                with patch('aiohttp.ClientSession.post') as mock_post:
                    # Simulate occasional failures at high load
                    failure_rate = min(0.3, (flow_count - 5) * 0.05) if flow_count > 5 else 0
                    
                    def mock_response(*args, **kwargs):
                        if failure_rate > 0 and hash(str(args)) % 100 < failure_rate * 100:
                            raise asyncio.TimeoutError("Simulated overload")
                        
                        mock_resp = AsyncMock()
                        mock_resp.json = AsyncMock(return_value={"results": []})
                        mock_resp.status = 200
                        return mock_resp
                    
                    mock_post.return_value.__aenter__ = AsyncMock(side_effect=mock_response)
                    
                    start_time = time.time()
                    
                    tasks = [adapter.search(f"cliff test {i}") for i, adapter in enumerate(adapters)]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    end_time = time.time()
                    
                    # Calculate performance metrics
                    success_count = sum(1 for r in results if not isinstance(r, Exception))
                    error_count = len(results) - success_count
                    duration_ms = (end_time - start_time) * 1000
                    throughput = len(results) / ((end_time - start_time) or 0.001)
                    success_rate = success_count / len(results) if results else 0
                    
                    metrics = scaling_harness.capture_system_metrics(
                        flow_count, duration_ms, throughput, success_rate, error_count
                    )
                    result.metrics.append(metrics)
                
                await scaling_harness.cleanup_test_environment()
                
            except Exception as e:
                logger.error("Performance test failed", flow_count=flow_count, error=str(e))
                break
        
        # Analyze performance degradation
        result.analyze_scaling_characteristics()
        
        # Should detect performance issues at high loads
        assert len(result.bottlenecks) > 0, "No bottlenecks detected in stress test"
        assert result.max_sustainable_flows < max(flow_counts), "No performance limits found"
        
        logger.info("Performance cliff analysis",
                   bottlenecks=result.bottlenecks,
                   max_flows=result.max_sustainable_flows)
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_connection_limits(self, scaling_harness):
        """Test behavior with high concurrent connection counts"""
        connection_counts = [5, 10, 20, 50]
        connection_metrics = []
        
        for conn_count in connection_counts:
            adapters = await scaling_harness.setup_test_environment(1)  # Single adapter, many connections
            adapter = adapters[0]
            
            with patch('aiohttp.ClientSession.post') as mock_post:
                mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={"results": []})
                mock_post.return_value.__aenter__.return_value.status = 200
                
                start_time = time.time()
                
                # Create many concurrent requests on single adapter
                tasks = [adapter.search(f"connection test {i}") for i in range(conn_count)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                end_time = time.time()
                
                success_count = sum(1 for r in results if not isinstance(r, Exception))
                duration = end_time - start_time
                throughput = success_count / duration if duration > 0 else 0
                
                connection_metrics.append((conn_count, success_count, throughput))
            
            await scaling_harness.cleanup_test_environment()
        
        # Analyze connection scaling
        for conn_count, success_count, throughput in connection_metrics:
            success_rate = success_count / conn_count
            if conn_count <= 20:
                assert success_rate > 0.8, f"Low success rate at {conn_count} connections: {success_rate:.2%}"
        
        logger.info("Connection scaling validated", connection_metrics=connection_metrics)


class TestScalingEfficiencyMetrics:
    """Test scaling efficiency and capacity planning metrics"""
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_throughput_per_flow_ratio(self, scaling_harness):
        """Test throughput efficiency as flow count increases"""
        flow_counts = [1, 2, 4, 8]
        efficiency_metrics = []
        
        for flow_count in flow_counts:
            adapters = await scaling_harness.setup_test_environment(flow_count)
            
            with patch('aiohttp.ClientSession.post') as mock_post:
                mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={"results": []})
                mock_post.return_value.__aenter__.return_value.status = 200
                
                start_time = time.time()
                
                # Each adapter performs multiple operations
                tasks = []
                operations_per_flow = 3
                for adapter in adapters:
                    for i in range(operations_per_flow):
                        tasks.append(adapter.search(f"efficiency test {len(tasks)}"))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                end_time = time.time()
                
                success_count = sum(1 for r in results if not isinstance(r, Exception))
                throughput = success_count / (end_time - start_time)
                efficiency = throughput / flow_count
                
                efficiency_metrics.append((flow_count, throughput, efficiency))
            
            await scaling_harness.cleanup_test_environment()
        
        # Analyze efficiency trends
        efficiencies = [e[2] for e in efficiency_metrics]
        
        # Efficiency should not degrade significantly
        baseline_efficiency = efficiencies[0]
        for flow_count, throughput, efficiency in efficiency_metrics[1:]:
            efficiency_ratio = efficiency / baseline_efficiency
            if flow_count <= 8:  # Within reasonable scale
                assert efficiency_ratio > 0.8, f"Efficiency degraded at {flow_count} flows: {efficiency_ratio:.2%}"
        
        logger.info("Throughput efficiency validated", efficiency_metrics=efficiency_metrics)
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_resource_efficiency_scaling(self, scaling_harness):
        """Test resource efficiency (operations per MB) scaling"""
        flow_counts = [2, 4, 6, 8]
        resource_metrics = []
        
        for flow_count in flow_counts:
            adapters = await scaling_harness.setup_test_environment(flow_count)
            
            with patch('aiohttp.ClientSession.post') as mock_post:
                mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={"results": []})
                mock_post.return_value.__aenter__.return_value.status = 200
                
                start_time = time.time()
                tasks = [adapter.search(f"resource test {i}") for i, adapter in enumerate(adapters)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                end_time = time.time()
                
                success_count = sum(1 for r in results if not isinstance(r, Exception))
                throughput = success_count / (end_time - start_time)
                memory_mb = scaling_harness.process.memory_info().rss / 1024 / 1024
                resource_efficiency = throughput / memory_mb if memory_mb > 0 else 0
                
                resource_metrics.append((flow_count, throughput, memory_mb, resource_efficiency))
            
            await scaling_harness.cleanup_test_environment()
        
        # Resource efficiency should not collapse
        for flow_count, throughput, memory_mb, efficiency in resource_metrics:
            assert efficiency > 0, f"Zero resource efficiency at {flow_count} flows"
        
        logger.info("Resource efficiency validated", resource_metrics=resource_metrics)


class TestCapacityPlanningData:
    """Generate production capacity planning data"""
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_generate_capacity_report(self, scaling_harness):
        """Generate comprehensive capacity planning report"""
        result = ScalingTestResult(test_name="capacity_planning")
        
        # Test multiple scenarios
        scenarios = [
            ("light_load", [1, 2, 3], 2),
            ("medium_load", [2, 4, 6], 3), 
            ("heavy_load", [4, 8, 12], 4),
            ("stress_test", [8, 12, 16], 2)
        ]
        
        capacity_data = {}
        
        for scenario_name, flow_counts, ops_per_flow in scenarios:
            scenario_metrics = []
            
            for flow_count in flow_counts:
                try:
                    adapters = await scaling_harness.setup_test_environment(flow_count)
                    
                    with patch('aiohttp.ClientSession.post') as mock_post:
                        mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={"results": []})
                        mock_post.return_value.__aenter__.return_value.status = 200
                        
                        start_time = time.time()
                        
                        tasks = []
                        for adapter in adapters:
                            for i in range(ops_per_flow):
                                tasks.append(adapter.search(f"{scenario_name} test {len(tasks)}"))
                        
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        end_time = time.time()
                        
                        success_count = sum(1 for r in results if not isinstance(r, Exception))
                        error_count = len(results) - success_count
                        duration_ms = (end_time - start_time) * 1000
                        throughput = success_count / ((end_time - start_time) or 0.001)
                        success_rate = success_count / len(results) if results else 0
                        
                        metrics = scaling_harness.capture_system_metrics(
                            flow_count, duration_ms, throughput, success_rate, error_count
                        )
                        scenario_metrics.append(metrics)
                    
                    await scaling_harness.cleanup_test_environment()
                    
                except Exception as e:
                    logger.error("Capacity test failed", scenario=scenario_name, flows=flow_count, error=str(e))
                    break
            
            capacity_data[scenario_name] = scenario_metrics
        
        # Generate capacity recommendations
        recommendations = self._generate_capacity_recommendations(capacity_data)
        
        # Log capacity planning data
        logger.info("Capacity planning report generated",
                   scenarios=list(capacity_data.keys()),
                   recommendations=recommendations)
        
        # Validate we have meaningful data
        assert len(capacity_data) > 0, "No capacity data generated"
        assert len(recommendations) > 0, "No capacity recommendations generated"
    
    def _generate_capacity_recommendations(self, capacity_data: Dict[str, List[ScalingMetrics]]) -> List[str]:
        """Generate capacity planning recommendations from test data"""
        recommendations = []
        
        # Analyze each scenario
        for scenario, metrics in capacity_data.items():
            if not metrics:
                continue
                
            max_throughput = max(m.throughput_ops_per_sec for m in metrics)
            max_memory = max(m.memory_usage_mb for m in metrics)
            max_flows = max(m.flow_count for m in metrics)
            
            recommendations.append(f"{scenario}: {max_flows} flows, {max_throughput:.1f} ops/sec, {max_memory:.1f} MB")
        
        # Overall recommendations
        all_metrics = [m for metrics in capacity_data.values() for m in metrics]
        if all_metrics:
            peak_memory = max(m.memory_usage_mb for m in all_metrics)
            peak_throughput = max(m.throughput_ops_per_sec for m in all_metrics)
            
            recommendations.extend([
                f"Peak performance: {peak_throughput:.1f} ops/sec",
                f"Peak memory usage: {peak_memory:.1f} MB",
                f"Recommended production limits: 80% of peak values",
                f"Monitor memory growth rates > 1.5x per flow scale-up"
            ])
        
        return recommendations


if __name__ == "__main__":
    # Run scaling tests
    pytest.main([
        __file__,
        "-v",
        "-m", "performance",
        "--tb=short",
        "--capture=no"
    ])