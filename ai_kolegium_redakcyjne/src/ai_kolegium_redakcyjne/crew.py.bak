from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task, before_kickoff, after_kickoff
from crewai.agents.agent_builder.base_agent import BaseAgent
# from crewai_tools import SerperDevTool, ScrapeWebsiteTool  # TODO: Fix crewai-tools version
from typing import List, Dict, Any
from datetime import datetime
import logging

from .models import (
    TopicDiscoveryList,
    ViralAnalysisList,
    EditorialDecision,
    QualityAssessment,
    EditorialReport
)
from .tools.normalized_content_reader import create_kolegium_content_tools

# Configure logging - reduce verbosity
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Disable memory operation logs
import os
os.environ["CREWAI_STORAGE_LOG_ENABLED"] = "false"

@CrewBase
class AiKolegiumRedakcyjne():
    """Vector Wave - AI Kolegium Redakcyjne crew for editorial decision making"""

    agents: List[BaseAgent]
    tasks: List[Task]

    @before_kickoff
    def prepare_crew(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare crew execution with current date and categories"""
        logger.info("🚀 Starting AI Kolegium Redakcyjne editorial pipeline...")
        
        # Add current date if not provided
        if 'current_date' not in inputs:
            inputs['current_date'] = datetime.now().strftime("%Y-%m-%d")
        
        # Default categories if not provided
        if 'categories' not in inputs:
            inputs['categories'] = ["AI", "Technology", "Digital Culture", "Startups"]
        
        return inputs

    @after_kickoff
    def process_results(self, result: Any) -> Any:
        """Process and emit AG-UI events after crew completion"""
        logger.info("✅ Editorial pipeline completed!")
        
        # TODO: Emit AG-UI event with results
        # emit_agui_event("EDITORIAL_PIPELINE_COMPLETE", result)
        
        return result

    # === AGENTS DEFINITION ===
    
    @agent
    def content_scout(self) -> Agent:
        """Content Scout - discovers trending topics"""
        # Create kolegium content tools (reads from normalized folder)
        kolegium_tools = create_kolegium_content_tools()
        
        return Agent(
            config=self.agents_config['content_scout'],
            tools=[
                *kolegium_tools,  # Normalized content reader and analyzer
                # SerperDevTool(),  # Google Search - TODO: Fix version
                # ScrapeWebsiteTool(),  # Web scraping - TODO: Fix version
                # TODO: Add custom RSS tool
                # TODO: Add social media monitoring tool
            ],
            verbose=True,
            memory=True,  # Enable memory for consistency
            max_iter=5,
            max_execution_time=300  # 5 minutes timeout
        )

    @agent
    def trend_analyst(self) -> Agent:
        """Trend Analyst - analyzes viral potential"""
        return Agent(
            config=self.agents_config['trend_analyst'],
            tools=[
                # SerperDevTool(),  # For trend research
                # TODO: Add Google Trends tool
                # TODO: Add social analytics tool
            ],
            verbose=True,
            memory=True,
            max_iter=3
        )

    @agent
    def editorial_strategist(self) -> Agent:
        """Editorial Strategist - makes content decisions"""
        return Agent(
            config=self.agents_config['editorial_strategist'],
            tools=[
                # TODO: Add controversy detector tool
                # TODO: Add brand alignment checker
            ],
            verbose=True,
            memory=True,
            allow_delegation=False,  # Critical decisions, no delegation
            human_input=False  # Disable for now for testing
        )

    @agent
    def quality_assessor(self) -> Agent:
        """Quality Assessor - fact-checking and verification"""
        return Agent(
            config=self.agents_config['quality_assessor'],
            tools=[
                # ScrapeWebsiteTool(),  # For fact-checking
                # TODO: Add fact-checking API tool
                # TODO: Add plagiarism checker
            ],
            verbose=True,
            memory=True
        )

    @agent
    def decision_coordinator(self) -> Agent:
        """Decision Coordinator - orchestrates final decisions"""
        return Agent(
            config=self.agents_config['decision_coordinator'],
            tools=[
                # TODO: Add report generator tool
                # TODO: Add consensus builder tool
            ],
            verbose=True,
            memory=True,
            allow_delegation=True,  # Can delegate to other agents
            max_iter=3
        )

    # === TASKS DEFINITION ===
    
    @task
    def topic_discovery(self) -> Task:
        """Discover trending topics across multiple sources"""
        return Task(
            config=self.tasks_config['topic_discovery'],
            output_pydantic=TopicDiscoveryList  # Use Pydantic model
        )

    @task
    def viral_analysis(self) -> Task:
        """Analyze topics for viral potential"""
        return Task(
            config=self.tasks_config['viral_analysis'],
            output_pydantic=ViralAnalysisList  # Use Pydantic model
        )

    @task
    def editorial_review(self) -> Task:
        """Review topics and make editorial decisions"""
        return Task(
            config=self.tasks_config['editorial_review'],
            output_pydantic=EditorialDecision,  # Use Pydantic model
            human_input=False  # Disable for now for testing
        )

    @task
    def quality_check(self) -> Task:
        """Perform quality assessment and fact-checking"""
        return Task(
            config=self.tasks_config['quality_check'],
            output_pydantic=QualityAssessment  # Use Pydantic model
        )

    @task
    def final_coordination(self) -> Task:
        """Coordinate all decisions and generate final report"""
        return Task(
            config=self.tasks_config['final_coordination'],
            output_pydantic=EditorialReport,  # Use Pydantic model
            output_file='editorial_report.json',
            human_input=False  # Disable for now for testing
        )

    @crew
    def crew(self) -> Crew:
        """Creates the AI Kolegium Redakcyjne editorial crew"""
        
        return Crew(
            agents=self.agents,  # All 5 agents
            tasks=self.tasks,    # All 5 tasks in sequence
            process=Process.sequential,  # Start with sequential, later upgrade to hierarchical
            verbose=2,  # 0=silent, 1=minimal, 2=normal, True=full
            memory=True,  # Enable crew-level memory
            memory_config={
                "provider": "sqlite",
                "config": {
                    "db_path": ".crew_memory.db"
                }
            },
            embedder={
                "provider": "openai",
                "config": {"model": "text-embedding-3-small"}
            },
            # TODO: Add knowledge sources
            # knowledge_sources=[
            #     TextFileKnowledgeSource("./knowledge/editorial_guidelines.txt"),
            #     TextFileKnowledgeSource("./knowledge/content_strategies.txt"),
            # ],
            max_rpm=10,  # Rate limiting
            share_crew=True  # Enable sharing between agents
        )