"""Second recount: sample-count cross table, force-definition cross table, m1b record contents."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control")
D = ROOT / r"06_analysis\02_control\paper\ml_jc"
h = json.load(open(D / "ml_jc_head.json", encoding="utf-8"))
det = json.load(open(D / "ml_jc_missed_detail.json", encoding="utf-8"))
FMIN = 9.41458911
SETS = ("train", "validation", "test", "OOD-1", "OOD-2", "MLJ")
rows = [(s, r) for s in SETS for it in h[s] for r in it["rows"] if r["scope"] == "scored"]
t = Counter()
for _, r in rows:
    t[("under" if r["true_at_samples_min_kN"] < FMIN else "between", "1" if r["samples"] == 1 else ">=2", "jc_miss" if r["JC_first_decision_s"] is None else "jc_ok", "jp_miss" if r["JP_first_decision_s"] is None else "jp_ok")] += 1
for k in sorted(t):
    print(k, t[k])
key = {(o["set"], o["run"], o["leg"], o["t_on"]): o for o in det}
x = Counter()
for s, r in rows:
    if r["JC_first_decision_s"] is None:
        o = key[(s, r["run"], r["leg"], round(r["t_on_s"], 1))]
        x[("1ms<=0" if o["min_window_kN"] <= 0 else "1ms>0", "rec<=0" if r["true_min_kN"] <= 0 else "rec>0", "lift" if r["is_lift"] else "nolift", "air" if o["air_ms"] > 0 else "noair")] += 1
for k in sorted(x):
    print(k, x[k])
print("median under ms", sorted(o["under_ms"] for o in det)[len(det) // 2])

M = ROOT / r"06_analysis\03_hydraulic\coupled\pressure_review\m1b"
for name in ("g4.jsonl", "r12.jsonl", "early.jsonl"):
    lines = (M / name).read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    print(name, "rows", len(lines), "keys", list(first.keys())[:40])
    txt = "\n".join(lines)
    for term in ("pressure", "J_P", "J_C", "contact", "combined", "missed", "M1_missed"):
        print("   ", term, txt.count(term))
    variants = Counter(str(json.loads(l).get("variant") or json.loads(l).get("mode")) for l in lines)
    print("   variants", variants.most_common(14))
j = json.load(open(M / "m1b_judgement.json", encoding="utf-8"))
print("judgement keys", list(j.keys())[:30])
print("files mentioning pressure-only under pressure_review:")
for p in (ROOT / r"06_analysis\03_hydraulic\coupled\pressure_review").rglob("*"):
    if p.is_file() and p.suffix in (".json", ".jsonl", ".md") and p.stat().st_size < 3e6:
        s = p.read_text(encoding="utf-8", errors="ignore")
        n = s.count("pressure_only") + s.count("J_P") + s.count('"contact": "pressure"') + s.count("압력만")
        if n:
            print("  ", p.relative_to(ROOT), n)
