"""
Shared utility helpers for Brickfolio backend
"""
import math
import requests
from datetime import datetime
from fastapi import Request


# ─── Price Formatting ─────────────────────────────────────────────────────

def format_price(price: int) -> str:
    """Convert raw int price to Indian display string."""
    if not price:
        return "₹ On Request"
    if price >= 10_000_000:
        return f"₹{price / 10_000_000:.1f} Cr"
    if price >= 100_000:
        return f"₹{price // 100_000} Lakh"
    return f"₹{price:,}"


# ─── Geo Distance ─────────────────────────────────────────────────────────

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in km between two lat/lng coordinates."""
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi    = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ─── IP Location ──────────────────────────────────────────────────────────

def get_location_from_ip(ip: str) -> dict:
    """
    Detect approximate city + coordinates from an IP address.
    Falls back to Pune if detection fails.
    """
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        data = resp.json()
        if data.get("status") == "success":
            return {
                "city":      data.get("city", "Pune"),
                "latitude":  data.get("lat", 18.5204),
                "longitude": data.get("lon", 73.8567),
                "source":    "ip",
            }
    except Exception:
        pass
    return {"city": "Pune", "latitude": 18.5204, "longitude": 73.8567, "source": "default"}


def get_client_ip(request: Request) -> str:
    """Extract real client IP, honouring X-Forwarded-For in production."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


# ─── Badge Helper ─────────────────────────────────────────────────────────

def badge_css_class(badge: str) -> str:
    """Map a property badge string to a CSS class name."""
    if not badge:
        return "default"
    b = badge.lower()
    if "ready" in b or "move" in b:
        return "ready"
    if "new" in b or "launch" in b:
        return "new"
    if "luxury" in b or "premium" in b or "penthouse" in b:
        return "luxury"
    if "hot" in b or "limited" in b:
        return "hot"
    if "plot" in b:
        return "plot"
    return "default"


# ─── Pagination ───────────────────────────────────────────────────────────

def paginate(total: int, page: int, limit: int) -> dict:
    """Return pagination metadata."""
    return {
        "total":  total,
        "page":   page,
        "limit":  limit,
        "pages":  math.ceil(total / limit) if limit else 1,
        "has_next": page * limit < total,
        "has_prev": page > 1,
    }


# ─── Timestamp ────────────────────────────────────────────────────────────

def utc_now_str() -> str:
    return datetime.utcnow().isoformat() + "Z"