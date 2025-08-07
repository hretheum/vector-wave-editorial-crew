"""
Performance Tests for Knowledge Base Integration
Tests latency, concurrency, memory usage and throughput
"""

import pytest
import asyncio
import time
import psutil
import os
from unittest.mock import AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor
import threading

import sys
sys.path.insert(0, 'src')

from ai_writing_flow.adapters.knowledge_adapter import (
    KnowledgeAdapter,
    SearchStrategy,
    KnowledgeResponse
)


class TestPerformanceMetrics:
    """Test performance metrics and benchmarks"""

    @pytest.mark.asyncio
    async def test_single_query_latency(self):
        """Test single query latency target <500ms"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.HYBRID)
        
        # Mock fast responses
        mock_kb_response = {"results": [{"content": "test", "score": 0.9}]}
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_kb_response)
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            with patch.object(adapter, '_search_local_files', return_value="file content"):
                
                start_time = time.time()
                result = await adapter.search("test query")
                end_time = time.time()
                
                latency_ms = (end_time - start_time) * 1000
                
                print(f"Single query latency: {latency_ms:.2f}ms")
                
                # Target: <500ms for single query
                assert latency_ms < 500, f"Latency {latency_ms}ms exceeds 500ms target"
                assert isinstance(result, KnowledgeResponse)
        
        await adapter.close()

    @pytest.mark.asyncio
    async def test_concurrent_queries_throughput(self):
        """Test concurrent query throughput"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.HYBRID)
        
        mock_kb_response = {"results": [{"content": "test", "score": 0.9}]}
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_kb_response)
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            with patch.object(adapter, '_search_local_files', return_value="file content"):
                
                # Test 20 concurrent queries
                num_queries = 20
                start_time = time.time()
                
                tasks = [
                    adapter.search(f"test query {i}") 
                    for i in range(num_queries)
                ]
                
                results = await asyncio.gather(*tasks)
                
                end_time = time.time()
                total_time = end_time - start_time
                throughput = num_queries / total_time
                
                print(f"Concurrent throughput: {throughput:.2f} queries/second")
                print(f"Total time for {num_queries} queries: {total_time:.2f}s")
                
                assert len(results) == num_queries
                assert all(isinstance(r, KnowledgeResponse) for r in results)
                
                # Target: >10 queries/second for concurrent load
                assert throughput > 10, f"Throughput {throughput:.2f} q/s below 10 q/s target"
        
        await adapter.close()

    @pytest.mark.asyncio 
    async def test_memory_usage_stability(self):
        """Test memory usage remains stable under load"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.HYBRID)
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        mock_kb_response = {"results": [{"content": "test content", "score": 0.9}]}
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_kb_response)
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            with patch.object(adapter, '_search_local_files', return_value="file content"):
                
                # Perform 100 searches to stress test memory
                for i in range(100):
                    await adapter.search(f"query {i}")
                    
                    # Check memory every 20 queries
                    if i % 20 == 0:
                        current_memory = process.memory_info().rss / 1024 / 1024
                        memory_increase = current_memory - initial_memory
                        
                        print(f"Memory after {i+1} queries: {current_memory:.2f}MB (+{memory_increase:.2f}MB)")
                        
                        # Memory should not increase by more than 50MB
                        assert memory_increase < 50, f"Memory leak detected: +{memory_increase:.2f}MB"
        
        # Final memory check
        final_memory = process.memory_info().rss / 1024 / 1024
        total_increase = final_memory - initial_memory
        
        print(f"Final memory usage: {final_memory:.2f}MB (+{total_increase:.2f}MB)")
        
        # Total memory increase should be reasonable
        assert total_increase < 100, f"Excessive memory usage: +{total_increase:.2f}MB"
        
        await adapter.close()

    @pytest.mark.asyncio
    async def test_error_recovery_performance(self):
        """Test performance degradation during error recovery"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.KB_FIRST, max_retries=2)
        
        # Mock intermittent failures then success
        call_count = 0
        
        async def mock_post_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count <= 2:  # First 2 calls fail
                raise ConnectionError("Simulated network error")
            else:  # Subsequent calls succeed
                mock_resp = AsyncMock()
                mock_resp.status = 200
                mock_resp.json = AsyncMock(return_value={"results": []})
                return mock_resp.__aenter__.return_value
        
        with patch('aiohttp.ClientSession.post', side_effect=mock_post_side_effect):
            with patch.object(adapter, '_search_local_files', return_value="fallback content"):
                
                start_time = time.time()
                
                # This should fallback to file search quickly
                result = await adapter.search("test query")
                
                end_time = time.time()
                recovery_time = (end_time - start_time) * 1000
                
                print(f"Error recovery time: {recovery_time:.2f}ms")
                
                # Should recover quickly via fallback
                assert recovery_time < 1000, f"Recovery time {recovery_time}ms too slow"
                assert result.file_content == "fallback content"
                assert not result.kb_available
        
        await adapter.close()

    @pytest.mark.asyncio
    async def test_circuit_breaker_performance_impact(self):
        """Test circuit breaker doesn't significantly impact performance"""
        
        adapter = KnowledgeAdapter(circuit_breaker_threshold=2)
        
        # Force circuit breaker open
        adapter.circuit_breaker._is_open = True
        adapter.circuit_breaker._failure_count = 10
        
        with patch.object(adapter, '_search_local_files', return_value="fallback content"):
            
            start_time = time.time()
            
            # Should fail immediately without network calls
            try:
                await adapter.search("test query") 
            except Exception:
                pass
            
            end_time = time.time()
            circuit_breaker_time = (end_time - start_time) * 1000
            
            print(f"Circuit breaker response time: {circuit_breaker_time:.2f}ms")
            
            # Circuit breaker should fail fast (<10ms)
            assert circuit_breaker_time < 10, f"Circuit breaker too slow: {circuit_breaker_time}ms"
        
        await adapter.close()


class TestLoadTesting:
    """Load testing scenarios"""

    @pytest.mark.asyncio
    async def test_sustained_load(self):
        """Test performance under sustained load"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.HYBRID)
        
        mock_kb_response = {"results": [{"content": "load test", "score": 0.8}]}
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_kb_response)
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            with patch.object(adapter, '_search_local_files', return_value="file content"):
                
                # Simulate 5 minutes of load (scaled down for testing)
                duration_seconds = 10  # 10 seconds for test
                target_qps = 5  # 5 queries per second
                
                start_time = time.time()
                query_count = 0
                latencies = []
                
                while time.time() - start_time < duration_seconds:
                    batch_start = time.time()
                    
                    # Send batch of queries
                    batch_tasks = [
                        adapter.search(f"load test query {query_count + i}")
                        for i in range(target_qps)
                    ]
                    
                    await asyncio.gather(*batch_tasks)
                    
                    batch_end = time.time()
                    batch_latency = (batch_end - batch_start) * 1000
                    latencies.append(batch_latency)
                    
                    query_count += target_qps
                    
                    # Wait to maintain target QPS
                    elapsed = batch_end - batch_start
                    if elapsed < 1.0:
                        await asyncio.sleep(1.0 - elapsed)
                
                end_time = time.time()
                actual_duration = end_time - start_time
                actual_qps = query_count / actual_duration
                
                avg_latency = sum(latencies) / len(latencies)
                max_latency = max(latencies)
                
                print(f"Sustained load results:")
                print(f"  Duration: {actual_duration:.2f}s")
                print(f"  Total queries: {query_count}")
                print(f"  Actual QPS: {actual_qps:.2f}")
                print(f"  Average batch latency: {avg_latency:.2f}ms")
                print(f"  Max batch latency: {max_latency:.2f}ms")
                
                # Performance assertions
                assert actual_qps >= target_qps * 0.8, f"QPS too low: {actual_qps:.2f}"
                assert avg_latency < 1000, f"Average latency too high: {avg_latency:.2f}ms"
                assert max_latency < 2000, f"Max latency too high: {max_latency:.2f}ms"
        
        await adapter.close()

    @pytest.mark.asyncio
    async def test_burst_traffic(self):
        """Test handling of burst traffic patterns"""
        
        adapter = KnowledgeAdapter(strategy=SearchStrategy.HYBRID)
        
        mock_kb_response = {"results": [{"content": "burst test", "score": 0.9}]}
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_kb_response)
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            with patch.object(adapter, '_search_local_files', return_value="file content"):
                
                # Simulate burst pattern: 50 queries in quick succession
                burst_size = 50
                
                start_time = time.time()
                
                tasks = [
                    adapter.search(f"burst query {i}")
                    for i in range(burst_size)
                ]
                
                results = await asyncio.gather(*tasks)
                
                end_time = time.time()
                burst_duration = end_time - start_time
                burst_qps = burst_size / burst_duration
                
                print(f"Burst traffic results:")
                print(f"  Burst size: {burst_size} queries")
                print(f"  Burst duration: {burst_duration:.2f}s")
                print(f"  Burst QPS: {burst_qps:.2f}")
                
                assert len(results) == burst_size
                assert all(isinstance(r, KnowledgeResponse) for r in results)
                
                # Should handle burst gracefully
                assert burst_qps > 20, f"Burst handling too slow: {burst_qps:.2f} QPS"
                assert burst_duration < 5, f"Burst took too long: {burst_duration:.2f}s"
        
        await adapter.close()


class TestScalabilityLimits:
    """Test scalability limits and breaking points"""

    @pytest.mark.asyncio
    async def test_connection_pool_limits(self):
        """Test behavior at connection pool limits"""
        
        # Adapter with small connection pool
        adapter = KnowledgeAdapter(strategy=SearchStrategy.KB_FIRST)
        
        mock_kb_response = {"results": [{"content": "pool test", "score": 0.9}]}
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_kb_response)
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            # Create more concurrent requests than pool size
            num_requests = 15  # More than default pool limit (10)
            
            start_time = time.time()
            
            tasks = [
                adapter.search(f"pool test {i}")
                for i in range(num_requests)
            ]
            
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            print(f"Connection pool test:")
            print(f"  Requests: {num_requests}")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Effective QPS: {num_requests/total_time:.2f}")
            
            assert len(results) == num_requests
            assert all(isinstance(r, KnowledgeResponse) for r in results)
            
            # Should still complete in reasonable time
            assert total_time < 10, f"Pool saturation caused excessive delay: {total_time:.2f}s"
        
        await adapter.close()

    def test_statistics_memory_growth(self):
        """Test statistics don't cause memory leaks"""
        
        adapter = KnowledgeAdapter()
        
        # Simulate lots of queries to check statistics memory usage
        for i in range(1000):
            adapter.stats.total_queries += 1
            adapter.stats.kb_successes += 1
            adapter.stats.total_response_time_ms += 100
            
            # Add strategy usage
            strategy = SearchStrategy.HYBRID
            if strategy not in adapter.stats.strategy_usage:
                adapter.stats.strategy_usage[strategy] = 0
            adapter.stats.strategy_usage[strategy] += 1
        
        # Statistics should remain reasonable in size
        stats = adapter.get_statistics()
        
        assert stats.total_queries == 1000
        assert stats.average_response_time_ms == 100
        assert len(adapter.stats.strategy_usage) == 1  # Should not grow indefinitely
        
        print(f"Statistics after 1000 operations:")
        print(f"  Total queries: {stats.total_queries}")
        print(f"  Average response time: {stats.average_response_time_ms}ms")
        print(f"  Strategy usage entries: {len(adapter.stats.strategy_usage)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to see print output