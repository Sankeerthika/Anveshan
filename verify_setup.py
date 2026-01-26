import os
import sys
import importlib
from dotenv import load_dotenv
import mysql.connector

# Add backend to path so we can import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def check_env():
    print("Checking environment variables...")
    load_dotenv()
    required_vars = ["DB_HOST", "DB_USER", "DB_NAME", "SECRET_KEY"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        return False
    print("✅ Environment variables present.")
    return True

def check_db_connection():
    print("\nChecking database connection...")
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "anveshan"),
            port=int(os.getenv("DB_PORT", 3306))
        )
        conn.close()
        print("✅ Database connection successful.")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_imports():
    print("\nChecking imports...")
    modules_to_check = [
        "app",
        "db",
        "routes.auth",
        "routes.events",
        "routes.club",
        "routes.find_team",
        "routes.student",
        "routes.collaboration"
    ]
    
    all_good = True
    for module in modules_to_check:
        try:
            importlib.import_module(module)
            print(f"✅ Imported {module}")
        except Exception as e:
            print(f"❌ Failed to import {module}: {e}")
            all_good = False
    return all_good

def main():
    print("=== Anveshan System Verification ===\n")
    
    env_ok = check_env()
    db_ok = check_db_connection()
    imports_ok = check_imports()
    
    print("\n" + "="*30)
    if env_ok and db_ok and imports_ok:
        print("🎉 System verification PASSED. The app should run correctly.")
        print("Run 'python backend/app.py' to start the server.")
    else:
        print("⚠️ System verification FAILED. Please fix the errors above.")

if __name__ == "__main__":
    main()
