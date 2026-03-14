@echo off
REM Encrypt MySQL Cloud Database Credentials
REM This creates an encrypted_credentials.bin file

echo === ZK BioTime Credential Encryption ===
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

python src\encrypt_zk_credentials.py

echo.
pause
