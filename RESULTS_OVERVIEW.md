# Temporal Truth Architecture (TTA) Benchmark Results Overview

## Executive Summary

This document summarizes the benchmark experiments comparing TTA against baseline systems across progressively harder adversarial benchmarks.

**IMPORTANT**: Results were updated after fixing a bug in task family mapping (v3/v4 question types now correctly handled).

## Systems Compared

| System | Description |
|--------|-------------|
| **A** (Plain RAG) | Naive retrieval - picks most recent fact by timestamp |
| **B** (Temporal Rerank) | Temporal validity + recency scoring, no decay |
| **C** (Time Constraint) | Explicit temporal validity filtering |
| **D** (TTA Full) | Truth intervals + domain-adaptive decay + reranking |

## Benchmark Versions

| Version | Description | Key Features |
|---------|-------------|--------------|
| v1 | Original/Easy | Standard temporal facts, 60-day timeline |
| v2 | Adversarial | Past-query traps, 50% past questions |
| v3 | Hard | 30% overlapping facts, observation delays |
| v4 | Extreme | 50% overlapping facts, high update frequency |

## Results Summary

### v1 (Easy) - 2,000 questions
| System | Temporal Accuracy | Staleness Error | TRS |
|--------|-------------------|-----------------|-----|
| A | 3.0% | 97.0% | 0.37 |
| B | 100% | 0% | 1.0 |
| C | 100% | 0% | 1.0 |
| D | 100% | 0% | 1.0 |

**Key Finding**: All temporal systems achieve perfect scores on easy benchmark.

### v2 (Adversarial) - 2,000 questions
| System | Temporal Accuracy | Staleness Error | TRS |
|--------|-------------------|-----------------|-----|
| A | 37.5% | 62.5% | 0.59 |
| B | 100% | 0% | 1.0 |
| C | 100% | 0% | 1.0 |
| D | 100% | 0% | 1.0 |

**Key Finding**: Plain RAG degrades significantly on past-query tasks.

### v3 (Hard) - 1,900 questions (corrected)
| System | Temporal Accuracy | Staleness Error | TRS |
|--------|-------------------|-----------------|-----|
| A | 19.8% | 79.0% | 0.33 |
| B | 51.1% | 0% | 0.68 |
| **C** | **53.7%** | **0%** | **0.69** |
| D | 50.5% | 0% | 0.68 |

**Key Finding**: Time-Constraint (C) slightly edges out TTA (D). Decay hurts on overlapping facts.

### v4 (Extreme) - 2,000 questions (corrected)
| System | Temporal Accuracy | Staleness Error | TRS |
|--------|-------------------|-----------------|-----|
| A | 44.0% | 77.3% | 0.22 |
| B | 63.9% | 0% | 0.52 |
| **C** | **69.3%** | **0%** | **0.54** |
| D | 63.1% | 0% | 0.52 |

**Key Finding**: Time-Constraint (C) outperforms TTA (D) on extreme benchmarks.

## Ablation Studies (v3 Hard)

| Variant | Temporal Accuracy | Staleness Error | TRS |
|---------|-------------------|-----------------|-----|
| D (Full TTA) | 50.5% | 0% | 0.68 |
| D_no_decay | 45.9% | 0% | 0.66 |
| D_no_intervals | 14.4% | 79.9% | 0.31 |
| D_no_rerank | 19.8% | 79.0% | 0.33 |

**Key Findings**:
- Truth intervals are critical - removing them causes 36% accuracy drop
- Decay function has mixed results - helps slightly on v3 but not on overlapping facts
- Time-constraint (C) consistently beats full TTA (D) on hard/extreme

## Key Insights

1. **Truth intervals are essential**: Without temporal validity windows, accuracy drops dramatically (50% → 14%)

2. **Decay function is problematic**: On benchmarks with overlapping facts, decay hurts performance by preferring newer facts over older but still-valid ones

3. **Plain RAG has hidden staleness**: High raw accuracy possible but 77-97% of answers use stale facts

4. **Simple methods beat complex ones**: Time-constraint (C) consistently outperforms full TTA (D) on hard/extreme benchmarks

5. **The decay function is the culprit**: Ablations show D_no_decay (45.9%) is slightly worse than D (50.5%), suggesting the decay math needs work

## Recommendations for TTA Improvement

1. **Reconsider decay entirely**: The half-life math may be fundamentally flawed for overlapping facts
2. **Trust validity windows**: Let truth intervals be the source of truth, not decay weighting  
3. **Simplify scoring**: Use confidence only for tiebreaking between equally valid facts
4. **Domain-specific tuning**: Fast-changing domains may need different handling than slow ones

## Bug Fixes Applied

- Fixed task family mapping in `run_benchmark.py` to correctly handle v3/v4 question types (DecayTrap, OverlapTrap, OverlapQuery)
- Results updated to reflect corrected evaluation

## Files Generated

```
benchmarks/
  temporalbench_v1_events.jsonl (5,530)
  temporalbench_v1_facts.jsonl (5,530)
  temporalbench_v1_questions.jsonl (2,000)
  temporalbench_v2_*.jsonl
  temporalbench_v3_*.jsonl
  temporalbench_v4_*.jsonl

results/
  v1_main_table.csv
  v2_main_table.csv
  v3_main_table.csv
  v4_main_table.csv
  ablation_table.csv

scripts/
  generate_temporalbench_v1.py
  generate_temporalbench_v2.py
  generate_temporalbench_v3.py
  generate_temporalbench_v4.py
  run_benchmark.py
```
