from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import DATABASE_URL
from database import db, init_db, Route, Crew, DynamicStopRequest
import pytz
import traceback

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

        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid or missing JSON payload"}), 400

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
# 👥 Crew Management API
# ===========================
@app.route('/crew', methods=['GET', 'POST'])
def manage_crew():
    try:
        if request.method == 'GET':
            crew = Crew.query.all()
            return jsonify([member.serialize() for member in crew]), 200

        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid or missing JSON payload"}), 400

        new_crew = Crew(**data)
        db.session.add(new_crew)
        db.session.commit()
        return jsonify({"message": "Crew member added!"}), 201

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/crew/<int:crew_id>', methods=['PUT', 'DELETE'])
def update_or_delete_crew(crew_id):
    try:
        crew_member = Crew.query.get(crew_id)
        if not crew_member:
            return jsonify({"error": "Crew member not found"}), 404

        if request.method == 'PUT':
            data = request.get_json(silent=True)
            if not data:
                return jsonify({"error": "Invalid or missing JSON payload"}), 400

            crew_member.name = data.get('name', crew_member.name)
            crew_member.role = data.get('role', crew_member.role)
            crew_member.shift = data.get('shift', crew_member.shift)
            crew_member.assigned_route = data.get('assigned_route', crew_member.assigned_route)
            db.session.commit()
            return jsonify({"message": "Crew member updated!"}), 200

        if request.method == 'DELETE':
            db.session.delete(crew_member)
            db.session.commit()
            return jsonify({"message": "Crew member deleted!"}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ===========================
# 🚌 Dynamic Stop Requests
# ===========================
@app.route('/dynamic_stops', methods=['GET', 'POST'])
def manage_stops():
    try:
        if request.method == 'GET':
            stops = DynamicStopRequest.query.all()
            return jsonify([stop.serialize() for stop in stops]), 200

        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid or missing JSON payload"}), 400

        new_stop = DynamicStopRequest(
            latitude=float(data['latitude']),
            longitude=float(data['longitude']),
            status=data.get('status', 'Pending')
        )
        db.session.add(new_stop)
        db.session.commit()
        return jsonify({"message": "Stop request added!"}), 201

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/dynamic_stops/<int:stop_id>', methods=['PUT', 'DELETE'])
def update_or_delete_stop(stop_id):
    try:
        stop = DynamicStopRequest.query.get(stop_id)
        if not stop:
            return jsonify({"error": "Stop request not found"}), 404

        if request.method == 'PUT':
            data = request.get_json(silent=True)
            if not data:
                return jsonify({"error": "Invalid or missing JSON payload"}), 400

            stop.latitude = float(data.get('latitude', stop.latitude))
            stop.longitude = float(data.get('longitude', stop.longitude))
            stop.status = data.get('status', stop.status)
            db.session.commit()
            return jsonify({"message": "Stop request updated!"}), 200

        if request.method == 'DELETE':
            db.session.delete(stop)
            db.session.commit()
            return jsonify({"message": "Stop request deleted!"}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ✅ Run the App
if __name__ == "__main__":
    app.run(debug=True)
