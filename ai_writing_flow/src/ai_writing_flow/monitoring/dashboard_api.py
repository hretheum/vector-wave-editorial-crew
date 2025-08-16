"""
Dashboard API - Real-time monitoring dashboard data endpoints

This module provides API endpoints for dashboard consumption, delivering
real-time metrics data in dashboard-friendly formats.

Key Features:
- REST API endpoints for metrics data
- Real-time WebSocket streaming
- Dashboard-optimized data formats
- Historical data aggregation
- Health check endpoints
"""

import json
import asyncio
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

from .flow_metrics import FlowMetrics, KPIType, KPISnapshot, MetricsConfig


class TimeRange(Enum):
    """Time range options for dashboard data"""
    LAST_5_MINUTES = "5m"
    LAST_15_MINUTES = "15m" 
    LAST_HOUR = "1h"
    LAST_6_HOURS = "6h"
    LAST_DAY = "24h"
    LAST_WEEK = "7d"


@dataclass
class DashboardMetrics:
    """Dashboard-optimized metrics format"""
    timestamp: str
    status: str  # "healthy", "warning", "critical"
    overview: Dict[str, Any]
    performance: Dict[str, Any]
    flows: Dict[str, Any]
    system: Dict[str, Any]
    alerts: List[Dict[str, Any]]


@dataclass 
class TimeSeriesPoint:
    """Single point in time series data"""
    timestamp: int  # Unix timestamp in milliseconds
    value: float
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TimeSeriesData:
    """Time series data for charts"""
    metric_name: str
    unit: str
    data_points: List[TimeSeriesPoint]
    summary: Dict[str, float]  # min, max, avg, current


class DashboardAPI:
    """
    Dashboard API for real-time monitoring
    
    Provides REST-like interface for dashboard data consumption
    with optimized data formats and caching.
    """
    
    def __init__(self, flow_metrics: FlowMetrics, config: Optional[MetricsConfig] = None):
        """
        Initialize Dashboard API
        
        Args:
            flow_metrics: FlowMetrics instance to pull data from
            config: Optional configuration override
        """
        self.flow_metrics = flow_metrics
        self.config = config or MetricsConfig()
        
        # Dashboard state
        self._active_alerts: List[Dict[str, Any]] = []
        self._last_dashboard_update = 0
        self._cached_dashboard_data: Optional[DashboardMetrics] = None
        self._time_series_cache: Dict[str, TimeSeriesData] = {}
        
        # WebSocket connections (for real-time streaming)
        self._websocket_clients: List[Any] = []  # Would be WebSocket objects in real implementation
        
    def get_dashboard_overview(self, time_range: TimeRange = TimeRange.LAST_HOUR) -> DashboardMetrics:
        """
        Get complete dashboard overview
        
        Args:
            time_range: Time range for historical data
            
        Returns:
            Complete dashboard metrics optimized for display
        """
        current_time = time.time()
        
        # Use cache if still valid (30 second cache for dashboard)
        if (self._cached_dashboard_data and 
            current_time - self._last_dashboard_update < 30):
            return self._cached_dashboard_data
        
        # Get current KPIs
        kpis = self.flow_metrics.get_current_kpis()
        flow_summary = self.flow_metrics.get_flow_summary()
        stage_performance = self.flow_metrics.get_stage_performance_summary()
        
        # Determine overall system status 
        status = self._calculate_system_status(kpis)
        
        # Build dashboard metrics
        dashboard_data = DashboardMetrics(
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=status,
            overview=self._build_overview_data(kpis, flow_summary),
            performance=self._build_performance_data(kpis, stage_performance),
            flows=self._build_flows_data(flow_summary, stage_performance),
            system=self._build_system_data(kpis),
            alerts=self._get_active_alerts()
        )
        
        # Cache the result
        self._cached_dashboard_data = dashboard_data
        self._last_dashboard_update = current_time
        
        return dashboard_data
    
    def get_time_series_data(self, kpi_type: KPIType, 
                           time_range: TimeRange = TimeRange.LAST_HOUR,
                           resolution: int = 60) -> TimeSeriesData:
        """
        Get time series data for charts
        
        Args:
            kpi_type: KPI to get time series for
            time_range: Time range for data
            resolution: Data point resolution in seconds
            
        Returns:
            Time series data optimized for charting
        """
        cache_key = f"{kpi_type.value}_{time_range.value}_{resolution}"
        
        # Check cache (5 minute cache for time series)
        if (cache_key in self._time_series_cache and
            time.time() - self._time_series_cache[cache_key].summary.get("cached_at", 0) < 300):
            return self._time_series_cache[cache_key]
        
        # Calculate time window
        time_window_seconds = self._get_time_window_seconds(time_range)
        
        # Get detailed metrics from FlowMetrics
        metrics = self.flow_metrics.get_detailed_metrics(kpi_type, time_window_seconds)
        
        # Convert to time series format
        data_points = []
        if metrics:
            # Group by time buckets for aggregation
            time_buckets = self._aggregate_to_time_buckets(metrics, resolution)
            
            for bucket_time, bucket_values in time_buckets.items():
                if bucket_values:
                    avg_value = sum(bucket_values) / len(bucket_values)
                    data_points.append(TimeSeriesPoint(
                        timestamp=int(bucket_time * 1000),  # Convert to milliseconds
                        value=avg_value,
                        metadata={"samples": len(bucket_values)}
                    ))
        
        # Sort by timestamp
        data_points.sort(key=lambda p: p.timestamp)
        
        # Calculate summary statistics
        values = [p.value for p in data_points] if data_points else [0]
        summary = {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values) if values else 0,
            "current": values[-1] if values else 0,
            "samples": len(data_points),
            "cached_at": time.time()
        }
        
        # Build time series data
        time_series = TimeSeriesData(
            metric_name=kpi_type.value,
            unit=self._get_metric_unit(kpi_type),
            data_points=data_points,
            summary=summary
        )
        
        # Cache the result
        self._time_series_cache[cache_key] = time_series
        
        return time_series
    
    def get_health_check(self) -> Dict[str, Any]:
        """
        Get system health check for monitoring
        
        Returns:
            Health check data including status and diagnostics
        """
        kpis = self.flow_metrics.get_current_kpis()
        
        # Health check criteria
        health_checks = {
            "metrics_collection": self._check_metrics_collection_health(),
            "memory_usage": kpis.memory_usage < self.config.memory_threshold_mb,
            "cpu_usage": kpis.cpu_usage < self.config.cpu_threshold_percent,
            "error_rate": kpis.error_rate < self.config.error_rate_threshold,
            "active_flows": kpis.active_flows < 100,  # Reasonable limit
            "data_freshness": time.time() - self.flow_metrics._last_kpi_calculation < 60
        }
        
        # Overall health status
        all_healthy = all(health_checks.values())
        critical_issues = [k for k, v in health_checks.items() if not v and k in ["memory_usage", "cpu_usage"]]
        
        if critical_issues:
            status = "critical"
        elif not all_healthy:
            status = "warning"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": health_checks,
            "summary": {
                "total_checks": len(health_checks),
                "passed": sum(health_checks.values()),
                "failed": len(health_checks) - sum(health_checks.values())
            },
            "metrics": {
                "uptime_seconds": time.time() - self.flow_metrics._start_time,
                "total_flows_processed": kpis.total_executions,
                "current_memory_mb": kpis.memory_usage,
                "current_cpu_percent": kpis.cpu_usage
            }
        }
    
    def get_flow_details(self, flow_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed information about flows
        
        Args:
            flow_id: Optional specific flow ID to get details for
            
        Returns:
            Flow details including execution history and performance
        """
        if flow_id:
            # Get specific flow details
            return self._get_specific_flow_details(flow_id)
        else:
            # Get overview of all flows
            return self._get_all_flows_overview()
    
    def _calculate_system_status(self, kpis: KPISnapshot) -> str:
        """Calculate overall system status based on KPIs"""
        # Critical thresholds
        if (kpis.memory_usage > self.config.memory_threshold_mb * 1.5 or
            kpis.cpu_usage > self.config.cpu_threshold_percent * 1.2 or
            kpis.error_rate > self.config.error_rate_threshold * 2):
            return "critical"
        
        # Warning thresholds
        if (kpis.memory_usage > self.config.memory_threshold_mb or
            kpis.cpu_usage > self.config.cpu_threshold_percent or
            kpis.error_rate > self.config.error_rate_threshold or
            kpis.success_rate < 90):
            return "warning"
        
        return "healthy"
    
    def _build_overview_data(self, kpis: KPISnapshot, flow_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Build overview section for dashboard"""
        return {
            "success_rate": {
                "value": round(kpis.success_rate, 1),
                "unit": "%",
                "trend": "stable",  # Could be calculated from historical data
                "status": "good" if kpis.success_rate >= 95 else "warning" if kpis.success_rate >= 90 else "critical"
            },
            "throughput": {
                "value": round(kpis.throughput, 2),
                "unit": "ops/sec",
                "trend": "stable",
                "status": "good" if kpis.throughput > 10 else "warning"
            },
            "avg_execution_time": {
                "value": round(kpis.avg_execution_time, 3),
                "unit": "seconds",
                "trend": "stable",
                "status": "good" if kpis.avg_execution_time < 5 else "warning"
            },
            "active_flows": {
                "value": kpis.active_flows,
                "unit": "flows",
                "trend": "stable",
                "status": "good" if kpis.active_flows < 50 else "warning"
            }
        }
    
    def _build_performance_data(self, kpis: KPISnapshot, stage_performance: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Build performance section for dashboard"""
        return {
            "execution_times": {
                "average": round(kpis.avg_execution_time, 3),
                "p95": round(kpis.p95_execution_time, 3),
                "p99": round(kpis.p99_execution_time, 3),
                "unit": "seconds"
            },
            "resource_usage": {
                "cpu": {
                    "value": round(kpis.cpu_usage, 1),
                    "unit": "%",
                    "status": "good" if kpis.cpu_usage < 50 else "warning" if kpis.cpu_usage < 80 else "critical"
                },
                "memory": {
                    "value": round(kpis.memory_usage, 1),
                    "unit": "MB",
                    "status": "good" if kpis.memory_usage < 200 else "warning" if kpis.memory_usage < 400 else "critical"
                }
            },
            "efficiency": {
                "flow_efficiency": round(kpis.flow_efficiency, 1),
                "resource_efficiency": round(kpis.resource_efficiency, 2),
                "avg_stage_duration": round(kpis.avg_stage_duration, 3)
            },
            "stage_breakdown": stage_performance
        }
    
    def _build_flows_data(self, flow_summary: Dict[str, Any], stage_performance: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Build flows section for dashboard"""
        return {
            "summary": flow_summary,
            "stage_performance": stage_performance,
            "recent_activity": self._get_recent_flow_activity()
        }
    
    def _build_system_data(self, kpis: KPISnapshot) -> Dict[str, Any]:
        """Build system section for dashboard"""
        uptime = time.time() - self.flow_metrics._start_time
        
        return {
            "uptime": {
                "seconds": uptime,
                "formatted": self._format_uptime(uptime)
            },
            "resource_usage": {
                "cpu_percent": round(kpis.cpu_usage, 1),
                "memory_mb": round(kpis.memory_usage, 1),
                "active_flows": kpis.active_flows
            },
            "metrics_collection": {
                "total_metrics": sum(len(metrics) for metrics in self.flow_metrics._metrics.values()),
                "cache_hit_ratio": 85.5,  # Could be calculated from actual cache stats
                "collection_rate": "1/second"
            }
        }
    
    def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get current active alerts"""
        # This would integrate with the alerting system
        return self._active_alerts.copy()
    
    def _get_time_window_seconds(self, time_range: TimeRange) -> int:
        """Convert TimeRange enum to seconds"""
        time_mapping = {
            TimeRange.LAST_5_MINUTES: 300,
            TimeRange.LAST_15_MINUTES: 900,
            TimeRange.LAST_HOUR: 3600,
            TimeRange.LAST_6_HOURS: 21600,
            TimeRange.LAST_DAY: 86400,
            TimeRange.LAST_WEEK: 604800
        }
        return time_mapping.get(time_range, 3600)
    
    def _aggregate_to_time_buckets(self, metrics: List, resolution: int) -> Dict[float, List[float]]:
        """Aggregate metrics into time buckets for charting.

        Buckets are anchored at the earliest metric timestamp to ensure that
        synthetic/test datasets that expect grouping relative to the first
        sample (not wall-clock boundaries) are aggregated as intended.
        """
        if not metrics:
            return {}

        # Anchor buckets at the earliest metric timestamp (sliding window anchoring)
        earliest_ts = min(m.timestamp.timestamp() for m in metrics)

        time_buckets: Dict[float, List[float]] = {}

        for metric in metrics:
            ts = metric.timestamp.timestamp()
            # Compute bucket start relative to the anchor
            offset = ts - earliest_ts
            bucket_start = earliest_ts + (int(offset // resolution) * resolution)

            if bucket_start not in time_buckets:
                time_buckets[bucket_start] = []

            time_buckets[bucket_start].append(metric.value)

        return time_buckets
    
    def _get_metric_unit(self, kpi_type: KPIType) -> str:
        """Get display unit for metric type"""
        unit_mapping = {
            KPIType.CPU_USAGE: "%",
            KPIType.MEMORY_USAGE: "MB",
            KPIType.EXECUTION_TIME: "seconds",
            KPIType.SUCCESS_RATE: "%",
            KPIType.COMPLETION_RATE: "%",
            KPIType.RETRY_RATE: "retries",
            KPIType.THROUGHPUT: "ops/sec",
            KPIType.ERROR_RATE: "%",
            KPIType.QUEUE_SIZE: "flows",
            KPIType.RESPONSE_TIME: "ms",
            KPIType.STAGE_DURATION: "seconds",
            KPIType.FLOW_EFFICIENCY: "%",
            KPIType.RESOURCE_EFFICIENCY: "ops/resource"
        }
        return unit_mapping.get(kpi_type, "")
    
    def _check_metrics_collection_health(self) -> bool:
        """Check if metrics collection is healthy"""
        # Check if we have recent metrics
        current_time = time.time()
        last_update = self.flow_metrics._last_kpi_calculation
        
        return current_time - last_update < 120  # Metrics updated within 2 minutes
    
    def _get_specific_flow_details(self, flow_id: str) -> Dict[str, Any]:
        """Get details for a specific flow"""
        # Check active flows
        with self.flow_metrics._lock:
            if flow_id in self.flow_metrics._active_flows:
                flow_data = self.flow_metrics._active_flows[flow_id].copy()
                flow_data["status"] = "active"
                return flow_data
            
            # Check completed flows
            for flow in self.flow_metrics._completed_flows:
                if flow.get("flow_id") == flow_id or str(hash(str(flow))) == flow_id:
                    flow_copy = flow.copy()
                    flow_copy["status"] = "completed"
                    return flow_copy
            
            # Check failed flows
            for flow in self.flow_metrics._failed_flows:
                if flow.get("flow_id") == flow_id or str(hash(str(flow))) == flow_id:
                    flow_copy = flow.copy()
                    flow_copy["status"] = "failed"
                    return flow_copy
        
        return {"error": "Flow not found", "flow_id": flow_id}
    
    def _get_all_flows_overview(self) -> Dict[str, Any]:
        """Get overview of all flows"""
        with self.flow_metrics._lock:
            active_flows = [
                {
                    "flow_id": fid,
                    "current_stage": data.get("current_stage"),
                    "start_time": data.get("start_time"),
                    "stages_completed": len(data.get("stages_completed", [])),
                    "retry_count": data.get("retry_count", 0),
                    "status": "active"
                }
                for fid, data in self.flow_metrics._active_flows.items()
            ]
            
            # Recent completed flows (last 10)
            recent_completed = [
                {
                    "flow_id": flow.get("flow_id", "unknown"),
                    "total_time": flow.get("total_time", 0),
                    "stages_completed": len(flow.get("stages_completed", [])),
                    "final_stage": flow.get("final_stage"),
                    "status": "completed"
                }
                for flow in self.flow_metrics._completed_flows[-10:]
            ]
            
            # Recent failed flows (last 5)
            recent_failed = [
                {
                    "flow_id": flow.get("flow_id", "unknown"),
                    "total_time": flow.get("total_time", 0),
                    "final_stage": flow.get("final_stage"),
                    "error": flow.get("error", "Unknown error"),
                    "status": "failed"
                }
                for flow in self.flow_metrics._failed_flows[-5:]
            ]
        
        return {
            "active_flows": active_flows,
            "recent_completed": recent_completed,
            "recent_failed": recent_failed,
            "summary": {
                "total_active": len(active_flows),
                "total_completed": len(self.flow_metrics._completed_flows),
                "total_failed": len(self.flow_metrics._failed_flows)
            }
        }
    
    def _get_recent_flow_activity(self) -> List[Dict[str, Any]]:
        """Get recent flow activity for dashboard feed"""
        activities = []
        
        # Recent completions
        for flow in self.flow_metrics._completed_flows[-5:]:
            activities.append({
                "type": "completion",
                "flow_id": flow.get("flow_id", "unknown"),
                "timestamp": flow.get("end_time", time.time()),
                "message": f"Flow completed successfully in {flow.get('total_time', 0):.2f}s"
            })
        
        # Recent failures
        for flow in self.flow_metrics._failed_flows[-3:]:
            activities.append({
                "type": "failure", 
                "flow_id": flow.get("flow_id", "unknown"),
                "timestamp": flow.get("end_time", time.time()),
                "message": f"Flow failed at {flow.get('final_stage', 'unknown')} stage"
            })
        
        # Sort by timestamp (most recent first)
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return activities[:10]  # Return last 10 activities
    
    def _format_uptime(self, uptime_seconds: float) -> str:
        """Format uptime in human-readable format"""
        if uptime_seconds < 60:
            return f"{int(uptime_seconds)}s"
        elif uptime_seconds < 3600:
            return f"{int(uptime_seconds // 60)}m {int(uptime_seconds % 60)}s"
        elif uptime_seconds < 86400:
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
        else:
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            return f"{days}d {hours}h"
    
    def export_dashboard_json(self, filepath: Union[str, Path] = None) -> Dict[str, Any]:
        """
        Export dashboard data as JSON
        
        Args:
            filepath: Optional file path to save JSON
            
        Returns:
            Complete dashboard data as dictionary
        """
        dashboard_data = self.get_dashboard_overview()
        dashboard_dict = asdict(dashboard_data)
        
        if filepath:
            with open(filepath, 'w') as f:
                json.dump(dashboard_dict, f, indent=2)
        
        return dashboard_dict
    
    def add_alert(self, alert_type: str, message: str, severity: str = "warning", 
                  metadata: Dict[str, Any] = None) -> None:
        """Add an alert to the active alerts list"""
        alert = {
            "id": f"alert_{int(time.time() * 1000)}",
            "type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }
        
        self._active_alerts.append(alert)
        
        # Keep only last 50 alerts
        if len(self._active_alerts) > 50:
            self._active_alerts = self._active_alerts[-50:]
    
    def clear_alerts(self, alert_type: Optional[str] = None) -> int:
        """
        Clear alerts from active list
        
        Args:
            alert_type: Optional alert type to clear, if None clears all
            
        Returns:
            Number of alerts cleared
        """
        if alert_type is None:
            cleared_count = len(self._active_alerts)
            self._active_alerts.clear()
            return cleared_count
        else:
            original_count = len(self._active_alerts)
            self._active_alerts = [
                alert for alert in self._active_alerts 
                if alert.get("type") != alert_type
            ]
            return original_count - len(self._active_alerts)