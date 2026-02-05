import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def delete_users():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "anveshan"),
            port=int(os.getenv("DB_PORT", 3306))
        )
        cursor = conn.cursor()
        
        # IDs identified as non-college (gmail)
        ids_to_delete = [1, 4, 5, 6, 10]
        
        if not ids_to_delete:
            print("No users to delete.")
            return

        format_strings = ','.join(['%s'] * len(ids_to_delete))
        query = f"DELETE FROM users WHERE id IN ({format_strings})"
        
        cursor.execute(query, tuple(ids_to_delete))
        conn.commit()
        
        print(f"Deleted {cursor.rowcount} users.")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    delete_users()