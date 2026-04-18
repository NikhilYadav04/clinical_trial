import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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


_NODE_STEP = {
    "extract_profile":   0,
    "trial_search":      1,
    "trial_evaluation":  2,
    "ranking":           3,
    "report_generation": 4,
}

_NODE_LABEL = {
    "extract_profile":   "Extracting patient profile",
    "trial_search":      "Searching ClinicalTrials.gov",
    "trial_evaluation":  "Evaluating trial eligibility",
    "ranking":           "Ranking matched trials",
    "report_generation": "Generating patient & physician reports",
}


@app.post("/api/match/stream")
def match_stream(form: PatientFormInput):
    from src.graph import app as langgraph_app
    patient_text = build_patient_text(form)
    initial_state = {
        "raw_patient_input": patient_text,
        "patient_profile":   None,
        "candidate_trials":  [],
        "evaluated_trials":  [],
        "ranked_trials":     [],
        "error":             None,
        "status_log":        [],
    }

    def generate():
        # Accumulate state manually (status_log uses operator.add so node output only has new entries)
        acc_logs: list[str] = []
        acc_candidates: list = []
        acc_evaluated: list = []
        acc_ranked: list = []
        acc_profile = None

        try:
            for chunk in langgraph_app.stream(initial_state):
                node_name = next(iter(chunk))
                node_output = chunk[node_name]
                step = _NODE_STEP.get(node_name, -1)
                label = _NODE_LABEL.get(node_name, node_name)

                # Accumulate state fields
                new_logs = node_output.get("status_log", [])
                acc_logs.extend(new_logs)
                if "patient_profile" in node_output and node_output["patient_profile"]:
                    acc_profile = node_output["patient_profile"]
                if "candidate_trials" in node_output:
                    acc_candidates.extend(node_output["candidate_trials"])
                if "evaluated_trials" in node_output:
                    acc_evaluated = node_output["evaluated_trials"]
                if "ranked_trials" in node_output:
                    acc_ranked = node_output["ranked_trials"]

                # Signal that the next step is starting
                next_step = step + 1
                if next_step < len(_NODE_STEP):
                    next_node = next((k for k, v in _NODE_STEP.items() if v == next_step), None)
                    next_label = _NODE_LABEL.get(next_node, "")
                    evt = json.dumps({"type": "step", "step": next_step, "label": next_label})
                    yield f"data: {evt}\n\n"

                for log in new_logs:
                    evt = json.dumps({"type": "log", "message": log, "step": step, "node": node_name, "agent": label})
                    yield f"data: {evt}\n\n"

            result = {
                "patient_profile":  _profile(acc_profile) if acc_profile else None,
                "ranked_trials":    [_trial(t) for t in acc_ranked],
                "candidates_count": len(acc_candidates),
                "evaluated_count":  len(acc_evaluated),
                "log":              acc_logs,
            }
            evt = json.dumps({"type": "result", "data": result})
            yield f"data: {evt}\n\n"
        except Exception as e:
            evt = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {evt}\n\n"
        yield "data: {\"type\":\"done\"}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


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
