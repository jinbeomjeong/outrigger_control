"""S1 runs: L1 superstructure + locked legs + ground bushing on a level floor (static).

``00_docs/03_chrono/chrono_build_plan.md`` S1; checks V0, V1, V2, V3, V13
(``outrigger_sim.verify.s1``). Usage (Chrono-dev python, from any folder)::

    python -I -u run_S1.py all            # 4 cases in own processes (P-core pinned) + summary
    python -I -u run_S1.py case <name>    # one case: top | middle | bottom | cross_top
    python -I -u run_S1.py summary        # rebuild the summary from stored case results

Cases:

* ``top``, ``middle``, ``bottom``: analytic static start (plan section 2 rule 1; pose from
  the V2 / V3 reference values, bushings at t = 0 with zero force), settle 10 s, still
  window 5 s (judged), snapshot ``07_results/states/S1_L1_<level>`` (R16) and a restore
  round trip (continue 1 s vs. restore into a fresh build and run 1 s).
* ``cross_top``: no analytic start (level zero pose, pads just touching, bushings at t = 0),
  settle ``ceil(simulation.settle_on_pads_min_s)`` = 53 s, still window 5 s (risk 3 cross
  check of the analytic start).

Outputs: ``07_results/S1/<case>/record.npz`` + ``meta.json`` (Record, git-ignored),
``07_results/S1/<case>/result.json``, ``07_results/states/S1_L1_<level>.npz`` + meta,
summary ``06_analysis/01_chrono/11_S1/verify_S1_L1.json`` and figure ``verify_S1_L1.png``.
Sampling: every 10 ms before the still window, every 1 ms (10 steps) inside it.
Units SI; angles in deg where named ``*_deg``.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))

RESULTS = ROOT / "07_results" / "S1"
STATES = ROOT / "07_results" / "states"
ANALYSIS_DIR = ROOT / "06_analysis" / "01_chrono" / "11_S1"
SUMMARY = ANALYSIS_DIR / "verify_S1_L1.json"
FIGURE = ANALYSIS_DIR / "verify_S1_L1.png"
# bundle B: output roots and the snapshot folder tagged by l1r_variant (no change without it)
sys.path.insert(0, str(HERE))
import l1r_variant as _l1rv  # noqa: E402

RESULTS, STATES = _l1rv.tagged(RESULTS), _l1rv.tagged(STATES)
SUMMARY, FIGURE = _l1rv.tagged(SUMMARY), _l1rv.tagged(FIGURE)
CASES = ("top", "middle", "bottom", "cross_top")
PY = sys.executable
ROUNDTRIP_S = 1.0
ROUNDTRIP_TOL_M = 1.0e-12
COARSE_SAMPLE_S = 1.0e-2
FINE_SAMPLE_S = 1.0e-3


def run_case(name: str) -> dict:
    from outrigger_sim.hostcpu import place_process

    placement = place_process("pcore")
    import numpy as np

    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.chrono.model import L1Model, operating_extensions_m, run_settle, zero_pose
    from outrigger_sim.params import load_params
    from outrigger_sim.record import (
        Recorder,
        load_snapshot,
        make_run_meta,
        save_record,
        save_snapshot,
    )
    from outrigger_sim.scenarios.settle import (
        SETTLE_S,
        STILL_S,
        analytic_static_pose,
        cross_settle_s,
        linear_static_solution,
    )
    from outrigger_sim.signals import Command
    from outrigger_sim.verify.checks import all_passed, check_max, summary_table
    from outrigger_sim.verify.reference import load_references
    from outrigger_sim.verify.s1 import v0_checks, v1_v3_checks, v13_checks

    cross = name.startswith("cross_")
    level = name.removeprefix("cross_")
    params = load_params(level=level)
    refs = load_references()
    ext = operating_extensions_m(params)
    t_build = time.perf_counter()
    if cross:
        pose = zero_pose(params, ext)
        start = {
            "kind": "zero pose (pads just touching, level, at rest), no analytic start",
            "origin_m": list(pose.origin_m),
            "quat_wxyz": list(pose.quat_wxyz),
        }
        settle_s = cross_settle_s(params)
    else:
        sp = analytic_static_pose(params, refs, ext)
        pose = BodyPose(sp.origin_m, sp.quat_wxyz)
        start = {"kind": "analytic static start (plan section 2 rule 1)", **sp.__dict__}
        settle_s = SETTLE_S
    model = L1Model(params, pose=pose, rod_side_mechanics=_l1rv.mechanics())
    build_s = time.perf_counter() - t_build
    inventory = model.v0_inventory()
    checks = v0_checks(params, inventory)

    dt = model.dt_s
    run_meta = make_run_meta(
        params,
        model.meta(),
        scenario="S1_settle" if not cross else "S1_settle_cross",
        scenario_settings={
            "settle_s": settle_s,
            "still_s": STILL_S,
            "start": start["kind"],
            "sample_s": [COARSE_SAMPLE_S, FINE_SAMPLE_S],
        },
        reference_sha256=refs.sha256_by_file(),
        extra={"cpu_placement": placement},
    )
    recorder = Recorder(run_meta)
    command = Command(t_s=0.0, leg_speed_m_s=np.zeros(4))
    run = run_settle(
        model,
        settle_s,
        STILL_S,
        coarse_sample_s=COARSE_SAMPLE_S,
        fine_sample_s=FINE_SAMPLE_S,
        on_sample=lambda probe: recorder.append(model.truth(probe), command),
    )
    events = run.events
    for event in events:
        recorder.add_bushing_event(event.t_s, event.leg, event.kind)
    run_wall = run.wall_s
    n_steps = run.steps
    all_t, all_n, all_rp = run.t_s, run.pad_normal_N, run.roll_pitch_deg

    # frame / callback cross-check at the end
    probe_end = run.end_probe
    rep_end = run.end_contacts
    cb_diff = float(np.abs(rep_end.force_world_N[1:] - probe_end.pad_contact_world_N).max())
    gb_diff = float(np.abs(model.bushing.normal_force_raw_N - probe_end.pad_normal_force_N).max())
    stats = run.stats
    checks += v1_v3_checks(params, refs, stats) + v13_checks(refs, stats)

    out_dir = RESULTS / name
    record_path = save_record(recorder.finish(), out_dir, overwrite=True)

    snapshot_info = None
    if not cross:
        snap = model.snapshot()
        snap_name = f"S1_L1_{level}"
        snap_path = save_snapshot(
            snap,
            snap_name,
            directory=STATES,
            overwrite=True,
            note={
                "stage": "S1",
                "case": name,
                "scenario": "analytic start + settle 10 s + still 5 s",
                "t_s": snap.time_s,
                "script": "04_scripts/02_chrono/run_S1.py",
            },
        )
        # round trip: continue this model vs. restore the file into a fresh build (R16)
        loaded = load_snapshot(snap_name, params_sha256=params.sha256, directory=STATES)
        fresh = L1Model(params, pose=pose, rod_side_mechanics=_l1rv.mechanics())
        t_restored = fresh.restore(loaded)
        n_rt = round(ROUNDTRIP_S / dt)
        for _ in range(n_rt):
            model.step()
            fresh.step()
        pa = np.array([[b.GetPos().x, b.GetPos().y, b.GetPos().z] for b in model.bodies])
        pb = np.array([[b.GetPos().x, b.GetPos().y, b.GetPos().z] for b in fresh.bodies])
        snapshot_info = {
            "path": str(snap_path.relative_to(ROOT)).replace("\\", "/"),
            "time_s": snap.time_s,
            "params_sha256": params.sha256,
            "roundtrip_continue_s": ROUNDTRIP_S,
            "roundtrip_restored_time_s": t_restored,
            "roundtrip_max_position_diff_m": float(np.abs(pa - pb).max()),
            "roundtrip_bit_identical": bool(np.array_equal(pa, pb)),
        }
        checks.append(
            check_max(
                "R16",
                "snapshot round trip: restore into a fresh build, 1 s, position diff",
                float(np.abs(pa - pb).max()),
                ROUNDTRIP_TOL_M,
                "m",
                note="plan S0 snapshot criterion (<= 1e-12 m)",
            )
        )

    lin = linear_static_solution(params, params.contact.rigid_floor.L1.kn_per_pad_N_m)
    lin32 = linear_static_solution(
        params, [float(np.float32(k)) for k in params.contact.rigid_floor.L1.kn_per_pad_N_m]
    )
    gb = model.bushing
    return {
        "case": name,
        "level": level,
        "analytic_start": not cross,
        "start": {k: (list(v) if isinstance(v, tuple) else v) for k, v in start.items()},
        "settle_s": settle_s,
        "still_s": STILL_S,
        "dt_s": dt,
        "steps": n_steps,
        "checks": summary_table(checks),
        "all_passed": all_passed(checks),
        "still_window": {
            k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in stats.__dict__.items()
        },
        "series_coarse": {
            "t_s": all_t[:: max(1, len(all_t) // 600)],
            "pad_normal_N": [list(map(float, v)) for v in all_n[:: max(1, len(all_n) // 600)]],
            "roll_pitch_deg": [list(map(float, v)) for v in all_rp[:: max(1, len(all_rp) // 600)]],
        },
        "frame_and_callback": {
            "GetContactForce_vs_ReportContactCallback_max_abs_N": cb_diff,
            "probe_vs_bushing_normal_max_abs_N": gb_diff,
            "callback_counts_end": rep_end.count.tolist(),
            "callback_other_contacts_end": rep_end.n_other,
            "pad_contact_world_end_N": probe_end.pad_contact_world_N.tolist(),
        },
        "ground_bushing": {
            "events": [[e.t_s, e.leg, e.kind] for e in events],
            "yield_steps": gb.yield_steps.tolist(),
            "slip_total_m": gb.slip_total_m.tolist(),
            "tangential_force_end_N": gb.tangential_force_world_N().tolist(),
        },
        "linear_static_cross_check": {
            "note": "dynamics_model.md 3.1 linear 3-DoF with the YAML kn (and with the float32 "
            "kn Chrono stores); independent of reference.json",
            "contact_N": lin["contact_N"].tolist(),
            "cylinder_N": lin["cylinder_N"].tolist(),
            "penetration_mm": (lin["penetration_m"] * 1e3).tolist(),
            "roll_pitch_deg": np.degrees(lin["q"][1:]).tolist(),
            "contact_N_float32_kn": lin32["contact_N"].tolist(),
            "total_weight_N": lin["total_weight_N"],
        },
        "snapshot": snapshot_info,
        "record": str(record_path.relative_to(ROOT)).replace("\\", "/"),
        "timing": {
            "build_s": build_s,
            "run_wall_s": run_wall,
            "wall_us_per_step_incl_sampling": run_wall / n_steps * 1e6,
            "cpu_placement": placement,
        },
        "v0_inventory": inventory,
    }


def foreign_processes() -> list[str]:
    try:
        txt = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"], capture_output=True, timeout=30, check=False
        ).stdout.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ["<tasklist failed>"]
    out = []
    for line in txt.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) > 1 and parts[0].lower().removesuffix(".exe") in (
            "julia",
            "freecad",
            "freecadcmd",
            "gmsh",
            "ccx",
            "matlab",
        ):
            out.append(f"{parts[0]}:{parts[1]}")
    return out


def run_all() -> None:
    for name in CASES:
        before = foreign_processes()
        t0 = time.perf_counter()
        done = subprocess.run(
            [PY, "-I", "-u", str(Path(__file__).resolve()), "case", name],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        tail = (done.stdout.strip().splitlines() or [""])[-1]
        print(
            f"{name}: rc={done.returncode} {time.perf_counter() - t0:.1f}s {tail} "
            f"foreign={before}/{foreign_processes()}",
            flush=True,
        )
        if done.returncode != 0:
            print(done.stderr[-3000:], flush=True)
    summarize()


def summarize() -> None:
    import numpy as np

    results = {}
    for name in CASES:
        p = RESULTS / name / "result.json"
        if p.is_file():
            results[name] = json.loads(p.read_text(encoding="utf-8"))
    table = []
    for name, r in results.items():
        for c in r["checks"]:
            if c["id"] == "V0":
                continue
            table.append(
                {
                    "case": name,
                    "id": c["id"],
                    "item": c["item"],
                    "value": c["value"],
                    "ref": c["ref"],
                    "tol": c["tol"],
                    "tol_kind": c["tol_kind"],
                    "unit": c["unit"],
                    "passed": c["passed"],
                    "ref_key": c["ref_key"],
                }
            )
    v0 = {
        name: {
            "n_checks": sum(1 for c in r["checks"] if c["id"] == "V0"),
            "failed": [c for c in r["checks"] if c["id"] == "V0" and not c["passed"]],
        }
        for name, r in results.items()
    }
    by_id: dict[str, bool] = {}
    for name, r in results.items():
        for c in r["checks"]:
            key = f"{c['id']}" + ("" if not name.startswith("cross") else " (cross_top)")
            by_id[key] = by_id.get(key, True) and c["passed"]
    summary = {
        "meta": {
            "generated": _dt.datetime.now().isoformat(timespec="seconds"),
            "stage": "S1 (chrono_build_plan.md): L1 superstructure + locked legs at e_op + ground "
            "bushing at t = 0, level rigid floor, static",
            "script": "04_scripts/02_chrono/run_S1.py",
            "model": "outrigger_sim.chrono.model.L1Model (crawler spheres layout D on, floor "
            "patches 4 pad + 2 crawler, families floor 0 / superstructure 1 / rod 2)",
            "judgement": "automatic pre-check; final physical judgement by dynamics-expert",
            "python": platform.python_version(),
            "host": os.environ.get("COMPUTERNAME", ""),
            "raw_data": {
                name: {
                    "record": r["record"],
                    "result": f"07_results/S1/{name}/result.json",
                    "snapshot": (r["snapshot"] or {}).get("path"),
                }
                for name, r in results.items()
            },
            "figure": str(FIGURE.relative_to(ROOT)).replace("\\", "/"),
        },
        "verdict_by_check": by_id,
        "all_passed": all(r["all_passed"] for r in results.values()),
        "table": table,
        "v0": v0,
        "cases": {
            name: {k: v for k, v in r.items() if k not in ("v0_inventory", "series_coarse")}
            for name, r in results.items()
        },
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {SUMMARY}")

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, len(results), figsize=(4.2 * len(results), 6.4), squeeze=False)
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    for j, (name, r) in enumerate(results.items()):
        s = r["series_coarse"]
        t = np.asarray(s["t_s"])
        n = np.asarray(s["pad_normal_N"]) / 1e3
        rp = np.asarray(s["roll_pitch_deg"])
        ax = axes[0, j]
        for i, leg in enumerate(("FL", "FR", "RL", "RR")):
            ax.plot(t, n[:, i], color=colors[i], lw=1, label=leg)
        ax.set_title(name)
        ax.set_xlabel("time [s]")
        ax.set_ylabel("pad normal force [kN]")
        ax.grid(alpha=0.3)
        if j == 0:
            ax.legend(fontsize=8)
        ax = axes[1, j]
        ax.plot(t, rp[:, 0], color="#444444", lw=1, label="roll")
        ax.plot(t, rp[:, 1], color="#9467bd", lw=1, label="pitch")
        ax.set_xlabel("time [s]")
        ax.set_ylabel("attitude [deg]")
        ax.grid(alpha=0.3)
        if j == 0:
            ax.legend(fontsize=8)
    fig.tight_layout()
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=110)
    print(f"wrote {FIGURE}")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "case":
        case = sys.argv[2]
        if case not in CASES:
            raise SystemExit(f"unknown case {case!r}, expected one of {CASES}")
        result = run_case(case)
        out = RESULTS / case / "result.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
        failed = [c["id"] + ": " + c["item"] for c in result["checks"] if not c["passed"]]
        print(
            "OK",
            case,
            f"{result['timing']['wall_us_per_step_incl_sampling']:.1f} us/step",
            "all_passed" if result["all_passed"] else f"FAILED {failed}",
            flush=True,
        )
    elif mode == "all":
        run_all()
    elif mode == "summary":
        summarize()
    else:
        raise SystemExit(f"unknown mode {mode!r}")
