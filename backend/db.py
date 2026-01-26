# backend/db.py
import mysql.connector
import sys
import os
from dotenv import load_dotenv

if not load_dotenv():
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

def _connect_db():
    host_env = os.getenv("DB_HOST", "localhost")
    hosts = [host_env] + (["127.0.0.1"] if host_env.lower() == "localhost" else [])
    last_err = None
    for h in hosts:
        try:
            return mysql.connector.connect(
                host=h,
                user=os.getenv("DB_USER", "root"),
                password=os.getenv("DB_PASSWORD", ""),
                database=os.getenv("DB_NAME", "anveshan"),
                port=int(os.getenv("DB_PORT", 3306)),
                connection_timeout=5
            )
        except mysql.connector.Error as err:
            last_err = err
    print(f"Error connecting to MySQL: {last_err}")
    print("Ensure that your MySQL server is running and reachable at the configured host and port.")
    sys.exit(1)

db = _connect_db()
