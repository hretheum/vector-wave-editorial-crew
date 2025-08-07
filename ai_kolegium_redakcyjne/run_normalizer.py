#!/usr/bin/env python
"""
Run the Content Normalizer Crew to preprocess raw content
"""

import sys
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, 'src')

from ai_kolegium_redakcyjne.normalizer_crew import ContentNormalizerCrew

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_normalizer():
    """Run the content normalizer crew"""
    
    logger.info("🔄 Starting Content Normalizer...")
    logger.info(f"Processing content from: /content/raw")
    logger.info(f"Output directory: /content/normalized")
    
    inputs = {
        'source_path': '/Users/hretheum/dev/bezrobocie/vector-wave/content/raw',
        'output_path': '/Users/hretheum/dev/bezrobocie/vector-wave/content/normalized',
        'processing_date': datetime.now().strftime("%Y-%m-%d"),
    }
    
    try:
        crew = ContentNormalizerCrew()
        result = crew.crew().kickoff(inputs=inputs)
        
        logger.info("✅ Content normalization completed!")
        
        # Log summary if available
        if isinstance(result, dict):
            if 'normalized_count' in result:
                logger.info(f"📊 Normalized {result['normalized_count']} files")
            if 'processing_stats' in result:
                stats = result['processing_stats']
                logger.info(f"📈 Stats: {stats.get('total_words_processed', 0)} words, "
                          f"{stats.get('total_data_points_extracted', 0)} data points")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error during normalization: {e}")
        raise


if __name__ == "__main__":
    try:
        result = run_normalizer()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)