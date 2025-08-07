"""
Optimized CrewAI Flow for Development - Task 11.2

Implements optimizations for faster local development:
- Caching integration
- Development shortcuts
- Performance improvements
"""

import time
from typing import Dict, Any, Optional, List
from contextlib import contextmanager

from ..crewai_flow.flows.ai_writing_flow import AIWritingFlow
from ..crewai_flow.flows.ui_integrated_flow import UIIntegratedFlow
from ..config.dev_config import get_dev_config
from .dev_cache import (
    get_dev_cache, 
    cache_kb_query, 
    cache_model_response,
    cache_validation,
    DevPerformanceMonitor,
    HotReloadManager
)
from ..profiling.dev_profiler import DevelopmentProfiler

import structlog

logger = structlog.get_logger(__name__)


class OptimizedAIWritingFlow(AIWritingFlow):
    """
    Optimized AI Writing Flow for local development.
    
    Optimizations:
    - Cached KB queries
    - Smaller models for faster response
    - Validation skipping in dev mode
    - Performance monitoring
    - Hot reload support
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize optimized flow"""
        # Get dev config
        self.dev_config = get_dev_config()
        self.cache = get_dev_cache()
        self.perf_monitor = DevPerformanceMonitor()
        self.hot_reload = HotReloadManager()
        
        # Apply dev optimizations to config
        optimized_config = self._optimize_config(config or {})
        
        # Initialize parent with optimized config
        super().__init__(optimized_config)
        
        logger.info(
            "Optimized AI Writing Flow initialized",
            dev_mode=self.dev_config.dev_mode,
            cache_enabled=self.dev_config.enable_cache,
            model_override=self.dev_config.model_override
        )
    
    def _optimize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply development optimizations to config"""
        optimized = config.copy()
        
        if self.dev_config.dev_mode:
            # Use smaller, faster models
            if self.dev_config.use_smaller_models and self.dev_config.model_override:
                optimized['model'] = self.dev_config.model_override
                optimized['temperature'] = 0.1  # More deterministic for caching
            
            # Reduce timeouts
            optimized['timeout'] = self.dev_config.request_timeout
            
            # Limit concurrency
            optimized['max_concurrent'] = self.dev_config.max_concurrent_agents
            
            # Enable auto-approval if set
            if self.dev_config.auto_approve_human_review:
                optimized['auto_approve'] = True
            
            # Verbose logging
            optimized['verbose'] = self.dev_config.verbose_logging
        
        return optimized
    
    @contextmanager
    def _track_performance(self, operation: str):
        """Track operation performance"""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            self.perf_monitor.record_timing(operation, duration)
            logger.debug(f"{operation} took {duration:.3f}s")
    
    @cache_kb_query(ttl=3600)
    def _query_knowledge_base_cached(self, query: str, **kwargs) -> Dict[str, Any]:
        """Cached KB query implementation"""
        with self._track_performance("kb_query"):
            # Check if we should use local fallback
            if self.dev_config.kb_local_fallback:
                try:
                    return super()._query_knowledge_base(query, **kwargs)
                except Exception as e:
                    logger.warning(f"KB query failed, using fallback: {e}")
                    return {"results": [], "fallback": True}
            else:
                return super()._query_knowledge_base(query, **kwargs)
    
    def _query_knowledge_base(self, query: str, **kwargs) -> Dict[str, Any]:
        """Override to use cached version"""
        # Check hot reload
        if self.hot_reload.check_reload_needed():
            # Reload config
            from ..config.dev_config import reload_dev_config
            self.dev_config = reload_dev_config()
        
        return self._query_knowledge_base_cached(query, **kwargs)
    
    @cache_model_response(ttl=1800)
    def _generate_content_cached(self, prompt: str, **kwargs) -> str:
        """Cached content generation"""
        with self._track_performance("content_generation"):
            return super()._generate_content(prompt, **kwargs)
    
    def _generate_content(self, prompt: str, **kwargs) -> str:
        """Override to use cached version"""
        return self._generate_content_cached(prompt, **kwargs)
    
    @cache_validation(ttl=300)
    def _validate_content_cached(self, content: str, **kwargs) -> Dict[str, Any]:
        """Cached validation"""
        if self.dev_config.skip_validation:
            logger.info("Skipping validation in dev mode")
            return {
                "valid": True,
                "score": 1.0,
                "skipped": True,
                "reason": "DEV_MODE skip_validation enabled"
            }
        
        with self._track_performance("validation"):
            return super()._validate_content(content, **kwargs)
    
    def _validate_content(self, content: str, **kwargs) -> Dict[str, Any]:
        """Override to use cached version"""
        return self._validate_content_cached(content, **kwargs)
    
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Run flow with performance tracking"""
        logger.info("Starting optimized flow execution")
        
        # Enable profiling if verbose
        if self.dev_config.verbose_logging:
            profiler = DevelopmentProfiler()
            profiler.start_profiling(self.__class__.__name__)
        
        try:
            with self._track_performance("total_flow_execution"):
                result = super().run(inputs)
            
            # Print performance summary
            if self.dev_config.verbose_logging:
                self.perf_monitor.print_summary()
            
            return result
            
        finally:
            if self.dev_config.verbose_logging and 'profiler' in locals():
                profile = profiler.stop_profiling()
                profiler.print_summary(profile)
                profiler.save_profile(profile)


class OptimizedUIIntegratedFlow(UIIntegratedFlow):
    """
    Optimized UI Integrated Flow for development.
    
    Optimizations:
    - Reduced UI update frequency
    - Cached progress calculations
    - Mock UI for testing
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize optimized UI flow"""
        self.dev_config = get_dev_config()
        self.cache = get_dev_cache()
        self.perf_monitor = DevPerformanceMonitor()
        
        # Apply UI optimizations
        optimized_config = self._optimize_ui_config(config or {})
        
        super().__init__(optimized_config)
        
        logger.info(
            "Optimized UI Flow initialized",
            update_interval=self.dev_config.ui_update_interval_ms,
            auto_approve=self.dev_config.auto_approve_human_review
        )
    
    def _optimize_ui_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply UI-specific optimizations"""
        optimized = config.copy()
        
        if self.dev_config.dev_mode:
            # Reduce update frequency
            optimized['update_interval_ms'] = self.dev_config.ui_update_interval_ms
            
            # Disable animations
            optimized['disable_animations'] = self.dev_config.disable_animations
            
            # Auto-approve if enabled
            if self.dev_config.auto_approve_human_review:
                optimized['auto_mode'] = True
            
            # Mock services if needed
            if self.dev_config.mock_external_services:
                optimized['mock_ui_bridge'] = True
        
        return optimized
    
    async def _send_progress_update(self, stage: str, message: str, 
                                   progress_percent: Optional[float] = None,
                                   metadata: Optional[Dict[str, Any]] = None):
        """Optimized progress updates"""
        # Skip some updates in dev mode for performance
        if self.dev_config.dev_mode and progress_percent:
            # Only send updates at 10% intervals
            if int(progress_percent) % 10 != 0:
                return
        
        # Create performance monitor if not exists
        if not hasattr(self, 'perf_monitor'):
            self.perf_monitor = DevPerformanceMonitor()
            
        # Track performance if possible
        start = time.time()
        try:
            await super()._send_progress_update(stage, message, progress_percent, metadata)
        finally:
            if hasattr(self, 'perf_monitor'):
                self.perf_monitor.record_timing("ui_update", time.time() - start)


# Convenience functions for development
def create_optimized_flow(flow_type: str = "writing", **kwargs) -> Any:
    """
    Create an optimized flow for development.
    
    Args:
        flow_type: Type of flow ("writing" or "ui")
        **kwargs: Additional configuration
        
    Returns:
        Optimized flow instance
    """
    if flow_type == "writing":
        return OptimizedAIWritingFlow(kwargs)
    elif flow_type == "ui":
        return OptimizedUIIntegratedFlow(kwargs)
    else:
        raise ValueError(f"Unknown flow type: {flow_type}")


def clear_dev_cache(pattern: Optional[str] = None):
    """Clear development cache"""
    cache = get_dev_cache()
    cache.invalidate(pattern)
    logger.info(f"Cleared cache: {pattern or 'all'}")


def get_performance_stats() -> Dict[str, Any]:
    """Get current performance statistics"""
    # This would aggregate stats from various sources
    cache = get_dev_cache()
    
    # Count cache entries
    cache_stats = {
        "memory_entries": len(cache._memory_cache),
        "disk_entries": len(list(cache.cache_dir.glob("*.cache")))
    }
    
    return {
        "cache": cache_stats,
        "config": get_dev_config().to_dict()
    }