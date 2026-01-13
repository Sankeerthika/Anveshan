from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from db import db
from mysql.connector import Error
import os
import hashlib
import random
import smtplib
import ssl
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

def is_college_email(email: str) -> bool:
    try:
        e = (email or "").strip().lower()
        if "@" not in e:
            return False
        domain = e.split("@")[-1]
        allowed_domains = {"anurag.edu.in"}
        return domain in allowed_domains
    except Exception:
        return False
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    db.commit()
    c.close()
except Exception:
    pass
def generate_otp():
    return f"{random.randint(100000, 999999)}"
def hash_otp(email, code):
    return hashlib.sha256((email.lower().strip() + ":" + code).encode()).hexdigest()
def send_email(to_email, subject, body):
    host = current_app.config.get("SMTP_HOST")
    port = int(current_app.config.get("SMTP_PORT") or 587)
    username = current_app.config.get("SMTP_USER")
    password = current_app.config.get("SMTP_PASSWORD")
    use_tls = bool(current_app.config.get("SMTP_TLS", True))
    if not host or not username or not password:
        try:
            root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
            if os.path.isfile(root_env):
                with open(root_env, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#') or '=' not in line:
                            continue
                        k, v = line.split('=', 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and v:
                            os.environ[k] = v
                # update config after reading .env
                current_app.config.update({
                    "SMTP_HOST": os.environ.get("SMTP_HOST"),
                    "SMTP_PORT": int(os.environ.get("SMTP_PORT") or port),
                    "SMTP_USER": os.environ.get("SMTP_USER"),
                    "SMTP_PASSWORD": os.environ.get("SMTP_PASSWORD"),
                    "SMTP_TLS": str(os.environ.get("SMTP_TLS", "true")).lower() in ("1", "true", "yes", "on"),
                })
                host = current_app.config.get("SMTP_HOST")
                username = current_app.config.get("SMTP_USER")
                password = current_app.config.get("SMTP_PASSWORD")
                use_tls = bool(current_app.config.get("SMTP_TLS", True))
                port = int(current_app.config.get("SMTP_PORT") or 587)
        except Exception:
            pass
    if not host or not username or not password:
        try:
            current_app.logger.info("Email to %s subject=%s body=%s", to_email, subject, body)
        except Exception:
            pass
        return False
    try:
        message = f"From: {username}\r\nTo: {to_email}\r\nSubject: {subject}\r\n\r\n{body}"
        if use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(host, port) as server:
                server.starttls(context=context)
                server.login(username, password)
                server.sendmail(username, [to_email], message.encode("utf-8"))
        else:
            with smtplib.SMTP(host, port) as server:
                server.login(username, password)
                server.sendmail(username, [to_email], message.encode("utf-8"))
        return True
    except Exception:
        try:
            current_app.logger.warning("SMTP failed; email not sent to %s", to_email)
        except Exception:
            pass
        return False
def smtp_missing_keys():
    missing = []
    if not current_app.config.get("SMTP_HOST"):
        missing.append("SMTP_HOST")
    if not current_app.config.get("SMTP_USER"):
        missing.append("SMTP_USER")
    if not current_app.config.get("SMTP_PASSWORD"):
        missing.append("SMTP_PASSWORD")
    return missing
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
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, password)
        )
        user = cursor.fetchone()
        cursor.close()

        if user:
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

        flash("Invalid email or password", "danger")
        return redirect(url_for('auth.login'))

    return render_template('login.html')


# ------------------- REGISTER -------------------
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        otp = request.form.get('otp', '').strip()
        role = request.form.get('role', 'student')
        allowed_roles = {'student', 'club', 'faculty'}
        if role not in allowed_roles:
            role = 'student'

        if not name or not email or not password:
            flash("All fields are required", "danger")
            return redirect(url_for('auth.register'))

        if role in {'student', 'faculty'} and not is_college_email(email):
            flash("Please register using your college email address (e.g., name@college.ac.in or name@college.edu).", "warning")
            return redirect(url_for('auth.register'))
        if not otp:
            flash("Enter the OTP sent to your email.", "warning")
            return redirect(url_for('auth.register'))
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, expires_at, used FROM otp_codes
            WHERE email=%s AND purpose='registration' AND code_hash=%s
            ORDER BY id DESC LIMIT 1
        """, (email, hash_otp(email, otp)))
        row = cursor.fetchone()
        if not row or row['used'] == 1 or row['expires_at'] < datetime.now():
            cursor.close()
            flash("Invalid or expired OTP.", "danger")
            return redirect(url_for('auth.register'))

        cursor2 = db.cursor()
        try:
            cursor2.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                (name, email, password, role)
            )
            cursor.execute("UPDATE otp_codes SET used=1 WHERE id=%s", (row['id'],))
            db.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('auth.login'))

        except Error as e:
            if e.errno == 1062:
                flash("Email already registered", "warning")
            else:
                flash("Something went wrong", "danger")
            return redirect(url_for('auth.register'))

        finally:
            cursor2.close()
            try:
                cursor.close()
            except Exception:
                pass

    return render_template('register.html')

@auth_bp.route('/register/request-otp', methods=['POST'])
def request_registration_otp():
    email = request.form.get('email', '').strip()
    if not email:
        flash("Enter email to send OTP.", "warning")
        return redirect(url_for('auth.register'))
    code = generate_otp()
    h = hash_otp(email, code)
    expires = datetime.now() + timedelta(minutes=10)
    c = db.cursor()
    c.execute("""
        INSERT INTO otp_codes (email, code_hash, purpose, expires_at)
        VALUES (%s,%s,'registration',%s)
    """, (email, h, expires.strftime('%Y-%m-%d %H:%M:%S')))
    db.commit()
    c.close()
    sent = send_email(email, "Your Anveshan Registration OTP", f"Your OTP is {code}. It expires in 10 minutes.")
    if sent:
        flash("OTP sent to your email.", "info")
        return redirect(url_for('auth.register'))
    else:
        mk = ", ".join(smtp_missing_keys()) or "SMTP config"
        flash(f"Email service not configured. Missing: {mk}", "danger")
        return redirect(url_for('auth.smtp_config'))

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
        sent = send_email(email, "Your Anveshan Password Reset OTP", f"Your OTP is {code}. It expires in 10 minutes.")
        if sent:
            flash("OTP sent to your email.", "info")
            return redirect(url_for('auth.reset_password', email=email))
        else:
            mk = ", ".join(smtp_missing_keys()) or "SMTP config"
            flash(f"Email service not configured. Missing: {mk}", "danger")
            return redirect(url_for('auth.smtp_config'))
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
            c2.execute("UPDATE users SET password=%s WHERE email=%s", (new_password, email))
            cursor.execute("UPDATE otp_codes SET used=1 WHERE id=%s", (row['id'],))
            db.commit()
        finally:
            c2.close()
            cursor.close()
        flash("Password updated. Login with your new password.", "success")
        return redirect(url_for('auth.login'))
    email = request.args.get('email', '')
    return render_template('reset_password.html', email=email)

@auth_bp.route('/smtp-config', methods=['GET', 'POST'])
def smtp_config():
    host = current_app.config.get("SMTP_HOST")
    user = current_app.config.get("SMTP_USER")
    tls = current_app.config.get("SMTP_TLS")
    port = current_app.config.get("SMTP_PORT")
    if request.method == 'POST':
        new_host = request.form.get('host', '').strip()
        new_port = request.form.get('port', '').strip() or "587"
        new_user = request.form.get('user', '').strip()
        new_pass = request.form.get('password', '').strip()
        new_tls = request.form.get('tls') == 'on'
        if not new_host or not new_user or not new_pass:
            flash("Please fill all required fields.", "danger")
            return redirect(url_for('auth.smtp_config'))
        try:
            current_app.config.update({
                "SMTP_HOST": new_host,
                "SMTP_PORT": int(new_port),
                "SMTP_USER": new_user,
                "SMTP_PASSWORD": new_pass,
                "SMTP_TLS": new_tls,
            })
            root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
            with open(root_env, 'w', encoding='utf-8') as f:
                f.write(f"SMTP_HOST={new_host}\n")
                f.write(f"SMTP_PORT={new_port}\n")
                f.write(f"SMTP_USER={new_user}\n")
                f.write(f"SMTP_PASSWORD={new_pass}\n")
                f.write(f"SMTP_TLS={'true' if new_tls else 'false'}\n")
            test_email = request.form.get('test_email', '').strip()
            if test_email:
                ok = send_email(test_email, "SMTP Test (Anveshan)", "SMTP configuration works.")
                if ok:
                    flash("SMTP saved and test email sent.", "success")
                else:
                    flash("SMTP saved, but sending failed. Check credentials.", "danger")
            else:
                flash("SMTP settings saved.", "success")
        except Exception as e:
            flash("Failed to save SMTP settings.", "danger")
        return redirect(url_for('auth.smtp_config'))
    return render_template('smtp_config.html', host=host, user=user, tls=tls, port=port)

# ------------------- LOGOUT -------------------
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for('auth.login'))
