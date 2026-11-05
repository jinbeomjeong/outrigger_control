import json, sys
sys.stdout.reconfigure(encoding="utf-8")
p = r"C:\workspace\outrigger_control\06_analysis\02_control\s9\rev85\harness_chrono_pairs.json"
d = json.load(open(p, encoding="utf-8"))
print(json.dumps(d["pairs"][0]["delta"], ensure_ascii=False))
for key in ("pairs", "final_pairs"):
    acc = {}
    for r in d[key]:
        if r.get("superseded_by"):
            continue
        cens = r.get("censored_at_guard")
        for k, v in (r.get("delta") or {}).items():
            if isinstance(v, (int, float)):
                acc.setdefault((k, bool(cens)), []).append(v)
    for (k, c), v in sorted(acc.items()):
        print(key, k, "censored" if c else "uncens", len(v), round(min(v), 3), round(max(v), 3), round(sum(v) / len(v), 3))
