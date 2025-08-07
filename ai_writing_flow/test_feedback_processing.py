#!/usr/bin/env python3
"""Test Feedback Processing Flow - Task 8.2"""

import sys
import time
import json

sys.path.append('src')

from ai_writing_flow.crewai_flow.flows.feedback_processing_flow import (
    FeedbackProcessingFlow,
    FeedbackAction
)

def test_feedback_processing():
    """Test feedback processing flow implementation"""
    
    print("🧪 Testing Feedback Processing Flow - Task 8.2")
    print("=" * 60)
    
    # Test 1: Flow initialization
    print("\n1️⃣ Testing flow initialization...")
    try:
        flow = FeedbackProcessingFlow(config={
            'max_revisions': 3
        })
        
        print("✅ FeedbackProcessingFlow initialized")
        print(f"✅ Flow ID: {flow.state.flow_id}")
        print(f"✅ Max revisions: {flow.state.max_revisions}")
        print(f"✅ Available flows: {list(flow.available_flows.keys())}")
        
    except Exception as e:
        print(f"❌ Flow initialization failed: {e}")
        return False
    
    # Test 2: Approve decision processing
    print("\n2️⃣ Testing approve decision...")
    try:
        feedback_data = {
            "decision": "approve",
            "feedback": None,
            "review_point": "draft_completion"
        }
        
        result = flow.process_feedback_decision(feedback_data)
        
        print("✅ Approve decision processed")
        print(f"✅ Action: {result['action']}")
        print(f"✅ Stage: {result['stage']}")
        
        assert result['action'] == FeedbackAction.CONTINUE.value
        
        # Test routing
        route = flow.route_by_action(result)
        assert route == "continue"
        
        # Handle continue
        continue_result = flow.handle_continue()
        print(f"✅ Continue handled: {continue_result['message']}")
        
    except Exception as e:
        print(f"❌ Approve decision test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Revise decision processing
    print("\n3️⃣ Testing revise decision...")
    try:
        feedback_data = {
            "decision": "revise",
            "feedback": "Please add more technical details and examples",
            "review_point": "content_review"
        }
        
        result = flow.process_feedback_decision(feedback_data)
        
        print("✅ Revise decision processed")
        print(f"✅ Action: {result['action']}")
        print(f"✅ Revision count: {result['revision_count']}")
        
        assert result['action'] == FeedbackAction.REVISE.value
        
        # Handle revision
        revise_result = flow.handle_revision()
        print(f"✅ Revision handled: {revise_result['message']}")
        print(f"✅ Revision context included: {'revision_context' in revise_result}")
        
        assert flow.state.revision_count == 1
        assert len(flow.state.revision_history) == 1
        
    except Exception as e:
        print(f"❌ Revise decision test failed: {e}")
        return False
    
    # Test 4: Edit decision processing
    print("\n4️⃣ Testing edit decision...")
    try:
        feedback_data = {
            "decision": "edit",
            "feedback": "Change the title to be more engaging\nAdd a conclusion section\nRemove the third paragraph",
            "review_point": "final_review"
        }
        
        result = flow.process_feedback_decision(feedback_data)
        
        print("✅ Edit decision processed")
        print(f"✅ Action: {result['action']}")
        
        assert result['action'] == FeedbackAction.EDIT.value
        
        # Handle edit
        edit_result = flow.handle_edit()
        print(f"✅ Edit handled: {edit_result['message']}")
        print(f"✅ Edit instructions parsed: {edit_result['edits_count']} edits")
        
        # Check edit parsing
        assert edit_result['edits_count'] == 3
        assert any(inst['type'] == 'replace' for inst in edit_result['edit_instructions'])
        assert any(inst['type'] == 'add' for inst in edit_result['edit_instructions'])
        assert any(inst['type'] == 'remove' for inst in edit_result['edit_instructions'])
        
    except Exception as e:
        print(f"❌ Edit decision test failed: {e}")
        return False
    
    # Test 5: Redirect decision processing
    print("\n5️⃣ Testing redirect decision...")
    try:
        feedback_data = {
            "decision": "redirect",
            "feedback": "This needs to be more technical - redirect to technical flow",
            "review_point": "routing_review"
        }
        
        result = flow.process_feedback_decision(feedback_data)
        
        print("✅ Redirect decision processed")
        print(f"✅ Action: {result['action']}")
        
        assert result['action'] == FeedbackAction.REDIRECT.value
        
        # Handle redirect
        redirect_result = flow.handle_redirect()
        print(f"✅ Redirect handled: {redirect_result['message']}")
        print(f"✅ Redirect path: {redirect_result['redirect_path']}")
        
        assert redirect_result['redirect_path'] == 'technical'
        assert flow.state.redirect_flow_path == 'technical'
        
    except Exception as e:
        print(f"❌ Redirect decision test failed: {e}")
        return False
    
    # Test 6: Maximum revisions
    print("\n6️⃣ Testing maximum revisions...")
    try:
        # Reset flow for clean test
        max_rev_flow = FeedbackProcessingFlow(config={'max_revisions': 2})
        
        # Simulate multiple revisions
        for i in range(3):
            feedback_data = {
                "decision": "revise",
                "feedback": f"Revision {i+1} requested",
                "review_point": "content_review"
            }
            
            result = max_rev_flow.process_feedback_decision(feedback_data)
            
            if i < 2:
                revise_result = max_rev_flow.handle_revision()
                print(f"✅ Revision {i+1} processed")
            else:
                # Should hit max revisions
                revise_result = max_rev_flow.handle_revision()
                print(f"✅ Max revisions reached: {revise_result['message']}")
                assert revise_result['action'] == 'terminate'
        
    except Exception as e:
        print(f"❌ Maximum revisions test failed: {e}")
        return False
    
    # Test 7: Terminate decision
    print("\n7️⃣ Testing terminate decision...")
    try:
        feedback_data = {
            "decision": "skip",
            "feedback": "Topic not suitable for publication",
            "review_point": "viability_check"
        }
        
        result = flow.process_feedback_decision(feedback_data)
        
        assert result['action'] == FeedbackAction.TERMINATE.value
        
        # Handle termination
        terminate_result = flow.handle_termination()
        print("✅ Termination handled")
        print(f"✅ Reason: {terminate_result['reason']}")
        
    except Exception as e:
        print(f"❌ Terminate decision test failed: {e}")
        return False
    
    # Test 8: Processing summary
    print("\n8️⃣ Testing processing summary...")
    try:
        summary = flow.get_processing_summary()
        
        print("✅ Processing summary generated")
        print(f"✅ Total revisions: {summary['total_revisions']}")
        print(f"✅ Revision history entries: {len(summary['revision_history'])}")
        print(f"✅ Redirect occurred: {summary['redirect_occurred']}")
        if summary['redirect_details']:
            print(f"✅ Redirect: {summary['redirect_details']['from']} → {summary['redirect_details']['to']}")
        
    except Exception as e:
        print(f"❌ Processing summary failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All Feedback Processing tests passed!")
    print("✅ Task 8.2 implementation is complete and functional")
    print("\nKey achievements:")
    print("- All decision types processed (approve/edit/revise/redirect)")
    print("- Flow branching implemented correctly")
    print("- Revision loop management with limits")
    print("- Edit instruction parsing")
    print("- Redirect target detection")
    print("- Comprehensive decision logging")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_feedback_processing()
    exit(0 if success else 1)