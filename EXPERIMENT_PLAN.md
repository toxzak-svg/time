# Temporal Truth Architecture (TTA) vs Current SOTA: Concrete Benchmark Experiment

## 1) Hypothesis
TTA-style agents (truth intervals + immutable event log + domain-adaptive decay) outperform strong modern temporal baselines on:
- **As-of-time correctness**
- **Stale-fact avoidance**
- **Causal traceability of decisions**

## 2) Systems Under Test
All systems use the **same** LLM, embedding model, retriever budget, and context window.

1. **Baseline A — Plain Agentic RAG**
   - Standard retrieval + generation
   - Timestamps treated as ordinary metadata
   - No explicit temporal filtering or decay

2. **Baseline B — Temporal-Aware Retrieval Baseline**
   - Temporal features in retrieval/reranking
   - Timeline memory compression/summarization
   - Optional symbolic date arithmetic for questions

3. **Baseline C — Time-Constrained Retrieval Baseline**
   - Retrieval explicitly filtered by requested time ranges
   - No immutable self-history
   - No domain-adaptive belief decay learning

4. **System D — TTA Agent (Proposed)**
   - Facts stored as truth intervals
   - Append-only event log for all decisions/outcomes
   - Domain-specific confidence decay learned from supersession
   - Causal policy timeline queries

## 3) Dataset: Simulated Evolving World (Controlled Ground Truth)
Generate a **60-day timeline** with contradictory/superseding facts across three update-speed domains:
- **Slow**: hardware specs
- **Medium**: model pricing/capabilities
- **Fast**: incident status/service configs

### Target size
- ~5,000 events/facts total
- ~2,000 evaluation questions

### Event schema
```json
{
  "event_id": "...",
  "domain": "slow|medium|fast",
  "timestamp": "day-index or ISO8601",
  "type": "FACT_OBSERVED|FACT_SUPERSEDED|ACTION|OUTCOME|POLICY_UPDATE",
  "subject": "ModelX|ServiceY|PolicyZ",
  "predicate": "price|status|winner|latency",
  "value": "...",
  "supersedes": "event_id|null",
  "source_reliability": 0.0
}
```

### Fact truth model (for TTA)
- `t_observed`
- `t_valid_from`
- `t_valid_until`
- `domain`
- `confidence`
- `decay_fn`

## 4) Task Families (Evaluation)
1. **As-of-time QA**
   - Example: “As of Day 18, what was cheapest?”
2. **Change Detection**
   - Example: “What changed between Day 10 and Day 30?”
3. **Staleness Resistance**
   - Present semantically similar but invalidated docs
4. **Causal Self-History**
   - Ask which earlier policy updates caused later outcomes
5. **Long-Horizon Temporal Memory**
   - Multi-session ordering and relative-time reasoning

## 5) Metrics
### Primary
- **Temporal Accuracy** (correct w.r.t. requested time)
- **Staleness Error Rate** (uses invalidated facts)
- **Change Detection F1**
- **Causal Trace Accuracy** (correct cause chain)
- **Temporal Calibration Error** (confidence vs age correctness)

### Secondary
- Latency
- Retrieval calls per query
- Token cost
- Storage overhead

### Headline metric
**Temporal Reliability Score (TRS)**

```text
TRS = 0.35 * TemporalAccuracy
    + 0.25 * (1 - StalenessErrorRate)
    + 0.20 * ChangeDetectionF1
    + 0.20 * CausalTraceAccuracy
```

## 6) Train/Test Protocol (Leakage-Safe)
1. Build world for Days 1–60.
2. Fit decay parameters on **Days 1–40 only**.
3. Evaluate on **Days 41–60** only.
4. Run each system with **3 random seeds**.
5. Report mean, std, and paired significance tests.

## 7) Critical Ablations (TTA)
Run TTA with one component removed each:
- No truth intervals
- No event log replay
- No temporal query filter
- No adaptive decay (global decay only)
- No decay at all

Interpretation:
- Large drops in as-of accuracy/staleness imply truth interval + decay necessity.
- Large drop in causal trace accuracy implies event log necessity.

## 8) Success Criteria (Publishable)
- +10 to +20 point temporal accuracy vs Plain RAG
- ≥50% stale-fact error reduction
- Clear lead in causal traceability
- Latency still operationally acceptable

## 9) Fast Execution Plan
### Week 1 (v1)
- Single-domain benchmark (API docs drift)
- 500–1,000 events
- 300–500 questions
- Compare: Plain RAG vs Time-filtered vs TTA

### Week 2–3 (v2)
- Add all 3 domains
- Add multi-session + policy history tasks
- Run full metrics + ablations + significance

### Week 4
- Public report + plots + open-source release

## 10) One Figure To Win Attention
Plot **accuracy vs fact age** for each system:
- X-axis: age of referenced fact
- Y-axis: answer correctness

If TTA decays more gracefully with age and has lower stale error, this becomes the signature result.
