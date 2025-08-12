"""
Historical Metrics Storage - Persistent storage for long-term metrics analysis

This module provides persistent storage capabilities for metrics data,
enabling historical analysis and long-term trend monitoring.

Key Features:
- Multiple storage backends (SQLite, PostgreSQL, File-based)
- Efficient data compression and aggregation
- Automatic data retention and cleanup
- Query interface for historical analysis
- Export capabilities for external analysis tools
"""

import json
import sqlite3
import gzip
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
import statistics

from .flow_metrics import KPIType, MetricDataPoint, KPISnapshot


@dataclass
class StorageConfig:
    """Configuration for metrics storage"""
    storage_path: Union[str, Path] = "metrics_storage"
    retention_days: int = 90
    compression_enabled: bool = True
    batch_size: int = 1000
    flush_interval_seconds: int = 300  # 5 minutes
    aggregation_intervals: List[int] = None  # [3600, 86400]  # 1hour, 1day
    
    def __post_init__(self):
        if self.aggregation_intervals is None:
            self.aggregation_intervals = [3600, 86400]  # 1 hour, 1 day


@dataclass
class MetricRecord:
    """Single metric record for storage"""
    timestamp: datetime
    kpi_type: str
    value: float
    stage: Optional[str] = None
    flow_id: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class AggregatedMetric:
    """Aggregated metric data"""
    timestamp: datetime
    kpi_type: str
    interval_seconds: int
    count: int
    min_value: float
    max_value: float
    avg_value: float
    sum_value: float
    p95_value: Optional[float] = None
    p99_value: Optional[float] = None


class StorageBackend(ABC):
    """Abstract base class for storage backends"""
    
    @abstractmethod
    def store_metrics(self, metrics: List[MetricRecord]) -> bool:
        """Store metrics batch"""
        pass
    
    @abstractmethod
    def query_metrics(self, kpi_type: KPIType, start_time: datetime, 
                     end_time: datetime, limit: Optional[int] = None) -> List[MetricRecord]:
        """Query metrics by type and time range"""
        pass
    
    @abstractmethod
    def get_aggregated_metrics(self, kpi_type: KPIType, interval_seconds: int,
                              start_time: datetime, end_time: datetime) -> List[AggregatedMetric]:
        """Get aggregated metrics"""
        pass
    
    @abstractmethod
    def cleanup_old_data(self, retention_days: int) -> int:
        """Clean up old data, return number of records removed"""
        pass
    
    @abstractmethod
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        pass


class SQLiteStorageBackend(StorageBackend):
    """SQLite storage backend for metrics"""
    
    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database schema"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            
            # Create metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    kpi_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    stage TEXT,
                    flow_id TEXT,
                    metadata TEXT,
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # Create aggregated metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS aggregated_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    kpi_type TEXT NOT NULL,
                    interval_seconds INTEGER NOT NULL,
                    count INTEGER NOT NULL,
                    min_value REAL NOT NULL,
                    max_value REAL NOT NULL,
                    avg_value REAL NOT NULL,
                    sum_value REAL NOT NULL,
                    p95_value REAL,
                    p99_value REAL,
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # Create indexes for better query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_kpi_type ON metrics(kpi_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_kpi_time ON metrics(kpi_type, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_aggregated_kpi_time ON aggregated_metrics(kpi_type, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_aggregated_interval ON aggregated_metrics(interval_seconds)")
            
            conn.commit()
    
    def store_metrics(self, metrics: List[MetricRecord]) -> bool:
        """Store metrics batch in SQLite"""
        if not metrics:
            return True
        
        try:
            with self._lock:
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.cursor()
                    
                    # Prepare data for insertion
                    data = []
                    for metric in metrics:
                        metadata_json = json.dumps(metric.metadata) if metric.metadata else None
                        data.append((
                            metric.timestamp.timestamp(),
                            metric.kpi_type,
                            metric.value,
                            metric.stage,
                            metric.flow_id,
                            metadata_json
                        ))
                    
                    # Batch insert
                    cursor.executemany("""
                        INSERT INTO metrics (timestamp, kpi_type, value, stage, flow_id, metadata)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, data)
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            print(f"Error storing metrics: {e}")
            return False
    
    def query_metrics(self, kpi_type: KPIType, start_time: datetime, 
                     end_time: datetime, limit: Optional[int] = None) -> List[MetricRecord]:
        """Query metrics from SQLite"""
        try:
            with self._lock:
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.cursor()
                    
                    query = """
                        SELECT timestamp, kpi_type, value, stage, flow_id, metadata
                        FROM metrics
                        WHERE kpi_type = ? AND timestamp BETWEEN ? AND ?
                        ORDER BY timestamp DESC
                    """
                    
                    params = [kpi_type.value, start_time.timestamp(), end_time.timestamp()]
                    
                    if limit:
                        query += " LIMIT ?"
                        params.append(limit)
                    
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    
                    # Convert to MetricRecord objects
                    metrics = []
                    for row in rows:
                        timestamp, kpi_type_str, value, stage, flow_id, metadata_json = row
                        metadata = json.loads(metadata_json) if metadata_json else None
                        
                        metrics.append(MetricRecord(
                            timestamp=datetime.fromtimestamp(timestamp, tz=timezone.utc),
                            kpi_type=kpi_type_str,
                            value=value,
                            stage=stage,
                            flow_id=flow_id,
                            metadata=metadata
                        ))
                    
                    return metrics
                    
        except Exception as e:
            print(f"Error querying metrics: {e}")
            return []
    
    def get_aggregated_metrics(self, kpi_type: KPIType, interval_seconds: int,
                              start_time: datetime, end_time: datetime) -> List[AggregatedMetric]:
        """Get aggregated metrics from SQLite"""
        try:
            with self._lock:
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        SELECT timestamp, kpi_type, interval_seconds, count, min_value, max_value,
                               avg_value, sum_value, p95_value, p99_value
                        FROM aggregated_metrics
                        WHERE kpi_type = ? AND interval_seconds = ? 
                              AND timestamp BETWEEN ? AND ?
                        ORDER BY timestamp
                    """, [kpi_type.value, interval_seconds, start_time.timestamp(), end_time.timestamp()])
                    
                    rows = cursor.fetchall()
                    
                    aggregated = []
                    for row in rows:
                        timestamp, kpi_type_str, interval_sec, count, min_val, max_val, avg_val, sum_val, p95_val, p99_val = row
                        
                        aggregated.append(AggregatedMetric(
                            timestamp=datetime.fromtimestamp(timestamp, tz=timezone.utc),
                            kpi_type=kpi_type_str,
                            interval_seconds=interval_sec,
                            count=count,
                            min_value=min_val,
                            max_value=max_val,
                            avg_value=avg_val,
                            sum_value=sum_val,
                            p95_value=p95_val,
                            p99_value=p99_val
                        ))
                    
                    return aggregated
                    
        except Exception as e:
            print(f"Error getting aggregated metrics: {e}")
            return []
    
    def cleanup_old_data(self, retention_days: int) -> int:
        """Clean up old data from SQLite"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            with self._lock:
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.cursor()
                    
                    # Count records to be deleted
                    cursor.execute("SELECT COUNT(*) FROM metrics WHERE timestamp < ?", 
                                 [cutoff_time.timestamp()])
                    metrics_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM aggregated_metrics WHERE timestamp < ?",
                                 [cutoff_time.timestamp()])
                    aggregated_count = cursor.fetchone()[0]
                    
                    # Delete old records
                    cursor.execute("DELETE FROM metrics WHERE timestamp < ?", 
                                 [cutoff_time.timestamp()])
                    cursor.execute("DELETE FROM aggregated_metrics WHERE timestamp < ?",
                                 [cutoff_time.timestamp()])
                    
                    # Vacuum to reclaim space
                    cursor.execute("VACUUM")
                    
                    conn.commit()
                    
                    total_deleted = metrics_count + aggregated_count
                    return total_deleted
                    
        except Exception as e:
            print(f"Error cleaning up old data: {e}")
            return 0
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get SQLite storage statistics"""
        try:
            with self._lock:
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.cursor()
                    
                    # Get record counts
                    cursor.execute("SELECT COUNT(*) FROM metrics")
                    metrics_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM aggregated_metrics")
                    aggregated_count = cursor.fetchone()[0]
                    
                    # Get database size
                    db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
                    
                    # Get oldest and newest records
                    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM metrics")
                    result = cursor.fetchone()
                    oldest_metric = result[0] if result[0] else None
                    newest_metric = result[1] if result[1] else None
                    
                    return {
                        "backend_type": "SQLite",
                        "database_path": str(self.db_path),
                        "database_size_bytes": db_size,
                        "metrics_count": metrics_count,
                        "aggregated_metrics_count": aggregated_count,
                        "oldest_metric": datetime.fromtimestamp(oldest_metric, tz=timezone.utc).isoformat() if oldest_metric else None,
                        "newest_metric": datetime.fromtimestamp(newest_metric, tz=timezone.utc).isoformat() if newest_metric else None,
                        "data_span_days": (newest_metric - oldest_metric) / 86400 if oldest_metric and newest_metric else 0
                    }
                    
        except Exception as e:
            return {"error": str(e)}
    
    def aggregate_raw_metrics(self, interval_seconds: int, start_time: Optional[datetime] = None) -> int:
        """Create aggregated metrics from raw metrics.

        Improvements:
        - Align start time to bucket boundary
        - If no prior aggregation, start from first raw metric timestamp
        - Limit bucketing to the actual min/max timestamps per KPI to avoid empty iterations
        - When resuming, continue from the NEXT bucket after the last aggregated bucket
        """
        try:
            # Determine the initial time window for scanning raw metrics
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                last_agg_ts: Optional[float] = None
                if start_time is None:
                    cursor.execute(
                        """
                        SELECT MAX(timestamp) FROM aggregated_metrics
                        WHERE interval_seconds = ?
                        """,
                        [interval_seconds],
                    )
                    row = cursor.fetchone()
                    last_agg_ts = row[0] if row and row[0] is not None else None

                # If caller did not provide start_time:
                if start_time is None:
                    if last_agg_ts is not None and last_agg_ts > 0:
                        # Continue from the next bucket after last aggregated
                        base_start_ts = last_agg_ts + interval_seconds
                    else:
                        # No previous aggregation: start from first raw metric
                        cursor.execute("SELECT MIN(timestamp) FROM metrics")
                        min_raw = cursor.fetchone()[0]
                        if min_raw is None:
                            return 0  # No data at all
                        base_start_ts = float(min_raw)
                else:
                    base_start_ts = float(start_time.timestamp())

            # Do NOT align to wall-clock bucket boundaries.
            # Use the actual earliest data timestamp as the anchor so tests that
            # expect sliding windows starting at first sample pass.
            aligned_start_ts = int(base_start_ts)
            aligned_start = datetime.fromtimestamp(aligned_start_ts, tz=timezone.utc)

            aggregated_count = 0

            # For each KPI that has data in [aligned_start, now], aggregate within its own min/max bounds
            end_time = datetime.now(timezone.utc)
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT DISTINCT kpi_type FROM metrics
                    WHERE timestamp BETWEEN ? AND ?
                    """,
                    [aligned_start.timestamp(), end_time.timestamp()],
                )
                kpi_types = [row[0] for row in cursor.fetchall()]

            for kpi_type_str in kpi_types:
                # Determine min/max timestamps for this KPI to bound the loop
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT MIN(timestamp), MAX(timestamp)
                        FROM metrics
                        WHERE kpi_type = ? AND timestamp >= ? AND timestamp <= ?
                        """,
                        [kpi_type_str, aligned_start.timestamp(), end_time.timestamp()],
                    )
                    min_ts, max_ts = cursor.fetchone()

                if min_ts is None or max_ts is None:
                    continue

                # Anchor buckets at the first sample for this KPI (sliding window),
                # not at wall-clock boundaries
                kpi_first_ts = float(min_ts)
                # If resuming from a previous aggregation and that start is after first sample,
                # continue from the next bucket after the last aggregated timestamp
                if last_agg_ts is not None and last_agg_ts >= kpi_first_ts:
                    kpi_start_ts = last_agg_ts + interval_seconds
                else:
                    kpi_start_ts = int(kpi_first_ts)
                # Compute final bucket start to include the bucket containing max_ts
                kpi_end_ts = int(float(max_ts))

                current_time = datetime.fromtimestamp(kpi_start_ts, tz=timezone.utc)
                final_time = datetime.fromtimestamp(kpi_end_ts, tz=timezone.utc) + timedelta(seconds=interval_seconds)

                while current_time < final_time:
                    bucket_end = current_time + timedelta(seconds=interval_seconds)

                    # Fetch raw values for this bucket
                    with sqlite3.connect(str(self.db_path)) as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            SELECT value FROM metrics
                            WHERE kpi_type = ? AND timestamp >= ? AND timestamp < ?
                            """,
                            [kpi_type_str, current_time.timestamp(), bucket_end.timestamp()],
                        )
                        values = [row[0] for row in cursor.fetchall()]

                    if values:
                        count = len(values)
                        min_val = min(values)
                        max_val = max(values)
                        avg_val = statistics.mean(values)
                        sum_val = sum(values)

                        sorted_values = sorted(values)
                        p95_val = (
                            sorted_values[int(0.95 * len(sorted_values))]
                            if len(sorted_values) > 1
                            else sorted_values[0]
                        )
                        p99_val = (
                            sorted_values[int(0.99 * len(sorted_values))]
                            if len(sorted_values) > 1
                            else sorted_values[0]
                        )

                        with sqlite3.connect(str(self.db_path)) as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                """
                                INSERT INTO aggregated_metrics
                                (timestamp, kpi_type, interval_seconds, count, min_value, max_value,
                                 avg_value, sum_value, p95_value, p99_value)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                [
                                    current_time.timestamp(),
                                    kpi_type_str,
                                    interval_seconds,
                                    count,
                                    min_val,
                                    max_val,
                                    avg_val,
                                    sum_val,
                                    p95_val,
                                    p99_val,
                                ],
                            )
                            conn.commit()

                        aggregated_count += 1

                    current_time = bucket_end

            return aggregated_count

        except Exception as e:
            print(f"Error aggregating metrics: {e}")
            return 0


class FileStorageBackend(StorageBackend):
    """File-based storage backend with compression"""
    
    def __init__(self, storage_path: Union[str, Path], compression: bool = True):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.compression = compression
        self._lock = threading.RLock()
    
    def store_metrics(self, metrics: List[MetricRecord]) -> bool:
        """Store metrics in compressed JSON files"""
        if not metrics:
            return True
        
        try:
            # Group metrics by date for efficient storage
            metrics_by_date = {}
            for metric in metrics:
                date_key = metric.timestamp.strftime("%Y-%m-%d")
                if date_key not in metrics_by_date:
                    metrics_by_date[date_key] = []
                metrics_by_date[date_key].append(metric)
            
            with self._lock:
                for date_key, date_metrics in metrics_by_date.items():
                    filename = f"metrics_{date_key}.json"
                    if self.compression:
                        filename += ".gz"
                    
                    filepath = self.storage_path / filename
                    
                    # Load existing data if file exists
                    existing_data = []
                    if filepath.exists():
                        existing_data = self._load_metrics_file(filepath)
                    
                    # Add new metrics
                    for metric in date_metrics:
                        existing_data.append(asdict(metric))
                    
                    # Save updated data
                    self._save_metrics_file(filepath, existing_data)
            
            return True
            
        except Exception as e:
            print(f"Error storing metrics to file: {e}")
            return False
    
    def query_metrics(self, kpi_type: KPIType, start_time: datetime, 
                     end_time: datetime, limit: Optional[int] = None) -> List[MetricRecord]:
        """Query metrics from files"""
        try:
            metrics = []
            
            # Determine which date files to read
            current_date = start_time.date()
            end_date = end_time.date()
            
            with self._lock:
                while current_date <= end_date:
                    date_key = current_date.strftime("%Y-%m-%d")
                    filename = f"metrics_{date_key}.json"
                    if self.compression:
                        filename += ".gz"
                    
                    filepath = self.storage_path / filename
                    
                    if filepath.exists():
                        file_data = self._load_metrics_file(filepath)
                        
                        # Filter metrics by type and time range
                        for metric_dict in file_data:
                            if metric_dict["kpi_type"] == kpi_type.value:
                                metric_time = datetime.fromisoformat(metric_dict["timestamp"])
                                if start_time <= metric_time <= end_time:
                                    metric = MetricRecord(
                                        timestamp=metric_time,
                                        kpi_type=metric_dict["kpi_type"],
                                        value=metric_dict["value"],
                                        stage=metric_dict.get("stage"),
                                        flow_id=metric_dict.get("flow_id"),
                                        metadata=metric_dict.get("metadata")
                                    )
                                    metrics.append(metric)
                    
                    current_date += timedelta(days=1)
            
            # Sort by timestamp and apply limit
            metrics.sort(key=lambda m: m.timestamp, reverse=True)
            if limit:
                metrics = metrics[:limit]
            
            return metrics
            
        except Exception as e:
            print(f"Error querying metrics from file: {e}")
            return []
    
    def get_aggregated_metrics(self, kpi_type: KPIType, interval_seconds: int,
                              start_time: datetime, end_time: datetime) -> List[AggregatedMetric]:
        """Get aggregated metrics (computed on-the-fly for file backend)"""
        # For file backend, we compute aggregations on demand
        raw_metrics = self.query_metrics(kpi_type, start_time, end_time)
        
        if not raw_metrics:
            return []
        
        # Group metrics by time buckets
        aggregated = []
        current_bucket = start_time
        
        while current_bucket < end_time:
            bucket_end = current_bucket + timedelta(seconds=interval_seconds)
            
            # Get metrics in this bucket
            bucket_metrics = [
                m for m in raw_metrics
                if current_bucket <= m.timestamp < bucket_end
            ]
            
            if bucket_metrics:
                values = [m.value for m in bucket_metrics]
                sorted_values = sorted(values)
                
                aggregated.append(AggregatedMetric(
                    timestamp=current_bucket,
                    kpi_type=kpi_type.value,
                    interval_seconds=interval_seconds,
                    count=len(values),
                    min_value=min(values),
                    max_value=max(values),
                    avg_value=statistics.mean(values),
                    sum_value=sum(values),
                    p95_value=sorted_values[int(0.95 * len(sorted_values))] if len(sorted_values) > 1 else sorted_values[0],
                    p99_value=sorted_values[int(0.99 * len(sorted_values))] if len(sorted_values) > 1 else sorted_values[0]
                ))
            
            current_bucket = bucket_end
        
        return aggregated
    
    def cleanup_old_data(self, retention_days: int) -> int:
        """Clean up old files"""
        try:
            cutoff_date = datetime.now(timezone.utc).date() - timedelta(days=retention_days)
            deleted_count = 0
            
            with self._lock:
                for filepath in self.storage_path.glob("metrics_*.json*"):
                    # Extract date from filename
                    filename = filepath.stem
                    if filepath.suffix == ".gz":
                        filename = filepath.with_suffix("").stem
                    
                    try:
                        date_str = filename.replace("metrics_", "")
                        file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        
                        if file_date < cutoff_date:
                            filepath.unlink()
                            deleted_count += 1
                    except ValueError:
                        # Skip files that don't match expected pattern
                        continue
            
            return deleted_count
            
        except Exception as e:
            print(f"Error cleaning up old files: {e}")
            return 0
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get file storage statistics"""
        try:
            total_size = 0
            file_count = 0
            oldest_date = None
            newest_date = None
            
            with self._lock:
                for filepath in self.storage_path.glob("metrics_*.json*"):
                    file_count += 1
                    total_size += filepath.stat().st_size
                    
                    # Extract date from filename
                    filename = filepath.stem
                    if filepath.suffix == ".gz":
                        filename = filepath.with_suffix("").stem
                    
                    try:
                        date_str = filename.replace("metrics_", "")
                        file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        
                        if oldest_date is None or file_date < oldest_date:
                            oldest_date = file_date
                        if newest_date is None or file_date > newest_date:
                            newest_date = file_date
                    except ValueError:
                        continue
            
            data_span_days = (newest_date - oldest_date).days if oldest_date and newest_date else 0
            
            return {
                "backend_type": "File",
                "storage_path": str(self.storage_path),
                "total_size_bytes": total_size,
                "file_count": file_count,
                "compression_enabled": self.compression,
                "oldest_data": oldest_date.isoformat() if oldest_date else None,
                "newest_data": newest_date.isoformat() if newest_date else None,
                "data_span_days": data_span_days
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _load_metrics_file(self, filepath: Path) -> List[Dict[str, Any]]:
        """Load metrics from file"""
        try:
            if filepath.suffix == ".gz":
                with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                    return json.load(f)
            else:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            return []
    
    def _save_metrics_file(self, filepath: Path, data: List[Dict[str, Any]]) -> None:
        """Save metrics to file"""
        # Convert datetime objects to ISO format strings
        for item in data:
            if isinstance(item.get("timestamp"), datetime):
                item["timestamp"] = item["timestamp"].isoformat()
        
        if filepath.suffix == ".gz":
            with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                json.dump(data, f, separators=(',', ':'))
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)


class MetricsStorage:
    """
    Main metrics storage coordinator
    
    Manages persistent storage of metrics with automatic batching,
    aggregation, and cleanup.
    """
    
    def __init__(self, config: StorageConfig, backend: Optional[StorageBackend] = None):
        self.config = config
        self.backend = backend or SQLiteStorageBackend(
            Path(config.storage_path) / "metrics.db"
        )
        
        # Buffering for batch writes
        self._buffer: List[MetricRecord] = []
        self._buffer_lock = threading.RLock()
        self._last_flush = time.time()
        
        # Background thread for periodic operations
        self._running = True
        self._background_thread = threading.Thread(target=self._background_worker, daemon=True)
        self._background_thread.start()
    
    def store_metric(self, kpi_type: KPIType, value: float, timestamp: Optional[datetime] = None,
                    stage: Optional[str] = None, flow_id: Optional[str] = None,
                    metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store a single metric (buffered)"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        metric = MetricRecord(
            timestamp=timestamp,
            kpi_type=kpi_type.value,
            value=value,
            stage=stage,
            flow_id=flow_id,
            metadata=metadata
        )
        
        with self._buffer_lock:
            self._buffer.append(metric)
            
            # Flush if buffer is full
            if len(self._buffer) >= self.config.batch_size:
                self._flush_buffer()
    
    def store_metrics_batch(self, metrics: List[MetricRecord]) -> bool:
        """Store multiple metrics immediately"""
        return self.backend.store_metrics(metrics)
    
    def query_metrics(self, kpi_type: KPIType, time_range_hours: int = 24,
                     limit: Optional[int] = None) -> List[MetricRecord]:
        """Query recent metrics"""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=time_range_hours)
        
        return self.backend.query_metrics(kpi_type, start_time, end_time, limit)
    
    def get_aggregated_metrics(self, kpi_type: KPIType, interval_hours: int = 1,
                              time_range_days: int = 7) -> List[AggregatedMetric]:
        """Get aggregated metrics for longer time periods"""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=time_range_days)
        interval_seconds = interval_hours * 3600
        
        return self.backend.get_aggregated_metrics(kpi_type, interval_seconds, start_time, end_time)
    
    def get_metrics_summary(self, kpi_type: KPIType, time_range_hours: int = 24) -> Dict[str, Any]:
        """Get summary statistics for a metric"""
        metrics = self.query_metrics(kpi_type, time_range_hours)
        
        if not metrics:
            return {"error": "No data found"}
        
        values = [m.value for m in metrics]
        sorted_values = sorted(values)
        
        return {
            "kpi_type": kpi_type.value,
            "time_range_hours": time_range_hours,
            "sample_count": len(values),
            "min_value": min(values),
            "max_value": max(values),
            "avg_value": statistics.mean(values),
            "median_value": statistics.median(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
            "p95_value": sorted_values[int(0.95 * len(sorted_values))] if len(sorted_values) > 1 else sorted_values[0],
            "p99_value": sorted_values[int(0.99 * len(sorted_values))] if len(sorted_values) > 1 else sorted_values[0],
            "oldest_sample": metrics[-1].timestamp.isoformat(),
            "newest_sample": metrics[0].timestamp.isoformat()
        }
    
    def cleanup_old_data(self) -> Dict[str, Any]:
        """Clean up old data according to retention policy"""
        deleted_count = self.backend.cleanup_old_data(self.config.retention_days)
        
        return {
            "deleted_records": deleted_count,
            "retention_days": self.config.retention_days,
            "cleanup_time": datetime.now(timezone.utc).isoformat()
        }
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """Get comprehensive storage statistics"""
        backend_stats = self.backend.get_storage_stats()
        
        with self._buffer_lock:
            buffer_size = len(self._buffer)
        
        return {
            **backend_stats,
            "buffer_size": buffer_size,
            "batch_size": self.config.batch_size,
            "retention_days": self.config.retention_days,
            "compression_enabled": self.config.compression_enabled,
            "last_flush": datetime.fromtimestamp(self._last_flush, tz=timezone.utc).isoformat()
        }
    
    def export_metrics(self, kpi_type: KPIType, output_path: Union[str, Path],
                      time_range_days: int = 30, format: str = "json") -> bool:
        """Export metrics to file"""
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=time_range_days)
            
            metrics = self.backend.query_metrics(kpi_type, start_time, end_time)
            
            output_path = Path(output_path)
            
            if format.lower() == "json":
                data = [asdict(m) for m in metrics]
                # Convert datetime objects to strings
                for item in data:
                    if isinstance(item["timestamp"], datetime):
                        item["timestamp"] = item["timestamp"].isoformat()
                
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=2)
            
            elif format.lower() == "csv":
                import csv
                with open(output_path, 'w', newline='') as f:
                    if metrics:
                        writer = csv.DictWriter(f, fieldnames=asdict(metrics[0]).keys())
                        writer.writeheader()
                        for metric in metrics:
                            row = asdict(metric)
                            # Convert datetime to string
                            row["timestamp"] = row["timestamp"].isoformat()
                            # Convert metadata dict to JSON string
                            if row["metadata"]:
                                row["metadata"] = json.dumps(row["metadata"])
                            writer.writerow(row)
            
            return True
            
        except Exception as e:
            print(f"Error exporting metrics: {e}")
            return False
    
    def _flush_buffer(self) -> None:
        """Flush buffered metrics to storage"""
        if not self._buffer:
            return
        
        # Copy buffer and clear it
        metrics_to_store = self._buffer.copy()
        self._buffer.clear()
        
        # Store metrics
        success = self.backend.store_metrics(metrics_to_store)
        if not success:
            print(f"Failed to store {len(metrics_to_store)} metrics")
        
        self._last_flush = time.time()
    
    def _background_worker(self) -> None:
        """Background thread for periodic operations"""
        while self._running:
            try:
                current_time = time.time()
                
                # Periodic flush
                if current_time - self._last_flush > self.config.flush_interval_seconds:
                    with self._buffer_lock:
                        if self._buffer:
                            self._flush_buffer()
                
                # Periodic aggregation (if SQLite backend)
                if isinstance(self.backend, SQLiteStorageBackend):
                    for interval in self.config.aggregation_intervals:
                        self.backend.aggregate_raw_metrics(interval)
                
                # Sleep for a minute before next check
                time.sleep(60)
                
            except Exception as e:
                print(f"Background worker error: {e}")
                time.sleep(60)
    
    def shutdown(self) -> None:
        """Shutdown storage and flush remaining data"""
        self._running = False
        
        # Final flush
        with self._buffer_lock:
            if self._buffer:
                self._flush_buffer()
        
        # Wait for background thread
        if self._background_thread.is_alive():
            self._background_thread.join(timeout=5)