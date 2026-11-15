"""C-3 (J-5): D-1 fixed soil rows S-03, S-04 (`D1S_G1_B_{middle,bottom}_Fs4_spJ1FL`).
Rules 5.2 C-3, d1 rules 11 "S-03·04 | P3 + G6": P3-1..P3-5, P3-8 with 377 demotion, G6-6
(FAULT 0 + READY <= 120 s). P3-6 (90 s) is a record (spec 284). Safe stop: spec 427.9 conditions 1-5
(rev6 R6-B8 / D-26, rev18 R18-2) -> allowed_stop replaces P3-5 / P3-6 / FAULT0 (G6-6 stays judged). stroke_limited_stop is allowed
as for H-S-A (d1 11; see README 확인 필요 Q-C3).
rev24 (common block scope sentence): CD-4 adds P3-7 (judged), CD-5 handles a run without READY.
rev25 CD-11 G6 table: grade items = P3-1..P3-5, G6-6 (no FAULT and READY reached), P3-8, READY_le_120s and P3-7;
P3-6 (421.1 limit), P3-9 and FAULT0 are records; a 427.9 safe-stop row is graded by 427.9-1..5 only.
"""
import p2_cd as CD
import p2_kinds as K
import p2_rules as R

CRITERIA = ("C-3",)
EXPECTED_ROWS = 2


def kind_of(case):
    return "P3_G6"


def judge_row(row, case, kind, params):
    items, keys, notes = K.items_p3(row, params, R.READY_FLAT_S, ready_judged=False, g6=True, allow_stop=True)
    CD.set_p3_6(items, keys, row, judged=False)   # rev25 CD-4: recorded on the C-3 G6 rows
    CD.g6_split(items, keys, row, graded=True)   # rev25 CD-11 G6 table
    CD.add_p3_7(items, keys, row, params, judged=True)
    CD.apply_ready_none(items, keys, row)
    CD.scm_grade_guard(items, keys)
    return items, keys, notes, False


def bundle_status(rows):
    b = K.bundle_status(rows, EXPECTED_ROWS)
    b["safe_stop_427_9"] = K.safe_stop_summary(rows)   # rev18 R18-2 (S-03, S-04)
    return b
