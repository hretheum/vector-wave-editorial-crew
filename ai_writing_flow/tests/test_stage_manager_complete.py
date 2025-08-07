"""
Comprehensive unit tests for StageManager - Phase 3, Task 21.3

This test suite provides 100% coverage for StageManager including:
- Stage configuration and initialization
- Stage execution lifecycle
- Completion tracking and results
- Skip conditions
- History and event tracking
- Thread safety
- Timeout management
- Memory management and cleanup
- Performance analysis
- Loop detection
- Export functionality
"""

import pytest
import threading
import time
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from ai_writing_flow.managers.stage_manager import (
    StageManager, StageConfig, ExecutionEvent, ExecutionEventType
)
from ai_writing_flow.models.flow_control_state import FlowControlState, StageResult, StageStatus
from ai_writing_flow.models.flow_stage import FlowStage, get_linear_flow
from ai_writing_flow.models.stage_execution import StageExecution


class TestStageManagerInitialization:
    """Test StageManager initialization and configuration"""
    
    def test_default_initialization(self):
        """Test stage manager with default configuration"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        assert manager.flow_state == flow_state
        assert len(manager.stage_configs) == len(get_linear_flow())
        assert len(manager._execution_events) > 0  # Should have FLOW_STARTED event
        assert manager._current_execution is None
        assert len(manager._stage_executions) == 0
        
    def test_default_stage_configs(self):
        """Test default stage configurations are created"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Check each stage has a config
        for stage in get_linear_flow():
            assert stage in manager.stage_configs
            config = manager.stage_configs[stage]
            assert config.stage == stage
            assert config.required == True
            assert config.timeout_seconds == 300
            assert config.max_retries == 3
            
    def test_research_skip_condition(self):
        """Test research stage skip condition"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Research should have skip condition
        research_config = manager.stage_configs[FlowStage.RESEARCH]
        assert research_config.skip_conditions is not None
        assert len(research_config.skip_conditions) > 0
        
    def test_flow_started_event(self):
        """Test that FLOW_STARTED event is logged on initialization"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        events = manager.get_execution_events()
        assert len(events) > 0
        assert events[0].event_type == ExecutionEventType.FLOW_STARTED
        assert events[0].metadata['flow_id'] == flow_state.execution_id


class TestStageConfiguration:
    """Test stage configuration functionality"""
    
    def test_configure_stage(self):
        """Test configuring a specific stage"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        custom_config = StageConfig(
            stage=FlowStage.DRAFT_GENERATION,
            required=False,
            timeout_seconds=600,
            max_retries=5
        )
        
        manager.configure_stage(FlowStage.DRAFT_GENERATION, custom_config)
        
        assert manager.stage_configs[FlowStage.DRAFT_GENERATION] == custom_config
        assert manager.stage_configs[FlowStage.DRAFT_GENERATION].timeout_seconds == 600
        
    def test_skip_conditions(self):
        """Test stage skip conditions"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Add a custom skip condition
        def always_skip(state):
            return True
        
        config = StageConfig(
            stage=FlowStage.QUALITY_CHECK,
            skip_conditions=[always_skip]
        )
        
        assert config.should_skip(flow_state) == True
        
    def test_research_skip_with_existing_data(self):
        """Test research skip when data exists"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # The _has_existing_research method checks for existence and length
        # It expects the stage_result to convert to string with > 100 chars
        from ai_writing_flow.models.flow_control_state import StageResult, StageStatus
        
        # First test - no research result
        assert manager._has_existing_research(flow_state) == False
        
        # Add research result as StageResult object
        result = StageResult(
            stage=FlowStage.RESEARCH,
            status=StageStatus.SUCCESS,
            output={"research_data": "x" * 200},  # Long research result
            execution_time_seconds=10.0,
            retry_count=0
        )
        flow_state.stage_results[FlowStage.RESEARCH.value] = result
        
        # Now should detect existing research
        assert manager._has_existing_research(flow_state) == True
        
        # The research stage has skip_conditions that check _has_existing_research
        # So it should skip even when not completed
        assert manager.should_skip_stage(FlowStage.RESEARCH) == True  # Skips due to skip_condition
        
        # Also test when marked as completed
        flow_state.completed_stages.add(FlowStage.RESEARCH)
        assert manager.should_skip_stage(FlowStage.RESEARCH) == True  # Still skips


class TestStageExecution:
    """Test stage execution lifecycle"""
    
    def test_start_stage_success(self):
        """Test successful stage start"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        execution = manager.start_stage(FlowStage.INPUT_VALIDATION)
        
        assert execution is not None
        assert execution.stage == FlowStage.INPUT_VALIDATION
        assert execution.execution_id == flow_state.execution_id
        assert manager._current_execution == execution
        assert len(manager._stage_executions) == 1
        
    def test_start_invalid_transition(self):
        """Test starting stage with invalid transition"""
        flow_state = FlowControlState()
        flow_state.current_stage = FlowStage.INPUT_VALIDATION
        manager = StageManager(flow_state)
        
        # Try to jump to QUALITY_CHECK (invalid)
        with pytest.raises(ValueError) as exc_info:
            manager.start_stage(FlowStage.QUALITY_CHECK)
        
        assert "Cannot start stage" in str(exc_info.value)
        
    def test_start_current_stage(self):
        """Test starting the current stage (should be allowed)"""
        flow_state = FlowControlState()
        flow_state.current_stage = FlowStage.RESEARCH
        manager = StageManager(flow_state)
        
        # Should be able to start current stage
        execution = manager.start_stage(FlowStage.RESEARCH)
        assert execution.stage == FlowStage.RESEARCH
        
    def test_complete_stage_success(self):
        """Test successful stage completion"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Start and complete a stage
        execution = manager.start_stage(FlowStage.INPUT_VALIDATION)
        result = {"validated": True, "data": "test"}
        
        manager.complete_stage(
            FlowStage.INPUT_VALIDATION, 
            success=True, 
            result=result
        )
        
        assert execution.success == True
        assert execution.result == result
        assert execution.end_time is not None
        assert flow_state.is_stage_complete(FlowStage.INPUT_VALIDATION)
        
    def test_complete_stage_failure(self):
        """Test stage completion with failure"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Start and fail a stage
        execution = manager.start_stage(FlowStage.RESEARCH)
        error_msg = "API rate limit exceeded"
        
        manager.complete_stage(
            FlowStage.RESEARCH, 
            success=False, 
            error=error_msg
        )
        
        assert execution.success == False
        assert execution.error == error_msg
        assert flow_state.is_stage_complete(FlowStage.RESEARCH)  # Still marked complete
        
    def test_skip_stage_execution(self):
        """Test skipping a stage"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Mark stage as already completed
        flow_state.completed_stages.add(FlowStage.RESEARCH)
        
        execution = manager.start_stage(FlowStage.RESEARCH)
        
        assert execution.result == {'skipped': True}
        assert execution.end_time is not None
        
        # Check skip event was logged
        events = manager.get_execution_events(event_type=ExecutionEventType.STAGE_SKIPPED)
        assert len(events) > 0


class TestStageResults:
    """Test stage result management"""
    
    def test_get_stage_result(self):
        """Test retrieving stage results"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Complete a stage with result
        execution = manager.start_stage(FlowStage.INPUT_VALIDATION)
        result = {"input": "test", "validated": True}
        manager.complete_stage(FlowStage.INPUT_VALIDATION, result=result)
        
        # Retrieve result
        retrieved = manager.get_stage_result(FlowStage.INPUT_VALIDATION)
        assert retrieved.output == result
        
    def test_reset_stage(self):
        """Test resetting a stage"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Complete a stage
        execution = manager.start_stage(FlowStage.RESEARCH)
        manager.complete_stage(FlowStage.RESEARCH, result={"data": "research"})
        
        assert flow_state.is_stage_complete(FlowStage.RESEARCH)
        
        # Reset the stage
        manager.reset_stage(FlowStage.RESEARCH)
        
        assert not flow_state.is_stage_complete(FlowStage.RESEARCH)
        assert manager.get_stage_result(FlowStage.RESEARCH) is None


class TestExecutionHistory:
    """Test execution history tracking"""
    
    def test_get_execution_history(self):
        """Test retrieving execution history"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Execute multiple stages
        manager.start_stage(FlowStage.INPUT_VALIDATION)
        manager.complete_stage(FlowStage.INPUT_VALIDATION)
        
        flow_state.add_transition(FlowStage.RESEARCH, "Next stage")
        manager.start_stage(FlowStage.RESEARCH)
        manager.complete_stage(FlowStage.RESEARCH)
        
        # Get all history
        all_history = manager.get_execution_history()
        assert len(all_history) == 2
        
        # Get specific stage history
        research_history = manager.get_execution_history(FlowStage.RESEARCH)
        assert len(research_history) == 1
        assert research_history[0].stage == FlowStage.RESEARCH
        
    def test_execution_events(self):
        """Test execution event logging"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Execute a stage
        manager.start_stage(FlowStage.INPUT_VALIDATION)
        manager.complete_stage(FlowStage.INPUT_VALIDATION, success=True)
        
        # Check events
        events = manager.get_execution_events()
        
        # Should have FLOW_STARTED, STAGE_STARTED, STAGE_COMPLETED
        event_types = [e.event_type for e in events]
        assert ExecutionEventType.FLOW_STARTED in event_types
        assert ExecutionEventType.STAGE_STARTED in event_types
        assert ExecutionEventType.STAGE_COMPLETED in event_types
        
    def test_event_filtering(self):
        """Test filtering execution events"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Execute stages
        manager.start_stage(FlowStage.INPUT_VALIDATION)
        manager.complete_stage(FlowStage.INPUT_VALIDATION, success=True)
        
        flow_state.add_transition(FlowStage.RESEARCH, "Next")
        manager.start_stage(FlowStage.RESEARCH)
        manager.complete_stage(FlowStage.RESEARCH, success=False, error="Test error")
        
        # Filter by event type
        failed_events = manager.get_execution_events(
            event_type=ExecutionEventType.STAGE_FAILED
        )
        assert len(failed_events) == 1
        assert failed_events[0].stage == FlowStage.RESEARCH
        
        # Filter by stage
        research_events = manager.get_execution_events(stage=FlowStage.RESEARCH)
        assert all(e.stage == FlowStage.RESEARCH for e in research_events)


class TestMetrics:
    """Test metrics calculation"""
    
    def test_stage_metrics(self):
        """Test calculating metrics for a specific stage"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Execute stage multiple times with mixed results
        for i in range(3):
            exec = manager.start_stage(FlowStage.INPUT_VALIDATION)
            time.sleep(0.01)  # Small delay for duration
            success = i < 2  # First 2 succeed, last fails
            manager.complete_stage(FlowStage.INPUT_VALIDATION, success=success)
            flow_state.reset_stage(FlowStage.INPUT_VALIDATION)
        
        metrics = manager.get_stage_metrics(FlowStage.INPUT_VALIDATION)
        
        assert metrics['executions'] == 3
        assert metrics['successful'] == 2
        assert metrics['failed'] == 1
        assert metrics['success_rate'] == 2/3
        assert metrics['total_duration_seconds'] > 0
        assert metrics['average_duration_seconds'] > 0
        
    def test_overall_metrics(self):
        """Test overall flow metrics"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Execute multiple stages
        manager.start_stage(FlowStage.INPUT_VALIDATION)
        manager.complete_stage(FlowStage.INPUT_VALIDATION)
        
        flow_state.add_transition(FlowStage.RESEARCH, "Next")
        manager.start_stage(FlowStage.RESEARCH)
        manager.complete_stage(FlowStage.RESEARCH)
        
        metrics = manager.get_overall_metrics()
        
        assert metrics['total_executions'] == 2
        assert metrics['completed_stages'] == 2
        assert metrics['total_stages'] == len(get_linear_flow())
        assert metrics['completion_percentage'] > 0
        assert metrics['current_stage'] == FlowStage.RESEARCH.value
        assert metrics['is_completed'] == False


class TestThreadSafety:
    """Test thread safety of StageManager"""
    
    def test_concurrent_stage_execution(self):
        """Test concurrent access to stage execution"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                # Try to start the same stage
                exec = manager.start_stage(FlowStage.INPUT_VALIDATION)
                time.sleep(0.01)
                manager.complete_stage(FlowStage.INPUT_VALIDATION, 
                                     result={"worker": worker_id})
                results.append(worker_id)
            except Exception as e:
                errors.append((worker_id, str(e)))
        
        # Launch concurrent threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # At least one should succeed
        assert len(results) >= 1
        assert len(results) + len(errors) == 5
        
    def test_concurrent_event_logging(self):
        """Test concurrent event logging is thread-safe"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        def log_events(worker_id):
            for i in range(10):
                manager._log_event(
                    ExecutionEventType.STAGE_STARTED,
                    metadata={"worker": worker_id, "iteration": i}
                )
        
        threads = []
        for i in range(5):
            t = threading.Thread(target=log_events, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should have all events (1 FLOW_STARTED + 50 logged)
        events = manager.get_execution_events()
        assert len(events) == 51


class TestTimeoutManagement:
    """Test timeout management functionality"""
    
    def test_stage_timeout_configuration(self):
        """Test getting stage timeouts"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Default timeout
        assert manager.get_stage_timeout(FlowStage.RESEARCH) == 300
        
        # Custom timeout
        custom_config = StageConfig(
            stage=FlowStage.DRAFT_GENERATION,
            timeout_seconds=900
        )
        manager.configure_stage(FlowStage.DRAFT_GENERATION, custom_config)
        assert manager.get_stage_timeout(FlowStage.DRAFT_GENERATION) == 900
        
    def test_check_stage_timeout(self):
        """Test checking if stage has timed out"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Configure short timeout
        manager.configure_stage(
            FlowStage.INPUT_VALIDATION,
            StageConfig(stage=FlowStage.INPUT_VALIDATION, timeout_seconds=1)
        )
        
        # Check timeout
        start_time = datetime.now(timezone.utc)
        assert manager.check_stage_timeout(FlowStage.INPUT_VALIDATION, start_time) == False
        
        # Wait for timeout
        time.sleep(1.1)
        assert manager.check_stage_timeout(FlowStage.INPUT_VALIDATION, start_time) == True
        
    def test_flow_timeout_check(self):
        """Test checking overall flow timeout"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Initially should not be timed out
        assert manager.check_flow_timeout() == False
        
        # Mock old start time
        manager._flow_start_time = datetime.now(timezone.utc) - timedelta(hours=3)
        assert manager.check_flow_timeout() == True
        
    def test_start_stage_with_timeout(self):
        """Test starting stage with timeout monitoring"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        execution = manager.start_stage_with_timeout(FlowStage.INPUT_VALIDATION)
        
        assert execution is not None
        assert hasattr(execution, '_timeout_start')
        
    def test_complete_stage_with_timeout_check(self):
        """Test completing stage with timeout checking"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Configure very short timeout
        manager.configure_stage(
            FlowStage.INPUT_VALIDATION,
            StageConfig(stage=FlowStage.INPUT_VALIDATION, timeout_seconds=0.1)
        )
        
        # Start stage with timeout
        execution = manager.start_stage_with_timeout(FlowStage.INPUT_VALIDATION)
        
        # Wait for timeout
        time.sleep(0.2)
        
        # Complete should detect timeout
        manager.complete_stage_with_timeout_check(
            FlowStage.INPUT_VALIDATION,
            success=True,
            result={"test": "data"}
        )
        
        # Should be marked as failed due to timeout
        assert execution.success == False
        assert "timed out" in execution.error
        
    def test_force_timeout_stage(self):
        """Test forcing a stage to timeout"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Start a stage
        execution = manager.start_stage(FlowStage.RESEARCH)
        
        # Force timeout
        manager.force_timeout_stage(FlowStage.RESEARCH, "Test timeout")
        
        assert execution.success == False
        assert "Forced timeout" in execution.error
        
        # Check timeout event was logged
        events = manager.get_execution_events(event_type=ExecutionEventType.STAGE_TIMEOUT)
        assert len(events) > 0
        
    def test_timeout_status_report(self):
        """Test getting timeout status report"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Start a stage with timeout tracking
        execution = manager.start_stage_with_timeout(FlowStage.RESEARCH)
        
        status = manager.get_timeout_status()
        
        assert status['flow_timeout_status'] == 'OK'
        assert len(status['active_stages']) == 1
        assert status['active_stages'][0]['stage'] == FlowStage.RESEARCH.value
        assert status['active_stages'][0]['timeout_status'] == 'OK'


class TestMemoryManagement:
    """Test memory management and cleanup"""
    
    def test_cleanup_history(self):
        """Test cleaning up execution history"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Create many executions
        for i in range(150):
            manager._stage_executions.append(
                StageExecution(
                    stage=FlowStage.RESEARCH,
                    execution_id=f"test_{i}",
                    retry_attempt=0
                )
            )
        
        # Also add many events
        for i in range(400):
            manager._execution_events.append(
                ExecutionEvent(
                    event_type=ExecutionEventType.STAGE_STARTED,
                    stage=FlowStage.RESEARCH
                )
            )
        
        # Cleanup
        manager.cleanup_history(keep_last_n=50)
        
        assert len(manager._stage_executions) == 50
        assert len(manager._execution_events) <= 150  # 3x executions
        
    def test_cleanup_old_events(self):
        """Test cleaning up old events"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Add old events
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        for i in range(10):
            event = ExecutionEvent(
                event_type=ExecutionEventType.STAGE_STARTED,
                timestamp=old_time
            )
            manager._execution_events.append(event)
        
        # Add recent events
        for i in range(5):
            manager._log_event(ExecutionEventType.STAGE_COMPLETED)
        
        # Add milestone event (should be kept)
        milestone = ExecutionEvent(
            event_type=ExecutionEventType.FLOW_STARTED,
            timestamp=old_time
        )
        manager._execution_events.append(milestone)
        
        # Cleanup old events
        removed = manager.cleanup_old_events(max_age_hours=24)
        
        assert removed == 10  # Only non-milestone old events
        # Should have: 1 initial FLOW_STARTED + 5 recent + 1 old milestone FLOW_STARTED = 7
        assert len(manager._execution_events) == 7
        
    def test_memory_usage_report(self):
        """Test memory usage reporting"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Increase loop prevention limit for this test
        manager.loop_prevention.max_executions_per_stage = 20
        
        # Add some data
        for i in range(10):
            manager.start_stage(FlowStage.INPUT_VALIDATION)
            manager.complete_stage(FlowStage.INPUT_VALIDATION)
            flow_state.reset_stage(FlowStage.INPUT_VALIDATION)
        
        report = manager.get_memory_usage_report()
        
        assert 'total_memory_bytes' in report
        assert 'total_memory_mb' in report
        assert report['stage_executions']['count'] == 10
        assert report['execution_events']['count'] > 10  # More events than executions
        assert 'recommendations' in report


class TestPerformanceAnalysis:
    """Test performance analysis features"""
    
    def test_analyze_stage_performance(self):
        """Test analyzing performance for a specific stage"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Execute stage multiple times
        for i in range(5):
            exec = manager.start_stage(FlowStage.RESEARCH)
            time.sleep(0.01 * (i + 1))  # Variable durations
            success = i < 4  # Last one fails
            manager.complete_stage(FlowStage.RESEARCH, success=success)
            flow_state.reset_stage(FlowStage.RESEARCH)
        
        analysis = manager.analyze_stage_performance(FlowStage.RESEARCH)
        
        assert analysis['stage'] == FlowStage.RESEARCH.value
        assert analysis['total_executions'] == 5
        assert analysis['successful_executions'] == 4
        assert analysis['failed_executions'] == 1
        assert analysis['success_rate'] == 0.8
        assert analysis['average_duration_seconds'] > 0
        assert analysis['min_duration_seconds'] > 0
        assert analysis['max_duration_seconds'] > analysis['min_duration_seconds']
        
    def test_detect_execution_loops(self):
        """Test detection of execution loops"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Create a loop pattern
        for i in range(15):
            manager._log_event(
                ExecutionEventType.STAGE_STARTED,
                stage=FlowStage.DRAFT_GENERATION
            )
            time.sleep(0.01)
        
        loops = manager.detect_execution_loops(lookback_minutes=60)
        
        assert len(loops) > 0
        assert loops[0]['stage'] == FlowStage.DRAFT_GENERATION.value
        assert loops[0]['execution_count'] == 15
        assert loops[0]['risk_level'] == 'HIGH'
        
    def test_flow_health_report(self):
        """Test comprehensive flow health report"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Execute some stages
        manager.start_stage(FlowStage.INPUT_VALIDATION)
        manager.complete_stage(FlowStage.INPUT_VALIDATION, success=True)
        
        flow_state.add_transition(FlowStage.RESEARCH, "Next")
        manager.start_stage(FlowStage.RESEARCH)
        manager.complete_stage(FlowStage.RESEARCH, success=False, error="Test failure")
        
        report = manager.get_flow_health_report()
        
        assert 'health_status' in report
        assert 'warnings' in report
        assert 'total_events' in report
        assert 'event_breakdown' in report
        assert 'stage_completion_rate' in report
        assert report['stage_completion_rate'] == 0.5  # 1 success, 1 failure


class TestExportFunctionality:
    """Test export and serialization"""
    
    def test_export_execution_history(self):
        """Test exporting execution history to JSON"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Create some history
        manager.start_stage(FlowStage.INPUT_VALIDATION)
        manager.complete_stage(FlowStage.INPUT_VALIDATION)
        
        # Export to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            exported_file = manager.export_execution_history(temp_file)
            assert os.path.exists(exported_file)
            
            # Load and verify
            with open(exported_file, 'r') as f:
                data = json.load(f)
            
            assert data['flow_id'] == flow_state.execution_id
            assert data['total_events'] > 0
            assert len(data['events']) > 0
            assert 'flow_state_summary' in data
            
        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)
                
    def test_export_auto_filename(self):
        """Test export with auto-generated filename"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        manager.start_stage(FlowStage.INPUT_VALIDATION)
        
        exported_file = manager.export_execution_history()
        
        try:
            assert os.path.exists(exported_file)
            assert flow_state.execution_id in exported_file
            assert '.json' in exported_file
        finally:
            # Cleanup
            if os.path.exists(exported_file):
                os.unlink(exported_file)
                
    def test_event_serialization(self):
        """Test ExecutionEvent serialization"""
        event = ExecutionEvent(
            event_type=ExecutionEventType.STAGE_COMPLETED,
            stage=FlowStage.RESEARCH,
            execution_id="test-123",
            duration_seconds=5.5,
            metadata={"key": "value"}
        )
        
        # To dict
        event_dict = event.to_dict()
        assert event_dict['event_type'] == ExecutionEventType.STAGE_COMPLETED.value
        assert event_dict['stage'] == FlowStage.RESEARCH.value
        assert event_dict['execution_id'] == "test-123"
        
        # From dict
        restored = ExecutionEvent.from_dict(event_dict)
        assert restored.event_type == event.event_type
        assert restored.stage == event.stage
        assert restored.execution_id == event.execution_id


class TestLoopPrevention:
    """Test loop prevention integration"""
    
    def test_loop_prevention_tracking(self):
        """Test that loop prevention tracks method executions"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Execute start_stage multiple times
        for i in range(5):
            manager.start_stage(FlowStage.INPUT_VALIDATION)
            flow_state.reset_stage(FlowStage.INPUT_VALIDATION)
        
        # Loop prevention should have tracked executions
        # Just verify no error occurred during multiple executions
        assert len(manager._stage_executions) == 5
        
    def test_loop_prevention_limits(self):
        """Test loop prevention limits are enforced"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Set low limit for testing
        manager.loop_prevention.max_executions_per_method = 3
        
        # Try to execute beyond limit
        executions = []
        errors = []
        
        for i in range(5):
            try:
                exec = manager.start_stage(FlowStage.INPUT_VALIDATION)
                executions.append(exec)
                flow_state.reset_stage(FlowStage.INPUT_VALIDATION)
            except RuntimeError as e:
                errors.append(str(e))
        
        # Should have some executions blocked
        assert len(errors) > 0
        assert len(executions) == 3  # Only 3 should succeed


class TestEdgeCases:
    """Test edge cases and error scenarios"""
    
    def test_complete_without_start(self):
        """Test completing a stage that wasn't started"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Complete without starting - should not crash
        # The method finds no execution and handles gracefully
        manager.complete_stage(FlowStage.RESEARCH, success=True)
        
        # Manager should log the event even without execution
        events = manager.get_execution_events(event_type=ExecutionEventType.STAGE_COMPLETED)
        # Should have at least one completion event
        assert any(e.stage == FlowStage.RESEARCH for e in events)
        
    def test_empty_metrics(self):
        """Test metrics when no executions"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        metrics = manager.get_stage_metrics(FlowStage.RESEARCH)
        assert metrics['executions'] == 0
        # When no executions, there's no 'success_rate' key
        
    def test_get_execution_timeline(self):
        """Test getting chronological timeline"""
        flow_state = FlowControlState()
        manager = StageManager(flow_state)
        
        # Add events with delays
        for i in range(3):
            manager._log_event(ExecutionEventType.STAGE_STARTED)
            time.sleep(0.01)
        
        timeline = manager.get_execution_timeline()
        
        # Should be sorted by timestamp
        assert len(timeline) >= 3
        for i in range(1, len(timeline)):
            assert timeline[i]['timestamp'] >= timeline[i-1]['timestamp']


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])