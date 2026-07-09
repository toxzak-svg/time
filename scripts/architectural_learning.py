#!/usr/bin/env python3
"""
Run architectural learning pipeline: benchmark results → diagnoser → integrator.

Learning is about *architectural efficiency* (redundancy, separation, composability),
not just bug fixes. Reads results/*.csv, produces diagnoses and recommended policy changes.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

# Add project root for src
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.diagnoser import (
    RetrievalArchitecture,
    diagnose_redundancy,
    architectural_report,
    result_to_signals,
    signals_to_diagnoses,
)
from src.integrator import integrate_diagnoses, recommended_policy_for_signals


def load_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    results_dir = ROOT / "results"
    v3 = results_dir / "v3_main_table.csv"
    v4 = results_dir / "v4_main_table.csv"
    ablation = results_dir / "ablation_table.csv"

    print("=== Architectural learning (efficiency, not just bugs) ===\n")

    # 1) Describe current retrieval architectures
    architectures = [
        RetrievalArchitecture(
            "A",
            uses_validity=False,
            uses_decay=False,
            uses_recency_in_ranking=True,
            notes="Plain RAG: latest by timestamp",
        ),
        RetrievalArchitecture(
            "B",
            uses_validity=True,
            uses_decay=False,
            uses_recency_in_ranking=True,
            notes="Temporal rerank, no decay",
        ),
        RetrievalArchitecture(
            "C",
            uses_validity=True,
            uses_decay=False,
            uses_confidence_tiebreak=True,
            validity_before_ranking=True,
            notes="Validity filter + recency tiebreak",
        ),
        RetrievalArchitecture(
            "D",
            uses_validity=True,
            uses_decay=True,
            decay_affects_ranking=True,
            notes="TTA full: validity + domain decay",
        ),
    ]
    diagnoses_arch = architectural_report(architectures)
    print("1) Architectural diagnoses (redundancy / separation / composability):")
    for d in diagnoses_arch:
        print(f"   [{d.severity}] {d.component}: {d.message}")
        print(f"   -> {d.suggestion}\n")

    # 2) Benchmark signals → diagnoses
    if v3.exists():
        main_rows = load_csv(v3)
        ablation_rows = load_csv(ablation) if ablation.exists() else None
        signals = result_to_signals(main_rows, ablation_rows, "v3")
        print("2) Benchmark signals (v3):")
        for line in signals.to_architectural_summary():
            print(f"   - {line}")
        diag_dicts = signals_to_diagnoses(signals)
        print("\n3) Diagnoses from signals:")
        for d in diag_dicts:
            print(f"   {d['component']}: {d['suggestion']}")

        # 4) Integrate: recommended architectural changes
        changes = integrate_diagnoses(diag_dicts)
        print("\n4) Integrated architectural changes:")
        for c in changes:
            print(f"   target={c.target}, type={c.change_type}")
            print(f"   {c.description}")
            print(f"   reason: {c.reason}")
            if c.policy:
                print(f"   -> use policy: validity_only_tiebreak_policy()")
    else:
        print("No v3_main_table.csv found; run benchmark first.")
        print("Example: python scripts/run_benchmark.py --facts benchmarks/temporalbench_v3_facts.jsonl ...")

    # 5) Direct policy recommendation from signals
    if v3.exists() and v4.exists():
        s3 = result_to_signals(load_csv(v3), None, "v3")
        s4 = result_to_signals(load_csv(v4), None, "v4")
        rec = recommended_policy_for_signals(
            simpler_beats_full=s3.simpler_beats_full or s4.simpler_beats_full,
            overlap_heavy=True,
            staleness_eliminated_by_validity=s3.staleness_eliminated_by_validity,
        )
        if rec:
            print("\n5) Recommended policy: validity-only + confidence/recency tiebreak (no decay).")


if __name__ == "__main__":
    main()
