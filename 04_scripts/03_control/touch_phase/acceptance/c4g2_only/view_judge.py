"""Compact view of acceptance/c4g2_only/judgement.json, verify files, grid failures against both and off. E core 27."""
import json
from pathlib import Path

import psutil

psutil.Process().cpu_affinity([27])
ACC = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance")
O = ACC / "c4g2_only"
for v in ("verify_r79_L1L2.json", "verify_r79_L3.json"):
    print(v, (O / v).read_text(encoding="utf-8").replace("\n", "")[:500] if (O / v).exists() else "missing")
j = json.loads((O / "judgement.json").read_text(encoding="utf-8")) if (O / "judgement.json").exists() else None
if j:
    print("top", list(j))
    g = j["grid"]
    print("grid accept", g["accept"], "n", g["n"])
    for p in g["parts"]:
        print(" ", p.get("name"), {k: (len(v) if isinstance(v, list) else v) for k, v in p.items() if k not in ("name", "failed_rows")}, "p2f", p.get("pass_to_fail"), "f2p", (p.get("fail_to_pass") or [])[:8])
    n = j.get("noise_L2")
    print("noise_L2", json.dumps(n, default=str)[:2200])
    print("noise_L3", json.dumps(j.get("noise_L3_record"), default=str)[:900])
    for k in ("soil", "d8", "crawler", "regression_flat", "regression_A"):
        print(k, json.dumps(j.get(k), default=str)[:200])


def fails(fname):
    d = json.loads(Path(fname).read_text(encoding="utf-8"))
    out = {}
    for res in d["results"]:
        for i, r in enumerate(res["runs"]):
            out[(res["key"], r.get("event"), r.get("offset_s"), i)] = r
    return out


tot = {"c4g2": {}, "both": {}}
for f in ("grid_r67_main", "grid_r67_top", "grid_r69_top", "grid_r69_bottom"):
    a, b = fails(O / f"grid/{f}.json"), fails(ACC / f"grid/{f}.json")
    for name, runs in (("c4g2", a), ("both", b)):
        for k, r in runs.items():
            tot[name]["runs"] = tot[name].get("runs", 0) + 1
            tot[name]["fail"] = tot[name].get("fail", 0) + (not r["pass"])
            for gate, ok in r["gates"].items():
                if not ok:
                    tot[name][gate] = tot[name].get(gate, 0) + 1
            tot[name]["minF"] = min(tot[name].get("minF", 1e9), min((r.get("adj_min_F_in_W_kN") or {"x": 1e9}).values()))
            tot[name]["union_max"] = max(tot[name].get("union_max", 0), r.get("pair_union_s", 0))
    print(f, "wall", json.loads((O / f"grid/{f}.json").read_text(encoding="utf-8"))["meta"].get("wall_s"))
print("grid gate totals", json.dumps(tot))
