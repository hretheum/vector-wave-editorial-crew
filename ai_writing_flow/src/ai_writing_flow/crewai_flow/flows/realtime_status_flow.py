"""
Real-time Status Flow - Task 9.2

Implements real-time flow status updates for UI integration
with detailed progress tracking and stage visualization.
"""

import time
import asyncio
import structlog
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from pydantic import BaseModel, Field
try:
    from crewai.flow import Flow as _CrewFlow
    BaseFlow = _CrewFlow
except Exception:
    BaseFlow = object

from ...utils.ui_bridge_v2 import UIBridgeV2
from ..persistence import get_state_manager

# Configure structured logging
logger = structlog.get_logger(__name__)


class FlowStage(str, Enum):
    """Flow execution stages"""
    INITIALIZATION = "initialization"
    CONTENT_ANALYSIS = "content_analysis"
    RESEARCH = "research"
    DRAFT_GENERATION = "draft_generation"
    HUMAN_REVIEW = "human_review"
    FEEDBACK_PROCESSING = "feedback_processing"
    STYLE_VALIDATION = "style_validation"
    QUALITY_CHECK = "quality_check"
    FINALIZATION = "finalization"
    COMPLETED = "completed"
    ERROR = "error"


class StageProgress(BaseModel):
    """Progress information for a stage"""
    stage: FlowStage
    status: str = "pending"  # pending, in_progress, completed, error
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[float] = None
    progress_percent: float = 0.0
    message: str = ""
    substeps: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class RealtimeStatusState(BaseModel):
    """State for real-time status tracking"""
    
    # Flow identification
    flow_id: str = Field(default_factory=lambda: f"realtime_flow_{int(time.time())}")
    session_id: Optional[str] = None
    
    # Stage tracking
    stages: Dict[str, StageProgress] = Field(default_factory=dict)
    current_stage: Optional[FlowStage] = None
    overall_progress: float = 0.0
    
    # Update tracking
    status_updates_sent: int = 0
    update_frequency_ms: int = 500  # Update every 500ms
    last_update_time: float = 0.0
    
    # Performance metrics
    start_time: float = Field(default_factory=time.time)
    estimated_completion_time: Optional[float] = None


class RealtimeStatusFlow(BaseFlow):
    """
    Flow with real-time status updates for UI.
    
    Features:
    - Granular progress tracking per stage
    - Real-time status streaming
    - Substep tracking for complex operations
    - ETA calculation
    - Error tracking and reporting
    """
    
    # Stage weights for progress calculation
    STAGE_WEIGHTS = {
        FlowStage.INITIALIZATION: 5,
        FlowStage.CONTENT_ANALYSIS: 10,
        FlowStage.RESEARCH: 20,
        FlowStage.DRAFT_GENERATION: 25,
        FlowStage.HUMAN_REVIEW: 15,
        FlowStage.FEEDBACK_PROCESSING: 10,
        FlowStage.STYLE_VALIDATION: 5,
        FlowStage.QUALITY_CHECK: 5,
        FlowStage.FINALIZATION: 5
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Real-time Status Flow
        
        Args:
            config: Configuration including ui_bridge
        """
        super().__init__()
        # Ensure state exists without CrewAI runtime
        try:
            self.state  # type: ignore[attr-defined]
        except Exception:
            self.state = RealtimeStatusState()
        self.config = config or {}
        
        # UI Bridge for status updates
        self.ui_bridge = self.config.get('ui_bridge') or UIBridgeV2()
        
        # Initialize stages
        self._initialize_stages()
        
        # Background update task
        self.update_task = None
        
        # State manager
        self.state_manager = get_state_manager()
        
        logger.info(
            "RealtimeStatusFlow initialized",
            flow_id=self.state.flow_id,
            stages=len(self.state.stages)
        )
    
    def _initialize_stages(self):
        """Initialize all stages with pending status"""
        for stage in FlowStage:
            if stage != FlowStage.ERROR:
                self.state.stages[stage.value] = StageProgress(
                    stage=stage,
                    status="pending",
                    message=f"Waiting for {stage.value.replace('_', ' ')}"
                )
    
    def start_with_status_tracking(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start flow with real-time status tracking
        
        Args:
            inputs: Flow inputs
            
        Returns:
            Initialization result
        """
        # Start UI session
        self.state.session_id = self.ui_bridge.start_flow_session(inputs)
        
        # Start background status updates (handle both sync and async contexts)
        try:
            # Try to get current event loop
            loop = asyncio.get_running_loop()
            self.update_task = loop.create_task(self._background_status_updates())
        except RuntimeError:
            # No event loop running, create one for background task
            self.update_task = None
            logger.info("No event loop for background updates (sync mode)")
        
        # Update initialization stage
        self._update_stage(
            FlowStage.INITIALIZATION,
            status="in_progress",
            message="Initializing AI Writing Flow..."
        )
        
        # Simulate initialization work
        time.sleep(0.5)
        
        # Complete initialization
        self._update_stage(
            FlowStage.INITIALIZATION,
            status="completed",
            message="Initialization complete",
            progress_percent=100.0
        )
        
        logger.info(
            "Flow started with status tracking",
            flow_id=self.state.flow_id,
            session_id=self.state.session_id
        )
        
        return {
            "session_id": self.state.session_id,
            "status_tracking": "active",
            "update_frequency_ms": self.state.update_frequency_ms
        }
    
    def execute_with_detailed_status(self, init_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute flow with detailed status updates
        
        Returns:
            Execution result
        """
        try:
            # Stage 1: Content Analysis
            self._execute_stage_with_substeps(
                stage=FlowStage.CONTENT_ANALYSIS,
                substeps=[
                    ("Parsing input parameters", 2),
                    ("Analyzing content type", 3),
                    ("Determining complexity", 3),
                    ("Setting up workflow", 2)
                ]
            )
            
            # Stage 2: Research
            self._execute_stage_with_substeps(
                stage=FlowStage.RESEARCH,
                substeps=[
                    ("Searching knowledge base", 5),
                    ("Gathering external sources", 5),
                    ("Analyzing references", 5),
                    ("Synthesizing findings", 5)
                ]
            )
            
            # Stage 3: Draft Generation
            self._execute_stage_with_substeps(
                stage=FlowStage.DRAFT_GENERATION,
                substeps=[
                    ("Creating outline", 5),
                    ("Writing introduction", 5),
                    ("Developing main content", 10),
                    ("Crafting conclusion", 5)
                ]
            )
            
            # Stage 4: Human Review (simulated)
            self._update_stage(
                FlowStage.HUMAN_REVIEW,
                status="in_progress",
                message="Awaiting human review..."
            )
            time.sleep(2)  # Simulate review time
            self._update_stage(
                FlowStage.HUMAN_REVIEW,
                status="completed",
                message="Review completed - approved",
                progress_percent=100.0
            )
            
            # Stage 5: Style Validation
            self._execute_stage_with_substeps(
                stage=FlowStage.STYLE_VALIDATION,
                substeps=[
                    ("Checking tone consistency", 2),
                    ("Validating formatting", 2),
                    ("Ensuring platform compliance", 1)
                ]
            )
            
            # Stage 6: Quality Check
            self._execute_stage_with_substeps(
                stage=FlowStage.QUALITY_CHECK,
                substeps=[
                    ("Grammar and spelling check", 2),
                    ("Fact verification", 2),
                    ("Final review", 1)
                ]
            )
            
            # Stage 7: Finalization
            self._update_stage(
                FlowStage.FINALIZATION,
                status="in_progress",
                message="Finalizing content..."
            )
            time.sleep(0.5)
            self._update_stage(
                FlowStage.FINALIZATION,
                status="completed",
                message="Content finalized",
                progress_percent=100.0
            )
            
            # Mark as completed
            self._update_stage(
                FlowStage.COMPLETED,
                status="completed",
                message="Flow completed successfully!",
                progress_percent=100.0
            )
            
            # Force overall progress to 100%
            self.state.overall_progress = 100.0
            
            # Stop background updates
            if self.update_task:
                self.update_task.cancel()
            
            return {
                "success": True,
                "total_stages": len(self.state.stages),
                "completed_stages": sum(
                    1 for s in self.state.stages.values() 
                    if s.status == "completed"
                ),
                "total_duration": time.time() - self.state.start_time,
                "status_updates_sent": self.state.status_updates_sent
            }
            
        except Exception as e:
            logger.error(
                "Flow execution failed",
                flow_id=self.state.flow_id,
                error=str(e)
            )
            
            # Update error stage
            self._update_stage(
                FlowStage.ERROR,
                status="error",
                message=f"Error: {str(e)}",
                progress_percent=0.0
            )
            
            # Stop background updates
            if self.update_task:
                self.update_task.cancel()
            
            raise
    
    def _execute_stage_with_substeps(
        self,
        stage: FlowStage,
        substeps: List[tuple[str, float]]
    ):
        """Execute a stage with detailed substep tracking"""
        # Start stage
        self._update_stage(
            stage,
            status="in_progress",
            message=f"Starting {stage.value.replace('_', ' ')}...",
            progress_percent=0.0
        )
        
        total_weight = sum(weight for _, weight in substeps)
        completed_weight = 0.0
        
        # Execute substeps
        for substep_name, weight in substeps:
            # Update substep
            substep_progress = (completed_weight / total_weight) * 100
            self._update_stage(
                stage,
                status="in_progress",
                message=substep_name,
                progress_percent=substep_progress,
                substeps=self.state.stages[stage.value].substeps + [{
                    "name": substep_name,
                    "status": "in_progress",
                    "start_time": time.time()
                }]
            )
            
            # Simulate work
            time.sleep(weight * 0.1)  # 0.1 second per weight unit
            
            # Complete substep
            completed_weight += weight
            substep_progress = (completed_weight / total_weight) * 100
            
            # Update last substep as completed
            current_substeps = self.state.stages[stage.value].substeps
            if current_substeps:
                current_substeps[-1]["status"] = "completed"
                current_substeps[-1]["end_time"] = time.time()
        
        # Complete stage
        self._update_stage(
            stage,
            status="completed",
            message=f"{stage.value.replace('_', ' ')} completed",
            progress_percent=100.0
        )
    
    def _update_stage(
        self,
        stage: FlowStage,
        status: str,
        message: str,
        progress_percent: Optional[float] = None,
        substeps: Optional[List[Dict[str, Any]]] = None
    ):
        """Update stage progress"""
        stage_progress = self.state.stages.get(stage.value)
        if not stage_progress:
            stage_progress = StageProgress(stage=stage)
            self.state.stages[stage.value] = stage_progress
        
        # Update stage
        stage_progress.status = status
        stage_progress.message = message
        
        if progress_percent is not None:
            stage_progress.progress_percent = progress_percent
        
        if substeps is not None:
            stage_progress.substeps = substeps
        
        # Track timing
        if status == "in_progress" and not stage_progress.start_time:
            stage_progress.start_time = time.time()
        elif status in ["completed", "error"] and stage_progress.start_time:
            stage_progress.end_time = time.time()
            stage_progress.duration = stage_progress.end_time - stage_progress.start_time
        
        # Update current stage
        if status == "in_progress":
            self.state.current_stage = stage
        
        # Calculate overall progress
        self._calculate_overall_progress()
        
        # Send immediate update (handle sync context)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._send_status_update())
        except RuntimeError:
            # Run synchronously if no event loop
            asyncio.run(self._send_status_update())
    
    def _calculate_overall_progress(self):
        """Calculate overall flow progress"""
        total_weight = sum(self.STAGE_WEIGHTS.values())
        completed_weight = 0.0
        
        for stage_name, stage_progress in self.state.stages.items():
            if stage_name in self.STAGE_WEIGHTS:
                weight = self.STAGE_WEIGHTS[FlowStage(stage_name)]
                if stage_progress.status == "completed":
                    completed_weight += weight
                elif stage_progress.status == "in_progress":
                    # Partial credit for in-progress
                    completed_weight += weight * (stage_progress.progress_percent / 100.0)
        
        self.state.overall_progress = (completed_weight / total_weight) * 100.0
        
        # Estimate completion time
        if self.state.overall_progress > 0:
            elapsed = time.time() - self.state.start_time
            total_estimated = elapsed / (self.state.overall_progress / 100.0)
            self.state.estimated_completion_time = self.state.start_time + total_estimated
    
    async def _send_status_update(self):
        """Send status update to UI"""
        current_stage = self.state.stages.get(self.state.current_stage.value) if self.state.current_stage else None
        
        metadata = {
            "overall_progress": round(self.state.overall_progress, 1),
            "current_stage": self.state.current_stage.value if self.state.current_stage else None,
            "stages_status": {
                stage_name: {
                    "status": stage.status,
                    "progress": round(stage.progress_percent, 1)
                }
                for stage_name, stage in self.state.stages.items()
            },
            "estimated_completion": self.state.estimated_completion_time,
            "elapsed_time": time.time() - self.state.start_time
        }
        
        # Add current stage details
        if current_stage:
            metadata["current_stage_details"] = {
                "message": current_stage.message,
                "progress": round(current_stage.progress_percent, 1),
                "substeps_completed": sum(
                    1 for s in current_stage.substeps 
                    if s.get("status") == "completed"
                ),
                "total_substeps": len(current_stage.substeps)
            }
        
        await self.ui_bridge.stream_progress(
            stage=self.state.current_stage.value if self.state.current_stage else "waiting",
            message=current_stage.message if current_stage else "Preparing...",
            session_id=self.state.session_id,
            progress_percent=self.state.overall_progress,
            metadata=metadata
        )
        
        self.state.status_updates_sent += 1
        self.state.last_update_time = time.time()
    
    async def _background_status_updates(self):
        """Send periodic status updates"""
        while True:
            try:
                # Wait for update interval
                await asyncio.sleep(self.state.update_frequency_ms / 1000.0)
                
                # Send update if enough time has passed
                if time.time() - self.state.last_update_time > (self.state.update_frequency_ms / 1000.0):
                    await self._send_status_update()
                    
            except asyncio.CancelledError:
                logger.info("Background status updates stopped")
                break
            except Exception as e:
                logger.error(f"Background update error: {e}")
                await asyncio.sleep(1)  # Back off on error
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed status information"""
        return {
            "flow_id": self.state.flow_id,
            "session_id": self.state.session_id,
            "overall_progress": round(self.state.overall_progress, 1),
            "current_stage": self.state.current_stage.value if self.state.current_stage else None,
            "elapsed_time": time.time() - self.state.start_time,
            "estimated_remaining": (
                self.state.estimated_completion_time - time.time()
                if self.state.estimated_completion_time else None
            ),
            "stages": {
                stage_name: {
                    "status": stage.status,
                    "progress": round(stage.progress_percent, 1),
                    "duration": stage.duration,
                    "message": stage.message,
                    "substeps_completed": sum(
                        1 for s in stage.substeps 
                        if s.get("status") == "completed"
                    ),
                    "errors": stage.errors
                }
                for stage_name, stage in self.state.stages.items()
            },
            "status_updates_sent": self.state.status_updates_sent
        }