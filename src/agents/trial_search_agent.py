"""
Trial Search Agent

Uses the structured patient profile to query ClinicalTrials.gov
and return a longlist of candidate trials for deeper evaluation.
"""

from src.state import GraphState, PatientProfile, TrialRecord
from src.tools.clinicaltrials_api import search_trials


def _build_search_query(profile: PatientProfile) -> str:
    """
    Build a safe ClinicalTrials.gov search query.
    Uses diagnosis only — biomarkers cause 400 errors due to special characters (%, +).
    Biomarker matching is handled later by the evaluator agents.
    """
    import re
    # Strip any special characters that break the API query
    diagnosis = re.sub(r"[%+&]", "", profile.diagnosis).strip()
    return diagnosis


def trial_search_agent(state: GraphState) -> dict:
    """
    LangGraph node — queries ClinicalTrials.gov and returns candidate trial list.
    Updates state with: candidate_trials, status_log
    """
    profile = state.get("patient_profile")

    if not profile:
        return {
            "status_log": ["Trial Search Agent skipped — no patient profile available"],
            "error": "No patient profile found",
        }

    query = _build_search_query(profile)
    location = profile.location
    max_travel = profile.max_travel_miles or 100

    print(f"\n[Trial Search Agent] Searching for: '{query}'")
    print(f"[Trial Search Agent] Location: {location}, Radius: {max_travel} miles")

    # Primary search — recruiting trials
    trials: list[TrialRecord] = []

    try:
        recruiting_trials = search_trials(
            condition=query,
            location=location,
            distance_miles=max_travel,
            status="RECRUITING",
            max_results=50,
        )
        trials.extend(recruiting_trials)
        print(f"[Trial Search Agent] Found {len(recruiting_trials)} RECRUITING trials")
    except RuntimeError as e:
        print(f"[Trial Search Agent] Primary search error: {e}")

    # Fallback — broader search without location filter if < 10 results
    if len(trials) < 10 and location:
        print("[Trial Search Agent] Too few local results — broadening search nationally...")
        try:
            national_trials = search_trials(
                condition=profile.diagnosis,  # simpler query without biomarkers
                status="RECRUITING",
                max_results=50,
            )
            # Deduplicate by NCT ID
            existing_ids = {t.nct_id for t in trials}
            new_trials = [t for t in national_trials if t.nct_id not in existing_ids]
            trials.extend(new_trials)
            print(f"[Trial Search Agent] Added {len(new_trials)} national trials")
        except RuntimeError as e:
            print(f"[Trial Search Agent] National search error: {e}")

    # Filter by preferred phases if specified
    if profile.preferred_phases:
        phase_map = {
            1: ["PHASE1", "PHASE_1", "EARLY_PHASE1"],
            2: ["PHASE2", "PHASE_2"],
            3: ["PHASE3", "PHASE_3"],
            4: ["PHASE4", "PHASE_4"],
        }
        allowed_phases = set()
        for p in profile.preferred_phases:
            allowed_phases.update(phase_map.get(p, []))

        filtered = [
            t for t in trials
            if t.phase is None or t.phase.upper() in allowed_phases
        ]
        if filtered:
            print(f"[Trial Search Agent] Phase filter applied: {len(trials)} -> {len(filtered)} trials")
            trials = filtered

    print(f"[Trial Search Agent] Final candidate list: {len(trials)} trials")

    return {
        "candidate_trials": trials,
        "status_log": [
            f"Trial search complete: {len(trials)} candidates found for '{profile.diagnosis}'"
        ],
    }
