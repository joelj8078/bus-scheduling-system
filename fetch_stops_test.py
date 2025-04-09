from app import app, fetch_bus_stops_from_osm
from database import db, BusStop

# Choose your center point for the search (Delhi here)
latitude = 28.6139
longitude = 77.2090

with app.app_context():
    print("🌐 Fetching stops from OpenStreetMap...")
    stops = fetch_bus_stops_from_osm(latitude, longitude)

    print(f"🚏 Found {len(stops)} bus stops. Here’s a sample:")
    for i, (name, lat, lon) in enumerate(stops[:3]):
        print(f"🔍 Stop {i+1}: {name}")

    print("💾 Saving to database...")
    for name, lat, lon in stops:
        existing = BusStop.query.filter_by(name=name).first()
        if not existing:
            new_stop = BusStop(name=name, latitude=lat, longitude=lon)
            db.session.add(new_stop)

    db.session.commit()
    print("✅ Bus stops saved to database.")
