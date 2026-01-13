# backend/db.py
import mysql.connector
import sys

try:
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",          # XAMPP default is EMPTY
        database="anveshan",
        port=3306              # or 3307 if changed
    )
except mysql.connector.Error as err:
    print(f"Error connecting to MySQL: {err}")
    print("Ensure that your MySQL server (e.g., XAMPP) is running and accessible on localhost:3306.")
    sys.exit(1)
