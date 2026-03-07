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

**Multiple seeds and uncertainty** (Section 6)

- **Current**: Single run per system; no variance reported.
- **Action**: Run benchmark with 3 seeds (e.g. `--seed 0,1,2`), aggregate mean ± std per metric, and report in tables/figures.

**Significance testing** (Section 6)

- **Action**: Add paired comparisons (e.g. D vs A, D vs C) with paired t-test and bootstrap 95% CI for TRS / Temporal Accuracy so claims are statistically grounded.

---

## 3. TTA improvements (research priority)

From `RESULTS_OVERVIEW.md`:

- **Decay**: On v3/v4, domain-adaptive decay hurts (C > D). Consider:
  - **Option A**: Remove decay from D; use validity windows only and confidence for tiebreak.
  - **Option B**: Redesign decay so it does not downweight valid overlapping facts (e.g. decay only beyond `t_valid_until`, or domain-specific rules for overlap).
- **Scoring**: Use confidence only to break ties among facts that are valid at query time.
- **Domain tuning**: Separate handling or tuning for fast vs slow domains.

**Action**: Implement one “D_revised” variant (e.g. validity-only + tiebreak), re-run v3/v4 and ablations, and compare to C and current D.

---

## 4. Figures and analysis (medium priority)

**Accuracy vs fact age** (Section 9)

- **Current**: Single figure for v1 only (`figures/accuracy_vs_fact_age.png`).
- **Action**: Either:
  - Add accuracy-vs-age plots for v2/v3/v4, or
  - One combined figure (e.g. faceted by benchmark version) to show how the gap between A and B/C/D evolves with difficulty.

**Change detection**

- **Current**: ChangeDetectionF1 is 0 in results (no or few change-detection questions in current generators).
- **Action**: If change detection is required for the report, add change-detection questions to a generator (e.g. v2 or v3) and ensure the harness evaluates them; then report F1.

---

## 5. Housekeeping (low priority)

- **README**: Update with v2/v3/v4 generators, multi-version run instructions, and pointer to `RESULTS_OVERVIEW.md` and (once written) the one-page report.
- **Colab**: `tta_benchmark_colab.ipynb` — confirm it runs with current scripts and document in README if it’s the preferred way to run benchmarks.
- **Cleanup**: Decide whether `results/test_table.csv` and `results/main_table.csv` (vs versioned `v*_main_table.csv`) should be canonical and document in README.

---

## Suggested order of work

| Order | Task | Effort |
|-------|------|--------|
| 1 | Write one-page experimental report | Small |
| 2 | Add 3-seed runs + mean ± std to harness and tables | Medium |
| 3 | Implement D_revised (validity-only + tiebreak), run v3/v4 | Medium |
| 4 | Add significance tests (paired t-test + bootstrap CI) | Medium |
| 5 | Extend accuracy-vs-age figure to v2/v3/v4 or combined | Small |
| 6 | Update README and optional change-detection questions | Small |

This order closes the main deliverable first, then strengthens the evaluation protocol, then iterates on TTA design and presentation.
