"""
Cloud Sync Manager
Handles synchronization of attendance data to Supabase cloud backend
Uses REST API for compatibility across all Supabase versions
"""

import logging
import asyncio
import os
from datetime import datetime
from typing import Dict, List, Optional
import json
import requests

logger = logging.getLogger(__name__)

class CloudSyncManager:
    """Manages cloud synchronization operations"""
    
    def __init__(self, config: Dict, sync_queue_manager, connectivity_monitor):
        """
        Initialize cloud sync manager
        
        Args:
            config: Cloud configuration dictionary
            sync_queue_manager: SyncQueueManager instance
            connectivity_monitor: ConnectivityMonitor instance
        """
        self.config = config
        self.enabled = config.get('enabled', False)
        self.sync_queue = sync_queue_manager
        self.connectivity = connectivity_monitor
        
        self.supabase_url = config.get('url')
        self.supabase_key = config.get('api_key')
        self.device_id = config.get('device_id', 'unknown')
        
        self.sync_interval = config.get('sync_interval', 60)
        self.sync_on_capture = config.get('sync_on_capture', True)
        self.retry_attempts = config.get('retry_attempts', 3)
        self.retry_delay = config.get('retry_delay', 30)
        
        self.client = None
        self._sync_count = 0
        
        if self.enabled:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Supabase REST API client"""
        if not self.supabase_url or not self.supabase_key:
            logger.warning("Supabase credentials not configured - cloud sync disabled")
            self.enabled = False
            return
        
        try:
            # Test connection with REST API
            url = f"{self.supabase_url}/rest/v1/attendance"
            headers = {
                'apikey': self.supabase_key,
                'Authorization': f'Bearer {self.supabase_key}'
            }
            response = requests.get(url, headers=headers, params={'limit': 1}, timeout=5)
            
            if response.status_code == 200:
                self.client = True  # Mark as initialized
                logger.info(f"Cloud sync initialized via REST API (Device: {self.device_id})")
            else:
                raise Exception(f"API test failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to initialize Supabase REST API: {e}")
            self.enabled = False
    
    def _insert_to_cloud(self, cloud_data: Dict) -> Optional[str]:
        """
        Insert attendance record to cloud using REST API
        
        Args:
            cloud_data: Attendance data to insert
            
        Returns:
            Cloud record ID if successful, None otherwise
        """
        try:
            url = f"{self.supabase_url}/rest/v1/attendance"
            headers = {
                'apikey': self.supabase_key,
                'Authorization': f'Bearer {self.supabase_key}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            }
            
            response = requests.post(url, headers=headers, json=cloud_data, timeout=10)
            
            if response.status_code in [200, 201]:
                data = response.json()
                cloud_id = data[0]['id'] if isinstance(data, list) else data.get('id')
                return str(cloud_id)
            else:
                logger.error(f"Cloud insert failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Cloud insert error: {e}")
            return None
    
    def sync_attendance_record(self, attendance_data: Dict, photo_path: str = None) -> bool:
        """
        Sync a single attendance record to cloud
        
        Args:
            attendance_data: Attendance record dictionary
            photo_path: Optional path to photo file
        
        Returns:
            True if sync successful, False otherwise
        """
        if not self.enabled or not self.client:
            # Add to queue for later sync
            self.sync_queue.add_to_queue(
                'attendance',
                attendance_data.get('id'),
                {'attendance': attendance_data, 'photo_path': photo_path}
            )
            logger.debug(f"Cloud sync disabled - queued attendance ID {attendance_data.get('id')}")
            return False
        
        # Check connectivity
        if not self.connectivity.is_online():
            # Queue for later
            self.sync_queue.add_to_queue(
                'attendance',
                attendance_data.get('id'),
                {'attendance': attendance_data, 'photo_path': photo_path}
            )
            logger.debug(f"Offline - queued attendance ID {attendance_data.get('id')}")
            return False
        
        # Attempt sync
        try:
            # Upload photo first if provided
            photo_url = None
            if photo_path and os.path.exists(photo_path):
                from .photo_uploader import PhotoUploader
                uploader = PhotoUploader(self.supabase_url, self.supabase_key)
                photo_url = uploader.upload_photo(photo_path, attendance_data.get('student_id'))
            
            # Prepare attendance data for cloud
            cloud_data = {
                'student_id': attendance_data.get('student_id'),
                'timestamp': attendance_data.get('timestamp'),
                'photo_url': photo_url,
                'qr_data': attendance_data.get('qr_data'),
                'status': attendance_data.get('status', 'present'),
                'device_id': self.device_id
            }
            
            # Insert into cloud database using REST API
            cloud_record_id = self._insert_to_cloud(cloud_data)
            
            if cloud_record_id:
                # Mark as synced in local database
                self.sync_queue.mark_attendance_synced(
                    attendance_data.get('id'),
                    cloud_record_id
                )
                
                self._sync_count += 1
                logger.info(f"Synced attendance ID {attendance_data.get('id')} to cloud (cloud ID: {cloud_record_id})")
                return True
            else:
                raise Exception("Failed to insert to cloud")
        
        except Exception as e:
            logger.error(f"Failed to sync attendance: {e}")
            # Add to queue for retry
            self.sync_queue.add_to_queue(
                'attendance',
                attendance_data.get('id'),
                {'attendance': attendance_data, 'photo_path': photo_path}
            )
            return False
    
    def process_sync_queue(self, batch_size: int = 10) -> Dict:
        """
        Process pending records in sync queue
        
        Args:
            batch_size: Maximum number of records to process
        
        Returns:
            Dictionary with sync results:
                - processed: int
                - succeeded: int
                - failed: int
        """
        if not self.enabled or not self.client:
            return {'processed': 0, 'succeeded': 0, 'failed': 0}
        
        # Check connectivity
        if not self.connectivity.is_online():
            logger.debug("Offline - skipping queue processing")
            return {'processed': 0, 'succeeded': 0, 'failed': 0}
        
        # Get pending records
        pending = self.sync_queue.get_pending_records(limit=batch_size)
        
        if not pending:
            return {'processed': 0, 'succeeded': 0, 'failed': 0}
        
        logger.info(f"Processing {len(pending)} pending sync records")
        
        succeeded = 0
        failed = 0
        
        for record in pending:
            queue_id = record['id']
            record_type = record['record_type']
            data = record['data']
            retry_count = record['retry_count']
            
            # Skip if too many retries
            if retry_count >= self.retry_attempts:
                logger.warning(f"Queue record {queue_id} exceeded max retries - removing")
                self.sync_queue.remove_from_queue(queue_id)
                failed += 1
                continue
            
            try:
                if record_type == 'attendance':
                    attendance_data = data.get('attendance')
                    photo_path = data.get('photo_path')
                    
                    # Upload photo if exists
                    photo_url = None
                    if photo_path and os.path.exists(photo_path):
                        from .photo_uploader import PhotoUploader
                        uploader = PhotoUploader(self.supabase_url, self.supabase_key)
                        photo_url = uploader.upload_photo(photo_path, attendance_data.get('student_id'))
                    
                    # Sync attendance record
                    cloud_data = {
                        'student_id': attendance_data.get('student_id'),
                        'timestamp': attendance_data.get('timestamp'),
                        'photo_url': photo_url,
                        'qr_data': attendance_data.get('qr_data'),
                        'status': attendance_data.get('status', 'present'),
                        'device_id': self.device_id
                    }
                    
                    # Insert using REST API
                    cloud_record_id = self._insert_to_cloud(cloud_data)
                    
                    if cloud_record_id:
                        # Mark as synced
                        self.sync_queue.mark_attendance_synced(
                            attendance_data.get('id'),
                            cloud_record_id
                        )
                        
                        # Remove from queue
                        self.sync_queue.remove_from_queue(queue_id)
                        
                        succeeded += 1
                        self._sync_count += 1
                        logger.info(f"Synced queued record {queue_id} (attendance ID {attendance_data.get('id')})")
                    else:
                        raise Exception("Failed to insert to cloud")
                
                else:
                    logger.warning(f"Unknown record type: {record_type}")
                    self.sync_queue.remove_from_queue(queue_id)
                    failed += 1
            
            except Exception as e:
                logger.error(f"Failed to sync queue record {queue_id}: {e}")
                self.sync_queue.update_retry_count(queue_id, str(e))
                failed += 1
        
        # Update device status
        self.sync_queue.update_device_status(self.device_id, self._sync_count)
        
        result = {
            'processed': len(pending),
            'succeeded': succeeded,
            'failed': failed
        }
        
        logger.info(f"Sync queue processed: {succeeded} succeeded, {failed} failed")
        
        return result
    
    def get_sync_status(self) -> Dict:
        """
        Get current sync status
        
        Returns:
            Dictionary with sync status information
        """
        device_status = self.sync_queue.get_device_status()
        queue_size = self.sync_queue.get_queue_size()
        unsynced = len(self.sync_queue.get_unsynced_attendance())
        connectivity_quality = self.connectivity.get_connection_quality()
        
        return {
            'enabled': self.enabled,
            'online': connectivity_quality.get('online', False),
            'device_id': self.device_id,
            'sync_count': self._sync_count,
            'queue_size': queue_size,
            'unsynced_records': unsynced,
            'last_sync': device_status.get('last_sync'),
            'latency_ms': connectivity_quality.get('latency_ms')
        }
    
    def force_sync_all(self) -> Dict:
        """
        Force synchronization of all unsynced records
        
        Returns:
            Sync results dictionary
        """
        if not self.enabled or not self.client:
            return {'processed': 0, 'succeeded': 0, 'failed': 0}
        
        # Wait for connection if offline
        if not self.connectivity.is_online():
            logger.info("Offline - waiting for connection...")
            if not self.connectivity.wait_for_connection(timeout=30):
                logger.error("Connection timeout - cannot sync")
                return {'processed': 0, 'succeeded': 0, 'failed': 0}
        
        # Get all unsynced records
        unsynced = self.sync_queue.get_unsynced_attendance()
        
        logger.info(f"Force syncing {len(unsynced)} unsynced records")
        
        succeeded = 0
        failed = 0
        
        for attendance_data in unsynced:
            try:
                # Upload photo if exists
                photo_path = attendance_data.get('photo_path')
                photo_url = None
                
                if photo_path and os.path.exists(photo_path):
                    from .photo_uploader import PhotoUploader
                    uploader = PhotoUploader(self.supabase_url, self.supabase_key)
                    photo_url = uploader.upload_photo(photo_path, attendance_data.get('student_id'))
                
                # Sync record
                cloud_data = {
                    'student_id': attendance_data.get('student_id'),
                    'timestamp': attendance_data.get('timestamp'),
                    'photo_url': photo_url,
                    'qr_data': attendance_data.get('qr_data'),
                    'status': attendance_data.get('status', 'present'),
                    'device_id': self.device_id
                }
                
                # Insert using REST API
                cloud_record_id = self._insert_to_cloud(cloud_data)
                
                if cloud_record_id:
                    self.sync_queue.mark_attendance_synced(attendance_data.get('id'), cloud_record_id)
                    succeeded += 1
                    self._sync_count += 1
                else:
                    raise Exception("Failed to insert to cloud")
            
            except Exception as e:
                logger.error(f"Failed to sync attendance ID {attendance_data.get('id')}: {e}")
                failed += 1
        
        # Update device status
        self.sync_queue.update_device_status(self.device_id, self._sync_count)
        
        result = {
            'processed': len(unsynced),
            'succeeded': succeeded,
            'failed': failed
        }
        
        logger.info(f"Force sync complete: {succeeded}/{len(unsynced)} succeeded")
        
        return result
