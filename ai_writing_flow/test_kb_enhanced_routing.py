#!/usr/bin/env python3
"""Test KB-enhanced routing - Task 5.3"""

import sys
sys.path.append('src')

from ai_writing_flow.crewai_flow.flows.research_flow import ResearchFlow
from ai_writing_flow.adapters.knowledge_adapter import KnowledgeResponse, SearchStrategy
from unittest.mock import patch, MagicMock, AsyncMock

def test_kb_enhanced_routing():
    """Test KB-enhanced routing decisions"""
    
    print("🧪 Testing KB-enhanced routing - Task 5.3")
    print("=" * 60)
    
    # Test 1: Flow with KB enabled
    print("\n1️⃣ Testing Research Flow with KB enabled...")
    try:
        flow = ResearchFlow(config={
            'verbose': True,
            'kb_enabled': True,
            'research_depth': 'comprehensive'
        })
        print("✅ Research Flow initialized with KB enabled")
        print(f"✅ KB enabled: {flow.config.get('kb_enabled', True)}")
    except Exception as e:
        print(f"❌ Flow initialization failed: {e}")
        return False
    
    # Test 2: Mock KB responses for different scenarios
    print("\n2️⃣ Testing KB-enhanced routing scenarios...")
    
    # Test scenario 1: Technical content with KB guidance
    print("\n   Scenario 1: Technical content with KB deep dive recommendation")
    try:
        # Create mock KB response for technical content
        mock_kb_response = KnowledgeResponse(
            query="CrewAI Flow routing patterns for TECHNICAL content",
            results=[{
                "content": "For technical implementation details, use deep dive comprehensive research approach",
                "score": 0.95,
                "source": "knowledge_base"
            }],
            kb_available=True,
            strategy_used=SearchStrategy.HYBRID
        )
        
        # Mock the KnowledgeAdapter search method
        with patch('ai_writing_flow.adapters.knowledge_adapter.KnowledgeAdapter') as mock_adapter_class:
            mock_adapter = mock_adapter_class.return_value
            mock_adapter.search = AsyncMock(return_value=mock_kb_response)
            
            # Test routing
            analysis_output = {
                "content_type": "TECHNICAL",
                "viability_score": 0.85
            }
            
            route = flow.route_by_content_type(analysis_output)
            
            print(f"   ✅ Route decision: {route}")
            print(f"   ✅ KB insights: {flow.state.kb_insights}")
            
            assert route == "deep_research"
            assert len(flow.state.kb_insights) > 0
            
    except Exception as e:
        print(f"   ❌ Scenario 1 failed: {e}")
        return False
    
    # Test scenario 2: Low viability with KB override
    print("\n   Scenario 2: Low viability content with KB override")
    try:
        # Reset KB insights
        flow.state.kb_insights = []
        
        # Create mock KB response suggesting hidden gem
        mock_kb_response = KnowledgeResponse(
            query="CrewAI Flow routing patterns",
            results=[{
                "content": "This is an emerging trend with future potential, consider as hidden gem",
                "score": 0.85,
                "source": "knowledge_base"
            }],
            kb_available=True
        )
        
        with patch('ai_writing_flow.adapters.knowledge_adapter.KnowledgeAdapter') as mock_adapter_class:
            mock_adapter = mock_adapter_class.return_value
            mock_adapter.search = AsyncMock(return_value=mock_kb_response)
            
            # Test routing with low viability
            analysis_output = {
                "content_type": "STANDARD",
                "viability_score": 0.25  # Low viability
            }
            
            route = flow.route_by_content_type(analysis_output)
            
            print(f"   ✅ Route decision: {route}")
            print(f"   ✅ KB override applied: {'KB: Override low viability' in str(flow.state.kb_insights)}")
            
            # Should override to standard_research instead of skip_research
            assert route == "standard_research"
            assert any("override" in insight.lower() for insight in flow.state.kb_insights)
            
    except Exception as e:
        print(f"   ❌ Scenario 2 failed: {e}")
        return False
    
    # Test scenario 3: Viral content with urgency
    print("\n   Scenario 3: Viral content with high urgency")
    try:
        # Reset KB insights
        flow.state.kb_insights = []
        
        # Create mock KB response for viral content
        mock_kb_response = KnowledgeResponse(
            query="CrewAI Flow routing patterns",
            results=[{
                "content": "Time-sensitive viral trend requiring urgent quick turnaround",
                "score": 0.9,
                "source": "knowledge_base"
            }],
            kb_available=True
        )
        
        with patch('ai_writing_flow.adapters.knowledge_adapter.KnowledgeAdapter') as mock_adapter_class:
            mock_adapter = mock_adapter_class.return_value
            mock_adapter.search = AsyncMock(return_value=mock_kb_response)
            
            # Test routing
            analysis_output = {
                "content_type": "VIRAL",
                "viability_score": 0.75
            }
            
            route = flow.route_by_content_type(analysis_output)
            
            print(f"   ✅ Route decision: {route}")
            print(f"   ✅ Viral urgency detected: {'viral urgency' in str(flow.state.kb_insights).lower()}")
            
            assert route == "quick_research"
            
    except Exception as e:
        print(f"   ❌ Scenario 3 failed: {e}")
        return False
    
    # Test 3: KB disabled scenario
    print("\n3️⃣ Testing routing with KB disabled...")
    try:
        flow_no_kb = ResearchFlow(config={
            'verbose': True,
            'kb_enabled': False
        })
        
        # Should fall back to standard routing
        analysis_output = {
            "content_type": "TECHNICAL",
            "viability_score": 0.85
        }
        
        route = flow_no_kb.route_by_content_type(analysis_output)
        
        print(f"✅ Route without KB: {route}")
        print(f"✅ No KB insights added: {len(flow_no_kb.state.kb_insights) == 0}")
        
        assert route == "deep_research"
        assert len(flow_no_kb.state.kb_insights) == 0
        
    except Exception as e:
        print(f"❌ KB disabled test failed: {e}")
        return False
    
    # Test 4: KB error handling
    print("\n4️⃣ Testing KB error handling...")
    try:
        flow.state.kb_insights = []
        
        # Mock KB search to raise exception
        with patch('ai_writing_flow.adapters.knowledge_adapter.KnowledgeAdapter') as mock_adapter_class:
            mock_adapter = mock_adapter_class.return_value
            mock_adapter.search = AsyncMock(side_effect=Exception("KB connection failed"))
            
            # Should fall back to standard routing
            analysis_output = {
                "content_type": "STANDARD",
                "viability_score": 0.5
            }
            
            route = flow.route_by_content_type(analysis_output)
            
            print(f"✅ Fallback route on KB error: {route}")
            print(f"✅ Graceful degradation: routing still works")
            
            assert route == "standard_research"
            
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False
    
    # Test 5: KB confidence thresholds
    print("\n5️⃣ Testing KB confidence thresholds...")
    try:
        flow.state.kb_insights = []
        
        # Low confidence KB result
        mock_kb_response = KnowledgeResponse(
            query="CrewAI Flow routing patterns",
            results=[{
                "content": "Maybe consider deep research",
                "score": 0.6,  # Below threshold
                "source": "knowledge_base"
            }],
            kb_available=True
        )
        
        with patch('ai_writing_flow.adapters.knowledge_adapter.KnowledgeAdapter') as mock_adapter_class:
            mock_adapter = mock_adapter_class.return_value
            mock_adapter.search = AsyncMock(return_value=mock_kb_response)
            
            analysis_output = {
                "content_type": "TECHNICAL",
                "viability_score": 0.85
            }
            
            route = flow.route_by_content_type(analysis_output)
            
            print(f"✅ Low confidence KB ignored: {route}")
            print(f"✅ Uses standard routing logic")
            
            assert route == "deep_research"
            
    except Exception as e:
        print(f"❌ Confidence threshold test failed: {e}")
        return False
    
    # Test 6: Multiple KB results analysis
    print("\n6️⃣ Testing multiple KB results analysis...")
    try:
        flow.state.kb_insights = []
        
        # Multiple KB results
        mock_kb_response = KnowledgeResponse(
            query="CrewAI Flow routing patterns",
            results=[
                {
                    "content": "Consider deep technical implementation details",
                    "score": 0.8,
                    "source": "knowledge_base"
                },
                {
                    "content": "@router decorator for conditional routing patterns",
                    "score": 0.85,
                    "source": "knowledge_base"
                },
                {
                    "content": "Extreme technical depth required",
                    "score": 0.9,
                    "source": "knowledge_base"
                }
            ],
            kb_available=True
        )
        
        with patch('ai_writing_flow.adapters.knowledge_adapter.KnowledgeAdapter') as mock_adapter_class:
            mock_adapter = mock_adapter_class.return_value
            mock_adapter.search = AsyncMock(return_value=mock_kb_response)
            
            analysis_output = {
                "content_type": "TECHNICAL",
                "viability_score": 0.85
            }
            
            route = flow.route_by_content_type(analysis_output)
            
            print(f"✅ Multiple KB results processed: {route}")
            print(f"✅ Router pattern detected: {'Router pattern detected' in str(flow.state.kb_insights)}")
            print(f"✅ Extreme depth detected: {'Extreme technical depth' in str(flow.state.kb_insights)}")
            
            assert route == "deep_research"
            assert len(flow.state.kb_insights) >= 2
            
    except Exception as e:
        print(f"❌ Multiple results test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All KB-enhanced routing tests passed!")
    print("✅ Task 5.3 implementation is complete and functional")
    print("\nKey achievements:")
    print("- KB queries enhance routing decisions")
    print("- High confidence KB overrides standard routing")
    print("- Low viability topics can be rescued by KB insights")
    print("- Graceful fallback when KB unavailable")
    print("- Multiple KB results analyzed for patterns")
    print("- Confidence thresholds applied correctly")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_kb_enhanced_routing()
    exit(0 if success else 1)