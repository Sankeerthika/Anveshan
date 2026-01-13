from flask import Flask, render_template, redirect, url_for, session
from datetime import datetime, date
from routes.auth import auth_bp
from routes.events import events_bp
from routes.club import club_bp
from routes.find_team import find_team_bp
from routes.student import student_bp
from routes.collaboration import collaboration_bp
from db import db
import os

app = Flask(__name__)
app.secret_key = "secret123"
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Auto-reload templates
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Prevent caching of static files
def load_env_file():
    root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
    local_env = os.path.abspath(os.path.join(os.path.dirname(__file__), '.env'))
    for p in (root_env, local_env):
        if os.path.isfile(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#') or '=' not in line:
                            continue
                        k, v = line.split('=', 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and v and not os.environ.get(k):
                            os.environ[k] = v
            except Exception:
                pass
load_env_file()
app.config.update({
    "SMTP_HOST": os.environ.get("SMTP_HOST"),
    "SMTP_PORT": os.environ.get("SMTP_PORT") or 587,
    "SMTP_USER": os.environ.get("SMTP_USER"),
    "SMTP_PASSWORD": os.environ.get("SMTP_PASSWORD"),
    "SMTP_TLS": str(os.environ.get("SMTP_TLS", "true")).lower() in ("1", "true", "yes", "on"),
})
app.logger.info(
    "SMTP config: HOST=%s USER=%s TLS=%s",
    app.config.get("SMTP_HOST"),
    app.config.get("SMTP_USER"),
    app.config.get("SMTP_TLS")
)

# ===============================
# REGISTER BLUEPRINTS
# ===============================
app.register_blueprint(auth_bp)
app.register_blueprint(events_bp)
app.register_blueprint(find_team_bp)
app.register_blueprint(club_bp)
app.register_blueprint(student_bp)
app.register_blueprint(collaboration_bp)

# ===============================
# HOME ROUTE
# ===============================
@app.route('/')
def home():
    return redirect(url_for('auth.login'))

# ===============================
# RUN APP
# ===============================
if __name__ == "__main__":
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=True, use_reloader=True, use_debugger=True)
