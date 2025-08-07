#!/usr/bin/env python
"""
Run full content pipeline: Normalization → Editorial Review
"""

import sys
import logging
import subprocess
from datetime import datetime
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_normalizer():
    """Run the content normalizer"""
    logger.info("=" * 50)
    logger.info("🔄 PHASE 1: Content Normalization")
    logger.info("=" * 50)
    
    try:
        # Run normalizer using subprocess to ensure clean execution
        result = subprocess.run(
            [sys.executable, "run_normalizer.py"],
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info("✅ Normalization completed successfully")
        if result.stdout:
            logger.debug(f"Normalizer output:\n{result.stdout}")
            
        # Give it a moment to ensure files are written
        time.sleep(2)
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Normalization failed: {e}")
        if e.stderr:
            logger.error(f"Error output:\n{e.stderr}")
        return False


def run_kolegium():
    """Run the AI Kolegium editorial review"""
    logger.info("=" * 50)
    logger.info("📰 PHASE 2: AI Kolegium Editorial Review")
    logger.info("=" * 50)
    
    try:
        # Modify the kolegium to read from normalized folder
        # For now, we'll run the standard kolegium
        # In production, you'd modify Content Scout to read from /normalized
        
        result = subprocess.run(
            [sys.executable, "src/ai_kolegium_redakcyjne/main.py"],
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info("✅ Editorial review completed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Editorial review failed: {e}")
        if e.stderr:
            logger.error(f"Error output:\n{e.stderr}")
        return False


def main():
    """Run the full pipeline"""
    logger.info("🚀 Starting Full Content Pipeline")
    logger.info(f"Timestamp: {datetime.now()}")
    
    # Phase 1: Normalize content
    if not run_normalizer():
        logger.error("Pipeline aborted due to normalization failure")
        return False
    
    logger.info("\n⏸️  Waiting 5 seconds before starting editorial review...\n")
    time.sleep(5)
    
    # Phase 2: Run editorial review
    if not run_kolegium():
        logger.error("Pipeline completed with editorial review failure")
        return False
    
    logger.info("\n" + "=" * 50)
    logger.info("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
    logger.info("=" * 50)
    
    logger.info("\n📋 Next steps:")
    logger.info("1. Check /content/normalized for processed files")
    logger.info("2. Review editorial_report.json for content decisions")
    logger.info("3. Publish approved content via TypeFully")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)