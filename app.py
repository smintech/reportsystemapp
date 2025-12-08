from flask import Flask, render_template, g, request, redirect, url_for, session , flash
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import timedelta
import secrets
app = Flask(__name__)
app.secret_key = "admin_logged_in_77"
app.permanent_session_lifetime = timedelta(days=30)
DATABASE = "database.db"
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        print(f"Flask app database path: {os.path.abspath(DATABASE)}")
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()
        
def init_db():
    """Initialize database and default admin"""
    db = sqlite3.connect(DATABASE)
    db.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
admin_email = "admin@ratel.com"
admin_password_hash = generate_password_hash("admin7070")
exists = db.execute("SELECT * FROM user WHERE email = ?", (admin_email,)).fetchone()
if not exists:
    db.execute("INSERT INTO user (email, password_hash, role) VALUES (?, ?, ?)",
    (admin_email, admin_password_hash, "admin"))
    db.commit()
    db.close()

@app.route("/")
def home():
    return render_template("index.html")
    
def adminonly(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("You must log in as admin first!", "error")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function
    
def admin_dashboard_only(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("You must log in as admin first!", "error")
            return redirect(url_for("admin_login"))
        
        # Check if dashboard token exists
        if not session.get("dashboard_token"):
            flash("You can only access this page via the dashboard!", "error")
            return redirect(url_for("admin_dashboard"))

        return f(*args, **kwargs)
    return decorated
    
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        remember = "remember" in request.form

        db = get_db()
        admin = db.execute(
            "SELECT * FROM user WHERE email = ? AND role = 'admin'",
            (email,)
        ).fetchone()

        if admin and check_password_hash(admin["password_hash"], password):
            if remember:
                session.permanent = True
            else:
                session.permanent = False
            session["admin_logged_in"] = True
            flash("Welcome, admin!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid admin credentials!", "error")

    return render_template("admin_login.html")
    
@app.route("/admin")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        flash("Please log in as admin first!", "error")
        return redirect(url_for("admin_login"))
        
    session["dashboard_token"] = secrets.token_hex(16)

    db = get_db()
    users = db.execute("SELECT * FROM user").fetchall()
    return render_template("admin_dashboard.html", users=users)
    
@app.route("/users")
@adminonly
def list_users():
    db = get_db()
    users = db.execute("SELECT * FROM user").fetchall()
    return render_template("users.html", users=users)
    
@app.route("/add_user", methods=["GET", "POST"])
@adminonly
def add_user():
    if request.method == "POST":
        email = request.form["email"]
        role = request.form["role"]
        password = request.form["password"]

        db = get_db()
        hashed_password = generate_password_hash(password)
        try:
            db.execute(
                "INSERT INTO user (email, password_hash, role) VALUES (?, ?, ?)",
                (email, hashed_password, role)
            )
            db.commit()
            flash("User added successfully!", "success")
        except sqlite3.IntegrityError:
            flash("User with this email already exists!", "error")
        return redirect(url_for("admin_dashboard"))

    return render_template("add_users.html")

@app.route("/delete_user/<int:user_id>", methods=["POST"])
@adminonly
def delete_user(user_id):
    if not session.get("admin_logged_in"):
        flash("Please log in first.", "error")
        return redirect(url_for("admin_login"))

    db = get_db()
    db.execute("DELETE FROM user WHERE id = ?", (user_id,))
    db.commit()
    flash("User deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))
    
@app.route("/admin_logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    flash("Logged out successfully.", "success")
    return redirect(url_for("admin_login"))
    
if __name__ == "__main__":
    init_db()
    app.run(debug=True)