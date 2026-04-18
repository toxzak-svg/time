#!/usr/bin/env python3
"""Compute paired t-test and bootstrap 95%% CI for TRS and TemporalAccuracy."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
NUMERIC_KEYS = ["TRS", "TemporalAccuracy"]


def load_per_seed(path: Path) -> dict[tuple[str, str], list[dict]]:
    """Load per-seed CSV; return dict (version, system) -> list of rows."""
    by_key = {}
    with path.open("r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = (row["version"], row["system"])
            if key not in by_key:
                by_key[key] = []
            by_key[key].append(row)
    return by_key


def bootstrap_ci(values: list[float], n_bootstrap: int = 2000, ci: float = 0.95) -> tuple[float, float]:
    """Bootstrap 95% CI (default) for mean."""
    n = len(values)
    rng = np.random.default_rng(42)
    means = [float(np.mean(rng.choice(values, size=n, replace=True))) for _ in range(n_bootstrap)]
    lo = (1 - ci) / 2
    hi = 1 - lo
    return float(np.quantile(means, lo)), float(np.quantile(means, hi))


def paired_ttest(v1: list[float], v2: list[float]) -> tuple[float, float]:
    """Paired t-test (v1 - v2); return (t_stat, p_value). Use scipy if available."""
    n = len(v1)
    if n != len(v2) or n < 2:
        return float("nan"), float("nan")
    try:
        from scipy import stats
        t, p = stats.ttest_rel(v1, v2)
        return float(t), float(p)
    except ImportError:
        # Manual paired t-test
        diff = np.array(v1) - np.array(v2)
        mean_d = float(np.mean(diff))
        std_d = float(np.std(diff)) or 1e-10
        t = mean_d / (std_d / np.sqrt(n))
        # Approximate p from t (two-tailed); rough for small n
        from math import erf, sqrt
        p = 2 * (1 - 0.5 * (1 + erf(abs(t) / sqrt(2))))
        return float(t), float(p)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-seed-csv", default="results/per_seed_results.csv")
    ap.add_argument("--out", default="results/significance.csv")
    ap.add_argument("--comparisons", type=str, default="D_vs_A,D_vs_C,D_revised_vs_D,D_revised_vs_C,C_vs_A",
                    help="Comma-separated comparison names (pair: left vs right)")
    args = ap.parse_args()

    path = Path(args.per_seed_csv)
    if not path.is_absolute():
        path = RESULTS_DIR / path.name
    if not path.exists():
        raise SystemExit(f"Missing {path}; run scripts/run_benchmark_multi_seed.py first")

    by_key = load_per_seed(path)
    versions = sorted({k[0] for k in by_key})

    # Parse comparisons: "D_vs_A" -> (D, A)
    comparisons = []
    for s in args.comparisons.split(","):
        s = s.strip()
        if "_vs_" in s:
            left, right = s.split("_vs_", 1)
            comparisons.append((left.strip(), right.strip()))
        else:
            comparisons.append((s, None))

    rows = []
    for version in versions:
        for metric in NUMERIC_KEYS:
            for left, right in comparisons:
                if right is None:
                    continue
                k_left = (version, left)
                k_right = (version, right)
                if k_left not in by_key or k_right not in by_key:
                    continue
                left_vals = [float(r[metric]) for r in by_key[k_left]]
                right_vals = [float(r[metric]) for r in by_key[k_right]]
                if len(left_vals) != len(right_vals) or len(left_vals) < 2:
                    continue
                try:
                    t, p = paired_ttest(left_vals, right_vals)
                except Exception:
                    t, p = float("nan"), float("nan")
                ci_lo, ci_hi = bootstrap_ci([a - b for a, b in zip(left_vals, right_vals)])
                rows.append({
                    "version": version,
                    "metric": metric,
                    "comparison": f"{left}_vs_{right}",
                    "mean_diff": float(np.mean(np.array(left_vals) - np.array(right_vals))),
                    "ci_95_lo": ci_lo,
                    "ci_95_hi": ci_hi,
                    "t_stat": t,
                    "p_value": p,
                })

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = RESULTS_DIR / out_path.name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["version", "metric", "comparison", "mean_diff", "ci_95_lo", "ci_95_hi", "t_stat", "p_value"]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out_path}")
    for r in rows:
        sig = " *" if r["p_value"] < 0.05 else ""
        print(f"  {r['version']} {r['metric']} {r['comparison']}: diff={r['mean_diff']:.4f} "
              f"95% CI=[{r['ci_95_lo']:.4f}, {r['ci_95_hi']:.4f}] p={r['p_value']:.4f}{sig}")


if __name__ == "__main__":
    main()
