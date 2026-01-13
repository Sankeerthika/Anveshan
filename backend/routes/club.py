from flask import Blueprint, render_template, session, redirect, url_for
from db import db
from datetime import datetime, timedelta

club_bp = Blueprint('club', __name__)

def get_event_stats(cursor, club_id, event_type):
    """Helper function to get statistics for a specific event type"""
    try:
        # First, check if the event_type column exists
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'events' 
            AND COLUMN_NAME = 'event_type'
        """)
        has_event_type = cursor.fetchone()['total'] > 0
        
        if not has_event_type:
            # If no event_type column, treat all events as the requested type
            where_clause = "WHERE created_by = %s"
            params = (club_id,)
        else:
            where_clause = "WHERE created_by = %s AND event_type = %s"
            params = (club_id, event_type)
        
        # Get total count
        cursor.execute(f"""
            SELECT COUNT(*) AS total
            FROM events
            {where_clause}
        """, params)
        total = cursor.fetchone()['total'] or 0
        
        # Get active/upcoming count
        cursor.execute(f"""
            SELECT COUNT(*) AS active
            FROM events
            {where_clause}
            AND (end_time >= NOW() OR (start_time IS NULL AND deadline >= CURDATE()))
        """, params)
        active = cursor.fetchone()['active'] or 0
        
        return {'total': total, 'active': active}
        
    except Exception as e:
        print(f"Error getting stats for {event_type}: {str(e)}")
        return {'total': 0, 'active': 0}

@club_bp.route('/club-dashboard')
def club_dashboard():
    # 🔐 Login & role check
    if 'user_id' not in session or session.get('role') != 'club':
        return redirect(url_for('auth.login'))

    club_id = session['user_id']
    cursor = db.cursor(dictionary=True)

    try:
        # Get stats for each event type
        hackathon_stats = get_event_stats(cursor, club_id, 'hackathon')
        event_stats = get_event_stats(cursor, club_id, 'event')
        techtalk_stats = get_event_stats(cursor, club_id, 'techtalk')
        
        # Get total registrations across all events
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM event_registrations er
            JOIN events e ON er.event_id = e.id
            WHERE e.created_by = %s
        """, (club_id,))
        total_registrations = cursor.fetchone()['total']

        # Get recent questions (last 30 days)
        cursor.execute("""
            SELECT q.*, e.title AS event_title, e.event_type
            FROM event_questions q
            JOIN events e ON q.event_id = e.id
            WHERE e.created_by = %s
            AND q.created_at >= %s
            ORDER BY q.created_at DESC
            LIMIT 5
        """, (club_id, (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')))
        recent_questions = cursor.fetchall()

        # Get club name for the welcome message
        cursor.execute("SELECT name FROM clubs WHERE id = %s", (club_id,))
        club = cursor.fetchone() or {'name': 'Club'}

        return render_template(
            'club_dashboard.html',
            club=club,
            hackathon_stats=hackathon_stats,
            event_stats=event_stats,
            techtalk_stats=techtalk_stats,
            total_registrations=total_registrations,
            recent_questions=recent_questions
        )

    except Exception as e:
        print(f"Error in club dashboard: {e}")
        # Return minimal template with error
        return render_template('club_dashboard.html', error=str(e))
    finally:
        cursor.close()