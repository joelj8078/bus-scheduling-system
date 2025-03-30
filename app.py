from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import DATABASE_URL
from database import db, init_db, Route, Crew, DynamicStopRequest, User
import pytz
import traceback
from datetime import datetime, timezone

# Set timezone
DESIRED_TZ = pytz.timezone("Asia/Kolkata")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True

db.init_app(app)
migrate = Migrate(app, db)

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
        print(f"✅ JSON Payload: {request.get_json(silent=True)}")

# ===========================
# 🏠 Web Page Routes
# ===========================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/routes_page')
def routes_page():
    return render_template('routes.html')

@app.route('/crew_page')
def crew_page():
    return render_template('crew.html')

@app.route('/dynamic_stop_requests')
def dynamic_stop_requests():
    return render_template('dynamic_stop_requests.html')

# ===========================
# 🚍 Route Management API
# ===========================
@app.route('/routes', methods=['GET', 'POST'])
def manage_routes():
    try:
        if request.method == 'GET':
            routes = Route.query.all()
            return jsonify([{
                "id": route.id,
                "route_name": route.route_name,
                "start_point": route.start_point,
                "end_point": route.end_point
            } for route in routes]), 200

        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 415

        data = request.get_json()
        if not all(k in data for k in ('route_name', 'start_point', 'end_point')):
            return jsonify({"error": "Missing required fields"}), 422

        # Check for duplicate route name
        duplicate_name = Route.query.filter_by(route_name=data['route_name']).first()
        # Check for duplicate start and end point
        duplicate_start_end = Route.query.filter_by(
            start_point=data['start_point'],
            end_point=data['end_point']
        ).first()

        # If either condition is true, reject the addition
        if duplicate_name and duplicate_start_end:
            return jsonify({"error": "A route with the same name and same start & end points already exists."}), 409
        elif duplicate_name:
            return jsonify({"error": "A route with the same name already exists."}), 409
        elif duplicate_start_end:
            return jsonify({"error": "A route with the same start and end points already exists."}), 409

        # If no duplicates, create a new route
        new_route = Route(
            route_name=data['route_name'],
            start_point=data['start_point'],
            end_point=data['end_point']
        )
        db.session.add(new_route)
        db.session.commit()
        return jsonify({"message": "✅ Route added successfully!"}), 201

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/routes/<int:route_id>', methods=['PUT', 'DELETE'])
def update_or_delete_route(route_id):
    try:
        route = Route.query.get(route_id)
        if not route:
            return jsonify({"error": "Route not found"}), 404

        if request.method == 'PUT':
            data = request.get_json(silent=True)
            if not data:
                return jsonify({"error": "Invalid or missing JSON payload"}), 400

            route.route_name = data.get('route_name', route.route_name)
            route.start_point = data.get('start_point', route.start_point)
            route.end_point = data.get('end_point', route.end_point)
            db.session.commit()
            return jsonify({"message": "Route updated!"}), 200

        if request.method == 'DELETE':
            db.session.delete(route)
            db.session.commit()
            return jsonify({"message": "Route deleted!"}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ===========================
# 👥 Crew Management API (Fixed)
# ===========================
@app.route('/crew', methods=['GET', 'POST'])
def manage_crew():
    try:
        if request.method == 'GET':
            crew = Crew.query.all()
            return jsonify([{
                "id": member.id,
                "name": member.name,
                "role": member.role,
                "shift": member.shift,
                "contact_number": member.contact_number,
                "assigned_route": member.assigned_route
            } for member in crew]), 200

        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Missing JSON payload"}), 400

        # Check for missing fields
        required_fields = ['name', 'role', 'shift', 'contact_number', 'assigned_route']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 422

        # Debugging Data
        print(f"🟡 Received Crew Data: {data}")

        new_crew = Crew(
            name=data['name'],
            role=data['role'],
            shift=data['shift'],
            contact_number=data['contact_number'],  
            assigned_route=data['assigned_route']
        )
        db.session.add(new_crew)
        db.session.commit()
        return jsonify({"message": "✅ Crew member added successfully!"}), 201

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
@app.route('/crew/<int:crew_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_single_crew(crew_id):
    try:
        crew_member = Crew.query.get(crew_id)
        if not crew_member:
            return jsonify({"error": "Crew member not found"}), 404

        if request.method == 'GET':
            return jsonify({
                "id": crew_member.id,
                "name": crew_member.name,
                "role": crew_member.role,
                "shift": crew_member.shift,
                "contact_number": crew_member.contact_number,
                "assigned_route": crew_member.assigned_route
            }), 200

        if request.method == 'PUT':
            data = request.get_json(silent=True)
            if not data:
                return jsonify({"error": "Invalid or missing JSON payload"}), 400

            crew_member.name = data.get('name', crew_member.name)
            crew_member.role = data.get('role', crew_member.role)
            crew_member.shift = data.get('shift', crew_member.shift)
            crew_member.contact_number = data.get('contact_number', crew_member.contact_number)
            crew_member.assigned_route = data.get('assigned_route', crew_member.assigned_route)
            db.session.commit()
            return jsonify({"message": "✅ Crew member updated!"}), 200

        if request.method == 'DELETE':
            db.session.delete(crew_member)
            db.session.commit()
            return jsonify({"message": "✅ Crew member deleted!"}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ===========================
# 🚌 Dynamic Stop Request API
# ===========================
@app.route('/dynamic_requests', methods=['GET', 'POST'])
def manage_dynamic_stop_requests():
    try:
        if request.method == 'GET':
            requests = DynamicStopRequest.query.all()
            return jsonify([{
                'id': req.id,
                'latitude': req.latitude,
                'longitude': req.longitude,
                'requested_time': req.get_requested_time_ist(),
                'status': req.status,
                'user_id': req.user_id,
                'username': req.user.username if req.user else "Unknown"
            } for req in requests]), 200

        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 415

        data = request.get_json()
        if not all(k in data for k in ('latitude', 'longitude', 'user_id')):
            return jsonify({'error': 'Missing required fields (latitude, longitude, user_id)'}), 422

        user = User.query.get(data['user_id'])
        if not user:
            return jsonify({'error': 'User not found.'}), 404

        new_request = DynamicStopRequest(
            latitude=data['latitude'],
            longitude=data['longitude'],
            user_id=data['user_id'],
            requested_time=datetime.now(timezone.utc),
            status="Pending"
        )
        db.session.add(new_request)
        db.session.commit()
        return jsonify({"message": "✅ Dynamic stop request added successfully.", "id": new_request.id}), 201

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/dynamic_requests/<int:request_id>', methods=['PUT', 'DELETE'])
def manage_single_dynamic_stop_request(request_id):
    try:
        req = DynamicStopRequest.query.get(request_id)
        if not req:
            return jsonify({'error': 'Dynamic stop request not found.'}), 404

        if request.method == 'PUT':
            data = request.get_json(silent=True)
            if not data:
                return jsonify({'error': 'Invalid or missing JSON payload'}), 400

            req.latitude = data.get('latitude', req.latitude)
            req.longitude = data.get('longitude', req.longitude)
            req.status = data.get('status', req.status)

            if 'requested_time' in data:
                return jsonify({'error': 'requested_time cannot be modified manually'}), 400
                
            if 'user_id' in data:
                user = User.query.get(data['user_id'])
                if user:
                    req.user_id = data['user_id']
                else:
                    return jsonify({'error': 'User not found.'}), 404

            db.session.commit()
            return jsonify({'message': '✅ Dynamic stop request updated successfully.'}), 200

        if request.method == 'DELETE':
            db.session.delete(req)
            db.session.commit()
            return jsonify({'message': '✅ Dynamic stop request deleted successfully.'}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ✅ Run the App
if __name__ == "__main__":
    app.run(debug=True)
