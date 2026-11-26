"""k02: offline replay of the probe K1 window candidates on the dynamics d00 re-runs.

Inputs (read only): ``../dynamics_d1_d3/rerun_raw/logs/<run>_{ctrl,plant,cue}.*`` (23 runs of the
edition 7 run commit C 8a2a52ce, arms a2 = edition 7 sealed controller, A = (i-b) off with the
witness on). The controller log ``ctrl`` holds the 10 Hz reading the probe uses
(``s.last_reading.cylinder_force_N`` / ``rod_stroke_m`` (piston, ``stroke_corrected_m``) /
``motor_stroke_m``), the command ``cmd`` and ``s.probe_round.leg``; the plant log holds the
harness truth (seal force ``f``, capacity ``Fs``, piston ``x``, oil stiffness ``ko``).

What it does, per probe round and probed leg (extend first only; retract-first legs are listed):

* reconstructs the current K1 window (``ground_contact.py`` 991-993 mid reading = the reading at
  which 5 of the 10 trapezoid commands have been sent, 1138-1143 extended reading = end of the
  first hold) and checks it against the controller cue (``stiffness_N_m``) of the run;
* candidate (a) ``moved_mid``: mid = the later of the current mid reading and the first reading
  whose piston reading has moved >= delta from the leg's first-command reading; K1 NaN when the
  mid -> extended piston travel is below ``min_travel`` (0.2 mm, ``ProbeSettings.min_travel_m``);
* candidate (b) ``slip_secant``: over the current window, keep only the reading intervals whose
  secant ``dF / dx`` is below ``0.5 k_h`` (k_h = plant ``ko`` of the leg, the head oil column);
* candidate (c) ``stuck_skip``: current window, but K1 NaN (leg out of the scale) when the piston
  reading has moved < delta by the current mid reading;
* the harness truth of each window: ``K_pad = (dF + df) / dx`` (seal-band part removed) and the
  seal state at the mid reading;
* per round: the median ratio over the legs the stiffness cue calls grounded (K1 > 0.3 S_ii,
  finite, ``c2.py`` 3093-3097, ``ground_contact.py`` 611) with at least 3 legs
  (``MIN_STIFFNESS_SCALE_LEGS``), the scale clipped to [1.0, 1.5] and the warning flags for the
  upper bounds 2.3 (now) and the candidates; and the load / seal-friction estimates with the
  measured-if-grounded correction (``ground_contact.py`` 612-622, ``c2.py`` 1688-1693, 2561).

Round 1 is exact (K1 only acts after the round, ``c2.py`` 9822-9837); later rounds are replayed
on the recorded trajectory of the old controller (approximate: the scale / F_band of round 1
would have changed the commands after round 1).

Usage: conda run -n dynamics-dev python -I -B k02_replay.py
Output (this folder): k02_legs.csv, k02_rounds.csv, k02_summary.json
"""
import csv
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / "dynamics_d1_d3" / "rerun_raw" / "logs"
LEGS = ("FL", "FR", "RL", "RR")
C1 = (5.83e6, 5.83e6, 6.98e6, 6.98e6)        # c2.py 1682 PROBE_CORRECTION_SENSITIVITY_N_M
GROUNDED_RATIO = 0.3                         # ground_contact.py 153
MIN_TRAVEL = 2e-4                            # ground_contact.py 151
MIN_LEGS = 3                                 # c2.py 1542
SCALE_MIN, SCALE_MAX = 1.0, 1.5              # c2.py 1643-1644
SEAL_MARGIN, SEAL_MIN = 1e3, 1e3             # ground_contact.py 160, 164
HALF = 5                                     # len(trapezoid) // 2, 10 periods
DELTAS = (0.02e-3, 0.05e-3, 0.1e-3, 0.2e-3)
WARN_HIGHS = (2.3, 3.0, 3.3, 3.6)


def series(path: Path, tkey: str) -> dict:
    """All objects of a log merged by time (objects are snapshots of the same run)."""
    z = np.load(path, allow_pickle=False)
    objs = sorted({k.split("|")[0] for k in z.files})
    best = max(objs, key=lambda o: len(z[f"{o}|{tkey}"]) if f"{o}|{tkey}" in z.files else 0)
    return {k.split("|", 1)[1]: z[k] for k in z.files if k.startswith(best + "|")}


def plant_series(path: Path) -> dict:
    z = np.load(path, allow_pickle=False)
    objs = sorted({k.split("|")[0] for k in z.files})
    parts = []
    for o in objs:
        if f"{o}|t" not in z.files:
            continue
        parts.append({k.split("|", 1)[1]: z[k] for k in z.files if k.startswith(o + "|")
                      and k.split("|", 1)[1] in ("t", "x", "f", "Fs", "ko", "sref")})
    t = np.concatenate([p["t"] for p in parts])
    order = np.argsort(t, kind="stable")
    out = {"t": t[order]}
    for key in ("x", "f", "Fs", "ko", "sref"):
        out[key] = np.concatenate([p[key] for p in parts])[order]
    return out


def secant(F, x, a, b):
    dx = x[b] - x[a]
    return (F[b] - F[a]) / dx if dx != 0 else math.nan


def estimates(cue_row, k1, s_nom, leg):
    """Load / seal-friction estimates (ground_contact.py 610-622) with K1 = k1."""
    grounded = math.isfinite(k1) and k1 > GROUNDED_RATIO * s_nom
    corr = k1 if grounded else C1[leg]
    gap = cue_row["extended_rod_stroke_m"] - cue_row["retracted_rod_stroke_m"]
    E, R = cue_row["extended_force_N"], cue_row["retracted_force_N"]
    load = 0.5 * (E + R) - 0.5 * corr * gap
    seal = 0.5 * (E - R - corr * gap)
    return grounded, load, seal


def round_summary(legs, s_nom_of):
    ratios = [r["k1"] / s_nom_of[r["leg"]] for r in legs
              if math.isfinite(r["k1"]) and r["k1"] > GROUNDED_RATIO * s_nom_of[r["leg"]]]
    if len(ratios) < MIN_LEGS:
        return None, len(ratios)
    return float(np.median(ratios)), len(ratios)


def main() -> int:
    leg_rows, round_rows, problems = [], [], []
    runs = sorted(p.name[:-len("_ctrl.npz")] for p in RAW.glob("*_ctrl.npz"))
    for run in runs:
        ctrl = series(RAW / f"{run}_ctrl.npz", "m.t_s")
        plant = plant_series(RAW / f"{run}_plant.npz")
        cue = json.loads((RAW / f"{run}_cue.json").read_text(encoding="utf-8"))
        t = ctrl["m.t_s"]
        F = ctrl["s.last_reading.cylinder_force_N"]
        x = ctrl["s.last_reading.rod_stroke_m"]
        cmd = ctrl["cmd"]
        phase = np.char.lower(ctrl["phase_name"].astype(str))
        pleg = ctrl["s.probe_round.leg"]
        rcount = ctrl["s.probe_round_count"]
        cue_rows = cue["cue"]
        s_nom_of = {}
        for c in cue_rows:
            s_nom_of[int(c["leg_index"])] = c["load_sensitivity_N_m"]
        # probe legs: contiguous periods in PROBE with the same (round, leg)
        in_probe = (phase == "probe") & np.isfinite(pleg)
        keys = []
        k = 0
        n = len(t)
        while k < n:
            if not in_probe[k]:
                k += 1
                continue
            key = (int(rcount[k]), int(pleg[k]))
            k1 = k
            while k1 + 1 < n and in_probe[k1 + 1] and (int(rcount[k1 + 1]), int(pleg[k1 + 1])) == key:
                k1 += 1
            keys.append((key, k, k1))
            k = k1 + 1
        per_round = {}
        for (rnd, leg), ka, kb in keys:
            if leg >= 4:
                continue
            c_leg = cmd[ka:kb + 2, leg] if kb + 2 <= n else cmd[ka:, leg]
            nz = np.flatnonzero(np.abs(c_leg) > 1e-12)
            if len(nz) == 0:
                continue
            if cmd[ka + int(nz[0]), leg] < 0:
                leg_rows.append({"run": run, "round": rnd, "leg": LEGS[leg], "reversed": True})
                continue
            # The logged ``cmd`` of a period can be the delayed output; the mid reading is found
            # by its cue force inside the leg's segment and the first-command decision reading is
            # HALF periods before it (ground_contact.py 991-993: 5 commands sent before it).
            found = None
            for kk in range(ka, min(kb + 1, n)):
                cands = [c for c in cue_rows if int(c["leg_index"]) == leg
                         and not c.get("is_reversed")
                         and abs(c["first_move_mid_force_N"] - F[kk, leg]) < 1.0]
                if cands:
                    found = (kk, cands[0])
                    break
            if found is None:
                problems.append(f"{run} r{rnd} {LEGS[leg]}: no cue mid reading in the segment")
                continue
            k_mid, c = found
            k0 = k_mid - HALF
            ext_c = [j for j in range(k_mid + 1, min(k_mid + 20, n))
                     if abs(F[j, leg] - c["extended_force_N"]) < 1.0]
            if not ext_c:
                problems.append(f"{run} r{rnd} {LEGS[leg]}: extended reading not found")
                continue
            k_ext = ext_c[0]
            k1_old = secant(F[:, leg], x[:, leg], k_mid, k_ext)
            if abs(k1_old - c["stiffness_N_m"]) > 1e-6 * abs(c["stiffness_N_m"]):
                problems.append(f"{run} r{rnd} {LEGS[leg]}: K1 replay {k1_old} != cue {c['stiffness_N_m']}")
            x0 = x[k0, leg]
            moved_mid = x[k_mid, leg] - x0
            ip = lambda j: int(np.argmin(np.abs(plant["t"] - t[j])))  # noqa: E731
            ko = float(plant["ko"][ip(k_mid), leg])
            Fs = float(plant["Fs"][ip(k_mid), leg])
            f_at = lambda j: float(plant["f"][ip(j), leg])  # noqa: E731

            def kpad(a, b):
                dx = x[b, leg] - x[a, leg]
                if dx == 0:
                    return math.nan
                return (F[b, leg] - F[a, leg] + f_at(b) - f_at(a)) / dx

            row = {"run": run, "round": rnd, "leg": LEGS[leg], "reversed": False,
                   "t_first_cmd_s": round(float(t[k0]), 2), "t_mid_s": round(float(t[k_mid]), 2),
                   "t_ext_s": round(float(t[k_ext]), 2),
                   "s_nom_MN_m": s_nom_of[leg] / 1e6, "ko_MN_m": ko / 1e6, "Fs_kN": Fs / 1e3,
                   "f_mid_kN": f_at(k_mid) / 1e3, "stuck_at_mid": abs(f_at(k_mid)) < Fs - 1.0,
                   "moved_by_mid_mm": moved_mid * 1e3,
                   "window_travel_mm": (x[k_ext, leg] - x[k_mid, leg]) * 1e3,
                   "k1_old": k1_old, "kpad_old": kpad(k_mid, k_ext)}
            for d in DELTAS:
                tag = f"{d * 1e3:g}"
                cand = [j for j in range(k0 + 1, k_ext) if x[j, leg] - x0 >= d]
                if cand:
                    ja = max(k_mid, cand[0])
                    travel = x[k_ext, leg] - x[ja, leg]
                    k1a = secant(F[:, leg], x[:, leg], ja, k_ext) if travel >= MIN_TRAVEL else math.nan
                    row[f"a{tag}_mid_shift"] = ja - k_mid
                    row[f"a{tag}_k1"] = k1a
                    row[f"a{tag}_kpad"] = kpad(ja, k_ext) if travel >= MIN_TRAVEL else math.nan
                    row[f"a{tag}_travel_mm"] = travel * 1e3
                    row[f"a{tag}_stuck_at_mid"] = abs(f_at(ja)) < Fs - 1.0
                    row[f"a{tag}_kband_ratio"] = ((k1a - row[f"a{tag}_kpad"]) / s_nom_of[leg]
                                                  if travel >= MIN_TRAVEL else math.nan)
                else:
                    row[f"a{tag}_stuck_at_mid"] = None
                    row[f"a{tag}_kband_ratio"] = math.nan
                    row[f"a{tag}_mid_shift"] = None
                    row[f"a{tag}_k1"] = math.nan
                    row[f"a{tag}_kpad"] = math.nan
                    row[f"a{tag}_travel_mm"] = None
                row[f"c{tag}_k1"] = k1_old if moved_mid >= d else math.nan
            dF_sum = dx_sum = 0.0
            for j in range(k_mid, k_ext):
                dx = x[j + 1, leg] - x[j, leg]
                dF = F[j + 1, leg] - F[j, leg]
                if dx > 0 and dF / dx < 0.5 * ko:
                    dF_sum += dF
                    dx_sum += dx
            row["b_k1"] = dF_sum / dx_sum if dx_sum >= MIN_TRAVEL else math.nan
            row["b_travel_mm"] = dx_sum * 1e3
            for name in ["k1_old", "b_k1"] + [f"a{d * 1e3:g}_k1" for d in DELTAS] + [f"c{d * 1e3:g}_k1" for d in DELTAS]:
                g, load, seal = estimates(c, row[name], s_nom_of[leg], leg)
                row[f"{name}_ratio"] = row[name] / s_nom_of[leg] if math.isfinite(row[name]) else math.nan
                row[f"{name}_load_kN"] = load / 1e3
                row[f"{name}_seal_kN"] = seal / 1e3
                row[f"{name}_grounded"] = g
            row["kpad_old_ratio"] = row["kpad_old"] / s_nom_of[leg]
            row["kband_old_ratio"] = (row["k1_old"] - row["kpad_old"]) / s_nom_of[leg]
            # decoupled variant: the old K1 decides the scale-leg set (grounded by stiffness),
            # the moved-mid K1 gives the ratio when it is finite and above 0.3 S_ii
            for d in DELTAS:
                tag = f"{d * 1e3:g}"
                old_grounded = math.isfinite(k1_old) and k1_old > GROUNDED_RATIO * s_nom_of[leg]
                k_new = row[f"a{tag}_k1"]
                row[f"dec{tag}_k1"] = (k_new if old_grounded and math.isfinite(k_new)
                                       and k_new > GROUNDED_RATIO * s_nom_of[leg] else math.nan)
            leg_rows.append(row)
            per_round.setdefault(rnd, []).append(row)
        for rnd, rows in sorted(per_round.items()):
            out = {"run": run, "round": rnd, "legs": len(rows)}
            names = (["k1_old", "b_k1", "kpad_old"] + [f"a{d * 1e3:g}_k1" for d in DELTAS]
                     + [f"c{d * 1e3:g}_k1" for d in DELTAS] + [f"dec{d * 1e3:g}_k1" for d in DELTAS])
            for name in names:
                legs = [{"leg": LEGS.index(r["leg"]), "k1": r[name]} for r in rows]
                med, cnt = round_summary(legs, s_nom_of)
                out[f"{name}_median"] = med
                out[f"{name}_count"] = cnt
                out[f"{name}_scale"] = None if med is None else min(max(med, SCALE_MIN), SCALE_MAX)
                for hi in WARN_HIGHS:
                    out[f"{name}_warn{hi:g}"] = med is not None and not 0.8 <= med <= hi
                if name != "kpad_old":
                    src = "k1_old" if name.startswith("dec") else name
                    seals = [r[f"{src}_seal_kN"] for r in rows]
                    out[f"{name}_seal_max_kN"] = max(seals)
            round_rows.append(out)
    for path, rows in (("k02_legs.csv", leg_rows), ("k02_rounds.csv", round_rows)):
        fields = []
        for r in rows:
            for key in r:
                if key not in fields:
                    fields.append(key)
        with (HERE / path).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in rows:
                w.writerow({k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()})
    summary = {"runs": runs, "leg_rows": len(leg_rows), "round_rows": len(round_rows),
               "replay_problems": problems,
               "k1_replay_checked": sum(1 for r in leg_rows if not r.get("reversed"))}
    (HERE / "k02_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
