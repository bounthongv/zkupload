@echo off
REM Create virtual environment in a clean location
cd /d %~dp0

REM Remove old venv if exists
if exist venv rmdir /s /q venv

REM Create new venv using py launcher
py -3 -m venv venv

REM Activate and install dependencies
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ================================================
echo Virtual environment created successfully!
echo ================================================
echo.
echo Next steps:
echo 1. Edit config.json with your PostgreSQL password
echo 2. Run: encrypt_credentials.bat
echo 3. Run: test_postgres.bat
echo.
pause
