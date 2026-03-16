"""
ZK BioTime Cloud Sync - System Tray Application (4-Table Sync)
Provides a user-friendly interface with system tray controls for syncing 4 tables:
1. departments (from personnel_department)
2. employees (from personnel_employee)
3. devices (from iclock_terminal)
4. attendance_logs (from iclock_transaction)
"""
import os
import sys
import json
import threading
import time
from datetime import datetime
import psycopg2
import pymysql
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from PyQt5.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QAction, QMessageBox, 
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QTextEdit, QGroupBox, QFormLayout, QTabWidget, QWidget, QProgressBar,
    QGridLayout, QFrame
)
from PyQt5.QtGui import QIcon, QPixmap, QFont, QColor
from PyQt5.QtCore import QTimer, QThread, pyqtSignal

# Configuration files
CONFIG_FILE = "config.json"
ENCRYPTED_CREDENTIALS_FILE = "encrypted_credentials.bin"
SYNC_POSITIONS_FILE = "sync_positions.json"

# Fixed encryption key - must match other components
ENCRYPTION_KEY = b'ZK8pQeHY8pQeHY8RMyeYf6e5Twq9PdOBVo9JPsqHZA4='


def load_config():
    """Load public configuration from JSON file"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        default_config = {
            "POSTGRESQL_CONFIG": {
                "host": "127.0.0.1",
                "port": 7496,
                "database": "biotime",
                "user": "postgres",
                "password": ""
            },
            "SYNC_SCHEDULES": {
                "departments": "01:00",
                "employees": ["01:00", "07:00", "13:00", "19:00"],
                "devices": "02:00",
                "attendance_logs": ["09:00", "12:00", "17:00", "22:00"]
            },
            "BATCH_SIZE": 100
        }
        save_config(default_config)
        return default_config
    except Exception as e:
        print(f"Error loading config: {e}")
        return {
            "POSTGRESQL_CONFIG": {
                "host": "127.0.0.1",
                "port": 7496,
                "database": "biotime",
                "user": "postgres",
                "password": ""
            },
            "SYNC_SCHEDULES": {
                "departments": "01:00",
                "employees": ["01:00", "07:00", "13:00", "19:00"],
                "devices": "02:00",
                "attendance_logs": ["09:00", "12:00", "17:00", "22:00"]
            },
            "BATCH_SIZE": 100
        }


def load_encrypted_credentials():
    """Load and decrypt MySQL cloud credentials"""
    try:
        with open(ENCRYPTED_CREDENTIALS_FILE, 'rb') as f:
            encrypted_data = f.read()
        
        fernet = Fernet(ENCRYPTION_KEY)
        decrypted_data = fernet.decrypt(encrypted_data)
        credentials = json.loads(decrypted_data.decode())
        return credentials.get("DB_CONFIG", {})
    except FileNotFoundError:
        print(f"Encrypted credentials file not found: {ENCRYPTED_CREDENTIALS_FILE}")
        return {}
    except Exception as e:
        print(f"Error decrypting credentials: {e}")
        return {}


def save_config(config):
    """Save public configuration to JSON file"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False


def load_sync_positions():
    """Load sync positions from JSON file"""
    try:
        with open(SYNC_POSITIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "departments": {"last_sync": None, "records_synced": 0, "sync_status": "pending"},
            "employees": {"last_sync_time": None, "records_synced": 0, "sync_status": "pending"},
            "devices": {"last_sync_id": 0, "records_synced": 0, "sync_status": "pending"},
            "attendance_logs": {"last_sync_id": 0, "records_synced": 0, "sync_status": "pending"}
        }
    except Exception as e:
        print(f"Error loading sync positions: {e}")
        return None


def save_sync_positions(positions):
    """Save sync positions to JSON file"""
    try:
        with open(SYNC_POSITIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(positions, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving sync positions: {e}")
        return False


def log_msg(message):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    sys.stdout.flush()


class SyncWorker(QThread):
    """Worker thread for sync operations"""
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    table_status_signal = pyqtSignal(str, dict)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.paused = False
        self.manual_sync_requested = False
        self.manual_sync_table = None
        self.credentials = load_encrypted_credentials()
    
    def run(self):
        self.running = True
        last_run_minute = None
        last_sync_completed_at = None
        
        while self.running:
            # Check for manual sync request first
            if self.manual_sync_requested:
                if self.manual_sync_table:
                    self.perform_single_table_sync(self.manual_sync_table)
                else:
                    self.sync_all_tables()
                self.manual_sync_requested = False
                self.manual_sync_table = None
                last_sync_completed_at = datetime.now()
            
            if not self.paused:
                current_config = load_config()
                schedules = current_config.get("SYNC_SCHEDULES", {})
                
                now = datetime.now()
                current_time = now.strftime("%H:%M")
                
                # Check if any table should be synced
                should_sync = False
                for table_name, schedule in schedules.items():
                    if isinstance(schedule, str):
                        if current_time == schedule:
                            should_sync = True
                            break
                    elif isinstance(schedule, list):
                        if current_time in schedule:
                            should_sync = True
                            break
                
                if should_sync:
                    if current_time != last_run_minute:
                        self.status_signal.emit(f"Syncing at {current_time}...")
                        self.sync_all_tables()
                        last_run_minute = current_time
                        last_sync_completed_at = datetime.now()
                        
                        # Show waiting message after sync
                        next_t = self.get_next_schedule(schedules)
                        self.log_signal.emit(f"Sync completed at {last_sync_completed_at.strftime('%H:%M:%S')}. Waiting for next schedule at {next_t}...")
                        
                        # Sleep for 61 seconds to avoid re-triggering in the same minute
                        time.sleep(61)
                else:
                    # Only show waiting message once every 10 minutes to avoid log spam
                    if not last_sync_completed_at or (now.minute % 10 == 0 and now.second < 30):
                        next_t = self.get_next_schedule(schedules)
                        self.log_signal.emit(f"Sync idle. Waiting for next schedule at {next_t}... (Current time: {current_time})")
            
            if not self.paused:
                time.sleep(30)
            else:
                time.sleep(1)
    
    def get_next_schedule(self, schedules):
        """Calculate the next scheduled sync time"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        all_times = []
        for table, schedule in schedules.items():
            if isinstance(schedule, str):
                all_times.append(schedule)
            elif isinstance(schedule, list):
                all_times.extend(schedule)
        
        all_times = sorted(list(set(all_times)))
        
        if not all_times:
            return "None"
            
        for t in all_times:
            if t > current_time:
                return t
                
        return all_times[0]  # First schedule of tomorrow
    
    def stop(self):
        self.running = False
    
    def pause(self):
        self.paused = True
    
    def resume(self):
        self.paused = False
    
    def request_manual_sync(self, table_name=None):
        """Request a manual sync from another thread"""
        self.manual_sync_requested = True
        self.manual_sync_table = table_name
        self.log_signal.emit(f"Manual sync request received for {table_name if table_name else 'all tables'}")
    
    def perform_single_table_sync(self, table_name):
        """Perform sync for a single table in the background thread"""
        if table_name == 'departments':
            self.sync_departments()
        elif table_name == 'employees':
            self.sync_employees()
        elif table_name == 'devices':
            self.sync_devices()
        elif table_name == 'attendance_logs':
            self.sync_attendance_logs()
    
    def connect_to_postgresql(self):
        """Connect to ZKBioTime PostgreSQL database (using .env or config.json)"""
        try:
            # Try loading from environment variables first (.env)
            env_host = os.getenv("PG_HOST")
            env_port = os.getenv("PG_PORT")
            env_db = os.getenv("PG_DATABASE")
            env_user = os.getenv("PG_USER")
            env_pass = os.getenv("PG_PASSWORD")

            if all([env_host, env_db, env_user]):
                # print(f"Connecting to PostgreSQL using .env configuration ({env_host})...")
                return psycopg2.connect(
                    host=env_host,
                    port=int(env_port) if env_port else 7496,
                    database=env_db,
                    user=env_user,
                    password=env_pass if env_pass else "",
                    connect_timeout=60
                )

            # Fallback to config.json
            config = load_config()
            pg_config = config.get("POSTGRESQL_CONFIG", {})
            
            conn = psycopg2.connect(
                host=pg_config.get('host', '127.0.0.1'),
                port=pg_config.get('port', 7496),
                database=pg_config.get('database', 'biotime'),
                user=pg_config.get('user', 'postgres'),
                password=pg_config.get('password', ''),
                connect_timeout=60
            )
            return conn
        except Exception as e:
            self.log_signal.emit(f"Error connecting to PostgreSQL: {e}")
            return None
    
    def connect_to_mysql(self):
        """Connect to cloud MySQL database (using .env or encrypted bin)"""
        try:
            # Try loading from environment variables first (.env)
            env_host = os.getenv("MYSQL_HOST")
            env_user = os.getenv("MYSQL_USER")
            env_password = os.getenv("MYSQL_PASSWORD")
            env_database = os.getenv("MYSQL_DATABASE")
            env_port = os.getenv("MYSQL_PORT", "3306")

            if all([env_host, env_user, env_database]):
                # print(f"Connecting to MySQL using .env configuration ({env_host})...")
                return pymysql.connect(
                    host=env_host,
                    user=env_user,
                    password=env_password,
                    database=env_database,
                    port=int(env_port),
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor,
                    connect_timeout=60
                )

            # Fallback to encrypted credentials file
            current_credentials = load_encrypted_credentials()
            if not current_credentials:
                self.log_signal.emit("Error: No cloud credentials found in .env or encrypted bin.")
                return None
            
            conn = pymysql.connect(
                host=current_credentials.get('host', 'localhost'),
                user=current_credentials.get('user', ''),
                password=current_credentials.get('password', ''),
                database=current_credentials.get('database', ''),
                port=current_credentials.get('port', 3306),
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=60
            )
            return conn
        except Exception as e:
            self.log_signal.emit(f"Error connecting to MySQL: {e}")
            return None
    
    def check_mysql_table_exists(self, table_name):
        """Check if table exists in MySQL"""
        mysql_conn = self.connect_to_mysql()
        if not mysql_conn:
            return False
        
        try:
            cursor = mysql_conn.cursor()
            cursor.execute(f"SELECT 1 FROM {table_name} LIMIT 1")
            cursor.fetchone()
            mysql_conn.close()
            return True
        except:
            mysql_conn.close()
            return False
    
    # ================================================================
    # SYNC FUNCTIONS (4 Tables)
    # ================================================================
    
    def sync_departments(self):
        """Sync departments (Full Sync)"""
        self.log_signal.emit("=== Syncing Departments (Full Sync) ===")
        
        if not self.check_mysql_table_exists('departments'):
            self.log_signal.emit("ERROR: departments table does not exist!")
            return 0
        
        pg_conn = self.connect_to_postgresql()
        if not pg_conn:
            return 0
        
        try:
            cursor = pg_conn.cursor()
            cursor.execute("""
                SELECT id, dept_code, dept_name, parent_dept_id
                FROM personnel_department
                ORDER BY id
            """)
            pg_records = cursor.fetchall()
            pg_conn.close()
            
            if not pg_records:
                self.log_signal.emit("No departments found")
                return 0
            
            mysql_conn = self.connect_to_mysql()
            if not mysql_conn:
                return 0
            
            try:
                cursor = mysql_conn.cursor()
                replace_query = """
                    REPLACE INTO departments 
                    (id, dept_code, dept_name, parent_dept_id, last_sync)
                    VALUES (%s, %s, %s, %s, NOW())
                """
                
                count = 0
                for record in pg_records:
                    values = (record[0], record[1], record[2], record[3])
                    cursor.execute(replace_query, values)
                    count += 1
                
                mysql_conn.commit()
                self.log_signal.emit(f"Uploaded {count} departments")
                
                # Update sync positions
                positions = load_sync_positions()
                positions['departments'] = {
                    "last_sync": datetime.now().isoformat(),
                    "method": "full",
                    "records_synced": count,
                    "sync_status": "completed"
                }
                save_sync_positions(positions)
                
                self.table_status_signal.emit('departments', positions['departments'])
                
                return count
            except Exception as e:
                self.log_signal.emit(f"Error syncing departments: {e}")
                mysql_conn.rollback()
                return 0
            finally:
                try:
                    if mysql_conn and mysql_conn.open:
                        mysql_conn.close()
                except:
                    pass
        except Exception as e:
            self.log_signal.emit(f"Error in departments sync: {e}")
            return 0
    
    def sync_employees(self):
        """Sync employees (Incremental)"""
        self.log_signal.emit("=== Syncing Employees (Incremental) ===")
        
        if not self.check_mysql_table_exists('employees'):
            self.log_signal.emit("ERROR: employees table does not exist!")
            return 0
        
        positions = load_sync_positions()
        last_sync_time = positions.get('employees', {}).get('last_sync_time')
        
        pg_conn = self.connect_to_postgresql()
        if not pg_conn:
            return 0
        
        try:
            cursor = pg_conn.cursor()
            
            if last_sync_time:
                cursor.execute("""
                    SELECT id, emp_code, first_name, last_name, nickname,
                           department_id, emp_type, hire_date, is_active,
                           mobile, email
                    FROM personnel_employee
                    WHERE update_time > %s OR change_time > %s
                    ORDER BY id
                """, (last_sync_time, last_sync_time))
            else:
                cursor.execute("""
                    SELECT id, emp_code, first_name, last_name, nickname,
                           department_id, emp_type, hire_date, is_active,
                           mobile, email
                    FROM personnel_employee
                    WHERE is_active = TRUE
                    ORDER BY id
                """)
            
            pg_records = cursor.fetchall()
            pg_conn.close()
            
            if not pg_records:
                self.log_signal.emit("No new employees found")
                return 0
            
            mysql_conn = self.connect_to_mysql()
            if not mysql_conn:
                return 0
            
            try:
                cursor = mysql_conn.cursor()
                upsert_query = """
                    INSERT INTO employees 
                    (id, emp_code, first_name, last_name, display_name,
                     department_id, emp_type, hire_date, is_active, mobile, email, last_sync)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON DUPLICATE KEY UPDATE
                        first_name = VALUES(first_name),
                        last_name = VALUES(last_name),
                        display_name = VALUES(display_name),
                        department_id = VALUES(department_id),
                        emp_type = VALUES(emp_type),
                        hire_date = VALUES(hire_date),
                        is_active = VALUES(is_active),
                        mobile = VALUES(mobile),
                        email = VALUES(email),
                        last_sync = NOW()
                """
                
                count = 0
                max_id = 0
                for record in pg_records:
                    values = (
                        record[0], record[1], record[2], record[3], record[4],
                        record[5], record[6], record[7], record[8], record[9], record[10]
                    )
                    cursor.execute(upsert_query, values)
                    count += 1
                    max_id = max(max_id, record[0])
                
                mysql_conn.commit()
                self.log_signal.emit(f"Uploaded {count} employees")
                
                positions['employees'] = {
                    "last_sync_id": max_id,
                    "last_sync_time": datetime.now().isoformat(),
                    "method": "incremental",
                    "records_synced": count,
                    "sync_status": "completed"
                }
                save_sync_positions(positions)
                
                self.table_status_signal.emit('employees', positions['employees'])
                
                return count
            except Exception as e:
                self.log_signal.emit(f"Error syncing employees: {e}")
                mysql_conn.rollback()
                return 0
            finally:
                try:
                    if mysql_conn and mysql_conn.open:
                        mysql_conn.close()
                except:
                    pass
        except Exception as e:
            self.log_signal.emit(f"Error in employees sync: {e}")
            return 0
    
    def sync_devices(self):
        """Sync devices (Incremental)"""
        self.log_signal.emit("=== Syncing Devices (Incremental) ===")
        
        if not self.check_mysql_table_exists('devices'):
            self.log_signal.emit("ERROR: devices table does not exist!")
            return 0
        
        positions = load_sync_positions()
        last_sync_id = positions.get('devices', {}).get('last_sync_id', 0)
        
        pg_conn = self.connect_to_postgresql()
        if not pg_conn:
            return 0
        
        try:
            cursor = pg_conn.cursor()
            
            if last_sync_id > 0:
                cursor.execute("""
                    SELECT id, sn, alias, ip_address, state, is_attendance, last_activity
                    FROM iclock_terminal
                    WHERE id > %s
                    ORDER BY id
                """, (last_sync_id,))
            else:
                cursor.execute("""
                    SELECT id, sn, alias, ip_address, state, is_attendance, last_activity
                    FROM iclock_terminal
                    ORDER BY id
                """)
            
            pg_records = cursor.fetchall()
            pg_conn.close()
            
            if not pg_records:
                self.log_signal.emit("No new devices found")
                return 0
            
            mysql_conn = self.connect_to_mysql()
            if not mysql_conn:
                return 0
            
            try:
                cursor = mysql_conn.cursor()
                upsert_query = """
                    INSERT INTO devices 
                    (id, terminal_sn, terminal_alias, ip_address, state, is_attendance, last_activity, last_sync)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON DUPLICATE KEY UPDATE
                        terminal_alias = VALUES(terminal_alias),
                        ip_address = VALUES(ip_address),
                        state = VALUES(state),
                        is_attendance = VALUES(is_attendance),
                        last_activity = VALUES(last_activity),
                        last_sync = NOW()
                """
                
                count = 0
                max_id = 0
                for record in pg_records:
                    values = (
                        record[0], record[1], record[2], record[3],
                        record[4], record[5], record[6]
                    )
                    cursor.execute(upsert_query, values)
                    count += 1
                    max_id = max(max_id, record[0])
                
                mysql_conn.commit()
                self.log_signal.emit(f"Uploaded {count} devices")
                
                positions['devices'] = {
                    "last_sync_id": max_id,
                    "last_sync_time": datetime.now().isoformat(),
                    "method": "incremental",
                    "records_synced": count,
                    "sync_status": "completed"
                }
                save_sync_positions(positions)
                
                self.table_status_signal.emit('devices', positions['devices'])
                
                return count
            except Exception as e:
                self.log_signal.emit(f"Error syncing devices: {e}")
                mysql_conn.rollback()
                return 0
            finally:
                try:
                    if mysql_conn and mysql_conn.open:
                        mysql_conn.close()
                except:
                    pass
        except Exception as e:
            self.log_signal.emit(f"Error in devices sync: {e}")
            return 0
    
    def sync_attendance_logs(self):
        """Sync attendance_logs (Incremental)"""
        self.log_signal.emit("=== Syncing Attendance Logs (Incremental) ===")
        
        if not self.check_mysql_table_exists('attendance_logs'):
            self.log_signal.emit("ERROR: attendance_logs table does not exist!")
            return 0
        
        positions = load_sync_positions()
        last_sync_id = positions.get('attendance_logs', {}).get('last_sync_id', 0)
        
        config = load_config()
        batch_size = config.get("BATCH_SIZE", 100)
        
        pg_conn = self.connect_to_postgresql()
        if not pg_conn:
            return 0
        
        try:
            cursor = pg_conn.cursor()
            
            if last_sync_id > 0:
                cursor.execute("""
                    SELECT id, emp_code, punch_time, punch_state, verify_type,
                           terminal_sn, terminal_alias, emp_id, terminal_id
                    FROM iclock_transaction
                    WHERE id > %s
                    ORDER BY id ASC
                """, (last_sync_id,))
            else:
                cursor.execute("""
                    SELECT id, emp_code, punch_time, punch_state, verify_type,
                           terminal_sn, terminal_alias, emp_id, terminal_id
                    FROM iclock_transaction
                    ORDER BY id ASC
                """)
            
            pg_records = cursor.fetchall()
            pg_conn.close()
            
            if not pg_records:
                self.log_signal.emit("No new attendance records found")
                return 0
            
            self.log_signal.emit(f"Found {len(pg_records)} records. Processing...")
            
            mysql_conn = self.connect_to_mysql()
            if not mysql_conn:
                return 0
            
            try:
                cursor = mysql_conn.cursor()
                upsert_query = """
                    INSERT INTO attendance_logs 
                    (emp_code, punch_time, punch_state, verify_type, terminal_sn,
                     terminal_alias, emp_id, terminal_id, server_time, source_device)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), 'zkbiotime')
                    ON DUPLICATE KEY UPDATE
                        punch_state = VALUES(punch_state),
                        verify_type = VALUES(verify_type),
                        terminal_alias = VALUES(terminal_alias),
                        server_time = NOW()
                """
                
                total_uploaded = 0
                max_id = 0
                
                for i in range(0, len(pg_records), batch_size):
                    batch = pg_records[i:i + batch_size]
                    
                    for record in batch:
                        values = (
                            record[1], record[2], record[3], record[4],
                            record[5], record[6], record[7], record[8]
                        )
                        cursor.execute(upsert_query, values)
                        total_uploaded += 1
                        max_id = max(max_id, record[0])
                    
                    mysql_conn.commit()
                    
                    batch_num = (i // batch_size) + 1
                    total_batches = (len(pg_records) + batch_size - 1) // batch_size
                    self.log_signal.emit(f"Batch {batch_num}/{total_batches}")
                    
                    time.sleep(0.1)
                
                self.log_signal.emit(f"Uploaded {total_uploaded} attendance records")
                
                positions['attendance_logs'] = {
                    "last_sync_id": max_id,
                    "last_sync_time": datetime.now().isoformat(),
                    "method": "incremental",
                    "records_synced": total_uploaded,
                    "sync_status": "completed"
                }
                save_sync_positions(positions)
                
                self.table_status_signal.emit('attendance_logs', positions['attendance_logs'])
                
                return total_uploaded
            except Exception as e:
                self.log_signal.emit(f"Error syncing attendance_logs: {e}")
                mysql_conn.rollback()
                return 0
            finally:
                try:
                    if mysql_conn and mysql_conn.open:
                        mysql_conn.close()
                except:
                    pass
        except Exception as e:
            self.log_signal.emit(f"Error in attendance_logs sync: {e}")
            return 0
    
    def sync_all_tables(self):
        """Sync all 4 tables in correct order"""
        self.log_signal.emit("========================================")
        self.log_signal.emit("Starting Full 4-Table Sync")
        self.log_signal.emit("========================================")
        
        results = {}
        
        # 1. Departments
        self.log_signal.emit("Step 1: Syncing Departments...")
        results['departments'] = self.sync_departments()
        time.sleep(0.5)
        
        # 2. Devices
        self.log_signal.emit("Step 2: Syncing Devices...")
        results['devices'] = self.sync_devices()
        time.sleep(0.5)
        
        # 3. Employees
        self.log_signal.emit("Step 3: Syncing Employees...")
        results['employees'] = self.sync_employees()
        time.sleep(0.5)
        
        # 4. Attendance Logs
        self.log_signal.emit("Step 4: Syncing Attendance Logs...")
        results['attendance_logs'] = self.sync_attendance_logs()
        
        self.log_signal.emit("========================================")
        self.log_signal.emit(f"Sync Completed!")
        self.log_signal.emit(f"  Departments: {results['departments']} records")
        self.log_signal.emit(f"  Devices: {results['devices']} records")
        self.log_signal.emit(f"  Employees: {results['employees']} records")
        self.log_signal.emit(f"  Attendance: {results['attendance_logs']} records")
        self.log_signal.emit("========================================")
        
        self.status_signal.emit(f"Last sync: {datetime.now().strftime('%H:%M:%S')}")
        
        return results


class TableStatusWidget(QWidget):
    """Widget to display status of a single table"""
    def __init__(self, table_name, display_name):
        super().__init__()
        self.table_name = table_name
        self.display_name = display_name
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Table name
        name_label = QLabel(f"<b>{self.display_name}</b>")
        name_label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(name_label)
        
        # Status label
        self.status_label = QLabel("Status: Pending")
        self.status_label.setFont(QFont("Arial", 9))
        layout.addWidget(self.status_label)
        
        # Last sync label
        self.last_sync_label = QLabel("Last sync: Never")
        self.last_sync_label.setFont(QFont("Arial", 8))
        layout.addWidget(self.last_sync_label)
        
        # Records label
        self.records_label = QLabel("Records: 0")
        self.records_label.setFont(QFont("Arial", 8))
        layout.addWidget(self.records_label)
        
        # Sync button
        self.sync_btn = QPushButton("Sync Now")
        self.sync_btn.setFont(QFont("Arial", 8))
        self.sync_btn.setMaximumWidth(80)
        layout.addWidget(self.sync_btn)
        
        self.setLayout(layout)
        
        # Frame styling
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setLineWidth(2)
    
    def update_status(self, status_data):
        """Update status display"""
        if status_data.get('sync_status') == 'completed':
            self.status_label.setText("Status: ✓ Synced")
            self.status_label.setStyleSheet("color: green;")
        elif status_data.get('sync_status') == 'failed':
            self.status_label.setText("Status: ✗ Failed")
            self.status_label.setStyleSheet("color: red;")
        else:
            self.status_label.setText("Status: Pending")
            self.status_label.setStyleSheet("color: orange;")
        
        # Last sync time
        last_sync = status_data.get('last_sync') or status_data.get('last_sync_time')
        if last_sync:
            try:
                sync_time = datetime.fromisoformat(last_sync)
                self.last_sync_label.setText(f"Last sync: {sync_time.strftime('%Y-%m-%d %H:%M')}")
            except:
                self.last_sync_label.setText(f"Last sync: {last_sync}")
        else:
            self.last_sync_label.setText("Last sync: Never")
        
        # Records count
        records = status_data.get('records_synced', 0)
        self.records_label.setText(f"Records: {records:,}")


class ConfigDialog(QDialog):
    """Dialog for editing configuration"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configuration Editor")
        self.setGeometry(300, 300, 600, 400)
        
        layout = QVBoxLayout()
        
        # PostgreSQL Configuration
        pg_group = QGroupBox("PostgreSQL Configuration (ZKBioTime)")
        pg_layout = QFormLayout()
        
        config = load_config()
        pg_config = config.get("POSTGRESQL_CONFIG", {})
        
        self.pg_host_edit = QLineEdit()
        self.pg_host_edit.setText(pg_config.get("host", "127.0.0.1"))
        pg_layout.addRow("Host:", self.pg_host_edit)
        
        self.pg_port_edit = QLineEdit()
        self.pg_port_edit.setText(str(pg_config.get("port", 7496)))
        pg_layout.addRow("Port:", self.pg_port_edit)
        
        self.pg_database_edit = QLineEdit()
        self.pg_database_edit.setText(pg_config.get("database", "biotime"))
        pg_layout.addRow("Database:", self.pg_database_edit)
        
        self.pg_user_edit = QLineEdit()
        self.pg_user_edit.setText(pg_config.get("user", "postgres"))
        pg_layout.addRow("User:", self.pg_user_edit)
        
        self.pg_password_edit = QLineEdit()
        self.pg_password_edit.setText(pg_config.get("password", ""))
        self.pg_password_edit.setEchoMode(QLineEdit.Password)
        pg_layout.addRow("Password:", self.pg_password_edit)
        
        pg_group.setLayout(pg_layout)
        layout.addWidget(pg_group)
        
        # Sync Schedules
        schedule_group = QGroupBox("Sync Schedules (HH:MM, comma-separated)")
        schedule_layout = QFormLayout()
        
        schedules = config.get("SYNC_SCHEDULES", {})
        
        self.departments_time_edit = QLineEdit()
        dept_schedule = schedules.get("departments", "01:00")
        if isinstance(dept_schedule, list):
            dept_schedule = ", ".join(dept_schedule)
        self.departments_time_edit.setText(dept_schedule)
        schedule_layout.addRow("Departments:", self.departments_time_edit)
        
        self.employees_time_edit = QLineEdit()
        emp_schedule = schedules.get("employees", ["01:00", "07:00", "13:00", "19:00"])
        if isinstance(emp_schedule, list):
            emp_schedule = ", ".join(emp_schedule)
        self.employees_time_edit.setText(emp_schedule)
        schedule_layout.addRow("Employees:", self.employees_time_edit)
        
        self.devices_time_edit = QLineEdit()
        dev_schedule = schedules.get("devices", "02:00")
        if isinstance(dev_schedule, list):
            dev_schedule = ", ".join(dev_schedule)
        self.devices_time_edit.setText(dev_schedule)
        schedule_layout.addRow("Devices:", self.devices_time_edit)
        
        self.attendance_time_edit = QLineEdit()
        att_schedule = schedules.get("attendance_logs", ["09:00", "12:00", "17:00", "22:00"])
        if isinstance(att_schedule, list):
            att_schedule = ", ".join(att_schedule)
        self.attendance_time_edit.setText(att_schedule)
        schedule_layout.addRow("Attendance:", self.attendance_time_edit)
        
        schedule_group.setLayout(schedule_layout)
        layout.addWidget(schedule_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Configuration")
        self.save_btn.clicked.connect(self.save_config)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def save_config(self):
        """Save configuration"""
        try:
            # Parse schedules
            def parse_schedule(text):
                times = [time.strip() for time in text.split(",")]
                for time_str in times:
                    if len(time_str) != 5 or time_str[2] != ':':
                        raise ValueError(f"Invalid time format: {time_str}")
                    hour, minute = time_str.split(':')
                    if not (hour.isdigit() and minute.isdigit()):
                        raise ValueError(f"Invalid time format: {time_str}")
                    h, m = int(hour), int(minute)
                    if h < 0 or h > 23 or m < 0 or m > 59:
                        raise ValueError(f"Invalid time: {time_str}")
                return times if len(times) > 1 else times[0]
            
            config = load_config()
            
            config["POSTGRESQL_CONFIG"] = {
                "host": self.pg_host_edit.text(),
                "port": int(self.pg_port_edit.text()),
                "database": self.pg_database_edit.text(),
                "user": self.pg_user_edit.text(),
                "password": self.pg_password_edit.text()
            }
            
            config["SYNC_SCHEDULES"] = {
                "departments": parse_schedule(self.departments_time_edit.text()),
                "employees": parse_schedule(self.employees_time_edit.text()),
                "devices": parse_schedule(self.devices_time_edit.text()),
                "attendance_logs": parse_schedule(self.attendance_time_edit.text())
            }
            
            save_config(config)
            
            QMessageBox.information(self, "Success", "Configuration saved successfully!")
            self.accept()
        
        except ValueError as e:
            QMessageBox.critical(self, "Error", f"Invalid configuration: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save configuration: {str(e)}")


class LogViewer(QDialog):
    """Dialog for viewing logs"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Log Viewer")
        self.setGeometry(300, 300, 700, 500)
        
        layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        
        layout.addWidget(self.log_text)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def append_log(self, message):
        """Append message to log viewer"""
        self.log_text.append(message)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


class SystemTrayApp:
    """Main System Tray Application"""
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        # Create tray icon
        self.tray_icon = QSystemTrayIcon()
        
        # Use custom icon if available
        icon_path = "zk_upload.ico"
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        else:
            # Create a blue icon if the .ico file is missing
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor(0, 120, 215)) # Windows Blue
            icon = QIcon(pixmap)
        
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("ZK BioTime Cloud Sync")
        
        # Create menu
        self.tray_menu = QMenu()
        
        # Status label
        self.status_action = self.tray_menu.addAction("Status: Idle")
        self.status_action.setEnabled(False)
        self.tray_menu.addSeparator()
        
        # Control actions
        self.start_action = self.tray_menu.addAction("Start Service")
        self.start_action.triggered.connect(self.start_service)
        
        self.stop_action = self.tray_menu.addAction("Stop Service")
        self.stop_action.triggered.connect(self.stop_service)
        
        self.sync_now_action = self.tray_menu.addAction("Sync All Tables Now")
        self.sync_now_action.triggered.connect(self.sync_now)
        
        self.status_action_menu = self.tray_menu.addAction("Check Status")
        self.status_action_menu.triggered.connect(self.check_status)
        
        self.config_action = self.tray_menu.addAction("Configure")
        self.config_action.triggered.connect(self.configure_settings)
        
        self.logs_action = self.tray_menu.addAction("View Logs")
        self.logs_action.triggered.connect(self.view_logs)
        
        self.tray_menu.addSeparator()
        
        self.about_action = self.tray_menu.addAction("About")
        self.about_action.triggered.connect(self.show_about)
        
        self.tray_menu.addSeparator()
        
        self.exit_action = self.tray_menu.addAction("Exit")
        self.exit_action.triggered.connect(self.exit_app)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        
        # Initialize worker
        self.worker = SyncWorker()
        self.worker.status_signal.connect(self.update_status)
        self.worker.log_signal.connect(self.log_message)
        
        self.tray_icon.show()
        self.worker.start()
        self.update_status("Stopped")
        
        # Store logs for viewer
        self.log_messages = []
        
        # Create status window (optional, shown on double-click)
        self.status_window = None
    
    def on_tray_icon_activated(self, reason):
        """Handle tray icon clicks"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_status_window()
    
    def show_status_window(self):
        """Show detailed status window"""
        if self.status_window is None:
            self.status_window = QDialog()
            self.status_window.setWindowTitle("ZK BioTime Sync Status")
            self.status_window.setGeometry(300, 300, 650, 400)
            
            layout = QVBoxLayout()
            
            # Title
            title = QLabel("<h2>4-Table Sync Status</h2>")
            title.setAlignment(0x0004)  # Center
            layout.addWidget(title)
            
            # Table status widgets
            self.table_widgets = {}
            
            for table_name, display_name in [
                ('departments', 'Departments'),
                ('employees', 'Employees'),
                ('devices', 'Devices'),
                ('attendance_logs', 'Attendance Logs')
            ]:
                widget = TableStatusWidget(table_name, display_name)
                self.table_widgets[table_name] = widget
                
                # Connect sync button
                if table_name == 'departments':
                    widget.sync_btn.clicked.connect(lambda: self.sync_table('departments'))
                elif table_name == 'employees':
                    widget.sync_btn.clicked.connect(lambda: self.sync_table('employees'))
                elif table_name == 'devices':
                    widget.sync_btn.clicked.connect(lambda: self.sync_table('devices'))
                elif table_name == 'attendance_logs':
                    widget.sync_btn.clicked.connect(lambda: self.sync_table('attendance_logs'))
                
                layout.addWidget(widget)
            
            # Refresh button
            refresh_btn = QPushButton("Refresh Status")
            refresh_btn.clicked.connect(self.refresh_status)
            layout.addWidget(refresh_btn)
            
            # Close button
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(self.status_window.close)
            layout.addWidget(close_btn)
            
            self.status_window.setLayout(layout)
            
            # Connect worker signal to update widgets
            self.worker.table_status_signal.connect(self.update_table_status)
        
        # Update status before showing
        self.refresh_status()
        self.status_window.show()
    
    def refresh_status(self):
        """Refresh status display"""
        positions = load_sync_positions()
        
        for table_name, widget in self.table_widgets.items():
            if table_name in positions:
                widget.update_status(positions[table_name])
    
    def update_table_status(self, table_name, status_data):
        """Update status for a specific table"""
        if table_name in self.table_widgets:
            self.table_widgets[table_name].update_status(status_data)
    
    def sync_table(self, table_name):
        """Sync a specific table via worker thread request"""
        self.log_message(f"Manual sync requested for {table_name}")
        self.worker.request_manual_sync(table_name)
    
    def update_status(self, status):
        """Update status in menu"""
        self.status_action.setText(f"Status: {status}")
    
    def log_message(self, message):
        """Log message handler and update log viewer if open"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        self.log_messages.append(log_entry)
        
        # Keep only last 1000 messages
        if len(self.log_messages) > 1000:
            self.log_messages = self.log_messages[-1000:]
            
        # Update log viewer if it's open
        if hasattr(self, 'current_log_viewer') and self.current_log_viewer.isVisible():
            self.current_log_viewer.log_text.append(log_entry)
    
    def start_service(self):
        """Start the sync service"""
        self.worker.resume()
        self.update_status("Running")
        self.log_message("Service started")
    
    def stop_service(self):
        """Stop the sync service"""
        self.worker.pause()
        self.update_status("Stopped")
        self.log_message("Service stopped")
    
    def sync_now(self):
        """Force sync all tables via worker thread request"""
        self.log_message("Manual full sync requested")
        self.worker.request_manual_sync()
    
    def check_status(self):
        """Check service status"""
        status = "Running" if not self.worker.paused else "Stopped"
        positions = load_sync_positions()
        
        status_text = f"Service Status: {status}\n\n"
        status_text += "Table Sync Status:\n"
        
        for table_name in ['departments', 'employees', 'devices', 'attendance_logs']:
            if table_name in positions:
                pos = positions[table_name]
                last_sync = pos.get('last_sync') or pos.get('last_sync_time') or 'Never'
                records = pos.get('records_synced', 0)
                sync_status = pos.get('sync_status', 'pending')
                
                status_text += f"\n{table_name.capitalize()}:"
                status_text += f"\n  Status: {sync_status}"
                status_text += f"\n  Last Sync: {last_sync}"
                status_text += f"\n  Records: {records:,}"
        
        QMessageBox.information(None, "Service Status", status_text)
    
    def configure_settings(self):
        """Open configuration dialog"""
        try:
            dialog = ConfigDialog()
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Could not open configuration: {str(e)}")
    
    def view_logs(self):
        """Open log viewer with real-time updates"""
        try:
            if not hasattr(self, 'current_log_viewer') or not self.current_log_viewer.isVisible():
                self.current_log_viewer = QDialog()
                self.current_log_viewer.setWindowTitle("Log Viewer")
                self.current_log_viewer.setGeometry(300, 300, 700, 500)
                
                layout = QVBoxLayout()
                self.current_log_viewer.log_text = QTextEdit()
                self.current_log_viewer.log_text.setReadOnly(True)
                self.current_log_viewer.log_text.setFont(QFont("Consolas", 9))
                
                # Load existing logs
                for msg in self.log_messages:
                    self.current_log_viewer.log_text.append(msg)
                
                layout.addWidget(self.current_log_viewer.log_text)
                
                close_btn = QPushButton("Close")
                close_btn.clicked.connect(self.current_log_viewer.close)
                layout.addWidget(close_btn)
                
                self.current_log_viewer.setLayout(layout)
            
            self.current_log_viewer.show()
            self.current_log_viewer.raise_()
            self.current_log_viewer.activateWindow()
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Could not open log viewer: {str(e)}")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.information(
            None,
            "About ZK BioTime Cloud Sync",
            "ZK BioTime Cloud Sync v2.0 (4-Table Sync)\n"
            "By Apis Co. Ltd. March 2026\n\n"
            "Syncs 4 tables from ZKBioTime PostgreSQL\n"
            "to cloud MySQL database:\n\n"
            "• departments (daily)\n"
            "• employees (every 6 hours)\n"
            "• devices (daily)\n"
            "• attendance_logs (every 4 hours)\n\n"
            "For salary calculation integration."
        )
    
    def exit_app(self):
        """Exit application"""
        self.worker.stop()
        self.tray_icon.hide()
        self.app.quit()
    
    def run(self):
        """Run the application"""
        sys.exit(self.app.exec_())


if __name__ == "__main__":
    print("====================================================")
    print(" ZK BioTime Cloud Sync - System Tray Application ")
    print("====================================================")
    print("Status: Application is starting...")
    print("Check your System Tray (near the clock) for the icon.")
    print("Right-click the icon for the menu, or double-click to show the status.")
    print("Press Ctrl+C in this console to exit.")
    print("----------------------------------------------------")
    
    try:
        app = SystemTrayApp()
        print("Status: Application is running in the system tray.")
        app.run()
    except KeyboardInterrupt:
        print("\nApplication closed by user.")
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
