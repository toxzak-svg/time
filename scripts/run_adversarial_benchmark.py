#!/usr/bin/env python3
"""Run adversarial temporal benchmark: metrics by task type (Reversion, Interval, CausalReasoning).

Uses same retrieval systems as run_benchmark.py. Reads adversarial_temporal_*.jsonl.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# Allow importing run_benchmark from same directory
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_benchmark as rb


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        return [__import__("json").loads(line) for line in fh if line.strip()]


def evaluate_system(
    system: str,
    facts: list[dict],
    questions: list[dict],
) -> dict:
    """Evaluate one system; break down by adversarial task_family."""
    resolvers = {
        "A": rb.retrieve_plain,
        "B": rb.retrieve_temporal_rerank,
        "C": rb.retrieve_time_constraint,
        "D": rb.retrieve_tta,
        "D_improved": rb.retrieve_tta_improved,
        "D_revised": rb.retrieve_tta_improved,  # Validity-only + confidence tiebreak (no decay)
    }
    resolver = resolvers.get(system)
    if not resolver:
        raise ValueError(f"Unknown system: {system}")

    by_family: dict[str, list[dict]] = {}
    for q in questions:
        fam = q.get("task_family", "Other")
        by_family.setdefault(fam, []).append(q)

    out = {"system": system}
    correct_by_family = {}
    n_by_family = {}

    for fam, qs in by_family.items():
        correct = 0
        for q in qs:
            pred = resolver(
                facts,
                q["domain"],
                q["subject"],
                q["as_of_day"],
            )
            if q.get("answer") is None:
                correct += 1 if pred is None else 0
            elif pred == q["answer"]:
                correct += 1
        correct_by_family[fam] = correct
        n_by_family[fam] = len(qs)
        acc = correct / len(qs) if qs else 0.0
        out[f"{fam}Accuracy"] = round(acc, 4)
        out[f"N_{fam}"] = len(qs)

    total_q = len(questions)
    total_correct = sum(correct_by_family.values())
    out["OverallAccuracy"] = round(total_correct / total_q, 4) if total_q else 0.0
    out["N_total"] = total_q
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Run adversarial temporal benchmark by task type.")
    ap.add_argument(
        "--facts",
        type=Path,
        default=Path("benchmarks/adversarial_temporal_facts.jsonl"),
        help="Facts JSONL",
    )
    ap.add_argument(
        "--questions",
        type=Path,
        default=Path("benchmarks/adversarial_temporal_questions.jsonl"),
        help="Questions JSONL",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("results/adversarial_temporal_results.csv"),
        help="Output CSV",
    )
    ap.add_argument(
        "--systems",
        type=str,
        default="A,B,C,D,D_revised",
        help="Comma-separated systems (e.g. A,B,C,D,D_revised)",
    )
    args = ap.parse_args()

    facts = read_jsonl(args.facts)
    questions = read_jsonl(args.questions)
    if not facts or not questions:
        print("No facts or questions found. Run scripts/generate_adversarial_temporal.py first.")
        sys.exit(1)

    systems = [s.strip() for s in args.systems.split(",")]
    rows = [evaluate_system(s, facts, questions) for s in systems]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {args.out}")
    for r in rows:
        parts = [f"{k}={r[k]}" for k in fieldnames if k != "system" and not k.startswith("N_")]
        print(f"  {r['system']}: " + ", ".join(parts))


if __name__ == "__main__":
    main()
