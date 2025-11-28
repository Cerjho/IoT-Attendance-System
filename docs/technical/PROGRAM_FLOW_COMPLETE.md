# Complete IoT Attendance System - Program Flow Explanation

## Overview

This is a comprehensive IoT-based attendance system that uses QR codes and face detection to automatically record student attendance, capture photos, sync to cloud, and notify parents via SMS in real-time.

---

## 🎯 System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     IoT ATTENDANCE SYSTEM                           │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Camera   │  │ QR Code  │  │ Face     │  │ Local Database   │   │
│  │ Hardware │→ │ Scanner  │→ │ Detector │→ │ (SQLite)         │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘   │
│                                                       │              │
│                                                       ↓              │
│                                            ┌──────────────────────┐ │
│                                            │ Cloud Sync (Supabase)│ │
│                                            │ (Parallel Thread)    │ │
│                                            └──────────────────────┘ │
│                                                       │              │
│                                                       ↓              │
│                                            ┌──────────────────────┐ │
│                                            │ SMS Notifications    │ │
│                                            │ (Parent Alerts)      │ │
│                                            └──────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Complete Program Flow (Step by Step)

### Phase 1: System Initialization

```
APPLICATION START
    ↓
Load configuration from config/config.json
    ↓
Initialize Components:
  • Camera Handler (USB/Raspberry Pi camera)
  • Face Detector (ML-based detection)
  • SQLite Database (local storage)
  • Buzzer Controller (GPIO pins)
  • Lighting Analyzer (camera quality)
  • Connectivity Monitor (internet check)
  • Cloud Sync Manager (Supabase)
  • SMS Notifier (parent alerts)
    ↓
Create directories: photos/, logs/, data/
    ↓
Start background sync thread (runs every 60 seconds)
    ↓
MAIN LOOP READY
    ↓
Display: "🟢 STANDBY - Waiting for QR code scan..."
```

### Phase 2: QR Code Scanning (Standby State)

```
STANDBY STATE - Continuous Camera Loop
    ↓
Capture frame from camera (~30 fps)
    ↓
Analyze frame for QR codes using ZBar decoder
    ↓
Is QR code detected?
    ├─ NO: Continue to next frame, go back to "Capture frame"
    │
    └─ YES: Extract student ID from QR code
           ↓
           Buzzer: QR_DETECTED pattern (100ms beep)
           ↓
           Check database: Is student already scanned today?
           ├─ YES: 
           │   • Buzzer: DUPLICATE pattern (5 beeps)
           │   • Display: "ALREADY SCANNED TODAY"
           │   • Message displayed for 2 seconds (non-blocking)
           │   • Return to STANDBY
           │
           └─ NO:
               ↓
               Transition to CAPTURING state
               ↓
               Buzzer: Face detection starting
               ↓
               Print: "📱 QR CODE DETECTED: [Student ID]"
               ↓
               "👤 Starting face detection..."
```

### Phase 3: Face Detection (Capturing State)

```
CAPTURING STATE - 5 Second Window
    ↓
Start timer: 0 seconds elapsed
    ↓
Display: "CAPTURING: 5s" "DETECTING..."
    ↓
Loop for next 5 seconds:
    ├─ Capture frame from camera
    ├─ Run face detection algorithm (MediaPipe)
    ├─ Is face detected?
    │  ├─ YES:
    │  │   • Buzzer: FACE_DETECTED pattern (50ms beep)
    │  │   • Print: "✓ Face detected!"
    │  │   • Store best face frame (largest face)
    │  │   • Store face bounding box coordinates
    │  │   • Display: "CAPTURING: 4s" "FACE DETECTED!"
    │  │   • (Keep looking for better faces until timeout)
    │  │
    │  └─ NO:
    │      • Display: "CAPTURING: 3s" "DETECTING..."
    │
    └─ Has 5 seconds elapsed?
       ├─ NO: Continue loop
       │
       └─ YES: Proceed to Phase 4
```

### Phase 4: Photo Capture & Processing

```
Face detection window expired (5 seconds passed)
    ↓
Was a face detected during window?
    ├─ NO:
    │   • Buzzer: ERROR pattern (1000ms beep)
    │   • Print: "❌ No face detected in capture window"
    │   • Display: "NO FACE DETECTED" (2 seconds non-blocking)
    │   • Return to STANDBY
    │   • Student can try again
    │
    └─ YES:
        ↓
        Print: "📸 Capturing photo..."
        ↓
        Take high-resolution still image:
          • Use high-res camera setting (if enabled)
          • Wait for sensor to settle (700ms)
          • Capture frame
        ↓
        Process image:
          • Optional: Crop to face region with padding
          • Optional: Denoise (reduce noise)
          • Optional: White balance correction
          • Optional: CLAHE enhancement (contrast)
          • Optional: Sharpen
        ↓
        Save image to photos/ directory:
          • Filename: attendance_[student_id]_[timestamp].jpg
          • Format: JPEG quality 95%
        ↓
        Print: "✓ Photo saved: [filename]"
        ↓
        Transition to UPLOADING state
```

### Phase 5: Local Database Upload

```
UPLOADING STATE
    ↓
Create attendance record:
  {
    student_id: "2021001",
    timestamp: "2025-11-24 14:30:22",
    photo_path: "photos/attendance_2021001_20251124_143022.jpg",
    qr_data: "2021001",
    status: "present",
    synced: 0,                    ← Not synced yet
    sync_timestamp: NULL,
    cloud_record_id: NULL
  }
    ↓
Insert record into SQLite database
    ↓
Print: "💾 Uploading to database..."
    ↓
✓ LOCAL PERSISTENCE: Record committed to local DB
    ↓
Database confirms: Record saved with ID [123]
```

### Phase 6: Cloud Synchronization (Parallel)

```
CloudSyncManager (Running in background thread AND called directly)
    ↓
Is internet connection available?
    ├─ NO:
    │   • Add record to sync_queue table
    │   • Mark with retry_count = 0
    │   • Attempt will be retried in 60 seconds
    │   • Print: "⟳ QUEUE: Record queued for cloud sync"
    │   • Continue to Phase 7
    │
    └─ YES:
        ↓
        ☁️ CLOUD SYNC ATTEMPT:
        ↓
        Upload photo to Supabase storage:
          • Bucket: "attendance_photos"
          • Path: "photos/[student_id]/[timestamp].jpg"
          • Auth: API key from config
        ↓
        Insert record into Supabase database:
          • Table: "attendance"
          • Fields: student_id, timestamp, photo_url, etc.
        ↓
        Is upload successful?
        ├─ NO:
        │   • Store error message
        │   • Add to sync_queue for retry
        │   • Max 3 retry attempts
        │   • Retry after 30 seconds delay
        │   • Print: "⟳ QUEUE: Failed to sync, queued for retry"
        │   • Photo kept locally for retry
        │
        └─ YES:
            ↓
            Update local database:
              • synced = 1
              • sync_timestamp = [current time]
              • cloud_record_id = [Supabase ID]
            ↓
            DELETE local photo after confirmation
              (free up disk space)
            ↓
            Print: "✓ CLOUD: Synced to Supabase"
            ↓
            Proceed to Phase 7
```

### Phase 7: SMS Parent Notification

```
Parent notification system
    ↓
Is SMS notifications enabled in config?
    ├─ NO:
    │   • Skip SMS sending
    │   • Continue to Phase 8
    │
    └─ YES:
        ↓
        Query database:
          • Get parent phone number for this student_id
          • Get student name
        ↓
        Does student have parent phone number?
        ├─ NO:
        │   • Log: "No parent phone for student"
        │   • Continue to Phase 8
        │
        └─ YES:
            ↓
            Build SMS message from template:
              Default: "Attendance Alert: {student_name} 
                       (ID: {student_id}) checked in at 
                       {time} on {date}."
            ↓
            Example message: "Attendance Alert: John Doe 
                            (ID: STU001) checked in at 
                            02:30 PM on November 24, 2025."
            ↓
            Send via SMS Gateway:
              • API: Android SMS Gateway (cloud-based)
              • Username/Password: From config
              • Device ID: Target device
              • URL: https://api.sms-gate.app/3rdparty/v1/message
            ↓
            Is SMS sent successfully?
            ├─ NO:
            │   • Log error
            │   • Retry in background
            │   • Print: "⚠️ SMS failed, will retry"
            │
            └─ YES:
                ↓
                Print: "📱 SMS sent to parent"
                ↓
                Continue to Phase 8
```

### Phase 8: Success Feedback & Return to Standby

```
Success confirmation
    ↓
Buzzer: SUCCESS pattern (200ms-100ms-200ms-100ms-200ms)
    ↓
Display on screen:
  "SUCCESS!"
  "Student: [Student ID]"
    ↓
Print to console:
  "✓ Attendance recorded successfully!"
  "📊 Total today: [count] student(s)"
    ↓
Session counter increment
    ↓
Display success message for 1.5 seconds (non-blocking)
    ↓
Clear feedback message
    ↓
Return to STANDBY state
    ↓
Print: "🟢 STANDBY - Waiting for QR code scan..."
    ↓
Loop back to Phase 2
```

---

## 🔄 Background Processes (Parallel Execution)

### Background Sync Thread (Every 60 seconds)

```
While system running:
    ↓
Sleep 60 seconds
    ↓
Check sync queue table for failed records
    ↓
Are there unsynced records?
    ├─ NO:
    │   • Wait 60 seconds
    │   • Loop again
    │
    └─ YES:
        ↓
        Is internet available?
        ├─ NO:
        │   • Wait 60 seconds
        │   • Try again later
        │
        └─ YES:
            ↓
            Fetch up to 10 unsynced records
            ↓
            For each record:
              • Attempt cloud sync
              • If success:
                - Update local database (synced = 1)
                - Delete local photo
                - Remove from queue
              • If failure:
                - Increment retry_count
                - Wait 30 seconds
                - Try again (max 3 attempts)
            ↓
            Log results: "[X] succeeded, [Y] failed"
            ↓
            Wait 60 seconds
            ↓
            Loop again
```

---

## 💾 Data Flow & Storage

### Local Storage (SQLite Database)

```
data/attendance.db
  │
  ├── attendance table
  │   ├── id (auto-increment)
  │   ├── student_id
  │   ├── timestamp
  │   ├── photo_path (local file path)
  │   ├── qr_data
  │   ├── status (present/absent)
  │   ├── synced (0 or 1)
  │   ├── sync_timestamp
  │   └── cloud_record_id
  │
  ├── sync_queue table
  │   ├── id
  │   ├── attendance_id
  │   ├── student_id
  │   ├── timestamp
  │   ├── photo_path
  │   ├── error_message
  │   ├── retry_count (0-3)
  │   └── created_at
  │
  ├── students table
  │   ├── student_id (primary key)
  │   ├── name
  │   ├── email
  │   └── parent_phone (for SMS)
  │
  └── device_status table
      ├── device_id
      ├── last_sync
      ├── sync_count
      └── pending_records
```

### File Storage

```
projects/
├── photos/
│   ├── attendance_[student_id]_[timestamp].jpg
│   ├── attendance_2021001_20251124_143022.jpg
│   └── ... (deleted after cloud sync confirmed)
│
├── data/qr_codes/
│   ├── qr_code_STU001.png
│   ├── qr_code_STU002.png
│   └── ... (for printing)
│
└── logs/
    ├── iot_attendance_system.log
    └── ... (debug information)
```

### Cloud Storage (Supabase)

```
Supabase Database Tables:
├── attendance
│   ├── id
│   ├── student_id
│   ├── timestamp
│   ├── photo_url (reference to storage)
│   ├── device_id
│   └── status
│
└── students
    ├── student_id
    ├── name
    ├── parent_phone
    └── email

Supabase Storage Buckets:
└── attendance_photos/
    ├── 2021001/[timestamp].jpg
    ├── 2021002/[timestamp].jpg
    └── ... (photos deleted locally after sync)
```

---

## 🔌 Hardware Components

### 1. **Camera**
- Input: USB webcam or Raspberry Pi camera module
- Resolution: 640x480 (streaming), optional high-res capture
- FPS: ~30 fps continuous
- Purpose: QR code scanning + face detection + photo capture

### 2. **Buzzer**
- GPIO pin controlled
- Patterns:
  - `qr_detected`: 100ms beep
  - `face_detected`: 50ms beep
  - `success`: 200-100-200-100-200ms pattern
  - `error`: 1000ms long beep
  - `duplicate`: 5x 100ms beeps

### 3. **Optional: LED Indicators**
- Green: Standby/Ready
- Blue: Processing
- Red: Error
- (Programmable via GPIO)

---

## ⚙️ Configuration Flow

```
Startup
    ↓
Load config/config.json
    ↓
Parse settings:
  ├── Camera settings
  │   ├── Resolution
  │   ├── FPS
  │   └── Auto-focus mode
  │
  ├── Face detection
  │   ├── Confidence threshold
  │   └── Detection model
  │
  ├── Database
  │   └── File path
  │
  ├── Cloud (Supabase)
  │   ├── API URL
  │   ├── API key
  │   └── Device ID
  │
  ├── SMS Notifications
  │   ├── Enabled flag
  │   ├── API credentials
  │   ├── Message template
  │   └── Device ID
  │
  ├── Offline mode
  │   ├── Queue strategy
  │   ├── Retry attempts
  │   └── Retry delay
  │
  └── Buzzer
      └── GPIO pins + patterns
    ↓
Initialize all components with config values
    ↓
System ready
```

---

## 📱 SMS Notification Flow

```
Student checked in
    ↓
Get student record
    ↓
Retrieve parent phone number
    ↓
Build message:
  Template: "Attendance Alert: {student_name} (ID: {student_id}) 
            checked in at {time} on {date}."
    ↓
Example: "Attendance Alert: John Doe (ID: STU001) checked in at 
         02:30 PM on November 24, 2025."
    ↓
Send to SMS Gateway API:
  POST https://api.sms-gate.app/3rdparty/v1/message
  Headers: Authorization
  Body: {
    username: "EWW3VZ",
    password: "ri9-rbprxdf2ph",
    device_id: "zmmfTkL3NacdGAfNqwD7q",
    recipient: "+1234567890",
    message: "Attendance Alert: John Doe..."
  }
    ↓
Gateway processes:
  • Receives SMS from device
  • Routes to mobile network
  • Delivers to parent's phone
    ↓
Parent receives SMS:
  "Attendance Alert: John Doe (ID: STU001) checked in at 
   02:30 PM on November 24, 2025."
    ↓
Parent confirmed notification
```

---

## 🌐 Offline & Resilience Flow

### Offline Scenario

```
Student checked in
    ↓
Record saved to LOCAL database ✓
    ↓
Is internet available?
    ├─ YES: Sync to cloud immediately
    │   └─ Continue to Phase 6
    │
    └─ NO:
        ↓
        Add to sync_queue table
          • Status: "queued"
          • Retry_count: 0
          • Photo kept locally
        ↓
        Message: "Record queued for cloud sync"
        ↓
        Continue to Phase 8 (success)
        ↓
        Background thread checks every 60 seconds
        ↓
        Internet comes back online?
        ├─ YES:
        │   ↓
        │   Sync all queued records
        │   ↓
        │   Mark as synced
        │   ↓
        │   Delete photos
        │
        └─ NO:
            ↓
            Wait for internet
            ↓
            Retry in 60 seconds
```

### Failure & Retry

```
Cloud sync fails
    ↓
Error captured: "Connection timeout" / "API error" / etc.
    ↓
Add to sync_queue:
  retry_count: 1
  error_message: "Connection timeout"
  photo_path: "photos/[student_id]_[timestamp].jpg"
    ↓
Wait 30 seconds
    ↓
Background thread retries
    ↓
Still fails?
    ├─ retry_count < 3:
    │   ↓
    │   Increment retry_count
    │   ↓
    │   Wait 30 seconds
    │   ↓
    │   Retry again
    │
    └─ retry_count >= 3:
        ↓
        Log as "failed - max retries"
        ↓
        Admin needs to manually sync
        ↓
        Command: python scripts/sync_to_cloud.py
        ↓
        Photo stays local until synced
```

---

## 🎯 State Machine

```
           ┌─────────────┐
           │   START     │
           └──────┬──────┘
                  │
                  ↓
        ┌─────────────────────┐
        │ Initialize System   │
        │ Load Config         │
        │ Start Background    │
        │ Sync Thread         │
        └─────────┬───────────┘
                  │
                  ↓
         ┌────────────────────────────────┐
         │    STANDBY STATE               │
         │ Capture frames from camera     │
         │ Scan for QR codes continuously │
         └────────────┬───────────────────┘
                      │
              ┌───────┴──────────┐
              │ QR Detected?     │
              └───────┬──────────┘
                      │
                      ├─ NO ─→ Loop back to STANDBY
                      │
                      └─ YES
                          │
                          ↓
                ┌──────────────────────┐
                │ Already scanned?     │
                └──────┬───────────────┘
                       │
                   ┌───┴────────────┐
                   │ YES (Duplicate)│ ─→ Show message → Back to STANDBY
                   └───┴────────────┘
                       │
                       └─ NO
                           │
                           ↓
                    ┌─────────────────────┐
                    │ CAPTURING STATE     │
                    │ Detect face (5 sec) │
                    └────────┬────────────┘
                             │
                    ┌────────┴─────────┐
                    │ Face detected?   │
                    └────────┬─────────┘
                             │
                         ┌───┴──────────────┐
                         │ NO ─→ Error msg  │ ─→ Back to STANDBY
                         │      (2 sec)     │
                         └───┴──────────────┘
                             │
                             └─ YES
                                 │
                                 ↓
                          ┌──────────────────┐
                          │ UPLOADING STATE  │
                          │ Capture Photo    │
                          │ Process Image    │
                          └────────┬─────────┘
                                   │
                                   ↓
                         ┌──────────────────────┐
                         │ Save to Local DB     │
                         │ (✓ LOCAL PHASE)      │
                         └────────┬─────────────┘
                                  │
                                  ↓
                         ┌──────────────────────┐
                         │ Cloud Sync Thread    │
                         │ (☁️ CLOUD PHASE)     │
                         │ • Sync to Supabase   │
                         │ • Or queue for retry │
                         └────────┬─────────────┘
                                  │
                                  ↓
                         ┌──────────────────────┐
                         │ SMS Notification     │
                         │ (📱 SMS PHASE)       │
                         │ Send to parent       │
                         └────────┬─────────────┘
                                  │
                                  ↓
                         ┌──────────────────────┐
                         │ Success Message      │
                         │ (1.5 seconds)        │
                         └────────┬─────────────┘
                                  │
                                  ↓
                        Back to STANDBY
```

---

## 📊 Complete Data Life Cycle

```
1. CAPTURE PHASE
   Student presents ID
   ├─ QR Code scanned
   │   └─ Student ID extracted: "2021001"
   │
   └─ Face detected
       └─ Image captured: "attendance_2021001_20251124_143022.jpg"

2. LOCAL PERSISTENCE PHASE
   Data saved to SQLite database
   ├─ attendance table
   │   ├── id: 123
   │   ├── student_id: "2021001"
   │   ├── timestamp: "2025-11-24 14:30:22"
   │   ├── photo_path: "photos/attendance_2021001_20251124_143022.jpg"
   │   └── synced: 0 (not yet synced)
   │
   └─ File saved
       └─ photos/attendance_2021001_20251124_143022.jpg

3. CLOUD SYNC PHASE
   Background thread attempts cloud sync
   ├─ Upload photo to Supabase storage
   │   └─ Path: attendance_photos/2021001/20251124_143022.jpg
   │
   ├─ Insert record to Supabase database
   │   └─ Synced record ID: "supabase_uuid"
   │
   └─ Update local database
       ├── synced: 1
       ├── cloud_record_id: "supabase_uuid"
       └── sync_timestamp: "2025-11-24 14:30:35"

4. CLEANUP PHASE
   After confirmed sync
   └─ Delete local photo
      └─ Photos directory freed up
          └─ Space saved for future captures

5. REPORTING PHASE
   Data available for analysis
   ├─ Local database
   │   └─ Quick access, offline capability
   │
   ├─ Cloud database
   │   └─ Permanent backup, remote access
   │
   ├─ SMS Notifications
   │   └─ Real-time parent alerts
   │
   └─ JSON Export
       └─ Reports and analytics
```

---

## 🔐 Security & Data Protection

```
1. LOCAL DATA
   ├─ SQLite database encrypted via password (optional)
   ├─ Photos with restricted file permissions
   └─ Logs with attendance records

2. CLOUD DATA
   ├─ Supabase API key protected
   │   └─ Stored in environment variables (not hardcoded)
   │
   ├─ HTTPS encryption
   │   └─ All data in transit encrypted
   │
   └─ Database permissions
       └─ Row-level security (RLS) configured

3. SMS DATA
   ├─ Parent phone numbers in database
   ├─ Credentials in config file
   └─ API calls via HTTPS only

4. PHOTO DATA
   ├─ Stored with student ID reference
   ├─ Automatically deleted after cloud sync
   └─ Backup in cloud storage
```

---

## ⚡ Performance Optimization

### Continuous Scanning (Latest Implementation)

```
Before (Blocking):
  Frame 1 → QR detected → BLOCK 2 seconds → Frame 11
  (Missed frames 2-10)

After (Non-Blocking):
  Frame 1 → QR detected → Queue message → Continue
  Frame 2 → Render message → Continue
  Frame 3 → Render message → Continue
  ...
  Frame 60 → Message expires → Continue
  (All frames processed, 30 FPS maintained)
```

### Key Optimizations

1. **Non-blocking feedback system**
   - Messages rendered on frame with elapsed time tracking
   - Loop continues at full FPS
   - No missed QR codes

2. **Background sync thread**
   - Parallel processing
   - Doesn't block main scanning loop
   - Batch processing of queued records

3. **Headless mode**
   - No GUI rendering overhead
   - Ideal for remote deployment
   - Faster processing

4. **High-res still capture**
   - High-res image only for final photo
   - Streaming frames at lower resolution
   - Best quality + performance balance

---

## 📈 Monitoring & Debugging

### View System Status

```bash
# Check attendance records
sqlite3 data/attendance.db "SELECT * FROM attendance WHERE date(timestamp) = date('now');"

# Check sync queue
sqlite3 data/attendance.db "SELECT * FROM sync_queue;"

# View logs
tail -f logs/iot_attendance_system.log

# Check camera
python -c "from src.camera import CameraHandler; cam = CameraHandler(); print('✓ Camera OK')"

# Test SMS
python manage_parents.py --test-sms
```

### Expected Console Output

```
🟢 STANDBY - Waiting for QR code scan...

========================================================================
📱 QR CODE DETECTED: 2021001
========================================================================
👤 Starting face detection...
   ✓ Face detected!
📸 Capturing photo...
   ✓ Photo saved: photos/attendance_2021001_20251124_143022.jpg
💾 Uploading to database...
   ✓ LOCAL: Attendance recorded!
   ☁️ CLOUD: Synced to Supabase
   📱 SMS sent to parent
   ✓ Attendance recorded successfully!
   📊 Total today: 1

========================================================================

🟢 STANDBY - Waiting for QR code scan...
```

---

## 🎓 Example Workflow

### Complete Student Check-in Sequence

```
TIME: 08:30:00
USER ACTION: Student 2021001 (John Doe) scans QR code at kiosk

08:30:00.001
SYSTEM: Detects QR code in camera frame
SYSTEM: Extracts student_id = "2021001"
SYSTEM: Buzzer: 100ms beep (qr_detected)
SYSTEM: Checks database: Not scanned today
SYSTEM: Transitions to CAPTURING state

08:30:00.100
SYSTEM: Starts 5-second face detection window
SYSTEM: Displays: "CAPTURING: 5s DETECTING..."

08:30:00.500
SYSTEM: Detects face in frame
SYSTEM: Buzzer: 50ms beep (face_detected)
SYSTEM: Stores best face image and bounding box
SYSTEM: Displays: "CAPTURING: 4s FACE DETECTED!"

08:30:05.000
SYSTEM: Face detection window expires
SYSTEM: Has face been captured? YES
SYSTEM: Captures high-resolution photo
SYSTEM: Processes image (denoise, white balance, enhance)
SYSTEM: Saves: photos/attendance_2021001_20251124_083000.jpg

08:30:05.200
SYSTEM: Creates database record:
         {
           student_id: "2021001",
           timestamp: "2025-11-24 08:30:00",
           photo_path: "photos/attendance_2021001_20251124_083000.jpg",
           synced: 0
         }
SYSTEM: Inserts into SQLite database ✓
SYSTEM: ✓ LOCAL: Record persisted

08:30:05.300
SYSTEM: Attempts cloud sync
SYSTEM: Checks internet connection: ONLINE
SYSTEM: Uploads photo to Supabase storage ✓
SYSTEM: Inserts record to Supabase database ✓
SYSTEM: ☁️ CLOUD: Synced successfully
SYSTEM: Updates local database: synced = 1
SYSTEM: Deletes local photo (space freed)

08:30:05.400
SYSTEM: Queries student record
SYSTEM: Gets parent phone: "+1-555-1234"
SYSTEM: Gets student name: "John Doe"
SYSTEM: Builds SMS: "Attendance Alert: John Doe (ID: 2021001) 
                     checked in at 08:30 AM on November 24, 2025."
SYSTEM: Sends via SMS Gateway API
SYSTEM: 📱 SMS delivered to parent

08:30:05.500
SYSTEM: Displays: "SUCCESS!" (1.5 seconds)
SYSTEM: Buzzer: SUCCESS pattern (200-100-200-100-200ms)
SYSTEM: Print: "✓ Attendance recorded successfully!"
SYSTEM: Print: "📊 Total today: 1"
SYSTEM: Increments session counter

08:30:07.000
SYSTEM: Feedback timeout
SYSTEM: Returns to STANDBY state
SYSTEM: Displays: "🟢 STANDBY - Waiting for QR code scan..."
SYSTEM: Ready for next student

08:30:07.001 onwards
SYSTEM: Continuous camera loop at ~30 fps
SYSTEM: Scanning for next QR code
```

---

## Summary

The IoT Attendance System is a **complete, production-ready solution** that:

1. ✅ **Captures** attendance via QR codes and face detection
2. ✅ **Records** data locally (SQLite) and in cloud (Supabase)
3. ✅ **Notifies** parents via SMS in real-time
4. ✅ **Optimizes** performance with continuous, non-blocking scanning
5. ✅ **Handles** offline scenarios with intelligent queueing
6. ✅ **Provides** feedback via visual, audio, and SMS alerts
7. ✅ **Scales** from single device to multi-device deployment

Perfect for schools, offices, and event management systems.
