"""
Circuit Breaker Pattern
Prevents cascading failures by stopping repeated calls to failing endpoints
"""
import time
from enum import Enum
from typing import Callable, Dict, Optional

from src.utils.logging_factory import get_logger
from src.utils.audit_logger import get_audit_logger, get_business_logger

logger = get_logger(__name__)
audit_logger = get_audit_logger()
business_logger = get_business_logger()


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """Circuit breaker for external service calls"""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        success_threshold: int = 2,
    ):
        """
        Initialize circuit breaker

        Args:
            name: Circuit name for logging
            failure_threshold: Consecutive failures before opening
            timeout_seconds: Wait time before trying again (open -> half-open)
            success_threshold: Consecutive successes to close from half-open
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout_seconds
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_state_change = time.time()

        logger.info(
            f"Circuit breaker '{name}' initialized: fail_threshold={failure_threshold}, timeout={timeout_seconds}s"
        )

    def call(self, func: Callable, *args, **kwargs):
        """
        Execute function through circuit breaker

        Args:
            func: Function to call
            *args, **kwargs: Arguments to pass to func

        Returns:
            Result from func

        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Original exception from func if circuit allows call
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                raise CircuitBreakerOpen(
                    f"Circuit '{self.name}' is OPEN (too many failures)"
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return False
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.timeout

    def _transition_to_half_open(self):
        """Transition from OPEN to HALF_OPEN"""
        logger.info(
            f"Circuit '{self.name}' transitioning OPEN -> HALF_OPEN (testing recovery)"
        )
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.last_state_change = time.time()

    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed call"""
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Failed during recovery attempt, reopen
            self._transition_to_open()
        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self._transition_to_open()

    def _transition_to_open(self):
        """Transition to OPEN state"""
        logger.error(
            f"Circuit '{self.name}' OPEN (failed {self.failure_count}/{self.failure_threshold} times)"
        )
        
        # Audit log circuit breaker opening
        audit_logger.system_event(
            f"Circuit breaker opened - service degraded",
            component=self.name,
            failure_count=self.failure_count,
            threshold=self.failure_threshold,
            status="OPEN"
        )
        
        # Track error rate
        business_logger.log_error_rate(
            component=self.name,
            error_count=self.failure_count,
            total_count=self.failure_count,
            period="recent"
        )
        
        self.state = CircuitState.OPEN
        self.last_state_change = time.time()

    def _transition_to_closed(self):
        """Transition to CLOSED state"""
        logger.info(
            f"Circuit '{self.name}' CLOSED (recovered after {self.success_count} successes)"
        )
        
        # Audit log circuit breaker recovery
        audit_logger.system_event(
            f"Circuit breaker closed - service recovered",
            component=self.name,
            success_count=self.success_count,
            status="CLOSED"
        )
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_state_change = time.time()

    def reset(self):
        """Manually reset circuit to CLOSED state"""
        logger.info(f"Circuit '{self.name}' manually reset to CLOSED")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_state_change = time.time()

    def get_status(self) -> Dict:
        """
        Get current circuit status

        Returns:
            dict with state, failure_count, success_count, uptime_seconds
        """
        uptime = time.time() - self.last_state_change
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "state_uptime_seconds": uptime,
            "last_failure_time": self.last_failure_time,
        }


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open"""

    pass


class CircuitBreakerManager:
    """Manage multiple circuit breakers"""

    def __init__(self):
        self.circuits: Dict[str, CircuitBreaker] = {}

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        success_threshold: int = 2,
    ) -> CircuitBreaker:
        """
        Get existing circuit or create new one

        Args:
            name: Circuit name
            failure_threshold: Failures before opening
            timeout_seconds: Wait before retry
            success_threshold: Successes to close

        Returns:
            CircuitBreaker instance
        """
        if name not in self.circuits:
            self.circuits[name] = CircuitBreaker(
                name, failure_threshold, timeout_seconds, success_threshold
            )
        return self.circuits[name]

    def reset_all(self):
        """Reset all circuits to CLOSED"""
        for circuit in self.circuits.values():
            circuit.reset()

    def get_status_all(self) -> Dict[str, Dict]:
        """Get status of all circuits"""
        return {name: circuit.get_status() for name, circuit in self.circuits.items()}
