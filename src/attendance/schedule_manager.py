#!/usr/bin/env python3
"""
School Schedule Manager
Handles morning/afternoon class sessions, login/logout tracking
"""

import logging
from datetime import datetime, time, timedelta
from typing import Dict, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class SessionType(Enum):
    """Class session types"""
    MORNING = "morning"
    AFTERNOON = "afternoon"
    UNKNOWN = "unknown"


class ScanType(Enum):
    """Type of attendance scan"""
    LOGIN = "time_in"      # Arrival/Check-in
    LOGOUT = "time_out"    # Dismissal/Check-out


class AttendanceStatus(Enum):
    """Attendance status types"""
    PRESENT = "present"
    LATE = "late"
    ABSENT = "absent"
    EXCUSED = "excused"


class ScheduleManager:
    """
    Manages school schedule for morning and afternoon classes
    
    Morning Class: 7:00 AM - 12:00 PM
    - Login window: 6:30 AM - 7:30 AM
    - Logout window: 11:30 AM - 12:30 PM
    
    Afternoon Class: 1:00 PM - 5:00 PM  
    - Login window: 12:30 PM - 1:30 PM
    - Logout window: 4:30 PM - 5:30 PM
    """
    
    def __init__(self, config: Dict):
        """
        Initialize schedule manager
        
        Args:
            config: School schedule configuration
        """
        self.config = config
        
        # Morning class schedule
        morning = config.get('morning_class', {})
        self.morning_start = self._parse_time(morning.get('start_time', '07:00'))
        self.morning_end = self._parse_time(morning.get('end_time', '12:00'))
        self.morning_login_start = self._parse_time(morning.get('login_window_start', '06:30'))
        self.morning_login_end = self._parse_time(morning.get('login_window_end', '07:30'))
        self.morning_logout_start = self._parse_time(morning.get('logout_window_start', '11:30'))
        self.morning_logout_end = self._parse_time(morning.get('logout_window_end', '12:30'))
        self.morning_late_threshold = morning.get('late_threshold_minutes', 15)
        
        # Afternoon class schedule
        afternoon = config.get('afternoon_class', {})
        self.afternoon_start = self._parse_time(afternoon.get('start_time', '13:00'))
        self.afternoon_end = self._parse_time(afternoon.get('end_time', '17:00'))
        self.afternoon_login_start = self._parse_time(afternoon.get('login_window_start', '12:30'))
        self.afternoon_login_end = self._parse_time(afternoon.get('login_window_end', '13:30'))
        self.afternoon_logout_start = self._parse_time(afternoon.get('logout_window_start', '16:30'))
        self.afternoon_logout_end = self._parse_time(afternoon.get('logout_window_end', '17:30'))
        self.afternoon_late_threshold = afternoon.get('late_threshold_minutes', 15)
        
        # General settings
        self.auto_detect_session = config.get('auto_detect_session', True)
        self.allow_early_arrival = config.get('allow_early_arrival', True)
        self.require_logout = config.get('require_logout', True)
        self.duplicate_cooldown_minutes = config.get('duplicate_scan_cooldown_minutes', 5)
        
        logger.info("Schedule Manager initialized:")
        logger.info(f"  Morning: {self.morning_start.strftime('%H:%M')} - {self.morning_end.strftime('%H:%M')}")
        logger.info(f"  Afternoon: {self.afternoon_start.strftime('%H:%M')} - {self.afternoon_end.strftime('%H:%M')}")
    
    def _parse_time(self, time_str: str) -> time:
        """Parse time string (HH:MM) to time object"""
        try:
            return datetime.strptime(time_str, '%H:%M').time()
        except Exception as e:
            logger.error(f"Error parsing time '{time_str}': {e}")
            return time(0, 0)
    
    def get_current_session(self, current_time: datetime = None) -> SessionType:
        """
        Determine current class session based on time
        
        Args:
            current_time: Time to check (default: now)
            
        Returns:
            SessionType (MORNING, AFTERNOON, or UNKNOWN)
        """
        if current_time is None:
            current_time = datetime.now()
        
        current = current_time.time()
        
        # Check morning session (including login/logout windows)
        if self.morning_login_start <= current <= self.morning_logout_end:
            return SessionType.MORNING
        
        # Check afternoon session (including login/logout windows)
        if self.afternoon_login_start <= current <= self.afternoon_logout_end:
            return SessionType.AFTERNOON
        
        return SessionType.UNKNOWN
    
    def get_expected_scan_type(self, current_time: datetime = None) -> Tuple[ScanType, SessionType]:
        """
        Determine what type of scan is expected now (login or logout)
        
        Args:
            current_time: Time to check (default: now)
            
        Returns:
            Tuple of (ScanType, SessionType)
        """
        if current_time is None:
            current_time = datetime.now()
        
        current = current_time.time()
        session = self.get_current_session(current_time)
        
        if session == SessionType.MORNING:
            # Morning session
            if self.morning_login_start <= current <= self.morning_login_end:
                return (ScanType.LOGIN, SessionType.MORNING)
            elif self.morning_logout_start <= current <= self.morning_logout_end:
                return (ScanType.LOGOUT, SessionType.MORNING)
            elif current <= self.morning_logout_start:
                # During class, default to login if not logged in yet
                return (ScanType.LOGIN, SessionType.MORNING)
        
        elif session == SessionType.AFTERNOON:
            # Afternoon session
            if self.afternoon_login_start <= current <= self.afternoon_login_end:
                return (ScanType.LOGIN, SessionType.AFTERNOON)
            elif self.afternoon_logout_start <= current <= self.afternoon_logout_end:
                return (ScanType.LOGOUT, SessionType.AFTERNOON)
            elif current <= self.afternoon_logout_start:
                # During class, default to login if not logged in yet
                return (ScanType.LOGIN, SessionType.AFTERNOON)
        
        # Outside class hours
        return (ScanType.LOGIN, SessionType.UNKNOWN)
    
    def determine_attendance_status(
        self, 
        scan_time: datetime,
        session: SessionType,
        scan_type: ScanType
    ) -> AttendanceStatus:
        """
        Determine attendance status based on scan time
        
        Args:
            scan_time: Time of attendance scan
            session: Class session (MORNING or AFTERNOON)
            scan_type: Type of scan (LOGIN or LOGOUT)
            
        Returns:
            AttendanceStatus (PRESENT or LATE)
        """
        if scan_type == ScanType.LOGOUT:
            # Logout scans are always marked as present
            return AttendanceStatus.PRESENT
        
        # For LOGIN scans, check if late
        current = scan_time.time()
        
        if session == SessionType.MORNING:
            late_time = (
                datetime.combine(scan_time.date(), self.morning_start) + 
                timedelta(minutes=self.morning_late_threshold)
            ).time()
            
            if current > late_time:
                return AttendanceStatus.LATE
        
        elif session == SessionType.AFTERNOON:
            late_time = (
                datetime.combine(scan_time.date(), self.afternoon_start) + 
                timedelta(minutes=self.afternoon_late_threshold)
            ).time()
            
            if current > late_time:
                return AttendanceStatus.LATE
        
        return AttendanceStatus.PRESENT
    
    def is_within_login_window(self, current_time: datetime = None) -> bool:
        """Check if current time is within any login window"""
        if current_time is None:
            current_time = datetime.now()
        
        current = current_time.time()
        
        # Check morning login window
        if self.morning_login_start <= current <= self.morning_login_end:
            return True
        
        # Check afternoon login window
        if self.afternoon_login_start <= current <= self.afternoon_login_end:
            return True
        
        return False
    
    def is_within_logout_window(self, current_time: datetime = None) -> bool:
        """Check if current time is within any logout window"""
        if current_time is None:
            current_time = datetime.now()
        
        current = current_time.time()
        
        # Check morning logout window
        if self.morning_logout_start <= current <= self.morning_logout_end:
            return True
        
        # Check afternoon logout window
        if self.afternoon_logout_start <= current <= self.afternoon_logout_end:
            return True
        
        return False
    
    def get_schedule_info(self, current_time: datetime = None) -> Dict:
        """
        Get current schedule information for display
        
        Args:
            current_time: Time to check (default: now)
            
        Returns:
            Dictionary with schedule information
        """
        if current_time is None:
            current_time = datetime.now()
        
        session = self.get_current_session(current_time)
        scan_type, detected_session = self.get_expected_scan_type(current_time)
        attendance_status = self.determine_attendance_status(current_time, session, scan_type)
        
        info = {
            'current_time': current_time.strftime('%H:%M:%S'),
            'current_session': session.value,
            'expected_scan_type': scan_type.value,
            'attendance_status': attendance_status.value,
            'in_login_window': self.is_within_login_window(current_time),
            'in_logout_window': self.is_within_logout_window(current_time)
        }
        
        if session == SessionType.MORNING:
            info['session_start'] = self.morning_start.strftime('%H:%M')
            info['session_end'] = self.morning_end.strftime('%H:%M')
            info['login_window'] = f"{self.morning_login_start.strftime('%H:%M')} - {self.morning_login_end.strftime('%H:%M')}"
            info['logout_window'] = f"{self.morning_logout_start.strftime('%H:%M')} - {self.morning_logout_end.strftime('%H:%M')}"
        
        elif session == SessionType.AFTERNOON:
            info['session_start'] = self.afternoon_start.strftime('%H:%M')
            info['session_end'] = self.afternoon_end.strftime('%H:%M')
            info['login_window'] = f"{self.afternoon_login_start.strftime('%H:%M')} - {self.afternoon_login_end.strftime('%H:%M')}"
            info['logout_window'] = f"{self.afternoon_logout_start.strftime('%H:%M')} - {self.afternoon_logout_end.strftime('%H:%M')}"
        
        return info
    
    def should_allow_scan(
        self,
        student_id: str,
        last_scan_time: Optional[datetime],
        current_time: datetime = None
    ) -> Tuple[bool, str]:
        """
        Check if student scan should be allowed
        
        Args:
            student_id: Student ID
            last_scan_time: Time of last scan (None if first scan today)
            current_time: Current time (default: now)
            
        Returns:
            Tuple of (allow: bool, reason: str)
        """
        if current_time is None:
            current_time = datetime.now()
        
        # If no previous scan today, allow
        if last_scan_time is None:
            return (True, "First scan of the day")
        
        # Check cooldown period
        time_diff = (current_time - last_scan_time).total_seconds() / 60
        if time_diff < self.duplicate_cooldown_minutes:
            return (False, f"Duplicate scan (wait {int(self.duplicate_cooldown_minutes - time_diff)} min)")
        
        # Check if in different session
        current_session = self.get_current_session(current_time)
        last_session = self.get_current_session(last_scan_time)
        
        if current_session != last_session:
            return (True, f"Different session ({current_session.value})")
        
        # Same session - check scan type
        current_scan_type, _ = self.get_expected_scan_type(current_time)
        last_scan_type, _ = self.get_expected_scan_type(last_scan_time)
        
        if current_scan_type != last_scan_type:
            return (True, f"Different scan type ({current_scan_type.value})")
        
        # Same session, same scan type - not allowed
        return (False, f"Already scanned for {current_scan_type.value}")
