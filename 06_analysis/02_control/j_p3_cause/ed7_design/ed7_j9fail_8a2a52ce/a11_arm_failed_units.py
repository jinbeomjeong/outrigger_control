"""a11: V0-relative failed (plant, key) units of every probe 6bfb2560 main-part arm, including
the c2 control arm (A_ib on, D6 witness and (i-b) retract position target off) and a1/a5/a6,
with the judge-commit T (60ebb4a4) adoption-tool functions and its FIXED reading
(J7 ed7_new, sens plants stiffness-exempt, VBM 5 plants). Only COMPARED_ARMS is widened (and
the expected ib condition of the extra arms); nothing is written into the tool or the run
folders. Output: a11_arm_failed_units.json in this folder.

Run (dynamics-dev): python -I -B a11_arm_failed_units.py
"""
import json
import os
import sys
from pathlib import Path

T = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed7-judge")
sys.path[:0] = [str(T / "04_scripts" / "04_hydraulic" / "coupled"), str(T / "03_src")]
import ed7_condition3_adoption as ad  # noqa: E402

OUT = Path(os.path.dirname(os.path.abspath(__file__)))
J = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause")
ROWS = J / "j9_runs" / "6bfb2560" / "ed7_probe_a1" / "ed7_probe.jsonl"
KEYS = J / "ed7_design" / "tool_6bfb2560" / "keys" / "probe_keys_ed7.json"
KEYS_SHA = "189dbb1315e2267812a1a14724c1cf405c96b70e2f43735ee22da940b28053da"
V0 = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\main.jsonl")
V0_SHA = "9ad749907c34c9e9efb77579a8ab6e3b1f86cdc32d36162c0029005ca545b29e"
ARMS = ("a1", "a2", "a3", "a4", "a5", "a6", "c2")

ad.COMPARED_ARMS = ARMS
for arm in ("a1", "a5", "a6", "c2"):
    ad.EXPECTED_CONDITION.setdefault(arm, "with_twist")
keys, planned = ad.read_key_file(KEYS, KEYS_SHA)
v0_rows = ad.v0_metric_rows(V0, V0_SHA)
t4h = ROWS.with_name(f"{ROWS.stem}_t4h")
scan = ad.scan_lines(ROWS, t4h, planned, keys, ad.expected_options)
groups = {k: ad.group_judgement(m, v0_rows) for k, m in scan.metrics.items()}
out = {"inputs": {"rows": str(ROWS), "keys_sha256": KEYS_SHA, "v0_sha256": V0_SHA,
                  "tool_checkout": str(T), "tool_identity": ad.code_identity()},
       "reading": "J7 ed7_new, stiffness exempt on Mslow/Mfast/Mc005/Mc04, plants VBM5",
       "arms": {}}
for arm in ARMS:
    units = []
    for plant in ad.PLANT_SETS["vbm5"]:
        g = groups.get((plant, arm, ad.MAIN_PART))
        if g is None:
            units.append([plant, "NO_GROUP"])
            continue
        exempt = plant in ad.SENSITIVITY_PLANTS
        for key in sorted(ad.failed_keys(g, "ed7_new", exempt_stiffness=exempt)):
            items = [f'{i["item"]}: {i["detail"]}' for i in g["fail_items"]["ed7_new"]
                     if i["key"] == key and not (exempt and i["item"] == "J7")]
            units.append([plant, key, items])
    out["arms"][arm] = {"failed_units": len([u for u in units if u[1] != "NO_GROUP"]),
                        "units": units}
    print(arm, out["arms"][arm]["failed_units"], json.dumps(units, ensure_ascii=False)[:1200])
(OUT / "a11_arm_failed_units.json").write_text(json.dumps(out, indent=1, ensure_ascii=False),
                                               encoding="utf-8")
