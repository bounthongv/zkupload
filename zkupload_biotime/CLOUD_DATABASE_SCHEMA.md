# Cloud Database Schema Reference

**For:** Salary/Payment Web Application Integration  
**Database:** ZK BioTime Attendance Cloud  
**Updated:** 2026-03-14

---

## Tables

### 1. attendance_logs

**Purpose:** Raw attendance punches

| Column | Type | Description |
|--------|------|-------------|
| id | INT AUTO_INCREMENT | Primary key |
| emp_code | VARCHAR(20) | Employee ID |
| punch_time | DATETIME | Attendance timestamp |
| punch_state | VARCHAR(5) | 0=IN, 1=OUT, 2=Break-out, 3=Break-in, 4=OT-in, 5=OT-out |
| verify_type | INT | 0=Unknown, 1=Fingerprint, 2=Face, 3=Card, 4=Password, 5=Mobile |
| terminal_sn | VARCHAR(50) | Device serial number |
| terminal_alias | VARCHAR(50) | Device location name |
| emp_id | INT | FK to employees.id |
| terminal_id | INT | FK to devices.id |
| server_time | DATETIME | When uploaded to cloud |
| source_device | VARCHAR(50) | Always 'zkbiotime' |

**Indexes:** emp_code, punch_time, (emp_code, punch_time), terminal_sn

**Unique:** (emp_code, punch_time, terminal_sn)

---

### 2. employees

**Purpose:** Employee master data

| Column | Type | Description |
|--------|------|-------------|
| id | INT | Primary key |
| emp_code | VARCHAR(20) | Employee identifier (unique) |
| first_name | VARCHAR(100) | Given name |
| last_name | VARCHAR(100) | Family name |
| display_name | VARCHAR(100) | Nickname/preferred name |
| department_id | INT | FK to departments.id |
| emp_type | INT | Employee type (1=Full-time, 2=Part-time, etc.) |
| hire_date | DATE | Date of hiring |
| is_active | BOOLEAN | 1=Active, 0=Inactive |
| mobile | VARCHAR(20) | Contact number |
| email | VARCHAR(50) | Email address |
| last_sync | DATETIME | Last sync time |

**Indexes:** emp_code, department_id, is_active, (emp_code, is_active)

**Unique:** emp_code

---

### 3. departments

**Purpose:** Department structure

| Column | Type | Description |
|--------|------|-------------|
| id | INT | Primary key |
| dept_code | VARCHAR(50) | Department code (unique) |
| dept_name | VARCHAR(200) | Department name |
| parent_dept_id | INT | Parent department (hierarchy) |
| last_sync | DATETIME | Last sync time |

**Indexes:** dept_code, parent_dept_id

**Unique:** dept_code

---

### 4. devices

**Purpose:** Device information

| Column | Type | Description |
|--------|------|-------------|
| id | INT | Primary key |
| terminal_sn | VARCHAR(50) | Serial number (unique) |
| terminal_alias | VARCHAR(50) | Device name/location |
| ip_address | VARCHAR(50) | Device IP address |
| state | INT | 0=Offline, 1=Online |
| is_attendance | BOOLEAN | 1=Attendance device |
| last_activity | DATETIME | Last communication |
| last_sync | DATETIME | Last sync to cloud |

**Indexes:** terminal_sn, state

**Unique:** terminal_sn

---

### 5. sync_tracking

**Purpose:** Monitor sync status

| Column | Type | Description |
|--------|------|-------------|
| id | INT AUTO_INCREMENT | Primary key |
| table_name | VARCHAR(50) | Table name (unique) |
| last_sync_id | INT | Last synced record ID |
| last_sync_time | DATETIME | When sync completed |
| records_synced | INT | Records in last sync |
| sync_status | VARCHAR(20) | pending, in_progress, completed, failed |
| sync_error | TEXT | Error message if failed |
| updated_at | DATETIME | Last update time |

**Unique:** table_name

---

## Views

### v_attendance_detail

**Columns:**
attendance_id, emp_code, first_name, last_name, display_name, department, punch_time, punch_state, punch_state_name, verify_type, verify_type_name, terminal_sn, terminal_alias, device_ip, server_time, source_device

---

### v_employees_active

**Columns:**
id, emp_code, first_name, last_name, display_name, department, emp_type, hire_date, mobile, email, is_active

---

### v_device_status

**Columns:**
id, terminal_sn, terminal_alias, ip_address, state_name, is_attendance, last_activity, minutes_since_activity, last_sync

---

## Reference

### Punch State Codes

| Code | Meaning |
|------|---------|
| 0 | Check-in |
| 1 | Check-out |
| 2 | Break-out |
| 3 | Break-in |
| 4 | OT-in |
| 5 | OT-out |

### Verify Type Codes

| Code | Method |
|------|--------|
| 0 | Unknown |
| 1 | Fingerprint |
| 2 | Face Recognition |
| 3 | RFID Card |
| 4 | Password |
| 5 | Mobile App |

### Sync Schedule

| Table | Frequency | Times |
|-------|-----------|-------|
| attendance_logs | Every 4 hours | 09:00, 12:00, 17:00, 22:00 |
| employees | Every 6 hours | 01:00, 07:00, 13:00, 19:00 |
| departments | Daily | 01:00 |
| devices | Daily | 02:00 |

---
