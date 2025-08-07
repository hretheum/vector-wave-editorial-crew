#!/usr/bin/env python3
"""Production health check script for AI Writing Flow V2"""
import sys
import json
import psutil
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def check_system_resources():
    """Check system resource usage"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "memory_mb": memory.used / (1024 * 1024),
        "disk_percent": disk.percent,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def check_flow_health():
    """Check AI Writing Flow components health"""
    try:
        from ai_writing_flow.ai_writing_flow_v2 import AIWritingFlowV2
        
        # Test minimal initialization
        flow = AIWritingFlowV2(monitoring_enabled=False)
        
        return {
            "flow_initialization": "OK",
            "components_loaded": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "flow_initialization": "ERROR",
            "error": str(e),
            "components_loaded": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

def check_monitoring_storage():
    """Check monitoring storage health"""
    try:
        db_path = Path("metrics_data/flow_metrics.db")
        if db_path.exists():
            size_mb = db_path.stat().st_size / (1024 * 1024)
            return {
                "storage_available": True,
                "database_size_mb": size_mb,
                "path": str(db_path),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "storage_available": False,
                "error": "Database file not found",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        return {
            "storage_available": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

def main():
    """Run comprehensive health check"""
    print("🏥 AI Writing Flow V2 - Production Health Check")
    print("=" * 50)
    
    # System resources
    print("📊 Checking system resources...")
    system_health = check_system_resources()
    print(f"   CPU: {system_health['cpu_percent']:.1f}%")
    print(f"   Memory: {system_health['memory_mb']:.0f}MB ({system_health['memory_percent']:.1f}%)")
    print(f"   Disk: {system_health['disk_percent']:.1f}%")
    
    # Flow health
    print("\n🚀 Checking flow components...")
    flow_health = check_flow_health()
    if flow_health['components_loaded']:
        print("   ✅ Flow components: OK")
    else:
        print(f"   ❌ Flow components: {flow_health['error']}")
    
    # Storage health
    print("\n💾 Checking monitoring storage...")
    storage_health = check_monitoring_storage()
    if storage_health['storage_available']:
        print(f"   ✅ Storage: OK ({storage_health['database_size_mb']:.1f}MB)")
    else:
        print(f"   ❌ Storage: {storage_health['error']}")
    
    # Overall assessment
    print("\n" + "=" * 50)
    overall_healthy = (
        system_health['cpu_percent'] < 90 and
        system_health['memory_percent'] < 90 and
        flow_health['components_loaded'] and
        storage_health['storage_available']
    )
    
    if overall_healthy:
        print("✅ Overall system health: HEALTHY")
        return 0
    else:
        print("⚠️ Overall system health: DEGRADED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
