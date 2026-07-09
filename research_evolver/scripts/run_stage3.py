#!/usr/bin/env python3
"""
Stage 3: real confirmation — load top stage2 from DB, full steps, frozen holdout, 2 seeds. Persist.
Usage: python research_evolver/scripts/run_stage3.py [--generation 1] [--smoke]
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research_evolver.src.core.genome import Genome
from research_evolver.src.execution.stage_runner import run_stage3_batch, rank_by_proxy
from research_evolver.src.utils.config_loader import get_db_path, get_artifacts_root, load_benchmarks
from research_evolver.src.memory import get_connection, get_experiments_by_generation_stage, update_experiment_stage_fitness, insert_metrics


def main() -> int:
    ap = argparse.ArgumentParser(description="Run stage-3 on promoted stage2 experiments")
    ap.add_argument("--generation", type=int, default=1, help="Generation index")
    ap.add_argument("--smoke", action="store_true", help="Fewer steps for quick check")
    args = ap.parse_args()

    db_path = get_db_path()
    conn = get_connection(str(db_path))
    rows = get_experiments_by_generation_stage(conn, args.generation, "stage2", order_by_fitness_desc=True)
    conn.close()

    bench = load_benchmarks()
    promo = bench.get("promotion", {})
    top_n = promo.get("stage2_top_n", 10)
    min_s3 = promo.get("min_stage3", 1)
    n_take = max(min_s3, min(top_n, len(rows))) if rows else 0
    to_run = rows[:n_take]

    if not to_run:
        print("No stage2 experiments to promote for generation %d." % args.generation)
        return 0

    children: list[tuple[str, Genome]] = []
    for exp_id, genome_json, _ in to_run:
        children.append((exp_id, Genome.from_json(genome_json)))

    data_dir = ROOT / "research_evolver" / "data"
    artifacts_root = get_artifacts_root()
    print("Running stage-3 on %d experiments (holdout, 2 seeds; smoke=%s)..." % (len(children), args.smoke))
    results = run_stage3_batch(children, data_dir, artifacts_root)
    ranked = rank_by_proxy(results, metric="holdout_accuracy")

    errors = [(eid, m.get("error")) for eid, m in results if m.get("error")]
    if errors:
        print("Errors (first 3):")
        for eid, err in errors[:3]:
            print("  %s: %s" % (eid, (err or "")[:200]))
    print("Top 5 by holdout accuracy (stage3):")
    for exp_id, m in ranked[:5]:
        print("  %s: %.4f" % (exp_id, m.get("holdout_accuracy", m.get("accuracy", 0))))

    conn = get_connection(str(db_path))
    for exp_id, metrics in results:
        fit = metrics.get("holdout_accuracy", metrics.get("accuracy"))
        update_experiment_stage_fitness(conn, exp_id, "stage3", fit)
        numeric = {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))}
        if numeric:
            insert_metrics(conn, exp_id, "holdout", numeric, seed=0)
    conn.close()

    report_dir = artifacts_root / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "gen%d_stage3.txt" % args.generation
    with open(report_path, "w") as f:
        f.write("Generation %d — Stage 3 (holdout accuracy)\n" % args.generation)
        f.write("=" * 60 + "\n")
        for exp_id, m in ranked:
            f.write("%s\t%.4f\n" % (exp_id, m.get("holdout_accuracy", m.get("accuracy", 0))))
    print("Report written to %s" % report_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
