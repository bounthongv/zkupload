@echo off
REM Run ZK Sync Service (Console Mode)
REM This runs the sync service in console mode for testing/debugging

echo === ZK BioTime Cloud Sync Service ===
echo Starting in console mode...
echo.

python src\zk_sync_to_cloud.py

pause
