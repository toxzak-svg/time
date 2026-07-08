#!/usr/bin/env python3
"""
Primary generation loop:
  load_population (or baseline for gen 0) -> spawn_children -> run_stage1 -> promote -> run_stage2 -> promote -> run_stage3
  -> choose_survivors -> update_lineages -> insert_generation_summary -> report
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research_evolver.src.core.baseline_genome import get_baseline_genome
from research_evolver.src.core.genome import Genome
from research_evolver.src.core.mutations import spawn_children_with_parent_indices, spawn_children_with_crossover
from research_evolver.src.execution.stage_runner import (
    run_stage1_batch,
    run_stage2_batch,
    run_stage3_batch,
    rank_by_proxy,
)
from research_evolver.src.utils.config_loader import get_db_path, get_artifacts_root, load_benchmarks
from research_evolver.src.memory import (
    get_connection,
    insert_experiment,
    insert_metrics,
    get_experiments_by_generation_stage,
    update_experiment_stage_fitness,
    get_best_survivors,
    insert_generation_summary,
    upsert_lineage,
)


def run_generation(
    gen_idx: int,
    *,
    n_children: int = 50,
    smoke: bool = False,
    dry_run: bool = False,
) -> None:
    data_dir = ROOT / "research_evolver" / "data"
    artifacts_root = get_artifacts_root()
    db_path = get_db_path()
    bench = load_benchmarks()
    promo = bench.get("promotion", {})
    top_frac = promo.get("stage1_top_fraction", 0.2)
    min_s2 = promo.get("min_stage2", 2)
    stage2_top_n = promo.get("stage2_top_n", 10)
    min_s3 = promo.get("min_stage3", 1)
    survivors_limit = promo.get("survivors_for_next_gen", 10)
    species_cap = promo.get("species_cap")
    use_crossover = promo.get("use_crossover", False)
    crossover_frac = promo.get("crossover_fraction", 0.2)

    rng = __import__("random").Random(42 + gen_idx)
    n_immigrants = min(5, max(1, n_children // 10))
    n_mutants = n_children - n_immigrants
    if n_mutants < 1:
        n_mutants = 1
        n_immigrants = n_children - 1

    # --- Parents (with optional species cap: max N per lineage) ---
    if gen_idx == 0:
        parents: list[Genome] = [get_baseline_genome()]
        parent_lineages: list[tuple[str, str]] = [("baseline", "gen0_baseline")]
    else:
        conn = get_connection(str(db_path))
        rows = get_best_survivors(conn, gen_idx - 1, "stage3", limit=survivors_limit * 2)
        conn.close()
        if not rows:
            raise RuntimeError("No survivors from generation %d; cannot run gen %d." % (gen_idx - 1, gen_idx))
        if species_cap is not None and species_cap >= 1:
            conn = get_connection(str(db_path))
            lineage_count: dict[str, int] = {}
            capped = []
            for eid, js, fit in rows:
                row = conn.execute("SELECT lineage_id FROM experiments WHERE experiment_id = ?", (eid,)).fetchone()
                lid = row[0] if row and row[0] else eid
                if lineage_count.get(lid, 0) < species_cap:
                    lineage_count[lid] = lineage_count.get(lid, 0) + 1
                    capped.append((eid, js, fit))
                if len(capped) >= survivors_limit:
                    break
            conn.close()
            rows = capped[:survivors_limit]
        else:
            rows = rows[:survivors_limit]
        parents = [Genome.from_json(js) for _, js, _ in rows]
        parent_lineages = [(eid, eid) for eid, _, _ in rows]

    # --- Spawn children (crossover or mutation) with parent indices for lineage ---
    if use_crossover and len(parents) >= 2:
        spawned = spawn_children_with_crossover(parents, n_mutants, n_immigrants, rng, crossover_fraction=crossover_frac)
    else:
        spawned = spawn_children_with_parent_indices(parents, n_mutants, n_immigrants, rng)
    exp_ids = [f"gen{gen_idx}_exp{i:03d}" for i in range(1, len(spawned) + 1)]
    children: list[tuple[str, Genome]] = []
    lineage_ids: list[str | None] = []
    for i, (genome, parent_idx) in enumerate(spawned):
        exp_id = exp_ids[i]
        children.append((exp_id, genome))
        if parent_idx is not None and parent_idx < len(parent_lineages):
            lineage_ids.append(parent_lineages[parent_idx][1])
        else:
            lineage_ids.append(exp_id)

    # --- Stage 1 ---
    if dry_run:
        stage1_results = [(eid, {"accuracy": 0.0}) for eid, _ in children]
    else:
        train_steps = 10 if smoke else None
        stage1_results = run_stage1_batch(
            children, data_dir, artifacts_root, train_steps=train_steps
        )
    ranked_s1 = rank_by_proxy(stage1_results)
    conn = get_connection(str(db_path))
    for (exp_id, genome), lid in zip(children, lineage_ids):
        conn.execute("DELETE FROM metrics WHERE experiment_id = ?", (exp_id,))
        conn.execute("DELETE FROM experiments WHERE experiment_id = ?", (exp_id,))
    conn.commit()
    children_by_id = {eid: g for eid, g in children}
    for (exp_id, metrics), lineage_id in zip(stage1_results, lineage_ids):
        genome = children_by_id[exp_id]
        insert_experiment(
            conn,
            experiment_id=exp_id,
            generation=gen_idx,
            lineage_id=lineage_id,
            stage="stage1",
            status="completed",
            genome_json=genome.to_json(),
            fitness=metrics.get("accuracy"),
        )
        numeric = {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))}
        if numeric:
            insert_metrics(conn, exp_id, "proxy", numeric, seed=genome.seed)
    conn.close()

    n_s1 = len(ranked_s1)
    to_s2 = max(min_s2, int(n_s1 * top_frac))
    to_s2 = min(to_s2, n_s1)
    conn = get_connection(str(db_path))
    rows_s2 = get_experiments_by_generation_stage(conn, gen_idx, "stage1", limit=to_s2)
    conn.close()
    stage2_candidates = [(eid, Genome.from_json(js)) for eid, js, _ in rows_s2]

    # --- Stage 2 ---
    if not dry_run and stage2_candidates:
        s2_results = run_stage2_batch(
            stage2_candidates, data_dir, artifacts_root,
            train_steps=20 if smoke else None,
        )
        ranked_s2 = rank_by_proxy(s2_results)
        conn = get_connection(str(db_path))
        for exp_id, metrics in s2_results:
            update_experiment_stage_fitness(conn, exp_id, "stage2", metrics.get("accuracy"))
            numeric = {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))}
            if numeric:
                insert_metrics(conn, exp_id, "proxy_stage2", numeric, seed=0)
        conn.close()
        n_s2 = len(s2_results)
        to_s3 = max(min_s3, min(promo.get("stage2_top_n", 10), n_s2))
        conn = get_connection(str(db_path))
        rows_s3 = get_experiments_by_generation_stage(conn, gen_idx, "stage2", limit=to_s3)
        conn.close()
        stage3_candidates = [(eid, Genome.from_json(js)) for eid, js, _ in rows_s3]
    else:
        ranked_s2 = []
        stage3_candidates = []

    # --- Stage 3 ---
    if not dry_run and stage3_candidates:
        s3_results = run_stage3_batch(stage3_candidates, data_dir, artifacts_root)
        ranked_s3 = rank_by_proxy(s3_results, metric="holdout_accuracy")
        conn = get_connection(str(db_path))
        for exp_id, metrics in s3_results:
            fit = metrics.get("holdout_accuracy", metrics.get("accuracy"))
            update_experiment_stage_fitness(conn, exp_id, "stage3", fit)
            numeric = {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))}
            if numeric:
                insert_metrics(conn, exp_id, "holdout", numeric, seed=0)
        conn.close()
        best_fitness = ranked_s3[0][1].get("holdout_accuracy", 0.0) if ranked_s3 else None
    else:
        ranked_s3 = []
        best_fitness = ranked_s1[0][1].get("accuracy", 0.0) if ranked_s1 else None

    # --- Survivors & lineage: best per lineage ---
    conn = get_connection(str(db_path))
    s3_rows = get_experiments_by_generation_stage(conn, gen_idx, "stage3", limit=survivors_limit)
    lineage_best: dict[str, tuple[str, float | None]] = {}
    for exp_id, genome_json, fitness in s3_rows:
        row = conn.execute("SELECT lineage_id FROM experiments WHERE experiment_id = ?", (exp_id,)).fetchone()
        lid = row[0] if row and row[0] else exp_id
        if lid not in lineage_best or (fitness is not None and (lineage_best[lid][1] is None or fitness > lineage_best[lid][1])):
            lineage_best[lid] = (exp_id, fitness)
    for lid, (best_exp_id, _) in lineage_best.items():
        upsert_lineage(conn, lid, lid, best_exp_id, gen_idx + 1, 0)
    conn.close()

    # --- Generation summary ---
    conn = get_connection(str(db_path))
    insert_generation_summary(
        conn,
        gen_idx,
        population_size=len(children),
        stage1_pass_count=len(ranked_s1),
        stage2_pass_count=len(stage2_candidates) if not dry_run else 0,
        stage3_pass_count=len(stage3_candidates) if not dry_run else 0,
        best_fitness=best_fitness,
        total_cost=0.0,
    )
    conn.close()

    # --- Report ---
    report_dir = artifacts_root / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"gen{gen_idx}_summary.txt"
    with open(report_path, "w") as f:
        f.write("Generation %d summary\n" % gen_idx)
        f.write("Population: %d -> stage1: %d -> stage2: %d -> stage3: %d\n" % (
            len(children), n_s1, len(stage2_candidates), len(stage3_candidates)
        ))
        f.write("Best fitness (stage3 holdout): %s\n" % (best_fitness if best_fitness is not None else "N/A"))
        if ranked_s3:
            f.write("Top survivors:\n")
            for exp_id, m in ranked_s3[:5]:
                f.write("  %s\t%.4f\n" % (exp_id, m.get("holdout_accuracy", 0)))
    print("Generation %d done. Report: %s" % (gen_idx, report_path))


def main() -> None:
    ap = argparse.ArgumentParser(description="Run one full evolution generation")
    ap.add_argument("generation", type=int, nargs="?", default=0, help="Generation index (default 0)")
    ap.add_argument("--n-children", type=int, default=50, help="Children per generation")
    ap.add_argument("--smoke", action="store_true", help="Minimal steps for quick check")
    ap.add_argument("--dry-run", action="store_true", help="Spawn and persist only; no training")
    args = ap.parse_args()
    run_generation(
        args.generation,
        n_children=args.n_children,
        smoke=args.smoke,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
