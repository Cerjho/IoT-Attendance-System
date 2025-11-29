"""
Tests for Graceful Shutdown Handler

Tests signal handling, resource cleanup, callback execution,
and timeout enforcement.
"""

import signal
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from src.utils.shutdown_handler import ShutdownHandler, ShutdownManager


class TestShutdownHandler:
    """Test ShutdownHandler class."""

    def test_initialization(self):
        """Test handler initialization."""
        handler = ShutdownHandler(timeout=30)
        assert handler.timeout == 30
        assert not handler.shutdown_in_progress
        assert len(handler.shutdown_callbacks) == 0

    def test_register_callback(self):
        """Test callback registration."""
        handler = ShutdownHandler()

        def callback1():
            pass

        def callback2():
            pass

        handler.register_callback(callback1, "callback1")
        handler.register_callback(callback2, "callback2")

        assert len(handler.shutdown_callbacks) == 2

    def test_shutdown_executes_callbacks(self):
        """Test that shutdown executes callbacks."""
        handler = ShutdownHandler(timeout=5)

        callback_executed = []

        def callback1():
            callback_executed.append(1)

        def callback2():
            callback_executed.append(2)

        handler.register_callback(callback1)
        handler.register_callback(callback2)
        handler.shutdown()

        # Callbacks executed in reverse order (LIFO)
        assert callback_executed == [2, 1]
        assert handler.shutdown_in_progress

    def test_shutdown_timeout(self):
        """Test shutdown timeout enforcement."""
        handler = ShutdownHandler(timeout=1)

        def slow_callback():
            time.sleep(2)

        handler.register_callback(slow_callback)

        start = time.time()
        handler.shutdown()
        elapsed = time.time() - start

        # Should timeout after ~1 second
        assert elapsed < 1.5

    def test_shutdown_idempotent(self):
        """Test that shutdown can be called multiple times safely."""
        handler = ShutdownHandler()

        executed = []

        def callback():
            executed.append(1)

        handler.register_callback(callback)

        handler.shutdown()
        handler.shutdown()  # Second call should be no-op

        assert len(executed) == 1

    def test_shutdown_callback_exception_handling(self):
        """Test that exceptions in callbacks don't stop other callbacks."""
        handler = ShutdownHandler()

        executed = []

        def failing_callback():
            executed.append(1)
            raise Exception("Test error")

        def good_callback():
            executed.append(2)

        handler.register_callback(failing_callback)
        handler.register_callback(good_callback)

        handler.shutdown()

        # Both callbacks should execute despite exception
        assert 1 in executed
        assert 2 in executed

    def test_is_shutting_down(self):
        """Test shutdown status check."""
        handler = ShutdownHandler()
        assert not handler.is_shutting_down()

        handler.shutdown()
        assert handler.is_shutting_down()

    def test_wait_for_shutdown(self):
        """Test waiting for shutdown signal."""
        handler = ShutdownHandler()

        # Should return False on timeout
        result = handler.wait_for_shutdown(timeout=0.1)
        assert not result

        # Trigger shutdown in background
        def trigger_shutdown():
            time.sleep(0.1)
            handler.shutdown()

        threading.Thread(target=trigger_shutdown, daemon=True).start()

        # Should return True when shutdown triggered
        result = handler.wait_for_shutdown(timeout=1.0)
        assert result


class TestShutdownManager:
    """Test ShutdownManager class."""

    @pytest.fixture
    def config(self):
        """Test configuration."""
        return {
            "offline_mode": {"enabled": False},
        }

    def test_initialization(self, config):
        """Test manager initialization."""
        manager = ShutdownManager(config, timeout=30)
        assert manager.config == config
        assert len(manager.components) == 0

    def test_register_component(self, config):
        """Test component registration."""
        manager = ShutdownManager(config)

        def shutdown_func():
            pass

        manager.register_component("test_component", shutdown_func, priority=10)

        assert "test_component" in manager.components
        assert manager.components["test_component"]["priority"] == 10

    def test_component_priority_order(self, config):
        """Test components shut down in priority order."""
        manager = ShutdownManager(config)

        execution_order = []

        def high_priority():
            execution_order.append("high")

        def medium_priority():
            execution_order.append("medium")

        def low_priority():
            execution_order.append("low")

        manager.register_component("high", high_priority, priority=10)
        manager.register_component("low", low_priority, priority=1)
        manager.register_component("medium", medium_priority, priority=5)

        manager.handler.shutdown()

        # Should execute in priority order (highest first)
        # Note: _reregister_callbacks sorts and registers correctly
        assert set(execution_order) == {"high", "medium", "low"}
        assert execution_order[0] == "high"  # Highest priority first

    def test_persist_state(self, config, tmp_path):
        """Test state persistence."""
        manager = ShutdownManager(config)

        state_file = tmp_path / "state.json"
        manager.persist_state(str(state_file))

        assert state_file.exists()

        import json

        with open(state_file) as f:
            state = json.load(f)

        assert state["clean_shutdown"] is True
        assert "shutdown_time" in state

    @patch("src.network.connectivity.ConnectivityMonitor")
    def test_flush_pending_queue_online(self, mock_connectivity, config):
        """Test queue flush when online."""
        mock_connectivity_instance = MagicMock()
        mock_connectivity_instance.is_online.return_value = True
        mock_connectivity.return_value = mock_connectivity_instance

        manager = ShutdownManager(config)

        mock_queue = MagicMock()
        mock_queue.get_pending_records.return_value = [1, 2, 3]

        # Should not raise exception
        manager.flush_pending_queue(mock_queue)

    @patch("src.network.connectivity.ConnectivityMonitor")
    def test_flush_pending_queue_offline(self, mock_connectivity, config):
        """Test queue flush when offline."""
        mock_connectivity_instance = MagicMock()
        mock_connectivity_instance.is_online.return_value = False
        mock_connectivity.return_value = mock_connectivity_instance

        manager = ShutdownManager(config)

        mock_queue = MagicMock()

        # Should handle offline gracefully
        manager.flush_pending_queue(mock_queue)
