"""Dump TOUCH-phase time series for an S8 case at a coarse stride."""
import sys, os, numpy as np
d = sys.argv[1]
stride = int(sys.argv[2]) if len(sys.argv) > 2 else 10
t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
t1 = float(sys.argv[4]) if len(sys.argv) > 4 else 1e9
rec = np.load(os.path.join(d, "record/record.npz"))
r8 = np.load(os.path.join(d, "r8_series.npz"))
t = r8["t"]
np.set_printoptions(precision=2, suppress=True, linewidth=250)
print("t phase | s_motor[mm] | F_cyl[kN] | F_hat[kN] | F_low[kN] | contact | issued_u[mm/s] | Fband")
for k in range(0, len(t), stride):
    if t[k] < t0 or t[k] > t1:
        continue
    print(f"{t[k]:6.1f} {r8['phase'][k]:>6s} | {np.array2string(rec['s_motor'][k]*1e3)} | "
          f"{np.array2string(rec['F_cyl'][k]/1e3)} | {np.array2string(r8['F_hat_N'][k]/1e3)} | "
          f"{np.array2string(r8['F_lower_N'][k]/1e3)} | {rec['pad_in_contact'][k].astype(int)} | "
          f"{np.array2string(r8['issued_u'][k]*1e3)} | {r8['F_band_N'][k]/1e3:.2f} | {r8['limit_flags'][k][:60]}")
