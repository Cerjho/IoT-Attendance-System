# Test Organization Guide

**Last Updated**: December 7, 2025  
**Total Tests**: 194  
**Pass Rate**: 97.8%  
**Coverage**: 50%

---

## Test Directory Structure

```
tests/
├── conftest.py                        # Shared pytest fixtures
├── README.md                          # Test documentation
│
├── Unit Tests (Fast, Isolated)
│   ├── test_alerts.py                 # Alert system (20 tests)
│   ├── test_circuit_breaker.py        # Circuit breaker (10 tests)
│   ├── test_db_transactions.py        # Database transactions (8 tests)
│   ├── test_disk_monitor.py           # Disk space monitoring (7 tests)
│   ├── test_file_locks.py             # File locking (11 tests)
│   ├── test_metrics.py                # Metrics collector (22 tests)
│   ├── test_network_timeouts.py       # Network timeouts (8 tests)
│   ├── test_queue_validator.py        # Queue validation (15 tests)
│   ├── test_shutdown_handler.py       # Shutdown handler (14 tests)
│   ├── test_structured_logging.py     # Logging (9 tests)
│   ├── test_signed_urls.py            # URL signing (5 tests) ✅ NEW
│   ├── test_lighting.py               # Lighting modules (16 tests) ✅ NEW
│   └── test_photo_uploader.py         # Photo uploader (11 tests) ✅ NEW
│
├── Integration Tests (Cross-component)
│   ├── test_cloud_sync_unit.py        # Cloud sync unit tests (5 tests)
│   ├── test_cloud_sync_extended.py    # Cloud sync extended (3 tests)
│   ├── test_queue_sync_integration.py # Queue → cloud sync (1 test)
│   ├── test_system_integration.py     # System integration tests
│   ├── test_all_sms_templates.py      # SMS template tests (10 tests)
│   └── test_sms_notifier_unit.py      # SMS notifier (2 tests)
│
├── Business Logic Tests
│   ├── test_schedule.py               # Schedule manager (1 test)
│   ├── test_attendance_page.py        # Attendance page (5 tests)
│   └── test_improvements.py           # Phase 1/2 improvements (9 tests)
│
├── Hardware Tests (Marked @hardware)
│   ├── test_hardware.py               # General hardware tests (skipped)
│   ├── test_hardware_camera.py        # Camera tests (skipped)
│   ├── test_hardware_gpio.py          # GPIO tests (skipped)
│   └── test_face_quality.py           # Face quality (hardware-dependent)
│
├── Experimental/WIP Tests
│   ├── test_new_supabase.py           # New Supabase integration
│   ├── test_real_complete_flow.py     # Real flow tests
│   ├── test_roster_sync.py            # Roster sync tests
│   └── test_env_security.py           # Environment security
│
└── Quick Test Scripts
    └── test_sms_quick.sh              # Quick SMS validation
```

---

## Test Categories & Markers

### Pytest Markers
```python
@pytest.mark.hardware      # Requires physical hardware (Pi, camera, GPIO)
@pytest.mark.integration   # Cross-component integration test
@pytest.mark.slow          # Takes >1s to run
@pytest.mark.e2e           # End-to-end flow test
```

### Running Tests by Category

```bash
# Fast unit tests only (recommended for development)
pytest -q -m "not hardware and not integration and not slow"

# Integration tests
pytest -q -m integration

# Hardware tests (on Raspberry Pi only)
pytest -q -m hardware

# All tests with coverage
pytest -q --cov=src --cov-report=term-missing

# Specific test file
pytest tests/test_lighting.py -v

# Stop on first failure
pytest -x -v
```

---

## Test Execution Speed

### Fast Tests (<1s each)
- All unit tests in `/tests/test_*.py`
- Total: ~180 tests in 40-50 seconds
- **Use for**: Rapid development, pre-commit checks

### Slow Tests (1-5s each)
- Integration tests with database/network mocking
- System integration tests
- **Use for**: Pre-push validation, CI/CD

### Hardware Tests (requires Pi)
- Camera capture tests
- GPIO control tests
- Face quality with real camera
- **Use for**: On-device validation only

---

## Coverage by Module

### Excellent Coverage (80%+) ✅
```
✅ structured_logging.py     100%
✅ network_timeouts.py        100%
✅ circuit_breaker.py          91%
✅ alerts.py                   90%
✅ db_transactions.py          90%
✅ metrics.py                  89%
✅ shutdown_handler.py         85%
✅ file_locks.py               85%
✅ disk_monitor.py             84%
✅ lighting/compensator.py     80% ⭐ NEW
```

### Good Coverage (60-79%) 🟢
```
🟢 lighting/analyzer.py        74% ⭐ NEW
🟢 schedule_manager.py         70%
🟢 sync_queue.py               61%
```

### Needs Improvement (40-59%) 🟡
```
🟡 cloud_sync.py               57%
🟡 sms_notifier.py             55%
🟡 photo_uploader.py           51% ⭐ IMPROVED (was 16%)
🟡 url_signer.py               51%
🟡 config_loader.py            48%
🟡 template_cache.py           48%
🟡 db_handler.py               40%
```

### Low Coverage (0-39%) 🔴
```
🔴 connectivity.py             26%
🔴 buzzer_controller.py        19%
🔴 face_quality.py             11%
🔴 roster_sync.py              10%
🔴 rgb_led_controller.py       10%
🔴 camera_handler.py            0% (hardware)
🔴 schedule_sync.py             0%
🔴 power_button.py              0% (hardware)
```

---

## Recent Improvements (Dec 7, 2025)

### ✅ Completed
1. **Signed URL Tests** (5 tests)
   - Fixed return value warnings
   - Changed `return True/False` → `assert` statements
   - 100% passing, zero warnings

2. **Lighting Module Tests** (16 tests)
   - `test_lighting.py` created
   - Coverage: Analyzer 0%→74%, Compensator 0%→80%
   - Tests: initialization, brightness analysis, compensation logic

3. **Photo Uploader Tests** (11 tests)
   - `test_photo_uploader.py` created
   - Coverage: 16%→51%
   - Tests: upload success/failure, auth, edge cases

### Impact
- **Total tests**: 165 → 194 (+29)
- **Overall coverage**: 46% → 50% (+4%)
- **Pass rate**: 97.8% (189 passed, 3 skipped, 2 deselected)

---

## Test File Naming Convention

### Pattern
```
test_<module_name>.py          # Unit tests for specific module
test_<feature>_integration.py  # Integration tests
test_<component>_unit.py       # Explicit unit tests
test_hardware_<device>.py      # Hardware-specific tests
```

### Examples
```
✅ test_alerts.py              # Clear: tests src/utils/alerts.py
✅ test_cloud_sync_unit.py     # Clear: unit tests for cloud sync
✅ test_queue_sync_integration.py  # Clear: integration test
✅ test_hardware_camera.py     # Clear: camera hardware tests
```

---

## Test Fixtures (conftest.py)

### Available Fixtures
```python
@pytest.fixture
def temp_db():
    """Temporary SQLite database for testing"""
    
@pytest.fixture
def mock_config():
    """Mock configuration dictionary"""
    
@pytest.fixture
def sample_attendance_data():
    """Sample attendance records"""
```

### Usage
```python
def test_save_attendance(temp_db):
    db = AttendanceDB(temp_db)
    # Test with temporary database
```

---

## Writing New Tests

### Template for Unit Tests
```python
"""
Tests for <module_name>
"""

import pytest
from src.module import ClassName


class TestClassName:
    """Test ClassName functionality"""

    def test_initialization(self):
        """Test object initialization"""
        obj = ClassName()
        assert obj is not None

    def test_feature_success(self):
        """Test feature works correctly"""
        obj = ClassName()
        result = obj.method()
        assert result == expected_value

    def test_feature_error_handling(self):
        """Test error handling"""
        obj = ClassName()
        with pytest.raises(ValueError):
            obj.method(invalid_input)
```

### Template for Integration Tests
```python
"""
Integration tests for <workflow>
"""

import pytest
from unittest.mock import Mock, patch


@pytest.mark.integration
class TestWorkflowIntegration:
    """Test cross-component workflow"""

    @patch('requests.post')
    def test_complete_flow(self, mock_post):
        """Test complete workflow from start to finish"""
        # Setup mocks
        mock_post.return_value = Mock(status_code=200)
        
        # Execute workflow
        result = execute_workflow()
        
        # Verify results
        assert result.success is True
        mock_post.assert_called_once()
```

---

## CI/CD Integration

### GitHub Actions (Recommended)
```yaml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests
        run: |
          pytest -q -m "not hardware" --cov=src --cov-fail-under=50
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Troubleshooting Tests

### Common Issues

#### 1. Import Errors
```bash
# Problem: ModuleNotFoundError
# Solution: Ensure PYTHONPATH includes project root
export PYTHONPATH=/home/iot/attendance-system:$PYTHONPATH
pytest
```

#### 2. Database Locked
```bash
# Problem: sqlite3.OperationalError: database is locked
# Solution: Use temporary database in tests (temp_db fixture)
```

#### 3. Mock Not Working
```bash
# Problem: Mock object not being called
# Solution: Patch at the point of use, not definition
# Wrong:  @patch('src.module.function')
# Right:  @patch('src.caller.function')
```

#### 4. Test Isolation
```bash
# Problem: Tests passing individually but failing together
# Solution: Ensure proper cleanup in fixtures
@pytest.fixture
def resource():
    r = setup()
    yield r
    cleanup(r)  # Always cleanup
```

---

## Performance Benchmarks

### Test Execution Time (Target)
```
Unit tests:        < 50 seconds
Integration tests: < 2 minutes
Full suite:        < 3 minutes
Hardware tests:    < 5 minutes (on Pi)
```

### Current Performance
```
Unit tests:        ~48 seconds ✅
Integration tests: ~1.5 minutes ✅
Full suite:        ~2 minutes ✅
```

---

## Next Steps (Post-Defense)

See `docs/testing/POST_DEFENSE_ROADMAP.md` for:
1. Integration test expansion (target 80% coverage)
2. Performance & load testing
3. Database migration tests
4. Hardware mocking improvements
5. Error handling & edge case coverage

---

## Resources

### Documentation
- [pytest Documentation](https://docs.pytest.org/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

### Project Docs
- `tests/README.md` - Test suite overview
- `docs/testing/TEST_STATUS.md` - Current test status
- `docs/testing/POST_DEFENSE_ROADMAP.md` - Future improvements

---

**Maintained by**: Development Team  
**Last Test Run**: December 7, 2025  
**Next Review**: After Phase 1 improvements
