# Next Steps for TTA Benchmark Project

Based on `EXPERIMENT_PLAN.md`, `RESULTS_OVERVIEW.md`, and current deliverables.

---

## 1. Missing deliverable (high priority)

**One-page experimental report** (Section 10 of EXPERIMENT_PLAN) ✅

- **Done**: `EXPERIMENTAL_REPORT.md` — claim, main results (TRS/Temporal Acc v1–v4 + ablation), error analysis.
- **Action** (if expanding): Add:
  - **Claim**: Summary of hypothesis and whether TTA met the preregistered success criteria.
  - **Main result**: TRS and Temporal Accuracy across A/B/C/D for v1–v4; ablation summary.
  - **Error analysis**: Why C beats D on hard/extreme (decay + overlapping facts); when TTA helps (truth intervals critical).
- **Inputs**: `RESULTS_OVERVIEW.md`, `results/*.csv`, `figures/accuracy_vs_fact_age.png`.

---

## 2. Protocol gaps (medium priority)

**Multiple seeds and uncertainty** (Section 6) ✅

- **Done**: `scripts/run_benchmark_multi_seed.py` runs with configurable seeds (default `0,1,2`) and versions (v1–v4), writes `results/per_seed_results.csv` and `results/main_table_multi_seed.csv` with mean ± std per metric.

**Significance testing** (Section 6) ✅

- **Done**: `scripts/compute_significance.py` reads per-seed results and outputs paired t-test and bootstrap 95% CI for TRS and Temporal Accuracy (e.g. D vs A, D vs C, D_revised vs D) to `results/significance.csv`.

---

## 3. TTA improvements (research priority)

From `RESULTS_OVERVIEW.md`:

- **Decay**: On v3/v4, domain-adaptive decay hurts (C > D). Consider:
  - **Option A**: Remove decay from D; use validity windows only and confidence for tiebreak.
  - **Option B**: Redesign decay so it does not downweight valid overlapping facts (e.g. decay only beyond `t_valid_until`, or domain-specific rules for overlap).
- **Scoring**: Use confidence only to break ties among facts that are valid at query time.
- **Domain tuning**: Separate handling or tuning for fast vs slow domains.

**Done**: Implemented one “D_revised” variant (e.g. validity-only + tiebreak), multi-seed v3 shows D_revised matches C and outperforms D.

---

## 4. Figures and analysis (medium priority)

**Accuracy vs fact age** (Section 9) ✅

- **Done**: `scripts/generate_accuracy_figure.py` supports `--version v1|v2|v3|v4` and `--combined` for a faceted figure (v1–v4) at `figures/accuracy_vs_fact_age_combined.png`. Temporal question types for all versions are included.

**Change detection** ✅

- **Done**: Added 50 ChangeDetection questions to v3 generator; harness already evaluates them. v3 runs now report non-zero ChangeDetectionF1 when applicable.

---

## 5. Housekeeping (low priority)

- **README** ✅: Updated with v1–v4 generators, multi-version and multi-seed run instructions, significance script, figures, and pointers to `RESULTS_OVERVIEW.md` and `EXPERIMENTAL_REPORT.md`.
- **Colab**: `tta_benchmark_colab.ipynb` — documented in README; clone repo then run generate + `run_benchmark.py`.
- **Cleanup**: Canonical single-run tables are `results/v*_main_table.csv`; multi-seed outputs are `results/per_seed_results.csv`, `results/main_table_multi_seed.csv`, `results/significance.csv`. Documented in README.

---

## Suggested order of work

| Order | Task | Effort |
|-------|------|--------|
| 1 | Write one-page experimental report | Small | ✅ |
| 2 | Add 3-seed runs + mean ± std to harness and tables | Medium | ✅ |
| 3 | Implement D_revised (validity-only + tiebreak), run v3/v4 | Medium | ✅ |
| 4 | Add significance tests (paired t-test + bootstrap CI) | Medium | ✅ |
| 5 | Extend accuracy-vs-age figure to v2/v3/v4 or combined | Small | ✅ |
| 6 | Update README and optional change-detection questions | Small | ✅ |

This order closes the main deliverable first, then strengthens the evaluation protocol, then iterates on TTA design and presentation.

---

## 6. Adversarial temporal tasks (optional expansion)

**Reference**: `ADVERSARIAL_TEMPORAL_TASKS.md` — full spec for 7 task types + one “extremely hard” (timeline reconstruction).

- **Current coverage**: v1–v4 already stress interval reasoning, staleness, and some causal trace; reversion appears implicitly via overlapping facts.
- **Possible extensions** (see mapping table in that doc):
  - Reversion-focused generator (explicit A→B→A timelines).
  - Interval-only / midpoint diagnostic set.
  - Multi-entity join generator (“who was X when Y?”).
  - Future-fact and “who will be …?” questions.
  - Timeline reconstruction (relative-order facts only; infer order and answer “who served second?”).

If you add a Colab experiment that highlights TTA vs RAG on these tasks (e.g. reversion or interval in &lt;5 min), it can be linked from the README or from `ADVERSARIAL_TEMPORAL_TASKS.md`.
