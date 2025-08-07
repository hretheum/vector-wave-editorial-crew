"""
CrewAI Tasks Module

Contains specialized tasks for content generation pipeline:
- ContentAnalysisTask: Analyzes input and determines strategy
- ResearchTask: Conducts research and gathers information
- WritingTask: Creates content drafts
- StyleTask: Applies style and formatting
- QualityTask: Validates quality and compliance

Each task corresponds to specific agent capabilities and pipeline stages.
"""

from .content_analysis_task import ContentAnalysisTask
from .research_task import ResearchTask
from .writing_task import WritingTask
from .style_task import StyleTask
from .quality_task import QualityTask

__all__ = [
    "ContentAnalysisTask",
    "ResearchTask",
    "WritingTask", 
    "StyleTask",
    "QualityTask",
]