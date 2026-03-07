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


def generate_multi_reversion_facts_and_questions(
    n_subjects: int, seed: int, n_switches: int = 4
) -> tuple[list[dict], list[dict]]:
    """Multiple reversions: A -> B -> C -> B -> D. Query at end should return D, not B or C."""
    rng = random.Random(seed)
    names = ["Alice", "Bob", "Carol", "Dave", "Eve"]
    facts = []
    questions = []
    day_max = 60
    step = day_max // (n_switches + 1)
    for i in range(n_subjects):
        subj = f"multirev_{i}"
        timeline = [names[k % len(names)] for k in range(n_switches + 1)]
        for k in range(n_switches + 1):
            t_from = 1 + k * step
            t_until = (k + 1) * step if k < n_switches else day_max
            facts.append({
                "fact_id": f"mrev_{i}_v{k}",
                "content": f"ceo:{subj}:d{t_from}:{timeline[k]}",
                "t_valid_from": t_from,
                "t_valid_until": t_until,
                "domain": "ceo",
                "confidence": 1.0,
                "decay_fn": "none",
            })
        questions.append({
            "question_id": f"mrev_q_{i}_end",
            "task_family": "MultiReversion",
            "prompt": f"As of day {day_max}, who was CEO of {subj}?",
            "as_of_day": day_max,
            "domain": "ceo",
            "subject": subj,
            "answer": f"ceo:{subj}:d{1 + n_switches * step}:{timeline[-1]}",
        })
    return facts, questions


def generate_interval_midpoint_questions(
    n_subjects: int, seed: int
) -> tuple[list[dict], list[dict]]:
    """Interval facts plus midpoint query: 'Who was CEO halfway between Bob start and end?'"""
    rng = random.Random(seed)
    facts = []
    questions = []
    for i in range(n_subjects):
        subj = f"midpoint_{i}"
        # Alice 1-20, Bob 21-40, Carol 41-60
        facts.append({"fact_id": f"mid_{i}_alice", "content": f"ceo:{subj}:d1:Alice",
            "t_valid_from": 1, "t_valid_until": 20, "domain": "ceo", "confidence": 1.0, "decay_fn": "none"})
        facts.append({"fact_id": f"mid_{i}_bob", "content": f"ceo:{subj}:d21:Bob",
            "t_valid_from": 21, "t_valid_until": 40, "domain": "ceo", "confidence": 1.0, "decay_fn": "none"})
        facts.append({"fact_id": f"mid_{i}_carol", "content": f"ceo:{subj}:d41:Carol",
            "t_valid_from": 41, "t_valid_until": 60, "domain": "ceo", "confidence": 1.0, "decay_fn": "none"})
        mid_bob = (21 + 40) // 2
        questions.append({
            "question_id": f"mid_q_{i}_bob",
            "task_family": "IntervalMidpoint",
            "prompt": f"Who was CEO of {subj} halfway between Bob's start and end date?",
            "as_of_day": mid_bob,
            "domain": "ceo",
            "subject": subj,
            "answer": f"ceo:{subj}:d21:Bob",
        })
    return facts, questions


def generate_multi_entity_join_facts_and_questions(
    n_pairs: int, seed: int
) -> tuple[list[dict], list[dict]]:
    """Two entities (e.g. Google CEO, Microsoft CEO); query aligns timelines: 'Who was Microsoft CEO when X became Google CEO?'"""
    rng = random.Random(seed)
    facts = []
    questions = []
    for i in range(n_pairs):
        # Entity A (e.g. Google): Alice 1-25, Bob 26-50
        # Entity B (e.g. Microsoft): Carol 1-30, Dave 31-60
        subj_a = f"company_a_{i}"
        subj_b = f"company_b_{i}"
        facts.append({"fact_id": f"join_{i}_a1", "content": f"ceo:{subj_a}:d1:Alice",
            "t_valid_from": 1, "t_valid_until": 25, "domain": "ceo", "confidence": 1.0, "decay_fn": "none"})
        facts.append({"fact_id": f"join_{i}_a2", "content": f"ceo:{subj_a}:d26:Bob",
            "t_valid_from": 26, "t_valid_until": 60, "domain": "ceo", "confidence": 1.0, "decay_fn": "none"})
        facts.append({"fact_id": f"join_{i}_b1", "content": f"ceo:{subj_b}:d1:Carol",
            "t_valid_from": 1, "t_valid_until": 30, "domain": "ceo", "confidence": 1.0, "decay_fn": "none"})
        facts.append({"fact_id": f"join_{i}_b2", "content": f"ceo:{subj_b}:d31:Dave",
            "t_valid_from": 31, "t_valid_until": 60, "domain": "ceo", "confidence": 1.0, "decay_fn": "none"})
        # At day 26 Bob becomes CEO of A. Who was CEO of B at that time? -> Carol (31 not yet)
        questions.append({
            "question_id": f"join_q_{i}",
            "task_family": "MultiEntityJoin",
            "prompt": f"When Bob became CEO of {subj_a} (day 26), who was CEO of {subj_b}?",
            "as_of_day": 26,
            "domain": "ceo",
            "subject": subj_b,
            "answer": f"ceo:{subj_b}:d1:Carol",
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
    ap.add_argument("--multi-reversion", type=int, default=5, help="Number of multi-reversion subjects")
    ap.add_argument("--interval-midpoint", type=int, default=5, help="Number of interval-midpoint subjects")
    ap.add_argument("--multi-entity", type=int, default=5, help="Number of multi-entity join pairs")
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

    # Multi-reversion (A->B->C->B->D)
    f4, q4 = generate_multi_reversion_facts_and_questions(args.multi_reversion, args.seed)
    for q in q4:
        q["question_id"] = f"adv_q{q_id}"
        q_id += 1
    all_facts.extend(f4)
    all_questions.extend(q4)

    # Interval midpoint
    f5, q5 = generate_interval_midpoint_questions(args.interval_midpoint, args.seed)
    for q in q5:
        q["question_id"] = f"adv_q{q_id}"
        q_id += 1
    all_facts.extend(f5)
    all_questions.extend(q5)

    # Multi-entity join
    f6, q6 = generate_multi_entity_join_facts_and_questions(args.multi_entity, args.seed)
    for q in q6:
        q["question_id"] = f"adv_q{q_id}"
        q_id += 1
    all_facts.extend(f6)
    all_questions.extend(q6)

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
