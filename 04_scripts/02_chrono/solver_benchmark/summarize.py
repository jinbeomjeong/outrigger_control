"""Collect 07_results/solver_benchmark/ into 06_analysis/01_chrono/01_cost/solver_benchmark.*

Writes ``solver_benchmark.json`` and ``solver_benchmark.png`` there.

Usage: python -I summarize.py   (no simulation; reads the saved per-run results)
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # python -I: the script folder is not on sys.path
import bench_common as bcm  # noqa: E402  (puts 03_src and 04_scripts/00_cad on sys.path)

RES = bcm.RESULTS_DIR
OUT = bcm.ANALYSIS_DIR
LABEL = {"QR": "SPARSE_QR", "LU": "SPARSE_LU", "PARDISO": "PARDISO_MKL"}


def load(phase: str) -> dict[str, dict]:
    out = {}
    for f in sorted((RES / phase).glob("*.json")):
        if f.name.endswith(".cfg.json"):
            continue
        out[f.stem] = json.loads(f.read_text())
    return out


def crawler_layout_note(results: dict[str, dict]) -> dict:
    """Crawler layout the stored runs were measured with (bench_case.py extra) vs the YAML.

    Runs written before layout D carry only n_crawler_spheres (18 = old 2 x 9 layout); runs
    written after it also carry crawler_layout_scheme.
    """
    counts = sorted({r["extra"]["n_crawler_spheres"] for r in results.values()})
    schemes = sorted(
        {
            r["extra"].get("crawler_layout_scheme", "2x9 bbox (pre layout D)")
            for r in results.values()
        }
    )
    return {
        "n_crawler_spheres_in_stored_results": counts,
        "layout_in_stored_results": schemes,
        "current_yaml_layout": "D rollers_plus_gapped_end_shoes, 24 spheres "
        "(contact.crawler.sphere_layout)",
        "note": "measured with the crawler layout above; the YAML is now layout D (24 spheres, "
        "bench_case.py builds it). Step cost with layout D is re-measured in the S0 "
        "cost measurement (this benchmark was not re-run).",
    }


def row(r: dict) -> dict:
    t = r["chrono_timers_us_per_step"]
    d = r["direct_solver_us_per_step"]
    ls = t["LSsetup"] + t["LSsolve"]
    reps = r["wall_us_per_step_reps"]
    return {
        "wall_us_per_step_median": round(r["wall_us_per_step_median"], 2),
        "wall_us_per_step_reps": [round(v, 2) for v in reps],
        "rep_spread_pct": round((max(reps) - min(reps)) / statistics.median(reps) * 100, 1),
        "chrono_step_us": round(t["Step"], 2),
        "ls_us": round(ls, 2),
        "ls_share_of_step": round(ls / t["Step"], 3),
        "ls_matrix_assembly_us": round(d["setup_assembly"] + d["solve_assembly"], 2),
        "ls_factor_solve_call_us": round(d["setup_solver_call"] + d["solve_solver_call"], 2),
        "collision_us": round(t["Collision"], 2),
        "setup_us": round(t["Setup"], 2),
        "advance_minus_ls_us": round(t["Advance"] - ls, 2),
        "steps_per_rep": r["steps"],
        "kkt_size": r["counts"]["kkt_size"],
        "coords_vel": r["counts"]["coords_vel"],
        "constraints": r["counts"]["constraints"],
        "contacts": r["counts"]["contacts"],
        "process_wall_s": round(r.get("process_wall_s", float("nan")), 1),
    }


def parse(stem: str) -> tuple[str, bool, str]:
    m = re.search(r"(QR|LU|PARDISO)_lock(\d)_thr(\w+)$", stem)
    return m.group(1), m.group(2) == "1", m.group(3)


def max_diff(a, b) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    return float(np.max(np.abs(a - b)))


def agreement(group: dict[str, dict], ref_key: str, keys: list[str]) -> dict:
    ref = group[ref_key]["state_after_warmup"]
    out = {}
    for k, r in group.items():
        st = r["state_after_warmup"]
        out[k] = {kk: max_diff(st[kk], ref[kk]) for kk in keys if kk in st and st[kk] is not None}
    return out


def main() -> None:
    summary: dict = {
        "date": "2026-10-20",
        "engine": "pychrono 10.0.0, Chrono-dev, Windows 11, 28 logical cores",
        "protocol": (
            "one process per case; warm-up (fixed steps) -> 3 timing windows (wall clock, median) "
            "-> "
            "1 profiling window reading per-step Chrono timers; Pardiso needs libomp.dll preload "
            "(make_system); MKL_NUM_THREADS set only in the child env ('def' = unset)"
        ),
        "timer_definitions": {
            "wall_us_per_step": "perf_counter around the step loop (L1 includes the Python "
            "ground-bushing hook)",
            "chrono_step_us": "ChSystem.GetTimerStep (per step)",
            "ls_us": "GetTimerLSsetup + GetTimerLSsolve (matrix assembly + factorisation + solve)",
            "ls_matrix_assembly_us": "ChDirectSolverLS GetTimeSetup_Assembly + "
            "GetTimeSolve_Assembly",
            "ls_factor_solve_call_us": "ChDirectSolverLS GetTimeSetup_SolverCall + "
            "GetTimeSolve_SolverCall",
            "advance_minus_ls_us": "GetTimerAdvance - ls_us (load Jacobians of bushings by finite "
            "differences, "
            "integrator bookkeeping)",
            "setup_us": "GetTimerSetup (includes the SCM loader: ray casting, contact patches, "
            "forces)",
        },
    }
    # L1
    l1 = load("l1")
    l1_out = {}
    for dt in ("1e-04", "1e-05"):
        grp = {k: v for k, v in l1.items() if k.startswith(f"dt{dt}_")}
        ref = f"dt{dt}_QR_lock0_thrdef"
        agr = agreement(grp, ref, ["sup_pos_m", "sup_quat", "leg_fz_N"])
        cases = {}
        for k, r in grp.items():
            s, lock, thr = parse(k)
            rr = row(r)
            rr.update(
                {
                    "solver": LABEL[s],
                    "lock_sparsity": lock,
                    "MKL_NUM_THREADS": thr,
                    "max_diff_vs_QR_lock0_after_warmup": agr[k],
                    "state_after_warmup_sum_fz_over_weight": r["state_after_warmup"][
                        "sum_fz_over_weight"
                    ],
                }
            )
            cases[k.replace(f"dt{dt}_", "")] = rr
        l1_out[f"dt_{dt}_s"] = {"warmup_steps": grp[ref]["warmup_steps"], "cases": cases}
    summary["full_scale_L1"] = {
        "model": (
            "superstructure (top auger) + 4 leg moving parts on ChLinkMotorLinearPosition "
            "(locked), SMC pad "
            "spheres (YAML kn/gn), crawler spheres (contact.crawler.*, layout at measurement: "
            "crawler_layout_at_measurement; 50 mm above floor in the levelled "
            "state: no crawler contact), 4 ChLoadBodyBodyBushingSpherical ground bushings + "
            "Python circular "
            "Coulomb hook; start: pads touching, unloaded (drop transient, not settled)"
        ),
        "crawler_layout_at_measurement": crawler_layout_note(l1),
        "results": l1_out,
    }
    # SCM
    scm = load("scm")
    scm_out = {}
    for delta in ("0.05", "0.02", "0.01"):
        grp = {k: v for k, v in scm.items() if k.startswith(f"d{delta}_")}
        ref = f"d{delta}_QR_lock0_thrdef"
        agr = agreement(grp, ref, ["sup_pos_m", "sup_quat", "leg_fz_N"])
        cases = {}
        for k, r in grp.items():
            s, lock, thr = parse(k)
            rr = row(r)
            sc = r["scm_timers_per_step"]
            rr.update(
                {
                    "solver": LABEL[s],
                    "lock_sparsity": lock,
                    "MKL_NUM_THREADS": thr,
                    "scm_us": round(
                        (
                            sc["active_domains"]
                            + sc["ray_testing"]
                            + sc["ray_casting"]
                            + sc["contact_patches"]
                            + sc["contact_forces"]
                            + sc["bulldozing"]
                        )
                        * 1e3,
                        1,
                    ),
                    "scm_ray_testing_us": round(sc["ray_testing"] * 1e3, 1),
                    "scm_ray_casting_us": round(sc["ray_casting"] * 1e3, 1),
                    "scm_num_ray_casts": sc["num_ray_casts"],
                    "scm_num_ray_hits": round(sc["num_ray_hits"], 1),
                    "max_diff_vs_QR_lock0_after_warmup": agr[k],
                    "state_after_warmup": {
                        kk: r["state_after_warmup"][kk]
                        for kk in ("pad_sinkage_m", "sum_fz_over_weight", "crawler_fz_N")
                    },
                }
            )
            cases[k.replace(f"d{delta}_", "")] = rr
        scm_out[f"delta_{delta}_m"] = cases
    summary["scm"] = {
        "model": (
            "same machine without floor plate and ground bushings; pads = cylinders of the pad "
            "bottom area "
            "(r 0.1846 m, h 0.025 m); SCMTerrain 8 m x 6 m, active domains: 4 pads (0.6x0.6x0.4 "
            "m) + 2 crawler "
            "strips; dt 1e-4 s; SMC system (no SMC contacts present)"
        ),
        "soil_ASSUMPTION": {
            "source": "test only: Wong, Theory of Ground Vehicles, Bekker table 'heavy clay 25 % "
            "moisture'",
            "Kphi_N_m^(n+2)": 1555.95e3,
            "Kc_N_m^(n+1)": 12.70e3,
            "n": 0.13,
            "cohesion_Pa": 68.95e3,
            "friction_deg": 34.0,
            "janosi_m": 0.01,
            "elastic_K_Pa_m": 2e8,
            "damping_R_Pa_s_m": 3e4,
            "note": "Janosi, elastic K and damping R are Chrono-demo-order values, not soil data",
        },
        "scm_timer_unit": "SCMTerrain GetTimer* return milliseconds (checked: ray_testing ms x "
        "1e3 ~ Setup timer us)",
        "crawler_layout_at_measurement": crawler_layout_note(scm),
        "results": scm_out,
    }
    # scaling
    sc = load("scale")
    scale_out: dict = {}
    for k, r in sc.items():
        topo, N = re.match(r"(grid|chain)_N(\d+)_", k).groups()
        s, lock, thr = parse(k)
        rr = row(r)
        rr.update({"solver": LABEL[s], "lock_sparsity": lock, "MKL_NUM_THREADS": thr})
        scale_out.setdefault(topo, {}).setdefault(int(N), {})[k.split(f"N{N}_")[1]] = rr
    # agreement for scaling (state after the fixed warm-up of 100 steps)
    for topo in scale_out:
        for N in scale_out[topo]:
            grp = {k: v for k, v in sc.items() if k.startswith(f"{topo}_N{N}_")}
            refk = f"{topo}_N{N}_LU_lock1_thrdef"
            if refk not in grp:
                continue
            ref = grp[refk]["state_after_warmup"]
            for k, r in grp.items():
                st = r["state_after_warmup"]
                scale_out[topo][N][k.split(f"N{N}_")[1]]["max_diff_vs_LU_after_warmup"] = {
                    "z_m": max_diff(st["_z"], ref["_z"]),
                    "quat_vec": max_diff(st["_q"], ref["_q"]),
                }
    log = (RES / "log.txt").read_text(encoding="utf-8").splitlines()
    timeouts = [ln for ln in log if "TIMEOUT" in ln or "rc=0x0" not in ln]
    summary["scaling"] = {
        "models": {
            "grid": (
                "N bodies on a square grid, each on a ChLinkMotorLinearPosition to the floor "
                "(spherical guide, "
                "z = 1 mm sine), neighbours coupled by ChLoadBodyBodyBushingSpherical (k 1e6 N/m, "
                "c 1e3 N s/m): "
                "2-D coupling through the bushing stiffness blocks"
            ),
            "chain": (
                "N bodies in a chain joined by ChLinkLockSpherical, body 0 to the floor, each "
                "with a ground "
                "bushing at its COM, gravity: banded coupling through constraint Jacobians"
            ),
        },
        "dt_s": 1e-4,
        "failed_or_timeout_runs": timeouts,
        "results": scale_out,
    }
    bcm.SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    bcm.SUMMARY_JSON.write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")

    # figure: N vs us/step (step and LS), both topologies
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), dpi=130, sharey=True)
    colors = {"SPARSE_QR": "#1f77b4", "SPARSE_LU": "#2ca02c", "PARDISO_MKL": "#d62728"}
    for ax, topo in zip(axes, ("grid", "chain"), strict=True):
        data = scale_out.get(topo, {})
        for variant, lab, ls_ in (
            ("QR_lock1_thrdef", "SPARSE_QR", "-"),
            ("LU_lock1_thrdef", "SPARSE_LU", "-"),
            ("PARDISO_lock1_thrdef", "PARDISO_MKL", "-"),
            ("PARDISO_lock1_thr1", "PARDISO_MKL", ":"),
        ):
            Ns = sorted(n for n in data if variant in data[n])
            if not Ns:
                continue
            step = [data[n][variant]["chrono_step_us"] for n in Ns]
            lsv = [data[n][variant]["ls_us"] for n in Ns]
            name = lab + (" (MKL 1 thread)" if variant.endswith("thr1") else "")
            ax.plot(Ns, step, ls_, marker="o", color=colors[lab], label=f"{name} step")
            if not variant.endswith("thr1"):
                ax.plot(
                    Ns, lsv, "--", marker="x", color=colors[lab], alpha=0.7, label=f"{lab} LS only"
                )
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("number of bodies N")
        ax.set_title(
            f"{topo}: "
            + ("bushing-coupled 2-D grid" if topo == "grid" else "spherical-joint chain")
        )
        ax.grid(True, which="both", alpha=0.3)
        if data:
            Ns = sorted(data)
            sec = ax.secondary_xaxis("top")
            any_v = None
            sec.set_xticks(
                Ns, labels=[str(data[n][next(iter(data[n]))]["kkt_size"]) for n in Ns], fontsize=7
            )
            sec.minorticks_off()
            sec.set_xlabel("KKT unknowns (vel coords + constraints)", fontsize=8)
            del any_v
    axes[0].set_ylabel("time per step [us] (Chrono timer, dt 1e-4 s, lock on)")
    axes[1].legend(fontsize=7.5, loc="upper left")
    fig.suptitle(
        "PyChrono 10 direct linear solvers: step time vs model size (median of 3; this PC)",
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(bcm.SUMMARY_PNG)
    print("written", bcm.SUMMARY_JSON, bcm.SUMMARY_PNG)


if __name__ == "__main__":
    main()
