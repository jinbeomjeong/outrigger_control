"""Build the K-2 V-2 .. V-6 pre-launch drafts (rules k2_touch_creep_rules.md + rev1; nothing is run).

Writes next to this file:
  k2_v3_keys.txt            V-3 273 keys (rules 3.3 selection on the stored D8x ra_off.json)
  k2_commands.json          every launch step of V-2 .. V-6 (argv, cwd, env, output, pool placeholders)
  k2_manifest.json          inputs of k2_judge.py (path 1) and k2_recount.py (path 2)
  k2_expect.json            k2_recount --expect (expect-template + the fixed g8 count)
  k2_fields.json            path 2 field map (= k2_recount DEFAULT_FIELDS, written out to be sha-fixed)
  k2_prelaunch_<v2..v6>.json  pre-launch record drafts (rules I-3); pool / worker fields left to the plan

Usage: python -I -B make_prelaunch.py [--run-wt <pinned checkout at the run HEAD>]
       [--ra-off <stored D8x ra_off.json>]
Placeholders kept for the launch: {MASK} {WORKERS} (compute-scheduler-expert plan), {BATCH_<engine>_<arm>}
(Chrono batch folders, known after the runner starts).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PY = r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe"
CHRONO_PY = r"C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe"
RUN_WT_DEFAULT = r"C:\workspace\outrigger_control\.claude\worktrees\k2-run"
RA_OFF_DEFAULT = r"C:\workspace\outrigger_control\06_analysis\02_control\d8x\ra\ra_off.json"
HEAD = ("{RUN_HEAD} = the master merge commit of k2-v7k1-dhat (cad-expert 09f66c4), k2-prelaunch-fix "
        "(python-expert c77ecf5) and k2-prelaunch (k2_recount 1.2) onto dc2029b")
ENV_DIR = Path(PY).parent
THREAD_ENV = {"MKL_THREADING_LAYER": "TBB", "MKL_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
              "OPENBLAS_NUM_THREADS": "1", "NUMBA_NUM_THREADS": "1", "PYTHONDONTWRITEBYTECODE": "1"}
PATH_VALUE = ";".join([str(ENV_DIR), str(ENV_DIR / "Library/mingw-w64/bin"), str(ENV_DIR / "Library/usr/bin"),
                       str(ENV_DIR / "Library/bin"), str(ENV_DIR / "Scripts"), str(ENV_DIR / "bin"),
                       r"C:\Windows\System32", r"C:\Windows", r"C:\Program Files\Git\cmd"])
HARNESS_ENV = {"CONDA_PREFIX": str(ENV_DIR), "CONDA_DEFAULT_ENV": "dynamics-dev", "PATH": PATH_VALUE, **THREAD_ENV}
V3_ARMS = ("H0", "L1eq", "L1eq_fs", "L1eq_zm", "AUG", "AUG_crc2", "AUG_eps")
ARMS = {"off": "off", "tcl": "on"}
V5_STEP_IDS = ("reg1", "reg2", "reg3", "reg4", "reg5", "reg6", "reg7", "grid_r67_main", "grid_r67_top",
               "grid_r69_top", "grid_r69_bottom", "soil_A", "d8", "noise_L1L2")
V5_BUNDLE_OF = {**{f"reg{i}": "regression" for i in range(1, 8)},
                **{s: "grid" for s in ("grid_r67_main", "grid_r67_top", "grid_r69_top", "grid_r69_bottom")},
                "soil_A": "soil", "d8": "d8", "noise_L1L2": "noise_L2"}
G8_JOBS = ("jobs1.json", "jobs3.json", "jobs5.json")
V5_BUNDLES = (("noise_L2", "noise_cp", 855), ("grid", "pass_to_fail", 768), ("d8", "pass_to_fail", 576),
              ("soil", "pass_to_fail", 60), ("regression", "pass_to_fail", 93),
              ("ps7", "pass_to_fail", 20), ("g8_safe_stop", "g8", 83))
"""V-5 judged rows per arm. regression 93 = judged rows of the 118 (criteria.md: L1 / L2 / soil / slope rows
judged, L3 rows record only; acc_judge counts 13 + 17 + 2 + 11 + clip_A 20 + r79 L1/L2 30), record-level
correction (a) of the pre-launch record, 2026-11-10."""
WRAP_REL = r"04_scripts\03_control\k2\run_with_identity.py"
FIX_BLOBS = {  # python-expert k2-prelaunch-fix c77ecf5 (given; re-check at RUN_HEAD with git rev-parse)
    "04_scripts/03_control/k2/k2_judge.py": "7ee9ccc109578da2bb0e8e25f3811d9c0f73664b",
    "04_scripts/03_control/k2/k2_v5_flatten.py": "a83abd803dd91e3855159e919770092e40a3cdb9",
    "04_scripts/03_control/k2/run_with_identity.py": "fab7664bd3ba16723e4202bf71dc7d87ab0cf7f0",
    "04_scripts/03_control/touch_phase/run_ps7.py": "248f5363cbdbaf1bc20eac3ef5e73bdfd6e05acd",
    "06_analysis/02_control/touch_phase/acceptance/g8_safe_stop/g8trace.py": "d8bfe68e4350195951ec58a6a69bc24c04d293cc",
}
V5_NOTE_REGRESSION = (
    "V-5 regression: the rules 3.4 / criteria.md row is '118 | L1 / L2 / soil / slope rows pass->fail 0 (L3 rows "
    "record only)'. The judged rows are 93 (acc_judge: 13 + 17 + 2 + 11 + clip_A 20 + r79 L1/L2 30, python-expert "
    "count). The other 25 of the 118 are rows acc_judge does not judge (clip_r79_L3L4 is record only; the r79 L1 "
    "reference rows are not judged rows); their exact list is fixed from the flattener summary at the launch "
    "record. The flat file of k2_v5_flatten.py holds the 93 judged rows; E-1 expects 93. Record-level correction "
    "(a): the sealed text already restricts the criterion to those rows; no grade effect.")


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def blob(path: str) -> str:
    """Blob id the working file has / will have when committed (``git hash-object``, filters applied)."""
    out = subprocess.run(["git", "-C", str(REPO), "hash-object", path], capture_output=True,
                         text=True, timeout=60)
    return out.stdout.strip() or "<hash-object failed>"


def v3_keys(ra_off: Path) -> list[str]:
    """Rules 3.3: J3 fail rows (68) union all top rows with theta_g > 0 (272) of the K1-off arm."""
    runs = json.loads(ra_off.read_text(encoding="utf-8"))["runs"]
    sel = {r["id"] for r in runs if r["d8x"]["J3_pad_lift_samples"] > 0}
    sel |= {r["id"] for r in runs if r["level"] == "top" and r["angles_deg"][1] > 0}
    return sorted(sel)


def harness_step(sid: str, bundle: str, arm: str, script: str, args: list[str], out: str, run_wt: str,
                 env: dict | None = None, rows: int | None = None) -> dict:
    return {"id": sid, "bundle": bundle, "arm": arm, "rows": rows, "pool": "{POOL}", "mask": "{MASK}",
            "argv": [PY, "-I", "-B", script, *args], "cwd": run_wt,
            "env": {**HARNESS_ENV, **(env or {})}, "output": out,
            "identity_sidecar": out + ".launch.json"}


def d8x_steps(run_wt: str) -> list[dict]:
    acc = rf"{run_wt}\04_scripts\03_control\touch_phase\acceptance\acc_d8.py"
    d8x_pts = rf"{run_wt}\06_analysis\02_control\d8x\d8x_points.json"
    k2_pts = rf"{run_wt}\06_analysis\02_control\k2\k2_points_5p5_3p5.json"
    keys = rf"{run_wt}\06_analysis\02_control\k2\prelaunch\k2_v3_keys.txt"
    runs = rf"{run_wt}\06_analysis\02_control\k2\runs"
    steps = []
    for arm, k2 in ARMS.items():
        for k1, stages, n in (("off", "main,robust,kt", 910), ("on", "main", 192)):
            out = rf"{runs}\v2\v2_k1{k1}_{arm}.json"
            steps.append(harness_step(f"v2_k1{k1}_{arm}", "v2", arm, acc,
                                      [out, "--points", d8x_pts, "--stages", stages, "--k1", k1, "--k2", k2,
                                       "--workers", "{WORKERS}"], out, run_wt, rows=n))
        for aug in V3_ARMS:
            out = rf"{runs}\v3\v3_{aug}_{arm}.json"
            steps.append(harness_step(f"v3_{aug}_{arm}", "v3", arm, acc,
                                      [out, "--points", d8x_pts, "--stages", "main,robust,kt", "--k1", "off",
                                       "--k2", k2, "--aug", aug, "--keys-file", keys, "--workers", "{WORKERS}"],
                                      out, run_wt, rows=273))
        out = rf"{runs}\v4\v4_{arm}.json"
        steps.append(harness_step(f"v4_{arm}", "v4", arm, acc,
                                  [out, "--points", k2_pts, "--stages", "main,robust,kt", "--levels", "top",
                                   "--k1", "off", "--k2", k2, "--workers", "{WORKERS}"], out, run_wt, rows=596))
    return steps


def v5_steps(run_wt: str) -> list[dict]:
    """The stored C4G2/K1 acceptance steps (steps_E1/E2.json) moved to the pinned checkout, ACC_COMBO preset,
    ACC_K2 per arm, outputs under k2/runs/v5/<arm>; plus PS-7 and the G8 safe-stop driver."""
    acc_dir = REPO / "04_scripts" / "03_control" / "touch_phase" / "acceptance"
    stored = []
    for name in ("steps_E1.json", "steps_E2.json"):
        stored += json.loads((acc_dir / name).read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in stored}
    launch = rf"{run_wt}\04_scripts\03_control\touch_phase\acceptance\acc_launch.py"
    steps = []
    for arm, k2 in ARMS.items():
        out_dir = rf"{run_wt}\06_analysis\02_control\k2\runs\v5\{arm}"
        for sid in V5_STEP_IDS:
            s = by_id[sid]
            cmd = s["cmd"]
            old_wt = s["env"]["ACC_WT"]
            body = cmd.split(" -I -B ", 1)[1]
            script, rest = body.split(" ", 1)
            if script.endswith("acc_launch.py"):
                target, rest = rest.split(" ", 1)
                target = target.replace(old_wt, run_wt)
                head = [launch, target]
            else:  # acc_d8.py / acc_crawler.py of the old scratch copy -> the committed one
                head = [rf"{run_wt}\04_scripts\03_control\touch_phase\acceptance\{Path(script).name}"]
            rest = rest.replace(old_wt, run_wt)
            rest = re.sub(r"C:\\workspace\\outrigger_control\\06_analysis\\02_control\\touch_phase\\acceptance"
                          r"\\(?:regression|grid|soil|d8|noise|crawler)\\", lambda m: out_dir + "\\", rest)
            rest = re.sub(r"--affinity 0x[0-9A-Fa-f]+", "--affinity {MASK}", rest)
            rest = re.sub(r"--workers \d+", "--workers {WORKERS}", rest)
            env = {k: v for k, v in s["env"].items() if k not in HARNESS_ENV}
            env.update({"ACC_WT": run_wt, "ACC_COMBO": "preset", "ACC_K2": k2, "OUTRIGGER_ACC": "k2",
                        "ACC_PROVENANCE": rf"{out_dir}\provenance\{sid}.json"})
            for k in list(env):
                if k.endswith("_AFFINITY"):
                    env[k] = "{MASK}"
            args = _split(rest)
            out_guess = next((a for a in args if a.startswith(out_dir)), env["ACC_PROVENANCE"])
            steps.append({"id": f"v5_{sid}_{arm}", "bundle": "v5", "v5_bundle": V5_BUNDLE_OF[sid], "arm": arm,
                          "pool": "{POOL}", "mask": "{MASK}", "argv": [PY, "-I", "-B", *head, *args],
                          "cwd": run_wt, "env": {**HARNESS_ENV, **env}, "output": out_guess,
                          "identity_sidecar": rf"{out_dir}\{sid}.launch.json",
                          "note": "output file named by the script env/args (r67/r69/r72/r79/r426a write under "
                                  "their own default names when no --out is given; the provenance file is the "
                                  "step record)"})
        ps7 = rf"{run_wt}\04_scripts\03_control\touch_phase\run_ps7.py"
        steps.append({"id": f"v5_ps7_{arm}", "bundle": "v5", "v5_bundle": "ps7", "arm": arm, "pool": "{POOL}",
                      "mask": "{MASK}",
                      "argv": [PY, "-I", "-B", launch, ps7, "E", "--workers", "{WORKERS}", "--mask", "{MASK}",
                               "--out", rf"{out_dir}\ps7.json"],
                      "cwd": run_wt,
                      "env": {**HARNESS_ENV, "ACC_WT": run_wt, "ACC_COMBO": "preset", "ACC_K2": k2,
                              "OUTRIGGER_ACC": "k2", "ACC_PROVENANCE": rf"{out_dir}\provenance\ps7.json"},
                      "output": rf"{out_dir}\ps7.json",
                      "identity_sidecar": rf"{out_dir}\ps7.launch.json"})
        g8 = rf"{run_wt}\06_analysis\02_control\touch_phase\acceptance\g8_safe_stop"
        for job in G8_JOBS:
            stem = job.replace(".json", "")
            steps.append({"id": f"v5_g8_{stem}_{arm}", "bundle": "v5", "v5_bundle": "g8_safe_stop", "arm": arm,
                          "pool": "{POOL}", "mask": "{MASK}",
                          "argv": [PY, "-I", "-B", rf"{g8}\g8trace.py", run_wt, rf"{g8}\{job}",
                                   rf"{out_dir}\g8_{stem}.jsonl", "--workers", "{WORKERS}"],
                          "cwd": run_wt,
                          "env": {**HARNESS_ENV, "ACC_WT": run_wt, "ACC_COMBO": "off", "ACC_K2": k2,
                                  "R72_PATH": "per_leg", "R79_AFFINITY": "{MASK}"},
                          "output": rf"{out_dir}\g8_{stem}.jsonl",
                          "identity_sidecar": rf"{out_dir}\g8_{stem}.launch.json"})
        judge = rf"{run_wt}\04_scripts\03_control\s8\r79_sensor_judge.py"
        for name, run_file in (("r79_L1L2", "r79_L1L2.json"), ("clip_r79_L1L2", "clip_r79_L1L2.json")):
            out = rf"{out_dir}\{name}_judgement.json"
            steps.append({"id": f"v5_judge_{name}_{arm}", "bundle": "v5", "v5_bundle": "post", "arm": arm,
                          "after": [f"v5_{'noise_L1L2' if name == 'r79_L1L2' else 'reg4'}_{arm}"],
                          "pool": "{POOL}", "mask": "{MASK}",
                          "argv": [PY, "-I", "-B", judge, "judge", out, rf"{out_dir}\{run_file}"],
                          "cwd": run_wt, "env": {**HARNESS_ENV}, "output": out,
                          "identity_sidecar": rf"{out_dir}\{name}_judgement.launch.json",
                          "note": "the existing r79 judgement (acc_judge.r79_judge), needed by the flattener"})
        flat = rf"{out_dir}\flat"
        steps.append({"id": f"v5_flatten_{arm}", "bundle": "v5", "v5_bundle": "post", "arm": arm,
                      "after": [f"v5_*_{arm}"], "pool": "{POOL}", "mask": "{MASK}",
                      "argv": [PY, "-I", "-B", rf"{run_wt}\04_scripts\03_control\k2\k2_v5_flatten.py",
                               "--arm-dir", out_dir, "--out-dir", flat, "--checkout", run_wt],
                      "cwd": run_wt, "env": {**HARNESS_ENV}, "output": flat,
                      "identity_sidecar": rf"{out_dir}\flatten.launch.json",
                      "note": "last V-5 step of the arm; writes <bundle>.json per V-5 bundle and flatten_summary.json"})
    return steps


def wrap(step: dict, run_wt: str) -> dict:
    """Harness steps run under run_with_identity.py (python-expert c77ecf5); the parent shell is pinned first."""
    if "identity_sidecar" not in step or step["argv"][0] != PY:
        return step
    inner = step["argv"]
    step = dict(step)
    step["inner_argv"] = inner
    step["argv"] = [PY, "-I", "-B", rf"{run_wt}\{WRAP_REL}", step["identity_sidecar"], "--git-dir", run_wt, "--",
                    *inner]
    step["affinity_note"] = "the wrapper never sets affinity: start it from a shell / runner already pinned to {MASK}"
    return step


def _split(text: str) -> list[str]:
    out, cur, quoted = [], "", False
    for ch in text:
        if ch == '"':
            quoted = not quoted
            continue
        if ch == " " and not quoted:
            if cur:
                out.append(cur)
            cur = ""
            continue
        cur += ch
    if cur:
        out.append(cur)
    return out


def v6_steps(run_wt: str) -> list[dict]:
    s6c = rf"{run_wt}\04_scripts\02_chrono\run_S6C.py"
    s8c = rf"{run_wt}\04_scripts\02_chrono\run_S8C.py"
    steps = [{"id": "v6_snaps_k2_check", "bundle": "v6", "arm": "both", "pool": "any",
              "argv": [CHRONO_PY, "-I", "-X", "utf8", "-u", s6c, "snaps-k2", "--jobs", "1", "--dry-run"],
              "cwd": run_wt,
              "note": "check only: the shared start state 07_results\\states_L1R\\S6_crawler_top_k2pp025 exists; "
                      "the dry run must list it under 'existing' and 'missing' empty (else stop and ask)"}]
    for arm, k2 in ARMS.items():
        tag = "final_C4G2_LAS" + ("_TCL" if arm == "tcl" else "")
        l1_dir = rf"{run_wt}\07_results\S6\k2v6_L1_{arm}"
        l2_dir = rf"{run_wt}\07_results\S8\k2v6_L2b_{arm}"
        steps.append({"id": f"v6_L1_{arm}", "bundle": "v6", "engine": "L1", "arm": arm, "pool": "{POOL}",
                      "argv": [CHRONO_PY, "-I", "-X", "utf8", "-u", s6c, "run", "--set", "k2_v6", "--approved",
                               "--jobs", "2", "--k2", k2, "--k1-order-gate", "off", "--expect-controller", tag,
                               "--pad-zeta-moving", "0.1", "--tag", f"k2v6_{arm}", "--placement", "{PLACEMENT}",
                               "--batch-dir", l1_dir],
                      "cwd": run_wt, "output": l1_dir,
                      "identity": rf"{l1_dir}\batch_meta.json identity_start / identity_end (orig_argv, cwd, git HEAD "
                                  r"and status, env, affinity, per-row exit_code, all_rc_zero); batch.json exit_code",
                      "placement_rule": "{PLACEMENT} = ecore on the E pool, pcore on the P pool (the runner default "
                                        "is pcore); both arms the same",
                      "est_s_per_row": {"E": 624, "P": [177, 270]}})
        steps.append({"id": f"v6_L2b_{arm}", "bundle": "v6", "engine": "L2b", "arm": arm, "pool": "{POOL}",
                      "argv": [CHRONO_PY, "-I", "-X", "utf8", "-u", s8c, "run", "--set", "k2_v6", "--approved",
                               "--workers", "{L2B_WORKERS}", "--k2", k2, "--k1-order-gate", "off",
                               "--expect-controller", tag, "--tag", f"k2v6_{arm}", "--batch-dir", l2_dir],
                      "cwd": run_wt, "output": l2_dir,
                      "identity": rf"{l2_dir}\batch_meta.json identity_start / identity_end; batch.json exit_code",
                      "placement_rule": "{L2B_WORKERS} = e6 on the E pool, p7 on the P pool; both arms the same",
                      "est_s_per_row": {"E": [829, 865], "E_upper": 1400, "P": [507, 529]}})
    return steps


V7_ROWS = ("K2V7_P3b_J1_B_top_Fs4", "K2V7_P3b_J2_B_top_Fs4")
V7_TAG = {"off": "final_C4G2_LAS_K1", "tcl": "final_C4G2_LAS_K1_TCL"}


def v7_steps(run_wt: str) -> list[dict]:
    """V-7 SCM, record only, K1 on (user decision): cad-expert branch k2-v7k1-dhat (bf3f475)."""
    s9 = rf"{run_wt}\04_scripts\02_chrono\s9_batch.py"
    return [{"id": "v7_k2_v7", "bundle": "v7", "arm": "both", "pool": "{POOL}",
             "argv": [CHRONO_PY, "-I", "-X", "utf8", "-u", s9, "run", "k2_v7", "--parallel", "{P}"],
             "cwd": run_wt, "env": {"OMP_WAIT_POLICY": "PASSIVE"},
             "rows": [f"{r}_{a}" for r in V7_ROWS for a in ("off", "tcl")], "expected_tag": V7_TAG,
             "est_p_s_per_row": 11000,
             "note": "argv per row = the FINAL-REP row + --expect-controller <tag> --k1-order-gate on --k2 off|on "
                     "(s9_batch k2_v7); --threads / OMP_WAIT_POLICY / hull hook recorded per row (I-6); "
                     "[--parallel-e N] only if the plan puts rows on E (then both arms of a row pair on the same pool)",
             "output": "{BATCH_V7}", "identity_sidecar": "{BATCH_V7}.launch.json"}]


def manifest(run_wt: str) -> dict:
    runs = rf"{run_wt}\06_analysis\02_control\k2\runs"
    d8x_pts = rf"{run_wt}\06_analysis\02_control\d8x\d8x_points.json"
    k2_pts = rf"{run_wt}\06_analysis\02_control\k2\k2_points_5p5_3p5.json"
    stored = [r"C:\workspace\outrigger_control\06_analysis\02_control\d8x\ra\ra_off.json",
              r"C:\workspace\outrigger_control\06_analysis\02_control\d8x\ra\ra_on.json"]

    m = {"_note": "one manifest for both paths: 'points' (path 1) and 'points_file' (path 2) name the same file; "
                  "each acc_d8 output keeps its series in <stem>_series next to it (no series_root: k2_recount "
                  "1.2 takes that folder per file)",
         "v2": {"off": [rf"{runs}\v2\v2_k1off_off.json", rf"{runs}\v2\v2_k1on_off.json"],
                "tcl": [rf"{runs}\v2\v2_k1off_tcl.json", rf"{runs}\v2\v2_k1on_tcl.json"],
                "points": d8x_pts, "points_file": d8x_pts, "stored_off": stored},
         "v3": {"arms": {a: {"off": [rf"{runs}\v3\v3_{a}_off.json"], "tcl": [rf"{runs}\v3\v3_{a}_tcl.json"]}
                         for a in V3_ARMS},
                "points": d8x_pts, "points_file": d8x_pts},
         "v4": {"off": [rf"{runs}\v4\v4_off.json"], "tcl": [rf"{runs}\v4\v4_tcl.json"],
                "points": k2_pts, "points_file": k2_pts},
         "v5": {b: {"kind": k, "count": n, "off": [rf"{runs}\v5\off\flat\{b}.json"],
                    "tcl": [rf"{runs}\v5\tcl\flat\{b}.json"], "key": "key", "status": "pass",
                    **({"ready": "ready", "faults": "faults"} if k == "g8" else {})}
                for b, k, n in V5_BUNDLES},
         "v6": {"rows": {}}}
    for eng, sub in (("L1", "S6"), ("L2b", "S8")):
        for floor in ("fdown3.5", "k2pp025"):
            fs = "Fs0" if eng == "L1" else "Fs4"
            for arm in ARMS:
                name = f"K2_{eng}_top_{floor}_{fs}_{arm}"
                b = rf"{run_wt}\07_results\{sub}\k2v6_{eng}_{arm}"
                m["v6"]["rows"][name] = {"row_json": rf"{b}\{name}\k2_row.json",
                                         "pads_npz": rf"{b}\{name}\k2_pads.npz",
                                         "rate_npz": rf"{b}\{name}\k2_rate.npz", "engine": eng, "arm": arm}
    m["v7"] = {"rows": {f"{r}_{a}": {"row_json": rf"{{BATCH_V7}}\{r}_{a}\k2_row.json",
                                     "pads_npz": rf"{{BATCH_V7}}\{r}_{a}\k2_pads.npz", "engine": "SCM", "arm": a,
                                     "expected_tag": V7_TAG[a]}
                        for r in V7_ROWS for a in ("off", "tcl")},
               "_note": "record only (rules 3.6); path 2 k2_recount has no V-7 command (record-v7 is path 1 only)"}
    return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-wt", default=RUN_WT_DEFAULT)
    ap.add_argument("--ra-off", default=RA_OFF_DEFAULT)
    args = ap.parse_args()
    keys = v3_keys(Path(args.ra_off))
    key_sha = hashlib.sha256("\n".join(keys).encode()).hexdigest()
    assert len(keys) == 273 and key_sha == "d4a030d71e4a365e328fbbf7caa212c378a8671fed8ba206d25b50666255cf95", key_sha
    (HERE / "k2_v3_keys.txt").write_bytes(("\n".join(keys) + "\n").encode("utf-8"))
    spec = importlib.util.spec_from_file_location("k2_recount", REPO / "04_scripts/03_control/k2/k2_recount.py")
    kr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kr)
    expect = kr.expect_template()
    expect["v5"]["g8_safe_stop"]["count"] = 83
    expect["v5"]["regression"]["count"] = 93
    expect["note"] = ("expect-template of k2_recount; g8_safe_stop = 83 jobs (jobs1 12 + jobs3 37 + jobs5 34); "
                      "regression = 93 judged rows of the 118 (" + V5_NOTE_REGRESSION + ")")
    files = {"k2_commands.json": {"head": HEAD, "run_wt": args.run_wt,
                                  "steps": [wrap(s, args.run_wt) for s in d8x_steps(args.run_wt) + v5_steps(args.run_wt)]
                                  + v6_steps(args.run_wt) + v7_steps(args.run_wt)},
             "k2_manifest.json": manifest(args.run_wt), "k2_expect.json": expect,
             "k2_fields.json": kr.DEFAULT_FIELDS}
    for name, doc in files.items():
        (HERE / name).write_bytes(json.dumps(doc, indent=1).encode("utf-8"))
    k2 = REPO / "06_analysis/02_control/k2"
    common = {
        "status": "draft (not a launch record until the pool fields and placeholders are filled)",
        "head": HEAD, "run_wt": args.run_wt,
        "rules": {"original": {"path": "06_analysis/02_control/k2/k2_touch_creep_rules.md",
                               "sha256": sha(k2 / "k2_touch_creep_rules.md")},
                  "rev1": {"path": "06_analysis/02_control/k2/k2_touch_creep_rules_rev1.md",
                           "sha256": sha(k2 / "k2_touch_creep_rules_rev1.md")},
                  "dyn_spec": {"path": "06_analysis/02_control/k2/k2_dyn_spec.md", "sha256": sha(k2 / "k2_dyn_spec.md")}},
        "path2": {"path": "04_scripts/03_control/k2/k2_recount.py",
                  "blob": blob("04_scripts/03_control/k2/k2_recount.py")},
        "path1": {"path": "04_scripts/03_control/k2/k2_judge.py",
                  "blob": FIX_BLOBS["04_scripts/03_control/k2/k2_judge.py"]},
        "fix_blobs_c77ecf5": FIX_BLOBS,
        "chrono_identity": "V-6 batch_meta.json identity_start / identity_end (orig_argv, cwd, git HEAD and status, "
                           "env, affinity, per-row exit_code, all_rc_zero) + batch.json exit_code (cad-expert "
                           "09f66c4); V-7 s9_batch batch.json argv / rc",
        "v5_regression_rows": V5_NOTE_REGRESSION,
        "point_files": {"k2_points_5p5_3p5.json": sha(k2 / "k2_points_5p5_3p5.json"),
                        "d8x_points.json": sha(REPO / "06_analysis/02_control/d8x/d8x_points.json")},
        "inputs": {n: sha(HERE / n) for n in ("k2_manifest.json", "k2_expect.json", "k2_fields.json",
                                             "k2_commands.json", "k2_v3_keys.txt")},
        "v3_keys": {"n": len(keys), "sha256_sorted_joined": key_sha},
        "interpreter": {"harness": PY, "chrono": CHRONO_PY},
        "threads": THREAD_ENV,
        "pool": {"plan_id": "{PLAN_ID}", "mask": "{MASK}", "workers": "{WORKERS}", "pcore_or_ecore": "{POOL}",
                 "rule": "the off and K-2 steps of one bundle (and of one V-3 arm) run in the same pool"},
        "notes": (k2 / "k2_prelaunch_notes.md").read_text(encoding="utf-8"),
    }
    for b in ("v2", "v3", "v4", "v5", "v6", "v7"):
        doc = {**common, "bundle": b, "steps": [s["id"] for s in files["k2_commands.json"]["steps"] if s["bundle"] == b]}
        (HERE / f"k2_prelaunch_{b}.json").write_bytes(json.dumps(doc, indent=1, ensure_ascii=False).encode("utf-8"))
    print(json.dumps({"keys": len(keys), "steps": len(files["k2_commands.json"]["steps"]),
                      "inputs": common["inputs"], "path2_blob": common["path2"]["blob"]}))


if __name__ == "__main__":
    main()
