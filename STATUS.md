# TTA Benchmark — Project Status

**Last updated**: March 2025 (after full multi-seed run v1–v4 × 3 seeds)

---

## Summary

The Temporal Truth Architecture (TTA) benchmark evaluates retrieval systems A/B/C/D and D_revised across four benchmark versions (v1 easy → v4 extreme). All planned protocol and housekeeping items are complete: multi-seed runs with mean ± std, significance testing, D_revised (validity-only + tiebreak), accuracy-vs-age figures for all versions, change detection in v3, and README updates.

---

## Deliverables Status

| Item | Status | Notes |
|------|--------|------|
| One-page experimental report | ✅ | `EXPERIMENTAL_REPORT.md` |
| Multi-seed runs (3 seeds) | ✅ | `run_benchmark_multi_seed.py`; outputs per-seed + aggregated |
| Significance testing | ✅ | `compute_significance.py` → `results/significance.csv` |
| D_revised variant | ✅ | Validity-only + confidence tiebreak; in harness and multi-seed |
| Accuracy vs fact age (v1–v4) | ✅ | `generate_accuracy_figure.py` — single + `--combined` faceted |
| Change detection (v3) | ✅ | 50 ChangeDetection questions in v3 generator |
| README & docs | ✅ | Multi-version, multi-seed, figures, results layout |

---

## Key Results (multi-seed mean ± std)

**TRS (Temporal Retrieval Score)** — higher is better.

| Version | A | B | C | D | D_revised |
|---------|------|------|------|------|-----------|
| v1 (Easy) | 0.38±0.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| v2 (Adversarial) | 0.59±0.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| v3 (Hard) | 0.48±0.00 | 0.82±0.01 | **0.83±0.00** | 0.82±0.01 | **0.83±0.00** |
| v4 (Extreme) | 0.22±0.02 | 0.50±0.01 | **0.53±0.01** | 0.49±0.01 | **0.53±0.01** |

**Temporal Accuracy** — fraction of temporal questions correct.

| Version | A | B | C | D | D_revised |
|---------|------|------|------|------|-----------|
| v1 | 0.04±0.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| v2 | 0.37±0.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| v3 | 0.20±0.00 | 0.49±0.02 | **0.52±0.00** | 0.47±0.02 | **0.52±0.00** |
| v4 | 0.46±0.02 | 0.58±0.02 | **0.65±0.03** | 0.55±0.02 | **0.65±0.03** |

**Finding**: On v3/v4, C (time constraint) and D_revised (validity-only + tiebreak) tie and outperform D (full TTA with decay). Significance: on v4, D_revised vs D and D vs C are significant (p &lt; 0.05) for TRS and Temporal Accuracy.

---

## Artifacts

| Path | Description |
|------|-------------|
| `results/per_seed_results.csv` | Per (version, seed, system) metrics (60 rows for v1–v4 × 3 seeds × 5 systems) |
| `results/main_table_multi_seed.csv` | Aggregated mean ± std per (version, system) |
| `results/significance.csv` | Paired comparisons: D vs A, D vs C, D_revised vs D, D_revised vs C, C vs A (TRS + TemporalAccuracy, 95% CI, p-values) |
| `results/v1_main_table.csv` … `v4_main_table.csv` | Single-run canonical tables (optional) |
| `figures/accuracy_vs_fact_age.png` | Single-version accuracy vs fact age |
| `figures/accuracy_vs_fact_age_combined.png` | Faceted v1–v4 accuracy vs fact age |
| `benchmarks/{v1,v2,v3,v4}_seed{0,1,2}/` | Generated data for multi-seed runs |

---

## How to Run

```bash
# Full multi-seed (v1–v4 × seeds 0,1,2)
python scripts/run_benchmark_multi_seed.py --seeds 0,1,2 --versions v1,v2,v3,v4

# Significance (after per-seed results exist)
python scripts/compute_significance.py

# Combined accuracy figure (uses benchmarks/temporalbench_v*.jsonl)
python scripts/generate_accuracy_figure.py --combined
```

See **README.md** for quickstart, systems table, and Colab notes.

---

## Reference Docs

- **EXPERIMENT_PLAN.md** — hypothesis, protocol, metrics
- **RESULTS_OVERVIEW.md** — narrative results summary
- **EXPERIMENTAL_REPORT.md** — one-page report
- **NEXT_STEPS.md** — completed checklist + optional future work (adversarial tasks, etc.)
