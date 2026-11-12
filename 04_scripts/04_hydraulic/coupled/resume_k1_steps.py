"""Steps and line counts of the 436.8 harness bundles (rules ``v5_resume_4368_rules.md`` 4.3, 5.1,
revised by ``v5_resume_4368_rules_rev1.md`` RV1-2 .. RV1-4, RV1-12).

Writes one steps file per bundle (the ``make_runner.py`` form ``{"steps": [{id, cwd, cmd, env}]}``,
every step with a ``resume_k1`` block: bundle, settings, expected tags of 4.1, output of 4.3 /
RV1-3.3, counted lines) and ``steps_h2.json`` (H-1 .. H-10 in one file, the name the rules give),
plus ``counts.json``: per bundle the line count of 5.1 / RV1-12, the count this module derives
from the job definitions and the stored key sources, and the stop flag S-15. Writes files only;
it never starts a run.

Commands are the stored ones (``sched_v5all`` / ``v5_r5rerun`` / ``las_t3`` usage) with the 436.8
output names: the runner scripts of the repository only, no wrapper, no preset keyword, no
candidate token (4.2). H-6 .. H-9 grid follow RV1-3: the key set of the stored file (sha256 of
appendix B checked here) and the repository runner; each r79 / r67 / r69 output gets an identity
step before and after it (``resume_k1_identity.py``). A bundle whose stored key source is missing
or has another sha256 is listed under ``blocked`` (S-1 handling of appendix B), not as steps.

Usage (python-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/resume_k1_steps.py <out_dir> [--root <checkout>]
      [--workers 24] [--mask 0x0FFFFFFF] [--data-root <folder with 06_analysis results>]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_v5  # noqa: E402
import u3_judge  # noqa: E402

DYNAMICS_PYTHON = r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B"
PYTHON_DEV = r"C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B"
V5 = "06_analysis/03_hydraulic/coupled/v5"
RESUME = f"{V5}/resume_k1"
LAS_K1 = "06_analysis/02_control/v5_rerun/las_k1"
RV85 = "06_analysis/02_control/s9/rev85"
RV84 = "06_analysis/02_control/s9/rev84"
FIX = "04_scripts/03_control/s9/s9_slope_fix_candidates.py"
B5 = "04_scripts/03_control/s9/b5_baseline_compare.py"
RUN_V5 = "04_scripts/04_hydraulic/coupled/run_v5.py"

TABLE_LINES = {
    "H-0": 360,
    "H-1": 868,
    "H-2": 1,
    "H-3": 2228,
    "H-4": 726 + 242,
    "H-5": 14,
    "H-6": 135,
    "H-7": 135,
    "H-8": 3106,
    "H-9": 812 + 96 + 768,
    "H-10": 388 + 28 + 12 + 12,
}
"""Rules 5.1 line counts with rev1 RV1-12 (H-4 = U-6 726 + IND_LAS record 242, H-9 = main 812 +
pressure_only 96 + grid ``runs[]`` 768, H-10 = 440: the 22 p3_hash jobs are main VB jobs, RV1-2)."""
MAIN_BUNDLES = ("H-1", "H-3", "H-4", "H-5", "H-6", "H-7", "H-8", "H-9", "H-10")
MAIN_TOTAL_LINES = 9570
"""Rev3 R3-F1: the main bundles (without H-0 and the one-line H-2 calculation) sum to 9,570
(the 9,800 / 9,778 of the original / rev1 were addition errors). A record only: S-15 compares
the bundle counts, never the sum."""
TAGS_V0_VB = {"V0": "final_C4G2_LAS_K1", "VB": "final_C4G2_P3_LAS_K1"}
U6_TAGS = {"C2": "final_C4G2_P3_LAS_K1", "ABL": "ABL_LAS_K1", "IND": "IND"}
FIX_SUITES = (
    ("slope", "harness", "finB2_harness", True),
    ("h9", "harness", "finB2_h9", True),
    ("h6", "harness", "finB2_harness", False),
    ("g6", "p0", "finB2_p0", False),
    ("g8", "p0", "finB2_p0", False),
    ("p3b", "p0", "finB2_p0", False),
    ("x426b", "harness", "finB2_x426b", False),
)
"""``sched_v5all/gen_steps.py`` suites: (suite, settle hook, ids file, ``--reuse-d1``)."""
MAIN_STAGE1_SETTINGS = ("V0", "V1", "V2", "V3", "L1", "L2", "V4", "V5", "V6", "V7", "V8")
"""H-9: the main batch without VB / LS1 .. LS4 (V0 .. V8, L1, L2)."""
MAIN_REUSE_SETTINGS = ("VB", "LS1", "LS2", "LS3", "LS4")
"""H-10: the main batch VB / LS1 .. LS4."""

R79 = "04_scripts/03_control/s8/r79_L3L4_final.py"
DG3 = "04_scripts/04_hydraulic/coupled/las_t3_dg3.py"
R67 = "04_scripts/03_control/s8/r67_g1_screen.py"
R69 = "04_scripts/03_control/s8/r69_g5_screen.py"
IDENTITY = "04_scripts/04_hydraulic/coupled/resume_k1_identity.py"
THREAD_ENV = {
    "MKL_THREADING_LAYER": "TBB",
    "MKL_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "NUMBA_NUM_THREADS": "1",
}
"""Rules 6: one BLAS thread per worker, TBB layer (record only; the r67 runner sets none itself)."""
R79_ENV = {"R72_PATH": "per_leg"}
STORED_SOURCES = {
    "dg3_v4_on": ("dg3/dg3_v4_on.json",
                  "5f912ca0d25d6dfe0114e05bf8c7a083fa542ad3de71e76c472e44a1a351167d"),
    "dg3_off": ("dg3/off/dg3_off.json",
                "95b81f82d800ae3ccf0dd15e205f12ec4b8795a1dcb482e6e30ed41aa0cfd5ce"),
    "noise_VB": ("noise_vb/r79_VB_L1L2L3.json",
                 "d3c9bba1abd3c1fbc700a26527856e14f7754740192c55a404bc203ef8a763b9"),
    "noise_V0": ("noise_v0/r79_V0_L1L2L3.json",
                 "af6a7ae51abe4b9094db9b21cf49f8770861fb0ed91cb269effb6b2cab9b459a"),
    "seedext_VB": ("seedext/r79_VB_seedext.json",
                   "6ddca3d5ce5dc6286c319de13d779bbb419df8fbee2bd13577d04b0f4c2d6f57"),
    "seedext_V0": ("seedext/r79_V0_seedext.json",
                   "f2c01d65238cac50da57c26ca33541b9506ff50b14aee80d65f31e1378dabaa8"),
    "grid_r67_main": ("grid_vb/grid_r67_main.json",
                      "8ef4237dc7658559efa04ac07edc1641fe422cbb55e5fee902fbac94eac13ef7"),
    "grid_r67_top": ("grid_vb/grid_r67_top.json",
                     "498aa41199b2e4ed3467573c061ab2d6a182ffcd10871fe9bc7420989e6e6412"),
    "grid_r69_bottom": ("grid_vb/grid_r69_bottom.json",
                        "ee84750be278a2c284bf1fe614155240c0a4c2b564762862276a007afc9609e9"),
    "grid_r69_top": ("grid_vb/grid_r69_top.json",
                     "c132fd41f13b8033b25804fbc777408a5d1729f31348af34aadd7fd6dfaad325"),
}
"""Rev1 appendix B: the H-6 .. H-9 key sources (file under ``v5/``, full sha256)."""
R79_CANDIDATE_PREFIX = "cand=current#"
"""``r79_L3L4_final.candidate_key`` prefix of every stored r79 key (``--keys`` takes plain keys)."""
GRID_EVENTS = ("G4", "RE1bF", "FS24")
"""``r67_g1_screen.EVENTS`` (every screen job runs each event at each offset)."""
GRID_LEVELS = ("top", "bottom")
GRID_TIMINGS = ("ready", "level")
GRID_LEGS = ("FL", "FR", "RL", "RR")
GRID_SETTING = "VB"
GRID_RUNS = {
    "grid_r67_main": {"script": R67, "fs_kN": (0.0, 8.0),
                      "env": {"R67_MODE": "screen", "R67_OFFSETS": "0,0.05"}},
    "grid_r67_top": {"script": R67, "fs_kN": (0.0, 8.0),
                     "env": {"R67_MODE": "screen", "R67_OFFSETS": "0,0.025,0.05,0.075",
                             "R67_FILTER": "screen|top|"}},
    "grid_r69_bottom": {"script": R69, "fs_kN": (2.0, 4.0),
                        "env": {"R69_FS": "2,4", "R67_OFFSETS": "0,0.025,0.05,0.075",
                                "R67_FILTER": "|bottom|"}},
    "grid_r69_top": {"script": R69, "fs_kN": (2.0, 4.0),
                     "env": {"R69_FS": "2,4", "R67_OFFSETS": "0,0.025,0.05,0.075",
                             "R67_FILTER": "|top|"}},
}
"""RV1-3.2 H-9 grid: runner (the ``script`` of the stored V0 pair provenance) and the ``R67_*`` /
``R69_FS`` env that rebuild the stored ``grid_vb`` meta (``offsets_s``, ``n_jobs``,
``candidate`` current, ``v5_setting`` VB). ``R67_CANDIDATE`` and ``R67_SLICE`` stay unset. The
F_s list mirrors ``r67_g1_screen.FS_KN`` (``r69_g5_screen`` replaces it with ``R69_FS``)."""
GRID_META_FIELDS = ("offsets_s", "n_jobs", "candidate", "v5_setting")


def _step(step_id: str, cmd: str, root: str, meta: dict, env: dict | None = None) -> dict:
    step = {"id": step_id, "cwd": root, "cmd": cmd, "resume_k1": meta}
    if env:
        step["env"] = env
    return step


def _meta(bundle: str, output: str, settings, tags, lines: int | None) -> dict:
    return {
        "bundle": bundle,
        "output": output,
        "settings": list(settings),
        "expected_tags": tags,
        "lines": lines,
    }


def h0_steps(root: str, workers: int, mask: str) -> list[dict]:
    """H-0 T-3K: ``las_t3.py run`` (rules rev5 default, output ``v5/las/t3_k1/``, ``las_targeted_rules_rev5`` 2.6)."""
    cmd = (
        f"{DYNAMICS_PYTHON} 04_scripts/04_hydraulic/coupled/las_t3.py run --workers {workers} "
        f"--affinity {mask}"
    )
    meta = _meta(
        "H-0",
        f"{V5}/las/t3_k1/",
        ("V0", "VB"),
        "las_targeted_rules_rev5 (T-3K)",
        TABLE_LINES["H-0"],
    )
    return [
        _step(
            "h0_t3k", cmd, root, {**meta, "lines_source": "rules 5.1 (las_t3.py list counts them)"}
        )
    ]


def run_v5_step(
    step_id: str,
    batch: str,
    out: str,
    settings,
    root: str,
    workers: int,
    mask: str,
    bundle: str,
    lines: int,
) -> dict:
    settings_arg = "" if settings is None else f" --settings {','.join(settings)}"
    cmd = f"{DYNAMICS_PYTHON} {RUN_V5} {batch} --workers {workers} --mask {mask} --out {out}{settings_arg}"
    shown = _settings_of(batch, settings)
    tags = {s: run_v5_tag(s) for s in shown}
    return _step(step_id, cmd, root, _meta(bundle, out, shown, tags, lines))


def _settings_of(batch: str, settings) -> tuple[str, ...]:
    """The settings a run_v5 step runs (d1: V0 / VB; p3_hash: VB, read from the stored main.jsonl at run time)."""
    if settings is not None:
        return tuple(settings)
    if batch == run_v5.D1_BATCH:
        return ("V0", "VB")
    if batch == run_v5.P3_HASH_BATCH:
        return ("VB",)
    return tuple(sorted({job["setting"] for job in run_v5.batch_jobs(batch)}))


def run_v5_tag(setting: str) -> str:
    """Rules 4.1: ③ settings (VB, LS1 .. LS4) ``final_C4G2_P3_LAS_K1``, the others ``final_C4G2_LAS_K1``."""
    return (
        TAGS_V0_VB["VB"]
        if run_v5.SETTINGS[setting][1].get("extend_start_tracked")
        else TAGS_V0_VB["V0"]
    )


def u3_steps(root: str, workers: int, mask: str) -> list[dict]:
    """H-3: the ``sched_v5all`` U-3 commands with the outputs in ``v5_rerun/las_k1/`` and the D-1 reuse input
    ``resume_k1/h1_d1.jsonl`` (rules 7.1 rev3 part)."""
    expected = {bundle.name: bundle.expected for bundle in u3_judge.BUNDLES}
    steps = []
    for setting in ("V0", "VB"):
        tags = {setting: TAGS_V0_VB[setting]}
        for suite, hook, ids, reuse in FIX_SUITES:
            out = f"{LAS_K1}/u3_{suite}_{setting}.json"
            cmd = (
                f"{DYNAMICS_PYTHON} {FIX} run --suite {suite} --settle-hook {hook} --v5-setting {setting} "
                f"--ids-from {RV85}/{ids}.json --pad B "
                + (f"--reuse-d1 {RESUME}/h1_d1.jsonl " if reuse else "")
                + f"--workers {workers} --affinity {mask} --out {out}"
            )
            steps.append(
                _step(
                    f"u3_{suite}_{setting}",
                    cmd,
                    root,
                    _meta("H-3", out, (setting,), tags, expected[suite]),
                )
            )
        out = f"{LAS_K1}/u3_C_{setting}.json"
        cmd = (
            f"{DYNAMICS_PYTHON} 04_scripts/03_control/s8/r72_g6_screen.py {root} {out} {workers} "
            f"--v5-setting {setting} --ids-from {RV85}/fin_x426_C.json --pad B"
        )
        env = {
            "R72_SET": "x426",
            "R72_PATH": "per_leg",
            "S9_SETTLE_HOOK": "p0",
            "R72_AFFINITY": mask,
        }
        steps.append(
            _step(
                f"u3_C_{setting}",
                cmd,
                root,
                _meta("H-3", out, (setting,), tags, expected["C"]),
                env,
            )
        )
        out = f"{LAS_K1}/u3_D_{setting}.json"
        cmd = (
            f"{DYNAMICS_PYTHON} 04_scripts/03_control/s9/s9_soil_slope.py --groups H8 --v5-setting {setting} "
            f"--ids-from {RV85}/fin_x426_D.json --pad B --workers {workers} --affinity {mask} --out {out}"
        )
        steps.append(
            _step(f"u3_D_{setting}", cmd, root, _meta("H-3", out, (setting,), tags, expected["D"]))
        )
    return steps


def u6_steps(root: str, workers: int, mask: str) -> list[dict]:
    """H-4: U-6 VB (C2, ABL, IND) and the IND_LAS record column (rules rev2 3), outputs in ``las_k1/``."""
    steps = []
    for label, cases_arg, ids, cases, pad, env in (
        ("wide", "wide --official", f"{RV84}/fin2_b5_wide_official.json", 226, "B", None),
        ("main", "all", f"{RV84}/fin_b5_main.json", 16, None, {"R72_PATH": "per_leg"}),
    ):
        pad_arg = f" --pad {pad}" if pad else ""
        for controllers, runs, tags in (
            ("C2,ABL,IND", 3 * cases, U6_TAGS),
            ("IND_LAS", cases, {"IND_LAS": "IND_LAS"}),
        ):
            suffix = "" if controllers != "IND_LAS" else "_IND_LAS"
            out = f"{LAS_K1}/u6_b5_{label}_VB{suffix}.json"
            cmd = (
                f"{DYNAMICS_PYTHON} {B5} run --cases {cases_arg} --controllers {controllers} --v5-setting VB "
                f"--ids-from {ids}{pad_arg} --workers {workers} --affinity {mask} --out {out}"
            )
            steps.append(
                _step(
                    f"u6_{label}_VB{suffix}", cmd, root, _meta("H-4", out, ("VB",), tags, runs), env
                )
            )
    return steps


class StoredSourceError(Exception):
    """A stored key source of appendix B is missing or has another sha256 (S-1 handling)."""


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stored_source(data_root: Path, name: str) -> tuple[str, dict]:
    """(repository-relative path, document) of a :data:`STORED_SOURCES` file.

    Raises:
        StoredSourceError: The file is missing or its sha256 is not the appendix B value.
    """
    relative, sha256 = STORED_SOURCES[name]
    path = Path(data_root) / V5 / relative
    if not path.is_file():
        raise StoredSourceError(f"{V5}/{relative} missing")
    actual = file_sha256(path)
    if actual != sha256:
        normalised = hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        if normalised != sha256:  # rev3 R3-F4: CRLF -> LF only is a pass, disclosed
            raise StoredSourceError(f"{V5}/{relative} sha256 {actual[:16]} != {sha256[:16]}")
        CRLF_ONLY_SOURCES[f"{V5}/{relative}"] = {"raw_sha256": actual,
                                                 "lf_normalised_sha256": normalised,
                                                 "note": "CRLF 변환만 다름"}
    return f"{V5}/{relative}", json.loads(path.read_text(encoding="utf-8"))


CRLF_ONLY_SOURCES: dict[str, dict] = {}
"""Stored key sources that matched appendix B only after CRLF -> LF (rev3 R3-F4)."""


def stored_r79_keys(document: dict) -> list[str]:
    return [str(row["key"]) for row in document["results"]]


def plain_r79_key(key: str) -> str:
    """The ``--keys`` form of a stored r79 key (``cand=current#`` removed).

    Raises:
        StoredSourceError: A key of another candidate (the runner runs ``current`` only).
    """
    if not key.startswith(R79_CANDIDATE_PREFIX):
        raise StoredSourceError(f"stored r79 key without {R79_CANDIDATE_PREFIX!r}: {key!r}")
    return key[len(R79_CANDIDATE_PREFIX):]


def r79_levels(keys: list[str]) -> tuple[str, ...]:
    """Levels of r79 keys in the order L1, L2, L3, L4."""
    levels = {plain_r79_key(key).split("|", 1)[0] for key in keys}
    return tuple(sorted(levels))


def identity_steps(step_id: str, run_step: dict, root: str) -> list[dict]:
    """RV1-3.1: the ``.identity.json`` record before and after an r79 / r67 / r69 run."""
    output = run_step["resume_k1"]["output"]
    steps = []
    for moment in ("start", "end"):
        cmd = f"{DYNAMICS_PYTHON} {IDENTITY} {output} --moment {moment}"
        meta = {**run_step["resume_k1"], "lines": 0, "identity_of": run_step["id"]}
        steps.append(_step(f"{step_id}_identity_{moment}", cmd, root, meta))
    return [steps[0], run_step, steps[1]]


def dg3_steps(root: str, workers: int, mask: str, data_root: Path) -> dict[str, list[dict]]:
    """H-6 (③ on) and H-7 (③ off) by ``las_t3_dg3.py`` with the 135 stored dg3 keys (RV1-3.2).

    Raises:
        StoredSourceError: A key source fails :func:`stored_source`, the two key sets differ, or
            the levels are not L2, L3.
    """
    _, on_doc = stored_source(data_root, "dg3_v4_on")
    _, off_doc = stored_source(data_root, "dg3_off")
    keys = stored_r79_keys(on_doc)
    if set(keys) != set(stored_r79_keys(off_doc)):
        raise StoredSourceError("dg3 v4_on and off key sets differ (RV1-3.2: H-7 = H-6 keys)")
    levels = r79_levels(keys)
    if levels != ("L2", "L3"):
        raise StoredSourceError(f"dg3 keys of levels {levels}, L2, L3 expected")
    plain = ";".join(plain_r79_key(key) for key in keys)
    bundles = {}
    for bundle, name, p3, tag in (("H-6", "h6_dg3_v4on", "on", TAGS_V0_VB["VB"]),
                                  ("H-7", "h7_dg3_off", "off", TAGS_V0_VB["V0"])):
        out = f"{RESUME}/{name}.json"
        env = {**THREAD_ENV, **R79_ENV, "R79_V5_SETTING": "VB",
               "R79_T4H_DIR": f"{RESUME}/{name}_t4h",
               "LAS_T3_DG3_LAS": "on", "LAS_T3_DG3_K1": "on", "LAS_T3_DG3_P3": p3}
        cmd = (f"{DYNAMICS_PYTHON} {DG3} {root} run {out} --levels {','.join(levels)} "
               f'--keys "{plain}" --workers {workers} --affinity {mask}')
        meta = _meta(bundle, out, ("VB",), {"VB": tag}, len(keys))
        meta["key_source"] = STORED_SOURCES["dg3_v4_on" if p3 == "on" else "dg3_off"][0]
        step = _step(f"{name}", cmd, root, meta, env)
        bundles[bundle] = identity_steps(name, step, root)
    return bundles


def noise_steps(root: str, workers: int, mask: str, data_root: Path) -> list[dict]:
    """H-8: the noise VB / V0 runs (default job list of L1, L2, L3) and seedext VB / V0 (the
    stored key file through ``--keys-file``), RV1-3.2 / RV1-3.3.

    Raises:
        StoredSourceError: A key source fails :func:`stored_source`, or the VB / V0 key sets of
            a pair differ.
    """
    steps = []
    for kind, levels_arg in (("noise", "L1,L2,L3"), ("seedext", None)):
        key_sets = {}
        for setting in ("VB", "V0"):
            relative, document = stored_source(data_root, f"{kind}_{setting}")
            keys = stored_r79_keys(document)
            key_sets[setting] = set(keys)
            levels = ",".join(r79_levels(keys))
            if levels_arg is not None and levels != levels_arg:
                raise StoredSourceError(f"{relative}: levels {levels}, {levels_arg} expected")
            out = f"{RESUME}/h8_{kind}_{setting}.json"
            keys_arg = "" if kind == "noise" else f" --keys-file {relative}"
            cmd = (f"{DYNAMICS_PYTHON} {R79} {root} run {out} --levels {levels}{keys_arg} "
                   f"--workers {workers} --affinity {mask}")
            env = {**THREAD_ENV, **R79_ENV, "R79_V5_SETTING": setting}
            meta = _meta("H-8", out, (setting,), {setting: TAGS_V0_VB[setting]}, len(keys))
            meta["key_source"] = relative
            step_id = f"h8_{kind}_{setting}"
            steps += identity_steps(step_id, _step(step_id, cmd, root, meta, env), root)
        if key_sets["VB"] != key_sets["V0"]:
            raise StoredSourceError(f"{kind}: VB and V0 key sets differ (RV1-3.2)")
    return steps


def grid_expected_keys(name: str) -> list[str]:
    """Screen job keys the grid run :data:`GRID_RUNS` ``name`` makes (``r67_g1_screen.all_jobs``
    of mode screen with the F_s list, then the ``R67_FILTER`` substrings), sorted like the runner
    (LEVEL screens first, then by key)."""
    spec = GRID_RUNS[name]
    jobs = [f"screen|{level}|{fs}|{timing}|{leg}" for level in GRID_LEVELS
            for fs in spec["fs_kN"] for timing in GRID_TIMINGS for leg in GRID_LEGS]
    substrings = spec["env"].get("R67_FILTER")
    if substrings:
        jobs = [job for job in jobs if any(part in job for part in substrings.split(","))]
    return sorted(jobs, key=lambda key: (0 if "|level|" in key else 1, key))


def grid_expected_meta(name: str) -> dict:
    """The stored-meta fields (:data:`GRID_META_FIELDS`) the grid run ``name`` writes."""
    spec = GRID_RUNS[name]
    return {"offsets_s": spec["env"]["R67_OFFSETS"], "n_jobs": len(grid_expected_keys(name)),
            "candidate": "current", "v5_setting": GRID_SETTING}


def grid_expected_runs(name: str) -> int:
    offsets = GRID_RUNS[name]["env"]["R67_OFFSETS"].split(",")
    return len(grid_expected_keys(name)) * len(GRID_EVENTS) * len(offsets)


def grid_source_problems(name: str, document: dict) -> list[str]:
    """Differences of the stored grid file from what :data:`GRID_RUNS` ``name`` rebuilds: key
    set, meta fields, ``runs[]`` count (RV1-3.2 H-9: S-15 before any run)."""
    problems = []
    stored_keys = [row["key"] for row in document["results"]]
    if set(stored_keys) != set(grid_expected_keys(name)):
        problems.append(f"key set differs: stored {len(stored_keys)}, rebuilt "
                        f"{len(grid_expected_keys(name))}")
    meta = document.get("meta") or {}
    for field, want in grid_expected_meta(name).items():
        if meta.get(field) != want:
            problems.append(f"meta {field} stored {meta.get(field)!r} != rebuilt {want!r}")
    runs = sum(len(row.get("runs") or []) for row in document["results"])
    if runs != grid_expected_runs(name):
        problems.append(f"runs stored {runs} != rebuilt {grid_expected_runs(name)}")
    return problems


def grid_steps(root: str, workers: int, mask: str, data_root: Path) -> list[dict]:
    """H-9 grid: the four ``grid_vb`` runs under ``h9_grid/`` (RV1-3.2 / RV1-3.3).

    Raises:
        StoredSourceError: A key source fails :func:`stored_source` or
            :func:`grid_source_problems`.
    """
    steps = []
    for name, spec in GRID_RUNS.items():
        relative, document = stored_source(data_root, name)
        problems = grid_source_problems(name, document)
        if problems:
            raise StoredSourceError(f"{relative}: {problems}")
        out = f"{RESUME}/h9_grid/{name}.json"
        env = {**THREAD_ENV, **spec["env"], "R67_V5_SETTING": GRID_SETTING, "R67_AFFINITY": mask}
        cmd = f"{DYNAMICS_PYTHON} {spec['script']} {root} {out} {workers}"
        meta = _meta("H-9", out, (GRID_SETTING,), {GRID_SETTING: TAGS_V0_VB["VB"]},
                     grid_expected_runs(name))
        meta.update(key_source=relative, lines_source="runs[] (RV1-3.2)",
                    expected_meta=grid_expected_meta(name),
                    unset_env=["R67_CANDIDATE", "R67_SLICE"])
        steps += identity_steps(f"h9_{name}", _step(f"h9_{name}", cmd, root, meta, env), root)
    return steps


GRID_V0_STORED = "06_analysis/02_control/touch_phase/acceptance/c4g2_only/grid"
"""v5 criteria 10: the stored V0 grid (``acceptance/c4g2_only/grid``, old V0 controller)."""
GRID_V0_SETTING = "V0"
GRID_V0_SAMPLE_DIR = f"{RESUME}/h9_grid_v0_sample"
GRID_V0_DIR = f"{RESUME}/h9_grid_v0"
FAMILY_F_KEYS = ("screen|top|0.0|ready|FR", "screen|top|0.0|ready|FL")
FAMILY_F_EVENT = "FS24"
FAMILY_F_PHASES = 16
FAMILY_F_STEP_S = 0.00625
FAMILY_F_OFFSETS = ",".join(f"{i * FAMILY_F_STEP_S:g}" for i in range(FAMILY_F_PHASES))
"""v5 criteria rev5 5.2: phases 0, 0.00625, ..., 0.09375 s."""
FAMILY_F_OUT = f"{RESUME}/h9_family_F.jsonl"
FAMILY_F_COLLECT = "04_scripts/04_hydraulic/coupled/resume_k1_family_f.py"
FAMILY_F_LINES = len(FAMILY_F_KEYS) * FAMILY_F_PHASES * 2


def grid_v0_sample_keys(data_root: Path) -> dict[str, list[str]]:
    """Rev3 R3-E1 (the original names no jobs): per stored V0 grid file the first and the last
    result key in result order; the first run of each is compared (8 jobs, fixed before results).

    Raises:
        StoredSourceError: A stored V0 grid file is missing.
    """
    keys = {}
    for name in GRID_RUNS:
        path = Path(data_root) / GRID_V0_STORED / f"{name}.json"
        if not path.is_file():
            raise StoredSourceError(f"{GRID_V0_STORED}/{name}.json missing")
        results = json.loads(path.read_text(encoding="utf-8"))["results"]
        keys[name] = [results[0]["key"], results[-1]["key"]]
    return keys


def _grid_run_step(step_id: str, name: str, out: str, setting: str, root: str, workers: int,
                   mask: str, lines: int, extra_env: dict | None = None,
                   keys: list[str] | None = None) -> dict:
    spec = GRID_RUNS[name]
    env = {**THREAD_ENV, **spec["env"], **(extra_env or {}), "R67_V5_SETTING": setting,
           "R67_AFFINITY": mask}
    keys_arg = "" if keys is None else f' --keys "{",".join(keys)}"'
    cmd = f"{DYNAMICS_PYTHON} {spec['script']} {root} {out} {workers}{keys_arg}"
    tag = TAGS_V0_VB["VB" if setting == "VB" else "V0"]
    meta = _meta("H-9", out, (setting,), {setting: tag}, lines)
    meta["unset_env"] = ["R67_CANDIDATE", "R67_SLICE"]
    return _step(step_id, cmd, root, meta, env)


def grid_v0_sample_steps(root: str, workers: int, mask: str, data_root: Path) -> list[dict]:
    """R3-E1 step 1: the 8-job V0 sample (always), outputs under ``h9_grid_v0_sample/``."""
    steps = []
    for name, keys in grid_v0_sample_keys(data_root).items():
        out = f"{GRID_V0_SAMPLE_DIR}/{name}.json"
        step = _grid_run_step(f"h9_v0_sample_{name}", name, out, GRID_V0_SETTING, root, workers,
                              mask, 0, keys=keys)
        step["resume_k1"].update(sample_of=f"{GRID_V0_STORED}/{name}.json", sample_keys=keys,
                                 compared="every run of each key by (event, offset) (R4-B4)")
        steps += identity_steps(step["id"], step, root)
    return steps


def grid_v0_full_steps(root: str, workers: int, mask: str) -> list[dict]:
    """R3-E1 step 3 (conditional: a sample hash differs): V0 768 under ``h9_grid_v0/``."""
    steps = []
    for name in GRID_RUNS:
        out = f"{GRID_V0_DIR}/{name}.json"
        step = _grid_run_step(f"h9_v0_{name}", name, out, GRID_V0_SETTING, root, workers, mask,
                              grid_expected_runs(name))
        step["resume_k1"]["condition"] = "grid-v0-sample: a sample hash differs (R3-E1)"
        steps += identity_steps(step["id"], step, root)
    return steps


def family_f_steps(root: str, workers: int, mask: str) -> list[dict]:
    """R3-E2 (conditional: a family F pass -> fail by Fmin_after_W / U57_outside only): the
    rev5 5.2 runs, 2 keys x 16 phases x V0 / VB (r67 runs every event; the FS24 runs are the 64
    lines), collected into ``h9_family_F.jsonl``."""
    steps, outputs = [], []
    for setting in (GRID_V0_SETTING, "VB"):
        out = f"{RESUME}/h9_family_F_{setting}.json"
        outputs.append(out)
        step = _grid_run_step(f"h9_family_F_{setting}", "grid_r67_main", out, setting, root,
                              workers, mask, 0, extra_env={"R67_OFFSETS": FAMILY_F_OFFSETS},
                              keys=list(FAMILY_F_KEYS))
        step["resume_k1"]["condition"] = "family-f-trigger: a family F pass -> fail (R3-E2)"
        steps += identity_steps(step["id"], step, root)
    cmd = (f"{PYTHON_DEV} {FAMILY_F_COLLECT} {outputs[0]} {outputs[1]} --event {FAMILY_F_EVENT} "
           f"--out {FAMILY_F_OUT}")
    meta = _meta("H-9", FAMILY_F_OUT, (GRID_V0_SETTING, "VB"), TAGS_V0_VB, FAMILY_F_LINES)
    meta["condition"] = "family-f-trigger: a family F pass -> fail (R3-E2)"
    steps.append(_step("h9_family_F_collect", cmd, root, meta))
    return steps


def conditional_counts() -> dict:
    """R3-E1 / R3-E2: the conditional runs S-15 adds to H-9 when their condition holds."""
    return {
        "H-9 grid V0 sample": {"jobs_compared": 2 * len(GRID_RUNS), "condition": "always",
                               "lines": 0, "note": "output h9_grid_v0_sample/, no H-9 line"},
        "H-9 grid V0 768": {"lines": sum(grid_expected_runs(name) for name in GRID_RUNS),
                            "condition": "grid-v0-sample: a sample hash differs"},
        "H-9 family F": {"lines": FAMILY_F_LINES,
                         "condition": "family-f-trigger: a pass -> fail by Fmin_after_W / "
                                      "U57_outside only"},
        "rule": "H-9 S-15 value = 1,676 + the lines of the conditional runs that ran (R3-E1/E2)",
    }


def stored_main_path(data_root: Path) -> Path:
    return data_root / V5 / "main.jsonl"


def h10_counts(data_root: Path) -> dict:
    """H-10 jobs per part (RV1-2: main VB / LS1 .. LS4, U-9 VB, item8, overlap = 440, no p3_hash
    run) and the check that every p3_hash job of the stored ``main.jsonl`` is a main VB job
    (same ``run_v5.job_key``; 22/22 on 2026-11-13)."""
    parts = {
        "main": run_v5.select_settings(run_v5.batch_jobs("main"), MAIN_REUSE_SETTINGS),
        "u9_targeted": run_v5.select_settings(run_v5.u9_targeted_jobs(), ("VB",)),
        "item8": run_v5.batch_jobs("item8"),
        "overlap": run_v5.batch_jobs("overlap"),
    }
    keys = {run_v5.job_key(job) for jobs in parts.values() for job in jobs}
    out = {
        "jobs": {name: len(jobs) for name, jobs in parts.items()},
        "jobs_total": sum(len(jobs) for jobs in parts.values()),
        "distinct_keys": len(keys),
        "p3_hash": "not run (RV1-2: the main VB lines are those jobs)",
    }
    main_path = stored_main_path(data_root)
    if not main_path.is_file():
        out["p3_hash_in_main_vb"] = "main.jsonl missing (not checked)"
        return out
    main_vb = {run_v5.job_key(job) for job in parts["main"] if job["setting"] == "VB"}
    p3_keys = [run_v5.job_key(job) for _, job in run_v5.p3_hash_jobs(main_path)]
    out["p3_hash_in_main_vb"] = f"{sum(key in main_vb for key in p3_keys)}/{len(p3_keys)}"
    out["p3_hash_all_in_main_vb"] = all(key in main_vb for key in p3_keys)
    return out


def build(args: argparse.Namespace) -> dict:
    root, w, m = args.root, args.workers, args.mask
    d1_lines = _d1_count()
    h1 = [run_v5_step("h1_d1", "d1", f"{RESUME}/h1_d1.jsonl", None, root, w, m, "H-1", d1_lines)]
    h2 = [
        _step(
            "h2_d1_select",
            f"{PYTHON_DEV} 04_scripts/04_hydraulic/coupled/d1_select.py "
            f"{RESUME}/h2_d1_select.json {RESUME}/h1_d1.jsonl",
            root,
            _meta("H-2", f"{RESUME}/h2_d1_select.json", (), None, 1),
        )
    ]
    u9_v0 = len(run_v5.select_settings(run_v5.u9_targeted_jobs(), ("V0",)))
    h5 = [
        run_v5_step(
            "h5_u9_v0", "u9_targeted", f"{RESUME}/h5_u9_v0.jsonl", ("V0",), root, w, m, "H-5", u9_v0
        )
    ]
    main9 = len(run_v5.select_settings(run_v5.batch_jobs("main"), MAIN_STAGE1_SETTINGS))
    h9 = [
        run_v5_step(
            "h9_main",
            "main",
            f"{RESUME}/h9_stage1.jsonl",
            MAIN_STAGE1_SETTINGS,
            root,
            w,
            m,
            "H-9",
            main9,
        ),
        run_v5_step(
            "h9_pressure_only",
            "pressure_only",
            f"{RESUME}/h9_stage1.jsonl",
            None,
            root,
            w,
            m,
            "H-9",
            len(run_v5.batch_jobs("pressure_only")),
        ),
    ]
    data_root = Path(args.data_root)
    bundles = {
        "H-0": h0_steps(root, w, m),
        "H-1": h1,
        "H-2": h2,
        "H-3": u3_steps(root, w, m),
        "H-4": u6_steps(root, w, m),
        "H-5": h5,
    }
    blocked = {}
    try:
        bundles.update(dg3_steps(root, w, m, data_root))
    except StoredSourceError as exc:
        blocked["H-6"] = blocked["H-7"] = str(exc)
    try:
        bundles["H-8"] = noise_steps(root, w, m, data_root)
    except StoredSourceError as exc:
        blocked["H-8"] = str(exc)
    try:
        h9 += grid_steps(root, w, m, data_root)
    except StoredSourceError as exc:
        blocked["H-9 grid"] = str(exc)
    bundles["H-9"] = h9
    bundles["H-10"] = h10_steps(root, w, m)
    try:
        bundles["H-9 V0 sample"] = grid_v0_sample_steps(root, w, m, data_root)
    except StoredSourceError as exc:
        blocked["H-9 V0 sample"] = str(exc)
    counts = counts_report(bundles, d1_lines, main9, data_root, blocked)
    counts["conditional"] = conditional_counts()
    if CRLF_ONLY_SOURCES:
        counts["appendix_b_crlf_only"] = dict(CRLF_ONLY_SOURCES)
    return {
        "bundles": bundles,
        "conditional": {"H-9 grid V0 768": grid_v0_full_steps(root, w, m),
                        "H-9 family F": family_f_steps(root, w, m)},
        "blocked": blocked,
        "counts": counts,
    }


H10_OUT = f"{RESUME}/h10_reuse_rerun.jsonl"
H10_OVERLAP_REFERENCE = f"{RESUME}/h10_overlap_t_a.json"
"""RV1-4: the t_a of the new VB reference run (the stored ``v5/overlap_t_a.json`` is not read)."""


def h10_steps(root: str, workers: int, mask: str) -> list[dict]:
    """H-10 (RV1-2: no p3_hash step) with the overlap reference path of RV1-4."""
    steps = [
        run_v5_step("h10_main", "main", H10_OUT, MAIN_REUSE_SETTINGS, root, workers, mask, "H-10",
                    len(run_v5.select_settings(run_v5.batch_jobs("main"), MAIN_REUSE_SETTINGS))),
        run_v5_step("h10_u9_vb", "u9_targeted", H10_OUT, ("VB",), root, workers, mask, "H-10",
                    len(run_v5.select_settings(run_v5.u9_targeted_jobs(), ("VB",)))),
        run_v5_step("h10_item8", "item8", H10_OUT, None, root, workers, mask, "H-10",
                    len(run_v5.batch_jobs("item8"))),
        run_v5_step("h10_overlap", "overlap", H10_OUT, None, root, workers, mask, "H-10",
                    len(run_v5.batch_jobs("overlap"))),
    ]
    overlap = steps[-1]
    overlap["cmd"] += f" --overlap-reference {H10_OVERLAP_REFERENCE}"
    overlap["resume_k1"]["overlap_reference"] = H10_OVERLAP_REFERENCE
    return steps


def _d1_count() -> int | None:
    """H-1 jobs from ``d1_rows.jobs()`` (None when the module does not import in this interpreter)."""
    try:
        import d1_rows  # noqa: PLC0415
    except ImportError:
        return None
    return len(d1_rows.jobs())


def counts_report(bundles: dict, d1_lines: int | None, main9: int, data_root: Path,
                  blocked: dict[str, str]) -> dict:
    """Rules 5.1 / RV1-12 / S-15: per bundle the table count, the derived count and whether they
    differ, and the same for the main total (RV1-2 9,778)."""
    derived: dict[str, int | None] = {}
    for name, steps in bundles.items():
        lines = [step["resume_k1"]["lines"] for step in steps]
        derived[name] = None if any(v is None for v in lines) else sum(lines)
    if "H-9 grid" in blocked:
        derived["H-9"] = None
    h10 = h10_counts(data_root)
    if h10["jobs_total"] != h10["distinct_keys"] or derived.get("H-10") != h10["jobs_total"]:
        derived["H-10"] = None  # a repeated job key or steps that do not run the counted jobs
    out = {}
    for name, table in TABLE_LINES.items():
        value = derived.get(name)
        out[name] = {
            "table": table,
            "derived": value,
            "differs_S15": None if value is None else value != table,
        }
    grid = {name: grid_expected_runs(name) for name in GRID_RUNS}
    out["H-9"]["parts"] = {
        "main V0..V8 L1 L2": main9,
        "pressure_only": len(run_v5.batch_jobs("pressure_only")),
        "grid runs[]": "blocked" if "H-9 grid" in blocked else grid,
    }
    out["H-10"]["parts"] = h10
    out["H-1"]["source"] = (
        "d1_rows.jobs()" if d1_lines is not None else "d1_rows not importable here"
    )
    out["main_total"] = main_total_report(out)
    return out


def main_total_report(counts: dict) -> dict:
    """Rev3 R3-F1: the sum of the main bundles (table and derived), a record (no S-15)."""
    table_sum = sum(TABLE_LINES[name] for name in MAIN_BUNDLES)
    values = [counts[name]["derived"] for name in MAIN_BUNDLES]
    derived_sum = None if any(value is None for value in values) else sum(values)
    return {
        "rules_value": MAIN_TOTAL_LINES,
        "table_sum": table_sum,
        "derived": derived_sum,
        "record_only": "R3-F1: S-15 compares the bundle counts only",
        "differs_S15": None,
    }


def _file_token(name: str) -> str:
    """``H-9 V0 sample`` -> ``h9_v0_sample``."""
    return name.replace("-", "").replace(" ", "_").lower()


def write(out_dir: Path, built: dict) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    harness = [step for name, steps in built["bundles"].items() if name != "H-0" for step in steps]
    for name, steps in built["bundles"].items():
        path = out_dir / f"steps_bundle_{_file_token(name)}.json"  # not steps_h2.json (all)
        path.write_text(json.dumps({"steps": steps}, indent=1), encoding="utf-8")
        files[name] = str(path)
    for name, steps in built.get("conditional", {}).items():  # R3-E1 / R3-E2, not in steps_h2
        path = out_dir / f"steps_conditional_{_file_token(name)}.json"
        path.write_text(json.dumps({"steps": steps}, indent=1), encoding="utf-8")
        files[f"conditional {name}"] = str(path)
    (out_dir / "steps_h2.json").write_text(
        json.dumps({"steps": harness}, indent=1), encoding="utf-8"
    )
    report = {
        "counts": built["counts"],
        "blocked": built["blocked"],
        "files": files,
        "steps_h2": str(out_dir / "steps_h2.json"),
    }
    (out_dir / "counts.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out_dir", type=Path)
    parser.add_argument(
        "--root", default=r"C:\workspace\outrigger_control", help="checkout the steps run in"
    )
    parser.add_argument(
        "--data-root", default=str(ROOT), help="folder holding the stored v5/main.jsonl"
    )
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--mask", default="0x0FFFFFFF")
    args = parser.parse_args(argv)
    report = write(args.out_dir, build(args))
    differs = [n for n, c in report["counts"].items()
               if isinstance(c, dict) and c.get("differs_S15")]
    blocked = sorted(report["blocked"])
    print(json.dumps({"differs_S15": differs, "blocked": blocked, "steps_h2": report["steps_h2"]}))
    return 1 if differs or blocked else 0


if __name__ == "__main__":
    sys.exit(main())
