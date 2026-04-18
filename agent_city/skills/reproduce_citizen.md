# Skill: Reproduce (Spawn Child Citizen)

Use this skill when the user or an approved workflow asks to **spawn a new citizen** (child agent) in Agent City. Reproduction creates a new OpenClaw workspace with a SOUL derived from a parent and an optional focus trait.

## When to use

- User asks to "spawn a child agent," "create a new citizen," "reproduce with trait X," or "create a specialist for FutureFact/Interval/Reversion/Evolution."
- You have **explicit approval** (user or gateway confirmed). Do not run reproduction without approval.

## How to run

From the **repository root**. When your workspace is `agent_city/workspaces/<name>/`, use: `cd ../../ && `.

```bash
cd ../../ && python agent_city/scripts/reproduce.py --parent RESEARCHER --child CHILD_NAME --trait TRAIT
```

- **RESEARCHER:** Parent workspace id: `researcher` or `temporal_citizen` (or another existing citizen name).
- **CHILD_NAME:** New workspace name, e.g. `future_specialist`, `interval_focus`, `reversion_specialist`, `evolution_focus`. Use lowercase with underscores; it will be slugified.
- **TRAIT:** Focus trait for the child, e.g. `FutureFact`, `Interval`, `Reversion`, `CausalReasoning`, `MultiReversion`, `IntervalMidpoint`, `MultiEntityJoin`, `TimelineReconstruction`, or `general`.

**Examples:**

```bash
python agent_city/scripts/reproduce.py --parent researcher --child future_specialist --trait FutureFact
python agent_city/scripts/reproduce.py --parent researcher --child evolution_focus --trait Evolution
python agent_city/scripts/reproduce.py --parent temporal_citizen --child interval_focus --trait Interval
```

## What the script does

- Creates `agent_city/workspaces/<child_name>/SOUL.md` with identity, handoffs (Researcher, Temporal Citizen), and boundaries.
- Creates `agent_city/workspaces/<child_name>/IDENTITY.md` so OpenClaw can load the workspace without extra setup.

## After spawning: add to OpenClaw

- **Symlink (from repo root):**  
  `ln -s "$(pwd)/agent_city/workspaces/<child_name>" ~/.openclaw/workspace-<child_name>`
- Or add an entry to OpenClaw config `agents.list` with `workspace: REPO_ROOT/agent_city/workspaces/<child_name>`.
- Ensure the new workspace has an `IDENTITY.md` (see above).

## Boundaries

- Run only after **explicit user or gateway approval**. Do not spawn children autonomously.
- Do not change the reproduce script or SOUL template from within this skill.
- Child names must be new; the script exits with error if the workspace already exists.
