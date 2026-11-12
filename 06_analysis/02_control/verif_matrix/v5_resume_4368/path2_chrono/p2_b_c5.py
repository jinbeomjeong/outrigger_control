"""C-5 (J-15): stage-3 Chrono rows (v5 rev12 2.1 with `_LAS_K1` tags), 35 rows executed.
Judged items (rev12 2.2): T4-0 / T4 / T5, J11, J-P3, D2 and lock-window items.
rev4 R4-A2: J-P3 / J11 / D2 recomputed from the run records (option b); T4-0 / T4 / T5 from the
path 2 run of `chrono_t45_replay` (option c, `p2_t45.py`, pass `--aux t45=<t45_path2.json>`),
graded by path 2 (rev6 4.6, rev7). rev6 4.6 bundle phrase: all L2b rows T4 / T5 over 0 and T4-0
passed -> `일치`(등급 `부분`).
"""
import json
from pathlib import Path

import p2_kinds as K

CRITERIA = ("C-5",)
EXPECTED_ROWS = 35
AUX = {}
_T45 = {}


def kind_of(case):
    return "stage3"


def _t45():
    if "doc" not in _T45:
        p = AUX.get("t45")
        _T45["doc"] = json.loads(Path(p).read_text(encoding="utf-8")) if p else None
    return _T45["doc"]


def judge_row(row, case, kind, params):
    items, keys, notes = K.items_c5(row, params, _t45())
    return items, keys, notes, False


def bundle_status(rows):
    b = K.bundle_status(rows, EXPECTED_ROWS)
    l2b = [r for r in rows if r["engine"] == "l2b"]
    over = sum(int(r["items"].get(k, {}).get("over_0p6kN") or 0) for r in l2b for k in ("T4", "T5"))
    t40 = all(r["items"].get("T4-0", {}).get("verdict") == "pass" for r in l2b) if l2b else False
    b["rev6_4_6_phrase"] = ("일치(등급 부분)" if (t40 and over == 0) else
                            ("불일치 (H-7)" if over > 0 else "판정 안 함 (T4-0 또는 입력)"))
    b["t45_report"] = AUX.get("t45")
    return b
