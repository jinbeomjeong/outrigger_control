"""Expected I4 classes (spec s6_control_spec.md rev. 41 211.2, rebuilt in rev. 42 212.6) for the S8 item-9 cases.

I4 (203.5) compares three per-case classes of a Chrono S8 case with the reduced pre-check (200.2 / 212.2,
``s8_fs_precheck.json``, rev. 42 harness: 3-4-5 sink on 1 ms chunks, L1-R rod side from the start, rear seal
x 0.8333) or, where the reduced harness has no such case, with the mechanism of 199:

* ``p_miss``     -- offline J_P judge level (F_hat < F_min) over the U/L episodes after the event start:
                    "miss" (>= 1 episode never flagged) / "detect" / "none" (no episode).
* ``item6``      -- item 6 (1): min rod-axis force of all legs from the event start >= F_min: "pass" / "fail".
* ``reapproach`` -- ``leg_reapproach_start`` (P-R8-13) after the event start: "yes" / "no" / "if_lift".
* "n/a"          -- not compared (reason in ``basis``).

Rev. 42 rule for the harness-covered events (flat floor, all start phases of the event in the harness):
  item6  = "pass" if min over phases - U >= F_min, "fail" if max over phases + U < F_min, else "n/a";
  p_miss = "none" when item6 = "pass"; when item6 = "fail" the harness J_P class if all phases agree
           ("miss" / "detect"), else "n/a"; "n/a" when item6 = "n/a";
  reapproach: harness value if all phases agree and the event lifts a leg in the harness (lift >= 0.3 s) or never
           re-approaches; G4 keeps "if_lift" (re-approach without lift depends on the measured F_band, 212.6).
  U = 1.0 kN (ASSUMPTION): harness vs Chrono L1-R G4 F_s 0 <= 0.4 kN after the rev. 42 fix, plus the L1-R vs
  L2b slow-component pair difference (S7 rpB -0.94 kN, rev. 37).
HOLD, D8, RE1bP, RE1c keep the rev. 41 mechanism classes. The reduced values are copied to ``reduced_ref``.
Deterministic, no random numbers.

Run: conda run -n dynamics-dev python -I s8_i4_expected.py <precheck_json> <out_json>
"""
from __future__ import annotations

import json
import sys

F_MIN_KN = 9.41459
LIFT_MIN_S = 0.3
U_KN = 1.0

EVENT_MAP = {"G4": "E1_sink11.5_2s", "SS": "E2_sink11.5_20s", "RE1bF": "E3_drop30_0.05s",
             "SS9": "E4_sink9_20s", "HOLD": "E0_hold"}


def _p_miss(e) -> str:
    eps = e["JP_m0"]["episodes"]
    if not eps:
        return "none"
    return "miss" if any(x["missed"] for x in eps) else "detect"


def reduced_ref(runs, judge: str, fs: float, event: str):
    """Flat-floor reduced events (all phases) for (judge, F_s, event); None if not covered."""
    key = EVENT_MAP.get(event)
    if key is None:
        return None
    out = []
    for r in runs:
        if r["floor"] != "flat" or r["judge"] != judge or r["Fs_kN"] != fs:
            continue
        for e in r["events"]:
            if e["event"] != key:
                continue
            out.append({"offset_s": e["offset_s"], "min_true_kN": round(e["min_true_kN"], 2),
                        "t_below_Fmin_s": round(e["t_below_Fmin_s"], 2), "t_lift_s": round(e["t_lift_s"], 2),
                        "reapproach": bool(e["reapproach"]), "p_miss": _p_miss(e),
                        "F_band_kN": round(r["F_band_kN"], 2)})
    return out or None


def d8_ref(runs, judge: str, floor: str, fs: float):
    for r in runs:
        if r["floor"] == floor and r["judge"] == judge and r["Fs_kN"] == fs:
            return [{"D8_min_true_after_liftoff_kN": round(r["D8_min_true_after_liftoff_kN"], 2),
                     "F_band_kN": round(r["F_band_kN"], 2)}]
    return None


def harness_classes(event: str, judge: str, fs: float, ref) -> tuple[dict[str, str], str]:
    lo = min(x["min_true_kN"] for x in ref)
    hi = max(x["min_true_kN"] for x in ref)
    if lo - U_KN >= F_MIN_KN:
        item6 = "pass"
    elif hi + U_KN < F_MIN_KN:
        item6 = "fail"
    else:
        item6 = "n/a"
    pm = {x["p_miss"] for x in ref}
    if item6 == "pass":
        p_miss = "none"
    elif item6 == "fail" and len(pm) == 1 and pm != {"none"}:
        p_miss = pm.pop()
    else:
        p_miss = "n/a"
    reap = {x["reapproach"] for x in ref}
    lifts = all(x["t_lift_s"] >= LIFT_MIN_S for x in ref)
    if event == "G4":
        reap_c = "no" if (judge == "pressure" and fs >= 8.0 and reap == {False}) else "if_lift"
    elif len(reap) == 1 and (lifts or reap == {False}):
        reap_c = "yes" if reap.pop() else "no"
    else:
        reap_c = "if_lift"
    basis = (f"reduced rev. 42 (flat, {len(ref)} phases): min true {lo:.2f}..{hi:.2f} kN "
             f"(F_min {F_MIN_KN:.2f}, U {U_KN:g} kN -> item6 {item6}); J_P {sorted({x['p_miss'] for x in ref})}; "
             f"re-approach {sorted({x['reapproach'] for x in ref})}, lift max "
             f"{max(x['t_lift_s'] for x in ref):.1f} s.")
    if item6 == "n/a":
        basis += " Within U of F_min: not compared (C8 / item 6 gate decides)."
    if event == "G4" and reap_c == "if_lift":
        basis += (" G4 re-approach compared only with a lift >= 0.3 s: in the harness it may start without a lift "
                  "(lower bound P - F_band < F_min/2), which depends on the measured F_band.")
    return {"p_miss": p_miss, "item6": item6, "reapproach": reap_c}, basis


def mechanism_classes(event: str, judge: str, fs: float) -> tuple[dict[str, str], str]:
    if event == "RE1bP":
        return ({"p_miss": "detect", "item6": "fail", "reapproach": "yes"},
                "not in the reduced harness; mechanism as RE1bF (drop lifts RR; lifted reading "
                "F_s - m g <= 5.95 kN < F_min, so J_P flags; combined lower bound < F_min/2).")
    if event == "RE1c":
        return ({"p_miss": "detect", "item6": "n/a", "reapproach": "n/a"},
                "not in the reduced harness; forced retract (runner overrides RR): reading "
                "-F_s - m g (retract-direction friction, 203.4), item 6 and reapproach are not "
                "controller outcomes.")
    if event == "HOLD":
        return ({"p_miss": "none", "item6": "pass", "reapproach": "no"},
                "reduced E0 (40 s hold, all floors, F_s 0..8): no READY exit, no flag; 120 s "
                "extension is an ASSUMPTION.")
    if event == "D8":
        return ({"p_miss": "none", "item6": "n/a", "reapproach": "no"},
                "reduced 200.1 / 212.2 (D8 min >= 42 kN, F_s <= 8): no U/L episode after lift-off + 8 s; "
                "item 6 not applicable (C1 is the gate). fdown3.5 is not in the reduced set "
                "(mechanism only).")
    raise ValueError(event)


def build(precheck: dict) -> dict:
    runs = precheck["runs"]
    spec: list[tuple[str, str, str, float, float | None]] = []
    for fs in (0.0, 2.0, 4.0, 8.0):
        for off in (0.0, 0.05):
            cid = f"E_G4_Fs{fs:g}" + ("" if off == 0.0 else f"_ph{off:g}")
            spec.append((cid, "G4", "combined", fs, off))
    for fs in (0.0, 4.0, 8.0):
        spec.append((f"E_SS_Fs{fs:g}", "SS", "combined", fs, None))
    for ev in ("RE1bF", "RE1bP"):
        for fs in (0.0, 8.0):
            spec.append((f"E_{ev}_Fs{fs:g}", ev, "combined", fs, None))
    spec.append(("E_HOLD120_Fs8", "HOLD", "combined", 8.0, None))
    for fs in (0.0, 4.0, 8.0):
        spec.append((f"N_SS_Fs{fs:g}_pressure", "SS", "pressure", fs, None))
    spec.append(("N_SS9_Fs8_pressure", "SS9", "pressure", 8.0, None))
    spec.append(("N_SS9_Fs8_combined", "SS9", "combined", 8.0, None))
    for fs in (0.0, 4.0, 8.0):
        spec.append((f"N_G4_Fs{fs:g}_pressure", "G4", "pressure", fs, 0.0))
    for fs in (0.0, 8.0):
        spec.append((f"N_RE1bF_Fs{fs:g}_pressure", "RE1bF", "pressure", fs, None))
    for fs in (0.0, 8.0):
        spec.append((f"N_RE1c_Fs{fs:g}_combined", "RE1c", "combined", fs, None))
    spec.append(("N_HOLD120_Fs8_pressure", "HOLD", "pressure", 8.0, None))
    for f in ("rpB", "fdown3.5"):
        spec.append((f"N_D8_top_{f}_Fs8_pressure", "D8", "pressure", 8.0, None))
        spec.append((f"K8_top_{f}_Fs8", "D8", "combined", 8.0, None))

    cases = {}
    for cid, ev, judge, fs, _off in spec:
        if ev == "D8":
            floor = "rpB" if "rpB" in cid else "fdown3.5"
            ref = d8_ref(runs, judge, floor, fs) if floor == "rpB" else None
            c, basis = mechanism_classes(ev, judge, fs)
        elif ev in ("HOLD",):
            ref = reduced_ref(runs, judge, fs, ev)
            c, basis = mechanism_classes(ev, judge, fs)
        elif ev in EVENT_MAP:
            ref = reduced_ref(runs, judge, fs, ev)
            c, basis = harness_classes(ev, judge, fs, ref)
        else:
            ref = None
            c, basis = mechanism_classes(ev, judge, fs)
        cases[cid] = {"event": ev, "judge": "pressure" if judge == "pressure" else "combined",
                      "fs_kN": fs, "expected": c, "basis": basis, "reduced_ref": ref}
    n_press = sum(1 for k in cases if k.startswith("N_") and k.endswith("_pressure"))
    n_comb = sum(1 for k in cases if k.startswith("N_") and not k.endswith("_pressure"))
    assert (n_press, n_comb) == (12, 3), (n_press, n_comb)
    return {
        "meta": {
            "spec": "00_docs/04_control/s6_control_spec.md rev. 41 211.2, rebuilt rev. 42 212.6 (I4 of 203.5)",
            "source": "06_analysis/02_control/s8/s8_fs_precheck.json (reduced rev. 42 harness, flat floor)",
            "harness": {k: precheck["meta"].get(k) for k in ("sink", "rod_side", "rear_scale")},
            "f_min_kN": F_MIN_KN,
            "lift_min_s": LIFT_MIN_S,
            "uncertainty_kN": U_KN,
            "classes": {
                "p_miss": "offline J_P judge level F_hat < F_min over U/L episodes (203.1) with "
                          "t_on >= event start and without crawler_transient: miss / detect / "
                          "none",
                "item6": "min over legs of the 1 ms rod-axis force (C-S8-2) on [event start, "
                         "end] >= F_min: pass / fail",
                "reapproach": "any leg_reapproach_start with t >= event start: yes / no; "
                              "if_lift = expected yes when an L episode >= lift_min_s exists "
                              "after the event start, else not compared",
                "n/a": "not compared (see basis)"},
            "event_start": {"G4/SS/SS9/RE1bF/RE1c": "EVENTS[ev]['at'] (ready + 5 s)",
                            "RE1bP": "probe start + 0.1 s",
                            "HOLD": "READY entry", "D8": "crawler lift-off + 8 s"},
            "n_cases": len(cases), "n_group_N": {"pressure": n_press, "combined": n_comb}},
        "cases": cases}


def main() -> None:
    pre = json.load(open(sys.argv[1], encoding="utf-8"))
    doc = build(pre)
    with open(sys.argv[2], "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
    bad = 0
    for cid, c in doc["cases"].items():
        e = c["expected"]
        chk = []
        for r in c["reduced_ref"] or []:
            if "p_miss" not in r:
                continue
            got = {"p_miss": r["p_miss"],
                   "item6": "pass" if r["min_true_kN"] >= F_MIN_KN else "fail",
                   "reapproach": "yes" if r["reapproach"] else "no"}
            for k, v in got.items():
                want = e[k]
                if want == "if_lift":
                    want = "yes" if r["t_lift_s"] >= LIFT_MIN_S else None
                if want not in (None, "n/a") and want != v:
                    chk.append(f"{k}@{r['offset_s']:g}: reduced {v} != {want}")
        bad += len(chk)
        rng = ""
        if c["reduced_ref"] and "min_true_kN" in c["reduced_ref"][0]:
            v = [x["min_true_kN"] for x in c["reduced_ref"]]
            rng = f"[{min(v):.2f}, {max(v):.2f}]"
        print(f"{cid:28s} {e['p_miss']:7s} {e['item6']:5s} {e['reapproach']:8s} {rng:16s} "
              f"{'; '.join(chk) if chk else 'reduced consistent' if c['reduced_ref'] else '-'}")
    print("reduced mismatches", bad)
    print("cases", doc["meta"]["n_cases"], doc["meta"]["n_group_N"])


if __name__ == "__main__":
    main()
