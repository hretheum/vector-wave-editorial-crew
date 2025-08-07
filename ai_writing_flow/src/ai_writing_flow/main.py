#!/usr/bin/env python
"""
AI Writing Flow - Production V2 with Full Monitoring & Quality Gates

This is the main entry point for AI Writing Flow V2, providing:
- Complete monitoring stack with real-time KPI tracking
- Multi-channel alerting system (console, webhook, email)  
- Quality gates with 5 validation rules
- Linear execution flow (eliminates infinite loops)
- Backward compatibility with Kolegium system

V2 replaces the legacy @router/@listen implementation with production-ready architecture.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel
from dotenv import load_dotenv

# Phase 4: Import V2 Production Implementation
from ai_writing_flow.ai_writing_flow_v2 import AIWritingFlowV2

# Legacy compatibility imports
from ai_writing_flow.models import WritingFlowState, HumanFeedbackDecision
from ai_writing_flow.utils.ui_bridge import UIBridge

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


# Phase 4: AIWritingFlowV2 Integration - Task 30.1
# This is the new production-ready flow class with full monitoring & quality gates
AIWritingFlowV2 = AIWritingFlowV2  # Export V2 as primary class


# Legacy compatibility wrapper - maintains backward compatibility with Kolegium
class AIWritingFlow:
    """
    Legacy compatibility wrapper for AIWritingFlow
    
    This class maintains backward compatibility with existing Kolegium integrations
    while delegating to the new AIWritingFlowV2 implementation.
    
    DEPRECATED: Use AIWritingFlowV2 directly for new implementations
    """
    
    def __init__(self, **kwargs):
        """Initialize legacy wrapper with V2 flow"""
        logger.info("🔄 Legacy AIWritingFlow wrapper - using V2 implementation")
        
        # Initialize V2 flow with production defaults
        self.flow_v2 = AIWritingFlowV2(
            monitoring_enabled=kwargs.get('monitoring_enabled', True),
            alerting_enabled=kwargs.get('alerting_enabled', True), 
            quality_gates_enabled=kwargs.get('quality_gates_enabled', True),
            storage_path=kwargs.get('storage_path', None)
        )
        
        # Legacy compatibility properties
        self.ui_bridge = UIBridge()
        self._execution_count = 0
        
        # Initialize legacy state for compatibility
        self.state = WritingFlowState()
    
    def kickoff(self, inputs: Dict[str, Any]) -> WritingFlowState:
        """
        Legacy compatibility method - delegates to V2 flow
        
        Args:
            inputs: Flow input parameters (legacy format)
            
        Returns:
            WritingFlowState: Final execution state
        """
        
        logger.info("🔄 Legacy kickoff() called - delegating to V2 flow")
        
        try:
            # Convert legacy inputs and execute V2 flow
            final_state = self.flow_v2.kickoff(inputs)
            
            # Update legacy state for compatibility
            self.state = final_state
            
            return final_state
            
        except Exception as e:
            logger.error(f"❌ Legacy flow execution failed: {e}")
            # Create failure state for compatibility
            failure_state = WritingFlowState()
            failure_state.current_stage = "failed"
            failure_state.error_message = str(e)
            self.state = failure_state
            return failure_state
    
    def plot(self, filename: str = "ai_writing_flow_diagram.png") -> None:
        """Legacy plot method - delegates to V2"""
        logger.info("🔄 Legacy plot() called - using V2 diagram")
        self.flow_v2.plot(filename)
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get dashboard metrics from V2 flow"""
        return self.flow_v2.get_dashboard_metrics()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status from V2 flow"""
        return self.flow_v2.get_health_status()
    
    def emergency_stop(self) -> None:
        """Emergency stop - delegates to V2"""
        logger.critical("🚨 Legacy emergency stop - delegating to V2")
        self.flow_v2.emergency_stop()


def kickoff():
    """
    Legacy entry point - now uses AIWritingFlowV2
    
    This function maintains backward compatibility while using the new V2 implementation
    with full monitoring, alerting, and quality gates.
    """
    
    logger.info("🚀 Legacy kickoff() - using AI Writing Flow V2")
    
    # Example inputs for V2 flow (using realistic test content)
    initial_inputs = {
        "topic_title": "AI Writing Flow V2 Production Implementation",
        "platform": "LinkedIn", 
        "file_path": "content/test-content.md",  # Would need actual file
        "content_type": "STANDALONE",
        "content_ownership": "ORIGINAL",
        "viral_score": 8.0,
        "editorial_recommendations": "Focus on V2 production features and monitoring capabilities"
    }
    
    try:
        # Create V2 flow with full monitoring stack
        flow_v2 = AIWritingFlowV2(
            monitoring_enabled=True,
            alerting_enabled=True,
            quality_gates_enabled=True
        )
        
        # Execute with V2 implementation
        final_state = flow_v2.kickoff(initial_inputs)
        
        logger.info("✅ V2 flow execution completed successfully")
        return final_state
        
    except Exception as e:
        logger.error(f"❌ V2 flow execution failed: {e}")
        raise


def plot():
    """
    Legacy plot function - now uses AIWritingFlowV2
    
    Generates architecture diagram for the new V2 implementation
    """
    
    logger.info("📊 Legacy plot() - generating V2 architecture diagram")
    
    try:
        flow_v2 = AIWritingFlowV2()
        flow_v2.plot("ai_writing_flow_v2_diagram.png")
        
        logger.info("✅ V2 architecture diagram generated")
        
    except Exception as e:
        logger.error(f"❌ Failed to generate V2 diagram: {e}")
        raise


if __name__ == "__main__":
    kickoff()
