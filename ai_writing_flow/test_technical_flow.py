#!/usr/bin/env python3
"""Test Technical Content Flow - Task 6.1"""

import sys
sys.path.append('src')

from ai_writing_flow.crewai_flow.flows.technical_content_flow import TechnicalContentFlow

def test_technical_content_flow():
    """Test Technical Content Flow with all stages"""
    
    print("🧪 Testing Technical Content Flow - Task 6.1")
    print("=" * 60)
    
    # Test 1: Flow initialization
    print("\n1️⃣ Testing Technical Flow initialization...")
    try:
        flow = TechnicalContentFlow(config={
            'verbose': True,
            'validate_code': True,
            'max_code_examples': 5,
            'technical_level': 'deep'
        })
        print("✅ Technical Flow initialized successfully")
        print(f"✅ Flow ID: {flow.state.flow_id}")
        print(f"✅ Flow path: {flow.state.flow_path}")
        print(f"✅ Technical depth: {flow.state.technical_depth}")
    except Exception as e:
        print(f"❌ Flow initialization failed: {e}")
        return False
    
    # Test 2: Deep technical research
    print("\n2️⃣ Testing deep technical research (@start)...")
    try:
        test_inputs = {
            'topic_title': 'Implementing CrewAI Flow with Circuit Breakers',
            'platform': 'Blog',
            'key_themes': ['fault tolerance', 'resilience patterns', 'production systems'],
            'editorial_recommendations': 'Focus on practical implementation with real-world examples',
            'code_language': 'python',
            'framework': 'CrewAI'
        }
        
        research_result = flow.deep_technical_research(test_inputs)
        
        print("✅ Deep technical research completed")
        print(f"✅ Sources found: {len(flow.state.research_result.sources)}")
        print(f"✅ Key insights: {len(flow.state.research_result.key_insights)}")
        print(f"✅ Research time: {flow.state.research_time:.2f}s")
        print(f"✅ Next stage: {research_result['next_stage']}")
        
        # Check research quality
        assert len(flow.state.research_result.sources) >= 3, "Insufficient sources"
        assert len(flow.state.research_result.key_insights) >= 5, "Insufficient insights"
        assert flow.state.research_result.data_points, "No data points found"
        
    except Exception as e:
        print(f"❌ Technical research failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Code validation
    print("\n3️⃣ Testing code validation (@listen)...")
    try:
        # Simulate listener execution
        validation_result = flow.validate_code_examples(research_result)
        
        print("✅ Code validation completed")
        print(f"✅ Validated: {flow.state.code_validation_result['validated']}")
        print(f"✅ Code examples: {flow.state.total_code_examples}")
        print(f"✅ Validation time: {flow.state.validation_time:.2f}s")
        print(f"✅ Next stage: {validation_result['next_stage']}")
        
        # Check validation results
        assert flow.state.code_validation_result['validated'], "Code validation failed"
        assert flow.state.total_code_examples > 0, "No code examples generated"
        
        # Print example details
        if 'code_examples' in flow.state.code_validation_result:
            print("\n   📝 Code examples validated:")
            for i, example in enumerate(flow.state.code_validation_result['code_examples'], 1):
                print(f"   {i}. {example['title']} - {example['test_result']}")
        
    except Exception as e:
        print(f"❌ Code validation failed: {e}")
        return False
    
    # Test 4: Technical writing
    print("\n4️⃣ Testing technical writing...")
    try:
        writing_result = flow.technical_writing(validation_result)
        
        print("✅ Technical writing completed")
        print(f"✅ Draft title: {flow.state.technical_draft.title}")
        print(f"✅ Word count: {flow.state.technical_draft.word_count}")
        print(f"✅ Key sections: {len(flow.state.technical_draft.key_sections)}")
        print(f"✅ Non-obvious insights: {len(flow.state.technical_draft.non_obvious_insights)}")
        print(f"✅ Writing time: {flow.state.writing_time:.2f}s")
        
        # Check draft quality
        assert flow.state.technical_draft.word_count >= 2000, "Content too short for technical deep dive"
        assert len(flow.state.technical_draft.key_sections) >= 8, "Missing key sections"
        assert flow.state.technical_draft.structure_type == "deep_analysis", "Wrong structure type"
        
        # Print key sections
        print("\n   📑 Key sections:")
        for section in flow.state.technical_draft.key_sections[:5]:
            print(f"   - {section}")
        
    except Exception as e:
        print(f"❌ Technical writing failed: {e}")
        return False
    
    # Test 5: Technical review and optimization
    print("\n5️⃣ Testing technical review and optimization...")
    try:
        review_result = flow.technical_review_optimization(writing_result)
        
        print("✅ Technical review completed")
        print(f"✅ Technical accuracy: {review_result['review']['technical_accuracy']}")
        print(f"✅ Code quality: {review_result['review']['code_quality']}")
        print(f"✅ Completeness: {review_result['review']['completeness']}")
        print(f"✅ Optimizations applied: {len(review_result['review']['optimizations_applied'])}")
        
        # Check review results
        assert review_result['review']['technical_accuracy'] == 'verified', "Technical accuracy not verified"
        assert review_result['review']['code_quality'] == 'high', "Code quality not high"
        assert all(review_result['review']['final_checks'].values()), "Some final checks failed"
        
        # Print optimizations
        print("\n   🔧 Optimizations applied:")
        for opt in review_result['review']['optimizations_applied'][:3]:
            print(f"   - {opt}")
        
    except Exception as e:
        print(f"❌ Technical review failed: {e}")
        return False
    
    # Test 6: Flow summary
    print("\n6️⃣ Testing flow summary...")
    try:
        summary = flow.get_flow_summary()
        
        print(f"✅ Flow summary generated")
        print(f"   - Flow type: {summary['flow_type']}")
        print(f"   - Total execution time: {summary['metrics']['total_execution_time']:.2f}s")
        print(f"   - Code language: {summary['technical_details']['code_language']}")
        print(f"   - Framework: {summary['technical_details']['framework']}")
        print(f"   - Code examples: {summary['technical_details']['code_examples_included']}")
        print(f"   - Production ready: {summary['quality_indicators']['production_ready']}")
        
        # Verify all stages completed
        assert summary['current_stage'] == 'technical_review', "Flow did not complete all stages"
        assert summary['quality_indicators']['production_ready'], "Content not production ready"
        
    except Exception as e:
        print(f"❌ Flow summary failed: {e}")
        return False
    
    # Test 7: Code validation disabled scenario
    print("\n7️⃣ Testing with code validation disabled...")
    try:
        flow_no_validation = TechnicalContentFlow(config={
            'verbose': False,
            'validate_code': False  # Disable validation
        })
        
        # Run research
        inputs = {'topic_title': 'Quick Technical Test'}
        research = flow_no_validation.deep_technical_research(inputs)
        
        # Try validation
        validation = flow_no_validation.validate_code_examples(research)
        
        print("✅ Flow works with validation disabled")
        print(f"✅ Validation skipped: {not flow_no_validation.state.code_validation_result['validated']}")
        print(f"✅ Reason: {flow_no_validation.state.code_validation_result['reason']}")
        
    except Exception as e:
        print(f"❌ No-validation test failed: {e}")
        return False
    
    # Test 8: Draft content structure
    print("\n8️⃣ Validating technical draft structure...")
    try:
        draft_content = flow.state.technical_draft.draft
        
        # Check for key technical elements
        technical_elements = [
            "## Architecture Overview",
            "## Implementation Details",
            "## Code Examples",
            "## Performance Considerations",
            "## Testing Strategies",
            "## Best Practices"
        ]
        
        missing_elements = []
        for element in technical_elements:
            if element not in draft_content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"⚠️  Missing elements: {missing_elements}")
        else:
            print("✅ All technical elements present in draft")
        
        # Check code examples formatting
        code_block_count = draft_content.count("```")
        print(f"✅ Code blocks found: {code_block_count // 2}")
        
        # Check references
        reference_count = draft_content.count("## References")
        print(f"✅ References section: {'Present' if reference_count > 0 else 'Missing'}")
        
    except Exception as e:
        print(f"❌ Draft validation failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All Technical Content Flow tests passed!")
    print("✅ Task 6.1 implementation is complete and functional")
    print("\nKey achievements:")
    print("- Deep technical research with exhaustive search")
    print("- Code validation and testing integration")
    print("- Technical writing with code examples")
    print("- Comprehensive review and optimization")
    print("- Production-ready technical content generation")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_technical_content_flow()
    exit(0 if success else 1)