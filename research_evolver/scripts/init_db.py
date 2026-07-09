#!/usr/bin/env python3
"""Initialize Research Evolution SQLite DB. Run from repo root or research_evolver/."""

import sys
from pathlib import Path

# Allow importing from research_evolver.src
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research_evolver.src.memory import get_connection, init_db


def main() -> None:
    db_path = ROOT / "research_evolver" / "data" / "evolver.db"
    conn = get_connection(str(db_path))
    init_db(conn)
    print("DB initialized:", db_path)
    conn.close()


if __name__ == "__main__":
    main()
