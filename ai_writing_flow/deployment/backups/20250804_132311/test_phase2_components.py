"""
Comprehensive test suite for Phase 2 components - Tasks 11.2, 11.3, 12.1-12.3, 13.1-13.3, 14.1-14.3

Tests all linear flow components without external dependencies.
"""

import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add src to path
sys.path.append('src')

def test_flow_path_configuration():
    """Test Task 11.2: Flow path configuration"""
    
    from ai_writing_flow.flow_inputs import WritingFlowInputs, FlowPathConfig, determine_flow_path, validate_flow_path_configuration
    
    print("\n--- Task 11.2: Flow Path Configuration ---")
    
    # Create test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Test Content")
        test_file = f.name
    
    try:
        # Test 1: ORIGINAL content path
        inputs = WritingFlowInputs(
            topic_title="Original Content",
            platform="LinkedIn",
            file_path=test_file,
            content_ownership="ORIGINAL",
            viral_score=8.5
        )
        
        config = determine_flow_path(inputs)
        assert config.skip_research == True  # ORIGINAL should skip research
        assert config.draft_max_retries == 4  # More drafts for ORIGINAL
        assert config.auto_approve_threshold == 9.0  # High viral score
        print("✅ ORIGINAL content path configuration correct")
        
        # Test 2: EXTERNAL Twitter content  
        inputs = WritingFlowInputs(
            topic_title="Twitter Content",
            platform="Twitter",
            file_path=test_file,
            content_ownership="EXTERNAL",
            viral_score=3.0
        )
        
        config = determine_flow_path(inputs)
        assert config.skip_research == False  # EXTERNAL should include research
        assert config.require_human_approval == False  # Twitter optimization
        assert config.auto_approve_threshold == 6.0  # Low viral score
        print("✅ EXTERNAL Twitter path configuration correct")
        
        # Test 3: Blog series with high viral potential
        inputs = WritingFlowInputs(
            topic_title="Blog Series",
            platform="Blog", 
            file_path=test_file,
            content_type="SERIES",
            viral_score=9.0
        )
        
        config = determine_flow_path(inputs)
        assert config.max_feedback_iterations == 5  # Blog needs more iterations
        assert config.audience_max_retries == 3  # Series needs more audience work
        assert config.auto_approve_threshold == 9.0  # High viral score
        print("✅ Blog series path configuration correct")
        
        # Test 4: Configuration validation
        valid_result = validate_flow_path_configuration(config)
        assert valid_result["valid"] == True
        print("✅ Flow path configuration validation working")
        
        # Test 5: Invalid configuration
        invalid_config = FlowPathConfig(
            max_feedback_iterations=15,  # Too high
            auto_approve_threshold=15.0  # Too high
        )
        
        try:
            validate_flow_path_configuration(invalid_config)
            assert False, "Should have raised ValueError"
        except ValueError:
            print("✅ Invalid configuration correctly rejected")
        
        return True
        
    finally:
        os.unlink(test_file)


def test_early_validation():
    """Test Task 11.3: Early validation with fast failure"""
    
    from ai_writing_flow.flow_inputs import WritingFlowInputs, validate_inputs_early_failure
    
    print("\n--- Task 11.3: Early Validation ---")
    
    # Create test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Test Content")
        test_file = f.name
    
    try:
        # Test 1: Valid inputs pass early validation
        inputs = WritingFlowInputs(
            topic_title="Valid Topic",
            platform="LinkedIn",
            file_path=test_file,
            viral_score=7.5
        )
        
        result = validate_inputs_early_failure(inputs)
        assert result["validation_successful"] == True
        assert result["prerequisites_met"] == True
        assert len(result["critical_errors"]) == 0
        print("✅ Valid inputs pass early validation")
        
        # Test 2: Empty topic title fails fast
        try:
            invalid_inputs = WritingFlowInputs(
                topic_title="",
                platform="LinkedIn", 
                file_path=test_file
            )
            validate_inputs_early_failure(invalid_inputs)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Topic title cannot be empty" in str(e)
            print("✅ Empty topic title fails fast")
        
        # Test 3: Nonexistent file fails fast
        try:
            invalid_inputs = WritingFlowInputs(
                topic_title="Valid Topic",
                platform="LinkedIn",
                file_path="/nonexistent/path.md"
            )
            validate_inputs_early_failure(invalid_inputs)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "does not exist" in str(e)
            print("✅ Nonexistent file fails fast")
        
        # Test 4: Invalid viral score fails fast
        try:
            invalid_inputs = WritingFlowInputs(
                topic_title="Valid Topic",
                platform="LinkedIn",
                file_path=test_file,
                viral_score=15.0  # Invalid
            )
            validate_inputs_early_failure(invalid_inputs)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Viral score must be 0-10" in str(e)
            print("✅ Invalid viral score fails fast")
        
        return True
        
    finally:
        os.unlink(test_file)


def test_linear_research_executor():
    """Test Tasks 12.1-12.3: Linear research execution"""
    
    print("\n--- Tasks 12.1-12.3: Linear Research Execution ---")
    
    # Mock dependencies
    mock_stage_manager = Mock()
    mock_circuit_breaker = Mock()
    mock_config = Mock()
    mock_config.skip_research = False
    
    # Mock stage manager methods
    mock_stage_result = Mock()
    mock_stage_result.status.value = "PENDING"
    mock_stage_manager.get_stage_result.return_value = None
    mock_stage_manager.complete_stage.return_value = None
    
    # Mock circuit breaker
    mock_circuit_breaker.call.side_effect = lambda func, **kwargs: func(**kwargs)
    mock_circuit_breaker.get_status.return_value = {"state": "CLOSED"}
    
    from ai_writing_flow.research_linear import LinearResearchExecutor, ResearchResult
    from ai_writing_flow.models import WritingFlowState
    
    executor = LinearResearchExecutor(mock_stage_manager, mock_circuit_breaker, mock_config)
    
    # Test 1: Should execute research for EXTERNAL content
    writing_state = WritingFlowState(
        topic_title="Test Topic",
        content_ownership="EXTERNAL",
        research_sources=[],
        research_summary="",
        agents_executed=[]
    )
    
    assert executor.should_execute_research(writing_state) == True
    print("✅ EXTERNAL content should execute research")
    
    # Test 2: Should skip research for ORIGINAL content
    writing_state.content_ownership = "ORIGINAL"
    assert executor.should_execute_research(writing_state) == False
    print("✅ ORIGINAL content should skip research")
    
    # Test 3: Execute research successfully
    writing_state.content_ownership = "EXTERNAL"
    result = executor.execute_research(writing_state)
    
    assert isinstance(result, ResearchResult)
    assert len(result.sources) > 0
    assert result.summary != ""
    assert result.completion_time is not None
    print("✅ Research execution produces valid results")
    
    # Test 4: Research completion tracking
    assert executor.should_execute_research(writing_state) == False  # Should be marked complete
    print("✅ Research completion tracking working")
    
    # Test 5: Status reporting
    status = executor.get_research_status(writing_state)
    assert "should_execute" in status
    assert "is_completed" in status
    assert "circuit_breaker_status" in status
    print("✅ Research status reporting working")
    
    return True


def test_linear_audience_executor():
    """Test Tasks 13.1-13.3: Linear audience alignment execution"""
    
    print("\n--- Tasks 13.1-13.3: Linear Audience Alignment ---")
    
    # Mock dependencies
    mock_stage_manager = Mock()
    mock_circuit_breaker = Mock()
    mock_config = Mock()
    mock_config.skip_audience_alignment = False
    
    mock_stage_manager.get_stage_result.return_value = None
    mock_stage_manager.complete_stage.return_value = None
    mock_circuit_breaker.call.side_effect = lambda func, **kwargs: func(**kwargs)
    mock_circuit_breaker.get_status.return_value = {"state": "CLOSED"}
    
    from ai_writing_flow.audience_linear import LinearAudienceExecutor, AudienceAlignmentResult
    from ai_writing_flow.models import WritingFlowState
    
    executor = LinearAudienceExecutor(mock_stage_manager, mock_circuit_breaker, mock_config)
    
    # Test 1: Should execute audience alignment by default
    writing_state = WritingFlowState(
        topic_title="Test Topic",
        platform="LinkedIn",
        viral_score=7.5,
        audience_scores={},
        audience_insights="",
        current_stage="initialized"
    )
    
    assert executor.should_execute_audience_alignment(writing_state) == True
    print("✅ Should execute audience alignment by default")
    
    # Test 2: Execute audience alignment successfully
    result = executor.execute_audience_alignment(writing_state)
    
    assert isinstance(result, AudienceAlignmentResult)
    assert result.technical_founder_score > 0
    assert result.recommended_depth_level > 0
    assert result.audience_insights != ""
    assert result.completion_time is not None
    print("✅ Audience alignment execution produces valid results")
    
    # Test 3: Platform-specific scoring
    writing_state.platform = "Twitter"
    result_twitter = executor.execute_audience_alignment(writing_state)
    
    writing_state.platform = "Blog"
    result_blog = executor.execute_audience_alignment(writing_state)
    
    # Blog should have higher depth level than Twitter
    assert result_blog.recommended_depth_level >= result_twitter.recommended_depth_level
    print("✅ Platform-specific audience scoring working")
    
    # Test 4: Error handling with fallback
    mock_circuit_breaker.call.side_effect = Exception("Test error")
    
    fallback_result = executor.execute_audience_alignment(writing_state)
    assert fallback_result.fallback_used == True
    assert fallback_result.technical_founder_score > 0  # Should have default values
    print("✅ Audience alignment error handling with fallback working")
    
    return True


def test_linear_draft_executor():
    """Test Tasks 14.1-14.3: Linear draft generation execution"""
    
    print("\n--- Tasks 14.1-14.3: Linear Draft Generation ---")
    
    # Mock dependencies
    mock_stage_manager = Mock()
    mock_circuit_breaker = Mock()
    mock_config = Mock()
    mock_config.require_human_approval = True
    mock_config.auto_approve_threshold = 8.0
    
    mock_stage_manager.get_stage_result.return_value = None
    mock_stage_manager.complete_stage.return_value = None
    mock_circuit_breaker.call.side_effect = lambda func, **kwargs: func(**kwargs)
    mock_circuit_breaker.get_status.return_value = {"state": "CLOSED"}
    
    from ai_writing_flow.draft_linear import LinearDraftExecutor, DraftGenerationResult, HumanReviewCheckpoint
    from ai_writing_flow.models import WritingFlowState
    
    executor = LinearDraftExecutor(mock_stage_manager, mock_circuit_breaker, mock_config)
    
    # Test 1: Should execute draft generation when no draft exists
    writing_state = WritingFlowState(
        topic_title="Test Topic",
        platform="LinkedIn",
        current_draft="",
        target_depth_level=2,
        audience_scores={"technical_founder": 0.8},
        research_sources=[{"title": "Test source"}],
        research_summary="Test research summary",
        draft_versions=[],
        agents_executed=[]
    )
    
    assert executor.should_execute_draft_generation(writing_state) == True
    print("✅ Should execute draft generation when no draft exists")
    
    # Test 2: Execute draft generation successfully
    result = executor.execute_draft_generation(writing_state)
    
    assert isinstance(result, DraftGenerationResult)
    assert result.draft_content != ""
    assert result.word_count > 0
    assert result.version_number == 1
    assert result.completion_time is not None
    print("✅ Draft generation execution produces valid results")
    
    # Test 3: Platform-specific draft generation
    platforms = ["Twitter", "LinkedIn", "Blog"]
    for platform in platforms:
        writing_state.platform = platform
        writing_state.current_draft = ""  # Reset
        
        result = executor.execute_draft_generation(writing_state)
        assert result.draft_content != ""
        assert platform.lower() in result.draft_content.lower() or "thread" in result.draft_content.lower() or "#" in result.draft_content
        print(f"✅ {platform} draft generation working")
    
    # Test 4: Human review checkpoint creation
    writing_state.platform = "LinkedIn"
    writing_state.current_draft = ""
    writing_state.viral_score = 8.5
    
    result = executor.execute_draft_generation(writing_state)
    checkpoint = executor.get_review_checkpoint(writing_state)
    
    assert isinstance(checkpoint, HumanReviewCheckpoint)
    assert checkpoint.review_required == True  # High viral score should require review
    assert checkpoint.quality_score > 0
    assert len(checkpoint.review_criteria) > 0
    print("✅ Human review checkpoint creation working")
    
    # Test 5: Draft versioning
    versions = executor.get_draft_versions(writing_state)
    assert len(versions) > 0
    print("✅ Draft versioning working")
    
    # Test 6: Status reporting
    status = executor.get_draft_status(writing_state)
    assert "should_execute" in status
    assert "current_draft_exists" in status
    assert "review_checkpoint" in status
    print("✅ Draft status reporting working")
    
    return True


def run_all_phase2_tests():
    """Run all Phase 2 component tests"""
    
    print("🚀 STARTING PHASE 2 COMPONENT TESTS")
    print("=" * 80)
    
    tests = [
        ("Task 11.2: Flow Path Configuration", test_flow_path_configuration),
        ("Task 11.3: Early Validation", test_early_validation),
        ("Tasks 12.1-12.3: Linear Research", test_linear_research_executor),
        ("Tasks 13.1-13.3: Linear Audience", test_linear_audience_executor),
        ("Tasks 14.1-14.3: Linear Draft", test_linear_draft_executor)
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
    print("📊 PHASE 2 COMPONENT TEST RESULTS")
    print("=" * 80)
    print(f"PASSED: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL PHASE 2 COMPONENT TESTS PASSED!")
        print("✅ Flow path configuration implemented")
        print("✅ Early validation with fast failure working")
        print("✅ Linear research execution ready") 
        print("✅ Linear audience alignment ready")
        print("✅ Linear draft generation ready")
        print("✅ Human review checkpoints integrated")
        print("✅ Draft versioning implemented")
        print("✅ Circuit breaker protection active")
        print("✅ Error handling with fallbacks working")
        print("\n🚀 READY FOR PHASE 2 INTEGRATION AND TESTING!")
        return True
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_phase2_tests()
    sys.exit(0 if success else 1)