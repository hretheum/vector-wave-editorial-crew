#!/bin/bash

# Start development environment for AI Kolegium Redakcyjne

set -e

echo "🚀 Starting AI Kolegium Redakcyjne Development Environment..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please update .env with your configuration"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker Desktop."
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose."
    exit 1
fi

# Start services
echo "🐳 Starting Docker containers..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check health
echo "🔍 Checking service health..."
services=(
    "http://localhost:8082/api/v1/knowledge/health:Knowledge Base"
    "http://localhost:8001/health:API Gateway"
    "http://localhost:9091:Prometheus"
    "http://localhost:3001:Grafana"
)

for service in "${services[@]}"; do
    IFS=':' read -r url name <<< "$service"
    if curl -f -s "$url" > /dev/null; then
        echo "✅ $name is healthy"
    else
        echo "❌ $name is not responding"
    fi
done

echo ""
echo "📊 Services available at:"
echo "   - API: http://localhost:8001"
echo "   - Knowledge Base: http://localhost:8082"
echo "   - Prometheus: http://localhost:9091"
echo "   - Grafana: http://localhost:3001 (admin/admin)"
echo "   - Redis: localhost:6379"
echo "   - PostgreSQL: localhost:5432"
echo ""
echo "📋 View logs: docker-compose logs -f [service_name]"
echo "🛑 Stop all: docker-compose down"
echo ""
echo "✨ Development environment is ready!"