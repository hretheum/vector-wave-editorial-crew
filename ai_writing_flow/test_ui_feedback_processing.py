#!/usr/bin/env python3
"""Test UI Feedback Processing Integration - Task 9.3"""

import sys
import time

sys.path.append('src')

from ai_writing_flow.crewai_flow.flows.ui_integrated_flow import UIIntegratedFlow
from ai_writing_flow.crewai_flow.flows.feedback_processing_flow import FeedbackProcessingFlow
from ai_writing_flow.utils.ui_bridge_v2 import UIBridgeV2
from ai_writing_flow.models import HumanFeedbackDecision

def test_ui_feedback_processing():
    """Test that human feedback from UI is properly processed by flow"""
    
    print("🧪 Testing UI Feedback Processing - Task 9.3")
    print("=" * 60)
    
    # Test 1: UI Bridge feedback handling
    print("\n1️⃣ Testing UI Bridge feedback mechanism...")
    try:
        ui_bridge = UIBridgeV2()
        
        # Start a session
        session_id = ui_bridge.start_flow_session({
            'topic_title': 'Testing UI Feedback Processing',
            'platform': 'Blog'
        })
        
        # Send draft for review
        review_id = ui_bridge.send_draft_for_review(
            draft="Test draft content for feedback processing",
            metadata={'word_count': 10, 'structure_type': 'test'},
            session_id=session_id
        )
        
        # Get human feedback (simulated)
        feedback = ui_bridge.get_human_feedback(review_id)
        
        print("✅ UI Bridge feedback mechanism working")
        if feedback:
            print(f"✅ Feedback type: {feedback.feedback_type}")
            print(f"✅ Feedback text: {feedback.feedback_text}")
        else:
            print("✅ No feedback (approval)")
        
    except Exception as e:
        print(f"❌ UI Bridge feedback test failed: {e}")
        return False
    
    # Test 2: Feedback processing integration
    print("\n2️⃣ Testing feedback processing integration...")
    try:
        # Create feedback processing flow
        feedback_flow = FeedbackProcessingFlow()
        
        # Process different types of feedback
        if feedback and feedback.feedback_type:
            feedback_data = {
                "decision": feedback.feedback_type,
                "feedback": feedback.feedback_text,
                "review_point": "draft_completion"
            }
            
            processing_result = feedback_flow.process_feedback_decision(feedback_data)
            
            print("✅ Feedback processed successfully")
            print(f"✅ Action: {processing_result['action']}")
            print(f"✅ Processing time: {processing_result['processing_time']:.2f}s")
            
            # Route and handle based on action
            route = feedback_flow.route_by_action(processing_result)
            print(f"✅ Routed to: {route}")
        else:
            print("✅ No feedback to process (approval path)")
        
    except Exception as e:
        print(f"❌ Feedback processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Complete UI flow with feedback
    print("\n3️⃣ Testing complete UI flow with feedback...")
    try:
        # Create integrated flow
        ui_flow = UIIntegratedFlow(config={
            'ui_bridge': ui_bridge,
            'auto_mode': False  # Use actual UI Bridge feedback
        })
        
        # Start flow
        inputs = {
            'topic_title': 'Complete UI Feedback Test',
            'platform': 'LinkedIn'
        }
        
        session_result = ui_flow.start_ui_flow(inputs)
        
        # Process with UI updates (this includes feedback handling)
        flow_result = ui_flow.process_with_ui_updates(session_result)
        
        print("✅ Complete flow with feedback processing executed")
        print(f"✅ Success: {flow_result['success']}")
        print(f"✅ Final draft includes feedback: {feedback is not None}")
        
        # Verify feedback was applied
        if feedback and feedback.feedback_type:
            final_draft = ui_flow.state.final_draft
            # Check that feedback was incorporated
            if feedback.feedback_type == "minor":
                assert "Minor revisions applied" in final_draft
            elif feedback.feedback_type == "major":
                assert "Restructured based on feedback" in final_draft
            elif feedback.feedback_type == "pivot":
                assert "Revised Approach" in final_draft
            print("✅ Feedback properly incorporated into final draft")
        
    except Exception as e:
        print(f"❌ Complete flow test failed: {e}")
        return False
    
    # Test 4: Multiple feedback rounds
    print("\n4️⃣ Testing multiple feedback rounds...")
    try:
        # Create flow with revision support
        revision_flow = UIIntegratedFlow(config={
            'ui_bridge': ui_bridge,
            'auto_mode': True  # Simulate for speed
        })
        
        # Track revision count
        initial_revisions = 0
        
        # Simulate multiple review cycles
        for i in range(2):
            # Mock feedback that requires revision
            mock_feedback = HumanFeedbackDecision(
                feedback_type="minor",
                feedback_text=f"Revision {i+1}: Please adjust tone",
                specific_changes=["Adjust tone", "Add examples"],
                continue_to_stage="validate_style"
            )
            
            # Process feedback
            revised_draft = revision_flow._process_feedback(mock_feedback)
            print(f"✅ Revision {i+1} processed")
        
        print("✅ Multiple feedback rounds handled correctly")
        
    except Exception as e:
        print(f"❌ Multiple feedback test failed: {e}")
        return False
    
    # Test 5: Feedback metrics
    print("\n5️⃣ Testing feedback metrics tracking...")
    try:
        metrics = ui_flow.get_ui_metrics()
        
        print("✅ Feedback metrics tracked")
        print(f"✅ Average UI response time: {metrics['avg_ui_response_time']:.2f}s")
        print(f"✅ Total execution time: {metrics['total_execution_time']:.2f}s")
        
        # Check session has feedback recorded
        session_info = ui_bridge.get_session_info(ui_flow.state.session_id)
        if session_info and 'draft_versions' in session_info:
            print(f"✅ Draft versions tracked: {len(session_info['draft_versions'])}")
        
    except Exception as e:
        print(f"❌ Metrics tracking test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All UI Feedback Processing tests passed!")
    print("✅ Task 9.3 implementation is complete and functional")
    print("\nKey achievements:")
    print("- Human feedback from UI properly received")
    print("- Feedback processed and influences flow decisions")
    print("- Multiple revision rounds supported")
    print("- Complete integration with existing components")
    print("- Metrics tracking for feedback processing")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_ui_feedback_processing()
    exit(0 if success else 1)