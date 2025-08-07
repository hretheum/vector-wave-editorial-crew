"""
Normalized Content Reader Tool for AI Kolegium Redakcyjne
Reads already normalized content from the normalized folder
"""

from pathlib import Path
from typing import Type, List
from pydantic import BaseModel

from .local_content_reader import LocalContentReaderTool, LocalContentReaderInput, ContentAnalyzerTool


class NormalizedContentReaderTool(LocalContentReaderTool):
    """Reads content from the normalized folder for editorial review"""
    
    name: str = "Normalized Content Reader"
    description: str = (
        "Reads pre-processed, normalized content from /content/normalized folder. "
        "This content has already been classified and standardized by the normalization crew. "
        "Returns structured data about each content piece including metadata and statistics."
    )
    args_schema: Type[BaseModel] = LocalContentReaderInput
    
    # Override base path to read from normalized folder
    _base_path: Path = Path("/Users/hretheum/dev/bezrobocie/vector-wave/content/normalized")


def create_kolegium_content_tools() -> List:
    """Create content tools for the AI Kolegium (reads from normalized folder)"""
    
    reader = NormalizedContentReaderTool()
    analyzer = ContentAnalyzerTool()
    
    return [reader, analyzer]