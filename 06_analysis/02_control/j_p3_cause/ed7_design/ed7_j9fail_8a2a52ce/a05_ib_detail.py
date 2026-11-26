"""a05: A_ib record detail (triggers, protect, latch, completion, shots, LEVEL done paths) and
the post-event LEVEL twist / command trace for the end_att lines and the S7 relevel lines.

Reads jsonl lines (lsb_record.blind) and T4h (lsb_ib_twist_load_N, command_m_s, locked,
lsb_ib_stretch_periods, lsb_protected). Output a05_ib_detail.json + printed summary."""
import json
import os

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
J9 = r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
U_HOLD = 0.01 * 0.020924
CASES = [
    ("ed7_j9main", "LSM4", "R12_top-FR-Fs0-o0.05"),
    ("ed7_j9main", "VBM", "R12_top-FR-Fs0-o0.05"),
    ("ed7_sens", "VBMslow", "R12_top-FL-Fs0-o0.0"),
    ("ed7_sens", "VBMslow", "R12_top-FL-Fs0-o0.05"),
    ("ed7_j9main", "VBM", "S7_e0.002"),
    ("ed7_j9main", "VBM", "S7_e0.001"),
    ("ed7_sens", "VBMslow", "S7_e0.0"),
    ("ed7_sens", "VBMslow", "S7_e0.002"),
]
SRC = {"ed7_j9main": (J9 + r"\8a2a52ce\j9main_a1\j9_main.jsonl",
                      J9 + r"\8a2a52ce\j9main_a1\j9_main_t4h"),
       "ed7_sens": (J9 + r"\8a2a52ce\sens_a1\sens.jsonl", J9 + r"\8a2a52ce\sens_a1\sens_t4h")}

lines = {}
for src, (jl, _) in SRC.items():
    want = {f"{k}_{s}.npz" for (so, s, k) in CASES if so == src}
    with open(jl, encoding="utf-8") as f:
        for ln in f:
            d = json.loads(ln)
            if d.get("t4h_file") in want:
                lines[(src, d["t4h_file"])] = d

LEGS = ("FL", "FR", "RL", "RR")
res = {}
for src, setting, key in CASES:
    name = f"{key}_{setting}.npz"
    d = lines.get((src, name))
    z = np.load(os.path.join(SRC[src][1], name), allow_pickle=False)
    t = z["t_s"]
    ph = z["phase"].astype(str)
    cmd = z["command_m_s"]
    inp = z["lsb_input_m_s"]
    out = z["lsb_output_m_s"]
    locked = z["locked"]
    tw = z["lsb_ib_twist_load_N"]
    st = z["lsb_ib_stretch_periods"]
    prot = z["lsb_protected"]
    ib_on = z["lsb_ib_on"]
    blind = d["lsb_record"]["blind"]
    # LEVEL segments
    segs = []
    s = None
    for i in range(len(t)):
        if ph[i] == "level" and s is None:
            s = i
        if s is not None and (ph[i] != "level" or i == len(t) - 1):
            e = i if ph[i] == "level" else i - 1
            segs.append((s, e))
            s = None
    seg_info = []
    for (a, b) in segs:
        w = slice(a, b + 1)
        twk = tw[w] / 1e3
        info = {"t0": round(float(t[a]), 1), "t1": round(float(t[b]), 1),
                "dur_s": round(float(t[b] - t[a]), 1),
                "twist_kN_first_last_min_max": [round(float(twk[0]), 2), round(float(twk[-1]), 2),
                                                round(float(np.nanmin(twk)), 2),
                                                round(float(np.nanmax(twk)), 2)],
                "max_stretch_periods": [int(st[w, i].max()) for i in range(4)],
                "ib_on_periods": [int(ib_on[w, i].sum()) for i in range(4)],
                "protected_periods": [int(prot[w, i].sum()) for i in range(4)],
                "blind_periods_input": [int(((np.abs(inp[w, i]) > 0) & (np.abs(inp[w, i]) <= U_HOLD + 1e-12)).sum()) for i in range(4)],
                "blind_periods_output": [int(((np.abs(out[w, i]) > 0) & (np.abs(out[w, i]) <= U_HOLD + 1e-12)).sum()) for i in range(4)],
                "locked_frac": [round(float(locked[w, i].mean()), 2) for i in range(4)]}
        # twist trace every 2 s in the long LEVEL
        if info["dur_s"] > 15:
            idx = list(range(a, b + 1, 20))
            info["twist_trace_kN"] = [[round(float(t[k]), 1), round(float(tw[k]) / 1e3, 2)] for k in idx]
            info["cmd_trace_mm_s"] = [[round(float(t[k]), 1)] + [round(float(cmd[k, i]) * 1e3, 3) for i in range(4)] for k in idx]
            info["input_trace_mm_s"] = [[round(float(t[k]), 1)] + [round(float(inp[k, i]) * 1e3, 3) for i in range(4)] for k in idx]
        seg_info.append(info)
    r = {"legs": blind["legs"], "shots": blind.get("shots"), "level_done": blind.get("level_done"),
         "twist_over_limit": blind.get("twist_over_limit"), "level_segments": seg_info,
         "events": d.get("events"), "event_names": d.get("event_names"),
         "t_event_s": d.get("t_event_s"), "final_phase": d.get("final_phase")}
    res[f"{setting} {key}"] = r
    print("=====", setting, key, "final", d.get("final_phase"), "t_event", d.get("t_event_s"))
    print(" legs", json.dumps({k: {kk: v[kk] for kk in ("triggers", "latches", "n_rev", "protect_blocked_periods", "triggers_completion_unknown", "end")} for k, v in blind["legs"].items()}))
    print(" shots", json.dumps(blind.get("shots"))[:1500])
    print(" level_done", json.dumps(blind.get("level_done")))
    print(" over", json.dumps(blind.get("twist_over_limit"))[:400])
    for si in seg_info:
        print(" seg", json.dumps({k: v for k, v in si.items() if not k.endswith("trace_kN") and not k.endswith("mm_s")}))
        if "twist_trace_kN" in si:
            print("  twist", si["twist_trace_kN"])
            print("  input", si["input_trace_mm_s"])
json.dump(res, open(os.path.join(OUT, "a05_ib_detail.json"), "w", encoding="utf-8"), indent=1)
