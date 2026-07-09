# Research Evolution v1 — Build Status

**Source:** `research_evolution_implementation_blueprint.pdf`  
**Goal:** One task family, Qwen ~1.5B–1.7B, LoRA, 3-stage funnel, SQLite. Success = autonomous generations, best pipeline beats baseline on frozen holdout, improvement holds for ≥2 seeds, within budget, lineage explainable.

---

## Repository layout (scaffolded)

```
research_evolver/
  configs/          base.yaml, search_space.yaml, benchmarks.yaml
  data/             raw/, processed/, synthetic/; evolver.db
  artifacts/         experiments/, reports/
  models/
  src/
    core/            genome, mutations, fitness
    execution/       (training, eval, stage runners — stubs)
    memory/          schema.sql, db.py
    policy/          (selection, promotion — stubs)
    benchmarks/      (stubs)
    reporting/       (stubs)
    utils/
  scripts/           init_db, run_generation, run_stage1–3, make_report
```

---

## Implementation order (blueprint)

| Step | Component | Outcome | Status |
|------|------------|---------|--------|
| 1 | Genome + search space YAML | Valid experiment recipe, serializable and repairable | ✅ Scaffolded |
| 2 | Baseline trainer + evaluator | Locked baseline run; improvement measured from it | ✅ Implemented |
| 3 | SQLite schema + artifact writer | Persistent state, reproducible outputs | ✅ Schema + init_db |
| 4 | Mutator + stage-1 runner | Cheap child generation and ranking | ✅ Implemented |
| 5 | Generation loop + promotion logic | Full staged search over one generation | ✅ Implemented |
| 6 | Lineage tracking + dashboard | Human-readable ancestry and progress | ✅ lineage_report.txt + dashboard.html (make_report --dashboard) |
| 7 | Crossover + species + novelty | Broader search after mutation-only stable | ✅ Crossover + species_cap in config; novelty_score stub |

---

## Month-1 roadmap (weeks)

| Week | Focus | Deliverable | Gate |
|------|--------|-------------|------|
| 1 | Baseline path | Dataset loader, baseline fine-tune, proxy eval, holdout eval, DB init | One end-to-end baseline run reproduces cleanly |
| 2 | Mutation-only search | Genome schema, search-space config, mutator, stage-1 scheduler, generation report | ≥50 children generated, run, ranked |
| 3 | Promotion and survival | Stage-2 and stage-3 promotion, survivor logic, lineage tracking, simple dashboard | One full generation through all three stages |
| 4 | Search quality | Crossover, species cap, novelty score, mutation contribution report | First autonomous-evolution demo ready |

---

## Immediate next steps (from blueprint)

1. **Implement the baseline path first** — freeze it before any evolutionary search.
2. **Genome validation and repair** — implement fully before the mutator.
3. **Stage-1 extremely fast** — whole system depends on cheap early rejection.
4. **No crossover until** mutation-only generations produce sane lineages.
5. **First successful demo** = benchmarked systems result, not just a concept.

---

## How to run (current)

```bash
# From repo root

# 1. Init DB
python research_evolver/scripts/init_db.py

# 2. Generate minimal synthetic data (train/proxy/holdout JSONL)
python research_evolver/scripts/generate_synthetic_data.py

# 3. Run baseline (install deps first: pip install -r research_evolver/requirements.txt)
python research_evolver/scripts/run_baseline.py          # full run
python research_evolver/scripts/run_baseline.py --smoke # 10 steps, no GPU needed for quick check
```

**Mutation-only search (Step 4):**
```bash
# Spawn 50 children, run stage-1, rank, report (no GPU: dry-run only)
python research_evolver/scripts/run_stage1.py --dry-run --n-children 50

# With training (needs pip install -r research_evolver/requirements.txt and GPU for speed)
python research_evolver/scripts/run_stage1.py --n-children 50
python research_evolver/scripts/run_stage1.py --smoke --n-children 10  # 10 steps each, quick check
```

**Full generation and reporting:**
```bash
python research_evolver/scripts/run_generation.py 0 --n-children 50   # gen 0 (optional --smoke or --dry-run)
python research_evolver/scripts/run_generation.py 1 --n-children 50   # gen 1 (uses survivors from gen 0)
python research_evolver/scripts/make_report.py --dashboard             # lineage_report.txt + dashboard.html
```
Optional: run_stage2.py / run_stage3.py by hand for a given generation (after stage1 has been run).

**Note:** Full baseline run needs a compatible env (Python 3.10–3.12 recommended; `pip install -r research_evolver/requirements.txt`). The pipeline is implemented; failures due to torch/transformers/torchvision version mismatch are environment-specific.

---

## Success criteria (v1)

- [ ] System completes multiple generations without manual intervention between stages.
- [ ] Best evolved pipeline beats locked baseline on frozen holdout.
- [ ] Improvement survives at least two seeds.
- [ ] Result within declared compute budget.
- [ ] Winning lineage explainable at the field level.
