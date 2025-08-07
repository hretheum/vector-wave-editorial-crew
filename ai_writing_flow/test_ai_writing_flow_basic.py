#!/usr/bin/env python3
"""
Basic validation test for AIWritingFlow

Tests:
1. Flow instantiation 
2. @start decorator functionality
3. kickoff() method compatibility
4. Infrastructure integration
5. Error handling
"""

import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_writing_flow.crewai_flow.flows.ai_writing_flow import AIWritingFlow, create_ai_writing_flow
from ai_writing_flow.linear_flow import WritingFlowInputs

def test_flow_instantiation():
    """Test basic flow instantiation"""
    print("🧪 Testing flow instantiation...")
    
    try:
        flow = AIWritingFlow()
        print(f"✅ Flow created with ID: {flow.flow_id}")
        
        # Test infrastructure components
        assert flow.metrics is not None, "FlowMetrics not initialized"
        assert flow.content_analysis_breaker is not None, "Circuit breaker not initialized"
        assert flow.content_analysis_agent is not None, "Content analysis agent not initialized"
        assert flow.content_analysis_task is not None, "Content analysis task not initialized"
        
        print("✅ Infrastructure components initialized")
        return True
        
    except Exception as e:
        print(f"❌ Flow instantiation failed: {e}")
        return False

def test_input_validation():
    """Test input validation and conversion"""
    print("\n🧪 Testing input validation...")
    
    try:
        flow = AIWritingFlow()
        
        # Test valid inputs
        test_inputs = {
            "topic_title": "Test CrewAI Flow Implementation",
            "platform": "LinkedIn",
            "file_path": str(Path(__file__).parent),  # Use current directory
            "content_type": "STANDALONE",
            "viral_score": 7.5
        }
        
        validated = flow._validate_and_convert_inputs(test_inputs)
        assert isinstance(validated, WritingFlowInputs)
        assert validated.topic_title == "Test CrewAI Flow Implementation"
        assert validated.platform == "LinkedIn"
        
        print("✅ Input validation successful")
        
        # Test invalid inputs
        try:
            invalid_inputs = {
                "topic_title": "",  # Empty title
                "platform": "LinkedIn", 
                "file_path": "/nonexistent/path"  # Invalid path
            }
            flow._validate_and_convert_inputs(invalid_inputs)
            print("❌ Should have failed with invalid inputs")
            return False
        except ValueError:
            print("✅ Invalid input handling works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Input validation test failed: {e}")
        return False

def test_start_decorator():
    """Test @start decorator functionality"""
    print("\n🧪 Testing @start decorator...")
    
    try:
        flow = AIWritingFlow()
        
        # Create test inputs
        test_inputs = {
            "topic_title": "CrewAI Flow Testing",
            "platform": "LinkedIn",
            "file_path": str(Path(__file__).parent),
            "content_type": "STANDALONE",
            "viral_score": 6.0
        }
        
        # Execute the @start method through kickoff 
        # (Direct @start method calls are handled by CrewAI framework)
        inputs = WritingFlowInputs(
            topic_title="CrewAI Flow Testing",
            platform="LinkedIn",
            file_path=str(Path(__file__).parent),
            content_type="STANDALONE",
            viral_score=6.0
        )
        result = flow.kickoff(inputs)
        
        # Validate result structure
        assert "flow_id" in result
        assert "analysis_result" in result
        assert "flow_state" in result
        assert "success" in result
        assert result["success"] == True
        
        # Validate flow state was created
        assert flow.flow_state is not None
        assert flow.flow_state.topic_title == "CrewAI Flow Testing" 
        assert flow.flow_state.current_stage == "content_analysis"
        assert "content_analysis_agent" in flow.flow_state.agents_executed
        
        print("✅ @start decorator execution successful")
        print(f"   Flow ID: {result['flow_id']}")
        print(f"   Analysis confidence: {result['analysis_result'].get('analysis_confidence', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ @start decorator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_kickoff_compatibility():
    """Test kickoff() method compatibility"""
    print("\n🧪 Testing kickoff() compatibility...")
    
    try:
        flow = AIWritingFlow()
        
        # Create WritingFlowInputs
        inputs = WritingFlowInputs(
            topic_title="Kickoff Test",
            platform="Twitter",
            file_path=str(Path(__file__).parent),
            content_type="STANDALONE",
            viral_score=5.0,
            skip_research=True
        )
        
        # Execute kickoff
        result = flow.kickoff(inputs)
        
        # Validate result
        assert result["success"] == True
        assert "flow_id" in result
        
        print("✅ kickoff() method compatibility confirmed")
        return True
        
    except Exception as e:
        print(f"❌ kickoff() compatibility test failed: {e}")
        return False

def test_metrics_integration():
    """Test FlowMetrics integration"""
    print("\n🧪 Testing metrics integration...")
    
    try:
        flow = AIWritingFlow()
        
        # Get initial metrics
        metrics = flow.get_flow_metrics()
        assert "flow_id" in metrics
        assert "current_kpis" in metrics
        assert "circuit_breaker_status" in metrics
        
        print("✅ Metrics integration working")
        print(f"   Active flows: {metrics['current_kpis']['active_flows']}")
        print(f"   Circuit breaker state: {metrics['circuit_breaker_status']['state']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Metrics integration test failed: {e}")
        return False

def test_factory_function():
    """Test factory function"""
    print("\n🧪 Testing factory function...")
    
    try:
        config = {
            "agents": {
                "content_analysis": {
                    "verbose": False,
                    "max_execution_time": 60
                }
            }
        }
        
        flow = create_ai_writing_flow(config)
        assert flow is not None
        assert flow.config["agents"]["content_analysis"]["verbose"] == False
        
        print("✅ Factory function working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Factory function test failed: {e}")
        return False

def run_all_tests():
    """Run all validation tests"""
    print("🚀 Starting AIWritingFlow Basic Validation Tests")
    print("=" * 60)
    
    tests = [
        test_flow_instantiation,
        test_input_validation,
        test_start_decorator,
        test_kickoff_compatibility,
        test_metrics_integration,
        test_factory_function
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! AIWritingFlow is ready for integration.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)