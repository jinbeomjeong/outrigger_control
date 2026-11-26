"""a04: the failed lines (and their V0 / VBJ / VBL twins) from a01, plus phase timelines
from T4h for the end_att lines. Writes a04_failed_lines.json and prints a compact table."""
import csv
import json
import os

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
J9 = r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
rows = list(csv.DictReader(open(os.path.join(OUT, "a01_line_summary.csv"), encoding="utf-8")))

S7 = [r for r in rows if r["case"] == "S7"]
print("== S7 t_first_ready by setting/eps")
tab = {}
for r in S7:
    eps = r["key"].split("|")[1]
    tab.setdefault(r["source"] + ":" + r["setting"], {})[eps] = (
        r["t_first_ready_s"], r["t_first_done_s"], r["level_done_n"], r["stiff_n"])
for k, v in tab.items():
    print(k, json.dumps(v))

print("== R12 top-*-Fs0 lines (t_ready_back, final)")
for r in rows:
    if r["case"] == "R12" and "|top|" in r["key"] and r["key"].endswith("|0.0") and \
            r["source"] in ("V0", "ed5_j9main", "ed6rec_j9main", "ed7_j9main", "ed7_sens",
                            "ed6rec_sens"):
        if r["setting"] in ("V0", "VB", "VBJ", "VBL", "VBM", "LS4", "LSJ4", "LSL4", "LSM4",
                            "VBMslow", "VBLv15", "VBLv05"):
            print(r["source"], r["setting"], r["key"], r["final_phase"], r["t_event_s"],
                  r["t_ready_back_s"], r["ib_shots"], r["warn_names"])


def timeline(path):
    z = np.load(path, allow_pickle=False)
    t = z["t_s"]
    ph = z["phase"].astype(str)
    runs = []
    s = 0
    for i in range(1, len(ph) + 1):
        if i == len(ph) or ph[i] != ph[s]:
            runs.append([ph[s], round(float(t[s]), 1), round(float(t[i - 1]), 1)])
            s = i
    locked = z["locked"]
    stroke = z["motor_stroke_m"]
    cmd = z["command_m_s"]
    ib = z["lsb_ib_on"] if "lsb_ib_on" in z.files else None
    tw = z["lsb_ib_twist_load_N"] if "lsb_ib_twist_load_N" in z.files else None
    last20 = t >= t[-1] - 20.0
    return {"runs": runs, "t_end": round(float(t[-1]), 1),
            "last20_stroke_span_mm": [round(float(np.ptp(stroke[last20, i])) * 1e3, 3)
                                      for i in range(4)],
            "last20_locked_frac": [round(float(locked[last20, i].mean()), 2) for i in range(4)],
            "ib_on_periods": None if ib is None else [int(ib[:, i].sum()) for i in range(4)],
            "max_abs_twist_kN_level": None if tw is None else round(
                float(np.nanmax(np.abs(tw))) / 1e3, 2),
            "blind_dwell": blind_dwell(t, ph, cmd, locked)}


def blind_dwell(t, ph, cmd, locked, u_hold=0.01 * 0.020924):
    """Longest run of 0 < |u| <= u_hold while locked, LEVEL only, per leg (s)."""
    out = []
    for i in range(4):
        best = 0.0
        run = 0
        for k in range(len(t)):
            u = abs(cmd[k, i])
            if ph[k] == "level" and 0 < u <= u_hold + 1e-12 and locked[k, i]:
                run += 1
                best = max(best, run * 0.1)
            else:
                run = 0
        out.append(round(best, 1))
    return out


TL = {
    "LSM4 R12_top-FR-Fs0-o0.05": J9 + r"\8a2a52ce\j9main_a1\j9_main_t4h\R12_top-FR-Fs0-o0.05_LSM4.npz",
    "VBM R12_top-FR-Fs0-o0.05": J9 + r"\8a2a52ce\j9main_a1\j9_main_t4h\R12_top-FR-Fs0-o0.05_VBM.npz",
    "LSL4 R12_top-FR-Fs0-o0.05": J9 + r"\79495405\records_after_stop\B_a1\j9_main_t4h\R12_top-FR-Fs0-o0.05_LSL4.npz",
    "VBMslow R12_top-FL-Fs0-o0.0": J9 + r"\8a2a52ce\sens_a1\sens_t4h\R12_top-FL-Fs0-o0.0_VBMslow.npz",
    "VBMslow R12_top-FL-Fs0-o0.05": J9 + r"\8a2a52ce\sens_a1\sens_t4h\R12_top-FL-Fs0-o0.05_VBMslow.npz",
    "VBM R12_top-FL-Fs0-o0.0": J9 + r"\8a2a52ce\j9main_a1\j9_main_t4h\R12_top-FL-Fs0-o0.0_VBM.npz",
    "VBMslow S7_e0.0": J9 + r"\8a2a52ce\sens_a1\sens_t4h\S7_e0.0_VBMslow.npz",
    "VBM S7_e0.002": J9 + r"\8a2a52ce\j9main_a1\j9_main_t4h\S7_e0.002_VBM.npz",
    "VBM S7_e0.001": J9 + r"\8a2a52ce\j9main_a1\j9_main_t4h\S7_e0.001_VBM.npz",
    "VBL S7_e0.002": J9 + r"\79495405\records_after_stop\B_a1\j9_main_t4h\S7_e0.002_VBL.npz",
    "VBJ S7_e0.002": J9 + r"\606f8713\j9main_a1\j9_main_t4h\S7_e0.002_VBJ.npz",
}
res = {}
for k, p in TL.items():
    if os.path.exists(p):
        res[k] = timeline(p)
        print("==", k, json.dumps(res[k]))
    else:
        print("missing", k, p)
json.dump(res, open(os.path.join(OUT, "a04_failed_lines.json"), "w", encoding="utf-8"), indent=1)
