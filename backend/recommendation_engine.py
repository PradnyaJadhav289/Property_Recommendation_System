"""
recommendation_engine.py — Brickfolio AI Recommendation Engine

Scoring signals (total 110 pts):
  1. Location affinity   30 pts  — matches user's searched / interested locations
  2. Budget match        25 pts  — how well price fits stored budget_range
  3. Property type       20 pts  — inferred from viewed_properties history
  4. Feature similarity  15 pts  — cosine similarity via scikit-learn (optional)
  5. Proximity           10 pts  — haversine distance from live GPS coordinates
  6. Collaborative       10 pts  — what similar users also viewed
"""

import math
from database import db

try:
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("⚠️  scikit-learn not found — feature similarity disabled (pip install scikit-learn)")


# ── Constants ─────────────────────────────────────────────────────────────
PROPERTY_TYPES = ["1BHK", "2BHK", "3BHK", "4BHK", "VILLA", "PLOT", "STUDIO"]
PUNE_LOCATIONS = [
    "Wakad", "Hinjewadi", "Baner", "Balewadi", "Kharadi",
    "Viman Nagar", "Kalyani Nagar", "Aundh", "Pimpri", "Chinchwad",
    "Sus Road", "Pashan", "Hadapsar", "Koregaon Park", "Shivajinagar",
]


class RecommendationEngine:
    """
    Usage:
        engine = RecommendationEngine()
        recs   = engine.get_recommendations(user, live_location, limit=10)
    """

    # ── Public API ────────────────────────────────────────────────────────

    def get_recommendations(
        self,
        user: dict | None,
        live_location: dict | None,
        limit: int = 10,
    ) -> list:
        """Return top-N ranked properties for a user."""
        all_props = list(db.properties.find({}, {"_id": 0}))
        if not all_props:
            return []

        # New / anonymous user — rank by proximity or return featured first
        if not user:
            if live_location:
                return self._rank_by_proximity(all_props, live_location, limit)
            featured = [p for p in all_props if p.get("featured")]
            return (featured + [p for p in all_props if not p.get("featured")])[:limit]

        scored = self._score_all(all_props, user, live_location)
        scored.sort(key=lambda x: x["_score"], reverse=True)

        # Strip internal scoring keys before returning
        results = []
        for p in scored[:limit]:
            p.pop("_score", None)
            p.pop("_score_breakdown", None)
            results.append(p)
        return results

    # ── Collaborative filtering ───────────────────────────────────────────

    def get_collaborative_score(
        self,
        property_id: str,
        viewed_ids: set,
        current_user_id: str = "",
        limit: int = 50,
    ) -> float:
        """
        Collaborative filtering — 'users who viewed what you viewed also viewed this'.
        Returns a 0.0–1.0 score based on how often similar users viewed this property.

        Steps:
          1. Find other users who share at least 1 viewed property with the current user.
          2. Collect every property those similar users viewed (excluding already-seen ones).
          3. Normalise the co-view count to 0.0–1.0.
        """
        if not viewed_ids:
            return 0.0

        # Step 1: find similar users — exclude the current user
        query: dict = {"viewed_properties": {"$in": list(viewed_ids)}}
        if current_user_id:
            query["user_id"] = {"$ne": current_user_id}

        similar_users = list(
            db.users.find(query, {"viewed_properties": 1}).limit(limit)
        )

        if not similar_users:
            return 0.0

        # Step 2: count how often each unseen property appears across similar users
        co_viewed: dict = {}
        for u in similar_users:
            for pid in u.get("viewed_properties", []):
                if pid not in viewed_ids:          # skip what current user already saw
                    co_viewed[pid] = co_viewed.get(pid, 0) + 1

        if property_id not in co_viewed:
            return 0.0

        # Step 3: normalise — property seen by all similar users → 1.0
        max_count = max(co_viewed.values())
        return co_viewed[property_id] / max_count

    # ── Scoring pipeline ─────────────────────────────────────────────────

    def _score_all(
        self,
        properties: list,
        user: dict,
        live_location: dict | None,
    ) -> list:
        search_history  = user.get("search_history", [])
        viewed_ids      = set(user.get("viewed_properties", []))
        interested_locs = user.get("interested_locations", [])
        budget          = user.get("budget_range") or {}
        budget_min      = budget.get("min", 0)
        budget_max      = budget.get("max", 999_999_999)
        current_uid     = user.get("user_id", "")

        # Derive preference signals once — reuse for every property
        searched_locs     = [s.get("location", "") for s in search_history if s.get("location")]
        all_interest_locs = list(set(interested_locs + searched_locs))
        preferred_types   = self._infer_preferred_types(viewed_ids)
        viewed_vectors    = self._get_viewed_vectors(viewed_ids) if ML_AVAILABLE else None

        scored = []
        for prop in properties:
            score     = 0.0
            breakdown = {}

            # 1. Location affinity (0–30 pts)
            loc = self._location_score(prop, all_interest_locs)
            score += loc * 30
            breakdown["location"] = round(loc * 30, 2)

            # 2. Budget match (0–25 pts)
            bud = self._budget_score(prop.get("price", 0), budget_min, budget_max)
            score += bud * 25
            breakdown["budget"] = round(bud * 25, 2)

            # 3. Property type (0–20 pts)
            typ = self._type_score(prop.get("property_type", ""), preferred_types)
            score += typ * 20
            breakdown["property_type"] = round(typ * 20, 2)

            # 4. Feature similarity (0–15 pts) — only when sklearn is installed
            if viewed_vectors is not None:
                sim = self._cosine_score(prop, viewed_vectors)
                score += sim * 15
                breakdown["similarity"] = round(sim * 15, 2)

            # 5. Proximity (0–10 pts)
            if live_location:
                prox = self._proximity_score(
                    prop.get("latitude", 0),
                    prop.get("longitude", 0),
                    live_location["latitude"],
                    live_location["longitude"],
                )
                score += prox * 10
                breakdown["proximity"] = round(prox * 10, 2)

            # 6. Collaborative signal (0–10 pts) — other users' behaviour
            collab = self.get_collaborative_score(
                prop.get("property_id", ""),
                viewed_ids,
                current_user_id=current_uid,
            )
            score += collab * 10
            breakdown["collaborative"] = round(collab * 10, 2)

            # Penalty: property already viewed — surface fresh content
            if prop.get("property_id") in viewed_ids:
                score *= 0.25

            prop["_score"]           = round(score, 3)
            prop["_score_breakdown"] = breakdown
            scored.append(prop)

        return scored

    # ── Signal functions ─────────────────────────────────────────────────

    def _location_score(self, prop: dict, interest_locs: list) -> float:
        if not interest_locs:
            return 0.0
        prop_loc = prop.get("location", "").lower()
        for loc in interest_locs:
            if not loc:
                continue
            loc_l = loc.lower()
            if loc_l in prop_loc:
                return 1.0
            # Partial word match — e.g. "Hinjewadi" matches "Hinjewadi Phase 1"
            if any(word in prop_loc for word in loc_l.split() if len(word) > 3):
                return 0.6
        return 0.0

    def _budget_score(self, price: int, budget_min: int, budget_max: int) -> float:
        if not price:
            return 0.5
        # No budget set → neutral
        if budget_min == 0 and budget_max == 999_999_999:
            return 0.5
        if budget_min <= price <= budget_max:
            return 1.0
        if price < budget_min:
            deviation = (budget_min - price) / max(budget_min, 1)
            return max(0.0, 1.0 - deviation)
        # price > budget_max — penalise more steeply
        deviation = (price - budget_max) / max(budget_max, 1)
        return max(0.0, 1.0 - deviation * 2)

    def _type_score(self, prop_type: str, preferred_types: list) -> float:
        if not preferred_types:
            return 0.3   # neutral for new users
        prop_upper = prop_type.upper()
        for pt in preferred_types:
            if pt.upper() in prop_upper or prop_upper in pt.upper():
                return 1.0
        return 0.0

    def _cosine_score(self, prop: dict, viewed_vectors: list) -> float:
        try:
            prop_vec = np.array(self._vectorize(prop)).reshape(1, -1)
            mean_vec = np.mean(viewed_vectors, axis=0).reshape(1, -1)
            sim      = cosine_similarity(prop_vec, mean_vec)[0][0]
            return float(max(0.0, sim))
        except Exception:
            return 0.0

    def _proximity_score(
        self, plat: float, plng: float, ulat: float, ulng: float
    ) -> float:
        dist = self.haversine(ulat, ulng, plat, plng)
        if dist <= 5:
            return 1.0
        if dist <= 30:
            return max(0.0, 1.0 - (dist - 5) / 25)
        return 0.0

    # ── Helpers ───────────────────────────────────────────────────────────

    def _infer_preferred_types(self, viewed_ids: set) -> list:
        if not viewed_ids:
            return []
        props = list(db.properties.find(
            {"property_id": {"$in": list(viewed_ids)}},
            {"property_type": 1},
        ))
        counts: dict = {}
        for p in props:
            t = p.get("property_type", "")
            counts[t] = counts.get(t, 0) + 1
        return sorted(counts, key=counts.get, reverse=True)[:2]

    def _get_viewed_vectors(self, viewed_ids: set):
        if not viewed_ids:
            return None
        props = list(db.properties.find(
            {"property_id": {"$in": list(viewed_ids)}},
            {"_id": 0},
        ))
        if not props:
            return None
        return [self._vectorize(p) for p in props]

    def _vectorize(self, prop: dict) -> list:
        """Encode a property as a numeric feature vector for cosine similarity."""
        price    = prop.get("price",     5_000_000) / 10_000_000.0
        bedrooms = prop.get("bedrooms",  2)          /  5.0
        size     = prop.get("size_sqft", 1000)       / 5000.0
        lat      = (prop.get("latitude",  18.5) - 18.0) / 2.0
        lng      = (prop.get("longitude", 73.8) - 73.0) / 2.0

        ptype    = prop.get("property_type", "2BHK").upper()
        type_vec = [1 if t in ptype else 0 for t in PROPERTY_TYPES]

        loc     = prop.get("location", "")
        loc_vec = [1 if l.lower() in loc.lower() else 0 for l in PUNE_LOCATIONS]

        return [price, bedrooms, size, lat, lng] + type_vec + loc_vec

    def _rank_by_proximity(
        self, properties: list, live_location: dict, limit: int
    ) -> list:
        for p in properties:
            p["distance_km"] = round(
                self.haversine(
                    live_location["latitude"],
                    live_location["longitude"],
                    p.get("latitude", 0),
                    p.get("longitude", 0),
                ),
                1,
            )
        return sorted(properties, key=lambda x: x["distance_km"])[:limit]

    # ── Static utility ────────────────────────────────────────────────────

    @staticmethod
    def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Return the great-circle distance in km between two coordinates."""
        R    = 6371
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi    = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = (
            math.sin(dphi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        )
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))