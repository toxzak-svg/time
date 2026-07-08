#!/usr/bin/env python3
"""Generate TemporalBench-v3 - ULTRA-ADVERSARIAL that stresses TTA components.

Goals to break TTA:
1. DECAY TRAPS: Query at times where old-but-confident facts should beat new ones
2. OVERLAP TRAPS: Multiple facts valid simultaneously, tie-breaking matters  
3. AMBIGUOUS VALIDITY: Facts where t_valid_until is unclear
4. OBSERVATION DELAY: Facts known later than they occurred
5. HIGH-FREQUENCY UPDATES: Create many close-together updates
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
        "subjects": [f"hw_{i}" for i in range(15)] + [f"spec_{i}" for i in range(15)],
        "update_p": 0.15,
    },
    "medium": {
        "subjects": [f"api_{i}" for i in range(15)] + [f"mdl_{i}" for i in range(15)] + [f"prc_{i}" for i in range(10)],
        "update_p": 0.30,
    },
    "fast": {
        "subjects": [f"sts_{i}" for i in range(25)] + [f"inc_{i}" for i in range(25)] + [f"doc_{i}" for i in range(20)],
        "update_p": 0.80,  # Very high update rate
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


def generate_base_world_v3(days: int, seed: int) -> tuple[list[Event], list[Fact]]:
    """Generate world with overlapping facts and observation delays."""
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
                
                # Add observation delay - fact known later than it occurred
                obs_delay = rng.randint(0, 3) if version > 1 else 0
                value = f"{domain}:{subject}:d{day}:v{version}:{rng.randint(1000,9999)}"
                prev = latest_event_by_subject.get(key)

                eid += 1
                ev = Event(
                    event_id=f"e{eid}",
                    t_event=day,
                    t_observed=min(days, day + obs_delay),
                    domain=domain,
                    event_type="FACT_OBSERVED" if prev is None else "FACT_SUPERSEDED",
                    subject=subject,
                    value=value,
                    supersedes=prev.event_id if prev else None,
                    source_reliability=round(0.5 + rng.random() * 0.5, 3),
                )
                events.append(ev)
                latest_event_by_subject[key] = ev

                # Don't always close previous fact's validity - create overlaps
                if prev and rng.random() < 0.7:  # 70% of the time, close it
                    for f in reversed(facts):
                        if f.content.startswith(f"{domain}:{subject}:") and f.t_valid_until is None:
                            f.t_valid_until = day - 1
                            break
                # 30% of time, leave it overlapping

                # Vary confidence - some facts more reliable than others
                conf = round(0.6 + rng.random() * 0.4, 3)
                
                fid += 1
                facts.append(
                    Fact(
                        fact_id=f"f{fid}",
                        content=value,
                        t_valid_from=day,
                        t_valid_until=None,  # Will be set later
                        domain=domain,
                        confidence=conf,
                        decay_fn="domain_half_life",
                    )
                )

    return events, facts


def generate_adversarial_questions_v3(
    facts: list[Fact], 
    events: list[Event], 
    days: int, 
    seed: int,
    question_count: int
) -> list[dict]:
    """Generate ultra-adversarial questions that stress TTA."""
    rng = random.Random(seed + 500)
    questions: list[dict] = []
    
    facts_dict = [asdict(f) for f in facts]
    
    # Group facts by subject
    by_subject: dict[str, list[dict]] = {}
    for f in facts_dict:
        subject = f["content"].split(":")[1]
        by_subject.setdefault(subject, []).append(f)
    
    for subj_facts in by_subject.values():
        subj_facts.sort(key=lambda x: x["t_valid_from"])
    
    # Strategy 1: DECAY TRAPS (30%) - Query old times where decay hurts
    # At old query times, a slightly older but high-confidence fact might be "correct"
    # but decay might prefer newer ones
    decay_count = int(question_count * 0.30)
    for _ in range(decay_count):
        subjects = [s for s, fs in by_subject.items() if len(fs) >= 2]
        if not subjects:
            continue
        subject = rng.choice(subjects)
        subj_facts = by_subject[subject]
        domain = subj_facts[0]["domain"]
        
        # Pick an old fact and query at a time when decay would hurt
        if len(subj_facts) >= 2:
            old_fact = subj_facts[0]  # Very old fact
            # Query at mid-point where decay might not favor old enough fact
            query_day = old_fact["t_valid_from"] + rng.randint(5, 15)
            if query_day <= days:
                questions.append({
                    "question_id": f"q{len(questions)+1}",
                    "task_family": "DecayTrap",
                    "prompt": f"As of day {query_day}, what is the value for {subject}?",
                    "as_of_day": query_day,
                    "domain": domain,
                    "subject": subject,
                    "answer": old_fact["content"],
                    "trap_type": "decay"
                })
    
    # Strategy 2: OVERLAP TRAPS (25%) - Query when multiple facts valid
    # TTA must pick the right one based on decay/scoring
    overlap_count = int(question_count * 0.25)
    for _ in range(overlap_count):
        subjects = [s for s, fs in by_subject.items() if len(fs) >= 2]
        if not subjects:
            continue
        subject = rng.choice(subjects)
        subj_facts = by_subject[subject]
        domain = subj_facts[0]["domain"]
        
        # Find overlapping facts
        if len(subj_facts) >= 2:
            f1, f2 = subj_facts[0], subj_facts[1]
            # Query at time when both might be valid
            query_day = max(f1["t_valid_from"], f2["t_valid_from"]) + rng.randint(0, 3)
            if query_day <= days:
                questions.append({
                    "question_id": f"q{len(questions)+1}",
                    "task_family": "OverlapTrap",
                    "prompt": f"As of day {query_day}, what is the value for {subject}?",
                    "as_of_day": query_day,
                    "domain": domain,
                    "subject": subject,
                    "answer": f2["content"],  # Newer one typically correct
                    "trap_type": "overlap"
                })
    
    # Strategy 3: PAST QUERY TRAPS (25%) - The classic trap
    past_count = int(question_count * 0.25)
    for _ in range(past_count):
        subjects = [s for s, fs in by_subject.items() if len(fs) >= 2]
        if not subjects:
            continue
        subject = rng.choice(subjects)
        subj_facts = by_subject[subject]
        domain = subj_facts[0]["domain"]
        
        old_fact = rng.choice(subj_facts[:-1])
        query_day = old_fact["t_valid_from"] + rng.randint(0, (old_fact["t_valid_until"] or days) - old_fact["t_valid_from"])
        query_day = min(query_day, days)
        
        if old_fact["t_valid_from"] <= query_day and (old_fact["t_valid_until"] is None or query_day <= old_fact["t_valid_until"]):
            questions.append({
                "question_id": f"q{len(questions)+1}",
                "task_family": "PastQueryTrap",
                "prompt": f"As of day {query_day}, what was the value for {subject}?",
                "as_of_day": query_day,
                "domain": domain,
                "subject": subject,
                "answer": old_fact["content"],
                "trap_type": "past_query"
            })
    
    # Strategy 4: CURRENT QUERY (remaining) - Easy baseline
    current_count = question_count - len(questions)
    for _ in range(current_count):
        subject = rng.choice(list(by_subject.keys()))
        subj_facts = by_subject[subject]
        domain = subj_facts[0]["domain"]
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
    
    rng.shuffle(questions)
    for i, q in enumerate(questions, 1):
        q["question_id"] = f"q{i}"
    
    return questions[:question_count]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate ultra-adversarial TemporalBench-v3")
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--seed", type=int, default=123)
    ap.add_argument("--questions", type=int, default=2000)
    ap.add_argument("--events-out", default="benchmarks/temporalbench_v3_events.jsonl")
    ap.add_argument("--facts-out", default="benchmarks/temporalbench_v3_facts.jsonl")
    ap.add_argument("--questions-out", default="benchmarks/temporalbench_v3_questions.jsonl")
    args = ap.parse_args()

    print("Generating ultra-adversarial v3 world...")
    events, facts = generate_base_world_v3(args.days, args.seed)
    
    print(f"Generated {len(events)} events, {len(facts)} facts")
    print("Generating adversarial questions...")
    
    questions = generate_adversarial_questions_v3(facts, events, args.days, args.seed, args.questions)
    
    # Add causal questions
    causal_rng = random.Random(args.seed + 1000)
    causal_events = []
    for i, ev in enumerate(events[:100]):
        if ev.event_type == "FACT_OBSERVED":
            outcome_day = min(ev.t_event + causal_rng.randint(1, 10), args.days)
            causal_events.append({
                "event_id": f"causal_{i}",
                "action_event": ev.event_id,
                "action_day": ev.t_event,
                "outcome_day": outcome_day,
                "domain": ev.domain,
                "subject": ev.subject,
                "t_event": ev.t_event,
                "event_type": "ACTION",
            })
    
    causal_questions = []
    for i, ce in enumerate(causal_events[:100]):
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

    # Change detection (optional): pairs of facts for "what changed between start_day and end_day?"
    facts_dict = [asdict(f) for f in facts]
    by_subject: dict[str, list[dict]] = {}
    for f in facts_dict:
        subject = f["content"].split(":")[1]
        by_subject.setdefault(subject, []).append(f)
    change_rng = random.Random(args.seed + 2000)
    change_questions = []
    for _ in range(50):
        subjects = [s for s, fs in by_subject.items() if len(fs) >= 2]
        if not subjects:
            break
        subject = change_rng.choice(subjects)
        subj_facts = sorted(by_subject[subject], key=lambda x: x["t_valid_from"])
        f1, f2 = subj_facts[0], subj_facts[1]
        early_day, late_day = f1["t_valid_from"], f2["t_valid_from"]
        if early_day >= late_day:
            continue
        domain = f1["domain"]
        change_questions.append({
            "question_id": f"q{len(questions)+len(change_questions)+1}",
            "task_family": "ChangeDetection",
            "prompt": f"What changed for {subject} between day {early_day} and day {late_day}?",
            "start_day": early_day,
            "end_day": late_day,
            "domain": domain,
            "subject": subject,
            "answer": f"{f1['content']} -> {f2['content']}",
        })
    questions.extend(change_questions)

    random.Random(args.seed).shuffle(questions)
    questions = questions[:args.questions]

    write_jsonl(Path(args.events_out), [asdict(e) for e in events] + causal_events)
    write_jsonl(Path(args.facts_out), [asdict(f) for f in facts])
    write_jsonl(Path(args.questions_out), questions)

    print(f"wrote {len(events) + len(causal_events)} events -> {args.events_out}")
    print(f"wrote {len(facts)} facts -> {args.facts_out}")
    print(f"wrote {len(questions)} questions -> {args.questions_out}")
    
    task_families = {}
    for q in questions:
        task_families[q["task_family"]] = task_families.get(q["task_family"], 0) + 1
    print("\nQuestion distribution:")
    for tf, count in sorted(task_families.items()):
        print(f"  {tf}: {count}")


if __name__ == "__main__":
    main()
