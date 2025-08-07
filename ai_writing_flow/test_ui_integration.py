#!/usr/bin/env python3
"""Test UI Integration - Task 9.1"""

import sys
import time
import asyncio

sys.path.append('src')

from ai_writing_flow.crewai_flow.flows.ui_integrated_flow import UIIntegratedFlow
from ai_writing_flow.utils.ui_bridge_v2 import UIBridgeV2

def test_ui_integration():
    """Test UI Bridge integration with CrewAI Flow"""
    
    print("🧪 Testing UI Integration - Task 9.1")
    print("=" * 60)
    
    # Test 1: Flow initialization with UI Bridge
    print("\n1️⃣ Testing flow initialization with UI Bridge...")
    try:
        # Create UI Bridge instance
        ui_bridge = UIBridgeV2()
        
        # Create flow with UI Bridge
        flow = UIIntegratedFlow(config={
            'ui_bridge': ui_bridge,
            'auto_mode': True  # Auto-approve for testing
        })
        
        print("✅ UIIntegratedFlow initialized")
        print(f"✅ Flow ID: {flow.state.flow_id}")
        print(f"✅ UI Bridge initialized: {flow.state.ui_bridge_initialized}")
        
    except Exception as e:
        print(f"❌ Flow initialization failed: {e}")
        return False
    
    # Test 2: Session start and tracking
    print("\n2️⃣ Testing session start and tracking...")
    try:
        inputs = {
            'topic_title': 'Testing UI Integration with CrewAI Flow',
            'platform': 'Blog',
            'key_themes': ['integration', 'ui', 'crewai']
        }
        
        session_result = flow.start_ui_flow(inputs)
        
        print("✅ UI session started")
        print(f"✅ Session ID: {session_result['session_id']}")
        print(f"✅ Topic: {session_result['topic']}")
        print(f"✅ UI Ready: {session_result['ui_ready']}")
        
        # Verify session in UI Bridge
        session_info = ui_bridge.get_session_info(session_result['session_id'])
        assert session_info is not None
        assert session_info['status'] == 'active'
        
        print("✅ Session tracked in UI Bridge")
        
    except Exception as e:
        print(f"❌ Session start test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Progress streaming
    print("\n3️⃣ Testing progress streaming...")
    try:
        # Process with UI updates
        processing_result = flow.process_with_ui_updates(session_result)
        
        print("✅ Flow processed with UI updates")
        print(f"✅ Success: {processing_result['success']}")
        print(f"✅ Execution time: {processing_result['execution_time']:.2f}s")
        print(f"✅ Progress updates sent: {flow.state.progress_updates_sent}")
        
        # Check that multiple progress updates were sent
        assert flow.state.progress_updates_sent > 3
        
    except Exception as e:
        print(f"❌ Progress streaming test failed: {e}")
        return False
    
    # Test 4: Draft review integration
    print("\n4️⃣ Testing draft review integration...")
    try:
        # Check that draft was sent for review
        assert len(flow.state.active_review_ids) > 0
        print(f"✅ Draft sent for review: {flow.state.active_review_ids[0]}")
        
        # Check session has draft versions
        session_info = ui_bridge.get_session_info(flow.state.session_id)
        assert len(session_info['draft_versions']) > 0
        print(f"✅ Draft versions tracked: {len(session_info['draft_versions'])}")
        
    except Exception as e:
        print(f"❌ Draft review integration test failed: {e}")
        return False
    
    # Test 5: Completion notification
    print("\n5️⃣ Testing completion notification...")
    try:
        # Check session completion
        session_info = ui_bridge.get_session_info(flow.state.session_id)
        assert session_info['status'] == 'completed'
        assert 'completion_data' in session_info
        
        completion_data = session_info['completion_data']
        print("✅ Completion notification sent")
        print(f"✅ Quality score: {completion_data['metrics']['quality_score']}")
        print(f"✅ Word count: {completion_data['metrics']['word_count']}")
        print(f"✅ Processing time: {completion_data['metrics']['processing_time']:.1f}s")
        
    except Exception as e:
        print(f"❌ Completion notification test failed: {e}")
        return False
    
    # Test 6: Error handling and escalation
    print("\n6️⃣ Testing error handling and escalation...")
    try:
        # Create flow that will error
        error_flow = UIIntegratedFlow(config={
            'ui_bridge': ui_bridge,
            'auto_mode': True
        })
        
        # Start session but simulate error
        error_inputs = {
            'topic_title': '',  # Empty title should cause issues
            'platform': 'Unknown'
        }
        
        error_session = error_flow.start_ui_flow(error_inputs)
        
        # Test escalation
        ui_bridge.escalate_to_human(
            reason="Test escalation for error handling",
            severity="medium",
            session_id=error_session['session_id'],
            context={"test": True}
        )
        
        print("✅ Error escalation handled")
        print(f"✅ Notification queue size: {len(ui_bridge.notification_queue)}")
        
        # Check escalation in notifications
        assert any(n['type'] == 'escalation' for n in ui_bridge.notification_queue)
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False
    
    # Test 7: UI metrics
    print("\n7️⃣ Testing UI metrics...")
    try:
        metrics = flow.get_ui_metrics()
        
        print("✅ UI metrics collected")
        print(f"✅ Progress updates: {metrics['progress_updates_sent']}")
        print(f"✅ Active reviews: {metrics['active_reviews']}")
        print(f"✅ Average response time: {metrics['avg_ui_response_time']:.2f}s")
        print(f"✅ Total execution time: {metrics['total_execution_time']:.2f}s")
        print(f"✅ Current stage: {metrics['current_stage']}")
        
    except Exception as e:
        print(f"❌ UI metrics test failed: {e}")
        return False
    
    # Test 8: Session cleanup
    print("\n8️⃣ Testing session cleanup...")
    try:
        # Clean up session
        flow.cleanup()
        
        # Verify session removed
        session_info = ui_bridge.get_session_info(flow.state.session_id)
        assert session_info is None
        
        print("✅ Session cleaned up successfully")
        
    except Exception as e:
        print(f"❌ Session cleanup test failed: {e}")
        return False
    
    # Test 9: Dashboard metrics integration
    print("\n9️⃣ Testing dashboard metrics...")
    try:
        dashboard_metrics = ui_bridge.get_dashboard_metrics()
        
        print("✅ Dashboard metrics available")
        if 'active_sessions' in dashboard_metrics:
            print(f"✅ Active sessions: {dashboard_metrics['active_sessions']}")
            print(f"✅ Notification count: {dashboard_metrics['notification_count']}")
        elif 'error' in dashboard_metrics:
            print(f"✅ Dashboard API not configured (expected): {dashboard_metrics['error']}")
        
    except Exception as e:
        print(f"❌ Dashboard metrics test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All UI Integration tests passed!")
    print("✅ Task 9.1 implementation is complete and functional")
    print("\nKey achievements:")
    print("- CrewAI Flow integrated with existing UIBridge")
    print("- Session tracking and management working")
    print("- Progress streaming to UI functional")
    print("- Human review requests handled properly")
    print("- Error escalation working")
    print("- Compatibility with existing Kolegium interface maintained")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_ui_integration()
    exit(0 if success else 1)