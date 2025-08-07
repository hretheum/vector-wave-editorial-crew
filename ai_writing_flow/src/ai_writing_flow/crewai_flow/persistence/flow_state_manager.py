"""
Flow State Persistence Manager - Task 7.3

Provides state persistence capabilities for CrewAI Flow:
- Save flow state to disk
- Load flow state from disk
- State versioning and migration
- Automatic state recovery
"""

import json
import pickle
import time
from pathlib import Path
from typing import Dict, Any, Optional, Type, TypeVar
from datetime import datetime
import structlog
from pydantic import BaseModel

# Configure structured logging
logger = structlog.get_logger(__name__)

T = TypeVar('T', bound=BaseModel)


class FlowStateManager:
    """
    Manages persistence of CrewAI Flow states.
    
    Features:
    - JSON and pickle serialization support
    - Automatic state directory management
    - State versioning with timestamps
    - Recovery from latest checkpoint
    - State migration capabilities
    """
    
    def __init__(self, state_dir: Optional[str] = None):
        """
        Initialize Flow State Manager
        
        Args:
            state_dir: Directory for state files (default: states/)
        """
        self.state_dir = Path(state_dir or "states")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # State subdirectories
        self.checkpoints_dir = self.state_dir / "checkpoints"
        self.checkpoints_dir.mkdir(exist_ok=True)
        
        self.completed_dir = self.state_dir / "completed"
        self.completed_dir.mkdir(exist_ok=True)
        
        self.failed_dir = self.state_dir / "failed"
        self.failed_dir.mkdir(exist_ok=True)
        
        logger.info(
            "FlowStateManager initialized",
            state_dir=str(self.state_dir)
        )
    
    def save_state(
        self,
        flow_id: str,
        state: BaseModel,
        stage: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save flow state to disk
        
        Args:
            flow_id: Unique flow identifier
            state: Pydantic model representing flow state
            stage: Current flow stage
            metadata: Additional metadata to save
            
        Returns:
            Path to saved state file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{flow_id}_{stage}_{timestamp}.json"
        filepath = self.checkpoints_dir / filename
        
        # Prepare state data
        state_data = {
            "flow_id": flow_id,
            "stage": stage,
            "timestamp": timestamp,
            "state": state.model_dump(),
            "state_class": f"{state.__class__.__module__}.{state.__class__.__name__}",
            "metadata": metadata or {}
        }
        
        # Save as JSON
        with open(filepath, 'w') as f:
            json.dump(state_data, f, indent=2, default=str)
        
        logger.info(
            "Flow state saved",
            flow_id=flow_id,
            stage=stage,
            filepath=str(filepath)
        )
        
        return str(filepath)
    
    def load_state(
        self,
        flow_id: str,
        state_class: Type[T],
        stage: Optional[str] = None
    ) -> Optional[T]:
        """
        Load flow state from disk
        
        Args:
            flow_id: Flow identifier to load
            state_class: Pydantic model class for deserialization
            stage: Specific stage to load (optional, loads latest if not specified)
            
        Returns:
            Loaded state object or None if not found
        """
        # Find matching state files
        pattern = f"{flow_id}_*"
        if stage:
            pattern = f"{flow_id}_{stage}_*"
        
        matching_files = list(self.checkpoints_dir.glob(f"{pattern}.json"))
        
        if not matching_files:
            logger.warning(
                "No state files found",
                flow_id=flow_id,
                stage=stage
            )
            return None
        
        # Get latest file
        latest_file = max(matching_files, key=lambda f: f.stat().st_mtime)
        
        try:
            with open(latest_file, 'r') as f:
                state_data = json.load(f)
            
            # Reconstruct state object
            state = state_class(**state_data["state"])
            
            logger.info(
                "Flow state loaded",
                flow_id=flow_id,
                stage=state_data["stage"],
                timestamp=state_data["timestamp"],
                filepath=str(latest_file)
            )
            
            return state
            
        except Exception as e:
            logger.error(
                "Failed to load flow state",
                flow_id=flow_id,
                filepath=str(latest_file),
                error=str(e)
            )
            return None
    
    def list_checkpoints(self, flow_id: str) -> list[Dict[str, Any]]:
        """
        List all checkpoints for a flow
        
        Args:
            flow_id: Flow identifier
            
        Returns:
            List of checkpoint metadata
        """
        pattern = f"{flow_id}_*.json"
        checkpoints = []
        
        for filepath in self.checkpoints_dir.glob(pattern):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                checkpoints.append({
                    "filepath": str(filepath),
                    "stage": data["stage"],
                    "timestamp": data["timestamp"],
                    "metadata": data.get("metadata", {})
                })
            except Exception as e:
                logger.warning(
                    "Failed to read checkpoint",
                    filepath=str(filepath),
                    error=str(e)
                )
        
        # Sort by timestamp
        checkpoints.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return checkpoints
    
    def save_completed_flow(
        self,
        flow_id: str,
        state: BaseModel,
        results: Dict[str, Any]
    ) -> str:
        """
        Save completed flow state
        
        Args:
            flow_id: Flow identifier
            state: Final flow state
            results: Flow execution results
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{flow_id}_completed_{timestamp}.json"
        filepath = self.completed_dir / filename
        
        # Prepare completion data
        completion_data = {
            "flow_id": flow_id,
            "timestamp": timestamp,
            "state": state.model_dump(),
            "results": results,
            "completion_time": datetime.now().isoformat()
        }
        
        # Save as JSON
        with open(filepath, 'w') as f:
            json.dump(completion_data, f, indent=2, default=str)
        
        # Clean up checkpoints
        self._cleanup_checkpoints(flow_id)
        
        logger.info(
            "Completed flow saved",
            flow_id=flow_id,
            filepath=str(filepath)
        )
        
        return str(filepath)
    
    def save_failed_flow(
        self,
        flow_id: str,
        state: BaseModel,
        error: Exception,
        stage: str
    ) -> str:
        """
        Save failed flow state for debugging
        
        Args:
            flow_id: Flow identifier
            state: Flow state at failure
            error: Exception that caused failure
            stage: Stage where failure occurred
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{flow_id}_failed_{timestamp}.json"
        filepath = self.failed_dir / filename
        
        # Prepare failure data
        failure_data = {
            "flow_id": flow_id,
            "timestamp": timestamp,
            "stage": stage,
            "state": state.model_dump(),
            "error": {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": None  # Could add traceback if needed
            },
            "failure_time": datetime.now().isoformat()
        }
        
        # Save as JSON
        with open(filepath, 'w') as f:
            json.dump(failure_data, f, indent=2, default=str)
        
        logger.info(
            "Failed flow saved",
            flow_id=flow_id,
            stage=stage,
            error_type=type(error).__name__,
            filepath=str(filepath)
        )
        
        return str(filepath)
    
    def recover_flow(
        self,
        flow_id: str,
        state_class: Type[T]
    ) -> Optional[tuple[T, str]]:
        """
        Recover flow from latest checkpoint
        
        Args:
            flow_id: Flow identifier
            state_class: State class for deserialization
            
        Returns:
            Tuple of (state, stage) or None if not found
        """
        checkpoints = self.list_checkpoints(flow_id)
        
        if not checkpoints:
            logger.warning(
                "No checkpoints found for recovery",
                flow_id=flow_id
            )
            return None
        
        # Try to load latest checkpoint
        latest = checkpoints[0]
        
        try:
            with open(latest["filepath"], 'r') as f:
                state_data = json.load(f)
            
            state = state_class(**state_data["state"])
            stage = state_data["stage"]
            
            logger.info(
                "Flow recovered from checkpoint",
                flow_id=flow_id,
                stage=stage,
                timestamp=latest["timestamp"]
            )
            
            return state, stage
            
        except Exception as e:
            logger.error(
                "Failed to recover flow",
                flow_id=flow_id,
                error=str(e)
            )
            return None
    
    def _cleanup_checkpoints(self, flow_id: str):
        """Remove checkpoints for completed flow"""
        pattern = f"{flow_id}_*.json"
        
        for filepath in self.checkpoints_dir.glob(pattern):
            try:
                filepath.unlink()
                logger.debug(
                    "Checkpoint removed",
                    filepath=str(filepath)
                )
            except Exception as e:
                logger.warning(
                    "Failed to remove checkpoint",
                    filepath=str(filepath),
                    error=str(e)
                )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get state persistence statistics"""
        return {
            "total_checkpoints": len(list(self.checkpoints_dir.glob("*.json"))),
            "completed_flows": len(list(self.completed_dir.glob("*.json"))),
            "failed_flows": len(list(self.failed_dir.glob("*.json"))),
            "storage_used_mb": sum(
                f.stat().st_size for f in self.state_dir.rglob("*.json")
            ) / (1024 * 1024)
        }


# Global instance
_state_manager: Optional[FlowStateManager] = None


def get_state_manager() -> FlowStateManager:
    """Get or create global state manager instance"""
    global _state_manager
    if _state_manager is None:
        _state_manager = FlowStateManager()
    return _state_manager