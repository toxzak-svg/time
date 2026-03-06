#!/usr/bin/env python3
"""Generate TemporalBench-v1 synthetic events/facts/questions."""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

DOMAINS = {
    "slow": {"subjects": ["gpu_a", "gpu_b", "disk_sku", "cpu_line"], "update_p": 0.08},
    "medium": {"subjects": ["api_price", "model_tier", "quota_limit", "feature_flag"], "update_p": 0.22},
    "fast": {"subjects": ["status_page", "incident_level", "docs_notice", "release_channel"], "update_p": 0.45},
}

EVENT_TYPES = ["FACT_OBSERVED", "FACT_SUPERSEDED", "ACTION", "OUTCOME", "POLICY_UPDATE"]


@dataclass
class Event:
    event_id: str
    t_event: int
    t_observed: int
    domain: str
    event_type: str
    subject: str
    value: str
    supersedes: Optional[str]
    source_reliability: float


@dataclass
class Fact:
    fact_id: str
    content: str
    t_valid_from: int
    t_valid_until: Optional[int]
    domain: str
    confidence: float
    decay_fn: str


def maybe_update(rng: random.Random, p: float) -> bool:
    return rng.random() < p


def gen_value(domain: str, subject: str, day: int, version: int) -> str:
    return f"{domain}:{subject}:d{day}:v{version}"


def generate(days: int, seed: int, question_count: int) -> tuple[list[dict], list[dict], list[dict]]:
    rng = random.Random(seed)
    events: list[Event] = []
    facts: list[Fact] = []
    latest_event_by_subject: dict[str, Event] = {}
    subject_version: dict[str, int] = {}

    eid = 0
    fid = 0

    for day in range(1, days + 1):
        for domain, cfg in DOMAINS.items():
            for subject in cfg["subjects"]:
                key = f"{domain}:{subject}"
                do_update = key not in latest_event_by_subject or maybe_update(rng, cfg["update_p"])
                if not do_update:
                    continue

                subject_version[key] = subject_version.get(key, 0) + 1
                value = gen_value(domain, subject, day, subject_version[key])
                prev = latest_event_by_subject.get(key)

                eid += 1
                ev = Event(
                    event_id=f"e{eid}",
                    t_event=day,
                    t_observed=min(days, day + rng.randint(0, 1)),
                    domain=domain,
                    event_type="FACT_OBSERVED" if prev is None else "FACT_SUPERSEDED",
                    subject=subject,
                    value=value,
                    supersedes=prev.event_id if prev else None,
                    source_reliability=round(0.6 + rng.random() * 0.4, 3),
                )
                events.append(ev)
                latest_event_by_subject[key] = ev

                if prev:
                    for f in reversed(facts):
                        if f.content.startswith(f"{domain}:{subject}:") and f.t_valid_until is None:
                            f.t_valid_until = day - 1
                            break

                fid += 1
                facts.append(
                    Fact(
                        fact_id=f"f{fid}",
                        content=value,
                        t_valid_from=day,
                        t_valid_until=None,
                        domain=domain,
                        confidence=round(0.8 + rng.random() * 0.2, 3),
                        decay_fn="domain_half_life",
                    )
                )

    questions: list[dict] = []
    for qid in range(1, question_count + 1):
        f = rng.choice(facts)
        as_of = rng.randint(f.t_valid_from, f.t_valid_until or days)
        prompt = f"As of day {as_of}, what was true about {f.content.split(':')[1]} in {f.domain}?"
        questions.append(
            {
                "question_id": f"q{qid}",
                "task_family": "AsOfQA",
                "prompt": prompt,
                "as_of_day": as_of,
                "domain": f.domain,
                "subject": f.content.split(":")[1],
                "answer": f.content,
            }
        )

    return [asdict(e) for e in events], [asdict(f) for f in facts], questions


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--questions", type=int, default=2000)
    ap.add_argument("--events-out", default="benchmarks/temporalbench_v1_events.jsonl")
    ap.add_argument("--facts-out", default="benchmarks/temporalbench_v1_facts.jsonl")
    ap.add_argument("--questions-out", default="benchmarks/temporalbench_v1_questions.jsonl")
    args = ap.parse_args()

    events, facts, questions = generate(args.days, args.seed, args.questions)
    write_jsonl(Path(args.events_out), events)
    write_jsonl(Path(args.facts_out), facts)
    write_jsonl(Path(args.questions_out), questions)

    print(f"wrote {len(events)} events -> {args.events_out}")
    print(f"wrote {len(facts)} facts -> {args.facts_out}")
    print(f"wrote {len(questions)} questions -> {args.questions_out}")


if __name__ == "__main__":
    main()
