# IoT Attendance System - Detailed Execution Flow

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     RASPBERRY PI / IoT DEVICE                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  HARDWARE LAYER:                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │   USB       │  │   GPIO      │  │   Network   │  │   Storage   │  │
│  │   Camera    │  │   Buzzer    │  │   Ethernet  │  │   SD Card   │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │
│         │              │                   │              │            │
│         └──────────────┴───────────────────┴──────────────┘            │
│                        │                                               │
├─────────────────────────────────────────────────────────────────────────┤
│  SOFTWARE LAYER:                                                       │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                   MAIN APPLICATION                               │  │
│  │         (attendance_system.py - 856 lines)                       │  │
│  │                                                                  │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │  │
│  │  │  QR Scanner  │  │ Face Detector│  │ Photo Capture│          │  │
│  │  │  (pyzbar)    │  │ (MediaPipe)  │  │ (OpenCV)     │          │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘          │  │
│  │         │                 │                 │                   │  │
│  │         └─────────────────┴─────────────────┘                   │  │
│  │                       │                                         │  │
│  │                       ↓                                         │  │
│  │         ┌──────────────────────────────┐                       │  │
│  │         │  SQLite Database Manager     │                       │  │
│  │         │  (data/attendance.db)         │                       │  │
│  │         └──────────────────────────────┘                       │  │
│  │                       │                                         │  │
│  │         ┌─────────────┴──────────────┐                         │  │
│  │         │                            │                         │  │
│  │         ↓                            ↓                         │  │
│  │  ┌─────────────────┐      ┌────────────────────┐              │  │
│  │  │ Cloud Sync Mgr  │      │ SMS Notifier       │              │  │
│  │  │ (Supabase)      │      │ (SMS Gateway)      │              │  │
│  │  │ [Background]    │      │ [Parallel]         │              │  │
│  │  └─────────────────┘      └────────────────────┘              │  │
│  │                                                                  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
         │                           │                      │
         │                           │                      │
         ↓                           ↓                      ↓
    ┌────────────┐           ┌──────────────┐         ┌──────────────┐
    │  SUPABASE  │           │  SMS GATEWAY │         │  INTERNET    │
    │  Cloud DB  │           │  (Android)   │         │  CONNECTION  │
    └────────────┘           └──────────────┘         └──────────────┘
         │                           │
         │                           │
         ↓                           ↓
    ┌────────────┐           ┌──────────────┐
    │ Attendance │           │ Parent Phones│
    │ Records    │           │ (SMS alerts) │
    │ (Backup)   │           │              │
    └────────────┘           └──────────────┘
```

---

## Complete Execution Sequence Diagram

```
TIME    MAIN THREAD              BACKGROUND THREAD           EXTERNAL
───────────────────────────────────────────────────────────────────────
0:00    START APPLICATION
        ├─ Load config.json
        ├─ Initialize Camera
        ├─ Initialize Detector
        ├─ Load Database
        ├─ Start Background Thread
        │                        ├─ Start (Daemon)
        │                        ├─ Every 60 sec:
        │                        │  ├─ Check sync_queue
        │                        │  ├─ Retry failed syncs
        │                        │  └─ Delete synced photos
        └─ Enter Main Loop

0:01    🟢 STANDBY STATE
        ├─ Capture frame (30 FPS)
        ├─ Analyze for QR codes
        ├─ No QR? Loop to 0:01
        │
        └─ QR DETECTED! "2021001"
          ├─ Buzzer: beep (100ms)
          ├─ Check: Already scanned?
          │  └─ YES → Error msg (2s) → Back to STANDBY
          │  └─ NO → Continue
          └─ Transition: CAPTURING

0:02    🎥 CAPTURING STATE (5 sec window)
        ├─ Loop for 5 seconds:
        │  ├─ Capture frame
        │  ├─ Detect faces
        │  ├─ Face found? Store image
        │  ├─ Display countdown
        │  └─ Time expired?
        │
        └─ YES → Face detected? → YES → Proceed
                                    NO → Error msg

0:03    📸 PHOTO CAPTURE & PROCESS
        ├─ Capture high-res still
        ├─ Process image:
        │  ├─ Denoise
        │  ├─ White balance
        │  ├─ Enhance contrast
        │  └─ Sharpen
        ├─ Save to photos/
        └─ Proceed to UPLOADING

0:04    💾 LOCAL DATABASE INSERT
        ├─ Create record:
        │  {
        │    student_id: "2021001",
        │    timestamp: "2025-11-24 14:30:00",
        │    photo_path: "photos/...",
        │    synced: 0
        │  }
        ├─ Insert to SQLite
        ├─ ✓ LOCAL: Persisted
        └─ Proceed to CLOUD SYNC

0:05    ☁️ CLOUD SYNC (Immediate attempt)
        ├─ Check internet: ONLINE
        ├─ Upload photo → Supabase
        ├─ Insert record → Supabase
        │                                 → SUPABASE CLOUD
        │                                   ├─ Store photo
        │                                   ├─ Record inserted
        │                                   └─ UUID returned
        ├─ Update local DB:
        │  {synced: 1, cloud_id: "uuid"}
        ├─ DELETE local photo
        ├─ ✓ CLOUD: Synced
        └─ Proceed to SMS

0:06    📱 SMS NOTIFICATION
        ├─ Get parent phone
        ├─ Build message:
        │  "Attendance Alert: John Doe
        │   (ID: 2021001) checked in at
        │   02:30 PM on November 24, 2025."
        ├─ Send to SMS Gateway
        │                                 → SMS GATEWAY
        │                                   ├─ API call
        │                                   ├─ Send to device
        │                                   └─ Route to network
        │                                      ↓
        │                                   PARENT PHONE
        │                                   ├─ SMS received
        │                                   ├─ Notification
        │                                   └─ Parent reads
        ├─ ✓ SMS: Sent
        └─ Proceed to SUCCESS

0:07    ✅ SUCCESS & RETURN
        ├─ Display: "SUCCESS!" (1.5s)
        ├─ Buzzer: success pattern
        ├─ Print: "✓ Attendance recorded!"
        ├─ Print: "📊 Total today: 1"
        ├─ Session counter++
        └─ Transition: STANDBY

0:09    Back to 🟢 STANDBY STATE
        └─ Ready for next student


PARALLEL BACKGROUND THREAD (Every 60 seconds):
───────────────────────────────────────────────

        While system running:
        │
        ├─ Sleep 60 seconds
        │
        ├─ Query sync_queue table
        │  └─ Find unsynced records
        │
        ├─ For each queued record:
        │  ├─ Is internet available?
        │  │  └─ NO: Wait for internet
        │  │
        │  └─ YES:
        │     ├─ Attempt cloud sync
        │     │  ├─ If success: Update DB, delete photo
        │     │  └─ If failure: Increment retry_count
        │     │
        │     ├─ retry_count < 3?
        │     │  ├─ YES: Mark for retry in 30 sec
        │     │  └─ NO: Log as failed
        │     │
        │     └─ Remove from queue (or keep for manual)
        │
        └─ Loop every 60 seconds
```

---

## Detailed Phase Breakdown

### PHASE 1: INITIALIZATION

```
Application Start
    │
    ├─→ Load Configuration
    │    └─ config/config.json
    │       ├─ Camera: resolution, fps, auto-focus
    │       ├─ Database: path, type
    │       ├─ Cloud: Supabase URL, API key
    │       ├─ SMS: Gateway credentials, template
    │       ├─ Offline: queue strategy, retries
    │       └─ Buzzer: GPIO pins, patterns
    │
    ├─→ Initialize Components
    │    ├─ Camera Handler
    │    │  └─ Connect to USB/Pi camera
    │    │     └─ Set resolution, FPS
    │    │
    │    ├─ Face Detector
    │    │  └─ Load MediaPipe model
    │    │     └─ Ready for real-time detection
    │    │
    │    ├─ SQLite Database
    │    │  └─ Connect to data/attendance.db
    │    │     ├─ Verify tables exist
    │    │     └─ Initialize if new
    │    │
    │    ├─ Buzzer Controller
    │    │  └─ Initialize GPIO
    │    │     └─ Test patterns
    │    │
    │    ├─ Cloud Sync Manager
    │    │  └─ Load Supabase credentials
    │    │     ├─ Test connection (optional)
    │    │     └─ Ready for async sync
    │    │
    │    └─ SMS Notifier
    │       └─ Load SMS Gateway credentials
    │          └─ Ready to send notifications
    │
    ├─→ Start Background Thread
    │    └─ Daemon thread (won't block exit)
    │       ├─ Check every 60 seconds
    │       ├─ Process sync_queue
    │       └─ Retry failed records
    │
    ├─→ Create Directories
    │    ├─ photos/      (attendance images)
    │    ├─ logs/        (debug logs)
    │    └─ data/        (database file)
    │
    ├─→ Display System Status
    │    └─ "IoT ATTENDANCE SYSTEM"
    │       "System Ready!"
    │       "Press Ctrl+C to stop"
    │
    └─→ MAIN LOOP READY
        └─ Transition to STANDBY
```

### PHASE 2: QR CODE SCANNING (CONTINUOUS LOOP)

```
🟢 STANDBY STATE
    │
    └─→ Continuous Camera Loop (while True):
        │
        ├─→ Capture Frame
        │    └─ Read from camera (30 FPS)
        │       └─ Frame size: 640x480 (or custom)
        │
        ├─→ QR Code Scanning
        │    └─ Use ZBar decoder
        │       ├─ Scan entire frame
        │       ├─ Look for valid QR codes
        │       └─ Extract student_id
        │
        ├─→ Is QR Code Detected?
        │    │
        │    ├─ NO:
        │    │  └─ Continue loop
        │    │     └─ Go back to "Capture Frame"
        │    │
        │    └─ YES: Extract student_id
        │        │
        │        └─→ VALIDATION
        │             │
        │             ├─→ Buzzer: QR_DETECTED pattern
        │             │    └─ 100ms beep (auditory feedback)
        │             │
        │             ├─→ Print: "📱 QR CODE DETECTED: [ID]"
        │             │
        │             ├─→ Check Database
        │             │    └─ SELECT * FROM attendance
        │             │       WHERE student_id = "2021001"
        │             │       AND date(timestamp) = date('now')
        │             │
        │             └─→ Already Scanned Today?
        │                  │
        │                  ├─ YES (DUPLICATE):
        │                  │  │
        │                  │  ├─→ Buzzer: DUPLICATE pattern
        │                  │  │    └─ 5x 100ms beeps
        │                  │  │
        │                  │  ├─→ Print: "⚠️ Student ... ALREADY SCANNED"
        │                  │  │
        │                  │  ├─→ Display: "ALREADY SCANNED TODAY"
        │                  │  │    └─ Non-blocking (2 seconds)
        │                  │  │
        │                  │  └─→ Return to STANDBY
        │                  │      └─ Go back to loop
        │                  │
        │                  └─ NO (VALID):
        │                     │
        │                     └─→ Transition to CAPTURING
        │                          │
        │                          ├─→ Print: "📱 QR CODE DETECTED: 2021001"
        │                          ├─→ Print: "👤 Starting face detection..."
        │                          ├─→ Buzzer: face_detection starting
        │                          │
        │                          └─→ Set timer: 5 seconds
        │                             CAPTURING state ready
```

### PHASE 3: FACE DETECTION (5-SECOND WINDOW)

```
🎥 CAPTURING STATE
    │
    └─→ Detect Face (5 second countdown):
        │
        ├─→ Initialize
        │    ├─ Start time: now()
        │    ├─ Best face: None
        │    ├─ Best box: None
        │    └─ Display: "CAPTURING: 5s DETECTING..."
        │
        ├─→ Loop (while remaining time > 0):
        │    │
        │    ├─→ Capture Frame
        │    │    └─ Read from camera
        │    │
        │    ├─→ Run Face Detection
        │    │    ├─ Use MediaPipe Mediapipe
        │    │    ├─ Analyze frame for faces
        │    │    └─ Get bounding boxes + confidence
        │    │
        │    ├─→ Any Faces Found?
        │    │    │
        │    │    ├─ NO:
        │    │    │  └─ Continue loop
        │    │    │     └─ Display: "CAPTURING: 3s DETECTING..."
        │    │    │
        │    │    └─ YES:
        │    │        │
        │    │        ├─→ Buzzer: FACE_DETECTED (once)
        │    │        │    └─ 50ms beep
        │    │        │
        │    │        ├─→ Print: "✓ Face detected!"
        │    │        │
        │    │        ├─→ Store Best Face
        │    │        │    ├─ Get largest face (area = width × height)
        │    │        │    ├─ Save frame image
        │    │        │    ├─ Save bounding box (x, y, w, h)
        │    │        │    └─ Keep looking for better faces
        │    │        │
        │    │        └─→ Display: "CAPTURING: 2s FACE DETECTED!"
        │    │            └─ Show on-screen detection box
        │    │
        │    ├─→ Calculate Remaining Time
        │    │    └─ remaining = capture_window - elapsed_time
        │    │       └─ remaining = 5.0 - 1.5 = 3.5 seconds
        │    │
        │    └─→ Has 5 Seconds Elapsed?
        │         │
        │         ├─ NO: Continue loop
        │         │
        │         └─ YES: Break loop, proceed
        │
        └─→ Check: Was Face Detected?
             │
             ├─ NO:
             │  │
             │  ├─→ Buzzer: ERROR pattern
             │  │    └─ 1000ms (1 second) beep
             │  │
             │  ├─→ Print: "❌ No face detected in capture window"
             │  │
             │  ├─→ Display: "NO FACE DETECTED" (2 sec non-blocking)
             │  │
             │  └─→ Return to STANDBY
             │      └─ Student can try again
             │
             └─ YES:
                 │
                 └─→ Proceed to PHOTO CAPTURE
```

### PHASE 4: PHOTO CAPTURE & PROCESSING

```
📸 PHOTO CAPTURE & PROCESSING
    │
    ├─→ Print: "📸 Capturing photo..."
    │
    ├─→ Capture High-Resolution Still
    │    ├─ Use high-res setting (if enabled)
    │    │  └─ Higher resolution than streaming
    │    │
    │    ├─ Wait for sensor to settle
    │    │  └─ 700ms delay (configurable)
    │    │
    │    └─ Capture frame
    │       └─ Image ready for processing
    │
    ├─→ Image Processing Pipeline
    │    │
    │    ├─ Step 1: Crop to Face (optional)
    │    │  ├─ Get bounding box from Phase 3
    │    │  ├─ Add padding around face
    │    │  └─ Crop image to region
    │    │     └─ Result: Focused photo
    │    │
    │    ├─ Step 2: Denoise (optional)
    │    │  ├─ Use non-local means denoising
    │    │  ├─ Reduce noise
    │    │  └─ Preserve edges
    │    │     └─ Result: Cleaner image
    │    │
    │    ├─ Step 3: White Balance (optional)
    │    │  ├─ Gray-world white balance
    │    │  ├─ Correct color casts
    │    │  └─ Natural color reproduction
    │    │     └─ Result: Accurate colors
    │    │
    │    ├─ Step 4: Enhance Contrast (optional)
    │    │  ├─ CLAHE (Contrast Limited Adaptive Histogram)
    │    │  ├─ Improve details
    │    │  └─ Avoid over-enhancement
    │    │     └─ Result: Better visibility
    │    │
    │    └─ Step 5: Sharpen (optional)
    │        ├─ Unsharp mask
    │        ├─ Enhance fine details
    │        └─ Reduce blur
    │           └─ Result: Sharp photo
    │
    ├─→ Save Image
    │    ├─ Filename: attendance_[student_id]_[timestamp].jpg
    │    │  └─ Example: attendance_2021001_20251124_143022.jpg
    │    │
    │    ├─ Directory: photos/
    │    │
    │    ├─ Format: JPEG
    │    │  └─ Compression: Quality 95%
    │    │
    │    └─ File size: ~50-200 KB (depending on settings)
    │
    ├─→ Print: "✓ Photo saved: [filename]"
    │
    └─→ Proceed to LOCAL DATABASE INSERT
```

### PHASE 5: LOCAL DATABASE INSERT

```
💾 LOCAL DATABASE UPLOAD
    │
    ├─→ Create Attendance Record
    │    │
    │    └─ Record Data:
    │        {
    │          student_id: "2021001",
    │          timestamp: "2025-11-24 14:30:22",
    │          photo_path: "photos/attendance_2021001_20251124_143022.jpg",
    │          qr_data: "2021001",
    │          status: "present",
    │          synced: 0,              ← Not synced yet
    │          sync_timestamp: NULL,
    │          cloud_record_id: NULL
    │        }
    │
    ├─→ Insert into SQLite
    │    │
    │    ├─ SQL: INSERT INTO attendance
    │    │       (student_id, timestamp, photo_path, ...)
    │    │       VALUES ("2021001", "2025-11-24 14:30:22", ...)
    │    │
    │    └─ Local database confirms
    │       └─ Record ID: 123 (auto-increment)
    │
    ├─→ ✓ LOCAL PERSISTENCE
    │    └─ Data guaranteed safe locally
    │
    ├─→ Print: "✓ LOCAL: Attendance recorded!"
    │
    └─→ Proceed to CLOUD SYNC ATTEMPT
```

### PHASE 6: CLOUD SYNCHRONIZATION

```
☁️ CLOUD SYNC (Parallel - happens in main or background)
    │
    ├─→ Check Internet Connection
    │    │
    │    ├─ Test connectivity: ping 8.8.8.8
    │    │
    │    └─ Is Online?
    │         │
    │         ├─ NO (OFFLINE):
    │         │  │
    │         │  ├─→ Add to sync_queue
    │         │  │    {
    │         │  │      attendance_id: 123,
    │         │  │      student_id: "2021001",
    │         │  │      photo_path: "photos/...",
    │         │  │      retry_count: 0,
    │         │  │      error_message: NULL,
    │         │  │      created_at: NOW()
    │         │  │    }
    │         │  │
    │         │  ├─→ Print: "⟳ QUEUE: Record queued for cloud sync"
    │         │  │
    │         │  ├─→ Photo stays local for retry
    │         │  │
    │         │  └─→ Proceed to SMS
    │         │      (can still send SMS if phone has data)
    │         │
    │         └─ YES (ONLINE):
    │             │
    │             └─→ CLOUD SYNC ATTEMPT
    │                  │
    │                  ├─ Step 1: Upload Photo
    │                  │  │
    │                  │  ├─ Supabase storage bucket: "attendance_photos"
    │                  │  ├─ Path: 2021001/20251124_143022.jpg
    │                  │  ├─ File: photo_data (binary)
    │                  │  ├─ Auth: API key
    │                  │  │
    │                  │  └─ Response: photo_url
    │                  │     └─ URL: https://supabase.../2021001/...jpg
    │                  │
    │                  ├─ Step 2: Insert Record
    │                  │  │
    │                  │  ├─ Supabase table: "attendance"
    │                  │  ├─ Data:
    │                  │  │  {
    │                  │  │    student_id: "2021001",
    │                  │  │    timestamp: "2025-11-24 14:30:22",
    │                  │  │    photo_url: "[url from step 1]",
    │                  │  │    device_id: "device_001",
    │                  │  │    status: "present"
    │                  │  │  }
    │                  │  │
    │                  │  └─ Response: record_id (UUID)
    │                  │     └─ UUID: "abc123def456..."
    │                  │
    │                  └─ Is Upload Successful?
    │                     │
    │                     ├─ NO (ERROR):
    │                     │  │
    │                     │  ├─→ Capture error: "Connection timeout"
    │                     │  │
    │                     │  ├─→ Add to sync_queue
    │                     │  │    {
    │                     │  │      retry_count: 0,
    │                     │  │      error_message: "Connection timeout"
    │                     │  │    }
    │                     │  │
    │                     │  ├─→ Photo kept locally
    │                     │  │
    │                     │  ├─→ Print: "⟳ QUEUE: Failed to sync, queued"
    │                     │  │
    │                     │  └─→ Background thread will retry
    │                     │      (Max 3 attempts, 30s delay between)
    │                     │
    │                     └─ YES (SUCCESS):
    │                         │
    │                         ├─→ Update Local Database
    │                         │    UPDATE attendance
    │                         │    SET synced = 1,
    │                         │        sync_timestamp = NOW(),
    │                         │        cloud_record_id = "abc123..."
    │                         │    WHERE id = 123
    │                         │
    │                         ├─→ DELETE Local Photo
    │                         │    os.remove("photos/...")
    │                         │    └─ Free up disk space
    │                         │
    │                         ├─→ Print: "✓ CLOUD: Synced to Supabase"
    │                         │
    │                         └─→ Proceed to SMS
```

### PHASE 7: SMS PARENT NOTIFICATION

```
📱 SMS NOTIFICATION
    │
    ├─→ Is SMS Enabled?
    │    │
    │    ├─ NO: Skip SMS, proceed to SUCCESS
    │    │
    │    └─ YES: Continue
    │
    ├─→ Get Parent Contact Info
    │    │
    │    ├─ Query database:
    │    │  SELECT name, parent_phone
    │    │  FROM students
    │    │  WHERE student_id = "2021001"
    │    │
    │    └─ Result:
    │        {
    │          name: "John Doe",
    │          parent_phone: "+1-555-1234"
    │        }
    │
    ├─→ Has Parent Phone?
    │    │
    │    ├─ NO: 
    │    │  └─ Log: "No parent phone, skip SMS"
    │    │     └─ Proceed to SUCCESS
    │    │
    │    └─ YES: Continue
    │
    ├─→ Build Message
    │    │
    │    ├─ Template: "Attendance Alert: {student_name}
    │    │             (ID: {student_id}) checked in at
    │    │             {time} on {date}."
    │    │
    │    ├─ Substitute variables:
    │    │  ├─ {student_name}: "John Doe"
    │    │  ├─ {student_id}: "2021001"
    │    │  ├─ {time}: "02:30 PM"
    │    │  └─ {date}: "November 24, 2025"
    │    │
    │    └─ Final message:
    │        "Attendance Alert: John Doe (ID: 2021001)
    │         checked in at 02:30 PM on November 24, 2025."
    │
    ├─→ Send via SMS Gateway
    │    │
    │    ├─ API Endpoint: https://api.sms-gate.app/3rdparty/v1/message
    │    │
    │    ├─ HTTP Method: POST
    │    │
    │    ├─ Request Headers:
    │    │  └─ Authorization: Bearer [api_key]
    │    │
    │    ├─ Request Body:
    │    │  {
    │    │    "username": "EWW3VZ",
    │    │    "password": "ri9-rbprxdf2ph",
    │    │    "device_id": "zmmfTkL3NacdGAfNqwD7q",
    │    │    "recipient": "+1-555-1234",
    │    │    "message": "Attendance Alert: John Doe..."
    │    │  }
    │    │
    │    └─ Send request
    │        │
    │        └─→ SMS GATEWAY PROCESSES
    │            │
    │            ├─ Authenticate request
    │            ├─ Queue message
    │            ├─ Find device (Android phone)
    │            ├─ Route to mobile network
    │            └─ Deliver to parent's phone
    │
    ├─→ Check Response
    │    │
    │    ├─ Success?
    │    │  │
    │    │  ├─ YES:
    │    │  │  ├─→ Print: "📱 SMS sent to parent"
    │    │  │  └─→ Proceed to SUCCESS
    │    │  │
    │    │  └─ NO:
    │    │     ├─→ Log error
    │    │     ├─→ Retry in background (optional)
    │    │     ├─→ Print: "⚠️ SMS failed, will retry"
    │    │     └─→ Proceed to SUCCESS
    │    │        (Attendance still recorded!)
    │    │
    │    └─→ PARENT PHONE RECEIVES SMS
    │        │
    │        ├─ SMS alert notification
    │        ├─ Message display:
    │        │  "Attendance Alert: John Doe (ID: 2021001)
    │        │   checked in at 02:30 PM on November 24, 2025."
    │        │
    │        └─ Parent acknowledges
```

### PHASE 8: SUCCESS & RETURN TO STANDBY

```
✅ SUCCESS & RETURN TO STANDBY
    │
    ├─→ Audio Feedback
    │    └─ Buzzer: SUCCESS pattern
    │       └─ 200ms-100ms-200ms-100ms-200ms (melodic beep)
    │
    ├─→ Visual Feedback
    │    ├─ Display: "SUCCESS!"
    │    │           "Student: 2021001"
    │    │
    │    └─ Non-blocking display (1.5 seconds)
    │       └─ Message rendered on video frame
    │
    ├─→ Console Feedback
    │    ├─ Print: "✓ Attendance recorded successfully!"
    │    ├─ Print: "📊 Total today: 1 student(s)"
    │    │
    │    └─ Session statistics updated
    │
    ├─→ Increment Session Counter
    │    └─ self.session_count += 1
    │
    ├─→ Wait (Non-blocking)
    │    └─ Message displays for 1.5 seconds
    │       └─ Loop continues processing frames
    │
    ├─→ Clear Feedback Message
    │    └─ After 1.5 seconds, clear from display
    │
    ├─→ Return to STANDBY
    │    └─ Print: "🟢 STANDBY - Waiting for QR code scan..."
    │
    └─→ Loop Back to PHASE 2
        └─ Ready for next student
```

---

## Background Sync Thread Execution

```
BACKGROUND THREAD (Daemon - runs in parallel)
    │
    └─→ Initialization
        ├─ Start as daemon thread (won't block shutdown)
        └─ Log: "Background sync thread started"
    │
    └─→ Infinite Loop
        │
        ├─→ Sleep 60 seconds
        │    └─ Configurable via sync_interval
        │
        ├─→ Check Internet Connectivity
        │    └─ Is online?
        │
        ├─ Is OFFLINE?
        │  └─ Wait 60 seconds, try again
        │
        └─ Is ONLINE?
           │
           └─→ Process Sync Queue
               │
               ├─→ Query sync_queue table
               │    └─ Get unsynced records (max 10 at a time)
               │
               ├─→ For each queued record:
               │    │
               │    ├─→ Attempt Cloud Sync
               │    │    ├─ Upload photo to Supabase
               │    │    └─ Insert record to Supabase
               │    │
               │    ├─→ Is Successful?
               │    │    │
               │    │    ├─ YES:
               │    │    │  ├─ Update local DB: synced = 1
               │    │    │  ├─ Delete local photo
               │    │    │  └─ Remove from queue
               │    │    │
               │    │    └─ NO:
               │    │        │
               │    │        ├─ Increment retry_count
               │    │        │
               │    │        ├─ Has retry_count < 3?
               │    │        │  │
               │    │        │  ├─ YES: Keep in queue
               │    │        │  │       Wait 30 seconds
               │    │        │  │       Will retry next cycle
               │    │        │  │
               │    │        │  └─ NO: Mark as failed
               │    │        │        (manual intervention needed)
               │    │        │
               │    │        └─ Keep photo local
               │    │            (for eventual sync)
               │    │
               │    └─→ Log result
               │         "[X] succeeded, [Y] failed"
               │
               └─→ Wait 60 seconds
                   Loop again
```

---

## Complete Timing Example

```
08:30:00.001  QR detected            (instant)
08:30:00.100  Transition to CAPTURING
08:30:00.105  Buzzer beep             (5ms)
08:30:00.500  Face detected           (400ms later)
08:30:00.505  Buzzer beep             (5ms)
08:30:05.000  Capture window expires  (5 seconds)
08:30:05.100  Photo capture           (100ms)
08:30:05.200  Photo processing        (100ms)
08:30:05.300  Local DB insert         (100ms)
08:30:05.350  Cloud sync attempt      (50ms to start)
08:30:05.400  Photo upload            (50-200ms)
08:30:05.500  Record inserted         (50-100ms)
08:30:05.550  Local photo deleted     (5ms)
08:30:05.600  SMS message built       (10ms)
08:30:05.610  SMS gateway API call    (50-500ms)
08:30:06.100  SMS delivered           (varies)
08:30:06.110  Success display         (1.5 seconds)
08:30:07.610  Return to STANDBY       (instant)
08:30:07.611  Ready for next scan

TOTAL TIME: ~7.6 seconds (online)
TOTAL TIME: ~0.5 seconds (offline, local only)
```

---

This comprehensive execution flow diagram shows exactly how the IoT Attendance
System processes each student from QR scan through cloud sync and parent
notification. Every step is tracked, optimized, and resilient to failures.
