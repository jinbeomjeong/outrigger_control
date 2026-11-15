"""C-8a / C-8b (O-C5) path 2 values (rules 9.1 C-8 row, 7.4, rev2 R2-5 / R2-6). Record rows.
m = four-leg min of the per-leg min of 1 ms true F_cyl for t >= t_D (R2-6 path 2), treatment
column of 7.4 (stop / margin record / record), F<F_min and F<F_min+2 kN times in [t_D, t_D + 8 s]
and [t_D, end] (R2-5), R_c from the recorded crawler attitude (rules 2 formula).
rev24 CD-8: the 원판 7.4 record values are all written (F^a / F^t per-leg minima after departure with their times,
F<F_min and F<F_min+2 kN times, P3-3_within, LAS-b start / end / reason, K1 decisions, R_c, crawler attitude,
floor angles, crawler stiffness factor k, P3-1..P3-9 / D8 / G6 values); a row is 기록 완료 when all are present.
C-8a S-9 is handled by user decisions 60 (A) / 88 (L-5 known limit, not a stop) only when m and the minimum leg
equal this path's R3d C-8 output (`--r3d-c8`), else 원판 7.4 stop.
rev25 CD-8: F^a = minimum from t_D to the record end, F^t = minimum in [t_D, t_D + 8 s) (same 1 ms true F_cyl);
P3-5 = 해당 없음(rigid_base); D8 = SCM D8 values (1)-(4); G6 = eight gate values (G6-6, READY_le_120s apart).
"""
import p2_cd as CD
import p2_core as C
import p2_kinds as K
import p2_rules as R

CRITERIA = ("C-8", "C-8a", "C-8b")


def kind_of(case):
    return "OC5"


def judge_row(row, case, kind, params):
    F_min = params["F_min_N"]
    t_D = C.t_departure(row)
    items = {"departure": {"t_D_s": t_D, "clause": "rev2 R2-5", "verdict": "record" if t_D else "indeterminate"}}
    full = C.min_force_after(row, t_D, None, F_min)
    w8 = C.min_force_after(row, t_D, None if t_D is None else t_D + R.FMIN_REC_WINDOW_S, F_min)
    rc = C.rc_from_record(row)
    items["R_c"] = dict(rc or {"reason": "missing"}, clause="rules 2", verdict="record" if rc else "indeterminate")
    m = None if full is None else full["min_all_N"]
    if m is None:
        treat = None
    elif R.lt(m, F_min):
        treat = "stop (S-9)"
    elif R.lt(m, F_min + R.FMIN_PLUS_N):
        treat = "margin record"
    else:
        treat = "record"
    items["m_7_4"] = {"clause": "rules 7.4 / rev2 R2-6 path 2", "m_N": m, "treatment": treat,
                      "per_leg": None if full is None else full,
                      "applies": rc is not None and R.le(rc["R_c"], 1.0),
                      "verdict": "record" if m is not None else "indeterminate"}
    if rc is not None and R.gt(rc["R_c"], 1.0):
        items["m_7_4"]["stop"] = "S-10 (R_c > 1)"
    elif treat == "stop (S-9)":
        items["m_7_4"]["stop"] = "S-9"
    items["Fmin_time_8s"] = dict(w8 or {"reason": "t_D undefined"}, clause="rev2 R2-5",
                                 verdict="record" if w8 else "indeterminate")
    items["Fmin_time_full"] = dict(full or {"reason": "t_D undefined"}, clause="rev2 R2-5 (record only)",
                                   verdict="record" if full else "indeterminate")
    keys = ["departure", "R_c", "m_7_4", "Fmin_time_8s"]
    _add_record_values(items, row, params)
    if CD.is_c8a(case, row) and items["m_7_4"].get("stop") == "S-9":
        _c8a_s9(items, rc, F_min, row)
    items["CD-8_record"] = CD.c8_values(row, items, params)
    items["CD-8_record"]["verdict"] = "record" if not items["CD-8_record"]["missing"] else "indeterminate"
    if items["CD-8_record"]["missing"]:
        items["CD-8_record"][CD.REASON_KEY] = "기록 값 없음: " + ", ".join(items["CD-8_record"]["missing"])
    keys.append("CD-8_record")
    return items, keys, list(row.notes), True


def _add_record_values(items, row, params):
    """CD-8: P3-1..P3-9 / FAULT0 (P3-6 with the 421.1 limit, P3-7 recorded), G6-6 and READY_le_120s apart, as
    records. The SCM D8 values (1)-(4) are written by `p2_cd.c8_values` (rev25 CD-8 8)."""
    p3, p3_keys, _ = K.items_p3(row, params, R.READY_FLAT_S, ready_judged=False, g6=True, allow_stop=False)
    for k, v in p3.items():
        items.setdefault(k, v)
    CD.set_p3_6(items, [], row, judged=False)
    CD.g6_split(items, [], row, graded=False)
    CD.add_p3_7(items, [], row, params, judged=False)
    CD.apply_ready_none(items, [], row)


def _c8a_s9(items, rc, F_min, row):
    """CD-8 (user decisions 60 (A) / 88): C-8a S-9 is an L-5 known limit with the S-9 facts recorded, when m and
    the minimum leg equal this path's R3d output; otherwise the 원판 7.4 stop stays."""
    m74 = items["m_7_4"]
    s9 = CD.c8a_s9_record(row, m74)
    s9["facts"] = {"m_N": m74.get("m_N"), "min_leg": (m74.get("per_leg") or {}).get("min_leg"),
                   "margin_vs_F_min_N": None if m74.get("m_N") is None else m74["m_N"] - F_min,
                   "R_c": None if rc is None else rc.get("R_c")}
    s9["verdict"] = "record"
    items["CD-8_S9"] = s9
    if "stop" in s9:
        m74["stop"] = s9.pop("stop")   # one stop per row (on m_7_4)
        s9["stop_on"] = "m_7_4"
    else:
        m74["stop_handled_cd8"] = m74.pop("stop")
        m74["known_limit"] = s9["known_limit"]


def bundle_status(rows):
    return K.bundle_status(rows, None, record_bundle=True)
