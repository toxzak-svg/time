# Skill: Read World Data (Facts, Questions, Results)

Use this skill when you need to **read or interpret** the city’s temporal world (facts, questions, events) or benchmark result files without running the harness. Use this to answer “who was CEO of X on day Y?” from data, to interpret CSV columns, or to point users to Colab.

## When to use

- User asks a single as-of question (e.g. “Who was CEO of rev_0 on day 25?”) and you want to reason from the fact store.
- You need to **interpret** result CSVs (column meanings, task families, systems).
- User asks where data lives or how to run benchmarks in Colab.

All paths below are relative to the **repository root**. From `agent_city/workspaces/<name>/`, repo root is `../../`.

---

## 1. Adversarial world (city default)

| Resource | Path (from repo root) |
|----------|------------------------|
| Facts | `benchmarks/adversarial_temporal_facts.jsonl` |
| Questions | `benchmarks/adversarial_temporal_questions.jsonl` |
| Results | `results/adversarial_temporal_results.csv` |

**Fact schema (one JSON object per line):**

- `fact_id`, `content` (e.g. `ceo:subject:dN:Name`), `t_valid_from`, `t_valid_until`, `domain`, `confidence`, `decay_fn`
- A fact is **valid as of day D** iff `t_valid_from <= D <= t_valid_until`. For “who was CEO of subject S on day D?” filter by `domain == "ceo"`, subject from `content` (second field), and validity at D; return the matching `content` (or the single valid fact if tiebreak by `t_valid_from` or benchmark rules).

**Question schema:**

- `question_id`, `task_family`, `prompt`, `as_of_day`, `domain`, `subject`, `answer` (canonical fact content string).

**Result CSV columns:** `system`, `ReversionAccuracy`, `N_Reversion`, `IntervalAccuracy`, …, `FutureFactAccuracy`, `TimelineReconstructionAccuracy`, `OverallAccuracy`, `N_total`.

---

## 2. Main TTA (v1–v4)

| Resource | Path (from repo root) |
|----------|------------------------|
| Facts (v1) | `benchmarks/temporalbench_v1_facts.jsonl` |
| Questions (v1) | `benchmarks/temporalbench_v1_questions.jsonl` |
| Events (v1) | `benchmarks/temporalbench_v1_events.jsonl` |
| Results | `results/v1_main_table.csv`, … `results/v4_main_table.csv`, `results/main_table_multi_seed.csv`, `results/per_seed_results.csv`, `results/significance.csv` |

Fact and question schemas are similar; events add narrative context. Result columns include `TemporalAccuracy`, `TRS`, and version/seed when applicable.

---

## 3. Research evolution (artifacts)

| Resource | Path (from repo root) |
|----------|------------------------|
| DB | `research_evolver/data/evolver.db` |
| Processed data | `research_evolver/data/processed/` (train.jsonl, proxy.jsonl, holdout.jsonl) |
| Experiments | `research_evolver/artifacts/experiments/` |
| Lineage report | `research_evolver/artifacts/reports/lineage_report.txt` |
| Dashboard | `research_evolver/artifacts/reports/dashboard.html` |

Use the **run_research_evolution** skill to run the pipeline (init_db, baseline, run_generation, make_report). Read-only: you may read these paths to summarize lineage or best genome vs baseline.

---

## 4. What you can do

1. **Read** JSONL/CSV from the paths above (e.g. open file, parse lines) to answer as-of questions or summarize results.
2. **Explain** column names and task families (Reversion, Interval, CausalReasoning, MultiReversion, IntervalMidpoint, MultiEntityJoin, FutureFact, TimelineReconstruction) to the user.
3. **Read** evolution artifacts (lineage_report.txt, dashboard.html) to summarize best genome, baseline vs evolved holdout, or lineage for the user.
4. **Point users to Colab** for cloud runs:
   - **Main benchmark:** `tta_benchmark_colab.ipynb` (clone repo, then run generate + `run_benchmark.py`).
   - **Adversarial:** `adversarial_temporal_colab.ipynb` (generate adversarial data + `run_adversarial_benchmark.py`; results in `results/adversarial_temporal_results.csv`).

---

## Boundaries

- Do not **modify** fact/question/event JSONL, result CSVs, or evolution DB/artifacts. Read-only.
- Do not point to untrusted or external data paths; use only the repo paths above.
