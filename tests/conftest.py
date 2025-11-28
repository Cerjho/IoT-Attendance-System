import os

import pytest

# Optional imports for hardware controllers; fall back to dummies
try:
    from src.hardware.buzzer_controller import BuzzerController as _RealBuzzer
except Exception:
    _RealBuzzer = None

try:
    from src.hardware.rgb_led_controller import RGBLEDController as _RealRGB
except Exception:
    _RealRGB = None

# Optional import for config loader
try:
    from src.utils.config_loader import load_config
except Exception:
    load_config = None

try:
    from src.notifications.sms_notifier import SMSNotifier as _RealSMS
except Exception:
    _RealSMS = None


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--hardware",
        action="store_true",
        default=False,
        help="Include hardware tests (GPIO, buzzer, RGB).",
    )
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Include system integration test module.",
    )


def pytest_ignore_collect(path, config):
    # Ignore system integration module by default (it calls sys.exit)
    if path.basename == "test_system_integration.py" and not config.getoption(
        "--integration"
    ):
        return True
    return False


def pytest_collection_modifyitems(config: pytest.Config, items: list) -> None:
    # Skip hardware tests unless --hardware is set
    if not config.getoption("--hardware"):
        skip_hw = pytest.mark.skip(
            reason="skipped by default; run with --hardware to enable"
        )
        for item in items:
            if (
                "tests/test_hardware.py" in item.nodeid
                or item.nodeid.endswith("test_hardware.py::test_buzzer")
                or item.nodeid.endswith("test_hardware.py::test_rgb_led")
            ):
                item.add_marker(skip_hw)


# Provide safe dummy fixtures to satisfy signatures if someone enables --hardware without real hardware
class _DummyBuzzer:
    def __init__(self):
        self.enabled = False

    def beep_simple(self, *_args, **_kwargs):
        return

    def beep_pattern(self, *_args, **_kwargs):
        return


class _DummyRGB:
    def __init__(self):
        self.enabled = False

    def set_color(self, *_args, **_kwargs):
        return

    def show_color(self, *_args, **_kwargs):
        return

    def fade_to_color(self, *_args, **_kwargs):
        return

    def blink(self, *_args, **_kwargs):
        return

    def pulse(self, *_args, **_kwargs):
        return

    def off(self):
        return


@pytest.fixture
def buzzer():
    # If real controller import worked, try constructing it; otherwise return dummy disabled buzzer
    if _RealBuzzer and load_config:
        try:
            cfg = load_config("config/config.json").get("buzzer", {})
            return _RealBuzzer(cfg)
        except Exception:
            return _DummyBuzzer()
    return _DummyBuzzer()


@pytest.fixture
def rgb():
    if _RealRGB and load_config:
        try:
            cfg = load_config("config/config.json").get("rgb_led", {})
            return _RealRGB(cfg)
        except Exception:
            return _DummyRGB()
    return _DummyRGB()


# --- SMS fixtures for template tests at repo root ---
class _DummySMS:
    enabled = False

    def send_attendance_notification(self, *args, **kwargs):
        return False

    def send_sms(self, *args, **kwargs):
        return False


@pytest.fixture
def sms():
    # Prefer real notifier but keep disabled to avoid external calls
    if _RealSMS and load_config:
        try:
            cfg = (
                load_config("config/config.json").get_all().get("sms_notifications", {})
            )
            cfg = dict(cfg)
            cfg["enabled"] = False  # force disabled in tests
            return _RealSMS(cfg)
        except Exception:
            return _DummySMS()
    return _DummySMS()


@pytest.fixture
def student_id():
    return "2021001"


@pytest.fixture
def name():
    return "Test Student"


@pytest.fixture
def phone():
    return "+639171234567"
