"""Spec rev. 69: second path for the r69_g8_screen.py gate quantities on chosen runs.

Path A = ``r69_g8_screen.job`` (re-run; its command hash must equal the batch JSON). Path B re-runs the same key
with its own loop record and computes the gate quantities from other signals:
  crawler lift-off time from the 1 ms crawler-force series (first 1 ms chunk with zero crawler force that stays zero
  for 0.1 s, in LEVEL) instead of the 10 Hz log; true cylinder force = pad contact - m_rod g from the controller
  geometry (YAML) instead of the plant ``Wr``; pad lift = pad gap > 0 instead of contact <= 0; final attitude = mean
  of the controller-independent plant attitude over the last 1 s re-sampled at 10 Hz from the log; FAULT from the
  controller's final phase and stroke-end steps; stroke at the end from the 10 Hz log; first contact of leg k from
  the pad gap (<= 0 for 0.1 s); crawler clearance as the gap of all crawler nodes above the base floor.

Usage (dynamics-dev): python -I r69_g8_xcheck.py <project_root> <batch_dir> <out_json>
"""
from __future__ import annotations

import json
import sys
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s8"))

import numpy as np  # noqa: E402

import r51_reapp_closed_loop as r51  # noqa: E402
import r67_g1_screen as r67  # noqa: E402
import r69_g8_screen as g8  # noqa: E402

KEYS = ["main|flat|top|0.0|RR|raised|55.0", "main|flat|bottom|8.0|FL|raised|5.0",
        "main|flat|top|4.0|FL|lowered|150.0", "slope|edge|top|4.0|FL|raised|170.0",
        "slope|edge|top|4.0|FL|raised|20.0", "slope|rpB|top|4.0|RR|raised|20.0"]


def path_b(key):
    mode, floor_id, level, fs, leg_name, kind, val = key.split("|")
    leg = None if leg_name == "ref" else g8.LEGS.index(leg_name)
    r51.place_worker()
    cl, c2, Meas = r51._imports()
    cl.rmf.CONFIG.clear()
    cl.rpt.RCFG.clear()
    plant, ctrl, info, _ = g8.make_base_g8(cl, c2, level, float(fs), g8.FLOORS[floor_id], leg,
                                           None if leg is None else (kind, float(val)))
    rec, crawler, log = [], [], []
    r67.run_base(cl, c2, Meas, plant, ctrl, rec=rec, crawler=crawler, log=log)
    rec = np.array(rec)
    t = rec[:, 0]
    contact, gap = rec[:, 1:5], rec[:, 13:17]
    cr = np.asarray(crawler)[-len(t):]
    tl = np.array([q[0] for q in log])
    ph = [q[1] for q in log]
    t_level = next(q[0] for q in log if q[1] == "level") - 0.1  # phase of a period is set at its end
    zero = (cr == 0.0) & (t >= t_level)
    n = 100
    run = np.convolve(zero.astype(int), np.ones(n, int), "valid")
    i0 = int(np.flatnonzero(run == n)[0])
    t_lift = float(t[i0])
    F = contact - np.asarray(ctrl.geometry.rod_weight_N, float)
    w = t >= t_lift
    mins = F[w].min(axis=0) / 1e3
    lift = (gap[w] > 0.0).sum(axis=0) * 1e-3
    k_tail = tl >= tl[-1] - 1.0 + 1e-9
    att_end = np.array([q[4] for q in log])[k_tail].mean(axis=0)
    out = {"t_lift_s": round(t_lift, 3), "min_F_after_liftoff_kN": {g8.LEGS[i]: round(float(mins[i]), 2) for i in range(4)},
           "lift_after_liftoff_s": {g8.LEGS[i]: round(float(lift[i]), 3) for i in range(4)},
           "att_end_deg_10Hz": [round(float(a), 4) for a in att_end],
           "fault": str(ctrl.phase) in ("fault", "fault_reground") or "fault" in ph,
           "stroke_end_mm_log": (np.asarray(log[-1][2]) * 1e3).round(2).tolist(),
           "crawler_clearance_all_nodes_mm": round(float(g8.crawler_node_heights(cl, plant).min()) * 1e3, 1)}
    if leg is not None:
        on = gap[:, leg] <= 0.0
        run = np.convolve(on.astype(int), np.ones(n, int), "valid")
        idx = np.flatnonzero(run == n)
        out["first_contact_s"] = None if not idx.size else round(float(t[idx[0]]), 3)
    return out


def job(key):
    a = g8.job(key)
    b = path_b(key)
    gA = a["gates"]
    d8A = min(a["min_F_after_liftoff_kN"].values())
    d8B = min(b["min_F_after_liftoff_kN"].values())
    gB = {"Fmin_plus5": d8B >= (g8.F_MIN_N + 5e3) / 1e3, "no_lift": all(v == 0 for v in b["lift_after_liftoff_s"].values()),
          "end_att": bool(np.all(np.abs(b["att_end_deg_10Hz"]) <= 0.2)), "fault0": not b["fault"],
          "stroke_end": max(b["stroke_end_mm_log"]) <= g8.STROKE_END_OK_M * 1e3}
    cmp = {k: (gA[k], gB[k]) for k in gB}
    return {"key": key, "cmd_sha256_A": a["cmd_sha256"], "t_lift_A": a["t_lift"], "t_lift_B": b["t_lift_s"],
            "D8_min_kN": [d8A, d8B], "lift_s": [a["lift_after_liftoff_s"], b["lift_after_liftoff_s"]],
            "att_end_deg": [a["att_end_deg"], b["att_end_deg_10Hz"]],
            "stroke_max_mm": [max(a["stroke_end_mm"]), max(b["stroke_end_mm_log"])],
            "first_contact_s": [(a.get("touch") or {}).get("first_contact_s"), b.get("first_contact_s")],
            "clearance_mm": [a["crawler_clearance_end_mm"], b["crawler_clearance_all_nodes_mm"]],
            "gates_A_vs_B": cmp, "gate_verdicts_equal": all(x == y for x, y in cmp.values())}


def main():
    batch = Path(sys.argv[2])
    stored = {}
    for p in batch.glob("r69_g8_*.json"):
        for r in json.loads(p.read_text(encoding="utf-8"))["results"]:
            stored[r["key"]] = r.get("cmd_sha256")
    with Pool(len(KEYS)) as pool:
        res = pool.map(job, KEYS)
    for r in res:
        r["cmd_sha256_batch"] = stored.get(r["key"])
        r["hash_equal_batch"] = r["cmd_sha256_A"] == r["cmd_sha256_batch"]
    Path(sys.argv[3]).write_text(json.dumps({"script": "04_scripts/03_control/s8/r69_g8_xcheck.py", "results": res},
                                            indent=1, default=float), encoding="utf-8")
    for r in res:
        print(json.dumps(r))


if __name__ == "__main__":
    main()
