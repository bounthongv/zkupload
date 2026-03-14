# ZK BioTime Cloud Sync (4-Table Sync)

Attendance data synchronization from ZKBioTime (PostgreSQL) to Cloud MySQL database.

## 📊 Tables Synced

| # | PostgreSQL Table | Cloud MySQL Table | Sync Strategy | Frequency | Priority |
|---|------------------|-------------------|---------------|-----------|----------|
| 1 | `personnel_department` | `departments` | Full sync | Daily (01:00) | MEDIUM |
| 2 | `personnel_employee` | `employees` | Incremental | Every 6 hours | HIGH |
| 3 | `iclock_terminal` | `devices` | Incremental | Daily (02:00) | MEDIUM |
| 4 | `iclock_transaction` | `attendance_logs` | Incremental | Every 4 hours | **CRITICAL** |

## Purpose

This application syncs 4 tables from the local ZKBioTime system to a cloud MySQL database for:
- Salary calculation integration with PHP web application
- Employee master data management
- Device monitoring and tracking
- Attendance record aggregation

## System Architecture

```
ZK Attendance Device
        ↓ (pushes via iClock protocol)
ZKBioTime Server (Local)
        ↓ (PostgreSQL: 4 tables)
ZK Upload Sync Service
        ↓ (MySQL: 4 tables)
Cloud Database
        ↓ (PHP API)
Salary Calculation Web App
```

## Features

- ✅ **4-Table Sync**: Departments, Employees, Devices, Attendance Logs
- ✅ **Incremental Sync**: Only uploads new/changed records
- ✅ **Scheduled Sync**: Different schedules per table type
- ✅ **Duplicate Prevention**: Uses unique constraints to prevent duplicates
- ✅ **Batch Processing**: Processes large tables in configurable batches
- ✅ **System Tray UI**: User-friendly interface with per-table controls
- ✅ **Secure Credentials**: Encrypted storage for cloud database passwords
- ✅ **Idempotent**: Safe to restart or re-run without data corruption
- ✅ **Sync Tracking**: Maintains sync position for each table

## Installation

### Prerequisites

1. **Python 3.8+** installed on the ZKBioTime server machine
2. **ZKBioTime** installed and running (with PostgreSQL database)
3. **Cloud MySQL database** accessible from the server
4. **Microsoft Visual C++ Redistributable** (for some Python packages)

### Step 1: Install Python Dependencies

```bash
cd D:\zkupload\zkupload_biotime

# Create virtual environment (optional but recommended)
python -m venv venv
venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### Step 2: Create Cloud Database Tables

1. Connect to your cloud MySQL database
2. Run the SQL script: `docs/zk_cloud_setup.sql`
3. This creates all 4 tables + sync_tracking table + 3 views

Example:
```bash
mysql -h your-cloud-host.com -u your_user -p your_database < docs/zk_cloud_setup.sql
```

### Step 3: Configure PostgreSQL Connection

Edit `config.json` to match your ZKBioTime PostgreSQL settings:

```json
{
    "POSTGRESQL_CONFIG": {
        "host": "127.0.0.1",
        "port": 7496,
        "database": "biotime",
        "user": "postgres",
        "password": "YOUR_PASSWORD"
    }
}
```

**Finding PostgreSQL Password:**

The password is in `D:\ZKBioTime\attsite.ini`:

```ini
[DATABASE]
ENGINE=postgresql
NAME=biotime
USER=postgres
PASSWORD=@!@=XSY3CL6OIqr6sH0=  <-- This is your password
PORT=7496
HOST=127.0.0.1
```

### Step 4: Encrypt Cloud MySQL Credentials

Run the credential encryption utility:

```bash
encrypt_credentials.bat
```

Enter your cloud MySQL credentials when prompted:
- Host: e.g., `cloud.example.com`
- Port: `3306` (default)
- Database: Your cloud database name
- Username: Your MySQL username
- Password: Your MySQL password

This creates `encrypted_credentials.bin` (keep this secure!)

### Step 5: Test the Connection

Test PostgreSQL connection:

```bash
test_postgres.bat
```

This will verify:
- PostgreSQL connection works
- All source tables exist
- Record counts and statistics

### Step 6: Run the Application

#### Option A: System Tray Application (Recommended)

```bash
run_zk_tray.bat
```

This creates a system tray icon with:
- **Start Service**: Begin scheduled syncing
- **Stop Service**: Pause syncing
- **Sync All Tables Now**: Force immediate sync of all 4 tables
- **Individual Sync Buttons**: Sync specific tables from status window
- **Configure**: Edit PostgreSQL settings and schedules
- **View Logs**: See sync history

#### Option B: Console Service

```bash
run_zk_sync.bat
```

Runs in console mode with detailed logging.

## Configuration

### config.json

```json
{
    "POSTGRESQL_CONFIG": {
        "host": "127.0.0.1",
        "port": 7496,
        "database": "biotime",
        "user": "postgres",
        "password": ""
    },
    "SYNC_SCHEDULES": {
        "departments": "01:00",
        "employees": ["01:00", "07:00", "13:00", "19:00"],
        "devices": "02:00",
        "attendance_logs": ["09:00", "12:00", "17:00", "22:00"]
    },
    "BATCH_SIZE": 100
}
```

### Sync Schedules Explained

| Table | Default Schedule | Rationale |
|-------|-----------------|-----------|
| **departments** | Daily at 01:00 | Small table, rarely changes |
| **employees** | Every 6 hours (01:00, 07:00, 13:00, 19:00) | Medium table, moderate changes |
| **devices** | Daily at 02:00 | Small table, rarely changes |
| **attendance_logs** | Every 4 hours (09:00, 12:00, 17:00, 22:00) | **Critical**, frequent updates |

### Customizing Schedules

Edit `config.json`:

**Sync attendance every 2 hours during work hours:**
```json
"attendance_logs": ["08:00", "10:00", "12:00", "14:00", "16:00", "18:00"]
```

**Sync employees every hour:**
```json
"employees": ["00:00", "01:00", "02:00", ..., "23:00"]
```

**Sync departments weekly (Sundays at 02:00):**
- Requires cron job or Windows Task Scheduler (not supported in current version)

## Database Schema

### Cloud MySQL Tables

#### 1. departments (from personnel_department)

| Column | Type | Description |
|--------|------|-------------|
| id | INT | Department ID (preserved for FK) |
| dept_code | VARCHAR(50) | Department code (unique) |
| dept_name | VARCHAR(200) | Department name |
| parent_dept_id | INT | Parent department (hierarchy) |
| last_sync | DATETIME | When last synced |

#### 2. employees (from personnel_employee)

| Column | Type | Description |
|--------|------|-------------|
| id | INT | Employee ID (preserved for FK) |
| emp_code | VARCHAR(20) | Employee identifier (unique) |
| first_name | VARCHAR(100) | Given name |
| last_name | VARCHAR(100) | Family name |
| display_name | VARCHAR(100) | Nickname/preferred name |
| department_id | INT | FK to departments |
| emp_type | INT | Employee type (full-time, etc.) |
| hire_date | DATE | Date of hiring |
| is_active | BOOLEAN | Active/inactive status |
| mobile | VARCHAR(20) | Contact number |
| email | VARCHAR(50) | Email address |
| last_sync | DATETIME | When last synced |

#### 3. devices (from iclock_terminal)

| Column | Type | Description |
|--------|------|-------------|
| id | INT | Device ID (preserved for FK) |
| terminal_sn | VARCHAR(50) | Serial number (unique) |
| terminal_alias | VARCHAR(50) | Device name/location |
| ip_address | VARCHAR(50) | Device IP address |
| state | INT | Device status (online/offline) |
| is_attendance | BOOLEAN | Is attendance device |
| last_activity | DATETIME | Last communication |
| last_sync | DATETIME | When last synced |

#### 4. attendance_logs (from iclock_transaction)

| Column | Type | Description |
|--------|------|-------------|
| id | INT AUTO_INCREMENT | Primary key |
| emp_code | VARCHAR(20) | Employee ID |
| punch_time | DATETIME | Attendance timestamp |
| punch_state | VARCHAR(5) | 0=IN, 1=OUT, 2-5=Other |
| verify_type | INT | 1=Fingerprint, 2=Face, 3=Card |
| terminal_sn | VARCHAR(50) | Device serial number |
| terminal_alias | VARCHAR(50) | Device location name |
| emp_id | INT | FK to employees |
| terminal_id | INT | FK to devices |
| server_time | DATETIME | When uploaded to cloud |
| source_device | VARCHAR(50) | Always 'zkbiotime' |

### Useful Views

The SQL script creates 3 helpful views:

#### v_attendance_detail
```sql
-- Attendance with employee and device information
SELECT * FROM v_attendance_detail 
WHERE DATE(punch_time) = CURDATE();
```

#### v_employees_active
```sql
-- Active employees with department
SELECT * FROM v_employees_active 
ORDER BY emp_code;
```

#### v_device_status
```sql
-- Device status with health monitoring
SELECT * FROM v_device_status 
WHERE state_name = 'Offline';
```

## Usage

### System Tray Application

**Main Window:**
- Right-click tray icon for menu
- Double-click tray icon for status window

**Status Window:**
- Shows sync status for all 4 tables
- Individual "Sync Now" button per table
- Last sync time and record count
- Refresh button to update status

**Menu Options:**
- **Start Service**: Begin scheduled syncing
- **Stop Service**: Pause scheduled syncing
- **Sync All Tables Now**: Force immediate full sync
- **Check Status**: Show sync status summary
- **Configure**: Edit PostgreSQL and schedule settings
- **View Logs**: View sync operation logs
- **About**: Application information
- **Exit**: Close application

### Manual Sync (Command Line)

```bash
# Sync specific table
python -c "from src.zk_sync_to_cloud import sync_departments; sync_departments()"
python -c "from src.zk_sync_to_cloud import sync_employees; sync_employees()"
python -c "from src.zk_sync_to_cloud import sync_devices; sync_devices()"
python -c "from src.zk_sync_to_cloud import sync_attendance_logs; sync_attendance_logs()"

# Sync all tables
python -c "from src.zk_sync_to_cloud import sync_all_tables; sync_all_tables()"
```

### Checking Sync Status

```bash
# View sync_positions.json
cat sync_positions.json

# Or query MySQL
SELECT * FROM sync_tracking;
```

## Troubleshooting

### "departments table does not exist"

Run `docs/zk_cloud_setup.sql` on your cloud database.

### "PostgreSQL connection failed"

1. Verify ZKBioTime is running
2. Check PostgreSQL service: `services.msc` → look for `bio-pgsql`
3. Verify password in `D:\ZKBioTime\attsite.ini`
4. Check firewall allows port 7496

### "No new records found"

This is normal if:
- For departments/devices: No changes since last sync
- For employees: No employee updates since last sync
- For attendance: No new punches since last sync

Check `sync_positions.json` to see last sync time.

### "Duplicate entry" error

Should not happen due to `ON DUPLICATE KEY UPDATE`. If it does:
1. Check unique constraints in MySQL
2. Verify data integrity in PostgreSQL
3. Check logs for specific error

### Sync is slow

1. Increase `BATCH_SIZE` in config.json (e.g., 500)
2. Check network speed to cloud MySQL
3. Add indexes to MySQL tables (already included in schema)

### Only some tables sync

Check `SYNC_SCHEDULES` in config.json:
- Each table has independent schedule
- Table only syncs at its scheduled time
- Use "Sync Now" for manual sync

## Monitoring

### Check Sync Status

```sql
-- Last sync for each table
SELECT * FROM sync_tracking;

-- Recent attendance records
SELECT * FROM attendance_logs 
ORDER BY server_time DESC 
LIMIT 100;

-- Employee count by department
SELECT d.dept_name, COUNT(e.id) as emp_count
FROM employees e
LEFT JOIN departments d ON e.department_id = d.id
GROUP BY d.dept_name;

-- Device status
SELECT terminal_alias, state, last_activity
FROM devices
ORDER BY terminal_alias;
```

### Data Validation

```sql
-- Compare record counts
SELECT 'PostgreSQL' as source, COUNT(*) as count FROM iclock_transaction
UNION ALL
SELECT 'MySQL', COUNT(*) FROM attendance_logs;

-- Check for missing employees in attendance
SELECT DISTINCT a.emp_code
FROM attendance_logs a
LEFT JOIN employees e ON a.emp_code = e.emp_code
WHERE e.emp_code IS NULL;

-- Verify department hierarchy
SELECT d1.dept_name as dept, d2.dept_name as parent
FROM departments d1
LEFT JOIN departments d2 ON d1.parent_dept_id = d2.id;
```

## Deployment Options

### Option 1: Desktop Application (Tray Icon)

**Best for:** Small offices, single server

```bash
run_zk_tray.bat
```

**Pros:**
- User-friendly interface
- Easy to monitor and control
- Visible status

**Cons:**
- Requires user login
- Must be started manually

### Option 2: Windows Service (NSSM)

**Best for:** Production servers, 24/7 operation

```bash
# Compile executable
compile_service.bat

# Install as Windows Service
nssm install ZKUploadService "D:\zkupload\zkupload_biotime\dist\zkupload_service.exe"
nssm set ZKUploadService StartService SERVICE_AUTO_START
nssm start ZKUploadService
```

**Pros:**
- Runs on boot
- No user login required
- Automatic restart on failure

**Cons:**
- Requires NSSM
- Admin rights needed
- No UI (console logging only)

### Option 3: Windows Task Scheduler

**Best for:** Scheduled syncs only

1. Open Task Scheduler
2. Create Basic Task: "ZK Upload Sync"
3. Trigger: Daily at 01:00, 02:00, etc.
4. Action: `zkupload_service.exe`

**Pros:**
- Built-in Windows feature
- Scheduled execution

**Cons:**
- Not continuous
- More complex to configure multiple schedules

## Security Considerations

1. **Protect `encrypted_credentials.bin`**: Contains encrypted MySQL credentials
2. **Restrict MySQL user permissions**: Only grant SELECT, INSERT, UPDATE
3. **Use SSL for MySQL connections**: Configure in MySQL server
4. **Firewall rules**: Only allow necessary ports (7496 for PostgreSQL, 3306 for MySQL)
5. **Regular backups**: Backup both PostgreSQL and MySQL databases
6. **Data privacy**: Sensitive fields (passwords, SSN) are NOT synced

## Performance Optimization

### Batch Size

| Batch Size | Pros | Cons | Recommended For |
|------------|------|------|-----------------|
| 50 | Less memory, frequent checkpoints | More round-trips | Slow networks |
| 100 (default) | Balanced | - | Most scenarios |
| 500 | Faster sync | More memory | Fast networks, large datasets |
| 1000 | Fastest | Most memory | Very large datasets (>100k records) |

### Indexes

The SQL schema includes optimized indexes:

```sql
-- attendance_logs
INDEX idx_emp_code (emp_code)
INDEX idx_punch_time (punch_time)
INDEX idx_emp_time (emp_code, punch_time)

-- employees
INDEX idx_emp_code (emp_code)
INDEX idx_department_id (department_id)
```

## Data Privacy

**EXCLUDED from sync (sensitive data):**
- ❌ Passwords (self_password, device_password)
- ❌ National ID / SSN
- ❌ Passport numbers
- ❌ Driver's license numbers
- ❌ Photos
- ❌ Bank account details

**INCLUDED (necessary for business):**
- ✅ Employee name and code
- ✅ Department assignment
- ✅ Attendance punches
- ✅ Device information

## Future Enhancements

Potential additions for future versions:

- [ ] **personnel_position** table sync
- [ ] **personnel_company** table sync (multi-company support)
- [ ] Real-time sync (webhook-based)
- [ ] Data compression for large batches
- [ ] Retry mechanism with exponential backoff
- [ ] Email/SMS notifications on sync failures
- [ ] Web dashboard for monitoring
- [ ] REST API for PHP integration

## Support

### Log Files
- Console mode: Displayed in console window
- Tray mode: Right-click tray icon → View Logs

### Configuration Files
- `config.json`: Edit with text editor or tray Configure dialog
- `encrypted_credentials.bin`: Auto-generated by encrypt_credentials.bat
- `sync_positions.json`: Auto-generated, tracks sync progress

### Important Paths
```
ZKBioTime PostgreSQL: D:\ZKBioTime\attsite.ini (password here)
Application Config:   D:\zkupload\zkupload_biotime\config.json
Sync Positions:       D:\zkupload\zkupload_biotime\sync_positions.json
Logs:                 D:\zkupload\zkupload_biotime\logs\
```

## Version History

- **v2.0** (2026-03-14): 4-Table Sync
  - Added departments, employees, devices tables
  - Per-table sync schedules
  - Individual table sync controls
  - Sync position tracking per table
  - Enhanced status window

- **v1.0** (2026-03-14): Initial release
  - attendance_logs table only
  - Basic scheduled sync

---

**Note:** This application is designed to work with ZKBioTime 9.x and MySQL 5.7+/8.0+

**Last Updated:** 2026-03-14  
**Version:** 2.0
