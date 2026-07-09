#!/usr/bin/env python3
"""Minimal benchmark harness for TemporalBench-v1.

This initial implementation evaluates lightweight heuristic agents to establish
an end-to-end benchmark flow before integrating full LLM-backed systems.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Dict, List, Tuple


def load_records(path: Path) -> Tuple[List[dict], List[dict], List[dict]]:
    events, facts, questions = [], [], []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            rtype = rec.get("record_type")
            if rtype == "event":
                events.append(rec)
            elif rtype == "fact":
                facts.append(rec)
            elif rtype == "question":
                questions.append(rec)
    return events, facts, questions


def index_facts(facts: List[dict]) -> Dict[str, List[dict]]:
    by_subject = defaultdict(list)
    for fact in facts:
        by_subject[fact["content"].split("=", 1)[0]].append(fact)
    for subject in by_subject:
        by_subject[subject].sort(key=lambda x: (x["t_valid_from"], x["t_valid_until"]))
    return by_subject


def fact_at_time(subject_facts: List[dict], t: int):
    for fact in subject_facts:
        if fact["t_valid_from"] <= t <= fact["t_valid_until"]:
            return fact
    return None


def answer_baseline_a(question: dict, by_subject: Dict[str, List[dict]]) -> str:
    # Plain RAG proxy: choose the highest-confidence fact regardless of query time.
    facts = by_subject.get(question["subject"], [])
    if not facts:
        return "UNKNOWN"
    top = max(facts, key=lambda f: f["confidence"])
    return top["content"].split("=", 1)[1]


def answer_baseline_c(question: dict, by_subject: Dict[str, List[dict]]) -> str:
    # Time-constrained retrieval proxy: select fact active at query time.
    facts = by_subject.get(question["subject"], [])
    anchor = question.get("time_anchor") or question.get("time_window", [None, None])[1]
    if anchor is None:
        return "UNKNOWN"
    hit = fact_at_time(facts, int(anchor))
    if not hit:
        return "UNKNOWN"
    return hit["content"].split("=", 1)[1]


def answer_tta(question: dict, by_subject: Dict[str, List[dict]]) -> str:
    # TTA core proxy: time-constrained with domain decay penalty for stale candidate ranking.
    facts = by_subject.get(question["subject"], [])
    anchor = question.get("time_anchor") or question.get("time_window", [None, None])[1]
    if anchor is None or not facts:
        return "UNKNOWN"

    best = None
    best_score = float("-inf")
    for fact in facts:
        center_age = max(0, int(anchor) - fact["t_valid_from"])
        half_life = float(str(fact["decay_fn"]).split("_")[-1])
        decay = 0.5 ** (center_age / max(half_life, 0.1))
        active_bonus = 1.0 if fact["t_valid_from"] <= int(anchor) <= fact["t_valid_until"] else 0.0
        score = float(fact["confidence"]) * decay + active_bonus
        if score > best_score:
            best = fact
            best_score = score

    return best["content"].split("=", 1)[1] if best else "UNKNOWN"


def evaluate(questions: List[dict], by_subject: Dict[str, List[dict]], agent_name: str):
    answer_fn = {
        "baseline_a": answer_baseline_a,
        "baseline_c": answer_baseline_c,
        "tta": answer_tta,
    }[agent_name]

    temporal_correct = []
    stale_error = []
    for q in questions:
        if q["family"] not in {"as_of_time", "staleness_resistance"}:
            continue
        pred = answer_fn(q, by_subject)
        correct = pred == q["gold_answer"]
        temporal_correct.append(1.0 if correct else 0.0)
        stale_error.append(0.0 if correct else 1.0)

    asof_acc = mean(temporal_correct) if temporal_correct else 0.0
    stale_err = mean(stale_error) if stale_error else 1.0
    trs = 0.35 * asof_acc + 0.30 * (1.0 - stale_err)
    return {
        "system": agent_name,
        "asof_accuracy": round(asof_acc, 4),
        "staleness_error_rate": round(stale_err, 4),
        "trs_partial": round(trs, 4),
        "samples": len(temporal_correct),
    }


def write_results(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run minimal TemporalBench benchmark")
    parser.add_argument("--input", type=Path, default=Path("benchmarks/temporalbench_v1.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("results/main_table.csv"))
    args = parser.parse_args()

    _, facts, questions = load_records(args.input)
    by_subject = index_facts(facts)

    rows = [evaluate(questions, by_subject, name) for name in ["baseline_a", "baseline_c", "tta"]]
    write_results(args.output, rows)
    print(f"Wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
