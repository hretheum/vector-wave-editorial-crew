# API Reference - Kolegium AI Writing Flow

## 🚀 Quick Start

Base URL: `http://localhost:8003`

## 📊 Current Status (2025-08-06)
- ✅ Phase 5: AI Assistant Integration - COMPLETED (12/12 steps)
- ✅ Phase 6: TRUE Agentic RAG - COMPLETED
- ✅ All endpoints production-ready with error handling
- ✅ Conversation memory & streaming support

## 🔥 Core Endpoints

### 1. Generate Draft with TRUE Agentic RAG
```bash
POST /generate-draft
{
  "content": {
    "title": "Your topic here",
    "platform": "LinkedIn",
    "content_type": "THOUGHT_LEADERSHIP",
    "content_ownership": "ORIGINAL"
  }
}
```
- Uses iterative style guide search (3-5 autonomous queries)
- Each generation is unique even for same input
- Response time: 20-50s

### 2. Analyze Custom Ideas (Batch)
```bash
POST /analyze-custom-ideas
{
  "ideas": ["idea 1", "idea 2", "idea 3"]
}
```
- Analyzes multiple ideas in parallel
- Returns scores, recommendations, best idea

### 3. Stream Batch Analysis (SSE)
```bash
POST /analyze-custom-ideas-stream
{
  "ideas": ["idea 1", "idea 2", "idea 3"]
}
```
- Real-time progress updates
- Event types: start, progress, result, error, complete

### 4. Iterative Style Guide Analysis
```bash
POST /style-guide/analyze-iterative
{
  "content": "Your content to analyze",
  "platform": "LinkedIn",
  "max_iterations": 5
}
```
- Agent autonomously searches style guide
- Returns search log, discovered rules, analysis

### 5. Chat with AI Assistant
```bash
POST /api/chat
{
  "message": "Make the draft more engaging",
  "session_id": "user-123-session-456",
  "context": {
    "currentDraft": "current draft...",
    "topicTitle": "AI in Marketing",
    "platform": "LinkedIn",
    "metrics": {
      "quality_score": 7.5,
      "viral_score": 6.0
    }
  }
}
```
- Natural language draft editing
- Intent recognition with function calling
- Context-aware responses
- Conversation memory (20 messages per session)

### 6. Streaming Chat (SSE)
```bash
POST /api/chat/stream
{
  "message": "Analyze impact of adding hook",
  "session_id": "user-123-session-456",
  "context": {...}
}
```
- Real-time streaming responses
- Progress updates for long operations
- Same features as regular chat

### 7. Clear Conversation Memory
```bash
DELETE /api/chat/memory/{session_id}
```
- Clears conversation history for a session
- Returns success/info status

### 8. AI Assistant Health Check
```bash
GET /api/chat/health
```
- Checks OpenAI API configuration
- Tests connection and model availability
- Reports vector DB and memory status

## 📊 Style Guide Endpoints

### Seed Style Guide (180 rules)
```bash
POST /style-guide/seed
```

### Check Style Guide
```bash
POST /style-guide/check
{
  "content": "Your content",
  "platform": "LinkedIn"
}
```

## 🔍 Diagnostic Endpoints

### Health Check
```bash
GET /health
```

### OpenAPI Docs
```bash
GET /docs
```

## 🎯 Key Features

1. **TRUE Agentic RAG**
   - Agent decides what to search
   - 3-5 autonomous queries per generation
   - No hardcoded rules or patterns

2. **Unique Results**
   - Same input → Different queries
   - Different queries → Different content
   - Zero predetermined outcomes

3. **Real-time Streaming**
   - SSE for batch analysis
   - Progress tracking (0-100%)
   - Instant feedback

4. **Smart Caching**
   - Redis cache for analysis results
   - 5-minute TTL
   - Preload on startup

## 🚨 Error Handling

All endpoints return structured error responses with user-friendly messages:

### Error Types
- `missing_api_key` - "❌ Brak klucza API OpenAI"
- `rate_limit` - "⏳ Przekroczono limit zapytań"
- `timeout` - "⏱️ Przekroczono czas oczekiwania"
- `connection_error` - "🌐 Błąd połączenia"
- `model_error` - "🤖 Niedostępny model"
- `vector_db_error` - "⚠️ Błąd bazy wektorowej"
- `service_unavailable` - "❌ AI Assistant niedostępny"

### Example Error Response
```json
{
  "response": "⏳ Przekroczono limit zapytań do API. Proszę spróbować za chwilę (zwykle 1-2 minuty).",
  "intent": null,
  "context_actions": [],
  "error": "rate_limit"
}
```

## 📋 Requirements

- OpenAI API key required (`OPENAI_API_KEY`)
- ChromaDB must be running (port 8001)
- Redis must be running (port 6380)
- All times are estimates based on OpenAI response times

## 🚀 Performance

- **generate-draft**: 20-50s (with full Agentic RAG)
- **analyze-potential**: 1ms (cached/calculated)
- **chat**: 5-15s (depending on operation)
- **chat/stream**: Real-time streaming
- **analyze-iterative**: 15-30s