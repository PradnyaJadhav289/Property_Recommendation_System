"""
User routes for Brickfolio
POST /api/track-view          – log property view / click
POST /api/search              – log search query + preferences
POST /api/update-location     – store live GPS coordinates
GET  /api/users/{id}/profile  – user profile + history
GET  /api/detect-location     – IP-based location fallback
"""
from fastapi import APIRouter, Request
from database import db
from models.user import TrackViewRequest, SearchRequest, LocationRequest
from utils.helpers import get_client_ip, get_location_from_ip, utc_now_str
from datetime import datetime

router = APIRouter(prefix="/api", tags=["Users"])


# ─── Track Property View / Click ──────────────────────────────────────────

@router.post("/track-view")
async def track_view(req: TrackViewRequest):
    """Log a user's interaction with a property."""
    db.user_activity.insert_one({
        "user_id":     req.user_id,
        "property_id": req.property_id,
        "action_type": req.action_type,
        "timestamp":   datetime.utcnow(),
    })

    db.users.update_one(
        {"user_id": req.user_id},
        {
            "$addToSet":  {"viewed_properties": req.property_id},
            "$setOnInsert": {
                "user_id":             req.user_id,
                "name":                "Guest",
                "search_history":      [],
                "interested_locations": [],
                "budget_range":        {},
            },
        },
        upsert=True,
    )
    return {"success": True, "tracked": req.action_type}


# ─── Track Search ─────────────────────────────────────────────────────────

@router.post("/search")
async def track_search(req: SearchRequest):
    """Store a search query and infer user preferences."""
    entry = {
        "query":     req.query,
        "location":  req.location,
        "timestamp": utc_now_str(),
    }

    update: dict = {
        "$push": {
            "search_history": {
                "$each":  [entry],
                "$slice": -20,      # keep last 20 searches
            }
        },
        "$setOnInsert": {
            "user_id":             req.user_id,
            "name":                "Guest",
            "viewed_properties":   [],
            "interested_locations": [],
        },
    }

    if req.location:
        update["$addToSet"] = {"interested_locations": req.location}

    if req.budget_min is not None and req.budget_max is not None:
        update.setdefault("$set", {})["budget_range"] = {
            "min": req.budget_min,
            "max": req.budget_max,
        }

    db.users.update_one({"user_id": req.user_id}, update, upsert=True)
    return {"success": True}


# ─── Update Live Location ─────────────────────────────────────────────────

@router.post("/update-location")
async def update_location(req: LocationRequest):
    """Store the user's current GPS coordinates."""
    db.users.update_one(
        {"user_id": req.user_id},
        {
            "$set": {
                "live_location": {
                    "latitude":   req.latitude,
                    "longitude":  req.longitude,
                    "updated_at": datetime.utcnow(),
                }
            },
            "$setOnInsert": {
                "user_id":             req.user_id,
                "name":                "Guest",
                "search_history":      [],
                "interested_locations": [],
                "viewed_properties":   [],
                "budget_range":        {},
            },
        },
        upsert=True,
    )
    return {"success": True}


# ─── User Profile ─────────────────────────────────────────────────────────

@router.get("/users/{user_id}/profile")
async def get_user_profile(user_id: str):
    """Return a user's full profile including history and preferences."""
    user = db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        return {"success": True, "user": {"user_id": user_id, "is_new": True}}

    # Attach recent activity
    recent = list(
        db.user_activity.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(10)
    )
    # Convert datetimes to strings for JSON serialisation
    for r in recent:
        if isinstance(r.get("timestamp"), datetime):
            r["timestamp"] = r["timestamp"].isoformat()

    return {"success": True, "user": user, "recent_activity": recent}


# ─── IP Location Fallback ─────────────────────────────────────────────────

@router.get("/detect-location")
async def detect_location(request: Request):
    """Detect approximate location from the client's IP address."""
    ip   = get_client_ip(request)
    data = get_location_from_ip(ip)
    return {"success": True, **data}