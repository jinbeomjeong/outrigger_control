"""LAS-b revision targets on the reduced harness: P5 (beta 4.5), P3 (n_min 8), P53 (both).

Rules: ``06_analysis/02_control/verif_matrix/las_rev_targeted_rules.md`` (control-expert,
sealed; LF sha256 ``las_rev_judge.RULES_SHA256``) with addendum rev1 (``RULES_REV1_SHA256``,
both checked). The rules text wins where this code differs;
``run`` and ``list`` stop with exit 2 when the rules or their ``.sha256`` are missing or differ.

Candidates (rules 1.2, ``las`` = ``C2Config.with_10hz_d1().liftoff_approach_slow``, b0):
  P0  the preset as it is (no override at all)
  P5  ``replace(las, light_leg_fraction_of_F_min=4.5)``
  P3  ``replace(las, min_active_periods=8)``
  P53 both
A candidate is applied in the worker by wrapping ``C2Controller.__init__``: a config whose
LAS-b is the b0 preset gets the candidate settings (``dataclasses.replace``), one that already
has them is kept, any other LAS-b raises (the run becomes an error line). The preset itself and
``fb_targeted.check_preset_las`` are not touched; the old ``las_targeted.install`` wrapper is
never installed. Every line records the settings the run's controller really used (K-4).

Bundles (rules 3), output ``06_analysis/03_hydraulic/coupled/v5/las/rev/rev_R<bundle>.jsonl``
(opened with ``"x"``, no resume):
  R-0   6 P0 bit tests (rules 7.1): T-1 K1 VB e0 / K3 V0 e0 plain, D-b A-1 (K3 VB / V0
        e0.002) with the TOUCH budget LT c1 j0 and the D-b recorder, F-3 diag-psa-soil VB,
        verdict R12 VB. Each hash must equal the stored 64-character value (H-2: stop).
  R-G   (ga) 30 grid points (``las_phase_diag`` D-b: TOUCH-only budget, period record) x
        P5, P3, P53 = 90; line label ``<candidate>-LT-c<centre>-j<j>``.
  R-T   (na) T-1 8 + T-2 184 keys x the candidates given (those that passed (ga)).
  R-S   (da) F-3 16 + F-4 14 jobs (``fb_targeted.bundle_base_jobs``) x the candidates given.
  R-P0  P0 on the union of the keys whose hash changed in the R-T / R-S files (rules 7.3).
  R-X   P0 with the DONE record on the keys of the C-4 exception claims (rules 6), or --keys.
Job dicts of R-T / R-S are compared with the stored L lines' ``job`` first (H-4: exit 2).
R-T / R-S / R-P0 / R-X also need an ``rev_RG*.jsonl`` and every earlier bundle line
(``rev_RG*``, ``rev_RT*``, ``rev_RS*``, ``rev_RP0*``) from the current commit and tool sha256
(exit 2 otherwise). A line whose ``controller_tag`` is not ``final_C4G2_LAS`` /
``final_C4G2_P3_LAS`` stops the batch.

DONE record (rules 4.2, record only; on in every bundle unless ``--no-done-record``): from the
first LOC (soil response off: the first LEVEL step) to the first READY + 1 s, one
``done_trace`` row per LEVEL / DONE period with t_s, phase, loc_ok, ref_on_target,
deviation_deg, attitude_in_band, clearance_done, twist_path, twist_ok, complete_now,
diff_sink_hold, reapproaching, complete_since_s; and ``done_clock`` {t_first_done_s,
t_loc_last_before_done_s, clock_starts_s, resets [{t_s, names}], loss_s, ...}. The values are
the return values of the controller's own calls, taken on their way out
(``_update_completion``, ``_is_reference_on_target``, ``_completion_deviation_rad``,
``_is_clearance_done``, ``_is_twist_condition_met``, ``_is_diff_sink_holding``,
``_reapproaching_legs``); no method is called a second time (``_is_twist_condition_met`` changes
state). A field whose call did not happen in the period is None (``_update_completion``
returning early before the LOC: ``loc_ok`` False, the rest None).

During a batch (``las_rev_judge`` checks on each finished line):
  H-2 R-0 hash mismatch -> stop everything; H-3 a K-1 .. K-4 mismatch -> no more jobs of that
  candidate; H-8 a candidate with 5 pairs with a C-2 type violation -> no more of its jobs;
  H-7 an error line -> the job once more (R-G: stop, the 30 lines are re-run as a whole);
  a run identity change -> stop.
Line = the ``run_v5`` line + ``las`` (``fb_targeted.las_block_from_meta`` with the candidate
name and ``params.n_min``) + ``rev`` {bundle, candidate, label, key, grid_point, identity,
rules_sha256, settings, expected_settings, settings_match, controller_tag, record flags}
(+ ``diag`` for grid lines, + ``done_trace`` / ``done_clock``).

Usage (dynamics-dev python.exe, project root, PowerShell):
  python -I -B 04_scripts/04_hydraulic/coupled/las_rev_targeted.py list [--bundle R-0 ..]
      [--candidates P5,P3]
  python -I -B 04_scripts/04_hydraulic/coupled/las_rev_targeted.py run --bundle R-G
      [--candidates P5,P3,P53] [--workers 4] [--affinity HEX] [--out <jsonl>] [--keys K1,K2]
      [--from <jsonl> ..] [--limit N] [--no-done-record]
Exit codes: 0 done, 1 a stop condition or run errors (run) / a count or reference mismatch
(list), 2 input error (rules seal, dirty code, existing --out, job dict mismatch).
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
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fb_targeted as fb  # noqa: E402  (sets the thread variables before numpy loads)
import las_rev_judge as judge  # noqa: E402
import numpy as np  # noqa: E402

ROOT = fb.ROOT
REV_DIR = judge.REV_DIR
IDENTITY_FILES = {**fb.IDENTITY_FILES,
                  "las_phase_diag.py": HERE / "las_phase_diag.py",
                  "las_rev_targeted.py": HERE / "las_rev_targeted.py",
                  "las_rev_judge.py": HERE / "las_rev_judge.py"}
"""Rules 4.1: c2.py, this tool, the judge, las_phase_diag, fb_targeted, las_targeted."""
ALLOWED_DIRTY = (".gitattributes", "00_docs/decision_log.md")
"""Rules 4.1: the only dirty (tracked, uncommitted) files a run may have."""

BUNDLES = judge.BUNDLES
BUNDLE_CANDIDATES = {"R-0": ("P0",), "R-G": judge.GRID_CANDIDATES, "R-T": None, "R-S": None,
                     "R-P0": ("P0",), "R-X": ("P0",)}
"""None: the candidates must be given (those that passed (ga), rules 3 order)."""
BUNDLE_COUNTS = {"R-0": 6, "R-G": 90}
GRID_KEYS = ("D1|H-R-A|rigid+J1@FR|T|diag-op|K3|VB|e0.002",
             "D1|H-R-A|rigid+J1@FR|T|diag-op|K3|V0|e0.002")
R0_GRID_POINT = ("1", 0)
PHASE_LEVEL_DONE = ("level", "done")
PHASE_READY = "ready"
PHASE_DONE = "done"
READY_TAIL_S = 1.0
TIME_TOLERANCE_S = 1e-9
DONE_LOG_ATTRIBUTE = "_las_rev_done"


# ------------------------------------------------------------------------------- candidates
@dataclass(frozen=True)
class RevCandidate:
    """One revision candidate of rules 1.2 (``beta``, ``n_min`` over the b0 preset)."""

    name: str
    beta: float
    n_min: int

    def settings_from(self, preset_settings):
        """The candidate's ``LiftoffApproachSlowSettings`` (P0: the preset unchanged)."""
        if self.name == "P0":
            return preset_settings
        return replace(preset_settings, light_leg_fraction_of_F_min=self.beta,
                       min_active_periods=self.n_min)


CANDIDATES = {name: RevCandidate(name, beta, n_min)
              for name, (beta, n_min) in judge.CANDIDATE_VALUES.items()}


def preset_las_settings():
    from outrigger_sim.control import c2

    return c2.C2Config().with_10hz_d1().liftoff_approach_slow


def candidate_config(config, candidate: RevCandidate, preset_settings):
    """``config`` with the candidate's LAS-b (rules 7.2).

    Raises:
        RuntimeError: LAS-b on with settings that are neither b0 nor the candidate's.
    """
    settings = config.liftoff_approach_slow
    target = candidate.settings_from(preset_settings)
    if not settings.enable or settings == target:
        return config
    if settings != preset_settings:
        raise RuntimeError(f"LAS-b settings are neither b0 nor {candidate.name}: {settings}")
    return replace(config, liftoff_approach_slow=target)


_INSTALLED: dict = {}


def install_candidate(candidate: RevCandidate, controller_class=None,
                      preset_settings=None) -> None:
    """Wrap ``C2Controller.__init__`` so every controller of this worker gets the candidate.

    Raises:
        RuntimeError: Installed twice in one process.
    """
    if "init" in _INSTALLED:
        raise RuntimeError("las_rev_targeted.install_candidate: already installed")
    if controller_class is None:
        from outrigger_sim.control import c2

        controller_class = c2.C2Controller
    preset_settings = preset_settings or preset_las_settings()
    original_init = controller_class.__init__

    def __init__(self, geometry, config=None, *args, **kwargs):
        if config is not None:
            config = candidate_config(config, candidate, preset_settings)
        original_init(self, geometry, config, *args, **kwargs)

    controller_class.__init__ = __init__
    _INSTALLED["init"] = (controller_class, original_init)


# ------------------------------------------------------------------------------- DONE record
@dataclass
class DoneLog:
    """What the DONE hooks keep for one controller (``controller.__dict__[...]``)."""

    rows: list[dict] = field(default_factory=list)
    loc_onsets_s: list[float] = field(default_factory=list)
    was_loc: bool = False
    t_first_loc_s: float | None = None
    t_trace_start_s: float | None = None
    t_first_ready_s: float | None = None
    t_first_done_s: float | None = None


_PERIOD: dict = {}
"""Return values of the running period's calls (one controller at a time in a worker)."""
_SCOPE = {"level": False, "completion": False, "after_completion": False}
CAPTURED_METHODS = {
    "_is_reference_on_target": ("ref_on_target", "completion"),
    "_completion_deviation_rad": ("deviation_rad", "completion"),
    "_is_clearance_done": ("clearance_done", "completion"),
    "_is_twist_condition_met": ("twist_condition", "completion"),
    "_is_diff_sink_holding": ("diff_sink_hold", "after_completion"),
    "_reapproaching_legs": ("reapproaching", "level"),
}
"""Method -> (record name, scope): the first return value inside the scope is kept."""


def _done_log_of(controller) -> DoneLog:
    log = controller.__dict__.get(DONE_LOG_ATTRIBUTE)
    if log is None:
        log = DoneLog()
        controller.__dict__[DONE_LOG_ATTRIBUTE] = log
    return log


def _captured_value(name: str, result):
    if name == "reapproaching":
        return bool(np.any(result))
    if name == "deviation_rad":
        return float(result)
    return bool(result)


def _capture_hook(original, name: str, scope: str):
    def hooked(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        values = _PERIOD.setdefault("values", {})
        if _SCOPE[scope] and name not in values:
            values[name] = _captured_value(name, result)
        return result

    return hooked


def _completion_hook(original):
    def update_completion(self, reading, filtered_clearance_m):
        _SCOPE["completion"] = True
        try:
            result = original(self, reading, filtered_clearance_m)
        finally:
            _SCOPE["completion"] = False
        _PERIOD["completion"] = {
            "returned": bool(result), "since_after": self._state.complete_since_s,
            "twist_load_N": float(self.geometry.twist_vector @ reading.cylinder_force_N),
            "phase": str(self._state.phase)}
        _SCOPE["after_completion"] = True
        return result

    return update_completion


def _level_hook(original):
    def level_step(self, reading):
        _SCOPE["level"] = True
        try:
            result = original(self, reading)
        finally:
            _SCOPE["level"] = False
            _SCOPE["after_completion"] = False
        _PERIOD["since_after_level"] = self._state.complete_since_s
        _PERIOD["level_ran"] = True
        return result

    return level_step


def _is_loc(controller) -> bool:
    soil = controller._state.soil  # read, never created
    return bool(soil is not None and soil.is_liftoff_confirmed)


def done_row(t_s: float, phase_before: str, phase: str, period: dict, thresholds) -> dict:
    """One ``done_trace`` row from the period's captured values (rules 4.2).

    Args:
        thresholds: ``done_attitude_rad`` and ``done_twist_N`` of the controller.
    """
    values = period.get("values", {})
    completion = period.get("completion")
    row = {"t_s": t_s, "phase_before": phase_before, "phase": phase,
           "level_step": bool(period.get("level_ran")), "loc_ok": None, "ref_on_target": None,
           "deviation_deg": None, "attitude_in_band": None, "clearance_done": None,
           "twist_path": None, "twist_ok": None, "complete_now": None,
           "diff_sink_hold": values.get("diff_sink_hold"),
           "reapproaching": values.get("reapproaching"),
           "complete_since_s": period.get("since_after_level")}
    if completion is None:
        return row
    is_loc_ok = "ref_on_target" in values  # an early return calls no sub-condition
    row["loc_ok"] = is_loc_ok
    if not is_loc_ok:
        row["complete_now"] = False
        return row
    deviation = values.get("deviation_rad")
    is_relax = "twist_condition" in values
    twist_ok = values["twist_condition"] if is_relax else (
        abs(completion["twist_load_N"]) < thresholds.done_twist_N)
    row.update(ref_on_target=values["ref_on_target"],
               deviation_deg=None if deviation is None else float(np.degrees(deviation)),
               attitude_in_band=None if deviation is None
               else deviation < thresholds.done_attitude_rad,
               clearance_done=values.get("clearance_done"),
               twist_path="relax" if is_relax else "plain", twist_ok=bool(twist_ok),
               complete_now=completion["since_after"] is not None)
    return row


def _note_period(controller, t_s: float, phase_before: str) -> None:
    log = _done_log_of(controller)
    phase = str(controller._state.phase)
    is_loc = _is_loc(controller)
    if is_loc and not log.was_loc:
        log.loc_onsets_s.append(t_s)
        log.t_first_loc_s = t_s if log.t_first_loc_s is None else log.t_first_loc_s
    log.was_loc = is_loc
    if phase == PHASE_DONE and log.t_first_done_s is None:
        log.t_first_done_s = t_s
    if log.t_trace_start_s is None:
        is_soil_off = not controller.config.soil.enable
        if is_loc or (is_soil_off and _PERIOD.get("level_ran")):
            log.t_trace_start_s = t_s
        else:
            return
    if log.t_first_ready_s is not None and t_s > log.t_first_ready_s + READY_TAIL_S + 1e-9:
        return
    if phase == PHASE_READY and log.t_first_ready_s is None:
        log.t_first_ready_s = t_s
    if phase_before in PHASE_LEVEL_DONE or phase in PHASE_LEVEL_DONE:
        log.rows.append(done_row(t_s, phase_before, phase, _PERIOD, controller.config.thresholds))


def _update_hook(original):
    def update(self, measurements):
        _PERIOD.clear()
        for name in _SCOPE:
            _SCOPE[name] = False
        phase_before = str(self._state.phase)
        command = original(self, measurements)
        _note_period(self, float(measurements.t_s), phase_before)
        return command

    return update


def install_done_recorder(controller_class=None) -> None:
    """Patch the controller class (outermost ``update``) with the DONE capture hooks.

    Raises:
        RuntimeError: Installed twice in one process.
    """
    if "done" in _INSTALLED:
        raise RuntimeError("las_rev_targeted.install_done_recorder: already installed")
    if controller_class is None:
        from outrigger_sim.control import c2

        controller_class = c2.C2Controller
    cls = controller_class
    originals = {name: getattr(cls, name) for name in
                 ("update", "_level_step", "_update_completion", *CAPTURED_METHODS)}
    for method, (name, scope) in CAPTURED_METHODS.items():
        setattr(cls, method, _capture_hook(originals[method], name, scope))
    cls._update_completion = _completion_hook(originals["_update_completion"])
    cls._level_step = _level_hook(originals["_level_step"])
    cls.update = _update_hook(originals["update"])
    _INSTALLED["done"] = (cls, originals)


def uninstall() -> None:
    """Undo both installs (tests only; workers never uninstall)."""
    if "done" in _INSTALLED:
        cls, originals = _INSTALLED.pop("done")
        for name, method in originals.items():
            setattr(cls, name, method)
    if "init" in _INSTALLED:
        cls, original_init = _INSTALLED.pop("init")
        cls.__init__ = original_init
    _PERIOD.clear()


RESET_FALSE_NAMES = ("loc_ok", "ref_on_target", "attitude_in_band", "clearance_done",
                     "twist_ok")
RESET_TRUE_NAMES = ("diff_sink_hold", "reapproaching")


def reset_names(row: dict) -> list[str]:
    """Sub-conditions behind a clock reset: the false ones, and a hold / re-approach that was
    on; a phase outside LEVEL / DONE is named too."""
    names = [name for name in RESET_FALSE_NAMES if row.get(name) is False]
    names += [name for name in RESET_TRUE_NAMES if row.get(name) is True]
    if row["phase"] not in PHASE_LEVEL_DONE:
        names.append(f"phase:{row['phase']}")
    return names


def done_clock_of(rows: list[dict], loc_onsets_s: list[float], t_first_done_s: float | None,
                  t_first_ready_s: float | None = None) -> dict:
    """The ``done_clock`` summary of a trace (rules 4.2).

    The clock window is [last LOC onset before the first DONE, first DONE]; a clock start is a
    period whose ``complete_since_s`` went from None to a value, a reset one where it went from
    a value to None. ``loss_s = c_m - c_1`` (0 with one start, None without a start or DONE).
    """
    out = {"t_first_done_s": t_first_done_s, "t_first_ready_s": t_first_ready_s,
           "loc_onsets_s": list(loc_onsets_s), "t_loc_last_before_done_s": None,
           "clock_starts_s": [], "resets": [], "loss_s": None, "trace_rows": len(rows)}
    if t_first_done_s is None:
        return out
    onsets = [t for t in loc_onsets_s if t <= t_first_done_s + TIME_TOLERANCE_S]
    t_loc_s = onsets[-1] if onsets else (rows[0]["t_s"] if rows else None)
    out["t_loc_last_before_done_s"] = onsets[-1] if onsets else None
    if t_loc_s is None:
        return out
    previous = None
    for row in rows:
        if row["t_s"] < t_loc_s - TIME_TOLERANCE_S:
            previous = row["complete_since_s"]
            continue
        if row["t_s"] > t_first_done_s + TIME_TOLERANCE_S:
            break
        since = row["complete_since_s"]
        if previous is None and since is not None:
            out["clock_starts_s"].append(row["t_s"])
        elif previous is not None and since is None:
            out["resets"].append({"t_s": row["t_s"], "names": reset_names(row)})
        previous = since
    starts = out["clock_starts_s"]
    out["loss_s"] = starts[-1] - starts[0] if starts else None
    return out


def done_blocks(controller) -> tuple[list[dict], dict]:
    log = controller.__dict__.get(DONE_LOG_ATTRIBUTE) or DoneLog()
    clock = done_clock_of(log.rows, log.loc_onsets_s, log.t_first_done_s, log.t_first_ready_s)
    clock.update(t_first_loc_s=log.t_first_loc_s, t_trace_start_s=log.t_trace_start_s)
    return log.rows, clock


# ------------------------------------------------------------------------------- jobs
def _entry(bundle: str, candidate: str, label: str, grid_point=None, record_diag=False,
           record_done=True) -> dict:
    return {"bundle": bundle, "candidate": candidate, "label": label,
            "grid_point": None if grid_point is None else list(grid_point),
            "record_diag": record_diag, "record_done": record_done}


def grid_label(candidate: str, centre: str, j: int) -> str:
    return f"{candidate}-LT-c{centre}-j{j}"


def _with_entry(job: dict, entry: dict, mask: int | None) -> dict:
    return {**job, "mask": mask, "rev": entry}


def _jobs_by_key(base: list[dict]) -> dict[str, dict]:
    return {fb.fb_key(job): job for job in base}


def r0_jobs() -> tuple[list[dict], list[dict]]:
    """Rules 7.1: the six P0 bit-test jobs (key, label) of ``las_rev_judge.R0_EXPECTED``."""
    import las_targeted

    jobs, entries = [], []
    for key, label in judge.R0_EXPECTED:
        if key.startswith("R12|"):
            base = _jobs_by_key(fb.bundle_base_jobs("F-4"))[key]
        elif "diag-psa-soil" in key:
            base = _jobs_by_key(fb.bundle_base_jobs("F-3"))[key]
        else:
            base = las_targeted.jobs_for_keys([key])[0]
        grid = R0_GRID_POINT if label != "P0" else None
        jobs.append(base)
        entries.append(_entry("R-0", "P0", label, grid, record_diag=grid is not None))
    return jobs, entries


def grid_jobs(candidates) -> tuple[list[dict], list[dict]]:
    """R-G: the two G-3 keys (VB first) x candidates x centre x j (rules 3.1)."""
    import las_targeted

    base = sorted(las_targeted.jobs_for_keys(list(GRID_KEYS)),
                  key=lambda job: job["setting"] != "VB")
    jobs, entries = [], []
    for candidate in candidates:
        for job in base:
            for centre in judge.GRID_CENTRES:
                for j in judge.GRID_STEPS:
                    jobs.append(job)
                    entries.append(_entry("R-G", candidate, grid_label(candidate, centre, j),
                                          (centre, j), record_diag=True))
    return jobs, entries


def t_base_jobs() -> list[dict]:
    import las_targeted

    return las_targeted.jobs_for_keys(las_targeted.stage_keys("T-1")
                                      + las_targeted.stage_keys("T-2"))


def s_base_jobs() -> list[dict]:
    return fb.bundle_base_jobs("F-3") + fb.bundle_base_jobs("F-4")


def pair_jobs(bundle: str, base: list[dict], candidates) -> tuple[list[dict], list[dict]]:
    """One job per (key, candidate), the candidates of a key next to each other, VB first."""
    ordered = sorted(base, key=lambda job: job["setting"] != "VB")
    jobs, entries = [], []
    for job in ordered:
        for candidate in candidates:
            jobs.append(job)
            entries.append(_entry(bundle, candidate, candidate))
    return jobs, entries


def keys_from_files(paths: list[Path], bundle: str, stored: dict) -> list[str]:
    """R-P0: changed keys; R-X: exception-claim keys of the given R-T / R-S files."""
    lines = [line for path in paths for line in judge.read_lines(path)]
    if bundle == "R-P0":
        return sorted(judge.changed_keys(lines, stored))
    return sorted(judge.exception_claim_keys(lines, stored))


def bundle_jobs(bundle: str, candidates, mask: int | None = None, keys=None,
                record_done: bool = True) -> list[dict]:
    """The jobs of a bundle with their ``rev`` entries (``keys`` filters R-T / R-S / R-P0 /
    R-X and is required for R-P0 / R-X)."""
    if bundle == "R-0":
        base, entries = r0_jobs()
    elif bundle == "R-G":
        base, entries = grid_jobs(candidates)
    elif bundle in ("R-T", "R-S"):
        all_base = t_base_jobs() if bundle == "R-T" else s_base_jobs()
        if keys is not None:
            all_base = [job for job in all_base if fb.fb_key(job) in set(keys)]
        base, entries = pair_jobs(bundle, all_base, candidates)
    elif bundle in ("R-P0", "R-X"):
        if keys is None:
            raise ValueError(f"{bundle} needs keys (--keys or --from)")
        by_key = _jobs_by_key(t_base_jobs() + s_base_jobs())
        missing = [key for key in keys if key not in by_key]
        if missing:
            raise KeyError(f"{bundle}: keys outside R-T / R-S: {missing[:5]}")
        base, entries = pair_jobs(bundle, [by_key[key] for key in keys], ("P0",))
    else:
        raise ValueError(f"unknown bundle {bundle!r}")
    jobs = []
    for index, (job, entry) in enumerate(zip(base, entries, strict=True)):
        entry = {**entry, "id": index, "record_done": record_done}
        jobs.append(_with_entry(job, entry, mask))
    return jobs


def _comparable_job(job: dict) -> str:
    return json.dumps({k: v for k, v in job.items() if k not in ("mask", "rev", "t4h_dir")},
                      sort_keys=True)


def job_dict_problems(jobs: list[dict], stored: dict) -> list[str]:
    """H-4 (rules 3.3): every paired job equals the stored L line's ``job``."""
    problems = []
    for job in jobs:
        key = fb.fb_key(job)
        line = judge.stored_line(stored, key)
        if job["rev"]["bundle"] in ("R-T", "R-S", "R-P0", "R-X") and line is None:
            problems.append(f"{key}: no stored L line")
        elif line is not None and _comparable_job(job) != _comparable_job(line["job"]):
            problems.append(f"{key}: job dict differs from the stored L line")
    return problems


# ------------------------------------------------------------------------------- worker
def run_identity() -> dict:
    """``fb_targeted.run_identity`` with this tool's files and the rules sha256."""
    return {**fb.run_identity(files=IDENTITY_FILES), "rules_sha256": judge.RULES_SHA256,
            "rules_rev1_sha256": judge.RULES_REV1_SHA256}


def identity_problems(identity: dict) -> list[str]:
    """Rules 4.1: only the allowed dirty files and no uncommitted code."""
    problems = [f"dirty {name}" for name in identity["dirty_files"] if name not in ALLOWED_DIRTY]
    if identity["code_diff_sha256"] != fb.EMPTY_SHA256:
        problems.append(f"code_diff_sha256 {identity['code_diff_sha256']} is not empty")
    return problems + fb.thread_problems(identity["threads"])


_RUN: dict = {}
"""The worker's run values (one run per worker)."""


def _install_all(entry: dict) -> None:
    import las_phase_diag

    fb._install_candidate(fb.CANDIDATES["L"])  # threads, preset LAS-b b0, run capture
    # Read before the run: the harness later patches with_10hz_d1 (and keeps its last result).
    _RUN["preset_settings"] = preset_las_settings()
    grid_point = None if entry["grid_point"] is None else tuple(entry["grid_point"])
    if entry["record_diag"] or grid_point is not None:
        las_phase_diag.install(entry["record_diag"], grid_point)
    candidate = CANDIDATES[entry["candidate"]]
    if candidate.name != "P0":
        install_candidate(candidate, preset_settings=_RUN["preset_settings"])
    if entry["record_done"]:
        install_done_recorder()


def las_block(controller, harness: dict | None, candidate: str) -> dict:
    """``fb_targeted.las_block_from_meta`` with the candidate's name and ``n_min``."""
    from outrigger_sim.control import c2

    meta = controller.meta()["liftoff_approach_slow"]
    block = fb.las_block_from_meta(meta, controller.config.soil.enable,
                                   controller._reference_weight_N(), harness, c2.LEG_ORDER)
    settings = meta["settings"]
    return {**block, "candidate": candidate,
            "params": {**fb.las_params_of(settings), "n_min": settings["min_active_periods"]},
            "settings": settings}


def rev_block(entry: dict, job: dict, controller, line: dict, identity: dict) -> dict:
    settings = asdict(controller.config.liftoff_approach_slow)
    preset = _RUN.get("preset_settings") or preset_las_settings()
    expected = asdict(CANDIDATES[entry["candidate"]].settings_from(preset))
    return {**{name: entry[name] for name in ("bundle", "candidate", "label", "grid_point",
                                              "record_diag", "record_done")},
            "key": fb.fb_key(job), "identity": identity, "rules_sha256": judge.RULES_SHA256,
            "settings": settings, "expected_settings": expected,
            "settings_match": settings == expected,
            "controller_tag": line.get("controller_tag")}


def _add_blocks(line: dict, entry: dict, job: dict, identity: dict) -> None:
    import las_phase_diag

    plant, controller = fb._run_objects(job)
    if plant is None or controller is None:
        raise RuntimeError(f"run objects not captured (plant {plant is not None}, "
                           f"controller {controller is not None})")
    line["las"] = las_block(controller, fb._CAPTURE.get("harness"), entry["candidate"])
    line["rev"] = rev_block(entry, job, controller, line, identity)
    if entry["record_diag"]:
        diag_entry = {"bundle": entry["bundle"], "label": entry["label"], "record": True}
        line["diag"] = {"key": fb.fb_key(job),
                        **las_phase_diag.diag_block(diag_entry, line, line["las"], controller,
                                                    plant, identity)}
    if entry["record_done"]:
        line["done_trace"], line["done_clock"] = done_blocks(controller)


def run_rev_job(job: dict) -> dict:
    """Worker: install the candidate (+ TOUCH budget / recorders), run, add the blocks."""
    t_start = time.perf_counter()
    entry = job.pop("rev")
    head = {"job": job, "rev": {**entry, "key": fb.fb_key(job)}}
    try:
        import run_v5  # sys.path and thread variables first

        identity = run_identity()
        _install_all(entry)
    except Exception as exc:  # recorded as an error line; the batch decides (H-7)
        return {**head, "error": f"install: {exc!r}", "tb": traceback.format_exc()[-3000:],
                "wall_s": round(time.perf_counter() - t_start, 1)}
    line = run_v5.run_one(job)
    if "error" in line:
        return {**line, "rev": head["rev"]}
    try:
        _add_blocks(line, entry, job, identity)
    except Exception as exc:
        return {**head, "error": f"metrics: {exc!r}", "tb": traceback.format_exc()[-3000:],
                "wall_s": round(time.perf_counter() - t_start, 1)}
    line["rev"]["id"] = entry["id"]
    return line


# ------------------------------------------------------------------------------- batch
@dataclass
class BatchState:
    """Stops of a running batch (rules 8)."""

    stop: str | None = None
    stopped_candidates: dict[str, str] = field(default_factory=dict)
    c2_pairs: dict[str, set] = field(default_factory=dict)
    attempts: dict[int, int] = field(default_factory=dict)
    runs: int = 0
    errors: int = 0
    skipped: int = 0


def check_line(record: dict, bundle: str, state: BatchState, stored: dict, k3_keys: dict,
               current_identity: dict) -> None:
    """Rules 8 on one finished line: identity, H-2 / H-3 (K checks), H-8 (C-2 count)."""
    rev = record["rev"]
    candidate = rev["candidate"]
    problems = fb.identity_mismatch(rev.get("identity"), current_identity)
    if problems:
        state.stop = f"run identity changed during the batch: {problems[:3]}"
        return
    tags = judge.tag_problems(record)
    if tags:
        state.stop = f"{rev['key']}: {tags}"
        return
    try:
        k_found = judge.k_problems(record, stored, k3_keys)
    except judge.MissingField as exc:
        k_found = [f"missing {exc}"]
    if k_found:
        print(f"K MISMATCH {candidate} {rev['key']}: {k_found}", flush=True)
        if bundle == "R-0" or any(text.startswith("H-2") for text in k_found):
            state.stop = f"H-2 R-0 mismatch: {k_found}"
        else:
            state.stopped_candidates.setdefault(candidate, f"H-3 {rev['key']}: {k_found}")
    l_line = judge.stored_line(stored, rev["key"])
    if bundle in ("R-P0", "R-X") and (
            l_line is None or record["commands_sha256"] != l_line["commands_sha256"]):
        state.stop = f"H-5 {bundle} {rev['key']} does not reproduce the stored L hash"
        return
    if bundle not in ("R-T", "R-S") or l_line is None:
        return
    try:
        violations = judge.pair_violations(record, l_line)
    except judge.MissingField as exc:
        violations = [f"undecidable: missing {exc}"]
    if violations:
        pairs = state.c2_pairs.setdefault(candidate, set())
        pairs.add(rev["key"])
        if len(pairs) >= judge.C2_STOP_PAIRS:
            state.stopped_candidates.setdefault(candidate, f"H-8 {len(pairs)} C-2 pairs")


def _print_line(state: BatchState, total: int, record: dict) -> None:
    rev = record.get("rev") or {}
    if "error" in record:
        text = f"ERROR {record['error'][:200]}"
    else:
        las = record.get("las") or {}
        text = (f"{(record.get('d1') or {}).get('verdict', record.get('final_phase'))} "
                f"{record['commands_sha256'][:12]} start {las.get('start_t_s')} "
                f"a {las.get('active_periods')} end {las.get('end_reason')} "
                f"loss {(record.get('done_clock') or {}).get('loss_s')} {record['wall_s']}s")
    print(f"{state.runs}/{total} {rev.get('label')} {rev.get('key')}: {text}", flush=True)


def _handle_record(record, jobs_by_id, bundle, state, stored, k3_keys, identity, resubmit
                   ) -> None:
    job_id = (record.get("rev") or {}).get("id")
    if "error" in record:
        state.errors += 1
        if bundle == "R-G":
            state.stop = "H-7 / G-3: an R-G error line (re-run the 30 lines as a whole)"
        elif state.attempts.get(job_id, 1) >= 2:
            state.stop = f"H-7: second error of {record['rev'].get('key')}"
        else:
            state.attempts[job_id] = 2
            resubmit(jobs_by_id[job_id])
        return
    check_line(record, bundle, state, stored, k3_keys, identity)


def run_batch(jobs: list[dict], path: Path, workers: int, bundle: str, stored: dict,
              current_identity: dict) -> BatchState:
    """Run the jobs in spawned workers (one run each, at most ``workers`` in flight) and
    write every line to the new file; stopped candidates get no further jobs."""
    import verdict_runs

    verdict_runs.warm_numba_cache()
    path.parent.mkdir(parents=True, exist_ok=True)
    state = BatchState()
    k3_keys = judge.p3_identical_keys(stored)
    jobs_by_id = {job["rev"]["id"]: job for job in jobs}
    pending = list(jobs)
    results: queue.Queue = queue.Queue()
    in_flight = 0
    with path.open("x", encoding="utf-8") as handle, \
            get_context("spawn").Pool(workers, maxtasksperchild=1) as pool:

        def submit(job: dict) -> None:
            nonlocal in_flight
            in_flight += 1
            pool.apply_async(run_rev_job, (dict(job),), callback=results.put,
                             error_callback=lambda exc, job=job: results.put(
                                 {"job": {k: v for k, v in job.items() if k != "rev"},
                                  "rev": job["rev"], "error": f"pool: {exc!r}", "wall_s": 0.0}))

        while state.stop is None and (pending or in_flight):
            while pending and in_flight < workers:
                job = pending.pop(0)
                if job["rev"]["candidate"] in state.stopped_candidates:
                    state.skipped += 1
                    continue
                submit(job)
            if not in_flight:
                break
            record = results.get()
            in_flight -= 1
            record.setdefault("job", {}).pop("mask", None)
            handle.write(json.dumps(record, default=_json_default) + "\n")
            handle.flush()
            state.runs += 1
            _print_line(state, len(jobs), record)
            _handle_record(record, jobs_by_id, bundle, state, stored, k3_keys,
                           current_identity, lambda job: pending.insert(0, job))
        if state.stop is not None:
            pool.terminate()
    state.skipped += len(pending)
    return state


def _json_default(value):
    return value.item() if hasattr(value, "item") else str(value)


# ------------------------------------------------------------------------------- CLI
def default_out(bundle: str, candidates, default_candidates) -> Path:
    name = f"rev_{bundle.replace('-', '')}"
    if default_candidates is None or tuple(candidates) != tuple(default_candidates):
        name += "_" + "_".join(candidates)
    return REV_DIR / f"{name}.jsonl"


def out_path_problem(path: Path, out_dir: Path = REV_DIR, root: Path = ROOT) -> str | None:
    """Inside the project ``--out`` must lie in ``v5/las/rev/``; it must not exist (``"x"``)."""
    resolved = path.resolve()
    if resolved.is_relative_to(root.resolve()) and not resolved.is_relative_to(
            out_dir.resolve()):
        return f"--out {path} is inside the project but not in {out_dir}"
    if resolved.exists():
        return f"--out {path} exists (new files only, no resume)"
    return None


def resolve_candidates(bundle: str, text: str | None) -> tuple[str, ...]:
    """Bundle candidates (R-T / R-S need them; R-0 / R-P0 / R-X are P0 only).

    Raises:
        ValueError: Missing, unknown or not allowed candidates.
    """
    default = BUNDLE_CANDIDATES[bundle]
    names = tuple(text.split(",")) if text else default
    if not names:
        raise ValueError(f"{bundle} needs --candidates (those that passed (ga))")
    allowed = default or judge.GRID_CANDIDATES
    unknown = [name for name in names if name not in allowed]
    if unknown:
        raise ValueError(f"{bundle}: candidates {unknown} not in {allowed}")
    return names


def list_bundles(bundles, candidates_text: str | None) -> tuple[list[str], list[str]]:
    """(report lines, problems): counts, the R-0 references in the stored files, K-3 counts."""
    stored = judge.load_stored()
    lines, problems = [], []
    for bundle in bundles:
        if bundle in ("R-P0", "R-X"):
            lines.append(f"{bundle}: keys from the R-T / R-S files (run --from / --keys)")
            continue
        names = resolve_candidates(bundle, candidates_text or (
            ",".join(judge.GRID_CANDIDATES) if bundle in ("R-T", "R-S") else None))
        jobs = bundle_jobs(bundle, names)
        lines.append(f"{bundle}: {len(jobs)} runs, candidates {names}")
        expected = BUNDLE_COUNTS.get(bundle)
        if expected is not None and len(jobs) != expected:
            problems.append(f"{bundle}: {len(jobs)} runs, expected {expected}")
        problems += job_dict_problems(jobs, stored) if bundle in ("R-T", "R-S") else []
    k3 = judge.p3_identical_keys(stored)
    counts = {source: len(keys) for source, keys in k3.items()}
    lines.append(f"K-3 P3 identical keys {counts} (rules {judge.K3_EXPECTED_COUNTS})")
    if counts != judge.K3_EXPECTED_COUNTS:
        problems.append(f"K-3 counts {counts} != {judge.K3_EXPECTED_COUNTS}")
    for (key, label), sha in judge.R0_EXPECTED.items():
        line = judge.stored_line(stored, key)
        if line is not None and label == "P0" and line["commands_sha256"] != sha:
            problems.append(f"R-0 reference {key} differs from the stored line")
    return lines, problems


def _parse_args(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list", help="runs of the bundles and the reference checks")
    listing.add_argument("--bundle", nargs="+", choices=BUNDLES, default=list(BUNDLES))
    listing.add_argument("--candidates", default=None)
    run = sub.add_parser("run", help="run a bundle into a new file")
    run.add_argument("--bundle", required=True, choices=BUNDLES)
    run.add_argument("--candidates", default=None, help="comma-separated, e.g. P5,P53")
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--affinity", default=None, help="hex mask, set in every worker")
    run.add_argument("--out", type=Path, default=None)
    run.add_argument("--keys", default=None, help="comma-separated pair keys (subset)")
    run.add_argument("--from", dest="from_files", type=Path, nargs="+", default=None,
                     help="R-P0 / R-X: the R-T / R-S files the keys come from")
    run.add_argument("--limit", type=int, default=None, help="first N runs only")
    run.add_argument("--no-done-record", action="store_true")
    return parser.parse_args(argv)


def _keys_of(args, stored: dict) -> list[str] | None:
    if args.keys:
        return args.keys.split(",")
    if args.bundle in ("R-P0", "R-X"):
        files = args.from_files or sorted(REV_DIR.glob("rev_RT*.jsonl")) + sorted(
            REV_DIR.glob("rev_RS*.jsonl"))
        return keys_from_files(files, args.bundle, stored)
    return None


EARLIER_BUNDLE_FILES = ("rev_RG*.jsonl", "rev_RT*.jsonl", "rev_RS*.jsonl", "rev_RP0*.jsonl")
"""The bundle files that must come from the current run identity before R-T .. R-X."""


def earlier_identity_problems(bundle: str, current: dict, directory: Path = REV_DIR
                              ) -> list[str]:
    """Rules 4.1 before R-T / R-S / R-P0 / R-X: an R-G file exists and every earlier bundle
    line has the current commit and tool sha256 (otherwise the candidate's lines would mix
    run identities)."""
    if bundle in ("R-0", "R-G"):
        return []
    paths = sorted({path for pattern in EARLIER_BUNDLE_FILES
                    for path in directory.glob(pattern)})
    if not any(path.name.startswith("rev_RG") for path in paths):
        return [f"no rev_RG*.jsonl in {directory}"]
    problems = []
    for path in paths:
        for line in judge.read_lines(path):
            if "error" in line:
                continue
            recorded = (line.get("rev") or {}).get("identity") or {}
            for name in ("git_head", "sha256"):
                if recorded.get(name) != current.get(name):
                    problems.append(f"{path.name} {(line.get('rev') or {}).get('key')}: {name}")
    return problems


def _prepare(args) -> tuple[list[dict], Path, dict, dict]:
    """Jobs, output path, stored lines and identity of a run (raises on input errors)."""
    candidates = resolve_candidates(args.bundle, args.candidates)
    path = args.out or default_out(args.bundle, candidates, BUNDLE_CANDIDATES[args.bundle])
    problem = out_path_problem(path)
    if problem is not None:
        raise ValueError(problem)
    identity = run_identity()
    problems = identity_problems(identity)
    if problems:
        raise ValueError(f"run identity (rules 4.1): {problems}")
    problems = earlier_identity_problems(args.bundle, identity)
    if problems:
        raise ValueError(f"earlier bundle lines of another run identity: {problems[:5]}")
    stored = judge.load_stored()
    mask = None if args.affinity is None else int(args.affinity, 16)
    keys = _keys_of(args, stored)
    if keys is not None and not keys:
        raise ValueError("no keys selected")
    jobs = bundle_jobs(args.bundle, candidates, mask, keys, not args.no_done_record)
    problems = job_dict_problems(jobs, stored)
    if problems:
        raise ValueError(f"H-4 job dicts: {problems[:5]}")
    jobs = jobs if args.limit is None else jobs[: args.limit]
    if not jobs:
        raise ValueError("no runs selected")
    return jobs, path, stored, identity


def _run_command(args) -> int:
    try:
        jobs, path, stored, identity = _prepare(args)
    except (KeyError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"input error: {exc!r}")
        print(json.dumps({"bundle": args.bundle, "stop": "input", "reason": str(exc)}))
        return 2
    print(f"run identity: {identity['git_head']} dirty {identity['git_dirty']} "
          f"code_diff {identity['code_diff_sha256'][:12]}", flush=True)
    print(f"{args.bundle}: {len(jobs)} runs -> {path}", flush=True)
    state = run_batch(jobs, path, args.workers, args.bundle, stored, identity)
    summary = {"bundle": args.bundle, "out": str(path), "runs": state.runs,
               "errors": state.errors, "skipped": state.skipped, "stop": state.stop,
               "stopped_candidates": state.stopped_candidates,
               "c2_pairs": {name: len(keys) for name, keys in state.c2_pairs.items()}}
    print(json.dumps(summary))
    is_bad = state.stop or state.stopped_candidates or state.skipped
    return 1 if is_bad else 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    problems = judge.sealed_rules_problems()
    if problems:
        print(f"input error (H-1): {problems}")
        print(json.dumps({"stop": "H-1", "reasons": problems}))
        return 2
    if args.command == "run":
        return _run_command(args)
    try:
        lines, problems = list_bundles(args.bundle, args.candidates)
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
