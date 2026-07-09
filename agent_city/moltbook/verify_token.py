#!/usr/bin/env python3
"""Verify a Moltbook identity token and print the agent profile (for testing or simple backends).

Usage:
  export MOLTBOOK_APP_KEY=moltdev_...
  python agent_city/moltbook/verify_token.py "<identity_token>"

Do not log or expose the token. Requires requests (pip install requests).
"""

from __future__ import annotations

import json
import os
import sys


def verify_token(token: str) -> dict:
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.moltbook.com/api/v1/agents/verify-identity",
            data=json.dumps({"token": token}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Moltbook-App-Key": os.environ.get("MOLTBOOK_APP_KEY", "").strip(),
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"success": False, "error": str(e)}


def main() -> None:
    app_key = os.environ.get("MOLTBOOK_APP_KEY", "").strip()
    if not app_key or not app_key.startswith("moltdev_"):
        print("Set MOLTBOOK_APP_KEY (moltdev_...) in the environment.", file=sys.stderr)
        sys.exit(1)
    if len(sys.argv) < 2:
        print("Usage: verify_token.py <identity_token>", file=sys.stderr)
        sys.exit(1)
    token = sys.argv[1].strip()
    if not token:
        print("Empty token.", file=sys.stderr)
        sys.exit(1)
    result = verify_token(token)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
