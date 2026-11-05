"""Collect the tables of the report into summary.json and print them."""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

BASE = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\pressure_review")
OUT = BASE / "m1_hopsan"
summary = {}
t1 = json.loads((OUT / "t1_floor.json").read_text(encoding="utf-8"))
t5 = {r["name"]: r for r in json.loads((OUT / "t5_formula.json").read_text(encoding="utf-8"))["rows"]}
table = defaultdict(dict)
for r in t1:
    if r["cmd"] != "0.25vmax":
        continue
    key = (("FR" if r["leg"] == 1 else "RL"), int(r["p_h_target"]), int(r["fs0_kN"]))
    table[key][r["mode"]] = {"stroke": round(r["stroke_open_mm"], 2), "t_open": round(r["t_open_s"], 3), "m1": round(r["formula_mm"], 2), "m1b": round(t5[r["name"]]["m1b_mm"], 2), "p_r_pre": round(r["p_r_pre"], 2), "void": round(r["void_mm"], 2)}
summary["t1_at_0.25vmax"] = {str(k): v for k, v in table.items()}
print("leg ph fs | mode: Hopsan mm (M1, M1b)")
for k, v in table.items():
    print(k, {m: (x["stroke"], x["m1"], x["m1b"]) for m, x in v.items() if m in ("ramp_vent", "ramp_floor_ref", "ramp_lowcrack", "ramp_block", "IC_floor", "ramp_vent_pT0")})
# speed independence
sp = defaultdict(list)
for r in t1:
    sp[(r["leg"], r["p_h_target"], r["fs0_kN"], r["mode"])].append(r["stroke_open_mm"])
spread = max((max(x) - min(x)) / min(x) for x in sp.values())
print("largest stroke spread across command speeds", round(spread, 4))
summary["speed_spread"] = spread
t2 = json.loads((OUT / "t2_chop.json").read_text(encoding="utf-8"))
res = defaultdict(lambda: defaultdict(int))
errs = defaultdict(list)
for r in t2:
    h = r["t_open_hopsan"]
    h = None if h != h else h
    for name in ("rule", "literal", "drain"):
        x = r[f"t_open_{name}"]
        if h is None and x is None:
            res[r["variant"]][f"{name}_both_none"] += 1
        elif (h is None) != (x is None):
            res[r["variant"]][f"{name}_wrong_outcome"] += 1
        else:
            errs[(r["variant"], name)].append(abs(x / h - 1.0))
for v, d in res.items():
    print(v, dict(d), {name: (len(errs[(v, name)]), round(max(errs[(v, name)]), 3) if errs[(v, name)] else None, round(float(np.median(errs[(v, name)])), 3) if errs[(v, name)] else None) for name in ("rule", "literal", "drain")})
summary["t2_counts"] = {v: dict(d) for v, d in res.items()}
summary["t2_errors"] = {f"{k[0]}|{k[1]}": {"n": len(x), "max": max(x) if x else None, "median": float(np.median(x)) if x else None} for k, x in errs.items()}
rows = json.loads((OUT / "t4_replay.json").read_text(encoding="utf-8"))
main = {(r["job"]["variant"], r["job"]["offset_s"]): r for r in (json.loads(x) for x in (BASE / "m1" / "main.jsonl").read_text(encoding="utf-8").splitlines()) if r["job"]["case"] == "R12"}
agg = defaultdict(list)
for r in rows:
    h = main[(r["commands"], r["offset"])]
    f = r["F_min_kN"]
    agg[(r["circuit"], r["commands"])].append([f["RR"], r["Foil_min_kN"]["RR"], r["F_avg025_min_kN"]["RR"], r["F_min_t_s"]["RR"], h["event_output"]["min_F_after_event_kN"]["RR"], f["FL"], f["FR"], f["RL"]])
print("circuit cmds | RR load, RR oil, RR avg, t_min, harness RR, FL, FR, RL")
tab = {}
for k, v in agg.items():
    a = np.array(v)
    tab[str(k)] = {"RR_load": [a[:, 0].min(), a[:, 0].max()], "RR_oil": [a[:, 1].min(), a[:, 1].max()], "RR_avg025": [a[:, 2].min(), a[:, 2].max()], "t_min": [a[:, 3].min(), a[:, 3].max()], "harness_RR": [a[:, 4].min(), a[:, 4].max()], "FL": [a[:, 5].min(), a[:, 5].max()], "FR": [a[:, 6].min(), a[:, 6].max()], "RL": [a[:, 7].min(), a[:, 7].max()]}
    print(k, " | ".join(f"{a[:, i].min():.1f}..{a[:, i].max():.1f}" for i in range(a.shape[1])))
summary["t4_table"] = tab
print("open times offset 0.025")
op = {}
for r in rows:
    if r["circuit"] in ("vent", "vent_ref", "lowcrack", "block", "block_db") and r["commands"] in ("V1", "B1"):
        op.setdefault(f"{r['circuit']}|{r['commands']}", []).append(r["t_first_head_check_open_s"])
for k, v in op.items():
    print(k, {leg: [round(x[leg], 2) for x in v] for leg in ("FL", "FR", "RL", "RR")})
summary["t4_open"] = op
for off in (0.0, 0.025, 0.05, 0.075):
    for variant in ("V1", "B1"):
        h = main[(variant, off)]
        t0 = h["values"]["times"]["t_first_ready_s"] + 5.0 + off
        fills = [(["FL", "FR", "RL", "RR"][f[2]], f[3], round(f[0] - t0, 2), round(f[1] - t0, 2), f[4], f[5], f[6]) for f in h["m1"]["fills"] if t0 < f[1] < t0 + 2.5]
        print("harness", variant, off, fills)
        summary[f"harness_fills_{variant}_{off}"] = fills
conv = json.loads((OUT / "t4_conv_5e-06.json").read_text(encoding="utf-8"))
base = {(r["circuit"], r["commands"], r["offset"]): r for r in rows}
for r in conv:
    b = base[(r["circuit"], r["commands"], r["offset"])]
    print("conv", r["circuit"], {leg: (round(b["F_min_kN"][leg], 2), round(r["F_min_kN"][leg], 2)) for leg in ("RR", "FR", "RL")})
summary["t4_conv"] = [{"circuit": r["circuit"], "F_min_5e-6": r["F_min_kN"], "F_min_1e-5": base[(r["circuit"], r["commands"], r["offset"])]["F_min_kN"]} for r in conv]
(OUT / "summary.json").write_text(json.dumps(summary, indent=0, default=float), encoding="utf-8")
