"""
Property routes for Brickfolio
GET  /properties            – list with filters + pagination
GET  /properties/nearby     – proximity search by lat/lng
GET  /properties/{id}       – single property detail
GET  /seed-data             – seed MongoDB with sample data
"""
import math
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from database import db
from utils.helpers import haversine, paginate, format_price

router = APIRouter(prefix="/properties", tags=["Properties"])


@router.get("")
async def get_properties(
    location:      Optional[str] = Query(None),
    min_price:     Optional[int] = Query(None),
    max_price:     Optional[int] = Query(None),
    property_type: Optional[str] = Query(None),
    bedrooms:      Optional[int] = Query(None),
    page:          int           = Query(1, ge=1),
    limit:         int           = Query(12, ge=1, le=50),
):
    """Return all properties with optional filters and pagination."""
    query: dict = {}

    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    if property_type:
        query["property_type"] = {"$regex": property_type, "$options": "i"}
    if bedrooms is not None:
        query["bedrooms"] = bedrooms

    price_filter: dict = {}
    if min_price is not None:
        price_filter["$gte"] = min_price
    if max_price is not None:
        price_filter["$lte"] = max_price
    if price_filter:
        query["price"] = price_filter

    skip  = (page - 1) * limit
    total = db.properties.count_documents(query)
    props = list(db.properties.find(query, {"_id": 0}).skip(skip).limit(limit))

    return {
        "success":    True,
        "properties": props,
        **paginate(total, page, limit),
    }


@router.get("/nearby")
async def get_nearby(
    lat:       float = Query(...),
    lng:       float = Query(...),
    radius_km: float = Query(10),
    limit:     int   = Query(8, ge=1, le=20),
):
    """Return properties within radius_km of a given coordinate."""
    all_props = list(db.properties.find({}, {"_id": 0}))
    nearby = []
    for p in all_props:
        dist = haversine(lat, lng, p.get("latitude", 0), p.get("longitude", 0))
        if dist <= radius_km:
            p["distance_km"] = round(dist, 1)
            nearby.append(p)

    nearby.sort(key=lambda x: x["distance_km"])
    return {"success": True, "count": len(nearby[:limit]), "properties": nearby[:limit]}


@router.get("/featured")
async def get_featured(limit: int = Query(6, ge=1, le=12)):
    """Return featured properties."""
    props = list(db.properties.find({"featured": True}, {"_id": 0}).limit(limit))
    return {"success": True, "properties": props}


@router.get("/seed-data/run")
async def seed_data():
    """Drop and re-seed properties collection with sample Pune data."""
    from seed_properties import PROPERTIES
    db.properties.drop()
    db.properties.insert_many(PROPERTIES)
    return {"success": True, "inserted": len(PROPERTIES), "message": "Database seeded!"}


@router.get("/{property_id}")
async def get_property(property_id: str):
    """Return a single property by its ID."""
    prop = db.properties.find_one({"property_id": property_id}, {"_id": 0})
    if not prop:
        raise HTTPException(status_code=404, detail=f"Property '{property_id}' not found")
    return {"success": True, "property": prop}