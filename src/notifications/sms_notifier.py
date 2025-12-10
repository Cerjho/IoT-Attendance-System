#!/usr/bin/env python3
"""
SMS Notifier for Parent Notifications
Uses Android SMS Gateway Cloud Server API
API Documentation: https://capcom6.github.io/android-sms-gateway/

Enhanced with server-side template and preference management.
"""
import base64
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import requests

from src.notifications.template_cache import TemplateCache

logger = logging.getLogger(__name__)


def format_phone_number(phone: str) -> str:
    """
    Format phone number to international format (+63)

    Args:
        phone: Phone number in various formats (09xx, 639xx, +639xx)

    Returns:
        Phone number in +63 format (E.164 standard: +63XXXXXXXXXX where X is 10 digits)
    """
    # Remove spaces, dashes, parentheses, and any non-digit characters except leading +
    original = phone
    phone = phone.strip()
    has_plus = phone.startswith("+")
    phone = "".join(c for c in phone if c.isdigit())
    
    # Handle different formats
    if phone.startswith("09"):
        # 09XXXXXXXXX (11 digits) → +639XXXXXXXXX (13 chars total)
        if len(phone) == 11:
            formatted = "+63" + phone[1:]
        elif len(phone) == 12:
            # Extra digit - try to fix: 091231231123 → +639123123112 (take first 11)
            logger.warning(f"Phone has 12 digits (expected 11): {original} → using first 11 digits")
            phone = phone[:11]
            formatted = "+63" + phone[1:]
        else:
            logger.warning(f"Phone starting with 09 has unusual length {len(phone)}: {original}")
            formatted = "+63" + phone[1:]
    elif phone.startswith("63"):
        # 639XXXXXXXXX (12 digits) → +639XXXXXXXXX
        if len(phone) == 12:
            formatted = "+" + phone
        else:
            logger.warning(f"Phone starting with 63 has unusual length {len(phone)}: {original}")
            formatted = "+" + phone
    elif has_plus and phone.startswith("63"):
        # Already +639XXXXXXXXX
        if len(phone) == 12:
            formatted = "+" + phone
        else:
            logger.warning(f"Phone with +63 has unusual length {len(phone)}: {original}")
            formatted = "+" + phone
    else:
        # Unknown format - assume it's local 9XXXXXXXXX (10 digits) and add +63
        logger.warning(f"Unknown phone format, assuming local: {original}")
        formatted = "+63" + phone
    
    # Validate final format: +63 followed by 10 digits (13 chars total)
    if len(formatted) != 13 or not formatted[3:].isdigit():
        logger.warning(f"Final phone format may be invalid: {original} → {formatted} (expected 13 chars, got {len(formatted)})")
    
    logger.debug(f"Phone formatted: {original} → {formatted}")
    return formatted


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
                - supabase_url: Supabase URL for template/preference fetching
                - supabase_key: Supabase API key
                - db_path: Local database path for template cache
        """
        # Store config for later use
        self.config = config
        
        # Time provider for easier testing of cooldown & quiet hours
        self.time_provider = time_provider or TimeProvider()
        self.enabled = config.get("enabled", False)
        self.username = config.get("username")
        self.password = config.get("password")
        self.device_id = config.get("device_id")
        self.api_url = config.get(
            "api_url", "https://api.sms-gate.app/3rdparty/v1/message"
        )

        # Supabase configuration for server-side templates and preferences
        self.supabase_url = config.get("supabase_url", os.environ.get("SUPABASE_URL", ""))
        self.supabase_key = config.get("supabase_key", os.environ.get("SUPABASE_KEY", ""))
        self.server_templates_enabled = config.get("server_templates_enabled", True)
        
        # Initialize template cache
        db_path = config.get("db_path", "data/attendance.db")
        self.template_cache = TemplateCache(db_path)
        
        # Refresh templates from server on startup
        if self.server_templates_enabled and self.supabase_url and self.supabase_key:
            self._refresh_templates_from_server()

        # Legacy fallback: Support for local template configuration
        # These will be used only if server templates are disabled or unavailable
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
        
        # Signed URL configuration
        self.use_signed_urls = config.get("use_signed_urls", True)
        self.signed_url_expiry_hours = config.get("signed_url_expiry_hours", 48)
        self.url_signing_secret = os.environ.get('URL_SIGNING_SECRET')
        
        # Initialize URL signer if signed URLs enabled
        self.url_signer = None
        if self.use_signed_urls:
            if self.url_signing_secret and not self.url_signing_secret.startswith("${"):
                try:
                    from src.auth.url_signer import URLSigner
                    self.url_signer = URLSigner(self.url_signing_secret)
                    logger.info(f"URL signing enabled (expiry: {self.signed_url_expiry_hours}h)")
                except Exception as e:
                    logger.error(f"Failed to initialize URL signer: {e}")
                    self.url_signer = None
            else:
                logger.warning("Signed URLs enabled but URL_SIGNING_SECRET not set in .env")

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

        # Webhook fallback configuration (for retry when SMS gateway has no signal)
        self.webhook_config = config.get("webhook", {})
        self.webhook_enabled = self.webhook_config.get("enabled", False)
        self.webhook_url = self.webhook_config.get("url", "")
        self.webhook_auth = self.webhook_config.get("auth_header", "")
        self.webhook_timeout = self.webhook_config.get("timeout", 10)
        self.webhook_on_failure_only = self.webhook_config.get("on_failure_only", True)
        
        if self.webhook_enabled:
            if not self.webhook_url:
                logger.warning("Webhook enabled but no URL configured, disabling webhook")
                self.webhook_enabled = False
            else:
                logger.info(f"Webhook fallback enabled: {self.webhook_url} (on_failure_only={self.webhook_on_failure_only})")

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
    
    def _generate_attendance_link(self, student_identifier: str) -> str:
        """
        Generate attendance view link (signed or unsigned).
        
        Args:
            student_identifier: Student UUID from Supabase (preferred) or student_number (fallback)
        
        Returns:
            Signed URL if signing enabled, plain URL otherwise
            
        Note:
            Should use student UUID (e.g., '3c2c6e8f-...') not student_number (e.g., '2021001')
            Student_number is only for QR codes, UUID is for public links.
        """
        if not self.attendance_view_url:
            return ""
        
        # Extract base URL (remove query params if any)
        base_url = self.attendance_view_url.split('?')[0]
        
        # If URL signing enabled and signer initialized, generate signed URL
        if self.use_signed_urls and self.url_signer:
            try:
                signed_url = self.url_signer.sign_url(
                    base_url=base_url,
                    student_id=student_identifier,
                    expiry_hours=self.signed_url_expiry_hours
                )
                logger.debug(f"Generated signed URL for student {student_identifier}")
                return signed_url
            except Exception as e:
                logger.error(f"Failed to generate signed URL: {e}")
                # Fallback to unsigned URL
                return self.attendance_view_url.format(student_id=student_identifier)
        else:
            # Plain URL without signature
            return self.attendance_view_url.format(student_id=student_identifier)
    
    def _refresh_templates_from_server(self) -> bool:
        """
        Fetch SMS templates from Supabase and update local cache.
        
        Returns:
            True if templates fetched successfully
        """
        try:
            if not self.supabase_url or not self.supabase_key:
                logger.debug("Supabase credentials not configured, skipping template refresh")
                return False
            
            # Fetch all active templates from Supabase
            url = f"{self.supabase_url}/rest/v1/sms_templates"
            params = {"is_active": "eq.true", "select": "*"}
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                templates = response.json()
                count = self.template_cache.update_cache(templates)
                logger.info(f"Refreshed {count} SMS templates from server")
                return True
            else:
                logger.warning(f"Failed to fetch templates from server: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error refreshing templates from server: {e}")
            return False
    
    def _get_template_from_server_or_cache(self, template_type: str) -> str:
        """
        Get template message text from cache (or fallback to local config).
        
        Args:
            template_type: Type of template (check_in, check_out, late_arrival, etc.)
        
        Returns:
            Template message text with {{variable}} placeholders
        """
        if not self.server_templates_enabled:
            # Use legacy local templates
            return self._get_local_template(template_type)
        
        # Try to get from cache first
        template_text = self.template_cache.get_template_text(template_type)
        
        # Check if cache is stale and attempt refresh in background
        if self.template_cache.is_cache_stale():
            logger.debug("Template cache is stale, attempting refresh")
            self._refresh_templates_from_server()
        
        return template_text
    
    def _get_local_template(self, template_type: str) -> str:
        """
        Get template from local config (legacy fallback).
        
        Args:
            template_type: Type of template
        
        Returns:
            Template string with {variable} placeholders (Python format style)
        """
        template_map = {
            'check_in': self.login_message_template,
            'check_out': self.logout_message_template,
            'late_arrival': self.late_arrival_template,
            'early_departure': self.no_checkout_template,
            'absence_detected': self.absence_alert_template,
            'no_checkout': self.no_checkout_template,
        }
        return template_map.get(template_type, self.login_message_template)
    
    def _should_send_notification(
        self, 
        phone: str, 
        student_id: str, 
        notification_type: str,
        student_uuid: Optional[str] = None
    ) -> bool:
        """
        Check if notification should be sent based on server preferences.
        
        Args:
            phone: Parent phone number
            student_id: Student number (e.g., '2021001')
            notification_type: Type of notification (check_in, check_out, etc.)
            student_uuid: Student UUID from Supabase (if available)
        
        Returns:
            True if notification should be sent
        """
        if not self.server_templates_enabled or not self.supabase_url:
            # Fallback to local checks only
            return True
        
        try:
            # Call should_send_notification RPC function
            url = f"{self.supabase_url}/rest/v1/rpc/should_send_notification"
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "application/json"
            }
            
            # Use UUID if available, otherwise student_number
            identifier = student_uuid if student_uuid else student_id
            
            payload = {
                "phone_param": phone,
                "student_id_param": identifier,
                "notification_type": notification_type
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                should_send = result if isinstance(result, bool) else True
                
                if not should_send:
                    logger.info(f"Notification blocked by server preferences: {notification_type} to {phone}")
                
                return should_send
            else:
                # On error, default to allowing notification (fail open)
                logger.warning(f"Failed to check notification preferences: {response.status_code}")
                return True
                
        except Exception as e:
            logger.error(f"Error checking notification preferences: {e}")
            # Fail open: allow notification if check fails
            return True
    
    def _format_template_variables(self, template: str, **kwargs) -> str:
        """
        Format template variables, supporting both {{var}} and {var} styles.
        
        Args:
            template: Template string
            **kwargs: Variable values
        
        Returns:
            Formatted message
        """
        # Convert {{variable}} to {variable} for Python formatting
        import re
        formatted_template = re.sub(r'\{\{(\w+)\}\}', r'{\1}', template)
        
        try:
            return formatted_template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            # Return template with missing variables as-is
            return formatted_template

    def send_attendance_notification(
        self,
        student_id: str,
        student_name: Optional[str],
        parent_phone: str,
        timestamp: Optional[datetime] = None,
        scan_type: str = "time_in",
        status: str = "present",
        minutes_late: int = 0,
        student_uuid: Optional[str] = None,
    ) -> bool:
        """
        Send attendance notification to parent

        Args:
            student_id: Student number (from QR code, e.g., '2021001')
            student_name: Student name (optional)
            parent_phone: Parent's phone number (E.164 format preferred)
            timestamp: Attendance timestamp (defaults to now)
            scan_type: 'time_in' for login or 'time_out' for logout
            status: 'present', 'late', or 'absent'
            minutes_late: Minutes late (if status is 'late')
            student_uuid: Student UUID from Supabase (for attendance link)

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

        # Check quiet hours (local check)
        if self._is_quiet_hours():
            logger.info(f"Quiet hours active, skipping SMS for {student_id}")
            return False

        # Determine notification type for server preference check
        notification_type = self._get_notification_type(scan_type, status, minutes_late)
        
        # Check server-side preferences
        if not self._should_send_notification(parent_phone, student_id, notification_type, student_uuid):
            return False

        # Check cooldown (local)
        if not self._check_cooldown(student_id, notification_type):
            return False

        # Use current time if not provided
        if timestamp is None:
            timestamp = self.time_provider.now()

        # Get template from server/cache
        template = self._get_template_from_server_or_cache(notification_type)

        # Generate attendance view link using UUID (not student_number)
        link_identifier = student_uuid if student_uuid else student_id
        attendance_link = self._generate_attendance_link(link_identifier)

        # Prepare template variables
        template_vars = {
            'student_id': student_id,
            'student_number': student_id,
            'student_name': student_name or student_id,
            'time': timestamp.strftime("%I:%M %p"),
            'date': timestamp.strftime("%B %d, %Y"),
            'attendance_link': attendance_link,
            'minutes_late': minutes_late,
            'school_name': self.config.get('school_name', 'School')
        }

        # Format message
        message = self._format_template_variables(template, **template_vars)

        # Add unsubscribe text if enabled
        if self.include_unsubscribe:
            message += self.unsubscribe_text

        # Send SMS
        return self.send_sms(parent_phone, message)
    
    def _get_notification_type(self, scan_type: str, status: str, minutes_late: int) -> str:
        """
        Determine notification type for template/preference lookup.
        
        Args:
            scan_type: 'time_in' or 'time_out'
            status: 'present', 'late', etc.
            minutes_late: Minutes late
        
        Returns:
            Notification type string (check_in, check_out, late_arrival, etc.)
        """
        if status == "late" and minutes_late > 0:
            return "late_arrival"
        elif scan_type == "time_out":
            return "check_out"
        else:
            return "check_in"

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
            message_preview = message[:50] + "..." if len(message) > 50 else message
            logger.info(f"📱 SMS Send Started: to={phone_number}→{formatted_phone}, msg_len={len(message)}, preview='{message_preview}'")
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
                    if i > 0:
                        logger.info(f"📱 SMS Retry: attempt {i+1}/{attempts} for {phone_number}")
                    
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
                        try:
                            response_data = response.json()
                            message_id = response_data.get("id", "unknown")
                        except json.JSONDecodeError:
                            logger.warning(f"SMS API returned non-JSON response: {response.text[:100]}")
                            message_id = "unknown"
                            
                        logger.info(
                            f"✅ SMS Sent Successfully: to={phone_number}, msg_id={message_id}, attempt={i+1}/{attempts}, msg_len={len(message)}"
                        )
                        return True
                    else:
                        last_err = f"status={response.status_code} body={response.text}"
                        logger.warning(
                            f"⚠️ SMS HTTP Error: to={phone_number}, attempt={i+1}/{attempts}, status={response.status_code}, response='{response.text[:100]}'"
                        )
                except requests.exceptions.SSLError as e:
                    last_err = f"SSL error: {str(e)}"
                    logger.warning(
                        f"⚠️ SMS SSL Error: to={phone_number}, attempt={i+1}/{attempts}, error={str(e)[:100]}"
                    )
                except requests.exceptions.Timeout as e:
                    last_err = f"Timeout: {str(e)}"
                    logger.warning(
                        f"⚠️ SMS Timeout: to={phone_number}, attempt={i+1}/{attempts}, waited=10s"
                    )
                except requests.exceptions.ConnectionError as e:
                    last_err = f"Connection refused: {str(e)}"
                    logger.warning(
                        f"⚠️ SMS Connection Error: to={phone_number}, attempt={i+1}/{attempts}, error={str(e)[:100]} (API may be down)"
                    )
                except Exception as e:
                    last_err = str(e)
                    logger.warning(
                        f"❌ SMS Unexpected Error: to={phone_number}, attempt={i+1}/{attempts}, error={str(e)[:100]}"
                    )
                if i + 1 < attempts:
                    try:
                        import time as _time
                        _time.sleep(delay)
                        delay = min(delay * 2, 10)
                    except Exception:
                        pass

            logger.error(f"❌ SMS Failed: to={phone_number}, all {attempts} attempts exhausted, last_error='{last_err}'")
            
            # Try webhook fallback if enabled and configured for failure retry
            if self.webhook_enabled and self.webhook_on_failure_only:
                logger.info(f"📡 SMS failed, attempting webhook fallback for {phone_number}")
                return self._send_via_webhook(formatted_phone, message, phone_number)
            
            return False
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            
            # Try webhook fallback on exception
            if self.webhook_enabled and self.webhook_on_failure_only:
                try:
                    formatted_phone = format_phone_number(phone_number)
                    logger.info(f"📡 SMS exception, attempting webhook fallback for {phone_number}")
                    return self._send_via_webhook(formatted_phone, message, phone_number)
                except Exception:
                    pass
            
            return False

    def _send_via_webhook(
        self,
        phone_number: str,
        message: str,
        original_phone: str = None,
    ) -> bool:
        """
        Send SMS via webhook fallback (e.g., when local gateway has no signal)
        
        Args:
            phone_number: Formatted phone number (+63 format)
            message: SMS message content
            original_phone: Original unformatted phone number (for logging)
            
        Returns:
            bool: True if webhook sent successfully
        """
        if not self.webhook_enabled:
            return False
            
        try:
            payload = {
                "type": "sms_retry",
                "phone": phone_number,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "device_id": self.device_id,
                "reason": "local_gateway_failed"
            }
            
            headers = {"Content-Type": "application/json"}
            if self.webhook_auth:
                headers["Authorization"] = self.webhook_auth
            
            logger.debug(f"Sending webhook to {self.webhook_url}")
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=self.webhook_timeout,
            )
            
            if response.status_code in [200, 201, 202, 204]:
                logger.info(
                    f"✅ Webhook sent successfully: to={original_phone or phone_number}, "
                    f"status={response.status_code}"
                )
                return True
            else:
                logger.warning(
                    f"⚠️ Webhook failed: status={response.status_code}, "
                    f"response={response.text[:200]}"
                )
                return False
                
        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ Webhook timeout after {self.webhook_timeout}s")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"⚠️ Webhook connection error: {str(e)[:100]}")
            return False
        except Exception as e:
            logger.error(f"❌ Webhook error: {str(e)}")
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
