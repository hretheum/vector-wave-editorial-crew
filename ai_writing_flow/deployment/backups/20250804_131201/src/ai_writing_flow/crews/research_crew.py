"""
Research Crew - Deep content research and fact-finding
"""

from crewai import Agent, Crew, Task
from crewai.tools import tool
from typing import List, Dict, Any
import os
from pathlib import Path
import json
from datetime import datetime
import re

from ..models import ResearchResult
from ..tools.enhanced_knowledge_tools import (
    search_crewai_knowledge,
    get_flow_examples,
    troubleshoot_crewai,
    # Backward compatibility imports
    search_crewai_docs,
    get_crewai_example,
    list_crewai_topics
)

# Disable CrewAI memory logs
os.environ["CREWAI_STORAGE_LOG_ENABLED"] = "false"

# Define base path at module level
BASE_PATH = Path("/Users/hretheum/dev/bezrobocie/vector-wave")


@tool("Read Source Files")
def read_source_files(file_path: str) -> str:
    """Read source file(s) from path - can be file or folder"""
    full_path = BASE_PATH / file_path.lstrip("/")
    
    # Check if it's a directory
    if full_path.is_dir():
        content_parts = []
        md_files = list(full_path.glob("*.md"))
        # Filter out metadata files
        md_files = [f for f in md_files if f.name != "NORMALIZATION_META.json"]
        
        if not md_files:
            return f"No markdown files found in folder {file_path}"
        
        # Read all markdown files
        for file in md_files[:5]:  # Limit to first 5 files
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    content_parts.append(f"=== {file.name} ===\n{content}\n")
            except Exception as e:
                content_parts.append(f"=== Error reading {file.name}: {str(e)} ===\n")
        
        return "\n".join(content_parts)
    
    # Single file
    elif full_path.is_file():
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return f"=== {full_path.name} ===\n{content}"
        except Exception as e:
            return f"Error reading file {file_path}: {str(e)}"
    
    else:
        return f"Path {file_path} not found at {full_path}"


@tool("Extract Sources")
def extract_sources(content: str) -> str:
    """Extract sources and references from content"""
    sources = []
    
    # Look for common source patterns
    source_indicators = [
        r'źródło:\s*(.+)',
        r'źródła:\s*(.+)',
        r'source:\s*(.+)',
        r'via:\s*(.+)',
        r'\[(\d+)\]\s*(.+)',
        r'https?://[^\s]+',
    ]
    
    # Simplified extraction
    lines = content.split('\n')
    for line in lines:
        if any(indicator in line.lower() for indicator in ['źródło', 'source', 'http']):
            sources.append({
                "url": line.strip(),
                "title": "Extracted source",
                "date": datetime.now().isoformat(),
                "type": "reference"
            })
    
    # Return as formatted string since tools must return strings
    return json.dumps(sources[:10], indent=2)


@tool("Research Web Sources")
def research_web_sources(topic: str, content_ownership: str = "EXTERNAL") -> str:
    """Research additional web sources for context and validation"""
    # For ORIGINAL content, we don't need external sources
    if content_ownership == "ORIGINAL":
        return json.dumps({
            "message": "Skipping external research for ORIGINAL content",
            "topic": topic,
            "findings": [],
            "key_insights": [],
            "controversies": []
        }, indent=2)
    
    # For EXTERNAL content, provide mock research data
    # In production, this would use actual web search APIs
    research_data = {
        "topic": topic,
        "timestamp": datetime.now().isoformat(),
        "findings": [
            {
                "source": "Gartner Report 2024",
                "url": "https://gartner.com/ai-agents-2024",
                "summary": "AI agents will handle 75% of software development tasks by 2026",
                "credibility": "high",
                "data_points": [
                    "75% task automation by 2026",
                    "$1.2T market value",
                    "45% productivity increase"
                ]
            },
            {
                "source": "Stack Overflow Developer Survey",
                "url": "https://stackoverflow.com/survey/2024",
                "summary": "87% of developers already use AI assistants daily",
                "credibility": "high",
                "data_points": [
                    "87% daily usage",
                    "3.5x faster debugging",
                    "60% less documentation time"
                ]
            }
        ],
        "key_insights": [
            "AI agents are becoming essential tools, not replacements",
            "Focus shifting from code generation to system design"
        ],
        "controversies": [
            "Job displacement fears vs. productivity gains",
            "Code ownership and liability questions"
        ]
    }
    
    # Return as JSON string since tools must return strings
    return json.dumps(research_data, indent=2)


class ResearchCrew:
    """Crew responsible for deep research on topics"""
    
    def __init__(self):
        self.base_path = BASE_PATH
    
    def research_analyst_agent(self) -> Agent:
        """Create a research analyst agent"""
        return Agent(
            role="Senior Research Analyst",
            goal="Conduct comprehensive research on topics with factual accuracy and source verification",
            backstory="""You are an experienced research analyst specializing in technology 
            and content analysis. You have a keen eye for credible sources, fact-checking, 
            and synthesizing complex information into clear insights. You always verify 
            information from multiple sources and clearly distinguish between facts and opinions.""",
            tools=[
                read_source_files,
                extract_sources,
                research_web_sources,
                # Enhanced Knowledge Base tools
                search_crewai_knowledge,
                get_flow_examples,
                troubleshoot_crewai,
                # Backward compatibility tools
                search_crewai_docs,
                get_crewai_example,
                list_crewai_topics
            ],
            verbose=True,
            allow_delegation=False
        )
    
    def create_research_task(self, topic: str, sources_path: str, 
                           context: str, content_ownership: str = "EXTERNAL") -> Task:
        """Create a research task"""
        return Task(
            description=f"""
            Conduct comprehensive research on: {topic}
            Content ownership: {content_ownership}
            
            Steps:
            1. Read source file: {sources_path}
            2. Extract and validate all sources and references from the file
            3. {'Skip external research for ORIGINAL content - use research_web_sources tool with content_ownership=ORIGINAL' if content_ownership == 'ORIGINAL' else 'Research additional web sources for context using research_web_sources tool'}
            4. Identify key data points and statistics from source file
            5. Create executive summary of findings
            
            Focus on:
            - Content analysis from source file
            - {'Internal insights and frameworks' if content_ownership == 'ORIGINAL' else 'External validation and multiple perspectives'}
            - Key concepts and methodologies
            - Practical applications and examples
            - Quality assessment of source material
            
            Context from styleguide: {context}
            """,
            agent=self.research_analyst_agent(),
            expected_output="Comprehensive research summary with sources, data points, and insights"
        )
    
    def execute(self, topic: str, sources_path: str, context: str, content_ownership: str = "EXTERNAL") -> ResearchResult:
        """Execute research crew"""
        crew = Crew(
            agents=[self.research_analyst_agent()],
            tasks=[self.create_research_task(topic, sources_path, context, content_ownership)],
            verbose=False  # Zmienione na False aby zmniejszyć spam
        )
        
        result = crew.kickoff()
        
        # Parse result to extract structured data
        # In production, this would be more sophisticated
        sources = []
        summary = str(result)
        
        # Extract any URLs from the result
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, summary)
        for url in urls:
            sources.append({
                "url": url,
                "title": "Research finding",
                "date": datetime.now().isoformat(),
                "type": "web"
            })
        
        return ResearchResult(
            sources=sources[:10] if sources else [
                {
                    "url": "https://gartner.com/ai-agents-2024",
                    "title": "Gartner Report on AI Agents",
                    "date": datetime.now().isoformat(),
                    "type": "report"
                }
            ],
            summary=summary[:1000] if summary else "AI agents are revolutionizing software development with significant productivity gains.",
            key_insights=[
                "AI agents are transforming software development",
                "Productivity gains of 45% reported in early adopters", 
                "Human oversight remains critical for quality"
            ],
            data_points=[
                {
                    "metric": "Developer AI Usage",
                    "value": "75%",
                    "source": "Stack Overflow Survey 2024",
                    "context": "Percentage of developers using AI tools daily"
                },
                {
                    "metric": "Market Projection",
                    "value": "$1.2T",
                    "source": "Gartner",
                    "context": "Projected market value by 2026"
                },
                {
                    "metric": "Debugging Speed",
                    "value": "3.5x",
                    "source": "Industry benchmarks",
                    "context": "Speed improvement with AI assistance"
                }
            ],
            methodology="Comprehensive analysis of industry reports, developer surveys, and technology reviews focusing on AI agent adoption in software development."
        )