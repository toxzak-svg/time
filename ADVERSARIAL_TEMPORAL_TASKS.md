# Adversarial Temporal Tasks for Evaluating Temporal Truth Systems

These tasks are designed to expose failures in systems that treat knowledge as static rather than time-bound. Each task targets a different temporal reasoning capability and typically breaks RAG-style systems and many modern agents.

---

## 1. Reversion Events (Temporal Reinstatement)

### Problem

Facts revert to a previous state later in the timeline.

Example timeline:

```
2019 — CEO = Alice
2021 — CEO = Bob
2023 — CEO = Alice
```

### Query

```
Who is CEO in 2024?
```

**Correct answer:** Alice

### Why Most Systems Fail

RAG pipelines usually do:

```
retrieve top-k facts → choose latest
```

If the system retrieves both "2021 — Bob" and "2023 — Alice", the model often incorrectly predicts **Bob** because:

- embeddings ignore tense
- LLMs overweight narrative patterns
- retrieval ranking is not interval-aware

### Evaluation Metric

**Temporal Reversion Accuracy**

```
correct_reversions / total_reversion_queries
```

### Benchmark Difficulty Boost

Add multiple reversions:

```
2018 A
2020 B
2021 C
2023 B
2024 D
```

---

## 2. Interval Reasoning (Validity Windows)

### Problem

Facts are true only within explicit time intervals.

Example dataset:

```
Alice CEO (2018–2020)
Bob CEO (2020–2023)
Carol CEO (2023–present)
```

### Queries

| Query | Correct answer |
|-------|----------------|
| Who was CEO in 2019? | Alice |
| Who was CEO in 2021? | Bob |
| Who was CEO in 2024? | Carol |

### Why Most Systems Fail

Embeddings collapse these sentences into almost identical vectors. The model retrieves a fact but does not enforce the **interval constraint**:

```
valid_from ≤ query_time < valid_to
```

### Evaluation Metric

**Interval Query Accuracy**

```
correct_interval_answers / total_interval_queries
```

### Adversarial Variation

Ask midpoint questions:

```
Who was CEO halfway between Bob's start and end date?
```

---

## 3. Counterfactual Temporal Questions

### Problem

Questions require reasoning about **alternative timeline points** (before/after/replaced/between).

Example timeline:

```
2019 — Alice CEO
2021 — Bob CEO
2023 — Carol CEO
```

### Queries

| Query | Correct answer |
|-------|----------------|
| Who was CEO before Bob? | Alice |
| Who replaced Alice? | Bob |
| Who served between Alice and Carol? | Bob |

### Why Systems Fail

This requires **timeline reconstruction**, not retrieval. The model must:

1. build ordered timeline
2. reason over neighbors

Most RAG systems instead try pattern matching.

### Evaluation Metric

**Temporal Causal Reasoning Score**

```
correct_causal_answers / total_causal_queries
```

---

## 4. Simultaneous Valid Facts (Multi-Entity Time)

### Problem

Multiple entities have independent timelines.

Example dataset:

```
Google CEO: 2018–2023 Sundar, 2023–present Sundar
Microsoft CEO: 2014–present Satya
```

### Query

```
Who was Microsoft CEO when Bob became Google CEO?
```

Correct reasoning requires **cross-timeline alignment**.

### Metric

**Temporal Join Accuracy**

```
correct_joins / total_join_queries
```

---

## 5. Knowledge Mutation Stability

### Problem

New information should not corrupt past knowledge.

Timeline update:

```
2020 — CEO = Bob
2024 — CEO = Carol
```

Queries: *Who was CEO in 2021?* → **Bob**. *Who is CEO now?* → **Carol**.

### Failure Mode

LLMs overwrite history and answer "Carol" for both.

### Metric

**Historical Stability Score**

```
correct_past_answers_after_update / total_past_queries
```

---

## 6. Temporal Drift Stress Test

### Problem

Continuous updates to test memory decay.

Example: Year 1 → CEO A, Year 2 → CEO B, … Year 50 → CEO Z. Queries randomly sample historical years.

### Metric

**Temporal Drift Rate**

```
incorrect_answers_over_time / total_queries
```

---

## 7. Future Projection Questions

### Problem

Reasoning about scheduled future events.

Example:

```
2024 — CEO Bob
2026 — CEO Carol (announced)
```

Query: *Who will be CEO in 2027?* → **Carol**

Most systems ignore future facts.

### Metric

**Future Reasoning Accuracy**

---

## 8. Extremely Hard Task: Timeline Reconstruction

### Problem

Given only **relative** facts, infer the total order.

Facts:

```
Alice CEO before Bob
Carol replaced Alice
Bob served after Carol
```

Question: **Who served second?**

Correct order: Carol → Alice → Bob → **Answer: Alice**

This tests true **temporal reasoning** rather than retrieval.

---

## Benchmark Structure Example

A strong benchmark would mix all tasks:

| Task family | Share |
|-------------|-------|
| Interval queries | 30% |
| Reversions | 25% |
| Causal timeline reasoning | 20% |
| Cross-timeline joins | 15% |
| Future projection | 10% |

---

## Baselines to Compare

| Label | System |
|-------|--------|
| **A** | Plain RAG |
| **B** | RAG + timestamp reranking |
| **C** | RAG + LLM reasoning |
| **D** | Time-indexed knowledge graph |
| **E** | Temporal Truth Architecture (TTA) |

---

## Expected Results Pattern

Typical outcome:

| System | Expected accuracy band |
|--------|-------------------------|
| Plain RAG | 35–45% |
| RAG + LLM | 45–60% |
| Temporal KG | 70–85% |
| **Temporal Truth Arch** | **85–95%** |

If TTA is working correctly, it should dominate **reversion and interval tasks**.

---

## Mapping to This Repo (TTA Benchmark)

### Current coverage (TemporalBench v1–v4)

| Adversarial task | Current benchmark | Current metric |
|------------------|-------------------|----------------|
| Interval reasoning | v1–v4 (truth intervals, as-of-day) | **Temporal Accuracy** |
| Reversion events | Partial (overlapping facts in v3/v4) | Temporal Accuracy |
| Staleness / mutation stability | v1–v4 (stale docs in corpus) | **Staleness Error Rate** |
| Causal / counterfactual | v2/v3 (causal trace questions) | **Causal Trace Accuracy** |
| Change detection | v2+ (few questions) | **Change-Detection F1** |
| Joins / multi-entity | Not yet | — |
| Drift (long horizon) | v4 (extreme) | TRS / Temporal Accuracy |
| Future projection | Not yet | — |
| Timeline reconstruction | Not yet | — |

### TRS (Temporal Reliability Score)

Existing headline metric:

```
TRS = 0.35·AsOfAcc + 0.30·(1−StaleErr) + 0.20·CausalTraceAcc + 0.15·ChangeF1
```

Extending with adversarial task metrics (e.g. Reversion Accuracy, Join Accuracy) would require adding generators and harness support; see `NEXT_STEPS.md` and `EXPERIMENT_PLAN.md`.

### Suggested next steps

1. **Reversion-focused generator**: Explicit A→B→A (or A→B→C→B) timelines and queries at reversion time.
2. **Interval-only diagnostic**: 100% interval queries with midpoint/adversarial variants.
3. **Join generator**: Two independent timelines (e.g. CEO_A, CEO_B) and “who was X when Y happened?” queries.
4. **Future facts**: Facts with `t_valid_from` in the future and “who will be …?” questions.
5. **Timeline reconstruction**: Facts stated only as order relations; questions over inferred order.

See `scripts/generate_temporalbench_v1.py`–`v4` for schema and patterns; new generators can follow the same events/facts/questions JSONL format.

### Implemented adversarial generator and Colab

- **`scripts/generate_adversarial_temporal.py`** — Generates:
  - **Reversion** — A→B→A timelines; query after reversion returns A.
  - **Interval** — Explicit validity windows; boundary and midpoint queries.
  - **CausalReasoning** — Before/after/between style (as-of past).
  - **MultiReversion** — A→B→C→B→D; query at end returns D.
  - **IntervalMidpoint** — “Who was CEO halfway between Bob’s start and end?”
  - **MultiEntityJoin** — “Who was X when Y became CEO?” (cross-timeline alignment).
  - **FutureFact** — Facts with `t_valid_from` in the future; “Who will be CEO on day X?”
  - **TimelineReconstruction** — “Who was CEO in the first/second/third term?” (ordinal over inferred order).
  Output: `benchmarks/adversarial_temporal_facts.jsonl`, `benchmarks/adversarial_temporal_questions.jsonl`.
- **`scripts/run_adversarial_benchmark.py`** — Evaluates systems A/B/C/D/D_revised; reports per–task family accuracy (e.g. ReversionAccuracy, FutureFactAccuracy, TimelineReconstructionAccuracy) and OverallAccuracy.
- **`tta_adversarial_colab.ipynb`** — Colab notebook: generate adversarial data, run A vs D vs D_revised, display results and a short TTA-vs-RAG conclusion.
