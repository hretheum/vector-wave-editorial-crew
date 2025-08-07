#!/usr/bin/env python3
"""
Test script to verify code structure and imports
Tests what we can without external dependencies
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_file_structure():
    """Test that all files exist in correct structure"""
    print("🧪 Testing file structure...")
    
    base_path = Path(__file__).parent / "src" / "ai_writing_flow"
    
    # Check adapters
    adapters_path = base_path / "adapters"
    assert adapters_path.exists(), "Adapters directory missing"
    assert (adapters_path / "__init__.py").exists(), "Adapters __init__.py missing"
    assert (adapters_path / "knowledge_adapter.py").exists(), "Knowledge adapter missing"
    
    # Check tools
    tools_path = base_path / "tools"
    assert tools_path.exists(), "Tools directory missing"
    assert (tools_path / "enhanced_knowledge_tools.py").exists(), "Enhanced tools missing"
    
    print("✅ File structure OK")
    return True


def test_imports_syntax():
    """Test that Python files have valid syntax"""
    print("🧪 Testing Python syntax...")
    
    files_to_check = [
        "src/ai_writing_flow/adapters/knowledge_adapter.py",
        "src/ai_writing_flow/tools/enhanced_knowledge_tools.py"
    ]
    
    for file_path in files_to_check:
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            
            # Check syntax by compiling
            compile(code, file_path, 'exec')
            print(f"✅ {file_path} syntax OK")
            
        except SyntaxError as e:
            print(f"❌ Syntax error in {file_path}: {e}")
            return False
        except Exception as e:
            print(f"⚠️  Could not check {file_path}: {e}")
    
    return True


def test_class_definitions():
    """Test that key classes are defined correctly"""
    print("🧪 Testing class definitions...")
    
    try:
        # Test adapter file without importing external dependencies
        adapter_file = Path("src/ai_writing_flow/adapters/knowledge_adapter.py")
        with open(adapter_file, 'r') as f:
            content = f.read()
        
        # Check key class definitions exist
        assert "class SearchStrategy" in content, "SearchStrategy enum missing"
        assert "class KnowledgeAdapter" in content, "KnowledgeAdapter class missing"
        assert "class AdapterError" in content, "AdapterError class missing"
        assert "class CircuitBreakerOpen" in content, "CircuitBreakerOpen class missing"
        assert "class KnowledgeResponse" in content, "KnowledgeResponse class missing"
        
        print("✅ Adapter classes defined correctly")
        
        # Test tools file
        tools_file = Path("src/ai_writing_flow/tools/enhanced_knowledge_tools.py")
        with open(tools_file, 'r') as f:
            content = f.read()
        
        # Check key function definitions exist
        assert "@tool" in content, "Tool decorators missing"
        assert "def search_crewai_knowledge" in content, "search_crewai_knowledge missing"
        assert "def get_flow_examples" in content, "get_flow_examples missing"
        assert "def troubleshoot_crewai" in content, "troubleshoot_crewai missing"
        
        print("✅ Tool functions defined correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Class definition test failed: {e}")
        return False


def test_research_crew_updates():
    """Test that research crew was updated correctly"""
    print("🧪 Testing research crew updates...")
    
    try:
        crew_file = Path("src/ai_writing_flow/crews/research_crew.py")
        with open(crew_file, 'r') as f:
            content = f.read()
        
        # Check imports were updated
        assert "from ..tools.enhanced_knowledge_tools import" in content, "Enhanced tools import missing"
        assert "search_crewai_knowledge" in content, "search_crewai_knowledge not imported"
        assert "get_flow_examples" in content, "get_flow_examples not imported"
        assert "troubleshoot_crewai" in content, "troubleshoot_crewai not imported"
        
        print("✅ Research crew updated correctly")
        return True
        
    except Exception as e:
        print(f"❌ Research crew test failed: {e}")
        return False


def test_backward_compatibility():
    """Test that backward compatibility is maintained"""
    print("🧪 Testing backward compatibility...")
    
    try:
        tools_file = Path("src/ai_writing_flow/tools/enhanced_knowledge_tools.py")
        with open(tools_file, 'r') as f:
            content = f.read()
        
        # Check legacy functions are still available
        assert "def search_crewai_docs" in content, "Legacy search_crewai_docs missing"
        assert "def get_crewai_example" in content, "Legacy get_crewai_example missing"
        assert "def list_crewai_topics" in content, "Legacy list_crewai_topics missing"
        
        print("✅ Backward compatibility maintained")
        return True
        
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        return False


def test_configuration():
    """Test configuration setup"""
    print("🧪 Testing configuration...")
    
    try:
        config_file = Path("knowledge_config.py")
        assert config_file.exists(), "Configuration file missing"
        
        with open(config_file, 'r') as f:
            content = f.read()
        
        assert "class KnowledgeConfig" in content, "KnowledgeConfig class missing"
        assert "DEVELOPMENT_ENV" in content, "Development config missing"
        assert "PRODUCTION_ENV" in content, "Production config missing"
        
        print("✅ Configuration setup OK")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def test_documentation():
    """Test that required files exist"""
    print("🧪 Testing documentation...")
    
    required_files = [
        "requirements_enhanced.txt",
        "test_knowledge_integration.py",
        "knowledge_config.py"
    ]
    
    for file_name in required_files:
        file_path = Path(file_name)
        assert file_path.exists(), f"Required file missing: {file_name}"
    
    print("✅ Documentation files OK")
    return True


def main():
    """Run all structure tests"""
    print("🚀 Starting Knowledge Base Integration Structure Tests\n")
    
    tests = [
        test_file_structure,
        test_imports_syntax,
        test_class_definitions,
        test_research_crew_updates,
        test_backward_compatibility,
        test_configuration,
        test_documentation
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = test()
            if result:
                passed += 1
                print(f"✅ {test.__name__} PASSED")
            else:
                failed += 1
                print(f"❌ {test.__name__} FAILED")
        except Exception as e:
            print(f"❌ {test.__name__} failed with exception: {e}")
            failed += 1
        print()
    
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All structure tests passed! Implementation looks good.")
        print("\n📋 Next Steps:")
        print("1. Install dependencies: pip install aiohttp structlog")
        print("2. Run full integration tests")
        print("3. Test with actual Knowledge Base API")
        print("4. Add to CI/CD pipeline")
        return True
    else:
        print("❌ Some tests failed. Please fix issues before proceeding.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)