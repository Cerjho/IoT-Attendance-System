# Public Attendance View

This directory contains the public-facing attendance view page for the IoT Attendance System.

## Files

- **index.html** - Redirects to view-attendance.html
- **view-attendance.html** - Student attendance viewer (no login required)

## GitHub Pages Setup

This directory is configured to be served via GitHub Pages at:
https://cerjho.github.io/IoT-Attendance-System/

### Enable GitHub Pages

1. Go to repository Settings
2. Navigate to "Pages" section
3. Under "Source", select:
   - Branch: `main`
   - Folder: `/docs`
4. Click Save

The page will be live at: https://cerjho.github.io/IoT-Attendance-System/view-attendance.html

## Usage

Students and parents can view attendance records by visiting:
```
https://cerjho.github.io/IoT-Attendance-System/view-attendance.html?student_id=STUDENT_ID
```

Replace `STUDENT_ID` with the actual student ID (e.g., 2021001, 233294, etc.)

## SMS Integration

The SMS notification system includes this URL, so parents receive a direct link to view their child's attendance.

Example SMS message includes:
```
📊 View full attendance:
https://cerjho.github.io/IoT-Attendance-System/view-attendance.html?student_id=2021001
```

## Features

- ✅ No login required
- ✅ Works on any device (mobile, tablet, desktop)
- ✅ Real-time data from Supabase
- ✅ Clean, modern interface
- ✅ Shows attendance history, statistics, and calendar view
