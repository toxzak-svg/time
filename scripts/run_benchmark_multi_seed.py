#!/usr/bin/env python3
"""Run benchmark with multiple seeds; aggregate mean ± std per metric."""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

# Import harness components (run from repo root: python scripts/run_benchmark_multi_seed.py)
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from scripts.run_benchmark import read_jsonl, evaluate

BENCHMARKS_DIR = Path(__file__).resolve().parent.parent / "benchmarks"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
SCRIPTS_DIR = Path(__file__).resolve().parent

GENERATORS = {
    "v1": [sys.executable, str(SCRIPTS_DIR / "generate_temporalbench_v1.py")],
    "v2": [sys.executable, str(SCRIPTS_DIR / "generate_temporalbench_v2.py")],
    "v3": [sys.executable, str(SCRIPTS_DIR / "generate_temporalbench_v3.py")],
    "v4": [sys.executable, str(SCRIPTS_DIR / "generate_temporalbench_v4.py")],
}

SYSTEMS = ["A", "B", "C", "D", "D_revised"]
NUMERIC_KEYS = ["TemporalAccuracy", "StalenessErrorRate", "ChangeDetectionF1", "CausalTraceAccuracy", "TRS"]


def generate_version_seed(version: str, seed: int) -> Path:
    """Generate benchmark data for a version and seed; return dir with facts/questions/events."""
    out_dir = BENCHMARKS_DIR / f"{version}_seed{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)
    events_out = out_dir / "events.jsonl"
    facts_out = out_dir / "facts.jsonl"
    questions_out = out_dir / "questions.jsonl"

    cmd = GENERATORS[version] + [
        "--seed", str(seed),
        "--events-out", str(events_out),
        "--facts-out", str(facts_out),
        "--questions-out", str(questions_out),
    ]
    subprocess.run(cmd, check=True, cwd=Path(__file__).resolve().parent.parent)
    return out_dir


def run_one(version: str, seed: int, systems: list[str], out_dir: Path) -> list[dict]:
    """Run evaluation for one (version, seed); return list of result rows."""
    facts = read_jsonl(out_dir / "facts.jsonl")
    questions = read_jsonl(out_dir / "questions.jsonl")
    events = read_jsonl(out_dir / "events.jsonl")
    rows = []
    for system in systems:
        row = evaluate(system, facts, questions, events)
        row["version"] = version
        row["seed"] = seed
        rows.append(row)
    return rows


def aggregate(per_seed_rows: list[dict]) -> list[dict]:
    """Aggregate per-seed rows into mean ± std per (version, system)."""
    import numpy as np
    by_key = {}
    for row in per_seed_rows:
        key = (row["version"], row["system"])
        if key not in by_key:
            by_key[key] = []
        by_key[key].append(row)

    out = []
    for (version, system), group in sorted(by_key.items()):
        agg_row = {"version": version, "system": system}
        for k in NUMERIC_KEYS:
            vals = [r[k] for r in group]
            mean_val = float(np.mean(vals))
            std_val = float(np.std(vals)) if len(vals) > 1 else 0.0
            agg_row[k] = mean_val
            agg_row[f"{k}_std"] = std_val
        # Keep first row's N_* and system label
        agg_row["N_AsOf"] = group[0]["N_AsOf"]
        agg_row["N_Change"] = group[0]["N_Change"]
        agg_row["N_Causal"] = group[0]["N_Causal"]
        out.append(agg_row)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Run benchmark with multiple seeds; report mean ± std")
    ap.add_argument("--seeds", type=str, default="0,1,2", help="Comma-separated seeds (e.g. 0,1,2)")
    ap.add_argument("--versions", type=str, default="v1,v2,v3,v4", help="Comma-separated versions")
    ap.add_argument("--systems", type=str, default=None, help="Comma-separated systems (default: A,B,C,D,D_revised)")
    ap.add_argument("--out-csv", default="results/per_seed_results.csv", help="Per-seed results CSV")
    ap.add_argument("--out-aggregated", default="results/main_table_multi_seed.csv", help="Aggregated mean ± std CSV")
    ap.add_argument("--skip-generate", action="store_true", help="Skip generation; use existing benchmark dirs")
    args = ap.parse_args()

    seeds = [int(s.strip()) for s in args.seeds.split(",")]
    versions = [v.strip() for v in args.versions.split(",")]
    for v in versions:
        if v not in GENERATORS:
            raise SystemExit(f"Unknown version: {v}")
    systems = [s.strip() for s in (args.systems or "A,B,C,D,D_revised").split(",")]

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)

    all_rows = []
    for version in versions:
        for seed in seeds:
            out_dir = BENCHMARKS_DIR / f"{version}_seed{seed}"
            if not args.skip_generate:
                print(f"Generating {version} seed={seed}...")
                generate_version_seed(version, seed)
            if not (out_dir / "facts.jsonl").exists():
                raise SystemExit(f"Missing {out_dir / 'facts.jsonl'}; run without --skip-generate first")
            print(f"Evaluating {version} seed={seed}...")
            rows = run_one(version, seed, systems, out_dir)
            all_rows.extend(rows)

    # Write per-seed results
    if all_rows:
        fieldnames = list(all_rows[0].keys())
        with open(RESULTS_DIR / Path(args.out_csv).name, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(all_rows)
        print(f"Wrote {args.out_csv} ({len(all_rows)} rows)")

    # Aggregate and write
    agg_rows = aggregate(all_rows)
    agg_fieldnames = ["version", "system"] + NUMERIC_KEYS + [f"{k}_std" for k in NUMERIC_KEYS] + ["N_AsOf", "N_Change", "N_Causal"]
    agg_path = RESULTS_DIR / Path(args.out_aggregated).name
    with open(agg_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=agg_fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(agg_rows)
    print(f"Wrote {args.out_aggregated} (mean ± std)")

    # Print summary
    for version in versions:
        print(f"\n{version}:")
        for row in agg_rows:
            if row["version"] != version:
                continue
            trs_std = row.get("TRS_std", 0)
            acc_std = row.get("TemporalAccuracy_std", 0)
            print(f"  {row['system']}: TRS={row['TRS']:.4f}±{trs_std:.4f}, TemporalAccuracy={row['TemporalAccuracy']:.4f}±{acc_std:.4f}")


if __name__ == "__main__":
    main()
