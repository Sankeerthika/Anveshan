from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from backend.db import db
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename
from flask import current_app

club_bp = Blueprint('club', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def get_event_stats(cursor, club_id, event_type):
    """Helper function to get statistics for a specific event type"""
    try:
        def column_exists(col):
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'events' 
                  AND COLUMN_NAME = %s
            """, (col,))
            res = cursor.fetchone()
            return (res and res.get('total', 0) > 0)

        has_event_type = column_exists('event_type')
        has_created_by = column_exists('created_by')
        has_deadline = column_exists('deadline')
        has_start_time = column_exists('start_time')
        has_end_time = column_exists('end_time')

        where_clause = []
        params = []

        if has_created_by:
            where_clause.append("created_by = %s")
            params.append(club_id)
        else:
            cursor.execute("SELECT name FROM clubs WHERE id = %s", (club_id,))
            club = cursor.fetchone()
            org_name = (club and (club.get('name') if isinstance(club, dict) else club[0])) or None
            if not org_name:
                cursor.execute("SELECT name FROM users WHERE id = %s AND role = 'club'", (club_id,))
                u = cursor.fetchone()
                org_name = (u and (u.get('name') if isinstance(u, dict) else u[0])) or None
            if org_name:
                where_clause.append("organizer = %s")
                params.append(org_name)

        if has_event_type:
            where_clause.append("event_type = %s")
            params.append(event_type)

        wc = ("WHERE " + " AND ".join(where_clause)) if where_clause else ""
        
        cursor.execute(f"""
            SELECT COUNT(*) AS total
            FROM events
            {wc}
        """, tuple(params))
        total = cursor.fetchone()['total'] or 0
        
        active_cond_parts = []
        if has_end_time:
            active_cond_parts.append("(end_time IS NOT NULL AND end_time >= NOW())")
        if has_start_time and has_deadline:
            active_cond_parts.append("(start_time IS NULL AND (deadline IS NULL OR deadline >= CURDATE()))")
        elif has_deadline:
            active_cond_parts.append("(deadline IS NULL OR deadline >= CURDATE())")
        else:
            active_cond_parts.append("1=1")

        active_cond = " OR ".join(active_cond_parts)

        cursor.execute(f"""
            SELECT COUNT(*) AS active
            FROM events
            {wc}{" AND " if wc else " WHERE "}{active_cond}
        """, tuple(params))
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
            SELECT q.*, e.title AS event_title, e.event_type, u.name AS student_name
            FROM event_questions q
            JOIN events e ON q.event_id = e.id
            LEFT JOIN users u ON u.email = q.student_email
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

@club_bp.route('/post-announcement', methods=['GET'])
def post_announcement_page():
    if 'user_id' not in session or session.get('role') != 'club':
        return redirect(url_for('auth.login'))
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT name FROM clubs WHERE id = %s", (session['user_id'],))
    club = cursor.fetchone() or {'name': 'Club'}
    cursor.close()
    return render_template('post_announcement.html', club=club, event=None)

@club_bp.route('/post_announcement', methods=['POST'])
def post_announcement():
    if 'user_id' not in session or session.get('role') != 'club':
        return redirect(url_for('auth.login'))

    title = request.form.get('title')
    description = request.form.get('description') or None
    registration_end_date = request.form.get('registration_end_date') or None
    external_registration_link = request.form.get('external_registration_link') or None
    target_years_list = request.form.getlist('target_years')
    target_years = ",".join(target_years_list) if target_years_list else None

    if not title or not external_registration_link or not registration_end_date:
        flash("Please provide title, registration end date and registration link.", "danger")
        return redirect(url_for('club.club_dashboard'))

    poster_file = request.files.get('poster')
    poster_path = None
    if poster_file and poster_file.filename and allowed_file(poster_file.filename):
        upload_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'uploads', 'hackathons')
        os.makedirs(upload_root, exist_ok=True)
        filename = secure_filename(f"hackathon_{session['user_id']}_{int(datetime.now().timestamp())}_{poster_file.filename}")
        poster_file.save(os.path.join(upload_root, filename))
        poster_path = os.path.join('uploads', 'hackathons', filename).replace("\\", "/")

    cursor = db.cursor()
    try:
        cursor.execute("SELECT name FROM clubs WHERE id = %s", (session['user_id'],))
        club = cursor.fetchone()
        organizer_name = club[0] if club else None
        if not organizer_name:
            cursor.execute("SELECT name FROM users WHERE id = %s AND role = 'club'", (session['user_id'],))
            u = cursor.fetchone()
            organizer_name = (u and (u.get('name') if isinstance(u, dict) else u[0])) or None
        cursor.execute("""
            INSERT INTO events
            (title, event_type, description, deadline, organizer, created_by, poster_path, external_registration_link, target_years)
            VALUES (%s, 'hackathon', %s, %s, %s, %s, %s, %s, %s)
        """, (title, description, registration_end_date, organizer_name, session['user_id'], poster_path, external_registration_link, target_years))
        db.commit()
        flash("Announcement posted. Students in targeted years will see it.", "success")
    except Exception as e:
        db.rollback()
        print(f"Error posting announcement: {e}")
        if current_app.debug:
            flash(f"Error posting announcement: {e}", "danger")
        else:
            flash("Error posting announcement. Please try again.", "danger")
    finally:
        cursor.close()

    return redirect(url_for('club.club_dashboard'))

@club_bp.route('/edit-announcement')
def edit_announcements_page():
    if 'user_id' not in session or session.get('role') != 'club':
        return redirect(url_for('auth.login'))
    club_id = session['user_id']
    cursor = db.cursor(dictionary=True)
    try:
        def column_exists(col):
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'events' 
                  AND COLUMN_NAME = %s
            """, (col,))
            res = cursor.fetchone()
            return (res and res.get('total', 0) > 0)
        has_event_type = column_exists('event_type')
        has_created_by = column_exists('created_by')
        has_deadline = column_exists('deadline')
        has_start_time = column_exists('start_time')
        has_end_time = column_exists('end_time')
        has_created_at = column_exists('created_at')
        where_clause = []
        params = []
        if has_created_by:
            where_clause.append("created_by = %s")
            params.append(club_id)
        else:
            cursor.execute("SELECT name FROM clubs WHERE id = %s", (club_id,))
            club = cursor.fetchone()
            org_name = (club and (club.get('name') if isinstance(club, dict) else club[0])) or None
            if not org_name:
                cursor.execute("SELECT name FROM users WHERE id = %s AND role = 'club'", (club_id,))
                u = cursor.fetchone()
                org_name = (u and (u.get('name') if isinstance(u, dict) else u[0])) or None
            if org_name:
                where_clause.append("organizer = %s")
                params.append(org_name)
        if has_event_type:
            where_clause.append("event_type = %s")
            params.append('hackathon')
        wc = ("WHERE " + " AND ".join(where_clause)) if where_clause else ""
        active_cond_parts = []
        if has_end_time:
            active_cond_parts.append("(end_time IS NOT NULL AND end_time >= NOW())")
        if has_start_time and has_deadline:
            active_cond_parts.append("(start_time IS NULL AND (deadline IS NULL OR deadline >= CURDATE()))")
        elif has_deadline:
            active_cond_parts.append("(deadline IS NULL OR deadline >= CURDATE())")
        else:
            active_cond_parts.append("1=1")
        active_cond = " OR ".join(active_cond_parts)
        order_clause = "ORDER BY created_at DESC" if has_created_at else "ORDER BY id DESC"
        cursor.execute(f"""
            SELECT id, title, event_type, deadline, external_registration_link, target_years
            FROM events
            {wc}{" AND " if wc else " WHERE "}{active_cond}
            {order_clause}
        """, tuple(params))
        events = cursor.fetchall()
        hackathons = []
        for e in events or []:
            tys = e.get('target_years') or ""
            if isinstance(tys, str):
                years = [t.strip() for t in tys.split(",") if t.strip()]
            else:
                years = []
            hackathons.append({
                "id": e.get("id"),
                "title": e.get("title"),
                "event_type": e.get("event_type"),
                "deadline": e.get("deadline"),
                "external_registration_link": e.get("external_registration_link"),
                "target_years": years,
            })
        cursor.execute("SELECT name FROM clubs WHERE id = %s", (club_id,))
        club = cursor.fetchone() or {'name': 'Club'}
        return render_template('edit_announcements.html', hackathons=hackathons, club=club)
    except Exception as e:
        print(f"Error loading edit announcements: {e}")
        flash("Error loading active hackathons.", "danger")
        return redirect(url_for('club.club_dashboard'))
    finally:
        cursor.close()

@club_bp.route('/edit-announcement/<int:event_id>')
def edit_announcement(event_id):
    if 'user_id' not in session or session.get('role') != 'club':
        return redirect(url_for('auth.login'))
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT * FROM events WHERE id = %s
        """, (event_id,))
        event = cursor.fetchone()
        if not event:
            flash("Event not found.", "danger")
            return redirect(url_for('club.edit_announcements_page'))
        # Ownership check by created_by or organizer fallback
        allowed = False
        club_id = session['user_id']
        if event.get('created_by') == club_id:
            allowed = True
        else:
            cursor.execute("SELECT name FROM clubs WHERE id = %s", (club_id,))
            club = cursor.fetchone()
            org_name = (club and (club.get('name') if isinstance(club, dict) else club[0])) or None
            if not org_name:
                cursor.execute("SELECT name FROM users WHERE id = %s AND role = 'club'", (club_id,))
                u = cursor.fetchone()
                org_name = (u and (u.get('name') if isinstance(u, dict) else u[0])) or None
            if org_name and (event.get('organizer') == org_name):
                allowed = True
        if not allowed:
            flash("You do not have permission to edit this event.", "warning")
            return redirect(url_for('club.edit_announcements_page'))
        cursor.execute("SELECT name FROM clubs WHERE id = %s", (club_id,))
        club = cursor.fetchone() or {'name': 'Club'}
        return render_template('post_announcement.html', event=event, club=club)
    except Exception as e:
        print(f"Error loading event for edit: {e}")
        flash("Error while opening edit page.", "danger")
        return redirect(url_for('club.edit_announcements_page'))
    finally:
        cursor.close()

@club_bp.route('/update-announcement/<int:event_id>', methods=['POST'])
def update_announcement(event_id):
    if 'user_id' not in session or session.get('role') != 'club':
        return redirect(url_for('auth.login'))
    title = request.form.get('title')
    description = request.form.get('description') or None
    registration_end_date = request.form.get('registration_end_date') or None
    external_registration_link = request.form.get('external_registration_link') or None
    target_years_list = request.form.getlist('target_years')
    target_years = ",".join(target_years_list) if target_years_list else None
    if not title or not external_registration_link or not registration_end_date:
        flash("Please provide title, registration end date and registration link.", "danger")
        return redirect(url_for('club.edit_announcement', event_id=event_id))
    poster_file = request.files.get('poster')
    poster_path_set = None
    if poster_file and poster_file.filename and allowed_file(poster_file.filename):
        upload_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'uploads', 'hackathons')
        os.makedirs(upload_root, exist_ok=True)
        filename = secure_filename(f"hackathon_{session['user_id']}_{int(datetime.now().timestamp())}_{poster_file.filename}")
        poster_file.save(os.path.join(upload_root, filename))
        poster_path_set = os.path.join('uploads', 'hackathons', filename).replace("\\", "/")
    cursor = db.cursor()
    try:
        params = [title, description, registration_end_date, external_registration_link, target_years, event_id]
        set_clause = "title=%s, description=%s, deadline=%s, external_registration_link=%s, target_years=%s"
        if poster_path_set:
            set_clause += ", poster_path=%s"
            params = [title, description, registration_end_date, external_registration_link, target_years, poster_path_set, event_id]
        cursor.execute(f"UPDATE events SET {set_clause} WHERE id=%s", tuple(params))
        db.commit()
        flash("Hackathon updated successfully.", "success")
    except Exception as e:
        db.rollback()
        print(f"Error updating announcement: {e}")
        if current_app.debug:
            flash(f"Error updating hackathon: {e}", "danger")
        else:
            flash("Error updating hackathon.", "danger")
    finally:
        cursor.close()
    return redirect(url_for('club.edit_announcements_page'))
