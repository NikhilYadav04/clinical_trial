# Clinical Trial Matching Agent — Project Plan

## Overview

An AI agent system that matches patients to relevant clinical trials by reading their medical profile and intelligently evaluating thousands of trials from ClinicalTrials.gov. Compresses weeks of manual research into minutes.

**Framework:** LangGraph  
**LLM:** Claude Sonnet (claude-sonnet-4-6)  
**Primary API:** ClinicalTrials.gov REST API v2 (free, official)  
**UI:** Streamlit  

---

## Problem Statement

- 80% of clinical trials fail to meet enrollment targets
- Patients with serious conditions spend months manually searching 400,000+ trials
- Eligibility criteria are written in dense medical/legal language
- Oncologists spend 15-20 mins per patient on trial matching — not scalable

---

## System Architecture

```
USER INPUT
(diagnosis, medications, labs, history, location, preferences)
        │
        ▼
┌──────────────────────────────┐
│   Patient Profile Agent      │  ← Structures raw input into normalized clinical profile
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│   Trial Search Agent         │  ← Queries ClinicalTrials.gov API (50-200 candidates)
└──────────────┬───────────────┘
               │
        FAN OUT (parallel per trial batch)
               │
┌──────────────────────────────────────────────────┐
│            Per-Trial Evaluation Pipeline          │
│                                                  │
│  ┌────────────────────┐  ┌─────────────────────┐ │
│  │ Eligibility Parser │  │ Inclusion/Exclusion  │ │
│  │ Agent              │  │ Checker Agent        │ │
│  └────────────────────┘  └─────────────────────┘ │
│                                                  │
│  ┌────────────────────┐  ┌─────────────────────┐ │
│  │ Logistics Agent    │  │ Trial Quality Agent  │ │
│  └────────────────────┘  └─────────────────────┘ │
└──────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────┐
│   Ranking & Scoring Agent    │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│   Report Generation Agent    │  ← Patient report + Physician brief
│   + Outreach Draft Agent     │  ← Coordinator outreach emails
└──────────────────────────────┘
```

---

## The 7 Agents

### Agent 1 — Patient Profile Agent
- **Input:** Free-text patient description or structured form
- **Does:** Extracts diagnosis (with stage/grade), medications, lab values, biomarkers, ECOG score, prior treatments, age, sex, comorbidities, location, preferences
- **Maps:** Diagnosis to ICD-10/MeSH terms for better API matching
- **Output:** Structured patient profile JSON

### Agent 2 — Trial Search Agent
- **Input:** Patient profile JSON
- **Does:** Queries ClinicalTrials.gov API with condition + location + status=RECRUITING filters, pulls 50-200 candidate trials
- **Tools:** ClinicalTrials.gov REST API v2
- **Output:** List of candidate trial IDs + metadata

### Agent 3 — Eligibility Parser Agent
- **Input:** Raw eligibility criteria text from trial record
- **Does:** Parses dense medical/legal text into structured inclusion and exclusion criteria checklist, categorizes each criterion type (biomarker, lab value, prior treatment, functional status, age)
- **Output:** Structured eligibility checklist per trial

### Agent 4 — Inclusion/Exclusion Checker Agent
- **Input:** Patient profile + eligibility checklist
- **Does:** Checks patient against every criterion — PASS / FAIL / UNCERTAIN, flags hard-stop exclusions, calculates eligibility confidence score
- **Output:** Per-criterion verdict + overall eligibility verdict

### Agent 5 — Logistics Agent
- **Input:** Trial site locations + patient location + visit schedule
- **Does:** Calculates distance to nearest site, estimates visit burden, flags financial assistance programs
- **Tools:** Google Maps API (distance matrix)
- **Output:** Logistics feasibility score

### Agent 6 — Trial Quality Agent
- **Input:** Trial metadata
- **Does:** Evaluates phase (1/2/3), sponsor credibility, enrollment pace, principal investigator background
- **Tools:** ClinicalTrials.gov API + Tavily web search
- **Output:** Trial quality/credibility score

### Agent 7 — Report Generation + Outreach Agent
- **Input:** All scored/evaluated trials
- **Does:** Writes patient-facing plain English summary, physician brief, coordinator outreach emails, "questions to ask your doctor" list
- **Output:** Ranked matches PDF + JSON

---

## Scoring Model

| Dimension                  | Weight | Notes                                   |
|----------------------------|--------|-----------------------------------------|
| Eligibility match          | 40%    | Hard criteria pass rate                 |
| Biomarker/disease alignment| 20%    | Specificity to patient's subtype        |
| Trial quality & phase      | 15%    | Phase 3 > Phase 2 > Phase 1             |
| Logistics feasibility      | 15%    | Distance + visit burden                 |
| Enrollment status          | 10%    | Actively enrolling vs. slow/stalled     |

---

## Tech Stack

| Component        | Choice                    | Why                                      |
|------------------|---------------------------|------------------------------------------|
| Agent framework  | LangGraph                 | Stateful graph, parallel trial eval      |
| LLM              | claude-sonnet-4-6         | Medical text parsing, report generation  |
| Trial data       | ClinicalTrials.gov API v2 | Free, official, 400k+ trials             |
| Distance calc    | Google Maps API           | Free tier sufficient                     |
| Web search       | Tavily API                | PI/sponsor research                      |
| Output           | JSON + PDF (ReportLab)    | Shareable patient report                 |
| UI               | Streamlit                 | Patient intake form + results dashboard  |

---

## Build Phases

### Phase 1 — Foundation
- [x] Create project plan doc
- [ ] Set up project structure (folders, requirements.txt, .env)
- [ ] Integrate ClinicalTrials.gov API v2 — explore endpoints
- [ ] Build Patient Profile Agent (form → structured JSON)
- [ ] Build Trial Search Agent (query API, return raw trial list)
- [ ] Test: input a real cancer diagnosis, get trials back

### Phase 2 — Core Matching Logic
- [ ] Build Eligibility Parser Agent (LLM reads criteria → structured checklist)
- [ ] Build Inclusion/Exclusion Checker Agent (patient vs. checklist)
- [ ] Build Logistics Agent (distance calculation + visit burden)
- [ ] Wire parallel fan-out in LangGraph — evaluate trials concurrently

### Phase 3 — Scoring & Output
- [ ] Build Trial Quality Agent (phase, sponsor, enrollment pace)
- [ ] Implement weighted scoring model
- [ ] Build Report Generation Agent (patient-facing + physician brief)
- [ ] Build Outreach Draft Agent (coordinator emails)
- [ ] Generate structured JSON + readable report

### Phase 4 — Polish
- [ ] Build Streamlit UI — patient intake form + results dashboard
- [ ] PDF export of full patient report
- [ ] Test on 5 real patient scenarios
- [ ] Add "questions to ask your doctor" generation
- [ ] Write README with architecture diagram
- [ ] Record 2-minute demo video

---

## Sample Output

```
CLINICAL TRIAL MATCHES
Patient: 58F, Stage IIIB NSCLC, EGFR+, post-platinum therapy
Searched: 847 trials → 12 matches → Top 5 shown

MATCH 1 — NCT04948411                 Score: 91/100
Osimertinib + Savolitinib — Phase 3
Sponsor: AstraZeneca | Site: Mass General, Boston (3.2 miles)

Why this matches you:
✓ Targets EGFR mutations specifically (your subtype)
✓ Designed for patients who received prior platinum therapy
✓ ECOG 0-1 required — you qualify
✓ Phase 3 — highest evidence stage

What's involved:
Daily oral pill. 6 clinic visits over 12 months.
No hospital stays required. Travel assistance available.

Confirm with your doctor:
- Your ALT level must be under 3x normal range
- Cannot have received prior EGFR inhibitor therapy
```
