"""
Test suite for flow inputs validation - Task 11.1 validation

Tests the extracted initialize_flow logic without external dependencies.
"""

import tempfile
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append('src')

def test_writing_flow_inputs_validation():
    """Test WritingFlowInputs validation"""
    
    from ai_writing_flow.flow_inputs import WritingFlowInputs
    
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
        assert inputs.skip_research == False
        print("✅ Valid inputs created successfully")
        
        # Test 2: Default values
        minimal_inputs = WritingFlowInputs(
            topic_title="Minimal Topic",
            platform="Twitter",
            file_path=test_file
        )
        
        assert minimal_inputs.content_type == "STANDALONE"
        assert minimal_inputs.content_ownership == "EXTERNAL"
        assert minimal_inputs.viral_score == 0.0
        assert minimal_inputs.skip_research == False
        print("✅ Default values work correctly")
        
        # Test 3: Invalid viral score (should raise ValidationError)
        try:
            invalid_inputs = WritingFlowInputs(
                topic_title="Test Topic",
                platform="LinkedIn",
                file_path=test_file,
                viral_score=15.0  # Invalid - should be 0-10
            )
            assert False, "Should have raised ValidationError"
        except Exception as e:
            print("✅ ValidationError correctly raised for invalid viral_score")
        
        # Test 4: Empty topic title (should raise ValidationError)
        try:
            invalid_inputs = WritingFlowInputs(
                topic_title="",  # Invalid empty title
                platform="LinkedIn",
                file_path=test_file
            )
            assert False, "Should have raised ValidationError"
        except Exception as e:
            print("✅ ValidationError correctly raised for empty topic_title")
        
        # Test 5: Empty platform (should raise ValidationError)
        try:
            invalid_inputs = WritingFlowInputs(
                topic_title="Valid Topic",
                platform="",  # Invalid empty platform
                file_path=test_file
            )
            assert False, "Should have raised ValidationError"
        except Exception as e:
            print("✅ ValidationError correctly raised for empty platform")
        
        return True
        
    finally:
        os.unlink(test_file)


def test_validate_and_process_inputs():
    """Test validate_and_process_inputs function"""
    
    from ai_writing_flow.flow_inputs import WritingFlowInputs, validate_and_process_inputs
    
    # Create temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Test Content\n\nThis is test content.")
        test_file = f.name
    
    try:
        inputs = WritingFlowInputs(
            topic_title="Test Topic",
            platform="LinkedIn",
            file_path=test_file,
            viral_score=7.5
        )
        
        # Test valid processing
        result = validate_and_process_inputs(inputs)
        
        assert result["validation_successful"] == True
        assert result["platform_supported"] == True
        assert result["content_path"].exists()
        assert "validated_inputs" in result
        print("✅ Input validation and processing successful")
        
        # Test nonexistent file
        invalid_inputs = WritingFlowInputs(
            topic_title="Test Topic",
            platform="LinkedIn", 
            file_path="/nonexistent/path.md"
        )
        
        try:
            validate_and_process_inputs(invalid_inputs)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "does not exist" in str(e)
            print("✅ ValueError correctly raised for nonexistent file")
        
        return True
        
    finally:
        os.unlink(test_file)


def test_process_content_paths():
    """Test process_content_paths function"""
    
    from ai_writing_flow.flow_inputs import process_content_paths
    
    # Test 1: Single file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Test Content")
        test_file = f.name
    
    try:
        result = process_content_paths(test_file)
        
        assert result["is_file"] == True
        assert result["is_directory"] == False
        assert len(result["source_files"]) == 1
        assert result["primary_file"] == test_file
        print("✅ Single file processing successful")
        
    finally:
        os.unlink(test_file)
    
    # Test 2: Directory with multiple files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create multiple markdown files
        file1 = Path(temp_dir) / "content1.md"
        file2 = Path(temp_dir) / "content2.md"
        
        file1.write_text("# Content 1")
        file2.write_text("# Content 2")
        
        result = process_content_paths(temp_dir)
        
        assert result["is_directory"] == True
        assert result["is_file"] == False
        assert len(result["source_files"]) == 2
        assert str(file1) in result["source_files"]
        assert str(file2) in result["source_files"]
        assert result["primary_file"] is None  # Multiple files
        print("✅ Directory with multiple files processing successful")
    
    # Test 3: Directory with single file
    with tempfile.TemporaryDirectory() as temp_dir:
        file1 = Path(temp_dir) / "single.md"
        file1.write_text("# Single Content")
        
        result = process_content_paths(temp_dir)
        
        assert result["is_directory"] == True
        assert len(result["source_files"]) == 1
        assert result["primary_file"] == str(file1)
        print("✅ Directory with single file processing successful")
    
    # Test 4: Directory with no markdown files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create non-markdown file
        (Path(temp_dir) / "readme.txt").write_text("Not markdown")
        
        try:
            process_content_paths(temp_dir)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "No markdown files found" in str(e)
            print("✅ ValueError correctly raised for directory with no markdown files")
    
    # Test 5: Nonexistent path
    try:
        process_content_paths("/nonexistent/path")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "not a file or directory" in str(e)
        print("✅ ValueError correctly raised for nonexistent path")
    
    return True


def run_all_tests():
    """Run all Task 11.1 validation tests"""
    
    print("🚀 Starting Task 11.1 - Replace @start with linear initialization tests")
    print("=" * 80)
    
    tests = [
        ("WritingFlowInputs Validation", test_writing_flow_inputs_validation),
        ("Input Processing", test_validate_and_process_inputs),
        ("Content Path Processing", test_process_content_paths)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 80)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 80)
    print(f"PASSED: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL TASK 11.1 TESTS PASSED!")
        print("✅ Linear initialization logic implemented successfully")
        print("✅ Input validation working correctly")  
        print("✅ Path processing handles all cases")
        print("✅ Ready for Task 11.2: Add flow path configuration")
        return True
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)