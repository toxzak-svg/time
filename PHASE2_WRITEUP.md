# TemporalBench: Phase 2 Analysis — Writeup Draft

## What We Tested

Phase 2 tested whether per-question characteristics (temporal distance, recency, fact density, overlap) correlate with model accuracy differently across systems.

**Dataset:** 398,370 questions across Systems A/B/C/D.
**Features:** temporal_distance (0–60 days), recency_score (0=oldest, 1=newest), subject_fact_count (4–54 facts per subject).

---

## Finding 1: System A Has a Staleness Problem

System A's accuracy correlates with temporal distance at **r = −0.129** — 3.7× stronger than Systems B/C/D (r ≈ −0.035). This means the older the fact being queried, the worse System A performs. B/C/D stay relatively flat across all time periods.

| System | Near-present accuracy (recency≥0.9) | Far-past accuracy (recency<0.5) | Gap |
|--------|--------------------------------------|--------------------------------|-----|
| A | **27.3%** | 33.3% | **−6.0 pp** |
| B | 72.6% | 76.7% | −4.1 pp |
| C | 74.7% | 79.1% | −4.4 pp |
| D | 72.5% | 76.1% | −3.6 pp |

System A is *worse at near-present than far-past* — the opposite of what decay-based models would predict. This is a world-model indexing failure: System A knows facts exist but cannot determine which version is current.

---

## Finding 2: OverlapQuery Reveals the Sharpest Divergence

When multiple facts compete for the same subject (OverlapQuery trap), System A fails catastrophically:

| System | OverlapQuery accuracy |
|--------|----------------------|
| A | **2.2%** |
| B | 88.5% |
| C | **100.0%** |
| D | 86.3% |

System C's perfect score on OverlapQuery suggests it has a working validity-window mechanism: it tracks which fact is current and suppresses conflicting older values. System A's 2.2% suggests it defaults to whichever value it encountered first, regardless of recency.

---

## Finding 3: Per-Version Accuracy Tells a Gradual Learning Story

System A shows a distinctive pattern: near-zero accuracy on early versions (v1–v3 = 0%), then a gradual climb reaching near-perfect on the newest versions (v51–v54). This is consistent with a system that learns facts one at a time without a temporal index — it stores each new fact but can't distinguish "this supersedes that" without explicit time markers.

Systems B/C/D show high accuracy throughout, with minor dips on mid-range versions (v42–v48), suggesting they handle most facts correctly but occasionally confuse validity windows in the middle temporal ranges.

---

## Implication for AGI Benchmarks

This pattern reveals that temporal reasoning is not a single capability — it's two distinct skills:

1. **Temporal tracking** — knowing which version of a fact is current (validity windows)
2. **Causal attribution** — knowing what caused a change (ChangeDetection, CausalTrace)

Systems B/C/D have both. System A has causal attribution (perfect ChangeDetection and CausalTrace scores) but lacks temporal tracking. This explains why System A can tell you *what changed* and *why* but cannot answer *what is true now*.

An AGI benchmark that doesn't separately measure these two sub-capabilities will fail to diagnose why a system is struggling. TemporalBench's deliberate 90–98% noise ratio forces systems to use temporal tracking to retrieve relevant facts — making it a specific probe for the validity window mechanism rather than general reasoning.

---

## Summary Table

| Feature | System A | Systems B/C/D |
|---------|----------|---------------|
| temporal_distance correlation | r = −0.129 | r ≈ −0.035 |
| Near-present accuracy | 27.3% | 72–75% |
| OverlapQuery accuracy | 2.2% | 86–100% |
| ChangeDetection F1 | 1.0 | 1.0 |
| CausalTrace accuracy | 1.0 | 1.0 |

**Conclusion:** The primary differentiator between systems is not compression ratio, causal reasoning, or noise handling — it's whether the system maintains an explicit temporal index (validity windows) that lets it answer "what is true now?" with high confidence. Validity windows beat decay functions. This finding converges with results from contextual-flux Experiment 04 (structured state +15.8% over summaries, p<0.0001).