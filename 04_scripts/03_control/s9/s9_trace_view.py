"""Print a decimated trace of one run of an s9_soil_closed_loop result (inspection helper)."""
import json
import sys

d = json.loads(open(sys.argv[1], encoding="utf-8").read())
key = sys.argv[2]
step = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
t_lo = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
t_hi = float(sys.argv[5]) if len(sys.argv) > 5 else 1e9
for r in d["runs"]:
    if r["id"] != key:
        continue
    cols = r["trace_cols"]
    print({k: v for k, v in r.items() if k not in ("trace", "trace_cols", "events", "case")})
    print("events:", r["events"][:80])
    sel = ("t", "u_FL", "u_RL", "x_FL", "x_RL", "Fread_FL", "Fread_FR", "Fread_RL", "Fread_RR", "Ftrue_FL", "Ftrue_RL",
           "z_FL", "z_RL", "z_RR", "crawler_kN", "roll", "pitch", "clear_true_mm", "clear_est_mm", "phase")
    idx = [cols.index(c) for c in sel]
    print(" ".join(f"{c:>8s}" for c in sel))
    nxt = t_lo
    for row in r["trace"]:
        if row[0] + 1e-9 >= nxt and t_lo <= row[0] <= t_hi:
            print(" ".join(f"{row[i]:>8}" if isinstance(row[i], str) else f"{row[i]:8.2f}" if abs(row[i]) >= 0.1 or row[i] == 0 else f"{row[i]:8.4f}" for i in idx))
            nxt = row[0] + step
