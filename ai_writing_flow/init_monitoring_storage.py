#!/usr/bin/env python3
"""Initialize production monitoring storage"""
import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def create_metrics_database():
    """Create SQLite database for metrics storage"""
    db_path = Path("metrics_data/flow_metrics.db")
    db_path.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create metrics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flow_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            execution_id TEXT,
            cpu_usage REAL,
            memory_usage REAL,
            execution_time REAL,
            success_rate REAL,
            error_rate REAL,
            throughput REAL,
            stage TEXT,
            metadata TEXT
        )
    ''')
    
    # Create alerts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            alert_id TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            kpi_type TEXT,
            threshold_value REAL,
            actual_value REAL,
            resolved BOOLEAN DEFAULT FALSE,
            resolved_at DATETIME
        )
    ''')
    
    # Create quality_gate_results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quality_gate_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            execution_id TEXT,
            rule_name TEXT NOT NULL,
            passed BOOLEAN NOT NULL,
            score REAL,
            message TEXT,
            details TEXT
        )
    ''')
    
    # Create indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON flow_metrics(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_quality_timestamp ON quality_gate_results(timestamp)')
    
    conn.commit()
    conn.close()
    
    print(f"✅ Created metrics database: {db_path}")

def initialize_monitoring_components():
    """Initialize monitoring components"""
    try:
        from ai_writing_flow.monitoring.storage import MetricsStorage, StorageConfig
        from ai_writing_flow.monitoring.flow_metrics import FlowMetrics, MetricsConfig
        from ai_writing_flow.monitoring.alerting import AlertManager
        
        # Initialize storage
        storage_config = StorageConfig(
            storage_path="metrics_data",
            retention_days=30,
            enable_aggregation=True,
            aggregation_intervals=["1m", "5m", "1h", "1d"]
        )
        storage = MetricsStorage(storage_config)
        print("✅ MetricsStorage initialized")
        
        # Initialize metrics
        metrics_config = MetricsConfig()
        metrics = FlowMetrics(config=metrics_config)
        print("✅ FlowMetrics initialized")
        
        # Initialize alerting
        alert_manager = AlertManager()
        print("✅ AlertManager initialized")
        
        return True
    except Exception as e:
        print(f"⚠️ Monitoring components initialization: {e}")
        return False

def main():
    print("🔧 Initializing production monitoring storage...")
    
    create_metrics_database()
    
    if initialize_monitoring_components():
        print("✅ All monitoring components initialized successfully")
    else:
        print("⚠️ Some monitoring components had issues but core functionality is ready")
    
    # Create initial log files
    log_dir = Path("monitoring/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    for log_file in ["flow_metrics.log", "alerts.log", "quality_gates.log"]:
        log_path = log_dir / log_file
        if not log_path.exists():
            log_path.touch()
            print(f"✅ Created log file: {log_path}")
    
    print("🎉 Monitoring storage initialization completed!")

if __name__ == "__main__":
    main()
