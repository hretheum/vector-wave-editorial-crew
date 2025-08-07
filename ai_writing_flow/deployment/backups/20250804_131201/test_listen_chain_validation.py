"""
Test method chaining validation - Task 15.3

This test validates that the LinearExecutionChain properly chains methods
without circular dependencies and with proper state-based routing.
"""

import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone

# Add src to path
sys.path.append('src')

def test_chain_configuration_validation():
    """Test Task 15.3: Method chaining validation"""
    
    print("\n--- Task 15.3: Method Chaining Validation ---")
    
    from ai_writing_flow.listen_chain import LinearExecutionChain
    from ai_writing_flow.flow_inputs import FlowPathConfig
    from ai_writing_flow.managers.stage_manager import StageManager
    from ai_writing_flow.utils.circuit_breaker import StageCircuitBreaker
    from ai_writing_flow.models.flow_control_state import FlowControlState
    
    # Mock dependencies
    flow_state = FlowControlState()
    stage_manager = Mock()
    circuit_breaker = Mock()
    config = FlowPathConfig()
    
    # Create execution chain
    chain = LinearExecutionChain(stage_manager, circuit_breaker, config)
    
    # Test 1: Validate chain configuration
    validation_result = chain.validate_chain_configuration()
    assert validation_result["valid"] == True
    assert validation_result["total_steps"] == 7  # Expected number of steps
    assert validation_result["chain_length_ok"] == True
    print("✅ Chain configuration validation passed")
    
    # Test 2: Test next method routing logic
    next_method = chain.get_next_method("validate_inputs", success=True)
    assert next_method == "conduct_research"
    print("✅ Next method routing for validate_inputs works")
    
    next_method = chain.get_next_method("conduct_research", success=True) 
    assert next_method == "align_audience"
    print("✅ Next method routing for conduct_research works")
    
    next_method = chain.get_next_method("align_audience", success=True)
    assert next_method == "generate_draft"
    print("✅ Next method routing for align_audience works")
    
    next_method = chain.get_next_method("generate_draft", success=True)
    assert next_method == "validate_style"
    print("✅ Next method routing for generate_draft works")
    
    next_method = chain.get_next_method("validate_style", success=True)
    assert next_method == "assess_quality"
    print("✅ Next method routing for validate_style works")
    
    next_method = chain.get_next_method("assess_quality", success=True)
    assert next_method == "finalize"
    print("✅ Next method routing for assess_quality works")
    
    next_method = chain.get_next_method("finalize", success=True)
    assert next_method is None  # End of chain
    print("✅ Next method routing for finalize works (end of chain)")
    
    # Test 3: Test failure routing
    next_method = chain.get_next_method("conduct_research", success=False)
    assert next_method == "align_audience"  # Should continue to next step
    print("✅ Failure routing continues to next step")
    
    # Test 4: Test invalid method handling
    next_method = chain.get_next_method("invalid_method", success=True)
    assert next_method is None
    print("✅ Invalid method handling works")
    
    return True


def test_execution_status_tracking():
    """Test execution status tracking and monitoring"""
    
    print("\n--- Execution Status Tracking ---")
    
    from ai_writing_flow.listen_chain import LinearExecutionChain, ChainExecutionResult
    from ai_writing_flow.flow_inputs import FlowPathConfig
    from ai_writing_flow.models.flow_control_state import FlowControlState
    
    # Mock dependencies
    flow_state = FlowControlState()
    stage_manager = Mock()
    circuit_breaker = Mock()
    config = FlowPathConfig()
    
    # Create execution chain
    chain = LinearExecutionChain(stage_manager, circuit_breaker, config)
    
    # Test 1: Initial status
    status = chain.get_execution_status()
    assert status["total_steps"] == 7
    assert status["completed_steps"] == 0
    assert status["failed_steps"] == 0
    assert status["progress_percentage"] == 0.0
    print("✅ Initial execution status correct")
    
    # Test 2: Simulate execution logging
    mock_writing_state = Mock()
    mock_writing_state.current_stage = "initialized"
    
    chain._log_execution_step("validate_inputs", "SUCCESS", mock_writing_state)
    chain._log_execution_step("conduct_research", "SKIPPED", mock_writing_state)
    chain._log_execution_step("align_audience", "SUCCESS", mock_writing_state)
    
    status = chain.get_execution_status()
    assert status["completed_steps"] == 3  # SUCCESS + SKIPPED count as completed
    assert status["failed_steps"] == 0
    assert status["progress_percentage"] > 0.0
    print("✅ Execution logging and status tracking works")
    
    # Test 3: Test failure tracking
    chain._log_execution_step("generate_draft", "FAILED", mock_writing_state)
    
    status = chain.get_execution_status()
    assert status["failed_steps"] == 1
    print("✅ Failure tracking works")
    
    # Test 4: Check execution history
    assert len(status["execution_history"]) == 4
    assert status["execution_history"][0]["method"] == "validate_inputs"
    assert status["execution_history"][0]["status"] == "SUCCESS"
    print("✅ Execution history tracking works")
    
    return True


def test_conditional_routing_logic():
    """Test conditional routing based on state and configuration"""
    
    print("\n--- Conditional Routing Logic ---")
    
    from ai_writing_flow.listen_chain import LinearExecutionChain  
    from ai_writing_flow.flow_inputs import FlowPathConfig
    from ai_writing_flow.models.flow_control_state import FlowControlState
    
    # Test 1: Research skip condition 
    config = FlowPathConfig(skip_research=True)
    flow_state = FlowControlState()
    stage_manager = Mock()
    circuit_breaker = Mock()
    
    chain = LinearExecutionChain(stage_manager, circuit_breaker, config)
    
    # Get research step condition
    research_step = None
    for step in chain._execution_chain:
        if step["method"] == "conduct_research":
            research_step = step
            break
    
    assert research_step is not None
    
    # Test with ORIGINAL content (should skip research)
    mock_state = Mock()
    mock_state.content_ownership = "ORIGINAL"
    
    should_execute = research_step["condition"](mock_state)
    assert should_execute == False  # Should skip due to config.skip_research=True
    print("✅ Research skip condition works with configuration")
    
    # Test 2: Style validation skip condition
    config2 = FlowPathConfig(skip_style_validation=True)
    chain2 = LinearExecutionChain(stage_manager, circuit_breaker, config2)
    
    style_step = None
    for step in chain2._execution_chain:
        if step["method"] == "validate_style":
            style_step = step
            break
    
    should_execute = style_step["condition"](mock_state)
    assert should_execute == False  # Should skip due to config.skip_style_validation=True
    print("✅ Style validation skip condition works")
    
    # Test 3: Always execute conditions
    for step in chain._execution_chain:
        if step["method"] in ["validate_inputs", "generate_draft", "finalize"]:
            should_execute = step["condition"](mock_state)
            assert should_execute == True
            print(f"✅ {step['method']} always executes")
    
    return True


def test_chain_result_conversion():
    """Test ChainExecutionResult conversion and standardization"""
    
    print("\n--- Chain Result Conversion ---")
    
    from ai_writing_flow.listen_chain import LinearExecutionChain, ChainExecutionResult
    from ai_writing_flow.flow_inputs import FlowPathConfig
    from ai_writing_flow.models.flow_control_state import FlowControlState
    
    # Mock dependencies
    flow_state = FlowControlState()
    stage_manager = Mock()
    circuit_breaker = Mock()
    config = FlowPathConfig()
    
    chain = LinearExecutionChain(stage_manager, circuit_breaker, config)
    
    # Test 1: Convert boolean result
    step_config = {"next_on_success": "next_method", "next_on_skip": "skip_method"}
    
    result = chain._convert_to_chain_result(True, step_config)
    assert result.success == True
    assert result.next_method == "next_method"
    print("✅ Boolean True conversion works")
    
    result = chain._convert_to_chain_result(False, step_config)
    assert result.success == False
    assert result.next_method == "skip_method"
    print("✅ Boolean False conversion works")
    
    # Test 2: Convert object with success attribute
    mock_result = Mock()
    mock_result.success = True
    mock_result.completion_time = datetime.now(timezone.utc)
    mock_result.data = "test data"
    
    result = chain._convert_to_chain_result(mock_result, step_config)
    assert result.success == True
    assert result.next_method == "next_method"
    print("✅ Object with success attribute conversion works")
    
    # Test 3: Convert object with completion_time (assume success)
    mock_result2 = Mock()
    mock_result2.completion_time = datetime.now(timezone.utc)
    del mock_result2.success  # Remove success attribute
    
    result = chain._convert_to_chain_result(mock_result2, step_config)
    assert result.success == True
    assert result.next_method == "next_method"
    print("✅ Object with completion_time conversion works")
    
    # Test 4: Convert None (failure)
    result = chain._convert_to_chain_result(None, step_config)
    assert result.success == False
    assert result.next_method == "skip_method" 
    print("✅ None conversion works")
    
    return True


def test_continue_after_failure_logic():
    """Test should_continue_after_failure decision logic"""
    
    print("\n--- Continue After Failure Logic ---")
    
    from ai_writing_flow.listen_chain import LinearExecutionChain, ChainExecutionResult
    from ai_writing_flow.flow_inputs import FlowPathConfig
    from ai_writing_flow.models.flow_control_state import FlowControlState
    
    # Mock dependencies
    flow_state = FlowControlState()
    stage_manager = Mock()
    circuit_breaker = Mock()
    config = FlowPathConfig()
    
    chain = LinearExecutionChain(stage_manager, circuit_breaker, config)
    
    # Test 1: Critical step failure (should not continue)
    step_config = {"method": "validate_inputs"}
    result = ChainExecutionResult()
    result.fallback_used = False
    
    should_continue = chain._should_continue_after_failure(step_config, result)
    assert should_continue == False  # Critical step
    print("✅ Critical step failure stops chain")
    
    step_config = {"method": "finalize"}
    should_continue = chain._should_continue_after_failure(step_config, result)
    assert should_continue == False  # Critical step
    print("✅ Finalize step failure stops chain")
    
    # Test 2: Optional step failure (should continue)
    step_config = {"method": "conduct_research"}
    should_continue = chain._should_continue_after_failure(step_config, result)
    assert should_continue == True  # Optional step
    print("✅ Optional step failure continues chain")
    
    step_config = {"method": "validate_style"}
    should_continue = chain._should_continue_after_failure(step_config, result)
    assert should_continue == True  # Optional step
    print("✅ Style validation failure continues chain")
    
    # Test 3: Fallback used (should continue)
    step_config = {"method": "generate_draft"}
    result.fallback_used = True
    
    should_continue = chain._should_continue_after_failure(step_config, result)
    assert should_continue == True  # Fallback used
    print("✅ Fallback used allows continuation")
    
    # Test 4: Non-critical step with no fallback (should continue with warning)
    step_config = {"method": "align_audience"}
    result.fallback_used = False
    
    should_continue = chain._should_continue_after_failure(step_config, result)
    assert should_continue == True  # Non-critical, default continue
    print("✅ Non-critical step failure continues with warning")
    
    return True


def run_all_chain_validation_tests():
    """Run all method chaining validation tests"""
    
    print("🚀 STARTING METHOD CHAINING VALIDATION TESTS - Task 15.3")
    print("=" * 80)
    
    tests = [
        ("Chain Configuration Validation", test_chain_configuration_validation),
        ("Execution Status Tracking", test_execution_status_tracking),
        ("Conditional Routing Logic", test_conditional_routing_logic),
        ("Chain Result Conversion", test_chain_result_conversion),
        ("Continue After Failure Logic", test_continue_after_failure_logic)
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
    print("📊 METHOD CHAINING VALIDATION RESULTS - Task 15.3")
    print("=" * 80)
    print(f"PASSED: {passed}/{total} ({(passed/total)*100:.1f}%)") 
    
    if passed == total:
        print("\n🎉 ALL METHOD CHAINING VALIDATION TESTS PASSED!")
        print("✅ Chain configuration validation working")
        print("✅ Method routing logic functional")
        print("✅ Conditional execution implemented")
        print("✅ Status tracking operational")
        print("✅ Result conversion standardized")
        print("✅ Failure handling logic correct")
        print("✅ State-based routing validated")
        print("\n🚀 TASK 15.3 COMPLETED - METHOD CHAINING VALIDATION READY!")
        return True
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_chain_validation_tests()
    sys.exit(0 if success else 1)