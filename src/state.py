from typing import TypedDict, Optional, Annotated
import operator
from pydantic import BaseModel, Field


# ─── Patient Profile ──────────────────────────────────────────────────────────

class PatientProfile(BaseModel):
    """Structured patient clinical profile extracted by Patient Profile Agent."""

    # Core diagnosis
    diagnosis: str = Field(description="Primary diagnosis e.g. Non-Small Cell Lung Cancer")
    stage: Optional[str] = Field(None, description="Stage or grade e.g. Stage IIIB")
    diagnosis_codes: list[str] = Field(default_factory=list, description="ICD-10 or MeSH terms")

    # Biomarkers and genetics
    biomarkers: list[str] = Field(default_factory=list, description="e.g. EGFR mutation positive, PD-L1 40%")

    # Patient demographics
    age: Optional[int] = None
    sex: Optional[str] = None  # male / female / other

    # Clinical status
    ecog_score: Optional[int] = Field(None, description="ECOG performance status 0-4")
    prior_treatments: list[str] = Field(default_factory=list, description="Prior drugs or therapies received")
    comorbidities: list[str] = Field(default_factory=list, description="Other medical conditions")
    current_medications: list[str] = Field(default_factory=list)

    # Lab values (key ones that often appear in eligibility criteria)
    lab_values: dict[str, float] = Field(
        default_factory=dict,
        description="Lab results e.g. {'creatinine': 0.9, 'ALT': 32, 'hemoglobin': 11.2}"
    )

    # Location and preferences
    location: Optional[str] = Field(None, description="City, State or zip code")
    max_travel_miles: Optional[int] = Field(None, description="Max distance patient will travel")
    preferred_phases: list[int] = Field(default_factory=list, description="Preferred trial phases e.g. [2, 3]")

    # Clarifications needed
    missing_info: list[str] = Field(
        default_factory=list,
        description="Fields that were ambiguous or missing from input"
    )


# ─── Trial Record ─────────────────────────────────────────────────────────────

class TrialRecord(BaseModel):
    """A single clinical trial from ClinicalTrials.gov."""

    nct_id: str = Field(description="ClinicalTrials.gov identifier e.g. NCT04948411")
    title: str
    status: str = Field(description="RECRUITING, ACTIVE_NOT_RECRUITING, etc.")
    phase: Optional[str] = None
    sponsor: Optional[str] = None
    conditions: list[str] = Field(default_factory=list)
    interventions: list[str] = Field(default_factory=list)
    eligibility_criteria_raw: Optional[str] = Field(None, description="Raw eligibility text from trial")
    locations: list[dict] = Field(default_factory=list, description="List of site dicts with city/state/country")
    start_date: Optional[str] = None
    completion_date: Optional[str] = None
    enrollment_target: Optional[int] = None
    brief_summary: Optional[str] = None
    url: str = Field(default="")

    # Filled in by evaluation agents
    eligibility_score: Optional[float] = None       # 0-100
    logistics_score: Optional[float] = None         # 0-100
    quality_score: Optional[float] = None           # 0-100
    final_score: Optional[float] = None             # weighted composite

    eligibility_breakdown: list[dict] = Field(
        default_factory=list,
        description="Per-criterion: {criterion, verdict, reason}"
    )
    nearest_site_miles: Optional[float] = None
    patient_summary: Optional[str] = None           # plain English for patient
    physician_brief: Optional[str] = None           # clinical summary for doctor
    outreach_email: Optional[str] = None            # draft email to coordinator


# ─── LangGraph State ──────────────────────────────────────────────────────────

class GraphState(TypedDict):
    """Shared state passed between all nodes in the LangGraph graph."""

    # Input
    raw_patient_input: str

    # Agent outputs
    patient_profile: Optional[PatientProfile]
    candidate_trials: Annotated[list[TrialRecord], operator.add]  # fan-in from parallel nodes
    evaluated_trials: list[TrialRecord]
    ranked_trials: list[TrialRecord]

    # Control
    error: Optional[str]
    status_log: Annotated[list[str], operator.add]  # running log of agent steps
