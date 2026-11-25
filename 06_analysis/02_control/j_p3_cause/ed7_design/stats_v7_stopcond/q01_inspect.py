"""Per-setting probe-seen structure of sens_keys_ed7.json and probe keys (no metrics).
Outputs (argv[1]): q01_inspect.json. stdout: status only."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

KEYS = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\tool_a6fc3dd5\keys")


def main() -> int:
    sens = json.loads((KEYS / "sens_keys_ed7.json").read_text(encoding="utf-8"))
    probe = json.loads((KEYS / "probe_keys_ed7.json").read_text(encoding="utf-8"))
    out = {"settings_judged": sens["settings_judged"], "settings_record": sens["settings_record"]}
    per = defaultdict(Counter)
    rows = defaultdict(lambda: defaultdict(list))
    for ln in sens["lines"]:
        s = ln["job"]["setting"]
        per[s]["lines"] += 1
        per[s]["probe_seen"] += int(ln["probe_seen"])
        per[s]["judged"] += int(ln["judged"])
        rows[s][ln["job"]["case"]].append([ln["key"], ln["job"].get("eps"), ln["job"].get("offset_s"),
                                          ln["probe_seen"], ln["judged"], ln["head_only_declared"]])
    out["per_setting"] = {s: dict(c) for s, c in per.items()}
    s0 = sens["settings_judged"][0]
    out["frame_" + s0] = {case: v for case, v in rows[s0].items()}
    out["v0_pair_example"] = sens["lines"][0]["v0_pair"]
    out["probe_top_keys"] = [k for k in probe if k not in ("lines",)]
    out["probe_keys"] = probe["keys"]
    out["probe_plants"] = probe["plants"]
    out["probe_arms"] = probe["arms"]
    for k in probe:
        if k not in ("keys", "plants", "arms", "lines", "generation_command"):
            v = probe[k]
            out["probe_" + k] = v if len(json.dumps(v)) < 3000 else f"<{type(v).__name__} len {len(v)}>"
    if "lines" in probe:
        out["probe_line0"] = probe["lines"][0]
        out["probe_nlines"] = len(probe["lines"])
    (Path(sys.argv[1]) / "q01_inspect.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
