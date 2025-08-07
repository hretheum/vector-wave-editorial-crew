"""
CrewAI Flow Integration Module

This module contains the CrewAI Flow implementation for AI Writing Flow.
Provides agents, tasks, crews, and flows for content generation pipeline.

CrewAI Version: 0.152.0
"""

__version__ = "0.1.0"
__author__ = "Vector Wave Team"

from .flows.ai_writing_flow import AIWritingFlow
from .crews.writing_crew import WritingCrew

__all__ = [
    "AIWritingFlow",
    "WritingCrew",
]