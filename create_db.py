from flask import Flask
from werkzeug.security import generate_password_hash
from models import db, User

def make_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    return app

app = make_app()
with app.app_context():
    db.create_all()
    print("✔ Database tables created")

    email = "admin@ratel.com"
    if not User.query.filter_by(email=email).first():
        admin = User(
            email=email,
            password_hash=generate_password_hash("AdminPass123"),
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()
        print("✔ Admin user created:", email)
    else:
        print("ℹ Admin already exists")