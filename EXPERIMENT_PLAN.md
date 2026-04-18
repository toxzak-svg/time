# Temporal Truth Architecture (TTA) vs Current Baselines: Concrete Experiment

## 1) Hypothesis
A time-first agent (truth intervals + immutable event log + domain-adaptive decay) will significantly outperform strong non-temporal and temporal-aware baselines on:
- **as-of-time correctness**,
- **stale-fact avoidance**,
- **causal traceability of decisions to outcomes**.

## 2) Systems Compared (same base model stack)
Use one shared LLM, one embedding model, and one retrieval budget for all systems.

1. **Baseline A — Plain RAG Agent**
   - ReAct/tool-use agent
   - vector retrieval only
   - timestamps as metadata only
   - no temporal filtering, no decay

2. **Baseline B — Temporal-Aware Retrieval Agent**
   - temporal features in retrieval/reranking
   - optional timeline summarization
   - no immutable self-history

3. **Baseline C — Time-Constraint Retrieval Agent**
   - explicit retrieval filter for query time window
   - no learned domain decay
   - no policy/event causality model

4. **System D — TTA Agent (proposed)**
   - facts as truth intervals
   - append-only causal event ledger
   - domain-specific learned confidence decay
   - policy timeline + causal query layer

## 3) Dataset Design (TemporalBench-v1)
### Simulated evolving world
- **Duration**: 60 simulated days
- **Domains** (different update rates):
  - Slow: hardware/spec facts
  - Medium: model/API pricing + capability updates
  - Fast: incidents/status/docs changes
- **Scale target**:
  - ~5,000 events/facts total
  - ~2,000 evaluation questions

### Event schema
```json
{
  "event_id": "...",
  "t_event": "...",
  "t_observed": "...",
  "domain": "slow|medium|fast",
  "event_type": "FACT_OBSERVED|FACT_SUPERSEDED|ACTION|OUTCOME|POLICY_UPDATE",
  "subject": "...",
  "value": "...",
  "supersedes": "optional_event_id",
  "source_reliability": 0.0
}
```

### Fact schema
```json
{
  "fact_id": "...",
  "content": "...",
  "t_valid_from": "...",
  "t_valid_until": "...",
  "domain": "...",
  "confidence": 1.0,
  "decay_fn": "domain_half_life"
}
```

## 4) Task Families
1. **As-of-time QA**
   - "As of day 18, what was true about X?"
2. **Change detection**
   - "What changed between day 10 and day 30?"
3. **Staleness resistance**
   - adversarially include high-similarity but outdated docs
4. **Causal self-history**
   - "Which policy change caused outcome Y later?"
5. **Long-horizon temporal memory**
   - ordering/relative-time queries across 20–100 sessions

### 4b) Adversarial task taxonomy

A fuller set of adversarial temporal tasks (reversion events, interval reasoning, counterfactual/causal questions, multi-entity joins, knowledge mutation stability, drift, future projection, timeline reconstruction) is specified in **`ADVERSARIAL_TEMPORAL_TASKS.md`**. That doc also gives:
- per-task evaluation metrics
- a suggested benchmark mix (e.g. 30% interval, 25% reversion, 20% causal, 15% joins, 10% future)
- an expected results pattern: Plain RAG 35–45%, RAG+LLM 45–60%, Temporal KG 70–85%, TTA 85–95%

Current TemporalBench v1–v4 cover a subset; extending with reversion-focused, join, and timeline-reconstruction generators is described there and in `NEXT_STEPS.md`.

## 5) Metrics
### Primary
- **Temporal Accuracy** (correct relative to requested time)
- **Staleness Error Rate** (invalidated fact asserted as current)
- **Change-Detection F1**
- **Causal Trace Accuracy**
- **Temporal Calibration Error** (confidence vs fact age)

### Secondary
- latency
- token cost
- retrieval calls
- storage overhead

### Headline metric
**Temporal Reliability Score (TRS)**

\[
TRS = 0.35\cdot AsOfAcc + 0.30\cdot(1-StaleErr) + 0.20\cdot CausalTraceAcc + 0.15\cdot ChangeF1
\]

## 6) Training / Evaluation Protocol
1. Build all 4 systems with identical underlying model stack.
2. Split timeline:
   - **Days 1–40**: fit decay parameters / tune prompts
   - **Days 41–60**: strict held-out evaluation
3. Run each system with **3 random seeds**.
4. Report mean ± std.
5. Perform paired significance tests (paired t-test + bootstrap CI).

## 7) Required Ablations (TTA only)
Run TTA variants removing one component at a time:
- no truth intervals
- no domain-adaptive decay (global decay only)
- no event log (mutable state only)
- no temporal query filter

Goal: show which mechanism drives gains.

## 8) Success Criteria (publishable threshold)
Treat these as preregistered targets:
- **+10–20 points** Temporal Accuracy vs Plain RAG
- **>=50% reduction** in Staleness Error Rate vs Plain RAG
- clear lead in Causal Trace Accuracy vs all baselines
- latency within acceptable tradeoff (e.g., <=25% increase)

## 9) Fast Execution Plan (2-week sprint)
### Week 1
- implement data generator + schemas
- implement Baselines A/C + TTA core
- generate v1 corpus (1,000 events, 500 QA)

### Week 2
- add Baseline B
- run full 60-day protocol
- produce tables + core figure:
  - x-axis: fact age
  - y-axis: answer accuracy
  - lines: A/B/C/D

## 10) Deliverables
- `benchmarks/temporalbench_v1.jsonl`
- `scripts/run_benchmark.py`
- `results/main_table.csv`
- `results/ablation_table.csv`
- `figures/accuracy_vs_fact_age.png`
- one-page experimental report with claim + error analysis

