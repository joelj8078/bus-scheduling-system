from flask import Flask, request, jsonify, render_template
from flask_migrate import Migrate
from config import DATABASE_URL
from database import db, init_db, Route, Crew, DynamicStopRequest
import pytz
from datetime import datetime

# Set the desired timezone (Example: Asia/Kolkata - IST)
DESIRED_TZ = pytz.timezone("Asia/Kolkata")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Initialize database
db.init_app(app)
migrate = Migrate(app, db)

with app.app_context():
    init_db(app)  # Ensures tables are created

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

# ==============================
# 🚏 Dynamic Bus Stops API
# ==============================
@app.route('/dynamic_stops', methods=['GET'])
def get_dynamic_stops():
    requests = DynamicStopRequest.query.all()

    result = [
        {
            "id": request.id,
            "latitude": request.latitude,
            "longitude": request.longitude,
            "requested_time": request.requested_time.astimezone(DESIRED_TZ).isoformat(),
            "status": request.status
        }
        for request in requests
    ]

    return jsonify(result)

@app.route('/dynamic_stops', methods=['POST'])
def add_dynamic_stop():
    data = request.json
    if not all(k in data for k in ('latitude', 'longitude')):
        return jsonify({"error": "Latitude and Longitude are required"}), 400

    new_stop = DynamicStopRequest(
        latitude=data['latitude'],
        longitude=data['longitude']
    )
    db.session.add(new_stop)
    db.session.commit()
    return jsonify({"message": "Dynamic stop request added successfully!"})

@app.route('/dynamic_stops/<int:stop_id>', methods=['PUT'])
def update_dynamic_stop(stop_id):
    stop = DynamicStopRequest.query.get(stop_id)
    if not stop:
        return jsonify({"error": "Dynamic stop request not found"}), 404

    data = request.json
    if 'status' in data:
        stop.status = data['status']  # Status: Pending, Approved, Rejected
        db.session.commit()
        return jsonify({"message": "Dynamic stop status updated successfully!"})

    return jsonify({"error": "Invalid request"}), 400

@app.route('/dynamic_stops/<int:stop_id>', methods=['DELETE'])
def delete_dynamic_stop(stop_id):
    stop = DynamicStopRequest.query.get(stop_id)
    if not stop:
        return jsonify({"error": "Dynamic stop request not found"}), 404

    db.session.delete(stop)
    db.session.commit()
    return jsonify({"message": "Dynamic stop request deleted successfully!"})

# ==============================
# 🏁 Route Management API
# ==============================
@app.route('/routes', methods=['GET'])
def get_routes():
    routes = Route.query.all()
    return jsonify([
        {
            "id": route.id,
            "route_name": route.route_name,
            "start_point": route.start_point,
            "end_point": route.end_point
        }
        for route in routes
    ])

@app.route('/routes/<int:route_id>', methods=['GET'])
def get_route(route_id):
    route = Route.query.get(route_id)
    if not route:
        return jsonify({"error": "Route not found"}), 404
    return jsonify({
        "id": route.id,
        "route_name": route.route_name,
        "start_point": route.start_point,
        "end_point": route.end_point
    })

@app.route('/routes', methods=['POST'])
def add_route():
    data = request.json
    if not all(k in data for k in ('route_name', 'start_point', 'end_point')):
        return jsonify({"error": "Missing required fields"}), 400

    new_route = Route(
        route_name=data['route_name'],
        start_point=data['start_point'],
        end_point=data['end_point']
    )
    db.session.add(new_route)
    db.session.commit()
    return jsonify({"message": "Route added successfully!"})

@app.route('/routes/<int:route_id>', methods=['PUT'])
def update_route(route_id):
    data = request.json
    route = Route.query.get(route_id)
    if not route:
        return jsonify({"error": "Route not found"}), 404

    route.route_name = data.get('route_name', route.route_name)
    route.start_point = data.get('start_point', route.start_point)
    route.end_point = data.get('end_point', route.end_point)

    db.session.commit()
    return jsonify({"message": "Route updated successfully!"})

@app.route('/routes/<int:route_id>', methods=['DELETE'])
def delete_route(route_id):
    route = Route.query.get(route_id)
    if not route:
        return jsonify({"error": "Route not found"}), 404

    db.session.delete(route)
    db.session.commit()
    return jsonify({"message": "Route deleted successfully!"})

# ==============================
# 👥 Crew Management API
# ==============================
@app.route('/crew', methods=['GET'])
def get_crew():
    crew = Crew.query.all()
    return jsonify([
        {
            "id": member.id,
            "name": member.name,
            "role": member.role,
            "shift": member.shift,
            "assigned_route": member.assigned_route
        }
        for member in crew
    ])

@app.route('/crew', methods=['POST'])
def add_crew():
    data = request.json
    if not all(k in data for k in ('name', 'role', 'shift')):
        return jsonify({"error": "Missing required fields"}), 400

    assigned_route = data.get('assigned_route')
    if assigned_route and not Route.query.get(assigned_route):
        return jsonify({"error": f"Route ID {assigned_route} does not exist!"}), 400

    new_crew = Crew(
        name=data['name'],
        role=data['role'],
        shift=data['shift'],
        assigned_route=assigned_route
    )
    db.session.add(new_crew)
    db.session.commit()
    return jsonify({"message": "Crew member added successfully!"})

@app.route('/crew/<int:crew_id>', methods=['PUT'])
def update_crew(crew_id):
    data = request.json
    crew = Crew.query.get(crew_id)
    if not crew:
        return jsonify({"error": "Crew member not found"}), 404

    crew.name = data.get('name', crew.name)
    crew.role = data.get('role', crew.role)
    crew.shift = data.get('shift', crew.shift)
    crew.assigned_route = data.get('assigned_route', crew.assigned_route)

    db.session.commit()
    return jsonify({"message": "Crew details updated successfully!"})

@app.route('/crew/<int:crew_id>', methods=['DELETE'])
def delete_crew(crew_id):
    crew = Crew.query.get(crew_id)
    if not crew:
        return jsonify({"error": "Crew member not found"}), 404

    db.session.delete(crew)
    db.session.commit()
    return jsonify({"message": "Crew member deleted successfully!"})

# ==============================
# 🚀 Run Flask App
# ==============================
if __name__ == '__main__':
    app.run(debug=True)
