"""Aggregate final-controller harness results, part 5 (read-only)."""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9")
R = ROOT / "rev85"
L = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
A = L(R / "finB2_A.json")["results"]
per = defaultdict(Counter); fl = Counter(); minF = defaultdict(list); lift = defaultdict(list); pres = defaultdict(list)
for job in A:
    for run in job["runs"]:
        per[job["soil"]][run["pass"]] += 1
        fl.update(run.get("flags") or [])
        if run.get("min_F_after_W_kN") is not None: minF[job["soil"]].append(run["min_F_after_W_kN"])
        for k in ("lifts",):
            pass
        p = run.get("pressure") or {}
        if isinstance(p, dict):
            v = p.get("event_window_max_bar") or p.get("max_event_bar") or p.get("in_window_max_bar")
            if v is not None: pres[job["soil"]].append(v)
print("A per soil", {k: dict(v) for k, v in per.items()}, "flags", dict(fl))
print("A minF after W sample", json.dumps(next(iter(minF.values()))[0])[:300])
print("A pressure keys", list((A[0]["runs"][0].get("pressure") or {}).keys()))
for job in A:
    for run in job["runs"]:
        if not run["pass"]:
            print("  A fail", job["key"], run["event"], run["timing"], {k: v for k, v in run["gates"].items() if v is not True})
cmpA = L(R / "finB2_A_cmp.json")
for row in cmpA["rows"]:
    if row["pass_before"] != row["pass_after"] or (row.get("d_ready_back_s") and abs(row["d_ready_back_s"]) > 5):
        print("  Acmp", row["key"], row["pass_before"], "->", row["pass_after"], row.get("d_ready_back_s"), row.get("flags_after"))
# H9
H9 = L(R / "finB2_h9.json")["records"]
for r in H9:
    print("  H9", r["id"], r["verdict"], r["failed_rows"], None if r["t_ready_s"] is None else round(r["t_ready_s"], 1), round(r["max_stroke_mm"], 1), round(r["min_force_kN"] or -1, 1), round(r.get("rut_ready_mm") or -1, 1))
# r67
for n in ("finB2_r67_main_cmp.json", "finB2_r67_top_cmp.json"):
    c = L(R / n)
    rows = c["rows"]
    print(n, c["summary"], "pass_after", sum(1 for r in rows if r["pass_after"]), "/", len(rows))
# pairs table
Pp = L(R / "harness_chrono_pairs.json")
print("by_variable_side", json.dumps(Pp["summary"]["by_variable_side"], ensure_ascii=False))
print("pairs keys", list(Pp["pairs"][0].keys()), list(Pp["pairs"][0]["delta"].keys()), list(Pp["pairs"][0]["chrono"].keys()))
for p in Pp["pairs"]:
    d = p["delta"]
    print("  P", p["variable"], "|", p["chrono_case"], "|", p["harness_id"], "|", p["side"], "|", p["chrono"].get("verdict"), "/", p["harness"].get("verdict"), "|", {k: (round(v, 2) if isinstance(v, (int, float)) else v) for k, v in d.items()}, "|", p.get("chrono_version_note"))
for s in Pp["static_pairs"]:
    print("  S", s)
