#!/usr/bin/env python
"""Test audience crew execution directly"""

import sys
sys.path.append('src')

from ai_writing_flow.crews.audience_crew import AudienceCrew
import logging

# Enable detailed logging
logging.basicConfig(level=logging.INFO)

def test_audience_crew():
    print("Testing AudienceCrew execution...\n")
    
    # Create crew instance
    crew = AudienceCrew()
    
    # Test parameters
    topic = "The Rise of AI Agents in Software Development"
    platform = "LinkedIn"
    research_summary = "AI agents are transforming software development with 75% automation by 2026."
    editorial_recommendations = "Focus on practical examples and ROI"
    
    try:
        # Execute crew
        result = crew.execute(
            topic=topic,
            platform=platform,
            research_summary=research_summary,
            editorial_recommendations=editorial_recommendations
        )
        
        print("\n✅ SUCCESS! Crew completed.")
        print(f"Result type: {type(result)}")
        print(f"Primary audience score: {result.technical_founder_score}")
        print(f"Recommended depth: {result.recommended_depth}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_audience_crew()