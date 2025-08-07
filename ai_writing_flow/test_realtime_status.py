#!/usr/bin/env python3
"""Test Real-time Status Updates - Task 9.2"""

import sys
import time
import asyncio

sys.path.append('src')

from ai_writing_flow.crewai_flow.flows.realtime_status_flow import (
    RealtimeStatusFlow,
    FlowStage
)
from ai_writing_flow.utils.ui_bridge_v2 import UIBridgeV2

def test_realtime_status():
    """Test real-time status update functionality"""
    
    print("🧪 Testing Real-time Status Updates - Task 9.2")
    print("=" * 60)
    
    # Test 1: Flow initialization
    print("\n1️⃣ Testing flow initialization with status tracking...")
    try:
        ui_bridge = UIBridgeV2()
        
        flow = RealtimeStatusFlow(config={
            'ui_bridge': ui_bridge
        })
        
        print("✅ RealtimeStatusFlow initialized")
        print(f"✅ Flow ID: {flow.state.flow_id}")
        print(f"✅ Update frequency: {flow.state.update_frequency_ms}ms")
        print(f"✅ Stages initialized: {len(flow.state.stages)}")
        
        # Check all stages are initialized
        for stage_name, stage_progress in flow.state.stages.items():
            assert stage_progress.status == "pending"
        print("✅ All stages initialized as pending")
        
    except Exception as e:
        print(f"❌ Flow initialization failed: {e}")
        return False
    
    # Test 2: Start with status tracking
    print("\n2️⃣ Testing flow start with status tracking...")
    try:
        inputs = {
            'topic_title': 'Real-time Status Testing',
            'platform': 'Blog'
        }
        
        start_result = flow.start_with_status_tracking(inputs)
        
        print("✅ Flow started with status tracking")
        print(f"✅ Session ID: {start_result['session_id']}")
        print(f"✅ Status tracking: {start_result['status_tracking']}")
        
        # Check initialization stage completed
        init_stage = flow.state.stages[FlowStage.INITIALIZATION.value]
        assert init_stage.status == "completed"
        assert init_stage.progress_percent == 100.0
        print("✅ Initialization stage marked as completed")
        
    except Exception as e:
        print(f"❌ Flow start test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Execute with detailed status
    print("\n3️⃣ Testing execution with detailed status updates...")
    try:
        # Execute flow (this will take a few seconds due to simulated work)
        print("   ⏳ Executing flow stages (this will take ~10 seconds)...")
        
        # Track progress updates
        initial_updates = flow.state.status_updates_sent
        
        execution_result = flow.execute_with_detailed_status(start_result)
        
        print("✅ Flow execution completed")
        print(f"✅ Success: {execution_result['success']}")
        print(f"✅ Total stages: {execution_result['total_stages']}")
        print(f"✅ Completed stages: {execution_result['completed_stages']}")
        print(f"✅ Total duration: {execution_result['total_duration']:.1f}s")
        print(f"✅ Status updates sent: {execution_result['status_updates_sent']}")
        
        # Verify multiple status updates were sent
        assert execution_result['status_updates_sent'] > initial_updates
        
    except Exception as e:
        print(f"❌ Execution test failed: {e}")
        return False
    
    # Test 4: Stage progress tracking
    print("\n4️⃣ Testing stage progress tracking...")
    try:
        # Check each stage was properly tracked
        stages_with_progress = 0
        stages_with_timing = 0
        stages_with_substeps = 0
        
        for stage_name, stage_progress in flow.state.stages.items():
            if stage_progress.status == "completed":
                stages_with_progress += 1
                
                # Check timing data
                if stage_progress.duration is not None:
                    stages_with_timing += 1
                
                # Check substeps
                if len(stage_progress.substeps) > 0:
                    stages_with_substeps += 1
        
        print(f"✅ Stages with progress: {stages_with_progress}")
        print(f"✅ Stages with timing data: {stages_with_timing}")
        print(f"✅ Stages with substeps: {stages_with_substeps}")
        
        # Verify key stages have substeps
        assert len(flow.state.stages[FlowStage.CONTENT_ANALYSIS.value].substeps) > 0
        assert len(flow.state.stages[FlowStage.RESEARCH.value].substeps) > 0
        assert len(flow.state.stages[FlowStage.DRAFT_GENERATION.value].substeps) > 0
        
    except Exception as e:
        print(f"❌ Stage tracking test failed: {e}")
        return False
    
    # Test 5: Overall progress calculation
    print("\n5️⃣ Testing overall progress calculation...")
    try:
        assert flow.state.overall_progress == 100.0
        print(f"✅ Overall progress: {flow.state.overall_progress:.1f}%")
        
        # Check estimated completion time was calculated
        assert flow.state.estimated_completion_time is not None
        print("✅ Estimated completion time calculated")
        
    except Exception as e:
        print(f"❌ Progress calculation test failed: {e}")
        return False
    
    # Test 6: Detailed status retrieval
    print("\n6️⃣ Testing detailed status retrieval...")
    try:
        detailed_status = flow.get_detailed_status()
        
        print("✅ Detailed status retrieved")
        print(f"✅ Overall progress: {detailed_status['overall_progress']}%")
        print(f"✅ Current stage: {detailed_status['current_stage']}")
        print(f"✅ Elapsed time: {detailed_status['elapsed_time']:.1f}s")
        print(f"✅ Status updates sent: {detailed_status['status_updates_sent']}")
        
        # Sample stage details
        if FlowStage.RESEARCH.value in detailed_status['stages']:
            research_stage = detailed_status['stages'][FlowStage.RESEARCH.value]
            print(f"\n   Research stage details:")
            print(f"   - Status: {research_stage['status']}")
            print(f"   - Progress: {research_stage['progress']}%")
            print(f"   - Duration: {research_stage['duration']:.1f}s")
            print(f"   - Substeps completed: {research_stage['substeps_completed']}")
        
    except Exception as e:
        print(f"❌ Detailed status test failed: {e}")
        return False
    
    # Test 7: UI Bridge integration
    print("\n7️⃣ Testing UI Bridge integration...")
    try:
        # Check session was created and updated
        session_info = ui_bridge.get_session_info(flow.state.session_id)
        assert session_info is not None
        assert len(session_info['progress_updates']) > 0
        
        print(f"✅ Session has {len(session_info['progress_updates'])} progress updates")
        
        # Check progress update structure
        if session_info['progress_updates']:
            latest_update = session_info['progress_updates'][-1]
            print(f"✅ Latest update stage: {latest_update['stage']}")
            print(f"✅ Latest update message: {latest_update['message']}")
            if 'metadata' in latest_update and latest_update['metadata']:
                print(f"✅ Update includes metadata with {len(latest_update['metadata'])} fields")
        
    except Exception as e:
        print(f"❌ UI Bridge integration test failed: {e}")
        return False
    
    # Test 8: Error handling
    print("\n8️⃣ Testing error stage handling...")
    try:
        # Create new flow that will error
        error_flow = RealtimeStatusFlow()
        
        # Manually trigger error stage
        error_flow._update_stage(
            FlowStage.ERROR,
            status="error",
            message="Test error occurred",
            progress_percent=0.0
        )
        
        error_stage = error_flow.state.stages.get(FlowStage.ERROR.value)
        assert error_stage is not None
        assert error_stage.status == "error"
        assert error_stage.message == "Test error occurred"
        
        print("✅ Error stage handling works correctly")
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All Real-time Status tests passed!")
    print("✅ Task 9.2 implementation is complete and functional")
    print("\nKey achievements:")
    print("- Real-time flow progress tracking")
    print("- Granular stage and substep monitoring")
    print("- Overall progress calculation with ETA")
    print("- Detailed status updates sent to UI")
    print("- Integration with existing UIBridge")
    print("- Comprehensive error tracking")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_realtime_status()
    exit(0 if success else 1)