#!/usr/bin/env python3
"""Generate accuracy vs fact age figure for TemporalBench-v1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def is_valid_as_of(fact: dict, day: int) -> bool:
    return fact["t_valid_from"] <= day and (fact["t_valid_until"] is None or day <= fact["t_valid_until"])


def get_subject(content: str) -> str:
    return content.split(":")[1]


def retrieve_plain(facts, domain, subject, as_of_day):
    cands = [f for f in facts if f["domain"] == domain and get_subject(f["content"]) == subject]
    if not cands:
        return None
    return max(cands, key=lambda x: x["t_valid_from"])["content"]


def retrieve_temporal_rerank(facts, domain, subject, as_of_day):
    cands = [f for f in facts if f["domain"] == domain and get_subject(f["content"]) == subject]
    if not cands:
        return None

    def score(f):
        if not is_valid_as_of(f, as_of_day):
            return -1.0
        recency = 1.0 / (1.0 + (as_of_day - f["t_valid_from"]) * 0.1)
        return f["confidence"] * recency

    ranked = sorted(cands, key=score, reverse=True)
    return ranked[0]["content"] if ranked and score(ranked[0]) >= 0 else None


def retrieve_time_constraint(facts, domain, subject, as_of_day):
    cands = [
        f for f in facts 
        if f["domain"] == domain and get_subject(f["content"]) == subject and is_valid_as_of(f, as_of_day)
    ]
    if not cands:
        return None
    return max(cands, key=lambda x: x["t_valid_from"])["content"]


def retrieve_tta(facts, domain, subject, as_of_day):
    cands = [f for f in facts if f["domain"] == domain and get_subject(f["content"]) == subject]
    if not cands:
        return None

    half_life = {"slow": 45, "medium": 20, "fast": 7}

    def score(f):
        if not is_valid_as_of(f, as_of_day):
            return -1.0
        age = max(0, as_of_day - f["t_valid_from"])
        decay = 0.5 ** (age / half_life.get(f["domain"], 20))
        return f["confidence"] * decay

    ranked = sorted(cands, key=score, reverse=True)
    return ranked[0]["content"] if ranked and score(ranked[0]) >= 0 else None


def compute_accuracy_by_age(facts, questions, resolver, max_age=60):
    """Compute accuracy by fact age buckets."""
    # Group questions by fact age
    age_buckets = {}
    for q in questions:
        if q.get("task_family") != "AsOfQA":
            continue
        as_of_day = q["as_of_day"]
        # Find the fact that is the answer
        answer_fact = next((f for f in facts if f["content"] == q["answer"]), None)
        if not answer_fact:
            continue
        age = as_of_day - answer_fact["t_valid_from"]
        if age < 0:
            continue
        bucket = min(age // 10 * 10, max_age)  # 10-day buckets
        if bucket not in age_buckets:
            age_buckets[bucket] = {"correct": 0, "total": 0}
        
        pred = resolver(facts, q["domain"], q["subject"], as_of_day)
        age_buckets[bucket]["total"] += 1
        if pred == q["answer"]:
            age_buckets[bucket]["correct"] += 1
    
    # Compute accuracy per bucket
    ages = sorted(age_buckets.keys())
    accuracies = []
    for age in ages:
        acc = age_buckets[age]["correct"] / age_buckets[age]["total"] if age_buckets[age]["total"] > 0 else 0
        accuracies.append(acc)
    
    return ages, accuracies


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--facts", default="benchmarks/temporalbench_v1_facts.jsonl")
    parser.add_argument("--questions", default="benchmarks/temporalbench_v1_questions.jsonl")
    parser.add_argument("--out", default="figures/accuracy_vs_fact_age.png")
    args = parser.parse_args()

    facts = read_jsonl(Path(args.facts))
    questions = read_jsonl(Path(args.questions))

    systems = {
        "A (Plain RAG)": retrieve_plain,
        "B (Temporal Rerank)": retrieve_temporal_rerank,
        "C (Time Filter)": retrieve_time_constraint,
        "D (TTA)": retrieve_tta,
    }

    plt.figure(figsize=(10, 6))
    colors = ["#e74c3c", "#3498db", "#2ecc71", "#9b59b6"]
    markers = ["o", "s", "^", "D"]

    for idx, (name, resolver) in enumerate(systems.items()):
        ages, accuracies = compute_accuracy_by_age(facts, questions, resolver)
        if ages:
            plt.plot(ages, accuracies, label=name, color=colors[idx], marker=markers[idx], linewidth=2, markersize=8)

    plt.xlabel("Fact Age (days)", fontsize=12)
    plt.ylabel("Answer Accuracy", fontsize=12)
    plt.title("Temporal Accuracy vs Fact Age", fontsize=14)
    plt.legend(loc="best", fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.ylim(0, 1.05)
    plt.xlim(-2, 62)

    # Add bucket labels
    plt.xticks([0, 10, 20, 30, 40, 50, 60], ["0-10", "10-20", "20-30", "30-40", "40-50", "50-60", "60+"])

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(args.out, dpi=150, bbox_inches="tight")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
