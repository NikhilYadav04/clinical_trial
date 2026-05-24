"""
Inclusion/Exclusion Checker Agent

Cross-references the patient profile against a structured eligibility checklist
and produces a per-criterion verdict for each trial.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
from src.utils.llm import get_llm, extract_content
from src.utils.retry import with_retry, call_with_timeout
from typing import Literal
import json

from src.state import PatientProfile
from src.agents.eligibility_parser_agent import EligibilityCriterion


SYSTEM_PROMPT = """You are a clinical trial eligibility checker. You will be given:
1. A patient's clinical profile (structured JSON)
2. A list of eligibility criteria for a clinical trial

For each criterion, determine:
- verdict: "PASS", "FAIL", or "UNCERTAIN"
  - PASS: patient clearly meets this criterion
  - FAIL: patient clearly does NOT meet this criterion
  - UNCERTAIN: not enough information to determine
- reason: one sentence explaining the verdict
- is_hard_stop: whether this criterion is an absolute disqualifier (copied from input)

Rules:
- Be conservative — if in doubt, use UNCERTAIN rather than PASS
- For EXCLUSION criteria: PASS means the patient does NOT have the exclusion (good), FAIL means they DO (bad)
- For lab values: if the patient's labs are not provided, mark UNCERTAIN
- A single FAIL on a hard_stop inclusion criterion = patient is ineligible

Return ONLY valid JSON as a list matching the input criteria order. No markdown, no explanation.

Example output:
[
  {"criterion_text": "Histologically confirmed NSCLC", "type": "inclusion", "verdict": "PASS", "reason": "Patient has confirmed NSCLC diagnosis", "is_hard_stop": true},
  {"criterion_text": "ECOG 0 or 1", "type": "inclusion", "verdict": "PASS", "reason": "Patient ECOG is 1", "is_hard_stop": true},
  {"criterion_text": "Prior EGFR inhibitor", "type": "exclusion", "verdict": "PASS", "reason": "No prior EGFR inhibitor in treatment history", "is_hard_stop": true},
  {"criterion_text": "ALT <= 2.5x ULN", "type": "inclusion", "verdict": "UNCERTAIN", "reason": "ALT value not provided in patient profile", "is_hard_stop": false}
]"""


class CriterionVerdict(BaseModel):
    criterion_text: str
    type: Literal["inclusion", "exclusion"]
    verdict: Literal["PASS", "FAIL", "UNCERTAIN"]
    reason: str
    is_hard_stop: bool


class EligibilityResult(BaseModel):
    nct_id: str
    verdicts: list[CriterionVerdict]
    is_eligible: bool          # True if no hard-stop FAILs
    eligibility_score: float   # 0-100 based on PASS rate
    hard_stop_fails: list[str] # criteria that disqualify the patient
    uncertain_items: list[str] # items needing doctor clarification


def check_eligibility(
    patient: PatientProfile,
    criteria: list[EligibilityCriterion],
    nct_id: str,
) -> EligibilityResult:
    """
    Check a patient against a trial's eligibility criteria.
    Returns an EligibilityResult with per-criterion verdicts and overall score.
    """
    if not criteria:
        return EligibilityResult(
            nct_id=nct_id,
            verdicts=[],
            is_eligible=True,
            eligibility_score=50.0,
            hard_stop_fails=[],
            uncertain_items=["No eligibility criteria available for this trial"],
        )

    llm = get_llm(temperature=0)

    patient_summary = patient.model_dump()
    criteria_list = [c.model_dump() for c in criteria]

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Patient profile:\n{json.dumps(patient_summary, indent=2)}\n\n"
            f"Eligibility criteria for trial {nct_id}:\n{json.dumps(criteria_list, indent=2)}"
        )),
    ]

    @with_retry(max_attempts=2, base_delay=2.0)
    def _invoke():
        return llm.invoke(messages)

    try:
        response = call_with_timeout(_invoke, timeout_seconds=120, label=nct_id)
        content = extract_content(response).strip()

        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        raw_list = json.loads(content)
        verdicts = [CriterionVerdict(**item) for item in raw_list]
    except Exception as exc:
        print(f"  [Inclusion/Exclusion] {nct_id} — failed: {exc}")
        # Fallback — mark everything uncertain
        verdicts = [
            CriterionVerdict(
                criterion_text=c.criterion_text,
                type=c.type,
                verdict="UNCERTAIN",
                reason="Could not evaluate — LLM parsing error",
                is_hard_stop=c.is_hard_stop,
            )
            for c in criteria
        ]

    # Compute summary
    hard_stop_fails = [
        v.criterion_text for v in verdicts
        if v.verdict == "FAIL" and v.is_hard_stop
    ]
    uncertain_items = [
        v.criterion_text for v in verdicts
        if v.verdict == "UNCERTAIN"
    ]

    pass_count    = sum(1 for v in verdicts if v.verdict == "PASS")
    uncertain_count = sum(1 for v in verdicts if v.verdict == "UNCERTAIN")
    total = len(verdicts)

    # UNCERTAIN counts as 0.3 of a pass — not neutral.
    # A trial where everything is unknown scores ~30, not 50.
    if total > 0:
        eligibility_score = round(
            ((pass_count + uncertain_count * 0.3) / total) * 100, 1
        )
    else:
        eligibility_score = 50.0

    return EligibilityResult(
        nct_id=nct_id,
        verdicts=verdicts,
        is_eligible=len(hard_stop_fails) == 0,
        eligibility_score=eligibility_score,
        hard_stop_fails=hard_stop_fails,
        uncertain_items=uncertain_items,
    )
