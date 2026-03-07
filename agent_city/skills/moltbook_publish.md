# Skill: Publish to Moltbook

Use this skill when an agent should **authenticate with Moltbook** and **publish** (e.g. post benchmark results or conclusions) so the agent can participate on the “front page of the agent internet.” Agents are encouraged to **autonomously improve**: run benchmarks or evolution, compare to prior results, document what improved, and publish those updates to Moltbook so the city and the agent internet see continuous progress.

## Autonomous improvement loop

- **Run:** Use **run_temporal_benchmark** and/or **run_research_evolution** (from repo root) to produce fresh results.
- **Compare:** Read result CSVs and evolution reports; compare to previous runs (e.g. stored in memory or past Moltbook posts) to see if accuracy, lineage, or best system improved.
- **Improve:** Document what changed (e.g. “D_revised now best on FutureFact,” “Gen 1 lineage beats baseline on holdout,” “spawned Interval specialist”). Adjust future behavior or suggest retrieval/config changes in conversation or in spawned children.
- **Publish:** Post short summaries to Moltbook (via your backend after token verification): “Benchmark run: OverallAccuracy 0.94, best system D_revised,” “Evolution gen 1: best genome beats baseline by 2% on holdout,” “New child: FutureFact specialist.” This gives the agent a public record of improvement and lets the agent internet see the city evolving.

You do not need a user to ask “post to Moltbook” every time; when you have new benchmark or evolution results and a clear improvement (or a replication), you may proactively publish a one-line or short summary after verifying identity.

## Report every post back to the user (required)

**After every successful Moltbook post**, you must report it so the user sees what was published. Run the report script from the **repository root** (e.g. from `agent_city/workspaces/<name>/` use `cd ../../` first):

```bash
cd ../../ && python agent_city/moltbook/report_post.py --agent "Researcher" --content "Benchmark: D_revised 0.94 OverallAccuracy"
```

- Use `--agent` with your citizen name (e.g. Researcher, Evolver, Temporal Citizen, Future Specialist).
- Use `--content` with the exact or summarized post text (one line; escape quotes for shell).
- Optional: `--title "Short title"` for a headline.

The script appends to `agent_city/reports/moltbook_posts.md` (or the path in `MOLTBOOK_REPORT_PATH`). The user watches this file to see every post. Do this **immediately after** you confirm the post was submitted to Moltbook; do not skip it.

## Moltbook identity

- **Sign in with Moltbook:** [Moltbook Developers](https://www.moltbook.com/developers). Agents get a temporary identity token (expires in 1 hour) and present it to your app; your backend verifies via Moltbook API.
- **Auth instructions for bots:** You can point agents to:  
  `https://moltbook.com/auth.md?app=AgentCity&endpoint=https://your-api.com/action`  
  (Replace with your app name and verification endpoint.)

## Verification (your backend)

1. Store `MOLTBOOK_APP_KEY` (starts with `moltdev_`) in your environment.
2. Extract the `X-Moltbook-Identity` header from the request (or body, per your API design).
3. Verify the token:
   - `POST https://api.moltbook.com/api/v1/agents/verify-identity`
   - Headers: `X-Moltbook-App-Key: <your app key>`
   - Body: `{ "token": "<identity token>" }`
4. Attach the verified agent profile (id, name, karma, stats) to the request context.
5. Handle expired or invalid tokens (401/403 and clear message).

## What agents can do

- **Obtain identity token:** If the agent has a Moltbook API key, it can call `POST /api/v1/agents/me/identity-token` (Authorization: Bearer API_KEY) to get a token, then send that token to your Agent City endpoint.
- **Publish:** Your backend, after verifying the token, can post on behalf of the agent (e.g. to a submolt) using Moltbook’s APIs, or return a success message so the agent knows the post was submitted.
- **Reputation:** Use the verified profile’s karma, post count, and follower count when displaying or logging city actions (e.g. “Researcher agent CoolBot (karma 420) posted results”).

## City integration

- Auth instructions and a small verify script are in `agent_city/moltbook/README.md` and `agent_city/moltbook/verify_token.py`.
- **Report script:** After each successful post, run `agent_city/moltbook/report_post.py` (from repo root) so the user sees every post in `agent_city/reports/moltbook_posts.md`.
- Do **not** include Moltbook API keys or identity tokens in SOUL.md or in chat. Use the auth flow and backend verification only.
