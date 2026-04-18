"""
Patient Profile Agent

Reads free-text patient description and extracts a structured
clinical profile (diagnosis, biomarkers, labs, location, etc.)
ready for trial matching.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from src.utils.llm import get_llm
from src.utils.retry import with_retry, call_with_timeout
from src.state import GraphState, PatientProfile
import json


SYSTEM_PROMPT = """You are a clinical data extraction specialist. Your job is to read a patient description
and extract structured information for clinical trial matching.

Extract the following fields from the patient description:
- diagnosis: Primary diagnosis (full name, not abbreviated)
- stage: Stage or grade if mentioned (e.g. "Stage IIIB", "Grade 2")
- diagnosis_codes: Map the diagnosis to ICD-10 codes if you can (e.g. ["C34.12"])
- biomarkers: Any biomarkers, genetic mutations, or molecular markers mentioned (e.g. ["EGFR exon 19 deletion", "PD-L1 40%"])
- age: Patient age as integer
- sex: "male", "female", or null
- ecog_score: ECOG performance status as integer (0-4) if mentioned
- prior_treatments: List of drugs, radiation, surgeries the patient has already received
- comorbidities: Other medical conditions (e.g. ["Type 2 Diabetes", "Hypertension"])
- current_medications: Current medications beyond cancer treatment
- lab_values: Key lab results as a dict (e.g. {"creatinine": 0.9, "ALT": 32})
- location: City and state or zip code
- max_travel_miles: Maximum distance patient is willing to travel (default to 100 if not stated)
- preferred_phases: Trial phases the patient prefers (e.g. [2, 3]). Default to [1, 2, 3] if not stated.
- missing_info: List of important fields that are missing or ambiguous that a doctor should clarify

Return ONLY valid JSON matching this exact structure. No explanations, no markdown, just JSON.

Example output:
{
  "diagnosis": "Non-Small Cell Lung Cancer",
  "stage": "Stage IIIB",
  "diagnosis_codes": ["C34.12"],
  "biomarkers": ["EGFR exon 19 deletion positive", "PD-L1 40%"],
  "age": 58,
  "sex": "female",
  "ecog_score": 1,
  "prior_treatments": ["Carboplatin", "Paclitaxel"],
  "comorbidities": ["Hypertension"],
  "current_medications": ["Amlodipine 5mg"],
  "lab_values": {"creatinine": 0.9, "ALT": 32},
  "location": "Boston, MA",
  "max_travel_miles": 100,
  "preferred_phases": [2, 3],
  "missing_info": ["ECOG score not mentioned — assumed 1 based on description"]
}"""


def patient_profile_agent(state: GraphState) -> dict:
    """
    LangGraph node — extracts structured patient profile from raw input.
    Updates state with: patient_profile, status_log
    """
    llm = get_llm(temperature=0)

    raw_input = state["raw_patient_input"]

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Extract the clinical profile from this patient description:\n\n{raw_input}"),
    ]

    print("\n[Patient Profile Agent] Extracting clinical profile...")

    @with_retry(max_attempts=3, base_delay=2.0)
    def _invoke():
        return llm.invoke(messages)

    try:
        response = call_with_timeout(_invoke, timeout_seconds=90, label="patient_profile")
    except Exception as exc:
        error_msg = f"Patient Profile Agent timed out or failed after retries: {exc}"
        print(f"[Patient Profile Agent] ERROR: {error_msg}")
        return {
            "error": error_msg,
            "status_log": [f"ERROR in Patient Profile Agent: {error_msg}"],
        }

    content = response.content.strip()

    # Strip markdown code fences if LLM adds them
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        profile_dict = json.loads(content)
        patient_profile = PatientProfile(**profile_dict)
        print(f"[Patient Profile Agent] Extracted: {patient_profile.diagnosis}, {patient_profile.stage}")
        if patient_profile.missing_info:
            print(f"[Patient Profile Agent] Missing info flagged: {patient_profile.missing_info}")

        return {
            "patient_profile": patient_profile,
            "status_log": [f"Patient profile extracted: {patient_profile.diagnosis} {patient_profile.stage or ''}"],
        }

    except (json.JSONDecodeError, Exception) as e:
        error_msg = f"Patient Profile Agent failed to parse response: {e}"
        print(f"[Patient Profile Agent] ERROR: {error_msg}")
        return {
            "error": error_msg,
            "status_log": [f"ERROR in Patient Profile Agent: {error_msg}"],
        }
