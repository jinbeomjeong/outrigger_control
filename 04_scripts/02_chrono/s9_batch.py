"""S9 P1 / P2 batch driver (dynamics_model.md 5.34.13, rev. 49; user decision 2026-10-26).

Runs the cases of one batch as separate Chrono-dev processes (each pins itself to the P-cores,
``run_S9.place``), at most ``--parallel`` at a time (default 2: the main-tree regression shares the
P-cores). Writes ``07_results/S9/<batch>_<stamp>/``: one folder per case (``result.json`` +
``series.npz`` of run_S9), ``<case>.log`` (stdout / stderr), ``progress.log`` (one START and one
END line per case, read by the periodic monitor) and ``batch.json`` (argv, return code, wall time).
A failed case (return code != 0) stops new launches; running ones finish.

Usage (worktree root)::

    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py list
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run P1_V0p [--parallel 2]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PY = sys.executable
RUN = [PY, "-I", "-X", "utf8", "-u", str(HERE / "run_S9.py")]
EQ = [PY, "-I", "-X", "utf8", "-u", str(HERE / "s9_dual_terrain_equivalence.py")]

B = ["--pad-variant", "dwg_rear250"]
STEPS = ["--load-steps", "0.25,0.5,0.75,1.0,0.5", "--load-ramp", "1.0", "--step-ramp", "0.5", "--step-hold", "auto"]


def _g(h: float) -> str:
    return f"{h * 100:g}cm".replace(".", "p")


def batches() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    # prep 1: dual-terrain equivalence E1-E4 (5.34.12)
    out["E_dual"] = [{"case": f"E_{lay}_rep{r}", "argv": EQ + ["run", "--layout", lay, "--rep", str(r)],
                      "eq_out": True, "est_s": 300} for lay in ("single", "dual") for r in (1, 2)]
    # P1-V0': single pad G1 RL fixed, Poly345 1 s + 1 s hold, 1 / 0.5 cm
    out["P1_V0p"] = [{"case": f"V0p_G1_B_RL_{_g(h)}", "est_s": 120,
                      "argv": RUN + ["single-pad", "--soil", "G1", *B, "--leg", "RL", "--joint", "fixed",
                                     "--grid", str(h), "--force", "0", "--t-settle", "2", "--t-end", "2"]}
                     for h in (0.01, 0.005)]
    v16 = []
    for soil in ("G1", "J1"):
        for leg in ("RL", "FL"):
            for h in (0.02, 0.01, 0.005):
                v16.append({"case": f"V16_{soil}_B_{leg}_{_g(h)}", "est_s": 300,
                            "argv": RUN + ["single-pad", "--soil", soil, *B, "--leg", leg, "--joint", "fixed",
                                           "--grid", str(h), "--force", "0", *STEPS]})
    for h in (0.02, 0.01):
        v16.append({"case": f"V16bp_J2_B_RL_{_g(h)}", "est_s": 150,
                    "argv": RUN + ["single-pad", "--soil", "J2", *B, "--leg", "RL", "--joint", "fixed",
                                   "--grid", str(h), "--force", "0", *STEPS]})
    v16.append({"case": "V16d_G1_B_RL_2cm_step", "est_s": 60,
                "argv": RUN + ["single-pad", "--soil", "G1", *B, "--leg", "RL", "--joint", "fixed", "--grid", "0.02",
                               "--force", "0", "--load-ramp-shape", "step", "--t-settle", "2", "--t-end", "2"]})
    out["P1_V16"] = v16
    lc = []
    for soil, h in (("J1", 0.01), ("G1", 0.02)):
        for shear in ("native", "bprime"):
            lc.append({"case": f"L1_{soil}_fixed_F0_{shear}_{_g(h)}", "est_s": 75,
                       "argv": RUN + ["single-pad", "--soil", soil, *B, "--leg", "RL", "--joint", "fixed",
                                      "--scm-shear", shear, "--grid", str(h), "--force", "0",
                                      "--t-settle", "3", "--t-end", "3"]})
    for F in (4450, 6980, 20000):
        lc.append({"case": f"L2_J1_B_RL_F{F}_1cm", "est_s": 320,
                   "argv": RUN + ["single-pad", "--soil", "J1", *B, "--leg", "RL", "--grid", "0.01",
                                  "--force", str(F), "--t-settle", "3", "--t-ramp", "0.5", "--t-end", "13.5"]})
    for soil in ("J1", "J2"):
        lc.append({"case": f"L3_{soil}_B_RL_1.2limit_1cm", "est_s": 150,
                   "argv": RUN + ["single-pad", "--soil", soil, *B, "--leg", "RL", "--grid", "0.01",
                                  "--force-limit-factor", "1.2", "--terrain-size", "6", "1.2",
                                  "--t-settle", "3", "--t-ramp", "0.5", "--t-end", "5.0"]})
    l4 = [("L4_J1_B_RL_1cm", ["--soil", "J1", *B, "--leg", "RL", "--grid", "0.01"]),
          ("L4_J1_A_FL_1cm", ["--soil", "J1", "--pad-variant", "cad330", "--leg", "FL", "--grid", "0.01"]),
          ("L4_G1_B_RL_2cm", ["--soil", "G1", *B, "--leg", "RL", "--grid", "0.02"]),
          ("L4_J1_B_RL_1cm_ksw0", ["--soil", "J1", *B, "--leg", "RL", "--grid", "0.01", "--k-sw", "0"])]
    for name, a in l4:
        lc.append({"case": name, "est_s": 450,
                   "argv": RUN + ["single-pad", *a, "--force", "0", "--load-ramp", "20", "--load-ramp-shape", "linear",
                                  "--t-settle", "22", "--t-end", "22"]})
    for soil, h in (("J1", 0.01), ("G1", 0.02)):
        lc.append({"case": f"L5_{soil}_M14s_pitch3.5", "est_s": 600,
                   "argv": RUN + ["machine", "--soil", soil, *B, "--grid", str(h), "--crawler-grid", "0.04",
                                  "--floor-pitch", "3.5", "--gravity-ramp", "3", "--gravity-hold", "12",
                                  "--drift-window", "10"]})
    for joint in ("fixed", "spherical"):
        for dt in ("1e-4", "5e-5"):
            lc.append({"case": f"L6_J1_B_RL_native_{joint}_dt{dt}_1cm", "est_s": 180 * (2 if dt == "5e-5" else 1),
                       "argv": RUN + ["single-pad", "--soil", "J1", *B, "--leg", "RL", "--grid", "0.01",
                                      "--scm-shear", "native", "--joint", joint, "--dt", dt, "--force", "4450",
                                      "--t-settle", "3", "--t-ramp", "0.5", "--t-end", "7.5"]})
    out["P1_L"] = lc
    p2 = []
    for soil, h in (("J1", 0.01), ("J2", 0.01), ("S1", 0.02)):
        p2.append({"case": f"P2-1_{soil}_top_M14s", "est_s": 240,
                   "argv": RUN + ["machine", "--soil", soil, *B, "--grid", str(h), "--crawler-grid", "0.04"]})
    for soil in ("J1", "S1"):
        p2.append({"case": f"P2-2_{soil}_top_single2cm", "est_s": 600,
                   "argv": RUN + ["machine", "--soil", soil, *B, "--grid", "0.02"]})
    for lvl in ("middle", "bottom"):
        p2.append({"case": f"P2-3_G1_{lvl}_M14s", "est_s": 150,
                   "argv": RUN + ["machine", "--soil", "G1", *B, "--level", lvl, "--grid", "0.02",
                                  "--crawler-grid", "0.04"]})
    out["P2"] = p2
    return out


def _log(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


def run_batch(name: str, parallel: int, only: list[str] | None) -> Path:
    cases = [c for c in batches()[name] if not only or c["case"] in only]
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = ROOT / "07_results" / "S9" / f"batch_{name}_{stamp}"
    folder.mkdir(parents=True, exist_ok=True)
    progress = folder / "progress.log"
    _log(progress, f"# batch {name} {len(cases)} cases, parallel {parallel}, started {_dt.datetime.now().isoformat(timespec='seconds')}")
    pending = list(cases)
    running: list[tuple[dict, subprocess.Popen, float, object]] = []
    done: list[dict] = []
    failed = False
    while pending or running:
        while pending and len(running) < parallel and not failed:
            c = pending.pop(0)
            argv = list(c["argv"]) + (["--out", str(folder / "E")] if c.get("eq_out")
                                      else ["--case", c["case"], "--out-root", str(folder)])
            logf = (folder / f"{c['case']}.log").open("w", encoding="utf-8")
            p = subprocess.Popen(argv, cwd=str(ROOT), stdout=logf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
            _log(progress, f"START {c['case']} {_dt.datetime.now().isoformat(timespec='seconds')} pid={p.pid} est_s={c['est_s']}")
            running.append((c, p, time.perf_counter(), logf))
        time.sleep(2.0)
        for item in list(running):
            c, p, t0, logf = item
            rc = p.poll()
            if rc is None:
                continue
            logf.close()
            wall = time.perf_counter() - t0
            running.remove(item)
            done.append({"case": c["case"], "argv": c["argv"], "rc": rc, "wall_s": wall, "est_s": c["est_s"]})
            _log(progress, f"END {c['case']} {_dt.datetime.now().isoformat(timespec='seconds')} rc={rc} wall_s={wall:.0f}")
            if rc != 0:
                failed = True
        if failed and pending:
            for c in pending:
                _log(progress, f"SKIP {c['case']} (earlier failure)")
                done.append({"case": c["case"], "argv": c["argv"], "rc": None, "wall_s": 0.0, "est_s": c["est_s"]})
            pending = []
    status = {"batch": name, "folder": folder.as_posix(), "parallel": parallel, "cases": done, "failed": failed,
              "wall_serial_s": sum(d["wall_s"] for d in done), "est_serial_s": sum(d["est_s"] for d in done)}
    (folder / "batch.json").write_text(json.dumps(status, indent=1), "utf-8")
    _log(progress, f"# batch {name} finished {_dt.datetime.now().isoformat(timespec='seconds')} failed={failed}")
    print(folder)
    return folder


def main(argv) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="action", required=True)
    sub.add_parser("list")
    r = sub.add_parser("run")
    r.add_argument("batch", choices=sorted(batches()))
    r.add_argument("--parallel", type=int, default=2)
    r.add_argument("--only", nargs="*")
    a = ap.parse_args(argv)
    if a.action == "list":
        for k, v in batches().items():
            print(k, len(v), [c["case"] for c in v])
    else:
        run_batch(a.batch, a.parallel, a.only)


if __name__ == "__main__":
    main(sys.argv[1:])
