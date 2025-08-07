#!/usr/bin/env python3
"""Test ContentAnalysisAgent functionality - Task 2.2 validation"""

import sys
import time
sys.path.append('src')

from ai_writing_flow.crewai_flow.agents.content_analysis_agent import ContentAnalysisAgent
from ai_writing_flow.crewai_flow.tasks.content_analysis_task import ContentAnalysisTask
from ai_writing_flow.models import ContentAnalysisResult

def test_content_analysis_agent():
    """Comprehensive test of ContentAnalysisAgent with KB integration"""
    
    print("🧪 Testing ContentAnalysisAgent - Task 2.2")
    print("=" * 60)
    
    # Test 1: Agent initialization
    print("\n1️⃣ Testing agent initialization...")
    try:
        agent = ContentAnalysisAgent()
        print("✅ Agent initialized successfully")
        
        info = agent.get_agent_info()
        print(f"✅ Version: {info['version']}")
        print(f"✅ KB integration enabled: {info['kb_integration']}")
        print(f"✅ Circuit breaker enabled: {info['circuit_breaker']}")
        print(f"✅ Tools count: {info['tools_count']}")
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
    except Exception as e:
        print(f"❌ CrewAI agent creation failed: {e}")
        return False
    
    # Test 3: Content requirements analysis
    print("\n3️⃣ Testing content requirements analysis...")
    try:
        test_inputs = {
            'topic_title': 'Building AI Agents with CrewAI: Best Practices',
            'platform': 'LinkedIn',
            'content_type': 'STANDALONE',
            'file_path': 'example_content.md',
            'editorial_recommendations': 'Focus on practical implementation tips',
            'viral_score': 0.8
        }
        
        start_time = time.time()
        analysis_result = agent.analyze_content_requirements(test_inputs)
        processing_time = time.time() - start_time
        
        print(f"✅ Analysis completed in {processing_time:.2f}s")
        print(f"✅ Content type: {analysis_result['content_type']}")
        print(f"✅ Viral score: {analysis_result['viral_score']}")
        print(f"✅ Complexity: {analysis_result['complexity_level']}")
        print(f"✅ Recommended flow: {analysis_result['recommended_flow_path']}")
        print(f"✅ KB available: {analysis_result['kb_available']}")
        print(f"✅ Key themes: {analysis_result['key_themes']}")
    except Exception as e:
        print(f"❌ Content analysis failed: {e}")
        return False
    
    # Test 4: Task creation integration
    print("\n4️⃣ Testing task creation integration...")
    try:
        task_creator = ContentAnalysisTask()
        task = task_creator.create_task(crewai_agent, test_inputs)
        print(f"✅ Task created successfully")
        print(f"✅ Task description length: {len(task.description)} chars")
        print(f"✅ Output model: ContentAnalysisResult")
        print(f"✅ Tools assigned: {len(task.tools)}")
    except Exception as e:
        print(f"❌ Task creation failed: {e}")
        return False
    
    # Test 5: Agent performance metrics
    print("\n5️⃣ Testing performance metrics...")
    try:
        # Update metrics
        agent.update_metrics(processing_time, kb_queries=3)
        
        # Get updated info
        updated_info = agent.get_agent_info()
        metrics = updated_info['metrics']
        
        print(f"✅ Analysis count: {metrics['analysis_count']}")
        print(f"✅ Total processing time: {metrics['total_processing_time']:.2f}s")
        print(f"✅ Average processing time: {metrics['average_processing_time']:.2f}s")
        print(f"✅ KB query count: {metrics['kb_query_count']}")
    except Exception as e:
        print(f"❌ Metrics update failed: {e}")
        return False
    
    # Test 6: Role, Goal, Backstory validation
    print("\n6️⃣ Testing agent configuration...")
    try:
        print(f"✅ Role length: {len(crewai_agent.role)} chars")
        print(f"✅ Goal length: {len(crewai_agent.goal)} chars")
        print(f"✅ Backstory length: {len(crewai_agent.backstory)} chars")
        
        # Verify content
        assert "CrewAI Flow Expertise" in crewai_agent.role
        assert "Knowledge Base insights" in crewai_agent.goal
        assert "CrewAI Flow Specialization" in crewai_agent.backstory
        print("✅ All agent configuration strings properly set")
    except Exception as e:
        print(f"❌ Agent configuration validation failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All ContentAnalysisAgent tests passed!")
    print("✅ Task 2.2 implementation is complete and functional")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_content_analysis_agent()
    exit(0 if success else 1)