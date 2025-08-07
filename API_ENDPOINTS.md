# API Endpoints Documentation - AI Kolegium Redakcyjne

## Overview
**Base URL:** `http://localhost:8003`  
**Last Updated:** 2025-08-05 (commit: `58cbf76`)

## 🎯 Core Endpoints

### 1. Health Check
```bash
GET /health
```
Returns basic health status.

**Response:**
```json
{
  "status": "healthy",
  "container": "running"
}
```

### 2. Analyze Content Potential ⚡ (with Redis Cache)
```bash
POST /api/analyze-potential
```
Ultra-fast content analysis (1ms response time) with 5-minute Redis cache.

**Request:**
```json
{
  "folder": "2025-07-31-adhd-ideas-overflow",
  "use_flow": false
}
```

**Response:**
```json
{
  "folder": "2025-07-31-adhd-ideas-overflow",
  "filesCount": 5,
  "contentType": "GENERAL",
  "contentOwnership": "ORIGINAL",
  "valueScore": 7.5,
  "viral_score": 0.75,
  "topTopics": [
    {
      "title": "5 Lessons from ADHD Ideas Overflow Implementation",
      "platform": "LinkedIn",
      "viralScore": 8
    }
  ],
  "recommendation": "🔥 High viral potential!",
  "processing_time_ms": 1,
  "from_cache": false  // true on subsequent calls within 5 minutes
}
```

**Cache behavior:**
- First call: `from_cache: false`, data computed and cached
- Subsequent calls (within 5 min): `from_cache: true`, instant response
- Cache TTL: 300 seconds (5 minutes)
- Cache key: `analysis:{folder_name}`

### 3. Generate Draft 🚀
```bash
POST /api/generate-draft
```
Generates content draft using CrewAI Writer Agent.

**Request:**
```json
{
  "content": {
    "title": "5 AI Automation Mistakes",
    "content_type": "STANDARD",
    "platform": "LinkedIn",
    "content_ownership": "ORIGINAL"
  },
  "skip_research": true  // Automatic for ORIGINAL content
}
```

**Response:**
```json
{
  "status": "completed",
  "draft": {
    "title": "5 AI Automation Mistakes",
    "content": "Full draft content...",
    "platform": "LinkedIn",
    "word_count": 458,
    "optimized_for": "LinkedIn"
  },
  "metadata": {
    "generated_at": "2025-08-05T20:04:39.350855",
    "content_type": "STANDARD",
    "used_research": false,
    "execution_time_seconds": 20.5,
    "optimization_applied": true
  }
}
```

### 4. Execute Research
```bash
POST /api/research
```
Performs deep research on a topic.

**Request:**
```json
{
  "topic": "AI Automation Trends",
  "depth": "standard",  // quick, standard, deep
  "skip_research": false
}
```

**Response:**
```json
{
  "status": "completed",
  "topic": "AI Automation Trends",
  "findings": {
    "summary": "Research findings...",
    "key_points": ["Point 1", "Point 2"],
    "word_count": 350
  },
  "execution_time_ms": 2500
}
```

### 5. Execute Complete Flow
```bash
POST /api/execute-flow
```
Runs the complete flow: routing → research → writing.

**Request:**
```json
{
  "title": "Building AI Agents",
  "content_type": "TECHNICAL",
  "platform": "Blog",
  "content_ownership": "EXTERNAL"
}
```

### 6. Execute Flow with Tracking
```bash
POST /api/execute-flow-tracked
```
Complete flow with detailed diagnostics and step tracking.

**Response includes:**
- Flow ID for tracking
- Step-by-step execution details
- Agent decisions
- Content loss metrics
- Timing information

### 7. Flow Diagnostics
```bash
GET /api/flow-diagnostics/{flow_id}
```
Get detailed diagnostics for a specific flow execution.

```bash
GET /api/flow-diagnostics?limit=10
```
List recent flow executions.

### 8. List Content Folders
```bash
GET /api/list-content-folders
```
Lists available content folders from the raw content directory.

**Response:**
```json
{
  "status": "ok",
  "folders": [
    {
      "name": "2025-07-31-adhd-ideas-overflow",
      "path": "/path/to/folder",
      "type": "raw_content"
    }
  ],
  "total": 15
}
```

### 9. Verify OpenAI Integration
```bash
GET /api/verify-openai
```
Verifies that the system is using real OpenAI API.

### 10. Cache Test
```bash
GET /api/cache-test
```
Tests Redis cache functionality.

**Response:**
```json
{
  "status": "ok",
  "cached_value": "Hello Redis!",
  "ttl": 59
}
```

### 11. Style Guide Seed
```bash
POST /api/style-guide/seed
```
Seeds ChromaDB with Vector Wave style guide rules.

**Response:**
```json
{
  "status": "success",
  "rules_added": 8,
  "total_rules": 8
}
```

### 12. Style Guide Check (Naive RAG)
```bash
POST /api/style-guide/check
```
Checks content against Vector Wave style guide using Naive RAG.

**Request:**
```json
{
  "content": "Your content here...",
  "platform": "LinkedIn",
  "check_categories": ["tone", "structure", "engagement"]
}
```

**Response:**
```json
{
  "status": "success",
  "style_score": 85,
  "relevant_rules": [
    {
      "rule_id": "linkedin-1",
      "rule": "LinkedIn posts should start with a pattern interrupt",
      "category": "platform-linkedin",
      "priority": "high",
      "relevance_score": 0.85
    }
  ],
  "violations": [
    {
      "rule": "Use short paragraphs (max 3 sentences)",
      "severity": "low",
      "suggestion": "Break up long paragraphs for better readability"
    }
  ],
  "suggestions": [
    {
      "rule": "Ask questions to encourage comments",
      "suggestion": "Add a question at the end like 'What's your experience with this?'"
    }
  ],
  "platform": "LinkedIn",
  "checked_categories": ["tone", "structure", "engagement"]
}
```

### 13. Style Guide Check - Agentic RAG
```bash
POST /api/style-guide/check-agentic
```
Intelligent style analysis using CrewAI agent with context awareness.

**Request:**
```json
{
  "content": "Your content here...",
  "platform": "LinkedIn",
  "focus_areas": ["engagement", "clarity", "viral_potential"],
  "context": "Technical achievement post"
}
```

**Response:**
```json
{
  "status": "success",
  "analysis_type": "agentic",
  "style_score": 70,
  "agent_analysis": "Overall Style Score: 70/100\n\nWhat Works Well:\n1. Clear communication...\n\nCritical Improvements:\n1. Lacks strong hook...\n\nAlternative Opening: \"Guess how we boosted...\"\n\nRecommended CTA: \"Share your experiences...\"",
  "relevant_rules_used": 7,
  "execution_time_seconds": 17.74,
  "cost_estimate": "$0.02-0.05 (GPT-4)"
}
```

### 14. Compare Style Check Methods
```bash
POST /api/style-guide/compare
```
Compare Naive RAG vs Agentic RAG analysis for the same content.

**Response:**
```json
{
  "status": "success",
  "comparison": {
    "naive_rag": {
      "score": 65,
      "violations": 2,
      "suggestions": 1,
      "execution_time": 0.293
    },
    "agentic_rag": {
      "score": 65,
      "has_alternative_opening": true,
      "has_cta_recommendation": true,
      "execution_time": 12.498
    }
  },
  "recommendation": "Use Naive RAG for real-time validation, Agentic RAG for deep analysis"
}
```

## 🔧 Frontend Proxy Endpoints

### Generate Draft (Frontend Proxy)
```bash
POST /api/generate-draft  # Port 3000
```
Frontend proxy that transforms data between UI and backend formats.

**Key Transformations:**
- `topic_title` → `content.title`
- Adds default values for missing fields
- Transforms response format (`status: "completed"` → `success: true`)
- Automatically sets `skip_research: true` for ORIGINAL content

## 📊 Performance Metrics

| Endpoint | Average Response Time | Notes |
|----------|---------------------|-------|
| `/api/analyze-potential` | 1ms | No AI calls |
| `/api/generate-draft` (ORIGINAL) | ~20s | Skip research |
| `/api/generate-draft` (EXTERNAL) | ~25s | With research |
| `/api/execute-research` | 2-3s | Deep research |
| `/api/execute-flow` | 25-50s | Full flow |

## 🚀 Optimizations

### Skip Research for ORIGINAL Content
When `content_ownership = "ORIGINAL"`:
- Research phase is automatically skipped
- Special context provided to AI agent
- ~20% faster draft generation (25s → 20s)

### Response Caching
- Simple in-memory caching available
- Cache key: `{title}:{platform}`
- Useful for repeated requests

## 🔍 Error Handling

All endpoints return consistent error format:
```json
{
  "status": "error",
  "error": "Error message",
  "detail": "Additional context if available"
}
```

Common HTTP status codes:
- `200`: Success
- `404`: Endpoint not found (check URL)
- `422`: Validation error (check request format)
- `500`: Server error

## 🧪 Testing

### Quick Test Commands

```bash
# Test health
curl http://localhost:8003/health

# Test analyze (fastest)
curl -X POST http://localhost:8003/api/analyze-potential \
  -H "Content-Type: application/json" \
  -d '{"folder": "test-folder"}'

# Test draft generation
curl -X POST http://localhost:8003/api/generate-draft \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "title": "Test Draft",
      "platform": "LinkedIn",
      "content_ownership": "ORIGINAL"
    },
    "skip_research": true
  }'
```

## 📝 Notes

1. **Port Configuration**: Backend runs on port 8003, frontend on 3000
2. **CORS**: Enabled for frontend integration
3. **Authentication**: Currently no auth required (development mode)
4. **Rate Limiting**: Not implemented yet
5. **Logging**: Optimization logs visible in console