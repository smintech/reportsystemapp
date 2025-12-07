from flask import Flask, render_template, g
import sqlite3
app = Flask(__name__)
DATABASE = "database.db"

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route("/")
def home():
    return render_template("index.html")
    
@app.route("/users")
def list_users():
    db = get_db()
    users = db.execute("SELECT * FROM user").fetchall()
    return render_template("users.html", users=users)
    
if __name__ == "__main__":
    app.run()