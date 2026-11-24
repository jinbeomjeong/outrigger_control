"""List the arrays and the hydraulic / plant meta of one confirmation (가) T4h file (read only)."""
import json
import sys
from pathlib import Path

import numpy as np

T4H = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405"
           r"\confirm_a1\confirm_a_t4h")


def main(name: str) -> None:
    with np.load(T4H / name, allow_pickle=False) as d:
        for key in d.files:
            arr = d[key]
            print(f"{key:40s} {arr.dtype} {arr.shape}")
        meta = json.loads(str(d["meta_json"]))
    for key, value in meta.items():
        if key == "events":
            continue
        text = json.dumps(value, default=str)
        print(f"META {key}: {text[:1500]}")


if __name__ == "__main__":
    main(sys.argv[1])
