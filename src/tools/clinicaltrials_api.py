"""
ClinicalTrials.gov REST API v2 wrapper.
Docs: https://clinicaltrials.gov/data-api/api
No API key required.
"""

import requests
from typing import Optional
from src.state import TrialRecord
from src.utils.retry import with_retry


BASE_URL = "https://clinicaltrials.gov/api/v2"


@with_retry(max_attempts=3, base_delay=1.0, exceptions=(requests.RequestException,))
def _fetch_json(url: str, params: dict) -> dict:
    """GET request with automatic retry on network/HTTP errors."""
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def search_trials(
    condition: str,
    location: Optional[str] = None,
    distance_miles: Optional[int] = None,
    status: str = "RECRUITING",
    max_results: int = 50,
) -> list[TrialRecord]:
    """
    Search ClinicalTrials.gov for trials matching a condition.

    Args:
        condition:      Disease/condition to search for (e.g. "lung cancer EGFR")
        location:       City/state or zip code (e.g. "Boston, MA")
        distance_miles: Radius around location in miles
        status:         Trial status filter (RECRUITING | ACTIVE_NOT_RECRUITING | ALL)
        max_results:    Max number of trials to return

    Returns:
        List of TrialRecord objects with metadata populated.
    """
    params = {
        "query.cond": condition,
        "filter.overallStatus": status,
        "pageSize": min(max_results, 100),
        "format": "json",
    }

    if location:
        params["query.locn"] = location
    # Note: distance filtering is handled post-fetch by the logistics agent (Haversine)
    # ClinicalTrials.gov v2 distance filter requires aggFilters with geo coords — not used here

    try:
        data = _fetch_json(f"{BASE_URL}/studies", params)
    except requests.RequestException as e:
        raise RuntimeError(f"ClinicalTrials.gov API error: {e}")

    trials = []
    for study in data.get("studies", []):
        proto = study.get("protocolSection", {})
        trial = _parse_study(proto)
        if trial:
            trials.append(trial)

    return trials


def get_trial_details(nct_id: str) -> Optional[TrialRecord]:
    """Fetch full details for a single trial by NCT ID."""
    try:
        data = _fetch_json(f"{BASE_URL}/studies/{nct_id}", {"format": "json"})
    except requests.RequestException as e:
        raise RuntimeError(f"ClinicalTrials.gov API error for {nct_id}: {e}")

    proto = data.get("protocolSection", {})
    return _parse_study(proto)


def _parse_study(proto: dict) -> Optional[TrialRecord]:
    """Parse a protocolSection dict into a TrialRecord."""
    try:
        id_module = proto.get("identificationModule", {})
        status_module = proto.get("statusModule", {})
        desc_module = proto.get("descriptionModule", {})
        eligibility_module = proto.get("eligibilityModule", {})
        design_module = proto.get("designModule", {})
        sponsor_module = proto.get("sponsorCollaboratorsModule", {})
        conditions_module = proto.get("conditionsModule", {})
        interventions_module = proto.get("armsInterventionsModule", {})
        contacts_module = proto.get("contactsLocationsModule", {})

        nct_id = id_module.get("nctId", "")
        if not nct_id:
            return None

        # Phase
        phases = design_module.get("phases", [])
        phase = phases[0] if phases else None

        # Interventions
        interventions = [
            i.get("name", "")
            for i in interventions_module.get("interventions", [])
            if i.get("name")
        ]

        # Locations
        locations = []
        for loc in contacts_module.get("locations", []):
            locations.append({
                "facility": loc.get("facility", ""),
                "city": loc.get("city", ""),
                "state": loc.get("state", ""),
                "country": loc.get("country", ""),
            })

        # Enrollment
        enrollment_info = status_module.get("enrollmentInfo", {})
        enrollment_target = enrollment_info.get("count")

        return TrialRecord(
            nct_id=nct_id,
            title=id_module.get("briefTitle", ""),
            status=status_module.get("overallStatus", ""),
            phase=phase,
            sponsor=sponsor_module.get("leadSponsor", {}).get("name"),
            conditions=conditions_module.get("conditions", []),
            interventions=interventions,
            eligibility_criteria_raw=eligibility_module.get("eligibilityCriteria"),
            locations=locations,
            start_date=status_module.get("startDateStruct", {}).get("date"),
            completion_date=status_module.get("completionDateStruct", {}).get("date"),
            enrollment_target=enrollment_target,
            brief_summary=desc_module.get("briefSummary"),
            url=f"https://clinicaltrials.gov/study/{nct_id}",
        )
    except Exception:
        return None
