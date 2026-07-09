#!/usr/bin/env python3
"""
Stage 2: signal validation — load top stage1 from DB, run 400–800 steps, larger proxy eval, persist.
Usage: python research_evolver/scripts/run_stage2.py [--generation 1] [--smoke]
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research_evolver.src.core.genome import Genome
from research_evolver.src.execution.stage_runner import run_stage2_batch, rank_by_proxy
from research_evolver.src.utils.config_loader import get_db_path, get_artifacts_root, load_benchmarks
from research_evolver.src.memory import get_connection, get_experiments_by_generation_stage, update_experiment_stage_fitness, insert_metrics


def main() -> int:
    ap = argparse.ArgumentParser(description="Run stage-2 on promoted stage1 experiments")
    ap.add_argument("--generation", type=int, default=1, help="Generation index")
    ap.add_argument("--smoke", action="store_true", help="Fewer steps for quick check")
    args = ap.parse_args()

    db_path = get_db_path()
    conn = get_connection(str(db_path))
    rows = get_experiments_by_generation_stage(conn, args.generation, "stage1", order_by_fitness_desc=True)
    conn.close()

    bench = load_benchmarks()
    promo = bench.get("promotion", {})
    top_frac = promo.get("stage1_top_fraction", 0.2)
    min_s2 = promo.get("min_stage2", 2)
    n_take = max(min_s2, int(len(rows) * top_frac)) if rows else 0
    to_run = rows[:n_take]

    if not to_run:
        print("No stage1 experiments to promote for generation %d." % args.generation)
        return 0

    children: list[tuple[str, Genome]] = []
    for exp_id, genome_json, _ in to_run:
        children.append((exp_id, Genome.from_json(genome_json)))

    data_dir = ROOT / "research_evolver" / "data"
    artifacts_root = get_artifacts_root()
    train_steps = 20 if args.smoke else None
    print("Running stage-2 on %d experiments (smoke=%s)..." % (len(children), args.smoke))
    results = run_stage2_batch(
        children,
        data_dir,
        artifacts_root,
        train_steps=train_steps,
    )
    ranked = rank_by_proxy(results)

    errors = [(eid, m.get("error")) for eid, m in results if m.get("error")]
    if errors:
        print("Errors (first 3):")
        for eid, err in errors[:3]:
            print("  %s: %s" % (eid, (err or "")[:200]))
    print("Top 5 by proxy accuracy (stage2):")
    for exp_id, m in ranked[:5]:
        print("  %s: %.4f" % (exp_id, m.get("accuracy", 0)))

    conn = get_connection(str(db_path))
    for exp_id, metrics in results:
        update_experiment_stage_fitness(conn, exp_id, "stage2", metrics.get("accuracy"))
        numeric = {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))}
        if numeric:
            insert_metrics(conn, exp_id, "proxy_stage2", numeric, seed=0)
    conn.close()

    report_dir = artifacts_root / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "gen%d_stage2.txt" % args.generation
    with open(report_path, "w") as f:
        f.write("Generation %d — Stage 2 (proxy accuracy)\n" % args.generation)
        f.write("=" * 60 + "\n")
        for exp_id, m in ranked:
            f.write("%s\t%.4f\n" % (exp_id, m.get("accuracy", 0)))
    print("Report written to %s" % report_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
