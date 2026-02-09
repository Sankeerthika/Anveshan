from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from backend.db import db
from mysql.connector import Error
import os
import hashlib
import random
import smtplib
import ssl
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from backend.utils.email_sender import send_email, smtp_missing_keys
from backend.utils.env_manager import update_env_file

load_dotenv()

auth_bp = Blueprint('auth', __name__)

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

def generate_otp():
    return f"{random.randint(100000, 999999)}"
def hash_otp(email, code):
    return hashlib.sha256((email.lower().strip() + ":" + code).encode()).hexdigest()
def ensure_otp_table_exists():
    try:
        c = db.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS otp_codes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                code_hash VARCHAR(255) NOT NULL,
                purpose ENUM('password_reset','registration') NOT NULL,
                expires_at DATETIME NOT NULL,
                used TINYINT(1) DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
        c.close()
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        current_app.logger.error("ensure_otp_table_exists failed: %s", e)

# ------------------- LOGIN -------------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():

    # Already logged in
    if 'user_id' in session:
        role = session.get('role')
        if role == 'club':
            return redirect(url_for('club.club_dashboard'))
        if role == 'faculty':
            return redirect(url_for('collaboration.faculty_dashboard'))
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash("Please enter email and password", "danger")
            return redirect(url_for('auth.login'))

        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE email=%s",
            (email,)
        )
        user = cursor.fetchone()
        
        if not user:
            flash(f"No account found with email '{email}'. Please register first.", "danger")
            cursor.close()
            return redirect(url_for('auth.login'))
        
        # Verify password (hash or legacy plaintext)
        authenticated = False
        if user:
            stored_password = user['password']
            # Check if it's a hash (Werkzeug hashes usually start with 'scrypt:' or 'pbkdf2:')
            if stored_password.startswith(('scrypt:', 'pbkdf2:')):
                if check_password_hash(stored_password, password):
                    authenticated = True
            elif stored_password == password:
                # Legacy plaintext match -> Upgrade to hash
                new_hash = generate_password_hash(password)
                cursor.execute("UPDATE users SET password=%s WHERE id=%s", (new_hash, user['id']))
                db.commit()
                authenticated = True
        
        cursor.close()

        if authenticated:
            # 🔑 STORE EVERYTHING NEEDED
            session.clear()
            session.permanent = True
            session['user_id'] = user['id']
            session['user_email'] = user['email']   # ✅ FIX
            session['user_name'] = user['name']
            session['role'] = user.get('role', 'student')

            role = session['role']
            if role == 'club':
                return redirect(url_for('club.club_dashboard'))
            if role == 'faculty':
                return redirect(url_for('collaboration.faculty_dashboard'))
            return redirect(url_for('student.dashboard'))

        flash("Incorrect password. Please try again or reset it.", "danger")
        return redirect(url_for('auth.login'))

    return render_template('login.html')


# ------------------- REGISTER -------------------
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if not email:
            flash("Enter your email to request OTP.", "danger")
            return redirect(url_for('auth.register'))
        return redirect(url_for('auth.request_registration_otp'))

    return render_template('register.html')

@auth_bp.route('/register/request-otp', methods=['GET', 'POST'])
def request_registration_otp():
    if request.method == 'GET':
        return redirect(url_for('auth.register'))
    email = request.form.get('email', '').strip()
    if not email:
        flash("Enter email to send OTP.", "warning")
        return redirect(url_for('auth.register'))
    if not is_college_email(email):
        flash("Please use your college email address.", "warning")
        return redirect(url_for('auth.register'))
    try:
        c0 = db.cursor()
        c0.execute("SELECT id FROM users WHERE email=%s", (email,))
        exists_user = c0.fetchone()
        c0.close()
        if exists_user:
            flash("Email already registered. Please login.", "info")
            return redirect(url_for('auth.login'))
        code = generate_otp()
        h = hash_otp(email, code)
        expires = datetime.now() + timedelta(minutes=10)
        ensure_otp_table_exists()
        c = db.cursor()
        c.execute("""
            INSERT INTO otp_codes (email, code_hash, purpose, expires_at)
            VALUES (%s,%s,'registration',%s)
        """, (email, h, expires.strftime('%Y-%m-%d %H:%M:%S')))
        db.commit()
        c.close()
    except Error as e:
        try:
            db.rollback()
        except Exception:
            pass
        current_app.logger.error("Registration OTP DB error: %s", e)
        flash("Database error while generating OTP. Please try again in a few minutes.", "danger")
        return redirect(url_for('auth.register'))
    except Exception as e:
        current_app.logger.error("Registration OTP unexpected error: %s", e)
        flash("Unexpected server error while generating OTP. Please try again later.", "danger")
        return redirect(url_for('auth.register'))
    missing = smtp_missing_keys()
    if missing:
        flash(f"Email sending misconfigured: {', '.join(missing)} not set.", "danger")
        return redirect(url_for('auth.register_verify', email=email))
    sent = send_email(email, "Your Anveshan Registration OTP", f"Your OTP is {code}. It expires in 10 minutes.")
    if sent:
        flash("OTP sent to your email. Enter it to set your password.", "info")
    else:
        # Don't expose config errors to user, just generic error
        err = current_app.config.get("SMTP_LAST_ERROR")
        if current_app.debug and err:
            flash(f"Email failed: {err}", "danger")
        else:
            flash("Unable to send email. Please try again later or contact support.", "danger")
        current_app.logger.error("Failed to send registration OTP to %s. Check SMTP config.", email)
    return redirect(url_for('auth.register_verify', email=email))

@auth_bp.route('/register/verify', methods=['GET', 'POST'])
def register_verify():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        otp = request.form.get('otp', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'student')
        allowed_roles = {'student', 'club', 'faculty'}
        if role not in allowed_roles:
            role = 'student'
        if not name or not email or not otp or not password:
            flash("Enter name, email, OTP, and password.", "danger")
            return redirect(url_for('auth.register_verify', email=email))
        if role in {'student', 'faculty'} and not is_college_email(email):
            flash("Please use your college email address.", "warning")
            return redirect(url_for('auth.register_verify', email=email))
        cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT id, expires_at, used FROM otp_codes
            WHERE email=%s AND purpose='registration' AND code_hash=%s
            ORDER BY id DESC LIMIT 1
        """, (email, hash_otp(email, otp)))
        row = cur.fetchone()
        if not row or row['used'] == 1 or row['expires_at'] < datetime.now():
            cur.close()
            flash("Invalid or expired OTP.", "danger")
            return redirect(url_for('auth.register_verify', email=email))
        c2 = db.cursor()
        try:
            hashed_password = generate_password_hash(password)
            c2.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                (name, email, hashed_password, role)
            )
            cur.execute("UPDATE otp_codes SET used=1 WHERE id=%s", (row['id'],))
            db.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('auth.login'))
        except Error as e:
            db.rollback()
            if getattr(e, "errno", None) == 1062:
                flash("Email already registered", "warning")
            else:
                flash(f"Registration error: {str(e)}", "danger")
            return redirect(url_for('auth.register_verify', email=email))
        finally:
            c2.close()
            cur.close()
    email = request.args.get('email', '')
    return render_template('register_verify.html', email=email)

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if not email:
            flash("Enter your email.", "warning")
            return redirect(url_for('auth.forgot_password'))
        c = db.cursor()
        c.execute("SELECT id FROM users WHERE email=%s", (email,))
        exists = c.fetchone()
        if not exists:
            c.close()
            # Security: Don't reveal if account exists, but for now we do to be helpful
            flash("No account found for this email.", "danger")
            return redirect(url_for('auth.forgot_password'))
        code = generate_otp()
        h = hash_otp(email, code)
        expires = datetime.now() + timedelta(minutes=10)
        c.execute("""
            INSERT INTO otp_codes (email, code_hash, purpose, expires_at)
            VALUES (%s,%s,'password_reset',%s)
        """, (email, h, expires.strftime('%Y-%m-%d %H:%M:%S')))
        db.commit()
        c.close()
        missing = smtp_missing_keys()
        if missing:
            flash(f"Email sending misconfigured: {', '.join(missing)} not set.", "danger")
            return redirect(url_for('auth.reset_password', email=email))
        sent = send_email(email, "Your Anveshan Password Reset OTP", f"Your OTP is {code}. It expires in 10 minutes.")
        if sent:
            flash("OTP sent to your email.", "info")
            return redirect(url_for('auth.reset_password', email=email))
        else:
            err = current_app.config.get("SMTP_LAST_ERROR")
            if current_app.debug and err:
                flash(f"Email failed: {err}", "danger")
            else:
                flash("Unable to send email. Please try again later.", "danger")
            current_app.logger.error("Failed to send password reset OTP to %s. Check SMTP config.", email)
            return redirect(url_for('auth.forgot_password'))
    return render_template('forgot_password.html')

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        otp = request.form.get('otp', '').strip()
        new_password = request.form.get('password', '').strip()
        if not email or not otp or not new_password:
            flash("Enter email, OTP, and new password.", "danger")
            return redirect(url_for('auth.reset_password'))
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, expires_at, used FROM otp_codes
            WHERE email=%s AND purpose='password_reset' AND code_hash=%s
            ORDER BY id DESC LIMIT 1
        """, (email, hash_otp(email, otp)))
        row = cursor.fetchone()
        if not row or row['used'] == 1 or row['expires_at'] < datetime.now():
            cursor.close()
            flash("Invalid or expired OTP.", "danger")
            return redirect(url_for('auth.reset_password'))
        c2 = db.cursor()
        try:
            hashed_password = generate_password_hash(new_password)
            c2.execute("UPDATE users SET password=%s WHERE email=%s", (hashed_password, email))
            cursor.execute("UPDATE otp_codes SET used=1 WHERE id=%s", (row['id'],))
            db.commit()
        finally:
            c2.close()
            cursor.close()
        flash("Password updated. Login with your new password.", "success")
        return redirect(url_for('auth.login'))
    email = request.args.get('email', '')
    return render_template('reset_password.html', email=email)

# ------------------- LOGOUT -------------------
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for('auth.login'))
