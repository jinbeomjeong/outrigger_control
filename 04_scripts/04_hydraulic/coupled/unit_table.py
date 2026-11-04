"""Unit conversion table of the valve coefficients and flows, with pint (hydraulic_coupling.md 2).

Writes unit_table.json. K [m3/s/sqrt(Pa)], Kv [m3/h/sqrt(bar)], Cv [US gpm/sqrt(psi)], Cd A [m2].
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pint  # noqa: E402

from params import LEGS, OUT_DIR, load_params  # noqa: E402

U = pint.UnitRegistry()


def row(Q_m3s: float, dp_pa: float, rho: float) -> dict:
    Q = Q_m3s * U("m**3/s")
    dp = dp_pa * U.Pa
    K = (Q / dp**0.5).to("m**3/s/Pa**0.5")
    Kv = (Q.to("m**3/hour") / dp.to("bar") ** 0.5).magnitude
    Cv = (Q.to("gallon/minute") / dp.to("psi") ** 0.5).magnitude
    CdA = (Q / ((2 * dp / (rho * U("kg/m**3"))) ** 0.5)).to("m**2").magnitude
    return {"Q_L_min": Q.to("L/min").magnitude, "dp_bar": dp.to("bar").magnitude, "K": K.magnitude, "Kv": Kv, "Cv": Cv,
            "Cd_A_m2": CdA, "A_at_Cq_mm2": CdA / 0.67 * 1e6}


def main() -> None:
    p = load_params()
    out = {"spool_P_A": {}, "compensator_open": row(p.comp_q_nom, 7e6, p.rho), "unloader_open": row(p.unl_q_nom, 7e6, p.rho),
           "pump": {"Q_th_L_min": p.Q_pump_th * 6e4, "D_cc_rev": 30.0, "n_rpm": p.Q_pump_th / 30e-6 * 60,
                    "Q_eta": {str(e): p.Q_pump_th * e * 6e4 for e in (0.95, 0.90, 0.85)}}}
    for i, leg in enumerate(LEGS):
        out["spool_P_A"][leg] = row(float(p.A_h[i] * p.v_max), p.dp_comp, p.rho)
    (OUT_DIR / "unit_table.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
