"""
API request / response models.
All data crossing the HTTP boundary is defined here.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field


# ── Request ───────────────────────────────────────────────────────────────────

class PatientFormInput(BaseModel):
    """Structured form fields sent from the frontend."""

    # Demographics
    age:            int             = Field(..., ge=1, le=120)
    sex:            Literal["Female", "Male", "Other"]
    ecog:           int             = Field(..., ge=0, le=4)

    # Diagnosis
    diagnosis:      str             = Field(..., min_length=2)
    stage:          Optional[str]   = None
    biomarkers:     Optional[str]   = None   # free text: "EGFR exon 19 del, PD-L1 40%"

    # Treatment history
    prior_treatments:   Optional[str] = None
    current_medications: Optional[str] = None
    comorbidities:      Optional[str] = None

    # Lab values — open-ended list, user adds any labs they have
    labs: list[dict] = Field(default_factory=list)
    # Each entry: {"name": "Creatinine", "value": "0.9", "unit": "mg/dL"}

    # Location & preferences
    location:    Optional[str] = None
    max_travel:  int           = Field(100, ge=0, le=5000)
    travel_unit: Literal["miles", "km"] = "miles"
    phases:      list[str]     = Field(default_factory=list)  # ["Phase 2", "Phase 3"]


# ── Job status ────────────────────────────────────────────────────────────────

class JobStatusResponse(BaseModel):
    job_id:    str
    status:    Literal["queued", "running", "done", "error"]
    log:       list[str] = []
    error:     Optional[str] = None


# ── Trial result (serialisable subset of TrialRecord) ─────────────────────────

class EligibilityItem(BaseModel):
    criterion_text: str
    type:           str               # "inclusion" | "exclusion"
    verdict:        str               # "PASS" | "FAIL" | "UNCERTAIN"
    reason:         str
    is_hard_stop:   bool


class TrialResult(BaseModel):
    nct_id:        str
    title:         str
    phase:         Optional[str]
    sponsor:       Optional[str]
    status:        str
    url:           str
    brief_summary: Optional[str]
    locations:     list[dict]         = []

    # Scores
    final_score:       Optional[float]
    eligibility_score: Optional[float]
    logistics_score:   Optional[float]
    quality_score:     Optional[float]

    nearest_site_miles: Optional[float]

    eligibility_breakdown: list[EligibilityItem] = []

    # Generated reports
    patient_summary:  Optional[str]
    physician_brief:  Optional[str]
    outreach_email:   Optional[str]


# ── Patient profile (returned so frontend can display it) ─────────────────────

class PatientProfileResponse(BaseModel):
    diagnosis:          str
    stage:              Optional[str]
    biomarkers:         list[str]
    age:                Optional[int]
    sex:                Optional[str]
    ecog_score:         Optional[int]
    prior_treatments:   list[str]
    comorbidities:      list[str]
    current_medications: list[str]
    lab_values:         dict[str, float]
    location:           Optional[str]
    max_travel_miles:   Optional[int]
    missing_info:       list[str]


# ── Full match result ─────────────────────────────────────────────────────────

class MatchResult(BaseModel):
    job_id:           str
    status:           Literal["done", "error"]
    error:            Optional[str]           = None
    patient_profile:  Optional[PatientProfileResponse] = None
    ranked_trials:    list[TrialResult]       = []
    candidates_count: int                     = 0
    evaluated_count:  int                     = 0
    log:              list[str]               = []


# ── Example patients ──────────────────────────────────────────────────────────

class ExamplePatient(BaseModel):
    label:  str
    fields: PatientFormInput
