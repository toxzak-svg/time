# What’s next: get Agent City running on OpenClaw and Moltbook

This checklist gets the city running end-to-end: OpenClaw with multiple citizens, benchmark from repo root, and optional Moltbook publishing.

---

## Current status (as you proceed)

| Step | Status | Notes |
|------|--------|--------|
| 1 Install OpenClaw | ✅ | Daemon, dashboard, `openclaw doctor` |
| 2 Telegram pairing | ⚙️ | Only if you see "access not configured"; run `openclaw pairing approve telegram <CODE>` |
| 3 Bootstrap workspaces | ✅ | All four citizens have `SOUL.md` + `IDENTITY.md`; `reproduce.py` creates both for new children |
| 4 Point OpenClaw at city | ✅ | `openclaw.json` has main + Researcher (default), Temporal Citizen, Evolver, Future Specialist; Webchat + Telegram → Researcher |
| 5 Run benchmark from repo root | ✅ | Skills use `cd ../../` or `AGENT_CITY_REPO`; run commands in §5 to verify |
| 6 Moltbook | ⚙️ | Optional: app key, verify endpoint, `report_post.py` → `reports/moltbook_posts.md` |
| 7 Verify | ⚙️ | Dashboard → ask Researcher to run benchmark; run `reproduce.py` to spawn a child; Moltbook when backend ready |

**Next:** Use the dashboard or Telegram to chat with Researcher; ask to “run the adversarial benchmark and report OverallAccuracy for system D.” For new citizens, run `python agent_city/scripts/reproduce.py --parent researcher --child <name> --trait <Trait>`, then add the workspace to `openclaw.json` if desired.

---

**Integration status:** OpenClaw is wired to the city so you can talk to it:

- **Config** (`~/.openclaw/openclaw.json`): Agents list includes **main** (your existing workspace) plus **Researcher**, **Temporal Citizen**, **Evolver**, **Future Specialist** (workspaces under `C:\dev\time\time\agent_city\workspaces\`). **Researcher** is the default agent.
- **Bindings:** **Webchat** (dashboard) and **Telegram** (default account) are bound to **Researcher**, so when you use the dashboard or Telegram you talk to the city (Researcher). Use the agent selector in the UI to switch to Main, Temporal Citizen, Evolver, or Future Specialist if needed.
- **Env:** `AGENT_CITY_REPO` and `MOLTBOOK_REPORT_PATH` are set; Moltbook posts are reported to `agent_city/reports/moltbook_posts.md`.

**To talk to the city:** Restart the gateway (`openclaw dashboard` or restart the daemon), then open the dashboard or Telegram. You’ll be routed to Researcher. If you get **auth errors** (e.g. OAuth/Codex) when using a city agent, copy the model auth from main: copy `~/.openclaw/agents/main/agent/auth-profiles.json` to `~/.openclaw/agents/researcher/agent/auth-profiles.json` (create the `agent` dir if needed), then retry.

---

## Use a .env file for API keys (recommended)

If you see **"Open AI not configured"** or API-key errors, use a `.env` file instead of putting secrets in `openclaw.json`:

1. **Copy the example** from this repo:
   ```powershell
   copy C:\dev\time\time\agent_city\.env.example %USERPROFILE%\.openclaw\.env
   ```
   (On macOS/Linux: `cp agent_city/.env.example ~/.openclaw/.env`.)

2. **Edit `%USERPROFILE%\.openclaw\.env`** and set at least:
   ```env
   OPENAI_API_KEY=sk-your-actual-key-here
   AGENT_CITY_REPO=C:\dev\time\time
   MOLTBOOK_REPORT_PATH=C:\dev\time\time\agent_city\reports\moltbook_posts.md
   ```

3. **Remove the key from config** so it comes only from `.env`: open `~/.openclaw/openclaw.json`, find the `env.vars` block, and delete the `OPENAI_API_KEY` line (and any other secrets). OpenClaw loads `~/.openclaw/.env` automatically and will use those values.

4. **Restart the gateway** (e.g. close the dashboard and run `openclaw dashboard` again).

OpenClaw’s env order: config `env` (if missing) → **`~/.openclaw/.env`** → `.env` in cwd → process env. So once the key is only in `.env`, it will be used. Keep `.env` out of git.

---

## 1. Install OpenClaw

- **Windows:** Prefer [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install); then use the Linux install. Or PowerShell:
  ```powershell
  iwr -useb https://openclaw.ai/install.ps1 | iex
  ```
- **macOS/Linux:**
  ```bash
  curl -fsSL https://openclaw.ai/install.sh | bash
  ```
- Then:
  ```bash
  openclaw onboard --install-daemon
  openclaw doctor
  openclaw dashboard
  ```

---

## 2. Approve access (Telegram pairing)

If you see **"OpenClaw: access not configured"** and have a pairing code (e.g. from Telegram):

- **If you are the OpenClaw bot owner / admin:** On a machine where the OpenClaw CLI is installed, run:
  ```bash
  openclaw pairing approve telegram SULCVN43
  ```
  (Use the actual pairing code you were given.) After approval, the user can access the bot.
- **If you are not the owner:** Send the pairing code and the approve command to whoever runs the OpenClaw instance so they can run the command above.

---

## 3. Bootstrap each citizen workspace

OpenClaw expects at least `SOUL.md` and `IDENTITY.md` in each workspace. This repo already has `SOUL.md` per citizen; add a minimal `IDENTITY.md` (or run `openclaw setup --workspace <path>` to seed).

- **Option A (recommended):** Copy the provided `IDENTITY.md` from each `agent_city/workspaces/<name>/` (see below) — they are already in the repo.
- **Option B:** From repo root:
  ```bash
  for name in temporal_citizen researcher future_specialist; do
    openclaw setup --workspace "$(pwd)/agent_city/workspaces/$name"
  done
  ```
  Then replace the generated `SOUL.md` with the city’s version (back up first).

---

## 4. Point OpenClaw at the city (multi-agent)

OpenClaw uses one **workspace per agent**. To run several citizens:

- **Option A — Symlink workspaces into OpenClaw state (default home):**

  Run from the **repository root**. If you use a custom OpenClaw home, set `OPENCLAW_HOME` and use that instead of `~/.openclaw` in the paths below.

  ```bash
  # Create OpenClaw state dir if it doesn't exist (e.g. before first run)
  mkdir -p ~/.openclaw

  ln -s "$(pwd)/agent_city/workspaces/temporal_citizen" ~/.openclaw/workspace-temporal_citizen
  ln -s "$(pwd)/agent_city/workspaces/researcher"       ~/.openclaw/workspace-researcher
  ln -s "$(pwd)/agent_city/workspaces/evolver"          ~/.openclaw/workspace-evolver
  ln -s "$(pwd)/agent_city/workspaces/future_specialist" ~/.openclaw/workspace-future_specialist
  ```
- **Option B — Config only:** In `~/.openclaw/openclaw.json` (or `OPENCLAW_CONFIG_PATH`), define multiple agents and point each to the city workspaces. A copyable example is in **`agent_city/openclaw.json.example`** — replace `REPO_ROOT` with the absolute path to this repo (e.g. `C:\dev\time\time` or `/home/user/time`). Then merge the `agents.list` entries into your existing config or use the example as a starting point.

Use the dashboard (or channel bindings) to choose which agent to chat with.

### Gateway vs nodes

| Role | Agents | Meaning |
|------|--------|--------|
| **Gateway** (bind to channels) | **Researcher**, optionally **Main** | These are the agents that receive traffic when a user opens the dashboard or messages Telegram. Bind Webchat and Telegram to **Researcher** (and/or Main) so the city has a single default “face.” |
| **Nodes** (no channel binding) | **Temporal Citizen**, **Evolver**, **Future Specialist** | These agents are not bound to any channel by default. Users can switch to them via the agent selector in the UI, or Researcher can hand off to them in conversation. They stay available as specialists. |

**Recommendation:** Bind only **Researcher** (and **Main** if you want your own workspace on the gateway). Leave **Temporal Citizen**, **Evolver**, and **Future Specialist** as nodes—selectable or handoff-only—so the default experience is one coherent “city” agent (Researcher) that can delegate when needed.

---

## 5. Run benchmark from repo root

Skills assume commands run from the **repository root** (where `scripts/` and `benchmarks/` live). Each citizen’s workspace is `agent_city/workspaces/<name>/`, so the repo root is **two levels up**: `../../`.

- **In skills / agent instructions:** Tell the agent to run from repo root, e.g.:
  ```bash
  cd ../../ && python scripts/run_adversarial_benchmark.py --facts benchmarks/adversarial_temporal_facts.jsonl --questions benchmarks/adversarial_temporal_questions.jsonl --out results/adversarial_temporal_results.csv --systems A,B,C,D,D_revised
  ```
- **Optional:** Set an env var for the gateway (or in `openclaw.json`) so the agent knows the repo root, e.g. `AGENT_CITY_REPO=/path/to/time`. Then the skill can say: “Run `cd $AGENT_CITY_REPO && python scripts/...`”.

**Adversarial (city default) — generate and run once:**

```bash
cd /path/to/time
python scripts/generate_adversarial_temporal.py --out-dir benchmarks
python scripts/run_adversarial_benchmark.py --systems A,B,C,D,D_revised
```

**Main TTA (v1–v4) and multi-seed (optional):**

```bash
cd /path/to/time
python scripts/generate_temporalbench_v1.py
python scripts/generate_temporalbench_v2.py
python scripts/generate_temporalbench_v3.py
python scripts/generate_temporalbench_v4.py
python scripts/run_benchmark_multi_seed.py --seeds 0,1,2 --versions v1,v2,v3,v4
pip install -q scipy && python scripts/compute_significance.py --per-seed-csv results/per_seed_results.csv --out results/significance.csv
```

**Research evolution (optional):**

Agents can run the evolution pipeline via the **run_research_evolution** skill. One-time setup then baseline and generations:

```bash
cd /path/to/time
pip install -r research_evolver/requirements.txt   # Python 3.10–3.12 recommended
python research_evolver/scripts/init_db.py
python research_evolver/scripts/generate_synthetic_data.py
python research_evolver/scripts/run_baseline.py --smoke   # quick check; drop --smoke for full run
python research_evolver/scripts/run_generation.py 0 --n-children 50   # gen 0
python research_evolver/scripts/make_report.py --dashboard   # lineage_report.txt + dashboard.html
```

See `agent_city/skills/run_research_evolution.md` and `RESEARCH_EVOLUTION_STATUS.md` for details.

---

## 6. Moltbook (optional)

- Apply at [moltbook.com/developers](https://www.moltbook.com/developers) and get an app key (`moltdev_...`).
- Set `MOLTBOOK_APP_KEY` in the environment (or in a secrets store the gateway uses).
- Test verification:
  ```bash
  export MOLTBOOK_APP_KEY=moltdev_...
  python agent_city/moltbook/verify_token.py "<identity_token>"
  ```
- Give agents the auth URL for Sign in with Moltbook:  
  `https://moltbook.com/auth.md?app=AgentCity&endpoint=https://YOUR_VERIFY_ENDPOINT`  
  Implement the verify endpoint (e.g. call Moltbook verify-identity API as in `moltbook/README.md`).
- **Report every post to you:** Agents are instructed to run `agent_city/moltbook/report_post.py` after each successful Moltbook post. All posts are appended to **`agent_city/reports/moltbook_posts.md`** (or `MOLTBOOK_REPORT_PATH`). Watch that file to see everything the city posts.

---

## 7. Verify the city is running

1. **OpenClaw:** `openclaw dashboard` → select an agent (e.g. Researcher or Evolver) → send: “Run the adversarial benchmark and report OverallAccuracy for system D.”
   Or ask: run the main benchmark for v1 and report TemporalAccuracy for system D.
2. **Reproduction:**  
   `python agent_city/scripts/reproduce.py --parent researcher --child my_specialist --trait Interval`  
   Then add the new workspace to OpenClaw (symlink or `agents.list` entry).
3. **Moltbook:** After backend verification is in place, ask Researcher to “post a one-sentence summary of the last benchmark run to Moltbook” (or explain that the endpoint is not set up yet).

---

## Troubleshooting

- **"Open AI not configured"** / **API key missing** — Use a `.env` file: see **Use a .env file for API keys** above. Copy `agent_city/.env.example` to `~/.openclaw/.env`, set `OPENAI_API_KEY=sk-...`, remove the key from `openclaw.json` `env.vars`, then restart the gateway.
- **"OAuth token refresh failed for openai-codex"** / **"refresh_token_reused"** — The OpenAI/Codex OAuth token was invalidated (expired, or reused elsewhere). **Fix:** Re-authenticate so OpenClaw gets a new refresh token (run in a **real terminal**, not from automation — it needs an interactive TTY):
  1. **Preferred:**  
     `openclaw models auth login --provider openai-codex --set-default`  
     Complete the browser/OAuth flow when it opens.
  2. **Alternative:**  
     `openclaw configure --section model`  
     Go through the model section and sign in for openai-codex when prompted.
  3. Restart the gateway (e.g. restart the daemon or close and run `openclaw dashboard` again), then retry the agent.
- **"gateway token missing"** / **"unauthorized … token_missing"** (Control UI / webchat) — The Control UI is connecting without a gateway token. **Fix:** Open the dashboard URL (from `openclaw dashboard` or your config), copy the gateway token, and paste it in the Control UI settings (e.g. Cursor’s OpenClaw integration or the webchat settings).
- **"EBUSY" or "resource busy or locked" when updating OpenClaw** — npm can’t replace the `openclaw` folder while the daemon is using it. **Fix:** Stop the daemon (e.g. `openclaw stop` or close the dashboard), run the update (e.g. `npm update -g openclaw` or the install script), then start OpenClaw again.
- **Logs say "Run openclaw doctor --fix"** — Apply suggested fixes:
  ```bash
  openclaw doctor --fix
  ```
- **Agent failed / need details** — View daemon logs:
  ```bash
  openclaw logs --follow
  ```

---

## Summary

| Step | Action |
|------|--------|
| 1 | Install OpenClaw (`install.sh` / `install.ps1`) and run `openclaw onboard --install-daemon` |
| 2 | If you see "access not configured", have the bot owner run `openclaw pairing approve telegram <CODE>` |
| 3 | Add `IDENTITY.md` (and optional `USER.md`) to each workspace or run `openclaw setup --workspace <path>` |
| 4 | Symlink or config: point OpenClaw at `agent_city/workspaces/*` as multiple agents |
| 5 | Run benchmark from repo root (`cd ../../` from workspace, or set `AGENT_CITY_REPO`); optionally run evolution (see Research evolution above) |
| 6 | Set `MOLTBOOK_APP_KEY`, implement verify endpoint, test `verify_token.py` |
| 7 | Chat with a citizen, run benchmark (and/or evolution), spawn a child, optionally publish to Moltbook |

Once these are in place, the city is running on OpenClaw with optional Moltbook integration.
