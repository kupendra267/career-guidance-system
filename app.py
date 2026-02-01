from flask import Flask, render_template, request, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "career_secret_key"

# ---------------- DATABASE ----------------
def get_db():
    return sqlite3.connect("career.db")

# ---------- CREATE TABLES ----------
conn = get_db()
cur = conn.cursor()

# Users table
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password_hash TEXT,
    role TEXT
)
""")

# Results table (APTITUDE BASED)
cur.execute("""
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    aptitude INTEGER,
    interest INTEGER,
    personality INTEGER,
    total INTEGER,
    career TEXT
)
""")

# Create default admin
cur.execute("SELECT * FROM users WHERE username='admin'")
if not cur.fetchone():
    cur.execute(
        "INSERT INTO users VALUES (NULL,?,?,?)",
        ("admin", generate_password_hash("admin123"), "admin")
    )

conn.commit()
conn.close()

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT password_hash, role FROM users WHERE username=?", (username,))
        user = cur.fetchone()

        # Auto-register student
        if not user and role == "student":
            cur.execute(
                "INSERT INTO users VALUES (NULL,?,?,?)",
                (username, generate_password_hash(password), "student")
            )
            conn.commit()
            conn.close()
            session["user"] = username
            session["role"] = "student"
            return redirect("/test")

        conn.close()

        if not user or role != user[1] or not check_password_hash(user[0], password):
            return "Invalid Login"

        session["user"] = username
        session["role"] = role

        return redirect("/admin" if role == "admin" else "/test")

    return render_template("login.html")

# ---------------- TEST PAGE ----------------
@app.route("/test")
def test():
    if "user" not in session:
        return redirect("/")
    return render_template("test.html")

# ---------------- RESULT ----------------
@app.route("/result", methods=["POST"])
def result():
    if "user" not in session:
        return redirect("/")

    aptitude = 0
    interest = 0
    personality = 0

    # Aptitude answers
    correct = {"q1": "b", "q2": "a", "q3": "c"}
    for q, ans in correct.items():
        if request.form.get(q) == ans:
            aptitude += 10

    # Interest
    for q in ["i1", "i2", "i3"]:
        if request.form.get(q) == "yes":
            interest += 10

    # Personality
    for q in ["p1", "p2", "p3"]:
        personality += int(request.form.get(q))

    total = aptitude + interest + personality

    if total >= 75:
        career = "AI / Data Science / Software Engineer"
    elif total >= 50:
        career = "Web Developer / Business Analyst"
    else:
        career = "Design / Arts / Humanities"

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO results
        (username, aptitude, interest, personality, total, career)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session["user"], aptitude, interest, personality, total, career))
    conn.commit()
    conn.close()

    return render_template(
        "result.html",
        aptitude=aptitude,
        interest=interest,
        personality=personality,
        total=total,
        career=career
    )

# ---------------- ADMIN ----------------
@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT career, COUNT(*) FROM results GROUP BY career")
    chart_data = cur.fetchall()
    cur.execute("SELECT * FROM results")
    table_data = cur.fetchall()
    conn.close()

    return render_template("admin.html", chart_data=chart_data, table_data=table_data)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)