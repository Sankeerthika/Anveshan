import mysql.connector
from mysql.connector import Error
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "anveshan"),
            port=int(os.getenv("DB_PORT", 3306))
        )
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

def create_database():
    """Create the database if it doesn't exist (requires root connection without db selected first)"""
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            port=int(os.getenv("DB_PORT", 3306))
        )
        cursor = conn.cursor()
        db_name = os.getenv("DB_NAME", "anveshan")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        print(f"Database '{db_name}' check/creation successful.")
        conn.close()
    except Exception as e:
        print(f"Error creating database: {e}")

def setup_tables():
    conn = get_db_connection()
    if not conn:
        print("Skipping table setup due to connection failure.")
        return
    
    cursor = conn.cursor()
    
    print("Setting up tables...")

    # 1. USERS Table
    # Combined schema from anveshan.sql, migrate_users.py, and migrate_collaboration.py
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(50),
            email VARCHAR(255) UNIQUE,
            password VARCHAR(255),
            role VARCHAR(20),
            profile_photo VARCHAR(255) DEFAULT 'default.jpg',
            bio TEXT,
            skills TEXT,
            linkedin_url VARCHAR(255),
            github_url VARCHAR(255),
            branch VARCHAR(50),
            year VARCHAR(20),
            section VARCHAR(10),
            interests TEXT,
            portfolio_url VARCHAR(255),
            medium_url VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("- users table checked.")

    # 2. EVENTS Table (from anveshan.sql)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(100),
            event_date DATE,
            deadline DATE,
            organizer VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("- events table checked.")

    # Ensure events table has required columns for features
    event_columns_to_ensure = [
        ("event_type", "VARCHAR(50)"),
        ("description", "TEXT"),
        ("mode", "VARCHAR(50)"),
        ("venue", "VARCHAR(255)"),
        ("organizer", "VARCHAR(100)"),
        ("domains", "TEXT"),
        ("organising_department", "VARCHAR(100)"),
        ("created_by", "INT"),
        ("min_team_size", "INT DEFAULT 1"),
        ("max_team_size", "INT DEFAULT 4"),
        ("registration_fee", "DECIMAL(10,2) DEFAULT 0"),
        ("girls_discount_enabled", "TINYINT(1) DEFAULT 0"),
        ("girls_team_discount", "DECIMAL(10,2) DEFAULT 0"),
        ("start_time", "DATETIME NULL"),
        ("end_time", "DATETIME NULL"),
        ("poster_path", "VARCHAR(255)"),
        ("external_registration_link", "VARCHAR(500)"),
        ("target_years", "VARCHAR(100)")
    ]
    for col_name, col_type in event_columns_to_ensure:
        try:
            cursor.execute(f"ALTER TABLE events ADD COLUMN {col_name} {col_type}")
        except Error as err:
            if getattr(err, "errno", None) == 1060:
                pass
            else:
                print(f"Error ensuring events column {col_name}: {err}")

    # 3. OTP_CODES Table (from auth.py)
    cursor.execute("""
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
    print("- otp_codes table checked.")

    # 4. PERSONAL_PROJECTS Table (from migrate_collaboration.py)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS personal_projects (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            title VARCHAR(255) NOT NULL,
            domain VARCHAR(100),
            description TEXT,
            tech_stack VARCHAR(255),
            looking_for VARCHAR(255),
            apply_deadline DATETIME NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    print("- personal_projects table checked.")

    # 5. PROJECT_REQUESTS, FOLLOWS, PROJECT_COMMENTS (from migrate_collab.py)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            project_id INT NOT NULL,
            user_id INT NOT NULL,
            message TEXT,
            status ENUM('pending', 'accepted', 'rejected') DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES personal_projects(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    print("- project_requests table checked.")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS follows (
            follower_id INT NOT NULL,
            followed_id INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (follower_id, followed_id),
            FOREIGN KEY (follower_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (followed_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    print("- follows table checked.")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_comments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            project_id INT NOT NULL,
            user_id INT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES personal_projects(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    print("- project_comments table checked.")

    # 6. FACULTY_COLLABORATIONS, COLLABORATION_REQUESTS (from migrate_faculty.py)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faculty_collaborations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            faculty_id INT NOT NULL,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            collaboration_type ENUM('article', 'project') NOT NULL,
            audience ENUM('faculty_only', 'students_only', 'both') NOT NULL,
            max_students INT DEFAULT 0,
            max_faculty INT DEFAULT 0,
            required_skills TEXT,
            required_skills_must TEXT,
            required_skills_nice TEXT,
            strict_visibility TINYINT(1) DEFAULT 0,
            apply_deadline DATETIME NULL,
            status ENUM('open', 'closed') DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (faculty_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    print("- faculty_collaborations table checked.")

    # Ensure new columns exist for backward DBs
    import mysql.connector
    try:
        cursor.execute("ALTER TABLE faculty_collaborations ADD COLUMN required_skills_must TEXT")
    except mysql.connector.Error as err:
        if err.errno == 1060:
            pass
        else:
            print(f"Error ensuring column required_skills_must: {err}")
    try:
        cursor.execute("ALTER TABLE faculty_collaborations ADD COLUMN required_skills_nice TEXT")
    except mysql.connector.Error as err:
        if err.errno == 1060:
            pass
        else:
            print(f"Error ensuring column required_skills_nice: {err}")
    try:
        cursor.execute("ALTER TABLE faculty_collaborations ADD COLUMN strict_visibility TINYINT(1) DEFAULT 0")
    except mysql.connector.Error as err:
        if err.errno == 1060:
            pass
        else:
            print(f"Error ensuring column strict_visibility: {err}")
    try:
        cursor.execute("ALTER TABLE faculty_collaborations ADD COLUMN apply_deadline DATETIME NULL")
    except mysql.connector.Error as err:
        if err.errno == 1060:
            pass
        else:
            print(f"Error ensuring column apply_deadline (faculty_collaborations): {err}")
    try:
        cursor.execute("ALTER TABLE personal_projects ADD COLUMN apply_deadline DATETIME NULL")
    except mysql.connector.Error as err:
        if err.errno == 1060:
            pass
        else:
            print(f"Error ensuring column apply_deadline (personal_projects): {err}")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS collaboration_requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            collaboration_id INT NOT NULL,
            user_id INT NOT NULL,
            message TEXT,
            status ENUM('pending', 'accepted', 'rejected') DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (collaboration_id) REFERENCES faculty_collaborations(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    print("- collaboration_requests table checked.")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS event_registrations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            event_id INT NOT NULL,
            team_name VARCHAR(255),
            domain VARCHAR(100),
            project_title VARCHAR(255),
            team_lead_name VARCHAR(255),
            team_lead_email VARCHAR(255),
            team_lead_phone VARCHAR(20),
            team_lead_year VARCHAR(20),
            team_lead_branch VARCHAR(50),
            team_lead_section VARCHAR(10),
            payment_screenshot VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
        )
    """)
    print("- event_registrations table checked.")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS event_team_members (
            id INT AUTO_INCREMENT PRIMARY KEY,
            registration_id INT NOT NULL,
            member_name VARCHAR(255),
            member_email VARCHAR(255),
            year VARCHAR(20),
            branch VARCHAR(50),
            section VARCHAR(10),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (registration_id) REFERENCES event_registrations(id) ON DELETE CASCADE
        )
    """)
    print("- event_team_members table checked.")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clubs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("- clubs table checked.")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS club_announcements (
            id INT AUTO_INCREMENT PRIMARY KEY,
            club_id INT NOT NULL,
            registration_link VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE
        )
    """)
    print("- club_announcements table checked.")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            event_id INT NOT NULL,
            domain VARCHAR(100),
            branch VARCHAR(50),
            year VARCHAR(20),
            required_size INT DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
        )
    """)
    print("- team_requests table checked.")

    # Ensure team_requests has required_skills column
    try:
        cursor.execute("ALTER TABLE team_requests ADD COLUMN required_skills TEXT")
    except mysql.connector.Error as err:
        if err.errno == 1060:
            pass
        else:
            print(f"Error ensuring team_requests column required_skills: {err}")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS join_requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            team_request_id INT NOT NULL,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            branch VARCHAR(50),
            year VARCHAR(20),
            phone VARCHAR(20),
            status ENUM('pending','accepted','rejected') DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_request_id) REFERENCES team_requests(id) ON DELETE CASCADE
        )
    """)
    print("- join_requests table checked.")

    # Ensure join_requests.phone can store long links (e.g., LinkedIn URLs)
    try:
        cursor.execute("ALTER TABLE join_requests MODIFY COLUMN phone VARCHAR(100)")
    except mysql.connector.Error as err:
        if err.errno == 1265 or err.errno == 1060 or err.errno == 1292:
            pass
        else:
            try:
                cursor.execute("ALTER TABLE join_requests MODIFY COLUMN phone VARCHAR(100)")
            except Exception:
                pass

    # Ensure existing users table has all columns (Migration logic)
    # This handles cases where the table exists but is missing newer columns
    columns_to_ensure = [
        ("profile_photo", "VARCHAR(255) DEFAULT 'default.jpg'"),
        ("bio", "TEXT"),
        ("skills", "TEXT"),
        ("linkedin_url", "VARCHAR(255)"),
        ("github_url", "VARCHAR(255)"),
        ("branch", "VARCHAR(50)"),
        ("year", "VARCHAR(20)"),
        ("section", "VARCHAR(10)"),
        ("interests", "TEXT"),
        ("portfolio_url", "VARCHAR(255)"),
        ("medium_url", "VARCHAR(255)"),
    ]

    print("Verifying user table columns...")
    for col_name, col_type in columns_to_ensure:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"  Added missing column: {col_name}")
        except mysql.connector.Error as err:
            if err.errno == 1060: # Duplicate column name (already exists)
                pass 
            else:
                print(f"  Error checking column {col_name}: {err}")

    # Ensure critical users column sizes (hashed password, email)
    try:
        cursor.execute("ALTER TABLE users MODIFY COLUMN password VARCHAR(255)")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users MODIFY COLUMN email VARCHAR(255)")
    except Exception:
        pass

    try:
        db_name = os.getenv("DB_NAME", "anveshan")
        cursor.execute(f"ALTER DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    except Exception:
        pass
    for t in [
        "users","events","otp_codes","personal_projects","project_requests","follows","project_comments",
        "faculty_collaborations","collaboration_requests","event_registrations","event_team_members",
        "clubs","club_announcements","team_requests","join_requests"
    ]:
        try:
            cursor.execute(f"ALTER TABLE {t} CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        except Exception:
            pass

    conn.commit()
    cursor.close()
    conn.close()
    print("\n✅ Database setup completed successfully!")

if __name__ == "__main__":
    create_database()
    setup_tables()
