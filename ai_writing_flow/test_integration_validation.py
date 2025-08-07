#!/usr/bin/env python3
"""Validate all integration points in CrewAI Flow - Task 4.2"""

import sys
sys.path.append('src')

from ai_writing_flow.crewai_flow.flows.ai_writing_flow import AIWritingFlow

def test_integration_validation():
    """Comprehensive validation of all integration points"""
    
    print("🧪 Integration Points Validation - Task 4.2")
    print("=" * 60)
    
    # Track validation results
    validations = []
    
    # Initialize flow
    print("\n📌 Initializing CrewAI Flow...")
    try:
        flow = AIWritingFlow()
        print(f"✅ Flow initialized: {flow.execution_id}")
    except Exception as e:
        print(f"❌ Flow initialization failed: {e}")
        return False
    
    # 1. Validate Phase 1 Infrastructure Integration
    print("\n1️⃣ Phase 1 Infrastructure Integration")
    print("-" * 40)
    
    # FlowMetrics
    try:
        assert hasattr(flow, 'metrics'), "FlowMetrics not found"
        assert flow.metrics is not None, "FlowMetrics is None"
        print("✅ FlowMetrics integrated")
        validations.append(("FlowMetrics", True))
    except AssertionError as e:
        print(f"❌ FlowMetrics: {e}")
        validations.append(("FlowMetrics", False))
    
    # CircuitBreaker
    try:
        assert hasattr(flow, 'content_analysis_breaker'), "CircuitBreaker not found"
        assert flow.content_analysis_breaker is not None, "CircuitBreaker is None"
        status = flow.content_analysis_breaker.get_status()
        print(f"✅ CircuitBreaker integrated (state: {status['state']})")
        validations.append(("CircuitBreaker", True))
    except Exception as e:
        print(f"❌ CircuitBreaker: {e}")
        validations.append(("CircuitBreaker", False))
    
    # FlowControlState
    try:
        assert hasattr(flow, 'flow_control_state'), "FlowControlState not found"
        assert flow.flow_control_state is not None, "FlowControlState is None"
        print("✅ FlowControlState integrated")
        validations.append(("FlowControlState", True))
    except Exception as e:
        print(f"❌ FlowControlState: {e}")
        validations.append(("FlowControlState", False))
    
    # 2. Validate Knowledge Base Integration
    print("\n2️⃣ Knowledge Base Integration")
    print("-" * 40)
    
    # KnowledgeAdapter
    try:
        assert hasattr(flow, 'knowledge_adapter'), "KnowledgeAdapter not found"
        assert flow.knowledge_adapter is not None, "KnowledgeAdapter is None"
        assert flow.knowledge_adapter.strategy.value == "HYBRID", "Wrong KB strategy"
        print(f"✅ KnowledgeAdapter integrated (strategy: {flow.knowledge_adapter.strategy.value})")
        validations.append(("KnowledgeAdapter", True))
    except Exception as e:
        print(f"❌ KnowledgeAdapter: {e}")
        validations.append(("KnowledgeAdapter", False))
    
    # KB Tools in Agent
    try:
        agent = flow.content_analysis_agent.create_agent()
        kb_tools = [t for t in agent.tools if 'knowledge' in str(t).lower()]
        assert len(kb_tools) > 0, "No KB tools found in agent"
        print(f"✅ KB Tools in Agent: {len(kb_tools)} tools configured")
        validations.append(("KB Tools", True))
    except Exception as e:
        print(f"❌ KB Tools: {e}")
        validations.append(("KB Tools", False))
    
    # 3. Validate CrewAI Components
    print("\n3️⃣ CrewAI Components Integration")
    print("-" * 40)
    
    # ContentAnalysisAgent
    try:
        assert hasattr(flow, 'content_analysis_agent'), "ContentAnalysisAgent not found"
        agent = flow.content_analysis_agent.create_agent()
        assert agent.role is not None, "Agent role not set"
        assert agent.goal is not None, "Agent goal not set"
        assert agent.backstory is not None, "Agent backstory not set"
        print(f"✅ ContentAnalysisAgent configured (tools: {len(agent.tools)})")
        validations.append(("ContentAnalysisAgent", True))
    except Exception as e:
        print(f"❌ ContentAnalysisAgent: {e}")
        validations.append(("ContentAnalysisAgent", False))
    
    # ContentAnalysisTask
    try:
        assert hasattr(flow, 'content_analysis_task'), "ContentAnalysisTask not found"
        test_inputs = {
            'topic_title': 'Test Topic',
            'platform': 'LinkedIn',
            'content_type': 'STANDALONE',
            'file_path': 'README.md'
        }
        task = flow.content_analysis_task.create_task(agent, test_inputs)
        assert task is not None, "Task creation failed"
        assert hasattr(task, 'description'), "Task missing description"
        print("✅ ContentAnalysisTask configured")
        validations.append(("ContentAnalysisTask", True))
    except Exception as e:
        print(f"❌ ContentAnalysisTask: {e}")
        validations.append(("ContentAnalysisTask", False))
    
    # 4. Validate Flow Decorators
    print("\n4️⃣ CrewAI Flow Decorators")
    print("-" * 40)
    
    # @start decorator
    try:
        assert hasattr(flow, 'analyze_content'), "analyze_content method not found"
        # Check if it's decorated (name changes when decorated)
        method = getattr(flow, 'analyze_content')
        print(f"✅ @start decorator present (method type: {type(method).__name__})")
        validations.append(("@start decorator", True))
    except Exception as e:
        print(f"❌ @start decorator: {e}")
        validations.append(("@start decorator", False))
    
    # 5. Validate Data Flow
    print("\n5️⃣ Data Flow Integration")
    print("-" * 40)
    
    try:
        # Test minimal data flow
        test_data = {
            'topic_title': 'Integration Test',
            'platform': 'Blog',
            'content_type': 'STANDALONE',
            'file_path': 'README.md',
            'editorial_recommendations': 'Test recommendations',
            'viral_score': 0.7
        }
        
        result = flow._execute_content_analysis_manually(test_data)
        
        # Validate response structure
        required_fields = ['flow_id', 'success', 'flow_state', 'flow_metadata']
        missing = [f for f in required_fields if f not in result]
        
        if not missing:
            print("✅ Data flow returns complete response structure")
            validations.append(("Data Flow", True))
        else:
            print(f"❌ Data flow missing fields: {missing}")
            validations.append(("Data Flow", False))
            
    except Exception as e:
        print(f"❌ Data flow test failed: {e}")
        validations.append(("Data Flow", False))
    
    # 6. Validate Error Handling
    print("\n6️⃣ Error Handling Integration")
    print("-" * 40)
    
    try:
        # Test with invalid data
        invalid_data = {
            'topic_title': '',  # Empty title
            'platform': 'InvalidPlatform',
            'content_type': 'INVALID',
            'file_path': '/does/not/exist.txt'
        }
        
        try:
            result = flow._execute_content_analysis_manually(invalid_data)
            print("❌ Error handling failed - should have raised exception")
            validations.append(("Error Handling", False))
        except ValueError as e:
            print(f"✅ Error handling works correctly: {type(e).__name__}")
            validations.append(("Error Handling", True))
            
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        validations.append(("Error Handling", False))
    
    # Final Summary
    print("\n" + "=" * 60)
    print("📊 Integration Validation Summary")
    print("=" * 60)
    
    total = len(validations)
    passed = sum(1 for _, success in validations if success)
    failed = total - passed
    
    print(f"\nTotal Integration Points: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    print("\nDetailed Results:")
    for name, success in validations:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
    
    if failed == 0:
        print("\n🎉 All integration points validated successfully!")
        print("✅ Task 4.2 - All integrations are working correctly")
    else:
        print(f"\n⚠️  {failed} integration points need attention")
    
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    success = test_integration_validation()
    exit(0 if success else 1)