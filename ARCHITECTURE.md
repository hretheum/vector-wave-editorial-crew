# Architecture Overview - Kolegium AI Writing Flow

## 🏗️ System Architecture

### Container Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐│
│  │   AI Writing    │  │    ChromaDB     │  │    Redis    ││
│  │     Flow        │  │  Vector Store   │  │    Cache    ││
│  │   (Port 8003)   │  │  (Port 8001)    │  │ (Port 6380) ││
│  └────────┬────────┘  └────────┬────────┘  └──────┬──────┘│
│           │                    │                   │        │
│           └────────────────────┼───────────────────┘        │
│                               │                             │
│                        ┌──────┴──────┐                      │
│                        │   Shared     │                     │
│                        │   Network    │                     │
│                        └─────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Data Flow - TRUE Agentic RAG

### Content Generation Flow
```
User Request
    ↓
generate_draft()
    ↓
analyze_with_iterations() ← TRUE Agentic RAG
    ↓
OpenAI Agent (GPT-4)
    ↓
┌─────────────────────────────────┐
│  Autonomous Decision Loop       │
│  ┌─────────────────────────────┐│
│  │ "I need LinkedIn rules"     ││
│  │         ↓                   ││
│  │ query_style_guide()         ││
│  │         ↓                   ││
│  │ "Now I need hook examples"  ││
│  │         ↓                   ││
│  │ query_style_guide()         ││
│  │         ↓                   ││
│  │ (3-5 iterations)           ││
│  └─────────────────────────────┘│
└─────────────────────────────────┘
    ↓
CrewAI Writer Agent
    ↓
Generated Content (Unique Each Time)
```

## 🧠 AI Agent Architecture

### 1. OpenAI Function Calling Agent (Agentic RAG)
- **Role**: Autonomous style guide researcher
- **Model**: GPT-4-turbo
- **Function**: `search_style_guide`
- **Behavior**: Decides what to search, when to search, when to stop
- **Iterations**: 3-5 autonomous queries

### 2. CrewAI Writer Agent
- **Role**: Content creator
- **Model**: GPT-4 via LangChain
- **Input**: Style guide discoveries from OpenAI agent
- **Output**: Platform-optimized content

### 3. AI Assistant Agent (Chat)
- **Role**: Interactive draft editor
- **Model**: GPT-4
- **Functions**: 
  - `analyze_draft_impact` - Predict metric changes
  - `regenerate_draft_with_suggestions` - Apply edits
- **Memory**: 20 messages per session

## 💾 Data Storage

### ChromaDB Vector Store
- **Collection**: `vector_wave_style_guide`
- **Documents**: 180 style guide rules
- **Source**: Markdown files in `/styleguides`
- **Embedding**: all-MiniLM-L6-v2
- **Query**: Semantic similarity search

### Redis Cache
- **Analysis Cache**: 5-minute TTL
- **Key Format**: `analysis:{folder_name}`
- **Preload Cache**: Content folders on startup
- **Batch Results**: Custom ideas analysis

### In-Memory Storage
- **Conversation Memory**: Session-based chat history
- **Flow Executions**: Diagnostic tracking
- **Max Messages**: 20 per session

## 🔌 API Endpoints

### Core Endpoints
1. `POST /api/generate-draft` - Main content generation with Agentic RAG
2. `POST /api/style-guide/analyze-iterative` - Direct iterative analysis
3. `POST /api/analyze-custom-ideas-stream` - SSE batch analysis
4. `POST /api/chat` - AI Assistant for draft editing
5. `POST /api/chat/stream` - Streaming AI Assistant

### Supporting Endpoints
- `/api/style-guide/seed` - Load rules from files
- `/api/style-guide/check` - Simple style check
- `/api/analyze-potential` - Quick content scoring
- `/api/chat/health` - Service health check
- `/health` - Container health check

## 🚀 Key Design Decisions

### 1. TRUE Agentic RAG
- **Problem**: Previous "agentic" was actually naive with hardcoded queries
- **Solution**: OpenAI Function Calling with autonomous agent loop
- **Result**: Each generation unique, agent decides everything

### 2. Container-First Architecture
- **Problem**: Complex multi-service dependencies
- **Solution**: Docker Compose with health checks
- **Result**: Single command deployment

### 3. Streaming for Long Operations
- **Problem**: 20-50s generation times
- **Solution**: SSE for real-time progress
- **Result**: Better UX with progress tracking

### 4. Smart Caching Strategy
- **Problem**: Expensive AI operations
- **Solution**: Multi-layer cache (preload → Redis → generate)
- **Result**: Instant responses for repeated queries

### 5. Conversation Memory
- **Problem**: No context between messages
- **Solution**: Session-based memory storage
- **Result**: Natural multi-turn conversations

## 📊 Performance Characteristics

### Response Times
- **generate-draft**: 20-50s (with Agentic RAG)
- **analyze-potential**: 1ms (cached/calculated)
- **style-guide/analyze-iterative**: 15-30s
- **chat**: 5-15s (depending on operation)
- **chat/stream**: Real-time streaming

### Resource Usage
- **Memory**: ~2GB (mainly ChromaDB embeddings)
- **CPU**: Spikes during generation
- **Network**: OpenAI API calls (3-8 per generation)

## 🔐 Security Considerations

1. **API Keys**: Environment variables only
2. **Network**: Internal Docker network
3. **Ports**: Minimal exposure (8003 for API)
4. **Data**: No PII stored, only content
5. **Error Handling**: Sanitized error messages

## 🎯 Future Optimizations

1. **Parallel Searches**: Agent could search multiple queries simultaneously
2. **Search Caching**: Cache individual style guide searches
3. **Model Selection**: Use smaller models for simple queries
4. **Batch Generation**: Process multiple drafts in parallel
5. **Persistent Memory**: Move conversation storage to Redis