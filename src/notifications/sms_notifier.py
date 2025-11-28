#!/usr/bin/env python3
"""
SMS Notifier for Parent Notifications
Uses Android SMS Gateway Cloud Server API
API Documentation: https://capcom6.github.io/android-sms-gateway/
"""
import base64
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


def format_phone_number(phone: str) -> str:
    """
    Format phone number to international format (+63)

    Args:
        phone: Phone number in various formats (09xx, 639xx, +639xx)

    Returns:
        Phone number in +63 format
    """
    # Remove spaces, dashes, parentheses
    phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

    # Convert 09xx to +639xx
    if phone.startswith("09"):
        return "+63" + phone[1:]

    # Convert 639xx to +639xx
    if phone.startswith("63") and not phone.startswith("+63"):
        return "+" + phone

    # Already in +63 format
    if phone.startswith("+63"):
        return phone

    # Unknown format, return as-is
    logger.warning(f"Unknown phone format: {phone}")
    return phone


class TimeProvider:
    """Provides current time. Abstracted for testability."""
    def now(self) -> datetime:
        return datetime.now()


class SMSNotifier:
    """
    SMS notification service using Android SMS Gateway
    Cloud Server API: https://api.sms-gate.app/3rdparty/v1/message
    """

    def __init__(self, config: Dict[str, Any], time_provider: Any = None):
        """
        Initialize SMS Notifier

        Args:
            config: Configuration dictionary with keys:
                - enabled: Enable/disable SMS notifications
                - username: SMS Gateway username
                - password: SMS Gateway password
                - device_id: SMS Gateway device ID
                - api_url: API endpoint URL (optional, defaults to cloud server)
                - message_template: SMS message template (optional)
        """
        # Time provider for easier testing of cooldown & quiet hours
        self.time_provider = time_provider or TimeProvider()
        self.enabled = config.get("enabled", False)
        self.username = config.get("username")
        self.password = config.get("password")
        self.device_id = config.get("device_id")
        self.api_url = config.get(
            "api_url", "https://api.sms-gate.app/3rdparty/v1/message"
        )

        # Support for multiple message templates
        self.login_message_template = config.get(
            "login_message_template",
            config.get(
                "message_template",
                "Good day! {student_name} (ID: {student_id}) checked IN at {time} on {date}.",
            ),
        )
        self.logout_message_template = config.get(
            "logout_message_template",
            "Good day! {student_name} (ID: {student_id}) checked OUT at {time} on {date}.",
        )
        self.late_arrival_template = config.get(
            "late_arrival_template",
            "⚠️ LATE ARRIVAL: {student_name} checked in at {time} ({minutes_late} mins late) on {date}.",
        )
        self.no_checkout_template = config.get(
            "no_checkout_template",
            "⚠️ NO CHECK-OUT: {student_name} did not check out. Last seen: {last_checkin_time}.",
        )
        self.absence_alert_template = config.get(
            "absence_alert_template",
            "❗ ABSENCE ALERT: {student_name} not detected at school on {date}.",
        )
        self.weekly_summary_template = config.get(
            "weekly_summary_template",
            "Week summary for {student_name}: {days_present}P {late_count}L {absent_count}A",
        )
        self.monthly_summary_template = config.get(
            "monthly_summary_template",
            "Month summary for {student_name}: {days_present}P {late_count}L {absent_count}A ({attendance_rate}%)",
        )

        # Attendance view URL for public access (no account needed)
        self.attendance_view_url = config.get("attendance_view_url", "")

        # Notification preferences
        self.notification_prefs = config.get("notification_preferences", {})

        # Quiet hours configuration
        self.quiet_hours = config.get("quiet_hours", {})
        self.quiet_hours_enabled = self.quiet_hours.get("enabled", True)
        self.quiet_start = self.quiet_hours.get("start", "22:00")
        self.quiet_end = self.quiet_hours.get("end", "06:00")

        # Duplicate SMS prevention
        self.cooldown_minutes = config.get("duplicate_sms_cooldown_minutes", 5)
        self.recent_notifications = {}  # Track recent SMS to prevent duplicates

        # Unsubscribe text
        self.include_unsubscribe = config.get("include_unsubscribe", True)
        self.unsubscribe_text = config.get(
            "unsubscribe_text", "\n\nReply STOP to unsubscribe"
        )

        # Validate configuration
        if self.enabled:
            if not all([self.username, self.password, self.device_id]):
                logger.error("SMS notification enabled but credentials are missing!")
                self.enabled = False
            else:
                # Validate environment variables are not placeholders
                if self.username and self.username.startswith("${"):
                    logger.error(
                        f"SMS username not loaded from environment: {self.username}"
                    )
                    self.enabled = False
                elif self.password and self.password.startswith("${"):
                    logger.error("SMS password not loaded from environment")
                    self.enabled = False
                elif self.device_id and self.device_id.startswith("${"):
                    logger.error(
                        f"SMS device_id not loaded from environment: {self.device_id}"
                    )
                    self.enabled = False
                else:
                    logger.info(f"SMS Notifier initialized (Device: {self.device_id})")
        else:
            logger.info("SMS Notifier disabled")

    def _is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours"""
        if not self.quiet_hours_enabled:
            return False

        now = self.time_provider.now().time()
        start = datetime.strptime(self.quiet_start, "%H:%M").time()
        end = datetime.strptime(self.quiet_end, "%H:%M").time()

        if start < end:
            return start <= now <= end
        else:  # Quiet hours span midnight
            return now >= start or now <= end

    def _check_cooldown(self, student_id: str, notification_type: str) -> bool:
        """
        Check if notification is within cooldown period

        Returns:
            bool: True if notification should be sent, False if in cooldown
        """
        key = f"{student_id}_{notification_type}"
        last_sent = self.recent_notifications.get(key)

        if last_sent:
            elapsed = (self.time_provider.now() - last_sent).total_seconds() / 60
            if elapsed < self.cooldown_minutes:
                logger.debug(f"SMS cooldown active for {key} ({elapsed:.1f} mins ago)")
                return False

        # Update last sent time
        self.recent_notifications[key] = self.time_provider.now()
        return True

    def send_attendance_notification(
        self,
        student_id: str,
        student_name: Optional[str],
        parent_phone: str,
        timestamp: Optional[datetime] = None,
        scan_type: str = "time_in",
        status: str = "present",
        minutes_late: int = 0,
    ) -> bool:
        """
        Send attendance notification to parent

        Args:
            student_id: Student identifier
            student_name: Student name (optional)
            parent_phone: Parent's phone number (E.164 format preferred)
            timestamp: Attendance timestamp (defaults to now)
            scan_type: 'time_in' for login or 'time_out' for logout
            status: 'present', 'late', or 'absent'
            minutes_late: Minutes late (if status is 'late')

        Returns:
            bool: True if notification sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("SMS notifications disabled, skipping")
            return False

        if not parent_phone:
            logger.warning(
                f"No parent phone number for student {student_id}, skipping SMS"
            )
            return False

        # Check quiet hours
        if self._is_quiet_hours():
            logger.info(f"Quiet hours active, skipping SMS for {student_id}")
            return False

        # Check cooldown
        notification_type = f"{scan_type}_{status}"
        if not self._check_cooldown(student_id, notification_type):
            return False

        # Use current time if not provided
        if timestamp is None:
            timestamp = self.time_provider.now()

        # Select appropriate message template based on status and scan type
        if status == "late" and minutes_late > 0:
            message_template = self.late_arrival_template
        elif scan_type == "time_out":
            message_template = self.logout_message_template
        else:
            message_template = self.login_message_template

        # Generate attendance view link
        attendance_link = ""
        if self.attendance_view_url:
            attendance_link = self.attendance_view_url.format(student_id=student_id)

        # Format message
        message = message_template.format(
            student_id=student_id,
            student_name=student_name or student_id,
            time=timestamp.strftime("%I:%M %p"),
            date=timestamp.strftime("%B %d, %Y"),
            attendance_link=attendance_link,
            minutes_late=minutes_late,
        )

        # Add unsubscribe text if enabled
        if self.include_unsubscribe:
            message += self.unsubscribe_text

        # Send SMS
        return self.send_sms(parent_phone, message)

    def send_sms(self, phone_number: str, message: str) -> bool:
        """
        Send SMS via Android SMS Gateway API

        Args:
            phone_number: Recipient phone number
            message: Message text

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Format phone number to international format
            formatted_phone = format_phone_number(phone_number)
            logger.debug(f"Phone formatted: {phone_number} → {formatted_phone}")

            # Prepare request payload (SMS-Gate API format)
            payload = {"phoneNumbers": [formatted_phone], "message": message}

            # Create Basic Auth header
            credentials = f"{self.username}:{self.password}"
            b64_credentials = base64.b64encode(credentials.encode()).decode()

            # Build URL with device ID
            url = f"{self.api_url}?deviceId={self.device_id}"

            # Retry strategy
            attempts = 3
            delay = 2
            last_err = None
            for i in range(attempts):
                try:
                    response = requests.post(
                        url,
                        json=payload,
                        headers={
                            "Authorization": f"Basic {b64_credentials}",
                            "Content-Type": "application/json",
                        },
                        timeout=10,
                    )
                    if response.status_code in [200, 202]:
                        response_data = response.json()
                        message_id = response_data.get("id", "unknown")
                        logger.info(
                            f"SMS sent successfully to {phone_number} (Message ID: {message_id})"
                        )
                        return True
                    else:
                        last_err = f"status={response.status_code} body={response.text}"
                        logger.warning(
                            f"SMS send failed attempt {i+1}/{attempts}: {last_err}"
                        )
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    last_err = str(e)
                    logger.warning(
                        f"SMS send error attempt {i+1}/{attempts}: {last_err}"
                    )
                except Exception as e:
                    last_err = str(e)
                    logger.warning(
                        f"SMS unexpected error attempt {i+1}/{attempts}: {last_err}"
                    )
                if i + 1 < attempts:
                    try:
                        import time as _time
                        _time.sleep(delay)
                        delay = min(delay * 2, 10)
                    except Exception:
                        pass

            logger.error(f"Failed to send SMS after retries: {last_err}")
            return False
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return False

    def send_no_checkout_alert(
        self,
        student_id: str,
        student_name: str,
        parent_phone: str,
        last_checkin_time: datetime,
    ) -> bool:
        """Send alert when student doesn't check out"""
        if not self.notification_prefs.get("no_checkout", False):
            return False

        if self._is_quiet_hours() or not self._check_cooldown(
            student_id, "no_checkout"
        ):
            return False

        attendance_link = (
            self.attendance_view_url.format(student_id=student_id)
            if self.attendance_view_url
            else ""
        )

        message = self.no_checkout_template.format(
            student_name=student_name,
            last_checkin_time=last_checkin_time.strftime("%I:%M %p"),
            attendance_link=attendance_link,
        )

        if self.include_unsubscribe:
            message += self.unsubscribe_text

        return self.send_sms(parent_phone, message)

    def send_absence_alert(
        self, student_id: str, student_name: str, parent_phone: str, date: datetime
    ) -> bool:
        """Send alert when student is absent"""
        if not self.notification_prefs.get("absence", False):
            return False

        if self._is_quiet_hours() or not self._check_cooldown(student_id, "absence"):
            return False

        attendance_link = (
            self.attendance_view_url.format(student_id=student_id)
            if self.attendance_view_url
            else ""
        )

        message = self.absence_alert_template.format(
            student_name=student_name,
            date=date.strftime("%B %d, %Y"),
            attendance_link=attendance_link,
        )

        if self.include_unsubscribe:
            message += self.unsubscribe_text

        return self.send_sms(parent_phone, message)

    def test_connection(self) -> Dict[str, Any]:
        """
        Test SMS Gateway connection

        Returns:
            dict: Test result with status and message
        """
        if not self.enabled:
            return {"status": "disabled", "message": "SMS notifications are disabled"}

        if not all([self.username, self.password, self.device_id]):
            return {"status": "error", "message": "Missing SMS Gateway credentials"}

        try:
            # Test with a simple request (we won't actually send an SMS)
            # Just verify credentials are accepted
            test_payload = {
                "textMessage": {"text": "Test connection"},
                "phoneNumbers": ["+1234567890"],  # Dummy number
                "deviceId": self.device_id,
            }

            # Make a test request (it will fail due to invalid number, but that's ok)
            response = requests.post(
                self.api_url,
                json=test_payload,
                auth=(self.username, self.password),
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            # Even if request fails, if we get 401, credentials are wrong
            if response.status_code == 401:
                return {
                    "status": "error",
                    "message": "Authentication failed. Check username and password.",
                }

            # Any other response means credentials are accepted
            return {
                "status": "success",
                "message": "SMS Gateway connection OK",
                "device_id": self.device_id,
            }

        except requests.exceptions.Timeout:
            return {"status": "error", "message": "Connection timeout"}

        except Exception as e:
            return {"status": "error", "message": f"Connection error: {str(e)}"}
