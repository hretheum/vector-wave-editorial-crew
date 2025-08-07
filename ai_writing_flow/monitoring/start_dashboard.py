#!/usr/bin/env python3
"""
Simple HTTP server for AI Writing Flow V2 monitoring dashboard
"""
import http.server
import socketserver
import webbrowser
from pathlib import Path

def start_dashboard(port=8080):
    """Start the monitoring dashboard server"""
    dashboard_dir = Path(__file__).parent / "dashboards"
    
    class CustomHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(dashboard_dir), **kwargs)
    
    try:
        with socketserver.TCPServer(("", port), CustomHandler) as httpd:
            print(f"🚀 AI Writing Flow V2 Monitoring Dashboard")
            print(f"📊 Server running at: http://localhost:{port}")
            print(f"📁 Serving from: {dashboard_dir}")
            print(f"🌐 Opening dashboard in browser...")
            
            # Open browser automatically
            webbrowser.open(f"http://localhost:{port}/production_dashboard.html")
            
            print(f"Press Ctrl+C to stop the server")
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n👋 Dashboard server stopped")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")

if __name__ == "__main__":
    start_dashboard()
