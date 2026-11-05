"""Complete the C4G2-only bundle and rejudge. Bundles shown K1-inactive by gap_check are copied from the C4G2 + K1 run (D8, crawler, r79 regression, x426), clip_A is cut from the new soil_A J2 jobs, all listed in reused_bundles.json.
Then acc_judge --acc c4g2_only (saved judgement overwritten, the former kept as judgement_before_gap.json) and comparison tables: soil and regression against stored off and both. E core 27. Writes rejudge_view.json."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import psutil

psutil.Process().cpu_affinity([27])
HERE = Path(__file__).resolve().parent
ACC = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance")
O = ACC / "c4g2_only"
REV85 = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9\rev85")
load = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))

copied = []
for rel in ("d8/d8_both.json", "d8/d8_main_off.json", "crawler/crawler_both.json", "regression/clip_x426_C.json", "regression/clip_x426_D.json", "regression/clip_r79_L1L2.json", "regression/clip_r79_L3L4.json"):
    (O / rel).parent.mkdir(parents=True, exist_ok=True)
    if not (O / rel).exists():
        shutil.copy2(ACC / rel, O / rel)
        copied.append(rel)
soil = load(O / "soil/soil_A.json")
clip_old = load(ACC / "regression/clip_A.json")
keys = {r["key"] for r in clip_old["results"]}
(O / "regression/clip_A.json").write_text(json.dumps({"meta": {**soil["meta"], "note": "cut from c4g2_only soil_A J2 jobs; stored clip_A hashes equal soil_A"}, "results": [r for r in soil["results"] if r["key"] in keys]}, default=float), encoding="utf-8")
(O / "reused_bundles.json").write_text(json.dumps({"rule": "gap_check: no re-approach start or no retrigger event, so C4G2 + K1 row = C4G2-only row", "copied": copied or "already there", "cut": "regression/clip_A.json from soil/soil_A.json"}, indent=1), encoding="utf-8")
if (O / "judgement.json").exists() and not (O / "judgement_before_gap.json").exists():
    shutil.copy2(O / "judgement.json", O / "judgement_before_gap.json")
step = next(s for s in load(HERE / "steps_c4g2only.json") if s["id"] == "judge")
r = subprocess.run(step["cmd"].split(), env={**os.environ, **step["env"]}, cwd=step["cwd"], capture_output=True, text=True, timeout=1800)
print("acc_judge rc", r.returncode, r.stderr[-400:])
J = load(O / "judgement.json")
print("top", list(J))
for k in ("grid",):
    print(k, "accept", J[k]["accept"])
print("soil", json.dumps({k: v for k, v in J["soil"].items() if k not in ("runs", "rows", "chrono_pick", "candidates")}, default=str)[:1800])
print("regression_flat", json.dumps(J["regression_flat"], default=str)[:1600])
print("regression_A", json.dumps(J["regression_A"], default=str)[:900])
print("regression_r79_L1L2", json.dumps({k: (v if not isinstance(v, list) or len(v) < 8 else len(v)) for k, v in J["regression_r79_L1L2"].items()} if isinstance(J["regression_r79_L1L2"], dict) else J["regression_r79_L1L2"], default=str)[:700])
print("d8", json.dumps({k: v for k, v in J["d8"].items() if not isinstance(v, (list,)) or len(v) < 6}, default=str)[:900])
print("crawler", json.dumps({k: v for k, v in J["crawler"].items() if not isinstance(v, (list,)) or len(v) < 6}, default=str)[:900])

# soil comparison
off = {r["key"]: r for r in load(REV85 / "finB2_A.json")["results"]}
both = {r["key"]: r for r in load(ACC / "soil/soil_A.json")["results"]}
rows = []
for res in soil["results"]:
    for i, run in enumerate(res["runs"]):
        o = next(x for x in off[res["key"]]["runs"] if x.get("timing") == run.get("timing") and x.get("event") == run.get("event"))
        b = both[res["key"]]["runs"][i]
        rows.append({"key": res["key"], "timing": run.get("timing"), "event": run.get("event"), "pass": run["pass"], "pass_off": o["pass"], "pass_both": b["pass"], "same_off": run["commands_sha256"] == o["commands_sha256"], "same_both": run["commands_sha256"] == b["commands_sha256"],
                     "fail": [k for k, v in run["gates"].items() if not v], "starts": len(run["reapproach_starts"]), "union": run.get("pair_union_s"), "union_both": b.get("pair_union_s"), "last_touch": run.get("pair_last_touch_s"), "min_after_W": min(run["min_F_after_W_kN"].values()), "min_after_W_both": min(b["min_F_after_W_kN"].values()), "min_after_W_off": min(o["min_F_after_W_kN"].values()), "lift_out": run.get("adj_lift_outside_W_s"), "adj_min": run["adj_min_F_in_W_kN"], "ready": run["t_ready_back_s"], "ready_off": o["t_ready_back_s"], "ready_both": b["t_ready_back_s"], "base_same_off": res["base"]["commands_sha256"] == off[res["key"]]["base"]["commands_sha256"], "flags": run.get("flags"), "wrongF": run["min_F_after_W_kN"], "crawler": run["crawler"]})
print("soil totals runs", len(rows), "pass", sum(r["pass"] for r in rows), "same as off", sum(r["same_off"] for r in rows), "same as both", sum(r["same_both"] for r in rows), "p2f vs off", [(r["key"], r["event"], r["timing"], r["fail"]) for r in rows if r["pass_off"] and not r["pass"]], "f2p vs off", [(r["key"], r["event"]) for r in rows if r["pass"] and not r["pass_off"]], "p2f vs both", [(r["key"], r["event"], r["timing"], r["fail"]) for r in rows if r["pass_both"] and not r["pass"]])
gap = load(O / "gap_check.json")["soil_A"]
dset = {(g["key"], g["timing"], g["event"]) for g in gap if g["class"] == "D"}
for r in rows:
    if (r["key"], r["timing"], r["event"]) in dset:
        print(" D", r["key"], r["event"], "same_off", r["same_off"], "same_both", r["same_both"], "pass c/o/b", r["pass"], r["pass_off"], r["pass_both"], "fail", r["fail"], "starts", r["starts"], "union", r["union"], r["union_both"], "minAfterW c/o/b", r["min_after_W"], r["min_after_W_off"], r["min_after_W_both"], "ready c/o/b", r["ready"], r["ready_off"], r["ready_both"], "base_off", r["base_same_off"], "adj", r["adj_min"], "lift_out", r["lift_out"])
print("non-D changed vs off", [(r["key"], r["event"], r["timing"]) for r in rows if (r["key"], r["timing"], r["event"]) not in dset and not r["same_off"]])
# regression records
reg = {}
for f in ("clip_harness", "clip_p0"):
    a, b = load(O / f"regression/{f}.json")["records"], load(ACC / f"regression/{f}.json")["records"]
    bm = {x["id"]: x for x in b}
    reg[f] = [{"id": x["id"], "passed": x.get("passed"), "verdict": x.get("verdict"), "failed": x.get("failed_rows"), "same_both": x.get("hash") == bm[x["id"]].get("hash"), "t_ready": x.get("t_ready_s"), "t_ready_both": bm[x["id"]].get("t_ready_s"), "minF": x.get("min_force_kN"), "minF_both": bm[x["id"]].get("min_force_kN"), "warnings": x.get("warnings"), "flags": x.get("flags")} for x in a]
    print(f, "n", len(a), "passed", sum(bool(x["passed"]) for x in reg[f]), "same hash as both", sum(x["same_both"] for x in reg[f]), "not passed", [(x["id"], x["failed"]) for x in reg[f] if not x["passed"]], "different", [(x["id"], x["t_ready"], x["t_ready_both"], x["minF"], x["minF_both"]) for x in reg[f] if not x["same_both"]])
(O / "rejudge_view.json").write_text(json.dumps({"soil": rows, "regression": reg}, indent=1, default=float), encoding="utf-8")
