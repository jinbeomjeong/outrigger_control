"""Edition 6 A(ii) lock-start fill floor and A(i) cap: hydraulic physics check (hydraulics-expert).

Opinion and calculation only: no harness or Chrono run, no project source changed. The stored
j9_main 606f8713 VBJ rows (already seen rows, spec ed. 6 O6-1) and the repository functions
``check_open_delay.retract_dead`` / ``CheckOpenGate`` (imported, not changed) are the inputs.

Parts (results in ``h6_lock_start_fill.json``):
  V  void of a locked leg rebuilt from the two chamber pressures since the lock anchor,
     void = [(L0h + s) dp_h + (L0r + s_max - s) dp_r] / beta, against the plant fill log
  L  retract lower bound x_lb (spec ed. 6 3.2 assumptions, and a robust set) against the plant
     need of the nominal / volume_scale 0.5 / 1.5 plants, per read of the 82 R12 fills, with a
     Monte Carlo of the normal-grade pressure sensor errors (seed fixed)
  X  extension opening volume: plant closed form against the spec ed. 6 formula and a lower
     bound over the rod-side pressure
  W  witness signals in the fill windows (harness truth): head drawdown while still locked,
     rod rise before / at the opening
  D  delay of the 82 fills: co-simulation read by read of the controller A(ii) output (increment
     limit 0.25 v_max per period, output delay d = 1) and the plant gate (1 ms chunks), plain end
     against look-ahead end, plants nominal / c_v 0.005 / c_v 0.04 / volume 0.5 / 1.5
  A  A(i) staircase: release thresholds up to 350 bar and opening times of a stalled leg

Conventions: pressures gauge [Pa] inside, bar(g) in the outputs; stroke m inside, mm out; speeds
mm/s out; extension positive. Valve and line values are plant ASSUMPTIONS (Q-M9, V-6).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control")
sys.path.insert(0, str(ROOT / "03_src"))
from outrigger_sim.hydraulics.check_open_delay import (  # noqa: E402
    CheckDelayCircuit, CheckDelayInputs, CheckOpenGate, RetractConfig, retract_dead)
from outrigger_sim.hydraulics.v5_options import CheckDelaySetting  # noqa: E402
from outrigger_sim.sensors.pressure_error import (  # noqa: E402
    CHAIN_RESOLUTION_PA, draw_unit_terms, error_terms_from_unit)

OUT = Path(__file__).resolve().parent
RUN = ROOT / "06_analysis" / "02_control" / "j_p3_cause" / "j9_runs" / "606f8713" / "j9main_a1"
H1_JSON = (ROOT / "06_analysis" / "02_control" / "j_p3_cause" / "ed5_j9fail_606f8713" / "hydraulics"
           / "h1_p1_physics.json")
LEGS = ("FL", "FR", "RL", "RR")
A_H = np.array([0.0132732289, 0.0132732289, 0.0095033178, 0.0095033178])  # m2, YAML
A_ANN = np.array([0.00376991118, 0.00376991118, 0.00314159265, 0.00314159265])  # m2, YAML
V_MAX = 0.0209243016  # m/s
S_MAX = 0.70
L0H = 0.05
L0R = 0.05
BETA = 1.0e9
P_T = 2.0e5  # Pa(g) ASSUMPTION
DP_C = 10.0e5  # Pa ASSUMPTION
P_FLOOR = 0.1e5 - 1.01325e5  # 0.1 bar abs as gauge
BAR = 1e5
T_S = 0.1
STEP = 0.25 * V_MAX  # increment limit per period (U-R8-27)
U_HOLD = 0.01 * V_MAX
F_S_MAX = np.array([8e3, 8e3, 8e3 * 0.833, 8e3 * 0.833])  # N, top of the F_s sensitivity
PLANT = {"v_line_m3": 285e-6, "beta_hose_Pa": 0.5e9, "psi": 3.5, "p_crack_Pa": 3e5}
LOWER_BOUNDS = {
    # spec ed. 6 3.2: psi 6, beta 1.6 GPa, V_line x0.5, void from readings; the rest nominal and
    # the unknown friction band taken as 0 (the controller has no band)
    "spec": {"psi": 6.0, "v_line_m3": 142.5e-6, "beta_hose_Pa": 0.5e9, "p_crack_Pa": 3e5,
             "beta": 1.6e9, "L0r": 0.05, "band": "zero", "p_margin_Pa": 0.0,
             "void_beta_head": 1.6e9, "void_beta_rod": 1.6e9},
    # robust: also band 2 F_s,max, L0r 0.02, beta_hose 1.0, p_crack 1 bar, +-4 bar reading margin
    "robust": {"psi": 6.0, "v_line_m3": 142.5e-6, "beta_hose_Pa": 1.0e9, "p_crack_Pa": 1e5,
               "beta": 1.6e9, "L0r": 0.02, "band": "two_fs_max", "p_margin_Pa": 4e5,
               "void_beta_head": 1.6e9, "void_beta_rod": 1.6e9},
}
PLANT_VARIANTS = {"nominal": (0.02, 1.0), "cv0.005": (0.005, 1.0), "cv0.04": (0.04, 1.0),
                  "vol0.5": (0.02, 0.5), "vol1.5": (0.02, 1.5)}
SEED = 20261123
N_DRAWS = 40
HOLD_MAX_S = 1.0  # hold arm: longest speed-floor hold after x_lb (ASSUMPTION of this check)


def stats(values) -> dict:
    v = np.asarray(list(values), float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {"n": 0}
    return {"n": int(v.size), "min": round(float(v.min()), 4),
            "p10": round(float(np.percentile(v, 10)), 4),
            "median": round(float(np.median(v)), 4),
            "p90": round(float(np.percentile(v, 90)), 4), "max": round(float(v.max()), 4)}


# --- plant and lower-bound need ------------------------------------------------------------------
def plant_need(leg, p_h, p_r, band, s, void, volume_scale) -> float:
    cfg = RetractConfig(rod_forward=True, volume_scale=volume_scale, **PLANT)
    return retract_dead(cfg, p_h, p_r, band, s, void, A_H[leg], A_ANN[leg], S_MAX, L0R, L0H,
                        BETA, P_T)["need"]


def lower_bound(leg, lb: dict, p_h_read, p_r_read, s, void_est) -> float:
    """x_lb with kappa 1 from readings (the controller does not know band, beta, psi, ...)."""
    cfg = RetractConfig(rod_forward=True, volume_scale=1.0, v_line_m3=lb["v_line_m3"],
                        beta_hose_Pa=lb["beta_hose_Pa"], psi=lb["psi"], p_crack_Pa=lb["p_crack_Pa"])
    band = 0.0 if lb["band"] == "zero" else 2.0 * F_S_MAX[leg]
    p_h = p_h_read - lb["p_margin_Pa"]
    p_r = max(p_r_read + lb["p_margin_Pa"], P_FLOOR)
    return retract_dead(cfg, p_h, p_r, band, s, void_est, A_H[leg], A_ANN[leg], S_MAX, lb["L0r"],
                        L0H, lb["beta"], P_T)["need"]


def void_from_pressures(p_h, p_r, p_h0, p_r0, s0, beta_head, beta_rod, l0r=L0R) -> float:
    """Oil the rod side did not get since the lock anchor: piston travel seen by the head minus
    the part the rod decompression absorbed (both chambers trapped)."""
    travel = (L0H + s0) * (p_h - p_h0) / beta_head
    absorbed = -(l0r + S_MAX - s0) * (p_r - p_r0) / beta_rod
    return max(travel - absorbed, 0.0)


# --- stored fills ---------------------------------------------------------------------------------
def load_fills() -> list[dict]:
    rows = json.loads(H1_JSON.read_text(encoding="utf-8"))["B_retract_dead_stroke"]["rows"]
    fills = []
    cache: dict[str, dict] = {}
    for r in rows:
        f = r["key"] + "_VBJ.npz"
        if f not in cache:
            z = np.load(RUN / "j9_main_t4h" / f, allow_pickle=False)
            cache[f] = {k: z[k] for k in ("t_s", "head_pressure_Pa", "rod_pressure_Pa",
                                          "motor_stroke_m", "command_m_s", "seal_band_N",
                                          "locked", "jp3_u_m_s")}
        z = cache[f]
        leg = LEGS.index(r["leg"])
        t = z["t_s"]
        i_open = int(np.searchsorted(t, r["open_s"] - 1e-9))  # first read at / after the opening
        lk = z["locked"][:, leg]
        i_last = i_open - 1  # last read still locked
        if not lk[i_last]:
            continue
        i_lock = i_last
        while i_lock > 0 and lk[i_lock - 1]:
            i_lock -= 1
        cmd = z["command_m_s"][:, leg]
        k_start = next((k for k in range(i_lock, i_last + 1) if cmd[k] < -U_HOLD), None)
        if k_start is None:
            continue
        fills.append({"key": r["key"], "leg": leg, "t": t, "p_h": z["head_pressure_Pa"][:, leg],
                      "p_r": z["rod_pressure_Pa"][:, leg], "s": z["motor_stroke_m"][:, leg],
                      "band": z["seal_band_N"][:, leg], "cmd": cmd,
                      "applied": z["jp3_u_m_s"][:, leg], "i_lock": i_lock, "i_last": i_last,
                      "k_start": k_start, "t_open_log": r["open_s"], "void_log_mm": r["void_mm"],
                      "p_h_log": r["p_h_bar"] * BAR, "p_r_log": r["p_r_bar"] * BAR,
                      "need_log_mm": r["need_log_mm"]})
    return fills


def void_true_series(f) -> np.ndarray:
    i0 = f["i_lock"]
    s0 = f["s"][i0]
    return np.array([void_from_pressures(f["p_h"][k], f["p_r"][k], f["p_h"][i0], f["p_r"][i0], s0,
                                         BETA, BETA) if k >= i0 else 0.0
                     for k in range(len(f["t"]))])


# --- part V ---------------------------------------------------------------------------------------
def part_v(fills) -> dict:
    rows = []
    for f in fills:
        v = void_true_series(f)
        i0 = f["i_lock"]
        v_log_p = void_from_pressures(f["p_h_log"], f["p_r_log"], f["p_h"][i0], f["p_r"][i0],
                                      f["s"][i0], BETA, BETA)
        rows.append({"key": f["key"], "leg": LEGS[f["leg"]],
                     "void_log_mm": f["void_log_mm"],
                     "void_rebuilt_last_locked_read_mm": round(v[f["i_last"]] * 1e3, 4),
                     "void_rebuilt_at_logged_pressures_mm": round(v_log_p * 1e3, 4),
                     "lock_age_s": round(float(f["t"][f["i_last"]] - f["t"][f["i_lock"]]), 2)})
    d = [r["void_rebuilt_last_locked_read_mm"] - r["void_log_mm"] for r in rows]
    ratio = [r["void_log_mm"] / r["void_rebuilt_last_locked_read_mm"] for r in rows
             if r["void_rebuilt_last_locked_read_mm"] > 0.05]
    d_p = [r["void_rebuilt_at_logged_pressures_mm"] - r["void_log_mm"] for r in rows]
    return {"rows": rows, "summary": {"rebuilt_minus_log_mm": stats(d),
                                      "rebuilt_at_logged_pressures_minus_log_mm": stats(d_p),
                                      "log_over_rebuilt": stats(ratio),
                                      "n_log_zero": sum(r["void_log_mm"] == 0 for r in rows)},
            "note": "log void is the plant value at the opening chunk; rebuilt uses the last "
                    "locked 10 Hz read (load moves inside the period)"}


# --- part L ---------------------------------------------------------------------------------------
def sensor_reads(rng, p_h, p_r):
    """Normal-grade readings of one run draw (head, rod) for arrays of true pressures."""
    terms = error_terms_from_unit(draw_unit_terms(rng, (2,)), "normal")
    out = []
    for side, p in ((0, p_h), (1, p_r)):
        e =(terms.offset_Pa[side] + terms.gain[side] * p
             + terms.nonlinearity_Pa[side] * ((p / 40e6 - (p / 40e6) ** 2 - 1 / 6) / (1 / 6)))
        e = np.clip(e, -4e5, 4e5)
        r = p + e + rng.normal(0.0, 0.20e5, p.shape)
        out.append(np.round(r / CHAIN_RESOLUTION_PA) * CHAIN_RESOLUTION_PA)
    return out


def part_l(fills) -> dict:
    rng = np.random.default_rng(SEED)
    res = {}
    per_fill_xlb = {name: [] for name in LOWER_BOUNDS}
    per_fill_need = []
    for name, lb in LOWER_BOUNDS.items():
        ratios = {vs: [] for vs in (0.5, 1.0, 1.5)}
        ratios_future = {vs: [] for vs in (0.5, 1.0, 1.5)}
        void_err = []
        for f in fills:
            leg = f["leg"]
            ks = list(range(f["k_start"], f["i_last"] + 1))
            v_true = void_true_series(f)
            needs = {vs: np.array([plant_need(leg, f["p_h"][k], f["p_r"][k], f["band"][k],
                                              f["s"][k], v_true[k], vs) for k in ks])
                     for vs in (0.5, 1.0, 1.5)}
            if name == "spec":
                per_fill_need.append(needs[1.0][0] * 1e3)
            i0 = f["i_lock"]
            for draw in range(N_DRAWS):
                ph_r, pr_r = sensor_reads(rng, f["p_h"], f["p_r"])
                xs = []
                for k in ks:
                    v_est = void_from_pressures(ph_r[k], pr_r[k], ph_r[i0], pr_r[i0], f["s"][i0],
                                                lb["void_beta_head"], lb["void_beta_rod"],
                                                l0r=lb["L0r"])
                    void_err.append((v_est - v_true[k]) * 1e3)
                    xs.append(lower_bound(leg, lb, ph_r[k], pr_r[k], f["s"][k], v_est))
                xs = np.array(xs)
                if draw == 0:
                    per_fill_xlb[name].append(xs[0] * 1e3)
                for vs in (0.5, 1.0, 1.5):
                    ratios[vs].extend(needs[vs] / xs)
                    fut = np.minimum.accumulate(needs[vs][::-1])[::-1]
                    ratios_future[vs].extend(fut / xs)
        res[name] = {
            "need_over_xlb_same_read": {f"vol{vs}": stats(r) for vs, r in ratios.items()},
            "need_later_min_over_xlb": {f"vol{vs}": stats(r) for vs, r in ratios_future.items()},
            "kappa_max_same_read": round(min(min(r) for r in ratios.values()), 4),
            "kappa_max_later_min": round(min(min(r) for r in ratios_future.values()), 4),
            "void_est_minus_true_mm": stats(void_err),
            "lb": lb}
    res["x_lb_at_start_mm"] = {name: stats(v) for name, v in per_fill_xlb.items()}
    res["need_nominal_at_start_mm"] = stats(per_fill_need)
    res["x_lb_over_need_nominal_at_start"] = {
        name: stats(np.array(v) / np.array(per_fill_need)) for name, v in per_fill_xlb.items()}
    res["draws_per_fill"] = N_DRAWS
    res["seed"] = SEED
    return res


# --- part X ---------------------------------------------------------------------------------------
def ext_open_x(leg, p_h, p_r, s, scale, psi=3.5, p_cr=3e5, v_line=285e-6, beta_hose=0.5e9) -> float:
    """Plant (CheckOpenDelay VN) extension line fill to the head-check opening at a speed above
    c_v v_max (no drain), in stroke units [m]."""
    c_r = A_ANN[leg] * (L0R + S_MAX - s) / BETA
    c_l = v_line * scale / beta_hose
    p_rod_thr = P_T + (p_r + p_cr - P_T) / psi
    p_b = min((c_r * p_r + c_l * P_T) / (c_r + c_l), p_r)
    p_head_thr = p_h + p_cr - psi * p_b
    p_a = max(p_rod_thr, p_head_thr)
    return max(p_a - P_T, 0.0) * v_line * scale / (A_H[leg] * beta_hose)


def ext_lb_spec(leg, p_h, psi=6.0, p_cr=3e5, v_line=142.5e-6, beta_hose=0.5e9) -> float:
    """Spec ed. 6 3.2: (p_h + p_cr - psi p_T - p_T) V_line / (A_h beta_hose)."""
    return max(p_h + p_cr - psi * P_T - P_T, 0.0) * v_line / (A_H[leg] * beta_hose)


def ext_lb_proposed(leg, p_h, p_r, psi=6.0, p_cr=1e5, v_line=142.5e-6, beta_hose=1.0e9,
                    margin=4e5) -> float:
    """Lower bound over the unknown rod-side line pressure p_B in [p_T, p_r]: the head check may
    open at p_A = p_h + p_cr - psi p_B with p_B up to p_r, but not before the rod check
    releases at p_A = p_T + (p_r + p_cr - p_T) / psi."""
    ph = p_h - margin
    pr = max(p_r - margin, P_FLOOR)
    p_rod_thr = P_T + (pr + p_cr - P_T) / psi
    p_head_thr = ph + p_cr - psi * (p_r + margin)
    return max(max(p_rod_thr, p_head_thr) - P_T, 0.0) * v_line / (A_H[leg] * beta_hose)


def gate_open_time(leg, direction, u_cmd, p_h, p_r, c_v, scale, void=0.0, s=0.396,
                   t_max=20.0, dt=1e-3):
    """Constant-input opening time with the repository gate (one leg circuit)."""
    gate = make_gate(leg, c_v, scale)
    for j in range(int(t_max / dt)):
        u = u_cmd(j * dt) * direction
        out = gate.filter(CheckDelayInputs(j * dt, dt, np.array([u]), np.array([p_h]),
                                           np.array([p_r]), np.array([True]), np.array([void]),
                                           np.array([0.0]), np.array([s])))
        if out.speed_m_s[0] != 0.0:
            return (j + 1) * dt
    return None


def part_x() -> dict:
    rows = []
    for leg in (0, 2):
        for p_h_bar, p_r_bar in ((30, 5), (60, 5), (90, 5), (130, 5), (200, 5), (30, 63),
                                 (60, 30), (90, -0.91325)):
            p_h, p_r = p_h_bar * BAR, p_r_bar * BAR
            row = {"leg": LEGS[leg], "p_h_bar": p_h_bar, "p_r_bar": p_r_bar}
            for scale in (0.5, 1.0, 1.5):
                row[f"plant_vol{scale}_mm"] = round(ext_open_x(leg, p_h, p_r, 0.396, scale) * 1e3, 4)
            row["lb_spec_mm"] = round(ext_lb_spec(leg, p_h) * 1e3, 4)
            row["lb_proposed_mm"] = round(ext_lb_proposed(leg, p_h, p_r) * 1e3, 4)
            row["spec_over_plant_vol0.5"] = round(row["lb_spec_mm"] / row["plant_vol0.5_mm"], 3) \
                if row["plant_vol0.5_mm"] > 0 else None
            row["proposed_over_plant_vol0.5"] = round(
                row["lb_proposed_mm"] / row["plant_vol0.5_mm"], 3) if row["plant_vol0.5_mm"] > 0 \
                else None
            rows.append(row)
    # check the closed form against the repository gate at v_max
    checks = []
    for leg, p_h_bar, p_r_bar in ((0, 90, 5), (2, 130, 5), (0, 30, 63)):
        t = gate_open_time(leg, 1, lambda _t: V_MAX, p_h_bar * BAR, p_r_bar * BAR, 0.02, 1.0)
        checks.append({"leg": LEGS[leg], "p_h_bar": p_h_bar, "p_r_bar": p_r_bar,
                       "gate_x_at_open_mm": round(t * V_MAX * 1e3, 4),
                       "closed_form_mm": round(ext_open_x(leg, p_h_bar * BAR, p_r_bar * BAR, 0.396,
                                                          1.0) * 1e3, 4)})
    return {"rows": rows, "gate_check": checks,
            "note": "plant psi 3.5, p_cr 3 bar, V_line 285 cm3, beta_hose 0.5 GPa; spec lb psi 6, "
                    "V_line x0.5; proposed lb psi 6, p_cr 1 bar, V_line x0.5, beta_hose 1.0 GPa, "
                    "+-4 bar margin, p_B up to p_r"}


# --- part W ---------------------------------------------------------------------------------------
def part_w(fills) -> dict:
    head_dd, head_rise, rod_rise_locked, rod_jump_open, head_jump_open = [], [], [], [], []
    for f in fills:
        ks = range(f["k_start"], f["i_last"] + 1)
        ph = f["p_h"][list(ks)] / BAR
        pr = f["p_r"][list(ks)] / BAR
        run_max = np.maximum.accumulate(ph)
        head_dd.append(float(np.max(run_max - ph)))
        head_rise.append(float(np.max(ph - ph[0])))
        rod_rise_locked.append(float(np.max(pr - pr[0])))
        i = f["i_last"]
        rod_jump_open.append(float((f["p_r"][i + 1] - f["p_r"][i]) / BAR))
        head_jump_open.append(float((f["p_h"][i + 1] - f["p_h"][i]) / BAR))
    sigma_diff = math.sqrt(2) * 0.20
    false_head = sum(dd >= 1.5 and ri >= 2.0 for dd, ri in zip(head_dd, head_rise, strict=True))
    return {"head_signal_rise2_drop1p5_before_opening": {"fires": int(false_head),
                                                         "of": len(head_dd)},
            "head_max_drawdown_while_locked_bar": stats(head_dd),
            "head_max_rise_while_locked_bar": stats(head_rise),
            "rod_max_rise_while_locked_bar": stats(rod_rise_locked),
            "rod_change_at_opening_read_bar": stats(rod_jump_open),
            "head_change_at_opening_read_bar": stats(head_jump_open),
            "reading_difference_noise_sigma_bar": round(sigma_diff, 3),
            "note": "harness truth pressures (gate mode: no rod or head change from the fill "
                    "before the opening; the rod jumps by the M2 seed at the opening)"}


# --- part D ---------------------------------------------------------------------------------------
def make_gate(leg, c_v, scale) -> CheckOpenGate:
    circuit = CheckDelayCircuit(head_area_m2=A_H[leg:leg + 1], annulus_area_m2=A_ANN[leg:leg + 1],
                                stroke_m=S_MAX, rod_dead_length_m=L0R, head_dead_length_m=L0H,
                                bulk_modulus_Pa=BETA, tank_pressure_Pa=P_T, max_speed_m_s=V_MAX,
                                compensator_drop_Pa=DP_C)
    return CheckOpenGate(CheckDelaySetting(kind="VN", volume_scale=scale, c_v=c_v), circuit)


def down_ramp(m: float, b: float) -> float:
    """Stroke the outputs above the base deliver on the way down from magnitude m to b."""
    total, x = 0.0, m - STEP
    while x > b + 1e-12:
        total += x * T_S
        x -= STEP
    return total


def cosim(f, c_v, scale, arm: str, v_true) -> dict:
    """Read-by-read co-simulation of one fill: controller output O[k] at read k, applied during
    the next period (d = 1), plant gate in 1 ms chunks."""
    leg = f["leg"]
    t, cmd = f["t"], f["cmd"]
    k0 = max(f["i_lock"], f["k_start"] - 30)
    k_end = min(len(t) - 2, f["i_last"] + 40)
    gate = make_gate(leg, c_v, scale)
    outputs = {k0 - 1: cmd[k0 - 1]}
    x_acc = 0.0
    active = arm != "base"
    opened_t = None
    moved = 0.0
    extra = 0.0
    lb = LOWER_BOUNDS.get(arm.split("_")[0]) if arm != "base" else None
    end_reason = None
    hold_phase, hold_start = False, None
    i0 = f["i_lock"]
    dt = 1e-3
    for k in range(k0, k_end):
        base = cmd[k]
        prev = outputs[k - 1]
        if arm == "base" or k < f["k_start"]:
            out = base
        else:
            if active and moved >= 1.0e-3:
                active, end_reason = False, end_reason or "witness_1mm"
            if active and base > U_HOLD:
                active, end_reason = False, end_reason or "sign_change"
            if active:
                if arm.startswith("oracle"):
                    x_lb = plant_need(leg, f["p_h"][k], f["p_r"][k], f["band"][k], f["s"][k],
                                      v_true[k], 1.0)
                else:
                    v_est = void_from_pressures(f["p_h"][k], f["p_r"][k], f["p_h"][i0],
                                                f["p_r"][i0], f["s"][i0], lb["void_beta_head"],
                                                lb["void_beta_rod"], l0r=lb["L0r"])
                    x_lb = lower_bound(leg, lb, f["p_h"][k], f["p_r"][k], f["s"][k], v_est)
                b, m_prev = abs(base), abs(prev)
                if arm.endswith("plain"):
                    if x_acc < x_lb:
                        out = prev + float(np.clip(-max(b, V_MAX) - prev, -STEP, STEP))
                    else:
                        active, end_reason = False, end_reason or "x_lb"
                        out = prev + float(np.clip(base - prev, -STEP, STEP))
                elif hold_phase:  # speed floor of one increment until the opening witness
                    seen_rod = opened_t is not None and t[k] > opened_t  # M2 seed jump read
                    if seen_rod or moved >= 1.0e-3 or t[k] - hold_start >= HOLD_MAX_S:
                        active = False
                        end_reason = "rod_witness" if seen_rod else (
                            "witness_1mm" if moved >= 1.0e-3 else "hold_timeout")
                        out = prev + float(np.clip(base - prev, -STEP, STEP))
                    else:
                        out = prev + float(np.clip(-max(b, STEP) - prev, -STEP, STEP))
                else:  # look-ahead: the elevated part ends by x_lb
                    chosen = None
                    for m in (min(m_prev + STEP, V_MAX), m_prev, m_prev - STEP):
                        m = max(m, b)
                        if x_acc + m * T_S + down_ramp(m, b) <= x_lb:
                            chosen = m
                            break
                    if chosen is None:
                        chosen = max(m_prev - STEP, b)
                    if arm.endswith("hold") and chosen <= max(b, STEP) + 1e-12:
                        hold_phase, hold_start = True, float(t[k])
                        chosen = max(b, STEP)
                    elif chosen <= b + 1e-12:
                        active, end_reason = False, end_reason or "x_lb"
                    out = -chosen
            else:
                out = prev + float(np.clip(base - prev, -STEP, STEP))
            x_acc += abs(out) * T_S
        outputs[k] = out
        u_applied = outputs[k - 1]
        u_base_applied = cmd[k - 1]
        for j in range(int(round(T_S / dt))):
            tc = t[k] + j * dt
            locked = opened_t is None
            o = gate.filter(CheckDelayInputs(tc, dt, np.array([u_applied]), np.array([f["p_h"][k]]),
                                             np.array([f["p_r"][k]]), np.array([locked]),
                                             np.array([v_true[k]]), np.array([f["band"][k]]),
                                             np.array([f["s"][k]])))
            if opened_t is None and o.speed_m_s[0] != 0.0:
                opened_t = tc
            if opened_t is not None:
                moved += abs(o.speed_m_s[0]) * dt
                extra += max(abs(u_applied) - abs(u_base_applied), 0.0) * dt
        if opened_t is not None and t[k] > opened_t + 1.5 and not active and \
                abs(outputs[k] - cmd[k]) < 1e-9:
            break
    t_start = float(t[f["k_start"]])
    return {"delay_s": None if opened_t is None else round(opened_t - t_start, 3),
            "t_open": opened_t, "extra_after_open_mm": round(extra * 1e3, 4),
            "end_reason": end_reason, "peak_out_mm_s": round(max(abs(v) for v in outputs.values())
                                                             * 1e3, 3)}


def part_d(fills) -> dict:
    arms = ("base", "spec_plain", "spec_look", "robust_look", "robust_hold", "oracle_look")
    rows = []
    for f in fills:
        v_true = void_true_series(f)
        row = {"key": f["key"], "leg": LEGS[f["leg"]], "t_open_log": f["t_open_log"],
               "t_start": float(f["t"][f["k_start"]])}
        for pname, (c_v, scale) in PLANT_VARIANTS.items():
            for arm in arms:
                r = cosim(f, c_v, scale, arm, v_true)
                row[f"{pname}|{arm}"] = r
        rows.append(row)
    summ = {}
    for pname in PLANT_VARIANTS:
        for arm in arms:
            d = [r[f"{pname}|{arm}"]["delay_s"] for r in rows]
            summ[f"{pname}|{arm}"] = {
                "delay_s": stats([x if x is not None else np.nan for x in d]),
                "not_open": sum(x is None for x in d),
                "extra_after_open_mm": stats(r[f"{pname}|{arm}"]["extra_after_open_mm"]
                                             for r in rows),
                "peak_out_mm_s": stats(r[f"{pname}|{arm}"]["peak_out_mm_s"] for r in rows)}
            if arm != "base":
                red = [r[f"{pname}|base"]["delay_s"] - r[f"{pname}|{arm}"]["delay_s"]
                       for r in rows if r[f"{pname}|base"]["delay_s"] is not None
                       and r[f"{pname}|{arm}"]["delay_s"] is not None]
                summ[f"{pname}|{arm}"]["reduction_s"] = stats(red)
    check = [abs(r["nominal|base"]["t_open"] - r["t_open_log"]) for r in rows
             if r["nominal|base"]["t_open"] is not None]
    return {"rows": rows, "summary": summ,
            "replay_check_abs_t_open_minus_log_s": stats(check)}


# --- part A ---------------------------------------------------------------------------------------
def release_threshold(p_open_minus_pT, area_ratio, c_v, n_f) -> float:
    s_ = math.sqrt(max(p_open_minus_pT, 0.0) / DP_C)
    x = n_f * area_ratio * s_
    return x / (1.0 + x / c_v)


def part_a() -> dict:
    thr = []
    for c_v in (0.005, 0.02, 0.04):
        for n_f in (0.05, 0.10):
            for p_h_bar in (30, 90, 130, 200, 350):
                p_h = p_h_bar * BAR
                r_e = release_threshold(p_h + 3e5 - 3.5 * P_T - P_T, 1.0, c_v, n_f)
                p_b = (p_h + 3e5 - P_T) / 3.5
                r_r = release_threshold(p_b - P_T, A_H[0] / A_ANN[0], c_v, n_f)
                thr.append({"c_v": c_v, "n_f": n_f, "p_h_bar": p_h_bar,
                            "ext_mm_s": round(r_e * V_MAX * 1e3, 4),
                            "ret_front_mm_s": round(r_r * V_MAX * 1e3, 4),
                            "asymptote_mm_s": round(c_v * V_MAX * 1e3, 4)})
    cases = [("ext_loaded_ph90_pr5", 1, 90e5, 5e5, 0.0),
             ("ret_loaded_ph122_floor_void1.2", -1, 122e5, P_FLOOR, 1.2e-3)]
    stair = []
    u0 = 0.30e-3
    n_trig = 10
    for name, direction, p_h, p_r, void in cases:
        for c_v in (0.005, 0.02, 0.04):
            for d_u in (0.05e-3, 0.1e-3, 0.2e-3, 0.4e-3):
                for cap in (0.8e-3, 0.9e-3, 1.05e-3, 1.25e-3):
                    def u_cmd(tt, d_u=d_u, cap=cap):
                        k = int(tt / T_S + 1e-9)
                        if k < n_trig:
                            return u0
                        return min(u0 + (k - n_trig + 1) * d_u, cap)
                    t_open = gate_open_time(0, direction, u_cmd, p_h, p_r, c_v, 1.0, void,
                                            t_max=40.0)
                    stair.append({"case": name, "c_v": c_v, "du_mm_s": d_u * 1e3,
                                  "cap_mm_s": cap * 1e3,
                                  "t_open_from_trigger_s": None if t_open is None else
                                  round(t_open - n_trig * T_S, 3),
                                  "u_at_open_mm_s": None if t_open is None else
                                  round(u_cmd(t_open) * 1e3, 3)})
    return {"thresholds": thr, "staircase": stair,
            "staircase_setup": {"u_before_trigger_mm_s": u0 * 1e3, "n_trig": n_trig,
                                "note": "front leg, constant pressures, open loop, plant volume 1"}}


def main() -> None:
    global N_DRAWS, OUT
    fills = load_fills()
    if "--quick" in sys.argv:  # smoke run of the script itself (scratch output folder)
        fills = fills[:3]
        N_DRAWS = 2
        OUT = Path(sys.argv[sys.argv.index("--quick") + 1])
    res = {"n_fills": len(fills), "V_void_rebuild": part_v(fills), "L_lower_bound": part_l(fills),
           "X_extension": part_x(), "W_witness": part_w(fills), "D_delay": part_d(fills),
           "A_staircase": part_a(),
           "assumptions": {"plant": PLANT, "beta_Pa": BETA, "L0r_m": L0R, "L0h_m": L0H,
                           "p_T_Pa_gauge": P_T, "dp_c_Pa": DP_C, "v_max_m_s": V_MAX,
                           "step_m_s": STEP, "u_hold_m_s": U_HOLD, "p_floor_Pa_gauge": P_FLOOR,
                           "F_s_max_N": F_S_MAX.tolist(), "seed": SEED}}
    with open(OUT / "h6_lock_start_fill.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, indent=1, default=float)
    brief = {"n_fills": res["n_fills"], "V": res["V_void_rebuild"]["summary"],
             "L": {k: {kk: vv for kk, vv in v.items() if kk.startswith("kappa") or
                       kk == "void_est_minus_true_mm"} for k, v in res["L_lower_bound"].items()
                   if isinstance(v, dict) and "lb" in v},
             "L_xlb": res["L_lower_bound"]["x_lb_at_start_mm"],
             "L_need": res["L_lower_bound"]["need_nominal_at_start_mm"],
             "W": res["W_witness"],
             "D_check": res["D_delay"]["replay_check_abs_t_open_minus_log_s"],
             "D": {k: {"delay_median": v["delay_s"].get("median"), "delay_max": v["delay_s"].get("max"),
                       "not_open": v["not_open"],
                       "red_median": v.get("reduction_s", {}).get("median"),
                       "extra_max": v["extra_after_open_mm"].get("max")}
                   for k, v in res["D_delay"]["summary"].items()}}
    print(json.dumps(brief, indent=1, default=float))


if __name__ == "__main__":
    main()
