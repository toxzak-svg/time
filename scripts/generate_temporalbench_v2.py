#!/usr/bin/env python3
"""Generate TemporalBench-v2 - ADVERSARIAL version that pushes systems to breaking point.

Key adversarial strategies:
1. PAST-QUERY TRAPS: Ask about past time, but latest fact is newer (catches "just get latest")
2. MIDDLE-AGE FACTS: Query at times between updates
3. HIGH UPDATE FREQUENCY: Fast domain with many updates
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

DOMAINS = {
    "slow": {
        "subjects": [f"hardware_{i}" for i in range(20)] + [f"spec_{i}" for i in range(20)],
        "update_p": 0.20,
    },
    "medium": {
        "subjects": [f"api_{i}" for i in range(20)] + [f"model_{i}" for i in range(20)] + [f"pricing_{i}" for i in range(10)],
        "update_p": 0.35,
    },
    "fast": {
        "subjects": [f"status_{i}" for i in range(30)] + [f"incident_{i}" for i in range(30)] + [f"docs_{i}" for i in range(20)],
        "update_p": 0.70,  # Very high update rate
    },
}


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


def generate_base_world(days: int, seed: int) -> tuple[list[Event], list[Fact], dict]:
    """Generate the base world with facts."""
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
                do_update = key not in latest_event_by_subject or rng.random() < cfg["update_p"]
                if not do_update:
                    continue

                subject_version[key] = subject_version.get(key, 0) + 1
                version = subject_version[key]
                value = f"{domain}:{subject}:day{day}:v{version}:{rng.randint(1000,9999)}"
                prev = latest_event_by_subject.get(key)

                eid += 1
                ev = Event(
                    event_id=f"e{eid}",
                    t_event=day,
                    t_observed=min(days, day + rng.randint(0, 2)),
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

    return events, facts, latest_event_by_subject


def generate_adversarial_questions(
    facts: list[Fact], 
    events: list[Event], 
    days: int, 
    seed: int,
    question_count: int
) -> list[dict]:
    """Generate questions that specifically test temporal reasoning - past queries."""
    rng = random.Random(seed)
    questions: list[dict] = []
    
    facts_dict = [asdict(f) for f in facts]
    
    # Group facts by subject
    by_subject: dict[str, list[dict]] = {}
    for f in facts_dict:
        subject = f["content"].split(":")[1]
        by_subject.setdefault(subject, []).append(f)
    
    for subj_facts in by_subject.values():
        subj_facts.sort(key=lambda x: x["t_valid_from"])
    
    # Strategy 1: PAST QUERY TRAPS (50%) - Query about PAST time, latest is wrong
    # This is the key adversarial case: ask "as of day X" where X < latest fact day
    past_query_count = int(question_count * 0.50)
    for _ in range(past_query_count):
        subject = rng.choice(list(by_subject.keys()))
        subj_facts = by_subject[subject]
        
        if len(subj_facts) < 2:
            continue
            
        domain = subj_facts[0]["domain"]
        
        # Pick a fact that's NOT the latest
        old_fact = rng.choice(subj_facts[:-1])
        
        # Query at or just after old_fact's validity ends
        # This is when old_fact is correct but there's a newer fact
        query_day = old_fact["t_valid_from"] + rng.randint(0, (old_fact["t_valid_until"] or days) - old_fact["t_valid_from"])
        query_day = min(query_day, days)
        
        # Verify old_fact is still valid at query_day
        if not (old_fact["t_valid_from"] <= query_day and (old_fact["t_valid_until"] is None or query_day <= old_fact["t_valid_until"])):
            continue
            
        # The trap: latest fact is from AFTER query_day, but we ask about query_day
        # A "just get latest" system will be wrong
        questions.append({
            "question_id": f"q{len(questions)+1}",
            "task_family": "PastQueryTrap",
            "prompt": f"As of day {query_day}, what was the value for {subject} in {domain}?",
            "as_of_day": query_day,
            "domain": domain,
            "subject": subject,
            "answer": old_fact["content"],
            "trap_type": "past_query"
        })
    
    # Strategy 2: CHANGE DETECTION (20%)
    change_count = int(question_count * 0.20)
    for _ in range(change_count):
        subjects_with_updates = [s for s, fs in by_subject.items() if len(fs) >= 2]
        if not subjects_with_updates:
            continue
            
        subject = rng.choice(subjects_with_updates)
        subj_facts = by_subject[subject]
        domain = subj_facts[0]["domain"]
        
        f1, f2 = rng.sample(subj_facts[:min(3, len(subj_facts))], 2)
        early_day = min(f1["t_valid_from"], f2["t_valid_from"])
        late_day = max(f1["t_valid_from"], f2["t_valid_from"])
        
        questions.append({
            "question_id": f"q{len(questions)+1}",
            "task_family": "ChangeDetection",
            "prompt": f"What changed for {subject} between day {early_day} and day {late_day}?",
            "start_day": early_day,
            "end_day": late_day,
            "domain": domain,
            "subject": subject,
            "answer": f"{f1['content']} -> {f2['content']}",
        })
    
    # Strategy 3: CURRENT QUERY (30%) - Easy questions where latest is correct
    # These are fair questions where the query time is at or after latest fact
    current_count = question_count - len(questions)
    for _ in range(current_count):
        subject = rng.choice(list(by_subject.keys()))
        subj_facts = by_subject[subject]
        domain = subj_facts[0]["domain"]
        
        # Query at or after the last update - these should be easy
        last_fact = subj_facts[-1]
        query_day = rng.randint(last_fact["t_valid_from"], days)
        
        questions.append({
            "question_id": f"q{len(questions)+1}",
            "task_family": "CurrentQuery",
            "prompt": f"As of day {query_day}, what is the current value for {subject}?",
            "as_of_day": query_day,
            "domain": domain,
            "subject": subject,
            "answer": last_fact["content"],
        })
    
    # Shuffle questions
    rng.shuffle(questions)
    
    # Re-number questions
    for i, q in enumerate(questions, 1):
        q["question_id"] = f"q{i}"
    
    return questions[:question_count]


def generate_events_for_causal(events: list[Event], days: int, seed: int, count: int = 100) -> list[dict]:
    """Generate action/outcome events for causal questions."""
    rng = random.Random(seed + 1000)
    causal_events = []
    
    for _ in range(count):
        ev = rng.choice(events)
        if ev.event_type == "FACT_OBSERVED":
            outcome_day = min(ev.t_event + rng.randint(1, 10), days)
            causal_events.append({
                "event_id": f"causal_{len(causal_events)+1}",
                "action_event": ev.event_id,
                "action_day": ev.t_event,
                "outcome_day": outcome_day,
                "domain": ev.domain,
                "subject": ev.subject,
                "t_event": ev.t_event,
                "event_type": "ACTION",
            })
    
    return causal_events


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate adversarial TemporalBench-v2")
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--questions", type=int, default=2000)
    ap.add_argument("--events-out", default="benchmarks/temporalbench_v2_events.jsonl")
    ap.add_argument("--facts-out", default="benchmarks/temporalbench_v2_facts.jsonl")
    ap.add_argument("--questions-out", default="benchmarks/temporalbench_v2_questions.jsonl")
    args = ap.parse_args()

    print("Generating base world...")
    events, facts, latest = generate_base_world(args.days, args.seed)
    
    print(f"Generated {len(events)} events, {len(facts)} facts")
    print("Generating adversarial questions...")
    
    questions = generate_adversarial_questions(facts, events, args.days, args.seed, args.questions)
    
    # Add some causal questions
    causal_events = generate_events_for_causal(events, args.days, args.seed)
    causal_questions = []
    for i, ce in enumerate(causal_events[:200]):
        causal_questions.append({
            "question_id": f"q{len(questions)+i+1}",
            "task_family": "CausalQuery",
            "prompt": f"Which change on day {ce['action_day']} caused the state on day {ce['outcome_day']} for {ce['subject']}?",
            "action_day": ce["action_day"],
            "outcome_day": ce["outcome_day"],
            "domain": ce["domain"],
            "subject": ce["subject"],
            "answer": ce["action_event"],
        })
    
    questions.extend(causal_questions)
    
    # Shuffle and trim
    random.Random(args.seed).shuffle(questions)
    questions = questions[:args.questions]

    write_jsonl(Path(args.events_out), [asdict(e) for e in events] + causal_events)
    write_jsonl(Path(args.facts_out), [asdict(f) for f in facts])
    write_jsonl(Path(args.questions_out), questions)

    print(f"wrote {len(events) + len(causal_events)} events -> {args.events_out}")
    print(f"wrote {len(facts)} facts -> {args.facts_out}")
    print(f"wrote {len(questions)} questions -> {args.questions_out}")
    
    # Print question distribution
    task_families = {}
    for q in questions:
        task_families[q["task_family"]] = task_families.get(q["task_family"], 0) + 1
    print("\nQuestion distribution:")
    for tf, count in sorted(task_families.items()):
        print(f"  {tf}: {count}")


if __name__ == "__main__":
    main()
