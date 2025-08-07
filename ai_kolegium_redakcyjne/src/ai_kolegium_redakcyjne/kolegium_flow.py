"""
CrewAI Flow implementation for AI Kolegium Redakcyjne with conditional logic
"""

from crewai.flow.flow import Flow, listen, start, router
try:
    from crewai.flow.flow import or_
except ImportError:
    # Fallback if or_ is not available in this version
    or_ = None
from crewai import Agent, Crew, Process, Task
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import os
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from .models import (
    TopicDiscoveryList,
    ViralAnalysisList,
    EditorialDecision,
    QualityAssessment,
    EditorialReport
)
from .tools.normalized_content_reader import create_kolegium_content_tools
from .config import load_style_guides

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EditorialState(BaseModel):
    """Shared state for editorial flow"""
    folder_path: str = ""  # Added default value
    content_type: str = "STANDALONE"  # SERIES or STANDALONE
    content_ownership: str = "EXTERNAL"  # ORIGINAL or EXTERNAL
    content_files: List[str] = []
    full_content: str = ""
    
    # Analysis results
    topics_discovered: List[Dict[str, Any]] = []
    viral_scores: Dict[str, float] = {}
    editorial_decisions: Dict[str, str] = {}
    quality_assessments: Dict[str, float] = {}
    
    # Final results
    approved_topics: List[Dict[str, Any]] = []
    rejected_topics: List[Dict[str, Any]] = []
    human_review_queue: List[Dict[str, Any]] = []
    
    # Metadata
    analysis_timestamp: str = ""
    total_processing_time: float = 0.0


class KolegiumEditorialFlow(Flow[EditorialState]):
    """Flow-based implementation of AI Kolegium Redakcyjne with conditional routing"""
    
    def __init__(self):
        super().__init__()
        self.start_time = datetime.now()
        
        # Load configurations
        self.agents_config = self._load_agents_config()
        self.tasks_config = self._load_tasks_config()
        self.style_guides = load_style_guides()
        
        # Initialize tools
        self.kolegium_tools = create_kolegium_content_tools()
    
    def _load_agents_config(self) -> Dict:
        """Load agents configuration"""
        # This would normally load from agents.yaml
        return {
            'content_scout': {
                'role': 'Content Scout',
                'goal': 'Discover trending topics and analyze content',
                'backstory': 'Expert content curator with deep knowledge of viral trends'
            },
            'trend_analyst': {
                'role': 'Trend Analyst',
                'goal': 'Analyze viral potential of content',
                'backstory': 'Data-driven analyst specializing in viral content patterns'
            },
            'editorial_strategist': {
                'role': 'Editorial Strategist',
                'goal': 'Make strategic content decisions',
                'backstory': 'Seasoned editor with expertise in content strategy'
            },
            'quality_assessor': {
                'role': 'Quality Assessor',
                'goal': 'Ensure content quality and accuracy',
                'backstory': 'Meticulous fact-checker and quality control specialist'
            },
            'style_guide_validator': {
                'role': 'Style Guide Validator',
                'goal': 'Ensure content follows brand style guide',
                'backstory': 'Brand consistency expert with attention to detail'
            }
        }
    
    def _load_tasks_config(self) -> Dict:
        """Load tasks configuration"""
        return {
            'topic_discovery': {
                'description': 'Discover and analyze content topics',
                'expected_output': 'List of discovered topics with metadata'
            },
            'viral_analysis': {
                'description': 'Analyze viral potential of content',
                'expected_output': 'Viral scores and trend analysis'
            },
            'style_validation': {
                'description': 'Validate content against style guide',
                'expected_output': 'Style guide compliance report'
            },
            'quality_check': {
                'description': 'Perform quality assessment',
                'expected_output': 'Quality scores and recommendations'
            }
        }
    
    @start()
    def analyze_content_ownership(self):
        """Initial step: Analyze content to determine type and ownership"""
        logger.info(f"🔍 Analyzing content in: {self.state.folder_path}")
        
        # Get content files from environment or default
        # For kolegium flow, we should read from RAW, not normalized
        base_raw_path = os.getenv("CONTENT_RAW_PATH", "/Users/hretheum/dev/bezrobocie/vector-wave/content/raw")
        content_dir = os.path.join(base_raw_path, self.state.folder_path)
        
        logger.info(f"📂 Looking for content in: {content_dir}")
        
        if os.path.exists(content_dir):
            files = [f for f in os.listdir(content_dir) if f.endswith('.md')]
            self.state.content_files = files
            
            # Determine content type
            if len(files) > 5 and self._has_numbering_pattern(files):
                self.state.content_type = "SERIES"
            else:
                self.state.content_type = "STANDALONE"
            
            # Read first file to check for sources
            if files:
                first_file_path = os.path.join(content_dir, files[0])
                with open(first_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.state.full_content = content
                    
                    # Check for source indicators
                    source_indicators = [
                        'źródło:', 'źródła:', 'source:', 'sources:',
                        'bibliografia:', 'references:', '[1]', '[2]',
                        'http://', 'https://', 'według ', 'za:'
                    ]
                    
                    has_sources = any(indicator in content.lower() for indicator in source_indicators)
                    self.state.content_ownership = "EXTERNAL" if has_sources else "ORIGINAL"
        
        logger.info(f"📊 Content type: {self.state.content_type}")
        logger.info(f"🏷️ Content ownership: {self.state.content_ownership}")
        
        return self.state
    
    def _has_numbering_pattern(self, files: List[str]) -> bool:
        """Check if files follow a numbering pattern"""
        pattern = re.compile(r'\d+[-_]')
        return sum(1 for f in files if pattern.match(f)) > len(files) * 0.7
    
    @router(analyze_content_ownership)
    def route_by_content_ownership(self):
        """Route to appropriate validation based on content ownership"""
        if self.state.content_ownership == "ORIGINAL":
            logger.info("➡️ Routing to ORIGINAL content validation (no source requirements)")
            return "validate_original_content"
        else:
            logger.info("➡️ Routing to EXTERNAL content validation (full source checking)")
            return "validate_external_content"
    
    @listen("validate_original_content")
    def validate_original_content(self):
        """Validation path for original content (without source verification)"""
        logger.info("🎨 Validating ORIGINAL content...")
        
        # Create agents for original content (skip source-related agents)
        agents = [
            Agent(
                config=self.agents_config['style_guide_validator'],
                tools=self.kolegium_tools,
                verbose=True
            ),
            Agent(
                config=self.agents_config['trend_analyst'],
                tools=self.kolegium_tools,
                verbose=True
            ),
            Agent(
                config=self.agents_config['editorial_strategist'],
                verbose=True
            )
        ]
        
        # Create tasks without source requirements
        tasks = [
            Task(
                description="""Analyze content style and brand consistency.
                For ORIGINAL content: Focus on voice, tone, and creativity.
                DO NOT check for external sources or citations.""",
                expected_output="Style guide compliance report focusing on brand voice",
                agent=agents[0]
            ),
            Task(
                description="Analyze viral potential and engagement metrics",
                expected_output="Viral score and trend analysis",
                agent=agents[1]
            ),
            Task(
                description="""Make editorial decision based on:
                - Brand voice consistency
                - Originality and creativity
                - Engagement potential
                NO source verification required.""",
                expected_output="Editorial decision with recommendations",
                agent=agents[2]
            )
        ]
        
        # Execute crew
        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True
        )
        
        inputs = {
            'content': self.state.full_content,
            'content_type': self.state.content_type,
            'style_guides': self.style_guides,
            'skip_source_validation': True
        }
        
        result = crew.kickoff(inputs=inputs)
        
        # Process results
        self._process_validation_results(result, "original")
        
        # Go to final report
        return self._generate_final_report()
    
    @listen("validate_external_content")
    def validate_external_content(self):
        """Full validation path for external/sourced content"""
        logger.info("📚 Validating EXTERNAL content with source verification...")
        
        # Create full agent set including source verification
        agents = [
            Agent(
                config=self.agents_config['content_scout'],
                tools=self.kolegium_tools,
                verbose=True
            ),
            Agent(
                config=self.agents_config['quality_assessor'],
                tools=self.kolegium_tools,
                verbose=True
            ),
            Agent(
                config=self.agents_config['style_guide_validator'],
                tools=self.kolegium_tools,
                verbose=True
            ),
            Agent(
                config=self.agents_config['trend_analyst'],
                tools=self.kolegium_tools,
                verbose=True
            ),
            Agent(
                config=self.agents_config['editorial_strategist'],
                verbose=True
            )
        ]
        
        # Create tasks with source requirements
        tasks = [
            Task(
                description="Find additional sources and verify existing citations",
                expected_output="List of sources with credibility assessment",
                agent=agents[0]
            ),
            Task(
                description="Verify facts and check source credibility (minimum 3 sources required)",
                expected_output="Fact-checking report with source verification",
                agent=agents[1]
            ),
            Task(
                description="""Validate style guide compliance INCLUDING:
                - Minimum 3 credible sources
                - Proper citation format
                - Fact accuracy""",
                expected_output="Complete style guide compliance report",
                agent=agents[2]
            ),
            Task(
                description="Analyze viral potential considering source credibility",
                expected_output="Viral score adjusted for content credibility",
                agent=agents[3]
            ),
            Task(
                description="Make editorial decision based on all factors including source quality",
                expected_output="Editorial decision with source-based recommendations",
                agent=agents[4]
            )
        ]
        
        # Execute crew
        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True
        )
        
        inputs = {
            'content': self.state.full_content,
            'content_type': self.state.content_type,
            'style_guides': self.style_guides,
            'require_source_validation': True,
            'min_sources': 3
        }
        
        result = crew.kickoff(inputs=inputs)
        
        # Process results
        self._process_validation_results(result, "external")
        
        # Go to final report
        return self._generate_final_report()
    
    def _generate_final_report(self):
        """Common final step: Generate editorial report"""
        logger.info("📝 Generating final editorial report...")
        
        # Calculate processing time
        self.state.total_processing_time = (datetime.now() - self.start_time).total_seconds()
        self.state.analysis_timestamp = datetime.now().isoformat()
        
        # Create final report with all required fields
        report = EditorialReport(
            executive_summary=f"Analyzed {len(self.state.topics_discovered)} topics from {self.state.folder_path}. "
                            f"Content type: {self.state.content_type}, Ownership: {self.state.content_ownership}. "
                            f"Results: {len(self.state.approved_topics)} approved, "
                            f"{len(self.state.rejected_topics)} rejected, "
                            f"{len(self.state.human_review_queue)} for human review.",
            approved_topics=self.state.approved_topics,
            rejected_topics=self.state.rejected_topics,
            human_review_queue=self.state.human_review_queue,
            content_calendar=[
                {
                    "topic_id": topic["id"],
                    "title": topic["title"],
                    "proposed_date": datetime.now().isoformat(),
                    "platform": "multi"
                } for topic in self.state.approved_topics
            ],
            resource_allocation={
                "content_team": [topic["id"] for topic in self.state.approved_topics],
                "review_team": [topic["id"] for topic in self.state.human_review_queue]
            },
            performance_predictions={
                "average_viral_score": sum(topic.get("viral_score", 0.7) for topic in self.state.approved_topics) / max(len(self.state.approved_topics), 1),
                "expected_engagement": 0.8,
                "quality_confidence": 0.85
            },
            visual_dashboard_data={
                "total_analyzed": len(self.state.topics_discovered),
                "approval_rate": len(self.state.approved_topics) / max(len(self.state.topics_discovered), 1),
                "content_ownership": self.state.content_ownership,
                "validation_path": "original" if self.state.content_ownership == "ORIGINAL" else "external"
            }
        )
        
        # Log summary
        logger.info(f"✅ Editorial review completed!")
        logger.info(f"📊 Results: {len(self.state.approved_topics)} approved, "
                   f"{len(self.state.rejected_topics)} rejected, "
                   f"{len(self.state.human_review_queue)} for human review")
        logger.info(f"⏱️ Processing time: {self.state.total_processing_time:.2f}s")
        logger.info(f"🏷️ Content ownership: {self.state.content_ownership}")
        
        return report
    
    def _process_validation_results(self, result: Any, validation_type: str):
        """Process validation results from crew execution"""
        # This is a simplified version - in reality, you'd parse the crew output
        # For now, we'll create mock results
        
        topic = {
            "id": f"topic-{datetime.now().timestamp()}",
            "title": self.state.content_files[0] if self.state.content_files else "Unknown",
            "content_preview": self.state.full_content[:200] + "...",
            "viral_score": 0.75,
            "quality_score": 0.85,
            "validation_type": validation_type,
            "content_ownership": self.state.content_ownership
        }
        
        self.state.topics_discovered.append(topic)
        
        # Make decision based on scores
        if topic["viral_score"] > 0.7 and topic["quality_score"] > 0.8:
            self.state.approved_topics.append(topic)
            self.state.editorial_decisions[topic["id"]] = "approved"
        elif topic["viral_score"] < 0.4 or topic["quality_score"] < 0.5:
            self.state.rejected_topics.append(topic)
            self.state.editorial_decisions[topic["id"]] = "rejected"
        else:
            self.state.human_review_queue.append(topic)
            self.state.editorial_decisions[topic["id"]] = "human_review"


# Factory function to create flow
def create_kolegium_flow() -> KolegiumEditorialFlow:
    """Create and return configured Kolegium Editorial Flow"""
    return KolegiumEditorialFlow()