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
    "slow": {
        "subjects": [f"hardware_{i}" for i in range(30)] + [f"spec_{i}" for i in range(30)],
        "update_p": 0.25
    },
    "medium": {
        "subjects": [f"api_{i}" for i in range(30)] + [f"model_{i}" for i in range(30)] + [f"pricing_{i}" for i in range(20)],
        "update_p": 0.40
    },
    "fast": {
        "subjects": [f"status_{i}" for i in range(25)] + [f"incident_{i}" for i in range(25)] + [f"docs_{i}" for i in range(20)],
        "update_p": 0.60
    },
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

    # Convert facts to dicts for easier processing
    facts_dict = [asdict(f) for f in facts]
    
    # Generate different types of questions
    questions: list[dict] = []
    
    # 1. As-of-time QA questions (60%)
    asof_count = int(question_count * 0.6)
    for qid in range(1, asof_count + 1):
        f = rng.choice(facts_dict)
        as_of = rng.randint(f["t_valid_from"], f["t_valid_until"] or days)
        prompt = f"As of day {as_of}, what was true about {f['content'].split(':')[1]} in {f['domain']}?"
        questions.append(
            {
                "question_id": f"q{qid}",
                "task_family": "AsOfQA",
                "prompt": prompt,
                "as_of_day": as_of,
                "domain": f["domain"],
                "subject": f["content"].split(":")[1],
                "answer": f["content"],
            }
        )

    # 2. Change detection questions (20%)
    change_count = int(question_count * 0.2)
    for qid in range(asof_count + 1, asof_count + change_count + 1):
        # Pick a subject and find two different facts about it
        domain = rng.choice(list(DOMAINS.keys()))
        subject = rng.choice(DOMAINS[domain]["subjects"])
        subj_facts = [f for f in facts_dict if f["domain"] == domain and f["content"].split(":")[1] == subject]
        if len(subj_facts) < 2:
            continue
        subj_facts_sorted = sorted(subj_facts, key=lambda x: x["t_valid_from"])
        f1, f2 = rng.sample(subj_facts_sorted[:3], 2)  # Get facts from early/mid timeline
        early_day = min(f1["t_valid_from"], f2["t_valid_from"])
        late_day = max(f1["t_valid_from"], f2["t_valid_from"])
        prompt = f"What changed for {subject} between day {early_day} and day {late_day}?"
        questions.append(
            {
                "question_id": f"q{qid}",
                "task_family": "ChangeDetection",
                "prompt": prompt,
                "start_day": early_day,
                "end_day": late_day,
                "domain": domain,
                "subject": subject,
                "answer": f"{f1['content']} -> {f2['content']}",
            }
        )

    # 3. Causal questions (20%)
    # Create ACTION/OUTCOME events for causal questions
    action_outcome_events = []
    for i in range(len(events) // 10):  # Create ~10% as action/outcome pairs
        ev = rng.choice(events)
        if ev.event_type == "FACT_OBSERVED":
            outcome_day = min(ev.t_event + rng.randint(1, 5), days)
            action_outcome_events.append({
                "action_event": ev.event_id,
                "action_day": ev.t_event,
                "outcome_day": outcome_day,
                "domain": ev.domain,
                "subject": ev.subject,
            })

    causal_count = question_count - asof_count - change_count
    for qid in range(asof_count + change_count + 1, question_count + 1):
        if not action_outcome_events:
            break
        ao = rng.choice(action_outcome_events)
        prompt = f"Which change on day {ao['action_day']} caused the state on day {ao['outcome_day']} for {ao['subject']}?"
        questions.append(
            {
                "question_id": f"q{qid}",
                "task_family": "CausalQuery",
                "prompt": prompt,
                "action_day": ao["action_day"],
                "outcome_day": ao["outcome_day"],
                "domain": ao["domain"],
                "subject": ao["subject"],
                "answer": ao["action_event"],
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
