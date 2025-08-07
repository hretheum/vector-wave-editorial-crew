# OpenAPI Documentation Usage

## Interactive Documentation

### Swagger UI
Access interactive API documentation at: http://localhost:8003/docs

Features:
- Try out endpoints directly from browser
- See request/response schemas
- View example payloads
- Test authentication (when implemented)

### ReDoc
Alternative documentation at: http://localhost:8003/redoc

Features:
- Clean, readable documentation
- Better for printing/PDF export
- Three-panel layout
- Search functionality

## OpenAPI JSON

### Get Full Schema
```bash
curl http://localhost:8003/openapi.json > openapi.json
```

### Generate Client Code

Using OpenAPI Generator:
```bash
# Install openapi-generator
brew install openapi-generator

# Generate Python client
openapi-generator generate \
  -i http://localhost:8003/openapi.json \
  -g python \
  -o ./generated-client

# Generate TypeScript client
openapi-generator generate \
  -i http://localhost:8003/openapi.json \
  -g typescript-axios \
  -o ./generated-client-ts
```

### Import to Postman
1. Open Postman
2. Click "Import" → "Link"
3. Enter: `http://localhost:8003/openapi.json`
4. Collection with all endpoints will be created

### Generate API Tests

Using Dredd:
```bash
# Install dredd
npm install -g dredd

# Generate test blueprint
dredd init

# Run API tests
dredd http://localhost:8003/openapi.json http://localhost:8003
```

## Key Endpoints by Tag

### Content Operations
- `POST /api/analyze-potential` - Ultra-fast content analysis (1ms)
- `POST /api/generate-draft` - Generate content with AI
- `GET /api/list-content-folders` - List available content

### Research
- `POST /api/research` - Deep research on topics

### Flow Execution
- `POST /api/execute-flow` - Complete content flow
- `POST /api/execute-flow-tracked` - Flow with diagnostics

### Diagnostics
- `GET /api/flow-diagnostics` - List recent executions
- `GET /api/flow-diagnostics/{flow_id}` - Detailed flow analysis

### Health
- `GET /health` - Container health check
- `GET /api/verify-openai` - Verify AI integration

## Performance Expectations

| Endpoint | Response Time | AI Calls |
|----------|--------------|----------|
| `/api/analyze-potential` | ~1ms | No |
| `/api/generate-draft` (ORIGINAL) | ~20s | Yes |
| `/api/generate-draft` (EXTERNAL) | ~25s | Yes |
| `/api/research` | 2-3s | Yes |
| `/api/execute-flow` | 25-50s | Yes |

## Example Workflow

1. List available content:
```bash
curl http://localhost:8003/api/list-content-folders
```

2. Analyze content potential:
```bash
curl -X POST http://localhost:8003/api/analyze-potential \
  -H "Content-Type: application/json" \
  -d '{"folder": "2025-07-31-adhd-ideas"}'
```

3. Generate draft for best topic:
```bash
curl -X POST http://localhost:8003/api/generate-draft \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "title": "5 ADHD Productivity Hacks",
      "platform": "LinkedIn",
      "content_ownership": "ORIGINAL"
    },
    "skip_research": true
  }'
```

## Schema Validation

The OpenAPI schema includes:
- Request/response models with descriptions
- Field validations and defaults
- Enum values for constrained fields
- Optional vs required fields
- Example values

Use the schema to:
- Validate requests before sending
- Generate strongly-typed clients
- Create mock servers for testing
- Document integrations