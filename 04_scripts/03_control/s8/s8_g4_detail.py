"""G4 (RR 11.5 mm / 2 s) detail under seal friction, combined judge, flat top (S8 pre-check).

Run: conda run -n dynamics-dev python -I s8_g4_detail.py <project_root> <out_txt>
Prints per control sample after the sink start: t, phase, RR reading P, RR lower bound P - F_band, RR true force,
RR command, RR friction state f (plant), for F_s 0 / 2 / 4 / 8 kN.
"""
import copy
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s8_fs_precheck as pc  # noqa: E402  (argv[1] = project root)


def main():
    lines = []
    cl, C2Controller, C2Phase, ContactJudge, Measurements = pc._imports()
    for fs in (0.0, 2.0, 4.0, 8.0):
        cl.rmf.CONFIG.clear(); cl.rpt.RCFG.clear()
        plant = cl.rmf.FlexPlant("top", 0.0, 0.0, Fs=fs * 1e3)
        plant.step(np.zeros(4), int(round(cl.rcc.SETTLE_ON_CRAWLER_S / plant.dt)))
        plant.t = 0.0
        ctrl = C2Controller.from_params(cl.PARAMS, cl.preset_config(ContactJudge.COMBINED, with_imu_samples=True))
        ha = ctrl.geometry.head_area_m2
        cmd, valve = np.zeros(4), np.zeros(4)
        t_ready = None
        while plant.t < 170:
            m, *_ = pc.period(cl, Measurements, plant, cmd, valve, ha, ctrl.period_s)
            cmd = np.array(ctrl.update(m).leg_speed_m_s)
            if ctrl.phase is C2Phase.READY and t_ready is None:
                t_ready = plant.t
            if t_ready is not None and plant.t >= t_ready + 5.0 - 1e-9:
                break
        t_ev = plant.t
        n0 = len(ctrl.events)
        lines.append(f"=== F_s {fs} kN  F_band {ctrl.seal_band_N/1e3:.2f} kN  t_ready {t_ready:.1f}")
        while plant.t < t_ev + 4.0:
            plant.goff[3] = 0.0115 * min(1.0, max(0.0, (plant.t - t_ev) / 2.0))
            m, fmin, cmin, _ = pc.period(cl, Measurements, plant, cmd, valve, ha, ctrl.period_s)
            P = plant.pressure()[3]
            cmd = np.array(ctrl.update(m).leg_speed_m_s)
            lines.append(f"t {plant.t - t_ev:5.2f} {str(ctrl.phase):6s} P {P/1e3:7.2f} lo {(P - ctrl.seal_band_N)/1e3:7.2f} "
                         f"true {fmin[3]/1e3:7.2f} f {plant.f[3]/1e3:6.2f} cmdRR {cmd[3]*1e3:6.2f} mm/s "
                         f"cmd {np.round(cmd*1e3, 2).tolist()}")
        lines.append("events " + str([(round(e.t_s - t_ev, 2), e.name) for e in ctrl.events[n0:]][:8]))
    Path(sys.argv[2]).write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
