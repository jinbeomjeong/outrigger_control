"""C-4 (J-14): LAS Chrono check V5-LAS-CHRONO (mixed rigid + J1@FR, record_only), 4 rows.
Rules 5.2 C-4 "기록, D8·G6", 7.4 (rows with R_c > 1: F_min shortfall = L-5, not graded).
Record bundle: D8 items, G6 items (P3-1..P3-5, P3-8 + 377, G6-6), P3-3 within, R_c from the
recorded crawler attitude, F<F_min times in [t_D, t_D + 8 s] (rev2 R2-5), K1 class
(off arm = 'LAS 없음', rev1 RV1-10 b).
rev24 CD-9 (decision 88 over rev18 R18-6): per row a record status from the values present (P3-1..P3-9 /
FAULT0 incl. 해당 없음, t_D, per-leg minimum after departure with leg and time, R_c); rigid_base rows take
P3-5 = 해당 없음(rigid_base); CD-4 adds P3-7 (record), CD-5 handles a run without READY.
"""
import p2_cd as CD
import p2_core as C
import p2_kinds as K
import p2_rules as R

CRITERIA = ("C-4",)
EXPECTED_ROWS = 4


def kind_of(case):
    return "record_D8_G6"


def judge_row(row, case, kind, params):
    items, keys, notes = K.items_p3(row, params, R.READY_SLOPE_S, ready_judged=False, g6=True, allow_stop=False)
    d8, _, _ = K.items_d8p(row, params, judged=False, hold=False)
    for k in ("D8_F_after_liftoff", "D8_end_attitude", "D8_READY", "D8_pressure"):
        items[k] = d8[k]
    t_D = items["departure"]["t_D_s"]
    items["Fmin_time_8s"] = dict(C.min_force_after(row, t_D, None if t_D is None else t_D + R.FMIN_REC_WINDOW_S,
                                                   params["F_min_N"]) or {"reason": "t_D undefined"},
                                 clause="rev2 R2-5 [t_D, t_D + 8 s]", verdict="record" if t_D else "indeterminate")
    rc = C.rc_from_record(row)
    items["R_c"] = dict(rc or {"reason": "crawler_attitude_deg missing"}, clause="rules 2 / 7.4",
                        verdict="record" if rc else "indeterminate")
    if rc and R.gt(rc["R_c"], 1.0):
        items["P3-3"]["outside_start_condition"] = "R_c > 1: shortfall = L-5 known limit (7.4)"
    CD.set_p3_6(items, keys, row, judged=False)   # rev25 CD-4: 421.1 limit, recorded on C-4
    CD.g6_split(items, keys, row, graded=False)   # rev25 CD-11: G6-6 and READY_le_120s apart (records)
    CD.add_p3_7(items, keys, row, params, judged=False)
    CD.apply_ready_none(items, keys, row)
    items["CD-9_record"] = CD.c4_record(row, items)
    items["earlier_record_keys"] = {"verdict": "record", "keys": keys + ["D8_F_after_liftoff", "D8_end_attitude",
                                                                        "D8_pressure", "Fmin_time_8s", "R_c"]}
    return items, ["CD-9_record"], notes, True


def bundle_status(rows):
    return K.bundle_status(rows, EXPECTED_ROWS, record_bundle=True)
