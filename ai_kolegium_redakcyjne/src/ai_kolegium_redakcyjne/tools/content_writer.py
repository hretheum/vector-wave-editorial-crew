"""
Content Writer Tool for saving normalized content
"""

import os
from pathlib import Path
from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from datetime import datetime
import re


class ContentWriterInput(BaseModel):
    """Input schema for ContentWriterTool"""
    file_name: str = Field(
        ..., 
        description="File name for the normalized content (without path)"
    )
    content: str = Field(
        ..., 
        description="Full content to write including YAML frontmatter"
    )


class ContentWriterTool(BaseTool):
    name: str = "Content Writer"
    description: str = (
        "Writes normalized content to /content/normalized/ folder. "
        "Ensures proper file naming and directory structure. "
        "Use for saving processed content with metadata."
    )
    args_schema: Type[BaseModel] = ContentWriterInput
    
    # Fixed output path
    _output_path: Path = Path("/Users/hretheum/dev/bezrobocie/vector-wave/content/normalized")
    
    def _run(self, file_name: str, content: str) -> str:
        """
        Write normalized content to file
        
        Returns:
            Success message with file path
        """
        
        # Ensure output directory exists
        self._output_path.mkdir(parents=True, exist_ok=True)
        
        # Sanitize filename
        safe_filename = self._sanitize_filename(file_name)
        if not safe_filename.endswith('.md'):
            safe_filename += '.md'
            
        # Full file path
        file_path = self._output_path / safe_filename
        
        try:
            # Write content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Get file stats
            file_size = file_path.stat().st_size
            
            return f"Successfully wrote {file_size} bytes to {file_path}"
            
        except Exception as e:
            return f"Error writing file: {str(e)}"
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe filesystem usage"""
        # Remove or replace unsafe characters
        safe = re.sub(r'[^\w\s\-\.]', '', filename)
        safe = re.sub(r'[\s]+', '-', safe)
        safe = safe.lower().strip('-')
        
        # Ensure it starts with date if not present
        if not re.match(r'^\d{4}-\d{2}-\d{2}', safe):
            safe = f"{datetime.now().strftime('%Y-%m-%d')}-{safe}"
            
        return safe