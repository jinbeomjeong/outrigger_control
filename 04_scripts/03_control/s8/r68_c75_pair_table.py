"""C-S8-75 bundle B pair table (spec rev. 68 358.6): P-S8-27 (4790e2b) vs P-S8-26 (cb292e8).

Same six L2b-NSC slope TOUCH cases, controller the only difference. Per case: judge rows newly
failed by 4790e2b among those the pair passed, TOUCH span / length, READY time, minimum true
cylinder force after the crawler lift-off (1 ms) and its difference, ``INFO_TOUCH_DIP_HELD``
events, and whether the 10 Hz issued command (``r8_series.npz`` ``issued_u``) is identical up to
the TOUCH end (and over the whole run). FLAG when the minimum force drops by more than 10 kN
(harness worst 8.6 kN). Times [s] on the case clock, forces [kN], commands [m/s].

Usage: python -I r68_c75_pair_table.py <batch new> <batch pair> <judge new> <judge pair> <out>
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

DROP_FLAG_KN = 10.0


def phases(m: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    for t, name in m.get("phases", []):
        out.setdefault(str(name), float(t))
    return out


def dip_events(case_dir: Path) -> list[str]:
    p = case_dir / "controller_events.json"
    if not p.exists():
        return []
    txt = p.read_text(encoding="utf-8")
    doc = json.loads(txt)
    items = doc if isinstance(doc, list) else doc.get("events", [])
    return [str(e) for e in items if "INFO_TOUCH_DIP_HELD" in json.dumps(e, default=str)]


def cmd(case_dir: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    z = np.load(case_dir / "r8_series.npz")
    return np.asarray(z["t"], float), np.asarray(z["issued_u"], float), \
        np.array([str(p) for p in z["phase"]])


def main() -> None:
    b_new, b_pair, j_new_p, j_pair_p, out_p = (Path(a) for a in sys.argv[1:6])
    jn = json.loads(j_new_p.read_text(encoding="utf-8"))
    jp = json.loads(j_pair_p.read_text(encoding="utf-8"))
    mn = {m["case"]: m for m in jn["metrics"]}
    mp = {m["case"]: m for m in jp["metrics"]}
    rows_n = {(r["case"], r["item"]): r for r in jn["rows"]}
    rows_p = {(r["case"], r["item"]): r for r in jp["rows"]}
    cases = sorted(mn)
    table = {}
    for c in cases:
        a, b = mn[c], mp[c]
        pa, pb = phases(a), phases(b)
        newly = sorted(k[1] for k, r in rows_p.items() if k[0] == c and r.get("passed") is True
                       and rows_n.get(k, {}).get("passed") is False)
        fail_new = sorted(k[1] for k, r in rows_n.items() if k[0] == c
                          and r.get("passed") is False)
        missing = sorted(k[1] for k in rows_p if k[0] == c and k not in rows_n)
        ta, ua, pha = cmd(b_new / c)
        tb, ub, phb = cmd(b_pair / c)
        n = min(len(ua), len(ub))
        diff = np.flatnonzero(np.any(ua[:n] != ub[:n], axis=1))
        first = None if diff.size == 0 else {"k": int(diff[0]), "t_s": float(ta[diff[0]]),
                                             "phase": str(pha[diff[0]])}
        # TOUCH end on the r8 series clock (engine clock; the judge phases are relative to the
        # start state, offset t0): first sample after the last 'touch' label of the pair run
        k_touch = np.flatnonzero(np.char.lower(phb) == "touch")
        k_end = int(k_touch[-1]) + 1 if k_touch.size else n
        t_touch_end_b = float(tb[k_end]) if k_end < len(tb) else None
        same_to_touch_end = bool(k_end <= min(len(ua), len(ub))
                                 and np.array_equal(ua[:k_end], ub[:k_end]))
        dips = dip_events(b_new / c)

        def touch(p: dict[str, float]) -> dict[str, float | None]:
            t0, t1 = p.get("touch"), p.get("level")
            return {"start_s": t0, "end_s": t1,
                    "length_s": None if t0 is None or t1 is None else t1 - t0}

        tn, tp = touch(pa), touch(pb)
        fmin_n, fmin_p = a.get("min_cyl_after_liftoff_kN"), b.get("min_cyl_after_liftoff_kN")
        d_f = None if fmin_n is None or fmin_p is None else fmin_n - fmin_p
        table[c] = {
            "judge_rows": {"new_failed": fail_new, "newly_failed_vs_pair": newly,
                           "rows_missing_in_new": missing,
                           "n_rows": sum(1 for k in rows_n if k[0] == c)},
            "final_phase": {"new": a.get("final_phase"), "pair": b.get("final_phase")},
            "touch": {"new": tn, "pair": tp,
                      "length_diff_s": None if tn["length_s"] is None or tp["length_s"] is None
                      else tn["length_s"] - tp["length_s"]},
            "ready_s": {"new": a.get("ready_s"), "pair": b.get("ready_s"),
                        "diff_s": None if a.get("ready_s") is None or b.get("ready_s") is None
                        else a["ready_s"] - b["ready_s"]},
            "min_cyl_after_liftoff_kN": {"new": fmin_n, "pair": fmin_p, "diff": d_f,
                                         "leg_new": a.get("min_cyl_leg"),
                                         "leg_pair": b.get("min_cyl_leg")},
            "min_cyl_slow_after_liftoff_kN": {"new": a.get("min_cyl_slow_after_liftoff_kN"),
                                              "pair": b.get("min_cyl_slow_after_liftoff_kN")},
            "att_err_last5_maxabs_deg": {"new": a.get("att_err_last5_maxabs_deg"),
                                         "pair": b.get("att_err_last5_maxabs_deg")},
            "info_touch_dip_held": dips,
            "dip_held": bool(dips),
            "command": {"sha_new": hashlib.sha256(ua.tobytes()).hexdigest()[:16],
                        "sha_pair": hashlib.sha256(ub.tobytes()).hexdigest()[:16],
                        "identical_whole_run": bool(len(ua) == len(ub) and diff.size == 0),
                        "identical_to_touch_end": same_to_touch_end,
                        "touch_end_pair_r8_clock_s": t_touch_end_b, "first_diff_r8_clock": first,
                        "r8_clock_minus_judge_clock_s": float(a["times_s"]["t0"])},
            "flag_min_force_drop_gt_10kN": bool(d_f is not None and d_f < -DROP_FLAG_KN),
        }
    summary = {
        "new_judge_failed": jn["meta"]["failed"], "pair_judge_failed": jp["meta"]["failed"],
        "rows_new": jn["meta"]["rows"], "rows_pair": jp["meta"]["rows"],
        "newly_failed_total": sum(len(v["judge_rows"]["newly_failed_vs_pair"])
                                  for v in table.values()),
        "flags": [c for c, v in table.items() if v["flag_min_force_drop_gt_10kN"]],
        "dip_held_cases": [c for c, v in table.items() if v["dip_held"]],
        "no_dip_but_command_differs_before_touch_end": [
            c for c, v in table.items()
            if not v["dip_held"] and not v["command"]["identical_to_touch_end"]],
        "touch_length_diff_s": {c: v["touch"]["length_diff_s"] for c, v in table.items()},
        "ready_diff_s": {c: v["ready_s"]["diff_s"] for c, v in table.items()},
        "min_force_diff_kN": {c: v["min_cyl_after_liftoff_kN"]["diff"] for c, v in table.items()},
    }
    doc = {"meta": {"spec": "s6_control_spec.md rev. 68 358.6 C-S8-75 bundle B",
                    "new": {"controller": "4790e2b (P-S8-27)", "batch": str(b_new),
                            "judge": str(j_new_p)},
                    "pair": {"controller": "cb292e8 (P-S8-26)", "batch": str(b_pair),
                             "judge": str(j_pair_p)},
                    "flag_rule": f"min true cylinder force after crawler lift-off drop > "
                                 f"{DROP_FLAG_KN:g} kN",
                    "touch_span": "judge phases: 'touch' start .. 'level' start (10 Hz record, "
                                  "clock relative to the start state); command / event times "
                                  "are on the r8 series (engine) clock = judge clock + t0",
                    "units": "s, kN, deg"},
           "summary": summary, "cases": table}
    Path(out_p).write_text(json.dumps(doc, indent=1, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main()
