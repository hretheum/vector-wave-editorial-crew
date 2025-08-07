"""
CrewAI Flows Module

Contains flow orchestration for complex content generation workflows:
- AIWritingFlow: Main flow that integrates with existing linear flow

Flows provide high-level workflow management and integration points.
"""

from .ai_writing_flow import AIWritingFlow

__all__ = [
    "AIWritingFlow",
]