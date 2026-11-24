"""Retract dead volume ("need") of the P1 line-fill gate against the oil the probe retraction
delivers, per leg and setting, for the first probe (before the event) of confirmation (가) T4h
files. Read only; no simulation.

Two paths for ``need``:
  hand: the retract dead-volume formula written out here (check_open_delay.retract_dead text,
        hydraulics review), SI units;
  code: ``outrigger_sim.hydraulics.check_open_delay.retract_dead`` imported read-only from the
        run worktree (commit 79495405).
Plant values: YAML (worktree 02_params/rexome33.yaml) and the harness assumptions (params.py):
p_T 2 bar, V_line 285 cm3, beta_hose 0.5 GPa, psi 3.5, p_crack 3 bar, circuit VN (delta = p_crack).
F_band = F_s of the key (front F_s, rear 0.833 F_s) minus the acting friction f; f is not in the
T4h, so the Fs4 / Fs8 rows show band = F_s (upper) and band = 0 (lower). Fs0 rows are exact (0).
void_m (floor-limited rod spring) is taken as 0 (ASSUMPTION; the opening intervals agree).

Delivered oil: sum of |u| x 0.1 s over the retract commands of the probe (controller reads; the
valve output follows one period later, d = 1), in stroke units [mm].
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

WORKTREE = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed6-run6")
T4H = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405"
           r"\confirm_a1\confirm_a_t4h")
LEGS = ("FL", "FR", "RL", "RR")
BAR = 1e5
PERIOD_S = 0.1

A_H = np.array([0.013273229, 0.013273229, 0.00950331778, 0.00950331778])
A_ANN = np.array([0.00376991118, 0.00376991118, 0.00314159265, 0.00314159265])
S_MAX, L0R, L0H, BETA = 0.7, 0.05, 0.05, 1.0e9
P_T, V_LINE, BETA_HOSE, PSI, P_CR = 2e5, 285e-6, 0.5e9, 3.5, 3e5
REAR_FS_RATIO = 0.833


def need_hand(scale, p_h, p_r, band, s, leg, beta=BETA, l0r=L0R, l0h=L0H, v_line=V_LINE,
              scale_chambers=True):
    """Hand path. ``scale_chambers`` False scales only the line volume (the dead lengths are
    given directly): the physically uncertain parts alone."""
    a_h, a_ann = A_H[leg], A_ANN[leg]
    delta = P_CR
    drive = max(p_h, 0.0) + P_CR - P_T
    p_free = max(drive / PSI, 0.0)
    if a_ann * (p_free - delta - p_r) > band:
        p_b = (drive - (a_ann * (delta + p_r) + band) / a_h) / (PSI - a_ann / a_h)
    else:
        p_b = p_free
    p_rod = max(p_b - delta, p_r)
    dp_h = max(a_ann * (p_rod - p_r) - band, 0.0) / a_h
    v_head = a_h * (l0h + s)
    v_rod = a_ann * (l0r + S_MAX - s)
    k_line = scale
    k_ch = scale if scale_chambers else 1.0
    parts = {"line": k_line * v_line * max(p_b - P_T, 0.0) / BETA_HOSE,
             "rod": k_ch * v_rod * (p_rod - p_r) / beta,
             "head": k_ch * a_ann * v_head * dp_h / (beta * a_h)}
    need = sum(parts.values()) / a_ann
    return need, p_b, p_rod, dp_h, {k: v / a_ann for k, v in parts.items()}


def need_code(retract_dead, RetractConfig, scale, p_h, p_r, band, s, leg):
    cfg = RetractConfig(rod_forward=True, volume_scale=scale, v_line_m3=V_LINE,
                        beta_hose_Pa=BETA_HOSE, psi=PSI, p_crack_Pa=P_CR)
    out = retract_dead(cfg, p_h, p_r, band, s, 0.0, A_H[leg], A_ANN[leg], S_MAX, L0R, L0H, BETA,
                       P_T)
    return out["need"], out["p_open"], out["p_rod"]


def first_probe(phase):
    idx = np.flatnonzero(phase == "probe")
    if not len(idx):
        return None
    end = idx[0]
    while end + 1 < len(phase) and phase[end + 1] == "probe":
        end += 1
    return idx[0], end


def main(names):
    sys.path.insert(0, str(WORKTREE / "03_src"))
    try:
        from outrigger_sim.hydraulics.check_open_delay import RetractConfig, retract_dead
        code_ok = True
    except Exception as exc:  # noqa: BLE001 - record and continue on the hand path
        print(f"code path unavailable: {exc!r}")
        code_ok = False
    for name in names:
        with np.load(T4H / name, allow_pickle=False) as d:
            t, ph = d["t_s"], d["phase"]
            u, s = d["command_m_s"], d["motor_stroke_m"]
            locked = d["locked"]
            p_h, p_r = d["head_pressure_Pa"], d["rod_pressure_Pa"]
            meta = json.loads(str(d["meta_json"]))
        gate = meta["hydraulic_options"]["line_fill_gate"]
        scale = float(gate["volume_scale"])
        fs = float(meta["job"]["twin"]["fs_kN"]) * 1e3
        seg = first_probe(ph)
        print(f"== {name}: scale {scale}, c_v {gate['c_v']}, F_s {fs / 1e3:.1f} kN (front)")
        print("  leg  t_ret0  p_h   p_r   s_mm   deliv_mm  band_kN  need_mm(hand/code)  p_b   p_rod"
              "  dp_h  parts(line/rod/head mm)  released  ds_mm")
        i0, i1 = seg
        for leg in range(4):
            seg_u = u[i0:i1 + 1, leg]
            neg = np.flatnonzero(seg_u < -1e-9)
            if not len(neg):
                print(f"  {LEGS[leg]}  no retract command")
                continue
            k0 = i0 + neg[0]
            delivered = float(-seg_u[seg_u < -1e-9].sum() * PERIOD_S * 1e3)
            k_end = min(i0 + neg[-1] + 12, i1)
            released = bool((~locked[k0:k_end + 1, leg]).any())
            ds = float((s[k_end, leg] - s[k0, leg]) * 1e3)
            fs_leg = fs * (1.0 if leg < 2 else REAR_FS_RATIO)
            for band in sorted({fs_leg, 0.0}, reverse=True):
                need, p_b, p_rod, dp_h, parts = need_hand(scale, p_h[k0, leg], p_r[k0, leg], band,
                                                          s[k0, leg], leg)
                code = (need_code(retract_dead, RetractConfig, scale, p_h[k0, leg], p_r[k0, leg],
                                  band, s[k0, leg], leg)[0] if code_ok else math.nan)
                print(f"  {LEGS[leg]} {t[k0]:6.1f} {p_h[k0, leg] / BAR:6.2f} {p_r[k0, leg] / BAR:5.2f}"
                      f" {s[k0, leg] * 1e3:7.2f} {delivered:7.3f} {band / 1e3:6.2f}"
                      f"  {need * 1e3:6.3f}/{code * 1e3:6.3f}  {p_b / BAR:5.2f} {p_rod / BAR:5.2f}"
                      f" {dp_h / BAR:5.2f}  {parts['line'] * 1e3:.3f}/{parts['rod'] * 1e3:.3f}/"
                      f"{parts['head'] * 1e3:.3f}  {released}  {ds:6.3f}")


if __name__ == "__main__":
    main(sys.argv[1:])
