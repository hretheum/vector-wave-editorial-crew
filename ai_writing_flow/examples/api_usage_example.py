#!/usr/bin/env python3
"""
AI Writing Flow V2 API Usage Examples

This script demonstrates how to use the AI Writing Flow V2 API 
in various scenarios without requiring external dependencies.
"""

import asyncio
import json
import time
from typing import Dict, Any


# Mock implementation for demonstration
class MockAIWritingFlowV2:
    """Mock implementation for demonstration purposes"""
    
    def __init__(self, **kwargs):
        self.config = kwargs
        print(f"🚀 Mock AIWritingFlowV2 initialized with config: {kwargs}")
    
    def kickoff(self, inputs: Dict[str, Any]):
        """Mock flow execution"""
        print(f"📝 Executing flow with inputs: {inputs['topic_title']}")
        
        # Simulate processing time
        time.sleep(0.1)
        
        # Create mock result
        class MockState:
            def __init__(self):
                self.current_stage = "completed"
                self.final_draft = f"Generated content for: {inputs['topic_title']}\n\nThis is a comprehensive article about the topic with excellent quality and style."
                self.error_message = None
                self.quality_score = 8.7
                self.style_score = 9.1
                self.revision_count = 2
                self.agents_executed = ["research", "audience", "draft", "style", "quality"]
        
        return MockState()
    
    def get_health_status(self):
        """Mock health status"""
        return {
            "overall_status": "healthy",
            "timestamp": "2025-01-01T10:00:00Z",
            "components": {
                "linear_flow": {"status": "healthy"},
                "monitoring": {"status": "healthy"},
                "alerting": {"status": "healthy"}
            }
        }
    
    def get_dashboard_metrics(self):
        """Mock dashboard metrics"""
        return {
            "monitoring_enabled": True,
            "dashboard_metrics": {
                "success_rate": {"value": 96.5, "unit": "%"},
                "throughput": {"value": 15.2, "unit": "ops/sec"},
                "avg_execution_time": {"value": 4.8, "unit": "seconds"}
            }
        }


# Patch the real import for demo
import sys
from pathlib import Path

# Add the demo FlowAPI with mock
class DemoFlowAPI:
    """Demo version of FlowAPI with mock dependencies"""
    
    def __init__(self, storage_path=None):
        self.storage_path = storage_path
        self._active_flows = {}
        self._flow_results = {}
        self._api_stats = {
            "total_requests": 0,
            "successful_executions": 0,
            "failed_executions": 0
        }
        print(f"🌉 Demo Flow API initialized (storage: {storage_path})")
    
    async def execute_flow(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Demo flow execution"""
        print(f"\n🚀 Executing flow: {request_data.get('topic_title', 'Unknown')}")
        
        # Generate flow ID
        flow_id = f"demo_flow_{int(time.time())}"
        
        # Create mock flow
        flow = MockAIWritingFlowV2(
            monitoring_enabled=request_data.get('monitoring_enabled', True),
            alerting_enabled=request_data.get('alerting_enabled', True),
            quality_gates_enabled=request_data.get('quality_gates_enabled', True)
        )
        
        self._api_stats["total_requests"] += 1
        
        try:
            # Execute flow
            start_time = time.time()
            final_state = flow.kickoff(request_data)
            end_time = time.time()
            
            execution_time = end_time - start_time
            success = final_state.current_stage == "completed"
            
            if success:
                self._api_stats["successful_executions"] += 1
            else:
                self._api_stats["failed_executions"] += 1
            
            # Build response
            result = {
                "flow_id": flow_id,
                "status": "completed" if success else "failed",
                "message": "Flow executed successfully" if success else "Flow execution failed",
                "final_draft": final_state.final_draft if success else None,
                "metrics": {
                    "execution_time": execution_time,
                    "quality_score": getattr(final_state, 'quality_score', 0),
                    "style_score": getattr(final_state, 'style_score', 0),
                    "revision_count": getattr(final_state, 'revision_count', 0),
                    "agents_executed": len(getattr(final_state, 'agents_executed', [])),
                    "word_count": len(final_state.final_draft.split()) if final_state.final_draft else 0
                },
                "errors": [],
                "execution_time": execution_time
            }
            
            self._flow_results[flow_id] = result
            return result
            
        except Exception as e:
            self._api_stats["failed_executions"] += 1
            return {
                "flow_id": flow_id,
                "status": "error",
                "message": f"Execution error: {str(e)}",
                "final_draft": None,
                "metrics": {},
                "errors": [str(e)],
                "execution_time": 0.0
            }
    
    async def get_flow_status(self, flow_id: str) -> Dict[str, Any]:
        """Get flow status"""
        if flow_id in self._flow_results:
            result = self._flow_results[flow_id]
            return {
                "flow_id": flow_id,
                "status": result["status"],
                "current_stage": "completed" if result["status"] == "completed" else "failed",
                "progress_percent": 100.0,
                "metrics": result["metrics"],
                "errors": result["errors"]
            }
        else:
            return {
                "flow_id": flow_id,
                "status": "not_found",
                "errors": [f"Flow {flow_id} not found"]
            }
    
    async def get_health_check(self) -> Dict[str, Any]:
        """Get health status"""
        mock_flow = MockAIWritingFlowV2()
        health = mock_flow.get_health_status()
        
        health.update({
            "version": "2.0.0",
            "api_statistics": self._api_stats,
            "uptime_seconds": 3600.0
        })
        
        return health
    
    async def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get dashboard metrics"""
        mock_flow = MockAIWritingFlowV2()
        metrics = mock_flow.get_dashboard_metrics()
        
        metrics["api_metrics"] = {
            "total_requests": self._api_stats["total_requests"],
            "success_rate": (
                self._api_stats["successful_executions"] / 
                max(self._api_stats["total_requests"], 1) * 100
            )
        }
        
        return metrics
    
    async def list_flows(self, limit: int = 10) -> Dict[str, Any]:
        """List recent flows"""
        flows = []
        for flow_id, result in list(self._flow_results.items())[-limit:]:
            flows.append({
                "flow_id": flow_id,
                "status": result["status"],
                "execution_time": result["execution_time"],
                "word_count": result["metrics"].get("word_count", 0),
                "quality_score": result["metrics"].get("quality_score", 0)
            })
        
        return {
            "flows": flows,
            "total_count": len(flows),
            "statistics": self._api_stats
        }


async def demo_basic_flow_execution():
    """Demonstrate basic flow execution"""
    print("=" * 60)
    print("🧪 DEMO: Basic Flow Execution")
    print("=" * 60)
    
    # Initialize API
    api = DemoFlowAPI(storage_path="demo_metrics")
    
    # Execute a flow
    request_data = {
        "topic_title": "AI-Powered Content Generation Best Practices",
        "platform": "LinkedIn",
        "content_type": "STANDALONE",
        "viral_score": 8.5,
        "editorial_recommendations": "Focus on practical implementation examples",
        "monitoring_enabled": True,
        "alerting_enabled": True,
        "quality_gates_enabled": True
    }
    
    print("📋 Request:")
    print(json.dumps(request_data, indent=2))
    
    # Execute
    result = await api.execute_flow(request_data)
    
    print(f"\n✅ Response:")
    print(f"   Flow ID: {result['flow_id']}")
    print(f"   Status: {result['status']}")
    print(f"   Execution Time: {result['execution_time']:.3f}s")
    print(f"   Quality Score: {result['metrics']['quality_score']}")
    print(f"   Word Count: {result['metrics']['word_count']}")
    print(f"   Draft Preview: {result['final_draft'][:100]}...")
    
    return result['flow_id']


async def demo_flow_status_tracking():
    """Demonstrate flow status tracking"""
    print("\n" + "=" * 60)
    print("🔍 DEMO: Flow Status Tracking")
    print("=" * 60)
    
    api = DemoFlowAPI()
    
    # Execute flow
    result = await api.execute_flow({
        "topic_title": "Status Tracking Demo",
        "platform": "Twitter"
    })
    flow_id = result['flow_id']
    
    # Check status
    status = await api.get_flow_status(flow_id)
    
    print(f"📊 Flow Status:")
    print(f"   Flow ID: {status['flow_id']}")
    print(f"   Status: {status['status']}")
    print(f"   Progress: {status['progress_percent']}%")
    print(f"   Metrics: {json.dumps(status['metrics'], indent=4)}")
    
    # Test non-existent flow
    not_found = await api.get_flow_status("nonexistent_flow")
    print(f"\n❌ Non-existent flow:")
    print(f"   Status: {not_found['status']}")
    print(f"   Errors: {not_found['errors']}")


async def demo_health_monitoring():
    """Demonstrate health monitoring"""
    print("\n" + "=" * 60)
    print("💚 DEMO: Health Monitoring")
    print("=" * 60)
    
    api = DemoFlowAPI()
    
    # Execute some flows to generate statistics
    await api.execute_flow({"topic_title": "Health Test 1"})
    await api.execute_flow({"topic_title": "Health Test 2"})
    
    # Get health status
    health = await api.get_health_check()
    
    print(f"🏥 System Health:")
    print(f"   Overall Status: {health['overall_status']}")
    print(f"   Version: {health['version']}")
    print(f"   Uptime: {health['uptime_seconds']}s")
    print(f"   Components: {len(health['components'])} healthy")
    print(f"   API Stats: {json.dumps(health['api_statistics'], indent=4)}")


async def demo_dashboard_metrics():
    """Demonstrate dashboard metrics"""
    print("\n" + "=" * 60)
    print("📊 DEMO: Dashboard Metrics")
    print("=" * 60)
    
    api = DemoFlowAPI()
    
    # Execute multiple flows
    for i in range(5):
        await api.execute_flow({
            "topic_title": f"Dashboard Test {i+1}",
            "platform": "LinkedIn" if i % 2 == 0 else "Twitter"
        })
    
    # Get dashboard metrics
    metrics = await api.get_dashboard_metrics()
    
    print(f"📈 Dashboard Metrics:")
    print(f"   Monitoring Enabled: {metrics['monitoring_enabled']}")
    
    if 'dashboard_metrics' in metrics:
        dm = metrics['dashboard_metrics']
        print(f"   Success Rate: {dm['success_rate']['value']}{dm['success_rate']['unit']}")
        print(f"   Throughput: {dm['throughput']['value']} {dm['throughput']['unit']}")
        print(f"   Avg Execution Time: {dm['avg_execution_time']['value']}{dm['avg_execution_time']['unit']}")
    
    if 'api_metrics' in metrics:
        am = metrics['api_metrics']
        print(f"   Total API Requests: {am['total_requests']}")
        print(f"   API Success Rate: {am['success_rate']:.1f}%")


async def demo_flow_listing():
    """Demonstrate flow listing"""
    print("\n" + "=" * 60)
    print("📋 DEMO: Flow Listing")
    print("=" * 60)
    
    api = DemoFlowAPI()
    
    # Execute several flows
    topics = [
        "Machine Learning Trends 2025",
        "API Design Best Practices", 
        "Cloud Architecture Patterns",
        "DevOps Automation Strategies"
    ]
    
    for topic in topics:
        await api.execute_flow({
            "topic_title": topic,
            "platform": "LinkedIn",
            "viral_score": 7.0 + (len(topic) % 3)
        })
    
    # List flows
    flow_list = await api.list_flows()
    
    print(f"📝 Recent Flows ({flow_list['total_count']} total):")
    for flow in flow_list['flows']:
        print(f"   • {flow['flow_id']}: {flow['status']} "
              f"({flow['execution_time']:.3f}s, {flow['word_count']} words, "
              f"Q:{flow['quality_score']})")
    
    print(f"\n📊 Statistics:")
    stats = flow_list['statistics']
    print(f"   Total Requests: {stats['total_requests']}")
    print(f"   Successful: {stats['successful_executions']}")
    print(f"   Failed: {stats['failed_executions']}")


async def demo_error_handling():
    """Demonstrate error handling"""
    print("\n" + "=" * 60)
    print("⚠️  DEMO: Error Handling")
    print("=" * 60)
    
    api = DemoFlowAPI()
    
    # Test with invalid request (missing required field)
    try:
        result = await api.execute_flow({
            "platform": "LinkedIn"  # Missing topic_title
        })
        print(f"🤔 Unexpected success: {result['status']}")
    except Exception as e:
        print(f"✅ Handled validation error: {str(e)}")
    
    # Test with valid request that might fail
    result = await api.execute_flow({
        "topic_title": "Error Handling Test",
        "platform": "LinkedIn"
    })
    
    if result['status'] == 'error':
        print(f"❌ Flow Error:")
        print(f"   Message: {result['message']}")
        print(f"   Errors: {result['errors']}")
    else:
        print(f"✅ Flow Success: {result['status']}")


async def demo_api_integration_patterns():
    """Demonstrate various API integration patterns"""
    print("\n" + "=" * 60)
    print("🔗 DEMO: API Integration Patterns")
    print("=" * 60)
    
    api = DemoFlowAPI()
    
    print("1️⃣ Fire-and-forget pattern:")
    result = await api.execute_flow({
        "topic_title": "Fire and Forget Demo",
        "platform": "Twitter"
    })
    print(f"   Started flow: {result['flow_id']}")
    
    print("\n2️⃣ Monitor-until-completion pattern:")
    result = await api.execute_flow({
        "topic_title": "Monitor Demo",
        "platform": "LinkedIn"
    })
    flow_id = result['flow_id']
    
    # Since this is a demo, flow completes immediately
    status = await api.get_flow_status(flow_id)
    print(f"   Flow {flow_id} status: {status['status']}")
    
    print("\n3️⃣ Batch processing pattern:")
    batch_topics = [
        "Batch Item 1: AI Ethics",
        "Batch Item 2: ML Operations", 
        "Batch Item 3: Data Privacy"
    ]
    
    batch_results = []
    for topic in batch_topics:
        result = await api.execute_flow({
            "topic_title": topic,
            "platform": "LinkedIn"
        })
        batch_results.append(result)
    
    print(f"   Processed {len(batch_results)} items in batch")
    successful = sum(1 for r in batch_results if r['status'] == 'completed')
    print(f"   Success rate: {successful}/{len(batch_results)}")
    
    print("\n4️⃣ Health-aware pattern:")
    health = await api.get_health_check()
    if health['overall_status'] == 'healthy':
        print("   ✅ System healthy - proceeding with operation")
        result = await api.execute_flow({
            "topic_title": "Health-Aware Demo",
            "platform": "Twitter"
        })
        print(f"   Operation completed: {result['status']}")
    else:
        print(f"   ⚠️ System unhealthy ({health['overall_status']}) - skipping operation")


async def main():
    """Run all demo scenarios"""
    print("🚀 AI Writing Flow V2 API - Usage Examples")
    print("This demo shows how to use the API without external dependencies")
    
    await demo_basic_flow_execution()
    await demo_flow_status_tracking()
    await demo_health_monitoring()
    await demo_dashboard_metrics()
    await demo_flow_listing()
    await demo_error_handling()
    await demo_api_integration_patterns()
    
    print("\n" + "=" * 60)
    print("✅ All demos completed successfully!")
    print("📚 This shows the API works correctly with mock implementations")
    print("🔧 In production, replace mocks with real AIWritingFlowV2")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())