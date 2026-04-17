# The System A Paradox: How Accurate AI Systems Be Blind to Recent Facts

**Temporal Reasoning in Production RAG — A Problem Nobody Is Talking About**

*Zachary Maronek — Measuring Progress Toward AGI | April 2026*

---

## The Paradox

A memory system scores 92% overall accuracy on temporal questions — then fails 73% of the time on queries about *what is true right now*. It gets perfect marks on "what changed" and "why did it change" — but cannot answer "what is current."

This is System A. It is not a hypothetical edge case. It is the default architecture of most production RAG deployments.

---

## What the Benchmark Tests

TemporalBench evaluates memory systems across **10 task families** and **398,370 questions** spanning 5 versions and 3 random seeds. The benchmark is designed to be adversarial: each question's domain contains 90–98% irrelevant facts (high noise), forcing systems to identify temporal relevance — not just semantic similarity.

The 10 task families:
- **AsOfQA**: What is true at time T? (primary test)
- **OverlapQuery**: Which of multiple competing facts is current?
- **ChangeDetection**: What changed between T1 and T2?
- **DecayTrap**: Does the system suppress outdated facts?
- **CausalTrace**: Can the system identify what caused a change?
- **TemporalOrdering**: Which fact is newer?
- **TemporalReasoning**: Multi-step temporal inference
- *(and 3 additional variants)*

Each question includes a time-indexed fact store, a query timestamp, and an expected answer derived from the fact with the most recent valid_until timestamp.

---

## Finding 1: The Staleness Signal

The critical differentiator between systems is not overall accuracy — it's near-present accuracy.

| System | Near-present (recency ≥ 0.9) | Far-past (recency < 0.5) | Gap |
|--------|------------------------------|--------------------------|-----|
| System A | **27.3%** | 33.3% | **−6.0 pp** |
| System B | 72.6% | 76.7% | −4.1 pp |
| System C | 74.7% | 79.1% | −4.4 pp |
| System D | 72.5% | 76.1% | −3.6 pp |

System A gets *worse* at near-present facts than far-past ones. Every other system gets slightly worse on recent facts too, but from a much higher base — and the magnitude is much smaller.

The temporal_distance correlation confirms this:

| System | r(temporal_distance, accuracy) |
|--------|-------------------------------|
| System A | **−0.129** (3.7× stronger) |
| Systems B/C/D | ≈ −0.035 |

System A's accuracy is far more sensitive to how old the target fact is. This is the staleness problem — it knows facts exist but cannot determine which version is current.

---

## Finding 2: OverlapQuery — The Sharpest Divider

When multiple facts exist for the same subject, the systems diverge catastrophically:

| System | OverlapQuery Accuracy |
|--------|----------------------|
| System C | **100.0%** |
| System B | 88.5% |
| System D | 86.3% |
| System A | **2.2%** |

System A gets this wrong 98% of the time. Given competing values for the same entity, it defaults to the wrong one almost always. System C's perfect score means it has a reliable mechanism for determining which fact supersedes the others.

---

## Finding 3: Causal Attribution ≠ Temporal Indexing

System A gets perfect scores on ChangeDetection (F1 = 1.0) and CausalTrace (Accuracy = 1.0). It can track what changed and why. But it fails on AsOfQA.

This reveals that temporal reasoning is two distinct capabilities:

1. **Temporal tracking** — knowing which version of a fact is current (validity windows)
2. **Causal attribution** — knowing what caused a change (change detection)

System A has causal attribution but lacks temporal indexing. It knows *what changed* and *why* — but not *when that change is true until*. This is why it gets high overall accuracy on causal tasks while failing catastrophically on recency tasks.

---

## Why Existing Approaches Fail

### Decay Functions

Decay functions (exponential, recency-weighted, time-since-read) treat older facts as lower priority. The problem: an old fact that was *superseded* should score 0, not just lower. Decay functions have no mechanism to distinguish "old but still valid" from "old and superseded."

System A — which uses a decay-inspired approach — performs at 27.3% on near-present queries because the decay function correctly down-weights old facts, but incorrectly allows superseded facts to remain retrievable when no newer fact has accumulated enough weight.

### Semantic Search

Semantic similarity search amplifies the retrieval paradox: when a user asks about a topic they've queried before, the system retrieves the most *semantically similar* prior context — regardless of temporal validity. The retrieved context may be fluent, relevant-sounding, and confidently wrong.

### Production Systems

- **LangChain WindowMemory**: Scores 7/10. Finite context window with no temporal encoding — old facts expire mechanically regardless of validity.
- **Mem0**: Scores 7/10. Recency-weighted semantic memory — good signal, no validity gating.
- **TimeAwareRAG**: Scores 8/10. Adds time-decay to retrieval but lacks hard validity windows.
- **SimpleRAG**: Scores 6/10. Pure semantic retrieval with no temporal awareness.

---

## The Fix: Validity Windows

The systems that score 10/10 (D_revised, HybridStore) use a different mechanism: **validity windows** as hard constraints on retrieval.

```
score(f, t_query) = validity_window(f, t_query) × retrieval_score(f, t_query)

where validity_window(f, t) = 1 if valid_from ≤ t ≤ valid_to, else 0
```

A fact is retrieved only if the query timestamp falls within its validity window. Not "lower score if older" — **excluded entirely if superseded**. This is the critical architectural difference.

**The implementation challenge**: validity_window requires knowing valid_from and valid_to for each fact. Three approaches work:

1. **Explicit temporal markers**: facts are stored with (valid_from, valid_to) at write time — the system records when each fact became and ceased being true
2. **Causal chaining**: when a new fact contradicts an old one, the system marks the old fact's valid_to = new_fact's valid_from
3. **Change-point detection**: analyze the fact sequence to detect discontinuities that signal a superseded value

All three require the system to reason about *time*, not just *relevance*.

---

## Key Results Summary

| Feature | System A | Systems B/C/D |
|---------|----------|---------------|
| Near-present accuracy | 27.3% | 72–75% |
| OverlapQuery accuracy | 2.2% | 86–100% |
| ChangeDetection F1 | 1.0 | 1.0 |
| CausalTrace accuracy | 1.0 | 1.0 |
| Temporal distance correlation | −0.129 | ≈ −0.035 |

**Primary insight**: The dominant factor in temporal benchmark performance is not compression ratio, noise handling, or causal reasoning — it is whether the system maintains an explicit temporal index (validity windows) that lets it answer "what is true now?" with high confidence.

Validity windows beat decay functions. This finding converges with recent results from contextual-flux research (structured state +15.8% correctness over summaries, p<0.0001) and temporal Phase 2 analysis (D_revised > D on hard versions).

---

## Implications for AGI

The systems that will succeed at temporal reasoning are those that:

1. **Track explicit validity intervals** — not just relevance scores — on stored facts
2. **Treat causal attribution and temporal indexing as separate subsystems** — a system that solves one does not automatically solve the other
3. **Gate retrieval on temporal validity** — letting soft retrieval scores modulate hard temporal constraints, not replace them

System A is not broken. It is genuinely useful for causal reasoning tasks. But it cannot answer "what is true now?" because it was never architected to track validity intervals. Building that awareness — not adding more context or better embedding models — is what closes the gap.

---

## Try It Yourself

The benchmark, evaluation code, and Phase 2 analysis are available at:
- **Benchmark data**: temporalbench dataset on Kaggle (benchmarks/)
- **Evaluator notebook**: adversarial_temporal_colab.ipynb
- **Phase 2 analysis**: phase2_correlation.py (run on 398K questions)
