"""Value summaries of the S9 P1 / P2 batches against the criteria of dynamics_model.md 5.34.13 (rev. 49).

Values and criterion comparisons only; pass / fail decisions are dynamics-expert's. Reads a batch
folder of ``s9_batch.py`` and writes one JSON to ``06_analysis/01_chrono/19_S9/``.

Usage (Chrono-dev, worktree root)::

    python -I -X utf8 04_scripts/02_chrono/s9_batch_summary.py <V0p|V16|L|P2> <batch folder> [<out.json>]

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
                                 "N_h = Chrono contact nodes, b_hull = 2 A / P of the contact-node hull",
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
        l2.append({"case": k, "force_N": F, "drift_mm": h["drift_mm"], "drift_window_means_mm": h["drift_window_means_mm"],
                   "drift_velocity_m_s": h["drift_velocity_m_s"], "Ft_over_F": h["Ft_over_F"],
                   "Ft_step_range_rel": (h["Ft_step_range_N"][1] - h["Ft_step_range_N"][0]) / F,
                   "x_mean_mm": h["x_mean_mm"], "elastic_expected_mm": h["elastic_expected_mm"],
                   "elastic_ratio": h["x_mean_mm"] / h["elastic_expected_mm"] if h["elastic_expected_mm"] else None,
                   "slip_total_x_mm": h["slip_total_x_mm"], "tilt_deg_max": h["tilt_deg_max"],
                   "limit_N": r["limit_N"], "F_over_limit": F / r["limit_N"] if r["limit_N"] else None,
                   "window_s": h["window_s"],
                   "criterion": "drift <= 0.01 mm, F_t = F +-0.5 %, step range <= 1 %, elastic F / k_t +-1 %"})
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
            l4.append({"case": k, "k_sw_N_m_rad": r["meta"]["k_sw_N_m_rad"], "tilt_deg_max_all": r["tilt_deg_max_all"],
                       "tilt_deg_end": r["tilt_deg_end"], "sinkage_end_mm": -r["z_bottom_end_mm"],
                       "Fz_end_N": r["Fz_scm_end_N"], "swivel": r.get("swivel"),
                       "criterion": "tilt <= 0.5 deg (k_sw 0: instability record)"})
    out["L4"] = l4
    l5 = []
    for k, r in cs.items():
        if k.startswith("L5_"):
            l5.append({"case": k, "settle_drift": r.get("settle_drift"), "settle_last_1s": r.get("settle_last_1s"),
                       "track_utilisation": r["end"].get("track_utilisation"),
                       "equilibrium_rel_error": r["end"]["equilibrium_rel_error"],
                       "first_step_force_norm_max_N": r["first_step"]["force_norm_max_N"],
                       "us_per_step": r["us_per_step"], "criterion": "10 s drift <= 0.1 mm, track utilisation recorded"})
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


def main(argv) -> None:
    kind, folder = argv[0], Path(argv[1])
    fn = {"V0p": summary_v0p, "V16": summary_v16, "L": summary_l, "P2": summary_p2}[kind]
    res = fn(folder)
    res["source_batch"] = folder.as_posix()
    res["generator"] = "04_scripts/02_chrono/s9_batch_summary.py"
    out = Path(argv[2]) if len(argv) > 2 else OUT / f"s9_P1_{kind}_summary.json".replace("P1_P2", "P2")
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float), "utf-8")
    print(out)


if __name__ == "__main__":
    main(sys.argv[1:])
