import mysql.connector
import os
from dotenv import load_dotenv

# Load .env from backend directory as verify_schema.py is in root but uses backend config
load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))
# Also try root .env
load_dotenv()

def check_schema():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "anveshan"),
            port=int(os.getenv("DB_PORT", 3306))
        )
        cursor = conn.cursor()
        
        tables = ['faculty_collaborations', 'collaboration_requests']
        for table in tables:
            print(f"\nChecking table: {table}...")
            try:
                cursor.execute(f"DESCRIBE {table}")
                columns = cursor.fetchall()
                print(f"Table {table} exists. Columns:")
                for col in columns:
                    print(f"  {col[0]} ({col[1]})")
            except mysql.connector.Error as err:
                print(f"Error checking {table}: {err}")
                
        conn.close()
        print("\nSchema check finished.")
    except Exception as e:
        print(f"\nSchema check failed: {e}")

if __name__ == "__main__":
    check_schema()