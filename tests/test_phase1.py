"""
Phase 1 Test — Patient Profile + Trial Search

Runs only the first two agents directly (no evaluation, no reports).
Prints rich formatted output for each step.

Usage:
    python tests/test_phase1.py           # NSCLC (default)
    python tests/test_phase1.py breast
    python tests/test_phase1.py als
"""

import os
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from src.agents.patient_profile_agent import patient_profile_agent
from src.agents.trial_search_agent import trial_search_agent


# ── Patient Scenarios ─────────────────────────────────────────────────────────

SCENARIOS = {
    "nsclc": {
        "label": "Stage IIIB NSCLC — EGFR+ (Boston)",
        "input": """
            58-year-old female with Stage IIIB Non-Small Cell Lung Cancer (NSCLC).
            EGFR exon 19 deletion positive, PD-L1 expression 40%.
            Previously treated with Carboplatin and Paclitaxel (completed 6 months ago).
            No prior EGFR inhibitor therapy. ECOG performance status 1.
            Lab values: creatinine 0.9 mg/dL, ALT 32 U/L, hemoglobin 11.2 g/dL.
            Comorbidities: Hypertension (controlled with Amlodipine 5mg).
            Located in Boston, MA. Willing to travel up to 100 miles.
            Interested in Phase 2 or Phase 3 trials only.
        """,
    },
    "breast": {
        "label": "Stage II HER2+ Breast Cancer (New York)",
        "input": """
            45-year-old woman recently diagnosed with HER2-positive breast cancer, Stage II.
            No prior systemic treatment. ER negative, PR negative, HER2 positive (3+).
            ECOG 0. No significant comorbidities. No current medications.
            Located in New York, NY. Can travel up to 50 miles. Open to any phase.
        """,
    },
    "als": {
        "label": "ALS — 18 Months Post-Diagnosis (Chicago)",
        "input": """
            62-year-old male with ALS (Amyotrophic Lateral Sclerosis) diagnosed 18 months ago.
            Currently on Riluzole. Limb onset, ALSFRS-R score approximately 38.
            FVC 78% of predicted. No dementia. ECOG 1.
            Lab values: creatinine 1.0 mg/dL, ALT 30 U/L.
            Lives in Chicago, IL. Prefers trials within 75 miles. Open to any phase.
        """,
    },
}


# ── Display helpers ───────────────────────────────────────────────────────────

W = 70  # box width

def banner(text: str):
    print(f"\n{'═' * W}")
    print(f"  {text}")
    print(f"{'═' * W}")

def section(title: str):
    print(f"\n  ┌─ {title} {'─' * (W - len(title) - 5)}┐")

def section_end():
    print(f"  └{'─' * (W - 2)}┘")

def row(label: str, value, indent: int = 4):
    label_str = f"{label}:"
    if isinstance(value, list):
        if not value:
            print(f"  {'':>{indent}}{label_str:<20} (none)")
        else:
            print(f"  {'':>{indent}}{label_str:<20} {value[0]}")
            for v in value[1:]:
                print(f"  {'':>{indent}}{'':20} {v}")
    else:
        print(f"  {'':>{indent}}{label_str:<20} {value if value is not None else '—'}")

def divider():
    print(f"  {'─' * (W - 2)}")

def step_header(n: int, title: str, elapsed: float = None):
    timing = f"  [{elapsed:.1f}s]" if elapsed is not None else ""
    print(f"\n  ╔{'═' * (W - 4)}╗")
    print(f"  ║  STEP {n} — {title:<{W - 13}}{timing if elapsed else ''}║")
    print(f"  ╚{'═' * (W - 4)}╝")


# ── Phase 1 runner ────────────────────────────────────────────────────────────

def run_phase1(key: str = "nsclc"):
    scenario = SCENARIOS[key]

    banner(f"PHASE 1 TEST  ·  {scenario['label']}")
    print(f"\n  Input:\n")
    for line in scenario["input"].strip().splitlines():
        print(f"    {line.strip()}")


    # ── STEP 1: Patient Profile ───────────────────────────────────────────────

    step_header(1, "PATIENT PROFILE EXTRACTION")

    state = {
        "raw_patient_input": scenario["input"],
        "patient_profile": None,
        "candidate_trials": [],
        "evaluated_trials": [],
        "ranked_trials": [],
        "error": None,
        "status_log": [],
    }

    t0 = time.time()
    result1 = patient_profile_agent(state)
    t1 = time.time() - t0

    state.update(result1)

    if state.get("error"):
        print(f"\n  ✗ FAILED ({t1:.1f}s): {state['error']}")
        return

    p = state["patient_profile"]
    print(f"\n  Completed in {t1:.1f}s\n")

    section("Clinical Details")
    row("Diagnosis",    p.diagnosis)
    row("Stage",        p.stage)
    row("ICD-10",       p.diagnosis_codes or ["—"])
    row("Biomarkers",   p.biomarkers or ["(none)"])
    row("Age / Sex",    f"{p.age or '?'} / {p.sex or 'unknown'}")
    row("ECOG",         p.ecog_score)
    section_end()

    section("Treatment & History")
    row("Prior Tx",     p.prior_treatments or ["(none)"])
    row("Comorbidities",p.comorbidities or ["(none)"])
    row("Medications",  p.current_medications or ["(none)"])
    section_end()

    section("Lab Values")
    if p.lab_values:
        for k, v in p.lab_values.items():
            row(k, v)
    else:
        print("    (no lab values extracted)")
    section_end()

    section("Trial Matching Preferences")
    row("Location",     p.location)
    row("Travel max",   f"{p.max_travel_miles} miles")
    row("Phases",       p.preferred_phases or ["any"])
    section_end()

    if p.missing_info:
        print(f"\n  ⚠  Missing / Ambiguous Info:")
        for item in p.missing_info:
            print(f"       • {item}")


    # ── STEP 2: Trial Search ──────────────────────────────────────────────────

    step_header(2, "TRIAL SEARCH  (ClinicalTrials.gov)")

    t0 = time.time()
    result2 = trial_search_agent(state)
    t2 = time.time() - t0

    state.update(result2)
    trials = state.get("candidate_trials", [])

    print(f"\n  Completed in {t2:.1f}s")
    print(f"  Query:    \"{p.diagnosis}\"")
    print(f"  Location: {p.location}  (radius: {p.max_travel_miles} mi)")
    print(f"  Status:   RECRUITING")
    if p.preferred_phases:
        print(f"  Phases:   {p.preferred_phases}  (filter applied)")

    divider()
    print(f"  Total candidates returned:  {len(trials)}")
    divider()

    if not trials:
        print("\n  ✗ No trials found.")
    else:
        print(f"\n  Showing first 10 of {len(trials)} candidates:\n")
        for i, t in enumerate(trials[:10], 1):
            phase_str = (t.phase or "N/A").replace("PHASE", "Phase ").replace("_", " ")
            n_sites   = len(t.locations)
            conditions_short = ", ".join(t.conditions[:2]) if t.conditions else "—"
            interventions_short = ", ".join(t.interventions[:2]) if t.interventions else "—"

            print(f"  [{i:>2}]  {t.nct_id}  ·  {phase_str}  ·  {n_sites} site(s)")
            print(f"        {t.title[:65]}")
            print(f"        Sponsor:       {(t.sponsor or 'N/A')[:50]}")
            print(f"        Conditions:    {conditions_short[:55]}")
            print(f"        Interventions: {interventions_short[:55]}")
            print(f"        Enrollment:    {t.enrollment_target or '?'}  |  URL: {t.url}")
            print()

        if len(trials) > 10:
            print(f"  ... and {len(trials) - 10} more (passing top 15 to evaluator)")


    # ── Summary ───────────────────────────────────────────────────────────────

    total = t1 + t2
    banner(f"PHASE 1 COMPLETE  ·  {total:.1f}s total")
    print(f"  Patient profile:  ✓  {p.diagnosis}, {p.stage or 'stage unknown'}")
    print(f"  Trials found:     {len(trials)}")
    print(f"  Ready for Phase 2 evaluation\n")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in SCENARIOS else "nsclc"
    run_phase1(key)
