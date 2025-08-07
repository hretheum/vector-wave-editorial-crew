# 🚨 CRITICAL: WORKING BACKEND STATE DOCUMENTATION

## ⚠️ DO NOT MODIFY WITHOUT READING THIS FIRST ⚠️

### 📍 Working Version Information
- **Commit ID**: `2c960c1`
- **Timestamp**: 2025-08-05 16:44:00 CEST
- **Previous Working Commit**: `ec9a64e` (base for this version)
- **Status**: ✅ FULLY FUNCTIONAL WITH REAL CREWAI + OPENAI

### 🎯 What This Version Contains

#### ✅ Working Components:
1. **FastAPI Backend** on port 8003
2. **Real CrewAI Agents** with OpenAI GPT-4
3. **Docker Container** with all dependencies
4. **Hot Reload** for development

#### ✅ Working Endpoints:

##### 1. `/api/execute-flow` - Complete AI Writing Flow
```bash
# ORIGINAL content (skips research)
curl -X POST http://localhost:8003/api/execute-flow \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My AI Journey",
    "content_ownership": "ORIGINAL",
    "platform": "LinkedIn"
  }'

# EXTERNAL content (includes research)
curl -X POST http://localhost:8003/api/execute-flow \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Kubernetes Best Practices",
    "content_ownership": "EXTERNAL",
    "content_type": "TECHNICAL",
    "platform": "Blog"
  }'
```

##### 2. `/api/research` - Research Agent
```bash
curl -X POST http://localhost:8003/api/research \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Container Security Best Practices",
    "depth": "deep",
    "skip_research": false
  }'
```

##### 3. `/api/generate-draft` - Writer Agent
```bash
curl -X POST http://localhost:8003/api/generate-draft \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "title": "AI Revolution",
      "platform": "LinkedIn",
      "content_type": "STANDARD"
    },
    "research_data": null
  }'
```

### 🔧 Configuration

#### Environment Variables:
```bash
OPENAI_API_KEY=your-openai-api-key-here
```

#### Docker Setup:
```yaml
# docker-compose.minimal.yml
services:
  ai-writing-flow:
    build:
      context: .
      dockerfile: Dockerfile.minimal
    ports:
      - "8003:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./app.py:/app/app.py  # Hot reload
```

### 🚀 How to Run

```bash
# Start container
docker-compose -f docker-compose.minimal.yml up -d

# Check logs
docker logs kolegium-ai-writing-flow-1 -f

# Test health
curl http://localhost:8003/health

# Stop container
docker-compose -f docker-compose.minimal.yml down
```

### ⚠️ Common Issues & Solutions

1. **Import Errors**: DO NOT modify imports or add CrewAI flow imports
2. **NameError**: GenerateDraftRequest is already defined, don't duplicate
3. **Container not responding**: Check OPENAI_API_KEY in environment
4. **Hot reload not working**: Restart container with docker-compose restart

### 📝 Key Files

1. **app.py** - Main FastAPI application with CrewAI agents
2. **Dockerfile.minimal** - Container definition with dependencies
3. **docker-compose.minimal.yml** - Container orchestration
4. **requirements-crewai.txt** - Python dependencies including CrewAI

### ❌ DO NOT:
- Import ai_writing_flow modules (they're not needed)
- Modify CrewAI agent definitions
- Change port mappings
- Update dependencies without testing

### ✅ Safe to Modify:
- Add new endpoints (but keep existing ones)
- Add logging
- Add error handling
- Update prompts in agents

### 🔄 Recovery Instructions

If something breaks:
```bash
# Restore this exact version
git checkout 2c960c1 -- app.py docker-compose.minimal.yml Dockerfile.minimal requirements-crewai.txt

# Rebuild container
docker-compose -f docker-compose.minimal.yml build --no-cache

# Restart
docker-compose -f docker-compose.minimal.yml up -d
```

---

**REMEMBER**: This is the ONLY version that works properly with real CrewAI before frontend integration. Always backup before making changes!