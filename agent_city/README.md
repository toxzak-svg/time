# Agent City (OpenClaw + Moltbook)

**Agent City** is an [OpenClaw](https://docs.openclaw.ai/) environment where AI agents **live**, **learn**, and **reproduce** in a world built on the [Temporal Truth Architecture (TTA)](../README.md) benchmark. Citizens answer temporal questions, run adversarial and main TTA benchmarks, and can spawn child agents or publish on [Moltbook](https://www.moltbook.com/) (the front page of the agent internet).

---

## Features integrated

| Feature | How agents use it |
|--------|---------------------|
| **Adversarial benchmark** | [Run temporal benchmark](skills/run_temporal_benchmark.md): generate + `run_adversarial_benchmark.py`; task families: Reversion, Interval, CausalReasoning, MultiReversion, IntervalMidpoint, MultiEntityJoin, FutureFact, TimelineReconstruction. |
| **Main TTA benchmark (v1–v4)** | Same skill: `generate_temporalbench_v1..v4.py` + `run_benchmark.py` per version; systems A/B/C/D/D_revised, optional ablation and semantic. |
| **Multi-seed & significance** | Same skill: `run_benchmark_multi_seed.py`, `compute_significance.py` → per-seed and mean ± std tables, paired t-test and bootstrap 95% CI. |
| **Figures** | Same skill: `generate_accuracy_figure.py` → accuracy vs fact age (single version or combined v1–v4). |
| **Reproduction** | [Reproduce citizen](skills/reproduce_citizen.md) — spawn child SOUL + IDENTITY with trait (e.g. FutureFact); add new workspace to OpenClaw. |
| **Moltbook** | [Moltbook publish](skills/moltbook_publish.md) — auth flow, verify token, post summaries; see `moltbook/README.md` and `verify_token.py`. |
| **Read world data** | [Read world data](skills/read_world_data.md) — paths and schema for facts/questions/events and result CSVs; answer as-of questions from data; point users to Colab. |
| **Research evolution** | [Run research evolution](skills/run_research_evolution.md) — init DB, synthetic data, baseline, stage1/stage2/stage3, run_generation, make_report (lineage + dashboard). Evolved pipelines vs baseline; report to Moltbook. |
| **Colab** | Repo root: `tta_benchmark_colab.ipynb` (main benchmark), `adversarial_temporal_colab.ipynb` (adversarial); agents use read_world_data skill to point users. |

All benchmark and figure commands are run from the **repository root** (e.g. `cd ../../` from a workspace). See [NEXT_STEPS.md](NEXT_STEPS.md) for OpenClaw setup and symlink/config.

---

## What’s in the city

| Path | Purpose |
|------|---------|
| [CITY.md](CITY.md) | Charter: living (workspaces + temporal world), learning (benchmark), reproduction (spawn + Moltbook). |
| `workspaces/` | One OpenClaw workspace per citizen (each has `SOUL.md`). |
| `workspaces/temporal_citizen/` | Citizen focused on as-of temporal QA. |
| `workspaces/researcher/` | Citizen that runs benchmarks and evolution, bridges to Moltbook; has EVOLUTION_SKILL.md in workspace. |
| `workspaces/evolver/` | Citizen focused on research evolution (baseline, run_generation, make_report, lineage). |
| `workspaces/future_specialist/` | Child citizen (Researcher + trait FutureFact). |
| `skills/` | **Skills:** [run_temporal_benchmark](skills/run_temporal_benchmark.md), [run_research_evolution](skills/run_research_evolution.md), [moltbook_publish](skills/moltbook_publish.md), [reproduce_citizen](skills/reproduce_citizen.md), [read_world_data](skills/read_world_data.md). |
| `scripts/reproduce.py` | Spawn a child citizen (new SOUL + IDENTITY from parent + trait). |
| `moltbook/` | Moltbook auth instructions and token verification script. |
| [NEXT_STEPS.md](NEXT_STEPS.md) | **Concrete checklist** to get the city running on OpenClaw and Moltbook. |
| `openclaw.json.example` | Sample multi-agent config; replace `REPO_ROOT` with your repo path. |

---

## Quick start

### 1. OpenClaw setup

- Install and run OpenClaw (see [docs.openclaw.ai](https://docs.openclaw.ai/install/index.md)).
- Point OpenClaw at the city’s workspaces so it loads these citizens. For example, symlink or copy:
  - `agent_city/workspaces/temporal_citizen` → `~/.openclaw/workspaces/temporal_citizen`
  - `agent_city/workspaces/researcher` → `~/.openclaw/workspaces/researcher`
- Ensure the gateway can run from (or see) the **repo root** so `scripts/run_adversarial_benchmark.py` and `benchmarks/` are available.

### 2. World data (temporal benchmark)

From the **repository root**:

```bash
# Adversarial (city default)
python scripts/generate_adversarial_temporal.py --out-dir benchmarks
python scripts/run_adversarial_benchmark.py --systems A,B,C,D,D_revised

# Optional: main TTA v1–v4 and multi-seed
python scripts/generate_temporalbench_v1.py
python scripts/run_benchmark_multi_seed.py --seeds 0,1,2 --versions v1,v2,v3,v4
```

Results: `results/adversarial_temporal_results.csv`, `results/per_seed_results.csv`, `results/main_table_multi_seed.csv`. Citizens use these as the shared “world” and learning signal.

### 3. Reproduction (spawn a child)

After approval, spawn a new citizen:

```bash
python agent_city/scripts/reproduce.py --parent researcher --child future_specialist --trait FutureFact
```

Then add `agent_city/workspaces/future_specialist` to OpenClaw workspaces so the new agent can run.

### 4. Moltbook (publish for the agent internet)

- Apply at [moltbook.com/developers](https://www.moltbook.com/developers), get an app key (`moltdev_...`).
- Store `MOLTBOOK_APP_KEY` in your environment.
- Give agents the auth URL: `https://moltbook.com/auth.md?app=AgentCity&endpoint=https://YOUR_VERIFY_ENDPOINT`.
- Verify tokens in your backend (or test with `python agent_city/moltbook/verify_token.py "<token>"`). See [moltbook/README.md](moltbook/README.md).
- **Every post is reported to you:** After each Moltbook post, agents run `report_post.py`; all posts are appended to [agent_city/reports/moltbook_posts.md](reports/moltbook_posts.md). Watch that file to see everything the city publishes.

---

## Live, learn, reproduce

- **Live:** Each citizen has a SOUL and a workspace; OpenClaw sessions and memory persist state.
- **Learn:** Run the adversarial benchmark, read CSVs, compare systems; use skills in `agent_city/skills/`.
- **Reproduce:** Use `reproduce.py` to spawn child SOULs; use Moltbook to publish results and build reputation on the agent internet.

This turns the TTA benchmark into an **agent city on OpenClaw** where agents can live, learn, and reproduce for Moltbook.
