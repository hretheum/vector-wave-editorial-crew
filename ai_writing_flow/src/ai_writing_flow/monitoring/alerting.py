"""
Alerting System - Threshold-based alerting with multiple notification channels

This module provides a comprehensive alerting system that monitors metrics
and sends notifications when thresholds are exceeded.

Key Features:
- Multiple notification channels (email, webhook, console)
- Configurable alert rules and thresholds
- Alert aggregation and rate limiting
- Alert history and resolution tracking
- Integration with FlowMetrics via observer pattern
"""

import asyncio
import json
import logging
import smtplib
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
from urllib.request import urlopen, Request
from urllib.error import URLError

from .flow_metrics import KPIType, MetricsObserver


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status states"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    ESCALATED = "escalated"


@dataclass
class AlertRule:
    """Definition of an alert rule"""
    id: str
    name: str
    kpi_type: KPIType
    threshold: float
    comparison: str  # "greater_than", "less_than", "equals"
    severity: AlertSeverity
    description: str
    enabled: bool = True
    cooldown_minutes: int = 15  # Minimum time between similar alerts
    escalation_threshold: int = 3  # Number of occurrences before escalation
    auto_resolve: bool = True  # Auto-resolve when condition clears
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """Individual alert instance"""
    id: str
    rule_id: str
    kpi_type: KPIType
    severity: AlertSeverity
    status: AlertStatus
    message: str
    value: float
    threshold: float
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    escalation_count: int = 0
    notification_count: int = 0


class NotificationChannel(ABC):
    """Abstract base class for notification channels"""
    
    @abstractmethod
    async def send_notification(self, alert: Alert, context: Dict[str, Any]) -> bool:
        """Send notification for alert"""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test if notification channel is working"""
        pass


class ConsoleNotificationChannel(NotificationChannel):
    """Console/logging notification channel"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    async def send_notification(self, alert: Alert, context: Dict[str, Any]) -> bool:
        """Send console notification"""
        try:
            log_level = {
                AlertSeverity.LOW: logging.INFO,
                AlertSeverity.MEDIUM: logging.WARNING,
                AlertSeverity.HIGH: logging.ERROR,
                AlertSeverity.CRITICAL: logging.CRITICAL
            }.get(alert.severity, logging.WARNING)
            
            message = (
                f"ALERT [{alert.severity.value.upper()}] {alert.message} "
                f"(Value: {alert.value}, Threshold: {alert.threshold})"
            )
            
            self.logger.log(log_level, message)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send console notification: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test console notification"""
        try:
            self.logger.info("Console notification channel test - OK")
            return True
        except Exception:
            return False


class WebhookNotificationChannel(NotificationChannel):
    """Webhook notification channel (Slack, Discord, etc.)"""
    
    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None,
                 timeout: int = 10):
        self.webhook_url = webhook_url
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout
    
    async def send_notification(self, alert: Alert, context: Dict[str, Any]) -> bool:
        """Send webhook notification"""
        try:
            payload = self._build_webhook_payload(alert, context)
            
            request = Request(
                self.webhook_url,
                data=json.dumps(payload).encode('utf-8'),
                headers=self.headers
            )
            
            with urlopen(request, timeout=self.timeout) as response:
                return response.status == 200
                
        except URLError as e:
            logging.error(f"Webhook notification failed: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error in webhook notification: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test webhook connectivity"""
        try:
            test_payload = {
                "text": "Test notification from AI Writing Flow monitoring system",
                "username": "FlowMetrics",
                "icon_emoji": ":robot_face:"
            }
            
            request = Request(
                self.webhook_url,
                data=json.dumps(test_payload).encode('utf-8'),
                headers=self.headers
            )
            
            with urlopen(request, timeout=self.timeout) as response:
                return response.status == 200
                
        except Exception:
            return False
    
    def _build_webhook_payload(self, alert: Alert, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build webhook payload (Slack format by default)"""
        color_map = {
            AlertSeverity.LOW: "#36a64f",      # Green
            AlertSeverity.MEDIUM: "#ff9900",   # Orange  
            AlertSeverity.HIGH: "#ff4444",     # Red
            AlertSeverity.CRITICAL: "#8b0000"  # Dark red
        }
        
        return {
            "username": "FlowMetrics Alerting",
            "icon_emoji": ":warning:",
            "attachments": [{
                "color": color_map.get(alert.severity, "#ff9900"),
                "title": f"{alert.severity.value.upper()} Alert: {alert.kpi_type.value}",
                "text": alert.message,
                "fields": [
                    {
                        "title": "Current Value",
                        "value": str(alert.value),
                        "short": True
                    },
                    {
                        "title": "Threshold",
                        "value": str(alert.threshold),
                        "short": True
                    },
                    {
                        "title": "Severity",
                        "value": alert.severity.value.title(),
                        "short": True
                    },
                    {
                        "title": "Status",
                        "value": alert.status.value.title(),
                        "short": True
                    }
                ],
                "footer": "AI Writing Flow Monitoring",
                "ts": int(alert.created_at.timestamp())
            }]
        }


class EmailNotificationChannel(NotificationChannel):
    """Email notification channel"""
    
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str,
                 from_email: str, to_emails: List[str], use_tls: bool = True):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
        self.use_tls = use_tls
    
    async def send_notification(self, alert: Alert, context: Dict[str, Any]) -> bool:
        """Send email notification"""
        try:
            # Build email message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = f"[{alert.severity.value.upper()}] FlowMetrics Alert: {alert.kpi_type.value}"
            
            # Email body
            body = self._build_email_body(alert, context)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                text = msg.as_string()
                server.sendmail(self.from_email, self.to_emails, text)
            
            return True
            
        except Exception as e:
            logging.error(f"Email notification failed: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test email connection"""
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
            return True
        except Exception:
            return False
    
    def _build_email_body(self, alert: Alert, context: Dict[str, Any]) -> str:
        """Build HTML email body"""
        severity_color = {
            AlertSeverity.LOW: "#28a745",
            AlertSeverity.MEDIUM: "#ffc107", 
            AlertSeverity.HIGH: "#dc3545",
            AlertSeverity.CRITICAL: "#6f42c1"
        }.get(alert.severity, "#ffc107")
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
            <div style="border-left: 4px solid {severity_color}; padding-left: 20px;">
                <h2 style="color: {severity_color}; margin-top: 0;">
                    {alert.severity.value.upper()} Alert: {alert.kpi_type.value.replace('_', ' ').title()}
                </h2>
                
                <p><strong>Message:</strong> {alert.message}</p>
                
                <table style="border-collapse: collapse; width: 100%; max-width: 500px;">
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px; background-color: #f9f9f9;"><strong>Current Value</strong></td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{alert.value}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px; background-color: #f9f9f9;"><strong>Threshold</strong></td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{alert.threshold}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px; background-color: #f9f9f9;"><strong>Created At</strong></td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px; background-color: #f9f9f9;"><strong>Status</strong></td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{alert.status.value.title()}</td>
                    </tr>
                </table>
                
                <p style="margin-top: 20px; font-size: 12px; color: #666;">
                    This alert was generated by the AI Writing Flow monitoring system.
                </p>
            </div>
        </body>
        </html>
        """


class AlertManager:
    """
    Alert manager that monitors metrics and sends notifications
    
    Implements the observer pattern to receive metric updates and evaluate
    alert rules, managing the complete alert lifecycle.
    """
    
    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self._notification_channels: List[NotificationChannel] = []
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Rate limiting and cooldown tracking
        self._last_alert_times: Dict[str, float] = {}
        self._alert_counts: Dict[str, int] = {}
        
        # Statistics
        self._stats = {
            "total_alerts_created": 0,
            "total_alerts_resolved": 0,
            "total_notifications_sent": 0,
            "notification_failures": 0
        }
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule"""
        with self._lock:
            self._rules[rule.id] = rule
            logging.info(f"Added alert rule: {rule.name} ({rule.id})")
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule"""
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]
                logging.info(f"Removed alert rule: {rule_id}")
                return True
            return False
    
    def add_notification_channel(self, channel: NotificationChannel) -> None:
        """Add a notification channel"""
        self._notification_channels.append(channel)
        logging.info(f"Added notification channel: {type(channel).__name__}")
    
    def remove_notification_channel(self, channel: NotificationChannel) -> bool:
        """Remove a notification channel"""
        if channel in self._notification_channels:
            self._notification_channels.remove(channel)
            return True
        return False
    
    def on_threshold_exceeded(self, kpi_type: KPIType, value: float, 
                            threshold: float, metadata: Dict[str, Any]) -> None:
        """
        Called when a metric threshold is exceeded (MetricsObserver implementation)
        """
        with self._lock:
            # Find applicable rules
            applicable_rules = [
                rule for rule in self._rules.values()
                if (rule.kpi_type == kpi_type and 
                    rule.enabled and
                    self._evaluate_rule_condition(rule, value))
            ]
            
            for rule in applicable_rules:
                self._process_rule_trigger(rule, value, threshold, metadata)
    
    def _evaluate_rule_condition(self, rule: AlertRule, value: float) -> bool:
        """Evaluate if rule condition is met"""
        if rule.comparison == "greater_than":
            return value > rule.threshold
        elif rule.comparison == "less_than":
            return value < rule.threshold
        elif rule.comparison == "equals":
            return abs(value - rule.threshold) < 0.001  # Float comparison
        else:
            logging.warning(f"Unknown comparison operator: {rule.comparison}")
            return False
    
    def _process_rule_trigger(self, rule: AlertRule, value: float, 
                            original_threshold: float, metadata: Dict[str, Any]) -> None:
        """Process a triggered rule"""
        current_time = time.time()
        
        # Check cooldown (do not early return; allow escalation during cooldown)
        last_alert_key = f"{rule.id}_{rule.kpi_type.value}"
        last_alert_time = self._last_alert_times.get(last_alert_key, 0)
        in_cooldown = (current_time - last_alert_time) < (rule.cooldown_minutes * 60)
        
        # Create or update alert (single active alert per rule)
        alert_id = rule.id
        
        # Fast path: lookup by stable alert_id
        existing_alert = self._active_alerts.get(alert_id)
        if existing_alert and existing_alert.status != AlertStatus.ACTIVE:
            # Treat non-active alerts as non-existing for update path
            existing_alert = None
        
        if existing_alert:
            # Update existing alert
            if not in_cooldown:
                # Only update value/timestamp when not in cooldown
                existing_alert.value = value
                existing_alert.updated_at = datetime.now(timezone.utc)
            # Increment escalation count on every repeated trigger (even during cooldown)
            existing_alert.escalation_count += 1
            
            # Check for escalation
            if existing_alert.escalation_count >= rule.escalation_threshold:
                existing_alert.status = AlertStatus.ESCALATED
                existing_alert.severity = AlertSeverity.CRITICAL
            
            alert = existing_alert
        else:
            # Create new alert
            alert = Alert(
                id=alert_id,
                rule_id=rule.id,
                kpi_type=rule.kpi_type,
                severity=rule.severity,
                status=AlertStatus.ACTIVE,
                message=self._build_alert_message(rule, value),
                value=value,
                threshold=rule.threshold,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                metadata=metadata
            )
            
            self._active_alerts[alert_id] = alert
            self._alert_history.append(alert)
            self._stats["total_alerts_created"] += 1
        
        # Update counters
        self._alert_counts[last_alert_key] = self._alert_counts.get(last_alert_key, 0) + 1
        
        # Only update cooldown timestamp and send notifications when not in cooldown
        if not in_cooldown:
            self._last_alert_times[last_alert_key] = current_time
            # Send notifications (handle sync/async contexts)
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._send_notifications(alert))
            except RuntimeError:
                # No running event loop (e.g., sync test) - run synchronously
                try:
                    asyncio.run(self._send_notifications(alert))
                except RuntimeError:
                    # If already inside an event loop but get_running_loop failed for other reasons
                    # fallback: schedule via thread
                    threading.Thread(target=lambda: asyncio.run(self._send_notifications(alert)), daemon=True).start()
    
    def _build_alert_message(self, rule: AlertRule, value: float) -> str:
        """Build alert message"""
        comparison_text = {
            "greater_than": "exceeded",
            "less_than": "below",
            "equals": "equals"
        }.get(rule.comparison, "triggered")
        
        return f"{rule.name}: {rule.kpi_type.value.replace('_', ' ').title()} {comparison_text} threshold ({value} vs {rule.threshold})"
    
    async def _send_notifications(self, alert: Alert) -> None:
        """Send notifications for alert"""
        if not self._notification_channels:
            logging.warning("No notification channels configured")
            return
        
        context = {
            "system_name": "AI Writing Flow",
            "environment": "production",  # Could be configurable
            "dashboard_url": "http://localhost:8080/dashboard"  # Could be configurable
        }
        
        success_count = 0
        
        for channel in self._notification_channels:
            try:
                success = await channel.send_notification(alert, context)
                if success:
                    success_count += 1
                    self._stats["total_notifications_sent"] += 1
                else:
                    self._stats["notification_failures"] += 1
            except Exception as e:
                logging.error(f"Notification channel error: {e}")
                self._stats["notification_failures"] += 1
        
        # Update alert notification count
        alert.notification_count += success_count
        
        logging.info(f"Sent {success_count}/{len(self._notification_channels)} notifications for alert {alert.id}")
    
    def resolve_alert(self, alert_id: str, resolution_message: str = "") -> bool:
        """Manually resolve an alert"""
        with self._lock:
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now(timezone.utc)
                alert.updated_at = datetime.now(timezone.utc)
                
                if resolution_message:
                    alert.metadata["resolution_message"] = resolution_message
                
                # Move to history
                del self._active_alerts[alert_id]
                self._stats["total_alerts_resolved"] += 1
                
                logging.info(f"Manually resolved alert: {alert_id}")
                return True
        
        return False
    
    def auto_resolve_alerts(self, kpi_type: KPIType, current_value: float) -> int:
        """Auto-resolve alerts when conditions clear"""
        resolved_count = 0
        
        with self._lock:
            alerts_to_resolve = []
            
            for alert in self._active_alerts.values():
                if (alert.kpi_type == kpi_type and 
                    alert.status == AlertStatus.ACTIVE):
                    
                    # Get the rule to check auto-resolve condition
                    rule = self._rules.get(alert.rule_id)
                    if rule and rule.auto_resolve:
                        # Check if condition has cleared
                        if not self._evaluate_rule_condition(rule, current_value):
                            alerts_to_resolve.append(alert.id)
            
            # Resolve alerts
            for alert_id in alerts_to_resolve:
                if self.resolve_alert(alert_id, "Auto-resolved: condition cleared"):
                    resolved_count += 1
        
        return resolved_count
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get active alerts, optionally filtered by severity"""
        with self._lock:
            alerts = list(self._active_alerts.values())
            
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
            
            # Sort by severity and creation time
            severity_order = {
                AlertSeverity.CRITICAL: 0,
                AlertSeverity.HIGH: 1,
                AlertSeverity.MEDIUM: 2,
                AlertSeverity.LOW: 3
            }
            
            alerts.sort(key=lambda a: (severity_order.get(a.severity, 4), a.created_at))
            return alerts
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history"""
        with self._lock:
            return self._alert_history[-limit:] if limit > 0 else self._alert_history.copy()
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert system statistics"""
        with self._lock:
            active_by_severity = {}
            for severity in AlertSeverity:
                active_by_severity[severity.value] = len([
                    a for a in self._active_alerts.values() 
                    if a.severity == severity
                ])
            
            return {
                "active_alerts": len(self._active_alerts),
                "active_by_severity": active_by_severity,
                "total_rules": len(self._rules),
                "enabled_rules": len([r for r in self._rules.values() if r.enabled]),
                "notification_channels": len(self._notification_channels),
                "stats": self._stats.copy(),
                "uptime": time.time() - getattr(self, '_start_time', time.time())
            }
    
    def test_notification_channels(self) -> Dict[str, bool]:
        """Test all notification channels"""
        results = {}
        
        for i, channel in enumerate(self._notification_channels):
            channel_name = f"{type(channel).__name__}_{i}"
            try:
                results[channel_name] = channel.test_connection()
            except Exception as e:
                logging.error(f"Error testing {channel_name}: {e}")
                results[channel_name] = False
        
        return results
    
    def suppress_alert(self, alert_id: str, duration_minutes: int = 60) -> bool:
        """Suppress an alert for a specific duration"""
        with self._lock:
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]
                alert.status = AlertStatus.SUPPRESSED
                alert.updated_at = datetime.now(timezone.utc)
                alert.metadata["suppressed_until"] = (
                    datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
                ).isoformat()
                
                logging.info(f"Suppressed alert {alert_id} for {duration_minutes} minutes")
                return True
        
        return False
    
    def cleanup_old_alerts(self, max_history_size: int = 1000, max_age_days: int = 30) -> int:
        """Clean up old alerts from history"""
        with self._lock:
            original_count = len(self._alert_history)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            
            # Remove old alerts
            self._alert_history = [
                alert for alert in self._alert_history
                if alert.created_at > cutoff_date
            ]
            
            # Limit history size
            if len(self._alert_history) > max_history_size:
                self._alert_history = self._alert_history[-max_history_size:]
            
            cleaned_count = original_count - len(self._alert_history)
            
            if cleaned_count > 0:
                logging.info(f"Cleaned up {cleaned_count} old alerts from history")
            
            return cleaned_count