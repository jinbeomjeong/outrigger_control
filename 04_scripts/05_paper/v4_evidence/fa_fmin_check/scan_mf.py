"""Rows of finB2_p0 (min_force_kN) and fin_x426_C within F_s(front) of F_min (read-only)."""
import json
import re
from pathlib import Path

D = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9\rev85")
F_MIN = 9.415
doc = json.loads((D / "finB2_p0.json").read_text(encoding="utf-8"))
hits = []
for r in doc["records"]:
    v = r.get("min_force_kN")
    m = re.search(r"Fs([0-9.]+)", r["id"])
    fs = float(m.group(1)) if m else None
    if v is None or fs is None:
        continue
    if v - F_MIN < fs:
        hits.append((v, r["id"], fs, r.get("verdict")))
hits.sort()
print("finB2_p0 within F_s:", len(hits))
for h in hits:
    print(f"   {h[0]:6.2f} kN margin {h[0]-F_MIN:+.2f}  Fs {h[2]:g}  {h[1]}  {h[3]}")
doc = json.loads((D / "fin_x426_C.json").read_text(encoding="utf-8"))
print("fin_x426_C within F_s:")
for r in doc["results"]:
    v = r.get("min_true_Fcyl_after_off_kN")
    fs = r.get("fs_kN")
    if v is not None and fs is not None and v - F_MIN < fs:
        print(f"   {v:6.2f} kN margin {v-F_MIN:+.2f}  Fs {fs:g}  {r['key']}  pass={r.get('pass')}")
