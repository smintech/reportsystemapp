from flask import Flask, render_template, g, request, redirect, url_for, session , flash, jsonify, make_response
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import timedelta
import secrets
import psycopg2
import psycopg2.extras
from psycopg2 import IntegrityError
import uuid
import hashlib
app = Flask(__name__)
app.secret_key = "admin_logged_in_77"
app.permanent_session_lifetime = timedelta(days=1)
RATEL_DB_URL = os.getenv("DATABASE_URL")
def get_db():
    if "db" not in g:
        g.db = psycopg2.connect(RATEL_DB_URL, sslmode="require")
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db:
        db.close()
        
def init_db():
    """Create tables if missing (users + reports). Run once at startup."""
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
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id SERIAL PRIMARY KEY,
        anon_id TEXT,
        fingerprint TEXT,
        reporter_email TEXT,
        tracking_id TEXT,
        category TEXT NOT NULL,
        details TEXT NOT NULL,
        evidence TEXT,
        status TEXT NOT NULL DEFAULT 'Pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_reports_active ON reports (anon_id, fingerprint, reporter_email, status);
    """)
    cur.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS unique_admin ON users((CASE WHEN role='admin' THEN 1 ELSE NULL END));
    """)
    
    db.commit()
    cur.close()

@app.route("/", methods=["GET", "POST"])
def home():
    tracking_id = None
    
    db = get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        if request.method == "POST":
            reporter_email = request.form.get("reporter_email") or None
            fingerprint = request.form.get("fingerprint") or None
            category = request.form.get("category", "").strip()
            details = request.form.get("details", "").strip()
            evidence = request.form.get("evidence", "").strip() or None

            if not category or not details:
                flash("Category and details are required.", "error")
                return redirect(url_for("home"))

            # Get or create anon_id cookie
            anon_id = request.cookies.get("anon_id")
            if not anon_id:
                anon_id = "anon_" + str(uuid.uuid4())

            # Check for existing active tracking
            active_tracking = None
            if reporter_email:
                cur.execute("""
                    SELECT tracking_id FROM reports
                    WHERE reporter_email = %s AND status IN ('Pending', 'In Progress')
                    ORDER BY created_at DESC LIMIT 1
                """, (reporter_email,))
                row = cur.fetchone()
                if row:
                    active_tracking = row["tracking_id"]

            if not active_tracking and anon_id and fingerprint:
                cur.execute("""
                    SELECT tracking_id FROM reports
                    WHERE anon_id = %s AND fingerprint = %s AND status IN ('Pending', 'In Progress')
                    ORDER BY created_at DESC LIMIT 1
                """, (anon_id, fingerprint))
                row = cur.fetchone()
                if row:
                    active_tracking = row["tracking_id"]

            tracking_id = active_tracking if active_tracking else str(uuid.uuid4())

            # Insert new report
            cur.execute("""
                INSERT INTO reports
                (anon_id, fingerprint, reporter_email, tracking_id, category, details, evidence, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'Pending', NOW(), NOW())
            """, (anon_id, fingerprint, reporter_email, tracking_id, category, details, evidence))
            db.commit()

            # Prepare response with cookie
            response = make_response(redirect(url_for("home")))
            response.set_cookie("anon_id", anon_id, max_age=90*24*3600, httponly=True, samesite="Lax")
            flash(f"Report submitted. Tracking ID: {tracking_id}", "success")
            return response

    # GET request
    return render_template("index.html", tracking_id=tracking_id)
    
def get_or_create_anon_cookie():
    anon_id = request.cookies.get("anon_id")
    if not anon_id:
        anon_id = "anon_" + str(uuid.uuid4())
    return anon_id
    
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
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE email=%s AND role='admin'", (email,))
            admin = cur.fetchone()
            if admin and check_password_hash(admin["password_hash"], password):
                session["admin_logged_in"] = True
                session["dashboard_token"] = secrets.token_hex(16)
                session.permanent = True if remember else False
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
    cur.execute("SELECT * FROM reports ORDER BY created_at DESC LIMIT 100")
    reports = cur.fetchall()
    cur.close()
    return render_template("admin_dashboard.html", users=users, reports=reports)
    
@app.route("/users")
@adminonly
def list_users():
    db = get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
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
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            if role.lower() == "admin":
                cur.execute("SELECT * FROM users WHERE role='admin'")
                existing_admin = cur.fetchone()
                if existing_admin:
                    flash("An admin already exists!.", "error")
                    return redirect(url_for("admin_dashboard"))
            try:
                cur.execute(
                    "INSERT INTO users (email, password_hash, role) VALUES (%s, %s, %s)",
                    (email, hashed_password, role)
                )
                db.commit()
                flash("User added successfully!", "success")
            except psycopg2.IntegrityError:
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
    with db.cursor() as cur:
        cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
        db.commit()
        flash("User deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))
    
@app.route("/staff_login", methods=["GET", "POST"])
def staff_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        remember = "remember" in request.form

        db = get_db()
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE email = %s AND role != 'admin'", (email,))
            user = cur.fetchone()
            if user and check_password_hash(user["password_hash"], password):
                session["staff_logged_in"] = True
                session["staff_role"] = user["role"]
                session["staff_email"] = user["email"]
                session.permanent = True if remember else False
                flash(f"Welcome {user['role'].capitalize()}!", "success")
                return redirect(url_for("staff_dashboard"))
            else:
                flash("Invalid credentials!", "error")

    return render_template("staff_login.html")

@app.route("/staff_dashboard")
def staff_dashboard():
    if not session.get("staff_logged_in"):
        flash("Please log in as staff first!", "error")
        return redirect(url_for("staff_login"))
        
        db = get_db
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM reports ORDER BY created_at DESC LIMIT 200")
        reports = cur.fetchall()
        cur.close()
        return render_template("staff_dashboard.html",
                           staff_email=session.get("staff_email", "Unknown"),
                            staff_role=session.get("staff_role", "Staff"),
                            reports=reports)
    
@app.route("/admin_logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    flash("Logged out successfully.", "success")
    return redirect(url_for("admin_login"))

@app.route("/staff_logout")
def staff_logout():
    session.pop("staff_logged_in", None)
    session.pop("staff_email", None)
    session.pop("staff_role", None)
    flash("Logged out successfully.", "success")
    return redirect(url_for("staff_login"))
    
@app.route("/track/<tracking_id>")
def track_status(tracking_id):
    db = get_db()
    cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT id, category, status, created_at, updated_at FROM reports WHERE tracking_id=%s ORDER BY created_at ASC", (tracking_id,))
    rows = cur.fetchall()
    cur.close()
    if not rows:
        return jsonify({"ok": False, "msg": "No such existing case for that tracking id"}), 404
        
    summary = {
        "tracking_id": tracking_id,
        "count": len(rows),
        "status": rows[-1]["status"],
        "history": [{"id": r["id"], "category": r["category"], "status": r["status"], "created_at": r["created_at"].isoformat()} for r in rows]
    }
    return jsonify({"ok": True, "report": summary})
    
if __name__ == "__main__":
     with app.app_context():
         init_db()
     app.run(debug=True)