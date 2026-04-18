"""
Job Manager — only builds patient text now.
Pipeline runs directly in main.py via SSE stream.
"""

from api.models import PatientFormInput


def build_patient_text(form: PatientFormInput) -> str:
    """Convert structured form fields into natural-language string for the agents."""
    parts = []

    line = f"{form.age}-year-old {form.sex.lower()} with {form.diagnosis}"
    if form.stage:
        line += f", {form.stage}"
    parts.append(line + ".")

    if form.biomarkers:
        parts.append(f"Biomarkers: {form.biomarkers}.")
    if form.prior_treatments:
        parts.append(f"Prior treatments: {form.prior_treatments}.")
    if form.current_medications:
        parts.append(f"Current medications: {form.current_medications}.")
    if form.comorbidities:
        parts.append(f"Comorbidities: {form.comorbidities}.")

    parts.append(f"ECOG performance status {form.ecog}.")

    if form.labs:
        lab_parts = [
            f"{l['name']} {l['value']} {l.get('unit', '')}".strip()
            for l in form.labs
            if l.get('name') and l.get('value')
        ]
        if lab_parts:
            parts.append(f"Lab values: {', '.join(lab_parts)}.")

    if form.location:
        parts.append(
            f"Located in {form.location}. "
            f"Willing to travel up to {form.max_travel} {form.travel_unit}."
        )
    if form.phases:
        parts.append(f"Interested in {', '.join(form.phases)} trials only.")

    return "\n".join(parts)
