"""List array names, shapes and meta keys of a few T4h npz files."""
import json
import sys

import numpy as np

DIR = (r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
       r"\6bfb2560\ed7_probe_a1\ed7_probe_t4h")
for name in sys.argv[1:]:
    with np.load(f"{DIR}\\{name}", allow_pickle=False) as data:
        print("==", name)
        for k in data.files:
            a = data[k]
            extra = ""
            if a.dtype.kind in "US" and a.size < 20:
                extra = str(a)[:200]
            print(f"  {k}: {a.dtype} {a.shape} {extra}")
        if "meta_json" in data.files:
            meta = json.loads(str(data["meta_json"]))
            print("  meta keys:", list(meta.keys()))
            for k in ("head_only_declared", "p1_read_columns", "p1_columns"):
                if k in meta:
                    print("   ", k, json.dumps(meta[k])[:600])
            for k, v in meta.items():
                if "p1" in k or "code" in k.lower():
                    print("   ", k, json.dumps(v)[:800])
