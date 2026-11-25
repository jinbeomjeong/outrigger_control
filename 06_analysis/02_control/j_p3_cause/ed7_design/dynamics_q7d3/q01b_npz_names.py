"""List all T4h array names (tail) and meta_json top keys for one a2 repro npz."""
import json
from pathlib import Path

import numpy as np

T4H = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\b46bdf8f\repro_a2\ed7_probe_a2_t4h")
f = sorted(T4H.glob("R12_top-FR-Fs0-o0.05_P7-M-a2.npz"))[0]
z = np.load(f, allow_pickle=False)
names = z.files
i0 = names.index("lsb_g2_split")
for n in names[i0:]:
    print(n, z[n].dtype, z[n].shape)
meta = json.loads(str(z["meta_json"]))
print("META KEYS:", list(meta.keys())[:80])
