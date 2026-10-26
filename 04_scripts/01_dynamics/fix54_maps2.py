"""Flat-floor axis stroke boundaries at 700 mm stroke (margins 0 / 10 mm) for clearance 50/20/0 mm."""
import json
import numpy as np

E = r"C:\workspace\outrigger_control\06_analysis\00_dynamics\target_envelope.json"
d = json.load(open(E, encoding="utf-8"))
roll = np.array(d["meta"]["grid_roll_deg"]); pitch = np.array(d["meta"]["grid_pitch_deg"])
smax = d["meta"]["stroke_m"] * 1000.0


def cross(x, y, lim):
    for i in range(1, len(x)):
        if y[i] > lim >= y[i - 1]:
            return x[i - 1] + (lim - y[i - 1]) * (x[i] - x[i - 1]) / (y[i] - y[i - 1])
    return None


res = {}
for stg in ("top|flat", "middle|flat", "bottom|flat"):
    g = d["maps"][stg]
    for c in ("c50", "c20", "c0"):
        S = np.array(g[f"s_max_{c}_m"], dtype=float).T * 1000.0
        S = np.where(np.isfinite(S), S, 1e9)
        i0 = int(np.argmin(abs(pitch))); j0 = int(np.argmin(abs(roll)))
        for mg in (0.0, 10.0):
            lim = smax - mg
            rp, rn, pp, pn = roll >= 0, roll <= 0, pitch >= 0, pitch <= 0
            v = (cross(roll[rp], S[rp, i0], lim), cross(-roll[rn][::-1], S[rn, i0][::-1], lim),
                 cross(pitch[pp], S[j0, pp], lim), cross(-pitch[pn][::-1], S[j0, pn][::-1], lim))
            res.setdefault((c, mg), []).append(v)
for k, vs in res.items():
    a = np.array([[np.nan if x is None else x for x in v] for v in vs])
    print(k, "roll", np.round(np.nanmin(a[:, :2]), 2), np.round(np.nanmax(a[:, :2]), 2),
          "pitch+", np.round(a[:, 2].min(), 2), np.round(a[:, 2].max(), 2),
          "pitch-", np.round(a[:, 3].min(), 2), np.round(a[:, 3].max(), 2))
