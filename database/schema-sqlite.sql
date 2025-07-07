-- =====================================================
-- Attendance Management System Database Schema (SQLite)
-- Version: 1.0.0
-- Created: 2025-01-20
-- Description: SQLite-compatible database schema for attendance management
-- =====================================================

-- =====================================================
-- USERS TABLE
-- =====================================================
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    password_hash TEXT NOT NULL,
    original_password TEXT NOT NULL,
    name TEXT NOT NULL,
    employee_id INTEGER UNIQUE NOT NULL,
    roles TEXT NOT NULL,
    department TEXT NOT NULL,
    email TEXT UNIQUE,
    phone TEXT,
    is_active INTEGER DEFAULT 1,
    remember_token TEXT,
    remember_token_expires DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster lookups
CREATE INDEX idx_users_employee_id ON users(employee_id);
CREATE INDEX idx_users_department ON users(department);
CREATE INDEX idx_users_roles ON users(roles);
CREATE INDEX idx_users_email ON users(email);

-- =====================================================
-- DEPARTMENTS TABLE
-- =====================================================
CREATE TABLE departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    code TEXT UNIQUE NOT NULL,
    description TEXT,
    manager_id INTEGER REFERENCES users(id),
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create index for departments
CREATE INDEX idx_departments_code ON departments(code);
CREATE INDEX idx_departments_manager ON departments(manager_id);

-- =====================================================
-- ATTENDANCES TABLE
-- =====================================================
CREATE TABLE attendances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    check_in DATETIME,
    check_out DATETIME,
    date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    note TEXT,
    break_time REAL NOT NULL DEFAULT 1.0,
    is_holiday INTEGER NOT NULL DEFAULT 0,
    holiday_type TEXT,
    total_work_hours REAL,
    overtime_before_22 TEXT,
    overtime_after_22 TEXT,
    approved INTEGER DEFAULT 0,
    approved_by INTEGER REFERENCES users(id),
    approved_at DATETIME,
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

-- =====================================================
-- REQUESTS TABLE
-- =====================================================
CREATE TABLE requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    request_type TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    current_approver_id INTEGER REFERENCES users(id),
    step TEXT NOT NULL DEFAULT 'leader',
    reject_reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for requests
CREATE INDEX idx_requests_user_id ON requests(user_id);
CREATE INDEX idx_requests_status ON requests(status);
CREATE INDEX idx_requests_approver ON requests(current_approver_id);
CREATE INDEX idx_requests_type ON requests(request_type);
CREATE INDEX idx_requests_dates ON requests(start_date, end_date);

-- =====================================================
-- AUDIT LOGS TABLE
-- =====================================================
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    action TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id INTEGER,
    old_values TEXT,  -- JSON as TEXT in SQLite
    new_values TEXT,  -- JSON as TEXT in SQLite
    ip_address TEXT,
    user_agent TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for audit logs
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_table ON audit_logs(table_name);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_ip ON audit_logs(ip_address);

-- =====================================================
-- CONSTRAINTS
-- =====================================================

-- Add constraints for data integrity
-- Note: SQLite has limited constraint support, so we'll use CHECK constraints where possible

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
    COUNT(CASE WHEN a.approved = 0 THEN 1 END) as pending_records,
    AVG(a.total_work_hours) as avg_work_hours,
    SUM(CASE WHEN a.is_holiday = 1 THEN 1 ELSE 0 END) as holiday_days
FROM users u
LEFT JOIN attendances a ON u.id = a.user_id
WHERE u.is_active = 1
GROUP BY u.id, u.name, u.employee_id, u.department;

-- View for department statistics
CREATE VIEW department_stats AS
SELECT 
    d.name as department_name,
    d.code as department_code,
    COUNT(u.id) as total_employees,
    COUNT(CASE WHEN u.is_active = 1 THEN 1 END) as active_employees,
    AVG(CASE WHEN a.total_work_hours IS NOT NULL THEN a.total_work_hours END) as avg_work_hours
FROM departments d
LEFT JOIN users u ON d.id = u.department
LEFT JOIN attendances a ON u.id = a.user_id
WHERE d.is_active = 1
GROUP BY d.id, d.name, d.code; 