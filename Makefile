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