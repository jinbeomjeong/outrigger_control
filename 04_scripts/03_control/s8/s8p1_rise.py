"""RE1b other-leg 'rise': split contact-point height change and the L1 N/kn term (L2b NSC)."""
import sys, os, json, numpy as np
d = sys.argv[1]; kn = float(sys.argv[2]); t_ev_rel = float(sys.argv[3]); t_end_rel = float(sys.argv[4]); t0 = 3.0
p = np.load(os.path.join(d, "pads.npz"))
tp = p["t"] - t0
n = p["n_world"]; nref = n[(tp >= t_ev_rel - 0.1) & (tp < t_ev_rel)].mean(0); nref /= np.linalg.norm(nref)
cp = p["contact_point_world"] @ nref
N = np.clip(p["N"], 0, None)
before = (tp >= t_ev_rel - 0.1) & (tp < t_ev_rel)
inside = (tp >= t_ev_rel) & (tp <= t_end_rel)
dcp = cp[inside] - cp[before].mean(0)
dNk = (N[inside] - N[before].mean(0)) / kn
tot = dcp + dNk
for leg, name in enumerate(["FL", "FR", "RL"]):
    k = np.argmax(tot[:, leg])
    print(f"{name}: rise max {tot[k,leg]*1e3:.2f} mm = contact-point {dcp[k,leg]*1e3:.3f} mm + dN/kn {dNk[k,leg]*1e3:.2f} mm "
          f"(dN {(N[inside][k,leg]-N[before].mean(0)[leg])/1e3:.1f} kN); contact-point max {dcp[:,leg].max()*1e3:.3f} mm; "
          f"airborne samples {int(p['airborne'][inside][:,leg].sum())}")
