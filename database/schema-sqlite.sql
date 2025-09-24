-- =====================================================
-- Enhanced Attendance Management System Database Schema (SQLite)
-- Version: 2.0.0
-- Created: 2025-01-20
-- Description: SQLite-compatible database schema with improved security and performance
-- =====================================================

-- =====================================================
-- USERS TABLE
-- =====================================================
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL CHECK (length(name) >= 2 AND length(name) <= 100),
    employee_id INTEGER UNIQUE NOT NULL CHECK (employee_id >= 1 AND employee_id <= 999999),
    roles TEXT NOT NULL CHECK (roles IN ('EMPLOYEE', 'TEAM_LEADER', 'MANAGER', 'ADMIN') OR roles LIKE '%,%'),
    department TEXT NOT NULL CHECK (length(department) >= 2 AND length(department) <= 50),
    email TEXT UNIQUE CHECK (email IS NULL OR (length(email) >= 5 AND email LIKE '%@%.%')),
    phone TEXT CHECK (phone IS NULL OR (length(phone) >= 10 AND phone LIKE '0%')),
    is_active INTEGER DEFAULT 1 CHECK (is_active IN (0, 1)),
    remember_token TEXT,
    remember_token_expires DATETIME,
    personal_signature TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for faster lookups
CREATE INDEX idx_users_employee_id ON users(employee_id);
CREATE INDEX idx_users_department ON users(department);
CREATE INDEX idx_users_roles ON users(roles);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_remember_token ON users(remember_token);

-- =====================================================
-- DEPARTMENTS TABLE
-- =====================================================
CREATE TABLE departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL CHECK (length(name) >= 2 AND length(name) <= 50),
    code TEXT UNIQUE NOT NULL CHECK (length(code) >= 2 AND length(code) <= 10),
    description TEXT CHECK (description IS NULL OR length(description) <= 500),
    manager_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    is_active INTEGER DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create index for departments
CREATE INDEX idx_departments_code ON departments(code);
CREATE INDEX idx_departments_manager ON departments(manager_id);
CREATE INDEX idx_departments_is_active ON departments(is_active);

-- =====================================================
-- ATTENDANCES TABLE
-- =====================================================
CREATE TABLE attendances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    check_in DATETIME,
    check_out DATETIME,
    date DATE NOT NULL CHECK (date <= date('now')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    note TEXT CHECK (note IS NULL OR length(note) <= 1000),
    break_time REAL NOT NULL DEFAULT 1.0 CHECK (break_time >= 0 AND break_time <= 8),
    overtime_comp_time REAL NOT NULL DEFAULT 0.0 CHECK (overtime_comp_time >= 0 AND overtime_comp_time <= 8),
    is_holiday INTEGER NOT NULL DEFAULT 0 CHECK (is_holiday IN (0, 1)),
    holiday_type TEXT CHECK (holiday_type IN ('normal', 'weekend', 'vietnamese_holiday', 'japanese_holiday')),
    total_work_hours REAL CHECK (total_work_hours IS NULL OR (total_work_hours >= 0 AND total_work_hours <= 24)),
    regular_work_hours REAL CHECK (regular_work_hours IS NULL OR (regular_work_hours >= 0 AND regular_work_hours <= 8)),
    overtime_before_22 TEXT CHECK (overtime_before_22 IS NULL OR overtime_before_22 LIKE '%:%'),
    overtime_after_22 TEXT CHECK (overtime_after_22 IS NULL OR overtime_after_22 LIKE '%:%'),
    approved INTEGER DEFAULT 0 CHECK (approved IN (0, 1)),
    approved_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    approved_at DATETIME,
    shift_code TEXT CHECK (shift_code IS NULL OR length(shift_code) <= 10),
    shift_start TIME,
    shift_end TIME,
    signature TEXT,
    team_leader_signature TEXT,
    manager_signature TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for attendances
CREATE INDEX idx_attendances_user_id ON attendances(user_id);
CREATE INDEX idx_attendances_date ON attendances(date);
CREATE INDEX idx_attendances_status ON attendances(status);
CREATE INDEX idx_attendances_approved ON attendances(approved);
CREATE INDEX idx_attendances_user_date ON attendances(user_id, date);
CREATE INDEX idx_attendances_holiday_type ON attendances(holiday_type);
CREATE INDEX idx_attendances_approved_by ON attendances(approved_by);
CREATE INDEX idx_attendances_shift_code ON attendances(shift_code);
CREATE INDEX idx_attendances_created_at ON attendances(created_at);

-- =====================================================
-- REQUESTS TABLE
-- =====================================================
CREATE TABLE requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    request_type TEXT NOT NULL CHECK (length(request_type) >= 2 AND length(request_type) <= 50),
    start_date DATE NOT NULL CHECK (start_date >= date('now')),
    end_date DATE NOT NULL CHECK (end_date >= start_date),
    reason TEXT NOT NULL CHECK (length(reason) >= 10 AND length(reason) <= 500),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    current_approver_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    step TEXT NOT NULL DEFAULT 'leader' CHECK (step IN ('leader', 'manager', 'admin')),
    reject_reason TEXT CHECK (reject_reason IS NULL OR length(reject_reason) <= 500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for requests
CREATE INDEX idx_requests_user_id ON requests(user_id);
CREATE INDEX idx_requests_status ON requests(status);
CREATE INDEX idx_requests_approver ON requests(current_approver_id);
CREATE INDEX idx_requests_type ON requests(request_type);
CREATE INDEX idx_requests_dates ON requests(start_date, end_date);
CREATE INDEX idx_requests_step ON requests(step);
CREATE INDEX idx_requests_created_at ON requests(created_at);

-- =====================================================
-- AUDIT LOGS TABLE
-- =====================================================
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL CHECK (length(action) >= 2 AND length(action) <= 50),
    table_name TEXT NOT NULL CHECK (length(table_name) >= 2 AND length(table_name) <= 50),
    record_id INTEGER,
    old_values TEXT,  -- JSON as TEXT in SQLite
    new_values TEXT,  -- JSON as TEXT in SQLite
    ip_address TEXT CHECK (ip_address IS NULL OR length(ip_address) <= 45),
    user_agent TEXT CHECK (user_agent IS NULL OR length(user_agent) <= 1000),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for audit logs
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_table ON audit_logs(table_name);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_ip ON audit_logs(ip_address);
CREATE INDEX idx_audit_logs_record_id ON audit_logs(record_id);

-- =====================================================
-- PASSWORD RESET TOKENS TABLE
-- =====================================================
CREATE TABLE password_reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL CHECK (length(token) >= 32),
    expires_at DATETIME NOT NULL CHECK (expires_at > datetime('now')),
    used INTEGER DEFAULT 0 CHECK (used IN (0, 1)),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for password reset tokens
CREATE INDEX idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);
CREATE INDEX idx_password_reset_tokens_token ON password_reset_tokens(token);
CREATE INDEX idx_password_reset_tokens_expires_at ON password_reset_tokens(expires_at);
CREATE INDEX idx_password_reset_tokens_used ON password_reset_tokens(used);

-- =====================================================
-- RATE LIMITING TABLE (for persistent rate limiting)
-- =====================================================
CREATE TABLE rate_limits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_ip TEXT NOT NULL CHECK (length(client_ip) <= 45),
    endpoint TEXT NOT NULL CHECK (length(endpoint) <= 100),
    request_count INTEGER DEFAULT 1 CHECK (request_count >= 0),
    window_start DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for rate limiting
CREATE INDEX idx_rate_limits_client_endpoint ON rate_limits(client_ip, endpoint);
CREATE INDEX idx_rate_limits_window_start ON rate_limits(window_start);

-- =====================================================
-- VIEWS FOR COMMON QUERIES
-- =====================================================

-- View for user attendance summary
CREATE VIEW user_attendance_summary AS
SELECT 
    u.id,
    u.name,
    u.employee_id,
    u.department,
    COUNT(a.id) as total_records,
    COUNT(CASE WHEN a.approved = 1 THEN 1 END) as approved_records,
    COUNT(CASE WHEN a.approved = 0 AND a.status = 'pending' THEN 1 END) as pending_records,
    COUNT(CASE WHEN a.status = 'rejected' THEN 1 END) as rejected_records,
    AVG(a.total_work_hours) as avg_work_hours,
    SUM(CASE WHEN a.is_holiday = 1 THEN 1 ELSE 0 END) as holiday_days,
    MAX(a.updated_at) as last_attendance
FROM users u
LEFT JOIN attendances a ON u.id = a.user_id
WHERE u.is_active = 1
GROUP BY u.id, u.name, u.employee_id, u.department;

-- View for department statistics
CREATE VIEW department_statistics AS
SELECT 
    d.id,
    d.name,
    d.code,
    COUNT(u.id) as total_employees,
    COUNT(CASE WHEN u.is_active = 1 THEN 1 END) as active_employees,
    AVG(CASE WHEN a.total_work_hours IS NOT NULL THEN a.total_work_hours END) as avg_work_hours,
    COUNT(CASE WHEN a.is_holiday = 1 THEN 1 END) as total_holiday_days
FROM departments d
LEFT JOIN users u ON d.id = u.department
LEFT JOIN attendances a ON u.id = a.user_id
WHERE d.is_active = 1
GROUP BY d.id, d.name, d.code;

-- View for recent audit activities
CREATE VIEW recent_audit_activities AS
SELECT 
    al.id,
    al.action,
    al.table_name,
    al.record_id,
    u.name as user_name,
    u.employee_id,
    al.ip_address,
    al.created_at
FROM audit_logs al
LEFT JOIN users u ON al.user_id = u.id
WHERE al.created_at >= datetime('now', '-7 days')
ORDER BY al.created_at DESC;

-- =====================================================
-- TRIGGERS FOR DATA INTEGRITY
-- =====================================================

-- Trigger to update updated_at timestamp
CREATE TRIGGER update_users_updated_at
    AFTER UPDATE ON users
    FOR EACH ROW
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER update_attendances_updated_at
    AFTER UPDATE ON attendances
    FOR EACH ROW
BEGIN
    UPDATE attendances SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER update_requests_updated_at
    AFTER UPDATE ON requests
    FOR EACH ROW
BEGIN
    UPDATE requests SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER update_departments_updated_at
    AFTER UPDATE ON departments
    FOR EACH ROW
BEGIN
    UPDATE departments SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Trigger to validate attendance time logic
CREATE TRIGGER validate_attendance_times
    BEFORE INSERT ON attendances
    FOR EACH ROW
BEGIN
    SELECT CASE 
        WHEN NEW.check_in IS NOT NULL AND NEW.check_out IS NOT NULL 
             AND NEW.check_in >= NEW.check_out
        THEN RAISE(ABORT, 'Check-in time must be before check-out time')
    END;
END;

-- Trigger to validate request date logic
CREATE TRIGGER validate_request_dates
    BEFORE INSERT ON requests
    FOR EACH ROW
BEGIN
    SELECT CASE 
        WHEN NEW.start_date > NEW.end_date
        THEN RAISE(ABORT, 'Start date must be before or equal to end date')
    END;
END;

-- Trigger to clean up expired password reset tokens
CREATE TRIGGER cleanup_expired_tokens
    AFTER INSERT ON password_reset_tokens
    FOR EACH ROW
BEGIN
    DELETE FROM password_reset_tokens 
    WHERE expires_at < datetime('now') OR used = 1;
END;

-- Trigger to clean up old rate limit records
CREATE TRIGGER cleanup_old_rate_limits
    AFTER INSERT ON rate_limits
    FOR EACH ROW
BEGIN
    DELETE FROM rate_limits 
    WHERE window_start < datetime('now', '-1 hour');
END;

-- =====================================================
-- INITIAL DATA (OPTIONAL)
-- =====================================================

-- Insert default departments
INSERT OR IGNORE INTO departments (name, code, description) VALUES 
('Information Technology', 'IT', 'IT Department'),
('Human Resources', 'HR', 'Human Resources Department'),
('Finance', 'FIN', 'Finance Department'),
('Operations', 'OPS', 'Operations Department');

-- Insert default admin user (password: admin123)
INSERT OR IGNORE INTO users (employee_id, name, password_hash, roles, department, email, is_active) VALUES 
(1, 'System Administrator', 'pbkdf2:sha256:600000$admin123', 'ADMIN', 'Information Technology', 'admin@company.com', 1); 