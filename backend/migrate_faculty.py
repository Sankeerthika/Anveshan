import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def create_faculty_tables():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "anveshan"),
            port=int(os.getenv("DB_PORT", 3306))
        )
        cursor = conn.cursor()
        
        # 1. Faculty Collaborations Table
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
                status ENUM('open', 'closed') DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (faculty_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        print("Created faculty_collaborations table.")

        # 2. Collaboration Requests Table (specific to faculty collaborations)
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
        print("Created collaboration_requests table.")
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_faculty_tables()