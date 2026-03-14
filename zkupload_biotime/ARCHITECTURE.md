# System Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    ZK ATTENDANCE DEVICE                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Fingerprint  │  │ Face Scanner │  │ Card Reader  │          │
│  │ Scanner      │  │              │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                 │
│  Network: 192.168.100.x                                        │
│  Protocol: iClock (push to server)                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Push attendance data
                         │ (real-time via iClock protocol)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ZKBIOTIME SERVER (LOCAL)                      │
│              Machine: Same network as device                    │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  bio-server (ZKBioTime Web Application)                  │  │
│  │  - Device management                                     │  │
│  │  - Employee management                                   │  │
│  │  - Attendance rules                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  PostgreSQL Database (port 7496)                         │  │
│  │                                                          │  │
│  │  Table: iclock_transaction                               │  │
│  │  ┌────────────────────────────────────────────────────┐ │  │
│  │  │ id | emp_code | punch_time | punch_state | ...     │ │  │
│  │  │ 1  | EMP001   | 2026-03-14   | 0           | ...   │ │  │
│  │  │ 2  | EMP002   | 2026-03-14   | 1           | ...   │ │  │
│  │  │ ...                                                 │ │  │
│  │  └────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Read new records
                         │ (SELECT WHERE id > last_sync_id)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              ZK UPLOAD SYNC SERVICE (THIS APPLICATION)          │
│              Machine: Same as ZKBioTime server                  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  config.json                                             │  │
│  │  - PostgreSQL connection settings                        │  │
│  │  - Upload schedule: ["09:00", "12:00", "17:00", "22:00"]│  │
│  │  - Batch size: 100                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  encrypted_credentials.bin                               │  │
│  │  - Cloud MySQL credentials (encrypted)                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Sync Engine                                             │  │
│  │                                                          │  │
│  │  1. Read last_sync_id from file                          │  │
│  │  2. Query PostgreSQL for new records                     │  │
│  │  3. Process in batches                                   │  │
│  │  4. INSERT to MySQL with ON DUPLICATE KEY UPDATE         │  │
│  │  5. Update last_sync_id after each batch                 │  │
│  │  6. Wait for next scheduled time                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  System Tray UI (zk_tray_app.py)                         │  │
│  │  - Start/Stop service                                    │  │
│  │  - Sync Now button                                       │  │
│  │  - Configuration dialog                                  │  │
│  │  - Log viewer                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Upload via Internet
                         │ (MySQL protocol, port 3306)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CLOUD MYSQL DATABASE                         │
│              Host: cloud.example.com (public IP)                │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Database: zk_attendance_cloud                           │  │
│  │                                                          │  │
│  │  Table: zk_attendance_logs                               │  │
│  │  ┌────────────────────────────────────────────────────┐ │  │
│  │  │ id | emp_code | punch_time | punch_state | ...     │ │  │
│  │  │ 1  | EMP001   | 2026-03-14   | 0           | ...   │ │  │
│  │  │ 2  | EMP002   | 2026-03-14   | 1           | ...   │ │  │
│  │  │ ...                                                 │ │  │
│  │  └────────────────────────────────────────────────────┘ │  │
│  │                                                          │  │
│  │  Unique Constraint: (emp_code, punch_time, terminal_sn) │  │
│  │  Indexes: emp_code, punch_time, emp_time                │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Read attendance data
                         │ (PHP PDO MySQL)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PHP WEB APPLICATION                            │
│              Purpose: Salary Calculation                        │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Modules:                                                │  │
│  │  - Employee attendance summary                           │  │
│  │  - Late arrivals / Early departures                      │  │
│  │  - Overtime calculation                                  │  │
│  │  - Work duration calculation                             │  │
│  │  - Salary generation                                     │  │
│  │  - Reports (Excel, PDF)                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Data Synchronization Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: Check Schedule                                         │
│  ─────────────────────────────────────────────────────────────  │
│  Current time: 09:00                                            │
│  Scheduled times: ["09:00", "12:00", "17:00", "22:00"]         │
│  Match found! → Start sync                                      │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: Read Last Sync Position                                │
│  ─────────────────────────────────────────────────────────────  │
│  File: last_sync_zk.txt                                         │
│  Content: 15234  (last synced PostgreSQL record ID)             │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: Query PostgreSQL for New Records                       │
│  ─────────────────────────────────────────────────────────────  │
│  SQL: SELECT * FROM iclock_transaction                          │
│       WHERE id > 15234                                          │
│       ORDER BY id ASC                                           │
│                                                                 │
│  Result: 250 new records found                                  │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: Process in Batches                                     │
│  ─────────────────────────────────────────────────────────────  │
│  Batch size: 100 (from config.json)                             │
│                                                                 │
│  Batch 1: Records 1-100    → Upload → Update last_sync_id       │
│  Batch 2: Records 101-200  → Upload → Update last_sync_id       │
│  Batch 3: Records 201-250  → Upload → Update last_sync_id       │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 5: Upload to Cloud MySQL                                  │
│  ─────────────────────────────────────────────────────────────  │
│  SQL: INSERT INTO zk_attendance_logs                            │
│       (emp_code, punch_time, punch_state, ...)                  │
│       VALUES (%s, %s, %s, ...)                                  │
│       ON DUPLICATE KEY UPDATE                                   │
│         punch_state = VALUES(punch_state),                      │
│         server_time = NOW()                                     │
│                                                                 │
│  Result: 250 records uploaded successfully                      │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 6: Update Sync Position                                   │
│  ─────────────────────────────────────────────────────────────  │
│  File: last_sync_zk.txt                                         │
│  New content: 15484 (ID of last uploaded record)                │
│                                                                 │
│  Next sync will start from: WHERE id > 15484                    │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 7: Wait for Next Schedule                                 │
│  ─────────────────────────────────────────────────────────────  │
│  Next scheduled time: 12:00                                     │
│  Current time: 09:02                                            │
│  Sleep until 12:00 (check every 30 seconds)                     │
└─────────────────────────────────────────────────────────────────┘
```

## Component Interaction

```
┌─────────────────────────────────────────────────────────────────┐
│  ZK_TRAY_APP.py (UI Layer)                                      │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐ │
│  │ System Tray     │  │ Config Dialog   │  │ Log Viewer     │ │
│  │ Icon            │  │                 │  │                │ │
│  │ - Start/Stop    │  │ - PostgreSQL    │  │ - Real-time    │ │
│  │ - Sync Now      │  │ - Schedule      │  │   logs         │ │
│  │ - Status        │  │ - Save/Cancel   │  │ - Scrollable   │ │
│  └─────────────────┘  └─────────────────┘  └────────────────┘ │
│                                                                 │
│  Communicates with: SyncWorker (QThread)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Qt Signals/Slots
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  SyncWorker (Background Thread)                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Main Loop (runs continuously)                           │  │
│  │                                                          │  │
│  │  while running:                                          │  │
│  │    if not paused:                                        │  │
│  │      if current_time in schedule:                        │  │
│  │        sync_from_zk_to_cloud()                           │  │
│  │    sleep(30 seconds)                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Emits signals: status_signal, log_signal                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Function calls
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Sync Functions (Business Logic)                                │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  1. connect_to_postgresql()                                     │
│  2. get_new_records_from_postgresql(last_sync_id)              │
│  3. connect_to_mysql()                                          │
│  4. sync_records_to_mysql(records)                             │
│  5. set_last_sync_id(max_id)                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Database Schema Comparison

### Source: PostgreSQL (ZKBioTime)

```sql
TABLE: iclock_transaction
┌─────────────────┬──────────────────┬─────────────┬──────────┐
│ Column          │ Type             │ Nullable    │ Example  │
├─────────────────┼──────────────────┼─────────────┼──────────┤
│ id              │ SERIAL           │ NO          │ 15234    │
│ emp_code        │ VARCHAR(20)      │ NO          │ 'EMP001' │
│ punch_time      │ TIMESTAMPTZ      │ NO          │ 2026-03-14│
│ punch_state     │ VARCHAR(5)       │ NO          │ '0'      │
│ verify_type     │ INT              │ NO          │ 2        │
│ terminal_sn     │ VARCHAR(50)      │ YES         │ 'ZK12345'│
│ terminal_alias  │ VARCHAR(50)      │ YES         │ 'Office' │
│ emp_id          │ INT              │ YES         │ 42       │
│ terminal_id     │ INT              │ YES         │ 1        │
│ ... (more fields)                  │             │          │
└─────────────────┴──────────────────┴─────────────┴──────────┘

Primary Key: id
Unique: (company_code, emp_code, punch_time)
Foreign Keys: emp_id → personnel_employee, terminal_id → iclock_terminal
```

### Destination: MySQL (Cloud)

```sql
TABLE: zk_attendance_logs
┌─────────────────┬──────────────────┬─────────────┬──────────┐
│ Column          │ Type             │ Nullable    │ Example  │
├─────────────────┼──────────────────┼─────────────┼──────────┤
│ id              │ INT AUTO_INCREMENT│ NO         │ 1001     │
│ emp_code        │ VARCHAR(20)      │ NO          │ 'EMP001' │
│ punch_time      │ DATETIME         │ NO          │ 2026-03-14│
│ punch_state     │ VARCHAR(5)       │ NO          │ '0'      │
│ verify_type     │ INT              │ NO          │ 2        │
│ terminal_sn     │ VARCHAR(50)      │ YES         │ 'ZK12345'│
│ terminal_alias  │ VARCHAR(50)      │ YES         │ 'Office' │
│ emp_id          │ INT              │ YES         │ 42       │
│ terminal_id     │ INT              │ YES         │ 1        │
│ server_time     │ DATETIME         │ NO (NOW())  │ 2026-03-14│
│ source_device   │ VARCHAR(50)      │ NO          │ 'zkbiotime'│
└─────────────────┴──────────────────┴─────────────┴──────────┘

Primary Key: id
Unique: (emp_code, punch_time, terminal_sn)
Indexes: emp_code, punch_time, emp_time, terminal_sn
```

### Field Mapping

| PostgreSQL | MySQL | Transformation |
|------------|-------|----------------|
| id | (not synced) | Used for sync tracking only |
| emp_code | emp_code | Direct copy |
| punch_time | punch_time | Direct copy (timezone handled by DB) |
| punch_state | punch_state | Direct copy |
| verify_type | verify_type | Direct copy |
| terminal_sn | terminal_sn | Direct copy |
| terminal_alias | terminal_alias | Direct copy |
| emp_id | emp_id | Direct copy |
| terminal_id | terminal_id | Direct copy |
| (none) | server_time | Auto-generated (NOW()) |
| (none) | source_device | Fixed value ('zkbiotime') |

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Credential Storage                                             │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  config.json (Plain text, safe to share)                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ {                                                        │  │
│  │   "POSTGRESQL_CONFIG": {                                 │  │
│  │     "host": "127.0.0.1",                                 │  │
│  │     "password": ""  ← Empty or plain text (local only)   │  │
│  │   }                                                      │  │
│  │ }                                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  encrypted_credentials.bin (Binary, NEVER share)               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Fernet Encrypted:                                        │  │
│  │ {                                                        │  │
│  │   "DB_CONFIG": {                                         │  │
│  │     "host": "cloud.example.com",                         │  │
│  │     "password": "secret123"  ← ENCRYPTED                 │  │
│  │   }                                                      │  │
│  │ }                                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Encryption: Fernet (symmetric, AES-128-CBC)                   │
│  Key: Embedded in source code                                  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Error Handling Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│  Error Type              │  Handling Strategy                    │
│  ─────────────────────────────────────────────────────────────  │
│  PostgreSQL connection   │  Log error, retry next schedule       │
│  failed                  │  Show error in tray logs              │
│  ─────────────────────────────────────────────────────────────  │
│  MySQL connection        │  Log error, retry next schedule       │
│  failed                  │  Do NOT update last_sync_id           │
│  ─────────────────────────────────────────────────────────────  │
│  Query failed            │  Rollback transaction                 │
│  (syntax error, etc)     │  Log detailed error                   │
│  ─────────────────────────────────────────────────────────────  │
│  Network timeout         │  Retry current batch (max 3 times)    │
│  during upload           │  If still fails, stop and log         │
│  ─────────────────────────────────────────────────────────────  │
│  Duplicate key           │  ON DUPLICATE KEY UPDATE              │
│  (record exists)         │  Update existing record               │
│  ─────────────────────────────────────────────────────────────  │
│  Power failure           │  last_sync_id preserved in file       │
│  during sync             │  Resume from last successful batch    │
│  ─────────────────────────────────────────────────────────────  │
│  Multiple instances      │  File locking prevents conflicts      │
│  running                 │  Second instance exits gracefully     │
└─────────────────────────────────────────────────────────────────┘
```

## Performance Optimization

### Batch Processing

```
Small batches (50-100):
✅ Less memory usage
✅ More frequent sync position updates
✅ Better for slow networks
❌ More round-trips to database

Large batches (500-1000):
✅ Fewer round-trips
✅ Faster overall sync
❌ More memory usage
❌ Larger rollback on failure

Recommended: 100 (balanced)
```

### Index Usage

```sql
-- PostgreSQL side (already indexed by ZKBioTime)
CREATE INDEX iclock_transaction_emp_id_60fa3521 
ON iclock_transaction(emp_id);

CREATE INDEX iclock_transaction_terminal_id_451c81c2 
ON iclock_transaction(terminal_id);

-- MySQL side (created by zk_cloud_setup.sql)
CREATE INDEX idx_emp_code ON zk_attendance_logs(emp_code);
CREATE INDEX idx_punch_time ON zk_attendance_logs(punch_time);
CREATE INDEX idx_emp_time ON zk_attendance_logs(emp_code, punch_time);
```

---

This architecture ensures:
- ✅ **Reliability**: Incremental sync with checkpoint recovery
- ✅ **Data Integrity**: Unique constraints prevent duplicates
- ✅ **Performance**: Batch processing and indexes
- ✅ **Security**: Encrypted credentials
- ✅ **Maintainability**: Clear separation of concerns
