"""
Resource-Aware Local Setup - Task 11.3

Automatically adjusts system configuration based on available resources
for optimal local development performance.
"""

import os
import psutil
import platform
from typing import Dict, Any, Optional
from dataclasses import dataclass
import structlog

from ..config.dev_config import get_dev_config

logger = structlog.get_logger(__name__)


@dataclass
class SystemResources:
    """System resource information"""
    cpu_count: int
    cpu_freq_mhz: float
    memory_total_gb: float
    memory_available_gb: float
    disk_free_gb: float
    platform: str
    python_version: str
    
    @property
    def memory_used_percent(self) -> float:
        """Memory usage percentage"""
        return ((self.memory_total_gb - self.memory_available_gb) / self.memory_total_gb) * 100
    
    @property
    def is_low_memory(self) -> bool:
        """Check if system has low memory"""
        return self.memory_available_gb < 2.0  # Less than 2GB available
    
    @property
    def is_low_cpu(self) -> bool:
        """Check if system has low CPU resources"""
        return self.cpu_count < 4 or self.cpu_freq_mhz < 2000
    
    @property
    def resource_tier(self) -> str:
        """Determine resource tier: low, medium, high"""
        score = 0
        
        # CPU scoring
        if self.cpu_count >= 8:
            score += 2
        elif self.cpu_count >= 4:
            score += 1
        
        # Memory scoring
        if self.memory_total_gb >= 16:
            score += 2
        elif self.memory_total_gb >= 8:
            score += 1
        
        # Classify
        if score >= 3:
            return "high"
        elif score >= 2:
            return "medium"
        else:
            return "low"


class ResourceAwareManager:
    """
    Manages resource-aware configuration adjustments.
    
    Features:
    - Automatic resource detection
    - Dynamic configuration adjustment
    - Performance recommendations
    - Resource monitoring
    """
    
    def __init__(self):
        """Initialize resource manager"""
        self.resources = self._detect_resources()
        self.config = get_dev_config()
        
        logger.info(
            "Resource manager initialized",
            tier=self.resources.resource_tier,
            cpu_count=self.resources.cpu_count,
            memory_gb=f"{self.resources.memory_total_gb:.1f}",
            platform=self.resources.platform
        )
    
    def _detect_resources(self) -> SystemResources:
        """Detect system resources"""
        # CPU info
        cpu_count = psutil.cpu_count(logical=False) or psutil.cpu_count() or 2
        cpu_freq = psutil.cpu_freq()
        cpu_freq_mhz = cpu_freq.current if cpu_freq else 2000.0
        
        # Memory info
        memory = psutil.virtual_memory()
        memory_total_gb = memory.total / (1024 ** 3)
        memory_available_gb = memory.available / (1024 ** 3)
        
        # Disk info
        disk = psutil.disk_usage('/')
        disk_free_gb = disk.free / (1024 ** 3)
        
        # Platform info
        platform_name = platform.system()
        python_version = platform.python_version()
        
        return SystemResources(
            cpu_count=cpu_count,
            cpu_freq_mhz=cpu_freq_mhz,
            memory_total_gb=memory_total_gb,
            memory_available_gb=memory_available_gb,
            disk_free_gb=disk_free_gb,
            platform=platform_name,
            python_version=python_version
        )
    
    def get_optimized_config(self) -> Dict[str, Any]:
        """
        Get configuration optimized for current resources.
        
        Returns:
            Optimized configuration dictionary
        """
        tier = self.resources.resource_tier
        
        if tier == "low":
            return self._get_low_resource_config()
        elif tier == "medium":
            return self._get_medium_resource_config()
        else:
            return self._get_high_resource_config()
    
    def _get_low_resource_config(self) -> Dict[str, Any]:
        """Configuration for low-resource systems"""
        logger.info("Applying low-resource optimizations")
        
        return {
            # Use minimal models
            "model_override": "gpt-3.5-turbo",
            "use_smaller_models": True,
            
            # Limit concurrency
            "max_concurrent_agents": 1,
            "max_workers": 2,
            
            # Aggressive caching
            "enable_cache": True,
            "cache_ttl_seconds": 7200,  # 2 hours
            "kb_cache_size": 50,  # Smaller cache
            
            # Reduce timeouts
            "request_timeout": 20,
            
            # Disable non-essential features
            "skip_validation": True,
            "disable_animations": True,
            "verbose_logging": False,
            
            # Memory management
            "batch_size": 10,
            "chunk_size": 1000,
            
            # UI optimizations
            "ui_update_interval_ms": 2000,  # Less frequent updates
        }
    
    def _get_medium_resource_config(self) -> Dict[str, Any]:
        """Configuration for medium-resource systems"""
        logger.info("Applying medium-resource optimizations")
        
        return {
            # Use balanced models
            "model_override": "gpt-3.5-turbo",
            "use_smaller_models": True,
            
            # Moderate concurrency
            "max_concurrent_agents": 2,
            "max_workers": 4,
            
            # Standard caching
            "enable_cache": True,
            "cache_ttl_seconds": 3600,  # 1 hour
            "kb_cache_size": 100,
            
            # Standard timeouts
            "request_timeout": 30,
            
            # Balanced features
            "skip_validation": False,
            "disable_animations": True,
            "verbose_logging": True,
            
            # Memory management
            "batch_size": 50,
            "chunk_size": 5000,
            
            # UI optimizations
            "ui_update_interval_ms": 1000,
        }
    
    def _get_high_resource_config(self) -> Dict[str, Any]:
        """Configuration for high-resource systems"""
        logger.info("Applying high-resource optimizations")
        
        return {
            # Use best models
            "model_override": None,  # Use default (GPT-4)
            "use_smaller_models": False,
            
            # Maximum concurrency
            "max_concurrent_agents": 4,
            "max_workers": 8,
            
            # Extended caching
            "enable_cache": True,
            "cache_ttl_seconds": 1800,  # 30 minutes
            "kb_cache_size": 200,
            
            # Relaxed timeouts
            "request_timeout": 60,
            
            # All features enabled
            "skip_validation": False,
            "disable_animations": False,
            "verbose_logging": True,
            
            # Memory management
            "batch_size": 100,
            "chunk_size": 10000,
            
            # UI optimizations
            "ui_update_interval_ms": 500,  # Smooth updates
        }
    
    def apply_resource_config(self) -> Dict[str, Any]:
        """Apply resource-aware configuration to current environment"""
        optimized = self.get_optimized_config()
        
        # Update environment variables
        env_mappings = {
            "skip_validation": "SKIP_VALIDATION",
            "verbose_logging": "VERBOSE",
            "model_override": "MODEL_OVERRIDE",
        }
        
        for key, env_var in env_mappings.items():
            if key in optimized:
                os.environ[env_var] = str(optimized[key])
        
        logger.info(
            "Resource configuration applied",
            tier=self.resources.resource_tier,
            adjustments=len(optimized)
        )
        
        return optimized
    
    def get_recommendations(self) -> list[str]:
        """Get performance recommendations based on resources"""
        recommendations = []
        
        # Low memory recommendations
        if self.resources.is_low_memory:
            recommendations.append(
                f"Low memory detected ({self.resources.memory_available_gb:.1f}GB available). "
                "Consider closing other applications."
            )
            recommendations.append("Enable aggressive caching to reduce memory usage")
            recommendations.append("Use smaller batch sizes for processing")
        
        # Low CPU recommendations
        if self.resources.is_low_cpu:
            recommendations.append(
                f"Limited CPU resources ({self.resources.cpu_count} cores). "
                "Reduce concurrent agent execution."
            )
            recommendations.append("Disable verbose logging for better performance")
        
        # Disk space check
        if self.resources.disk_free_gb < 5:
            recommendations.append(
                f"Low disk space ({self.resources.disk_free_gb:.1f}GB free). "
                "Clear cache regularly."
            )
        
        # Platform-specific
        if self.resources.platform == "Darwin":  # macOS
            recommendations.append("Consider using Metal Performance Shaders for ML tasks")
        elif self.resources.platform == "Linux":
            recommendations.append("Enable huge pages for better memory performance")
        
        # General recommendations based on tier
        tier = self.resources.resource_tier
        if tier == "low":
            recommendations.append("Run one flow at a time for best performance")
            recommendations.append("Use mock services when possible")
        elif tier == "medium":
            recommendations.append("Current configuration is balanced for your system")
        else:
            recommendations.append("Your system can handle parallel flow execution")
            recommendations.append("Consider enabling advanced features")
        
        return recommendations
    
    def monitor_resources(self) -> Dict[str, Any]:
        """Monitor current resource usage"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024 ** 3),
            "disk_read_mb": disk_io.read_bytes / (1024 ** 2) if disk_io else 0,
            "disk_write_mb": disk_io.write_bytes / (1024 ** 2) if disk_io else 0,
            "resource_tier": self.resources.resource_tier
        }
    
    def should_throttle(self) -> bool:
        """Check if system should throttle operations"""
        # High memory usage
        if psutil.virtual_memory().percent > 90:
            logger.warning("High memory usage detected, throttling recommended")
            return True
        
        # High CPU usage
        if psutil.cpu_percent(interval=0.1) > 90:
            logger.warning("High CPU usage detected, throttling recommended")
            return True
        
        return False
    
    def print_resource_summary(self):
        """Print resource summary"""
        print("\n💻 System Resource Summary")
        print("=" * 50)
        print(f"Platform: {self.resources.platform}")
        print(f"Python: {self.resources.python_version}")
        print(f"CPU: {self.resources.cpu_count} cores @ {self.resources.cpu_freq_mhz:.0f}MHz")
        print(f"Memory: {self.resources.memory_total_gb:.1f}GB total, "
              f"{self.resources.memory_available_gb:.1f}GB available")
        print(f"Disk: {self.resources.disk_free_gb:.1f}GB free")
        print(f"Resource Tier: {self.resources.resource_tier.upper()}")
        print("=" * 50)
        
        # Print recommendations
        recommendations = self.get_recommendations()
        if recommendations:
            print("\n💡 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
        
        print()


# Global resource manager instance
_resource_manager: Optional[ResourceAwareManager] = None

def get_resource_manager() -> ResourceAwareManager:
    """Get or create resource manager"""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceAwareManager()
    return _resource_manager


def auto_configure_for_resources() -> Dict[str, Any]:
    """Automatically configure system based on available resources"""
    manager = get_resource_manager()
    return manager.apply_resource_config()