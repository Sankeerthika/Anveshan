import mysql.connector

def check_schema():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="anveshan",
            port=3306
        )
        cursor = conn.cursor()
        
        tables = ['faculty_collaborations', 'collaboration_requests']
        for table in tables:
            print(f"\nChecking table: {table}...")
            try:
                cursor.execute(f"DESCRIBE {table}")
                columns = cursor.fetchall()
                print(f"Table {table} exists. Columns:")
                for col in columns:
                    print(f"  {col[0]} ({col[1]})")
            except mysql.connector.Error as err:
                print(f"Error checking {table}: {err}")
                
        conn.close()
        print("\nSchema check finished.")
    except Exception as e:
        print(f"\nSchema check failed: {e}")

if __name__ == "__main__":
    check_schema()
