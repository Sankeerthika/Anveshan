from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import db
from mysql.connector import Error

auth_bp = Blueprint('auth', __name__)

# ------------------- LOGIN -------------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():

    # Already logged in
    if 'user_id' in session:
        if session.get('role') == 'club':
            return redirect(url_for('club.club_dashboard'))
        return redirect(url_for('student_dashboard'))

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

            if session['role'] == 'club':
                return redirect(url_for('club.club_dashboard'))
            return redirect(url_for('student_dashboard'))

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
        role = request.form.get('role', 'student')

        if not name or not email or not password:
            flash("All fields are required", "danger")
            return redirect(url_for('auth.register'))

        cursor = db.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                (name, email, password, role)
            )
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
            cursor.close()

    return render_template('register.html')


# ------------------- LOGOUT -------------------
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for('auth.login'))
