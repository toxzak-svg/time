# time

Concrete experiment specification for evaluating **Temporal Truth Architecture (TTA)** against current time-aware agent baselines is documented in:

- `EXPERIMENT_PLAN.md`

## Initial implementation

Started implementation for the Week 1 plan:

- `scripts/generate_temporalbench_v1.py` generates synthetic events, facts, and as-of QA prompts.
- `scripts/run_benchmark.py` runs an initial A/B/C/D benchmark harness and writes `results/main_table.csv`.

### Quickstart

```bash
python3 scripts/generate_temporalbench_v1.py
python3 scripts/run_benchmark.py
```
