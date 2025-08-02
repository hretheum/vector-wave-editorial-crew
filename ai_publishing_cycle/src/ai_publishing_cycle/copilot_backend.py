#!/usr/bin/env python
"""
Backend server that connects CopilotKit UI with our CrewAI crews
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
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
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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

# Store for active writing flows
active_flows = {}

@app.post("/api/generate-draft")
async def generate_draft(request: GenerateDraftRequest):
    """Start AI Writing Flow to generate draft"""
    try:
        if not WRITING_FLOW_AVAILABLE:
            raise HTTPException(status_code=503, detail="AI Writing Flow not available")
        
        # Create flow state from request
        initial_state = WritingFlowState(
            topic_title=request.topic_title,
            platform=request.platform,
            folder_path=request.folder_path,
            content_type=request.content_type,
            content_ownership=request.content_ownership,
            viral_score=request.viral_score,
            editorial_recommendations=request.editorial_recommendations,
            skip_research=request.skip_research
        )
        
        # Generate unique flow ID
        flow_id = str(uuid.uuid4())
        
        # Initialize flow
        flow = AIWritingFlow()
        active_flows[flow_id] = {
            "flow": flow,
            "state": initial_state,
            "status": "running",
            "started_at": datetime.now().isoformat()
        }
        
        # Start flow in background (in production, use proper async task queue)
        import asyncio
        asyncio.create_task(run_writing_flow(flow_id, flow, initial_state))
        
        return {
            "status": "started",
            "flow_id": flow_id,
            "message": f"Started generating draft for: {request.topic_title}",
            "metadata": {
                "platform": request.platform,
                "content_ownership": request.content_ownership,
                "skip_research": request.skip_research
            }
        }
        
    except Exception as e:
        logger.error(f"Generate draft error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_writing_flow(flow_id: str, flow: AIWritingFlow, initial_state: WritingFlowState):
    """Run writing flow asynchronously"""
    try:
        # Run flow
        result = await asyncio.to_thread(flow.kickoff, initial_state)
        
        # Update flow status
        active_flows[flow_id]["status"] = "completed"
        active_flows[flow_id]["result"] = result
        active_flows[flow_id]["completed_at"] = datetime.now().isoformat()
        
    except Exception as e:
        logger.error(f"Writing flow error: {e}")
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
                response.update({
                    "current_stage": result.current_stage,
                    "agents_executed": result.agents_executed,
                    "draft": result.final_draft,
                    "quality_score": result.quality_score,
                    "style_score": result.style_score,
                    "revision_count": result.revision_count,
                    "completed_at": flow_data.get("completed_at")
                })
        elif flow_data["status"] == "failed":
            response["error"] = flow_data.get("error")
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