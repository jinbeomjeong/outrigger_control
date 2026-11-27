"""G' window shift, part 8: out-of-sample checks of the reduced model calibrated on bottom RE1bF 30/0.05.

(A) Different floor shape, same plant: bottom FR FS24 (24 mm / 0.3 s), stored reruns VBM and U8-A at
    F_s 8 kN (dynamics_u832_o00/rerun_raw; seen keys), own valve history. Compare event-leg and diagonal
    lift intervals (model has no seal friction).
(B) Different inertia, same floor shape: top RE1bF front legs, stored V0 grid (g01 / u04): diagonal first lift
    0.126..0.131 s, event-leg window start bounded by the diagonal starts at the 4 offsets
    (t_r* in (0.275, 0.300] s at F_s 2..4 kN). Top: YAML auger_levels.top inertia, CoM height +1.400 m.
Usage: python -I -B g08_model_check.py <rerun_dir> <out_folder>
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g00_rock_model as rm  # noqa: E402

rerun, out = Path(sys.argv[1]), Path(sys.argv[2])
ens = json.loads((out / "g04_calibration.json").read_text(encoding="utf-8"))["ensemble"]


def intervals(t, F):
    air = F <= 0
    idx = np.flatnonzero(air & (t >= 0))
    if not idx.size:
        return []
    br = np.flatnonzero(np.diff(idx) > 1)
    st = np.r_[idx[0], idx[br + 1]]
    en = np.r_[idx[br], idx[-1]]
    return [(round(float(t[a]), 3), round(float(t[b]) + 1e-3, 3)) for a, b in zip(st, en)]


lines = []
res = {"A_fs24": [], "B_top": []}
for arm in ("VBM", "U8-A"):
    stem = f"R12_bottom-FR-Fs8-o0.0-FS24-ready_{arm}"
    valve, t, rows = rm.load_valve(rerun, stem)
    w = (t >= -0.01) & (t <= 1.2)
    st_ev = intervals(t[w], rows[w, 2])
    st_dg = intervals(t[w], rows[w, 3])
    lines.append(f"(A) {stem}: stored event {st_ev[:3]} diag {st_dg[:3]}")
    for i, p in enumerate(ens[:3]):
        tt, F, g = rm.simulate(1, 0.024, 0.3, p["kf"], p["cf"], valve, h=p["h"], ktf=p["ktf"], t_end=1.2)
        me, md = intervals(tt, F[:, 1]), intervals(tt, F[:, 2])
        lines.append(f"    model ens{i}: event {me[:3]} diag {md[:3]}")
        res["A_fs24"].append({"stem": stem, "ens": i, "stored_event": st_ev[:3], "stored_diag": st_dg[:3],
                              "model_event": me[:3], "model_diag": md[:3]})
I_TOP = [[533505.361, -941.461576], [-941.461576, 688692.429]]
for leg, fs in ((0, 2.0), (1, 2.0), (0, 4.0), (1, 4.0)):
    for i, p in enumerate(ens[:3]):
        tt, F, g = rm.simulate(leg, 0.03, 0.05, p["kf"], p["cf"], None, h=p["h"] + 1.40078, ktf=p["ktf"], i2=I_TOP,
                               t_end=1.2)
        f = rm.window_features(tt, F, g, leg, fs)
        lines.append(f"(B) top {'FL' if leg == 0 else 'FR'} Fs{fs:g} ens{i}: diag lift {f['d_lift']:.3f} (stored 0.126-0.131), "
                     f"t_contact {f['t_contact']:.3f}, t_r* {f['t_r_star']:.3f} (stored bound (0.275, 0.300]), "
                     f"t_h* {f['t_h_star']:.3f}, relift {f['t_relift']:.3f}")
        res["B_top"].append({"leg": leg, "fs": fs, "ens": i, **{k: round(v, 4) for k, v in f.items()}})
(out / "g08_model_check.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
(out / "g08_model_check.txt").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
print(json.dumps({"status": "ok"}))
