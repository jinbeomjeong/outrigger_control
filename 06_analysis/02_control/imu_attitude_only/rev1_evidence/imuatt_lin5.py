"""Revision 1, third sweep: the A-g gain set (Kp 0.10, Ki 0.005, Kg 0.08) on the 5 Hz (ifm default proxy) and the
two-first-order 1 Hz filters (imuatt_lin3 model)."""
import json
import sys
import time
from multiprocessing import get_context
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import imuatt_lin3 as L3  # noqa: E402

V = {"A2_butter5_Kp0.1_Kg0.08": ("A2", ("butter", 5.0), 2, {"Kp": 0.10, "Ki": 0.005}, 0.08),
     "A_f1.0_Kp0.1_Kg0.08": ("A", (1.0,), 2, {"Kp": 0.10, "Ki": 0.005}, 0.08),
     "A2_bessel1_Kp0.1_Kg0.08_tv0.15": ("A2", ("bessel", 1.0), 2, {"Kp": 0.10, "Ki": 0.005, "tau_v": 0.15}, 0.08)}
L3.V.clear()
L3.V.update(V)


def _init():
    L3.V.clear()
    L3.V.update(V)


def main():
    R = L3.R
    items = R.catalogue_ext()
    pads = [i for i in range(len(items)) if items[i][0].support == "pads" and items[i][1] == 1.0]
    jobs = [(i, v, -1) for i in range(len(items)) for v in V] + [(i, v, g) for i in pads for v in V for g in range(4)]
    t0 = time.time()
    with get_context("spawn").Pool(12, initializer=_init) as pool:
        results = pool.map(L3.one, jobs, chunksize=4)
    json.dump({"variants": V, "results": results}, open(sys.argv[1], "w"), indent=1, default=str)
    print(f"{len(results)} jobs, {sum('error' in r for r in results)} errors, {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
