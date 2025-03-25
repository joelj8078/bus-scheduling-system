import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:joel@localhost/bus_scheduling")
SQLALCHEMY_TRACK_MODIFICATIONS = False

print(f"✅ DATABASE_URL: {DATABASE_URL}")  # For debugging
