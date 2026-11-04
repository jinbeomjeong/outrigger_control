"""Stored flow-on S8 soil row: limit windows, first contact, delivered speed and travel, eps for 1/3 and 2/3 of a period. Read only."""
import json
from pathlib import Path

import numpy as np

D = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_COUPLED_eta085_20261104_142213\S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0")
r = json.loads((D / "result.json").read_text(encoding="utf-8"))
print("args flow", {k: v for k, v in r["args"].items() if k.startswith("flow")}, "out_root", r["args"]["out_root"], "t_loop", r["t_loop_start_s"])
print("phases", [(round(p["t_s"], 1), p["phase"]) for p in r["phases"]], "loc", [round(e["t_s"], 1) for e in r["events"] if e["name"] == "crawler_liftoff_confirmed"])
print("code", json.dumps(r["code_state"]["git_at_start"])[:300])
fl = r["flow_limit"]
print("flow keys", list(fl))
print("summary keys", list(fl["summary"]))
print("max_sum_over_supply", fl["summary"].get("max_sum_Q_over_supply_minus_1"), "steps", fl["summary"].get("steps"))
z = np.load(D / "flow_series.npz", allow_pickle=True)
rows, cols = z["rows"], [str(c) for c in z["columns"]]
supply = float(z["supply_m3_s"])
i = {c: k for k, c in enumerate(cols)}
t = rows[:, i["t"]]
print("flow t range", t[0], t[-1], "n", len(t), "supply L/min", supply * 6e4)
lim = rows[:, i["limited_mask"]].astype(int) > 0
edges = np.diff(np.concatenate(([0], lim.astype(int), [0])))
runs = [(round(float(t[a]), 3), round(float(t[b - 1]), 3)) for a, b in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1), strict=True)]
print("limit runs >= 0.05 s", [x for x in runs if x[1] - x[0] >= 0.05][:12], "first", runs[:2])
LEGS = ("FL", "FR", "RL", "RR")
v = rows[:, [i[f"v_{l}"] for l in LEGS]]
u = rows[:, [i[f"u_{l}"] for l in LEGS]]
oil = rows[:, [i[f"oil_force_{l}"] for l in LEGS]]
s9 = np.load(D / "step_series.npz", allow_pickle=False)
ts, Fn, sm = s9["t_s"], s9["scm_pad_normal_N"], s9["s_motor_m"] * 1e3
print("oil force before contact max per leg kN, t 20-25", np.round(oil[(t > 20) & (t < 25)].max(axis=0) / 1e3, 3))
GATE = 12.85
kg = int(np.searchsorted(ts, GATE))
tc = {}
for j, l in enumerate(LEGS):
    k3 = int(np.argmax(Fn[:, j] > 3000.0))
    tc[l] = float(ts[k3])
    kv = int(np.searchsorted(t, ts[k3] - 0.15))
    print(l, "t_F3kN", round(float(ts[k3]), 3), "phase in 0.1 s", round(float(ts[k3] % 0.1), 3), "s_motor", round(float(sm[k3, j]), 3), "v delivered mm/s before contact", np.round(v[kv, j] * 1e3, 3), "u", np.round(u[kv, j] * 1e3, 3))
first = min(tc.values())
kf = int(np.searchsorted(ts, first))
travel = sm[kf] - sm[kg]
print("first contact", first, "s at first", np.round(sm[kf], 3), "travel from gate", np.round(travel, 3))
kvf = int(np.searchsorted(t, first - 0.15))
vf = v[kvf] * 1e3
print("v before first contact mm/s", np.round(vf, 3))
for tq in (13.0, 14.0, 16.0, 20.0, 24.0, 28.0, 29.0, 30.0, 31.0, 32.0, 32.5, 33.0):
    k = int(np.searchsorted(t, tq))
    print("t", tq, "u", np.round(u[k] * 1e3, 2), "v", np.round(v[k] * 1e3, 2), "mask", int(rows[k, i["limited_mask"]]), "Qdem", round(float(rows[k, i["Q_dem"]] * 6e4), 2), "Qsum", round(float(rows[k, i["Q_sum"]] * 6e4), 2))
# delay per leg with travel to that leg's contact and its speed there
for frac in (1 / 3, 2 / 3):
    e = {}
    for j, l in enumerate(LEGS):
        k3 = int(np.searchsorted(ts, tc[l]))
        kv = int(np.searchsorted(t, tc[l] - 0.15))
        e[l] = frac * 0.1 * v[kv, j] * 1e3 / max(sm[k3, j] - sm[kg, j], 1e-9)
    print("frac", round(frac, 3), "eps per leg contact", {k: round(float(x), 6) for k, x in e.items()})
