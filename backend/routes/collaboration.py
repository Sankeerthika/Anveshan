from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import db
import os
from werkzeug.utils import secure_filename

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
                filter_keywords.extend([k.strip() for k in p['tech_stack'].split(',')])
            if p['domain']:
                filter_keywords.append(p['domain'])
        # Remove duplicates
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
            keywords.extend([k.strip() for k in project['tech_stack'].split(',')])
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
            cursor.close()
    else:
        # Check if current user has already requested to join
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT status FROM project_requests WHERE project_id = %s AND user_id = %s", (project_id, session['user_id']))
        req = cursor.fetchone()
        project['request_status'] = req['status'] if req else None
        cursor.close()

    return render_template('project_details.html', user=user, project=project, recommended_users=recommended_users, comments=comments, requests=requests)

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
    published_collabs = cursor.fetchall()

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

    cursor.close()
    return render_template('faculty_dashboard.html', user=user, active_collabs=active_collabs, published_collabs=published_collabs, requests=incoming_requests)

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
        title = request.form.get('title')
        description = request.form.get('description')
        collab_type = request.form.get('type') # article, project
        audience = request.form.get('audience') # faculty_only, students_only, both
        max_students = request.form.get('max_students', 0)
        max_faculty = request.form.get('max_faculty', 0)
        required_skills = request.form.get('required_skills', '')

        try:
            cursor.execute("""
                INSERT INTO faculty_collaborations 
                (faculty_id, title, description, collaboration_type, audience, max_students, max_faculty, required_skills)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (session['user_id'], title, description, collab_type, audience, max_students, max_faculty, required_skills))
            db.commit()
            flash("Collaboration posted successfully!", "success")
            return redirect(url_for('collaboration.faculty_dashboard'))
        except Exception as e:
            db.rollback()
            print(f"Error creating faculty collab: {e}")
            flash("Error creating collaboration.", "danger")
    
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
                req_skills = [s.strip().lower() for s in (collab['required_skills'] or "").split(',') if s.strip()]
                user_skills = [s.strip().lower() for s in (user['skills'] or "").split(',') if s.strip()]
                
                # Check intersection
                if req_skills:
                    has_skill = any(skill in user_skills for skill in req_skills)
                    if not has_skill:
                        can_apply = False
                        rejection_reason = f"Missing required skills: {', '.join(req_skills)}"

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
    return render_template('faculty_collaboration_details.html', user=user, collab=collab, can_apply=can_apply, rejection_reason=rejection_reason, requests=requests)

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
