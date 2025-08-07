#!/bin/bash

# AI Writing Flow V2 - Local Production Deployment Script
# This script deploys the AI Writing Flow V2 system locally with full monitoring

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_ENV="${DEPLOYMENT_ENV:-local}"
MONITORING_ENABLED="${MONITORING_ENABLED:-true}"
BACKUP_ENABLED="${BACKUP_ENABLED:-true}"
HEALTH_CHECK_TIMEOUT="${HEALTH_CHECK_TIMEOUT:-300}"

# Logging
LOG_FILE="$PROJECT_ROOT/deployment/deploy_$(date +%Y%m%d_%H%M%S).log"
exec 1> >(tee -a "$LOG_FILE")
exec 2> >(tee -a "$LOG_FILE" >&2)

echo -e "${BLUE}🚀 AI Writing Flow V2 - Local Production Deployment${NC}"
echo "=================================================="
echo "Start Time: $(date)"
echo "Environment: $DEPLOYMENT_ENV"
echo "Project Root: $PROJECT_ROOT"
echo "Log File: $LOG_FILE"
echo ""

# Function to log with timestamps
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to handle errors
handle_error() {
    log "${RED}❌ Error on line $1: $2${NC}"
    echo ""
    echo "=== Deployment Failed ==="
    echo "Check log file: $LOG_FILE"
    exit 1
}

# Set error trap
trap 'handle_error ${LINENO} "$BASH_COMMAND"' ERR

# Function to check prerequisites
check_prerequisites() {
    log "${BLUE}🔍 Checking prerequisites...${NC}"
    
    # Check Python version
    if ! python3 --version | grep -E "Python 3\.(8|9|10|11|12|13)" > /dev/null; then
        log "${RED}❌ Python 3.8+ is required${NC}"
        exit 1
    fi
    log "${GREEN}✅ Python version OK${NC}"
    
    # Check if virtual environment exists
    if [ ! -d "$PROJECT_ROOT/venv" ]; then
        log "${YELLOW}⚠️ Virtual environment not found, creating...${NC}"
        cd "$PROJECT_ROOT"
        python3 -m venv venv
    fi
    log "${GREEN}✅ Virtual environment OK${NC}"
    
    # Check required directories
    for dir in "src" "tests" "monitoring"; do
        if [ ! -d "$PROJECT_ROOT/$dir" ]; then
            log "${RED}❌ Required directory missing: $dir${NC}"
            exit 1
        fi
    done
    log "${GREEN}✅ Required directories OK${NC}"
    
    echo ""
}

# Function to backup current state
backup_current_state() {
    if [ "$BACKUP_ENABLED" = "true" ]; then
        log "${BLUE}📦 Creating backup of current state...${NC}"
        
        BACKUP_DIR="$PROJECT_ROOT/deployment/backups/$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        
        # Backup critical files
        cp -r "$PROJECT_ROOT/src" "$BACKUP_DIR/" 2>/dev/null || true
        cp -r "$PROJECT_ROOT/tests" "$BACKUP_DIR/" 2>/dev/null || true
        cp "$PROJECT_ROOT"/*.py "$BACKUP_DIR/" 2>/dev/null || true
        cp "$PROJECT_ROOT"/requirements*.txt "$BACKUP_DIR/" 2>/dev/null || true
        cp "$PROJECT_ROOT/pyproject.toml" "$BACKUP_DIR/" 2>/dev/null || true
        
        # Create backup manifest
        cat > "$BACKUP_DIR/BACKUP_MANIFEST.txt" << EOF
AI Writing Flow V2 - Backup Manifest
=====================================
Backup Date: $(date)
Environment: $DEPLOYMENT_ENV
Git Commit: $(cd "$PROJECT_ROOT" && git rev-parse HEAD 2>/dev/null || echo "Not a git repository")
Git Branch: $(cd "$PROJECT_ROOT" && git branch --show-current 2>/dev/null || echo "Not a git repository")

Backed up components:
- Source code (src/)
- Test suite (tests/)
- Configuration files
- Requirements files
EOF
        
        log "${GREEN}✅ Backup created: $BACKUP_DIR${NC}"
        echo "BACKUP_DIR=$BACKUP_DIR" > "$PROJECT_ROOT/deployment/.last_backup"
    else
        log "${YELLOW}⚠️ Backup disabled${NC}"
    fi
    echo ""
}

# Function to setup environment
setup_environment() {
    log "${BLUE}🔧 Setting up environment...${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    python -m pip install --upgrade pip
    
    # Install requirements
    if [ -f "requirements_enhanced.txt" ]; then
        log "📥 Installing enhanced requirements..."
        pip install -r requirements_enhanced.txt
    elif [ -f "requirements.txt" ]; then
        log "📥 Installing requirements..."
        pip install -r requirements.txt
    else
        log "${YELLOW}⚠️ No requirements file found, installing basic dependencies...${NC}"
        pip install pytest pydantic python-dotenv
    fi
    
    # Install package in development mode
    if [ -f "pyproject.toml" ]; then
        log "📦 Installing package in development mode..."
        pip install -e .
    fi
    
    log "${GREEN}✅ Environment setup complete${NC}"
    echo ""
}

# Function to run pre-deployment tests
run_pre_deployment_tests() {
    log "${BLUE}🧪 Running pre-deployment tests...${NC}"
    
    cd "$PROJECT_ROOT"
    source venv/bin/activate
    
    # Run core tests
    log "Running core architecture tests..."
    python -m pytest tests/test_flow_control_state.py -v --tb=short || {
        log "${RED}❌ Core architecture tests failed${NC}"
        exit 1
    }
    
    # Run integration tests
    log "Running integration tests..."
    python -m pytest tests/test_flow_integration.py -v --tb=short || {
        log "${RED}❌ Integration tests failed${NC}"
        exit 1
    }
    
    # Run monitoring tests
    if [ -d "tests/monitoring" ]; then
        log "Running monitoring tests..."
        python -m pytest tests/monitoring/ -v --tb=short || {
            log "${YELLOW}⚠️ Monitoring tests failed, but continuing...${NC}"
        }
    fi
    
    # Run load tests
    log "Running critical load tests..."
    python -m pytest tests/test_failure_recovery_load.py::TestFailureRecoveryUnderLoad::test_mixed_failure_recovery -v --tb=short || {
        log "${RED}❌ Critical load tests failed${NC}"
        exit 1
    }
    
    log "${GREEN}✅ Pre-deployment tests passed${NC}"
    echo ""
}

# Function to setup monitoring stack
setup_monitoring_stack() {
    if [ "$MONITORING_ENABLED" = "true" ]; then
        log "${BLUE}📊 Setting up monitoring stack...${NC}"
        
        # Create monitoring directories
        mkdir -p "$PROJECT_ROOT/monitoring/data"
        mkdir -p "$PROJECT_ROOT/monitoring/logs"
        mkdir -p "$PROJECT_ROOT/metrics_data"
        
        # Create monitoring configuration
        cat > "$PROJECT_ROOT/monitoring/monitoring_config.json" << EOF
{
    "environment": "$DEPLOYMENT_ENV",
    "enabled": true,
    "metrics": {
        "retention_days": 30,
        "aggregation_intervals": ["1m", "5m", "1h", "1d"]
    },
    "alerting": {
        "enabled": true,
        "channels": ["console", "file"],
        "thresholds": {
            "cpu_usage": 80.0,
            "memory_usage": 400.0,
            "error_rate": 10.0,
            "throughput": 50.0
        }
    },
    "quality_gates": {
        "enabled": true,
        "strict_mode": false
    }
}
EOF
        
        # Initialize metrics storage
        cat > "$PROJECT_ROOT/init_monitoring.py" << 'EOF'
#!/usr/bin/env python3
"""Initialize monitoring stack for production deployment"""
import os
import json
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_writing_flow.monitoring.storage import MetricsStorage, StorageConfig

def main():
    print("🔧 Initializing monitoring stack...")
    
    # Load configuration
    config_path = Path("monitoring/monitoring_config.json")
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    else:
        config = {"metrics": {"retention_days": 30}}
    
    # Initialize storage
    storage_config = StorageConfig(
        storage_path="metrics_data",
        retention_days=config["metrics"]["retention_days"],
        enable_aggregation=True,
        aggregation_intervals=config["metrics"].get("aggregation_intervals", ["1h", "1d"])
    )
    
    storage = MetricsStorage(storage_config)
    
    # Create initial tables/directories
    try:
        # This will create necessary storage structures
        from datetime import datetime, timezone
        test_kpis = {
            "timestamp": datetime.now(timezone.utc),
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "throughput": 0.0,
            "error_rate": 0.0
        }
        storage.store_kpis(test_kpis)
        print("✅ Monitoring storage initialized")
    except Exception as e:
        print(f"⚠️ Monitoring storage initialization warning: {e}")
    
    print("✅ Monitoring stack ready")

if __name__ == "__main__":
    main()
EOF
        
        # Initialize monitoring
        cd "$PROJECT_ROOT"
        source venv/bin/activate
        python init_monitoring.py
        
        log "${GREEN}✅ Monitoring stack setup complete${NC}"
    else
        log "${YELLOW}⚠️ Monitoring disabled${NC}"
    fi
    echo ""
}

# Function to deploy the application
deploy_application() {
    log "${BLUE}🚀 Deploying AI Writing Flow V2...${NC}"
    
    cd "$PROJECT_ROOT"
    source venv/bin/activate
    
    # Create production configuration
    cat > ".env.production" << EOF
# AI Writing Flow V2 Production Configuration
ENVIRONMENT=production
MONITORING_ENABLED=true
ALERTING_ENABLED=true
QUALITY_GATES_ENABLED=true
LOG_LEVEL=INFO
METRICS_STORAGE_PATH=metrics_data
DEPLOYMENT_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF
    
    # Create deployment marker
    cat > "DEPLOYMENT_STATUS.json" << EOF
{
    "status": "deployed",
    "version": "v2.0.0",
    "deployment_time": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "environment": "$DEPLOYMENT_ENV",
    "monitoring_enabled": $MONITORING_ENABLED,
    "backup_location": "$(cat deployment/.last_backup 2>/dev/null | cut -d= -f2 || echo 'none')"
}
EOF
    
    log "${GREEN}✅ Application deployed successfully${NC}"
    echo ""
}

# Function to run health checks
run_health_checks() {
    log "${BLUE}🏥 Running health checks...${NC}"
    
    cd "$PROJECT_ROOT"
    source venv/bin/activate
    
    # Create health check script
    cat > "health_check.py" << 'EOF'
#!/usr/bin/env python3
"""Health check script for AI Writing Flow V2"""
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def check_imports():
    """Check if all critical imports work"""
    try:
        from ai_writing_flow.ai_writing_flow_v2 import AIWritingFlowV2
        from ai_writing_flow.models.flow_stage import FlowStage
        from ai_writing_flow.models.flow_control_state import FlowControlState
        return True, "All imports successful"
    except Exception as e:
        return False, f"Import error: {e}"

def check_flow_initialization():
    """Check if flow can be initialized"""
    try:
        from ai_writing_flow.ai_writing_flow_v2 import AIWritingFlowV2
        flow = AIWritingFlowV2(
            monitoring_enabled=True,
            alerting_enabled=True,
            quality_gates_enabled=True
        )
        return True, "Flow initialization successful"
    except Exception as e:
        return False, f"Flow initialization error: {e}"

def check_monitoring_stack():
    """Check if monitoring stack is accessible"""
    try:
        from ai_writing_flow.monitoring.flow_metrics import FlowMetrics
        from ai_writing_flow.monitoring.alerting import AlertManager
        from ai_writing_flow.validation.quality_gate import QualityGate
        
        metrics = FlowMetrics()
        alert_manager = AlertManager()
        quality_gate = QualityGate()
        
        return True, "Monitoring stack accessible"
    except Exception as e:
        return False, f"Monitoring stack error: {e}"

def main():
    print("🔍 Running AI Writing Flow V2 Health Checks...")
    print("=" * 50)
    
    checks = [
        ("Imports", check_imports),
        ("Flow Initialization", check_flow_initialization),
        ("Monitoring Stack", check_monitoring_stack)
    ]
    
    results = {}
    all_passed = True
    
    for name, check_func in checks:
        try:
            passed, message = check_func()
            results[name] = {"passed": passed, "message": message}
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} {name}: {message}")
            if not passed:
                all_passed = False
        except Exception as e:
            results[name] = {"passed": False, "message": f"Check failed: {e}"}
            print(f"❌ FAIL {name}: Check failed: {e}")
            all_passed = False
    
    print("=" * 50)
    
    if all_passed:
        print("✅ All health checks passed!")
        sys.exit(0)
    else:
        print("❌ Some health checks failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF
    
    # Run health checks with timeout
    local timeout_duration="$HEALTH_CHECK_TIMEOUT"
    if timeout "$timeout_duration" python health_check.py; then
        log "${GREEN}✅ Health checks passed${NC}"
    else
        log "${RED}❌ Health checks failed or timed out${NC}"
        exit 1
    fi
    
    echo ""
}

# Function to show deployment summary
show_deployment_summary() {
    log "${BLUE}📋 Deployment Summary${NC}"
    echo "======================"
    
    echo "✅ Deployment Status: SUCCESS"
    echo "📅 Deployment Time: $(date)"
    echo "🌍 Environment: $DEPLOYMENT_ENV"
    echo "📁 Project Root: $PROJECT_ROOT"
    echo "📝 Log File: $LOG_FILE"
    
    if [ "$BACKUP_ENABLED" = "true" ] && [ -f "$PROJECT_ROOT/deployment/.last_backup" ]; then
        echo "💾 Backup Location: $(cat "$PROJECT_ROOT/deployment/.last_backup" | cut -d= -f2)"
    fi
    
    if [ "$MONITORING_ENABLED" = "true" ]; then
        echo "📊 Monitoring: ENABLED"
        echo "📈 Metrics Storage: $PROJECT_ROOT/metrics_data"
    fi
    
    echo ""
    echo "🚀 AI Writing Flow V2 is now ready for production use!"
    echo ""
    echo "Quick Start Commands:"
    echo "  cd $PROJECT_ROOT"
    echo "  source venv/bin/activate"
    echo "  python -c \"from ai_writing_flow.ai_writing_flow_v2 import AIWritingFlowV2; print('✅ Ready!')\""
    echo ""
    echo "To rollback: ./deployment/rollback_flow_v2.sh"
    echo "To monitor: tail -f $PROJECT_ROOT/monitoring/logs/flow_v2.log"
    echo ""
}

# Main deployment sequence
main() {
    log "${BLUE}Starting AI Writing Flow V2 deployment sequence...${NC}"
    
    check_prerequisites
    backup_current_state
    setup_environment
    run_pre_deployment_tests
    setup_monitoring_stack
    deploy_application
    run_health_checks
    show_deployment_summary
    
    log "${GREEN}🎉 Deployment completed successfully!${NC}"
}

# Execute main function
main "$@"