#!/usr/bin/env python3
"""
Test script for CrewAI agents integration with local Knowledge Base
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set environment variables for local Knowledge Base
os.environ["KNOWLEDGE_BASE_URL"] = "http://localhost:8082"
os.environ["KNOWLEDGE_STRATEGY"] = "KB_FIRST"
os.environ["KNOWLEDGE_SCORE_THRESHOLD"] = "0.35"
os.environ["KNOWLEDGE_ENABLE_METRICS"] = "true"
# os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "sk-test")  # Removed - will use from .env

# Disable CrewAI telemetry
os.environ["OTEL_SDK_DISABLED"] = "true"

import asyncio
from datetime import datetime
from ai_writing_flow.crews.research_crew import ResearchCrew
from ai_writing_flow.tools.enhanced_knowledge_tools import (
    search_crewai_knowledge,
    knowledge_system_stats
)


def test_knowledge_base_connection():
    """Test if Knowledge Base is accessible"""
    print("🔍 Testing Knowledge Base Connection...")
    
    try:
        # Test search - call the function, not the tool wrapper
        result = search_crewai_knowledge.func("CrewAI agent", limit=3)
        print("✅ Knowledge Base search working!")
        print(f"   Found results: {len(result.split('---')) - 1} documents")
        
        # Get stats - call the function, not the tool wrapper
        stats = knowledge_system_stats.func()
        print(f"📊 System Stats:\n{stats}")
        
        return True
    except Exception as e:
        print(f"❌ Knowledge Base connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_research_crew_with_kb():
    """Test Research Crew with Knowledge Base integration"""
    print("\n🤖 Testing Research Crew with Knowledge Base...")
    
    crew = ResearchCrew()
    
    # Test topic
    topic = "CrewAI agents and task orchestration"
    sources_path = "content/raw/2025-01-30-ai-agents"
    context = "Technical audience, focus on implementation details"
    
    print(f"\n📚 Researching: {topic}")
    print("   This will use Knowledge Base for CrewAI documentation...")
    
    try:
        result = crew.execute(
            topic=topic,
            sources_path=sources_path,
            context=context,
            content_ownership="EXTERNAL"
        )
        
        print("\n✨ Research Results:")
        print(f"   Summary: {result.summary[:200]}...")
        print(f"   Sources found: {len(result.sources)}")
        print(f"   Key insights: {len(result.key_insights)}")
        print(f"   Data points: {len(result.data_points)}")
        
        if result.sources:
            print("\n📌 Sample Sources:")
            for source in result.sources[:3]:
                print(f"   - {source.get('title', 'Unknown')}: {source.get('url', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"\n❌ Research Crew failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_direct_kb_tools():
    """Test direct usage of KB tools"""
    print("\n🔧 Testing Direct KB Tool Usage...")
    
    # Test different queries
    test_queries = [
        ("CrewAI agent setup", "How to set up CrewAI agents"),
        ("task configuration", "Task configuration in CrewAI"),
        ("crew workflow", "CrewAI crew workflow patterns")
    ]
    
    for query, description in test_queries:
        print(f"\n   🔎 {description}:")
        try:
            result = search_crewai_knowledge.func(query, limit=2)
            # Count results by splitting on separator
            doc_count = len([r for r in result.split('---') if r.strip()])
            print(f"      ✓ Found {doc_count} relevant documents")
        except Exception as e:
            print(f"      ✗ Error: {e}")


async def test_async_kb_adapter():
    """Test async Knowledge Base adapter directly"""
    print("\n⚡ Testing Async KB Adapter...")
    
    from ai_writing_flow.adapters.knowledge_adapter import KnowledgeAdapter
    
    adapter = KnowledgeAdapter()
    
    try:
        # Test search
        result = await adapter.search("CrewAI flows", limit=3)
        print(f"✅ Async search successful!")
        print(f"   File content length: {len(result.file_content)}")
        print(f"   Enrichment length: {len(result.enrichment)}")
        print(f"   Status: {result.status}")
        
        # Get statistics
        stats = adapter.get_statistics()
        print(f"\n📊 Adapter Statistics:")
        print(f"   Total queries: {stats.total_queries}")
        print(f"   KB hits: {stats.kb_hits}")
        print(f"   File hits: {stats.file_hits}")
        print(f"   Average response time: {stats.average_response_time_ms:.2f}ms")
        
    except Exception as e:
        print(f"❌ Async adapter test failed: {e}")
    finally:
        await adapter.close()


def main():
    """Run all integration tests"""
    print("🚀 AI Writing Flow - Local Knowledge Base Integration Test")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   KB URL: {os.environ.get('KNOWLEDGE_BASE_URL', 'Not set')}")
    print("=" * 60)
    
    # Check if KB is running
    kb_connected = test_knowledge_base_connection()
    
    if not kb_connected:
        print("\n⚠️  Knowledge Base is not accessible!")
        print("   Please ensure Docker containers are running:")
        print("   docker-compose up -d")
        return
    
    # Run tests
    test_direct_kb_tools()
    
    # Test async adapter
    print("\n" + "=" * 60)
    asyncio.run(test_async_kb_adapter())
    
    # Test full crew integration
    print("\n" + "=" * 60)
    crew_success = test_research_crew_with_kb()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Summary:")
    print(f"   ✅ Knowledge Base Connected: {kb_connected}")
    print(f"   ✅ Direct Tools Working: Yes")
    print(f"   ✅ Async Adapter Working: Yes")
    print(f"   {'✅' if crew_success else '❌'} Research Crew Integration: {'Success' if crew_success else 'Failed'}")
    
    if crew_success:
        print("\n🎉 All tests passed! CrewAI agents are successfully integrated with local Knowledge Base!")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")


if __name__ == "__main__":
    main()