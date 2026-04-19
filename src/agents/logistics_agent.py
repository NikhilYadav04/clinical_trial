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
import json
import logging
from pathlib import Path
from src.state import PatientProfile, TrialRecord

logger = logging.getLogger(__name__)

# ── Persistent disk cache ─────────────────────────────────────────────────────
_CACHE_FILE = Path(__file__).parent.parent.parent / "src" / "cache" / "geocode_cache.json"

def _load_disk_cache() -> dict[str, tuple[float, float] | None]:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if _CACHE_FILE.exists():
            raw = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            return {k: tuple(v) if v else None for k, v in raw.items()}
    except Exception as exc:
        logger.debug("[Logistics] Could not load geocode cache: %s", exc)
    return {}

def _save_disk_cache(cache: dict) -> None:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(
            json.dumps({k: list(v) if v else None for k, v in cache.items()}, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.debug("[Logistics] Could not save geocode cache: %s", exc)

# ── In-memory geocode cache (pre-loaded from disk) ────────────────────────────
_geocode_cache: dict[str, tuple[float, float] | None] = _load_disk_cache()

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


# ── Hardcoded fallback — US cities + world capitals + major cities ────────────
_CITY_COORDS_FALLBACK: dict[str, tuple[float, float]] = {
    # ── US cities (state abbreviation format) ────────────────────────────────
    "boston, ma":           (42.3601, -71.0589),
    "new york, ny":         (40.7128, -74.0060),
    "los angeles, ca":      (34.0522, -118.2437),
    "chicago, il":          (41.8781, -87.6298),
    "houston, tx":          (29.7604, -95.3698),
    "philadelphia, pa":     (39.9526, -75.1652),
    "phoenix, az":          (33.4484, -112.0740),
    "san antonio, tx":      (29.4241, -98.4936),
    "san diego, ca":        (32.7157, -117.1611),
    "dallas, tx":           (32.7767, -96.7970),
    "san francisco, ca":    (37.7749, -122.4194),
    "seattle, wa":          (47.6062, -122.3321),
    "denver, co":           (39.7392, -104.9903),
    "atlanta, ga":          (33.7490, -84.3880),
    "miami, fl":            (25.7617, -80.1918),
    "minneapolis, mn":      (44.9778, -93.2650),
    "cleveland, oh":        (41.4993, -81.6944),
    "baltimore, md":        (39.2904, -76.6122),
    "pittsburgh, pa":       (40.4406, -79.9959),
    "nashville, tn":        (36.1627, -86.7816),
    "portland, or":         (45.5051, -122.6750),
    "las vegas, nv":        (36.1699, -115.1398),
    "memphis, tn":          (35.1495, -90.0490),
    "louisville, ky":       (38.2527, -85.7585),
    "richmond, va":         (37.5407, -77.4360),
    "new orleans, la":      (29.9511, -90.0715),
    "salt lake city, ut":   (40.7608, -111.8910),
    "hartford, ct":         (41.7658, -72.6851),
    "new haven, ct":        (41.3082, -72.9279),
    "rochester, mn":        (44.0121, -92.4802),
    "rochester, ny":        (43.1566, -77.6088),
    "buffalo, ny":          (42.8864, -78.8784),
    "albany, ny":           (42.6526, -73.7562),
    "detroit, mi":          (42.3314, -83.0458),
    "ann arbor, mi":        (42.2808, -83.7430),
    "columbus, oh":         (39.9612, -82.9988),
    "cincinnati, oh":       (39.1031, -84.5120),
    "indianapolis, in":     (39.7684, -86.1581),
    "milwaukee, wi":        (43.0389, -87.9065),
    "madison, wi":          (43.0731, -89.4012),
    "kansas city, mo":      (39.0997, -94.5786),
    "st. louis, mo":        (38.6270, -90.1994),
    "omaha, ne":            (41.2565, -95.9345),
    "oklahoma city, ok":    (35.4676, -97.5164),
    "tucson, az":           (32.2226, -110.9747),
    "albuquerque, nm":      (35.0844, -106.6504),
    "sacramento, ca":       (38.5816, -121.4944),
    "portland, me":         (43.6591, -70.2568),
    "burlington, vt":       (44.4759, -73.2121),
    "providence, ri":       (41.8240, -71.4128),
    "worcester, ma":        (42.2626, -71.8023),
    "springfield, ma":      (42.1015, -72.5898),
    "aurora, co":           (39.7294, -104.8319),
    "colorado springs, co": (38.8339, -104.8214),
    "jacksonville, fl":     (30.3322, -81.6557),
    "tampa, fl":            (27.9506, -82.4572),
    "orlando, fl":          (28.5383, -81.3792),
    "charlotte, nc":        (35.2271, -80.8431),
    "raleigh, nc":          (35.7796, -78.6382),
    "durham, nc":           (35.9940, -78.8986),
    "chapel hill, nc":      (35.9132, -79.0558),
    "greensboro, nc":       (36.0726, -79.7920),
    "columbia, sc":         (34.0007, -81.0348),
    "birmingham, al":       (33.5186, -86.8104),
    "little rock, ar":      (34.7465, -92.2896),
    "baton rouge, la":      (30.4515, -91.1871),
    "jackson, ms":          (32.2988, -90.1848),
    "charleston, wv":       (38.3498, -81.6326),
    "lexington, ky":        (38.0406, -84.5037),
    "des moines, ia":       (41.5868, -93.6250),
    "iowa city, ia":        (41.6611, -91.5302),
    "fargo, nd":            (46.8772, -96.7898),
    "sioux falls, sd":      (43.5446, -96.7311),
    "billings, mt":         (45.7833, -108.5007),
    "boise, id":            (43.6150, -116.2023),
    "spokane, wa":          (47.6588, -117.4260),
    "tacoma, wa":           (47.2529, -122.4443),
    "anchorage, ak":        (61.2181, -149.9003),
    "honolulu, hi":         (21.3069, -157.8583),
    # ── US by city name only (no state) ──────────────────────────────────────
    "boston":               (42.3601, -71.0589),
    "new york":             (40.7128, -74.0060),
    "los angeles":          (34.0522, -118.2437),
    "chicago":              (41.8781, -87.6298),
    "houston":              (29.7604, -95.3698),
    "philadelphia":         (39.9526, -75.1652),
    "san francisco":        (37.7749, -122.4194),
    "seattle":              (47.6062, -122.3321),
    "denver":               (39.7392, -104.9903),
    "atlanta":              (33.7490, -84.3880),
    "miami":                (25.7617, -80.1918),
    "minneapolis":          (44.9778, -93.2650),
    "baltimore":            (39.2904, -76.6122),
    "bethesda":             (38.9807, -77.1002),
    "rochester":            (44.0121, -92.4802),
    "ann arbor":            (42.2808, -83.7430),
    "stanford":             (37.4275, -122.1697),
    # ── World capitals ────────────────────────────────────────────────────────
    "london":               (51.5074, -0.1278),
    "paris":                (48.8566,  2.3522),
    "berlin":               (52.5200, 13.4050),
    "madrid":               (40.4168, -3.7038),
    "rome":                 (41.9028, 12.4964),
    "amsterdam":            (52.3676,  4.9041),
    "brussels":             (50.8503,  4.3517),
    "vienna":               (48.2082, 16.3738),
    "zurich":               (47.3769,  8.5417),
    "bern":                 (46.9481,  7.4474),
    "stockholm":            (59.3293, 18.0686),
    "oslo":                 (59.9139, 10.7522),
    "copenhagen":           (55.6761, 12.5683),
    "helsinki":             (60.1699, 24.9384),
    "warsaw":               (52.2297, 21.0122),
    "prague":               (50.0755, 14.4378),
    "budapest":             (47.4979, 19.0402),
    "bucharest":            (44.4268, 26.1025),
    "sofia":                (42.6977, 23.3219),
    "athens":               (37.9838, 23.7275),
    "lisbon":               (38.7223, -9.1393),
    "moscow":               (55.7558, 37.6173),
    "kyiv":                 (50.4501, 30.5234),
    "ankara":               (39.9334, 32.8597),
    "istanbul":             (41.0082, 28.9784),
    "toronto":              (43.6532, -79.3832),
    "montreal":             (45.5017, -73.5673),
    "vancouver":            (49.2827, -123.1207),
    "calgary":              (51.0447, -114.0719),
    "ottawa":               (45.4215, -75.6972),
    "mexico city":          (19.4326, -99.1332),
    "guadalajara":          (20.6597, -103.3496),
    "monterrey":            (25.6866, -100.3161),
    "bogota":               (-4.7110, -74.0721),
    "lima":                 (-12.0464, -77.0428),
    "santiago":             (-33.4489, -70.6693),
    "buenos aires":         (-34.6037, -58.3816),
    "sao paulo":            (-23.5505, -46.6333),
    "rio de janeiro":       (-22.9068, -43.1729),
    "brasilia":             (-15.7939, -47.8828),
    "caracas":              (10.4806, -66.9036),
    "quito":                (-0.1807, -78.4678),
    "tokyo":                (35.6762, 139.6503),
    "osaka":                (34.6937, 135.5023),
    "kyoto":                (35.0116, 135.7681),
    "beijing":              (39.9042, 116.4074),
    "shanghai":             (31.2304, 121.4737),
    "guangzhou":            (23.1291, 113.2644),
    "shenzhen":             (22.5431, 114.0579),
    "chengdu":              (30.5728, 104.0668),
    "seoul":                (37.5665, 126.9780),
    "busan":                (35.1796, 129.0756),
    "taipei":               (25.0330, 121.5654),
    "hong kong":            (22.3193, 114.1694),
    "singapore":            (1.3521,  103.8198),
    "mumbai":               (19.0760, 72.8777),
    "delhi":                (28.7041, 77.1025),
    "new delhi":            (28.6139, 77.2090),
    "bangalore":            (12.9716, 77.5946),
    "hyderabad":            (17.3850, 78.4867),
    "chennai":              (13.0827, 80.2707),
    "kolkata":              (22.5726, 88.3639),
    "pune":                 (18.5204, 73.8567),
    "ahmedabad":            (23.0225, 72.5714),
    "sydney":               (-33.8688, 151.2093),
    "melbourne":            (-37.8136, 144.9631),
    "brisbane":             (-27.4698, 153.0251),
    "perth":                (-31.9505, 115.8605),
    "auckland":             (-36.8485, 174.7633),
    "johannesburg":         (-26.2041, 28.0473),
    "cape town":            (-33.9249, 18.4241),
    "nairobi":              (-1.2921, 36.8219),
    "lagos":                (6.5244,  3.3792),
    "cairo":                (30.0444, 31.2357),
    "casablanca":           (33.5731, -7.5898),
    "tunis":                (36.8188,  10.1658),
    "tel aviv":             (32.0853, 34.7818),
    "jerusalem":            (31.7683, 35.2137),
    "dubai":                (25.2048, 55.2708),
    "abu dhabi":            (24.4539, 54.3773),
    "riyadh":               (24.7136, 46.6753),
    "tehran":               (35.6892, 51.3890),
    "bangkok":              (13.7563, 100.5018),
    "kuala lumpur":         (3.1390,  101.6869),
    "jakarta":              (-6.2088, 106.8456),
    "manila":               (14.5995, 120.9842),
    "ho chi minh city":     (10.8231, 106.6297),
    "hanoi":                (21.0285, 105.8542),
    "karachi":              (24.8607, 67.0011),
    "lahore":               (31.5204, 74.3587),
    "islamabad":            (33.6844, 73.0479),
    "dhaka":                (23.8103, 90.4125),
    "colombo":              (6.9271,  79.8612),
    "kathmandu":            (27.7172, 85.3240),
    "ulaanbaatar":          (47.8864, 106.9057),
    "warsaw, poland":       (52.2297, 21.0122),
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
                _save_disk_cache(_geocode_cache)
                return coords
        except Exception as exc:
            logger.debug("[Logistics] Nominatim failed for '%s': %s", query, exc)

    # 4. Give up — cache the miss so we don't retry
    _geocode_cache[key] = None
    _save_disk_cache(_geocode_cache)
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
    max_same_country_cities: int = 5,
    max_foreign_countries: int = 3,
) -> list[dict]:
    """
    Smart site sampling to minimize geocoding calls while keeping accuracy.

    Rules:
      1. Same city as patient          → include ALL  (most relevant, usually cached)
      2. Same country, different city  → 1 site from up to max_same_country_cities unique cities
      3. Other countries               → 1 site from up to max_foreign_countries unique countries
    """
    same_city:                list[dict]            = []
    same_country_by_city:     dict[str, list[dict]] = {}
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

    # 1 site per same-country city, capped at max_same_country_cities unique cities
    for city_sites in list(same_country_by_city.values())[:max_same_country_cities]:
        sampled.append(city_sites[0])

    # 1 site per foreign country, capped at max_foreign_countries
    for country_sites in list(other_country_by_country.values())[:max_foreign_countries]:
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
