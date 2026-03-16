
import os
import sys

print("--- Diagnostics Started ---")
print(f"Python Version: {sys.version}")
print(f"Current Directory: {os.getcwd()}")

try:
    import PyQt5
    from PyQt5.QtWidgets import QApplication
    print(f"PyQt5 Version: {PyQt5.QtCore.PYQT_VERSION_STR}")
    
    app = QApplication(sys.argv)
    print("PyQt5 Application initialized successfully.")
    
    from PyQt5.QtWidgets import QSystemTrayIcon
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("WARNING: System Tray is NOT available on this system!")
    else:
        print("System Tray is available.")
        
except ImportError as e:
    print(f"CRITICAL: PyQt5 is NOT installed correctly: {e}")
except Exception as e:
    print(f"ERROR during PyQt5 initialization: {e}")

try:
    import psycopg2
    print("psycopg2 imported successfully.")
except ImportError:
    print("psycopg2 is NOT installed.")

try:
    import pymysql
    print("pymysql imported successfully.")
except ImportError:
    print("pymysql is NOT installed.")

try:
    from cryptography.fernet import Fernet
    print("cryptography imported successfully.")
except ImportError:
    print("cryptography is NOT installed.")

print("--- Diagnostics Finished ---")
