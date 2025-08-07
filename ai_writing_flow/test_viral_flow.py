#!/usr/bin/env python3
"""Test Viral Content Flow - Task 6.2"""

import sys
sys.path.append('src')

from ai_writing_flow.crewai_flow.flows.viral_content_flow import ViralContentFlow

def test_viral_content_flow():
    """Test Viral Content Flow with all stages"""
    
    print("🧪 Testing Viral Content Flow - Task 6.2")
    print("=" * 60)
    
    # Test 1: Flow initialization
    print("\n1️⃣ Testing Viral Flow initialization...")
    try:
        flow = ViralContentFlow(config={
            'verbose': True,
            'platform_specific': True,
            'max_hashtags': 5,
            'viral_threshold': 0.7
        })
        print("✅ Viral Flow initialized successfully")
        print(f"✅ Flow ID: {flow.state.flow_id}")
        print(f"✅ Flow path: {flow.state.flow_path}")
        print(f"✅ Urgency level: {flow.state.urgency_level}")
        print(f"✅ Target emotion: {flow.state.target_emotion}")
    except Exception as e:
        print(f"❌ Flow initialization failed: {e}")
        return False
    
    # Test 2: Trend research and timing
    print("\n2️⃣ Testing trend research and timing (@start)...")
    try:
        test_inputs = {
            'topic_title': 'AI Agents Writing Code Better Than Humans',
            'platform': 'Twitter',
            'key_themes': ['AI revolution', 'automation', 'future of coding'],
            'editorial_recommendations': 'Create controversy with practical insights',
            'trend_keywords': ['AI', 'coding', 'automation']
        }
        
        trend_result = flow.trend_research_timing(test_inputs)
        
        print("✅ Trend research completed")
        print(f"✅ Viral score: {flow.state.viral_score}")
        print(f"✅ Urgency: {flow.state.trend_analysis['timing']['urgency']}")
        print(f"✅ Predicted reach: {flow.state.estimated_reach:,}")
        print(f"✅ Research time: {flow.state.research_time:.2f}s")
        print(f"✅ Next stage: {trend_result['next_stage']}")
        
        # Check trend quality
        assert flow.state.viral_score > 0.7, "Viral score too low"
        assert flow.state.trend_analysis is not None, "No trend analysis"
        assert flow.state.estimated_reach > 10000, "Reach too low"
        
        # Print viral factors
        print("\n   📊 Viral factors:")
        for factor, score in flow.state.trend_analysis['viral_factors'].items():
            print(f"   - {factor}: {score}")
        
    except Exception as e:
        print(f"❌ Trend research failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Viral writing optimization
    print("\n3️⃣ Testing viral writing optimization (@listen)...")
    try:
        writing_result = flow.viral_writing_optimization(trend_result)
        
        print("✅ Viral writing completed")
        print(f"✅ Draft title: {flow.state.viral_draft.title}")
        print(f"✅ Word count: {flow.state.viral_draft.word_count}")
        print(f"✅ Structure type: {flow.state.viral_draft.structure_type}")
        print(f"✅ Writing time: {flow.state.writing_time:.2f}s")
        
        # Check viral elements
        viral_elements = writing_result['viral_elements']
        print("\n   🔥 Viral elements:")
        print(f"   - Hook strength: {viral_elements['hook_strength']}")
        print(f"   - Shareability: {viral_elements['shareability']}")
        print(f"   - Emotion trigger: {viral_elements['emotion_trigger']}")
        
        assert viral_elements['hook_strength'] > 0.8, "Weak hook"
        assert flow.state.viral_draft.structure_type == "quick_take", "Wrong structure"
        
    except Exception as e:
        print(f"❌ Viral writing failed: {e}")
        return False
    
    # Test 4: Engagement optimization
    print("\n4️⃣ Testing engagement optimization...")
    try:
        optimization_result = flow.engagement_optimization_final(writing_result)
        
        print("✅ Engagement optimization completed")
        print(f"✅ Final viral score: {flow.state.engagement_optimization['final_viral_score']}")
        print(f"✅ Optimizations applied: {len(flow.state.engagement_optimization['optimizations_applied'])}")
        print(f"✅ Ready to post: {optimization_result['ready_to_post']}")
        
        # Print optimizations
        print("\n   ⚡ Optimizations applied:")
        for opt in flow.state.engagement_optimization['optimizations_applied'][:3]:
            print(f"   - {opt}")
        
        # Print engagement predictions
        print("\n   📈 Engagement predictions:")
        for metric, prediction in flow.state.engagement_optimization['engagement_predictions'].items():
            print(f"   - {metric}: {prediction}")
        
        assert flow.state.engagement_optimization['final_viral_score'] > 0.8, "Low final score"
        assert optimization_result['ready_to_post'], "Content not ready"
        
    except Exception as e:
        print(f"❌ Engagement optimization failed: {e}")
        return False
    
    # Test 5: Platform-specific optimizations
    print("\n5️⃣ Testing platform-specific optimizations...")
    try:
        if 'platform_specific' in flow.state.engagement_optimization:
            platform_opts = flow.state.engagement_optimization['platform_specific'].get('Twitter', {})
            
            print(f"✅ Thread optimized: {platform_opts.get('thread_optimized', False)}")
            print(f"✅ Character count: {platform_opts.get('character_count', 0)}")
            print(f"✅ Hashtag relevance: {platform_opts.get('hashtag_relevance', 0)}")
            print(f"✅ Reply bait included: {platform_opts.get('reply_bait_included', False)}")
            
            assert platform_opts.get('character_count', 0) <= 280, "Tweet too long"
            assert platform_opts.get('thread_optimized', False), "Thread not optimized"
        
    except Exception as e:
        print(f"❌ Platform optimization test failed: {e}")
        return False
    
    # Test 6: Draft content validation
    print("\n6️⃣ Validating viral draft content...")
    try:
        draft_content = flow.state.viral_draft.draft
        
        # Check for viral elements
        viral_elements = [
            "🚨",  # Attention emoji
            "BREAKING",  # Urgency word
            "nobody is talking about",  # Exclusivity
            "plot twist",  # Curiosity
            "🧵",  # Thread indicator
            "#"  # Hashtags
        ]
        
        missing_elements = []
        for element in viral_elements:
            if element not in draft_content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"⚠️  Missing viral elements: {missing_elements}")
        else:
            print("✅ All viral elements present")
        
        # Check thread structure for Twitter
        if flow.state.platform == "Twitter":
            thread_markers = ["2/", "3/", "4/", "5/"]
            thread_present = all(marker in draft_content for marker in thread_markers)
            print(f"✅ Thread structure: {'Present' if thread_present else 'Missing'}")
            
            # Check CTA
            cta_present = "Follow for more" in draft_content
            print(f"✅ Call to action: {'Present' if cta_present else 'Missing'}")
        
    except Exception as e:
        print(f"❌ Draft validation failed: {e}")
        return False
    
    # Test 7: Flow summary
    print("\n7️⃣ Testing flow summary...")
    try:
        summary = flow.get_flow_summary()
        
        print(f"✅ Flow summary generated")
        print(f"   - Flow type: {summary['flow_type']}")
        print(f"   - Total execution time: {summary['metrics']['total_execution_time']:.2f}s")
        print(f"   - Viral potential: {summary['quality_indicators']['viral_potential']}")
        print(f"   - Timing optimal: {summary['quality_indicators']['timing_optimal']}")
        print(f"   - Platform optimized: {summary['quality_indicators']['platform_optimized']}")
        
        assert summary['current_stage'] == 'engagement_optimization', "Flow incomplete"
        assert summary['quality_indicators']['ready_to_post'], "Content not ready"
        
    except Exception as e:
        print(f"❌ Flow summary failed: {e}")
        return False
    
    # Test 8: Different platform test (LinkedIn)
    print("\n8️⃣ Testing with different platform (LinkedIn)...")
    try:
        flow_linkedin = ViralContentFlow(config={'verbose': False})
        
        linkedin_inputs = {
            'topic_title': 'The Future of AI in Business',
            'platform': 'LinkedIn',
            'key_themes': ['AI transformation', 'business innovation']
        }
        
        # Run through flow
        trend = flow_linkedin.trend_research_timing(linkedin_inputs)
        writing = flow_linkedin.viral_writing_optimization(trend)
        final = flow_linkedin.engagement_optimization_final(writing)
        
        print("✅ LinkedIn flow completed")
        print(f"✅ Platform: {flow_linkedin.state.platform}")
        print(f"✅ Viral score: {flow_linkedin.state.viral_score}")
        
        # LinkedIn content should be different
        assert flow_linkedin.state.platform == 'LinkedIn'
        assert flow_linkedin.state.viral_draft.word_count == 280  # Still optimized for brevity
        
    except Exception as e:
        print(f"❌ LinkedIn test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All Viral Content Flow tests passed!")
    print("✅ Task 6.2 implementation is complete and functional")
    print("\nKey achievements:")
    print("- Trend research with timing optimization")
    print("- Viral writing with engagement hooks")
    print("- Platform-specific optimizations")
    print("- Engagement prediction and optimization")
    print("- Ready-to-post viral content generation")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_viral_content_flow()
    exit(0 if success else 1)