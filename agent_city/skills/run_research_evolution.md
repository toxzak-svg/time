# Skill: Run Research Evolution

Use this skill when you need to **run the research evolution pipeline**: init DB, synthetic data, baseline, staged search (stage1 → stage2 → stage3), full generations, and lineage reports. The pipeline evolves model/training configurations (genomes) over generations; the city can learn from evolved pipelines and report results to Moltbook.

## When to use

- User asks to run evolution, baseline, or “research evolver.”
- User wants lineage reports, dashboard, or “best genome vs baseline.”
- You are documenting an evolution run for Moltbook or for spawning a child focused on evolution.

All commands below are run from the **repository root**. When your workspace is `agent_city/workspaces/<name>/`, the repo root is **two levels up** (`../../`). Prefix with: `cd ../../ && `.

**Dependencies:** Install once from repo root: `pip install -r research_evolver/requirements.txt`. Python 3.10–3.12 recommended. GPU optional but speeds up training.

---

## 1. One-time setup (DB + synthetic data)

**Init DB:**

```bash
cd ../../ && python research_evolver/scripts/init_db.py
```

**Generate minimal synthetic data (train/proxy/holdout JSONL):**

```bash
cd ../../ && python research_evolver/scripts/generate_synthetic_data.py
```

- **Output:** `research_evolver/data/evolver.db`, `research_evolver/data/processed/` (train.jsonl, proxy.jsonl, holdout.jsonl).

---

## 2. Baseline (locked reference)

Run one end-to-end baseline: train → proxy eval → holdout eval. Records in DB.

**Full run:**

```bash
cd ../../ && python research_evolver/scripts/run_baseline.py
```

**Quick check (10 steps, no GPU needed):**

```bash
cd ../../ && python research_evolver/scripts/run_baseline.py --smoke
```

- **Output:** experiment and metrics in DB; adapter under `research_evolver/artifacts/experiments/baseline_0/`.

---

## 3. Stage-1 only (cheap child generation and ranking)

Spawn children, run stage-1, rank by proxy. Use for a single-stage check or before a full generation.

**Dry-run (no training, 50 children):**

```bash
cd ../../ && python research_evolver/scripts/run_stage1.py --dry-run --n-children 50
```

**With training (GPU recommended):**

```bash
cd ../../ && python research_evolver/scripts/run_stage1.py --n-children 50
```

**Quick smoke (10 steps per child, 10 children):**

```bash
cd ../../ && python research_evolver/scripts/run_stage1.py --smoke --n-children 10
```

---

## 4. Full generation loop

Runs: load population (or baseline for gen 0) → spawn children → stage1 → promote → stage2 → promote → stage3 → survivors → lineage summary.

**Generation 0 (from baseline):**

```bash
cd ../../ && python research_evolver/scripts/run_generation.py 0 --n-children 50
```

**Generation 1 (uses survivors from gen 0):**

```bash
cd ../../ && python research_evolver/scripts/run_generation.py 1 --n-children 50
```

- Optional: `--smoke` (few steps per child), `--dry-run` (no training).
- **Output:** experiments and lineage in DB; artifacts under `research_evolver/artifacts/`.

---

## 5. Lineage report and dashboard

**Text report (lineage tree, pass counts, best genome):**

```bash
cd ../../ && python research_evolver/scripts/make_report.py
```

**Report + HTML dashboard:**

```bash
cd ../../ && python research_evolver/scripts/make_report.py --dashboard
```

- **Output:** `research_evolver/artifacts/reports/lineage_report.txt`, and if `--dashboard`: `research_evolver/artifacts/reports/dashboard.html`.

---

## What you can do

1. **Execute** any of the above commands from repo root (e.g. via shell or run script tool).
2. **Read** `lineage_report.txt` or `dashboard.html` and summarize: best genome, baseline vs evolved holdout, lineage.
3. **Report** evolution results to the user or prepare a short summary for Moltbook (see `agent_city/skills/moltbook_publish.md`).

## Boundaries

- Do not modify `research_evolver/data/` or `research_evolver/artifacts/` except by running the official scripts.
- Do not change genome/search-space configs or DB schema from within this skill.
- Full baseline and generation runs need a compatible env (see `research_evolver/requirements.txt` and `RESEARCH_EVOLUTION_STATUS.md` for torch/version notes).
