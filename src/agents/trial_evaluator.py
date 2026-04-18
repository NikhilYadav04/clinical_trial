"""
Trial Evaluator

Orchestrates the per-trial evaluation pipeline:
  1. Parse eligibility criteria
  2. Check inclusion/exclusion against patient
  3. Evaluate logistics
  4. Compute quality score
  5. Compute weighted final score

This is called in parallel for each trial in the LangGraph fan-out.
"""

from src.state import PatientProfile, TrialRecord
from src.agents.eligibility_parser_agent import parse_eligibility_criteria
from src.agents.inclusion_exclusion_agent import check_eligibility
from src.agents.logistics_agent import evaluate_logistics


# ── Quality scoring ───────────────────────────────────────────────────────────

PHASE_SCORES = {
    "PHASE1": 40,
    "EARLY_PHASE1": 30,
    "PHASE2": 65,
    "PHASE3": 90,
    "PHASE4": 85,
}

REPUTABLE_SPONSORS = [
    "national cancer institute", "nih", "nci", "astrazeneca", "pfizer",
    "roche", "novartis", "bristol-myers squibb", "bms", "merck", "johnson",
    "eli lilly", "abbvie", "genentech", "amgen", "biogen", "regeneron",
    "national institutes of health", "mayo clinic", "md anderson",
    "memorial sloan kettering", "johns hopkins", "mass general",
]


def _compute_quality_score(trial: TrialRecord) -> float:
    """Score a trial on phase, sponsor credibility, and enrollment pace (0-100)."""
    score = 50.0  # Baseline

    # Phase score
    phase = (trial.phase or "").upper()
    for phase_key, phase_score in PHASE_SCORES.items():
        if phase_key in phase:
            score = phase_score
            break

    # Sponsor credibility boost
    sponsor = (trial.sponsor or "").lower()
    if any(rep in sponsor for rep in REPUTABLE_SPONSORS):
        score = min(100, score + 10)

    # Enrollment data — if enrollment target is large and trial is still recruiting, good sign
    if trial.enrollment_target and trial.enrollment_target > 200:
        score = min(100, score + 5)

    return round(score, 1)


def _compute_final_score(
    eligibility_score: float,
    logistics_score: float,
    quality_score: float,
    biomarker_match: bool,
    hard_stop_fails: int = 0,
    pass_count: int = 0,
    total_criteria: int = 0,
) -> float:
    """
    Weighted composite score (0-100).

    Weights:
      Eligibility match:          60%
      Biomarker/disease align:    10%
      Trial quality & phase:      20%
      Logistics feasibility:      10%

    Penalty rules (applied in order):
      1. Any hard-stop FAIL        → cap at 25  (disqualified)
      2. Pass ratio < 20%          → cap at 25  (too little evidence of fit)
         Prevents trials with all-UNCERTAIN criteria from ranking as matches.
    """
    biomarker_score = 90.0 if biomarker_match else 50.0

    final = (
        eligibility_score * 0.60
        + biomarker_score  * 0.10
        + quality_score    * 0.20
        + logistics_score  * 0.10
    )
    final = round(final, 1)

    # Penalty 1 — hard-stop fails
    if hard_stop_fails > 0:
        return min(final, 25.0)

    # Penalty 2 — minimum confidence gate (at least 20% actual PASSes)
    if total_criteria > 0 and (pass_count / total_criteria) < 0.20:
        return min(final, 25.0)

    # Penalty 3 — high uncertainty gate (>60% UNCERTAIN = not enough info to recommend)
    uncertain_count = total_criteria - pass_count - hard_stop_fails
    if total_criteria > 0 and (uncertain_count / total_criteria) > 0.60:
        return min(final, 25.0)

    return final


def _check_biomarker_match(patient: PatientProfile, trial: TrialRecord) -> bool:
    """Check if any patient biomarkers appear in the trial title or interventions."""
    search_text = (
        (trial.title or "") + " " +
        " ".join(trial.interventions) + " " +
        (trial.brief_summary or "")
    ).lower()

    for biomarker in patient.biomarkers:
        # Simplify biomarker to key terms for fuzzy match
        terms = biomarker.lower().replace("+", "").replace("-", " ").split()
        if any(term in search_text for term in terms if len(term) > 3):
            return True
    return False


# ── Main evaluation function ──────────────────────────────────────────────────

def evaluate_trial(patient: PatientProfile, trial: TrialRecord) -> TrialRecord:
    """
    Run the full evaluation pipeline for a single trial.
    Returns the trial with all scores and breakdowns populated.
    """
    nct_id = trial.nct_id
    print(f"  [Evaluator] Evaluating {nct_id}: {trial.title[:60]}...")

    # 1. Parse eligibility criteria
    criteria = []
    if trial.eligibility_criteria_raw:
        try:
            criteria = parse_eligibility_criteria(trial.eligibility_criteria_raw, nct_id)
        except Exception as e:
            print(f"  [Evaluator] Eligibility parsing failed for {nct_id}: {e}")

    # 2. Check inclusion/exclusion
    try:
        eligibility_result = check_eligibility(patient, criteria, nct_id)
        trial.eligibility_score = eligibility_result.eligibility_score
        trial.eligibility_breakdown = [v.model_dump() for v in eligibility_result.verdicts]
    except Exception as e:
        print(f"  [Evaluator] Eligibility check failed for {nct_id}: {e}")
        trial.eligibility_score = 50.0
        trial.eligibility_breakdown = []

    # 3. Evaluate logistics
    try:
        logistics = evaluate_logistics(patient, trial)
        trial.logistics_score = logistics["logistics_score"]
        trial.nearest_site_miles = logistics["nearest_site_miles"]
    except Exception as e:
        print(f"  [Evaluator] Logistics eval failed for {nct_id}: {e}")
        trial.logistics_score = 50.0

    # 4. Quality score (no LLM call — rule-based)
    trial.quality_score = _compute_quality_score(trial)

    # 5. Biomarker match check
    biomarker_match = _check_biomarker_match(patient, trial)

    # 6. Final weighted score
    n_hard_fails = sum(
        1 for v in trial.eligibility_breakdown
        if v.get("verdict") == "FAIL" and v.get("is_hard_stop")
    )
    n_pass = sum(
        1 for v in trial.eligibility_breakdown
        if v.get("verdict") == "PASS"
    )
    n_total = len(trial.eligibility_breakdown)

    trial.final_score = _compute_final_score(
        eligibility_score=trial.eligibility_score or 50.0,
        logistics_score=trial.logistics_score or 50.0,
        quality_score=trial.quality_score or 50.0,
        biomarker_match=biomarker_match,
        hard_stop_fails=n_hard_fails,
        pass_count=n_pass,
        total_criteria=n_total,
    )

    print(f"  [Evaluator] {nct_id} scored {trial.final_score}/100")
    return trial
