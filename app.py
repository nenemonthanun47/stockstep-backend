from flask import Flask, request, jsonify
import sqlite3
from flask_cors import CORS
import os

app = Flask(__name__)
app.url_map.strict_slashes = False # Treat /route and /route/ the same
CORS(app, resources={r"/*": {"origins": "*"}}) # Robust CORS config

# create database
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    xp INTEGER DEFAULT 0,
    lesson1quiz1 INTEGER DEFAULT 0,
    lesson1quiz2 INTEGER DEFAULT 0,
    lesson2quiz1 INTEGER DEFAULT 0,
    lesson2quiz2 INTEGER DEFAULT 0,
    lesson3quiz1 INTEGER DEFAULT 0,
    lesson3quiz2 INTEGER DEFAULT 0
)
""")

    # Ensure columns exist (migration for existing databases)
    c.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in c.fetchall()]
    for col in ["lesson1quiz1", "lesson1quiz2", "lesson2quiz1", "lesson2quiz2", "lesson3quiz1", "lesson3quiz2"]:
        if col not in columns:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT 0")

    # Always ensure row id=1 exists and initialize all columns to 0 if they are NULL
    c.execute("INSERT OR IGNORE INTO users (id, xp) VALUES (1, 0)")
    quiz_cols = ["lesson1quiz1", "lesson1quiz2", "lesson2quiz1", "lesson2quiz2", "lesson3quiz1", "lesson3quiz2"]
    for col in quiz_cols:
        c.execute(f"UPDATE users SET {col} = 0 WHERE id=1 AND {col} IS NULL")
    
    # Ensure XP is also non-null
    c.execute("UPDATE users SET xp = 0 WHERE id=1 AND xp IS NULL")

    conn.commit()
    conn.close()

# Initialize the database when the app starts
init_db()

@app.route("/")
def home():
    return "Backend is running!"

@app.route("/get-xp")
def get_xp():
    data = get_user_data_logic()
    return jsonify({"xp": data.get("xp", 0)})

@app.route("/get-progress")
def get_progress():
    return jsonify(get_user_data_logic())

def get_user_data_logic():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=1")
    user_data = c.fetchone()
    conn.close()

    if user_data:
        data = dict(user_data)
        for key in ["lesson1quiz1", "lesson1quiz2", "lesson2quiz1", "lesson2quiz2", "lesson3quiz1", "lesson3quiz2"]:
            data[key] = int(data.get(key) or 0)

        xp = (
            data["lesson1quiz1"] +
            data["lesson1quiz2"] +
            data["lesson2quiz1"] +
            data["lesson2quiz2"] +
            data["lesson3quiz1"] +
            data["lesson3quiz2"]
        ) * 10

        data["xp"] = xp
        return data
    else:
        return {"xp": 0, "lesson1quiz1": 0, "lesson1quiz2": 0, "lesson2quiz1": 0, "lesson2quiz2": 0, "lesson3quiz1": 0, "lesson3quiz2": 0}

@app.route("/reset-progress", methods=["GET", "POST", "OPTIONS"])
def reset_all_progress():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})
    
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""UPDATE users SET 
                 xp=0, lesson1quiz1=0, lesson1quiz2=0, 
                 lesson2quiz1=0, lesson2quiz2=0, 
                 lesson3quiz1=0, lesson3quiz2=0 
                 WHERE id=1""")
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route("/save-quiz", methods=["GET", "POST", "OPTIONS"])
def save_quiz():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})
        
    if request.method == "GET":
        return jsonify({"message": "This endpoint requires a POST request with JSON data"}), 405

    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No JSON data provided"}), 400
        
    quiz = data["quiz"]   # e.g. "lesson1quiz1"
    value = data["value"] # 1 or 0

    # List of allowed column names to prevent SQL injection
    allowed_quizzes = [
        "lesson1quiz1", "lesson1quiz2", "lesson2quiz1", "lesson2quiz2", "lesson3quiz1", "lesson3quiz2"
    ]
    if quiz not in allowed_quizzes:
        return jsonify({"status": "error", "message": "Invalid quiz name"}), 400

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Ensure the row exists
    c.execute("INSERT OR IGNORE INTO users (id, xp, lesson1quiz1, lesson1quiz2, lesson2quiz1, lesson2quiz2, lesson3quiz1, lesson3quiz2) VALUES (1, 0, 0, 0, 0, 0, 0, 0)")

    # Update the specific quiz status
    c.execute(f"UPDATE users SET {quiz}=? WHERE id=1", (value,))

    # Recalculate XP directly in SQL for maximum reliability
    c.execute("""
        UPDATE users SET xp = (
            COALESCE(lesson1quiz1, 0) + COALESCE(lesson1quiz2, 0) + 
            COALESCE(lesson2quiz1, 0) + COALESCE(lesson2quiz2, 0) + 
            COALESCE(lesson3quiz1, 0) + COALESCE(lesson3quiz2, 0)
        ) * 10 WHERE id=1
    """)
    conn.commit()

    c.execute("SELECT xp FROM users WHERE id=1")
    new_xp = c.fetchone()[0]
    conn.close()

    return jsonify({"status": "saved", "xp": int(new_xp)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)