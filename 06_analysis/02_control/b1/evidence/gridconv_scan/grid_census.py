"""Census of SCM pad grid used by stored S9 Chrono rows (read-only): soil, pad variant, grid per case."""
import json
import sys
from collections import Counter
from pathlib import Path

root = Path(r"C:\workspace\outrigger_control\07_results\S9")
cnt = Counter()
rows = []
for bj in sorted(root.glob("batch_*/batch.json")):
    try:
        b = json.loads(bj.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print("ERR", bj, e)
        continue
    cases = b.get("cases") or []
    for c in cases:
        argv = c.get("argv") or []
        if isinstance(argv, str):
            argv = argv.split()

        def val(flag):
            if flag in argv:
                i = argv.index(flag)
                return argv[i + 1] if i + 1 < len(argv) else None
            return None
        soil = val("--soil")
        grid = val("--grid")
        pv = val("--pad-variant")
        mode = next((a for a in argv if a in ("level", "machine", "single-pad")), "?")
        key = (bj.parent.name, mode, soil, pv, grid, val("--soil-patch-grid"))
        cnt[key] += 1
for k, v in sorted(cnt.items()):
    if k[2] in ("J1", "J2") or (k[5] is not None):
        print(*k, v, sep=" | ")
