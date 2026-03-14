@echo off
REM Compile ZK Tray Application to Standalone Executable
REM Requires: pip install pyinstaller

echo === Compiling ZK Tray Application ===
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Install dependencies if needed
echo Checking dependencies...
pip install -r requirements.txt

echo.
echo Building executable...
pyinstaller --clean zk_tray_app.spec

echo.
if exist dist\zkupload_tray.exe (
    echo SUCCESS: Executable created at dist\zkupload_tray.exe
) else (
    echo ERROR: Compilation failed
)

echo.
pause
