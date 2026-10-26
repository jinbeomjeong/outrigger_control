"""Value summaries of the S9 P1 / P2 / P3a batches against the criteria of dynamics_model.md 5.34.13
(rev. 49), 5.35.4, 5.36.3 (P2'-b J1 / J2 health limit) and 5.36.5 (P3a, rev. 51).

Values and criterion comparisons only; pass / fail decisions are dynamics-expert's. Reads a batch
folder of ``s9_batch.py`` and writes one JSON to ``06_analysis/01_chrono/19_S9/``.

Usage (Chrono-dev, worktree root)::

    python -I -X utf8 04_scripts/02_chrono/s9_batch_summary.py <V0p|V16|L|P2|P2prime|P3a> <batch folder> [<out.json>]

Units: SI in keys ending _m, _N, _s; mm / deg / % where the key says so. Frames: single pad world
z up, SCM plane z = 0; machine world = body axes at the start (x forward, z up), pitch > 0 nose down.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
G = 9.80665
OUT = ROOT / "06_analysis" / "01_chrono" / "19_S9"
SOILS = json.loads((ROOT / "02_params" / "scm_soil_sets.json").read_text("utf-8"))["sets"]

# dynamics_model.md 5.31.8 grid phase ranges [%] (25 phases) at the design load, (2 cm, 1 cm, 0.5 cm)
PHASE_RANGE_PCT = {("J1", "RL"): ((-28.1, 29.4), (-1.9, 3.2), (-0.6, 2.4)),
                   ("J1", "FL"): ((-9.6, 16.3), (-4.2, 6.4), (-0.8, 2.1)),
                   ("J2", "RL"): ((-19.5, 17.8), (-1.3, 2.0), (-0.4, 1.6)),
                   ("J2", "FL"): ((-6.4, 10.1), (-2.8, 4.1), (-0.5, 1.3))}
GRID_INDEX = {0.02: 0, 0.01: 1, 0.005: 2}
L4_LOADED_FRACTION = 0.01
"""P1-L4 tilt judged while the SCM normal exceeds 1 % of the full load (5.35.2, U-S9P-3)."""
DYN_REV50_JSON = OUT / "s9_P1P2_dyn_judgement_rev50.json"
"""dynamics rev. 50 replica values (5.35.4 P2' comparison values, ``crawler_replica_variants``)."""


def l5_split(case_dir: Path, r: dict[str, Any], window_s: float = 10.0, mean_s: float = 4.0) -> dict[str, Any]:
    """P1-L5 split (dynamics 5.35.2, ``s9_p1p2_judge_rev50.l5_split`` ported): in-plane motion of the
    track anchor point (body frame, ``meta.crawler_anchor.points_body_m``; x, z used, planar) from
    ``mean_s`` window means at the start and the end of the last ``window_s`` of the settle, against
    the origin end points; pitch change; rocking peak frequency and zeta from the 2 s p-p decay.
    In-plane axis = world x rotated by the floor pitch (``args.floor_pitch``)."""
    d = np.load(case_dir / "series.npz")
    a = math.radians(float(r["args"].get("floor_pitch") or 0.0))
    t = d["t_s"]
    pos = d["body_pos_m"]
    th = np.radians(d["roll_pitch_deg"][:, 1])
    xtr, _, ztr = r["meta"]["crawler_anchor"]["points_body_m"][0]
    px = pos[:, 0] + xtr * np.cos(th) + ztr * np.sin(th)
    pz = pos[:, 2] - xtr * np.sin(th) + ztr * np.cos(th)
    tin = px * math.cos(a) - pz * math.sin(a)
    oin = pos[:, 0] * math.cos(a) - pos[:, 2] * math.sin(a)
    t1 = float(t[-1])
    t0 = t1 - window_s

    def wm(x, lo, hi):
        s = (t > lo + 1e-9) & (t <= hi + 1e-9)
        return float(x[s].mean())

    i0, i1 = int(np.argmin(abs(t - t0))), len(t) - 1
    sel = t > t0
    x = np.degrees(th[sel]) - np.degrees(th[sel]).mean()
    f = np.fft.rfftfreq(len(x), float(np.median(np.diff(t))))
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    pp2 = [float(np.ptp(np.degrees(th[(t > s0) & (t <= s0 + 2)]))) for s0 in np.arange(t0, t1 - 1.99, 2)]
    fpk = float(f[1:][np.argmax(spec[1:])])
    zeta = math.log(pp2[0] / pp2[-1]) / (2 * math.pi * fpk * 2 * (len(pp2) - 1)) if (fpk > 0 and len(pp2) > 1) else None
    d_track = (wm(tin, t1 - mean_s, t1) - wm(tin, t0, t0 + mean_s)) * 1e3
    return {"window_s": [t0, t1], "mean_window_s": mean_s, "track_point_body_xz_m": [xtr, ztr],
            "origin_in_plane_endpoints_mm": float(oin[i1] - oin[i0]) * 1e3,
            "track_point_in_plane_endpoints_mm": float(tin[i1] - tin[i0]) * 1e3,
            "pitch_change_endpoints_deg": float(np.degrees(th[i1] - th[i0])),
            "track_point_in_plane_4s_means_mm": d_track,
            "pitch_change_4s_means_deg": float(np.degrees(wm(th, t1 - mean_s, t1) - wm(th, t0, t0 + mean_s))),
            "rocking_peak_Hz": fpk, "pitch_pp_per_2s_deg": pp2, "rocking_zeta_from_pp_decay": zeta,
            "criterion_mm": 0.1, "within_0p1mm": bool(abs(d_track) <= 0.1),
            "basis": "dynamics 5.35.2 L5: track-point 4 s window means (rocking 0.5-0.7 Hz cancels), "
                     "origin end points are mostly rigid rocking about the contact"}


def v16_replica_mm(r: dict[str, Any], row_levels: list[dict[str, Any]], q32: bool) -> list[float]:
    """1-DoF heave replica of a V16 load-step run (dynamics 5.35.2 V16a, ``s9_p1p2_judge_rev50.v16_replica``
    ported): loaded mass N / g, the run's load-step schedule, Chrono SCM node law (Bekker value
    replaces the elastic try, ``SCMTerrain.cpp:1394-1465``), area = Chrono contact nodes x h^2 and
    b = contact hull 2A / P at the last level; ``q32`` rounds the hit height to float32 at the
    machine pad height z = -1.0469 m. Returns the sinkage [mm] at the end of every level."""
    sc = r["load_steps"]["schedule"]
    soil = r["meta"]["scm"]["soil"]["chrono"]
    n_h, b = row_levels[-1]["n_contact"], row_levels[-1]["b_hull_m"]
    h = float(r["args"]["grid"])
    area = n_h * h * h
    m = float(r["meta"]["normal_load_N"]) / G
    k_el, kphi, kc, n, r_d = soil["elastic_K"], soil["Kphi"], soil["Kc"], soil["n"], soil["damping_R"]
    coef = kc / b + kphi
    z0w = -1.0469

    def poly(u):
        u = min(max(u, 0.0), 1.0)
        return 10 * u ** 3 - 15 * u ** 4 + 6 * u ** 5

    def factor(t):
        for row in sc:
            if t < row["t_hold_start_s"]:
                return row["from_factor"] + (row["factor"] - row["from_factor"]) * poly((t - row["t_ramp_start_s"]) / row["ramp_s"])
            if t < row["t_hold_end_s"]:
                return row["factor"]
        return sc[-1]["factor"]

    dt = 1e-4
    z = v = sp = sy = 0.0
    marks = {round(row["t_hold_end_s"] / dt): row["level"] for row in sc}
    out = [math.nan] * len(sc)
    for k in range(int(round(sc[-1]["t_hold_end_s"] / dt))):
        zw = z0w + z
        if q32:
            zw = float(np.float32(zw))
        s = z0w - zw
        sig = k_el * (s - sp)
        force = 0.0
        if sig > 0:
            if sig > sy:
                sig = coef * max(s, 0.0) ** n
                sy = sig
                sp = s - sig / k_el
            sig += -v * r_d
            force = sig * area
        v += dt * (force / m - G * factor(k * dt))
        z += dt * v
        if (k + 1) in marks:
            out[marks[k + 1]] = -z * 1e3
    return out


def load(case_dir: Path) -> dict[str, Any]:
    return json.loads((case_dir / "result.json").read_text("utf-8"))


def cases(folder: Path) -> dict[str, dict[str, Any]]:
    out = {}
    for d in sorted(p for p in folder.iterdir() if p.is_dir() and (p / "result.json").exists()):
        out[d.name] = load(d)
    return out


def batch_cost(folder: Path) -> dict[str, Any] | None:
    if not (folder / "batch.json").exists():
        return None
    b = json.loads((folder / "batch.json").read_text("utf-8"))
    return {"folder": b["folder"], "parallel": b["parallel"], "failed": b["failed"],
            "wall_serial_s": b["wall_serial_s"], "est_serial_s": b["est_serial_s"],
            "wall_over_est": b["wall_serial_s"] / b["est_serial_s"] if b["est_serial_s"] else None,
            "per_case": [{k: c[k] for k in ("case", "rc", "wall_s", "est_s")} for c in b["cases"]],
            "note": "P-cores shared with the main-tree YAML regression R3 (8 P-cores) and 2 S9 runs at a time: contended"}


def replica_settle_m(area_m2: float, n_load_N: float, soil: str, *, ramp_s: float, t_end_s: float = 2.0,
                     dt: float = 1e-4, z0: float = 0.0005) -> float:
    """1-DoF heave replica of the single-pad settle (s9_pad_settle_replica.py generalised: SCM law
    SCMTerrain.cpp:1394-1465 with Kc / b omitted, i.e. G1 Kc = 0 only). Final sinkage [m]."""
    c = SOILS[soil]["chrono"]
    if c["Kc"] != 0.0:
        raise ValueError("replica only for Kc = 0 sets")
    kphi, k_el, r_d, n = c["Kphi"], c["elastic_K"], c["damping_R"], c["n"]
    m = n_load_N / G
    z, v, sp, sy = z0, 0.0, 0.0, 0.0
    for k in range(int(round(t_end_s / dt))):
        t = k * dt
        if ramp_s > 0:
            u = min(t / ramp_s, 1.0)
            f = 10 * u ** 3 - 15 * u ** 4 + 6 * u ** 5
        else:
            f = 1.0
        s = -z
        sig = k_el * (s - sp)
        force = 0.0
        if sig > 0:
            if sig > sy:
                sig = kphi * s ** n
                sy = sig
                sp = s - sig / k_el
            sig += -v * r_d
            force = sig * area_m2
        v += dt * (force / m - G * f)
        z += dt * v
    return -z


def node_end(r: dict[str, Any]) -> dict[str, Any]:
    return r["node_series"][-1]


def summary_v0p(folder: Path) -> dict[str, Any]:
    rows = []
    for name, r in cases(folder).items():
        n = node_end(r)
        h = float(r["args"]["grid"])
        N = float(r["meta"]["normal_load_N"])
        a_nodes = n["n_contact"] * h * h
        rep = replica_settle_m(a_nodes, N, r["args"]["soil"], ramp_s=float(r["args"]["load_ramp"]),
                               t_end_s=float(r["args"]["t_end"]))
        sc = n["sinkage_mean_contact_m"]
        rows.append({"case": name, "grid_m": h, "n_contact": n["n_contact"], "n_inside": n["n_inside"],
                     "node_sinkage_mm": sc * 1e3, "geometric_sinkage_mm": n["sinkage_geometric_m"] * 1e3,
                     "node_minus_geometric_mm": n["node_minus_geometric_m"] * 1e3,
                     "criterion_node_minus_geometric_mm": 0.05,
                     "within_0p05mm": abs(n["node_minus_geometric_m"]) <= 0.05e-3,
                     "replica_ramp_mm": rep * 1e3, "replica_basis": f"A = n_contact h^2 = {a_nodes:.6f} m^2",
                     "node_vs_replica_pct": (sc - rep) / rep * 100.0, "criterion_pct": 0.5,
                     "within_0p5pct": abs((sc - rep) / rep) <= 5e-3,
                     "Fz_over_load": r["settle_end"]["Fz_over_weight"],
                     "first_record_Fz_N": r["first_step"]["first_record_Fz_scm_N"],
                     "us_per_step": r["us_per_step"], "threads": r["meta"].get("num_threads_chrono")})
    rows.append({"case": "V0 (iii) 2 cm, cad 2026-10-26 (5.34.10 table)", "grid_m": 0.02, "n_contact": 157,
                 "node_minus_geometric_mm": -9.5e-6, "node_sinkage_mm": 7.738, "replica_ramp_mm": 7.738,
                 "note": "earlier run, Chrono-default SCM threads"})
    return {"batch": "P1-V0'", "criteria": "5.34.13 P1-V0': node - geometric <= 0.05 mm; sinkage = 1-DoF replica "
                                           "with the same contact node count +-0.5 %",
            "case_def": "single pad G1 RL type B, fixed joint, load 72.8 kN Poly345 1 s + 1 s hold, Δt 1e-4 s, mesh",
            "rows": rows, "cost": batch_cost(folder)}


def v16_reference_m(soil: str, load_N: float, n_contact: int, h: float, b_m: float | None) -> float:
    c = SOILS[soil]["chrono"]
    k = c["Kphi"] + (c["Kc"] / b_m if (c["Kc"] and b_m) else 0.0)
    return (load_N / (n_contact * h * h * k)) ** (1.0 / c["n"])


def summary_v16(folder: Path) -> dict[str, Any]:
    out_rows, conv = [], {}
    all_cases = cases(folder)
    for name, r in all_cases.items():
        soil, leg, h = r["args"]["soil"], r["args"]["leg"], float(r["args"]["grid"])
        n_exp = SOILS[soil]["chrono"]["n"]
        row: dict[str, Any] = {"case": name, "soil": soil, "leg": leg, "grid_m": h, "pad_variant": r["args"]["pad_variant"],
                               "obj_bottom_minus_yaml_mm": r["meta"]["obj_bottom_minus_yaml_bottom_m"] * 1e3,
                               "us_per_step": r["us_per_step"]}
        if r.get("load_steps") is None:  # V16d sudden
            n = node_end(r)
            N = float(r["meta"]["normal_load_N"])
            a = n["n_contact"] * h * h
            sud = replica_settle_m(a, N, soil, ramp_s=0.0, t_end_s=float(r["args"]["t_end"]))
            ramp = replica_settle_m(a, N, soil, ramp_s=1.0, t_end_s=float(r["args"]["t_end"]))
            row.update(kind="V16d sudden load (record)", node_sinkage_mm=n["sinkage_mean_contact_m"] * 1e3,
                       geometric_sinkage_mm=n["sinkage_geometric_m"] * 1e3, n_contact=n["n_contact"],
                       replica_sudden_mm=sud * 1e3, replica_ramp_mm=ramp * 1e3,
                       chrono_over_replica_ramp=n["sinkage_mean_contact_m"] / ramp,
                       replica_sudden_over_ramp=sud / ramp,
                       criterion="same side and size (+-20 %) as the replica dynamic excess (record only)")
            out_rows.append(row)
            continue
        levels = []
        z100 = None
        for sch, lv in zip(r["load_steps"]["schedule"], r["load_steps"]["levels"], strict=True):
            e, s0 = lv["end"], lv["start"]
            n = e["nodes"]
            b = (2.0 * n["contact_hull_area_m2"] / n["contact_hull_perimeter_m"]) if n["contact_hull_area_m2"] else None
            zc = n["sinkage_mean_contact_m"]
            ent = {"factor": sch["factor"], "load_N": e["load_N"], "hold_s": sch["hold_s"], "tau_est_s": sch["tau_est_s"],
                   "Fz_scm_over_load": e["Fz_scm_N"] / e["load_N"], "n_contact": n["n_contact"],
                   "n_sigma_negative": n["n_sigma_negative"], "patches": n["contact_patches"],
                   "b_hull_m": b, "node_sinkage_mm": None if zc is None else zc * 1e3,
                   "geometric_sinkage_mm": n["sinkage_geometric_m"] * 1e3,
                   "geometric_sinkage_obj_mm": n["sinkage_geometric_obj_m"] * 1e3,
                   "node_minus_geometric_mm": None if n["node_minus_geometric_m"] is None else n["node_minus_geometric_m"] * 1e3,
                   "hold_sinkage_progress_mm": (None if (zc is None or s0["nodes"]["sinkage_mean_contact_m"] is None)
                                                else (zc - s0["nodes"]["sinkage_mean_contact_m"]) * 1e3),
                   "unloading": sch["unloading"]}
            if not sch["unloading"] and zc is not None and n["n_contact"] > 0:
                zr = v16_reference_m(soil, e["load_N"], n["n_contact"], h, b)
                ent["V16a_reference_mm"] = zr * 1e3
                ent["V16a_pressure_diff_pct"] = n_exp * (zc - zr) / zr * 100.0
                ent["V16a_criterion_pct"] = 0.5 if soil == "G1" else 1.0
                ent["V16a_within"] = abs(ent["V16a_pressure_diff_pct"]) <= ent["V16a_criterion_pct"]
                if sch["factor"] == 1.0:
                    z100 = (zc, e["load_N"], n["n_contact"])
            if sch["unloading"] and z100 is not None and zc is not None:
                k_el = SOILS[soil]["chrono"]["elastic_K"]
                rec_m = z100[0] - zc
                pred = (z100[1] - e["load_N"]) / (k_el * z100[2] * h * h)
                ent["V16c_recovery_mm"] = rec_m * 1e3
                ent["V16c_predicted_mm"] = pred * 1e3
                ent["V16c_diff_pct"] = (rec_m - pred) / pred * 100.0
                ent["V16c_criterion_pct"] = 2.0
                ent["V16c_within"] = abs(ent["V16c_diff_pct"]) <= 2.0
            levels.append(ent)
        if n_exp < 1.0 and levels and levels[-1]["n_contact"]:
            # 5.35.2 V16a (U-S9P-3): for n << 1 the static virgin reference is replaced by the 1-DoF replica
            # with the same schedule (dynamic plastic excess of the runner's loaded mass N / g)
            rep64 = v16_replica_mm(r, levels, False)
            rep32 = v16_replica_mm(r, levels, True)
            for ent, a64, a32 in zip(levels, rep64, rep32, strict=True):
                zc = ent["node_sinkage_mm"]
                ent["V16a_replica_f64_mm"], ent["V16a_replica_f32_mm"] = a64, a32
                if zc is None or ent["factor"] < 0.5:
                    ent["V16a_replica_note"] = "record only (25 % level: first-contact pre-compression, 5.35.1)"
                    continue
                lo, hi = min(a64, a32), max(a64, a32)
                near = min(abs(zc - a64), abs(zc - a32))
                ent["V16a_replica_rel_nearest"] = near / max(abs(a64), 1e-12)
                ent["V16a_replica_in_range"] = bool(lo <= zc <= hi)
                ent["V16a_replica_within"] = bool(ent["V16a_replica_in_range"] or ent["V16a_replica_rel_nearest"] <= 0.01)
        row.update(kind="V16a-c load steps", levels=levels)
        out_rows.append(row)
        if z100 is not None:
            conv.setdefault((soil, leg), {})[h] = z100[0]
    v16b = []
    for (soil, leg), zz in sorted(conv.items()):
        ref_h = min(zz)
        ent = {"soil": soil, "leg": leg, "reference_grid_m": ref_h, "node_sinkage_100pct_mm": {f"{k:g}": v * 1e3 for k, v in zz.items()}}
        rng = PHASE_RANGE_PCT.get((soil, leg))
        diffs = {}
        for hh, z in zz.items():
            if hh == ref_h:
                continue
            d = (z - zz[ref_h]) / zz[ref_h] * 100.0
            e = {"diff_vs_ref_pct": d}
            if rng is not None:
                lo, hi = rng[GRID_INDEX[hh]]
                e.update(phase_range_pct=[lo, hi], within_range=lo <= d <= hi)
            diffs[f"{hh:g}"] = e
        ent["diffs"] = diffs
        if rng is None:
            ent["note"] = "no 5.31.8 phase range for this soil (G1 n = 1: sinkage error = -node-area error)"
        v16b.append(ent)
    return {"batch": "P1-V16a-c, V16b', V16d",
            "criteria": {"V16a": "n |z_node - z_ref| / z_ref <= 0.5 % (G1) / 1 % (J1); z_ref = (F / (N_h h^2 (Kc / b_hull + Kphi)))^(1/n), "
                                 "N_h = Chrono contact nodes, b_hull = 2 A / P of the contact-node hull; "
                                 "n < 1 (J1, J2) since 5.35.2 (U-S9P-3): node sinkage vs the 1-DoF replica with the "
                                 "same schedule inside [f64, f32] or within 1 % of the nearer (levels >= 50 %)",
                         "V16b": "diff vs the finest grid within the 5.31.8 phase range of that grid",
                         "V16c": "recovery 100 -> 50 % = dF / (K N_h h^2) +-2 %",
                         "V16b'": "J2 B rear 2 cm outside the range (warning), 1 cm inside",
                         "type_A_rear": "V16a judged on type B (OBJ bottom = YAML bottom); for type A rear the OBJ-bottom "
                                        "geometric sinkage (geometric_sinkage_obj_mm, 0.044 mm deeper) is the comparison basis"},
            "case_def": "single pad, fixed joint, type B (dwg_rear250: RL 250 / FL 330), load steps 25/50/75/100 -> 50 % of the "
                        "design load (Poly345 1 s first, 0.5 s between), hold max(1 s, 5 tau); Δt 1e-4 s, mesh ray targets, 4 SCM threads",
            "rows": out_rows, "V16b": v16b, "cost": batch_cost(folder)}


def summary_l(folder: Path) -> dict[str, Any]:
    cs = cases(folder)
    out: dict[str, Any] = {"batch": "P1-L1 ... L6 (5.33.9, 5.34.4)", "cost": batch_cost(folder)}
    l1 = []
    for soil in ("J1", "G1"):
        nat = next((r for k, r in cs.items() if k.startswith(f"L1_{soil}_") and "native" in k), None)
        bp = next((r for k, r in cs.items() if k.startswith(f"L1_{soil}_") and "bprime" in k), None)
        if nat is None or bp is None:
            continue
        sn, sb = nat["settle_end"], bp["settle_end"]
        l1.append({"soil": soil, "grid_m": nat["args"]["grid"],
                   "bprime_scm_tangential_abs_max_N": bp["scm_tangential_abs_max_N"],
                   "native_scm_tangential_abs_max_N": nat["scm_tangential_abs_max_N"],
                   "Fz_native_N": sn["Fz_scm_N"], "Fz_bprime_N": sb["Fz_scm_N"],
                   "Fz_rel_diff_pct": (sb["Fz_scm_N"] - sn["Fz_scm_N"]) / sn["Fz_scm_N"] * 100.0,
                   "sinkage_native_mm": sn["sinkage_mm"], "sinkage_bprime_mm": sb["sinkage_mm"],
                   "sinkage_rel_diff_pct": (sb["sinkage_mm"] - sn["sinkage_mm"]) / sn["sinkage_mm"] * 100.0,
                   "node_sinkage_native_mm": sn["nodes"]["sinkage_mean_contact_m"] * 1e3,
                   "node_sinkage_bprime_mm": sb["nodes"]["sinkage_mean_contact_m"] * 1e3,
                   "criterion": "bprime |F_t| = 0 exactly; settle Fz and sinkage diff <= 0.1 %"})
    out["L1"] = l1
    l2 = []
    for k, r in cs.items():
        if not k.startswith("L2_"):
            continue
        h = r["hold"]
        F = r["force_N"]
        # the share mass rings on k_t (about 3 Hz, zeta about 0.03, decay time about 1.5 s): values of the
        # last 5 s of the hold as well (ringing mostly gone), from the 1 ms series
        z = np.load(folder / k / "series.npz")
        t = z["t"]
        late = t >= t[-1] - 5.0
        x = z["x"]
        a0 = (t >= t[-1] - 5.0) & (t < t[-1] - 4.5)
        a1 = t >= t[-1] - 0.5
        ft = -(z["Fx_scm"] + z["Ft_bush_x"])
        last5 = {"window_s": [float(t[late][0]), float(t[-1])],
                 "drift_window_means_mm": float((x[a1].mean() - x[a0].mean()) * 1e3),
                 "Ft_pp_rel": float(np.ptp(ft[late]) / F),
                 "Ft_over_F": float(ft[late].mean() / F),
                 "step_range_rel_max": float((z["Fx_step_max"][late] - z["Fx_step_min"][late]).max() / F),
                 "x_mean_mm": float(x[late].mean() * 1e3)}
        # 5.35.2 (U-S9P-3): judged on the last 5 s (hold start + 5 s on); slip sum = main indicator
        last5["drift_criterion_mm"] = 0.01
        last5["drift_within"] = bool(abs(last5["drift_window_means_mm"]) <= 0.01)
        l2.append({"last_5s": last5, "case": k, "judged_window": "last_5s (5.35.2)",
                   "slip_sum_main_indicator_mm": h["slip_total_x_mm"], "force_N": F, "drift_mm": h["drift_mm"], "drift_window_means_mm": h["drift_window_means_mm"],
                   "drift_velocity_m_s": h["drift_velocity_m_s"], "Ft_over_F": h["Ft_over_F"],
                   "Ft_step_range_rel": (h["Ft_step_range_N"][1] - h["Ft_step_range_N"][0]) / F,
                   "x_mean_mm": h["x_mean_mm"], "elastic_expected_mm": h["elastic_expected_mm"],
                   "elastic_ratio": h["x_mean_mm"] / h["elastic_expected_mm"] if h["elastic_expected_mm"] else None,
                   "slip_total_x_mm": h["slip_total_x_mm"], "tilt_deg_max": h["tilt_deg_max"],
                   "limit_N": r["limit_N"], "F_over_limit": F / r["limit_N"] if r["limit_N"] else None,
                   "window_s": h["window_s"],
                   "criterion": "last 5 s: drift (0.5 s window means) <= 0.01 mm with the slip sum as the main "
                                "indicator (5.35.2); F_t = F +-0.5 %, step range <= 1 %, elastic F / k_t +-1 %; "
                                "whole-hold drift_mm kept as a record (elastic approach tail, proportional to F)"})
    out["L2"] = l2
    l3 = []
    for k, r in cs.items():
        if k.startswith("L3_"):
            h = r["hold"]
            l3.append({"case": k, "force_N": r["force_N"], "limit_N": r["limit_N"], "Ft_over_limit_mean": h["Ft_over_limit"],
                       "Ft_over_limit_last_1s": h["Ft_over_limit_last_1s"], "slip_total_x_mm": h["slip_total_x_mm"],
                       "window_s": h["window_s"], "criterion": "F_t / limit = 1 +-2 % while sliding"})
    out["L3"] = l3
    l4 = []
    for k, r in cs.items():
        if k.startswith("L4_"):
            # 5.35.2 (U-S9P-3): tilt judged while loaded (SCM normal > 1 % of the full load); the air phase
            # after the first-contact pre-compression rebound (F_z = 0) is excluded
            z = np.load(folder / k / "series.npz")
            n_full = float(r["meta"]["normal_load_N"])
            loaded = z["Fz_scm"] > L4_LOADED_FRACTION * n_full
            tilt_loaded = float(z["tilt_deg"][loaded].max()) if loaded.any() else None
            t_air = z["t"][~loaded & (z["t"] > z["t"][np.argmax(loaded)])] if loaded.any() else np.array([])
            l4.append({"case": k, "k_sw_N_m_rad": r["meta"]["k_sw_N_m_rad"], "tilt_deg_max_all": r["tilt_deg_max_all"],
                       "tilt_deg_max_loaded": tilt_loaded,
                       "t_tilt_max_all_s": float(z["t"][int(np.argmax(z["tilt_deg"]))]),
                       "loaded_rule": f"SCM normal > {L4_LOADED_FRACTION:g} x full load {n_full:.0f} N",
                       "unloaded_after_first_load_s": [float(t_air[0]), float(t_air[-1])] if t_air.size else None,
                       "tilt_deg_end": r["tilt_deg_end"], "sinkage_end_mm": -r["z_bottom_end_mm"],
                       "Fz_end_N": r["Fz_scm_end_N"], "swivel": r.get("swivel"),
                       "within_0p5deg_loaded": None if tilt_loaded is None else bool(tilt_loaded <= 0.5),
                       "criterion": "tilt while loaded (> 1 % N) <= 0.5 deg (5.35.2); k_sw 0: instability record"})
    out["L4"] = l4
    l5 = []
    for k, r in cs.items():
        if k.startswith("L5_"):
            l5.append({"case": k, "settle_drift": r.get("settle_drift"), "settle_last_1s": r.get("settle_last_1s"),
                       "track_point_split": l5_split(folder / k, r),
                       "track_utilisation": r["end"].get("track_utilisation"),
                       "equilibrium_rel_error": r["end"]["equilibrium_rel_error"],
                       "first_step_force_norm_max_N": r["first_step"]["force_norm_max_N"],
                       "us_per_step": r["us_per_step"],
                       "criterion": "10 s drift <= 0.1 mm judged on the track-point 4 s window means "
                                    "(track_point_split, 5.35.2); origin end points recorded; track utilisation recorded"})
    out["L5"] = l5
    l6 = []
    for k, r in cs.items():
        if k.startswith("L6_"):
            h = r["hold"]
            m_tot = float(r["meta"]["normal_load_N"]) / G
            dt = float(r["args"]["dt"])
            ref = r["force_N"] * dt / m_tot
            l6.append({"case": k, "joint": r["args"]["joint"], "dt_s": dt, "drift_velocity_m_s": h["drift_velocity_m_s"],
                       "F_dt_over_M_m_s": ref, "ratio": h["drift_velocity_m_s"] / ref, "tilt_deg_max": h["tilt_deg_max"],
                       "p1_l6": h["p1_l6"], "Fx_scm_abs_max_N": h["Fx_scm_abs_max_N"],
                       "criterion": "fixed: drift = F dt / M +-5 %; spherical: record (5.34.4), not judged"})
    out["L6"] = l6
    return out


def summary_p2(folder: Path) -> dict[str, Any]:
    cs = cases(folder)
    rows = {}
    for k, r in cs.items():
        soil, lvl = r["args"]["soil"], r["args"]["level"]
        s = r["settle_last_1s"]
        p0 = SOILS[soil]["crawler_settle_P0"] if lvl == "top" else None
        rows[k] = {"soil": soil, "level": lvl, "pad_grid_m": r["args"]["grid"], "crawler_grid_m": r["args"]["crawler_grid"],
                   "P2-a_first_step_force_N": r["first_step"]["force_norm_max_N"],
                   "P2-a_start_rise_mm": r["start_rise"]["z_origin_max_mm"] - r["start_rise"]["z_origin_start_mm"],
                   "pitch_mean_deg": s["pitch_mean_deg"], "z0_mean_mm": s["z_origin_mean_mm"], "roll_mean_deg": s["roll_mean_deg"],
                   "P2-b_replica": "pending (dynamics-expert: J1 / J2 Kc/b replica; S1 / G1 middle-bottom same-phase replica)",
                   "P2-c_pitch_pp_deg": s["pitch_pp_deg"], "P2-d_normal_over_weight": s["normal_over_weight"],
                   "P2-f_vs_P0": None if p0 is None else {
                       "P0_pitch_deg": p0["pitch_deg"], "P0_z0_mm": p0["z0_mm"],
                       "pitch_pct": (s["pitch_mean_deg"] - p0["pitch_deg"]) / p0["pitch_deg"] * 100.0,
                       "z0_pct": (s["z_origin_mean_mm"] - p0["z0_mm"]) / p0["z0_mm"] * 100.0, "warn_over_pct": 10.0},
                   "us_per_step": r["us_per_step"], "build_s": r["build_s"], "threads": r.get("num_threads_chrono")}
    p2e = []
    for soil in ("J1", "S1"):
        a = next((v for k, v in rows.items() if k.startswith(f"P2-1_{soil}_")), None)
        b = next((v for k, v in rows.items() if k.startswith(f"P2-2_{soil}_")), None)
        if a and b:
            p2e.append({"soil": soil, "M14s_pitch_deg": a["pitch_mean_deg"], "single2cm_pitch_deg": b["pitch_mean_deg"],
                        "pitch_rel_pct": (a["pitch_mean_deg"] - b["pitch_mean_deg"]) / b["pitch_mean_deg"] * 100.0,
                        "M14s_z0_mm": a["z0_mean_mm"], "single2cm_z0_mm": b["z0_mean_mm"],
                        "z0_rel_pct": (a["z0_mean_mm"] - b["z0_mean_mm"]) / b["z0_mean_mm"] * 100.0,
                        "criterion_pct": 2.0, "note": "crawler 4 cm (M14s) vs 2 cm (single terrain)"})
    return {"batch": "P2-1 ... P2-3 (5.34.11 criteria P2-a ... P2-f, user decision 2026-10-26)",
            "criteria": {"P2-a": "first-step SCM force <= 100 N, start rise <= 0.1 mm",
                         "P2-b": "same node-phase replica: <= 1 % (G1, S1); J1 / J2 vs Kc/b replica <= 3 % (provisional)",
                         "P2-c": "last 1 s pitch p-p <= 0.02 deg", "P2-d": "normal sum / weight 1 +- 0.002",
                         "P2-e": "crawler 4 cm vs 2 cm pitch, z0 <= 2 %", "P2-f": "vs P0 record only, warn > 10 %"},
            "case_def": "machine settle, gravity Poly345 3 s + hold 2 s, judged on the last 1 s mean; type B pads, (b'), Δt 1e-4 s, "
                        "mesh ray targets, 4 SCM threads",
            "G1_top_reference": "M14s G1 top (5.34.11): pitch 0.151153 deg, z0 -1.2693 mm",
            "rows": rows, "P2-e": p2e, "cost": batch_cost(folder)}


P2P_RANGE_MARGIN = (0.005, 0.05)
"""P2'-b J1 / J2 margin around the replica f64-f32 range (deg, mm) (5.35.4, U-S9P-2; record since U-S9P-4)."""
P2P_HEALTH_LIMIT = (0.03, 0.5)
"""P2'-b J1 / J2 health limit vs the replica f64 (deg, mm) (5.36.3, U-S9P-4 (c) 2026-10-26)."""


def p2prime_references() -> dict[str, dict[str, Any]]:
    """5.35.4 P2' comparison values from the dynamics rev. 50 JSON (``*_dp2e6_zt_t8``, f64 and f32)."""
    doc = json.loads(DYN_REV50_JSON.read_text("utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for c in doc["crawler_replica_variants"]:
        if not c["case"].endswith("_dp2e6_zt_t8"):
            continue
        key = "f32" if c["float32_hit"] else "f64"
        out.setdefault(c["soil"], {})[key] = {k: c[k] for k in ("pitch_deg", "z0_mm", "start_rise_max_mm", "pitch_pp_deg")}
    return out


def summary_p2prime(folder: Path) -> dict[str, Any]:
    """P2' (dynamics 5.35.4, 5.35.5 #2; U-S9P-1 / 2): dashpot settle 8 s, judged on 7-8 s.
    z0 = body-origin z change from the first record [mm] (as the dynamics replica comparison)."""
    refs = p2prime_references()
    rows = {}
    for k, r in cases(folder).items():
        soil = r["args"]["soil"]
        d = np.load(folder / k / "series.npz")
        t = d["t_s"]
        t_end = float(t[-1])
        sel = t > t_end - 1.0 + 1e-9
        z = (d["body_pos_m"][:, 2] - d["body_pos_m"][0, 2]) * 1e3
        pitch = d["roll_pitch_deg"][:, 1]
        roll = d["roll_pitch_deg"][:, 0]
        s = r["settle_last_1s"]
        early = t <= 5.0 + 1e-9
        rise = float(z[early].max())
        pm, zm = float(pitch[sel].mean()), float(z[sel].mean())
        ref = refs.get(soil, {})
        row: dict[str, Any] = {
            "soil": soil, "level": r["args"]["level"], "pad_grid_m": r["args"]["grid"],
            "crawler_grid_m": r["args"]["crawler_grid"], "t_end_s": t_end, "judge_window_s": [t_end - 1.0, t_end],
            "settle_dashpot": r["gravity_schedule"].get("settle_dashpot"),
            "P2'-a_first_step_force_N": r["first_step"]["force_norm_max_N"],
            "P2'-a_start_rise_mm": rise, "P2'-a_start_rise_t_s": float(t[early][int(np.argmax(z[early]))]),
            "P2'-a_within": bool(r["first_step"]["force_norm_max_N"] <= 100.0 and rise <= 2.0),
            "pitch_mean_deg": pm, "z0_mean_mm": zm, "roll_mean_deg": float(roll[sel].mean()),
            "P2'-c_pitch_pp_deg": float(np.ptp(pitch[sel])), "roll_pp_deg": float(np.ptp(roll[sel])),
            "P2'-c_within": bool(np.ptp(pitch[sel]) <= 0.02),
            "P2'-d_normal_over_weight": s["normal_over_weight"],
            "P2'-d_within": bool(abs(s["normal_over_weight"] - 1.0) <= 0.002),
            "replica_f64": ref.get("f64"), "replica_f32": ref.get("f32"),
            "us_per_step": r["us_per_step"], "wall_s": r["wall_s"], "build_s": r["build_s"],
            "threads": r.get("num_threads_chrono"), "placement": r.get("placement")}
        if soil in ("G1", "S1") and ref:
            p_ref, z_ref = ref["f64"]["pitch_deg"], ref["f64"]["z0_mm"]
            row["P2'-b"] = {"basis": "(a) replica f64 (5.35.4), <= 1 %", "pitch_ref_deg": p_ref, "z0_ref_mm": z_ref,
                            "pitch_rel_pct": (pm - p_ref) / p_ref * 100.0, "z0_rel_pct": (zm - z_ref) / z_ref * 100.0}
            row["P2'-b"]["within"] = bool(abs(row["P2'-b"]["pitch_rel_pct"]) <= 1.0 and abs(row["P2'-b"]["z0_rel_pct"]) <= 1.0)
        elif ref:
            # U-S9P-4 (c) 2026-10-26 (dynamics 5.36.3): the J1 / J2 settle state is a record; health limit
            # |pitch - replica f64| <= 0.03 deg, |z0 - replica f64| <= 0.5 mm. The former U-S9P-2 range
            # +- (0.005 deg, 0.05 mm) is kept as a record (two samples of the rounding-pattern spread, 5.36.2)
            pr = sorted((ref["f64"]["pitch_deg"], ref["f32"]["pitch_deg"]))
            zr = sorted((ref["f64"]["z0_mm"], ref["f32"]["z0_mm"]))
            mp, mz = P2P_RANGE_MARGIN
            hp, hz = P2P_HEALTH_LIMIT
            dp, dz = pm - ref["f64"]["pitch_deg"], zm - ref["f64"]["z0_mm"]
            row["P2'-b"] = {"basis": "record + health limit vs replica f64 |d pitch| <= 0.03 deg, |d z0| <= 0.5 mm "
                                     "(5.36.3, U-S9P-4 (c))",
                            "kind": "record", "pitch_ref_f64_deg": ref["f64"]["pitch_deg"], "z0_ref_f64_mm": ref["f64"]["z0_mm"],
                            "d_pitch_vs_f64_deg": dp, "d_z0_vs_f64_mm": dz, "health_limit_deg_mm": [hp, hz],
                            "health_within": bool(abs(dp) <= hp and abs(dz) <= hz),
                            "former_range_record": {
                                "basis": "replica f64-f32 range +- (0.005 deg, 0.05 mm) (5.35.4, U-S9P-2; superseded)",
                                "pitch_range_deg": pr, "z0_range_mm": zr,
                                "pitch_outside_range_deg": max(pr[0] - pm, pm - pr[1], 0.0),
                                "z0_outside_range_mm": max(zr[0] - zm, zm - zr[1], 0.0),
                                "within_range_margin": bool(pr[0] - mp <= pm <= pr[1] + mp and zr[0] - mz <= zm <= zr[1] + mz)}}
            row["P2'-b"]["within"] = row["P2'-b"]["health_within"]
        rows[k] = row
    return {"batch": "P2' (dynamics_model.md 5.35.4 / 5.35.5 #2 / 5.36.3; user decisions U-S9P-1, U-S9P-2, U-S9P-4 (c) 2026-10-26)",
            "criteria": {"P2'-a": "first-step SCM force <= 100 N, start rise (max z0 up to 5 s) <= 2 mm",
                         "P2'-b": "G1, S1: replica (a) f64 <= 1 %; J1, J2: record + health limit |d pitch| <= 0.03 deg, "
                                  "|d z0| <= 0.5 mm vs replica f64 (U-S9P-4 (c), 5.36.3); P3 judged relative to each "
                                  "case's own settle state",
                         "P2'-c": "7-8 s pitch p-p <= 0.02 deg", "P2'-d": "SCM normal sum / weight 1 +- 0.002 (last 1 s)"},
            "case_def": "machine settle, type B pads, top auger, M14s (pads 1 cm J1 / J2, 2 cm G1 / S1; crawler 4 cm), "
                        "gravity Poly345 3 s + hold 5 s, settle dashpot c_z 2e6 N s/m, c_pitch 3.4e6, c_roll 2.2e6 N m s/rad "
                        "(ASSUMPTION) full to 3 s, linear to 0 at 5 s; (b'), Δt 1e-4 s, mesh ray targets, 4 SCM threads",
            "reference_source": DYN_REV50_JSON.relative_to(ROOT).as_posix(),
            "values_only": "pass / fail decisions are dynamics-expert's; *_within flags compare with the 5.35.4 criteria",
            "rows": rows, "cost": batch_cost(folder)}


P3A_EXPECTED = {"P3a_J1_B": {"t_liftoff_s": 28.7, "end_pitch_deg": -0.44, "set_by": "rear"},
                "P3a_J1_A": {"t_liftoff_s": 27.4, "end_pitch_deg": 0.6, "set_by": "front"},
                "P3a_G1_B": {"t_liftoff_s": 25.2, "end_pitch_deg": "|.| <= 0.02"},
                "P3a_G1_A": {"t_liftoff_s": 25.0, "end_pitch_deg": "|.| <= 0.02"}}
"""dynamics 5.36.5 qualitative expectations (single-pad V16 design-load sinkage, same-speed lift);
lift start = 8.0 s; end pitch change ~ (front - rear sinkage) / 4.85 m."""
V16_JSON = OUT / "s9_P1_V16_summary.json"
LEGS = ("FL", "FR", "RL", "RR")


def v16_reference_levels(soil: str, grid_m: float) -> dict[str, Any]:
    """V16 single-pad node sinkage per virgin load level (type B; FL = front 330, RL = rear 250 pad) for
    the P3a-6 comparison, with a linear interpolation helper at a given load (record only)."""
    if not V16_JSON.exists():
        return {}
    doc = json.loads(V16_JSON.read_text("utf-8"))
    out = {}
    for row in doc["rows"]:
        if row.get("kind") != "V16a-c load steps" or row["soil"] != soil or abs(row["grid_m"] - grid_m) > 1e-9:
            continue
        lv = [(e["load_N"], e["node_sinkage_mm"]) for e in row["levels"] if not e["unloading"] and e["node_sinkage_mm"] is not None]
        out[row["leg"]] = {"case": row["case"], "pad_variant": row["pad_variant"], "levels_load_N_sinkage_mm": lv}
    return out


def _interp_sinkage_mm(levels: list[tuple[float, float]], load_N: float) -> float | None:
    if not levels:
        return None
    f, z = zip(*sorted(levels), strict=True)
    if load_N > f[-1] or load_N < f[0]:
        return None  # outside the V16 steps: no extrapolation
    return float(np.interp(load_N, f, z))


def summary_p3a(folder: Path) -> dict[str, Any]:
    """P3a open-loop lift (dynamics 5.36.5, U-S9P-5 (a)): judged items P3a-1 ... 5 as values vs criteria,
    records P3a-6 ... 10. J1 values relative to each run's own settle end (5.36.3, U-S9P-4 (c))."""
    rows = {}
    for k, r in cases(folder).items():
        p = r.get("p3a")
        if p is None:
            continue
        a = r["args"]
        lo = p["P3a-2_liftoff"]
        f1 = p["P3a-1_force_peak"]
        eq = p["P3a-3_end_equilibrium"]
        st = p["P3a-4_stroke"]
        tl = p["P3a-5_pad_tilt"]
        exp = P3A_EXPECTED.get(k, {})
        end_load = eq["pad_normal_mean_N"]
        v16 = v16_reference_levels(a["soil"], float(a["grid"]))
        node_end = (p["P3a-6_sinkage"].get("node_end") or {}).get("sinkage_mean_contact_m")
        sink_cmp = []
        for i, leg in enumerate(LEGS):
            ref_leg = "FL" if i < 2 else "RL"
            ref = v16.get(ref_leg)
            same_pad = ref is not None and (i < 2 or a["pad_variant"] == "dwg_rear250")
            sink_cmp.append({"leg": leg, "end_pad_normal_N": end_load[i],
                             "end_geometric_sinkage_mm": p["P3a-6_sinkage"]["geometric_end_m"][i] * 1e3,
                             "end_node_sinkage_mm": None if (node_end is None or node_end[i] is None) else node_end[i] * 1e3,
                             "V16_case": None if ref is None else ref["case"],
                             "V16_same_pad": same_pad,
                             "V16_interp_at_end_load_mm": (_interp_sinkage_mm(ref["levels_load_N_sinkage_mm"], end_load[i])
                                                           if same_pad else None)})
        rows[k] = {
            "soil": a["soil"], "pad_variant": a["pad_variant"], "pad_grid_m": a["grid"], "crawler_grid_m": a["crawler_grid"],
            "level": a["level"], "lift_s": a["lift_s"], "t_lift_start_s": p["t_lift_start_s"],
            "judged": {
                "P3a-1_force_peak": {"F_peak_kN": [v / 1e3 for v in f1["F_peak_N"]], "limit_kN": [v / 1e3 for v in f1["limit_N"]],
                                     "peak_over_limit": f1["peak_over_limit"], "t_peak_s": f1["t_peak_s"],
                                     "within": f1["within"]},
                "P3a-2_liftoff": {"lifted": lo["lifted"], "t_liftoff_s": lo.get("t_liftoff_s"),
                                  "t_after_lift_start_s": lo.get("t_after_lift_start_s"),
                                  "expected_t_liftoff_s": exp.get("t_liftoff_s"),
                                  "minus_expected_s": (None if lo.get("t_liftoff_s") is None or exp.get("t_liftoff_s") is None
                                                       else lo["t_liftoff_s"] - exp["t_liftoff_s"]),
                                  "recontact_after_confirm_t_s": lo.get("recontact_after_confirm_t_s"), "rule": lo["rule"]},
                "P3a-3_end_equilibrium": {"pad_normal_sum_over_weight": eq["pad_normal_sum_over_weight"],
                                          "window_s": eq["window_s"], "window_after_liftoff": eq["window_after_liftoff"],
                                          "crawler_normal_mean_N": eq["crawler_normal_mean_N"], "criterion": "1 +- 0.002",
                                          "within": eq["within"]},
                "P3a-4_stroke": {"s_motor_max_m": st["s_motor_max_m"], "limit_m": st["limit_m"], "margin_m": st["margin_m"],
                                 "within": st["within"]},
                "P3a-5_pad_tilt": {"tilt_max_loaded_deg": tl["tilt_max_loaded_deg"], "t_s": tl["t_tilt_max_loaded_s"],
                                   "criterion_deg": tl["criterion_deg"], "within": tl["within"]}},
            "records": {
                "P3a-6_sinkage": {**p["P3a-6_sinkage"], "V16_comparison": sink_cmp},
                "P3a-7_attitude": {**p["P3a-7_attitude"], "expected_end_pitch_change_deg": exp.get("end_pitch_deg")},
                "P3a-8_first_touch": p["P3a-8_first_touch"], "P3a-9_min_cylinder_force": p["P3a-9_min_cylinder_force"],
                "P3a-10_rut_track": p["P3a-10_rut_track"]},
            "end_equilibrium_total_over_weight": r["end"]["equilibrium_rel_error"] + 1.0,
            "settle_last_1s": r.get("settle_last_1s"),
            "us_per_step": r["us_per_step"], "wall_s": r["wall_s"], "build_s": r["build_s"],
            "threads": r.get("num_threads_chrono"), "placement": r.get("placement")}
    return {"batch": "P3a open-loop lift (dynamics_model.md 5.36.5; user decisions U-S9P-4 (c), U-S9P-5 (a) 2026-10-26)",
            "criteria": {"P3a-1": "cylinder force peak per leg <= 278.7 kN (FL, FR) / 199.6 kN (RL, RR), 210 bar extension",
                         "P3a-2": "crawler SCM normal < 1 % W for 0.1 s within the run (lift-off)",
                         "P3a-3": "last 1 s pad SCM normal sum / W = 1 +- 0.002 after lift-off",
                         "P3a-4": "max s_motor <= 0.6848 m",
                         "P3a-5": "pad tilt while loaded (> 1 % of the leg design load) <= 0.5 deg",
                         "P3a-6..10": "records: sinkage history (V16 comparison), pitch / roll transient vs the settle end, "
                                      "first-touch 0.2 s SCM force rise, minimum cylinder force, rut clearance and track utilisation"},
            "case_def": "machine, top auger, M14s (pads 1 cm J1 / 2 cm G1, crawler 4 cm), settle 8 s (gravity Poly345 3 s + "
                        "hold 5 s, dashpot c_z 2e6 N s/m, c_pitch 3.4e6, c_roll 2.2e6 N m s/rad ASSUMPTION, full to 3 s, 0 at 5 s), "
                        "then four legs at v_max 20.924 mm/s (command ramp 0.1 s) for 28 s; (b'), Δt 1e-4 s, mesh ray targets, "
                        "4 SCM threads, L2b force-law actuator; F_cyl = acting force (+ = extension push)",
            "frames": "world = body axes at the start, x forward, y left, z up; pitch > 0 nose down; SCM normals along the plane normal",
            "expected_source": "dynamics_model.md 5.36.5 (qualitative, single-pad V16 design-load sinkage)",
            "values_only": "pass / fail decisions are dynamics-expert's; *within flags compare with the 5.36.5 criteria",
            "rows": rows, "cost": batch_cost(folder)}


RE1C_LIMIT_S = 10.0
"""P-S9-10 re-approach time limit of the R8 preset (``max_duration_s``)."""
RE1C_TIME_TOL_S = 0.1
RE1C_QUIET_BEFORE_S = 9.9
RE1C_MAX_TRAVEL_M = 0.04


def _c2_event_list(case_dir: Path, r: dict[str, Any]) -> list[tuple[float, str]]:
    """C2 events (absolute engine time) of an S8 case: ``controller_events.json`` (``C2Event(t_s=..,
    name='..')`` strings or dicts)."""
    p = case_dir / "controller_events.json"
    raw = json.loads(p.read_text("utf-8")) if p.exists() else (r.get("events") or [])
    out = []
    for e in raw:
        if isinstance(e, dict):
            out.append((float(e["t_s"]), str(e["name"])))
            continue
        s = str(e)
        try:
            out.append((float(s.split("t_s=")[1].split(",")[0]), s.split("name='")[1].rstrip("')")))
        except (IndexError, ValueError):
            continue
    return sorted(out)


def re1c_summary(case_dir: Path) -> dict[str, Any]:
    """RE1c positive test of the re-approach time limit (P-S9-10, control D-5): R-1 one
    ``leg_reapproach_start:RR`` after the forced-retract start and none before; R-2 exactly one
    ``WARN_LEG_REAPPROACH_NO_CONTACT:RR`` at start + 10.0 s (+-0.1 s), its meta interval
    ``no_contact``, end - start in [9.9, 10.1] s, travel < 0.04 m; R-3 no such warning on any leg
    before start + 9.9 s; R-4 no RR restart after it, no FAULT event / phase, no exception, the run
    reached its end; R-5 (record) RR ``computed_u`` after the warning (r8_series.npz). Inputs:
    run_S8C ``result.json`` (``controller_meta.lifted_reapproach``, ``event.forced_retract``,
    ``s8_end``), ``controller_events.json``, ``r8_series.npz``, ``case.log``; absolute engine times."""
    r = load(case_dir)
    ev = _c2_event_list(case_dir, r)
    cm = r.get("controller_meta") or {}
    hist = cm.get("lifted_reapproach") or []
    lr_set = (cm.get("r8") or {}).get("lifted_reapproach") or {}
    t_force = ((r.get("event") or {}).get("forced_retract") or {}).get("t_start_s")
    starts = [t for t, n in ev if n == "leg_reapproach_start:RR"]
    before = [t for t in starts if t_force is not None and t < t_force - 1e-9]
    after = [t for t in starts if t_force is not None and t >= t_force - 1e-9]
    r1 = {"t_forced_start_s": t_force, "starts_before": len(before), "starts_after": len(after),
          "ok": bool(t_force is not None and not before and len(after) == 1)}
    t0 = after[0] if after else None
    warns = [(t, n) for t, n in ev if n.startswith("WARN_LEG_REAPPROACH_NO_CONTACT:")]
    warn_rr = [t for t, n in warns if n.endswith(":RR")]
    row = None if t0 is None else next((h for h in hist if h.get("leg") == "RR"
                                        and abs(float(h.get("start_s", -1e9)) - t0) <= RE1C_TIME_TOL_S), None)
    dur = None if row is None or row.get("end_s") is None else float(row["end_s"]) - float(row["start_s"])
    r2 = {"t_start_s": t0, "warn_rr_t_s": warn_rr, "warn_minus_start_s": None if (t0 is None or not warn_rr)
          else warn_rr[0] - t0, "interval": row, "interval_duration_s": dur,
          "max_duration_s_setting": lr_set.get("max_duration_s")}
    r2["ok"] = bool(t0 is not None and len(warn_rr) == 1
                    and abs(warn_rr[0] - (t0 + RE1C_LIMIT_S)) <= RE1C_TIME_TOL_S + 1e-9
                    and row is not None and row.get("outcome") == "no_contact" and dur is not None
                    and RE1C_LIMIT_S - RE1C_TIME_TOL_S - 1e-9 <= dur <= RE1C_LIMIT_S + RE1C_TIME_TOL_S + 1e-9
                    and float(row.get("travel_m") or 0.0) < RE1C_MAX_TRAVEL_M)
    early = [] if t0 is None else [(t, n) for t, n in warns if t < t0 + RE1C_QUIET_BEFORE_S - 1e-9]
    r3 = {"early_warnings": early, "ok": bool(t0 is not None and not early)}
    t_w = warn_rr[0] if warn_rr else None
    restarts = [] if t_w is None else [t for t in starts if t > t_w + 1e-9]
    faults = [(t, n) for t, n in ev if n.startswith("FAULT")]
    phases = r.get("phases") or []
    fault_phase = any((p[1] if isinstance(p, (list, tuple)) else p) == "fault" for p in phases)
    log = case_dir / "case.log"
    log_text = log.read_text("utf-8", errors="replace") if log.exists() else ""
    exception = ("Traceback" in log_text) or ("finished: failed" in log_text)
    s8_end = r.get("s8_end") or {}
    reached = bool(s8_end.get("end_t_s") is not None and (s8_end.get("stopped_at_target") or s8_end.get("timeout")))
    r4 = {"rr_restarts_after_warning": restarts, "fault_events": faults, "fault_phase": fault_phase,
          "exception_in_log": exception, "s8_end": {k: s8_end.get(k) for k in ("end_t_s", "target_t_s", "upper_used_s",
                                                                                "stopped_at_target", "timeout",
                                                                                "final_phase")},
          "reached_end": reached}
    r4["ok"] = bool(t_w is not None and not restarts and not faults and not fault_phase and not exception and reached)
    r5: dict[str, Any] = {"note": "record only"}
    sp = case_dir / "r8_series.npz"
    if t_w is not None and sp.exists():
        with np.load(sp, allow_pickle=False) as z:
            if "computed_u" in z.files:
                ts, cu = np.asarray(z["t"], float), np.asarray(z["computed_u"], float)[:, 3]
                a = ts >= t_w - 1e-9

                def at(dt):
                    k = int(np.searchsorted(ts, t_w + dt - 1e-9))
                    return None if k >= len(ts) else float(cu[k])

                r5.update(computed_u_RR_at_warning_m_s=at(0.0), at_plus_1s=at(1.0), at_plus_5s=at(5.0),
                          min_after_m_s=float(cu[a].min()) if a.any() else None,
                          max_after_m_s=float(cu[a].max()) if a.any() else None,
                          mean_after_m_s=float(cu[a].mean()) if a.any() else None, end_m_s=float(cu[-1]))
    return {"rule": "control D-5 R-1 ... R-5 (P-S9-10 positive test)", "R-1": r1, "R-2": r2, "R-3": r3, "R-4": r4,
            "R-5": r5, "all_ok": bool(r1["ok"] and r2["ok"] and r3["ok"] and r4["ok"]),
            "lifted_reapproach_settings": lr_set}


def summary_p3b(folder: Path) -> dict[str, Any]:
    """P3b C2 levelling on SCM (control spec 284 P3-1 ... 9, 301 W-61): per ``run_S9.py level`` case the
    ``p3b`` values (``checks`` and the main items) and the C2 meta ``soil`` block; the S8 re-approach
    limit cases of the same batch run in their own run_S8C folders (named in ``<case>.log``)."""
    rows = {}
    for k, r in cases(folder).items():
        p = r.get("p3b")
        if p is None:
            continue
        a = r["args"]
        rows[k] = {"soil": a["soil"], "pad_variant": a["pad_variant"], "level": a["level"], "fs_kN": a.get("fs_kN"),
                   "pad_grid_m": a["grid"], "crawler_grid_m": a["crawler_grid"], "checks": p["checks"],
                   "departure": p["departure"], "P3-2_loc": p["P3-2_loc"], "P3-3_leg_force": p["P3-3_leg_force"],
                   "P3-4_attitude": p["P3-4_attitude"], "creep_stop": p["creep_stop"],
                   "pre_liftoff_min_F_cyl": p["pre_liftoff_min_F_cyl"], "P3-6_ready": p["P3-6_ready"],
                   "P3-8_counts": p["P3-8_false_triggers"]["counts"], "P3-9_deferred": p["P3-9_deferred"],
                   "track_utilisation": {kk: p["track_utilisation"][kk] for kk in ("max", "t_max_s", "rule")},
                   "W61_warnings": p["W61_watch"]["warnings"], "W61_rows": p["W61_watch"]["rows"],
                   "reapproach_limit_FLAG": p.get("reapproach_limit"),
                   "sensors": {k: (r.get("sensors") or {}).get(k) for k in ("pressure_grade", "imu_grade", "noise_seed",
                                                                            "zero_calibration")},
                   "c2_soil": r.get("c2_soil"), "c2_reapproach_max_duration_s":
                       (r.get("c2_lifted_reapproach") or {}).get("max_duration_s"),
                   "settle_reference": r.get("settle_reference"),
                   "us_per_step": r.get("us_per_step"), "wall_s": r.get("wall_s"),
                   "threads": r.get("num_threads_chrono"), "placement": r.get("placement")}
    sys.path.insert(0, str(HERE))
    try:
        import s9_batch  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    s8c = []
    for log in sorted(folder.glob("N_RE1c_*.log")):
        chk = s9_batch.s8c_case_check(log.read_text("utf-8", errors="replace"), log.stem)
        row = {"case": log.stem, "s8c_check": chk, "s8c_batch": chk["batch_dir"]}
        if chk["result_exists"]:
            row["re1c"] = re1c_summary(Path(chk["result_json"]).parent)
        s8c.append(row)
    return {"batch": "P3b C2 levelling on SCM (control spec 284; user decision U-S9P-6 (가) 2026-10-26)",
            "criteria": {"P3-4 (main)": "max |roll|, |pitch| (true, absolute) <= 0.2 deg over [max(two-sided creep "
                                        "stop, last READY entry), t_end] (control D-3); window < 5 s = window_short FLAG",
                         "RE1c": "R-1 ... R-4 (control D-5), R-5 record",
                         "P3-1..3, 5..9": "control spec 284 (records / FLAGs as defined there)",
                         "W-61": "spec 301 record rows (warnings, not judgements)"},
            "values_only": "pass / fail decisions are control's (284) and dynamics' (physics)",
            "rows": rows, "s8c_reapproach_limit_cases": s8c, "cost": batch_cost(folder)}


def main(argv) -> None:
    kind, folder = argv[0], Path(argv[1])
    fn = {"V0p": summary_v0p, "V16": summary_v16, "L": summary_l, "P2": summary_p2, "P2prime": summary_p2prime,
          "P3a": summary_p3a, "P3b": summary_p3b}[kind]
    res = fn(folder)
    res["source_batch"] = folder.as_posix()
    res["generator"] = "04_scripts/02_chrono/s9_batch_summary.py"
    out = Path(argv[2]) if len(argv) > 2 else OUT / (f"s9_{kind}_summary.json" if kind.startswith(("P2", "P3"))
                                                     else f"s9_P1_{kind}_summary.json")
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float), "utf-8")
    print(out)


if __name__ == "__main__":
    main(sys.argv[1:])
