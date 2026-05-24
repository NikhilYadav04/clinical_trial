"""
Eligibility Parser Agent

Reads raw eligibility criteria text from a clinical trial (dense medical/legal language)
and extracts a structured checklist of inclusion and exclusion criteria.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from src.utils.llm import get_llm, extract_content
from src.utils.retry import with_retry, call_with_timeout
from typing import Literal
import json


SYSTEM_PROMPT = """You are a clinical trial eligibility specialist. Parse raw eligibility criteria
text from clinical trial records into a structured, machine-readable checklist.

For each criterion extract:
- criterion_text: concise version of the original criterion
- type: "inclusion" or "exclusion"
- category: one of — "diagnosis", "biomarker", "prior_treatment", "lab_value",
             "functional_status", "age", "demographics", "comorbidity", "medication", "other"
- is_hard_stop: true if failing this is an absolute disqualifier
- key_values: specific numbers/values (e.g. {"ECOG_max": 1, "creatinine_max_mg_dL": 1.5})

Return ONLY a valid JSON list. No markdown, no explanation.

Example:
[
  {"criterion_text": "Histologically confirmed NSCLC", "type": "inclusion", "category": "diagnosis", "is_hard_stop": true, "key_values": {}},
  {"criterion_text": "ECOG performance status 0 or 1", "type": "inclusion", "category": "functional_status", "is_hard_stop": true, "key_values": {"ECOG_max": 1}},
  {"criterion_text": "Prior treatment with EGFR inhibitor", "type": "exclusion", "category": "prior_treatment", "is_hard_stop": true, "key_values": {}},
  {"criterion_text": "ALT/AST <= 2.5x ULN", "type": "inclusion", "category": "lab_value", "is_hard_stop": false, "key_values": {"ALT_max_x_ULN": 2.5}}
]"""


class EligibilityCriterion(BaseModel):
    criterion_text: str
    type: Literal["inclusion", "exclusion"]
    category: Literal[
        "diagnosis", "biomarker", "prior_treatment", "lab_value",
        "functional_status", "age", "demographics", "comorbidity", "medication", "other"
    ]
    is_hard_stop: bool = True
    key_values: dict = Field(default_factory=dict)


def parse_eligibility_criteria(raw_criteria: str, nct_id: str) -> list[EligibilityCriterion]:
    """
    Parse raw eligibility text into a structured checklist.
    Returns list of EligibilityCriterion objects.
    """
    if not raw_criteria or len(raw_criteria.strip()) < 20:
        return []

    llm = get_llm(temperature=0)

    # Truncate very long criteria to avoid token limits
    criteria_text = raw_criteria[:3000] if len(raw_criteria) > 3000 else raw_criteria

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Parse eligibility criteria for trial {nct_id}:\n\n{criteria_text}"),
    ]

    @with_retry(max_attempts=2, base_delay=2.0)
    def _invoke():
        return llm.invoke(messages)

    try:
        response = call_with_timeout(_invoke, timeout_seconds=120, label=nct_id)
    except Exception as exc:
        print(f"  [Eligibility Parser] {nct_id} — timed out or failed after retries: {exc}")
        return []

    content = extract_content(response).strip()

    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        raw_list = json.loads(content)
        return [EligibilityCriterion(**item) for item in raw_list]
    except Exception:
        return []
