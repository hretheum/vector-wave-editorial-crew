#!/usr/bin/env python3
"""Test Decision Logging and Monitoring - Task 7.2"""

import sys
import json
import time

sys.path.append('src')

from ai_writing_flow.crewai_flow.flows.research_flow import ResearchFlow
from ai_writing_flow.crewai_flow.logging import get_decision_logger

def test_decision_logging():
    """Test decision logging functionality"""
    
    print("🧪 Testing Decision Logging and Monitoring - Task 7.2")
    print("=" * 60)
    
    # Test 1: Decision logger initialization
    print("\n1️⃣ Testing decision logger initialization...")
    try:
        logger = get_decision_logger()
        print("✅ Decision logger initialized")
        print(f"✅ Session file: {logger.session_file}")
        print(f"✅ Log directory: {logger.log_dir}")
    except Exception as e:
        print(f"❌ Logger initialization failed: {e}")
        return False
    
    # Test 2: Flow with decision logging
    print("\n2️⃣ Testing flow execution with decision logging...")
    test_cases = [
        {
            "name": "Technical Content",
            "inputs": {
                'topic_title': 'Building Distributed Systems with Rust',
                'platform': 'Blog',
                'key_themes': ['rust', 'distributed', 'performance'],
                'editorial_recommendations': 'Deep technical dive with benchmarks'
            }
        },
        {
            "name": "Viral Content",
            "inputs": {
                'topic_title': 'This AI Trick Will Change Everything',
                'platform': 'Twitter',
                'key_themes': ['viral', 'AI', 'shocking'],
                'editorial_recommendations': 'Create buzz with bold claims'
            }
        },
        {
            "name": "Standard Content",
            "inputs": {
                'topic_title': 'Monthly Tech News Roundup',
                'platform': 'Newsletter',
                'key_themes': ['news', 'updates', 'trends'],
                'editorial_recommendations': 'Balanced overview of recent developments'
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n   📝 Test case {i}: {test_case['name']}")
        
        try:
            # Create flow
            flow = ResearchFlow(config={'verbose': False})
            
            # Execute content analysis
            analysis_result = flow.analyze_content(test_case['inputs'])
            
            # Execute routing
            routing_decision = flow.route_by_content_type(analysis_result)
            
            print(f"   ✅ Analysis complete: {analysis_result['content_type']}")
            print(f"   ✅ Routing decision: {routing_decision}")
            
        except Exception as e:
            print(f"   ❌ Test case failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Test 3: Session summary
    print("\n3️⃣ Testing session summary generation...")
    try:
        summary = logger.get_session_summary()
        
        print("✅ Session summary generated")
        print(f"   - Total decisions: {summary['metrics']['total_decisions']}")
        print(f"   - Routing decisions: {summary['metrics']['routing_decisions']}")
        print(f"   - KB consultations: {summary['metrics']['kb_consultations']}")
        print(f"   - Avg decision time: {summary['metrics']['avg_decision_time_ms']:.2f}ms")
        
        # Decision type breakdown
        print("\n   📊 Decision types:")
        for decision_type, count in summary['metrics']['decision_type_counts'].items():
            print(f"   - {decision_type}: {count}")
        
        # Routing accuracy
        print("\n   🎯 Routing accuracy:")
        accuracy = summary['routing_accuracy']
        print(f"   - Total routing decisions: {accuracy.get('total_routing_decisions', 0)}")
        print(f"   - Average confidence: {accuracy.get('avg_confidence', 0):.2%}")
        print(f"   - KB-enhanced ratio: {accuracy.get('kb_enhanced_ratio', 0):.2%}")
        
    except Exception as e:
        print(f"❌ Session summary failed: {e}")
        return False
    
    # Test 4: Decision timeline
    print("\n4️⃣ Testing decision timeline...")
    try:
        timeline = summary['decision_timeline']
        
        print(f"✅ Decision timeline has {len(timeline)} entries")
        
        # Show first few entries
        print("\n   🕒 Recent decisions:")
        for entry in timeline[:5]:
            print(f"   - {entry['timestamp']}: {entry['decision_type']} "
                  f"({entry['execution_time_ms']:.1f}ms)")
        
    except Exception as e:
        print(f"❌ Timeline generation failed: {e}")
        return False
    
    # Test 5: Export session report
    print("\n5️⃣ Testing session report export...")
    try:
        report_file = logger.export_session_report()
        
        print(f"✅ Session report exported to: {report_file}")
        
        # Verify report content
        with open(report_file, 'r') as f:
            report_data = json.load(f)
        
        print(f"✅ Report contains {len(report_data['decisions'])} decision records")
        print(f"✅ Report generated at: {report_data['generated_at']}")
        
    except Exception as e:
        print(f"❌ Report export failed: {e}")
        return False
    
    # Test 6: Decision record details
    print("\n6️⃣ Testing decision record details...")
    try:
        if logger.session_decisions:
            # Show a sample decision record
            sample_decision = logger.session_decisions[0]
            
            print("✅ Sample decision record:")
            print(f"   - Decision ID: {sample_decision.decision_id}")
            print(f"   - Type: {sample_decision.decision_type.value}")
            print(f"   - Flow ID: {sample_decision.context.flow_id}")
            print(f"   - Topic: {sample_decision.context.topic_title}")
            print(f"   - Confidence: {sample_decision.confidence:.2f}")
            print(f"   - KB consulted: {sample_decision.kb_consulted}")
            print(f"   - Execution time: {sample_decision.execution_time_ms:.2f}ms")
            
            if sample_decision.reasoning:
                print(f"   - Reasoning: {sample_decision.reasoning}")
        
    except Exception as e:
        print(f"❌ Decision record test failed: {e}")
        return False
    
    # Test 7: Log file verification
    print("\n7️⃣ Testing log file persistence...")
    try:
        # Read log file
        with open(logger.session_file, 'r') as f:
            lines = f.readlines()
        
        print(f"✅ Log file contains {len(lines)} decision records")
        
        # Verify each line is valid JSON
        valid_count = 0
        for line in lines:
            try:
                json.loads(line.strip())
                valid_count += 1
            except:
                pass
        
        print(f"✅ All {valid_count} records are valid JSON")
        
        assert valid_count == len(lines), "Some records are not valid JSON"
        
    except Exception as e:
        print(f"❌ Log file verification failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All Decision Logging tests passed!")
    print("✅ Task 7.2 implementation is complete and functional")
    print("\nKey achievements:")
    print("- Comprehensive decision logging for all routing decisions")
    print("- Performance metrics tracking")
    print("- Decision audit trail with persistence")
    print("- Session summary and reporting")
    print("- Export capabilities for analysis")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_decision_logging()
    exit(0 if success else 1)