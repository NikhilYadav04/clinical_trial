import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.models import PatientFormInput
from api.job_manager import build_patient_text

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _trial(t) -> dict:
    return {
        "nct_id": t.nct_id, "title": t.title, "phase": t.phase,
        "sponsor": t.sponsor, "status": t.status, "url": t.url,
        "brief_summary": t.brief_summary, "locations": t.locations or [],
        "final_score": t.final_score, "eligibility_score": t.eligibility_score,
        "logistics_score": t.logistics_score, "quality_score": t.quality_score,
        "nearest_site_miles": t.nearest_site_miles,
        "eligibility_breakdown": [
            {"criterion_text": v.get("criterion_text",""), "type": v.get("type","inclusion"),
             "verdict": v.get("verdict","UNCERTAIN"), "reason": v.get("reason",""),
             "is_hard_stop": v.get("is_hard_stop", False)}
            for v in (t.eligibility_breakdown or [])
        ],
        "patient_summary": t.patient_summary,
        "physician_brief": t.physician_brief,
        "outreach_email": t.outreach_email,
    }


def _profile(p) -> dict:
    return {
        "diagnosis": p.diagnosis, "stage": p.stage, "biomarkers": p.biomarkers or [],
        "age": p.age, "sex": p.sex, "ecog_score": p.ecog_score,
        "prior_treatments": p.prior_treatments or [], "comorbidities": p.comorbidities or [],
        "current_medications": p.current_medications or [], "lab_values": p.lab_values or {},
        "location": p.location, "max_travel_miles": p.max_travel_miles,
        "missing_info": p.missing_info or [],
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/match")
def match(form: PatientFormInput):
    from src.graph import app as langgraph_app
    patient_text = build_patient_text(form)
    result = langgraph_app.invoke({
        "raw_patient_input": patient_text,
        "patient_profile":   None,
        "candidate_trials":  [],
        "evaluated_trials":  [],
        "ranked_trials":     [],
        "error":             None,
        "status_log":        [],
    })
    profile = result.get("patient_profile")
    ranked  = result.get("ranked_trials", [])
    return {
        "patient_profile":   _profile(profile) if profile else None,
        "ranked_trials":     [_trial(t) for t in ranked],
        "candidates_count":  len(result.get("candidate_trials", [])),
        "evaluated_count":   len(result.get("evaluated_trials", [])),
        "log":               result.get("status_log", []),
    }


@app.get("/api/examples")
def get_examples():
    return {"examples": [
        {"label": "NSCLC - EGFR+ (Boston)", "fields": {
            "age": 58, "sex": "Female", "ecog": 1,
            "diagnosis": "Non-Small Cell Lung Cancer (NSCLC)", "stage": "Stage IIIB",
            "biomarkers": "EGFR exon 19 deletion positive, PD-L1 expression 40%",
            "prior_treatments": "Carboplatin and Paclitaxel (6 cycles, completed 6 months ago)",
            "current_medications": "Amlodipine 5mg", "comorbidities": "Hypertension (controlled)",
            "labs": [{"name": "Creatinine", "value": "0.9", "unit": "mg/dL"}, {"name": "ALT", "value": "32", "unit": "U/L"}],
            "location": "Boston, MA", "max_travel": 100, "travel_unit": "miles", "phases": ["Phase 2", "Phase 3"],
        }},
        {"label": "HER2+ Breast Cancer (New York)", "fields": {
            "age": 45, "sex": "Female", "ecog": 0,
            "diagnosis": "HER2-positive Breast Cancer", "stage": "Stage II",
            "biomarkers": "ER negative, PR negative, HER2 3+",
            "prior_treatments": None, "current_medications": None, "comorbidities": None,
            "labs": [], "location": "New York, NY", "max_travel": 50, "travel_unit": "miles", "phases": [],
        }},
        {"label": "ALS (Chicago)", "fields": {
            "age": 62, "sex": "Male", "ecog": 1,
            "diagnosis": "ALS (Amyotrophic Lateral Sclerosis)", "stage": "18 months post-diagnosis",
            "biomarkers": "Limb onset, ALSFRS-R score ~38, FVC 78%",
            "prior_treatments": None, "current_medications": "Riluzole", "comorbidities": None,
            "labs": [{"name": "Creatinine", "value": "1.0", "unit": "mg/dL"}],
            "location": "Chicago, IL", "max_travel": 75, "travel_unit": "miles", "phases": [],
        }},
        {"label": "NSCLC - EGFR+ (Mumbai, India)", "fields": {
            "age": 52, "sex": "Male", "ecog": 1,
            "diagnosis": "Non-Small Cell Lung Cancer (NSCLC)", "stage": "Stage IIIB",
            "biomarkers": "EGFR exon 19 deletion positive, PD-L1 35%",
            "prior_treatments": "Carboplatin and Pemetrexed (4 cycles)",
            "current_medications": "Metformin 500mg", "comorbidities": "Type 2 Diabetes",
            "labs": [{"name": "Creatinine", "value": "0.95", "unit": "mg/dL"}],
            "location": "Mumbai, Maharashtra, India", "max_travel": 300, "travel_unit": "km", "phases": ["Phase 2", "Phase 3"],
        }},
    ]}
