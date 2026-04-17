"""
Phase 2: Per-Question Accuracy Correlation Analysis
====================================================
Computes per-question features (temporal_distance, recency_score, fact_count, overlap)
and correlates them with per-system model accuracy.

Hypothesis: System A accuracy negatively correlates with temporal_distance (older = worse),
while Systems B/C/D stay flat (they use validity windows, not decay).
"""
import pandas as pd
import numpy as np
from pathlib import Path

RESULTS_DIR = Path(r'C:\Users\Zwmar\.openclaw\workspace\projects\time\results')
preds = pd.read_csv(RESULTS_DIR / 'per_question_predictions.csv')
feats = pd.read_csv(RESULTS_DIR / 'per_question_features.csv')

df = preds.merge(feats[['question_id', 'temporal_distance', 'recency_score', 'subject_fact_count']], on='question_id', how='left')

print("=" * 60)
print("PHASE 2: PER-QUESTION ACCURACY CORRELATION")
print("=" * 60)

# ── 1. Feature summary ──────────────────────────────────────────────────────
print("\n[Features] Per-question feature distributions:")
print(f"  temporal_distance: mean={df['temporal_distance'].mean():.3f}, std={df['temporal_distance'].std():.3f}, range=[{df['temporal_distance'].min():.3f}, {df['temporal_distance'].max():.3f}]")
print(f"  recency_score:     mean={df['recency_score'].mean():.3f}, std={df['recency_score'].std():.3f}, range=[{df['recency_score'].min():.3f}, {df['recency_score'].max():.3f}]")
print(f"  subject_fact_count: mean={df['subject_fact_count'].mean():.1f}, range=[{df['subject_fact_count'].min()}, {df['subject_fact_count'].max()}]")
print(f"  Total questions: {len(df)}")

# ── 2. Correlation: temporal_distance vs accuracy per system ────────────────
print("\n[Core Hypothesis Test]")
print("Does temporal_distance predict accuracy for System A but not B/C/D?")
print()

for sys in ['A', 'B', 'C', 'D']:
    s = df[df['system'] == sys].copy()
    # Pearson correlation
    corr = s['temporal_distance'].corr(s['correct'])
    # Spearman (rank-based, robust to non-linearity)
    spearman = s['temporal_distance'].corr(s['correct'], method='spearman')
    
    # Mean accuracy by temporal_distance quartile
    s['td_quartile'] = pd.qcut(s['temporal_distance'], q=4, labels=['Q1(oldest)', 'Q2', 'Q3', 'Q4(newest)'])
    quartile_acc = s.groupby('td_quartile')['correct'].mean()
    
    print(f"System {sys}:")
    print(f"  Pearson r(temporal_distance, accuracy) = {corr:.4f}")
    print(f"  Spearman rho = {spearman:.4f}")
    print(f"  Accuracy by temporal quartile: {dict(quartile_acc.round(3))}")
    print()

# ── 3. Recency score vs accuracy ────────────────────────────────────────────
print("[Recency Score vs Accuracy]")
for sys in ['A', 'B', 'C', 'D']:
    s = df[df['system'] == sys]
    corr = s['recency_score'].corr(s['correct'])
    spearman = s['recency_score'].corr(s['correct'], method='spearman')
    print(f"  System {sys}: Pearson={corr:.4f}, Spearman={spearman:.4f}")
print()

# ── 4. Near-present accuracy (recency >= 0.9) ───────────────────────────────
print("[Near-Present Accuracy] (recency_score >= 0.9 = most recent)")
for sys in ['A', 'B', 'C', 'D']:
    s = df[df['system'] == sys]
    near = s[s['recency_score'] >= 0.9]
    far = s[s['recency_score'] < 0.5]
    mid = s[(s['recency_score'] >= 0.5) & (s['recency_score'] < 0.9)]
    
    near_acc = near['correct'].mean() if len(near) > 0 else 0
    far_acc = far['correct'].mean() if len(far) > 0 else 0
    mid_acc = mid['correct'].mean() if len(mid) > 0 else 0
    
    print(f"  System {sys}: near={near_acc:.1%}(n={len(near)}), mid={mid_acc:.1%}(n={len(mid)}), far={far_acc:.1%}(n={len(far)})")
print()

# ── 5. Subject fact count vs accuracy ──────────────────────────────────────
print("[Subject Fact Count vs Accuracy]")
for sys in ['A', 'B', 'C', 'D']:
    s = df[df['system'] == sys]
    corr = s['subject_fact_count'].corr(s['correct'])
    print(f"  System {sys}: r={corr:.4f} (more facts = harder?)")
print()

# ── 6. OverlapQuery trap analysis ─────────────────────────────────────────
print("[OverlapQuery Trap Analysis]")
overlap = df[df['task_family'] == 'OverlapQuery']
for sys in ['A', 'B', 'C', 'D']:
    s = overlap[overlap['system'] == sys]
    acc = s['correct'].mean() if len(s) > 0 else 0
    print(f"  System {sys}: OverlapQuery accuracy = {acc:.1%} (n={len(s)})")
print()

# ── 7. Staleness error rate confirmation ───────────────────────────────────
print("[Staleness Error Rate] (predicted != expected AND expected is newer version)")
# A staleness error = model predicted an OLD version of a fact when a NEWER version exists
# We can detect this by checking if predicted version < expected version
def is_staleness_error(row):
    try:
        pred_ver = int(row['predicted'].split('v')[-1]) if 'v' in str(row['predicted']) else 0
        exp_ver = int(row['expected'].split('v')[-1]) if 'v' in str(row['expected']) else 0
        return row['correct'] == False and pred_ver < exp_ver
    except:
        return False

df['staleness_error'] = df.apply(is_staleness_error, axis=1)
staleness = df.groupby('system')['staleness_error'].mean()
print(f"  Staleness error rate by system: {dict(staleness.round(3))}")
print()

# ── 8. Per-version accuracy breakdown ──────────────────────────────────────
print("[Per-Version Accuracy] (v1=oldest, v4=newest)")
versions = df['expected'].str.extract(r'v(\d+)')[0].astype(float)
df['version'] = versions
for sys in ['A', 'B', 'C', 'D']:
    s = df[df['system'] == sys]
    by_v = s.groupby('version')['correct'].mean()
    print(f"  System {sys}: {dict(by_v.round(3))}")
print()

# ── 9. Summary table ────────────────────────────────────────────────────────
print("=" * 60)
print("SUMMARY: What predicts failure?")
print("=" * 60)
summary = []
for sys in ['A', 'B', 'C', 'D']:
    s = df[df['system'] == sys]
    near = s[s['recency_score'] >= 0.9]['correct'].mean()
    far = s[s['recency_score'] < 0.5]['correct'].mean()
    td_corr = s['temporal_distance'].corr(s['correct'])
    near_vs_far_gap = near - far
    staleness_rate = s['staleness_error'].mean()
    summary.append({
        'system': sys,
        'near_acc': near,
        'far_acc': far,
        'gap': near_vs_far_gap,
        'td_corr': td_corr,
        'staleness_err': staleness_rate
    })
summary_df = pd.DataFrame(summary)
print(summary_df.to_string(index=False))
print()

# ── 10. Key insight ─────────────────────────────────────────────────────────
print("[KEY INSIGHT]")
a = df[df['system'] == 'A']
bcd = df[df['system'].isin(['B', 'C', 'D'])]
a_near_acc = a[a['recency_score'] >= 0.9]['correct'].mean()
a_far_acc = a[a['recency_score'] < 0.5]['correct'].mean()
a_gap = a_near_acc - a_far_acc

bcd_near = bcd[bcd['recency_score'] >= 0.9]['correct'].mean()
bcd_far = bcd[bcd['recency_score'] < 0.5]['correct'].mean()
bcd_gap = bcd_near - bcd_far

print(f"System A near-far gap: {a_gap:+.3f} (near={a_near_acc:.1%}, far={a_far_acc:.1%})")
print(f"System B/C/D near-far gap: {bcd_gap:+.3f} (near={bcd_near:.1%}, far={bcd_far:.1%})")
if a_gap < bcd_gap:
    print('-> A is WORSE at near-present than far-past -> staleness problem CONFIRMED')
else:
    print('-> A is BETTER at near-present -> unexpected')