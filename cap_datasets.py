import pandas as pd, os

base = r"C:\Users\Zwmar\.openclaw\workspace\projects\time"
os.chdir(base)

for name in ["reversion", "ambiguity", "negation"]:
    df = pd.read_csv(f"datasets/temporal_{name}.csv")
    df = df.head(150)  # 150 per task, 450 total
    df.to_csv(f"datasets/temporal_{name}.csv", index=False)
    print(f"{name}: {len(df)} questions")