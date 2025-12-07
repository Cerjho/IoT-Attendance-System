# Testing Documentation

This directory contains test reports, test scripts, and testing-related documentation.

## Contents

### Test Reports
- `TEST_REPORT_YYYYMMDD.md` - Dated comprehensive test reports
- Generated after major system tests or before deployment

### Test Scripts
- `test_system.sh` - Comprehensive system feature test (345 lines)
  - Tests all components: config, dependencies, database, camera, etc.
  - Generates test report with pass/fail/skip statistics
  - Usage: `bash docs/testing/test_system.sh`

## Running Tests

### Quick Unit Tests
```bash
# From project root
pytest -q
```

### Comprehensive System Test
```bash
bash docs/testing/test_system.sh
```

### Integration Tests
```bash
pytest -q -m integration
```

### Hardware Tests (requires Pi hardware)
```bash
pytest -q -m hardware
```

## Test Categories

1. **Unit Tests** (`tests/`) - Fast, isolated component tests
2. **Integration Tests** - Multi-component interaction tests
3. **System Tests** (`test_system.sh`) - Full system validation
4. **Hardware Tests** - GPIO, camera, LED, buzzer tests

## Test Markers

See `pytest.ini` for marker definitions:
- `@pytest.mark.hardware` - Requires physical hardware
- `@pytest.mark.integration` - Integration test
- `@pytest.mark.slow` - Long-running test

## Adding New Tests

1. Unit tests go in `tests/test_*.py`
2. Use appropriate markers
3. Follow existing test patterns
4. Run full test suite before committing

---

For more testing information, see:
- `/tests/README.md` - Test suite organization
- `/docs/technical/TESTING_GUIDE.md` - Testing best practices (if exists)
