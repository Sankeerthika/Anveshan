import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "anveshan"),
    "port": int(os.getenv("DB_PORT", 3306))
}

SMTP_CONFIG = {
    "SMTP_HOST": os.getenv("SMTP_HOST"),
    "SMTP_PORT": int(os.getenv("SMTP_PORT", 587)),
    "SMTP_USER": os.getenv("SMTP_USER"),
    "SMTP_PASSWORD": os.getenv("SMTP_PASSWORD"),
    "SMTP_TLS": str(os.getenv("SMTP_TLS", "true")).lower() in ("1", "true", "yes", "on")
}

APP_CONFIG = {
    "SECRET_KEY": os.getenv("SECRET_KEY", "dev_secret_key_change_in_production"),
    "ALLOWED_DOMAINS": os.getenv("ALLOWED_DOMAINS", "anurag.edu.in")
}
