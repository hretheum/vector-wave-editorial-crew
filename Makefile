.PHONY: container-build container-test container-up container-down

container-build:
	docker build -f Dockerfile.minimal -t ai-writing-flow:minimal .

container-up:
	docker compose -f docker-compose.minimal.yml up -d
	@echo "Waiting for container to be ready..."
	@for i in {1..30}; do \
		if curl -s http://localhost:8003/health > /dev/null; then \
			echo "Container is ready!"; \
			break; \
		fi; \
		sleep 2; \
	done

container-test: container-up
	pytest tests/test_container_api.py -v
	
container-down:
	docker compose -f docker-compose.minimal.yml down

container-full-test: container-build container-test container-down
	@echo "✅ All container tests passed!"

# Quick test routing
test-routing:
	@echo "Testing ORIGINAL (should skip research):"
	@curl -s -X POST http://localhost:8003/api/test-routing \
		-H "Content-Type: application/json" \
		-d '{"title": "Test", "content_ownership": "ORIGINAL"}' | jq .
	
	@echo "\nTesting EXTERNAL (should do research):"
	@curl -s -X POST http://localhost:8003/api/test-routing \
		-H "Content-Type: application/json" \
		-d '{"title": "Test", "content_ownership": "EXTERNAL"}' | jq .

logs:
	docker compose -f docker-compose.minimal.yml logs -f

clean:
	docker compose -f docker-compose.minimal.yml down
	docker rmi ai-writing-flow:minimal || true

# Test Flow Diagnostics
test-diagnostics:
	@echo "Testing Flow Diagnostics with ORIGINAL content:"
	@curl -s -X POST http://localhost:8003/api/execute-flow-tracked \
		-H "Content-Type: application/json" \
		-d '{"title": "My AI Journey", "content_ownership": "ORIGINAL", "platform": "LinkedIn"}' | jq .
	
	@echo "\nTesting Flow Diagnostics with EXTERNAL content:"
	@curl -s -X POST http://localhost:8003/api/execute-flow-tracked \
		-H "Content-Type: application/json" \
		-d '{"title": "Kubernetes Best Practices", "content_ownership": "EXTERNAL", "content_type": "TECHNICAL"}' | jq .

list-flows:
	@echo "Recent flow executions:"
	@curl -s http://localhost:8003/api/flow-diagnostics?limit=5 | jq .

# Test Writer Agent
test-writer:
	@echo "Testing Writer Agent without research:"
	@curl -s -X POST http://localhost:8003/api/generate-draft \
		-H "Content-Type: application/json" \
		-d '{"content": {"title": "5 AI Productivity Tips", "platform": "LinkedIn"}}' | jq .

test-writer-research:
	@echo "Testing Writer Agent with research data:"
	@curl -s -X POST http://localhost:8003/api/generate-draft \
		-H "Content-Type: application/json" \
		-d '{"content": {"title": "AI Tools Review", "platform": "Blog", "content_type": "TECHNICAL"}, "research_data": {"findings": {"summary": "Top AI tools in 2025 include GPT-4, Claude, and Gemini"}}}' | jq .

test-complete-flow:
	@echo "Testing complete flow (routing -> research -> writing):"
	@curl -s -X POST http://localhost:8003/api/execute-flow \
		-H "Content-Type: application/json" \
		-d '{"title": "Future of Work", "content_ownership": "EXTERNAL", "platform": "LinkedIn"}' | jq .

all: clean container-build container-up test-routing

# --- Local CI parity helpers ---
.PHONY: act-aiwf act-api docker-test-aiwf docker-test-api

# Run GH Actions test job locally (ai_writing_flow)
act-aiwf:
	@command -v act >/dev/null 2>&1 || { echo "❌ 'act' not found. Install: brew install act"; exit 1; }
	@echo "🏃 Running GH Actions test job for ai_writing_flow via act..."
	@act --container-architecture linux/amd64 --bind \
	  -j test-python --matrix service:ai_writing_flow

# Run GH Actions test job locally (api)
act-api:
	@command -v act >/dev/null 2>&1 || { echo "❌ 'act' not found. Install: brew install act"; exit 1; }
	@echo "🏃 Running GH Actions test job for api via act..."
	@act --container-architecture linux/amd64 --bind \
	  -j test-python --matrix service:api

# Run tests in Docker (Python 3.11), mirrors CI job
docker-test-aiwf:
	@echo "🐳 Running ai_writing_flow tests in Docker (Python 3.11)..."
	@SERVICE=ai_writing_flow docker compose -f docker-compose.test.yml run --rm test-python-3.11

docker-test-api:
	@echo "🐳 Running api tests in Docker (Python 3.11)..."
	@SERVICE=api docker compose -f docker-compose.test.yml run --rm test-python-3.11