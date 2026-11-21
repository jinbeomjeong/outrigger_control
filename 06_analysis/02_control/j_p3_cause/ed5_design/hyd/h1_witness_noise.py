"""H-1: false and true witnesses of the R5-8 stroke rule on the saved VBH / VBJ T4h (read only).

Definitions (approximation of the monitor classes from the T4h columns):
* carry = maximal run of reads with |u| > u_hold whose previous read had |u| <= u_hold; the
  reference is the reading of the read before the carry (single read, as in the draft) or the
  mean of the last 5 reads before it (option).
* a witness test at carry read k: undirected |s_k - s_ref| >= T, or directed sign(u) (s_k - s_ref)
  >= T; 'persist2' = two consecutive carry reads both pass.
* false witness = the test passes on a read whose plant state is locked (T4h ``locked``) on that
  read and on every earlier read of the carry (the plant never released yet).
* locked stretches (draft rule includes LOCK/HOLD): maximal runs with the plant locked and
  |u| <= u_hold; reference = first read; false = any read passes.
Also the retention: for every dominated R5-7 stretch (``retract_tracker_stretch_log``), the
directed displacement of the carry that ended at its opening, against T.
"""
import json
import math
from pathlib import Path

import numpy as np

RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\78fd5d2d\dg3_a1")
OUT = Path(__file__).with_suffix(".json")
U_HOLD = 2.0924e-4
THRESHOLDS = (0.6e-3, 0.8e-3, 1.0e-3, 1.2e-3)
LEGS = ["FL", "FR", "RL", "RR"]


def runs(mask):
    """(start, stop) index pairs of True runs."""
    out = []
    i, n = 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def analyse(setting):
    lines = json.loads((RUN / f"dg3_{setting}.json").read_text(encoding="utf-8"))["results"]
    res = {"carry_tests": 0, "carry_locked_tests": 0, "carries": 0,
           "locked_stretches": 0, "locked_stretch_reads": 0}
    for T in THRESHOLDS:
        for mode in ("undirected", "directed", "directed_persist2", "directed_mean5"):
            res[f"false_carry_{mode}_{T*1e3:.1f}"] = 0
        res[f"false_lockstretch_undirected_{T*1e3:.1f}"] = 0
    retention = {f"{T*1e3:.1f}": 0 for T in THRESHOLDS}
    retention_n = 0
    disp_list = []
    for line in lines:
        with np.load(RUN / f"{setting}_t4h" / line["t4h_file"], allow_pickle=False) as z:
            t, s, u, locked = z["t_s"], z["motor_stroke_m"], z["command_m_s"], z["locked"]
        for leg in range(4):
            big = np.abs(u[:, leg]) > U_HOLD
            # carries
            for a, b in runs(big):
                if a == 0:
                    continue
                res["carries"] += 1
                sign = math.copysign(1.0, u[a, leg])
                ref1 = s[a - 1, leg]
                ref5 = s[max(a - 5, 0):a, leg].mean()
                still_locked = True
                prev_pass = {T: False for T in THRESHOLDS}
                for k in range(a, b):
                    still_locked = still_locked and bool(locked[k, leg])
                    res["carry_tests"] += 1
                    if not still_locked:
                        continue
                    res["carry_locked_tests"] += 1
                    d1 = s[k, leg] - ref1
                    d5 = s[k, leg] - ref5
                    for T in THRESHOLDS:
                        tag = f"{T*1e3:.1f}"
                        if abs(d1) >= T:
                            res[f"false_carry_undirected_{tag}"] += 1
                        p = sign * d1 >= T
                        if p:
                            res[f"false_carry_directed_{tag}"] += 1
                        if p and prev_pass[T]:
                            res[f"false_carry_directed_persist2_{tag}"] += 1
                        prev_pass[T] = p
                        if sign * d5 >= T:
                            res[f"false_carry_directed_mean5_{tag}"] += 1
            # locked command-free stretches (plant locked, |u| <= u_hold)
            calm = locked[:, leg] & ~big
            for a, b in runs(calm):
                if b - a < 2:
                    continue
                res["locked_stretches"] += 1
                res["locked_stretch_reads"] += b - a - 1
                d = np.abs(s[a + 1:b, leg] - s[a, leg])
                for T in THRESHOLDS:
                    if (d >= T).any():
                        res[f"false_lockstretch_undirected_{T*1e3:.1f}"] += 1
        # retention on dominated stretches
        log = line["hydraulics_record"]["extend_bound_check"].get("retract_tracker_stretch_log") or []
        for row in log:
            if (row.get("dominated_reads") or 0) <= 0:
                continue
            leg = LEGS.index(row["leg"])
            i_open = int(np.searchsorted(t, row["t_open_s"] - 1e-6))
            # the carry that ended just before the opening read
            k = i_open - 1
            while k >= 0 and abs(u[k, leg]) <= U_HOLD and t[i_open] - t[k] < 5.0:
                k -= 1
            if k < 0 or abs(u[k, leg]) <= U_HOLD:
                continue
            b = k + 1
            a = k
            while a - 1 >= 0 and abs(u[a - 1, leg]) > U_HOLD:
                a -= 1
            if a == 0:
                continue
            sign = math.copysign(1.0, u[a, leg])
            disp = float(np.max(sign * (s[a:b, leg] - s[a - 1, leg])))
            retention_n += 1
            disp_list.append(disp)
            for T in THRESHOLDS:
                if disp >= T:
                    retention[f"{T*1e3:.1f}"] += 1
    res["retention_n"] = retention_n
    res["retention_directed_max_disp_ge"] = retention
    if disp_list:
        res["retention_disp_mm_p10_p50_p90"] = [round(v * 1e3, 3) for v in np.percentile(disp_list, [10, 50, 90])]
    return res


def analytic():
    """Gaussian per-read probabilities (sigma 0.1 mm, single-read reference)."""
    from scipy.stats import norm
    sig = 1e-4
    out = {}
    for T in THRESHOLDS:
        z1 = T / (math.sqrt(2) * sig)
        zm = T / math.sqrt(sig**2 + sig**2 / 5)
        out[f"{T*1e3:.1f}"] = {"z_single": round(z1, 3), "p_directed_single": norm.sf(z1),
                               "z_mean5": round(zm, 3), "p_directed_mean5": norm.sf(zm)}
    return out


if __name__ == "__main__":
    result = {"VBH": analyse("VBH"), "VBJ": analyse("VBJ"), "analytic": analytic()}
    OUT.write_text(json.dumps(result, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=1))
