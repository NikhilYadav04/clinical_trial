"""
Clinical Trial Matching Agent — Full Test Scenarios

5 realistic patient cases covering different cancer types, locations,
and complexity levels. Run one at a time or all sequentially.

Usage:
    python tests/test_scenarios.py            # runs all 5
    python tests/test_scenarios.py nsclc      # runs one by name
"""

import os
import sys
import time
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from src.graph import app


# ── Patient Scenarios ─────────────────────────────────────────────────────────

SCENARIOS = {

    # ── 1. NSCLC — EGFR+ post-chemo ──────────────────────────────────────────
    "nsclc": {
        "label": "Stage IIIB NSCLC — EGFR+ (Boston)",
        "what_to_expect": "Should find EGFR-targeted Phase 2/3 trials near Boston. "
                          "Carboplatin/Paclitaxel prior tx may trigger exclusions in some trials.",
        "input": """
            58-year-old female. Diagnosis: Non-Small Cell Lung Cancer (NSCLC), Stage IIIB.
            Biomarkers: EGFR exon 19 deletion positive, PD-L1 tumor proportion score 40%.
            Prior treatments: Carboplatin (6 cycles, completed 8 months ago), Paclitaxel (6 cycles).
            No prior EGFR inhibitor therapy.
            ECOG performance status: 1.
            Lab values: creatinine 0.9 mg/dL, ALT 32 U/L, AST 28 U/L, hemoglobin 11.2 g/dL.
            Comorbidities: Hypertension (well-controlled on Amlodipine 5mg daily).
            Location: Boston, MA. Willing to travel up to 100 miles.
            Prefers Phase 2 or Phase 3 trials only.
        """,
    },

    # ── 2. HER2+ Breast Cancer — treatment naive ─────────────────────────────
    "breast": {
        "label": "Stage II HER2+ Breast Cancer — Treatment Naive (New York)",
        "what_to_expect": "Should find HER2-targeted trials near NYC. "
                          "No prior treatment is a PASS for most trials. Phase 1-3 all eligible.",
        "input": """
            45-year-old woman. Diagnosis: HER2-positive breast cancer, Stage II.
            Receptor status: ER negative, PR negative, HER2 3+ by IHC (confirmed by FISH).
            No prior systemic treatment for breast cancer.
            ECOG performance status: 0.
            Lab values: creatinine 0.8 mg/dL, ALT 22 U/L, hemoglobin 13.1 g/dL, platelets 210 K/uL.
            No significant comorbidities.
            Current medications: none.
            Location: New York, NY. Can travel up to 50 miles.
            Open to any trial phase.
        """,
    },

    # ── 3. ALS — 18 months post-diagnosis ────────────────────────────────────
    "als": {
        "label": "ALS — 18 Months Post-Diagnosis (Chicago)",
        "what_to_expect": "ALS trials are rare — expect fewer results. "
                          "ALSFRS-R and FVC values should help with eligibility checks.",
        "input": """
            62-year-old male. Diagnosis: Amyotrophic Lateral Sclerosis (ALS), limb onset.
            Diagnosed 18 months ago. Symptom onset was left hand weakness.
            Current medications: Riluzole 50mg twice daily (started 16 months ago).
            Functional status: ALSFRS-R score approximately 38. Independent with most ADLs.
            Pulmonary: FVC 78% of predicted. No ventilator support.
            Cognitive: no frontotemporal dementia. MoCA score normal.
            ECOG performance status: 1.
            Lab values: creatinine 1.0 mg/dL, ALT 30 U/L, CK 180 U/L.
            No significant comorbidities beyond ALS.
            Location: Chicago, IL. Maximum travel 75 miles.
            Open to any trial phase, including Phase 1.
        """,
    },

    # ── 4. Multiple Myeloma — relapsed/refractory 3rd line ───────────────────
    "myeloma": {
        "label": "Relapsed/Refractory Multiple Myeloma — 3rd Line (Philadelphia)",
        "what_to_expect": "Should find trials for heavily pre-treated myeloma. "
                          "Prior Bortezomib, Lenalidomide, Daratumumab will exclude some trials "
                          "and qualify for others specifically designed for triple-class refractory.",
        "input": """
            67-year-old male. Diagnosis: Multiple Myeloma, relapsed and refractory, 3rd line.
            Cytogenetics: del(17p) positive by FISH (high-risk), t(4;14) negative.
            Prior lines of therapy:
              1st line: Bortezomib + Lenalidomide + Dexamethasone (VRd) — progressed after 14 months.
              2nd line: Daratumumab + Pomalidomide + Dexamethasone — progressed after 9 months.
              3rd line (current): Carfilzomib monotherapy — tolerating but suboptimal response.
            ECOG performance status: 1.
            Lab values: creatinine 1.4 mg/dL (eGFR 52), ALT 28 U/L, hemoglobin 9.8 g/dL,
                        platelets 98 K/uL, M-protein 2.1 g/dL.
            Comorbidities: Type 2 Diabetes (Metformin 1000mg twice daily), mild peripheral neuropathy.
            Location: Philadelphia, PA. Can travel up to 120 miles.
            Interested in Phase 1, 2, or 3 trials. Open to CAR-T or bispecific antibodies.
        """,
    },

    # ── 5. Pancreatic Cancer — locally advanced, BRCA2 mutation ──────────────
    "pancreatic": {
        "label": "Locally Advanced Pancreatic Cancer — BRCA2+ (Houston)",
        "what_to_expect": "BRCA2 mutation opens PARP inhibitor trials. "
                          "Locally advanced (not metastatic) may restrict some trials. "
                          "Should find targeted therapy and immunotherapy options.",
        "input": """
            54-year-old male. Diagnosis: Pancreatic ductal adenocarcinoma (PDAC), locally advanced,
            unresectable. Staging: T4 N1 M0.
            Germline BRCA2 pathogenic variant confirmed (c.5946delT).
            CA 19-9: 1240 U/mL at diagnosis, now 890 U/mL after treatment.
            Prior treatments: FOLFIRINOX (6 cycles, completed 4 months ago) — partial response.
            No prior PARP inhibitor therapy. No prior immunotherapy.
            ECOG performance status: 1.
            Lab values: creatinine 0.95 mg/dL, ALT 45 U/L, AST 38 U/L, total bilirubin 0.9 mg/dL,
                        hemoglobin 10.6 g/dL, CA 19-9 890 U/mL.
            Comorbidities: none significant.
            Location: Houston, TX. Willing to travel up to 150 miles.
            Open to Phase 1, 2, or 3 trials. Particularly interested in PARP inhibitors or immunotherapy.
        """,
    },
}


# ── Output printer ────────────────────────────────────────────────────────────

def print_results(label: str, result: dict, elapsed: float):
    profile = result.get("patient_profile")
    ranked  = result.get("ranked_trials", [])
    logs    = result.get("status_log", [])
    n_candidates  = len(result.get("candidate_trials", []))
    n_evaluated   = len(result.get("evaluated_trials", []))

    print(f"\n{'='*68}")
    print(f"  {label}")
    print(f"  Time: {elapsed:.1f}s")
    print(f"{'='*68}")

    # Pipeline log
    print("\n── PIPELINE ──")
    for log in logs:
        print(f"  • {log}")

    if result.get("error"):
        print(f"\n  ❌ ERROR: {result['error']}")
        return

    # Patient profile
    if profile:
        print(f"\n── PATIENT PROFILE ──")
        print(f"  Diagnosis:      {profile.diagnosis} {profile.stage or ''}")
        print(f"  Biomarkers:     {profile.biomarkers or 'none'}")
        print(f"  Prior Tx:       {profile.prior_treatments or 'none'}")
        print(f"  ECOG:           {profile.ecog_score}")
        print(f"  Location:       {profile.location}")
        print(f"  Travel max:     {profile.max_travel_miles} miles")
        print(f"  Phases:         {profile.preferred_phases}")
        if profile.missing_info:
            print(f"  ⚠ Missing:      {profile.missing_info}")

    # Stats
    print(f"\n── STATS ──")
    print(f"  Candidates found:  {n_candidates}")
    print(f"  Evaluated:         {n_evaluated}")
    print(f"  Ranked matches:    {len(ranked)}")
    if ranked:
        print(f"  Top score:         {ranked[0].final_score}/100")

    # Top 3 results
    if not ranked:
        print("\n  ⚠ No trials matched above threshold.")
        return

    print(f"\n── TOP {min(len(ranked), 3)} MATCHES ──")
    for i, trial in enumerate(ranked[:3], 1):
        dist = f"{trial.nearest_site_miles} mi" if trial.nearest_site_miles else "dist unknown"
        n_pass    = sum(1 for v in trial.eligibility_breakdown if v.get("verdict") == "PASS")
        n_fail    = sum(1 for v in trial.eligibility_breakdown if v.get("verdict") == "FAIL")
        n_uncert  = sum(1 for v in trial.eligibility_breakdown if v.get("verdict") == "UNCERTAIN")
        hard_fails = [v["criterion_text"] for v in trial.eligibility_breakdown
                      if v.get("verdict") == "FAIL" and v.get("is_hard_stop")]

        phase_str = (trial.phase or "N/A").replace("PHASE", "Phase ").replace("_", " ")
        status = "🟢 Eligible" if not hard_fails else "🔴 Disqualified"

        print(f"""
  #{i}  [{trial.final_score}/100]  {status}
       {trial.nct_id} — {trial.title[:65]}
       Phase: {phase_str} | Sponsor: {(trial.sponsor or 'N/A')[:40]}
       Nearest site: {dist}
       Eligibility: ✓{n_pass} met  ⚠{n_uncert} uncertain  ❌{n_fail} fails
       URL: {trial.url}""")

        if hard_fails:
            print(f"       Disqualifiers: {hard_fails[:2]}")

    # Patient summary for top match
    if ranked and ranked[0].patient_summary:
        print(f"\n── PATIENT SUMMARY (Match #1) ──")
        print(f"  {ranked[0].patient_summary[:600]}")

    # Outreach email for top match
    if ranked and ranked[0].outreach_email:
        print(f"\n── OUTREACH EMAIL DRAFT (Match #1) ──")
        print(ranked[0].outreach_email[:500])


# ── Runner ────────────────────────────────────────────────────────────────────

def run_scenario(key: str):
    scenario = SCENARIOS[key]
    print(f"\n{'─'*68}")
    print(f"  RUNNING: {scenario['label']}")
    print(f"  EXPECTED: {scenario['what_to_expect']}")
    print(f"{'─'*68}")

    initial_state = {
        "raw_patient_input": scenario["input"],
        "patient_profile": None,
        "candidate_trials": [],
        "evaluated_trials": [],
        "ranked_trials": [],
        "error": None,
        "status_log": [],
    }

    start = time.time()
    result = app.invoke(initial_state)
    elapsed = time.time() - start

    print_results(scenario["label"], result, elapsed)
    return result


def run_all():
    print("\n" + "="*68)
    print("  CLINICAL TRIAL MATCHING AGENT — FULL TEST SUITE")
    print("  5 patient scenarios")
    print("="*68)

    results = {}
    for key in SCENARIOS:
        results[key] = run_scenario(key)

    # Summary table
    print(f"\n\n{'='*68}")
    print("  TEST SUMMARY")
    print(f"{'='*68}")
    print(f"  {'Scenario':<35} {'Candidates':>10} {'Matches':>8} {'Top Score':>10}")
    print(f"  {'─'*60}")
    for key, result in results.items():
        label = SCENARIOS[key]["label"][:34]
        n_cand = len(result.get("candidate_trials", []))
        ranked = result.get("ranked_trials", [])
        top    = ranked[0].final_score if ranked else "—"
        print(f"  {label:<35} {n_cand:>10} {len(ranked):>8} {str(top):>10}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "scenario",
        nargs="?",
        choices=list(SCENARIOS.keys()),
        help="Run a single scenario by name. Omit to run all.",
    )
    args = parser.parse_args()

    if args.scenario:
        run_scenario(args.scenario)
    else:
        run_all()
