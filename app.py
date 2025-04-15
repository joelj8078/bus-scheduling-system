from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, desc 
from flask_migrate import Migrate
from config import DATABASE_URL
from database import db, init_db, Route, Crew, DynamicStopRequest, User, CrowdReport, BusStop, Bus 
import pytz
import traceback
from datetime import datetime, timezone
import random
import time 
import requests


# Set timezone
DESIRED_TZ = pytz.timezone("Asia/Kolkata")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True
ORS_API_KEY = '5b3ce3597851110001cf62487d98feb98f784f8198ab3e59395a1436'

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

@app.route('/voice_request_stop')
def voice_request_stop():
    return render_template('voice_request_stop.html')

@app.route('/crowd_report')
def crowd_report_page():
    return render_template('crowd_report.html')

@app.route('/crowd_map')
def crowd_map():
    return render_template('crowd_map.html')

@app.route('/crowd_heatmap')
def heatmap_page():
    return render_template('crowd_heatmap.html')

@app.route('/map')
def map_page():
    return render_template('map.html')

@app.route('/inspector-dashboard')
def inspect_dashboard():
    buses = Bus.query.all()
    return render_template('inspector_dashboard.html', buses=buses)




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
    
# ===============================
# 🧭 View Dynamic Stops (UI page)
# ===============================
@app.route('/dynamic-stops')
def view_dynamic_stops():
    try:
        requests = DynamicStopRequest.query.all()
        return render_template('dynamic_stops.html', requests=requests)
    except Exception as e:
        traceback.print_exc()
        return "Something went wrong while loading dynamic stops!", 500
  
# Dummy bus data (simulating real-time updates)
bus_data = [
    {"id": 1, "latitude": 12.9716, "longitude": 77.5946},  # Initial location (Bangalore)
    {"id": 2, "latitude": 12.9756, "longitude": 77.5986},  # Another bus
]

@app.route('/bus_locations', methods=['GET'])
def get_bus_locations():
    """Simulates real-time bus movement."""
    for bus in bus_data:
        # Randomly adjust latitude and longitude to simulate movement
        bus["latitude"] += (random.uniform(-0.0005, 0.0005))
        bus["longitude"] += (random.uniform(-0.0005, 0.0005))
    return jsonify(bus_data)

@app.route('/get-alternative-routes', methods=['POST'])
def get_alternative_routes():
    try:
        data = request.get_json()
        start = data.get('start')
        end = data.get('end')

        if not start or not end:
            return jsonify({"error": "Missing start or end coordinates"}), 400

        # OpenRouteService Directions API
        ors_url = 'https://api.openrouteservice.org/v2/directions/driving-car'
        headers = {
            'Authorization': ORS_API_KEY,
            'Content-Type': 'application/json'
        }
        payload = {
            "coordinates": [start, end],
            "alternative_routes": {
                "share_factor": 0.6,
                "target_count": 3,
                "weight_factor": 1.6
            }
        }

        response = requests.post(ors_url, headers=headers, json=payload)
        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch routes from OpenRouteService", "details": response.text}), 500

        data = response.json()

        routes = []
        for feature in data.get("features", []):
            route_info = {
                "distance_km": round(feature["properties"]["segments"][0]["distance"] / 1000, 2),
                "duration_min": round(feature["properties"]["segments"][0]["duration"] / 60, 2),
                "coordinates": feature["geometry"]["coordinates"]
            }
            routes.append(route_info)

        return jsonify({"routes": routes}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
@app.route('/submit_voice_stop', methods=['POST'])
def submit_voice_stop():
    data = request.get_json()
    stop_name = data.get('stop_name')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    user_id = data.get('user_id')  # ✅ Add this

    if not stop_name or not latitude or not longitude or not user_id:
        return jsonify({'message': 'Invalid input data: stop_name, latitude, longitude, and user_id are required.'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    now_ist = datetime.now(pytz.timezone('Asia/Kolkata'))

    new_request = DynamicStopRequest(
        latitude=latitude,
        longitude=longitude,
        requested_time=now_ist,
        status='Pending',
        user_id=user_id  # ✅ Assign user_id
    )

    db.session.add(new_request)
    db.session.commit()

    return jsonify({'message': f'Stop request for "{stop_name}" submitted successfully! ✅'})


# ===========================
# 🚀 API to Submit Crowd Report
# ===========================

@app.route('/submit_crowd_report', methods=['POST'])
def submit_crowd_report():
    data = request.get_json()

    stop_name = data.get('stop_name')
    crowd_level = data.get('crowd_level')
    reported_by_voice = data.get('reported_by_voice', False)
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if not stop_name or not crowd_level:
        return jsonify({"message": "Stop name and crowd level are required."}), 400

    # Check if the stop already exists
    bus_stop = BusStop.query.filter_by(name=stop_name).first()

    # If stop doesn't exist and coordinates are provided, create a new stop
    if not bus_stop and latitude is not None and longitude is not None:
        bus_stop = BusStop(
            name=stop_name,
            latitude=str(latitude),  # ensure string to match DB type
            longitude=str(longitude)
        )
        db.session.add(bus_stop)
        db.session.commit()

    # If stop still doesn't exist and we couldn't create one
    if not bus_stop:
        return jsonify({"message": "Stop not found and no valid coordinates provided."}), 400

    # Create the new crowd report
    report = CrowdReport(
        stop_id=bus_stop.id,
        crowd_level=crowd_level,
        reported_by_voice=reported_by_voice
    )

    db.session.add(report)
    db.session.commit()

    return jsonify({"message": f"✅ Crowd level '{crowd_level}' reported for stop '{stop_name}'."}), 200

    
def fetch_bus_stops_from_osm(lat, lon, radius=1000):
    print("🌐 Calling Overpass API to get bus stops...")
    overpass_url = "http://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    (
      node(around:{radius},{lat},{lon})[highway=bus_stop];
    );
    out body;
    """
    response = requests.post(overpass_url, data=query)
    data = response.json()

    stops = []
    for element in data['elements']:
        name = element['tags'].get('name')
        if name:
            stops.append((name, element['lat'], element['lon']))
    
    return stops


@app.route("/api/bus_stops")
def get_bus_stops():
    try:
        stops = BusStop.query.order_by(BusStop.name).all()
        return jsonify([{"id": stop.id, "name": stop.name} for stop in stops])
    except Exception as e:
        print("Error fetching bus stops:", e)
        return jsonify({"error": "Internal server error"}), 500
    
@app.route('/api/crowd_heatmap')
def crowd_heatmap():
    try:
        # Subquery: Get the latest report timestamp for each stop
        subquery = (
            db.session.query(
                CrowdReport.stop_id,
                func.max(CrowdReport.timestamp).label('latest_timestamp')
            ).group_by(CrowdReport.stop_id).subquery()
        )

        # Join the subquery with original CrowdReport to get full row
        latest_reports = (
            db.session.query(CrowdReport, BusStop)
            .join(subquery, (CrowdReport.stop_id == subquery.c.stop_id) &
                             (CrowdReport.timestamp == subquery.c.latest_timestamp))
            .join(BusStop, BusStop.id == CrowdReport.stop_id)
            .all()
        )

        # Format the results
        results = []
        for report, stop in latest_reports:
            results.append({
                "id": stop.id,
                "name": stop.name,
                "latitude": float(stop.latitude),
                "longitude": float(stop.longitude),
                "crowd_level": report.crowd_level
            })

        return jsonify(results)
    except Exception as e:
        print("Error generating heatmap data:", e)
        return jsonify({'success': False, 'message': 'Error fetching heatmap data.'}), 500
    
@app.route('/inspector/dashboard', methods=['GET', 'POST'])
def inspector_dashboard():
    # Fetch buses from the database
    buses = Bus.query.all()

    if request.method == 'POST':
        bus_id = request.form.get('bus_id')
        bus = Bus.query.get(bus_id)
        if bus:
            # Toggle the status to cycle through 'On Time', 'Delayed', and 'Maintenance'
            if bus.status == 'On Time':
                bus.status = 'Delayed'
            elif bus.status == 'Delayed':
                bus.status = 'Maintenance'
            else:
                bus.status = 'On Time'
            db.session.commit()
            return redirect(url_for('inspector_dashboard'))

    return render_template('inspector_dashboard.html', buses=buses)





# ✅ Run the App
if __name__ == "__main__":
    app.run(debug=True)
