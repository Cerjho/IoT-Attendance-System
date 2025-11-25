# Test Scripts

## Available Tests

### test_simple_flow.py
Complete system flow test without camera hardware.

**Purpose:** Test the entire attendance workflow from QR scan to SMS notification without requiring physical camera.

**Features:**
- Simulates QR code scanning
- Tests schedule detection
- Validates duplicate prevention
- Records attendance to database
- Tests cloud sync queue
- Sends SMS notifications

**Usage:**
```bash
cd /home/iot/attendance-system
source venv/bin/activate
python3 tests/test_simple_flow.py
```

### test_sms_quick.sh
Quick SMS notification test.

**Purpose:** Test SMS delivery after ensuring SMS Gateway device is online.

**Usage:**
```bash
cd /home/iot/attendance-system
./tests/test_sms_quick.sh
```

## Test Data

Current test students:
- 233294: Maria Santos
- 221566: John Paolo Gonzales

Update parent phone numbers in test_simple_flow.py as needed.
