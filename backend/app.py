import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask, render_template, redirect, url_for, session
from datetime import datetime, date
from backend.routes.auth import auth_bp
from backend.routes.events import events_bp
from backend.routes.club import club_bp
from backend.routes.find_team import find_team_bp
from backend.routes.student import student_bp
from backend.routes.collaboration import collaboration_bp
from backend.db import db
import os
from dotenv import load_dotenv
from backend.config import SMTP_CONFIG, APP_CONFIG

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = APP_CONFIG.get("SECRET_KEY")
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Auto-reload templates
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Prevent caching of static files

app.config.update(SMTP_CONFIG)
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
