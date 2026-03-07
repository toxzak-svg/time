# time

Concrete experiment specification for evaluating **Temporal Truth Architecture (TTA)** against current time-aware agent baselines is documented in:

- **`EXPERIMENT_PLAN.md`** — hypothesis, systems, dataset design, metrics, protocol
- **`ADVERSARIAL_TEMPORAL_TASKS.md`** — adversarial task taxonomy (reversion, interval, causal, joins, drift, future, timeline reconstruction) and mapping to this benchmark

## Initial implementation

Started implementation for the Week 1 plan:

- `scripts/generate_temporalbench_v1.py` generates synthetic events, facts, and as-of QA prompts.
- `scripts/run_benchmark.py` runs an initial A/B/C/D benchmark harness and writes `results/main_table.csv`.

### Quickstart

```bash
python3 scripts/generate_temporalbench_v1.py
python3 scripts/run_benchmark.py
```

### Adversarial temporal tasks (Colab)

- **`tta_benchmark_colab.ipynb`** — Main benchmark (A/B/C/D and optional semantic systems) on TemporalBench v1–v4.
- **`adversarial_temporal_colab.ipynb`** — Adversarial tasks and metrics: Reversion, Interval, Causal Reasoning. Run `scripts/generate_adversarial_temporal.py` then `scripts/run_adversarial_benchmark.py`; results in `results/adversarial_temporal_results.csv`.
