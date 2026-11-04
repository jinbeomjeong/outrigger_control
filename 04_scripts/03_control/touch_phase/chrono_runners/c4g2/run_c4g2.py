"""C4G2 rigid batch: nine table rows at commit 74032be, flow limit off, end rule on. No source change.

Config per row through the default of the preset call (the rigid path has no config argument). Gap: L2bModel(pad_gap_offsets_m=...).
Rows 6 and 9: A_bottom_rpB_Fs0 cloned with fs_kN = 4.0 (case_clone). One batch folder per row with the case folder named by the case id.
Usage: python -I -B -X utf8 -u run_c4g2.py run
       python -I -B -X utf8 -u run_c4g2.py check     (no simulation: clone and config check, prints and writes c4g2_clone_check.json)
"""
from __future__ import annotations

import dataclasses
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
COMMIT = "74032beae72c7e44858e41384bc54c263e724fd3"
C2_SHA = "28482b8d5678c3e1079c9dd89046013bd60cac718e0e8efa195101a36236df67"
TIMEOUT_S = 5400.0
P_LOGICAL = list(range(16))
P_LIMIT = 90.0
MAX_RUNNING = 3
SAMPLE_PY = r"C:\Users\jinbeom\.claude\tools\cpu-scheduler\sample.py"
DEV_PY = r"C:\ProgramData\miniforge3\envs\python-dev\python.exe"
sys.path.insert(0, str(WT / "03_src"))
sys.path.insert(0, str(WT / "04_scripts" / "02_chrono"))

M = 1.0e-3
D000 = [-2.00 * M, 2.00 * M, -2.00 * M, 2.00 * M]
D035 = [-1.65 * M, 2.35 * M, -1.65 * M, 2.35 * M]
D070 = [-1.30 * M, 2.70 * M, -1.30 * M, 2.70 * M]
K1 = {"touch_twist_hold": True, "reapproach_retrigger_two_samples": True}
C4 = {"touch_twist_hold": True}
OFF: dict = {}
R16, R12, R15, R9, R9F = "G1L_RE1bF_FL_top_o050_Fs4", "E_G4_Fs4", "G1L_RE1bF_FL_top_Fs0", "A_bottom_rpB_Fs0", "A_bottom_rpB_Fs4"
ROWS = {"R16_mirror2_d000_C4G2K1": (R16, D000, K1), "R16_mirror2_d070_C4G2K1": (R16, D070, K1), "R12_C4G2K1": (R12, None, K1), "R16_mirror2_d000_C4G2": (R16, D000, C4),
        "R15_C4G2K1": (R15, None, K1), "R9_mirror2_d035_Fs4_C4G2K1": (R9F, D035, K1), "R9_mirror2_d000_off": (R9, D000, OFF), "R9_mirror2_d035_off": (R9, D035, OFF),
        "R9_mirror2_d035_Fs4_off": (R9F, D035, OFF)}


def case_clone(s8):
    """A_bottom_rpB_Fs0 as a new case id with fs_kN 4.0; the rest of the table case unchanged. pair_fs0 as the Fs8 table case."""
    c = s8.case_table()[R9]
    base = dataclasses.replace(c.base, case_id=R9F, scenario=dataclasses.replace(c.base.scenario, case_id=R9F))
    return dataclasses.replace(c, case_id=R9F, fs_kN=4.0, pair_fs0=R9, base=base)


def main_tree_modules() -> list[str]:
    root = MAIN.resolve()
    return [f"{n}: {m.__file__}" for n, m in list(sys.modules.items()) if getattr(m, "__file__", None) and Path(m.__file__).resolve().is_relative_to(root)]


def job(case, case_dir):
    import outrigger_sim
    from outrigger_sim.chrono import l2b_model
    from outrigger_sim.control import c2

    import run_S8C as s8

    sha = hashlib.sha256(Path(c2.__file__).read_bytes()).hexdigest()
    checks = {"outrigger_sim": outrigger_sim.__file__, "run_S8C": s8.__file__, "c2": c2.__file__, "c2_sha256": sha, "commit": COMMIT}
    if not (Path(outrigger_sim.__file__).resolve().is_relative_to(WT.resolve()) and Path(s8.__file__).resolve().is_relative_to(WT.resolve())) or sha != C2_SHA or main_tree_modules():
        raise SystemExit(f"code mix, stopped: {checks} {main_tree_modules()}")
    flags = dict(case.settings["preset_flags"])
    real_preset = c2.C2Config.with_10hz_d1

    def preset(self, **kw):
        for k, v in flags.items():
            kw.setdefault(k, v)
        return real_preset(self, **kw)

    c2.C2Config.with_10hz_d1 = preset
    if case.case_id == R9F:
        table = s8.case_table()
        table[R9F] = case_clone(s8)
        s8.case_table = lambda: table
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
    cfg = c2.C2Config().with_10hz_d1()
    side = dict(checks, row=case.settings["row"], preset_flags=flags, pad_gap_offsets_m=offsets, models_built_offsets=built, main_tree_modules_at_end=main_tree_modules(),
                config_hold=str(cfg.touch_twist_hold), config_clip=cfg.clip_returned_command, config_retrigger_samples=cfg.r8.lifted_reapproach.retrigger_samples,
                fs_kN=res["settings"]["s8"].get("fs_kN"), flow_limit=res["settings"].get("flow_limit"), hold_meta=(res.get("controller_meta") or {}).get("touch_twist_hold"),
                env={k: v for k, v in os.environ.items() if k.startswith("OUTRIGGER_")})
    Path(case_dir, "c4g2_job_side.json").write_text(json.dumps(side, indent=1, default=str), encoding="utf-8")
    return out


def p_use(psutil) -> float:
    per = psutil.cpu_percent(interval=2.0, percpu=True)
    return sum(per[i] for i in P_LOGICAL) / len(P_LOGICAL)


def check() -> None:
    from outrigger_sim.control import c2

    import run_S8C as s8

    print("outrigger_sim mix", main_tree_modules(), "c2 sha ok", hashlib.sha256(Path(c2.__file__).read_bytes()).hexdigest() == C2_SHA, s8.ROOT)
    table = s8.case_table()
    fs0, fs8, clone = table[R9], table["A_bottom_rpB_Fs8"], case_clone(s8)

    def flat(meta, prefix="") -> dict:
        out = {}
        for k, v in meta.items():
            out.update(flat(v, f"{prefix}{k}.") if isinstance(v, dict) else {f"{prefix}{k}": v})
        return out

    a, b, c = flat(fs0.to_meta()), flat(fs8.to_meta()), flat(clone.to_meta())
    res = {"clone_vs_Fs0": {k: [a.get(k), c.get(k)] for k in a.keys() | c.keys() if a.get(k) != c.get(k)},
           "Fs8_vs_Fs0_table": {k: [a.get(k), b.get(k)] for k in a.keys() | b.keys() if a.get(k) != b.get(k)},
           "clone_vs_Fs8_except_fs": {k: [b.get(k), c.get(k)] for k in b.keys() | c.keys() if b.get(k) != c.get(k)},
           "scenario_seed": [fs0.scenario.seed, clone.scenario.seed], "wall_estimate_s": clone.wall_estimate_s("p")}
    plant = {}
    cfgs = {}
    for name, cc in (("Fs0", fs0), ("clone", clone), ("Fs8", fs8)):
        params, ctrl, over = s8.l2b_params(cc)
        plant[name] = {k: v for k, v in over.items()}
        cfgs[name] = str(s8._controller(cc, ctrl, params)[1])
    res["plant_overrides"] = plant
    res["config_text_same_clone_vs_Fs0"] = cfgs["clone"] == cfgs["Fs0"]
    res["config_text_same_clone_vs_Fs8"] = cfgs["clone"] == cfgs["Fs8"]
    off = c2.C2Config().with_10hz_d1()
    on = c2.C2Config().with_10hz_d1(**K1)
    res["off_preset"] = {"hold": str(off.touch_twist_hold), "clip": off.clip_returned_command, "retrigger_samples": off.r8.lifted_reapproach.retrigger_samples}
    res["k1_preset"] = {"hold": str(on.touch_twist_hold), "clip": on.clip_returned_command, "retrigger_samples": on.r8.lifted_reapproach.retrigger_samples}
    for cid in (R16, R12, R15):
        print(cid, table[cid].fs_kN, table[cid].event, table[cid].phase_offset_s)
    res["main_tree_modules"] = main_tree_modules()
    (HERE / "c4g2_clone_check.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=0, default=str)[:4000])


def run() -> None:
    import psutil

    from outrigger_sim import batch as B
    from outrigger_sim.batch import Case

    head = subprocess.run(["git", "-c", "core.longpaths=true", "-C", str(WT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL).stdout.strip()
    if head != COMMIT:
        raise SystemExit(f"worktree at {head}, want {COMMIT}")
    bad = {k: os.environ[k] for k in os.environ if k.startswith("OUTRIGGER_") and k != "OUTRIGGER_ROD_SIDE_MECHANICS"}
    if bad:
        raise SystemExit(f"OUTRIGGER_* set, refusing: {bad}")
    stamp = time.strftime("%Y%m%d_%H%M%S")
    log = (HERE / f"run_c4g2_{stamp}.log").open("a", encoding="utf-8", buffering=1)

    def say(msg: str) -> None:
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        log.write(line + "\n")

    ctx = multiprocessing.get_context("spawn")
    items = []
    for row, (cid, offs, flags) in ROWS.items():
        d = MAIN / "07_results/S8" / f"c4g2_{row}_{stamp}"
        d.mkdir(parents=False, exist_ok=False)
        (d / "code_state.json").write_text(json.dumps({"commit": head, "worktree": str(WT), "c2_sha256": C2_SHA, "row": row, "case": cid, "pad_gap_offsets_m": offs, "preset_flags": flags}, indent=1), encoding="utf-8")
        case = Case(cid, {"duration_s": None, "row": row, "pad_gap_offsets_m": offs, "preset_flags": flags})
        B._check_inputs([case], job, d, 1)
        items.append((row, case, d))
    pending = list(items)
    running: dict[int, tuple] = {}
    done = {}
    limit, sampler, last_start, high_since, t0, started_utc = MAX_RUNNING, None, -1e9, None, time.perf_counter(), B._utc_now_text()
    say(f"stamp {stamp} commit {head}")
    while pending or running:
        use = p_use(psutil)
        now = time.perf_counter()
        if len(running) >= 3 and use > P_LIMIT:
            high_since = high_since if high_since is not None else now
            if limit == 3 and now - high_since > 60.0:
                limit = 2
                say(f"P use {use:.1f} % above {P_LIMIT} % for 60 s: limit 2 (no running case is touched)")
        else:
            high_since = None
        gap_ok = len(running) < 2 or now - last_start > 60.0
        if pending and len(running) < limit and gap_ok and (use <= P_LIMIT or len(running) < 2):
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
            B._write_text_atomically(d / B.BATCH_META_NAME, B._json_text(B._batch_document([o], job, started_utc, o.wall_s, 1, B.Placement.PCORE)))
            say(f"finished {row} {o.status} {o.wall_s:.1f} s; pending {len(pending)} running {len(running)}")
            if o.status != "ok":
                say((o.error or "")[-3000:])
    say(f"done wall {time.perf_counter() - t0:.1f} s stamp {stamp} limit {limit}; bad {[r for r, o in done.items() if o.status != 'ok']}")


if __name__ == "__main__":
    check() if sys.argv[1] == "check" else run()
