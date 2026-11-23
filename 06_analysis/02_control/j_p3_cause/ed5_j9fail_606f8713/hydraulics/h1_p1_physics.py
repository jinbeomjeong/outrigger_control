"""P1 (M1c line_fill_gate) physics review of the j9_main 606f8713 failure (hydraulics-expert).

Read only: stored j9_main.jsonl / T4h of run 606f8713 and the repository function
``check_open_delay.retract_dead`` (imported, not changed). No simulation is run.

Parts (outputs in this folder, h1_*.json):
  A  steady release threshold of a locked leg (VN neutral drain balance), extension and retract,
     sensitivity to c_v, n_f, psi, p_crack, p_h
  B  retract dead stroke of the loaded legs in the R12 events (P1 fill log of the VBJ rows):
     parts line / rod chamber / head creep / void, time at the delivered speed, sensitivity
  C  rod pressure rise of the locked unloading leg: closed form (two trapped chambers, beta free)
     against the T4h truth reading (P4) of the VBJ rows
  D  old VB plant: rod pressure dump at the micro retract release, force it frees
     (A_ann (p_r,peak - p_T)) against Fmin VB - VBJ (a2_r12_mechanism.csv)
  E  opening time of a locked leg at small constant commands with the repository
     ``CheckOpenGate`` (constant inputs, open loop): c_v 0.02 / 0.002, volume_scale 1 / 0.5

Conventions: pressures gauge [Pa] inside, bar(g) in the outputs; stroke and speed m, m/s inside,
mm, mm/s in the outputs; extension positive. All valve and line values are ASSUMPTIONS of the
plant (``CheckValveValues``: Q-M9, V-6).
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control")
sys.path.insert(0, str(ROOT / "03_src"))
from outrigger_sim.hydraulics.check_open_delay import RetractConfig, retract_dead  # noqa: E402

OUT = Path(__file__).resolve().parent
RUN = ROOT / "06_analysis" / "02_control" / "j_p3_cause" / "j9_runs" / "606f8713" / "j9main_a1"
A2_CSV = OUT.parent / "a2_r12_mechanism.csv"
LEGS = ("FL", "FR", "RL", "RR")
A_H = np.array([0.0132732289, 0.0132732289, 0.0095033178, 0.0095033178])  # m2, YAML
A_ANN = np.array([0.00376991118, 0.00376991118, 0.00314159265, 0.00314159265])  # m2, YAML
V_MAX = 0.0209243016  # m/s, YAML actuator.max_speed_m_s
S_MAX = 0.70  # m
L0H = 0.05  # m, YAML oil_dead_length_m (harness params.L0h)
L0R = 0.05  # m, YAML rod_dead_length_m
BETA = 1.0e9  # Pa, YAML oil_bulk_modulus_eff_Pa
P_T = 2.0e5  # Pa(g), flow-share ASSUMPTION
DP_C = 10.0e5  # Pa, compensator drop ASSUMPTION
NOMINAL = {"v_line_m3": 285e-6, "beta_hose_Pa": 0.5e9, "psi": 3.5, "p_crack_Pa": 3e5,
           "n_f": 0.05, "c_v": 0.02}
BAR = 1e5


def release_threshold(p_open_minus_pT_Pa: float, area_ratio: float, c_v: float, n_f: float) -> float:
    """Steady speed ratio r = |u| / v_max below which a locked leg never opens (VN drain).

    Fill flow A |u| against the neutral drain K_n g sqrt(p - p_T), K_n = n_f A_h v_max / sqrt(dp_c),
    g = (1 - r / c_v)+. Extension: A = A_h (area_ratio 1). Retract: A = A_ann (area_ratio phi):
    r = n_f k S (1 - r / c_v), S = sqrt((p_open - p_T) / dp_c), k = area_ratio
    -> r = n_f k S / (1 + n_f k S / c_v).
    """
    s_ = math.sqrt(max(p_open_minus_pT_Pa, 0.0) / DP_C)
    x = n_f * area_ratio * s_
    return x / (1.0 + x / c_v)


def part_a() -> dict:
    """Release thresholds (mm/s) over p_h and the valve values."""
    out = {"definition": "steady VN drain balance; extension opening p_A = p_h + p_cr - psi p_T "
                         "(rod check released, p_B ~ p_T); retract opening p_B = (p_h + p_cr - p_T)/psi",
           "extension": [], "retract_front": [], "retract_rear": []}
    grid = [(c_v, n_f, psi, pcr) for c_v in (0.005, 0.01, 0.02, 0.04) for n_f in (0.025, 0.05, 0.10)
            for psi in (3.5,) for pcr in (3e5,)]
    grid += [(0.02, 0.05, psi, 3e5) for psi in (3.0, 4.2, 6.0)]
    grid += [(0.02, 0.05, 3.5, pcr) for pcr in (1e5, 5e5)]
    for c_v, n_f, psi, pcr in grid:
        for p_h_bar in (10, 30, 60, 90, 130):
            p_h = p_h_bar * BAR
            p_a = p_h + pcr - psi * P_T
            r_e = release_threshold(p_a - P_T, 1.0, c_v, n_f)
            p_b = (p_h + pcr - P_T) / psi
            row = {"c_v": c_v, "n_f": n_f, "psi": psi, "p_crack_bar": pcr / BAR, "p_h_bar": p_h_bar}
            out["extension"].append({**row, "r_pct": round(100 * r_e, 4),
                                     "u_mm_s": round(r_e * V_MAX * 1e3, 4)})
            for name, leg in (("retract_front", 0), ("retract_rear", 2)):
                phi = A_H[leg] / A_ANN[leg]
                r_r = release_threshold(p_b - P_T, phi, c_v, n_f)
                out[name].append({**row, "r_pct": round(100 * r_r, 4),
                                  "u_mm_s": round(r_r * V_MAX * 1e3, 4)})
    return out


def need_parts(values: dict, p_h, p_r, band, s, void, leg, beta=BETA, l0r=L0R, l0h=L0H) -> dict:
    """retract_dead and its parts (mm of stroke) for one leg."""
    cfg = RetractConfig(rod_forward=True, volume_scale=1.0, v_line_m3=values["v_line_m3"],
                        beta_hose_Pa=values["beta_hose_Pa"], psi=values["psi"],
                        p_crack_Pa=values["p_crack_Pa"])
    r = retract_dead(cfg, p_h, p_r, band, s, void, A_H[leg], A_ANN[leg], S_MAX, l0r, l0h, beta, P_T)
    a_h, a_ann = A_H[leg], A_ANN[leg]
    line = values["v_line_m3"] * max(r["p_open"] - P_T, 0.0) / values["beta_hose_Pa"] / a_ann
    rod = (l0r + S_MAX - s) * (r["p_rod"] - p_r) / beta
    head = a_ann * a_h * (l0h + s) * r["dp_h"] / (beta * a_h) / a_ann
    return {"need_mm": r["need"] * 1e3, "line_mm": line * 1e3, "rod_mm": rod * 1e3,
            "head_mm": head * 1e3, "void_mm": void * 1e3, "p_open_bar": r["p_open"] / BAR,
            "p_rod_bar": r["p_rod"] / BAR, "dp_h_bar": r["dp_h"] / BAR,
            "creep_ref_mm": r["creep_ref"] * 1e3}


def load_rows(setting: str) -> list[dict]:
    rows = []
    with open(RUN / "j9_main.jsonl", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if (d.get("job") or {}).get("setting") == setting:
                rows.append(d)
    return rows


def part_b(vbj: list[dict]) -> dict:
    """Retract fills of the loaded legs opened in [t_ev, t_ev + 3 s] of the R12 VBJ rows."""
    recs = []
    for d in vbj:
        if not d["t4h_file"].startswith("R12"):
            continue
        t_ev = float(d["t_event_s"])
        z = np.load(RUN / "j9_main_t4h" / d["t4h_file"], allow_pickle=False)
        t = z["t_s"]
        g = d["hydraulics_record"]["line_fill_gate"]
        for f in g["fills"]:
            start, t_open, leg, direction, need_mm, p_h_bar, p_r_bar, void_mm = f[:8]
            if direction != -1 or not (t_ev <= t_open <= t_ev + 3.0) or p_h_bar < 60:
                continue
            m = (t > start - 1e-9) & (t <= t_open + 1e-9)
            u = z["command_m_s"][m, leg]
            delivered_mm = float(np.sum(-np.minimum(u, 0.0)) * 0.1 * 1e3)  # 10 Hz reads, command
            i_open = int(np.searchsorted(t, t_open))
            s = float(z["motor_stroke_m"][min(i_open, len(t) - 1), leg])
            band = float(z["seal_band_N"][min(i_open, len(t) - 1), leg])
            parts = need_parts(NOMINAL, p_h_bar * BAR, p_r_bar * BAR, band, s, void_mm * 1e-3, leg)
            sens = {}
            for name, change in (("psi_3.0", {"psi": 3.0}), ("psi_4.2", {"psi": 4.2}),
                                 ("psi_6.0", {"psi": 6.0}),
                                 ("beta_hose_0.3", {"beta_hose_Pa": 0.3e9}),
                                 ("beta_hose_1.0", {"beta_hose_Pa": 1.0e9}),
                                 ("v_line_x0.5", {"v_line_m3": 142.5e-6}),
                                 ("v_line_x2", {"v_line_m3": 570e-6})):
                sens[name] = round(need_parts({**NOMINAL, **change}, p_h_bar * BAR, p_r_bar * BAR,
                                              band, s, void_mm * 1e-3, leg)["need_mm"], 4)
            for name, kw in (("beta_0.69", {"beta": 0.69e9}), ("beta_1.6", {"beta": 1.6e9}),
                             ("L0r_0.02", {"l0r": 0.02}), ("L0r_0.10", {"l0r": 0.10}),
                             ("L0h_0.08", {"l0h": 0.08})):
                sens[name] = round(need_parts(NOMINAL, p_h_bar * BAR, p_r_bar * BAR, band, s,
                                              void_mm * 1e-3, leg, **kw)["need_mm"], 4)
            sens["void_0"] = round(parts["need_mm"] - parts["void_mm"], 4)
            recs.append({"key": d["t4h_file"].rsplit("_", 1)[0], "leg": LEGS[leg],
                         "fill_start_s": start, "open_s": t_open,
                         "delay_s": round(t_open - start, 3), "need_log_mm": need_mm,
                         "p_h_bar": p_h_bar, "p_r_bar": p_r_bar, "void_mm": void_mm,
                         "s_mm": round(s * 1e3, 1), "band_kN": round(band / 1e3, 3),
                         "cmd_integral_mm": round(delivered_mm, 3),
                         **{k: round(v, 4) for k, v in parts.items()},
                         "t_at_5p5_mm_s": round(parts["need_mm"] / 5.5, 3),
                         "t_at_vmax": round(parts["need_mm"] / (V_MAX * 1e3), 3),
                         "need_sens_mm": sens})
    keys = ["need_mm", "line_mm", "rod_mm", "head_mm", "void_mm", "delay_s", "p_open_bar",
            "p_rod_bar", "t_at_5p5_mm_s", "t_at_vmax", "cmd_integral_mm"]
    summ = {k: {"min": round(min(r[k] for r in recs), 3),
                "median": round(float(np.median([r[k] for r in recs])), 3),
                "max": round(max(r[k] for r in recs), 3)} for k in keys}
    sens_keys = recs[0]["need_sens_mm"].keys()
    summ["need_sens_ratio_median"] = {
        k: round(float(np.median([r["need_sens_mm"][k] / r["need_mm"] for r in recs])), 3)
        for k in sens_keys}
    summ["n"] = len(recs)
    summ["need_log_vs_recomputed_max_abs_mm"] = round(max(abs(r["need_log_mm"] - r["need_mm"])
                                                          for r in recs), 4)
    return {"rows": recs, "summary": summ}


def k_split(leg: int, s: float, l0r: float = L0R, l0h: float = L0H) -> float:
    """k_r / (k_h + k_r) of a locked leg (beta cancels)."""
    k_h = A_H[leg] / (l0h + s)
    k_r = A_ANN[leg] / (l0r + S_MAX - s)
    return k_r / (k_h + k_r)


def part_c(vbj: list[dict]) -> dict:
    """Rod rise of the unloading locked leg: dp_r = -dF k_r / ((k_h + k_r) A_ann)."""
    with open(A2_CSV, encoding="utf-8") as f:
        a2 = {r["key"]: r for r in csv.DictReader(f)}
    recs = []
    for d in vbj:
        key = d["t4h_file"].rsplit("_", 1)[0]
        if key not in a2:
            continue
        leg = LEGS.index(a2[key]["leg"])
        t_ev = float(d["t_event_s"])
        z = np.load(RUN / "j9_main_t4h" / d["t4h_file"], allow_pickle=False)
        t = z["t_s"]
        w = np.flatnonzero((t >= t_ev - 1e-9) & (t <= t_ev + 5.0))
        lk = z["locked"][:, leg]
        f = z["true_force_N"][:, leg]
        pr = z["rod_pressure_Pa"][:, leg]
        i0 = w[0]
        # last read still locked before the first unlock in the window
        unl = w[~lk[w]]
        i1 = (unl[0] - 1) if len(unl) else w[-1]
        if not lk[i0] or i1 <= i0:
            continue
        s = float(z["motor_stroke_m"][i0, leg])
        dF = float(f[i1] - f[i0])
        pred = pr[i0] - dF * k_split(leg, s) / A_ANN[leg]
        lo = pr[i0] - dF * k_split(leg, s, l0r=0.10) / A_ANN[leg]
        hi = pr[i0] - dF * k_split(leg, s, l0r=0.02) / A_ANN[leg]
        recs.append({"key": key, "leg": LEGS[leg], "t0_s": float(t[i0]), "t1_s": float(t[i1]),
                     "s_mm": round(s * 1e3, 1), "dF_kN": round(dF / 1e3, 2),
                     "p_r0_bar": round(pr[i0] / BAR, 2), "p_r1_T4h_bar": round(pr[i1] / BAR, 2),
                     "p_r1_closed_bar": round(pred / BAR, 2),
                     "p_r1_closed_L0r_0.10_bar": round(lo / BAR, 2),
                     "p_r1_closed_L0r_0.02_bar": round(hi / BAR, 2),
                     "split": round(k_split(leg, s), 4)})
    diff = [r["p_r1_T4h_bar"] - r["p_r1_closed_bar"] for r in recs]
    return {"rows": recs, "summary": {"n": len(recs),
                                      "T4h_minus_closed_bar": {"min": round(min(diff), 2),
                                                               "median": round(float(np.median(diff)), 2),
                                                               "max": round(max(diff), 2)}}}


def part_d() -> dict:
    """Old VB: the rod dump at the micro retract release frees A_ann (p_r,peak - p_T)."""
    with open(A2_CSV, encoding="utf-8") as f:
        a2 = list(csv.DictReader(f))
    recs = []
    for r in a2:
        leg = LEGS.index(r["leg"])
        dump = A_ANN[leg] * (float(r["pr_max_to_min_bar_VB"]) - 2.0) * BAR / 1e3
        gap = float(r["Fmin_kN_VB"]) - float(r["Fmin_kN_VBJ"])
        recs.append({"key": r["key"], "leg": r["leg"], "pr_peak_VB_bar": float(r["pr_max_to_min_bar_VB"]),
                     "dump_force_kN": round(dump, 2), "Fmin_VB_minus_VBJ_kN": round(gap, 2),
                     "Fmin_VB_kN": float(r["Fmin_kN_VB"]),
                     "Fmin_VB_minus_dump_kN": round(float(r["Fmin_kN_VB"]) - dump, 2)})
    def agg(k):
        v = [x[k] for x in recs]
        return {"min": round(min(v), 2), "median": round(float(np.median(v)), 2), "max": round(max(v), 2)}
    return {"rows": recs, "summary": {"n": len(recs), "dump_force_kN": agg("dump_force_kN"),
                                      "Fmin_VB_minus_VBJ_kN": agg("Fmin_VB_minus_VBJ_kN"),
                                      "Fmin_VB_minus_dump_kN": agg("Fmin_VB_minus_dump_kN"),
                                      "corr": round(float(np.corrcoef(
                                          [x["dump_force_kN"] for x in recs],
                                          [x["Fmin_VB_minus_VBJ_kN"] for x in recs])[0, 1]), 3)}}


def open_time(direction: int, leg: int, u_m_s: float, p_h: float, p_r: float, c_v: float,
              scale: float = 1.0, void_m: float = 0.0, s_ref: float = 0.396,
              t_max: float = 20.0) -> float | None:
    """Time [s] from an empty line to the opening of a locked leg at a constant command, with the
    repository ``CheckOpenGate`` (1 ms chunks, constant pressures, band 0). None = not by t_max."""
    from outrigger_sim.hydraulics.check_open_delay import (CheckDelayCircuit, CheckDelayInputs,
                                                           CheckOpenGate)
    from outrigger_sim.hydraulics.v5_options import CheckDelaySetting
    circuit = CheckDelayCircuit(head_area_m2=A_H, annulus_area_m2=A_ANN, stroke_m=S_MAX,
                                rod_dead_length_m=L0R, head_dead_length_m=L0H, bulk_modulus_Pa=BETA,
                                tank_pressure_Pa=P_T, max_speed_m_s=V_MAX, compensator_drop_Pa=DP_C)
    gate = CheckOpenGate(CheckDelaySetting(kind="VN", volume_scale=scale, c_v=c_v), circuit)
    dt = 1e-3
    u = np.zeros(4)
    u[leg] = direction * u_m_s
    ph = np.full(4, p_h)
    pr = np.full(4, p_r)
    void = np.zeros(4)
    void[leg] = void_m
    for k in range(int(t_max / dt)):
        out = gate.filter(CheckDelayInputs(k * dt, dt, u, ph, pr, np.ones(4, bool), void,
                                           np.zeros(4), np.full(4, s_ref)))
        if out.speed_m_s[leg] != 0.0:
            return round((k + 1) * dt, 3)
    return None


def part_e() -> dict:
    """Opening time of a locked leg at small constant commands: c_v 0.02 (nominal) / 0.002 and
    volume_scale 1 / 0.5. Cases: loaded leg extension (p_h 90 bar, p_r 5 bar), unloading leg
    extension after the locked rod rise (p_h 30, p_r 63), loaded leg retract (p_h 122, p_r floor,
    void 1.2 mm, the R12 FR fill), light leg retract (p_h 30, p_r 5)."""
    cases = [("ext_loaded_ph90_pr5", 1, 90e5, 5e5, 0.0), ("ext_unloading_ph30_pr63", 1, 30e5, 63e5, 0.0),
             ("ret_loaded_ph122_floor_void1.2", -1, 122e5, -0.91325e5, 1.2e-3),
             ("ret_light_ph30_pr5", -1, 30e5, 5e5, 0.0)]
    rows = []
    for name, direction, p_h, p_r, void in cases:
        for leg in (0, 2):
            for u_mm in (0.1, 0.25, 0.35, 0.45, 1.0, 5.5, V_MAX * 1e3):
                row = {"case": name, "leg": LEGS[leg], "u_mm_s": round(u_mm, 3)}
                for c_v, scale in ((0.02, 1.0), (0.002, 1.0), (0.02, 0.5), (0.002, 0.5)):
                    row[f"t_cv{c_v}_vs{scale}"] = open_time(direction, leg, u_mm * 1e-3, p_h, p_r,
                                                            c_v, scale, void)
                rows.append(row)
    return {"rows": rows, "note": "None = not open within 20 s (steady drain balance or slower)"}


def main() -> None:
    vbj = load_rows("VBJ")
    res = {"A_release_threshold": part_a(), "B_retract_dead_stroke": part_b(vbj),
           "C_locked_rod_rise": part_c(vbj), "D_old_vb_rod_dump": part_d(),
           "E_open_time_small_commands": part_e(),
           "assumptions": {**NOMINAL, "beta_Pa": BETA, "L0r_m": L0R, "L0h_m": L0H,
                           "p_T_Pa_gauge": P_T, "dp_c_Pa": DP_C, "v_max_m_s": V_MAX}}
    with open(OUT / "h1_p1_physics.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: v["summary"] for k, v in res.items() if isinstance(v, dict) and "summary" in v},
                     indent=1))


if __name__ == "__main__":
    main()
