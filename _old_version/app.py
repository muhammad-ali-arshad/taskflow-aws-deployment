"""
Task Manager - small Flask web app
Features: Signup, Login/Logout with JWT token, CRUD on tasks, SQLite local database
"""
import sqlite3
import datetime
from functools import wraps

import jwt
from flask import Flask, render_template, request, redirect, url_for, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "my-task-manager-super-secret-key-2026"   # used to sign JWT tokens
DATABASE = "database.db"


# ---------------- DATABASE ----------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    db.commit()
    db.close()


# ---------------- JWT HELPERS ----------------
def create_token(user_id, username):
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2),
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")


def login_required(f):
    """Checks the JWT token stored in the cookie before opening a page."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.cookies.get("token")
        if not token:
            flash("Please log in first.")
            return redirect(url_for("login"))
        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            g.user_id = data["user_id"]
            g.username = data["username"]
        except jwt.ExpiredSignatureError:
            flash("Session expired. Please log in again.")
            return redirect(url_for("login"))
        except jwt.InvalidTokenError:
            flash("Invalid token. Please log in again.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# ---------------- AUTH ROUTES ----------------
@app.route("/")
def home():
    return redirect(url_for("tasks"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        if not username or not password:
            flash("Username and password are required.")
            return redirect(url_for("signup"))
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                       (username, generate_password_hash(password)))
            db.commit()
        except sqlite3.IntegrityError:
            flash("Username already exists.")
            return redirect(url_for("signup"))
        flash("Account created! Please log in.")
        return redirect(url_for("login"))
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        user = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user["password"], password):
            token = create_token(user["id"], user["username"])
            resp = redirect(url_for("tasks"))
            resp.set_cookie("token", token, httponly=True, samesite="Lax")
            return resp
        flash("Wrong username or password.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    resp = redirect(url_for("login"))
    resp.delete_cookie("token")
    flash("You have been logged out.")
    return resp


# ---------------- TASK CRUD ----------------
@app.route("/tasks")
@login_required
def tasks():                                   # READ
    rows = get_db().execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY id DESC",
                            (g.user_id,)).fetchall()
    return render_template("tasks.html", tasks=rows, username=g.username)


@app.route("/tasks/add", methods=["POST"])
@login_required
def add_task():                                # CREATE
    title = request.form["title"].strip()
    description = request.form.get("description", "").strip()
    if title:
        db = get_db()
        db.execute("INSERT INTO tasks (user_id, title, description) VALUES (?, ?, ?)",
                   (g.user_id, title, description))
        db.commit()
        flash("Task added.")
    return redirect(url_for("tasks"))


@app.route("/tasks/edit/<int:task_id>", methods=["GET", "POST"])
@login_required
def edit_task(task_id):                        # UPDATE
    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?",
                      (task_id, g.user_id)).fetchone()
    if task is None:
        flash("Task not found.")
        return redirect(url_for("tasks"))
    if request.method == "POST":
        db.execute("UPDATE tasks SET title = ?, description = ?, status = ? WHERE id = ? AND user_id = ?",
                   (request.form["title"], request.form["description"],
                    request.form["status"], task_id, g.user_id))
        db.commit()
        flash("Task updated.")
        return redirect(url_for("tasks"))
    return render_template("edit.html", task=task, username=g.username)


@app.route("/tasks/delete/<int:task_id>", methods=["POST"])
@login_required
def delete_task(task_id):                      # DELETE
    db = get_db()
    db.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, g.user_id))
    db.commit()
    flash("Task deleted.")
    return redirect(url_for("tasks"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
