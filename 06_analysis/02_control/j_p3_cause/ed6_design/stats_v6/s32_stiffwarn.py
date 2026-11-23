"""Ed. 6 review: where WARN_PROBE_STIFFNESS_OUT_OF_RANGE occurs in probe 1bd405c8 (seen design
input, ed6_design/probe_1bd405c8/p2_stiffness_warn.json) and how the sensitivity-only J7 exception
(user decision 2026-11-24) changes the sensitivity cluster rule (stats-design-expert, design only).
Writes s32_stiffwarn.json / .txt next to this file. stdout: status only.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "probe_1bd405c8" / "p2_stiffness_warn.json"
PAT = re.compile(r"^probe:(?P<key>.+)_P6-(?P<plant>[^-]+)-(?P<arm>[^-]+)$")
PAT_D0 = re.compile(r"^d0:(?P<key>.+)_(?P<variant>D0-\d+)$")   # ed. 5 D0 rows (8 variants)
PAT_J9 = re.compile(r"^j9main:(?P<key>.+)_(?P<variant>[A-Za-z0-9]+)$")   # ed. 5 j9_main rows


def main() -> int:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    rows = defaultdict(lambda: {"rows": 0, "rows_warn": 0, "n_warn": 0, "ratio_max": 0.0,
                                "phases": set(), "arms_warn": set()})
    bad = []
    for name, warns in d.items():
        m = PAT.match(name)
        if m:
            plant, key, arm = m["plant"], m["key"], m["arm"]
        else:
            m0 = PAT_D0.match(name) or PAT_J9.match(name)
            if not m0:
                bad.append(name)
                continue
            plant = "D0" if name.startswith("d0:") else "j9main_ed5"
            key, arm = m0["key"], m0["variant"]
        m = {"arm": arm}
        cell = rows[(plant, key)]
        cell["rows"] += 1
        if warns:
            cell["rows_warn"] += 1
            cell["n_warn"] += len(warns)
            cell["arms_warn"].add(m["arm"])
            for w in warns:
                cell["ratio_max"] = max(cell["ratio_max"], float(w["ratio"]))
                cell["phases"].add(str(w["phase"]))
    by_plant = defaultdict(lambda: {"rows": 0, "rows_warn": 0, "keys_warn": 0, "keys": 0})
    table = {}
    for (plant, key), c in sorted(rows.items()):
        table[f"{plant}|{key}"] = {**{k: v for k, v in c.items() if k not in ("phases", "arms_warn")},
                                   "phases": sorted(c["phases"]), "arms_warn": sorted(c["arms_warn"])}
        bp = by_plant[plant]
        bp["rows"] += c["rows"]
        bp["rows_warn"] += c["rows_warn"]
        bp["keys"] += 1
        bp["keys_warn"] += int(c["rows_warn"] > 0)
    out = {"source": str(SRC), "n_entries": len(d), "unparsed": bad, "by_plant": by_plant,
           "by_plant_key": table}
    (HERE / "s32_stiffwarn.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    L = [f"entries {len(d)}, unparsed {len(bad)} {bad[:6]}"]
    for p, v in sorted(by_plant.items()):
        L.append(f"plant {p:<5} rows {v['rows']:>3} rows_warn {v['rows_warn']:>3} "
                 f"keys_warn {v['keys_warn']}/{v['keys']}")
    for k, v in table.items():
        if v["rows_warn"]:
            L.append(f"  {k:<34} rows_warn {v['rows_warn']}/{v['rows']} ratio_max "
                     f"{v['ratio_max']:.3f} phases {v['phases']} arms {v['arms_warn']}")
    (HERE / "s32_stiffwarn.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("ok" if not bad else "unparsed_entries")
    return 0 if not bad else 3


if __name__ == "__main__":
    sys.exit(main())
