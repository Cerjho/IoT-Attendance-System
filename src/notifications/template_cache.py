"""
SMS Template Cache Module

Provides local caching of SMS templates from Supabase with:
- Automatic refresh on system start
- Fallback to cache when server unavailable
- Cache expiry management (24 hours)
- SQLite-based persistence
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from pathlib import Path

from src.utils.logging_factory import get_logger
from src.utils.log_decorators import log_execution_time
from src.utils.audit_logger import get_business_logger

logger = get_logger(__name__)
business_logger = get_business_logger()


class TemplateCache:
    """
    Manages local caching of SMS templates from Supabase.
    
    Provides reliable template access even when offline by:
    - Fetching templates from Supabase on startup
    - Storing templates in local SQLite database
    - Serving cached templates when server unavailable
    - Auto-expiring stale cache (24 hours)
    """
    
    # Default templates as ultimate fallback
    DEFAULT_TEMPLATES = {
        'check_in': "Good day! Your child {{student_name}} ({{student_number}}) has checked in at {{time}}. - {{school_name}}",
        'check_out': "Good day! Your child {{student_name}} ({{student_number}}) has checked out at {{time}}. - {{school_name}}",
        'late_arrival': "LATE ARRIVAL: {{student_name}} ({{student_number}}) arrived at {{time}}, {{minutes_late}} minutes late. - {{school_name}}",
        'early_departure': "EARLY DEPARTURE: {{student_name}} ({{student_number}}) left at {{time}}, before scheduled time. - {{school_name}}",
        'absence_detected': "ABSENCE ALERT: {{student_name}} ({{student_number}}) has not checked in today ({{date}}). Please verify. - {{school_name}}",
        'schedule_violation': "SCHEDULE VIOLATION: {{student_name}} ({{student_number}}) scanned during wrong session. Expected: {{expected_session}}, Attempted: {{attempted_session}}. - {{school_name}}",
        'multiple_scans': "MULTIPLE SCANS: {{student_name}} ({{student_number}}) scanned multiple times today. Last scan: {{time}}. - {{school_name}}",
        'system_alert': "SYSTEM ALERT: {{alert_message}} - {{school_name}}"
    }
    
    def __init__(self, db_path: str = "data/attendance.db", cache_expiry_hours: int = 24):
        """
        Initialize template cache.
        
        Args:
            db_path: Path to SQLite database
            cache_expiry_hours: Hours before cache is considered stale
        """
        self.db_path = db_path
        self.cache_expiry_hours = cache_expiry_hours
        self._ensure_cache_table()
        logger.info(f"Template cache initialized (expiry: {cache_expiry_hours}h)")
    
    def _ensure_cache_table(self):
        """Create template_cache table if it doesn't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS template_cache (
                    template_type TEXT PRIMARY KEY,
                    template_name TEXT NOT NULL,
                    message_template TEXT NOT NULL,
                    variables TEXT,
                    is_active INTEGER DEFAULT 1,
                    cached_at TEXT NOT NULL,
                    server_updated_at TEXT
                )
            """)
            
            conn.commit()
            conn.close()
            logger.debug("Template cache table verified")
            
        except Exception as e:
            logger.error(f"Failed to create template cache table: {e}")
    
    def update_cache(self, templates: List[Dict]) -> int:
        """
        Update cache with templates from Supabase.
        
        Args:
            templates: List of template dictionaries from Supabase
        
        Returns:
            Number of templates cached
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cached_count = 0
            cached_at = datetime.now().isoformat()
            
            for template in templates:
                cursor.execute("""
                    INSERT OR REPLACE INTO template_cache 
                    (template_type, template_name, message_template, variables, 
                     is_active, cached_at, server_updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    template.get('template_type'),
                    template.get('template_name', ''),
                    template.get('message_template', ''),
                    json.dumps(template.get('variables', [])),
                    1 if template.get('is_active', True) else 0,
                    cached_at,
                    template.get('updated_at')
                ))
                cached_count += 1
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated cache with {cached_count} templates")
            return cached_count
            
        except Exception as e:
            logger.error(f"Failed to update template cache: {e}")
            return 0
    
    def get_template(self, template_type: str) -> Optional[Dict]:
        """
        Get template from cache.
        
        Args:
            template_type: Type of template to retrieve
        
        Returns:
            Template dictionary or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT template_type, template_name, message_template, 
                       variables, is_active, cached_at, server_updated_at
                FROM template_cache
                WHERE template_type = ? AND is_active = 1
            """, (template_type,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                template = dict(row)
                template['variables'] = json.loads(template.get('variables', '[]'))
                
                # Check if cache is stale
                cached_at = datetime.fromisoformat(template['cached_at'])
                age_hours = (datetime.now() - cached_at).total_seconds() / 3600
                
                if age_hours > self.cache_expiry_hours:
                    logger.warning(f"Template '{template_type}' cache is stale ({age_hours:.1f}h old)")
                
                return template
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get template from cache: {e}")
            return None
    
    def get_template_text(self, template_type: str) -> str:
        """
        Get template message text only.
        
        Args:
            template_type: Type of template to retrieve
        
        Returns:
            Template message text, or default if not found
        """
        template = self.get_template(template_type)
        
        if template:
            return template.get('message_template', '')
        
        # Fallback to default template
        default = self.DEFAULT_TEMPLATES.get(template_type)
        if default:
            logger.debug(f"Using default template for '{template_type}'")
            return default
        
        logger.error(f"No template found for '{template_type}'")
        return "Notification: {{student_name}} ({{student_number}}) - {{school_name}}"
    
    def get_all_templates(self) -> List[Dict]:
        """
        Get all cached templates.
        
        Returns:
            List of all templates in cache
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT template_type, template_name, message_template, 
                       variables, is_active, cached_at, server_updated_at
                FROM template_cache
                ORDER BY template_type
            """)
            
            templates = []
            for row in cursor.fetchall():
                template = dict(row)
                template['variables'] = json.loads(template.get('variables', '[]'))
                templates.append(template)
            
            conn.close()
            return templates
            
        except Exception as e:
            logger.error(f"Failed to get all templates: {e}")
            return []
    
    def is_cache_stale(self) -> bool:
        """
        Check if cache is stale and needs refresh.
        
        Returns:
            True if cache is older than expiry time
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT MIN(cached_at) as oldest FROM template_cache")
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0]:
                oldest = datetime.fromisoformat(row[0])
                age_hours = (datetime.now() - oldest).total_seconds() / 3600
                return age_hours > self.cache_expiry_hours
            
            # No cache = stale
            return True
            
        except Exception as e:
            logger.error(f"Failed to check cache staleness: {e}")
            return True
    
    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Count total templates
            cursor.execute("SELECT COUNT(*) FROM template_cache")
            total = cursor.fetchone()[0]
            
            # Count active templates
            cursor.execute("SELECT COUNT(*) FROM template_cache WHERE is_active = 1")
            active = cursor.fetchone()[0]
            
            # Get oldest cache time
            cursor.execute("SELECT MIN(cached_at) FROM template_cache")
            oldest = cursor.fetchone()[0]
            
            # Get newest cache time
            cursor.execute("SELECT MAX(cached_at) FROM template_cache")
            newest = cursor.fetchone()[0]
            
            conn.close()
            
            stats = {
                'total_templates': total,
                'active_templates': active,
                'inactive_templates': total - active,
                'oldest_cache': oldest,
                'newest_cache': newest,
                'is_stale': self.is_cache_stale()
            }
            
            if oldest:
                oldest_dt = datetime.fromisoformat(oldest)
                age_hours = (datetime.now() - oldest_dt).total_seconds() / 3600
                stats['cache_age_hours'] = round(age_hours, 1)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}
    
    def clear_cache(self) -> bool:
        """
        Clear all cached templates.
        
        Returns:
            True if successful
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM template_cache")
            deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            logger.info(f"Cleared {deleted} templates from cache")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
    
    def populate_with_defaults(self) -> int:
        """
        Populate cache with default templates (emergency fallback).
        
        Returns:
            Number of templates added
        """
        templates = []
        for template_type, message in self.DEFAULT_TEMPLATES.items():
            templates.append({
                'template_type': template_type,
                'template_name': template_type.replace('_', ' ').title(),
                'message_template': message,
                'variables': ['student_name', 'student_number', 'school_name'],
                'is_active': True
            })
        
        return self.update_cache(templates)


# Module-level convenience functions
_cache_instance = None


def get_cache_instance(db_path: str = "data/attendance.db") -> TemplateCache:
    """Get or create global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = TemplateCache(db_path)
    return _cache_instance


def get_template(template_type: str, db_path: str = "data/attendance.db") -> str:
    """
    Convenience function to get template text.
    
    Args:
        template_type: Type of template
        db_path: Database path
    
    Returns:
        Template message text
    """
    cache = get_cache_instance(db_path)
    return cache.get_template_text(template_type)
