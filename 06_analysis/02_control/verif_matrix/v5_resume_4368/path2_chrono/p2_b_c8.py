"""C-8a / C-8b (O-C5) path 2 values (rules 9.1 C-8 row, 7.4, rev2 R2-5 / R2-6). Record rows.
m = four-leg min of the per-leg min of 1 ms true F_cyl for t >= t_D (R2-6 path 2), treatment
column of 7.4 (stop / margin record / record), F<F_min and F<F_min+2 kN times in [t_D, t_D + 8 s]
and [t_D, end] (R2-5), R_c from the recorded crawler attitude (rules 2 formula).
"""
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
    return items, keys, list(row.notes), True


def bundle_status(rows):
    return K.bundle_status(rows, None, record_bundle=True)
