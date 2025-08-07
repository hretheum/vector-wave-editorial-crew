#!/usr/bin/env python
import sys
import warnings
from datetime import datetime
import asyncio
import logging
import os

# Import both implementations
from ai_kolegium_redakcyjne.crew import AiKolegiumRedakcyjne
from ai_kolegium_redakcyjne.kolegium_flow import create_kolegium_flow

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run():
    """
    Run the AI Kolegium Redakcyjne editorial crew.
    Now supports both Flow and Crew implementations.
    """
    # Check if we should use Flow implementation - default to false
    use_flow = os.environ.get('USE_CREWAI_FLOW', 'false').lower() == 'true'
    
    if use_flow:
        return run_flow()
    else:
        return run_crew()

def run_flow():
    """Run using CrewAI Flow implementation with conditional logic"""
    logger.info("🚀 Starting AI Kolegium Redakcyjne with FLOW implementation...")
    
    try:
        # Create flow instance
        flow = create_kolegium_flow()
        
        # Get content folders to analyze
        from ai_kolegium_redakcyjne.config import get_content_folders
        folders = get_content_folders()
        
        if not folders:
            logger.warning("No content folders found in /content/normalized")
            return None
        
        # Process first folder (or could process all)
        folder = folders[0] if folders else "2025-01-31-sample"
        logger.info(f"Processing folder: {folder}")
        
        # Run flow asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Set initial state
        flow.state.folder_path = folder
        
        # Kickoff the flow
        result = loop.run_until_complete(flow.kickoff())
        
        logger.info("✅ Flow execution completed successfully!")
        return result
        
    except Exception as e:
        logger.error(f"❌ An error occurred while running the flow: {e}")
        raise

def run_crew():
    """Run using original Crew implementation"""
    inputs = {
        'categories': ['AI', 'Technology', 'Digital Culture', 'Startups'],
        'current_date': datetime.now().strftime("%Y-%m-%d"),
        'max_topics': 10,
        'controversy_threshold': 0.7
    }
    
    logger.info("🚀 Starting AI Kolegium Redakcyjne with CREW implementation...")
    logger.info(f"Focus categories: {inputs['categories']}")
    
    try:
        result = AiKolegiumRedakcyjne().crew().kickoff(inputs=inputs)
        logger.info("✅ Editorial pipeline completed successfully!")
        
        # Log summary
        if isinstance(result, dict):
            approved = len(result.get('approved_topics', []))
            rejected = len(result.get('rejected_topics', []))
            human_review = len(result.get('human_review_queue', []))
            
            logger.info(f"📊 Results: {approved} approved, {rejected} rejected, {human_review} for human review")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ An error occurred while running the crew: {e}")
        raise

def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        'categories': ['AI', 'Technology'],
        'current_date': datetime.now().strftime("%Y-%m-%d")
    }
    
    try:
        n_iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 5
        filename = sys.argv[2] if len(sys.argv) > 2 else "training_data.json"
        
        logger.info(f"🎯 Training crew for {n_iterations} iterations...")
        AiKolegiumRedakcyjne().crew().train(
            n_iterations=n_iterations, 
            filename=filename, 
            inputs=inputs
        )
        logger.info("✅ Training completed!")

    except Exception as e:
        logger.error(f"❌ An error occurred while training the crew: {e}")
        raise

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        if len(sys.argv) < 2:
            logger.error("Please provide a task_id to replay")
            sys.exit(1)
            
        task_id = sys.argv[1]
        logger.info(f"🔄 Replaying crew from task: {task_id}")
        
        AiKolegiumRedakcyjne().crew().replay(task_id=task_id)
        logger.info("✅ Replay completed!")

    except Exception as e:
        logger.error(f"❌ An error occurred while replaying the crew: {e}")
        raise

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        'categories': ['AI', 'Technology'],
        'current_date': datetime.now().strftime("%Y-%m-%d")
    }
    
    try:
        n_iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 3
        eval_llm = sys.argv[2] if len(sys.argv) > 2 else "gpt-4"
        
        logger.info(f"🧪 Testing crew for {n_iterations} iterations...")
        results = AiKolegiumRedakcyjne().crew().test(
            n_iterations=n_iterations, 
            eval_llm=eval_llm, 
            inputs=inputs
        )
        
        logger.info("✅ Testing completed!")
        logger.info(f"📊 Test results: {results}")
        
        return results

    except Exception as e:
        logger.error(f"❌ An error occurred while testing the crew: {e}")
        raise

def run_with_server():
    """
    Run the crew with AG-UI server for real-time monitoring.
    """
    # TODO: Implement AG-UI server integration
    logger.info("🌐 Starting crew with AG-UI server...")
    logger.warning("AG-UI server integration not yet implemented")
    run()

if __name__ == "__main__":
    # Allow running with different modes
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "server":
            run_with_server()
        else:
            result = run()
            # Ensure we exit with 0 for success
            sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)