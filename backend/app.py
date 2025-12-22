from flask import Flask, render_template, redirect, url_for, session
from datetime import datetime, date
from routes.auth import auth_bp
from routes.events import events_bp
from routes.club import club_bp
from routes.find_team import find_team_bp
from db import db

app = Flask(__name__)
app.secret_key = "secret123"

# ===============================
# REGISTER BLUEPRINTS
# ===============================
app.register_blueprint(auth_bp)
app.register_blueprint(events_bp)
app.register_blueprint(find_team_bp)
app.register_blueprint(club_bp)

# ===============================
# HOME ROUTE
# ===============================
@app.route('/')
def home():
    return redirect(url_for('auth.login'))

# ===============================
# STUDENT DASHBOARD
# ===============================
@app.route('/student-dashboard')
def student_dashboard():
    # 🔐 Auth check
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)

    try:
        # ✅ Get logged-in student's email
        cursor.execute(
            "SELECT email FROM users WHERE id = %s",
            (session['user_id'],)
        )
        user = cursor.fetchone()
        user_email = user['email']

        # ✅ Fetch all hackathons
        cursor.execute("""
            SELECT *
            FROM events
            ORDER BY deadline ASC
        """)
        all_events = cursor.fetchall()

        # Filter out events whose deadline is in the past
        events = []
        today = date.today()

        for ev in all_events:
            dl = ev.get('deadline')
            include = True

            if dl is None:
                include = True
            else:
                # dl may be a date/datetime or a string
                if isinstance(dl, datetime):
                    dl_date = dl.date()
                elif isinstance(dl, date):
                    dl_date = dl
                else:
                    # try parsing common string formats
                    dl_date = None
                    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y", "%d/%m/%Y"):
                        try:
                            parsed = datetime.strptime(str(dl), fmt)
                            dl_date = parsed.date()
                            break
                        except Exception:
                            continue

                if dl_date is not None and dl_date < today:
                    include = False

            if include:
                events.append(ev)

        # ✅ Attach team info if student already registered (only for included events)
        for event in events:
            cursor.execute("""
                SELECT 
                    r.id AS registration_id,
                    r.team_name,
                    r.project_title,
                    r.domain
                FROM event_registrations r
                JOIN event_team_members tm
                    ON r.id = tm.registration_id
                WHERE tm.member_email = %s
                  AND r.event_id = %s
            """, (user_email, event['id']))

            event['team'] = cursor.fetchone()
            # attach any questions the student asked for this event
            cursor.execute("""
                SELECT id, question, answer, status, created_at, answered_at
                FROM event_questions
                WHERE event_id = %s AND student_email = %s
                ORDER BY created_at DESC
            """, (event['id'], user_email))
            event['questions'] = cursor.fetchall()

    finally:
        cursor.close()

    return render_template(
        'student_dashboard.html',
        events=events
    )

# ===============================
# RUN APP
# ===============================
if __name__ == "__main__":
    app.run(debug=True)
