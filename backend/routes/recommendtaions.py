"""
Recommendation routes for Brickfolio
GET /recommendations/{user_id}  – AI-ranked property list
"""
from typing import Optional
from fastapi import APIRouter, Query
from database import db
from recommendation_engine import RecommendationEngine

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

engine = RecommendationEngine()


@router.get("/{user_id}")
async def get_recommendations(
    user_id: str,
    lat:     Optional[float] = Query(None, description="User's live latitude"),
    lng:     Optional[float] = Query(None, description="User's live longitude"),
    limit:   int             = Query(10, ge=1, le=20),
):
    """
    Return AI-ranked property recommendations for a user.

    Scoring signals (total 100 pts):
      • Location affinity  — 30 pts  (from search + interested locations)
      • Budget match       — 25 pts  (from stored budget_range)
      • Property type      — 20 pts  (inferred from viewed_properties)
      • Feature similarity — 15 pts  (cosine similarity via scikit-learn)
      • Proximity          — 10 pts  (haversine distance from live GPS)
    """
    user = db.users.find_one({"user_id": user_id})

    # Resolve live location: query param → stored → None
    if lat is not None and lng is not None:
        live_location = {"latitude": lat, "longitude": lng}
        # Persist latest coordinates
        if user:
            db.users.update_one(
                {"user_id": user_id},
                {"$set": {"live_location": {"latitude": lat, "longitude": lng}}},
            )
    elif user and user.get("live_location"):
        live_location = user["live_location"]
    else:
        live_location = None

    recs = engine.get_recommendations(user=user, live_location=live_location, limit=limit)

    # Summarise which signals were active
    signals = []
    if live_location:
        signals.append("live_location")
    if user and user.get("search_history"):
        signals.append("search_history")
    if user and user.get("viewed_properties"):
        signals.append("viewed_properties")
    if user and user.get("budget_range"):
        signals.append("budget_range")

    return {
        "success":         True,
        "user_id":         user_id,
        "count":           len(recs),
        "signals_used":    signals,
        "recommendations": recs,
    }