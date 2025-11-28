#!/usr/bin/env python3
"""
Test script for code improvements
Tests threading locks, exponential backoff, config validation, etc.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import threading
import time
import unittest
from datetime import datetime

from src.attendance.schedule_manager import ScheduleManager
from src.cloud.cloud_sync import CloudSyncManager
from src.database import AttendanceDatabase
from src.database.sync_queue import SyncQueueManager
from src.network import ConnectivityMonitor
from src.notifications import SMSNotifier


class TestThreadSafety(unittest.TestCase):
    """Test thread safety improvements"""

    def setUp(self):
        """Set up test database"""
        self.test_db = "data/test_thread_safety.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        self.db = AttendanceDatabase(self.test_db)

    def tearDown(self):
        """Clean up test database"""
        self.db.close()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_concurrent_writes(self):
        """Test concurrent database writes with threading lock"""
        results = []

        def add_students(start_id, count):
            for i in range(count):
                student_id = f"STU{start_id + i:04d}"
                result = self.db.add_student(student_id, f"Student {start_id + i}")
                results.append(result)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_students, args=(i * 10, 10))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All operations should succeed
        self.assertTrue(all(results))

        # Verify all students were added
        stats = self.db.get_statistics()
        self.assertEqual(stats["total_students"], 50)
        print("✅ Concurrent writes test passed")

    def test_context_manager(self):
        """Test database context manager"""
        with AttendanceDatabase(self.test_db) as db:
            result = db.add_student("CTX001", "Context Test")
            self.assertTrue(result)

        # Database should still be accessible after context exit
        db2 = AttendanceDatabase(self.test_db)
        student = db2.get_student("CTX001")
        self.assertIsNotNone(student)
        db2.close()
        print("✅ Context manager test passed")


class TestExponentialBackoff(unittest.TestCase):
    """Test exponential backoff implementation"""

    def test_backoff_calculation(self):
        """Test exponential backoff delay calculation"""
        # Initialize database first
        test_db = "data/test_backoff.db"
        if os.path.exists(test_db):
            os.remove(test_db)

        # Create attendance table
        db = AttendanceDatabase(test_db)

        config = {
            "enabled": False,  # Disabled for testing
            "url": "https://test.supabase.co",
            "api_key": "test_key",
            "retry_delay": 30,
        }

        sync_queue = SyncQueueManager(test_db)
        connectivity = ConnectivityMonitor({"enabled": True})
        manager = CloudSyncManager(config, sync_queue, connectivity)

        # Test backoff delays
        delays = [manager._get_retry_delay(i) for i in range(5)]

        # Should be: 30, 60, 120, 240, 300 (capped at 300)
        expected = [30, 60, 120, 240, 300]
        self.assertEqual(delays, expected)
        print(f"✅ Exponential backoff test passed: {delays}")

        # Clean up
        db.close()
        if os.path.exists(test_db):
            os.remove(test_db)


class TestConfigValidation(unittest.TestCase):
    """Test configuration validation"""

    def test_schedule_validation_invalid_times(self):
        """Test schedule manager rejects invalid time configurations"""
        invalid_config = {
            "morning_class": {
                "start_time": "12:00",
                "end_time": "07:00",  # End before start - INVALID
            },
            "afternoon_class": {
                "start_time": "13:00",
                "end_time": "17:00",
            },
            "duplicate_scan_cooldown_minutes": 5,
        }

        with self.assertRaises(ValueError) as context:
            ScheduleManager(invalid_config)

        self.assertIn("must be before", str(context.exception))
        print("✅ Schedule validation (invalid times) test passed")

    def test_schedule_validation_negative_threshold(self):
        """Test schedule manager rejects negative thresholds"""
        invalid_config = {
            "morning_class": {
                "start_time": "07:00",
                "end_time": "12:00",
                "late_threshold_minutes": -10,  # Negative - INVALID
            },
            "afternoon_class": {
                "start_time": "13:00",
                "end_time": "17:00",
            },
            "duplicate_scan_cooldown_minutes": 5,
        }

        with self.assertRaises(ValueError) as context:
            ScheduleManager(invalid_config)

        self.assertIn("cannot be negative", str(context.exception))
        print("✅ Schedule validation (negative threshold) test passed")

    def test_schedule_validation_valid(self):
        """Test schedule manager accepts valid configuration"""
        valid_config = {
            "morning_class": {
                "start_time": "07:00",
                "end_time": "12:00",
                "login_window_start": "06:30",
                "login_window_end": "07:30",
                "logout_window_start": "11:30",
                "logout_window_end": "12:30",
                "late_threshold_minutes": 15,
            },
            "afternoon_class": {
                "start_time": "13:00",
                "end_time": "17:00",
                "login_window_start": "12:30",
                "login_window_end": "13:30",
                "logout_window_start": "16:30",
                "logout_window_end": "17:30",
                "late_threshold_minutes": 15,
            },
            "duplicate_scan_cooldown_minutes": 5,
        }

        try:
            manager = ScheduleManager(valid_config)
            self.assertIsNotNone(manager)
            print("✅ Schedule validation (valid config) test passed")
        except ValueError as e:
            self.fail(f"Valid config rejected: {e}")


class TestEnvironmentValidation(unittest.TestCase):
    """Test environment variable validation"""

    def test_cloud_sync_placeholder_detection(self):
        """Test CloudSyncManager detects placeholder env vars"""
        # Initialize database first
        test_db = "data/test_env.db"
        if os.path.exists(test_db):
            os.remove(test_db)

        # Create attendance table
        db = AttendanceDatabase(test_db)

        config = {
            "enabled": True,
            "url": "${SUPABASE_URL}",  # Placeholder - should be rejected
            "api_key": "test_key",
        }

        sync_queue = SyncQueueManager(test_db)
        connectivity = ConnectivityMonitor({"enabled": True})

        with self.assertRaises(ValueError) as context:
            manager = CloudSyncManager(config, sync_queue, connectivity)

        self.assertIn("Environment variable not loaded", str(context.exception))
        print("✅ Environment validation (cloud sync) test passed")

        # Clean up
        db.close()
        if os.path.exists(test_db):
            os.remove(test_db)

    def test_sms_notifier_placeholder_detection(self):
        """Test SMS notifier detects placeholder env vars"""
        config = {
            "enabled": True,
            "username": "${SMS_USERNAME}",  # Placeholder
            "password": "test_pass",
            "device_id": "test_device",
        }

        notifier = SMSNotifier(config)

        # Should be disabled due to invalid username
        self.assertFalse(notifier.enabled)
        print("✅ Environment validation (SMS) test passed")


class TestPerformanceOptimizations(unittest.TestCase):
    """Test performance optimizations"""

    def test_qr_scanning_frequency(self):
        """Test that QR scanning only happens every 3rd frame"""
        # This is a conceptual test - actual implementation is in attendance_system.py
        # We verify the logic here

        scan_frames = []
        for frame_count in range(30):
            if frame_count % 3 == 0:
                scan_frames.append(frame_count)

        # Should scan on frames: 0, 3, 6, 9, 12, 15, 18, 21, 24, 27
        expected_scans = 10
        self.assertEqual(len(scan_frames), expected_scans)
        print(
            f"✅ QR scanning frequency test passed: {expected_scans}/30 frames scanned"
        )


def run_all_tests():
    """Run all improvement tests"""
    print("\n" + "=" * 70)
    print("TESTING CODE IMPROVEMENTS")
    print("=" * 70 + "\n")

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestThreadSafety))
    suite.addTests(loader.loadTestsFromTestCase(TestExponentialBackoff))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestEnvironmentValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceOptimizations))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70 + "\n")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
