"""C-2 (J-4): D-1 selected rows + PS-c. Rules 5.2 C-2, rev1 RV1-10 g, rev2 R2-8, d1 rules 11:
- C2-03, C2-07 (L2b): D8.P judged (as C-1).
- S-01, S-02 (SCM): P3, READY 120 s; a soil-guard stop row is graded by spec 427.9 conditions 1-5 only
  (rev6 R6-B8 / D-26, rev18 R18-2, rev19 R19-1: allowed_stop / fail; P3 / FAULT0 / READY items recorded).
- baseline-failure extra rows: same item set as their family (D1C2_* -> D8.P, D1S_* -> P3 S-type).
- D1-PSC event rows: 426.3 E-1..E-7 (+ stroke <= 684.8 mm in E-5, DSb75 record), rev18 R18-3 1, rev19 R19-3
  (`p2_psc`): E-1..E-6 recomputed from the raw record (rev4 R4-A2 b) on the adapter branch window, E-7 from the
  path 2 run of the designated tool (`p2_e7.py`, rev4 R4-A2 c, `--aux e7=<e7_path2.json>`). An item that cannot
  be computed makes the row 판정 불가.
- D1-PSC base row (no `--soil-event` in argv): record row (rev19 R19-2), P3 and D8 values recorded, no E items.
rev24 (common block scope sentence): L2b rows take CD-2; S-type SCM rows take CD-4 (P3-7 added, judged) and
CD-5 (no READY); the PS-c base row records P3-7; the PS-c event row keeps its 426.3 E items.
"""
import p2_cd as CD
import p2_kinds as K
import p2_psc as P
import p2_rules as R

CRITERIA = ("C-2",)
FIXED = ("C2-03", "C2-07", "S-01", "S-02")
AUX = {}
E7_LIMIT = ("rev4 R4-A2 한계 공개 문장(판정서 한계 절에 그대로): \"T4-0·T4·T5, PS-c E-7, 잡음 S-1~S-6과 L1 게이트의 "
            "항목 값은 원 규칙이 지정한 같은 판정 도구를 경로 2가 따로 실행해 얻었다. 그래서 두 경로는 같은 계산 "
            "함수에 기댄다. 경로 2의 독립성은 도구 실행과 등급 재집계에 있고, 항목 값 계산에는 없다.\"")
PSC_KINDS = ("PSC", "PSC_base")


def kind_of(case):
    d1 = str(case.get("d1_id") or "")
    name = str(case.get("case") or "")
    if d1 in ("C2-03", "C2-07") or (not d1 and name.startswith("D1C2_")):
        return "D8P_judged"
    if d1 in ("S-01", "S-02") or (not d1 and name.startswith("D1S_")):
        return "P3_S"
    if "PSC" in d1.upper() or name.startswith("D1PSC_"):
        # rev19 R19-2: the base row (same argv without --soil-event, time base of the event row) is a record row
        return "PSC" if "--soil-event" in (case.get("argv") or []) else "PSC_base"
    if d1.startswith("C2-"):
        return "D8P_judged"
    if d1.startswith("S-"):
        return "P3_S"
    return "unknown"


def judge_row(row, case, kind, params):
    if kind == "D8P_judged":
        items, keys, notes = K.items_d8p(row, params, judged=True, hold=True)
        CD.use_cd2(items, keys, row, params)
        return items, keys, notes, False
    if kind == "P3_S":
        items, keys, notes = K.items_p3(row, params, R.READY_SLOPE_S, ready_judged=True, g6=False,
                                        allow_stop=True)
        CD.add_p3_7(items, keys, row, params, judged=True)
        CD.apply_ready_none(items, keys, row)
        CD.scm_grade_guard(items, keys)
        return items, keys, notes, False
    if kind == "PSC":
        return _psc(row, params)
    if kind == "PSC_base":
        return _psc_base(row, params)
    return {"kind": {"verdict": "indeterminate", "reason": "unknown row kind"}}, ["kind"], [], False


def _psc(row, params):
    items, keys = P.e_items(row, params, P.load_e7(AUX.get("e7")))
    return items, keys, list(row.notes), False


def _psc_base(row, params):
    """rev19 R19-2: record row. No E items (no event: not missing); P3 and D8 values recorded, failures reported."""
    items, keys, notes = K.items_p3(row, params, R.READY_SLOPE_S, ready_judged=True, g6=False, allow_stop=True)
    CD.add_p3_7(items, keys, row, params, judged=False)
    CD.apply_ready_none(items, keys, row)
    d8, d8k, _ = K.items_d8p(row, params, judged=False, hold=False)
    for k in d8k:
        if k not in items:
            items[k] = d8[k]
            keys.append(k)
    items["E_items"] = {"verdict": "record", "clause": "rev19 R19-2",
                        "note": "PS-c base row: no soil event, E-1..E-7 not computed (not a missing input)"}
    return items, keys, notes, True


def bundle_status(rows):
    ids = [r.get("d1_id") for r in rows]
    stops = []
    missing = [f for f in FIXED if ids.count(f) != 1]
    if missing:
        stops.append(f"S-15 (rev2 R2-8): fixed rows not exactly once: {missing}")
    psc = [r for r in rows if r["kind"] in PSC_KINDS]
    extra = [r for r in rows if r.get("d1_id") not in FIXED and r["kind"] not in PSC_KINDS]
    if len(psc) > 2:
        stops.append(f"S-15 (RV1-10 g): PS-c rows {len(psc)} > 2")
    if len(extra) > 4:
        stops.append(f"S-15 (RV1-10 g): baseline extra rows {len(extra)} > 4")
    if not 4 <= len(rows) <= 10:
        stops.append(f"S-15: rows {len(rows)} not in 4..10")
    b = K.bundle_status(rows, None, extra_stops=stops)
    b["safe_stop_427_9"] = K.safe_stop_summary(rows)
    ev = [r for r in psc if r["kind"] == "PSC"]
    b["psc_E"] = {"clause": "426.3 E-1..E-7 (rev4 R4-A2 b / c, rev18 R18-3 1, rev19 R19-2 / R19-3)",
                  "rows": {r["case"]: {k: (r["items"].get(k) or {}).get("verdict") for k in P.E_KEYS} for r in ev},
                  "record_rows": [r["case"] for r in psc if r["kind"] == "PSC_base"],
                  "e7_tool_output": AUX.get("e7"), "limit_disclosure": E7_LIMIT if ev else None}
    return b
