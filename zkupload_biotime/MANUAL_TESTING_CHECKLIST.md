# 📋 Manual Testing Checklist

**For:** ZK BioTime Cloud Sync v2.0 (4-Table Sync)

**When to use:** When you have:
- [ ] Cloud MySQL database created
- [ ] Python environment fixed (see IMPORTANT_PYTHON_FIX.md)
- [ ] 15-20 minutes of uninterrupted time

---

## 📝 Pre-Testing Preparation

### Step 1: Fix Python Environment (if needed)

**If you see "SRE module mismatch" error:**

```bash
# Delete corrupted file
del D:\ZKBioTime\Python311\Lib\site-packages\zope.event-4.6-py3.9-nspkg.pth
```

### Step 2: Setup Python Environment

```bash
cd D:\zkupload\zkupload_biotime

# Create virtual environment
py -m venv venv

# Activate
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**✅ Expected:** All packages install without errors

---

## 🗄️ Step 3: Create Cloud Database

**On your cloud MySQL server:**

```bash
mysql -h YOUR_CLOUD_HOST -u YOUR_USER -p YOUR_DATABASE < docs/zk_cloud_setup.sql
```

**✅ Expected:** 
- 4 tables created (departments, employees, devices, attendance_logs)
- 1 tracking table (sync_tracking)
- 3 views created

**Verify:**
```sql
SHOW TABLES;
-- Should show: attendance_logs, departments, devices, employees, sync_tracking, + 3 views
```

---

## ⚙️ Step 4: Configure Application

### 4.1: Edit config.json

Open `config.json` and update:

```json
{
    "POSTGRESQL_CONFIG": {
        "host": "127.0.0.1",
        "port": 7496,
        "database": "biotime",
        "user": "postgres",
        "password": "COPY_FROM_D:\\ZKBioTime\\attsite.ini"
    }
}
```

**Find password in:** `D:\ZKBioTime\attsite.ini` → `[DATABASE]` section

### 4.2: Encrypt Cloud Credentials

```bash
encrypt_credentials.bat
```

**Enter when prompted:**
- Host: your cloud MySQL host
- Port: 3306
- Database: your database name
- User: your MySQL username
- Password: your MySQL password

**✅ Expected:** "Credentials encrypted successfully"

---

## 🧪 Step 5: Test PostgreSQL Connection

```bash
test_postgres.bat
```

**✅ Expected Output:**
```
✅ PostgreSQL connection successful!
✅ iclock_transaction table found!
📊 Total records in iclock_transaction: X,XXX
```

**❌ If fails:**
- Check ZKBioTime is running
- Verify password in `D:\ZKBioTime\attsite.ini`
- Check PostgreSQL service is running

---

## 🔄 Step 6: Test First Sync

### 6.1: Test Individual Table Sync

```bash
# Test departments
python -c "from src.zk_sync_to_cloud import sync_departments; sync_departments()"

# Test employees
python -c "from src.zk_sync_to_cloud import sync_employees; sync_employees()"

# Test devices
python -c "from src.zk_sync_to_cloud import sync_devices; sync_devices()"

# Test attendance logs
python -c "from src.zk_sync_to_cloud import sync_attendance_logs; sync_attendance_logs()"
```

**✅ Expected:** Each should report number of records synced

### 6.2: Verify on Cloud MySQL

```sql
-- Check record counts
SELECT 'departments' as table_name, COUNT(*) as count FROM departments
UNION ALL
SELECT 'employees', COUNT(*) FROM employees
UNION ALL
SELECT 'devices', COUNT(*) FROM devices
UNION ALL
SELECT 'attendance_logs', COUNT(*) FROM attendance_logs;

-- Check sync status
SELECT * FROM sync_tracking;
```

**✅ Expected:** All tables should have records, status = 'completed'

---

## 🖥️ Step 7: Test Tray Application

```bash
run_zk_tray.bat
```

**✅ Expected:**
- System tray icon appears (bottom-right)
- No error messages

**Test Menu:**
1. Right-click tray icon
2. Click "Check Status"
3. Should show sync status for all 4 tables

**Test Sync:**
1. Right-click tray icon
2. Click "Sync All Tables Now"
3. Watch console window for progress

---

## 🔁 Step 8: Test Duplicate Prevention

Run sync again:

```bash
python -c "from src.zk_sync_to_cloud import sync_attendance_logs; sync_attendance_logs()"
```

**✅ Expected:** "No new attendance records found"

This confirms sync position is tracked correctly.

---

## 📊 Step 9: Verify Data Integrity

**On cloud MySQL:**

```sql
-- Test JOIN query
SELECT 
    a.emp_code,
    e.first_name,
    d.dept_name,
    a.punch_time,
    a.punch_state
FROM attendance_logs a
LEFT JOIN employees e ON a.emp_id = e.id
LEFT JOIN departments d ON e.department_id = d.id
LIMIT 10;

-- Test view
SELECT * FROM v_attendance_detail LIMIT 10;
```

**✅ Expected:** Returns data with employee names and departments

---

## ⏰ Step 10: Test Scheduled Sync

**Wait for next scheduled time:**
- Attendance logs: 09:00, 12:00, 17:00, or 22:00
- Employees: 01:00, 07:00, 13:00, or 19:00

**✅ Expected:** Sync runs automatically at scheduled time

**Check logs to confirm.**

---

## ✅ Testing Complete Checklist

Mark as complete when done:

- [ ] Python environment working
- [ ] Cloud database created
- [ ] config.json configured
- [ ] Credentials encrypted
- [ ] PostgreSQL connection works
- [ ] All 4 tables sync successfully
- [ ] Data appears in cloud MySQL
- [ ] Tray application runs
- [ ] Duplicate prevention works
- [ ] Data integrity verified (JOINs work)
- [ ] Scheduled sync works

---

## 📝 Test Results Template

**Date:** _______________

**Environment:**
- ZKBioTime Version: _______
- Python Version: _______
- MySQL Version: _______

**Results:**
- PostgreSQL Connection: ☐ Pass ☐ Fail
- Departments Sync: ☐ Pass ☐ Fail
- Employees Sync: ☐ Pass ☐ Fail
- Devices Sync: ☐ Pass ☐ Fail
- Attendance Sync: ☐ Pass ☐ Fail
- Tray App: ☐ Pass ☐ Fail
- Duplicate Prevention: ☐ Pass ☐ Fail
- Data Integrity: ☐ Pass ☐ Fail

**Issues Found:**
1. _______________________
2. _______________________

**Overall:** ☐ READY ☐ NEEDS FIXES

---

## 🆘 Common Issues & Solutions

### "PostgreSQL connection failed"
- Check ZKBioTime is running
- Verify password in `D:\ZKBioTime\attsite.ini`
- Check PostgreSQL service: `services.msc` → `bio-pgsql`

### "MySQL connection failed"
- Check cloud MySQL is accessible
- Verify credentials in `encrypted_credentials.bin`
- Check firewall allows port 3306

### "No new records found"
- This is normal if no new data since last sync
- Check `sync_positions.json` for last sync time

### "Table does not exist"
- Run `docs/zk_cloud_setup.sql` on cloud MySQL
- Verify database name is correct

---

## 📞 Need Help?

1. Check logs in application
2. Review `README.md` troubleshooting section
3. Check `TESTING_GUIDE.md` for detailed tests

---

**Good luck with testing! 🚀**

Take your time and report back any issues you find.
