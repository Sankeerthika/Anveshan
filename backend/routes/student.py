from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import db
import os
from werkzeug.utils import secure_filename
from datetime import datetime, date
from utils.skills import expand_skills

student_bp = Blueprint('student', __name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'uploads', 'profile_pics')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@student_bp.route('/student-dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)

    search_query = request.args.get('q', '').strip()
    type_filter = request.args.get('type', '').strip()
    domain_filter = request.args.get('domain', '').strip()
    mode_filter = request.args.get('mode', '').strip()
    from_date_str = request.args.get('from_date', '').strip()
    to_date_str = request.args.get('to_date', '').strip()

    from_date = None
    to_date = None
    if from_date_str:
        try:
            from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
        except Exception:
            from_date = None
    if to_date_str:
        try:
            to_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()
        except Exception:
            to_date = None

    try:
        cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
        user = cursor.fetchone()
        
        def column_exists(col):
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'events' 
                  AND COLUMN_NAME = %s
            """, (col,))
            res = cursor.fetchone()
            return (res and (res.get('total', 0) if isinstance(res, dict) else (res[0] if res else 0)) > 0)

        order_clause = "created_at DESC" if column_exists('created_at') else "id DESC"
        cursor.execute(f"SELECT * FROM events ORDER BY {order_clause}")
        all_events = cursor.fetchall()

        events = []
        today = date.today()

        user_year_raw = (user.get('year') or "").strip().lower()
        def _norm_year(y):
            y = y.replace("year", "").strip()
            mapping = {
                "1": "1st", "i": "1st", "first": "1st", "1st": "1st",
                "2": "2nd", "ii": "2nd", "second": "2nd", "2nd": "2nd",
                "3": "3rd", "iii": "3rd", "third": "3rd", "3rd": "3rd",
                "4": "4th", "iv": "4th", "fourth": "4th", "4th": "4th"
            }
            return mapping.get(y, y)
        user_year_norm = _norm_year(user_year_raw)

        for ev in all_events:
            dl = ev.get('registration_deadline') or ev.get('deadline')
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
                et = ev.get('end_time')
                if et is not None:
                    if isinstance(et, datetime):
                        et_dt = et
                    elif isinstance(et, date):
                        et_dt = datetime.combine(et, datetime.min.time())
                    else:
                        et_dt = None
                        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y"):
                            try:
                                et_dt = datetime.strptime(str(et), fmt)
                                break
                            except Exception:
                                continue
                    if et_dt and et_dt.date() < today:
                        include = False

            if include:
                target_years_str = (ev.get('target_years') or "").strip()
                ev_type_norm = (ev.get('event_type') or "").strip().lower()
                if target_years_str and user_year_norm and ev_type_norm != 'hackathon':
                    allowed_years = [_norm_year(y.strip().lower()) for y in target_years_str.split(",") if y.strip()]
                    if allowed_years and user_year_norm not in allowed_years:
                        include = False

            if include:
                events.append(ev)

        filtered_events = []
        for ev in events:
            if type_filter:
                ev_type = (ev.get('event_type') or "").strip()
                if ev_type.lower() != type_filter.lower():
                    continue

            if mode_filter:
                ev_mode = (ev.get('mode') or "").strip()
                if ev_mode.lower() != mode_filter.lower():
                    continue

            if domain_filter:
                ev_domains = (ev.get('domains') or "")
                if domain_filter.lower() not in ev_domains.lower():
                    continue

            ev_date_raw = ev.get('event_date')
            ev_date_value = None
            if ev_date_raw is not None:
                if isinstance(ev_date_raw, datetime):
                    ev_date_value = ev_date_raw.date()
                elif isinstance(ev_date_raw, date):
                    ev_date_value = ev_date_raw
                else:
                    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y", "%d/%m/%Y"):
                        try:
                            parsed = datetime.strptime(str(ev_date_raw), fmt)
                            ev_date_value = parsed.date()
                            break
                        except Exception:
                            continue

            if from_date and ev_date_value and ev_date_value < from_date:
                continue
            if to_date and ev_date_value and ev_date_value > to_date:
                continue

            if search_query:
                haystack_parts = [
                    ev.get('title') or "",
                    ev.get('organizer') or ev.get('club_name') or "",
                    ev.get('description') or "",
                    ev.get('domains') or ""
                ]
                haystack = " ".join(str(p) for p in haystack_parts).lower()
                if search_query.lower() not in haystack:
                    continue

            filtered_events.append(ev)

        events = filtered_events

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
            """, (user['email'], event['id']))
            event['team'] = cursor.fetchone()

            # Attach questions
            cursor.execute("""
                SELECT id, question, answer, status, created_at, answered_at
                FROM event_questions
                WHERE event_id = %s AND student_email = %s
                ORDER BY created_at DESC
            """, (event['id'], user['email']))
            event['questions'] = cursor.fetchall()

        # ✅ Fetch faculty collaborations visible to students (status=open, audience=students_only/both)
        student_skills = []
        if user and user.get('skills'):
            student_skills = expand_skills(str(user['skills']).split(','))

        base_sql = """
            SELECT fc.id, fc.title, fc.description, fc.collaboration_type, fc.audience, fc.required_skills, fc.created_at
            FROM faculty_collaborations fc
            WHERE fc.status = 'open'
              AND fc.audience IN ('students_only','both')
        """
        params = []
        if student_skills:
            like_parts = []
            for s in student_skills:
                like_parts.append("fc.required_skills LIKE %s")
                params.append(f"%{s}%")
            base_sql += " AND (" + " OR ".join(like_parts) + ")"
        else:
            # If the student has no skills filled, only show collaborations without required skills
            base_sql += " AND (fc.required_skills IS NULL OR fc.required_skills = '')"

        base_sql += " ORDER BY fc.created_at DESC LIMIT 12"
        cursor.execute(base_sql, tuple(params))
        collaborations = cursor.fetchall()
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        events = []
        user = {}
        collaborations = []
    finally:
        cursor.close()

    return render_template(
        'student_dashboard.html',
        events=events,
        user=user,
        collaborations=collaborations,
        search_query=search_query,
        type_filter=type_filter,
        domain_filter=domain_filter,
        mode_filter=mode_filter,
        from_date_str=from_date_str,
        to_date_str=to_date_str
    )

@student_bp.route('/student/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form.get('name')
        bio = request.form.get('bio')
        skills = request.form.get('skills')
        interests = request.form.get('interests')
        linkedin_url = request.form.get('linkedin_url')
        github_url = request.form.get('github_url')
        portfolio_url = request.form.get('portfolio_url')
        medium_url = request.form.get('medium_url')
        branch = request.form.get('branch')
        year = request.form.get('year')
        section = request.form.get('section')
        
        # Handle file upload
        profile_photo = None
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"user_{session['user_id']}_{file.filename}")
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                profile_photo = filename

        try:
            # Update query
            query = """
                UPDATE users 
                SET name=%s, bio=%s, skills=%s, interests=%s, linkedin_url=%s, github_url=%s, 
                    portfolio_url=%s, medium_url=%s, branch=%s, year=%s, section=%s
            """
            params = [name, bio, skills, interests, linkedin_url, github_url, portfolio_url, medium_url, branch, year, section]
            
            if profile_photo:
                query += ", profile_photo=%s"
                params.append(profile_photo)
            
            query += " WHERE id=%s"
            params.append(session['user_id'])

            cursor.execute(query, tuple(params))
            db.commit()
            flash("Profile updated successfully!", "success")
        except Exception as e:
            db.rollback()
            print(f"Error updating profile: {e}")
            flash("Error updating profile.", "danger")
        
        return redirect(url_for('student.profile'))

    # GET
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()

    return render_template('student_profile.html', user=user)
