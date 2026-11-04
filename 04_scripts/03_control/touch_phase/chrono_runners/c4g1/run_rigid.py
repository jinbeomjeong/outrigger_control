"""C4G1 rigid rows: R9 mirror2 delta 0, delta 0.35 mm, R9 symmetric, R4. Pinned worktree code, flow limit off.

Config: the preset with touch_twist_hold=True (the rigid path has no config argument, so the preset call takes that default
here; the returned clip comes on with the preset). Gap: L2bModel(pad_gap_offsets_m=...). One batch folder per row with the case folder
named by the case id, so judge_batch reads it unchanged. Stops a case on any main-tree module.
Usage: python -I -B -X utf8 -u run_rigid.py
"""
from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import subprocess
import sys
import time
from functools import partial
from multiprocessing.connection import wait
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

HERE = Path(__file__).resolve().parent
WT = HERE / "wt"
MAIN = Path(r"C:\workspace\outrigger_control")
COMMIT = "15176d153465b45c6bbd58aec5bed2732b9696e8"
C2_SHA = "02ca442c3be01ab3c91822b3101c0c1054f1b59c878555ced14c7393af58afd4"
TIMEOUT_S = 5400.0
P_LOGICAL = list(range(16))
P_LIMIT = 80.0
SAMPLE_PY = r"C:\Users\jinbeom\.claude\tools\cpu-scheduler\sample.py"
DEV_PY = r"C:\ProgramData\miniforge3\envs\python-dev\python.exe"
sys.path.insert(0, str(WT / "03_src"))
sys.path.insert(0, str(WT / "04_scripts" / "02_chrono"))


def gaps(asym_m: float, delta_m: float) -> list[float]:
    """Offsets (FL, FR, RL, RR): left +asym, right -asym, all + delta [m]; run_asym.py gaps()."""
    return [asym_m + delta_m, -asym_m + delta_m, asym_m + delta_m, -asym_m + delta_m]


ROWS = {"R9_mirror2_d000": ("A_bottom_rpB_Fs0", gaps(-2.0e-3, 0.0)), "R9_mirror2_d035": ("A_bottom_rpB_Fs0", gaps(-2.0e-3, 0.35e-3)),
        "R9_sym": ("A_bottom_rpB_Fs0", None), "R4": ("K24_top_roll5.5_Fs4", None)}


def main_tree_modules() -> list[str]:
    root = MAIN.resolve()
    return [f"{n}: {m.__file__}" for n, m in list(sys.modules.items()) if getattr(m, "__file__", None) and Path(m.__file__).resolve().is_relative_to(root)]


def job(case, case_dir):
    import outrigger_sim
    from outrigger_sim.chrono import l2b_model
    from outrigger_sim.control import c2

    import run_S8C as s8

    c2_file = Path(c2.__file__)
    sha = hashlib.sha256(c2_file.read_bytes()).hexdigest()
    checks = {"outrigger_sim": outrigger_sim.__file__, "run_S8C": s8.__file__, "c2": str(c2_file), "c2_sha256": sha, "commit": COMMIT}
    if not (Path(outrigger_sim.__file__).resolve().is_relative_to(WT.resolve()) and Path(s8.__file__).resolve().is_relative_to(WT.resolve())) or sha != C2_SHA or main_tree_modules():
        raise SystemExit(f"code mix, stopped: {checks} {main_tree_modules()}")
    real_preset = c2.C2Config.with_10hz_d1

    def preset(self, **kw):
        kw.setdefault("touch_twist_hold", True)
        return real_preset(self, **kw)

    c2.C2Config.with_10hz_d1 = preset
    offsets = case.settings.get("pad_gap_offsets_m")
    built = []
    if offsets is not None:
        real = l2b_model.L2bModel

        def model(*a, **k):
            m = partial(real, pad_gap_offsets_m=tuple(offsets))(*a, **k)
            built.append(list(m.pad_gap_offsets_m))
            return m

        l2b_model.L2bModel = model
    out = s8.job_case(case, case_dir)
    res = json.loads(Path(case_dir, "result.json").read_text(encoding="utf-8"))
    text = str(res["settings"].get("controller_config", ""))
    side = dict(checks, row=case.settings["row"], pad_gap_offsets_m=offsets, models_built_offsets=built, main_tree_modules_at_end=main_tree_modules(),
                config_has_hold="touch_twist_hold=TouchTwistHoldSettings(enable=True, vector_ramp=True" in text, config_has_clip="clip_returned_command=True" in text,
                flow_limit=res["settings"].get("flow_limit"), hold_meta=(res.get("controller_meta") or {}).get("touch_twist_hold"), env={k: v for k, v in os.environ.items() if k.startswith("OUTRIGGER_")})
    Path(case_dir, "c4g1_job_side.json").write_text(json.dumps(side, indent=1, default=str), encoding="utf-8")
    return out


def p_use(psutil) -> float:
    per = psutil.cpu_percent(interval=2.0, percpu=True)
    return sum(per[i] for i in P_LOGICAL) / len(P_LOGICAL)


def main() -> None:
    import psutil

    from outrigger_sim import batch as B
    from outrigger_sim.batch import Case

    head = subprocess.run(["git", "-c", "core.longpaths=true", "-C", str(WT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL).stdout.strip()
    if head != COMMIT:
        raise SystemExit(f"worktree at {head}, want {COMMIT}")
    if any(k.startswith("OUTRIGGER_") for k in os.environ):
        raise SystemExit("OUTRIGGER_* set, refusing")
    stamp = time.strftime("%Y%m%d_%H%M%S")
    log = (HERE / f"run_rigid_{stamp}.log").open("a", encoding="utf-8", buffering=1)

    def say(msg: str) -> None:
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        log.write(line + "\n")

    ctx = multiprocessing.get_context("spawn")
    items = []
    for row, (cid, offs) in ROWS.items():
        d = MAIN / "07_results/S8" / f"c4g1_{row}_{stamp}"
        d.mkdir(parents=False, exist_ok=False)
        (d / "code_state.json").write_text(json.dumps({"commit": head, "worktree": str(WT), "c2_sha256": C2_SHA, "row": row, "pad_gap_offsets_m": offs, "pair_preset": "with_10hz_d1(touch_twist_hold=True)"}, indent=1), encoding="utf-8")
        case = Case(cid, {"duration_s": None, "row": row, "pad_gap_offsets_m": offs})
        B._check_inputs([case], job, d, 1)
        items.append((row, case, d))
    pending = list(items)
    running: dict[int, tuple] = {}
    done = {}
    sampler, last_start, t0, started_utc = None, -1e9, time.perf_counter(), B._utc_now_text()
    say(f"stamp {stamp} commit {head} P use {p_use(psutil):.1f} %")
    while pending or running:
        use = p_use(psutil)
        now = time.perf_counter()
        gap_ok = len(running) < 3 or now - last_start > 60.0
        if pending and len(running) < 4 and gap_ok and (use <= P_LIMIT or len(running) < 3):
            row, case, d = pending.pop(0)
            rc = B._start_case(ctx, job, case, d, B.Placement.PCORE, TIMEOUT_S)
            running[rc.process.sentinel] = (rc, row, d)
            last_start = now
            say(f"started {row} pid {rc.process.pid} P use {use:.1f} % running {len(running)}")
            if sampler is None:
                out = d / f"{row}.sample.json"
                sampler = subprocess.Popen([DEV_PY, "-I", SAMPLE_PY, "--pid", str(rc.process.pid), "--interval", "5", "--no-gpu", "--out", str(out)], stdin=subprocess.DEVNULL,
                                           stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            continue
        if not running:
            continue
        by_rc = {k: v[0] for k, v in running.items()}
        ended = wait(list(by_rc), timeout=min(10.0, B._wait_timeout_s(by_rc)))
        for sentinel in {*ended, *B._terminate_timed_out(by_rc)}:
            rc, row, d = running.pop(sentinel)
            o = B._finish_case(rc)
            done[row] = o
            doc = B._batch_document([o], job, started_utc, o.wall_s, 1, B.Placement.PCORE)
            B._write_text_atomically(d / B.BATCH_META_NAME, B._json_text(doc))
            say(f"finished {row} {o.status} {o.wall_s:.1f} s; running {len(running)}")
            if o.status != "ok":
                say((o.error or "")[-3000:])
    say(f"done wall {time.perf_counter() - t0:.1f} s stamp {stamp}; bad {[r for r, o in done.items() if o.status != 'ok']}")


if __name__ == "__main__":
    main()
