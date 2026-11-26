"""l01: first period at which the LEVEL-deadlock fix candidates would act, on recorded traces.

Exact only up to the first period the candidate acts (the commands are the recorded ones until
then); nothing after it is replayed.

Inputs (read only):
* ``../control_early_handover/probe_8a2a52ce/diag/diag_case1_trace.csv``: G1 key
  R12 bottom-FR-Fs4-o0.075-RE1bF-ready, VBM plant, arms A and H3 (per control period: commands
  ``u_*``, plant lock ``locked_*``, readings ``F_*`` (kN), ``D_kN``, completion flags).
* ``../dynamics_d1_d3/d08_d3_tail_twist_trace.csv``: D-3 tails (LSM4 R12 top-FR-Fs0 o0.05,
  VBMslow R12 top-FL-Fs0 o0.0, arms a2 / A; no clearance flag -> taken as met, stated).

Candidates (spec v8 rev 2 3.8):
* L-1: A_ib condition 3 (da) also opens while on target and clearance done when
  ``|D|(t) - |D|(t - 5 s) > 0.6 kN`` (|D| <= 15 kN); the A_ib shot then needs a leg with a
  sub-hold stretch (same sign, 0 < |u| <= u_hold) of >= 25 periods that has not moved (proxy:
  plant ``locked`` for the stretch; the controller uses the stroke reads, condition 2).
* L-2: relaxed twist completion waives "not rising" when, over the whole 5 s window, a leg has
  been sub-hold and still (>= 50 periods), the rise is <= 2.5 kN, |D| + 0.5 kN <= 15 kN and every
  reading >= F_min (proxy for the lower estimates); settle 10 s of on target and clearance.
  DONE would follow ``done_hold_s`` 1 s later if the flags hold.

Usage: conda run -n dynamics-dev python -I -B l01_first_trigger.py
Output: l01_out.txt (this folder).
"""
import csv
import json
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIAG = HERE.parent / "control_early_handover" / "probe_8a2a52ce" / "diag" / "diag_case1_trace.csv"
D08 = HERE.parent / "dynamics_d1_d3" / "d08_d3_tail_twist_trace.csv"
LEGS = ("FL", "FR", "RL", "RR")
U_HOLD = 0.209243
F_MIN = 9.415
W_PER = 50      # 5 s window
RISE_L1 = 0.6
RISE_L2 = 2.5
N_BLIND = 25
SETTLE_PER = 100
LIMIT = 15.0


def num(v, default=float("nan")):
    if isinstance(v, str) and v.strip().lower() in ("true", "false"):
        return 1.0 if v.strip().lower() == "true" else 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def rows_of(path, key, tkey):
    runs = {}
    for r in csv.DictReader(path.open(encoding="utf-8")):
        runs.setdefault(r[key], []).append(r)
    for rs in runs.values():
        rs.sort(key=lambda r: num(r[tkey]))
    return runs


def analyse(name, rs, tkey, has_clear):
    out = {"run": name, "periods": len(rs)}
    stretch = {g: (0, 0) for g in LEGS}          # (sign, periods) of sub-hold commands
    still = {g: 0 for g in LEGS}                  # consecutive sub-hold & locked periods
    hist = deque()
    settle = 0
    l1 = l2 = None
    first_ib = None
    first_done = None
    for r in rs:
        t = num(r[tkey])
        if r.get("phase", "level").lower() not in ("level",):
            stretch = {g: (0, 0) for g in LEGS}
            still = {g: 0 for g in LEGS}
            hist.clear()
            settle = 0
            continue
        D = abs(num(r["D_kN"]))
        on = num(r["on_target"], 0.0) >= 0.5
        clear = (num(r["clearance_done"], 0.0) >= 0.5) if has_clear else True
        for g in LEGS:
            u = num(r.get(f"u_{g}_mm_s", r.get(f"{g}_u_mm_s")))
            locked = num(r.get(f"locked_{g}", r.get(f"{g}_locked")), 0.0) >= 0.5
            if 0.0 < abs(u) <= U_HOLD:
                s = 1 if u > 0 else -1
                sign, n = stretch[g]
                stretch[g] = (s, n + 1 if s == sign else 1)
                still[g] = still[g] + 1 if locked else 0
            else:
                stretch[g] = (0, 0)
                still[g] = 0
        hist.append((t, D))
        while len(hist) > W_PER + 1:
            hist.popleft()
        settle = settle + 1 if (on and clear) else 0
        rise = D - hist[0][1] if len(hist) == W_PER + 1 else float("nan")
        cand_legs = [g for g in LEGS if stretch[g][1] >= N_BLIND and still[g] >= N_BLIND]
        if l1 is None and on and clear and D <= LIMIT and rise == rise and rise > RISE_L1 and cand_legs:
            l1 = {"t": t, "D_kN": round(D, 2), "rise_kN": round(rise, 2), "legs": cand_legs}
        win_legs = [g for g in LEGS if still[g] >= W_PER]
        F_ok = all(num(r.get(f"F_{g}_kN"), 99.0) >= F_MIN for g in LEGS)
        if (l2 is None and settle >= SETTLE_PER and rise == rise and RISE_L1 < rise <= RISE_L2
                and win_legs and D + 0.5 <= LIMIT and F_ok):
            l2 = {"t": t, "t_done_if_held": round(t + 1.0, 2), "D_kN": round(D, 2),
                  "rise_kN": round(rise, 2), "legs": win_legs}
        ib = r.get("ib_on") or ""
        if first_ib is None and ib and "true" in ib.lower():
            first_ib = t
        if first_done is None and num(r.get("complete"), 0.0) >= 0.5:
            first_done = t
    out.update({"first_recorded_ib_on_t": first_ib, "first_complete_flag_t": first_done,
                "L1_first_open_and_shot_ready": l1, "L2_first_waiver": l2,
                "clearance_flag": "recorded" if has_clear else "absent (taken as met)"})
    return out


def main() -> int:
    res = []
    for name, rs in rows_of(DIAG, "arm", "t_rel_s").items():
        res.append(analyse(f"G1 bottom-FR-Fs4-o0.075 {name}", rs, "t_rel_s", True))
    for name, rs in rows_of(D08, "run", "t_after_event_s").items():
        res.append(analyse(name, rs, "t_after_event_s", False))
    text = "\n".join(json.dumps(r) for r in res)
    (HERE / "l01_out.txt").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
