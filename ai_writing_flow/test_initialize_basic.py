"""
Basic test for initialize_flow method - Task 11.1 validation
"""

import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
sys.path.append('src')

def test_initialize_basic():
    """Basic validation that initialize_flow method works"""
    
    # Mock all external dependencies
    with patch('ai_writing_flow.linear_flow.WritingCrew') as mock_crew, \
         patch('ai_writing_flow.linear_flow.load_styleguide_context') as mock_styleguide, \
         patch('ai_writing_flow.linear_flow.UIBridge') as mock_ui_bridge:
        
        mock_styleguide.return_value = "Mock styleguide"
        
        from ai_writing_flow.linear_flow import LinearAIWritingFlow, WritingFlowInputs
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Test Content\n\nThis is test content.")
            test_file = f.name
        
        try:
            # Create flow instance
            flow = LinearAIWritingFlow()
            assert flow is not None
            print("✅ LinearAIWritingFlow initialized successfully")
            
            # Create valid inputs
            inputs = WritingFlowInputs(
                topic_title="Test Topic",
                platform="LinkedIn",
                file_path=test_file,
                content_type="STANDALONE",
                content_ownership="EXTERNAL",
                viral_score=7.5,
                skip_research=False
            )
            
            print("✅ WritingFlowInputs created successfully")
            
            # Test initialization
            flow.initialize_flow(inputs)
            print("✅ initialize_flow executed successfully")
            
            # Verify basic state
            assert flow.writing_state.topic_title == "Test Topic"
            assert flow.writing_state.platform == "LinkedIn"
            assert flow.writing_state.file_path == test_file
            assert flow.writing_state.viral_score == 7.5
            assert flow._execution_count == 1
            
            print("✅ Flow state initialized correctly")
            print("✅ Task 11.1 validation successful!")
            
        finally:
            # Cleanup
            os.unlink(test_file)


if __name__ == "__main__":
    test_initialize_basic()
    print("\n🎉 All Task 11.1 tests passed!")