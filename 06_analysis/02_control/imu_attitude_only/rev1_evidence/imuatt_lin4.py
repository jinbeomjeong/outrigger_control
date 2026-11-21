"""Revision 1, second sweep: lower gains for the product-shaped inclinometer filters (imuatt_lin3 model)."""
import json
import sys
import time
from multiprocessing import get_context
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import imuatt_lin3 as L3  # noqa: E402

V = {}
for shape in ("bessel", "butter"):
    for kp, kg in ((0.10, 0.10), (0.10, 0.08), (0.08, 0.08)):
        V[f"A2_{shape}1_Kp{kp}_Kg{kg}"] = ("A2", (shape, 1.0), 2, {"Kp": kp, "Ki": kp * 0.05}, kg)
V["A2_butter5_Kp0.12_Kg0.1"] = ("A2", ("butter", 5.0), 2, {"Kp": 0.12, "Ki": 0.006}, 0.10)
V["A2_bessel0.5_Kp0.12_Kg0.1"] = ("A2", ("bessel", 0.5), 2, {"Kp": 0.12, "Ki": 0.006}, 0.10)
for kp, kg in ((0.10, 0.08), (0.08, 0.08)):
    V[f"MA200_Kp{kp}_Kg{kg}"] = ("S0", (None,), 12, {"Kp": kp, "Ki": kp * 0.05}, kg)
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


def _init():
    L3.V.clear()
    L3.V.update(V)


if __name__ == "__main__":
    main()
