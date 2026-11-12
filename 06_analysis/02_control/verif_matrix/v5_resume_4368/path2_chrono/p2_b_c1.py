"""C-1 (J-3): D-1 fixed rigid rows. Rules 5.2 C-1, 7.1 (d1 rules 11):
- C2-01, 02, 04, 05, 06, 08 (L2b NSC, VB): D8.P judged, tag "이륙 뒤 8 s 강체 크롤러 상한" -> R40-2 hold.
- C1-09..12 (L1-R V0 Kc x3): record (D8.P computed, failures reported), rule 8 transfer is H-2's job.
"""
import p2_kinds as K

CRITERIA = ("C-1",)
EXPECTED_ROWS = 10


def kind_of(case):
    d1 = str(case.get("d1_id") or "")
    if d1.startswith("C2-"):
        return "D8P_judged"
    if d1.startswith("C1-"):
        return "D8P_record"
    return "unknown"


def judge_row(row, case, kind, params):
    if kind == "D8P_judged":
        items, keys, notes = K.items_d8p(row, params, judged=True, hold=True)
        return items, keys, notes, False
    if kind == "D8P_record":
        items, keys, notes = K.items_d8p(row, params, judged=False, hold=False)
        return items, keys, notes, True
    return {"kind": {"verdict": "indeterminate", "reason": "unknown d1_id"}}, ["kind"], [], False


def bundle_status(rows):
    return K.bundle_status(rows, EXPECTED_ROWS)
