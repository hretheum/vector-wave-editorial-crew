"""
Simplified Integration Tests for Knowledge Base System
Testing core functionality without full CrewAI dependencies
"""

import pytest
import asyncio
import aiohttp
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import json
import time
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, 'src')

from ai_writing_flow.adapters.knowledge_adapter import (
    KnowledgeAdapter,
    SearchStrategy,
    KnowledgeResponse,
    AdapterError,
    CircuitBreakerOpen,
    get_adapter
)


class TestKnowledgeBaseConnectivity:
    """Test Knowledge Base API connectivity"""

    @pytest.mark.asyncio
    async def test_kb_api_connectivity_success(self):
        """Test successful KB API connectivity"""
        
        mock_response_data = {
            "results": [
                {
                    "content": "CrewAI agents are autonomous entities",
                    "score": 0.95,
                    "metadata": {
                        "source": "agents.md",
                        "title": "Agent Overview"
                    }
                }
            ],
            "status": "success",
            "query_time_ms": 45
        }
        
        adapter = KnowledgeAdapter(
            kb_api_url="http://localhost:8080",
            strategy=SearchStrategy.KB_ONLY
        )
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock successful response
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response_data)
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            result = await adapter.search_knowledge_base("CrewAI agents")
            
            assert len(result.results) == 1
            assert result.results[0]["content"] == "CrewAI agents are autonomous entities"
            assert result.results[0]["score"] == 0.95
            assert result.kb_available is True
        
        await adapter.close()

    @pytest.mark.asyncio
    async def test_kb_api_connectivity_failure(self):
        """Test KB API connectivity failure and circuit breaker"""
        
        adapter = KnowledgeAdapter(
            kb_api_url="http://localhost:8080",
            circuit_breaker_threshold=2
        )
        
        with patch('aiohttp.ClientSession.post', side_effect=aiohttp.ClientConnectionError("Connection failed")):
            
            # First failure
            with pytest.raises(AdapterError):
                await adapter.search_knowledge_base("test")
            
            assert not adapter.circuit_breaker.is_open()
            
            # Second failure - should open circuit breaker
            with pytest.raises(AdapterError):
                await adapter.search_knowledge_base("test")
            
            assert adapter.circuit_breaker.is_open()
            
            # Third attempt should fail immediately due to circuit breaker
            with pytest.raises(CircuitBreakerOpen):
                await adapter.search_knowledge_base("test")
        
        await adapter.close()

    @pytest.mark.asyncio
    async def test_kb_fallback_to_file_search(self):
        """Test fallback to file search when KB is down"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.KB_FIRST)
        
        # Mock file search to return content
        with patch.object(adapter, '_search_local_files') as mock_file_search:
            mock_file_search.return_value = "Local file content about CrewAI"
            
            with patch('aiohttp.ClientSession.post', side_effect=aiohttp.ClientConnectionError()):
                
                result = await adapter.search("CrewAI agents")
                
                assert result.strategy_used == SearchStrategy.FILE_FIRST  # Fallback strategy
                assert result.file_content == "Local file content about CrewAI"
                assert not result.kb_available
                assert len(result.results) == 0
        
        await adapter.close()


class TestSearchStrategies:
    """Test different search strategies work correctly"""

    @pytest.fixture
    def sample_kb_response(self):
        return {
            "results": [
                {
                    "content": "KB content about CrewAI flows",
                    "score": 0.92,
                    "metadata": {"source": "flows.md", "title": "Flow Patterns"}
                }
            ]
        }

    @pytest.fixture
    def sample_file_content(self):
        return "Local file content about CrewAI implementation"

    @pytest.mark.asyncio
    async def test_kb_first_strategy(self, sample_kb_response, sample_file_content):
        """Test KB_FIRST strategy prioritizes Knowledge Base"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.KB_FIRST)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=sample_kb_response)
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            with patch.object(adapter, '_search_local_files', return_value=sample_file_content):
                
                result = await adapter.search("CrewAI flows")
                
                assert result.strategy_used == SearchStrategy.KB_FIRST
                assert len(result.results) == 1
                assert result.results[0]["content"] == "KB content about CrewAI flows"
                assert result.kb_available is True
        
        await adapter.close()

    @pytest.mark.asyncio
    async def test_file_first_strategy(self, sample_kb_response, sample_file_content):
        """Test FILE_FIRST strategy prioritizes local files"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.FILE_FIRST)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=sample_kb_response)
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            with patch.object(adapter, '_search_local_files', return_value=sample_file_content):
                
                result = await adapter.search("CrewAI flows")
                
                assert result.strategy_used == SearchStrategy.FILE_FIRST
                assert result.file_content == sample_file_content
                # Should also have KB results for enrichment
                assert len(result.results) == 1
                assert result.kb_available is True
        
        await adapter.close()

    @pytest.mark.asyncio
    async def test_hybrid_strategy(self, sample_kb_response, sample_file_content):
        """Test HYBRID strategy combines both sources"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.HYBRID)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=sample_kb_response)
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            with patch.object(adapter, '_search_local_files', return_value=sample_file_content):
                
                result = await adapter.search("CrewAI flows")
                
                assert result.strategy_used == SearchStrategy.HYBRID
                assert result.file_content == sample_file_content
                assert len(result.results) == 1
                assert result.kb_available is True
        
        await adapter.close()

    @pytest.mark.asyncio
    async def test_kb_only_strategy_no_fallback(self):
        """Test KB_ONLY strategy doesn't fall back to files"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.KB_ONLY)
        
        with patch('aiohttp.ClientSession.post', side_effect=aiohttp.ClientConnectionError()):
            
            with pytest.raises(AdapterError, match="Knowledge Base unavailable"):
                await adapter.search("CrewAI flows")
        
        await adapter.close()


class TestCircuitBreakerFunctionality:
    """Test circuit breaker functionality in depth"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after failure threshold"""
        
        adapter = KnowledgeAdapter(circuit_breaker_threshold=3)
        
        with patch('aiohttp.ClientSession.post', side_effect=aiohttp.ClientConnectionError()):
            
            # Failures 1 and 2 - circuit breaker should remain closed
            for i in range(2):
                with pytest.raises(AdapterError):
                    await adapter.search_knowledge_base("test")
                assert not adapter.circuit_breaker.is_open()
            
            # Failure 3 - should open circuit breaker
            with pytest.raises(AdapterError):
                await adapter.search_knowledge_base("test")
            assert adapter.circuit_breaker.is_open()
        
        await adapter.close()

    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_requests_when_open(self):
        """Test circuit breaker prevents requests when open"""
        
        adapter = KnowledgeAdapter()
        
        # Force circuit breaker open
        adapter.circuit_breaker._is_open = True
        adapter.circuit_breaker._failure_count = 10
        
        with pytest.raises(CircuitBreakerOpen):
            await adapter.search_knowledge_base("test")
        
        await adapter.close()

    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_on_success(self):
        """Test circuit breaker resets on successful request"""
        
        adapter = KnowledgeAdapter(circuit_breaker_threshold=2)
        
        # First cause a failure
        with patch('aiohttp.ClientSession.post', side_effect=aiohttp.ClientConnectionError()):
            with pytest.raises(AdapterError):
                await adapter.search_knowledge_base("test")
        
        assert adapter.circuit_breaker._failure_count == 1
        
        # Then succeed
        mock_response = {"results": []}
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            await adapter.search_knowledge_base("test")
        
        assert adapter.circuit_breaker._failure_count == 0
        assert not adapter.circuit_breaker.is_open()
        
        await adapter.close()


class TestPerformanceMeasurement:
    """Test performance measurement and metrics"""

    @pytest.mark.asyncio
    async def test_response_time_measurement(self):
        """Test that response times are measured correctly"""
        
        adapter = KnowledgeAdapter()
        
        mock_response = {"results": []}
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            # Add artificial delay
            with patch('time.time', side_effect=[0, 0.150]):  # 150ms
                result = await adapter.search("test query")
        
        stats = adapter.get_statistics()
        assert stats.total_queries == 1
        assert stats.average_response_time_ms == 150
        
        await adapter.close()

    @pytest.mark.asyncio
    async def test_statistics_tracking(self):
        """Test comprehensive statistics tracking"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.HYBRID)
        
        # Mock successful KB and file search
        mock_response = {"results": [{"content": "test"}]}
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            with patch.object(adapter, '_search_local_files', return_value="file content"):
                
                # Perform multiple searches
                await adapter.search("query 1")
                await adapter.search("query 2")
                await adapter.search("query 3")
        
        stats = adapter.get_statistics()
        
        assert stats.total_queries == 3
        assert stats.kb_successes == 3
        assert stats.kb_errors == 0
        assert stats.file_searches == 3
        assert stats.kb_availability == 1.0
        assert stats.strategy_usage[SearchStrategy.HYBRID] == 3
        
        await adapter.close()

    @pytest.mark.asyncio
    async def test_concurrent_requests_performance(self):
        """Test performance under concurrent load"""
        
        adapter = KnowledgeAdapter()
        
        mock_response = {"results": []}
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            with patch.object(adapter, '_search_local_files', return_value="content"):
                
                start_time = time.time()
                
                # Run 10 concurrent searches
                tasks = [adapter.search(f"query {i}") for i in range(10)]
                results = await asyncio.gather(*tasks)
                
                end_time = time.time()
                total_time = end_time - start_time
        
        assert len(results) == 10
        assert all(isinstance(r, KnowledgeResponse) for r in results)
        
        # Should complete in reasonable time (less than 2 seconds for 10 requests)
        assert total_time < 2.0
        
        stats = adapter.get_statistics()
        assert stats.total_queries == 10
        
        await adapter.close()


class TestEndToEndScenarios:
    """Test realistic end-to-end scenarios"""

    @pytest.mark.asyncio
    async def test_crewai_agent_flow_question(self):
        """Test realistic CrewAI agent flow question"""
        
        # Mock KB response with relevant CrewAI content
        kb_response = {
            "results": [
                {
                    "content": """
# CrewAI Agent Creation

To create a CrewAI agent:

```python
from crewai import Agent

agent = Agent(
    role='Research Specialist',
    goal='Gather comprehensive information on the topic',
    backstory='Expert researcher with 10 years experience',
    tools=[search_tool, analysis_tool],
    verbose=True
)
```
                    """.strip(),
                    "score": 0.95,
                    "metadata": {
                        "source": "agent-guide.md",
                        "title": "Agent Creation Guide"
                    }
                }
            ]
        }
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.HYBRID)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=kb_response)
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            with patch.object(adapter, '_search_local_files') as mock_file_search:
                mock_file_search.return_value = "Additional agent configuration examples..."
                
                result = await adapter.search("How to create CrewAI agent with tools")
        
        assert result.strategy_used == SearchStrategy.HYBRID
        assert len(result.results) == 1
        assert "Agent(" in result.results[0]["content"]
        assert "role='Research Specialist'" in result.results[0]["content"]
        assert result.file_content == "Additional agent configuration examples..."
        
        await adapter.close()

    @pytest.mark.asyncio
    async def test_troubleshooting_memory_issues(self):
        """Test troubleshooting scenario for memory issues"""
        
        kb_response = {
            "results": [
                {
                    "content": """
# CrewAI Memory Troubleshooting

Common memory issues:

1. **Short-term memory not persisting**: Ensure `memory=True` in Crew configuration
2. **Long-term memory errors**: Check vector store configuration
3. **Memory conflicts**: Use separate memory instances for different crews

Example fix:
```python
crew = Crew(
    agents=[agent1, agent2],
    tasks=[task1, task2],
    memory=True,
    memory_type="long_term"
)
```
                    """.strip(),
                    "score": 0.88,
                    "metadata": {
                        "source": "troubleshooting.md",
                        "title": "Memory Issues"
                    }
                }
            ]
        }
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.KB_FIRST)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=kb_response)
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            result = await adapter.search("CrewAI memory issues troubleshooting")
        
        assert result.strategy_used == SearchStrategy.KB_FIRST
        assert "memory=True" in result.results[0]["content"]
        assert "Memory Troubleshooting" in result.results[0]["content"]
        
        await adapter.close()

    @pytest.mark.asyncio
    async def test_backward_compatibility_with_old_tools(self):
        """Test backward compatibility with existing tool interfaces"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.FILE_FIRST)
        
        with patch.object(adapter, '_search_local_files') as mock_file_search:
            mock_file_search.return_value = "Legacy file search result"
            
            # Simulate old tool behavior - just return string
            result = await adapter.search("legacy query")
            
            # KnowledgeResponse should be convertible to string
            result_str = str(result)
            assert "Legacy file search result" in result_str
        
        await adapter.close()


class TestGlobalAdapterInstance:
    """Test global adapter instance management"""

    def test_get_adapter_singleton(self):
        """Test that get_adapter returns singleton instance"""
        
        with patch.dict('os.environ', {'KNOWLEDGE_STRATEGY': 'HYBRID'}):
            adapter1 = get_adapter()
            adapter2 = get_adapter()
            
            assert adapter1 is adapter2
            assert adapter1.strategy == SearchStrategy.HYBRID

    def test_get_adapter_with_strategy_override(self):
        """Test get_adapter with strategy override"""
        
        # Clear any existing instance first
        import ai_writing_flow.adapters.knowledge_adapter as ka_module
        ka_module._adapter_instance = None
        
        adapter = get_adapter(strategy=SearchStrategy.KB_ONLY)
        assert adapter.strategy == SearchStrategy.KB_ONLY

    def test_get_adapter_environment_configuration(self):
        """Test get_adapter respects environment configuration"""
        
        # Clear any existing instance first
        import ai_writing_flow.adapters.knowledge_adapter as ka_module
        ka_module._adapter_instance = None
        
        with patch.dict('os.environ', {
            'KNOWLEDGE_STRATEGY': 'FILE_FIRST',
            'KNOWLEDGE_BASE_URL': 'http://custom:9090',
            'KNOWLEDGE_TIMEOUT': '30.0'
        }):
            adapter = get_adapter()
            
            assert adapter.strategy == SearchStrategy.FILE_FIRST
            assert adapter.kb_api_url == 'http://custom:9090'
            assert adapter.timeout == 30.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])