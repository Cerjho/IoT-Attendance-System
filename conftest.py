import pytest

try:
    from src.utils.config_loader import load_config
except Exception:
    load_config = None

try:
    from src.notifications.sms_notifier import SMSNotifier as _RealSMS
except Exception:
    _RealSMS = None


class _DummySMS:
    enabled = False
    def send_attendance_notification(self, *args, **kwargs):
        return False
    def send_sms(self, *args, **kwargs):
        return False


@pytest.fixture
def sms():
    if _RealSMS and load_config:
        try:
            cfg = load_config('config/config.json').get_all().get('sms_notifications', {})
            cfg = dict(cfg)
            cfg['enabled'] = False
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
