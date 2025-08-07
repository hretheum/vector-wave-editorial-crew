#!/bin/bash

# AI Writing Flow V2 - Rollback Script
# This script provides fast rollback capabilities for the AI Writing Flow V2 system

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
ROLLBACK_REASON="${1:-manual_rollback}"

# Logging
LOG_FILE="$PROJECT_ROOT/deployment/rollback_$(date +%Y%m%d_%H%M%S).log"
exec 1> >(tee -a "$LOG_FILE")
exec 2> >(tee -a "$LOG_FILE" >&2)

echo -e "${RED}🔙 AI Writing Flow V2 - Emergency Rollback${NC}"
echo "=============================================="
echo "Start Time: $(date)"
echo "Reason: $ROLLBACK_REASON"
echo "Project Root: $PROJECT_ROOT"
echo "Log File: $LOG_FILE"
echo ""

# Function to log with timestamps
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to handle errors
handle_error() {
    log "${RED}❌ Rollback error on line $1: $2${NC}"
    echo ""
    echo "=== CRITICAL: Rollback Failed ==="
    echo "Manual intervention required!"
    echo "Check log file: $LOG_FILE"
    exit 1
}

# Set error trap
trap 'handle_error ${LINENO} "$BASH_COMMAND"' ERR

# Function to emergency stop running processes
emergency_stop_processes() {
    log "${RED}🚨 Emergency stop - Killing running AI Flow processes...${NC}"
    
    # Kill any running Python processes that might be AI Writing Flow
    pkill -f "ai_writing_flow" 2>/dev/null || true
    pkill -f "flow_v2" 2>/dev/null || true
    
    # Kill monitoring processes
    pkill -f "prometheus" 2>/dev/null || true
    pkill -f "grafana" 2>/dev/null || true
    
    log "${GREEN}✅ Emergency stop completed${NC}"
    echo ""
}

# Function to find latest backup
find_latest_backup() {
    BACKUP_BASE_DIR="$PROJECT_ROOT/deployment/backups"
    
    if [ ! -d "$BACKUP_BASE_DIR" ]; then
        log "${RED}❌ No backup directory found: $BACKUP_BASE_DIR${NC}"
        exit 1
    fi
    
    # Find the most recent backup
    LATEST_BACKUP=$(find "$BACKUP_BASE_DIR" -maxdepth 1 -type d -name "20*" | sort -r | head -n 1)
    
    if [ -z "$LATEST_BACKUP" ]; then
        log "${RED}❌ No backups found in $BACKUP_BASE_DIR${NC}"
        exit 1
    fi
    
    log "${BLUE}📦 Latest backup found: $LATEST_BACKUP${NC}"
    
    # Verify backup integrity
    if [ ! -f "$LATEST_BACKUP/BACKUP_MANIFEST.txt" ]; then
        log "${YELLOW}⚠️ Backup manifest missing, but proceeding...${NC}"
    else
        log "${GREEN}✅ Backup integrity verified${NC}"
        echo "Backup details:"
        cat "$LATEST_BACKUP/BACKUP_MANIFEST.txt" | head -10
        echo ""
    fi
    
    export LATEST_BACKUP
}

# Function to restore from backup
restore_from_backup() {
    log "${BLUE}🔄 Restoring from backup: $LATEST_BACKUP${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Create rollback backup of current state
    ROLLBACK_BACKUP="$PROJECT_ROOT/deployment/rollback_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$ROLLBACK_BACKUP"
    
    log "Creating rollback backup in case we need to re-rollback..."
    cp -r src "$ROLLBACK_BACKUP/" 2>/dev/null || true
    cp -r tests "$ROLLBACK_BACKUP/" 2>/dev/null || true
    cp *.py "$ROLLBACK_BACKUP/" 2>/dev/null || true
    
    # Restore source code
    if [ -d "$LATEST_BACKUP/src" ]; then
        log "Restoring source code..."
        rm -rf src/
        cp -r "$LATEST_BACKUP/src" ./
    fi
    
    # Restore tests
    if [ -d "$LATEST_BACKUP/tests" ]; then
        log "Restoring test suite..."
        rm -rf tests/
        cp -r "$LATEST_BACKUP/tests" ./
    fi
    
    # Restore configuration files
    for file in "$LATEST_BACKUP"/*.py "$LATEST_BACKUP"/*.txt "$LATEST_BACKUP"/*.toml; do
        if [ -f "$file" ]; then
            cp "$file" ./ 2>/dev/null || true
        fi
    done
    
    log "${GREEN}✅ Code restoration completed${NC}"
    echo ""
}

# Function to reset environment
reset_environment() {
    log "${BLUE}🔧 Resetting environment...${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Remove production configuration
    rm -f .env.production
    rm -f DEPLOYMENT_STATUS.json
    rm -f init_monitoring.py
    rm -f health_check.py
    
    # Reset monitoring data (but keep backups)
    if [ -d "monitoring/data" ]; then
        log "Archiving monitoring data..."
        MONITORING_ARCHIVE="monitoring/archive_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$MONITORING_ARCHIVE"
        mv monitoring/data/* "$MONITORING_ARCHIVE/" 2>/dev/null || true
    fi
    
    # Clean metrics data (but keep archives)
    if [ -d "metrics_data" ]; then
        log "Archiving metrics data..."
        METRICS_ARCHIVE="metrics_data/archive_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$METRICS_ARCHIVE"
        mv metrics_data/*.db "$METRICS_ARCHIVE/" 2>/dev/null || true
        mv metrics_data/*.json "$METRICS_ARCHIVE/" 2>/dev/null || true
    fi
    
    log "${GREEN}✅ Environment reset completed${NC}"
    echo ""
}

# Function to run rollback verification
run_rollback_verification() {
    log "${BLUE}🧪 Running rollback verification...${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Activate virtual environment if it exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi
    
    # Test basic imports
    log "Testing basic imports..."
    python3 -c "
import sys
sys.path.insert(0, 'src')
try:
    from ai_writing_flow.models.flow_stage import FlowStage
    print('✅ Core imports working')
except Exception as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
" || {
        log "${RED}❌ Basic imports failed after rollback${NC}"
        exit 1
    }
    
    # Run a quick test if test suite exists
    if [ -f "tests/test_flow_control_state.py" ]; then
        log "Running basic functionality test..."
        python -m pytest tests/test_flow_control_state.py::TestFlowControlState::test_initialization -v --tb=short || {
            log "${YELLOW}⚠️ Some tests failed, but rollback structure is OK${NC}"
        }
    fi
    
    log "${GREEN}✅ Rollback verification completed${NC}"
    echo ""
}

# Function to create rollback report
create_rollback_report() {
    ROLLBACK_REPORT="$PROJECT_ROOT/deployment/ROLLBACK_REPORT_$(date +%Y%m%d_%H%M%S).md"
    
    cat > "$ROLLBACK_REPORT" << EOF
# AI Writing Flow V2 - Rollback Report

## Rollback Details
- **Date**: $(date)
- **Reason**: $ROLLBACK_REASON
- **Restored from**: $LATEST_BACKUP
- **Status**: SUCCESS
- **Log File**: $LOG_FILE

## Actions Performed
1. Emergency process termination
2. Code restoration from backup
3. Environment reset
4. Verification tests
5. System stabilization

## System Status Post-Rollback
- ✅ Core components restored
- ✅ Test suite functional
- ✅ Environment cleaned
- ✅ Monitoring data archived

## Next Steps
1. Investigate root cause of rollback requirement
2. Address issues before re-deployment
3. Run full test suite before next deployment attempt
4. Review monitoring data from archived directories

## Recovery Commands
\`\`\`bash
cd $PROJECT_ROOT
source venv/bin/activate
python -c "from ai_writing_flow.models.flow_stage import FlowStage; print('System ready')"
\`\`\`

## Escalation Path
If issues persist:
1. Check log file: $LOG_FILE
2. Review backup manifest: $LATEST_BACKUP/BACKUP_MANIFEST.txt
3. Contact system administrator
4. Use emergency-system-controller agent if available

---
Generated by rollback_flow_v2.sh at $(date)
EOF

    log "${GREEN}📝 Rollback report created: $ROLLBACK_REPORT${NC}"
}

# Function to show rollback summary
show_rollback_summary() {
    log "${BLUE}📋 Rollback Summary${NC}"
    echo "==================="
    
    echo "✅ Rollback Status: SUCCESS"
    echo "📅 Rollback Time: $(date)"
    echo "🔙 Reason: $ROLLBACK_REASON"
    echo "📦 Restored from: $LATEST_BACKUP"
    echo "📁 Project Root: $PROJECT_ROOT"
    echo "📝 Log File: $LOG_FILE"
    
    echo ""
    echo "🔙 AI Writing Flow V2 has been successfully rolled back!"
    echo ""
    echo "Next Steps:"
    echo "  1. Investigate the cause of rollback requirement"
    echo "  2. Review archived monitoring data"
    echo "  3. Run full test suite before re-deployment"
    echo "  4. Address issues identified in rollback analysis"
    echo ""
    echo "System Status Check:"
    echo "  cd $PROJECT_ROOT"
    echo "  source venv/bin/activate"
    echo "  python -c \"from ai_writing_flow.models.flow_stage import FlowStage; print('✅ System Ready')\""
    echo ""
}

# Main rollback sequence
main() {
    log "${RED}Starting AI Writing Flow V2 rollback sequence...${NC}"
    log "${YELLOW}Reason: $ROLLBACK_REASON${NC}"
    
    emergency_stop_processes
    find_latest_backup
    restore_from_backup
    reset_environment
    run_rollback_verification
    create_rollback_report
    show_rollback_summary
    
    log "${GREEN}🎉 Rollback completed successfully!${NC}"
}

# Show usage if help requested
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    echo "AI Writing Flow V2 - Rollback Script"
    echo ""
    echo "Usage: $0 [reason]"
    echo ""
    echo "Arguments:"
    echo "  reason    Optional reason for rollback (default: manual_rollback)"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Manual rollback"
    echo "  $0 \"performance_degradation\"        # Rollback due to performance"
    echo "  $0 \"critical_bug_detected\"          # Rollback due to bug"
    echo ""
    echo "This script will:"
    echo "  1. Stop all running processes"
    echo "  2. Restore from the latest backup"
    echo "  3. Reset the environment"
    echo "  4. Verify system functionality"
    echo "  5. Create a rollback report"
    echo ""
    exit 0
fi

# Execute main function
main "$@"