import pandas as pd

preds = pd.read_csv(r'C:\Users\Zwmar\.openclaw\workspace\projects\time\results\per_question_predictions.csv')
feats = pd.read_csv(r'C:\Users\Zwmar\.openclaw\workspace\projects\time\results\per_question_features.csv')
df = preds.merge(feats[['question_id','temporal_distance','recency_score']], on='question_id', how='left')

# DecayTrap deep dive
print('=== DECAYTRAP DEEP DIVE (ALL SYSTEMS) ===')
dt = df[df['task_family']=='DecayTrap']
for sys in ['A','B','C','D']:
    s = dt[dt['system']==sys]
    acc = s['correct'].mean()
    print(f'System {sys}: {acc:.1%} ({len(s)} questions)')

print()
print('=== DECAYTRAP BY DOMAIN ===')
for sys in ['A','B','C','D']:
    s = dt[dt['system']==sys]
    by_d = s.groupby('domain')['correct'].agg(['mean','count'])
    print(f'System {sys}:')
    for dom in ['fast','medium','slow']:
        if dom in by_d.index:
            val = by_d.loc[dom,'mean']
            cnt = by_d.loc[dom,'count']
            print(f'  {dom}: {val:.1%} (n={cnt})')
    print()

print('=== DECAYTRAP: WHAT GOES WRONG? ===')
d_dt = dt[dt['system']=='D']
d_dt_wrong = d_dt[~d_dt['correct']]
print(f'D wrong on {len(d_dt_wrong)} / {len(d_dt)} DecayTrap questions')
print()

# Compare wrong patterns across systems
for sys in ['A','B','C','D']:
    s_dt = dt[dt['system']==sys]
    wrong = s_dt[~s_dt['correct']]
    # extract version numbers from predictions
    # pattern: subject:key:dXX:vYY
    wrong_versions = wrong['expected'].str.extract(r'd(\d+):v(\d+)')
    pred_versions = wrong['predicted'].str.extract(r'd(\d+):v(\d+)')
    if len(wrong_versions) > 0:
        wrong_versions.columns = ['exp_d','exp_v']
        pred_versions.columns = ['pred_d','pred_v']
        merged = pd.concat([wrong_versions, pred_versions], axis=1)
        avg_d_diff = (merged['exp_d'].astype(float) - merged['pred_d'].astype(float)).mean()
        avg_v_diff = (merged['exp_v'].astype(float) - merged['pred_v'].astype(float)).mean()
        print(f'{sys}: avg day diff on errors = {avg_d_diff:.1f}, avg version diff = {avg_v_diff:.1f}')

print()
print('=== DECAYTRAP SAMPLE WRONG (D) ===')
print(d_dt_wrong[['question_id','predicted','expected','recency_score','domain']].head(20).to_string())

print()
print('=== ALL SYSTEMS: DECAYTRAP RECENCY CURVE ===')
for sys in ['A','B','C','D']:
    s = dt[dt['system']==sys]
    bins = [0, 0.3, 0.5, 0.7, 0.9, 1.01]
    labels = ['0-0.3','0.3-0.5','0.5-0.7','0.7-0.9','0.9-1.0']
    s['recency_bin'] = pd.cut(s['recency_score'], bins=bins, labels=labels)
    by_bin = s.groupby('recency_bin')['correct'].agg(['mean','count'])
    print(f'System {sys}:')
    for label in labels:
        if label in by_bin.index:
            val = by_bin.loc[label,'mean']
            cnt = by_bin.loc[label,'count']
            print(f'  recency {label}: {val:.1%} (n={cnt})')
    print()

print('=== SYSTEM C vs D: WHERE DO THEY DIFFER? ===')
c_preds = df[df['system']=='C'][['question_id','correct','predicted','expected']].rename(columns={'correct':'c_correct','predicted':'c_pred','expected':'c_exp'})
d_preds = df[df['system']=='D'][['question_id','correct','predicted','expected']].rename(columns={'correct':'d_correct','predicted':'d_pred','expected':'d_exp'})
merged = c_preds.merge(d_preds, on='question_id')

# Questions C gets right, D gets wrong
c_right_d_wrong = merged[(merged['c_correct']==True) & (merged['d_correct']==False)]
print(f'C right, D wrong: {len(c_right_d_wrong)} questions')

# Breakdown by task_family
diff_by_task = c_right_d_wrong.groupby('task_family').size()
print('By task family:')
print(diff_by_task.sort_values(ascending=False).to_string())
print()

# Questions D gets right, C gets wrong
d_right_c_wrong = merged[(merged['d_correct']==True) & (merged['c_correct']==False)]
print(f'D right, C wrong: {len(d_right_c_wrong)} questions')
diff_by_task2 = d_right_c_wrong.groupby('task_family').size()
print('By task family:')
print(diff_by_task2.sort_values(ascending=False).to_string())
print()

print('=== OTHER PUBLISHED BENCHMARKS TO COMPARE AGAINST ===')
print('ARC-AGI: abstraction and reasoning (Kaggle)')
print('BigBench: 200+ diverse tasks')
print('GPQA: PhD-level reasoning')
print('MMLU: 57 subjects, mass-multiple choice')
print('HellaSwag: common sense reasoning')
print('TruthfulQA: truthfulness and falsehood detection')
print('TemporalBench (THIS benchmark): temporal reasoning with recency emphasis')
print()
print('For temporal specifically:')
print('- TempReason (Zhou et al.): explicit temporal logic')
print('- TimelineQA: timeline-based question answering')
print('- ClocQ: temporal knowledge graph probing')
print('- BLiMP: grammar temporal phenomena')