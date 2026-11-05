"""Task 4: open-loop replay of the stored R12 commands on a four-leg Hopsan circuit with lines and pilot checks.

3-DOF body and k_st from coupled/build_hopsan_spec.py. Valve: lagged flow source + meter-out land + neutral vent, as the
single-leg bench. G4: ground under RR falls 11.5 mm in 2 s. Commands are the 10 Hz outputs saved by the harness, so the
controller does not react to this plant: a direction check, not a closed-loop result.
Circuits: nocheck (no lines, no checks, chambers sealed at u = 0), vent, vent_ref, lowcrack, block, block_db.
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np
from bench import AFFINITY_MASK, BETA_HOSE, CQ, P_CRACK, POC_KS, PSI, REAR_FS_SCALE, RHO, TAU_V, TS, V_LINE, load_params, pin
from build_hopsan_spec import build_spec
from common import P_ATM, Hmf, lag_series
from hopsan_run import run_hopsan

ROOT = Path(r"C:\workspace\outrigger_control")
OUT = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "pressure_review" / "m1_hopsan"
MAIN = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "pressure_review" / "m1" / "main.jsonl"
SER = HERE.parent / "ctrl_m1" / "series"
LEGS = ("FL", "FR", "RL", "RR")
REMOVE_PREFIX = ("TankP", "TankT", "Pump", "Gallery", "Unloader", "LSsource", "LSfloor", "LSrelief", "LSmax", "LSmin",
                 "Comp", "Vmid", "Spool", "Cmd", "Gate", "PSens", "LSgated")
C_LOCK = np.array([34403.5, 34403.5, 30348.5, 30348.5])
FS_FRONT = 4.0e3
SINK_M, SINK_S = 0.0115, 2.0
T_SETTLE = 0.5
T_AFTER = 6.0
P_T = 2.0e5
CIRCUITS = {
    "nocheck": dict(check=False),
    "vent": dict(check=True, neutral="vent"),
    "vent_ref": dict(check=True, neutral="vent", ref=True),
    "lowcrack": dict(check=True, neutral="vent", ref=True, crack_b=0.5e5),
    "block": dict(check=True, neutral="block"),
    "block_db": dict(check=True, neutral="block", deadband=True),
    "vent_V05": dict(check=True, neutral="vent", v_scale=0.5),
    "block_V05": dict(check=True, neutral="block", v_scale=0.5),
}


def load_row(variant: str, offset: float) -> dict:
    for line in MAIN.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        job = r["job"]
        if job["case"] == "R12" and job["variant"] == variant and job["offset_s"] == offset:
            return r
    raise KeyError((variant, offset))


def _removed(name: str) -> bool:
    return not name.startswith("Comprn") and any(name.startswith(x) for x in REMOVE_PREFIX)


def build(name: str, circuit: dict, variant: str, offset: float, p, folder: Path):
    row = load_row(variant, offset)
    state = row["state_at"]["ready"]
    F0 = np.array(state["F"]) * 1e3
    s0 = np.array(state["s"]) * 1e-3
    t_ready = row["values"]["times"]["t_first_ready_s"]
    d = np.load(SER / f"R12__{variant}_0.0_{offset}.npz", allow_pickle=True)
    t_cmd_h = d["t"] - (t_ready + 5.0 + offset) + T_SETTLE
    cmd_u = d["command"]
    t_end = T_SETTLE + T_AFTER
    grid = np.arange(0.0, t_end + 1e-9, 1.0e-3)
    idx = np.searchsorted(t_cmd_h, grid, side="right") - 1
    cmd = cmd_u[np.clip(idx, 0, len(cmd_u) - 1)]
    cmd[grid < t_cmd_h[0]] = 0.0
    u = np.column_stack([lag_series(grid, cmd[:, i], TAU_V) for i in range(4)])

    spec = build_spec(p.with_(V_hose=0.0), stop_s=t_end, ts=TS)
    h = Hmf(name, t_end, TS)
    h.comp("SignalTime", "Clock")
    for comp in spec["components"]:
        n = comp["name"]
        if _removed(n) or n in tuple(f"S0{x}" for x in ("RR",)):
            continue
        pars = dict(comp["parameters"])
        leg = n[-2:]
        if leg in LEGS:
            i = LEGS.index(leg)
            if n == f"Mass{leg}":
                fs = FS_FRONT * (1.0 if i < 2 else REAR_FS_SCALE)
                h.comp("MechanicTranslationalMassWithCoulombFriction", n, {"m": float(p.m_rod[i]), "b#Value": 0.0, "f_s#Value": fs, "f_k#Value": fs, "x_min#Value": -1e3, "x_max#Value": 1e3})
                continue
            if n == f"Cyl{leg}":
                continue  # added below
            if n == f"Load{leg}":
                pars["P1#Position"] = float(s0[i])
            if n == f"S0{leg}":
                pars["y#Value"] = float(s0[i])
            if n == f"K{leg}":
                pars["k#Value"] = float(p.k_st[i])
            if n == f"C{leg}":
                pars["k#Value"] = 0.0
            if n == f"F0{leg}":
                pars["y#Value"] = float(F0[i] + (p.A_h[i] - p.A_r[i]) * P_ATM)
        h.comp(comp["typename"], n, pars)
    for c in spec["connections"]:
        ca, pa = c["from"].split("#")
        cb, pb = c["to"].split("#")
        if _removed(ca) or _removed(cb) or ca.startswith("Cyl") and cb.startswith("Spool") or cb.startswith("Cyl") and ca.startswith("Spool"):
            continue
        if ca == "S0RR":
            continue
        if ca.startswith("dF"):
            ca = f"DClip{ca[-2:]}"
        h.connect(ca, pa, cb, pb)
    h.lookup(folder, "S0RR", np.array([0.0, T_SETTLE, T_SETTLE + SINK_S, t_end]),
             s0[3] + SINK_M * np.array([0.0, 0.0, 1.0, 1.0]), "ComprnRR", "insub")

    k_scale = circuit.get("v_scale", 1.0)
    v_line = V_LINE * k_scale
    for i, leg in enumerate(LEGS):
        A_h, A_r = float(p.A_h[i]), float(p.A_r[i])
        h.comp("SignalConstant", f"DMin{leg}", {"y#Value": -float(F0[i]) - float(p.m_rod[i]) * 9.80665})
        h.comp("SignalMax", f"DClip{leg}")
        h.connect(f"dF{leg}", "out", f"DClip{leg}", "in")
        h.connect(f"DMin{leg}", "y", f"DClip{leg}", "in")
        p_r_abs = P_ATM + P_T
        F_h = F0[i] + (A_h - A_r) * P_ATM
        p_h_abs = (F_h + A_r * p_r_abs) / A_h
        h.comp("HydraulicCylinderC", f"Cyl{leg}", {
            "P1#Pressure": p_h_abs, "P1#WaveVariable": p_h_abs, "P2#Pressure": p_r_abs, "P2#WaveVariable": p_r_abs,
            "P3#Position": -float(s0[i]), "P3#Force": F_h, "P3#WaveVariable": F_h,
            "A_1#Value": A_h, "A_2#Value": A_r, "s_l#Value": p.stroke, "V_1#Value": A_h * p.L0h, "V_2#Value": A_r * p.L0r,
            "B_p#Value": float(C_LOCK[i]), "Beta_e#Value": p.beta, "c_leak#Value": 0.0, "use_sl": False})
        a_full = A_h * p.v_max / np.sqrt(p.dp_comp) / (CQ * np.sqrt(2.0 / RHO))
        frac = np.abs(u[:, i]) / p.v_max
        tank = f"Tank{leg}"
        h.comp("HydraulicTankC", tank + "A", {"p": P_ATM + P_T})
        h.comp("HydraulicTankC", tank + "B", {"p": P_ATM + P_T})
        for q, orf, chamber_port, port_tank in (("QA", "OA", "P1", tank + "A"), ("QB", "OB", "P2", tank + "B")):
            h.comp("HydraulicFlowSourceQ", q + leg, {"q#Value": 0.0})
            h.comp("HydraulicTurbulentOrifice", orf + leg, {"A#Value": 0.0, "C_q#Value": CQ, "rho#Value": RHO})
            h.connect(orf + leg, "P2", port_tank, "P1")
            if not circuit["check"]:
                h.connect(q + leg, "P1", f"Cyl{leg}", chamber_port)
                h.connect(orf + leg, "P1", f"Cyl{leg}", chamber_port)
        if not circuit["check"]:
            h.comp("HydraulicPressureSensor", f"SH{leg}")
            h.comp("HydraulicPressureSensor", f"SR{leg}")
            h.connect(f"SH{leg}", "P1", f"QA{leg}", "P1")
            h.connect(f"SR{leg}", "P1", f"QB{leg}", "P1")
            qa = A_h * np.maximum(u[:, i], 0.0)
            qb = A_r * np.maximum(-u[:, i], 0.0)
            oa = a_full * frac * (u[:, i] < 0)
            ob = a_full * frac * (u[:, i] > 0)
        else:
            neutral = circuit["neutral"]
            line_a0 = P_ATM + P_T if neutral == "vent" else p_h_abs + P_CRACK
            h.comp("HydraulicVolumeMultiPort", f"LineA{leg}", {"V#Value": v_line, "Beta_e#Value": BETA_HOSE, "P1#Pressure": line_a0})
            h.comp("HydraulicVolumeMultiPort", f"LineB{leg}", {"V#Value": v_line, "Beta_e#Value": BETA_HOSE, "P1#Pressure": P_ATM + P_T})
            h.connect(f"QA{leg}", "P1", f"LineA{leg}", "P1")
            h.connect(f"QB{leg}", "P1", f"LineB{leg}", "P1")
            h.connect(f"OA{leg}", "P1", f"LineA{leg}", "P1")
            h.connect(f"OB{leg}", "P1", f"LineB{leg}", "P1")
            a_check = POC_KS / (CQ * np.sqrt(2.0 / RHO))
            crack_b = circuit.get("crack_b", P_CRACK)
            shift_b = PSI * P_T if circuit.get("ref") else 0.0
            for base, line, port, pilot_orf, crack, shift in (("POCA", "LineA", "P1", "OB", P_CRACK, 0.0), ("POCB", "LineB", "P2", "OA", crack_b, shift_b)):
                n = base + leg
                pf = crack + shift + P_ATM * PSI
                h.comp("HydraulicTurbulentOrifice", n, {"A#Value": 0.0, "C_q#Value": CQ, "rho#Value": RHO})
                h.connect(n, "P1", line + leg, "P1")
                h.connect(n, "P2", f"Cyl{leg}", port)
                for sensor in ("SL", "SP", "SC"):
                    h.comp("HydraulicPressureSensor", f"{sensor}{n}")
                h.comp("SignalGain", f"GP{n}", {"k#Value": PSI})
                h.comp("SignalSub", f"D{n}")
                h.comp("SignalConstant", f"Pf{n}", {"y#Value": pf})
                h.comp("SignalGreaterThan", f"GT{n}", {"x_limit#Value": 0.0})
                h.comp("SignalGain", f"AG{n}", {"k#Value": a_check})
                h.connect(f"SL{n}", "P1", n, "P1")
                h.connect(f"SC{n}", "P1", n, "P2")
                h.connect(f"SP{n}", "P1", pilot_orf + leg, "P1")
                h.connect(f"SP{n}", "out", f"GP{n}", "in")
                h.connect(f"SL{n}", "out", f"D{n}", "insum")
                h.connect(f"GP{n}", "out", f"D{n}", "insum")
                h.connect(f"SC{n}", "out", f"D{n}", "insub")
                h.connect(f"Pf{n}", "y", f"D{n}", "insub")
                h.connect(f"D{n}", "out", f"GT{n}", "in")
                h.connect(f"GT{n}", "out", f"AG{n}", "in")
                h.connect(f"AG{n}", "out", n, "A")
            gate = (frac >= 0.02) if circuit.get("deadband") else np.ones_like(frac, bool)
            qa = A_h * np.maximum(u[:, i], 0.0) * gate
            qb = A_r * np.maximum(-u[:, i], 0.0) * gate
            a_neutral = 0.05 * a_full if neutral == "vent" else 0.0
            vent = a_neutral * np.clip(1.0 - frac / 0.02, 0.0, 1.0)
            oa = vent + a_full * frac * (u[:, i] < 0)
            ob = vent + a_full * frac * (u[:, i] > 0)
        h.lookup(folder, f"LUqa{leg}", grid, qa, f"QA{leg}", "q")
        h.lookup(folder, f"LUqb{leg}", grid, qb, f"QB{leg}", "q")
        h.lookup(folder, f"LUoa{leg}", grid, oa, f"OA{leg}", "A")
        h.lookup(folder, f"LUob{leg}", grid, ob, f"OB{leg}", "A")
    n_log = int(t_end / 5e-4) + 1
    model = h.write(folder / f"{name}.hmf", n_log=n_log)
    log = []
    for leg in LEGS:
        log += [f"Ftot{leg}#out", f"Mass{leg}#P2#Position"]
        if circuit["check"]:
            log += [f"POCA{leg}#P2#Pressure", f"POCB{leg}#P2#Pressure", f"POCB{leg}#P1#Pressure", f"POCA{leg}#P1#Pressure", f"GTPOCA{leg}#out", f"GTPOCB{leg}#out"]
        else:
            log += [f"QA{leg}#P1#Pressure", f"QB{leg}#P1#Pressure"]
    return model, t_end, n_log, log, grid, u, F0


def run_one(job, p, work):
    name, circuit_name, variant, offset = job
    circuit = CIRCUITS[circuit_name]
    folder = work / name
    model, t_end, n_log, log, grid, u, F0 = build(name, circuit, variant, offset, p, folder)
    df, _un, info = run_hopsan(model, folder, sim=(0.0, TS, t_end), log_only=log, num_log_samples=n_log, timeout=500.0)
    t = df.index.to_numpy()
    out = {"name": name, "circuit": circuit_name, "commands": variant, "offset": offset, "wall_s": info["wall_s"]}
    F = np.zeros((len(t), 4))
    Fo = np.zeros((len(t), 4))
    ph = np.zeros((len(t), 4))
    pr = np.zeros((len(t), 4))
    for i, leg in enumerate(LEGS):
        A_h, A_r = float(p.A_h[i]), float(p.A_r[i])
        F[:, i] = df[f"Ftot{leg}#out#Value"].to_numpy() - (A_h - A_r) * P_ATM
        if circuit["check"]:
            ph[:, i] = df[f"POCA{leg}#P2#Pressure"].to_numpy() - P_ATM
            pr[:, i] = df[f"POCB{leg}#P2#Pressure"].to_numpy() - P_ATM
        else:
            ph[:, i] = df[f"QA{leg}#P1#Pressure"].to_numpy() - P_ATM
            pr[:, i] = df[f"QB{leg}#P1#Pressure"].to_numpy() - P_ATM
        Fo[:, i] = A_h * ph[:, i] - A_r * pr[:, i]
    w = t >= T_SETTLE
    dt = t[1] - t[0]
    n_avg = int(0.25 / dt)
    kernel = np.ones(n_avg) / n_avg
    avg = np.column_stack([np.convolve(F[:, i], kernel, mode="same") for i in range(4)])
    out["F_min_kN"] = {leg: float(F[w, i].min() / 1e3) for i, leg in enumerate(LEGS)}
    out["F_min_t_s"] = {leg: float(t[w][np.argmin(F[w, i])] - T_SETTLE) for i, leg in enumerate(LEGS)}
    out["Foil_min_kN"] = {leg: float(Fo[w, i].min() / 1e3) for i, leg in enumerate(LEGS)}
    out["F_avg025_min_kN"] = {leg: float(avg[(t >= T_SETTLE) & (t <= t[-1] - 0.2), i].min() / 1e3) for i, leg in enumerate(LEGS)}
    pre = (t > T_SETTLE - 0.1) & (t < T_SETTLE)
    out["F_pre_kN"] = {leg: float(F[pre, i].mean() / 1e3) for i, leg in enumerate(LEGS)}
    if circuit["check"]:
        first = {}
        for i, leg in enumerate(LEGS):
            a = df[f"GTPOCA{leg}#out#Value"].to_numpy() > 0.5
            k = np.flatnonzero((t > T_SETTLE + 0.5) & a)  # block: the trapped line A passes for an instant at the start
            first[leg] = float(t[k[0]] - T_SETTLE) if k.size else None
        out["t_first_head_check_open_s"] = first
        rod = {}
        for i, leg in enumerate(LEGS):
            b = df[f"GTPOCB{leg}#out#Value"].to_numpy() > 0.5
            closed = np.flatnonzero((t > T_SETTLE) & ~b)
            if closed.size:
                reopen = np.flatnonzero((t > t[closed[0]]) & b)
                rod[leg] = {"first_closed_s": float(t[closed[0]] - T_SETTLE), "reopen_s": float(t[reopen[0]] - T_SETTLE) if reopen.size else None}
            else:
                rod[leg] = {"first_closed_s": None, "reopen_s": None}
        out["rod_check"] = rod
    # stored samples at the event for the comparison with the fill log
    sample = {}
    for rel in (1.0, 1.4, 1.8, 2.0, 2.5):
        j = int(np.argmin(np.abs(t - T_SETTLE - rel)))
        sample[f"+{rel:g}"] = {"F": np.round(F[j] / 1e3, 1).tolist(), "p_h": np.round(ph[j] / 1e5, 1).tolist(), "p_r": np.round(pr[j] / 1e5, 1).tolist()}
    out["samples"] = sample
    np.savez_compressed(work / f"{name}.npz", t=t[::5] - T_SETTLE, F=F[::5], ph=ph[::5], pr=pr[::5], Fo=Fo[::5])
    return out


def main(argv):
    pin()
    p = load_params()
    work = HERE / "t4"
    work.mkdir(parents=True, exist_ok=True)
    quick = "--quick" in argv
    if quick:
        jobs = [("q_nocheck_OFF", "nocheck", "OFF", 0.025), ("q_vent_V1", "vent", "V1", 0.025)]
    elif "--conv" in argv:  # step convergence, half and quarter step
        import t4_replay as self_module  # noqa: F401
        global TS
        TS = float(argv[argv.index("--conv") + 1])
        jobs = [(f"conv{TS:g}_{c}_{v}", c, v, 0.025) for c, v in (("vent", "V1"), ("vent_ref", "V1"), ("block", "B1"))]
    else:
        jobs = []
        for off in (0.0, 0.025, 0.05, 0.075):
            for circuit, variant in (("nocheck", "OFF"), ("nocheck", "V1"), ("nocheck", "B1"), ("vent", "V1"), ("vent", "OFF"), ("vent_ref", "V1"), ("lowcrack", "V1"),
                                     ("block", "B1"), ("block", "OFF"), ("block_db", "B1"), ("vent_V05", "V05"), ("block_V05", "B05")):
                jobs.append((f"{circuit}_{variant}_{off:g}", circuit, variant, off))
    print("jobs", len(jobs), flush=True)
    with ThreadPoolExecutor(4) as pool:
        rows = list(pool.map(lambda j: run_one(j, p, work), jobs))
    out_name = "t4_quick.json" if quick else (f"t4_conv_{TS:g}.json" if "--conv" in argv else "t4_replay.json")
    (OUT / out_name).write_text(json.dumps(rows, indent=0), encoding="utf-8")
    for r in rows:
        print(r["name"], "wall", r["wall_s"], "RR Fmin", round(r["F_min_kN"]["RR"], 2), "t", round(r["F_min_t_s"]["RR"], 2), "oil", round(r["Foil_min_kN"]["RR"], 2), "avg", round(r["F_avg025_min_kN"]["RR"], 2), "pre", r["F_pre_kN"]["RR"], r.get("t_first_head_check_open_s"), flush=True)
        for key, s in r["samples"].items():
            if key in ("+1.8", "+2"):
                print("   ", key, s, flush=True)


if __name__ == "__main__":
    main(sys.argv)
