#!/usr/bin/env python3
"""
Phase 2 Per-Question Correlation Analysis for TemporalBench.

Runs per-question predictions for all systems (A, B, C, D, D_revised),
extracts per-question features, computes feature-accuracy correlations,
and validates the Phase 1 hypothesis:
  System A's failures are predicted by temporal distance (recency).

Outputs:
  results/per_question_predictions.csv   - per-question predictions + correctness
  results/per_question_features.csv      - per-question feature vectors
  results/per_question_correlation.csv    - correlation analysis results
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

# ── Retrieval functions (copied from run_benchmark.py) ──────────────────────

def get_subject(content: str) -> str:
    parts = content.split(":")
    return parts[1] if len(parts) >= 2 else ""


def is_valid_as_of(fact: dict, day: int) -> bool:
    return fact["t_valid_from"] <= day and (fact["t_valid_until"] is None or day <= fact["t_valid_until"])


def retrieve_plain(facts: list[dict], domain: str, subject: str, as_of_day: int, **kwargs) -> Optional[str]:
    """Baseline A: naive latest semantic match, ignores time."""
    cands = [f for f in facts if f["domain"] == domain and get_subject(f["content"]) == subject]
    if not cands:
        return None
    return max(cands, key=lambda x: x["t_valid_from"])["content"]


def retrieve_temporal_rerank(facts: list[dict], domain: str, subject: str, as_of_day: int, **kwargs) -> Optional[str]:
    """Baseline B: temporal-aware retrieval with reranking."""
    cands = [f for f in facts if f["domain"] == domain and get_subject(f["content"]) == subject]
    if not cands:
        return None

    def score(f: dict) -> float:
        if not is_valid_as_of(f, as_of_day):
            return -1.0
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
    """Baseline D: full TTA with truth intervals and domain-adaptive decay."""
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
    """D_revised: Validity-only + confidence tiebreaker (no decay)."""
    cands = [f for f in facts if f["domain"] == domain and get_subject(f["content"]) == subject]
    if not cands:
        return None
    valid_cands = [f for f in cands if is_valid_as_of(f, as_of_day)]
    if not valid_cands:
        return None
    return max(valid_cands, key=lambda x: (x["t_valid_from"], x["confidence"]))["content"]


RESOLVERS = {
    "A": retrieve_plain,
    "B": retrieve_temporal_rerank,
    "C": retrieve_time_constraint,
    "D": retrieve_tta,
    "D_revised": retrieve_tta_improved,
}

SYSTEMS = ["A", "B", "C", "D", "D_revised"]


# ── JSONL reader ────────────────────────────────────────────────────────────

def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


# ── Phase 1: Per-Question Predictions ───────────────────────────────────────

def run_per_question_predictions(facts_path: Path, questions_path: Path,
                                 version: str, seed: int,
                                 systems: list[str] = None) -> list[dict]:
    """Run every system on every question, return per-question results."""
    if systems is None:
        systems = SYSTEMS

    facts = read_jsonl(facts_path)
    questions = read_jsonl(questions_path)

    # Build fact lookup by content
    fact_by_content = {f["content"]: f for f in facts}

    # Filter to temporal/AsOf questions only (exclude ChangeDetection, CausalQuery)
    temporal_task_families = {
        "AsOfQA", "StalenessTrap", "EdgeCase", "SimpleRecency",
        "PastQueryTrap", "CurrentQuery", "DecayTrap", "OverlapTrap", "OverlapQuery",
    }
    temporal_questions = [q for q in questions if q.get("task_family") in temporal_task_families]

    rows = []
    for q in temporal_questions:
        resolver_args = {"facts": facts, "domain": q["domain"],
                         "subject": q["subject"], "as_of_day": q["as_of_day"]}

        for sys_name in systems:
            resolver = RESOLVERS[sys_name]
            predicted = resolver(**resolver_args)
            expected = q.get("answer")

            correct = (predicted == expected) if expected is not None else (predicted is None)

            # Staleness error: predicted fact is NOT valid at query time
            staleness_error = False
            if predicted is not None:
                pred_fact = fact_by_content.get(predicted)
                if pred_fact is not None:
                    staleness_error = not is_valid_as_of(pred_fact, q["as_of_day"])

            rows.append({
                "question_id": q["question_id"],
                "system": sys_name,
                "version": version,
                "seed": seed,
                "correct": correct,
                "predicted": predicted if predicted else "",
                "expected": expected if expected else "",
                "staleness_error": staleness_error,
                # Mirror features from question for convenience
                "task_family": q.get("task_family", ""),
                "domain": q.get("domain", ""),
                "subject": q.get("subject", ""),
                "as_of_day": q.get("as_of_day", 0),
            })

    return rows


# ── Phase 2: Per-Question Feature Extraction ─────────────────────────────────

def compute_question_features(questions_path: Path, facts_path: Path) -> dict[str, dict]:
    """
    Compute feature vector for each question_id.
    Returns dict: question_id -> {feature_name: value}
    """
    questions = read_jsonl(questions_path)
    facts = read_jsonl(facts_path)

    # max day across all facts (proxy for "now")
    max_day = max(f["t_valid_from"] for f in facts)
    min_day = min(f["t_valid_from"] for f in facts)

    # Build subject -> [facts] index
    subject_to_facts = defaultdict(list)
    for f in facts:
        subject_to_facts[get_subject(f["content"])].append(f)

    # Build domain -> set of subjects index
    domain_to_subjects = defaultdict(set)
    for f in facts:
        domain_to_subjects[f["domain"]].add(get_subject(f["content"]))

    # Domain sizes
    domain_sizes = {d: len(subjects) for d, subjects in domain_to_subjects.items()}

    features = {}
    for q in questions:
        qid = q["question_id"]
        subject = q.get("subject", "")
        domain = q.get("domain", "")
        as_of_day = q.get("as_of_day", 0)

        subject_facts = subject_to_facts.get(subject, [])
        domain_size = domain_sizes.get(domain, 1)

        # temporal_distance: days between query time and max fact day
        temporal_distance = max_day - as_of_day

        # recency_score: 1.0 = query is at max_day (most recent), 0.0 = at min_day
        day_range = max_day - min_day if max_day > min_day else 1
        recency_score = 1.0 - (as_of_day - min_day) / day_range
        recency_score = max(0.0, min(1.0, recency_score))

        # subject_fact_count
        subject_fact_count = len(subject_facts)

        # overlap_count: how many other subjects share the same domain
        overlap_count = domain_size - 1  # exclude this subject

        # subject_fact_density: fact_count / domain_size
        subject_fact_density = subject_fact_count / domain_size if domain_size > 0 else 0.0

        features[qid] = {
            "question_id": qid,
            "temporal_distance": temporal_distance,
            "recency_score": recency_score,
            "subject_fact_count": subject_fact_count,
            "overlap_count": overlap_count,
            "subject_fact_density": subject_fact_density,
            "domain": domain,
            "task_family": q.get("task_family", ""),
            "as_of_day": as_of_day,
            "subject": subject,
        }

    return features


# ── Phase 3: Correlation Analysis ───────────────────────────────────────────

def pearson_corr(xs: list[float], ys: list[float]) -> float:
    """Compute Pearson correlation coefficient between two lists."""
    n = len(xs)
    if n < 2:
        return float("nan")

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))

    if den_x == 0 or den_y == 0:
        return float("nan")
    return num / (den_x * den_y)


def run_correlation_analysis(predictions: list[dict], features: dict[str, dict],
                             systems: list[str] = None) -> list[dict]:
    """
    For each system compute:
      - Pearson corr: temporal_distance vs per-question accuracy
      - Stratified accuracy: near (recency > 0.8) vs far (recency < 0.2)
      - Mean accuracy by task_family
      - Mean accuracy by domain
    """
    if systems is None:
        systems = SYSTEMS

    # Index predictions by (question_id, system)
    pred_index: dict[tuple, dict] = {}
    for p in predictions:
        pred_index[(p["question_id"], p["system"])] = p

    # Collect question_ids that appear in predictions
    qids = sorted(set(p["question_id"] for p in predictions))

    rows = []
    for sys_name in systems:
        # Per-question accuracy for this system
        td_vals = []   # temporal distances
        acc_vals = []  # binary accuracy (1/0)
        near_correct = 0; near_total = 0
        far_correct = 0; far_total = 0
        task_acc = defaultdict(lambda: [0, 0])  # task_family -> [correct, total]
        domain_acc = defaultdict(lambda: [0, 0]) # domain -> [correct, total]

        for qid in qids:
            feat = features.get(qid)
            if feat is None:
                continue
            pred = pred_index.get((qid, sys_name))
            if pred is None:
                continue

            correct = 1 if pred["correct"] else 0
            td = feat["temporal_distance"]
            recency = feat["recency_score"]

            td_vals.append(td)
            acc_vals.append(correct)

            if recency > 0.8:
                near_total += 1
                near_correct += correct
            elif recency < 0.2:
                far_total += 1
                far_correct += correct

            tf = feat["task_family"]
            task_acc[tf][0] += correct
            task_acc[tf][1] += 1

            dom = feat["domain"]
            domain_acc[dom][0] += correct
            domain_acc[dom][1] += 1

        # Pearson correlation
        corr = pearson_corr(td_vals, acc_vals) if len(td_vals) >= 2 else float("nan")

        near_acc = near_correct / near_total if near_total > 0 else float("nan")
        far_acc = far_correct / far_total if far_total > 0 else float("nan")

        current_acc = _mean_acc(task_acc, "CurrentQuery")
        past_acc    = _mean_acc(task_acc, "PastQueryTrap")
        overlap_acc = _mean_acc(task_acc, "OverlapQuery")
        fast_acc    = _mean_acc(domain_acc, "fast")
        slow_acc    = _mean_acc(domain_acc, "slow")

        rows.append({
            "system": sys_name,
            "temporal_distance_corr": round(corr, 4) if not math.isnan(corr) else float("nan"),
            "near_accuracy": round(near_acc, 4) if not math.isnan(near_acc) else float("nan"),
            "far_accuracy": round(far_acc, 4) if not math.isnan(far_acc) else float("nan"),
            "current_accuracy": round(current_acc, 4) if not math.isnan(current_acc) else float("nan"),
            "past_accuracy": round(past_acc, 4) if not math.isnan(past_acc) else float("nan"),
            "overlap_accuracy": round(overlap_acc, 4) if not math.isnan(overlap_acc) else float("nan"),
            "fast_accuracy": round(fast_acc, 4) if not math.isnan(fast_acc) else float("nan"),
            "slow_accuracy": round(slow_acc, 4) if not math.isnan(slow_acc) else float("nan"),
            "n_questions": len(td_vals),
        })

    return rows


def _mean_acc(counter: dict, key: str) -> float:
    c, t = counter.get(key, (0, 0))
    return c / t if t > 0 else float("nan")


# ── Main orchestration ───────────────────────────────────────────────────────

VERSIONS = ["v1", "v2", "v3", "v4"]
SEEDS    = [0, 1, 2]

BENCHMARK_BASE = Path("C:/Users/Zwmar/dev/time/benchmarks")
RESULTS_DIR    = Path("C:/Users/Zwmar/dev/time/results")


def main():
    ap = argparse.ArgumentParser(description="Phase 2 TemporalBench correlation analysis")
    ap.add_argument("--versions", type=str, default="v1,v2,v3,v4",
                    help="Comma-separated versions to process")
    ap.add_argument("--seeds", type=str, default="0,1,2",
                    help="Comma-separated seeds to process")
    ap.add_argument("--systems", type=str, default="A,B,C,D,D_revised",
                    help="Comma-separated systems to evaluate")
    args = ap.parse_args()

    versions = [v.strip() for v in args.versions.split(",")]
    seeds    = [int(s.strip()) for s in args.seeds.split(",")]
    systems  = [s.strip() for s in args.systems.split(",")]

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Collect all predictions across all version/seed combos ──
    all_predictions: list[dict] = []

    for version in versions:
        for seed in seeds:
            facts_path    = BENCHMARK_BASE / f"temporalbench_{version}_facts.jsonl"
            questions_path = BENCHMARK_BASE / f"temporalbench_{version}_questions.jsonl"

            if not facts_path.exists() or not questions_path.exists():
                print(f"SKIP: {version}_seed{seed} data not found", file=sys.stderr)
                continue

            print(f"  Running predictions: {version}_seed{seed}")
            preds = run_per_question_predictions(
                facts_path, questions_path, version, seed, systems=systems
            )
            all_predictions.extend(preds)

    # ── Write per-question predictions ──
    pred_out = RESULTS_DIR / "per_question_predictions.csv"
    if all_predictions:
        fieldnames = list(all_predictions[0].keys())
        with pred_out.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_predictions)
        print(f"\nWrote {pred_out}  ({len(all_predictions)} rows)")

    # ── Feature extraction (one per version; features are static across seeds) ──
    all_features: dict[str, dict] = {}  # qid -> feature dict (merged across versions)

    for version in versions:
        facts_path    = BENCHMARK_BASE / f"temporalbench_{version}_facts.jsonl"
        questions_path = BENCHMARK_BASE / f"temporalbench_{version}_questions.jsonl"
        if not facts_path.exists():
            continue

        feat = compute_question_features(questions_path, facts_path)
        # Prefix question_ids with version to avoid collisions
        for qid, f in feat.items():
            all_features[f"{version}:{qid}"] = f

    # Merge predictions with features using version prefix
    for p in all_predictions:
        p["question_id"] = f"{p['version']}:{p['question_id']}"

    # ── Write per-question features ──
    feat_out = RESULTS_DIR / "per_question_features.csv"
    if all_features:
        fieldnames = list(next(iter(all_features.values())).keys())
        with feat_out.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for f in sorted(all_features.values(), key=lambda x: x["question_id"]):
                writer.writerow(f)
        print(f"Wrote {feat_out}  ({len(all_features)} questions)")

    # ── Correlation analysis ──
    corr_rows = run_correlation_analysis(all_predictions, all_features, systems=systems)

    corr_out = RESULTS_DIR / "per_question_correlation.csv"
    if corr_rows:
        fieldnames = list(corr_rows[0].keys())
        with corr_out.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(corr_rows)
        print(f"Wrote {corr_out}")

    # ── Print summary ──
    print("\n=== Correlation Summary ===")
    header = f"{'system':<12} {'td_corr':>10} {'near_acc':>10} {'far_acc':>10} {'current':>10} {'past':>10} {'overlap':>10} {'fast':>10} {'slow':>10}"
    print(header)
    print("-" * len(header))
    for row in corr_rows:
        print(
            f"{row['system']:<12} "
            f"{row['temporal_distance_corr']:>10.4f} "
            f"{row['near_accuracy']:>10.4f} "
            f"{row['far_accuracy']:>10.4f} "
            f"{row['current_accuracy']:>10.4f} "
            f"{row['past_accuracy']:>10.4f} "
            f"{row['overlap_accuracy']:>10.4f} "
            f"{row['fast_accuracy']:>10.4f} "
            f"{row['slow_accuracy']:>10.4f}"
        )


if __name__ == "__main__":
    main()
