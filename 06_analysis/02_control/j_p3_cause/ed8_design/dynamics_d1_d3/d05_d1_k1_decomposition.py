"""d05 (D-1): split each probe K1 into the pad-load slope and the seal-friction band term.

Harness piston law (quasi-static, massless piston, ``run_s6_slope_boundary_check`` /
``run_mast_flex_c2_check`` physics): ``F_cyl = F_el - W_r - f`` with the oil force
``F_cyl = k_o (s_ref - x)`` (+ rod-side term) and the seal force ``f`` (|f| <= F_s, stuck inside).
The controller K1 is ``dF_read / dx`` over the mid -> extended reads (the piston reading is the
plant ``x``: d04 trace ``read_piston == x``). Hence

    K1 = (dF_el - df) / dx  =  K_pad  +  (-df / dx),   K_pad = (dF_read + df) / dx

``K_pad`` is the support slope the probe means to read; ``-df/dx`` is the part of the seal
breakaway (f moving through its stick band) that falls inside the window. Also the oil-coordinate
slope ``K_m = dF / ds_ref`` and the identity ``K1 = 1 / (1/K_m - 1/k_o)`` (exact when the reading
is the oil force), and the seal force of the probed leg just before its first command (the
pre-load: +F_s = held at the retract-direction extreme, the band to cross is ``F_s + f_0``).

Mid / extended read times: the plant snapshot whose force reading equals the cue's mid / extended
force (T4h force rows, |diff| < 1 N), searched inside the probe phase of that leg.

Usage: conda run -n dynamics-dev python -I -B d05_d1_k1_decomposition.py <d00 scratch dir>
Output: d05_d1_k1_decomposition.csv, d05_d1_k1_decomposition.json (this folder).
"""
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent
LEGS = ("FL", "FR", "RL", "RR")
A_H = np.array([math.pi / 4 * 0.13 ** 2] * 2 + [math.pi / 4 * 0.11 ** 2] * 2)
A_ROD = np.array([math.pi / 4 * 0.11 ** 2] * 2 + [math.pi / 4 * 0.09 ** 2] * 2)
A_ANN = A_H - A_ROD
S_NOM = None  # filled from the cue log (load_sensitivity_N_m)
RUNS = ("R12_top-FR-Fs8-o0.0_D8-M-a2", "R12_top-FR-Fs8-o0.0_D8-M-A",
        "R12_top-FR-Fs8-o0.0_D8-L-a2", "R12_top-FR-Fs8-o0.0_D8-L-A",
        "R12_top-FR-Fs0-o0.05_D8-LSM4-a2", "R12_top-FR-Fs0-o0.05_D8-LSM4-A",
        "R12_top-FL-Fs0-o0.0_D8-Mslow-a2", "R12_top-FL-Fs0-o0.0_D8-Mslow-A",
        "R12_top-FR-Fs8-o0.0_D8-Mslow-a2", "R12_top-FR-Fs8-o0.0_D8-Mslow-A",
        "R12_top-FR-Fs8-o0.0_D8-Mh15-a2", "R12_top-FR-Fs8-o0.0_D8-Mh15-A",
        "R7_e0.0_D8-M-a2", "R7_e0.0_D8-M-A")


def longest(path: Path, tkey: str) -> dict:
    z = np.load(path, allow_pickle=False)
    objs = sorted({k.split("|")[0] for k in z.files})
    best = max(objs, key=lambda o: len(z[f"{o}|{tkey}"]) if f"{o}|{tkey}" in z.files else 0)
    return {k.split("|", 1)[1]: z[k] for k in z.files if k.startswith(best + "|")}


def main() -> int:
    scratch = Path(sys.argv[1])
    rows = []
    for run in RUNS:
        t4h = dict(np.load(scratch / "t4h" / f"{run}.npz", allow_pickle=False))
        plant = longest(scratch / "logs" / f"{run}_plant.npz", "t")
        cue = json.loads((scratch / "logs" / f"{run}_cue.json").read_text(encoding="utf-8"))
        t = t4h["t_s"]
        F = t4h["head_pressure_Pa"] * A_H - t4h["rod_pressure_Pa"] * A_ANN
        cmd = t4h["command_m_s"]
        ph = np.char.lower(t4h["phase"].astype(str))
        seen = set()
        # cue rows: rounds of 4 (FL, FR, RL, RR order of the probe); de-duplicate the copies
        samples = []
        for c in cue["cue"]:
            if c.get("is_reversed"):
                continue
            sig = (round(c["first_move_mid_force_N"], 3), round(c["extended_force_N"], 3))
            if sig in seen:
                continue
            seen.add(sig)
            samples.append(c)
        rnd_of = {}
        for n, c in enumerate(samples):
            leg = n % 4
            rnd = n // 4 + 1
            # rows of this leg inside a probe phase with a positive command block
            cand = np.flatnonzero(ph == "probe")
            im = [k for k in cand if abs(F[k, leg] - c["first_move_mid_force_N"]) < 1.0]
            ie = [k for k in cand if abs(F[k, leg] - c["extended_force_N"]) < 1.0]
            if not im or not ie:
                continue
            # choose the pair in the right order closest together
            pairs = [(a, b) for a in im for b in ie if 0 < b - a < 25]
            if not pairs:
                continue
            a, b = min(pairs, key=lambda p: p[1] - p[0])
            first_cmd = next((k for k in range(a, -1, -1) if cmd[k, leg] > 1e-9
                              and (k == 0 or cmd[k - 1, leg] <= 1e-9)), a)
            ia = int(np.argmin(np.abs(plant["t"] - t[a])))
            ib = int(np.argmin(np.abs(plant["t"] - t[b])))
            i0 = int(np.argmin(np.abs(plant["t"] - t[max(first_cmd - 1, 0)])))
            dF = c["extended_force_N"] - c["first_move_mid_force_N"]
            dx = c["extended_rod_stroke_m"] - c["first_move_mid_rod_stroke_m"]
            ds = float(plant["sref"][ib, leg] - plant["sref"][ia, leg])
            df = float(plant["f"][ib, leg] - plant["f"][ia, leg])
            Fs = float(plant["Fs"][ia, leg])
            ko = float(plant["ko"][ia, leg])
            k1 = c["stiffness_N_m"]
            s_nom = c["load_sensitivity_N_m"]
            kpad = (dF + df) / dx if dx else math.nan
            km = dF / ds if ds else math.nan
            f0 = float(plant["f"][i0, leg])
            rows.append({
                "run": run, "round": rnd, "leg": LEGS[leg],
                "t_first_cmd_s": round(float(t[first_cmd]), 2), "t_mid_s": round(float(t[a]), 2),
                "t_ext_s": round(float(t[b]), 2),
                "f0_before_kN": round(f0 / 1e3, 3), "Fs_kN": round(Fs / 1e3, 3),
                "band_to_cross_kN": round((Fs + f0) / 1e3, 3),
                "f_mid_kN": round(float(plant["f"][ia, leg]) / 1e3, 3),
                "f_ext_kN": round(float(plant["f"][ib, leg]) / 1e3, 3),
                "x_moved_by_mid_mm": round(float(plant["x"][ia, leg] - plant["x"][i0, leg]) * 1e3, 4),
                "dF_kN": round(dF / 1e3, 3), "dx_mm": round(dx * 1e3, 4), "dsref_mm": round(ds * 1e3, 4),
                "dseal_kN": round(df / 1e3, 3),
                "K1_MN_m": round(k1 / 1e6, 3), "Kpad_MN_m": round(kpad / 1e6, 3),
                "Kband_MN_m": round((-df / dx) / 1e6, 3) if dx else None,
                "Km_MN_m": round(km / 1e6, 3), "ko_MN_m": round(ko / 1e6, 3),
                "K1_from_Km_MN_m": round(1.0 / (1.0 / km - 1.0 / ko) / 1e6, 3) if km else None,
                "amplification_dK1_dKm": round(1.0 / (1.0 - km / ko), 3) if km else None,
                "ratio_K1": round(k1 / s_nom, 3), "ratio_Kpad": round(kpad / s_nom, 3),
                "Sii_nom_MN_m": round(s_nom / 1e6, 3)})
    fields = list(rows[0].keys())
    with (OUT / "d05_d1_k1_decomposition.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    # per round medians (the controller's raw ratio) and with K_pad
    med = {}
    for r in rows:
        med.setdefault((r["run"], r["round"]), []).append(r)
    summary = []
    for (run, rnd), rs in med.items():
        if len(rs) == 4:
            summary.append({"run": run, "round": rnd,
                            "median_ratio_K1": round(float(np.median([r["ratio_K1"] for r in rs])), 3),
                            "median_ratio_Kpad": round(float(np.median([r["ratio_Kpad"] for r in rs])), 3),
                            "ratios_K1": [r["ratio_K1"] for r in rs],
                            "ratios_Kpad": [r["ratio_Kpad"] for r in rs]})
    (OUT / "d05_d1_k1_decomposition.json").write_text(
        json.dumps({"rows": rows, "round_medians": summary}, indent=1), encoding="utf-8")
    for r in rows:
        print(r["run"][-22:], r["round"], r["leg"], "f0", r["f0_before_kN"], "band", r["band_to_cross_kN"],
              "fmid", r["f_mid_kN"], "xmid", r["x_moved_by_mid_mm"], "K1", r["K1_MN_m"], "Kpad",
              r["Kpad_MN_m"], "Kband", r["Kband_MN_m"], "Km", r["Km_MN_m"], "chk", r["K1_from_Km_MN_m"],
              "amp", r["amplification_dK1_dKm"], "rK1", r["ratio_K1"], "rKpad", r["ratio_Kpad"])
    for s in summary:
        print(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
