"""
Logistics Agent

Evaluates the practical feasibility of a clinical trial for a patient:
- Distance to nearest site (dynamic geocoding via Nominatim/OpenStreetMap)
- Estimated visit burden
- Financial assistance availability

Geocoding strategy:
  1. In-memory cache (instant — avoids repeat API calls within a run)
  2. Hardcoded fallback dict (instant — covers 20 common US cities)
  3. Nominatim via RateLimiter (1 req/sec — free, global, no API key)
  4. None — defaults to neutral logistics score of 50
"""

import math
import time
import logging
from src.state import PatientProfile, TrialRecord

logger = logging.getLogger(__name__)

# ── In-memory geocode cache (shared across all trial evaluations in a run) ────
_geocode_cache: dict[str, tuple[float, float] | None] = {}

# ── Nominatim geolocator (lazy init) ─────────────────────────────────────────
_geolocator = None
_rate_limiter = None

def _get_geolocator():
    global _geolocator, _rate_limiter
    if _geolocator is None:
        try:
            from geopy.geocoders import Nominatim
            from geopy.extra.rate_limiter import RateLimiter
            _geolocator = Nominatim(user_agent="clinical-trial-matcher-v1", timeout=5)
            _rate_limiter = RateLimiter(
                _geolocator.geocode,
                min_delay_seconds=1.1,   # slightly over 1s to stay safe
                max_retries=1,
                error_wait_seconds=2.0,
                swallow_exceptions=True, # never crash — just return None
            )
        except ImportError:
            logger.warning("[Logistics] geopy not installed — using hardcoded coords only")
    return _rate_limiter


# ── Hardcoded fallback (20 common US trial hub cities) ───────────────────────
_CITY_COORDS_FALLBACK: dict[str, tuple[float, float]] = {
    "boston, ma":        (42.3601, -71.0589),
    "new york, ny":      (40.7128, -74.0060),
    "los angeles, ca":   (34.0522, -118.2437),
    "chicago, il":       (41.8781, -87.6298),
    "houston, tx":       (29.7604, -95.3698),
    "philadelphia, pa":  (39.9526, -75.1652),
    "phoenix, az":       (33.4484, -112.0740),
    "san antonio, tx":   (29.4241, -98.4936),
    "san diego, ca":     (32.7157, -117.1611),
    "dallas, tx":        (32.7767, -96.7970),
    "san francisco, ca": (37.7749, -122.4194),
    "seattle, wa":       (47.6062, -122.3321),
    "denver, co":        (39.7392, -104.9903),
    "atlanta, ga":       (33.7490, -84.3880),
    "miami, fl":         (25.7617, -80.1918),
    "minneapolis, mn":   (44.9778, -93.2650),
    "cleveland, oh":     (41.4993, -81.6944),
    "baltimore, md":     (39.2904, -76.6122),
    "pittsburgh, pa":    (40.4406, -79.9959),
    "nashville, tn":     (36.1627, -86.7816),
}


def _geocode(query: str) -> tuple[float, float] | None:
    """
    Resolve a location string to (lat, lon).
    Tries cache → hardcoded fallback → Nominatim API.
    Never raises — returns None on failure.
    """
    key = query.lower().strip()

    # 1. Cache hit
    if key in _geocode_cache:
        return _geocode_cache[key]

    # 2. Hardcoded fallback
    if key in _CITY_COORDS_FALLBACK:
        _geocode_cache[key] = _CITY_COORDS_FALLBACK[key]
        return _CITY_COORDS_FALLBACK[key]

    # Partial match on hardcoded dict
    for city_key, coords in _CITY_COORDS_FALLBACK.items():
        if city_key.split(",")[0] in key:
            _geocode_cache[key] = coords
            return coords

    # 3. Nominatim API
    geocode_fn = _get_geolocator()
    if geocode_fn:
        try:
            result = geocode_fn(query)
            if result:
                coords = (result.latitude, result.longitude)
                _geocode_cache[key] = coords
                return coords
        except Exception as exc:
            logger.debug("[Logistics] Nominatim failed for '%s': %s", query, exc)

    # 4. Give up — cache the miss so we don't retry
    _geocode_cache[key] = None
    return None


def _detect_patient_location(location_str: str) -> tuple[str, str]:
    """
    Extract (city, country) from a patient location string.
    Examples:
      "Boston, MA"                 → ("boston", "united states")
      "Mumbai, Maharashtra, India" → ("mumbai", "india")
      "New Delhi, India"           → ("new delhi", "india")
    """
    if not location_str:
        return ("", "")

    parts = [p.strip().lower() for p in location_str.split(",")]
    city  = parts[0] if parts else ""

    _COUNTRY_MAP = {
        "india":          "india",
        "china":          "china",
        "japan":          "japan",
        "germany":        "germany",
        "france":         "france",
        "united kingdom": "united kingdom",
        "uk":             "united kingdom",
        "canada":         "canada",
        "australia":      "australia",
        "brazil":         "brazil",
        "south korea":    "south korea",
        "korea":          "south korea",
        "italy":          "italy",
        "spain":          "spain",
        "netherlands":    "netherlands",
        "sweden":         "sweden",
        "switzerland":    "switzerland",
        "singapore":      "singapore",
        "mexico":         "mexico",
        "israel":         "israel",
    }

    last = parts[-1].strip() if parts else ""
    for keyword, country_name in _COUNTRY_MAP.items():
        if keyword in last:
            return (city, country_name)

    # 2-part "City, ST" → US state abbreviation
    if len(parts) == 2 and len(parts[1].strip()) == 2:
        return (city, "united states")

    # Default to US
    return (city, "united states")


def _sample_sites(
    sites: list[dict],
    patient_city: str,
    patient_country: str,
    max_other_city: int = 2,
) -> list[dict]:
    """
    Smart site sampling to minimize geocoding calls while keeping accuracy.

    Rules:
      1. Same city as patient          → include ALL  (most relevant)
      2. Same country, different city  → up to max_other_city per unique city
      3. Other countries               → 1 representative per country

    Falls back to first 5 sites if sampling yields nothing.
    """
    same_city:               list[dict]         = []
    same_country_by_city:    dict[str, list[dict]] = {}
    other_country_by_country: dict[str, list[dict]] = {}

    for site in sites:
        site_city    = (site.get("city",    "") or "").lower().strip()
        site_country = (site.get("country", "") or "united states").lower().strip()

        # Normalize common US variants
        if site_country in ("us", "usa", "united states of america"):
            site_country = "united states"

        is_same_city    = bool(patient_city)    and patient_city    in site_city
        is_same_country = bool(patient_country) and (
            patient_country in site_country or site_country in patient_country
        )

        if is_same_city:
            same_city.append(site)
        elif is_same_country:
            city_key = site_city or site.get("state", "unknown") or "unknown"
            same_country_by_city.setdefault(city_key, []).append(site)
        else:
            country_key = site_country or "unknown"
            other_country_by_country.setdefault(country_key, []).append(site)

    sampled: list[dict] = list(same_city)

    # Up to max_other_city per same-country city
    for city_sites in same_country_by_city.values():
        sampled.extend(city_sites[:max_other_city])

    # 1 representative per foreign country
    for country_sites in other_country_by_country.values():
        sampled.append(country_sites[0])

    return sampled if sampled else sites[:5]


def _build_location_query(city: str, state: str, country: str) -> str:
    """
    Build a clean Nominatim query from site fields.
    Works for US (city, state) and international (city, country).
    """
    parts = [p.strip() for p in [city, state, country] if p and p.strip()]
    return ", ".join(parts) if parts else ""


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in miles between two lat/lon points."""
    R = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi   = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _estimate_visit_burden(trial: TrialRecord) -> dict:
    """
    Estimate visit frequency and duration from trial metadata.
    Returns a dict with estimated burden info.
    """
    phase = (trial.phase or "").upper()
    interventions = " ".join(trial.interventions).lower()

    if "1" in phase:
        visits_per_month = 4
        duration_months  = 6
        burden_label     = "High"
    elif "2" in phase:
        visits_per_month = 2
        duration_months  = 12
        burden_label     = "Moderate"
    else:
        visits_per_month = 1
        duration_months  = 18
        burden_label     = "Low-Moderate"

    if any(w in interventions for w in ["infusion", "injection", "iv ", "intravenous"]):
        visits_per_month = max(visits_per_month, 2)

    return {
        "estimated_visits_per_month": visits_per_month,
        "estimated_duration_months":  duration_months,
        "total_estimated_visits":     visits_per_month * duration_months,
        "burden_label":               burden_label,
    }


def evaluate_logistics(patient: PatientProfile, trial: TrialRecord) -> dict:
    """
    Evaluate logistics feasibility for a patient + trial pair.

    Returns:
        dict with: nearest_site_miles, logistics_score (0-100), visit_burden, notes
    """
    result = {
        "nearest_site_miles": None,
        "nearest_site":       None,
        "logistics_score":    50.0,
        "visit_burden":       {},
        "notes":              [],
    }

    # ── Distance ─────────────────────────────────────────────────────────────
    patient_query  = patient.location or ""
    patient_coords = _geocode(patient_query)
    max_miles      = patient.max_travel_miles or 100

    patient_city, patient_country = _detect_patient_location(patient_query)

    if patient_coords and trial.locations:
        min_distance = float("inf")
        closest_site = None

        sites_to_check = _sample_sites(trial.locations, patient_city, patient_country)
        logger.debug(
            "[Logistics] %s: sampling %d/%d sites (city=%s, country=%s)",
            trial.nct_id, len(sites_to_check), len(trial.locations),
            patient_city, patient_country,
        )

        for site in sites_to_check:
            city    = site.get("city", "")
            state   = site.get("state", "")
            country = site.get("country", "United States")

            query = _build_location_query(city, state, country)
            if not query:
                continue

            site_coords = _geocode(query)
            if site_coords:
                dist = _haversine_miles(*patient_coords, *site_coords)
                if dist < min_distance:
                    min_distance = dist
                    closest_site = site

        if min_distance < float("inf"):
            result["nearest_site_miles"] = round(min_distance, 1)
            result["nearest_site"]       = closest_site
        else:
            result["notes"].append("Could not calculate distance — site coordinates unknown")

    elif not patient_coords:
        result["notes"].append("Patient location not recognized — distance not calculated")

    # ── Distance Score ────────────────────────────────────────────────────────
    dist = result["nearest_site_miles"]
    if dist is not None:
        if dist <= 25:
            dist_score = 100
        elif dist <= max_miles:
            dist_score = 100 - ((dist - 25) / (max_miles - 25)) * 50
        else:
            dist_score = max(0, 50 - ((dist - max_miles) / max_miles) * 50)
            result["notes"].append(
                f"Nearest site ({dist} mi) exceeds patient's max travel ({max_miles} mi)"
            )
    else:
        dist_score = 50

    # ── Visit Burden ──────────────────────────────────────────────────────────
    burden = _estimate_visit_burden(trial)
    result["visit_burden"] = burden

    if burden["burden_label"] == "High":
        burden_score = 60
    elif burden["burden_label"] == "Moderate":
        burden_score = 80
    else:
        burden_score = 100

    # ── Financial Assistance ──────────────────────────────────────────────────
    summary = (trial.brief_summary or "").lower()
    if any(w in summary for w in ["travel assistance", "reimbursement", "stipend", "compensation"]):
        result["notes"].append("Financial assistance / travel reimbursement mentioned")

    # ── Final Logistics Score ─────────────────────────────────────────────────
    result["logistics_score"] = round((dist_score * 0.6) + (burden_score * 0.4), 1)

    return result
