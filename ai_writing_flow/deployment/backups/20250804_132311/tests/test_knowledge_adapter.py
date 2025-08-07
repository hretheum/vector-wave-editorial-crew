"""
Test Knowledge Adapter - TDD implementation
Following Clean Architecture and production-ready patterns
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta
import aiohttp
import json
from typing import Dict, List, Any

from src.ai_writing_flow.adapters.knowledge_adapter import (
    KnowledgeAdapter,
    SearchStrategy,
    KnowledgeResponse,
    AdapterError,
    CircuitBreakerOpen
)


class TestKnowledgeAdapterConfiguration:
    """Test adapter configuration and initialization"""

    def test_default_configuration(self):
        """Test adapter with default configuration"""
        adapter = KnowledgeAdapter()
        
        assert adapter.strategy == SearchStrategy.HYBRID
        assert adapter.kb_api_url == "http://localhost:8080"
        assert adapter.timeout == 10.0
        assert adapter.max_retries == 3
        assert not adapter.circuit_breaker._is_open

    def test_custom_configuration(self):
        """Test adapter with custom configuration"""
        config = {
            "strategy": SearchStrategy.KB_ONLY,
            "kb_api_url": "http://custom:9090",
            "timeout": 30.0,
            "max_retries": 5,
            "circuit_breaker_threshold": 10
        }
        
        adapter = KnowledgeAdapter(**config)
        
        assert adapter.strategy == SearchStrategy.KB_ONLY
        assert adapter.kb_api_url == "http://custom:9090"
        assert adapter.timeout == 30.0
        assert adapter.max_retries == 5

    def test_invalid_strategy_raises_error(self):
        """Test that invalid strategy raises configuration error"""
        with pytest.raises(ValueError, match="Invalid search strategy"):
            KnowledgeAdapter(strategy="INVALID_STRATEGY")


class TestKnowledgeAdapterCircuitBreaker:
    """Test circuit breaker functionality"""

    @pytest.fixture
    def adapter(self):
        return KnowledgeAdapter(circuit_breaker_threshold=2)

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self, adapter):
        """Test circuit breaker opens after threshold failures"""
        
        # Mock KB API to always fail
        with patch('aiohttp.ClientSession.post', side_effect=aiohttp.ClientError()):
            
            # First failure
            with pytest.raises(AdapterError):
                await adapter.search_knowledge_base("test query")
            assert not adapter.circuit_breaker._is_open
            
            # Second failure - should open circuit breaker
            with pytest.raises(AdapterError):
                await adapter.search_knowledge_base("test query")
            assert adapter.circuit_breaker._is_open

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_requests_when_open(self, adapter):
        """Test circuit breaker blocks requests when open"""
        
        # Force circuit breaker open
        adapter.circuit_breaker._is_open = True
        adapter.circuit_breaker._last_failure = datetime.now()
        
        with pytest.raises(CircuitBreakerOpen):
            await adapter.search_knowledge_base("test query")

    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_after_timeout(self, adapter):
        """Test circuit breaker resets after timeout period"""
        
        # Force circuit breaker open but expired
        adapter.circuit_breaker._is_open = True
        adapter.circuit_breaker._last_failure = datetime.now() - timedelta(seconds=61)
        
        # Mock successful KB response
        mock_response = {
            "results": [
                {
                    "content": "Test content",
                    "score": 0.95,
                    "metadata": {"source": "test.md"}
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aenter__.return_value.status = 200
            
            result = await adapter.search_knowledge_base("test query")
            
            assert not adapter.circuit_breaker._is_open
            assert len(result.results) == 1


class TestKnowledgeAdapterSearchStrategies:
    """Test different search strategies"""

    @pytest.fixture
    def mock_kb_response(self):
        return {
            "results": [
                {
                    "content": "KB result content",
                    "score": 0.95,
                    "metadata": {"source": "kb", "title": "KB Document"}
                }
            ]
        }

    @pytest.fixture
    def mock_file_content(self):
        return "File-based content about CrewAI agents and tasks"

    @pytest.mark.asyncio
    async def test_kb_first_strategy_success(self, mock_kb_response):
        """Test KB_FIRST strategy with successful KB response"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.KB_FIRST)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_kb_response)
            mock_post.return_value.__aenter__.return_value.status = 200
            
            result = await adapter.search("test query")
            
            assert result.strategy_used == SearchStrategy.KB_FIRST
            assert len(result.results) == 1
            assert result.results[0]["content"] == "KB result content"
            assert result.kb_available

    @pytest.mark.asyncio
    async def test_kb_first_strategy_fallback_to_file(self, mock_file_content):
        """Test KB_FIRST strategy falls back to file when KB fails"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.KB_FIRST)
        
        with patch('aiohttp.ClientSession.post', side_effect=aiohttp.ClientError()):
            with patch.object(adapter, '_search_local_files', return_value=mock_file_content):
                
                result = await adapter.search("test query")
                
                assert result.strategy_used == SearchStrategy.FILE_FIRST
                assert result.file_content == mock_file_content
                assert not result.kb_available

    @pytest.mark.asyncio
    async def test_file_first_strategy(self, mock_file_content):
        """Test FILE_FIRST strategy searches files first"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.FILE_FIRST)
        
        with patch.object(adapter, '_search_local_files', return_value=mock_file_content):
            
            result = await adapter.search("test query")
            
            assert result.strategy_used == SearchStrategy.FILE_FIRST
            assert result.file_content == mock_file_content

    @pytest.mark.asyncio
    async def test_hybrid_strategy_combines_results(self, mock_kb_response, mock_file_content):
        """Test HYBRID strategy combines KB and file results"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.HYBRID)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_kb_response)
            mock_post.return_value.__aenter__.return_value.status = 200
            
            with patch.object(adapter, '_search_local_files', return_value=mock_file_content):
                
                result = await adapter.search("test query")
                
                assert result.strategy_used == SearchStrategy.HYBRID
                assert len(result.results) == 1
                assert result.file_content == mock_file_content
                assert result.kb_available

    @pytest.mark.asyncio
    async def test_kb_only_strategy_no_fallback(self):
        """Test KB_ONLY strategy doesn't fall back to files"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.KB_ONLY)
        
        with patch('aiohttp.ClientSession.post', side_effect=aiohttp.ClientError()):
            
            with pytest.raises(AdapterError, match="Knowledge Base unavailable"):
                await adapter.search("test query")


class TestKnowledgeAdapterErrorHandling:
    """Test error handling and resilience patterns"""

    @pytest.mark.asyncio
    async def test_kb_timeout_handling(self):
        """Test handling of KB API timeout"""
        
        adapter = KnowledgeAdapter(timeout=0.1)
        
        with patch('aiohttp.ClientSession.post', side_effect=asyncio.TimeoutError()):
            
            with pytest.raises(AdapterError, match="Knowledge Base request timed out"):
                await adapter.search_knowledge_base("test query")

    @pytest.mark.asyncio
    async def test_kb_invalid_response_handling(self):
        """Test handling of invalid KB API response"""
        
        adapter = KnowledgeAdapter()
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={"invalid": "format"})
            mock_post.return_value.__aenter__.return_value.status = 200
            
            with pytest.raises(AdapterError, match="Invalid response format"):
                await adapter.search_knowledge_base("test query")

    @pytest.mark.asyncio
    async def test_file_read_error_handling(self):
        """Test handling of file read errors"""
        
        adapter = KnowledgeAdapter()
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', side_effect=PermissionError("Access denied")):
                
                result = adapter._search_local_files("test query")
                
                assert "Error reading documentation" in result

    @pytest.mark.asyncio
    async def test_network_error_retry_logic(self):
        """Test retry logic for network errors"""
        
        adapter = KnowledgeAdapter(max_retries=2)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # First call fails, second succeeds
            mock_post.side_effect = [
                aiohttp.ClientError("Network error"),
                AsyncMock()
            ]
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={"results": []})
            mock_post.return_value.__aenter__.return_value.status = 200
            
            # Should not raise error due to retry
            result = await adapter.search_knowledge_base("test query")
            assert mock_post.call_count == 2


class TestKnowledgeAdapterStatistics:
    """Test statistics tracking and reporting"""

    @pytest.mark.asyncio
    async def test_statistics_tracking(self):
        """Test that adapter tracks usage statistics"""
        
        adapter = KnowledgeAdapter()
        
        with patch.object(adapter, '_search_local_files', return_value="file content"):
            
            # Perform multiple searches
            await adapter.search("query 1")
            await adapter.search("query 2")
            
            stats = adapter.get_statistics()
            
            assert stats.total_queries == 2
            assert stats.file_searches == 2
            assert stats.strategy_usage[SearchStrategy.HYBRID] == 2

    @pytest.mark.asyncio
    async def test_error_statistics_tracking(self):
        """Test that errors are tracked in statistics"""
        
        adapter = KnowledgeAdapter()
        
        with patch('aiohttp.ClientSession.post', side_effect=aiohttp.ClientError()):
            with patch.object(adapter, '_search_local_files', return_value="fallback content"):
                
                await adapter.search("test query")
                
                stats = adapter.get_statistics()
                assert stats.kb_errors == 1
                assert stats.kb_availability < 1.0

    def test_statistics_reset(self):
        """Test statistics can be reset"""
        
        adapter = KnowledgeAdapter()
        adapter.stats.total_queries = 10
        adapter.stats.kb_successes = 5
        
        adapter.reset_statistics()
        
        stats = adapter.get_statistics()
        assert stats.total_queries == 0
        assert stats.kb_successes == 0


class TestKnowledgeAdapterIntegration:
    """Integration tests with actual components"""

    @pytest.mark.asyncio
    async def test_real_file_search(self):
        """Test searching real CrewAI documentation files"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.FILE_FIRST)
        
        # This test requires actual docs to be present
        result = await adapter.search("agent role")
        
        assert result.file_content is not None
        assert len(result.file_content) > 0
        assert result.strategy_used == SearchStrategy.FILE_FIRST

    @pytest.mark.asyncio
    async def test_context_preservation(self):
        """Test that search context is preserved across operations"""
        
        adapter = KnowledgeAdapter()
        
        with patch.object(adapter, '_search_local_files', return_value="context content"):
            
            result1 = await adapter.search("first query")
            result2 = await adapter.search("second query", context=result1)
            
            # Context should be preserved in the second search
            assert result2.context_used
            assert result1.query in str(result2)