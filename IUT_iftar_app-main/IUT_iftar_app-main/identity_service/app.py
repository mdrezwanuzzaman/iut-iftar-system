from flask import Flask, request, jsonify
import sqlite3
import jwt
import time
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

app = Flask(__name__)
SECRET = "iftar-secret-key"

login_attempts = {}

def get_connection():
    return sqlite3.connect("students.db")

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def check_rate_limit(student_id):
    now = datetime.now()
    if student_id not in login_attempts:
        login_attempts[student_id] = {'count': 1, 'first_attempt': now}
        return True
    attempts = login_attempts[student_id]
    time_diff = (now - attempts['first_attempt']).total_seconds()
    if time_diff > 60:
        login_attempts[student_id] = {'count': 1, 'first_attempt': now}
        return True
    if attempts['count'] >= 3:
        return False
    attempts['count'] += 1
    return True

@app.route("/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json
    student_id = data.get("student_id")
    password = data.get("password")
    if not check_rate_limit(student_id):
        return jsonify({"error": "Too many attempts. Please wait 60 seconds.", "rate_limited": True}), 429
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT password_hash, budget FROM students WHERE student_id=?", (student_id,))
    row = cur.fetchone()
    conn.close()
    if not row or not check_password_hash(row[0], password):
        return jsonify({"error": "Invalid Credentials"}), 401
    if student_id in login_attempts:
        del login_attempts[student_id]
    token = jwt.encode({"student_id": student_id, "exp": time.time() + 3600}, SECRET, algorithm="HS256")
    return jsonify({"token": token, "budget": row[1]})

@app.route("/budget/<student_id>", methods=["GET", "OPTIONS"])
def get_budget(student_id):
    if request.method == "OPTIONS":
        return jsonify({}), 200
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT budget FROM students WHERE student_id=?", (student_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Student not found"}), 404
    return jsonify({"budget": row[0]})

@app.route("/deduct", methods=["POST", "OPTIONS"])
def deduct():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json
    student_id = data.get("student_id")
    amount = data.get("amount")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT budget FROM students WHERE student_id=?", (student_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Student not found"}), 404
    if row[0] < amount:
        conn.close()
        return jsonify({"error": "Insufficient budget"}), 400
    cur.execute("UPDATE students SET budget = budget - ? WHERE student_id=?", (amount, student_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "Budget Deducted", "remaining": row[0] - amount})

@app.route("/add_budget", methods=["POST", "OPTIONS"])
def add_budget():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json
    student_id = data.get("student_id")
    amount = data.get("amount")
    if not student_id or not amount:
        return jsonify({"error": "Missing fields"}), 400
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT budget FROM students WHERE student_id=?", (student_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Student not found"}), 404
    new_budget = row[0] + amount
    cur.execute("UPDATE students SET budget = ? WHERE student_id=?", (new_budget, student_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "Budget Added", "new_budget": new_budget})

@app.route("/add_student", methods=["POST", "OPTIONS"])
def add_student():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json
    student_id = data.get("student_id")
    password = data.get("password")
    budget = data.get("budget", 500)
    if not student_id or not password:
        return jsonify({"error": "Missing fields"}), 400
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO students VALUES (?,?,?)", (student_id, generate_password_hash(password), budget))
        conn.commit()
        result = jsonify({"status": "Student Added"})
    except sqlite3.IntegrityError:
        result = jsonify({"error": "Student ID exists"}), 400
    finally:
        conn.close()
    return result

@app.route("/remove_student", methods=["POST", "OPTIONS"])
def remove_student():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json
    student_id = data.get("student_id")
    if not student_id:
        return jsonify({"error": "Missing student_id"}), 400
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE student_id=?", (student_id,))
    conn.commit()
    conn.close()
    if student_id in login_attempts:
        del login_attempts[student_id]
    return jsonify({"status": "Student Removed"})

@app.route("/students", methods=["GET", "OPTIONS"])
def get_all_students():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT student_id, budget FROM students ORDER BY student_id")
    rows = cur.fetchall()
    conn.close()
    return jsonify([{"student_id": r[0], "budget": r[1]} for r in rows])

@app.route("/health", methods=["GET", "OPTIONS"])
def health():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    return jsonify({"service": "identity", "status": "online", "time": time.time()})

if __name__ == "__main__":
    print("=" * 50)
    print("Identity Service Running on http://127.0.0.1:5001")
    print("=" * 50)
    app.run(host="127.0.0.1", port=5001, debug=True, threaded=True)