"""
ZK BioTime Cloud Sync - Credential Encryption Utility
Encrypts MySQL cloud database credentials for secure storage
"""
import json
import getpass
from cryptography.fernet import Fernet

# Fixed encryption key - DO NOT CHANGE once credentials are encrypted
# This key is embedded in compiled executables
ENCRYPTION_KEY = b'ZK8pQeHY8pQeHY8RMyeYf6e5Twq9PdOBVo9JPsqHZA4='

def encrypt_credentials():
    """Encrypt MySQL cloud database credentials"""
    print("=== ZK BioTime Cloud Sync - Credential Encryption ===")
    print("\nEnter your MySQL cloud database credentials:\n")
    
    # Get credentials from user
    host = input("Host (e.g., cloud.example.com): ").strip()
    port = input("Port (default: 3306): ").strip() or "3306"
    database = input("Database name: ").strip()
    user = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    
    # Create credentials dictionary
    credentials = {
        "DB_CONFIG": {
            "host": host,
            "port": int(port),
            "database": database,
            "user": user,
            "password": password
        }
    }
    
    # Encrypt credentials
    fernet = Fernet(ENCRYPTION_KEY)
    encrypted_data = fernet.encrypt(json.dumps(credentials).encode())
    
    # Save to file
    output_file = "encrypted_credentials.bin"
    with open(output_file, 'wb') as f:
        f.write(encrypted_data)
    
    print(f"\n✅ Credentials encrypted and saved to: {output_file}")
    print("\n⚠️  IMPORTANT:")
    print(f"   - Keep this file secure: {output_file}")
    print(f"   - Never share this file with unauthorized persons")
    print(f"   - The encryption key is embedded in compiled executables")
    print(f"   - If you lose this file, you'll need to re-run this utility")
    
    # Verify encryption
    print("\n--- Verification ---")
    try:
        with open(output_file, 'rb') as f:
            encrypted_data_verify = f.read()
        decrypted_data = fernet.decrypt(encrypted_data_verify)
        decrypted_credentials = json.loads(decrypted_data.decode())
        print(f"Host: {decrypted_credentials['DB_CONFIG']['host']}")
        print(f"Port: {decrypted_credentials['DB_CONFIG']['port']}")
        print(f"Database: {decrypted_credentials['DB_CONFIG']['database']}")
        print(f"User: {decrypted_credentials['DB_CONFIG']['user']}")
        print("Password: ********")
        print("\n✅ Verification successful - credentials can be decrypted")
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")

if __name__ == "__main__":
    try:
        encrypt_credentials()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
