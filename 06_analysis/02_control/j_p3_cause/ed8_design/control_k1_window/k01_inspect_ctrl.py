"""k01: controller-log keys with 'probe' / 'reading' / 'twist', time coverage, cue rows.

Usage: conda run -n dynamics-dev python -I -B k01_inspect_ctrl.py
Output: k01_out.txt (this folder).
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / "dynamics_d1_d3" / "rerun_raw"
RUN = "R12_top-FR-Fs8-o0.0_D8-M-a2"


def main() -> int:
    lines = []
    z = np.load(RAW / "logs" / f"{RUN}_ctrl.npz", allow_pickle=False)
    objs = sorted({k.split("|")[0] for k in z.files})
    lines.append(f"ctrl objects: {objs}")
    for o in objs:
        t = z[f"{o}|m.t_s"] if f"{o}|m.t_s" in z.files else None
        if t is not None:
            lines.append(f"  {o}: n={len(t)} t0={t[0]:.2f} t1={t[-1]:.2f} dt_med={np.median(np.diff(t)):.3f}")
    for k in z.files:
        if any(s in k for s in ("probe", "twist", "phase", "seal_band", "stiff")):
            lines.append(f"  {k} {z[k].shape} {z[k].dtype}")
    p = np.load(RAW / "logs" / f"{RUN}_plant.npz", allow_pickle=False)
    pobjs = sorted({k.split("|")[0] for k in p.files})
    for o in pobjs:
        if f"{o}|t" in p.files:
            t = p[f"{o}|t"]
            lines.append(f"plant {o}: n={len(t)} t0={t[0]:.3f} t1={t[-1]:.3f} dt_med={np.median(np.diff(t)):.4f}")
    for k in p.files:
        if k.startswith(pobjs[0] + "|") and any(s in k.split("|")[1] for s in ("x", "sref", "stuck", "lk", "f")) and len(k.split("|")[1]) <= 8:
            lines.append(f"  plant {k} {p[k].shape}")
    cue = json.loads((RAW / "logs" / f"{RUN}_cue.json").read_text(encoding="utf-8"))
    for c in cue["cue"]:
        lines.append("cue " + json.dumps({k: c[k] for k in ("leg_index", "is_reversed", "first_move_mid_force_N",
                                                           "first_move_mid_rod_stroke_m", "extended_force_N",
                                                           "extended_rod_stroke_m", "stiffness_N_m", "is_grounded")}))
    for r in cue["ratio"]:
        lines.append("ratio " + json.dumps(r)[:400])
    (HERE / "k01_out.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
