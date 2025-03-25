from functools import wraps
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
from config import DATABASE_URL
from database import db, init_db, User, Route, Crew, DynamicStopRequest
import pytz
from datetime import timedelta
import os
import traceback

# Set timezone
DESIRED_TZ = pytz.timezone("Asia/Kolkata")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config["JWT_SECRET_KEY"] = os.getenv('JWT_SECRET_KEY', 'default_secret_key')
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)

db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

with app.app_context():
    init_db(app)

# ===========================
# ✅ Log Request Info
# ===========================
@app.before_request
def log_request_info():
    print(f"\n✅ URL: {request.url}")
    print(f"✅ Method: {request.method}")
    print(f"✅ Headers: {request.headers}")
    if request.is_json:
        print(f"✅ JSON Payload: {request.get_json()}")

# ===========================
# 🔐 Role-Based Access Control
# ===========================
def role_required(required_role):
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorated_view(*args, **kwargs):
            user_id = get_jwt_identity()
            claims = get_jwt()
            role = claims.get("role")
            print(f"✅ User ID: {user_id}, Role: {role}")  # Debug
            if role != required_role:
                return jsonify({"error": "Access denied"}), 403
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

# ===========================
# 🏠 Web Page Routes
# ===========================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/crew_page')
def crew_page():
    return render_template('crew.html')

@app.route('/dynamic_stop_requests')
def dynamic_stop_requests():
    return render_template('dynamic_stop_requests.html')

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

@app.route('/route_details')
def route_details():
    return render_template('route_details.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/protected_route', methods=['GET'])
@jwt_required()
def protected_route():
    try:
        user_id = get_jwt_identity()
        user_role = get_jwt()["role"]
        print(f"✅ JWT User ID: {user_id}, Role: {user_role}")
        if not user:
            return jsonify({"error": "Unauthorized access"}), 401
        return jsonify({"message": "Token is valid", "user_id": user_id}), 200
    except Exception as e:
        print(f"❌ Error in protected_route: {e}")
        return jsonify({"error": str(e)}), 500


# ===========================
# 📝 Authentication API
# ===========================
@app.route('/register', methods=['POST'])
def register_user():
    if not request.is_json:
        return jsonify({"error": "Invalid Content-Type. Expected JSON"}), 415

    data = request.get_json()
    if not all(k in data for k in ('username', 'email', 'password', 'role')):
        return jsonify({"error": "Missing required fields"}), 400

    if data['role'] not in ["Admin", "Driver", "Passenger"]:
        return jsonify({"error": "Invalid role!"}), 400

    existing_user = User.query.filter((User.username == data['username']) | (User.email == data['email'])).first()
    if existing_user:
        return jsonify({"error": "User already exists"}), 400

    new_user = User(username=data['username'], email=data['email'], role=data['role'])
    new_user.set_password(data['password'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User registered successfully!"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', '')).strip()

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"message": "Invalid username or password"}), 401

    # Create token with user ID as identity and role as additional claim
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify({"message": "Login successful", "token": token, "role": user.role}), 200

# ===========================
# 🚍 Route Management API
# ===========================
@app.route('/routes', methods=['GET', 'POST'])
@role_required("Admin")
def manage_routes():
    user_id = get_jwt_identity()
    user_role = get_jwt()["role"]
    print(f"✅ JWT User ID: {user_id}, Role: {user_role}")  # Debugging

    if request.method == 'GET':
        routes = Route.query.all()
        if not routes:
            return jsonify([]), 200
        return jsonify([{
            "id": route.id,
            "route_name": route.route_name,
            "start_point": route.start_point,
            "end_point": route.end_point
        }]), 200

    if request.method == 'POST':
        data = request.get_json() or {}
        if not all(k in data for k in ('route_name', 'start_point', 'end_point')):
            return jsonify({"error": "Missing required fields"}), 422

        new_route = Route(
            route_name=data['route_name'],
            start_point=data['start_point'],
            end_point=data['end_point']
        )
        db.session.add(new_route)
        db.session.commit()
        return jsonify({"message": "Route added!"}), 201

# ===========================
# 👥 Crew Management API
# ===========================
@app.route('/crew', methods=['GET', 'POST'])
@role_required("Admin")
def manage_crew():
    user_id = get_jwt_identity()
    user_role = get_jwt()["role"]

    if request.method == 'GET':
        crew = Crew.query.all()
        return jsonify([{
            "id": member.id,
            "name": member.name,
            "role": member.role,
            "shift": member.shift,
            "assigned_route": member.assigned_route
        } for member in crew]), 200

    if request.method == 'POST':
        data = request.get_json()
        if not all(k in data for k in ('name', 'role', 'shift')):
            return jsonify({"error": "Missing required fields"}), 422

        new_crew = Crew(**data)
        db.session.add(new_crew)
        db.session.commit()
        return jsonify({"message": "Crew added!"}), 201

# ===========================
# 🚌 Dynamic Stop Requests
# ===========================
@app.route('/dynamic_stops', methods=['GET', 'POST'])
@jwt_required()
def manage_stops():
    user_id = get_jwt_identity()
    user_role = get_jwt()["role"]

    if request.method == 'GET':
        stops = DynamicStopRequest.query.all()
        return jsonify([{
            "id": stop.id,
            "latitude": stop.latitude,
            "longitude": stop.longitude,
            "status": stop.status,
            "requested_time": stop.requested_time.astimezone(DESIRED_TZ).isoformat()
        } for stop in stops]), 200

    if request.method == 'POST':
        data = request.get_json()
        if not all(k in data for k in ('latitude', 'longitude')):
            return jsonify({"error": "Missing required fields"}), 422

        new_stop = DynamicStopRequest(
            latitude=float(data['latitude']),
            longitude=float(data['longitude']),
            user_id=user_id
        )
        db.session.add(new_stop)
        db.session.commit()
        return jsonify({"message": "Dynamic stop request added!"}), 201

# ===========================
# ✅ Run the App
# ===========================
if __name__ == "__main__":
    app.run(debug=True)
