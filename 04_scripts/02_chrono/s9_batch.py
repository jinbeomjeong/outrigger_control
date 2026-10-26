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
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run P3b --parallel 4   # 2 S8C + 24 level (approved)

``s8c`` rows run ``run_S8C.py run --only <case>`` unchanged (no ``--case`` / ``--out-root``): the
S8 runner writes ``07_results/S8/<tag>_<stamp>/`` and prints it at the end of ``<case>.log``.
run_S8C exits 0 even when its case failed, so an ``s8c`` row with return code 0 is checked from its
log (:func:`s8c_case_check`: outcome line ``ok``, batch folder line, ``result.json``); a failed check
is recorded as rc 4 (``batch.json`` ``s8c_check``) and stops new launches like any failure.
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
S8C = [PY, "-I", "-X", "utf8", "-u", str(HERE / "run_S8C.py")]

B = ["--pad-variant", "dwg_rear250"]
FORMER = ["--settle-dashpot", "none"]
"""Batches run before 2026-10-26 U-S9P-1 used the former settle (no dashpot, hold 2 s / given hold)."""
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
                                  "--drift-window", "10", *FORMER]})
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
                   "argv": RUN + ["machine", "--soil", soil, *B, "--grid", str(h), "--crawler-grid", "0.04", *FORMER]})
    for soil in ("J1", "S1"):
        p2.append({"case": f"P2-2_{soil}_top_single2cm", "est_s": 600,
                   "argv": RUN + ["machine", "--soil", soil, *B, "--grid", "0.02", *FORMER]})
    for lvl in ("middle", "bottom"):
        p2.append({"case": f"P2-3_G1_{lvl}_M14s", "est_s": 150,
                   "argv": RUN + ["machine", "--soil", "G1", *B, "--level", lvl, "--grid", "0.02",
                                  "--crawler-grid", "0.04", *FORMER]})
    out["P2"] = p2
    # P2prime (dynamics 5.35.4 / 5.35.5 #2, U-S9P-1): settle dashpot (runner default), t_end 8 s, M14s, top
    out["P2prime"] = [{"case": f"P2prime_{soil}_top_M14s_dashpot8s", "est_s": 420 if soil in ("J1", "J2") else 300,
                        "argv": RUN + ["machine", "--soil", soil, *B, "--grid", str(h), "--crawler-grid", "0.04",
                                       "--settle-dashpot", "zrp"]}
                       for soil, h in (("J1", 0.01), ("J2", 0.01), ("G1", 0.02), ("S1", 0.02))]
    # P3a (dynamics 5.36.5, U-S9P-5 (a) 2026-10-26): open-loop lift 28 s after the 8 s dashpot settle,
    # J1 / G1 x type B / A, top auger; --abort-on-limit = exit 3 on a force-limit or stroke-margin excess.
    # Order B J1, B G1, A J1, A G1: with 2 slots the two long J1 runs overlap the G1 pair (about 1.5 h)
    p3a = []
    for soil, pad, pv, h, est in (("J1", "B", "dwg_rear250", 0.01, 3600), ("G1", "B", "dwg_rear250", 0.02, 1800),
                                  ("J1", "A", "cad330", 0.01, 3600), ("G1", "A", "cad330", 0.02, 1800)):
        p3a.append({"case": f"P3a_{soil}_{pad}", "est_s": est,
                    "argv": RUN + ["machine", "--soil", soil, "--pad-variant", pv, "--grid", str(h),
                                   "--crawler-grid", "0.04", "--settle-dashpot", "zrp", "--lift-s", "28",
                                   "--level", "top", "--threads", "4", "--abort-on-limit"]})
    out["P3a"] = p3a
    out["P3b"] = p3b_batch()
    return out


def p3b_batch() -> list[dict]:
    """P3b (control spec 284, U-S9P-6 (가); dynamics 5.37.6): the two re-approach 10 s limit positive
    tests first (run_S8C L2b-NSC rigid floor, R8 preset ``with_10hz_d1``, one case per process, own
    folder ``07_results/S8/p3b_<case>_<stamp>``; user decision 2026-10-26), then the 24 ``run_S9.py
    level`` cases in the 5.37.6 order (G1 10, J1 10, J2 / S1 4). Run with ``--parallel 4`` (4 SCM
    threads each = 16 P-core logical processors)."""
    sys.path.insert(0, str(HERE))
    try:
        import run_S9 as r9  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    rows = [{"case": cid, "est_s": est, "s8c": True,
             "argv": S8C + ["run", "--set", "rest", "--only", cid, "--tag", f"p3b_{cid}", "--approved",
                            "--workers", "p7"]}  # S8 'rest' set member; S8 sensors (ideal) unchanged
            for cid, est in r9.P3B_S8C_CASES.items()]
    rows += [{"case": c["case"], "est_s": c["est_s"], "argv": RUN + r9.p3b_level_argv(c)} for c in r9.p3b_cases()]
    return rows


S8C_FAILED_RC = 4
"""Return code recorded for an ``s8c`` row whose run_S8C process exited 0 but whose case failed
(run_S8C ``run`` prints the case outcome and returns 0 either way; its behaviour is unchanged)."""


def s8c_case_check(log_text: str, case_id: str, root: Path = ROOT) -> dict:
    """Outcome of one ``run_S8C.py run --only <case_id>`` from its log: the outcome line
    ``<case_id>: ok <wall>s`` (``run_batch``), the batch folder of the last ``batch wall ... -> <dir>``
    line and ``<dir>/<case_id>/result.json``. ``ok`` only when all three hold."""
    lines = log_text.splitlines()
    status = next((ln.split(":", 1)[1].split()[0] for ln in reversed(lines)
                   if ln.startswith(f"{case_id}:") and len(ln.split(":", 1)[1].split()) >= 1), None)
    batch_dir = next((ln.split("->", 1)[1].strip() for ln in reversed(lines)
                      if ln.startswith("batch wall") and "->" in ln), None)
    result = None
    if batch_dir:
        d = Path(batch_dir)
        result = (d if d.is_absolute() else root / d) / case_id / "result.json"
    out = {"case": case_id, "status": status, "batch_dir": batch_dir,
           "result_json": None if result is None else result.as_posix(),
           "result_exists": bool(result is not None and result.is_file())}
    reasons = []
    if status != "ok":
        reasons.append(f"case outcome {status!r} (expected 'ok')")
    if batch_dir is None:
        reasons.append("no 'batch wall ... -> <dir>' line")
    elif not out["result_exists"]:
        reasons.append("result.json missing")
    out.update(ok=not reasons, reason="; ".join(reasons) or None)
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
            if c.get("s8c"):  # run_S8C writes its own batch folder (named in the case log)
                argv = list(c["argv"])
            else:
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
            entry = {"case": c["case"], "argv": c["argv"], "rc": rc, "wall_s": wall, "est_s": c["est_s"]}
            note = ""
            if c.get("s8c") and rc == 0:  # run_S8C returns 0 even when its case failed: read the outcome
                chk = s8c_case_check((folder / f"{c['case']}.log").read_text("utf-8", errors="replace"), c["case"])
                entry["s8c_check"] = chk
                if not chk["ok"]:
                    rc = entry["rc"] = S8C_FAILED_RC
                    entry["process_rc"] = 0
                    note = f" s8c_check=FAILED ({chk['reason']})"
                else:
                    note = f" s8c_check=ok {chk['batch_dir']}"
            done.append(entry)
            _log(progress, f"END {c['case']} {_dt.datetime.now().isoformat(timespec='seconds')} rc={rc} "
                           f"wall_s={wall:.0f}{note}")
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
