# Professional Logging - Quick Reference Guide

## Quick Start

### 1. Import and Get Logger
```python
from src.utils.logging_factory import get_logger

logger = get_logger(__name__)
```

### 2. Basic Logging
```python
logger.debug("Detailed diagnostic information")
logger.info("Normal operation")
logger.warning("Warning condition")
logger.error("Error occurred")
logger.critical("Critical failure")
```

### 3. Structured Logging (Add Context)
```python
logger.info("Student attendance recorded", extra={
    "student_id": "2021001",
    "scan_type": "LOGIN",
    "status": "ON_TIME",
    "processing_time_ms": 456.78
})
```

---

## Specialized Logging

### Audit Trail
```python
from src.utils.audit_logger import get_audit_logger

audit_logger = get_audit_logger()

# Security events
audit_logger.security_event(
    "Unauthorized access attempt",
    threat_level="MEDIUM",  # LOW, MEDIUM, HIGH, CRITICAL
    student_id="unknown"
)

# Access tracking
audit_logger.access_event(
    action="LOGIN",
    resource="attendance_system",
    status="success",
    student_id="2021001"
)

# Data changes
audit_logger.data_change(
    entity_type="attendance",
    entity_id="rec-123",
    action="CREATE",  # CREATE, UPDATE, DELETE
    after={"student_id": "2021001", "status": "present"}
)
```

### Business Metrics
```python
from src.utils.audit_logger import get_business_logger

business_logger = get_business_logger()

# Attendance events
business_logger.log_event(
    "student_attendance",
    student_id="2021001",
    scan_type="LOGIN",
    processing_time_ms=456.78
)

# Performance tracking
business_logger.log_performance(
    operation="face_detection",
    duration_ms=234.56
)
```

---

## Decorators

### Automatic Performance Tracking
```python
from src.utils.log_decorators import log_execution_time

@log_execution_time(slow_threshold_ms=1000.0)
def process_image(frame):
    # Automatically logs if > 1000ms
    ...
```

### Operation Context
```python
from src.utils.log_decorators import log_with_context

@log_with_context(operation="face_detection")
def detect_face(frame):
    # All nested logs include operation context
    logger.info("Processing...")  # [face_detection] Processing...
    ...
```

### Exception Handling
```python
from src.utils.log_decorators import log_exceptions

@log_exceptions(reraise=False, default_return=None)
def risky_operation():
    # Exceptions automatically logged with full context
    ...
```

---

## Correlation IDs

Track related operations with correlation IDs:

```python
from src.utils.structured_logging import set_correlation_id
import uuid

# Set at operation start
correlation_id = f"att-{student_id}-{int(time.time())}"
set_correlation_id(correlation_id)

# All subsequent logs include this ID
logger.info("Step 1")  # [att-2021001-1702225593] Step 1
logger.info("Step 2")  # [att-2021001-1702225593] Step 2
```

---

## Custom Log Levels

```python
logger.security("Security-related event")  # SECURITY level (25)
logger.audit("Audit trail entry")          # AUDIT level (22)
logger.metrics("Performance metric")       # METRICS level (21)
```

---

## Log File Locations

```
data/logs/
├── attendance_system_YYYYMMDD.log      # Human-readable logs
├── attendance_system_YYYYMMDD.json     # Structured JSON logs
├── audit_YYYYMMDD.log                  # Audit trail (text)
├── audit_YYYYMMDD.json                 # Audit trail (JSON)
└── business_metrics_YYYYMMDD.json      # Business metrics
```

---

## Common Patterns

### Initialization Logging
```python
logger.info("Component initializing", extra={
    "component": "camera",
    "config": camera_config
})
```

### Error Logging
```python
try:
    result = operation()
except Exception as e:
    logger.error("Operation failed", extra={
        "operation": "capture_photo",
        "error": str(e)
    }, exc_info=True)  # Include traceback
```

### Performance Logging
```python
start_time = time.perf_counter()
result = expensive_operation()
duration_ms = (time.perf_counter() - start_time) * 1000

logger.info("Operation completed", extra={
    "operation": "face_detection",
    "duration_ms": round(duration_ms, 2),
    "result": result
})
```

### State Change Logging
```python
logger.info("State transition", extra={
    "previous_state": "STANDBY",
    "new_state": "CAPTURING",
    "trigger": "qr_code_detected"
})
```

---

## Viewing Logs

### Tail Logs in Real-Time
```bash
# Human-readable logs
tail -f data/logs/attendance_system_$(date +%Y%m%d).log

# Systemd journal (if running as service)
journalctl -u attendance-system -f
```

### Search Logs
```bash
# Search by student ID
grep "2021001" data/logs/attendance_system_$(date +%Y%m%d).log

# Search by correlation ID
grep "att-2021001" data/logs/attendance_system_$(date +%Y%m%d).log

# Search JSON logs with jq
jq 'select(.student_id=="2021001")' data/logs/attendance_system_$(date +%Y%m%d).json
```

### Analyze Audit Trail
```bash
# Security events
jq 'select(.event_type=="SECURITY")' data/logs/audit_$(date +%Y%m%d).json

# Data changes
jq 'select(.action=="CREATE")' data/logs/audit_$(date +%Y%m%d).json
```

### Business Metrics
```bash
# Attendance events
jq 'select(.event=="student_attendance")' data/logs/business_metrics_$(date +%Y%m%d).json

# Average processing time
jq 'select(.event=="student_attendance") | .processing_time_ms' \
  data/logs/business_metrics_$(date +%Y%m%d).json | \
  awk '{sum+=$1; count++} END {print sum/count}'
```

---

## Configuration

Edit `config/config.json`:

```json
{
  "logging": {
    "level": "INFO",
    "log_dir": "data/logs",
    "outputs": {
      "file": {"enabled": true},
      "json_file": {"enabled": true},
      "console": {"enabled": true, "colored": true},
      "syslog": {"enabled": true}
    }
  }
}
```

---

## Testing

```bash
# Run logging system tests
python tests/test_logging_system.py

# Verify all log files created
ls -lh data/logs/
```

---

## Best Practices

### DO
✅ Use structured logging with `extra` fields  
✅ Set correlation IDs for related operations  
✅ Log at appropriate levels (DEBUG for diagnostics, INFO for events)  
✅ Include context (student_id, device_id, operation)  
✅ Use decorators for automatic timing  
✅ Log exceptions with `exc_info=True`

### DON'T
❌ Use print() statements (use logger instead)  
❌ Log sensitive data (passwords, tokens, full photos)  
❌ Log at DEBUG level in production  
❌ Log in tight loops without rate limiting  
❌ Forget to set correlation IDs for multi-step operations  
❌ Log huge objects (limit strings to ~100 chars)

---

## Troubleshooting

### Logs Not Appearing?
1. Check log level: `config.json → logging.level`
2. Check console level: `config.json → logging.outputs.console.level`
3. Verify log directory exists: `ls -la data/logs/`
4. Check file permissions: `chmod -R 755 data/logs`

### Too Many Logs?
1. Increase log level to WARNING or ERROR
2. Use `@log_rate_limit` decorator for frequent operations
3. Adjust `slow_threshold_ms` in decorators

### Missing Context?
1. Set correlation ID: `set_correlation_id(...)`
2. Add `extra` fields: `logger.info("msg", extra={...})`
3. Use `@log_with_context` decorator

---

## Examples from Codebase

### attendance_system.py
```python
@log_execution_time(slow_threshold_ms=2000.0)
def upload_to_database(student_id, photo_path, ...):
    set_correlation_id(f"att-{student_id}-{int(time.time())}")
    
    audit_logger.access_event(
        action="LOGIN",
        resource="attendance_system",
        status="success",
        student_id=student_id
    )
    
    business_logger.log_event(
        "student_attendance",
        student_id=student_id,
        processing_time_ms=processing_time
    )
```

### camera_handler.py
```python
from src.utils.logging_factory import get_logger
from src.utils.log_decorators import log_execution_time

logger = get_logger(__name__)

@log_execution_time(slow_threshold_ms=500.0)
def capture_frame(self):
    logger.debug("Capturing frame", extra={
        "backend": self.backend,
        "resolution": f"{self.width}x{self.height}"
    })
```

---

## Summary

**Core Components:**
- `logging_factory.py` - Unified logging configuration
- `log_decorators.py` - Automatic tracking decorators
- `audit_logger.py` - Audit trail and business metrics

**Key Functions:**
- `get_logger(__name__)` - Get logger for module
- `set_correlation_id(id)` - Track related operations
- `@log_execution_time` - Auto timing
- `@log_with_context` - Add context to nested logs

**Log Files:**
- Human-readable: `attendance_system_*.log`
- Structured JSON: `attendance_system_*.json`
- Audit trail: `audit_*.json`
- Business metrics: `business_metrics_*.json`

---

For complete documentation, see: `LOGGING_IMPLEMENTATION_SUMMARY.md`
