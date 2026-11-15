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


def judge_row(row, case, kind, params):
    _MCASES.update((CTX.get("mrows") or {}).keys())
    items, keys, notes = K.items_c5(row, params, _t45(), case=case, ctx=CTX)
    return items, keys, notes, False


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


def bundle_status(rows):
    pc = pair_check(rows, _MCASES)
    b = K.bundle_status(rows, EXPECTED_ROWS, extra_stops=pc["stops"])
    b["rev19_R19_6_pairs"] = pc
    if not pc["exact"]:
        b["status"] = "판정 불가"   # S-15: no grade
    l2b = [r for r in rows if r["engine"] == "l2b"]
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
