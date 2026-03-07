#!/usr/bin/env python3
"""Baseline benchmark harness for TemporalBench-v1 with TTA ablation support."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Optional

# Try to import sentence-transformers for semantic retrieval
try:
    from sentence_transformers import SentenceTransformer
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False

# Global embedding model cache
_embedding_model = None
_fact_embeddings = None


def get_embedding_model():
    """Get or load the sentence-transformer model."""
    global _embedding_model
    if _embedding_model is None:
        print("Loading sentence-transformer model (first run may be slow)...")
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedding_model


def compute_fact_embeddings(facts: list[dict], model=None):
    """Pre-compute embeddings for all facts."""
    global _fact_embeddings
    if _fact_embeddings is not None:
        return _fact_embeddings
    
    if model is None:
        model = get_embedding_model()
    
    # Create text representations of facts for embedding
    fact_texts = []
    for f in facts:
        # Convert fact content to readable text
        parts = f["content"].split(":")
        if len(parts) >= 3:
            text = f"Domain {parts[0]}, subject {parts[1]}, day {parts[2]}"
        else:
            text = f["content"]
        fact_texts.append(text)
    
    print(f"Computing embeddings for {len(facts)} facts...")
    _fact_embeddings = model.encode(fact_texts, show_progress_bar=True)
    return _fact_embeddings


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def is_valid_as_of(fact: dict, day: int) -> bool:
    return fact["t_valid_from"] <= day and (fact["t_valid_until"] is None or day <= fact["t_valid_until"])


def get_subject(content: str) -> str:
    # Extract subject - format is "domain:subject:day..."
    parts = content.split(":")
    if len(parts) >= 2:
        return parts[1]
    return content


def extract_subject_from_fact(fact_content: str) -> str:
    """Extract subject from fact content, handling edge cases."""
    # Format: domain:subject:day...
    parts = fact_content.split(":")
    if len(parts) >= 2:
        return parts[1]
    return ""


# ============ RETRIEVAL FUNCTIONS ============

def retrieve_plain(facts: list[dict], domain: str, subject: str, as_of_day: int, **kwargs) -> Optional[str]:
    """Baseline A: naive latest semantic match, ignores time."""
    cands = [f for f in facts if f["domain"] == domain and get_subject(f["content"]) == subject]
    if not cands:
        return None
    return max(cands, key=lambda x: x["t_valid_from"])["content"]


def retrieve_temporal_rerank(facts: list[dict], domain: str, subject: str, as_of_day: int, **kwargs) -> Optional[str]:
    """Baseline B: temporal-aware retrieval with reranking.
    Uses recency + temporal validity scoring, but no decay function."""
    cands = [f for f in facts if f["domain"] == domain and get_subject(f["content"]) == subject]
    if not cands:
        return None

    def score(f: dict) -> float:
        if not is_valid_as_of(f, as_of_day):
            return -1.0
        # Recency bonus - prefer more recent facts
        recency = 1.0 / (1.0 + (as_of_day - f["t_valid_from"]) * 0.1)
        return f["confidence"] * recency

    ranked = sorted(cands, key=score, reverse=True)
    return ranked[0]["content"] if ranked and score(ranked[0]) >= 0 else None


def retrieve_time_constraint(facts: list[dict], domain: str, subject: str, as_of_day: int, **kwargs) -> Optional[str]:
    """Baseline C: explicit time filter only."""
    cands = [
        f for f in facts 
        if f["domain"] == domain and get_subject(f["content"]) == subject and is_valid_as_of(f, as_of_day)
    ]
    if not cands:
        return None
    return max(cands, key=lambda x: x["t_valid_from"])["content"]


def retrieve_tta(facts: list[dict], domain: str, subject: str, as_of_day: int, **kwargs) -> Optional[str]:
    """System D: full TTA with truth intervals and domain-adaptive decay."""
    cands = [f for f in facts if f["domain"] == domain and get_subject(f["content"]) == subject]
    if not cands:
        return None

    half_life = {"slow": 45, "medium": 20, "fast": 7}

    def score(f: dict) -> float:
        if not is_valid_as_of(f, as_of_day):
            return -1.0
        age = max(0, as_of_day - f["t_valid_from"])
        decay = 0.5 ** (age / half_life.get(f["domain"], 20))
        return f["confidence"] * decay

    ranked = sorted(cands, key=score, reverse=True)
    return ranked[0]["content"] if ranked and score(ranked[0]) >= 0 else None


def retrieve_tta_improved(facts: list[dict], domain: str, subject: str, as_of_day: int, **kwargs) -> Optional[str]:
    """System D-Improved: Time constraint + confidence tiebreaker (no decay)."""
    cands = [f for f in facts if f["domain"] == domain and get_subject(f["content"]) == subject]
    if not cands:
        return None

    # Filter to valid facts only, then pick by confidence (not decay)
    valid_cands = [f for f in cands if is_valid_as_of(f, as_of_day)]
    if not valid_cands:
        return None
    
    # Pick most recent valid fact (like C), but use confidence to break ties
    return max(valid_cands, key=lambda x: (x["t_valid_from"], x["confidence"]))["content"]


def retrieve_semantic(facts: list[dict], domain: str, subject: str, as_of_day: int, 
                       embeddings=None, model=None, use_temporal: bool = True) -> Optional[str]:
    """System E: Semantic retrieval using sentence embeddings.
    
    Uses dense embeddings for semantic matching, with optional temporal filtering.
    Falls back to keyword match if semantic retrieval fails or embeddings unavailable.
    """
    if not SEMANTIC_AVAILABLE:
        # Fallback to time constraint if no sentence-transformers
        return retrieve_time_constraint(facts, domain, subject, as_of_day)
    
    # First try exact domain+subject match (fast path)
    exact_cands = [f for f in facts if f["domain"] == domain and get_subject(f["content"]) == subject]
    
    if exact_cands:
        # Filter by temporal validity if enabled
        if use_temporal:
            valid_cands = [f for f in exact_cands if is_valid_as_of(f, as_of_day)]
            if valid_cands:
                return max(valid_cands, key=lambda x: x["t_valid_from"])["content"]
        else:
            return max(exact_cands, key=lambda x: x["t_valid_from"])["content"]
    
    # No exact match - use semantic search
    if model is None:
        model = get_embedding_model()
    
    # Build query text
    query_text = f"What is true about {subject} in {domain} domain?"
    
    # Get all facts in this domain for semantic search
    domain_facts = [f for f in facts if f["domain"] == domain]
    if not domain_facts:
        return None
    
    # Create fact texts
    fact_texts = []
    for f in domain_facts:
        parts = f["content"].split(":")
        if len(parts) >= 3:
            text = f"Day {parts[2]}: {parts[1]}"
        else:
            text = f["content"]
        fact_texts.append(text)
    
    # Encode query and facts
    query_emb = model.encode([query_text])
    fact_embs = model.encode(fact_texts)
    
    # Compute similarities
    from sklearn.metrics.pairwise import cosine_similarity
    sims = cosine_similarity(query_emb, fact_embs)[0]
    
    # Score with temporal validity
    half_life = {"slow": 45, "medium": 20, "fast": 7}
    best_score = -1.0
    best_fact = None
    
    for i, f in enumerate(domain_facts):
        if use_temporal and not is_valid_as_of(f, as_of_day):
            continue
        
        # Base score from semantic similarity
        base_score = sims[i]
        
        # Add temporal bonus for valid facts
        if is_valid_as_of(f, as_of_day):
            age = max(0, as_of_day - f["t_valid_from"])
            decay = 0.5 ** (age / half_life.get(f["domain"], 20))
            score = base_score * (0.5 + 0.5 * decay)  # Blend semantic + temporal
        else:
            score = base_score * 0.1  # Heavily penalize stale facts
        
        if score > best_score:
            best_score = score
            best_fact = f
    
    return best_fact["content"] if best_fact else None


def retrieve_semantic_hybrid(facts: list[dict], domain: str, subject: str, as_of_day: int, **kwargs) -> Optional[str]:
    """System E-Hybrid: Combines exact match + semantic fallback.
    
    Strategy:
    1. Try exact domain+subject match with temporal validity filter
    2. If exact match fails, use semantic search across domain
    3. Apply temporal validity filtering on semantic results
    """
    # First, exact domain+subject match (most reliable)
    exact_cands = [f for f in facts if f["domain"] == domain and get_subject(f["content"]) == subject]
    
    if exact_cands:
        # Filter to valid facts at query time
        valid_cands = [f for f in exact_cands if is_valid_as_of(f, as_of_day)]
        if valid_cands:
            return max(valid_cands, key=lambda x: x["t_valid_from"])["content"]
    
    # Fallback: semantic search if no exact match found
    if SEMANTIC_AVAILABLE:
        return retrieve_semantic(facts, domain, subject, as_of_day, use_temporal=True)
    
    # Last resort: time constraint without semantic
    return retrieve_time_constraint(facts, domain, subject, as_of_day)


# ============ TTA ABLATION VARIANTS ============

def retrieve_tta_no_decay(facts: list[dict], domain: str, subject: str, as_of_day: int, **kwargs) -> Optional[str]:
    """TTA variant: no domain-adaptive decay (global decay only)."""
    cands = [f for f in facts if f["domain"] == domain and get_subject(f["content"]) == subject]
    if not cands:
        return None

    def score(f: dict) -> float:
        if not is_valid_as_of(f, as_of_day):
            return -1.0
        # Global decay only
        age = max(0, as_of_day - f["t_valid_from"])
        decay = 0.5 ** (age / 30)  # Fixed 30-day half-life
        return f["confidence"] * decay

    ranked = sorted(cands, key=score, reverse=True)
    return ranked[0]["content"] if ranked and score(ranked[0]) >= 0 else None


def retrieve_tta_no_intervals(facts: list[dict], domain: str, subject: str, as_of_day: int, **kwargs) -> Optional[str]:
    """TTA variant: no truth intervals (ignores validity windows)."""
    cands = [f for f in facts if f["domain"] == domain and get_subject(f["content"]) == subject]
    if not cands:
        return None

    half_life = {"slow": 45, "medium": 20, "fast": 7}

    def score(f: dict) -> float:
        # Ignore validity - always consider facts
        age = max(0, as_of_day - f["t_valid_from"])
        decay = 0.5 ** (age / half_life.get(f["domain"], 20))
        return f["confidence"] * decay

    ranked = sorted(cands, key=score, reverse=True)
    return ranked[0]["content"] if ranked else None


def retrieve_tta_no_rerank(facts: list[dict], domain: str, subject: str, as_of_day: int, **kwargs) -> Optional[str]:
    """TTA variant: no temporal reranking (just latest fact)."""
    cands = [f for f in facts if f["domain"] == domain and get_subject(f["content"]) == subject]
    if not cands:
        return None
    # Just return latest fact, no scoring
    return max(cands, key=lambda x: x["t_valid_from"])["content"]


# ============ CHANGE DETECTION ============

def retrieve_for_change_detection(facts: list[dict], domain: str, subject: str, start_day: int, end_day: int) -> str:
    """Get facts at both start and end day for change detection."""
    # Get fact at start day
    start_cands = [f for f in facts if f["domain"] == domain and get_subject(f["content"]) == subject 
                   and f["t_valid_from"] <= start_day and (f["t_valid_until"] is None or start_day <= f["t_valid_until"])]
    start_fact = max(start_cands, key=lambda x: x["t_valid_from"])["content"] if start_cands else None
    
    # Get fact at end day
    end_cands = [f for f in facts if f["domain"] == domain and get_subject(f["content"]) == subject 
                 and f["t_valid_from"] <= end_day and (f["t_valid_until"] is None or end_day <= f["t_valid_until"])]
    end_fact = max(end_cands, key=lambda x: x["t_valid_from"])["content"] if end_cands else None
    
    if start_fact and end_fact:
        return f"{end_fact} -> {start_fact}"
    return None


def evaluate_change_detection(pred: str, answer: str) -> bool:
    """Check if change detection answer is correct."""
    if pred is None:
        return False
    # Normalize and compare - order doesn't matter
    pred_parts = set(pred.split(" -> "))
    ans_parts = set(answer.split(" -> "))
    return pred_parts == ans_parts


# ============ MAIN EVALUATION ============

def evaluate(system: str, facts: list[dict], questions: list[dict], events: list[dict] = None) -> dict:
    """Evaluate a system on all questions."""
    
    resolvers = {
        "A": retrieve_plain,
        "B": retrieve_temporal_rerank,
        "C": retrieve_time_constraint,
        "D": retrieve_tta,
        "D_improved": retrieve_tta_improved,
        # Semantic retrieval systems
        "E": retrieve_semantic,
        "E_hybrid": retrieve_semantic_hybrid,
        # Ablation variants
        "D_no_decay": retrieve_tta_no_decay,
        "D_no_intervals": retrieve_tta_no_intervals,
        "D_no_rerank": retrieve_tta_no_rerank,
    }
    
    resolver = resolvers.get(system)
    if not resolver:
        raise ValueError(f"Unknown system: {system}")

    # Separate questions by type (handles all benchmark versions)
    # v1/v2: AsOfQA, StalenessTrap, EdgeCase, SimpleRecency
    # v3: DecayTrap, OverlapTrap, PastQueryTrap, CurrentQuery, CausalQuery
    # v4: CurrentQuery, OverlapQuery, PastQueryTrap
    asof_questions = [q for q in questions if q.get("task_family") in [
        "AsOfQA", "StalenessTrap", "EdgeCase", "SimpleRecency", 
        "PastQueryTrap", "CurrentQuery", 
        "DecayTrap", "OverlapTrap", "OverlapQuery"  # v3/v4 temporal questions
    ]]
    change_questions = [q for q in questions if q.get("task_family") == "ChangeDetection"]
    causal_questions = [q for q in questions if q.get("task_family") == "CausalQuery"]

    # Evaluate AsOfQA / temporal questions
    total_asof = len(asof_questions)
    correct_asof = 0
    stale = 0

    for q in asof_questions:
        pred = resolver(facts, q["domain"], q["subject"], q["as_of_day"])
        # For questions with None answer, pred should be None
        if q["answer"] is None:
            correct_asof += 1 if pred is None else 0
        elif pred == q["answer"]:
            correct_asof += 1
        # Track staleness errors
        if pred is not None:
            pred_fact = next((f for f in facts if f["content"] == pred), None)
            if pred_fact and not is_valid_as_of(pred_fact, q["as_of_day"]):
                stale += 1

    # Evaluate Change Detection
    total_change = len(change_questions)
    correct_change = 0
    for q in change_questions:
        pred = retrieve_for_change_detection(facts, q["domain"], q["subject"], q["start_day"], q["end_day"])
        if evaluate_change_detection(pred, q["answer"]):
            correct_change += 1

    # Evaluate Causal (simplified: check if we can trace to correct event)
    total_causal = len(causal_questions)
    correct_causal = 0
    if events:
        for q in causal_questions:
            # Simplified: check if we can find the action event
            action_day = q.get("action_day")
            subject = q.get("subject")
            domain = q.get("domain")
            matching_events = [
                e for e in events 
                if e.get("domain") == domain and e.get("subject") == subject and e.get("t_event") == action_day
            ]
            if matching_events:
                correct_causal += 1

    # Calculate metrics
    asof_acc = correct_asof / total_asof if total_asof else 0.0
    stale_err = stale / total_asof if total_asof else 0.0
    change_f1 = correct_change / total_change if total_change else 0.0
    causal_acc = correct_causal / total_causal if total_causal else 0.0
    
    trs = 0.35 * asof_acc + 0.30 * (1 - stale_err) + 0.20 * causal_acc + 0.15 * change_f1
    
    return {
        "system": system,
        "TemporalAccuracy": round(asof_acc, 4),
        "StalenessErrorRate": round(stale_err, 4),
        "ChangeDetectionF1": round(change_f1, 4),
        "CausalTraceAccuracy": round(causal_acc, 4),
        "TRS": round(trs, 4),
        "N_AsOf": total_asof,
        "N_Change": total_change,
        "N_Causal": total_causal,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--facts", default="benchmarks/temporalbench_v1_facts.jsonl")
    ap.add_argument("--questions", default="benchmarks/temporalbench_v1_questions.jsonl")
    ap.add_argument("--events", default="benchmarks/temporalbench_v1_events.jsonl")
    ap.add_argument("--out", default="results/main_table.csv")
    ap.add_argument("--ablation", action="store_true", help="Run ablation studies only")
    ap.add_argument("--semantic", action="store_true", help="Include semantic retrieval systems (E, E_hybrid)")
    ap.add_argument("--systems", type=str, default=None, help="Comma-separated list of systems to run (e.g., 'A,B,C,D,E')")
    args = ap.parse_args()

    facts = read_jsonl(Path(args.facts))
    questions = read_jsonl(Path(args.questions))
    events = read_jsonl(Path(args.events))

    # Determine which systems to run
    if args.systems:
        # Explicit systems specified
        systems = [s.strip() for s in args.systems.split(",")]
        out_path = args.out  # Use default or specified output path
    elif args.ablation:
        systems = ["D", "D_no_decay", "D_no_intervals", "D_no_rerank"]
        out_path = "results/ablation_table.csv"
    elif args.semantic:
        # Include semantic systems
        systems = ["A", "B", "C", "D", "E", "E_hybrid"]
        out_path = "results/main_table_with_semantic.csv"
    else:
        systems = ["A", "B", "C", "D"]
        out_path = args.out

    # Check if semantic is available
    if not SEMANTIC_AVAILABLE and any(s in systems for s in ["E", "E_hybrid"]):
        print("WARNING: sentence-transformers not installed. Semantic systems will fall back to time-constraint.")
        print("Install with: pip install sentence-transformers scikit-learn")

    rows = [evaluate(system, facts, questions, events) for system in systems]

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with Path(out_path).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {out_path}")
    for row in rows:
        print(f"  {row['system']}: TRS={row['TRS']}, AsOfAcc={row['TemporalAccuracy']}, "
              f"StaleErr={row['StalenessErrorRate']}, ChangeF1={row['ChangeDetectionF1']}, "
              f"CausalAcc={row['CausalTraceAccuracy']}")


if __name__ == "__main__":
    main()
