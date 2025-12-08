from flask import Flask, render_template, g, request, redirect, url_for, session , flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
app = Flask(__name__)
app.secret_key = "supersecretkey"
DATABASE = "database.db"
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

@app.route("/")
def home():
    return render_template("index.html")
    
app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        db = get_db()
        admin = db.execute(
            "SELECT * FROM user WHERE email = ? AND role = 'admin'",
            (email,)
        ).fetchone()

        if admin and check_password_hash(admin["password_hash"], password):
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

    db = get_db()
    users = db.execute("SELECT * FROM user").fetchall()
    return render_template("admin_dashboard.html", users=users)
    
@app.route("/users")
def list_users():
    db = get_db()
    users = db.execute("SELECT * FROM user").fetchall()
    return render_template("users.html", users=users)
    
@app.route("/add_users", methods=["GET", "POST"])
def add_user():
    if request.method == "POST":
        email = request.form["email"]
        role = request.form["role"]
        password = request.form["password"]  # (plain text for now)

        db = get_db()
        hashed_password = generate_password_hash(password)
        db.execute(
            "INSERT INTO user (email, password_hash, role, created_at) VALUES (?, ?, ?, datetime('now'))",
            (email, hashed_password, role)
        )
        db.commit()
        flash("User added successfully!", "success")
        return redirect(url_for("admin_dashboard"))
        
    return redirect(url_for("add_users"))

@app.route("/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    if not session.get("admin_logged_in"):
        flash("Please log in first.", "error")
        return redirect(url_for("admin_login"))

    db = get_db()
    db.execute("DELETE FROM user WHERE id = ?", (user_id,))
    db.commit()
    flash("User deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))
    
if __name__ == "__main__":
    app.run(debug=True)