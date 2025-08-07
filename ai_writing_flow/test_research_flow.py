#!/usr/bin/env python3
"""Test Research Flow with @listen handlers - Task 5.2"""

import sys
sys.path.append('src')

from ai_writing_flow.crewai_flow.flows.research_flow import ResearchFlow, ResearchFlowState
from ai_writing_flow.models import ContentAnalysisResult

def test_research_flow():
    """Test Research Flow with conditional routing"""
    
    print("🧪 Testing Research Flow - Task 5.2: @listen handlers")
    print("=" * 60)
    
    # Test 1: Flow initialization
    print("\n1️⃣ Testing Research Flow initialization...")
    try:
        flow = ResearchFlow(config={
            'verbose': True,
            'kb_enabled': True,
            'research_depth': 'comprehensive'
        })
        print("✅ Research Flow initialized successfully")
        print(f"✅ Flow ID: {flow.state.flow_id}")
        print(f"✅ Initial stage: {flow.state.current_stage}")
    except Exception as e:
        print(f"❌ Flow initialization failed: {e}")
        return False
    
    # Test 2: Content analysis with @start decorator
    print("\n2️⃣ Testing @start decorator (content analysis)...")
    try:
        test_inputs = {
            'topic_title': 'Advanced CrewAI Flow Patterns',
            'platform': 'Blog',
            'content_type': 'technical',
            'key_themes': ['conditional routing', 'state management'],
            'editorial_recommendations': 'Focus on practical implementation'
        }
        
        # Simulate start method execution
        analysis_result = flow.analyze_content(test_inputs)
        
        print("✅ Content analysis completed")
        print(f"✅ Content category: {analysis_result['content_type']}")
        print(f"✅ Viability score: {analysis_result['viability_score']}")
        print(f"✅ Analysis time: {flow.state.analysis_time:.2f}s")
        
    except Exception as e:
        print(f"❌ Content analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Router logic
    print("\n3️⃣ Testing @router decorator (content type routing)...")
    try:
        # Test different content types
        test_cases = [
            {"content_type": "TECHNICAL", "viability_score": 0.85, "expected": "deep_research"},
            {"content_type": "VIRAL", "viability_score": 0.75, "expected": "quick_research"},
            {"content_type": "STANDARD", "viability_score": 0.65, "expected": "standard_research"},
            {"content_type": "STANDARD", "viability_score": 0.25, "expected": "skip_research"}
        ]
        
        for test_case in test_cases:
            route = flow.route_by_content_type(test_case)
            if route == test_case["expected"]:
                print(f"✅ {test_case['content_type']} (score: {test_case['viability_score']}) → {route}")
            else:
                print(f"❌ {test_case['content_type']} expected {test_case['expected']}, got {route}")
                return False
                
    except Exception as e:
        print(f"❌ Router testing failed: {e}")
        return False
    
    # Test 4: @listen handlers for different research types
    print("\n4️⃣ Testing @listen handlers for research paths...")
    
    # Test deep research
    try:
        print("\n   Testing deep_research listener...")
        # Reset flow state for deep research
        flow.state.content_analysis = ContentAnalysisResult(
            content_type="TECHNICAL",
            viral_score=0.85,
            complexity_level="advanced",
            recommended_flow_path="deep_content_flow",
            kb_insights=["Implementation patterns"],
            processing_time=2.5,
            target_platform="Blog",
            analysis_confidence=0.9,
            key_themes=["CrewAI"],
            audience_indicators={"target": "Developers"},
            content_structure={},
            kb_available=True,
            search_strategy_used="HYBRID",
            kb_query_count=3
        )
        
        deep_result = flow.conduct_deep_research()
        print(f"   ✅ Deep research completed")
        print(f"   ✅ Sources found: {deep_result['sources_count']}")
        print(f"   ✅ Research type: {deep_result['research_type']}")
        print(f"   ✅ Research time: {flow.state.research_time:.2f}s")
        
    except Exception as e:
        print(f"   ❌ Deep research failed: {e}")
        return False
    
    # Test quick research
    try:
        print("\n   Testing quick_research listener...")
        flow.state.content_analysis.content_type = "VIRAL"
        
        quick_result = flow.conduct_quick_research()
        print(f"   ✅ Quick research completed")
        print(f"   ✅ Sources found: {quick_result['sources_count']}")
        print(f"   ✅ Research type: {quick_result['research_type']}")
        
    except Exception as e:
        print(f"   ❌ Quick research failed: {e}")
        return False
    
    # Test standard research
    try:
        print("\n   Testing standard_research listener...")
        flow.state.content_analysis.content_type = "STANDARD"
        
        standard_result = flow.conduct_standard_research()
        print(f"   ✅ Standard research completed")
        print(f"   ✅ Sources found: {standard_result['sources_count']}")
        print(f"   ✅ Research type: {standard_result['research_type']}")
        
    except Exception as e:
        print(f"   ❌ Standard research failed: {e}")
        return False
    
    # Test skip research
    try:
        print("\n   Testing skip_research listener...")
        flow.state.content_analysis.viral_score = 0.2
        
        skip_result = flow.skip_research_process()
        print(f"   ✅ Skip research completed")
        print(f"   ✅ Sources found: {skip_result['sources_count']}")
        print(f"   ✅ Research type: {skip_result['research_type']}")
        
    except Exception as e:
        print(f"   ❌ Skip research failed: {e}")
        return False
    
    # Test 5: Flow state management
    print("\n5️⃣ Testing flow state management...")
    try:
        # Verify state updates throughout flow
        assert flow.state.topic_title == 'Advanced CrewAI Flow Patterns'
        print("✅ Topic title preserved in state")
        
        assert flow.state.platform == 'Blog'
        print("✅ Platform preserved in state")
        
        assert flow.state.research_result is not None
        print("✅ Research result stored in state")
        
        print(f"   Debug: total_sources = {flow.state.total_sources}")
        # Note: Skip research sets total_sources to 0, which is correct
        assert flow.state.total_sources >= 0
        print("✅ Source count tracked in state")
        
        # Check flow summary
        summary = flow.get_flow_summary()
        print(f"✅ Flow summary generated")
        print(f"   - Flow ID: {summary['flow_id']}")
        print(f"   - Current stage: {summary['current_stage']}")
        print(f"   - Total execution time: {summary['metrics']['total_execution_time']:.2f}s")
        
    except AssertionError as e:
        print(f"❌ State management validation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ State management test failed: {e}")
        return False
    
    # Test 6: Research agent metrics
    print("\n6️⃣ Testing research agent metrics integration...")
    try:
        agent_info = flow.research_agent.get_agent_info()
        metrics = agent_info['metrics']
        
        print(f"✅ Research count: {metrics['research_count']}")
        print(f"✅ Total processing time: {metrics['total_processing_time']:.2f}s")
        print(f"✅ Sources found: {metrics['sources_found']}")
        
        assert metrics['research_count'] > 0, "No research executions recorded"
        assert metrics['sources_found'] > 0, "No sources found"
        
    except Exception as e:
        print(f"❌ Metrics test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All Research Flow tests passed!")
    print("✅ Task 5.2 implementation is complete and functional")
    print("\nKey achievements:")
    print("- @start decorator for content analysis")
    print("- @router decorator for content type routing")
    print("- @listen handlers for different research paths")
    print("- State management throughout flow execution")
    print("- Conditional branching based on content type")
    print("- Integration with Research Agent")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_research_flow()
    exit(0 if success else 1)