#!/usr/bin/env python3
"""
Run one end-to-end baseline: train -> proxy eval -> holdout eval.
Records experiment and metrics in DB. Use --smoke for a fast run (few steps, tiny data).
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research_evolver.src.core.baseline_genome import get_baseline_genome
from research_evolver.src.execution.data_loader import load_train, load_proxy, load_holdout
from research_evolver.src.execution.trainer import train
from research_evolver.src.execution.evaluator import evaluate
from research_evolver.src.utils.config_loader import get_db_path, get_artifacts_root
from research_evolver.src.memory import get_connection, insert_experiment, insert_metrics


BASELINE_EXPERIMENT_ID = "baseline_0"


def main() -> int:
    ap = argparse.ArgumentParser(description="Run baseline train + proxy + holdout eval")
    ap.add_argument("--smoke", action="store_true", help="Fast run: 10 steps, skip holdout if no data")
    ap.add_argument("--no-train", action="store_true", help="Skip training (use existing adapter if any)")
    args = ap.parse_args()

    genome = get_baseline_genome()
    data_dir = ROOT / "research_evolver" / "data"
    artifacts_root = get_artifacts_root()
    exp_artifacts = artifacts_root / "experiments" / BASELINE_EXPERIMENT_ID
    adapter_dir = exp_artifacts / "adapter"
    adapter_dir.mkdir(parents=True, exist_ok=True)

    train_data = load_train(data_dir)
    proxy_data = load_proxy(data_dir)
    holdout_data = load_holdout(data_dir)

    if not train_data:
        print("No train data in research_evolver/data/processed/train.jsonl. Add data or run generate_synthetic_data.py first.")
        return 1

    # Train
    if not args.no_train:
        max_steps = 10 if args.smoke else None
        print("Training baseline (smoke=%s)..." % args.smoke)
        train(genome, train_data, adapter_dir, max_steps=max_steps)
    else:
        if not adapter_dir.joinpath("adapter_config.json").exists() and not adapter_dir.joinpath("config.json").exists():
            print("No adapter found at %s; run without --no-train first." % adapter_dir)
            return 1

    # Proxy eval
    proxy_metrics = {}
    if proxy_data:
        proxy_metrics = evaluate(genome, adapter_dir, proxy_data)
        print("Proxy accuracy:", proxy_metrics.get("accuracy", 0))
    else:
        print("No proxy split; skipping proxy eval.")
        proxy_metrics = {"accuracy": 0.0}

    # Holdout eval (optional in smoke if no holdout)
    holdout_metrics = {}
    if holdout_data:
        holdout_metrics = evaluate(genome, adapter_dir, holdout_data)
        print("Holdout accuracy:", holdout_metrics.get("accuracy", 0))
    elif not args.smoke:
        print("No holdout split; skipping holdout eval.")
    holdout_metrics = holdout_metrics or {"accuracy": 0.0}

    # Persist to DB (allow re-run: replace existing baseline row)
    db_path = get_db_path()
    conn = get_connection(str(db_path))
    conn.execute("DELETE FROM experiments WHERE experiment_id = ?", (BASELINE_EXPERIMENT_ID,))
    conn.execute("DELETE FROM metrics WHERE experiment_id = ?", (BASELINE_EXPERIMENT_ID,))
    conn.commit()
    insert_experiment(
        conn,
        experiment_id=BASELINE_EXPERIMENT_ID,
        generation=0,
        lineage_id=None,
        stage="baseline",
        status="completed",
        genome_json=genome.to_json(),
        fitness=None,
    )
    insert_metrics(conn, BASELINE_EXPERIMENT_ID, "proxy", proxy_metrics, seed=genome.seed)
    insert_metrics(conn, BASELINE_EXPERIMENT_ID, "holdout", holdout_metrics, seed=genome.seed)
    conn.close()
    print("Baseline run recorded in DB:", db_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
