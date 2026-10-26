"""S9 P2' (settle dashpot) dynamics judgement support values (dynamics_model.md rev. 51, 5.36).

Reads the cad P2' batch and the dyn repeat runs (07_results/S9/...), re-runs the planar crawler
settle replica (s9_crawler_replica_kcb.simulate + settle dashpot on heave / pitch, faded 3 -> 5 s)
with a hit-height rounding sweep, writes one JSON:

  (A) Chrono P2' windows: 1 s means / p-p of pitch, roll, z0 for 3-8 s, 1 s-mean drift 4-8 s,
      dominant rocking frequency 5-8 s, start rise; pad SCM force (pads must be off the soil).
  (B) Chrono J1 repeats: SCM threads 2 / 6 (summation order) and gravity ramp 2.95 / 3.05 s
      (approach speed at first contact) against the P2' run (threads 4, ramp 3 s).
  (C) Replica rounding sweep: hit height rounded to a quantum q in {6e-8 ... 9.6e-7} m with a
      per-node random phase (seeds 1-3) = stand-in for the Chrono per-node rounding pattern of
      the Bullet single-precision ray test; J1, J2, c_z 2e6 N s/m.
  (D) Replica dashpot strength (J1, c_z 2e6 / 6e6 / 2e7, pitch c = c_z (1.3 m)^2) and gravity
      ramp 2.95 / 3.0 / 3.05 s under rounding: does the dashpot or the ramp set the state?

Frame: body x forward, z up; pitch > 0 nose down; z0 = body-origin z change [mm]; gravity
(0, 0, -9.80665) m/s^2 x Poly345 ramp; SI unless the key says mm / deg.

Usage (dynamics-dev, activated):
  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/s9_p2prime_judge_rev51.py <out.json>
"""

from __future__ import annotations

import inspect
import json
import sys
import textwrap
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

WT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WT / "04_scripts" / "01_dynamics"))
import s9_crawler_replica_kcb as kcb  # noqa: E402

S9 = WT / "07_results" / "S9"
P2P = S9 / "batch_P2prime_20261026_083209"
REP = S9 / "batch_P2prime_rep_20261026"
CASES = {s: f"P2prime_{s}_top_M14s_dashpot8s" for s in ("J1", "J2", "G1", "S1")}
REPEATS = {
    "threads2": "P2prime_J1_top_M14s_dashpot8s_thr2",
    "threads6": "P2prime_J1_top_M14s_dashpot8s_thr6",
    "ramp2.95": "P2prime_J1_top_M14s_dashpot8s_ramp2.95",
    "ramp3.05": "P2prime_J1_top_M14s_dashpot8s_ramp3.05",
}


# ---------------------------------------------------------------- (A) / (B) Chrono series
def chrono_windows(case_dir: Path) -> dict:
    d = np.load(case_dir / "series.npz")
    t = d["t_s"]
    z0 = (d["body_pos_m"][:, 2] - d["body_pos_m"][0, 2]) * 1e3
    roll, pitch = d["roll_pitch_deg"][:, 0], d["roll_pitch_deg"][:, 1]
    t_end = float(t[-1])
    win = {}
    for a in range(3, int(round(t_end))):
        m = (t >= a) & (t < a + 1)
        win[f"{a}-{a + 1}"] = dict(pitch_deg=float(pitch[m].mean()), pitch_pp_deg=float(np.ptp(pitch[m])),
                                  roll_deg=float(roll[m].mean()), z0_mm=float(z0[m].mean()),
                                  z0_pp_mm=float(np.ptp(z0[m])))
    last = t > t_end - 1.0 + 1e-9
    m4 = [(t >= a) & (t < a + 1) for a in (4, 5, 6, 7)]
    drift = float(pitch[m4[-1]].mean() - pitch[m4[0]].mean())
    m5 = t >= 5.0
    x = pitch[m5] - np.polyval(np.polyfit(t[m5], pitch[m5], 1), t[m5])
    f = np.fft.rfftfreq(len(x), t[1] - t[0])
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    inst = {f"{tt:g}": float(pitch[min(np.searchsorted(t, tt - 1e-9), len(t) - 1)]) for tt in (3, 4, 5, 6, 7, 8)}
    early = t <= 5.0 + 1e-9
    return dict(
        case=case_dir.name, t_end_s=t_end,
        judge_window=dict(pitch_deg=float(pitch[last].mean()), z0_mm=float(z0[last].mean()),
                          pitch_pp_deg=float(np.ptp(pitch[last])), roll_deg=float(roll[last].mean())),
        windows_1s=win, pitch_drift_1s_means_4_to_8_deg=drift,
        pitch_instant_at_integer_s_deg=inst,
        rocking_peak_hz_5_8s=float(f[np.argmax(spec[1:]) + 1]),
        start_rise_mm=float(z0[early].max()), start_rise_t_s=float(t[early][np.argmax(z0[early])]),
        first_crawler_force_t_s=float(t[np.argmax(d["scm_crawler_normal_N"] > 0)]),
        pad_scm_force_abs_max_N=float(np.abs(d["scm_pad_normal_N"]).max()),
        ray_hits_end=float(d["scm_ray_hits"][-1]),
    )


def repeat_diff(ref_dir: Path, rep_dir: Path) -> dict:
    a, b = np.load(ref_dir / "series.npz"), np.load(rep_dir / "series.npz")
    n = min(len(a["t_s"]), len(b["t_s"]))
    same_t = bool(np.array_equal(a["t_s"][:n], b["t_s"][:n]))
    out = dict(same_time_grid=same_t)
    if same_t and len(a["t_s"]) == len(b["t_s"]):
        out["max_abs_diff"] = {k: float(np.abs(a[k] - b[k]).max()) for k in ("body_pos_m", "roll_pitch_deg",
                                                                              "scm_crawler_normal_N")}
    return out


# ---------------------------------------------------------------- (C) / (D) replica
def _patched():
    src = textwrap.dedent(inspect.getsource(kcb.simulate))
    old = "        sink = p0.Z_SURF - zw\n"
    new = "        sink = p0.Z_SURF - ((np.round((zw + OFF) / QQ) * QQ - OFF) if QQ > 0 else zw)\n"
    oldv = "        vz += dt * (Fz / m - G * gf)\n        om += dt * My / Iyy\n"
    newv = ("        cdf = CD * min(1.0, max(0.0, (T1 - t) / (T1 - T0)))\n"
            "        vz += dt * (Fz / m - G * gf - cdf * vz / m)\n"
            "        om += dt * (My - cdf * 1.69 * om) / Iyy\n")
    assert src.count(old) == 1 and src.count(oldv) == 1
    src = src.replace(old, new).replace(oldv, newv)
    src = src.replace("def simulate(\n", "def simulate_v(\n    QQ,\n    OFF,\n    CD,\n    T0,\n    T1,\n", 1)
    src = src.replace("simulate.last_anchor_events", "kcb.simulate.last_anchor_events")
    ns = dict(kcb.__dict__)
    ns["kcb"] = kcb
    exec(compile(src, "simulate_v", "exec"), ns)
    return ns["simulate_v"]


def replica_job(spec):
    group, soil, q, seed, cd, ramp = spec
    sim = _patched()
    md = kcb.build(soil, 0.04, kcb.CH)
    if q > 0 and seed > 0:
        off = np.random.default_rng(seed).uniform(0.0, q, size=md["w"].shape)
    else:
        off = np.zeros_like(md["w"])
    t_end = ramp + 5.0
    out, _ = sim(q, off, cd, 3.0, 5.0, md, t_end=t_end, ramp=ramp)
    t, th, z = out[:, 0], out[:, 1], out[:, 3] * 1e3
    e = t <= 5.0 + 1e-9
    s = t > t_end - 1.0 + 1e-9
    return dict(group=group, soil=soil, q_m=q, seed=seed, c_z_N_s_m=cd, ramp_s=ramp,
                start_rise_mm=float(z[e].max()), pitch_deg=float(th[s].mean()), z0_mm=float(z[s].mean()),
                pitch_pp_deg=float(np.ptp(th[s])))


def replica_specs():
    out = []
    for soil in ("J1", "J2"):
        out.append(("C", soil, 0.0, 0, 2.0e6, 3.0))
        for q in (6e-8, 1.2e-7, 2.4e-7, 4.8e-7, 9.6e-7):
            for seed in (1, 2, 3):
                out.append(("C", soil, q, seed, 2.0e6, 3.0))
    for cd in (6.0e6, 2.0e7):
        out.append(("D_c", "J1", 0.0, 0, cd, 3.0))
        for q in (1.2e-7, 4.8e-7):
            for seed in (1, 2, 3):
                out.append(("D_c", "J1", q, seed, cd, 3.0))
    for soil in ("J1", "J2"):
        for ramp in (2.95, 3.05):
            out.append(("D_ramp", soil, 0.0, 0, 2.0e6, ramp))
            out.append(("D_ramp", soil, 1.2e-7, 0, 2.0e6, ramp))
            out.append(("D_ramp", soil, 4.8e-7, 1, 2.0e6, ramp))
        out.append(("D_ramp", soil, 1.2e-7, 0, 2.0e6, 3.0))
    return out


def envelope(rows):
    p = [r["pitch_deg"] for r in rows]
    z = [r["z0_mm"] for r in rows]
    s = [r["start_rise_mm"] for r in rows]
    return dict(n=len(rows), pitch_deg=[min(p), max(p)], z0_mm=[min(z), max(z)], start_rise_mm=[min(s), max(s)])


def main():
    t0 = time.perf_counter()
    out = dict(
        doc="dynamics_model.md rev. 51, 5.36", frame="body x fwd, z up, pitch > 0 nose down; z0 body origin [mm]",
        chrono=dict(p2prime={s: chrono_windows(P2P / c) for s, c in CASES.items()}),
    )
    reps = {}
    for tag, c in REPEATS.items():
        if (REP / c / "series.npz").exists():
            w = chrono_windows(REP / c)
            w["diff_to_p2prime"] = repeat_diff(P2P / CASES["J1"], REP / c)
            w["argv_note"] = ("--threads " + tag[7:]) if tag.startswith("threads") else ("--gravity-ramp " + tag[4:])
            reps[tag] = w
    out["chrono"]["j1_repeats"] = reps
    with ProcessPoolExecutor(8) as ex:
        rows = list(ex.map(replica_job, replica_specs()))
    out["replica"] = rows
    env = {}
    for soil in ("J1", "J2"):
        rr = [r for r in rows if r["group"] == "C" and r["soil"] == soil]
        env[soil] = dict(all=envelope(rr), rounded_only=envelope([r for r in rr if r["q_m"] > 0]))
    out["replica_envelope_c2e6"] = env
    out["wall_s"] = time.perf_counter() - t0
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1), encoding="utf-8")
    for soil in ("J1", "J2"):
        print(soil, json.dumps(env[soil]))
    print("wall", out["wall_s"])


if __name__ == "__main__":
    main()
