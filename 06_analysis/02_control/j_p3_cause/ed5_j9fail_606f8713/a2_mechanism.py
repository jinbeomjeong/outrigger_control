"""j9_main 606f8713 failure analysis, step A2: mechanism features from T4h (read only).

Pairs: stored VB T4h (old VB plant; commands_sha256 equal to the 606f8713 VB / VBH T8 rows,
see a1) against VBJ / LSJ T4h of j9main_a1 (P1..P4 plant + ③ rev 6). V0 has no T4h; its
scalar values come from main.jsonl (a1).

Conventions: negative feedback, controller period T_s = 0.1 s, output delay d = 1, T4h rows are
controller reads (10 Hz). Forces kN (net cylinder force, true_force_min_N = minimum of the 1 ms
true force over (t_k-1, t_k]), pressures bar(g), stroke mm (oil coordinate motor_stroke_m),
speed mm/s. u_hold = 0.01 v_max = 0.20924 mm/s.

Outputs (this folder): a2_r12_mechanism.csv, a2_level_gate_hold.csv, a2_summary.json,
a2_fig_r12_o0.png, a2_fig_level_u.png
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(r"C:\workspace\outrigger_control")
V5 = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5"
VB_T4H = V5 / "main" / "t4h"
RUN = ROOT / "06_analysis" / "02_control" / "j_p3_cause" / "j9_runs" / "606f8713" / "j9main_a1"
J9 = RUN / "j9_main.jsonl"
J9_T4H = RUN / "j9_main_t4h"
OUT = Path(__file__).resolve().parent
LEGS = ("FL", "FR", "RL", "RR")
V_MAX = 0.020924302  # m/s, YAML actuator.max_speed_m_s
U_HOLD = 0.01 * V_MAX
EPS = 1.0e-6  # m/s, check_open_delay.EPS_M_S
F_MIN_KN = 9.41458911
A_H = np.array([0.0132732289, 0.0132732289, 0.0095033178, 0.0095033178])  # bore 130 / 110 mm
A_ANN = np.array([0.00376991118, 0.00376991118, 0.00314159265, 0.00314159265])  # YAML


def rows_of(path: Path, settings: set[str]) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if (d.get("job") or {}).get("setting") in settings:
                out.append(d)
    return out


def stem(d: dict) -> str:
    """T4h stem without the setting suffix (pair key)."""
    return d["t4h_file"].rsplit("_", 1)[0]


def r12_features(z, t_ev: float, leg: int) -> dict:
    t = z["t_s"]
    u = z["command_m_s"][:, leg]
    lk = z["locked"][:, leg]
    f = z["true_force_min_N"][:, leg] / 1e3
    ph = z["head_pressure_Pa"][:, leg] / 1e5
    pr = z["rod_pressure_Pa"][:, leg] / 1e5
    s = z["motor_stroke_m"][:, leg] * 1e3
    w = (t >= t_ev - 1e-9) & (t <= t_ev + 5.0 + 1e-9)
    iw = np.flatnonzero(w)
    i_min = iw[int(np.nanargmin(f[iw]))]
    ext = iw[(u[iw] > U_HOLD)]
    i_ext = int(ext[0]) if len(ext) else None
    i_unl = None
    if i_ext is not None:
        after = np.flatnonzero((np.arange(len(t)) >= i_ext) & ~lk)
        i_unl = int(after[0]) if len(after) else None
    pre = iw[iw < (i_ext if i_ext is not None else i_min)]
    held = iw[(iw <= i_min) & lk[iw] & (np.abs(u[iw]) > EPS)]
    i0 = iw[0]
    return {
        "t_min_s": round(float(t[i_min]), 3),
        "Fmin_kN": round(float(f[i_min]), 3),
        "F_event_kN": round(float(f[i0]), 3),
        "t_ext_s": None if i_ext is None else round(float(t[i_ext]), 3),
        "F_at_ext_kN": None if i_ext is None else round(float(f[i_ext]), 3),
        "locked_at_ext": None if i_ext is None else bool(lk[i_ext]),
        "unlock_delay_s": (None if i_ext is None or i_unl is None
                           else round(float(t[i_unl] - t[i_ext]), 3)),
        "retract_reads_before_ext": int(np.sum(u[pre] < -U_HOLD)),
        "min_u_before_ext_mm_s": round(float(np.min(u[pre])) * 1e3, 3) if len(pre) else None,
        "unlocked_reads_before_ext": int(np.sum(~lk[pre])),
        "gate_held_reads_to_min": int(len(held)),
        "pr_at_ext_bar": None if i_ext is None else round(float(pr[i_ext]), 2),
        "ph_at_ext_bar": None if i_ext is None else round(float(ph[i_ext]), 2),
        "pr_max_to_min_bar": round(float(np.max(pr[iw[iw <= i_min]])), 2),
        "rod_term_at_ext_kN": (None if i_ext is None
                               else round(float(pr[i_ext] * 1e5 * A_ANN[leg] / 1e3), 3)),
        "stroke_change_to_min_mm": round(float(s[i_min] - s[i0]), 3),
        "drop_pre_ext_kN": None if i_ext is None else round(float(f[i0] - f[i_ext]), 3),
        "drop_post_ext_kN": None if i_ext is None else round(float(f[i_ext] - f[i_min]), 3),
    }


def retract_delays(z, t_ev: float, min_leg: int) -> dict:
    """Twist / relevel retraction of the other legs after the event: first read with
    u < -1 mm/s in [t_ev, t_ev + 3 s] and the delay to the first unlocked read from there."""
    t = z["t_s"]
    out = {}
    for leg in range(4):
        if leg == min_leg:
            continue
        u = z["command_m_s"][:, leg]
        lk = z["locked"][:, leg]
        idx = np.flatnonzero((t >= t_ev - 1e-9) & (t <= t_ev + 3.0) & (u < -1.0e-3))
        if not len(idx):
            continue
        i0 = int(idx[0])
        un = np.flatnonzero((np.arange(len(t)) >= i0) & ~lk)
        out[LEGS[leg]] = {"t_cmd_s": round(float(t[i0]), 2),
                          "delay_s": None if not len(un) else round(float(t[un[0]] - t[i0]), 2)}
    delays = [v["delay_s"] for v in out.values() if v["delay_s"] is not None]
    return {"legs": out, "max_delay_s": max(delays) if delays else None}


def level_hold(z) -> dict:
    """LEVEL reads: plant locked while |u| > EPS (P1 gate hold candidates) and |u| of them."""
    ph = np.char.lower(z["phase"].astype(str))
    lv = ph == "level"
    u = np.abs(z["command_m_s"])
    lk = z["locked"]
    held = lv[:, None] & lk & (u > EPS)
    moving_cmd = lv[:, None] & (u > EPS)
    t = z["t_s"]
    last = t >= t[-1] - 20.0 - 1e-6
    width = (np.nanmax(z["motor_stroke_m"][last], axis=0) - np.nanmin(z["motor_stroke_m"][last], axis=0)) * 1e3
    return {
        "level_reads": int(lv.sum()),
        "level_cmd_leg_reads": int(moving_cmd.sum()),
        "level_held_leg_reads": int(held.sum()),
        "held_fraction": round(float(held.sum() / max(moving_cmd.sum(), 1)), 4),
        "held_u_median_mm_s": round(float(np.median(u[held])) * 1e3, 4) if held.any() else None,
        "held_u_p90_mm_s": round(float(np.percentile(u[held], 90)) * 1e3, 4) if held.any() else None,
        "held_u_list": (u[held] * 1e3).tolist(),
        "t_end_s": round(float(t[-1]), 2),
        "last_phase": str(ph[-1]),
        "last20_stroke_width_mm": [round(float(x), 3) for x in width],
        "last20_all_locked_fraction": round(float(np.mean(np.all(lk[last], axis=1))), 3),
        "last20_cmd_le_uhold_fraction": round(float(np.mean(u[last] <= U_HOLD)), 3),
    }


def dead_zone_extend(p_h_bar: float, c_v: float = 0.02, nf: float = 0.05, dp_c_bar: float = 10.0,
                     psi: float = 3.5, p_crack_bar: float = 3.0, p_T_bar: float = 2.0) -> float:
    """Steady-state P1 (VN) extension release threshold r = |u|/v_max for a locked leg.

    Line balance of check_open_delay._extend_step at the head-check opening pressure
    p_A = p_h + p_crack - psi p_b (p_b ~ p_T after the rod check released):
    r = nf S (1 - r / c_v),  S = sqrt((p_A - p_T) / dp_c)  ->  r = nf S / (1 + nf S / c_v).
    """
    p_a = p_h_bar + p_crack_bar - psi * p_T_bar
    s_ = math.sqrt(max(p_a - p_T_bar, 0.0) / dp_c_bar)
    return nf * s_ / (1.0 + nf * s_ / c_v)


def main() -> None:
    vbj = {stem(d): d for d in rows_of(J9, {"VBJ"})}
    lsj = rows_of(J9, {"LSJ1", "LSJ2", "LSJ3", "LSJ4"})
    vb = {stem(d): d for d in rows_of(V5 / "main.jsonl", {"VB"})}
    recs = []
    for k in sorted(x for x in vbj if x.startswith("R12")):
        dj, db = vbj[k], vb[k]
        mfw = dj["event_output"]["min_F_after_W_kN"]
        leg = LEGS.index(min(mfw, key=mfw.get))
        zj = np.load(J9_T4H / dj["t4h_file"], allow_pickle=False)
        zb = np.load(VB_T4H / db["t4h_file"], allow_pickle=False)
        fj = r12_features(zj, dj["t_event_s"], leg)
        fb = r12_features(zb, db["t_event_s"], leg)
        r = {"key": k, "leg": LEGS[leg], "t_ev_VB": db["t_event_s"], "t_ev_VBJ": dj["t_event_s"],
             "final_VBJ": dj["final_phase"],
             "gates_failed_VBJ": ";".join(g for g, x in dj["event_output"]["gates"].items() if x is False)}
        r.update({f"{a}_VB": b for a, b in fb.items()})
        r.update({f"{a}_VBJ": b for a, b in fj.items()})
        rb, rj = retract_delays(zb, db["t_event_s"], leg), retract_delays(zj, dj["t_event_s"], leg)
        r["other_leg_retract_delay_max_s_VB"] = rb["max_delay_s"]
        r["other_leg_retract_delay_max_s_VBJ"] = rj["max_delay_s"]
        r["other_leg_retract_VB"] = json.dumps(rb["legs"])
        r["other_leg_retract_VBJ"] = json.dumps(rj["legs"])
        recs.append(r)
    with open(OUT / "a2_r12_mechanism.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(recs[0].keys()))
        w.writeheader()
        w.writerows(recs)

    def agg(name, fn):
        vals = [fn(r) for r in recs]
        vals = [v for v in vals if v is not None]
        return {"n": len(vals), "min": min(vals), "median": float(np.median(vals)), "max": max(vals)}

    summ = {
        "u_hold_mm_s": U_HOLD * 1e3,
        "R12_rows": len(recs),
        "VB_locked_at_ext": sum(1 for r in recs if r["locked_at_ext_VB"]),
        "VBJ_locked_at_ext": sum(1 for r in recs if r["locked_at_ext_VBJ"]),
        "VB_unlock_delay_s": agg("", lambda r: r["unlock_delay_s_VB"]),
        "VBJ_unlock_delay_s": agg("", lambda r: r["unlock_delay_s_VBJ"]),
        "VB_gate_held_reads_to_min": agg("", lambda r: r["gate_held_reads_to_min_VB"]),
        "VBJ_gate_held_reads_to_min": agg("", lambda r: r["gate_held_reads_to_min_VBJ"]),
        "VB_retract_before_ext_rows": sum(1 for r in recs if r["retract_reads_before_ext_VB"] > 0),
        "VBJ_retract_before_ext_rows": sum(1 for r in recs if r["retract_reads_before_ext_VBJ"] > 0),
        "VB_unlocked_before_ext_rows": sum(1 for r in recs if r["unlocked_reads_before_ext_VB"] > 0),
        "VBJ_unlocked_before_ext_rows": sum(1 for r in recs if r["unlocked_reads_before_ext_VBJ"] > 0),
        "F_at_ext_VB_minus_VBJ_kN": agg("", lambda r: (None if r["F_at_ext_kN_VB"] is None or r["F_at_ext_kN_VBJ"] is None
                                                        else r["F_at_ext_kN_VB"] - r["F_at_ext_kN_VBJ"])),
        "drop_post_ext_VBJ_minus_VB_kN": agg("", lambda r: (None if r["drop_post_ext_kN_VB"] is None or r["drop_post_ext_kN_VBJ"] is None
                                                             else r["drop_post_ext_kN_VBJ"] - r["drop_post_ext_kN_VB"])),
        "rod_term_at_ext_VBJ_minus_VB_kN": agg("", lambda r: (None if r["rod_term_at_ext_kN_VB"] is None or r["rod_term_at_ext_kN_VBJ"] is None
                                                               else r["rod_term_at_ext_kN_VBJ"] - r["rod_term_at_ext_kN_VB"])),
        "Fmin_VB_minus_VBJ_kN": agg("", lambda r: r["Fmin_kN_VB"] - r["Fmin_kN_VBJ"]),
        "other_leg_retract_delay_max_s_VB": agg("", lambda r: r["other_leg_retract_delay_max_s_VB"]),
        "other_leg_retract_delay_max_s_VBJ": agg("", lambda r: r["other_leg_retract_delay_max_s_VBJ"]),
        "t_min_minus_t_event_s_VB": agg("", lambda r: r["t_min_s_VB"] - r["t_ev_VB"]),
        "t_min_minus_t_event_s_VBJ": agg("", lambda r: r["t_min_s_VBJ"] - r["t_ev_VBJ"]),
        "dead_zone_extend_r_at_p_h_bar": {str(p): round(dead_zone_extend(p), 5) for p in (10, 30, 60, 90, 130)},
        "dead_zone_extend_mm_s_at_p_h_bar": {str(p): round(dead_zone_extend(p) * V_MAX * 1e3, 4)
                                             for p in (10, 30, 60, 90, 130)},
    }

    # LEVEL gate hold: R15, S5 (VBJ fail rows) and S1 (LSJ3 L-b row) against VB
    lv = []
    pick = [k for k in vbj if k.startswith(("R15", "S5", "S1"))
            or (k.startswith("R12") and vbj[k]["final_phase"] != "ready")]
    for k in sorted(pick):
        for s, d, base in (("VB", vb.get(k), VB_T4H), ("VBJ", vbj[k], J9_T4H)):
            if d is None:
                continue
            z = np.load(base / d["t4h_file"], allow_pickle=False)
            h = level_hold(z)
            lv.append({"key": k, "setting": s, "final_phase": d["final_phase"],
                       "t_first_ready_s": d["values"]["times"].get("t_first_ready_s"),
                       **{a: b for a, b in h.items() if a != "held_u_list"}})
    for d in lsj:
        k = stem(d)
        if not k.startswith(("R15", "S5", "S1", "R12_top-FL-Fs4-o0.0", "R12_top-FR-Fs0-o0.0",
                             "R12_bottom-FL-Fs4-o0.05")):
            continue
        z = np.load(J9_T4H / d["t4h_file"], allow_pickle=False)
        h = level_hold(z)
        lv.append({"key": k, "setting": d["job"]["setting"], "final_phase": d["final_phase"],
                   "t_first_ready_s": d["values"]["times"].get("t_first_ready_s"),
                   **{a: b for a, b in h.items() if a != "held_u_list"}})
    with open(OUT / "a2_level_gate_hold.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lv[0].keys()))
        w.writeheader()
        w.writerows(lv)
    summ["level_rows"] = len(lv)

    # ③ can change commands only through a fallback leg (spec v5 4.5, T8). Fallback evidence per
    # VBJ / LSJ row: WARN_ROD_PRESSURE_FALLBACK events and lock_window_alignment fallback legs.
    def fallback_of(d: dict) -> bool:
        ev = [e for e in (d.get("events") or []) if "FALLBACK" in str(e)]
        names = [n for n in (d.get("event_names") or {}) if "FALLBACK" in n]
        fl = ((d.get("lock_window_alignment") or {}).get("fallback_legs") or {})
        return bool(ev or names or fl)

    # held reads above c_v v_max (no neutral drain there) on the VBJ / LSJ LEVEL rows
    # Held stretches: consecutive LEVEL reads of one leg with the plant locked and |u| > EPS.
    # Short stretches are the normal fill delay of a start; long ones (>= 1 s) are the dead zone.
    tot = above = 0
    long_n = long_all_below = 0
    long_reads = 0
    for d in list(vbj.values()) + lsj:
        z = np.load(J9_T4H / d["t4h_file"], allow_pickle=False)
        ph = np.char.lower(z["phase"].astype(str))
        u = np.abs(z["command_m_s"])
        held = (ph == "level")[:, None] & z["locked"] & (u > EPS)
        tot += int(held.sum())
        above += int((held & (u > 0.02 * V_MAX * 1.05)).sum())
        for leg in range(4):
            h = held[:, leg]
            i = 0
            while i < len(h):
                if not h[i]:
                    i += 1
                    continue
                j = i
                while j < len(h) and h[j]:
                    j += 1
                if j - i >= 10:
                    long_n += 1
                    long_reads += j - i
                    if np.max(u[i:j, leg]) <= 0.02 * V_MAX * 1.05:
                        long_all_below += 1
                i = j
    summ["level_held_leg_reads_all_388"] = tot
    summ["level_held_leg_reads_above_1p05_cv_vmax"] = above
    summ["held_stretches_ge_1s"] = long_n
    summ["held_stretch_reads_ge_1s"] = long_reads
    summ["held_stretches_ge_1s_all_u_le_1p05_cv_vmax"] = long_all_below

    allj = list(vbj.values()) + lsj
    summ["rows_with_fallback"] = sorted(f"{d['job']['setting']} {stem(d)}" for d in allj if fallback_of(d))
    summ["rows_checked_for_fallback"] = len(allj)
    with open(OUT / "a2_summary.json", "w", encoding="utf-8") as f:
        json.dump(summ, f, indent=1)
    print(json.dumps(summ, indent=1))

    # Figure 1: R12 offset 0 (RR, F_s 4, top) VB against VBJ
    k = "R12_o0.0"
    leg = 3
    fig, ax = plt.subplots(4, 1, figsize=(8.0, 9.0), sharex=True)
    for s, d, base, col in (("VB (old plant)", vb[k], VB_T4H, "#4a6fa5"),
                            ("VBJ (P1-P4 plant, rev 6)", vbj[k], J9_T4H, "#c0504d")):
        z = np.load(base / d["t4h_file"], allow_pickle=False)
        tr = z["t_s"] - d["t_event_s"]
        m = (tr > -0.5) & (tr < 3.0)
        ax[0].plot(tr[m], z["true_force_min_N"][m, leg] / 1e3, color=col, label=s)
        ax[1].plot(tr[m], z["head_pressure_Pa"][m, leg] / 1e5, color=col)
        ax[1].plot(tr[m], z["rod_pressure_Pa"][m, leg] / 1e5, color=col, ls="--")
        ax[2].step(tr[m], z["command_m_s"][m, leg] * 1e3, where="post", color=col)
        ax[3].step(tr[m], z["locked"][m, leg].astype(int), where="post", color=col)
    ax[0].axhline(F_MIN_KN, color="k", lw=0.8, ls=":")
    ax[0].set_ylabel("RR net force min [kN]")
    ax[0].legend(fontsize=8)
    ax[1].set_ylabel("p_h (solid), p_r (dashed) [bar]")
    ax[2].axhline(U_HOLD * 1e3, color="grey", lw=0.6)
    ax[2].axhline(-U_HOLD * 1e3, color="grey", lw=0.6)
    ax[2].set_ylabel("command u [mm/s]")
    ax[3].set_ylabel("plant locked [-]")
    ax[3].set_xlabel("time after event t - t_event [s]")
    fig.suptitle("R12 offset 0.0 (event leg RR, F_s 4 kN, top): RR leg, T_s 0.1 s reads")
    fig.tight_layout()
    fig.savefig(OUT / "a2_fig_r12_o0.png", dpi=130)
    plt.close(fig)

    # Figure 2: |u| of gate-held LEVEL reads (VBJ) against the steady release threshold
    fig, ax = plt.subplots(figsize=(8.0, 4.0))
    for k in ("R15_o0.05", "R15_o0.0", "S5_e0.0"):
        z = np.load(J9_T4H / vbj[k]["t4h_file"], allow_pickle=False)
        h = level_hold(z)
        if h["held_u_list"]:
            ax.hist(h["held_u_list"], bins=np.linspace(0, 1.0, 51), histtype="step", label=f"{k} VBJ")
    for p in (30, 90):
        ax.axvline(dead_zone_extend(p) * V_MAX * 1e3, color="k", ls=":", lw=0.8)
    ax.axvline(U_HOLD * 1e3, color="grey", lw=0.8)
    ax.axvline(0.02 * V_MAX * 1e3, color="k", lw=0.8)
    ax.set_xlabel("|u| of LEVEL leg-reads with plant locked [mm/s]")
    ax.set_title("grey: u_hold 0.209; dotted: P1 steady release at p_h 30 / 90 bar; black: c_v v_max 0.418",
                 fontsize=9)
    ax.set_ylabel("leg-reads [-]")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "a2_fig_level_u.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    main()
