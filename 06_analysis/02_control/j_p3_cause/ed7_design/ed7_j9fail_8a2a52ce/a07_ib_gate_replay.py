"""a07: which A_ib trigger condition blocked the shot in the long post-event LEVEL tails.

Offline replay of spec v7 3.1 conditions 1 and 2 from T4h (``lsb_ib_stretch_periods`` =
condition 1 counter as logged by the controller, ``motor_stroke_m`` = harness oil coordinate
``stroke_m``; E3 still test dS = mean(s[k-2..k]) - mean(s[ks+2..ks+4]) times the stretch sign,
ks = k - stretch + 1, s_still 0.1 mm). Periods where 1 and 2 hold but no shot started are
then blocked by condition 3 (completion (da)) or by the protect guard (logged separately,
``lsb_protected``) or the latch (record). Output a07_ib_gate_replay.json."""
import json
import os

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
J9 = r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
FILES = {
    "LSM4 R12_top-FR-Fs0-o0.05": J9 + r"\8a2a52ce\j9main_a1\j9_main_t4h\R12_top-FR-Fs0-o0.05_LSM4.npz",
    "VBMslow R12_top-FL-Fs0-o0.0": J9 + r"\8a2a52ce\sens_a1\sens_t4h\R12_top-FL-Fs0-o0.0_VBMslow.npz",
    "VBM R12_top-FR-Fs0-o0.05": J9 + r"\8a2a52ce\j9main_a1\j9_main_t4h\R12_top-FR-Fs0-o0.05_VBM.npz",
    "VBM S7_e0.002": J9 + r"\8a2a52ce\j9main_a1\j9_main_t4h\S7_e0.002_VBM.npz",
    "VBMslow S7_e0.0": J9 + r"\8a2a52ce\sens_a1\sens_t4h\S7_e0.0_VBMslow.npz",
}
N_BLIND, S_STILL = 25, 1e-4
res = {}
for name, path in FILES.items():
    z = np.load(path, allow_pickle=False)
    t = z["t_s"]
    ph = z["phase"].astype(str)
    s = z["motor_stroke_m"]
    st = z["lsb_ib_stretch_periods"]
    inp = z["lsb_input_m_s"]
    ib = z["lsb_ib_on"]
    prot = z["lsb_protected"]
    tw = z["lsb_ib_twist_load_N"]
    out = {}
    for leg in range(4):
        cand, still, shot_start = 0, 0, 0
        still_t = []
        for k in range(len(t)):
            if ph[k] != "level" or st[k, leg] < N_BLIND:
                continue
            cand += 1
            ks = k - int(st[k, leg]) + 1
            if ks + 4 > k - 2 or ks + 4 >= len(t):
                continue
            sign = np.sign(inp[k, leg]) or 1.0
            ds = (np.mean(s[k - 2:k + 1, leg]) - np.mean(s[ks + 2:ks + 5, leg])) * sign
            if ds < S_STILL:
                still += 1
                still_t.append(round(float(t[k]), 1))
            if ib[k, leg] and not ib[k - 1, leg]:
                shot_start += 1
        out["FL FR RL RR".split()[leg]] = {
            "stretch_ge_25_periods": cand, "still_periods": still,
            "still_first_last_t": [still_t[0], still_t[-1]] if still_t else None,
            "shots_started": shot_start, "protected_periods": int(prot[:, leg].sum())}
    lv = ph == "level"
    out["twist_abs_kN_in_still_window"] = None
    res[name] = out
    print(name, json.dumps(out))
json.dump(res, open(os.path.join(OUT, "a07_ib_gate_replay.json"), "w", encoding="utf-8"), indent=1)
