import mysql.connector
from backend.config import DB_CONFIG

def _connect_db(host_override=None):
    host_env = DB_CONFIG.get("host", "localhost")
    host = host_override or host_env
    try_hosts = [host] + (["127.0.0.1"] if host.lower() == "localhost" else [])
    last_err = None
    for h in try_hosts:
        try:
            conn = mysql.connector.connect(
                host=h,
                user=DB_CONFIG.get("user", "root"),
                password=DB_CONFIG.get("password", ""),
                database=DB_CONFIG.get("database", "anveshan"),
                port=int(DB_CONFIG.get("port", 3306)),
                charset="utf8mb4",
                connection_timeout=5
            )
            try:
                conn.set_charset_collation("utf8mb4", "utf8mb4_unicode_ci")
            except Exception:
                pass
            return conn
        except mysql.connector.Error as err:
            last_err = err
    raise last_err or RuntimeError("Unknown MySQL connection error")

class ReconnectingDB:
    def __init__(self):
        self._conn = None

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
