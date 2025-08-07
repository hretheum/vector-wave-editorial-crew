"""
Flow Profiler - Comprehensive execution profiling for AI Writing Flow V2

This module provides detailed profiling of flow execution including:
- Method-level execution timing
- Memory allocation patterns
- CPU usage profiling  
- I/O operation analysis
- Critical path identification
"""

import cProfile
import io
import pstats
import time
import threading
import logging
import gc
import tracemalloc
import psutil
from typing import Dict, List, Any, Optional, Callable, NamedTuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from functools import wraps
import json

logger = logging.getLogger(__name__)


@dataclass
class ProfilingConfig:
    """Configuration for flow profiling"""
    
    # Profiling modes
    enable_cprofile: bool = True
    enable_memory_profiling: bool = True
    enable_cpu_monitoring: bool = True
    enable_io_profiling: bool = True
    
    # Sampling rates
    memory_sample_interval: float = 0.1  # seconds
    cpu_sample_interval: float = 0.1     # seconds
    io_sample_interval: float = 0.5      # seconds
    
    # Output options
    output_directory: str = "profiling_results"
    save_detailed_reports: bool = True
    save_flamegraph_data: bool = True
    
    # Performance thresholds
    slow_method_threshold: float = 1.0    # seconds
    memory_growth_threshold: int = 50     # MB
    cpu_spike_threshold: float = 80.0     # percent


class ProfilingData:
    """Container for profiling data"""
    
    def __init__(self):
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.cprofile_stats: Optional[pstats.Stats] = None
        self.memory_snapshots: List[Dict[str, Any]] = []
        self.cpu_samples: List[Dict[str, Any]] = []
        self.io_samples: List[Dict[str, Any]] = []
        self.method_timings: Dict[str, List[float]] = {}
        self.method_call_counts: Dict[str, int] = {}
        self.critical_path: List[str] = []
        self.bottlenecks: List[Dict[str, Any]] = []


@dataclass
class MethodProfile:
    """Profile data for a single method"""
    name: str
    call_count: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    memory_delta: int  # bytes
    cpu_usage: float   # percent
    is_bottleneck: bool = False


@dataclass
class ProfilingReport:
    """Comprehensive profiling report"""
    
    execution_id: str
    start_time: datetime
    end_time: datetime
    total_duration: float
    
    # Method profiling
    method_profiles: Dict[str, MethodProfile]
    critical_path: List[str]
    
    # Resource usage
    peak_memory_mb: float
    avg_cpu_percent: float
    peak_cpu_percent: float
    total_io_operations: int
    
    # Bottlenecks and hotspots
    performance_bottlenecks: List[Dict[str, Any]]
    memory_hotspots: List[Dict[str, Any]]
    cpu_hotspots: List[Dict[str, Any]]
    
    # Optimization recommendations
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for serialization"""
        return {
            "execution_id": self.execution_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "total_duration": self.total_duration,
            "method_profiles": {
                name: {
                    "name": profile.name,
                    "call_count": profile.call_count,
                    "total_time": profile.total_time,
                    "avg_time": profile.avg_time,
                    "min_time": profile.min_time,
                    "max_time": profile.max_time,
                    "memory_delta": profile.memory_delta,
                    "cpu_usage": profile.cpu_usage,
                    "is_bottleneck": profile.is_bottleneck
                }
                for name, profile in self.method_profiles.items()
            },
            "critical_path": self.critical_path,
            "peak_memory_mb": self.peak_memory_mb,
            "avg_cpu_percent": self.avg_cpu_percent,
            "peak_cpu_percent": self.peak_cpu_percent,
            "total_io_operations": self.total_io_operations,
            "performance_bottlenecks": self.performance_bottlenecks,
            "memory_hotspots": self.memory_hotspots,
            "cpu_hotspots": self.cpu_hotspots,
            "recommendations": self.recommendations
        }


class FlowProfiler:
    """
    Comprehensive flow execution profiler
    
    Provides detailed profiling of AI Writing Flow V2 execution including:
    - cProfile integration for detailed call statistics
    - Memory profiling with tracemalloc
    - CPU usage monitoring  
    - I/O operation tracking
    - Bottleneck detection and analysis
    """
    
    def __init__(self, config: Optional[ProfilingConfig] = None):
        """
        Initialize FlowProfiler
        
        Args:
            config: Profiling configuration
        """
        self.config = config or ProfilingConfig()
        self.profiling_data = ProfilingData()
        
        # Profiling state
        self._profiling_active = False
        self._cprofile: Optional[cProfile.Profile] = None
        self._monitoring_threads: List[threading.Thread] = []
        self._stop_monitoring = threading.Event()
        
        # Create output directory
        Path(self.config.output_directory).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🔍 FlowProfiler initialized with config: {self.config}")
    
    @contextmanager
    def profile_execution(self, execution_id: str):
        """
        Context manager for profiling flow execution
        
        Args:
            execution_id: Unique identifier for this execution
        """
        logger.info(f"🚀 Starting profiling for execution: {execution_id}")
        
        try:
            self._start_profiling(execution_id)
            yield self
        finally:
            self._stop_profiling()
            logger.info(f"✅ Profiling completed for execution: {execution_id}")
    
    def profile_method(self, method_name: str):
        """
        Decorator for profiling individual methods
        
        Args:
            method_name: Name of the method to profile
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self._profile_method_execution(method_name, func, *args, **kwargs)
            return wrapper
        return decorator
    
    def _start_profiling(self, execution_id: str) -> None:
        """Start all profiling activities"""
        self._profiling_active = True
        self.profiling_data.start_time = datetime.now(timezone.utc)
        
        # Start cProfile
        if self.config.enable_cprofile:
            self._cprofile = cProfile.Profile()
            self._cprofile.enable()
            logger.info("📊 cProfile started")
        
        # Start memory profiling
        if self.config.enable_memory_profiling:
            tracemalloc.start()
            self._start_memory_monitoring()
            logger.info("🧠 Memory profiling started")
        
        # Start CPU monitoring
        if self.config.enable_cpu_monitoring:
            self._start_cpu_monitoring()
            logger.info("💻 CPU monitoring started")
        
        # Start I/O monitoring
        if self.config.enable_io_profiling:
            self._start_io_monitoring()
            logger.info("💾 I/O monitoring started")
    
    def _stop_profiling(self) -> None:
        """Stop all profiling activities"""
        self._profiling_active = False
        self.profiling_data.end_time = datetime.now(timezone.utc)
        
        # Stop monitoring threads
        self._stop_monitoring.set()
        for thread in self._monitoring_threads:
            thread.join(timeout=1.0)
        
        # Stop cProfile
        if self._cprofile:
            self._cprofile.disable()
            logger.info("📊 cProfile stopped")
        
        # Stop memory profiling
        if self.config.enable_memory_profiling and tracemalloc.is_tracing():
            # Take final memory snapshot
            self._take_memory_snapshot("final")
            tracemalloc.stop()
            logger.info("🧠 Memory profiling stopped")
        
        logger.info("🛑 All profiling activities stopped")
    
    def _profile_method_execution(self, method_name: str, func: Callable, *args, **kwargs) -> Any:
        """Profile individual method execution"""
        if not self._profiling_active:
            return func(*args, **kwargs)
        
        logger.debug(f"📊 Profiling method: {method_name}")
        
        # Take memory snapshot before
        memory_before = self._get_current_memory_usage()
        cpu_before = psutil.cpu_percent()
        
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Take memory snapshot after
            memory_after = self._get_current_memory_usage()
            cpu_after = psutil.cpu_percent()
            
            # Record method timing
            if method_name not in self.profiling_data.method_timings:
                self.profiling_data.method_timings[method_name] = []
            self.profiling_data.method_timings[method_name].append(execution_time)
            
            # Update call count
            self.profiling_data.method_call_counts[method_name] = (
                self.profiling_data.method_call_counts.get(method_name, 0) + 1
            )
            
            # Check for bottlenecks
            if execution_time > self.config.slow_method_threshold:
                bottleneck = {
                    "method": method_name,
                    "execution_time": execution_time,
                    "memory_delta": memory_after - memory_before,
                    "cpu_usage": (cpu_before + cpu_after) / 2,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                self.profiling_data.bottlenecks.append(bottleneck)
                logger.warning(f"⚠️ Bottleneck detected in {method_name}: {execution_time:.2f}s")
            
            logger.debug(f"✅ Method {method_name} profiled: {execution_time:.3f}s")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error profiling method {method_name}: {str(e)}")
            raise
    
    def _start_memory_monitoring(self) -> None:
        """Start memory monitoring thread"""
        def monitor_memory():
            while not self._stop_monitoring.is_set():
                try:
                    if tracemalloc.is_tracing():
                        self._take_memory_snapshot("periodic")
                    time.sleep(self.config.memory_sample_interval)
                except Exception as e:
                    logger.error(f"Memory monitoring error: {e}")
        
        thread = threading.Thread(target=monitor_memory, daemon=True)
        thread.start()
        self._monitoring_threads.append(thread)
    
    def _start_cpu_monitoring(self) -> None:
        """Start CPU monitoring thread"""
        def monitor_cpu():
            while not self._stop_monitoring.is_set():
                try:
                    cpu_percent = psutil.cpu_percent(interval=None)
                    cpu_sample = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "cpu_percent": cpu_percent,
                        "load_avg": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
                    }
                    self.profiling_data.cpu_samples.append(cpu_sample)
                    
                    # Check for CPU spikes
                    if cpu_percent > self.config.cpu_spike_threshold:
                        logger.warning(f"🔥 CPU spike detected: {cpu_percent:.1f}%")
                    
                    time.sleep(self.config.cpu_sample_interval)
                except Exception as e:
                    logger.error(f"CPU monitoring error: {e}")
        
        thread = threading.Thread(target=monitor_cpu, daemon=True)
        thread.start()
        self._monitoring_threads.append(thread)
    
    def _start_io_monitoring(self) -> None:
        """Start I/O monitoring thread"""
        def monitor_io():
            last_io_counters = psutil.disk_io_counters()
            
            while not self._stop_monitoring.is_set():
                try:
                    current_io_counters = psutil.disk_io_counters()
                    
                    if last_io_counters and current_io_counters:
                        read_bytes_delta = current_io_counters.read_bytes - last_io_counters.read_bytes
                        write_bytes_delta = current_io_counters.write_bytes - last_io_counters.write_bytes
                        
                        io_sample = {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "read_bytes_delta": read_bytes_delta,
                            "write_bytes_delta": write_bytes_delta,
                            "read_ops_delta": current_io_counters.read_count - last_io_counters.read_count,
                            "write_ops_delta": current_io_counters.write_count - last_io_counters.write_count
                        }
                        self.profiling_data.io_samples.append(io_sample)
                    
                    last_io_counters = current_io_counters
                    time.sleep(self.config.io_sample_interval)
                    
                except Exception as e:
                    logger.error(f"I/O monitoring error: {e}")
        
        thread = threading.Thread(target=monitor_io, daemon=True)
        thread.start()
        self._monitoring_threads.append(thread)
    
    def _take_memory_snapshot(self, snapshot_type: str) -> None:
        """Take memory snapshot"""
        try:
            if not tracemalloc.is_tracing():
                return
            
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            
            # Get current memory usage
            process = psutil.Process()
            memory_info = process.memory_info()
            
            memory_snapshot = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "snapshot_type": snapshot_type,
                "rss_mb": memory_info.rss / 1024 / 1024,  # Resident Set Size
                "vms_mb": memory_info.vms / 1024 / 1024,  # Virtual Memory Size
                "top_memory_users": [
                    {
                        "file": stat.traceback.format()[0] if stat.traceback else "unknown",
                        "size_mb": stat.size / 1024 / 1024,
                        "count": stat.count
                    }
                    for stat in top_stats[:10]  # Top 10 memory users
                ]
            }
            
            self.profiling_data.memory_snapshots.append(memory_snapshot)
            
        except Exception as e:
            logger.error(f"Error taking memory snapshot: {e}")
    
    def _get_current_memory_usage(self) -> int:
        """Get current memory usage in bytes"""
        try:
            process = psutil.Process()
            return process.memory_info().rss
        except Exception:
            return 0
    
    def generate_report(self, execution_id: str) -> ProfilingReport:
        """
        Generate comprehensive profiling report
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            ProfilingReport with detailed analysis
        """
        logger.info(f"📊 Generating profiling report for: {execution_id}")
        
        if not self.profiling_data.start_time or not self.profiling_data.end_time:
            raise ValueError("Profiling data incomplete - ensure profiling was started and stopped")
        
        total_duration = (
            self.profiling_data.end_time - self.profiling_data.start_time
        ).total_seconds()
        
        # Process cProfile data
        cprofile_stats = None
        if self._cprofile:
            stats_stream = io.StringIO()
            cprofile_stats = pstats.Stats(self._cprofile, stream=stats_stream)
            cprofile_stats.sort_stats('cumulative')
            self.profiling_data.cprofile_stats = cprofile_stats
        
        # Generate method profiles
        method_profiles = self._generate_method_profiles()
        
        # Identify critical path
        critical_path = self._identify_critical_path()
        
        # Calculate resource usage
        peak_memory_mb = self._calculate_peak_memory()
        avg_cpu_percent, peak_cpu_percent = self._calculate_cpu_usage()
        total_io_operations = self._calculate_total_io_operations()
        
        # Detect hotspots
        performance_bottlenecks = self._detect_performance_bottlenecks()
        memory_hotspots = self._detect_memory_hotspots()
        cpu_hotspots = self._detect_cpu_hotspots()
        
        # Generate optimization recommendations
        recommendations = self._generate_optimization_recommendations(
            method_profiles, performance_bottlenecks, memory_hotspots
        )
        
        report = ProfilingReport(
            execution_id=execution_id,
            start_time=self.profiling_data.start_time,
            end_time=self.profiling_data.end_time,
            total_duration=total_duration,
            method_profiles=method_profiles,
            critical_path=critical_path,
            peak_memory_mb=peak_memory_mb,
            avg_cpu_percent=avg_cpu_percent,
            peak_cpu_percent=peak_cpu_percent,
            total_io_operations=total_io_operations,
            performance_bottlenecks=performance_bottlenecks,
            memory_hotspots=memory_hotspots,
            cpu_hotspots=cpu_hotspots,
            recommendations=recommendations
        )
        
        # Save detailed reports if configured
        if self.config.save_detailed_reports:
            self._save_detailed_reports(execution_id, report)
        
        logger.info(f"✅ Profiling report generated successfully")
        return report
    
    def _generate_method_profiles(self) -> Dict[str, MethodProfile]:
        """Generate detailed method profiles"""
        method_profiles = {}
        
        for method_name, timings in self.profiling_data.method_timings.items():
            if not timings:
                continue
            
            call_count = self.profiling_data.method_call_counts.get(method_name, 0)
            total_time = sum(timings)
            avg_time = total_time / len(timings)
            min_time = min(timings)
            max_time = max(timings)
            
            # Estimate memory and CPU usage for this method
            method_memory_delta = 0
            method_cpu_usage = 0.0
            
            # Find bottlenecks for this method
            method_bottlenecks = [
                b for b in self.profiling_data.bottlenecks 
                if b.get('method') == method_name
            ]
            
            if method_bottlenecks:
                method_memory_delta = sum(b.get('memory_delta', 0) for b in method_bottlenecks)
                method_cpu_usage = sum(b.get('cpu_usage', 0) for b in method_bottlenecks) / len(method_bottlenecks)
            
            is_bottleneck = (
                max_time > self.config.slow_method_threshold or
                method_memory_delta > self.config.memory_growth_threshold * 1024 * 1024  # Convert MB to bytes
            )
            
            method_profiles[method_name] = MethodProfile(
                name=method_name,
                call_count=call_count,
                total_time=total_time,
                avg_time=avg_time,
                min_time=min_time,
                max_time=max_time,
                memory_delta=method_memory_delta,
                cpu_usage=method_cpu_usage,
                is_bottleneck=is_bottleneck
            )
        
        return method_profiles
    
    def _identify_critical_path(self) -> List[str]:
        """Identify the critical path through the execution"""
        # Sort methods by total execution time (descending)
        method_times = [
            (method, sum(timings))
            for method, timings in self.profiling_data.method_timings.items()
        ]
        method_times.sort(key=lambda x: x[1], reverse=True)
        
        # Critical path is the top methods that make up 80% of execution time
        total_time = sum(time for _, time in method_times)
        critical_path = []
        cumulative_time = 0.0
        
        for method, time in method_times:
            critical_path.append(method)
            cumulative_time += time
            
            if cumulative_time >= 0.8 * total_time:  # 80% of total time
                break
        
        return critical_path
    
    def _calculate_peak_memory(self) -> float:
        """Calculate peak memory usage in MB"""
        if not self.profiling_data.memory_snapshots:
            return 0.0
        
        return max(
            snapshot.get('rss_mb', 0) 
            for snapshot in self.profiling_data.memory_snapshots
        )
    
    def _calculate_cpu_usage(self) -> tuple[float, float]:
        """Calculate average and peak CPU usage"""
        if not self.profiling_data.cpu_samples:
            return 0.0, 0.0
        
        cpu_values = [
            sample.get('cpu_percent', 0) 
            for sample in self.profiling_data.cpu_samples
        ]
        
        avg_cpu = sum(cpu_values) / len(cpu_values)
        peak_cpu = max(cpu_values)
        
        return avg_cpu, peak_cpu
    
    def _calculate_total_io_operations(self) -> int:
        """Calculate total I/O operations"""
        if not self.profiling_data.io_samples:
            return 0
        
        total_ops = 0
        for sample in self.profiling_data.io_samples:
            total_ops += sample.get('read_ops_delta', 0)
            total_ops += sample.get('write_ops_delta', 0)
        
        return total_ops
    
    def _detect_performance_bottlenecks(self) -> List[Dict[str, Any]]:
        """Detect performance bottlenecks"""
        return self.profiling_data.bottlenecks.copy()
    
    def _detect_memory_hotspots(self) -> List[Dict[str, Any]]:
        """Detect memory hotspots"""
        hotspots = []
        
        for snapshot in self.profiling_data.memory_snapshots:
            if snapshot.get('rss_mb', 0) > 100:  # More than 100MB
                hotspots.append({
                    "timestamp": snapshot['timestamp'],
                    "memory_mb": snapshot['rss_mb'],
                    "snapshot_type": snapshot['snapshot_type'],
                    "top_users": snapshot.get('top_memory_users', [])[:3]
                })
        
        return hotspots
    
    def _detect_cpu_hotspots(self) -> List[Dict[str, Any]]:
        """Detect CPU hotspots"""
        hotspots = []
        
        for sample in self.profiling_data.cpu_samples:
            cpu_percent = sample.get('cpu_percent', 0)
            if cpu_percent > self.config.cpu_spike_threshold:
                hotspots.append({
                    "timestamp": sample['timestamp'],
                    "cpu_percent": cpu_percent,
                    "load_avg": sample.get('load_avg')
                })
        
        return hotspots
    
    def _generate_optimization_recommendations(
        self, 
        method_profiles: Dict[str, MethodProfile],
        performance_bottlenecks: List[Dict[str, Any]],
        memory_hotspots: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Performance recommendations
        bottleneck_methods = [profile for profile in method_profiles.values() if profile.is_bottleneck]
        if bottleneck_methods:
            recommendations.append(
                f"Consider optimizing {len(bottleneck_methods)} bottleneck methods: "
                f"{', '.join(p.name for p in bottleneck_methods[:3])}"
            )
        
        # Memory recommendations
        if memory_hotspots:
            peak_memory = max(h['memory_mb'] for h in memory_hotspots)
            recommendations.append(
                f"Peak memory usage of {peak_memory:.1f}MB detected. "
                f"Consider memory optimization for high-usage components."
            )
        
        # Method call optimization
        high_call_count_methods = [
            profile for profile in method_profiles.values() 
            if profile.call_count > 100
        ]
        if high_call_count_methods:
            recommendations.append(
                f"Methods with high call counts detected: "
                f"{', '.join(p.name for p in high_call_count_methods[:3])}. "
                f"Consider caching or batching optimizations."
            )
        
        # CPU optimization
        avg_cpu = sum(s.get('cpu_percent', 0) for s in self.profiling_data.cpu_samples)
        if self.profiling_data.cpu_samples:
            avg_cpu /= len(self.profiling_data.cpu_samples)
            if avg_cpu > 60:
                recommendations.append(
                    f"High average CPU usage ({avg_cpu:.1f}%). "
                    f"Consider async processing or algorithm optimization."
                )
        
        if not recommendations:
            recommendations.append("Performance looks good! No major optimizations needed.")
        
        return recommendations
    
    def _save_detailed_reports(self, execution_id: str, report: ProfilingReport) -> None:
        """Save detailed profiling reports to files"""
        output_dir = Path(self.config.output_directory) / execution_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save JSON report
        json_path = output_dir / "profiling_report.json"
        with open(json_path, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        logger.info(f"📄 JSON report saved: {json_path}")
        
        # Save cProfile stats
        if self.profiling_data.cprofile_stats:
            stats_path = output_dir / "cprofile_stats.txt"
            with open(stats_path, 'w') as f:
                self.profiling_data.cprofile_stats.print_stats(file=f)
            logger.info(f"📊 cProfile stats saved: {stats_path}")
        
        # Save memory snapshots
        memory_path = output_dir / "memory_snapshots.json"
        with open(memory_path, 'w') as f:
            json.dump(self.profiling_data.memory_snapshots, f, indent=2)
        logger.info(f"🧠 Memory snapshots saved: {memory_path}")
        
        # Save CPU samples
        cpu_path = output_dir / "cpu_samples.json"
        with open(cpu_path, 'w') as f:
            json.dump(self.profiling_data.cpu_samples, f, indent=2)
        logger.info(f"💻 CPU samples saved: {cpu_path}")
        
        # Save I/O samples
        io_path = output_dir / "io_samples.json"
        with open(io_path, 'w') as f:
            json.dump(self.profiling_data.io_samples, f, indent=2)
        logger.info(f"💾 I/O samples saved: {io_path}")
