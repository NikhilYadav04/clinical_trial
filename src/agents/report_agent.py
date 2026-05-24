"""
Report Generation Agent

Generates two outputs per top-matched trial:
  1. Patient-facing summary  — plain English, 8th grade reading level
  2. Physician brief         — clinical language, structured for handoff
  3. Outreach email draft    — to trial coordinator
"""

from src.utils.llm import get_llm, extract_content
from src.utils.retry import with_retry, call_with_timeout
from langchain_core.messages import SystemMessage, HumanMessage
import json

from src.state import PatientProfile, TrialRecord


PATIENT_SUMMARY_PROMPT = """You are a patient advocate writing about clinical trials.
Write a clear, warm, plain-English summary of this clinical trial for a patient.

Rules:
- Use 8th grade reading level (simple words, short sentences)
- NO medical jargon — explain any technical terms
- Structure:
    WHAT THIS TRIAL IS TESTING: (1-2 sentences)
    WHY THIS MIGHT BE RIGHT FOR YOU: (2-3 bullet points based on patient profile match)
    WHAT WOULD BE INVOLVED: (visits, duration, treatment type)
    IMPORTANT TO CONFIRM WITH YOUR DOCTOR: (any UNCERTAIN eligibility items)
- Be honest — if there are potential disqualifiers, mention them
- Keep it under 200 words
- Do NOT use markdown headers with #, use plain text labels"""


PHYSICIAN_BRIEF_PROMPT = """You are writing a clinical trial briefing for a physician.
Write a concise, structured brief for the referring physician about this trial match.

Structure:
    TRIAL: NCT ID, title, phase, sponsor
    CLINICAL RATIONALE: Why this trial fits this patient's specific profile (biomarkers, prior therapy, stage)
    KEY ELIGIBILITY: Confirmed matches and any uncertain criteria needing verification
    LOGISTICS: Nearest site and distance, estimated visit schedule
    RECOMMENDATION: Brief assessment (Strong Match / Moderate Match / Weak Match) with one sentence rationale

Keep it under 150 words. Use clinical language appropriate for an oncologist."""


OUTREACH_EMAIL_PROMPT = """Write a professional outreach email from a patient to a clinical trial coordinator.

Rules:
- Professional, concise, respectful tone
- Include: patient's diagnosis and key relevant details, why they're interested in this specific trial
- Ask about: current enrollment status, next steps for pre-screening
- Do NOT include identifying information like full name or date of birth
- Keep it under 150 words
- Subject line included at top"""


def _call_llm(system_prompt: str, user_content: str) -> str:
    @with_retry(max_attempts=2, base_delay=2.0)
    def _invoke():
        llm = get_llm(temperature=0.3)
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ])
        return extract_content(response).strip()

    return call_with_timeout(_invoke, timeout_seconds=90, label="report_agent")


def _format_eligibility_summary(trial: TrialRecord) -> dict:
    """Extract key eligibility facts from breakdown."""
    passes = [v["criterion_text"] for v in trial.eligibility_breakdown if v.get("verdict") == "PASS"]
    fails = [v["criterion_text"] for v in trial.eligibility_breakdown if v.get("verdict") == "FAIL" and v.get("is_hard_stop")]
    uncertain = [v["criterion_text"] for v in trial.eligibility_breakdown if v.get("verdict") == "UNCERTAIN"]
    return {"passes": passes[:5], "hard_fails": fails, "uncertain": uncertain[:4]}


def generate_patient_summary(patient: PatientProfile, trial: TrialRecord) -> str:
    """Generate plain-English patient-facing trial summary."""
    eligibility = _format_eligibility_summary(trial)
    dist = f"{trial.nearest_site_miles} miles away" if trial.nearest_site_miles else "distance unknown"

    context = f"""
Patient profile:
- Diagnosis: {patient.diagnosis} {patient.stage or ''}
- Biomarkers: {', '.join(patient.biomarkers) or 'none listed'}
- Prior treatments: {', '.join(patient.prior_treatments) or 'none'}
- Location: {patient.location}, willing to travel {patient.max_travel_miles} miles

Trial details:
- Title: {trial.title}
- NCT ID: {trial.nct_id}
- Phase: {trial.phase}
- Sponsor: {trial.sponsor}
- Nearest site: {dist}
- Brief summary: {(trial.brief_summary or '')[:500]}
- Interventions: {', '.join(trial.interventions[:3])}
- Match score: {trial.final_score}/100

Eligibility matches: {eligibility['passes']}
Items to confirm with doctor: {eligibility['uncertain']}
Disqualifiers found: {eligibility['hard_fails']}
"""
    return _call_llm(PATIENT_SUMMARY_PROMPT, context)


def generate_physician_brief(patient: PatientProfile, trial: TrialRecord) -> str:
    """Generate clinical physician handoff brief."""
    eligibility = _format_eligibility_summary(trial)
    dist = f"{trial.nearest_site_miles} mi" if trial.nearest_site_miles else "unknown"

    context = f"""
Patient: {patient.age}{'F' if patient.sex == 'female' else 'M' if patient.sex == 'male' else ''}, {patient.diagnosis} {patient.stage or ''}
Biomarkers: {', '.join(patient.biomarkers)}
Prior therapy: {', '.join(patient.prior_treatments)}
ECOG: {patient.ecog_score}
Labs: {json.dumps(patient.lab_values)}

Trial: {trial.nct_id} — {trial.title}
Phase: {trial.phase} | Sponsor: {trial.sponsor}
Interventions: {', '.join(trial.interventions[:3])}
Nearest site: {dist}
Match score: {trial.final_score}/100
Eligibility score: {trial.eligibility_score}/100

Confirmed criteria met: {eligibility['passes']}
Uncertain (needs verification): {eligibility['uncertain']}
Hard-stop fails: {eligibility['hard_fails']}
"""
    return _call_llm(PHYSICIAN_BRIEF_PROMPT, context)


def generate_outreach_email(patient: PatientProfile, trial: TrialRecord) -> str:
    """Generate coordinator outreach email draft."""
    context = f"""
Patient details for email:
- Diagnosis: {patient.diagnosis}, {patient.stage or ''}
- Key biomarkers: {', '.join(patient.biomarkers[:2])}
- Prior treatments: {', '.join(patient.prior_treatments[:2])}
- ECOG: {patient.ecog_score}
- Location: {patient.location}

Trial to inquire about:
- NCT ID: {trial.nct_id}
- Title: {trial.title}
- Phase: {trial.phase}
- Sponsor: {trial.sponsor}
"""
    return _call_llm(OUTREACH_EMAIL_PROMPT, context)


def generate_reports_for_trial(patient: PatientProfile, trial: TrialRecord) -> TrialRecord:
    """
    Generate all three reports for a single trial.
    Populates trial.patient_summary, trial.physician_brief, trial.outreach_email.
    Returns the updated trial.
    """
    print(f"  [Report Agent] Generating reports for {trial.nct_id}...")

    try:
        trial.patient_summary = generate_patient_summary(patient, trial)
    except Exception as e:
        trial.patient_summary = f"Summary unavailable: {e}"

    try:
        trial.physician_brief = generate_physician_brief(patient, trial)
    except Exception as e:
        trial.physician_brief = f"Brief unavailable: {e}"

    try:
        trial.outreach_email = generate_outreach_email(patient, trial)
    except Exception as e:
        trial.outreach_email = f"Email unavailable: {e}"

    return trial
