"""C-5 (J-15): stage-3 Chrono rows (v5 rev12 2.1 with `_LAS_K1` tags), 35 rows executed.
Judged items (rev12 2.2): T4 / T5 (rev6 4, rev7), J11, J-P3 (rev8, ③ on rows), D2 and lock-window
items. Path 2 recomputes t_lift / H-9 (rev6 5), records lock transitions (rev6 6) and K1 class;
T4-0 / T4 / T5 / J-P3 / D2 (and J11 window when an actual fallback leg exists) are re-aggregated
from result.json with the grade rules applied by path 2 (rev3 R3-G1, Q-C1 = A; TABLE_REAGG).
"""
import p2_kinds as K

CRITERIA = ("C-5",)
EXPECTED_ROWS = 35


def kind_of(case):
    return "stage3"


def judge_row(row, case, kind, params):
    items, keys, notes = K.items_c5(row, params)
    return items, keys, notes, False


def bundle_status(rows):
    return K.bundle_status(rows, EXPECTED_ROWS)
