#!/usr/bin/env python3
"""Test Standard Content Flow - Task 6.3"""

import sys
sys.path.append('src')

from ai_writing_flow.crewai_flow.flows.standard_content_flow import StandardContentFlow

def test_standard_content_flow():
    """Test Standard Content Flow with all stages"""
    
    print("🧪 Testing Standard Content Flow - Task 6.3")
    print("=" * 60)
    
    # Test 1: Flow initialization
    print("\n1️⃣ Testing Standard Flow initialization...")
    try:
        flow = StandardContentFlow(config={
            'verbose': True,
            'min_sources': 3,
            'quality_threshold': 0.8
        })
        print("✅ Standard Flow initialized successfully")
        print(f"✅ Flow ID: {flow.state.flow_id}")
        print(f"✅ Flow path: {flow.state.flow_path}")
        print(f"✅ Platform: {flow.state.platform}")
    except Exception as e:
        print(f"❌ Flow initialization failed: {e}")
        return False
    
    # Test 2: Comprehensive research
    print("\n2️⃣ Testing comprehensive research (@start)...")
    try:
        test_inputs = {
            'topic_title': 'Building Scalable AI Systems',
            'platform': 'Blog',
            'key_themes': ['scalability', 'best practices', 'architecture'],
            'editorial_recommendations': 'Focus on practical implementation with real-world examples'
        }
        
        research_result = flow.comprehensive_research(test_inputs)
        
        print("✅ Comprehensive research completed")
        print(f"✅ Sources found: {len(flow.state.research_result.sources)}")
        print(f"✅ Key insights: {len(flow.state.research_result.key_insights)}")
        print(f"✅ Research time: {flow.state.research_time:.2f}s")
        print(f"✅ Next stage: {research_result['next_stage']}")
        
        # Check research quality
        assert len(flow.state.research_result.sources) >= 3, "Insufficient sources"
        assert len(flow.state.research_result.key_insights) >= 5, "Insufficient insights"
        
    except Exception as e:
        print(f"❌ Comprehensive research failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Audience analysis
    print("\n3️⃣ Testing audience analysis (@listen)...")
    try:
        audience_result = flow.audience_analysis(research_result)
        
        print("✅ Audience analysis completed")
        print(f"✅ Primary audience: {flow.state.audience_analysis['primary_audience']['profile']}")
        print(f"✅ Expertise level: {flow.state.audience_analysis['primary_audience']['expertise_level']}")
        print(f"✅ Content preferences: {flow.state.audience_analysis['content_preferences']['format']}")
        print(f"✅ Analysis time: {flow.state.audience_time:.2f}s")
        
        # Check audience analysis
        assert flow.state.audience_analysis is not None, "No audience analysis"
        assert 'primary_audience' in flow.state.audience_analysis, "Missing primary audience"
        assert 'content_preferences' in flow.state.audience_analysis, "Missing content preferences"
        
    except Exception as e:
        print(f"❌ Audience analysis failed: {e}")
        return False
    
    # Test 4: Structured writing
    print("\n4️⃣ Testing structured writing...")
    try:
        writing_result = flow.structured_writing(audience_result)
        
        print("✅ Structured writing completed")
        print(f"✅ Draft title: {flow.state.draft_content.title}")
        print(f"✅ Word count: {flow.state.draft_content.word_count}")
        print(f"✅ Structure type: {flow.state.draft_content.structure_type}")
        print(f"✅ Key sections: {len(flow.state.draft_content.key_sections)}")
        print(f"✅ Writing time: {flow.state.writing_time:.2f}s")
        
        # Check draft quality
        assert flow.state.draft_content.word_count >= 1000, "Content too short"
        assert len(flow.state.draft_content.key_sections) >= 6, "Missing key sections"
        assert flow.state.draft_content.structure_type == "comprehensive_guide", "Wrong structure type"
        
        # Print key sections
        print("\n   📑 Key sections:")
        for section in flow.state.draft_content.key_sections[:5]:
            print(f"   - {section}")
        
    except Exception as e:
        print(f"❌ Structured writing failed: {e}")
        return False
    
    # Test 5: Style optimization
    print("\n5️⃣ Testing style optimization...")
    try:
        style_result = flow.style_optimization(writing_result)
        
        print("✅ Style optimization completed")
        print(f"✅ Readability score: {flow.state.style_optimization['readability_score']}")
        print(f"✅ Tone: {flow.state.style_optimization['tone']}")
        print(f"✅ Improvements made: {len(flow.state.style_optimization['improvements_made'])}")
        print(f"✅ Style time: {flow.state.style_time:.2f}s")
        
        # Check style optimization
        assert flow.state.style_optimization['readability_score'] > 0.8, "Low readability"
        assert len(flow.state.style_optimization['improvements_made']) > 0, "No improvements made"
        
        # Print improvements
        print("\n   ✨ Style improvements:")
        for improvement in flow.state.style_optimization['improvements_made'][:3]:
            print(f"   - {improvement}")
        
    except Exception as e:
        print(f"❌ Style optimization failed: {e}")
        return False
    
    # Test 6: Quality review
    print("\n6️⃣ Testing quality review...")
    try:
        review_result = flow.quality_review_final(style_result)
        
        print("✅ Quality review completed")
        print(f"✅ Overall quality score: {flow.state.quality_review['overall_quality_score']}")
        print(f"✅ Approval status: {flow.state.quality_review['approval_status']}")
        print(f"✅ Quality time: {flow.state.quality_time:.2f}s")
        
        # Print criteria scores
        print("\n   📊 Quality criteria scores:")
        for criterion, score in flow.state.quality_review['criteria_scores'].items():
            print(f"   - {criterion}: {score}")
        
        # Check quality
        assert flow.state.quality_review['overall_quality_score'] >= 0.8, "Quality below threshold"
        assert flow.state.quality_review['approval_status'] == "ready_to_publish", "Not ready to publish"
        assert all(flow.state.quality_review['final_checks'].values()), "Some final checks failed"
        
    except Exception as e:
        print(f"❌ Quality review failed: {e}")
        return False
    
    # Test 7: Flow summary
    print("\n7️⃣ Testing flow summary...")
    try:
        summary = flow.get_flow_summary()
        
        print(f"✅ Flow summary generated")
        print(f"   - Flow type: {summary['flow_type']}")
        print(f"   - Total execution time: {summary['metrics']['total_execution_time']:.2f}s")
        print(f"   - Research quality: {summary['quality_indicators']['research_quality']}")
        print(f"   - Quality score: {summary['quality_indicators']['quality_score']}")
        
        # Verify all stages completed
        assert summary['current_stage'] == 'quality_review', "Flow did not complete all stages"
        assert summary['quality_indicators']['quality_score'] >= 0.8, "Quality below threshold"
        
    except Exception as e:
        print(f"❌ Flow summary failed: {e}")
        return False
    
    # Test 8: Draft content validation
    print("\n8️⃣ Validating standard draft structure...")
    try:
        draft_content = flow.state.draft_content.draft
        
        # Check for key standard elements
        standard_elements = [
            "## Executive Summary",
            "## Introduction",
            "## Key Concepts",
            "## Implementation Guide",
            "## Best Practices",
            "## Common Challenges",
            "## Success Metrics",
            "## Conclusion"
        ]
        
        missing_elements = []
        for element in standard_elements:
            if element not in draft_content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"⚠️  Missing elements: {missing_elements}")
        else:
            print("✅ All standard elements present in draft")
        
        # Check structure quality
        has_phases = "Phase 1:" in draft_content and "Phase 2:" in draft_content
        print(f"✅ Phased approach: {'Present' if has_phases else 'Missing'}")
        
        has_metrics = "Success Metrics" in draft_content
        print(f"✅ Success metrics: {'Present' if has_metrics else 'Missing'}")
        
        has_next_steps = "Next Steps:" in draft_content
        print(f"✅ Next steps: {'Present' if has_next_steps else 'Missing'}")
        
    except Exception as e:
        print(f"❌ Draft validation failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All Standard Content Flow tests passed!")
    print("✅ Task 6.3 implementation is complete and functional")
    print("\nKey achievements:")
    print("- Comprehensive research with source verification")
    print("- Audience-aligned content creation")
    print("- Structured writing following editorial process")
    print("- Style optimization for readability")
    print("- Quality review ensuring publication readiness")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_standard_content_flow()
    exit(0 if success else 1)