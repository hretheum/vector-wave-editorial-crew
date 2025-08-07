#!/usr/bin/env python3
"""
CrewAI Agent Integration Tests

Tests that demonstrate real-world usage of Knowledge Base tools
with actual CrewAI agents and crews.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_writing_flow.tools.enhanced_knowledge_tools import (
    search_crewai_knowledge,
    get_flow_examples,
    troubleshoot_crewai
)


class TestCrewAIAgentIntegration:
    """Test integration with actual CrewAI agents"""
    
    def test_research_agent_with_knowledge_tools(self):
        """Test a research agent using knowledge tools"""
        print("\n🤖 Testing Research Agent with Knowledge Tools...")
        
        try:
            from crewai import Agent, Task, Crew
            
            # Create research agent with knowledge tools
            researcher = Agent(
                role='CrewAI Research Specialist',
                goal='Research and provide comprehensive information about CrewAI topics',
                backstory='''You are an expert researcher specializing in CrewAI framework. 
                You have access to comprehensive knowledge tools and can provide detailed, 
                accurate information about CrewAI concepts, patterns, and troubleshooting.''',
                tools=[search_crewai_knowledge, get_flow_examples, troubleshoot_crewai],
                verbose=True
            )
            
            # Create research task
            research_task = Task(
                description='''Research CrewAI agent configuration patterns and provide:
                1. Basic agent setup patterns
                2. Common configuration options
                3. Best practices for agent design
                4. Troubleshooting tips for common agent issues
                
                Use the available knowledge tools to gather comprehensive information.''',
                agent=researcher,
                expected_output='''A comprehensive guide covering:
                - Agent configuration patterns with code examples
                - Best practices and recommendations
                - Common issues and troubleshooting steps'''
            )
            
            # Create and execute crew
            crew = Crew(
                agents=[researcher],
                tasks=[research_task],
                verbose=True
            )
            
            print("   Executing research crew...")
            result = crew.kickoff()
            
            print(f"   ✅ Crew execution completed")
            print(f"   Result length: {len(str(result))} characters")
            print(f"   Result preview: {str(result)[:300]}...")
            
            # Validate result
            result_str = str(result)
            assert len(result_str) > 500, "Result should be comprehensive"
            assert "agent" in result_str.lower(), "Should contain agent information"
            
            return result_str
            
        except ImportError:
            print("   ⚠️  CrewAI not available - skipping agent integration test")
            pytest.skip("CrewAI not installed")
    
    def test_multi_agent_knowledge_collaboration(self):
        """Test multiple agents collaborating with knowledge tools"""
        print("\n🤖 Testing Multi-Agent Knowledge Collaboration...")
        
        try:
            from crewai import Agent, Task, Crew
            
            # Create multiple specialized agents
            researcher = Agent(
                role='Technical Researcher',
                goal='Research CrewAI technical details and patterns',
                backstory='Expert at finding technical information and code patterns',
                tools=[search_crewai_knowledge, get_flow_examples],
                verbose=False
            )
            
            troubleshooter = Agent(
                role='Technical Support Specialist', 
                goal='Provide troubleshooting guidance and solutions',
                backstory='Expert at diagnosing and solving CrewAI issues',
                tools=[troubleshoot_crewai, search_crewai_knowledge],
                verbose=False
            )
            
            writer = Agent(
                role='Technical Writer',
                goal='Create comprehensive technical documentation',
                backstory='Expert at organizing technical information into clear guides',
                tools=[search_crewai_knowledge],
                verbose=False
            )
            
            # Create collaborative tasks
            research_task = Task(
                description='Research CrewAI agent creation patterns and gather technical details',
                agent=researcher,
                expected_output='Technical details about agent creation patterns'
            )
            
            troubleshooting_task = Task(
                description='Identify common CrewAI agent issues and provide solutions',
                agent=troubleshooter,
                expected_output='List of common issues and troubleshooting steps'
            )
            
            documentation_task = Task(
                description='''Create a comprehensive guide combining research and troubleshooting information.
                Include:
                1. Agent creation patterns from research
                2. Common issues and solutions from troubleshooting
                3. Best practices and recommendations''',
                agent=writer,
                expected_output='Comprehensive agent guide with patterns, troubleshooting, and best practices'
            )
            
            # Create collaborative crew
            crew = Crew(
                agents=[researcher, troubleshooter, writer],
                tasks=[research_task, troubleshooting_task, documentation_task],
                verbose=True
            )
            
            print("   Executing collaborative crew...")
            result = crew.kickoff()
            
            print(f"   ✅ Multi-agent collaboration completed")
            print(f"   Result length: {len(str(result))} characters")
            print(f"   Result preview: {str(result)[:300]}...")
            
            # Validate collaborative result
            result_str = str(result)
            assert len(result_str) > 800, "Collaborative result should be extensive"
            assert "agent" in result_str.lower(), "Should contain agent information"
            assert any(word in result_str.lower() for word in ["troubleshoot", "issue", "problem"]), "Should contain troubleshooting info"
            
            return result_str
            
        except ImportError:
            print("   ⚠️  CrewAI not available - skipping multi-agent test")
            pytest.skip("CrewAI not installed")
    
    def test_knowledge_tool_error_handling_in_agents(self):
        """Test how agents handle knowledge tool errors"""
        print("\n🤖 Testing Knowledge Tool Error Handling in Agents...")
        
        try:
            from crewai import Agent, Task, Crew
            
            # Create agent that might encounter tool errors
            robust_agent = Agent(
                role='Robust Researcher',
                goal='Research topics even when some tools might fail',
                backstory='Experienced researcher who handles tool failures gracefully',
                tools=[search_crewai_knowledge, get_flow_examples, troubleshoot_crewai],
                verbose=False
            )
            
            # Create task that might trigger tool errors
            error_handling_task = Task(
                description='''Try to research these topics, handling any tool errors gracefully:
                1. A very specific topic that might not exist
                2. An invalid flow example pattern
                3. An unknown troubleshooting issue type
                
                If tools fail, explain what happened and provide alternative approaches.''',
                agent=robust_agent,
                expected_output='Research results with graceful error handling'
            )
            
            crew = Crew(
                agents=[robust_agent],
                tasks=[error_handling_task],
                verbose=False
            )
            
            print("   Testing error handling...")
            result = crew.kickoff()
            
            print(f"   ✅ Error handling test completed")
            print(f"   Result length: {len(str(result))} characters")  
            print(f"   Result preview: {str(result)[:300]}...")
            
            # Should complete even with potential tool errors
            assert len(str(result)) > 100, "Should provide some result even with errors"
            
            return str(result)
            
        except ImportError:
            print("   ⚠️  CrewAI not available - skipping error handling test")
            pytest.skip("CrewAI not installed")
    
    def test_knowledge_tools_performance_in_crews(self):
        """Test knowledge tools performance when used in crews"""
        print("\n🤖 Testing Knowledge Tools Performance in Crews...")
        
        try:
            from crewai import Agent, Task, Crew
            import time
            
            # Create performance-focused agent
            fast_researcher = Agent(
                role='Fast Researcher',
                goal='Quickly research multiple topics efficiently',
                backstory='Expert at efficiently gathering information using available tools',
                tools=[search_crewai_knowledge],
                verbose=False
            )
            
            # Create multiple quick research tasks
            tasks = []
            topics = [
                "CrewAI agent basics",
                "task orchestration",
                "crew configuration", 
                "tool integration"
            ]
            
            for i, topic in enumerate(topics):
                task = Task(
                    description=f'Quickly research "{topic}" and provide key points',
                    agent=fast_researcher,
                    expected_output=f'Key information about {topic}'
                )
                tasks.append(task)
            
            crew = Crew(
                agents=[fast_researcher],
                tasks=tasks,
                verbose=False
            )
            
            print(f"   Testing performance with {len(tasks)} research tasks...")
            start_time = time.time()
            
            result = crew.kickoff()
            
            end_time = time.time()
            total_time = end_time - start_time
            
            print(f"   ✅ Performance test completed")
            print(f"   Total time: {total_time:.2f} seconds")
            print(f"   Average per task: {total_time/len(tasks):.2f} seconds")
            print(f"   Result length: {len(str(result))} characters")
            
            # Performance should be reasonable
            assert total_time < 60, f"Total time {total_time:.2f}s too slow for {len(tasks)} tasks"
            assert len(str(result)) > 200, "Should have substantial results"
            
            return {
                "total_time": total_time,
                "avg_time_per_task": total_time / len(tasks),
                "result_length": len(str(result))
            }
            
        except ImportError:
            print("   ⚠️  CrewAI not available - skipping performance test")
            pytest.skip("CrewAI not installed")


class TestRealWorldScenarios:
    """Test real-world usage scenarios"""
    
    def test_content_creation_workflow(self):
        """Test a content creation workflow using knowledge tools"""
        print("\n📝 Testing Content Creation Workflow...")
        
        try:
            from crewai import Agent, Task, Crew
            
            # Content creation agents
            researcher = Agent(
                role='Content Researcher',
                goal='Research CrewAI topics for content creation',
                backstory='Expert at gathering comprehensive information for content',
                tools=[search_crewai_knowledge, get_flow_examples],
                verbose=False
            )
            
            creator = Agent(
                role='Content Creator', 
                goal='Create engaging content based on research',
                backstory='Expert at creating technical content and tutorials',
                tools=[search_crewai_knowledge],
                verbose=False
            )
            
            # Content creation tasks
            research_task = Task(
                description='''Research CrewAI agent patterns for a beginner tutorial:
                1. Basic agent concepts
                2. Simple agent creation examples
                3. Common agent configuration options''',
                agent=researcher,
                expected_output='Research materials for beginner tutorial'
            )
            
            creation_task = Task(
                description='''Create a beginner-friendly tutorial about CrewAI agents based on the research.
                Include:
                1. Clear explanations of concepts
                2. Code examples
                3. Step-by-step instructions''',
                agent=creator,
                expected_output='Complete beginner tutorial for CrewAI agents'
            )
            
            crew = Crew(
                agents=[researcher, creator],
                tasks=[research_task, creation_task],
                verbose=False
            )
            
            print("   Creating tutorial content...")
            result = crew.kickoff()
            
            print(f"   ✅ Content creation completed")
            print(f"   Tutorial length: {len(str(result))} characters")
            print(f"   Preview: {str(result)[:200]}...")
            
            # Validate tutorial content
            result_str = str(result)
            assert len(result_str) > 600, "Tutorial should be comprehensive"
            assert "agent" in result_str.lower(), "Should explain agents"
            assert any(word in result_str for word in ["example", "code", "```"]), "Should include examples"
            
            return result_str
            
        except ImportError:
            print("   ⚠️  CrewAI not available - skipping content creation test")
            pytest.skip("CrewAI not installed")
    
    def test_technical_support_workflow(self):
        """Test a technical support workflow"""
        print("\n🛠️ Testing Technical Support Workflow...")
        
        try:
            from crewai import Agent, Task, Crew
            
            # Support agents
            diagnostician = Agent(
                role='Technical Diagnostician',
                goal='Diagnose CrewAI technical issues',
                backstory='Expert at identifying and analyzing technical problems',
                tools=[troubleshoot_crewai, search_crewai_knowledge],
                verbose=False
            )
            
            solution_provider = Agent(
                role='Solution Provider',
                goal='Provide solutions and workarounds for technical issues',
                backstory='Expert at finding and implementing solutions',
                tools=[search_crewai_knowledge, get_flow_examples],
                verbose=False
            )
            
            # Support tasks
            diagnosis_task = Task(
                description='''Diagnose common CrewAI issues:
                1. Installation problems
                2. Memory issues
                3. Agent configuration errors''',
                agent=diagnostician,
                expected_output='Diagnosis of common issues with symptoms and causes'
            )
            
            solution_task = Task(
                description='''Provide solutions for the diagnosed issues:
                1. Step-by-step solution guides
                2. Code examples where applicable
                3. Prevention tips''',
                agent=solution_provider,
                expected_output='Complete solution guide for common issues'
            )
            
            crew = Crew(
                agents=[diagnostician, solution_provider],
                tasks=[diagnosis_task, solution_task],
                verbose=False
            )
            
            print("   Providing technical support...")
            result = crew.kickoff()
            
            print(f"   ✅ Technical support completed")
            print(f"   Support guide length: {len(str(result))} characters")
            print(f"   Preview: {str(result)[:200]}...")
            
            # Validate support content
            result_str = str(result)
            assert len(result_str) > 400, "Support guide should be detailed"
            assert any(word in result_str.lower() for word in ["issue", "problem", "solution"]), "Should address issues"
            assert any(word in result_str.lower() for word in ["install", "memory"]), "Should cover common problems"
            
            return result_str
            
        except ImportError:
            print("   ⚠️  CrewAI not available - skipping technical support test")
            pytest.skip("CrewAI not installed")


def run_all_agent_tests():
    """Run all agent integration tests and generate report"""
    print("🤖 Starting CrewAI Agent Integration Tests...")
    print("=" * 60)
    
    test_results = {}
    
    # Run integration tests
    integration_tests = TestCrewAIAgentIntegration()
    
    test_methods = [
        "test_research_agent_with_knowledge_tools",
        "test_multi_agent_knowledge_collaboration", 
        "test_knowledge_tool_error_handling_in_agents",
        "test_knowledge_tools_performance_in_crews"
    ]
    
    for method_name in test_methods:
        try:
            method = getattr(integration_tests, method_name)
            result = method()
            test_results[method_name] = {"status": "PASSED", "result": result}
            print(f"✅ {method_name} PASSED")
        except Exception as e:
            test_results[method_name] = {"status": "FAILED", "error": str(e)}
            print(f"❌ {method_name} FAILED: {e}")
    
    # Run real-world scenario tests
    scenario_tests = TestRealWorldScenarios()
    
    scenario_methods = [
        "test_content_creation_workflow",
        "test_technical_support_workflow"
    ]
    
    for method_name in scenario_methods:
        try:
            method = getattr(scenario_tests, method_name)
            result = method()
            test_results[method_name] = {"status": "PASSED", "result": result}
            print(f"✅ {method_name} PASSED")
        except Exception as e:
            test_results[method_name] = {"status": "FAILED", "error": str(e)}
            print(f"❌ {method_name} FAILED: {e}")
    
    # Generate report
    print("\n" + "="*60)
    print("📋 CREWAI AGENT INTEGRATION TEST REPORT")
    print("="*60)
    
    passed_tests = sum(1 for result in test_results.values() if result["status"] == "PASSED")
    total_tests = len(test_results)
    
    print(f"\n📊 TEST SUMMARY:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {passed_tests}")
    print(f"   Failed: {total_tests - passed_tests}")
    print(f"   Success Rate: {passed_tests/total_tests*100:.1f}%")
    
    print(f"\n🔧 TESTED SCENARIOS:")
    print(f"   ✅ Single Agent with Knowledge Tools")
    print(f"   ✅ Multi-Agent Collaboration")
    print(f"   ✅ Error Handling in Agents")
    print(f"   ✅ Performance Testing")
    print(f"   ✅ Content Creation Workflow")
    print(f"   ✅ Technical Support Workflow")
    
    print(f"\n🎯 INTEGRATION STATUS:")
    if passed_tests == total_tests:
        print(f"   🎉 ALL TESTS PASSED - CrewAI Integration Ready!")
    else:
        print(f"   ⚠️  Some tests failed - Review integration setup")
    
    print("="*60)
    
    return test_results


if __name__ == "__main__":
    run_all_agent_tests()