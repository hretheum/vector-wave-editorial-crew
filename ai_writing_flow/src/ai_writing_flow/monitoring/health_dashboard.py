"""
Simple Health Dashboard - Task 12.3

Provides a simple web-based health dashboard for local development
showing system status and basic metrics.
"""

from typing import Dict, Any, Optional
import time
import json
import threading
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from ..monitoring.local_metrics import get_metrics_collector
from ..optimization.resource_manager import get_resource_manager
from ..config.dev_config import get_dev_config
from ..optimization.dev_cache import get_dev_cache
import structlog

logger = structlog.get_logger(__name__)


class HealthDashboard:
    """Simple health dashboard for local development"""
    
    def __init__(self):
        self.metrics_collector = get_metrics_collector()
        self.resource_manager = get_resource_manager()
        self.dev_config = get_dev_config()
        self.dev_cache = get_dev_cache()
        self.start_time = time.time()
        
        # Component status
        self.component_status = {
            "flow_engine": "healthy",
            "knowledge_base": "healthy",
            "cache": "healthy",
            "ui_bridge": "healthy"
        }
        
        # Recent events
        self.recent_events = []
        self.max_events = 50
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        uptime = time.time() - self.start_time
        
        # Get metrics summary
        metrics_summary = self.metrics_collector.get_summary()
        
        # Get resource status
        resource_status = self.resource_manager.monitor_resources()
        
        # Get cache stats
        cache_stats = {
            "enabled": self.dev_cache.enabled,
            "memory_entries": len(self.dev_cache._memory_cache),
            "disk_entries": len(list(self.dev_cache.cache_dir.glob("*.cache")))
        }
        
        # Check component health
        components = {}
        for component, status in self.component_status.items():
            components[component] = {
                "status": status,
                "healthy": status == "healthy"
            }
        
        # Overall health
        all_healthy = all(c["healthy"] for c in components.values())
        
        return {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": uptime,
            "overall_status": "healthy" if all_healthy else "degraded",
            "components": components,
            "metrics": {
                "flows": metrics_summary["flow_metrics"],
                "kb": metrics_summary["kb_metrics"],
                "performance": metrics_summary["performance_metrics"]
            },
            "resources": resource_status,
            "cache": cache_stats,
            "config": {
                "dev_mode": self.dev_config.dev_mode,
                "hot_reload": self.dev_config.hot_reload,
                "auto_approve": self.dev_config.auto_approve_human_review
            },
            "recent_events": self.recent_events[-10:]  # Last 10 events
        }
    
    def add_event(self, event_type: str, message: str, level: str = "info"):
        """Add event to recent events"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "message": message,
            "level": level
        }
        
        self.recent_events.append(event)
        
        # Keep only recent events
        if len(self.recent_events) > self.max_events:
            self.recent_events = self.recent_events[-self.max_events:]
    
    def update_component_status(self, component: str, status: str):
        """Update component status"""
        if component in self.component_status:
            self.component_status[component] = status
            self.add_event(
                "component_status",
                f"{component} status changed to {status}",
                "warning" if status != "healthy" else "info"
            )


# Global dashboard instance
_dashboard: Optional[HealthDashboard] = None

def get_dashboard() -> HealthDashboard:
    """Get or create dashboard instance"""
    global _dashboard
    if _dashboard is None:
        _dashboard = HealthDashboard()
    return _dashboard


# Simple HTTP server for dashboard
class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for dashboard"""
    
    def do_GET(self):
        """Handle GET requests"""
        path = urlparse(self.path).path
        
        if path == "/":
            self.serve_dashboard()
        elif path == "/health":
            self.serve_health_json()
        elif path == "/metrics":
            self.serve_metrics()
        else:
            self.send_error(404)
    
    def serve_dashboard(self):
        """Serve main dashboard HTML"""
        dashboard = get_dashboard()
        health = dashboard.get_health_status()
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AI Writing Flow - Health Dashboard</title>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
            margin-left: 10px;
        }}
        .status-healthy {{
            background: #27ae60;
            color: white;
        }}
        .status-degraded {{
            background: #f39c12;
            color: white;
        }}
        .status-error {{
            background: #e74c3c;
            color: white;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .card {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h3 {{
            margin-top: 0;
            color: #34495e;
        }}
        .metric {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #ecf0f1;
        }}
        .metric:last-child {{
            border-bottom: none;
        }}
        .metric-value {{
            font-weight: 600;
            color: #2c3e50;
        }}
        .component {{
            display: flex;
            align-items: center;
            padding: 10px;
            margin: 5px 0;
            background: #f8f9fa;
            border-radius: 5px;
        }}
        .component-status {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 10px;
        }}
        .healthy {{
            background: #27ae60;
        }}
        .unhealthy {{
            background: #e74c3c;
        }}
        .event {{
            padding: 8px;
            margin: 4px 0;
            background: #f8f9fa;
            border-radius: 4px;
            font-size: 14px;
        }}
        .event-time {{
            color: #7f8c8d;
            font-size: 12px;
        }}
        .refresh {{
            float: right;
            padding: 8px 16px;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }}
        .refresh:hover {{
            background: #2980b9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <button class="refresh" onclick="location.reload()">Refresh</button>
        <h1>
            AI Writing Flow Health Dashboard
            <span class="status-badge status-{health['overall_status']}">{health['overall_status'].upper()}</span>
        </h1>
        <p>Uptime: {int(health['uptime_seconds']//3600)}h {int((health['uptime_seconds']%3600)//60)}m {int(health['uptime_seconds']%60)}s</p>
        
        <div class="grid">
            <!-- Components Status -->
            <div class="card">
                <h3>🔧 Components</h3>
                {"".join(f'''
                <div class="component">
                    <div class="component-status {'healthy' if comp['healthy'] else 'unhealthy'}"></div>
                    <span>{name.replace('_', ' ').title()}: {comp['status']}</span>
                </div>
                ''' for name, comp in health['components'].items())}
            </div>
            
            <!-- Flow Metrics -->
            <div class="card">
                <h3>📊 Flow Metrics</h3>
                <div class="metric">
                    <span>Total Flows</span>
                    <span class="metric-value">{health['metrics']['flows']['total_flows']}</span>
                </div>
                <div class="metric">
                    <span>Active Flows</span>
                    <span class="metric-value">{health['metrics']['flows']['active_flows']}</span>
                </div>
                <div class="metric">
                    <span>Success Rate</span>
                    <span class="metric-value">{health['metrics']['flows']['success_rate']*100:.1f}%</span>
                </div>
                <div class="metric">
                    <span>Avg Duration</span>
                    <span class="metric-value">{health['metrics']['flows']['avg_duration']:.2f}s</span>
                </div>
            </div>
            
            <!-- KB Metrics -->
            <div class="card">
                <h3>🗄️ Knowledge Base</h3>
                <div class="metric">
                    <span>Total Queries</span>
                    <span class="metric-value">{health['metrics']['kb']['total_queries']}</span>
                </div>
                <div class="metric">
                    <span>Cache Hit Rate</span>
                    <span class="metric-value">{health['metrics']['kb']['cache_hit_rate']*100:.1f}%</span>
                </div>
                <div class="metric">
                    <span>Queries/Flow</span>
                    <span class="metric-value">{health['metrics']['kb']['queries_per_flow']:.1f}</span>
                </div>
            </div>
            
            <!-- Resources -->
            <div class="card">
                <h3>💻 System Resources</h3>
                <div class="metric">
                    <span>CPU Usage</span>
                    <span class="metric-value">{health['resources']['cpu_percent']:.1f}%</span>
                </div>
                <div class="metric">
                    <span>Memory Usage</span>
                    <span class="metric-value">{health['resources']['memory_percent']:.1f}%</span>
                </div>
                <div class="metric">
                    <span>Memory Available</span>
                    <span class="metric-value">{health['resources']['memory_available_gb']:.1f}GB</span>
                </div>
                <div class="metric">
                    <span>Resource Tier</span>
                    <span class="metric-value">{health['resources']['resource_tier'].upper()}</span>
                </div>
            </div>
            
            <!-- Cache Stats -->
            <div class="card">
                <h3>⚡ Cache</h3>
                <div class="metric">
                    <span>Cache Enabled</span>
                    <span class="metric-value">{'Yes' if health['cache']['enabled'] else 'No'}</span>
                </div>
                <div class="metric">
                    <span>Memory Entries</span>
                    <span class="metric-value">{health['cache']['memory_entries']}</span>
                </div>
                <div class="metric">
                    <span>Disk Entries</span>
                    <span class="metric-value">{health['cache']['disk_entries']}</span>
                </div>
            </div>
            
            <!-- Configuration -->
            <div class="card">
                <h3>⚙️ Configuration</h3>
                <div class="metric">
                    <span>Dev Mode</span>
                    <span class="metric-value">{'ON' if health['config']['dev_mode'] else 'OFF'}</span>
                </div>
                <div class="metric">
                    <span>Hot Reload</span>
                    <span class="metric-value">{'ON' if health['config']['hot_reload'] else 'OFF'}</span>
                </div>
                <div class="metric">
                    <span>Auto Approve</span>
                    <span class="metric-value">{'ON' if health['config']['auto_approve'] else 'OFF'}</span>
                </div>
            </div>
        </div>
        
        <!-- Recent Events -->
        <div class="card" style="margin-top: 20px;">
            <h3>📋 Recent Events</h3>
            {"".join(f'''
            <div class="event">
                <span class="event-time">{event['timestamp'].split('T')[1].split('.')[0]}</span>
                <strong>[{event['type']}]</strong> {event['message']}
            </div>
            ''' for event in reversed(health['recent_events']))}
        </div>
        
        <p style="text-align: center; color: #7f8c8d; margin-top: 40px;">
            Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
            <a href="/health">JSON</a> | 
            <a href="/metrics">Metrics</a>
        </p>
    </div>
    
    <script>
        // Auto-refresh every 5 seconds
        setTimeout(() => location.reload(), 5000);
    </script>
</body>
</html>
"""
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())
    
    def serve_health_json(self):
        """Serve health status as JSON"""
        dashboard = get_dashboard()
        health = dashboard.get_health_status()
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(health, indent=2).encode())
    
    def serve_metrics(self):
        """Serve detailed metrics"""
        dashboard = get_dashboard()
        metrics = dashboard.metrics_collector.get_summary()
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(metrics, indent=2).encode())
    
    def log_message(self, format, *args):
        """Override to suppress request logging"""
        pass


def start_health_dashboard(port: int = 8083, background: bool = True):
    """
    Start the health dashboard server.
    
    Args:
        port: Port to run on (default: 8083)
        background: Run in background thread
    """
    server = HTTPServer(('localhost', port), DashboardHandler)
    
    logger.info(f"Health dashboard started at http://localhost:{port}")
    
    if background:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server
    else:
        server.serve_forever()


def stop_health_dashboard(server: HTTPServer):
    """Stop the health dashboard server"""
    server.shutdown()
    logger.info("Health dashboard stopped")