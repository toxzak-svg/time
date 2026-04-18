"""
Stage runners: run_stage1_batch runs cheap screening (100–200 steps, small eval) on a list of (exp_id, genome).
run_stage2_batch: signal validation (400–800 steps, larger proxy eval). run_stage3_batch: holdout confirmation (full steps, 2 seeds).
Returns list of (exp_id, metrics) for ranking.
"""

from pathlib import Path
from typing import Any

from research_evolver.src.core.genome import Genome
from research_evolver.src.execution.data_loader import load_train, load_proxy, load_holdout
from research_evolver.src.execution.trainer import train
from research_evolver.src.execution.evaluator import evaluate
from research_evolver.src.utils.config_loader import load_benchmarks


def run_stage1_batch(
    children: list[tuple[str, Genome]],
    data_dir: Path,
    artifacts_root: Path,
    *,
    train_steps: int | None = None,
    proxy_eval_size: int | None = None,
) -> list[tuple[str, dict[str, float]]]:
    """
    Run stage-1 (cheap screening) on each (exp_id, genome).
    Returns [(exp_id, metrics), ...] with at least "accuracy" for proxy.
    """
    bench = load_benchmarks()
    stage1 = bench.get("stage1", {})
    steps_range = stage1.get("train_steps_range", [100, 200])
    eval_size = proxy_eval_size or stage1.get("eval_size", 100)
    steps = train_steps if train_steps is not None else steps_range[0]  # use min for speed

    train_data = load_train(data_dir)
    proxy_data = load_proxy(data_dir)
    if not train_data:
        return [(eid, {"accuracy": 0.0, "error": "no_train_data"}) for eid, _ in children]
    proxy_slice = proxy_data[:eval_size] if proxy_data else []

    results: list[tuple[str, dict[str, float]]] = []
    for i, (exp_id, genome) in enumerate(children):
        out_dir = artifacts_root / "experiments" / exp_id / "adapter"
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            train(genome, train_data, out_dir, max_steps=steps)
            metrics = evaluate(genome, out_dir, proxy_slice) if proxy_slice else {"accuracy": 0.0}
        except Exception as e:
            metrics = {"accuracy": 0.0, "error": str(e)}
            # Print first failure so user sees traceback cause
            if not any(r[1].get("error") for r in results):
                import traceback
                print("Stage-1 failed for %s: %s" % (exp_id, e))
                traceback.print_exc()
        results.append((exp_id, metrics))
    return results


def rank_by_proxy(results: list[tuple[str, dict[str, float]]], metric: str = "accuracy") -> list[tuple[str, dict[str, float]]]:
    """Sort by metric descending. Returns same list sorted."""
    return sorted(results, key=lambda x: x[1].get(metric, 0.0), reverse=True)


def run_stage2_batch(
    children: list[tuple[str, Genome]],
    data_dir: Path,
    artifacts_root: Path,
    *,
    train_steps: int | None = None,
    proxy_eval_size: int | None = None,
) -> list[tuple[str, dict[str, float]]]:
    """
    Stage 2: signal validation — 400–800 train steps, larger proxy eval.
    Returns [(exp_id, metrics), ...] with at least "accuracy" on proxy.
    """
    bench = load_benchmarks()
    stage2 = bench.get("stage2", {})
    steps_range = stage2.get("train_steps_range", [400, 800])
    eval_size = proxy_eval_size or stage2.get("eval_size", 300)
    steps = train_steps if train_steps is not None else steps_range[0]

    train_data = load_train(data_dir)
    proxy_data = load_proxy(data_dir)
    if not train_data:
        return [(eid, {"accuracy": 0.0, "error": "no_train_data"}) for eid, _ in children]
    proxy_slice = proxy_data[:eval_size] if proxy_data else []

    results: list[tuple[str, dict[str, float]]] = []
    for exp_id, genome in children:
        out_dir = artifacts_root / "experiments" / exp_id / "adapter"
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            train(genome, train_data, out_dir, max_steps=steps)
            metrics = evaluate(genome, out_dir, proxy_slice) if proxy_slice else {"accuracy": 0.0}
        except Exception as e:
            metrics = {"accuracy": 0.0, "error": str(e)}
            if not any(r[1].get("error") for r in results):
                import traceback
                print("Stage-2 failed for %s: %s" % (exp_id, e))
                traceback.print_exc()
        results.append((exp_id, metrics))
    return results


def run_stage3_batch(
    children: list[tuple[str, Genome]],
    data_dir: Path,
    artifacts_root: Path,
    *,
    holdout_seeds: list[int] | None = None,
    holdout_eval_size: int | None = None,
) -> list[tuple[str, dict[str, float]]]:
    """
    Stage 3: real confirmation — full train_steps from genome, frozen holdout, 2 seeds.
    Returns [(exp_id, metrics), ...] with "accuracy" = mean over seeds and "holdout_accuracy".
    """
    bench = load_benchmarks()
    stage3 = bench.get("stage3", {})
    seeds = holdout_seeds or stage3.get("seeds", 2)
    if isinstance(seeds, int):
        seeds = [42 + i for i in range(seeds)]
    eval_size = holdout_eval_size or stage3.get("eval_size", 500)

    train_data = load_train(data_dir)
    holdout_data = load_holdout(data_dir)
    if not train_data:
        return [(eid, {"accuracy": 0.0, "holdout_accuracy": 0.0, "error": "no_train_data"}) for eid, _ in children]
    holdout_slice = holdout_data[:eval_size] if holdout_data else []

    results: list[tuple[str, dict[str, float]]] = []
    for exp_id, genome in children:
        out_dir = artifacts_root / "experiments" / exp_id / "adapter"
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            train(genome, train_data, out_dir, max_steps=None)  # full steps from genome
            accs: list[float] = []
            for seed in seeds:
                # Eval with same adapter; seed affects decoding if we used do_sample
                m = evaluate(genome, out_dir, holdout_slice)
                accs.append(m.get("accuracy", 0.0))
            mean_acc = sum(accs) / len(accs) if accs else 0.0
            metrics = {"accuracy": mean_acc, "holdout_accuracy": mean_acc}
            for i, a in enumerate(accs):
                metrics["holdout_seed%d" % i] = a
        except Exception as e:
            metrics = {"accuracy": 0.0, "holdout_accuracy": 0.0, "error": str(e)}
            if not any(r[1].get("error") for r in results):
                import traceback
                print("Stage-3 failed for %s: %s" % (exp_id, e))
                traceback.print_exc()
        results.append((exp_id, metrics))
    return results
