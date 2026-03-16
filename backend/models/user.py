"""
User Pydantic models for Brickfolio
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


class BudgetRange(BaseModel):
    min: Optional[int] = 0
    max: Optional[int] = 99999999


class LiveLocation(BaseModel):
    latitude: float
    longitude: float
    updated_at: Optional[datetime] = None


class SearchEntry(BaseModel):
    query: str
    location: Optional[str] = None
    timestamp: Optional[str] = None


class UserProfile(BaseModel):
    user_id: str
    name: Optional[str] = "Guest"
    email: Optional[str] = None
    search_history: List[SearchEntry] = []
    interested_locations: List[str] = []
    viewed_properties: List[str] = []
    budget_range: Optional[BudgetRange] = BudgetRange()
    live_location: Optional[LiveLocation] = None


# ─── Request Bodies ────────────────────────────────────────────────────────

class TrackViewRequest(BaseModel):
    user_id: str
    property_id: str
    action_type: str = "view"   # view | click | search


class SearchRequest(BaseModel):
    user_id: str
    query: str
    location: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    property_type: Optional[str] = None


class LocationRequest(BaseModel):
    user_id: str
    latitude: float
    longitude: float