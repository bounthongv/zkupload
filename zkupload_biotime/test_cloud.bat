@echo off
REM Test Cloud MySQL Connection
REM Verifies connection to cloud MySQL database

echo === ZK BioTime Cloud MySQL Connection Test ===
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

python test_cloud_connection.py

echo.
pause
