import mysql.connector
import sys
import os
from dotenv import load_dotenv

# Load .env from project root if not already loaded
if not load_dotenv():
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

def _connect_db(host_override=None):
    host_env = os.getenv("DB_HOST", "localhost")
    host = host_override or host_env
    try_hosts = [host] + (["127.0.0.1"] if host.lower() == "localhost" else [])
    last_err = None
    for h in try_hosts:
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
    raise last_err or RuntimeError("Unknown MySQL connection error")

class ReconnectingDB:
    def __init__(self):
        self._conn = None
        self._ensure()

    def _ensure(self):
        try:
            if self._conn is None:
                self._conn = _connect_db()
            elif not self._conn.is_connected():
                try:
                    self._conn.reconnect(attempts=3, delay=2)
                except Exception:
                    self._conn = _connect_db()
        except Exception as e:
            print(f"Error connecting to MySQL: {e}")
            print("Ensure that your MySQL server is running and reachable at the configured host and port.")
            raise

    def cursor(self, *args, **kwargs):
        self._ensure()
        return self._conn.cursor(*args, **kwargs)

    def commit(self):
        self._ensure()
        return self._conn.commit()

    def rollback(self):
        try:
            if self._conn:
                return self._conn.rollback()
        except Exception:
            return None

    def close(self):
        try:
            if self._conn:
                self._conn.close()
        except Exception:
            pass

    def is_connected(self):
        try:
            return self._conn.is_connected() if self._conn else False
        except Exception:
            return False

# Export a reconnecting DB handle compatible with existing usage
db = ReconnectingDB()
