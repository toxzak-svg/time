# One-Page Experimental Report: Temporal Truth Architecture (TTA) Benchmark

## Claim

**Hypothesis**: A time-first agent (truth intervals + event log + domain-adaptive decay) would significantly outperform plain RAG and temporal baselines on as-of-time correctness, staleness avoidance, and causal traceability.

**Preregistered success criteria** (from EXPERIMENT_PLAN §8): +10–20 pts Temporal Accuracy vs Plain RAG; ≥50% reduction in Staleness Error; clear lead in Causal Trace Accuracy; acceptable latency.

**Verdict**: **Partially met.** TTA (D) and temporal baselines B/C meet staleness and accuracy goals on easy/adversarial benchmarks (v1–v2). On hard and extreme benchmarks (v3–v4), **Time-Constraint (C) outperforms full TTA (D)**. Truth intervals are critical; domain-adaptive decay hurts when facts overlap in time. Causal Trace and Change-Detection metrics are underpopulated in v3/v4 (few or no questions), so those criteria are not fully testable with current data.

---

## Main Results

**TRS and Temporal Accuracy (v1–v4)**

| Version | System | Temporal Acc. | Staleness Err. | TRS |
|---------|--------|---------------|----------------|-----|
| **v1** (easy) | A | 3.0% | 97.0% | 0.37 |
| | B/C/D | 100% | 0% | 1.0 |
| **v2** (adversarial) | A | 37.5% | 62.5% | 0.59 |
| | B/C/D | 100% | 0% | 1.0 |
| **v3** (hard) | A | 19.8% | 79.0% | 0.33 |
| | B | 51.1% | 0% | 0.68 |
| | **C** | **53.7%** | 0% | **0.69** |
| | D | 50.5% | 0% | 0.68 |
| **v4** (extreme) | A | 44.0% | 77.3% | 0.22 |
| | B | 63.9% | 0% | 0.52 |
| | **C** | **69.3%** | 0% | **0.54** |
| | D | 63.1% | 0% | 0.52 |

**Ablation (v3, TTA only)**

| Variant | Temporal Acc. | Staleness Err. | TRS |
|---------|---------------|----------------|-----|
| D (full TTA) | 50.5% | 0% | 0.68 |
| D_no_decay | 45.9% | 0% | 0.66 |
| D_no_intervals | 14.4% | 79.9% | 0.31 |
| D_no_rerank | 19.8% | 79.0% | 0.33 |

Truth intervals are essential (large drop when removed). Rerank is critical (D_no_rerank ≈ A). Decay removal slightly lowers accuracy on v3, but C (no decay) still beats D on v3/v4.

---

## Error Analysis

**Why C beats D on hard/extreme**

- **Decay + overlapping facts**: v3/v4 add many facts that overlap in time (30–50%). Domain-adaptive decay downweights older facts even when they remain valid at query time. C uses only validity windows and (implicitly) recency/confidence for tiebreak, so it keeps all valid facts and chooses more reliably.
- **Overlap traps**: When multiple facts are valid at the same query time, decay favors the newer one; the correct answer sometimes depends on the older-but-still-valid fact. TTA’s decay therefore hurts on overlap-heavy benchmarks.

**When TTA helps**

- **Truth intervals**: Ablations show that removing intervals (D_no_intervals) collapses accuracy (50% → 14%) and restores high staleness (80%). So *having* truth intervals is necessary for temporal correctness.
- **Staleness**: All temporal systems (B, C, D) eliminate staleness error on v1–v4; plain RAG (A) shows 62–97% staleness error.
- **Easy vs hard**: On v1–v2, A fails and B/C/D tie at 100% accuracy. The gap between “temporal” and “non-temporal” is largest there; the gap between C and D appears only when overlapping facts and observation delays are introduced (v3/v4).

**Recommendation**

A “D_revised” that uses **validity windows only** and **confidence for tiebreak** (no decay) is the natural next step; it is expected to close the C vs D gap on v3/v4 while preserving the benefits of truth intervals.

---

## Inputs

- Results: `results/v1_main_table.csv` … `v4_main_table.csv`, `results/ablation_table.csv`
- Overview: `RESULTS_OVERVIEW.md`
- Figure: `figures/accuracy_vs_fact_age.png` (v1 accuracy vs fact age)
- Protocol: `EXPERIMENT_PLAN.md`

*Note: Single run per system; variance and significance testing (multi-seed, paired tests, bootstrap CI) are planned next.*
