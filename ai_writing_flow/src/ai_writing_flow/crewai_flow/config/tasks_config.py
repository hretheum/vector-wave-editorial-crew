"""
Tasks Configuration

Centralized configuration for all CrewAI tasks in the writing pipeline.
Defines descriptions, expected outputs, and task relationships.
"""

from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class TaskConfig:
    """Configuration for a single task."""
    description: str
    expected_output: str
    tools: list = None
    context: list = None

class TasksConfig:
    """
    Configuration manager for all CrewAI tasks.
    Provides standardized task definitions for consistent execution.
    """
    
    @staticmethod
    def get_content_analysis_config() -> TaskConfig:
        """Get configuration for Content Analysis Task."""
        return TaskConfig(
            description=(
                "Analyze the input content requirements, target audience, "
                "and desired outcomes. Identify content type, structure needs, "
                "key topics, and processing constraints. Create a comprehensive "
                "analysis that will guide the entire content generation pipeline."
            ),
            expected_output=(
                "A detailed content analysis report including: content type, "
                "target audience characteristics, key topics to cover, "
                "structure requirements, tone and style preferences, "
                "and strategic recommendations for content generation."
            ),
            tools=[]
        )
    
    @staticmethod
    def get_research_config() -> TaskConfig:
        """Get configuration for Research Task."""
        return TaskConfig(
            description=(
                "Conduct comprehensive research based on the content analysis. "
                "Search knowledge bases, gather relevant information, validate "
                "sources, and compile research findings that will support "
                "high-quality content creation."
            ),
            expected_output=(
                "A comprehensive research report with relevant facts, statistics, "
                "examples, and supporting information organized by topic. "
                "Include source credibility assessment and key insights "
                "that will enhance content quality and accuracy."
            ),
            tools=["knowledge_search", "context_retrieval"]
        )
    
    @staticmethod
    def get_writing_config() -> TaskConfig:
        """Get configuration for Writing Task."""
        return TaskConfig(
            description=(
                "Create high-quality content draft based on the analysis and "
                "research findings. Structure the content logically, integrate "
                "research insights, and ensure the draft meets the identified "
                "requirements and audience needs."
            ),
            expected_output=(
                "A well-structured content draft that incorporates research findings, "
                "follows the recommended structure, addresses the target audience, "
                "and meets the specified requirements. Include proper formatting "
                "and logical flow throughout the content."
            ),
            tools=[],
            context=["content_analysis_task", "research_task"]
        )
    
    @staticmethod
    def get_style_config() -> TaskConfig:
        """Get configuration for Style Task."""
        return TaskConfig(
            description=(
                "Apply style guidelines and formatting to the content draft. "
                "Ensure consistency in tone, voice, and brand alignment. "
                "Polish the content for readability and presentation while "
                "maintaining the core message and structure."
            ),
            expected_output=(
                "A polished content piece with consistent style, proper formatting, "
                "aligned tone and voice, and enhanced readability. The content "
                "should maintain all key information while presenting it in "
                "an engaging and professional manner."
            ),
            tools=[],
            context=["writing_task"]
        )
    
    @staticmethod
    def get_quality_config() -> TaskConfig:
        """Get configuration for Quality Task."""
        return TaskConfig(
            description=(
                "Perform comprehensive quality assessment of the styled content. "
                "Check for accuracy, completeness, compliance with requirements, "
                "grammar and spelling, readability, and overall quality. "
                "Provide validation and any necessary recommendations."
            ),
            expected_output=(
                "A quality assessment report with overall quality score, "
                "compliance validation, identified issues (if any), and "
                "final recommendations. Include the validated final content "
                "if it passes all quality checks."
            ),
            tools=[],
            context=["style_task"]
        )
    
    @classmethod
    def get_all_configs(cls) -> Dict[str, TaskConfig]:
        """Get all task configurations."""
        return {
            'content_analysis': cls.get_content_analysis_config(),
            'research': cls.get_research_config(),
            'writing': cls.get_writing_config(),
            'style': cls.get_style_config(),
            'quality': cls.get_quality_config(),
        }