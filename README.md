# time

Concrete experiment specification for evaluating **Temporal Truth Architecture (TTA)** against current time-aware agent baselines:

- **`EXPERIMENT_PLAN.md`** — hypothesis, systems, dataset design, metrics, protocol
- **`ADVERSARIAL_TEMPORAL_TASKS.md`** — adversarial task taxonomy and mapping to this benchmark
- **`RESULTS_OVERVIEW.md`** — benchmark results summary (v1–v4, ablations)
- **`EXPERIMENTAL_REPORT.md`** — one-page experimental report (claim, main results, error analysis)
- **`NEXT_STEPS.md`** — suggested follow-up work (multi-seed, significance, D_revised, figures)

## Implementation

- **Generators**: `scripts/generate_temporalbench_v1.py` … `v4.py` — synthetic events, facts, and questions (v1 easy → v4 extreme).
- **Harness**: `scripts/run_benchmark.py` — A/B/C/D (and D_revised, ablation, semantic) evaluation → `results/*.csv`.
- **Multi-seed**: `scripts/run_benchmark_multi_seed.py` — run with 3 seeds, aggregate mean ± std → `results/per_seed_results.csv`, `results/main_table_multi_seed.csv`.
- **Significance**: `scripts/compute_significance.py` — paired t-test and bootstrap 95% CI (requires `results/per_seed_results.csv`).
- **Figures**: `scripts/generate_accuracy_figure.py` — accuracy vs fact age (single version or `--combined` for v1–v4 faceted).

### Quickstart (single run)

```bash
# v1 only
python scripts/generate_temporalbench_v1.py
python scripts/run_benchmark.py

# v2 / v3 / v4 (then run harness with versioned paths)
python scripts/generate_temporalbench_v2.py
python scripts/run_benchmark.py --facts benchmarks/temporalbench_v2_facts.jsonl --questions benchmarks/temporalbench_v2_questions.jsonl --events benchmarks/temporalbench_v2_events.jsonl --out results/v2_main_table.csv
```

### Multi-version (v1–v4)

```bash
python scripts/generate_temporalbench_v1.py
python scripts/generate_temporalbench_v2.py
python scripts/generate_temporalbench_v3.py
python scripts/generate_temporalbench_v4.py
python scripts/run_benchmark.py --facts benchmarks/temporalbench_v3_facts.jsonl --questions benchmarks/temporalbench_v3_questions.jsonl --events benchmarks/temporalbench_v3_events.jsonl --out results/v3_main_table.csv
# Similarly for v2, v4. Or use multi-seed script to generate and run all versions × seeds.
```

### Multi-seed and significance

```bash
# Generate v1–v4 with seeds 0,1,2 and run A,B,C,D,D_revised; write per-seed and aggregated tables
python scripts/run_benchmark_multi_seed.py --seeds 0,1,2 --versions v1,v2,v3,v4

# Then compute paired t-tests and bootstrap 95% CI (D vs A, D vs C, D_revised vs D, etc.)
pip install scipy  # optional; script falls back to manual t-test if missing
python scripts/compute_significance.py --per-seed-csv results/per_seed_results.csv --out results/significance.csv
```

### Figures

```bash
# Single version (default v1)
python scripts/generate_accuracy_figure.py --out figures/accuracy_vs_fact_age.png

# By version
python scripts/generate_accuracy_figure.py --version v3 --out figures/accuracy_vs_fact_age_v3.png

# Combined faceted figure (v1–v4)
python scripts/generate_accuracy_figure.py --combined --out figures/accuracy_vs_fact_age.png
# Writes figures/accuracy_vs_fact_age_combined.png
```

### Systems

| Code | Description |
|------|-------------|
| A | Plain RAG (latest fact by timestamp) |
| B | Temporal rerank (validity + recency, no decay) |
| C | Time constraint (validity filter only) |
| D | TTA full (intervals + domain-adaptive decay) |
| D_revised | Validity-only + confidence tiebreak (no decay) |

Ablation: `python scripts/run_benchmark.py --ablation` (D, D_no_decay, D_no_intervals, D_no_rerank). Semantic: `--semantic` adds E, E_hybrid (requires `sentence-transformers`).

### Adversarial temporal tasks (TTA vs RAG)

- **Generator**: `scripts/generate_adversarial_temporal.py` — Reversion, Interval, CausalReasoning, MultiReversion, IntervalMidpoint, MultiEntityJoin.
- **Harness**: `scripts/run_adversarial_benchmark.py` — metrics by task family (e.g. ReversionAccuracy, OverallAccuracy). Systems: A, B, C, D, D_revised.
- **Colab**: `tta_adversarial_colab.ipynb` — generate adversarial data, run A vs D vs D_revised, view per-task accuracy and conclusion.

```bash
python scripts/generate_adversarial_temporal.py --out-dir benchmarks
python scripts/run_adversarial_benchmark.py --systems A,D,D_revised --out results/adversarial_results.csv
```

### Colab

- **`tta_benchmark_colab.ipynb`** — main benchmark (A/B/C/D and optional semantic) on v1–v4. Clone the repo into the Colab runtime then run the notebook cells (generate + `run_benchmark.py`).
- **`adversarial_temporal_colab.ipynb`** — adversarial tasks: run `scripts/generate_adversarial_temporal.py` and `scripts/run_adversarial_benchmark.py`; results in `results/adversarial_temporal_results.csv`.

### Results layout

- **Canonical single-run tables**: `results/v1_main_table.csv` … `results/v4_main_table.csv`, `results/ablation_table.csv`.
- **Multi-seed**: `results/per_seed_results.csv` (per version/seed/system), `results/main_table_multi_seed.csv` (mean ± std).
- **Significance**: `results/significance.csv` (paired comparisons, 95% CI, p-values).
