# ZK BioTime Cloud Sync - Testing Guide

## Pre-Testing Checklist

Before starting tests, ensure:

- [ ] ZKBioTime is installed and running
- [ ] PostgreSQL database is accessible
- [ ] Cloud MySQL database is set up
- [ ] Python 3.8+ is installed
- [ ] Git repository is cloned

---

## Phase 1: Environment Setup Testing

### Step 1.1: Install Dependencies

```bash
cd D:\zkupload\zkupload_biotime

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Expected Result:**
- ✅ All packages install successfully
- ✅ No error messages

**Troubleshooting:**
```bash
# If psycopg2 fails to install
pip install psycopg2-binary

# If PyQt5 fails
pip install PyQt5
```

---

### Step 1.2: Verify PostgreSQL Connection

```bash
# Run test script
test_postgres.bat
```

**Expected Result:**
```
=== ZK BioTime PostgreSQL Connection Test ===

Configuration:
  Host: 127.0.0.1
  Port: 7496
  Database: biotime
  User: postgres

✅ PostgreSQL connection successful!

✅ iclock_transaction table found!
   Total columns: 27

📊 Total records in iclock_transaction: 1,234
```

**Troubleshooting:**

If connection fails:
1. Check ZKBioTime is running
2. Verify PostgreSQL service: `services.msc` → look for `bio-pgsql`
3. Check password in `D:\ZKBioTime\attsite.ini`
4. Verify port 7496 is not blocked by firewall

---

### Step 1.3: Setup Cloud MySQL Database

```bash
# On your cloud MySQL server, run:
mysql -h your-cloud-host -u your-user -p your-database < docs/zk_cloud_setup.sql
```

**Expected Result:**
```
Tables created:
- departments
- employees
- devices
- attendance_logs
- sync_tracking

Views created:
- v_attendance_detail
- v_employees_active
- v_device_status
```

**Verify Tables:**
```sql
-- Check all tables exist
SHOW TABLES;

-- Expected output:
-- attendance_logs
-- departments
-- devices
-- employees
-- sync_tracking
-- v_attendance_detail (view)
-- v_employees_active (view)
-- v_device_status (view)
```

---

## Phase 2: Configuration Testing

### Step 2.1: Configure PostgreSQL Connection

Edit `config.json`:

```json
{
    "POSTGRESQL_CONFIG": {
        "host": "127.0.0.1",
        "port": 7496,
        "database": "biotime",
        "user": "postgres",
        "password": "YOUR_PASSWORD_FROM_attsite.ini"
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

**Find Password:**
```
File: D:\ZKBioTime\attsite.ini
Section: [DATABASE]
Key: PASSWORD
```

---

### Step 2.2: Encrypt Cloud MySQL Credentials

```bash
# Run encryption utility
encrypt_credentials.bat
```

**Input when prompted:**
```
Host: your-cloud-host.com
Port: 3306
Database: zk_attendance_cloud
Username: your_mysql_user
Password: your_mysql_password
```

**Expected Result:**
```
✅ Credentials encrypted and saved to: encrypted_credentials.bin

⚠️  IMPORTANT:
   - Keep this file secure
   - Never share this file with unauthorized persons

--- Verification ---
Host: your-cloud-host.com
Port: 3306
Database: zk_attendance_cloud
User: your_mysql_user
Password: ********

✅ Verification successful - credentials can be decrypted
```

**Troubleshooting:**

If file is created but verification fails:
- Delete `encrypted_credentials.bin` and try again
- Ensure encryption key matches in all files

---

### Step 2.3: Test MySQL Connection

```bash
# Test connection to cloud MySQL
python -c "from src.zk_sync_to_cloud import connect_to_mysql; conn = connect_to_mysql(); print('MySQL OK' if conn else 'MySQL FAILED'); conn.close()"
```

**Expected Result:**
```
MySQL OK
```

---

## Phase 3: Sync Testing

### Step 3.1: Test Individual Table Sync

**Test Departments Sync:**
```bash
python -c "from src.zk_sync_to_cloud import sync_departments; result = sync_departments(); print(f'Departments synced: {result} records')"
```

**Expected Result:**
```
=== Starting Departments Sync (Full Sync) ===
Found 15 departments in PostgreSQL
Uploaded 15 departments to cloud MySQL
Departments synced: 15 records
```

**Test Employees Sync:**
```bash
python -c "from src.zk_sync_to_cloud import sync_employees; result = sync_employees(); print(f'Employees synced: {result} records')"
```

**Test Devices Sync:**
```bash
python -c "from src.zk_sync_to_cloud import sync_devices; result = sync_devices(); print(f'Devices synced: {result} records')"
```

**Test Attendance Logs Sync:**
```bash
python -c "from src.zk_sync_to_cloud import sync_attendance_logs; result = sync_attendance_logs(); print(f'Attendance synced: {result} records')"
```

---

### Step 3.2: Verify Data in Cloud MySQL

```sql
-- Check departments
SELECT COUNT(*) FROM departments;

-- Check employees
SELECT COUNT(*) FROM employees;

-- Check devices
SELECT COUNT(*) FROM devices;

-- Check attendance_logs
SELECT COUNT(*) FROM attendance_logs;

-- Check sync tracking
SELECT * FROM sync_tracking;
```

**Expected Result:**
- All tables should have records
- sync_tracking should show 'completed' status

---

### Step 3.3: Test Full Sync (All Tables)

```bash
python -c "from src.zk_sync_to_cloud import sync_all_tables; sync_all_tables()"
```

**Expected Result:**
```
========================================
Starting Full 4-Table Sync
========================================
Step 1: Syncing Departments...
=== Starting Departments Sync (Full Sync) ===
Uploaded 15 departments
Step 2: Syncing Devices...
=== Starting Devices Sync (Incremental) ===
Uploaded 5 devices
Step 3: Syncing Employees...
=== Starting Employees Sync (Incremental) ===
Uploaded 234 employees
Step 4: Syncing Attendance Logs...
=== Starting Attendance Logs Sync (Incremental) ===
Found 1234 records. Processing...
Uploaded 1234 attendance records
========================================
Sync Completed!
  Departments: 15 records
  Devices: 5 records
  Employees: 234 records
  Attendance: 1234 records
========================================
```

---

### Step 3.4: Test Duplicate Prevention

Run the sync again immediately:

```bash
python -c "from src.zk_sync_to_cloud import sync_attendance_logs; sync_attendance_logs()"
```

**Expected Result:**
```
=== Starting Attendance Logs Sync (Incremental) ===
No new attendance records found
```

This confirms:
- ✅ Sync position is tracked correctly
- ✅ No duplicate records are created

---

## Phase 4: Application Testing

### Step 4.1: Test Tray Application

```bash
# Run tray application
run_zk_tray.bat
```

**Expected Behavior:**
1. ✅ Application window appears (optional)
2. ✅ System tray icon appears (bottom-right)
3. ✅ Right-click shows menu with options

**Test Menu Items:**
- Right-click tray icon
- Click "Check Status"
- Should show service status and sync positions

**Test Configuration Dialog:**
- Right-click tray icon → Configure
- Verify PostgreSQL settings are displayed
- Verify sync schedules are displayed
- Click Cancel (don't save changes)

**Test Log Viewer:**
- Right-click tray icon → View Logs
- Should show log messages

---

### Step 4.2: Test Manual Sync

**From Tray Icon:**
1. Right-click tray icon
2. Click "Sync All Tables Now"
3. Watch logs in console window
4. Verify sync completes successfully

**From Status Window:**
1. Double-click tray icon
2. Click individual "Sync Now" buttons
3. Verify each table syncs independently

---

### Step 4.3: Test Scheduled Sync

**Wait for next scheduled time** (e.g., 09:00, 12:00, 17:00, or 22:00)

**Expected Behavior:**
- At scheduled time, sync should start automatically
- Check logs to confirm
- Verify records appear in cloud MySQL

---

## Phase 5: Integration Testing

### Step 5.1: Test Data Integrity

```sql
-- Verify JOIN works correctly
SELECT 
    a.emp_code,
    e.first_name,
    e.last_name,
    d.dept_name,
    a.punch_time,
    a.punch_state
FROM attendance_logs a
LEFT JOIN employees e ON a.emp_id = e.id
LEFT JOIN departments d ON e.department_id = d.id
LIMIT 10;
```

**Expected Result:**
- Should return records without errors
- Employee names should match emp_code
- Department names should be populated

---

### Step 5.2: Test Views

```sql
-- Test v_attendance_detail
SELECT * FROM v_attendance_detail 
WHERE DATE(punch_time) = CURDATE()
LIMIT 10;

-- Test v_employees_active
SELECT * FROM v_employees_active 
ORDER BY emp_code
LIMIT 10;

-- Test v_device_status
SELECT * FROM v_device_status;
```

**Expected Result:**
- All views should return data
- No NULL values in critical fields

---

### Step 5.3: Test with PHP Application

**Sample PHP Connection Test:**

```php
<?php
$host = 'your-cloud-host';
$db = 'your-database';
$user = 'your-username';
$pass = 'your-password';

try {
    $pdo = new PDO("mysql:host=$host;dbname=$db;charset=utf8mb4", $user, $pass);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    
    // Test query
    $stmt = $pdo->query("SELECT COUNT(*) as count FROM attendance_logs");
    $result = $stmt->fetch();
    echo "Attendance records: " . $result['count'];
    
} catch (PDOException $e) {
    echo "Connection failed: " . $e->getMessage();
}
?>
```

---

## Phase 6: Performance Testing

### Step 6.1: Test Large Dataset Sync

**If you have many records (>10,000):**

```bash
# Time the sync
python -c "import time; start = time.time(); from src.zk_sync_to_cloud import sync_attendance_logs; sync_attendance_logs(); print(f'Time: {time.time() - start:.2f}s')"
```

**Expected Performance:**
- 1,000 records: ~5-10 seconds
- 10,000 records: ~30-60 seconds
- 100,000 records: ~5-10 minutes

---

### Step 6.2: Test Batch Processing

Edit `config.json` to test different batch sizes:

```json
{
    "BATCH_SIZE": 50  // Test with smaller batches
}
```

**Expected Behavior:**
- Sync processes in smaller chunks
- More frequent log messages
- Same final result

---

## Phase 7: Error Handling Testing

### Step 7.1: Test PostgreSQL Connection Failure

1. Stop PostgreSQL service temporarily
2. Run sync
3. Verify error is logged
4. Restart PostgreSQL service

**Expected Behavior:**
- Application doesn't crash
- Error is logged clearly
- Next sync attempt works

---

### Step 7.2: Test MySQL Connection Failure

1. Disconnect network or use wrong credentials
2. Run sync
3. Verify error handling

**Expected Behavior:**
- Application doesn't crash
- Error is logged
- Sync position is preserved

---

### Step 7.3: Test Power Failure Recovery

1. Start sync with many records
2. Interrupt mid-sync (Ctrl+C)
3. Check sync_positions.json
4. Restart sync

**Expected Behavior:**
- Sync resumes from last successful batch
- No data loss or corruption
- No duplicate records

---

## Success Criteria

All tests pass if:

- [x] All dependencies install successfully
- [x] PostgreSQL connection works
- [x] MySQL connection works
- [x] All 4 tables sync successfully
- [x] Sync positions are tracked
- [x] Duplicate prevention works
- [x] Tray application runs without errors
- [x] Scheduled sync works
- [x] Data integrity is maintained
- [x] Views return correct data
- [x] Error handling works properly
- [x] Performance is acceptable

---

## Test Report Template

```
Test Date: _______________
Tester: _______________

Environment:
- ZKBioTime Version: _______
- Python Version: _______
- MySQL Version: _______

Test Results:
- Phase 1 (Setup): ☐ Pass ☐ Fail
- Phase 2 (Config): ☐ Pass ☐ Fail
- Phase 3 (Sync): ☐ Pass ☐ Fail
- Phase 4 (App): ☐ Pass ☐ Fail
- Phase 5 (Integration): ☐ Pass ☐ Fail
- Phase 6 (Performance): ☐ Pass ☐ Fail
- Phase 7 (Error Handling): ☐ Pass ☐ Fail

Issues Found:
1. _______________________
2. _______________________
3. _______________________

Overall Status: ☐ READY FOR PRODUCTION ☐ NEEDS FIXES
```

---

## Next Steps After Testing

If all tests pass:

1. ✅ Deploy to production server
2. ✅ Setup Windows Service or Task Scheduler
3. ✅ Configure monitoring and alerts
4. ✅ Train operations team
5. ✅ Handover to PHP team for integration

If tests fail:

1. 📝 Document the issue
2. 🔍 Check logs for errors
3. 🐛 Fix the issue
4. 🔄 Re-test
5. ✅ Verify fix

---

**Good luck with testing! 🚀**
