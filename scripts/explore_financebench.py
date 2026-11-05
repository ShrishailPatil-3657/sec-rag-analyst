import json, glob

for path in glob.glob("data/financebench/data/*.jsonl"):
    rows = [json.loads(line) for line in open(path)]
    print("FILE:", path)
    print("rows:", len(rows))
    print("fields:", list(rows[0].keys()))
    for r in rows[:5]:
        print(r)
        print()