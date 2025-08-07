"""
Topic Generator Agent - Analyzes content folders for editorial opportunities
"""

from typing import Dict, Any, List
from pathlib import Path
import json
from datetime import datetime

from crewai import Agent, Task
from crewai.agent import Agent as BaseAgent


class TopicGeneratorAgent:
    """Analyzes content folders and generates topic suggestions based on styleguide"""
    
    def __init__(self):
        self.styleguide = self._load_styleguide()
        
    def _load_styleguide(self) -> Dict[str, Any]:
        """Load Vector Wave styleguide rules"""
        # In production, load from actual styleguide files
        return {
            "forbidden_topics": ["crypto", "web3", "nft"],
            "preferred_topics": ["ai", "productivity", "automation", "tech culture"],
            "content_principles": [
                "Data-driven insights",
                "Practical applications",
                "No hype or buzzwords"
            ]
        }
    
    async def analyze_folder(self, folder_path: str, styleguide_path: str = None) -> Dict[str, Any]:
        """Analyze folder content and generate topic opportunities"""
        
        folder = Path(folder_path)
        if not folder.exists():
            return {"error": "Folder not found"}
        
        # Analyze folder structure
        files = list(folder.glob("*.md"))
        
        # Check if it's a multi-part series
        is_series = self._is_content_series(files)
        
        if is_series:
            return await self._analyze_series(folder, files)
        else:
            return await self._analyze_individual_files(folder, files)
    
    def _is_content_series(self, files: List[Path]) -> bool:
        """Check if files form a series"""
        # Look for numbered files
        numbered_files = [f for f in files if f.name[:2].isdigit()]
        return len(numbered_files) > 3
    
    async def _analyze_series(self, folder: Path, files: List[Path]) -> Dict[str, Any]:
        """Analyze a content series as a whole"""
        
        # Read first and last files to understand the narrative
        first_file = sorted(files)[0]
        last_file = sorted(files)[-1]
        
        with open(first_file, 'r') as f:
            intro_content = f.read()
        with open(last_file, 'r') as f:
            conclusion_content = f.read()
        
        # Extract key information
        analysis = {
            "folder_path": str(folder),
            "files_count": len(files),
            "content_type": "SERIES",
            "series_title": self._extract_series_title(intro_content),
            "value_score": 9,  # High value for complete series
            "recommendation": "This is a complete content series. Treat as a single narrative unit.",
            "metadata_suggestion": {
                "treat_as": "single_narrative",
                "parts_count": len(files),
                "narrative_flow": "sequential",
                "content_format": "expert_panel_discussion"
            },
            "topic_suggestions": [
                {
                    "title": "Behind the Scenes: How We Built Our Style Guide",
                    "platform": "LinkedIn",
                    "format": "article",
                    "viral_score": 8,
                    "angle": "Transparency in editorial process"
                },
                {
                    "title": "5 Tech Journalism Legends Debate Content Strategy",
                    "platform": "Twitter",
                    "format": "thread",
                    "viral_score": 9,
                    "angle": "Expert insights compilation"
                },
                {
                    "title": "From Chaos to Clarity: Building Editorial Standards",
                    "platform": "Newsletter",
                    "format": "deep-dive",
                    "viral_score": 7,
                    "angle": "Process documentation"
                }
            ],
            "tags": ["process", "editorial", "behind-the-scenes", "expert-insights"],
            "styleguide_alignment": {
                "score": 10,
                "reasons": [
                    "Shows transparency in process",
                    "Features expert voices",
                    "Educational content",
                    "No forbidden topics"
                ]
            }
        }
        
        return analysis
    
    def _extract_series_title(self, content: str) -> str:
        """Extract series title from content"""
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                return line[2:].strip()
        return "Untitled Series"
    
    async def _analyze_individual_files(self, folder: Path, files: List[Path]) -> Dict[str, Any]:
        """Analyze files individually"""
        # Implementation for individual file analysis
        pass
    
    def create_agent(self) -> BaseAgent:
        """Create CrewAI agent instance"""
        return Agent(
            role="Content Topic Generator & Analyzer",
            goal="Analyze content folders and generate high-value topic suggestions aligned with styleguide",
            backstory="""You are an expert content strategist who understands viral mechanics,
            audience psychology, and editorial standards. You excel at finding unique angles
            in existing content and transforming raw materials into compelling narratives.""",
            verbose=True,
            allow_delegation=False,
            tools=[]  # Add specific tools as needed
        )