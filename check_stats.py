import csv
# Check per_seed_results for near/far accuracy
rows = []
with open('projects/time/results/per_seed_results.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['system'] == 'A' and row['version'] == 'v1':
            rows.append(row)
print('v1 System A per-seed:')
for r in rows[:5]:
    print(f"  seed={r['seed']} TemporalAccuracy={r['TemporalAccuracy']} TRS={r['TRS']}")

# Check per_question_correlation columns
import json
pq = [json.loads(l) for l in open('projects/time/results/per_question_correlation.csv')][:1]
if pq:
    print('PQ columns:', list(pq[0].keys()))
    # Check near/far stats
    near = [r for r in pq if r.get('temporal_distance', 999) <= 10]
    far = [r for r in pq if r.get('temporal_distance', 999) > 50]
    print(f"near questions: {len(near)}, far: {len(far)}")

# TODO (rotator): **Baseline A — Plain RAG Agent**

# TODO (rotator): **Baseline A — Plain RAG Agent**

# TODO (rotator): **Baseline A — Plain RAG Agent**

# TODO (rotator): **Baseline A — Plain RAG Agent**