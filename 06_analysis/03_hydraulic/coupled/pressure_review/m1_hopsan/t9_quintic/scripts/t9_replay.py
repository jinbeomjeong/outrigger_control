"""R12 open-loop replay with the harness quintic sink: t4_replay.py with three changes.

1. S0RR follows D tau^3 (10 - 15 tau + 6 tau^2), D 11.5 mm, tau = t / 2 s (harness r67 branch).
2. Initial leg loads = the harness series at t = 0 of the same variant and phase.
3. The event time of the stored 10 Hz commands is fitted to the harness 1 ms valve series (no rounding of READY + 5 s).
Usage: t9_replay.py [--first] (--first = no-check OFF on four phases only). Pressures bar gauge on output.
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np
import t4_replay as t4
from bench import load_params, pin
from common import P_ATM

ROOT = Path(r"C:\workspace\outrigger_control")
BASE = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "pressure_review"
OUT = BASE / "m1_hopsan" / "t9_quintic"
SERIES = BASE / "m1b" / "series_r12"
LEGS = t4.LEGS
OFFSETS = (0.0, 0.025, 0.05, 0.075)
HARNESS_OFF = {0.0: 13.75, 0.025: 12.01, 0.05: 12.17, 0.075: 12.98}


def quintic_mm(t):
    tau = np.clip(t / 2.0, 0.0, 1.0)
    return 11.5 * tau**3 * (10.0 - 15.0 * tau + 6.0 * tau**2)


def event_fit(variant: str, offset: float) -> dict:
    """Time of the sink start on the stored 10 Hz command clock, and the harness state at t = 0."""
    h = np.load(SERIES / f"R12_{variant}_{offset}.npz")
    d = np.load(t4.SER / f"R12__{variant}_0.0_{offset}.npz", allow_pickle=True)
    row = t4.load_row(variant, offset)
    t_guess = row["values"]["times"]["t_first_ready_s"] + 5.0 + offset
    best = (None, np.inf)
    th = h["t"]
    keep = (th > 0.5) & (th < 4.0)
    clock = np.arange(-1.0, 4.5, 1e-3)
    rel = d["t"] - t_guess
    idx = np.searchsorted(rel, clock, side="right") - 1
    cmd = d["command"][np.clip(idx, 0, len(rel) - 1)]
    cmd[clock < rel[0]] = 0.0
    u = np.column_stack([t4.lag_series(clock, cmd[:, i], t4.TAU_V) for i in range(4)])  # time invariant: shift it below
    grid = th[keep]
    delivered = h["u"][keep]
    mask = np.abs(delivered) > 1e-5  # M1 runs deliver zero while a line fills
    for shift in np.arange(-0.25, 0.25001, 0.001):
        ug = np.column_stack([np.interp(grid + shift, clock, u[:, i]) for i in range(4)])
        err = float(np.sqrt(np.mean((ug[mask] - delivered[mask]) ** 2)))
        if err < best[1]:
            best = (t_guess + shift, err)
    k0 = int(np.searchsorted(th, 0.0))
    return {"t_event": best[0], "rms_u_mm_s": best[1] * 1e3, "shift_from_ready5": best[0] - t_guess, "F0_kN": (h["F"][k0] / 1e3).tolist()}


FITS: dict = {}


def build(name, circuit, variant, offset, p, folder):
    """t4_replay.build with the event time, the loads and the sink curve replaced."""
    fit = FITS[(variant, offset)]
    row = t4.load_row(variant, offset)
    t_ready = row["values"]["times"]["t_first_ready_s"]
    original_load = t4.load_row
    original_lookup = t4.Hmf.lookup

    def load_row_patched(v, o):
        r = json.loads(json.dumps(original_load(v, o)))
        r["state_at"]["ready"]["F"] = fit["F0_kN"]
        r["values"]["times"]["t_first_ready_s"] = fit["t_event"] - 5.0 - o  # build() subtracts t_ready + 5 + offset
        return r

    def lookup_patched(self, fold, lname, t, y, target, port):
        if lname == "S0RR":
            t = np.arange(0.0, t4.T_SETTLE + t4.T_AFTER + 1e-9, 1e-3)
            y = float(y[0]) + quintic_mm(t - t4.T_SETTLE) * 1e-3
        return original_lookup(self, fold, lname, t, y, target, port)

    t4.load_row = load_row_patched
    t4.Hmf.lookup = lookup_patched
    try:
        return t4.build(name, circuit, variant, offset, p, folder)
    finally:
        t4.load_row = original_load
        t4.Hmf.lookup = original_lookup


def run_one(job, p, work):
    name, circuit_name, variant, offset = job
    circuit = t4.CIRCUITS[circuit_name]
    folder = work / name
    model, t_end, n_log, log, grid, u, F0 = build(name, circuit, variant, offset, p, folder)
    df, _un, info = t4.run_hopsan(model, folder, sim=(0.0, t4.TS, t_end), log_only=log, num_log_samples=n_log, timeout=500.0)
    t = df.index.to_numpy() - t4.T_SETTLE
    n = len(t)
    F, ph, pr, la, lb = (np.zeros((n, 4)) for _ in range(5))
    oa, ob = np.zeros((n, 4)), np.zeros((n, 4))
    for i, leg in enumerate(LEGS):
        F[:, i] = df[f"Ftot{leg}#out#Value"].to_numpy() - (p.A_h[i] - p.A_r[i]) * P_ATM
        if circuit["check"]:
            ph[:, i] = df[f"POCA{leg}#P2#Pressure"].to_numpy() - P_ATM
            pr[:, i] = df[f"POCB{leg}#P2#Pressure"].to_numpy() - P_ATM
            la[:, i] = df[f"POCA{leg}#P1#Pressure"].to_numpy() - P_ATM
            lb[:, i] = df[f"POCB{leg}#P1#Pressure"].to_numpy() - P_ATM
            oa[:, i] = df[f"GTPOCA{leg}#out#Value"].to_numpy()
            ob[:, i] = df[f"GTPOCB{leg}#out#Value"].to_numpy()
        else:
            ph[:, i] = df[f"QA{leg}#P1#Pressure"].to_numpy() - P_ATM
            pr[:, i] = df[f"QB{leg}#P1#Pressure"].to_numpy() - P_ATM
    np.savez_compressed(work / f"{name}.npz", t=t, F=F, ph=ph, pr=pr, la=la, lb=lb, oa=oa, ob=ob, grid=grid - t4.T_SETTLE, u=u)
    w = t >= 0.0
    out = {"name": name, "circuit": circuit_name, "commands": variant, "offset": offset, "wall_s": info["wall_s"],
           "F_min_kN": {leg: float(F[w, i].min() / 1e3) for i, leg in enumerate(LEGS)},
           "F_min_t_s": {leg: float(t[w][np.argmin(F[w, i])]) for i, leg in enumerate(LEGS)}}
    marks = {}
    for rel in (0.5, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.5):
        j = int(np.argmin(np.abs(t - rel)))
        marks[f"+{rel:g}"] = {"F": np.round(F[j] / 1e3, 2).tolist(), "p_h": np.round(ph[j] / 1e5, 1).tolist(), "p_r": np.round(pr[j] / 1e5, 1).tolist(),
                              "line_a": np.round(la[j] / 1e5, 1).tolist(), "line_b": np.round(lb[j] / 1e5, 1).tolist()}
    out["marks"] = marks
    if circuit["check"]:
        first = {}
        for i, leg in enumerate(LEGS):
            head = np.flatnonzero((t > 0.3) & (oa[:, i] > 0.5))
            closed = np.flatnonzero((t > 0.0) & (ob[:, i] < 0.5))
            rod_open = None
            if closed.size:
                again = np.flatnonzero((t > t[closed[0]]) & (ob[:, i] > 0.5))
                rod_open = float(t[again[0]]) if again.size else None
            ucmd = np.flatnonzero(np.abs(u[:, i]) > 1e-6)
            first[leg] = {"head_first_open_s": float(t[head[0]]) if head.size else None, "rod_first_closed_s": float(t[closed[0]]) if closed.size else None,
                          "rod_reopen_s": rod_open, "first_cmd_s": float(grid[ucmd[0]] - t4.T_SETTLE) if ucmd.size else None,
                          "p_r_max_before_2s": float(pr[(t > 0) & (t < 2.0), i].max() / 1e5)}
        out["checks"] = first
    return out


def main(argv):
    pin()
    p = load_params()
    work = HERE / "t9"
    work.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for variant in ("OFF", "V1", "B1"):
        for off in OFFSETS:
            FITS[(variant, off)] = event_fit(variant, off)
    print({f"{k[0]}_{k[1]}": (round(v["t_event"], 3), round(v["rms_u_mm_s"], 3), round(v["shift_from_ready5"], 3)) for k, v in FITS.items()}, flush=True)
    (OUT / "event_fit.json").write_text(json.dumps({f"{k[0]}_{k[1]}": v for k, v in FITS.items()}, indent=1), encoding="utf-8")
    if "--first" in argv:
        jobs = [(f"nocheck_OFF_{o}", "nocheck", "OFF", o) for o in OFFSETS]
        target = "first_nocheck.json"
    else:
        jobs = [(f"{c}_{v}_{o}", c, v, o) for o in OFFSETS for c in ("nocheck", "vent", "vent_ref", "block") for v in ("OFF", "V1", "B1")]
        target = "replay.json"
    with ThreadPoolExecutor(4) as pool:
        rows = list(pool.map(lambda j: run_one(j, p, work), jobs))
    (OUT / target).write_text(json.dumps(rows, indent=0), encoding="utf-8")
    for r in rows:
        extra = ""
        if r["commands"] == "OFF" and r["circuit"] == "nocheck":
            extra = f"harness {HARNESS_OFF[r['offset']]}"
        print(r["name"], "RR min", round(r["F_min_kN"]["RR"], 2), "t", round(r["F_min_t_s"]["RR"], 3), extra, "marks", {k: r["marks"][k]["F"] for k in ("+1", "+1.4")}, "pr+1.4", r["marks"]["+1.4"]["p_r"], flush=True)


if __name__ == "__main__":
    main(sys.argv)
