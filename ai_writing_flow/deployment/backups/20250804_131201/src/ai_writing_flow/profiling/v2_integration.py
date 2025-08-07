"""
V2 Integration Module - Integration of profiling with AI Writing Flow V2

This module provides seamless integration of the profiling system with
the AI Writing Flow V2 architecture, including integration with monitoring,
execution guards, and flow metrics.
"""

import logging
from typing import Dict, Any, Optional
from contextlib import contextmanager
from datetime import datetime

from .flow_profiler import FlowProfiler, ProfilingConfig, ProfilingReport
from .performance_analyzer import PerformanceAnalyzer
from .mock_profiler import MockFlowProfiler

# Import V2 components
try:
    from ai_writing_flow.monitoring.flow_metrics import FlowMetrics
    from ai_writing_flow.execution_guards import FlowExecutionGuards
    from ai_writing_flow.linear_flow import LinearAIWritingFlow
    V2_AVAILABLE = True
except ImportError:
    V2_AVAILABLE = False

logger = logging.getLogger(__name__)


class ProfiledFlowV2Integration:
    """
    Integration class for profiling AI Writing Flow V2 executions
    
    Provides seamless integration between the profiling system and V2 architecture
    including monitoring, guards, and flow metrics integration.
    """
    
    def __init__(
        self,
        flow_metrics: Optional['FlowMetrics'] = None,
        execution_guards: Optional['FlowExecutionGuards'] = None,
        use_mock_profiler: bool = False,
        profiling_config: Optional[ProfilingConfig] = None
    ):
        """
        Initialize V2 integration
        
        Args:
            flow_metrics: V2 FlowMetrics instance
            execution_guards: V2 FlowExecutionGuards instance
            use_mock_profiler: Whether to use mock profiler for testing
            profiling_config: Configuration for profiling
        """
        self.flow_metrics = flow_metrics
        self.execution_guards = execution_guards
        self.profiling_config = profiling_config or ProfilingConfig()
        
        # Initialize profiler
        if use_mock_profiler or not V2_AVAILABLE:
            self.profiler = MockFlowProfiler(self.profiling_config)
            logger.info("🎭 Using MockFlowProfiler for V2 integration")
        else:
            self.profiler = FlowProfiler(self.profiling_config)
            logger.info("🔍 Using FlowProfiler for V2 integration")
        
        # Initialize performance analyzer
        self.performance_analyzer = PerformanceAnalyzer()
        
        # Integration state
        self._current_execution_id: Optional[str] = None
        self._profiling_active = False
        
        logger.info("🔗 ProfiledFlowV2Integration initialized")
    
    @contextmanager
    def profile_v2_execution(self, execution_id: str, flow_inputs: Dict[str, Any]):
        """
        Context manager for profiling V2 flow execution
        
        Args:
            execution_id: Unique execution identifier
            flow_inputs: Flow input parameters
        """
        logger.info(f"🚀 Starting V2 flow profiling: {execution_id}")
        
        self._current_execution_id = execution_id
        self._profiling_active = True
        
        try:
            # Start profiling
            with self.profiler.profile_execution(execution_id):
                
                # Integrate with V2 monitoring if available
                if self.flow_metrics:
                    self.flow_metrics.start_flow_execution(execution_id)
                
                # Start execution guards monitoring if available
                if self.execution_guards:
                    self.execution_guards.start_flow_execution()
                
                yield self
                
        finally:
            # Stop V2 monitoring
            if self.flow_metrics:
                self.flow_metrics.end_flow_execution(execution_id)
            
            if self.execution_guards:
                self.execution_guards.stop_flow_execution()
            
            self._profiling_active = False
            logger.info(f"✅ V2 flow profiling completed: {execution_id}")
    
    def profile_method(self, method_name: str):
        """
        Decorator for profiling V2 flow methods with integration
        
        Args:
            method_name: Name of the method to profile
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                if not self._profiling_active:
                    return func(*args, **kwargs)
                
                # Record method start in V2 monitoring
                if self.flow_metrics and self._current_execution_id:
                    self.flow_metrics.record_stage_completion(
                        self._current_execution_id,
                        method_name,
                        0.0,  # Will be updated with actual time
                        success=True
                    )
                
                # Use profiler's method profiling
                profiled_func = self.profiler.profile_method(method_name)(func)
                
                try:
                    result = profiled_func(*args, **kwargs)
                    
                    # Record success in V2 monitoring
                    if self.flow_metrics and self._current_execution_id:
                        # Calculate execution time would be done by profiler
                        pass
                    
                    return result
                    
                except Exception as e:
                    # Record error in V2 monitoring
                    if self.flow_metrics and self._current_execution_id:
                        self.flow_metrics.record_error(method_name, str(e))
                    
                    raise
            
            return wrapper
        return decorator
    
    def generate_integrated_report(self, execution_id: str) -> Dict[str, Any]:
        """
        Generate integrated profiling report with V2 metrics
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            Dict containing integrated profiling and V2 monitoring data
        """
        logger.info(f"📊 Generating integrated V2 profiling report: {execution_id}")
        
        # Generate base profiling report
        if isinstance(self.profiler, MockFlowProfiler):
            profiling_report = self.profiler.generate_mock_report(execution_id)
        else:
            profiling_report = self.profiler.generate_report(execution_id)
        
        # Perform performance analysis
        performance_analysis = self.performance_analyzer.analyze_report(profiling_report)
        
        # Collect V2 monitoring data
        v2_metrics = self._collect_v2_metrics()
        
        # Collect execution guards data
        guards_status = self._collect_guards_status()
        
        # Create integrated report
        integrated_report = {
            "execution_id": execution_id,
            "timestamp": datetime.now().isoformat(),
            "profiling_report": profiling_report.to_dict(),
            "performance_analysis": performance_analysis,
            "v2_metrics": v2_metrics,
            "execution_guards_status": guards_status,
            "integration_metadata": {
                "profiler_type": "mock" if isinstance(self.profiler, MockFlowProfiler) else "real",
                "v2_monitoring_available": self.flow_metrics is not None,
                "execution_guards_available": self.execution_guards is not None,
                "integration_version": "1.0.0"
            }
        }
        
        # Generate integrated recommendations
        integrated_recommendations = self._generate_integrated_recommendations(
            profiling_report, performance_analysis, v2_metrics, guards_status
        )
        
        integrated_report["integrated_recommendations"] = integrated_recommendations
        
        logger.info(f"✅ Integrated V2 report generated successfully")
        return integrated_report
    
    def _collect_v2_metrics(self) -> Dict[str, Any]:
        """Collect V2 FlowMetrics data"""
        if not self.flow_metrics:
            return {"available": False, "message": "V2 FlowMetrics not available"}
        
        try:
            current_kpis = self.flow_metrics.get_current_kpis()
            flow_summary = self.flow_metrics.get_flow_summary()
            stage_performance = self.flow_metrics.get_stage_performance_summary()
            
            return {
                "available": True,
                "current_kpis": {
                    "cpu_usage": current_kpis.cpu_usage,
                    "memory_usage": current_kpis.memory_usage,
                    "avg_execution_time": current_kpis.avg_execution_time,
                    "success_rate": current_kpis.success_rate,
                    "throughput": current_kpis.throughput,
                    "error_rate": current_kpis.error_rate,
                    "active_flows": current_kpis.active_flows
                },
                "flow_summary": flow_summary,
                "stage_performance": stage_performance
            }
            
        except Exception as e:
            logger.error(f"Error collecting V2 metrics: {e}")
            return {"available": False, "error": str(e)}
    
    def _collect_guards_status(self) -> Dict[str, Any]:
        """Collect execution guards status"""
        if not self.execution_guards:
            return {"available": False, "message": "ExecutionGuards not available"}
        
        try:
            guards_status = self.execution_guards.get_guard_status()
            
            return {
                "available": True,
                "guard_status": guards_status
            }
            
        except Exception as e:
            logger.error(f"Error collecting guards status: {e}")
            return {"available": False, "error": str(e)}
    
    def _generate_integrated_recommendations(
        self,
        profiling_report: ProfilingReport,
        performance_analysis: Dict[str, Any],
        v2_metrics: Dict[str, Any],
        guards_status: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate integrated optimization recommendations"""
        
        recommendations = []
        
        # Base performance recommendations
        base_recommendations = performance_analysis.get("optimization_recommendations", [])
        recommendations.extend(base_recommendations)
        
        # V2 monitoring integration recommendations
        if v2_metrics.get("available"):
            kpis = v2_metrics.get("current_kpis", {})
            
            # FlowMetrics-based recommendations
            if kpis.get("error_rate", 0) > 5.0:
                recommendations.append({
                    "priority": "high",
                    "category": "v2_monitoring_integration",
                    "description": f"High error rate detected by V2 monitoring: {kpis['error_rate']:.1f}%",
                    "suggestions": [
                        "Review V2 FlowMetrics error tracking",
                        "Implement better error handling in flow methods",
                        "Add retry mechanisms for transient failures"
                    ],
                    "integration_source": "v2_flow_metrics"
                })
            
            if kpis.get("throughput", 0) < 0.1:
                recommendations.append({
                    "priority": "medium",
                    "category": "v2_monitoring_integration",
                    "description": f"Low throughput detected: {kpis['throughput']:.3f} ops/sec",
                    "suggestions": [
                        "Optimize critical path methods identified in profiling",
                        "Consider parallel processing for independent stages",
                        "Review V2 linear flow execution patterns"
                    ],
                    "integration_source": "v2_flow_metrics"
                })
        
        # Execution guards recommendations
        if guards_status.get("available"):
            guard_data = guards_status.get("guard_status", {})
            
            # Resource usage recommendations
            resource_usage = guard_data.get("resource_usage", {})
            if resource_usage.get("cpu_percent", 0) > 70:
                recommendations.append({
                    "priority": "medium",
                    "category": "execution_guards_integration",
                    "description": f"ExecutionGuards detected high CPU usage: {resource_usage['cpu_percent']:.1f}%",
                    "suggestions": [
                        "Review CPU-intensive methods in profiling report",
                        "Consider async processing patterns",
                        "Optimize V2 execution guards CPU monitoring thresholds"
                    ],
                    "integration_source": "v2_execution_guards"
                })
            
            # Violation recommendations
            recent_violations = guard_data.get("recent_violations", [])
            if recent_violations:
                high_severity_violations = [v for v in recent_violations if v.get("severity") == "critical"]
                if high_severity_violations:
                    recommendations.append({
                        "priority": "critical",
                        "category": "execution_guards_integration",
                        "description": f"Critical guard violations detected: {len(high_severity_violations)}",
                        "suggestions": [
                            "Investigate critical violations in ExecutionGuards",
                            "Review resource limits and thresholds",
                            "Implement emergency stop procedures if not present"
                        ],
                        "integration_source": "v2_execution_guards"
                    })
        
        # Cross-system integration recommendations
        profiling_bottlenecks = len(profiling_report.performance_bottlenecks)
        v2_error_rate = v2_metrics.get("current_kpis", {}).get("error_rate", 0)
        
        if profiling_bottlenecks > 3 and v2_error_rate > 2.0:
            recommendations.append({
                "priority": "high",
                "category": "cross_system_integration",
                "description": "Correlation between profiling bottlenecks and V2 monitoring errors detected",
                "suggestions": [
                    "Focus optimization efforts on bottlenecked methods causing V2 errors",
                    "Implement better error handling in identified bottleneck methods",
                    "Consider circuit breaker patterns for unreliable components"
                ],
                "integration_source": "cross_system_analysis"
            })
        
        return recommendations
    
    def create_profiling_dashboard_data(self) -> Dict[str, Any]:
        """Create data structure for profiling dashboard"""
        
        if not self._current_execution_id:
            return {"error": "No active profiling session"}
        
        try:
            # Collect real-time profiling data
            dashboard_data = {
                "execution_id": self._current_execution_id,
                "timestamp": datetime.now().isoformat(),
                "profiling_active": self._profiling_active,
                "v2_integration_status": {
                    "flow_metrics_connected": self.flow_metrics is not None,
                    "execution_guards_connected": self.execution_guards is not None,
                    "profiler_type": "mock" if isinstance(self.profiler, MockFlowProfiler) else "real"
                }
            }
            
            # Add V2 monitoring data if available
            if self.flow_metrics:
                try:
                    current_kpis = self.flow_metrics.get_current_kpis()
                    dashboard_data["real_time_metrics"] = {
                        "cpu_usage": current_kpis.cpu_usage,
                        "memory_usage": current_kpis.memory_usage,
                        "success_rate": current_kpis.success_rate,
                        "error_rate": current_kpis.error_rate,
                        "active_flows": current_kpis.active_flows
                    }
                except Exception as e:
                    dashboard_data["real_time_metrics"] = {"error": str(e)}
            
            # Add execution guards status if available
            if self.execution_guards:
                try:
                    guards_status = self.execution_guards.get_guard_status()
                    dashboard_data["guards_status"] = {
                        "active_methods": guards_status.get("active_methods", []),
                        "resource_usage": guards_status.get("resource_usage", {}),
                        "recent_violations_count": len(guards_status.get("recent_violations", []))
                    }
                except Exception as e:
                    dashboard_data["guards_status"] = {"error": str(e)}
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error creating dashboard data: {e}")
            return {"error": str(e)}


def create_profiled_v2_flow(
    use_mock: bool = True,
    profiling_config: Optional[ProfilingConfig] = None
) -> ProfiledFlowV2Integration:
    """
    Factory function to create a profiled V2 flow integration
    
    Args:
        use_mock: Whether to use mock profiler (useful for testing)
        profiling_config: Configuration for profiling
        
    Returns:
        ProfiledFlowV2Integration instance
    """
    
    # Initialize V2 components if available
    flow_metrics = None
    execution_guards = None
    
    if V2_AVAILABLE and not use_mock:
        try:
            # This would be initialized with actual V2 flow
            flow_metrics = FlowMetrics(history_size=1000)
            # execution_guards would be initialized with loop prevention
            logger.info("✅ V2 components initialized for profiling integration")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize V2 components: {e}")
    
    return ProfiledFlowV2Integration(
        flow_metrics=flow_metrics,
        execution_guards=execution_guards,
        use_mock_profiler=use_mock,
        profiling_config=profiling_config or ProfilingConfig()
    )


# Example usage function
def run_profiled_v2_example():
    """
    Example of running profiled V2 flow execution
    
    This demonstrates the complete integration of profiling with V2 architecture
    """
    print("🚀 AI Writing Flow V2 - Profiled Execution Example")
    print("=" * 60)
    
    # Create profiled flow integration
    profiled_flow = create_profiled_v2_flow(use_mock=True)
    
    # Example flow inputs
    flow_inputs = {
        "topic_title": "Comprehensive Performance Analysis of AI Writing Flow V2",
        "platform": "LinkedIn",
        "file_path": "content/performance-analysis-example.md",
        "content_type": "STANDALONE",
        "content_ownership": "ORIGINAL",
        "viral_score": 8.5,
        "editorial_recommendations": "Focus on technical depth and profiling insights"
    }
    
    execution_id = f"v2_profiled_example_{int(datetime.now().timestamp())}"
    
    try:
        # Execute profiled flow
        with profiled_flow.profile_v2_execution(execution_id, flow_inputs):
            
            print(f"📊 Profiling V2 execution: {execution_id}")
            
            # Simulate V2 flow method calls with profiling
            @profiled_flow.profile_method("validate_inputs")
            def mock_validate_inputs():
                import time
                time.sleep(0.1)  # Simulate processing
                return {"validation": "success"}
            
            @profiled_flow.profile_method("conduct_research")
            def mock_conduct_research():
                import time
                time.sleep(1.2)  # Simulate research
                return {"research_data": "comprehensive analysis data"}
            
            @profiled_flow.profile_method("generate_draft")
            def mock_generate_draft():
                import time
                time.sleep(2.5)  # Simulate draft generation
                return {"draft": "performance analysis article"}
            
            # Execute methods
            print("🔍 Validating inputs...")
            validation_result = mock_validate_inputs()
            
            print("📚 Conducting research...")
            research_result = mock_conduct_research()
            
            print("✍️ Generating draft...")
            draft_result = mock_generate_draft()
            
            print("✅ V2 flow execution completed")
        
        # Generate integrated report
        print("\n📊 Generating integrated profiling report...")
        integrated_report = profiled_flow.generate_integrated_report(execution_id)
        
        # Display results
        print("\n🎯 PROFILING RESULTS SUMMARY")
        print("-" * 40)
        
        profiling_data = integrated_report["profiling_report"]
        performance_data = integrated_report["performance_analysis"]
        
        print(f"Total Execution Time: {profiling_data['total_duration']:.2f}s")
        print(f"Peak Memory Usage: {profiling_data['peak_memory_mb']:.1f}MB")
        print(f"Performance Score: {performance_data['performance_score']:.1f}/100")
        print(f"Methods Profiled: {len(profiling_data['method_profiles'])}")
        print(f"Bottlenecks Detected: {len(profiling_data['performance_bottlenecks'])}")
        
        # Show top recommendations
        recommendations = integrated_report.get("integrated_recommendations", [])
        if recommendations:
            print(f"\n🔧 TOP OPTIMIZATION RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"{i}. [{rec['priority'].upper()}] {rec['description']}")
        
        # Show integration status
        integration_meta = integrated_report["integration_metadata"]
        print(f"\n🔗 INTEGRATION STATUS:")
        print(f"Profiler Type: {integration_meta['profiler_type']}")
        print(f"V2 Monitoring: {'✅' if integration_meta['v2_monitoring_available'] else '❌'}")
        print(f"Execution Guards: {'✅' if integration_meta['execution_guards_available'] else '❌'}")
        
        print(f"\n✅ V2 profiled execution example completed successfully!")
        
        return integrated_report
        
    except Exception as e:
        print(f"❌ Error in profiled V2 execution: {e}")
        raise


if __name__ == "__main__":
    # Run example when script is executed directly
    result = run_profiled_v2_example()
