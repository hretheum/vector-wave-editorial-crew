#!/usr/bin/env python3
"""
Knowledge Base Connectivity Test Script

Tests the integration between AI Writing Flow and Knowledge Base:
1. Tests direct API connectivity on port 8082
2. Verifies enhanced tools can reach KB API
3. Tests fallback to file search functionality
4. Validates configuration loading
"""

import asyncio
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import aiohttp
import structlog
from ai_writing_flow.adapters.knowledge_adapter import (
    KnowledgeAdapter,
    SearchStrategy,
    get_adapter
)
from ai_writing_flow.tools.enhanced_knowledge_tools import (
    search_crewai_knowledge,
    get_flow_examples,
    troubleshoot_crewai
)
from knowledge_config import KnowledgeConfig

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger(__name__)


class KBConnectivityTest:
    """Test suite for Knowledge Base connectivity"""
    
    def __init__(self):
        self.config = KnowledgeConfig()
        self.results = {
            "config_validation": False,
            "direct_api_test": False,
            "adapter_initialization": False,
            "enhanced_tools_test": False,
            "fallback_test": False,
            "error_handling_test": False
        }
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run complete test suite"""
        logger.info("🧪 Starting Knowledge Base connectivity tests")
        
        test_methods = [
            ("config_validation", self.test_config_validation),
            ("direct_api_test", self.test_direct_api_connectivity),
            ("adapter_initialization", self.test_adapter_initialization),
            ("enhanced_tools_test", self.test_enhanced_tools),
            ("fallback_test", self.test_fallback_functionality),
            ("error_handling_test", self.test_error_handling)
        ]
        
        for test_name, test_method in test_methods:
            try:
                logger.info(f"Running test: {test_name}")
                result = await test_method()
                self.results[test_name] = result
                status = "✅ PASS" if result else "❌ FAIL"
                logger.info(f"{status} {test_name}")
            except Exception as e:
                logger.error(f"❌ FAIL {test_name}: {str(e)}")
                self.results[test_name] = False
        
        return self.results
    
    async def test_config_validation(self) -> bool:
        """Test configuration validation"""
        try:
            # Print current configuration
            print("\n🔧 Current Configuration:")
            print(f"  KB API URL: {self.config.KB_API_URL}")
            print(f"  Timeout: {self.config.KB_TIMEOUT}s")
            print(f"  Strategy: {self.config.DEFAULT_STRATEGY.value}")
            print(f"  Docs Path: {self.config.DOCS_PATH}")
            
            # Validate configuration
            issues = self.config.validate_config()
            if issues:
                print("⚠️  Configuration Issues:")
                for issue in issues:
                    print(f"    - {issue}")
                return False
            
            print("✅ Configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Config validation error: {e}")
            return False
    
    async def test_direct_api_connectivity(self) -> bool:
        """Test direct connection to Knowledge Base API"""
        try:
            timeout = aiohttp.ClientTimeout(total=5.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Test health endpoint
                async with session.get(f"{self.config.KB_API_URL}/api/v1/knowledge/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ KB Health check: {data}")
                        return True
                    else:
                        print(f"❌ KB Health check failed: {response.status}")
                        return False
                        
        except aiohttp.ClientConnectorError:
            print(f"❌ Cannot connect to KB at {self.config.KB_API_URL}")
            print("   Make sure Knowledge Base is running on port 8082")
            return False
        except Exception as e:
            logger.error(f"Direct API test error: {e}")
            return False
    
    async def test_adapter_initialization(self) -> bool:
        """Test KnowledgeAdapter initialization"""
        try:
            adapter = get_adapter()
            print(f"✅ Adapter initialized with strategy: {adapter.strategy.value}")
            
            # Test adapter stats
            stats = adapter.get_statistics()
            print(f"✅ Adapter stats: total_queries={stats.total_queries}, kb_successes={stats.kb_successes}")
            return True
            
        except Exception as e:
            logger.error(f"Adapter initialization error: {e}")
            return False
    
    async def test_enhanced_tools(self) -> bool:
        """Test enhanced knowledge tools"""
        try:
            # Test search_crewai_knowledge tool
            print("\n🔍 Testing search_crewai_knowledge tool...")
            # Note: CrewAI tools are not directly callable, they're designed for agent use
            # Instead, test the underlying adapter directly
            adapter = get_adapter()
            search_result = await adapter.search("CrewAI agent configuration", limit=3)
            
            if search_result and hasattr(search_result, 'results'):
                print(f"✅ Search returned {len(search_result.results)} results")
                print(f"   Strategy used: {search_result.strategy_used.value}")
                print(f"   Response time: {search_result.response_time_ms:.2f}ms")
                return True
            else:
                print("❌ Search returned no results")
                return False
                
        except Exception as e:
            logger.error(f"Enhanced tools test error: {e}")
            return False
    
    async def test_fallback_functionality(self) -> bool:
        """Test fallback to file search when KB is unavailable"""
        try:
            # Create adapter with unreachable KB URL to force fallback
            fallback_adapter = KnowledgeAdapter(
                strategy=SearchStrategy.HYBRID,
                kb_api_url="http://localhost:9999",  # Non-existent port
                timeout=1.0,
                max_retries=1,
                docs_path=str(self.config.DOCS_PATH)
            )
            
            # Test search (should fallback to file search)
            results = await fallback_adapter.search("CrewAI setup", limit=2)
            
            if results and hasattr(results, 'results'):
                print(f"✅ Fallback search returned {len(results.results)} results")
                print(f"   Strategy used: {results.strategy_used.value}")
                return True
            else:
                print("❌ Fallback search failed")
                return False
                
        except Exception as e:
            logger.error(f"Fallback test error: {e}")
            return False
    
    async def test_error_handling(self) -> bool:
        """Test error handling scenarios"""
        try:
            adapter = get_adapter()
            
            # Test with empty query
            results = await adapter.search("", limit=1)
            print(f"✅ Empty query handled gracefully: {len(results.results) if hasattr(results, 'results') else 0} results")
            
            # Test with very long query
            long_query = "CrewAI " * 100
            results = await adapter.search(long_query, limit=1)
            print(f"✅ Long query handled gracefully: {len(results.results) if hasattr(results, 'results') else 0} results")
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling test error: {e}")
            return False
    
    def print_summary(self):
        """Print test summary"""
        passed = sum(1 for result in self.results.values() if result)
        total = len(self.results)
        
        print(f"\n📊 Test Summary: {passed}/{total} tests passed")
        print("=" * 50)
        
        for test_name, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
        
        if passed == total:
            print("\n🎉 All tests passed! KB integration is working correctly.")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed. Check configuration and KB status.")
        
        return passed == total


async def main():
    """Main test runner"""
    test_suite = KBConnectivityTest()
    
    print("🚀 Knowledge Base Connectivity Test Suite")
    print("=" * 50)
    
    # Run all tests
    results = await test_suite.run_all_tests()
    
    # Print summary
    success = test_suite.print_summary()
    
    # Additional diagnostics
    print(f"\n🔧 Environment Information:")
    print(f"  Python version: {sys.version}")
    print(f"  Working directory: {os.getcwd()}")
    print(f"  KB_API_URL: {os.getenv('KB_API_URL', 'Not set')}")
    print(f"  KB_SEARCH_STRATEGY: {os.getenv('KB_SEARCH_STRATEGY', 'Not set')}")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())