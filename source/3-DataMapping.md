# Data Mapping: ZKBioTime PostgreSQL → Cloud MySQL

## Overview

This document defines the mapping from 4 tables in the local ZKBioTime PostgreSQL database to the cloud MySQL database for attendance and salary calculation integration.

## Table Mapping Summary

| # | PostgreSQL Table | Cloud MySQL Table | Sync Strategy | Priority |
|---|------------------|-------------------|---------------|----------|
| 1 | `iclock_transaction` | `attendance_logs` | Incremental (ID-based) | **CRITICAL** |
| 2 | `personnel_employee` | `employees` | Incremental (ID or timestamp) | **HIGH** |
| 3 | `personnel_department` | `departments` | Full sync (small table) | MEDIUM |
| 4 | `iclock_terminal` | `devices` | Incremental (ID-based) | MEDIUM |

---

## 1. attendance_logs (from iclock_transaction)

**Purpose:** Raw attendance punches from devices (check-in/check-out)

**Sync Frequency:** Every scheduled sync (default: 09:00, 12:00, 17:00, 22:00)

**Sync Strategy:** Incremental by `id` field

### Field Mapping

| PostgreSQL Field | Cloud Field | Type | Required | Notes |
|------------------|-------------|------|----------|-------|
| `id` | (not synced) | - | - | Used for sync tracking only |
| `emp_code` | `emp_code` | VARCHAR(20) | ✅ | Employee identifier |
| `punch_time` | `punch_time` | DATETIME | ✅ | Attendance timestamp |
| `punch_state` | `punch_state` | VARCHAR(5) | ✅ | 0=IN, 1=OUT, 2-5=Other |
| `verify_type` | `verify_type` | INT | ✅ | 1=Fingerprint, 2=Face, 3=Card |
| `terminal_sn` | `terminal_sn` | VARCHAR(50) | ✅ | Device serial number |
| `terminal_alias` | `terminal_alias` | VARCHAR(50) | ❌ | Device name/location |
| `emp_id` | `emp_id` | INT | ❌ | FK to employees table |
| `terminal_id` | `terminal_id` | INT | ❌ | FK to devices table |
| (generated) | `server_time` | DATETIME | ✅ | When uploaded to cloud |
| (fixed) | `source_device` | VARCHAR(50) | ✅ | Always 'zkbiotime' |

### Recommended Fields (Senior Advisor Recommendation)

**✅ INCLUDE (Core Fields):**
- `emp_code` - Essential for employee identification
- `punch_time` - Critical for salary/overtime calculations
- `punch_state` - Determines IN/OUT for work duration
- `terminal_sn` - Identifies which device (multiple locations)
- `verify_type` - Useful for security audits

**✅ INCLUDE (Supporting Fields):**
- `terminal_alias` - Human-readable location name (Office, Warehouse, etc.)
- `emp_id` - For future JOIN with employees table
- `terminal_id` - For future JOIN with devices table

**✅ INCLUDE (Audit Fields):**
- `server_time` - Auto-generated timestamp when uploaded
- `source_device` - Distinguish from other data sources

**❌ EXCLUDE (Not Needed for Salary):**
- `work_code`, `purpose`, `crc`, `is_attendance`, `reserved`
- GPS fields (`longitude`, `latitude`, `gps_location`)
- `mobile`, `source`, `is_mask`, `temperature`
- `company_code`, `upload_time`, `sync_status`, `sync_time`

**Rationale:** Keep the cloud table lean and focused on salary calculation needs. Additional fields can be added later if requirements change.

### Unique Constraint
```sql
UNIQUE KEY unique_emp_punch (emp_code, punch_time, terminal_sn)
```

### Indexes
```sql
INDEX idx_emp_code (emp_code)
INDEX idx_punch_time (punch_time)
INDEX idx_emp_time (emp_code, punch_time)
```

---

## 2. employees (from personnel_employee)

**Purpose:** Employee master data for name, department, and status lookup

**Sync Frequency:** Once per day (or when changes detected)

**Sync Strategy:** Incremental by `update_time` or `change_time`

### Field Mapping

| PostgreSQL Field | Cloud Field | Type | Required | Notes |
|------------------|-------------|------|----------|-------|
| `id` | `id` | INT | ✅ | Internal employee ID (preserve for FK) |
| `emp_code` | `emp_code` | VARCHAR(20) | ✅ | Employee identifier (unique) |
| `first_name` | `first_name` | VARCHAR(100) | ❌ | Given name |
| `last_name` | `last_name` | VARCHAR(100) | ❌ | Family name |
| `nickname` | `display_name` | VARCHAR(100) | ❌ | Preferred name |
| `department_id` | `department_id` | INT | ❌ | FK to departments |
| `emp_type` | `emp_type` | INT | ❌ | Employee type (full-time, part-time) |
| `hire_date` | `hire_date` | DATE | ❌ | For seniority calculation |
| `is_active` | `is_active` | BOOLEAN | ✅ | Active/inactive status |
| `mobile` | `mobile` | VARCHAR(20) | ❌ | Contact number |
| `email` | `email` | VARCHAR(50) | ❌ | Email address |
| (generated) | `last_sync` | DATETIME | ✅ | When last synced |

### Recommended Fields (Senior Advisor Recommendation)

**✅ INCLUDE (Core Fields):**
- `id` - Preserve for foreign key relationships
- `emp_code` - Primary identifier used in attendance_logs
- `first_name`, `last_name` - Employee full name
- `department_id` - For department filtering
- `is_active` - Filter active employees only
- `emp_type` - May affect salary calculation (full-time vs part-time)

**✅ INCLUDE (Useful for HR):**
- `nickname` - Display name (often used in reports)
- `hire_date` - For seniority-based benefits
- `mobile`, `email` - Contact information

**❌ EXCLUDE (Not Needed):**
- Passwords (`self_password`, `device_password`)
- Security fields (`acc_group`, `acc_timezone`, `dev_privilege`)
- System fields (`create_time`, `create_user`, `change_time`, `change_user`)
- Photos, licenses, SSN, passport (privacy concerns)
- `verify_mode`, `app_status`, `app_role`, `session_key`, `login_ip`
- `leave_group`, `emp_code_digit`, `superior_id`, `company_id`

**Rationale:** Include enough for employee identification and basic HR info, but exclude sensitive data (passwords, SSN) and system fields not needed for salary calculation.

### Unique Constraint
```sql
UNIQUE KEY unique_emp_code (emp_code)
```

### Indexes
```sql
INDEX idx_emp_code (emp_code)
INDEX idx_department_id (department_id)
INDEX idx_is_active (is_active)
```

---

## 3. departments (from personnel_department)

**Purpose:** Department structure for organizational grouping

**Sync Frequency:** Once per day (or on-demand, table is small)

**Sync Strategy:** Full sync (table typically has < 100 records)

### Field Mapping

| PostgreSQL Field | Cloud Field | Type | Required | Notes |
|------------------|-------------|------|----------|-------|
| `id` | `id` | INT | ✅ | Internal department ID (preserve for FK) |
| `dept_code` | `dept_code` | VARCHAR(50) | ✅ | Department code (unique) |
| `dept_name` | `dept_name` | VARCHAR(200) | ✅ | Department name |
| `parent_dept_id` | `parent_dept_id` | INT | ❌ | For hierarchy (optional) |
| (generated) | `last_sync` | DATETIME | ✅ | When last synced |

### Recommended Fields (Senior Advisor Recommendation)

**✅ INCLUDE:**
- `id` - Preserve for foreign key relationships
- `dept_code` - Unique identifier
- `dept_name` - Display name
- `parent_dept_id` - For department hierarchy (if needed)

**❌ EXCLUDE:**
- `is_default` - System flag not needed in cloud
- `dept_manager_id` - Changes frequently, not needed for salary
- `company_id` - Single company assumed

**Rationale:** Keep it simple. Department hierarchy may be useful for multi-level reporting, but manager tracking is not needed for salary calculation.

### Unique Constraint
```sql
UNIQUE KEY unique_dept_code (dept_code)
```

---

## 4. devices (from iclock_terminal)

**Purpose:** Device information for location and status tracking

**Sync Frequency:** Once per day or when device changes

**Sync Strategy:** Incremental by `id` or `change_time`

### Field Mapping

| PostgreSQL Field | Cloud Field | Type | Required | Notes |
|------------------|-------------|------|----------|-------|
| `id` | `id` | INT | ✅ | Internal device ID (preserve for FK) |
| `sn` | `terminal_sn` | VARCHAR(50) | ✅ | Serial number (unique) |
| `alias` | `terminal_alias` | VARCHAR(50) | ✅ | Device name |
| `ip_address` | `ip_address` | VARCHAR(50) | ❌ | Device IP |
| `state` | `state` | INT | ❌ | Device status |
| `terminal_tz` | `timezone` | INT | ❌ | Device timezone |
| `is_attendance` | `is_attendance` | BOOLEAN | ❌ | Attendance device flag |
| `last_activity` | `last_activity` | DATETIME | ❌ | Last communication |
| `area_id` | `area_id` | INT | ❌ | For location grouping |
| (generated) | `last_sync` | DATETIME | ✅ | When last synced |

### Recommended Fields (Senior Advisor Recommendation)

**✅ INCLUDE (Core Fields):**
- `id` - Preserve for foreign key relationships
- `sn` → `terminal_sn` - Unique serial number (matches attendance_logs)
- `alias` → `terminal_alias` - Human-readable name
- `state` - Device online/offline status

**✅ INCLUDE (Optional but Useful):**
- `ip_address` - For troubleshooting device connectivity
- `last_activity` - Monitor device health
- `is_attendance` - Confirm device type

**❌ EXCLUDE:**
- Protocol/version fields (`push_protocol`, `push_ver`, `fw_ver`)
- Capacity fields (`user_count`, `transaction_count`, `fp_count`, `face_count`)
- System fields (`create_time`, `create_user`, `change_time`, `change_user`)
- `controller_type`, `authentication`, `style`, `product_type`
- `terminal_name`, `platform`, `oem_vendor`
- Stamp fields (`log_stamp`, `op_log_stamp`, `capture_stamp`)
- `lock_func`, `is_access`, `area_id`

**Rationale:** Focus on device identification and basic status. Exclude technical details not needed for attendance tracking.

### Unique Constraint
```sql
UNIQUE KEY unique_terminal_sn (terminal_sn)
```

---

## Sync Order and Dependencies

```
1. departments (no dependencies)
2. employees (depends on departments via department_id)
3. devices (no dependencies)
4. attendance_logs (depends on employees and devices via emp_id, terminal_id)
```

**Recommended Sync Schedule:**

| Table | Frequency | Scheduled Times |
|-------|-----------|-----------------|
| departments | Daily | 01:00 |
| employees | Every 6 hours | 01:00, 07:00, 13:00, 19:00 |
| devices | Daily | 02:00 |
| attendance_logs | Every 4 hours | 09:00, 12:00, 17:00, 22:00 |

---

## Data Privacy Considerations

**EXCLUDED from sync (sensitive data):**
- ❌ Passwords (self_password, device_password)
- ❌ National ID / SSN
- ❌ Passport numbers
- ❌ Driver's license numbers
- ❌ Photos
- ❌ Bank account details (for payroll)

**INCLUDED (necessary for business):**
- ✅ Employee name and code
- ✅ Department assignment
- ✅ Attendance punches
- ✅ Device information

**Recommendation:** Ensure cloud database has proper access controls and encryption at rest.

---

## Future Enhancements (Phase 2)

Consider adding these tables later:

1. **personnel_position** - Job titles/positions
2. **personnel_company** - Company structure (multi-company support)
3. **attendance records** - Processed attendance (after rules applied)
4. **shift schedules** - Employee shift assignments
5. **leave records** - Time-off requests and approvals

---

## Revision History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-03-14 | Initial mapping (4 tables) | User |
| 2.0 | 2026-03-14 | Senior advisor recommendations added | AI Assistant |

---

## Notes for PHP Team

**For salary calculation, you will need to:**

1. JOIN `attendance_logs` with `employees` to get employee names:
```sql
SELECT 
    a.emp_code,
    e.first_name,
    e.last_name,
    a.punch_time,
    a.punch_state,
    d.dept_name
FROM attendance_logs a
LEFT JOIN employees e ON a.emp_code = e.emp_code
LEFT JOIN departments d ON e.department_id = d.id
WHERE a.punch_time >= '2026-03-01'
ORDER BY a.punch_time;
```

2. Calculate work duration by pairing IN/OUT punches:
```sql
-- This requires complex SQL or application logic
-- Recommend handling in PHP with proper business rules
```

3. Filter active employees only:
```sql
SELECT * FROM employees WHERE is_active = 1;
```
