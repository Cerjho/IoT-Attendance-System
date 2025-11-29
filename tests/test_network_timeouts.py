"""
Tests for Network Timeouts
"""
import pytest

from src.utils.network_timeouts import DEFAULT_TIMEOUTS, NetworkTimeouts


def test_default_timeouts():
    """Test default timeout values"""
    config = DEFAULT_TIMEOUTS
    timeouts = NetworkTimeouts(config)

    assert timeouts.connect_timeout == 5
    assert timeouts.read_timeout == 10
    assert timeouts.supabase_connect == 5
    assert timeouts.supabase_read == 10
    assert timeouts.storage_connect == 5
    assert timeouts.storage_read == 30
    assert timeouts.connectivity_timeout == 3
    assert timeouts.sms_timeout == 10


def test_custom_timeouts():
    """Test custom timeout configuration"""
    config = {
        "connect_timeout": 3,
        "read_timeout": 8,
        "supabase_connect_timeout": 4,
        "supabase_read_timeout": 12,
        "storage_read_timeout": 60,
    }
    timeouts = NetworkTimeouts(config)

    assert timeouts.connect_timeout == 3
    assert timeouts.read_timeout == 8
    assert timeouts.supabase_connect == 4
    assert timeouts.supabase_read == 12
    assert timeouts.storage_read == 60


def test_get_supabase_timeout():
    """Test Supabase timeout tuple"""
    config = {
        "supabase_connect_timeout": 5,
        "supabase_read_timeout": 15,
    }
    timeouts = NetworkTimeouts(config)

    connect, read = timeouts.get_supabase_timeout()
    assert connect == 5
    assert read == 15


def test_get_storage_timeout():
    """Test Storage timeout tuple"""
    config = {
        "storage_connect_timeout": 10,
        "storage_read_timeout": 60,
    }
    timeouts = NetworkTimeouts(config)

    connect, read = timeouts.get_storage_timeout()
    assert connect == 10
    assert read == 60


def test_get_connectivity_timeout():
    """Test connectivity check timeout"""
    config = {"connectivity_timeout": 2}
    timeouts = NetworkTimeouts(config)

    assert timeouts.get_connectivity_timeout() == 2


def test_get_sms_timeout():
    """Test SMS API timeout"""
    config = {"sms_timeout": 15}
    timeouts = NetworkTimeouts(config)

    assert timeouts.get_sms_timeout() == 15


def test_get_timeout_dict():
    """Test getting all timeouts as dict"""
    config = DEFAULT_TIMEOUTS
    timeouts = NetworkTimeouts(config)

    timeout_dict = timeouts.get_timeout_dict()

    assert "connect_timeout" in timeout_dict
    assert "read_timeout" in timeout_dict
    assert "supabase_connect" in timeout_dict
    assert "supabase_read" in timeout_dict
    assert "storage_connect" in timeout_dict
    assert "storage_read" in timeout_dict
    assert "connectivity_timeout" in timeout_dict
    assert "sms_timeout" in timeout_dict


def test_inherit_defaults():
    """Test service-specific timeouts inherit from defaults"""
    config = {
        "connect_timeout": 7,
        "read_timeout": 14,
    }
    timeouts = NetworkTimeouts(config)

    # Should inherit from connect_timeout
    assert timeouts.supabase_connect == 7
    assert timeouts.storage_connect == 7

    # Should inherit from read_timeout
    assert timeouts.supabase_read == 14


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
