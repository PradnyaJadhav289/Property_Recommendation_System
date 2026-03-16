"""
database.py — MongoDB connection for Brickfolio
Reads MONGO_URI and DB_NAME from .env
"""
import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME   = os.environ.get("DB_NAME",   "brickfolio")

# ── Connect ───────────────────────────────────────────────────────────────
client = MongoClient(MONGO_URI)
db     = client[DB_NAME]

# ── Create indexes (safe to call multiple times) ──────────────────────────
def create_indexes():
    try:
        # users
        db.users.create_index("user_id", unique=True)

        # properties
        db.properties.create_index("property_id", unique=True)
        db.properties.create_index([("location",      ASCENDING)])
        db.properties.create_index([("price",         ASCENDING)])
        db.properties.create_index([("property_type", ASCENDING)])
        db.properties.create_index([("featured",      DESCENDING)])

        # activity feed — sort by newest first
        db.user_activity.create_index(
            [("user_id", ASCENDING), ("timestamp", DESCENDING)]
        )

        print("✅ Indexes ready")
    except Exception as e:
        print(f"⚠️  Index warning (safe to ignore on first run): {e}")

create_indexes()
print(f"✅ MongoDB connected → {MONGO_URI}  |  db: {DB_NAME}")