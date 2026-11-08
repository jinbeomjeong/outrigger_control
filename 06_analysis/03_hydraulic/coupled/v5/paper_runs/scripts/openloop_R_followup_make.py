"""Make the follow-up copies of the three sealed V5-OPENLOOP-R scripts (prereg 2.3: only the RUNS dict changes).

Reads each original, checks its SHA-256 against the seal, replaces the exact RUNS block by the same block plus the
two follow-up rows (a) P3a_J1_B_V0_rep and (b) P3a_J1_B_V0_R1490k, writes openloop_R_followup_<name>.py next to it
and prints the unified diff (must show RUNS lines only). Usage: python -I openloop_R_followup_make.py
"""
import difflib
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
F = r"C:\workspace\outrigger_control\07_results\S9\batch_V5-OPENLOOP-RFU_20261109_0100"
SEAL = {
    "openloop_R_compare.py": "ccd4528b3740c8a21e7d11564981b9f47222ec34d51d9fae509a51413f204aaa",
    "openloop_R_def2.py": "99bcdc01f805ba3452702c699eb5120fd27d4eda37e8834d4df83c3b65d1cd4d",
    "openloop_R_tm_check.py": "878b54a23a43bc7d3b086ea7a9cc94dc7a4ff3ec26a3c2687776c841cacfab91",
}
EDITS = {
    "openloop_R_compare.py": (
        '    "VB_prop": (R / "batch_V5-OPENLOOP-VB-PROP_20261108_164953/P3a_J1_B_VB_prop", U * 0.894736837447082, 1.0),\n}\n',
        '    "VB_prop": (R / "batch_V5-OPENLOOP-VB-PROP_20261108_164953/P3a_J1_B_VB_prop", U * 0.894736837447082, 1.0),\n'
        f'    "rep_a": (Path(r"{F}\\P3a_J1_B_V0_rep"), U, 1.0),\n'
        f'    "R1490k": (Path(r"{F}\\P3a_J1_B_V0_R1490k"), U, 1490000 / 992000),\n}}\n'),
    "openloop_R_def2.py": (
        '        "VB_prop": R / "batch_V5-OPENLOOP-VB-PROP_20261108_164953/P3a_J1_B_VB_prop"}\n',
        '        "VB_prop": R / "batch_V5-OPENLOOP-VB-PROP_20261108_164953/P3a_J1_B_VB_prop",\n'
        f'        "rep_a": Path(r"{F}\\P3a_J1_B_V0_rep"), "R1490k": Path(r"{F}\\P3a_J1_B_V0_R1490k")}}\n'),
    "openloop_R_tm_check.py": (
        '        "R888k": B / "P3a_J1_B_V0_R888k", "R600k": B / "P3a_J1_B_V0_R600k", "R300k": B / "P3a_J1_B_V0_R300k"}\n',
        '        "R888k": B / "P3a_J1_B_V0_R888k", "R600k": B / "P3a_J1_B_V0_R600k", "R300k": B / "P3a_J1_B_V0_R300k",\n'
        f'        "rep_a": Path(r"{F}\\P3a_J1_B_V0_rep"), "R1490k": Path(r"{F}\\P3a_J1_B_V0_R1490k")}}\n'),
}
for name, (old, new) in EDITS.items():
    src = (HERE / name).read_bytes()
    h = hashlib.sha256(src).hexdigest()
    if h != SEAL[name]:
        sys.exit(f"{name}: sha {h} != seal")
    text = src.decode("utf-8")
    if text.count(old) != 1:
        sys.exit(f"{name}: RUNS block not found once")
    out = text.replace(old, new)
    dst = HERE / name.replace("openloop_R_", "openloop_R_followup_")
    dst.write_bytes(out.encode("utf-8"))
    print(f"== {name} (sha ok) -> {dst.name} sha {hashlib.sha256(out.encode('utf-8')).hexdigest()}")
    sys.stdout.writelines(difflib.unified_diff(text.splitlines(True), out.splitlines(True), name, dst.name, n=0))
