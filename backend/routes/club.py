from flask import Blueprint, render_template, session, redirect, url_for
from db import db
from datetime import datetime, timedelta

club_bp = Blueprint('club', __name__)

@club_bp.route('/club-dashboard')
def club_dashboard():

    # 🔐 Login & role check
    if 'user_id' not in session or session.get('role') != 'club':
        return redirect(url_for('auth.login'))

    club_id = session['user_id']

    cursor = db.cursor(dictionary=True)

    # 1️⃣ Total hackathons created by this club
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM events
        WHERE created_by = %s
    """, (club_id,))
    total_events = cursor.fetchone()['total']

    # 2️⃣ Total student registrations for this club's events
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM event_registrations er
        JOIN events e ON er.event_id = e.id
        WHERE e.created_by = %s
    """, (club_id,))
    total_students = cursor.fetchone()['total']

    # 3️⃣ Active events (deadline not passed)
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM events
        WHERE created_by = %s
          AND deadline >= CURDATE()
    """, (club_id,))
    active_events = cursor.fetchone()['total']

    # 4️⃣ Recent questions from students (last 30 days)
    cursor.execute("""
        SELECT q.*, e.title AS event_title
        FROM event_questions q
        JOIN events e ON q.event_id = e.id
        WHERE e.created_by = %s
        AND q.created_at >= %s
        ORDER BY q.created_at DESC
        LIMIT 3
    """, (club_id, (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')))
    recent_questions = cursor.fetchall()

    cursor.close()

    return render_template(
        'club_dashboard.html',
        total_events=total_events,
        total_students=total_students,
        active_events=active_events,
        recent_questions=recent_questions
    )
