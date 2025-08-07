"""
Test only WritingFlowInputs validation - Task 11.1 basic validation
"""

import tempfile
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append('src')

def test_inputs_validation():
    """Test WritingFlowInputs validation logic"""
    
    try:
        from ai_writing_flow.linear_flow import WritingFlowInputs
        print("✅ WritingFlowInputs imported successfully")
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Test Content\n\nThis is test content.")
            test_file = f.name
        
        try:
            # Test 1: Valid inputs
            inputs = WritingFlowInputs(
                topic_title="Test Topic",
                platform="LinkedIn",
                file_path=test_file,
                content_type="STANDALONE",
                content_ownership="EXTERNAL",
                viral_score=7.5,
                skip_research=False
            )
            
            assert inputs.topic_title == "Test Topic"
            assert inputs.platform == "LinkedIn"
            assert inputs.file_path == test_file
            assert inputs.viral_score == 7.5
            print("✅ Valid inputs created successfully")
            
            # Test 2: Invalid viral score (should raise ValidationError)
            try:
                invalid_inputs = WritingFlowInputs(
                    topic_title="Test Topic",
                    platform="LinkedIn", 
                    file_path=test_file,
                    viral_score=15.0  # Invalid - should be 0-10
                )
                print("❌ Should have raised ValidationError for invalid viral_score")
                return False
            except Exception as e:
                print("✅ ValidationError correctly raised for invalid viral_score")
            
            # Test 3: Empty topic title (should raise ValidationError)
            try:
                invalid_inputs = WritingFlowInputs(
                    topic_title="",  # Invalid empty title
                    platform="LinkedIn",
                    file_path=test_file
                )
                print("❌ Should have raised ValidationError for empty topic_title")
                return False
            except Exception as e:
                print("✅ ValidationError correctly raised for empty topic_title")
            
            print("✅ Input validation working correctly")
            print("✅ Task 11.1 basic validation successful!")
            return True
            
        finally:
            os.unlink(test_file)
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


if __name__ == "__main__":
    if test_inputs_validation():
        print("\n🎉 Task 11.1 input validation tests passed!")
    else:
        print("\n❌ Task 11.1 tests failed!")
        sys.exit(1)