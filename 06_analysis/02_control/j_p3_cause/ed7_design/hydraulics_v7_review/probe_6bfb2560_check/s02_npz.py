"""List the arrays of one T4h npz (name, shape, dtype) and print a meta array if present."""
import json
import sys

import numpy as np

with np.load(sys.argv[1], allow_pickle=False) as data:
    for name in data.files:
        array = data[name]
        print(name, array.shape, array.dtype)
    for name in data.files:
        if "meta" in name:
            text = str(data[name])
            try:
                meta = json.loads(text)
                print("META keys:", list(meta)[:80])
            except json.JSONDecodeError:
                print("META raw:", text[:2000])
