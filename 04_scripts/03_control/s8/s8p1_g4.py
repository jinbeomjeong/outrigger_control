"""C-S8-14 style RR timeline of the E-group G4 cases (controller time = record time - 3 s)."""
import sys, os, json, re, numpy as np
base = sys.argv[1]
T0 = 3.0


def find(obj, key):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                return v
            r = find(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find(v, key)
            if r is not None:
                return r
    return None


for name in sorted(os.listdir(base)):
    if not name.startswith("E_G4"):
        continue
    d = os.path.join(base, name)
    res = json.load(open(os.path.join(d, "result.json"), encoding="utf-8"))
    ev = json.load(open(os.path.join(d, "controller_events.json"), encoding="utf-8"))
    evs = [(float(re.search(r"t_s=([0-9.]+)", e).group(1)) - T0, re.search(r"name='([^']+)'", e).group(1)) for e in ev]
    t_ev = res["event_t_s"]
    after = [(round(t - t_ev, 2), n) for t, n in evs if t >= t_ev - 1e-6]
    pads = np.load(os.path.join(d, "pads.npz"))
    r8 = np.load(os.path.join(d, "r8_series.npz"))
    tp = pads["t"] - T0
    w = (tp >= t_ev) & (tp <= t_ev + 10)
    fmin_int = pads["F_cyl_min_interval"][w, 3]
    k = int(np.argmin(fmin_int))
    t_min = tp[w][k] - t_ev
    tr = r8["t"] - T0
    t_pred = next((t for t, n in evs if n.startswith("relevel_predicted") and t >= t_ev), None)
    t_reap = next((t for t, n in evs if n.startswith("leg_reapproach_start") and t >= t_ev), None)
    t_hi = t_reap if t_reap is not None else t_ev + t_min
    sel = (tr > (t_pred if t_pred else t_ev)) & (tr <= t_hi)
    u_rr = r8["issued_u"][sel, 3] * 1e3
    band = r8["leg_band_N"][np.argmin(np.abs(tr - t_ev)), 3] / 1e3
    scale = find(res, "twist_stiffness_scale")
    lowF = r8["F_lower_N"][:, 3] - r8["leg_band_N"][:, 3]
    k_reap_cond = np.flatnonzero((tr >= t_ev) & (lowF < 0.5 * 9414.59))
    print(f"{name:18s} min RR {fmin_int[k]/1e3:6.2f} kN at ev+{t_min:.2f}s | pred ev+{(t_pred - t_ev) if t_pred else None} "
          f"reap ev+{(t_reap - t_ev) if t_reap else None} | RR u mean {u_rr.mean() if u_rr.size else float('nan'):.2f} mm/s "
          f"(n={u_rr.size}) | band {band:.2f} kN | scale {scale} | lower<0.5Fmin first ev+{(tr[k_reap_cond[0]] - t_ev) if k_reap_cond.size else None}")
    print("    events after:", after[:8])
