"""C-2 (J-4): D-1 selected rows + PS-c. Rules 5.2 C-2, rev1 RV1-10 g, rev2 R2-8, d1 rules 11:
- C2-03, C2-07 (L2b): D8.P judged (as C-1).
- S-01, S-02 (SCM): P3, READY 120 s, stroke_limited_stop allowed.
- baseline-failure extra rows: same item set as their family (D1C2_* -> D8.P, D1S_* -> P3 S-type).
- D1-PSC rows: 426.3 E-1..E-7 + stroke <= 684.8 mm; path 2 recomputes E-5 (with stroke);
  E-1..E-6 (rev4 b) and E-7 (rev4 c) are not built in this version -> PS-c row 판정 불가.
"""
import p2_core as C
import p2_kinds as K
import p2_rules as R

CRITERIA = ("C-2",)
FIXED = ("C2-03", "C2-07", "S-01", "S-02")


def kind_of(case):
    d1 = str(case.get("d1_id") or "")
    name = str(case.get("case") or "")
    if d1 in ("C2-03", "C2-07") or (not d1 and name.startswith("D1C2_")):
        return "D8P_judged"
    if d1 in ("S-01", "S-02") or (not d1 and name.startswith("D1S_")):
        return "P3_S"
    if "PSC" in d1.upper() or name.startswith("D1PSC_"):
        return "PSC"
    if d1.startswith("C2-"):
        return "D8P_judged"
    if d1.startswith("S-"):
        return "P3_S"
    return "unknown"


def judge_row(row, case, kind, params):
    if kind == "D8P_judged":
        items, keys, notes = K.items_d8p(row, params, judged=True, hold=True)
        return items, keys, notes, False
    if kind == "P3_S":
        items, keys, notes = K.items_p3(row, params, R.READY_SLOPE_S, ready_judged=True, g6=False,
                                        allow_stop=True)
        return items, keys, notes, False
    if kind == "PSC":
        return _psc(row, params)
    return {"kind": {"verdict": "indeterminate", "reason": "unknown row kind"}}, ["kind"], [], False


def _psc(row, params):
    items = {}
    t_R = C.first_phase_time(row, "ready")
    last = row.phases[-1][1] if row.phases else None
    sel = row.t_att >= row.t_end - 1.0 - R.CMP_TOL
    import numpy as np
    m = np.abs(row.att[sel].mean(axis=0)) if sel.any() else None
    items["E-5"] = {"clause": "426.3 E-5: ends in READY, last 1 s mean |roll|,|pitch| <= 0.2, FAULT 0, stroke <= 684.8 mm",
                    "last_phase": last, "end_mean_abs_deg": None if m is None else m.tolist(),
                    "fault": C.fault_present(row)["any"], "stroke_max_m": float(row.s_motor.max())}
    ok = (last == "ready" and m is not None and R.le(float(m.max()), R.ATT_LIMIT_DEG)
          and not items["E-5"]["fault"] and R.le(items["E-5"]["stroke_max_m"], R.STROKE_END_M))
    items["E-5"]["verdict"] = "pass" if ok else "fail"
    # rev4 R4-A2: E-1..E-6 recompute from soil_event_series.npz (option b), E-7 by running the
    # study A judge function (option c). Not built in this tool version (PS-c rows are 0..2 and
    # appear only if H-2 selects them); a PS-c row is 판정 불가 until built.
    has = (row.folder / "soil_event_series.npz").exists()
    for k in ("E-1", "E-2", "E-3", "E-4", "E-6", "E-7"):
        items[k] = {"clause": "426.3 / rev4 R4-A2", "verdict": "indeterminate",
                    "soil_event_series_present": has,
                    "reason": "PS-c E path 2 not built yet (rev4 b / c); build before judging a PS-c row"}
    keys = ["E-1", "E-2", "E-3", "E-4", "E-5", "E-6", "E-7"]
    return items, keys, list(row.notes), False


def bundle_status(rows):
    ids = [r.get("d1_id") for r in rows]
    stops = []
    missing = [f for f in FIXED if ids.count(f) != 1]
    if missing:
        stops.append(f"S-15 (rev2 R2-8): fixed rows not exactly once: {missing}")
    psc = [r for r in rows if r["kind"] == "PSC"]
    extra = [r for r in rows if r.get("d1_id") not in FIXED and r["kind"] != "PSC"]
    if len(psc) > 2:
        stops.append(f"S-15 (RV1-10 g): PS-c rows {len(psc)} > 2")
    if len(extra) > 4:
        stops.append(f"S-15 (RV1-10 g): baseline extra rows {len(extra)} > 4")
    if not 4 <= len(rows) <= 10:
        stops.append(f"S-15: rows {len(rows)} not in 4..10")
    return K.bundle_status(rows, None, extra_stops=stops)
