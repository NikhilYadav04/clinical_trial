# TrialMatch — AI Clinical Trial Matching Agent

<div align="center">

**Compress weeks of manual clinical trial research into minutes.**

An intelligent multi-agent system that matches patients to relevant clinical trials by reading their medical profile and evaluating thousands of trials from ClinicalTrials.gov — criterion by criterion.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-1C3C3C?style=flat-square&logo=langchain&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)
![Claude](https://img.shields.io/badge/LLM-Claude_Sonnet-D4A017?style=flat-square&logo=anthropic&logoColor=white)

</div>

---

## The Problem

- **80%** of clinical trials fail to meet enrollment targets
- Patients with serious conditions spend **months** manually searching 400,000+ trials
- Eligibility criteria are written in **dense medical/legal language**
- Oncologists spend **15–20 minutes per patient** on trial matching — not scalable

TrialMatch solves this by deploying a coordinated pipeline of AI agents that automate the entire matching workflow.

---

## Demo

```
CLINICAL TRIAL MATCHES
Patient: 58F, Stage IIIB NSCLC, EGFR+, post-platinum therapy
Searched: 847 trials → 15 evaluated → 5 ranked matches

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
```

---

## Architecture

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
│   Trial Search Agent         │  ← Queries ClinicalTrials.gov API (50–200 candidates)
└──────────────┬───────────────┘
               │
        FAN OUT (parallel evaluation per trial)
               │
┌─────────────────────────────────────────────────────┐
│             Per-Trial Evaluation Pipeline            │
│                                                     │
│  ┌────────────────────┐  ┌──────────────────────┐  │
│  │ Eligibility Parser │  │ Inclusion / Exclusion │  │
│  │ Agent              │  │ Checker Agent         │  │
│  └────────────────────┘  └──────────────────────┘  │
│                                                     │
│  ┌────────────────────┐  ┌──────────────────────┐  │
│  │ Logistics Agent    │  │ Trial Quality Agent   │  │
│  └────────────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────┐
│   Ranking & Scoring Node     │  ← Weighted composite score (threshold: 30/100)
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│   Report Generation Agent    │  ← Patient summary + Physician brief + Outreach email
└──────────────────────────────┘
```

---

## The 7 Agents

| Agent | Role | Output |
|---|---|---|
| **Patient Profile Agent** | Parses free-text clinical notes into a structured JSON profile. Maps diagnoses to ICD-10/MeSH terms. | `PatientProfile` object |
| **Trial Search Agent** | Queries ClinicalTrials.gov REST API v2 with condition + location + `status=RECRUITING` filters. | List of 50–200 candidate `TrialRecord` objects |
| **Eligibility Parser Agent** | Reads dense medical/legal eligibility text and outputs structured inclusion/exclusion checklists, with criterion type tagging. | Structured checklist per trial |
| **Inclusion/Exclusion Checker Agent** | Checks every criterion against the patient profile: `PASS / FAIL / UNCERTAIN`. Flags hard-stop exclusions. | Per-criterion verdict + confidence score |
| **Logistics Agent** | Calculates distance to nearest trial site using Nominatim geocoding. Estimates visit burden and flags financial assistance. | Logistics feasibility score (0–100) |
| **Trial Quality Agent** | Evaluates trial phase, sponsor credibility, and enrollment pace. | Quality/credibility score (0–100) |
| **Report Generation Agent** | Writes patient-facing plain English summary, physician brief, and coordinator outreach email for each top match. | `patient_summary`, `physician_brief`, `outreach_email` |

---

## Scoring Model

| Dimension | Weight | Notes |
|---|---|---|
| Eligibility match | **40%** | Hard criteria pass rate |
| Biomarker / disease alignment | **20%** | Specificity to patient's subtype |
| Trial quality & phase | **15%** | Phase 3 > Phase 2 > Phase 1 |
| Logistics feasibility | **15%** | Distance + visit burden |
| Enrollment status | **10%** | Actively enrolling vs. slow/stalled |

Only trials scoring **≥ 30/100** are shown.

---

## Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| Agent framework | **LangGraph 0.2+** | Stateful graph, parallel trial evaluation, conditional routing |
| LLM | **Claude Sonnet (claude-sonnet-4-6)** | Medical text parsing, eligibility reasoning, report generation |
| Trial data | **ClinicalTrials.gov REST API v2** | Free, official, 400k+ trials |
| Geocoding | **Nominatim / OpenStreetMap** | Free, global, no API key required |
| Web search | **Tavily API** | PI / sponsor background research |
| Backend | **FastAPI + Uvicorn** | Async SSE streaming, JWT auth, REST endpoints |
| Frontend | **React 18 + Vite + Tailwind CSS** | Real-time pipeline progress, trial cards, export |
| PDF export | **ReportLab** | Formatted patient report PDF |
| Observability | **LangSmith** | Agent trace inspection (optional) |
| Deployment | **Docker Compose** | One-command local or cloud deployment |

---

## Project Structure

```
TrialMatch/
├── api/                        # FastAPI backend
│   ├── main.py                 # All API routes (auth, match, bookmarks, history, export)
│   ├── models.py               # Pydantic request/response models
│   ├── auth.py                 # JWT authentication (register, login, token validation)
│   ├── job_manager.py          # Background job orchestration
│   └── data/                   # Per-user JSON storage (gitignored)
│
├── src/                        # LangGraph agent pipeline
│   ├── graph.py                # Graph assembly — nodes, edges, conditional routing
│   ├── state.py                # PatientProfile, TrialRecord, GraphState definitions
│   ├── agents/
│   │   ├── patient_profile_agent.py
│   │   ├── trial_search_agent.py
│   │   ├── eligibility_parser_agent.py
│   │   ├── inclusion_exclusion_agent.py
│   │   ├── logistics_agent.py          # Geocoding, distance, visit burden
│   │   ├── trial_evaluator.py          # Orchestrates per-trial evaluation
│   │   └── report_agent.py             # Patient summary, physician brief, email
│   ├── tools/
│   │   └── clinicaltrials_api.py       # ClinicalTrials.gov REST API v2 wrapper
│   ├── utils/
│   │   ├── llm.py                      # LLM client factory (Anthropic / Gemini)
│   │   └── retry.py                    # Exponential backoff + timeout utilities
│   └── cache/
│       └── geocode_cache.json          # Persistent geocode cache (auto-generated)
│
├── frontend/                   # React + Vite frontend
│   └── src/
│       ├── App.jsx             # Root app — layout, state, SSE streaming
│       ├── api.js              # API client (all fetch calls)
│       └── components/
│           ├── AuthPage.jsx            # Login / Register
│           ├── PatientForm.jsx         # Patient intake form with example presets
│           ├── TrialCard.jsx           # Trial match card (score, breakdown, bookmark)
│           ├── TrialDetailModal.jsx    # Full trial detail overlay
│           ├── StageDetails.jsx        # Expandable per-stage pipeline details
│           ├── Stepper.jsx             # Live pipeline progress indicator
│           ├── StatsBanner.jsx         # Candidates / Evaluated / Matched / Top Score
│           ├── ProfileCard.jsx         # Extracted patient profile display
│           ├── BookmarksPage.jsx       # Saved trials with comparison tool
│           ├── HistoryPage.jsx         # Previous search history
│           ├── DashboardPage.jsx       # Analytics — score distribution, trends
│           ├── ComparisonModal.jsx     # Side-by-side trial comparison
│           └── OnboardingTour.jsx      # First-use guided walkthrough
│
├── tests/
│   ├── test_phase1.py          # Patient profile & trial search tests
│   ├── test_phase2.py          # Eligibility & logistics agent tests
│   └── test_scenarios.py       # End-to-end real patient scenario tests
│
├── Dockerfile                  # Backend container
├── docker-compose.yml          # Backend + frontend services
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
└── PLAN.md                     # Project architecture plan
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com/)
- *(Optional)* Tavily API key for trial quality web search
- *(Optional)* LangSmith API key for agent tracing

### 1. Clone & configure

```bash
git clone https://github.com/your-username/trialmatch.git
cd trialmatch

cp .env.example .env
# Edit .env and fill in your API keys
```

### 2. Backend setup

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Run the backend

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8005 --reload
```

The API will be available at `http://localhost:8005`.  
Interactive docs: `http://localhost:8005/docs`

### 4. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Docker Compose (recommended)

Run the full stack with a single command:

```bash
cp .env.example .env
# Fill in your API keys in .env

docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8005 |
| API Docs | http://localhost:8005/docs |

User data is persisted in `./api/data/` via a Docker volume mount.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the required values:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional — enables trial quality web search
TAVILY_API_KEY=tvly-...

# Optional — for geocoding via Google Maps (falls back to Nominatim if absent)
GOOGLE_MAPS_API_KEY=...

# Optional — LangSmith agent tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=TrialMatch

# Auth (change in production)
JWT_SECRET=trialmatch-dev-secret-change-in-prod
```

> **Note:** ClinicalTrials.gov API requires no key — it is a free public API.

---

## API Reference

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register a new account |
| `POST` | `/api/auth/login` | Login and receive JWT |
| `GET` | `/api/auth/me` | Get current user info |

### Matching Pipeline

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/match/start` | Start async match job, returns `job_id` |
| `GET` | `/api/match/stream/{job_id}` | SSE stream — logs + final result |
| `POST` | `/api/match` | Synchronous match (blocking) |

### User Data

| Method | Endpoint | Description |
|---|---|---|
| `GET/POST/DELETE` | `/api/bookmarks` | Save / list / remove bookmarked trials |
| `GET/POST/DELETE` | `/api/history` | Search history (auto-saved, last 30) |
| `GET/POST/DELETE` | `/api/notes` | Per-trial notes |
| `GET/POST/DELETE` | `/api/feedback` | Trial relevance feedback |

### Export

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/export/pdf` | Generate formatted PDF report |
| `POST` | `/api/export/csv` | Export results as CSV |

---

## Frontend Features

- **Real-time pipeline progress** — SSE streaming with a 5-step progress indicator
- **Live agent log console** — colour-coded output as each agent runs
- **Patient intake form** — structured fields with 4 built-in example presets (NSCLC, HER2+ breast, ALS, international)
- **Trial cards** — score badges, eligibility breakdown, distance, sponsor, bookmark, feedback
- **Trial Detail Modal** — full eligibility breakdown, patient summary, physician brief, outreach email
- **Side-by-side comparison** — compare up to 2 bookmarked trials
- **Export** — PDF report (ReportLab) and CSV download
- **Search history** — auto-saved, reload any past result
- **Analytics dashboard** — score distribution, match trends, diagnosis breakdown
- **Onboarding tour** — guided first-use walkthrough
- **JWT authentication** — per-user data isolation

---

## Running Tests

```bash
# Phase 1 — patient profile & trial search
pytest tests/test_phase1.py -v

# Phase 2 — eligibility & logistics agents
pytest tests/test_phase2.py -v

# End-to-end scenarios (requires API keys)
pytest tests/test_scenarios.py -v
```

---

## Key Design Decisions

### Parallel trial evaluation
Trials are evaluated concurrently using `ThreadPoolExecutor`. For Anthropic/Gemini, up to 3 workers run in parallel. For local Ollama models (single-threaded), the system automatically falls back to 1 worker.

### Pre-filtering before LLM calls
A cheap keyword-overlap filter removes obviously irrelevant trials before spending LLM tokens on eligibility evaluation, reducing cost and latency significantly.

### Geocoding strategy (no paid API required)
The logistics agent uses a 4-tier geocoding approach:
1. In-memory cache (instant)
2. 200+ city hardcoded lookup (instant, covers major US cities + world capitals)
3. Nominatim via rate limiter (free, global, 1 req/sec)
4. Neutral score fallback (50/100) if location is unknown

### SSE streaming architecture
The backend runs the LangGraph pipeline in a background thread, captures stdout via a custom `TextIOBase` wrapper, and streams log lines + final results to the frontend via Server-Sent Events — giving users live progress feedback without polling.

### Per-user data isolation
All user data (bookmarks, history, notes, feedback) is stored as JSON files under `api/data/{user_id}/`, making it easy to inspect, back up, or migrate without a database dependency.

---

## Built-in Example Patients

The UI ships with 4 real clinical scenarios to demo the system immediately:

| Example | Details |
|---|---|
| NSCLC — EGFR+ (Boston) | 58F, Stage IIIB, post-platinum, EGFR exon 19 del, PD-L1 40% |
| HER2+ Breast Cancer (New York) | 45F, Stage II, ER-/PR-/HER2 3+, treatment-naive |
| ALS (Chicago) | 62M, 18 months post-diagnosis, ALSFRS-R ~38, on Riluzole |
| NSCLC — EGFR+ (Mumbai, India) | 52M, Stage IIIB, post-platinum, Type 2 diabetes comorbidity |

---

## Roadmap

- [ ] PDF export of full patient report
- [ ] Streamlit alternative UI for clinical environments
- [ ] FHIR / EHR integration for structured patient import
- [ ] Multi-condition matching (patients with co-occurring diagnoses)
- [ ] Coordinator contact lookup automation
- [ ] Fine-tuned eligibility parsing model

---

## Contributing

Contributions are welcome! Please open an issue before submitting a pull request for significant changes.

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'feat: add your feature'`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Disclaimer

TrialMatch is a research and informational tool. It does **not** constitute medical advice. Always confirm trial eligibility and suitability with a qualified physician and the trial coordinator before proceeding.

---

<div align="center">
  Built with LangGraph · Powered by Claude · Data from ClinicalTrials.gov
</div>
