"""
Flow Metrics Integration - Task 12.1

Integrates metrics collection with CrewAI Flow components.
"""

from typing import Dict, Any, Optional
import time
from functools import wraps

from ..crewai_flow.flows.ai_writing_flow import AIWritingFlow
from ..crewai_flow.flows.ui_integrated_flow import UIIntegratedFlow
from .local_metrics import get_metrics_collector, LocalMetricsCollector
import structlog

logger = structlog.get_logger(__name__)


class MetricsEnabledFlow:
    """Mixin for flows with metrics tracking"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metrics_collector = get_metrics_collector()
        self._flow_metric = None
        
    def start_metrics_tracking(self, flow_type: Optional[str] = None):
        """Start tracking metrics for this flow"""
        flow_type = flow_type or self.__class__.__name__
        flow_id = getattr(self, 'flow_id', f"{flow_type}_{int(time.time()*1000)}")
        
        metadata = {
            "config": getattr(self, 'config', {}),
            "started_at": time.time()
        }
        
        self._flow_metric = self.metrics_collector.start_flow(
            flow_id=flow_id,
            flow_type=flow_type,
            metadata=metadata
        )
        
        logger.info(f"Started metrics tracking for {flow_id}")
    
    def end_metrics_tracking(self, status: str = "completed", errors: Optional[list] = None):
        """End metrics tracking"""
        if self._flow_metric:
            self.metrics_collector.end_flow(
                flow_id=self._flow_metric.flow_id,
                status=status,
                errors=errors
            )
    
    def track_stage(self, stage_name: str):
        """Track stage completion"""
        if self._flow_metric:
            self.metrics_collector.record_stage(
                flow_id=self._flow_metric.flow_id,
                stage=stage_name
            )
    
    def track_kb_query(self, cache_hit: bool = False):
        """Track KB query"""
        if self._flow_metric:
            self.metrics_collector.record_kb_query(
                flow_id=self._flow_metric.flow_id,
                cache_hit=cache_hit
            )
    
    def track_performance(self, operation: str, duration: float):
        """Track operation performance"""
        self.metrics_collector.record_performance(
            operation=operation,
            duration=duration
        )


class MetricsAIWritingFlow(MetricsEnabledFlow, AIWritingFlow):
    """AI Writing Flow with integrated metrics"""
    
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Run flow with metrics tracking"""
        self.start_metrics_tracking("ai_writing_flow")
        
        try:
            # Track input analysis stage
            start = time.time()
            self.track_stage("initialization")
            
            # Run actual flow
            result = super().run(inputs)
            
            # Track completion
            self.track_stage("completed")
            self.end_metrics_tracking("completed")
            
            return result
            
        except Exception as e:
            self.end_metrics_tracking("failed", [str(e)])
            raise
    
    def _query_knowledge_base(self, query: str, **kwargs) -> Dict[str, Any]:
        """Override to track KB queries"""
        start = time.time()
        
        # Check if this is a cache hit (simplified check)
        cache_hit = hasattr(self, '_kb_cache') and query in getattr(self, '_kb_cache', {})
        self.track_kb_query(cache_hit)
        
        result = super()._query_knowledge_base(query, **kwargs)
        
        duration = time.time() - start
        self.track_performance("kb_query", duration)
        
        return result
    
    def _generate_content(self, prompt: str, **kwargs) -> str:
        """Override to track content generation"""
        start = time.time()
        self.track_stage("content_generation")
        
        result = super()._generate_content(prompt, **kwargs)
        
        duration = time.time() - start
        self.track_performance("content_generation", duration)
        
        return result
    
    def _validate_content(self, content: str, **kwargs) -> Dict[str, Any]:
        """Override to track validation"""
        start = time.time()
        self.track_stage("validation")
        
        result = super()._validate_content(content, **kwargs)
        
        duration = time.time() - start
        self.track_performance("validation", duration)
        
        return result


class MetricsUIIntegratedFlow(MetricsEnabledFlow, UIIntegratedFlow):
    """UI Integrated Flow with metrics"""
    
    def start_ui_flow(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Start flow with metrics"""
        self.start_metrics_tracking("ui_integrated_flow")
        self.track_stage("ui_session_start")
        
        return super().start_ui_flow(inputs)
    
    def process_with_ui_updates(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process with metrics tracking"""
        try:
            # Track each major stage
            result = super().process_with_ui_updates(session_data)
            
            self.track_stage("ui_processing_complete")
            self.end_metrics_tracking("completed")
            
            return result
            
        except Exception as e:
            self.end_metrics_tracking("failed", [str(e)])
            raise
    
    async def _send_progress_update(self, stage: str, message: str, 
                                   progress_percent: Optional[float] = None,
                                   metadata: Optional[Dict[str, Any]] = None):
        """Track UI updates"""
        start = time.time()
        
        await super()._send_progress_update(stage, message, progress_percent, metadata)
        
        duration = time.time() - start
        self.track_performance("ui_update", duration)
        
        # Track stage changes
        if stage != getattr(self, '_last_tracked_stage', None):
            self.track_stage(f"ui_stage_{stage}")
            self._last_tracked_stage = stage


# Metrics integration helpers
def with_metrics(flow_class):
    """Decorator to add metrics to any flow class"""
    class MetricsFlow(MetricsEnabledFlow, flow_class):
        def run(self, *args, **kwargs):
            self.start_metrics_tracking(flow_class.__name__)
            try:
                result = super().run(*args, **kwargs)
                self.end_metrics_tracking("completed")
                return result
            except Exception as e:
                self.end_metrics_tracking("failed", [str(e)])
                raise
    
    MetricsFlow.__name__ = f"Metrics{flow_class.__name__}"
    return MetricsFlow


# Flow execution with automatic metrics
def execute_flow_with_metrics(flow_class, inputs: Dict[str, Any], **flow_kwargs) -> Dict[str, Any]:
    """
    Execute a flow with automatic metrics collection.
    
    Args:
        flow_class: Flow class to execute
        inputs: Flow inputs
        **flow_kwargs: Additional flow constructor arguments
        
    Returns:
        Flow execution result
    """
    # Create metrics-enabled version
    if not issubclass(flow_class, MetricsEnabledFlow):
        flow_class = with_metrics(flow_class)
    
    # Execute flow
    flow = flow_class(**flow_kwargs)
    result = flow.run(inputs)
    
    # Print summary
    collector = get_metrics_collector()
    collector.print_summary()
    
    return result


# Standalone metrics dashboard
def show_metrics_dashboard():
    """Display current metrics dashboard"""
    collector = get_metrics_collector()
    summary = collector.get_summary()
    
    print("\n📊 AI Writing Flow - Local Metrics Dashboard")
    print("=" * 60)
    print(f"Updated: {summary['timestamp']}")
    print(f"Session Duration: {summary['session_duration']/60:.1f} minutes")
    
    # Flow metrics
    flow_m = summary["flow_metrics"]
    print(f"\n📝 Flow Execution:")
    print(f"├─ Total Flows: {flow_m['total_flows']}")
    print(f"├─ Active: {flow_m['active_flows']}")
    print(f"├─ Success Rate: {flow_m['success_rate']*100:.1f}%")
    print(f"└─ Avg Duration: {flow_m['avg_duration']:.1f}s")
    
    # Flow breakdown
    if flow_m.get('flows_by_type'):
        print(f"\n   By Type:")
        for flow_type, count in flow_m['flows_by_type'].items():
            print(f"   ├─ {flow_type}: {count}")
    
    # KB metrics
    kb_m = summary["kb_metrics"]
    print(f"\n🔍 Knowledge Base:")
    print(f"├─ Total Queries: {kb_m['total_queries']}")
    print(f"├─ Cache Hit Rate: {kb_m['cache_hit_rate']*100:.1f}%")
    print(f"└─ Avg Queries/Flow: {kb_m['queries_per_flow']:.1f}")
    
    # Performance breakdown
    perf_m = summary["performance_metrics"]
    if perf_m:
        print(f"\n⚡ Performance Breakdown:")
        for op, stats in sorted(perf_m.items()):
            print(f"├─ {op}:")
            print(f"│  ├─ Count: {stats['count']}")
            print(f"│  ├─ Avg: {stats['avg_duration']:.3f}s")
            print(f"│  └─ Success: {stats['success_rate']*100:.1f}%")
    
    # Recent errors
    errors = flow_m.get("recent_errors", [])
    if errors:
        print(f"\n⚠️  Recent Errors:")
        for err in errors[:5]:
            print(f"├─ {err['flow_type']}: {err['error'][:50]}...")
    
    print("\n" + "=" * 60)
    
    return summary