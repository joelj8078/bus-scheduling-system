from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Define the Route model
class Route(db.Model):
    __tablename__ = "routes"
    id = db.Column(db.Integer, primary_key=True)
    route_name = db.Column(db.String(100), nullable=False)
    start_point = db.Column(db.String(100), nullable=False)
    end_point = db.Column(db.String(100), nullable=False)

# Define the Crew model
class Crew(db.Model):
    __tablename__ = "crew"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # Driver or Conductor
    shift = db.Column(db.String(50), nullable=False)  # Morning, Evening, Night
    assigned_route = db.Column(db.Integer, db.ForeignKey('routes.id'), nullable=True)

# Define the Dynamic Stop Requests table
class DynamicStopRequest(db.Model):
    __tablename__ = "dynamic_stop_requests"
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    requested_time = db.Column(db.DateTime, default=db.func.current_timestamp())
    status = db.Column(db.String(20), default="Pending")  # Pending, Approved, Rejected

# Function to initialize database (to be called in `app.py`)
def init_db(app):
    with app.app_context():
        db.create_all()
        print("✅ Database initialized successfully.")
