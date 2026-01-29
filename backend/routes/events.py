from flask import Blueprint, request, redirect, url_for, flash, session, render_template, Response, current_app
from db import db
import os
import csv
from datetime import datetime
from werkzeug.utils import secure_filename
import json
from dotenv import load_dotenv

load_dotenv()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def is_college_email(email: str) -> bool:
    try:
        e = (email or "").strip().lower()
        if "@" not in e:
            return False
        domain = e.split("@")[-1]
        allowed_domains_str = os.getenv("ALLOWED_DOMAINS", "anurag.edu.in")
        allowed_domains = {d.strip() for d in allowed_domains_str.split(",")}
        return domain in allowed_domains
    except Exception:
        return False
events_bp = Blueprint('events', __name__)
from routes.club import club_bp

# Ensure uploads directory exists
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Ensure questions table exists
try:
    c = db.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS event_questions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            event_id INT NOT NULL,
            student_email VARCHAR(255),
            question TEXT NOT NULL,
            answer TEXT,
            answered_by INT,
            status ENUM('open','answered') DEFAULT 'open',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            answered_at DATETIME NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    ''')
    db.commit()
    c.close()
except Exception:
    pass

# ================================
# LIST ALL EVENTS (PUBLIC)
# ================================
@events_bp.route('/events')
def events():
    cursor = db.cursor(dictionary=True)
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
    events = cursor.fetchall()
    cursor.close()
    return render_template('events.html', events=events)

# ================================
# STUDENT REGISTRATION
# ================================
@events_bp.route('/register/<int:event_id>')
def open_registration_form(event_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM events WHERE id = %s", (event_id,))
    event = cursor.fetchone()
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()

    if not event:
        flash("Event not found", "danger")
        return redirect(url_for('student.dashboard'))

    if event.get('external_registration_link'):
        return redirect(event['external_registration_link'])
    else:
        flash("This event uses external registration. Link unavailable.", "warning")
        return redirect(url_for('student.dashboard'))

    return render_template('hackathon_registration.html', event=event, event_id=event_id, user=user)


@events_bp.route('/submit-registration', methods=['POST'])
def submit_registration():
    flash("On-platform registrations are disabled. Please use the external link.", "warning")
    return redirect(url_for('student.dashboard'))


# ================================
# QUESTIONS / DOUBTS (STUDENTS)
# ================================
@events_bp.route('/event/<int:event_id>/questions')
def event_questions(event_id):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM events WHERE id = %s", (event_id,))
        event = cursor.fetchone()
        if not event:
            flash("Event not found", "danger")
            return redirect(url_for('student.dashboard'))
        cursor.execute("""
            SELECT id, student_email, question, answer, status, created_at, answered_at
            FROM event_questions
            WHERE event_id = %s
            ORDER BY created_at DESC
        """, (event_id,))
        questions = cursor.fetchall()
        user = None
        if 'user_id' in session:
            cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
            user = cursor.fetchone()
    except Exception as e:
        print(f"Error loading event questions: {e}")
        flash("Error loading questions for this event.", "danger")
        return redirect(url_for('student.dashboard'))
    finally:
        cursor.close()
    return render_template('event_questions.html', event=event, questions=questions, user=user)

@events_bp.route('/submit-question', methods=['POST'])
def submit_question():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    question = request.form.get('question')
    event_id = request.form.get('event_id')

    if not question or not event_id:
        flash('Please enter your question.', 'danger')
        try:
            eid = int(event_id)
            return redirect(url_for('events.event_questions', event_id=eid))
        except Exception:
            return redirect(url_for('student.dashboard'))

    # get student email
    cursor = db.cursor()
    cursor.execute("SELECT email FROM users WHERE id=%s", (session['user_id'],))
    student_email = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO event_questions (event_id, student_email, question)
        VALUES (%s, %s, %s)
    """, (event_id, student_email, question))
    db.commit()
    cursor.close()

    flash('Question submitted!', 'success')
    return redirect(url_for('events.event_questions', event_id=int(event_id)))


# ================================
# CLUB: CREATE EVENT / HACKATHON
# ================================

@events_bp.route('/create-hackathon', methods=['GET', 'POST'])
def create_hackathon():
    if 'user_id' not in session or session.get('role') != 'club':
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        event_date = request.form.get('event_date')
        deadline = request.form.get('deadline')
        mode = request.form.get('mode')
        venue = request.form.get('venue')

        min_team_size = request.form.get('min_team_size', 1)
        max_team_size = request.form.get('max_team_size', 4)

        domains = ",".join(request.form.getlist('domains[]')) if request.form.getlist('domains[]') else None

        poster_file = request.files.get('poster')
        poster_path = None
        if poster_file and poster_file.filename and allowed_file(poster_file.filename):
            filename = secure_filename(f"hackathon_{session['user_id']}_{int(datetime.now().timestamp())}_{poster_file.filename}")
            dest_folder = os.path.join(UPLOAD_FOLDER, 'hackathons')
            os.makedirs(dest_folder, exist_ok=True)
            poster_file.save(os.path.join(dest_folder, filename))
            poster_path = os.path.join('uploads', 'hackathons', filename).replace("\\", "/")

        external_registration_link = request.form.get('external_registration_link') or None
        if external_registration_link:
            external_registration_link = external_registration_link.strip()
            if external_registration_link == "":
                external_registration_link = None

        target_years_list = request.form.getlist('target_years[]')
        target_years = ",".join(target_years_list) if target_years_list else None

        cursor = db.cursor()
        try:
            cursor.execute("""
                INSERT INTO events
                (title, event_type, description, event_date, deadline, mode, venue,
                 created_by, min_team_size, max_team_size, domains, poster_path,
                 external_registration_link, target_years)
                VALUES (%s, 'hackathon', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                title, description, event_date, deadline, mode, venue,
                session['user_id'], min_team_size, max_team_size, domains, poster_path,
                external_registration_link, target_years
            ))
            db.commit()
            flash("✅ Hackathon created successfully!", "success")
            return redirect(url_for('events.create_event'))
        except Exception as e:
            db.rollback()
            print(f"Error creating hackathon: {e}")
            flash("Error creating hackathon. Please try again.", "danger")
        finally:
            cursor.close()

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()

    return render_template('create_hackathon.html', user=user)




@events_bp.route('/edit-question/<int:qid>', methods=['GET', 'POST'])
def edit_question(qid):
    if 'user_id' not in session or session.get('role') != 'student':
        flash('Unauthorized', 'danger')
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)

    # ensure this student owns the question
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    u = cursor.fetchone()
    student_email = u['email'] if u else None

    cursor.execute('SELECT * FROM event_questions WHERE id = %s', (qid,))
    q = cursor.fetchone()
    if not q or q.get('student_email') != student_email:
        cursor.close()
        flash('You are not allowed to edit this question.', 'danger')
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        new_q = request.form.get('question')
        if not new_q:
            flash('Please enter the question text.', 'danger')
            cursor.close()
            return redirect(url_for('events.edit_question', qid=qid))

        # update question, reset answer so club can re-answer
        cursor.execute(
            """
            UPDATE event_questions
            SET question = %s, status = 'open', answer = NULL, answered_by = NULL, answered_at = NULL
            WHERE id = %s
            """,
            (new_q, qid)
        )
        db.commit()
        cursor.close()
        flash('Question updated.', 'success')
        return redirect(url_for('student.dashboard'))

    cursor.close()
    return render_template('edit_question.html', q=q, user=u)


# ================================
# CLUB: View and answer questions
# ================================
@club_bp.route('/club-questions')
def club_questions():
    if 'user_id' not in session or session.get('role') != 'club':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)

    # Fetch user for sidebar
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()

    # fetch questions for events created by this club
    cursor.execute('''
        SELECT q.*, e.title AS event_title
        FROM event_questions q
        JOIN events e ON e.id = q.event_id
        WHERE e.created_by = %s
        ORDER BY q.created_at DESC
    ''', (session['user_id'],))

    questions = cursor.fetchall()
    cursor.close()
    return render_template('club_questions.html', questions=questions, user=user)


@club_bp.route('/answer-question/<int:qid>', methods=['GET', 'POST'])
def answer_question(qid):
    if 'user_id' not in session or session.get('role') != 'club':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':
        answer = request.form.get('answer')
        if not answer:
            flash('Please provide an answer.', 'danger')
            return redirect(url_for('club.answer_question', qid=qid))

        cursor.execute(
            "UPDATE event_questions SET answer=%s, answered_by=%s, status='answered', answered_at=%s WHERE id=%s",
            (answer, session['user_id'], datetime.now(), qid)
        )
        db.commit()
        cursor.close()
        flash('Answer submitted.', 'success')
        return redirect(url_for('club.club_questions'))

    cursor.execute('SELECT q.*, e.title AS event_title FROM event_questions q JOIN events e ON e.id = q.event_id WHERE q.id = %s', (qid,))
    q = cursor.fetchone()
    cursor.close()
    return render_template('answer_question.html', q=q)


# ================================
# CREATE EVENT (CLUB)
# ================================
@events_bp.route('/create-event', methods=['GET', 'POST'])
def create_event():
    if 'user_id' not in session or session.get('role') != 'club':
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))
    flash("Manage Events is disabled. Use Post Announcement instead.", "warning")
    return redirect(url_for('club.post_announcement_page'))


# ================================
# VIEW REGISTRATIONS (CLUB)
# ================================
@events_bp.route('/view-registrations')
def view_registrations():
    if 'user_id' not in session or session.get('role') != 'club':
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)
    
    try:
        selected_event_id = request.args.get('event_id')
        event_filter_clause = ""
        params = [session['user_id']]
        if selected_event_id:
            event_filter_clause = " AND r.event_id = %s"
            params.append(selected_event_id)

        # Base query to get all registrations for events created by this club
        query = f"""
            SELECT 
                r.*,
                e.title AS event_title
            FROM event_registrations r
            JOIN events e ON e.id = r.event_id
            WHERE e.created_by = %s{event_filter_clause}
            ORDER BY r.created_at DESC
        """
        
        cursor.execute(query, tuple(params))
        registrations = cursor.fetchall()
        
        # For each registration, get team members
        for reg in registrations:
            cursor.execute("""
                SELECT 
                    member_name,
                    member_email,
                    branch,
                    year
                FROM event_team_members 
                WHERE registration_id = %s
            """, (reg['id'],))
            
            members = cursor.fetchall()
            reg['team_members'] = members
            reg['team_size'] = len(members) + 1  # +1 for team lead

        # Get unique values for filters
        branch_query = f"""
            SELECT DISTINCT team_lead_branch as branch 
            FROM event_registrations r
            JOIN events e ON e.id = r.event_id
            WHERE e.created_by = %s AND team_lead_branch IS NOT NULL{event_filter_clause}
        """
        cursor.execute(branch_query, tuple(params))
        branches = [row['branch'] for row in cursor.fetchall()]

        year_query = f"""
            SELECT DISTINCT team_lead_year as year 
            FROM event_registrations r
            JOIN events e ON e.id = r.event_id
            WHERE e.created_by = %s AND team_lead_year IS NOT NULL{event_filter_clause}
        """
        cursor.execute(year_query, tuple(params))
        years = [row['year'] for row in cursor.fetchall()]

        domain_query = f"""
            SELECT DISTINCT domain 
            FROM event_registrations 
            WHERE domain IS NOT NULL
        """
        # domain is not tied to created_by table in current schema; when filtering by event, restrict via registration ids
        if selected_event_id:
            domain_query += " AND event_id = %s"
            cursor.execute(domain_query, (selected_event_id,))
        else:
            cursor.execute(domain_query)
        domains = [row['domain'] for row in cursor.fetchall()]

        # Events list for selector
        cursor.execute("""
            SELECT id, title
            FROM events
            WHERE created_by = %s
            ORDER BY id DESC
        """, (session['user_id'],))
        events_list = cursor.fetchall()

        cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
        user = cursor.fetchone()

        selected_event_title = None
        if selected_event_id:
            cursor.execute("SELECT title FROM events WHERE id = %s AND created_by = %s", (selected_event_id, session['user_id']))
            ev = cursor.fetchone()
            selected_event_title = ev['title'] if ev else None

        return render_template(
            'view_registrations.html',
            registrations=registrations,
            branches=sorted(branches),
            years=sorted(years),
            domains=sorted(domains),
            selected_branch=request.args.get('branch', ''),
            selected_year=request.args.get('year', ''),
            selected_domain=request.args.get('domain', ''),
            selected_event_id=selected_event_id or '',
            selected_event_title=selected_event_title,
            events_list=events_list,
            user=user
        )

    except Exception as e:
        print(f"Error in view_registrations: {str(e)}")
        flash("An error occurred while loading registrations", "danger")
        return redirect(url_for('club.club_dashboard'))
    finally:
        cursor.close()


# ================================
# DOWNLOAD REGISTRATIONS (CSV)
# ================================
@events_bp.route('/download-registrations')
def download_registrations():
    if 'user_id' not in session or session.get('role') != 'club':
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)

    selected_event_id = request.args.get('event_id')
    event_filter_clause = ""
    params = [session['user_id']]
    if selected_event_id:
        event_filter_clause = " AND r.event_id = %s"
        params.append(selected_event_id)

    cursor.execute("""
        SELECT
            e.title AS event_title,
            r.team_name,
            r.team_lead_name,
            r.team_lead_email,
            r.team_lead_branch,
            r.team_lead_year,
            (COUNT(tm.id) + 1) AS team_size,
            COALESCE(
                GROUP_CONCAT(
                    CONCAT(tm.member_name, ' (', tm.member_email, ')')
                    SEPARATOR ', '
                ), '') AS team_members
        FROM event_registrations r
        JOIN events e ON e.id = r.event_id
        LEFT JOIN event_team_members tm ON tm.registration_id = r.id
        WHERE e.created_by = %s""" + event_filter_clause + """
        GROUP BY r.id
        ORDER BY r.id DESC
    """, tuple(params))

    rows = cursor.fetchall()
    cursor.close()

    def generate():
        writer = csv.writer(Echo())
        yield writer.writerow([
            "Event", "Team Name", "Team Lead", "Lead Email",
            "Branch", "Year", "Team Size", "Team Members"
        ])
        for row in rows:
            yield writer.writerow([
                row['event_title'],
                row['team_name'],
                row['team_lead_name'],
                row['team_lead_email'],
                row['team_lead_branch'],
                row['team_lead_year'],
                row['team_size'],
                row['team_members']
            ])

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=registrations.csv"}
    )


class Echo:
    def write(self, value):
        return value
