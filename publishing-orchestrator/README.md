# Publishing Orchestrator API v2.0.0

Enhanced multi-platform publishing orchestration with Editorial Service integration.

## Features

- **Multi-platform Support**: LinkedIn, Twitter, BeehiIV, Ghost
- **Editorial Service Integration**: Comprehensive content validation
- **LinkedIn PPT Generation**: Automatic presentation creation for suitable content
- **AI Writing Flow Integration**: Dynamic content generation
- **Publication Status Tracking**: Real-time status monitoring
- **Metrics & Analytics**: Publication success rates and platform usage

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Client Request  │───▶│ Publishing       │───▶│ AI Writing Flow │
│                 │    │ Orchestrator     │    │ (Port 8001)     │
└─────────────────┘    │ (Port 8050)      │    └─────────────────┘
                       │                  │
                       │                  │    ┌─────────────────┐
                       │                  │───▶│ Editorial       │
                       │                  │    │ Service         │
                       │                  │    │ (Port 8040)     │
                       │                  │    └─────────────────┘
                       │                  │
                       │                  │    ┌─────────────────┐
                       │                  │───▶│ LinkedIn PPT    │
                       │                  │    │ Generator       │
                       └──────────────────┘    │ (Port 8002)     │
                                               └─────────────────┘
```

## Quick Start

### Using Docker

```bash
# Build and start orchestrator
docker-compose up -d --build

# Check health
curl http://localhost:8050/health

# View logs
docker-compose logs -f publishing-orchestrator
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
cd src && python main.py

# Server runs on http://localhost:8050
```

## API Endpoints

### Publication

#### `POST /publish`
Create new multi-platform publication.

**Request Body:**
```json
{
  "topic": {
    "title": "AI Writing Flow Integration",
    "description": "Advanced multi-platform content generation",
    "keywords": ["AI", "automation", "content"],
    "target_audience": "developers"
  },
  "platforms": {
    "linkedin": {
      "enabled": true,
      "account_id": "personal",
      "direct_content": false
    },
    "twitter": {
      "enabled": true,
      "account_id": "main",
      "direct_content": true
    }
  },
  "request_id": "optional-tracking-id"
}
```

**Response:**
```json
{
  "publication_id": "pub_12345",
  "request_id": "optional-tracking-id",
  "status": "completed",
  "platform_content": {
    "linkedin": {
      "content": "Generated LinkedIn content...",
      "quality_score": 0.85,
      "validation_compliant": true,
      "generation_time": 2.3
    }
  },
  "scheduled_jobs": {
    "linkedin": "linkedin_job_456"
  },
  "generation_time": 5.7,
  "success_count": 1,
  "error_count": 0
}
```

#### `GET /publication/{publication_id}`
Get publication status and details.

#### `GET /publications`
List recent publications with filtering options.

### System

#### `GET /health`
Health check endpoint.

#### `GET /metrics`
Publishing orchestrator metrics.

#### `GET /queue/status`
Status kolejek publikacji. Jeśli skonfigurowano `REDIS_URL` i dostępny jest klient redis,
zwraca rzeczywiste głębokości kolejek oraz `jobs_by_platform`. W przeciwnym razie zwraca
streszczenie na podstawie pamięci (`publications_store`).

#### `POST /test/simple`
Simple test endpoint for basic functionality validation.

#### `POST /test/publish-gamma`
Trigger LinkedIn flow with presentation generation and Gamma preference.

Request (all fields optional, defaults favor Gamma):
```json
{
  "title": "Architecture Strategy Overview",
  "description": "System architecture and strategy for multi-service publishing",
  "keywords": ["architecture", "system", "strategy"],
  "target_audience": "developers",
  "force_presentation": true,
  "force_gamma": true,
  "direct_content": false
}
```

Notes:
- When `direct_content=false`, orchestrator runs full generation path. With `force_presentation=true` and `force_gamma=true`, it will prefer Gamma (if healthy) and return links under `platform_content.linkedin.manual_upload.assets.{pdf_url,ppt_url}` and `platform_content.linkedin.presentation.provider="gamma"`.
- Health/selection still respects service availability.

## Integration Points

### AI Writing Flow Service (Port 8001)
- Generates platform-specific content
- Uses crew-based approach with research, writing, audience, style, and quality crews
- Provides quality scoring and metadata

### Editorial Service (Port 8040)  
- Comprehensive content validation using ChromaDB rules
- Platform compliance verification
- Grammar, style, and brand voice alignment

### LinkedIn PPT Generator (Port 8002)
- Automatic presentation generation for suitable content
- Triggered for content with architecture, system, framework keywords
- Integrates with LinkedIn posts

## Configuration

### Environment Variables

- `AI_WRITING_FLOW_URL`: URL of AI Writing Flow service (default: http://localhost:8001)
- `LINKEDIN_PPT_GENERATOR_URL`: URL of LinkedIn PPT Generator (default: http://localhost:8002)  
- `EDITORIAL_SERVICE_URL`: URL of Editorial Service (default: http://localhost:8040)
- `ENVIRONMENT`: Runtime environment (development/production)
- `LOG_LEVEL`: Logging level (info/debug/warning/error)

### Platform Configuration

Each platform supports:
- `enabled`: Enable/disable platform
- `account_id`: Platform account identifier  
- `schedule_time`: Optional scheduling (ISO format)
- `direct_content`: Use direct content vs AI generation
- `options`: Platform-specific options

## Content Generation Flow

1. **Request Received**: Parse multi-platform publication request
2. **Content Generation**: 
   - Use AI Writing Flow for dynamic content generation
   - Or use direct content if configured
3. **Editorial Validation**: Validate content with Editorial Service
4. **LinkedIn PPT**: Generate presentation for suitable content
5. **Scheduling**: Schedule publication jobs for each platform
6. **Response**: Return publication status and content variations

## Monitoring & Analytics

- **Success Rate**: Overall publication success percentage
- **Platform Usage**: Usage statistics per platform
- **Generation Time**: Content generation performance metrics
- **Quality Scores**: Average quality scores by platform
- **Error Tracking**: Detailed error logging and categorization

## Testing

### Basic Test
```bash
curl -X POST http://localhost:8050/test/simple
```

### Custom Test
```bash
curl -X POST http://localhost:8050/publish \
  -H "Content-Type: application/json" \
  -d '{
    "topic": {
      "title": "Test Publication",
      "description": "Testing orchestrator"
    },
    "platforms": {
      "linkedin": {
        "enabled": true,
        "account_id": "test",
        "direct_content": true
      }
    }
  }'
```

## Development

### Adding New Platforms

1. Add platform to `PlatformType` enum
2. Implement platform-specific content generation in `generate_platform_content`
3. Add platform-specific scheduling in `schedule_platform_publication`
4. Update validation logic if needed

### Service Integration

All external service calls use async HTTP clients with:
- Timeout handling
- Error recovery
- Circuit breaker pattern (implicit)
- Comprehensive logging

## Deployment

The orchestrator is designed for container-first deployment with:
- Health checks for container orchestration
- Graceful shutdown handling
- Environment-based configuration
- Network isolation support

For production deployment, integrate with:
- Redis for job scheduling
- PostgreSQL for persistence
- Prometheus for metrics
- Grafana for dashboards