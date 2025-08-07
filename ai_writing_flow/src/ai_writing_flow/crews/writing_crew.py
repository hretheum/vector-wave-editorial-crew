"""
Writing Crew - Main crew orchestrating all writing agents
"""

from .research_crew import ResearchCrew
from .audience_crew import AudienceCrew
from .writer_crew import WriterCrew
from .style_crew import StyleCrew
from .quality_crew import QualityCrew


class WritingCrew:
    """Main crew that orchestrates all writing agents"""
    
    def __init__(self):
        self._research_crew = None
        self._audience_crew = None
        self._writer_crew = None
        self._style_crew = None
        self._quality_crew = None
    
    def research_agent(self):
        """Get or create research crew"""
        if not self._research_crew:
            self._research_crew = ResearchCrew()
        return self._research_crew
    
    def audience_mapper(self):
        """Get or create audience crew"""
        if not self._audience_crew:
            self._audience_crew = AudienceCrew()
        return self._audience_crew
    
    def content_writer(self):
        """Get or create writer crew"""
        if not self._writer_crew:
            self._writer_crew = WriterCrew()
        return self._writer_crew
    
    def style_validator(self):
        """Get or create style crew"""
        if not self._style_crew:
            self._style_crew = StyleCrew()
        return self._style_crew
    
    def quality_controller(self):
        """Get or create quality crew"""
        if not self._quality_crew:
            self._quality_crew = QualityCrew()
        return self._quality_crew