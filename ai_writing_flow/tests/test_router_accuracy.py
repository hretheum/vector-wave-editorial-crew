#!/usr/bin/env python3
"""
Test Router Accuracy - Task 7.1

Comprehensive test suite for validating routing accuracy
of the CrewAI Flow @router decorator implementation.
"""

import sys
import json
import time
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

sys.path.append('src')

from ai_writing_flow.crewai_flow.flows.research_flow import ResearchFlow
from ai_writing_flow.models import ContentAnalysisResult


@dataclass
class TestCase:
    """Test case for router accuracy testing"""
    name: str
    topic: str
    key_themes: List[str]
    editorial_recommendations: str
    expected_route: str
    expected_content_type: str
    expected_score_range: Tuple[float, float]


class RouterAccuracyTester:
    """Comprehensive router accuracy testing suite"""
    
    def __init__(self):
        self.test_cases = self._create_test_cases()
        self.results = {
            "total": 0,
            "correct": 0,
            "incorrect": 0,
            "accuracy": 0.0,
            "details": []
        }
    
    def _create_test_cases(self) -> List[TestCase]:
        """Create comprehensive test cases for different content types"""
        return [
            # Technical content cases
            TestCase(
                name="Deep Technical Architecture",
                topic="Implementing Microservices with Event Sourcing",
                key_themes=["architecture", "patterns", "implementation"],
                editorial_recommendations="Include code examples and performance benchmarks",
                expected_route="deep_research",
                expected_content_type="TECHNICAL",
                expected_score_range=(0.8, 1.0)
            ),
            TestCase(
                name="Framework Deep Dive",
                topic="Building Real-Time Systems with Apache Kafka",
                key_themes=["kafka", "streaming", "performance"],
                editorial_recommendations="Technical deep dive with configuration examples",
                expected_route="deep_research",
                expected_content_type="TECHNICAL",
                expected_score_range=(0.8, 1.0)
            ),
            TestCase(
                name="Algorithm Implementation",
                topic="Implementing Distributed Consensus Algorithms",
                key_themes=["algorithms", "distributed systems", "consensus"],
                editorial_recommendations="Mathematical proofs and implementation details",
                expected_route="deep_research",
                expected_content_type="TECHNICAL",
                expected_score_range=(0.9, 1.0)
            ),
            
            # Viral content cases
            TestCase(
                name="Trending AI Controversy",
                topic="AI Will Replace All Developers by 2025",
                key_themes=["controversy", "future", "disruption"],
                editorial_recommendations="Create buzz with bold predictions",
                expected_route="quick_research",
                expected_content_type="VIRAL",
                expected_score_range=(0.7, 0.9)
            ),
            TestCase(
                name="Shocking Tech News",
                topic="This One Weird Trick Makes Your Code 10x Faster",
                key_themes=["shocking", "performance", "tricks"],
                editorial_recommendations="Clickbait style with surprising revelation",
                expected_route="quick_research",
                expected_content_type="VIRAL",
                expected_score_range=(0.8, 1.0)
            ),
            TestCase(
                name="Hot Take on Trends",
                topic="Why Everyone Is Wrong About Cloud Computing",
                key_themes=["controversy", "trends", "opinion"],
                editorial_recommendations="Contrarian view to spark debate",
                expected_route="quick_research",
                expected_content_type="VIRAL",
                expected_score_range=(0.7, 0.9)
            ),
            
            # Standard content cases
            TestCase(
                name="Industry Overview",
                topic="State of DevOps in 2025",
                key_themes=["industry", "trends", "best practices"],
                editorial_recommendations="Balanced overview with practical insights",
                expected_route="standard_research",
                expected_content_type="STANDARD",
                expected_score_range=(0.5, 0.7)
            ),
            TestCase(
                name="Tutorial Guide",
                topic="Getting Started with Container Orchestration",
                key_themes=["tutorial", "beginner", "guide"],
                editorial_recommendations="Step-by-step guide for beginners",
                expected_route="standard_research",
                expected_content_type="STANDARD",
                expected_score_range=(0.4, 0.6)
            ),
            TestCase(
                name="Best Practices Article",
                topic="Security Best Practices for Modern Applications",
                key_themes=["security", "best practices", "guidelines"],
                editorial_recommendations="Comprehensive guide with checklists",
                expected_route="standard_research",
                expected_content_type="STANDARD",
                expected_score_range=(0.5, 0.7)
            ),
            
            # Edge cases
            TestCase(
                name="Mixed Technical-Viral",
                topic="This Algorithm Hack Will Blow Your Mind",
                key_themes=["algorithm", "viral", "hack"],
                editorial_recommendations="Technical content with viral framing",
                expected_route="quick_research",  # Viral framing should win
                expected_content_type="VIRAL",
                expected_score_range=(0.6, 0.8)
            ),
            TestCase(
                name="Low Quality Topic",
                topic="Random Thoughts About Programming",
                key_themes=["random", "thoughts"],
                editorial_recommendations="Just some musings",
                expected_route="skip_research",
                expected_content_type="STANDARD",
                expected_score_range=(0.0, 0.3)
            ),
            TestCase(
                name="Ambiguous Content",
                topic="Understanding Modern Software Development",
                key_themes=["software", "development"],
                editorial_recommendations="General overview",
                expected_route="standard_research",
                expected_content_type="STANDARD",
                expected_score_range=(0.4, 0.6)
            )
        ]
    
    def run_test_case(self, test_case: TestCase) -> Dict[str, Any]:
        """Run a single test case and return results"""
        print(f"\n🧪 Testing: {test_case.name}")
        print(f"   Topic: {test_case.topic}")
        
        # Create flow instance
        flow = ResearchFlow(config={'verbose': False})
        
        # Prepare inputs
        inputs = {
            'topic_title': test_case.topic,
            'platform': 'Blog',
            'key_themes': test_case.key_themes,
            'editorial_recommendations': test_case.editorial_recommendations
        }
        
        # Run content analysis
        start_time = time.time()
        analysis_result = flow.analyze_content(inputs)
        analysis_time = time.time() - start_time
        
        # Get routing decision
        route_decision = flow.route_by_content_type(analysis_result)
        
        # Extract results
        actual_content_type = flow.state.content_analysis.content_type
        actual_score = flow.state.content_analysis.viral_score
        
        # Validate results
        route_correct = route_decision == test_case.expected_route
        type_correct = actual_content_type == test_case.expected_content_type
        score_in_range = test_case.expected_score_range[0] <= actual_score <= test_case.expected_score_range[1]
        
        overall_correct = route_correct and type_correct and score_in_range
        
        # Build result
        result = {
            "test_case": test_case.name,
            "topic": test_case.topic,
            "expected": {
                "route": test_case.expected_route,
                "content_type": test_case.expected_content_type,
                "score_range": test_case.expected_score_range
            },
            "actual": {
                "route": route_decision,
                "content_type": actual_content_type,
                "score": actual_score,
                "kb_consulted": hasattr(flow.state, 'kb_consulted') and flow.state.kb_consulted
            },
            "validation": {
                "route_correct": route_correct,
                "type_correct": type_correct,
                "score_in_range": score_in_range,
                "overall_correct": overall_correct
            },
            "performance": {
                "analysis_time": analysis_time
            }
        }
        
        # Print result
        status = "✅" if overall_correct else "❌"
        print(f"   {status} Route: {route_decision} (expected: {test_case.expected_route})")
        print(f"   {status} Type: {actual_content_type} (expected: {test_case.expected_content_type})")
        print(f"   {status} Score: {actual_score:.2f} (expected: {test_case.expected_score_range})")
        
        return result
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all test cases and calculate accuracy"""
        print("🎯 Running Router Accuracy Tests - Task 7.1")
        print("=" * 60)
        
        for test_case in self.test_cases:
            result = self.run_test_case(test_case)
            
            self.results["total"] += 1
            if result["validation"]["overall_correct"]:
                self.results["correct"] += 1
            else:
                self.results["incorrect"] += 1
            
            self.results["details"].append(result)
        
        # Calculate accuracy
        self.results["accuracy"] = self.results["correct"] / self.results["total"] if self.results["total"] > 0 else 0
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate detailed accuracy report"""
        report = "\n" + "=" * 60 + "\n"
        report += "📊 ROUTER ACCURACY TEST RESULTS\n"
        report += "=" * 60 + "\n\n"
        
        # Summary
        report += f"Total Test Cases: {self.results['total']}\n"
        report += f"Correct Decisions: {self.results['correct']}\n"
        report += f"Incorrect Decisions: {self.results['incorrect']}\n"
        report += f"Overall Accuracy: {self.results['accuracy']:.1%}\n\n"
        
        # Detailed breakdown by content type
        type_stats = {"TECHNICAL": {"total": 0, "correct": 0},
                     "VIRAL": {"total": 0, "correct": 0},
                     "STANDARD": {"total": 0, "correct": 0}}
        
        for detail in self.results["details"]:
            content_type = detail["expected"]["content_type"]
            type_stats[content_type]["total"] += 1
            if detail["validation"]["overall_correct"]:
                type_stats[content_type]["correct"] += 1
        
        report += "Accuracy by Content Type:\n"
        for content_type, stats in type_stats.items():
            if stats["total"] > 0:
                accuracy = stats["correct"] / stats["total"]
                report += f"- {content_type}: {accuracy:.1%} ({stats['correct']}/{stats['total']})\n"
        
        # Failed cases analysis
        report += "\nFailed Test Cases:\n"
        failed_count = 0
        for detail in self.results["details"]:
            if not detail["validation"]["overall_correct"]:
                failed_count += 1
                report += f"\n{failed_count}. {detail['test_case']}:\n"
                report += f"   Topic: {detail['topic']}\n"
                
                if not detail["validation"]["route_correct"]:
                    report += f"   ❌ Route: {detail['actual']['route']} (expected: {detail['expected']['route']})\n"
                if not detail["validation"]["type_correct"]:
                    report += f"   ❌ Type: {detail['actual']['content_type']} (expected: {detail['expected']['content_type']})\n"
                if not detail["validation"]["score_in_range"]:
                    report += f"   ❌ Score: {detail['actual']['score']:.2f} (expected: {detail['expected']['score_range']})\n"
        
        if failed_count == 0:
            report += "None - All test cases passed! 🎉\n"
        
        # Performance metrics
        report += "\nPerformance Metrics:\n"
        avg_time = sum(d["performance"]["analysis_time"] for d in self.results["details"]) / len(self.results["details"])
        report += f"- Average analysis time: {avg_time:.3f}s\n"
        
        # KB usage statistics
        kb_used = sum(1 for d in self.results["details"] if d["actual"].get("kb_consulted", False))
        report += f"- Knowledge Base consulted: {kb_used}/{self.results['total']} times\n"
        
        report += "\n" + "=" * 60 + "\n"
        
        return report
    
    def save_results(self, filename: str = "router_accuracy_results.json"):
        """Save detailed results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Detailed results saved to: {filename}")


def main():
    """Run router accuracy tests"""
    tester = RouterAccuracyTester()
    
    # Run all tests
    results = tester.run_all_tests()
    
    # Generate and print report
    report = tester.generate_report()
    print(report)
    
    # Save detailed results
    tester.save_results()
    
    # Check if accuracy meets threshold
    ACCURACY_THRESHOLD = 0.9  # 90% accuracy required
    
    if results["accuracy"] >= ACCURACY_THRESHOLD:
        print(f"✅ Router accuracy {results['accuracy']:.1%} meets threshold of {ACCURACY_THRESHOLD:.0%}")
        print("✅ Task 7.1 Decision accuracy testing PASSED")
        return True
    else:
        print(f"❌ Router accuracy {results['accuracy']:.1%} below threshold of {ACCURACY_THRESHOLD:.0%}")
        print("❌ Task 7.1 Decision accuracy testing FAILED")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)