"""
Tests for Circuit Breaker
"""
import time

import pytest

from src.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpen, CircuitState


def test_circuit_breaker_closed_state():
    """Test circuit breaker starts in CLOSED state"""
    cb = CircuitBreaker("test", failure_threshold=3, timeout_seconds=1)
    assert cb.state == CircuitState.CLOSED


def test_circuit_breaker_success():
    """Test successful calls keep circuit closed"""
    cb = CircuitBreaker("test", failure_threshold=3)

    def success_func():
        return "ok"

    result = cb.call(success_func)
    assert result == "ok"
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_failure_opens():
    """Test consecutive failures open circuit"""
    cb = CircuitBreaker("test", failure_threshold=3, timeout_seconds=1)

    def fail_func():
        raise Exception("failed")

    # Fail 3 times to open circuit
    for _ in range(3):
        with pytest.raises(Exception):
            cb.call(fail_func)

    assert cb.state == CircuitState.OPEN
    assert cb.failure_count == 3


def test_circuit_breaker_open_rejects():
    """Test open circuit rejects calls"""
    cb = CircuitBreaker("test", failure_threshold=2, timeout_seconds=1)

    def fail_func():
        raise Exception("failed")

    # Open circuit
    for _ in range(2):
        with pytest.raises(Exception):
            cb.call(fail_func)

    assert cb.state == CircuitState.OPEN

    # Next call should be rejected immediately
    with pytest.raises(CircuitBreakerOpen):
        cb.call(fail_func)


def test_circuit_breaker_half_open_timeout():
    """Test circuit transitions to HALF_OPEN after timeout"""
    cb = CircuitBreaker("test", failure_threshold=2, timeout_seconds=0.5)

    def fail_func():
        raise Exception("failed")

    # Open circuit
    for _ in range(2):
        with pytest.raises(Exception):
            cb.call(fail_func)

    assert cb.state == CircuitState.OPEN

    # Wait for timeout
    time.sleep(0.6)

    # Next call should transition to HALF_OPEN then fail
    with pytest.raises(Exception):
        cb.call(fail_func)

    # Should be back to OPEN after failure in HALF_OPEN
    assert cb.state == CircuitState.OPEN


def test_circuit_breaker_recovery():
    """Test circuit closes after successful recovery"""
    cb = CircuitBreaker(
        "test", failure_threshold=2, timeout_seconds=0.5, success_threshold=2
    )

    def fail_func():
        raise Exception("failed")

    def success_func():
        return "ok"

    # Open circuit
    for _ in range(2):
        with pytest.raises(Exception):
            cb.call(fail_func)

    assert cb.state == CircuitState.OPEN

    # Wait for timeout
    time.sleep(0.6)

    # Succeed twice to close circuit
    result1 = cb.call(success_func)
    assert result1 == "ok"
    assert cb.state == CircuitState.HALF_OPEN

    result2 = cb.call(success_func)
    assert result2 == "ok"
    assert cb.state == CircuitState.CLOSED


def test_circuit_breaker_half_open_failure():
    """Test failure in HALF_OPEN reopens circuit"""
    cb = CircuitBreaker(
        "test", failure_threshold=2, timeout_seconds=0.5, success_threshold=2
    )

    def fail_func():
        raise Exception("failed")

    def success_func():
        return "ok"

    # Open circuit
    for _ in range(2):
        with pytest.raises(Exception):
            cb.call(fail_func)

    # Wait for timeout
    time.sleep(0.6)

    # First success in HALF_OPEN
    cb.call(success_func)
    assert cb.state == CircuitState.HALF_OPEN

    # Failure should reopen
    with pytest.raises(Exception):
        cb.call(fail_func)
    assert cb.state == CircuitState.OPEN


def test_circuit_breaker_reset():
    """Test manual reset"""
    cb = CircuitBreaker("test", failure_threshold=2)

    def fail_func():
        raise Exception("failed")

    # Open circuit
    for _ in range(2):
        with pytest.raises(Exception):
            cb.call(fail_func)

    assert cb.state == CircuitState.OPEN

    # Manual reset
    cb.reset()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_status():
    """Test status reporting"""
    cb = CircuitBreaker("test_circuit", failure_threshold=3)

    status = cb.get_status()
    assert status["name"] == "test_circuit"
    assert status["state"] == "closed"
    assert status["failure_count"] == 0
    assert "state_uptime_seconds" in status


def test_circuit_breaker_success_resets_failures():
    """Test success resets failure count in CLOSED state"""
    cb = CircuitBreaker("test", failure_threshold=5)

    def fail_func():
        raise Exception("failed")

    def success_func():
        return "ok"

    # Fail twice (not enough to open)
    for _ in range(2):
        with pytest.raises(Exception):
            cb.call(fail_func)

    assert cb.failure_count == 2
    assert cb.state == CircuitState.CLOSED

    # Success should reset failure count
    cb.call(success_func)
    assert cb.failure_count == 0
    assert cb.state == CircuitState.CLOSED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
