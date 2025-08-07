"""
Live Knowledge Base Integration Test
Tests with actual KB API (if available) and real file system
"""

import pytest
import asyncio
import aiohttp
import time
import sys
sys.path.insert(0, 'src')

from ai_writing_flow.adapters.knowledge_adapter import (
    KnowledgeAdapter,
    SearchStrategy,
    AdapterError,
    CircuitBreakerOpen
)


class TestLiveKnowledgeBase:
    """Test with actual Knowledge Base API (if running)"""

    @pytest.fixture
    async def kb_adapter(self):
        """Create adapter for live KB testing"""
        adapter = KnowledgeAdapter(
            strategy=SearchStrategy.HYBRID,
            kb_api_url="http://localhost:8080",
            timeout=5.0
        )
        yield adapter
        await adapter.close()

    @pytest.mark.asyncio
    async def test_kb_health_check(self, kb_adapter):
        """Test KB API health check"""
        
        try:
            # Try to make a simple request to check if KB is running
            session = await kb_adapter._get_session()
            async with session.get(f"{kb_adapter.kb_api_url}/api/v1/health") as response:
                print(f"KB Health Check Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"KB Health Response: {data}")
                    assert True  # KB is running
                else:
                    print(f"KB returned status {response.status}")
                    pytest.skip("Knowledge Base not available for live testing")
                    
        except aiohttp.ClientConnectionError:
            pytest.skip("Knowledge Base not running on localhost:8080")
        except Exception as e:
            print(f"KB connection error: {e}")
            pytest.skip(f"Knowledge Base connection failed: {e}")

    @pytest.mark.asyncio
    async def test_live_hybrid_search(self, kb_adapter):
        """Test hybrid search with live KB and real files"""
        
        try:
            result = await kb_adapter.search("CrewAI agent creation")
            
            print(f"Live search results:")
            print(f"  Strategy used: {result.strategy_used}")
            print(f"  KB available: {result.kb_available}")
            print(f"  KB results count: {len(result.results)}")
            print(f"  Has file content: {bool(result.file_content)}")
            print(f"  Response time: {result.response_time_ms:.2f}ms")
            
            # Should have either KB results or file content (or both)
            assert result.results or result.file_content, "No results from either source"
            
            # If KB is available, should have used HYBRID strategy
            if result.kb_available:
                assert result.strategy_used == SearchStrategy.HYBRID
            
        except CircuitBreakerOpen:
            pytest.skip("Circuit breaker is open - KB likely down")
        except AdapterError as e:
            if "Knowledge Base" in str(e):
                pytest.skip(f"KB unavailable: {e}")
            else:
                raise

    @pytest.mark.asyncio
    async def test_live_file_only_search(self):
        """Test file-only search with real documentation"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.FILE_FIRST)
        
        try:
            result = await adapter.search("agent role goal backstory")
            
            print(f"File-only search results:")
            print(f"  Strategy used: {result.strategy_used}")
            print(f"  Has file content: {bool(result.file_content)}")
            print(f"  File content length: {len(result.file_content) if result.file_content else 0}")
            
            # Should have file content if docs exist
            if result.file_content:
                assert "agent" in result.file_content.lower() or "role" in result.file_content.lower()
            
        finally:
            await adapter.close()

    @pytest.mark.asyncio
    async def test_live_performance_measurement(self, kb_adapter):
        """Test performance with live system"""
        
        queries = [
            "CrewAI agent setup",
            "task orchestration patterns", 
            "crew configuration",
            "tool integration",
            "memory management"
        ]
        
        start_time = time.time()
        results = []
        
        for query in queries:
            try:
                result = await kb_adapter.search(query)
                results.append(result)
            except (AdapterError, CircuitBreakerOpen):
                # Skip failed queries in live testing
                continue
        
        end_time = time.time()
        total_time = end_time - start_time
        
        if results:
            avg_time_per_query = total_time / len(results)
            
            print(f"Live performance results:")
            print(f"  Successful queries: {len(results)}/{len(queries)}")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Average time per query: {avg_time_per_query:.2f}s")
            
            # Check statistics
            stats = kb_adapter.get_statistics()
            print(f"  Total queries tracked: {stats.total_queries}")
            print(f"  KB availability: {stats.kb_availability:.1%}")
            print(f"  Average response time: {stats.average_response_time_ms:.2f}ms")
            
            # Performance assertions for live system
            assert avg_time_per_query < 10, f"Live queries too slow: {avg_time_per_query:.2f}s"
            assert len(results) > 0, "No successful queries"


class TestRealFileSystem:
    """Test with real CrewAI documentation files"""

    @pytest.mark.asyncio
    async def test_real_docs_search(self):
        """Test searching real CrewAI documentation"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.FILE_FIRST)
        
        try:
            # Search for common CrewAI terms
            result = await adapter.search("Agent")
            
            print(f"Real docs search for 'Agent':")
            print(f"  Has file content: {bool(result.file_content)}")
            print(f"  Content length: {len(result.file_content) if result.file_content else 0}")
            
            if result.file_content:
                # Should find agent-related content
                content_lower = result.file_content.lower()
                assert any(term in content_lower for term in ['agent', 'role', 'goal', 'backstory'])
                print(f"  Found relevant agent content: ✅")
            else:
                print(f"  No content found - docs path may not exist")
                print(f"  Docs path: {adapter.docs_path}")
                
        finally:
            await adapter.close()

    @pytest.mark.asyncio
    async def test_docs_path_configuration(self):
        """Test different documentation paths"""
        
        # Test with default path
        adapter1 = KnowledgeAdapter()
        print(f"Default docs path: {adapter1.docs_path}")
        print(f"Default path exists: {adapter1.docs_path.exists()}")
        
        # Test with custom path
        custom_path = "/Users/hretheum/dev/bezrobocie/vector-wave/knowledge-base"
        adapter2 = KnowledgeAdapter(docs_path=custom_path)
        print(f"Custom docs path: {adapter2.docs_path}")  
        print(f"Custom path exists: {adapter2.docs_path.exists()}")
        
        await adapter1.close()
        await adapter2.close()


class TestCircuitBreakerLive:
    """Test circuit breaker with simulated failures"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_real_timeouts(self):
        """Test circuit breaker with real timeout conditions"""
        
        # Use very short timeout to trigger circuit breaker
        adapter = KnowledgeAdapter(
            strategy=SearchStrategy.KB_ONLY,
            timeout=0.001,  # 1ms timeout - guaranteed to fail
            circuit_breaker_threshold=2
        )
        
        try:
            # First request should timeout
            with pytest.raises(AdapterError):
                await adapter.search("test query 1")
            
            assert not adapter.circuit_breaker.is_open()
            print(f"After 1st failure - Circuit breaker open: {adapter.circuit_breaker.is_open()}")
            
            # Second request should timeout and open circuit breaker
            with pytest.raises(AdapterError):
                await adapter.search("test query 2")
            
            assert adapter.circuit_breaker.is_open()
            print(f"After 2nd failure - Circuit breaker open: {adapter.circuit_breaker.is_open()}")
            
            # Third request should fail immediately
            start_time = time.time()
            with pytest.raises(CircuitBreakerOpen):
                await adapter.search("test query 3")
            end_time = time.time()
            
            immediate_fail_time = (end_time - start_time) * 1000
            print(f"Circuit breaker immediate fail time: {immediate_fail_time:.2f}ms")
            
            # Should fail very quickly
            assert immediate_fail_time < 50, f"Circuit breaker not immediate: {immediate_fail_time:.2f}ms"
            
        finally:
            await adapter.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])