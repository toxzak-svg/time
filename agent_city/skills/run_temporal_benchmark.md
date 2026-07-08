# Skill: Run Temporal Benchmark

Use this skill when you need to **run temporal benchmarks** (adversarial or main TTA v1–v4) or **read results** so the city can learn from accuracy metrics. Covers: adversarial task families, main benchmark by version, multi-seed runs, significance, and figures.

## When to use

- User asks for benchmark results, OverallAccuracy, or per–task family accuracy (Reversion, Interval, FutureFact, TimelineReconstruction, etc.).
- You need to compare systems A, B, C, D, or D_revised.
- User wants main TTA benchmark (v1–v4), multi-seed stats, significance tests, or accuracy-vs-age figures.
- You are documenting an experiment for Moltbook or for spawning a child agent.

All commands below are run from the **repository root**. When your workspace is `agent_city/workspaces/<name>/`, the repo root is **two levels up** (`../../`). Prefix with: `cd ../../ && `.

---

## 1. Adversarial temporal benchmark (recommended for city)

**Generate data:**

```bash
cd ../../ && python scripts/generate_adversarial_temporal.py --out-dir benchmarks
```

**Run harness:**

```bash
cd ../../ && python scripts/run_adversarial_benchmark.py --facts benchmarks/adversarial_temporal_facts.jsonl --questions benchmarks/adversarial_temporal_questions.jsonl --out results/adversarial_temporal_results.csv --systems A,B,C,D,D_revised
```

- **Output:** `results/adversarial_temporal_results.csv` — columns: system, ReversionAccuracy, N_Reversion, IntervalAccuracy, …, FutureFactAccuracy, TimelineReconstructionAccuracy, OverallAccuracy, N_total.

---

## 2. Main TTA benchmark (v1–v4)

Generate and run a single version (e.g. v1):

```bash
cd ../../ && python scripts/generate_temporalbench_v1.py
cd ../../ && python scripts/run_benchmark.py --out results/v1_main_table.csv --systems A,B,C,D,D_revised
```

Other versions (v2, v3, v4) use different fact/question/event files; generate first, then:

```bash
python scripts/run_benchmark.py --facts benchmarks/temporalbench_v3_facts.jsonl --questions benchmarks/temporalbench_v3_questions.jsonl --events benchmarks/temporalbench_v3_events.jsonl --out results/v3_main_table.csv --systems A,B,C,D,D_revised
```

- **Ablation:** add `--ablation` for D vs D_no_decay, D_no_intervals, D_no_rerank.
- **Semantic systems (E, E_hybrid):** add `--semantic` (requires `sentence-transformers`).

---

## 3. Multi-seed and significance

**Multi-seed (v1–v4, seeds 0,1,2):**

```bash
cd ../../ && python scripts/run_benchmark_multi_seed.py --seeds 0,1,2 --versions v1,v2,v3,v4 --systems A,B,C,D,D_revised
```

- **Outputs:** `results/per_seed_results.csv`, `results/main_table_multi_seed.csv` (mean ± std).

**Significance (paired t-test, bootstrap 95% CI):**

```bash
cd ../../ && pip install -q scipy
cd ../../ && python scripts/compute_significance.py --per-seed-csv results/per_seed_results.csv --out results/significance.csv
```

---

## 4. Figures (accuracy vs fact age)

```bash
cd ../../ && pip install -q matplotlib
cd ../../ && python scripts/generate_accuracy_figure.py --out figures/accuracy_vs_fact_age.png
```

- **By version:** `--version v3 --out figures/accuracy_vs_fact_age_v3.png`
- **Combined (v1–v4 faceted):** `--combined --out figures/accuracy_vs_fact_age.png` → writes `figures/accuracy_vs_fact_age_combined.png`

---

## What you can do

1. **Execute** any of the above commands from repo root (e.g. via shell or run script tool).
2. **Read** output CSVs and summarize: best system, per–task or per-version accuracy, mean ± std, significance.
3. **Report** results to the user or prepare a short summary for Moltbook (see `agent_city/skills/moltbook_publish.md`).

## Boundaries

- Do not modify `--facts`, `--questions`, or `--events` paths to point at untrusted or altered data. Use only the repo’s benchmark data.
- Do not change the benchmark scripts or fact/question JSONL from within this skill.
