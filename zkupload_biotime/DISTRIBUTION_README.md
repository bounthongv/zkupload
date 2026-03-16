# ZK BioTime Cloud Sync - Setup Guide

This application synchronizes attendance data from your local ZKBioTime (PostgreSQL) server to a cloud MySQL database.

## 📁 Package Contents
*   `zk_tray_app.exe`: The main application.
*   `config.json`: Configuration for local database and sync schedules.
*   `.env`: Configuration for cloud database credentials.

---

## 🚀 Quick Setup

### Step 1: Configure Cloud Credentials
Open the `.env` file with Notepad and fill in your cloud database details:
```ini
MYSQL_HOST=your-cloud-ip-or-host
MYSQL_PORT=3306
MYSQL_DATABASE=your-database-name
MYSQL_USER=your-username
MYSQL_PASSWORD=your-password
```

### Step 2: Configure Local Database (Optional)
If your local ZKBioTime PostgreSQL uses a different port or has a password, add it to the `.env` file:
```ini
PG_HOST=127.0.0.1
PG_PORT=7496
PG_DATABASE=biotime
PG_USER=postgres
PG_PASSWORD=your-postgres-password
```

### Step 3: Run the Application
Double-click `zk_tray_app.exe`. 
*   Look for a **blue square icon** in your System Tray (near the clock).
*   Right-click the icon for the menu.
*   Select **"View Logs"** to monitor the progress.
*   Select **"Sync All Tables Now"** to start the first upload.

---

## ⚙️ How it Works
*   **Automatic Sync:** The application watches the clock and syncs based on the schedules in `config.json`.
*   **No Duplicates:** The system tracks the last record ID uploaded. It only syncs new data since the last run.
*   **Background Operation:** Once started, the app runs in the background. Keep the tray icon active to ensure continuous syncing.

---
**Developed by Apis Co. Ltd.**  
March 2026
