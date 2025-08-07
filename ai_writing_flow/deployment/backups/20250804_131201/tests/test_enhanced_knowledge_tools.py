"""
Test Enhanced Knowledge Tools - TDD implementation
Tests for CrewAI tools with Knowledge Base integration
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from src.ai_writing_flow.tools.enhanced_knowledge_tools import (
    search_crewai_knowledge,
    get_flow_examples,
    troubleshoot_crewai,
    # Backward compatibility imports
    search_crewai_docs as legacy_search_docs,
    get_crewai_example as legacy_get_example,
    list_crewai_topics as legacy_list_topics
)
from src.ai_writing_flow.adapters.knowledge_adapter import KnowledgeResponse, SearchStrategy


class TestSearchCrewAIKnowledge:
    """Test the main search_crewai_knowledge tool"""

    @pytest.fixture
    def mock_adapter_response(self):
        """Mock adapter response with mixed KB and file results"""
        return KnowledgeResponse(
            query="CrewAI agent setup",
            results=[
                {
                    "content": "Agent setup from KB",
                    "score": 0.95,
                    "metadata": {"source": "kb", "title": "Agent Setup Guide"}
                },
                {
                    "content": "Additional agent info",
                    "score": 0.88,
                    "metadata": {"source": "kb", "title": "Agent Best Practices"}
                }
            ],
            file_content="Local file content about agents...",
            strategy_used=SearchStrategy.HYBRID,
            kb_available=True,
            response_time_ms=150
        )

    def test_search_with_default_parameters(self, mock_adapter_response):
        """Test search with default parameters"""
        
        with patch('src.ai_writing_flow.tools.enhanced_knowledge_tools._get_adapter') as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.search.return_value = mock_adapter_response
            mock_get_adapter.return_value = mock_adapter
            
            result = search_crewai_knowledge("CrewAI agent setup")
            
            # Verify adapter was called correctly
            mock_adapter.search.assert_called_once_with(
                query="CrewAI agent setup",
                limit=5,
                score_threshold=0.7,
                context=None
            )
            
            # Check result format
            assert "## Knowledge Base Results" in result
            assert "Agent setup from KB" in result
            assert "## Local Documentation" in result
            assert "Local file content about agents" in result
            assert "Response time: 150ms" in result

    def test_search_with_custom_parameters(self, mock_adapter_response):
        """Test search with custom parameters"""
        
        with patch('src.ai_writing_flow.tools.enhanced_knowledge_tools._get_adapter') as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.search.return_value = mock_adapter_response
            mock_get_adapter.return_value = mock_adapter
            
            result = search_crewai_knowledge(
                query="advanced patterns",
                limit=10,
                score_threshold=0.8,
                strategy="KB_FIRST"
            )
            
            mock_adapter.search.assert_called_once_with(
                query="advanced patterns",
                limit=10,
                score_threshold=0.8,
                context=None
            )
            
            assert "Knowledge Base Results" in result

    def test_search_kb_unavailable_fallback(self):
        """Test search when KB is unavailable"""
        
        kb_unavailable_response = KnowledgeResponse(
            query="test query",
            results=[],
            file_content="Fallback file content",
            strategy_used=SearchStrategy.FILE_FIRST,
            kb_available=False,
            response_time_ms=50
        )
        
        with patch('src.ai_writing_flow.tools.enhanced_knowledge_tools._get_adapter') as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.search.return_value = kb_unavailable_response
            mock_get_adapter.return_value = mock_adapter
            
            result = search_crewai_knowledge("test query")
            
            assert "⚠️ Knowledge Base unavailable" in result
            assert "Fallback file content" in result
            assert "Strategy used: FILE_FIRST" in result

    def test_search_no_results_found(self):
        """Test search when no results are found"""
        
        no_results_response = KnowledgeResponse(
            query="obscure query",
            results=[],
            file_content="",
            strategy_used=SearchStrategy.HYBRID,
            kb_available=True,
            response_time_ms=200
        )
        
        with patch('src.ai_writing_flow.tools.enhanced_knowledge_tools._get_adapter') as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.search.return_value = no_results_response
            mock_get_adapter.return_value = mock_adapter
            
            result = search_crewai_knowledge("obscure query")
            
            assert "No relevant results found" in result
            assert "Try different keywords" in result


class TestGetFlowExamples:
    """Test the get_flow_examples tool"""

    def test_get_flow_examples_agent_patterns(self):
        """Test getting agent pattern examples"""
        
        mock_response = KnowledgeResponse(
            query="agent patterns",
            results=[
                {
                    "content": "```python\nagent = Agent(role='Researcher')\n```",
                    "score": 0.92,
                    "metadata": {"source": "patterns", "title": "Agent Patterns"}
                }
            ],
            file_content="Additional agent examples...",
            strategy_used=SearchStrategy.KB_FIRST,
            kb_available=True
        )
        
        with patch('src.ai_writing_flow.tools.enhanced_knowledge_tools._get_adapter') as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.search.return_value = mock_response
            mock_get_adapter.return_value = mock_adapter
            
            result = get_flow_examples("agent_patterns")
            
            # Should search for agent-specific patterns
            mock_adapter.search.assert_called_once()
            call_args = mock_adapter.search.call_args[1]
            assert "agent" in call_args["query"].lower()
            assert "pattern" in call_args["query"].lower()
            
            assert "Agent Patterns" in result
            assert "```python" in result

    def test_get_flow_examples_task_orchestration(self):
        """Test getting task orchestration examples"""
        
        mock_response = KnowledgeResponse(
            query="task orchestration patterns",
            results=[
                {
                    "content": "Task orchestration example...",
                    "score": 0.89,
                    "metadata": {"source": "examples", "title": "Task Orchestration"}
                }
            ],
            file_content="",
            strategy_used=SearchStrategy.HYBRID,
            kb_available=True
        )
        
        with patch('src.ai_writing_flow.tools.enhanced_knowledge_tools._get_adapter') as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.search.return_value = mock_response
            mock_get_adapter.return_value = mock_adapter
            
            result = get_flow_examples("task_orchestration")
            
            call_args = mock_adapter.search.call_args[1]
            assert "task" in call_args["query"].lower()
            assert "orchestration" in call_args["query"].lower()

    def test_get_flow_examples_invalid_pattern(self):
        """Test getting examples for invalid pattern"""
        
        result = get_flow_examples("invalid_pattern")
        
        assert "Unknown pattern type" in result
        assert "Available patterns:" in result
        assert "agent_patterns" in result
        assert "task_orchestration" in result


class TestTroubleshootCrewAI:
    """Test the troubleshoot_crewai tool"""

    def test_troubleshoot_installation_issues(self):
        """Test troubleshooting installation issues"""
        
        mock_response = KnowledgeResponse(
            query="CrewAI installation troubleshooting",
            results=[
                {
                    "content": "Common installation issues and solutions...",
                    "score": 0.95,
                    "metadata": {"source": "troubleshooting", "title": "Installation Issues"}
                }
            ],
            file_content="Additional troubleshooting content",
            strategy_used=SearchStrategy.HYBRID,
            kb_available=True
        )
        
        with patch('src.ai_writing_flow.tools.enhanced_knowledge_tools._get_adapter') as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.search.return_value = mock_response
            mock_get_adapter.return_value = mock_adapter
            
            result = troubleshoot_crewai("installation")
            
            # Should search for installation troubleshooting
            call_args = mock_adapter.search.call_args[1]
            assert "installation" in call_args["query"].lower()
            assert "troubleshoot" in call_args["query"].lower()
            
            assert "🔧 Troubleshooting" in result
            assert "Installation Issues" in result

    def test_troubleshoot_memory_issues(self):
        """Test troubleshooting memory issues"""
        
        mock_response = KnowledgeResponse(
            query="CrewAI memory troubleshooting",
            results=[],
            file_content="Memory troubleshooting from local files",
            strategy_used=SearchStrategy.FILE_FIRST,
            kb_available=False
        )
        
        with patch('src.ai_writing_flow.tools.enhanced_knowledge_tools._get_adapter') as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.search.return_value = mock_response
            mock_get_adapter.return_value = mock_adapter
            
            result = troubleshoot_crewai("memory")
            
            assert "memory" in result.lower()
            assert "🔧 Troubleshooting" in result

    def test_troubleshoot_invalid_issue_type(self):
        """Test troubleshooting with invalid issue type"""
        
        result = troubleshoot_crewai("unknown_issue")
        
        assert "⚠️ Unknown issue type" in result
        assert "Common issue types:" in result
        assert "installation" in result
        assert "memory" in result


class TestBackwardCompatibility:
    """Test backward compatibility with existing tools"""

    def test_legacy_search_crewai_docs_compatibility(self):
        """Test that legacy search_crewai_docs works as before"""
        
        mock_response = KnowledgeResponse(
            query="test query",
            results=[],
            file_content="Legacy file content",
            strategy_used=SearchStrategy.FILE_FIRST,
            kb_available=False
        )
        
        with patch('src.ai_writing_flow.tools.enhanced_knowledge_tools._get_adapter') as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.search.return_value = mock_response
            mock_get_adapter.return_value = mock_adapter
            
            result = legacy_search_docs("test query")
            
            # Should maintain same interface
            assert isinstance(result, str)
            assert "Legacy file content" in result

    def test_legacy_get_crewai_example_compatibility(self):
        """Test that legacy get_crewai_example works as before"""
        
        result = legacy_get_example("crew creation")
        
        # Should return same format as before
        assert isinstance(result, str)
        assert "```python" in result
        assert "from crewai import" in result

    def test_legacy_list_crewai_topics_compatibility(self):
        """Test that legacy list_crewai_topics works as before"""
        
        result = legacy_list_topics()
        
        # Should return same format as before
        assert isinstance(result, str)
        assert "Available CrewAI documentation topics" in result


class TestKnowledgeToolsErrorHandling:
    """Test error handling in knowledge tools"""

    def test_adapter_initialization_error(self):
        """Test handling of adapter initialization errors"""
        
        with patch('src.ai_writing_flow.tools.enhanced_knowledge_tools._get_adapter', side_effect=Exception("Init error")):
            
            result = search_crewai_knowledge("test query")
            
            assert "⚠️ Knowledge system temporarily unavailable" in result
            assert "falling back to basic search" in result

    def test_search_timeout_error(self):
        """Test handling of search timeout errors"""
        
        with patch('src.ai_writing_flow.tools.enhanced_knowledge_tools._get_adapter') as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.search.side_effect = asyncio.TimeoutError("Search timed out")
            mock_get_adapter.return_value = mock_adapter
            
            result = search_crewai_knowledge("test query")
            
            assert "⚠️ Search timed out" in result
            assert "Please try again" in result

    def test_adapter_circuit_breaker_open(self):
        """Test handling when circuit breaker is open"""
        
        from src.ai_writing_flow.adapters.knowledge_adapter import CircuitBreakerOpen
        
        with patch('src.ai_writing_flow.tools.enhanced_knowledge_tools._get_adapter') as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.search.side_effect = CircuitBreakerOpen("KB unavailable")
            mock_get_adapter.return_value = mock_adapter
            
            result = search_crewai_knowledge("test query")
            
            assert "⚠️ Knowledge Base temporarily unavailable" in result
            assert "circuit breaker protection" in result


class TestToolConfiguration:
    """Test tool configuration and customization"""

    def test_tool_uses_correct_strategy_config(self):
        """Test that tools use correct strategy configuration"""
        
        # This would test environment-based configuration
        with patch.dict('os.environ', {'KNOWLEDGE_STRATEGY': 'KB_FIRST'}):
            with patch('src.ai_writing_flow.tools.enhanced_knowledge_tools._get_adapter') as mock_get_adapter:
                mock_adapter = AsyncMock()
                mock_adapter.search.return_value = KnowledgeResponse(
                    query="test", results=[], file_content="", 
                    strategy_used=SearchStrategy.KB_FIRST, kb_available=True
                )
                mock_get_adapter.return_value = mock_adapter
                
                search_crewai_knowledge("test query")
                
                # Verify adapter was initialized with correct strategy
                mock_get_adapter.assert_called_once()

    def test_tool_performance_tracking(self):
        """Test that tools track performance metrics"""
        
        mock_response = KnowledgeResponse(
            query="test", results=[], file_content="", 
            strategy_used=SearchStrategy.HYBRID, kb_available=True,
            response_time_ms=123
        )
        
        with patch('src.ai_writing_flow.tools.enhanced_knowledge_tools._get_adapter') as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.search.return_value = mock_response
            mock_get_adapter.return_value = mock_adapter
            
            result = search_crewai_knowledge("test query")
            
            # Performance info should be included
            assert "Response time: 123ms" in result