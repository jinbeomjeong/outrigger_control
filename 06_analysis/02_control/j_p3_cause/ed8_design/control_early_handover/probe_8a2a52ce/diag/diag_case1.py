"""Diagnosis case 1: R12 bottom-FR-Fs4-RE1bF-ready o0.075, A vs H3 (VBM), post-event LEVEL.

Per run: phase timeline, stall signature (jp3_ed7_rules.is_stall_signature_ed7, spec v7 6.2 fixed
reading: T4h phase / t_s / motor_stroke_m, t_event), and 5 s windows of the post-event LEVEL:
held legs (plant locked and |u| > 0), mean |u| per leg vs u_hold, executed piston rate, twist
load D (T4h lsb_ib_twist_load_N = nu^T F), completion flags (on_target / clearance_done /
complete), attitude (controller roll / pitch), A(i)-b trigger predicate parts (which condition
held the trigger back) and A(i) stretch. Also the first 3 s per 0.1 s period (re-approach phase).

Usage: conda run -n dynamics-dev python -I -B diag_case1.py
Output: diag_case1_out.txt, diag_case1_windows.csv, diag_case1_trace.csv
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed7-impl")
sys.path.insert(0, str(WT / "04_scripts" / "04_hydraulic" / "coupled"))
import jp3_ed7_rules as rules  # noqa: E402

LEGS = ("FL", "FR", "RL", "RR")
U_HOLD = 0.01 * 0.020924
STEMS = {"A": "R12_bottom-FR-Fs4-o0.075-RE1bF-ready_P89-A-VBM",
         "H3": "R12_bottom-FR-Fs4-o0.075-RE1bF-ready_P89-H3-VBM"}


def longest(path: Path, tkey: str) -> dict:
    z = np.load(path, allow_pickle=False)
    objs = sorted({k.split("|")[0] for k in z.files})
    best = max(objs, key=lambda o: len(z[f"{o}|{tkey}"]) if f"{o}|{tkey}" in z.files else 0)
    return {k.split("|", 1)[1]: z[k] for k in z.files if k.startswith(best + "|")}


recs = {json.loads(x)["diag"]["stem"]: json.loads(x)
        for x in (RAW / "runs.jsonl").read_text("utf-8").splitlines()}
out, wrows, trows = [], [], []
lsb_settings = None
for arm, stem in STEMS.items():
    r = recs[stem]
    lsb_settings = r.get("lsb_settings")
    te = float(r["t_event_s"])
    z = dict(np.load(RAW / "t4h" / f"{stem}.npz", allow_pickle=False))
    t = z["t_s"]
    ph = np.char.lower(z["phase"].astype(str))
    stall = rules.is_stall_signature_ed7(list(ph), t, z["motor_stroke_m"], te)
    # stall conditions separately
    after = ph[t >= te]
    win = t >= t[-1] - rules.STALL_WINDOW_S - rules.STALL_WINDOW_TOLERANCE_S
    spans = z["motor_stroke_m"][win].max(axis=0) - z["motor_stroke_m"][win].min(axis=0)
    seg, last = [], None
    for tt, p in zip(t, ph):
        if p != last:
            seg.append((round(float(tt - te), 2), str(p)))
            last = p
    out.append(f"===== {arm} {stem} t_event {te}  T4h t_end {t[-1]:.2f} (rel {t[-1]-te:.2f})")
    out.append(f"  phases (rel s): {[s for s in seg if s[0] > -1]}")
    out.append(f"  stall signature ed7: {stall}; READY after event {'ready' in set(after)}; "
               f"last phase {ph[-1]}; any fault {bool(np.isin(ph, rules.FAULT_PHASES).any())}; "
               f"last-20 s stroke spans mm {np.round(spans * 1e3, 4).tolist()}")
    ctrl = longest(RAW / "logs" / f"{stem}_ctrl.npz", "m.t_s")
    plant = longest(RAW / "logs" / f"{stem}_plant.npz", "t")
    L = json.loads((RAW / "logs" / f"{stem}_lsb.json").read_text("utf-8"))
    fl = {round(f["t"], 3): f for f in L["floors"]}
    bt = L["blind_trigger"]
    u = z["command_m_s"]
    locked = z["locked"] > 0.5
    D = z["lsb_ib_twist_load_N"]
    lin, lout = z["lsb_input_m_s"], z["lsb_output_m_s"]
    lvl = np.flatnonzero((ph == "level") & (t > te))
    i0 = lvl[0]
    i1 = i0
    while i1 + 1 < len(t) and ph[i1 + 1] == "level":
        i1 += 1
    out.append(f"  post-event LEVEL {t[i0]-te:.2f} .. {t[i1]-te:.2f} s ({t[i1]-t[i0]+0.1:.1f} s)")
    ic = [int(np.argmin(np.abs(ctrl["m.t_s"] - t[k]))) for k in range(len(t))]
    ip = [int(np.argmin(np.abs(plant["t"] - t[k]))) for k in range(len(t))]
    x = plant["x"]
    for w0 in np.arange(0.0, t[i1] - te + 1e-9, 5.0):
        m = np.flatnonzero((t - te >= w0) & (t - te < w0 + 5.0) & (np.arange(len(t)) >= i0)
                           & (np.arange(len(t)) <= i1))
        if len(m) < 2:
            continue
        held = locked[m] & (np.abs(u[m]) > 1e-12)
        flags = [fl.get(round(float(t[k]), 3)) for k in m]
        on_t = np.mean([f["on_target"] for f in flags if f and f["on_target"] is not None] or [np.nan])
        clr = np.mean([f["clearance_done"] for f in flags if f and f["clearance_done"] is not None]
                      or [np.nan])
        cmp_ = np.mean([f["complete"] for f in flags if f and f["complete"] is not None] or [np.nan])
        btw = [b for b in bt if w0 <= b["t"] - te < w0 + 5.0]
        reasons = {}
        for b in btw:
            if b["result"]:
                key = "TRIGGER"
            elif b["a1_floor_on"]:
                key = "a1_floor_on"
            elif b["protected"]:
                key = "protected"
            elif not (b["still_m"] < b["still_limit_m"]):
                key = "moved(still>=limit)"
            elif not b["completion_open"]:
                key = "completion_closed"
            else:
                key = "other"
            reasons[f"{LEGS[b['leg']]}:{key}"] = reasons.get(f"{LEGS[b['leg']]}:{key}", 0) + 1
        vx = (x[ip[m[-1]]] - x[ip[m[0]]]) / max(t[m[-1]] - t[m[0]], 1e-9)
        roll = np.array([ctrl["s.roll_rad"][ic[k]] for k in m])
        pitch = np.array([ctrl["s.pitch_rad"][ic[k]] for k in m])
        row = {"arm": arm, "w0_rel_s": round(float(w0), 1), "periods": len(m),
               "held": {LEGS[j]: int(held[:, j].sum()) for j in range(4)},
               "locked": {LEGS[j]: int(locked[m, j].sum()) for j in range(4)},
               "mean_abs_u_mm_s": {LEGS[j]: round(float(np.abs(u[m, j]).mean()) * 1e3, 4)
                                   for j in range(4)},
               "subhold_periods": {LEGS[j]: int(((np.abs(u[m, j]) > 1e-12)
                                                 & (np.abs(u[m, j]) <= U_HOLD + 1e-12)).sum())
                                   for j in range(4)},
               "mean_vx_mm_s": {LEGS[j]: round(float(vx[j]) * 1e3, 4) for j in range(4)},
               "D_kN": [round(float(D[m[0]]) / 1e3, 2), round(float(D[m[-1]]) / 1e3, 2)],
               "roll_mrad": [round(float(roll.min()) * 1e3, 3), round(float(roll.max()) * 1e3, 3)],
               "pitch_mrad": [round(float(pitch.min()) * 1e3, 3), round(float(pitch.max()) * 1e3, 3)],
               "on_target": round(float(on_t), 2), "clearance_done": round(float(clr), 2),
               "complete": round(float(cmp_), 2),
               "ib_trigger_checks": reasons,
               "ib_on": int(np.sum(z["lsb_ib_on"][m])), "a1_on": int(np.sum(z["lsb_a1_on"][m]))}
        wrows.append(row)
        out.append("  " + json.dumps(row))
    for k in range(max(i0 - 1, 0), i1 + 1):
        f = fl.get(round(float(t[k]), 3)) or {}
        trows.append({"arm": arm, "t_rel_s": round(float(t[k] - te), 2), "phase": str(ph[k]),
                      **{f"u_{LEGS[j]}_mm_s": round(float(u[k, j]) * 1e3, 4) for j in range(4)},
                      **{f"in_{LEGS[j]}_mm_s": round(float(lin[k, j]) * 1e3, 4) for j in range(4)},
                      **{f"locked_{LEGS[j]}": int(locked[k, j]) for j in range(4)},
                      **{f"F_{LEGS[j]}_kN": round(float(z["true_force_N"][k, j]) / 1e3, 2)
                         for j in range(4)},
                      **{f"stroke_{LEGS[j]}_mm": round(float(z["motor_stroke_m"][k, j]) * 1e3, 3)
                         for j in range(4)},
                      "D_kN": round(float(D[k]) / 1e3, 3),
                      "roll_mrad": round(float(ctrl["s.roll_rad"][ic[k]]) * 1e3, 4),
                      "pitch_mrad": round(float(ctrl["s.pitch_rad"][ic[k]]) * 1e3, 4),
                      "on_target": f.get("on_target"), "clearance_done": f.get("clearance_done"),
                      "complete": f.get("complete"),
                      "ib_stretch": json.dumps(f.get("ib_stretch")),
                      "a1_stretch": json.dumps(f.get("a1_stretch")),
                      "ib_on": json.dumps(f.get("ib_on")), "a1_on": json.dumps(f.get("a1_on"))})
    # completion-flag decomposition if the controller state has it
    keys = [k for k in ctrl if k.startswith("s.completion_flags.")]
    out.append(f"  completion flag fields: {keys}")
    tail = [k for k in range(len(t)) if t[k] - te > 20.0 and ph[k] == "level"]
    if tail:
        cf = {k.split(".")[-1]: float(np.mean([ctrl[k][ic[j]] > 0.5 for j in tail])) for k in keys}
        out.append(f"  completion flags share after +20 s (LEVEL periods): {cf}")
out.append(f"lsb_settings: {json.dumps(lsb_settings)[:1500]}")
for name, rows in (("windows", wrows), ("trace", trows)):
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with (HERE / f"diag_case1_{name}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in r.items()})
text = "\n".join(out)
(HERE / "diag_case1_out.txt").write_text(text, "utf-8")
print(text.encode("ascii", "replace").decode())
