# TemporalBench: Concrete Experiment Plan for TTA vs Current SOTA

## 1) Hypothesis
Temporal Truth Architecture (TTA) agents outperform strong baselines on:
- **As-of temporal accuracy** (what was true at time `T`)  
- **Staleness resistance** (avoiding invalidated facts)  
- **Causal traceability** (linking outcomes to prior decisions)

## 2) Systems Under Test
Use the **same base LLM, embedding model, retriever budget, and prompt budget** for all systems.

### A. Plain Strong Agent (baseline)
- ReAct/tool-use style agent
- Standard vector RAG
- Timestamps only as metadata
- No temporal filter, no decay modeling

### B. Time-Aware Retrieval Baseline (TReMu/Memory-T1 style)
- Temporal-aware retrieval
- Timeline summarization/compression
- Optional symbolic date reasoning step
- No immutable self-evolution log

### C. Temporal-Constraint Retrieval Baseline (TempAgent style)
- Retrieval constrained by explicit time windows
- No domain-learned decay
- No policy evolution timeline

### D. TTA Agent (proposed)
- Fact truth intervals (`t_valid_from`, `t_valid_until`)
- Append-only immutable event log
- Domain-adaptive confidence decay
- Policy version history + causal links
- Temporal query engine (`facts_valid_at(T)`, `policy_at(T)`, `causal_chain(e)`)

## 3) Dataset: Simulated Evolving World (Ground-Truth Known)
Create a **60-day timeline** with **~5,000 events/facts** across three update-speed domains:

1. **Slow-changing**: hardware capabilities/specs
2. **Medium-changing**: model pricing/features/rankings
3. **Fast-changing**: incidents, issue states, service status

Each event row should include:
- `event_time`
- `observation_time`
- `fact_id`
- `domain`
- `statement`
- `supersedes_fact_id` (nullable)
- `source_reliability`
- `valid_from`, `valid_until`

This enables exact labels for:
- true-at-time-T
- stale-at-time-T
- what-changed-between-T1-T2
- supersession chain correctness

## 4) Task Suite (2,000 QA items)
### Task Family 1: As-of-Time QA
Examples:
- “As of Day 18, what was the cheapest model?”
- “Was GPU-A still the fastest on Day 33?”

### Task Family 2: Change Detection
Examples:
- “What changed between Day 10 and Day 30?”
- “Which claim about Model-B was invalidated first?”

### Task Family 3: Staleness Resistance
Inject highly similar outdated docs and ask current-state questions:
- “What is the current endpoint?”
- “Which version is currently supported?”

### Task Family 4: Causal Self-History
Multi-episode policy updates with delayed outcomes:
- “Which policy update caused latency improvements on Day 22?”
- “When did the routing strategy shift?”

### Task Family 5: Long-Context Temporal Memory
20–100 session histories with recurring entities:
- “Did migration occur before or after incident X?”
- “When did the user first report bug Y relative to patch Z?”

## 5) Metrics
### Primary
- **Temporal Accuracy**
- **Staleness Error Rate**
- **Change Detection F1**
- **Causal Trace Accuracy**
- **Temporal Calibration Error** (confidence vs age)

### Secondary
- Latency
- Retrieval calls/query
- Token cost
- Storage overhead

### Headline Metric: Temporal Reliability Score (TRS)
A weighted score:

`TRS = w1*TemporalAccuracy + w2*(1-StalenessErrorRate) + w3*CausalTraceAccuracy + w4*ChangeF1`

Recommended initial weights: `w1=0.35, w2=0.30, w3=0.25, w4=0.10`.

## 6) Critical Ablations (on TTA)
1. Remove truth intervals
2. Remove domain-adaptive decay
3. Replace domain decay with single global decay
4. Remove temporal query filter
5. Remove append-only event log (use mutable state)

Expected findings:
- Biggest drops in as-of/stale metrics when removing truth intervals/decay
- Biggest drop in causal trace accuracy when removing event log

## 7) Protocol (Reproducible)
1. Fix model stack for all systems
2. Generate 60-day world + tasks
3. Fit decay parameters **only** on Days 1–40
4. Evaluate on Days 41–60 (held-out updates)
5. Run 3 seeds per system
6. Report mean, std, and paired significance tests

Suggested significance tests:
- Paired bootstrap for accuracy differences
- McNemar for paired classification outcomes
- Wilcoxon signed-rank for per-query score deltas

## 8) Concrete “Win Conditions”
A strong result threshold:
- +10 to +20 points temporal accuracy vs plain RAG
- >=50% lower stale-answer rate vs plain RAG
- Clear lead in causal trace accuracy
- Latency within practical bounds (even if modestly higher)

## 9) Minimal Build Path
### v1 (fastest)
- 1 domain (e.g., evolving API docs)
- 500–1,000 events
- 300–500 questions
- 3 systems (Plain RAG, Temporal Filter, TTA)

### v2 (paper/demo)
- Add multi-domain world
- Add self-history causal tasks
- Add domain-adaptive decay learning
- Full 4-system comparison + ablations

## 10) Deliverables for Credibility + Notoriety
1. **Open-source repo** with generator, runners, and scorer
2. **Public benchmark card** (task definitions + schema)
3. **One memorable figure**: accuracy vs fact-age decay curve
4. **Reproducibility artifact**: fixed seeds + config files
5. **Short paper**: methods + ablations + error analysis

## 11) Recommended Repo Layout
```text
temporalbench/
  data_gen/
    world_generator.py
    task_generator.py
  systems/
    plain_rag.py
    temporal_retrieval.py
    temp_constrained.py
    tta_agent.py
  eval/
    metrics.py
    significance.py
    run_suite.py
  configs/
    base_model.yaml
    dataset_v1.yaml
  docs/
    benchmark_card.md
```

## 12) One-Sentence Public Positioning
**“Knowledge without time is incomplete: TemporalBench shows that treating time as a first-class causal dimension materially reduces stale errors and improves time-indexed reasoning in LLM agents.”**
