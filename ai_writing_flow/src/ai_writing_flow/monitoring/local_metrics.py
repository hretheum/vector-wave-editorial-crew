"""
Essential Local Metrics - Task 12.1

Implements basic metrics collection for local development
including flow execution, KB usage, and performance metrics.
"""

import time
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class FlowMetric:
    """Single flow execution metric"""
    flow_id: str
    flow_type: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "running"  # running, completed, failed
    stages_completed: List[str] = field(default_factory=list)
    kb_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """Calculate duration"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        return 1.0 if self.status == "completed" else 0.0
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0


@dataclass
class PerformanceMetric:
    """Performance tracking metric"""
    operation: str
    timestamp: float
    duration: float
    memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    success: bool = True
    
    
class LocalMetricsCollector:
    """
    Collects essential metrics for local development.
    
    Features:
    - Flow execution tracking
    - KB usage statistics  
    - Performance metrics
    - Cache effectiveness
    - Error tracking
    - Simple persistence
    """
    
    def __init__(self, metrics_dir: str = "metrics"):
        """Initialize metrics collector"""
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(exist_ok=True)
        
        # Active flow metrics
        self.active_flows: Dict[str, FlowMetric] = {}
        
        # Completed metrics (keep last 100)
        self.completed_flows: deque[FlowMetric] = deque(maxlen=100)
        
        # Performance metrics by operation
        self.performance_metrics: Dict[str, deque[PerformanceMetric]] = defaultdict(
            lambda: deque(maxlen=50)
        )
        
        # Aggregate counters
        self.counters = {
            "total_flows": 0,
            "successful_flows": 0,
            "failed_flows": 0,
            "total_kb_queries": 0,
            "total_cache_hits": 0,
            "total_cache_misses": 0,
            "total_errors": 0
        }
        
        # Load previous session if exists
        self._load_session()
        
        logger.info(
            "Local metrics collector initialized",
            metrics_dir=str(self.metrics_dir)
        )
    
    def start_flow(self, flow_id: str, flow_type: str, metadata: Optional[Dict[str, Any]] = None) -> FlowMetric:
        """Start tracking a flow"""
        metric = FlowMetric(
            flow_id=flow_id,
            flow_type=flow_type,
            start_time=time.time(),
            metadata=metadata or {}
        )
        
        self.active_flows[flow_id] = metric
        self.counters["total_flows"] += 1
        
        logger.debug(f"Started tracking flow: {flow_id}")
        return metric
    
    def end_flow(self, flow_id: str, status: str = "completed", errors: Optional[List[str]] = None):
        """End tracking a flow"""
        if flow_id not in self.active_flows:
            logger.warning(f"Unknown flow: {flow_id}")
            return
        
        metric = self.active_flows.pop(flow_id)
        metric.end_time = time.time()
        metric.status = status
        
        if errors:
            metric.errors.extend(errors)
            self.counters["total_errors"] += len(errors)
        
        # Update counters
        if status == "completed":
            self.counters["successful_flows"] += 1
        else:
            self.counters["failed_flows"] += 1
        
        # Store in completed
        self.completed_flows.append(metric)
        
        logger.debug(
            f"Ended flow: {flow_id}",
            status=status,
            duration=metric.duration
        )
        
        # Persist metrics
        self._save_session()
    
    def record_stage(self, flow_id: str, stage: str):
        """Record stage completion"""
        if flow_id in self.active_flows:
            self.active_flows[flow_id].stages_completed.append(stage)
            logger.debug(f"Stage completed: {flow_id} - {stage}")
    
    def record_kb_query(self, flow_id: str, cache_hit: bool = False):
        """Record KB query"""
        self.counters["total_kb_queries"] += 1
        
        if flow_id in self.active_flows:
            self.active_flows[flow_id].kb_queries += 1
            
            if cache_hit:
                self.active_flows[flow_id].cache_hits += 1
                self.counters["total_cache_hits"] += 1
            else:
                self.active_flows[flow_id].cache_misses += 1
                self.counters["total_cache_misses"] += 1
    
    def record_performance(self, operation: str, duration: float, 
                         memory_mb: Optional[float] = None,
                         cpu_percent: Optional[float] = None,
                         success: bool = True):
        """Record performance metric"""
        metric = PerformanceMetric(
            operation=operation,
            timestamp=time.time(),
            duration=duration,
            memory_mb=memory_mb,
            cpu_percent=cpu_percent,
            success=success
        )
        
        self.performance_metrics[operation].append(metric)
    
    def get_flow_metrics(self) -> Dict[str, Any]:
        """Get flow execution metrics"""
        all_flows = list(self.completed_flows) + list(self.active_flows.values())
        
        if not all_flows:
            return {
                "total_flows": 0,
                "success_rate": 0.0,
                "avg_duration": 0.0,
                "active_flows": 0
            }
        
        completed = [f for f in all_flows if f.status != "running"]
        successful = [f for f in completed if f.status == "completed"]
        
        return {
            "total_flows": len(all_flows),
            "active_flows": len(self.active_flows),
            "completed_flows": len(completed),
            "success_rate": len(successful) / len(completed) if completed else 0.0,
            "avg_duration": sum(f.duration for f in completed) / len(completed) if completed else 0.0,
            "flows_by_type": self._count_by_type(all_flows),
            "recent_errors": self._get_recent_errors()
        }
    
    def get_kb_metrics(self) -> Dict[str, Any]:
        """Get Knowledge Base usage metrics"""
        cache_total = self.counters["total_cache_hits"] + self.counters["total_cache_misses"]
        
        return {
            "total_queries": self.counters["total_kb_queries"],
            "cache_hits": self.counters["total_cache_hits"],
            "cache_misses": self.counters["total_cache_misses"],
            "cache_hit_rate": self.counters["total_cache_hits"] / cache_total if cache_total > 0 else 0.0,
            "queries_per_flow": self.counters["total_kb_queries"] / max(self.counters["total_flows"], 1)
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics by operation"""
        metrics = {}
        
        for operation, readings in self.performance_metrics.items():
            if readings:
                durations = [m.duration for m in readings]
                metrics[operation] = {
                    "count": len(readings),
                    "avg_duration": sum(durations) / len(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                    "success_rate": sum(1 for m in readings if m.success) / len(readings)
                }
        
        return metrics
    
    def get_summary(self) -> Dict[str, Any]:
        """Get complete metrics summary"""
        return {
            "timestamp": datetime.now().isoformat(),
            "session_duration": self._get_session_duration(),
            "flow_metrics": self.get_flow_metrics(),
            "kb_metrics": self.get_kb_metrics(),
            "performance_metrics": self.get_performance_metrics(),
            "counters": self.counters
        }
    
    def _count_by_type(self, flows: List[FlowMetric]) -> Dict[str, int]:
        """Count flows by type"""
        counts = defaultdict(int)
        for flow in flows:
            counts[flow.flow_type] += 1
        return dict(counts)
    
    def _get_recent_errors(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent errors"""
        errors = []
        
        for flow in reversed(list(self.completed_flows)):
            if flow.errors:
                for error in flow.errors:
                    errors.append({
                        "flow_id": flow.flow_id,
                        "flow_type": flow.flow_type,
                        "error": error,
                        "timestamp": flow.end_time
                    })
                    if len(errors) >= limit:
                        return errors
        
        return errors
    
    def _get_session_duration(self) -> float:
        """Get total session duration"""
        all_flows = list(self.completed_flows) + list(self.active_flows.values())
        if not all_flows:
            return 0.0
        
        start_time = min(f.start_time for f in all_flows)
        return time.time() - start_time
    
    def _save_session(self):
        """Save metrics to file"""
        session_file = self.metrics_dir / f"session_{datetime.now().strftime('%Y%m%d')}.json"
        
        try:
            # Convert to serializable format
            data = {
                "counters": self.counters,
                "completed_flows": [asdict(f) for f in self.completed_flows],
                "summary": self.get_summary()
            }
            
            with open(session_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def _load_session(self):
        """Load previous session metrics"""
        today_file = self.metrics_dir / f"session_{datetime.now().strftime('%Y%m%d')}.json"
        
        if today_file.exists():
            try:
                with open(today_file, 'r') as f:
                    data = json.load(f)
                
                # Restore counters
                self.counters.update(data.get("counters", {}))
                
                logger.info("Loaded previous session metrics")
                
            except Exception as e:
                logger.error(f"Failed to load metrics: {e}")
    
    def print_summary(self):
        """Print human-readable summary"""
        summary = self.get_summary()
        
        print("\n📊 Local Development Metrics Summary")
        print("=" * 50)
        
        # Flow metrics
        flow_m = summary["flow_metrics"]
        print(f"\n🔄 Flow Execution:")
        print(f"  Total: {flow_m['total_flows']} ({flow_m['active_flows']} active)")
        print(f"  Success Rate: {flow_m['success_rate']*100:.1f}%")
        print(f"  Avg Duration: {flow_m['avg_duration']:.2f}s")
        
        # KB metrics
        kb_m = summary["kb_metrics"]
        print(f"\n🗄️  Knowledge Base:")
        print(f"  Total Queries: {kb_m['total_queries']}")
        print(f"  Cache Hit Rate: {kb_m['cache_hit_rate']*100:.1f}%")
        print(f"  Queries/Flow: {kb_m['queries_per_flow']:.1f}")
        
        # Performance metrics
        perf_m = summary["performance_metrics"]
        if perf_m:
            print(f"\n⚡ Performance:")
            for op, stats in perf_m.items():
                print(f"  {op}:")
                print(f"    Avg: {stats['avg_duration']:.3f}s")
                print(f"    Range: {stats['min_duration']:.3f}s - {stats['max_duration']:.3f}s")
        
        # Recent errors
        errors = flow_m.get("recent_errors", [])
        if errors:
            print(f"\n❌ Recent Errors:")
            for err in errors[:3]:
                print(f"  - {err['flow_type']}: {err['error']}")
        
        print("\n" + "=" * 50)


# Global metrics collector
_metrics_collector: Optional[LocalMetricsCollector] = None

def get_metrics_collector() -> LocalMetricsCollector:
    """Get or create metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = LocalMetricsCollector()
    return _metrics_collector


# Convenience decorators
def track_flow(flow_type: str):
    """Decorator to track flow execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            flow_id = f"{flow_type}_{int(time.time()*1000)}"
            
            collector.start_flow(flow_id, flow_type)
            try:
                result = func(*args, **kwargs)
                collector.end_flow(flow_id, "completed")
                return result
            except Exception as e:
                collector.end_flow(flow_id, "failed", [str(e)])
                raise
        
        return wrapper
    return decorator


def track_performance(operation: str):
    """Decorator to track operation performance"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            start = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                collector.record_performance(operation, duration, success=True)
                return result
            except Exception as e:
                duration = time.time() - start
                collector.record_performance(operation, duration, success=False)
                raise
        
        return wrapper
    return decorator