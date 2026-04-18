# time

Concrete experiment specification for evaluating **Temporal Truth Architecture (TTA)** against current time-aware agent baselines:

- `EXPERIMENT_PLAN.md`

## Initial implementation status

This repository now includes a minimal Week 1 bootstrap for the plan:

- `scripts/generate_temporalbench_v1.py`: synthetic `TemporalBench-v1` dataset generator with events, truth-interval facts, and QA tasks.
- `scripts/run_benchmark.py`: lightweight benchmark harness producing an initial `results/main_table.csv` for Baseline A, Baseline C, and a TTA-core proxy.

## Quickstart

Generate a minimal reproducible benchmark dataset:

```bash
python3 scripts/generate_temporalbench_v1.py \
  --duration-days 60 \
  --events 1000 \
  --questions 500 \
  --output benchmarks/temporalbench_v1.jsonl
```

Run the benchmark harness:

```bash
python3 scripts/run_benchmark.py \
  --input benchmarks/temporalbench_v1.jsonl \
  --output results/main_table.csv
```
