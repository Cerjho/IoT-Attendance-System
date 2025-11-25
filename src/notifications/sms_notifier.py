#!/usr/bin/env python3
"""
SMS Notifier for Parent Notifications
Uses Android SMS Gateway Cloud Server API
API Documentation: https://capcom6.github.io/android-sms-gateway/
"""
import requests
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import base64

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
    phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    # Convert 09xx to +639xx
    if phone.startswith('09'):
        return '+63' + phone[1:]
    
    # Convert 639xx to +639xx
    if phone.startswith('63') and not phone.startswith('+63'):
        return '+' + phone
    
    # Already in +63 format
    if phone.startswith('+63'):
        return phone
    
    # Unknown format, return as-is
    logger.warning(f"Unknown phone format: {phone}")
    return phone


class SMSNotifier:
    """
    SMS notification service using Android SMS Gateway
    Cloud Server API: https://api.sms-gate.app/3rdparty/v1/message
    """
    
    def __init__(self, config: Dict[str, Any]):
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
        self.enabled = config.get('enabled', False)
        self.username = config.get('username')
        self.password = config.get('password')
        self.device_id = config.get('device_id')
        self.api_url = config.get('api_url', 'https://api.sms-gate.app/3rdparty/v1/message')
        
        # Support for separate login and logout message templates
        self.login_message_template = config.get('login_message_template', 
            config.get('message_template', 
                'Good day! {student_name} (ID: {student_id}) checked IN at {time} on {date}.'))
        self.logout_message_template = config.get('logout_message_template',
            'Good day! {student_name} (ID: {student_id}) checked OUT at {time} on {date}.')
        
        # Attendance view URL for public access (no account needed)
        self.attendance_view_url = config.get('attendance_view_url', '')
        
        # Validate configuration
        if self.enabled:
            if not all([self.username, self.password, self.device_id]):
                logger.error("SMS notification enabled but credentials are missing!")
                self.enabled = False
            else:
                logger.info(f"SMS Notifier initialized (Device: {self.device_id})")
        else:
            logger.info("SMS Notifier disabled")
    
    def send_attendance_notification(
        self, 
        student_id: str,
        student_name: Optional[str],
        parent_phone: str,
        timestamp: Optional[datetime] = None,
        scan_type: str = 'time_in'
    ) -> bool:
        """
        Send attendance notification to parent
        
        Args:
            student_id: Student identifier
            student_name: Student name (optional)
            parent_phone: Parent's phone number (E.164 format preferred)
            timestamp: Attendance timestamp (defaults to now)
            scan_type: 'time_in' for login or 'time_out' for logout
            
        Returns:
            bool: True if notification sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("SMS notifications disabled, skipping")
            return False
        
        if not parent_phone:
            logger.warning(f"No parent phone number for student {student_id}, skipping SMS")
            return False
        
        # Use current time if not provided
        if timestamp is None:
            timestamp = datetime.now()
        
        # Select appropriate message template based on scan type
        message_template = self.logout_message_template if scan_type == 'time_out' else self.login_message_template
        
        # Generate attendance view link
        attendance_link = ''
        if self.attendance_view_url:
            attendance_link = self.attendance_view_url.format(student_id=student_id)
        
        # Format message
        message = message_template.format(
            student_id=student_id,
            student_name=student_name or student_id,
            time=timestamp.strftime('%I:%M %p'),
            date=timestamp.strftime('%B %d, %Y'),
            attendance_link=attendance_link
        )
        
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
            payload = {
                "phoneNumbers": [formatted_phone],
                "message": message
            }
            
            # Create Basic Auth header
            credentials = f"{self.username}:{self.password}"
            b64_credentials = base64.b64encode(credentials.encode()).decode()
            
            # Build URL with device ID
            url = f"{self.api_url}?deviceId={self.device_id}"
            
            # Make API request with Basic Auth
            response = requests.post(
                url,
                json=payload,
                headers={
                    'Authorization': f'Basic {b64_credentials}',
                    'Content-Type': 'application/json'
                },
                timeout=10
            )
            
            # Check response
            if response.status_code in [200, 202]:  # Success or Accepted
                response_data = response.json()
                message_id = response_data.get('id', 'unknown')
                logger.info(f"SMS sent successfully to {phone_number} (Message ID: {message_id})")
                return True
            else:
                logger.error(f"Failed to send SMS. Status: {response.status_code}, Response: {response.text}")
                return False
        
        except requests.exceptions.Timeout:
            logger.error(f"SMS API request timeout for {phone_number}")
            return False
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"SMS API connection error: {str(e)}")
            return False
        
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return False
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test SMS Gateway connection
        
        Returns:
            dict: Test result with status and message
        """
        if not self.enabled:
            return {
                'status': 'disabled',
                'message': 'SMS notifications are disabled'
            }
        
        if not all([self.username, self.password, self.device_id]):
            return {
                'status': 'error',
                'message': 'Missing SMS Gateway credentials'
            }
        
        try:
            # Test with a simple request (we won't actually send an SMS)
            # Just verify credentials are accepted
            test_payload = {
                "textMessage": {
                    "text": "Test connection"
                },
                "phoneNumbers": ["+1234567890"],  # Dummy number
                "deviceId": self.device_id
            }
            
            # Make a test request (it will fail due to invalid number, but that's ok)
            response = requests.post(
                self.api_url,
                json=test_payload,
                auth=(self.username, self.password),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            # Even if request fails, if we get 401, credentials are wrong
            if response.status_code == 401:
                return {
                    'status': 'error',
                    'message': 'Authentication failed. Check username and password.'
                }
            
            # Any other response means credentials are accepted
            return {
                'status': 'success',
                'message': 'SMS Gateway connection OK',
                'device_id': self.device_id
            }
        
        except requests.exceptions.Timeout:
            return {
                'status': 'error',
                'message': 'Connection timeout'
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Connection error: {str(e)}'
            }
