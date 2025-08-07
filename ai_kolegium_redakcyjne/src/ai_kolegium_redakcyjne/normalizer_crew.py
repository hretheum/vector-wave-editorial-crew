from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from typing import List, Dict, Any
from datetime import datetime
import logging
import json
from pathlib import Path

from .tools import LocalContentReaderTool, ContentWriterTool

# Configure logging - reduce verbosity
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Disable memory operation logs
import os
os.environ["CREWAI_STORAGE_LOG_ENABLED"] = "false"


@CrewBase
class ContentNormalizerCrew:
    """Content Normalizer Crew for preprocessing raw content"""

    agents_config = 'config/normalizer_agents.yaml'
    tasks_config = 'config/normalizer_tasks.yaml'

    @agent
    def content_classifier(self) -> Agent:
        """Content Classifier - identifies content type and purpose"""
        return Agent(
            config=self.agents_config['content_classifier'],
            tools=[LocalContentReaderTool()],
            verbose=1,  # Reduced verbosity
            memory=True,
            max_iter=3
        )

    @agent
    def metadata_extractor(self) -> Agent:
        """Metadata Extractor - extracts key information and metrics"""
        return Agent(
            config=self.agents_config['metadata_extractor'],
            tools=[],
            verbose=1,  # Reduced verbosity
            memory=True
        )

    @agent
    def content_normalizer(self) -> Agent:
        """Content Normalizer - creates standardized format"""
        return Agent(
            config=self.agents_config['content_normalizer'],
            tools=[ContentWriterTool()],
            verbose=1,  # Reduced verbosity
            memory=True
        )

    @task
    def classify_content(self) -> Task:
        """Classify and categorize all content from raw folder"""
        return Task(
            config=self.tasks_config['classify_content'],
            output_file='content_classification.json'
        )

    @task
    def extract_metadata(self) -> Task:
        """Extract metadata and key information from each content piece"""
        return Task(
            config=self.tasks_config['extract_metadata'],
            context=[self.classify_content()],
            output_file='content_metadata.json'
        )

    @task
    def normalize_content(self) -> Task:
        """Create normalized versions of all content"""
        return Task(
            config=self.tasks_config['normalize_content'],
            context=[self.classify_content(), self.extract_metadata()],
            output_file='normalization_report.json'
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Content Normalizer crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=1,  # Reduced verbosity
            memory=True,
            max_rpm=10
        )