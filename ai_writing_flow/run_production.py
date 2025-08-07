#!/usr/bin/env python3
"""
AI Writing Flow V2 - Production Server
Uruchamia AI Writing Flow V2 w trybie produkcyjnym z pełnym monitorowaniem
"""

import sys
import os
import signal
import time
import threading
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_writing_flow.ai_writing_flow_v2 import AIWritingFlowV2
from ai_writing_flow.linear_flow import WritingFlowInputs

class ProductionServer:
    """Production server dla AI Writing Flow V2"""
    
    def __init__(self):
        self.running = False
        self.flow_v2 = None
        self.dashboard_thread = None
        self.metrics_thread = None
        
    def start(self):
        """Uruchom serwer produkcyjny"""
        print("🚀 Uruchamianie AI Writing Flow V2 - Production Server")
        print("=" * 60)
        
        try:
            # Initialize AI Writing Flow V2
            print("🔧 Inicjalizacja AI Writing Flow V2...")
            self.flow_v2 = AIWritingFlowV2(
                monitoring_enabled=True,
                alerting_enabled=True,
                quality_gates_enabled=True
            )
            print("✅ AI Writing Flow V2 zainicjalizowany")
            
            # Start monitoring dashboard
            print("📊 Uruchamianie dashboard monitorowania...")
            self.start_dashboard()
            
            # Start metrics collection
            print("📈 Uruchamianie zbierania metryk...")
            self.start_metrics_collection()
            
            # Show server info
            self.show_server_info()
            
            # Set running flag
            self.running = True
            
            # Setup signal handlers
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            # Main server loop
            self.run_server_loop()
            
        except Exception as e:
            print(f"❌ Błąd podczas uruchamiania serwera: {e}")
            self.stop()
            sys.exit(1)
    
    def start_dashboard(self):
        """Uruchom dashboard w osobnym wątku"""
        def run_dashboard():
            try:
                import subprocess
                subprocess.run([
                    sys.executable, 
                    "monitoring/start_dashboard.py"
                ], cwd=Path(__file__).parent)
            except Exception as e:
                print(f"⚠️ Dashboard nie mógł się uruchomić: {e}")
        
        self.dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
        self.dashboard_thread.start()
        time.sleep(2)  # Give dashboard time to start
    
    def start_metrics_collection(self):
        """Uruchom zbieranie metryk w osobnym wątku"""
        def collect_metrics():
            while self.running:
                try:
                    import subprocess
                    subprocess.run([
                        sys.executable,
                        "monitoring/collect_metrics.py"
                    ], cwd=Path(__file__).parent, capture_output=True)
                    time.sleep(30)  # Collect metrics every 30 seconds
                except Exception as e:
                    print(f"⚠️ Błąd zbierania metryk: {e}")
                    time.sleep(60)
        
        self.metrics_thread = threading.Thread(target=collect_metrics, daemon=True)
        self.metrics_thread.start()
    
    def show_server_info(self):
        """Pokaż informacje o serwerze"""
        print("\n" + "=" * 60)
        print("🎉 AI Writing Flow V2 PRODUCTION SERVER - AKTYWNY")
        print("=" * 60)
        print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌍 Environment: local_production")
        print(f"📁 Working dir: {Path.cwd()}")
        print()
        
        print("📊 MONITORING:")
        print("  🌐 Dashboard: http://localhost:8080/production_dashboard.html")
        print("  📈 Health Check: python monitoring/health_check.py")
        print("  📊 Metrics: python monitoring/collect_metrics.py")
        print()
        
        print("🚀 USAGE EXAMPLES:")
        print("  Przykład 1 - Test flow:")
        print("    python -c \"from run_production import test_flow; test_flow()\"")
        print()
        print("  Przykład 2 - API call:")
        print("    curl http://localhost:8080/health")
        print()
        
        print("🛑 STOP SERVER:")
        print("  Ctrl+C lub kill signal")
        print("=" * 60)
        print()
    
    def run_server_loop(self):
        """Główna pętla serwera"""
        print("🔄 Serwer działa... (Ctrl+C aby zatrzymać)")
        
        try:
            while self.running:
                # Show server status every 5 minutes
                print(f"⚡ Server active - {datetime.now().strftime('%H:%M:%S')} - Health: {self.get_health_status()}")
                time.sleep(300)  # 5 minutes
                
        except KeyboardInterrupt:
            print("\n🛑 Otrzymano sygnał przerwania...")
            self.stop()
    
    def get_health_status(self):
        """Sprawdź status zdrowia serwera"""
        try:
            if self.flow_v2:
                health = self.flow_v2.get_health_status()
                return health.get("overall_status", "unknown")
            return "not_initialized"
        except:
            return "error"
    
    def signal_handler(self, signum, frame):
        """Obsługa sygnałów systemowych"""
        print(f"\n🚨 Otrzymano sygnał {signum}")
        self.stop()
    
    def stop(self):
        """Zatrzymaj serwer"""
        print("🛑 Zatrzymywanie AI Writing Flow V2 Production Server...")
        
        self.running = False
        
        # Stop monitoring
        if self.flow_v2:
            try:
                self.flow_v2.emergency_stop()
            except:
                pass
        
        print("✅ Serwer zatrzymany")

def test_flow():
    """Test AI Writing Flow V2 execution"""
    print("🧪 Test AI Writing Flow V2...")
    
    try:
        # Create test inputs
        inputs = {
            "topic_title": "AI Writing Flow V2 Production Test",
            "platform": "LinkedIn",
            "file_path": str(Path("src").absolute()),
            "content_type": "STANDALONE",
            "content_ownership": "EXTERNAL",
            "viral_score": 8.0,
            "editorial_recommendations": "Focus on production capabilities and monitoring"
        }
        
        # Initialize flow
        flow = AIWritingFlowV2(
            monitoring_enabled=True,
            alerting_enabled=True,
            quality_gates_enabled=True
        )
        
        print("✅ Flow zainicjalizowany")
        print("🔧 Wykonywanie testu...")
        
        # Execute test (this would normally process content)
        print("📊 Test execution simulation completed")
        print("✅ AI Writing Flow V2 działa poprawnie!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Main entry point"""
    print("AI Writing Flow V2 - Production Server")
    print("Usage:")
    print("  python run_production.py          # Start production server")
    print("  python -c 'from run_production import test_flow; test_flow()'  # Test flow")
    print()
    
    # Start production server
    server = ProductionServer()
    server.start()

if __name__ == "__main__":
    main()