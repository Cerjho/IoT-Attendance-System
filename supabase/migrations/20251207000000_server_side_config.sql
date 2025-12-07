-- Server-Side Configuration Tables
-- These tables store configuration that was previously hardcoded in config.json

-- =====================================================
-- IoT Device Configuration
-- Stores device-specific settings (name, location, etc.)
-- =====================================================

-- Device location and metadata are already in iot_devices table
-- No additional table needed, but ensure these fields exist:
-- - device_id (unique identifier)
-- - device_name
-- - location (JSON: building, floor, room, description)
-- - section_id (links to teaching location)
-- - subject_id (current subject being taught)
-- - teaching_load_id (current teaching assignment)

COMMENT ON TABLE iot_devices IS 'Stores IoT device configuration including location and teaching assignments';

-- =====================================================
-- SMS Notification Templates
-- Stores customizable SMS message templates
-- =====================================================

CREATE TABLE IF NOT EXISTS sms_templates (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    template_name VARCHAR(50) UNIQUE NOT NULL,
    template_type VARCHAR(50) NOT NULL CHECK (template_type IN (
        'check_in', 'check_out', 'late_arrival', 'no_checkout',
        'absence_alert', 'schedule_violation', 'weekly_summary', 'monthly_summary'
    )),
    message_template TEXT NOT NULL,
    variables TEXT[], -- Array of variable names used in template
    is_active BOOLEAN DEFAULT TRUE,
    school_name VARCHAR(200) DEFAULT 'Mabini High School',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL
);

-- Default SMS templates
INSERT INTO sms_templates (template_name, template_type, message_template, variables, school_name) VALUES
(
    'Check-In Notification',
    'check_in',
    '📚 {school_name}

✅ CHECK-IN: {student_name}
🕐 {time} | {date}

View: {attendance_link}',
    ARRAY['school_name', 'student_name', 'time', 'date', 'attendance_link'],
    'MABINI HIGH SCHOOL'
),
(
    'Check-Out Notification',
    'check_out',
    '📚 {school_name}

🏁 CHECK-OUT: {student_name}
🕐 {time} | {date}

View: {attendance_link}',
    ARRAY['school_name', 'student_name', 'time', 'date', 'attendance_link'],
    'MABINI HIGH SCHOOL'
),
(
    'Late Arrival Alert',
    'late_arrival',
    '⚠️ LATE ARRIVAL

{student_name} checked in at {time}
({minutes_late} mins late)
📅 {date}

View: {attendance_link}

- {school_name}',
    ARRAY['student_name', 'time', 'minutes_late', 'date', 'attendance_link', 'school_name'],
    'Mabini High School'
),
(
    'No Check-Out Alert',
    'no_checkout',
    '⚠️ NO CHECK-OUT

{student_name} did not check out today.
Last seen: {last_checkin_time}

Please verify.

View: {attendance_link}

- {school_name}',
    ARRAY['student_name', 'last_checkin_time', 'attendance_link', 'school_name'],
    'Mabini High School'
),
(
    'Absence Alert',
    'absence_alert',
    '❗ ABSENCE ALERT

{student_name} not detected at school today ({date}).

If excused, please contact office.

View: {attendance_link}

- {school_name}',
    ARRAY['student_name', 'date', 'attendance_link', 'school_name'],
    'Mabini High School'
),
(
    'Schedule Violation',
    'schedule_violation',
    '❌ SCHEDULE VIOLATION

{student_name}
Assigned: {allowed_session} class
Attempted: {current_session} scan
📅 {date} at {time}

Scan rejected. Please check schedule.

- {school_name}',
    ARRAY['student_name', 'allowed_session', 'current_session', 'date', 'time', 'school_name'],
    'Mabini High School'
),
(
    'Weekly Summary',
    'weekly_summary',
    '📊 WEEKLY SUMMARY

{student_name}
Present: {days_present}/{total_days}
Late: {late_count}
Absent: {absent_count}

View: {attendance_link}

- {school_name}',
    ARRAY['student_name', 'days_present', 'total_days', 'late_count', 'absent_count', 'attendance_link', 'school_name'],
    'Mabini High School'
),
(
    'Monthly Summary',
    'monthly_summary',
    '📊 MONTHLY SUMMARY

{student_name}
Present: {days_present}/{total_days} ({percentage}%)
Late: {late_count} times
Absent: {absent_count} days

View: {attendance_link}

- {school_name}',
    ARRAY['student_name', 'days_present', 'total_days', 'percentage', 'late_count', 'absent_count', 'attendance_link', 'school_name'],
    'Mabini High School'
)
ON CONFLICT (template_name) DO NOTHING;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_sms_templates_type ON sms_templates(template_type);
CREATE INDEX IF NOT EXISTS idx_sms_templates_active ON sms_templates(is_active);

-- =====================================================
-- Notification Preferences
-- Stores per-parent notification settings
-- =====================================================

CREATE TABLE IF NOT EXISTS notification_preferences (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    parent_phone VARCHAR(20) NOT NULL,
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    check_in_enabled BOOLEAN DEFAULT TRUE,
    check_out_enabled BOOLEAN DEFAULT TRUE,
    late_arrival_enabled BOOLEAN DEFAULT TRUE,
    no_checkout_enabled BOOLEAN DEFAULT FALSE,
    absence_alert_enabled BOOLEAN DEFAULT FALSE,
    schedule_violation_enabled BOOLEAN DEFAULT FALSE,
    weekly_summary_enabled BOOLEAN DEFAULT FALSE,
    monthly_summary_enabled BOOLEAN DEFAULT FALSE,
    quiet_hours_start TIME DEFAULT '22:00:00',
    quiet_hours_end TIME DEFAULT '06:00:00',
    quiet_hours_enabled BOOLEAN DEFAULT TRUE,
    unsubscribed BOOLEAN DEFAULT FALSE,
    unsubscribed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(parent_phone, student_id)
);

CREATE INDEX IF NOT EXISTS idx_notification_prefs_phone ON notification_preferences(parent_phone);
CREATE INDEX IF NOT EXISTS idx_notification_prefs_student ON notification_preferences(student_id);
CREATE INDEX IF NOT EXISTS idx_notification_prefs_unsubscribed ON notification_preferences(unsubscribed);

-- =====================================================
-- RLS Policies
-- =====================================================

-- SMS Templates (read-only for authenticated users)
ALTER TABLE sms_templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "SMS templates are viewable by authenticated users"
ON sms_templates FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "SMS templates are viewable by anon users"
ON sms_templates FOR SELECT
TO anon
USING (is_active = true);

-- Notification Preferences (parents can manage their own)
ALTER TABLE notification_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Parents can view their own notification preferences"
ON notification_preferences FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "Parents can update their own notification preferences"
ON notification_preferences FOR UPDATE
TO authenticated
USING (true);

-- =====================================================
-- Helper Functions
-- =====================================================

-- Function to get SMS template by type
CREATE OR REPLACE FUNCTION get_sms_template(template_type_param VARCHAR)
RETURNS TABLE (
    template_name VARCHAR,
    message_template TEXT,
    variables TEXT[],
    school_name VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.template_name,
        t.message_template,
        t.variables,
        t.school_name
    FROM sms_templates t
    WHERE t.template_type = template_type_param
      AND t.is_active = true
    LIMIT 1;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to check if notification should be sent
CREATE OR REPLACE FUNCTION should_send_notification(
    phone_param VARCHAR,
    student_id_param UUID,
    notification_type VARCHAR
)
RETURNS BOOLEAN AS $$
DECLARE
    prefs notification_preferences;
    check_time TIME;
BEGIN
    -- Get preferences
    SELECT * INTO prefs
    FROM notification_preferences
    WHERE parent_phone = phone_param
      AND student_id = student_id_param
    LIMIT 1;
    
    -- If no preferences, use defaults (all enabled except advanced features)
    IF prefs IS NULL THEN
        RETURN notification_type IN ('check_in', 'check_out', 'late_arrival');
    END IF;
    
    -- Check if unsubscribed
    IF prefs.unsubscribed THEN
        RETURN FALSE;
    END IF;
    
    -- Check quiet hours
    IF prefs.quiet_hours_enabled THEN
        check_time := CURRENT_TIME;
        IF prefs.quiet_hours_start > prefs.quiet_hours_end THEN
            -- Crosses midnight
            IF check_time >= prefs.quiet_hours_start OR check_time <= prefs.quiet_hours_end THEN
                RETURN FALSE;
            END IF;
        ELSE
            -- Same day
            IF check_time >= prefs.quiet_hours_start AND check_time <= prefs.quiet_hours_end THEN
                RETURN FALSE;
            END IF;
        END IF;
    END IF;
    
    -- Check specific notification type
    RETURN CASE notification_type
        WHEN 'check_in' THEN prefs.check_in_enabled
        WHEN 'check_out' THEN prefs.check_out_enabled
        WHEN 'late_arrival' THEN prefs.late_arrival_enabled
        WHEN 'no_checkout' THEN prefs.no_checkout_enabled
        WHEN 'absence_alert' THEN prefs.absence_alert_enabled
        WHEN 'schedule_violation' THEN prefs.schedule_violation_enabled
        WHEN 'weekly_summary' THEN prefs.weekly_summary_enabled
        WHEN 'monthly_summary' THEN prefs.monthly_summary_enabled
        ELSE FALSE
    END;
END;
$$ LANGUAGE plpgsql STABLE;

-- =====================================================
-- Comments
-- =====================================================

COMMENT ON TABLE sms_templates IS 'Stores customizable SMS notification templates';
COMMENT ON TABLE notification_preferences IS 'Per-parent notification preferences including quiet hours and unsubscribe';
COMMENT ON FUNCTION get_sms_template IS 'Retrieves active SMS template by type';
COMMENT ON FUNCTION should_send_notification IS 'Checks if notification should be sent based on preferences and quiet hours';

-- =====================================================
-- Migration Notes
-- =====================================================

-- This migration moves the following from config.json to database:
-- 1. school_schedule → school_schedules table (already exists)
-- 2. SMS templates → sms_templates table (NEW)
-- 3. Notification preferences → notification_preferences table (NEW)
-- 4. Device metadata → iot_devices table (already exists)
--
-- Benefits:
-- - Centralized configuration management
-- - No need to edit local config files
-- - Per-parent notification customization
-- - Template management via admin dashboard
-- - Dynamic updates without system restart
