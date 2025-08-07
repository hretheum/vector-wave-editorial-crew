#!/usr/bin/env python3
"""
Test script for Knowledge Base Integration
Verifies the implementation works correctly
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_writing_flow.adapters.knowledge_adapter import (
    KnowledgeAdapter,
    SearchStrategy,
    AdapterError,
    CircuitBreakerOpen
)
from ai_writing_flow.tools.enhanced_knowledge_tools import (
    search_crewai_knowledge,
    get_flow_examples,
    troubleshoot_crewai
)


def test_adapter_basic_configuration():
    """Test basic adapter configuration"""
    print("🧪 Testing adapter basic configuration...")
    
    # Test default configuration
    adapter = KnowledgeAdapter()
    assert adapter.strategy == SearchStrategy.HYBRID
    assert adapter.kb_api_url == "http://localhost:8080"
    assert adapter.timeout == 10.0
    print("✅ Default configuration OK")
    
    # Test custom configuration
    adapter = KnowledgeAdapter(
        strategy=SearchStrategy.KB_FIRST,
        kb_api_url="http://custom:9090",
        timeout=30.0
    )
    assert adapter.strategy == SearchStrategy.KB_FIRST
    assert adapter.kb_api_url == "http://custom:9090"
    assert adapter.timeout == 30.0
    print("✅ Custom configuration OK")


def test_adapter_file_search():
    """Test local file search functionality"""
    print("🧪 Testing local file search...")
    
    adapter = KnowledgeAdapter(strategy=SearchStrategy.FILE_FIRST)
    
    # Test file search (should work even without KB)
    result = adapter._search_local_files("agent")
    
    assert isinstance(result, str)
    assert len(result) > 0
    print(f"✅ File search returned {len(result)} characters")


async def test_adapter_fallback_strategy():
    """Test adapter fallback when KB is unavailable"""
    print("🧪 Testing fallback strategy...")
    
    # Use a non-existent KB URL to force fallback
    adapter = KnowledgeAdapter(
        strategy=SearchStrategy.KB_FIRST,
        kb_api_url="http://nonexistent:9999",
        timeout=1.0,
        max_retries=1
    )
    
    try:
        result = await adapter.search("CrewAI agent")
        
        # Should fallback to file search
        assert result.strategy_used == SearchStrategy.FILE_FIRST
        assert not result.kb_available
        assert result.file_content is not None
        print("✅ Fallback strategy works correctly")
        
    finally:
        await adapter.close()


def test_enhanced_tools():
    """Test enhanced knowledge tools"""
    print("🧪 Testing enhanced knowledge tools...")
    
    # Test search tool
    result = search_crewai_knowledge("CrewAI agent setup")
    assert isinstance(result, str)
    assert len(result) > 0
    assert "Knowledge Search Results" in result
    print("✅ search_crewai_knowledge works")
    
    # Test flow examples
    result = get_flow_examples("agent_patterns")
    assert isinstance(result, str)
    assert len(result) > 0
    print("✅ get_flow_examples works")
    
    # Test troubleshooting
    result = troubleshoot_crewai("installation")
    assert isinstance(result, str)
    assert len(result) > 0
    assert "Troubleshooting" in result
    print("✅ troubleshoot_crewai works")


def test_error_handling():
    """Test error handling"""
    print("🧪 Testing error handling...")
    
    # Test invalid pattern type
    result = get_flow_examples("invalid_pattern")
    assert "Unknown pattern type" in result
    print("✅ Invalid pattern handling works")
    
    # Test invalid issue type
    result = troubleshoot_crewai("invalid_issue")
    assert "Unknown issue type" in result
    print("✅ Invalid issue handling works")


def test_backward_compatibility():
    """Test backward compatibility"""
    print("🧪 Testing backward compatibility...")
    
    # Import legacy tools (should work without errors)
    from ai_writing_flow.tools.enhanced_knowledge_tools import (
        search_crewai_docs,
        get_crewai_example,
        list_crewai_topics
    )
    
    # Test legacy search
    result = search_crewai_docs("agent")
    assert isinstance(result, str)
    print("✅ Legacy search_crewai_docs works")
    
    # Test legacy example
    result = get_crewai_example("crew creation")
    assert isinstance(result, str)
    print("✅ Legacy get_crewai_example works")
    
    # Test legacy topics
    result = list_crewai_topics()
    assert isinstance(result, str)
    print("✅ Legacy list_crewai_topics works")


async def run_async_tests():
    """Run async tests"""
    print("🧪 Running async tests...")
    await test_adapter_fallback_strategy()


def main():
    """Run all tests"""
    print("🚀 Starting Knowledge Base Integration Tests\n")
    
    try:
        # Basic tests
        test_adapter_basic_configuration()
        test_adapter_file_search()
        test_enhanced_tools()
        test_error_handling()
        test_backward_compatibility()
        
        # Async tests
        asyncio.run(run_async_tests())
        
        print("\n🎉 All tests passed! Knowledge Base integration is working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)