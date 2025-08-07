"""
Test Enhanced Content Analysis Agent (Task 2.2)

Comprehensive test suite for the enhanced ContentAnalysisAgent
with Knowledge Base integration, viral scoring, and CrewAI flow routing.
"""

import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Test imports
from src.ai_writing_flow.crewai_flow.agents.content_analysis_agent import ContentAnalysisAgent
from src.ai_writing_flow.crewai_flow.tasks.content_analysis_task import ContentAnalysisTask
from src.ai_writing_flow.models import ContentAnalysisResult


class TestEnhancedContentAnalysisAgent:
    """Test suite for Enhanced Content Analysis Agent"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.agent_config = {
            'verbose': True,
            'max_iter': 3,
            'max_execution_time': 180,
            'kb_integration': True,
            'circuit_breaker': True
        }
        
        self.test_inputs = {
            'topic_title': 'Advanced CrewAI Flow Patterns for AI Content Generation',
            'platform': 'LinkedIn',
            'content_type': 'STANDALONE',
            'file_path': '/path/to/source/file.md',
            'editorial_recommendations': 'Focus on technical depth and practical examples'
        }
    
    def test_agent_initialization(self):
        """Test agent initialization with enhanced configuration"""
        agent = ContentAnalysisAgent(self.agent_config)
        
        # Verify configuration
        assert agent.config['verbose'] is True
        assert agent.config['max_execution_time'] == 180
        assert agent.config['kb_integration'] is True
        assert agent.config['circuit_breaker'] is True
        
        # Verify metrics initialization
        assert agent.analysis_count == 0
        assert agent.total_processing_time == 0.0
        assert agent.kb_query_count == 0
        
        print("✅ Agent initialization test passed")
    
    def test_agent_info(self):
        """Test agent info retrieval"""
        agent = ContentAnalysisAgent(self.agent_config)
        info = agent.get_agent_info()
        
        # Verify info structure
        assert info['role'] == "Content Analysis Specialist with CrewAI Flow Expertise"
        assert info['version'] == "2.2_enhanced"
        assert 'metrics' in info
        assert 'status' in info
        assert 'config' in info
        
        # Verify metrics structure
        metrics = info['metrics']
        assert 'analysis_count' in metrics
        assert 'total_processing_time' in metrics
        assert 'average_processing_time' in metrics
        assert 'kb_query_count' in metrics
        
        print("✅ Agent info test passed")
    
    def test_content_requirements_analysis(self):
        """Test standalone content requirements analysis"""
        agent = ContentAnalysisAgent(self.agent_config)
        
        # Perform analysis
        start_time = time.time()
        result = agent.analyze_content_requirements(self.test_inputs)
        processing_time = time.time() - start_time
        
        # Verify result structure
        assert isinstance(result, dict)
        
        # Verify required fields
        required_fields = [
            'content_type', 'viral_score', 'complexity_level', 
            'recommended_flow_path', 'target_platform', 
            'analysis_confidence', 'processing_time'
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        # Verify field types and values
        assert isinstance(result['viral_score'], float)
        assert 0.0 <= result['viral_score'] <= 1.0
        assert result['complexity_level'] in ['beginner', 'intermediate', 'advanced']
        assert isinstance(result['processing_time'], float)
        assert result['processing_time'] > 0
        assert result['target_platform'] == 'LinkedIn'
        
        # Verify content classification
        assert 'crewai' in result['content_type'].lower() or 'technical' in result['content_type'].lower()
        
        print(f"✅ Content analysis test passed - Processing time: {result['processing_time']:.3f}s")
        print(f"   Content type: {result['content_type']}")
        print(f"   Viral score: {result['viral_score']:.2f}")
        print(f"   Complexity: {result['complexity_level']}")
        print(f"   Flow path: {result['recommended_flow_path']}")
    
    def test_viral_score_calculation(self):
        """Test viral score calculation logic"""
        agent = ContentAnalysisAgent(self.agent_config)
        
        # Test viral keywords
        viral_title = "The Secret Truth About AI That Nobody Tells You"
        viral_score = agent._calculate_viral_score(viral_title, "Twitter")
        assert viral_score > 0.6  # Should get bonus for viral keywords and Twitter
        
        # Test regular title
        regular_title = "Basic Introduction to Machine Learning"
        regular_score = agent._calculate_viral_score(regular_title, "LinkedIn")
        assert 0.4 <= regular_score <= 0.6  # Should be moderate
        
        print(f"✅ Viral scoring test passed")
        print(f"   Viral title score: {viral_score:.2f}")
        print(f"   Regular title score: {regular_score:.2f}")
    
    def test_complexity_assessment(self):
        """Test complexity level assessment"""
        agent = ContentAnalysisAgent(self.agent_config)
        
        # Test different complexity levels
        test_cases = [
            ("Beginner's Guide to AI", "beginner", "STANDALONE"),
            ("Advanced Neural Network Architecture", "advanced", "STANDALONE"),
            ("Machine Learning Tutorial", "intermediate", "STANDALONE")
        ]
        
        for title, expected_complexity, content_type in test_cases:
            complexity = agent._assess_complexity(title, content_type)
            assert complexity == expected_complexity, f"Expected {expected_complexity}, got {complexity} for '{title}'"
        
        print("✅ Complexity assessment test passed")
    
    def test_flow_path_recommendation(self):
        """Test CrewAI flow path recommendations"""
        agent = ContentAnalysisAgent(self.agent_config)
        
        # Test different flow paths
        test_cases = [
            ("SERIES", "LinkedIn", "multi_part_content_flow"),
            ("STANDALONE", "Twitter", "twitter_thread_flow"),
            ("STANDALONE", "LinkedIn", "linkedin_post_flow"),
            ("STANDALONE", "Medium", "standard_content_flow")
        ]
        
        for content_type, platform, expected_flow in test_cases:
            flow_path = agent._recommend_flow_path(content_type, platform)
            assert flow_path == expected_flow, f"Expected {expected_flow}, got {flow_path}"
        
        print("✅ Flow path recommendation test passed")
    
    def test_metrics_tracking(self):
        """Test performance metrics tracking"""
        agent = ContentAnalysisAgent(self.agent_config)
        
        # Initial state
        assert agent.analysis_count == 0
        assert agent.total_processing_time == 0.0
        
        # Update metrics
        agent.update_metrics(1.5, kb_queries=3)
        assert agent.analysis_count == 1
        assert agent.total_processing_time == 1.5
        assert agent.kb_query_count == 3
        
        # Update again
        agent.update_metrics(2.0, kb_queries=2)
        assert agent.analysis_count == 2
        assert agent.total_processing_time == 3.5
        assert agent.kb_query_count == 5
        
        # Check average calculation
        info = agent.get_agent_info()
        assert info['metrics']['average_processing_time'] == 1.75
        
        print("✅ Metrics tracking test passed")
    
    @patch('src.ai_writing_flow.crewai_flow.tools.crewai_knowledge_tools.enhanced_knowledge_search')
    def test_knowledge_tools_loading(self, mock_search):
        """Test Knowledge Base tools loading"""
        # Test with KB integration enabled
        agent = ContentAnalysisAgent({'kb_integration': True})
        tools = agent._get_agent_tools()
        assert len(tools) > 0  # Should have KB tools
        
        # Test with KB integration disabled
        agent_no_kb = ContentAnalysisAgent({'kb_integration': False})
        tools_no_kb = agent_no_kb._get_agent_tools()
        assert len(tools_no_kb) == 0  # Should have no tools
        
        print("✅ Knowledge tools loading test passed")
    
    def test_crewai_agent_creation(self):
        """Test CrewAI Agent creation"""
        agent = ContentAnalysisAgent(self.agent_config)
        crewai_agent = agent.create_agent()
        
        # Verify agent properties
        assert hasattr(crewai_agent, 'role')
        assert hasattr(crewai_agent, 'goal')
        assert hasattr(crewai_agent, 'backstory')
        assert "Content Analysis Specialist" in crewai_agent.role
        assert "CrewAI Flow" in crewai_agent.role
        
        # Test agent property
        same_agent = agent.agent
        assert crewai_agent is same_agent  # Should return same instance
        
        print("✅ CrewAI Agent creation test passed")


class TestEnhancedContentAnalysisTask:
    """Test suite for Enhanced Content Analysis Task"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.task_config = {
            'timeout': 60,
            'retry_count': 3,
            'use_new_model': True,
            'async_execution': False,
            'human_input': False
        }
        
        self.test_inputs = {
            'topic_title': 'Advanced CrewAI Flow Patterns',
            'platform': 'LinkedIn',
            'content_type': 'STANDALONE',
            'editorial_recommendations': 'Focus on practical examples'
        }
    
    def test_task_initialization(self):
        """Test task initialization with enhanced configuration"""
        task = ContentAnalysisTask(self.task_config)
        
        # Verify configuration
        assert task.config['timeout'] == 60
        assert task.config['retry_count'] == 3
        assert task.config['use_new_model'] is True
        assert task.config['async_execution'] is False
        
        print("✅ Task initialization test passed")
    
    def test_task_info(self):
        """Test task info retrieval"""
        task = ContentAnalysisTask(self.task_config)
        info = task.get_task_info()
        
        # Verify info structure
        assert info['task_type'] == "content_analysis"
        assert info['version'] == "2.2_enhanced"
        assert info['output_format'] == "ContentAnalysisResult"
        assert 'features' in info
        
        # Verify features
        features = info['features']
        assert features['kb_integration'] is True
        assert features['viral_scoring'] is True
        assert features['flow_routing'] is True
        
        print("✅ Task info test passed")
    
    def test_task_creation_with_mock_agent(self):
        """Test task creation with mock agent"""
        task = ContentAnalysisTask(self.task_config)
        
        # Create mock agent
        mock_agent = Mock()
        mock_agent.role = "Test Agent"
        mock_agent.tools = []
        
        # Create task
        crewai_task = task.create_task(mock_agent, self.test_inputs)
        
        # Verify task properties
        assert hasattr(crewai_task, 'description')
        assert hasattr(crewai_task, 'agent')
        assert hasattr(crewai_task, 'expected_output')
        
        print("✅ Task creation test passed")
    
    def test_task_description_building(self):
        """Test task description building"""
        task = ContentAnalysisTask(self.task_config)
        description = task._build_task_description(self.test_inputs)
        
        # Verify description contains key information
        assert "Advanced CrewAI Flow Patterns" in description
        assert "LinkedIn" in description
        assert "STANDALONE" in description
        assert "Focus on practical examples" in description
        
        # Verify description structure
        assert "Content Classification" in description
        assert "Platform Optimization" in description
        assert "Audience Analysis" in description
        assert "Content Strategy" in description
        
        print("✅ Task description building test passed")
    
    def test_expected_output_description(self):
        """Test expected output description for new model"""
        task = ContentAnalysisTask({'use_new_model': True})
        output_desc = task._get_expected_output_description()
        
        # Verify new model fields are mentioned
        assert "ContentAnalysisResult" in output_desc
        assert "viral_score" in output_desc
        assert "recommended_flow_path" in output_desc
        assert "kb_insights" in output_desc
        assert "Knowledge Base Integration" in output_desc
        
        print("✅ Expected output description test passed")
    
    def test_legacy_model_compatibility(self):
        """Test backward compatibility with legacy model"""
        task = ContentAnalysisTask({'use_new_model': False})
        info = task.get_task_info()
        
        assert info['output_format'] == "ContentAnalysisOutput"
        assert info['features']['viral_scoring'] is False
        assert info['features']['flow_routing'] is False
        
        output_desc = task._get_expected_output_description()
        assert "ContentAnalysisResult" not in output_desc
        assert "viral_score" not in output_desc
        
        print("✅ Legacy model compatibility test passed")


class TestContentAnalysisResultModel:
    """Test suite for ContentAnalysisResult Pydantic model"""
    
    def test_model_validation(self):
        """Test Pydantic model validation"""
        # Valid data
        valid_data = {
            'content_type': 'technical_tutorial',
            'viral_score': 0.7,
            'complexity_level': 'intermediate',
            'recommended_flow_path': 'linkedin_post_flow',
            'target_platform': 'LinkedIn',
            'analysis_confidence': 0.85,
            'processing_time': 1.23,
            'key_themes': ['AI', 'CrewAI', 'automation'],
            'kb_insights': ['Pattern X is effective', 'Consider approach Y']
        }
        
        # Should create successfully
        result = ContentAnalysisResult(**valid_data)
        assert result.content_type == 'technical_tutorial'
        assert result.viral_score == 0.7
        assert result.complexity_level == 'intermediate'
        assert len(result.key_themes) == 3
        assert len(result.kb_insights) == 2
        
        print("✅ Model validation test passed")
    
    def test_model_defaults(self):
        """Test model default values"""
        # Minimal required data
        minimal_data = {
            'content_type': 'general',
            'viral_score': 0.5,
            'complexity_level': 'beginner',
            'recommended_flow_path': 'standard',
            'target_platform': 'General',
            'analysis_confidence': 0.8,
            'processing_time': 1.0
        }
        
        result = ContentAnalysisResult(**minimal_data)
        
        # Check defaults
        assert result.kb_insights == []
        assert result.key_themes == []
        assert result.audience_indicators == {}
        assert result.content_structure == {}
        assert result.kb_available is True
        assert result.search_strategy_used == "HYBRID"
        assert result.kb_query_count == 0
        
        print("✅ Model defaults test passed")
    
    def test_model_validation_errors(self):
        """Test model validation errors"""
        # Invalid viral score
        with pytest.raises(ValueError):
            ContentAnalysisResult(
                content_type='test',
                viral_score=1.5,  # Invalid: > 1.0
                complexity_level='beginner',
                recommended_flow_path='test',
                target_platform='test',
                analysis_confidence=0.8,
                processing_time=1.0
            )
        
        # Invalid confidence score
        with pytest.raises(ValueError):
            ContentAnalysisResult(
                content_type='test',
                viral_score=0.5,
                complexity_level='beginner',
                recommended_flow_path='test',
                target_platform='test',
                analysis_confidence=1.5,  # Invalid: > 1.0
                processing_time=1.0
            )
        
        print("✅ Model validation errors test passed")


def run_comprehensive_test():
    """Run comprehensive test suite"""
    print("🚀 Starting Enhanced Content Analysis Agent Test Suite (Task 2.2)")
    print("=" * 70)
    
    try:
        # Test Agent
        print("\n📋 Testing Enhanced ContentAnalysisAgent...")
        agent_tests = TestEnhancedContentAnalysisAgent()
        agent_tests.setup_method()
        
        agent_tests.test_agent_initialization()
        agent_tests.test_agent_info()
        agent_tests.test_content_requirements_analysis()
        agent_tests.test_viral_score_calculation()
        agent_tests.test_complexity_assessment()
        agent_tests.test_flow_path_recommendation()
        agent_tests.test_metrics_tracking()
        agent_tests.test_knowledge_tools_loading()
        agent_tests.test_crewai_agent_creation()
        
        # Test Task
        print("\n📋 Testing Enhanced ContentAnalysisTask...")
        task_tests = TestEnhancedContentAnalysisTask()
        task_tests.setup_method()
        
        task_tests.test_task_initialization()
        task_tests.test_task_info()
        task_tests.test_task_creation_with_mock_agent()
        task_tests.test_task_description_building()
        task_tests.test_expected_output_description()
        task_tests.test_legacy_model_compatibility()
        
        # Test Model
        print("\n📋 Testing ContentAnalysisResult Model...")
        model_tests = TestContentAnalysisResultModel()
        
        model_tests.test_model_validation()
        model_tests.test_model_defaults()
        model_tests.test_model_validation_errors()
        
        print("\n" + "=" * 70)
        print("🎉 ALL TESTS PASSED! Enhanced Content Analysis Agent is ready for production.")
        print("✅ Task 2.2 - Implement content analysis agent - COMPLETED")
        print("\n📊 Test Summary:")
        print("   - ContentAnalysisAgent: 9/9 tests passed")
        print("   - ContentAnalysisTask: 6/6 tests passed") 
        print("   - ContentAnalysisResult: 3/3 tests passed")
        print("   - Total: 18/18 tests passed")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_comprehensive_test()
    exit(0 if success else 1)