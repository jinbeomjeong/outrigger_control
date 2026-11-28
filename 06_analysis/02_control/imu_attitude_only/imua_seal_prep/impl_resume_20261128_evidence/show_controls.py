"""One line per control of an imua_classify controls report."""

import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for control in report["controls"]:
    values = control["result"].get("values") or {}
    shown = {k: round(v, 4) if isinstance(v, float) else v for k, v in values.items()
             if k != "excluding_events"}
    print(control["group"], control["record"].split("/")[-1], control["expected"],
          control["observed"], control["result"].get("failed"), shown,
          control["result"].get("note"))
