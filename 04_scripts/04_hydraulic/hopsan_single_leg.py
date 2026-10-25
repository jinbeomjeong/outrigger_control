"""Hopsan 2.24.4 models of the single-leg bench (independent reference, spec 6).

Builds one hand-written .hmf per scenario (flipped topology: HydraulicCylinderC has its barrel fixed
to the inertial frame, so the bench is barrel -- cylinder -- rod m_r -- spring k_g -- M), runs
hopsancli through the hydraulics-expert helper hopsan_run.py and converts the results to the record
format of single_leg.run (s, p_A_g, p_B_g, F_g, xM, ...). Same parameters and breakpoints as the
Python spec implementation (l2_params.build, scenarios.make). Basis: the pinned history YAML of
l2_params (REXOME33 old common dimensions 115/110 mm, D7 2026-10-25), not the current per-leg YAML.

Hopsan conventions handled here (measured 2026-10-20, Hopsan 2.24.4):
  * pressures are ABSOLUTE (tank 1e5 Pa); the cylinder force is A1 p1 - A2 p2 (no atmosphere term),
    so the Python side runs with p_force_ref = 0 for these comparisons
  * pressure-valve set points and pilot pressures are absolute: p_ref is shifted by p_atm (1 + ratio)
  * cylinder P3 position = -s (negative when extended)

Models are written to 04_scripts/04_hydraulic/hopsan_models/<scenario>/ (with their lookup CSVs);
hopsancli runs in a scratch copy (work_dir argument).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:\Users\jinbeom\.claude\tools\hydraulics")

import l2_params as lp  # noqa: E402
import scenarios as sc  # noqa: E402
from hopsan_run import run_hopsan  # noqa: E402

MODEL_DIR = HERE / "hopsan_models"
P_ATM = 1.0e5
RHO = 860.0


class Hmf:
    def __init__(self, name: str, t_end: float, ts: float):
        self.name, self.t_end, self.ts = name, t_end, ts
        self.objs: list[str] = []
        self.conns: list[tuple[str, str, str, str]] = []

    def comp(self, typename: str, name: str, params: dict) -> None:
        lines = [f'      <component typename="{typename}" name="{name}">', "        <parameters>"]
        for k, v in params.items():
            if isinstance(v, bool):
                val, typ = ("true" if v else "false"), "bool"
            elif isinstance(v, int):
                val, typ = str(v), "integer"
            elif isinstance(v, str):
                val, typ = v, "string"
            else:
                val, typ = repr(float(v)), "double"
            lines.append(f"          <parameter name={quoteattr(k)} value={quoteattr(val)} type=\"{typ}\"/>")
        lines += ["        </parameters>", "      </component>"]
        self.objs.append("\n".join(lines))

    def connect(self, c1: str, p1: str, c2: str, p2: str) -> None:
        self.conns.append((c1, p1, c2, p2))

    def xml(self, n_log: int) -> str:
        con = "\n".join(f'      <connect startcomponent="{a}" startport="{b}" endcomponent="{c}" endport="{d}"/>'
                        for a, b, c, d in self.conns)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<hopsanmodelfile hmfversion="0.4" hopsanguiversion="0.7.x" hopsancoreversion="2.24.4">\n'
            "  <requirements>\n    <componentlibrary>HopsanDefaultComponentLibrary</componentlibrary>\n"
            "  </requirements>\n"
            f'  <system typename="Subsystem" name="{self.name}">\n'
            f'    <simulationtime stop="{self.t_end}" timestep="{self.ts}" start="0" inherit_timestep="true"/>\n'
            f'    <simulationlogsettings numsamples="{n_log}" starttime="0"/>\n'
            "    <parameters/>\n    <aliases/>\n    <objects>\n"
            + "\n".join(self.objs)
            + "\n    </objects>\n    <connections>\n" + con + "\n    </connections>\n  </system>\n"
            "</hopsanmodelfile>\n"
        )


def _lookup(h: Hmf, folder: Path, name: str, sig: list, target: str, port: str, scale: float = 1.0,
            offset: float = 0.0) -> None:
    """Piecewise-linear signal from a CSV lookup driven by SignalTime."""
    csv = folder / f"{name}.csv"
    pts = [(t, v * scale + offset) for t, v in sig]
    csv.write_text("\n".join(f"{t:.9g},{v:.12g}" for t, v in pts) + "\n", encoding="ascii")
    h.comp("Signal1DLookupTable", name, {"in#Value": 0.0, "filename": csv.name, "csvsep": ",",
                                         "inid": 0, "outid": 1, "reload": True})
    h.connect("Clock", "out", name, "in")
    h.connect(name, "out", target, port)


def build_model(name: str, ts: float = 1.0e-5, F_s: float | None = None, beta: float = 1.0e9) -> tuple[Path, dict]:
    """Write the .hmf (+ CSVs) of scenario `name`; return (path, info)."""
    _, c0 = lp.build()
    sch, t_end, o = sc.make(name, c0)
    F_s = o["F_s"] if F_s is None else F_s
    prm, c = lp.build(beta=beta, F_s=F_s, with_relief=o["with_relief"], with_cb=o["with_cb"],
                      hopsan_force_convention=True)
    g = prm.geometry
    folder = MODEL_DIR / name
    folder.mkdir(parents=True, exist_ok=True)
    h = Hmf(f"leg_{name}", t_end, ts)

    M = o["M"] or c["M_eq"]
    F_pre = o["F_preload"] if o["F_preload"] is not None else c["M_eq"] * c["g"]
    F0 = F_pre
    s0 = c["s0"]
    pB0 = P_ATM + c["p_rod0_g"]
    pA0 = (F0 + pB0 * g.area_rod_side_m2) / g.area_head_m2          # Hopsan force convention
    moving_any = any(v > 0.5 for _, v in sch.moving)

    # start values live on the C-type components (cylinder, spring, force source); Q masses read them
    h.comp("SignalTime", "Clock", {})
    h.comp("HydraulicCylinderC", "Cyl", {
        "P1#Pressure": pA0, "P1#WaveVariable": pA0, "P2#Pressure": pB0, "P2#WaveVariable": pB0,
        "P3#Position": -s0, "P3#Force": F0, "P3#WaveVariable": F0,
        "A_1#Value": g.area_head_m2, "A_2#Value": g.area_rod_side_m2, "s_l#Value": g.stroke_m,
        "V_1#Value": g.dead_volume_head_m3, "V_2#Value": g.dead_volume_rod_m3,
        "B_p#Value": prm.c_h_locked_N_s_m, "Beta_e#Value": beta, "c_leak#Value": 0.0, "use_sl": True})
    if F_s > 0.0:
        h.comp("MechanicTranslationalMassWithCoulombFriction", "Rod", {
            "m": c["m_r"], "b#Value": 0.0, "f_s#Value": F_s, "f_k#Value": F_s,
            "x_min#Value": -1e3, "x_max#Value": 1e3})
    else:
        h.comp("MechanicTranslationalMass", "Rod", {
            "m": c["m_r"], "B#Value": 0.0, "k#Value": 0.0, "x_min#Value": -1e3, "x_max#Value": 1e3})
    h.comp("MechanicTranslationalSpring", "Kg", {
        "k#Value": c["k_g"], "P1#Force": F0, "P2#Force": F0, "P1#Position": s0, "P2#Position": 0.0,
        "P1#WaveVariable": F0, "P2#WaveVariable": F0})
    h.comp("MechanicTranslationalMass", "Sup", {
        "m": M, "B#Value": 0.0, "k#Value": 0.0, "x_min#Value": -1e3, "x_max#Value": 1e3})
    h.comp("MechanicForceTransformer", "Load", {"F#Value": F0, "P1#Force": F0, "P1#Position": 0.0})
    h.connect("Cyl", "P3", "Rod", "P1")
    h.connect("Rod", "P2", "Kg", "P1")
    h.connect("Kg", "P2", "Sup", "P1")
    h.connect("Sup", "P2", "Load", "P1")
    _lookup(h, folder, "LU_F", sch.D2_N, "Load", "F", offset=F_pre)

    if moving_any:
        h.comp("HydraulicFlowSourceQ", "QA", {"q#Value": 0.0})
        h.connect("QA", "P1", "Cyl", "P1")
        _lookup(h, folder, "LU_q", sch.q_head, "QA", "q")
        # moving damping switch on B_p
        _lookup(h, folder, "LU_Bp", [(t, prm.c_h_locked_N_s_m + v * (prm.c_h_moving_N_s_m - prm.c_h_locked_N_s_m))
                                     for t, v in sch.moving], "Cyl", "B_p")
        if prm.relief is not None:
            rv = prm.relief
            h.comp("HydraulicPressureReliefValve", "PRV", {
                "p_max#Value": rv.p_set_gauge_Pa + P_ATM, "tao#Value": rv.tau_s, "p_h#Value": rv.hysteresis_Pa,
                "k_cs": rv.k_cs, "k_cf": rv.k_cf, "q_nom": rv.q_nom_m3_s})
            h.comp("HydraulicTankC", "TankR", {"p": P_ATM})
            h.connect("PRV", "P1", "Cyl", "P1")
            h.connect("PRV", "P2", "TankR", "P1")
        d, f, cq = 0.002, 0.5, 0.67
        xvmax = c["rod_valve_Ks"] / (cq * f * math.pi * d * math.sqrt(2.0 / RHO))
        h.comp("Hydraulic22Valve", "VB", {"in#Value": 0.0, "C_q#Value": cq, "rho#Value": RHO, "d#Value": d,
                                         "f#Value": f, "x_vmax#Value": xvmax, "omega_h": 2000.0, "delta_h": 1.0})
        h.comp("HydraulicPressureSourceC", "PsB", {"p#Value": P_ATM})
        h.connect("VB", "PP", "Cyl", "P2")
        h.connect("VB", "PA", "PsB", "P1")
        _lookup(h, folder, "LU_open", sch.rod_open, "VB", "in", scale=xvmax)
        _lookup(h, folder, "LU_pline", sch.p_rod_line_g, "PsB", "p", offset=P_ATM)
    else:
        h.comp("HydraulicPlugQ", "PlugA", {})
        h.comp("HydraulicPlugQ", "PlugB", {})
        h.connect("PlugA", "P1", "Cyl", "P1")
        h.connect("PlugB", "P1", "Cyl", "P2")
        if prm.counterbalance is not None:
            cb = prm.counterbalance
            h.comp("HydraulicOverCenterValve", "CB", {
                "p_ref#Value": cb.p_set_gauge_Pa + P_ATM * (1.0 + cb.pilot_ratio),
                "p_h#Value": cb.hysteresis_Pa, "a_ratio#Value": cb.pilot_ratio,
                "tao": cb.tau_s, "k_cs": cb.k_cs, "k_cf": cb.k_cf, "q_nom": cb.q_nom_m3_s, "p_nom": cb.p_nom_Pa})
            h.comp("HydraulicTankC", "TankCB", {"p": P_ATM})
            h.comp("HydraulicTankC", "TankPilot", {"p": P_ATM})
            h.connect("CB", "P1", "Cyl", "P1")
            h.connect("CB", "P2", "TankCB", "P1")
            h.connect("CB", "P_CONTROL", "TankPilot", "P1")

    n_log = int(round(t_end / 1.0e-4)) + 1
    path = folder / (f"leg_{name}.hmf" if ts == 1.0e-5 else f"leg_{name}_ts{ts:g}.hmf")
    path.write_text(h.xml(n_log), encoding="utf-8")
    info = {"hmf": str(path), "ts": ts, "t_end": t_end, "n_log": n_log, "F_s": F_s, "beta": beta,
            "moving": moving_any, "p_A0_abs": pA0, "p_B0_abs": pB0, "M": M, "F_preload": F_pre}
    return path, info


def run_model(name: str, work_root: Path, ts: float = 1.0e-5, F_s: float | None = None,
              beta: float = 1.0e9, tag: str = "") -> dict:
    """Build, run and convert one scenario. Returns the single_leg-style record + info."""
    path, info = build_model(name, ts=ts, F_s=F_s, beta=beta)
    work = work_root / f"{name}{tag}"
    # lookup CSVs must sit next to the model copy
    work.mkdir(parents=True, exist_ok=True)
    for f in path.parent.glob("*.csv"):
        (work / f.name).write_bytes(f.read_bytes())
    df, units, run_info = run_hopsan(path, work, sim="hmf", num_log_samples=info["n_log"], timeout=600)
    t = df.index.to_numpy()
    s = -df["Cyl#P3#Position"].to_numpy()
    if info["moving"]:
        pA = df["QA#P1#Pressure"].to_numpy()
        pB = df["VB#PP#Pressure"].to_numpy()
    else:
        pA = df["PlugA#P1#Pressure"].to_numpy()
        pB = df["PlugB#P1#Pressure"].to_numpy()
    rec = {
        "t": t, "s": s, "v": -df["Cyl#P3#Velocity"].to_numpy(),
        "p_A_g": pA - P_ATM, "p_B_g": pB - P_ATM,
        "F_g": df["Kg#P1#Force"].to_numpy(),
        "xM_raw": df["Sup#P2#Position"].to_numpy(),
        "vM_raw": df["Sup#P2#Velocity"].to_numpy(),
    }
    if "PRV#P1#Flow" in df:
        rec["q_relief"] = -df["PRV#P1#Flow"].to_numpy()
    if "CB#P1#Flow" in df:
        rec["q_cb"] = -df["CB#P1#Flow"].to_numpy()
    if "VB#PP#Flow" in df:
        rec["q_rod"] = df["VB#PP#Flow"].to_numpy()
    rec = {k: np.asarray(v) for k, v in rec.items()}
    rec["info"] = {**info, **{k: run_info[k] for k in ("cmd", "cwd", "csv", "wall_s")}}
    return rec


if __name__ == "__main__":
    import json

    work = Path(sys.argv[1])
    for nm in sys.argv[2:] or sc.ALL:
        r = run_model(nm, work)
        print(nm, json.dumps({k: (float(v[-1]) if isinstance(v, np.ndarray) else None) for k, v in r.items()
                              if k != "info"}), r["info"]["wall_s"])
