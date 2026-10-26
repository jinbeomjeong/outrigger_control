"""Stand-alone (uncontended) step cost of the S9 P3b levelling run, per soil and per phase.

S9 pre-start check 4 (cost): the P3b batch costs were measured with 4 cases in parallel. This
script reruns the P3b ``run_S9.py level`` setup unchanged (pad B ``dwg_rear250``, auger top, F_s 4 kN,
pad grid G1 / S1 2 cm, J1 / J2 1 cm, crawler 4 cm, 4 SCM threads, P-core placement with EcoQoS off)
with only ``--duration`` shortened, one case at a time, and times every physics step.

Timing: ``S9Model.step`` is wrapped on the instance (no change to ``03_src``). Per 0.5 s simulated-time
bin it accumulates the step wall time (``DoStepDynamics`` + model hooks) and the inclusive wall time
between successive step starts (adds the controller, sensors and recording of the closed loop).
Phase windows are taken from the pad SCM normal sum of ``step_series.npz``: settle [0, 8) s,
pre-contact [8, t_first), load transfer [t_first, t_full), full load [t_full, end).

Usage (Chrono-dev python, project root)::

    python -I -X utf8 -u 04_scripts/02_chrono/solver_benchmark/step_cost_S9.py batch
        [--cases G1:40,S1:50,J1:40,J2:45] [--ref-batch 07_results/S9/batch_P3b_20261026_122444]
    python -I -X utf8 -u 04_scripts/02_chrono/solver_benchmark/step_cost_S9.py case --soil G1 --end-s 40 \
        --out-root <dir>                                    # one case (the batch launches this)

``batch`` writes ``07_results/S9/cost_solo_<stamp>/`` (``progress.log``, one folder per case with the
``run_S9`` outputs plus ``step_timing.json``) and the summary
``06_analysis/01_chrono/01_cost/S9_P3b_solo_step_cost.json``. After the first case it checks that the
shortened run reproduces the reference P3b trajectory (``step_series.npz`` over the common time) and
stops when it does not.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CHRONO_SCRIPTS = ROOT / "04_scripts" / "02_chrono"
RESULTS = ROOT / "07_results" / "S9"
SUMMARY = ROOT / "06_analysis" / "01_chrono" / "01_cost" / "S9_P3b_solo_step_cost.json"
REF_BATCH = RESULTS / "batch_P3b_20261026_122444"
BIN_S = 0.5
SETTLE_END_S = 8.0
PAD_FIRST_N = 1.0e3
FULL_LOAD_FRACTION = 0.95
COMPARE_KEYS = ("t_s", "s_motor_m", "F_cyl_N", "roll_pitch_deg", "z_origin_m", "scm_pad_normal_N",
                "scm_crawler_normal_N")
DEFAULT_CASES = "G1:40,S1:50,J1:40,J2:45"


# --- one case (child process) ----------------------------------------------------------------------


def run_case(args) -> None:
    sys.path.insert(0, str(CHRONO_SCRIPTS))
    sys.path.insert(0, str(ROOT / "03_src"))
    import numpy as np
    import psutil
    import run_S9 as R

    case = next(c for c in R.p3b_cases()
                if c["soil"] == args.soil and c["pad"] == "B" and c["level"] == "top" and c["fs_kN"] == 4.0)
    duration = args.end_s - R.CRAWLER_SETTLE_S
    argv = R.p3b_level_argv(case)
    i = argv.index("--duration")
    argv[i + 1] = f"{duration:g}"
    argv += ["--case", args.case, "--out-root", str(args.out_root)]

    nb = int(math.ceil(args.end_s / BIN_S)) + 4
    step_s = np.zeros(nb)
    incl_s = np.zeros(nb)
    count = np.zeros(nb, dtype=np.int64)
    state = {"last": None, "last_bin": None, "model": None}
    orig_build = R.build_machine

    def build(a, params, pv, soil):
        m = orig_build(a, params, pv, soil)
        state["model"] = m
        inner = m.step
        pc = time.perf_counter
        sysm = m.system

        def timed(*p, **kw):
            t0 = pc()
            last = state["last"]
            if last is not None:
                incl_s[state["last_bin"]] += t0 - last
            b = int(sysm.GetChTime() / BIN_S + 1e-9)
            r = inner(*p, **kw)
            step_s[b] += pc() - t0
            count[b] += 1
            state["last"] = t0
            state["last_bin"] = b
            return r

        m.step = timed
        return m

    R.build_machine = build
    proc = psutil.Process()
    cpu0 = proc.cpu_times()
    t_wall0 = time.perf_counter()
    d = R.run_level(R.build_parser().parse_args(argv))
    wall_total = time.perf_counter() - t_wall0
    if state["last"] is not None:  # the last step's inclusive time ends at the run end (approximation: step only)
        incl_s[state["last_bin"]] += step_s[state["last_bin"]] / max(count[state["last_bin"]], 1)
    cpu1 = proc.cpu_times()
    mem = proc.memory_info()
    res = json.loads((Path(d) / "result.json").read_text("utf-8"))
    n = int(count.sum())
    out = {
        "soil": args.soil, "case": args.case, "argv": argv, "end_s": args.end_s, "duration_s": duration,
        "bin_s": BIN_S, "dt_s": float(state["model"].dt_s), "num_threads_chrono": res.get("num_threads_chrono"),
        "bins": {"t0_s": [k * BIN_S for k in range(nb)], "steps": count.tolist(),
                 "step_wall_s": step_s.tolist(), "inclusive_wall_s": incl_s.tolist()},
        "n_steps_timed": n, "n_steps_run_S9": res.get("n_steps"),
        "build_s": res.get("build_s"), "settle_wall_s": res.get("settle_wall_s"), "loop_wall_s": res.get("loop_wall_s"),
        "us_per_step_run_S9": res.get("us_per_step"), "wall_total_process_s": wall_total,
        "placement": res.get("placement"), "cpu_affinity_end": proc.cpu_affinity(),
        "cpu_user_s": cpu1.user - cpu0.user, "cpu_system_s": cpu1.system - cpu0.system,
        "peak_rss_MB": getattr(mem, "peak_wset", mem.rss) / 2**20, "rss_end_MB": mem.rss / 2**20,
        "phases": res.get("phases"),
    }
    (Path(d) / "step_timing.json").write_text(json.dumps(out, indent=1), "utf-8")
    print("step_timing ->", Path(d) / "step_timing.json", flush=True)


# --- batch (driver) ---------------------------------------------------------------------------------


def top_cpu(n: int = 6) -> list[dict]:
    import psutil

    procs = list(psutil.process_iter(["pid", "name"]))
    for p in procs:
        try:
            p.cpu_percent(None)
        except Exception:  # noqa: BLE001
            pass
    time.sleep(1.0)
    rows = []
    for p in procs:
        try:
            rows.append({"pid": p.pid, "name": p.info["name"], "cpu_pct": p.cpu_percent(None)})
        except Exception:  # noqa: BLE001
            pass
    rows = [r for r in rows if r["name"] not in ("System Idle Process",)]
    rows.sort(key=lambda r: -r["cpu_pct"])
    return rows[:n]


def phase_windows(series_path: Path, end_s: float) -> dict:
    import numpy as np

    z = np.load(series_path)
    t = z["t_s"]
    pad = z["scm_pad_normal_N"].sum(axis=1)
    full = float(np.nanmax(pad))
    i1 = np.flatnonzero(pad > PAD_FIRST_N)
    t_first = float(t[i1[0]]) if len(i1) else None
    ref_full_N = 380.1e3  # P3b steady pad normal sum (batch_P3b_20261026_122444, all four soils)
    i2 = np.flatnonzero(pad >= FULL_LOAD_FRACTION * ref_full_N)
    t_full = float(t[i2[0]]) if len(i2) else None
    w = {"settle": (0.0, SETTLE_END_S)}
    if t_first is not None:
        w["pre_contact"] = (SETTLE_END_S, t_first)
        w["load_transfer"] = (t_first, t_full if t_full is not None else end_s)
        if t_full is not None:
            w["full_load"] = (t_full, end_s)
    else:
        w["pre_contact"] = (SETTLE_END_S, end_s)
    w["closed_loop_all"] = (SETTLE_END_S, end_s)
    w["whole_run"] = (0.0, end_s)
    return {"windows": w, "t_pad_first_s": t_first, "t_full_load_s": t_full, "pad_sum_max_N": full,
            "full_load_rule": f"pad SCM normal sum >= {FULL_LOAD_FRACTION} x 380.1 kN; first contact > {PAD_FIRST_N:g} N"}


def window_costs(timing: dict, windows: dict) -> dict:
    t0 = timing["bins"]["t0_s"]
    out = {}
    for name, (a, b) in windows.items():
        n = sw = iw = 0.0
        # bins are 0.5 s; a window takes the whole bins inside [a, b) (snapped inward, no bin in two windows)
        lo = math.ceil(a / BIN_S - 1e-9) * BIN_S
        hi = math.floor(b / BIN_S + 1e-9) * BIN_S
        for k, tb in enumerate(t0):
            if lo - 1e-9 <= tb and tb + BIN_S <= hi + 1e-9:
                n += timing["bins"]["steps"][k]
                sw += timing["bins"]["step_wall_s"][k]
                iw += timing["bins"]["inclusive_wall_s"][k]
        out[name] = {"t_from_s": lo, "t_to_s": hi,
                     "steps": int(n), "ms_per_step_physics": (sw / n * 1e3) if n else None,
                     "ms_per_step_inclusive": (iw / n * 1e3) if n else None}
    return out


def compare_trajectory(new_dir: Path, ref_dir: Path) -> dict:
    import numpy as np

    a = np.load(new_dir / "step_series.npz")
    b = np.load(ref_dir / "step_series.npz")
    n = min(len(a["t_s"]), len(b["t_s"]))
    rep = {"ref": str(ref_dir), "rows_compared": int(n), "t_end_compared_s": float(a["t_s"][n - 1]), "keys": {}}
    identical = True
    for k in COMPARE_KEYS:
        if k not in a.files or k not in b.files:
            rep["keys"][k] = "missing"
            identical = False
            continue
        x, y = np.asarray(a[k][:n], float), np.asarray(b[k][:n], float)
        eq = bool(np.array_equal(x, y, equal_nan=True))
        diff = np.abs(x - y)
        diff = diff[np.isfinite(diff)]
        rep["keys"][k] = {"bit_identical": eq, "max_abs_diff": float(diff.max()) if diff.size else 0.0}
        identical &= eq
    rep["bit_identical"] = bool(identical)
    return rep


def run_batch(args) -> int:
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    root = RESULTS / f"cost_solo_{stamp}"
    root.mkdir(parents=True, exist_ok=False)
    log = (root / "progress.log").open("a", encoding="utf-8")

    def say(msg: str) -> None:
        line = f"{_dt.datetime.now().isoformat(timespec='seconds')} {msg}"
        log.write(line + "\n")
        log.flush()
        print(line, flush=True)

    cases = [(s.split(":")[0], float(s.split(":")[1])) for s in args.cases.split(",")]
    say(f"start batch root={root} cases={cases} python={sys.executable}")
    summary = {"purpose": "S9 pre-start check 4: stand-alone P3b step cost (one case at a time, P-cores, EcoQoS off)",
               "root": str(root), "started": stamp, "cases": [], "trajectory_check": None,
               "setup": "run_S9.p3b_level_argv(P3b_<soil>_B_top_Fs4) with --duration = end_s - 8 s; "
                        "pad B dwg_rear250, auger top, F_s 4 kN, 4 SCM threads, dt 1e-4 s"}
    status = 0
    for k, (soil, end_s) in enumerate(cases):
        case = f"solo_{soil}_B_top_Fs4_end{end_s:g}"
        top = top_cpu()
        say(f"case {case} start; top cpu: " + ", ".join(f"{r['name']}({r['pid']}) {r['cpu_pct']:.0f}%" for r in top))
        busy = [r for r in top if r["cpu_pct"] > 50.0 and r["pid"] != os.getpid()]
        cmd = [sys.executable, "-I", "-X", "utf8", "-u", str(Path(__file__).resolve()), "case", "--soil", soil,
               "--end-s", f"{end_s:g}", "--out-root", str(root), "--case", case]
        env = dict(os.environ, OUTRIGGER_PLACEMENT="pcore")
        t0 = time.perf_counter()
        with (root / f"{case}.out.log").open("w", encoding="utf-8") as fo, \
                (root / f"{case}.err.log").open("w", encoding="utf-8") as fe:
            rc = subprocess.run(cmd, stdout=fo, stderr=fe, env=env, cwd=str(ROOT)).returncode
        wall = time.perf_counter() - t0
        d = root / case
        if rc != 0 or not (d / "step_timing.json").exists():
            say(f"case {case} FAILED rc={rc} wall={wall:.0f}s (see {case}.err.log)")
            status = 1
            break
        timing = json.loads((d / "step_timing.json").read_text("utf-8"))
        ph = phase_windows(d / "step_series.npz", end_s)
        costs = window_costs(timing, ph["windows"])
        row = {"soil": soil, "case": case, "end_s": end_s, "process_wall_s": wall, "top_cpu_before": top,
               "busy_before": busy, **{k2: timing[k2] for k2 in (
                   "num_threads_chrono", "dt_s", "n_steps_timed", "n_steps_run_S9", "build_s", "settle_wall_s",
                   "loop_wall_s", "us_per_step_run_S9", "placement", "cpu_affinity_end", "cpu_user_s",
                   "cpu_system_s", "peak_rss_MB", "phases")},
               "phase_detection": {k2: v for k2, v in ph.items() if k2 != "windows"}, "windows": costs}
        summary["cases"].append(row)
        fl = costs.get("full_load", {})
        say(f"case {case} end rc=0 wall={wall:.0f}s mean={timing['us_per_step_run_S9'] / 1e3:.2f} ms/step; "
            f"settle {costs['settle']['ms_per_step_physics']:.2f}, pre_contact "
            f"{costs['pre_contact']['ms_per_step_inclusive']:.2f}, full_load "
            f"{fl.get('ms_per_step_inclusive') or float('nan'):.2f} ms/step (incl.); peak RSS {timing['peak_rss_MB']:.0f} MB")
        if k == 0:
            ref = Path(args.ref_batch) / f"P3b_{soil}_B_top_Fs4"
            rep = compare_trajectory(d, ref)
            summary["trajectory_check"] = rep
            say(f"trajectory check vs {ref.name}: bit_identical={rep['bit_identical']} up to "
                f"{rep['t_end_compared_s']:.3f} s; " + ", ".join(
                    f"{kk}={v['max_abs_diff']:.3g}" if isinstance(v, dict) else f"{kk}={v}" for kk, v in rep["keys"].items()))
            if not rep["bit_identical"]:
                say("STOP: the shortened run does not reproduce the reference trajectory")
                status = 2
                break
        SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY.write_text(json.dumps(summary, indent=1, ensure_ascii=False), "utf-8")
    summary["finished"] = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    summary["status"] = {0: "complete", 1: "case failed", 2: "trajectory mismatch stop"}[status]
    SUMMARY.write_text(json.dumps(summary, indent=1, ensure_ascii=False), "utf-8")
    say(f"batch end status={summary['status']} summary={SUMMARY}")
    return status


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="action", required=True)
    b = sub.add_parser("batch")
    b.add_argument("--cases", default=DEFAULT_CASES, help="soil:end_s list (end = absolute sim time incl. 8 s settle)")
    b.add_argument("--ref-batch", default=str(REF_BATCH))
    c = sub.add_parser("case")
    c.add_argument("--soil", choices=("G1", "S1", "J1", "J2"), required=True)
    c.add_argument("--end-s", type=float, required=True)
    c.add_argument("--out-root", type=Path, required=True)
    c.add_argument("--case", required=True)
    a = ap.parse_args(argv)
    if a.action == "case":
        run_case(a)
        return 0
    return run_batch(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
