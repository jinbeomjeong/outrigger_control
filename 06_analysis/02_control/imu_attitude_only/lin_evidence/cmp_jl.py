import json
import sys

rows = json.load(open(sys.argv[1]))
for r in sorted(rows, key=lambda r: -r["max_abs_rel"]):
    py, jl = r["python_Ms"], r["julia_Ms"]
    ch = max(py, key=py.get)
    print(f'{r["plant"]:38s} {r["name"]:22s} g{r["guard_leg"]:2d} worst {ch:5s} py {py[ch]:.5f} jl {jl[ch]:.5f} '
          f'max|rel| {r["max_abs_rel"]:.2e} ' + " ".join(f"{k}:{v:+.1e}" for k, v in r["rel"].items()))
