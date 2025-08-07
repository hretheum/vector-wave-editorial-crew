#!/usr/bin/env python3
"""
Test search with different score thresholds
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_writing_flow.adapters.knowledge_adapter import get_adapter

async def main():
    print("🔍 Testing Search with Different Thresholds")
    print("=" * 50)
    
    adapter = get_adapter()
    
    query = "CrewAI agents"
    thresholds = [0.3, 0.5, 0.7, 0.9]
    
    for threshold in thresholds:
        print(f"\n🎯 Query: '{query}' with threshold {threshold}")
        result = await adapter.search(query, limit=3, score_threshold=threshold)
        
        print(f"   Found: {len(result.results)} results")
        
        for i, res in enumerate(result.results[:2]):  # Show top 2
            title = res.get('title', 'No title')
            score = res.get('score', 0)
            content = res.get('content', '')[:100]
            print(f"   {i+1}. {title} (score: {score:.3f})")
            print(f"      {content}...")

if __name__ == "__main__":
    asyncio.run(main())