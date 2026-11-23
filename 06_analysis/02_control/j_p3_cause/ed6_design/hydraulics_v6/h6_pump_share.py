"""Edition 6 A(ii): pump flow of simultaneous lock-start fills (hydraulics-expert, hand check).

Flow of each leg at the per-leg command cap v_max (head side for extension, annulus for retract)
against the pump drawing flow 60.2 L/min x 0.95 (YAML basis of v_max), and the oil of one fill.
Results in ``h6_pump_share.json``. Areas and v_max are the YAML values; p values are gauge.
"""
from __future__ import annotations

import json
from pathlib import Path

A_H = [0.0132732289, 0.0132732289, 0.0095033178, 0.0095033178]  # m2
A_ANN = [0.00376991118, 0.00376991118, 0.00314159265, 0.00314159265]  # m2
V_MAX = 0.0209243016  # m/s
STEP = 0.25 * V_MAX
Q_PUMP = 60.2 / 60000.0  # m3/s drawing flow
ETA = 0.95
LPM = 60000.0


def main() -> None:
    ext = [a * V_MAX * LPM for a in A_H]
    ret = [a * V_MAX * LPM for a in A_ANN]
    res = {
        "extension_at_v_max_L_min": [round(q, 3) for q in ext],
        "extension_sum_L_min": round(sum(ext), 3),
        "retract_at_v_max_L_min": [round(q, 3) for q in ret],
        "retract_sum_L_min": round(sum(ret), 3),
        "pump_times_eta_L_min": round(Q_PUMP * ETA * LPM, 3),
        "four_leg_one_increment_extension_L_min": round(sum(a * STEP * LPM for a in A_H), 3),
        "retract_fill_oil_cm3_front_3p1mm": round(A_ANN[0] * 3.1e-3 * 1e6, 2),
        "extension_line_oil_cm3_p90bar": round(285e-6 * 88e5 / 0.5e9 * 1e6, 2),
        "note": "v_max is defined so that sum(A_h) v_max = 0.95 Q_pump; a fill floor that keeps "
                "|u| <= v_max per leg cannot ask more than the pump (flow share off in the harness)",
    }
    out = Path(__file__).resolve().parent / "h6_pump_share.json"
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
