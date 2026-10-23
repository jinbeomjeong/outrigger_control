"""S6 spec revision 5: probe cues under seal friction F_s (0 / 5 / 12 kN) on the three-leg (RR lifted) support.

Re-uses s6r4_lifted_probe.py (probe_with_trace, summarise) and the test helpers by import. Reduced plant with
Plant(..., Fs=F_s) (rod seal friction, pressure reading = true force +- F_s). Top level, settle 14 / 20 / 26 s after
the 30 mm RR floor sink, rect and trapezoid; also the four-leg reference. Reports per leg: band, stiffness verdict,
incremental stiffness / S_ii, midpoint load estimate, attitude ratio, window ripple, final verdict; and the RR
pressure reading while lifted (what a pressure-only judge sees).
Run: conda run -n dynamics-dev python -I s6r5_fs_probe.py <project_root> <out_json>
"""
from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(sys.argv[1])
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s6r4_lifted_probe as L  # noqa: E402

T = L.T
CFG = {"Fs": 0.0}


def settled(roll_deg=0.0, pitch_deg=0.0):
    plant = T.reduced_model.Plant("top", roll_deg, pitch_deg, Fs=CFG["Fs"])
    plant.step(np.zeros(4), int(round(T.reduced_model.SETTLE_ON_CRAWLER_S / T.reduced_model.DT)))
    plant.t = 0.0
    return plant


T.settled_plant = settled


def main():
    out = []
    for Fs in (0.0, 5e3, 12e3):
        CFG["Fs"] = Fs
        base = T.levelled(T.c2_loop())
        Sii = np.asarray(base.controller.geometry.load_sensitivity_diag_N_m)
        for name in ("rect", "trap"):
            lp = copy.deepcopy(base)
            pr, tr = L.probe_with_trace(lp, L.SETTINGS[name])
            s = L.summarise(pr, tr, lp, L.SETTINGS[name], f"Fs{Fs/1e3:g}|4leg|{name}", {"Fs_kN": Fs / 1e3})
            s["k_over_Sii"] = [round(r.incremental_stiffness_N_m / Sii[i], 3) if math.isfinite(r.incremental_stiffness_N_m)
                               else None for i, r in enumerate(pr.results)]
            out.append(s)
        loop = copy.deepcopy(base); pl = loop.plant; t0 = pl.t
        snaps = {}; targets = [14.0, 20.0, 26.0]; rr_reading = []
        while targets:
            pl.goff[T.RR] = T.LIFTING_SINK_M * min(1.0, (pl.t - t0) / T.SINK_RAMP_S)
            m = loop.advance(np.zeros(4))
            if loop.record.pad_contact_force_N[-1][T.RR] == 0.0:
                rr_reading.append(float(m.head_pressure_Pa[T.RR] * loop.controller.geometry.head_area_m2[T.RR]))
            if pl.t - t0 - T.SINK_RAMP_S >= targets[0] - 1e-9:
                snaps[targets.pop(0)] = copy.deepcopy(loop)
        for S, snap in snaps.items():
            for name in ("rect", "trap"):
                lp = copy.deepcopy(snap)
                pr, tr = L.probe_with_trace(lp, L.SETTINGS[name])
                s = L.summarise(pr, tr, lp, L.SETTINGS[name], f"Fs{Fs/1e3:g}|lifted|S{S}|{name}", {"Fs_kN": Fs / 1e3})
                s["k_over_Sii"] = [round(r.incremental_stiffness_N_m / Sii[i], 3)
                                   if math.isfinite(r.incremental_stiffness_N_m) else None for i, r in enumerate(pr.results)]
                s["rr_reading_lifted_kN_range"] = [round(min(rr_reading) / 1e3, 2), round(max(rr_reading) / 1e3, 2)] if rr_reading else None
                out.append(s)
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1, default=str))
    for s in out:
        print(f"{s['label']:24s} truth={['G' if x else 'L' for x in s['truth_grounded']]} verdict={['G' if x else 'L' for x in s['verdict']]} "
              f"band={s['band']} stiff={s['by_stiffness']} k/S={s['k_over_Sii']} load={s['load_kN']} ratio={s['ratio']} "
              f"rip={s['ripple_over_expected']} RRread={s.get('rr_reading_lifted_kN_range')}")


if __name__ == "__main__":
    main()
