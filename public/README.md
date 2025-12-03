# Public Attendance Viewer

This directory contains the public-facing attendance viewer that parents can access via SMS links.

## Files

- **view-attendance.html** - Standalone HTML page for viewing student attendance

## Features

- 📱 Mobile-friendly responsive design
- 🎨 Beautiful gradient interface
- 📊 Table view of last 30 attendance records
- 🔒 Secure client-side Supabase auth
- ✅ Color-coded status badges (Present/Late/Absent)
- 👤 Shows student name and grade level
- ⚡ Fast loading, no backend required

## Deployment

### Option 1: GitHub Pages (Recommended)

1. Push to GitHub repository
2. Go to Settings → Pages
3. Enable GitHub Pages
4. Source: Deploy from branch `main`
5. Directory: `/public` (or root)
6. Your URL will be: `https://cerjho.github.io/IoT-Attendance-System/view-attendance.html`

Update `config/config.json`:
```json
"attendance_view_url": "https://mabini-hs-attendance.vercel.app/Parents/?student_id={student_id}"
```

### Option 2: Supabase Storage

```bash
# Upload to Supabase Storage
1. Go to Supabase Dashboard → Storage
2. Create public bucket: "attendance-viewer"
3. Upload view-attendance.html
4. Copy public URL
5. Update config/config.json with the URL
```

### Option 3: Local Server (Testing)

```bash
# Simple Python server
cd public
python3 -m http.server 8080

# Access at: http://localhost:8080/view-attendance.html?student_id=233294
```

For production with local hosting, use ngrok or similar:
```bash
ngrok http 8080
# Use the ngrok URL in config
```

## Usage

Parents receive SMS with link:
```
📊 View full attendance:
https://your-domain.com/view-attendance.html?student_id=233294
```

Clicking the link shows:
- Student name and grade
- Last 30 attendance records
- Time in and time out
- Status (Present/Late/Absent)
- Formatted dates and times

## Configuration

The HTML file contains the Supabase configuration:
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Public anon key (safe for client-side)

These are embedded in the HTML file. If you change Supabase projects, update these values.

## Security

✅ **Safe Design:**
- Uses Supabase anon (public) key
- Protected by Row Level Security (RLS) policies
- Read-only access
- No sensitive operations
- Client-side only (no server required)

⚠️ **Note:** The anon key is safe to expose in client-side code. It only allows operations permitted by your RLS policies.

## Browser Compatibility

- ✅ Chrome/Edge (Desktop & Mobile)
- ✅ Firefox (Desktop & Mobile)
- ✅ Safari (Desktop & Mobile)
- ✅ Samsung Internet
- ✅ All modern browsers with ES6 support

## Troubleshooting

**Error: "No student ID provided"**
- Solution: Make sure URL includes `?student_id=XXXXX`

**Error: "Failed to load attendance"**
- Check Supabase URL and key in HTML file
- Verify RLS policy is enabled for public read access
- Check browser console for detailed error

**Empty records**
- Verify student has attendance records in database
- Check student_id matches exactly

## Customization

To customize the appearance, edit the `<style>` section in view-attendance.html:
- Colors: Update gradient colors and theme
- School name: Change in HTML content
- Table columns: Modify displayAttendance() function
- Date/time format: Update formatDate() and formatTime() functions

## Related Files

- `/config/config.json` - SMS message templates with attendance_view_url
- `/src/notifications/sms_notifier.py` - SMS sending logic
- `/scripts/deployment/enable_public_attendance_view.sql` - RLS policy
- `/docs/implementation/PUBLIC_ATTENDANCE_VIEW.md` - Full documentation
