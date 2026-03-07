#!/usr/bin/env python3
"""Generate adversarial temporal benchmark: reversion, interval, and causal-style questions.

Outputs facts and questions in the same JSONL schema as TemporalBench (run_benchmark.py).
Task families: Reversion, Interval, CausalReasoning.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def generate_reversion_facts_and_questions(
    n_subjects: int, seed: int
) -> tuple[list[dict], list[dict]]:
    """Timeline A -> B -> A (reversion). Query at day 45 should return A, not B."""
    rng = random.Random(seed)
    facts = []
    questions = []
    # Segment boundaries (days 1-60): A=1-20, B=21-40, A=41-60
    for i in range(n_subjects):
        subj = f"reversion_{i}"
        # First A
        facts.append({
            "fact_id": f"rev_{i}_a1",
            "content": f"ceo:{subj}:d1:Alice",
            "t_valid_from": 1,
            "t_valid_until": 20,
            "domain": "ceo",
            "confidence": 1.0,
            "decay_fn": "none",
        })
        # B
        facts.append({
            "fact_id": f"rev_{i}_b",
            "content": f"ceo:{subj}:d21:Bob",
            "t_valid_from": 21,
            "t_valid_until": 40,
            "domain": "ceo",
            "confidence": 1.0,
            "decay_fn": "none",
        })
        # Second A (reversion)
        facts.append({
            "fact_id": f"rev_{i}_a2",
            "content": f"ceo:{subj}:d41:Alice",
            "t_valid_from": 41,
            "t_valid_until": 60,
            "domain": "ceo",
            "confidence": 1.0,
            "decay_fn": "none",
        })
        # Query after reversion: day 50 -> Alice
        questions.append({
            "question_id": f"rev_q_{i}",
            "task_family": "Reversion",
            "prompt": f"As of day 50, who was CEO of {subj}?",
            "as_of_day": 50,
            "domain": "ceo",
            "subject": subj,
            "answer": f"ceo:{subj}:d41:Alice",
        })
        # Query in middle B: day 30 -> Bob
        questions.append({
            "question_id": f"rev_q_{i}_mid",
            "task_family": "Reversion",
            "prompt": f"As of day 30, who was CEO of {subj}?",
            "as_of_day": 30,
            "domain": "ceo",
            "subject": subj,
            "answer": f"ceo:{subj}:d21:Bob",
        })
    return facts, questions


def generate_interval_facts_and_questions(
    n_subjects: int, seed: int
) -> tuple[list[dict], list[dict]]:
    """Explicit validity windows. Queries at boundaries and midpoints."""
    rng = random.Random(seed)
    facts = []
    questions = []
    # Alice 1-20, Bob 21-40, Carol 41-60
    for i in range(n_subjects):
        subj = f"interval_{i}"
        facts.append({
            "fact_id": f"int_{i}_alice",
            "content": f"ceo:{subj}:d1:Alice",
            "t_valid_from": 1,
            "t_valid_until": 20,
            "domain": "ceo",
            "confidence": 1.0,
            "decay_fn": "none",
        })
        facts.append({
            "fact_id": f"int_{i}_bob",
            "content": f"ceo:{subj}:d21:Bob",
            "t_valid_from": 21,
            "t_valid_until": 40,
            "domain": "ceo",
            "confidence": 1.0,
            "decay_fn": "none",
        })
        facts.append({
            "fact_id": f"int_{i}_carol",
            "content": f"ceo:{subj}:d41:Carol",
            "t_valid_from": 41,
            "t_valid_until": 60,
            "domain": "ceo",
            "confidence": 1.0,
            "decay_fn": "none",
        })
        # Boundary and midpoint queries (inclusive: valid iff t_valid_from <= day <= t_valid_until)
        # Alice 1-20, Bob 21-40, Carol 41-60
        for day, expected_content in [
            (10, f"ceo:{subj}:d1:Alice"),   # in [1,20]
            (11, f"ceo:{subj}:d1:Alice"),   # in [1,20], not Bob
            (25, f"ceo:{subj}:d21:Bob"),   # in [21,40]
            (40, f"ceo:{subj}:d21:Bob"),   # in [21,40]
            (41, f"ceo:{subj}:d41:Carol"), # in [41,60]
            (55, f"ceo:{subj}:d41:Carol"), # in [41,60]
        ]:
            questions.append({
                "question_id": f"int_q_{i}_d{day}",
                "task_family": "Interval",
                "prompt": f"As of day {day}, who was CEO of {subj}?",
                "as_of_day": day,
                "domain": "ceo",
                "subject": subj,
                "answer": expected_content,
            })
    return facts, questions


def generate_causal_facts_and_questions(
    n_subjects: int, seed: int
) -> tuple[list[dict], list[dict]]:
    """Ordered timeline; questions are 'before X', 'after Y' style (as-of past)."""
    rng = random.Random(seed)
    facts = []
    questions = []
    # Simple timeline: Alice 1-15, Bob 16-35, Carol 36-60
    for i in range(n_subjects):
        subj = f"causal_{i}"
        facts.append({
            "fact_id": f"caus_{i}_alice",
            "content": f"ceo:{subj}:d1:Alice",
            "t_valid_from": 1,
            "t_valid_until": 15,
            "domain": "ceo",
            "confidence": 1.0,
            "decay_fn": "none",
        })
        facts.append({
            "fact_id": f"caus_{i}_bob",
            "content": f"ceo:{subj}:d16:Bob",
            "t_valid_from": 16,
            "t_valid_until": 35,
            "domain": "ceo",
            "confidence": 1.0,
            "decay_fn": "none",
        })
        facts.append({
            "fact_id": f"caus_{i}_carol",
            "content": f"ceo:{subj}:d36:Carol",
            "t_valid_from": 36,
            "t_valid_until": 60,
            "domain": "ceo",
            "confidence": 1.0,
            "decay_fn": "none",
        })
        # "Who was CEO before Bob?" -> query at day 10, answer Alice
        questions.append({
            "question_id": f"caus_q_{i}_before_bob",
            "task_family": "CausalReasoning",
            "prompt": f"Who was CEO of {subj} before Bob took over? (as of day 10)",
            "as_of_day": 10,
            "domain": "ceo",
            "subject": subj,
            "answer": f"ceo:{subj}:d1:Alice",
        })
        # "Who was CEO after Alice?" at day 20 -> Bob
        questions.append({
            "question_id": f"caus_q_{i}_after_alice",
            "task_family": "CausalReasoning",
            "prompt": f"Who was CEO of {subj} after Alice? (as of day 20)",
            "as_of_day": 20,
            "domain": "ceo",
            "subject": subj,
            "answer": f"ceo:{subj}:d16:Bob",
        })
        # "Who was CEO between Alice and Carol?" at day 25 -> Bob
        questions.append({
            "question_id": f"caus_q_{i}_between",
            "task_family": "CausalReasoning",
            "prompt": f"Who was CEO of {subj} between Alice and Carol? (as of day 25)",
            "as_of_day": 25,
            "domain": "ceo",
            "subject": subj,
            "answer": f"ceo:{subj}:d16:Bob",
        })
    return facts, questions


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate adversarial temporal benchmark data.")
    ap.add_argument("--out-dir", type=Path, default=Path("benchmarks"), help="Output directory")
    ap.add_argument("--reversion", type=int, default=15, help="Number of reversion subjects")
    ap.add_argument("--interval", type=int, default=10, help="Number of interval subjects")
    ap.add_argument("--causal", type=int, default=10, help="Number of causal subjects")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    all_facts = []
    all_questions = []
    q_id = 0

    # Reversion
    f1, q1 = generate_reversion_facts_and_questions(args.reversion, args.seed)
    for q in q1:
        q["question_id"] = f"adv_q{q_id}"
        q_id += 1
    all_facts.extend(f1)
    all_questions.extend(q1)

    # Interval
    f2, q2 = generate_interval_facts_and_questions(args.interval, args.seed)
    for q in q2:
        q["question_id"] = f"adv_q{q_id}"
        q_id += 1
    all_facts.extend(f2)
    all_questions.extend(q2)

    # Causal
    f3, q3 = generate_causal_facts_and_questions(args.causal, args.seed)
    for q in q3:
        q["question_id"] = f"adv_q{q_id}"
        q_id += 1
    all_facts.extend(f3)
    all_questions.extend(q3)

    facts_path = args.out_dir / "adversarial_temporal_facts.jsonl"
    questions_path = args.out_dir / "adversarial_temporal_questions.jsonl"
    with facts_path.open("w", encoding="utf-8") as f:
        for rec in all_facts:
            f.write(json.dumps(rec) + "\n")
    with questions_path.open("w", encoding="utf-8") as f:
        for rec in all_questions:
            f.write(json.dumps(rec) + "\n")

    print(f"Wrote {len(all_facts)} facts -> {facts_path}")
    print(f"Wrote {len(all_questions)} questions -> {questions_path}")
    by_family = {}
    for q in all_questions:
        by_family[q["task_family"]] = by_family.get(q["task_family"], 0) + 1
    for k, v in sorted(by_family.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
