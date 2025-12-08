"""
Cloud Sync Manager
Handles synchronization of attendance data to Supabase cloud backend
Uses REST API for compatibility across all Supabase versions
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

import requests

from src.network.connectivity import ConnectivityMonitor
from src.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from src.utils.network_timeouts import NetworkTimeouts, DEFAULT_TIMEOUTS

logger = logging.getLogger(__name__)


class CloudSyncManager:
    """Manages cloud synchronization operations"""

    def __init__(self, config: Dict, *args):
        """
        Initialize cloud sync manager

        Supports both current and legacy constructor signatures:
        - Current: CloudSyncManager(config, sync_queue_manager, connectivity_monitor)
        - Legacy (used in tests): CloudSyncManager(config, db, sync_queue_manager)
        """
        self.config = config
        self.enabled = config.get("enabled", False)
        self.sync_queue = None
        self.connectivity = None

        # Resolve arguments for compatibility
        if len(args) >= 2:
            a1, a2 = args[0], args[1]

            # Heuristic: identify sync_queue by expected methods
            def is_sync_queue(obj):
                return all(
                    hasattr(obj, m)
                    for m in [
                        "get_queue_size",
                        "get_unsynced_attendance",
                        "add_to_queue",
                    ]
                )

            if is_sync_queue(a1):
                # Signature: (config, sync_queue, connectivity?)
                self.sync_queue = a1
                self.connectivity = a2 if hasattr(a2, "is_online") else None
            elif is_sync_queue(a2):
                # Legacy signature: (config, db, sync_queue)
                self.sync_queue = a2
                # No connectivity provided in legacy path
                self.connectivity = None
            else:
                # Fallback: assume first is sync_queue
                self.sync_queue = a1
                self.connectivity = a2 if hasattr(a2, "is_online") else None
        elif len(args) == 1:
            # Single extra arg, assume it's sync_queue
            self.sync_queue = args[0]

        # Provide a default connectivity monitor if missing
        if self.connectivity is None:
            self.connectivity = ConnectivityMonitor(self.config)

        self.supabase_url = config.get("url")
        self.supabase_key = config.get("api_key")
        self.device_id = config.get("device_id", "unknown")

        self.sync_interval = config.get("sync_interval", 60)
        self.sync_on_capture = config.get("sync_on_capture", True)
        self.retry_attempts = config.get("retry_attempts", 3)
        self.retry_delay = config.get("retry_delay", 30)

        self.client = None
        self._sync_count = 0

        # Initialize network timeouts
        timeout_config = config.get("network_timeouts", DEFAULT_TIMEOUTS)
        self.timeouts = NetworkTimeouts(timeout_config)

        # Initialize circuit breakers
        self.circuit_breaker_students = CircuitBreaker(
            name="supabase_students",
            failure_threshold=config.get("circuit_breaker_threshold", 5),
            timeout_seconds=config.get("circuit_breaker_timeout", 60),
            success_threshold=config.get("circuit_breaker_success", 2),
        )
        self.circuit_breaker_attendance = CircuitBreaker(
            name="supabase_attendance",
            failure_threshold=config.get("circuit_breaker_threshold", 5),
            timeout_seconds=config.get("circuit_breaker_timeout", 60),
            success_threshold=config.get("circuit_breaker_success", 2),
        )

        # Validate environment variables are loaded (not placeholders)
        if self.enabled:
            self._validate_credentials()
            self._initialize_client()

    def _validate_credentials(self):
        """Validate that environment variables are properly loaded"""
        if self.supabase_url and self.supabase_url.startswith("${"):
            raise ValueError(
                f"Environment variable not loaded for Supabase URL: {self.supabase_url}"
            )
        if self.supabase_key and self.supabase_key.startswith("${"):
            raise ValueError(f"Environment variable not loaded for Supabase API key")
        if self.device_id and self.device_id.startswith("${"):
            raise ValueError(
                f"Environment variable not loaded for device_id: {self.device_id}"
            )

    def _get_retry_delay(self, attempt: int) -> int:
        """Calculate exponential backoff delay"""
        # Exponential backoff: 30s, 60s, 120s, capped at 300s (5 minutes)
        delay = min(self.retry_delay * (2**attempt), 300)
        logger.debug(f"Retry attempt {attempt + 1}: waiting {delay}s")
        return delay

    def _initialize_client(self):
        """Initialize Supabase REST API client"""
        if not self.supabase_url or not self.supabase_key:
            logger.warning("Supabase credentials not configured - cloud sync disabled")
            self.enabled = False
            return

        # Additional validation for placeholder values
        if self.supabase_url.startswith("${") or self.supabase_key.startswith("${"):
            logger.error(
                "Environment variables not properly loaded - using placeholder values"
            )
            self.enabled = False
            return

        try:
            # Test connection with REST API
            url = f"{self.supabase_url}/rest/v1/attendance"
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
            }
            response = requests.get(
                url, headers=headers, params={"limit": 1}, timeout=self.timeouts.get_supabase_timeout()
            )

            if response.status_code == 200:
                self.client = True  # Mark as initialized
                logger.info(
                    f"Cloud sync initialized via REST API (Device: {self.device_id})"
                )
            else:
                raise Exception(f"API test failed: {response.status_code}")

        except requests.exceptions.SSLError as e:
            logger.error(f"SSL certificate error connecting to Supabase: {e}")
            logger.warning("Consider checking SSL certificates or setting verify=False for self-signed certs")
            self.enabled = False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection refused by Supabase (service may be down): {e}")
            logger.info("Will retry when network connectivity is restored")
            self.enabled = False
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout connecting to Supabase: {e}")
            logger.info("Network may be slow or Supabase endpoint unreachable")
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize Supabase REST API: {e}")
            self.enabled = False

    def _insert_to_cloud(self, cloud_data: Dict) -> Optional[str]:
        """
        Insert attendance record to cloud using REST API (NEW SCHEMA)

        New attendance table schema:
        - student_id: UUID (foreign key to students.id)
        - date: DATE
        - time_in: TIME
        - status: VARCHAR (present/late/absent/excused)
        - device_id: VARCHAR
        - remarks: TEXT (optional)

        Args:
            cloud_data: Attendance data to insert (must include student_number)

        Returns:
            Cloud record ID if successful, None otherwise
        """
        try:
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            }

            # Step 1: Get student UUID from student_number
            student_number = cloud_data.get("student_number")
            if not student_number:
                logger.error("Missing student_number in cloud_data")
                return None

            logger.debug(f"☁️ Looking up student UUID: student_number={student_number}")
            student_url = f"{self.supabase_url}/rest/v1/students?student_number=eq.{student_number}&select=id"
            
            # Student lookup with circuit breaker
            try:
                student_response = self.circuit_breaker_students.call(
                    requests.get, student_url, headers=headers, timeout=self.timeouts.get_supabase_timeout()
                )
            except CircuitBreakerOpen:
                logger.error(f"Circuit breaker OPEN for students endpoint (student: {student_number})")
                return None
            except requests.exceptions.SSLError as e:
                logger.error(f"SSL error during student lookup for {student_number}: {e}")
                return None
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error during student lookup for {student_number}: {e}")
                logger.debug("Supabase may be unreachable, record will be queued for retry")
                return None
            except requests.exceptions.Timeout as e:
                logger.error(f"Timeout during student lookup for {student_number}: {e}")
                return None
            except Exception as e:
                logger.error(f"Student lookup failed for {student_number}: {e}")
                return None

            if student_response.status_code != 200:
                logger.error(
                    f"Failed to lookup student UUID: {student_response.status_code}"
                )
                return None

            try:
                students = student_response.json()
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response from Supabase students endpoint: {student_response.text[:200]}")
                return None
                
            if not students or len(students) == 0:
                logger.error(f"Student not found in Supabase: {student_number}")
                return None

            student_uuid = students[0]["id"]

            # Step 2: Prepare attendance data for Supabase
            # Note: IoT device only sends core data. Backend/triggers determine:
            # - section_id (from iot_devices.section_id via device_id)
            # - subject_id and teaching_load_id (from schedule + time + section)
            attendance_url = f"{self.supabase_url}/rest/v1/attendance"
            attendance_data = {
                "student_id": student_uuid,  # UUID from students table
                "date": cloud_data.get("date"),  # DATE field
                "status": cloud_data.get("status", "present"),
                "device_id": self.device_id,  # Backend looks up section_id from iot_devices
                "remarks": f"QR: {cloud_data.get('qr_data', 'N/A')}",
            }
            
            # Add photo_url as separate field (not just in remarks)
            photo_url = cloud_data.get("photo_url")
            if photo_url:
                attendance_data["photo_url"] = photo_url
                logger.debug(f"Photo URL added to attendance: {photo_url}")
            
            # Add recorded_by if device operator is configured
            recorded_by = self.config.get("recorded_by_teacher_uuid")
            if recorded_by:
                attendance_data["recorded_by"] = recorded_by
                logger.debug(f"Recorded by teacher UUID: {recorded_by}")

            # Add time_in or time_out based on scan type
            if cloud_data.get("time_in"):
                attendance_data["time_in"] = cloud_data.get("time_in")
            if cloud_data.get("time_out"):
                attendance_data["time_out"] = cloud_data.get("time_out")

            # Step 4: Insert attendance record with circuit breaker
            try:
                response = self.circuit_breaker_attendance.call(
                    requests.post, attendance_url, headers=headers, json=attendance_data, timeout=self.timeouts.get_supabase_timeout()
                )
            except CircuitBreakerOpen:
                logger.error("Circuit breaker OPEN for attendance endpoint")
                return None
            except Exception as e:
                logger.error(f"Attendance insert failed: {e}")
                return None

            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON response from attendance endpoint: {response.text[:200]}")
                    return None
                    
                cloud_id = data[0]["id"] if isinstance(data, list) else data.get("id")
                scan_type = cloud_data.get("time_in") and "login" or "logout"
                logger.info(
                    f"✅ Attendance Persisted: student={student_number}→{student_uuid}, cloud_id={cloud_id}, date={cloud_data.get('date')}, type={scan_type}"
                )
                return str(cloud_id)
            else:
                logger.error(
                    f"❌ Cloud insert failed: status={response.status_code}, body={response.text[:200]}"
                )
                return None

        except Exception as e:
            logger.error(f"Cloud insert error: {e}")
            return None

    def sync_attendance_record(
        self, attendance_data: Dict, photo_path: str = None
    ) -> bool:
        """
        Sync a single attendance record to cloud

        Args:
            attendance_data: Attendance record dictionary
            photo_path: Optional path to photo file

        Returns:
            True if sync successful, False otherwise
        """
        student_id = attendance_data.get("student_id")
        local_id = attendance_data.get("id")
        logger.info(f"☁️ Cloud Sync Started: local_id={local_id}, student={student_id}, has_photo={photo_path is not None}")
        
        if not self.enabled or not self.client:
            # Add to queue for later sync
            self.sync_queue.add_to_queue(
                "attendance",
                attendance_data.get("id"),
                {"attendance": attendance_data, "photo_path": photo_path},
            )
            logger.info(
                f"📥 Cloud Sync Queued (disabled): local_id={local_id}, student={student_id}"
            )
            return False

        # Check connectivity
        if not self.connectivity.is_online():
            # Queue for later
            self.sync_queue.add_to_queue(
                "attendance",
                attendance_data.get("id"),
                {"attendance": attendance_data, "photo_path": photo_path},
            )
            logger.info(f"📥 Cloud Sync Queued (offline): local_id={local_id}, student={student_id}")
            return False

        # Attempt sync
        try:
            # Upload photo first if provided
            photo_url = None
            if photo_path and os.path.exists(photo_path):
                logger.debug(f"☁️ Uploading photo: {photo_path}")
                from .photo_uploader import PhotoUploader

                uploader = PhotoUploader(self.supabase_url, self.supabase_key)
                photo_url = uploader.upload_photo(
                    photo_path, attendance_data.get("student_id")
                )
                if photo_url:
                    logger.info(f"✅ Photo uploaded: {photo_url}")
                else:
                    logger.warning(f"⚠️ Photo upload failed: {photo_path}")

            # Prepare attendance data for cloud (new schema)
            # Parse timestamp into date and time components
            timestamp = attendance_data.get("timestamp", datetime.now().isoformat())
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

            cloud_data = {
                "student_number": attendance_data.get(
                    "student_id"
                ),  # student_id is actually student_number in local cache
                "date": dt.date().isoformat(),
                "status": attendance_data.get("status", "present"),
                "qr_data": attendance_data.get("qr_data"),
                "photo_url": photo_url,  # Pass photo_url separately
                "remarks": f"Photo: {photo_url}" if photo_url else None,
            }

            # Add time_in or time_out based on scan type
            scan_type = attendance_data.get("scan_type", "time_in")
            if scan_type == "time_out":
                cloud_data["time_out"] = dt.time().isoformat()
            else:
                cloud_data["time_in"] = dt.time().isoformat()

            # Insert into cloud database using REST API
            cloud_record_id = self._insert_to_cloud(cloud_data)

            if cloud_record_id:
                # Mark as synced in local database
                self.sync_queue.mark_attendance_synced(
                    attendance_data.get("id"), cloud_record_id
                )

                # Optionally delete local photo after successful sync
                try:
                    if (
                        self.config.get("cleanup_photos_after_sync", True)
                        and photo_path
                        and os.path.exists(photo_path)
                    ):
                        os.remove(photo_path)
                        logger.debug(f"🗑️ Deleted local photo after sync: {photo_path}")
                except Exception as _e:
                    logger.warning(f"Failed to delete local photo {photo_path}: {_e}")

                self._sync_count += 1
                logger.info(
                    f"✅ Cloud Sync Success: local_id={attendance_data.get('id')}, cloud_id={cloud_record_id}, student={student_id}, photo={photo_url is not None}"
                )
                return True
            else:
                raise Exception("Failed to insert to cloud")

        except Exception as e:
            logger.error(f"❌ Cloud Sync Failed: local_id={local_id}, student={student_id}, error={str(e)[:100]}")
            # Add to queue for retry
            self.sync_queue.add_to_queue(
                "attendance",
                attendance_data.get("id"),
                {"attendance": attendance_data, "photo_path": photo_path},
            )
            logger.info(f"📥 Cloud Sync Queued (retry): local_id={local_id}")
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
            return {"processed": 0, "succeeded": 0, "failed": 0}

        # Check connectivity
        if not self.connectivity.is_online():
            logger.debug("Offline - skipping queue processing")
            return {"processed": 0, "succeeded": 0, "failed": 0}

        # Get pending records
        pending = self.sync_queue.get_pending_records(limit=batch_size)

        if not pending:
            return {"processed": 0, "succeeded": 0, "failed": 0}

        logger.info(f"📤 Processing sync queue: {len(pending)} pending records, batch_size={batch_size}")

        succeeded = 0
        failed = 0

        for record in pending:
            queue_id = record["id"]
            record_type = record["record_type"]
            data = record["data"]
            retry_count = record["retry_count"]

            # Skip if too many retries
            if retry_count >= self.retry_attempts:
                logger.warning(
                    f"Queue record {queue_id} exceeded max retries - removing"
                )
                self.sync_queue.remove_from_queue(queue_id)
                failed += 1
                continue

            try:
                if record_type == "attendance":
                    attendance_data = data.get("attendance")
                    photo_path = data.get("photo_path")

                    # Upload photo if exists
                    photo_url = None
                    if photo_path and os.path.exists(photo_path):
                        from .photo_uploader import PhotoUploader

                        uploader = PhotoUploader(self.supabase_url, self.supabase_key)
                        photo_url = uploader.upload_photo(
                            photo_path, attendance_data.get("student_id")
                        )

                    # Sync attendance record (new schema)
                    # Parse timestamp into date and time components
                    timestamp = attendance_data.get(
                        "timestamp", datetime.now().isoformat()
                    )
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

                    cloud_data = {
                        "student_number": attendance_data.get(
                            "student_id"
                        ),  # student_id is actually student_number
                        "date": dt.date().isoformat(),
                        "status": attendance_data.get("status", "present"),
                        "qr_data": attendance_data.get("qr_data"),
                        "photo_url": photo_url,  # Pass photo_url separately
                        "remarks": f"Photo: {photo_url}" if photo_url else None,
                    }

                    # Add time_in or time_out based on scan type
                    scan_type = attendance_data.get("scan_type", "time_in")
                    if scan_type == "time_out":
                        cloud_data["time_out"] = dt.time().isoformat()
                    else:
                        cloud_data["time_in"] = dt.time().isoformat()

                    # Insert using REST API
                    cloud_record_id = self._insert_to_cloud(cloud_data)

                    if cloud_record_id:
                        # Mark as synced
                        self.sync_queue.mark_attendance_synced(
                            attendance_data.get("id"), cloud_record_id
                        )

                        # Remove from queue
                        self.sync_queue.remove_from_queue(queue_id)

                        # Optionally delete local photo after successful sync
                        try:
                            if (
                                self.config.get("cleanup_photos_after_sync", True)
                                and photo_path
                                and os.path.exists(photo_path)
                            ):
                                os.remove(photo_path)
                                logger.debug(
                                    f"Deleted local photo after sync: {photo_path}"
                                )
                        except Exception as _e:
                            logger.warning(
                                f"Failed to delete local photo {photo_path}: {_e}"
                            )

                        succeeded += 1
                        self._sync_count += 1
                        logger.info(
                            f"✅ Queue sync success: queue_id={queue_id}, local_id={attendance_data.get('id')}, cloud_id={cloud_record_id}, student={attendance_data.get('student_id')}"
                        )
                    else:
                        raise Exception("Failed to insert to cloud")

                else:
                    logger.warning(f"Unknown record type: {record_type}")
                    self.sync_queue.remove_from_queue(queue_id)
                    failed += 1

            except Exception as e:
                logger.error(f"❌ Queue sync failed: queue_id={queue_id}, retry={retry_count+1}/{self.retry_attempts}, error={str(e)[:100]}")
                self.sync_queue.update_retry_count(queue_id, str(e))
                failed += 1

        # Update device status
        self.sync_queue.update_device_status(self.device_id, self._sync_count)

        result = {"processed": len(pending), "succeeded": succeeded, "failed": failed}

        logger.info(f"📊 Sync queue complete: processed={len(pending)}, succeeded={succeeded}, failed={failed}, total_synced={self._sync_count}")

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
            "enabled": self.enabled,
            "online": connectivity_quality.get("online", False),
            "device_id": self.device_id,
            "sync_count": self._sync_count,
            "queue_size": queue_size,
            "unsynced_records": unsynced,
            "last_sync": device_status.get("last_sync"),
            "latency_ms": connectivity_quality.get("latency_ms"),
        }

    def force_sync_all(self) -> Dict:
        """
        Force synchronization of all unsynced records

        Returns:
            Sync results dictionary
        """
        if not self.enabled or not self.client:
            return {"processed": 0, "succeeded": 0, "failed": 0}

        # Wait for connection if offline
        if not self.connectivity.is_online():
            logger.info("Offline - waiting for connection...")
            if not self.connectivity.wait_for_connection(timeout=30):
                logger.error("Connection timeout - cannot sync")
                return {"processed": 0, "succeeded": 0, "failed": 0}

        # Get all unsynced records
        unsynced = self.sync_queue.get_unsynced_attendance()

        logger.info(f"Force syncing {len(unsynced)} unsynced records")

        succeeded = 0
        failed = 0

        for attendance_data in unsynced:
            try:
                # Upload photo if exists
                photo_path = attendance_data.get("photo_path")
                photo_url = None

                if photo_path and os.path.exists(photo_path):
                    from .photo_uploader import PhotoUploader

                    uploader = PhotoUploader(self.supabase_url, self.supabase_key)
                    photo_url = uploader.upload_photo(
                        photo_path, attendance_data.get("student_id")
                    )

                # Sync record (new schema)
                # Parse timestamp into date and time components
                timestamp = attendance_data.get("timestamp", datetime.now().isoformat())
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

                cloud_data = {
                    "student_number": attendance_data.get(
                        "student_id"
                    ),  # student_id is actually student_number
                    "date": dt.date().isoformat(),
                    "status": attendance_data.get("status", "present"),
                    "qr_data": attendance_data.get("qr_data"),
                    "remarks": f"Photo: {photo_url}" if photo_url else None,
                }

                # Add time_in or time_out based on scan type
                scan_type = attendance_data.get("scan_type", "time_in")
                if scan_type == "time_out":
                    cloud_data["time_out"] = dt.time().isoformat()
                else:
                    cloud_data["time_in"] = dt.time().isoformat()

                # Insert using REST API
                cloud_record_id = self._insert_to_cloud(cloud_data)

                if cloud_record_id:
                    self.sync_queue.mark_attendance_synced(
                        attendance_data.get("id"), cloud_record_id
                    )
                    # Optionally delete local photo after successful sync
                    try:
                        if (
                            self.config.get("cleanup_photos_after_sync", True)
                            and photo_path
                            and os.path.exists(photo_path)
                        ):
                            os.remove(photo_path)
                            logger.debug(
                                f"Deleted local photo after sync: {photo_path}"
                            )
                    except Exception as _e:
                        logger.warning(
                            f"Failed to delete local photo {photo_path}: {_e}"
                        )
                    succeeded += 1
                    self._sync_count += 1
                else:
                    raise Exception("Failed to insert to cloud")

            except Exception as e:
                logger.error(
                    f"Failed to sync attendance ID {attendance_data.get('id')}: {e}"
                )
                failed += 1

        # Update device status
        self.sync_queue.update_device_status(self.device_id, self._sync_count)

        result = {"processed": len(unsynced), "succeeded": succeeded, "failed": failed}

        logger.info(f"Force sync complete: {succeeded}/{len(unsynced)} succeeded")

        return result
