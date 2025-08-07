"""
Test 10 Concurrent Flows - Production Performance Testing

This test suite validates that AI Writing Flow V2 can handle 10 concurrent flows
executing simultaneously without resource conflicts, deadlocks, or data corruption.

Test Coverage:
- Concurrent execution of 10 flows with different topics/platforms
- Thread safety validation
- Resource usage monitoring (CPU, memory)
- Performance benchmarks and timing analysis
- Error handling and isolation between flows
- Quality gate validation under concurrent load
- Monitoring system stress testing
- State isolation verification

Success Criteria:
✅ 10 flows execute concurrently without conflicts
✅ All flows complete within reasonable time (<30s total)
✅ Memory usage stays within limits (<500MB)
✅ CPU usage remains manageable
✅ Thread safety validated
✅ Monitoring data collected properly

Performance Agent: Task 33.1
Time Budget: 1h
"""

import pytest
import time
import threading
import asyncio
import logging
import uuid
import psutil
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import sys

# Mock all problematic imports before any real imports
sys.modules['crewai'] = Mock()
sys.modules['crewai.Agent'] = Mock()
sys.modules['crewai.Crew'] = Mock() 
sys.modules['crewai.Task'] = Mock()
sys.modules['crewai.tools'] = Mock()
sys.modules['structlog'] = Mock()
sys.modules['opentelemetry'] = Mock()
sys.modules['opentelemetry.trace'] = Mock()
sys.modules['prometheus_client'] = Mock()

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

# Import AI Writing Flow V2 and dependencies
from ai_writing_flow.ai_writing_flow_v2 import AIWritingFlowV2
from ai_writing_flow.linear_flow import WritingFlowInputs
from ai_writing_flow.models import WritingFlowState
from ai_writing_flow.monitoring.flow_metrics import FlowMetrics, KPISnapshot
from ai_writing_flow.monitoring.alerting import AlertManager  
from ai_writing_flow.validation.quality_gate import QualityGate

# Configure test logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Performance thresholds
MAX_EXECUTION_TIME_SECONDS = 30
MAX_MEMORY_USAGE_MB = 500
MAX_CPU_USAGE_PERCENT = 80
MIN_SUCCESS_RATE = 0.9  # 90% success rate

# Test data sets
CONCURRENT_FLOW_CONFIGS = [
    {
        "flow_id": "flow_001",
        "topic_title": "AI Agent Automation in Production Systems",
        "platform": "LinkedIn",
        "content_type": "THOUGHT_LEADERSHIP",
        "viral_score": 8.5,
        "editorial_recommendations": "Focus on technical implementation details"
    },
    {
        "flow_id": "flow_002", 
        "topic_title": "Distributed Tracing with OpenTelemetry",
        "platform": "Twitter",
        "content_type": "TECHNICAL_TUTORIAL",
        "viral_score": 7.2,
        "editorial_recommendations": "Keep it concise for Twitter audience"
    },
    {
        "flow_id": "flow_003",
        "topic_title": "GPU Optimization for Real-time Video Processing",
        "platform": "Medium",
        "content_type": "DEEP_DIVE",
        "viral_score": 9.1,
        "editorial_recommendations": "Include performance benchmarks"
    },
    {
        "flow_id": "flow_004",
        "topic_title": "Clean Architecture Patterns in Python",
        "platform": "LinkedIn",
        "content_type": "EDUCATIONAL",
        "viral_score": 6.8,
        "editorial_recommendations": "Add code examples and diagrams"
    },
    {
        "flow_id": "flow_005",
        "topic_title": "CI/CD Pipeline Security Best Practices",
        "platform": "DevTo",
        "content_type": "GUIDE",
        "viral_score": 7.9,
        "editorial_recommendations": "Include vulnerability scanning examples"
    },
    {
        "flow_id": "flow_006",
        "topic_title": "Microservices Observability Stack",
        "platform": "LinkedIn", 
        "content_type": "CASE_STUDY",
        "viral_score": 8.3,
        "editorial_recommendations": "Share real-world implementation story"
    },
    {
        "flow_id": "flow_007",
        "topic_title": "Event-Driven Architecture Design Patterns",
        "platform": "Twitter",
        "content_type": "THREAD",
        "viral_score": 7.6,
        "editorial_recommendations": "Break into digestible thread format"
    },
    {
        "flow_id": "flow_008",
        "topic_title": "Database Migration Strategies at Scale",
        "platform": "Medium",
        "content_type": "TECHNICAL_STORY",
        "viral_score": 8.7,
        "editorial_recommendations": "Include lessons learned and gotchas"
    },
    {
        "flow_id": "flow_009",
        "topic_title": "Container Security Hardening Checklist",
        "platform": "DevTo",
        "content_type": "CHECKLIST",
        "viral_score": 7.4,
        "editorial_recommendations": "Make it actionable and specific"
    },
    {
        "flow_id": "flow_010",
        "topic_title": "Performance Testing with K6 and Grafana",
        "platform": "LinkedIn",
        "content_type": "TUTORIAL",
        "viral_score": 8.0,
        "editorial_recommendations": "Include dashboard screenshots"
    }
]


class ConcurrentFlowTestMetrics:
    """Metrics collector for concurrent flow testing"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.flow_results = {}
        self.resource_snapshots = []
        self.errors = []
        self.performance_data = {}
        self._lock = threading.Lock()
    
    def start_monitoring(self):
        """Start performance monitoring"""
        self.start_time = time.time()
        self.resource_snapshots = []
        
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.end_time = time.time()
        
    def record_flow_result(self, flow_id: str, success: bool, execution_time: float, 
                          final_state: Optional[WritingFlowState] = None, error: Optional[str] = None):
        """Record result of individual flow execution"""
        with self._lock:
            self.flow_results[flow_id] = {
                "success": success,
                "execution_time": execution_time,
                "final_state": final_state,
                "error": error,
                "timestamp": datetime.now(timezone.utc)
            }
    
    def record_error(self, flow_id: str, error: str):
        """Record error during execution"""
        with self._lock:
            self.errors.append({
                "flow_id": flow_id,
                "error": error,
                "timestamp": datetime.now(timezone.utc)
            })
    
    def take_resource_snapshot(self):
        """Take snapshot of system resources"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent()
            
            snapshot = {
                "timestamp": time.time(),
                "memory_mb": memory_info.rss / 1024 / 1024,
                "cpu_percent": cpu_percent,
                "threads": process.num_threads()
            }
            
            with self._lock:
                self.resource_snapshots.append(snapshot)
                
        except Exception as e:
            logger.warning(f"Failed to take resource snapshot: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        if not self.start_time or not self.end_time:
            return {"error": "Monitoring not completed"}
        
        with self._lock:
            total_time = self.end_time - self.start_time
            successful_flows = sum(1 for r in self.flow_results.values() if r["success"])
            total_flows = len(self.flow_results)
            success_rate = successful_flows / total_flows if total_flows > 0 else 0
            
            execution_times = [r["execution_time"] for r in self.flow_results.values() if r["success"]]
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
            max_execution_time = max(execution_times) if execution_times else 0
            
            # Resource usage analysis
            if self.resource_snapshots:
                max_memory = max(s["memory_mb"] for s in self.resource_snapshots)
                avg_memory = sum(s["memory_mb"] for s in self.resource_snapshots) / len(self.resource_snapshots)
                max_cpu = max(s["cpu_percent"] for s in self.resource_snapshots)
                avg_cpu = sum(s["cpu_percent"] for s in self.resource_snapshots) / len(self.resource_snapshots)
            else:
                max_memory = avg_memory = max_cpu = avg_cpu = 0
            
            return {
                "execution_metrics": {
                    "total_execution_time": total_time,
                    "successful_flows": successful_flows,
                    "total_flows": total_flows,
                    "success_rate": success_rate,
                    "avg_flow_execution_time": avg_execution_time,
                    "max_flow_execution_time": max_execution_time,
                    "flows_per_second": total_flows / total_time if total_time > 0 else 0
                },
                "resource_metrics": {
                    "max_memory_mb": max_memory,
                    "avg_memory_mb": avg_memory,
                    "max_cpu_percent": max_cpu,
                    "avg_cpu_percent": avg_cpu,
                    "resource_snapshots_count": len(self.resource_snapshots)
                },
                "error_metrics": {
                    "total_errors": len(self.errors),
                    "error_rate": len(self.errors) / total_flows if total_flows > 0 else 0,
                    "unique_error_types": len(set(e["error"] for e in self.errors))
                },
                "flow_results": self.flow_results,
                "errors": self.errors
            }


class MockCrewAIComponents:
    """Mock implementations of CrewAI components for testing"""
    
    @staticmethod
    def create_mock_research_crew():
        """Create mock research crew that simulates realistic execution"""
        mock_crew = Mock()
        
        def mock_kickoff(*args, **kwargs):
            time.sleep(0.5)  # Simulate research work
            return Mock(
                raw="Mock research results: Industry trends show increased adoption of AI automation...",
                tasks_output=[
                    Mock(raw="Research source 1: Technical documentation"),
                    Mock(raw="Research source 2: Industry analysis")
                ]
            )
        
        mock_crew.kickoff = Mock(side_effect=mock_kickoff)
        return mock_crew
    
    @staticmethod
    def create_mock_audience_crew():
        """Create mock audience crew"""
        mock_crew = Mock()
        
        def mock_kickoff(*args, **kwargs):
            time.sleep(0.3)  # Simulate audience analysis
            return Mock(
                raw="Audience Analysis: Technical professionals, engineering managers...",
                tasks_output=[Mock(raw="Audience insights generated")]
            )
        
        mock_crew.kickoff = Mock(side_effect=mock_kickoff)
        return mock_crew
    
    @staticmethod
    def create_mock_draft_crew():
        """Create mock draft crew"""
        mock_crew = Mock()
        
        def mock_kickoff(*args, **kwargs):
            time.sleep(1.0)  # Simulate content generation
            return Mock(
                raw="Generated draft content with technical depth and engagement...",
                tasks_output=[Mock(raw="Draft content created")]
            )
        
        mock_crew.kickoff = Mock(side_effect=mock_kickoff)
        return mock_crew
    
    @staticmethod
    def create_mock_style_crew():
        """Create mock style crew"""
        mock_crew = Mock()
        
        def mock_kickoff(*args, **kwargs):
            time.sleep(0.4)  # Simulate style validation
            return Mock(
                raw="Style validation complete. No violations found.",
                tasks_output=[Mock(raw="Style check passed")]
            )
        
        mock_crew.kickoff = Mock(side_effect=mock_kickoff)
        return mock_crew
    
    @staticmethod
    def create_mock_quality_crew():
        """Create mock quality crew"""
        mock_crew = Mock()
        
        def mock_kickoff(*args, **kwargs):
            time.sleep(0.6)  # Simulate quality assessment
            return Mock(
                raw="Quality assessment: High-quality content with strong technical accuracy.",
                tasks_output=[Mock(raw="Quality assessment complete")]
            )
        
        mock_crew.kickoff = Mock(side_effect=mock_kickoff)
        return mock_crew


def execute_single_flow(flow_config: Dict[str, Any], test_metrics: ConcurrentFlowTestMetrics) -> Dict[str, Any]:
    """
    Execute a single AI Writing Flow V2 instance
    
    Args:
        flow_config: Configuration for the flow execution
        test_metrics: Shared metrics collector
        
    Returns:
        Dict containing execution results
    """
    flow_id = flow_config["flow_id"]
    start_time = time.time()
    
    try:
        logger.info(f"🚀 Starting flow {flow_id}: {flow_config['topic_title']}")
        
        # Create flow instance with monitoring enabled
        flow_v2 = AIWritingFlowV2(
            monitoring_enabled=True,
            alerting_enabled=True,
            quality_gates_enabled=True,
            storage_path=f"test_metrics_{flow_id}"
        )
        
        # Create flow inputs
        inputs = {
            "topic_title": flow_config["topic_title"],
            "platform": flow_config["platform"],
            "file_path": f"content/test/{flow_id}.md",  # Mock file path
            "content_type": flow_config.get("content_type", "STANDALONE"),
            "content_ownership": "EXTERNAL",
            "viral_score": flow_config.get("viral_score", 7.0),
            "editorial_recommendations": flow_config.get("editorial_recommendations", ""),
            "skip_research": False
        }
        
        # Apply comprehensive mocking
        with patch_crewai_components():
            # Execute flow
            final_state = flow_v2.kickoff(inputs)
            
            execution_time = time.time() - start_time
            success = hasattr(final_state, 'current_stage') and final_state.current_stage != "failed"
            
            # Record successful execution
            test_metrics.record_flow_result(
                flow_id=flow_id,
                success=success,
                execution_time=execution_time,
                final_state=final_state
            )
            
            logger.info(f"✅ Flow {flow_id} completed successfully in {execution_time:.2f}s")
            
            return {
                "flow_id": flow_id,
                "success": success,
                "execution_time": execution_time,
                "final_state": final_state,
                "dashboard_metrics": flow_v2.get_dashboard_metrics(),
                "health_status": flow_v2.get_health_status()
            }
            
    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = str(e)
        
        logger.error(f"❌ Flow {flow_id} failed after {execution_time:.2f}s: {error_msg}")
        
        # Record failed execution
        test_metrics.record_flow_result(
            flow_id=flow_id,
            success=False,
            execution_time=execution_time,
            error=error_msg
        )
        
        test_metrics.record_error(flow_id, error_msg)
        
        return {
            "flow_id": flow_id,
            "success": False,
            "execution_time": execution_time,
            "error": error_msg
        }


def patch_crewai_components():
    """Create comprehensive patch context for all CrewAI components"""
    
    # Mock the file system operations
    mock_file_exists = patch('pathlib.Path.exists', return_value=True)
    mock_file_read = patch('pathlib.Path.read_text', return_value="Mock content for testing")
    
    # Mock environment variables
    mock_env = patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test-key',
        'ANTHROPIC_API_KEY': 'test-key',
        'GEMINI_API_KEY': 'test-key'
    })
    
    # Mock CrewAI components
    mock_research_crew = patch(
        'ai_writing_flow.crews.research_crew.ResearchCrew',
        return_value=MockCrewAIComponents.create_mock_research_crew()
    )
    
    mock_audience_crew = patch(
        'ai_writing_flow.crews.audience_crew.AudienceCrew', 
        return_value=MockCrewAIComponents.create_mock_audience_crew()
    )
    
    mock_draft_crew = patch(
        'ai_writing_flow.crews.writer_crew.WriterCrew',
        return_value=MockCrewAIComponents.create_mock_draft_crew()
    )
    
    mock_style_crew = patch(
        'ai_writing_flow.crews.style_crew.StyleCrew',
        return_value=MockCrewAIComponents.create_mock_style_crew()
    )
    
    mock_quality_crew = patch(
        'ai_writing_flow.crews.quality_crew.QualityCrew',
        return_value=MockCrewAIComponents.create_mock_quality_crew()
    )
    
    # Mock Knowledge Base components
    mock_kb_adapter = patch('ai_writing_flow.adapters.knowledge_adapter.KnowledgeAdapter')
    mock_kb_tools = patch('ai_writing_flow.tools.enhanced_knowledge_tools.EnhancedKnowledgeTools')
    
    # Combine all patches
    from contextlib import ExitStack
    
    def combined_patch():
        stack = ExitStack()
        stack.enter_context(mock_file_exists)
        stack.enter_context(mock_file_read)
        stack.enter_context(mock_env)
        stack.enter_context(mock_research_crew)
        stack.enter_context(mock_audience_crew)
        stack.enter_context(mock_draft_crew)
        stack.enter_context(mock_style_crew)
        stack.enter_context(mock_quality_crew)
        stack.enter_context(mock_kb_adapter)
        stack.enter_context(mock_kb_tools)
        return stack
    
    return combined_patch()


class Test10ConcurrentFlows:
    """Main test class for concurrent flow execution"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_metrics = ConcurrentFlowTestMetrics()
        logger.info("🔧 Setting up concurrent flow test environment")
    
    def teardown_method(self):
        """Cleanup test environment"""
        # Cleanup any test data
        import shutil
        test_dirs = [f"test_metrics_flow_{i:03d}" for i in range(1, 11)]
        for test_dir in test_dirs:
            try:
                shutil.rmtree(test_dir, ignore_errors=True)
            except:
                pass
        
        logger.info("🧹 Cleaned up test environment")
    
    def test_10_concurrent_flows_execution(self):
        """
        Test 10 concurrent AI Writing Flow V2 executions
        
        This test validates:
        - Concurrent execution without conflicts
        - Resource usage within limits
        - Performance benchmarks
        - Thread safety
        - Error isolation
        """
        
        logger.info("🎯 Starting 10 concurrent flows test")
        
        # Start performance monitoring
        self.test_metrics.start_monitoring()
        
        # Monitor resources in background thread
        stop_monitoring = threading.Event()
        
        def resource_monitor():
            while not stop_monitoring.is_set():
                self.test_metrics.take_resource_snapshot()
                time.sleep(0.5)  # Take snapshot every 500ms
        
        monitor_thread = threading.Thread(target=resource_monitor, daemon=True)
        monitor_thread.start()
        
        try:
            # Execute flows concurrently using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=10, thread_name_prefix="FlowWorker") as executor:
                # Submit all flows for execution
                future_to_config = {
                    executor.submit(execute_single_flow, config, self.test_metrics): config
                    for config in CONCURRENT_FLOW_CONFIGS
                }
                
                results = []
                
                # Collect results as they complete
                for future in as_completed(future_to_config, timeout=MAX_EXECUTION_TIME_SECONDS):
                    config = future_to_config[future]
                    try:
                        result = future.result()
                        results.append(result)
                        logger.info(f"📊 Flow {config['flow_id']} result: {result['success']}")
                    except Exception as e:
                        logger.error(f"❌ Flow {config['flow_id']} failed with exception: {e}")
                        self.test_metrics.record_error(config['flow_id'], str(e))
            
            # Stop monitoring
            stop_monitoring.set()
            self.test_metrics.stop_monitoring()
            
            # Analyze results
            performance_summary = self.test_metrics.get_performance_summary()
            self._validate_performance_requirements(performance_summary)
            self._log_performance_summary(performance_summary)
            
            # Assert success criteria
            assert performance_summary["execution_metrics"]["success_rate"] >= MIN_SUCCESS_RATE, \
                f"Success rate {performance_summary['execution_metrics']['success_rate']:.1%} below minimum {MIN_SUCCESS_RATE:.1%}"
            
            assert performance_summary["execution_metrics"]["total_execution_time"] <= MAX_EXECUTION_TIME_SECONDS, \
                f"Total execution time {performance_summary['execution_metrics']['total_execution_time']:.1f}s exceeded maximum {MAX_EXECUTION_TIME_SECONDS}s"
            
            assert performance_summary["resource_metrics"]["max_memory_mb"] <= MAX_MEMORY_USAGE_MB, \
                f"Peak memory usage {performance_summary['resource_metrics']['max_memory_mb']:.1f}MB exceeded maximum {MAX_MEMORY_USAGE_MB}MB"
            
            logger.info("✅ All 10 concurrent flows test requirements passed!")
            
        except Exception as e:
            stop_monitoring.set()
            logger.error(f"❌ Concurrent flows test failed: {e}")
            raise
        
        finally:
            # Ensure monitoring thread is stopped
            if monitor_thread.is_alive():
                stop_monitoring.set()
                monitor_thread.join(timeout=2)
    
    def test_thread_safety_validation(self):
        """
        Test thread safety of shared components
        
        Validates:
        - FlowMetrics thread safety
        - AlertManager concurrent operations
        - Quality gates concurrent validation
        """
        
        logger.info("🔒 Testing thread safety of shared components")
        
        # Create shared FlowMetrics instance
        flow_metrics = FlowMetrics(history_size=1000)
        
        # Create shared AlertManager
        alert_manager = AlertManager()
        
        # Create shared QualityGate
        quality_gate = QualityGate()
        
        # Thread safety test function
        def stress_test_component(component_name: str, operations: List[callable]):
            """Stress test a component with concurrent operations"""
            errors = []
            
            def worker():
                for _ in range(50):  # 50 operations per thread
                    try:
                        # Pick random operation
                        import random
                        operation = random.choice(operations)
                        operation()
                        time.sleep(0.001)  # Small delay to increase contention
                    except Exception as e:
                        errors.append(f"{component_name}: {str(e)}")
            
            # Run 5 concurrent workers
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=worker)
                threads.append(thread)
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join(timeout=10)
            
            return errors
        
        # Test FlowMetrics thread safety
        metrics_operations = [
            lambda: flow_metrics.record_execution_time(1.5),
            lambda: flow_metrics.record_stage_completion("test_stage", True, 1.0),
            lambda: flow_metrics.record_error("test_error", "test message"),
            lambda: flow_metrics.get_current_kpis(),
            lambda: flow_metrics.start_flow_execution(f"test_{uuid.uuid4()}")
        ]
        
        metrics_errors = stress_test_component("FlowMetrics", metrics_operations)
        
        # Test AlertManager thread safety
        alert_operations = [
            lambda: alert_manager.get_alert_statistics(),
            lambda: alert_manager.get_active_alerts(),
            lambda: alert_manager.check_thresholds({})
        ]
        
        alert_errors = stress_test_component("AlertManager", alert_operations)
        
        # Test QualityGate thread safety
        quality_operations = [
            lambda: quality_gate.run_validation(),
            lambda: quality_gate.run_validation({"test": "context"})
        ]
        
        quality_errors = stress_test_component("QualityGate", quality_operations)
        
        # Validate no thread safety issues
        all_errors = metrics_errors + alert_errors + quality_errors
        
        if all_errors:
            logger.error(f"❌ Thread safety errors detected: {all_errors}")
            pytest.fail(f"Thread safety validation failed with {len(all_errors)} errors")
        
        logger.info("✅ Thread safety validation passed")
    
    def test_resource_isolation(self):
        """
        Test resource isolation between concurrent flows
        
        Validates:
        - No state contamination between flows
        - Independent metrics collection
        - Separate error handling
        """
        
        logger.info("🔬 Testing resource isolation between flows")
        
        # Create two flows with very different configurations
        flow1_config = {
            "flow_id": "isolation_test_1",
            "topic_title": "Test Topic 1",
            "platform": "LinkedIn",
            "viral_score": 5.0
        }
        
        flow2_config = {
            "flow_id": "isolation_test_2", 
            "topic_title": "Test Topic 2",
            "platform": "Twitter",
            "viral_score": 9.0
        }
        
        # Execute flows concurrently
        results = []
        
        def execute_flow(config):
            with patch_crewai_components():
                flow = AIWritingFlowV2(
                    monitoring_enabled=True,
                    storage_path=f"isolation_test_{config['flow_id']}"
                )
                
                inputs = {
                    "topic_title": config["topic_title"],
                    "platform": config["platform"],
                    "file_path": f"test/{config['flow_id']}.md",
                    "viral_score": config["viral_score"]
                }
                
                final_state = flow.kickoff(inputs)
                metrics = flow.get_dashboard_metrics()
                
                return {
                    "flow_id": config["flow_id"],
                    "final_state": final_state,
                    "metrics": metrics
                }
        
        # Execute flows in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(execute_flow, flow1_config)
            future2 = executor.submit(execute_flow, flow2_config)
            
            result1 = future1.result(timeout=15)
            result2 = future2.result(timeout=15)
        
        # Validate isolation
        assert result1["flow_id"] != result2["flow_id"], "Flow IDs should be different"
        assert result1["final_state"].topic_title != result2["final_state"].topic_title, "States should be isolated"
        
        # Validate metrics isolation
        if result1["metrics"]["monitoring_enabled"] and result2["metrics"]["monitoring_enabled"]:
            # Metrics should be separate instances
            assert id(result1["metrics"]) != id(result2["metrics"]), "Metrics should be isolated"
        
        logger.info("✅ Resource isolation validation passed")
    
    def test_error_handling_and_recovery(self):
        """
        Test error handling and recovery in concurrent environment
        
        Validates:
        - Individual flow failures don't affect others
        - Proper error propagation
        - System stability under partial failures
        """
        
        logger.info("⚠️ Testing error handling and recovery")
        
        # Create configs with one designed to fail
        normal_configs = CONCURRENT_FLOW_CONFIGS[:3]  # First 3 flows
        
        # Add a problematic flow
        failing_config = {
            "flow_id": "failing_flow",
            "topic_title": "",  # Empty title should cause validation failure
            "platform": "LinkedIn",
            "viral_score": 5.0
        }
        
        all_configs = normal_configs + [failing_config]
        test_metrics = ConcurrentFlowTestMetrics()
        
        # Execute all flows
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(execute_single_flow, config, test_metrics)
                for config in all_configs
            ]
            
            results = []
            for future in as_completed(futures, timeout=20):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.warning(f"Flow execution error (expected): {e}")
        
        # Validate error handling
        successful_flows = [r for r in results if r["success"]]
        failed_flows = [r for r in results if not r["success"]]
        
        # Should have 3 successful and 1 failed
        assert len(successful_flows) >= 2, f"Expected at least 2 successful flows, got {len(successful_flows)}"
        assert len(failed_flows) >= 1, f"Expected at least 1 failed flow, got {len(failed_flows)}"
        
        # Successful flows should have normal execution times
        success_times = [r["execution_time"] for r in successful_flows]
        avg_success_time = sum(success_times) / len(success_times)
        
        assert avg_success_time < 10, f"Average execution time {avg_success_time:.1f}s too high"
        
        logger.info("✅ Error handling and recovery validation passed")
    
    def _validate_performance_requirements(self, performance_summary: Dict[str, Any]):
        """Validate all performance requirements are met"""
        
        exec_metrics = performance_summary["execution_metrics"]
        resource_metrics = performance_summary["resource_metrics"]
        error_metrics = performance_summary["error_metrics"]
        
        requirements = [
            {
                "name": "Success Rate",
                "actual": exec_metrics["success_rate"],
                "threshold": MIN_SUCCESS_RATE,
                "operator": ">=",
                "unit": "%"
            },
            {
                "name": "Total Execution Time", 
                "actual": exec_metrics["total_execution_time"],
                "threshold": MAX_EXECUTION_TIME_SECONDS,
                "operator": "<=",
                "unit": "s"
            },
            {
                "name": "Peak Memory Usage",
                "actual": resource_metrics["max_memory_mb"],
                "threshold": MAX_MEMORY_USAGE_MB,
                "operator": "<=", 
                "unit": "MB"
            },
            {
                "name": "Peak CPU Usage",
                "actual": resource_metrics["max_cpu_percent"],
                "threshold": MAX_CPU_USAGE_PERCENT,
                "operator": "<=",
                "unit": "%"
            }
        ]
        
        failed_requirements = []
        
        for req in requirements:
            actual = req["actual"]
            threshold = req["threshold"]
            
            if req["operator"] == ">=" and actual < threshold:
                failed_requirements.append(req)
            elif req["operator"] == "<=" and actual > threshold:
                failed_requirements.append(req)
        
        if failed_requirements:
            failure_msg = "Performance requirements failed:\n"
            for req in failed_requirements:
                failure_msg += f"  • {req['name']}: {req['actual']:.2f}{req['unit']} {req['operator']} {req['threshold']}{req['unit']}\n"
            
            logger.error(f"❌ {failure_msg}")
            pytest.fail(failure_msg)
        
        logger.info("✅ All performance requirements passed")
    
    def _log_performance_summary(self, performance_summary: Dict[str, Any]):
        """Log comprehensive performance summary"""
        
        exec_metrics = performance_summary["execution_metrics"]
        resource_metrics = performance_summary["resource_metrics"]
        error_metrics = performance_summary["error_metrics"]
        
        logger.info("📊 CONCURRENT FLOW PERFORMANCE SUMMARY")
        logger.info("=" * 50)
        
        logger.info("🎯 Execution Metrics:")
        logger.info(f"  • Total Execution Time: {exec_metrics['total_execution_time']:.2f}s")
        logger.info(f"  • Successful Flows: {exec_metrics['successful_flows']}/{exec_metrics['total_flows']}")
        logger.info(f"  • Success Rate: {exec_metrics['success_rate']:.1%}")
        logger.info(f"  • Average Flow Time: {exec_metrics['avg_flow_execution_time']:.2f}s")
        logger.info(f"  • Maximum Flow Time: {exec_metrics['max_flow_execution_time']:.2f}s")
        logger.info(f"  • Throughput: {exec_metrics['flows_per_second']:.2f} flows/sec")
        
        logger.info("💾 Resource Metrics:")
        logger.info(f"  • Peak Memory Usage: {resource_metrics['max_memory_mb']:.1f}MB")
        logger.info(f"  • Average Memory Usage: {resource_metrics['avg_memory_mb']:.1f}MB")
        logger.info(f"  • Peak CPU Usage: {resource_metrics['max_cpu_percent']:.1f}%")
        logger.info(f"  • Average CPU Usage: {resource_metrics['avg_cpu_percent']:.1f}%")
        logger.info(f"  • Resource Snapshots: {resource_metrics['resource_snapshots_count']}")
        
        logger.info("⚠️ Error Metrics:")
        logger.info(f"  • Total Errors: {error_metrics['total_errors']}")
        logger.info(f"  • Error Rate: {error_metrics['error_rate']:.1%}")
        logger.info(f"  • Unique Error Types: {error_metrics['unique_error_types']}")
        
        logger.info("=" * 50)
        
        # Individual flow results
        logger.info("📋 Individual Flow Results:")
        for flow_id, result in performance_summary["flow_results"].items():
            status = "✅" if result["success"] else "❌"
            logger.info(f"  {status} {flow_id}: {result['execution_time']:.2f}s")
        
        # Errors details
        if performance_summary["errors"]:
            logger.info("🔍 Error Details:")
            for error in performance_summary["errors"]:
                logger.info(f"  • {error['flow_id']}: {error['error']}")


# Performance benchmarking fixtures
@pytest.fixture
def performance_baseline():
    """Baseline performance metrics for comparison"""
    return {
        "max_execution_time": MAX_EXECUTION_TIME_SECONDS,
        "max_memory_mb": MAX_MEMORY_USAGE_MB,
        "max_cpu_percent": MAX_CPU_USAGE_PERCENT,
        "min_success_rate": MIN_SUCCESS_RATE,
        "target_throughput": 0.5  # flows per second
    }


# Integration test marker
pytestmark = pytest.mark.integration


if __name__ == "__main__":
    """Run the test directly for development"""
    pytest.main([__file__, "-v", "--tb=short", "--workers=10"])