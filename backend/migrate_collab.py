import mysql.connector
import sys

# Direct connection config
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "anveshan",
    "port": 3306
}

def migrate():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # 1. Project Requests (Collaboration)
        print("Creating project_requests table...")
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

        # 2. Follows
        print("Creating follows table...")
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

        # 3. Project Comments
        print("Creating project_comments table...")
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

        conn.commit()
        cursor.close()
        conn.close()
        print("Migration successful!")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
