import pandas as pd
import numpy as np

preds = pd.read_csv(r'C:\Users\Zwmar\.openclaw\workspace\projects\time\results\per_question_predictions.csv')
feats = pd.read_csv(r'C:\Users\Zwmar\.openclaw\workspace\projects\time\results\per_question_features.csv')

# Merge on question_id only
df = preds.merge(feats[['question_id','temporal_distance','recency_score']], on='question_id', how='left')

# recency_score: 0 = oldest, 1 = most recent
df['is_near'] = df['recency_score'] >= 0.9
df['is_far'] = df['recency_score'] < 0.5

systems = ['A','B','C','D']
print('=== RECENCY BREAKDOWN (recency_score >= 0.9 = near, < 0.5 = far) ===')
for sys in systems:
    s = df[df['system']==sys]
    near = s[s['is_near']]
    far = s[s['is_far']]
    mid = s[~s['is_near'] & ~s['is_far']]
    
    print(f'System {sys}:')
    print(f'  Near (recency>=0.9): {near["correct"].mean():.1%} ({len(near)} q)')
    print(f'  Mid (0.5<=recency<0.9): {mid["correct"].mean():.1%} ({len(mid)} q)')
    print(f'  Far (recency<0.5): {far["correct"].mean():.1%} ({len(far)} q)')
    print()

print('=== TASK FAMILY ACCURACY FOR ALL SYSTEMS ===')
task_stats = df.groupby(['system','task_family']).agg(
    total=('correct','count'),
    acc=('correct','mean')
).reset_index()
task_pivot = task_stats.pivot(index='task_family', columns='system', values='acc').round(3)
print(task_pivot.to_string())
print()

print('=== TOP FAILURE TYPES FOR SYSTEM D ===')
d = df[df['system']=='D']
d_wrong = d[~d['correct']]
wrong_top = d_wrong.groupby(['task_family','domain']).agg(
    count=('correct','size'),
    recency_avg=('recency_score','mean')
).reset_index().sort_values('count', ascending=False).head(20)
print(wrong_top.to_string())
print()

print('=== NEAR FAILURE PATTERNS (System D, recency >= 0.9) ===')
d_near = d[d['is_near']]
near_wrong = d_near[~d_near['correct']]
print(f'D near failures: {len(near_wrong)} / {len(d_near)} ({len(near_wrong)/len(d_near)*100:.1f}%)')
near_fail_types = near_wrong.groupby(['task_family','domain']).size().reset_index(name='count').sort_values('count', ascending=False).head(15)
print(near_fail_types.to_string())
print()

print('=== WHAT DOES D PREDICT ON FAILING NEAR QUERIES? ===')
near_fail_pred = near_wrong.groupby(['predicted','expected']).size().reset_index(name='count').sort_values('count', ascending=False).head(10)
print(near_fail_pred.to_string())