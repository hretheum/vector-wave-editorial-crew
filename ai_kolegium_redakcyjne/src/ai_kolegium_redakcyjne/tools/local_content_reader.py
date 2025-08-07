"""
Local Content Reader Tool for AI Kolegium Redakcyjne
Reads and processes content from local folder structure
"""

import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool


class LocalContentReaderInput(BaseModel):
    """Input schema for LocalContentReaderTool"""
    folder_filter: Optional[str] = Field(
        default=None, 
        description="Optional specific folder name to read from (e.g. '2025-07-31-adhd-ideas-overflow'). Leave empty to read all folders."
    )


class LocalContentReaderTool(BaseTool):
    name: str = "Local Content Reader"
    description: str = (
        "Reads content from local Vector Wave content folders at /content/normalized. "
        "Reads preprocessed content with standardized metadata and classification. "
        "Returns structured data about each content piece including metadata and statistics."
    )
    args_schema: Type[BaseModel] = LocalContentReaderInput
    
    # Fixed base path as class attribute - reads from raw folder for normalization
    _base_path: Path = Path("/Users/hretheum/dev/bezrobocie/vector-wave/content/raw")
        
    def _run(self, folder_filter: Optional[str] = None) -> str:
        """
        Read all content from the specified folder
        
        Args:
            folder_filter: Optional specific folder name to read from
            
        Returns:
            JSON string with list of content items
        """
        contents = []
        
        # Get all folders or specific folder
        if folder_filter:
            folders = [self._base_path / folder_filter] if (self._base_path / folder_filter).exists() else []
        else:
            folders = [f for f in self._base_path.iterdir() if f.is_dir()]
        
        for folder in folders:
            # Process each markdown file in folder
            for md_file in folder.glob("*.md"):
                try:
                    content_data = self._process_file(md_file, folder.name)
                    contents.append(content_data)
                except Exception as e:
                    print(f"Error processing {md_file}: {e}")
                    continue
                    
        # Return as JSON string for agent consumption
        # Limit to first 5 items for now to avoid overwhelming the agent
        limited_contents = contents[:5] if len(contents) > 5 else contents
        
        result = {
            "total_files_found": len(contents),
            "files_returned": len(limited_contents),
            "content_items": limited_contents
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
    
    def _process_file(self, file_path: Path, folder_name: str) -> Dict[str, Any]:
        """Process a single markdown file"""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract title (first # heading or filename)
        title = self._extract_title(content, file_path.stem)
        
        # Count data points (numbers with context)
        data_points = self._count_data_points(content)
        
        # Get file stats
        stats = file_path.stat()
        created_date = datetime.fromtimestamp(stats.st_ctime).isoformat()
        
        # Extract any JSON metadata if present
        metadata = self._extract_metadata(content)
        
        return {
            "file_path": str(file_path),
            "folder_name": folder_name,
            "title": title,
            "content_preview": content[:500] + "..." if len(content) > 500 else content,
            "full_content": content,
            "metadata": metadata,
            "created_date": created_date,
            "file_type": file_path.suffix,
            "word_count": len(content.split()),
            "has_data_points": data_points > 0,
            "data_points_count": data_points
        }
    
    def _extract_title(self, content: str, filename: str) -> str:
        """Extract title from content or use filename"""
        lines = content.split('\n')
        for line in lines:
            if line.strip().startswith('# '):
                return line.strip()[2:]
        
        # Fallback to filename
        return filename.replace('-', ' ').replace('_', ' ').title()
    
    def _count_data_points(self, content: str) -> int:
        """Count numerical data points in content"""
        import re
        # Look for patterns like: 42%, $1000, 3.14, "increased by 200%"
        patterns = [
            r'\d+\.?\d*\s*%',  # Percentages
            r'\$\s*\d+\.?\d*[KMB]?',  # Dollar amounts
            r'\d+\.?\d*[KMB]?\s*(users?|downloads?|views?|clicks?)',  # Metrics
            r'(increased?|decreased?|grew|fell)\s+by\s+\d+\.?\d*',  # Changes
        ]
        
        total = 0
        for pattern in patterns:
            total += len(re.findall(pattern, content, re.IGNORECASE))
        
        return total
    
    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract any JSON metadata from content"""
        import re
        
        metadata = {}
        
        # Look for JSON blocks
        json_pattern = r'```json\s*(.*?)\s*```'
        json_matches = re.findall(json_pattern, content, re.DOTALL)
        
        for match in json_matches:
            try:
                data = json.loads(match)
                metadata.update(data)
            except:
                pass
        
        # Look for YAML-style metadata at the beginning
        if content.startswith('---'):
            yaml_end = content.find('---', 3)
            if yaml_end > 0:
                yaml_content = content[3:yaml_end]
                # Simple YAML parsing for key: value pairs
                for line in yaml_content.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        metadata[key.strip()] = value.strip()
        
        return metadata


class ContentAnalyzerInput(BaseModel):
    """Input schema for ContentAnalyzerTool"""
    contents_json: str = Field(
        ..., 
        description="JSON string with list of content items from LocalContentReaderTool"
    )


class ContentAnalyzerTool(BaseTool):
    name: str = "Content Analyzer"
    description: str = (
        "Analyzes local content for trends, topics, and patterns. "
        "Takes output from LocalContentReaderTool and identifies content gaps. "
        "Useful for understanding what content already exists and what's missing."
    )
    args_schema: Type[BaseModel] = ContentAnalyzerInput
    
    def _run(self, contents_json: str) -> str:
        """
        Analyze a list of content items for patterns
        
        Returns:
            JSON string with analysis results
        """
        
        # Parse the JSON input
        try:
            data = json.loads(contents_json)
            # Handle new format with content_items
            if isinstance(data, dict) and "content_items" in data:
                contents = data["content_items"]
            else:
                # Fallback to old format (direct list)
                contents = data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON input"})
        
        analysis = {
            "total_items": len(contents),
            "folders_analyzed": list(set(c["folder_name"] for c in contents)),
            "content_types": {},
            "topics_frequency": {},
            "data_rich_content": [],
            "recent_content": [],
            "content_gaps": []
        }
        
        # Analyze content types
        for content in contents:
            file_name = Path(content["file_path"]).name
            
            # Categorize by filename patterns
            if 'twitter' in file_name:
                content_type = 'twitter'
            elif 'linkedin' in file_name:
                content_type = 'linkedin'
            elif 'newsletter' in file_name:
                content_type = 'newsletter'
            elif 'technical' in file_name or 'code' in file_name:
                content_type = 'technical'
            else:
                content_type = 'other'
            
            analysis["content_types"][content_type] = analysis["content_types"].get(content_type, 0) + 1
            
            # Track data-rich content
            if content["data_points_count"] >= 3:
                analysis["data_rich_content"].append({
                    "title": content["title"],
                    "data_points": content["data_points_count"],
                    "path": content["file_path"]
                })
        
        # Sort by recency
        sorted_content = sorted(contents, key=lambda x: x["created_date"], reverse=True)
        analysis["recent_content"] = [
            {"title": c["title"], "date": c["created_date"], "folder": c["folder_name"]}
            for c in sorted_content[:5]
        ]
        
        # Identify topic patterns
        all_text = " ".join([c["full_content"].lower() for c in contents])
        
        # Key topics to track
        topics = {
            "AI/ML": ["ai", "machine learning", "llm", "gpt", "neural", "model"],
            "Automation": ["automation", "workflow", "n8n", "zapier", "make"],
            "Development": ["code", "programming", "development", "github", "api"],
            "Content Creation": ["content", "writing", "social media", "marketing"],
            "Productivity": ["productivity", "adhd", "tools", "system", "process"]
        }
        
        for topic, keywords in topics.items():
            count = sum(all_text.count(keyword) for keyword in keywords)
            if count > 0:
                analysis["topics_frequency"][topic] = count
        
        # Identify gaps (topics with low coverage)
        covered_topics = set(analysis["topics_frequency"].keys())
        all_topics = set(topics.keys())
        analysis["content_gaps"] = list(all_topics - covered_topics)
        
        # Return as JSON string
        return json.dumps(analysis, indent=2, ensure_ascii=False)


# Convenience function for CrewAI integration
def create_local_content_tools():
    """Create both reader and analyzer tools for CrewAI"""
    
    reader = LocalContentReaderTool()
    analyzer = ContentAnalyzerTool()
    
    return [reader, analyzer]