"""
Development Performance Profiler - Task 11.1

Profiling tool specifically designed for local development environment
to identify bottlenecks and optimization opportunities.
"""

import time
import tracemalloc
import cProfile
import pstats
import io
import psutil
import asyncio
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from contextlib import contextmanager
from datetime import datetime
import json
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ProfileSection:
    """Single profiling section data"""
    name: str
    start_time: float
    end_time: Optional[float] = None
    memory_start: int = 0
    memory_peak: int = 0
    cpu_percent: float = 0.0
    io_reads: int = 0
    io_writes: int = 0
    subsections: List['ProfileSection'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """Calculate duration in seconds"""
        if self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    @property
    def memory_used(self) -> int:
        """Memory used in this section"""
        return self.memory_peak - self.memory_start


@dataclass
class DevelopmentProfile:
    """Complete development profiling results"""
    flow_name: str
    total_duration: float
    peak_memory_mb: float
    avg_cpu_percent: float
    sections: List[ProfileSection]
    bottlenecks: List[Dict[str, Any]]
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "flow_name": self.flow_name,
            "total_duration": self.total_duration,
            "peak_memory_mb": self.peak_memory_mb,
            "avg_cpu_percent": self.avg_cpu_percent,
            "sections": [self._section_to_dict(s) for s in self.sections],
            "bottlenecks": self.bottlenecks,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat()
        }
    
    def _section_to_dict(self, section: ProfileSection) -> Dict[str, Any]:
        """Convert section to dictionary"""
        return {
            "name": section.name,
            "duration": section.duration,
            "memory_mb": section.memory_used / 1024 / 1024,
            "cpu_percent": section.cpu_percent,
            "subsections": [self._section_to_dict(s) for s in section.subsections]
        }


class DevelopmentProfiler:
    """
    Performance profiler for local development environment.
    
    Features:
    - Execution time profiling with section breakdown
    - Memory usage tracking
    - CPU utilization monitoring
    - I/O operation tracking
    - Bottleneck detection
    - Development-specific recommendations
    """
    
    def __init__(self, enable_memory: bool = True, enable_cpu: bool = True):
        """
        Initialize development profiler
        
        Args:
            enable_memory: Enable memory profiling
            enable_cpu: Enable CPU profiling
        """
        self.enable_memory = enable_memory
        self.enable_cpu = enable_cpu
        self.current_sections: List[ProfileSection] = []
        self.all_sections: List[ProfileSection] = []
        self.process = psutil.Process()
        self._start_time = None
        self._cprofile = None
        
        logger.info(
            "Development profiler initialized",
            enable_memory=enable_memory,
            enable_cpu=enable_cpu
        )
    
    def start_profiling(self, flow_name: str):
        """Start profiling session"""
        self._start_time = time.time()
        self.flow_name = flow_name
        
        if self.enable_memory:
            tracemalloc.start()
        
        if self.enable_cpu:
            self._cprofile = cProfile.Profile()
            self._cprofile.enable()
        
        logger.info(f"Started profiling for flow: {flow_name}")
    
    @contextmanager
    def profile_section(self, section_name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Profile a specific code section
        
        Args:
            section_name: Name of the section being profiled
            metadata: Additional metadata for the section
        """
        section = ProfileSection(
            name=section_name,
            start_time=time.time(),
            metadata=metadata or {}
        )
        
        # Track memory at start
        if self.enable_memory:
            section.memory_start = tracemalloc.get_traced_memory()[0]
        
        # Track I/O at start (if available - not on macOS)
        io_start = None
        try:
            io_start = self.process.io_counters()
        except AttributeError:
            pass  # io_counters not available on macOS
        
        # Add to current sections stack
        self.current_sections.append(section)
        
        try:
            yield section
        finally:
            # Complete section
            section.end_time = time.time()
            
            # Track memory peak
            if self.enable_memory:
                current, peak = tracemalloc.get_traced_memory()
                section.memory_peak = peak
            
            # Track CPU usage
            if self.enable_cpu:
                section.cpu_percent = self.process.cpu_percent()
            
            # Track I/O (if available)
            if io_start:
                try:
                    io_end = self.process.io_counters()
                    section.io_reads = io_end.read_count - io_start.read_count
                    section.io_writes = io_end.write_count - io_start.write_count
                except AttributeError:
                    pass  # io_counters not available on macOS
            
            # Remove from current stack
            self.current_sections.pop()
            
            # Add to parent or all sections
            if self.current_sections:
                parent = self.current_sections[-1]
                parent.subsections.append(section)
            else:
                self.all_sections.append(section)
            
            logger.debug(
                f"Profiled section: {section_name}",
                duration=section.duration,
                memory_mb=(section.memory_peak - section.memory_start) / 1024 / 1024
            )
    
    def stop_profiling(self) -> DevelopmentProfile:
        """
        Stop profiling and generate report
        
        Returns:
            Development profile with analysis
        """
        total_duration = time.time() - self._start_time
        
        # Stop CPU profiling
        if self._cprofile:
            self._cprofile.disable()
        
        # Get memory stats
        peak_memory = 0
        if self.enable_memory:
            current, peak = tracemalloc.get_traced_memory()
            peak_memory = peak
            tracemalloc.stop()
        
        # Calculate average CPU
        avg_cpu = sum(s.cpu_percent for s in self._flatten_sections()) / len(self.all_sections) if self.all_sections else 0
        
        # Detect bottlenecks
        bottlenecks = self._detect_bottlenecks()
        
        # Generate recommendations
        recommendations = self._generate_recommendations(bottlenecks)
        
        profile = DevelopmentProfile(
            flow_name=self.flow_name,
            total_duration=total_duration,
            peak_memory_mb=peak_memory / 1024 / 1024,
            avg_cpu_percent=avg_cpu,
            sections=self.all_sections,
            bottlenecks=bottlenecks,
            recommendations=recommendations
        )
        
        logger.info(
            f"Profiling complete for {self.flow_name}",
            total_duration=total_duration,
            peak_memory_mb=profile.peak_memory_mb,
            bottleneck_count=len(bottlenecks)
        )
        
        return profile
    
    def _flatten_sections(self) -> List[ProfileSection]:
        """Flatten all sections including subsections"""
        flattened = []
        
        def add_section(section: ProfileSection):
            flattened.append(section)
            for subsection in section.subsections:
                add_section(subsection)
        
        for section in self.all_sections:
            add_section(section)
        
        return flattened
    
    def _detect_bottlenecks(self) -> List[Dict[str, Any]]:
        """Detect performance bottlenecks"""
        bottlenecks = []
        all_sections = self._flatten_sections()
        
        if not all_sections:
            return bottlenecks
        
        # Calculate thresholds
        avg_duration = sum(s.duration for s in all_sections) / len(all_sections)
        avg_memory = sum(s.memory_used for s in all_sections) / len(all_sections)
        
        # Ensure minimum thresholds for dev environment
        avg_duration = max(avg_duration, 0.1)  # At least 100ms
        avg_memory = max(avg_memory, 1024 * 1024)  # At least 1MB
        
        for section in all_sections:
            issues = []
            
            # Slow execution (2x average)
            if section.duration > avg_duration * 2:
                issues.append({
                    "type": "slow_execution",
                    "severity": "high" if section.duration > avg_duration * 3 else "medium",
                    "details": f"Takes {section.duration:.2f}s (avg: {avg_duration:.2f}s)"
                })
            
            # High memory usage (3x average)
            if section.memory_used > avg_memory * 3:
                issues.append({
                    "type": "high_memory",
                    "severity": "high" if section.memory_used > avg_memory * 5 else "medium",
                    "details": f"Uses {section.memory_used/1024/1024:.1f}MB"
                })
            
            # High CPU usage
            if section.cpu_percent > 80:
                issues.append({
                    "type": "high_cpu",
                    "severity": "medium",
                    "details": f"CPU usage: {section.cpu_percent:.1f}%"
                })
            
            # High I/O
            if section.io_reads > 1000 or section.io_writes > 1000:
                issues.append({
                    "type": "high_io",
                    "severity": "low",
                    "details": f"I/O: {section.io_reads}r/{section.io_writes}w"
                })
            
            if issues:
                bottlenecks.append({
                    "section": section.name,
                    "duration": section.duration,
                    "issues": issues
                })
        
        # Sort by severity and duration
        bottlenecks.sort(key=lambda x: x["duration"], reverse=True)
        
        return bottlenecks
    
    def _generate_recommendations(self, bottlenecks: List[Dict[str, Any]]) -> List[str]:
        """Generate development-specific recommendations"""
        recommendations = []
        all_sections = self._flatten_sections()
        
        # Analyze all sections, not just bottlenecks
        for section in all_sections:
            name_lower = section.name.lower()
            
            # Knowledge Base recommendations
            if "knowledge" in name_lower or "kb" in name_lower:
                if section.duration > 0.2:  # More than 200ms
                    recommendations.append(f"Add local KB cache for {section.name}")
                    
            # Validation recommendations  
            elif "validation" in name_lower or "validate" in name_lower:
                if section.duration > 0.1:  # More than 100ms
                    recommendations.append(f"Add skip_validation flag for dev mode in {section.name}")
                    
            # Model loading recommendations
            elif "model" in name_lower or "loading" in name_lower:
                if section.duration > 0.3:  # More than 300ms
                    recommendations.append("Consider using smaller models for local development")
                    recommendations.append("Implement model caching between runs")
        
        # Analyze bottleneck patterns
        slow_sections = [b for b in bottlenecks if any(i["type"] == "slow_execution" for i in b["issues"])]
        memory_sections = [b for b in bottlenecks if any(i["type"] == "high_memory" for i in b["issues"])]
        io_sections = [b for b in bottlenecks if any(i["type"] == "high_io" for i in b["issues"])]
        
        # Slow execution recommendations
        if len(slow_sections) > 2:
            recommendations.append("Consider implementing caching for frequently executed sections")
            recommendations.append("Enable hot-reload to avoid full reinitialization")
        
        # Memory recommendations
        if memory_sections:
            recommendations.append("Implement lazy loading for large objects")
        
        # I/O recommendations
        if io_sections:
            recommendations.append("Add file caching to reduce I/O operations")
            recommendations.append("Consider in-memory alternatives for development")
        
        # General dev recommendations
        if not bottlenecks and not recommendations:
            recommendations.append("Performance is good! Consider adding more detailed profiling")
        else:
            if "DEV_MODE" not in str(recommendations):
                recommendations.append("Add DEV_MODE flag to skip non-essential operations")
            if "progressive" not in str(recommendations):
                recommendations.append("Implement progressive loading for better perceived performance")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        return unique_recommendations
    
    def save_profile(self, profile: DevelopmentProfile, output_path: Optional[str] = None):
        """Save profile to JSON file"""
        if not output_path:
            output_path = f"profiles/dev_profile_{profile.flow_name}_{profile.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(profile.to_dict(), f, indent=2)
        
        logger.info(f"Profile saved to: {output_path}")
        
        # Also save CPU profile if enabled
        if self._cprofile:
            stats_path = output_path.replace('.json', '_cpu.stats')
            self._cprofile.dump_stats(stats_path)
            
            # Generate readable report
            report_path = output_path.replace('.json', '_cpu.txt')
            with open(report_path, 'w') as f:
                stats = pstats.Stats(self._cprofile, stream=f)
                stats.sort_stats('cumulative')
                stats.print_stats(30)  # Top 30 functions
    
    def print_summary(self, profile: DevelopmentProfile):
        """Print human-readable summary"""
        print("\n" + "="*60)
        print(f"📊 Development Performance Profile: {profile.flow_name}")
        print("="*60)
        print(f"⏱️  Total Duration: {profile.total_duration:.2f}s")
        print(f"💾 Peak Memory: {profile.peak_memory_mb:.1f}MB")
        print(f"🖥️  Avg CPU: {profile.avg_cpu_percent:.1f}%")
        print(f"🔍 Bottlenecks Found: {len(profile.bottlenecks)}")
        
        if profile.bottlenecks:
            print("\n🚨 Top Bottlenecks:")
            for i, bottleneck in enumerate(profile.bottlenecks[:5], 1):
                print(f"\n{i}. {bottleneck['section']} ({bottleneck['duration']:.2f}s)")
                for issue in bottleneck['issues']:
                    print(f"   - {issue['type']}: {issue['details']}")
        
        if profile.recommendations:
            print("\n💡 Recommendations:")
            for i, rec in enumerate(profile.recommendations, 1):
                print(f"{i}. {rec}")
        
        print("\n" + "="*60)


# Convenience function for profiling flows
def profile_flow(flow_callable: Callable, *args, **kwargs) -> DevelopmentProfile:
    """
    Profile a flow execution
    
    Args:
        flow_callable: Flow function to profile
        *args, **kwargs: Arguments for the flow
        
    Returns:
        Development profile
    """
    profiler = DevelopmentProfiler()
    profiler.start_profiling(flow_callable.__name__)
    
    try:
        # Execute flow
        if asyncio.iscoroutinefunction(flow_callable):
            asyncio.run(flow_callable(*args, **kwargs))
        else:
            flow_callable(*args, **kwargs)
    finally:
        profile = profiler.stop_profiling()
        profiler.print_summary(profile)
        profiler.save_profile(profile)
    
    return profile