from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pytz

db = SQLAlchemy()

# ==========================
# 👤 User Model
# ==========================
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    stops = db.relationship('DynamicStopRequest', backref='user', lazy=True)

    def set_password(self, password):                                               
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ==========================
# 🚏 Route Model
# ==========================
class Route(db.Model):
    __tablename__ = "routes"
    id = db.Column(db.Integer, primary_key=True)
    route_name = db.Column(db.String(100), nullable=False)
    start_point = db.Column(db.String(100), nullable=False)
    end_point = db.Column(db.String(100), nullable=False)
    crew_members = db.relationship('Crew', backref='route', lazy=True)

# ==========================
# 👷 Crew Model
# ==========================
class Crew(db.Model):
    __tablename__ = "crew"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    shift = db.Column(db.String(50), nullable=False)
    assigned_route = db.Column(db.Integer, db.ForeignKey('routes.id'), nullable=True)

# ==========================
# 🚌 Dynamic Stop Request Model
# ==========================
class DynamicStopRequest(db.Model):
    __tablename__ = "dynamic_stop_requests"
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    requested_time = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="Pending")
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def get_requested_time_ist(self):
        """Converts stored UTC time to IST."""
        utc_time = self.requested_time.replace(tzinfo=pytz.utc)
        return utc_time.astimezone(pytz.timezone("Asia/Kolkata")).strftime('%Y-%m-%d %H:%M:%S')

# ==========================
# 🗄️ Database Initialization
# ==========================
def init_db(app):
    with app.app_context():
        db.create_all()
        print("✅ Database initialized successfully.")
