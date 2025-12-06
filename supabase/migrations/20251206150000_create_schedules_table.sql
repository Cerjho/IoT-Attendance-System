-- =====================================================
-- SCHOOL SCHEDULES TABLE
-- =====================================================
-- Stores school-wide class schedules (morning/afternoon sessions)
-- Each schedule can be assigned to sections or used as default

CREATE TABLE IF NOT EXISTS school_schedules (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Morning session
    morning_start_time TIME NOT NULL DEFAULT '07:00:00',
    morning_end_time TIME NOT NULL DEFAULT '12:00:00',
    morning_login_window_start TIME NOT NULL DEFAULT '06:30:00',
    morning_login_window_end TIME NOT NULL DEFAULT '07:30:00',
    morning_logout_window_start TIME NOT NULL DEFAULT '11:30:00',
    morning_logout_window_end TIME NOT NULL DEFAULT '12:30:00',
    morning_late_threshold_minutes INTEGER NOT NULL DEFAULT 15,
    
    -- Afternoon session
    afternoon_start_time TIME NOT NULL DEFAULT '13:00:00',
    afternoon_end_time TIME NOT NULL DEFAULT '17:00:00',
    afternoon_login_window_start TIME NOT NULL DEFAULT '12:30:00',
    afternoon_login_window_end TIME NOT NULL DEFAULT '13:30:00',
    afternoon_logout_window_start TIME NOT NULL DEFAULT '16:30:00',
    afternoon_logout_window_end TIME NOT NULL DEFAULT '17:30:00',
    afternoon_late_threshold_minutes INTEGER NOT NULL DEFAULT 15,
    
    -- Schedule settings
    auto_detect_session BOOLEAN DEFAULT TRUE,
    allow_early_arrival BOOLEAN DEFAULT TRUE,
    require_logout BOOLEAN DEFAULT TRUE,
    duplicate_scan_cooldown_minutes INTEGER DEFAULT 5,
    
    -- Day of week filters (for future use)
    apply_monday BOOLEAN DEFAULT TRUE,
    apply_tuesday BOOLEAN DEFAULT TRUE,
    apply_wednesday BOOLEAN DEFAULT TRUE,
    apply_thursday BOOLEAN DEFAULT TRUE,
    apply_friday BOOLEAN DEFAULT TRUE,
    apply_saturday BOOLEAN DEFAULT FALSE,
    apply_sunday BOOLEAN DEFAULT FALSE,
    
    -- Schedule status
    is_default BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX idx_school_schedules_status ON school_schedules(status);
CREATE INDEX idx_school_schedules_is_default ON school_schedules(is_default);

-- Ensure only one default schedule
CREATE UNIQUE INDEX idx_school_schedules_single_default 
    ON school_schedules(is_default) 
    WHERE is_default = TRUE AND status = 'active';

-- Add schedule_id to sections table
ALTER TABLE sections 
ADD COLUMN IF NOT EXISTS schedule_id UUID REFERENCES school_schedules(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_sections_schedule_id ON sections(schedule_id);

-- =====================================================
-- Insert default schedule
-- =====================================================
INSERT INTO school_schedules (
    name,
    description,
    is_default,
    status
) VALUES (
    'Standard Schedule',
    'Default school schedule for regular classes',
    TRUE,
    'active'
) ON CONFLICT DO NOTHING;

-- =====================================================
-- Enable RLS
-- =====================================================
ALTER TABLE school_schedules ENABLE ROW LEVEL SECURITY;

-- Policy: Allow anon/authenticated read access (for IoT devices)
CREATE POLICY "Allow read access to active schedules"
    ON school_schedules
    FOR SELECT
    USING (status = 'active');

-- Policy: Allow service_role full access
CREATE POLICY "Allow service role full access to schedules"
    ON school_schedules
    FOR ALL
    USING (auth.role() = 'service_role');

-- =====================================================
-- Update function for updated_at
-- =====================================================
CREATE OR REPLACE FUNCTION update_school_schedules_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER school_schedules_updated_at
    BEFORE UPDATE ON school_schedules
    FOR EACH ROW
    EXECUTE FUNCTION update_school_schedules_updated_at();

-- =====================================================
-- Comments
-- =====================================================
COMMENT ON TABLE school_schedules IS 'School-wide class schedules with morning and afternoon sessions';
COMMENT ON COLUMN school_schedules.is_default IS 'Default schedule used when section has no specific schedule';
COMMENT ON COLUMN school_schedules.auto_detect_session IS 'Automatically detect morning/afternoon session based on time';
COMMENT ON COLUMN school_schedules.morning_late_threshold_minutes IS 'Minutes after class start to mark as late';
