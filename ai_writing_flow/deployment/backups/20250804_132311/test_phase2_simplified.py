"""
Simplified Phase 2 Integration Test - Without CrewAI Dependencies

This test validates the core Phase 2 implementation without external dependencies.
"""

import tempfile
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.append('src')

def test_simplified_linear_executors():
    """Test all linear executors without full flow"""
    
    print("\n--- Simplified Linear Executors Test ---")
    
    from ai_writing_flow.research_linear import LinearResearchExecutor, ResearchResult
    from ai_writing_flow.audience_linear import LinearAudienceExecutor, AudienceAlignmentResult
    from ai_writing_flow.draft_linear import LinearDraftExecutor, DraftGenerationResult
    from ai_writing_flow.style_linear import LinearStyleExecutor, StyleValidationResult
    from ai_writing_flow.quality_linear import LinearQualityExecutor, QualityAssessmentResult
    from ai_writing_flow.flow_inputs import FlowPathConfig
    from ai_writing_flow.models import WritingFlowState, FlowControlState
    from ai_writing_flow.managers.stage_manager import StageManager
    from ai_writing_flow.utils.circuit_breaker import StageCircuitBreaker
    from unittest.mock import Mock
    
    # Setup mocks
    flow_state = FlowControlState()
    stage_manager = StageManager(flow_state)
    circuit_breaker = Mock()
    circuit_breaker.call.side_effect = lambda func, **kwargs: func(**kwargs)
    circuit_breaker.get_status.return_value = {"state": "CLOSED"}
    
    config = FlowPathConfig()
    
    # Test writing state
    writing_state = WritingFlowState()
    writing_state.topic_title = "Test Linear Executors"
    writing_state.platform = "LinkedIn"
    writing_state.content_ownership = "EXTERNAL"
    writing_state.viral_score = 7.5
    
    # Test 1: Research Executor
    research_executor = LinearResearchExecutor(stage_manager, circuit_breaker, config)
    should_execute = research_executor.should_execute_research(writing_state)
    assert should_execute == True
    
    research_result = research_executor.execute_research(writing_state)
    assert isinstance(research_result, ResearchResult)
    assert research_result.completion_time is not None
    print("✅ Research executor working")
    
    # Test 2: Audience Executor
    audience_executor = LinearAudienceExecutor(stage_manager, circuit_breaker, config)
    audience_result = audience_executor.execute_audience_alignment(writing_state)
    assert isinstance(audience_result, AudienceAlignmentResult)
    assert audience_result.technical_founder_score > 0
    print("✅ Audience executor working")
    
    # Test 3: Draft Executor
    draft_executor = LinearDraftExecutor(stage_manager, circuit_breaker, config)
    draft_result = draft_executor.execute_draft_generation(writing_state)
    assert isinstance(draft_result, DraftGenerationResult)
    assert draft_result.draft_content != ""
    assert draft_result.word_count > 0
    writing_state.current_draft = draft_result.draft_content
    print("✅ Draft executor working")
    
    # Test 4: Style Executor
    style_executor = LinearStyleExecutor(stage_manager, circuit_breaker, config)
    style_result = style_executor.execute_style_validation(writing_state)
    assert isinstance(style_result, StyleValidationResult)
    assert style_result.compliance_score > 0
    print("✅ Style executor working")
    
    # Test 5: Quality Executor  
    quality_executor = LinearQualityExecutor(stage_manager, circuit_breaker, config)
    quality_result = quality_executor.execute_quality_assessment(writing_state)
    assert isinstance(quality_result, QualityAssessmentResult)
    assert quality_result.quality_score > 0
    print("✅ Quality executor working")
    
    return True


def test_execution_guards_fixed():
    """Test execution guards with fixed issues"""
    
    print("\n--- Execution Guards Fixed Test ---")
    
    from ai_writing_flow.execution_guards import FlowExecutionGuards
    from ai_writing_flow.utils.loop_prevention import LoopPreventionSystem
    
    # Create components
    loop_prevention = LoopPreventionSystem()
    guards = FlowExecutionGuards(loop_prevention)
    
    # Test 1: Should stop execution method
    should_stop = loop_prevention.should_stop_execution()
    assert should_stop == False  # Should not stop initially
    print("✅ Loop prevention should_stop_execution working")
    
    # Test 2: Force stop method
    loop_prevention.force_stop()
    should_stop = loop_prevention.should_stop_execution()
    assert should_stop == True  # Should stop after force stop
    print("✅ Loop prevention force_stop working")
    
    # Reset for next test
    loop_prevention.reset_system()
    
    # Test 3: Guards execution
    def test_method():
        time.sleep(0.01)
        return "success"
    
    result = guards._execute_with_guards("test_method", test_method)
    assert result == "success"
    print("✅ Guards execution working")
    
    # Test 4: Resource monitoring
    usage = guards.resource_monitor.get_current_usage()
    assert "cpu_percent" in usage
    print("✅ Resource monitoring working")
    
    # Cleanup
    guards.stop_flow_execution()
    
    return True


def test_chain_execution_simplified():
    """Test chain execution with simplified setup"""
    
    print("\n--- Chain Execution Simplified Test ---")
    
    from ai_writing_flow.listen_chain import LinearExecutionChain
    from ai_writing_flow.flow_inputs import FlowPathConfig
    from ai_writing_flow.models import FlowControlState, WritingFlowState
    from unittest.mock import Mock
    
    # Setup
    flow_state = FlowControlState()
    stage_manager = Mock()
    circuit_breaker = Mock()
    circuit_breaker.call.side_effect = lambda func, **kwargs: func(**kwargs)
    
    config = FlowPathConfig()
    chain = LinearExecutionChain(stage_manager, circuit_breaker, config)
    
    # Test chain validation
    validation = chain.validate_chain_configuration()
    assert validation["valid"] == True
    print("✅ Chain configuration valid")
    
    # Test method routing
    next_method = chain.get_next_method("validate_inputs", success=True)
    assert next_method == "conduct_research"
    print("✅ Method routing working")
    
    # Test execution status
    status = chain.get_execution_status()
    assert "total_steps" in status
    assert status["total_steps"] == 7
    print("✅ Execution status tracking working")
    
    return True


def test_flow_path_configuration():
    """Test flow path configuration logic"""
    
    print("\n--- Flow Path Configuration Test ---")
    
    from ai_writing_flow.flow_inputs import WritingFlowInputs, determine_flow_path, validate_flow_path_configuration
    
    # Create test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Test Content")
        test_file = f.name
    
    try:
        # Test 1: ORIGINAL content configuration
        inputs = WritingFlowInputs(
            topic_title="Original Test",
            platform="LinkedIn",
            file_path=test_file,
            content_ownership="ORIGINAL",
            viral_score=8.0
        )
        
        config = determine_flow_path(inputs)
        assert config.skip_research == True  # ORIGINAL should skip research
        print("✅ ORIGINAL content path configuration")
        
        # Test 2: EXTERNAL content configuration
        inputs.content_ownership = "EXTERNAL"
        config = determine_flow_path(inputs)
        assert config.skip_research == False  # EXTERNAL should include research
        print("✅ EXTERNAL content path configuration")
        
        # Test 3: Platform-specific configuration (create new inputs for Twitter)
        twitter_inputs = WritingFlowInputs(
            topic_title="Twitter Test",
            platform="Twitter",
            file_path=test_file,
            content_ownership="EXTERNAL",
            viral_score=8.0
        )
        config = determine_flow_path(twitter_inputs)
        print(f"Twitter config: require_human_approval={config.require_human_approval}")
        assert config.require_human_approval == False  # Twitter optimization
        print("✅ Platform-specific configuration")
        
        # Test 4: Configuration validation
        validation = validate_flow_path_configuration(config)
        assert validation["valid"] == True
        print("✅ Configuration validation working")
        
        return True
        
    finally:
        os.unlink(test_file)


def test_input_validation():
    """Test input validation logic"""
    
    print("\n--- Input Validation Test ---")
    
    from ai_writing_flow.flow_inputs import WritingFlowInputs, validate_inputs_early_failure
    
    # Create test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Test Content")
        test_file = f.name
    
    try:
        # Test 1: Valid inputs
        inputs = WritingFlowInputs(
            topic_title="Valid Test",
            platform="LinkedIn",
            file_path=test_file,
            viral_score=7.5
        )
        
        result = validate_inputs_early_failure(inputs)
        assert result["validation_successful"] == True
        print("✅ Valid inputs pass validation")
        
        # Test 2: Invalid viral score (Pydantic will catch this during creation)
        try:
            invalid_inputs = WritingFlowInputs(
                topic_title="Valid Test",
                platform="LinkedIn",
                file_path=test_file,
                viral_score=15.0  # Invalid
            )
            assert False, "Should have failed"
        except Exception as e:
            # Pydantic validation error
            assert "less than or equal to 10" in str(e)
            print("✅ Invalid viral score rejected by Pydantic")
        
        # Test 3: Empty title (Pydantic will catch this during creation)
        try:
            invalid_inputs2 = WritingFlowInputs(
                topic_title="",  # Empty
                platform="LinkedIn",
                file_path=test_file,
                viral_score=7.5
            )
            assert False, "Should have failed"
        except Exception as e:
            # Pydantic validation error for min_length
            assert "at least 1 character" in str(e)
            print("✅ Empty title rejected by Pydantic")
        
        return True
        
    finally:
        os.unlink(test_file)


def run_simplified_phase2_tests():
    """Run simplified Phase 2 tests without external dependencies"""
    
    print("🚀 STARTING SIMPLIFIED PHASE 2 TESTS")
    print("=" * 80)
    
    tests = [
        ("Simplified Linear Executors", test_simplified_linear_executors),
        ("Execution Guards Fixed", test_execution_guards_fixed),
        ("Chain Execution Simplified", test_chain_execution_simplified),
        ("Flow Path Configuration", test_flow_path_configuration),
        ("Input Validation", test_input_validation)
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
    print("📊 SIMPLIFIED PHASE 2 TEST RESULTS")
    print("=" * 80)
    print(f"PASSED: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL SIMPLIFIED PHASE 2 TESTS PASSED!")
        print("✅ All linear executors functional")
        print("✅ Execution guards working with fixes")
        print("✅ Chain execution and routing operational")
        print("✅ Flow path configuration logic working")
        print("✅ Input validation with early failure working")
        print("\n🚀 PHASE 2 CORE FUNCTIONALITY VALIDATED!")
        return True
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_simplified_phase2_tests()
    sys.exit(0 if success else 1)