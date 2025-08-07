#!/usr/bin/env python
"""Test audience tools properly through run() method"""

import sys
sys.path.append('src')

from ai_writing_flow.crews.audience_crew import (
    get_audience_list,
    calculate_topic_fit_score,
    generate_key_message,
    analyze_all_audiences,
    calibrate_tone
)

def test_tools():
    print("Testing audience tools through run() method...\n")
    
    # Test 1: Get Audience List
    print("1. Testing Get Audience List:")
    print("-" * 50)
    result = get_audience_list.run()
    print(result)
    print()
    
    # Test 2: Calculate Topic Fit Score
    print("2. Testing Calculate Topic Fit Score:")
    print("-" * 50)
    topic = "The Rise of AI Agents in Software Development"
    result = calculate_topic_fit_score.run(
        topic=topic,
        audience_key="technical_founder",
        platform="LinkedIn"
    )
    print(result)
    print()
    
    # Test 3: Generate Key Message
    print("3. Testing Generate Key Message:")
    print("-" * 50)
    result = generate_key_message.run(
        topic=topic,
        audience_key="technical_founder",
        platform="LinkedIn"
    )
    print(result)
    print()
    
    # Test 4: Analyze All Audiences - THE PROBLEMATIC ONE
    print("4. Testing Analyze All Audiences:")
    print("-" * 50)
    try:
        result = analyze_all_audiences.run(
            topic=topic,
            platform="LinkedIn"
        )
        print(result)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # Test 5: Calibrate Tone
    print("5. Testing Calibrate Tone:")
    print("-" * 50)
    result = calibrate_tone.run(primary_audience="technical_founder")
    print(result)

if __name__ == "__main__":
    test_tools()