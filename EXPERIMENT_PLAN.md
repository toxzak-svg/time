# Temporal Truth Architecture (TTA) vs Current SOTA: Concrete Experiment

## Objective
Validate the claim that **time-first agents** outperform strong baselines on temporal reasoning, stale-fact avoidance, and causal traceability.

> Core hypothesis: A TTA agent (truth intervals + immutable event log + domain-adaptive decay) will significantly improve temporal reliability versus modern time-aware retrieval baselines.

---

## 1) Systems Under Test
Use the **same LLM, embedding model, retrieval budget, and context window** for all systems.

### A. Plain Agent Baseline (Strong Non-Temporal)
- ReAct/tool-using loop
- Standard vector RAG
- Timestamps only as passive metadata
- No explicit temporal filtering
- No learned decay

### B. Time-Aware Retrieval Baseline (TReMu/Memory-T1 style)
- Timeline-aware memory summarization
- Temporal features during retrieval/reranking
- Optional symbolic date arithmetic module
- No immutable self-history

### C. Time-Constrained Retrieval Baseline (TempAgent style)
- Retrieval filtered by explicit time constraints from query
- Time-constrained reranking
- No domain-adaptive confidence decay
- No policy lineage/event-sourced self-model

### D. TTA Agent (Proposed)
- Facts as truth intervals: `(content, t_observed, t_valid_from, t_valid_until, domain, confidence, decay_fn)`
- Append-only event log for all agent decisions/outcomes
- Domain-specific learned half-life / decay parameters
- Temporal query engine (`facts_valid_at(T)`, `policy_at(T)`, `causal_chain(event_id)`)
- Versioned policy history

---

## 2) Data: Simulated Evolving World (Ground-Truth Known)
Build a 60-day synthetic-but-realistic timeline with controlled supersession.

### Domains (different change rates)
1. **Slow**: hardware/spec facts (e.g., GPU architecture capabilities)
2. **Medium**: model pricing, benchmark standings, product limits
3. **Fast**: service incidents, API status, deployment flags

### Scale targets
- ~5,000 total events/facts
- ~2,000 evaluation questions
- Each event has:
  - `event_time`
  - `observation_time`
  - `valid_from`
  - `valid_until` (or open-ended)
  - `supersedes_event_id` (nullable)
  - `source_reliability`
  - `domain`

### Leakage control
- Fit/learn decay parameters using **Days 1–40 only**.
- Evaluate on **Days 41–60** with held-out updates.

---

## 3) Task Families
Use five task families to directly test the claimed strengths.

### T1. As-of-Time QA
Examples:
- “As of Day 18, what was the cheapest model?”
- “Was Service-X endpoint `/v2` active on Day 33?”

### T2. Change Detection
Examples:
- “What changed between Day 10 and Day 30?”
- “Which capability became invalid first for Model-B?”

### T3. Staleness Resistance
Setup:
- Present highly similar outdated and current docs together.
- Ask for **current** truth.

Examples:
- “What is the current rate limit?”
- “Which API version is currently supported?”

### T4. Causal Self-History / Policy Trace
Multi-episode tasks where the agent policy changes and outcomes lag.

Examples:
- “Which policy update most likely caused latency drop at Day 22?”
- “When did routing strategy change from P2 to P3?”

### T5. Long-History Temporal Memory
20–100 session histories with recurring entities and date references.

Examples:
- “Did migration occur before or after incident Alpha?”
- “When was the bug first reported relative to patch deployment?”

---

## 4) Metrics

### Primary
1. **Temporal Accuracy (TA)**
   - Correctness with respect to requested time `T`
2. **Staleness Error Rate (SER)**
   - Fraction of answers using invalidated facts
3. **Change-Detection F1 (CDF1)**
4. **Causal Trace Accuracy (CTA)**
   - Correctness of cited cause chain vs ground truth DAG
5. **Temporal Calibration Error (TCE)**
   - Miscalibration between confidence and fact age/validity

### Secondary
- End-to-end latency
- Retrieval calls per query
- Token usage / cost
- Storage overhead (event log + fact metadata)

### Headline Score: Temporal Reliability Score (TRS)
Normalize each metric to [0,1], then:

`TRS = 0.35*TA + 0.25*(1-SER) + 0.20*CDF1 + 0.15*CTA + 0.05*(1-TCE)`

(Weights can be sensitivity-tested in appendix.)

---

## 5) Ablation Study (Critical for Causal Claim)
Run TTA variants:
1. TTA - domain-adaptive decay (global decay only)
2. TTA - truth intervals (single timestamp only)
3. TTA - event log (mutable state snapshot only)
4. TTA - temporal query filter
5. Full TTA

Expected signatures:
- Removing truth intervals or domain decay should sharply increase SER.
- Removing event log should collapse CTA.

---

## 6) Exact Experimental Protocol
1. Fix model stack and compute budget for all systems.
2. Generate the 60-day event world and QA set.
3. Freeze splits and evaluation harness before running agents.
4. Learn decay params on Days 1–40 only.
5. Evaluate on Days 41–60.
6. Run each system with **3 random seeds**.
7. Report mean ± std for all metrics.
8. Perform paired significance tests (paired bootstrap or paired t-test where appropriate).
9. Publish all prompts/configs for reproducibility.

---

## 7) Minimal v1 (Fastest Credible Path)
If speed is critical, do this first:
- 1 domain (evolving software/API docs)
- 500–1,000 events
- 300–500 QA items
- 3 systems: Plain RAG, Time-Filtered Retrieval, TTA
- Core metrics: TA, SER, TRS

This is enough to validate stale-fact reduction quickly.

---

## 8) Success Criteria (Publishable Threshold)
A persuasive outcome is:
- **+10 to +20 points TA** over plain baseline
- **>=50% reduction in SER**
- Clear CTA advantage over all non-event-sourced baselines
- Competitive latency (may be modestly slower than plain RAG)

---

## 9) Artifact Plan (for Notoriety + Credibility)
1. **Open-source repo** with harness + data generator + baseline implementations
2. **Benchmark release** (“TemporalBench”) with fixed test split
3. **Reproducible leaderboard** script
4. **Paper + demo video**

### Memorable Figure
Plot accuracy vs fact age:
- x-axis: fact age
- y-axis: temporal answer accuracy
- lines: Plain, Time-Aware Baseline, TTA

TTA should degrade more gracefully as facts age.

---

## 10) Recommended Repository Skeleton
```text
temporal-agent/
  core/
    event_log.py
    temporal_fact_store.py
    decay_model.py
    temporal_query_engine.py
  agent/
    reasoning_loop.py
    policy_manager.py
  benchmarks/
    world_generator.py
    temporalbench_tasks.py
    scoring.py
    run_suite.py
  baselines/
    plain_rag.py
    time_aware_retrieval.py
    time_constrained_retrieval.py
  configs/
    experiment.yaml
  docs/
    experiment_protocol.md
```

