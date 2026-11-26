"""e01: early-handover exposure and the first decision of the handover-fix candidates.

Inputs (read only, dynamics U832 analysis ``../dynamics_u832_o00/``):
* ``u01_scan_ed6.csv`` / ``u01_scan_ed7.csv``: stored lines of editions 6 and 7 (grid192 VBL,
  confirm_a, G1, probe_d, j9_main, sens) with ``reapproach_starts`` = [[t_rel_s, leg], ...]
  (t_rel from the event for event rows).
* ``u11_periods.csv``: re-run lines (V0 / VBM / U8-A = direction A), per control period the lower
  load estimate L of each leg (``load_<leg>_kN``), start level (1.4 F_min) and the active
  re-approach (``<leg>:<exit samples>[:rt]``).

Diagonal handover = a re-approach start of DIAG[p] right after a run of leg p (single_leg: the
next start). Early = that start <= 0.45 s after the event (dynamics 4.6 (b) layer criterion).

First decision (exact, the commands are the recorded ones up to the handover period):
* H-C: at the handover period the diagonal's L < 0 -> wait (one period);
* H-B: the diagonal may start only after one sample with L >= the start level (1.4 F_min,
  its rocking lift ended) since the end of p's run -> deferred at the handover period when the
  diagonal has had no such sample since that end (here: the handover period itself is low).
Later decisions depend on the changed trajectory and are not replayed.

Usage: conda run -n dynamics-dev python -I -B e01_handover_exposure.py
Output: e01_out.txt, e01_exposure.csv, e01_rerun_handover.csv (this folder).
"""
import csv
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "dynamics_u832_o00"
DIAG = {"FL": "RR", "RR": "FL", "FR": "RL", "RL": "FR"}
EARLY_S = 0.45


def handovers(starts):
    out = []
    for (t0, p), (t1, d) in zip(starts, starts[1:]):
        if DIAG.get(p) == d:
            out.append((float(t0), p, float(t1), d))
    return out


def main() -> int:
    lines = []
    rows = []
    tally = Counter()
    for name in ("u01_scan_ed6.csv", "u01_scan_ed7.csv"):
        for r in csv.DictReader((SRC / name).open(encoding="utf-8")):
            starts = (json.loads(r["reapproach_starts"]) if r["reapproach_starts"] else None) or []
            hos = handovers(starts)
            is_event = r["t_event_s"] not in ("", "None")
            early = [h for h in hos if is_event and h[2] <= EARLY_S]
            key = (name[-7:-4], r["src"], r["setting"])
            tally[key + ("lines",)] += 1
            tally[key + ("with_diag_handover",)] += bool(hos)
            tally[key + ("with_early_handover",)] += bool(early)
            tally[key + ("u832_fail",)] += "U832_pair_union" in (r["failed_gates"] or "")
            tally[key + ("u832_fail_and_early",)] += ("U832_pair_union" in (r["failed_gates"] or "")
                                                      and bool(early))
            rows.append({"scan": name, "src": r["src"], "setting": r["setting"], "case": r["case"],
                         "level": r["level"], "leg": r["leg"], "fs_kN": r["fs_kN"],
                         "event": r["event"], "timing": r["timing"], "offset_s": r["offset_s"],
                         "eps": r["eps"], "pass": r["pass"], "failed_gates": r["failed_gates"],
                         "n_starts": len(starts), "diag_handovers": json.dumps(hos),
                         "early": bool(early)})
    with (HERE / "e01_exposure.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    groups = sorted({k[:3] for k in tally})
    lines.append("scan | src | setting | lines | with_diag_handover | with_early_handover | u832_fail | u832_fail_and_early")
    for g in groups:
        lines.append(" | ".join(map(str, g)) + " | " + " | ".join(
            str(tally[g + (m,)]) for m in ("lines", "with_diag_handover", "with_early_handover",
                                           "u832_fail", "u832_fail_and_early")))
    # re-run lines: the first handover decision of H-B / H-C
    per = {}
    for r in csv.DictReader((SRC / "u11_periods.csv").open(encoding="utf-8")):
        per.setdefault(r["run"], []).append(r)
    rr = []
    for run, ps in per.items():
        prev = None
        for i, p in enumerate(ps):
            act = p["active"]
            leg = act.split(":")[0] if act else None
            if prev and leg and leg != prev and DIAG[prev] == leg:
                start_level = float(p["start_level_kN"])
                L_now = float(p[f"load_{leg}_kN"])
                nxt = [float(q[f"load_{leg}_kN"]) for q in ps[i + 1:i + 6]]
                rr.append({"run": run, "t_handover_s": float(p["t_rel_s"]), "from": prev, "to": leg,
                           "L_diag_at_handover_kN": L_now,
                           "HC_waits": L_now < 0.0,
                           "HB_defers": L_now < start_level,
                           "L_diag_next5_kN_recorded": nxt})
                break
            prev = leg if leg else prev
    with (HERE / "e01_rerun_handover.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rr[0].keys()))
        w.writeheader()
        w.writerows(rr)
    lines.append("")
    lines.append("re-run first diagonal handover: run, t, from->to, L_diag, H-C waits, H-B defers, next recorded L (old trajectory)")
    for r in rr:
        lines.append(f"{r['run']} t={r['t_handover_s']} {r['from']}->{r['to']} L={r['L_diag_at_handover_kN']} "
                     f"HC={r['HC_waits']} HB={r['HB_defers']} next={r['L_diag_next5_kN_recorded']}")
    (HERE / "e01_out.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
