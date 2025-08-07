"""
Stage Execution - Tracks individual stage execution details
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from .flow_stage import FlowStage


class StageExecution(BaseModel):
    """
    Records details of a single stage execution.
    
    Tracks start/end times, success status, results, and errors
    for comprehensive monitoring and debugging.
    """
    
    stage: FlowStage
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    success: bool = False
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_id: str
    retry_attempt: int = 0
    
    def complete(
        self, 
        success: bool, 
        result: Optional[Dict[str, Any]] = None, 
        error: Optional[str] = None
    ) -> None:
        """Mark execution as complete with results."""
        self.end_time = datetime.now()
        self.success = success
        self.result = result
        self.error = error
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Get execution duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def is_complete(self) -> bool:
        """Check if execution is complete."""
        return self.end_time is not None
    
    def to_stage_result(self) -> 'StageResult':
        """Convert to StageResult for storage in FlowControlState."""
        from .flow_control_state import StageResult, StageStatus
        
        status = StageStatus.SUCCESS if self.success else StageStatus.FAILED
        if self.error and "timeout" in self.error.lower():
            status = StageStatus.TIMEOUT
        
        return StageResult(
            stage=self.stage,
            status=status,
            output=self.result,
            execution_time_seconds=self.duration_seconds or 0.0,
            retry_count=self.retry_attempt,
            error_details=self.error,
            agent_executed=self.result.get("agent") if self.result else None
        )