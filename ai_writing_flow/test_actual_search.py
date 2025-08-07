#!/usr/bin/env python3
"""
Test actual search with real KB results
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_writing_flow.adapters.knowledge_adapter import get_adapter

async def main():
    print("🔍 Testing Real Search Results")
    print("=" * 40)
    
    adapter = get_adapter()
    
    # Test queries
    queries = [
        "CrewAI agents",
        "task configuration", 
        "crew setup",
        "tools integration"
    ]
    
    for query in queries:
        print(f"\n🔎 Query: '{query}'")
        result = await adapter.search(query, limit=2)
        
        print(f"   Found: {len(result.results)} results")
        print(f"   Strategy: {result.strategy_used.value}")
        print(f"   Response time: {result.response_time_ms:.2f}ms")
        
        # Show first result preview
        if result.results:
            first_result = result.results[0]
            content = first_result.get('content', 'No content available')
            title = first_result.get('title', 'No title')
            score = first_result.get('score', 'No score')
            
            print(f"   Best match: '{title}' (score: {score})")
            print(f"   Preview: {content[:150]}...")
    
    # Stats summary
    stats = adapter.get_statistics()
    print(f"\n📊 Final Statistics:")
    print(f"   Total queries: {stats.total_queries}")
    print(f"   KB availability: {stats.kb_availability:.2%}")
    print(f"   Average response time: {stats.total_response_time_ms / stats.total_queries:.2f}ms")

if __name__ == "__main__":
    asyncio.run(main())