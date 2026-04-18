"""
Clinical Trial Matching Agent — LangGraph Graph

Phase 1: Patient Profile → Trial Search
Phase 2: Trial Evaluation (parallel per trial) → Ranking
Phase 3: Report Generation (top 5 trials) → Final Output
"""

from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError
from langgraph.graph import StateGraph, END
import re

from src.state import GraphState, TrialRecord
from src.agents.patient_profile_agent import patient_profile_agent
from src.agents.trial_search_agent import trial_search_agent
from src.agents.trial_evaluator import evaluate_trial
from src.agents.report_agent import generate_reports_for_trial


MAX_TRIALS_TO_EVALUATE = 15
MAX_TRIALS_TO_REPORT   = 3

# Ollama is single-threaded — parallel workers just queue up and appear frozen.
# Gemini API can handle concurrency. Set via LLM_PROVIDER env var.
import os as _os
MAX_WORKERS = 1 if _os.getenv("LLM_PROVIDER", "ollama").lower() == "ollama" else 3


# ── Layer 1: Condition relevance pre-filter ───────────────────────────────────

_STOPWORDS = {"and", "the", "with", "for", "non", "cell", "type", "stage",
              "cancer", "tumor", "disease", "advanced", "early", "late"}

def _is_condition_relevant(diagnosis: str, trial: TrialRecord) -> bool:
    """
    Cheap keyword overlap check — no LLM needed.
    Returns False if the trial has zero meaningful overlap with the patient's
    diagnosis, so we skip wasting evaluation calls on wrong-disease trials.
    """
    diag_words = {
        w.lower()
        for w in re.sub(r"[^a-zA-Z0-9 ]", " ", diagnosis).split()
        if len(w) >= 4 and w.lower() not in _STOPWORDS
    }
    if not diag_words:
        return True  # can't filter — let it through

    trial_text = (
        (trial.title or "") + " " +
        " ".join(trial.conditions or [])
    ).lower()

    return any(word in trial_text for word in diag_words)


# ── Node: Evaluate all trials in parallel ────────────────────────────────────

def trial_evaluation_node(state: GraphState) -> dict:
    patient = state.get("patient_profile")
    trials: list[TrialRecord] = state.get("candidate_trials", [])

    if not patient or not trials:
        return {
            "evaluated_trials": [],
            "status_log": ["Trial evaluation skipped — no candidates or no patient profile"],
        }

    # Layer 1 — pre-filter irrelevant trials before spending LLM calls on them
    relevant = [t for t in trials if _is_condition_relevant(patient.diagnosis, t)]
    irrelevant_count = len(trials) - len(relevant)
    if irrelevant_count:
        print(f"\n[Evaluation Node] Pre-filter: removed {irrelevant_count} off-topic trials "
              f"({len(relevant)} remaining)")

    trials_to_evaluate = relevant[:MAX_TRIALS_TO_EVALUATE]
    print(f"\n[Evaluation Node] Evaluating {len(trials_to_evaluate)} trials (workers={MAX_WORKERS})...")

    evaluated: list[TrialRecord] = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(evaluate_trial, patient, trial): trial
            for trial in trials_to_evaluate
        }
        for future in as_completed(futures):
            original = futures[future]
            try:
                evaluated.append(future.result(timeout=300))  # 5-min hard ceiling per trial
            except FutureTimeoutError:
                print(f"  [Evaluation Node] Hard timeout (5 min) for {original.nct_id} — skipping")
                original.final_score = 0.0
                evaluated.append(original)
            except Exception as e:
                print(f"  [Evaluation Node] Failed for {original.nct_id}: {e}")
                original.final_score = 0.0
                evaluated.append(original)

    print(f"[Evaluation Node] Done — {len(evaluated)} trials evaluated")

    return {
        "evaluated_trials": evaluated,
        "status_log": [f"Evaluated {len(evaluated)} trials"],
    }


# ── Node: Rank evaluated trials ──────────────────────────────────────────────

def ranking_node(state: GraphState) -> dict:
    evaluated = state.get("evaluated_trials", [])

    if not evaluated:
        return {
            "ranked_trials": [],
            "status_log": ["Ranking skipped — no evaluated trials"],
        }

    ranked = sorted(evaluated, key=lambda t: t.final_score or 0, reverse=True)
    ranked = [t for t in ranked if (t.final_score or 0) >= 30]

    print(f"\n[Ranking Node] Ranked {len(ranked)} trials")

    top = ranked[0].final_score if ranked else "N/A"
    return {
        "ranked_trials": ranked,
        "status_log": [f"Ranked {len(ranked)} eligible trials — top score: {top}"],
    }


# ── Node: Generate reports for top N trials ──────────────────────────────────

def report_generation_node(state: GraphState) -> dict:
    patient = state.get("patient_profile")
    ranked = state.get("ranked_trials", [])

    if not patient or not ranked:
        return {
            "ranked_trials": ranked,
            "status_log": ["Report generation skipped — no ranked trials"],
        }

    top_trials = ranked[:MAX_TRIALS_TO_REPORT]
    print(f"\n[Report Node] Generating reports for top {len(top_trials)} trials...")

    updated: list[TrialRecord] = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(generate_reports_for_trial, patient, trial): trial
            for trial in top_trials
        }
        for future in as_completed(futures):
            try:
                updated.append(future.result())
            except Exception as e:
                original = futures[future]
                print(f"  [Report Node] Failed for {original.nct_id}: {e}")
                updated.append(original)

    # Merge: updated top trials + rest unchanged
    updated_ids = {t.nct_id for t in updated}
    rest = [t for t in ranked if t.nct_id not in updated_ids]

    # Re-sort to preserve ranking order
    all_trials = updated + rest
    all_trials.sort(key=lambda t: t.final_score or 0, reverse=True)

    print(f"[Report Node] Reports generated for {len(updated)} trials")

    return {
        "ranked_trials": all_trials,
        "status_log": [f"Reports generated for top {len(updated)} matches"],
    }


# ── Routing ───────────────────────────────────────────────────────────────────

def route_after_profile(state: GraphState) -> str:
    if state.get("error") or not state.get("patient_profile"):
        return "end"
    return "search"


def route_after_search(state: GraphState) -> str:
    if not state.get("candidate_trials"):
        return "end"
    return "evaluate"


# ── Graph assembly ────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(GraphState)

    graph.add_node("patient_profile",   patient_profile_agent)
    graph.add_node("trial_search",      trial_search_agent)
    graph.add_node("trial_evaluation",  trial_evaluation_node)
    graph.add_node("ranking",           ranking_node)
    graph.add_node("report_generation", report_generation_node)

    graph.set_entry_point("patient_profile")

    graph.add_conditional_edges(
        "patient_profile",
        route_after_profile,
        {"search": "trial_search", "end": END},
    )

    graph.add_conditional_edges(
        "trial_search",
        route_after_search,
        {"evaluate": "trial_evaluation", "end": END},
    )

    graph.add_edge("trial_evaluation",  "ranking")
    graph.add_edge("ranking",           "report_generation")
    graph.add_edge("report_generation", END)

    return graph.compile()


app = build_graph()
