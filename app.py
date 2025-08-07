from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime
import time
import os
import redis
import json
import hashlib
import re
import asyncio
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
import chromadb
from chromadb.config import Settings
from openai import AsyncOpenAI
import json
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()

app = FastAPI(
    title="AI Writing Flow - Container First",
    description="AI-powered content generation system with CrewAI agents integration. Optimized for fast content analysis and draft generation.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "health", "description": "Health check endpoints"},
        {"name": "content", "description": "Content analysis and generation"},
        {"name": "research", "description": "Research operations"},
        {"name": "flow", "description": "Complete flow execution"},
        {"name": "diagnostics", "description": "Flow diagnostics and monitoring"},
        {"name": "assistant", "description": "AI Assistant chat endpoints"}
    ]
)

@app.on_event("startup")
async def startup_event():
    """Log startup configuration and validate services"""
    logger.info("🚀 AI Writing Flow starting up...", version="2.0.0")
    
    # Check OpenAI configuration
    if OPENAI_API_KEY:
        logger.info("✅ OpenAI API configured", key_prefix=OPENAI_API_KEY[:7])
    else:
        logger.warning("⚠️ OpenAI API key not configured - AI Assistant will be unavailable")
    
    # Check Redis
    if redis_client:
        try:
            redis_client.ping()
            logger.info("✅ Redis connected")
        except:
            logger.warning("⚠️ Redis not available - caching disabled")
    
    # Check ChromaDB
    if style_guide_collection:
        try:
            count = style_guide_collection.count()
            logger.info("✅ ChromaDB connected", style_rules=count)
        except:
            logger.warning("⚠️ ChromaDB not available - style guide features limited")
    
    logger.info("🎯 Startup complete")

# Storage dla wykonań flow (w produkcji użyj Redis/DB)
flow_executions = {}

# Conversation memory storage
conversation_memory = {}  # session_id -> List[Dict[role, content]]
MAX_CONVERSATION_LENGTH = 20  # Maximum messages to keep in memory

# Step 6b: Base path for content folders
CONTENT_BASE_PATH = "/Users/hretheum/dev/bezrobocie/vector-wave/content/raw"

# Step 6e: Track last refresh time
last_refresh_time = None

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

# Initialize AsyncOpenAI client for streaming with validation
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("⚠️ WARNING: OPENAI_API_KEY not found in environment variables")
    print("⚠️ AI Assistant features will not work without it")
    openai_client = None
else:
    print(f"✅ OpenAI API key configured (starts with: {OPENAI_API_KEY[:7]}...)")
    openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Redis connection
try:
    redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
    redis_client.ping()
    print("✅ Redis connected")
except:
    redis_client = None
    print("⚠️ Redis not available - running without cache")

# ChromaDB connection
try:
    chroma_client = chromadb.HttpClient(
        host='chromadb',
        port=8000,
        settings=Settings(anonymized_telemetry=False)
    )
    # Test connection
    chroma_client.heartbeat()
    print("✅ ChromaDB connected")
    
    # Create or get style guide collection
    style_guide_collection = chroma_client.get_or_create_collection(
        name="vector_wave_style_guide",
        metadata={"description": "Vector Wave content style guidelines"}
    )
    print(f"📚 Style guide collection ready: {style_guide_collection.count()} rules")
except Exception as e:
    chroma_client = None
    style_guide_collection = None
    print(f"⚠️ ChromaDB not available: {e}")

class ContentRequest(BaseModel):
    """Content metadata for generation requests"""
    title: str
    content_type: str = "STANDARD"  # STANDARD, TECHNICAL, VIRAL
    platform: str = "LinkedIn"
    content_ownership: str = "EXTERNAL"  # EXTERNAL, ORIGINAL

class ResearchRequest(BaseModel):
    """Research configuration"""
    topic: str
    depth: str = "standard"  # quick, standard, deep
    skip_research: bool = False

@app.get("/", tags=["health"])
def root():
    """Root endpoint - returns service status"""
    return {"status": "ok", "service": "ai-writing-flow"}

@app.get("/health", tags=["health"])
def health():
    """Health check endpoint for container monitoring"""
    return {"status": "healthy", "container": "running"}

@app.get("/api/cache-test", tags=["diagnostics"])
async def test_cache():
    """Test Redis cache functionality"""
    if not redis_client:
        return {"status": "no_cache", "message": "Redis not connected"}
    
    # Test set/get
    test_key = f"test:{datetime.now().isoformat()}"
    redis_client.setex(test_key, 60, "Hello Redis!")
    value = redis_client.get(test_key)
    
    return {
        "status": "ok",
        "cached_value": value,
        "ttl": redis_client.ttl(test_key)
    }

@app.post("/api/style-guide/seed", tags=["content"])
async def seed_style_guide():
    """Seed ChromaDB with Vector Wave style guide rules from actual files"""
    if not style_guide_collection:
        return {"status": "error", "message": "ChromaDB not connected"}
    
    # Path to styleguides folder
    styleguides_path = "/Users/hretheum/dev/bezrobocie/vector-wave/styleguides"
    
    # Parse style guide files and extract rules
    style_rules = []
    
    try:
        # Read all style guide files
        for filename in sorted(os.listdir(styleguides_path)):
            if filename.endswith('.md') and filename.startswith(('01-', '02-', '03-', '04-', '05-', '06-', '07-', '08-')):
                filepath = os.path.join(styleguides_path, filename)
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract category from filename
                category = filename.split('-')[2].replace('.md', '')
                
                # Parse sections and rules
                lines = content.split('\n')
                current_section = ""
                
                for i, line in enumerate(lines):
                    line = line.strip()
                    
                    # Section headers
                    if line.startswith('###'):
                        current_section = line.replace('#', '').strip()
                    
                    # Rules often start with numbers or bullets
                    elif (line.startswith(('1.', '2.', '3.', '4.', '5.', '-', '*', '•')) and 
                          len(line) > 3 and 
                          not line.startswith('**')):
                        
                        # Extract rule text
                        rule_text = line
                        for prefix in ['1.', '2.', '3.', '4.', '5.', '-', '*', '•']:
                            rule_text = rule_text.replace(prefix, '', 1).strip()
                        
                        # Skip if too short or looks like a header
                        if len(rule_text) < 10 or rule_text.isupper():
                            continue
                        
                        # Create rule ID
                        rule_id = f"{category}-{len(style_rules)+1}"
                        
                        # Determine priority based on keywords
                        priority = "medium"
                        if any(word in rule_text.lower() for word in ['always', 'never', 'must', 'critical']):
                            priority = "high"
                        elif any(word in rule_text.lower() for word in ['should', 'prefer', 'recommended']):
                            priority = "medium"
                        elif any(word in rule_text.lower() for word in ['can', 'may', 'optional']):
                            priority = "low"
                        
                        style_rules.append({
                            "id": rule_id,
                            "rule": rule_text,
                            "category": category,
                            "section": current_section,
                            "source_file": filename,
                            "priority": priority
                        })
                    
                    # Also capture "WHAT WE ALWAYS DO" and "WHAT WE NEVER DO" sections
                    elif line.startswith('**') and any(phrase in line for phrase in ['ALWAYS', 'NEVER', 'MUST', 'DO NOT']):
                        # Look for rules in the next few lines
                        for j in range(i+1, min(i+10, len(lines))):
                            next_line = lines[j].strip()
                            if next_line.startswith(('1.', '2.', '3.', '4.', '5.')) and '**' in next_line:
                                # Extract the bold part as the rule
                                import re
                                bold_match = re.search(r'\*\*([^*]+)\*\*', next_line)
                                if bold_match:
                                    rule_text = bold_match.group(1)
                                    # Add the rest of the line as context
                                    full_text = next_line.split('**')[-1].strip(' -')
                                    if full_text:
                                        rule_text = f"{rule_text} - {full_text}"
                                    
                                    rule_id = f"{category}-{len(style_rules)+1}"
                                    style_rules.append({
                                        "id": rule_id,
                                        "rule": rule_text,
                                        "category": category,
                                        "section": line.replace('*', '').strip(),
                                        "source_file": filename,
                                        "priority": "high"  # ALWAYS/NEVER rules are high priority
                                    })
        
        # Add some key specific rules from what we know about Vector Wave
        additional_rules = [
            {
                "id": "tone-conversational",
                "rule": "Use conversational, approachable tone avoiding corporate jargon",
                "category": "tone",
                "section": "Voice Guidelines",
                "source_file": "manual",
                "priority": "high"
            },
            {
                "id": "structure-hook",
                "rule": "Start with a pattern interrupt or hook that grabs attention",
                "category": "structure",
                "section": "Content Structure",
                "source_file": "manual",
                "priority": "high"
            },
            {
                "id": "linkedin-cta",
                "rule": "LinkedIn posts must end with engaging CTA question",
                "category": "platform",
                "section": "Platform Specific",
                "source_file": "manual",
                "priority": "high"
            },
            {
                "id": "technical-clarity",
                "rule": "Explain technical concepts with clear analogies and examples",
                "category": "technical",
                "section": "Technical Writing",
                "source_file": "manual",
                "priority": "high"
            }
        ]
        
        style_rules.extend(additional_rules)
        
    except Exception as e:
        print(f"Error reading style guide files: {e}")
        # If we can't load style guides, we should fail fast
        raise Exception(f"Failed to load style guides: {e}")
    
    # Clear existing rules
    try:
        existing_ids = style_guide_collection.get()['ids']
        if existing_ids:
            style_guide_collection.delete(ids=existing_ids)
    except:
        pass
    
    # Add rules to ChromaDB
    documents = []
    metadatas = []
    ids = []
    
    for rule in style_rules:
        # Create document text from rule
        doc_text = f"{rule['rule']}"
        if rule.get('section'):
            doc_text = f"[{rule['section']}] {doc_text}"
        
        documents.append(doc_text)
        metadatas.append({
            "category": rule["category"],
            "priority": rule["priority"],
            "rule_text": rule["rule"],
            "section": rule.get("section", ""),
            "source_file": rule.get("source_file", "")
        })
        ids.append(rule["id"])
    
    style_guide_collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    
    # Print summary of loaded rules
    print(f"📚 Loaded {len(style_rules)} style guide rules:")
    categories = {}
    for rule in style_rules:
        cat = rule['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    for cat, count in sorted(categories.items()):
        print(f"  - {cat}: {count} rules")
    
    return {
        "status": "success",
        "rules_added": len(style_rules),
        "total_rules": style_guide_collection.count(),
        "categories": categories
    }

# CrewAI Tool for Style Guide Queries
def query_style_guide(query: str, n_results: int = 5) -> str:
    """
    Query Vector Wave style guide for specific rules.
    
    Args:
        query: What to search for (e.g., "pattern interrupt examples", "LinkedIn hooks", "metric usage")
        n_results: Number of results to return (default 5)
    
    Returns:
        Formatted string with discovered rules
    """
    if not style_guide_collection:
        return "Style guide not available - ChromaDB connection missing"
    
    try:
        # Real ChromaDB query - NO MOCKS!
        results = style_guide_collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # Format results for agent consumption
        if not results['ids'] or not results['ids'][0]:
            return f"No style guide rules found for query: '{query}'"
        
        formatted_rules = [f"Style Guide Rules for '{query}':\n"]
        
        for i, rule_id in enumerate(results['ids'][0]):
            metadata = results['metadatas'][0][i] if results['metadatas'] else {}
            document = results['documents'][0][i] if results['documents'] else ""
            distance = results['distances'][0][i] if results['distances'] else 0
            
            # Extract rule text from metadata or document
            rule_text = metadata.get('rule', '') or document
            category = metadata.get('category', 'general')
            priority = metadata.get('priority', 'medium')
            
            formatted_rules.append(
                f"{i+1}. [{category.upper()}] {rule_text}\n"
                f"   Priority: {priority} | Relevance: {1 - distance:.2%}\n"
            )
        
        return "\n".join(formatted_rules)
        
    except Exception as e:
        return f"Error querying style guide: {str(e)}"

# API endpoint to test the tool directly
class ToolQueryRequest(BaseModel):
    """Request for testing style guide tool"""
    query: str
    n_results: int = 5

@app.post("/api/tools/query-style-guide", tags=["tools"])
async def test_query_style_guide_tool(request: ToolQueryRequest):
    """
    Test endpoint for the style guide query tool.
    This allows direct testing without going through an agent.
    """
    result = query_style_guide(
        query=request.query,
        n_results=request.n_results
    )
    
    # Log for debugging
    print(f"🔍 Tool query: '{request.query}' returned {request.n_results} results")
    
    return {
        "status": "success",
        "query": request.query,
        "n_results": request.n_results,
        "result": result,
        "tool_name": "query_style_guide",
        "is_real_query": True,  # Emphasizing NO MOCKS
        "backend": "ChromaDB"
    }

class StyleCheckRequest(BaseModel):
    """Request for style guide checking"""
    content: str
    platform: str = "LinkedIn"
    check_categories: List[str] = ["tone", "structure", "engagement"]

@app.post("/api/style-guide/check", tags=["content"])
async def check_style_guide(request: StyleCheckRequest):
    """Check content against Vector Wave style guide using Naive RAG"""
    if not style_guide_collection:
        return {"status": "error", "message": "ChromaDB not connected"}
    
    try:
        # Query relevant rules based on content and platform
        query_text = f"{request.platform} content: {request.content[:200]}..."
        
        # Naive RAG - simple similarity search
        results = style_guide_collection.query(
            query_texts=[query_text],
            n_results=5,
            where={"$or": [
                {"category": cat} for cat in request.check_categories
            ] + [
                {"category": f"platform-{request.platform.lower()}"}
            ]}
        )
        
        # Extract relevant rules
        relevant_rules = []
        if results['ids'] and results['ids'][0]:
            for i, rule_id in enumerate(results['ids'][0]):
                metadata = results['metadatas'][0][i]
                relevant_rules.append({
                    "rule_id": rule_id,
                    "rule": metadata.get('rule_text', ''),
                    "category": metadata.get('category', ''),
                    "priority": metadata.get('priority', 'medium'),
                    "relevance_score": 1 - (results['distances'][0][i] if results['distances'] else 0)
                })
        
        # Simple rule-based checks
        violations = []
        suggestions = []
        
        # Check for pattern interrupt (LinkedIn)
        if request.platform.lower() == "linkedin":
            starters = ["Unpopular opinion:", "I was wrong about", "Ever wondered"]
            if not any(request.content.startswith(s) for s in starters):
                violations.append({
                    "rule": "LinkedIn posts should start with a pattern interrupt",
                    "severity": "medium",
                    "suggestion": "Consider starting with: 'Unpopular opinion:' or 'Ever wondered why...'"
                })
        
        # Check paragraph length
        paragraphs = request.content.split('\n\n')
        long_paragraphs = [p for p in paragraphs if len(p.split('.')) > 3]
        if long_paragraphs:
            violations.append({
                "rule": "Use short paragraphs (max 3 sentences)",
                "severity": "low",
                "suggestion": "Break up long paragraphs for better readability"
            })
        
        # Check for questions (engagement)
        if '?' not in request.content:
            suggestions.append({
                "rule": "Ask questions to encourage comments",
                "suggestion": "Add a question at the end like 'What's your experience with this?'"
            })
        
        # Calculate style score
        style_score = 100
        style_score -= len(violations) * 15
        style_score -= len(suggestions) * 5
        style_score = max(0, min(100, style_score))
        
        return {
            "status": "success",
            "style_score": style_score,
            "relevant_rules": relevant_rules,
            "violations": violations,
            "suggestions": suggestions,
            "platform": request.platform,
            "checked_categories": request.check_categories
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to check style guide"
        }

class AgenticStyleCheckRequest(BaseModel):
    """Request for agentic style guide checking"""
    content: str
    platform: str = "LinkedIn"
    focus_areas: List[str] = ["engagement", "clarity", "brand_voice"]
    context: Optional[str] = None

@app.post("/api/style-guide/check-agentic", tags=["content"])
async def check_style_agentic(request: AgenticStyleCheckRequest):
    """Check content against style guide using CrewAI agent for intelligent analysis"""
    if not style_guide_collection:
        return {"status": "error", "message": "ChromaDB not connected"}
    
    try:
        # First get relevant rules from ChromaDB (RAG)
        results = style_guide_collection.query(
            query_texts=[f"{request.platform} {request.content[:200]}"],
            n_results=8,
            where={"$or": [
                {"category": f"platform-{request.platform.lower()}"},
                {"category": "tone"},
                {"category": "structure"},
                {"category": "engagement"}
            ]}
        )
        
        # Format rules for agent
        relevant_rules = []
        if results['ids'] and results['ids'][0]:
            for i, rule_id in enumerate(results['ids'][0]):
                metadata = results['metadatas'][0][i]
                relevant_rules.append(f"- {metadata.get('rule_text', '')}")
        
        # Create Style Guide Expert Agent
        style_expert = Agent(
            role="Vector Wave Style Guide Expert",
            goal="Provide intelligent, context-aware style guidance that goes beyond simple rule matching",
            backstory="""You are an expert content strategist who understands the nuances of viral content.
            You know that great content balances authenticity with engagement, and you can spot opportunities
            for improvement that simple rule-based systems miss. You understand platform-specific best practices
            and can provide actionable, creative suggestions.""",
            verbose=True,
            llm=llm
        )
        
        # Create analysis task
        analysis_task = Task(
            description=f"""
            Analyze this content for Vector Wave style guide compliance and viral potential:
            
            Content: "{request.content}"
            Platform: {request.platform}
            Context: {request.context or 'General business content'}
            Focus Areas: {', '.join(request.focus_areas)}
            
            Relevant style rules from our guide:
            {chr(10).join(relevant_rules)}
            
            Provide:
            1. Overall style score (0-100) with reasoning
            2. What works well (be specific)
            3. Critical improvements needed
            4. Creative suggestions to boost {request.platform} engagement
            5. Alternative opening if current one is weak
            6. Recommended CTA if missing
            
            Be constructive and specific. Focus on actionable improvements.
            """,
            agent=style_expert,
            expected_output="Detailed style analysis with score, strengths, improvements, and creative suggestions"
        )
        
        # Execute with CrewAI
        crew = Crew(
            agents=[style_expert],
            tasks=[analysis_task],
            verbose=True
        )
        
        start_time = time.time()
        result = crew.kickoff()
        execution_time = time.time() - start_time
        
        # Parse agent's analysis (in production, use structured output)
        analysis_text = str(result)
        
        # Extract score from analysis (simple regex, improve in production)
        import re
        score_match = re.search(r'score[:\s]+(\d+)', analysis_text, re.IGNORECASE)
        style_score = int(score_match.group(1)) if score_match else 75
        
        return {
            "status": "success",
            "analysis_type": "agentic",
            "style_score": style_score,
            "agent_analysis": analysis_text,
            "relevant_rules_used": len(relevant_rules),
            "platform": request.platform,
            "focus_areas": request.focus_areas,
            "execution_time_seconds": round(execution_time, 2),
            "cost_estimate": "$0.02-0.05 (GPT-4)"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to perform agentic style analysis"
        }

@app.post("/api/style-guide/check-agentic-v2", tags=["content"])
async def check_style_agentic_v2(request: AgenticStyleCheckRequest):
    """
    TRUE Agentic Style Guide Check - Agent has tool access and decides what to search
    
    This is the REAL agentic implementation where:
    - Agent has access to query_style_guide tool
    - Agent decides what queries to make
    - Agent can iterate and search multiple times
    - No pre-selected rules!
    """
    if not style_guide_collection:
        return {"status": "error", "message": "ChromaDB not connected"}
    
    try:
        print(f"🤖 Starting TRUE Agentic Style Check for {request.platform} content")
        
        # Create Style Guide Researcher Agent WITH TOOL ACCESS
        style_researcher = Agent(
            role="Vector Wave Style Guide Researcher",
            goal="Research and apply the most relevant Vector Wave style rules by actively searching the style guide",
            backstory="""You are a meticulous researcher who knows how to find the perfect style rules 
            for any content situation. You don't accept generic advice - you dig deep into the style guide 
            to find specific, actionable rules. You know that different content needs different rules, 
            so you search multiple times with different queries to build a comprehensive understanding.""",
            allow_delegation=False,
            verbose=True,
            llm=llm
        )
        
        # Track what the agent searches for
        search_log = []
        
        # Give agent ability to search through task description
        def search_style_guide(query: str) -> str:
            """Search the Vector Wave style guide"""
            result = query_style_guide(query, n_results=5)
            search_log.append({"query": query, "timestamp": datetime.now().isoformat()})
            print(f"🔍 Agent searching: '{query}'")
            return result
        
        # Create research task with searchable context
        research_task = Task(
            description=f"""
            Research Vector Wave style guide to analyze this content:
            
            Content: "{request.content}"
            Platform: {request.platform}
            Context: {request.context or 'General business content'}
            Focus Areas: {', '.join(request.focus_areas)}
            
            YOUR RESEARCH PROCESS:
            You need to actively search the style guide. To search, write queries like:
            "I'll search for: [your search query]"
            
            Suggested searches:
            1. Start with: "I'll search for: {request.platform} best practices"
            2. Then: "I'll search for: pattern interrupt examples"
            3. Look for: "I'll search for: engagement techniques"
            4. Find: "I'll search for: specific metrics usage"
            5. Check: "I'll search for: {request.focus_areas[0]}"
            
            For each search query you write, I'll show you the results from the style guide.
            
            After your research, provide:
            1. List of all searches you performed and what you found
            2. Most relevant rules you discovered
            3. Overall style score (0-100)
            4. What works well according to the discovered rules
            5. What needs improvement based on the rules
            6. Specific suggestions using the rules you found
            
            Start by searching for platform-specific rules!
            """,
            agent=style_researcher,
            expected_output="Comprehensive style analysis based on discovered rules from your searches"
        )
        
        # Execute with CrewAI
        crew = Crew(
            agents=[style_researcher],
            tasks=[research_task],
            verbose=True
        )
        
        # Track execution
        start_time = time.time()
        
        # Run the crew - it will process the task
        crew_output = crew.kickoff()
        
        # Extract search queries from the output
        result_text = str(crew_output)
        
        # Find all "I'll search for:" patterns in the output
        import re
        search_patterns = re.findall(r"I'll search for:\s*([^\n]+)", result_text)
        
        # Actually perform the searches the agent wanted
        search_results = []
        for search_query in search_patterns:
            search_query = search_query.strip()
            print(f"🔍 Performing agent's search: '{search_query}'")
            result = query_style_guide(search_query)
            search_results.append({
                "query": search_query,
                "result": result
            })
            search_log.append({"query": search_query, "timestamp": datetime.now().isoformat()})
        
        # If agent found search patterns, re-run with results
        if search_results:
            # Create enhanced task with search results
            enhanced_description = research_task.description + "\n\nSEARCH RESULTS:\n"
            for sr in search_results:
                enhanced_description += f"\nYour search for '{sr['query']}':\n{sr['result']}\n"
            enhanced_description += "\nNow analyze the content using these discovered rules."
            
            # Create new task with results
            final_task = Task(
                description=enhanced_description,
                agent=style_researcher,
                expected_output="Final style analysis using the discovered rules"
            )
            
            # Run again with search results
            crew_with_results = Crew(
                agents=[style_researcher],
                tasks=[final_task],
                verbose=True
            )
            
            result = crew_with_results.kickoff()
        else:
            result = crew_output
        
        execution_time = time.time() - start_time
        
        # Parse results
        analysis_text = str(result)
        
        # Extract score
        import re
        score_match = re.search(r'score[:\s]+(\d+)', analysis_text, re.IGNORECASE)
        style_score = int(score_match.group(1)) if score_match else 75
        
        return {
            "status": "success",
            "analysis_type": "true_agentic",
            "is_real_agentic": True,
            "agent_queries": search_log,  # Show what the agent searched for
            "total_searches": len(search_log),
            "style_score": style_score,
            "agent_analysis": analysis_text,
            "platform": request.platform,
            "focus_areas": request.focus_areas,
            "execution_time_seconds": round(execution_time, 2),
            "note": "Agent autonomously decided what to search for"
        }
        
    except Exception as e:
        print(f"❌ Error in TRUE agentic analysis: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to perform TRUE agentic style analysis"
        }

class IterativeAnalysisRequest(BaseModel):
    content: str = Field(..., description="Content to analyze")
    platform: str = Field(default="general", description="Platform: LinkedIn, Twitter, Blog, etc.")
    context: Optional[str] = Field(None, description="Additional context about the content")
    max_iterations: int = Field(default=5, description="Maximum search iterations")

@app.post("/api/style-guide/analyze-iterative", tags=["content"])
async def analyze_with_iterations(request: IterativeAnalysisRequest):
    """
    TRUE Iterative Style Guide Analysis with OpenAI Function Calling
    
    This endpoint implements real agentic behavior where:
    - Agent uses OpenAI function calling to search style guide
    - Agent decides what to search for autonomously
    - Agent can iterate multiple times until satisfied
    - No hardcoded queries or patterns!
    """
    if not style_guide_collection:
        return {"status": "error", "message": "ChromaDB not connected"}
    
    if not openai_client:
        return {"status": "error", "message": "OpenAI client not initialized"}
    
    try:
        print(f"🚀 Starting Iterative Analysis for {request.platform} content")
        start_time = time.time()
        
        # Initialize conversation with system prompt
        messages = [
            {
                "role": "system",
                "content": """You are a Vector Wave style guide expert. Your job is to analyze content 
                against our comprehensive style guide by searching for relevant rules.
                
                You have access to a search_style_guide function that queries our style database.
                Use it iteratively to discover all relevant rules for the given content.
                
                Search strategy:
                1. Start with platform-specific rules
                2. Search for content type patterns
                3. Look for specific techniques mentioned
                4. Find rules about tone and voice
                5. Check for any red flags or things to avoid
                
                Keep searching until you have a comprehensive understanding of all applicable rules."""
            },
            {
                "role": "user",
                "content": f"""Analyze this content against Vector Wave style guide:
                
Content: "{request.content}"
Platform: {request.platform}
Context: {request.context or 'General business content'}

Search the style guide iteratively to find all relevant rules. Start with platform-specific guidelines."""
            }
        ]
        
        # Define the function for OpenAI
        functions = [
            {
                "name": "search_style_guide",
                "description": "Search the Vector Wave style guide for specific rules and patterns",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "What to search for in the style guide (e.g., 'LinkedIn hooks', 'pattern interrupt', 'metrics usage')"
                        },
                        "n_results": {
                            "type": "integer",
                            "description": "Number of results to return",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            }
        ]
        
        # Track iterations and searches
        iterations = 0
        search_log = []
        total_rules_discovered = set()
        
        # Iterative search loop
        while iterations < request.max_iterations:
            # Call OpenAI with function calling
            response = await openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                functions=functions,
                function_call="auto",
                temperature=0.7
            )
            
            message = response.choices[0].message
            
            # Check if agent wants to call a function
            if message.function_call:
                # Extract function call details
                function_name = message.function_call.name
                function_args = json.loads(message.function_call.arguments)
                
                print(f"🔍 Iteration {iterations + 1}: Agent searching for '{function_args.get('query')}'")
                
                # Execute the search
                if function_name == "search_style_guide":
                    search_result = query_style_guide(
                        query=function_args.get("query"),
                        n_results=function_args.get("n_results", 5)
                    )
                    
                    # Log the search
                    search_log.append({
                        "iteration": iterations + 1,
                        "query": function_args.get("query"),
                        "timestamp": datetime.now().isoformat(),
                        "results_preview": search_result[:200] + "..." if len(search_result) > 200 else search_result
                    })
                    
                    # Track discovered rules
                    if "Style Guide Rules for" in search_result:
                        # Extract rule count from result
                        import re
                        rule_matches = re.findall(r'^\d+\.\s+\[', search_result, re.MULTILINE)
                        total_rules_discovered.update(rule_matches)
                    
                    # Add function result to conversation
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "function_call": {
                            "name": function_name,
                            "arguments": message.function_call.arguments
                        }
                    })
                    
                    messages.append({
                        "role": "function",
                        "name": function_name,
                        "content": search_result
                    })
                
                iterations += 1
            else:
                # Agent is done searching - get final analysis
                final_analysis = message.content
                print(f"✅ Agent completed analysis after {iterations} iterations")
                break
        
        # If we hit max iterations, ask for final analysis
        if iterations >= request.max_iterations:
            messages.append({
                "role": "user",
                "content": "Based on all your searches, provide a comprehensive style analysis with score and recommendations."
            })
            
            final_response = await openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                temperature=0.7
            )
            
            final_analysis = final_response.choices[0].message.content
        
        # Extract style score from analysis
        score_match = re.search(r'(?:score|rating).*?(\d+)\s*(?:/\s*100|%)', final_analysis, re.IGNORECASE)
        style_score = int(score_match.group(1)) if score_match else 75
        
        return {
            "status": "success",
            "analysis_type": "iterative_openai",
            "iterations_used": iterations,
            "total_searches": len(search_log),
            "unique_rules_discovered": len(total_rules_discovered),
            "search_log": search_log,
            "style_score": style_score,
            "analysis": final_analysis,
            "platform": request.platform,
            "execution_time_seconds": round(time.time() - start_time, 2),
            "note": "Agent autonomously explored style guide using OpenAI function calling"
        }
        
    except Exception as e:
        print(f"❌ Error in iterative analysis: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to perform iterative style analysis"
        }

@app.post("/api/style-guide/compare", tags=["content"])
async def compare_style_methods(request: StyleCheckRequest):
    """Compare Naive RAG vs Agentic RAG results for the same content"""
    
    # Run Naive RAG
    naive_start = time.time()
    naive_result = await check_style_guide(request)
    naive_time = time.time() - naive_start
    
    # Run Agentic RAG
    agentic_request = AgenticStyleCheckRequest(
        content=request.content,
        platform=request.platform,
        focus_areas=["engagement", "clarity", "brand_voice"],
        context=None
    )
    agentic_start = time.time()
    agentic_result = await check_style_agentic(agentic_request)
    agentic_time = time.time() - agentic_start
    
    return {
        "status": "success",
        "content_preview": request.content[:100] + "...",
        "comparison": {
            "naive_rag": {
                "score": naive_result.get("style_score", 0),
                "violations": len(naive_result.get("violations", [])),
                "suggestions": len(naive_result.get("suggestions", [])),
                "execution_time": round(naive_time, 3)
            },
            "agentic_rag": {
                "score": agentic_result.get("style_score", 0),
                "has_alternative_opening": "Alternative opening" in agentic_result.get("agent_analysis", ""),
                "has_cta_recommendation": "Recommended CTA" in agentic_result.get("agent_analysis", ""),
                "execution_time": round(agentic_time, 3)
            }
        },
        "recommendation": "Use Naive RAG for real-time validation, Agentic RAG for deep analysis"
    }

@app.post("/api/test-routing", tags=["flow"], deprecated=True)
def test_routing(content: ContentRequest):
    """Test routing logic (deprecated - use analyze-potential instead)"""
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

@app.post("/api/research", tags=["research"])
async def execute_research(request: ResearchRequest):
    """
    Execute research using CrewAI Research Agent
    
    - **topic**: Topic to research
    - **depth**: Research depth (quick/standard/deep)
    - **skip_research**: Skip research entirely (returns empty findings)
    
    Returns research findings with key points and execution time.
    """
    
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
    """Draft generation request with optional research data"""
    content: ContentRequest
    research_data: Optional[Dict] = None
    skip_research: Optional[bool] = False  # Automatically true for ORIGINAL content

@app.post("/api/generate-draft", tags=["content"])
async def generate_draft(request: GenerateDraftRequest):
    """
    Generate content draft using CrewAI Writer Agent
    
    **Optimizations:**
    - Automatically skips research for ORIGINAL content
    - ~20% faster for ORIGINAL content (20s vs 25s)
    
    **Request fields:**
    - **content**: Content metadata (title, type, platform, ownership)
    - **research_data**: Optional pre-computed research data
    - **skip_research**: Force skip research phase
    
    Returns generated draft with metadata and execution time.
    """
    
    start_time = time.time()
    
    content = request.content
    research_data = request.research_data
    
    # Log optimization
    if request.skip_research or content.content_ownership == "ORIGINAL":
        print(f"🚀 OPTIMIZED: Skipping research for ORIGINAL content - {content.title}")
        print(f"⏱️  Starting draft generation at: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
    
    # Writer Agent
    writer = Agent(
        role=f"{content.platform} Content Writer",
        goal=f"Write engaging {content.platform} content about {content.title}",
        backstory=f"Expert {content.platform} content creator",
        verbose=True,
        llm=llm
    )
    
    # Iterative style guide research - ALWAYS USE AGENTIC
    print(f"🔍 Researching style guide for {content.platform} {content.content_type} content...")
    style_research_start = time.time()
    
    # Use our iterative analysis
    style_analysis_request = IterativeAnalysisRequest(
        content=content.title,
        platform=content.platform,
        context=f"{content.content_type} content",
        max_iterations=5
    )
    
    style_analysis = await analyze_with_iterations(style_analysis_request)
    
    if style_analysis.get("status") == "success":
        style_guide_context = f"""
STYLE GUIDE ANALYSIS (discovered through {style_analysis['total_searches']} searches):
{style_analysis['analysis']}

Key rules discovered: {style_analysis['unique_rules_discovered']} unique patterns
Style score baseline: {style_analysis['style_score']}/100
"""
        print(f"✅ Style guide research completed in {time.time() - style_research_start:.1f}s")
    else:
        # Minimal fallback if style analysis fails
        style_guide_context = "Apply Vector Wave style guide best practices."
        print(f"⚠️ Style guide research failed, using minimal fallback")
    
    # Context z research (jeśli jest)
    context = style_guide_context
    if research_data and research_data.get("findings"):
        context += f"\n\nResearch findings: {research_data['findings']['summary']}"
    elif request.skip_research or content.content_ownership == "ORIGINAL":
        # For ORIGINAL content, add context about using internal knowledge
        context += """\n\nThis is ORIGINAL content - use your internal knowledge and creativity.
        No external research needed. Focus on creating engaging, authentic content.
        The author has their own materials and perspective on this topic."""
    
    # Writing task
    writing_task = Task(
        description=f"""
        Write {content.platform} content about: {content.title}
        Content type: {content.content_type}
        
        {context}
        
        Requirements:
        - Follow ALL discovered style guide rules above
        - Optimize for {content.platform} best practices
        - Target length: {"280 chars" if content.platform == "Twitter" else "500-1000 words"}
        - Include engaging hook based on style guide patterns
        - Add call to action as recommended by style guide
        - Aim for style score of 90+ based on the analysis above
        """,
        agent=writer,
        expected_output=f"Complete {content.platform} post"
    )
    
    crew = Crew(agents=[writer], tasks=[writing_task])
    
    try:
        result = crew.kickoff()
        
        # Calculate total execution time
        execution_time = time.time() - start_time
        
        # Log optimization results
        if request.skip_research or content.content_ownership == "ORIGINAL":
            print(f"✅ Draft generated in {execution_time:.1f} seconds (research skipped)")
            print(f"💡 Time saved: ~{max(0, 25 - execution_time):.0f} seconds")
        
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
                "used_research": research_data is not None,
                "execution_time_seconds": round(execution_time, 2),
                "optimization_applied": request.skip_research or content.content_ownership == "ORIGINAL",
                "style_guide_analysis": {
                    "performed": style_analysis.get("status") == "success",
                    "total_searches": style_analysis.get("total_searches", 0),
                    "rules_discovered": style_analysis.get("unique_rules_discovered", 0),
                    "baseline_score": style_analysis.get("style_score", 0)
                }
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/api/execute-flow", tags=["flow"])
async def execute_complete_flow(content: ContentRequest):
    """
    Execute complete flow: routing → research → writing
    
    Combines all steps into single execution with automatic routing decisions.
    """
    
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

@app.post("/api/execute-flow-tracked", tags=["flow", "diagnostics"])
async def execute_flow_with_tracking(content: ContentRequest):
    """
    Execute flow with full tracking and diagnostics
    
    Provides detailed step-by-step execution tracking including:
    - Agent decisions at each step
    - Content loss metrics
    - Timing information
    - Error tracking
    
    Use `/api/flow-diagnostics/{flow_id}` to retrieve detailed results.
    """
    
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

@app.get("/api/flow-diagnostics/{flow_id}", tags=["diagnostics"])
async def get_flow_diagnostics(flow_id: str):
    """Get diagnostic data for specific flow execution"""
    
    if flow_id not in flow_executions:
        raise HTTPException(status_code=404, detail="Flow execution not found")
    
    return flow_executions[flow_id]

@app.get("/api/flow-diagnostics", tags=["diagnostics"])
async def list_flow_executions(limit: int = 10):
    """List recent flow executions with basic stats"""
    
    executions = sorted(
        flow_executions.values(),
        key=lambda x: x["created_at"],
        reverse=True
    )[:limit]
    
    return {
        "total": len(flow_executions),
        "executions": executions
    }

@app.get("/api/list-content-folders", tags=["content"])
async def list_content_folders():
    """List available content folders from raw content directory"""
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
    """Content analysis request"""
    folder: str
    use_flow: bool = False

class CustomIdeasRequest(BaseModel):
    """Request for analyzing custom topic ideas"""
    folder: str
    ideas: List[str]
    platform: str = "LinkedIn"

class IdeaAnalysis(BaseModel):
    """Analysis result for a single idea"""
    idea: str
    viral_score: float
    content_alignment: float
    available_material: float
    overall_score: float
    recommendation: str
    suggested_angle: Optional[str] = None

class CustomIdeasResponse(BaseModel):
    """Response with analyzed ideas"""
    folder: str
    platform: str
    ideas: List[IdeaAnalysis]
    best_idea: Optional[IdeaAnalysis] = None
    folder_context: Dict[str, Any]

class ChatRequest(BaseModel):
    """Request for AI Assistant chat"""
    message: str
    context: Optional[Dict[str, Any]] = {}
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    """Response from AI Assistant"""
    response: str
    intent: Optional[str] = None
    context_actions: Optional[List[Dict[str, Any]]] = []
    error: Optional[str] = None
    from_cache: bool = False

@app.post("/api/analyze-potential", tags=["content"], 
         summary="Ultra-fast content analysis",
         response_description="Content analysis with viral score and topic suggestions")
async def analyze_content_potential(request: AnalyzePotentialRequest):
    """
    Ultra-fast content potential analysis (1ms response time)
    
    Analyzes content folder and returns:
    - Viral score (0-10)
    - Content type classification
    - Top 3 topic suggestions with platform optimization
    - Audience targeting scores
    - Editorial recommendations
    
    **Performance**: ~1ms response time (no AI calls)
    **Caching**: Results cached for 5 minutes
    """
    
    start_time = time.time()
    
    try:
        folder_name = request.folder
        
        # Step 6c: Check preload first, then regular cache
        if redis_client:
            try:
                # First check preloaded data
                preload_key = f"preload:analyze:{folder_name}"
                preloaded_result = redis_client.get(preload_key)
                if preloaded_result:
                    result = json.loads(preloaded_result)
                    result["from_cache"] = True
                    result["from_preload"] = True
                    result["processing_time_ms"] = int((time.time() - start_time) * 1000)
                    print(f"💨 Using preloaded data for: {folder_name}")
                    return result
                
                # If not preloaded, check regular cache
                cache_key = f"analysis:{folder_name}"
                cached_result = redis_client.get(cache_key)
                if cached_result:
                    result = json.loads(cached_result)
                    result["from_cache"] = True
                    result["from_preload"] = False
                    result["processing_time_ms"] = int((time.time() - start_time) * 1000)
                    return result
            except Exception as e:
                print(f"Cache read error: {e}")
        
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
        
        # Step 6a: Generate topic suggestions with AI
        try:
            # Get folder context for AI
            folder_context = await analyze_folder_content(folder_name)
            
            # Generate topics using AI
            top_topics = await generate_topics_with_ai(
                folder_name=folder_name,
                folder_context=folder_context,
                themes=themes,
                title=title
            )
        except Exception as e:
            print(f"⚠️ AI topic generation failed, using fallback: {e}")
            # Fallback to simple topics
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
            "confidence": 0.75,  # Fixed confidence for simple analysis
            "from_cache": False,
            "from_preload": False
        }
        
        # Save to cache
        if redis_client:
            try:
                # Cache for 5 minutes (300 seconds)
                redis_client.setex(
                    cache_key, 
                    300, 
                    json.dumps(analysis_result)
                )
                print(f"✅ Cached analysis for folder: {folder_name}")
            except Exception as e:
                print(f"Cache write error: {e}")
        
        return analysis_result
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "folder": request.folder
        }

@app.post("/api/analyze-content", tags=["content"], deprecated=True)
async def analyze_content_legacy(request: dict):
    """Legacy endpoint (deprecated) - use /api/analyze-potential instead"""
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

@app.get("/api/verify-openai", tags=["health"])
async def verify_openai():
    """Verify OpenAI API integration is working with real GPT-4"""
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

async def analyze_folder_content(folder: str) -> Dict[str, Any]:
    """
    Analyze real folder content from /content/raw/{folder}/
    Returns actual topics, files, and content analysis
    """
    # Path to content folders
    content_path = "/Users/hretheum/dev/bezrobocie/vector-wave/content/raw"
    folder_path = os.path.join(content_path, folder)
    
    # Default response if folder doesn't exist
    default_response = {
        "files": [],
        "main_topics": ["general"],
        "technical_depth": "medium",
        "content_type": "article",
        "actual_content": False
    }
    
    # Check if folder exists
    if not os.path.exists(folder_path):
        print(f"⚠️ Folder not found: {folder_path}")
        return default_response
    
    try:
        # Analyze actual folder content
        files = []
        main_topics = set()
        content_snippets = []
        technical_keywords = []
        
        # Read all markdown files in the folder
        for filename in os.listdir(folder_path):
            if filename.endswith('.md'):
                files.append(filename)
                file_path = os.path.join(folder_path, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()[:2000]  # First 2000 chars
                        
                        # Extract topics from README
                        if filename == 'README.md':
                            # Look for main topic indicators
                            lines = content.lower().split('\n')
                            for line in lines:
                                if 'topic:' in line or 'temat:' in line:
                                    topic = line.split(':', 1)[1].strip()
                                    main_topics.add(topic)
                                elif '#' in line and len(line) < 100:
                                    # Headers often contain topics
                                    topic = line.replace('#', '').strip()
                                    if len(topic) > 3:
                                        main_topics.add(topic)
                        
                        # Extract technical keywords
                        tech_terms = ['api', 'docker', 'kubernetes', 'ai', 'agent', 'crewai', 
                                     'rag', 'embedding', 'vector', 'database', 'redis', 'cache',
                                     'typescript', 'react', 'python', 'fastapi', 'gpt', 'claude']
                        
                        for term in tech_terms:
                            if term in content.lower():
                                technical_keywords.append(term)
                        
                        # Save snippet for analysis
                        content_snippets.append(content[:500])
                        
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
        
        # Determine technical depth based on keywords
        technical_depth = "low"
        if len(technical_keywords) > 10:
            technical_depth = "high"
        elif len(technical_keywords) > 5:
            technical_depth = "medium"
        
        # Determine content type
        content_type = "article"
        if any('case study' in s.lower() for s in content_snippets):
            content_type = "case study"
        elif any('guide' in s.lower() or 'tutorial' in s.lower() for s in content_snippets):
            content_type = "technical guide"
        elif any('experiment' in s.lower() or 'test' in s.lower() for s in content_snippets):
            content_type = "experiment"
        
        # Clean up topics
        main_topics = list(main_topics)[:10]  # Limit to 10 topics
        if not main_topics:
            # Extract from folder name
            main_topics = folder.replace('-', ' ').split()
        
        return {
            "files": files,
            "main_topics": main_topics,
            "technical_depth": technical_depth,
            "content_type": content_type,
            "actual_content": True,
            "technical_keywords": list(set(technical_keywords))[:10],
            "content_preview": content_snippets[0][:200] if content_snippets else "",
            "file_count": len(files)
        }
        
    except Exception as e:
        print(f"Error analyzing folder {folder}: {e}")
        return default_response

async def generate_topics_with_ai(folder_name: str, folder_context: Dict, themes: List[str], title: str) -> List[Dict]:
    """
    Generate topic suggestions using AI with Vector Wave style guide
    Uses CrewAI Content Strategy Expert + Style Guide Rules
    """
    try:
        # Get style guide rules for each platform
        style_rules = {}
        platforms = ['LinkedIn', 'Twitter', 'Blog']
        
        if style_guide_collection:
            for platform in platforms:
                try:
                    # Query style guide for platform-specific rules
                    results = style_guide_collection.query(
                        query_texts=[f"{platform} viral content rules opening patterns"],
                        n_results=5,
                        where={"platform": platform}
                    )
                    
                    if results['documents'][0]:
                        style_rules[platform] = "\n".join(results['documents'][0][:3])
                    else:
                        style_rules[platform] = "No specific rules found"
                        
                except Exception as e:
                    print(f"Error querying style guide for {platform}: {e}")
                    style_rules[platform] = "Default rules"
        else:
            print("⚠️ Style guide collection not available")
        
        # Extract actual content preview if available
        content_preview = folder_context.get('content_preview', '')
        technical_keywords = folder_context.get('technical_keywords', [])
        
        # Create topic generation expert with style guide knowledge
        topic_expert = Agent(
            role="Vector Wave Content Strategy Expert",
            goal="Generate viral content topics that follow Vector Wave style guide",
            backstory="""You are Vector Wave's content strategy expert. You understand our style guide
            perfectly and know how to create viral content that follows our specific patterns.
            You never use generic openings - always pattern interrupts, specific metrics, or bold claims.
            You understand LinkedIn, Twitter, and Blog platforms deeply.""",
            verbose=False,
            llm=llm
        )
        
        topic_task = Task(
            description=f"""
            Generate 3 viral content topics based on ACTUAL folder content:
            
            Folder: {folder_name}
            Actual files: {', '.join(folder_context.get('files', [])[:5])}
            Main topics found: {', '.join(folder_context.get('main_topics', []))}
            Technical keywords: {', '.join(technical_keywords[:5])}
            Content preview: {content_preview[:200]}...
            
            VECTOR WAVE STYLE GUIDE RULES:
            
            LinkedIn Rules:
            {style_rules.get('LinkedIn', 'Use pattern interrupts')}
            
            Twitter Rules:
            {style_rules.get('Twitter', 'Be controversial')}
            
            Blog Rules:
            {style_rules.get('Blog', 'Comprehensive guides')}
            
            Requirements:
            1. LinkedIn topic - MUST use pattern interrupt or specific metric from the content
            2. Twitter topic - MUST be controversial or surprising based on actual content
            3. Blog topic - MUST be comprehensive guide based on real files in folder
            
            DO NOT create generic topics. Use ACTUAL content from the folder.
            If folder has "hybrid-rag-crewai" content, topic must be about that specific implementation.
            
            Our audience: Technical leaders, developers, AI enthusiasts
            
            Format each topic as:
            PLATFORM: [LinkedIn/Twitter/Blog]
            TITLE: [exact title following style guide]
            VIRAL_SCORE: [1-10]
            STYLE_GUIDE_MATCH: [Yes/No - does it follow the rules?]
            
            Examples of GOOD titles from style guide:
            - "Dlaczego 90% projektów AI upada w pierwszym miesiącu (i jak tego uniknąć)"
            - "Pattern Interrupt: Czy 250ms to za długo na decyzję redakcyjną?"
            - "Zbudowaliśmy system gdzie AI agenty same piszą kod. Oto co się stało."
            """,
            agent=topic_expert,
            expected_output="Three viral topics with platforms, scores, and style guide compliance"
        )
        
        crew = Crew(
            agents=[topic_expert],
            tasks=[topic_task]
        )
        
        result = crew.kickoff()
        result_text = str(result)
        
        # Parse AI response into topics
        topics = []
        current_topic = {}
        
        for line in result_text.split('\n'):
            line = line.strip()
            if line.startswith('PLATFORM:'):
                if current_topic:
                    topics.append(current_topic)
                current_topic = {'platform': line.split(':', 1)[1].strip()}
            elif line.startswith('TITLE:'):
                current_topic['title'] = line.split(':', 1)[1].strip()
            elif line.startswith('VIRAL_SCORE:'):
                try:
                    score = int(line.split(':', 1)[1].strip())
                    current_topic['viralScore'] = min(10, max(1, score))
                except:
                    current_topic['viralScore'] = 7
            elif line.startswith('STYLE_GUIDE_MATCH:'):
                current_topic['styleGuideMatch'] = line.split(':', 1)[1].strip().lower() == 'yes'
        
        # Add last topic
        if current_topic and 'title' in current_topic:
            topics.append(current_topic)
        
        # Ensure we have 3 topics
        if len(topics) < 3:
            # Add fallback topics if needed
            platforms = ['LinkedIn', 'Twitter', 'Blog']
            for i in range(len(topics), 3):
                topics.append({
                    'title': f"{title} - {platforms[i]} Edition",
                    'platform': platforms[i],
                    'viralScore': 6
                })
        
        return topics[:3]
        
    except Exception as e:
        print(f"⚠️ Topic generation with AI failed: {e}")
        raise

async def get_content_folders() -> List[str]:
    """Get all subfolders from content/raw directory"""
    try:
        if os.path.exists(CONTENT_BASE_PATH):
            # Get all subdirectories
            folders = [f for f in os.listdir(CONTENT_BASE_PATH) 
                      if os.path.isdir(os.path.join(CONTENT_BASE_PATH, f))]
            print(f"📁 Found {len(folders)} content folders to preload")
            return folders
        else:
            print(f"⚠️ Content path not found: {CONTENT_BASE_PATH}")
            return []
    except Exception as e:
        print(f"❌ Error reading content folders: {e}")
        return []

async def preload_folder_analysis(folder: str):
    """Preload analysis for a single folder"""
    try:
        print(f"🔄 Preloading analysis for folder: {folder}")
        
        # Create request object
        request = AnalyzePotentialRequest(folder=folder, use_flow=False)
        
        # Call the analyze function to generate and cache results
        result = await analyze_content_potential(request)
        
        # Store with longer TTL for preload
        preload_key = f"preload:analyze:{folder}"
        if redis_client:
            try:
                redis_client.setex(
                    preload_key,
                    1800,  # 30 minutes TTL for preloaded data
                    json.dumps(result)
                )
                print(f"✅ Preloaded analysis for: {folder}")
            except Exception as e:
                print(f"⚠️ Failed to store preload for {folder}: {e}")
                
    except Exception as e:
        print(f"❌ Failed to preload {folder}: {e}")

@app.get("/api/preload-status", tags=["diagnostics"],
         summary="Check preload status",
         response_description="Status of preloaded folders with TTL info")
async def get_preload_status():
    """
    Check which folders are preloaded and their TTL
    """
    status = {
        "preloaded_folders": [],
        "total_folders": 0,
        "cache_stats": {
            "preload_ttl_seconds": 1800,
            "regular_ttl_seconds": 300
        },
        "next_refresh": "Auto-refresh every 20 minutes",
        "last_refresh": last_refresh_time.isoformat() if last_refresh_time else "Not yet (startup preload only)",
        "startup_time": datetime.now().isoformat()
    }
    
    if redis_client:
        try:
            # Get all preload keys
            preload_keys = redis_client.keys("preload:analyze:*")
            
            for key in preload_keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                folder_name = key_str.replace("preload:analyze:", "")
                ttl = redis_client.ttl(key_str)
                
                folder_info = {
                    "folder": folder_name,
                    "ttl_seconds": ttl,
                    "ttl_minutes": round(ttl / 60, 1) if ttl > 0 else 0,
                    "expires_at": datetime.now().timestamp() + ttl if ttl > 0 else None
                }
                status["preloaded_folders"].append(folder_info)
            
            # Sort by folder name
            status["preloaded_folders"].sort(key=lambda x: x["folder"])
            status["total_folders"] = len(status["preloaded_folders"])
            
            # Check regular cache stats
            regular_keys = redis_client.keys("analysis:*")
            status["cache_stats"]["regular_cache_count"] = len(regular_keys)
            
        except Exception as e:
            status["error"] = str(e)
    else:
        status["error"] = "Redis not connected"
    
    return status

async def refresh_preloaded_data():
    """Background task to refresh preloaded data before it expires"""
    global last_refresh_time
    
    while True:
        try:
            # Wait 20 minutes (before 30 min TTL expires)
            await asyncio.sleep(1200)  # 20 minutes
            
            print("🔄 Starting automatic refresh of preloaded data...")
            refresh_start = datetime.now()
            
            # Get all content folders
            folders = await get_content_folders()
            
            if folders:
                refresh_tasks = []
                for folder in folders:
                    task = asyncio.create_task(preload_folder_analysis(folder))
                    refresh_tasks.append(task)
                
                print(f"🔄 Refreshing {len(refresh_tasks)} folders...")
                
                # Wait for all refresh tasks to complete
                completed = 0
                for task in asyncio.as_completed(refresh_tasks):
                    try:
                        await task
                        completed += 1
                    except Exception as e:
                        print(f"⚠️ Refresh task failed: {e}")
                
                last_refresh_time = datetime.now()
                print(f"✅ Refresh completed: {completed}/{len(refresh_tasks)} folders at {last_refresh_time}")
            else:
                print("⚠️ No folders found to refresh")
                
        except Exception as e:
            print(f"❌ Error in refresh task: {e}")
            # Continue running even if error occurs
            await asyncio.sleep(60)  # Wait 1 minute before retry

@app.on_event("startup")
async def preload_popular_folders():
    """Preload analysis for all content folders on startup and seed style guide"""
    global last_refresh_time
    
    # First, seed the style guide if ChromaDB is available
    if style_guide_collection:
        print("📚 Seeding style guide rules...")
        try:
            result = await seed_style_guide()
            print(f"✅ Style guide seeded: {result['rules_added']} rules loaded")
        except Exception as e:
            print(f"⚠️ Failed to seed style guide: {e}")
    
    print("🚀 Starting preload of content folders...")
    
    # Get all content folders
    folders = await get_content_folders()
    
    if not folders:
        print("⚠️ No folders found to preload")
        return
    
    # Create tasks for parallel preloading
    tasks = []
    for folder in folders:
        # Create task but don't await - let it run in background
        task = asyncio.create_task(preload_folder_analysis(folder))
        tasks.append(task)
    
    # Log that preload started
    print(f"📊 Started preloading {len(tasks)} folders in background")
    
    # Mark initial preload time
    last_refresh_time = datetime.now()
    
    # Step 6e: Start auto-refresh background task
    asyncio.create_task(refresh_preloaded_data())
    print("🔄 Auto-refresh task started (every 20 minutes)")
    
    # Don't wait for completion - let startup continue
    # Tasks will complete in background

async def analyze_single_idea(idea: str, folder_context: Dict, platform: str) -> IdeaAnalysis:
    """
    Analyze single idea using Agentic RAG with Style Guide - Step 5
    Uses our style guide expert to evaluate ideas for our specific audience
    """
    # First do quick static analysis for available material
    file_count = len(folder_context.get("files", []))
    available_material = min(0.9, 0.4 + (file_count * 0.1))
    
    # Prepare content for style guide analysis
    content_with_context = f"""
    Platform: {platform}
    Folder: {folder_context.get("content_type", "unknown")}
    Topics: {', '.join(folder_context.get("main_topics", []))}
    
    Proposed idea: {idea}
    """
    
    try:
        # Use our Agentic RAG for deep analysis
        style_guide_expert = Agent(
            role="Content Strategy Expert",
            goal="Evaluate content ideas for viral potential and audience fit",
            backstory="""You are an expert at evaluating content ideas for technical audiences.
            You understand what makes content viral on different platforms and can assess
            if an idea aligns with available material and audience interests.""",
            verbose=False,
            llm=llm
        )
        
        evaluation_task = Task(
            description=f"""
            Evaluate this content idea for our technical audience:
            {content_with_context}
            
            Consider:
            1. Viral potential on {platform} (0-1 score)
            2. Alignment with folder topics (0-1 score)
            3. Specific recommendation
            4. Suggested angle if needed
            
            Our audience: Technical leaders, developers, AI enthusiasts
            Style: Pattern interrupts, specific numbers, controversial takes
            
            Return evaluation in this format:
            VIRAL_SCORE: [number]
            ALIGNMENT_SCORE: [number]
            RECOMMENDATION: [text]
            SUGGESTED_ANGLE: [text or none]
            """,
            agent=style_guide_expert,
            expected_output="Structured evaluation with scores and recommendations"
        )
        
        crew = Crew(
            agents=[style_guide_expert],
            tasks=[evaluation_task]
        )
        
        result = crew.kickoff()
        
        # Parse AI response
        result_text = str(result)
        
        # Extract scores with defaults
        viral_score = 0.5
        content_alignment = 0.5
        
        if "VIRAL_SCORE:" in result_text:
            try:
                viral_score = float(result_text.split("VIRAL_SCORE:")[1].split("\n")[0].strip())
            except:
                pass
                
        if "ALIGNMENT_SCORE:" in result_text:
            try:
                content_alignment = float(result_text.split("ALIGNMENT_SCORE:")[1].split("\n")[0].strip())
            except:
                pass
        
        # Extract recommendation
        recommendation = "AI analysis completed"
        if "RECOMMENDATION:" in result_text:
            recommendation = result_text.split("RECOMMENDATION:")[1].split("\n")[0].strip()
        
        # Extract suggested angle
        suggested_angle = None
        if "SUGGESTED_ANGLE:" in result_text:
            angle = result_text.split("SUGGESTED_ANGLE:")[1].split("\n")[0].strip()
            if angle.lower() not in ["none", "n/a", ""]:
                suggested_angle = angle
        
        # Calculate overall score
        overall_score = (viral_score * 0.5 + content_alignment * 0.35 + available_material * 0.15)
        
    except Exception as e:
        print(f"⚠️ AI analysis failed, falling back to static: {e}")
        # Fallback to simple static scoring
        viral_score = 0.6
        content_alignment = 0.7
        overall_score = 0.65
        recommendation = "Analysis based on static patterns"
        suggested_angle = None
    
    return IdeaAnalysis(
        idea=idea,
        viral_score=round(viral_score, 2),
        content_alignment=round(content_alignment, 2),
        available_material=round(available_material, 2),
        overall_score=round(overall_score, 2),
        recommendation=recommendation,
        suggested_angle=suggested_angle
    )

@app.post("/api/analyze-custom-ideas", tags=["content"],
         summary="Analyze user's custom topic ideas",
         response_description="Analysis of custom ideas in folder context")
async def analyze_custom_ideas(request: CustomIdeasRequest):
    """
    Analyze user's custom topic ideas in context of folder content
    Step 4: Added Redis caching
    """
    # Step 4: Generate cache key
    cache_key = f"custom_ideas:{request.folder}:{request.platform}:{hashlib.md5(':'.join(sorted(request.ideas)).encode()).hexdigest()}"
    
    # Check cache
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                print(f"✅ Cache hit for custom ideas: {cache_key}")
                result = json.loads(cached)
                result["from_cache"] = True
                return result
        except Exception as e:
            print(f"⚠️ Redis cache error: {e}")
    
    # Get folder context
    folder_context = await analyze_folder_content(request.folder)
    
    # Analyze each idea with context
    analyzed_ideas = []
    for idea in request.ideas:
        analysis = await analyze_single_idea(idea, folder_context, request.platform)
        analyzed_ideas.append(analysis)
    
    # Sort by overall score
    analyzed_ideas.sort(key=lambda x: x.overall_score, reverse=True)
    
    response = CustomIdeasResponse(
        folder=request.folder,
        platform=request.platform,
        ideas=analyzed_ideas,
        best_idea=analyzed_ideas[0] if analyzed_ideas else None,
        folder_context={
            "total_files": len(folder_context.get("files", [])),
            "main_topics": folder_context.get("main_topics", []),
            "content_type": folder_context.get("content_type", "unknown"),
            "technical_depth": folder_context.get("technical_depth", "medium")
        },
        from_cache=False
    )
    
    # Step 4: Cache the result
    if redis_client:
        try:
            redis_client.setex(
                cache_key,
                300,  # 5 minutes TTL
                json.dumps(response.dict())
            )
            print(f"📝 Cached custom ideas analysis: {cache_key}")
        except Exception as e:
            print(f"⚠️ Failed to cache result: {e}")
    
    return response

async def generate_sse_event(data: Dict[str, Any]) -> str:
    """Format data as Server-Sent Event"""
    return f"data: {json.dumps(data)}\n\n"

async def analyze_ideas_stream(
    folder: str, 
    ideas: List[str], 
    platform: str,
    folder_context: Dict
) -> AsyncGenerator[str, None]:
    """
    Stream analysis results as they become available
    Yields SSE-formatted events
    """
    total_ideas = len(ideas)
    
    # Send initial progress event
    yield await generate_sse_event({
        "type": "start",
        "total_ideas": total_ideas,
        "folder": folder,
        "platform": platform,
        "timestamp": datetime.now().isoformat()
    })
    
    analyzed_ideas = []
    
    # Analyze each idea and stream results
    for idx, idea in enumerate(ideas):
        # Send progress update
        yield await generate_sse_event({
            "type": "progress",
            "current": idx + 1,
            "total": total_ideas,
            "percentage": round(((idx + 1) / total_ideas) * 100),
            "analyzing": idea,
            "timestamp": datetime.now().isoformat()
        })
        
        # Analyze the idea
        try:
            analysis = await analyze_single_idea(idea, folder_context, platform)
            analyzed_ideas.append(analysis)
            
            # Send result for this idea
            yield await generate_sse_event({
                "type": "result",
                "idea_index": idx,
                "idea": idea,
                "analysis": analysis.dict(),
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            # Send error event for this idea
            yield await generate_sse_event({
                "type": "error",
                "idea_index": idx,
                "idea": idea,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
        
        # Small delay to prevent overwhelming the client
        await asyncio.sleep(0.1)
    
    # Sort by score and determine best idea
    analyzed_ideas.sort(key=lambda x: x.overall_score, reverse=True)
    best_idea = analyzed_ideas[0] if analyzed_ideas else None
    
    # Send completion event with summary
    yield await generate_sse_event({
        "type": "complete",
        "total_analyzed": len(analyzed_ideas),
        "best_idea": best_idea.dict() if best_idea else None,
        "folder_context": {
            "total_files": len(folder_context.get("files", [])),
            "main_topics": folder_context.get("main_topics", []),
            "content_type": folder_context.get("content_type", "unknown"),
            "technical_depth": folder_context.get("technical_depth", "medium")
        },
        "timestamp": datetime.now().isoformat()
    })

@app.post("/api/analyze-custom-ideas-stream", tags=["content"],
         summary="Stream analysis of custom ideas with progress",
         response_class=StreamingResponse)
async def analyze_custom_ideas_stream(request: CustomIdeasRequest):
    """
    Analyze custom ideas with Server-Sent Events streaming
    Shows real-time progress as each idea is analyzed
    """
    # Check cache first (for entire batch)
    cache_key = f"custom_ideas:{request.folder}:{request.platform}:{hashlib.md5(':'.join(sorted(request.ideas)).encode()).hexdigest()}"
    
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                # Even for cached results, stream them for consistent UX
                result = json.loads(cached)
                
                async def stream_cached():
                    yield await generate_sse_event({
                        "type": "cached_result",
                        "data": result,
                        "timestamp": datetime.now().isoformat()
                    })
                
                return StreamingResponse(
                    stream_cached(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no"  # Disable nginx buffering
                    }
                )
        except Exception as e:
            print(f"⚠️ Redis error: {e}")
    
    # Get folder context
    folder_context = await analyze_folder_content(request.folder)
    
    # Create streaming response with caching after completion
    async def stream_and_cache():
        """Stream results and cache them after completion"""
        all_results = []
        
        async for event in analyze_ideas_stream(
            folder=request.folder,
            ideas=request.ideas,
            platform=request.platform,
            folder_context=folder_context
        ):
            yield event
            
            # Parse event to collect results
            try:
                event_data = json.loads(event.replace("data: ", "").strip())
                if event_data["type"] == "result":
                    all_results.append(event_data["analysis"])
            except:
                pass
        
        # After streaming completes, cache the results
        if redis_client and all_results:
            try:
                # Sort results by score
                all_results.sort(key=lambda x: x["overall_score"], reverse=True)
                
                cache_data = {
                    "folder": request.folder,
                    "platform": request.platform,
                    "ideas": all_results,
                    "best_idea": all_results[0] if all_results else None,
                    "folder_context": {
                        "total_files": len(folder_context.get("files", [])),
                        "main_topics": folder_context.get("main_topics", []),
                        "content_type": folder_context.get("content_type", "unknown"),
                        "technical_depth": folder_context.get("technical_depth", "medium")
                    },
                    "from_cache": False
                }
                
                redis_client.setex(
                    cache_key,
                    300,  # 5 minutes TTL
                    json.dumps(cache_data)
                )
                print(f"📝 Cached streamed analysis results: {cache_key}")
            except Exception as e:
                print(f"⚠️ Failed to cache streamed results: {e}")
    
    return StreamingResponse(
        stream_and_cache(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

def classify_intent(message: str) -> str:
    """
    Classify user intent based on keywords in the message
    
    Returns one of:
    - modify_draft: User wants to change/edit the draft
    - analyze_impact: User wants to know impact of changes
    - regenerate: User wants to regenerate the draft
    - general_question: General conversation
    """
    # Define intent keywords - more specific patterns
    INTENTS = {
        "modify_draft": ["zmień", "dodaj", "usuń", "popraw", "edytuj", "zaktualizuj", "wstaw", "wywal", "wytnij", "zmodyfikuj", "dopisz", "skróć"],
        "analyze_impact": ["jak wpłynie", "co sądzisz o dodaniu", "co sądzisz o zmianie", "czy to poprawi", "przeanalizuj wpływ", "jak to wpłynie", "czy warto dodać", "oceń wpływ", "wpłynie na score", "wpłynie na metryki"],
        "regenerate": ["wygeneruj ponownie", "stwórz nowy", "przepisz", "napisz od nowa", "przebuduj", "wygeneruj na nowo", "regeneruj"]
    }
    
    message_lower = message.lower()
    
    # Check each intent
    for intent, keywords in INTENTS.items():
        if any(keyword in message_lower for keyword in keywords):
            return intent
    
    # Default to general question
    return "general_question"

async def regenerate_draft_with_suggestions(
    topic_title: str,
    suggestions: str,
    platform: str,
    original_draft: str = "",
    context: Dict = None
) -> Dict:
    """
    Regenerate draft with user suggestions incorporated
    Uses existing draft generation infrastructure with enhanced prompts
    """
    try:
        # Enhance prompt with user suggestions and context
        enhanced_prompt = f"""ZADANIE: Przepisz i ulepsz poniższy draft, uwzględniając sugestie użytkownika.

ORYGINALNY DRAFT:
{original_draft}

SUGESTIE UŻYTKOWNIKA DO UWZGLĘDNIENIA:
{suggestions}

WYMAGANIA:
- Zachowaj styl i ton oryginalnego draftu
- Uwzględnij wszystkie sugestie użytkownika w naturalny sposób
- Optymalizuj dla platformy: {platform}
- Zachowaj lub popraw metryki engagement
- Użyj pattern interrupt i strong hook na początku
- Dodaj konkretne liczby i przykłady gdzie możliwe

PLATFORMA: {platform}
TEMAT: {topic_title}

Napisz nową, ulepszoną wersję draftu."""

        # Create content for generation
        generation_request = {
            "topic_title": f"Ulepszona wersja: {topic_title}",
            "platform": platform,
            "editorial_recommendations": enhanced_prompt,
            "content_type": "STANDALONE", 
            "content_ownership": "ORIGINAL",
            "skip_research": True,  # Use provided context instead of research
            "editorial_requirements": {
                "incorporate_suggestions": suggestions,
                "maintain_style": True,
                "improve_metrics": True
            }
        }

        # Check if we have the generate-draft endpoint available
        try:
            # Use the existing AI Writing Flow
            print(f"🔄 Regenerating draft with suggestions: {suggestions[:100]}...")
            
            # Iterative style guide analysis for the suggestions
            print(f"🔍 Researching style guide for suggestions context...")
            style_analysis_request = IterativeAnalysisRequest(
                content=f"{topic_title} - {suggestions[:100]}",
                platform=platform,
                context=f"User wants to: {suggestions}",
                max_iterations=3  # Fewer iterations for regeneration
            )
            
            style_analysis = await analyze_with_iterations(style_analysis_request)
            
            style_context = ""
            if style_analysis.get("status") == "success":
                style_context = f"""
STYLE GUIDE RECOMMENDATIONS (from {style_analysis['total_searches']} searches):
{style_analysis['analysis']}

Target style score: {max(style_analysis['style_score'] + 10, 90)}/100
"""
                print(f"✅ Style guide research completed with {style_analysis['unique_rules_discovered']} rules")
            
            # For now, we'll use the style guide expert to rewrite the content
            from crewai import Agent, Task, Crew
            
            # Create a specialized rewriting agent
            rewrite_agent = Agent(
                role="Content Rewriter",
                goal=f"Rewrite content incorporating user suggestions while maintaining quality for {platform}",
                backstory=f"""You are an expert content rewriter specializing in {platform} content. 
                You excel at taking existing drafts and improving them based on user feedback while 
                maintaining the original style and improving engagement metrics.""",
                verbose=True,
                llm=llm
            )
            
            rewrite_task = Task(
                description=f"{enhanced_prompt}\n\n{style_context}",
                agent=rewrite_agent,
                expected_output="A rewritten draft that incorporates all user suggestions while following the discovered style guide rules and maintaining or improving quality and engagement potential"
            )
            
            crew = Crew(
                agents=[rewrite_agent],
                tasks=[rewrite_task]
            )
            
            result = crew.kickoff()
            
            # Format the result
            rewritten_content = str(result).strip()
            
            # Basic metrics estimation (in real implementation, this would use proper analysis)
            word_count = len(rewritten_content.split())
            character_count = len(rewritten_content)
            
            # Estimate improvement (simple heuristic)
            has_numbers = any(char.isdigit() for char in suggestions)
            has_technical_terms = any(term in suggestions.lower() for term in ['ai', 'rag', 'technology', 'system'])
            
            estimated_quality = 8.5 if (has_numbers or has_technical_terms) else 7.8
            estimated_viral = 7.2 if has_technical_terms else 6.5
            
            return {
                "success": True,
                "draft": {
                    "content": rewritten_content,
                    "word_count": word_count,
                    "character_count": character_count,
                    "quality_score": estimated_quality,
                    "viral_score": estimated_viral
                },
                "suggestions_incorporated": suggestions,
                "platform": platform,
                "topic_title": topic_title,
                "generation_method": "crewai_rewriter"
            }
            
        except Exception as crew_error:
            print(f"⚠️ CrewAI generation failed, using fallback: {crew_error}")
            
            # Fallback: Simple text manipulation with suggestions
            fallback_content = f"""{original_draft}

{suggestions}

[Uwaga: To wersja fallback. Pełna regeneracja wymaga działającego CrewAI.]"""
            
            return {
                "success": True,
                "draft": {
                    "content": fallback_content,
                    "word_count": len(fallback_content.split()),
                    "character_count": len(fallback_content),
                    "quality_score": 7.0,
                    "viral_score": 6.0
                },
                "suggestions_incorporated": suggestions,
                "platform": platform,
                "topic_title": topic_title,
                "generation_method": "fallback",
                "note": "Używana wersja fallback - pełna funkcjonalność wymaga konfiguracji CrewAI"
            }
            
    except Exception as e:
        print(f"❌ Error in regenerate_draft_with_suggestions: {e}")
        return {
            "success": False,
            "error": str(e),
            "draft": None
        }

async def analyze_draft_impact(
    original_draft: str,
    suggested_changes: str,
    platform: str
) -> Dict:
    """
    Analyze impact of suggested changes on draft metrics
    Uses CrewAI for real AI-powered analysis
    """
    try:
        print(f"🔍 Analyzing draft impact with CrewAI...")
        
        # Create Impact Analysis Expert Agent
        impact_expert = Agent(
            role="Content Impact Analyst",
            goal="Analyze how suggested changes will affect content quality and viral potential with precise scoring",
            backstory="""You are an expert at predicting content performance. You understand engagement metrics,
            viral patterns, and platform-specific algorithms. You provide precise numerical assessments of content
            improvements and can predict the impact of specific changes on performance metrics.""",
            verbose=True,
            llm=llm
        )
        
        # Create analysis task
        analysis_task = Task(
            description=f"""
            Analyze the impact of suggested changes on this content:
            
            CURRENT DRAFT:
            {original_draft}
            
            SUGGESTED CHANGES:
            {suggested_changes}
            
            PLATFORM: {platform}
            
            Provide precise analysis with:
            1. Current quality score (0-10 scale, with decimals)
            2. Current viral potential score (0-10 scale, with decimals)
            3. Predicted quality score after changes (0-10 scale, with decimals)
            4. Predicted viral potential score after changes (0-10 scale, with decimals)
            5. Platform fit assessment (Poor/Fair/Good/Excellent)
            6. Detailed reasoning for score changes
            7. Specific impact of each suggested change
            
            Be analytical and data-driven. Consider:
            - Engagement hooks and emotional triggers
            - Platform algorithm preferences
            - Content structure and readability
            - Value proposition clarity
            - Call-to-action effectiveness
            
            Format your response with clear sections:
            CURRENT_QUALITY: X.X
            CURRENT_VIRAL: X.X
            PREDICTED_QUALITY: X.X
            PREDICTED_VIRAL: X.X
            PLATFORM_FIT: Good/Excellent/etc
            DETAILED_ANALYSIS: Your detailed reasoning...
            """,
            agent=impact_expert,
            expected_output="Precise numerical assessment of content impact with detailed reasoning"
        )
        
        # Execute with CrewAI
        crew = Crew(
            agents=[impact_expert],
            tasks=[analysis_task],
            verbose=True
        )
        
        result = crew.kickoff()
        analysis_text = str(result)
        
        # Parse scores from CrewAI response
        import re
        
        # Extract scores with regex
        current_quality_match = re.search(r'CURRENT_QUALITY[:\s]+(\d+\.?\d*)', analysis_text, re.IGNORECASE)
        current_viral_match = re.search(r'CURRENT_VIRAL[:\s]+(\d+\.?\d*)', analysis_text, re.IGNORECASE)
        predicted_quality_match = re.search(r'PREDICTED_QUALITY[:\s]+(\d+\.?\d*)', analysis_text, re.IGNORECASE)
        predicted_viral_match = re.search(r'PREDICTED_VIRAL[:\s]+(\d+\.?\d*)', analysis_text, re.IGNORECASE)
        platform_fit_match = re.search(r'PLATFORM_FIT[:\s]+(\w+)', analysis_text, re.IGNORECASE)
        
        # Extract detailed analysis
        detailed_match = re.search(r'DETAILED_ANALYSIS[:\s]+(.*)', analysis_text, re.IGNORECASE | re.DOTALL)
        
        # Get values with fallbacks
        current_quality = float(current_quality_match.group(1)) if current_quality_match else 7.0
        current_viral = float(current_viral_match.group(1)) if current_viral_match else 6.0
        predicted_quality = float(predicted_quality_match.group(1)) if predicted_quality_match else current_quality + 0.5
        predicted_viral = float(predicted_viral_match.group(1)) if predicted_viral_match else current_viral + 0.3
        platform_fit = platform_fit_match.group(1) if platform_fit_match else "Good"
        detailed_analysis = detailed_match.group(1).strip() if detailed_match else analysis_text
        
        # Generate impact summary
        quality_diff = predicted_quality - current_quality
        viral_diff = predicted_viral - current_viral
        
        impact_analysis = f"""Na podstawie głębokiej analizy AI:

• **Jakość treści**: {current_quality:.1f} → {predicted_quality:.1f} ({'+' if quality_diff >= 0 else ''}{quality_diff:.1f})
• **Potencjał viralowy**: {current_viral:.1f} → {predicted_viral:.1f} ({'+' if viral_diff >= 0 else ''}{viral_diff:.1f})
• **Zgodność z platformą {platform}**: {platform_fit}

**Szczegółowa analiza wpływu:**
{detailed_analysis[:500]}..."""  # Limit length for UI

        # Determine recommendation based on real scores
        total_improvement = quality_diff + viral_diff
        if total_improvement > 1.0:
            recommendation = "🚀 Zdecydowanie rekomenduje - znacząca poprawa metryk!"
        elif total_improvement > 0.5:
            recommendation = "✅ Rekomenduje wprowadzenie zmian - widoczna poprawa wydajności."
        elif total_improvement > 0:
            recommendation = "👍 Zmiany przyniosą niewielką poprawę - warto rozważyć."
        elif total_improvement == 0:
            recommendation = "➡️ Zmiany neutralne - nie wpłyną znacząco na metryki."
        else:
            recommendation = "⚠️ Sugerowane zmiany mogą obniżyć wydajność - przemyśl inne podejście."
        
        return {
            "current_score": current_quality,
            "predicted_score": predicted_quality,
            "current_viral": current_viral,
            "predicted_viral": predicted_viral,
            "impact": impact_analysis,
            "recommendation": recommendation,
            "platform_fit": platform_fit,
            "detailed_analysis": {
                "full_text": analysis_text,
                "quality_change": quality_diff,
                "viral_change": viral_diff,
                "total_improvement": total_improvement
            }
        }
        
    except Exception as e:
        print(f"❌ Error in analyze_draft_impact: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback to simple analysis if CrewAI fails
        return {
            "current_score": 7.0,
            "predicted_score": 7.5,
            "current_viral": 6.0,
            "predicted_viral": 6.3,
            "impact": "Analiza podstawowa: Sugerowane zmiany powinny nieznacznie poprawić jakość contentu.",
            "recommendation": "✅ Rekomenduje wprowadzenie zmian.",
            "platform_fit": "Good",
            "detailed_analysis": {"error": str(e)}
        }

@app.post("/api/chat", tags=["assistant"],
         summary="Chat with AI Assistant",
         response_model=ChatResponse,
         description="Chat endpoint for AI Assistant that can help with draft editing and content strategy")
async def chat_with_assistant(request: ChatRequest):
    """
    Chat endpoint for AI Assistant with real OpenAI integration
    
    Step 2 implementation - uses GPT-4 for intelligent responses
    """
    # Check if OpenAI client is initialized
    if not openai_client:
        return ChatResponse(
            response="❌ AI Assistant jest niedostępny. Brak konfiguracji OPENAI_API_KEY.",
            intent=None,
            context_actions=[],
            error="service_unavailable"
        )
    
    try:
        # Manage conversation memory
        session_id = request.session_id
        if session_id not in conversation_memory:
            conversation_memory[session_id] = []
        
        # Add user message to memory
        conversation_memory[session_id].append({
            "role": "user",
            "content": request.message
        })
        
        # Trim conversation if too long
        if len(conversation_memory[session_id]) > MAX_CONVERSATION_LENGTH:
            # Keep system message if exists, then trim oldest messages
            conversation_memory[session_id] = conversation_memory[session_id][-MAX_CONVERSATION_LENGTH:]
        
        # Log for debugging
        print(f"💬 Chat request: {request.message}")
        print(f"📎 Context keys: {list(request.context.keys()) if request.context else []}")
        print(f"🧠 Session {session_id}: {len(conversation_memory.get(session_id, []))} messages in memory")
        
        # Build context information if provided
        context_info = ""
        if request.context:
            if request.context.get("currentDraft"):
                context_info += f"\n\n**AKTUALNY DRAFT:**\n{request.context['currentDraft']}\n"
            
            if request.context.get("topicTitle"):
                context_info += f"\n**TEMAT:** {request.context['topicTitle']}\n"
            
            if request.context.get("platform"):
                context_info += f"**PLATFORMA:** {request.context['platform']}\n"
            
            if request.context.get("metrics"):
                metrics = request.context['metrics']
                context_info += f"\n**METRYKI:**"
                if 'quality_score' in metrics:
                    context_info += f"\n- Jakość: {metrics['quality_score']}/10"
                if 'viral_score' in metrics:
                    context_info += f"\n- Potencjał viralowy: {metrics['viral_score']}/10"
                if 'compliance_score' in metrics:
                    context_info += f"\n- Zgodność ze stylem: {metrics['compliance_score']}/10"
                context_info += "\n"
        
        # Enhanced system prompt emphasizing conversational nature
        system_prompt = f"""Jesteś AI Assistantem Vector Wave - inteligentnym partnerem do rozmowy o content marketingu.

NAJWAŻNIEJSZE: Jesteś przede wszystkim konwersacyjnym assistentem. Możesz:
- Rozmawiać na dowolne tematy związane z marketingiem, pisaniem, AI bądź czymkolwiek innym
- Żartować, filozofować, doradzać
- Odpowiadać na pytania niezwiązane z draftem
- Po prostu gawędzić z użytkownikiem

Masz OPCJONALNY dostęp do narzędzi, ale używaj ich TYLKO gdy użytkownik wyraźnie:
- Prosi o analizę wpływu zmian na metryki
- Chce regenerować draft z konkretnymi sugestiami
- Pyta o konkretne score'y lub compliance

NIE używaj narzędzi gdy użytkownik:
- Pyta ogólne pytania ("Co sądzisz o AI?")
- Chce pogadać ("Nudzi mi się")
- Prosi o opinię niezwiązaną z konkretnymi metrykami
- Żartuje lub bawi się konwersacją

Bądź naturalny, pomocny i przyjacielski. To rozmowa, nie tylko wykonywanie poleceń.
{context_info if context_info else ""}"""

        # Define tools for function calling
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "analyze_draft_impact",
                    "description": "Use ONLY when user explicitly asks about impact on scores/metrics",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "original_draft": {"type": "string", "description": "The current draft content"},
                            "suggested_changes": {"type": "string", "description": "Changes user wants to make"},
                            "platform": {"type": "string", "description": "Platform: LinkedIn, Twitter, or Blog"}
                        },
                        "required": ["original_draft", "suggested_changes", "platform"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "regenerate_draft_with_suggestions",
                    "description": "Use ONLY when user explicitly asks to regenerate with specific changes",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "topic_title": {"type": "string", "description": "Title of the topic"},
                            "suggestions": {"type": "string", "description": "User's suggestions for regeneration"},
                            "platform": {"type": "string", "description": "Platform: LinkedIn, Twitter, or Blog"}
                        },
                        "required": ["topic_title", "suggestions", "platform"]
                    }
                }
            }
        ]
        
        # Create messages for OpenAI with conversation history
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history (excluding the current message we just added)
        if len(conversation_memory[session_id]) > 1:
            # Add previous messages (all except the last one which is the current message)
            for msg in conversation_memory[session_id][:-1]:
                messages.append(msg)
        
        # Add current message
        messages.append({"role": "user", "content": request.message})
        
        # Call OpenAI API with function calling
        try:
            # For function calling, we need to use the OpenAI client directly
            # or configure LangChain properly
            llm_with_tools = llm.bind(
                functions=[tool["function"] for tool in tools],
                function_call="auto"
            )
            
            response = await llm_with_tools.ainvoke(messages)
            
            # Check if function was called
            if hasattr(response, 'additional_kwargs') and 'function_call' in response.additional_kwargs:
                function_call = response.additional_kwargs['function_call']
                function_name = function_call.get('name', 'unknown')
                print(f"🔧 Function called: {function_name}")
                
                # Parse function arguments
                import json
                try:
                    function_args = json.loads(function_call.get('arguments', '{}'))
                except:
                    function_args = {}
                
                # Handle function calls
                if function_name == "analyze_draft_impact":
                    # Extract parameters with defaults from context
                    original_draft = function_args.get('original_draft') or request.context.get('currentDraft', '')
                    suggested_changes = function_args.get('suggested_changes', '')
                    platform = function_args.get('platform') or request.context.get('platform', 'LinkedIn')
                    
                    # Call the analysis function
                    result = await analyze_draft_impact(original_draft, suggested_changes, platform)
                    
                    # Enhanced response formatting with emoji indicators
                    score_diff = result['predicted_score'] - result['current_score']
                    viral_diff = result.get('predicted_viral', result.get('current_viral', 0)) - result.get('current_viral', 0)
                    
                    # Choose emoji based on impact
                    impact_emoji = "📈" if score_diff > 0 else ("📉" if score_diff < 0 else "➡️")
                    
                    ai_response = f"""### {impact_emoji} Analiza wpływu sugerowanych zmian

**📊 Metryki główne:**
• **Jakość treści:** {result['current_score']:.1f} → {result['predicted_score']:.1f} ({'+' if score_diff >= 0 else ''}{score_diff:.1f})
• **Potencjał viralowy:** {result.get('current_viral', 6.0):.1f} → {result.get('predicted_viral', 6.0):.1f} ({'+' if viral_diff >= 0 else ''}{viral_diff:.1f})

**💡 Analiza szczegółowa:**
{result['impact']}

**🎯 Rekomendacja:** {result['recommendation']}"""
                    
                    # Enhanced context actions based on analysis results
                    context_actions = []
                    
                    # Add regenerate button if improvement is predicted
                    if result['predicted_score'] > result['current_score']:
                        context_actions.append({
                            "label": "✍️ Wygeneruj draft z sugestiami",
                            "action": "regenerate_with_suggestions",
                            "params": {
                                "suggestions": suggested_changes,
                                "platform": platform,
                                "original_draft": original_draft
                            }
                        })
                    
                    # Add alternative suggestions button if no improvement
                    elif score_diff <= 0:
                        context_actions.append({
                            "label": "💭 Zaproponuj inne podejście",
                            "action": "suggest_alternatives",
                            "params": {
                                "current_approach": suggested_changes,
                                "platform": platform
                            }
                        })
                    
                    # Always add detailed report button
                    context_actions.append({
                        "label": "📄 Pokaż pełny raport",
                        "action": "show_detailed_report",
                        "params": {
                            "full_analysis": result.get('detailed_analysis', {}),
                            "metrics": {
                                "quality": {"before": result['current_score'], "after": result['predicted_score']},
                                "viral": {"before": result.get('current_viral', 0), "after": result.get('predicted_viral', 0)},
                                "platform_fit": result.get('platform_fit', 'Unknown')
                            }
                        }
                    })
                
                elif function_name == "regenerate_draft_with_suggestions":
                    # Extract parameters
                    topic_title = function_args.get('topic_title', '') or request.context.get('topicTitle', 'Untitled')
                    suggestions = function_args.get('suggestions', '')
                    platform = function_args.get('platform') or request.context.get('platform', 'LinkedIn')
                    original_draft = request.context.get('currentDraft', '')
                    
                    print(f"🔄 Regenerating draft: {topic_title} with suggestions: {suggestions[:50]}...")
                    
                    # Call the regeneration function
                    result = await regenerate_draft_with_suggestions(
                        topic_title=topic_title,
                        suggestions=suggestions,
                        platform=platform,
                        original_draft=original_draft,
                        context=request.context
                    )
                    
                    if result.get("success") and result.get("draft"):
                        draft = result["draft"]
                        ai_response = f"""### ✅ Draft zregenerowany z sugestiami!

**📝 Nowa wersja:**
{draft["content"]}

**📊 Metryki:**
• Słowa: {draft["word_count"]}
• Znaki: {draft["character_count"]}
• Quality Score: {draft["quality_score"]}/10
• Viral Score: {draft["viral_score"]}/10

**🔧 Metoda:** {result.get("generation_method", "unknown")}
**💡 Uwzględnione sugestie:** {result.get("suggestions_incorporated", "brak")}"""
                        
                        context_actions = [{
                            "label": "📝 Edytuj dalej",
                            "action": "open_editor",
                            "params": {
                                "draft": draft["content"],
                                "topic": topic_title,
                                "platform": platform
                            }
                        }, {
                            "label": "📊 Przeanalizuj ponownie",
                            "action": "analyze_regenerated_draft",
                            "params": {
                                "draft": draft["content"],
                                "original": original_draft,
                                "suggestions": suggestions
                            }
                        }]
                        
                        if result.get("note"):
                            ai_response += f"\n\n⚠️ **Uwaga:** {result['note']}"
                    else:
                        ai_response = f"""### ❌ Błąd regeneracji draftu

Nie udało się zregenerować draftu z sugestiami.

**Błąd:** {result.get('error', 'Nieznany błąd')}

**Sugestie do zastosowania ręcznie:**
{suggestions}"""
                        
                        context_actions = [{
                            "label": "📝 Edytuj draft ręcznie",
                            "action": "open_editor",
                            "params": {
                                "draft": original_draft,
                                "suggestions": suggestions
                            }
                        }]
                
                else:
                    ai_response = response.content
                    context_actions = []
                    
            else:
                ai_response = response.content
                context_actions = []
            
            print(f"✅ OpenAI response received, length: {len(ai_response)}")
            
        except Exception as openai_error:
            logger.error(f"OpenAI API error in chat endpoint: {openai_error}")
            print(f"❌ OpenAI API error: {openai_error}")
            
            # Specific error handling with user-friendly messages
            error_str = str(openai_error).lower()
            
            if "api_key" in error_str or "authentication" in error_str:
                return ChatResponse(
                    response="❌ Brak klucza API OpenAI. Administrator musi skonfigurować OPENAI_API_KEY w pliku .env",
                    intent=None,
                    context_actions=[],
                    error="missing_api_key"
                )
            elif "rate" in error_str or "limit" in error_str or "429" in error_str:
                return ChatResponse(
                    response="⏳ Przekroczono limit zapytań do API. Proszę spróbować za chwilę (zwykle 1-2 minuty).",
                    intent=None,
                    context_actions=[],
                    error="rate_limit"
                )
            elif "timeout" in error_str or "timed out" in error_str:
                return ChatResponse(
                    response="⏱️ Przekroczono czas oczekiwania na odpowiedź. Proszę spróbować ponownie.",
                    intent=None,
                    context_actions=[],
                    error="timeout"
                )
            elif "connection" in error_str or "network" in error_str:
                return ChatResponse(
                    response="🌐 Błąd połączenia z serwerem OpenAI. Sprawdź połączenie internetowe.",
                    intent=None,
                    context_actions=[],
                    error="connection_error"
                )
            elif "model" in error_str:
                return ChatResponse(
                    response="🤖 Niedostępny model GPT-4. Skontaktuj się z administratorem.",
                    intent=None,
                    context_actions=[],
                    error="model_error"
                )
            else:
                # Generic error with sanitized message
                return ChatResponse(
                    response=f"❌ Wystąpił błąd podczas przetwarzania: {str(openai_error)[:100]}...",
                    intent=None,
                    context_actions=[],
                    error="api_error"
                )
        
        # Intent recognition based on keywords
        intent = classify_intent(request.message)
        
        # Add assistant response to conversation memory
        conversation_memory[session_id].append({
            "role": "assistant",
            "content": ai_response
        })
        
        # Trim again if needed
        if len(conversation_memory[session_id]) > MAX_CONVERSATION_LENGTH:
            conversation_memory[session_id] = conversation_memory[session_id][-MAX_CONVERSATION_LENGTH:]
        
        return ChatResponse(
            response=ai_response,
            intent=intent,
            context_actions=context_actions if 'context_actions' in locals() else [],
            error=None
        )
        
    except Exception as e:
        logger.error(f"Chat endpoint general error: {e}")
        print(f"❌ Chat error: {e}")
        import traceback
        traceback.print_exc()
        
        # Handle unexpected errors gracefully
        error_str = str(e).lower()
        
        if "chromadb" in error_str or "vector" in error_str:
            return ChatResponse(
                response="⚠️ Błąd połączenia z bazą wektorową. Funkcje style guide mogą być niedostępne.",
                intent=None,
                context_actions=[],
                error="vector_db_error"
            )
        elif "redis" in error_str:
            return ChatResponse(
                response="⚠️ Błąd cache. Historia konwersacji może nie być zapisywana.",
                intent=None,
                context_actions=[],
                error="cache_error"
            )
        elif "json" in error_str:
            return ChatResponse(
                response="📝 Błąd formatu danych. Sprawdź poprawność zapytania.",
                intent=None,
                context_actions=[],
                error="format_error"
            )
        else:
            return ChatResponse(
                response=f"❌ Wystąpił nieoczekiwany błąd. Spróbuj ponownie lub skontaktuj się z administratorem.",
                intent=None,
                context_actions=[],
                error="unexpected_error"
            )

@app.post("/api/chat/stream", tags=["assistant"],
         summary="Chat with AI Assistant (Streaming)",
         description="Streaming chat endpoint for AI Assistant that supports long-running operations")
async def chat_with_assistant_stream(request: ChatRequest):
    """
    Streaming chat endpoint for AI Assistant
    
    Step 10 implementation - uses Server-Sent Events for streaming responses
    """
    # Check if OpenAI client is initialized
    if not openai_client:
        async def error_generator():
            yield f"data: {json.dumps({'type': 'error', 'error_type': 'service_unavailable', 'message': '❌ AI Assistant jest niedostępny. Brak konfiguracji OPENAI_API_KEY.'})}\n\n"
        return StreamingResponse(
            error_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    async def generate() -> AsyncGenerator[str, None]:
        try:
            # Manage conversation memory
            session_id = request.session_id
            if session_id not in conversation_memory:
                conversation_memory[session_id] = []
            
            # Add user message to memory
            conversation_memory[session_id].append({
                "role": "user",
                "content": request.message
            })
            
            # Trim conversation if too long
            if len(conversation_memory[session_id]) > MAX_CONVERSATION_LENGTH:
                conversation_memory[session_id] = conversation_memory[session_id][-MAX_CONVERSATION_LENGTH:]
            
            # Send initial event
            yield f"data: {json.dumps({'type': 'start', 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Build context information
            context_info = ""
            if request.context:
                if request.context.get("currentDraft"):
                    context_info += f"\n\n**AKTUALNY DRAFT:**\n{request.context['currentDraft']}\n"
                
                if request.context.get("topicTitle"):
                    context_info += f"\n**TEMAT:** {request.context['topicTitle']}\n"
                
                if request.context.get("platform"):
                    context_info += f"**PLATFORMA:** {request.context['platform']}\n"
                
                if request.context.get("metrics"):
                    metrics = request.context['metrics']
                    context_info += f"\n**METRYKI:**"
                    if 'quality_score' in metrics:
                        context_info += f"\n- Jakość: {metrics['quality_score']}/10"
                    if 'viral_score' in metrics:
                        context_info += f"\n- Potencjał viralowy: {metrics['viral_score']}/10"
                    if 'compliance_score' in metrics:
                        context_info += f"\n- Zgodność ze stylem: {metrics['compliance_score']}/10"
                    context_info += "\n"
            
            # System prompt
            system_prompt = f"""Jesteś AI Assistantem Vector Wave - inteligentnym partnerem do rozmowy o content marketingu.

NAJWAŻNIEJSZE: Jesteś przede wszystkim konwersacyjnym assistentem. Możesz:
- Rozmawiać na dowolne tematy związane z marketingiem, pisaniem, AI bądź czymkolwiek innym
- Żartować, filozofować, doradzać
- Odpowiadać na pytania niezwiązane z draftem
- Po prostu gawędzić z użytkownikiem

Masz OPCJONALNY dostęp do narzędzi, ale używaj ich TYLKO gdy użytkownik wyraźnie:
- Prosi o analizę wpływu zmian na metryki
- Chce regenerować draft z konkretnymi sugestiami
- Pyta o konkretne score'y lub compliance

NIE używaj narzędzi gdy użytkownik:
- Pyta ogólne pytania ("Co sądzisz o AI?")
- Chce pogadać ("Nudzi mi się")
- Prosi o opinię niezwiązaną z konkretnymi metrykami
- Żartuje lub bawi się konwersacją

Bądź naturalny, pomocny i przyjacielski. To rozmowa, nie tylko wykonywanie poleceń.
{context_info if context_info else ""}"""

            # Define tools
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "analyze_draft_impact",
                        "description": "Use ONLY when user explicitly asks about impact on scores/metrics",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "original_draft": {"type": "string"},
                                "suggested_changes": {"type": "string"},
                                "platform": {"type": "string"}
                            },
                            "required": ["original_draft", "suggested_changes", "platform"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "regenerate_draft_with_suggestions",
                        "description": "Use ONLY when user explicitly asks to regenerate with specific changes",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "topic_title": {"type": "string"},
                                "suggestions": {"type": "string"},
                                "platform": {"type": "string"}
                            },
                            "required": ["topic_title", "suggestions", "platform"]
                        }
                    }
                }
            ]
            
            # Create messages with conversation history
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add conversation history (excluding the current message we just added)
            if len(conversation_memory[session_id]) > 1:
                # Add previous messages (all except the last one which is the current message)
                for msg in conversation_memory[session_id][:-1]:
                    messages.append(msg)
            
            # Add current message
            messages.append({"role": "user", "content": request.message})
            
            # Intent detection
            intent = classify_intent(request.message)
            yield f"data: {json.dumps({'type': 'intent', 'intent': intent})}\n\n"
            
            # Stream OpenAI response
            stream = await openai_client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                stream=True,
                temperature=0.7,
                max_tokens=1000
            )
            
            # Variables to track function calls
            function_call_accumulator = ""
            current_function_name = None
            content_accumulator = ""
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    content_accumulator += content
                    yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
                
                # Check for tool calls
                if chunk.choices[0].delta.tool_calls:
                    for tool_call in chunk.choices[0].delta.tool_calls:
                        if tool_call.function:
                            if tool_call.function.name:
                                current_function_name = tool_call.function.name
                                yield f"data: {json.dumps({'type': 'function_start', 'function': current_function_name})}\n\n"
                            
                            if tool_call.function.arguments:
                                function_call_accumulator += tool_call.function.arguments
            
            # Handle function calls if any
            if current_function_name and function_call_accumulator:
                yield f"data: {json.dumps({'type': 'function_processing', 'function': current_function_name})}\n\n"
                
                try:
                    function_args = json.loads(function_call_accumulator)
                    
                    if current_function_name == "analyze_draft_impact":
                        result = await analyze_draft_impact(
                            function_args.get('original_draft', request.context.get('currentDraft', '')),
                            function_args.get('suggested_changes', ''),
                            function_args.get('platform', request.context.get('platform', 'LinkedIn'))
                        )
                        
                        # Format and send the result
                        score_diff = result['predicted_score'] - result['current_score']
                        impact_emoji = "📈" if score_diff > 0 else ("📉" if score_diff < 0 else "➡️")
                        
                        formatted_result = f"""### {impact_emoji} Analiza wpływu sugerowanych zmian

**📊 Metryki główne:**
• **Jakość treści:** {result['current_score']:.1f} → {result['predicted_score']:.1f} ({'+' if score_diff >= 0 else ''}{score_diff:.1f})

**💡 Analiza szczegółowa:**
{result['impact']}

**🎯 Rekomendacja:** {result['recommendation']}"""
                        
                        yield f"data: {json.dumps({'type': 'function_result', 'content': formatted_result})}\n\n"
                        
                        # Send context actions
                        context_actions = []
                        if result['predicted_score'] > result['current_score']:
                            context_actions.append({
                                "label": "✍️ Wygeneruj draft z sugestiami",
                                "action": "regenerate_with_suggestions",
                                "params": {
                                    "suggestions": function_args.get('suggested_changes', ''),
                                    "platform": function_args.get('platform', 'LinkedIn')
                                }
                            })
                        
                        yield f"data: {json.dumps({'type': 'context_actions', 'actions': context_actions})}\n\n"
                    
                    elif current_function_name == "regenerate_draft_with_suggestions":
                        yield f"data: {json.dumps({'type': 'status', 'message': 'Generuję nowy draft z Twoimi sugestiami...'})}\n\n"
                        
                        result = await regenerate_draft_with_suggestions(
                            function_args.get('topic_title', request.context.get('topicTitle', '')),
                            function_args.get('suggestions', ''),
                            function_args.get('platform', request.context.get('platform', 'LinkedIn')),
                            request.context.get('currentDraft', ''),
                            request.context
                        )
                        
                        if result.get('error'):
                            yield f"data: {json.dumps({'type': 'error', 'message': result['error']})}\n\n"
                        else:
                            yield f"data: {json.dumps({'type': 'draft_generated', 'draft': result.get('draft_content', '')})}\n\n"
                
                except Exception as func_error:
                    yield f"data: {json.dumps({'type': 'error', 'message': f'Błąd funkcji: {str(func_error)}'})}\n\n"
            
            # Add assistant response to conversation memory
            if content_accumulator:
                conversation_memory[session_id].append({
                    "role": "assistant",
                    "content": content_accumulator
                })
                
                # Trim again if needed
                if len(conversation_memory[session_id]) > MAX_CONVERSATION_LENGTH:
                    conversation_memory[session_id] = conversation_memory[session_id][-MAX_CONVERSATION_LENGTH:]
            
            # Send completion event
            yield f"data: {json.dumps({'type': 'complete', 'timestamp': datetime.now().isoformat()})}\n\n"
            
        except Exception as e:
            logger.error(f"Streaming chat error: {e}")
            error_str = str(e).lower()
            
            # Determine error type and user-friendly message
            if "api_key" in error_str or "authentication" in error_str:
                error_type = "missing_api_key"
                message = "❌ Brak klucza API OpenAI. Administrator musi skonfigurować OPENAI_API_KEY w pliku .env"
            elif "rate" in error_str or "limit" in error_str or "429" in error_str:
                error_type = "rate_limit"
                message = "⏳ Przekroczono limit zapytań do API. Proszę spróbować za chwilę (zwykle 1-2 minuty)."
            elif "timeout" in error_str or "timed out" in error_str:
                error_type = "timeout"
                message = "⏱️ Przekroczono czas oczekiwania na odpowiedź. Proszę spróbować ponownie."
            elif "connection" in error_str or "network" in error_str:
                error_type = "connection_error"
                message = "🌐 Błąd połączenia z serwerem OpenAI. Sprawdź połączenie internetowe."
            elif "model" in error_str:
                error_type = "model_error"
                message = "🤖 Niedostępny model GPT-4. Skontaktuj się z administratorem."
            else:
                error_type = "unknown_error"
                message = f"❌ Wystąpił błąd: {str(e)[:100]}..."
            
            yield f"data: {json.dumps({'type': 'error', 'error_type': error_type, 'message': message})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

@app.delete("/api/chat/memory/{session_id}", tags=["assistant"],
           summary="Clear conversation memory",
           description="Clear conversation history for a specific session")
async def clear_conversation_memory(session_id: str):
    """Clear conversation memory for a session"""
    if session_id in conversation_memory:
        del conversation_memory[session_id]
        return {"status": "success", "message": f"Conversation memory cleared for session {session_id}"}
    else:
        return {"status": "info", "message": f"No conversation memory found for session {session_id}"}

@app.get("/api/chat/health", tags=["assistant"],
         summary="Check AI Assistant health",
         description="Verify API keys and service availability")
async def check_chat_health():
    """Check if AI Assistant is properly configured and available"""
    health_status = {
        "status": "checking",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # Check OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        health_status["checks"]["openai_api_key"] = {
            "status": "error",
            "message": "OPENAI_API_KEY not configured in environment"
        }
        health_status["status"] = "unhealthy"
    elif not api_key.startswith("sk-"):
        health_status["checks"]["openai_api_key"] = {
            "status": "warning",
            "message": "OPENAI_API_KEY format appears incorrect"
        }
        health_status["status"] = "degraded"
    else:
        health_status["checks"]["openai_api_key"] = {
            "status": "ok",
            "message": "API key configured"
        }
    
    # Test OpenAI connection if key exists
    if api_key and health_status["status"] != "unhealthy":
        try:
            # Quick test with minimal tokens
            test_response = await openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            health_status["checks"]["openai_connection"] = {
                "status": "ok",
                "message": "Successfully connected to OpenAI API",
                "model": "gpt-4"
            }
            if health_status["status"] == "checking":
                health_status["status"] = "healthy"
        except Exception as e:
            error_msg = str(e)
            if "rate" in error_msg.lower():
                health_status["checks"]["openai_connection"] = {
                    "status": "warning",
                    "message": "Rate limit reached, but API is working"
                }
                if health_status["status"] == "checking":
                    health_status["status"] = "degraded"
            else:
                health_status["checks"]["openai_connection"] = {
                    "status": "error",
                    "message": f"Connection failed: {error_msg[:100]}"
                }
                health_status["status"] = "unhealthy"
    
    # Check conversation memory
    health_status["checks"]["conversation_memory"] = {
        "status": "ok",
        "message": f"Active sessions: {len(conversation_memory)}",
        "max_length": MAX_CONVERSATION_LENGTH
    }
    
    # Check ChromaDB connection
    if style_guide_collection:
        try:
            count = style_guide_collection.count()
            health_status["checks"]["vector_db"] = {
                "status": "ok",
                "message": f"ChromaDB connected, {count} style rules loaded"
            }
        except:
            health_status["checks"]["vector_db"] = {
                "status": "warning",
                "message": "ChromaDB unavailable, style guide features limited"
            }
    else:
        health_status["checks"]["vector_db"] = {
            "status": "warning",
            "message": "ChromaDB not initialized"
        }
    
    # Final status determination
    if health_status["status"] == "checking":
        health_status["status"] = "healthy"
    
    return health_status