"""h02: print the T4h meta_json snippets around a few stiffness / volume words (read only)."""
import json
import os
import re

import numpy as np

J9 = r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\8a2a52ce"
NPZ = os.path.join(J9, r"sens_a1\sens_t4h\R12_top-FL-Fs8-o0.0_VBMh15.npz")
OUT = os.path.dirname(os.path.abspath(__file__))
WORDS = ("denominator", "k_nom", "oil_stiff", "head_dead", "rod_dead", "bulk", "line_scale",
         "v_line", "stroke_reading", "corrected", "seal", "stiffness_warning")

import sys  # noqa: E402

if len(sys.argv) > 1:
    WORDS = tuple(sys.argv[1:])
z = np.load(NPZ, allow_pickle=False)
meta = str(z["meta_json"])
lines = [f"meta length {len(meta)}"]
try:
    m = json.loads(meta)
    lines.append("top keys: " + ", ".join(list(m.keys())[:80]))
except json.JSONDecodeError as exc:
    lines.append(f"not json: {exc}")
for w in WORDS:
    for hit in list(re.finditer(w, meta))[:4]:
        a = max(hit.start() - 150, 0)
        lines.append(f"[{w}] ..." + meta[a:hit.end() + 200].replace("\n", " ") + "...")
with open(os.path.join(OUT, "h02_out.txt"), "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(lines) + "\n")
print(len(lines))
