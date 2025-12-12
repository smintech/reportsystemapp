from flask import Flask, render_template, g, request, redirect, url_for, session , flash, jsonify, make_response, send_from_directory, abort
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime
from datetime import timedelta
import secrets
import psycopg2
import psycopg2.extras
from psycopg2 import IntegrityError
import uuid
import hashlib
import random
import json
import cloudinary
import cloudinary.uploader
import cloudinary.api
app = Flask(__name__)
app.secret_key = "admin_logged_in_77"
app.permanent_session_lifetime = timedelta(days=1)
cloudinary.config(
    cloud_name="dowpqktts",
    api_key="819877624561655",
    api_secret="OfGF1Kc261bOJa6dBUMDmk5p2po"
    )
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx', 'mp4'}  # Extend as needed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
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
        anon_id INTEGER NULL,
        fingerprint TEXT,
        reporter_email TEXT,
        tracking_id TEXT,
        category_group TEXT NOT NULL,
        options_group TEXT NOT NULL,
        details TEXT NOT NULL,
        evidence TEXT,
        status TEXT NOT NULL DEFAULT 'Pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS report_notes (
    id SERIAL PRIMARY KEY,
    report_id INT NOT NULL,
    note TEXT NOT NULL,
    added_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
def generate_unique_anon_id(cur):
    while True:
        anon_id = random.randint(100000, 999999)
        cur.execute("SELECT 1 FROM reports WHERE anon_id = %s LIMIT 1", (anon_id,))
        if not cur.fetchone():
            return anon_id
def get_or_create_cookie_uuid(cur):
    """
    Returns a tuple: (anon_id:int, cookie_uuid:str)
    Ensures same sender always gets same anon_id if cookie exists.
    """
    cookie_uuid = request.cookies.get("cookie_uuid")
    if cookie_uuid:
        # Lookup the last anon_id for this cookie in reports table
        cur.execute("""
            SELECT anon_id FROM reports
            WHERE cookie_uuid = %s
            ORDER BY created_at DESC LIMIT 1
        """, (cookie_uuid,))
        row = cur.fetchone()
        if row:
            return row["anon_id"], cookie_uuid
        else:
            # Cookie exists but no previous report → create new anon_id
            anon_id = generate_unique_anon_id(cur)
            return anon_id, cookie_uuid

    # No cookie → create new anon_id and cookie UUID
    anon_id = generate_unique_anon_id(cur)
    cookie_uuid = str(uuid.uuid4())
    return anon_id, cookie_uuid
    
@app.route("/", methods=["GET", "POST"])
def home():
    tracking_id = None
    db = get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:

        if request.method == "POST":
            reporter_email = request.form.get("reporter_email") or None
            fingerprint = request.form.get("fingerprint") or None
            category_group = request.form.get("category_group", "").strip()
            options_group = request.form.get("options_group","").strip()
            details = request.form.get("details", "").strip()
            evidence_link = request.form.get("evidence") or None  # link text input

            if not category_group or not details:
                flash("Category and details are required.", "error")
                return redirect(url_for("home"))

            # Get anon cookie or create new one
            anon_id, cookie_uuid = get_or_create_cookie_uuid(cur)
            tracking_id = str(uuid.uuid4())
            # ------------------- HANDLE FILES -------------------
            # --- FILE UPLOAD ---
            files = request.files.getlist("fileinput")
            uploaded_urls = []
            evidence_str = None
            if files:
                for file in files:
                    if file and allowed_file(file.filename):
                        upload_result = cloudinary.uploader.upload(
                        file,
                        resource_type="auto"
                        )
                        uploaded_urls.append(upload_result["secure_url"])

            # Combine file names or use evidence_link
            evidence_list = uploaded_urls.copy()
            if evidence_link:
                evidence_list.append(evidence_link)
            evidence_json = json.dumps(evidence_list)

            # ------------------- INSERT INTO DB -------------------
            cur.execute("""
                INSERT INTO reports
                (anon_id, cookie_uuid, fingerprint, category_group, options_group, reporter_email, tracking_id, details, evidence, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending', NOW(), NOW())
            """, (anon_id, cookie_uuid, fingerprint, category_group, options_group, reporter_email, tracking_id, details, evidence_json))
            
            db.commit()

            # ------------------- SEND RESPONSE + COOKIE -------------------
            response = make_response(redirect(url_for("home")))
            expires = datetime(2038, 12, 19)
            response.set_cookie("cookie_uuid", cookie_uuid, expires=expires, httponly=True, samesite="Lax")
            response.set_cookie("anon_id", str(anon_id), expires=expires, httponly=True, samesite="Lax")

            flash(f"Report submitted. Tracking ID: {tracking_id}", "success")
            return response

        # ------------------- GET REQUEST -------------------
        return render_template("index.html", tracking_id=tracking_id)
    
def parse_evidence(evidence_value):
    """
    Returns a dict containing:
      files → list of dicts {id, value} for multiple items
      link → first link if only one
      single → first file if only one
    """
    if not evidence_value:
        return {"files": None, "link": None, "single": None}

    # Convert JSON string to Python object
    try:
        if isinstance(evidence_value, str):
            evidence_list = json.loads(evidence_value.replace("'", '"'))
        else:
            evidence_list = evidence_value
    except (TypeError, json.JSONDecodeError):
        # fallback if somehow string is stored
        evidence_list = [evidence_value]
    files = []
    link = None
    
    for idx, item in enumerate(evidence_list):
        if str(item).startswith("http"):
            link = str(item)
        else:
            files.append({"id": idx + 1, "value": str(item)})
            
    if len(files) == 1 and not link:
        single = files[0]["value"]
    else:
        single = None
    # Multiple items
    return {"files": files if files else None, "link": link, "single": single}
    
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
    cur.execute("SELECT * FROM reports ORDER BY created_at DESC LIMIT 20")
    reports = cur.fetchall()
    
    for i, r in enumerate(reports):
        reports[i] = dict(r)  # convert psycopg2 row to regular dict
        reports[i]['evidence_parsed'] = parse_evidence(reports[i]['evidence'])
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
    
@app.route("/delete/<tracking_id>", methods=["POST"])
def delete_report(tracking_id):
    if not session.get("staff_logged_in"):
        flash("Please log in first.", "error")
        return redirect(url_for("staff_login"))

    db = get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM reports WHERE tracking_id = %s", (tracking_id,))
        db.commit()

    flash("Report deleted successfully.", "success")
    return redirect(url_for("staff_dashboard"))
    
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
                session["staff_id"] = user["id"]
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
        
    role = session.get("staff_role")
    user_id = session.get("staff_id")
    email = session.get("staff_email")
        
    db = get_db()
    cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
    if role == "vdmratelking":
        cur.execute("SELECT * FROM users ORDER BY id ASC")
        users = cur.fetchall()
        cur.execute("SELECT * FROM reports ORDER BY created_at DESC LIMIT 20")
        reports = cur.fetchall()
            
    else:
        users = None
        cur.execute("SELECT * FROM reports WHERE assigned_staff_id=%s ORDER BY created_at DESC", (user_id,))
        reports = cur.fetchall()
        
    for i, r in enumerate(reports):
        reports[i] = dict(r)  # convert psycopg2 row to regular dict
        reports[i]['evidence_parsed'] = parse_evidence(reports[i]['evidence'])
        
    cur.close()
        
    return render_template("staff_dashboard.html",
                           staff_email=session.get("staff_email", "Unknown"),
                           staff_role=session.get("staff_role", "Staff"),
                           users=users,
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
    
@app.route("/reports")
@adminonly
def reports_page():
    db = get_db()
    cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT * FROM reports ORDER BY created_at DESC")
    reports = cur.fetchall()
    reports_list = []
    for r in reports:
        r = dict(r)
        r['evidence_parsed'] = parse_evidence(r['evidence'])
        reports_list.append(r)

    cur.execute("SELECT email, role FROM users")
    users = cur.fetchall()

    cur.close()
    return render_template("reports.html", reports=reports_list, users=users)
    
@app.post("/assign/<int:rid>")
@adminonly
def assign_to_user(rid):
    user_email = request.form.get("user_email")
    if not user_email:
        flash("Select a user to assign!", "error")
        return redirect(url_for("reports_page"))

    db = get_db()
    cur = db.cursor()
    
    cur.execute("SELECT id FROM users WHERE email=%s", (user_email,))
    row = cur.fetchone()
    if not row:
        flash("Invalid user!", "error")
        cur.close()
        return redirect(url_for("reports_page"))

    user_id = row[0]

    cur.execute("UPDATE reports SET assigned_staff_id=%s WHERE id=%s", (user_id, rid))
    db.commit()
    cur.close()

    flash("Report assigned successfully!", "success")
    return redirect(url_for("reports_page"))
    
@app.post("/assign_self/<int:rid>")
@adminonly
def assign_to_self(rid):
    admin_email = session.get("staff_email") or "admin"

    db = get_db()
    cur = db.cursor()
    
    cur.execute("SELECT id FROM users WHERE email=%s", (admin_email,))
    row = cur.fetchone()
    if not row:
        flash("Admin not exist!", "error")
        cur.close()
        return redirect(url_for("reports_page"))

    user_id = row[0]

    cur.execute("UPDATE reports SET assigned_staff_id=%s WHERE id=%s", (user_id, rid))
    db.commit()
    cur.close()

    flash("You are now assigned to this case!", "success")
    return redirect(url_for("reports_page"))
    
@app.post("/status/<int:rid>")
def change_status(rid):
    if not session.get("admin_logged_in") and not session.get("staff_logged_in"):
        flash("Not authorized!", "error")
        return redirect(url_for("staff_login"))

    status = request.form.get("status")

    if status not in ["Pending", "In Progress", "Resolved", "Rejected", "Closed"]:
        flash("Invalid status!", "error")
        return redirect(url_for("reports_page"))

    db = get_db()
    cur = db.cursor()

    cur.execute("UPDATE reports SET status=%s, updated_at=NOW() WHERE id=%s", (status, rid))
    db.commit()
    cur.close()

    flash("Status updated.", "success")
    return redirect(url_for("reports_page"))
    
@app.post("/staff_change_status/<int:rid>")
def change_status_staff(rid):
    if not session.get("staff_logged_in"):
        flash("Login required", "error")
        return redirect(url_for("staff_login"))

    status = request.form.get("status")
    staff_id = session.get("staff_id")
    role = session.get("staff_role")

    db = get_db()
    cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # Only allow staff to update assigned reports
    cur.execute("SELECT assigned_staff_id FROM reports WHERE id=%s", (rid,))
    report = cur.fetchone()
    if not report or (report['assigned_staff_id'] != staff_id and role != "vdmratelking"):
        flash("You are not assigned to this report!", "error")
        cur.close()
        return redirect(url_for("staff_dashboard"))

    cur.execute("UPDATE reports SET status=%s, updated_at=NOW() WHERE id=%s", (status, rid))
    db.commit()
    cur.close()
    flash("Status updated.", "success")
    return redirect(url_for("staff_dashboard"))
    
@app.route("/report/<int:rid>")
def view_report(rid):
    db = get_db()
    cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT * FROM reports WHERE id=%s", (rid,))
    row = cur.fetchone()
    if not row:
        flash("Report not found.", "error")
        return redirect(url_for("home"))
        
    report = dict(row)
    report['evidence_list'] = parse_evidence(report['evidence'])
    
    cur.execute("SELECT * FROM report_notes WHERE report_id=%s ORDER BY created_at DESC", (rid,))
    notes = cur.fetchall()
    
    cur.close()
    return render_template("view_report.html", report=report, notes=notes)
    
@app.post("/add_note/<int:rid>")
def add_note(rid):
    if not session.get("admin_logged_in") and not session.get("staff_logged_in"):
        flash("Not authorized!", "error")
        return redirect(url_for("staff_login"))

    note = request.form.get("note")

    db = get_db()
    cur = db.cursor()

    cur.execute("""
        INSERT INTO report_notes (report_id, note, added_by)
        VALUES (%s, %s, %s)
    """, (rid, note, session.get("staff_email", "admin")))

    db.commit()
    cur.close()

    flash("Note added.", "success")
    return redirect(url_for("view_report", rid=rid))
    
@app.post("/staff_assign_self/<int:rid>")
def assign_to_self_staff(rid):
    if not session.get("staff_logged_in"):
        flash("Login required", "error")
        return redirect(url_for("staff_login"))

    email = session.get("staff_email")
    
    db = get_db()
    cur = db.cursor()
    
    cur.execute("SELECT id FROM users WHERE email=%s", (email,))
    row = cur.fetchone()
    if not row:
        flash("Staff not exist!", "error")
        cur.close()
        return redirect(url_for("reports_page"))

    user_id = row[0]

    cur.execute("UPDATE reports SET assigned_staff_id=%s WHERE id=%s", (user_id, rid))
    db.commit()
    cur.close()
    flash("You are now assigned to this report!", "success")
    return redirect(url_for("staff_dashboard"))
    
@app.post("/staff_assign_other/<int:rid>")
def assign_to_other_staff(rid):
    if not session.get("staff_logged_in") or session.get("staff_role") != "vdmratelking":
        flash("Unauthorized!", "error")
        return redirect(url_for("staff_dashboard"))

    user_email = request.form.get("user_email")
    if not user_email:
        flash("Select a user!", "error")
        return redirect(url_for("staff_dashboard"))

    db = get_db()
    cur = db.cursor()
    
    cur.execute("SELECT id FROM users WHERE email=%s", (user_email,))
    row = cur.fetchone()
    if not row:
        flash("Staff not exist!", "error")
        cur.close()
        return redirect(url_for("reports_page"))

    user_id = row[0]
    
    cur.execute("UPDATE reports SET assigned_staff_id=%s WHERE id=%s", (user_id, rid))
    db.commit()
    cur.close()
    flash("Report assigned successfully!", "success")
    return redirect(url_for("staff_dashboard"))
    
if __name__ == "__main__":
     with app.app_context():
         init_db()
     app.run(debug=True)