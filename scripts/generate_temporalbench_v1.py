#!/usr/bin/env python3
"""Generate TemporalBench-v1 synthetic events + QA pairs.

Output format is JSONL with mixed records:
- {"record_type": "event", ...EventSchema }
- {"record_type": "question", ...QuestionSchema }
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


DOMAIN_HALF_LIFE = {"slow": 30.0, "medium": 10.0, "fast": 3.0}


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


def _subject_pool(domain: str) -> List[str]:
    count = {"slow": 50, "medium": 80, "fast": 120}[domain]
    return [f"{domain}_subject_{i:03d}" for i in range(count)]


def _next_value(subject: str, version: int) -> str:
    return f"{subject}_value_v{version}"


def generate_events(duration_days: int, total_events: int, seed: int) -> List[Event]:
    rng = random.Random(seed)
    domains = [("slow", 0.2), ("medium", 0.35), ("fast", 0.45)]
    subjects = {d: _subject_pool(d) for d, _ in domains}
    domain_weights = [w for _, w in domains]

    state: Dict[str, Dict[str, str]] = {d: {} for d, _ in domains}
    version_counter: Dict[str, int] = {}
    latest_event_by_subject: Dict[str, str] = {}
    events: List[Event] = []

    for idx in range(total_events):
        domain = rng.choices([d for d, _ in domains], weights=domain_weights, k=1)[0]
        subject = rng.choice(subjects[domain])
        version_counter.setdefault(subject, 0)
        version_counter[subject] += 1
        value = _next_value(subject, version_counter[subject])

        t_event = rng.randint(1, duration_days)
        t_observed = min(duration_days, t_event + rng.randint(0, 2))
        event_id = f"ev_{idx:05d}"

        supersedes = latest_event_by_subject.get(subject)
        event_type = "FACT_OBSERVED" if supersedes is None else "FACT_SUPERSEDED"
        reliability_floor = {"slow": 0.85, "medium": 0.75, "fast": 0.60}[domain]
        source_reliability = round(rng.uniform(reliability_floor, 0.99), 3)

        event = Event(
            event_id=event_id,
            t_event=t_event,
            t_observed=t_observed,
            domain=domain,
            event_type=event_type,
            subject=subject,
            value=value,
            supersedes=supersedes,
            source_reliability=source_reliability,
        )
        events.append(event)
        latest_event_by_subject[subject] = event_id
        state[domain][subject] = value

    # Ensure chronological order for easier downstream eval.
    events.sort(key=lambda e: (e.t_event, e.t_observed, e.event_id))
    return events


def build_truth_intervals(events: List[Event], duration_days: int) -> Dict[str, List[dict]]:
    by_subject: Dict[str, List[Event]] = {}
    for ev in events:
        by_subject.setdefault(ev.subject, []).append(ev)

    facts: Dict[str, List[dict]] = {}
    for subject, subject_events in by_subject.items():
        subject_events.sort(key=lambda e: (e.t_event, e.t_observed, e.event_id))
        intervals = []
        for i, ev in enumerate(subject_events):
            valid_from = ev.t_event
            valid_until = (
                subject_events[i + 1].t_event - 1 if i < len(subject_events) - 1 else duration_days
            )
            intervals.append(
                {
                    "fact_id": f"fact_{ev.event_id}",
                    "content": f"{ev.subject}={ev.value}",
                    "t_valid_from": valid_from,
                    "t_valid_until": valid_until,
                    "domain": ev.domain,
                    "confidence": ev.source_reliability,
                    "decay_fn": f"half_life_days_{DOMAIN_HALF_LIFE[ev.domain]}",
                    "source_event_id": ev.event_id,
                }
            )
        facts[subject] = intervals
    return facts


def _fact_at_time(intervals: List[dict], t: int) -> Optional[dict]:
    for it in intervals:
        if it["t_valid_from"] <= t <= it["t_valid_until"]:
            return it
    return None


def generate_questions(
    facts: Dict[str, List[dict]],
    total_questions: int,
    duration_days: int,
    seed: int,
) -> List[dict]:
    rng = random.Random(seed + 1)
    subjects = list(facts.keys())
    families = ["as_of_time", "change_detection", "staleness_resistance"]
    family_weights = [0.5, 0.3, 0.2]

    questions = []
    for i in range(total_questions):
        family = rng.choices(families, weights=family_weights, k=1)[0]
        subject = rng.choice(subjects)
        intervals = facts[subject]

        if family == "as_of_time":
            t = rng.randint(1, duration_days)
            truth = _fact_at_time(intervals, t)
            answer = truth["content"].split("=", 1)[1] if truth else "UNKNOWN"
            questions.append(
                {
                    "question_id": f"q_{i:05d}",
                    "family": family,
                    "query": f"As of day {t}, what was true about {subject}?",
                    "time_anchor": t,
                    "subject": subject,
                    "gold_answer": answer,
                    "gold_event_id": truth["source_event_id"] if truth else None,
                }
            )
        elif family == "change_detection":
            t1 = rng.randint(1, duration_days - 1)
            t2 = rng.randint(t1 + 1, duration_days)
            f1 = _fact_at_time(intervals, t1)
            f2 = _fact_at_time(intervals, t2)
            changed = (f1 and f2 and f1["source_event_id"] != f2["source_event_id"]) or (f1 is None) != (f2 is None)
            questions.append(
                {
                    "question_id": f"q_{i:05d}",
                    "family": family,
                    "query": f"What changed for {subject} between day {t1} and day {t2}?",
                    "time_window": [t1, t2],
                    "subject": subject,
                    "gold_answer": "CHANGED" if changed else "NO_CHANGE",
                    "from_event_id": f1["source_event_id"] if f1 else None,
                    "to_event_id": f2["source_event_id"] if f2 else None,
                }
            )
        else:
            t = rng.randint(3, duration_days)
            truth = _fact_at_time(intervals, t)
            distractor = None
            older = [it for it in intervals if it["t_valid_until"] < t]
            if older:
                distractor = rng.choice(older)["content"]
            questions.append(
                {
                    "question_id": f"q_{i:05d}",
                    "family": family,
                    "query": f"Current value for {subject} on day {t}? Avoid stale information.",
                    "time_anchor": t,
                    "subject": subject,
                    "gold_answer": truth["content"].split("=", 1)[1] if truth else "UNKNOWN",
                    "adversarial_stale_hint": distractor,
                }
            )

    return questions


def write_jsonl(path: Path, records: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate TemporalBench-v1 synthetic data")
    parser.add_argument("--duration-days", type=int, default=60)
    parser.add_argument("--events", type=int, default=1000)
    parser.add_argument("--questions", type=int, default=500)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmarks/temporalbench_v1.jsonl"),
    )
    args = parser.parse_args()

    events = generate_events(args.duration_days, args.events, args.seed)
    facts = build_truth_intervals(events, args.duration_days)
    questions = generate_questions(facts, args.questions, args.duration_days, args.seed)

    records = []
    for ev in events:
        records.append({"record_type": "event", **ev.__dict__})
    for subject_facts in facts.values():
        for fact in subject_facts:
            records.append({"record_type": "fact", **fact})
    for q in questions:
        records.append({"record_type": "question", **q})

    write_jsonl(args.output, records)
    print(
        f"Generated {len(events)} events, "
        f"{sum(len(v) for v in facts.values())} facts, {len(questions)} questions -> {args.output}"
    )


if __name__ == "__main__":
    main()
