"""
Notification Module for Attendance System
Handles SMS notifications via Android SMS Gateway
"""

from .sms_notifier import SMSNotifier

__all__ = ["SMSNotifier"]
