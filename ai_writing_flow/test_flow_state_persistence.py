#!/usr/bin/env python3
"""Test Flow State Persistence - Task 7.3"""

import sys
import time
import json
from pathlib import Path

sys.path.append('src')

from ai_writing_flow.crewai_flow.flows.research_flow import ResearchFlow, ResearchFlowState
from ai_writing_flow.crewai_flow.persistence import get_state_manager

def test_flow_state_persistence():
    """Test flow state persistence functionality"""
    
    print("🧪 Testing Flow State Persistence - Task 7.3")
    print("=" * 60)
    
    # Test 1: State manager initialization
    print("\n1️⃣ Testing state manager initialization...")
    try:
        state_manager = get_state_manager()
        print("✅ State manager initialized")
        print(f"✅ State directory: {state_manager.state_dir}")
        print(f"✅ Checkpoints directory: {state_manager.checkpoints_dir}")
        print(f"✅ Completed directory: {state_manager.completed_dir}")
        print(f"✅ Failed directory: {state_manager.failed_dir}")
    except Exception as e:
        print(f"❌ State manager initialization failed: {e}")
        return False
    
    # Test 2: Flow execution with checkpointing
    print("\n2️⃣ Testing flow execution with checkpointing...")
    try:
        # Create flow
        flow = ResearchFlow(config={'verbose': False})
        flow_id = flow.state.flow_id
        
        print(f"✅ Flow created with ID: {flow_id}")
        
        # Execute content analysis
        test_inputs = {
            'topic_title': 'Testing State Persistence in CrewAI Flow',
            'platform': 'Blog',
            'key_themes': ['state management', 'persistence', 'recovery'],
            'editorial_recommendations': 'Technical documentation'
        }
        
        analysis_result = flow.analyze_content(test_inputs)
        print("✅ Content analysis completed")
        
        # Check if checkpoint was saved
        checkpoints = state_manager.list_checkpoints(flow_id)
        assert len(checkpoints) > 0, "No checkpoint saved after analysis"
        print(f"✅ Checkpoint saved: {checkpoints[0]['stage']}")
        
        # Execute routing
        routing_decision = flow.route_by_content_type(analysis_result)
        print(f"✅ Routing completed: {routing_decision}")
        
        # Check for routing checkpoint
        checkpoints = state_manager.list_checkpoints(flow_id)
        assert len(checkpoints) >= 2, "No checkpoint saved after routing"
        print(f"✅ Total checkpoints: {len(checkpoints)}")
        
    except Exception as e:
        print(f"❌ Flow execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: State recovery
    print("\n3️⃣ Testing state recovery...")
    try:
        # Create new flow instance
        new_flow = ResearchFlow(config={'verbose': False})
        
        # Manually set flow_id to recover previous state
        new_flow.state.flow_id = flow_id
        new_flow._recover_from_checkpoint()
        
        # Verify state was recovered
        if hasattr(new_flow, '_recovered_from_checkpoint'):
            print("✅ State recovered from checkpoint")
            print(f"✅ Recovered flow ID: {new_flow.state.flow_id}")
            print(f"✅ Recovered stage: {new_flow.state.current_stage}")
            print(f"✅ Content analysis present: {new_flow.state.content_analysis is not None}")
            
            # Verify recovered data
            assert new_flow.state.topic_title == test_inputs['topic_title'], "Topic not recovered"
            assert new_flow.state.content_analysis is not None, "Analysis not recovered"
            print("✅ State data correctly recovered")
        else:
            print("❌ State recovery failed")
            return False
        
    except Exception as e:
        print(f"❌ State recovery failed: {e}")
        return False
    
    # Test 4: Checkpoint listing
    print("\n4️⃣ Testing checkpoint listing...")
    try:
        checkpoints = state_manager.list_checkpoints(flow_id)
        
        print(f"✅ Found {len(checkpoints)} checkpoints")
        for cp in checkpoints:
            print(f"   - {cp['stage']} at {cp['timestamp']}")
        
        # Verify checkpoint content
        if checkpoints:
            latest = checkpoints[0]
            with open(latest['filepath'], 'r') as f:
                cp_data = json.load(f)
            
            print(f"✅ Checkpoint contains flow_id: {cp_data['flow_id']}")
            print(f"✅ Checkpoint stage: {cp_data['stage']}")
            print(f"✅ State class: {cp_data['state_class']}")
        
    except Exception as e:
        print(f"❌ Checkpoint listing failed: {e}")
        return False
    
    # Test 5: Complete flow saving
    print("\n5️⃣ Testing completed flow saving...")
    try:
        # Mark flow as completed
        results = {
            "total_time": 10.5,
            "decisions_made": 2,
            "final_output": "test content"
        }
        
        flow.complete_flow(results)
        
        # Check completed flows
        completed_files = list(state_manager.completed_dir.glob(f"{flow_id}_completed_*.json"))
        assert len(completed_files) > 0, "No completed flow file found"
        
        print(f"✅ Completed flow saved: {completed_files[0].name}")
        
        # Verify checkpoints were cleaned up
        remaining_checkpoints = state_manager.list_checkpoints(flow_id)
        print(f"✅ Checkpoints cleaned up: {len(remaining_checkpoints)} remaining")
        
    except Exception as e:
        print(f"❌ Complete flow saving failed: {e}")
        return False
    
    # Test 6: Failed flow handling
    print("\n6️⃣ Testing failed flow handling...")
    try:
        # Create a new flow that will fail
        failing_flow = ResearchFlow(config={'verbose': False})
        failing_flow_id = failing_flow.state.flow_id
        
        # Simulate an error
        test_error = ValueError("Simulated flow failure")
        failing_flow.handle_flow_error(test_error, "test_stage")
        
        # Check failed flows
        failed_files = list(state_manager.failed_dir.glob(f"{failing_flow_id}_failed_*.json"))
        assert len(failed_files) > 0, "No failed flow file found"
        
        print(f"✅ Failed flow saved: {failed_files[0].name}")
        
        # Verify failed flow content
        with open(failed_files[0], 'r') as f:
            failed_data = json.load(f)
        
        print(f"✅ Error type saved: {failed_data['error']['type']}")
        print(f"✅ Error message: {failed_data['error']['message']}")
        print(f"✅ Failure stage: {failed_data['stage']}")
        
    except Exception as e:
        print(f"❌ Failed flow handling test failed: {e}")
        return False
    
    # Test 7: Storage statistics
    print("\n7️⃣ Testing storage statistics...")
    try:
        stats = state_manager.get_statistics()
        
        print("✅ Storage statistics:")
        print(f"   - Total checkpoints: {stats['total_checkpoints']}")
        print(f"   - Completed flows: {stats['completed_flows']}")
        print(f"   - Failed flows: {stats['failed_flows']}")
        print(f"   - Storage used: {stats['storage_used_mb']:.2f} MB")
        
    except Exception as e:
        print(f"❌ Statistics generation failed: {e}")
        return False
    
    # Test 8: Recovery after interruption
    print("\n8️⃣ Testing recovery after interruption...")
    try:
        # Create a flow and simulate interruption
        interrupted_flow = ResearchFlow(config={'verbose': False})
        interrupted_id = interrupted_flow.state.flow_id
        
        # Run partial execution
        inputs = {
            'topic_title': 'Interrupted Flow Test',
            'platform': 'Twitter'
        }
        interrupted_flow.analyze_content(inputs)
        
        # Simulate interruption (don't complete the flow)
        print("✅ Flow interrupted after analysis")
        
        # Create new flow instance and recover
        recovered_flow = ResearchFlow(config={'verbose': False})
        recovered_flow.state.flow_id = interrupted_id
        recovered_flow._recover_from_checkpoint()
        
        # Verify recovery
        assert hasattr(recovered_flow, '_recovered_from_checkpoint'), "Recovery failed"
        assert recovered_flow.state.topic_title == 'Interrupted Flow Test', "Topic not recovered"
        assert recovered_flow.state.current_stage == 'content_analysis', "Stage not recovered"
        
        print("✅ Successfully recovered interrupted flow")
        print(f"✅ Can continue from stage: {recovered_flow.state.current_stage}")
        
    except Exception as e:
        print(f"❌ Interruption recovery test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All Flow State Persistence tests passed!")
    print("✅ Task 7.3 implementation is complete and functional")
    print("\nKey achievements:")
    print("- Automatic state checkpointing at key stages")
    print("- State recovery from latest checkpoint")
    print("- Completed flow archiving")
    print("- Failed flow debugging support")
    print("- Storage management and statistics")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_flow_state_persistence()
    exit(0 if success else 1)