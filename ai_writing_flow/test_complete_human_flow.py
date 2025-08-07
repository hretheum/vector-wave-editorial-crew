#!/usr/bin/env python3
"""Test Complete Flow with Human-in-Loop - Task 10.1"""

import sys
import time
import asyncio

sys.path.append('src')

from ai_writing_flow.crewai_flow.flows.ui_integrated_flow import UIIntegratedFlow
from ai_writing_flow.crewai_flow.flows.integrated_approval_flow import IntegratedApprovalFlow
from ai_writing_flow.crewai_flow.flows.realtime_status_flow import RealtimeStatusFlow
from ai_writing_flow.utils.ui_bridge_v2 import UIBridgeV2
from ai_writing_flow.models import HumanFeedbackDecision

def test_complete_human_flow():
    """Test complete flow scenarios with human interaction"""
    
    print("🧪 Testing Complete Flow with Human-in-Loop - Task 10.1")
    print("=" * 60)
    
    # Test 1: Standard approval flow
    print("\n1️⃣ Testing standard approval flow...")
    try:
        ui_bridge = UIBridgeV2()
        
        # Create integrated approval flow
        approval_flow = IntegratedApprovalFlow(config={
            'pattern': 'full_review',
            'ui_bridge': ui_bridge,
            'auto_approve': True  # For testing
        })
        
        content_data = {
            'topic_title': 'Complete Flow Test with Approval',
            'platform': 'Blog',
            'content': 'Test content for approval flow',
            'quality_score': 0.9,
            'checklist_status': 'All checks passed'
        }
        
        # Execute approval pattern
        result = approval_flow.execute_approval_pattern(content_data)
        print(f"✅ Approval pattern started: {result['pattern']}")
        
        # Process reviews
        sequence_result = approval_flow.process_review_sequence(result)
        print(f"✅ Reviews completed: {sequence_result['reviews_completed']}")
        
        # Get final decision
        final_route = approval_flow.route_final_decision(sequence_result)
        print(f"✅ Final decision: {final_route}")
        
        # Handle final decision
        if final_route == 'approved':
            final_result = approval_flow.handle_approval()
            print(f"✅ Content approved: {final_result['message']}")
        
        assert final_route == 'approved'
        
    except Exception as e:
        print(f"❌ Standard approval flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Flow with revision requests
    print("\n2️⃣ Testing flow with revision requests...")
    try:
        # Create UI integrated flow
        revision_flow = UIIntegratedFlow(config={
            'ui_bridge': ui_bridge,
            'auto_mode': False  # Use actual feedback simulation
        })
        
        # Mock UI Bridge to return revision feedback
        def mock_get_feedback(review_id=None, timeout=300):
            time.sleep(0.5)  # Simulate delay
            return HumanFeedbackDecision(
                feedback_type="major",
                feedback_text="Need to restructure content for better flow",
                specific_changes=["Add introduction", "Reorganize sections"],
                continue_to_stage="generate_draft"
            )
        
        # Temporarily replace method
        original_method = ui_bridge.get_human_feedback
        ui_bridge.get_human_feedback = mock_get_feedback
        
        try:
            # Start flow
            inputs = {
                'topic_title': 'Content Requiring Major Revisions',
                'platform': 'LinkedIn'
            }
            
            session_result = revision_flow.start_ui_flow(inputs)
            flow_result = revision_flow.process_with_ui_updates(session_result)
            
            print("✅ Flow with revisions completed")
            print(f"✅ Final draft includes revisions: {'Restructured based on feedback' in revision_flow.state.final_draft}")
            
            assert 'Restructured based on feedback' in revision_flow.state.final_draft
            
        finally:
            # Restore original method
            ui_bridge.get_human_feedback = original_method
        
    except Exception as e:
        print(f"❌ Revision flow test failed: {e}")
        return False
    
    # Test 3: Flow with real-time status and human interaction
    print("\n3️⃣ Testing flow with real-time status and human interaction...")
    try:
        # Create real-time status flow
        status_flow = RealtimeStatusFlow(config={
            'ui_bridge': ui_bridge
        })
        
        # Start with status tracking
        inputs = {
            'topic_title': 'Real-time Flow with Human Review',
            'platform': 'Blog'
        }
        
        start_result = status_flow.start_with_status_tracking(inputs)
        print(f"✅ Real-time tracking active: {start_result['status_tracking']}")
        
        # Get initial status
        initial_status = status_flow.get_detailed_status()
        print(f"✅ Initial progress: {initial_status['overall_progress']:.1f}%")
        
        # Execute flow
        exec_result = status_flow.execute_with_detailed_status(start_result)
        
        # Get final status
        final_status = status_flow.get_detailed_status()
        print(f"✅ Final progress: {final_status['overall_progress']:.1f}%")
        print(f"✅ Status updates sent: {final_status['status_updates_sent']}")
        
        assert final_status['overall_progress'] == 100.0
        
    except Exception as e:
        print(f"❌ Real-time status flow test failed: {e}")
        return False
    
    # Test 4: Quick review pattern
    print("\n4️⃣ Testing quick review pattern...")
    try:
        quick_flow = IntegratedApprovalFlow(config={
            'pattern': 'quick_review',
            'ui_bridge': ui_bridge,
            'auto_approve': True
        })
        
        # Execute quick review
        result = quick_flow.execute_approval_pattern({'content': 'Quick test'})
        sequence_result = quick_flow.process_review_sequence(result)
        
        print(f"✅ Quick review completed")
        print(f"✅ Reviews: {sequence_result['reviews_completed']}")
        print(f"✅ Max time: {quick_flow.state.pattern_config.max_total_time}s")
        
        assert len(sequence_result['reviews_completed']) == 1  # Only draft_completion
        
    except Exception as e:
        print(f"❌ Quick review test failed: {e}")
        return False
    
    # Test 5: Editorial review pattern with multiple revisions
    print("\n5️⃣ Testing editorial review pattern...")
    try:
        editorial_flow = IntegratedApprovalFlow(config={
            'pattern': 'editorial_review',
            'ui_bridge': ui_bridge,
            'auto_approve': True
        })
        
        # Check configuration
        print(f"✅ Editorial pattern configured")
        print(f"✅ Max revisions: {editorial_flow.state.pattern_config.max_revisions}")
        print(f"✅ Timeout enabled: {editorial_flow.state.pattern_config.enable_timeout}")
        
        assert editorial_flow.state.pattern_config.max_revisions == 5
        assert editorial_flow.state.pattern_config.enable_timeout == False
        
    except Exception as e:
        print(f"❌ Editorial review test failed: {e}")
        return False
    
    # Test 6: Auto-approve pattern
    print("\n6️⃣ Testing auto-approve pattern...")
    try:
        auto_flow = IntegratedApprovalFlow(config={
            'pattern': 'auto_approve',
            'ui_bridge': ui_bridge
        })
        
        # Execute auto-approve
        result = auto_flow.execute_approval_pattern({'content': 'Auto test'})
        
        print(f"✅ Auto-approve executed")
        print(f"✅ Approved: {result['approved']}")
        print(f"✅ Reviews completed: {result['reviews_completed']}")
        
        assert result['approved'] == True
        assert len(result['reviews_completed']) == 0
        
    except Exception as e:
        print(f"❌ Auto-approve test failed: {e}")
        return False
    
    # Test 7: End-to-end flow with all components
    print("\n7️⃣ Testing end-to-end flow with all components...")
    try:
        # Create comprehensive flow
        e2e_flow = UIIntegratedFlow(config={
            'ui_bridge': ui_bridge,
            'auto_mode': True
        })
        
        # Create approval flow
        e2e_approval = IntegratedApprovalFlow(config={
            'pattern': 'full_review',
            'ui_bridge': ui_bridge,
            'auto_approve': True
        })
        
        # Execute both flows
        inputs = {
            'topic_title': 'End-to-End Integration Test',
            'platform': 'Newsletter',
            'key_themes': ['integration', 'testing', 'human-in-loop']
        }
        
        # Start UI flow
        session = e2e_flow.start_ui_flow(inputs)
        
        # Process with updates
        ui_result = e2e_flow.process_with_ui_updates(session)
        
        # Run approval flow on the output
        approval_data = {
            'content': e2e_flow.state.final_draft,
            'quality_score': 0.85,
            'checklist_status': 'Passed'
        }
        
        approval_result = e2e_approval.execute_approval_pattern(approval_data)
        approval_sequence = e2e_approval.process_review_sequence(approval_result)
        
        print("✅ End-to-end flow completed")
        print(f"✅ UI flow success: {ui_result['success']}")
        print(f"✅ Approval reviews: {len(approval_sequence['reviews_completed'])}")
        print(f"✅ Final status: {approval_sequence['final_status']}")
        
        assert ui_result['success'] == True
        assert approval_sequence['final_status'] == 'completed'
        
    except Exception as e:
        print(f"❌ End-to-end test failed: {e}")
        return False
    
    # Test 8: Flow performance metrics
    print("\n8️⃣ Testing flow performance metrics...")
    try:
        # Collect metrics from various flows
        ui_metrics = e2e_flow.get_ui_metrics()
        approval_summary = e2e_approval.get_pattern_summary()
        
        print("✅ Performance metrics collected")
        print(f"✅ UI updates sent: {ui_metrics['progress_updates_sent']}")
        print(f"✅ Approval timeouts: {approval_summary['timeouts_occurred']}")
        print(f"✅ Total execution time: {ui_metrics['total_execution_time']:.1f}s")
        
        # Verify performance is acceptable
        assert ui_metrics['total_execution_time'] < 30  # Should complete within 30s
        
    except Exception as e:
        print(f"❌ Performance metrics test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All Complete Flow tests passed!")
    print("✅ Task 10.1 implementation is complete and functional")
    print("\nKey achievements:")
    print("- All flow patterns tested with human interaction")
    print("- Revision handling verified")
    print("- Real-time status updates working")
    print("- Multiple approval patterns functional")
    print("- End-to-end integration verified")
    print("- Performance within acceptable limits")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_complete_human_flow()
    exit(0 if success else 1)