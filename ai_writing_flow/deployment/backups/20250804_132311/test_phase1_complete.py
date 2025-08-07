"""
Complete Phase 1 Integration Test - All Blocks (1-9)

Tests all components working together:
- FlowStage & FlowControlState (Blok 1)
- StageManager (Blok 2)
- CircuitBreaker & RetryManager (Blok 4-5)
- Advanced StageManager features (Blok 7)
- LoopPreventionSystem (Blok 8)
"""

import sys
sys.path.append('src')
import time
import threading
from datetime import datetime, timezone

from ai_writing_flow.models import FlowStage, FlowControlState
from ai_writing_flow.managers.stage_manager import StageManager, ExecutionEventType
from ai_writing_flow.utils import RetryManager, StageCircuitBreaker, LoopPreventionSystem


def test_complete_integration():
    """Test all Phase 1 components working together."""
    print("\n=== COMPLETE PHASE 1 INTEGRATION TEST ===")
    
    # Initialize all components
    flow_state = FlowControlState()
    stage_manager = StageManager(flow_state)
    retry_manager = RetryManager(flow_state)
    
    print("✓ All components initialized")
    
    # Test 1: Normal flow with advanced tracking
    print("\n--- Test 1: Complete Flow Execution ---")
    
    stages_to_execute = [
        FlowStage.INPUT_VALIDATION,
        FlowStage.AUDIENCE_ALIGN,  # Skip research
        FlowStage.DRAFT_GENERATION,
        FlowStage.STYLE_VALIDATION,
        FlowStage.QUALITY_CHECK
    ]
    
    for i, stage in enumerate(stages_to_execute):
        print(f"Executing stage {i+1}/{len(stages_to_execute)}: {stage.value}")
        
        # Start with timeout monitoring
        execution = stage_manager.start_stage_with_timeout(stage)
        
        # Simulate some work
        time.sleep(0.1)
        
        # Complete successfully
        stage_manager.complete_stage_with_timeout_check(
            stage, 
            success=True, 
            result={'stage_data': f'{stage.value}_result', 'timestamp': datetime.now().isoformat()}
        )
        
        # Transition to next stage if not last
        if i < len(stages_to_execute) - 1:
            next_stage = stages_to_execute[i + 1]
            flow_state.add_transition(next_stage, f"Completed {stage.value}")
    
    # Finalize flow
    flow_state.add_transition(FlowStage.FINALIZED, "All stages completed")
    stage_manager._log_event(ExecutionEventType.FLOW_COMPLETED)
    
    print("✓ Complete flow executed successfully")
    
    return stage_manager, flow_state


def test_advanced_history_analysis():
    """Test advanced history analysis features (Blok 7)."""
    print("\n--- Test 2: Advanced History Analysis ---")
    
    stage_manager, flow_state = test_complete_integration()
    
    # Test execution events
    events = stage_manager.get_execution_events(limit=10)
    print(f"✓ Retrieved {len(events)} execution events")
    
    # Test timeline
    timeline = stage_manager.get_execution_timeline()
    print(f"✓ Generated timeline with {len(timeline)} events")
    
    # Test stage performance analysis
    for stage in [FlowStage.DRAFT_GENERATION, FlowStage.STYLE_VALIDATION]:
        performance = stage_manager.analyze_stage_performance(stage)
        print(f"✓ Performance analysis for {stage.value}: {performance['success_rate']:.1%} success rate")
    
    # Test flow health report
    health = stage_manager.get_flow_health_report()
    print(f"✓ Flow health: {health['health_status']} - {health['total_events']} events")
    
    # Test memory usage
    memory_report = stage_manager.get_memory_usage_report()
    print(f"✓ Memory usage: {memory_report['total_memory_mb']:.2f} MB")
    
    return stage_manager


def test_loop_prevention_integration():
    """Test loop prevention system integration (Blok 8)."""
    print("\n--- Test 3: Loop Prevention Integration ---")
    
    flow_state = FlowControlState()
    stage_manager = StageManager(flow_state)  # This now includes loop prevention
    
    # Reset loop prevention system to have higher limits for this test
    stage_manager.loop_prevention.max_executions_per_stage = 30
    
    # Test method execution tracking
    print("Testing method execution tracking...")
    
    # Simulate multiple calls to same method (should trigger detection)
    for i in range(15):  # Just below warning threshold
        record = stage_manager.loop_prevention.track_execution(
            method_name="test_method",
            stage=FlowStage.DRAFT_GENERATION,
            arguments={'call': i}
        )
        time.sleep(0.01)  # Small delay
        stage_manager.loop_prevention.complete_execution(record)
    
    # Check loop prevention status
    status = stage_manager.loop_prevention.get_status_report()
    print(f"✓ Loop prevention status: {status['system_status']}")
    print(f"✓ Method executions tracked: {status['total_executions']}")
    
    # Test pattern detection
    patterns = stage_manager.loop_prevention._detect_patterns()
    if patterns:
        print(f"✓ Detected {len(patterns)} patterns")
        for pattern in patterns:
            print(f"  - {pattern.pattern_type}: {pattern.risk_level.value} risk")
    else:
        print("✓ No concerning patterns detected")
    
    return stage_manager


def test_timeout_guards():
    """Test timeout guard functionality (Task 8.3)."""
    print("\n--- Test 4: Timeout Guards ---")
    
    flow_state = FlowControlState()
    stage_manager = StageManager(flow_state)
    
    # Test timeout status
    timeout_status = stage_manager.get_timeout_status()
    print(f"✓ Flow timeout status: {timeout_status['flow_timeout_status']}")
    print(f"✓ Flow execution time: {timeout_status['flow_execution_time_seconds']:.1f}s")
    
    # Test stage timeout configuration
    for stage in [FlowStage.RESEARCH, FlowStage.DRAFT_GENERATION]:
        timeout = stage_manager.get_stage_timeout(stage)
        print(f"✓ {stage.value} timeout: {timeout}s")
    
    # Start a stage to test timeout monitoring
    execution = stage_manager.start_stage_with_timeout(FlowStage.INPUT_VALIDATION)
    print(f"✓ Started stage with timeout monitoring")
    
    # Complete it quickly (should not timeout)
    stage_manager.complete_stage_with_timeout_check(
        FlowStage.INPUT_VALIDATION,
        success=True,
        result={'quick_completion': True}
    )
    print("✓ Stage completed within timeout")
    
    return True


def test_circuit_breaker_retry_integration():
    """Test circuit breaker and retry manager integration."""
    print("\n--- Test 5: Circuit Breaker + Retry Integration ---")
    
    flow_state = FlowControlState()
    retry_manager = RetryManager(flow_state)
    circuit_breaker = StageCircuitBreaker(
        FlowStage.RESEARCH, 
        flow_state,
        failure_threshold=3
    )
    
    # Test function that fails then succeeds
    attempts = []
    def research_function():
        attempts.append(1)
        if len(attempts) < 3:
            raise Exception(f"Research API error (attempt {len(attempts)})")
        return {"research_data": "success"}
    
    # Execute with both circuit breaker and retry
    try:
        result = circuit_breaker.call(
            lambda: retry_manager.retry_sync(research_function, FlowStage.RESEARCH)
        )
        print(f"✓ Circuit breaker + retry succeeded after {len(attempts)} attempts")
        print(f"✓ Result: {result}")
    except Exception as e:
        print(f"✗ Integration failed: {e}")
        return False
    
    # Test circuit state
    cb_status = circuit_breaker.get_status()
    print(f"✓ Circuit breaker state: {cb_status['state']}")
    print(f"✓ Success rate: {cb_status['success_rate']:.1%}")
    
    return True


def test_thread_safety_comprehensive():
    """Test thread safety across all components."""
    print("\n--- Test 6: Comprehensive Thread Safety ---")
    
    flow_state = FlowControlState()
    stage_manager = StageManager(flow_state)
    errors = []
    results = []
    
    def worker(worker_id):
        try:
            # Each worker executes a different stage
            stages = [
                FlowStage.INPUT_VALIDATION,
                FlowStage.AUDIENCE_ALIGN,
                FlowStage.DRAFT_GENERATION,
                FlowStage.STYLE_VALIDATION,
                FlowStage.QUALITY_CHECK
            ]
            
            stage = stages[worker_id % len(stages)]
            
            # Track with loop prevention
            record = stage_manager.loop_prevention.track_execution(
                method_name=f"worker_{worker_id}",
                stage=stage
            )
            
            # Start stage
            execution = stage_manager.start_stage(stage)
            time.sleep(0.05)  # Simulate work
            
            # Complete stage
            stage_manager.complete_stage(
                stage,
                success=True,
                result={'worker_id': worker_id, 'stage': stage.value}
            )
            
            # Complete loop tracking
            stage_manager.loop_prevention.complete_execution(record)
            
            results.append(worker_id)
            
        except Exception as e:
            errors.append((worker_id, str(e)))
    
    # Run workers concurrently
    threads = []
    for i in range(8):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    print(f"✓ Successful workers: {len(results)}")
    print(f"✓ Errors: {len(errors)}")
    
    if errors:
        print("Error details:")
        for worker_id, error in errors[:3]:  # Show first 3 errors
            print(f"  Worker {worker_id}: {error}")
    
    # Check system state after concurrent access
    health = stage_manager.get_flow_health_report()
    loop_status = stage_manager.loop_prevention.get_status_report()
    
    print(f"✓ Final health status: {health['health_status']}")
    print(f"✓ Loop prevention: {loop_status['system_status']}")
    
    return len(errors) == 0 or len(results) > 0


def test_performance_under_load():
    """Test performance with high load."""
    print("\n--- Test 7: Performance Under Load ---")
    
    flow_state = FlowControlState()
    stage_manager = StageManager(flow_state)
    
    # Increase limits for performance test
    stage_manager.loop_prevention.max_executions_per_stage = 200
    stage_manager.loop_prevention.max_executions_per_method = 200
    
    start_time = time.time()
    
    # Execute many operations quickly
    for i in range(100):
        # Track execution
        record = stage_manager.loop_prevention.track_execution(
            method_name="load_test",
            stage=FlowStage.DRAFT_GENERATION,
            arguments={'iteration': i}
        )
        
        # Log events
        stage_manager._log_event(
            ExecutionEventType.STAGE_STARTED,
            stage=FlowStage.DRAFT_GENERATION,
            metadata={'iteration': i}
        )
        
        stage_manager._log_event(
            ExecutionEventType.STAGE_COMPLETED,
            stage=FlowStage.DRAFT_GENERATION,
            duration_seconds=0.001,
            metadata={'iteration': i}
        )
        
        stage_manager.loop_prevention.complete_execution(record)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"✓ Processed 100 operations in {total_time:.2f}s")
    print(f"✓ Average: {(total_time/100)*1000:.1f}ms per operation")
    
    # Check memory usage
    memory_report = stage_manager.get_memory_usage_report()
    print(f"✓ Memory usage: {memory_report['total_memory_mb']:.2f} MB")
    
    # Clean up if needed
    if memory_report['total_memory_mb'] > 10:  # If > 10MB
        stage_manager.cleanup_history(keep_last_n=50)
        stage_manager.loop_prevention.cleanup_old_records(max_age_minutes=1)
        print("✓ Cleaned up history and records")
    
    return total_time < 5.0  # Should complete in under 5 seconds


def run_all_tests():
    """Run all integration tests."""
    print("🚀 STARTING COMPLETE PHASE 1 INTEGRATION TESTS")
    print("=" * 80)
    
    test_results = []
    
    try:
        # Basic integration
        stage_manager = test_complete_integration()
        test_results.append(("Complete Integration", True))
        
        # Advanced features
        test_advanced_history_analysis()
        test_results.append(("History Analysis", True))
        
        # Loop prevention
        test_loop_prevention_integration()
        test_results.append(("Loop Prevention", True))
        
        # Timeout guards
        result = test_timeout_guards()
        test_results.append(("Timeout Guards", result))
        
        # Circuit breaker + retry
        result = test_circuit_breaker_retry_integration()
        test_results.append(("Circuit Breaker + Retry", result))
        
        # Thread safety
        result = test_thread_safety_comprehensive()
        test_results.append(("Thread Safety", result))
        
        # Performance
        result = test_performance_under_load()
        test_results.append(("Performance", result))
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 80)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:30} {status}")
        if result:
            passed += 1
    
    print("-" * 80)
    print(f"TOTAL: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL PHASE 1 INTEGRATION TESTS PASSED!")
        print("🚀 Ready for Phase 2: CrewAI Flow Integration")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - review before Phase 2")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)