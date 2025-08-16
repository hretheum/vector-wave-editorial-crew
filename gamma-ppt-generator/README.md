# 🎨 Gamma PPT Generator Service

**Gamma.app API wrapper for AI-powered presentations**  
**Task 4.1.1**: Service foundation (port 8003) with API wrapper and circuit breaker

## 🎯 Overview

This service provides a FastAPI wrapper around the Gamma.app Generate API, enabling AI-powered presentation generation with circuit breaker protection, rate limiting, and cost tracking.

## 🏗️ Features

- **Gamma.app Integration**: Direct API integration for presentation generation
- **Circuit Breaker**: Fault tolerance to prevent wasted API costs
- **Rate Limiting**: Respect Gamma.app's 50/month Beta limit
- **Cost Tracking**: Monitor generation costs and usage
- **Demo Mode**: Test functionality without API key
- **Health Monitoring**: Comprehensive health checks and status endpoints

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker (optional)
- Gamma.app API key (optional for demo mode)

### Environment Variables

```bash
# Required for production
GAMMA_API_KEY=your_gamma_api_key_here

# Optional configuration
HOST=0.0.0.0
SERVICE_PORT=8003
DEBUG=false
```

### Running the Service

#### With Docker
```bash
# Build and run
docker build -t gamma-ppt-generator .
docker run -p 8003:8003 -e GAMMA_API_KEY=your_key gamma-ppt-generator
```

#### Direct Python
```bash
# Install dependencies
pip install -r requirements.txt

# Run service
cd src && python main.py
```

### Demo Mode

The service can run in demo mode without a Gamma API key:

```bash
# Runs with simulated API responses
python src/main.py
```

## 📊 API Endpoints

### Core Endpoints

- `GET /` - Service information and status
- `GET /health` - Health check with API connectivity
- `GET /docs` - Interactive API documentation

### Generation Endpoints

- `POST /generate/presentation` - Generate AI presentation
- `GET /generation/{id}/status` - Check generation status

### System Endpoints

- `POST /test-gamma-connectivity` - Test Gamma.app API connection
- `GET /cost-tracking` - Get cost and usage metrics

## 🎨 Usage Example

### Generate Presentation

```bash
curl -X POST http://localhost:8003/generate/presentation \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "topic": {
      "title": "AI Writing Flow Integration",
      "description": "Advanced multi-platform content generation",
      "keywords": ["AI", "automation", "content"],
      "target_audience": "developers"
    },
    "slides_count": 8,
    "theme": "business",
    "output_formats": ["pdf", "pptx"]
  }'
```

### Health Check

```bash
curl http://localhost:8003/health
```

Response:
```json
{
  "status": "healthy",
  "service": "gamma-ppt-generator",
  "version": "1.0.0",
  "port": 8003,
  "gamma_api_status": "connected",
  "api_calls_remaining": 45,
  "monthly_usage": 5,
  "circuit_breaker_state": "CLOSED"
}
```

## 🔧 Configuration

### Gamma.app API Setup

1. Get API key from https://developers.gamma.app
2. Set `GAMMA_API_KEY` environment variable
3. API limits: 50 generations per month (Beta)

### Circuit Breaker Settings

- **Failure Threshold**: 3 failures before opening
- **Recovery Timeout**: 120 seconds
- **Success Threshold**: 2 successes to close

## 🏗️ Architecture

### Circuit Breaker Pattern

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client API    │───▶│ Circuit Breaker │───▶│  Gamma.app API  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │
                               ▼
                       ┌─────────────────┐
                       │ Cost Protection │
                       │ & Rate Limiting │
                       └─────────────────┘
```

### Service Components

- **FastAPI Application**: HTTP API server
- **Gamma API Client**: HTTP client with connection pooling
- **Circuit Breaker**: Fault tolerance and cost protection
- **Rate Limiter**: API usage control
- **Cost Tracker**: Usage monitoring

## 📈 Monitoring

### Health Check

The service provides comprehensive health monitoring:

```bash
curl http://localhost:8003/health
```

### Cost Tracking

Monitor API usage and costs:

```bash
curl http://localhost:8003/cost-tracking
```

## 🚨 Error Handling

### Circuit Breaker Protection

When Gamma.app API fails repeatedly, the circuit breaker opens to:
- Prevent wasted API calls and costs
- Return immediate errors instead of waiting for timeouts
- Automatically attempt recovery after timeout period

### Rate Limiting

- Tracks monthly usage against Beta limit (50 generations)
- Rejects requests when limit exceeded
- Provides usage statistics in responses

## 🔒 Security

- Bearer token authentication (placeholder for JWT)
- Non-root Docker container
- Input validation with Pydantic models
- API key protection in environment variables

## 📝 Development

### Testing

```bash
# Test API connectivity
python -m pytest tests/ -v

# Test with demo mode
GAMMA_API_KEY="" python src/main.py
```

### Integration with Vector Wave

This service integrates with:
- **Publishing Orchestrator** (port 8080): Presentation service selection
- **Editorial Service** (port 8040): Content validation
- **Analytics Service** (port 8081): Usage tracking

---

**Task 4.1.1 Status**: ✅ **COMPLETED**  
**Service Foundation**: Gamma.app API wrapper with circuit breaker ready for integration

## KPIs i Walidacja

- Health: `GET /health` P95 < 80ms; status 200
- API quota awareness: `api_calls_remaining` exposed in health when real key configured
- Circuit breaker: state remains CLOSED during normal operation

Smoke:
```bash
curl -s http://localhost:8003/health | jq '.status'
```

## References
- docs/integration/PORT_ALLOCATION.md (port 8003)
- docs/GAMMA_INTEGRATION_PLAN.md
- PROJECT_CONTEXT.md
- docs/KPI_VALIDATION_FRAMEWORK.md