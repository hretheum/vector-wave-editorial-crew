#!/usr/bin/env python3
"""
Final Integration Test for AI Writing Flow with Knowledge Base

Quick test to verify all components work together after configuration.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_writing_flow.adapters.knowledge_adapter import get_adapter
from knowledge_config import KnowledgeConfig

async def main():
    print("🧪 Final Integration Test")
    print("=" * 40)
    
    # Load configuration
    config = KnowledgeConfig()
    print(f"📋 Configuration:")
    print(f"   KB API URL: {config.KB_API_URL}")
    print(f"   Timeout: {config.KB_TIMEOUT}s") 
    print(f"   Strategy: {config.DEFAULT_STRATEGY.value}")
    
    # Test adapter
    print(f"\n🔧 Testing Knowledge Adapter...")
    adapter = get_adapter()
    print(f"   Strategy: {adapter.strategy.value}")
    print(f"   KB URL: {adapter.kb_api_url}")
    
    # Test search
    print(f"\n🔍 Testing search functionality...")
    try:
        result = await adapter.search("CrewAI agents", limit=2)
        print(f"   Results: {len(result.results)} found")
        print(f"   Strategy used: {result.strategy_used.value}")
        print(f"   KB available: {result.kb_available}")
        print(f"   Response time: {result.response_time_ms:.2f}ms")
        
        if result.results:
            print(f"   First result preview: {result.results[0].get('content', 'No content')[:100]}...")
        
        # Test stats
        stats = adapter.get_statistics()
        print(f"\n📊 Adapter Statistics:")
        print(f"   Total queries: {stats.total_queries}")
        print(f"   KB successes: {stats.kb_successes}")
        print(f"   KB errors: {stats.kb_errors}")
        print(f"   File searches: {stats.file_searches}")
        print(f"   KB availability: {stats.kb_availability:.2%}")
        
        print(f"\n✅ Integration test successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)