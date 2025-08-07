"""
Performance Optimizer - Coordinated optimization system for AI Writing Flow V2

This module provides a comprehensive performance optimization system that coordinates
all optimization modules to achieve maximum performance improvements across the
entire writing flow pipeline.

Key Features:
- Coordinated optimization across all bottlenecks
- Intelligent resource allocation and scheduling
- Performance monitoring and adaptive optimization
- Memory management and cleanup coordination
- Comprehensive performance reporting
"""

import asyncio
import time
import logging
import gc
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
import json
import psutil
from datetime import datetime, timedelta

from .cache_manager import IntelligentCacheManager
from .optimized_knowledge_search import OptimizedKnowledgeSearch, create_optimized_search
from .optimized_research import OptimizedResearch, create_optimized_research
from .optimized_draft_generation import OptimizedDraftGeneration, create_optimized_draft_generator
from .optimized_audience_alignment import OptimizedAudienceAlignment, create_optimized_audience_alignment
from .optimized_quality_assessment import OptimizedQualityAssessment, create_optimized_quality_assessment

logger = logging.getLogger(__name__)


@dataclass
class OptimizationTarget:
    """Performance optimization target with before/after metrics"""
    method_name: str
    baseline_time_ms: float
    target_time_ms: float
    baseline_memory_mb: float
    target_memory_mb: float
    baseline_cpu_percent: float
    target_cpu_percent: float
    priority: int = 1  # 1=high, 2=medium, 3=low
    
    @property
    def time_improvement_target(self) -> float:
        """Calculate target time improvement percentage"""
        if self.baseline_time_ms == 0:
            return 0.0
        return ((self.baseline_time_ms - self.target_time_ms) / self.baseline_time_ms) * 100
    
    @property
    def memory_improvement_target(self) -> float:
        """Calculate target memory improvement percentage"""
        if self.baseline_memory_mb == 0:
            return 0.0
        return ((self.baseline_memory_mb - self.target_memory_mb) / self.baseline_memory_mb) * 100


@dataclass
class OptimizationResult:
    """Result of optimization process with performance gains"""
    method_name: str
    baseline_metrics: Dict[str, float]
    optimized_metrics: Dict[str, float]
    improvement_percentage: Dict[str, float]
    optimization_applied: List[str]
    success: bool = True
    
    def calculate_overall_improvement(self) -> float:
        """Calculate overall improvement score"""
        if not self.improvement_percentage:
            return 0.0
        
        # Weighted average of improvements
        weights = {'time': 0.5, 'memory': 0.3, 'cpu': 0.2}
        total_improvement = 0.0
        total_weight = 0.0
        
        for metric, improvement in self.improvement_percentage.items():
            if metric in weights:
                total_improvement += improvement * weights[metric]
                total_weight += weights[metric]
        
        return total_improvement / total_weight if total_weight > 0 else 0.0


@dataclass
class SystemPerformanceMetrics:
    """System-wide performance metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    active_optimizations: int
    cache_memory_mb: float
    total_time_saved_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "memory_percent": self.memory_percent,
            "active_optimizations": self.active_optimizations,
            "cache_memory_mb": self.cache_memory_mb,
            "total_time_saved_ms": self.total_time_saved_ms
        }


class PerformanceOptimizer:
    """
    Comprehensive performance optimization system
    
    Coordinates all optimization modules to achieve maximum performance
    improvements across the entire AI Writing Flow pipeline.
    
    Features:
    - Coordinated optimization across all bottlenecks
    - Intelligent resource allocation
    - Performance monitoring and adaptive optimization
    - Memory management coordination
    - Comprehensive performance reporting
    """
    
    def __init__(self,
                 total_memory_budget_mb: int = 200,
                 enable_adaptive_optimization: bool = True,
                 performance_monitoring_interval: float = 30.0):
        """
        Initialize PerformanceOptimizer
        
        Args:
            total_memory_budget_mb: Total memory budget for all optimizations
            enable_adaptive_optimization: Enable adaptive optimization based on usage patterns
            performance_monitoring_interval: Interval for performance monitoring in seconds
        """
        self.total_memory_budget_mb = total_memory_budget_mb
        self.enable_adaptive_optimization = enable_adaptive_optimization
        self.performance_monitoring_interval = performance_monitoring_interval
        
        # Optimization targets based on profiling results
        self.optimization_targets = self._initialize_optimization_targets()
        
        # Initialize optimization modules with budget allocation
        memory_allocation = self._calculate_memory_allocation()
        self._initialize_optimization_modules(memory_allocation)
        
        # Performance tracking
        self.performance_history: List[SystemPerformanceMetrics] = []
        self.optimization_results: Dict[str, OptimizationResult] = {}
        
        # Monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Start performance monitoring
        self._start_performance_monitoring()
        
        logger.info(f"🚀 PerformanceOptimizer initialized: "
                   f"memory_budget={total_memory_budget_mb}MB, "
                   f"adaptive={enable_adaptive_optimization}")
    
    def _initialize_optimization_targets(self) -> Dict[str, OptimizationTarget]:
        """Initialize optimization targets based on profiling results"""
        targets = {
            'conduct_research': OptimizationTarget(
                method_name='conduct_research',
                baseline_time_ms=26920.0,  # 26.92s
                target_time_ms=8000.0,     # Target: <8s
                baseline_memory_mb=200.0,
                target_memory_mb=100.0,
                baseline_cpu_percent=60.0,
                target_cpu_percent=35.0,
                priority=1
            ),
            
            'knowledge_base_search': OptimizationTarget(
                method_name='knowledge_base_search',
                baseline_time_ms=26310.0,  # 26.31s total (45 calls)
                target_time_ms=9000.0,     # Target: <9s total
                baseline_memory_mb=150.0,
                target_memory_mb=75.0,
                baseline_cpu_percent=40.0,
                target_cpu_percent=25.0,
                priority=1
            ),
            
            'generate_draft': OptimizationTarget(
                method_name='generate_draft',
                baseline_time_ms=17210.0,  # 17.21s
                target_time_ms=6000.0,     # Target: <6s
                baseline_memory_mb=300.0,  # High memory usage
                target_memory_mb=120.0,
                baseline_cpu_percent=50.0,
                target_cpu_percent=30.0,
                priority=1
            ),
            
            'align_audience': OptimizationTarget(
                method_name='align_audience',
                baseline_time_ms=21540.0,  # 21.54s total (7 calls)
                target_time_ms=5000.0,     # Target: <5s total
                baseline_memory_mb=100.0,
                target_memory_mb=50.0,
                baseline_cpu_percent=45.0,
                target_cpu_percent=25.0,
                priority=2
            ),
            
            'assess_quality': OptimizationTarget(
                method_name='assess_quality',
                baseline_time_ms=14000.0,  # 14.00s total (7 calls)
                target_time_ms=4000.0,     # Target: <4s total
                baseline_memory_mb=80.0,
                target_memory_mb=40.0,
                baseline_cpu_percent=35.0,
                target_cpu_percent=20.0,
                priority=2
            )
        }
        
        logger.debug(f"📊 Initialized {len(targets)} optimization targets")
        return targets
    
    def _calculate_memory_allocation(self) -> Dict[str, int]:
        """Calculate memory allocation for each optimization module"""
        # Allocate memory based on priority and expected impact
        allocations = {
            'knowledge_search': int(self.total_memory_budget_mb * 0.25),  # 25%
            'research': int(self.total_memory_budget_mb * 0.30),          # 30%
            'draft_generation': int(self.total_memory_budget_mb * 0.25),  # 25%
            'audience_alignment': int(self.total_memory_budget_mb * 0.10), # 10%
            'quality_assessment': int(self.total_memory_budget_mb * 0.10)  # 10%
        }
        
        logger.debug(f"💾 Memory allocation: {allocations}")
        return allocations
    
    def _initialize_optimization_modules(self, memory_allocation: Dict[str, int]):
        """Initialize all optimization modules with allocated resources"""
        
        # Knowledge Search Optimization
        self.knowledge_search = create_optimized_search(
            cache_size_mb=memory_allocation['knowledge_search'],
            enable_prefetch=True
        )
        
        # Research Optimization
        self.research = create_optimized_research(
            cache_size_mb=memory_allocation['research'],
            max_parallel_tasks=5,
            enable_synthesis=True
        )
        
        # Draft Generation Optimization
        self.draft_generation = create_optimized_draft_generator(
            cache_size_mb=memory_allocation['draft_generation'],
            max_parallel_sections=3,
            enable_streaming=True
        )
        
        # Audience Alignment Optimization
        self.audience_alignment = create_optimized_audience_alignment(
            cache_size_mb=memory_allocation['audience_alignment'],
            max_parallel_alignments=3
        )
        
        # Quality Assessment Optimization
        self.quality_assessment = create_optimized_quality_assessment(
            cache_size_mb=memory_allocation['quality_assessment'],
            max_parallel_metrics=4,
            quality_threshold=0.7
        )
        
        logger.info("✅ All optimization modules initialized")
    
    def _start_performance_monitoring(self):
        """Start background performance monitoring"""
        try:
            loop = asyncio.get_event_loop()
            self._monitoring_task = loop.create_task(self._performance_monitoring_loop())
        except RuntimeError:
            logger.info("No event loop found, performance monitoring disabled")
    
    async def _performance_monitoring_loop(self):
        """Background performance monitoring loop"""
        while True:
            try:
                await asyncio.sleep(self.performance_monitoring_interval)
                
                # Collect system metrics
                metrics = self._collect_system_metrics()
                self.performance_history.append(metrics)
                
                # Keep only last 100 measurements
                if len(self.performance_history) > 100:
                    self.performance_history = self.performance_history[-100:]
                
                # Adaptive optimization based on metrics
                if self.enable_adaptive_optimization:
                    await self._perform_adaptive_optimization(metrics)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
    
    def _collect_system_metrics(self) -> SystemPerformanceMetrics:
        """Collect current system performance metrics"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        # Calculate cache memory usage
        cache_memory_mb = (
            self.knowledge_search.cache.get_statistics().memory_usage_mb +
            self.research.cache.get_statistics().memory_usage_mb +
            self.draft_generation.cache.get_statistics().memory_usage_mb +
            self.audience_alignment.cache.get_statistics().memory_usage_mb +
            self.quality_assessment.cache.get_statistics().memory_usage_mb
        )
        
        return SystemPerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=psutil.cpu_percent(interval=1.0),
            memory_mb=memory_info.rss / (1024 * 1024),
            memory_percent=process.memory_percent(),
            active_optimizations=len(self.optimization_results),
            cache_memory_mb=cache_memory_mb,
            total_time_saved_ms=self._calculate_total_time_saved()
        )
    
    def _calculate_total_time_saved(self) -> float:
        """Calculate total time saved across all optimizations"""
        total_saved = 0.0
        
        for result in self.optimization_results.values():
            if 'time' in result.improvement_percentage:
                baseline_time = result.baseline_metrics.get('time_ms', 0)
                improvement_pct = result.improvement_percentage['time']
                time_saved = baseline_time * (improvement_pct / 100.0)
                total_saved += time_saved
        
        return total_saved
    
    async def _perform_adaptive_optimization(self, metrics: SystemPerformanceMetrics):
        """Perform adaptive optimization based on current metrics"""
        # Adjust cache sizes based on memory pressure
        if metrics.memory_percent > 80.0:  # High memory usage
            logger.info("🔧 High memory usage detected, adjusting cache sizes")
            await self._reduce_cache_sizes()
        elif metrics.memory_percent < 50.0:  # Low memory usage
            logger.debug("💾 Low memory usage, could increase cache sizes")
            await self._increase_cache_sizes()
        
        # Adjust parallelism based on CPU usage
        if metrics.cpu_percent > 85.0:  # High CPU usage
            logger.info("🔧 High CPU usage detected, reducing parallelism")
            await self._reduce_parallelism()
        elif metrics.cpu_percent < 30.0:  # Low CPU usage
            logger.debug("⚡ Low CPU usage, could increase parallelism")
            await self._increase_parallelism()
    
    async def _reduce_cache_sizes(self):
        """Reduce cache sizes to free memory"""
        # Clear least recently used cache entries
        for module in [self.knowledge_search, self.research, self.draft_generation,
                      self.audience_alignment, self.quality_assessment]:
            if hasattr(module, 'cache'):
                # Force cleanup of old entries
                module.cache._cleanup_expired()
    
    async def _increase_cache_sizes(self):
        """Increase cache sizes for better performance"""
        # This would involve recreating caches with larger sizes
        # For now, just log the opportunity
        logger.debug("💾 Memory available for cache expansion")
    
    async def _reduce_parallelism(self):
        """Reduce parallelism to lower CPU usage"""
        # Adjust parallel execution limits
        if hasattr(self.research, 'max_parallel_tasks'):
            self.research.max_parallel_tasks = max(2, self.research.max_parallel_tasks - 1)
        
        if hasattr(self.draft_generation, 'max_parallel_sections'):
            self.draft_generation.max_parallel_sections = max(1, self.draft_generation.max_parallel_sections - 1)
    
    async def _increase_parallelism(self):
        """Increase parallelism for better performance"""
        # Adjust parallel execution limits upward
        if hasattr(self.research, 'max_parallel_tasks'):
            self.research.max_parallel_tasks = min(8, self.research.max_parallel_tasks + 1)
        
        if hasattr(self.draft_generation, 'max_parallel_sections'):
            self.draft_generation.max_parallel_sections = min(5, self.draft_generation.max_parallel_sections + 1)
    
    async def optimize_workflow(self,
                              workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize complete workflow with coordinated optimizations
        
        Args:
            workflow_data: Workflow data containing all necessary information
            
        Returns:
            Optimized workflow results with performance metrics
        """
        start_time = time.time()
        
        logger.info("🚀 Starting coordinated workflow optimization")
        
        # Extract workflow components
        research_queries = workflow_data.get('research_queries', [])
        content_requirements = workflow_data.get('content_requirements', {})
        audience_targets = workflow_data.get('audience_targets', [])
        quality_criteria = workflow_data.get('quality_criteria', [])
        context = workflow_data.get('context', {})
        
        # Results storage
        optimization_results = {}
        
        try:
            # 1. Optimized Research (addresses conduct_research bottleneck)
            if research_queries:
                research_start = time.time()
                research_result = await self.research.conduct_research(
                    research_queries, context, priority_order=True
                )
                research_time = (time.time() - research_start) * 1000
                
                optimization_results['research'] = {
                    'result': research_result,
                    'time_ms': research_time,
                    'cached_results': research_result.get('cached_results', 0)
                }
                
                # Update context with research results
                context['research_findings'] = research_result
            
            # 2. Optimized Draft Generation (addresses generate_draft bottleneck)
            if content_requirements:
                draft_start = time.time()
                draft_result = await self.draft_generation.generate_draft(
                    content_requirements, context
                )
                draft_time = (time.time() - draft_start) * 1000
                
                optimization_results['draft_generation'] = {
                    'result': draft_result,
                    'time_ms': draft_time,
                    'streaming_used': draft_result.get('streaming_used', False)
                }
                
                # Use generated draft for further optimization
                generated_content = draft_result['content']
            else:
                generated_content = workflow_data.get('content', '')
            
            # 3. Optimized Audience Alignment (addresses align_audience bottleneck)
            if audience_targets and generated_content:
                alignment_start = time.time()
                
                # Create alignment tasks
                alignment_tasks = [(generated_content, target) for target in audience_targets]
                
                alignment_results = await self.audience_alignment.align_audience_batch(
                    alignment_tasks, context
                )
                alignment_time = (time.time() - alignment_start) * 1000
                
                optimization_results['audience_alignment'] = {
                    'results': alignment_results,
                    'time_ms': alignment_time,
                    'cached_alignments': sum(1 for r in alignment_results if r.from_cache)
                }
                
                # Use first alignment result for quality assessment
                if alignment_results:
                    final_content = alignment_results[0].aligned_content
                else:
                    final_content = generated_content
            else:
                final_content = generated_content
            
            # 4. Optimized Quality Assessment (addresses assess_quality bottleneck)
            if quality_criteria and final_content:
                quality_start = time.time()
                
                quality_result = await self.quality_assessment.assess_quality(
                    final_content, quality_criteria, context
                )
                quality_time = (time.time() - quality_start) * 1000
                
                optimization_results['quality_assessment'] = {
                    'result': quality_result,
                    'time_ms': quality_time,
                    'from_cache': quality_result.from_cache
                }
        
        except Exception as e:
            logger.error(f"❌ Workflow optimization error: {e}")
            # Return partial results
            optimization_results['error'] = str(e)
        
        total_time = (time.time() - start_time) * 1000
        
        # Calculate performance improvements
        performance_summary = self._calculate_performance_improvements(
            optimization_results, total_time
        )
        
        workflow_result = {
            'optimization_results': optimization_results,
            'performance_summary': performance_summary,
            'total_time_ms': total_time,
            'system_metrics': self._collect_system_metrics().to_dict(),
            'final_content': final_content if 'final_content' in locals() else '',
            'success': 'error' not in optimization_results
        }
        
        logger.info(f"✅ Workflow optimization completed: {total_time:.1f}ms")
        return workflow_result
    
    def _calculate_performance_improvements(self,
                                          results: Dict[str, Any],
                                          total_time_ms: float) -> Dict[str, Any]:
        """Calculate performance improvements against baseline"""
        improvements = {}
        
        # Calculate improvements for each optimization target
        for method_name, target in self.optimization_targets.items():
            actual_time = 0.0
            
            # Map optimization results to target methods
            if method_name == 'conduct_research' and 'research' in results:
                actual_time = results['research']['time_ms']
            elif method_name == 'generate_draft' and 'draft_generation' in results:
                actual_time = results['draft_generation']['time_ms']
            elif method_name == 'align_audience' and 'audience_alignment' in results:
                actual_time = results['audience_alignment']['time_ms']
            elif method_name == 'assess_quality' and 'quality_assessment' in results:
                actual_time = results['quality_assessment']['time_ms']
            elif method_name == 'knowledge_base_search':
                # Knowledge base search is integrated into research
                if 'research' in results:
                    # Estimate based on research time (knowledge search is part of it)
                    actual_time = results['research']['time_ms'] * 0.6
            
            if actual_time > 0:
                time_improvement = ((target.baseline_time_ms - actual_time) / target.baseline_time_ms) * 100
                improvements[method_name] = {
                    'baseline_time_ms': target.baseline_time_ms,
                    'actual_time_ms': actual_time,
                    'time_improvement_percent': max(0.0, time_improvement),
                    'target_met': actual_time <= target.target_time_ms
                }
        
        # Overall improvements
        total_baseline = sum(target.baseline_time_ms for target in self.optimization_targets.values())
        overall_improvement = ((total_baseline - total_time_ms) / total_baseline) * 100 if total_baseline > 0 else 0
        
        return {
            'individual_improvements': improvements,
            'overall_improvement_percent': max(0.0, overall_improvement),
            'total_baseline_time_ms': total_baseline,
            'total_actual_time_ms': total_time_ms,
            'performance_target_achieved': overall_improvement >= 25.0  # 25% improvement target
        }
    
    def get_comprehensive_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report across all optimizations"""
        
        # Collect metrics from all modules
        module_metrics = {
            'knowledge_search': self.knowledge_search.get_performance_metrics(),
            'research': self.research.get_performance_metrics(),
            'draft_generation': self.draft_generation.get_performance_metrics(),
            'audience_alignment': self.audience_alignment.get_performance_metrics(),
            'quality_assessment': self.quality_assessment.get_performance_metrics()
        }
        
        # System metrics
        current_metrics = self._collect_system_metrics()
        
        # Performance history analysis
        if len(self.performance_history) > 1:
            avg_cpu = sum(m.cpu_percent for m in self.performance_history) / len(self.performance_history)
            avg_memory = sum(m.memory_mb for m in self.performance_history) / len(self.performance_history)
            peak_memory = max(m.memory_mb for m in self.performance_history)
        else:
            avg_cpu = current_metrics.cpu_percent
            avg_memory = current_metrics.memory_mb
            peak_memory = current_metrics.memory_mb
        
        # Calculate overall optimization efficiency
        total_cache_hits = sum(
            metrics.get('cache_statistics', {}).get('hit_rate', 0)
            for metrics in module_metrics.values()
        ) / len(module_metrics)
        
        return {
            'summary': {
                'total_time_saved_ms': self._calculate_total_time_saved(),
                'overall_cache_hit_rate': total_cache_hits,
                'memory_budget_mb': self.total_memory_budget_mb,
                'memory_usage_mb': current_metrics.memory_mb,
                'memory_efficiency': (current_metrics.memory_mb / self.total_memory_budget_mb) * 100,
                'optimization_targets_count': len(self.optimization_targets),
                'active_optimizations': len(self.optimization_results)
            },
            'optimization_targets': {
                name: {
                    'time_improvement_target': target.time_improvement_target,
                    'memory_improvement_target': target.memory_improvement_target,
                    'priority': target.priority
                }
                for name, target in self.optimization_targets.items()
            },
            'module_performance': module_metrics,
            'system_performance': {
                'current': current_metrics.to_dict(),
                'averages': {
                    'cpu_percent': avg_cpu,
                    'memory_mb': avg_memory,
                    'peak_memory_mb': peak_memory
                },
                'history_points': len(self.performance_history)
            },
            'recommendations': self._generate_performance_recommendations()
        }
    
    def _generate_performance_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        current_metrics = self._collect_system_metrics()
        
        # Memory recommendations
        if current_metrics.memory_percent > 80:
            recommendations.append("High memory usage detected. Consider reducing cache sizes or processing batch sizes.")
        elif current_metrics.memory_percent < 40:
            recommendations.append("Low memory usage. Consider increasing cache sizes for better performance.")
        
        # CPU recommendations
        if current_metrics.cpu_percent > 85:
            recommendations.append("High CPU usage detected. Consider reducing parallelism or optimizing algorithms.")
        elif current_metrics.cpu_percent < 30:
            recommendations.append("Low CPU usage. Consider increasing parallelism for faster processing.")
        
        # Cache recommendations
        total_cache_memory = current_metrics.cache_memory_mb
        if total_cache_memory < self.total_memory_budget_mb * 0.5:
            recommendations.append("Cache memory usage is low. Consider enabling more aggressive caching.")
        
        # Module-specific recommendations
        for module_name, metrics in [
            ('knowledge_search', self.knowledge_search.get_performance_metrics()),
            ('research', self.research.get_performance_metrics()),
            ('draft_generation', self.draft_generation.get_performance_metrics()),
            ('audience_alignment', self.audience_alignment.get_performance_metrics()),
            ('quality_assessment', self.quality_assessment.get_performance_metrics())
        ]:
            cache_stats = metrics.get('cache_statistics', {})
            hit_rate = cache_stats.get('hit_rate', 0)
            
            if hit_rate < 0.3:  # Low cache hit rate
                recommendations.append(f"Low cache hit rate ({hit_rate:.1%}) in {module_name}. Consider cache warmup or longer TTL.")
        
        if not recommendations:
            recommendations.append("Performance is optimal. No specific recommendations at this time.")
        
        return recommendations
    
    async def warmup_all_caches(self, warmup_data: Optional[Dict[str, List[str]]] = None):
        """Warm up all optimization module caches"""
        logger.info("🔥 Warming up all optimization caches")
        
        try:
            # Default warmup data if none provided
            if warmup_data is None:
                warmup_data = {
                    'research_queries': [
                        'machine learning fundamentals',
                        'data science techniques',
                        'software architecture patterns',
                        'performance optimization strategies',
                        'user experience design principles'
                    ],
                    'content_types': ['article', 'blog', 'technical', 'documentation'],
                    'audience_types': ['technical_professional', 'business_executive', 'general_consumer'],
                    'quality_criteria': ['readability', 'coherence', 'completeness', 'accuracy']
                }
            
            # Warm up research cache
            if 'research_queries' in warmup_data:
                await asyncio.create_task(
                    self.research.warmup_cache(warmup_data['research_queries'])
                )
            
            # Warm up knowledge search cache
            await asyncio.create_task(
                self.knowledge_search.warmup_cache([
                    'CrewAI agents', 'flow execution', 'task management',
                    'AI writing assistance', 'content generation'
                ])
            )
            
            logger.info("✅ All caches warmed up successfully")
            
        except Exception as e:
            logger.error(f"❌ Cache warmup failed: {e}")
    
    def clear_all_caches(self):
        """Clear all optimization module caches"""
        logger.info("🧹 Clearing all optimization caches")
        
        self.knowledge_search.clear_cache()
        self.research.clear_cache()
        self.draft_generation.clear_cache()
        self.audience_alignment.clear_cache()
        self.quality_assessment.clear_cache()
        
        # Force garbage collection
        gc.collect()
        
        logger.info("✅ All caches cleared")
    
    async def close(self):
        """Close all optimization modules and cleanup resources"""
        logger.info("🛑 Shutting down PerformanceOptimizer")
        
        # Stop monitoring
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Close all optimization modules
        await asyncio.gather(
            self.knowledge_search.close(),
            self.research.close(),
            self.draft_generation.close(),
            self.audience_alignment.close(),
            self.quality_assessment.close(),
            return_exceptions=True
        )
        
        logger.info("✅ PerformanceOptimizer shutdown complete")
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            if hasattr(self, '_monitoring_task') and self._monitoring_task:
                self._monitoring_task.cancel()
        except Exception:
            pass


# Factory function for easy instantiation
def create_performance_optimizer(memory_budget_mb: int = 200,
                               enable_adaptive: bool = True) -> PerformanceOptimizer:
    """
    Create performance optimizer with recommended settings
    
    Args:
        memory_budget_mb: Total memory budget for all optimizations
        enable_adaptive: Enable adaptive optimization
        
    Returns:
        PerformanceOptimizer instance configured for optimal performance
    """
    return PerformanceOptimizer(
        total_memory_budget_mb=memory_budget_mb,
        enable_adaptive_optimization=enable_adaptive,
        performance_monitoring_interval=30.0
    )