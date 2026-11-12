"""C-3 (J-5): D-1 fixed soil rows S-03, S-04 (`D1S_G1_B_{middle,bottom}_Fs4_spJ1FL`).
Rules 5.2 C-3, d1 rules 11 "S-03·04 | P3 + G6": P3-1..P3-5, P3-8 with 377 demotion, G6-6
(FAULT 0 + READY <= 120 s). P3-6 (90 s) is a record (spec 284). stroke_limited_stop is allowed
as for H-S-A (d1 11; see README 확인 필요 Q-C3).
"""
import p2_kinds as K
import p2_rules as R

CRITERIA = ("C-3",)
EXPECTED_ROWS = 2


def kind_of(case):
    return "P3_G6"


def judge_row(row, case, kind, params):
    items, keys, notes = K.items_p3(row, params, R.READY_FLAT_S, ready_judged=False, g6=True, allow_stop=True)
    return items, keys, notes, False


def bundle_status(rows):
    return K.bundle_status(rows, EXPECTED_ROWS)
