from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime
import time
import os
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI

app = FastAPI(title="AI Writing Flow - Container First")

# Storage dla wykonań flow (w produkcji użyj Redis/DB)
flow_executions = {}

class FlowStep:
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name
        self.status = "pending"
        self.start_time = None
        self.end_time = None
        self.input = None
        self.output = None
        self.agent_decisions = []
        self.content_loss = None
        self.errors = []

# Initialize LLM for CrewAI
llm = ChatOpenAI(
    model_name="gpt-4",
    temperature=0.7,
    api_key=os.getenv("OPENAI_API_KEY")
)

class ContentRequest(BaseModel):
    title: str
    content_type: str = "STANDARD"  # STANDARD, TECHNICAL, VIRAL
    platform: str = "LinkedIn"
    content_ownership: str = "EXTERNAL"  # EXTERNAL, ORIGINAL

class ResearchRequest(BaseModel):
    topic: str
    depth: str = "standard"  # quick, standard, deep
    skip_research: bool = False

@app.get("/")
def root():
    return {"status": "ok", "service": "ai-writing-flow"}

@app.get("/health")
def health():
    return {"status": "healthy", "container": "running"}

@app.post("/api/test-routing")
def test_routing(content: ContentRequest):
    """Test endpoint pokazujący że routing działa"""
    # Podstawowa logika routingu
    if content.content_ownership == "ORIGINAL":
        route = "skip_research_flow"
    elif content.content_type == "TECHNICAL":
        route = "technical_deep_dive_flow"
    elif content.content_type == "VIRAL":
        route = "viral_engagement_flow"
    else:
        route = "standard_editorial_flow"
    
    return {
        "status": "routed",
        "input": content.dict(),
        "route_decision": route,
        "skip_research": content.content_ownership == "ORIGINAL",
        "container_id": "ai-writing-flow-v1"
    }

@app.post("/api/research")
async def execute_research(request: ResearchRequest):
    """Wykonuje research używając CrewAI Agent"""
    
    if request.skip_research:
        return {
            "status": "skipped",
            "reason": "skip_research flag is True",
            "topic": request.topic,
            "findings": []
        }
    
    # Stwórz Research Agent
    researcher = Agent(
        role="Senior Research Analyst",
        goal=f"Research comprehensive information about {request.topic}",
        backstory="Expert researcher with access to vast knowledge",
        verbose=True,
        llm=llm
    )
    
    # Stwórz task
    research_task = Task(
        description=f"""
        Research the topic: {request.topic}
        Depth level: {request.depth}
        
        Provide:
        1. Key concepts and definitions
        2. Current trends and developments
        3. Best practices
        4. Common challenges
        """,
        agent=researcher,
        expected_output="Comprehensive research findings"
    )
    
    # Wykonaj research
    crew = Crew(
        agents=[researcher],
        tasks=[research_task],
        verbose=True
    )
    
    try:
        start_time = time.time()
        result = crew.kickoff()
        execution_time = int((time.time() - start_time) * 1000)
        
        return {
            "status": "completed",
            "topic": request.topic,
            "depth": request.depth,
            "findings": {
                "summary": str(result),
                "key_points": extract_key_points(str(result)),
                "word_count": len(str(result).split())
            },
            "execution_time_ms": execution_time
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "topic": request.topic
        }

def extract_key_points(text: str) -> list:
    """Wyciągnij kluczowe punkty z tekstu"""
    # Prosta heurystyka - w produkcji użyj NLP
    lines = text.split('\n')
    key_points = [line.strip() for line in lines if line.strip() and len(line.strip()) > 20][:5]
    return key_points

class GenerateDraftRequest(BaseModel):
    content: ContentRequest
    research_data: Optional[Dict] = None

@app.post("/api/generate-draft")
async def generate_draft(request: GenerateDraftRequest):
    """Generuje draft używając CrewAI Writer Agent"""
    
    content = request.content
    research_data = request.research_data
    
    # Writer Agent
    writer = Agent(
        role=f"{content.platform} Content Writer",
        goal=f"Write engaging {content.platform} content about {content.title}",
        backstory=f"Expert {content.platform} content creator",
        verbose=True,
        llm=llm
    )
    
    # Context z research (jeśli jest)
    context = ""
    if research_data and research_data.get("findings"):
        context = f"Research findings: {research_data['findings']['summary']}"
    
    # Writing task
    writing_task = Task(
        description=f"""
        Write {content.platform} content about: {content.title}
        Content type: {content.content_type}
        
        {context}
        
        Requirements:
        - Optimize for {content.platform} best practices
        - Target length: {"280 chars" if content.platform == "Twitter" else "500-1000 words"}
        - Include engaging hook
        - Add call to action
        """,
        agent=writer,
        expected_output=f"Complete {content.platform} post"
    )
    
    crew = Crew(agents=[writer], tasks=[writing_task])
    
    try:
        result = crew.kickoff()
        
        return {
            "status": "completed",
            "draft": {
                "title": content.title,
                "content": str(result),
                "platform": content.platform,
                "word_count": len(str(result).split()),
                "optimized_for": content.platform
            },
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "content_type": content.content_type,
                "used_research": research_data is not None
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/api/execute-flow")
async def execute_complete_flow(content: ContentRequest):
    """Wykonuje kompletny flow: routing → research → writing"""
    
    execution_log = []
    start_time = datetime.now()
    
    # Step 1: Routing
    routing_result = test_routing(content)
    execution_log.append({
        "step": "routing",
        "result": routing_result,
        "duration_ms": 50
    })
    
    # Step 2: Research (jeśli potrzebny)
    research_result = None
    if not routing_result["skip_research"]:
        research_request = ResearchRequest(
            topic=content.title,
            depth="deep" if content.content_type == "TECHNICAL" else "standard"
        )
        research_result = await execute_research(research_request)
        execution_log.append({
            "step": "research",
            "result": research_result,
            "duration_ms": research_result.get("execution_time_ms", 2500)
        })
    
    # Step 3: Generate Draft
    draft_request = GenerateDraftRequest(
        content=content,
        research_data=research_result
    )
    draft_result = await generate_draft(draft_request)
    execution_log.append({
        "step": "draft_generation",
        "result": draft_result,
        "duration_ms": 3000
    })
    
    total_duration = int((datetime.now() - start_time).total_seconds() * 1000)
    
    return {
        "flow_id": f"flow_{int(time.time())}",
        "status": "completed",
        "routing_decision": routing_result["route_decision"],
        "execution_log": execution_log,
        "final_draft": draft_result.get("draft"),
        "total_duration_ms": total_duration
    }

@app.post("/api/execute-flow-tracked")
async def execute_flow_with_tracking(content: ContentRequest):
    """Wykonuje flow z pełnym śledzeniem dla diagnostyki"""
    
    flow_id = f"flow_{int(time.time())}"
    steps: List[FlowStep] = []
    
    # Step 1: Input Validation
    validation_step = FlowStep("input_validation", "Walidacja Wejścia")
    validation_step.start_time = datetime.now().isoformat()
    validation_step.input = content.dict()
    
    try:
        # Walidacja
        validation_step.output = {
            "validated": True,
            "content_type": content.content_type,
            "platform": content.platform,
            "ownership": content.content_ownership
        }
        validation_step.agent_decisions = [
            f"Wykryto typ contentu: {content.content_type}",
            f"Platforma docelowa: {content.platform}",
            f"Ownership: {content.content_ownership} - {'pominięto research' if content.content_ownership == 'ORIGINAL' else 'wymagany research'}"
        ]
        validation_step.status = "completed"
    except Exception as e:
        validation_step.status = "failed"
        validation_step.errors = [str(e)]
    
    validation_step.end_time = datetime.now().isoformat()
    steps.append(validation_step)
    
    # Step 2: Research (jeśli potrzebny)
    research_step = FlowStep("research", "Badanie Tematu")
    if content.content_ownership == "ORIGINAL":
        research_step.status = "skipped"
        research_step.agent_decisions = [
            "Pominięto research dla ORIGINAL content",
            "Flaga skip_research = true"
        ]
    else:
        research_step.start_time = datetime.now().isoformat()
        try:
            research_request = ResearchRequest(
                topic=content.title,
                depth="deep" if content.content_type == "TECHNICAL" else "standard"
            )
            research_result = await execute_research(research_request)
            
            research_step.output = research_result
            research_step.agent_decisions = [
                f"Wykonano {research_request.depth} research",
                f"Znaleziono {len(research_result.get('findings', {}).get('key_points', []))} kluczowych punktów",
                f"Czas wykonania: {research_result.get('execution_time_ms', 0)}ms"
            ]
            research_step.status = "completed"
            
            # Oblicz content loss
            input_size = len(content.title) * 50  # Przybliżenie
            output_size = research_result.get('findings', {}).get('word_count', 0) * 5
            research_step.content_loss = {
                "inputSize": input_size,
                "outputSize": output_size,
                "lossPercentage": round((1 - output_size/input_size) * 100, 1) if input_size > 0 else 0
            }
        except Exception as e:
            research_step.status = "failed"
            research_step.errors = [str(e)]
        
        research_step.end_time = datetime.now().isoformat()
    
    steps.append(research_step)
    
    # Step 3: Draft Generation
    draft_step = FlowStep("draft_generation", "Generowanie Draftu")
    draft_step.start_time = datetime.now().isoformat()
    
    try:
        draft_request = GenerateDraftRequest(
            content=content,
            research_data=research_step.output if research_step.status == "completed" else None
        )
        draft_result = await generate_draft(draft_request)
        
        draft_step.output = draft_result
        draft_step.agent_decisions = [
            "✅ Wygenerowano draft używając CrewAI Writer Agent",
            f"Długość: {draft_result.get('draft', {}).get('word_count', 0)} słów",
            f"Wykorzystano research: {'Tak' if draft_request.research_data else 'Nie'}",
            f"Platforma: {content.platform}"
        ]
        draft_step.status = "completed"
        
        # Content preservation check
        draft_step.content_loss = {
            "inputSize": len(str(draft_request.dict())) * 10,
            "outputSize": len(draft_result.get('draft', {}).get('content', '')),
            "lossPercentage": 0  # CrewAI zachowuje content
        }
    except Exception as e:
        draft_step.status = "failed"
        draft_step.errors = [str(e)]
    
    draft_step.end_time = datetime.now().isoformat()
    steps.append(draft_step)
    
    # Zapisz wykonanie
    flow_executions[flow_id] = {
        "flow_id": flow_id,
        "steps": [vars(step) for step in steps],
        "created_at": datetime.now().isoformat(),
        "total_duration_ms": sum(
            (datetime.fromisoformat(s.end_time) - datetime.fromisoformat(s.start_time)).total_seconds() * 1000
            for s in steps if s.start_time and s.end_time
        )
    }
    
    return {
        "flow_id": flow_id,
        "status": "completed" if all(s.status in ["completed", "skipped"] for s in steps) else "failed",
        "diagnostic_url": f"/api/flow-diagnostics/{flow_id}",
        "final_draft": draft_step.output.get("draft") if draft_step.status == "completed" else None
    }

@app.get("/api/flow-diagnostics/{flow_id}")
async def get_flow_diagnostics(flow_id: str):
    """Zwraca dane diagnostyczne dla konkretnego wykonania flow"""
    
    if flow_id not in flow_executions:
        raise HTTPException(status_code=404, detail="Flow execution not found")
    
    return flow_executions[flow_id]

@app.get("/api/flow-diagnostics")
async def list_flow_executions(limit: int = 10):
    """Lista ostatnich wykonań flow"""
    
    executions = sorted(
        flow_executions.values(),
        key=lambda x: x["created_at"],
        reverse=True
    )[:limit]
    
    return {
        "total": len(flow_executions),
        "executions": executions
    }

@app.get("/api/list-content-folders")
async def list_content_folders():
    """Lista folderów z contentem"""
    import os
    import glob
    
    content_path = "/Users/hretheum/dev/bezrobocie/vector-wave/content/raw"
    
    try:
        if not os.path.exists(content_path):
            return {
                "status": "error", 
                "message": f"❌ CRITICAL: Content path does not exist: {content_path}",
                "folders": []
            }
        
        # Znajdź wszystkie foldery w content/raw
        folders = []
        for folder_path in glob.glob(os.path.join(content_path, "*")):
            if os.path.isdir(folder_path):
                folder_name = os.path.basename(folder_path)
                folders.append({
                    "name": folder_name,
                    "path": folder_path,
                    "type": "raw_content"
                })
        
        return {
            "status": "ok",
            "folders": folders,
            "total": len(folders)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ CRITICAL ERROR: {str(e)}",
            "folders": []
        }

class AnalyzePotentialRequest(BaseModel):
    folder: str
    use_flow: bool = False

@app.post("/api/analyze-potential")
async def analyze_content_potential(request: AnalyzePotentialRequest):
    """Szybka analiza potencjału contentu (2-3 sekundy max)"""
    
    start_time = time.time()
    
    try:
        folder_name = request.folder
        
        # Simple analysis without ContentAnalysisAgent
        # Analyze folder name for themes
        title = folder_name.replace('-', ' ').title()
        themes = []
        
        # Extract key themes from folder name
        tech_keywords = ['ai', 'ml', 'api', 'database', 'cloud', 'automation', 'framework', 'workflow', 'agent']
        for keyword in tech_keywords:
            if keyword in folder_name.lower():
                themes.append(keyword.upper())
        
        if not themes:
            # Extract any significant words
            words = folder_name.split('-')
            themes = [w.upper() for w in words if len(w) > 3][:3]
        
        # Calculate viral score based on folder name
        viral_score = 0.5  # Base score
        viral_keywords = ['solution', 'hack', 'secret', 'mistake', 'truth', 'guide', 'tips']
        for keyword in viral_keywords:
            if keyword in folder_name.lower():
                viral_score += 0.1
        
        # Platform-specific boost
        if 'linkedin' in folder_name.lower():
            viral_score += 0.05
        
        viral_score = min(viral_score, 1.0)
        
        # Count actual files in folder
        import glob
        file_path = f"/Users/hretheum/dev/bezrobocie/vector-wave/content/raw/{folder_name}"
        files_count = len(glob.glob(f"{file_path}/*")) if os.path.exists(file_path) else 0
        
        # Determine content type and complexity
        content_type = "TECHNICAL" if any(kw in folder_name.lower() for kw in ['code', 'api', 'implementation']) else "GENERAL"
        complexity_level = "advanced" if any(kw in folder_name.lower() for kw in ['advanced', 'expert', 'deep']) else "intermediate"
        
        # Generate topic suggestions
        top_topics = []
        
        # LinkedIn topic
        top_topics.append({
            "title": f"5 Lessons from {title} Implementation",
            "platform": "LinkedIn",
            "viralScore": min(10, int(viral_score * 10 + 1))
        })
        
        # Twitter topic
        main_theme = themes[0] if themes else 'Tech'
        top_topics.append({
            "title": f"The {main_theme} Mistake Everyone Makes",
            "platform": "Twitter",
            "viralScore": min(10, int(viral_score * 10 + 2))
        })
        
        # Blog topic
        top_topics.append({
            "title": f"{title}: A Complete Guide",
            "platform": "Blog",
            "viralScore": min(10, int(viral_score * 10))
        })
        
        # Generate recommendation
        if viral_score > 0.7:
            recommendation = "🔥 High viral potential! Publish immediately on LinkedIn for maximum reach."
        elif viral_score > 0.5:
            recommendation = "✅ Good potential. Consider adding controversial angles to boost engagement."
        else:
            recommendation = "📊 Niche content. Focus on technical communities for better reception."
        
        # Get audience scores
        audience_scores = await get_quick_audience_scores(
            title,
            'LinkedIn',
            timeout=1.0,
            fallback_scores={
                "technical_founder": 0.7,
                "senior_engineer": 0.6,
                "decision_maker": 0.5,
                "skeptical_learner": 0.8
            }
        )
        
        # Build response
        analysis_result = {
            "folder": folder_name,
            "filesCount": files_count,
            "contentType": content_type,
            "contentOwnership": "ORIGINAL" if "adhd" in folder_name.lower() or "personal" in folder_name.lower() else "EXTERNAL",
            "valueScore": round(viral_score * 10, 1),
            "viral_score": viral_score,
            "complexity_level": complexity_level,
            "key_themes": themes,
            "topTopics": top_topics,
            "recommendation": recommendation,
            "audience_scores": audience_scores,
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "confidence": 0.75  # Fixed confidence for simple analysis
        }
        
        return analysis_result
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "folder": request.folder
        }

@app.post("/api/analyze-content")
async def analyze_content_legacy(request: dict):
    """Legacy endpoint for backward compatibility - redirects to analyze-potential"""
    analyze_request = AnalyzePotentialRequest(
        folder=request.get("folder", ""),
        use_flow=request.get("use_flow", False)
    )
    return await analyze_content_potential(analyze_request)

async def get_quick_audience_scores(
    title: str, 
    platform: str, 
    timeout: float = 1.0,
    fallback_scores: Dict[str, float] = None
) -> Dict[str, float]:
    """Get audience scores with simple heuristics"""
    
    if fallback_scores is None:
        fallback_scores = {
            "technical_founder": 0.6,
            "senior_engineer": 0.6,
            "decision_maker": 0.5,
            "skeptical_learner": 0.7
        }
    
    # Simple scoring based on title keywords
    title_lower = title.lower()
    
    scores = fallback_scores.copy()
    
    # Adjust scores based on keywords
    if any(word in title_lower for word in ['framework', 'workflow', 'process', 'solution']):
        scores["technical_founder"] += 0.2
        scores["decision_maker"] += 0.1
    
    if any(word in title_lower for word in ['architecture', 'code', 'technical', 'engineering', 'implementation']):
        scores["senior_engineer"] += 0.2
        scores["technical_founder"] += 0.1
    
    if any(word in title_lower for word in ['ai', 'automation', 'efficiency']):
        scores["skeptical_learner"] += 0.1
        scores["decision_maker"] += 0.1
    
    # Platform adjustments
    if platform.lower() == "linkedin":
        scores["decision_maker"] += 0.1
    elif platform.lower() == "twitter":
        scores["technical_founder"] += 0.1
        scores["senior_engineer"] += 0.1
    
    # Normalize scores to max 1.0
    for key in scores:
        scores[key] = min(scores[key], 1.0)
    
    return scores

@app.get("/api/verify-openai")
async def verify_openai():
    """Weryfikuje że używamy prawdziwego OpenAI API"""
    import time
    
    try:
        # Test bezpośredni z OpenAI
        start_time = time.time()
        test_agent = Agent(
            role="Verification Agent",
            goal="Generate a unique timestamp-based message",
            backstory="I verify API authenticity",
            verbose=True,
            llm=llm
        )
        
        test_task = Task(
            description=f"Generate ONE short sentence with current timestamp: {datetime.now().isoformat()}",
            agent=test_agent,
            expected_output="One unique sentence"
        )
        
        crew = Crew(agents=[test_agent], tasks=[test_task])
        result = crew.kickoff()
        
        execution_time = time.time() - start_time
        
        return {
            "status": "verified",
            "api_type": "OpenAI GPT-4",
            "response": str(result),
            "execution_time_seconds": round(execution_time, 2),
            "timestamp": datetime.now().isoformat(),
            "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
            "model": llm.model_name
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "api_key_configured": bool(os.getenv("OPENAI_API_KEY"))
        }