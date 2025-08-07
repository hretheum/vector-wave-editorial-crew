"""
CrewAI Crews Module

Contains crew orchestration for content generation:
- WritingCrew: Main crew that coordinates all agents and tasks

Crews manage the execution flow and agent collaboration.
"""

from .writing_crew import WritingCrew

__all__ = [
    "WritingCrew",
]