from flask import Flask, render_template, g, request, redirect, url_for, session , flash
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import timedelta
import secrets
import psycopg2
import psycopg2.extras
from psycopg2 import IntegrityError
app = Flask(__name__)
app.secret_key = "admin_logged_in_77"
app.permanent_session_lifetime = timedelta(days=1)
RATEL_DB_URL = os.getenv("RATEL_DB_URL")
def get_db():
    if "db" not in g:
        g.db = psycopg2.connect(RATEL_DB_URL)
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db:
        db.close()
        
def init_db():
    """Initialize database and default admin"""
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    db.commit()
    cur.close()

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
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cur.execute(
            "SELECT * FROM users WHERE email=%s AND role='admin'",
            (email,)
        )
        admin = cur.fetchone()

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
    cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cur.execute("SELECT * FROM users ORDER BY id ASC")
    users = cur.fetchall()
    return render_template("admin_dashboard.html", users=users)
    
@app.route("/users")
@adminonly
def list_users():
    db = get_db()
    cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cur.execute("SELECT * FROM users ORDER BY id ASC")
    users = cur.fetchall()
    return render_template("users.html", users=users)
    
@app.route("/add_user", methods=["GET", "POST"])
@adminonly
def add_user():
    if request.method == "POST":
        email = request.form["email"]
        role = request.form["role"]
        password = request.form["password"]
        
        hashed_password = generate_password_hash(password)

        db = get_db()
        cur = db.cursor()
        
        try:
            cur.execute(
                "INSERT INTO users (email, password_hash, role) VALUES (%s, %s, %s)",
                (email, hashed, role)
            )
            
            db.commit()
            flash("User added successfully!", "success")
        except IntegrityError:
            db.rollback()
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
    cur = db.cursor
    
    cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
    db.commit()
    flash("User deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))
    
@app.route("/admin_logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    flash("Logged out successfully.", "success")
    return redirect(url_for("admin_login"))
    
if __name__ == "__main__":
    with app.app_context():
    init_db()
    app.run(debug=True)