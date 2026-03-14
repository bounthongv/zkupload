@echo off
REM Test PostgreSQL Connection
REM Verifies connection to ZKBioTime PostgreSQL database

echo === ZK BioTime PostgreSQL Connection Test ===
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Install psycopg2 if not installed
pip install psycopg2-binary -q

python test_postgresql.py

echo.
pause
