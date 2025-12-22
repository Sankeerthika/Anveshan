
from flask import Blueprint, request, redirect, url_for, flash, session, render_template, Response
from db import db
import os
import csv
from datetime import datetime

events_bp = Blueprint('events', __name__)
from routes.club import club_bp

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
# STUDENT REGISTRATION
# ================================
@events_bp.route('/register/<int:event_id>')
def open_registration_form(event_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    return render_template('hackathon_registration.html', event_id=event_id)


@events_bp.route('/submit-registration', methods=['POST'])
def submit_registration():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    cursor = db.cursor()

    event_id = request.form.get('event_id')
    team_name = request.form.get('team_name')
    domain = request.form.get('domain')
    project_title = request.form.get('project_title')

    lead_name = request.form.get('lead_name')
    lead_email = request.form.get('lead_email')
    lead_phone = request.form.get('lead_phone')
    lead_year = request.form.get('lead_year')
    lead_branch = request.form.get('lead_branch')

    if not all([team_name, project_title, lead_name, lead_email, lead_phone]):
        flash("Please fill all required fields", "danger")
        return redirect(url_for('events.open_registration_form', event_id=event_id))

    payment_file = request.files.get('payment_screenshot')
    filename = None

    if payment_file and payment_file.filename:
        upload_folder = "static/uploads"
        os.makedirs(upload_folder, exist_ok=True)
        filename = payment_file.filename
        payment_file.save(os.path.join(upload_folder, filename))

    # Insert registration
    cursor.execute("""
        INSERT INTO event_registrations
        (event_id, team_name, domain, project_title,
         team_lead_name, team_lead_email, team_lead_phone,
         team_lead_year, team_lead_branch, payment_screenshot)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        event_id, team_name, domain, project_title,
        lead_name, lead_email, lead_phone,
        lead_year, lead_branch, filename
    ))

    registration_id = cursor.lastrowid

    # Insert team members
    member_names = request.form.getlist('member_name[]')
    member_emails = request.form.getlist('member_email[]')
    member_years = request.form.getlist('member_year[]')
    member_branches = request.form.getlist('member_branch[]')

    for i in range(len(member_names)):
        if member_names[i].strip():
            cursor.execute("""
                INSERT INTO event_team_members
                (registration_id, member_name, member_email, year, branch)
                VALUES (%s,%s,%s,%s,%s)
            """, (
                registration_id,
                member_names[i],
                member_emails[i],
                member_years[i],
                member_branches[i]
            ))

    db.commit()
    cursor.close()

    flash("🎉 Registration successful!", "success")
    return redirect(url_for('student_dashboard'))


# ================================
# QUESTIONS / DOUBTS (STUDENTS)
# ================================
@events_bp.route('/submit-question', methods=['POST'])
def submit_question():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    question = request.form.get('question')
    event_id = request.form.get('event_id')

    if not question or not event_id:
        flash('Please enter your question.', 'danger')
        return redirect(url_for('student_dashboard'))

    # get student email
    cursor = db.cursor()
    cursor.execute("SELECT email FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    student_email = user[0] if user else None

    cursor.execute(
        "INSERT INTO event_questions (event_id, student_email, question) VALUES (%s,%s,%s)",
        (event_id, student_email, question)
    )
    db.commit()
    cursor.close()

    flash('Your question has been submitted.', 'success')
    return redirect(url_for('student_dashboard'))


@events_bp.route('/edit-question/<int:qid>', methods=['GET', 'POST'])
def edit_question(qid):
    if 'user_id' not in session or session.get('role') != 'student':
        flash('Unauthorized', 'danger')
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)

    # ensure this student owns the question
    cursor.execute("SELECT email FROM users WHERE id = %s", (session['user_id'],))
    u = cursor.fetchone()
    student_email = u['email'] if u else None

    cursor.execute('SELECT * FROM event_questions WHERE id = %s', (qid,))
    q = cursor.fetchone()
    if not q or q.get('student_email') != student_email:
        cursor.close()
        flash('You are not allowed to edit this question.', 'danger')
        return redirect(url_for('student_dashboard'))

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
        return redirect(url_for('student_dashboard'))

    cursor.close()
    return render_template('edit_question.html', q=q)


# ================================
# CLUB: View and answer questions
# ================================
@club_bp.route('/club-questions')
def club_questions():
    if 'user_id' not in session or session.get('role') != 'club':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)

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
    return render_template('club_questions.html', questions=questions)


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
            return redirect(url_for('events.answer_question', qid=qid))

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

    if request.method == 'POST':
        title = request.form.get('title')
        deadline = request.form.get('deadline')
        club_name = request.form.get('club_name')
        organising_department = request.form.get('organising_department')
        domains = ",".join(request.form.getlist('domains[]'))

        cursor = db.cursor(dictionary=True)

        # 🔍 CHECK DUPLICATE EVENT
        cursor.execute("""
            SELECT id FROM events
            WHERE title = %s
              AND created_by = %s
              AND deadline = %s
        """, (title, session['user_id'], deadline))

        existing_event = cursor.fetchone()

        if existing_event:
            flash("⚠️ This hackathon already exists!", "warning")
            cursor.close()
            return redirect(url_for('club.club_dashboard'))

        # ✅ INSERT ONLY IF NOT EXISTS
        cursor.execute("""
            INSERT INTO events
            (title, domains, deadline, club_name, organising_department, created_by)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            title, domains, deadline,
            club_name, organising_department,
            session['user_id']
        ))

        db.commit()
        cursor.close()

        flash("✅ Hackathon created successfully!", "success")
        return redirect(url_for('club.club_dashboard'))

    return render_template('create_event.html')


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
        # Base query to get all registrations for events created by this club
        query = """
            SELECT 
                r.*,
                e.title AS event_title
            FROM event_registrations r
            JOIN events e ON e.id = r.event_id
            WHERE e.created_by = %s
            ORDER BY r.created_at DESC
        """
        
        cursor.execute(query, (session['user_id'],))
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
        cursor.execute("""
            SELECT DISTINCT team_lead_branch as branch 
            FROM event_registrations r
            JOIN events e ON e.id = r.event_id
            WHERE e.created_by = %s AND team_lead_branch IS NOT NULL
        """, (session['user_id'],))
        branches = [row['branch'] for row in cursor.fetchall()]

        cursor.execute("""
            SELECT DISTINCT team_lead_year as year 
            FROM event_registrations r
            JOIN events e ON e.id = r.event_id
            WHERE e.created_by = %s AND team_lead_year IS NOT NULL
        """, (session['user_id'],))
        years = [row['year'] for row in cursor.fetchall()]

        cursor.execute("""
            SELECT DISTINCT domain 
            FROM event_registrations 
            WHERE domain IS NOT NULL
        """)
        domains = [row['domain'] for row in cursor.fetchall()]

        return render_template(
            'view_registrations.html',
            registrations=registrations,
            branches=sorted(branches),
            years=sorted(years),
            domains=sorted(domains),
            selected_branch=request.args.get('branch', ''),
            selected_year=request.args.get('year', ''),
            selected_domain=request.args.get('domain', '')
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
        WHERE e.created_by = %s
        GROUP BY r.id
        ORDER BY r.id DESC
    """, (session['user_id'],))

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
