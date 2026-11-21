"""H-1 retention detail (VBH): for every dominated R5-7 stretch, the directed displacement of
the carry that ended at its opening (reference = the read before the carry), the carry duration
and mean |u|, split into changed / unchanged rows and weighted by dominated reads."""
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control")
RUN = ROOT / r"06_analysis\02_control\j_p3_cause\j9_runs\78fd5d2d\dg3_a1"
BASE = ROOT / r"06_analysis\03_hydraulic\coupled\v5\resume_k1\h6_dg3_v4on.json"
OUT = Path(__file__).with_suffix(".json")
U_HOLD = 2.0924e-4
LEGS = ["FL", "FR", "RL", "RR"]


def plain(k):
    return k.split("#", 1)[1] if "#" in k else k


new = {plain(r["key"]): r for r in json.loads((RUN / "dg3_VBH.json").read_text(encoding="utf-8"))["results"]}
base = {plain(r["key"]): r for r in json.loads(BASE.read_text(encoding="utf-8"))["results"]}
changed = {k for k in new if new[k].get("commands_sha256") != base[k].get("commands_sha256")}
rows_out = []
for key, line in new.items():
    log = line["hydraulics_record"]["extend_bound_check"].get("retract_tracker_stretch_log") or []
    cols = line["hydraulics_record"]["extend_bound_check"].get("retract_tracker_stretch_log_columns")
    with np.load(RUN / "VBH_t4h" / line["t4h_file"], allow_pickle=False) as z:
        t, s, u, locked = z["t_s"], z["motor_stroke_m"], z["command_m_s"], z["locked"]
    for row in log:
        if (row.get("dominated_reads") or 0) <= 0:
            continue
        leg = LEGS.index(row["leg"])
        i_open = int(np.searchsorted(t, row["t_open_s"] - 1e-6))
        k = i_open - 1
        while k >= 0 and abs(u[k, leg]) <= U_HOLD and t[i_open] - t[k] < 5.0:
            k -= 1
        rec = {"changed": key in changed, "dominated": row["dominated_reads"],
               "max_over_kN": row.get("max_over_kN"), "disp_mm": None}
        if k >= 1 and abs(u[k, leg]) > U_HOLD:
            a = k
            while a - 1 >= 0 and abs(u[a - 1, leg]) > U_HOLD:
                a -= 1
            if a >= 1:
                sign = math.copysign(1.0, u[a, leg])
                rec["disp_mm"] = float(np.max(sign * (s[a:k + 1, leg] - s[a - 1, leg]))) * 1e3
                rec["sign"] = sign
                rec["dur_s"] = float(t[k] - t[a]) + 0.1
                rec["mean_abs_u_mm_s"] = float(np.mean(np.abs(u[a:k + 1, leg]))) * 1e3
                rec["plant_released_in_carry"] = bool((~locked[a:k + 2, leg]).any())
        # any motion in the 5 s window (noise-robust: mean of first 5 vs last 5 reads)
        w = np.flatnonzero((t > t[i_open] - 5.0) & (t <= t[i_open]))
        if w.size >= 10:
            rec["window_mean_shift_mm"] = float(abs(s[w[-5:], leg].mean() - s[w[:5], leg].mean())) * 1e3
        rows_out.append(rec)

summary = {}
for c in (True, False):
    sel = [r for r in rows_out if r["changed"] == c]
    dom = np.array([r["dominated"] for r in sel], float)
    disp = np.array([np.nan if r["disp_mm"] is None else r["disp_mm"] for r in sel])
    over = np.array([np.nan if r["max_over_kN"] is None else r["max_over_kN"] for r in sel])
    wsh = np.array([r.get("window_mean_shift_mm", np.nan) for r in sel])
    part = {"stretches": len(sel), "no_carry_found": int(np.isnan(disp).sum()),
            "dominated_reads": int(dom.sum())}
    for T in (0.6, 1.0, 1.5, 2.0):
        m = disp >= T
        part[f"witness_ge_{T}"] = {"stretches": int(m.sum()), "dominated_reads": int(dom[m].sum()),
                                   "max_over_kN_median": (float(np.nanmedian(over[m])) if m.any() else None)}
    nm = ~(disp >= 1.0)
    part["no_witness_1.0"] = {"stretches": int(nm.sum()), "dominated_reads": int(dom[nm].sum()),
                              "max_over_kN_median": float(np.nanmedian(over[nm])) if nm.any() else None,
                              "max_over_kN_max": float(np.nanmax(over[nm])) if nm.any() else None,
                              "window_mean_shift_mm_p50_p90": [round(float(v), 3) for v in np.nanpercentile(wsh[nm], [50, 90])] if nm.any() else None,
                              "released_in_carry": int(sum(1 for r, flag in zip(sel, nm) if flag and r.get("plant_released_in_carry"))),
                              "carry_dur_s_p50": float(np.nanmedian([r.get("dur_s", np.nan) for r, flag in zip(sel, nm) if flag])) if nm.any() else None,
                              "carry_mean_u_mm_s_p50": float(np.nanmedian([r.get("mean_abs_u_mm_s", np.nan) for r, flag in zip(sel, nm) if flag])) if nm.any() else None}
    signs = [r.get("sign") for r in sel]
    part["carry_sign_counts"] = {"+": signs.count(1.0), "-": signs.count(-1.0)}
    summary["changed" if c else "unchanged"] = part
OUT.write_text(json.dumps({"summary": summary, "rows": rows_out}, indent=1), encoding="utf-8", newline="\n")
print(json.dumps(summary, indent=1))
