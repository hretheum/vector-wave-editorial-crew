# AI Writing Flow Service

## Overview
AI Writing Flow is a content generation service that uses CrewAI agents to create optimized content for various platforms.

## Features
- Content generation via `/generate` endpoint
- Content processing and enhancement via `/process` endpoint
- Integration with Editorial Service for validation
- Support for multiple platforms (LinkedIn, Twitter, etc.)
- Configurable validation modes (selective/comprehensive)

## API Endpoints

### Health Check
```
GET /health
```
Returns service health status and dependencies.

### Generate Content
```
POST /generate
{
    "topic_title": "string",
    "topic_description": "string",
    "platform": "string",
    "viral_score": 7.5
}
```
Generates new content based on topic information.

### Process Content
```
POST /process
{
    "content": "string",
    "platform": "string",
    "topic": {},
    "validation_mode": "selective"
}
```
Processes existing content through the AI pipeline.

## Configuration

Environment variables:
- `EDITORIAL_SERVICE_URL`: URL of Editorial Service (default: `http://editorial-service:8040`)
- `OPENAI_API_KEY`: OpenAI API key for content generation
- `SERVICE_PORT`: Service port (default: `8003`)

## Integration with Orchestrator

The AI Writing Flow integrates with CrewAI Orchestrator via the `/publish` endpoint:

```
POST /publish
{
    "topic": {
        "title": "Topic Title",
        "description": "Topic description",
        "viral_score": 8.0
    },
    "platform": "linkedin",
    "direct_content": false
}
```

When `direct_content=false`, the orchestrator will use AI Writing Flow to generate content.

## Testing

Run smoke tests:
```bash
./scripts/test_ai_writing_flow_integration.sh
```

## Docker

Build and run:
```bash
docker-compose up ai-writing-flow
```

The service will be available at `http://localhost:8003`.