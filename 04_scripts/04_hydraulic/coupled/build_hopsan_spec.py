"""Generate the JSON spec of the four-leg Hopsan circuit (hopsan-mcp create_model format).

Run in hydraulics-dev. write_hopsan_model.py (env hopsan-mcp) checks it against the
component catalog and writes the .hmf with the same functions create_model uses.
Scenario values are overridden at run time with scenario_overrides().

Rigid body in signals: leg load F_i = F0_i + K_i (s_i - s0_i - w_i) + c_i (v_i - dw_i),
body accelerations from the load changes, w_i = z + yp phi - xp theta. Coupling gains
K_i, c_i = 0 give prescribed loads. Hopsan cylinder force has no atmospheric term, so
F0_i carries + (A_h - A_r) p_atm to keep the gauge chamber pressures equal to the
numpy model.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

from params import LEGS, P_ATM_HOPSAN, Params, load_params  # noqa: E402
from scenarios import Scenario  # noqa: E402 (extension and locked legs only, see Scenario.hopsan)

X_VMAX = 1.0e-3  # spool stroke [m] at u = 1
SPOOL_OMEGA = 2000.0  # rad/s, fast enough to be outside the model scope
TAO_VALVE = 1.0e-4  # s, compensator and inlet compensator lag, numerically small
V_MID = 1.0e-3  # m3, node between compensator and spool (numerical, see hydraulic_coupling.md)
DP_HOPSAN = 1.0e-5  # default time step


def abs_p(p: float) -> float:
    return p + P_ATM_HOPSAN


def spool_d(p: Params, i: int) -> float:
    return float(p.K_spool_hopsan[i] / (p.Cq * math.pi * X_VMAX * math.sqrt(2.0 / p.rho)))


def build_spec(p: Params, stop_s: float = 5.0, ts: float = DP_HOPSAN) -> dict:
    comps: list[dict] = []
    conns: list[dict] = []

    def add(name, typename, **parameters):
        comps.append({"name": name, "typename": typename, "parameters": parameters})

    def con(a, b):
        conns.append({"from": a, "to": b})

    # --- supply ---
    add("TankP", "HydraulicTankC", p=abs_p(0.0))
    add("TankT", "HydraulicTankC", p=abs_p(p.p_T))
    add("Pump", "HydraulicFixedDisplacementPump", **{
        "D_p#Value": 30e-6, "n_p#Value": 2 * math.pi * p.Q_pump_th * 0.95 / 30e-6, "C_lp#Value": 0.0})
    add("Gallery", "HydraulicVolumeMultiPort", **{"V#Value": p.V_g, "Beta_e#Value": p.beta,
                                                  "P1#Pressure": abs_p(100e5)})
    add("Unloader", "HydraulicPressureControlledValve", **{
        "p_ref#Value": p.dp_unl, "p_h#Value": 0.0, "tao": TAO_VALVE, "k_cs": p.unl_k_cs, "k_cf": p.unl_k_cf,
        "q_nom": p.unl_q_nom, "p_nom": 7.0e6})
    add("LSsource", "HydraulicPressureSourceC", **{"p#Value": abs_p(p.p_T)})
    con("TankP#P1", "Pump#P1")
    con("Pump#P2", "Gallery#P1")
    con("Unloader#P1", "Gallery#P1")
    con("Unloader#P2", "TankT#P1")
    con("Unloader#P_OPEN", "Gallery#P1")
    con("Unloader#P_CLOSE", "LSsource#P1")
    # ideal LS: max of the gated head pressures and the tank, clamped by the LS relief
    add("LSfloor", "SignalConstant", **{"y#Value": abs_p(p.p_T)})
    add("LSrelief", "SignalConstant", **{"y#Value": abs_p(p.p_relief)})
    add("LSmax", "SignalMax")
    con("LSfloor#y", "LSmax#in")
    for leg in LEGS:
        con(f"LSgated{leg}#out", "LSmax#in")
    add("LSmin", "SignalMin")
    con("LSmax#out", "LSmin#in")
    con("LSrelief#y", "LSmin#in")
    con("LSmin#out", "LSsource#p")

    # --- rigid body ---
    # each body axis is one Q-type mass (m, I_roll, I_pitch): signal integrators would
    # close an algebraic loop through dF; a force on P2 > 0 pushes P2 to negative, hence Neg.
    for ax, inertia in (("Z", p.mass), ("R", p.I_roll), ("P", p.I_pitch)):
        add(f"Sum{ax}", "SignalSum")
        add(f"Neg{ax}", "SignalGain", **{"k#Value": -1.0})
        add(f"FBody{ax}", "MechanicForceTransformer", **{"F#Value": 0.0})
        add(f"FFree{ax}", "MechanicForceTransformer", **{"F#Value": 0.0})
        add(f"Body{ax}", "MechanicTranslationalMass", **{"m": float(inertia), "B#Value": 0.0, "k#Value": 0.0})
        add(f"Pos{ax}", "MechanicPositionSensor")
        add(f"Vel{ax}", "MechanicSpeedSensor")
        con(f"Sum{ax}#out", f"Neg{ax}#in")
        con(f"Neg{ax}#out", f"FBody{ax}#F")
        con(f"FFree{ax}#P1", f"Body{ax}#P1")
        con(f"Body{ax}#P2", f"FBody{ax}#P1")
        con(f"Pos{ax}#P1", f"Body{ax}#P2")
        con(f"Vel{ax}#P1", f"Body{ax}#P2")

    # --- legs ---
    for i, leg in enumerate(LEGS):
        A_h, A_r = float(p.A_h[i]), float(p.A_r[i])
        add(f"Comp{leg}", "HydraulicPressureCompensatingValve", **{
            "p_ref#Value": p.dp_comp, "p_h#Value": 0.0, "tao": TAO_VALVE, "k_cs": p.comp_k_cs, "k_cf": p.comp_k_cf,
            "q_nom": p.comp_q_nom})
        add(f"Vmid{leg}", "HydraulicVolumeMultiPort", **{"V#Value": V_MID, "Beta_e#Value": p.beta,
                                                         "P1#Pressure": abs_p(100e5)})
        add(f"Spool{leg}", "Hydraulic43Valve", **{
            "C_q#Value": p.Cq, "rho#Value": p.rho, "d#Value": spool_d(p, i), "f_pa#Value": 1.0, "f_pb#Value": 1.0,
            "f_at#Value": p.bt_ratio, "f_bt#Value": p.bt_ratio, "x_pa#Value": 0.0, "x_pb#Value": 0.0,
            "x_at#Value": 0.0, "x_bt#Value": 0.0, "x_vmax#Value": X_VMAX, "omega_h": SPOOL_OMEGA, "delta_h": 1.0})
        add(f"Cyl{leg}", "HydraulicCylinderC", **{
            "A_1#Value": A_h, "A_2#Value": A_r, "s_l#Value": p.stroke,
            "V_1#Value": A_h * p.L0h + p.V_hose, "V_2#Value": A_r * p.L0r + p.V_hose,
            "B_p#Value": 0.0, "Beta_e#Value": p.beta, "c_leak#Value": 0.0, "use_sl": False,
            "P1#Pressure": abs_p(90e5), "P2#Pressure": abs_p(p.p_T), "P3#Position": -float(p.s0[i])})
        add(f"Mass{leg}", "MechanicTranslationalMass", **{"m": float(p.m_rod[i]), "B#Value": 0.0, "k#Value": 0.0})
        add(f"Load{leg}", "MechanicForceTransformer", **{"F#Value": 0.0, "P1#Position": float(p.s0[i])})
        add(f"Cmd{leg}", "SignalRamp", **{"y_0#Value": 0.0, "y_A#Value": X_VMAX, "t_start#Value": 0.0,
                                          "t_end#Value": p.ramp})
        add(f"Gate{leg}", "SignalConstant", **{"y#Value": 1.0})
        add(f"PSens{leg}", "HydraulicPressureSensor")
        add(f"LSgated{leg}", "SignalMultiply")
        add(f"SPos{leg}", "MechanicPositionSensor")
        add(f"SVel{leg}", "MechanicSpeedSensor")
        add(f"TankT{leg}", "HydraulicTankC", p=abs_p(p.p_T))

        con(f"Comp{leg}#P1", "Gallery#P1")
        con(f"Comp{leg}#P2", f"Vmid{leg}#P1")
        con(f"Comp{leg}#P_OPEN", f"Vmid{leg}#P1")
        con(f"Comp{leg}#P_CLOSE", f"Cyl{leg}#P1")
        con(f"Spool{leg}#PP", f"Vmid{leg}#P1")
        con(f"Spool{leg}#PT", f"TankT{leg}#P1")
        con(f"Spool{leg}#PA", f"Cyl{leg}#P1")
        con(f"Spool{leg}#PB", f"Cyl{leg}#P2")
        con(f"Cmd{leg}#out", f"Spool{leg}#in")
        con(f"Cyl{leg}#P3", f"Mass{leg}#P1")
        con(f"Mass{leg}#P2", f"Load{leg}#P1")
        con(f"PSens{leg}#P1", f"Spool{leg}#PA")  # read ports cannot join a multiport
        con(f"PSens{leg}#out", f"LSgated{leg}#in1")
        con(f"Gate{leg}#y", f"LSgated{leg}#in2")
        con(f"SPos{leg}#P1", f"Mass{leg}#P2")
        con(f"SVel{leg}#P1", f"Mass{leg}#P2")

        # leg kinematics: w = z + yp phi - xp theta, and the same for the rates
        for kind, src in (("W", "Pos"), ("DW", "Vel")):
            add(f"{kind}r{leg}", "SignalGain", **{"k#Value": float(p.yp[i])})
            add(f"{kind}p{leg}", "SignalGain", **{"k#Value": float(-p.xp[i])})
            add(f"{kind}Sum{leg}", "SignalSum")
            con(f"{src}R#out", f"{kind}r{leg}#in")
            con(f"{src}P#out", f"{kind}p{leg}#in")
            con(f"{src}Z#out", f"{kind}Sum{leg}#in")
            con(f"{kind}r{leg}#out", f"{kind}Sum{leg}#in")
            con(f"{kind}p{leg}#out", f"{kind}Sum{leg}#in")
        # dF = K (s - s0 - w) + c (v - dw); both gains 0 for prescribed loads
        add(f"S0{leg}", "SignalConstant", **{"y#Value": float(p.s0[i])})
        add(f"Comprn{leg}", "SignalSub")
        add(f"Rate{leg}", "SignalSubtract")
        add(f"K{leg}", "SignalGain", **{"k#Value": float(p.k_st[i])})
        add(f"C{leg}", "SignalGain", **{"k#Value": float(p.c_g[i])})
        add(f"dF{leg}", "SignalAdd")
        con(f"SPos{leg}#out", f"Comprn{leg}#insum")
        con(f"S0{leg}#y", f"Comprn{leg}#insub")
        con(f"WSum{leg}#out", f"Comprn{leg}#insub")
        con(f"SVel{leg}#out", f"Rate{leg}#in1")
        con(f"DWSum{leg}#out", f"Rate{leg}#in2")
        con(f"Comprn{leg}#out", f"K{leg}#in")
        con(f"Rate{leg}#out", f"C{leg}#in")
        con(f"K{leg}#out", f"dF{leg}#in1")
        con(f"C{leg}#out", f"dF{leg}#in2")
        # total load on the rod and the reaction on the body
        add(f"F0{leg}", "SignalConstant", **{"y#Value": 1.0e5})
        add(f"Ftot{leg}", "SignalAdd")
        con(f"F0{leg}#y", f"Ftot{leg}#in1")
        con(f"dF{leg}#out", f"Ftot{leg}#in2")
        con(f"Ftot{leg}#out", f"Load{leg}#F")
        add(f"Gr{leg}", "SignalGain", **{"k#Value": float(p.yp[i])})
        add(f"Gp{leg}", "SignalGain", **{"k#Value": float(-p.xp[i])})
        con(f"dF{leg}#out", f"Gr{leg}#in")
        con(f"dF{leg}#out", f"Gp{leg}#in")
        con(f"dF{leg}#out", "SumZ#in")
        con(f"Gr{leg}#out", "SumR#in")
        con(f"Gp{leg}#out", "SumP#in")

    return {
        "name": "coupled_four_leg",
        "simulation": {"start_s": 0.0, "timestep_s": ts, "stop_s": stop_s, "num_samples": 2001},
        "components": comps,
        "connections": conns,
    }


def scenario_overrides(p: Params, sc: Scenario) -> dict[str, object]:
    """Scenario values as Hopsan parameter overrides (absolute pressures)."""
    F0 = sc.loads(p)
    u = np.array(sc.u)
    active = u > 0
    p_h0 = (F0 + p.A_r * p.p_T) / p.A_h
    ls = max(p.p_T, float(p_h0[active].max()) if active.any() else p.p_T)
    p_P0 = min(ls, p.p_relief) + p.dp_unl
    out: dict[str, object] = {
        "Pump#n_p#Value": 2 * math.pi * p.Q_pump(sc.eta_v) / 30e-6,
        "Gallery#P1#Pressure": abs_p(p_P0),
        "LSsource#p#Value": abs_p(min(ls, p.p_relief)),
        "Unloader#p_ref#Value": p.dp_unl,
    }
    for i, leg in enumerate(LEGS):  # the spool sizing and the compensator set point follow dp_comp
        out[f"Comp{leg}#p_ref#Value"] = p.dp_comp
        out[f"Spool{leg}#d#Value"] = spool_d(p, i)
    for i, leg in enumerate(LEGS):
        rod_area_atm = (p.A_h[i] - p.A_r[i]) * P_ATM_HOPSAN
        hose = p.V_hose if active[i] else 0.0
        out.update({
            f"F0{leg}#y#Value": float(F0[i] + rod_area_atm),
            f"Cmd{leg}#y_A#Value": float(u[i] * X_VMAX),
            f"Cmd{leg}#t_end#Value": float(p.ramp * u[i]) if active[i] else 1.0,
            f"Gate{leg}#y#Value": 1.0 if active[i] else 0.0,
            f"Cyl{leg}#V_1#Value": float(p.A_h[i] * p.L0h + hose),
            f"Cyl{leg}#V_2#Value": float(p.A_r[i] * p.L0r + hose),
            f"Cyl{leg}#P1#Pressure": abs_p(float(p_h0[i])),
            f"Cyl{leg}#P2#Pressure": abs_p(p.p_T),
            f"Vmid{leg}#P1#Pressure": abs_p(p_P0),
            f"K{leg}#k#Value": float(p.k_st[i]) if sc.coupled else 0.0,
            f"C{leg}#k#Value": float(p.c_g[i]) if sc.coupled else 0.0,
        })
    return out


def log_vars() -> list[str]:
    names = ["Pump#P2#Pressure", "Pump#P2#Flow", "Unloader#P2#Flow", "BodyZ#P2#Position", "BodyR#P2#Position",
             "BodyP#P2#Position"]
    for leg in LEGS:
        names += [f"Mass{leg}#P2#Velocity", f"Mass{leg}#P2#Position", f"Spool{leg}#PA#Pressure",
                  f"Spool{leg}#PB#Pressure", f"Comp{leg}#P2#Flow", f"Spool{leg}#PB#Flow", f"Ftot{leg}#out",
                  f"Spool{leg}#PP#Pressure", f"Spool{leg}#PA#Flow"]
    return names


def main() -> None:
    p = load_params()
    out = HERE / "hopsan_spec.json"
    spec = build_spec(p)
    out.write_text(json.dumps(spec, indent=0), encoding="utf-8")
    print(f"{out}: {len(spec['components'])} components, {len(spec['connections'])} connections")


if __name__ == "__main__":
    main()
