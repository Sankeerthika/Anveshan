import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def check_users():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "anveshan"),
            port=int(os.getenv("DB_PORT", 3306))
        )
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id, email, name, role FROM users")
        users = cursor.fetchall()
        
        print(f"Total users: {len(users)}")
        print("-" * 50)
        print(f"{'ID':<5} {'Name':<20} {'Email':<30} {'Role'}")
        print("-" * 50)
        
        non_college_ids = []
        for user in users:
            print(f"{user['id']:<5} {user['name']:<20} {user['email']:<30} {user['role']}")
            email = user['email'].lower()
            # Heuristic for non-college emails: gmail, yahoo, hotmail, outlook, or just no .edu/.ac
            if '@gmail.com' in email or '@yahoo.com' in email or '@hotmail.com' in email or '@outlook.com' in email:
                non_college_ids.append(user['id'])
        
        print("-" * 50)
        print(f"Potential non-college users to delete: {non_college_ids}")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_users()
