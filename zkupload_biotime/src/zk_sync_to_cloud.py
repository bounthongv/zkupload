"""
ZK BioTime Cloud Sync Service - 4 Table Sync
Syncs attendance data from local ZKBioTime PostgreSQL to cloud MySQL database

Tables synced:
1. personnel_department → departments (Full sync, daily)
2. personnel_employee → employees (Incremental by update_time, every 6 hours)
3. iclock_terminal → devices (Incremental by id, daily)
4. iclock_transaction → attendance_logs (Incremental by id, every 4 hours)
"""
import os
import sys
import json
import time
import psycopg2
import pymysql
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration files
CONFIG_FILE = "config.json"
ENCRYPTED_CREDENTIALS_FILE = "encrypted_credentials.bin"
SYNC_POSITIONS_FILE = "sync_positions.json"
LOCK_FILE = "zk_sync.lock"

# Fixed encryption key - must match encrypt_zk_credentials.py
ENCRYPTION_KEY = b'ZK8pQeHY8pQeHY8RMyeYf6e5Twq9PdOBVo9JPsqHZA4='

# Platform-specific file locking
try:
    import fcntl
    USE_FCNTL = True
except ImportError:
    import msvcrt
    USE_FCNTL = False


def load_config():
    """Load public configuration from JSON file"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Create default config with 4-table sync schedules
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
        # Initialize sync positions for all 4 tables
        default_positions = {
            "departments": {
                "last_sync": None,
                "method": "full",
                "records_synced": 0,
                "sync_status": "pending"
            },
            "employees": {
                "last_sync_id": 0,
                "last_sync_time": None,
                "method": "incremental",
                "records_synced": 0,
                "sync_status": "pending"
            },
            "devices": {
                "last_sync_id": 0,
                "last_sync_time": None,
                "method": "incremental",
                "records_synced": 0,
                "sync_status": "pending"
            },
            "attendance_logs": {
                "last_sync_id": 0,
                "last_sync_time": None,
                "method": "incremental",
                "records_synced": 0,
                "sync_status": "pending"
            }
        }
        save_sync_positions(default_positions)
        return default_positions
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


def acquire_lock():
    """Acquire exclusive lock to prevent multiple instances"""
    global lock_file_handle
    try:
        lock_file_handle = open(LOCK_FILE, 'w')
        
        if USE_FCNTL:
            fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        else:
            msvcrt.locking(lock_file_handle.fileno(), msvcrt.LK_NBLCK, 1)
        
        lock_file_handle.write(str(os.getpid()))
        lock_file_handle.flush()
        return True
    except (IOError, OSError):
        if lock_file_handle:
            lock_file_handle.close()
            lock_file_handle = None
        return False


def release_lock():
    """Release the lock"""
    global lock_file_handle
    if lock_file_handle:
        try:
            if USE_FCNTL:
                fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_UN)
            else:
                lock_file_handle.seek(0)
                msvcrt.locking(lock_file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            
            lock_file_handle.close()
            lock_file_handle = None
            
            try:
                os.remove(LOCK_FILE)
            except:
                pass
        except:
            pass


def connect_to_postgresql():
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
        log_msg(f"Error connecting to PostgreSQL: {e}")
        return None


def connect_to_mysql():
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
                connect_timeout=60,
                read_timeout=60,
                write_timeout=60
            )

        # Fallback to encrypted credentials file
        credentials = load_encrypted_credentials()
        if not credentials:
            log_msg("Error: No cloud credentials found in .env or encrypted bin.")
            return None
        
        return pymysql.connect(
            host=credentials.get('host', 'localhost'),
            user=credentials.get('user', ''),
            password=credentials.get('password', ''),
            database=credentials.get('database', ''),
            port=credentials.get('port', 3306),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=60,
            read_timeout=60,
            write_timeout=60
        )
    except Exception as e:
        log_msg(f"Error connecting to MySQL: {e}")
        return None


def check_mysql_table_exists(table_name):
    """Check if table exists in MySQL"""
    mysql_conn = connect_to_mysql()
    if not mysql_conn:
        return False
    
    try:
        cursor = mysql_conn.cursor()
        cursor.execute("SELECT 1 FROM %s LIMIT 1" % table_name)
        cursor.fetchone()
        mysql_conn.close()
        return True
    except Exception as e:
        log_msg(f"MySQL table {table_name} check failed: {e}")
        mysql_conn.close()
        return False


def update_sync_tracking(table_name, last_sync_id, records_synced, sync_status, error=None):
    """Update sync_tracking table in MySQL"""
    mysql_conn = connect_to_mysql()
    if not mysql_conn:
        return False
    
    try:
        cursor = mysql_conn.cursor()
        
        if error:
            query = """
                UPDATE sync_tracking 
                SET last_sync_id = %s, 
                    last_sync_time = NOW(), 
                    records_synced = %s,
                    sync_status = %s,
                    sync_error = %s,
                    updated_at = NOW()
                WHERE table_name = %s
            """
            cursor.execute(query, (last_sync_id, records_synced, sync_status, error, table_name))
        else:
            query = """
                UPDATE sync_tracking 
                SET last_sync_id = %s, 
                    last_sync_time = NOW(), 
                    records_synced = %s,
                    sync_status = %s,
                    updated_at = NOW()
                WHERE table_name = %s
            """
            cursor.execute(query, (last_sync_id, records_synced, sync_status, table_name))
        
        mysql_conn.commit()
        return True
    except Exception as e:
        log_msg(f"Error updating sync_tracking: {e}")
        mysql_conn.rollback()
        return False
    finally:
        try:
            if mysql_conn and mysql_conn.open:
                mysql_conn.close()
        except:
            pass


# ================================================================
# SYNC FUNCTION 1: Departments (Full Sync)
# ================================================================
def sync_departments():
    """Sync personnel_department from PostgreSQL to departments in MySQL (Full Sync)"""
    log_msg("=== Starting Departments Sync (Full Sync) ===")
    
    # Check if target table exists
    if not check_mysql_table_exists('departments'):
        log_msg("ERROR: departments table does not exist in MySQL!")
        return 0
    
    pg_conn = connect_to_postgresql()
    if not pg_conn:
        return 0
    
    try:
        # Get all departments from PostgreSQL
        cursor = pg_conn.cursor()
        query = """
            SELECT id, dept_code, dept_name, parent_dept_id
            FROM personnel_department
            ORDER BY id
        """
        cursor.execute(query)
        pg_records = cursor.fetchall()
        pg_conn.close()
        
        if not pg_records:
            log_msg("No departments found in PostgreSQL")
            return 0
        
        log_msg(f"Found {len(pg_records)} departments in PostgreSQL")
        
        # Sync to MySQL
        mysql_conn = connect_to_mysql()
        if not mysql_conn:
            return 0
        
        try:
            cursor = mysql_conn.cursor()
            
            # Use REPLACE INTO for full sync (updates existing, inserts new)
            replace_query = """
                REPLACE INTO departments 
                (id, dept_code, dept_name, parent_dept_id, last_sync)
                VALUES (%s, %s, %s, %s, NOW())
            """
            
            count = 0
            for record in pg_records:
                values = (
                    record[0],  # id
                    record[1],  # dept_code
                    record[2],  # dept_name
                    record[3]   # parent_dept_id
                )
                cursor.execute(replace_query, values)
                count += 1
            
            mysql_conn.commit()
            log_msg(f"Uploaded {count} departments to cloud MySQL")
            
            # Update sync tracking
            update_sync_tracking('departments', count, count, 'completed')
            
            # Update sync positions
            positions = load_sync_positions()
            positions['departments'] = {
                "last_sync": datetime.now().isoformat(),
                "method": "full",
                "records_synced": count,
                "sync_status": "completed"
            }
            save_sync_positions(positions)
            
            return count
        except Exception as e:
            log_msg(f"Error syncing departments: {e}")
            mysql_conn.rollback()
            update_sync_tracking('departments', 0, 0, 'failed', str(e))
            return 0
        finally:
            try:
                if mysql_conn and mysql_conn.open:
                    mysql_conn.close()
            except:
                pass
    except Exception as e:
        log_msg(f"Error in departments sync: {e}")
        return 0


# ================================================================
# SYNC FUNCTION 2: Employees (Incremental by update_time)
# ================================================================
def sync_employees():
    """Sync personnel_employee from PostgreSQL to employees in MySQL (Incremental)"""
    log_msg("=== Starting Employees Sync (Incremental) ===")
    
    # Check if target table exists
    if not check_mysql_table_exists('employees'):
        log_msg("ERROR: employees table does not exist in MySQL!")
        return 0
    
    # Load sync positions
    positions = load_sync_positions()
    last_sync_time = positions.get('employees', {}).get('last_sync_time')
    
    pg_conn = connect_to_postgresql()
    if not pg_conn:
        return 0
    
    try:
        cursor = pg_conn.cursor()
        
        # Query employees with updates since last sync
        if last_sync_time:
            query = """
                SELECT id, emp_code, first_name, last_name, nickname,
                       department_id, emp_type, hire_date, is_active,
                       mobile, email
                FROM personnel_employee
                WHERE update_time > %s OR change_time > %s
                ORDER BY id
            """
            cursor.execute(query, (last_sync_time, last_sync_time))
        else:
            # First sync - get all active employees
            query = """
                SELECT id, emp_code, first_name, last_name, nickname,
                       department_id, emp_type, hire_date, is_active,
                       mobile, email
                FROM personnel_employee
                WHERE is_active = TRUE
                ORDER BY id
            """
            cursor.execute(query)
        
        pg_records = cursor.fetchall()
        pg_conn.close()
        
        if not pg_records:
            log_msg("No new or updated employees found")
            return 0
        
        log_msg(f"Found {len(pg_records)} employees to sync")
        
        # Sync to MySQL
        mysql_conn = connect_to_mysql()
        if not mysql_conn:
            return 0
        
        try:
            cursor = mysql_conn.cursor()
            
            # Use ON DUPLICATE KEY UPDATE for incremental sync
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
                    record[0],  # id
                    record[1],  # emp_code
                    record[2],  # first_name
                    record[3],  # last_name
                    record[4],  # nickname → display_name
                    record[5],  # department_id
                    record[6],  # emp_type
                    record[7],  # hire_date
                    record[8],  # is_active
                    record[9],  # mobile
                    record[10]  # email
                )
                cursor.execute(upsert_query, values)
                count += 1
                max_id = max(max_id, record[0])
            
            mysql_conn.commit()
            log_msg(f"Uploaded {count} employees to cloud MySQL")
            
            # Update sync tracking
            update_sync_tracking('employees', max_id, count, 'completed')
            
            # Update sync positions
            positions['employees'] = {
                "last_sync_id": max_id,
                "last_sync_time": datetime.now().isoformat(),
                "method": "incremental",
                "records_synced": count,
                "sync_status": "completed"
            }
            save_sync_positions(positions)
            
            return count
        except Exception as e:
            log_msg(f"Error syncing employees: {e}")
            mysql_conn.rollback()
            update_sync_tracking('employees', 0, 0, 'failed', str(e))
            return 0
        finally:
            try:
                if mysql_conn and mysql_conn.open:
                    mysql_conn.close()
            except:
                pass
    except Exception as e:
        log_msg(f"Error in employees sync: {e}")
        return 0


# ================================================================
# SYNC FUNCTION 3: Devices (Incremental by id)
# ================================================================
def sync_devices():
    """Sync iclock_terminal from PostgreSQL to devices in MySQL (Incremental by id)"""
    log_msg("=== Starting Devices Sync (Incremental) ===")
    
    # Check if target table exists
    if not check_mysql_table_exists('devices'):
        log_msg("ERROR: devices table does not exist in MySQL!")
        return 0
    
    # Load sync positions
    positions = load_sync_positions()
    last_sync_id = positions.get('devices', {}).get('last_sync_id', 0)
    
    pg_conn = connect_to_postgresql()
    if not pg_conn:
        return 0
    
    try:
        cursor = pg_conn.cursor()
        
        # Query devices newer than last sync
        if last_sync_id > 0:
            query = """
                SELECT id, sn, alias, ip_address, state, is_attendance, last_activity
                FROM iclock_terminal
                WHERE id > %s
                ORDER BY id
            """
            cursor.execute(query, (last_sync_id,))
        else:
            # First sync - get all devices
            query = """
                SELECT id, sn, alias, ip_address, state, is_attendance, last_activity
                FROM iclock_terminal
                ORDER BY id
            """
            cursor.execute(query)
        
        pg_records = cursor.fetchall()
        pg_conn.close()
        
        if not pg_records:
            log_msg("No new devices found")
            return 0
        
        log_msg(f"Found {len(pg_records)} devices to sync")
        
        # Sync to MySQL
        mysql_conn = connect_to_mysql()
        if not mysql_conn:
            return 0
        
        try:
            cursor = mysql_conn.cursor()
            
            # Use ON DUPLICATE KEY UPDATE for incremental sync
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
                    record[0],  # id
                    record[1],  # sn → terminal_sn
                    record[2],  # alias → terminal_alias
                    record[3],  # ip_address
                    record[4],  # state
                    record[5],  # is_attendance
                    record[6]   # last_activity
                )
                cursor.execute(upsert_query, values)
                count += 1
                max_id = max(max_id, record[0])
            
            mysql_conn.commit()
            log_msg(f"Uploaded {count} devices to cloud MySQL")
            
            # Update sync tracking
            update_sync_tracking('devices', max_id, count, 'completed')
            
            # Update sync positions
            positions['devices'] = {
                "last_sync_id": max_id,
                "last_sync_time": datetime.now().isoformat(),
                "method": "incremental",
                "records_synced": count,
                "sync_status": "completed"
            }
            save_sync_positions(positions)
            
            return count
        except Exception as e:
            log_msg(f"Error syncing devices: {e}")
            mysql_conn.rollback()
            update_sync_tracking('devices', 0, 0, 'failed', str(e))
            return 0
        finally:
            try:
                if mysql_conn and mysql_conn.open:
                    mysql_conn.close()
            except:
                pass
    except Exception as e:
        log_msg(f"Error in devices sync: {e}")
        return 0


# ================================================================
# SYNC FUNCTION 4: Attendance Logs (Incremental by id)
# ================================================================
def sync_attendance_logs():
    """Sync iclock_transaction from PostgreSQL to attendance_logs in MySQL (Incremental by id)"""
    log_msg("=== Starting Attendance Logs Sync (Incremental) ===")
    
    # Check if target table exists
    if not check_mysql_table_exists('attendance_logs'):
        log_msg("ERROR: attendance_logs table does not exist in MySQL!")
        return 0
    
    # Load sync positions
    positions = load_sync_positions()
    last_sync_id = positions.get('attendance_logs', {}).get('last_sync_id', 0)
    
    config = load_config()
    batch_size = config.get("BATCH_SIZE", 100)
    
    pg_conn = connect_to_postgresql()
    if not pg_conn:
        return 0
    
    try:
        cursor = pg_conn.cursor()
        
        # Query attendance records newer than last sync
        if last_sync_id > 0:
            query = """
                SELECT id, emp_code, punch_time, punch_state, verify_type,
                       terminal_sn, terminal_alias, emp_id, terminal_id
                FROM iclock_transaction
                WHERE id > %s
                ORDER BY id ASC
            """
            cursor.execute(query, (last_sync_id,))
        else:
            # First sync - get all records
            query = """
                SELECT id, emp_code, punch_time, punch_state, verify_type,
                       terminal_sn, terminal_alias, emp_id, terminal_id
                FROM iclock_transaction
                ORDER BY id ASC
            """
            cursor.execute(query)
        
        pg_records = cursor.fetchall()
        pg_conn.close()
        
        if not pg_records:
            log_msg("No new attendance records found")
            return 0
        
        log_msg(f"Found {len(pg_records)} attendance records. Processing in batches of {batch_size}...")
        
        # Sync to MySQL
        mysql_conn = connect_to_mysql()
        if not mysql_conn:
            return 0
        
        try:
            cursor = mysql_conn.cursor()
            
            # Use ON DUPLICATE KEY UPDATE for idempotent sync
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
            
            # Process in batches
            for i in range(0, len(pg_records), batch_size):
                batch = pg_records[i:i + batch_size]
                
                for record in batch:
                    values = (
                        record[1],  # emp_code
                        record[2],  # punch_time
                        record[3],  # punch_state
                        record[4],  # verify_type
                        record[5],  # terminal_sn
                        record[6],  # terminal_alias
                        record[7],  # emp_id
                        record[8]   # terminal_id
                    )
                    cursor.execute(upsert_query, values)
                    total_uploaded += 1
                    max_id = max(max_id, record[0])
                
                mysql_conn.commit()
                
                batch_num = (i // batch_size) + 1
                total_batches = (len(pg_records) + batch_size - 1) // batch_size
                log_msg(f"Batch {batch_num}/{total_batches}: Processed {len(batch)} records")
                
                # Small delay between batches
                time.sleep(0.1)
            
            log_msg(f"Uploaded {total_uploaded} attendance records to cloud MySQL")
            
            # Update sync tracking
            update_sync_tracking('attendance_logs', max_id, total_uploaded, 'completed')
            
            # Update sync positions
            positions['attendance_logs'] = {
                "last_sync_id": max_id,
                "last_sync_time": datetime.now().isoformat(),
                "method": "incremental",
                "records_synced": total_uploaded,
                "sync_status": "completed"
            }
            save_sync_positions(positions)
            
            return total_uploaded
        except Exception as e:
            log_msg(f"Error syncing attendance_logs: {e}")
            mysql_conn.rollback()
            update_sync_tracking('attendance_logs', 0, 0, 'failed', str(e))
            return 0
        finally:
            try:
                if mysql_conn and mysql_conn.open:
                    mysql_conn.close()
            except:
                pass
    except Exception as e:
        log_msg(f"Error in attendance_logs sync: {e}")
        return 0


# ================================================================
# MAIN SYNC ORCHESTRATION
# ================================================================
def sync_all_tables():
    """Sync all 4 tables in correct order"""
    log_msg("========================================")
    log_msg("Starting Full 4-Table Sync")
    log_msg("========================================")
    
    results = {}
    
    # 1. Sync Departments (no dependencies)
    log_msg("Step 1: Syncing Departments...")
    results['departments'] = sync_departments()
    time.sleep(0.5)
    
    # 2. Sync Devices (no dependencies)
    log_msg("Step 2: Syncing Devices...")
    results['devices'] = sync_devices()
    time.sleep(0.5)
    
    # 3. Sync Employees (depends on departments)
    log_msg("Step 3: Syncing Employees...")
    results['employees'] = sync_employees()
    time.sleep(0.5)
    
    # 4. Sync Attendance Logs (depends on employees and devices)
    log_msg("Step 4: Syncing Attendance Logs...")
    results['attendance_logs'] = sync_attendance_logs()
    
    log_msg("========================================")
    log_msg(f"Sync Completed!")
    log_msg(f"  Departments: {results['departments']} records")
    log_msg(f"  Devices: {results['devices']} records")
    log_msg(f"  Employees: {results['employees']} records")
    log_msg(f"  Attendance: {results['attendance_logs']} records")
    log_msg("========================================")
    
    return results


def get_next_schedule(schedules):
    """Calculate the next scheduled sync time"""
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    
    all_times = []
    for table, schedule in schedules.items():
        if isinstance(schedule, str) and schedule.strip():
            all_times.append(schedule.strip())
        elif isinstance(schedule, list):
            for t in schedule:
                if isinstance(t, str) and t.strip():
                    all_times.append(t.strip())
    
    all_times = sorted(list(set(all_times)))
    
    if not all_times:
        return "None"
        
    for t in all_times:
        if t > current_time:
            return t
            
    return all_times[0]  # First schedule of tomorrow


def should_sync_table(table_name, schedules):
    """Check if table should be synced based on schedule"""
    current_time = datetime.now().strftime("%H:%M")
    
    schedule = schedules.get(table_name)
    if not schedule:
        return False
    
    # Handle both string (single time) and list (multiple times)
    if isinstance(schedule, str):
        return current_time == schedule
    elif isinstance(schedule, list):
        return current_time in schedule
    
    return False


if __name__ == "__main__":
    lock_file_handle = None
    
    log_msg("=== ZK BioTime Cloud Sync Service Started (4-Table Sync) ===")
    
    # Load configuration
    config = load_config()
    log_msg(f"PostgreSQL Host: {config['POSTGRESQL_CONFIG']['host']}:{config['POSTGRESQL_CONFIG']['port']}")
    log_msg(f"PostgreSQL Database: {config['POSTGRESQL_CONFIG']['database']}")
    log_msg(f"Sync Schedules: {config.get('SYNC_SCHEDULES', {})}")
    log_msg(f"Batch Size: {config.get('BATCH_SIZE', 100)}")
    
    # Check credentials
    credentials = load_encrypted_credentials()
    log_msg(f"MySQL Credentials: {'LOADED' if credentials else 'NOT FOUND'}")
    
    # Check if MySQL tables exist
    tables_to_check = ['departments', 'employees', 'devices', 'attendance_logs']
    all_tables_exist = True
    for table in tables_to_check:
        if not check_mysql_table_exists(table):
            log_msg(f"WARNING: {table} table does not exist in MySQL!")
            all_tables_exist = False
    
    if not all_tables_exist:
        log_msg("Please run docs/zk_cloud_setup.sql to create tables")
    
    # Try to acquire lock
    if not acquire_lock():
        log_msg("Another instance is already running. Exiting...")
        sys.exit(1)
    
    log_msg("Lock acquired. Starting sync service...")
    
    try:
        # Continuous operation with scheduled sync times
        schedules = config.get("SYNC_SCHEDULES", {})
        last_sync_completed_at = None
        
        while True:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            
            # Check if any table should be synced
            should_sync = False
            
            for table_name in ['departments', 'employees', 'devices', 'attendance_logs']:
                if should_sync_table(table_name, schedules):
                    should_sync = True
                    break
            
            if should_sync:
                log_msg(f"Scheduled time reached ({current_time}). Starting full sync...")
                sync_all_tables()
                last_sync_completed_at = datetime.now()
                
                # Show waiting message after sync
                next_t = get_next_schedule(schedules)
                log_msg(f"Sync completed at {last_sync_completed_at.strftime('%H:%M:%S')}. Waiting for next schedule at {next_t}...")
                
                # Sleep for 61 seconds to avoid re-triggering in the same minute
                time.sleep(61)
            else:
                # Only show waiting message once every 10 minutes to avoid log spam
                if not last_sync_completed_at or (now.minute % 10 == 0 and now.second < 30):
                    next_t = get_next_schedule(schedules)
                    log_msg(f"Sync idle. Waiting for next schedule at {next_t}... (Current time: {current_time})")
            
            # Sleep for 30 seconds
            time.sleep(30)
    
    except KeyboardInterrupt:
        log_msg("Service interrupted by user")
    except Exception as e:
        log_msg(f"Error in sync service: {e}")
        import traceback
        traceback.print_exc()
    finally:
        release_lock()
        log_msg("Lock released.")
    
    log_msg("=== ZK BioTime Cloud Sync Service Ended ===")
