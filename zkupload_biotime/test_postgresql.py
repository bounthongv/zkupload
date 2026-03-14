"""
ZK BioTime PostgreSQL Connection Test
Tests connection to ZKBioTime PostgreSQL database and verifies iclock_transaction table
"""
import psycopg2
import json
from datetime import datetime

def load_config():
    """Load configuration from config.json"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return None

def test_postgresql_connection():
    """Test PostgreSQL connection and query iclock_transaction"""
    print("=== ZK BioTime PostgreSQL Connection Test ===\n")
    
    config = load_config()
    if not config:
        print("❌ Failed to load config.json")
        return
    
    pg_config = config.get("POSTGRESQL_CONFIG", {})
    
    print("Configuration:")
    print(f"  Host: {pg_config.get('host', 'N/A')}")
    print(f"  Port: {pg_config.get('port', 'N/A')}")
    print(f"  Database: {pg_config.get('database', 'N/A')}")
    print(f"  User: {pg_config.get('user', 'N/A')}")
    print(f"  Password: {'****' if pg_config.get('password') else '(empty)'}")
    print()
    
    try:
        # Test connection
        print("Connecting to PostgreSQL...")
        conn = psycopg2.connect(
            host=pg_config.get('host', '127.0.0.1'),
            port=pg_config.get('port', 7496),
            database=pg_config.get('database', 'biotime'),
            user=pg_config.get('user', 'postgres'),
            password=pg_config.get('password', ''),
            connect_timeout=30
        )
        print("✅ PostgreSQL connection successful!\n")
        
        # Test query iclock_transaction
        print("Querying iclock_transaction table...")
        cursor = conn.cursor()
        
        # Get table structure
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'iclock_transaction'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        print(f"\n✅ iclock_transaction table found!")
        print(f"   Total columns: {len(columns)}")
        print("\n   Key columns:")
        
        key_columns = ['id', 'emp_code', 'punch_time', 'punch_state', 
                      'verify_type', 'terminal_sn', 'terminal_alias', 
                      'emp_id', 'terminal_id']
        
        for col in columns:
            if col[0] in key_columns:
                nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
                print(f"   - {col[0]:20} {col[1]:20} {nullable}")
        
        # Get record count
        cursor.execute("SELECT COUNT(*) FROM iclock_transaction")
        count = cursor.fetchone()[0]
        print(f"\n📊 Total records in iclock_transaction: {count:,}")
        
        # Get latest records
        print("\n📋 Latest 5 records:")
        cursor.execute("""
            SELECT id, emp_code, punch_time, punch_state, verify_type, 
                   terminal_sn, terminal_alias
            FROM iclock_transaction
            ORDER BY punch_time DESC
            LIMIT 5
        """)
        
        records = cursor.fetchall()
        print(f"   {'ID':<8} {'Emp Code':<12} {'Punch Time':<22} {'State':<8} {'Type':<6} {'Device SN':<20} {'Alias':<15}")
        print("   " + "-" * 105)
        
        for rec in records:
            punch_time_str = str(rec[2])[:19] if rec[2] else 'N/A'
            print(f"   {rec[0]:<8} {rec[1]:<12} {punch_time_str:<22} {rec[3]:<8} {rec[4]:<6} {str(rec[5] or 'N/A'):<20} {str(rec[6] or 'N/A'):<15}")
        
        # Get record count by punch_state
        print("\n📊 Records by punch_state:")
        cursor.execute("""
            SELECT punch_state, COUNT(*) as count
            FROM iclock_transaction
            GROUP BY punch_state
            ORDER BY punch_state
        """)
        
        state_counts = cursor.fetchall()
        for state in state_counts:
            print(f"   State '{state[0]}': {state[1]:,} records")
        
        # Get record count by verify_type
        print("\n📊 Records by verify_type:")
        cursor.execute("""
            SELECT verify_type, COUNT(*) as count
            FROM iclock_transaction
            GROUP BY verify_type
            ORDER BY verify_type
        """)
        
        type_counts = cursor.fetchall()
        type_names = {0: 'Unknown', 1: 'Fingerprint', 2: 'Face', 3: 'Card', 
                     4: 'Password', 5: 'Mobile'}
        for type_count in type_counts:
            type_name = type_names.get(type_count[0], 'Other')
            print(f"   Type {type_count[0]} ({type_name}): {type_count[1]:,} records")
        
        # Get devices
        print("\n📊 Devices (terminal_sn):")
        cursor.execute("""
            SELECT terminal_sn, terminal_alias, COUNT(*) as count
            FROM iclock_transaction
            WHERE terminal_sn IS NOT NULL
            GROUP BY terminal_sn, terminal_alias
            ORDER BY count DESC
            LIMIT 10
        """)
        
        devices = cursor.fetchall()
        for dev in devices:
            print(f"   {str(dev[0] or 'N/A'):<25} {str(dev[1] or 'N/A'):<20} {dev[2]:,} records")
        
        cursor.close()
        conn.close()
        
        print("\n✅ All tests passed!")
        print("\nNext steps:")
        print("1. Run encrypt_credentials.bat to set up cloud MySQL credentials")
        print("2. Create zk_attendance_logs table on cloud MySQL (see docs/zk_cloud_setup.sql)")
        print("3. Run run_zk_sync.bat or run_zk_tray.bat to start syncing")
        
    except psycopg2.OperationalError as e:
        print(f"\n❌ Connection failed!")
        print(f"   Error: {e}")
        print("\nTroubleshooting:")
        print("1. Verify ZKBioTime is running")
        print("2. Check PostgreSQL service: services.msc → look for 'bio-pgsql'")
        print("3. Verify password in D:\\ZKBioTime\\attsite.ini")
        print("4. Check firewall allows port 7496")
        
    except psycopg2.ProgrammingError as e:
        print(f"\n❌ Database error!")
        print(f"   Error: {e}")
        print("\nPossible issues:")
        print("1. Database name is incorrect")
        print("2. iclock_transaction table doesn't exist")
        print("3. User doesn't have permission to access the table")
        
    except Exception as e:
        print(f"\n❌ Unexpected error!")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_postgresql_connection()
