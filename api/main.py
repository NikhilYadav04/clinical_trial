import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

import io
import json
import pathlib
import queue
import threading
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import Optional

from api.models import PatientFormInput
from api.job_manager import build_patient_text
from fastapi.security import OAuth2PasswordBearer
from api.auth import (
    get_current_user, create_token, create_user,
    find_by_email, verify_password, public, user_dir,
    SECRET_KEY, ALGORITHM,
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Storage helpers ───────────────────────────────────────────────────────────

def _load_json(path: pathlib.Path) -> list:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def _save_json(path: pathlib.Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _uf(user: dict, filename: str) -> pathlib.Path:
    """Return the per-user file path, ensuring the directory exists."""
    return user_dir(user["user_id"]) / filename


# ── Job registry ──────────────────────────────────────────────────────────────

_jobs: dict[str, queue.Queue] = {}


class _LineQueue(io.TextIOBase):
    def __init__(self, q: queue.Queue):
        self._q   = q
        self._raw = sys.__stdout__
        self._buf = ""

    def write(self, s: str) -> int:
        try:
            self._raw.write(s)
            self._raw.flush()
        except Exception:
            pass
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line.strip():
                self._q.put(("log", line.strip()))
        return len(s)

    def flush(self):
        try:
            self._raw.flush()
        except Exception:
            pass


# ── Serialisers ───────────────────────────────────────────────────────────────

def _trial(t) -> dict:
    return {
        "nct_id":         t.nct_id,
        "title":          t.title,
        "phase":          t.phase,
        "sponsor":        t.sponsor,
        "status":         t.status,
        "url":            t.url,
        "brief_summary":  t.brief_summary,
        "locations":      t.locations or [],
        "final_score":    t.final_score,
        "eligibility_score": t.eligibility_score,
        "logistics_score":   t.logistics_score,
        "quality_score":     t.quality_score,
        "nearest_site_miles": t.nearest_site_miles,
        "eligibility_breakdown": [
            {
                "criterion_text": v.get("criterion_text", ""),
                "type":           v.get("type", "inclusion"),
                "verdict":        v.get("verdict", "UNCERTAIN"),
                "reason":         v.get("reason", ""),
                "is_hard_stop":   v.get("is_hard_stop", False),
            }
            for v in (t.eligibility_breakdown or [])
        ],
        "patient_summary":  t.patient_summary,
        "physician_brief":  t.physician_brief,
        "outreach_email":   t.outreach_email,
    }


def _profile(p) -> dict:
    return {
        "diagnosis":           p.diagnosis,
        "stage":               p.stage,
        "biomarkers":          p.biomarkers or [],
        "age":                 p.age,
        "sex":                 p.sex,
        "ecog_score":          p.ecog_score,
        "prior_treatments":    p.prior_treatments or [],
        "comorbidities":       p.comorbidities or [],
        "current_medications": p.current_medications or [],
        "lab_values":          p.lab_values or {},
        "location":            p.location,
        "max_travel_miles":    p.max_travel_miles,
        "missing_info":        p.missing_info or [],
    }


def _build_result_payload(result: dict) -> dict:
    profile = result.get("patient_profile")
    ranked  = result.get("ranked_trials", [])
    return {
        "patient_profile":  _profile(profile) if profile else None,
        "ranked_trials":    [_trial(t) for t in ranked],
        "candidates_count": len(result.get("candidate_trials", [])),
        "evaluated_count":  len(result.get("evaluated_trials", [])),
        "log":              result.get("status_log", []),
    }


def _invoke_graph(patient_text: str) -> dict:
    from src.graph import app as langgraph_app
    config = {
        "run_name": "TrialMatch Pipeline",
        "tags": ["trialmatch", "clinical-trial", "langgraph"],
        "metadata": {"version": "1.0"},
    }
    return langgraph_app.invoke({
        "raw_patient_input": patient_text,
        "patient_profile":   None,
        "candidate_trials":  [],
        "evaluated_trials":  [],
        "ranked_trials":     [],
        "error":             None,
        "status_log":        [],
    }, config=config)


# ── Auth routes ───────────────────────────────────────────────────────────────

class RegisterIn(BaseModel):
    email:    str
    password: str
    name:     str

class LoginIn(BaseModel):
    email:    str
    password: str


@app.post("/api/auth/register")
def register(body: RegisterIn):
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    user  = create_user(body.email, body.password, body.name)
    token = create_token(user["user_id"], user["email"])
    return {"token": token, "user": public(user)}


@app.post("/api/auth/login")
def login(body: LoginIn):
    user = find_by_email(body.email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(user["user_id"], user["email"])
    return {"token": token, "user": public(user)}


@app.get("/api/auth/me")
def me(current_user: dict = Depends(get_current_user)):
    return public(current_user)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok"}


# ── Match routes ──────────────────────────────────────────────────────────────

@app.post("/api/match/start")
def match_start(form: PatientFormInput, current_user: dict = Depends(get_current_user)):
    job_id = str(uuid.uuid4())
    q: queue.Queue = queue.Queue()
    _jobs[job_id] = q

    def run():
        patient_text = build_patient_text(form)
        capture  = _LineQueue(q)
        old_out  = sys.stdout
        sys.stdout = capture
        try:
            result = _invoke_graph(patient_text)
            q.put(("done", _build_result_payload(result)))
        except Exception as exc:
            q.put(("error", str(exc)))
        finally:
            sys.stdout = old_out

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id}


def _user_from_token(token: str) -> dict:
    """Used by SSE endpoint where Authorization header isn't available."""
    from jose import jwt, JWTError
    from fastapi import HTTPException, status
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    from api.auth import _load_users
    user = next((u for u in _load_users() if u["user_id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@app.get("/api/match/stream/{job_id}")
def match_stream(job_id: str, token: str):
    _user_from_token(token)   # validates; raises 401 if invalid
    if job_id not in _jobs:
        def _not_found():
            yield f"data: {json.dumps({'type': 'error', 'message': 'Job not found'})}\n\n"
        return StreamingResponse(_not_found(), media_type="text/event-stream")

    q = _jobs[job_id]

    def generate():
        try:
            while True:
                try:
                    kind, data = q.get(timeout=300)
                except queue.Empty:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                    continue
                if kind == "log":
                    yield f"data: {json.dumps({'type': 'log', 'line': data})}\n\n"
                elif kind == "done":
                    yield f"data: {json.dumps({'type': 'done', **data})}\n\n"
                    break
                elif kind == "error":
                    yield f"data: {json.dumps({'type': 'error', 'message': data})}\n\n"
                    break
        finally:
            _jobs.pop(job_id, None)

    return StreamingResponse(
        generate(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.post("/api/match")
def match(form: PatientFormInput, current_user: dict = Depends(get_current_user)):
    patient_text = build_patient_text(form)
    result = _invoke_graph(patient_text)
    return _build_result_payload(result)


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
        {"label": "NSCLC — EGFR+ (Boston)", "fields": {
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
        {"label": "NSCLC — EGFR+ (Mumbai, India)", "fields": {
            "age": 52, "sex": "Male", "ecog": 1,
            "diagnosis": "Non-Small Cell Lung Cancer (NSCLC)", "stage": "Stage IIIB",
            "biomarkers": "EGFR exon 19 deletion positive, PD-L1 35%",
            "prior_treatments": "Carboplatin and Pemetrexed (4 cycles)",
            "current_medications": "Metformin 500mg", "comorbidities": "Type 2 Diabetes",
            "labs": [{"name": "Creatinine", "value": "0.95", "unit": "mg/dL"}],
            "location": "Mumbai, Maharashtra, India", "max_travel": 300, "travel_unit": "km", "phases": ["Phase 2", "Phase 3"],
        }},
    ]}


# ── Patients ──────────────────────────────────────────────────────────────────

class PatientRecordIn(BaseModel):
    label:     str
    form_data: dict


@app.post("/api/patients")
def save_patient(rec: PatientRecordIn, current_user: dict = Depends(get_current_user)):
    patients = _load_json(_uf(current_user, "patients.json"))
    entry = rec.model_dump()
    entry["patient_id"] = str(uuid.uuid4())
    entry["created_at"] = _now()
    patients.append(entry)
    _save_json(_uf(current_user, "patients.json"), patients)
    return entry


@app.get("/api/patients")
def get_patients(current_user: dict = Depends(get_current_user)):
    return _load_json(_uf(current_user, "patients.json"))


@app.delete("/api/patients/{patient_id}")
def delete_patient(patient_id: str, current_user: dict = Depends(get_current_user)):
    patients = _load_json(_uf(current_user, "patients.json"))
    _save_json(_uf(current_user, "patients.json"), [p for p in patients if p["patient_id"] != patient_id])
    return {"ok": True}


# ── History ───────────────────────────────────────────────────────────────────

MAX_HISTORY = 30

class HistoryEntryIn(BaseModel):
    diagnosis:    str
    location:     Optional[str]   = None
    ranked_count: int
    top_score:    Optional[float] = None
    result:       dict


@app.post("/api/history")
def save_history(entry: HistoryEntryIn, current_user: dict = Depends(get_current_user)):
    history = _load_json(_uf(current_user, "history.json"))
    item = entry.model_dump()
    item["history_id"] = str(uuid.uuid4())
    item["created_at"] = _now()
    history.append(item)
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
    _save_json(_uf(current_user, "history.json"), history)
    return item


@app.get("/api/history")
def get_history(current_user: dict = Depends(get_current_user)):
    return list(reversed(_load_json(_uf(current_user, "history.json"))))


@app.delete("/api/history/{history_id}")
def delete_history_entry(history_id: str, current_user: dict = Depends(get_current_user)):
    history = _load_json(_uf(current_user, "history.json"))
    _save_json(_uf(current_user, "history.json"), [h for h in history if h["history_id"] != history_id])
    return {"ok": True}


# ── Notes ─────────────────────────────────────────────────────────────────────

class NoteIn(BaseModel):
    nct_id: str
    note:   str


@app.post("/api/notes")
def save_note(n: NoteIn, current_user: dict = Depends(get_current_user)):
    notes = _load_json(_uf(current_user, "notes.json"))
    notes = [x for x in notes if x["nct_id"] != n.nct_id]
    if n.note.strip():
        entry = n.model_dump()
        entry["updated_at"] = _now()
        notes.append(entry)
    _save_json(_uf(current_user, "notes.json"), notes)
    return {"ok": True}


@app.get("/api/notes")
def get_notes(current_user: dict = Depends(get_current_user)):
    return _load_json(_uf(current_user, "notes.json"))


@app.delete("/api/notes/{nct_id}")
def delete_note(nct_id: str, current_user: dict = Depends(get_current_user)):
    notes = _load_json(_uf(current_user, "notes.json"))
    _save_json(_uf(current_user, "notes.json"), [x for x in notes if x["nct_id"] != nct_id])
    return {"ok": True}


# ── Bookmarks ─────────────────────────────────────────────────────────────────

class BookmarkIn(BaseModel):
    nct_id:          str
    title:           str
    score:           float
    phase:           Optional[str] = None
    sponsor:         Optional[str] = None
    url:             Optional[str] = None
    patient_context: Optional[dict] = None
    trial_data:      Optional[dict] = None


@app.post("/api/bookmarks")
def add_bookmark(bm: BookmarkIn, current_user: dict = Depends(get_current_user)):
    bookmarks = _load_json(_uf(current_user, "bookmarks.json"))
    if not any(b["nct_id"] == bm.nct_id for b in bookmarks):
        entry = bm.model_dump()
        entry["bookmarked_at"] = _now()
        bookmarks.append(entry)
        _save_json(_uf(current_user, "bookmarks.json"), bookmarks)
    return {"ok": True}


@app.get("/api/bookmarks")
def get_bookmarks(current_user: dict = Depends(get_current_user)):
    return _load_json(_uf(current_user, "bookmarks.json"))


@app.delete("/api/bookmarks/{nct_id}")
def remove_bookmark(nct_id: str, current_user: dict = Depends(get_current_user)):
    bookmarks = _load_json(_uf(current_user, "bookmarks.json"))
    _save_json(_uf(current_user, "bookmarks.json"), [b for b in bookmarks if b["nct_id"] != nct_id])
    return {"ok": True}


# ── Feedback ──────────────────────────────────────────────────────────────────

class FeedbackIn(BaseModel):
    nct_id:  str
    verdict: str
    note:    Optional[str] = None


@app.post("/api/feedback")
def submit_feedback(fb: FeedbackIn, current_user: dict = Depends(get_current_user)):
    if fb.verdict not in ("relevant", "not_relevant"):
        raise HTTPException(status_code=400, detail="verdict must be 'relevant' or 'not_relevant'")
    feedback = _load_json(_uf(current_user, "feedback.json"))
    entry = fb.model_dump()
    entry["created_at"] = _now()
    feedback = [f for f in feedback if f["nct_id"] != fb.nct_id]
    feedback.append(entry)
    _save_json(_uf(current_user, "feedback.json"), feedback)
    return {"ok": True}


@app.get("/api/feedback")
def get_feedback(current_user: dict = Depends(get_current_user)):
    return _load_json(_uf(current_user, "feedback.json"))


@app.delete("/api/feedback/{nct_id}")
def delete_feedback(nct_id: str, current_user: dict = Depends(get_current_user)):
    feedback = _load_json(_uf(current_user, "feedback.json"))
    _save_json(_uf(current_user, "feedback.json"), [f for f in feedback if f["nct_id"] != nct_id])
    return {"ok": True}


# ── PDF export ────────────────────────────────────────────────────────────────

@app.post("/api/export/csv")
async def export_csv(request: Request, current_user: dict = Depends(get_current_user)):
    import csv, io as _io
    payload = await request.json()
    ranked  = payload.get("ranked_trials", [])
    profile = payload.get("patient_profile") or {}
    buf = _io.StringIO()
    fields = ["rank","nct_id","title","final_score","eligibility_score","logistics_score",
              "quality_score","phase","sponsor","status","nearest_site_miles","url","brief_summary"]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for i, t in enumerate(ranked, 1):
        writer.writerow({
            "rank": i, "nct_id": t.get("nct_id",""), "title": t.get("title",""),
            "final_score": round(t.get("final_score") or 0),
            "eligibility_score": round(t.get("eligibility_score") or 0),
            "logistics_score":   round(t.get("logistics_score")   or 0),
            "quality_score":     round(t.get("quality_score")     or 0),
            "phase": t.get("phase",""), "sponsor": t.get("sponsor",""),
            "status": t.get("status",""),
            "nearest_site_miles": t.get("nearest_site_miles",""),
            "url": t.get("url",""),
            "brief_summary": (t.get("brief_summary") or "")[:300].replace("\n"," "),
        })
    return Response(
        content=buf.getvalue().encode("utf-8"), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trialmatch_results.csv"},
    )


@app.post("/api/export/pdf")
async def export_pdf(request: Request, current_user: dict = Depends(get_current_user)):
    payload   = await request.json()
    pdf_bytes = _generate_pdf(payload)
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=trialmatch_report.pdf"},
    )


def _generate_pdf(data: dict) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether,
    )
    from io import BytesIO

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=0.85*inch, rightMargin=0.85*inch,
                            topMargin=0.85*inch, bottomMargin=0.85*inch)

    OXFORD  = colors.HexColor("#1a4f7a")
    FOREST  = colors.HexColor("#1a6b3c")
    AMBER   = colors.HexColor("#7d4e00")
    CRIMSON = colors.HexColor("#8b1a1a")
    INK     = colors.HexColor("#1a1a1a")
    MUTED   = colors.HexColor("#6b6b6b")
    FAINT   = colors.HexColor("#9b9b9b")
    RULE    = colors.HexColor("#e8e4de")
    BGWARM  = colors.HexColor("#f9f8f5")

    def sty(name, **kw): return ParagraphStyle(name, **kw)

    S_TITLE   = sty("t",  fontName="Helvetica-Bold", fontSize=18, textColor=INK,   spaceAfter=2)
    S_SUB     = sty("s",  fontName="Helvetica",      fontSize=9,  textColor=MUTED, spaceAfter=0)
    S_SECTION = sty("sc", fontName="Helvetica-Bold", fontSize=7,  textColor=FAINT, spaceAfter=6, spaceBefore=12)
    S_BODY    = sty("b",  fontName="Helvetica",      fontSize=9,  textColor=INK,   leading=13)
    S_SMALL   = sty("sm", fontName="Helvetica",      fontSize=8,  textColor=MUTED, leading=12)
    S_TRITLE  = sty("tr", fontName="Helvetica-Bold", fontSize=10, textColor=INK,   leading=14, spaceAfter=3)
    S_REPORT  = sty("rp", fontName="Helvetica",      fontSize=8,  textColor=INK,   leading=12)

    profile  = data.get("patient_profile") or {}
    ranked   = data.get("ranked_trials") or []
    date_str = datetime.now().strftime("%B %d, %Y")
    story    = []

    story.append(Paragraph("TrialMatch", S_TITLE))
    story.append(Paragraph(f"Clinical Trial Matching Report  ·  {date_str}", S_SUB))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=RULE))
    story.append(Spacer(1, 10))

    if profile:
        story.append(Paragraph("PATIENT PROFILE", S_SECTION))
        pdata = []
        def prow(label, val):
            if val:
                pdata.append([
                    Paragraph(label, sty("pl", fontName="Helvetica-Bold", fontSize=7, textColor=FAINT)),
                    Paragraph(str(val), S_BODY),
                ])
        meta = " · ".join(filter(None, [
            f"{profile.get('age')} yo" if profile.get("age") else None,
            profile.get("sex"),
            f"ECOG {profile.get('ecog_score')}" if profile.get("ecog_score") is not None else None,
        ]))
        prow("Diagnosis",    profile.get("diagnosis"))
        prow("Stage",        profile.get("stage"))
        prow("Demographics", meta or None)
        prow("Location",     profile.get("location"))
        prow("Max Travel",   f"{profile.get('max_travel_miles')} miles" if profile.get("max_travel_miles") else None)
        if profile.get("biomarkers"):
            prow("Biomarkers", ", ".join(profile["biomarkers"]))
        if profile.get("prior_treatments"):
            prow("Prior Tx",   ", ".join(profile["prior_treatments"]))
        if pdata:
            t = Table(pdata, colWidths=[1.3*inch, 5.2*inch])
            t.setStyle(TableStyle([
                ("VALIGN", (0,0),(-1,-1),"TOP"),
                ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.white, BGWARM]),
                ("TOPPADDING",(0,0),(-1,-1),4), ("BOTTOMPADDING",(0,0),(-1,-1),4),
                ("LEFTPADDING",(0,0),(-1,-1),6), ("RIGHTPADDING",(0,0),(-1,-1),6),
                ("LINEBELOW",(0,0),(-1,-2),0.3,RULE),
            ]))
            story.append(t)

    story.append(Spacer(1, 10))
    story.append(Paragraph("PIPELINE SUMMARY", S_SECTION))
    candidates = data.get("candidates_count", "—")
    evaluated  = data.get("evaluated_count", "—")
    matched    = len(ranked)
    top_score  = ranked[0].get("final_score") if ranked else None
    stat_cells = [
        [Paragraph(str(x), sty(f"sv{i}", fontName="Helvetica-Bold", fontSize=16, textColor=INK))
         for i, x in enumerate([candidates, evaluated, matched,
                                 f"{round(top_score)}/100" if top_score else "—"])],
        [Paragraph(l, S_SMALL) for l in ["Candidates","Evaluated","Matched","Top Score"]],
    ]
    st = Table(stat_cells, colWidths=[1.6*inch]*4)
    st.setStyle(TableStyle([
        ("ALIGN",(0,0),(-1,-1),"CENTER"), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),8), ("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("BOX",(0,0),(-1,-1),0.5,RULE), ("INNERGRID",(0,0),(-1,-1),0.3,RULE),
        ("BACKGROUND",(0,0),(-1,-1),BGWARM),
    ]))
    story.append(st)
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1, color=RULE))

    if ranked:
        story.append(Paragraph("RANKED MATCHES", S_SECTION))
        for i, trial in enumerate(ranked[:10]):
            score = trial.get("final_score") or 0
            if score >= 70:   tier_label, tier_color = "Strong",   FOREST
            elif score >= 50: tier_label, tier_color = "Moderate", OXFORD
            elif score >= 30: tier_label, tier_color = "Weak",     AMBER
            else:             tier_label, tier_color = "Low",      CRIMSON

            phase = (trial.get("phase") or "N/A").replace("PHASE","Ph ").replace("EARLY_","Early ").replace("_"," ")
            dist  = f"{trial.get('nearest_site_miles')} mi" if trial.get("nearest_site_miles") is not None else "dist unknown"

            ht = Table([[
                Paragraph(f"#{i+1}", sty("rk", fontName="Helvetica-Bold", fontSize=9, textColor=FAINT)),
                Paragraph(trial.get("nct_id",""), sty("nc", fontName="Courier", fontSize=9, textColor=OXFORD)),
                Paragraph(f"{round(score)}/100  {tier_label}", sty("sc2", fontName="Helvetica-Bold", fontSize=9, textColor=tier_color)),
                Paragraph(f"{phase}  ·  {dist}", S_SMALL),
            ]], colWidths=[0.3*inch, 1.0*inch, 1.2*inch, 4.0*inch])
            ht.setStyle(TableStyle([
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"), ("TOPPADDING",(0,0),(-1,-1),6),
                ("BOTTOMPADDING",(0,0),(-1,-1),4), ("LEFTPADDING",(0,0),(-1,-1),6),
                ("BACKGROUND",(0,0),(-1,-1),BGWARM), ("LINEBELOW",(0,0),(-1,-1),0.5,RULE),
            ]))

            blocks = [ht, Spacer(1,4), Paragraph(trial.get("title",""), S_TRITLE)]
            if trial.get("sponsor"):
                blocks.append(Paragraph(trial["sponsor"][:60], S_SMALL))
            if trial.get("brief_summary"):
                blocks += [Spacer(1,4),
                           Paragraph(trial["brief_summary"][:400] + ("…" if len(trial["brief_summary"])>400 else ""), S_REPORT)]
            if trial.get("patient_summary"):
                blocks += [Spacer(1,4),
                           Paragraph("Patient Summary", sty("psh", fontName="Helvetica-Bold", fontSize=7, textColor=OXFORD)),
                           Paragraph(trial["patient_summary"], S_REPORT)]
            if trial.get("physician_brief"):
                blocks += [Spacer(1,4),
                           Paragraph("Physician Brief", sty("pbh", fontName="Helvetica-Bold", fontSize=7, textColor=colors.HexColor("#5b2d8e"))),
                           Paragraph(trial["physician_brief"], S_REPORT)]
            blocks += [Spacer(1,4), HRFlowable(width="100%", thickness=0.5, color=RULE), Spacer(1,8)]

            story.append(KeepTogether(blocks[:3]))
            for b in blocks[3:]:
                story.append(b)
    else:
        story.append(Spacer(1,12))
        story.append(Paragraph("No trials matched above the 30-point threshold.", S_SMALL))

    story.append(Spacer(1,12))
    story.append(Paragraph(
        "Generated by TrialMatch · For informational purposes only · Always confirm eligibility with the trial coordinator.",
        sty("foot", fontName="Helvetica", fontSize=7, textColor=FAINT, alignment=1),
    ))
    doc.build(story)
    return buf.getvalue()
