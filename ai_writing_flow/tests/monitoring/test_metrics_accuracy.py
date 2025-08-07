"""
Metrics Accuracy Tests - Phase 3, Task 26.1

This test suite validates that all metrics collection and calculation 
mechanisms produce accurate results within expected tolerances.

Key Test Areas:
- KPI calculation accuracy (CPU, memory, throughput, etc.)
- Time series data accuracy and aggregation
- Percentile calculations (P95, P99)
- Flow efficiency and resource efficiency metrics
- Storage and retrieval accuracy
- Dashboard API data consistency
"""

import pytest
import time
import threading
import statistics
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys
import tempfile
import shutil

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from ai_writing_flow.monitoring.flow_metrics import (
    FlowMetrics, KPIType, MetricsConfig, KPISnapshot, MetricDataPoint
)
from ai_writing_flow.monitoring.dashboard_api import DashboardAPI, TimeRange
from ai_writing_flow.monitoring.storage import (
    MetricsStorage, StorageConfig, SQLiteStorageBackend, FileStorageBackend, MetricRecord
)


class TestKPICalculationAccuracy:
    """Test accuracy of core KPI calculations"""
    
    def setup_method(self):
        """Setup metrics instance for testing"""
        config = MetricsConfig(
            cache_duration=0.1,  # Short cache for testing
            time_window=60,
            throughput_window=30
        )
        self.metrics = FlowMetrics(history_size=100, config=config)
    
    def test_cpu_usage_accuracy(self):
        """Test CPU usage metric accuracy"""
        # Mock psutil to return known values
        with patch('ai_writing_flow.monitoring.flow_metrics.psutil.Process') as mock_process:
            mock_instance = Mock()
            mock_instance.cpu_percent.return_value = 45.5
            mock_instance.memory_info.return_value = Mock(rss=100 * 1024 * 1024)  # 100MB
            mock_process.return_value = mock_instance
            
            # Record system metrics multiple times
            for _ in range(5):
                self.metrics.record_system_metrics()
                time.sleep(0.01)
            
            kpis = self.metrics.get_current_kpis(force_recalculate=True)
            
            # CPU usage should match mocked value (latest value strategy)
            assert abs(kpis.cpu_usage - 45.5) < 0.1, f"Expected ~45.5, got {kpis.cpu_usage}"
            
            # Memory should be ~100MB
            assert abs(kpis.memory_usage - 100.0) < 1.0, f"Expected ~100MB, got {kpis.memory_usage}"
    
    def test_execution_time_accuracy(self):
        """Test execution time calculations"""
        flow_id = "test_flow_accuracy"
        expected_times = [1.0, 2.0, 3.0, 1.5, 2.5]  # Known execution times
        
        # Record flow with known execution times
        self.metrics.record_flow_start(flow_id, "input_validation")
        
        for i, exec_time in enumerate(expected_times):
            stage = f"stage_{i}"
            self.metrics.record_stage_completion(flow_id, stage, exec_time, success=True)
        
        self.metrics.record_flow_completion(flow_id, success=True)
        
        kpis = self.metrics.get_current_kpis(force_recalculate=True)
        
        # Average should match statistics.mean(expected_times)
        expected_avg = statistics.mean(expected_times)
        assert abs(kpis.avg_execution_time - expected_avg) < 0.01, \
            f"Expected avg {expected_avg}, got {kpis.avg_execution_time}"
        
        # P95 and P99 calculations
        sorted_times = sorted(expected_times)
        expected_p95 = sorted_times[int(0.95 * len(sorted_times))]
        expected_p99 = sorted_times[int(0.99 * len(sorted_times))]
        
        assert abs(kpis.p95_execution_time - expected_p95) < 0.01, \
            f"Expected P95 {expected_p95}, got {kpis.p95_execution_time}"
        assert abs(kpis.p99_execution_time - expected_p99) < 0.01, \
            f"Expected P99 {expected_p99}, got {kpis.p99_execution_time}"
    
    def test_success_rate_accuracy(self):
        """Test success rate calculation accuracy"""
        # Record 7 successful and 3 failed executions
        successes = 7
        failures = 3
        
        for i in range(successes):
            flow_id = f"success_flow_{i}"
            self.metrics.record_flow_start(flow_id, "test_stage")
            self.metrics.record_stage_completion(flow_id, "test_stage", 1.0, success=True)
            self.metrics.record_flow_completion(flow_id, success=True)
        
        for i in range(failures):
            flow_id = f"failure_flow_{i}"
            self.metrics.record_flow_start(flow_id, "test_stage")
            self.metrics.record_stage_completion(flow_id, "test_stage", 1.0, success=False)
            self.metrics.record_flow_completion(flow_id, success=False)
        
        kpis = self.metrics.get_current_kpis(force_recalculate=True)
        
        # Success rate should be 70% (7/10)
        expected_success_rate = (successes / (successes + failures)) * 100
        assert abs(kpis.success_rate - expected_success_rate) < 0.1, \
            f"Expected success rate {expected_success_rate}%, got {kpis.success_rate}%"
        
        # Error rate should be 30% (3/10)
        expected_error_rate = (failures / (successes + failures)) * 100
        assert abs(kpis.error_rate - expected_error_rate) < 0.1, \
            f"Expected error rate {expected_error_rate}%, got {kpis.error_rate}%"
    
    def test_throughput_calculation_accuracy(self):
        """Test throughput calculation accuracy"""
        # Record flows with known timing
        start_time = time.time()
        
        # Record 10 flows over ~2 seconds
        for i in range(10):
            flow_id = f"throughput_flow_{i}"
            self.metrics.record_flow_start(flow_id, "test_stage")
            self.metrics.record_stage_completion(flow_id, "test_stage", 0.1, success=True)
            self.metrics.record_flow_completion(flow_id, success=True)
            time.sleep(0.2)  # 200ms between flows
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        kpis = self.metrics.get_current_kpis(force_recalculate=True)
        
        # Expected throughput: 10 flows / actual_duration
        expected_throughput = 10 / actual_duration
        
        # Allow 10% tolerance for timing variations
        assert abs(kpis.throughput - expected_throughput) < expected_throughput * 0.1, \
            f"Expected throughput ~{expected_throughput:.2f}, got {kpis.throughput:.2f}"
    
    def test_flow_efficiency_accuracy(self):
        """Test flow efficiency calculation"""
        # Create flows with known stage success patterns
        # Flow 1: 3/3 stages successful = 100% efficiency
        flow1 = "efficiency_flow_1"
        self.metrics.record_flow_start(flow1, "stage1")
        self.metrics.record_stage_completion(flow1, "stage1", 1.0, success=True)
        self.metrics.record_stage_completion(flow1, "stage2", 1.0, success=True)
        self.metrics.record_stage_completion(flow1, "stage3", 1.0, success=True)
        self.metrics.record_flow_completion(flow1, success=True)
        
        # Flow 2: 2/3 stages successful = 66.67% efficiency
        flow2 = "efficiency_flow_2"
        self.metrics.record_flow_start(flow2, "stage1")
        self.metrics.record_stage_completion(flow2, "stage1", 1.0, success=True)
        self.metrics.record_stage_completion(flow2, "stage2", 1.0, success=False)
        self.metrics.record_stage_completion(flow2, "stage3", 1.0, success=True)
        self.metrics.record_flow_completion(flow2, success=False)
        
        kpis = self.metrics.get_current_kpis(force_recalculate=True)
        
        # Overall efficiency: (3 + 2) successful / (3 + 3) total = 5/6 = 83.33%
        expected_efficiency = (5 / 6) * 100
        assert abs(kpis.flow_efficiency - expected_efficiency) < 0.1, \
            f"Expected efficiency {expected_efficiency:.2f}%, got {kpis.flow_efficiency:.2f}%"
    
    def test_resource_efficiency_accuracy(self):
        """Test resource efficiency calculation"""
        # Mock system resources
        with patch('ai_writing_flow.monitoring.flow_metrics.psutil.Process') as mock_process:
            mock_instance = Mock()
            mock_instance.cpu_percent.return_value = 50.0  # 50% CPU
            mock_instance.memory_info.return_value = Mock(rss=512 * 1024 * 1024)  # 512MB
            mock_process.return_value = mock_instance
            
            # Record some flows to generate throughput
            for i in range(5):
                flow_id = f"resource_flow_{i}"
                self.metrics.record_flow_start(flow_id, "test_stage")
                self.metrics.record_stage_completion(flow_id, "test_stage", 0.1, success=True)
                self.metrics.record_flow_completion(flow_id, success=True)
                time.sleep(0.1)
            
            kpis = self.metrics.get_current_kpis(force_recalculate=True)
            
            # Resource efficiency = throughput / ((cpu/100 + memory_gb) / 2)
            # CPU normalized: 50/100 = 0.5
            # Memory normalized: 512/1024 = 0.5 GB
            # Resource score: (0.5 + 0.5) / 2 = 0.5
            # Resource efficiency = throughput / 0.5 = throughput * 2
            
            expected_resource_efficiency = kpis.throughput * 2
            assert abs(kpis.resource_efficiency - expected_resource_efficiency) < 0.1, \
                f"Expected resource efficiency {expected_resource_efficiency:.2f}, got {kpis.resource_efficiency:.2f}"
    
    def test_stage_duration_accuracy(self):
        """Test stage-specific duration tracking accuracy"""
        stage_durations = {
            "stage_a": [1.0, 1.5, 2.0],
            "stage_b": [0.5, 0.8, 1.2],
            "stage_c": [3.0, 2.5, 3.5]
        }
        
        flow_id = "duration_test_flow"
        self.metrics.record_flow_start(flow_id, "stage_a")
        
        # Record known durations for each stage
        for stage_name, durations in stage_durations.items():
            for duration in durations:
                self.metrics.record_stage_completion(flow_id, stage_name, duration, success=True)
        
        # Get stage performance summary
        stage_summary = self.metrics.get_stage_performance_summary()
        
        # Verify accuracy for each stage
        for stage_name, expected_durations in stage_durations.items():
            assert stage_name in stage_summary, f"Stage {stage_name} not found in summary"
            
            stage_stats = stage_summary[stage_name]
            expected_avg = statistics.mean(expected_durations)
            expected_min = min(expected_durations)
            expected_max = max(expected_durations)
            expected_median = statistics.median(expected_durations)
            
            assert abs(stage_stats["avg_duration"] - expected_avg) < 0.01, \
                f"Stage {stage_name} avg: expected {expected_avg}, got {stage_stats['avg_duration']}"
            assert abs(stage_stats["min_duration"] - expected_min) < 0.01, \
                f"Stage {stage_name} min: expected {expected_min}, got {stage_stats['min_duration']}"
            assert abs(stage_stats["max_duration"] - expected_max) < 0.01, \
                f"Stage {stage_name} max: expected {expected_max}, got {stage_stats['max_duration']}"
            assert abs(stage_stats["median_duration"] - expected_median) < 0.01, \
                f"Stage {stage_name} median: expected {expected_median}, got {stage_stats['median_duration']}"
            assert stage_stats["total_executions"] == len(expected_durations), \
                f"Stage {stage_name} executions: expected {len(expected_durations)}, got {stage_stats['total_executions']}"


class TestTimeSeriesAccuracy:
    """Test time series data accuracy and aggregation"""
    
    def setup_method(self):
        """Setup for time series tests"""
        self.metrics = FlowMetrics(history_size=1000)
        self.dashboard_api = DashboardAPI(self.metrics)
    
    def test_time_series_data_points_accuracy(self):
        """Test that time series data points match recorded metrics"""
        # Record metrics with known timestamps and values
        base_time = datetime.now(timezone.utc)
        known_data = [
            (base_time - timedelta(minutes=10), 50.0),
            (base_time - timedelta(minutes=8), 60.0),
            (base_time - timedelta(minutes=6), 55.0),
            (base_time - timedelta(minutes=4), 70.0),
            (base_time - timedelta(minutes=2), 65.0),
        ]
        
        # Manually add metrics with specific timestamps
        for timestamp, value in known_data:
            metric_point = MetricDataPoint(
                timestamp=timestamp,
                value=value,
                stage="test_stage",
                flow_id="ts_test_flow"
            )
            self.metrics._metrics[KPIType.CPU_USAGE].append(metric_point)
        
        # Get time series data
        time_series = self.dashboard_api.get_time_series_data(
            KPIType.CPU_USAGE, 
            TimeRange.LAST_15_MINUTES,
            resolution=120  # 2-minute buckets
        )
        
        # Verify data points are present and accurate
        assert len(time_series.data_points) > 0, "No time series data points found"
        
        # Check summary statistics
        expected_values = [point[1] for point in known_data]
        expected_min = min(expected_values)
        expected_max = max(expected_values)
        expected_avg = statistics.mean(expected_values)
        
        assert abs(time_series.summary["min"] - expected_min) < 0.1, \
            f"Time series min: expected {expected_min}, got {time_series.summary['min']}"
        assert abs(time_series.summary["max"] - expected_max) < 0.1, \
            f"Time series max: expected {expected_max}, got {time_series.summary['max']}"
        assert abs(time_series.summary["avg"] - expected_avg) < 0.1, \
            f"Time series avg: expected {expected_avg}, got {time_series.summary['avg']}"
    
    def test_time_series_aggregation_accuracy(self):
        """Test time series aggregation into buckets"""
        # Add metrics across multiple time buckets
        base_time = datetime.now(timezone.utc)
        
        # Bucket 1: 3 values [10, 20, 30] -> avg = 20
        bucket1_values = [10.0, 20.0, 30.0]
        for i, value in enumerate(bucket1_values):
            timestamp = base_time - timedelta(minutes=10) + timedelta(seconds=i*20)
            metric_point = MetricDataPoint(timestamp=timestamp, value=value)
            self.metrics._metrics[KPIType.THROUGHPUT].append(metric_point)
        
        # Bucket 2: 2 values [40, 50] -> avg = 45
        bucket2_values = [40.0, 50.0]
        for i, value in enumerate(bucket2_values):
            timestamp = base_time - timedelta(minutes=8) + timedelta(seconds=i*20)
            metric_point = MetricDataPoint(timestamp=timestamp, value=value)
            self.metrics._metrics[KPIType.THROUGHPUT].append(metric_point)
        
        # Get aggregated time series with 2-minute resolution
        time_series = self.dashboard_api.get_time_series_data(
            KPIType.THROUGHPUT,
            TimeRange.LAST_15_MINUTES,
            resolution=120  # 2-minute buckets
        )
        
        # Should have at least 2 buckets with aggregated values
        bucket_values = [point.value for point in time_series.data_points if point.metadata and point.metadata.get("samples", 0) > 1]
        
        # Check aggregated values (allowing for some tolerance due to time bucketing)
        if len(bucket_values) >= 2:
            expected_values = [20.0, 45.0]  # Expected averages
            for expected in expected_values:
                found_close_match = any(abs(actual - expected) < 5.0 for actual in bucket_values)
                assert found_close_match, f"Expected aggregated value ~{expected} not found in {bucket_values}"


class TestStorageAccuracy:
    """Test storage and retrieval accuracy"""
    
    def setup_method(self):
        """Setup storage tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_config = StorageConfig(
            storage_path=self.temp_dir,
            retention_days=7,
            batch_size=10
        )
    
    def teardown_method(self):
        """Cleanup test storage"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_sqlite_storage_accuracy(self):
        """Test SQLite storage accuracy"""
        # Create SQLite storage
        db_path = Path(self.temp_dir) / "test_metrics.db"
        backend = SQLiteStorageBackend(db_path)
        
        # Known metrics to store
        test_metrics = [
            MetricRecord(
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=10),
                kpi_type=KPIType.CPU_USAGE.value,
                value=45.5,
                stage="test_stage",
                flow_id="test_flow_1",
                metadata={"test": "data"}
            ),
            MetricRecord(
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=5),
                kpi_type=KPIType.CPU_USAGE.value,
                value=55.2,
                stage="test_stage",
                flow_id="test_flow_2",
                metadata={"test": "data2"}
            )
        ]
        
        # Store metrics
        success = backend.store_metrics(test_metrics)
        assert success, "Failed to store metrics"
        
        # Retrieve metrics
        start_time = datetime.now(timezone.utc) - timedelta(minutes=15)
        end_time = datetime.now(timezone.utc)
        retrieved = backend.query_metrics(KPIType.CPU_USAGE, start_time, end_time)
        
        # Verify accuracy
        assert len(retrieved) == 2, f"Expected 2 retrieved metrics, got {len(retrieved)}"
        
        # Check values (order might be different due to DESC sorting)
        retrieved_values = sorted([m.value for m in retrieved])
        expected_values = sorted([m.value for m in test_metrics])
        
        for retrieved_val, expected_val in zip(retrieved_values, expected_values):
            assert abs(retrieved_val - expected_val) < 0.01, \
                f"Retrieved value {retrieved_val} doesn't match expected {expected_val}"
        
        # Check metadata
        retrieved_metadata = [m.metadata for m in retrieved if m.metadata]
        assert len(retrieved_metadata) >= 2, "Metadata not preserved correctly"
    
    def test_file_storage_accuracy(self):
        """Test file storage accuracy"""
        # Create file storage backend
        backend = FileStorageBackend(Path(self.temp_dir) / "file_storage", compression=True)
        
        # Test metrics spanning multiple days for date-based file storage
        base_time = datetime.now(timezone.utc)
        test_metrics = [
            MetricRecord(
                timestamp=base_time - timedelta(days=1),
                kpi_type=KPIType.MEMORY_USAGE.value,
                value=100.5,
                stage="memory_stage",
                flow_id="memory_flow_1"
            ),
            MetricRecord(
                timestamp=base_time,
                kpi_type=KPIType.MEMORY_USAGE.value,
                value=150.8,
                stage="memory_stage",
                flow_id="memory_flow_2"
            )
        ]
        
        # Store metrics
        success = backend.store_metrics(test_metrics)
        assert success, "Failed to store metrics to file backend"
        
        # Retrieve metrics
        start_time = base_time - timedelta(days=2)
        end_time = base_time + timedelta(hours=1)
        retrieved = backend.query_metrics(KPIType.MEMORY_USAGE, start_time, end_time)
        
        # Verify accuracy
        assert len(retrieved) == 2, f"Expected 2 retrieved metrics, got {len(retrieved)}"
        
        retrieved_values = sorted([m.value for m in retrieved])
        expected_values = sorted([m.value for m in test_metrics])
        
        for retrieved_val, expected_val in zip(retrieved_values, expected_values):
            assert abs(retrieved_val - expected_val) < 0.01, \
                f"File storage: Retrieved value {retrieved_val} doesn't match expected {expected_val}"
    
    def test_aggregated_metrics_accuracy(self):
        """Test aggregated metrics calculation accuracy"""
        db_path = Path(self.temp_dir) / "aggregation_test.db"
        backend = SQLiteStorageBackend(db_path)
        
        # Create metrics for aggregation testing
        base_time = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        
        # Hour 1: values [10, 20, 30] -> avg=20, min=10, max=30
        hour1_values = [10.0, 20.0, 30.0]
        for i, value in enumerate(hour1_values):
            metric = MetricRecord(
                timestamp=base_time - timedelta(hours=1) + timedelta(minutes=i*10),
                kpi_type=KPIType.THROUGHPUT.value,
                value=value
            )
            backend.store_metrics([metric])
        
        # Run aggregation
        aggregated_count = backend.aggregate_raw_metrics(3600)  # 1 hour intervals
        assert aggregated_count > 0, "No metrics were aggregated"
        
        # Retrieve aggregated data
        start_time = base_time - timedelta(hours=2)
        end_time = base_time
        aggregated = backend.get_aggregated_metrics(KPIType.THROUGHPUT, 3600, start_time, end_time)
        
        # Find the aggregated bucket for our test data
        test_bucket = None
        for agg in aggregated:
            if agg.count == 3:  # Should have 3 samples
                test_bucket = agg
                break
        
        assert test_bucket is not None, "Aggregated bucket with 3 samples not found"
        
        # Verify aggregation accuracy
        expected_avg = statistics.mean(hour1_values)
        expected_min = min(hour1_values)
        expected_max = max(hour1_values)
        expected_sum = sum(hour1_values)
        
        assert abs(test_bucket.avg_value - expected_avg) < 0.01, \
            f"Aggregated avg: expected {expected_avg}, got {test_bucket.avg_value}"
        assert abs(test_bucket.min_value - expected_min) < 0.01, \
            f"Aggregated min: expected {expected_min}, got {test_bucket.min_value}"
        assert abs(test_bucket.max_value - expected_max) < 0.01, \
            f"Aggregated max: expected {expected_max}, got {test_bucket.max_value}"
        assert abs(test_bucket.sum_value - expected_sum) < 0.01, \
            f"Aggregated sum: expected {expected_sum}, got {test_bucket.sum_value}"
        assert test_bucket.count == 3, \
            f"Aggregated count: expected 3, got {test_bucket.count}"


class TestDashboardAPIAccuracy:
    """Test Dashboard API data accuracy"""
    
    def setup_method(self):
        """Setup dashboard API tests"""
        self.metrics = FlowMetrics(history_size=500)
        self.dashboard = DashboardAPI(self.metrics)
    
    def test_dashboard_overview_accuracy(self):
        """Test dashboard overview data accuracy"""
        # Create known flow data
        flow_id = "dashboard_test_flow"
        
        # Mock system metrics
        with patch('ai_writing_flow.monitoring.flow_metrics.psutil.Process') as mock_process:
            mock_instance = Mock()
            mock_instance.cpu_percent.return_value = 35.5 
            mock_instance.memory_info.return_value = Mock(rss=200 * 1024 * 1024)  # 200MB
            mock_process.return_value = mock_instance
            
            # Record some flows
            success_flows = 8
            failed_flows = 2
            
            for i in range(success_flows):
                fid = f"{flow_id}_success_{i}"
                self.metrics.record_flow_start(fid, "test_stage")
                self.metrics.record_stage_completion(fid, "test_stage", 1.5, success=True)
                self.metrics.record_flow_completion(fid, success=True)
            
            for i in range(failed_flows):
                fid = f"{flow_id}_failed_{i}"
                self.metrics.record_flow_start(fid, "test_stage")
                self.metrics.record_stage_completion(fid, "test_stage", 1.5, success=False)
                self.metrics.record_flow_completion(fid, success=False)
            
            # Get dashboard overview
            dashboard_data = self.dashboard.get_dashboard_overview()
            
            # Verify overview accuracy
            expected_success_rate = (success_flows / (success_flows + failed_flows)) * 100
            actual_success_rate = dashboard_data.overview["success_rate"]["value"]
            
            assert abs(actual_success_rate - expected_success_rate) < 0.1, \
                f"Dashboard success rate: expected {expected_success_rate}%, got {actual_success_rate}%"
            
            # Verify execution time
            expected_avg_time = 1.5  # All flows had 1.5s execution time
            actual_avg_time = dashboard_data.overview["avg_execution_time"]["value"]
            
            assert abs(actual_avg_time - expected_avg_time) < 0.01, \
                f"Dashboard avg execution time: expected {expected_avg_time}s, got {actual_avg_time}s"
            
            # Verify system metrics
            performance_data = dashboard_data.performance
            assert abs(performance_data["resource_usage"]["cpu"]["value"] - 35.5) < 0.1, \
                "Dashboard CPU usage doesn't match metrics"
            assert abs(performance_data["resource_usage"]["memory"]["value"] - 200.0) < 1.0, \
                "Dashboard memory usage doesn't match metrics"
    
    def test_health_check_accuracy(self):
        """Test health check calculations"""
        # Configure thresholds
        config = MetricsConfig(
            memory_threshold_mb=100.0,
            cpu_threshold_percent=50.0,
            error_rate_threshold=5.0
        )
        self.metrics.config = config
        
        # Mock system metrics within healthy ranges
        with patch('ai_writing_flow.monitoring.flow_metrics.psutil.Process') as mock_process:
            mock_instance = Mock()
            mock_instance.cpu_percent.return_value = 30.0  # Under 50% threshold
            mock_instance.memory_info.return_value = Mock(rss=80 * 1024 * 1024)  # 80MB under 100MB threshold
            mock_process.return_value = mock_instance
            
            # Record successful flows (low error rate)
            for i in range(20):
                flow_id = f"health_flow_{i}"
                self.metrics.record_flow_start(flow_id, "test_stage")
                self.metrics.record_stage_completion(flow_id, "test_stage", 1.0, success=True)
                self.metrics.record_flow_completion(flow_id, success=True)
            
            # Get health check
            health = self.dashboard.get_health_check()
            
            # Should be healthy
            assert health["status"] == "healthy", f"Expected healthy status, got {health['status']}"
            
            # All checks should pass
            checks = health["checks"]
            assert checks["memory_usage"] == True, "Memory usage check should pass"
            assert checks["cpu_usage"] == True, "CPU usage check should pass"
            assert checks["error_rate"] == True, "Error rate check should pass"
    
    def test_flow_details_accuracy(self):
        """Test flow details data accuracy"""
        # Create flows with known characteristics
        active_flow = "active_test_flow"
        completed_flow = "completed_test_flow"
        
        # Active flow
        self.metrics.record_flow_start(active_flow, "stage1")
        self.metrics.record_stage_completion(active_flow, "stage1", 1.0, success=True)
        self.metrics.record_stage_completion(active_flow, "stage2", 1.5, success=True)
        # Don't complete this flow - keep it active
        
        # Completed flow
        self.metrics.record_flow_start(completed_flow, "stage1")
        self.metrics.record_stage_completion(completed_flow, "stage1", 2.0, success=True)
        self.metrics.record_flow_completion(completed_flow, success=True)
        
        # Get all flows overview
        flows_overview = self.dashboard.get_flow_details()
        
        # Verify active flows
        active_flows = flows_overview["active_flows"]
        assert len(active_flows) == 1, f"Expected 1 active flow, got {len(active_flows)}"
        
        active_flow_data = active_flows[0]
        assert active_flow_data["flow_id"] == active_flow, "Active flow ID mismatch"
        assert active_flow_data["stages_completed"] == 2, "Active flow stages count mismatch"
        assert active_flow_data["status"] == "active", "Active flow status mismatch"
        
        # Verify completed flows
        completed_flows = flows_overview["recent_completed"]
        assert len(completed_flows) >= 1, "Should have at least 1 completed flow"
        
        # Find our test flow in completed flows
        test_completed = next((f for f in completed_flows if f["flow_id"] == completed_flow), None)
        assert test_completed is not None, "Completed test flow not found"
        assert test_completed["status"] == "completed", "Completed flow status mismatch"


class TestEdgeCasesAccuracy:
    """Test accuracy in edge cases and boundary conditions"""
    
    def setup_method(self):
        """Setup for edge case testing"""
        self.metrics = FlowMetrics(history_size=50)  # Small history for edge case testing
    
    def test_empty_metrics_accuracy(self):
        """Test behavior with no metrics data"""
        kpis = self.metrics.get_current_kpis(force_recalculate=True)
        
        # All values should be zero or sensible defaults
        assert kpis.success_rate == 0.0, "Success rate should be 0 with no data"
        assert kpis.error_rate == 0.0, "Error rate should be 0 with no data"
        assert kpis.avg_execution_time == 0.0, "Avg execution time should be 0 with no data"
        assert kpis.throughput == 0.0, "Throughput should be 0 with no data"
        assert kpis.active_flows == 0, "Active flows should be 0 with no data"
        assert kpis.total_executions == 0, "Total executions should be 0 with no data"
    
    def test_single_data_point_accuracy(self):
        """Test calculations with only one data point"""
        flow_id = "single_point_flow"
        execution_time = 2.5
        
        self.metrics.record_flow_start(flow_id, "single_stage")
        self.metrics.record_stage_completion(flow_id, "single_stage", execution_time, success=True)
        self.metrics.record_flow_completion(flow_id, success=True)
        
        kpis = self.metrics.get_current_kpis(force_recalculate=True)
        
        # With single data point, avg = min = max = P95 = P99
        assert abs(kpis.avg_execution_time - execution_time) < 0.01, \
            f"Single point avg should equal the value: expected {execution_time}, got {kpis.avg_execution_time}"
        assert abs(kpis.p95_execution_time - execution_time) < 0.01, \
            f"Single point P95 should equal the value: expected {execution_time}, got {kpis.p95_execution_time}"
        assert abs(kpis.p99_execution_time - execution_time) < 0.01, \
            f"Single point P99 should equal the value: expected {execution_time}, got {kpis.p99_execution_time}"
        
        assert kpis.success_rate == 100.0, "Single successful flow should give 100% success rate"
        assert kpis.error_rate == 0.0, "Single successful flow should give 0% error rate"
    
    def test_extreme_values_accuracy(self):
        """Test handling of extreme values"""
        flow_id = "extreme_values_flow"
        
        # Very small and very large execution times
        extreme_times = [0.001, 0.005, 1000.0, 5000.0, 0.1]
        
        self.metrics.record_flow_start(flow_id, "extreme_stage")
        
        for i, exec_time in enumerate(extreme_times):
            stage_name = f"stage_{i}"
            self.metrics.record_stage_completion(flow_id, stage_name, exec_time, success=True)
        
        self.metrics.record_flow_completion(flow_id, success=True)
        
        kpis = self.metrics.get_current_kpis(force_recalculate=True)
        
        # Verify calculations handle extreme values correctly
        expected_avg = statistics.mean(extreme_times)
        assert abs(kpis.avg_execution_time - expected_avg) < 0.1, \
            f"Extreme values avg: expected {expected_avg}, got {kpis.avg_execution_time}"
        
        # Min and max should be the actual extremes
        expected_min = min(extreme_times)
        expected_max = max(extreme_times)
        
        # Get detailed metrics to check min/max (not directly in KPISnapshot)
        stage_summary = self.metrics.get_stage_performance_summary()
        all_min_durations = [stage_data["min_duration"] for stage_data in stage_summary.values()]
        all_max_durations = [stage_data["max_duration"] for stage_data in stage_summary.values()]
        
        actual_min = min(all_min_durations) if all_min_durations else float('inf')
        actual_max = max(all_max_durations) if all_max_durations else float('-inf')
        
        assert abs(actual_min - expected_min) < 0.01, \
            f"Extreme values min: expected {expected_min}, got {actual_min}"
        assert abs(actual_max - expected_max) < 0.1, \
            f"Extreme values max: expected {expected_max}, got {actual_max}"
    
    def test_concurrent_metrics_accuracy(self):
        """Test accuracy under concurrent access"""
        results = []
        errors = []
        
        def record_metrics_concurrently(thread_id):
            """Record metrics from multiple threads"""
            try:
                for i in range(10):
                    flow_id = f"concurrent_flow_{thread_id}_{i}"
                    self.metrics.record_flow_start(flow_id, "concurrent_stage")
                    self.metrics.record_stage_completion(flow_id, "concurrent_stage", 1.0, success=True)
                    self.metrics.record_flow_completion(flow_id, success=True)
                    time.sleep(0.001)  # Small delay
                
                results.append(f"Thread {thread_id} completed")
                
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
        
        # Run concurrent metric recording
        threads = []
        for i in range(3):
            thread = threading.Thread(target=record_metrics_concurrently, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent execution errors: {errors}"
        assert len(results) == 3, f"Expected 3 threads to complete, got {len(results)}"
        
        # Verify final metrics accuracy
        kpis = self.metrics.get_current_kpis(force_recalculate=True)
        
        # Should have 30 total executions (3 threads * 10 flows each)
        expected_total = 30
        assert kpis.total_executions == expected_total, \
            f"Concurrent execution count: expected {expected_total}, got {kpis.total_executions}"
        
        # All should be successful
        assert kpis.success_rate == 100.0, \
            f"Concurrent success rate: expected 100%, got {kpis.success_rate}%"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])