# Python Installation Guide for ZK Upload

## Problem

Your ZKBioTime Python installation is corrupted and cannot create virtual environments.

## Solution: Install Python Separately

### Step 1: Download Python

1. Go to https://www.python.org/downloads/
2. Download **Python 3.11.x** or **Python 3.12.x** (latest stable)
3. **IMPORTANT:** During installation, check:
   - ✅ "Add Python to PATH"
   - ✅ "Install for all users" (optional but recommended)

### Step 2: Verify Installation

Open **NEW** Command Prompt (close and reopen):

```bash
python --version
```

Expected: `Python 3.11.x` or `Python 3.12.x`

```bash
pip --version
```

Expected: pip version with Python 3.11 or 3.12 path

### Step 3: Create Virtual Environment

```bash
cd D:\zkupload\zkupload_biotime

# Remove corrupted venv
rmdir /s /q venv

# Create new venv
python -m venv venv

# Activate
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Test Connection

```bash
python test_postgresql.py
```

Expected: Should show PostgreSQL connection details

## Alternative: Use Existing Python from Another Location

If you have Python installed elsewhere (e.g., from another project):

```bash
# Find Python installations
where python

# Use specific Python version
C:\Python311\python.exe -m venv venv
```

## Workaround: Use ZKBioTime Python Directly (Not Recommended)

If you cannot install Python separately, you can try to fix the ZKBioTime Python:

```bash
# Navigate to ZKBioTime Python
cd d:\ZKBioTime\Python311

# Remove problematic file
del Lib\site-packages\zope.event-4.6-py3.9-nspkg.pth

# Try again
cd D:\zkupload\zkupload_biotime
python -m venv venv
```

**Warning:** This may break ZKBioTime functionality. Use at your own risk.

## After Python is Fixed

1. Run: `setup_venv.bat`
2. Edit `config.json` with PostgreSQL password
3. Run: `encrypt_credentials.bat`
4. Run: `test_postgres.bat`
5. Test sync: `python -c "from src.zk_sync_to_cloud import sync_all_tables; sync_all_tables()"`

## Contact

If issues persist, please:
1. Check if ZKBioTime is running properly
2. Contact ZKTeco support for Python issues
3. Consider running this application on a different machine
