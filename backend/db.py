# backend/db.py
import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  # your MySQL password
    database="anveshan",
    port=3306
)
