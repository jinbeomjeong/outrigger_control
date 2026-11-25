"""Review ed7 key lists (no metrics): sensitivity probe_seen structure, G1 pool overlaps.
stats-design-expert review, 2026-11-24. Writes r00_inspect.json next to this script."""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent
KEYS = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\tool_a6fc3dd5\keys")
POOL = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\stats_v7\s30_pool_runs.csv")
OPP = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\stats_v7\s30_pool_opp_p.csv")


def main() -> int:
    res = {}
    sens = json.loads((KEYS / "sens_keys_ed7.json").read_text(encoding="utf-8"))
    res["sens_top"] = {k: v for k, v in sens.items() if k != "lines"}
    probe = json.loads((KEYS / "probe_keys_ed7.json").read_text(encoding="utf-8"))
    res["probe_keys"] = probe["keys"]
    res["probe_plants"] = probe["plants"]
    lines = sens["lines"]
    res["sens_line_fields"] = sorted(lines[0].keys())
    res["sens_job_fields"] = sorted(lines[0]["job"].keys())
    res["sens_key_examples"] = [ln["key"] for ln in lines[:5]]
    per_setting = defaultdict(lambda: {"lines": 0, "seen": 0, "judged": 0})
    for ln in lines:
        s = ln["job"]["setting"]
        per_setting[s]["lines"] += 1
        per_setting[s]["seen"] += int(bool(ln["probe_seen"]))
        per_setting[s]["judged"] += int(bool(ln["judged"]))
    res["sens_per_setting"] = dict(per_setting)
    # row structure inside one judged setting (row key = case + twin; phase = offset/eps)
    sys.path.insert(0, r"C:\workspace\outrigger_control\.claude\worktrees\ed7-impl\04_scripts\04_hydraulic\coupled")
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "jp3_ed7_rules", r"C:\workspace\outrigger_control\.claude\worktrees\ed7-impl\04_scripts\04_hydraulic\coupled\jp3_ed7_rules.py")
    rules = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rules)
    rows = defaultdict(lambda: {"phases": 0, "seen": 0, "keys": []})
    for ln in lines:
        if ln["job"]["setting"] != "VBMslow":
            continue
        rk = rules.row_key(ln["job"])
        rows[rk]["phases"] += 1
        rows[rk]["seen"] += int(bool(ln["probe_seen"]))
        rows[rk]["keys"].append(ln["key"])
    res["sens_rows_VBMslow"] = {k: {"phases": v["phases"], "seen": v["seen"]} for k, v in rows.items()}
    res["sens_rows_VBMslow_keys"] = {k: v["keys"] for k, v in rows.items()}
    res["sens_frame_VBMslow"] = sorted(((v["phases"], v["seen"]) for v in rows.values()), reverse=True)
    seen_keys_in_sens = sorted({ln["key"] for ln in lines if ln["probe_seen"]})
    res["probe_keys_in_sens"] = seen_keys_in_sens
    # G1 pool
    pool = list(csv.DictReader(POOL.open(encoding="utf-8")))
    cl = defaultdict(list)
    for r in pool:
        cl[(r["level"], float(r["fs_kN"]), r["timing"], r["leg"], r["event"])].append(r)
    mixed = {c for c, m in cl.items() if len({x["v0_pass"] for x in m}) > 1}
    nocand = {c for c, m in cl.items() if not any(x["used_ed6"] == "False" and x["v0_pass"] == "True" for x in m)}
    allfail = {c for c, m in cl.items() if all(x["v0_pass"] == "False" for x in m)}
    res["g1"] = {"clusters": len(cl), "mixed": len(mixed), "nocand": len(nocand),
                 "mixed_and_nocand": [list(c) for c in mixed & nocand],
                 "all_v0_fail": len(allfail),
                 "nocand_not_allfail": [list(c) for c in nocand - allfail],
                 "eligible": len(set(cl) - mixed - nocand)}
    # s31 frame: clusters of opp_p with p_np == 0
    opp = list(csv.DictReader(OPP.open(encoding="utf-8")))
    res["opp_fields"] = list(opp[0].keys())
    s31_cl = defaultdict(list)
    for r in opp:
        if float(r["p_np"]) > 0:
            continue
        s31_cl[(r["level"], float(r["fs_kN"]), r["timing"], r["leg"], r["event"])].append(float(r["p_margin"]))
    res["s31_clusters"] = len(s31_cl)
    elig = set(cl) - mixed - nocand
    res["s31_vs_impl_cluster_sets_equal"] = set(s31_cl) == elig
    res["s31_minus_impl"] = [list(c) for c in set(s31_cl) - elig]
    res["impl_minus_s31"] = [list(c) for c in elig - set(s31_cl)]
    u832 = [("bottom", 2.0, "ready", "FL", "RE1bF"), ("bottom", 2.0, "ready", "FR", "RE1bF"),
            ("bottom", 4.0, "ready", "FR", "RE1bF")]
    fl4 = ("bottom", 4.0, "ready", "FL", "RE1bF")
    res["u832_pmargin"] = {"|".join(map(str, c)): s31_cl.get(c) for c in u832}
    res["fl4_pmargin"] = s31_cl.get(fl4)
    res["fl4_candidates"] = [x["offset_s"] for x in cl[fl4] if x["used_ed6"] == "False" and x["v0_pass"] == "True"]
    res["u832_candidates"] = {"|".join(map(str, c)): [x["offset_s"] for x in cl[c] if x["used_ed6"] == "False" and x["v0_pass"] == "True"] for c in u832}
    (OUT / "r00_inspect.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
