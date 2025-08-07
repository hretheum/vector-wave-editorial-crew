#!/usr/bin/env python3
"""Test Essential Local Metrics - Task 12.1"""

import sys
import time
import random

sys.path.append('src')

from ai_writing_flow.monitoring.local_metrics import (
    LocalMetricsCollector,
    get_metrics_collector,
    track_flow,
    track_performance
)
from ai_writing_flow.monitoring.flow_metrics_integration import (
    MetricsEnabledFlow,
    with_metrics,
    show_metrics_dashboard
)

def test_local_metrics():
    """Test essential local metrics functionality"""
    
    print("🧪 Testing Essential Local Metrics - Task 12.1")
    print("=" * 60)
    
    # Test 1: Basic metrics collection
    print("\n1️⃣ Testing basic metrics collection...")
    try:
        collector = LocalMetricsCollector("test_metrics")
        
        # Track a flow
        flow_metric = collector.start_flow("test_flow_1", "test_flow", {
            "user": "test",
            "platform": "blog"
        })
        
        # Simulate stages
        collector.record_stage("test_flow_1", "initialization")
        time.sleep(0.1)
        collector.record_stage("test_flow_1", "processing")
        time.sleep(0.1)
        collector.record_stage("test_flow_1", "completion")
        
        # End flow
        collector.end_flow("test_flow_1", "completed")
        
        # Check metrics
        flow_metrics = collector.get_flow_metrics()
        assert flow_metrics["total_flows"] == 1
        assert flow_metrics["completed_flows"] == 1
        assert flow_metrics["success_rate"] == 1.0
        
        print("✅ Basic metrics collection working")
        print(f"✅ Flow duration: {flow_metric.duration:.2f}s")
        print(f"✅ Stages completed: {len(flow_metric.stages_completed)}")
        
    except Exception as e:
        print(f"❌ Basic metrics test failed: {e}")
        return False
    
    # Test 2: KB metrics tracking
    print("\n2️⃣ Testing KB metrics tracking...")
    try:
        # Start another flow
        collector.start_flow("test_flow_2", "kb_test_flow")
        
        # Simulate KB queries
        for i in range(10):
            cache_hit = random.random() > 0.3  # 70% cache hit rate
            collector.record_kb_query("test_flow_2", cache_hit)
        
        collector.end_flow("test_flow_2", "completed")
        
        # Check KB metrics
        kb_metrics = collector.get_kb_metrics()
        assert kb_metrics["total_queries"] == 10
        assert kb_metrics["cache_hit_rate"] > 0.5  # Should be around 0.7
        
        print("✅ KB metrics tracking working")
        print(f"✅ Total queries: {kb_metrics['total_queries']}")
        print(f"✅ Cache hit rate: {kb_metrics['cache_hit_rate']*100:.1f}%")
        
    except Exception as e:
        print(f"❌ KB metrics test failed: {e}")
        return False
    
    # Test 3: Performance metrics
    print("\n3️⃣ Testing performance metrics...")
    try:
        # Record various operations
        operations = ["content_generation", "validation", "kb_query"]
        
        for op in operations:
            for i in range(5):
                duration = random.uniform(0.1, 0.5)
                success = random.random() > 0.1  # 90% success
                collector.record_performance(op, duration, success=success)
        
        # Get performance metrics
        perf_metrics = collector.get_performance_metrics()
        
        for op in operations:
            assert op in perf_metrics
            assert perf_metrics[op]["count"] == 5
            assert perf_metrics[op]["avg_duration"] > 0
            
        print("✅ Performance metrics working")
        print("✅ Operations tracked:")
        for op, stats in perf_metrics.items():
            print(f"   - {op}: avg {stats['avg_duration']:.3f}s, "
                  f"success {stats['success_rate']*100:.0f}%")
        
    except Exception as e:
        print(f"❌ Performance metrics test failed: {e}")
        return False
    
    # Test 4: Error tracking
    print("\n4️⃣ Testing error tracking...")
    try:
        # Start flow that will fail
        collector.start_flow("test_flow_3", "error_test_flow")
        collector.record_stage("test_flow_3", "initialization")
        
        # Simulate failure
        errors = ["Connection timeout", "Invalid input"]
        collector.end_flow("test_flow_3", "failed", errors)
        
        # Check error tracking
        flow_metrics = collector.get_flow_metrics()
        recent_errors = flow_metrics.get("recent_errors", [])
        
        assert len(recent_errors) >= len(errors)
        assert collector.counters["failed_flows"] == 1
        assert collector.counters["total_errors"] == len(errors)
        
        print("✅ Error tracking working")
        print(f"✅ Errors recorded: {len(recent_errors)}")
        print(f"✅ Failed flows: {collector.counters['failed_flows']}")
        
    except Exception as e:
        print(f"❌ Error tracking test failed: {e}")
        return False
    
    # Test 5: Decorator integration
    print("\n5️⃣ Testing decorator integration...")
    try:
        # Test flow decorator
        @track_flow("decorated_flow")
        def test_flow_function():
            time.sleep(0.1)
            return "success"
        
        result = test_flow_function()
        assert result == "success"
        
        # Test performance decorator
        @track_performance("decorated_operation")
        def test_operation():
            time.sleep(0.05)
            return 42
        
        result = test_operation()
        assert result == 42
        
        # Check that metrics were recorded
        summary = collector.get_summary()
        assert summary["counters"]["total_flows"] > 0
        
        print("✅ Decorator integration working")
        print("✅ Flow and performance decorators functional")
        
    except Exception as e:
        print(f"❌ Decorator test failed: {e}")
        return False
    
    # Test 6: Metrics persistence
    print("\n6️⃣ Testing metrics persistence...")
    try:
        # Save current state
        collector._save_session()
        
        # Create new collector (should load previous data)
        new_collector = LocalMetricsCollector("test_metrics")
        
        # Check counters were restored
        assert new_collector.counters["total_flows"] > 0
        
        print("✅ Metrics persistence working")
        print(f"✅ Restored {new_collector.counters['total_flows']} flows from session")
        
    except Exception as e:
        print(f"❌ Persistence test failed: {e}")
        return False
    
    # Test 7: Global metrics collector
    print("\n7️⃣ Testing global metrics collector...")
    try:
        global_collector = get_metrics_collector()
        
        # Track a flow using global collector
        global_collector.start_flow("global_test", "global_flow")
        global_collector.record_kb_query("global_test", cache_hit=True)
        global_collector.end_flow("global_test", "completed")
        
        # Verify it's tracking
        metrics = global_collector.get_flow_metrics()
        assert metrics["total_flows"] > 0
        
        print("✅ Global metrics collector working")
        
    except Exception as e:
        print(f"❌ Global collector test failed: {e}")
        return False
    
    # Test 8: Metrics summary display
    print("\n8️⃣ Testing metrics summary display...")
    try:
        # Display summary
        collector.print_summary()
        
        # Display dashboard
        dashboard_data = show_metrics_dashboard()
        
        assert "flow_metrics" in dashboard_data
        assert "kb_metrics" in dashboard_data
        assert "performance_metrics" in dashboard_data
        
        print("✅ Metrics display working")
        
    except Exception as e:
        print(f"❌ Summary display test failed: {e}")
        return False
    
    # Test 9: MetricsEnabledFlow integration
    print("\n9️⃣ Testing MetricsEnabledFlow integration...")
    try:
        # Create a simple test flow
        class TestFlow:
            def __init__(self):
                self.flow_id = "test_metrics_flow"
                
            def run(self, inputs):
                time.sleep(0.1)
                return {"result": "success"}
        
        # Add metrics to the flow
        MetricsTestFlow = with_metrics(TestFlow)
        
        # Run flow
        flow = MetricsTestFlow()
        result = flow.run({"test": True})
        
        assert result["result"] == "success"
        
        # Check metrics were recorded
        metrics = flow.metrics_collector.get_flow_metrics()
        assert metrics["total_flows"] > 0
        
        print("✅ MetricsEnabledFlow integration working")
        print("✅ Automatic metrics tracking for flows")
        
    except Exception as e:
        print(f"❌ Flow integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All Essential Local Metrics tests passed!")
    print("✅ Task 12.1 implementation is complete")
    print("\nKey achievements:")
    print("- Flow execution tracking with stages")
    print("- KB usage statistics and cache hit rates")
    print("- Performance metrics by operation")
    print("- Error tracking and reporting")
    print("- Decorator-based integration")
    print("- Metrics persistence across sessions")
    print("- Global metrics collector")
    print("- Human-readable dashboards")
    print("- Flow class integration")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_local_metrics()
    exit(0 if success else 1)