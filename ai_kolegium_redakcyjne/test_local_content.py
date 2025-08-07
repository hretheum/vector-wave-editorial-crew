#!/usr/bin/env python
"""
Test script for local content integration with AI Kolegium Redakcyjne
"""

import sys
import os
from datetime import datetime
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ai_kolegium_redakcyjne.tools import LocalContentReaderTool, ContentAnalyzerTool
from ai_kolegium_redakcyjne.crew import AiKolegiumRedakcyjne


def test_local_tools():
    """Test local content tools independently"""
    print("🔍 Testing Local Content Tools...\n")
    
    # Test reader
    reader = LocalContentReaderTool()
    contents = reader._run()
    
    print(f"📚 Found {len(contents)} content files")
    
    if contents:
        # Show sample
        sample = contents[0]
        print(f"\n📄 Sample content:")
        print(f"  - Title: {sample['title']}")
        print(f"  - Folder: {sample['folder_name']}")
        print(f"  - Word count: {sample['word_count']}")
        print(f"  - Data points: {sample['data_points_count']}")
        print(f"  - Preview: {sample['content_preview'][:100]}...")
        
        # Test analyzer
        analyzer = ContentAnalyzerTool()
        analysis = analyzer._run(contents)
        
        print(f"\n📊 Content Analysis:")
        print(f"  - Total items: {analysis['total_items']}")
        print(f"  - Content types: {analysis['content_types']}")
        print(f"  - Topics found: {list(analysis['topics_frequency'].keys())}")
        print(f"  - Data-rich content: {len(analysis['data_rich_content'])} items")
        
        if analysis['content_gaps']:
            print(f"  - Content gaps: {analysis['content_gaps']}")


def test_kolegium_with_local_content():
    """Test full kolegium workflow with local content"""
    print("\n\n🚀 Testing Full Kolegium with Local Content...\n")
    
    inputs = {
        'categories': ['AI', 'Technology', 'Digital Culture', 'Productivity'],
        'current_date': datetime.now().strftime("%Y-%m-%d"),
        'max_topics': 10,
        'controversy_threshold': 0.7,
        'content_source_path': '/Users/hretheum/dev/bezrobocie/vector-wave/content/raw'
    }
    
    print(f"📋 Configuration:")
    print(f"  - Categories: {inputs['categories']}")
    print(f"  - Content source: {inputs['content_source_path']}")
    print(f"  - Max topics: {inputs['max_topics']}")
    
    try:
        # Run the crew
        print("\n🎬 Starting AI Kolegium Redakcyjne...\n")
        result = AiKolegiumRedakcyjne().crew().kickoff(inputs=inputs)
        
        # Save result
        with open('editorial_report_with_local.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        print("\n✅ Editorial pipeline completed!")
        print("📄 Report saved to: editorial_report_with_local.json")
        
        # Show summary
        if isinstance(result, dict):
            approved = len(result.get('approved_topics', []))
            rejected = len(result.get('rejected_topics', []))
            human_review = len(result.get('human_review_queue', []))
            
            print(f"\n📊 Results Summary:")
            print(f"  - Approved topics: {approved}")
            print(f"  - Rejected topics: {rejected}")
            print(f"  - Human review needed: {human_review}")
            
            # Check if local content was used
            local_used = 0
            for topic in result.get('approved_topics', []):
                if 'local_content' in str(topic.get('source', '')):
                    local_used += 1
            
            print(f"  - Topics using local content: {local_used}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Test tools first
    test_local_tools()
    
    # Then test full integration
    response = input("\n\n🤔 Run full kolegium test? (y/n): ")
    if response.lower() == 'y':
        test_kolegium_with_local_content()
    else:
        print("Skipping full test. You can run it manually with:")
        print("python test_local_content.py")