"""
Photo Uploader
Handles uploading photos to Supabase Storage using REST API
"""

import logging
import os
from datetime import datetime
from typing import Optional

import requests

from src.utils.network_timeouts import NetworkTimeouts, DEFAULT_TIMEOUTS

logger = logging.getLogger(__name__)


class PhotoUploader:
    """Uploads photos to cloud storage"""

    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        bucket_name: str = "attendance-photos",
        timeout_config: Optional[dict] = None,
    ):
        """
        Initialize photo uploader

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase API key
            bucket_name: Storage bucket name
            timeout_config: Network timeout configuration
        """
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.bucket_name = bucket_name
        self.storage_url = f"{supabase_url}/storage/v1"
        
        # Initialize timeouts
        self.timeouts = NetworkTimeouts(timeout_config or DEFAULT_TIMEOUTS)

        logger.debug("Photo uploader initialized with REST API")

    def _initialize_client(self):
        """Deprecated - using REST API instead"""
        pass

    def upload_photo(self, local_path: str, student_id: str) -> Optional[str]:
        """
        Upload photo to cloud storage using REST API

        Args:
            local_path: Path to local photo file
            student_id: Student ID for organizing photos

        Returns:
            Public URL of uploaded photo, or None on failure
        """
        if not os.path.exists(local_path):
            logger.error(f"Photo file not found: {local_path}")
            return None

        try:
            # Generate cloud path
            filename = os.path.basename(local_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            cloud_path = f"{student_id}/{timestamp}_{filename}"

            # Read file
            try:
                with open(local_path, "rb") as f:
                    file_data = f.read()
            except FileNotFoundError:
                logger.error(f"Photo file not found: {local_path}")
                return None
            except PermissionError:
                logger.error(f"Permission denied reading photo: {local_path}")
                return None
            except Exception as e:
                logger.error(f"Error reading photo file: {e}")
                return None

            # Upload using REST API
            upload_url = f"{self.storage_url}/object/{self.bucket_name}/{cloud_path}"
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "image/jpeg",
            }

            response = requests.post(
                upload_url, headers=headers, data=file_data, timeout=self.timeouts.get_storage_timeout()
            )

            if response.status_code in [200, 201]:
                # Generate public URL
                public_url = (
                    f"{self.storage_url}/object/public/{self.bucket_name}/{cloud_path}"
                )
                logger.info(f"Photo uploaded: {cloud_path}")
                return public_url
            else:
                logger.error(f"Upload failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Failed to upload photo: {e}")
            return None

    def delete_photo(self, cloud_path: str) -> bool:
        """
        Delete photo from cloud storage using REST API

        Args:
            cloud_path: Path to photo in cloud storage

        Returns:
            True if successful, False otherwise
        """
        try:
            delete_url = f"{self.storage_url}/object/{self.bucket_name}/{cloud_path}"
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
            }

            response = requests.delete(delete_url, headers=headers, timeout=10)

            if response.status_code in [200, 204]:
                logger.info(f"Photo deleted: {cloud_path}")
                return True
            else:
                logger.error(f"Delete failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete photo: {e}")
            return False

    def list_photos(self, student_id: str = None) -> list:
        """
        List photos in storage using REST API

        Args:
            student_id: Optional student ID to filter by

        Returns:
            List of photo paths
        """
        try:
            path = student_id if student_id else ""
            list_url = f"{self.storage_url}/object/list/{self.bucket_name}"
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "application/json",
            }

            payload = {"prefix": path} if path else {}
            response = requests.post(
                list_url, headers=headers, json=payload, timeout=self.timeouts.get_supabase_timeout()
            )

            if response.status_code == 200:
                try:
                    files = response.json()
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON response from photo list: {response.text[:200]}")
                    return []
                    
                return [f["name"] for f in files if "name" in f]
            else:
                logger.error(f"List failed: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Failed to list photos: {e}")
            return []
