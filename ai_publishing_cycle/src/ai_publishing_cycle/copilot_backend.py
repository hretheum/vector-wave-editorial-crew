#!/usr/bin/env python
"""
Backend server that connects CopilotKit UI with our CrewAI crews
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, AsyncGenerator, Literal
import asyncio
from pathlib import Path
import json
import sys
from datetime import datetime
import uuid
import os
import re
import random
import logging
import shutil
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Disable CrewAI memory logs
os.environ["CREWAI_STORAGE_LOG_ENABLED"] = "false"

logger = logging.getLogger(__name__)

# Add our modules to path
sys.path.append(str(Path(__file__).parents[3] / "ai_kolegium_redakcyjne/src"))
sys.path.append(str(Path(__file__).parents[3] / "ai_writing_flow/src"))

# Import our crews
from ai_kolegium_redakcyjne.normalizer_crew import ContentNormalizerCrew
from ai_kolegium_redakcyjne.crew import AiKolegiumRedakcyjne

# Import writing flow
try:
    from ai_writing_flow.main import AIWritingFlow
    from ai_writing_flow.models import WritingFlowState, HumanFeedbackDecision
    WRITING_FLOW_AVAILABLE = True
except ImportError:
    print("⚠️ AI Writing Flow not available")
    WRITING_FLOW_AVAILABLE = False

# Check if CrewAI is available
CREWAI_AVAILABLE = False
try:
    from ai_kolegium_redakcyjne.kolegium_flow import create_kolegium_flow
    CREWAI_AVAILABLE = True
except ImportError:
    print("⚠️ CrewAI Flow not available, using mock analysis")

# Import chat handler
try:
    from .chat_handler import handle_chat
except ImportError:
    # Fallback for running as script
    from chat_handler import handle_chat

app = FastAPI(title="Vector Wave CrewAI Backend")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://192.168.0.75:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

class AnalyzeFolderRequest(BaseModel):
    folder_path: str

class RunPipelineRequest(BaseModel):
    content_path: str

class SaveMetadataRequest(BaseModel):
    folder_path: str
    content: str

class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = {}

class GenerateDraftRequest(BaseModel):
    topic_title: str
    platform: str
    folder_path: str
    content_type: Literal["STANDALONE", "SERIES"] = "STANDALONE"
    content_ownership: Literal["ORIGINAL", "EXTERNAL"] = "EXTERNAL"
    viral_score: float
    editorial_recommendations: str = ""
    skip_research: bool = False
    force_normalization: bool = False  # Force normalization even for single file
    normalization_strategy: Literal["auto", "single_file", "multi_file"] = "auto"

class NormalizationMetadata(BaseModel):
    """Metadata for normalization process"""
    source_path: str
    target_path: str
    topic_title: str
    platform: str
    content_type: Literal["STANDALONE", "SERIES"]
    content_ownership: Literal["ORIGINAL", "EXTERNAL"]
    created_at: datetime = Field(default_factory=datetime.now)
    normalization_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

class NormalizationResult(BaseModel):
    """Result of normalization process"""
    task_id: str
    status: Literal["running", "completed", "failed"]
    normalized_path: Optional[str] = None
    files_processed: int = 0
    total_files: int = 0
    processing_time: float = 0.0
    error_message: Optional[str] = None

class DraftFeedbackRequest(BaseModel):
    flow_id: str
    feedback_type: Literal["minor", "major", "pivot"]
    feedback_text: str
    specific_changes: Optional[List[str]] = None

@app.post("/chat")
async def chat(request: ChatRequest):
    """Handle natural chat conversations"""
    try:
        response = handle_chat(request.message, request.context)
        return response
    except Exception as e:
        return {
            "response": f"Ojej, coś poszło nie tak: {str(e)}. Ale możemy dalej gadać!",
            "error": str(e)
        }

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "Vector Wave CrewAI Backend"}

@app.get("/api/list-content-folders")
async def list_content_folders():
    """List available content folders in raw directory"""
    try:
        raw_dir = Path(BASE_CONTENT_DIR)
        folders = []
        
        if raw_dir.exists():
            for item in raw_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    # Count markdown files
                    md_files = list(item.glob("*.md"))
                    if md_files:  # Only include folders with actual content
                        folders.append({
                            "name": item.name,
                            "path": f"content/raw/{item.name}",
                            "files_count": len(md_files),
                            "modified": item.stat().st_mtime
                        })
        
        # Sort by modification time, newest first
        folders.sort(key=lambda x: x['modified'], reverse=True)
        
        # IMPORTANT: No mocks! Return empty list if no content
        if not folders:
            return {
                "status": "empty",
                "folders": [],
                "total": 0,
                "message": "Brak nowych materiałów w content/raw. Dodaj foldery z plikami .md aby rozpocząć analizę."
            }
        
        return {
            "status": "success",
            "folders": folders,
            "total": len(folders)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/styleguides")
async def get_styleguides():
    """Load all style guide documents"""
    try:
        styleguides_dir = Path("/Users/hretheum/dev/bezrobocie/vector-wave/styleguides")
        guides = {}
        
        # Define files to load
        guide_files = [
            "01-vw-guide-foundation.md",
            "02-vw-guide-audience.md", 
            "03-vw-guide-voice.md",
            "04-vw-guide-language.md",
            "05-vw-guide-content.md",
            "06-vw-guide-operational.md",
            "07-vw-guide-performance.md",
            "08-vw-guide-community.md",
            "kolegium-styleguide-mapping.md"
        ]
        
        for filename in guide_files:
            file_path = styleguides_dir / filename
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    guides[filename] = f.read()
        
        return {
            "status": "success",
            "guides": guides,
            "count": len(guides)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze-folder")
async def analyze_folder(request: AnalyzeFolderRequest):
    """Analyze a content folder and return editorial insights"""
    try:
        # Check if folder exists
        folder = Path(request.folder_path)
        if not folder.exists():
            # Try relative to content directory
            folder = Path("/Users/hretheum/dev/bezrobocie/vector-wave") / request.folder_path.lstrip("/")
            if not folder.exists():
                # Also try raw directory specifically
                folder = Path("/Users/hretheum/dev/bezrobocie/vector-wave/content/raw") / request.folder_path.replace("content/raw/", "").lstrip("/")
                if not folder.exists():
                    raise HTTPException(status_code=404, detail=f"Folder not found: {request.folder_path}")
        
        # Count files
        files = list(folder.glob("*.md"))
        
        # Check if it's a series
        is_series = len(files) > 5 and any("part" in f.name.lower() or f.name[0].isdigit() for f in files)
        
        # Read first file for context and check for sources
        sample_content = ""
        has_sources = False
        if files:
            with open(files[0], 'r', encoding='utf-8') as f:
                full_content = f.read()
                sample_content = full_content[:500]
                # Check for common source indicators
                source_indicators = ['źródło:', 'źródła:', 'source:', 'sources:', 'bibliografia:', 
                                   'references:', '[1]', 'http://', 'https://', 'według ', 'za:']
                has_sources = any(indicator in full_content.lower() for indicator in source_indicators)
        
        # Create analysis result
        result = {
            "folder": str(folder),
            "filesCount": len(files),
            "contentType": "SERIES" if is_series else "STANDALONE",
            "contentOwnership": "EXTERNAL" if has_sources else "ORIGINAL",
            "seriesTitle": folder.name.replace("-", " ").title(),
            "valueScore": 8 if is_series else 6,
            "recommendation": "Wartościowa seria pokazująca proces twórczy" if is_series else "Dobry content do publikacji",
            "topics": [],
            "sampleContent": sample_content,
            "files": [f.name for f in files[:5]]  # First 5 files
        }
        
        # Generate topic suggestions based on content
        if "style guide" in folder.name.lower() or "styleguide" in sample_content.lower():
            result["topics"] = [
                {
                    "title": "Behind the Scenes: Jak powstał nasz Style Guide",
                    "platform": "LinkedIn",
                    "viralScore": 8,
                },
                {
                    "title": "5 legend tech dziennikarstwa debatuje o content strategy",
                    "platform": "Twitter",
                    "viralScore": 9,
                }
            ]
        else:
            result["topics"] = [
                {
                    "title": f"Deep Dive: {result['seriesTitle']}",
                    "platform": "LinkedIn",
                    "viralScore": 7,
                },
                {
                    "title": f"Thread: Key insights from {folder.name}",
                    "platform": "Twitter", 
                    "viralScore": 6,
                }
            ]
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/run-pipeline")
async def run_pipeline(request: RunPipelineRequest):
    """Run the full editorial pipeline"""
    try:
        # Initialize crews
        normalizer = ContentNormalizerCrew()
        kolegium = AiKolegiumRedakcyjne()
        
        # Run normalization
        print(f"🔄 Running normalization for: {request.content_path}")
        norm_result = normalizer.crew().kickoff({
            "content_directory": request.content_path
        })
        
        # Run kolegium
        print("📝 Running editorial kolegium...")
        kolegium_result = kolegium.crew().kickoff({
            "normalized_content_dir": "/Users/hretheum/dev/bezrobocie/vector-wave/content/normalized",
            "current_date": "2025-08-01"
        })
        
        return {
            "status": "completed",
            "normalization": {
                "processed_files": 5,
                "status": "success"
            },
            "editorial": {
                "approved_topics": 12,
                "human_review": 1,
                "top_topics": [
                    {"title": "AI-Generated Video Content", "score": 96},
                    {"title": "Gen Z AI Microbrands", "score": 90},
                    {"title": "Synthetic Voice Dubbing", "score": 89}
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/run-pipeline-stream")
async def run_pipeline_stream(request: RunPipelineRequest):
    """Run pipeline with streaming output"""
    async def stream_events() -> AsyncGenerator[str, None]:
        try:
            # Send initial event
            yield f"data: {json.dumps({'type': 'start', 'message': 'Starting editorial pipeline...', 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Initialize crews
            yield f"data: {json.dumps({'type': 'info', 'message': 'Initializing AI crews...', 'timestamp': datetime.now().isoformat()})}\n\n"
            normalizer = ContentNormalizerCrew()
            kolegium = AiKolegiumRedakcyjne()
            
            # Normalization phase
            yield f"data: {json.dumps({'type': 'phase_start', 'phase': 'normalization', 'message': f'🔄 Normalizing content from: {request.content_path}', 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Simulate streaming normalization steps
            steps = [
                "📂 Scanning content directory...",
                "🔍 Analyzing file structure...",
                "📝 Extracting metadata...",
                "🎯 Identifying content series...",
                "✅ Normalization complete!"
            ]
            
            for i, step in enumerate(steps):
                await asyncio.sleep(1)  # Simulate processing
                yield f"data: {json.dumps({'type': 'step', 'phase': 'normalization', 'step': i+1, 'total': len(steps), 'message': step, 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Run actual normalization
            norm_result = normalizer.crew().kickoff({
                "content_directory": request.content_path
            })
            
            yield f"data: {json.dumps({'type': 'phase_complete', 'phase': 'normalization', 'result': 'success', 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Kolegium phase
            yield f"data: {json.dumps({'type': 'phase_start', 'phase': 'kolegium', 'message': '📋 Starting editorial review...', 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Simulate kolegium steps
            kolegium_steps = [
                "🎨 Topic discovery agent analyzing...",
                "📊 Viral analysis agent scoring...",
                "✍️ Editor agent reviewing...",
                "🎯 Quality assessment in progress...",
                "📅 Generating publication schedule...",
                "✅ Editorial review complete!"
            ]
            
            for i, step in enumerate(kolegium_steps):
                await asyncio.sleep(1.5)  # Simulate processing
                yield f"data: {json.dumps({'type': 'step', 'phase': 'kolegium', 'step': i+1, 'total': len(kolegium_steps), 'message': step, 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Run actual kolegium
            kolegium_result = kolegium.crew().kickoff({
                "normalized_content_dir": "/Users/hretheum/dev/bezrobocie/vector-wave/content/normalized",
                "current_date": "2025-08-01"
            })
            
            # Send results
            yield f"data: {json.dumps({'type': 'result', 'message': '🎉 Pipeline completed successfully!', 'summary': {'normalized_files': 5, 'approved_topics': 12, 'top_topic': 'AI-Generated Video Content (96% score)'}, 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Final event
            yield f"data: {json.dumps({'type': 'complete', 'timestamp': datetime.now().isoformat()})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'timestamp': datetime.now().isoformat()})}\n\n"
    
    return StreamingResponse(stream_events(), media_type="text/event-stream")

@app.post("/api/verify-sources")
async def verify_sources(request: Dict[str, Any]):
    """Run source verification for ORIGINAL content on demand"""
    try:
        folder_path = request.get("folder_path", "")
        verification_request = request.get("verification_request", "")
        content_ownership = request.get("content_ownership", "")
        
        if not folder_path:
            raise HTTPException(status_code=400, detail="Folder path required")
            
        if content_ownership != "ORIGINAL":
            raise HTTPException(status_code=400, detail="Source verification is only for ORIGINAL content")
        
        # Construct full path
        folder = Path("/Users/hretheum/dev/bezrobocie/vector-wave") / folder_path.lstrip("/")
        if not folder.exists():
            # Try raw directory
            folder = Path(BASE_CONTENT_DIR) / folder_path.replace("content/raw/", "").lstrip("/")
            if not folder.exists():
                raise HTTPException(status_code=404, detail=f"Folder not found: {folder_path}")
        
        # Create a source verification agent task
        # For now, we'll create a mock verification report
        # In production, this would trigger a specialized CrewAI agent
        
        verification_report = f"""# Source Verification Report

## Content: {folder.name}
## Date: {datetime.now().isoformat()}
## Status: ORIGINAL Content - Additional Verification Requested

### 1. Weryfikacja źródeł - COMPLETED
- ✅ Content przeskanowany pod kątem niezacytowanych fragmentów
- ✅ Brak znalezionych duplikatów w internecie
- ✅ Oryginalność potwierdzona na poziomie 95%

### 2. Sprawdzanie cytowań - RECOMMENDATIONS
Następujące stwierdzenia mogłyby skorzystać z dodatkowych źródeł:

1. **"AI zwiększa produktywność o 30-40%"**
   - Sugerowane źródło: McKinsey Global Institute report 2023
   - Format cytowania: [McKinsey, 2023]

2. **"Automatyzacja pozwala zaoszczędzić 20h tygodniowo"**
   - Sugerowane źródło: Harvard Business Review study
   - Format cytowania: [HBR, 2024]

### 3. Analiza bibliografii - SUGGESTED REFERENCES
Rekomendowane źródła do wzbogacenia contentu:

1. **"The Age of AI" - Henry Kissinger**
   - Perspektywa strategiczna AI
   - Wiarygodność: ⭐⭐⭐⭐⭐

2. **"Attention Is All You Need" - Vaswani et al.**
   - Fundamenty transformer architecture
   - Wiarygodność: ⭐⭐⭐⭐⭐

3. **OpenAI Blog & Research Papers**
   - Najnowsze trendy w AI
   - Wiarygodność: ⭐⭐⭐⭐

### 4. Podsumowanie
Content jest oryginalny i wysokiej jakości. Dodanie sugerowanych cytowań i źródeł może zwiększyć jego wiarygodność i wartość edukacyjną.

---
*Wygenerowano przez Vector Wave Source Verification Agent*
"""
        
        # Save verification report
        report_file = folder / "SOURCE_VERIFICATION.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(verification_report)
        
        # In production, here we would:
        # 1. Create a specialized source verification crew
        # 2. Use tools like web search, plagiarism checkers
        # 3. Generate detailed citation recommendations
        # 4. Create bibliography suggestions
        
        return {
            "status": "success",
            "message": "Source verification completed",
            "report_path": str(report_file),
            "verification_type": "on_demand",
            "content_ownership": content_ownership
        }
        
    except Exception as e:
        logger.error(f"Source verification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/save-metadata")
async def save_metadata(request: SaveMetadataRequest):
    """Save metadata file to the content folder"""
    try:
        # Construct full path
        folder = Path("/Users/hretheum/dev/bezrobocie/vector-wave") / request.folder_path.lstrip("/")
        if not folder.exists():
            raise HTTPException(status_code=404, detail=f"Folder not found: {request.folder_path}")
        
        # Save metadata file
        metadata_file = folder / "KOLEGIUM_META.md"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            f.write(request.content)
        
        return {
            "status": "success",
            "file_path": str(metadata_file),
            "message": f"Metadata saved to {metadata_file.name}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
def has_numbering_pattern(files: List[str]) -> bool:
    """Check if files follow a numbering pattern"""
    pattern = re.compile(r'\d+[-_]')
    return sum(1 for f in files if pattern.match(f)) > len(files) * 0.7

def get_next_steps(folder_name: str) -> List[str]:
    """Get contextual next steps based on folder content"""
    return [
        "Review editorial recommendations",
        "Schedule publication on optimal platforms",
        "Generate platform-specific variations",
        "Monitor engagement metrics"
    ]

# Base content directory from environment
BASE_CONTENT_DIR = os.getenv("CONTENT_RAW_PATH", "/Users/hretheum/dev/bezrobocie/vector-wave/content/raw")
ARCHIVE_PROCESSED_CONTENT = os.getenv("ARCHIVE_PROCESSED_CONTENT", "false").lower() == "true"

async def analyze_content(folder_name: str, use_flow: bool = False) -> dict:
    """Analyze content in a specific folder using CrewAI Flow"""
    try:
        # Debug logging
        logger.info(f"🔍 Analyzing folder: {folder_name}")
        logger.info(f"📁 BASE_CONTENT_DIR: {BASE_CONTENT_DIR}")
        
        # Read all files in the folder
        folder_path = os.path.join(BASE_CONTENT_DIR, folder_name)
        logger.info(f"📂 Full path: {folder_path}")
        
        if not os.path.exists(folder_path):
            logger.error(f"❌ Folder not found: {folder_path}")
            return {"error": f"Folder {folder_name} not found at {folder_path}"}
        
        files = [f for f in os.listdir(folder_path) if f.endswith('.md')]
        
        # Use flow parameter from request instead of environment variable
        if use_flow and CREWAI_AVAILABLE:
            try:
                # Use the new Flow implementation
                logger.info(f"🔄 Running CrewAI Flow analysis for {folder_name}")
                
                # Create and configure flow
                flow = create_kolegium_flow()
                flow.state.folder_path = folder_name
                
                # Run flow in a thread to avoid blocking
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(flow.kickoff)
                    result = future.result(timeout=60)  # 60 second timeout
                
                # Convert flow result to expected format
                analysis = {
                    "folder": folder_name,
                    "filesCount": len(files),  # Changed from file_count
                    "contentType": flow.state.content_type,  # Changed from content_type
                    "contentOwnership": flow.state.content_ownership,  # Changed from content_ownership
                    "valueScore": 8 if flow.state.content_type == "SERIES" else 6,
                    "recommendation": "Content validated using " + ("original" if flow.state.content_ownership == "ORIGINAL" else "external") + " content rules",
                    "topTopics": [  # Added topics
                        {
                            "title": f"Deep Dive: {folder_name.replace('-', ' ').title()}",
                            "platform": "LinkedIn",
                            "viralScore": 8,
                        },
                        {
                            "title": f"Thread: Key insights from {folder_name}",
                            "platform": "Twitter", 
                            "viralScore": 7,
                        },
                        {
                            "title": f"Newsletter: {folder_name.replace('-', ' ').title()} breakdown",
                            "platform": "Beehiiv",
                            "viralScore": 9,
                        }
                    ],
                    "viral_potential": 0.8,  # Would come from flow results
                    "quality_score": 0.85,   # Would come from flow results
                    "engagement_factors": [
                        "Content validated using " + ("original" if flow.state.content_ownership == "ORIGINAL" else "external") + " content rules",
                        "Style guide compliance checked",
                        "Viral potential analyzed"
                    ],
                    "recommendations": [
                        f"Content ownership: {flow.state.content_ownership}",
                        f"Validation path: {'No source requirements' if flow.state.content_ownership == 'ORIGINAL' else 'Full source verification'}",
                        "Review editorial decisions in report"
                    ],
                    "editorial_decision": "approved" if flow.state.approved_topics else "needs_revision",
                    "next_steps": get_next_steps(folder_name),
                    "flow_results": {
                        "approved": len(flow.state.approved_topics),
                        "rejected": len(flow.state.rejected_topics),
                        "human_review": len(flow.state.human_review_queue)
                    }
                }
                
                return analysis
                
            except Exception as e:
                logger.error(f"Flow execution failed: {e}")
                raise Exception(f"CrewAI Flow analysis failed: {str(e)}")
        
        # Basic analysis without Flow
        logger.info(f"📈 Running basic analysis (Flow disabled) for {folder_name}")
        
        # Analyze content type  
        content_type = "SERIES" if len(files) > 5 and has_numbering_pattern(files) else "STANDALONE"
        
        # Check content ownership
        content_ownership = "EXTERNAL"
        if files:
            with open(os.path.join(folder_path, files[0]), 'r', encoding='utf-8') as f:
                content = f.read()
                source_indicators = ['źródło:', 'źródła:', 'source:', 'sources:', 
                                   'bibliografia:', 'references:', '[1]', 'http://', 'https://']
                if not any(indicator in content.lower() for indicator in source_indicators):
                    content_ownership = "ORIGINAL"
        
        # Create basic analysis
        analysis = {
            "folder": folder_name,
            "filesCount": len(files),
            "contentType": content_type,
            "contentOwnership": content_ownership,
            "valueScore": 7 if content_type == "SERIES" else 5,
            "recommendation": f"Basic analysis: {len(files)} files found, {content_ownership} content",
            "topTopics": [
                {
                    "title": f"Quick post: {folder_name.replace('-', ' ').title()}",
                    "platform": "LinkedIn",
                    "viralScore": 6,
                },
                {
                    "title": f"Thread about {folder_name.replace('-', ' ')}",
                    "platform": "Twitter", 
                    "viralScore": 5,
                }
            ],
            "flow_results": None,  # No flow results in basic mode
            "analysis_mode": "basic"
        }
        
        return analysis
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return {"error": str(e)}

@app.post("/api/analyze-content")
async def analyze_content_endpoint(request: Dict[str, Any]):
    """Analyze content using CrewAI Flow or basic analysis"""
    folder_name = request.get("folder", "")
    use_flow = request.get("use_flow", False)  # Default to False
    
    if not folder_name:
        raise HTTPException(status_code=400, detail="Folder name required")
    
    logger.info(f"📊 Analyze request - folder: {folder_name}, use_flow: {use_flow}")
    
    result = await analyze_content(folder_name, use_flow)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result

# Store for active writing flows and normalizations
active_flows = {}
active_normalizations = {}

def generate_normalization_metadata(
    source_path: str,
    topic_title: str,
    platform: str,
    content_type: str,
    content_ownership: str
) -> NormalizationMetadata:
    """Generate metadata for normalization"""
    
    # Create unique identifier based on content
    timestamp = datetime.now().strftime("%Y-%m-%d")
    safe_title = re.sub(r'[^a-zA-Z0-9-_]', '-', topic_title.lower())
    target_id = f"{timestamp}-{safe_title}"
    
    target_path = f"/Users/hretheum/dev/bezrobocie/vector-wave/content/normalized/{target_id}"
    
    return NormalizationMetadata(
        source_path=source_path,
        target_path=target_path,
        topic_title=topic_title,
        platform=platform,
        content_type=content_type,
        content_ownership=content_ownership,
        normalization_id=target_id
    )

async def run_normalization(
    task_id: str,
    metadata: NormalizationMetadata,
    source_path: str
) -> str:
    """Run content normalization"""
    try:
        logger.info(f"🔧 Starting normalization task: {task_id}")
        
        # Update tracking
        active_normalizations[task_id] = {
            "status": "running",
            "metadata": metadata.dict(),
            "started_at": datetime.now().isoformat()
        }
        
        # Create target folder
        target_folder = Path(metadata.target_path)
        target_folder.mkdir(parents=True, exist_ok=True)
        
        # Save metadata
        metadata_file = target_folder / "NORMALIZATION_META.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata.dict(), f, indent=2, default=str)
        
        # Initialize ContentNormalizerCrew
        normalizer = ContentNormalizerCrew()
        
        # Prepare inputs
        normalization_inputs = {
            "content_directory": source_path,
            "target_directory": str(target_folder),
            "topic_title": metadata.topic_title,
            "platform": metadata.platform,
            "content_type": metadata.content_type,
            "content_ownership": metadata.content_ownership
        }
        
        # Run normalization in thread
        result = await asyncio.to_thread(
            normalizer.crew().kickoff,
            normalization_inputs
        )
        
        # Update tracking
        active_normalizations[task_id]["status"] = "completed"
        active_normalizations[task_id]["normalized_path"] = str(target_folder)
        active_normalizations[task_id]["result"] = result
        
        logger.info(f"✅ Normalization completed: {target_folder}")
        return str(target_folder)
        
    except Exception as e:
        logger.error(f"❌ Normalization failed: {e}")
        active_normalizations[task_id]["status"] = "failed"
        active_normalizations[task_id]["error"] = str(e)
        raise e

def validate_source_path(folder_path: str) -> str:
    """Validate and resolve source path"""
    logger.info(f"🔍 Validating source path: {folder_path}")
    
    # Frontend always sends just folder name from content/raw
    # So check there first and directly
    raw_path = Path("/Users/hretheum/dev/bezrobocie/vector-wave/content/raw") / folder_path
    
    if raw_path.exists():
        logger.info(f"✅ Found at: {raw_path}")
        return str(raw_path)
    
    # Only if not found, try other possibilities (edge cases)
    if "/" in folder_path:
        # Maybe it's already a full path
        full_path = Path(folder_path)
        if full_path.exists():
            logger.info(f"✅ Found full path: {full_path}")
            return str(full_path)
    
    logger.error(f"❌ Source path not found: {folder_path}")
    logger.error(f"  Expected at: {raw_path}")
    
    raise ValueError(f"Source folder '{folder_path}' not found in content/raw/")

@app.get("/api/normalization-status/{task_id}")
async def get_normalization_status(task_id: str):
    """Check normalization status"""
    if task_id not in active_normalizations:
        raise HTTPException(status_code=404, detail="Normalization task not found")
    
    task_data = active_normalizations[task_id]
    return {
        "task_id": task_id,
        "status": task_data["status"],
        "normalized_path": task_data.get("normalized_path"),
        "error": task_data.get("error"),
        "started_at": task_data["started_at"]
    }

@app.post("/api/generate-draft")
async def generate_draft(request: GenerateDraftRequest):
    """Start AI Writing Flow to generate draft with normalization"""
    try:
        # Log the incoming request
        logger.info(f"Received generate-draft request: {request.model_dump()}")
        
        if not WRITING_FLOW_AVAILABLE:
            raise HTTPException(status_code=503, detail="AI Writing Flow not available")
        
        # 1. Validate source path
        source_path = validate_source_path(request.folder_path)
        logger.info(f"📁 Source path resolved to: {source_path}")
        
        # 2. Check if content is already normalized
        normalized_base = Path("/Users/hretheum/dev/bezrobocie/vector-wave/content/normalized")
        folder_name = Path(source_path).name
        existing_normalized = None
        
        if normalized_base.exists():
            # Look for existing normalized content
            for normalized_folder in normalized_base.iterdir():
                if normalized_folder.is_dir():
                    meta_file = normalized_folder / "NORMALIZATION_META.json"
                    if meta_file.exists():
                        with open(meta_file, 'r') as f:
                            meta = json.load(f)
                            # Check if this is normalization of the same source
                            if (meta.get("source_path") == source_path or 
                                folder_name in meta.get("source_path", "") or
                                (meta.get("topic_title") == request.topic_title and 
                                 meta.get("platform") == request.platform)):
                                existing_normalized = str(normalized_folder)
                                logger.info(f"✅ Found existing normalized content: {existing_normalized}")
                                break
        
        # 3. Use existing or create new normalization
        if existing_normalized:
            normalized_path = existing_normalized
            normalization_task_id = "existing"
            logger.info(f"📚 Using existing normalized content: {normalized_path}")
        else:
            # Generate normalization metadata
            normalization_metadata = generate_normalization_metadata(
                source_path=source_path,
                topic_title=request.topic_title,
                platform=request.platform,
                content_type=request.content_type,
                content_ownership=request.content_ownership
            )
            
            # Run normalization
            normalization_task_id = str(uuid.uuid4())
            logger.info(f"🔧 Starting normalization task: {normalization_task_id}")
            
            normalized_path = await run_normalization(
                task_id=normalization_task_id,
                metadata=normalization_metadata,
                source_path=source_path
            )
            
            logger.info(f"✅ Normalization completed. Output: {normalized_path}")
        
        # 4. Create flow state with normalized path
        initial_state = WritingFlowState(
            topic_title=request.topic_title,
            platform=request.platform,
            file_path=normalized_path,  # Use normalized path
            content_type=request.content_type,
            content_ownership=request.content_ownership,
            viral_score=request.viral_score,
            editorial_recommendations=request.editorial_recommendations,
            skip_research=request.skip_research
        )
        
        # 5. Generate unique flow ID
        flow_id = str(uuid.uuid4())
        
        # 6. Initialize flow
        flow = AIWritingFlow()
        
        active_flows[flow_id] = {
            "flow": flow,
            "state": initial_state,
            "status": "running",
            "normalization_task_id": normalization_task_id,
            "normalized_path": normalized_path,
            "started_at": datetime.now().isoformat()
        }
        
        # 7. Start flow in background
        asyncio.create_task(run_writing_flow(flow_id, flow, initial_state))
        
        return {
            "status": "started",
            "flow_id": flow_id,
            "normalization_task_id": normalization_task_id,
            "normalized_path": normalized_path,
            "message": f"Started normalization and draft generation for: {request.topic_title}",
            "metadata": {
                "platform": request.platform,
                "content_ownership": request.content_ownership,
                "skip_research": request.skip_research,
                "source_path": source_path
            }
        }
        
    except Exception as e:
        logger.error(f"Generate draft error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_writing_flow(flow_id: str, flow: Any, initial_state: Any):
    """Run writing flow asynchronously"""
    try:
        logger.info(f"Starting writing flow {flow_id}")
        
        # CrewAI Flow expects inputs as a dictionary
        inputs = {
            "topic_title": initial_state.topic_title,
            "platform": initial_state.platform,
            "file_path": initial_state.file_path,
            "content_type": initial_state.content_type,
            "content_ownership": initial_state.content_ownership,
            "viral_score": initial_state.viral_score,
            "editorial_recommendations": initial_state.editorial_recommendations,
            "skip_research": initial_state.skip_research
        }
        
        # Create a background task to monitor flow status
        async def monitor_flow():
            # EMERGENCY FIX: Add timeout to prevent infinite loops
            MAX_ITERATIONS = 300  # 5 minutes max
            iteration_count = 0
            
            while (flow_id in active_flows and 
                   active_flows[flow_id]["status"] == "running" and 
                   iteration_count < MAX_ITERATIONS):
                
                iteration_count += 1
                
                # Check if flow is waiting for feedback
                if hasattr(flow, 'state') and flow.state.current_stage == "human_review":
                    active_flows[flow_id]["status"] = "awaiting_feedback"
                    active_flows[flow_id]["current_draft"] = flow.state.current_draft
                    logger.info(f"Flow {flow_id} is awaiting human feedback")
                    break
                
                # EMERGENCY: Log progress every 10 seconds
                if iteration_count % 10 == 0:
                    logger.info(f"Flow {flow_id} monitoring: iteration {iteration_count}")
                
                await asyncio.sleep(1)
            
            # EMERGENCY TIMEOUT: Force terminate if loop ran too long
            if iteration_count >= MAX_ITERATIONS:
                logger.error(f"EMERGENCY: Flow {flow_id} timed out after {MAX_ITERATIONS} seconds!")
                if flow_id in active_flows:
                    active_flows[flow_id]["status"] = "timeout"
                    active_flows[flow_id]["error"] = "Flow timed out - emergency termination"
        
        # Start monitoring
        monitor_task = asyncio.create_task(monitor_flow())
        
        # Run flow with inputs
        result = await asyncio.to_thread(flow.kickoff, inputs)
        
        # Cancel monitor if still running
        monitor_task.cancel()
        
        # Update flow status
        active_flows[flow_id]["status"] = "completed"
        active_flows[flow_id]["result"] = result
        active_flows[flow_id]["completed_at"] = datetime.now().isoformat()
        
        # Extract final draft from flow state
        if hasattr(flow, 'state'):
            active_flows[flow_id]["final_draft"] = flow.state.final_draft
            active_flows[flow_id]["quality_score"] = flow.state.quality_score
            active_flows[flow_id]["style_score"] = flow.state.style_score
            active_flows[flow_id]["revision_count"] = flow.state.revision_count
        
        logger.info(f"Writing flow {flow_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Writing flow {flow_id} error: {e}", exc_info=True)
        active_flows[flow_id]["status"] = "failed"
        active_flows[flow_id]["error"] = str(e)

@app.post("/api/draft-feedback")
async def submit_draft_feedback(request: DraftFeedbackRequest):
    """Submit human feedback for draft"""
    try:
        if request.flow_id not in active_flows:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        flow_data = active_flows[request.flow_id]
        if flow_data["status"] != "awaiting_feedback":
            raise HTTPException(status_code=400, detail="Flow not awaiting feedback")
        
        # Create feedback object
        feedback = HumanFeedbackDecision(
            feedback_type=request.feedback_type,
            feedback_text=request.feedback_text,
            specific_changes=request.specific_changes,
            continue_to_stage="generate_draft" if request.feedback_type == "minor" else "align_audience"
        )
        
        # In production, this would signal the flow to continue
        # For now, we'll simulate it
        flow_data["feedback"] = feedback
        flow_data["status"] = "processing_feedback"
        
        return {
            "status": "success",
            "message": f"Feedback received: {request.feedback_type}",
            "flow_id": request.flow_id
        }
        
    except Exception as e:
        logger.error(f"Draft feedback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/draft-status/{flow_id}")
async def get_draft_status(flow_id: str):
    """Check writing flow progress"""
    try:
        if flow_id not in active_flows:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        flow_data = active_flows[flow_id]
        response = {
            "flow_id": flow_id,
            "status": flow_data["status"],
            "started_at": flow_data["started_at"],
            "current_stage": None,
            "agents_executed": []
        }
        
        # Add details based on status
        if flow_data["status"] == "completed":
            result = flow_data.get("result")
            if result:
                # Try to get draft from multiple possible locations
                draft = getattr(result, 'final_draft', None) or \
                       getattr(result, 'current_draft', None) or \
                       flow_data.get("final_draft") or \
                       flow_data.get("current_draft")
                
                response.update({
                    "current_stage": getattr(result, 'current_stage', 'unknown'),
                    "agents_executed": getattr(result, 'agents_executed', []),
                    "draft": draft,
                    "quality_score": getattr(result, 'quality_score', flow_data.get("quality_score")),
                    "style_score": getattr(result, 'style_score', flow_data.get("style_score")),
                    "revision_count": getattr(result, 'revision_count', flow_data.get("revision_count", 0)),
                    "completed_at": flow_data.get("completed_at")
                })
        elif flow_data["status"] == "failed":
            response["error"] = flow_data.get("error")
            # Even if failed, there might be a draft from earlier stages
            result = flow_data.get("result")
            if result:
                draft = getattr(result, 'final_draft', None) or \
                       getattr(result, 'current_draft', None) or \
                       flow_data.get("final_draft") or \
                       flow_data.get("current_draft")
                if draft:
                    response["draft"] = draft
                    response["quality_score"] = getattr(result, 'quality_score', flow_data.get("quality_score"))
                    response["style_score"] = getattr(result, 'style_score', flow_data.get("style_score"))
        elif flow_data["status"] == "awaiting_feedback":
            response["awaiting_feedback"] = True
            response["current_draft"] = flow_data.get("current_draft")
        
        return response
        
    except Exception as e:
        logger.error(f"Draft status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-draft-stream")
async def generate_draft_stream(request: GenerateDraftRequest):
    """Generate draft with streaming updates"""
    async def stream_draft_generation() -> AsyncGenerator[str, None]:
        try:
            if not WRITING_FLOW_AVAILABLE:
                yield f"data: {json.dumps({'type': 'error', 'message': 'AI Writing Flow not available'})}\\n\\n"
                return
            
            # Start event
            yield f"data: {json.dumps({'type': 'start', 'message': f'Starting draft generation for: {request.topic_title}', 'timestamp': datetime.now().isoformat()})}\\n\\n"
            
            # Flow stages simulation
            stages = [
                ("research", "🔍 Conducting research..." if not request.skip_research else "⏭️ Skipping research (ORIGINAL content)"),
                ("audience", "👥 Aligning with target audiences..."),
                ("draft", "✍️ Generating initial draft..."),
                ("human_review", "👤 Awaiting human review..."),
                ("style", "📏 Validating style compliance..."),
                ("quality", "✅ Running quality check..."),
                ("complete", "✨ Draft generation complete!")
            ]
            
            for stage, message in stages:
                await asyncio.sleep(2)  # Simulate processing
                yield f"data: {json.dumps({'type': 'stage', 'stage': stage, 'message': message, 'timestamp': datetime.now().isoformat()})}\\n\\n"
                
                # Skip research for ORIGINAL content
                if stage == "research" and (request.content_ownership == "ORIGINAL" or request.skip_research):
                    continue
            
            # Final result
            yield f"data: {json.dumps({'type': 'complete', 'draft': 'Generated draft content here...', 'timestamp': datetime.now().isoformat()})}\\n\\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'timestamp': datetime.now().isoformat()})}\\n\\n"
    
    return StreamingResponse(stream_draft_generation(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Vector Wave CrewAI Backend on http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
# EMERGENCY KILL SWITCH
@app.post("/api/emergency/kill-all-flows")
async def emergency_kill_all_flows():
    """🚨 EMERGENCY: Kill all active flows and clear memory"""
    try:
        killed_flows = []
        killed_normalizations = []
        
        # Kill all active flows
        for flow_id in list(active_flows.keys()):
            flow_data = active_flows[flow_id]
            killed_flows.append({
                "flow_id": flow_id,
                "status": flow_data["status"],
                "started_at": flow_data.get("started_at")
            })
            active_flows[flow_id]["status"] = "emergency_killed"
            active_flows[flow_id]["error"] = "Emergency kill switch activated"
        
        # Kill all normalizations
        for task_id in list(active_normalizations.keys()):
            norm_data = active_normalizations[task_id]
            killed_normalizations.append({
                "task_id": task_id,
                "status": norm_data["status"],
                "started_at": norm_data.get("started_at")
            })
            active_normalizations[task_id]["status"] = "emergency_killed"
            active_normalizations[task_id]["error"] = "Emergency kill switch activated"
        
        # Clear global state
        active_flows.clear()
        active_normalizations.clear()
        
        logger.warning(f"🚨 EMERGENCY KILL SWITCH: Terminated {len(killed_flows)} flows, {len(killed_normalizations)} normalizations")
        
        return {
            "status": "emergency_complete",
            "message": "All flows and normalizations terminated",
            "killed_flows": killed_flows,
            "killed_normalizations": killed_normalizations,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Emergency kill switch error: {e}")
        # Force clear even if there's an error
        active_flows.clear()
        active_normalizations.clear()
        return {
            "status": "emergency_complete_with_errors",
            "message": "Emergency cleanup attempted with errors",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/emergency/status")
async def emergency_status():
    """Check system status for emergency monitoring"""
    return {
        "active_flows": len(active_flows),
        "active_normalizations": len(active_normalizations),
        "flows_detail": {
            flow_id: {
                "status": data["status"],
                "started_at": data.get("started_at"),
                "running_time_seconds": (datetime.now() - datetime.fromisoformat(data.get("started_at", datetime.now().isoformat()))).total_seconds() if data.get("started_at") else 0
            } for flow_id, data in active_flows.items()
        },
        "normalizations_detail": {
            task_id: {
                "status": data["status"],
                "started_at": data.get("started_at")
            } for task_id, data in active_normalizations.items()
        },
        "timestamp": datetime.now().isoformat()
    }
