#!/usr/bin/env python3
"""Collect and store production metrics"""
import sys
import json
import sqlite3
import psutil
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def collect_system_metrics():
    """Collect current system metrics"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu_usage": cpu_percent,
        "memory_usage": memory.used / (1024 * 1024),  # MB
        "memory_percent": memory.percent
    }

def store_metrics(metrics):
    """Store metrics in database"""
    db_path = Path("metrics_data/flow_metrics.db")
    
    if not db_path.exists():
        print("❌ Metrics database not found. Run setup_monitoring.sh first.")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO flow_metrics (
                timestamp, cpu_usage, memory_usage, execution_time,
                success_rate, error_rate, throughput
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            metrics["timestamp"],
            metrics["cpu_usage"],
            metrics["memory_usage"],
            0.0,  # execution_time - placeholder
            100.0,  # success_rate - placeholder
            0.0,  # error_rate - placeholder
            0.0   # throughput - placeholder
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error storing metrics: {e}")
        return False

def main():
    """Collect and store current metrics"""
    print("📊 Collecting production metrics...")
    
    metrics = collect_system_metrics()
    
    if store_metrics(metrics):
        print(f"✅ Metrics stored: CPU {metrics['cpu_usage']:.1f}%, Memory {metrics['memory_usage']:.0f}MB")
        return 0
    else:
        print("❌ Failed to store metrics")
        return 1

if __name__ == "__main__":
    sys.exit(main())
