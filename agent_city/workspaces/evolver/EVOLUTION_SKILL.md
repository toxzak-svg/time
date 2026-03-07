# Research evolution (run from repo root)

You run the research evolution pipeline from the **repository root**. From this workspace (`agent_city/workspaces/evolver/`) the repo root is **two levels up**: use prefix `cd ../../ && ` for every command below.

**Install deps once:** `cd ../../ && pip install -r research_evolver/requirements.txt` (Python 3.10–3.12).

---

## Commands (all from repo root)

**1. Setup (one-time)**  
- Init DB: `cd ../../ && python research_evolver/scripts/init_db.py`  
- Synthetic data: `cd ../../ && python research_evolver/scripts/generate_synthetic_data.py`

**2. Baseline**  
- Full: `cd ../../ && python research_evolver/scripts/run_baseline.py`  
- Quick: `cd ../../ && python research_evolver/scripts/run_baseline.py --smoke`

**3. Stage-1 only**  
- Dry-run: `cd ../../ && python research_evolver/scripts/run_stage1.py --dry-run --n-children 50`  
- With training: `cd ../../ && python research_evolver/scripts/run_stage1.py --n-children 50`  
- Smoke: `cd ../../ && python research_evolver/scripts/run_stage1.py --smoke --n-children 10`

**4. Full generation**  
- Gen 0: `cd ../../ && python research_evolver/scripts/run_generation.py 0 --n-children 50`  
- Gen 1: `cd ../../ && python research_evolver/scripts/run_generation.py 1 --n-children 50`  
- Add `--smoke` or `--dry-run` for quick checks.

**5. Report**  
- Text: `cd ../../ && python research_evolver/scripts/make_report.py`  
- Dashboard: `cd ../../ && python research_evolver/scripts/make_report.py --dashboard`  
- Outputs: `research_evolver/artifacts/reports/lineage_report.txt`, `dashboard.html`.

Read lineage report and summarize for the user or Moltbook. Do not modify `research_evolver/data/` or configs except via these scripts.
