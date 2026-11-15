"""C-5 (J-15): stage-3 Chrono rows (v5 rev12 2.1 with `_LAS_K1` tags), 35 rows executed.
Judged items (rev12 2.2): T4-0 / T4 / T5, J11, J-P3, D2 and lock-window items.
rev4 R4-A2: J-P3 / J11 / D2 recomputed from the run records (option b); T4-0 / T4 / T5 from the
path 2 run of `chrono_t45_replay` (option c, `p2_t45.py`, pass `--aux t45=<t45_path2.json>`),
graded by path 2 (rev6 4.6, rev7). rev6 4.6 bundle phrase: all L2b rows T4 / T5 over 0 and T4-0
passed -> `일치`(등급 `부분`).
rev24 CD-1 (closed item list of the C-5 row grade): all rows T4-0 / T4 / T5 (CD-6: only the 18 rows of v5 rev6 3,
other rows 해당 없음), J11 (`J11_window`), J-P3, D2 (record, as before) ; L2b rows the CD-2 block ; SCM rows the
CD-4 P3 items (P3-1..P3-5, P3-7, P3-8, FAULT0 graded; P3-6 and P3-9 records; CD-5 without READY). H-9 and
K1_class stay as records whose stops still stop the bundle. Row count 35 = L2b 24 + SCM 11, else S-15.
"""
import json
from pathlib import Path

import p2_cd as CD
import p2_kinds as K
import p2_rules as R

CRITERIA = ("C-5",)
EXPECTED_ROWS = 35
AUX = {}
CTX = {}   # set by p2_chrono per batch: K.ls_input_case context (rev9 R9-4 / rev10 R10-1)
_T45 = {}


def kind_of(case):
    return "stage3"


def _t45():
    if "doc" not in _T45:
        p = AUX.get("t45")
        _T45["doc"] = json.loads(Path(p).read_text(encoding="utf-8")) if p else None
    return _T45["doc"]


_MCASES = set()   # manifest C-5 row names seen over the batches (rev19 R19-6)
# rev19 R19-6 / v5 rev12 2.1: the six VB <-> V0 pairs
PAIRS_R19_6 = (
    ("E_G4_Fs4", "E_G4_Fs4_V0"), ("E_G4_Fs4_ph0.05", "E_G4_Fs4_ph0.05_V0"),
    ("G1R_FS24_FL_top_o050_Fs0", "G1R_FS24_FL_top_o050_Fs0_V0"), ("P3b_J1_B_top_Fs4", "P3b_J1_B_top_Fs4_v0v"),
    ("P3b_J2_B_top_Fs4_m1p1_t180", "P3b_J2_B_top_Fs4_m1p1_t180_v0v"),
    ("S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0", "S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0_v0v"),
)
V0_SUFFIXES = ("_V0", "_v0v")


CD1_ALL_ROWS = ("T4-0", "T4", "T5", "J-P3", "J11_window")
CD1_RECORD_ONLY = ("H-9", "K1_class")


def judge_row(row, case, kind, params):
    _MCASES.update((CTX.get("mrows") or {}).keys())
    items, keys, notes = K.items_c5(row, params, _t45(), case=case, ctx=CTX)
    graded = [k for k in keys if k in CD1_ALL_ROWS]
    for k in CD1_RECORD_ONLY:
        if isinstance(items.get(k), dict):
            items[k]["cd1_role"] = "record (CD-1 closed item list); a stop still stops the bundle"
    CD.apply_t45_targets(items, graded, row)
    if row.engine == "l2b":
        items["CD-2"] = CD.cd2_items(row, params)
        graded.append("CD-2")
    elif row.engine == "scm":
        _add_p3(items, graded, notes, row, params)
    return items, graded, notes, False


def _add_p3(items, graded, notes, row, params):
    """CD-4: the P3 definitions used for the C-2 / C-3 / C-4 SCM rows (`items_p3`), P3-6 as the recorded READY
    time (flat 90 / slope 120 s, as C-3 / C-4), plus P3-7; CD-5 without READY; CD-4 empty-grade guard."""
    limit = R.READY_FLAT_S if row.flat else R.READY_SLOPE_S
    p3, p3_keys, p3_notes = K.items_p3(row, params, limit, ready_judged=False, g6=False, allow_stop=True)
    for k, v in p3.items():
        items.setdefault(k, v)
    graded += [k for k in p3_keys if k in CD.P3_KEYS or k == "safe_stop_427_9"]
    CD.add_p3_7(items, graded, row, params, judged=True)
    CD.apply_ready_none(items, graded, row)
    CD.scm_grade_guard(items, graded)
    notes += [n for n in p3_notes if n not in notes]


def pairs_found(names) -> list:
    """VB <-> V0 pairs found in the row names: <name> with <name>_V0 or <name>_v0v."""
    s = set(names)
    return sorted((n, n + suf) for n in s for suf in V0_SUFFIXES if n + suf in s)


def pair_check(rows, manifest_cases) -> dict:
    """rev19 R19-6: pairs from the C-5 batch rows and the manifest rows together must be exactly the six of v5 rev12
    2.1 (else S-15, no grade); VB fail and V0 pass -> stop (rev12 2.2); the pair grade comparison is a record."""
    names = {r["case"] for r in rows} | set(manifest_cases)
    found = pairs_found(names)
    want = sorted(PAIRS_R19_6)
    out = {"clause": "rev19 R19-6 / v5 rev12 2.1, 2.2", "found": found, "expected": want,
           "exact": found == want, "pairs": [], "stops": []}
    if found != want:
        out["stops"].append(f"S-15 (rev19 R19-6): VB<->V0 pairs {found} != the six of v5 rev12 2.1")
        return out
    st = {r["case"]: r["status"] for r in rows}
    for vb, v0 in want:
        rec = {"vb": vb, "v0": v0, "vb_status": st.get(vb), "v0_status": st.get(v0), "verdict": "record"}
        if st.get(vb) == "미달" and st.get(v0) == "통과":
            out["stops"].append(f"v5 rev12 2.2: VB {vb} 미달 with V0 {v0} 통과 -> stop and ask")
        out["pairs"].append(rec)
    return out


def engine_counts(rows) -> dict:
    """CD-1: C-5 rows 35 = L2b 24 + SCM 11; any other count is S-15."""
    n_l2b = sum(1 for r in rows if r["engine"] == "l2b")
    n_scm = sum(1 for r in rows if r["engine"] == "scm")
    out = {"clause": "CD-1", "l2b": n_l2b, "scm": n_scm, "expected": [CD.C5_ROWS_L2B, CD.C5_ROWS_SCM]}
    if (n_l2b, n_scm) != (CD.C5_ROWS_L2B, CD.C5_ROWS_SCM):
        out["stop"] = f"S-15 (CD-1): L2b {n_l2b} / SCM {n_scm} != 24 / 11"
    return out


def bundle_status(rows):
    pc = pair_check(rows, _MCASES)
    ec = engine_counts(rows)
    b = K.bundle_status(rows, EXPECTED_ROWS, extra_stops=pc["stops"] + ([ec["stop"]] if "stop" in ec else []))
    b["rev19_R19_6_pairs"] = pc
    b["cd1_engine_counts"] = ec
    if not pc["exact"] or "stop" in ec:
        b["status"] = "판정 불가"   # S-15: no grade
    l2b = [r for r in rows if r["engine"] == "l2b" and r["case"] in CD.T45_TARGET_ROWS]   # CD-6 target rows
    over = sum(int(r["items"].get(k, {}).get("over_0p6kN") or 0) for r in l2b for k in ("T4", "T5"))
    t40 = all(r["items"].get("T4-0", {}).get("verdict") == "pass" for r in l2b) if l2b else False
    b["rev6_4_6_phrase"] = ("일치(등급 부분)" if (t40 and over == 0) else
                            ("불일치 (H-7)" if over > 0 else "판정 안 함 (T4-0 또는 입력)"))
    b["t45_report"] = AUX.get("t45")
    ls = [r["items"].get("LS_class") or {} for r in rows]
    b["rev9_R9_4_ls"] = {"ls_rows": sum(1 for x in ls if x.get("ls") is True),
                         "not_ls_rows": sum(1 for x in ls if x.get("ls") is False),
                         "not_judgeable_rows": sum(1 for x in ls if "ls" in x and x["ls"] is None)}
    return b
