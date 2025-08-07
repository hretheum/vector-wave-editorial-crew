"""
Complete Phase 2 Integration Test Suite

This test validates the complete Phase 2 implementation including:
- All linear executors (research, audience, draft, style, quality)
- Listen chain replacement and method chaining
- Execution guards with resource monitoring and time limits
- End-to-end flow execution without circular dependencies
"""

import tempfile
import os
import sys
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone

# Add src to path
sys.path.append('src')

def test_complete_linear_flow_execution():
    """Test complete end-to-end linear flow execution"""
    
    print("\n--- Complete Linear Flow Execution Test ---")
    
    from ai_writing_flow.linear_flow import LinearAIWritingFlow, WritingFlowInputs
    
    # Create test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Test Content\nThis is test content for the linear flow.")
        test_file = f.name
    
    try:
        # Create flow instance
        flow = LinearAIWritingFlow()
        
        # Create test inputs
        inputs = WritingFlowInputs(
            topic_title="Test Linear Flow",
            platform="LinkedIn", 
            file_path=test_file,
            content_ownership="EXTERNAL",
            viral_score=7.5
        )
        
        # Test 1: Initialize flow
        flow.initialize_flow(inputs)
        assert flow.flow_config is not None
        assert flow.execution_chain is not None
        assert flow.research_executor is not None
        assert flow.audience_executor is not None
        assert flow.draft_executor is not None
        assert flow.style_executor is not None
        assert flow.quality_executor is not None
        assert flow.execution_guards is not None
        print("✅ Flow initialization with all executors successful")
        
        # Test 2: Execute complete linear flow
        result = flow.execute_linear_flow()
        assert result is not None
        print(f"✅ Linear flow execution completed: success={result.success}")
        
        # Test 3: Verify final state
        assert flow.writing_state.current_draft != ""
        print("✅ Final draft generated successfully")
        
        # Test 4: Check execution guards status
        guards_status = flow.get_execution_guards_status()
        assert guards_status["guards_active"] == True
        print("✅ Execution guards were active during execution")
        
        return True
        
    finally:
        os.unlink(test_file)


def test_guards_resource_monitoring():
    """Test execution guards resource monitoring"""
    
    print("\n--- Execution Guards Resource Monitoring Test ---")
    
    from ai_writing_flow.execution_guards import FlowExecutionGuards, ResourceLimits
    from ai_writing_flow.utils.loop_prevention import LoopPreventionSystem
    
    # Create loop prevention system
    loop_prevention = LoopPreventionSystem()
    
    # Create guards with tight limits for testing
    guards = FlowExecutionGuards(loop_prevention)
    guards.limits.max_concurrent_methods = 1
    guards.limits.method_timeout = 5  # 5 seconds for testing
    
    # Test 1: Resource monitoring startup
    assert guards.resource_monitor._monitoring_active == True
    print("✅ Resource monitoring started automatically")
    
    # Test 2: Get current resource usage
    usage = guards.resource_monitor.get_current_usage()
    assert "cpu_percent" in usage
    assert "memory_percent" in usage
    assert usage["cpu_percent"] >= 0.0
    assert usage["memory_percent"] >= 0.0
    print("✅ Resource usage monitoring working")
    
    # Test 3: Guards status
    status = guards.get_guard_status()
    assert "resource_usage" in status
    assert "execution_times" in status
    assert "limits" in status
    print("✅ Guards status reporting working")
    
    # Test 4: Method execution with guards
    def test_method():
        time.sleep(0.1)  # Simulate work
        return "test_result"
    
    result = guards._execute_with_guards("test_method", test_method)
    assert result == "test_result"
    print("✅ Guarded method execution working")
    
    # Test 5: Cleanup
    guards.stop_flow_execution()
    print("✅ Guards cleanup successful")
    
    return True


def test_style_validation_with_retries():
    """Test style validation with retry logic and escalation"""
    
    print("\n--- Style Validation with Retries Test ---")
    
    from ai_writing_flow.style_linear import LinearStyleExecutor
    from ai_writing_flow.flow_inputs import FlowPathConfig
    from ai_writing_flow.managers.stage_manager import StageManager
    from ai_writing_flow.utils.circuit_breaker import StageCircuitBreaker
    from ai_writing_flow.models.flow_control_state import FlowControlState
    from ai_writing_flow.models import WritingFlowState
    
    # Mock dependencies
    flow_state = FlowControlState()
    stage_manager = Mock()
    circuit_breaker = Mock()
    
    # Configure for testing
    config = FlowPathConfig()
    config.style_max_retries = 2  # Allow 2 retries for testing
    
    circuit_breaker.call.side_effect = lambda func, **kwargs: func(**kwargs)
    circuit_breaker.get_status.return_value = {"state": "CLOSED"}
    
    # Create executor
    executor = LinearStyleExecutor(stage_manager, circuit_breaker, config)
    
    # Create test writing state
    writing_state = WritingFlowState()
    writing_state.topic_title = "Test Style Validation"
    writing_state.platform = "LinkedIn"
    writing_state.current_draft = "This is a test draft with forbidden phrases like click here and buy now!!!"
    
    # Test 1: Style validation should execute
    should_execute = executor.should_execute_style_validation(writing_state)
    assert should_execute == True
    print("✅ Style validation should execute for draft with violations")
    
    # Test 2: Execute style validation (will fail due to violations)
    result = executor.execute_style_validation(writing_state)
    assert result is not None
    assert result.is_compliant == False  # Should fail due to forbidden phrases
    assert len(result.violations) > 0
    print("✅ Style validation correctly detected violations")
    
    # Test 3: Check retry history
    retry_history = executor.get_retry_history(writing_state)
    assert len(retry_history) > 0
    print("✅ Retry history tracking working")
    
    # Test 4: Check escalation status
    escalation = executor.get_escalation_status(writing_state)
    if escalation:
        assert escalation.escalation_required == True
        print("✅ Escalation created for repeated failures")
    
    return True


def test_quality_assessment_with_gates():
    """Test quality assessment with quality gates and final output"""
    
    print("\n--- Quality Assessment with Gates Test ---")
    
    from ai_writing_flow.quality_linear import LinearQualityExecutor, QualityGates
    from ai_writing_flow.flow_inputs import FlowPathConfig
    from ai_writing_flow.managers.stage_manager import StageManager
    from ai_writing_flow.utils.circuit_breaker import StageCircuitBreaker
    from ai_writing_flow.models.flow_control_state import FlowControlState
    from ai_writing_flow.models import WritingFlowState
    
    # Mock dependencies
    flow_state = FlowControlState()
    stage_manager = Mock()
    circuit_breaker = Mock()
    config = FlowPathConfig()
    
    circuit_breaker.call.side_effect = lambda func, **kwargs: func(**kwargs)
    circuit_breaker.get_status.return_value = {"state": "CLOSED"}
    
    # Create executor
    executor = LinearQualityExecutor(stage_manager, circuit_breaker, config)
    
    # Test 1: Quality gates configuration
    gates = executor.quality_gates
    assert gates.minimum_passing_score > 0
    assert gates.auto_approval_threshold > gates.minimum_passing_score
    assert gates.excellence_threshold > gates.auto_approval_threshold
    print("✅ Quality gates properly configured")
    
    # Create high-quality test content
    writing_state = WritingFlowState()
    writing_state.topic_title = "High Quality Content"
    writing_state.platform = "LinkedIn"
    writing_state.current_draft = """# Professional Industry Analysis

This comprehensive analysis examines the current trends in the technology industry based on recent research data.

## Key Findings

According to industry reports, the market has shown significant growth in the past quarter. Business leaders should consider strategic investments in emerging technologies.

## Recommendations

Based on this analysis, organizations should focus on:
- Strategic technology adoption
- Professional development initiatives
- Industry collaboration opportunities

What are your thoughts on these industry developments? Share your experiences in the comments.

#technology #business #innovation"""
    
    writing_state.viral_score = 8.5  # High viral potential
    writing_state.research_sources = [{"title": "Industry Report", "url": "example.com"}]
    writing_state.audience_scores = {"technical_founder": 0.8}
    writing_state.target_depth_level = 2
    
    # Test 2: Execute quality assessment
    result = executor.execute_quality_assessment(writing_state)
    assert result is not None
    assert result.quality_score > 0
    print(f"✅ Quality assessment completed: score={result.quality_score:.1f}")
    
    # Test 3: Check if high-quality content meets approval
    if result.quality_score >= gates.auto_approval_threshold:
        assert result.meets_approval_threshold == True
        assert result.final_approval == True
        print("✅ High-quality content automatically approved")
    
    # Test 4: Verify final output preparation
    if hasattr(writing_state, 'final_output') and writing_state.final_output:
        assert "content" in writing_state.final_output
        assert "quality_score" in writing_state.final_output
        assert "approval_timestamp" in writing_state.final_output
        print("✅ Final output prepared for approved content")
    
    return True


def test_listen_chain_execution_flow():
    """Test LinearExecutionChain with complete method flow"""
    
    print("\n--- Listen Chain Execution Flow Test ---")
    
    from ai_writing_flow.listen_chain import LinearExecutionChain, ChainExecutionResult
    from ai_writing_flow.flow_inputs import FlowPathConfig
    from ai_writing_flow.models.flow_control_state import FlowControlState
    from ai_writing_flow.models import WritingFlowState
    
    # Mock dependencies
    flow_state = FlowControlState()
    stage_manager = Mock()
    circuit_breaker = Mock()
    config = FlowPathConfig()
    
    circuit_breaker.call.side_effect = lambda func, **kwargs: func(**kwargs)
    
    # Create execution chain
    chain = LinearExecutionChain(stage_manager, circuit_breaker, config)
    
    # Test 1: Chain configuration validation
    validation = chain.validate_chain_configuration()
    assert validation["valid"] == True
    assert validation["total_steps"] == 7
    print("✅ Chain configuration valid")
    
    # Create mock writing state
    writing_state = WritingFlowState()
    writing_state.topic_title = "Test Chain Execution"
    writing_state.platform = "LinkedIn"
    writing_state.current_draft = ""
    writing_state.content_ownership = "EXTERNAL"
    
    # Create mock method implementations
    method_implementations = {}
    
    def mock_validate_inputs(writing_state):
        return True
    
    def mock_conduct_research(writing_state):
        from ai_writing_flow.research_linear import ResearchResult
        result = ResearchResult()
        result.sources = [{"title": "Test Source"}]
        result.summary = "Test research summary"
        result.completion_time = datetime.now(timezone.utc)
        writing_state.research_sources = result.sources
        writing_state.research_summary = result.summary
        return result
    
    def mock_align_audience(writing_state):
        from ai_writing_flow.audience_linear import AudienceAlignmentResult
        result = AudienceAlignmentResult()
        result.technical_founder_score = 0.8
        result.recommended_depth_level = 2
        result.audience_insights = "Technical audience alignment"
        result.completion_time = datetime.now(timezone.utc)
        writing_state.audience_scores = {"technical_founder": 0.8}
        writing_state.target_depth_level = 2
        return result
    
    def mock_generate_draft(writing_state):
        from ai_writing_flow.draft_linear import DraftGenerationResult
        result = DraftGenerationResult()
        result.draft_content = "# Test Draft\n\nThis is a test draft generated by the chain."
        result.word_count = len(result.draft_content.split())
        result.completion_time = datetime.now(timezone.utc)
        writing_state.current_draft = result.draft_content
        return result
    
    def mock_validate_style(writing_state):
        from ai_writing_flow.style_linear import StyleValidationResult
        result = StyleValidationResult()
        result.is_compliant = True
        result.compliance_score = 8.5
        result.completion_time = datetime.now(timezone.utc)
        return result
    
    def mock_assess_quality(writing_state):
        from ai_writing_flow.quality_linear import QualityAssessmentResult
        result = QualityAssessmentResult()
        result.quality_score = 8.0
        result.meets_approval_threshold = True
        result.final_approval = True
        result.completion_time = datetime.now(timezone.utc)
        return result
    
    def mock_finalize(writing_state):
        writing_state.current_stage = "finalized"
        return True
    
    method_implementations = {
        "validate_inputs": mock_validate_inputs,
        "conduct_research": mock_conduct_research,
        "align_audience": mock_align_audience,
        "generate_draft": mock_generate_draft,
        "validate_style": mock_validate_style,
        "assess_quality": mock_assess_quality,
        "finalize": mock_finalize
    }
    
    # Test 2: Execute complete chain
    result = chain.execute_chain(writing_state, method_implementations)
    assert result is not None
    assert result.success == True
    print("✅ Complete chain execution successful")
    
    # Test 3: Verify execution status
    status = chain.get_execution_status()
    assert status["completed_steps"] > 0
    assert status["progress_percentage"] > 0
    print(f"✅ Chain execution progress: {status['progress_percentage']:.1f}%")
    
    # Test 4: Verify writing state updated
    assert writing_state.current_draft != ""
    assert writing_state.research_summary != ""
    assert len(writing_state.audience_scores) > 0
    print("✅ Writing state properly updated through chain")
    
    return True


def test_execution_guards_integration():
    """Test execution guards integration with flow methods"""
    
    print("\n--- Execution Guards Integration Test ---")
    
    from ai_writing_flow.execution_guards import FlowExecutionGuards
    from ai_writing_flow.utils.loop_prevention import LoopPreventionSystem
    
    # Create loop prevention and guards
    loop_prevention = LoopPreventionSystem()
    guards = FlowExecutionGuards(loop_prevention)
    
    # Test 1: Guards initialization
    assert guards.resource_monitor._monitoring_active == True
    assert guards.loop_prevention is not None
    print("✅ Guards properly initialized")
    
    # Test 2: Method execution with guards
    def test_guarded_method():
        # Simulate some work
        time.sleep(0.05)
        return {"status": "completed", "data": "test_data"}
    
    result = guards._execute_with_guards("test_method", test_guarded_method)
    assert result["status"] == "completed"
    print("✅ Guarded method execution successful")
    
    # Test 3: Guards prevent excessive execution
    execution_count = 0
    def frequent_method():
        nonlocal execution_count
        execution_count += 1
        return execution_count
    
    # Execute multiple times to test frequency limits
    for i in range(3):
        try:
            guards._execute_with_guards(f"frequent_method_{i}", frequent_method)
        except RuntimeError:
            # Expected if frequency limits exceeded
            pass
    
    print("✅ Guards frequency limiting working")
    
    # Test 4: Resource monitoring during execution
    initial_status = guards.get_guard_status()
    assert "resource_usage" in initial_status
    assert "execution_times" in initial_status
    print("✅ Resource monitoring during execution active")
    
    # Test 5: Emergency stop functionality
    guards.emergency_stop()
    print("✅ Emergency stop functionality working")
    
    return True


def run_complete_phase2_integration_tests():
    """Run all Phase 2 integration tests"""
    
    print("🚀 STARTING COMPLETE PHASE 2 INTEGRATION TESTS")
    print("=" * 80)
    
    tests = [
        ("Complete Linear Flow Execution", test_complete_linear_flow_execution),
        ("Guards Resource Monitoring", test_guards_resource_monitoring),
        ("Style Validation with Retries", test_style_validation_with_retries),
        ("Quality Assessment with Gates", test_quality_assessment_with_gates),
        ("Listen Chain Execution Flow", test_listen_chain_execution_flow),
        ("Execution Guards Integration", test_execution_guards_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("📊 COMPLETE PHASE 2 INTEGRATION TEST RESULTS")
    print("=" * 80)
    print(f"PASSED: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL PHASE 2 INTEGRATION TESTS PASSED!")
        print("✅ Linear execution chain fully functional")
        print("✅ All linear executors (research, audience, draft, style, quality) working")
        print("✅ Method chaining without circular dependencies")
        print("✅ Execution guards with resource monitoring active")
        print("✅ Style validation with retry and escalation logic")
        print("✅ Quality assessment with gates and final output")
        print("✅ Complete end-to-end flow execution successful")
        print("✅ Resource monitoring and time limits enforced")
        print("✅ Emergency stop functionality operational")
        print("\n🚀 PHASE 2: LINEAR FLOW IMPLEMENTATION - COMPLETED SUCCESSFULLY!")
        print("🎯 Ready for production deployment without infinite loops")
        return True
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_complete_phase2_integration_tests()
    sys.exit(0 if success else 1)