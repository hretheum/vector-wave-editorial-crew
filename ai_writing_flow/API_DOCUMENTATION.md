# AI Writing Flow V2 API Documentation

## Overview

The AI Writing Flow V2 API provides REST endpoints for executing and monitoring writing flows with comprehensive observability. The API maintains backward compatibility with V1 while providing enhanced V2 features.

**Base URL:** `http://localhost:8000`  
**API Version:** 2.0.0  
**Documentation:** Available at `/docs` (OpenAPI/Swagger)

## Quick Start

### 1. Start the API Server

```bash
# Using FastAPI directly
python -c "
from ai_writing_flow.api.endpoints import create_flow_app
import uvicorn
app = create_flow_app()
uvicorn.run(app, host='0.0.0.0', port=8000)
"

# Server will start at http://localhost:8000
# Interactive documentation at http://localhost:8000/docs
```

### 2. Execute a Flow

```bash
# V2 API (recommended)
curl -X POST "http://localhost:8000/api/v2/flows/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "topic_title": "AI Writing Flow V2 Features",
    "platform": "LinkedIn",
    "content_type": "STANDALONE",
    "monitoring_enabled": true,
    "quality_gates_enabled": true
  }'

# Legacy V1 API (backward compatibility)
curl -X POST "http://localhost:8000/api/v1/kickoff" \
  -H "Content-Type: application/json" \
  -d '{
    "topic_title": "Legacy API Test",
    "platform": "LinkedIn"
  }'
```

## V2 API Endpoints

### Flow Execution

#### `POST /api/v2/flows/execute`

Execute AI Writing Flow V2 with full monitoring.

**Request Body:**
```json
{
  "topic_title": "string",                    // Required: Content topic
  "platform": "LinkedIn",                     // Target platform
  "file_path": "content/input.md",           // Optional input file
  "content_type": "STANDALONE",              // Content type
  "content_ownership": "EXTERNAL",           // Ownership type
  "viral_score": 8.0,                       // Expected viral score
  "editorial_recommendations": "string",      // Editorial guidance
  "skip_research": false,                    // Skip research phase
  "monitoring_enabled": true,                // Enable monitoring
  "alerting_enabled": true,                  // Enable alerting
  "quality_gates_enabled": true              // Enable quality gates
}
```

**Response:**
```json
{
  "flow_id": "flow_1704067200",
  "status": "completed",                     // "completed", "failed", "error"
  "message": "Flow executed successfully",
  "final_draft": "Generated content...",
  "metrics": {
    "execution_time": 25.4,                 // Seconds
    "quality_score": 85,                    // 0-100
    "style_score": 92,                      // 0-100
    "revision_count": 2,                    // Number of revisions
    "agents_executed": 5,                   // Number of agents run
    "word_count": 450                       // Final word count
  },
  "errors": [],                             // Error messages if any
  "execution_time": 25.4
}
```

### Flow Status

#### `GET /api/v2/flows/{flow_id}/status`

Get status of specific flow execution.

**Response:**
```json
{
  "flow_id": "flow_1704067200",
  "status": "running",                      // "running", "completed", "failed", "not_found"
  "current_stage": "draft_generation",      // Current stage name
  "progress_percent": 60.0,                // Progress percentage
  "start_time": "2025-01-01T12:00:00Z",   // ISO format
  "end_time": null,                        // null if still running
  "metrics": {
    "stages_completed": 3,
    "total_stages": 5
  },
  "errors": []
}
```

### System Health

#### `GET /api/v2/health`

Comprehensive system health check.

**Response:**
```json
{
  "status": "healthy",                      // "healthy", "warning", "critical"
  "timestamp": "2025-01-01T12:00:00Z",
  "version": "2.0.0",
  "components": {
    "linear_flow": "healthy",
    "monitoring": "healthy",
    "alerting": "healthy",
    "quality_gates": "healthy"
  },
  "uptime_seconds": 3600.0,
  "api_statistics": {
    "total_requests": 150,
    "successful_executions": 142,
    "failed_executions": 8,
    "success_rate": 94.67,
    "active_flows": 2,
    "cached_results": 100
  }
}
```

### Monitoring Dashboard

#### `GET /api/v2/dashboard/metrics`

Get real-time dashboard metrics.

**Response:**
```json
{
  "monitoring_enabled": true,
  "dashboard_metrics": {
    "current_kpis": {
      "cpu_usage": 15.2,                   // Percentage
      "memory_usage": 89.5,                // MB
      "response_time": 156.3,              // Milliseconds
      "error_rate": 2.1,                   // Percentage
      "throughput": 125.7                  // Operations/second
    },
    "time_series_data": {
      "last_hour": [...],                  // Hourly data points
      "last_day": [...]                    // Daily data points
    }
  },
  "alert_statistics": {
    "active_alerts": 0,
    "total_alerts_24h": 3,
    "resolved_alerts_24h": 3
  },
  "api_metrics": {
    "total_requests": 150,
    "request_rate": 2.5,                   // Requests per minute
    "active_flows": 2,
    "cached_results": 100
  }
}
```

### Flow Listing

#### `GET /api/v2/flows`

List recent flow executions.

**Query Parameters:**
- `limit` (integer): Maximum flows to return (default: 50)
- `status` (string): Filter by status ("completed", "failed", "running")

**Response:**
```json
{
  "flows": [
    {
      "flow_id": "flow_1704067200",
      "status": "completed",
      "topic_title": "AI Writing Flow Features",
      "execution_time": 25.4,
      "word_count": 450,
      "quality_score": 85
    }
  ],
  "total_count": 45,
  "active_count": 2,
  "completed_count": 142,
  "failed_count": 8
}
```

## Legacy V1 API (Backward Compatibility)

### `POST /api/v1/kickoff`

Legacy flow execution endpoint.

**Request Body:**
```json
{
  "topic_title": "string",
  "platform": "LinkedIn",
  "file_path": "optional/path.md",
  "content_type": "STANDALONE",
  "viral_score": 8.0
}
```

**Response:**
```json
{
  "success": true,
  "flow_id": "flow_1704067200",
  "final_draft": "Generated content...",
  "metrics": {
    "execution_time": 25.4,
    "quality_score": 85
  },
  "execution_time": 25.4,
  "error_message": null
}
```

### `GET /api/v1/health`

Legacy health check.

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0"
}
```

## Error Handling

### HTTP Status Codes

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request data
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

### Error Response Format

```json
{
  "detail": "Error description",
  "error_code": "VALIDATION_ERROR",
  "context": {
    "field": "topic_title",
    "issue": "Field required"
  }
}
```

## Authentication

Currently, the API runs without authentication for development. For production deployment:

1. **API Keys**: Add API key validation
2. **JWT Tokens**: Implement token-based authentication
3. **Rate Limiting**: Configure request rate limits
4. **CORS**: Adjust CORS settings for production

## Production Configuration

### Environment Variables

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Monitoring
MONITORING_ENABLED=true
ALERTING_ENABLED=true
QUALITY_GATES_ENABLED=true
METRICS_STORAGE_PATH=/data/metrics

# Knowledge Base
KB_API_URL=http://localhost:8082
KB_TIMEOUT=5.0

# Performance
MAX_CONCURRENT_FLOWS=10
FLOW_TIMEOUT_SECONDS=300
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "-c", "from ai_writing_flow.api.endpoints import create_flow_app; import uvicorn; app = create_flow_app(); uvicorn.run(app, host='0.0.0.0', port=8000, workers=4)"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-writing-flow-v2
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-writing-flow-v2
  template:
    metadata:
      labels:
        app: ai-writing-flow-v2
    spec:
      containers:
      - name: api
        image: ai-writing-flow-v2:latest
        ports:
        - containerPort: 8000
        env:
        - name: MONITORING_ENABLED
          value: "true"
        - name: METRICS_STORAGE_PATH
          value: "/data/metrics"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: ai-writing-flow-v2-service
spec:
  selector:
    app: ai-writing-flow-v2
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Monitoring & Observability

### Prometheus Metrics

The API exposes Prometheus-compatible metrics at `/metrics`:

```
# Flow execution metrics
flow_executions_total{status="completed"} 142
flow_executions_total{status="failed"} 8
flow_execution_duration_seconds_bucket{le="30"} 140

# API metrics
api_requests_total{method="POST",endpoint="/api/v2/flows/execute"} 150
api_request_duration_seconds_bucket{le="0.5"} 145

# System metrics
system_cpu_usage_percent 15.2
system_memory_usage_bytes 93847552
```

### Grafana Dashboard

Sample Grafana queries:

```promql
# Flow success rate
rate(flow_executions_total{status="completed"}[5m]) / rate(flow_executions_total[5m]) * 100

# API response times
histogram_quantile(0.95, api_request_duration_seconds_bucket)

# Active flows
flow_active_count

# System resources
system_cpu_usage_percent
system_memory_usage_bytes / 1024 / 1024
```

### Log Aggregation

Structured JSON logs are output to stdout:

```json
{
  "timestamp": "2025-01-01T12:00:00Z",
  "level": "INFO",
  "logger": "ai_writing_flow.api",
  "message": "Flow execution completed",
  "flow_id": "flow_1704067200",
  "execution_time": 25.4,
  "status": "completed"
}
```

## Testing

### Unit Tests

```bash
# Run API tests
pytest tests/api/ -v

# Run integration tests
pytest tests/integration/ -v

# Run with coverage
pytest --cov=ai_writing_flow.api tests/ --cov-report=html
```

### Load Testing

```bash
# Using Apache Bench
ab -n 100 -c 10 -H "Content-Type: application/json" \
   -p test_payload.json \
   http://localhost:8000/api/v2/flows/execute

# Using wrk
wrk -t4 -c100 -d30s -s post.lua http://localhost:8000/api/v2/flows/execute
```

## Support

- **Documentation**: Interactive API docs at `/docs`
- **Health Check**: GET `/api/v2/health`
- **Metrics**: GET `/api/v2/dashboard/metrics`
- **GitHub Issues**: [Report issues](https://github.com/your-org/ai-writing-flow)
- **API Version**: 2.0.0

## Migration from V1

### Breaking Changes

1. **Response Format**: V2 uses different response structure
2. **Error Handling**: Enhanced error messages with context
3. **Monitoring**: Built-in metrics and health checks
4. **Quality Gates**: Pre/post execution validation

### Migration Steps

1. **Test V1 Compatibility**: Ensure existing integrations work with `/api/v1/` endpoints
2. **Update Clients**: Gradually migrate to V2 endpoints for new features
3. **Monitor Performance**: Use new monitoring endpoints to track performance
4. **Enable Quality Gates**: Gradually enable validation rules

### Example Migration

```python
# Old V1 client
import requests

response = requests.post("http://localhost:8000/api/v1/kickoff", json={
    "topic_title": "Test Topic",
    "platform": "LinkedIn"
})

result = response.json()
success = result["success"]
content = result["final_draft"]

# New V2 client
response = requests.post("http://localhost:8000/api/v2/flows/execute", json={
    "topic_title": "Test Topic",
    "platform": "LinkedIn",
    "monitoring_enabled": True,
    "quality_gates_enabled": True
})

result = response.json()
success = result["status"] == "completed"
content = result["final_draft"]
metrics = result["metrics"]
```

---

*API Documentation generated for AI Writing Flow V2 - Production Ready System*