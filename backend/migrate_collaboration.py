import mysql.connector
import sys

try:
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="anveshan",
        port=3306
    )
    cursor = db.cursor()
    
    # 1. Add new columns to users table
    columns_to_add = [
        ("interests", "TEXT"),
        ("portfolio_url", "VARCHAR(255)"),
        ("medium_url", "VARCHAR(255)"),
        ("github_url", "VARCHAR(255)"), # Re-checking these just in case
        ("linkedin_url", "VARCHAR(255)"),
        ("bio", "TEXT"),
        ("skills", "TEXT")
    ]

    print("Updating users table...")
    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"Added column: {col_name}")
        except mysql.connector.Error as err:
            if err.errno == 1060: # Duplicate column name
                print(f"Column {col_name} already exists.")
            else:
                print(f"Error adding {col_name}: {err}")

    # 2. Create personal_projects table
    print("Creating personal_projects table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS personal_projects (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            title VARCHAR(255) NOT NULL,
            domain VARCHAR(100),
            description TEXT,
            tech_stack VARCHAR(255),
            looking_for VARCHAR(255),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    print("Table personal_projects created or already exists.")

    db.commit()
    cursor.close()
    db.close()
    print("Migration completed successfully.")

except Exception as e:
    print(f"Migration failed: {e}")
