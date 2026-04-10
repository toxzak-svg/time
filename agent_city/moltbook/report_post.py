#!/usr/bin/env python3
"""Append a Moltbook post report so the user sees every post the city makes.

Usage (from repo root or with AGENT_CITY_REPO set):
  python agent_city/moltbook/report_post.py --agent Researcher --content "Benchmark: D_revised 0.94 OverallAccuracy"
  python agent_city/moltbook/report_post.py --agent Evolver --title "Gen 1 lineage" --content "Best genome +2% vs baseline"

Writes to agent_city/reports/moltbook_posts.md (or MOLTBOOK_REPORT_PATH). Create reports/ if needed.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone


def get_report_path() -> str:
    path = os.environ.get("MOLTBOOK_REPORT_PATH", "").strip()
    if path and os.path.isabs(path):
        return path
    repo = os.environ.get("AGENT_CITY_REPO", "").strip()
    if not repo:
        # Assume we're run from repo root
        repo = os.getcwd()
    return os.path.join(repo, "agent_city", "reports", "moltbook_posts.md")


def report_post(agent: str, content: str, title: str | None = None) -> None:
    path = get_report_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"- **{ts}** | **{agent}**"
    if title:
        line += f" — {title}"
    line += f"\n  {content}\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)


def main() -> None:
    ap = argparse.ArgumentParser(description="Report a Moltbook post to the user (append to report file).")
    ap.add_argument("--agent", required=True, help="Agent/citizen name (e.g. Researcher, Evolver)")
    ap.add_argument("--content", required=True, help="Post content or short summary (one line or sentence)")
    ap.add_argument("--title", default=None, help="Optional post title")
    args = ap.parse_args()
    report_post(agent=args.agent, content=args.content, title=args.title)
    print("Reported post to", get_report_path())


if __name__ == "__main__":
    main()
