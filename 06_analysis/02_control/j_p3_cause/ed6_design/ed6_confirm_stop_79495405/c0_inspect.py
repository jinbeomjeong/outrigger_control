"""List T4h arrays, meta keys and events of one confirmation (가) T4h file."""
import json
import sys
from pathlib import Path

import numpy as np

T4H = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405"
           r"\confirm_a1\confirm_a_t4h")


def main(name: str) -> None:
    with np.load(T4H / name, allow_pickle=False) as data:
        meta = json.loads(str(data["meta_json"]))
        print("arrays:")
        for key in data.files:
            arr = data[key]
            print(f"  {key} {arr.shape} {arr.dtype}")
    print("meta keys:", sorted(meta))
    events = meta.get("events") or []
    print("n events", len(events))
    for ev in events:
        print("  ", ev)


if __name__ == "__main__":
    main(sys.argv[1])
