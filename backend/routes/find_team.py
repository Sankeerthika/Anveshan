from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, jsonify
import mysql.connector
from backend.db import db

find_team_bp = Blueprint('find_team', __name__)

try:
    c = db.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS team_chat_messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            team_request_id INT NOT NULL,
            user_id INT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_request_id) REFERENCES team_requests(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    db.commit()
    c.close()
except Exception:
    pass

# =====================================================
# FIND TEAM / CREATE TEAM REQUEST
# =====================================================
@find_team_bp.route('/find-team', methods=['GET', 'POST'])
def find_team():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('auth.login'))

    user_email = session.get('user_email')
    cursor = db.cursor(dictionary=True)

    # Fetch user for sidebar
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()

    # -------------------------
    # CREATE / UPDATE TEAM REQUEST
    # -------------------------
    if request.method == 'POST':
        name = request.form['name']
        event_id = request.form['event_id']
        domain = request.form['domain']
        required_skills = request.form.get('required_skills', '')
        branch = request.form['branch']
        year = request.form['year']
        required_size = int(request.form['required_size'])

        cursor.execute("""
            SELECT id FROM team_requests
            WHERE email=%s AND event_id=%s
        """, (user_email, event_id))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE team_requests
                SET name=%s, domain=%s, required_skills=%s, branch=%s, year=%s, required_size=%s
                WHERE email=%s AND event_id=%s
            """, (name, domain, required_skills, branch, year, required_size, user_email, event_id))
        else:
            cursor.execute("""
                INSERT INTO team_requests
                (name, email, event_id, domain, required_skills, branch, year, required_size)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (name, user_email, event_id, domain, required_skills, branch, year, required_size))

        db.commit()
        cursor.close()
        return redirect(url_for('find_team.find_team'))

    # -------------------------
    # FETCH DATA
    # -------------------------
    cursor.execute("SELECT id, title FROM events")
    events = cursor.fetchall()

    # Build like-minded filter based on student's skills/interests and profile
    from backend.utils.skills import expand_skills
    skills_str = str(user.get('skills') or '')
    interests_str = str(user.get('interests') or '')
    initial_terms = [t.strip().lower() for t in (skills_str.split(',') + interests_str.split(',')) if t.strip()]
    raw_terms = expand_skills(initial_terms)
    
    # Year normalization similar to student dashboard
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
    user_year_norm = _norm_year(user_year_raw).lower() if user_year_raw else ""
    user_branch = (user.get('branch') or "").strip()

    base_sql = """
        SELECT tr.*,
               e.title AS event_title,
               u.id AS owner_id,
               u.profile_photo AS owner_photo
        FROM team_requests tr
        JOIN events e ON tr.event_id = e.id
        LEFT JOIN users u ON LOWER(u.email) = LOWER(tr.email)
        WHERE tr.email != %s AND tr.required_size > 0
    """
    params = [user_email]

    like_parts = []
    for term in raw_terms:
        like_parts.append("LOWER(tr.domain) LIKE %s")
        params.append(f"%{term}%")

    skill_parts = []
    for term in raw_terms:
        skill_parts.append("LOWER(tr.required_skills) LIKE %s")
        params.append(f"%{term}%")

    profile_match = []
    if user_branch and user_year_norm:
        profile_match.append("(tr.branch = %s AND LOWER(tr.year) = %s)")
        params.extend([user_branch, user_year_norm])
    elif user_branch:
        profile_match.append("(tr.branch = %s)")
        params.append(user_branch)
    elif user_year_norm:
        profile_match.append("(LOWER(tr.year) = %s)")
        params.append(user_year_norm)

    combined_filters = []
    if like_parts:
        combined_filters.append("(" + " OR ".join(like_parts) + ")")
    if profile_match:
        combined_filters.append("(" + " OR ".join(profile_match) + ")")
    if skill_parts:
        combined_filters.append("(tr.required_skills IS NULL OR tr.required_skills = '' OR (" + " OR ".join(skill_parts) + "))")

    if combined_filters:
        base_sql += " AND (" + " OR ".join(combined_filters) + ")"
    else:
        # No profile signals; avoid showing all requests
        base_sql += " AND 1=0"
        flash("Fill your skills/interests or profile (branch/year) to view like-minded team requests.", "warning")

    base_sql += " ORDER BY tr.id DESC"
    cursor.execute(base_sql, tuple(params))
    requests = cursor.fetchall()

    cursor.close()
    return render_template('find_team.html', events=events, requests=requests, user=user)


# =====================================================
# JOIN TEAM REQUEST
# =====================================================
@find_team_bp.route('/join-team/<int:request_id>', methods=['GET', 'POST'])
def join_team(request_id):
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('auth.login'))

    user_email = session.get('user_email')
    cursor = db.cursor(dictionary=True)

    # Fetch user for sidebar
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()

    cursor.execute("""
        SELECT tr.*,
               e.title AS event_title,
               u.id AS owner_id
        FROM team_requests tr
        JOIN events e ON tr.event_id = e.id
        LEFT JOIN users u ON LOWER(u.email) = LOWER(tr.email)
        WHERE tr.id=%s
    """, (request_id,))
    team_request = cursor.fetchone()

    if team_request and team_request.get('required_size', 0) <= 0:
        cursor.close()
        return redirect(url_for('find_team.find_team'))

    # Prevent joining own team
    if not team_request or team_request['email'] == user_email:
        cursor.close()
        return redirect(url_for('find_team.find_team'))

    if request.method == 'POST':
        name = request.form['name']
        branch = request.form['branch']
        year = request.form['year']
        phone = (request.form.get('phone') or '').strip()[:100]

        # 🚫 PREVENT DUPLICATE JOIN REQUEST
        cursor.execute("""
            SELECT id FROM join_requests
            WHERE team_request_id=%s AND email=%s
        """, (request_id, user_email))

        if cursor.fetchone():
            flash("You have already requested to join this team.", "info")
            cursor.close()
            return redirect(url_for('find_team.find_team'))

        cursor.execute("""
            INSERT INTO join_requests
            (team_request_id, name, email, branch, year, phone, status)
            VALUES (%s,%s,%s,%s,%s,%s,'pending')
        """, (request_id, name, user_email, branch, year, phone))

        db.commit()
        flash("Join request sent to the team owner.", "success")
        cursor.close()
        return redirect(url_for('find_team.find_team'))

    cursor.close()
    return render_template('join_team.html', team_request=team_request, user=user)


# =====================================================
# VIEW JOIN REQUESTS FOR YOUR TEAM (TEAM OWNER)
# =====================================================
@find_team_bp.route('/my-team-requests')
def my_team_requests():
    if session.get('role') != 'student':
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)

    # Fetch user for sidebar
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()

    cursor.execute("""
        SELECT 
            jr.id,
            jr.name,
            jr.email,
            jr.phone,
            jr.branch,
            jr.year,
            jr.status,
            tr.name AS team_owner,
            tr.id AS team_request_id,
            e.title AS event_title
        FROM join_requests jr
        JOIN team_requests tr ON jr.team_request_id = tr.id
        JOIN events e ON tr.event_id = e.id
        WHERE LOWER(tr.email) = LOWER(%s)
        ORDER BY jr.id DESC
    """, (session['user_email'],))

    join_requests = cursor.fetchall()
    cursor.close()

    return render_template(
        'my_team_requests.html',
        join_requests=join_requests,
        user=user
    )

@find_team_bp.route('/team-chats')
def team_chats():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('auth.login'))
    user_email = session.get('user_email')
    cursor = db.cursor(dictionary=True)
    # Rooms owned by user
    cursor.execute("""
        SELECT tr.id, tr.name, e.title AS event_title
        FROM team_requests tr
        JOIN events e ON tr.event_id = e.id
        WHERE LOWER(tr.email) = LOWER(%s)
        ORDER BY tr.id DESC
    """, (user_email,))
    owned = cursor.fetchall() or []
    # Rooms where user is accepted member
    cursor.execute("""
        SELECT DISTINCT tr.id, tr.name, e.title AS event_title
        FROM join_requests jr
        JOIN team_requests tr ON jr.team_request_id = tr.id
        JOIN events e ON tr.event_id = e.id
        WHERE jr.email = %s AND jr.status='accepted'
        ORDER BY tr.id DESC
    """, (user_email,))
    member = cursor.fetchall() or []
    # Merge by id
    rooms_map = {}
    for r in owned + member:
        rooms_map[r['id']] = r
    rooms = []
    # For each room, compute members and is_over flag
    for room_id, room in rooms_map.items():
        # is_over
        cursor.execute("""
            SELECT CASE
                     WHEN e.end_time IS NOT NULL THEN (e.end_time < NOW())
                     WHEN e.deadline IS NOT NULL THEN (e.deadline < CURDATE())
                     ELSE 0
                   END AS is_over
            FROM events e
            JOIN team_requests tr2 ON tr2.event_id = e.id
            WHERE tr2.id=%s
        """, (room_id,))
        over_row = cursor.fetchone() or {}
        is_over = bool(over_row.get('is_over'))
        # owner
        cursor.execute("""
            SELECT u.name, u.email
            FROM users u
            JOIN team_requests tr ON LOWER(u.email)=LOWER(tr.email)
            WHERE tr.id=%s
        """, (room_id,))
        owner_row = cursor.fetchone()
        owner_name = (owner_row and owner_row.get('name')) or None
        owner_email = (owner_row and owner_row.get('email')) or None
        if not owner_name:
            cursor.execute("SELECT name, email FROM team_requests WHERE id=%s", (room_id,))
            tr_fallback = cursor.fetchone()
            owner_name = tr_fallback and tr_fallback.get('name')
            owner_email = tr_fallback and tr_fallback.get('email')
        # accepted members
        cursor.execute("""
            SELECT COALESCE(u.name, jr.name) AS name, jr.email
            FROM join_requests jr
            LEFT JOIN users u ON LOWER(u.email)=LOWER(jr.email)
            WHERE jr.team_request_id=%s AND jr.status='accepted'
            ORDER BY name ASC
        """, (room_id,))
        members = cursor.fetchall() or []
        rooms.append({
            'id': room_id,
            'event_title': room.get('event_title'),
            'team_name': f"{room.get('name')}'s Team" if room.get('name') else 'Team',
            'owner_name': owner_name,
            'owner_email': owner_email,
            'members': members,
            'is_over': is_over
        })
    cursor.close()
    # Sort with active first
    rooms.sort(key=lambda r: (r['is_over'], -r['id']))
    return render_template('team_chats.html', rooms=rooms)

@find_team_bp.route('/team-chat/<int:team_request_id>')
def team_chat(team_request_id):
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('auth.login'))
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT tr.*, e.deadline, e.end_time
        FROM team_requests tr
        JOIN events e ON tr.event_id = e.id
        WHERE tr.id=%s
    """, (team_request_id,))
    tr = cursor.fetchone()
    if not tr:
        cursor.close()
        return redirect(url_for('find_team.find_team'))
    is_owner = str(tr.get('email') or '').strip().lower() == str(session.get('user_email') or '').strip().lower()
    if not is_owner:
        cursor.execute("""
            SELECT id FROM join_requests
            WHERE team_request_id=%s AND email=%s AND status='accepted'
        """, (team_request_id, session.get('user_email')))
        mem = cursor.fetchone()
        if not mem:
            cursor.close()
            return redirect(url_for('find_team.find_team'))
    cursor.execute("SELECT NOW()")
    now_row = cursor.fetchone()
    cursor.execute("""
        SELECT CASE
                 WHEN e.end_time IS NOT NULL THEN (e.end_time < NOW())
                 WHEN e.deadline IS NOT NULL THEN (e.deadline < CURDATE())
                 ELSE 0
               END AS is_over
        FROM events e
        JOIN team_requests tr2 ON tr2.event_id = e.id
        WHERE tr2.id=%s
    """, (team_request_id,))
    over_row = cursor.fetchone()
    if over_row and (over_row.get('is_over') == 1 or over_row.get('is_over') is True):
        try:
            cursor2 = db.cursor()
            cursor2.execute("DELETE FROM team_chat_messages WHERE team_request_id=%s", (team_request_id,))
            db.commit()
            cursor2.close()
        except Exception:
            db.rollback()
        cursor.close()
        flash("This team's chat has ended.", "info")
        return redirect(url_for('find_team.find_team'))
    cursor.execute("""
        SELECT m.id, m.message, m.created_at, u.name AS user_name, u.profile_photo
        FROM team_chat_messages m
        JOIN users u ON u.id = m.user_id
        WHERE m.team_request_id=%s
        ORDER BY m.created_at ASC, m.id ASC
    """, (team_request_id,))
    messages = cursor.fetchall()
    cursor.close()
    return render_template('team_chat.html', team_request=tr, messages=messages)

@find_team_bp.route('/team-chat/<int:team_request_id>/send', methods=['POST'])
def team_chat_send(team_request_id):
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('auth.login'))
    msg = (request.form.get('message') or '').strip()
    if not msg:
        return redirect(url_for('find_team.team_chat', team_request_id=team_request_id))
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT tr.*, e.deadline, e.end_time
        FROM team_requests tr
        JOIN events e ON tr.event_id = e.id
        WHERE tr.id=%s
    """, (team_request_id,))
    tr = cursor.fetchone()
    if not tr:
        cursor.close()
        return redirect(url_for('find_team.find_team'))
    is_owner = str(tr.get('email') or '').strip().lower() == str(session.get('user_email') or '').strip().lower()
    if not is_owner:
        cursor.execute("""
            SELECT id FROM join_requests
            WHERE team_request_id=%s AND email=%s AND status='accepted'
        """, (team_request_id, session.get('user_email')))
        mem = cursor.fetchone()
        if not mem:
            cursor.close()
            return redirect(url_for('find_team.find_team'))
    cursor.execute("""
        SELECT CASE
                 WHEN e.end_time IS NOT NULL THEN (e.end_time < NOW())
                 WHEN e.deadline IS NOT NULL THEN (e.deadline < CURDATE())
                 ELSE 0
               END AS is_over
        FROM events e
        JOIN team_requests tr2 ON tr2.event_id = e.id
        WHERE tr2.id=%s
    """, (team_request_id,))
    over_row = cursor.fetchone()
    if over_row and (over_row.get('is_over') == 1 or over_row.get('is_over') is True):
        cursor.close()
        flash("This team's chat has ended.", "info")
        return redirect(url_for('find_team.find_team'))
    try:
        cursor2 = db.cursor()
        cursor2.execute("""
            INSERT INTO team_chat_messages (team_request_id, user_id, message)
            VALUES (%s,%s,%s)
        """, (team_request_id, session['user_id'], msg))
        db.commit()
        cursor2.close()
    except Exception:
        db.rollback()
    cursor.close()
    return redirect(url_for('find_team.team_chat', team_request_id=team_request_id))

@find_team_bp.route('/team-chat/<int:team_request_id>/messages')
def team_chat_messages(team_request_id):
    try:
        if 'user_id' not in session or session.get('role') != 'student':
            return jsonify([])
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT tr.email FROM team_requests tr WHERE tr.id=%s
        """, (team_request_id,))
        tr = cursor.fetchone()
        if not tr:
            cursor.close()
            return jsonify([])
        is_owner = str(tr.get('email') or '').strip().lower() == str(session.get('user_email') or '').strip().lower()
        if not is_owner:
            cursor.execute("""
                SELECT id FROM join_requests
                WHERE team_request_id=%s AND email=%s AND status='accepted'
            """, (team_request_id, session.get('user_email')))
            mem = cursor.fetchone()
            if not mem:
                cursor.close()
                return jsonify([])
        cursor.execute("""
            SELECT m.id, m.message, m.created_at, u.name AS user_name
            FROM team_chat_messages m
            JOIN users u ON u.id = m.user_id
            WHERE m.team_request_id=%s
            ORDER BY m.created_at ASC, m.id ASC
        """, (team_request_id,))
        messages = cursor.fetchall()
        cursor.close()
        return jsonify(messages)
    except mysql.connector.Error as err:
        # On transient connection loss, respond with empty array so UI can retry
        if getattr(err, "errno", None) in (2006, 2013):
            try:
                cursor.close()
            except Exception:
                pass
            return jsonify([])
        raise

# =====================================================
# ACCEPT / REJECT JOIN REQUEST
# =====================================================
@find_team_bp.route('/handle-join-request/<int:request_id>', methods=['POST'])
def handle_join_request(request_id):
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('auth.login'))

    action = request.form.get('action')
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            jr.status,
            tr.required_size,
            tr.id AS team_id
        FROM join_requests jr
        JOIN team_requests tr ON jr.team_request_id = tr.id
        WHERE jr.id=%s AND tr.email=%s
    """, (request_id, session['user_email']))

    row = cursor.fetchone()

    # 🚫 If already accepted/rejected
    if not row or row['status'] != 'pending':
        cursor.close()
        return redirect(url_for('find_team.my_team_requests'))

    if action == 'accept' and row['required_size'] > 0:
        cursor.execute("""
            UPDATE join_requests
            SET status='accepted'
            WHERE id=%s
        """, (request_id,))

        cursor.execute("""
            UPDATE team_requests
            SET required_size = required_size - 1
            WHERE id=%s
        """, (row['team_id'],))

    elif action == 'reject':
        cursor.execute("""
            UPDATE join_requests
            SET status='rejected'
            WHERE id=%s
        """, (request_id,))

    db.commit()
    db.commit()

    # Log resulting status for debugging
    cursor.execute("SELECT status FROM join_requests WHERE id=%s", (request_id,))
    after = cursor.fetchone()
    current_app.logger.info("join_request %s status after update: %s", request_id, after.get('status') if after else 'MISSING')

    cursor.close()
    return redirect(url_for('find_team.my_team_requests'))


# =====================================================
# VIEW STATUS OF YOUR JOIN REQUESTS (STUDENT)
# =====================================================
@find_team_bp.route('/my-join-requests')
def my_join_requests():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)

    # Fetch user for sidebar
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()

    cursor.execute("""
        SELECT 
            jr.name,
            jr.branch,
            jr.year,
            jr.phone,
            jr.status,
            tr.name AS team_owner,
            tr.id AS team_request_id,
            e.title AS event_title
        FROM join_requests jr
        JOIN team_requests tr ON jr.team_request_id = tr.id
        JOIN events e ON tr.event_id = e.id
        WHERE jr.email = %s
        ORDER BY jr.id DESC
    """, (session['user_email'],))

    join_requests = cursor.fetchall()
    cursor.close()

    return render_template(
        'my_join_requests.html',
        join_requests=join_requests,
        user=user
    )
