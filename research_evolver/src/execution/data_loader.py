"""
Dataset loader for reasoning task. Expects JSONL with 'question' and 'answer' (or 'input'/'output').
Splits: train, proxy (small eval), holdout (frozen). Paths under research_evolver/data/.
"""

from pathlib import Path
from typing import Iterator

# Repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DATA_DIR = _REPO_ROOT / "research_evolver" / "data"


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    import json
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _normalize_item(row: dict) -> dict:
    """Unify keys to 'question' and 'answer' for training/eval."""
    if "question" in row and "answer" in row:
        return {"question": row["question"], "answer": row["answer"]}
    if "input" in row and "output" in row:
        return {"question": row["input"], "answer": row["output"]}
    if "prompt" in row and "completion" in row:
        return {"question": row["prompt"], "answer": row["completion"]}
    return row


def load_split(split: str, data_dir: Path | None = None) -> list[dict]:
    """
    Load a split: 'train', 'proxy', or 'holdout'.
    Files: {data_dir}/processed/train.jsonl, proxy.jsonl, holdout.jsonl
    """
    data_dir = data_dir or _DATA_DIR
    processed = data_dir / "processed"
    name = f"{split}.jsonl"
    path = processed / name
    rows = _load_jsonl(path)
    return [_normalize_item(r) for r in rows]


def load_train(data_dir: Path | None = None) -> list[dict]:
    return load_split("train", data_dir)


def load_proxy(data_dir: Path | None = None) -> list[dict]:
    return load_split("proxy", data_dir)


def load_holdout(data_dir: Path | None = None) -> list[dict]:
    return load_split("holdout", data_dir)


def iter_train(data_dir: Path | None = None) -> Iterator[dict]:
    """Stream training examples for large datasets."""
    for item in load_train(data_dir):
        yield item
