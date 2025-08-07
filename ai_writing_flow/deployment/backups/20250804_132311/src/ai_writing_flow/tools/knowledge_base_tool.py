"""
Knowledge Base Tool for AI Writing Flow
Uses simple file-based search for CrewAI documentation
"""

import os
from pathlib import Path
from typing import List, Dict, Any
from crewai_tools import tool


@tool("search_crewai_docs")
def search_crewai_docs(query: str) -> str:
    """
    Search CrewAI documentation for relevant information.
    
    Args:
        query: Search query string
        
    Returns:
        Relevant documentation content
    """
    # Path to CrewAI docs
    docs_path = Path("/Users/hretheum/dev/bezrobocie/vector-wave/knowledge-base/data/crewai-docs/docs/en")
    
    if not docs_path.exists():
        return f"Documentation path not found: {docs_path}"
    
    results = []
    query_lower = query.lower()
    
    # Search through all MDX files
    for mdx_file in docs_path.rglob("*.mdx"):
        try:
            content = mdx_file.read_text(encoding='utf-8')
            content_lower = content.lower()
            
            # Simple keyword matching
            if query_lower in content_lower:
                # Extract relevant section
                lines = content.split('\n')
                relevant_lines = []
                
                for i, line in enumerate(lines):
                    if query_lower in line.lower():
                        # Get context: 5 lines before and after
                        start = max(0, i - 5)
                        end = min(len(lines), i + 6)
                        relevant_lines.extend(lines[start:end])
                
                if relevant_lines:
                    relative_path = mdx_file.relative_to(docs_path)
                    results.append({
                        'path': str(relative_path),
                        'content': '\n'.join(relevant_lines[:50])  # Limit to 50 lines
                    })
                
                if len(results) >= 3:  # Limit to 3 results
                    break
                    
        except Exception as e:
            continue
    
    if not results:
        return f"No results found for query: {query}"
    
    # Format results
    formatted_results = []
    for result in results:
        formatted_results.append(f"**Source: {result['path']}**\n{result['content']}")
    
    return "\n\n---\n\n".join(formatted_results)


@tool("get_crewai_example")
def get_crewai_example(topic: str) -> str:
    """
    Get specific CrewAI code examples.
    
    Args:
        topic: Topic to get examples for (e.g., "crew creation", "agent definition")
        
    Returns:
        Example code and explanation
    """
    examples = {
        "crew creation": """
```python
from crewai import Crew, Agent, Task

# Define agents
researcher = Agent(
    role='Senior Research Analyst',
    goal='Uncover cutting-edge developments',
    backstory='You are an expert researcher...',
    verbose=True
)

writer = Agent(
    role='Tech Content Writer',
    goal='Create compelling content',
    backstory='You are a renowned writer...',
    verbose=True
)

# Create crew
crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    verbose=True
)

# Execute crew
result = crew.kickoff()
```
        """,
        "agent definition": """
```python
from crewai import Agent
from crewai_tools import SerperDevTool

agent = Agent(
    role='Market Research Analyst',
    goal='Provide insights on market trends',
    backstory='Expert analyst with 10 years experience...',
    tools=[SerperDevTool()],
    verbose=True,
    allow_delegation=False,
    max_iter=5
)
```
        """,
        "task creation": """
```python
from crewai import Task

task = Task(
    description='Analyze the latest AI trends and write a report',
    expected_output='A comprehensive report on AI trends',
    agent=analyst_agent,
    tools=[search_tool, analysis_tool]
)
```
        """
    }
    
    return examples.get(topic.lower(), f"No example found for topic: {topic}")


@tool("list_crewai_topics") 
def list_crewai_topics() -> str:
    """
    List available CrewAI documentation topics.
    
    Returns:
        List of available topics in the documentation
    """
    docs_path = Path("/Users/hretheum/dev/bezrobocie/vector-wave/knowledge-base/data/crewai-docs/docs/en")
    
    if not docs_path.exists():
        return "Documentation path not found"
    
    topics = []
    
    # List main directories
    for item in docs_path.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # Count files in directory
            file_count = len(list(item.rglob("*.mdx")))
            topics.append(f"- **{item.name}** ({file_count} files)")
    
    # List root files
    root_files = [f.stem for f in docs_path.glob("*.mdx")]
    if root_files:
        topics.append(f"- **Root topics**: {', '.join(root_files)}")
    
    return "Available CrewAI documentation topics:\n" + "\n".join(topics)