"""
Agents Configuration

Centralized configuration for all CrewAI agents in the writing pipeline.
Defines roles, goals, backstories, and capabilities for each agent.
"""

from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class AgentConfig:
    """Configuration for a single agent."""
    role: str
    goal: str
    backstory: str
    verbose: bool = True
    allow_delegation: bool = False
    max_iter: int = 10
    max_execution_time: int = 300

class AgentsConfig:
    """
    Configuration manager for all CrewAI agents.
    Provides standardized configuration for consistent agent behavior.
    """
    
    @staticmethod
    def get_content_analysis_config() -> AgentConfig:
        """Get configuration for Content Analysis Agent."""
        return AgentConfig(
            role="Content Analyst",
            goal="Analyze input content and determine optimal processing strategy",
            backstory=(
                "You are an expert content analyst with deep understanding of "
                "content types, audience needs, and processing requirements. "
                "You excel at breaking down complex content requirements into "
                "actionable insights and strategic recommendations."
            ),
            verbose=True,
            allow_delegation=False
        )
    
    @staticmethod
    def get_research_config() -> AgentConfig:
        """Get configuration for Research Agent."""
        return AgentConfig(
            role="Research Specialist",
            goal="Conduct comprehensive research and gather relevant information",
            backstory=(
                "You are a meticulous researcher with access to vast knowledge bases. "
                "You excel at finding relevant information, validating sources, "
                "and providing comprehensive research support for content creation."
            ),
            verbose=True,
            allow_delegation=False
        )
    
    @staticmethod
    def get_writer_config() -> AgentConfig:
        """Get configuration for Writer Agent."""
        return AgentConfig(
            role="Content Writer",
            goal="Create high-quality content drafts based on analysis and research",
            backstory=(
                "You are a skilled content writer with expertise in various formats "
                "and styles. You excel at transforming research and requirements "
                "into engaging, well-structured, and purposeful content."
            ),
            verbose=True,
            allow_delegation=False
        )
    
    @staticmethod
    def get_style_config() -> AgentConfig:
        """Get configuration for Style Agent."""
        return AgentConfig(
            role="Style Specialist",
            goal="Apply style guidelines and ensure content consistency",
            backstory=(
                "You are a style expert with keen attention to brand voice, "
                "tone consistency, and formatting standards. You excel at "
                "polishing content to meet specific style requirements."
            ),
            verbose=True,
            allow_delegation=False
        )
    
    @staticmethod
    def get_quality_config() -> AgentConfig:
        """Get configuration for Quality Agent."""
        return AgentConfig(
            role="Quality Assessor",
            goal="Validate content quality and ensure compliance with requirements",
            backstory=(
                "You are a quality assurance expert with high standards for "
                "content accuracy, readability, and compliance. You excel at "
                "identifying issues and ensuring content meets all requirements."
            ),
            verbose=True,
            allow_delegation=False
        )
    
    @classmethod
    def get_all_configs(cls) -> Dict[str, AgentConfig]:
        """Get all agent configurations."""
        return {
            'content_analysis': cls.get_content_analysis_config(),
            'research': cls.get_research_config(),
            'writer': cls.get_writer_config(),
            'style': cls.get_style_config(),
            'quality': cls.get_quality_config(),
        }