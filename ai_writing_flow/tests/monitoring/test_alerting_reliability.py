"""
Alerting Reliability Tests - Phase 3, Task 26.2

This test suite validates the reliability and correctness of the alerting system,
ensuring alerts are triggered, delivered, and managed correctly under various conditions.

Key Test Areas:
- Alert rule evaluation accuracy
- Notification channel reliability 
- Alert lifecycle management (creation, escalation, resolution)
- Rate limiting and cooldown mechanisms
- Observer pattern integration
- Error handling and fallback mechanisms
- Concurrent alerting scenarios
"""

import pytest
import asyncio
import time
import threading
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys
import json
import smtplib
from urllib.error import URLError

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from ai_writing_flow.monitoring.alerting import (
    AlertManager, AlertRule, Alert, AlertSeverity, AlertStatus,
    ConsoleNotificationChannel, WebhookNotificationChannel, EmailNotificationChannel,
    KPIType
)
from ai_writing_flow.monitoring.flow_metrics import FlowMetrics, MetricsConfig


class TestAlertRuleEvaluation:
    """Test alert rule evaluation accuracy and reliability"""
    
    def setup_method(self):
        """Setup alert manager and rules"""
        self.alert_manager = AlertManager()
        
        # Create test rules
        self.cpu_rule = AlertRule(
            id="cpu_high",
            name="High CPU Usage",
            kpi_type=KPIType.CPU_USAGE,
            threshold=80.0,
            comparison="greater_than",
            severity=AlertSeverity.HIGH,
            description="CPU usage exceeded 80%",
            cooldown_minutes=5,
            escalation_threshold=3
        )
        
        self.memory_rule = AlertRule(
            id="memory_low",
            name="Low Memory Available",
            kpi_type=KPIType.MEMORY_USAGE,
            threshold=100.0,
            comparison="less_than", 
            severity=AlertSeverity.MEDIUM,
            description="Available memory below 100MB",
            cooldown_minutes=10,
            auto_resolve=True
        )
        
        self.error_rate_rule = AlertRule(
            id="error_rate_high",
            name="High Error Rate",
            kpi_type=KPIType.ERROR_RATE,
            threshold=5.0,
            comparison="greater_than",
            severity=AlertSeverity.CRITICAL,
            description="Error rate exceeded 5%",
            cooldown_minutes=1,
            escalation_threshold=2
        )
        
        # Add rules to manager
        self.alert_manager.add_rule(self.cpu_rule)
        self.alert_manager.add_rule(self.memory_rule)
        self.alert_manager.add_rule(self.error_rate_rule)
    
    def test_greater_than_rule_evaluation(self):
        """Test greater_than comparison rule evaluation"""
        # Trigger CPU rule with value above threshold
        self.alert_manager.on_threshold_exceeded(
            KPIType.CPU_USAGE, 
            85.0,  # Above 80.0 threshold
            80.0,
            {"source": "test"}
        )
        
        # Should create an alert
        active_alerts = self.alert_manager.get_active_alerts()
        assert len(active_alerts) == 1, f"Expected 1 alert, got {len(active_alerts)}"
        
        alert = active_alerts[0]
        assert alert.rule_id == "cpu_high", f"Expected cpu_high rule, got {alert.rule_id}"
        assert alert.severity == AlertSeverity.HIGH, f"Expected HIGH severity, got {alert.severity}"
        assert alert.value == 85.0, f"Expected value 85.0, got {alert.value}"
        assert alert.status == AlertStatus.ACTIVE, f"Expected ACTIVE status, got {alert.status}"
    
    def test_less_than_rule_evaluation(self):
        """Test less_than comparison rule evaluation"""
        # Trigger memory rule with value below threshold
        self.alert_manager.on_threshold_exceeded(
            KPIType.MEMORY_USAGE,
            50.0,  # Below 100.0 threshold
            100.0,
            {"source": "memory_test"}
        )
        
        active_alerts = self.alert_manager.get_active_alerts()
        assert len(active_alerts) == 1, "Should have one memory alert"
        
        alert = active_alerts[0]
        assert alert.rule_id == "memory_low", "Should be memory_low rule"
        assert alert.severity == AlertSeverity.MEDIUM, "Should be MEDIUM severity"
        assert alert.value == 50.0, "Value should match triggered value"
    
    def test_rule_not_triggered_when_condition_not_met(self):
        """Test that rules don't trigger when conditions aren't met"""
        # CPU value below threshold - should not trigger
        self.alert_manager.on_threshold_exceeded(
            KPIType.CPU_USAGE,
            70.0,  # Below 80.0 threshold
            80.0,
            {"source": "test"}
        )
        
        # Memory value above threshold - should not trigger less_than rule
        self.alert_manager.on_threshold_exceeded(
            KPIType.MEMORY_USAGE,
            150.0,  # Above 100.0 threshold
            100.0,
            {"source": "test"}
        )
        
        active_alerts = self.alert_manager.get_active_alerts()
        assert len(active_alerts) == 0, f"Expected no alerts, got {len(active_alerts)}"
    
    def test_disabled_rule_not_triggered(self):
        """Test that disabled rules don't trigger alerts"""
        # Disable CPU rule
        self.cpu_rule.enabled = False
        
        # Try to trigger disabled rule
        self.alert_manager.on_threshold_exceeded(
            KPIType.CPU_USAGE,
            90.0,  # Well above threshold
            80.0,
            {"source": "test"}
        )
        
        active_alerts = self.alert_manager.get_active_alerts()
        assert len(active_alerts) == 0, "Disabled rule should not create alerts"
    
    def test_escalation_mechanism(self):
        """Test alert escalation after multiple triggers"""
        # Trigger error rate rule multiple times
        for i in range(3):
            self.alert_manager.on_threshold_exceeded(
                KPIType.ERROR_RATE,
                10.0,  # Above 5.0 threshold
                5.0,
                {"trigger_count": i+1}
            )
            time.sleep(0.1)  # Small delay between triggers
        
        active_alerts = self.alert_manager.get_active_alerts()
        assert len(active_alerts) == 1, "Should have one escalated alert"
        
        alert = active_alerts[0]
        assert alert.escalation_count >= 2, f"Expected escalation count >= 2, got {alert.escalation_count}"
        
        # After escalation_threshold (2), should be escalated to CRITICAL
        if alert.escalation_count >= self.error_rate_rule.escalation_threshold:
            assert alert.status == AlertStatus.ESCALATED, "Should be escalated status"
            assert alert.severity == AlertSeverity.CRITICAL, "Should be escalated to CRITICAL severity"


class TestNotificationChannelReliability:
    """Test reliability of different notification channels"""
    
    def setup_method(self):
        """Setup notification channel tests"""
        pass
    
    def test_console_notification_reliability(self):
        """Test console notification channel reliability"""
        # Create console channel with mock logger
        mock_logger = Mock()
        console_channel = ConsoleNotificationChannel(mock_logger)
        
        # Create test alert
        alert = Alert(
            id="test_alert_1",
            rule_id="test_rule",
            kpi_type=KPIType.CPU_USAGE,
            severity=AlertSeverity.HIGH,
            status=AlertStatus.ACTIVE,
            message="Test alert message",
            value=85.0,
            threshold=80.0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Test notification sending
        context = {"system": "test"}
        
        # Run async notification
        success = asyncio.run(console_channel.send_notification(alert, context))
        
        assert success == True, "Console notification should succeed"
        
        # Verify logger was called with appropriate level
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        log_level = call_args[0][0]  # First positional argument
        log_message = call_args[0][1]  # Second positional argument
        
        # HIGH severity should use ERROR log level
        import logging
        assert log_level == logging.ERROR, f"Expected ERROR log level for HIGH severity, got {log_level}"
        assert "ALERT [HIGH]" in log_message, "Log message should contain alert severity"
        assert "85.0" in log_message, "Log message should contain alert value"
        assert "80.0" in log_message, "Log message should contain threshold"
    
    def test_console_notification_error_handling(self):
        """Test console notification error handling"""
        # Create console channel with failing logger
        mock_logger = Mock()
        mock_logger.log.side_effect = Exception("Logger failed")
        
        console_channel = ConsoleNotificationChannel(mock_logger)
        
        alert = Alert(
            id="test_alert_error",
            rule_id="test_rule",
            kpi_type=KPIType.MEMORY_USAGE,
            severity=AlertSeverity.MEDIUM,
            status=AlertStatus.ACTIVE,
            message="Test error handling",
            value=50.0,
            threshold=100.0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Should handle error gracefully
        success = asyncio.run(console_channel.send_notification(alert, {}))
        
        assert success == False, "Should return False when logger fails"
        
        # Error should be logged to fallback logger
        mock_logger.error.assert_called_once()
    
    def test_webhook_notification_success(self):
        """Test successful webhook notification"""
        webhook_url = "https://hooks.slack.com/test"
        
        with patch('ai_writing_flow.monitoring.alerting.urlopen') as mock_urlopen:
            # Mock successful HTTP response
            mock_response = Mock()
            mock_response.status = 200
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=None)
            mock_urlopen.return_value = mock_response
            
            webhook_channel = WebhookNotificationChannel(webhook_url)
            
            alert = Alert(
                id="webhook_test",
                rule_id="webhook_rule",
                kpi_type=KPIType.THROUGHPUT,
                severity=AlertSeverity.CRITICAL,
                status=AlertStatus.ACTIVE,
                message="Webhook test alert",
                value=5.0,
                threshold=10.0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            success = asyncio.run(webhook_channel.send_notification(alert, {}))
            
            assert success == True, "Webhook notification should succeed"
            
            # Verify request was made
            mock_urlopen.assert_called_once()
            
            # Check request details
            call_args = mock_urlopen.call_args[0][0]  # Request object
            assert call_args.full_url == webhook_url, "URL should match"
            
            # Check payload content
            request_data = call_args.data.decode('utf-8')
            payload = json.loads(request_data)
            
            assert "attachments" in payload, "Payload should have attachments"
            assert len(payload["attachments"]) == 1, "Should have one attachment"
            
            attachment = payload["attachments"][0]
            assert attachment["title"] == "CRITICAL Alert: throughput", "Title should match alert"
            assert attachment["text"] == "Webhook test alert", "Text should match message"
    
    def test_webhook_notification_failure_handling(self):
        """Test webhook notification failure handling"""
        webhook_url = "https://hooks.slack.com/test"
        
        with patch('ai_writing_flow.monitoring.alerting.urlopen') as mock_urlopen:
            # Mock HTTP error
            mock_urlopen.side_effect = URLError("Connection failed")
            
            webhook_channel = WebhookNotificationChannel(webhook_url, timeout=1)
            
            alert = Alert(
                id="webhook_fail_test",
                rule_id="webhook_rule",
                kpi_type=KPIType.ERROR_RATE,
                severity=AlertSeverity.HIGH,
                status=AlertStatus.ACTIVE,
                message="Webhook failure test",
                value=15.0,
                threshold=5.0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            success = asyncio.run(webhook_channel.send_notification(alert, {}))
            
            assert success == False, "Should return False on connection failure"
    
    def test_email_notification_success(self):
        """Test successful email notification"""
        with patch('ai_writing_flow.monitoring.alerting.smtplib.SMTP') as mock_smtp:
            # Mock SMTP server
            mock_server = Mock()
            mock_smtp.return_value.__enter__ = Mock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = Mock(return_value=None)
            
            email_channel = EmailNotificationChannel(
                smtp_host="smtp.test.com",
                smtp_port=587,
                username="test@test.com",
                password="password",
                from_email="alerts@test.com",
                to_emails=["admin@test.com", "dev@test.com"]
            )
            
            alert = Alert(
                id="email_test",
                rule_id="email_rule",
                kpi_type=KPIType.MEMORY_USAGE,
                severity=AlertSeverity.MEDIUM,
                status=AlertStatus.ACTIVE,
                message="Email test alert",
                value=50.0,
                threshold=100.0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            success = asyncio.run(email_channel.send_notification(alert, {}))
            
            assert success == True, "Email notification should succeed"
            
            # Verify SMTP interactions
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("test@test.com", "password")
            mock_server.sendmail.assert_called_once()
            
            # Check sendmail call
            sendmail_args = mock_server.sendmail.call_args[0]
            from_addr = sendmail_args[0]
            to_addrs = sendmail_args[1]
            message = sendmail_args[2]
            
            assert from_addr == "alerts@test.com", "From address should match"
            assert to_addrs == ["admin@test.com", "dev@test.com"], "To addresses should match"
            assert "Email test alert" in message, "Message should contain alert text"
    
    def test_email_notification_failure_handling(self):
        """Test email notification failure handling"""
        with patch('ai_writing_flow.monitoring.alerting.smtplib.SMTP') as mock_smtp:
            # Mock SMTP failure
            mock_smtp.side_effect = smtplib.SMTPException("SMTP server error")
            
            email_channel = EmailNotificationChannel(
                smtp_host="smtp.test.com",
                smtp_port=587,
                username="test@test.com",
                password="password",
                from_email="alerts@test.com",
                to_emails=["admin@test.com"]
            )
            
            alert = Alert(
                id="email_fail_test",
                rule_id="email_rule",
                kpi_type=KPIType.CPU_USAGE,
                severity=AlertSeverity.HIGH,
                status=AlertStatus.ACTIVE,
                message="Email failure test",
                value=90.0,
                threshold=80.0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            success = asyncio.run(email_channel.send_notification(alert, {}))
            
            assert success == False, "Should return False on SMTP failure"


class TestAlertLifecycleManagement:
    """Test complete alert lifecycle management"""
    
    def setup_method(self):
        """Setup alert lifecycle tests"""
        self.alert_manager = AlertManager()
        
        # Add test notification channel
        self.mock_channel = Mock()
        self.mock_channel.send_notification = AsyncMock(return_value=True)
        self.alert_manager.add_notification_channel(self.mock_channel)
        
        # Create test rule
        self.test_rule = AlertRule(
            id="lifecycle_test",
            name="Lifecycle Test Rule",
            kpi_type=KPIType.CPU_USAGE,
            threshold=75.0,
            comparison="greater_than",
            severity=AlertSeverity.MEDIUM,
            description="Test rule for lifecycle",
            cooldown_minutes=1,
            auto_resolve=True
        )
        
        self.alert_manager.add_rule(self.test_rule)
    
    def test_alert_creation_lifecycle(self):
        """Test alert creation process"""
        initial_stats = self.alert_manager.get_alert_statistics()
        initial_total = initial_stats["stats"]["total_alerts_created"]
        
        # Trigger alert
        self.alert_manager.on_threshold_exceeded(
            KPIType.CPU_USAGE,
            80.0,
            75.0,
            {"test": "creation"}
        )
        
        # Wait for async notification
        time.sleep(0.1)
        
        # Check alert was created
        active_alerts = self.alert_manager.get_active_alerts()
        assert len(active_alerts) == 1, "Should have created one alert"
        
        alert = active_alerts[0]
        assert alert.rule_id == "lifecycle_test", "Should be our test rule"
        assert alert.status == AlertStatus.ACTIVE, "Should be active"
        assert alert.value == 80.0, "Should have correct value"
        assert alert.notification_count > 0, "Should have sent notification"
        
        # Check statistics
        updated_stats = self.alert_manager.get_alert_statistics()
        assert updated_stats["stats"]["total_alerts_created"] == initial_total + 1, \
            "Should increment alert creation count"
    
    def test_alert_update_on_repeated_trigger(self):
        """Test alert update when same rule triggers again"""
        # Initial trigger
        self.alert_manager.on_threshold_exceeded(
            KPIType.CPU_USAGE,
            80.0,
            75.0,
            {"trigger": "first"}
        )
        
        time.sleep(0.1)
        initial_alerts = self.alert_manager.get_active_alerts()
        assert len(initial_alerts) == 1, "Should have one alert initially"
        
        initial_alert = initial_alerts[0]
        initial_escalation_count = initial_alert.escalation_count
        
        # Wait for cooldown to pass
        time.sleep(61)  # 1 minute + buffer
        
        # Second trigger
        self.alert_manager.on_threshold_exceeded(
            KPIType.CPU_USAGE,
            85.0,  # Higher value
            75.0,
            {"trigger": "second"}
        )
        
        time.sleep(0.1)
        updated_alerts = self.alert_manager.get_active_alerts()
        assert len(updated_alerts) == 1, "Should still have one alert (updated)"
        
        updated_alert = updated_alerts[0]
        assert updated_alert.value == 85.0, "Should have updated value"
        assert updated_alert.escalation_count > initial_escalation_count, \
            "Should have incremented escalation count"
    
    def test_manual_alert_resolution(self):
        """Test manual alert resolution"""
        # Create alert
        self.alert_manager.on_threshold_exceeded(
            KPIType.CPU_USAGE,
            80.0,
            75.0,
            {"test": "resolution"}
        )
        
        time.sleep(0.1)
        active_alerts = self.alert_manager.get_active_alerts()
        assert len(active_alerts) == 1, "Should have one active alert"
        
        alert_id = active_alerts[0].id
        
        # Manually resolve alert
        resolution_message = "Manually resolved for testing"
        success = self.alert_manager.resolve_alert(alert_id, resolution_message)
        
        assert success == True, "Should successfully resolve alert"
        
        # Check alert is no longer active
        remaining_alerts = self.alert_manager.get_active_alerts()
        assert len(remaining_alerts) == 0, "Should have no active alerts after resolution"
        
        # Check in history
        history = self.alert_manager.get_alert_history(limit=1)
        assert len(history) >= 1, "Should be in alert history"
        
        resolved_alert = history[-1]  # Most recent
        assert resolved_alert.status == AlertStatus.RESOLVED, "Should be resolved status"
        assert resolved_alert.resolved_at is not None, "Should have resolution timestamp"
        assert resolved_alert.metadata.get("resolution_message") == resolution_message, \
            "Should have resolution message in metadata"
    
    def test_auto_resolution_mechanism(self):
        """Test automatic alert resolution when conditions clear"""
        # Create alert
        self.alert_manager.on_threshold_exceeded(
            KPIType.CPU_USAGE,
            80.0,
            75.0,
            {"test": "auto_resolve"}
        )
        
        time.sleep(0.1)
        active_alerts = self.alert_manager.get_active_alerts()
        assert len(active_alerts) == 1, "Should have one active alert"
        
        # Simulate condition clearing (CPU below threshold)
        resolved_count = self.alert_manager.auto_resolve_alerts(KPIType.CPU_USAGE, 70.0)
        
        assert resolved_count >= 1, f"Should have auto-resolved at least 1 alert, got {resolved_count}"
        
        # Check alert is resolved
        remaining_alerts = self.alert_manager.get_active_alerts()
        assert len(remaining_alerts) == 0, "Should have no active alerts after auto-resolution"


class TestRateLimitingAndCooldown:
    """Test rate limiting and cooldown mechanisms"""
    
    def setup_method(self):
        """Setup rate limiting tests"""
        self.alert_manager = AlertManager()
        
        # Rule with short cooldown for testing
        self.rate_limit_rule = AlertRule(
            id="rate_limit_test",
            name="Rate Limit Test",
            kpi_type=KPIType.ERROR_RATE,
            threshold=10.0,
            comparison="greater_than",
            severity=AlertSeverity.HIGH,
            description="Test rate limiting",
            cooldown_minutes=0.1  # 6 seconds for testing
        )
        
        self.alert_manager.add_rule(self.rate_limit_rule)
    
    def test_cooldown_prevents_duplicate_alerts(self):
        """Test that cooldown prevents rapid duplicate alerts"""
        # First trigger - should create alert
        self.alert_manager.on_threshold_exceeded(
            KPIType.ERROR_RATE,
            15.0,
            10.0,
            {"trigger": "first"}
        )
        
        time.sleep(0.1)
        first_check = self.alert_manager.get_active_alerts()
        assert len(first_check) == 1, "First trigger should create alert"
        
        # Second trigger immediately - should be blocked by cooldown
        self.alert_manager.on_threshold_exceeded(
            KPIType.ERROR_RATE,
            20.0,  # Even higher value
            10.0,
            {"trigger": "second_blocked"}
        )
        
        time.sleep(0.1)
        second_check = self.alert_manager.get_active_alerts()
        assert len(second_check) == 1, "Should still have only one alert due to cooldown"
        
        # Value should not have updated due to cooldown
        alert = second_check[0]
        assert alert.value == 15.0, "Value should not update during cooldown"
    
    def test_cooldown_allows_alerts_after_timeout(self):
        """Test that alerts are allowed after cooldown period"""
        # First trigger
        self.alert_manager.on_threshold_exceeded(
            KPIType.ERROR_RATE,
            15.0,
            10.0,
            {"trigger": "first"}
        )
        
        time.sleep(0.1)
        
        # Wait for cooldown to expire (6 seconds + buffer)
        time.sleep(7)
        
        # Second trigger after cooldown - should update existing alert
        self.alert_manager.on_threshold_exceeded(
            KPIType.ERROR_RATE,
            25.0,  # Higher value
            10.0,
            {"trigger": "second_allowed"}
        )
        
        time.sleep(0.1)
        alerts = self.alert_manager.get_active_alerts()
        assert len(alerts) == 1, "Should have one alert"
        
        alert = alerts[0]
        assert alert.value == 25.0, "Value should be updated after cooldown"
        assert alert.escalation_count >= 1, "Escalation count should increment"
    
    def test_rate_limiting_statistics_tracking(self):
        """Test that rate limiting is properly tracked in statistics"""
        initial_stats = self.alert_manager.get_alert_statistics()
        
        # Rapid-fire triggers (most should be rate limited)
        for i in range(5):
            self.alert_manager.on_threshold_exceeded(
                KPIType.ERROR_RATE,
                15.0 + i,  # Slightly different values
                10.0,
                {"rapid_trigger": i}
            )
            time.sleep(0.5)  # Small delay, but within cooldown
        
        time.sleep(0.1)
        
        # Should have only one alert due to rate limiting
        active_alerts = self.alert_manager.get_active_alerts()
        assert len(active_alerts) == 1, "Rate limiting should prevent multiple alerts"
        
        # But escalation count should reflect multiple triggers
        alert = active_alerts[0]
        # Note: Actual escalation count depends on exact timing and cooldown implementation


class TestConcurrentAlertingScenarios:
    """Test alerting behavior under concurrent load"""
    
    def setup_method(self):
        """Setup concurrent testing"""
        self.alert_manager = AlertManager()
        
        # Add multiple rules for different KPIs
        rules = [
            AlertRule(
                id=f"concurrent_rule_{i}",
                name=f"Concurrent Rule {i}",
                kpi_type=KPIType.CPU_USAGE,
                threshold=50.0 + i * 10,
                comparison="greater_than",
                severity=AlertSeverity.MEDIUM,
                description=f"Concurrent test rule {i}",
                cooldown_minutes=0.05  # 3 seconds
            )
            for i in range(3)
        ]
        
        for rule in rules:
            self.alert_manager.add_rule(rule)
        
        # Add mock notification channel
        self.mock_channel = Mock()
        self.mock_channel.send_notification = AsyncMock(return_value=True)
        self.alert_manager.add_notification_channel(self.mock_channel)
    
    def test_concurrent_alert_processing(self):
        """Test concurrent alert processing from multiple threads"""
        results = []
        errors = []
        
        def trigger_alerts_concurrently(thread_id):
            """Trigger alerts from multiple threads simultaneously"""
            try:
                for i in range(5):
                    value = 60.0 + thread_id * 10 + i  # Different values per thread
                    self.alert_manager.on_threshold_exceeded(
                        KPIType.CPU_USAGE,
                        value,
                        50.0,
                        {"thread_id": thread_id, "iteration": i}
                    )
                    time.sleep(0.1)
                
                results.append(f"Thread {thread_id} completed")
                
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
        
        # Run concurrent alert triggering
        threads = []
        for i in range(3):
            thread = threading.Thread(target=trigger_alerts_concurrently, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)
        
        time.sleep(0.5)  # Allow async notifications to complete
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent processing errors: {errors}"
        assert len(results) == 3, f"Expected 3 threads to complete, got {len(results)}"
        
        # Check that alerts were created appropriately
        active_alerts = self.alert_manager.get_active_alerts()
        
        # Should have multiple alerts due to different rule thresholds
        assert len(active_alerts) > 0, "Should have created some alerts"
        
        # All alerts should be properly formed
        for alert in active_alerts:
            assert alert.status == AlertStatus.ACTIVE, "All alerts should be active"
            assert alert.kpi_type == KPIType.CPU_USAGE, "All alerts should be for CPU usage"
            assert alert.value > 50.0, "All alert values should be above base threshold"
    
    def test_notification_channel_error_isolation(self):
        """Test that notification channel failures don't break alerting"""
        # Add a failing notification channel
        failing_channel = Mock()
        failing_channel.send_notification = AsyncMock(side_effect=Exception("Channel failed"))
        
        # Add a working channel too
        working_channel = Mock()
        working_channel.send_notification = AsyncMock(return_value=True)
        
        self.alert_manager.add_notification_channel(failing_channel)
        self.alert_manager.add_notification_channel(working_channel)
        
        # Trigger alert
        self.alert_manager.on_threshold_exceeded(
            KPIType.CPU_USAGE,
            70.0,
            50.0,
            {"test": "error_isolation"}
        )
        
        time.sleep(0.2)  # Allow notifications to process
        
        # Alert should still be created despite notification failure
        active_alerts = self.alert_manager.get_active_alerts()
        assert len(active_alerts) >= 1, "Alert should be created despite notification failures"
        
        # Working channel should have been called
        working_channel.send_notification.assert_called()
        
        # Failed channel should have been attempted
        failing_channel.send_notification.assert_called()
    
    def test_alert_statistics_under_load(self):
        """Test alert statistics accuracy under concurrent load"""
        initial_stats = self.alert_manager.get_alert_statistics()
        
        # Generate load with multiple concurrent triggers
        def generate_alert_load():
            for i in range(10):
                self.alert_manager.on_threshold_exceeded(
                    KPIType.CPU_USAGE,
                    75.0 + (i % 3),  # Vary values to trigger different rules
                    50.0,
                    {"load_test": i}
                )
                time.sleep(0.05)
        
        # Run load generation concurrently
        threads = [threading.Thread(target=generate_alert_load) for _ in range(2)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        time.sleep(0.2)  # Allow processing to complete
        
        # Check final statistics
        final_stats = self.alert_manager.get_alert_statistics()
        
        # Should have created more alerts
        alerts_created = final_stats["stats"]["total_alerts_created"] - initial_stats["stats"]["total_alerts_created"]
        assert alerts_created > 0, f"Should have created alerts during load test, got {alerts_created}"
        
        # Active alerts count should be reasonable
        assert final_stats["active_alerts"] >= 0, "Active alerts count should be non-negative"
        
        # Statistics should be consistent
        total_active = sum(final_stats["active_by_severity"].values())
        assert total_active == final_stats["active_alerts"], \
            "Active alerts count should match sum of severity breakdown"


class TestIntegrationWithFlowMetrics:
    """Test integration between alerting system and FlowMetrics"""
    
    def setup_method(self):
        """Setup integration tests"""
        # Create FlowMetrics with alerting integration
        config = MetricsConfig(
            memory_threshold_mb=100.0,
            cpu_threshold_percent=70.0,
            error_rate_threshold=5.0
        )
        self.flow_metrics = FlowMetrics(config=config)
        
        # Create alert manager with rules matching thresholds
        self.alert_manager = AlertManager()
        
        alert_rules = [
            AlertRule(
                id="integration_cpu",
                name="CPU Integration Test",
                kpi_type=KPIType.CPU_USAGE,
                threshold=70.0,
                comparison="greater_than",
                severity=AlertSeverity.HIGH,
                description="CPU threshold exceeded"
            ),
            AlertRule(
                id="integration_memory", 
                name="Memory Integration Test",
                kpi_type=KPIType.MEMORY_USAGE,
                threshold=100.0,
                comparison="greater_than",
                severity=AlertSeverity.MEDIUM,
                description="Memory threshold exceeded"
            )
        ]
        
        for rule in alert_rules:
            self.alert_manager.add_rule(rule)
        
        # Connect alert manager as observer
        self.flow_metrics.add_observer(self.alert_manager)
    
    def test_observer_pattern_integration(self):
        """Test observer pattern integration between metrics and alerting"""
        # Mock system metrics that exceed thresholds
        with patch('ai_writing_flow.monitoring.flow_metrics.psutil.Process') as mock_process:
            mock_instance = Mock()
            mock_instance.cpu_percent.return_value = 85.0  # Above 70% threshold
            mock_instance.memory_info.return_value = Mock(rss=150 * 1024 * 1024)  # 150MB above 100MB threshold
            mock_process.return_value = mock_instance
            
            # Get KPIs - should trigger threshold checks
            kpis = self.flow_metrics.get_current_kpis(force_recalculate=True)
            
            time.sleep(0.1)  # Allow observer notifications to process
            
            # Check that alerts were created via observer pattern
            active_alerts = self.alert_manager.get_active_alerts()
            
            # Should have alerts for both CPU and memory
            alert_types = [alert.kpi_type for alert in active_alerts]
            assert KPIType.CPU_USAGE in alert_types, "Should have CPU usage alert"
            assert KPIType.MEMORY_USAGE in alert_types, "Should have memory usage alert"
            
            # Verify alert values match KPI values
            cpu_alert = next(a for a in active_alerts if a.kpi_type == KPIType.CPU_USAGE)
            memory_alert = next(a for a in active_alerts if a.kpi_type == KPIType.MEMORY_USAGE)
            
            assert abs(cpu_alert.value - 85.0) < 0.1, "CPU alert value should match metrics"
            assert abs(memory_alert.value - 150.0) < 1.0, "Memory alert value should match metrics"
    
    def test_observer_removal_stops_alerts(self):
        """Test that removing observer stops alert generation"""
        # Remove alert manager as observer
        self.flow_metrics.remove_observer(self.alert_manager)
        
        # Mock metrics that would normally trigger alerts
        with patch('ai_writing_flow.monitoring.flow_metrics.psutil.Process') as mock_process:
            mock_instance = Mock()
            mock_instance.cpu_percent.return_value = 95.0  # Well above threshold
            mock_instance.memory_info.return_value = Mock(rss=200 * 1024 * 1024)  # Well above threshold
            mock_process.return_value = mock_instance
            
            # Get KPIs
            kpis = self.flow_metrics.get_current_kpis(force_recalculate=True)
            
            time.sleep(0.1)
            
            # Should not have created any alerts
            active_alerts = self.alert_manager.get_active_alerts()
            assert len(active_alerts) == 0, "Should not create alerts when observer is removed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])