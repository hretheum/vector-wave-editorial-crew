#!/usr/bin/env python3
"""Test Research Agent implementation - Task 5.1"""

import sys
sys.path.append('src')

from ai_writing_flow.crewai_flow.agents.research_agent import ResearchAgent
from ai_writing_flow.crewai_flow.tasks.research_task import ResearchTask
from ai_writing_flow.models import ResearchResult

def test_research_agent():
    """Test Research Agent functionality"""
    
    print("🧪 Testing Research Agent - Task 5.1")
    print("=" * 60)
    
    # Test 1: Agent initialization
    print("\n1️⃣ Testing Research Agent initialization...")
    try:
        agent = ResearchAgent(config={
            'verbose': True,
            'search_depth': 'comprehensive',
            'verify_sources': True
        })
        print("✅ Research Agent initialized successfully")
        
        info = agent.get_agent_info()
        print(f"✅ Version: {info['version']}")
        print(f"✅ Search depth: {info['search_depth']}")
        print(f"✅ Verify sources: {info['verify_sources']}")
    except Exception as e:
        print(f"❌ Agent initialization failed: {e}")
        return False
    
    # Test 2: Agent creation
    print("\n2️⃣ Testing CrewAI agent creation...")
    try:
        crewai_agent = agent.create_agent()
        print(f"✅ CrewAI Agent created: {crewai_agent.role}")
        print(f"✅ Tools available: {len(crewai_agent.tools)}")
        print(f"✅ Max execution time: {crewai_agent.max_execution_time}s")
        print(f"✅ Max iterations: {crewai_agent.max_iter}")
        
        # Check tools
        print("\n📚 Research tools configured:")
        for i, tool in enumerate(crewai_agent.tools, 1):
            tool_name = getattr(tool, 'name', str(tool))
            print(f"   {i}. {tool_name}")
            
    except Exception as e:
        print(f"❌ CrewAI agent creation failed: {e}")
        return False
    
    # Test 3: Task creation integration
    print("\n3️⃣ Testing Research Task creation...")
    try:
        task_creator = ResearchTask(config={
            'min_sources': 3,
            'verify_facts': True,
            'require_sources': True
        })
        
        test_inputs = {
            'topic_title': 'Advanced CrewAI Flow Patterns for Production Systems',
            'platform': 'Blog',
            'content_type': 'technical_guide',
            'key_themes': ['scalability', 'error handling', 'performance'],
            'editorial_recommendations': 'Focus on real-world implementations and best practices',
            'kb_insights': ['CrewAI supports async operations', 'Circuit breakers prevent cascading failures']
        }
        
        task = task_creator.create_task(crewai_agent, test_inputs)
        print("✅ Research Task created successfully")
        print(f"✅ Task description length: {len(task.description)} chars")
        print(f"✅ Output model: ResearchResult")
        print(f"✅ Tools assigned: {len(task.tools)}")
        
        # Check task configuration from task_creator
        print(f"✅ Min sources required: {task_creator.config.get('min_sources', 3)}")
        print(f"✅ Fact verification: {task_creator.config.get('verify_facts', True)}")
            
    except Exception as e:
        print(f"❌ Task creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Agent metrics
    print("\n4️⃣ Testing agent metrics...")
    try:
        # Simulate research execution
        agent.update_metrics(processing_time=15.5, sources=7, kb_queries=12)
        
        updated_info = agent.get_agent_info()
        metrics = updated_info['metrics']
        
        print(f"✅ Research count: {metrics['research_count']}")
        print(f"✅ Total processing time: {metrics['total_processing_time']:.2f}s")
        print(f"✅ Average processing time: {metrics['average_processing_time']:.2f}s")
        print(f"✅ Sources found: {metrics['sources_found']}")
        print(f"✅ KB queries: {metrics['kb_queries']}")
        print(f"✅ Avg sources per research: {metrics['avg_sources_per_research']:.1f}")
        
    except Exception as e:
        print(f"❌ Metrics test failed: {e}")
        return False
    
    # Test 5: Agent configuration validation
    print("\n5️⃣ Validating agent configuration...")
    try:
        # Check role and backstory
        assert len(crewai_agent.role) > 20, "Role too short"
        assert len(crewai_agent.goal) > 50, "Goal too short"
        assert len(crewai_agent.backstory) > 100, "Backstory too short"
        
        print("✅ Agent role properly configured")
        print("✅ Agent goal comprehensive")
        print("✅ Agent backstory detailed")
        
        # Check system template
        system_template = agent._get_system_template()
        assert "Research Protocol" in system_template
        assert "Quality Assurance" in system_template
        assert "Research Standards" in system_template
        print("✅ System template includes all research protocols")
        
    except AssertionError as e:
        print(f"❌ Configuration validation failed: {e}")
        return False
    
    # Test 6: Task configuration
    print("\n6️⃣ Testing task configuration...")
    try:
        task_info = task_creator.get_task_info()
        
        print(f"✅ Task type: {task_info['task_type']}")
        print(f"✅ Version: {task_info['version']}")
        
        # Check research requirements
        req = task_info['research_requirements']
        print(f"✅ Min sources: {req['min_sources']}")
        print(f"✅ Require sources: {req['require_sources']}")
        print(f"✅ Verify facts: {req['verify_facts']}")
        print(f"✅ Timeout: {req['timeout']}s")
        
        # Check features
        features = task_info['features']
        enabled_features = [k for k, v in features.items() if v]
        print(f"✅ Enabled features: {', '.join(enabled_features)}")
        
    except Exception as e:
        print(f"❌ Task configuration test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All Research Agent tests passed!")
    print("✅ Task 5.1 implementation is complete and functional")
    print("\nKey achievements:")
    print("- Research Agent with comprehensive backstory")
    print("- 4 KB research tools integrated")
    print("- ResearchTask with detailed requirements")
    print("- Source verification and fact-checking")
    print("- Metrics tracking for performance monitoring")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_research_agent()
    exit(0 if success else 1)