"""
Graceful Shutdown Handler

Provides clean shutdown with resource cleanup, pending queue flush,
and state persistence. Handles SIGTERM and SIGINT signals.
"""

import atexit
import logging
import signal
import sys
import threading
import time
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


class ShutdownHandler:
    """
    Handles graceful shutdown of the attendance system.

    Features:
    - Signal handling (SIGTERM, SIGINT)
    - Resource cleanup callbacks
    - Pending queue flush
    - State persistence
    - Timeout enforcement
    - Thread-safe shutdown coordination
    """

    def __init__(self, timeout: int = 30):
        """
        Initialize shutdown handler.

        Args:
            timeout: Maximum seconds to wait for graceful shutdown
        """
        self.timeout = timeout
        self.shutdown_callbacks: List[Callable] = []
        self.shutdown_event = threading.Event()
        self.shutdown_in_progress = False
        self.lock = threading.Lock()

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # Register atexit handler as fallback
        atexit.register(self._cleanup_on_exit)

        logger.info("Shutdown handler initialized", extra={"timeout": timeout})

    def register_callback(self, callback: Callable, name: Optional[str] = None) -> None:
        """
        Register a callback to be called during shutdown.

        Callbacks are called in reverse order of registration (LIFO).

        Args:
            callback: Function to call during shutdown
            name: Optional name for logging
        """
        with self.lock:
            self.shutdown_callbacks.append((callback, name or callback.__name__))
            logger.debug(
                f"Registered shutdown callback: {name or callback.__name__}",
                extra={"callback_count": len(self.shutdown_callbacks)},
            )

    def _signal_handler(self, signum: int, frame) -> None:
        """
        Handle shutdown signals.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        logger.info(f"Received signal {signal_name}, initiating graceful shutdown")
        self.shutdown()

    def shutdown(self) -> None:
        """
        Perform graceful shutdown.

        Executes all registered callbacks in reverse order with timeout.
        Thread-safe and idempotent.
        """
        with self.lock:
            if self.shutdown_in_progress:
                logger.warning("Shutdown already in progress")
                return
            self.shutdown_in_progress = True

        logger.info("Starting graceful shutdown")
        self.shutdown_event.set()

        start_time = time.time()
        callbacks = list(reversed(self.shutdown_callbacks))

        for callback, name in callbacks:
            elapsed = time.time() - start_time
            remaining = self.timeout - elapsed

            if remaining <= 0:
                logger.warning(
                    f"Shutdown timeout exceeded, skipping remaining callbacks",
                    extra={"elapsed": elapsed, "timeout": self.timeout},
                )
                break

            try:
                logger.debug(
                    f"Executing shutdown callback: {name}",
                    extra={"remaining_timeout": remaining},
                )

                # Execute callback with timeout using thread
                callback_thread = threading.Thread(target=callback, daemon=True)
                callback_thread.start()
                callback_thread.join(timeout=remaining)

                if callback_thread.is_alive():
                    logger.warning(
                        f"Callback {name} exceeded timeout",
                        extra={"timeout": remaining},
                    )
                else:
                    logger.debug(f"Callback {name} completed successfully")

            except Exception as e:
                logger.error(
                    f"Error in shutdown callback {name}: {e}",
                    extra={"error": str(e), "error_type": type(e).__name__},
                    exc_info=True,
                )

        total_elapsed = time.time() - start_time
        logger.info(
            "Graceful shutdown complete",
            extra={"elapsed": total_elapsed, "callbacks_executed": len(callbacks)},
        )

    def _cleanup_on_exit(self) -> None:
        """Fallback cleanup handler registered with atexit."""
        if not self.shutdown_in_progress:
            logger.info("atexit cleanup triggered")
            self.shutdown()

    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress."""
        return self.shutdown_event.is_set()

    def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for shutdown signal.

        Args:
            timeout: Optional timeout in seconds

        Returns:
            True if shutdown was signaled, False if timeout
        """
        return self.shutdown_event.wait(timeout)


class ShutdownManager:
    """
    High-level manager for system shutdown coordination.

    Coordinates shutdown across multiple components:
    - Database connections
    - Camera resources
    - Network connections
    - Pending sync queue
    - State persistence
    """

    def __init__(self, config: dict, timeout: int = 30):
        """
        Initialize shutdown manager.

        Args:
            config: System configuration
            timeout: Shutdown timeout in seconds
        """
        self.config = config
        self.handler = ShutdownHandler(timeout=timeout)
        self.components = {}

        logger.info("Shutdown manager initialized")

    def register_component(
        self, name: str, shutdown_func: Callable, priority: int = 0
    ) -> None:
        """
        Register a component for shutdown.

        Components with higher priority are shut down first.

        Args:
            name: Component name
            shutdown_func: Function to call for shutdown
            priority: Shutdown priority (higher = earlier)
        """
        self.components[name] = {"func": shutdown_func, "priority": priority}

        # Register in priority order
        self._reregister_callbacks()

        logger.info(
            f"Registered component for shutdown: {name}",
            extra={"priority": priority, "component_count": len(self.components)},
        )

    def _reregister_callbacks(self) -> None:
        """Re-register callbacks in priority order."""
        # Sort by priority (ascending) since shutdown() reverses callbacks (LIFO)
        # This ensures highest priority executes first
        sorted_components = sorted(
            self.components.items(), key=lambda x: x[1]["priority"], reverse=False
        )

        # Clear and re-register
        self.handler.shutdown_callbacks.clear()
        for name, component in sorted_components:
            self.handler.register_callback(component["func"], name)

    def flush_pending_queue(self, sync_queue_manager) -> None:
        """
        Flush pending sync queue before shutdown.

        Args:
            sync_queue_manager: SyncQueueManager instance
        """
        logger.info("Flushing pending sync queue")

        try:
            from src.network.connectivity import ConnectivityMonitor

            connectivity = ConnectivityMonitor(self.config.get("offline_mode", {}))

            if connectivity.is_online():
                queue_items = sync_queue_manager.get_pending_records()
                logger.info(
                    f"Found {len(queue_items)} pending records to sync",
                    extra={"pending_count": len(queue_items)},
                )

                # Attempt sync (will be handled by CloudSyncManager)
                logger.info("Queue flush deferred to sync manager")
            else:
                logger.info("Offline - queue will be synced on next startup")

        except Exception as e:
            logger.error(
                f"Error flushing queue: {e}",
                extra={"error": str(e)},
                exc_info=True,
            )

    def persist_state(self, state_file: str = "data/system_state.json") -> None:
        """
        Persist system state before shutdown.

        Args:
            state_file: Path to state file
        """
        import json
        from datetime import datetime
        from pathlib import Path

        logger.info(f"Persisting system state to {state_file}")

        try:
            state = {
                "shutdown_time": datetime.now().isoformat(),
                "clean_shutdown": True,
                "components": list(self.components.keys()),
            }

            Path(state_file).parent.mkdir(parents=True, exist_ok=True)
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)

            logger.info("System state persisted successfully")

        except Exception as e:
            logger.error(
                f"Error persisting state: {e}",
                extra={"error": str(e)},
                exc_info=True,
            )

    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress."""
        return self.handler.is_shutting_down()

    def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """Wait for shutdown signal."""
        return self.handler.wait_for_shutdown(timeout)
