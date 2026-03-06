#!/usr/bin/env python3
"""Baseline benchmark harness for TemporalBench-v1 (initial implementation)."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def is_valid_as_of(fact: dict, day: int) -> bool:
    return fact["t_valid_from"] <= day and (fact["t_valid_until"] is None or day <= fact["t_valid_until"])


def retrieve_plain(facts: list[dict], domain: str, subject: str, as_of_day: int) -> str | None:
    # Baseline A: naive latest semantic match, ignores time.
    cands = [f for f in facts if f["domain"] == domain and f["content"].split(":")[1] == subject]
    if not cands:
        return None
    return max(cands, key=lambda x: x["t_valid_from"])["content"]


def retrieve_time_constraint(facts: list[dict], domain: str, subject: str, as_of_day: int) -> str | None:
    # Baseline C: explicit time filter.
    cands = [
        f for f in facts if f["domain"] == domain and f["content"].split(":")[1] == subject and is_valid_as_of(f, as_of_day)
    ]
    if not cands:
        return None
    return max(cands, key=lambda x: x["t_valid_from"])["content"]


def retrieve_tta(facts: list[dict], domain: str, subject: str, as_of_day: int) -> str | None:
    # System D: initial TTA approximation using truth interval score.
    cands = [f for f in facts if f["domain"] == domain and f["content"].split(":")[1] == subject]
    if not cands:
        return None

    def score(f: dict) -> float:
        if not is_valid_as_of(f, as_of_day):
            return -1.0
        age = max(0, as_of_day - f["t_valid_from"])
        half_life = {"slow": 45, "medium": 20, "fast": 7}[f["domain"]]
        decay = 0.5 ** (age / half_life)
        return f["confidence"] * decay

    ranked = sorted(cands, key=score, reverse=True)
    return ranked[0]["content"] if ranked and score(ranked[0]) >= 0 else None


def evaluate(system: str, facts: list[dict], questions: list[dict]) -> dict:
    if system == "A":
        resolver = retrieve_plain
    elif system in {"B", "C"}:
        # B currently proxies C for initial implementation.
        resolver = retrieve_time_constraint
    elif system == "D":
        resolver = retrieve_tta
    else:
        raise ValueError(system)

    total = len(questions)
    correct = 0
    stale = 0

    for q in questions:
        pred = resolver(facts, q["domain"], q["subject"], q["as_of_day"])
        if pred == q["answer"]:
            correct += 1
        if pred is not None:
            pred_fact = next((f for f in facts if f["content"] == pred), None)
            if pred_fact and not is_valid_as_of(pred_fact, q["as_of_day"]):
                stale += 1

    asof_acc = correct / total if total else 0.0
    stale_err = stale / total if total else 0.0
    change_f1 = 0.0  # TODO: implement once change-detection questions are generated.
    causal_acc = 0.0  # TODO: implement once ACTION/OUTCOME ground truth is added.
    trs = 0.35 * asof_acc + 0.30 * (1 - stale_err) + 0.20 * causal_acc + 0.15 * change_f1
    return {
        "system": system,
        "TemporalAccuracy": round(asof_acc, 4),
        "StalenessErrorRate": round(stale_err, 4),
        "ChangeDetectionF1": round(change_f1, 4),
        "CausalTraceAccuracy": round(causal_acc, 4),
        "TRS": round(trs, 4),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--facts", default="benchmarks/temporalbench_v1_facts.jsonl")
    ap.add_argument("--questions", default="benchmarks/temporalbench_v1_questions.jsonl")
    ap.add_argument("--out", default="results/main_table.csv")
    args = ap.parse_args()

    facts = read_jsonl(Path(args.facts))
    questions = read_jsonl(Path(args.questions))

    rows = [evaluate(system, facts, questions) for system in ["A", "B", "C", "D"]]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with Path(args.out).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
