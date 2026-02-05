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
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key_change_in_production")
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Auto-reload templates
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Prevent caching of static files

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
# CONTEXT PROCESSOR
# ===============================
@app.context_processor
def inject_user():
    user = None
    if 'user_id' in session:
        try:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
            user = cursor.fetchone()
            cursor.close()
        except Exception as e:
            app.logger.error(f"Error injecting user: {e}")
    return dict(user=user, now=datetime.now())

# ===============================
# HOME ROUTE
# ===============================
@app.route('/')
def home():
    return render_template('landing.html', now=datetime.now())

# ===============================
# RUN APP
# ===============================
if __name__ == "__main__":
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=True, use_reloader=True, use_debugger=True)