"""List harness rows whose min true force after crawler lift-off is within F_s of F_min (read-only).

The harness 'true' force is F_a = F_cyl + f (|f| <= F_s per leg, front F_s, rear 0.8333 F_s), so a row
with F_a - F_min < F_s could change verdict if judged on F_cyl.  Prints id, F_s, min F_a, margin.
"""
import json
import sys
from pathlib import Path

D = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9")
F_MIN = 9.415
for n in sys.argv[1:]:
    doc = json.loads((D / n).read_text(encoding="utf-8"))
    recs = doc.get("records") or doc.get("results")
    items = recs.items() if isinstance(recs, dict) else [((r.get("id") or r.get("key")), r) for r in recs]
    rows = []
    for rid, r in items:
        if not isinstance(r, dict):
            continue
        v = r.get("min_true_Fcyl_after_off_kN")
        case = r.get("case", {}) if isinstance(r.get("case"), dict) else {}
        fs = case.get("fs_kN", r.get("fs_kN"))
        if v is None or fs is None:
            continue
        if v - F_MIN < max(float(fs), 0.0) + 1e-9:
            rows.append((rid, fs, v, v - F_MIN, r.get("verdict")))
    print("==", n, "rows within F_s of F_min:", len(rows))
    for x in sorted(rows, key=lambda t: t[2])[:30]:
        print("   ", x[0], "Fs", x[1], f"minFa {x[2]:.2f} kN margin {x[3]:+.2f}", x[4])
