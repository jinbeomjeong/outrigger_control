"""List npz keys/shapes for one S8 case."""
import sys, numpy as np, os
d = sys.argv[1]
for f in ["record/record.npz", "r8_series.npz", "s8_series.npz", "pads.npz"]:
    p = os.path.join(d, f)
    z = np.load(p, allow_pickle=True)
    print("==", f)
    for k in z.files:
        a = z[k]
        print(f"  {k}: {a.shape} {a.dtype}")
