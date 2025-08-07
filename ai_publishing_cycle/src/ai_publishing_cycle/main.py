#!/usr/bin/env python
"""
AI Publishing Cycle Flow - Orchestrates content normalization and editorial review
"""
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field

from crewai.flow import Flow, listen, start

# Import our crews - add parent project to path
kolegium_path = Path(__file__).parents[3] / "ai_kolegium_redakcyjne/src"
sys.path.insert(0, str(kolegium_path))

try:
    from ai_kolegium_redakcyjne.normalizer_crew import ContentNormalizerCrew
    from ai_kolegium_redakcyjne.crew import AiKolegiumRedakcyjne
except ImportError as e:
    print(f"Error importing crews from: {kolegium_path}")
    print(f"Current sys.path: {sys.path[:3]}...")
    raise


class PublishingState(BaseModel):
    """State for the entire publishing pipeline"""
    # Normalization phase
    raw_content_path: str = "/Users/hretheum/dev/bezrobocie/vector-wave/content/raw"
    normalized_content_path: str = "/Users/hretheum/dev/bezrobocie/vector-wave/content/normalized"
    normalization_report: Dict[str, Any] = Field(default_factory=dict)
    normalized_files_count: int = 0
    
    # Editorial phase
    editorial_report: Dict[str, Any] = Field(default_factory=dict)
    approved_topics: List[Dict[str, Any]] = Field(default_factory=list)
    rejected_topics: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Pipeline metadata
    pipeline_start_time: str = Field(default_factory=lambda: datetime.now().isoformat())
    pipeline_status: str = "starting"
    errors: List[str] = Field(default_factory=list)


class AIPublishingFlow(Flow[PublishingState]):
    """
    Orchestrates the complete content publishing pipeline:
    1. Content Normalization - preprocesses raw content
    2. Editorial Review - AI Kolegium analyzes and decides on content
    """

    @start()
    def normalize_content(self):
        """Phase 1: Normalize raw content from various sources"""
        print("\n" + "="*60)
        print("🔄 PHASE 1: Content Normalization")
        print("="*60)
        
        self.state.pipeline_status = "normalizing"
        
        try:
            # Run normalization crew
            normalizer_crew = ContentNormalizerCrew()
            result = normalizer_crew.crew().kickoff(inputs={
                "raw_content_path": self.state.raw_content_path,
                "output_path": self.state.normalized_content_path
            })
            
            # Parse normalization report
            if hasattr(result, 'raw'):
                report_data = result.raw
                # Extract key metrics from the report
                if isinstance(report_data, str) and "files processed:" in report_data.lower():
                    # Simple parsing - in production you'd want structured output
                    self.state.normalized_files_count = len([
                        line for line in report_data.split('\n') 
                        if line.strip() and not line.startswith('#')
                    ])
                
                self.state.normalization_report = {
                    "status": "completed",
                    "timestamp": datetime.now().isoformat(),
                    "details": report_data
                }
            
            print(f"✅ Normalization completed. Files processed: {self.state.normalized_files_count}")
            
        except Exception as e:
            error_msg = f"Normalization failed: {str(e)}"
            print(f"❌ {error_msg}")
            self.state.errors.append(error_msg)
            self.state.pipeline_status = "failed"
            self.state.normalization_report = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    @listen(normalize_content)
    def editorial_review(self):
        """Phase 2: Run AI Kolegium editorial review on normalized content"""
        print("\n" + "="*60)
        print("📰 PHASE 2: AI Kolegium Editorial Review")
        print("="*60)
        
        # Skip if normalization failed
        if self.state.pipeline_status == "failed":
            print("⚠️  Skipping editorial review due to normalization failure")
            return
        
        self.state.pipeline_status = "reviewing"
        
        try:
            # Run kolegium crew
            kolegium_crew = AiKolegiumRedakcyjne()
            result = kolegium_crew.crew().kickoff(inputs={
                "date": datetime.now().strftime("%Y-%m-%d"),
                "categories": ["AI", "Technology", "Digital Culture", "Startups"],
                "normalized_content_path": self.state.normalized_content_path
            })
            
            # Parse editorial report
            if hasattr(result, 'raw'):
                report_data = result.raw
                # In production, you'd parse the structured JSON output
                self.state.editorial_report = {
                    "status": "completed",
                    "timestamp": datetime.now().isoformat(),
                    "details": report_data
                }
                
                # Extract approved/rejected topics (simplified)
                # In production, parse the actual JSON structure
                print("✅ Editorial review completed")
            
        except Exception as e:
            error_msg = f"Editorial review failed: {str(e)}"
            print(f"❌ {error_msg}")
            self.state.errors.append(error_msg)
            self.state.pipeline_status = "failed"
            self.state.editorial_report = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    @listen(editorial_review)
    def generate_pipeline_report(self):
        """Phase 3: Generate final pipeline report"""
        print("\n" + "="*60)
        print("📊 PHASE 3: Pipeline Report Generation")
        print("="*60)
        
        # Determine final status
        if self.state.errors:
            self.state.pipeline_status = "completed_with_errors"
        else:
            self.state.pipeline_status = "completed"
        
        # Generate summary report
        report = {
            "pipeline_id": f"pub_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "status": self.state.pipeline_status,
            "start_time": self.state.pipeline_start_time,
            "end_time": datetime.now().isoformat(),
            "phases": {
                "normalization": self.state.normalization_report,
                "editorial_review": self.state.editorial_report
            },
            "metrics": {
                "normalized_files": self.state.normalized_files_count,
                "approved_topics": len(self.state.approved_topics),
                "rejected_topics": len(self.state.rejected_topics)
            },
            "errors": self.state.errors
        }
        
        # Save report
        report_path = Path("pipeline_report.json")
        import json
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Pipeline report saved to: {report_path}")
        print(f"📈 Status: {self.state.pipeline_status}")
        print(f"📁 Normalized files: {self.state.normalized_files_count}")
        
        if self.state.errors:
            print("\n⚠️  Errors encountered:")
            for error in self.state.errors:
                print(f"   - {error}")


def kickoff():
    """Run the AI Publishing Flow"""
    print("🚀 Starting AI Publishing Cycle Flow")
    print(f"⏰ Timestamp: {datetime.now()}")
    
    flow = AIPublishingFlow()
    flow.kickoff()
    
    print("\n🏁 Flow execution completed!")


def plot():
    """Generate flow visualization"""
    flow = AIPublishingFlow()
    flow.plot()


if __name__ == "__main__":
    kickoff()
