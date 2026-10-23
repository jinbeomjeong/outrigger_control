"""S6 spec revision 4: probe attitude cue on a statically determinate (three-leg) support, rect vs trapezoid.

Scenario (as 05_tests/unit/test_c2_closed_loop.py lifted_rr_loop, imported read-only): C2 R4 levels the reduced plant
(top / middle / bottom, flat), the RR floor sinks 30 mm over 5 s with the controller frozen (u = 0), RR lifts and the
machine teeters on the FR-RL diagonal; after a settle time S (12 ... 26 s, i.e. different teeter phases / amplitudes)
one probe round runs open loop (controller frozen) with
  rect      : R2/R3 profile 0.25 v_max, hold 0.4 s
  trap      : R4 default trapezoid D 0.56 s / tau 0.36 s, hold 0.4 s
  trap_h075 : trapezoid, hold 0.75 s (window-centre spacing 1.67 s)
Reported per run: verdicts, RR attitude-response ratio, RR midpoint load estimate, and the window ripple of the
rate-integrated attitude projected on J_i (peak-to-peak after removing the linear trend, max of the before / after
windows) / expected response |J_i| d - the candidate quality gate. Reference: the same rounds on the levelled
four-leg machine (no sink) for the false-abstain side.
Run: conda run -n dynamics-dev python -I s6r4_lifted_probe.py <project_root> <out_json> [workers]
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import copy  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\workspace\outrigger_control")
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(ROOT / "05_tests" / "unit"))
import test_c2_closed_loop as T  # noqa: E402
from outrigger_sim.control.ground_contact import ProbeProfile, ProbeSettings  # noqa: E402

LEVEL = {"name": "top"}
_orig_settled = T.settled_plant


def settled_plant_level(roll_deg=0.0, pitch_deg=0.0):
    plant = T.reduced_model.Plant(LEVEL["name"], roll_deg, pitch_deg)
    plant.step(np.zeros(4), int(round(T.reduced_model.SETTLE_ON_CRAWLER_S / T.reduced_model.DT)))
    plant.t = 0.0
    return plant


T.settled_plant = settled_plant_level

SETTINGS = {
    "rect": ProbeSettings(use_combined_verdict=True, profile=ProbeProfile.RECT),
    "trap": ProbeSettings(use_combined_verdict=True, profile=ProbeProfile.TRAPEZOID),
    "trap_h075": ProbeSettings(use_combined_verdict=True, profile=ProbeProfile.TRAPEZOID, hold_s=0.75),
}
SETTLES = (12.0, 14.0, 16.0, 18.0, 19.0, 20.0, 21.0, 22.0, 24.0, 26.0)


def probe_with_trace(loop, settings):
    """T._probe_round_without_controller plus a per-period trace of (t, leg, stage, has_record, rate attitude)."""
    trace = []
    orig_step = None
    import outrigger_sim.control.ground_contact as gc
    orig_step = gc.ProbeRound.step

    def step(self, reading):
        leg_before, rec_before, stage_before = self.leg, self._record is not None, self._stage.value
        out = orig_step(self, reading)
        trace.append((reading.t_s, leg_before, stage_before, rec_before, reading.rate_attitude_rad))
        return out
    gc.ProbeRound.step = step
    try:
        probe = T._probe_round_without_controller(loop, settings)
    finally:
        gc.ProbeRound.step = orig_step
    return probe, trace


def ripple_metrics(trace, J, depth, win_n):
    """Per leg: max over the before / after windows of the detrended p-p of the attitude projected on J_i."""
    out = []
    att = np.array([tr[4] for tr in trace])
    legs = np.array([tr[1] for tr in trace]); stages = [tr[2] for tr in trace]; recs = np.array([tr[3] for tr in trace])
    for k in range(4):
        u = np.asarray(J[k], float); nu = float(np.linalg.norm(u))
        if nu == 0:
            out.append(None); continue
        u = u / nu
        idx = np.where(legs == k)[0]
        if len(idx) == 0:
            out.append(None); continue
        i_start = idx[0]                                  # the period that created the leg record
        firsts = [i for i in idx if stages[i] == "first_move"]
        i_end = firsts[-1] if firsts else idx[-1]        # last period of the first stage (window mean taken)
        pp = []
        for a, b in ((i_start - win_n, i_start), (i_end - win_n + 1, i_end + 1)):
            a = max(a, 0)
            seg = att[a:b] @ u
            if len(seg) < 3:
                continue
            x = np.arange(len(seg))
            seg = seg - np.polyval(np.polyfit(x, seg, 1), x)
            pp.append(float(np.ptp(seg)))
        out.append(round(max(pp) / (nu * depth), 4) if pp else None)
    return out


def teeter_freq(loop, t0):
    s = loop.record.arrays()
    m = s["t_s"] >= t0
    f = s["force_N"][m][:, 0]
    f = f - f.mean()
    if len(f) < 50:
        return None
    dt = float(np.median(np.diff(s["t_s"][m])))
    fr = np.fft.rfftfreq(len(f), dt); S = np.abs(np.fft.rfft(f * np.hanning(len(f))))
    sel = fr > 0.3
    return round(float(fr[sel][np.argmax(S[sel])]), 3), round(float(np.ptp(f)) / 1e3, 1)


def summarise(probe, trace, loop, settings, label, extra):
    g = loop.controller.geometry
    J = np.asarray(g.attitude_sensitivity_rad_m)
    win_n = max(1, round(settings.attitude_window_s / loop.controller.period_s))
    rip = ripple_metrics(trace, J, settings.depth_m, win_n)
    res = probe.results
    contact = loop.record.arrays()["contact_N"][-1]
    return dict(label=label, **extra,
                truth_grounded=(contact > 0).tolist(),
                verdict=[r.is_grounded for r in res],
                by_stiffness=[r.is_grounded_by_stiffness for r in res],
                band=[None if r.load_band is None else str(r.load_band) for r in res],
                ratio=[None if r.attitude_response_ratio is None or not math.isfinite(r.attitude_response_ratio)
                       else round(r.attitude_response_ratio, 3) for r in res],
                load_kN=[round(r.load_estimate_N / 1e3, 2) for r in res],
                ripple_over_expected=rip)


def run_level(level):
    LEVEL["name"] = level
    out = []
    t0w = time.perf_counter()
    base = T.levelled(T.c2_loop())
    # reference: four-leg support, no sink
    for name, st in SETTINGS.items():
        lp = copy.deepcopy(base)
        probe, trace = probe_with_trace(lp, st)
        out.append(summarise(probe, trace, lp, st, f"{level}|4leg|{name}", {"level": level, "case": "4leg",
                                                                             "settle_s": None, "setting": name}))
    loop = copy.deepcopy(base)
    plant = loop.plant
    t_start = plant.t
    period = loop.controller.period_s
    snaps = {}
    t_target = sorted(SETTLES)
    while t_target:
        plant.goff[T.RR] = T.LIFTING_SINK_M * min(1.0, (plant.t - t_start) / T.SINK_RAMP_S)
        loop.advance(np.zeros(4))
        el = plant.t - t_start - T.SINK_RAMP_S
        if el >= t_target[0] - 1e-9:
            snaps[t_target.pop(0)] = copy.deepcopy(loop)
    for S, snap in snaps.items():
        tf = teeter_freq(snap, snap.plant.t - 8.0)
        for name, st in SETTINGS.items():
            lp = copy.deepcopy(snap)
            probe, trace = probe_with_trace(lp, st)
            out.append(summarise(probe, trace, lp, st, f"{level}|lifted|S{S}|{name}",
                                 {"level": level, "case": "lifted", "settle_s": S, "setting": name,
                                  "teeter_f_Hz_FLpp_kN_last8s": tf}))
    print(f"{level} done {time.perf_counter() - t0w:.0f} s", flush=True)
    return out


def main():
    out_json = Path(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    import multiprocessing as mp
    with mp.get_context("spawn").Pool(min(workers, 3)) as pool:
        res = sum(pool.map(run_level, ["top", "middle", "bottom"]), [])
    out_json.write_text(json.dumps(res, indent=1, default=str))
    for r in res:
        print(f"{r['label']:28s} truth={['G' if x else 'L' for x in r['truth_grounded']]} "
              f"verdict={['G' if x else 'L' for x in r['verdict']]} ratio={r['ratio']} RRload={r['load_kN'][3]} "
              f"rip={r['ripple_over_expected']} tf={r.get('teeter_f_Hz_FLpp_kN_last8s')}")


if __name__ == "__main__":
    main()
