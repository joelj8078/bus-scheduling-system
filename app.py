from functools import wraps
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from config import DATABASE_URL
from database import db, init_db, User, Route, Crew, DynamicStopRequest  
import pytz
from datetime import datetime, timedelta

# Set timezone
DESIRED_TZ = pytz.timezone("Asia/Kolkata")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True

app.config["JWT_SECRET_KEY"] = "324959191"  # Change for security
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)

# Initialize database
db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

with app.app_context():
    init_db(app)  # Ensure tables are created

# ==============================
# 🔐 Role-Based Access Control (RBAC)
# ==============================
def role_required(required_role):
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorated_view(*args, **kwargs):
            user = get_jwt_identity()
            if user["role"] != required_role:
                return jsonify({"error": "Unauthorized - Access Denied"}), 403
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

# ==============================
# 🏠 Serve Web Pages
# ==============================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/crew_page')
def crew_page():
    return render_template('crew.html')

@app.route('/dynamic_stop_requests')
def dynamic_stop_requests():
    return render_template('dynamic_stop_requests.html')

@app.route('/admin', methods=['GET'])
@role_required("Admin")  # Ensure only Admins can access
def admin_panel():
    return render_template('admin.html')

# ==============================
# 📝 User Authentication API
# ==============================

# ✅ Register User
@app.route('/register', methods=['POST'])
def register_user():
    data = request.json
    if not all(k in data for k in ('username', 'email', 'password', 'role')):
        return jsonify({"error": "Missing required fields"}), 400

    if data['role'] not in ["Admin", "Driver", "Passenger"]:
        return jsonify({"error": "Invalid role!"}), 400

    existing_user = User.query.filter(
        (User.username == data['username']) | (User.email == data['email'])
    ).first()
    if existing_user:
        return jsonify({"error": "Username or email already exists"}), 400

    new_user = User(username=data['username'], email=data['email'], role=data['role'])
    new_user.set_password(data['password'])
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully!"})

# ✅ User Login
@app.route('/login', methods=['POST'])
def login_user():
    data = request.json
    if not all(k in data for k in ('email', 'password')):
        return jsonify({"error": "Missing email or password"}), 400

    user = User.query.filter_by(email=data['email']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({"error": "Invalid email or password"}), 401  

    access_token = create_access_token(identity={"id": str(user.id), "role": user.role})
    return jsonify({"message": "Login successful!", "token": access_token, "role": user.role})

# ==============================
# 🛠️ Admin API for User Management
# ==============================

# ✅ Fetch all users (Admin Only)
@app.route('/users', methods=['GET'])
@role_required("Admin")
def get_users():
    users = User.query.all()
    return jsonify([
        {"id": user.id, "username": user.username, "email": user.email, "role": user.role}
        for user in users
    ])

# ✅ Update user role (Admin Only)
@app.route('/users/<int:user_id>', methods=['PUT'])
@role_required("Admin")
def update_user_role(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.json
    if "role" not in data or data["role"] not in ["Admin", "Driver", "Passenger"]:
        return jsonify({"error": "Invalid role"}), 400

    user.role = data["role"]
    db.session.commit()
    return jsonify({"message": f"User {user.username}'s role updated to {user.role}"})

# ✅ Delete a user (Admin Only)
@app.route('/users/<int:user_id>', methods=['DELETE'])
@role_required("Admin")
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": f"User {user.username} deleted successfully"})

# ==============================
# 🚍 Route Management API
# ==============================
@app.route('/routes', methods=['GET'])
@jwt_required()
def get_routes():
    routes = Route.query.all()
    return jsonify([
        {"id": route.id, "route_name": route.route_name, "start_point": route.start_point, "end_point": route.end_point}
        for route in routes
    ])

@app.route('/routes', methods=['POST'])
@role_required("Admin")
def add_route():
    data = request.json
    new_route = Route(route_name=data['route_name'], start_point=data['start_point'], end_point=data['end_point'])
    db.session.add(new_route)
    db.session.commit()
    return jsonify({"message": "Route added successfully!"})

@app.route('/routes/<int:route_id>', methods=['DELETE'])
@role_required("Admin")
def delete_route(route_id):
    route = Route.query.get(route_id)
    if not route:
        return jsonify({"error": "Route not found"}), 404

    db.session.delete(route)
    db.session.commit()
    return jsonify({"message": "Route deleted successfully!"})

# ==============================
# 📍 Dynamic Stop Requests API
# ==============================
@app.route('/dynamic_stops', methods=['GET'])
@jwt_required()
def get_dynamic_stops():
    requests = DynamicStopRequest.query.all()
    result = [
        {
            "id": request.id,
            "latitude": request.latitude,
            "longitude": request.longitude,
            "requested_time": request.requested_time.replace(tzinfo=pytz.utc).astimezone(DESIRED_TZ).isoformat(),
            "status": request.status
        }
        for request in requests
    ]
    return jsonify(result)

@app.route('/dynamic_stops', methods=['POST'])
@role_required("Passenger")
def add_dynamic_stop():
    data = request.json
    new_stop = DynamicStopRequest(latitude=data['latitude'], longitude=data['longitude'])
    db.session.add(new_stop)
    db.session.commit()
    return jsonify({"message": "Dynamic stop request added successfully!"})

@app.route('/dynamic_stops/<int:stop_id>', methods=['PUT'])
@role_required("Driver")
def update_dynamic_stop(stop_id):
    stop = DynamicStopRequest.query.get(stop_id)
    if not stop:
        return jsonify({"error": "Dynamic stop request not found"}), 404

    data = request.json
    stop.status = data['status']
    db.session.commit()
    return jsonify({"message": "Dynamic stop status updated successfully!"})

@app.route('/dynamic_stops/<int:stop_id>', methods=['DELETE'])
@role_required("Admin")
def delete_dynamic_stop(stop_id):
    stop = DynamicStopRequest.query.get(stop_id)
    if not stop:
        return jsonify({"error": "Dynamic stop request not found"}), 404

    db.session.delete(stop)
    db.session.commit()
    return jsonify({"message": "Dynamic stop request deleted successfully!"})

# ==============================
# 🚀 Run Flask App
# ==============================
if __name__ == '__main__':
    app.run(debug=True)
