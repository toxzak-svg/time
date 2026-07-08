#!/usr/bin/env python3
"""
Stage 1: spawn N children (mutations + random immigrants), run cheap screening, rank, persist, report.
Usage: python research_evolver/scripts/run_stage1.py [--generation 1] [--n-children 50] [--smoke]
  --smoke: use 10 train steps and skip writing heavy artifacts (for CI/quick check).
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research_evolver.src.core.baseline_genome import get_baseline_genome
from research_evolver.src.core.mutations import spawn_children
from research_evolver.src.execution.stage_runner import run_stage1_batch, rank_by_proxy
from research_evolver.src.utils.config_loader import get_db_path, get_artifacts_root
from research_evolver.src.memory import get_connection, insert_experiment, insert_metrics


def main() -> int:
    ap = argparse.ArgumentParser(description="Spawn children, run stage-1, rank, persist, report")
    ap.add_argument("--generation", type=int, default=1, help="Generation index")
    ap.add_argument("--n-children", type=int, default=50, help="Total children (mutants + immigrants)")
    ap.add_argument("--smoke", action="store_true", help="10 steps only, quick check")
    ap.add_argument("--dry-run", action="store_true", help="Only spawn children and write report; no training (no GPU needed)")
    args = ap.parse_args()

    rng = __import__("random").Random(42 + args.generation)
    # Total = args.n_children; use a few as random immigrants
    n_immigrants = min(5, max(1, args.n_children // 10))
    n_children = args.n_children - n_immigrants
    if n_children < 1:
        n_children = 1
        n_immigrants = args.n_children - 1

    parents = [get_baseline_genome()]
    children_genomes = spawn_children(parents, n_children, n_immigrants, rng)
    exp_ids = [f"gen{args.generation}_exp{i:03d}" for i in range(1, len(children_genomes) + 1)]
    children = list(zip(exp_ids, children_genomes))

    data_dir = ROOT / "research_evolver" / "data"
    artifacts_root = get_artifacts_root()

    if args.dry_run:
        print("Dry run: %d children spawned (no training)." % len(children))
        results = [(eid, {"accuracy": 0.0}) for eid, _ in children]
        ranked = results
    else:
        train_steps = 10 if args.smoke else None
        print("Running stage-1 on %d children (smoke=%s)..." % (len(children), args.smoke))
        results = run_stage1_batch(
            children,
            data_dir,
            artifacts_root,
            train_steps=train_steps,
        )
        ranked = rank_by_proxy(results)
    # Surface errors (e.g. train/eval failed → all 0)
    errors = [(eid, m.get("error")) for eid, m in results if m.get("error")]
    if errors:
        print("Errors (first 3):")
        for eid, err in errors[:3]:
            print("  %s: %s" % (eid, err[:200] + "..." if len(str(err)) > 200 else err))
    print("Top 5 by proxy accuracy:")
    for exp_id, m in ranked[:5]:
        print("  %s: %.4f" % (exp_id, m.get("accuracy", 0)))

    db_path = get_db_path()
    conn = get_connection(str(db_path))
    for exp_id, _ in children:
        conn.execute("DELETE FROM metrics WHERE experiment_id = ?", (exp_id,))
        conn.execute("DELETE FROM experiments WHERE experiment_id = ?", (exp_id,))
    conn.commit()
    children_by_id = {eid: g for eid, g in children}
    for exp_id, metrics in results:
        genome = children_by_id[exp_id]
        insert_experiment(
            conn,
            experiment_id=exp_id,
            generation=args.generation,
            lineage_id=None,
            stage="stage1",
            status="completed",
            genome_json=genome.to_json(),
            fitness=metrics.get("accuracy"),
        )
        numeric_metrics = {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))}
        if numeric_metrics:
            insert_metrics(conn, exp_id, "proxy", numeric_metrics, seed=genome.seed)
    conn.close()

    report_dir = artifacts_root / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"gen{args.generation}_stage1.txt"
    with open(report_path, "w") as f:
        f.write("Generation %d — Stage 1 ranking (by proxy accuracy)\n" % args.generation)
        f.write("=" * 60 + "\n")
        if errors:
            f.write("# Errors (train/eval failed):\n")
            for eid, err in errors[:10]:
                f.write("#   %s: %s\n" % (eid, (err or "")[:300]))
            f.write("\n")
        for exp_id, m in ranked:
            f.write("%s\t%.4f\n" % (exp_id, m.get("accuracy", 0)))
    print("Report written to %s" % report_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
