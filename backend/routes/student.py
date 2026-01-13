from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import db
import os
from werkzeug.utils import secure_filename
from datetime import datetime, date

student_bp = Blueprint('student', __name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'uploads', 'profile_pics')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@student_bp.route('/student-dashboard')
def dashboard():
    # 🔐 Auth check
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)

    try:
        # ✅ Get logged-in student's details
        cursor.execute(
            "SELECT * FROM users WHERE id = %s",
            (session['user_id'],)
        )
        user = cursor.fetchone()
        
        # ✅ Fetch all events
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
            # Check registration
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
            student_skills = [s.strip() for s in str(user['skills']).split(',') if s.strip()]

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
    finally:
        cursor.close()

    return render_template(
        'student_dashboard.html',
        events=events,
        user=user,
        collaborations=collaborations
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
