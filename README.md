# ZK Upload - ZKBioTime Cloud Sync

Attendance data synchronization from ZKBioTime (PostgreSQL) to Cloud MySQL database for salary calculation integration.

## 📊 Project Structure

```
zkupload/
├── zkupload_biotime/          # Main application (4-table sync)
│   ├── src/                   # Source code
│   ├── docs/                  # Database schema
│   ├── README.md              # Complete documentation
│   └── QUICKSTART.md          # Quick start guide
│
└── source/                    # Reference documentation
    ├── 1-instllation.md       # ZKBioTime installation
    ├── 2-local-posgre_dll.sql # PostgreSQL schema
    └── 3-DataMapping.md       # Field mapping
```

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/bounthongv/zkupload.git
cd zkupload/zkupload_biotime
```

### 2. Install Dependencies
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Setup Cloud Database
```bash
# Run on your cloud MySQL server
mysql -h cloud-host -u user -p database < docs/zk_cloud_setup.sql
```

### 4. Configure and Run
```bash
# Edit config.json with your PostgreSQL credentials
# Encrypt cloud MySQL credentials
encrypt_credentials.bat

# Test connection
test_postgres.bat

# Run application
run_zk_tray.bat
```

## 📚 Documentation

- **[zkupload_biotime/README.md](zkupload_biotime/README.md)** - Complete documentation
- **[zkupload_biotime/QUICKSTART.md](zkupload_biotime/QUICKSTART.md)** - 30-minute setup guide
- **[zkupload_biotime/ARCHITECTURE.md](zkupload_biotime/ARCHITECTURE.md)** - System architecture
- **[source/3-DataMapping.md](source/3-DataMapping.md)** - Field mapping details

## 🎯 Features

- ✅ **4-Table Sync**: departments, employees, devices, attendance_logs
- ✅ **Incremental Sync**: Only uploads new/changed records
- ✅ **Scheduled Sync**: Different schedules per table type
- ✅ **System Tray UI**: User-friendly interface
- ✅ **Secure Credentials**: Encrypted storage
- ✅ **Duplicate Prevention**: Unique constraints

## 📋 Tables Synced

| PostgreSQL Table | Cloud MySQL Table | Sync Strategy | Frequency |
|-----------------|-------------------|---------------|-----------|
| personnel_department | departments | Full sync | Daily |
| personnel_employee | employees | Incremental | Every 6 hours |
| iclock_terminal | devices | Incremental | Daily |
| iclock_transaction | attendance_logs | Incremental | Every 4 hours |

## 🔧 Requirements

- Python 3.8+
- ZKBioTime 9.x (local PostgreSQL)
- MySQL 5.7+/8.0+ (cloud)
- Windows 10/11

## 🛠️ Development

### Build Executables
```bash
# Build tray application
compile_tray.bat

# Build console service
compile_service.bat
```

### Run Tests
```bash
# Test PostgreSQL connection
test_postgres.bat
```

## 📞 Support

For issues or questions:
1. Check [zkupload_biotime/README.md](zkupload_biotime/README.md) troubleshooting section
2. Review logs in application
3. Check sync status: `SELECT * FROM sync_tracking;`

## 📄 License

Proprietary - For internal use only

## 👨‍💻 Author

Bounthong V.

## 📅 Version

Version: 2.0 (4-Table Sync)
Last Updated: 2026-03-14
