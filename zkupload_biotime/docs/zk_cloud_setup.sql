-- ================================================================
-- ZK BioTime Cloud Database Schema
-- ================================================================
-- Purpose: Create tables for syncing ZKBioTime attendance data
-- Source: Local ZKBioTime PostgreSQL (4 tables)
-- Destination: Cloud MySQL database
-- 
-- Tables:
--   1. departments - Department structure
--   2. employees - Employee master data
--   3. devices - Attendance devices
--   4. attendance_logs - Raw attendance punches
--
-- Usage: Run this script on your cloud MySQL database
-- ================================================================

-- Set character set and collation
SET NAMES utf8mb4;
SET COLLATION_CONNECTION = utf8mb4_unicode_ci;

-- ================================================================
-- Table 1: departments (from personnel_department)
-- ================================================================
-- Purpose: Store department structure for organizational grouping
-- Sync: Full sync daily (small table, typically < 100 records)
-- ================================================================

DROP TABLE IF EXISTS departments;

CREATE TABLE departments (
    id INT NOT NULL,
    dept_code VARCHAR(50) NOT NULL,
    dept_name VARCHAR(200) NOT NULL,
    parent_dept_id INT NULL,
    last_sync DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Primary key
    PRIMARY KEY (id),
    
    -- Indexes for performance
    INDEX idx_dept_code (dept_code),
    INDEX idx_parent_dept_id (parent_dept_id),
    
    -- Unique constraint on dept_code
    UNIQUE KEY unique_dept_code (dept_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ================================================================
-- Table 2: employees (from personnel_employee)
-- ================================================================
-- Purpose: Store employee master data for name and department lookup
-- Sync: Incremental by update_time or change_time
-- ================================================================

DROP TABLE IF EXISTS employees;

CREATE TABLE employees (
    id INT NOT NULL,
    emp_code VARCHAR(20) NOT NULL,
    first_name VARCHAR(100) NULL,
    last_name VARCHAR(100) NULL,
    display_name VARCHAR(100) NULL,
    department_id INT NULL,
    emp_type INT NULL,
    hire_date DATE NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    mobile VARCHAR(20) NULL,
    email VARCHAR(50) NULL,
    last_sync DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Primary key
    PRIMARY KEY (id),
    
    -- Indexes for performance
    INDEX idx_emp_code (emp_code),
    INDEX idx_department_id (department_id),
    INDEX idx_is_active (is_active),
    INDEX idx_emp_code_active (emp_code, is_active),
    
    -- Unique constraint on emp_code
    UNIQUE KEY unique_emp_code (emp_code)

    -- Foreign key to departments (optional, can be disabled if needed)
    -- CONSTRAINT fk_employee_department FOREIGN KEY (department_id) REFERENCES departments(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ================================================================
-- Table 3: devices (from iclock_terminal)
-- ================================================================
-- Purpose: Store device information for location and status tracking
-- Sync: Incremental by id
-- ================================================================

DROP TABLE IF EXISTS devices;

CREATE TABLE devices (
    id INT NOT NULL,
    terminal_sn VARCHAR(50) NOT NULL,
    terminal_alias VARCHAR(50) NOT NULL,
    ip_address VARCHAR(50) NULL,
    state INT NULL,
    is_attendance TINYINT(1) NULL,
    last_activity DATETIME NULL,
    last_sync DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Primary key
    PRIMARY KEY (id),
    
    -- Indexes for performance
    INDEX idx_terminal_sn (terminal_sn),
    INDEX idx_state (state),
    
    -- Unique constraint on terminal_sn
    UNIQUE KEY unique_terminal_sn (terminal_sn)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ================================================================
-- Table 4: attendance_logs (from iclock_transaction)
-- ================================================================
-- Purpose: Store raw attendance punches from devices
-- Sync: Incremental by id (most critical table, syncs frequently)
-- ================================================================

DROP TABLE IF EXISTS attendance_logs;

CREATE TABLE attendance_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    emp_code VARCHAR(20) NOT NULL,
    punch_time DATETIME NOT NULL,
    punch_state VARCHAR(5) NOT NULL,
    verify_type INT NOT NULL,
    terminal_sn VARCHAR(50) NOT NULL,
    terminal_alias VARCHAR(50) NULL,
    emp_id INT NULL,
    terminal_id INT NULL,
    server_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    source_device VARCHAR(50) DEFAULT 'zkbiotime',
    
    -- Indexes for performance
    INDEX idx_emp_code (emp_code),
    INDEX idx_punch_time (punch_time),
    INDEX idx_emp_time (emp_code, punch_time),
    INDEX idx_terminal_sn (terminal_sn),
    INDEX idx_emp_id (emp_id),
    INDEX idx_terminal_id (terminal_id),
    INDEX idx_server_time (server_time),
    
    -- Unique constraint to prevent duplicate uploads
    -- Same employee cannot have same punch_time from same device
    UNIQUE KEY unique_emp_punch (emp_code, punch_time, terminal_sn)

    -- Foreign keys (optional, can be enabled if referential integrity is needed)
    -- CONSTRAINT fk_attendance_employee FOREIGN KEY (emp_id) REFERENCES employees(id),
    -- CONSTRAINT fk_attendance_device FOREIGN KEY (terminal_id) REFERENCES devices(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ================================================================
-- Optional: Sync tracking table
-- ================================================================
-- Purpose: Track sync status for each table
-- Usage: Updated by sync application after each sync
-- ================================================================

DROP TABLE IF EXISTS sync_tracking;

CREATE TABLE sync_tracking (
    id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    last_sync_id INT NULL,
    last_sync_time DATETIME NULL,
    last_sync_timestamp DATETIME NULL,
    records_synced INT NULL,
    sync_status VARCHAR(20) DEFAULT 'pending',
    sync_error TEXT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_table_name (table_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Initialize sync tracking for all tables
INSERT INTO sync_tracking (table_name, last_sync_id, last_sync_time, records_synced, sync_status)
VALUES 
    ('departments', 0, NULL, 0, 'pending'),
    ('employees', 0, NULL, 0, 'pending'),
    ('devices', 0, NULL, 0, 'pending'),
    ('attendance_logs', 0, NULL, 0, 'pending')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- ================================================================
-- Optional: Views for common queries
-- ================================================================

-- View: Attendance with employee and device information
DROP VIEW IF EXISTS v_attendance_detail;

CREATE VIEW v_attendance_detail AS
SELECT 
    a.id AS attendance_id,
    a.emp_code,
    e.first_name,
    e.last_name,
    e.display_name,
    d.dept_name AS department,
    a.punch_time,
    a.punch_state,
    CASE a.punch_state
        WHEN '0' THEN 'Check-in'
        WHEN '1' THEN 'Check-out'
        WHEN '2' THEN 'Break-out'
        WHEN '3' THEN 'Break-in'
        WHEN '4' THEN 'OT-in'
        WHEN '5' THEN 'OT-out'
        ELSE 'Unknown'
    END AS punch_state_name,
    CASE a.verify_type
        WHEN 0 THEN 'Unknown'
        WHEN 1 THEN 'Fingerprint'
        WHEN 2 THEN 'Face'
        WHEN 3 THEN 'Card'
        WHEN 4 THEN 'Password'
        WHEN 5 THEN 'Mobile'
        ELSE 'Other'
    END AS verify_type_name,
    a.terminal_sn,
    a.terminal_alias,
    dev.ip_address AS device_ip,
    a.server_time,
    a.source_device
FROM attendance_logs a
LEFT JOIN employees e ON a.emp_id = e.id
LEFT JOIN departments d ON e.department_id = d.id
LEFT JOIN devices dev ON a.terminal_id = dev.id;

-- View: Active employees with department
DROP VIEW IF EXISTS v_employees_active;

CREATE VIEW v_employees_active AS
SELECT 
    e.id,
    e.emp_code,
    e.first_name,
    e.last_name,
    e.display_name,
    d.dept_name AS department,
    e.emp_type,
    e.hire_date,
    e.mobile,
    e.email,
    e.is_active
FROM employees e
LEFT JOIN departments d ON e.department_id = d.id
WHERE e.is_active = 1;

-- View: Device status
DROP VIEW IF EXISTS v_device_status;

CREATE VIEW v_device_status AS
SELECT 
    id,
    terminal_sn,
    terminal_alias,
    ip_address,
    CASE state
        WHEN 0 THEN 'Offline'
        WHEN 1 THEN 'Online'
        ELSE 'Unknown'
    END AS state_name,
    is_attendance,
    last_activity,
    TIMESTAMPDIFF(MINUTE, last_activity, NOW()) AS minutes_since_activity,
    last_sync
FROM devices;

-- ================================================================
-- Sample Queries for PHP Team
-- ================================================================

-- Get today's attendance
-- SELECT * FROM v_attendance_detail 
-- WHERE DATE(punch_time) = CURDATE() 
-- ORDER BY punch_time;

-- Get attendance for specific employee in date range
-- SELECT * FROM v_attendance_detail 
-- WHERE emp_code = 'EMP001' 
-- AND DATE(punch_time) BETWEEN '2026-03-01' AND '2026-03-31'
-- ORDER BY punch_time;

-- Get late arrivals (after 08:30)
-- SELECT * FROM v_attendance_detail 
-- WHERE punch_state = '0' 
-- AND TIME(punch_time) > '08:30:00'
-- ORDER BY punch_time;

-- Get early departures (before 17:30)
-- SELECT * FROM v_attendance_detail 
-- WHERE punch_state = '1' 
-- AND TIME(punch_time) < '17:30:00'
-- ORDER BY punch_time;

-- Count records by table
-- SELECT 'departments' AS table_name, COUNT(*) AS record_count FROM departments
-- UNION ALL
-- SELECT 'employees', COUNT(*) FROM employees
-- UNION ALL
-- SELECT 'devices', COUNT(*) FROM devices
-- UNION ALL
-- SELECT 'attendance_logs', COUNT(*) FROM attendance_logs;

-- ================================================================
-- Grant Permissions (adjust username as needed)
-- ================================================================
-- GRANT SELECT, INSERT, UPDATE ON departments TO 'your_cloud_user'@'%';
-- GRANT SELECT, INSERT, UPDATE ON employees TO 'your_cloud_user'@'%';
-- GRANT SELECT, INSERT, UPDATE ON devices TO 'your_cloud_user'@'%';
-- GRANT SELECT, INSERT, UPDATE ON attendance_logs TO 'your_cloud_user'@'%';
-- GRANT SELECT, INSERT, UPDATE ON sync_tracking TO 'your_cloud_user'@'%';

-- ================================================================
-- End of Schema
-- ================================================================
