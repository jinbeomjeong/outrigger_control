"""r79 sensor study, pressure grades L3 (conservative) / L4 (old_worst) with the final controller.

Why: the journal table T_sensor gives L3 14/501 and L4 82/501 from ``r79_final_judgement_v3.json``,
which ran before P-S8-33 (rule R6, LOC revocation). L2 (normal, 11/835) was re-run with the final
controller in re-run C (spec 429.11.2, ``fin_r79_merged.json``). User decision 2026-10-31: re-run
L3 / L4 with the final controller (``C2Config.with_10hz_d1()`` defaults = R8 C2 + L1gs + DSb75 +
SGS any_loc + R4c30, spec 429.11) on the same reduced harness.

Runs (``run``): the ``r79_sensor_screen.py`` jobs of set ``all`` (187 cases) x levels L3, L4 x the
default seeds 0..2, the same keys, case indices and noise seeds (H-4 ``case_seed``) as the stored
v3 runs, minus the cases the paper table leaves out:
  * S1 front patches (G6 ``S1@FL`` / ``S1@FR``, bearing-capacity failure region, spec 423.1);
  * pad type A reference runs (ref ``<soil>|A|0,0``, U-PAD-7, paper v4.4).
That leaves 167 cases x 3 seeds = 501 runs per level, 1002 in all. Every job goes through
``r79_sensor_screen.run_job`` unchanged (candidate ``current``, rod model ``dyn_map``,
``R72_PATH`` = ``per_leg``); this file only selects the jobs, records the controller settings
of every run and the worker peak working set, and checkpoints the results.

Judgement (``judge``): the new L3 / L4 runs against the final-controller L1 path references of
``fin_r79_merged.json`` (S-1 .. S-6 of ``r79_sensor_judge.judge_results``), failure counts per
level with the one-sided 95 % Clopper-Pearson upper bound (two paths: ``beta.ppf`` and the root
of ``binom.cdf(k, n, p) = 0.05``), acceptance upper bound <= 3 % (spec 423.1, Q-E rule), and the
verdict flips against the stored pre-R6 runs of ``r79_final_judgement_v3.json``.

Usage (repo root, dynamics-dev python):
  python -I 04_scripts/03_control/s8/r79_L3L4_final.py <project_root> list [--levels L3,L4]
  python -I 04_scripts/03_control/s8/r79_L3L4_final.py <project_root> run <out_json> [--workers N]
      [--levels L3,L4] [--keys "<plain key>;..." | --keys-file <stored run json | key list>]
      [--affinity 0x...]
    Results stream to ``<out_json>.partial.jsonl``; a re-start with the same out path skips
    the keys already there (resume). The final JSON is written when every job is done.
  python -I 04_scripts/03_control/s8/r79_L3L4_final.py <project_root> judge <out_json> <run_json> [<run_json> ...]
      [--reference <fin_r79_merged.json>] [--previous <r79_final_judgement_v3.json>]
"""

from __future__ import annotations

import os

# one BLAS thread per worker (the r79 runs are numpy-light; the pool gives the parallelism)
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("MKL_THREADING_LAYER", "TBB")

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from collections import Counter  # noqa: E402
from multiprocessing import Pool  # noqa: E402
from pathlib import Path  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
S8_DIR = ROOT / "04_scripts" / "03_control" / "s8"
if str(S8_DIR) not in sys.path:  # python -I does not put the script folder on sys.path
    sys.path.insert(0, str(S8_DIR))

import r79_sensor_screen as screen  # noqa: E402

REV79_DIR = ROOT / "06_analysis" / "02_control" / "s8" / "rev79"
DEFAULT_REFERENCE = REV79_DIR / "fin_r79_merged.json"
DEFAULT_PREVIOUS = REV79_DIR / "r79_final_judgement_v3.json"
C2_SOURCE = ROOT / "03_src" / "outrigger_sim" / "control" / "c2.py"
DEFAULT_LEVELS = ("L3", "L4")
CASE_SET = "all"
CANDIDATE = "current"
S1_FRONT_MARKERS = ("S1@FL", "S1@FR")
PAD_A_INNER = re.compile(r"(G1|J1|J2|S1)\|A\|.*")
"""Ref harness pad type A runs (``<soil>|A|0,0``), as figF10_sensor_grades.py."""
EXPECTED_RUNS_PER_LEVEL = 501
ACCEPT_UPPER = 0.03
CONFIDENCE = 0.95
FINAL_SETTINGS = {
    "lift_stroke_guard.enable": True,
    "lift_stroke_guard.soil_stop": True,
    "lift_stroke_guard.soil_stop_scope": "any_loc",
    "slope_clearance_margin.enable": True,
    "slope_clearance_margin.flat_soil_margin_m": 0.03,
    "loc_revoke.enable": True,
    "loc_revoke.soil_gate": True,
    "diff_sink.enable": True,
}
"""Final controller (spec 429.11): SGS any_loc, R4c30, L1gs, DSb75 must be on in every run."""
RECORDED_SETTINGS = (*FINAL_SETTINGS, "period_s", "soil.enable", "zero_calibration.mode",
                     "target.check_time_s", "target.gyro_noise_std_rad_s")


# --------------------------------------------------------------------------------------- jobs
def is_excluded(inner: str) -> bool:
    """Paper table rule: S1 front patch or pad type A reference run."""
    return any(m in inner for m in S1_FRONT_MARKERS) or PAD_A_INNER.fullmatch(inner) is not None


def plain_jobs(levels) -> list[str]:
    """r79 job keys (``L3|s0|g6|80|<inner>``) of the table rule, in the r79 order."""
    keys = screen.job_keys(CASE_SET, list(levels), None)
    return [k for k in keys if not is_excluded(screen.parse_job_key(k)[2].inner)]


def candidate_key(plain: str) -> str:
    return f"{screen.CANDIDATE_KEY_PREFIX}{CANDIDATE}{screen.CANDIDATE_KEY_SEPARATOR}{plain}"


def _dotted(config, name: str):
    value = config
    for part in name.split("."):
        value = getattr(value, part, None)
    if hasattr(value, "value"):  # enums
        value = value.value
    return value


def controller_settings(config) -> dict:
    return {name: _dotted(config, name) for name in RECORDED_SETTINGS}


def settings_mismatch(settings: dict | None) -> dict:
    if not settings:
        return {"missing": True}
    return {k: settings.get(k) for k, v in FINAL_SETTINGS.items()
            if not (settings.get(k) == v or (isinstance(v, float) and settings.get(k) is not None
                                              and abs(settings.get(k) - v) < 1e-12))}


def run_one(key: str) -> dict:
    """``r79_sensor_screen.run_job`` plus the settings of the controller the run used."""
    captured: dict = {}
    original = screen._rebuild_controller

    def rebuild(cl, c2, ctrl, level):
        rebuilt = original(cl, c2, ctrl, level)
        captured["settings"] = controller_settings(rebuilt.config)
        return rebuilt

    screen._rebuild_controller = rebuild
    try:
        record = screen.run_job(key)
    finally:
        screen._rebuild_controller = original
    record["controller_settings"] = captured.get("settings")
    try:
        import psutil

        info = psutil.Process().memory_info()
        record["worker_peak_wset_MB"] = round(getattr(info, "peak_wset", info.rss) / 2**20, 1)
    except Exception:  # memory record only
        record["worker_peak_wset_MB"] = None
    return record


def _git_head() -> str | None:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True,
                              text=True, timeout=30, check=True).stdout.strip()
    except Exception:
        return None


def _preset_settings() -> dict:
    from outrigger_sim.control.c2 import C2Config

    return controller_settings(C2Config().with_10hz_d1())


def _read_partial(path: Path) -> dict[str, dict]:
    done = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                done[rec["key"]] = rec
    return done


def read_keys_file(path: Path) -> list[str]:
    """Run keys of a stored r79 run JSON (``results[].key``, in file order) or of a text file
    (one key per line).

    Raises:
        SystemExit: A repeated key or no key.
    """
    text = Path(path).read_text(encoding="utf-8")
    if Path(path).suffix == ".json":
        keys = [str(row["key"]) for row in json.loads(text)["results"]]
    else:
        keys = [line.strip() for line in text.splitlines() if line.strip()]
    repeated = sorted(key for key, count in Counter(keys).items() if count > 1)
    if repeated:
        raise SystemExit(f"{path}: repeated keys {repeated[:5]}")
    if not keys:
        raise SystemExit(f"{path}: no key")
    return keys


def keys_file_problems(keys: list[str], levels: list[str]) -> list[str]:
    """Why keys of ``--keys-file`` are not jobs of this runner: the candidate must be
    ``current`` and the case (level, harness, index, case key) a table-rule job of ``levels``;
    the seed index may be any number >= 0 (436.8 rules rev1 RV1-3.2 seedext: seeds 0..24)."""
    cases = {_case_without_seed(plain) for plain in plain_jobs(levels)}
    problems = []
    for key in keys:
        candidate, plain = screen.split_candidate(key)
        if candidate not in (None, CANDIDATE):
            problems.append(f"{key}: candidate {candidate!r} is not {CANDIDATE!r}")
            continue
        try:
            _, seed_index, _ = screen.parse_job_key(plain)
        except (KeyError, ValueError) as exc:
            problems.append(f"{key}: not an r79 key ({exc!r})")
            continue
        if seed_index < 0 or _case_without_seed(plain) not in cases:
            problems.append(f"{key}: no table-rule case of levels {levels}")
    return problems


def _case_without_seed(plain: str) -> tuple[str, str, str, str]:
    level, _, harness, index, inner = plain.split("|", 4)
    return level, harness, index, inner


def cmd_run(args) -> None:
    levels = args.levels.split(",")
    keys = [candidate_key(k) for k in plain_jobs(levels)]
    if args.keys and args.keys_file:
        raise SystemExit("--keys and --keys-file exclude each other")
    if args.keys:
        wanted = [k for k in args.keys.split(";") if k]  # ";": ref keys hold a comma
        unknown = [k for k in wanted if candidate_key(k) not in keys]
        if unknown:
            raise SystemExit(f"keys not in the job list: {unknown}")
        keys = [candidate_key(k) for k in wanted]
    keys_file = None
    if args.keys_file:  # 436.8 rules rev1 RV1-3.2: the stored key list as it is (seedext)
        listed = read_keys_file(Path(args.keys_file))
        problems = keys_file_problems(listed, levels)
        if problems:
            raise SystemExit(f"--keys-file keys are no jobs of this runner: {problems[:5]}")
        keys = [candidate_key(screen.split_candidate(k)[1]) for k in listed]
        keys_file = {"path": str(args.keys_file), "n_keys": len(keys),
                     "sha256": hashlib.sha256(Path(args.keys_file).read_bytes()).hexdigest()}
    if args.affinity:
        os.environ["R79_AFFINITY"] = args.affinity
        screen.set_parent_placement()
    r72_path = screen.normalise_r72_path()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = out_path.with_name(out_path.name + ".partial.jsonl")
    done = _read_partial(partial_path)
    todo = [k for k in keys if k not in done]
    preset = _preset_settings()
    preset_mismatch = settings_mismatch(preset)
    print(f"jobs {len(keys)}, done {len(done)}, to run {len(todo)}, workers {args.workers}, "
          f"preset mismatch {preset_mismatch or 'none'}", flush=True)
    if preset_mismatch:
        raise SystemExit(f"with_10hz_d1() is not the final controller: {preset_mismatch}")
    t0 = time.perf_counter()
    if todo:
        with Pool(max(1, min(args.workers, len(todo)))) as pool, \
                partial_path.open("a", encoding="utf-8") as sink:
            for n, rec in enumerate(pool.imap_unordered(run_one, todo, chunksize=1), 1):
                sink.write(json.dumps(rec, default=float) + "\n")
                sink.flush()
                done[rec["key"]] = rec
                status = ("ERROR " + rec["error"]) if "error" in rec else (
                    f"pass {rec['base'].get('pass')} wall {rec.get('wall_s')}")
                print(f"[{n}/{len(todo)} {time.perf_counter() - t0:.0f} s] {rec['key']} {status}",
                      flush=True)
    results = [done[k] for k in keys]
    meta = {"script": "04_scripts/03_control/s8/r79_L3L4_final.py",
            "purpose": "r79 L3 / L4 with the final controller (user decision 2026-10-31)",
            "levels": ",".join(levels), "set": CASE_SET, "seeds": "default (L3 / L4: 0, 1, 2)",
            "excluded": "S1 front patches (S1@FL, S1@FR) and pad A reference runs",
            "candidate": CANDIDATE, "rod_model": os.environ.get("R79_ROD_MODEL",
                                                                screen.DEFAULT_ROD_MODEL),
            "r72_path": r72_path, "workers": args.workers, "affinity": args.affinity,
            "keys_option": bool(args.keys), "n_jobs": len(results),
            "n_errors": sum("error" in r for r in results),
            "wall_s_this_start": round(time.perf_counter() - t0, 1),
            "git_head": _git_head(),
            "c2_py_sha256": hashlib.sha256(C2_SOURCE.read_bytes()).hexdigest(),
            "preset_settings": preset}
    if keys_file is not None:  # a run without the option writes the former meta
        meta["seeds"] = "keys file"
        meta["keys_file"] = keys_file
    out_path.write_text(json.dumps({"meta": meta, "results": results}, indent=1, default=float),
                        encoding="utf-8")
    print("done", meta["wall_s_this_start"], "s ->", out_path, "errors", meta["n_errors"],
          flush=True)


# --------------------------------------------------------------------------------------- judge
def cp_upper_beta(k: int, n: int) -> float:
    from scipy.stats import beta

    return 1.0 if k >= n else float(beta.ppf(CONFIDENCE, k + 1, n - k))


def cp_upper_binom(k: int, n: int) -> float:
    """Independent path: the p with P(X <= k | n, p) = 1 - CONFIDENCE (brentq)."""
    from scipy.optimize import brentq
    from scipy.stats import binom

    if k >= n:
        return 1.0
    return float(brentq(lambda p: binom.cdf(k, n, p) - (1.0 - CONFIDENCE), 1e-15, 1 - 1e-15,
                        xtol=1e-15, rtol=1e-15, maxiter=500))


def _results(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["results"]


def _case_id(row: dict) -> tuple:
    return (row["level"], row["seed_index"], row["harness"], row["inner"])


def cmd_judge(args) -> None:
    import r79_sensor_judge as judge

    runs = [r for path in args.run_json for r in _results(Path(path))
            if r.get("level") in DEFAULT_LEVELS]
    keys = [r["key"] for r in runs]
    if len(keys) != len(set(keys)):
        raise SystemExit("a run key is in more than one run file")
    references =[r for r in _results(Path(args.reference)) if r.get("level") == "L1"]
    report = judge.judge_results(runs + references)
    judged = [row for row in report["runs"] if not is_excluded(row["inner"])]
    settings_bad = {r["key"]: settings_mismatch(r.get("controller_settings")) for r in runs
                    if "error" not in r and settings_mismatch(r.get("controller_settings"))}
    previous = {}
    if args.previous and Path(args.previous).exists():
        prev = json.loads(Path(args.previous).read_text(encoding="utf-8"))
        previous = {_case_id(r): r for r in prev["runs"] if r["level"] in DEFAULT_LEVELS}
    levels = {}
    for level in DEFAULT_LEVELS:
        rows = [r for r in judged if r["level"] == level]
        if not rows:
            continue
        k, n = sum(not r["pass"] for r in rows), len(rows)
        upper_beta, upper_binom = cp_upper_beta(k, n), cp_upper_binom(k, n)
        by_row = {name: sum(not r["rows"][name]["ok"] for r in rows)
                  for name in ("S-1", "S-2", "S-3", "S-4", "S-5", "S-6")}
        flips = {"pass_to_fail": [], "fail_to_pass": [], "no_previous": 0}
        for r in rows:
            old = previous.get(_case_id(r))
            if old is None:
                flips["no_previous"] += 1
            elif old["pass"] and not r["pass"]:
                flips["pass_to_fail"].append(r["key"])
            elif r["pass"] and not old["pass"]:
                flips["fail_to_pass"].append(r["key"])
        prev_rows = [previous[_case_id(r)] for r in rows if _case_id(r) in previous]
        levels[level] = {
            "runs": n, "failures": k, "rate": k / n, "cp95_upper": upper_beta,
            "cp95_upper_binom_root": upper_binom,
            "cp_paths_relerr": abs(upper_beta - upper_binom) / upper_beta if upper_beta else 0.0,
            "accepted_le_3pct": upper_beta <= ACCEPT_UPPER, "fail_rows": by_row,
            "expected_runs": EXPECTED_RUNS_PER_LEVEL,
            "previous_pre_R6": {"runs": len(prev_rows),
                                "failures": sum(not r["pass"] for r in prev_rows)},
            "flips_vs_pre_R6": flips,
            "failed_keys": [r["key"] for r in rows if not r["pass"]]}
    out = {"meta": {"script": "04_scripts/03_control/s8/r79_L3L4_final.py judge",
                    "run_json": [str(p) for p in args.run_json], "reference": str(args.reference),
                    "previous": str(args.previous),
                    "rule": "S-1 .. S-6 vs final-controller L1 (r79_sensor_judge); pad B, S1 front"
                            " excluded; one-sided 95 % Clopper-Pearson upper bound <= 3 %"},
           "levels": levels, "unmatched": report["unmatched"], "errors": report["errors"],
           "settings_mismatch": settings_bad, "table_all_groups": report["table"],
           "runs": judged}
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print("| level | runs | fail | rate | CP95 upper (beta / binom root) | <= 3 % | S-1..S-6 "
          "| pre-R6 fail/runs | pass->fail | fail->pass |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for level, e in levels.items():
        print(f"| {level} | {e['runs']} | {e['failures']} | {100 * e['rate']:.2f} % | "
              f"{100 * e['cp95_upper']:.3f} % / {100 * e['cp95_upper_binom_root']:.3f} % | "
              f"{e['accepted_le_3pct']} | {e['fail_rows']} | "
              f"{e['previous_pre_R6']['failures']}/{e['previous_pre_R6']['runs']} | "
              f"{len(e['flips_vs_pre_R6']['pass_to_fail'])} | "
              f"{len(e['flips_vs_pre_R6']['fail_to_pass'])} |")
    print("unmatched", len(report["unmatched"]), "errors", len(report["errors"]),
          "settings mismatch", len(settings_bad), "->", out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project_root", help="repo root; the r51 / r64 harness modules read "
                                             "sys.argv[1] as ROOT at import (workers too)")
    sub = parser.add_subparsers(dest="command", required=True)
    p_list = sub.add_parser("list")
    p_list.add_argument("--levels", default=",".join(DEFAULT_LEVELS))
    p_run = sub.add_parser("run")
    p_run.add_argument("out")
    p_run.add_argument("--workers", type=int, default=8)
    p_run.add_argument("--levels", default=",".join(DEFAULT_LEVELS))
    p_run.add_argument("--keys", default="")
    p_run.add_argument("--keys-file", default="",
                       help="run exactly the keys of a stored r79 run JSON (results[].key) or of "
                            "a text file (one key per line), any seed index (436.8 rules rev1 "
                            "RV1-3.2 seedext); each key runs through run_one unchanged")
    p_run.add_argument("--affinity", default="")
    p_judge = sub.add_parser("judge")
    p_judge.add_argument("out")
    p_judge.add_argument("run_json", nargs="+")
    p_judge.add_argument("--reference", default=str(DEFAULT_REFERENCE))
    p_judge.add_argument("--previous", default=str(DEFAULT_PREVIOUS))
    args = parser.parse_args()
    if Path(args.project_root).resolve() != ROOT:
        raise SystemExit(f"project_root {args.project_root} is not {ROOT}")
    if args.command == "list":
        jobs = plain_jobs(args.levels.split(","))
        for level in args.levels.split(","):
            print(level, sum(1 for j in jobs if j.startswith(level + "|")))
        print(len(jobs), "jobs")
    elif args.command == "run":
        cmd_run(args)
    else:
        cmd_judge(args)


if __name__ == "__main__":
    main()
