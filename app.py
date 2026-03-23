from flask import Flask, request, jsonify
import sqlite3
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# create database
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    xp INTEGER,
    lesson1quiz1 INTEGER,
    lesson1quiz2 INTEGER,
    lesson2quiz1 INTEGER,
    lesson2quiz2 INTEGER,
    lesson3quiz1 INTEGER,
    lesson3quiz2 INTEGER
)
""")

    # Ensure columns exist (migration for existing databases)
    c.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in c.fetchall()]
    for col in ["lesson1quiz1", "lesson1quiz2", "lesson2quiz1", "lesson2quiz2", "lesson3quiz1", "lesson3quiz2"]:
        if col not in columns:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} INTEGER")

    # insert default user if not exist
    c.execute("SELECT * FROM users WHERE id=1")
    if not c.fetchone():
        c.execute("INSERT INTO users (id, xp, lesson1quiz1, lesson1quiz2, lesson2quiz1, lesson2quiz2, lesson3quiz1, lesson3quiz2) VALUES (1, 0, NULL, NULL, NULL, NULL, NULL, NULL)")

    conn.commit()
    conn.close()

@app.route("/")
def home():
    return "Backend is running!"

@app.route("/save-xp", methods=["POST"])
def save_xp():
    data = request.json
    xp = data["xp"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("UPDATE users SET xp=? WHERE id=1", (xp,))
    conn.commit()
    conn.close()

    return jsonify({"status": "success"})

@app.route("/get-xp")
def get_xp():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT xp FROM users WHERE id=1")
    xp = c.fetchone()[0]

    conn.close()

    return {"xp": xp}

@app.route("/get-progress")
def get_progress():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=1")
    user_data = c.fetchone()
    conn.close()
    if user_data:
        return jsonify(dict(user_data))
    else:
        # This case should be handled by init_db, but as a fallback:
        return jsonify({"xp": 0, "lesson1quiz1": None, "lesson1quiz2": None, "lesson2quiz1": None, "lesson2quiz2": None, "lesson3quiz1": None, "lesson3quiz2": None})

@app.route("/reset-progress", methods=["POST"])
def reset_all_progress():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    # Using NULL is better to represent "not answered"
    c.execute("""UPDATE users SET 
                 xp=0, lesson1quiz1=NULL, lesson1quiz2=NULL, 
                 lesson2quiz1=NULL, lesson2quiz2=NULL, 
                 lesson3quiz1=NULL, lesson3quiz2=NULL 
                 WHERE id=1""")
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route("/save-quiz", methods=["POST"])
def save_quiz():
    data = request.json

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

    # Use the safe f-string now that we've validated the column
    query = f"UPDATE users SET {quiz}=? WHERE id=1"
    c.execute(query, (value,))

    conn.commit()
    conn.close()

    return {"status": "saved"}

if __name__ == "__main__":
    app.run()