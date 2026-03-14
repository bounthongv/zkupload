# Quick Start Guide

## First Time Setup (30 minutes)

### Step 1: Install Dependencies (5 min)

```bash
cd D:\zkupload\zkupload_biotime

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### Step 2: Create Cloud Database Table (5 min)

1. Login to your cloud MySQL (phpMyAdmin or MySQL Workbench)
2. Create new database (e.g., `zk_attendance_cloud`)
3. Run SQL: `docs/zk_cloud_setup.sql`

### Step 3: Configure PostgreSQL (5 min)

1. Open `D:\ZKBioTime\attsite.ini`
2. Copy the PostgreSQL password
3. Edit `config.json`:
   ```json
   {
       "POSTGRESQL_CONFIG": {
           "password": "PASTE_PASSWORD_HERE"
       }
   }
   ```

### Step 4: Test PostgreSQL Connection (2 min)

```bash
test_postgres.bat
```

✅ Should show table structure and record count

### Step 5: Encrypt Cloud Credentials (3 min)

```bash
encrypt_credentials.bat
```

Enter your cloud MySQL details when prompted.

### Step 6: Run First Sync (5 min)

**Option A - Tray Application (Recommended):**

```bash
run_zk_tray.bat
```

Right-click tray icon → Sync Now

**Option B - Console Mode:**

```bash
run_zk_sync.bat
```

### Step 7: Verify on Cloud (2 min)

Check your cloud MySQL:

```sql
SELECT COUNT(*) FROM zk_attendance_logs;
SELECT * FROM zk_attendance_logs ORDER BY server_time DESC LIMIT 10;
```

✅ **Done!** Your attendance data is now syncing to the cloud.

---

## Daily Operation

### Starting the Service

1. Double-click `zkupload_tray.exe` (or run `run_zk_tray.bat`)
2. Look for tray icon (bottom-right of screen)
3. Right-click → Start Service

### Stopping the Service

1. Right-click tray icon
2. Click "Stop Service" or "Exit"

### Checking Sync Status

1. Right-click tray icon
2. Click "Check Status" or "View Logs"

### Manual Sync

1. Right-click tray icon
2. Click "Sync Now"

---

## Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| "Credentials not found" | Run `encrypt_credentials.bat` |
| "PostgreSQL connection failed" | Check password in `config.json` |
| "MySQL table does not exist" | Run `docs/zk_cloud_setup.sql` |
| "No new records" | Check if device is pushing to ZKBioTime |
| Service won't start | Check logs in tray icon → View Logs |

---

## Configuration Tips

### Change Sync Schedule

Edit `config.json`:

```json
"UPLOAD_TIMES": ["08:00", "12:00", "17:00"]  // Sync at 8am, 12pm, 5pm
```

### Change Batch Size

For faster sync (larger batches):

```json
"BATCH_SIZE": 500  // Default is 100
```

For slower but more reliable sync:

```json
"BATCH_SIZE": 50
```

---

## What's Synced?

**Synced Fields:**

| Field | Description |
|-------|-------------|
| emp_code | Employee ID |
| punch_time | Check-in/out time |
| punch_state | IN/OUT status |
| verify_type | Fingerprint/Face/Card |
| terminal_sn | Device serial number |
| terminal_alias | Device location |

**Not Synced (yet):**

- Employee personal data (name, department)
- Device configuration
- Attendance rules
- Shift schedules

---

## Next Steps

After basic setup is working:

1. **Test with PHP Web App**: Connect your salary calculation system to cloud MySQL
2. **Set Up Auto-Start**: Use Windows Task Scheduler or NSSM to run on boot
3. **Monitor Sync**: Check cloud database daily for first week
4. **Backup**: Set up automated backups for both databases

---

## Support Checklist

Before asking for help, check:

- [ ] PostgreSQL connection works (`test_postgres.bat`)
- [ ] MySQL credentials encrypted (`encrypted_credentials.bin` exists)
- [ ] `zk_attendance_logs` table created on cloud
- [ ] ZKBioTime is running (`services.msc` → bio-* services)
- [ ] Firewall allows PostgreSQL (7496) and MySQL (3306)
- [ ] Logs show no errors (tray icon → View Logs)

---

**Need more help?** See full documentation in `README.md`
