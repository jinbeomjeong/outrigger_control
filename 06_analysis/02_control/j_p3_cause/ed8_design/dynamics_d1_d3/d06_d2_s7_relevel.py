"""d06 (D-2): S7 re-level after the first probe, short vs long branch, with plant / soil states.

Per run (d00 S7 reruns): the LEVEL segment right after PROBE 1. Trace per 10 Hz period:
controller roll / pitch (filtered, rad), roll / pitch integrals, completion flags, commands
(controller output, T4h ``command_m_s``), plant lock flag, seal force and stick state, soil
sinkage ``z``, plastic sinkage ``sp`` (Bekker element of the S9 harness, ``sp`` grows only on a
virgin load), soil force, twist load ``D = nu^T F`` (T4h ``lsb_ib_twist_load_N``) and the A_ib
floor flag. Summary per run: probe 1 net stroke change, re-level length, start error, the
first period the attitude is inside the completion band, the plastic sinkage added per leg
during PROBE 1 and during the re-level, the command sign pattern, sub-hold periods.

Usage: conda run -n dynamics-dev python -I -B d06_d2_s7_relevel.py <d00 scratch dir>
Output: d06_d2_s7_relevel_summary.csv, d06_d2_s7_relevel_trace.csv, d06_d2_s7_relevel.json.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent
LEGS = ("FL", "FR", "RL", "RR")
U_HOLD = 0.01 * 0.020924
RUNS = ("S7_e0.002_D8-M-a2", "S7_e0.003_D8-M-a2", "S7_e0.0_D8-M-a2",
        "S7_e0.0_D8-Mslow-a2", "S7_e0.002_D8-Mslow-a2",
        "S7_e0.002_D8-M-A", "S7_e0.003_D8-M-A", "S7_e0.0_D8-Mslow-A", "S7_e0.002_D8-Mslow-A")


def longest(path: Path, tkey: str) -> dict:
    z = np.load(path, allow_pickle=False)
    objs = sorted({k.split("|")[0] for k in z.files})
    best = max(objs, key=lambda o: len(z[f"{o}|{tkey}"]) if f"{o}|{tkey}" in z.files else 0)
    return {k.split("|", 1)[1]: z[k] for k in z.files if k.startswith(best + "|")}


def segs(ph):
    out, s = [], 0
    for i in range(1, len(ph) + 1):
        if i == len(ph) or ph[i] != ph[s]:
            out.append((str(ph[s]), s, i - 1))
            s = i
    return out


def main() -> int:
    scratch = Path(sys.argv[1])
    summary, trace = [], []
    for run in RUNS:
        t4h = dict(np.load(scratch / "t4h" / f"{run}.npz", allow_pickle=False))
        plant = longest(scratch / "logs" / f"{run}_plant.npz", "t")
        ctrl = longest(scratch / "logs" / f"{run}_ctrl.npz", "m.t_s")
        t = t4h["t_s"]
        ph = np.char.lower(t4h["phase"].astype(str))
        sg = segs(ph)
        k_probe = next(k for k, s in enumerate(sg) if s[0] == "probe")
        p0, p1 = sg[k_probe][1], sg[k_probe][2]
        nxt = sg[k_probe + 1] if k_probe + 1 < len(sg) else None
        if nxt is None or nxt[0] != "level":
            l0 = l1 = None
        else:
            l0, l1 = nxt[1], nxt[2]

        def pidx(k):
            return int(np.argmin(np.abs(plant["t"] - t[k])))

        def cidx(k):
            return int(np.argmin(np.abs(ctrl["m.t_s"] - t[k])))

        sp = plant["soil.sp"]
        row = {"run": run, "probe_t0_s": round(float(t[p0]), 2),
               "probe_len_s": round(float(t[p1] - t[p0] + 0.1), 2),
               "relevel_len_s": None if l0 is None else round(float(t[l1] - t[l0] + 0.1), 2)}
        stroke = t4h["motor_stroke_m"]
        for j, leg in enumerate(LEGS):
            row[f"probe_net_{leg}_mm"] = round(float(stroke[p1, j] - stroke[p0 - 1, j]) * 1e3, 3)
            row[f"probe_dsp_{leg}_mm"] = round(float(sp[pidx(p1), j] - sp[pidx(p0 - 1), j]) * 1e3, 3)
        if l0 is not None:
            c0 = cidx(l0)
            row["roll0_mrad"] = round(float(ctrl["s.roll_rad"][c0]) * 1e3, 4)
            row["pitch0_mrad"] = round(float(ctrl["s.pitch_rad"][c0]) * 1e3, 4)
            row["roll_int0"] = round(float(ctrl["s.roll_integral"][c0]), 5)
            row["pitch_int0"] = round(float(ctrl["s.pitch_integral"][c0]), 5)
            cmd = t4h["command_m_s"][l0:l1 + 1]
            sub = (np.abs(cmd) > 0) & (np.abs(cmd) <= U_HOLD + 1e-12)
            row["subhold_leg_periods"] = int(sub.sum())
            row["moving_leg_periods"] = int((np.abs(cmd) > U_HOLD + 1e-12).sum())
            signs = np.sign(np.round(cmd * 1e6))
            row["sign_changes"] = int(sum(np.count_nonzero(np.diff(signs[:, j][signs[:, j] != 0]))
                                          for j in range(4)))
            for j, leg in enumerate(LEGS):
                row[f"relevel_dsp_{leg}_mm"] = round(float(sp[pidx(l1), j] - sp[pidx(l0), j]) * 1e3, 3)
                row[f"relevel_net_{leg}_mm"] = round(float(stroke[l1, j] - stroke[l0 - 1, j]) * 1e3, 3)
            ib = t4h["lsb_ib_on"][l0:l1 + 1]
            row["ib_on_leg_periods"] = int(ib.sum())
            row["D_start_kN"] = round(float(t4h["lsb_ib_twist_load_N"][l0]) / 1e3, 3)
            row["D_end_kN"] = round(float(t4h["lsb_ib_twist_load_N"][l1]) / 1e3, 3)
            done = ctrl["s.completion_flags.is_on_target"]
            first_on = next((k for k in range(l0, l1 + 1) if done[cidx(k)] > 0.5), None)
            row["t_first_on_target_after_start_s"] = None if first_on is None else round(
                float(t[first_on] - t[l0]), 2)
            for k in range(max(p1 - 5, 0), min(l1 + 6, len(t))):
                ip, ic = pidx(k), cidx(k)
                tr = {"run": run, "t_s": round(float(t[k]), 2), "phase": ph[k],
                      "roll_mrad": round(float(ctrl["s.roll_rad"][ic]) * 1e3, 4),
                      "pitch_mrad": round(float(ctrl["s.pitch_rad"][ic]) * 1e3, 4),
                      "roll_int": round(float(ctrl["s.roll_integral"][ic]), 5),
                      "pitch_int": round(float(ctrl["s.pitch_integral"][ic]), 5),
                      "on_target": int(ctrl["s.completion_flags.is_on_target"][ic] > 0.5),
                      "complete": int(ctrl["s.completion_flags.is_complete"][ic] > 0.5),
                      "D_kN": round(float(t4h["lsb_ib_twist_load_N"][k]) / 1e3, 3)}
                for j, leg in enumerate(LEGS):
                    Fs = float(plant["Fs"][ip, j])
                    f = float(plant["f"][ip, j])
                    tr.update({f"{leg}_cmd_mm_s": round(float(t4h["command_m_s"][k, j]) * 1e3, 3),
                               f"{leg}_locked": int(plant["locked"][ip, j]),
                               f"{leg}_stuck": int(abs(f) < Fs - 1.0),
                               f"{leg}_f_kN": round(f / 1e3, 3),
                               f"{leg}_x_mm": round(float(plant["x"][ip, j]) * 1e3, 3),
                               f"{leg}_z_mm": round(float(plant["soil.z"][ip, j]) * 1e3, 3),
                               f"{leg}_sp_mm": round(float(sp[ip, j]) * 1e3, 4),
                               f"{leg}_Fsoil_kN": round(float(plant["soil.force"][ip, j]) / 1e3, 3),
                               f"{leg}_ib": int(t4h["lsb_ib_on"][k, j])})
                trace.append(tr)
        summary.append(row)
    for name, rows in (("summary", summary), ("trace", trace)):
        fields = []
        for r in rows:
            for k in r:
                if k not in fields:
                    fields.append(k)
        with (OUT / f"d06_d2_s7_relevel_{name}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
    (OUT / "d06_d2_s7_relevel.json").write_text(json.dumps({"summary": summary}, indent=1),
                                                encoding="utf-8")
    for r in summary:
        print(json.dumps(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
