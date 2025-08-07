"""
Mock Profiler - Simulated profiling for testing and demonstration

This module provides mock profiling capabilities that simulate realistic
flow execution patterns without requiring CrewAI or actual flow execution.
"""

import random
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager

from .flow_profiler import ProfilingConfig, ProfilingReport, MethodProfile

logger = logging.getLogger(__name__)


@dataclass
class SimulatedExecution:
    """Configuration for simulated execution"""
    
    # Execution parameters
    total_duration: float = 45.0  # seconds
    method_count: int = 12
    
    # Resource usage simulation
    base_memory_mb: float = 150.0
    peak_memory_mb: float = 420.0
    base_cpu_percent: float = 25.0
    peak_cpu_percent: float = 75.0
    
    # Bottleneck simulation
    bottleneck_probability: float = 0.3  # 30% chance per method
    memory_spike_probability: float = 0.2
    cpu_spike_probability: float = 0.25
    
    # Variation parameters
    time_variation: float = 0.3  # 30% variation in execution times
    resource_variation: float = 0.4  # 40% variation in resource usage


class MockFlowProfiler:
    """
    Mock implementation of FlowProfiler for testing and demonstration
    
    Simulates realistic flow execution patterns including:
    - Variable method execution times
    - Memory usage patterns
    - CPU spikes and bottlenecks
    - I/O operations
    - Critical path simulation
    """
    
    def __init__(self, config: Optional[ProfilingConfig] = None):
        """
        Initialize MockFlowProfiler
        
        Args:
            config: Profiling configuration (optional)
        """
        self.config = config or ProfilingConfig()
        self.simulation_config = SimulatedExecution()
        
        # Mock flow methods - simulating V2 architecture
        self.flow_methods = [
            "validate_inputs",
            "conduct_research", 
            "align_audience",
            "generate_draft",
            "validate_style",
            "assess_quality",
            "finalize_content",
            "knowledge_base_search",
            "styleguide_validation",
            "quality_gate_check",
            "monitoring_update",
            "state_synchronization"
        ]
        
        logger.info(f"🎭 MockFlowProfiler initialized with {len(self.flow_methods)} simulated methods")
    
    @contextmanager
    def profile_execution(self, execution_id: str):
        """
        Context manager for mock profiling
        
        Args:
            execution_id: Unique identifier for this execution
        """
        logger.info(f"🎬 Starting mock profiling for execution: {execution_id}")
        
        try:
            # Simulate profiling startup time
            time.sleep(0.1)
            yield self
        finally:
            logger.info(f"🎭 Mock profiling completed for execution: {execution_id}")
    
    def generate_mock_report(self, execution_id: str) -> ProfilingReport:
        """
        Generate realistic mock profiling report
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            ProfilingReport with simulated data
        """
        logger.info(f"📊 Generating mock profiling report for: {execution_id}")
        
        start_time = datetime.now(timezone.utc) - timedelta(seconds=self.simulation_config.total_duration)
        end_time = datetime.now(timezone.utc)
        
        # Generate method profiles
        method_profiles = self._generate_mock_method_profiles()
        
        # Generate critical path
        critical_path = self._generate_mock_critical_path(method_profiles)
        
        # Generate resource usage data
        peak_memory_mb = self._simulate_peak_memory()
        avg_cpu_percent = self._simulate_avg_cpu()
        peak_cpu_percent = self._simulate_peak_cpu()
        
        # Generate bottlenecks and hotspots
        performance_bottlenecks = self._generate_mock_bottlenecks(method_profiles)
        memory_hotspots = self._generate_mock_memory_hotspots()
        cpu_hotspots = self._generate_mock_cpu_hotspots()
        
        # Generate recommendations
        recommendations = self._generate_mock_recommendations(method_profiles, performance_bottlenecks)
        
        report = ProfilingReport(
            execution_id=execution_id,
            start_time=start_time,
            end_time=end_time,
            total_duration=self.simulation_config.total_duration,
            method_profiles=method_profiles,
            critical_path=critical_path,
            peak_memory_mb=peak_memory_mb,
            avg_cpu_percent=avg_cpu_percent,
            peak_cpu_percent=peak_cpu_percent,
            total_io_operations=self._simulate_io_operations(),
            performance_bottlenecks=performance_bottlenecks,
            memory_hotspots=memory_hotspots,
            cpu_hotspots=cpu_hotspots,
            recommendations=recommendations
        )
        
        logger.info(f"✅ Mock profiling report generated with {len(method_profiles)} methods")
        return report
    
    def _generate_mock_method_profiles(self) -> Dict[str, MethodProfile]:
        """Generate realistic method profiles"""
        
        method_profiles = {}
        remaining_time = self.simulation_config.total_duration
        
        for i, method_name in enumerate(self.flow_methods):
            
            # Simulate different execution patterns
            if method_name in ["conduct_research", "generate_draft"]:
                # Long-running methods
                base_time = random.uniform(3.0, 8.0)
                call_count = random.randint(1, 3)
            elif method_name in ["knowledge_base_search", "styleguide_validation"]:
                # Frequently called methods
                base_time = random.uniform(0.1, 0.5)
                call_count = random.randint(15, 50)
            else:
                # Regular methods
                base_time = random.uniform(0.5, 2.5)
                call_count = random.randint(1, 8)
            
            # Apply time variation
            variation_factor = 1.0 + random.uniform(-self.simulation_config.time_variation, 
                                                    self.simulation_config.time_variation)
            avg_time = base_time * variation_factor
            
            # Generate time distribution
            min_time = avg_time * 0.7
            max_time = avg_time * 1.8
            total_time = avg_time * call_count
            
            # Simulate memory usage
            if method_name in ["generate_draft", "conduct_research"]:
                memory_delta = random.randint(50, 200) * 1024 * 1024  # 50-200MB
            elif method_name == "knowledge_base_search":
                memory_delta = random.randint(10, 40) * 1024 * 1024   # 10-40MB
            else:
                memory_delta = random.randint(1, 15) * 1024 * 1024    # 1-15MB
            
            # Add memory leak simulation
            if random.random() < 0.1:  # 10% chance
                memory_delta *= 3  # Simulate memory leak
            
            # Simulate CPU usage
            if method_name in ["generate_draft", "assess_quality"]:
                cpu_usage = random.uniform(40.0, 85.0)
            else:
                cpu_usage = random.uniform(10.0, 45.0)
            
            # Determine if this is a bottleneck
            is_bottleneck = (
                avg_time > 2.0 or 
                memory_delta > 100 * 1024 * 1024 or
                cpu_usage > 70.0 or
                random.random() < self.simulation_config.bottleneck_probability
            )
            
            method_profiles[method_name] = MethodProfile(
                name=method_name,
                call_count=call_count,
                total_time=total_time,
                avg_time=avg_time,
                min_time=min_time,
                max_time=max_time,
                memory_delta=memory_delta,
                cpu_usage=cpu_usage,
                is_bottleneck=is_bottleneck
            )
        
        return method_profiles
    
    def _generate_mock_critical_path(self, method_profiles: Dict[str, MethodProfile]) -> List[str]:
        """Generate mock critical path"""
        
        # Sort methods by total time (descending)
        method_times = [(name, profile.total_time) for name, profile in method_profiles.items()]
        method_times.sort(key=lambda x: x[1], reverse=True)
        
        # Critical path includes top methods that make up ~80% of execution time
        total_time = sum(time for _, time in method_times)
        critical_path = []
        cumulative_time = 0.0
        
        for method_name, method_time in method_times:
            critical_path.append(method_name)
            cumulative_time += method_time
            
            if cumulative_time >= 0.8 * total_time or len(critical_path) >= 6:
                break
        
        return critical_path
    
    def _simulate_peak_memory(self) -> float:
        """Simulate peak memory usage"""
        
        base_peak = self.simulation_config.peak_memory_mb
        variation = base_peak * self.simulation_config.resource_variation
        
        peak_memory = base_peak + random.uniform(-variation, variation)
        
        # Simulate occasional memory spikes
        if random.random() < self.simulation_config.memory_spike_probability:
            peak_memory *= random.uniform(1.5, 2.5)
        
        return max(50.0, peak_memory)  # Minimum 50MB
    
    def _simulate_avg_cpu(self) -> float:
        """Simulate average CPU usage"""
        
        base_cpu = self.simulation_config.base_cpu_percent
        variation = base_cpu * self.simulation_config.resource_variation
        
        return max(5.0, base_cpu + random.uniform(-variation, variation))
    
    def _simulate_peak_cpu(self) -> float:
        """Simulate peak CPU usage"""
        
        base_peak = self.simulation_config.peak_cpu_percent
        variation = base_peak * self.simulation_config.resource_variation
        
        peak_cpu = base_peak + random.uniform(-variation, variation)
        
        # Simulate CPU spikes
        if random.random() < self.simulation_config.cpu_spike_probability:
            peak_cpu = min(100.0, peak_cpu * random.uniform(1.2, 1.8))
        
        return peak_cpu
    
    def _simulate_io_operations(self) -> int:
        """Simulate I/O operations count"""
        
        # Base I/O operations for different flow activities
        base_operations = 150
        variation = int(base_operations * 0.6)
        
        return base_operations + random.randint(-variation, variation)
    
    def _generate_mock_bottlenecks(self, method_profiles: Dict[str, MethodProfile]) -> List[Dict[str, Any]]:
        """Generate mock performance bottlenecks"""
        
        bottlenecks = []
        
        for method_name, profile in method_profiles.items():
            if profile.is_bottleneck:
                
                # Determine bottleneck type
                if profile.avg_time > 3.0:
                    bottleneck_type = "execution_time"
                    severity = "high" if profile.avg_time > 6.0 else "medium"
                elif profile.memory_delta > 100 * 1024 * 1024:
                    bottleneck_type = "memory_usage"
                    severity = "high" if profile.memory_delta > 200 * 1024 * 1024 else "medium"
                elif profile.cpu_usage > 70.0:
                    bottleneck_type = "cpu_usage"
                    severity = "high" if profile.cpu_usage > 85.0 else "medium"
                else:
                    bottleneck_type = "call_frequency"
                    severity = "medium"
                
                bottlenecks.append({
                    "method": method_name,
                    "bottleneck_type": bottleneck_type,
                    "severity": severity,
                    "execution_time": profile.avg_time,
                    "memory_delta": profile.memory_delta,
                    "cpu_usage": profile.cpu_usage,
                    "call_count": profile.call_count,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "impact_score": random.uniform(60.0, 95.0)
                })
        
        return bottlenecks
    
    def _generate_mock_memory_hotspots(self) -> List[Dict[str, Any]]:
        """Generate mock memory hotspots"""
        
        hotspots = []
        
        # Simulate 2-4 memory hotspots during execution
        hotspot_count = random.randint(2, 4)
        
        for i in range(hotspot_count):
            timestamp = datetime.now(timezone.utc) - timedelta(
                seconds=random.uniform(5, self.simulation_config.total_duration - 5)
            )
            
            memory_mb = random.uniform(200, 600)
            
            hotspots.append({
                "timestamp": timestamp.isoformat(),
                "memory_mb": memory_mb,
                "snapshot_type": "periodic",
                "top_users": [
                    {
                        "component": random.choice(["draft_generator", "knowledge_search", "style_validator"]),
                        "size_mb": random.uniform(20, 100),
                        "allocation_count": random.randint(1000, 10000)
                    }
                ]
            })
        
        return hotspots
    
    def _generate_mock_cpu_hotspots(self) -> List[Dict[str, Any]]:
        """Generate mock CPU hotspots"""
        
        hotspots = []
        
        # Simulate 1-3 CPU spikes
        spike_count = random.randint(1, 3)
        
        for i in range(spike_count):
            timestamp = datetime.now(timezone.utc) - timedelta(
                seconds=random.uniform(5, self.simulation_config.total_duration - 5)
            )
            
            cpu_percent = random.uniform(80.0, 98.0)
            
            hotspots.append({
                "timestamp": timestamp.isoformat(),
                "cpu_percent": cpu_percent,
                "duration_seconds": random.uniform(0.5, 3.0),
                "caused_by": random.choice([
                    "draft_generation_computation",
                    "knowledge_base_search",
                    "style_validation_regex",
                    "quality_assessment_analysis"
                ])
            })
        
        return hotspots
    
    def _generate_mock_recommendations(
        self,
        method_profiles: Dict[str, MethodProfile],
        bottlenecks: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate mock optimization recommendations"""
        
        recommendations = []
        
        # Recommendations based on bottlenecks
        high_impact_bottlenecks = [b for b in bottlenecks if b.get('impact_score', 0) > 80]
        
        if high_impact_bottlenecks:
            top_bottleneck = max(high_impact_bottlenecks, key=lambda b: b.get('impact_score', 0))
            recommendations.append(
                f"Optimize {top_bottleneck['method']} method - identified as critical bottleneck "
                f"({top_bottleneck['bottleneck_type']})"
            )
        
        # Memory recommendations
        memory_intensive_methods = [
            name for name, profile in method_profiles.items()
            if profile.memory_delta > 50 * 1024 * 1024
        ]
        
        if memory_intensive_methods:
            recommendations.append(
                f"Consider memory optimization for: {', '.join(memory_intensive_methods[:2])}. "
                f"Implement streaming or chunked processing."
            )
        
        # CPU recommendations
        cpu_intensive_methods = [
            name for name, profile in method_profiles.items()
            if profile.cpu_usage > 60.0
        ]
        
        if cpu_intensive_methods:
            recommendations.append(
                f"Consider async processing for CPU-intensive methods: {', '.join(cpu_intensive_methods[:2])}"
            )
        
        # Call frequency recommendations
        high_frequency_methods = [
            name for name, profile in method_profiles.items()
            if profile.call_count > 20
        ]
        
        if high_frequency_methods:
            recommendations.append(
                f"Add caching for frequently called methods: {', '.join(high_frequency_methods[:2])}"
            )
        
        # Generic recommendations for realistic scenario
        generic_recommendations = [
            "Consider implementing result caching for Knowledge Base searches",
            "Optimize draft generation by pre-loading style guidelines",
            "Implement batch processing for quality assessments",
            "Add memory cleanup after large document processing",
            "Consider parallel processing for independent validation steps"
        ]
        
        # Add 1-2 generic recommendations
        recommendations.extend(random.sample(generic_recommendations, random.randint(1, 2)))
        
        if not recommendations:
            recommendations.append("Performance looks optimal! No major optimizations needed.")
        
        return recommendations
    
    def simulate_profiling_session(self, execution_id: str) -> ProfilingReport:
        """
        Simulate complete profiling session with realistic timing
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            ProfilingReport with simulated profiling data
        """
        logger.info(f"🎭 Simulating complete profiling session: {execution_id}")
        
        with self.profile_execution(execution_id):
            # Simulate profiling overhead
            time.sleep(0.2)
            
            # Generate realistic report
            report = self.generate_mock_report(execution_id) 
            
            # Simulate report generation time
            time.sleep(0.1)
        
        logger.info(
            f"✅ Mock profiling session completed. "
            f"Duration: {report.total_duration:.1f}s, "
            f"Methods: {len(report.method_profiles)}, "
            f"Bottlenecks: {len(report.performance_bottlenecks)}"
        )
        
        return report
    
    def create_performance_scenario(self, scenario_type: str) -> None:
        """
        Configure profiler for specific performance scenarios
        
        Args:
            scenario_type: Type of scenario to simulate
                          ('optimal', 'bottlenecked', 'memory_intensive', 'cpu_intensive')
        """
        logger.info(f"🎨 Configuring mock profiler for scenario: {scenario_type}")
        
        if scenario_type == "optimal":
            self.simulation_config.total_duration = 25.0
            self.simulation_config.peak_memory_mb = 180.0
            self.simulation_config.peak_cpu_percent = 45.0
            self.simulation_config.bottleneck_probability = 0.1
            
        elif scenario_type == "bottlenecked":
            self.simulation_config.total_duration = 85.0
            self.simulation_config.peak_memory_mb = 650.0
            self.simulation_config.peak_cpu_percent = 95.0
            self.simulation_config.bottleneck_probability = 0.6
            
        elif scenario_type == "memory_intensive":
            self.simulation_config.total_duration = 55.0
            self.simulation_config.peak_memory_mb = 1200.0
            self.simulation_config.base_memory_mb = 400.0
            self.simulation_config.memory_spike_probability = 0.5
            
        elif scenario_type == "cpu_intensive":
            self.simulation_config.total_duration = 75.0
            self.simulation_config.base_cpu_percent = 65.0
            self.simulation_config.peak_cpu_percent = 98.0
            self.simulation_config.cpu_spike_probability = 0.6
            
        else:
            logger.warning(f"Unknown scenario type: {scenario_type}. Using default configuration.")
        
        logger.info(f"🎯 Scenario '{scenario_type}' configured successfully")
