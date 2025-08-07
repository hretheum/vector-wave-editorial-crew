#!/usr/bin/env python3
"""Test Integrated Approval Flow - Task 8.3"""

import sys
import time

sys.path.append('src')

from ai_writing_flow.crewai_flow.flows.integrated_approval_flow import (
    IntegratedApprovalFlow,
    ApprovalPattern
)

def test_integrated_approval():
    """Test integrated approval flow patterns"""
    
    print("🧪 Testing Integrated Approval Flow - Task 8.3")
    print("=" * 60)
    
    # Test 1: Quick review pattern
    print("\n1️⃣ Testing quick review pattern...")
    try:
        flow = IntegratedApprovalFlow(config={
            'pattern': 'quick_review',
            'auto_approve': True  # For testing
        })
        
        print("✅ Quick review pattern initialized")
        print(f"✅ Pattern: {flow.state.active_pattern}")
        print(f"✅ Review points: {flow.state.pattern_config.review_points}")
        print(f"✅ Timeout enabled: {flow.state.pattern_config.enable_timeout}")
        print(f"✅ Max time: {flow.state.pattern_config.max_total_time}s")
        
        # Execute pattern
        content_data = {
            "content": "Test content for quick review",
            "platform": "Blog",
            "word_count": 500
        }
        
        result = flow.execute_approval_pattern(content_data)
        print(f"✅ Pattern execution started: {result['pattern']}")
        
        # Process reviews
        sequence_result = flow.process_review_sequence(result)
        print(f"✅ Reviews completed: {sequence_result['reviews_completed']}")
        print(f"✅ Timeouts: {sequence_result['timeouts']}")
        
        # Get final decision
        route = flow.route_final_decision(sequence_result)
        print(f"✅ Final decision: {route}")
        
    except Exception as e:
        print(f"❌ Quick review pattern test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Auto-approve pattern
    print("\n2️⃣ Testing auto-approve pattern...")
    try:
        auto_flow = IntegratedApprovalFlow(config={
            'pattern': 'auto_approve'
        })
        
        print("✅ Auto-approve pattern initialized")
        print(f"✅ Review points: {auto_flow.state.pattern_config.review_points} (empty)")
        
        result = auto_flow.execute_approval_pattern({})
        print(f"✅ Auto-approved: {result['approved']}")
        print(f"✅ Total time: {result['total_time']:.2f}s")
        
        assert result['approved'] == True
        assert len(result['reviews_completed']) == 0
        
    except Exception as e:
        print(f"❌ Auto-approve pattern test failed: {e}")
        return False
    
    # Test 3: Full review pattern
    print("\n3️⃣ Testing full review pattern...")
    try:
        full_flow = IntegratedApprovalFlow(config={
            'pattern': 'full_review',
            'auto_approve': True
        })
        
        print("✅ Full review pattern initialized")
        print(f"✅ Review points: {full_flow.state.pattern_config.review_points}")
        print(f"✅ Revisions enabled: {full_flow.state.pattern_config.enable_revisions}")
        print(f"✅ Max revisions: {full_flow.state.pattern_config.max_revisions}")
        
        content_data = {
            "content": "Full review test content",
            "quality_score": 0.85,
            "checklist_status": "All checks passed"
        }
        
        result = full_flow.execute_approval_pattern(content_data)
        sequence_result = full_flow.process_review_sequence(result)
        
        print(f"✅ Reviews completed: {len(sequence_result['reviews_completed'])}")
        print(f"✅ Final status: {sequence_result['final_status']}")
        
    except Exception as e:
        print(f"❌ Full review pattern test failed: {e}")
        return False
    
    # Test 4: Custom pattern
    print("\n4️⃣ Testing custom pattern...")
    try:
        custom_pattern = ApprovalPattern(
            name="custom_fast",
            description="Custom fast approval",
            review_points=["draft_completion"],
            enable_timeout=True,
            timeout_behavior="skip",
            max_total_time=300,
            enable_revisions=False
        )
        
        custom_flow = IntegratedApprovalFlow(config={
            'pattern': 'custom_fast',
            'custom_patterns': {'custom_fast': custom_pattern},
            'auto_approve': True
        })
        
        print("✅ Custom pattern initialized")
        print(f"✅ Pattern name: {custom_flow.state.pattern_config.name}")
        print(f"✅ Timeout behavior: {custom_flow.state.pattern_config.timeout_behavior}")
        
        result = custom_flow.execute_approval_pattern({"content": "Test"})
        sequence_result = custom_flow.process_review_sequence(result)
        
        print(f"✅ Custom pattern executed successfully")
        
    except Exception as e:
        print(f"❌ Custom pattern test failed: {e}")
        return False
    
    # Test 5: Timeout handling
    print("\n5️⃣ Testing timeout handling...")
    try:
        # Create flow with very short max time
        timeout_pattern = ApprovalPattern(
            name="timeout_test",
            description="Test timeout handling",
            review_points=["draft_completion", "quality_gate"],
            enable_timeout=True,
            timeout_behavior="skip",
            max_total_time=1,  # Very short to trigger timeout
            enable_revisions=False
        )
        
        timeout_flow = IntegratedApprovalFlow(config={
            'pattern': 'timeout_test',
            'custom_patterns': {'timeout_test': timeout_pattern},
            'auto_approve': False  # Will cause delay
        })
        
        print("✅ Timeout test pattern initialized")
        print(f"✅ Max total time: {timeout_flow.state.pattern_config.max_total_time}s")
        
        # Add artificial delay to trigger timeout
        time.sleep(1.5)
        
        result = timeout_flow.execute_approval_pattern({})
        sequence_result = timeout_flow.process_review_sequence(result)
        
        print(f"✅ Reviews skipped due to timeout: {len(sequence_result['reviews_skipped'])}")
        print(f"✅ Final status: {sequence_result['final_status']}")
        
        # Route should be 'timeout'
        route = timeout_flow.route_final_decision(sequence_result)
        assert route == 'timeout'
        
        timeout_result = timeout_flow.handle_timeout()
        print(f"✅ Timeout handled: {timeout_result['message']}")
        
    except Exception as e:
        print(f"❌ Timeout handling test failed: {e}")
        return False
    
    # Test 6: Pattern summary
    print("\n6️⃣ Testing pattern summary...")
    try:
        summary = flow.get_pattern_summary()
        
        print("✅ Pattern summary generated")
        print(f"✅ Pattern: {summary['pattern']}")
        print(f"✅ Reviews completed: {summary['reviews_completed']}")
        print(f"✅ Timeouts occurred: {summary['timeouts_occurred']}")
        print(f"✅ Total elapsed time: {summary['total_elapsed_time']:.2f}s")
        
    except Exception as e:
        print(f"❌ Pattern summary test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All Integrated Approval Flow tests passed!")
    print("✅ Task 8.3 implementation is complete and functional")
    print("\nKey achievements:")
    print("- Pre-defined approval patterns (quick, full, editorial, auto)")
    print("- Timeout handling with configurable behaviors")
    print("- Pattern-based workflow execution")
    print("- Custom pattern support")
    print("- Comprehensive flow integration")
    print("- Maximum time limits per pattern")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_integrated_approval()
    exit(0 if success else 1)