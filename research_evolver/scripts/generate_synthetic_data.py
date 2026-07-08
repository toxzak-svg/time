#!/usr/bin/env python3
"""
Write minimal train/proxy/holdout JSONL for the baseline path.
Format: one object per line with "question" and "answer". Simple reasoning (arithmetic) so
the baseline has something to run on without external datasets.
"""

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PROCESSED = ROOT / "research_evolver" / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)


def make_example(rng: random.Random) -> dict:
    a, b = rng.randint(1, 50), rng.randint(1, 50)
    op = rng.choice([" + ", " - ", " * "])
    if op == " * ":
        answer = a * b
    elif op == " - ":
        answer = a - b
    else:
        answer = a + b
    question = f"What is {a}{op.strip()}{b}? Reply with a single number."
    return {"question": question, "answer": str(answer)}


def main():
    seed = 42
    rng = random.Random(seed)
    sizes = {"train": 200, "proxy": 50, "holdout": 50}
    for split, n in sizes.items():
        path = PROCESSED / f"{split}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for _ in range(n):
                f.write(json.dumps(make_example(rng)) + "\n")
        print("Wrote %s (%d examples)" % (path, n))
    print("Done. Run: python research_evolver/scripts/run_baseline.py [--smoke]")


if __name__ == "__main__":
    main()
