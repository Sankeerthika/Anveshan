from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import db
import os
from werkzeug.utils import secure_filename
import re
from utils.skills import expand_skills, all_known_terms

collaboration_bp = Blueprint('collaboration', __name__)

@collaboration_bp.route('/community')
def community():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)
    
    # Fetch logged-in user for sidebar
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()

    # Determine if we should filter profiles
    # Logic: If user has posted projects, filter people by those projects' requirements.
    # Otherwise, show all.
    
    show_all = request.args.get('show_all') == 'true'

    # 1. Get user's projects to find keywords
    cursor.execute("SELECT tech_stack, domain FROM personal_projects WHERE user_id = %s", (session['user_id'],))
    my_projects = cursor.fetchall()
    
    filter_keywords = []
    if my_projects and not show_all:
        for p in my_projects:
            if p['tech_stack']:
                filter_keywords.extend(expand_skills(p['tech_stack'].split(',')))
            if p['domain']:
                filter_keywords.append(p['domain'])
        # Remove duplicates
        filter_keywords = list(set(filter_keywords))

    # For faculty, also use their own skills/interests as matching signals
    if not show_all:
        if user and user.get('role') == 'faculty':
            skills_terms = expand_skills((user.get('skills') or '').split(','))
            interest_terms = expand_skills((user.get('interests') or '').split(','))
            filter_keywords.extend(skills_terms + interest_terms)
            filter_keywords = list(set(filter_keywords))

    # 2. Fetch profiles based on filter
    if filter_keywords:
        query_parts = []
        params = []
        
        # Always exclude self
        base_query = """
            SELECT id, name, role, bio, skills, interests, profile_photo, github_url, linkedin_url, portfolio_url, medium_url 
            FROM users 
            WHERE role IN ('student', 'faculty') AND id != %s
        """
        params.append(session['user_id'])
        
        keyword_conditions = []
        for k in filter_keywords:
            keyword_conditions.append("skills LIKE %s OR interests LIKE %s")
            params.extend([f"%{k}%", f"%{k}%"])
            
        if keyword_conditions:
            base_query += " AND (" + " OR ".join(keyword_conditions) + ")"
            
        base_query += " ORDER BY name ASC"
        
        cursor.execute(base_query, tuple(params))
        profiles = cursor.fetchall()
    else:
        # No projects or no keywords or show_all=true -> Show all (except self)
        cursor.execute("""
            SELECT id, name, role, bio, skills, interests, profile_photo, github_url, linkedin_url, portfolio_url, medium_url 
            FROM users 
            WHERE role IN ('student', 'faculty') AND id != %s
            ORDER BY name ASC
        """, (session['user_id'],))
        profiles = cursor.fetchall()

    # Fetch all personal projects
    cursor.execute("""
        SELECT p.*, u.name as creator_name, u.profile_photo as creator_photo
        FROM personal_projects p
        JOIN users u ON p.user_id = u.id
        ORDER BY p.created_at DESC
    """)
    projects = cursor.fetchall()

    cursor.close()

    return render_template('community.html', user=user, profiles=profiles, projects=projects, is_filtered=bool(filter_keywords))

# ===============================
# FACULTY PROFILE
# ===============================
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'uploads', 'profile_pics')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@collaboration_bp.route('/faculty/profile', methods=['GET', 'POST'])
def faculty_profile():
    if 'user_id' not in session or session.get('role') != 'faculty':
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

        profile_photo = None
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and file.filename != '' and _allowed_file(file.filename):
                filename = secure_filename(f"user_{session['user_id']}_{file.filename}")
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                profile_photo = filename

        try:
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
            print(f"Error updating faculty profile: {e}")
            flash("Error updating profile.", "danger")
        
        return redirect(url_for('collaboration.faculty_profile'))

    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()

    return render_template('faculty_profile.html', user=user)

@collaboration_bp.route('/community/project/create', methods=['GET', 'POST'])
def create_project():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()

    if request.method == 'POST':
        title = request.form.get('title')
        domain = request.form.get('domain')
        description = request.form.get('description')
        tech_stack = request.form.get('tech_stack')
        looking_for = request.form.get('looking_for')

        try:
            cursor.execute("""
                INSERT INTO personal_projects (user_id, title, domain, description, tech_stack, looking_for)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (session['user_id'], title, domain, description, tech_stack, looking_for))
            db.commit()
            flash("Project posted successfully!", "success")
            return redirect(url_for('collaboration.community'))
        except Exception as e:
            db.rollback()
            print(f"Error creating project: {e}")
            flash("Error creating project.", "danger")
        finally:
            cursor.close()

    cursor.close()
    return render_template('create_project.html', user=user)

@collaboration_bp.route('/community/project/<int:project_id>')
def project_details(project_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)
    
    # Fetch user for sidebar
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()

    # Fetch project details
    cursor.execute("""
        SELECT p.*, u.name as creator_name, u.email as creator_email, u.profile_photo as creator_photo, u.role as creator_role
        FROM personal_projects p
        JOIN users u ON p.user_id = u.id
        WHERE p.id = %s
    """, (project_id,))
    project = cursor.fetchone()
    
    # Fetch comments
    cursor.execute("""
        SELECT pc.*, u.name as user_name, u.profile_photo as user_photo
        FROM project_comments pc
        JOIN users u ON pc.user_id = u.id
        WHERE pc.project_id = %s
        ORDER BY pc.created_at DESC
    """, (project_id,))
    comments = cursor.fetchall()
    
    # Fetch join requests if owner
    requests = []
    if session['user_id'] == project['user_id']:
        cursor.execute("""
            SELECT pr.*, u.name as user_name, u.role as user_role, u.profile_photo as user_photo, u.skills as user_skills
            FROM project_requests pr
            JOIN users u ON pr.user_id = u.id
            WHERE pr.project_id = %s AND pr.status = 'pending'
            ORDER BY pr.created_at DESC
        """, (project_id,))
        requests = cursor.fetchall()

    cursor.close()

    if not project:
        flash("Project not found", "danger")
        return redirect(url_for('collaboration.community'))

    # Smart Matching for Project Owner
    recommended_users = []
    if session['user_id'] == project['user_id']:
        # Keywords from tech_stack and domain
        keywords = []
        if project['tech_stack']:
            keywords.extend(expand_skills(project['tech_stack'].split(',')))
        if project['domain']:
            keywords.append(project['domain'])
        
        if keywords:
            # Build dynamic SQL query
            query_parts = []
            params = [session['user_id']] # Exclude self
            
            for k in keywords:
                query_parts.append("skills LIKE %s OR interests LIKE %s")
                params.extend([f"%{k}%", f"%{k}%"])
            
            where_clause = " OR ".join(query_parts)
            
            sql = f"""
                SELECT id, name, role, skills, interests, profile_photo 
                FROM users 
                WHERE id != %s AND role = 'student' AND ({where_clause})
                LIMIT 6
            """
            
            cursor = db.cursor(dictionary=True) 
            cursor.execute(sql, tuple(params))
            recommended_users = cursor.fetchall()
            base_terms = []
            if project.get('tech_stack'):
                base_terms.extend([t.strip().lower() for t in str(project['tech_stack']).split(',') if t.strip()])
            if project.get('domain'):
                base_terms.append(str(project['domain']).strip().lower())
            split_terms = []
            for t in base_terms:
                parts = [p.strip() for p in re.split(r'[/&]|\band\b', t) if p.strip()]
                split_terms.extend(parts if parts else [t])
            base_terms = split_terms
            for u in recommended_users:
                user_terms = []
                if u.get('skills'):
                    base_ut = [s.strip().lower() for s in str(u['skills']).split(',') if s.strip()]
                    user_terms.extend(_expand_split(base_ut))
                if u.get('interests'):
                    base_ui = [s.strip().lower() for s in str(u['interests']).split(',') if s.strip()]
                    user_terms.extend(_expand_split(base_ui))
                user_terms_exp = set(expand_skills(user_terms))
                match_count = 0
                total = len(base_terms)
                for bt in base_terms:
                    exp_bt = set(expand_skills([bt]))
                    if exp_bt & user_terms_exp:
                        match_count += 1
                u['match_percent'] = int(round(100 * match_count / total)) if total > 0 else 0
            cursor.close()
    else:
        # Check if current user has already requested to join
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT status FROM project_requests WHERE project_id = %s AND user_id = %s", (project_id, session['user_id']))
        req = cursor.fetchone()
        project['request_status'] = req['status'] if req else None
        cursor.close()

    return render_template('project_details.html', user=user, project=project, recommended_users=recommended_users, comments=comments, requests=requests)

@collaboration_bp.route('/community/project/<int:project_id>/invite/<int:user_id>', methods=['POST'])
def invite_project_user(project_id, user_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT user_id FROM personal_projects WHERE id = %s", (project_id,))
    proj = cur.fetchone()
    if not proj or proj['user_id'] != session['user_id']:
        cur.close()
        flash("Unauthorized.", "danger")
        return redirect(url_for('collaboration.project_details', project_id=project_id))
    cur.close()
    cur2 = db.cursor()
    try:
        cur2.execute("SELECT 1 FROM project_requests WHERE project_id = %s AND user_id = %s", (project_id, user_id))
        if cur2.fetchone():
            flash("Already requested or invited.", "warning")
        else:
            cur2.execute("INSERT INTO project_requests (project_id, user_id, message) VALUES (%s, %s, %s)", (project_id, user_id, "Invitation from owner"))
            db.commit()
            flash("Invitation sent.", "success")
    except Exception as e:
        db.rollback()
        flash("Error sending invitation.", "danger")
    finally:
        cur2.close()
    return redirect(url_for('collaboration.project_details', project_id=project_id))

@collaboration_bp.route('/community/project/edit/<int:project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)
    
    # Fetch project and verify ownership
    cursor.execute("SELECT * FROM personal_projects WHERE id = %s", (project_id,))
    project = cursor.fetchone()

    if not project or project['user_id'] != session['user_id']:
        cursor.close()
        flash("Unauthorized or Project not found", "danger")
        return redirect(url_for('collaboration.community'))

    # Fetch user for sidebar
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()

    if request.method == 'POST':
        title = request.form.get('title')
        domain = request.form.get('domain')
        description = request.form.get('description')
        tech_stack = request.form.get('tech_stack')
        looking_for = request.form.get('looking_for')

        try:
            cursor.execute("""
                UPDATE personal_projects 
                SET title=%s, domain=%s, description=%s, tech_stack=%s, looking_for=%s
                WHERE id=%s
            """, (title, domain, description, tech_stack, looking_for, project_id))
            db.commit()
            flash("Project updated successfully!", "success")
            return redirect(url_for('collaboration.project_details', project_id=project_id))
        except Exception as e:
            db.rollback()
            print(f"Error updating project: {e}")
            flash("Error updating project.", "danger")
        finally:
            cursor.close()
    
    cursor.close()
    return render_template('create_project.html', user=user, project=project, is_edit=True)

@collaboration_bp.route('/community/profile/<int:profile_id>')
def view_profile(profile_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)
    
    # Fetch logged-in user for sidebar
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()

    # Fetch target profile
    cursor.execute("""
        SELECT id, name, role, email, bio, skills, interests, branch, year, section, 
               profile_photo, github_url, linkedin_url, portfolio_url, medium_url
        FROM users 
        WHERE id = %s
    """, (profile_id,))
    profile = cursor.fetchone()

    # Fetch projects by this user
    cursor.execute("""
        SELECT * FROM personal_projects WHERE user_id = %s ORDER BY created_at DESC
    """, (profile_id,))
    projects = cursor.fetchall()

    cursor.close()

    if not profile:
        flash("User not found", "danger")
        return redirect(url_for('collaboration.community'))

    return render_template('public_profile.html', user=user, profile=profile, projects=projects)

@collaboration_bp.route('/community/project/<int:project_id>/join', methods=['POST'])
def join_project(project_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    message = request.form.get('message')
    
    cursor = db.cursor()
    try:
        # Check if already requested
        cursor.execute("SELECT 1 FROM project_requests WHERE project_id = %s AND user_id = %s", (project_id, session['user_id']))
        if cursor.fetchone():
            flash("You have already sent a request for this project.", "warning")
        else:
            cursor.execute("INSERT INTO project_requests (project_id, user_id, message) VALUES (%s, %s, %s)", 
                          (project_id, session['user_id'], message))
            db.commit()
            flash("Request sent successfully!", "success")
    except Exception as e:
        db.rollback()
        print(f"Error joining project: {e}")
        flash("Error sending request.", "danger")
    finally:
        cursor.close()
        
    return redirect(url_for('collaboration.project_details', project_id=project_id))

@collaboration_bp.route('/community/request/<int:request_id>/<action>', methods=['POST'])
def manage_request(request_id, action):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    if action not in ['accepted', 'rejected']:
        return redirect(url_for('collaboration.community'))
        
    cursor = db.cursor(dictionary=True)
    try:
        # Verify ownership of the project associated with the request
        cursor.execute("""
            SELECT pr.project_id 
            FROM project_requests pr
            JOIN personal_projects pp ON pr.project_id = pp.id
            WHERE pr.id = %s AND pp.user_id = %s
        """, (request_id, session['user_id']))
        
        if not cursor.fetchone():
            flash("Unauthorized action.", "danger")
        else:
            cursor.execute("UPDATE project_requests SET status = %s WHERE id = %s", (action, request_id))
            db.commit()
            flash(f"Request {action}.", "success")
            
            # Fetch project_id to redirect back
            cursor.execute("SELECT project_id FROM project_requests WHERE id = %s", (request_id,))
            project_id = cursor.fetchone()['project_id']
            return redirect(url_for('collaboration.project_details', project_id=project_id))
            
    except Exception as e:
        db.rollback()
        print(f"Error managing request: {e}")
        flash("Error processing request.", "danger")
        return redirect(url_for('collaboration.community'))
    finally:
        cursor.close()

@collaboration_bp.route('/community/project/<int:project_id>/comment', methods=['POST'])
def add_comment(project_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    content = request.form.get('content')
    if not content:
        flash("Comment cannot be empty.", "warning")
        return redirect(url_for('collaboration.project_details', project_id=project_id))
        
    cursor = db.cursor()
    try:
        cursor.execute("INSERT INTO project_comments (project_id, user_id, content) VALUES (%s, %s, %s)", 
                      (project_id, session['user_id'], content))
        db.commit()
        flash("Comment posted!", "success")
    except Exception as e:
        db.rollback()
        print(f"Error posting comment: {e}")
        flash("Error posting comment.", "danger")
    finally:
        cursor.close()
        
    return redirect(url_for('collaboration.project_details', project_id=project_id))

# -------------------------------------------------------------------------
# FACULTY COLLABORATION ROUTES
# -------------------------------------------------------------------------

@collaboration_bp.route('/faculty/dashboard')
def faculty_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)
    
    # 1. Verify Faculty Role
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    
    if not user or user['role'] != 'faculty':
        flash("Access denied. Faculty only area.", "danger")
        cursor.close()
        return redirect(url_for('collaboration.community'))

    # 2. Fetch Active Collaborations (Open)
    cursor.execute("""
        SELECT * FROM faculty_collaborations 
        WHERE faculty_id = %s AND status = 'open'
        ORDER BY created_at DESC
    """, (session['user_id'],))
    active_collabs = cursor.fetchall()

    # 3. Fetch Published/Closed
    cursor.execute("""
        SELECT * FROM faculty_collaborations 
        WHERE faculty_id = %s AND status = 'closed'
        ORDER BY created_at DESC
    """, (session['user_id'],))
    closed_collabs = cursor.fetchall()

    # 4. Fetch Incoming Requests (Pending)
    cursor.execute("""
        SELECT cr.*, fc.title as collab_title, u.name as user_name, u.role as user_role
        FROM collaboration_requests cr
        JOIN faculty_collaborations fc ON cr.collaboration_id = fc.id
        JOIN users u ON cr.user_id = u.id
        WHERE fc.faculty_id = %s AND cr.status = 'pending'
        ORDER BY cr.created_at DESC
    """, (session['user_id'],))
    incoming_requests = cursor.fetchall()

    # Apply strict visibility filtering for listings if enabled
    def _skills_list(s): 
        return expand_skills((s or "").split(","))
    viewer_skills = _skills_list(user.get('skills'))
    def _matches(collab):
        if collab.get('faculty_id') == session['user_id']:
            return True
        vis_flag = collab.get('strict_visibility', collab.get('hide_non_matching', 0))
        if vis_flag != 1:
            return True
        # Only enforce when audience includes faculty
        if collab.get('audience') not in ('faculty_only', 'both'):
            return True
        req_must = _skills_list(collab.get('required_skills_must') or collab.get('must_have_skills') or collab.get('required_skills'))
        # Must-have needs intersection
        return (not req_must) or any(k in viewer_skills for k in req_must)
    active_collabs = [c for c in active_collabs if _matches(c)]
    closed_collabs = [c for c in closed_collabs if _matches(c)]

    # 5. Fetch invitations for current faculty (as invitee)
    cursor.execute("""
        SELECT cr.*, fc.title as collab_title
        FROM collaboration_requests cr
        JOIN faculty_collaborations fc ON cr.collaboration_id = fc.id
        WHERE cr.user_id = %s AND (cr.status = 'pending' OR cr.status IS NULL)
        ORDER BY cr.created_at DESC
    """, (session['user_id'],))
    my_invites = cursor.fetchall()

    cursor.execute("""
        SELECT fc.*
        FROM collaboration_requests cr
        JOIN faculty_collaborations fc ON cr.collaboration_id = fc.id
        WHERE cr.user_id = %s AND cr.status = 'accepted'
        ORDER BY fc.created_at DESC
    """, (session['user_id'],))
    my_participations = cursor.fetchall()

    cursor.close()
    return render_template('faculty_dashboard.html', user=user, active_collabs=active_collabs, closed_collabs=closed_collabs, requests=incoming_requests, my_invites=my_invites, my_participations=my_participations)

@collaboration_bp.route('/faculty/invitation/<int:req_id>/respond/<action>', methods=['POST'])
def respond_invitation(req_id, action):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    if action not in ['accepted', 'rejected']:
        return redirect(url_for('collaboration.faculty_dashboard'))
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT cr.id, cr.user_id, cr.collaboration_id, cr.status, fc.max_students, fc.max_faculty
            FROM collaboration_requests cr
            JOIN faculty_collaborations fc ON cr.collaboration_id = fc.id
            WHERE cr.id = %s
        """, (req_id,))
        req = cursor.fetchone()
        if not req or req['user_id'] != session['user_id'] or req['status'] != 'pending':
            flash("Unauthorized or invalid request.", "danger")
            return redirect(url_for('collaboration.faculty_dashboard'))
        if action == 'accepted':
            cursor.execute("SELECT role FROM users WHERE id = %s", (req['user_id'],))
            applicant = cursor.fetchone()
            cursor.execute("""
                SELECT COUNT(*) as count FROM collaboration_requests cr
                JOIN users u ON cr.user_id = u.id
                WHERE cr.collaboration_id = %s AND cr.status = 'accepted' AND u.role = %s
            """, (req['collaboration_id'], applicant['role']))
            current_count = cursor.fetchone()['count']
            limit = req['max_students'] if applicant['role'] == 'student' else req['max_faculty']
            if current_count >= limit:
                flash(f"Limit reached for {applicant['role']}s. Cannot accept.", "warning")
                return redirect(url_for('collaboration.faculty_dashboard'))
        cursor.execute("UPDATE collaboration_requests SET status = %s WHERE id = %s", (action, req_id))
        db.commit()
        flash(f"Invitation {action}.", "success")
    except Exception as e:
        db.rollback()
        print(f"Error responding to invitation: {e}")
        flash("Error.", "danger")
    finally:
        cursor.close()
    return redirect(url_for('collaboration.faculty_dashboard'))
@collaboration_bp.route('/faculty/create', methods=['GET', 'POST'])
def create_faculty_collaboration():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()

    if not user or user['role'] != 'faculty':
        cursor.close()
        flash("Access denied.", "danger")
        return redirect(url_for('collaboration.community'))

    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        description = (request.form.get('description') or '').strip()
        collab_type = (request.form.get('type') or 'article').strip()
        audience = (request.form.get('audience') or 'faculty_only').strip()
        try:
            max_students = int(request.form.get('max_students') or 0)
        except ValueError:
            max_students = 0
        try:
            max_faculty = int(request.form.get('max_faculty') or 0)
        except ValueError:
            max_faculty = 0
        required_skills_must = (request.form.get('required_skills_must') or '').strip()
        required_skills_nice = (request.form.get('required_skills_nice') or '').strip()
        strict_raw = (request.form.get('strict_visibility') or '').strip().lower()
        strict_visibility = 1 if strict_raw in ('on', '1', 'true', 'yes') else 0
        # Legacy aggregate (optional)
        required_skills = ", ".join([s for s in [required_skills_must, required_skills_nice] if s.strip()])

        try:
            cursor.execute("SHOW COLUMNS FROM faculty_collaborations")
            cols = [c['Field'] if isinstance(c, dict) else c[0] for c in cursor.fetchall()]
            available = set(cols)
            insert_cols = ['faculty_id','title','description','collaboration_type','audience','max_students','max_faculty','required_skills']
            values = [session['user_id'], title, description, collab_type, audience, max_students, max_faculty, required_skills]
            if 'required_skills_must' in available:
                insert_cols.append('required_skills_must'); values.append(required_skills_must)
            elif 'must_have_skills' in available:
                insert_cols.append('must_have_skills'); values.append(required_skills_must)
            if 'required_skills_nice' in available:
                insert_cols.append('required_skills_nice'); values.append(required_skills_nice)
            elif 'nice_to_have_skills' in available:
                insert_cols.append('nice_to_have_skills'); values.append(required_skills_nice)
            if 'strict_visibility' in available:
                insert_cols.append('strict_visibility'); values.append(strict_visibility)
            elif 'hide_non_matching' in available:
                insert_cols.append('hide_non_matching'); values.append(strict_visibility)
            cols_sql = ", ".join(insert_cols)
            ph_sql = ", ".join(["%s"] * len(values))
            cursor.execute(f"INSERT INTO faculty_collaborations ({cols_sql}) VALUES ({ph_sql})", tuple(values))
            db.commit()
            flash("Collaboration posted successfully!", "success")
            return redirect(url_for('collaboration.faculty_dashboard'))
        except Exception as e:
            db.rollback()
            print(f"Error creating faculty collab: {e}")
            flash(f"Error creating collaboration: {e}", "danger")
    
    cursor.close()
    return render_template('create_faculty_collaboration.html', user=user)

@collaboration_bp.route('/faculty/collaboration/<int:collab_id>')
def faculty_collaboration_details(collab_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)
    
    # User info
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()

    # Collab details
    cursor.execute("""
        SELECT fc.*, u.name as faculty_name, u.profile_photo as faculty_photo
        FROM faculty_collaborations fc
        JOIN users u ON fc.faculty_id = u.id
        WHERE fc.id = %s
    """, (collab_id,))
    collab = cursor.fetchone()

    if not collab:
        cursor.close()
        flash("Collaboration not found.", "danger")
        return redirect(url_for('collaboration.community'))

    # Access Control Logic (Visibility)
    if collab['audience'] == 'faculty_only' and user['role'] != 'faculty':
        cursor.close()
        flash("This collaboration is restricted to faculty members only.", "warning")
        return redirect(url_for('collaboration.community'))

    # Fetch accepted participants count
    cursor.execute("""
        SELECT u.role, COUNT(*) as count
        FROM collaboration_requests cr
        JOIN users u ON cr.user_id = u.id
        WHERE cr.collaboration_id = %s AND cr.status = 'accepted'
        GROUP BY u.role
    """, (collab_id,))
    counts = cursor.fetchall()
    
    current_students = 0
    current_faculty = 0
    for c in counts:
        if c['role'] == 'student':
            current_students = c['count']
        elif c['role'] == 'faculty':
            current_faculty = c['count']
    
    collab['current_students'] = current_students
    collab['current_faculty'] = current_faculty

    cursor.execute("""
        SELECT u.id, u.name, u.email, u.role, u.profile_photo
        FROM collaboration_requests cr
        JOIN users u ON cr.user_id = u.id
        WHERE cr.collaboration_id = %s AND cr.status = 'accepted'
        ORDER BY u.role ASC, u.name ASC
    """, (collab_id,))
    accepted_users = cursor.fetchall()

    try:
        cursor.execute("SHOW TABLES LIKE 'collaboration_comments'")
        exists = cursor.fetchone()
        if not exists:
            cursor.execute("""
                CREATE TABLE collaboration_comments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    collaboration_id INT NOT NULL,
                    user_id INT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.commit()
    except Exception:
        db.rollback()

    cursor.execute("""
        SELECT cc.*, u.name as user_name, u.profile_photo as user_photo
        FROM collaboration_comments cc
        JOIN users u ON cc.user_id = u.id
        WHERE cc.collaboration_id = %s
        ORDER BY cc.created_at DESC
    """, (collab_id,))
    collab_comments = cursor.fetchall()

    can_comment = (user['id'] == collab['faculty_id']) or any(u['id'] == user['id'] for u in accepted_users)

    # Recommended faculty (for owner)
    recommended_faculty = []
    if user['id'] == collab['faculty_id']:
        req_must = [s.strip().lower() for s in (collab.get('required_skills_must') or collab.get('must_have_skills') or "").split(',') if s.strip()]
        req_nice = [s.strip().lower() for s in (collab.get('required_skills_nice') or collab.get('nice_to_have_skills') or "").split(',') if s.strip()]
        req_all = [s.strip().lower() for s in (collab.get('required_skills') or "").split(',') if s.strip()]
        def _expand_split(terms):
            out = []
            for t in terms:
                parts = [p.strip() for p in re.split(r'[/&]|\band\b', t) if p.strip()]
                out.extend(parts if parts else [t])
            return out
        req_must = _expand_split(req_must)
        req_nice = _expand_split(req_nice)
        req_all = _expand_split(req_all)
        if (len(req_must) + len(req_nice) + len(req_all)) == 0:
            text = f"{str(collab.get('title') or '')} {str(collab.get('description') or '')}".lower()
            terms = []
            for t in all_known_terms():
                if t and t in text:
                    terms.append(t)
            req_all = terms
        # Build a simple scoring: skills matches + project domain/tech_stack matches
        kws = req_must + req_nice + req_all
        params = [user['id']]
        where_parts = []
        for k in kws:
            where_parts.append("LOWER(skills) LIKE %s OR LOWER(interests) LIKE %s")
            params.extend([f"%{k}%", f"%{k}%"])
        base = "SELECT id, name, skills, interests, profile_photo FROM users WHERE role='faculty' AND id != %s"
        if where_parts:
            base += " AND (" + " OR ".join(where_parts) + ")"
        base += " LIMIT 12"
        temp_cursor = db.cursor(dictionary=True)
        temp_cursor.execute(base, tuple(params))
        candidates = temp_cursor.fetchall()
        # Score candidates
        def _calc(u):
            us = []
            if u.get('skills'):
                base = [s.strip().lower() for s in str(u['skills']).split(',') if s.strip()]
                us.extend(_expand_split(base))
            if u.get('interests'):
                base_i = [s.strip().lower() for s in str(u['interests']).split(',') if s.strip()]
                us.extend(_expand_split(base_i))
            us_exp = set(expand_skills(us))
            must_matches = 0
            for k in req_must:
                if set(expand_skills([k])) & us_exp:
                    must_matches += 1
            nice_matches = 0
            for k in req_nice:
                if set(expand_skills([k])) & us_exp:
                    nice_matches += 1
            gen_matches = 0
            for k in req_all:
                if set(expand_skills([k])) & us_exp:
                    gen_matches += 1
            score = must_matches * 2 + nice_matches + gen_matches
            total = len(req_must) * 2 + len(req_nice) + len(req_all)
            percent = int(round(100 * score / total)) if total > 0 else 0
            u['match_percent'] = percent
            return score
        candidates.sort(key=_calc, reverse=True)
        recommended_faculty = candidates[:6]
        temp_cursor.close()

    # Check eligibility to apply
    can_apply = True
    rejection_reason = None

    # 1. Check if already applied
    cursor.execute("SELECT status FROM collaboration_requests WHERE collaboration_id = %s AND user_id = %s", (collab_id, user['id']))
    existing_request = cursor.fetchone()
    if existing_request:
        can_apply = False
        rejection_reason = f"Already applied (Status: {existing_request['status']})"
        collab['my_status'] = existing_request['status']
    else:
        collab['my_status'] = None

    if can_apply:
        if user['role'] == 'student':
            if collab['audience'] == 'faculty_only':
                can_apply = False
                rejection_reason = "Faculty only."
            elif current_students >= collab['max_students']:
                can_apply = False
                rejection_reason = "Student limit reached."
            else:
                # Skill Check
                req_skills_must = [s.strip().lower() for s in (collab.get('required_skills_must') or "").split(',') if s.strip()]
                user_skills = [s.strip().lower() for s in (user['skills'] or "").split(',') if s.strip()]
                
                # Check intersection
                if req_skills_must:
                    has_skill = any(skill in user_skills for skill in req_skills_must)
                    if not has_skill:
                        can_apply = False
                        rejection_reason = f"Missing must-have skills: {', '.join(req_skills_must)}"

        elif user['role'] == 'faculty':
            # Faculty applying to another faculty's project
            if collab['faculty_id'] == user['id']:
                can_apply = False
                rejection_reason = "Owner"
            elif collab['audience'] == 'students_only':
                can_apply = False
                rejection_reason = "Students only."
            elif current_faculty >= collab['max_faculty']:
                can_apply = False
                rejection_reason = "Faculty limit reached."
            else:
                req_skills_f = [s.strip().lower() for s in (collab.get('required_skills_must') or "").split(',') if s.strip()]
                user_skills_f = [s.strip().lower() for s in (user['skills'] or "").split(',') if s.strip()]
                if req_skills_f:
                    has_skill_f = any(skill in user_skills_f for skill in req_skills_f)
                    if not has_skill_f:
                        can_apply = False
                        rejection_reason = f"Missing must-have skills: {', '.join(req_skills_f)}"

    # Fetch pending requests if owner
    requests = []
    if user['id'] == collab['faculty_id']:
        cursor.execute("""
            SELECT cr.*, u.name as user_name, u.role as user_role, u.skills as user_skills
            FROM collaboration_requests cr
            JOIN users u ON cr.user_id = u.id
            WHERE cr.collaboration_id = %s AND cr.status = 'pending'
        """, (collab_id,))
        requests = cursor.fetchall()

    cursor.close()
    return render_template('faculty_collaboration_details.html', user=user, collab=collab, can_apply=can_apply, rejection_reason=rejection_reason, requests=requests, recommended_faculty=recommended_faculty, accepted_users=accepted_users, collab_comments=collab_comments, can_comment=can_comment)

@collaboration_bp.route('/faculty/collaboration/<int:collab_id>/apply', methods=['POST'])
def apply_faculty_collaboration(collab_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    message = request.form.get('message')
    
    cursor = db.cursor()
    try:
        cursor.execute("SELECT 1 FROM collaboration_requests WHERE collaboration_id = %s AND user_id = %s", (collab_id, session['user_id']))
        if cursor.fetchone():
            flash("Already applied.", "warning")
        else:
            cursor.execute("INSERT INTO collaboration_requests (collaboration_id, user_id, message) VALUES (%s, %s, %s)", 
                          (collab_id, session['user_id'], message))
            db.commit()
            flash("Application sent successfully!", "success")
    except Exception as e:
        db.rollback()
        print(f"Error applying: {e}")
        flash("Error applying.", "danger")
    finally:
        cursor.close()

    return redirect(url_for('collaboration.faculty_collaboration_details', collab_id=collab_id))

@collaboration_bp.route('/faculty/collaboration/<int:collab_id>/comment', methods=['POST'])
def add_collaboration_comment(collab_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    content = request.form.get('content', '').strip()
    if not content:
        flash("Message cannot be empty.", "warning")
        return redirect(url_for('collaboration.faculty_collaboration_details', collab_id=collab_id))
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT faculty_id FROM faculty_collaborations WHERE id = %s", (collab_id,))
        c = cur.fetchone()
        if not c:
            flash("Collaboration not found.", "danger")
            return redirect(url_for('collaboration.community'))
        cur.execute("""
            SELECT 1 FROM collaboration_requests 
            WHERE collaboration_id = %s AND user_id = %s AND status = 'accepted'
        """, (collab_id, session['user_id']))
        is_member = bool(cur.fetchone())
        if not is_member and c['faculty_id'] != session['user_id']:
            flash("You are not a participant.", "danger")
            return redirect(url_for('collaboration.faculty_collaboration_details', collab_id=collab_id))
        cur.close()
        cur2 = db.cursor()
        cur2.execute("INSERT INTO collaboration_comments (collaboration_id, user_id, content) VALUES (%s, %s, %s)", (collab_id, session['user_id'], content))
        db.commit()
        cur2.close()
        flash("Message posted.", "success")
    except Exception as e:
        db.rollback()
        print(f"Error posting collaboration message: {e}")
        flash("Error posting message.", "danger")
    return redirect(url_for('collaboration.faculty_collaboration_details', collab_id=collab_id))
@collaboration_bp.route('/faculty/collaboration/<int:collab_id>/invite/<int:user_id>', methods=['POST'])
def invite_faculty_user(collab_id, user_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT faculty_id FROM faculty_collaborations WHERE id = %s", (collab_id,))
    coll = cur.fetchone()
    if not coll or coll['faculty_id'] != session['user_id']:
        cur.close()
        flash("Unauthorized.", "danger")
        return redirect(url_for('collaboration.faculty_collaboration_details', collab_id=collab_id))
    cur.close()
    cur2 = db.cursor()
    try:
        cur2.execute("SELECT 1 FROM collaboration_requests WHERE collaboration_id = %s AND user_id = %s", (collab_id, user_id))
        if cur2.fetchone():
            flash("Already requested or invited.", "warning")
        else:
            cur2.execute("INSERT INTO collaboration_requests (collaboration_id, user_id, message) VALUES (%s, %s, %s)", (collab_id, user_id, "Invitation from owner"))
            db.commit()
            flash("Invitation sent.", "success")
    except Exception:
        db.rollback()
        flash("Error sending invitation.", "danger")
    finally:
        cur2.close()
    return redirect(url_for('collaboration.faculty_collaboration_details', collab_id=collab_id))
@collaboration_bp.route('/faculty/request/<int:req_id>/manage/<action>', methods=['POST'])
def manage_faculty_request(req_id, action):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    if action not in ['accepted', 'rejected']:
        return redirect(url_for('collaboration.faculty_dashboard'))

    cursor = db.cursor(dictionary=True)
    try:
        # Verify ownership
        cursor.execute("""
            SELECT cr.collaboration_id, fc.faculty_id, fc.max_students, fc.max_faculty
            FROM collaboration_requests cr
            JOIN faculty_collaborations fc ON cr.collaboration_id = fc.id
            WHERE cr.id = %s
        """, (req_id,))
        data = cursor.fetchone()

        if not data or data['faculty_id'] != session['user_id']:
            flash("Unauthorized.", "danger")
        else:
            # If accepting, check limits again
            if action == 'accepted':
                # Get applicant role
                cursor.execute("SELECT role FROM users WHERE id = (SELECT user_id FROM collaboration_requests WHERE id = %s)", (req_id,))
                applicant = cursor.fetchone()
                
                # Count current accepted
                cursor.execute("""
                    SELECT COUNT(*) as count FROM collaboration_requests cr
                    JOIN users u ON cr.user_id = u.id
                    WHERE cr.collaboration_id = %s AND cr.status = 'accepted' AND u.role = %s
                """, (data['collaboration_id'], applicant['role']))
                current_count = cursor.fetchone()['count']

                limit = data['max_students'] if applicant['role'] == 'student' else data['max_faculty']
                
                if current_count >= limit:
                    flash(f"Limit reached for {applicant['role']}s. Cannot accept.", "warning")
                    return redirect(url_for('collaboration.faculty_collaboration_details', collab_id=data['collaboration_id']))

            cursor.execute("UPDATE collaboration_requests SET status = %s WHERE id = %s", (action, req_id))
            db.commit()
            flash(f"Request {action}.", "success")
            
            return redirect(url_for('collaboration.faculty_collaboration_details', collab_id=data['collaboration_id']))

    except Exception as e:
        db.rollback()
        print(f"Error managing faculty request: {e}")
        flash("Error.", "danger")
    finally:
        cursor.close()

    return redirect(url_for('collaboration.faculty_dashboard'))

@collaboration_bp.route('/faculty/collaboration/<int:collab_id>/close', methods=['POST'])
def close_faculty_collaboration(collab_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    cursor = db.cursor(dictionary=True)
    try:
        # Verify ownership
        cursor.execute("SELECT faculty_id FROM faculty_collaborations WHERE id = %s", (collab_id,))
        collab = cursor.fetchone()
        
        if not collab or collab['faculty_id'] != session['user_id']:
            flash("Unauthorized.", "danger")
        else:
            cursor.execute("UPDATE faculty_collaborations SET status = 'closed' WHERE id = %s", (collab_id,))
            db.commit()
            flash("Collaboration closed.", "success")
            
    except Exception as e:
        db.rollback()
        print(f"Error closing collab: {e}")
        flash("Error closing collaboration.", "danger")
    finally:
        cursor.close()

    return redirect(url_for('collaboration.faculty_collaboration_details', collab_id=collab_id))
