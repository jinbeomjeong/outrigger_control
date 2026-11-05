"""Print item-9 rows of the stored batches, the CB batches and the v4 recheck for cases with events."""
import json
import re

R = r"C:\workspace\outrigger_control\07_results\S8"
A = r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\verdict\judgement_chrono\v4_recheck"
paths = {
    "p1r": R + r"\p1r_20261024_222013\verify_S8C.json",
    "rest": R + r"\rest_20261024_233615\verify_S8C.json",
    "cb_old": R + r"\cb_20261025_000840\verify_S8C.json",
    "cb_new": R + r"\cb_20261025_013946\verify_S8C.json",
    "recheck": A + r"\verify_final_v4recheck_20261104_202815.json",
}
PAT = re.compile(r"episodes (\d+) \(crawler_transient (\d+)\)")
for tag, p in paths.items():
    try:
        v = json.load(open(p, encoding="utf-8"))
    except FileNotFoundError:
        print(tag, "MISSING", p)
        continue
    print("=====", tag, "rev:", str(v["meta"].get("judge_revision"))[:120])
    totals = {}
    for r in v["rows"]:
        if not r["item"].startswith("item 9"):
            continue
        if r["item"].startswith("item 9 M5"):
            continue
        m = PAT.search(r.get("note") or "")
        if not m:
            print("  no-ep", r["case"], r["item"][:40], (r.get("note") or "")[:120])
            continue
        n, tr = int(m[1]), int(m[2])
        j = r.get("judge")
        t = totals.setdefault(j, [0, 0, 0, 0])
        t[0] += n
        t[1] += tr
        t[2] += r["value"][0] or 0
        t[3] += r["value"][1] or 0
        if n:
            print(f"  {r['case']:30s} {j} ep={n} tr={tr} M1={r['value'][0]} M1p={r['value'][1]} note={(r.get('note') or '')[:260]}")
    print("  totals [ep, transient, M1, M1p]", totals)
    if tag == "recheck":
        for c, m in v["s8_metrics"].items():
            print(" metric keys sample", c, [k for k in m.keys() if "ep" in k.lower() or "item" in k.lower() or "M1" in k][:12])
            break
