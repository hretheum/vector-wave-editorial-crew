"""
Test suite for linear flow methods

Tests the new linear flow implementation methods that replace
@start/@router/@listen decorators with linear execution.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.append('src')

from ai_writing_flow.linear_flow import (
    LinearAIWritingFlow, 
    WritingFlowInputs, 
    FlowDecisions,
    LinearFlowStateAdapter
)
from ai_writing_flow.models.flow_stage import FlowStage
from ai_writing_flow.models import WritingFlowState
from pydantic import ValidationError


class TestLinearFlowInitialization:
    """Test initialize_flow() method - Task 11.1"""
    
    def setup_method(self):
        """Setup test environment"""
        self.flow = LinearAIWritingFlow()
    
    def test_initialize_flow_with_valid_inputs(self):
        """Test successful flow initialization with valid inputs"""
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Test Content\n\nThis is test content.")
            test_file = f.name
        
        try:
            inputs = WritingFlowInputs(
                topic_title="Test Topic",
                platform="LinkedIn",
                file_path=test_file,
                content_type="STANDALONE",
                content_ownership="EXTERNAL",
                viral_score=7.5,
                skip_research=False
            )
            
            # Test initialization
            self.flow.initialize_flow(inputs)
            
            # Verify writing state was initialized
            assert self.flow.writing_state.topic_title == "Test Topic"
            assert self.flow.writing_state.platform == "LinkedIn"
            assert self.flow.writing_state.file_path == test_file
            assert self.flow.writing_state.viral_score == 7.5
            assert self.flow.writing_state.skip_research == False
            
            # Verify flow control state
            assert self.flow.flow_state.current_stage == FlowStage.INPUT_VALIDATION
            assert "flow_initialized" in self.flow.writing_state.agents_executed
            assert self.flow._execution_count == 1
            
        finally:
            # Cleanup
            os.unlink(test_file)
    
    def test_initialize_flow_with_directory_path(self):
        """Test initialization with directory containing markdown files"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple markdown files
            file1 = Path(temp_dir) / "content1.md"
            file2 = Path(temp_dir) / "content2.md"
            
            file1.write_text("# Content 1\n\nFirst content.")
            file2.write_text("# Content 2\n\nSecond content.")
            
            inputs = WritingFlowInputs(
                topic_title="Multi-file Topic",
                platform="Twitter", 
                file_path=temp_dir,
                content_ownership="ORIGINAL"
            )
            
            self.flow.initialize_flow(inputs)
            
            # Verify source files were detected
            assert len(self.flow.writing_state.source_files) == 2
            assert str(file1) in self.flow.writing_state.source_files
            assert str(file2) in self.flow.writing_state.source_files
    
    def test_initialize_flow_with_single_file_in_directory(self):
        """Test initialization with directory containing single markdown file"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create single markdown file
            file1 = Path(temp_dir) / "single.md"
            file1.write_text("# Single Content\n\nSingle file content.")
            
            inputs = WritingFlowInputs(
                topic_title="Single File Topic",
                platform="Blog",
                file_path=temp_dir
            )
            
            self.flow.initialize_flow(inputs)
            
            # Verify single file was selected as primary
            assert self.flow.writing_state.file_path == str(file1)
            assert len(self.flow.writing_state.source_files) == 1
    
    def test_initialize_flow_input_validation_errors(self):
        """Test input validation error handling"""
        
        # Test empty topic title
        with pytest.raises(ValidationError):
            WritingFlowInputs(
                topic_title="",  # Invalid empty title
                platform="LinkedIn",
                file_path="/valid/path"
            )
        
        # Test invalid viral score
        with pytest.raises(ValidationError):
            WritingFlowInputs(
                topic_title="Valid Topic",
                platform="LinkedIn", 
                file_path="/valid/path",
                viral_score=15.0  # Invalid - should be 0-10
            )
    
    def test_initialize_flow_nonexistent_file_path(self):
        """Test error handling for nonexistent file path"""
        
        inputs = WritingFlowInputs(
            topic_title="Test Topic",
            platform="LinkedIn",
            file_path="/nonexistent/path.md"
        )
        
        with pytest.raises(RuntimeError, match="Flow initialization failed"):
            self.flow.initialize_flow(inputs)
    
    def test_initialize_flow_no_markdown_files_in_directory(self):  
        """Test error handling when directory has no markdown files"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create non-markdown file
            (Path(temp_dir) / "readme.txt").write_text("Not markdown")
            
            inputs = WritingFlowInputs(
                topic_title="Test Topic",
                platform="LinkedIn",
                file_path=temp_dir
            )
            
            with pytest.raises(RuntimeError, match="Flow initialization failed"):
                self.flow.initialize_flow(inputs)
    
    def test_initialize_flow_multiple_executions_prevention(self):
        """Test prevention of multiple flow executions"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Test Content")
            test_file = f.name
        
        try:
            inputs = WritingFlowInputs(
                topic_title="Test Topic",
                platform="LinkedIn",
                file_path=test_file
            )
            
            # First execution should succeed
            self.flow.initialize_flow(inputs)
            assert self.flow._execution_count == 1
            
            # Second execution should succeed but log warning  
            self.flow.initialize_flow(inputs)
            assert self.flow._execution_count == 2
            
            # Third execution should succeed but log warning
            self.flow.initialize_flow(inputs)
            assert self.flow._execution_count == 3
            
            # Fourth execution should fail (infinite loop prevention)
            with pytest.raises(RuntimeError, match="Maximum flow execution limit exceeded"):
                self.flow.initialize_flow(inputs)
                
        finally:
            os.unlink(test_file)
    
    @patch('ai_writing_flow.linear_flow.load_styleguide_context')
    @patch('ai_writing_flow.linear_flow.WritingCrew')
    def test_initialize_flow_integration_with_phase1_components(self, mock_crew, mock_styleguide):
        """Test integration with Phase 1 architecture components"""
        
        mock_styleguide.return_value = "Mock styleguide context"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Test Content")
            test_file = f.name
        
        try:
            flow = LinearAIWritingFlow()
            
            # Verify Phase 1 components were initialized
            assert flow.flow_state is not None
            assert flow.stage_manager is not None
            assert flow.retry_manager is not None
            assert len(flow.circuit_breakers) > 0
            assert FlowStage.INPUT_VALIDATION in flow.circuit_breakers
            
            inputs = WritingFlowInputs(
                topic_title="Integration Test",
                platform="LinkedIn",
                file_path=test_file
            )
            
            flow.initialize_flow(inputs)
            
            # Verify stage execution was tracked
            events = flow.stage_manager.get_execution_events(limit=5)
            assert len(events) > 0
            
            # Verify flow state was updated
            assert flow.flow_state.current_stage == FlowStage.INPUT_VALIDATION
            
        finally:
            os.unlink(test_file)


class TestFlowDecisions:
    """Test pure decision functions extracted from routing logic"""
    
    def test_should_conduct_research_decisions(self):
        """Test research decision logic"""
        
        # EXTERNAL content should conduct research
        state = WritingFlowState(
            content_ownership="EXTERNAL",
            skip_research=False
        )
        assert FlowDecisions.should_conduct_research(state) == True
        
        # ORIGINAL content should skip research
        state = WritingFlowState(
            content_ownership="ORIGINAL",
            skip_research=False
        )
        assert FlowDecisions.should_conduct_research(state) == False
        
        # Skip research flag should skip research
        state = WritingFlowState(
            content_ownership="EXTERNAL",
            skip_research=True
        )
        assert FlowDecisions.should_conduct_research(state) == False
    
    def test_determine_feedback_action_decisions(self):
        """Test human feedback routing decisions"""
        
        # No feedback should go to style validation
        result = FlowDecisions.determine_feedback_action(None, "EXTERNAL")
        assert result == FlowStage.STYLE_VALIDATION
        
        # Minor feedback should go to style validation
        result = FlowDecisions.determine_feedback_action("minor", "EXTERNAL")
        assert result == FlowStage.STYLE_VALIDATION
        
        # Major feedback should go to audience alignment
        result = FlowDecisions.determine_feedback_action("major", "EXTERNAL")
        assert result == FlowStage.AUDIENCE_ALIGN
        
        # Pivot feedback should go to research (EXTERNAL)
        result = FlowDecisions.determine_feedback_action("pivot", "EXTERNAL")
        assert result == FlowStage.RESEARCH
        
        # Pivot feedback should go to audience align (ORIGINAL)
        result = FlowDecisions.determine_feedback_action("pivot", "ORIGINAL")
        assert result == FlowStage.AUDIENCE_ALIGN
    
    def test_should_retry_stage_decisions(self):
        """Test stage retry decision logic"""
        
        # Should retry when under limit
        assert FlowDecisions.should_retry_stage(
            FlowStage.RESEARCH, retry_count=1, max_retries=3
        ) == True
        
        # Should not retry when at limit
        assert FlowDecisions.should_retry_stage(
            FlowStage.RESEARCH, retry_count=3, max_retries=3  
        ) == False
        
        # Should retry draft generation for content quality issues
        assert FlowDecisions.should_retry_stage(
            FlowStage.DRAFT_GENERATION, 
            retry_count=1, 
            max_retries=3,
            error_type="content_quality"
        ) == True
        
        # Should not retry research for unsupported error type
        assert FlowDecisions.should_retry_stage(
            FlowStage.RESEARCH,
            retry_count=1,
            max_retries=3, 
            error_type="unsupported_error"
        ) == False


class TestLinearFlowStateAdapter:
    """Test state adapter for WritingFlowState compatibility"""
    
    def test_state_adapter_initialization(self):
        """Test adapter initialization"""
        
        flow = LinearAIWritingFlow()
        adapter = LinearFlowStateAdapter(flow.flow_state)
        
        assert adapter.flow_state is not None
        assert adapter.writing_state is not None
    
    def test_sync_to_writing_state_stage_mapping(self):
        """Test FlowStage to WritingFlowState stage mapping"""
        
        flow = LinearAIWritingFlow()
        flow.flow_state.current_stage = FlowStage.RESEARCH
        
        adapter = LinearFlowStateAdapter(flow.flow_state)
        writing_state = adapter.sync_to_writing_state()
        
        assert writing_state.current_stage == "research"
    
    def test_sync_to_writing_state_unknown_stage(self):
        """Test handling of unknown stage mapping"""
        
        flow = LinearAIWritingFlow()
        # This shouldn't happen in practice, but test edge case
        flow.flow_state.current_stage = None
        
        adapter = LinearFlowStateAdapter(flow.flow_state)
        writing_state = adapter.sync_to_writing_state()
        
        assert writing_state.current_stage == "unknown"


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v"])