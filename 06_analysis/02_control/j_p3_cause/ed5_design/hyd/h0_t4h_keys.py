"""List T4h npz keys of the VBH / VBJ runs and estimate the stroke reading noise on locked,
command-free reads (diff of motor_stroke_m between consecutive reads)."""
import json
from pathlib import Path

import numpy as np

RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\78fd5d2d\dg3_a1")
U_HOLD = 2.0924e-4

for setting in ("VBH", "VBJ"):
    lines = json.loads((RUN / f"dg3_{setting}.json").read_text(encoding="utf-8"))["results"]
    files = sorted((RUN / f"{setting}_t4h").glob("*.npz"))
    print(setting, "lines", len(lines), "npz", len(files))
    with np.load(files[0], allow_pickle=False) as z:
        print(" keys", {k: z[k].shape for k in z.files})
    # noise estimate: reads where the plant is locked on both reads and command zero
    by_level = {}
    for line in lines:
        key = line["key"].split("#", 1)[-1]
        level = key.split("|", 1)[0]
        with np.load(RUN / f"{setting}_t4h" / line["t4h_file"], allow_pickle=False) as z:
            s = z["motor_stroke_m"]
            locked = z["locked"]
            cmd = z["command_m_s"]
        both = locked[1:] & locked[:-1] & (np.abs(cmd[1:]) == 0.0) & (np.abs(cmd[:-1]) == 0.0)
        d = np.diff(s, axis=0)[both]
        by_level.setdefault(level, []).append(d)
    for level, parts in sorted(by_level.items()):
        d = np.concatenate(parts)
        if d.size:
            print(f"  {level}: n={d.size} std(diff)={d.std()*1e3:.4f} mm  max|diff|={np.abs(d).max()*1e3:.4f} mm")
