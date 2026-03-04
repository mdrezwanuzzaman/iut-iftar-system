import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect("students.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS students (
    student_id TEXT PRIMARY KEY,
    password_hash TEXT,
    budget INTEGER
)
""")

students = [
    ("240021127", generate_password_hash("rezwan"), 500),
    ("240041243", generate_password_hash("313131"), 400),
    ("2023001", generate_password_hash("student123"), 300),
]

cur.executemany("INSERT OR REPLACE INTO students VALUES (?,?,?)", students)
conn.commit()

cur.execute("SELECT COUNT(*) FROM students")
count = cur.fetchone()[0]
print(f"✅ Database initialized with {count} students")
conn.close()