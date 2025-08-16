"""
AI Writing Flow V2 Optimization Module

This module contains optimized implementations of critical path components
identified through flow execution profiling.
"""

from .optimized_knowledge_search import OptimizedKnowledgeSearch
from .optimized_research import OptimizedResearch
from .optimized_draft_generation import OptimizedDraftGeneration
from .optimized_audience_alignment import OptimizedAudienceAlignment
from .optimized_quality_assessment import OptimizedQualityAssessment
from .cache_manager import IntelligentCacheManager
from .performance_optimizer import PerformanceOptimizer, create_performance_optimizer

__all__ = [
    'OptimizedKnowledgeSearch',
    'OptimizedResearch', 
    'OptimizedDraftGeneration',
    'OptimizedAudienceAlignment',
    'OptimizedQualityAssessment',
    'IntelligentCacheManager',
    'PerformanceOptimizer',
    'create_performance_optimizer'
]