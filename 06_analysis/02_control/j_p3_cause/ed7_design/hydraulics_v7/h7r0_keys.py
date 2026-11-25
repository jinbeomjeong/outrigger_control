"""List the T4h arrays of one Part D npz (shapes, dtypes) and its meta keys.

Read only. Run: hydraulics-dev python.exe -I -B h7r0_keys.py <npz>
"""
import json
import sys
from pathlib import Path

import numpy as np


def main() -> None:
    path = Path(sys.argv[1])
    with np.load(path, allow_pickle=False) as data:
        for name in sorted(data.files):
            arr = data[name]
            extra = ""
            if arr.dtype.kind in "US" and arr.size < 20:
                extra = f" {arr.tolist()}"
            elif arr.ndim == 0:
                extra = f" {arr.item()!r}"[:300]
            print(f"{name:45s} {arr.dtype!s:8s} {arr.shape}{extra}")
        if "meta_json" in data.files:
            meta = json.loads(str(data["meta_json"]))
            print(json.dumps(meta, indent=1)[:4000])


if __name__ == "__main__":
    main()
