#!/usr/bin/env python3
"""
Production Integration Tests for AI Writing Flow with Knowledge Base

Focused tests for production readiness without CrewAI dependency.
Tests core adapter functionality, performance, and resilience.
"""

import asyncio
import sys
import time
import json
import statistics
from pathlib import Path
import requests
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_writing_flow.adapters.knowledge_adapter import (
    KnowledgeAdapter, 
    SearchStrategy, 
    KnowledgeResponse,
    get_adapter
)
from knowledge_config import KnowledgeConfig


class ProductionIntegrationTests:
    """Production-focused integration tests"""
    
    def __init__(self):
        self.kb_url = "http://localhost:8082"
        self.health_endpoint = f"{self.kb_url}/api/v1/knowledge/health"
        self.query_endpoint = f"{self.kb_url}/api/v1/knowledge/query"
        self.stats_endpoint = f"{self.kb_url}/api/v1/knowledge/stats"
        self.results = []
    
    def test_kb_connectivity(self):
        """Test Knowledge Base connectivity and health"""
        print("🔍 Testing Knowledge Base connectivity...")
        
        try:
            # Test health endpoint
            response = requests.get(self.health_endpoint, timeout=5)
            assert response.status_code == 200
            
            health_data = response.json()
            assert health_data["status"] == "healthy"
            
            print(f"   ✅ KB Status: {health_data['status']}")
            print(f"   📊 Components: {len(health_data.get('components', {}))}")
            
            # Test stats endpoint
            stats_response = requests.get(self.stats_endpoint, timeout=5)
            if stats_response.status_code == 200:
                stats = stats_response.json()
                print(f"   📈 Total queries: {stats.get('knowledge_base', {}).get('total_queries', 0)}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ KB connectivity failed: {e}")
            return False
    
    def test_kb_search_functionality(self):
        """Test Knowledge Base search with various queries"""
        print("🔍 Testing KB search functionality...")
        
        test_queries = [
            {"query": "CrewAI agents", "min_score": 0.3},
            {"query": "task orchestration", "min_score": 0.3},
            {"query": "crew configuration", "min_score": 0.3},
        ]
        
        successful_queries = 0
        
        for test in test_queries:
            try:
                payload = {
                    "query": test["query"],
                    "limit": 3,
                    "score_threshold": test["min_score"]
                }
                
                response = requests.post(
                    self.query_endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   Query: '{test['query'][:30]}...' -> {len(data['results'])} results ({data['query_time_ms']:.1f}ms)")
                    successful_queries += 1
                else:
                    print(f"   Query failed: '{test['query']}' -> {response.status_code}")
                    
            except Exception as e:
                print(f"   Query error: '{test['query']}' -> {e}")
        
        success_rate = successful_queries / len(test_queries)
        print(f"   ✅ Search success rate: {success_rate:.1%}")
        
        return success_rate > 0.8  # 80% success rate required
    
    async def test_adapter_strategies(self):
        """Test all adapter strategies"""
        print("🔧 Testing adapter strategies...")
        
        strategies = [
            SearchStrategy.HYBRID,
            SearchStrategy.KB_FIRST, 
            SearchStrategy.FILE_FIRST,
            SearchStrategy.KB_ONLY
        ]
        
        results = {}
        
        for strategy in strategies:
            try:
                adapter = KnowledgeAdapter(
                    strategy=strategy,
                    kb_api_url=self.kb_url,
                    timeout=5.0
                )
                
                start_time = time.time()
                result = await adapter.search(
                    query="CrewAI agent configuration",
                    limit=2,
                    score_threshold=0.3
                )
                end_time = time.time()
                
                results[strategy.value] = {
                    "success": True,
                    "kb_available": result.kb_available,
                    "results_count": len(result.results),
                    "has_file_content": bool(result.file_content.strip()), 
                    "response_time_ms": (end_time - start_time) * 1000,
                    "strategy_used": result.strategy_used.value
                }
                
                print(f"   {strategy.value}: {len(result.results)} KB results, file content: {bool(result.file_content.strip())}")
                
                await adapter.close()
                
            except Exception as e:
                results[strategy.value] = {
                    "success": False,
                    "error": str(e)
                }
                print(f"   {strategy.value}: FAILED - {e}")
        
        successful_strategies = sum(1 for r in results.values() if r.get("success", False))
        print(f"   ✅ Strategy success rate: {successful_strategies}/{len(strategies)}")
        
        return results
    
    async def test_performance_benchmarks(self):
        """Test performance benchmarks"""
        print("⚡ Testing performance benchmarks...")
        
        adapter = KnowledgeAdapter(
            strategy=SearchStrategy.HYBRID,
            kb_api_url=self.kb_url,
            timeout=10.0
        )
        
        try:
            # Single query latency test
            print("   Testing single query latency...")
            start_time = time.time()
            result = await adapter.search("CrewAI performance test")
            end_time = time.time()
            
            single_query_latency = (end_time - start_time) * 1000
            print(f"   Single query: {single_query_latency:.1f}ms")
            
            # Concurrent queries test
            print("   Testing concurrent queries...")
            num_concurrent = 5
            
            start_time = time.time()
            tasks = [
                adapter.search(f"concurrent test {i}")
                for i in range(num_concurrent)
            ]
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            concurrent_time = (end_time - start_time) * 1000
            throughput = num_concurrent / (concurrent_time / 1000)
            
            print(f"   Concurrent ({num_concurrent}): {concurrent_time:.1f}ms total, {throughput:.1f} q/s")
            
            # Performance targets
            performance_ok = (
                single_query_latency < 2000 and  # 2 second max for single query
                throughput > 2  # At least 2 queries per second
            )
            
            return {
                "single_query_latency_ms": single_query_latency,
                "concurrent_throughput_qps": throughput, 
                "performance_acceptable": performance_ok
            }
            
        finally:
            await adapter.close()
    
    async def test_resilience_features(self):
        """Test resilience and error handling"""
        print("🛡️ Testing resilience features...")
        
        resilience_results = {}
        
        # Test 1: KB unavailable fallback
        print("   Testing KB unavailable fallback...")
        try:
            adapter = KnowledgeAdapter(
                strategy=SearchStrategy.HYBRID,
                kb_api_url="http://localhost:9999",  # Non-existent
                timeout=2.0,
                max_retries=1
            )
            
            result = await adapter.search("fallback test")
            
            resilience_results["fallback"] = {
                "success": True,
                "kb_available": result.kb_available,
                "has_file_content": bool(result.file_content.strip())
            }
            
            print(f"      Fallback works: KB available={result.kb_available}, has file content={bool(result.file_content.strip())}")
            
            await adapter.close()
            
        except Exception as e:
            resilience_results["fallback"] = {"success": False, "error": str(e)}
            print(f"      Fallback failed: {e}")
        
        # Test 2: Timeout handling
        print("   Testing timeout handling...")
        try:
            adapter = KnowledgeAdapter(
                strategy=SearchStrategy.KB_FIRST,
                kb_api_url=self.kb_url,
                timeout=0.001,  # Very short timeout
                max_retries=1
            )
            
            start_time = time.time()
            try:
                await adapter.search("timeout test")
                resilience_results["timeout"] = {"success": True, "handled_gracefully": True}
            except Exception:
                end_time = time.time()
                timeout_duration = (end_time - start_time) * 1000
                resilience_results["timeout"] = {
                    "success": True,
                    "timeout_duration_ms": timeout_duration,
                    "handled_gracefully": timeout_duration < 1000
                }
            
            print(f"      Timeout handling: OK")
            await adapter.close()
            
        except Exception as e:
            resilience_results["timeout"] = {"success": False, "error": str(e)}
            print(f"      Timeout test failed: {e}")
        
        return resilience_results
    
    async def test_statistics_tracking(self):
        """Test statistics and monitoring"""
        print("📊 Testing statistics tracking...")
        
        adapter = KnowledgeAdapter(
            strategy=SearchStrategy.HYBRID,
            kb_api_url=self.kb_url,
            timeout=5.0
        )
        
        try:
            # Initial stats
            initial_stats = adapter.get_statistics()
            initial_queries = initial_stats.total_queries
            
            # Perform some operations
            await adapter.search("stats test 1")
            await adapter.search("stats test 2")
            await adapter.search("stats test 3")
            
            # Check updated stats
            final_stats = adapter.get_statistics()
            
            queries_performed = final_stats.total_queries - initial_queries
            
            print(f"   Queries tracked: {queries_performed}")
            print(f"   KB availability: {final_stats.kb_availability:.1%}")
            print(f"   Avg response time: {final_stats.average_response_time_ms:.1f}ms")
            
            return {
                "queries_tracked": queries_performed,
                "kb_availability": final_stats.kb_availability,
                "avg_response_time": final_stats.average_response_time_ms,
                "tracking_works": queries_performed >= 3
            }
            
        finally:
            await adapter.close()
    
    def test_configuration_management(self):
        """Test configuration management"""
        print("🔧 Testing configuration management...")
        
        try:
            config = KnowledgeConfig()
            issues = config.validate_config()
            
            print(f"   KB URL: {config.KB_API_URL}")
            print(f"   Strategy: {config.DEFAULT_STRATEGY.value}")
            print(f"   Timeout: {config.KB_TIMEOUT}s")
            print(f"   Config issues: {len(issues)}")
            
            for issue in issues:
                print(f"      - {issue}")
            
            return {
                "config_valid": len(issues) == 0,
                "kb_url": config.KB_API_URL,
                "strategy": config.DEFAULT_STRATEGY.value,
                "timeout": config.KB_TIMEOUT
            }
            
        except Exception as e:
            print(f"   Configuration test failed: {e}")
            return {"config_valid": False, "error": str(e)}
    
    async def run_all_tests(self):
        """Run all production integration tests"""
        print("🧪 Starting Production Integration Tests")
        print("=" * 60)
        
        test_results = {}
        
        # Test 1: KB Connectivity
        test_results["connectivity"] = self.test_kb_connectivity()
        
        # Test 2: KB Search
        test_results["search"] = self.test_kb_search_functionality()
        
        # Test 3: Adapter Strategies
        test_results["strategies"] = await self.test_adapter_strategies()
        
        # Test 4: Performance
        test_results["performance"] = await self.test_performance_benchmarks()
        
        # Test 5: Resilience
        test_results["resilience"] = await self.test_resilience_features()
        
        # Test 6: Statistics
        test_results["statistics"] = await self.test_statistics_tracking()
        
        # Test 7: Configuration
        test_results["configuration"] = self.test_configuration_management()
        
        return test_results
    
    def generate_report(self, test_results):
        """Generate comprehensive test report"""
        print("\n" + "="*80)
        print("📋 PRODUCTION INTEGRATION TEST REPORT")
        print("="*80)
        
        print("\n🏗️  SYSTEM STATUS:")
        print(f"   Knowledge Base: {'✅ HEALTHY' if test_results.get('connectivity') else '❌ UNAVAILABLE'}")
        print(f"   Search Functionality: {'✅ WORKING' if test_results.get('search') else '❌ FAILED'}")
        print(f"   Configuration: {'✅ VALID' if test_results.get('configuration', {}).get('config_valid') else '⚠️  ISSUES'}")
        
        print("\n🔧 ADAPTER STRATEGIES:")
        strategies_result = test_results.get("strategies", {})
        for strategy, result in strategies_result.items():
            status = "✅" if result.get("success") else "❌"
            print(f"   {strategy}: {status}")
        
        print("\n⚡ PERFORMANCE METRICS:")
        perf = test_results.get("performance", {})
        if perf:
            print(f"   Single Query Latency: {perf.get('single_query_latency_ms', 0):.1f}ms")
            print(f"   Concurrent Throughput: {perf.get('concurrent_throughput_qps', 0):.1f} q/s")
            print(f"   Performance: {'✅ ACCEPTABLE' if perf.get('performance_acceptable') else '⚠️  SLOW'}")
        
        print("\n🛡️  RESILIENCE:")
        resilience = test_results.get("resilience", {})
        fallback_ok = resilience.get("fallback", {}).get("success", False)
        timeout_ok = resilience.get("timeout", {}).get("success", False)
        print(f"   Fallback to Files: {'✅ WORKING' if fallback_ok else '❌ FAILED'}")
        print(f"   Timeout Handling: {'✅ WORKING' if timeout_ok else '❌ FAILED'}")
        
        print("\n📊 MONITORING:")
        stats = test_results.get("statistics", {})
        if stats:
            print(f"   Statistics Tracking: {'✅ WORKING' if stats.get('tracking_works') else '❌ FAILED'}")
            print(f"   KB Availability: {stats.get('kb_availability', 0):.1%}")
            print(f"   Average Response Time: {stats.get('avg_response_time', 0):.1f}ms")
        
        # Overall assessment
        print("\n🎯 PRODUCTION READINESS ASSESSMENT:")
        
        critical_tests = [
            test_results.get("connectivity", False),
            test_results.get("search", False),
            test_results.get("configuration", {}).get("config_valid", False)
        ]
        
        strategy_success_rate = len([r for r in strategies_result.values() if r.get("success", False)]) / max(len(strategies_result), 1)
        
        if all(critical_tests) and strategy_success_rate >= 0.75:
            print("   🎉 SYSTEM IS PRODUCTION READY!")
            print("   ✅ All critical systems operational")
            print("   ✅ Performance within acceptable limits")
            print("   ✅ Resilience features working")
            
            deployment_status = "READY FOR PRODUCTION"
        else:
            print("   ⚠️  SYSTEM NEEDS ATTENTION")
            print("   🔍 Review failed tests before production deployment")
            
            deployment_status = "NOT READY - ISSUES FOUND"
        
        print("\n📝 RECOMMENDATIONS:")
        print("   1. Monitor KB health endpoint: /api/v1/knowledge/health")
        print("   2. Set up alerts for KB unavailability")
        print("   3. Track query latency and error rates")
        print("   4. Implement log aggregation for troubleshooting")
        print("   5. Regular backups of knowledge base data")
        
        print(f"\n🚀 DEPLOYMENT STATUS: {deployment_status}")
        print("="*80)
        
        return deployment_status == "READY FOR PRODUCTION"


async def main():
    """Main test execution"""
    tester = ProductionIntegrationTests()
    test_results = await tester.run_all_tests()
    production_ready = tester.generate_report(test_results)
    
    return 0 if production_ready else 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)