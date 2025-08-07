"""
Configuration utilities for AI Kolegium Redakcyjne
"""

import os
import glob
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


def load_style_guides() -> Dict[str, str]:
    """Load all style guides from the styleguides directory"""
    style_guides = {}
    
    # Path to style guides
    styleguides_path = "/Users/hretheum/dev/bezrobocie/vector-wave/styleguides"
    
    if os.path.exists(styleguides_path):
        # Find all markdown files
        guide_files = glob.glob(os.path.join(styleguides_path, "*.md"))
        
        for guide_file in guide_files:
            try:
                with open(guide_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Use filename without extension as key
                    guide_name = os.path.basename(guide_file).replace('.md', '')
                    style_guides[guide_name] = content
                    logger.info(f"Loaded style guide: {guide_name}")
            except Exception as e:
                logger.error(f"Failed to load style guide {guide_file}: {e}")
    
    return style_guides


def get_content_folders() -> List[str]:
    """Get list of available content folders"""
    content_path = "/content/normalized"
    folders = []
    
    if os.path.exists(content_path):
        for item in os.listdir(content_path):
            if os.path.isdir(os.path.join(content_path, item)):
                folders.append(item)
    
    return sorted(folders)