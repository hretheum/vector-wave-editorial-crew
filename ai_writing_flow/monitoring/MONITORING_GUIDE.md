# AI Writing Flow V2 - Production Monitoring Guide

## Overview
This guide covers the comprehensive monitoring infrastructure for AI Writing Flow V2 in local production deployment.

## Components

### 1. Real-time Metrics Collection
- **FlowMetrics**: Real-time KPI tracking
- **MetricsStorage**: SQLite-based metrics persistence
- **Dashboard API**: HTTP API for metrics access

### 2. Alerting System
- **AlertManager**: Multi-channel alert processing
- **Alert Rules**: Configurable thresholds and conditions
- **Notification Channels**: Console, file, webhook support

### 3. Quality Gates
- **QualityGate**: Pre/post-execution validation
- **Validation Rules**: 5 comprehensive quality checks
- **Reporting**: Detailed validation reports

### 4. Monitoring Dashboard
- **Web Interface**: Real-time metrics visualization
- **System Health**: CPU, memory, execution metrics
- **Alert Visualization**: Recent alerts and status

## Quick Start

### Start Monitoring
```bash
# Run health check
python monitoring/health_check.py

# Collect metrics
python monitoring/collect_metrics.py

# Start dashboard
python monitoring/start_dashboard.py
```

### View Metrics
- Dashboard: http://localhost:8080/production_dashboard.html
- Logs: `monitoring/logs/`
- Database: `metrics_data/flow_metrics.db`

## Configuration Files

### Main Configuration
- `monitoring/config/production_monitoring.json` - Main settings
- `monitoring/config/alert_channels.json` - Alert configuration
- `monitoring/config/quality_gates.json` - Quality gate rules

### Thresholds
- CPU Usage: 80% (High alert)
- Memory Usage: 400MB (Medium alert)
- Error Rate: 10% (Critical alert)
- Execution Time: 300s (timeout)

## Monitoring Commands

### Health Checks
```bash
# System health
python monitoring/health_check.py

# Full validation
python deployment/validate_deployment.py
```

### Metrics Management
```bash
# Collect current metrics
python monitoring/collect_metrics.py

# View database
sqlite3 metrics_data/flow_metrics.db "SELECT * FROM flow_metrics LIMIT 10;"
```

### Dashboard
```bash
# Start monitoring dashboard
python monitoring/start_dashboard.py

# Custom port
python monitoring/start_dashboard.py 9090
```

## Alert Channels

### Console Alerts
- Real-time colored output
- Minimum severity: MEDIUM
- Format: Structured text

### File Alerts
- Path: `monitoring/logs/alerts.log`
- Format: JSON with rotation
- Minimum severity: LOW

### Webhook Alerts (Optional)
- URL: Configurable
- Minimum severity: HIGH
- Retry logic: 3 attempts

## Quality Gates

### Pre-execution Checks
1. System resources validation
2. Input validation
3. Component health check
4. Storage availability
5. Network connectivity

### Post-execution Checks
1. Output validation
2. Performance metrics
3. Error rate analysis
4. State consistency
5. Resource cleanup

## Troubleshooting

### Common Issues

**Database not found**
```bash
# Reinitialize storage
python init_monitoring_storage.py
```

**High memory usage**
```bash
# Check processes
python monitoring/health_check.py
```

**Dashboard not loading**
```bash
# Check port availability
netstat -ln | grep 8080
```

### Log Locations
- System logs: `monitoring/logs/`
- Deployment logs: `deployment/`
- Application logs: `src/ai_writing_flow/`

## Performance Tuning

### Metrics Collection
- Interval: 5 seconds (configurable)
- History size: 1000 entries
- Cleanup: Every hour

### Storage Optimization
- Database: SQLite with indexes
- Retention: 30 days default
- Compression: Enabled for archives

### Dashboard Refresh
- Default: 10 seconds
- Configurable via settings
- Auto-refresh on errors

## Integration with AI Writing Flow V2

### Automatic Monitoring
```python
from ai_writing_flow.ai_writing_flow_v2 import AIWritingFlowV2

# Full monitoring enabled
flow = AIWritingFlowV2(
    monitoring_enabled=True,
    alerting_enabled=True,
    quality_gates_enabled=True
)

# Execute with monitoring
result = flow.kickoff(inputs)
```

### Custom Metrics
```python
# Access metrics directly
metrics = flow.flow_metrics
current_kpis = metrics.get_current_kpis()
```

### Alert Handling
```python
# Add custom alert channel
from ai_writing_flow.monitoring.alerting import ConsoleNotificationChannel
channel = ConsoleNotificationChannel()
flow.add_notification_channel(channel)
```

## Maintenance

### Daily Tasks
- Review alert logs
- Check system health
- Validate metrics collection

### Weekly Tasks
- Archive old metrics
- Review alert thresholds
- Performance analysis

### Monthly Tasks
- Database maintenance
- Configuration review
- Threshold optimization

---

For support and advanced configuration, see the technical documentation in the codebase.
