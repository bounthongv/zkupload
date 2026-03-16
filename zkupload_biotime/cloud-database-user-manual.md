# Cloud Database User Manual

## For: Salary & Payment Web Application Developers

**Database:** ZK BioTime Attendance Cloud Database  
**Version:** 2.0  
**Last Updated:** 2026-03-14

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Database Connection](#database-connection)
3. [Database Schema](#database-schema)
4. [Table Descriptions](#table-descriptions)
5. [Common Queries](#common-queries)
6. [Salary Calculation Examples](#salary-calculation-examples)
7. [API Integration Guide](#api-integration-guide)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Overview

### Purpose

This cloud database contains synchronized attendance data from ZKBioTime system for use in salary and payment calculations.

### Data Flow

```
ZK Attendance Device
        ↓
ZKBioTime (PostgreSQL)
        ↓ (Sync every 4 hours)
Cloud MySQL Database ← YOUR WEB APP HERE
        ↓
Salary Calculation
```

### Sync Schedule

| Table | Sync Frequency | Freshness |
|-------|---------------|-----------|
| **attendance_logs** | Every 4 hours | 09:00, 12:00, 17:00, 22:00 |
| **employees** | Every 6 hours | 01:00, 07:00, 13:00, 19:00 |
| **departments** | Daily | 01:00 |
| **devices** | Daily | 02:00 |

**Note:** Data is typically 0-4 hours old depending on sync time.

---

## Database Connection

### Connection Parameters

```php
// PHP PDO Example
$host = 'YOUR_CLOUD_HOST';
$port = '3306';
$database = 'YOUR_DATABASE_NAME';
$username = 'YOUR_USERNAME';
$password = 'YOUR_PASSWORD';

try {
    $pdo = new PDO(
        "mysql:host=$host;port=$port;dbname=$database;charset=utf8mb4",
        $username,
        $password,
        [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false
        ]
    );
} catch (PDOException $e) {
    error_log("Connection failed: " . $e->getMessage());
    die("Database connection failed");
}
```

### Connection String Formats

**PHP PDO:**
```
mysql:host=HOST;port=3306;dbname=DB;charset=utf8mb4
```

**Node.js (mysql2):**
```javascript
{
  host: 'HOST',
  port: 3306,
  database: 'DB',
  user: 'USER',
  password: 'PASS',
  charset: 'utf8mb4'
}
```

**Python (pymysql):**
```python
{
  'host': 'HOST',
  'port': 3306,
  'database': 'DB',
  'user': 'USER',
  'password': 'PASS',
  'charset': 'utf8mb4'
}
```

**Java (JDBC):**
```
jdbc:mysql://HOST:3306/DB?useSSL=true&serverTimezone=UTC&characterEncoding=utf8
```

---

## Database Schema

### Tables Overview

```
┌─────────────────────┐
│ departments         │ ← Department structure
├─────────────────────┤
│ employees           │ ← Employee master data
├─────────────────────┤
│ devices             │ ← Attendance devices
├─────────────────────┤
│ attendance_logs     │ ← Raw attendance punches (MAIN TABLE)
├─────────────────────┤
│ sync_tracking       │ ← Sync status monitoring
└─────────────────────┘

Views (Pre-defined Queries):
- v_attendance_detail
- v_employees_active
- v_device_status
```

---

## Table Descriptions

### 1. attendance_logs (MAIN TABLE)

**Purpose:** Raw attendance punches from devices

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `id` | INT | Primary key | 12345 |
| `emp_code` | VARCHAR(20) | Employee ID | 'EMP001' |
| `punch_time` | DATETIME | Attendance timestamp | '2026-03-14 08:30:00' |
| `punch_state` | VARCHAR(5) | IN/OUT status | '0'=IN, '1'=OUT |
| `verify_type` | INT | Verification method | 1=Fingerprint, 2=Face |
| `terminal_sn` | VARCHAR(50) | Device serial | 'ZK12345' |
| `terminal_alias` | VARCHAR(50) | Device location | 'Office', 'Warehouse' |
| `emp_id` | INT | Employee internal ID | 42 |
| `terminal_id` | INT | Device internal ID | 1 |
| `server_time` | DATETIME | When uploaded to cloud | '2026-03-14 09:00:00' |
| `source_device` | VARCHAR(50) | Source system | 'zkbiotime' |

**Punch State Values:**

| Code | Meaning | Use Case |
|------|---------|----------|
| '0' | Check-in | Calculate work start time |
| '1' | Check-out | Calculate work end time |
| '2' | Break-out | Track break start |
| '3' | Break-in | Track break end |
| '4' | OT-in | Overtime start |
| '5' | OT-out | Overtime end |

**Verify Type Values:**

| Code | Method |
|------|--------|
| 0 | Unknown |
| 1 | Fingerprint |
| 2 | Face Recognition |
| 3 | RFID Card |
| 4 | Password |
| 5 | Mobile App |

**Indexes:**
- `idx_emp_code` - Fast lookup by employee
- `idx_punch_time` - Fast date range queries
- `idx_emp_time` - Fast employee + date queries
- `unique_emp_punch` - Prevents duplicates (emp_code, punch_time, terminal_sn)

---

### 2. employees

**Purpose:** Employee master data

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `id` | INT | Employee internal ID | 42 |
| `emp_code` | VARCHAR(20) | Employee identifier (unique) | 'EMP001' |
| `first_name` | VARCHAR(100) | Given name | 'Bounthong' |
| `last_name` | VARCHAR(100) | Family name | 'Vilaychit' |
| `display_name` | VARCHAR(100) | Nickname/preferred name | 'Boun' |
| `department_id` | INT | FK to departments | 5 |
| `emp_type` | INT | Employee type | 1=Full-time, 2=Part-time |
| `hire_date` | DATE | Date of hiring | '2025-01-15' |
| `is_active` | BOOLEAN | Active status | 1=Active, 0=Inactive |
| `mobile` | VARCHAR(20) | Contact number | '+856 20 XXXX XXXX' |
| `email` | VARCHAR(50) | Email address | 'boun@example.com' |
| `last_sync` | DATETIME | Last sync time | '2026-03-14 07:00:00' |

**Indexes:**
- `idx_emp_code` - Fast employee lookup
- `idx_department_id` - Fast department filtering
- `idx_is_active` - Filter active employees
- `unique_emp_code` - Unique employee code

---

### 3. departments

**Purpose:** Department/organizational structure

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `id` | INT | Department ID | 5 |
| `dept_code` | VARCHAR(50) | Department code (unique) | 'IT' |
| `dept_name` | VARCHAR(200) | Department name | 'Information Technology' |
| `parent_dept_id` | INT | Parent department (hierarchy) | 1 |
| `last_sync` | DATETIME | Last sync time | '2026-03-14 01:00:00' |

**Example Hierarchy:**
```
Root (id=1)
├── Administration (id=2)
├── IT (id=5)
│   ├── Development (id=6)
│   └── Support (id=7)
└── HR (id=3)
```

---

### 4. devices

**Purpose:** Attendance device information

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `id` | INT | Device ID | 1 |
| `terminal_sn` | VARCHAR(50) | Serial number (unique) | 'ZK12345' |
| `terminal_alias` | VARCHAR(50) | Device name | 'Office Main Entrance' |
| `ip_address` | VARCHAR(50) | Device IP | '192.168.1.100' |
| `state` | INT | Device status | 1=Online, 0=Offline |
| `is_attendance` | BOOLEAN | Is attendance device | 1=Yes |
| `last_activity` | DATETIME | Last communication | '2026-03-14 14:30:00' |
| `last_sync` | DATETIME | Last sync to cloud | '2026-03-14 02:00:00' |

---

### 5. sync_tracking

**Purpose:** Monitor sync status

| Column | Type | Description |
|--------|------|-------------|
| `table_name` | VARCHAR(50) | Table being synced |
| `last_sync_id` | INT | Last synced record ID |
| `last_sync_time` | DATETIME | When sync completed |
| `records_synced` | INT | Number of records in last sync |
| `sync_status` | VARCHAR(20) | 'pending', 'in_progress', 'completed', 'failed' |
| `sync_error` | TEXT | Error message if failed |

**Usage:**
```sql
-- Check if sync is healthy
SELECT table_name, sync_status, last_sync_time, records_synced
FROM sync_tracking
ORDER BY table_name;
```

---

## Common Queries

### 1. Get Today's Attendance

```sql
-- All attendance for today
SELECT 
    a.punch_time,
    e.emp_code,
    e.first_name,
    e.last_name,
    d.dept_name,
    a.punch_state,
    a.terminal_alias
FROM attendance_logs a
LEFT JOIN employees e ON a.emp_id = e.id
LEFT JOIN departments d ON e.department_id = d.id
WHERE DATE(a.punch_time) = CURDATE()
ORDER BY a.punch_time;
```

### 2. Get Employee's Attendance for Date Range

```sql
-- Attendance for specific employee
SELECT 
    a.punch_time,
    a.punch_state,
    a.terminal_alias,
    CASE a.punch_state
        WHEN '0' THEN 'Check-in'
        WHEN '1' THEN 'Check-out'
        WHEN '2' THEN 'Break-out'
        WHEN '3' THEN 'Break-in'
        WHEN '4' THEN 'OT-in'
        WHEN '5' THEN 'OT-out'
    END AS state_name
FROM attendance_logs a
WHERE a.emp_code = 'EMP001'
AND DATE(a.punch_time) BETWEEN '2026-03-01' AND '2026-03-31'
ORDER BY a.punch_time;
```

### 3. Get Late Arrivals

```sql
-- Employees who arrived after 08:30
SELECT 
    e.emp_code,
    e.first_name,
    d.dept_name,
    a.punch_time,
    TIME(a.punch_time) AS arrival_time,
    TIMEDIFF(TIME(a.punch_time), '08:30:00') AS late_by
FROM attendance_logs a
LEFT JOIN employees e ON a.emp_id = e.id
LEFT JOIN departments d ON e.department_id = d.id
WHERE a.punch_state = '0'  -- Check-in
AND TIME(a.punch_time) > '08:30:00'
AND DATE(a.punch_time) = CURDATE()
ORDER BY a.punch_time DESC;
```

### 4. Get Early Departures

```sql
-- Employees who left before 17:30
SELECT 
    e.emp_code,
    e.first_name,
    d.dept_name,
    a.punch_time,
    TIME(a.punch_time) AS departure_time,
    TIMEDIFF('17:30:00', TIME(a.punch_time)) AS early_by
FROM attendance_logs a
LEFT JOIN employees e ON a.emp_id = e.id
LEFT JOIN departments d ON e.department_id = d.id
WHERE a.punch_state = '1'  -- Check-out
AND TIME(a.punch_time) < '17:30:00'
AND DATE(a.punch_time) = CURDATE()
ORDER BY a.punch_time;
```

### 5. Get Active Employees

```sql
-- All active employees with department
SELECT 
    e.emp_code,
    e.first_name,
    e.last_name,
    e.display_name,
    d.dept_name,
    e.hire_date,
    e.mobile,
    e.email
FROM employees e
LEFT JOIN departments d ON e.department_id = d.id
WHERE e.is_active = 1
ORDER BY d.dept_name, e.emp_code;
```

### 6. Calculate Daily Work Hours

```sql
-- Work hours per employee per day (simplified)
SELECT 
    e.emp_code,
    e.first_name,
    DATE(a.punch_time) AS work_date,
    MIN(CASE WHEN a.punch_state = '0' THEN a.punch_time END) AS check_in,
    MAX(CASE WHEN a.punch_state = '1' THEN a.punch_time END) AS check_out,
    TIME_TO_SEC(
        TIMEDIFF(
            MAX(CASE WHEN a.punch_state = '1' THEN a.punch_time END),
            MIN(CASE WHEN a.punch_state = '0' THEN a.punch_time END)
        )
    ) / 3600 AS work_hours
FROM attendance_logs a
LEFT JOIN employees e ON a.emp_id = e.id
WHERE DATE(a.punch_time) = '2026-03-14'
AND e.is_active = 1
GROUP BY e.emp_code, DATE(a.punch_time)
HAVING check_in IS NOT NULL AND check_out IS NOT NULL;
```

### 7. Get Department-wise Attendance Summary

```sql
-- Attendance count by department for date range
SELECT 
    d.dept_name,
    COUNT(DISTINCT a.emp_code) AS employee_count,
    COUNT(*) AS total_punches,
    SUM(CASE WHEN a.punch_state = '0' THEN 1 ELSE 0 END) AS check_ins,
    SUM(CASE WHEN a.punch_state = '1' THEN 1 ELSE 0 END) AS check_outs
FROM attendance_logs a
LEFT JOIN employees e ON a.emp_id = e.id
LEFT JOIN departments d ON e.department_id = d.id
WHERE DATE(a.punch_time) BETWEEN '2026-03-01' AND '2026-03-31'
GROUP BY d.dept_name
ORDER BY d.dept_name;
```

### 8. Get Device Usage Statistics

```sql
-- Usage by device
SELECT 
    a.terminal_alias,
    a.terminal_sn,
    COUNT(*) AS total_punches,
    COUNT(DISTINCT a.emp_code) AS unique_employees,
    MIN(a.punch_time) AS first_punch,
    MAX(a.punch_time) AS last_punch
FROM attendance_logs a
WHERE DATE(a.punch_time) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
GROUP BY a.terminal_sn, a.terminal_alias
ORDER BY total_punches DESC;
```

---

## Salary Calculation Examples

### Example 1: Basic Monthly Attendance Summary

```sql
-- Monthly summary for salary calculation
SELECT 
    e.emp_code,
    e.first_name,
    e.last_name,
    d.dept_name,
    e.emp_type,
    
    -- Attendance counts
    COUNT(DISTINCT DATE(a.punch_time)) AS days_present,
    SUM(CASE WHEN a.punch_state = '0' THEN 1 ELSE 0 END) AS total_check_ins,
    SUM(CASE WHEN a.punch_state = '1' THEN 1 ELSE 0 END) AS total_check_outs,
    
    -- Work hours calculation
    SUM(
        TIME_TO_SEC(
            TIMEDIFF(
                MAX(CASE WHEN a.punch_state = '1' THEN a.punch_time END),
                MIN(CASE WHEN a.punch_state = '0' THEN a.punch_time END)
            )
        )
    ) / 3600 AS total_work_hours,
    
    -- Late arrivals (after 08:30)
    SUM(CASE 
        WHEN a.punch_state = '0' AND TIME(a.punch_time) > '08:30:00' 
        THEN 1 ELSE 0 
    END) AS late_count,
    
    -- Early departures (before 17:30)
    SUM(CASE 
        WHEN a.punch_state = '1' AND TIME(a.punch_time) < '17:30:00' 
        THEN 1 ELSE 0 
    END) AS early_departure_count
    
FROM employees e
LEFT JOIN attendance_logs a ON e.emp_id = a.emp_id
LEFT JOIN departments d ON e.department_id = d.id
WHERE e.is_active = 1
AND DATE(a.punch_time) >= '2026-03-01'
AND DATE(a.punch_time) < '2026-04-01'
GROUP BY e.emp_code, e.first_name, e.last_name, d.dept_name, e.emp_type
ORDER BY d.dept_name, e.emp_code;
```

### Example 2: Overtime Calculation

```sql
-- Overtime hours (work beyond 17:30)
SELECT 
    e.emp_code,
    e.first_name,
    DATE(a.punch_time) AS work_date,
    
    -- Check-out time
    MAX(CASE WHEN a.punch_state = '1' THEN a.punch_time END) AS check_out_time,
    
    -- Overtime calculation (hours beyond 17:30)
    CASE 
        WHEN TIME(MAX(CASE WHEN a.punch_state = '1' THEN a.punch_time END)) > '17:30:00'
        THEN TIME_TO_SEC(
            TIMEDIFF(
                MAX(CASE WHEN a.punch_state = '1' THEN a.punch_time END),
                CONCAT(DATE(a.punch_time), ' 17:30:00')
            )
        ) / 3600
        ELSE 0
    END AS overtime_hours
    
FROM attendance_logs a
LEFT JOIN employees e ON a.emp_id = e.id
WHERE a.punch_state = '1'
AND DATE(a.punch_time) >= '2026-03-01'
AND DATE(a.punch_time) < '2026-04-01'
GROUP BY e.emp_code, e.first_name, DATE(a.punch_time)
HAVING overtime_hours > 0
ORDER BY work_date, e.emp_code;
```

### Example 3: Absenteeism Report

```sql
-- Find employees who were absent (no check-in on work days)
SELECT 
    e.emp_code,
    e.first_name,
    d.dept_name,
    calendar.work_date,
    'Absent' AS status
FROM (
    -- Generate work days for the month
    SELECT DATE_ADD('2026-03-01', INTERVAL n DAY) AS work_date
    FROM (
        SELECT 0 AS n UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
        UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9
        UNION SELECT 10 UNION SELECT 11 UNION SELECT 12 UNION SELECT 13 UNION SELECT 14
        UNION SELECT 15 UNION SELECT 16 UNION SELECT 17 UNION SELECT 18 UNION SELECT 19
        UNION SELECT 20 UNION SELECT 21 UNION SELECT 22 UNION SELECT 23 UNION SELECT 24
        UNION SELECT 25 UNION SELECT 26 UNION SELECT 27 UNION SELECT 28 UNION SELECT 29
        UNION SELECT 30
    ) numbers
    WHERE DATE_ADD('2026-03-01', INTERVAL n DAY) < '2026-04-01'
    AND DAYOFWEEK(DATE_ADD('2026-03-01', INTERVAL n DAY)) NOT IN (1, 7)  -- Exclude weekends
) calendar
CROSS JOIN employees e
LEFT JOIN departments d ON e.department_id = d.id
LEFT JOIN attendance_logs a ON e.emp_id = a.emp_id 
    AND DATE(a.punch_time) = calendar.work_date
    AND a.punch_state = '0'
WHERE e.is_active = 1
AND a.emp_id IS NULL  -- No attendance record
ORDER BY calendar.work_date, e.emp_code;
```

### Example 4: Complete Salary Report

```sql
-- Comprehensive salary report
WITH daily_summary AS (
    SELECT 
        e.emp_id,
        e.emp_code,
        DATE(a.punch_time) AS work_date,
        MIN(CASE WHEN a.punch_state = '0' THEN a.punch_time END) AS check_in,
        MAX(CASE WHEN a.punch_state = '1' THEN a.punch_time END) AS check_out,
        
        -- Calculate work hours
        TIME_TO_SEC(
            TIMEDIFF(
                MAX(CASE WHEN a.punch_state = '1' THEN a.punch_time END),
                MIN(CASE WHEN a.punch_state = '0' THEN a.punch_time END)
            )
        ) / 3600 AS work_hours,
        
        -- Late arrival flag
        CASE WHEN TIME(MIN(CASE WHEN a.punch_state = '0' THEN a.punch_time END)) > '08:30:00'
             THEN 1 ELSE 0 END AS is_late,
        
        -- Overtime hours
        CASE 
            WHEN TIME(MAX(CASE WHEN a.punch_state = '1' THEN a.punch_time END)) > '17:30:00'
            THEN TIME_TO_SEC(
                TIMEDIFF(
                    MAX(CASE WHEN a.punch_state = '1' THEN a.punch_time END),
                    CONCAT(DATE(a.punch_time), ' 17:30:00')
                )
            ) / 3600
            ELSE 0 
        END AS overtime_hours
        
    FROM attendance_logs a
    LEFT JOIN employees e ON a.emp_id = e.id
    WHERE DATE(a.punch_time) >= '2026-03-01'
    AND DATE(a.punch_time) < '2026-04-01'
    AND a.punch_state IN ('0', '1')
    GROUP BY e.emp_id, e.emp_code, DATE(a.punch_time)
)

SELECT 
    e.emp_code,
    e.first_name,
    e.last_name,
    d.dept_name,
    e.emp_type,
    
    -- Attendance summary
    COUNT(ds.work_date) AS days_worked,
    SUM(ds.work_hours) AS total_work_hours,
    AVG(ds.work_hours) AS avg_daily_hours,
    
    -- Late/Early summary
    SUM(ds.is_late) AS late_days,
    SUM(ds.overtime_hours) AS total_overtime_hours,
    
    -- Salary calculation (example rates)
    COUNT(ds.work_date) * 50000 AS base_salary,  -- 50,000 per day
    SUM(ds.overtime_hours) * 10000 AS overtime_pay,  -- 10,000 per OT hour
    SUM(ds.is_late) * -5000 AS late_penalty,  -- -5,000 per late day
    
    -- Total salary
    (COUNT(ds.work_date) * 50000) + 
    (SUM(ds.overtime_hours) * 10000) - 
    (SUM(ds.is_late) * 5000) AS total_salary
    
FROM employees e
LEFT JOIN departments d ON e.department_id = d.id
LEFT JOIN daily_summary ds ON e.emp_id = ds.emp_id
WHERE e.is_active = 1
GROUP BY e.emp_code, e.first_name, e.last_name, d.dept_name, e.emp_type
ORDER BY d.dept_name, e.emp_code;
```

---

## API Integration Guide

### PHP REST API Example

```php
<?php
// api/attendance.php

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once 'config.php';

try {
    $pdo = new PDO(DB_DSN, DB_USER, DB_PASS);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    
    // Get query parameters
    $emp_code = $_GET['emp_code'] ?? null;
    $start_date = $_GET['start_date'] ?? date('Y-m-01');
    $end_date = $_GET['end_date'] ?? date('Y-m-d');
    
    // Build query
    $sql = "
        SELECT 
            a.id,
            a.emp_code,
            e.first_name,
            e.last_name,
            a.punch_time,
            a.punch_state,
            a.terminal_alias,
            a.server_time
        FROM attendance_logs a
        LEFT JOIN employees e ON a.emp_id = e.id
        WHERE DATE(a.punch_time) BETWEEN :start_date AND :end_date
    ";
    
    $params = [
        ':start_date' => $start_date,
        ':end_date' => $end_date
    ];
    
    if ($emp_code) {
        $sql .= " AND a.emp_code = :emp_code";
        $params[':emp_code'] = $emp_code;
    }
    
    $sql .= " ORDER BY a.punch_time DESC";
    
    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    
    $attendance = $stmt->fetchAll();
    
    echo json_encode([
        'success' => true,
        'data' => $attendance,
        'count' => count($attendance)
    ]);
    
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => $e->getMessage()
    ]);
}
?>
```

### JavaScript Frontend Example

```javascript
// Fetch attendance data
async function getAttendance(empCode, startDate, endDate) {
    const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate
    });
    
    if (empCode) {
        params.append('emp_code', empCode);
    }
    
    const response = await fetch(`/api/attendance.php?${params}`);
    const result = await response.json();
    
    if (result.success) {
        return result.data;
    } else {
        throw new Error(result.error);
    }
}

// Calculate salary
async function calculateSalary(empCode, month, year) {
    const startDate = `${year}-${month.toString().padStart(2, '0')}-01`;
    const endDate = new Date(year, month, 0).toISOString().split('T')[0];
    
    const attendance = await getAttendance(empCode, startDate, endDate);
    
    // Process attendance data
    const summary = {
        daysWorked: 0,
        totalHours: 0,
        lateDays: 0,
        overtimeHours: 0
    };
    
    // Group by date and calculate
    const byDate = {};
    attendance.forEach(record => {
        const date = record.punch_time.split(' ')[0];
        if (!byDate[date]) {
            byDate[date] = { checkIn: null, checkOut: null };
        }
        
        if (record.punch_state === '0') {
            byDate[date].checkIn = new Date(record.punch_time);
        } else if (record.punch_state === '1') {
            byDate[date].checkOut = new Date(record.punch_time);
        }
    });
    
    // Calculate summary
    Object.values(byDate).forEach(day => {
        if (day.checkIn && day.checkOut) {
            summary.daysWorked++;
            
            const hours = (day.checkOut - day.checkIn) / 3600000;
            summary.totalHours += hours;
            
            // Late check
            if (day.checkIn.getHours() > 8 || 
               (day.checkIn.getHours() === 8 && day.checkIn.getMinutes() > 30)) {
                summary.lateDays++;
            }
            
            // Overtime check
            if (day.checkOut.getHours() > 17 || 
               (day.checkOut.getHours() === 17 && day.checkOut.getMinutes() > 30)) {
                const otStart = new Date(day.checkOut);
                otStart.setHours(17, 30, 0, 0);
                summary.overtimeHours += (day.checkOut - otStart) / 3600000;
            }
        }
    });
    
    return summary;
}

// Usage
calculateSalary('EMP001', 3, 2026)
    .then(summary => {
        console.log('Salary Summary:', summary);
        // Display in UI
    })
    .catch(error => {
        console.error('Error:', error);
    });
```

---

## Best Practices

### 1. Query Performance

**✅ DO:**
```sql
-- Use indexed columns in WHERE clause
SELECT * FROM attendance_logs
WHERE emp_code = 'EMP001'
AND punch_time >= '2026-03-01';

-- Use date ranges
WHERE DATE(punch_time) BETWEEN '2026-03-01' AND '2026-03-31'

-- Limit results
LIMIT 1000
```

**❌ DON'T:**
```sql
-- Avoid functions on indexed columns
WHERE DATE(punch_time) = '2026-03-14'  -- Slower

-- Better:
WHERE punch_time >= '2026-03-14 00:00:00'
AND punch_time < '2026-03-15 00:00:00'
```

### 2. Data Freshness

**Check sync status before processing:**
```sql
SELECT table_name, sync_status, last_sync_time
FROM sync_tracking
WHERE sync_status != 'completed'
OR last_sync_time < DATE_SUB(NOW(), INTERVAL 6 HOUR);
```

If sync is delayed, warn users:
```php
$lastSync = $pdo->query("
    SELECT MAX(last_sync_time) FROM sync_tracking
")->fetchColumn();

if (strtotime($lastSync) < time() - 3600 * 6) {
    echo "Warning: Data may be outdated. Last sync: $lastSync";
}
```

### 3. Handle Missing Data

**Employees without attendance:**
```sql
-- Use LEFT JOIN to include all employees
SELECT e.emp_code, e.first_name, a.punch_time
FROM employees e
LEFT JOIN attendance_logs a ON e.emp_id = a.emp_id
WHERE e.is_active = 1
```

**Check for NULL values:**
```php
$workHours = $row['work_hours'] ?? 0;  // Default to 0 if NULL
```

### 4. Timezone Handling

**All timestamps are in server timezone. Convert if needed:**

```php
// Convert to user timezone
$punchTime = new DateTime($row['punch_time'], new DateTimeZone('UTC'));
$punchTime->setTimezone(new DateTimeZone('Asia/Vientiane'));
echo $punchTime->format('Y-m-d H:i:s');
```

### 5. Caching

**Cache frequently accessed data:**

```php
// Cache employee list for 1 hour
$employees = $cache->get('employees_active');
if (!$employees) {
    $employees = $pdo->query("
        SELECT * FROM v_employees_active
    ")->fetchAll();
    $cache->set('employees_active', $employees, 3600);
}
```

---

## Troubleshooting

### Issue 1: No Data Returned

**Check:**
1. Is sync running? Check `sync_tracking` table
2. Are employees active? `WHERE is_active = 1`
3. Date range correct? Verify start/end dates
4. Employee code correct? Check for typos

**Debug query:**
```sql
-- Check if data exists
SELECT COUNT(*) FROM attendance_logs;
SELECT COUNT(*) FROM employees WHERE is_active = 1;
SELECT * FROM sync_tracking;
```

### Issue 2: Duplicate Records

**Should not happen** due to unique constraint. If it does:

```sql
-- Find duplicates
SELECT emp_code, punch_time, terminal_sn, COUNT(*)
FROM attendance_logs
GROUP BY emp_code, punch_time, terminal_sn
HAVING COUNT(*) > 1;

-- Remove duplicates (keep latest)
DELETE t1 FROM attendance_logs t1
INNER JOIN attendance_logs t2
WHERE t1.id > t2.id
AND t1.emp_code = t2.emp_code
AND t1.punch_time = t2.punch_time
AND t1.terminal_sn = t2.terminal_sn;
```

### Issue 3: Slow Queries

**Optimize:**
1. Add indexes (already included in schema)
2. Use date ranges instead of DATE() function
3. Limit result sets
4. Use views for complex queries

**Check slow queries:**
```sql
-- Enable slow query log in MySQL
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;  -- Log queries > 2 seconds
```

### Issue 4: Missing Employees

**Check:**
```sql
-- Employees without attendance
SELECT e.emp_code, e.first_name
FROM employees e
LEFT JOIN attendance_logs a ON e.emp_id = a.emp_id
WHERE a.emp_id IS NULL
AND e.is_active = 1;
```

**Solution:** Employee may not have punched or sync issue

### Issue 5: Incorrect Work Hours

**Common causes:**
1. Missing check-out (employee forgot)
2. Multiple check-ins without check-out
3. System downtime

**Handle in query:**
```sql
-- Use COALESCE for missing check-out
COALESCE(
    MAX(CASE WHEN punch_state = '1' THEN punch_time END),
    NOW()  -- Assume still at work
) AS check_out
```

---

## Support

### Contact Information

- **Database Admin:** [Your contact]
- **Technical Support:** [Support email/phone]
- **Documentation:** See README.md in repository

### Useful Links

- GitHub Repository: https://github.com/bounthongv/zkupload
- ZKBioTime Documentation: [Link if available]

### Reporting Issues

When reporting issues, include:
1. Error message
2. Query that failed
3. Expected vs actual result
4. Timestamp of issue
5. Employee/device codes involved

---

## Appendix

### A. Sample PHP Class

```php
<?php
class AttendanceService {
    private $pdo;
    
    public function __construct($pdo) {
        $this->pdo = $pdo;
    }
    
    public function getEmployeeAttendance($empCode, $startDate, $endDate) {
        $stmt = $this->pdo->prepare("
            SELECT * FROM v_attendance_detail
            WHERE emp_code = :emp_code
            AND DATE(punch_time) BETWEEN :start AND :end
            ORDER BY punch_time
        ");
        
        $stmt->execute([
            ':emp_code' => $empCode,
            ':start' => $startDate,
            ':end' => $endDate
        ]);
        
        return $stmt->fetchAll();
    }
    
    public function calculateMonthlySalary($empCode, $month, $year) {
        $startDate = "$year-$month-01";
        $endDate = date('Y-m-t', strtotime($startDate));
        
        $attendance = $this->getEmployeeAttendance($empCode, $startDate, $endDate);
        
        // Process and calculate salary
        return $this->processSalaryCalculation($attendance);
    }
    
    private function processSalaryCalculation($attendance) {
        // Implementation here
    }
}
?>
```

### B. Database Backup Script

```bash
#!/bin/bash
# backup.sh - Daily backup script

BACKUP_DIR="/backups/zk_attendance"
DATE=$(date +%Y%m%d_%H%M%S)
mysqldump -h HOST -u USER -p'PASSWORD' \
    --single-transaction \
    --routines \
    --triggers \
    DATABASE_NAME > "$BACKUP_DIR/backup_$DATE.sql"

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
```

### C. Monitoring Query

```sql
-- Daily sync health check
SELECT 
    table_name,
    sync_status,
    last_sync_time,
    records_synced,
    TIMESTAMPDIFF(HOUR, last_sync_time, NOW()) AS hours_since_sync,
    CASE 
        WHEN sync_status = 'failed' THEN 'CRITICAL'
        WHEN TIMESTAMPDIFF(HOUR, last_sync_time, NOW()) > 6 THEN 'WARNING'
        ELSE 'OK'
    END AS health_status
FROM sync_tracking
ORDER BY table_name;
```

---

**End of Manual**

For questions or clarifications, please contact the development team.
