"""Edition 9 design input: D1'' time component (instant pressure vs IMU window) on a real chain.

Analysis only (no project simulation). hydraulics-expert, 2026-11-28.

What it does
1. Fits a power-law load-drop surrogate d(t) = -F0 (t/T_u)^n (0 <= t <= T_u, lift at T_u) to the
   harness boundary sweep (diag2 sweep_summary.csv, pre-lift samples only, where the lever
   term is small), using the harness chain: instant pressure vs 10 ms box IMU mean ending at t_k.
2. Adds the physics that the harness leaves out (rod + piston + pad mass between the oil
   column and the floor, head-side void floor, seal Coulomb friction), and the measurement
   chains of a real machine (sensor-block passage delay, transducer lag, ADC filter, IMU
   internal filter, timestamp offset).
3. Evaluates the time component r_time(t_k) = P_chain[F_oil](t_k) - IMU_chain[F_body](t_k) over
   sample phase t_k - t_lift in [-10, +40] ms, for the instant-sample rule and for C-b
   (pressure averaged over the same window as the IMU).

All forces are changes from the pre-event static state (N); pressures are gauge.
Outputs (next to this script): pressure_sampling_cases.csv, pressure_sampling_phase.csv,
pressure_sampling_basis.json.

Run: conda run -n hydraulics-dev python -I -B calc_pressure_sampling.py
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy import optimize, signal

HERE = Path(__file__).resolve().parent
SWEEP = (
    HERE.parent.parent
    / "ed8_design"
    / "stage5_aa_diag"
    / "diag2"
    / "sweep_summary.csv"
)

# ----------------------------------------------------------------------------- parameters
BETA = 1.0e9  # Pa, project base (YAML actuator.oil_bulk_modulus_eff_Pa); sensitivity 0.69-1.6 GPa
RHO = 860.0  # kg/m3, ASSUMPTION: mineral oil ISO VG 46 at about 50 C (grade not confirmed, H-1)
NU = 30e-6  # m2/s, ASSUMPTION: VG 46 at about 50 C
FRONT = {
    "A_p": 1.3273e-2,  # m2, hydraulic_circuit.md 4.1
    "A_ann": 3.770e-3,
    "m_rod": 106.78,  # kg, moving part (rod + piston + pad), C-10 unconfirmed
    "e": 0.4015,  # m, operating extension (assumption in hydraulic_circuit.md 7.4)
    "stroke": 0.70,
    "L0h": 0.05,
    "L0r": 0.05,
}
K_GROUND = 5.0e8  # N/m, ASSUMPTION: pad + concrete contact stiffness (only shapes the pre-lift rod lag)
ZETA_ROD = 0.05  # ASSUMPTION: viscous damping ratio of the rod-on-oil local mode
THRESH_N = 49.8e3  # N, adjacent rear-leg threshold in J1 (0.5 |dp_h| A_p), sweep_summary.csv
THRESH_MIN_N = 47.8e3  # N, smallest threshold seen in the 7 jobs (diag_interpretation 1.1)
WINDOW = 0.010  # s, IMU partial mean (100 Hz path)
DT = 1.0e-5  # s, analysis grid

A_WAVE = math.sqrt(BETA / RHO)


def k_oil(leg: dict) -> tuple[float, float]:
    k_h = BETA * leg["A_p"] / (leg["L0h"] + leg["e"])
    k_r = BETA * leg["A_ann"] / (leg["stroke"] - leg["e"] + leg["L0r"])
    return k_h, k_r


# ----------------------------------------------------------------------------- signals
def drop_shape(t: np.ndarray, f0: float, t_u: float, n: float) -> np.ndarray:
    """Event-leg force change of the massless harness leg (N, negative = unloading)."""
    g = np.clip(t / t_u, 0.0, 1.0) ** n
    g[t < 0.0] = 0.0
    return -f0 * g


def box_mean_end(t: np.ndarray, x: np.ndarray, t_end: np.ndarray, width: float) -> np.ndarray:
    """Mean of x over (t_end - width, t_end], trapezoid cumulative integral."""
    c = np.concatenate([[0.0], np.cumsum(0.5 * (x[1:] + x[:-1]) * np.diff(t))])
    hi = np.interp(t_end, t, c)
    lo = np.interp(t_end - width, t, c)
    return (hi - lo) / width


def first_order(t: np.ndarray, x: np.ndarray, tau: float) -> np.ndarray:
    if tau <= 0.0:
        return x.copy()
    a = math.exp(-(t[1] - t[0]) / tau)
    y = np.empty_like(x)
    y[0] = x[0]
    for i in range(1, x.size):
        y[i] = a * y[i - 1] + (1.0 - a) * x[i]
    return y


def butter2(t: np.ndarray, x: np.ndarray, fc: float) -> np.ndarray:
    b, a = signal.butter(2, 2.0 * math.pi * fc, analog=True)
    # signal starts at rest (x = 0 before the event), so shifting the time origin is exact
    _, y, _ = signal.lsim((b, a), x, t - t[0])
    return y


def delay(t: np.ndarray, x: np.ndarray, tau: float) -> np.ndarray:
    return np.interp(t - tau, t, x, left=x[0])


# ----------------------------------------------------------------------------- rod physics
def rod_response(
    t: np.ndarray, d: np.ndarray, leg: dict, f0: float, f_seal: float, void_floor: bool
) -> tuple[np.ndarray, np.ndarray]:
    """Oil force change and body force change with a rod mass between oil and floor.

    body --k_oil-- rod mass m --k_ground (unilateral)-- floor moving down by z(t).
    z(t) is chosen so the massless limit reproduces the harness force d(t).
    Returns (F_oil change, F_body change), both N, upward on the body positive.
    """
    k_h, k_r = k_oil(leg)
    k_o = k_h + k_r
    m = leg["m_rod"]
    k_s = k_o * K_GROUND / (k_o + K_GROUND)
    z = -d / k_s  # floor drop, m (massless mapping, t <= T_u)
    i_lift = int(np.argmax(d <= -f0 * (1.0 - 1e-12)))
    if i_lift > 0:  # keep the floor moving down after lift at the end speed
        vz = (z[i_lift] - z[i_lift - 1]) / (t[i_lift] - t[i_lift - 1])
        z[i_lift:] = z[i_lift] + vz * (t[i_lift:] - t[i_lift])
    omega = math.sqrt(k_o / m)
    c_v = 2.0 * ZETA_ROD * omega * m
    x = 0.0  # rod extension (down) from the static state, m
    v = 0.0
    x0 = f0 / k_o  # extension where the oil force change reaches -F0 (pressure ~ the static zero)
    f_oil = np.zeros_like(t)
    f_body = np.zeros_like(t)
    dt = t[1] - t[0]
    sub = 10
    h = dt / sub
    for i in range(t.size):
        zi = z[i]
        for _ in range(sub):
            if void_floor and x > x0:
                fo = -f0 - k_r * (x - x0)  # head side in void: only the rod side springs
            else:
                fo = -k_o * x
            # contact force change (unilateral): static F0 + change
            fc_total = f0 - K_GROUND * (zi - x)
            fc = max(fc_total, 0.0) - f0
            fs = f_seal * math.tanh(v / 1e-3)
            # downward positive for the rod: oil pushes down by (F0 + fo), ground up by (F0 + fc)
            acc = ((f0 + fo) - (f0 + fc) - fs - c_v * v) / m
            v += h * acc
            x += h * v
        f_oil[i] = fo
        f_body[i] = fo + fs + c_v * v  # reaction of seal friction and damping on the barrel
    return f_oil, f_body


# ----------------------------------------------------------------------------- chains
def evaluate(
    t: np.ndarray,
    f_p: np.ndarray,
    f_b: np.ndarray,
    t_lift: float,
    *,
    tau_line: float,
    tau_sensor: float,
    adc: str,
    imu: str,
    ts_offset: float,
    rule: str,
) -> dict:
    """Time component over sample phase. ts_offset > 0: the IMU window ends ts_offset before t_k."""
    p = delay(t, f_p, tau_line)
    p = first_order(t, p, tau_sensor)
    if adc == "rc_1p6ms":
        p = first_order(t, p, 1.6e-3)
    elif adc == "box_20ms":
        p_int = p
    if imu == "box10":
        imu_sig = f_b
    elif imu.startswith("bw2_"):
        imu_sig = butter2(t, f_b, float(imu.split("_")[1]))
    elif imu.startswith("fo_"):
        imu_sig = first_order(t, f_b, 1.0 / (2.0 * math.pi * float(imu.split("_")[1])))
    else:
        raise ValueError(imu)
    phase = np.arange(-10.0e-3, 40.0e-3 + 1e-12, 0.25e-3)
    tk = t_lift + phase
    t_imu = tk - ts_offset
    if imu == "box10":
        imu_val = box_mean_end(t, imu_sig, t_imu, WINDOW)
    else:
        imu_val = np.interp(t_imu, t, imu_sig)
    if rule == "instant":
        if adc == "box_20ms":
            p_val = box_mean_end(t, p_int, tk, 0.020)
        else:
            p_val = np.interp(tk, t, p)
    elif rule == "cb_box":  # pressure averaged over the window the controller believes the IMU used
        p_val = box_mean_end(t, p, tk, WINDOW)
    elif rule == "cb_rc5":  # analog/digital first-order 5 ms (same low-frequency group delay)
        p_val = np.interp(tk, t, first_order(t, p, 5.0e-3))
    elif rule == "cb_matched":  # pressure through the same filter as the IMU (bw2 / fo)
        if imu.startswith("bw2_"):
            p_m = butter2(t, p, float(imu.split("_")[1]))
        elif imu.startswith("fo_"):
            p_m = first_order(t, p, 1.0 / (2.0 * math.pi * float(imu.split("_")[1])))
        else:
            return {}
        p_val = np.interp(tk, t, p_m)
    else:
        raise ValueError(rule)
    r = p_val - imu_val
    above = np.abs(r) >= THRESH_N
    above_min = np.abs(r) >= THRESH_MIN_N
    step = 0.25
    return {
        "phase_ms": phase * 1e3,
        "r": r,
        "peak_abs_kN": float(np.max(np.abs(r)) / 1e3),
        "peak_phase_ms": float(phase[int(np.argmax(np.abs(r)))] * 1e3),
        "window_ms_thr49p8": float(above.sum() * step),
        "window_ms_thr47p8": float(above_min.sum() * step),
        "ratio_peak": float(np.max(np.abs(r)) / THRESH_N),
    }


# ----------------------------------------------------------------------------- fit
def read_sweep() -> dict[str, list[tuple[float, float]]]:
    out: dict[str, list[tuple[float, float]]] = {}
    with SWEEP.open(newline="") as fh:
        for row in csv.DictReader(fh):
            out.setdefault(row["shape"], []).append(
                (float(row["prev_sample_minus_lift_ms"]), float(row["residual_change_kN"]))
            )
    return out


def harness_curve(f0: float, t_u: float, n: float, phases_ms: np.ndarray) -> np.ndarray:
    t = np.arange(-0.05, 0.08, DT)
    d = drop_shape(t, f0, t_u, n)
    tk = t_u + phases_ms * 1e-3
    return np.abs(np.interp(tk, t, d) - box_mean_end(t, d, tk, WINDOW))


def fit_shape(points: list[tuple[float, float]], t_u: float) -> dict:
    pre = [(p, v) for p, v in points if -8.0 <= p <= 0.0]
    ph = np.array([p for p, _ in pre])
    obs = np.array([v for _, v in pre]) * 1e3

    def resid(x: np.ndarray) -> np.ndarray:
        return harness_curve(x[0], t_u, x[1], ph) - obs

    sol = optimize.least_squares(resid, x0=[112e3, 3.0], bounds=([30e3, 0.5], [200e3, 8.0]))
    res = resid(sol.x)
    return {
        "T_u_s": t_u,
        "F0_N": float(sol.x[0]),
        "n": float(sol.x[1]),
        "rms_kN": float(np.sqrt(np.mean(res**2)) / 1e3),
        "max_abs_kN": float(np.max(np.abs(res)) / 1e3),
        "points": [
            {"phase_ms": float(p), "obs_kN": float(o / 1e3), "fit_kN": float((o + e) / 1e3)}
            for p, o, e in zip(ph, obs, res, strict=True)
        ],
    }


# ----------------------------------------------------------------------------- main
def main() -> None:
    sweep = read_sweep()
    fits = {
        "J1shape_FR_30mm_0.04s": fit_shape(sweep["J1shape"], 0.013),
        "J3shape_FL_25mm_0.05s": fit_shape(sweep["J3shape"], 0.017),
    }
    k_h, k_r = k_oil(FRONT)
    omega_rod = math.sqrt((k_h + k_r) / FRONT["m_rod"])

    basis: dict = {
        "what": "D1'' time component on real chains, edition 9 design input (analysis, not a judgement)",
        "author": "hydraulics-expert 2026-11-28",
        "oil": {
            "grade": "ISO VG 46 (ASSUMPTION, H-1 unanswered)",
            "temp_C": 50,
            "rho_kg_m3": RHO,
            "nu_m2_s": NU,
            "beta_eff_Pa": BETA,
            "beta_note": "project base 1.0 GPa, sensitivity 0.69-1.6 GPa",
            "wave_speed_m_s": A_WAVE,
            "wave_speed_range_m_s": [math.sqrt(0.69e9 / RHO), math.sqrt(1.6e9 / RHO)],
        },
        "front_leg": {
            **FRONT,
            "k_h_N_m": k_h,
            "k_r_N_m": k_r,
            "rod_local_mode_Hz": omega_rod / (2 * math.pi),
            "rod_local_mode_Hz_head_only": math.sqrt(k_h / FRONT["m_rod"]) / (2 * math.pi),
            "rod_local_mode_Hz_beta_range": [
                math.sqrt(s * (k_h + k_r) / FRONT["m_rod"]) / (2 * math.pi) for s in (0.69, 1.6)
            ],
            "K_ground_N_m_ASSUMPTION": K_GROUND,
            "zeta_rod_ASSUMPTION": ZETA_ROD,
        },
        "fits": fits,
    }

    # line / sensor delays
    lines = {
        "production_block_short": 0.45 + 0.15,  # chamber column + block passage, m (L-3 unanswered)
        "photo_head_tube_long": 0.45 + 0.9,  # chamber + head tube upper estimate (hydraulic_circuit 7.4)
    }
    basis["line"] = {
        name: {
            "length_m": L,
            "one_way_delay_ms": L / A_WAVE * 1e3,
            "quarter_wave_Hz_closed_stub": A_WAVE / (4 * L),
        }
        for name, L in lines.items()
    }
    tube_only = {"head_tube_0.9m": 0.9, "block_0.15m": 0.15}
    basis["stub_quarter_wave_Hz"] = {k: A_WAVE / (4 * v) for k, v in tube_only.items()}

    # filter group delays and box response
    def box_gain(f: float) -> float:
        x = math.pi * f * WINDOW
        return abs(math.sin(x) / x) if x else 1.0

    basis["filters"] = {
        "box_10ms": {"group_delay_ms": 5.0, "f_3dB_Hz": 0.443 / WINDOW, "first_null_Hz": 1 / WINDOW},
        "box_10ms_gain": {f"{f}_Hz": box_gain(f) for f in (1, 2, 4, 8, 20, 44.3, 98, 150, 300)},
        "bw2_group_delay_ms_low_freq": {
            f"{fc}_Hz": math.sqrt(2.0) / (2 * math.pi * fc) * 1e3 for fc in (10, 25, 40, 50, 100)
        },
        "first_order_group_delay_ms_low_freq": {
            f"{fc}_Hz": 1 / (2 * math.pi * fc) * 1e3 for fc in (10, 25, 50, 100)
        },
        "wika_settling_lt_1ms_as_first_order_tau_ms": {
            "if_settling_is_10_90pct": 1.0 / math.log(9.0),
            "if_settling_is_to_1pct": 1.0 / math.log(100.0),
            "upper_bound_tau_eq_settling": 1.0,
            "2017_edition_lt_4ms_upper": 4.0,
        },
    }

    # Q1 pressure rates (fit J1)
    f1 = fits["J1shape_FR_30mm_0.04s"]
    f0, t_u, n = f1["F0_N"], f1["T_u_s"], f1["n"]
    dp_total_bar = f0 / FRONT["A_p"] / 1e5
    basis["q1_rates_front_J1fit"] = {
        "head_drop_bar_equiv": dp_total_bar,
        "mean_rate_bar_per_ms": dp_total_bar / (t_u * 1e3),
        "end_rate_bar_per_ms": n * dp_total_bar / (t_u * 1e3),
        "end_force_rate_kN_per_ms": n * f0 / t_u / 1e6,
        "note": "head-pressure equivalent of the net-force change (rod side ignored)",
        "stub_ringing_bound_bar": {
            name: n * dp_total_bar / (t_u * 1e3) * (L / A_WAVE * 1e3)
            for name, L in tube_only.items()
        },
        "stub_ringing_note": "order bound: end slope x one-way delay of the dead-end passage (chamber port to sensor), lossless, abrupt slope change",
        "sensor_lag_error_at_lift_bar": {
            f"tau_{tau}ms": n * dp_total_bar / (t_u * 1e3) * tau for tau in (0.25, 1.0, 4.0)
        },
    }

    # ---------------------------------------------------------------- cases
    t = np.arange(-0.05, 0.10, DT)
    t_lift = t_u
    d = drop_shape(t, f0, t_u, n)
    phys = {
        "massless_harness": (d, d),
        "rod_mass_Fs0": rod_response(t, d, FRONT, f0, 0.0, True),
        "rod_mass_Fs4kN": rod_response(t, d, FRONT, f0, 4.0e3, True),
    }
    fo_r, _ = phys["rod_mass_Fs0"]
    after = t >= t_lift
    ring = fo_r[after] - (-f0)
    basis["rod_ringing_Fs0"] = {
        "peak_to_peak_kN_first_20ms": float(
            (ring[: int(0.02 / DT)].max() - ring[: int(0.02 / DT)].min()) / 1e3
        ),
        "oil_force_at_lift_minus_massless_kN": float((fo_r[np.searchsorted(t, t_lift)] + f0) / 1e3),
    }

    case_defs = []
    # A harness reproduction
    case_defs.append(("A0 harness (massless, instant p, box IMU aligned)", "massless_harness", 0, 0, "none", "box10", 0, "instant"))
    # B physics only
    case_defs.append(("B1 + rod mass, Fs 0", "rod_mass_Fs0", 0, 0, "none", "box10", 0, "instant"))
    case_defs.append(("B2 + rod mass, Fs 4 kN", "rod_mass_Fs4kN", 0, 0, "none", "box10", 0, "instant"))
    # C pressure chain
    for tl_name, tl in (("short", basis["line"]["production_block_short"]["one_way_delay_ms"] / 1e3),
                        ("long", basis["line"]["photo_head_tube_long"]["one_way_delay_ms"] / 1e3)):
        for ts in (0.25e-3, 1.0e-3, 4.0e-3):
            case_defs.append((f"C line {tl_name} + sensor tau {ts*1e3:g} ms (rod mass Fs 0)", "rod_mass_Fs0", tl, ts, "none", "box10", 0, "instant"))
    case_defs.append(("C ADC RC 1.6 ms (100 Hz) + line short + tau 0.25", "rod_mass_Fs0",
                      basis["line"]["production_block_short"]["one_way_delay_ms"] / 1e3, 0.25e-3, "rc_1p6ms", "box10", 0, "instant"))
    case_defs.append(("C ADC 20 ms integration (50 Hz rejection) + line short + tau 0.25", "rod_mass_Fs0",
                      basis["line"]["production_block_short"]["one_way_delay_ms"] / 1e3, 0.25e-3, "box_20ms", "box10", 0, "instant"))
    # D IMU chain
    nominal_line = basis["line"]["production_block_short"]["one_way_delay_ms"] / 1e3
    for imu in ("box10", "bw2_50", "bw2_25", "fo_25", "bw2_10"):
        for off in (-5e-3, 0.0, 5e-3):
            case_defs.append((f"D IMU {imu}, ts offset {off*1e3:+g} ms (nominal p chain)", "rod_mass_Fs0", nominal_line, 0.25e-3, "none", imu, off, "instant"))
    # E C-b
    for off in (-5e-3, -2e-3, -1e-3, 0.0, 1e-3, 2e-3, 5e-3):
        case_defs.append((f"E C-b box, IMU box10, ts offset {off*1e3:+g} ms", "rod_mass_Fs0", nominal_line, 0.25e-3, "none", "box10", off, "cb_box"))
    case_defs.append(("E C-b box, harness massless, ideal chains", "massless_harness", 0, 0, "none", "box10", 0, "cb_box"))
    case_defs.append(("E C-b box, sensor tau 4 ms, long line", "rod_mass_Fs0",
                      basis["line"]["photo_head_tube_long"]["one_way_delay_ms"] / 1e3, 4e-3, "none", "box10", 0, "cb_box"))
    case_defs.append(("E C-b box, Fs 4 kN (seal term only)", "rod_mass_Fs4kN", nominal_line, 0.25e-3, "none", "box10", 0, "cb_box"))
    for imu in ("bw2_50", "bw2_25", "fo_25"):
        case_defs.append((f"E C-b box but IMU is {imu} (shape mismatch)", "rod_mass_Fs0", nominal_line, 0.25e-3, "none", imu, 0, "cb_box"))
        case_defs.append((f"E C-b matched filter (pressure through {imu})", "rod_mass_Fs0", nominal_line, 0.25e-3, "none", imu, 0, "cb_matched"))
    case_defs.append(("E C-b first-order 5 ms instead of box (IMU box10)", "rod_mass_Fs0", nominal_line, 0.25e-3, "none", "box10", 0, "cb_rc5"))

    rows = []
    phase_rows: dict[str, np.ndarray] = {}
    for label, ph_key, tl, ts, adc, imu, off, rule in case_defs:
        fp, fb = phys[ph_key]
        res = evaluate(t, fp, fb, t_lift, tau_line=tl, tau_sensor=ts, adc=adc, imu=imu, ts_offset=off, rule=rule)
        if not res:
            continue
        rows.append({
            "case": label,
            "physics": ph_key,
            "line_delay_ms": round(tl * 1e3, 4),
            "sensor_tau_ms": ts * 1e3,
            "adc": adc,
            "imu_chain": imu,
            "ts_offset_ms": off * 1e3,
            "rule": rule,
            "peak_abs_kN": round(res["peak_abs_kN"], 2),
            "peak_phase_ms": res["peak_phase_ms"],
            "ratio_peak_to_49p8kN": round(res["ratio_peak"], 3),
            "fault_window_ms_thr49p8": res["window_ms_thr49p8"],
            "fault_window_ms_thr47p8": res["window_ms_thr47p8"],
            "fault_window_pct_of_100ms": round(res["window_ms_thr49p8"], 2),
        })
        phase_rows[label] = res["r"] / 1e3
        phase_axis = res["phase_ms"]

    with (HERE / "pressure_sampling_cases.csv").open("w", newline="\n", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    keep = [k for k in phase_rows if k.startswith(("A0", "B1", "B2", "D IMU box10, ts offset +0", "D IMU bw2_25, ts offset +0", "E C-b box, IMU box10, ts offset +0", "E C-b box, IMU box10, ts offset +2"))]
    with (HERE / "pressure_sampling_phase.csv").open("w", newline="\n", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["phase_ms_tk_minus_lift"] + [f"r_time_kN | {k}" for k in keep])
        for i, p in enumerate(phase_axis):
            w.writerow([f"{p:.2f}"] + [f"{phase_rows[k][i]:.3f}" for k in keep])

    # allowable residual misalignment for C-b with harness-like slope (instant-free)
    allow = {}
    for target in (0.25, 0.5):
        lo, hi = 0.0, 0.02
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            res = evaluate(t, phys["rod_mass_Fs0"][0], phys["rod_mass_Fs0"][1], t_lift,
                           tau_line=0.0, tau_sensor=0.0, adc="none", imu="box10", ts_offset=mid, rule="cb_box")
            if res["peak_abs_kN"] * 1e3 > target * THRESH_N:
                hi = mid
            else:
                lo = mid
        allow[f"ts_offset_for_peak_{int(target*100)}pct_of_threshold_ms"] = lo * 1e3
    basis["cb_allowable_misalignment_J1fit"] = allow

    # J3 shape (gentler drop) on a subset of chains
    f3 = fits["J3shape_FL_25mm_0.05s"]
    d3 = drop_shape(t, f3["F0_N"], f3["T_u_s"], f3["n"])
    phys3 = {"massless_harness": (d3, d3), "rod_mass_Fs0": rod_response(t, d3, FRONT, f3["F0_N"], 0.0, True)}
    subset = [
        ("J3 A0 harness", "massless_harness", 0, 0, "box10", 0, "instant"),
        ("J3 B1 + rod mass", "rod_mass_Fs0", 0, 0, "box10", 0, "instant"),
        ("J3 D box10 +0 nominal p", "rod_mass_Fs0", nominal_line, 0.25e-3, "box10", 0, "instant"),
        ("J3 D box10 +5 nominal p", "rod_mass_Fs0", nominal_line, 0.25e-3, "box10", 5e-3, "instant"),
        ("J3 D bw2_25 +0 nominal p", "rod_mass_Fs0", nominal_line, 0.25e-3, "bw2_25", 0, "instant"),
        ("J3 E C-b box +0", "rod_mass_Fs0", nominal_line, 0.25e-3, "box10", 0, "cb_box"),
        ("J3 E C-b box +2", "rod_mass_Fs0", nominal_line, 0.25e-3, "box10", 2e-3, "cb_box"),
        ("J3 E C-b box -2", "rod_mass_Fs0", nominal_line, 0.25e-3, "box10", -2e-3, "cb_box"),
        ("J3 E C-b box +5", "rod_mass_Fs0", nominal_line, 0.25e-3, "box10", 5e-3, "cb_box"),
    ]
    j3 = []
    for label, pk, tl, ts, imu, off, rule in subset:
        fp, fb = phys3[pk]
        res = evaluate(t, fp, fb, f3["T_u_s"], tau_line=tl, tau_sensor=ts, adc="none", imu=imu, ts_offset=off, rule=rule)
        j3.append({"case": label, "peak_abs_kN": round(res["peak_abs_kN"], 2), "peak_phase_ms": res["peak_phase_ms"],
                   "ratio_peak_to_49p8kN": round(res["ratio_peak"], 3), "fault_window_ms_thr49p8": res["window_ms_thr49p8"]})
        print(f"{label:40s} peak {res['peak_abs_kN']:7.2f} kN ratio {res['ratio_peak']:.3f} win {res['window_ms_thr49p8']:5.2f} ms")
    basis["j3_subset"] = j3
    basis["outputs"] = ["pressure_sampling_cases.csv", "pressure_sampling_phase.csv"]
    basis["sweep_source"] = str(SWEEP)
    with (HERE / "pressure_sampling_basis.json").open("w", newline="\n", encoding="utf-8") as fh:
        json.dump(basis, fh, indent=1)
    for r in rows:
        print(f"{r['case'][:70]:70s} peak {r['peak_abs_kN']:7.2f} kN  ratio {r['ratio_peak_to_49p8kN']:.3f}  win {r['fault_window_ms_thr49p8']:5.2f} ms  at {r['peak_phase_ms']:+.2f}")
    print(json.dumps({k: basis[k] for k in ("fits", "rod_ringing_Fs0", "cb_allowable_misalignment_J1fit", "q1_rates_front_J1fit")}, indent=1)[:4000])


if __name__ == "__main__":
    main()
