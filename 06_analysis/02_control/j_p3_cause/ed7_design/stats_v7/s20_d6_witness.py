"""Ed. 7 Q7-S2: D6 opening witness s_w,D6 (spec v7 3.2) - false 'opened' (-> false D6 failure
count / false fallback), missed sensor faults, and candidate (i) 'retract until witness or cap'.
stats-design-expert, 2026-11-24, design only.

Model (one probe retract round of one leg):
  retract command profile per cycle (mm/s): base [0.02, 1.0, 2.0, 3.0, 3.571, 3.571, 3.571, 3.0,
  2.0, 1.25] scaled so that it delivers D_oil = 2.098 mm (ed6 hydraulics 1.2: -0.02..-3.57 mm/s,
  2.098 mm); output delay d = 1 (command of cycle k acts over [t_{k+1}, t_{k+2})); P1 gate: the
  leg stays at 0 until the delivered oil reaches `need`, afterwards it moves with the command
  (full flow; ed6 hydraulics 2.2: c005 moved 0.646 = 2.098 - 1.489 + ...). Stroke read noise
  N(0, 0.1 mm) i.i.d. per 10 Hz read (sensors/hydraulic.py:55,402). Harness coordinate = oil
  coordinate (no creep before opening); real-piston variant: pre-opening creep c * x/need
  (c 0.15 / 0.53 / 0.77 mm, spec v6 F6-7).
Witness estimators (retract direction positive), evaluated every read from the retract start read
  k0 to the end of the movement window (command cycles + 2 delay reads):
  E1max = max_j (r_k0 - r_j)               (spec v7 text: single-read difference, maximum)
  E3max = max_j (mean r[k0-2..k0] - mean r[j-2..j])   (3-read means at both ends)
Candidate (i): the retract continues after the witness test fails, at 2.0 mm/s (sens. 1.0, 3.57),
  until the witness holds or total oil reaches the cap 3.0 mm; variant (i-a) the witness may stop
  the retract before 2 mm, (i-b) at least the base 2 mm is delivered.
D6 consequences (two consecutive failing judged rounds -> fallback):
  pre-fix harness: rise 0 when not opened; post-fix (P1 fix (a)): rise ~21 bar when the delivered
  oil >= line term (0.43 nominal, 0.65 v15-like, ed6 h4) - else 0. Sensor fault: rise 0 always.
Outputs (argv[1]): s20_d6_witness.json / .txt. stdout: status only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import norm

SEED = 20261114
SIG = 0.1
T = 0.1
BASE = np.array([0.02, 1.0, 2.0, 3.0, 3.571, 3.571, 3.571, 3.0, 2.0, 1.25])
D_OIL = 2.098
CAP = 3.0
PROFILE = BASE * D_OIL / (BASE.sum() * T)


def run(rng, R, need, est, s_w, mode, creep=0.0, cont_speed=2.0, line=0.43):
    """mode: 'fixed' (2 mm, witness only classifies), 'i-a', 'i-b'. Returns arrays per replicate."""
    K = 60
    pre = 3
    reads = np.zeros((R, K + pre))
    pos = np.zeros(R)                 # true displacement (retract positive)
    oil = np.zeros(R)
    opened = np.zeros(R, bool)
    cmd_hist = np.zeros((R, K + 2))
    stopped = np.zeros(R, bool)
    wit = np.zeros(R, bool)
    wit_k = np.full(R, -1)
    open_k = np.full(R, -1)
    stop_k = np.full(R, -1)
    n_prof = PROFILE.size
    for j in range(pre):
        reads[:, j] = SIG * rng.standard_normal(R)
    base0 = reads[:, :pre].mean(1)
    r0 = reads[:, pre - 1]
    last_cmd_k = np.full(R, n_prof - 1)
    for k in range(K):
        # read at cycle k (index pre + k): position after interval k-1
        shown = pos + np.where(opened, 0.0, creep * np.minimum(oil / need, 1.0))
        reads[:, pre + k] = shown + SIG * rng.standard_normal(R)
        if est == "E1":
            w = (r0 - reads[:, pre + k]) * -1.0
        else:
            w = (reads[:, pre + k - 2:pre + k + 1].mean(1) - base0)
        # retract positive: displacement reads grow positive in this model
        in_window = (k <= n_prof + 2) if mode == "fixed" else ((stop_k < 0) | (k <= stop_k + 2))
        hit = (~wit) & (w >= s_w) & (k >= 1) & in_window
        wit_k[hit] = k
        wit |= hit
        # command for cycle k
        if mode == "fixed":
            c = np.full(R, PROFILE[k] if k < n_prof else 0.0)
        else:
            base_part = PROFILE[k] if k < n_prof else cont_speed
            c = np.full(R, base_part)
            if mode == "i-a":
                stop_now = wit
            else:
                stop_now = wit & (k >= n_prof)
            delivered = oil + cmd_hist[:, k] * T          # oil incl. the command already queued
            stop_now = stop_now | (delivered >= CAP)
            stop_k[stop_now & (stop_k < 0)] = k
            stopped |= stop_now
            c[stopped] = 0.0
            if mode != "fixed":
                c = np.minimum(c, np.maximum((CAP - delivered) / T, 0.0))
        cmd_hist[:, k + 1] = c
        # plant over interval k with the command of cycle k-1
        u = cmd_hist[:, k]
        add = u * T
        pre_open = ~opened
        fill_to = oil + add
        newly = pre_open & (fill_to >= need)
        move_part = np.where(newly, fill_to - need, np.where(opened, add, 0.0))
        oil = fill_to
        opened |= newly
        open_k[newly & (open_k < 0)] = k
        pos += move_part
    if est == "E1":
        pass
    return {"opened": opened, "wit": wit, "wit_k": wit_k, "open_k": open_k, "pos": pos, "oil": oil,
            "line_ok": oil >= line}


def summarise(r, need):
    op, wt = r["opened"], r["wit"]
    out = {"P_opened": float(op.mean()), "P_witness": float(wt.mean()),
           "P_witness_given_not_opened": float(wt[~op].mean()) if (~op).any() else None,
           "P_no_witness_given_opened": float((~wt[op]).mean()) if op.any() else None,
           "early_witness_before_open": float((wt & ((r["open_k"] < 0) | (r["wit_k"] <= r["open_k"]))).mean()),
           "disp_q50_95": [float(x) for x in np.percentile(r["pos"], [50, 95])],
           "oil_q50_95": [float(x) for x in np.percentile(r["oil"], [50, 95])]}
    return out


def main() -> int:
    out_dir = Path(sys.argv[1])
    rng = np.random.default_rng(SEED)
    R = 20000
    res = {"seed": SEED, "R": R, "profile_mm_s": PROFILE.round(4).tolist(), "fixed": {}, "cand": {},
           "consequence": {}}
    needs = (0.75, 1.49, 1.8, 1.95, 2.05, 2.15, 2.23, 2.6)
    for est in ("E1", "E3"):
        for s_w in (0.2, 0.3, 0.4, 0.5, 0.7, 1.0):
            for need in needs:
                r = run(rng, R, need, est, s_w, "fixed")
                res["fixed"][f"{est}|sw{s_w}|need{need}"] = summarise(r, need)
            for creep in (0.15, 0.53, 0.77):
                r = run(rng, R, 2.23, est, s_w, "fixed", creep=creep)
                res["fixed"][f"{est}|sw{s_w}|need2.23|creep{creep}"] = summarise(r, 2.23)
    for est in ("E1", "E3"):
        for s_w in (0.3, 0.4, 0.5):
            for mode in ("i-a", "i-b"):
                for need in (0.75, 1.49, 2.23, 2.6, 2.9):
                    for cs in (1.0, 2.0, 3.571):
                        r = run(rng, R // 4, need, est, s_w, mode, cont_speed=cs)
                        s = summarise(r, need)
                        s["P_stop_before_open"] = float((~r["opened"]).mean())
                        s["P_stop_before_open_fill_lt_line"] = float(((~r["opened"]) & (~r["line_ok"])).mean())
                        res["cand"][f"{est}|sw{s_w}|{mode}|need{need}|cs{cs}"] = s
    # consequences (two consecutive rounds, same leg, same state)
    for key, s in res["fixed"].items():
        if "creep" in key:
            continue
        pw_no = s["P_witness_given_not_opened"]
        res["consequence"][key] = {
            "pre_fix_false_fallback_2rounds": (pw_no ** 2) if pw_no is not None and s["P_opened"] < 0.5 else 0.0,
            "fault_detect_2rounds": s["P_witness"] ** 2}
    # self checks: noise-free analytic witness, large need never opens, E1 single-look tail
    chk = {}
    r = run(rng, 2000, 5.0, "E1", 0.3, "fixed")
    chk["never_opens_when_need_gt_oil"] = bool((~r["opened"]).all())
    one_look = 1 - norm.cdf(0.3 / (SIG * np.sqrt(2)))
    chk["E1_one_look_tail"] = float(one_look)
    chk["E1_false_witness_ge_one_look"] = res["fixed"]["E1|sw0.3|need2.6"]["P_witness_given_not_opened"] >= one_look
    r = run(rng, 2000, 1.0, "E3", 0.3, "fixed")
    chk["opened_disp_matches"] = abs(float(np.median(r["pos"])) - (D_OIL - 1.0)) < 0.01
    chk["ok"] = bool(chk["never_opens_when_need_gt_oil"] and chk["E1_false_witness_ge_one_look"]
                     and chk["opened_disp_matches"])
    res["self_checks"] = chk
    (out_dir / "s20_d6_witness.json").write_text(json.dumps(res, indent=1, default=lambda o: o.item()),
                                                 encoding="utf-8")
    L = [f"self_checks {json.dumps(chk, default=lambda o: o.item())}", "== fixed 2 mm =="]
    for k, v in res["fixed"].items():
        L.append(f"{k:<28} open {v['P_opened']:.3f} wit {v['P_witness']:.4f} "
                 f"wit|notopen {v['P_witness_given_not_opened']} miss|open {v['P_no_witness_given_opened']} "
                 f"disp {v['disp_q50_95']}")
    L.append("== candidate (i) ==")
    for k, v in res["cand"].items():
        L.append(f"{k:<34} open {v['P_opened']:.3f} stop<open {v['P_stop_before_open']:.4f} "
                 f"(fill<line {v['P_stop_before_open_fill_lt_line']:.4f}) disp {v['disp_q50_95']} "
                 f"oil {v['oil_q50_95']}")
    (out_dir / "s20_d6_witness.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("ok" if chk["ok"] else "self_check_failed")
    return 0 if chk["ok"] else 3


if __name__ == "__main__":
    sys.exit(main())
