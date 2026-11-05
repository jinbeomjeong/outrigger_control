"""Where does the suffix-minimum difference to the stored judge come from: largest differences with the row, and the same check moving the window index by one sample. Also the size of the dynamics tail scan."""
import json
from pathlib import Path

import numpy as np

S = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\chrono\k1soil\sweep")
LEGS = ("FL", "FR", "RL", "RR")
res = []
for arm in ("A", "B", "Af", "Bf"):
    z = np.load(S / f"{arm}.npz")
    for line in (S / f"{arm}.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        key = f"{r['row']}_{r['delta']:.2f}"
        t, suf = z[key + "_t"], z[key + "_sufmin"]
        k = int(np.searchsorted(t, r["W_end_s"], side="right"))
        for i, l in enumerate(LEGS):
            st = r["min_F_after_W_kN"][l]
            ds = [abs(float(suf[min(k + m, len(t) - 1), i]) / 1e3 - st) for m in (-2, -1, 0, 1, 2)]
            res.append((ds[2], min(ds), arm, key, l))
res.sort(reverse=True)
print("top", [(round(a, 3), round(b, 3), c, d, e) for a, b, c, d, e in res[:6]])
print("n > 0.01 kN at index 0", sum(x[0] > 0.01 for x in res), "of", len(res), "; best of +-2 samples max", round(max(x[1] for x in res), 4))
scan = json.loads(Path(r"C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\dyn_k1osc\a06_scan.json").read_text(encoding="utf-8"))
print(type(scan).__name__, list(scan)[:10] if isinstance(scan, dict) else len(scan))
rows = scan if isinstance(scan, list) else next((v for v in scan.values() if isinstance(v, list)), [])
print("scan rows", len(rows), "keys", list(rows[0])[:20] if rows else None)
if rows:
    print("no_creep_stop rows", [r.get("case") for r in rows if r.get("no_creep_stop")][:20])
