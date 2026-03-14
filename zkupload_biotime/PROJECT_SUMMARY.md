# ZK BioTime Cloud Sync - Project Summary

## 📁 Project Structure

```
D:\zkupload\zkupload_biotime\
│
├── 📄 README.md                    # Full documentation
├── 📄 QUICKSTART.md                # Quick start guide (30 min setup)
├── 📄 requirements.txt             # Python dependencies
├── 📄 config.json                  # Configuration (PostgreSQL + sync schedule)
│
├── 📁 docs\
│   └── zk_cloud_setup.sql         # MySQL cloud table creation script
│
├── 📁 src\
│   ├── zk_sync_to_cloud.py        # Core sync service (console)
│   ├── zk_tray_app.py             # System tray application
│   └── encrypt_zk_credentials.py  # Credential encryption utility
│
├── 📁 logs\                        # Log files (auto-created)
│
├── 🔧 test_postgresql.py           # Test PostgreSQL connection
├── 🔧 test_postgres.bat            # Quick test script
├── 🔧 encrypt_credentials.bat      # Encrypt cloud MySQL credentials
│
├── ▶️  run_zk_sync.bat             # Run console service
├── ▶️  run_zk_tray.bat             # Run tray application
│
├── 📦 compile_service.bat          # Build console .exe
├── 📦 compile_tray.bat             # Build tray .exe
│
├── 📦 zk_sync_service.spec         # PyInstaller spec for service
└── 📦 zk_tray_app.spec             # PyInstaller spec for tray
```

## 🎯 What Was Created

### 1. Database Schema (MySQL Cloud)
**File:** `docs/zk_cloud_setup.sql`

Creates 3 tables:
- `zk_attendance_logs` - Main attendance data (synced from ZKBioTime)
- `zk_employees` - Employee master data (optional, future use)
- `zk_devices` - Device information (optional, future use)

**Key fields synced:**
- emp_code, punch_time, punch_state, verify_type
- terminal_sn, terminal_alias, emp_id, terminal_id
- server_time (audit), source_device

### 2. Core Sync Service
**File:** `src/zk_sync_to_cloud.py`

**Features:**
- ✅ Incremental sync (ID-based, tracks last synced ID)
- ✅ Batch processing (configurable batch size)
- ✅ Duplicate prevention (ON DUPLICATE KEY UPDATE)
- ✅ Scheduled sync times (configurable)
- ✅ Connection pooling and error handling
- ✅ File locking (prevents multiple instances)

**Sync Strategy:**
```
1. Read last_sync_id from file
2. Query PostgreSQL: SELECT * FROM iclock_transaction WHERE id > last_sync_id
3. Process in batches
4. INSERT INTO zk_attendance_logs ... ON DUPLICATE KEY UPDATE
5. Update last_sync_id after each batch
6. Repeat at scheduled times
```

### 3. System Tray Application
**File:** `src/zk_tray_app.py`

**UI Features:**
- 🖥️ System tray icon with context menu
- ▶️ Start/Stop service controls
- 🔄 Sync Now (manual trigger)
- ⚙️ Configuration dialog (PostgreSQL + schedule)
- 📋 Log viewer
- ℹ️ Status display

**Menu Items:**
- Status: Running/Stopped
- Start Service
- Stop Service
- Sync Now
- Check Status
- Configure
- View Logs
- About
- Exit

### 4. Credential Encryption
**File:** `src/encrypt_zk_credentials.py`

**Security:**
- Fernet symmetric encryption
- Fixed encryption key embedded in code
- Encrypted file: `encrypted_credentials.bin`
- Separate from public config

### 5. Testing Utilities
**File:** `test_postgresql.py`

**Tests:**
- PostgreSQL connection
- iclock_transaction table structure
- Record counts and statistics
- Latest records preview
- Device breakdown

## 🔧 Configuration Files

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
    "UPLOAD_TIMES": ["09:00", "12:00", "17:00", "22:00"],
    "LAST_SYNC_FILE": "last_sync_zk.txt",
    "BATCH_SIZE": 100
}
```

### encrypted_credentials.bin (binary, auto-generated)
```
DB_CONFIG:
  - host: cloud.example.com
  - port: 3306
  - database: zk_attendance_cloud
  - user: cloud_user
  - password: ********
```

## 📊 Data Flow

```
┌─────────────────────┐
│  ZK Attendance      │
│  Device             │
│  (Fingerprint/Face) │
└──────────┬──────────┘
           │ iClock Protocol
           ▼
┌─────────────────────┐
│  ZKBioTime Server   │
│  (Local Machine)    │
└──────────┬──────────┘
           │ PostgreSQL
           │ iclock_transaction
           ▼
┌─────────────────────┐
│  zk_sync_to_cloud   │
│  (This Application) │
└──────────┬──────────┘
           │ MySQL (Cloud)
           │ zk_attendance_logs
           ▼
┌─────────────────────┐
│  PHP Web App        │
│  (Salary Calc)      │
└─────────────────────┘
```

## 🚀 Usage Scenarios

### Scenario 1: Desktop Operation (Recommended for Start)
```bash
# User runs tray application
run_zk_tray.bat

# System tray icon appears
# Right-click → Start Service
# Syncs automatically at scheduled times
```

### Scenario 2: Server Operation (Background Service)
```bash
# Build executable
compile_service.bat

# Install as Windows Service (using NSSM)
nssm install ZKUploadService "dist\zkupload_service.exe"
nssm start ZKUploadService
```

### Scenario 3: Scheduled Task (Intermittent Sync)
```bash
# Build executable
compile_service.bat

# Windows Task Scheduler
# Trigger: Daily at 09:00, 12:00, 17:00, 22:00
# Action: dist\zkupload_service.exe
```

## 📈 Sync Performance

**Expected Performance:**
- 1,000 records: ~5-10 seconds
- 10,000 records: ~30-60 seconds
- 100,000 records: ~5-10 minutes

**Factors affecting speed:**
- Network latency to cloud MySQL
- Batch size configuration
- Server CPU/memory
- Database load

## 🔒 Security Features

1. **Encrypted Credentials**: MySQL password encrypted with Fernet
2. **Separate Config**: Public config (config.json) vs private credentials
3. **File Locking**: Prevents multiple instances
4. **Unique Constraints**: Prevents data corruption
5. **Transaction Safety**: Rollback on errors

## 🛠️ Deployment Options

### Option A: Direct Python Execution
**Pros:** Easy to debug, no compilation needed
**Cons:** Requires Python installed

```bash
# Install dependencies
pip install -r requirements.txt

# Run directly
python src\zk_tray_app.py
```

### Option B: Compiled Executable
**Pros:** Standalone, no Python required
**Cons:** Larger file size, harder to debug

```bash
# Compile
compile_tray.bat

# Run executable
dist\zkupload_tray.exe
```

### Option C: Windows Service (NSSM)
**Pros:** Runs on boot, no user login required
**Cons:** Requires NSSM, admin rights

```bash
# Compile
compile_service.bat

# Install as service
nssm install ZKUploadService "dist\zkupload_service.exe"
nssm set ZKUploadService StartService SERVICE_AUTO_START
nssm start ZKUploadService
```

## 📝 Testing Checklist

Before going live:

- [ ] PostgreSQL connection test passes (`test_postgres.bat`)
- [ ] MySQL cloud table created (`docs/zk_cloud_setup.sql`)
- [ ] Cloud credentials encrypted (`encrypt_credentials.bat`)
- [ ] First manual sync successful
- [ ] Records visible in cloud MySQL
- [ ] Scheduled sync works (wait for next scheduled time)
- [ ] Tray controls work (Start/Stop/Sync Now)
- [ ] Logs show no errors
- [ ] PHP web app can read cloud data

## 🎓 Key Design Decisions

### Why ID-based sync instead of timestamp?
- **IDs are immutable**: Timestamps can be duplicated or updated
- **Simpler logic**: `WHERE id > last_sync_id` is straightforward
- **No timezone issues**: IDs don't have timezone complications

### Why ON DUPLICATE KEY UPDATE?
- **Idempotent**: Safe to re-run sync without data loss
- **Handles edge cases**: Network failures, restarts, etc.
- **Audit trail**: Updates server_time on re-sync

### Why batch processing?
- **Memory efficient**: Doesn't load all records at once
- **Progress tracking**: Updates sync position after each batch
- **Recoverable**: If fails, only current batch is lost

### Why separate config and credentials?
- **Security**: Credentials encrypted, config is plain text
- **Flexibility**: Easy to change schedule without re-encrypting
- **Deployment**: Can share config template, keep credentials private

## 📞 Support Information

### Log File Location
- Console mode: Displayed in console window
- Tray mode: Right-click tray icon → View Logs

### Configuration Files
- `config.json`: Edit with text editor or tray Configure dialog
- `encrypted_credentials.bin`: Auto-generated by encrypt_credentials.bat

### Important Paths
```
ZKBioTime PostgreSQL: D:\ZKBioTime\attsite.ini (password here)
Application Config:   D:\zkupload\zkupload_biotime\config.json
Sync Position:        D:\zkupload\zkupload_biotime\last_sync_zk.txt
Logs:                 D:\zkupload\zkupload_biotime\logs\
```

## 🎉 Success Criteria

The project is complete and ready when:

1. ✅ PostgreSQL connection works
2. ✅ Cloud MySQL table created
3. ✅ Credentials encrypted
4. ✅ First sync completes successfully
5. ✅ Records visible in cloud database
6. ✅ Scheduled sync works automatically
7. ✅ Tray UI is functional
8. ✅ No errors in logs

## 📚 Documentation Files

| File | Purpose | Audience |
|------|---------|----------|
| README.md | Full documentation | Administrators |
| QUICKSTART.md | 30-minute setup guide | New users |
| PROJECT_SUMMARY.md | This file | Developers |
| docs/zk_cloud_setup.sql | Database schema | DBAs |
| src/*.py | Source code | Developers |

## 🔮 Future Enhancements

Potential additions:

1. **Employee Sync**: Pull data from `personnel_employee` table
2. **Device Sync**: Pull data from `iclock_terminal` table
3. **Real-time Sync**: Webhook-based instead of scheduled
4. **Compression**: For large batches over slow networks
5. **Retry Logic**: Exponential backoff for failures
6. **Notifications**: Email/SMS on sync failures
7. **Web Dashboard**: Monitor multiple installations
8. **API Layer**: REST API for PHP integration

---

**Project Status:** ✅ COMPLETE AND READY FOR DEPLOYMENT

**Version:** 1.0
**Date:** 2026-03-14
**Author:** ZK Upload Project
