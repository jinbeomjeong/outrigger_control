"""LAS-b P5r4 + K1 re-judgement on the reduced harness: bundles Z-0 .. Z-X (run tool).

Rules: the sealed new original ``06_analysis/02_control/verif_matrix/las_p5r4_k1_rules.md``
(control-expert, LF sha256 ``las_p5r4k1_judge.RULES_SHA256``) and the ten rules files of its
section 0 table (all checked before anything runs, S-1). The rules text wins where this code
differs; section numbers in the comments are the rules'.

Arms (rules 2): ``ref`` = P0+K1, the preset ``C2Config().with_10hz_d1()`` as it is (LAS-b b0, the
R4c30 order gate on); ``cand`` = P5r4+K1, the same with one ``dataclasses.replace`` of
``liftoff_approach_slow`` (``light_leg_fraction_of_F_min=4.5``, ``end_ramp_periods=4``), applied
by this tool's own ``C2Controller.__init__`` wrapper in the worker on a config whose LAS-b is
the b0 preset (one already at P5r4 is kept, LAS-b off is kept, anything else raises). No K1
token, no ``--las-off``, no K-2 ``_TCL`` path, no older candidate wrapper, no sealed batch
runner (rules 2, 11.1, 16.1 O-1). Both arms carry the preset tags (VB ``final_C4G2_P3_LAS_K1``,
V0 ``final_C4G2_LAS_K1``); the arm is the ``las_candidate`` field.

Bundles (rules 4.2), output ``<v5>/las/p5r4k1/p5k_<bundle>.jsonl`` (opened with ``"x"``):
  Z-0  6 ref lines, the A-plan R-0 jobs (two with the TOUCH budget LT c1 j0)
  Z-A  102 cand lines, the A-plan R-0A (54) and R-Q (48) grid points (record on)
  Z-T  192 keys x ref, cand     Z-S  30 jobs x ref, cand     Z-C  456 S-C keys x ref, cand
  Z-X  ref + DONE record on the C-4 exception-claim keys (from the judge on the run folder)
Reused (job builders and record hooks only): ``las_rev_targeted`` (R-0 / T / S jobs, DONE
recorder), ``las_revA_targeted`` (grid jobs, the ``las`` block with the ramp),
``las_phase_diag`` (grid budget and period record), ``k1_targeted`` (the LOC witness of
``_apply_slope_clearance_margin``), ``s2_defer_targeted`` (S-C jobs), ``fb_targeted`` (thread
variables, preset LAS-b check, run capture, run identity).

Gates before a run (exit 2): seals; the stored files (raw sha256) and every key list
recomputed = appendix A; the preset (b0, gate on, N_r 0, touch creep latch off); the run
identity (empty code diff, only this work's tests dirty, one thread); job dicts = the stored
lines'; order (Z-A after a passing BT-0, Z-T / Z-S / Z-C after BT-0 and BT-A, Z-X after the
three pair bundles) with every earlier line from the current commit and tool sha256.
During a batch: a run identity change, a tag (K-3), gate (K-4) or LAS-b setting (K-5) problem
stops it; an error line runs once more (``rev.attempt`` 2), a second error is kept and the
batch goes on (the judge makes the key ``incomplete``, 10.1); five pairs with a C-2 type
violation stop the bundle (S-5). Every run line on stdout is ``n/total id unit: done|ERROR``
(no values, 16.2). The batch ends with the plain text line ``errors N`` (N = error lines,
first attempts included, 16.3) and exits non-zero when N > 0.

G-S (16.2): ``run --bundle <Z> --gs-list <list.json>`` runs the list's lines of that bundle
into ``<v5>/las/p5r4k1/gs/p5k_GS_<bundle>.jsonl`` (``p5k.gs`` true; no order gate). The list
comes from ``las_p5r4k1_gs.py list``; ``las_p5r4k1_gs.py check`` checks the lines.

Usage (dynamics-dev python.exe, project root, PowerShell):
  python -I -B 04_scripts/04_hydraulic/coupled/las_p5r4k1_targeted.py list [--v5-dir <v5>]
  python -I -B 04_scripts/04_hydraulic/coupled/las_p5r4k1_targeted.py run --bundle Z-0
      [--v5-dir <v5>] [--workers 4] [--affinity HEX] [--resume] [--gs-list <json>]
      [--trial-out <jsonl> [--keys U1,U2] [--limit N]]
Exit codes: 0 done, 1 a batch stop or error lines (run) / a count or reference mismatch (list),
2 input error (seals, stored files, lists, gates, identity, job dicts, existing output).
"""
from __future__ import annotations

import argparse
import json
import queue
import subprocess
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field, replace
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
JUDGE_DIR = HERE.parents[2] / "06_analysis" / "02_control" / "verif_matrix" / "scripts"
for _path in (HERE, JUDGE_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import fb_targeted as fb  # noqa: E402  (sets the thread variables before numpy loads)
import las_p5r4k1_judge as pj  # noqa: E402  (standard library only)

ROOT = fb.ROOT
TOOL_NAME = "las_p5r4k1_targeted.py"
IDENTITY_FILES = {
    TOOL_NAME: HERE / TOOL_NAME,
    "las_p5r4k1_judge.py": JUDGE_DIR / "las_p5r4k1_judge.py",
    "las_p5r4k1_gs.py": JUDGE_DIR / "las_p5r4k1_gs.py",
    "c2.py": ROOT / "03_src" / "outrigger_sim" / "control" / "c2.py",
    "v5_options.py": ROOT / "03_src" / "outrigger_sim" / "hydraulics" / "v5_options.py",
    "las_revA_targeted.py": HERE / "las_revA_targeted.py",
    "las_rev_targeted.py": HERE / "las_rev_targeted.py",
    "fb_targeted.py": HERE / "fb_targeted.py",
    "las_targeted.py": HERE / "las_targeted.py",
    "k1_targeted.py": HERE / "k1_targeted.py",
    "las_phase_diag.py": HERE / "las_phase_diag.py",
    "s2_defer_targeted.py": HERE / "s2_defer_targeted.py",
    "run_v5.py": HERE / "run_v5.py",
}
"""Rules 5.1: c2.py, v5_options.py, this tool, the judge, and the imported harness tools."""
IDENTITY_KEYS = ("git_head", "code_diff_sha256", "sha256")
FIRST_ATTEMPT, RERUN_ATTEMPT = 1, 2
LOC_CORRECTIONS_ATTRIBUTE = "_p5k_loc_corrections"
OVERRIDE_COUNTS: dict[str, int] = {"applications": 0, "kept_target": 0, "las_off": 0}
"""This worker's override counts (one run per worker, ``maxtasksperchild=1``)."""
BIT_GATES = {"Z-A": ("Z-0",), "Z-T": ("Z-0", "Z-A"), "Z-S": ("Z-0", "Z-A"),
             "Z-C": ("Z-0", "Z-A"), "Z-X": ("Z-0", "Z-A", "Z-T", "Z-S", "Z-C")}
"""Rules 4.2 order: the bundles whose bit predictions must hold before a bundle runs."""


# =============================================================================== preset (2)
def preset_problems(config) -> list[str]:
    """Why ``config`` is not the K1 preset this rules starts from (b0 + gate on + N_r 0 + no
    touch creep latch); ``fb_targeted.check_preset_las`` covers the other b0 fields."""
    las = config.liftoff_approach_slow
    problems = [f"liftoff_approach_slow.{name} {getattr(las, name)!r} != b0 {value!r}"
                for name, value in pj.B0_SETTINGS.items() if getattr(las, name) != value]
    if config.slope_clearance_margin.flat_soil_margin_order_gate is not True:
        problems.append("slope_clearance_margin.flat_soil_margin_order_gate is not True")
    creep = getattr(config, "touch_creep_latch", None)
    if creep is not None and getattr(creep, "enable", False):
        problems.append("touch_creep_latch.enable is True (K-2 _TCL is not adopted)")
    return problems


def check_preset() -> None:
    """The R8 preset of this process is the K1 preset with LAS-b b0 (rules 11.3 1).

    Raises:
        RuntimeError: Another LAS-b, the gate off, a ramp or the touch creep latch.
    """
    from outrigger_sim.control import c2

    fb.check_preset_las()
    problems = preset_problems(c2.C2Config().with_10hz_d1())
    if problems:
        raise RuntimeError(f"R8 preset is not P0+K1: {problems}")


def preset_las_settings():
    from outrigger_sim.control import c2

    return c2.C2Config().with_10hz_d1().liftoff_approach_slow


def p5r4_settings(preset_settings):
    """cand LAS-b settings: one ``replace`` of the b0 preset (rules 2)."""
    return replace(preset_settings, **pj.P5R4_OVERRIDE)


def arm_settings(arm: str, preset_settings):
    return p5r4_settings(preset_settings) if arm == pj.ARM_CAND else preset_settings


def p5r4_config(config, preset_settings, target_settings, counts: dict[str, int]):
    """``config`` with the P5r4 LAS-b; a config at P5r4 already or with LAS-b off is kept.

    Raises:
        RuntimeError: LAS-b on with settings that are neither b0 nor P5r4.
    """
    settings = config.liftoff_approach_slow
    if not settings.enable:
        counts["las_off"] += 1
        return config
    if settings == target_settings:
        counts["kept_target"] += 1
        return config
    if settings != preset_settings:
        raise RuntimeError(f"LAS-b settings are neither b0 nor P5r4: {settings}")
    counts["applications"] += 1
    return replace(config, liftoff_approach_slow=target_settings)


_INSTALLED: dict = {}


def install_p5r4_override(preset_settings, controller_class=None) -> None:
    """Wrap ``C2Controller.__init__`` so every controller of this worker runs P5r4.

    Raises:
        RuntimeError: Installed twice in one process.
    """
    if "override" in _INSTALLED:
        raise RuntimeError("las_p5r4k1_targeted.install_p5r4_override: already installed")
    if controller_class is None:
        from outrigger_sim.control import c2

        controller_class = c2.C2Controller
    target = p5r4_settings(preset_settings)
    original_init = controller_class.__init__

    def __init__(self, geometry, config=None, *args, **kwargs):
        if config is not None:
            config = p5r4_config(config, preset_settings, target, OVERRIDE_COUNTS)
        original_init(self, geometry, config, *args, **kwargs)

    controller_class.__init__ = __init__
    _INSTALLED["override"] = (controller_class, "__init__", original_init)


def _correction_hook(original):
    """rev1 RV1-5 ``anchor.loc_calls``: one entry per LOC, read from the state after the LOC
    was confirmed (``t_loc_s``, ``t_P_s``, ``bias_corner_raw_m``, ``bias_corner_m``)."""

    def _confirm_liftoff(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        soil = self._soil_state()
        raw = soil.corner_bias_raw_m
        self.__dict__.setdefault(LOC_CORRECTIONS_ATTRIBUTE, []).append({
            "t_loc_s": soil.liftoff_s, "t_P_s": soil.plateau_start_s,
            "bias_corner_raw_m": None if raw is None else [float(v) for v in raw],
            "bias_corner_m": [float(v) for v in soil.corner_bias_m],
            "loc_anchor_applied": bool(soil.is_loc_anchor_applied),
            "clearance_at_P_m": soil.clearance_at_plateau_start_m})
        return result

    return _confirm_liftoff


SOIL_META_KEYS = ("t_P_s", "t_loc_s", "bias_corner_raw_m", "bias_corner_m", "corner_order",
                  "loc_anchor_applied", "loc_anchor_bias_mm", "clearance_at_P_m",
                  "clearance_at_loc_m")
"""rev1 RV1-5: the ``controller_meta.soil`` keys ``anchor.soil_meta`` copies (None if absent)."""


def anchor_record(controller) -> dict:
    """rev1 RV1-5 ``anchor`` block: the end-of-run soil meta keys and the per-LOC calls."""
    soil = controller.meta().get("soil") or {}
    return {"soil_meta": {name: soil.get(name) for name in SOIL_META_KEYS},
            "loc_calls": list(controller.__dict__.get(LOC_CORRECTIONS_ATTRIBUTE) or ())}


def install_correction_witness(controller_class=None) -> None:
    """Record the S-3 correction of every LOC (read only; rev1 record items).

    Raises:
        RuntimeError: Installed twice in one process.
    """
    if "correction" in _INSTALLED:
        raise RuntimeError("las_p5r4k1_targeted.install_correction_witness: already installed")
    if controller_class is None:
        from outrigger_sim.control import c2

        controller_class = c2.C2Controller
    original = controller_class._confirm_liftoff
    controller_class._confirm_liftoff = _correction_hook(original)
    _INSTALLED["correction"] = (controller_class, "_confirm_liftoff", original)


def uninstall() -> None:
    """Undo this module's installs (tests only; workers never uninstall)."""
    for name in ("override", "correction"):
        if name in _INSTALLED:
            cls, attribute, original = _INSTALLED.pop(name)
            setattr(cls, attribute, original)
    for name in OVERRIDE_COUNTS:
        OVERRIDE_COUNTS[name] = 0


# =============================================================================== jobs (4.2)
def _entry(bundle: str, arm: str, label: str, grid_point=None, record_diag=False,
           record_done=False) -> dict:
    """The ``rev`` entry a job carries into the worker (the fields the copied checks read)."""
    return {"bundle": bundle, "arm": arm, "candidate": pj.ARM_CANDIDATE[arm], "label": label,
            "grid_point": None if grid_point is None else list(grid_point),
            "record_diag": record_diag, "record_done": record_done}


def z0_jobs() -> list[tuple[dict, dict]]:
    import las_rev_targeted as rev

    base, entries = rev.r0_jobs()
    return [(job, _entry("Z-0", pj.ARM_REF, entry["label"], entry["grid_point"],
                         entry["record_diag"])) for job, entry in zip(base, entries, strict=True)]


def za_jobs() -> list[tuple[dict, dict]]:
    import las_revA_targeted as revA

    out = []
    for bundle in ("R-0A", "R-Q"):
        base, entries = revA.grid_jobs(bundle, (pj.ARM_CANDIDATE[pj.ARM_CAND],))
        out += [(job, _entry("Z-A", pj.ARM_CAND, entry["label"], entry["grid_point"],
                             record_diag=True, record_done=True))
                for job, entry in zip(base, entries, strict=True)]
    return out


def pair_base_jobs(bundle: str) -> list[dict]:
    """The ``run_v5`` jobs of a pair bundle as the stored files' tools built them."""
    import las_rev_targeted as rev

    if bundle == "Z-T":
        return rev.t_base_jobs()
    if bundle == "Z-S":
        return rev.s_base_jobs()
    if bundle in ("Z-C", "Z-X"):
        import s2_defer_targeted as s2t

        return s2t.soil_group_jobs()
    raise ValueError(f"no pair jobs for {bundle!r}")


def pair_jobs(bundle: str) -> list[tuple[dict, dict]]:
    """ref then cand of each key, next to each other, VB first (cand with the DONE record)."""
    ordered = sorted(pair_base_jobs(bundle), key=lambda job: job["setting"] != "VB")
    out = []
    for job in ordered:
        out.append((job, _entry(bundle, pj.ARM_REF, "P0")))
        out.append((job, _entry(bundle, pj.ARM_CAND, "P5r4", record_done=True)))
    return out


def zx_jobs(keys: list[str]) -> list[tuple[dict, dict]]:
    """Z-X: ref with the DONE record on ``keys`` (taken from Z-T / Z-S / Z-C).

    Raises:
        KeyError: A key outside the three pair bundles.
    """
    by_key = {}
    for bundle in pj.PAIR_BUNDLES:
        for job in pair_base_jobs(bundle):
            by_key.setdefault(fb.fb_key(job), job)
    missing = [key for key in keys if key not in by_key]
    if missing:
        raise KeyError(f"Z-X keys without a job: {missing}")
    return [(by_key[key], _entry("Z-X", pj.ARM_REF, "P0", record_done=True)) for key in keys]


def bundle_jobs(bundle: str, z_x_keys: list[str] | None = None) -> list[dict]:
    """Jobs of a bundle with ``p5k_entry`` and ids over the bundle."""
    if bundle == "Z-0":
        pairs = z0_jobs()
    elif bundle == "Z-A":
        pairs = za_jobs()
    elif bundle in pj.PAIR_BUNDLES:
        pairs = pair_jobs(bundle)
    elif bundle == "Z-X":
        pairs = zx_jobs(list(z_x_keys or ()))
    else:
        raise ValueError(f"unknown bundle {bundle!r}")
    jobs = []
    for index, (job, entry) in enumerate(pairs):
        entry = {**entry, "id": index, "key": fb.fb_key(job)}
        jobs.append({**job, "p5k_entry": entry})
    return jobs


def unit_of_job(job: dict) -> str:
    entry = job["p5k_entry"]
    if entry["bundle"] == "Z-A":
        return f"{entry['key']}{pj.GRID_UNIT_SEPARATOR}{entry['label']}"
    return entry["key"]


def comparable_job(job: dict) -> str:
    return json.dumps({k: v for k, v in job.items()
                       if k not in ("mask", "rev", "t4h_dir", "p5k_entry")}, sort_keys=True)


def stored_jobs(bundle: str, bases: pj.Bases) -> dict[str, dict]:
    """unit -> the stored line's ``job`` the bundle's job dicts must equal (H-4 form)."""
    lines = bases.lines
    if bundle == "Z-0":
        return {pj.key_of(line): line["job"] for line in lines["R0"]}
    if bundle == "Z-A":
        return {pj.grid_unit(line): line["job"] for line in lines["R0A"] + lines["RQ"]}
    if bundle == "Z-T":
        return {line["las"]["key"]: line["job"] for line in lines["T1"] + lines["T2"]
                if pj.is_b0_t_line(line)}
    if bundle == "Z-S":
        return {pj.stored_key_of(line): line["job"] for line in lines["RS"]}
    out = {pj.stored_key_of(line): line["job"] for line in lines["SC"]}
    if bundle == "Z-X":
        out.update({line["las"]["key"]: line["job"] for line in lines["T1"] + lines["T2"]
                    if pj.is_b0_t_line(line)})
        out.update({pj.stored_key_of(line): line["job"] for line in lines["RS"]})
    return out


def job_problems(bundle: str, jobs: list[dict], bases: pj.Bases) -> list[str]:
    """Rules 4.1 / K-9: the units are the recomputed list (Z-X: the claims) and every job dict
    equals the stored line's ``job``."""
    stored = stored_jobs(bundle, bases)
    problems = []
    units = [unit_of_job(job) for job in jobs]
    if bundle != "Z-X":
        want = bases.labels["Z-A"] if bundle == "Z-A" else bases.lists[bundle]
        arms = len(pj.BUNDLE_ARMS[bundle])
        if sorted(units) != sorted(want * arms):
            problems.append(f"{bundle}: job units are not the appendix list x {arms} arm(s)")
    for job, unit in zip(jobs, units, strict=True):
        line_job = stored.get(unit)
        if line_job is None:
            problems.append(f"{bundle} {unit}: no stored line")
        elif comparable_job(job) != comparable_job(line_job):
            problems.append(f"{bundle} {unit}: job dict differs from the stored line")
    return problems


# =============================================================================== worker
def rules_record() -> dict[str, str]:
    """LF sha256 of every rules file a line records (rules 5.1)."""
    return {name: pj.lf_sha256(pj.RULES_DIR / name) for name in pj.sealed_rules()}


def run_identity() -> dict:
    return fb.run_identity(files=IDENTITY_FILES)


def code_blobs(root: Path = ROOT) -> dict[str, str | None]:
    """K-2: sha256 of the HEAD blob of ``c2.py`` and ``v5_options.py``."""
    head = fb._git(root, "rev-parse", "HEAD").strip()
    return {path: pj.git_blob_sha256(root, head, path) for path in pj.BLOB_FILES}


_RUN: dict = {}
"""The worker's run values (one run per worker)."""


def install_all(entry: dict) -> None:
    """Threads, preset (b0 + gate), run capture, witnesses, grid budget, the cand override,
    the DONE record."""
    import k1_targeted
    import las_phase_diag
    import las_rev_targeted as rev

    fb._install_candidate(fb.CANDIDATES["L"])  # threads, preset LAS-b b0, run capture
    check_preset()
    # Read before the run: the harness later patches with_10hz_d1 (and keeps its last result).
    _RUN["preset_settings"] = preset_las_settings()
    k1_targeted.install_loc_witness()
    install_correction_witness()
    grid_point = None if entry["grid_point"] is None else tuple(entry["grid_point"])
    if entry["record_diag"] or grid_point is not None:
        las_phase_diag.install(entry["record_diag"], grid_point)
    if entry["arm"] == pj.ARM_CAND:
        install_p5r4_override(_RUN["preset_settings"])
    if entry["record_done"]:
        rev.install_done_recorder()


def k1_record(controller) -> dict:
    """``k1`` block: the run controller's gate (setting and meta), decisions, the witness."""
    import k1_targeted

    meta = controller.meta()["slope_clearance_margin"]
    decisions = meta["order_gate"]["decisions"]
    return {"enabled": meta["order_gate"]["enabled"],
            "setting": controller.config.slope_clearance_margin.flat_soil_margin_order_gate,
            "decisions": decisions, "r4_applied": bool(meta["flat_soil_margin_applied"]),
            "would_block_any": any(d["would_block"] for d in decisions),
            "loc_calls": list(controller.__dict__.get(k1_targeted.WITNESS_ATTRIBUTE) or ())}


def rev_record(entry: dict, controller, line: dict) -> dict:
    preset = _RUN.get("preset_settings") or preset_las_settings()
    settings = asdict(controller.config.liftoff_approach_slow)
    expected = asdict(arm_settings(entry["arm"], preset))
    return {**{name: entry[name] for name in ("bundle", "candidate", "label", "grid_point",
                                              "record_diag", "record_done", "key", "id")},
            "attempt": entry["attempt"], "resumed": entry["resumed"],
            "settings": settings, "expected_settings": expected,
            "settings_match": settings == expected,
            "controller_tag": line.get("controller_tag")}


def p5k_record(entry: dict, controller, line: dict, identity: dict) -> dict:
    from outrigger_sim.hydraulics import v5_options

    meta = controller.meta()
    return {**head_record(entry), "identity": identity, "rules": rules_record(),
            "controller_tag": line.get("controller_tag"),
            "is_liftoff_slow_tag": v5_options.is_liftoff_slow_tag(line.get("controller_tag")),
            "las_settings": asdict(controller.config.liftoff_approach_slow),
            "override": dict(OVERRIDE_COUNTS), "k1_token": None,
            "touch_creep_latch_enabled": v5_options.is_touch_creep_on(controller.config),
            "touch_creep_meta": meta.get("touch_creep_latch")}


def effective_record(controller) -> dict:
    """Output contract 9: the run controller's effective gate and touch creep latch."""
    from outrigger_sim.hydraulics import v5_options

    return {"flat_soil_margin_order_gate": v5_options.is_order_gate_on(controller.config),
            "touch_creep_latch_enable": v5_options.is_touch_creep_on(controller.config)}


def head_record(entry: dict) -> dict:
    """The ``p5k`` fields known before the run (error lines carry them too)."""
    return {name: entry.get(name) for name in
            ("bundle", "arm", "las_candidate", "gs", "gs_stage", "id", "attempt", "resumed",
             "worker_mask", "code_blobs", "parent_head", "list_sha256")}


def add_blocks(line: dict, entry: dict, job: dict, identity: dict) -> None:
    import las_phase_diag
    import las_rev_targeted as rev
    import las_revA_targeted as revA

    plant, controller = fb._run_objects(job)
    if plant is None or controller is None:
        raise RuntimeError(f"run objects not captured (plant {plant is not None}, "
                           f"controller {controller is not None})")
    line["las"] = revA.las_block(controller, fb._CAPTURE.get("harness"), entry["candidate"])
    line["rev"] = {**rev_record(entry, controller, line), "identity": identity,
                   "rules_sha256": rules_record()}
    line["las_candidate"] = entry["candidate"]
    line["k1"] = k1_record(controller)
    line["p5k"] = p5k_record(entry, controller, line, identity)
    line["anchor"] = anchor_record(controller)
    line["effective"] = effective_record(controller)
    if entry["record_diag"]:
        diag_entry = {"bundle": entry["bundle"], "label": entry["label"], "record": True}
        line["diag"] = {"key": entry["key"],
                        **las_phase_diag.diag_block(diag_entry, line, line["las"], controller,
                                                    plant, identity)}
    if entry["record_done"]:
        line["done_trace"], line["done_clock"] = rev.done_blocks(controller)


def error_line(head: dict, stage: str, exc: Exception, t_start: float) -> dict:
    return {**head, "error": f"{stage}: {exc!r}", "tb": traceback.format_exc()[-3000:],
            "wall_s": round(time.perf_counter() - t_start, 1)}


def run_p5k_job(job: dict) -> dict:
    """Worker: install the arm, run, add the blocks (an exception is an error line)."""
    t_start = time.perf_counter()
    entry = job.pop("p5k_entry")
    head = {"job": job, "rev": {name: entry.get(name) for name in
                                ("bundle", "candidate", "label", "grid_point", "key", "id",
                                 "attempt", "resumed")},
            "las_candidate": entry.get("candidate"), "p5k": head_record(entry)}
    try:
        import run_v5  # sys.path and thread variables first

        identity = run_identity()
        install_all(entry)
    except Exception as exc:  # recorded as an error line; the batch decides (10.1)
        return error_line(head, "install", exc, t_start)
    line = run_v5.run_one(job)
    if "error" in line:
        return {**line, "rev": head["rev"], "p5k": head["p5k"]}
    try:
        add_blocks(line, entry, job, identity)
    except Exception as exc:
        return error_line(head, "metrics", exc, t_start)
    return line


# =============================================================================== batch
@dataclass
class BatchState:
    """What a running batch knows (rules 8.2)."""

    stop: str | None = None
    runs: int = 0
    error_lines: int = 0
    skipped: int = 0
    attempts: dict[int, int] = field(default_factory=dict)
    finished: dict[tuple[str, str], dict] = field(default_factory=dict)
    c2_pairs: set[str] = field(default_factory=set)
    k8_lines: int = 0
    error_units: set[tuple] = field(default_factory=set)

    @property
    def errors_left(self) -> int:
        """rev2 RV2-8: (arm, key) with error lines and no finished line."""
        return len({unit for unit in self.error_units if unit not in self.finished})


def batch_stop_reason(record: dict, current: dict) -> str | None:
    """Identity change, K-3 tag, K-4 gate or K-5 LAS-b problems stop the batch."""
    identity = pj.p5k_of(record).get("identity") or {}
    changed = [name for name in IDENTITY_KEYS if identity.get(name) != current.get(name)]
    if changed:
        return f"run identity changed during the batch: {changed}"
    found = pj.tag_problems(record) + pj.gate_problems(record) + pj.las_problems(record)
    if found:
        return f"{pj.unit_of(record)}: {found}"
    return None


def note_pair(record: dict, state: BatchState, bundle: str) -> None:
    """S-5: count the pairs with a C-2 type violation (an undecidable pair counts too)."""
    unit = pj.unit_of(record)
    arm = pj.p5k_of(record).get("arm")
    state.finished[(unit, arm)] = record
    other = state.finished.get((unit, pj.ARM_REF if arm == pj.ARM_CAND else pj.ARM_CAND))
    if bundle not in pj.PAIR_BUNDLES or other is None:
        return
    cand, ref = (record, other) if arm == pj.ARM_CAND else (other, record)
    try:
        violations = pj.c2_violations(cand, ref)
    except pj.MissingField as exc:
        violations = [f"undecidable: missing {exc}"]
    if violations:
        state.c2_pairs.add(unit)
    if len(state.c2_pairs) >= pj.C2_STOP_PAIRS:
        state.stop = f"S-5: {len(state.c2_pairs)} pairs with a C-2 type violation"


def handle_record(record: dict, jobs_by_id: dict, state: BatchState, bundle: str,
                  current: dict, resubmit) -> None:
    job_id = pj.p5k_of(record).get("id")
    if "error" in record:
        state.error_lines += 1
        state.error_units.add((pj.unit_of(record), pj.p5k_of(record).get("arm")))
        if state.attempts.get(job_id, FIRST_ATTEMPT) < RERUN_ATTEMPT and job_id in jobs_by_id:
            state.attempts[job_id] = RERUN_ATTEMPT
            job = jobs_by_id[job_id]
            job["p5k_entry"] = {**job["p5k_entry"], "attempt": RERUN_ATTEMPT}
            resubmit(job)
        return
    state.stop = batch_stop_reason(record, current) or state.stop
    if pj.k8_problems(record):
        state.k8_lines += 1
    note_pair(record, state, bundle)


def print_line(state: BatchState, total: int, record: dict) -> None:
    """One value-free progress line (16.2: no force, stroke, time or hash value)."""
    block = pj.p5k_of(record)
    text = "ERROR" if "error" in record else "done"
    print(f"{state.runs}/{total} {block.get('id')} {block.get('arm')} {pj.unit_of(record)}: "
          f"{text} (attempt {block.get('attempt')})", flush=True)


def run_batch(jobs: list[dict], path: Path, workers: int, bundle: str, current: dict
              ) -> BatchState:
    """Run the jobs in spawned workers (one run each) and write every line to the new file."""
    import verdict_runs

    verdict_runs.warm_numba_cache()
    path.parent.mkdir(parents=True, exist_ok=True)
    state = BatchState()
    jobs_by_id = {job["p5k_entry"]["id"]: job for job in jobs}
    pending = list(jobs)
    results: queue.Queue = queue.Queue()
    in_flight = 0
    with path.open("x", encoding="utf-8") as handle, \
            get_context("spawn").Pool(workers, maxtasksperchild=1) as pool:

        def submit(job: dict) -> None:
            nonlocal in_flight
            in_flight += 1
            entry = job["p5k_entry"]
            pool.apply_async(run_p5k_job, (json.loads(json.dumps(job)),), callback=results.put,
                             error_callback=lambda exc, job=job, entry=entry: results.put(
                                 {"job": {k: v for k, v in job.items() if k != "p5k_entry"},
                                  "rev": {"key": entry["key"], "label": entry["label"],
                                          "bundle": entry["bundle"],
                                          "attempt": entry.get("attempt")},
                                  "las_candidate": entry.get("candidate"),
                                  "p5k": head_record(entry), "error": f"pool: {exc!r}",
                                  "wall_s": 0.0}))

        while state.stop is None and (pending or in_flight):
            while pending and in_flight < workers:
                submit(pending.pop(0))
            if not in_flight:
                break
            record = results.get()
            in_flight -= 1
            record.setdefault("job", {}).pop("mask", None)
            handle.write(json.dumps(record, default=_json_default) + "\n")
            handle.flush()
            state.runs += 1
            print_line(state, len(jobs), record)
            handle_record(record, jobs_by_id, state, bundle, current,
                          lambda job: pending.insert(0, job))
        if state.stop is not None:
            pool.terminate()
    state.skipped += len(pending)
    return state


def _json_default(value):
    return value.item() if hasattr(value, "item") else str(value)


# =============================================================================== gates
def run_dir_of(v5_dir: Path) -> Path:
    return v5_dir / pj.RUN_DIR_RELATIVE


def out_path_of(bundle: str, run_dir: Path, is_resume: bool, is_gs: bool) -> Path:
    if is_gs:
        return run_dir / pj.GS_DIR_NAME / f"p5k_GS_{bundle.replace('-', '')}.jsonl"
    name = pj.BUNDLE_FILE[bundle]
    return run_dir / (name.replace(".jsonl", f"{pj.RESUME_SUFFIX}.jsonl") if is_resume else name)


def identity_problems(identity: dict) -> list[str]:
    """Rules 5.1: empty code diff, only this work's tests dirty, one thread."""
    probe = {"p5k": {"identity": identity, "rules": pj.sealed_rules()}}
    return [text for text in pj.identity_value_problems(probe) if not text.startswith("K-0")]


def order_problems(bundle: str, ctx: pj.Context, current: dict) -> list[str]:
    """Rules 4.2 / S-2: the bit predictions of the earlier bundles hold, their lines are all
    there and from the current commit and tool sha256."""
    problems = []
    for name in BIT_GATES.get(bundle, ()):
        for arm in pj.BUNDLE_ARMS[name]:
            part = ctx.parts[(name, arm)]
            expected = pj.expected_units(name, arm, ctx.bases, [])
            if name in ("Z-0", "Z-A") and len(part.finished) != len(expected):
                problems.append(f"{name} {arm}: {len(part.finished)}/{len(expected)} lines")
            if name in pj.PAIR_BUNDLES and not part.finished:
                problems.append(f"{name} {arm}: no lines")
            stale = [unit for unit, line in part.finished.items()
                     if any((pj.p5k_of(line).get("identity") or {}).get(key) != current.get(key)
                            for key in IDENTITY_KEYS)]
            if stale:
                problems.append(f"{name} {arm}: {len(stale)} lines of another run identity")
        if name in ("Z-0", "Z-A"):
            for arm, bit in pj.bit_predictions(name, ctx).items():
                if bit.get("predicted") and (bit.get("different") or bit.get("equal")
                                             != bit.get("expected")):
                    problems.append(f"{name} {arm}: bit prediction not met "
                                    f"({bit.get('equal')}/{bit.get('expected')} equal)")
    return problems


def resume_units(path: Path) -> list[str]:
    """10.1: units with exactly one error line and no finished line in the bundle file."""
    finished, errors = set(), {}
    for line in pj.read_lines(path) if path.is_file() else []:
        unit = pj.unit_of(line)
        if pj.is_error(line):
            errors[unit] = errors.get(unit, 0) + 1
        else:
            finished.add(unit)
    return sorted(unit for unit, count in errors.items() if count == 1 and unit not in finished)


def gs_units(path: Path, bundle: str) -> dict[tuple[str, str], str]:
    """(unit, arm) -> stage of the G-S list's lines of ``bundle``.

    Raises:
        ValueError: The list is not a G-S list document.
    """
    document = json.loads(path.read_text(encoding="utf-8"))
    rows = document.get("harness") if isinstance(document, dict) else None
    if not isinstance(rows, list):
        raise ValueError(f"{path}: no 'harness' row list (las_p5r4k1_gs.py list output)")
    return {(row["unit"], row["arm"]): row["stage"] for row in rows if row["bundle"] == bundle}


@dataclass
class RunPlan:
    """What ``run`` executes."""

    jobs: list[dict]
    path: Path
    identity: dict


def _select(jobs: list[dict], args, bundle: str, run_dir: Path) -> list[dict]:
    """Resume / G-S / trial selection of the bundle jobs (with the entry flags)."""
    if args.gs_list is not None:
        wanted = gs_units(args.gs_list, bundle)
        jobs = [job for job in jobs
                if (unit_of_job(job), job["p5k_entry"]["arm"]) in wanted]
        for job in jobs:
            stage = wanted[(unit_of_job(job), job["p5k_entry"]["arm"])]
            job["p5k_entry"].update(gs=True, gs_stage=stage)
            if bundle == "Z-X":
                job["p5k_entry"]["record_done"] = True
        return jobs
    if args.resume:
        units = set(resume_units(out_path_of(bundle, run_dir, False, False)))
        print(f"resume units (10.1): {len(units)}", flush=True)
        jobs = [job for job in jobs if unit_of_job(job) in units]
        for job in jobs:
            job["p5k_entry"].update(attempt=RERUN_ATTEMPT, resumed=True)
    if args.keys:
        wanted = set(args.keys.split(","))
        jobs = [job for job in jobs if unit_of_job(job) in wanted]
    return jobs if args.limit is None else jobs[: args.limit]


def prepare(args) -> RunPlan:
    """Jobs, output path and identity of a run.

    Raises:
        ValueError, KeyError, RuntimeError, pj.InputError: Input or gate problems (exit 2).
    """
    is_trial, is_gs = args.trial_out is not None, args.gs_list is not None
    run_dir = run_dir_of(args.v5_dir)
    if (args.keys or args.limit is not None) and not is_trial:
        raise ValueError("--keys / --limit only with --trial-out (rules 4.1)")
    if is_trial and args.trial_out.resolve().is_relative_to(run_dir.resolve()):
        raise ValueError("--trial-out must lie outside the p5r4k1 folder")
    bases = pj.load_bases(args.v5_dir)
    import run_v5  # noqa: F401  (puts 03_src on sys.path before the preset check)

    check_preset()
    identity = run_identity()
    problems = identity_problems(identity)
    if problems:
        raise ValueError(f"run identity (rules 5.1): {problems}")
    ctx = pj.load_context(run_dir, args.v5_dir, None)
    z_x_keys = pj.claim_keys(ctx) if args.bundle == "Z-X" else None
    if args.bundle == "Z-X" and is_gs:
        z_x_keys = [unit for unit, _arm in gs_units(args.gs_list, "Z-X")]
    if z_x_keys is not None and len(z_x_keys) > pj.Z_X_MAX_LINES:
        raise ValueError(f"Z-X: {len(z_x_keys)} claim keys > {pj.Z_X_MAX_LINES} (S-8: ask)")
    if not (is_trial or is_gs):
        problems = order_problems(args.bundle, ctx, identity)
        if problems:
            raise ValueError(f"order gates before {args.bundle}: {problems}")
    jobs = bundle_jobs(args.bundle, z_x_keys)
    problems = job_problems(args.bundle, jobs, bases)
    if problems:
        raise ValueError(f"job dicts / units (rules 4.1): {problems[:5]} ({len(problems)})")
    _decorate(jobs, args, bases, identity)
    jobs = _select(jobs, args, args.bundle, run_dir)
    if not jobs:
        raise ValueError("no runs selected")
    path = args.trial_out if is_trial else out_path_of(args.bundle, run_dir, args.resume, is_gs)
    if path.exists():
        raise ValueError(f"{path} exists (new files only)")
    return RunPlan(jobs, path, identity)


def _decorate(jobs: list[dict], args, bases: pj.Bases, identity: dict) -> None:
    """Entry fields every line records (mask, code blobs, list sha256, attempt)."""
    mask = None if args.affinity is None else int(args.affinity, 16)
    blobs = code_blobs()
    list_name = "Z-A" if args.bundle == "Z-A" else args.bundle
    list_sha = None if args.bundle == "Z-X" else pj.key_list_sha256(
        bases.labels["Z-A"] if list_name == "Z-A" else bases.lists[list_name])
    for job in jobs:
        job["mask"] = mask
        job["p5k_entry"].update(las_candidate=job["p5k_entry"]["candidate"], gs=False,
                                gs_stage=None, attempt=FIRST_ATTEMPT, resumed=False,
                                worker_mask=args.affinity, code_blobs=blobs,
                                parent_head=identity["git_head"], list_sha256=list_sha)


def run_command(args) -> int:
    try:
        plan = prepare(args)
    except (KeyError, OSError, ValueError, RuntimeError, pj.InputError,
            subprocess.SubprocessError) as exc:
        print(f"input error: {exc!r}")
        print(json.dumps({"bundle": args.bundle, "stop": "input", "reason": str(exc)}))
        return 2
    print(f"run identity: {plan.identity['git_head']} dirty {plan.identity['git_dirty']} "
          f"code_diff {plan.identity['code_diff_sha256'][:12]} rules {pj.RULES_SHA256[:12]}",
          flush=True)
    print(f"{args.bundle}: {len(plan.jobs)} runs -> {plan.path}", flush=True)
    state = run_batch(plan.jobs, plan.path, args.workers, args.bundle, plan.identity)
    print(f"errors {state.error_lines}", flush=True)
    summary = {"bundle": args.bundle, "out": str(plan.path), "runs": state.runs,
               "error_lines": state.error_lines, "errors_total": state.error_lines,
               "errors_left": state.errors_left, "skipped": state.skipped,
               "stop": state.stop, "c2_pairs": len(state.c2_pairs),
               "k8_problem_lines": state.k8_lines}
    print(json.dumps(summary))
    return 1 if state.stop or state.skipped or state.error_lines else 0


# =============================================================================== list
def list_bundles(v5_dir: Path) -> tuple[list[str], list[str]]:
    """(report lines, problems): stored files, lists and runs per bundle (no values)."""
    bases = pj.load_bases(v5_dir)
    report = [f"base {name}: sha256 {sha}" for name, sha in sorted(bases.sha256.items())]
    report += [f"list {name}: {len(keys)} keys sha256 {pj.key_list_sha256(keys)}"
               for name, keys in sorted(bases.lists.items())]
    report += [f"labels {name}: sha256 {sha}" for name, sha in pj.label_list_sha256(bases).items()]
    problems = []
    for bundle in pj.BUNDLES:
        if bundle == "Z-X":
            report.append("Z-X: keys from the judge on the run folder (C-4 claims)")
            continue
        jobs = bundle_jobs(bundle)
        report.append(f"{bundle}: {len(jobs)} runs")
        if len(jobs) != pj.BUNDLE_COUNTS[bundle]:
            problems.append(f"{bundle}: {len(jobs)} runs, expected {pj.BUNDLE_COUNTS[bundle]}")
        problems += job_problems(bundle, jobs, bases)
    return report, problems


# =============================================================================== CLI
def _parse_args(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list", help="stored files, key lists and runs per bundle")
    listing.add_argument("--v5-dir", type=Path, default=pj.V5_DIR,
                         help="v5 folder with the stored files (the main checkout's)")
    run = sub.add_parser("run", help="run a bundle into a new file")
    run.add_argument("--bundle", required=True, choices=pj.BUNDLES)
    run.add_argument("--v5-dir", type=Path, default=pj.V5_DIR)
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--affinity", default=None, help="hex mask, set in every worker")
    run.add_argument("--resume", action="store_true",
                     help="10.1: re-run the units with one error line once")
    run.add_argument("--gs-list", type=Path, default=None,
                     help="16.2 G-S: run this list's lines of the bundle into <run>/gs/")
    run.add_argument("--trial-out", type=Path, default=None,
                     help="trial file outside the p5r4k1 folder (never judged)")
    run.add_argument("--keys", default=None, help="trial only: comma-separated units")
    run.add_argument("--limit", type=int, default=None, help="trial only: first N runs")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    problems = pj.seal_problems()
    if problems:
        print(f"input error (S-1 seals): {problems}")
        print(json.dumps({"stop": "S-1", "reasons": problems}))
        return 2
    if args.command == "run":
        return run_command(args)
    try:
        report, problems = list_bundles(args.v5_dir)
    except (KeyError, OSError, ValueError, pj.InputError) as exc:
        print(f"input error: {exc!r}")
        print(json.dumps({"input_error": str(exc)}))
        return 2
    print("\n".join(report))
    for problem in problems:
        print(f"MISMATCH {problem}")
    print(json.dumps({"bundles": list(pj.BUNDLES), "problems": len(problems)}))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
