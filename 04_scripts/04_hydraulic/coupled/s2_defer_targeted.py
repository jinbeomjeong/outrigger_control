"""S-2 soil-mode start deferral S2D on the reduced harness: bundles S-0, S-C, S-D, A-S, A-P0.

Rules: ``06_analysis/02_control/verif_matrix/s2_soil_defer_rules.md`` (control-expert, sealed;
LF sha256 ``s2_defer_judge.RULES_S2D_SHA256``), its addenda ``s2_soil_defer_rules_rev1.md``
(``RULES_S2D_REV1_SHA256``) and ``s2_soil_defer_rules_rev2.md`` (``RULES_S2D_REV2_SHA256``)
and the six A-plan rules files it inherits (all checked, SH-1; every line records all nine
digests). The rules text wins where this code differs. The
run machinery (LAS-b candidate wrapper, DONE record, diagnosis recorders, pool, job dicts) is
``las_revA_targeted``'s; this tool adds the S2D settings wrapper, the S2D trace and the
``s2d`` block (``s2_defer_judge`` module docstring).

Soil candidates (``s2_defer_judge.SOIL_CANDIDATES``, ``dataclasses.replace`` on the run's
``config.soil`` in ``C2Controller.__init__``, worker only):
  N0     ``mode_defer_periods`` 0 given explicitly (S-0, A-P0)
  P0     the S2D values with ``mode_defer_shadow`` (record only, commands of P0; S-C)
  S2D    N_d 5, 6 mm, k_d 4 (S-D)
  P5r4S  the S2D values on the A-plan P5r4 LAS-b candidate (A-S)

Bundles (rules 3), output ``06_analysis/03_hydraulic/coupled/v5/soil_defer/s2d_<bundle>.jsonl``
(``--out-dir`` for another checkout, e.g. the main checkout from a worktree; files opened
with ``"x"``, no resume):
  S-0   9: the A-plan R-0 six jobs (stored hashes) + diagA P0 / P5 / P5r4 (stored hashes,
        diag period record with the ``soil`` field on), N0.
  S-C   456: the v5 D-1 soil-response groups (``d1_rows.jobs()``; job dict = the
        ``d1.jsonl`` line's), LAS P0 + soil P0 (shadow).
  S-D   S2D on every S-C key with a soil-mode start + 40 seeded others
        (``s2_defer_judge.sd_selection``).
  A-S   324: the A-plan rev2 bundles R-0A 54 + R-Q 48 + R-T 192 + R-S 30 with LAS P5r4 and
        soil P5r4S (revA2 line format; the Q-S1 boundary key with the diag soil record).
  A-P0  P0 / N0 on ``--keys``: A-S R-T / R-S keys whose hash changed and that the stored
        revA2 R-P0 did not reproduce (rules 5.2).
Gates before a run (exit 2): SH-1 seals; the run identity (one commit, empty code diff,
allowed dirty files, one thread); the LAS-b b0 preset; S-0 passed (same commit and tool
sha256) before every other bundle; S-C finished (456 lines) and SH-9 passed (rev1 RS1-9:
the S-C P0 hashes of the 19 keys with a stored ``fb_F3`` / ``fb_F4`` L job dict = the
stored L hashes) before S-D; the S judgement ``pass`` without an ask before A-S; A-S
finished before A-P0; job dicts (S-C = ``d1.jsonl``, A-S R-T / R-S = the stored L lines).
During a batch: identity or controller tag change, a settings mismatch (SH-4) or an S-0
hash mismatch (SH-2) stops everything; on S-D / A-S a K-S1 .. K-S5 problem stops the bundle
(SH-3; K-S4 checks the computed and the returned command of every deferral period, rev1
RS1-8); on S-D five pairs with an SC-2 / SC-F / SC-S / pair-level SC-R violation stop it
(SH-8, rev1 RS1-6); an error line runs once more (SH-5).

Usage (dynamics-dev python.exe, project root, PowerShell):
  python -I -B 04_scripts/04_hydraulic/coupled/s2_defer_targeted.py list
      [--bundle S-0 ..] [--out-dir <dir>] [--d1 <d1.jsonl>] [--diaga <diagA.jsonl>]
      [--rules-root <checkout>]
  python -I -B 04_scripts/04_hydraulic/coupled/s2_defer_targeted.py run --bundle S-0
      [--out-dir <dir>] [--workers 4] [--affinity HEX] [--keys K1,K2] [--limit N]
      [--d1 ..] [--reva2-dir ..] [--ref-rg ..] [--ref-reva-rg ..] [--ref-reva-rh ..]
      [--rules-root <checkout>]
Exit codes: 0 done, 1 a stop condition or run errors (run) / a count or reference mismatch
(list), 2 input error (seals, gates, dirty code, existing output, job dicts).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field, replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import las_revA_targeted as revA  # noqa: E402  (imports fb_targeted: thread variables first)
import numpy as np  # noqa: E402
import s2_defer_judge as sj  # noqa: E402

rev = revA.rev
fb = revA.fb
rj = revA.rj
diag = revA.diag
ajudge = revA.judge
ROOT = fb.ROOT
IDENTITY_FILES = {**revA.DIAG_IDENTITY_FILES,
                  "s2_defer_targeted.py": HERE / "s2_defer_targeted.py",
                  "s2_defer_judge.py": HERE / "s2_defer_judge.py"}
"""c2.py, the A-plan tools, the diagnosis recorder and the two S2D tools."""
OUT_NAMES = {"S-0": "s2d_S0.jsonl", "S-C": "s2d_SC.jsonl", "S-D": "s2d_SD.jsonl",
             "A-S": "s2d_AS.jsonl", "A-P0": "s2d_AP0.jsonl"}
BUNDLE_COUNTS = {"S-0": len(sj.S0_EXPECTED), "S-C": sj.SC_LINES, "A-S": sj.A_S_LINES}
DEFER_FIELDS = ("mode_defer_periods", "mode_defer_stroke_m", "mode_defer_rise_factor",
                "mode_defer_shadow")
TRACE_ATTRIBUTE = "_s2d_trace"
LOAD_TRACE_LEAD_S = 0.2
"""Load trace from the first entry evaluation - 0.2 s to the end of the run: every deferral of
the run (rev2 RS2-3: SC-T (d) per expired deferral, a later one after a LOC revocation too) and
the 1 s after it, on the S2D line and on the P0 line of the same key."""


# ------------------------------------------------------------------------------- S2D trace
@dataclass
class _Trace:
    """What the S2D update hook keeps for one controller (``controller.__dict__``)."""

    digest: object = field(default_factory=hashlib.sha256)
    t_rel_s: float | None = None
    first_check_t_s: float | None = None
    prefix_sha256: str | None = None
    defer_rows: list[dict] = field(default_factory=list)

    def to_record(self) -> dict:
        return {"t_rel_s": self.t_rel_s, "first_check_t_s": self.first_check_t_s,
                "prefix_sha256": self.prefix_sha256, "defer_rows": list(self.defer_rows)}


@dataclass(frozen=True)
class _SoilSnapshot:
    """Soil facts before one update (the soil state object is replaced at TOUCH entry)."""

    soil: object
    is_zone: bool
    checks: int
    soil_start_s: float | None
    is_loc: bool
    deferral: object


def _trace_of(controller) -> _Trace:
    trace = controller.__dict__.get(TRACE_ATTRIBUTE)
    if trace is None:
        trace = _Trace()
        controller.__dict__[TRACE_ATTRIBUTE] = trace
    return trace


def _snapshot(controller) -> _SoilSnapshot:
    soil = controller._state.soil  # read, never created here
    return _SoilSnapshot(
        soil=soil, is_zone=bool(controller._state.in_crawler_zone),
        checks=0 if soil is None else len(soil.defer_checks),
        soil_start_s=None if soil is None else soil.soil_mode_start_s,
        is_loc=bool(soil is not None and soil.is_liftoff_confirmed),
        deferral=None if soil is None else soil.defer)


def _is_release(controller, before: _SoilSnapshot, checks_now: int) -> bool:
    """A latch release before the LOC happened in this update (zone dropped, an entry
    evaluation, a soil-mode start or a deferral start)."""
    soil = controller._state.soil
    is_same = soil is before.soil
    if before.is_zone and not controller._state.in_crawler_zone:
        return True
    if checks_now > (before.checks if is_same else 0):
        return True
    if soil is None:
        return False
    new_start = soil.soil_mode_start_s is not None and (
        not is_same or soil.soil_mode_start_s != before.soil_start_s)
    new_deferral = soil.defer is not None and (not is_same or soil.defer is not before.deferral)
    return new_start or new_deferral


def computed_speeds(controller) -> np.ndarray:
    """The command computed in this update (before the output delay; rev1 RS1-8), read from
    the controller's output queue without touching it. Without a delay the computed command
    is the applied one (``_state.applied_output_m_s``, before the returned-command clip)."""
    state = controller._state
    latest = state.output_queue[-1] if state.output_queue else state.applied_output_m_s
    return np.array(latest, dtype=float)  # a copy: the controller's array is never changed


def _note_period(controller, trace: _Trace, before: _SoilSnapshot, t_s: float, command) -> None:
    prefix = trace.digest.hexdigest()  # the commands before this period
    speeds = np.asarray(command.leg_speed_m_s, dtype=float)
    trace.digest.update(speeds.tobytes())
    soil = controller._state.soil
    checks_now = 0 if soil is None else len(soil.defer_checks)
    is_new_check = checks_now > (before.checks if soil is before.soil else 0)
    if trace.first_check_t_s is None and is_new_check:
        trace.first_check_t_s, trace.prefix_sha256 = t_s, prefix
    if trace.t_rel_s is None and not before.is_loc and _is_release(controller, before,
                                                                   checks_now):
        trace.t_rel_s = t_s
    deferral = None if soil is None else soil.defer
    if deferral is not None and (deferral.is_active or deferral.end_s == t_s):
        trace.defer_rows.append({
            "t_s": t_s, "deferral_start_s": deferral.start_s, "active": deferral.is_active,
            "in_zone": bool(controller._state.in_crawler_zone),
            "min_command_m_s": float(speeds.min()),
            "min_computed_m_s": float(computed_speeds(controller).min()),
            "end_reason": None if deferral.end_reason is None else str(deferral.end_reason)})


def _trace_update_hook(original):
    def update(self, measurements):
        trace = _trace_of(self)
        before = _snapshot(self)
        command = original(self, measurements)
        _note_period(self, trace, before, float(measurements.t_s), command)
        return command

    return update


_INSTALLED: dict = {}


def install_trace_recorder(controller_class=None) -> None:
    """Wrap ``C2Controller.update`` (installed first: the innermost of the update hooks).

    Raises:
        RuntimeError: Installed twice in one process.
    """
    if "trace" in _INSTALLED:
        raise RuntimeError("s2_defer_targeted.install_trace_recorder: already installed")
    if controller_class is None:
        from outrigger_sim.control import c2

        controller_class = c2.C2Controller
    original = controller_class.update
    controller_class.update = _trace_update_hook(original)
    _INSTALLED["trace"] = (controller_class, "update", original)


def install_soil_candidate(values: dict, controller_class=None) -> None:
    """Wrap ``C2Controller.__init__`` so every controller of this worker gets the deferral
    fields ``values`` (``dataclasses.replace`` on ``config.soil``; nothing else changes).

    Raises:
        RuntimeError: Installed twice in one process.
    """
    if "soil" in _INSTALLED:
        raise RuntimeError("s2_defer_targeted.install_soil_candidate: already installed")
    if controller_class is None:
        from outrigger_sim.control import c2

        controller_class = c2.C2Controller
    original_init = controller_class.__init__

    def __init__(self, geometry, config=None, *args, **kwargs):
        if config is not None:
            config = replace(config, soil=replace(config.soil, **values))
        original_init(self, geometry, config, *args, **kwargs)

    controller_class.__init__ = __init__
    _INSTALLED["soil"] = (controller_class, "__init__", original_init)


def uninstall() -> None:
    """Undo both installs (tests only; workers never uninstall)."""
    for name in ("soil", "trace"):
        if name in _INSTALLED:
            cls, attribute, original = _INSTALLED.pop(name)
            setattr(cls, attribute, original)


# ------------------------------------------------------------------------------- jobs
def _s2d_entry(bundle: str, soil_record: bool = False) -> dict:
    return {"bundle": bundle, "candidate": sj.BUNDLE_SOIL_CANDIDATE[bundle],
            "soil_record": soil_record}


def _attach(jobs: list[dict], bundle: str, soil_record_keys=()) -> list[dict]:
    """New ids over the bundle and the ``s2d`` entry inside each ``rev`` entry."""
    out = []
    for index, job in enumerate(jobs):
        key = fb.fb_key({k: v for k, v in job.items() if k not in ("mask", "rev")})
        record = key in soil_record_keys
        entry = {**job["rev"], "id": index, "s2d": _s2d_entry(bundle, record)}
        if record:
            entry["record_diag"] = True  # las_phase_diag log for the diag soil block
        out.append({**job, "rev": entry})
    return out


def soil_group_jobs() -> list[dict]:
    """``d1_rows.jobs()`` of the rules-3 soil-response groups, in ``d1_rows`` order."""
    import d1_rows

    return [job for job in d1_rows.jobs() if job["d1"]["group"] in sj.SOIL_GROUP_COUNTS]


def _d1_pair_jobs(bundle: str, base: list[dict], mask: int | None) -> list[dict]:
    jobs = []
    for job in base:
        entry = rev._entry(bundle, "P0", "P0", record_done=False)
        jobs.append(rev._with_entry(job, {**entry, "record_done": False}, mask))
    return jobs


def s0_jobs(mask: int | None) -> list[dict]:
    jobs = (revA.bundle_jobs("R-0", ("P0",), mask)
            + revA.bundle_jobs(diag.BUNDLE, diag.CANDIDATE_NAMES, mask))
    return _attach(jobs, "S-0")


def sc_jobs(mask: int | None, keys=None) -> list[dict]:
    base = soil_group_jobs()
    if keys is not None:
        base = [job for job in base if fb.fb_key(job) in set(keys)]
    return _attach(_d1_pair_jobs("S-C", base, mask), "S-C")


def sd_jobs(mask: int | None, sc_lines: list[dict], keys=None) -> list[dict]:
    selected = sj.sd_selection(sc_lines)["keys"]
    if keys is not None:
        selected = [key for key in selected if key in set(keys)]
    by_key = {fb.fb_key(job): job for job in soil_group_jobs()}
    missing = [key for key in selected if key not in by_key]
    if missing:
        raise KeyError(f"S-D keys outside the soil groups: {missing[:5]}")
    return _attach(_d1_pair_jobs("S-D", [by_key[key] for key in selected], mask), "S-D")


def as_jobs(mask: int | None) -> list[dict]:
    jobs = []
    for bundle in sj.A_S_COUNTS:
        jobs += revA.bundle_jobs(bundle, ajudge.JUDGED_CANDIDATES, mask)
    return _attach(jobs, "A-S", soil_record_keys=(sj.Q_S1_KEY,))


def ap0_jobs(mask: int | None, keys: list[str]) -> list[dict]:
    return _attach(revA.bundle_jobs("R-P0", ("P0",), mask, keys), "A-P0")


# ------------------------------------------------------------------------------- worker
def rules_block() -> dict:
    return dict(zip(sj.RULES_FIELDS, sj.RULES_VALUES, strict=True))


def run_identity() -> dict:
    return {**fb.run_identity(files=IDENTITY_FILES), **rules_block()}


def _install_all(entry: dict) -> None:
    s2d_entry = entry["s2d"]
    install_trace_recorder()  # first: the innermost update hook
    revA._install_all(entry)  # L, preset, LAS-b candidate, recorders (D-A soil recorder last)
    install_soil_candidate({name: sj.SOIL_CANDIDATES[s2d_entry["candidate"]][name]
                            for name in DEFER_FIELDS})
    if s2d_entry["soil_record"] and entry["bundle"] != diag.BUNDLE:
        diag.install_soil_recorder()


def load_trace(plant, t_start_s: float | None) -> dict | None:
    """Smallest true leg force (1 ms plant rows) per control period ``(t - 0.1, t]`` from
    ``t_start_s - LOAD_TRACE_LEAD_S`` to the period holding the last plant row."""
    from harness_flow import COLUMN, TRUE_FORCE

    if t_start_s is None:
        return None
    rows = plant.flow_limiter.rows()
    if len(rows) == 0:
        return None
    t = rows[:, COLUMN["t"]]
    smallest = rows[:, TRUE_FORCE].min(axis=1)
    t0_s = round(t_start_s - LOAD_TRACE_LEAD_S, 10)
    periods = max(0, math.ceil((float(t[-1]) - t0_s) / sj.PERIOD_S - sj.TIME_TOLERANCE_S))
    out = []
    for index in range(periods + 1):
        t_end_s = round(t0_s + index * sj.PERIOD_S, 10)
        selected = (t > t_end_s - sj.PERIOD_S + sj.TIME_TOLERANCE_S) & (
            t <= t_end_s + sj.TIME_TOLERANCE_S)
        if selected.any():
            out.append([t_end_s, float(smallest[selected].min())])
    return {"t0_s": t0_s, "rule": "min over legs and 1 ms rows of (t - 0.1, t]", "rows": out}


def s2d_block(entry: dict, job: dict, controller, plant, identity: dict) -> dict:
    s2d_entry = entry["s2d"]
    meta = controller.meta()
    soil_meta = meta.get("soil") or {}
    margin = meta.get("slope_clearance_margin") or {}
    settings = {name: getattr(controller.config.soil, name) for name in DEFER_FIELDS}
    expected = {name: sj.SOIL_CANDIDATES[s2d_entry["candidate"]][name] for name in DEFER_FIELDS}
    trace = controller.__dict__.get(TRACE_ATTRIBUTE) or _Trace()
    return {**s2d_entry, "las_candidate": entry["candidate"], "key": fb.fb_key(job),
            "label": entry["label"], "origin_bundle": entry["bundle"], "settings": settings,
            "expected_settings": expected, "settings_match": settings == expected,
            "identity": identity, **rules_block(),
            "soil": {"enable": bool(controller.config.soil.enable),
                     "t_S_s": soil_meta.get("soil_mode_t_s"),
                     "soil_mode_start_stroke_m": soil_meta.get("soil_mode_start_stroke_m"),
                     "t_loc_s": soil_meta.get("t_loc_s"), "t_P_s": soil_meta.get("t_P_s"),
                     "push_m": soil_meta.get("push_m"), "defer": soil_meta.get("defer"),
                     "mode_starts": soil_meta.get("mode_starts"),
                     "deferrals": soil_meta.get("deferrals"),
                     "r4c30": bool(margin.get("flat_soil_margin_applied"))},
            "trace": trace.to_record(),
            "load_trace": load_trace(plant, trace.first_check_t_s or trace.t_rel_s)}


def _add_blocks(line: dict, entry: dict, job: dict, identity: dict) -> None:
    revA._add_blocks(line, entry, job, identity)
    plant, controller = fb._run_objects(job)
    if entry["s2d"]["soil_record"] and entry["bundle"] != diag.BUNDLE:
        line["diag"] = {"key": fb.fb_key(job),
                        **diag.diag_block(entry, line, line["las"], controller, plant,
                                          identity)}
    line["rev"].update(rules_block())
    line["s2d"] = s2d_block(entry, job, controller, plant, identity)


def run_s2d_job(job: dict) -> dict:
    """Worker: install the candidates and recorders, run, add the blocks."""
    t_start = time.perf_counter()
    entry = job.pop("rev")
    head = {"job": job, "rev": {**entry, "key": fb.fb_key(job)}, "s2d": entry["s2d"]}
    try:
        import run_v5  # sys.path and thread variables first

        identity = run_identity()
        _install_all(entry)
    except Exception as exc:  # recorded as an error line; the batch decides (SH-5)
        return {**head, "error": f"install: {exc!r}", "tb": traceback.format_exc()[-3000:],
                "wall_s": round(time.perf_counter() - t_start, 1)}
    line = run_v5.run_one(job)
    if "error" in line:
        return {**line, "rev": head["rev"], "s2d": head["s2d"]}
    try:
        _add_blocks(line, entry, job, identity)
    except Exception as exc:
        return {**head, "error": f"metrics: {exc!r}", "tb": traceback.format_exc()[-3000:],
                "wall_s": round(time.perf_counter() - t_start, 1)}
    line["rev"]["id"] = entry["id"]
    return line


# ------------------------------------------------------------------------------- batch checks
@dataclass
class CheckContext:
    """What the in-batch checks compare against (S-C lines, stored revA2 P5r4 lines)."""

    sc_by_key: dict = field(default_factory=dict)
    random_keys: set = field(default_factory=set)
    reva2_p5r4: dict = field(default_factory=dict)
    k_s1_targets: set = field(default_factory=set)


def line_problems(record: dict, bundle: str, context: CheckContext) -> tuple[list[str], str]:
    """(problems, stop kind) of one finished line."""
    problems = sj.settings_problems(record) + sj.rules_problems(record)
    if problems:
        return problems, "SH-4"
    if bundle == "S-0":
        expected = sj.S0_EXPECTED.get(sj.s0_expected_key(record))
        if record["commands_sha256"] != expected:
            return [f"S-0 {sj.s0_expected_key(record)} hash {record['commands_sha256']} != "
                    f"{expected}"], "SH-2"
        return [], ""
    if bundle == "S-D":
        base = context.sc_by_key.get(sj.key_of(record))
        if base is None:
            return [f"S-D {sj.key_of(record)}: no S-C line"], "SH-4"
        return sj.pair_k_problems(record, base, sj.key_of(record) in context.random_keys), "SH-3"
    if bundle == "A-S":
        rev_entry = rj.rev_of(record)
        index = (rev_entry["bundle"], rev_entry["label"], rev_entry["key"])
        found = sj.k_s4_problems(record) + sj.k_s5_problems(record)
        stored = context.reva2_p5r4.get(index)
        if index in context.k_s1_targets and (
                stored is None or stored["commands_sha256"] != record["commands_sha256"]):
            found.append(f"K-S1 {index}: hash changed")
        return found, "SH-3"
    return [], ""


def make_checker(context: CheckContext):
    """``check(record, bundle, state, stored, k3_keys, identity)`` of ``rev.run_batch``."""
    sc_pairs: set[str] = set()

    def check(record, bundle, state, stored, k3_keys, current_identity) -> None:
        s2d_entry = sj.s2d_of(record)
        problems = fb.identity_mismatch(s2d_entry.get("identity"), current_identity)
        if problems:
            state.stop = f"run identity changed during the batch: {problems[:3]}"
            return
        tags = ajudge.tag_problems(record)
        if tags:
            state.stop = f"{sj.key_of(record)}: {tags}"
            return
        try:
            found, kind = line_problems(record, s2d_entry["bundle"], context)
            if s2d_entry["bundle"] in ("S-D", "A-S"):
                # rev2 RS2-4: undecidable in the judge, not a stop; shown as the batch runs
                for text in sj.history_problems(record, is_candidate=True):
                    print(f"SH-4 undecidable (RS2-4) {text}", flush=True)
            if s2d_entry["bundle"] == "S-D" and not found:
                _count_sc_pair(record, context, sc_pairs, state)
        except rj.MissingField as exc:
            state.stop = f"SH-4 {sj.key_of(record)}: missing {exc}"
            return
        if found:
            print(f"{kind} {sj.key_of(record)}: {found}", flush=True)
            state.stop = f"{kind} {sj.key_of(record)}: {found[:3]}"

    return check


def _count_sc_pair(record: dict, context: CheckContext, pairs: set[str], state) -> None:
    """SH-8: five S-D pairs with an SC-2 / SC-F / SC-S / pair-level SC-R violation (READY dt
    > +5.0 s, rev1 RS1-6) stop the bundle."""
    pair = sj.sc_pair_record(record, context.sc_by_key[sj.key_of(record)])
    if sj.is_sh8_pair(pair):
        pairs.add(sj.key_of(record))
        if len(pairs) >= sj.SH8_PAIRS:
            state.stop = f"SH-8 {len(pairs)} pairs with SC-2 / SC-F / SC-S / SC-R violations"


# ------------------------------------------------------------------------------- gates
@dataclass
class Inputs:
    """Paths of the stored inputs (main checkout files that are not in git)."""

    out_dir: Path
    d1: Path
    diaga: Path
    reva2_dir: Path
    ref_rg: Path
    ref_reva_rg: Path
    ref_reva_rh: Path
    rules_root: Path


def bundle_lines(inputs: Inputs, bundle: str) -> list[dict]:
    path = inputs.out_dir / OUT_NAMES[bundle]
    return rj.read_lines(path) if path.exists() else []


def stale_problems(lines: list[dict], current: dict, name: str) -> list[str]:
    stale = [line for line in lines
             if any((sj.s2d_of(line).get("identity") or {}).get(field_name)
                    != current.get(field_name) for field_name in ("git_head", "sha256"))]
    return [f"{name}: {len(stale)} lines from another commit or tool sha256"] if stale else []


def s0_gate_problems(inputs: Inputs, identity: dict) -> list[str]:
    lines = bundle_lines(inputs, "S-0")
    result = sj.judge_s0(lines)
    problems = [] if result["status"] == sj.STATUS_PASS else [
        f"S-0 not passed: {result['status']}, ran {result['ran']}, errors {result['errors']}"]
    return problems + stale_problems(lines, identity, "S-0")


def sc_gate_problems(inputs: Inputs, identity: dict) -> list[str]:
    lines = bundle_lines(inputs, "S-C")
    finished = sj.by_key(sj.lines_of(lines, "S-C"))
    problems = stale_problems(lines, identity, "S-C")
    if len(finished) != sj.SC_LINES:
        problems.append(f"S-C has {len(finished)} finished keys, expected {sj.SC_LINES}")
    return problems


def s_gate_problems(inputs: Inputs, identity: dict) -> list[str]:
    lines = bundle_lines(inputs, "S-C") + bundle_lines(inputs, "S-D")
    result = sj.judge_s(lines)
    problems = stale_problems(lines, identity, "S-C / S-D")
    if result["status"] != sj.STATUS_PASS or result.get("asks"):
        problems.append(f"S judgement {result['status']}, asks {result.get('asks')}")
    if not sj.sc_census(lines)["Q-S2_holds"]:
        problems.append("SH-6 Q-S2 missed: ask before A-S")
    return problems


def sh9_gate_problems(inputs: Inputs, stored: dict) -> list[str]:
    """rev1 RS1-9 SH-9 after S-C, before S-D: the S-C P0 hashes of the 19 keys with a stored
    FB L job dict are the stored L hashes."""
    result = sj.sh9_check(bundle_lines(inputs, "S-C"), stored)
    if result["status"] == sj.STATUS_PASS:
        return []
    return [f"SH-9 {result['status']}: {result.get('problems') or result.get('reason')}"]


def gate_problems(bundle: str, inputs: Inputs, identity: dict,
                  stored: dict | None = None) -> list[str]:
    """Rules 3 order: S-0 -> S-C -> SH-9 -> S-D -> S judgement -> A-S -> A-P0.

    ``stored`` is ``las_rev_judge.load_stored()`` (loaded here when None and needed)."""
    if bundle == "S-0":
        return []
    problems = s0_gate_problems(inputs, identity)
    if bundle in ("S-D", "A-S", "A-P0"):
        problems += sc_gate_problems(inputs, identity)
        problems += sh9_gate_problems(inputs, stored if stored is not None else rj.load_stored())
    if bundle in ("A-S", "A-P0"):
        problems += s_gate_problems(inputs, identity)
    if bundle == "A-P0" and not bundle_lines(inputs, "A-S"):
        problems.append("A-P0 needs the A-S file")
    return problems


def d1_job_problems(jobs: list[dict], d1_path: Path) -> list[str]:
    """S-C / S-D job dicts = the ``d1.jsonl`` line's ``job`` (rules 3 S-C)."""
    problem = sj.file_problem(d1_path, sj.D1_SHA256)
    if problem is not None:
        return [problem]
    stored = {fb.fb_key(line["job"]): line["job"] for line in rj.read_lines(d1_path)}
    problems = []
    for job in jobs:
        key = fb.fb_key(job)
        if key not in stored:
            problems.append(f"{key}: not in d1.jsonl")
        elif rev._comparable_job(job) != rev._comparable_job(stored[key]):
            problems.append(f"{key}: job dict differs from d1.jsonl")
    return problems


def context_for(bundle: str, inputs: Inputs) -> CheckContext:
    context = CheckContext()
    if bundle == "S-D":
        sc_lines = bundle_lines(inputs, "S-C")
        context.sc_by_key = sj.by_key(sj.lines_of(sc_lines, "S-C"))
        context.random_keys = set(sj.sd_selection(sc_lines)["random_keys"])
    if bundle == "A-S":
        context.reva2_p5r4 = sj.reva2_p5r4(sj.load_reva2(inputs.reva2_dir))
        context.k_s1_targets = sj.k_s1_targets(context.reva2_p5r4)
    return context


def ap0_keys(inputs: Inputs, stored: dict) -> list[str]:
    """A-S R-T / R-S keys whose hash differs from the stored L and that the stored revA2
    R-P0 did not reproduce (rules 5.2)."""
    as_lines = sj.lines_of(bundle_lines(inputs, "A-S"), "A-S")
    changed = rj.changed_keys(as_lines, stored)
    reproduced = {sj.key_of(line) for line in rj.read_lines(inputs.reva2_dir / "revA_RP0.jsonl")
                  if not rj.is_error(line)}
    return sorted(changed - reproduced)


def bundle_jobs(bundle: str, inputs: Inputs, mask: int | None, keys=None,
                stored: dict | None = None) -> list[dict]:
    if bundle == "S-0":
        return s0_jobs(mask)
    if bundle == "S-C":
        return sc_jobs(mask, keys)
    if bundle == "S-D":
        return sd_jobs(mask, bundle_lines(inputs, "S-C"), keys)
    if bundle == "A-S":
        return as_jobs(mask)
    if bundle == "A-P0":
        keys = keys if keys is not None else ap0_keys(inputs, stored or rj.load_stored())
        return ap0_jobs(mask, keys) if keys else []
    raise ValueError(f"unknown bundle {bundle!r}")


def job_problems(bundle: str, jobs: list[dict], inputs: Inputs, stored: dict) -> list[str]:
    if bundle in ("S-C", "S-D"):
        return d1_job_problems(jobs, inputs.d1)
    if bundle in ("A-S", "A-P0"):
        return rev.job_dict_problems(jobs, stored)
    return []


# ------------------------------------------------------------------------------- CLI
def _add_input_args(parser) -> None:
    parser.add_argument("--out-dir", type=Path, default=sj.SOIL_DEFER_DIR,
                        help="soil_defer folder (the main checkout's from a worktree)")
    parser.add_argument("--d1", type=Path, default=sj.D1_PATH)
    parser.add_argument("--diaga", type=Path, default=sj.DIAGA_PATH)
    parser.add_argument("--reva2-dir", type=Path, default=ajudge.REVA2_DIR)
    parser.add_argument("--ref-rg", type=Path, default=ajudge.DEFAULT_REFERENCE_RG)
    parser.add_argument("--ref-reva-rg", type=Path, default=ajudge.DEFAULT_STORED_REVA_RG)
    parser.add_argument("--ref-reva-rh", type=Path, default=ajudge.DEFAULT_STORED_REVA_RH)
    parser.add_argument("--rules-root", type=Path, default=ROOT,
                        help="checkout whose verif_matrix holds the sealed S2D rules")


def _parse_args(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list", help="runs of the bundles and the stored-input checks")
    listing.add_argument("--bundle", nargs="+", choices=sj.BUNDLES, default=list(sj.BUNDLES))
    _add_input_args(listing)
    run = sub.add_parser("run", help="run a bundle into a new file")
    run.add_argument("--bundle", required=True, choices=sj.BUNDLES)
    _add_input_args(run)
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--affinity", default=None, help="hex mask, set in every worker")
    run.add_argument("--keys", default=None, help="comma-separated keys (S-C / S-D / A-P0)")
    run.add_argument("--limit", type=int, default=None, help="first N runs only")
    return parser.parse_args(argv)


def _inputs_of(args) -> Inputs:
    return Inputs(args.out_dir, args.d1, args.diaga, args.reva2_dir, args.ref_rg,
                  args.ref_reva_rg, args.ref_reva_rh, args.rules_root)


def _s0_reference_problems(inputs: Inputs) -> list[str]:
    """The diagA file is the stored one and holds the three S-0 diagA hashes."""
    problem = sj.file_problem(inputs.diaga, sj.DIAGA_SHA256)
    if problem is not None:
        return [problem]
    found = {(rj.rev_of(line)["bundle"], sj.key_of(line), rj.rev_of(line)["label"]):
             line["commands_sha256"] for line in rj.read_lines(inputs.diaga)}
    return [f"S-0 {index}: diagA.jsonl {found.get(index)} != {sha}"
            for index, sha in sj.S0_EXPECTED.items()
            if index[0] == diag.BUNDLE and found.get(index) != sha]


def _d1_census(d1_path: Path) -> tuple[int, int]:
    """(soil-group lines, soil-mode lines among them) of ``d1.jsonl`` (rules 0 / 3)."""
    lines = rj.read_lines(d1_path)
    soil = [line for line in lines if line["job"]["d1"]["group"] in sj.SOIL_GROUP_COUNTS]
    return len(soil), sum(1 for line in soil if sj.has_soil_event(line))


def list_bundles(bundles, inputs: Inputs) -> tuple[list[str], list[str]]:
    report, problems = [], []
    problems += sj.seal_problems(inputs.rules_root)
    stored = rj.load_stored()
    for bundle in bundles:
        if bundle == "S-D" and not bundle_lines(inputs, "S-C"):
            groups, soil = _d1_census(inputs.d1)
            report.append(f"S-D: needs the S-C file; estimate from d1.jsonl (LAS-less "
                          f"controller): {soil} soil-mode + {sj.SD_RANDOM_KEYS} = "
                          f"{soil + sj.SD_RANDOM_KEYS} of {groups}")
            continue
        if bundle == "A-P0" and not bundle_lines(inputs, "A-S"):
            report.append("A-P0: keys from the A-S file (changed, not in revA2 R-P0)")
            continue
        jobs = bundle_jobs(bundle, inputs, None, stored=stored)
        report.append(f"{bundle}: {len(jobs)} runs")
        expected = BUNDLE_COUNTS.get(bundle)
        if expected is not None and len(jobs) != expected:
            problems.append(f"{bundle}: {len(jobs)} runs, expected {expected}")
        problems += job_problems(bundle, jobs, inputs, stored)
        if bundle == "S-C":
            counts: dict[str, int] = {}
            for job in jobs:
                counts[job["d1"]["group"]] = counts.get(job["d1"]["group"], 0) + 1
            report.append(f"  groups {counts}")
            if counts != sj.SOIL_GROUP_COUNTS:
                problems.append(f"S-C groups {counts} != {sj.SOIL_GROUP_COUNTS}")
        if bundle == "S-0":
            problems += _s0_reference_problems(inputs)
    return report, problems


def _prepare(args) -> tuple[list[dict], Path, dict, dict, CheckContext]:
    """Jobs, output path, stored lines, identity and check context (raises on input errors)."""
    inputs = _inputs_of(args)
    path = inputs.out_dir / OUT_NAMES[args.bundle]
    problem = rev.out_path_problem(path, sj.SOIL_DEFER_DIR)
    if problem is not None:
        raise ValueError(problem)
    import run_v5  # noqa: F401  (puts 03_src on sys.path before the preset check)

    fb.check_preset_las()
    identity = run_identity()
    problems = rev.identity_problems(identity)
    if problems:
        raise ValueError(f"run identity (SH-4): {problems}")
    stored = rj.load_stored()
    problems = gate_problems(args.bundle, inputs, identity, stored)
    if problems:
        raise ValueError(f"gates before {args.bundle}: {problems[:5]}")
    if args.bundle == "S-0":
        problems = _s0_reference_problems(inputs)
        if problems:
            raise ValueError(f"S-0 references: {problems}")
    keys = args.keys.split(",") if args.keys else None
    mask = None if args.affinity is None else int(args.affinity, 16)
    jobs = bundle_jobs(args.bundle, inputs, mask, keys, stored)
    problems = job_problems(args.bundle, jobs, inputs, stored)
    if problems:
        raise ValueError(f"job dicts: {problems[:5]}")
    jobs = jobs if args.limit is None else jobs[: args.limit]
    if not jobs:
        raise ValueError("no runs selected")
    return jobs, path, stored, identity, context_for(args.bundle, inputs)


def _run_command(args) -> int:
    try:
        jobs, path, stored, identity, context = _prepare(args)
    except (KeyError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"input error: {exc!r}")
        print(json.dumps({"bundle": args.bundle, "stop": "input", "reason": str(exc)}))
        return 2
    print(f"run identity: {identity['git_head']} dirty {identity['git_dirty']} "
          f"code_diff {identity['code_diff_sha256'][:12]} rules {sj.RULES_S2D_SHA256[:12]}",
          flush=True)
    print(f"{args.bundle}: {len(jobs)} runs -> {path}", flush=True)
    state = rev.run_batch(jobs, path, args.workers, args.bundle, stored, identity,
                          worker=run_s2d_job, check=make_checker(context),
                          whole_bundle_rerun=())
    summary = {"bundle": args.bundle, "out": str(path), "runs": state.runs,
               "errors": state.errors, "skipped": state.skipped, "stop": state.stop}
    if args.bundle == "S-0":
        summary["S-0"] = sj.judge_s0(rj.read_lines(path))["status"]
    print(json.dumps(summary))
    return 1 if state.stop or state.skipped else 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    problems = sj.seal_problems(args.rules_root)
    if problems:
        print(f"input error (SH-1): {problems}")
        print(json.dumps({"stop": "SH-1", "reasons": problems}))
        return 2
    if args.command == "run":
        return _run_command(args)
    try:
        lines, problems = list_bundles(args.bundle, _inputs_of(args))
    except (KeyError, OSError, ValueError) as exc:
        print(f"input error: {exc!r}")
        return 2
    print("\n".join(lines))
    for problem in problems:
        print(f"MISMATCH {problem}")
    print(json.dumps({"bundles": args.bundle, "problems": len(problems)}))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
