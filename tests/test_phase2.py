"""
Phase 2 Test — Full Pipeline with Evaluation + Ranking

Runs all 5 nodes: Profile → Search → Evaluation → Ranking → Reports
Prints rich formatted output for every stage.

Usage:
    python tests/test_phase2.py           # NSCLC (default)
    python tests/test_phase2.py breast
    python tests/test_phase2.py als
"""

import os
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from src.graph import app


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
            62-year-old male with ALS diagnosed 18 months ago. Currently on Riluzole.
            Limb onset, ALSFRS-R score approximately 38. FVC 78% of predicted. ECOG 1.
            Lab values: creatinine 1.0 mg/dL, ALT 30 U/L.
            Lives in Chicago, IL. Prefers trials within 75 miles. Open to any phase.
        """,
    },

    # ── India scenarios ───────────────────────────────────────────────────────

    "nsclc_india": {
        "label": "Stage IIIB NSCLC — EGFR+ (Mumbai, India)",
        "input": """
            52-year-old male. Diagnosis: Non-Small Cell Lung Cancer (NSCLC), Stage IIIB.
            EGFR exon 19 deletion positive. PD-L1 expression 35%.
            No prior EGFR inhibitor therapy.
            Prior treatments: Carboplatin and Pemetrexed (4 cycles, completed 5 months ago).
            ECOG performance status 1.
            Lab values: creatinine 0.95 mg/dL, ALT 28 U/L, hemoglobin 10.8 g/dL.
            Comorbidities: Type 2 Diabetes (well-controlled on Metformin 500mg twice daily).
            Located in Mumbai, Maharashtra, India. Willing to travel up to 300 km.
            Interested in Phase 2 or Phase 3 trials.
        """,
    },

    "breast_india": {
        "label": "Stage III HER2+ Breast Cancer (Delhi, India)",
        "input": """
            38-year-old woman. Diagnosis: HER2-positive breast cancer, Stage III.
            ER negative, PR negative, HER2 3+ by IHC confirmed by FISH.
            No prior systemic treatment for breast cancer.
            ECOG performance status 0.
            Lab values: creatinine 0.8 mg/dL, ALT 25 U/L, hemoglobin 12.4 g/dL, platelets 220 K/uL.
            No significant comorbidities. No current medications.
            Located in New Delhi, India. Willing to travel up to 500 km.
            Open to any trial phase including Phase 1.
        """,
    },
}


# ── Display helpers ───────────────────────────────────────────────────────────

W = 72

def banner(text: str):
    print(f"\n{'═' * W}")
    print(f"  {text}")
    print(f"{'═' * W}")

def section(title: str):
    pad = W - len(title) - 6
    print(f"\n  ┌─ {title} {'─' * pad}┐")

def section_end():
    print(f"  └{'─' * (W - 2)}┘")

def row(label: str, value, indent: int = 4):
    label_str = f"{label}:"
    if isinstance(value, list):
        if not value:
            print(f"  {'':>{indent}}{label_str:<22} (none)")
        else:
            print(f"  {'':>{indent}}{label_str:<22} {value[0]}")
            for v in value[1:]:
                print(f"  {'':>{indent}}{'':22} {v}")
    else:
        print(f"  {'':>{indent}}{label_str:<22} {value if value is not None else '—'}")

def divider(char: str = '─'):
    print(f"  {char * (W - 2)}")

def step_header(n: int, title: str):
    inner = f"  STEP {n} — {title}"
    pad = W - len(inner) - 3
    print(f"\n  ╔{'═' * (W - 4)}╗")
    print(f"  ║{inner}{' ' * pad}║")
    print(f"  ╚{'═' * (W - 4)}╝")

def score_bar(score: float, width: int = 20) -> str:
    filled = int((score / 100) * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {score:>5.1f}/100"

def verdict_badge(verdict: str) -> str:
    return {"PASS": "✓", "FAIL": "✗", "UNCERTAIN": "?"}.get(verdict, " ")


# ── Main runner ───────────────────────────────────────────────────────────────

def run_phase2(key: str = "nsclc"):
    scenario = SCENARIOS[key]

    banner(f"FULL PIPELINE TEST  ·  {scenario['label']}")

    initial_state = {
        "raw_patient_input": scenario["input"],
        "patient_profile":   None,
        "candidate_trials":  [],
        "evaluated_trials":  [],
        "ranked_trials":     [],
        "error":             None,
        "status_log":        [],
    }

    # ── Run full graph ────────────────────────────────────────────────────────

    step_header(1, "PATIENT PROFILE  +  TRIAL SEARCH  +  EVALUATION  +  RANKING")
    print(f"\n  Running full pipeline... (agent logs below)\n")
    divider()

    t0 = time.time()
    result = app.invoke(initial_state)
    total_elapsed = time.time() - t0

    divider()
    print(f"\n  Pipeline finished in {total_elapsed:.1f}s")

    if result.get("error"):
        print(f"\n  ✗ PIPELINE ERROR: {result['error']}")
        return

    # ── Pipeline log ──────────────────────────────────────────────────────────

    step_header(2, "PIPELINE LOG")
    print()
    for log in result.get("status_log", []):
        print(f"    • {log}")

    # ── Patient Profile ───────────────────────────────────────────────────────

    p = result.get("patient_profile")
    if p:
        step_header(3, "EXTRACTED PATIENT PROFILE")

        section("Clinical Details")
        row("Diagnosis",    p.diagnosis)
        row("Stage",        p.stage)
        row("ICD-10",       p.diagnosis_codes or ["—"])
        row("Biomarkers",   p.biomarkers or ["(none)"])
        row("Age / Sex",    f"{p.age or '?'} / {p.sex or 'unknown'}")
        row("ECOG",         p.ecog_score)
        section_end()

        section("Treatment & History")
        row("Prior Tx",      p.prior_treatments or ["(none)"])
        row("Comorbidities", p.comorbidities or ["(none)"])
        row("Medications",   p.current_medications or ["(none)"])
        section_end()

        if p.lab_values:
            section("Lab Values")
            for k, v in p.lab_values.items():
                row(k, v)
            section_end()

        section("Trial Matching Preferences")
        row("Location",   p.location)
        row("Travel max", f"{p.max_travel_miles} miles")
        row("Phases",     p.preferred_phases or ["any"])
        section_end()

        if p.missing_info:
            print(f"\n  ⚠  Missing / Ambiguous Info:")
            for item in p.missing_info:
                print(f"       • {item}")

    # ── Search + Evaluation Stats ─────────────────────────────────────────────

    n_candidates = len(result.get("candidate_trials", []))
    n_evaluated  = len(result.get("evaluated_trials", []))
    ranked       = result.get("ranked_trials", [])

    step_header(4, "EVALUATION SUMMARY")
    print()
    print(f"    Candidates from API:    {n_candidates}")
    print(f"    Trials evaluated:       {n_evaluated}")
    print(f"    Passed ranking (≥30):   {len(ranked)}")
    if ranked:
        print(f"    Top score:              {ranked[0].final_score}/100")
        scores = [t.final_score for t in ranked if t.final_score]
        avg = sum(scores) / len(scores) if scores else 0
        print(f"    Average score:          {avg:.1f}/100")

    # ── Ranked Results ────────────────────────────────────────────────────────

    step_header(5, f"RANKED MATCHES  ({len(ranked)} trials above threshold)")

    if not ranked:
        print("\n  No trials scored above the 30-point threshold.")
    else:
        for i, trial in enumerate(ranked[:5], 1):
            n_pass    = sum(1 for v in trial.eligibility_breakdown if v.get("verdict") == "PASS")
            n_fail    = sum(1 for v in trial.eligibility_breakdown if v.get("verdict") == "FAIL")
            n_uncert  = sum(1 for v in trial.eligibility_breakdown if v.get("verdict") == "UNCERTAIN")
            hard_fails = [v["criterion_text"] for v in trial.eligibility_breakdown
                          if v.get("verdict") == "FAIL" and v.get("is_hard_stop")]
            uncertain  = [v["criterion_text"] for v in trial.eligibility_breakdown
                          if v.get("verdict") == "UNCERTAIN"]

            phase_str = (trial.phase or "N/A").replace("PHASE", "Phase ").replace("_", " ")
            dist      = f"{trial.nearest_site_miles} mi away" if trial.nearest_site_miles else "distance unknown"
            status    = "ELIGIBLE" if not hard_fails else "DISQUALIFIED"
            status_icon = "✓" if not hard_fails else "✗"

            print(f"\n  {'─' * (W - 2)}")
            print(f"  #{i}  {status_icon} {status}  ·  {trial.nct_id}  ·  {phase_str}")
            print(f"      {trial.title[:68]}")
            print(f"      Sponsor: {(trial.sponsor or 'N/A')[:55]}")
            print(f"      {dist}  ·  {len(trial.locations)} site(s)  ·  {trial.url}")
            print()

            # Score breakdown
            print(f"      SCORES")
            print(f"        Final:       {score_bar(trial.final_score or 0)}")
            print(f"        Eligibility: {score_bar(trial.eligibility_score or 0)}  (60% weight)")
            print(f"        Quality:     {score_bar(trial.quality_score or 0)}  (20% weight)")
            print(f"        Logistics:   {score_bar(trial.logistics_score or 0)}  (10% weight)")
            print()

            # Eligibility breakdown summary
            print(f"      ELIGIBILITY  ✓ {n_pass} passed  ? {n_uncert} uncertain  ✗ {n_fail} failed")

            if hard_fails:
                print(f"\n      HARD DISQUALIFIERS:")
                for hf in hard_fails[:3]:
                    print(f"        ✗  {hf[:70]}")

            if uncertain:
                print(f"\n      CONFIRM WITH DOCTOR:")
                for u in uncertain[:4]:
                    print(f"        ?  {u[:70]}")

            # Criterion-level detail (top 8)
            if trial.eligibility_breakdown:
                print(f"\n      CRITERIA DETAIL (first 8):")
                for v in trial.eligibility_breakdown[:8]:
                    icon    = verdict_badge(v.get("verdict", "?"))
                    ctype   = "INC" if v.get("type") == "inclusion" else "EXC"
                    hard    = " [HARD]" if v.get("is_hard_stop") else ""
                    text    = v.get("criterion_text", "")[:55]
                    reason  = v.get("reason", "")[:50]
                    print(f"        {icon} [{ctype}{hard}]  {text}")
                    print(f"             → {reason}")

        if len(ranked) > 5:
            print(f"\n  {'─' * (W - 2)}")
            print(f"  ... and {len(ranked) - 5} more matches (scores: "
                  f"{', '.join(str(t.final_score) for t in ranked[5:])})")

    # ── Top match reports ─────────────────────────────────────────────────────

    if ranked and ranked[0].patient_summary:
        step_header(6, "REPORTS — MATCH #1")

        print(f"\n  ── Patient Summary ──")
        for line in ranked[0].patient_summary.splitlines():
            print(f"    {line}")

        if ranked[0].physician_brief:
            print(f"\n  ── Physician Brief ──")
            for line in ranked[0].physician_brief.splitlines():
                print(f"    {line}")

        if ranked[0].outreach_email:
            print(f"\n  ── Outreach Email Draft ──")
            for line in ranked[0].outreach_email.splitlines():
                print(f"    {line}")

    # ── Final summary ─────────────────────────────────────────────────────────

    banner(f"PIPELINE COMPLETE  ·  {total_elapsed:.1f}s total")
    print(f"  Patient:        {p.diagnosis if p else '?'}, {p.stage if p else '?'}")
    print(f"  Candidates:     {n_candidates}  →  evaluated: {n_evaluated}  →  ranked: {len(ranked)}")
    if ranked:
        top = ranked[0]
        dist = f"{top.nearest_site_miles} mi" if top.nearest_site_miles else "dist unknown"
        print(f"  Best match:     {top.nct_id}  [{top.final_score}/100]  ·  {dist}")
        print(f"                  {top.title[:65]}")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in SCENARIOS else "nsclc"
    run_phase2(key)
