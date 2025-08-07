"""
Comprehensive Test Suite for Flow Profiler

This module provides comprehensive testing of the profiling system including:
- Mock profiling scenarios
- Performance analysis validation
- Bottleneck detection testing
- Integration tests with V2 architecture
"""

import unittest
import tempfile
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

from .mock_profiler import MockFlowProfiler, SimulatedExecution
from .performance_analyzer import PerformanceAnalyzer, BottleneckDetector
from .flow_profiler import ProfilingConfig

logger = logging.getLogger(__name__)


class TestFlowProfiler(unittest.TestCase):
    """Test cases for FlowProfiler functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = ProfilingConfig(
            output_directory=str(self.temp_dir),
            save_detailed_reports=True
        )
        self.mock_profiler = MockFlowProfiler(self.config)
        
    def test_mock_profiler_initialization(self):
        """Test mock profiler initialization"""
        self.assertIsNotNone(self.mock_profiler)
        self.assertEqual(len(self.mock_profiler.flow_methods), 12)
        self.assertIn("validate_inputs", self.mock_profiler.flow_methods)
        self.assertIn("generate_draft", self.mock_profiler.flow_methods)
        
    def test_mock_report_generation(self):
        """Test mock report generation"""
        execution_id = "test_execution_001"
        
        report = self.mock_profiler.generate_mock_report(execution_id)
        
        # Validate report structure
        self.assertEqual(report.execution_id, execution_id)
        self.assertIsInstance(report.total_duration, float)
        self.assertGreater(report.total_duration, 0)
        self.assertIsInstance(report.method_profiles, dict)
        self.assertGreater(len(report.method_profiles), 0)
        
        # Validate method profiles
        for method_name, profile in report.method_profiles.items():
            self.assertIn(method_name, self.mock_profiler.flow_methods)
            self.assertGreater(profile.call_count, 0)
            self.assertGreaterEqual(profile.total_time, 0)
            self.assertGreaterEqual(profile.avg_time, 0)
            
    def test_profiling_scenarios(self):
        """Test different profiling scenarios"""
        scenarios = ["optimal", "bottlenecked", "memory_intensive", "cpu_intensive"]
        
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                self.mock_profiler.create_performance_scenario(scenario)
                report = self.mock_profiler.generate_mock_report(f"test_{scenario}")
                
                # Validate scenario-specific characteristics
                if scenario == "optimal":
                    self.assertLess(report.total_duration, 40)
                    self.assertLess(report.peak_memory_mb, 300)
                elif scenario == "bottlenecked":
                    self.assertGreater(report.total_duration, 60)
                    self.assertGreater(len(report.performance_bottlenecks), 2)
                elif scenario == "memory_intensive":
                    self.assertGreater(report.peak_memory_mb, 800)
                elif scenario == "cpu_intensive":
                    self.assertGreater(report.peak_cpu_percent, 80)
                    
    def test_performance_analysis(self):
        """Test performance analysis functionality"""
        analyzer = PerformanceAnalyzer()
        
        # Generate test report
        report = self.mock_profiler.generate_mock_report("analysis_test")
        
        # Perform analysis
        analysis = analyzer.analyze_report(report)
        
        # Validate analysis structure
        self.assertIn("performance_metrics", analysis)
        self.assertIn("bottlenecks", analysis)
        self.assertIn("performance_score", analysis)
        self.assertIn("optimization_recommendations", analysis)
        
        # Validate performance score
        score = analysis["performance_score"]
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)
        
    def test_bottleneck_detection(self):
        """Test bottleneck detection algorithms"""
        detector = BottleneckDetector()
        
        # Generate bottlenecked scenario
        self.mock_profiler.create_performance_scenario("bottlenecked")
        report = self.mock_profiler.generate_mock_report("bottleneck_test")
        
        # Test execution anomaly detection
        anomalies = detector.detect_execution_anomalies(report.method_profiles)
        self.assertIsInstance(anomalies, list)
        
        # Validate anomaly structure
        for anomaly in anomalies:
            self.assertIn("method", anomaly)
            self.assertIn("anomaly_type", anomaly)
            self.assertIn("z_score", anomaly)
            self.assertIn("severity", anomaly)
            
    def test_critical_path_identification(self):
        """Test critical path identification"""
        report = self.mock_profiler.generate_mock_report("critical_path_test")
        
        # Validate critical path
        self.assertIsInstance(report.critical_path, list)
        self.assertGreater(len(report.critical_path), 0)
        
        # Verify critical path methods exist in profiles
        for method_name in report.critical_path:
            self.assertIn(method_name, report.method_profiles)
            
    def test_report_serialization(self):
        """Test report serialization to JSON"""
        report = self.mock_profiler.generate_mock_report("serialization_test")
        
        # Convert to dictionary
        report_dict = report.to_dict()
        
        # Validate serialization
        self.assertIsInstance(report_dict, dict)
        self.assertIn("execution_id", report_dict)
        self.assertIn("method_profiles", report_dict)
        self.assertIn("recommendations", report_dict)
        
        # Test JSON serialization
        json_str = json.dumps(report_dict, default=str)
        self.assertIsInstance(json_str, str)
        
        # Test deserialization
        loaded_dict = json.loads(json_str)
        self.assertEqual(loaded_dict["execution_id"], report.execution_id)


class TestPerformanceAnalyzer(unittest.TestCase):
    """Test cases for PerformanceAnalyzer"""
    
    def setUp(self):
        """Set up test environment"""
        self.analyzer = PerformanceAnalyzer()
        self.mock_profiler = MockFlowProfiler()
        
    def test_performance_metrics_calculation(self):
        """Test performance metrics calculation"""
        report = self.mock_profiler.generate_mock_report("metrics_test")
        analysis = self.analyzer.analyze_report(report)
        
        metrics = analysis["performance_metrics"]
        
        # Validate metrics structure
        required_metrics = [
            "total_execution_time", "method_count", "avg_method_time",
            "p50_method_time", "p95_method_time", "p99_method_time",
            "peak_memory_mb", "avg_cpu_percent", "performance_score"
        ]
        
        for metric in required_metrics:
            self.assertIn(metric, metrics)
            self.assertIsInstance(metrics[metric], (int, float))
            
    def test_bottleneck_analysis(self):
        """Test bottleneck analysis"""
        # Create bottlenecked scenario
        self.mock_profiler.create_performance_scenario("bottlenecked")
        report = self.mock_profiler.generate_mock_report("bottleneck_analysis_test")
        
        analysis = self.analyzer.analyze_report(report)
        bottlenecks = analysis["bottlenecks"]
        
        # Should have bottlenecks in bottlenecked scenario
        self.assertGreater(len(bottlenecks), 0)
        
        # Validate bottleneck structure
        for bottleneck in bottlenecks:
            self.assertIn("method_name", bottleneck)
            self.assertIn("bottleneck_type", bottleneck)
            self.assertIn("severity", bottleneck)
            self.assertIn("impact_score", bottleneck)
            self.assertIn("optimization_suggestions", bottleneck)
            
    def test_historical_comparison(self):
        """Test historical performance comparison"""
        # Generate multiple reports
        reports = []
        for i in range(5):
            report = self.mock_profiler.generate_mock_report(f"historical_test_{i}")
            reports.append(report)
            self.analyzer.analyze_report(report)
        
        # Test with latest report
        final_report = self.mock_profiler.generate_mock_report("final_historical_test")
        analysis = self.analyzer.analyze_report(final_report)
        
        # Should have historical comparison
        self.assertIn("historical_comparison", analysis)
        comparison = analysis["historical_comparison"]
        
        if "message" not in comparison:  # If we have enough historical data
            self.assertIn("duration_change_percent", comparison)
            self.assertIn("performance_trend", comparison)
            
    def test_optimization_recommendations(self):
        """Test optimization recommendations generation"""
        report = self.mock_profiler.generate_mock_report("optimization_test")
        analysis = self.analyzer.analyze_report(report)
        
        recommendations = analysis["optimization_recommendations"]
        
        # Should have recommendations
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)
        
        # Validate recommendation structure
        for recommendation in recommendations:
            self.assertIn("priority", recommendation)
            self.assertIn("category", recommendation)
            self.assertIn("description", recommendation)
            self.assertIn("suggestions", recommendation)


class TestBottleneckDetector(unittest.TestCase):
    """Test cases for BottleneckDetector"""
    
    def setUp(self):
        """Set up test environment"""
        self.detector = BottleneckDetector()
        self.mock_profiler = MockFlowProfiler()
        
    def test_execution_anomaly_detection(self):
        """Test execution anomaly detection"""
        report = self.mock_profiler.generate_mock_report("anomaly_test")
        
        anomalies = self.detector.detect_execution_anomalies(report.method_profiles)
        
        # Validate anomalies structure
        for anomaly in anomalies:
            self.assertIn("method", anomaly)
            self.assertIn("anomaly_type", anomaly)
            self.assertIn("z_score", anomaly)
            self.assertIn("actual_time", anomaly)
            self.assertIn("expected_time", anomaly)
            self.assertIn("severity", anomaly)
            
    def test_cpu_spike_detection(self):
        """Test CPU spike detection"""
        # Create CPU-intensive scenario
        self.mock_profiler.create_performance_scenario("cpu_intensive")
        
        # Generate mock CPU samples
        cpu_samples = [
            {"timestamp": "2025-01-01T10:00:00Z", "cpu_percent": 25.0},
            {"timestamp": "2025-01-01T10:00:01Z", "cpu_percent": 30.0},
            {"timestamp": "2025-01-01T10:00:02Z", "cpu_percent": 95.0},  # Spike
            {"timestamp": "2025-01-01T10:00:03Z", "cpu_percent": 28.0},
            {"timestamp": "2025-01-01T10:00:04Z", "cpu_percent": 32.0},
        ]
        
        spikes = self.detector.detect_cpu_spikes(cpu_samples)
        
        # Should detect the spike
        self.assertGreater(len(spikes), 0)
        
        # Validate spike structure
        for spike in spikes:
            self.assertIn("timestamp", spike)
            self.assertIn("cpu_percent", spike)
            self.assertIn("severity", spike)
            self.assertGreater(spike["cpu_percent"], 70)


def run_comprehensive_profiling_demo():
    """
    Run comprehensive profiling demonstration
    
    This function demonstrates all profiling capabilities with realistic scenarios
    """
    print("🚀 Starting Comprehensive Flow Profiling Demo")
    print("=" * 60)
    
    # Initialize profiler
    config = ProfilingConfig(
        output_directory="demo_profiling_results",
        save_detailed_reports=True
    )
    mock_profiler = MockFlowProfiler(config)
    analyzer = PerformanceAnalyzer()
    detector = BottleneckDetector()
    
    scenarios = [
        ("optimal", "🟢 Optimal Performance"),
        ("bottlenecked", "🔴 Performance Bottlenecks"),
        ("memory_intensive", "🧠 Memory Intensive"),
        ("cpu_intensive", "💻 CPU Intensive")
    ]
    
    results = []
    
    for scenario_type, scenario_name in scenarios:
        print(f"\n{scenario_name}")
        print("-" * 40)
        
        # Configure scenario
        mock_profiler.create_performance_scenario(scenario_type)
        
        # Run profiling
        execution_id = f"demo_{scenario_type}_{int(datetime.now().timestamp())}"
        
        with mock_profiler.profile_execution(execution_id):
            report = mock_profiler.generate_mock_report(execution_id)
        
        # Analyze performance
        analysis = analyzer.analyze_report(report)
        
        # Display results
        print(f"📊 Execution Time: {report.total_duration:.1f}s")
        print(f"🧠 Peak Memory: {report.peak_memory_mb:.1f}MB")
        print(f"💻 Peak CPU: {report.peak_cpu_percent:.1f}%")
        print(f"📈 Performance Score: {analysis['performance_score']:.1f}/100")
        print(f"⚠️  Bottlenecks Found: {len(report.performance_bottlenecks)}")
        
        # Display top recommendations
        recommendations = analysis.get("optimization_recommendations", [])
        if recommendations:
            print("🔧 Top Optimization Recommendations:")
            for i, rec in enumerate(recommendations[:2], 1):
                print(f"   {i}. {rec['description']}")
        
        # Detect anomalies
        anomalies = detector.detect_execution_anomalies(report.method_profiles)
        if anomalies:
            print(f"🚨 Execution Anomalies: {len(anomalies)} detected")
            
        results.append({
            "scenario": scenario_type,
            "report": report,
            "analysis": analysis
        })
    
    # Generate summary comparison
    print("\n" + "=" * 60)
    print("📊 SCENARIO COMPARISON SUMMARY")
    print("=" * 60)
    
    print(f"{'Scenario':<15} {'Duration':<10} {'Memory':<10} {'CPU':<8} {'Score':<8} {'Bottlenecks':<12}")
    print("-" * 70)
    
    for result in results:
        scenario = result["scenario"]
        report = result["report"]
        analysis = result["analysis"]
        
        print(f"{scenario:<15} "
              f"{report.total_duration:>7.1f}s "
              f"{report.peak_memory_mb:>7.1f}MB "
              f"{report.peak_cpu_percent:>6.1f}% "
              f"{analysis['performance_score']:>6.1f} "
              f"{len(report.performance_bottlenecks):>11}")
    
    # Show critical path analysis
    print(f"\n🎯 CRITICAL PATH ANALYSIS")
    print("-" * 40)
    
    optimal_result = next(r for r in results if r["scenario"] == "optimal")
    bottlenecked_result = next(r for r in results if r["scenario"] == "bottlenecked")
    
    print("Optimal Scenario Critical Path:")
    for method in optimal_result["report"].critical_path[:3]:
        profile = optimal_result["report"].method_profiles[method]
        print(f"  • {method}: {profile.total_time:.2f}s")
    
    print("\nBottlenecked Scenario Critical Path:")
    for method in bottlenecked_result["report"].critical_path[:3]:
        profile = bottlenecked_result["report"].method_profiles[method]
        print(f"  • {method}: {profile.total_time:.2f}s")
    
    print(f"\n✅ Demo completed! Detailed reports saved to: {config.output_directory}")
    
    return results


if __name__ == "__main__":
    # Run demo when script is executed directly
    results = run_comprehensive_profiling_demo()
    
    # Optionally run unit tests
    print("\n🧪 Running Unit Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
