# 🚀 AI Kolegium Redakcyjne - Deployment Guide

## 📋 Overview

This guide covers the complete deployment process for AI Kolegium Redakcyjne, from local development to production on Digital Ocean.

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌───────────────┐
│  GitHub Actions │────▶│ ghcr.io      │────▶│ Digital Ocean │
│  (CI/CD)        │     │ (Registry)   │     │ (Production)  │
└─────────────────┘     └──────────────┘     └───────────────┘
                                                     │
                                                     ▼
                                              ┌──────────────┐
                                              │  Watchtower  │
                                              │ (Auto-deploy)│
                                              └──────────────┘
```

## 🛠️ Local Development

### Prerequisites
- Docker Desktop
- Docker Compose v2+
- Python 3.11+
- Node.js 18+ (for frontend)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/kolegium.git
   cd kolegium
   ```

2. **Setup environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start services**
   ```bash
   ./scripts/start-dev.sh
   ```

4. **Verify installation**
   - API: http://localhost:8001/docs
   - Knowledge Base: http://localhost:8082/docs
   - Prometheus: http://localhost:9091
   - Grafana: http://localhost:3001

### Development Workflow

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Run tests
docker-compose exec api pytest

# Stop all services
docker-compose down
```

## 📦 Container Registry Setup

### GitHub Container Registry (ghcr.io)

1. **Create Personal Access Token**
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Create token with `write:packages` permission

2. **Login to registry**
   ```bash
   echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
   ```

3. **Build and push manually (optional)**
   ```bash
   docker build -t ghcr.io/your-org/kolegium-api:latest .
   docker push ghcr.io/your-org/kolegium-api:latest
   ```

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

The pipeline automatically:
1. Runs tests on every push
2. Performs security scanning
3. Builds Docker images
4. Pushes to ghcr.io
5. Deploys to production (main branch)

### Required Secrets

Set these in GitHub repository settings:

```yaml
DO_SSH_KEY          # SSH key for Digital Ocean droplet
DOMAIN_NAME         # Your production domain
SLACK_WEBHOOK       # For deployment notifications
OPENAI_API_KEY      # OpenAI API credentials
SERPER_API_KEY      # Serper API for search
```

## 🌊 Digital Ocean Setup

### 1. Initial Server Setup

```bash
# SSH into server
ssh root@46.101.156.14

# Create user
adduser editorial-ai
usermod -aG sudo editorial-ai
usermod -aG docker editorial-ai

# Setup SSH key
su - editorial-ai
mkdir ~/.ssh
echo "YOUR_PUBLIC_KEY" >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

### 2. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install other tools
sudo apt install -y git nginx certbot python3-certbot-nginx
```

### 3. Clone Repository

```bash
cd /home/editorial-ai
git clone https://github.com/your-org/kolegium.git
cd kolegium
```

### 4. Configure Environment

```bash
# Copy and edit production environment
cp .env.example .env
nano .env  # Add production values
```

### 5. Setup SSL with Let's Encrypt

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

### 6. Configure GitHub Container Registry

```bash
# Login to ghcr.io
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Save credentials for Watchtower
mkdir -p ~/.docker
cp ~/.docker/config.json /root/.docker/config.json
```

## 🚢 Production Deployment

### Manual Deployment

```bash
cd /home/editorial-ai/kolegium
git pull origin main
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

### Automatic Deployment with Watchtower

Watchtower automatically pulls and updates containers when new images are pushed to ghcr.io.

```bash
# Verify Watchtower is running
docker ps | grep watchtower

# View Watchtower logs
docker logs watchtower
```

### Health Checks

```bash
# Check all services
docker-compose -f docker-compose.prod.yml ps

# Check specific service health
curl https://your-domain.com/api/health

# View logs
docker-compose -f docker-compose.prod.yml logs -f api
```

## 📊 Monitoring

### Prometheus Metrics
- URL: https://your-domain.com/prometheus
- Scrapes metrics from all services
- Configured alerts for critical issues

### Grafana Dashboards
- URL: https://your-domain.com/grafana
- Default login: admin/[GRAFANA_PASSWORD]
- Pre-configured dashboards for:
  - System metrics
  - Application performance
  - Knowledge Base queries
  - Agent execution times

### Alerts

Configured alerts notify via Slack for:
- Service downtime
- High error rates
- Memory/CPU issues
- Slow response times

## 🔧 Troubleshooting

### Common Issues

1. **Container won't start**
   ```bash
   docker-compose -f docker-compose.prod.yml logs [service_name]
   ```

2. **Database connection issues**
   ```bash
   docker-compose -f docker-compose.prod.yml exec postgres psql -U kolegium
   ```

3. **Knowledge Base not responding**
   ```bash
   curl http://localhost:8082/api/v1/knowledge/health
   ```

4. **Disk space issues**
   ```bash
   docker system prune -a
   ```

### Emergency Rollback

```bash
# Stop current deployment
docker-compose -f docker-compose.prod.yml down

# Checkout previous version
git checkout HEAD~1

# Redeploy
docker-compose -f docker-compose.prod.yml up -d
```

## 🔐 Security Checklist

- [ ] All secrets in environment variables
- [ ] SSL certificates configured
- [ ] Firewall rules configured
- [ ] Regular security updates
- [ ] Backup strategy in place
- [ ] Log rotation configured
- [ ] Rate limiting enabled
- [ ] CORS properly configured

## 📱 Contact & Support

- **DevOps Lead**: [email]
- **Slack Channel**: #kolegium-ops
- **Documentation**: [wiki link]
- **Emergency**: [phone number]

---

## 🎯 Quick Reference

```bash
# Local development
./scripts/start-dev.sh

# Production deployment
ssh editorial-ai@46.101.156.14
cd /home/editorial-ai/kolegium
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose logs -f [service]

# Emergency stop
docker-compose down
```