
import json
import os
import pymysql
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration files
ENCRYPTED_CREDENTIALS_FILE = "encrypted_credentials.bin"
ENCRYPTION_KEY = b'ZK8pQeHY8pQeHY8RMyeYf6e5Twq9PdOBVo9JPsqHZA4='

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
        print(f"Error: {ENCRYPTED_CREDENTIALS_FILE} not found. Run encrypt_credentials.bat first.")
        return None
    except Exception as e:
        print(f"Error decrypting credentials: {e}")
        return None

def test_connection():
    print("=== ZK BioTime Cloud Sync - Cloud Connection Test ===")
    
    # Try loading from environment variables first (.env)
    env_host = os.getenv("MYSQL_HOST")
    env_user = os.getenv("MYSQL_USER")
    env_password = os.getenv("MYSQL_PASSWORD")
    env_database = os.getenv("MYSQL_DATABASE")
    env_port = os.getenv("MYSQL_PORT", "3306")

    credentials = {}
    if all([env_host, env_user, env_database]):
        print("Using credentials from .env file...")
        credentials = {
            'host': env_host,
            'user': env_user,
            'password': env_password,
            'database': env_database,
            'port': int(env_port)
        }
    else:
        print("No complete .env found, trying encrypted credentials...")
        credentials = load_encrypted_credentials()
    
    if not credentials:
        print("❌ ERROR: No credentials found. Please fill .env or run encrypt_credentials.bat")
        return

    print(f"Attempting to connect to cloud MySQL at {credentials.get('host')}...")
    
    try:
        conn = pymysql.connect(
            host=credentials.get('host'),
            user=credentials.get('user'),
            password=credentials.get('password'),
            database=credentials.get('database'),
            port=credentials.get('port', 3306),
            connect_timeout=10
        )
        print("✅ SUCCESS: Successfully connected to cloud MySQL database!")
        
        with conn.cursor() as cursor:
            # Check for tables
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['departments', 'employees', 'devices', 'attendance_logs', 'sync_tracking']
            print("\nDatabase Check:")
            for table in required_tables:
                status = "✓" if table in tables else "✗ (MISSING)"
                print(f"  {status} Table: {table}")
            
            if not all(table in tables for table in required_tables):
                print("\n⚠️  WARNING: Some tables are missing. Please run docs/zk_cloud_setup.sql on your cloud database.")
        
        conn.close()
    except Exception as e:
        print(f"❌ ERROR: Connection failed: {e}")

if __name__ == "__main__":
    test_connection()
