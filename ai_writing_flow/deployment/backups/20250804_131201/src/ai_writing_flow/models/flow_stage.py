"""
Flow Stage Enum - Defines all possible stages in AI Writing Flow

This module implements the FlowStage enum with proper state transitions
to prevent circular dependencies and infinite loops.
"""

from enum import Enum
from typing import List, Dict


class FlowStage(str, Enum):
    """
    Enumeration of all possible flow stages.
    
    Each stage represents a specific phase in the AI writing process.
    Stages are designed to flow linearly without circular dependencies.
    """
    
    # Initial stage - validates input
    INPUT_VALIDATION = "input_validation"
    
    # Research phase - only for EXTERNAL content
    RESEARCH = "research"
    
    # Audience alignment - maps content to target personas
    AUDIENCE_ALIGN = "audience_align"
    
    # Content generation phase
    DRAFT_GENERATION = "draft_generation"
    
    # Style validation phase - can retry draft generation
    STYLE_VALIDATION = "style_validation"
    
    # Final quality assessment
    QUALITY_CHECK = "quality_check"
    
    # Terminal states
    FINALIZED = "finalized"
    FAILED = "failed"


# Define valid transitions to prevent circular dependencies
VALID_TRANSITIONS: Dict[FlowStage, List[FlowStage]] = {
    FlowStage.INPUT_VALIDATION: [
        FlowStage.RESEARCH,        # For EXTERNAL content
        FlowStage.AUDIENCE_ALIGN,  # For ORIGINAL content (skip research)
        FlowStage.FAILED           # On validation failure
    ],
    FlowStage.RESEARCH: [
        FlowStage.AUDIENCE_ALIGN,  # Normal flow
        FlowStage.FAILED           # On research failure
    ],
    FlowStage.AUDIENCE_ALIGN: [
        FlowStage.DRAFT_GENERATION,  # Normal flow
        FlowStage.FAILED             # On alignment failure
    ],
    FlowStage.DRAFT_GENERATION: [
        FlowStage.STYLE_VALIDATION,  # Normal flow
        FlowStage.FAILED             # On generation failure
    ],
    FlowStage.STYLE_VALIDATION: [
        FlowStage.DRAFT_GENERATION,  # Retry on style issues (limited)
        FlowStage.QUALITY_CHECK,     # Style approved
        FlowStage.FAILED             # On max retries exceeded
    ],
    FlowStage.QUALITY_CHECK: [
        FlowStage.FINALIZED,  # Quality approved
        FlowStage.FAILED      # Quality rejected
    ],
    # Terminal states have no transitions
    FlowStage.FINALIZED: [],
    FlowStage.FAILED: []
}


def is_terminal_stage(stage: FlowStage) -> bool:
    """Check if a stage is terminal (no further transitions)."""
    return stage in [FlowStage.FINALIZED, FlowStage.FAILED]


def can_transition(from_stage: FlowStage, to_stage: FlowStage) -> bool:
    """Check if transition from one stage to another is valid."""
    allowed_transitions = VALID_TRANSITIONS.get(from_stage, [])
    return to_stage in allowed_transitions


def get_allowed_transitions(stage: FlowStage) -> List[FlowStage]:
    """Get list of valid transitions from a given stage."""
    return VALID_TRANSITIONS.get(stage, [])


def get_linear_flow() -> List[FlowStage]:
    """
    Get the standard linear flow of stages (excluding terminal states).
    
    Returns:
        List of FlowStage enums in typical execution order
    """
    return [
        FlowStage.INPUT_VALIDATION,
        FlowStage.RESEARCH,
        FlowStage.AUDIENCE_ALIGN,
        FlowStage.DRAFT_GENERATION,
        FlowStage.STYLE_VALIDATION,
        FlowStage.QUALITY_CHECK,
        FlowStage.FINALIZED
    ]


def is_valid_transition(from_stage: FlowStage, to_stage: FlowStage) -> bool:
    """
    Check if transition from one stage to another is valid.
    
    This is an alias for can_transition() to match expected API.
    
    Args:
        from_stage: Current stage
        to_stage: Target stage
        
    Returns:
        True if transition is valid, False otherwise
    """
    return can_transition(from_stage, to_stage)