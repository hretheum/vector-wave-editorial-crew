"""
Performance Analyzer - Advanced performance analysis and bottleneck detection

This module provides sophisticated analysis of profiling data including:
- Statistical analysis of performance metrics
- Bottleneck detection algorithms
- Performance regression detection
- Optimization recommendations
"""

import statistics
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path

from .flow_profiler import ProfilingReport, MethodProfile

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Aggregated performance metrics"""
    
    # Execution metrics
    total_execution_time: float
    method_count: int
    avg_method_time: float
    p50_method_time: float  # Median
    p95_method_time: float
    p99_method_time: float
    
    # Resource metrics  
    peak_memory_mb: float
    avg_memory_mb: float
    memory_efficiency: float  # MB per second
    
    # CPU metrics
    avg_cpu_percent: float
    peak_cpu_percent: float
    cpu_efficiency: float  # CPU time / wall time
    
    # I/O metrics
    total_io_operations: int
    io_throughput: float  # ops per second
    
    # Quality metrics
    bottleneck_count: int
    critical_path_length: int
    performance_score: float  # 0-100


@dataclass
class BottleneckAnalysis:
    """Detailed bottleneck analysis"""
    
    method_name: str
    bottleneck_type: str  # 'cpu', 'memory', 'io', 'time'
    severity: str         # 'low', 'medium', 'high', 'critical'
    impact_score: float   # 0-100
    
    # Metrics
    execution_time: float
    call_count: int
    memory_usage: int
    cpu_usage: float
    
    # Analysis
    root_cause: str
    optimization_suggestions: List[str]
    estimated_improvement: float  # Estimated time reduction in seconds


class PerformanceAnalyzer:
    """
    Advanced performance analysis and bottleneck detection
    
    Provides sophisticated analysis of profiling data to identify
    performance issues and generate actionable optimization recommendations.
    """
    
    def __init__(self):
        """Initialize PerformanceAnalyzer"""
        self.historical_reports: List[ProfilingReport] = []
        logger.info("📊 PerformanceAnalyzer initialized")
    
    def analyze_report(self, report: ProfilingReport) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a profiling report
        
        Args:
            report: ProfilingReport to analyze
            
        Returns:
            Dict containing detailed analysis results
        """
        logger.info(f"🔍 Analyzing performance report: {report.execution_id}")
        
        # Calculate performance metrics
        metrics = self._calculate_performance_metrics(report)
        
        # Detect bottlenecks
        bottlenecks = self._detect_bottlenecks(report)
        
        # Analyze critical path
        critical_path_analysis = self._analyze_critical_path(report)
        
        # Generate performance score
        performance_score = self._calculate_performance_score(report, metrics, bottlenecks)
        
        # Compare with historical data
        historical_comparison = self._compare_with_historical(report)
        
        # Generate optimization recommendations
        optimization_recommendations = self._generate_optimization_recommendations(
            report, metrics, bottlenecks
        )
        
        analysis_result = {
            "execution_id": report.execution_id,
            "analysis_timestamp": datetime.now().isoformat(),
            "performance_metrics": metrics.__dict__,
            "bottlenecks": [b.__dict__ for b in bottlenecks],
            "critical_path_analysis": critical_path_analysis,
            "performance_score": performance_score,
            "historical_comparison": historical_comparison,
            "optimization_recommendations": optimization_recommendations,
            "summary": self._generate_analysis_summary(metrics, bottlenecks, performance_score)
        }
        
        # Store report for historical comparison
        self.historical_reports.append(report)
        
        logger.info(f"✅ Performance analysis completed. Score: {performance_score:.1f}/100")
        return analysis_result
    
    def _calculate_performance_metrics(self, report: ProfilingReport) -> PerformanceMetrics:
        """Calculate aggregated performance metrics"""
        
        method_times = []
        total_memory_usage = 0
        total_cpu_usage = 0
        
        for profile in report.method_profiles.values():
            method_times.extend([profile.avg_time] * profile.call_count)
            total_memory_usage += abs(profile.memory_delta)
            total_cpu_usage += profile.cpu_usage * profile.total_time
        
        # Calculate percentiles
        if method_times:
            method_times.sort()
            p50 = statistics.median(method_times)
            p95 = method_times[int(0.95 * len(method_times))] if len(method_times) > 1 else method_times[0]
            p99 = method_times[int(0.99 * len(method_times))] if len(method_times) > 1 else method_times[0]
            avg_method_time = statistics.mean(method_times)
        else:
            p50 = p95 = p99 = avg_method_time = 0.0
        
        # Calculate efficiency metrics
        memory_efficiency = report.peak_memory_mb / report.total_duration if report.total_duration > 0 else 0
        cpu_efficiency = total_cpu_usage / report.total_duration if report.total_duration > 0 else 0
        io_throughput = report.total_io_operations / report.total_duration if report.total_duration > 0 else 0
        
        return PerformanceMetrics(
            total_execution_time=report.total_duration,
            method_count=len(report.method_profiles),
            avg_method_time=avg_method_time,
            p50_method_time=p50,
            p95_method_time=p95,
            p99_method_time=p99,
            peak_memory_mb=report.peak_memory_mb,
            avg_memory_mb=total_memory_usage / (1024 * 1024) / len(report.method_profiles) if report.method_profiles else 0,
            memory_efficiency=memory_efficiency,
            avg_cpu_percent=report.avg_cpu_percent,
            peak_cpu_percent=report.peak_cpu_percent,
            cpu_efficiency=cpu_efficiency,
            total_io_operations=report.total_io_operations,
            io_throughput=io_throughput,
            bottleneck_count=len(report.performance_bottlenecks),
            critical_path_length=len(report.critical_path),
            performance_score=0.0  # Will be calculated separately
        )
    
    def _detect_bottlenecks(self, report: ProfilingReport) -> List[BottleneckAnalysis]:
        """Detect and analyze bottlenecks"""
        bottlenecks = []
        
        for method_name, profile in report.method_profiles.items():
            bottleneck_analyses = []
            
            # Time-based bottleneck detection
            if profile.avg_time > 2.0:  # More than 2 seconds average
                bottleneck_analyses.append(self._create_time_bottleneck_analysis(profile))
            
            # Memory-based bottleneck detection
            if abs(profile.memory_delta) > 100 * 1024 * 1024:  # More than 100MB
                bottleneck_analyses.append(self._create_memory_bottleneck_analysis(profile))
            
            # CPU-based bottleneck detection
            if profile.cpu_usage > 80.0:  # More than 80% CPU
                bottleneck_analyses.append(self._create_cpu_bottleneck_analysis(profile))
            
            # Call frequency bottleneck detection
            if profile.call_count > 1000:  # Called more than 1000 times
                bottleneck_analyses.append(self._create_frequency_bottleneck_analysis(profile))
            
            bottlenecks.extend(bottleneck_analyses)
        
        # Sort by impact score (descending)
        bottlenecks.sort(key=lambda b: b.impact_score, reverse=True)
        
        return bottlenecks
    
    def _create_time_bottleneck_analysis(self, profile: MethodProfile) -> BottleneckAnalysis:
        """Create time-based bottleneck analysis"""
        
        # Determine severity based on execution time
        if profile.avg_time > 10.0:
            severity = "critical"
            impact_score = 95.0
        elif profile.avg_time > 5.0:
            severity = "high"
            impact_score = 80.0
        elif profile.avg_time > 2.0:
            severity = "medium"
            impact_score = 60.0
        else:
            severity = "low"
            impact_score = 30.0
        
        # Generate optimization suggestions
        suggestions = []
        if profile.call_count > 1:
            suggestions.append("Consider caching results to avoid repeated computation")
        if profile.avg_time > 5.0:
            suggestions.append("Profile internal operations to identify sub-bottlenecks")
        suggestions.append("Consider algorithm optimization or parallel processing")
        
        # Estimate improvement (assume 30-70% reduction possible)
        estimated_improvement = profile.total_time * 0.5
        
        return BottleneckAnalysis(
            method_name=profile.name,
            bottleneck_type="time",
            severity=severity,
            impact_score=impact_score,
            execution_time=profile.avg_time,
            call_count=profile.call_count,
            memory_usage=profile.memory_delta,
            cpu_usage=profile.cpu_usage,
            root_cause=f"Method execution time of {profile.avg_time:.2f}s exceeds performance thresholds",
            optimization_suggestions=suggestions,
            estimated_improvement=estimated_improvement
        )
    
    def _create_memory_bottleneck_analysis(self, profile: MethodProfile) -> BottleneckAnalysis:
        """Create memory-based bottleneck analysis"""
        
        memory_mb = abs(profile.memory_delta) / (1024 * 1024)
        
        # Determine severity based on memory usage
        if memory_mb > 500:
            severity = "critical"
            impact_score = 90.0
        elif memory_mb > 200:
            severity = "high"
            impact_score = 75.0
        elif memory_mb > 100:
            severity = "medium"
            impact_score = 50.0
        else:
            severity = "low"
            impact_score = 25.0
        
        suggestions = [
            "Implement memory-efficient data structures",
            "Consider streaming processing for large datasets",
            "Add explicit garbage collection or memory cleanup",
            "Use memory profiling to identify specific allocation hotspots"
        ]
        
        estimated_improvement = profile.total_time * 0.2  # Memory optimization typically gives 20% improvement
        
        return BottleneckAnalysis(
            method_name=profile.name,
            bottleneck_type="memory",
            severity=severity,
            impact_score=impact_score,
            execution_time=profile.avg_time,
            call_count=profile.call_count,
            memory_usage=profile.memory_delta,
            cpu_usage=profile.cpu_usage,
            root_cause=f"Method allocates {memory_mb:.1f}MB of memory, causing potential GC pressure",
            optimization_suggestions=suggestions,
            estimated_improvement=estimated_improvement
        )
    
    def _create_cpu_bottleneck_analysis(self, profile: MethodProfile) -> BottleneckAnalysis:
        """Create CPU-based bottleneck analysis"""
        
        # Determine severity based on CPU usage
        if profile.cpu_usage > 95.0:
            severity = "critical"
            impact_score = 85.0
        elif profile.cpu_usage > 80.0:
            severity = "high"
            impact_score = 70.0
        else:
            severity = "medium"
            impact_score = 45.0
        
        suggestions = [
            "Consider async/await patterns to reduce CPU blocking",
            "Implement CPU-intensive operations in separate threads",
            "Optimize algorithms for better computational complexity",
            "Consider caching computed results"
        ]
        
        estimated_improvement = profile.total_time * 0.3
        
        return BottleneckAnalysis(
            method_name=profile.name,
            bottleneck_type="cpu",
            severity=severity,
            impact_score=impact_score,
            execution_time=profile.avg_time,
            call_count=profile.call_count,
            memory_usage=profile.memory_delta,
            cpu_usage=profile.cpu_usage,
            root_cause=f"Method consumes {profile.cpu_usage:.1f}% CPU, indicating computational bottleneck",
            optimization_suggestions=suggestions,
            estimated_improvement=estimated_improvement
        )
    
    def _create_frequency_bottleneck_analysis(self, profile: MethodProfile) -> BottleneckAnalysis:
        """Create call frequency bottleneck analysis"""
        
        # Determine severity based on call count
        if profile.call_count > 10000:
            severity = "high"
            impact_score = 70.0
        elif profile.call_count > 5000:
            severity = "medium"
            impact_score = 50.0
        else:
            severity = "low"
            impact_score = 30.0
        
        suggestions = [
            "Implement result caching to reduce redundant calls",
            "Consider batching multiple calls into single operations",
            "Optimize call frequency through better flow control",
            "Add memoization for expensive computations"
        ]
        
        estimated_improvement = profile.total_time * 0.4  # High potential for improvement
        
        return BottleneckAnalysis(
            method_name=profile.name,
            bottleneck_type="frequency",
            severity=severity,
            impact_score=impact_score,
            execution_time=profile.avg_time,
            call_count=profile.call_count,
            memory_usage=profile.memory_delta,
            cpu_usage=profile.cpu_usage,
            root_cause=f"Method called {profile.call_count} times, indicating potential over-execution",
            optimization_suggestions=suggestions,
            estimated_improvement=estimated_improvement
        )
    
    def _analyze_critical_path(self, report: ProfilingReport) -> Dict[str, Any]:
        """Analyze the critical path through execution"""
        
        if not report.critical_path:
            return {"error": "No critical path data available"}
        
        # Calculate critical path metrics
        critical_path_time = 0.0
        critical_path_methods = []
        
        for method_name in report.critical_path:
            if method_name in report.method_profiles:
                profile = report.method_profiles[method_name]
                critical_path_time += profile.total_time
                critical_path_methods.append({
                    "method": method_name,
                    "total_time": profile.total_time,
                    "percentage_of_total": (profile.total_time / report.total_duration) * 100
                })
        
        # Identify parallelization opportunities
        parallelizable_methods = []
        for method_name in report.critical_path:
            if method_name in report.method_profiles:
                profile = report.method_profiles[method_name]
                if profile.cpu_usage < 50 and profile.avg_time > 1.0:
                    parallelizable_methods.append(method_name)
        
        return {
            "critical_path_length": len(report.critical_path),
            "critical_path_time": critical_path_time,
            "critical_path_percentage": (critical_path_time / report.total_duration) * 100,
            "critical_path_methods": critical_path_methods,
            "parallelization_opportunities": parallelizable_methods,
            "optimization_potential": len(parallelizable_methods) > 0
        }
    
    def _calculate_performance_score(
        self, 
        report: ProfilingReport, 
        metrics: PerformanceMetrics,
        bottlenecks: List[BottleneckAnalysis]
    ) -> float:
        """Calculate overall performance score (0-100)"""
        
        score = 100.0
        
        # Deduct points for bottlenecks
        for bottleneck in bottlenecks:
            if bottleneck.severity == "critical":
                score -= 25
            elif bottleneck.severity == "high":
                score -= 15
            elif bottleneck.severity == "medium":
                score -= 8
            elif bottleneck.severity == "low":
                score -= 3
        
        # Deduct points for high resource usage
        if metrics.peak_memory_mb > 1000:  # > 1GB
            score -= 10
        elif metrics.peak_memory_mb > 500:  # > 500MB
            score -= 5
        
        if metrics.peak_cpu_percent > 90:
            score -= 10
        elif metrics.peak_cpu_percent > 70:
            score -= 5
        
        # Deduct points for long execution time
        if report.total_duration > 300:  # > 5 minutes
            score -= 15
        elif report.total_duration > 120:  # > 2 minutes
            score -= 8
        elif report.total_duration > 60:   # > 1 minute
            score -= 3
        
        # Bonus points for efficiency
        if metrics.cpu_efficiency > 0.8:
            score += 5
        if metrics.memory_efficiency < 50:  # Low memory usage per second
            score += 5
        
        return max(0.0, min(100.0, score))
    
    def _compare_with_historical(self, report: ProfilingReport) -> Dict[str, Any]:
        """Compare performance with historical data"""
        
        if len(self.historical_reports) < 2:
            return {
                "message": "Insufficient historical data for comparison",
                "historical_count": len(self.historical_reports)
            }
        
        # Get recent reports (last 10)
        recent_reports = self.historical_reports[-10:]
        
        # Calculate averages
        avg_duration = statistics.mean(r.total_duration for r in recent_reports)
        avg_memory = statistics.mean(r.peak_memory_mb for r in recent_reports)
        avg_cpu = statistics.mean(r.avg_cpu_percent for r in recent_reports)
        
        # Calculate changes
        duration_change = ((report.total_duration - avg_duration) / avg_duration) * 100
        memory_change = ((report.peak_memory_mb - avg_memory) / avg_memory) * 100 if avg_memory > 0 else 0
        cpu_change = ((report.avg_cpu_percent - avg_cpu) / avg_cpu) * 100 if avg_cpu > 0 else 0
        
        # Determine trend
        def get_trend(change: float) -> str:
            if abs(change) < 5:
                return "stable"
            elif change > 0:
                return "degraded"
            else:
                return "improved"
        
        return {
            "historical_count": len(recent_reports),
            "duration_change_percent": duration_change,
            "memory_change_percent": memory_change,
            "cpu_change_percent": cpu_change,
            "performance_trend": get_trend(duration_change),
            "memory_trend": get_trend(memory_change),
            "cpu_trend": get_trend(cpu_change),
            "regression_detected": any(abs(change) > 20 for change in [duration_change, memory_change, cpu_change])
        }
    
    def _generate_optimization_recommendations(
        self,
        report: ProfilingReport,
        metrics: PerformanceMetrics,
        bottlenecks: List[BottleneckAnalysis]
    ) -> List[Dict[str, Any]]:
        """Generate specific optimization recommendations"""
        
        recommendations = []
        
        # High-impact bottleneck recommendations
        high_impact_bottlenecks = [b for b in bottlenecks if b.impact_score > 70]
        if high_impact_bottlenecks:
            for bottleneck in high_impact_bottlenecks[:3]:  # Top 3
                recommendations.append({
                    "priority": "high",
                    "category": "bottleneck_optimization",
                    "method": bottleneck.method_name,
                    "description": f"Optimize {bottleneck.bottleneck_type} bottleneck in {bottleneck.method_name}",
                    "suggestions": bottleneck.optimization_suggestions,
                    "estimated_improvement": f"{bottleneck.estimated_improvement:.1f}s",
                    "impact_score": bottleneck.impact_score
                })
        
        # Memory optimization recommendations
        if metrics.peak_memory_mb > 500:
            recommendations.append({
                "priority": "medium",
                "category": "memory_optimization",
                "description": f"Reduce peak memory usage from {metrics.peak_memory_mb:.1f}MB",
                "suggestions": [
                    "Implement streaming processing for large datasets",
                    "Add explicit memory cleanup in long-running methods",
                    "Consider using memory-mapped files for large data",
                    "Optimize data structures to reduce memory footprint"
                ],
                "estimated_improvement": "20-30% memory reduction"
            })
        
        # CPU optimization recommendations
        if metrics.avg_cpu_percent > 70:
            recommendations.append({
                "priority": "medium",
                "category": "cpu_optimization",
                "description": f"Reduce CPU usage from {metrics.avg_cpu_percent:.1f}%",
                "suggestions": [
                    "Implement asynchronous processing where possible",
                    "Consider parallel processing for CPU-intensive tasks",
                    "Optimize algorithms for better computational complexity",
                    "Add result caching to avoid redundant computations"
                ],
                "estimated_improvement": "15-25% CPU reduction"
            })
        
        # I/O optimization recommendations  
        if metrics.io_throughput > 100:  # High I/O activity
            recommendations.append({
                "priority": "low",
                "category": "io_optimization",
                "description": "Optimize I/O operations",
                "suggestions": [
                    "Implement I/O batching where possible",
                    "Consider async I/O for better concurrency",
                    "Optimize file access patterns",
                    "Add I/O caching layer"
                ],
                "estimated_improvement": "10-20% I/O efficiency improvement"
            })
        
        # Critical path optimization
        if len(report.critical_path) > 5:
            recommendations.append({
                "priority": "medium", 
                "category": "critical_path_optimization",
                "description": "Optimize critical path execution",
                "suggestions": [
                    "Identify parallelization opportunities in critical path",
                    "Optimize the top 3 methods in critical path",
                    "Consider pre-computation or caching for critical path methods",
                    "Reduce dependencies between critical path methods"
                ],
                "estimated_improvement": "25-40% overall performance improvement"
            })
        
        # Sort recommendations by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda r: priority_order.get(r["priority"], 3))
        
        return recommendations
    
    def _generate_analysis_summary(
        self,
        metrics: PerformanceMetrics,
        bottlenecks: List[BottleneckAnalysis],
        performance_score: float
    ) -> Dict[str, Any]:
        """Generate analysis summary"""
        
        # Categorize bottlenecks by severity
        critical_bottlenecks = [b for b in bottlenecks if b.severity == "critical"]
        high_bottlenecks = [b for b in bottlenecks if b.severity == "high"]
        
        # Generate status
        if performance_score >= 90:
            status = "excellent"
        elif performance_score >= 70:
            status = "good"
        elif performance_score >= 50:
            status = "fair"
        else:
            status = "poor"
        
        return {
            "performance_status": status, 
            "performance_score": performance_score,
            "total_bottlenecks": len(bottlenecks),
            "critical_bottlenecks": len(critical_bottlenecks),
            "high_bottlenecks": len(high_bottlenecks),
            "execution_time": metrics.total_execution_time,
            "peak_memory_mb": metrics.peak_memory_mb,
            "avg_cpu_percent": metrics.avg_cpu_percent,
            "key_findings": self._generate_key_findings(metrics, bottlenecks),
            "improvement_potential": self._calculate_improvement_potential(bottlenecks)
        }
    
    def _generate_key_findings(
        self,
        metrics: PerformanceMetrics,
        bottlenecks: List[BottleneckAnalysis]
    ) -> List[str]:
        """Generate key findings from analysis"""
        
        findings = []
        
        # Performance findings
        if metrics.total_execution_time > 300:
            findings.append(f"Long execution time of {metrics.total_execution_time:.1f}s detected")
        
        # Memory findings
        if metrics.peak_memory_mb > 1000:
            findings.append(f"High memory usage of {metrics.peak_memory_mb:.1f}MB detected")
        
        # CPU findings
        if metrics.avg_cpu_percent > 80:
            findings.append(f"High CPU usage of {metrics.avg_cpu_percent:.1f}% detected")
        
        # Bottleneck findings
        critical_bottlenecks = [b for b in bottlenecks if b.severity == "critical"]
        if critical_bottlenecks:
            findings.append(f"{len(critical_bottlenecks)} critical bottlenecks identified")
        
        # Efficiency findings
        if metrics.p95_method_time > 5.0:
            findings.append(f"95th percentile method time of {metrics.p95_method_time:.1f}s indicates performance outliers")
        
        if not findings:
            findings.append("No significant performance issues detected")
        
        return findings
    
    def _calculate_improvement_potential(self, bottlenecks: List[BottleneckAnalysis]) -> float:
        """Calculate total improvement potential in seconds"""
        
        return sum(b.estimated_improvement for b in bottlenecks)


class BottleneckDetector:
    """
    Specialized bottleneck detection algorithms
    
    Implements various algorithms for detecting different types of bottlenecks
    in flow execution.
    """
    
    def __init__(self):
        """Initialize BottleneckDetector"""
        logger.info("🔍 BottleneckDetector initialized")
    
    def detect_execution_anomalies(self, method_profiles: Dict[str, MethodProfile]) -> List[Dict[str, Any]]:
        """Detect execution time anomalies using statistical methods"""
        
        anomalies = []
        
        # Collect all execution times
        all_times = []
        for profile in method_profiles.values():
            all_times.extend([profile.avg_time] * profile.call_count)
        
        if len(all_times) < 10:  # Need sufficient data
            return anomalies
        
        # Calculate statistical thresholds
        mean_time = statistics.mean(all_times)
        stdev_time = statistics.stdev(all_times)
        
        # Z-score threshold (3 standard deviations)
        z_threshold = 3.0
        
        for method_name, profile in method_profiles.items():
            z_score = (profile.avg_time - mean_time) / stdev_time if stdev_time > 0 else 0
            
            if abs(z_score) > z_threshold:
                anomalies.append({
                    "method": method_name,
                    "anomaly_type": "execution_time",
                    "z_score": z_score,
                    "actual_time": profile.avg_time,
                    "expected_time": mean_time,
                    "deviation": profile.avg_time - mean_time,
                    "severity": "high" if abs(z_score) > 4 else "medium"
                })
        
        return anomalies
    
    def detect_memory_leaks(self, memory_snapshots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect potential memory leaks from memory snapshots"""
        
        if len(memory_snapshots) < 5:
            return []
        
        leaks = []
        
        # Extract memory usage over time
        memory_usage = [(s['timestamp'], s.get('rss_mb', 0)) for s in memory_snapshots]
        memory_usage.sort(key=lambda x: x[0])  # Sort by timestamp
        
        # Check for consistent memory growth
        memory_values = [usage for _, usage in memory_usage]
        
        # Calculate trend using linear regression (simplified)
        n = len(memory_values)
        if n >= 5:
            x_values = list(range(n))
            x_mean = statistics.mean(x_values)
            y_mean = statistics.mean(memory_values)
            
            # Calculate slope
            numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, memory_values))
            denominator = sum((x - x_mean) ** 2 for x in x_values)
            
            if denominator > 0:
                slope = numerator / denominator
                
                # If slope is positive and significant, potential memory leak
                if slope > 5.0:  # 5MB per measurement period
                    leaks.append({
                        "leak_type": "consistent_growth",
                        "growth_rate_mb_per_period": slope,
                        "total_growth_mb": memory_values[-1] - memory_values[0],
                        "measurement_count": n,
                        "severity": "high" if slope > 20 else "medium",
                        "estimated_leak_rate": f"{slope:.1f} MB per measurement period"
                    })
        
        return leaks
    
    def detect_cpu_spikes(self, cpu_samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect CPU usage spikes"""
        
        if not cpu_samples:
            return []
        
        spikes = []
        cpu_values = [sample.get('cpu_percent', 0) for sample in cpu_samples]
        
        if len(cpu_values) < 3:
            return spikes
        
        # Calculate mean and standard deviation
        mean_cpu = statistics.mean(cpu_values)
        stdev_cpu = statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0
        
        # Detect spikes (values significantly above mean)
        spike_threshold = mean_cpu + 2 * stdev_cpu
        
        for i, sample in enumerate(cpu_samples):
            cpu_percent = sample.get('cpu_percent', 0)
            
            if cpu_percent > spike_threshold and cpu_percent > 70:  # Absolute threshold
                spikes.append({
                    "timestamp": sample.get('timestamp'),
                    "cpu_percent": cpu_percent,
                    "mean_cpu": mean_cpu,
                    "deviation": cpu_percent - mean_cpu,
                    "z_score": (cpu_percent - mean_cpu) / stdev_cpu if stdev_cpu > 0 else 0,
                    "severity": "high" if cpu_percent > 90 else "medium"
                })
        
        return spikes
    
    def detect_io_bottlenecks(self, io_samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect I/O bottlenecks"""
        
        if not io_samples:
            return []
        
        bottlenecks = []
        
        # Calculate I/O rates
        total_read_bytes = sum(sample.get('read_bytes_delta', 0) for sample in io_samples)
        total_write_bytes = sum(sample.get('write_bytes_delta', 0) for sample in io_samples)
        total_read_ops = sum(sample.get('read_ops_delta', 0) for sample in io_samples)
        total_write_ops = sum(sample.get('write_ops_delta', 0) for sample in io_samples)
        
        # High I/O volume detection
        if total_read_bytes > 1024 * 1024 * 1024:  # > 1GB
            bottlenecks.append({
                "bottleneck_type": "high_read_volume",
                "total_read_gb": total_read_bytes / (1024 * 1024 * 1024),
                "severity": "medium",
                "recommendation": "Consider I/O optimization or caching"
            })
        
        if total_write_bytes > 512 * 1024 * 1024:  # > 512MB
            bottlenecks.append({
                "bottleneck_type": "high_write_volume", 
                "total_write_mb": total_write_bytes / (1024 * 1024),
                "severity": "medium",
                "recommendation": "Consider batching writes or async I/O"
            })
        
        # High I/O frequency detection
        if total_read_ops > 10000:
            bottlenecks.append({
                "bottleneck_type": "high_read_frequency",
                "total_read_ops": total_read_ops,
                "severity": "low",
                "recommendation": "Consider batching read operations"
            })
        
        if total_write_ops > 5000:
            bottlenecks.append({
                "bottleneck_type": "high_write_frequency",
                "total_write_ops": total_write_ops,
                "severity": "low", 
                "recommendation": "Consider batching write operations"
            })
        
        return bottlenecks
