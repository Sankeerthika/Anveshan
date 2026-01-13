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
    
    # List of columns to add
    columns_to_add = [
        ("profile_photo", "VARCHAR(255) DEFAULT 'default.jpg'"),
        ("bio", "TEXT"),
        ("skills", "TEXT"),
        ("linkedin_url", "VARCHAR(255)"),
        ("github_url", "VARCHAR(255)"),
        ("branch", "VARCHAR(50)"),
        ("year", "VARCHAR(20)"),
        ("section", "VARCHAR(10)")
    ]

    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"Added column: {col_name}")
        except mysql.connector.Error as err:
            if err.errno == 1060: # Duplicate column name
                print(f"Column {col_name} already exists.")
            else:
                print(f"Error adding {col_name}: {err}")

    db.commit()
    cursor.close()
    db.close()
    print("Migration completed.")

except Exception as e:
    print(f"Migration failed: {e}")
