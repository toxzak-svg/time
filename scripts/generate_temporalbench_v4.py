#!/usr/bin/env python3
"""Generate TemporalBench-v4 - EXTREME ADVERSARIAL designed to break TTA.

Key adversarial features:
1. 50% OVERLAPPING FACTS - multiple facts valid simultaneously
2. CONFUSING TIMESTAMPS - facts appear valid but are misleading
3. DECAY-OPTIMIZED QUERIES - query at times where decay makes wrong choice
4. HIGH CONFIDENCE OLD FACTS - old facts with high confidence confuse decay
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

DOMAINS = {
    "slow": {"subjects": [f"hw{i}" for i in range(10)], "update_p": 0.12},
    "medium": {"subjects": [f"api{i}" for i in range(10)], "update_p": 0.25},
    "fast": {"subjects": [f"sts{i}" for i in range(20)], "update_p": 0.75},
}


@dataclass
class Fact:
    fact_id: str
    content: str
    t_valid_from: int
    t_valid_until: Optional[int]
    domain: str
    confidence: float
    decay_fn: str


def generate_v4(days: int, seed: int, question_count: int) -> tuple[list[dict], list[dict], list[dict]]:
    """Generate extreme adversarial dataset."""
    rng = random.Random(seed)
    events, facts = [], []
    subject_version = {}
    
    fid = 0
    
    for day in range(1, days + 1):
        for domain, cfg in DOMAINS.items():
            for subject in cfg["subjects"]:
                key = f"{domain}:{subject}"
                
                if key not in subject_version:
                    subject_version[key] = 0
                
                # Higher update rate = more facts = more confusion
                if rng.random() < cfg["update_p"]:
                    subject_version[key] += 1
                    version = subject_version[key]
                    value = f"{domain}:{subject}:d{day}:v{version}:{rng.randint(1000,9999)}"
                    
                    fid += 1
                    conf = round(0.7 + rng.random() * 0.3, 3)  # High confidence
                    
                    # 50% of time, let facts overlap (no t_valid_until)
                    if rng.random() < 0.5:
                        t_until = None
                    else:
                        t_until = day - 1 if version > 1 else None
                    
                    facts.append({
                        "fact_id": f"f{fid}",
                        "content": value,
                        "t_valid_from": day,
                        "t_valid_until": t_until,
                        "domain": domain,
                        "confidence": conf,
                        "decay_fn": "domain_half_life"
                    })
                    
                    events.append({
                        "event_id": f"e{fid}",
                        "t_event": day,
                        "t_observed": day,
                        "domain": domain,
                        "event_type": "FACT_OBSERVED" if version == 1 else "FACT_SUPERSEDED",
                        "subject": subject,
                        "value": value,
                        "supersedes": None,
                        "source_reliability": conf
                    })
    
    # Group facts by subject
    by_subject = {}
    for f in facts:
        subject = f["content"].split(":")[1]
        by_subject.setdefault(subject, []).append(f)
    
    for s in by_subject:
        by_subject[s].sort(key=lambda x: x["t_valid_from"])
    
    questions = []
    
    # STRATEGY 1: Overlap queries (40%) - when multiple valid
    overlap_q = int(question_count * 0.40)
    for _ in range(overlap_q):
        subject = rng.choice(list(by_subject.keys()))
        subj_facts = by_subject[subject]
        domain = subj_facts[0]["domain"]
        
        # Find facts with None t_valid_until (overlapping)
        overlapping = [f for f in subj_facts if f["t_valid_until"] is None]
        if len(overlapping) >= 2:
            # Query at a time when multiple overlap
            f1, f2 = overlapping[0], overlapping[-1]
            query_day = rng.randint(f1["t_valid_from"], min(f2["t_valid_from"] + 5, days))
            
            # The correct answer: fact valid at query_day
            valid_at_q = [f for f in subj_facts if f["t_valid_from"] <= query_day and (f["t_valid_until"] is None or query_day <= f["t_valid_until"])]
            if valid_at_q:
                answer = max(valid_at_q, key=lambda x: x["t_valid_from"])["content"]
                questions.append({
                    "question_id": f"q{len(questions)+1}",
                    "task_family": "OverlapQuery",
                    "prompt": f"As of day {query_day}, what is the value for {subject}?",
                    "as_of_day": query_day,
                    "domain": domain,
                    "subject": subject,
                    "answer": answer
                })
    
    # STRATEGY 2: Past query traps (30%)
    past_q = int(question_count * 0.30)
    for _ in range(past_q):
        subject = rng.choice(list(by_subject.keys()))
        subj_facts = by_subject[subject]
        domain = subj_facts[0]["domain"]
        
        if len(subj_facts) >= 2:
            old_fact = rng.choice(subj_facts[:-1])
            query_day = old_fact["t_valid_from"] + rng.randint(1, 10)
            query_day = min(query_day, days)
            
            if old_fact["t_valid_from"] <= query_day and (old_fact["t_valid_until"] is None or query_day <= old_fact["t_valid_until"]):
                questions.append({
                    "question_id": f"q{len(questions)+1}",
                    "task_family": "PastQueryTrap",
                    "prompt": f"As of day {query_day}, what was the value for {subject}?",
                    "as_of_day": query_day,
                    "domain": domain,
                    "subject": subject,
                    "answer": old_fact["content"]
                })
    
    # STRATEGY 3: Current queries (30%)
    current_q = question_count - len(questions)
    for _ in range(current_q):
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
            "answer": last_fact["content"]
        })
    
    rng.shuffle(questions)
    for i, q in enumerate(questions, 1):
        q["question_id"] = f"q{i}"
    
    return events, facts, questions[:question_count]


def main():
    import random
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--seed", type=int, default=999)
    ap.add_argument("--questions", type=int, default=2000)
    args = ap.parse_args()
    
    events, facts, questions = generate_v4(args.days, args.seed, args.questions)
    
    Path("benchmarks").mkdir(exist_ok=True)
    
    with open("benchmarks/temporalbench_v4_events.jsonl", "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
    
    with open("benchmarks/temporalbench_v4_facts.jsonl", "w") as f:
        for fct in facts:
            f.write(json.dumps(fct) + "\n")
    
    with open("benchmarks/temporalbench_v4_questions.jsonl", "w") as f:
        for q in questions:
            f.write(json.dumps(q) + "\n")
    
    dist = {}
    for q in questions:
        dist[q["task_family"]] = dist.get(q["task_family"], 0) + 1
    print(f"Generated {len(events)} events, {len(facts)} facts, {len(questions)} questions")
    print(f"Distribution: {dist}")


if __name__ == "__main__":
    main()
