#!/usr/bin/env python3
"""Spawn a child agent (new OpenClaw workspace + SOUL.md) from a parent. Used for 'reproduction' in Agent City.

Usage:
  python agent_city/scripts/reproduce.py --parent researcher --child future_specialist --trait FutureFact
  python agent_city/scripts/reproduce.py --parent temporal_citizen --child interval_focus --trait Interval

Creates agent_city/workspaces/<child>/SOUL.md with identity and focus derived from parent and trait.
Requires explicit approval (e.g. run only after user or gateway confirms).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

# Default SOUL template: same structure as temporal_citizen, with placeholder for focus
CHILD_SOUL_TEMPLATE = """# {child_display} — Soul

## Identity

You are **{child_display}**, a citizen of Agent City. You were spawned from **{parent_display}** with a focus on **{trait_focus}**. You live in the same temporal world (adversarial benchmark facts and questions) and learn from benchmark results. You may hand off to the Researcher for full benchmark runs or Moltbook publishing, and to the Temporal Citizen for single as-of queries.

## Communication Style

- Be concise. When answering temporal questions, use the exact fact format (e.g. `ceo:subject:dN:Name`).
- Emphasize reasoning for your focus area: {trait_focus}.

## Values

- **Correctness** over speed. **Learning** from benchmark runs. **Reproducibility**: document your lineage as a child of {parent_display} with trait {trait_focus}.

## Boundaries

- Do not modify benchmark fact/question JSONL. Do not spawn a child without approval. Do not expose API keys or identity tokens.

## Handoff

- Full benchmark runs or Moltbook posts → Researcher.
- Single as-of temporal queries → Temporal Citizen.
"""

PARENT_DISPLAY_NAMES = {
    "researcher": "Researcher",
    "temporal_citizen": "Temporal Citizen",
}


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_") or "citizen"


def main() -> None:
    ap = argparse.ArgumentParser(description="Spawn a child agent workspace (reproduction) in Agent City.")
    ap.add_argument("--parent", required=True, help="Parent workspace name (e.g. researcher, temporal_citizen)")
    ap.add_argument("--child", required=True, help="Child workspace name (e.g. future_specialist)")
    ap.add_argument("--trait", default="general", help="Focus trait (e.g. FutureFact, Interval, Reversion, Evolution)")
    ap.add_argument("--workspaces-dir", type=Path, default=None, help="Override workspaces directory")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parent.parent.parent
    workspaces_dir = args.workspaces_dir or (repo_root / "agent_city" / "workspaces")
    child_name = slug(args.child)
    parent_name = slug(args.parent)
    parent_display = PARENT_DISPLAY_NAMES.get(parent_name, parent_name.replace("_", " ").title())
    child_display = child_name.replace("_", " ").title()
    trait_focus = args.trait.strip() or "general"

    child_dir = workspaces_dir / child_name
    if child_dir.exists():
        print(f"Child workspace already exists: {child_dir}", file=__import__("sys").stderr)
        __import__("sys").exit(1)

    child_dir.mkdir(parents=True, exist_ok=True)
    soul_path = child_dir / "SOUL.md"
    content = CHILD_SOUL_TEMPLATE.format(
        child_display=child_display,
        parent_display=parent_display,
        trait_focus=trait_focus,
    )
    soul_path.write_text(content, encoding="utf-8")
    # Minimal IDENTITY.md so OpenClaw can load the workspace without extra setup
    identity_path = child_dir / "IDENTITY.md"
    identity_content = f"""# {child_display}

**Name:** {child_display}  
**Vibe:** Focused on {trait_focus}.  
**Emoji:** 🔮

Child of {parent_display} (trait: {trait_focus}). Citizen of Agent City. Hand off full benchmark or Moltbook to Researcher; single as-of queries to Temporal Citizen.
"""
    identity_path.write_text(identity_content, encoding="utf-8")
    print(f"Created {soul_path}")
    print(f"Created {identity_path}")
    print(f"  Parent: {parent_display}  Trait: {trait_focus}")
    print("  Add this workspace to OpenClaw (e.g. symlink or copy to ~/.openclaw/workspaces) to run the new citizen.")


if __name__ == "__main__":
    main()
