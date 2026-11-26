"""k03: debug trace of the FR probe leg (round 1) of R12_top-FR-Fs8-o0.0_D8-M-a2: per controller
log period the phase, probe leg, round count, FR command, FR force / piston reading, to locate
the mid and extended readings of the cue.

Usage: conda run -n dynamics-dev python -I -B k03_debug_fr.py
Output: k03_out.txt (this folder).
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / "dynamics_d1_d3" / "rerun_raw" / "logs"
RUN = "R12_top-FR-Fs8-o0.0_D8-M-a2"


def main() -> int:
    z = np.load(RAW / f"{RUN}_ctrl.npz", allow_pickle=False)
    o = "o1"
    t = z[f"{o}|m.t_s"]
    F = z[f"{o}|s.last_reading.cylinder_force_N"]
    x = z[f"{o}|s.last_reading.rod_stroke_m"]
    xm = z[f"{o}|m.stroke_corrected_m"]
    cmd = z[f"{o}|cmd"]
    ph = z[f"{o}|phase_name"]
    leg = z[f"{o}|s.probe_round.leg"]
    rc = z[f"{o}|s.probe_round_count"]
    lrt = z[f"{o}|s.last_reading.t_s"]
    cue = json.loads((RAW / f"{RUN}_cue.json").read_text(encoding="utf-8"))
    mids = [c["first_move_mid_force_N"] for c in cue["cue"]]
    exts = [c["extended_force_N"] for c in cue["cue"]]
    lines = []
    for k in range(len(t)):
        if not (32.5 <= t[k] <= 40.5):
            continue
        tags = []
        for j in range(4):
            if any(abs(F[k, j] - m) < 1.0 for m in mids):
                tags.append(f"MID{j}")
            if any(abs(F[k, j] - e) < 1.0 for e in exts):
                tags.append(f"EXT{j}")
        lines.append(f"t={t[k]:.2f} lr_t={lrt[k]:.2f} ph={ph[k]} rc={rc[k]} leg={leg[k]} "
                     f"cmd={np.round(cmd[k] * 1e3, 3)} F={np.round(F[k] / 1e3, 2)} "
                     f"x={np.round(x[k] * 1e3, 3)} xm={np.round(xm[k] * 1e3, 3)} {' '.join(tags)}")
    (HERE / "k03_out.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
