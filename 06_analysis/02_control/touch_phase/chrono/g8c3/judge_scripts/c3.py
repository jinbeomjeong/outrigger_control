"""Why c_RL(t_P) differs between the harness and Chrono: strokes, loads and the plane estimate at t_P; RL pad position against the L2b patch."""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "cad_c4g2" / "wt" / "03_src"))
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.control import c2  # noqa: E402

geo = c2.C2Geometry.from_params(load_params(level="top"))
ORDER = [3, 2, 1, 0]  # corners RR, RL, FR, FL -> FL, FR, RL, RR
B = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_g8c3_20261105")
RUNS = {"R2L1": B / "G8C3_top_rpB_RL_g230_off", "R3L1": B / "G8C3_top_rpB_RL_g230_C4G2", "R2": B / "G8CL2b_top_rpB_RL_g230_Fs4_off", "R3": B / "G8CL2b_top_rpB_RL_g230_Fs4_C4G2"}
out2 = json.loads((HERE / "c2_out.json").read_text(encoding="utf-8"))
print("plane fit sensitivity dc_RL/ds per leg (FL, FR, RL, RR):", np.round([(geo.clearance_corners_m(np.eye(4)[i] * 1e-3)[1] - geo.clearance_corners_m(np.zeros(4))[1]) * 1e3 for i in range(4)], 3))
print("zero-stroke corners, FL FR RL RR mm", (geo.clearance_corners_m(np.zeros(4))[ORDER] * 1e3).round(1))
for line in (HERE / "out1.jsonl").read_text(encoding="utf-8").splitlines():
    r = json.loads(line)
    if r["key"].split("|")[3] != "29" or not r["key"].startswith("L1"):
        continue
    tp = r["loc"]["t_P"]
    tr = r["trace"]
    i = int(np.argmin([abs(x["t"] - tp) for x in tr]))
    x = tr[i]
    rod = np.array(x["r"]) * 1e-3
    c = geo.clearance_corners_m(rod)[ORDER] * 1e3
    lev0 = tr[0]
    print("harness", r["tag"], "t_P", round(tp, 1), "since LEVEL", round(tp - lev0["t"], 1), "m", x["m"], "r", x["r"], "m-r", np.round(np.array(x["m"]) - np.array(x["r"]), 2).tolist(), "F", x["F"], "c(FL,FR,RL,RR)", c.round(2).tolist(), "logged c(RR,RL,FR,FL)", r["loc"]["corner_c_tP_mm"], "true gap", x["cc"])
for name, d in RUNS.items():
    rec = np.load(d / "record" / "record.npz")
    res = out2[name]
    i = int(np.argmin(np.abs(rec["t"] - (res["t_P"] + res["t0"]))))
    corr = rec["meas.stroke_corrected"][i]
    m = rec["meas.stroke"][i]
    c = geo.clearance_corners_m(corr)[ORDER] * 1e3
    print("chrono", name, "t_P", round(res["t_P"], 1), "since LEVEL", round(res["t_P"] - res["t_level"], 1), "m", (m * 1e3).round(2).tolist(), "r", (corr * 1e3).round(2).tolist(), "m-r", ((m - corr) * 1e3).round(2).tolist(), "F", (rec["F_cyl"][i] / 1e3).round(1).tolist(), "c", c.round(2).tolist(), "true gap", round(res["cc_tP"], 2), "crawler N", np.linalg.norm(rec["F_crawler"][i]).round(0))
    # strokes at the LEVEL start, and the F at the TOUCH end
    il = int(np.argmin(np.abs(rec["t"] - (res["t_level"] + res["t0"]))))
    print("   LEVEL start m", (rec["meas.stroke"][il] * 1e3).round(2).tolist(), "r", (rec["meas.stroke_corrected"][il] * 1e3).round(2).tolist(), "F", (rec["F_cyl"][il] / 1e3).round(1).tolist(), "crawler kN", round(float(np.linalg.norm(rec["F_crawler"][il])) / 1e3, 1), "c", (geo.clearance_corners_m(rec["meas.stroke_corrected"][il])[ORDER] * 1e3).round(1).tolist())
# RL pad position on the L2b patch
d = RUNS["R3"]
pads = np.load(d / "pads.npz")
rec = np.load(d / "record" / "record.npz")
res = json.loads((d / "result.json").read_text(encoding="utf-8"))
g8 = res["g8"]
print({k: g8.get(k) for k in g8 if k not in ("crawler_gap", "crawler_gap_end_m")})
pc = rec["pad_in_contact"][:, 2]
t = rec["t"] - res["settings"]["start_t_s"]
on = np.flatnonzero(pc > 0)
print("RL pad_in_contact first", t[on[0]], "last", t[on[-1]], "gaps in contact after first", int((pc[on[0]:] <= 0).sum()))
cp = pads["contact_point_world"][:, 2, :]
ok = np.linalg.norm(cp, axis=1) > 0
tp = pads["t"] - res["settings"]["start_t_s"]
sel = ok & (tp > t[on[0]])
print("RL contact point world first", cp[sel][0].round(4).tolist(), "last", cp[sel][-1].round(4).tolist(), "range", np.ptp(cp[sel], axis=0).round(4).tolist(), "N end kN", round(float(pads["N"][-1, 2]) / 1e3, 1), "slip total end", np.round(pads["slip_total"][-1, 2], 4).tolist(), "sliding frac", round(float(pads["sliding"][sel, 2].mean()), 4))
for n2, d2 in RUNS.items():
    p2 = np.load(d2 / "pads.npz")
    print(n2, "F_cyl end", (p2["F_cyl"][-1] / 1e3).round(1).tolist(), "N end", (p2["N"][-1] / 1e3).round(1).tolist())
