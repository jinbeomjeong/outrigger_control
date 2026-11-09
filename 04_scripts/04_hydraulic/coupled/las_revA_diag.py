"""LAS-b revision A diagnosis diagA (bundle ``D-A`` of ``las_revA_targeted.py``) and its judge.

Plan: ``06_analysis/02_control/verif_matrix/las_revA_diag_plan.md`` (control-expert, sealed;
LF sha256 :data:`PLAN_SHA256`, H-D0). The plan text wins where this code differs.

Runs (plan 1): the failing C-S key :data:`KEY` (the ``fb_targeted.bundle_base_jobs("F-3")``
job, equal to the stored L line's ``job``) x P0 / P5 / P5r4 (``las_revA_targeted.CANDIDATES``,
``dataclasses.replace`` on the b0 preset), period record and DONE record on, one thread.

Recorder (plan 2 / 6): :func:`install_soil_recorder` wraps, in the worker only and after the
other recorders, ``C2Controller.update`` (outermost), ``_is_plateau_period``,
``_plateau_rise_N``, ``_update_liftoff_window``, ``_update_crawler_zone``,
``_hold_crawler_zone_until_liftoff`` and, only while ``_update_crawler_zone`` runs,
``_clearance_estimate_m`` (its return value is the latch's slow clearance, a local variable of
``_update_crawler_zone``). Every hook calls the original once with the same arguments and
returns its result object unchanged; it keeps the return value or copies the state the
original read or wrote (``applied_output_m_s``, the window, the soil flags). No hooked
method is called a second time. The only other calls are the pure readers
``_reference_weight_N`` and ``_clearance_target_m``.

Per period (``diag.periods[].soil``, one per controller update):
  plateau_period, applied_mean_over_vmax (``_is_plateau_period`` call; None when not called),
  window_update (``_update_liftoff_window`` ran), loc_before, held_by_reapproach,
  clear_branch (the window took the clear branch: not a plateau period or a re-approach hold),
  window_len_before, window_cleared (clear branch on a non-empty window: a window was
  emptied), window_len, window_span_mm, window_first_t_s, tail_span_ok (True: the tail
  covered 10 mm, i.e. ``_plateau_rise_N`` was called; False: a sample was added without a
  10 mm tail; None: no sample), rise_N, mean_load_over_W, is_flat (rise_N <= 2 kN),
  loc_confirmed_now, plateau_start_s, mean_motor_stroke_mm (the reading of the level step),
  slow_clearance_mm, zone_before, latch_release (zone latched before and slow clearance >=
  the release threshold), soil_hold_called, soil_mode_started_now, in_crawler_zone,
  soil_mode, loc, clearance_target_mm (state after the update).
Windows (plan 2): periods first TOUCH end - 0.5 s .. first READY + 1 s; 1 kHz force rows
crawler lift-off (``values.forces.t_lift_s``) - 0.5 s .. first LOC + 2 s.
Summary ``diag.soil_summary`` (plan 2): t_rel (first slow clearance >= 20 mm), t_S, t_LOC,
t_w0 (first sample of the window that confirmed the LOC), t_P, n_clear / clear_times_s and
n_steep / steep_times_s (crawler lift-off <= t < t_LOC), s_rel_mm, s_LOC_mm, and the controller
meta values (soil mode, LOC, R4c30).

Judge (plan 3 / 4 / 5): D-0a .. D-0d, W-1 .. W-3, B-1, H-D1, H-D3 and the branch table. Two
plan texts cannot be read mechanically in one way:
  W-1  prediction "s_LOC < s_rel and within 5 mm"; branch column "P0 too has s_LOC >= s_rel".
  W-3  prediction "t_rel < t_S"; in c2 the soil mode starts in the call that releases the
       latch (``_update_crawler_zone`` -> ``_hold_crawler_zone_until_liftoff``), so t_S =
       t_rel whenever the soil mode follows a release; the rejection column is "t_S not tied
       to t_rel" (the soil-mode period has no latch release).
The plan addendum ``las_revA_diag_plan_rev1.md`` (:data:`PLAN_REV1_SHA256`) fixes both
readings (DR1-1, DR1-2) and the branch order (DR1-3); the verdict is its branch
(``branch_rev1``). The literal reading (``branches_literal``, verdict ``verdict_literal``)
and the earlier alternative reading (``branches_alternative_reading``, not the rev1 reading)
are still reported; a literal branch other than the rev1 branch goes to ``asks`` (DR1-5).

Usage (dynamics-dev or python-dev python.exe, project root, PowerShell):
  python -I -B 04_scripts/04_hydraulic/coupled/las_revA_diag.py judge [diagA.jsonl]
      [--stored-l <fb_F3.jsonl>] [--stored-p5r4 <revA_RS.jsonl>] [--out <md>]
      [--json-out <json>]
Exit codes: 0 judged (one rev1 branch; ``asks`` may still hold a question for the user),
1 a stop (H-D0 / H-D1 / H-D3), missing runs or W-1 undecidable, 2 input error.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fb_targeted as fb  # noqa: E402  (sets the thread variables before numpy loads)
import las_phase_diag  # noqa: E402
import las_rev_judge as rj  # noqa: E402
import las_revA_judge as judge  # noqa: E402
import numpy as np  # noqa: E402

ROOT = fb.ROOT
DIAGA_DIR = fb.V5_DIR / "las" / "diagA"
DEFAULT_OUT = DIAGA_DIR / "diagA.jsonl"
PLAN_PATH = ROOT / "06_analysis" / "02_control" / "verif_matrix" / "las_revA_diag_plan.md"
PLAN_SHA_PATH = PLAN_PATH.with_suffix(".sha256")
PLAN_SHA256 = "da74185b79b654d4cfcf7ef5cc29efd82dedb872a52204e472380aed02c69961"
"""``las_revA_diag_plan.sha256`` (LF digest, sealed 2026-11-09 09:40:26 +09:00)."""
PLAN_REV1_PATH = PLAN_PATH.with_name("las_revA_diag_plan_rev1.md")
PLAN_REV1_SHA_PATH = PLAN_REV1_PATH.with_suffix(".sha256")
PLAN_REV1_SHA256 = "cbca7b4bd26408c5b27efbb1dada514db7f44664bd79325f56baa6096352d943"
"""``las_revA_diag_plan_rev1.sha256`` (LF digest, sealed 2026-11-09 10:00:24 +09:00)."""
RULES_REVA_REV3_PATH = judge.RULES_REVA_PATH.with_name("las_revA_targeted_rules_rev3.md")
RULES_REVA_REV3_SHA_PATH = RULES_REVA_REV3_PATH.with_suffix(".sha256")
RULES_REVA_REV3_SHA256 = "98082a368da626f90ce3b0a41f5c74145b4095c155f14b2b2f63eb319352d709"
"""revA rev3 (LF digest, sealed 2026-11-09 08:32:38 +09:00), the sixth rules file (plan 6)."""
RULES_FIELDS = (*judge.RULES_FIELDS, "rules_revA_rev3_sha256")
RULES_VALUES = (*judge.RULES_VALUES, RULES_REVA_REV3_SHA256)
SEALED_FILES = (*judge.SEALED_RULES,
                (RULES_REVA_REV3_PATH, RULES_REVA_REV3_SHA_PATH, RULES_REVA_REV3_SHA256),
                (PLAN_PATH, PLAN_SHA_PATH, PLAN_SHA256),
                (PLAN_REV1_PATH, PLAN_REV1_SHA_PATH, PLAN_REV1_SHA256))
"""H-1 files of the run and H-D0 (the plan): six rules files, the plan and its rev1."""

BUNDLE = "D-A"
KEY = "D1|H-S-A|G1+J1@FL|T|flat|K1|VB|e0"
CANDIDATE_NAMES = ("P0", "P5", "P5r4")
EXPECTED_HASHES = {
    "P0": "fae9b3900c9dc13dbe6fa3e9a8a38510da058f268af09684f8e51313ab35fe06",
    "P5r4": "eeacc7830847ecf2d597446d235277c990643f909dac06f8538038f29d5bbb9d",
}
"""Plan 1 pair hashes (D-0a: stored ``fb_F3.jsonl`` L, D-0b: stored revA2 R-S P5r4)."""
STORED_L_PATH = fb.V5_DIR / "fb" / "fb_F3.jsonl"
STORED_L_SHA256 = "76be00cfc12121ee1e4251f2f696caece544863f89afe1c4a8ff290acc880bcf"
STORED_P5R4_PATH = judge.REVA2_DIR / "revA_RS.jsonl"
STORED_P5R4_SHA256 = "7c407b6ee07b001f5504186fa013193ba6a2992516021f263b2bb537de43875d"
"""Raw sha256 of the two stored files of plan 0 (prefixes 76be00cf / 7c407b6e)."""

# Plan 3 values.
PLAN_LAS_START_S = 22.9
PLAN_LAS_END_S = 23.3
PLAN_LAS_END_REASON = "sum"
PLAN_LAS_ACTIVE_PERIODS = 4
PLAN_T_LIFT_S = 22.868
PLAN_P0_LOC_S = 23.5
PLAN_P5R4_LOC_S = 24.1
W1_MAX_GAP_MM = 5.0
W1B_MAX_ABS_GAP_MM = 5.0
"""W-1b (record only, DR1-2): |s_LOC - s_rel| <= this. Provisional definition of the main
session, pending control-expert's confirmation."""
W2_AFTER_RAMP_S = 0.5
B1_LOC_RANGE_S = (23.7, 24.1)
B1_MIN_STROKE_GAIN_MM = 25.0
R4C30_MARGIN_MM = 30.0
TIME_TOLERANCE_S = 1e-6
VALUE_TOLERANCE_MM = 1e-6

TOUCH_END_LEAD_S = 0.5
READY_TAIL_S = 1.0
LIFT_LEAD_S = 0.5
LOC_TAIL_S = 2.0
PHASE_READY = "ready"
M_TO_MM = 1e3
SOIL_LOG_ATTRIBUTE = "_diagA_soil"
FLAT_SOIL_MARGIN_EVENT = "INFO_LOC_FLAT_SOIL_MARGIN"
SOIL_MODE_EVENT = "soil_mode_start"

STATUS_TRUE, STATUS_FALSE, STATUS_UNDECIDABLE = "true", "false", "undecidable"
BRANCH_BETA = "beta"
BRANCH_RAMP = "ramp"
BRANCH_BOUNDARY = "boundary_key"
BRANCH_REJECTED = "rejected"
BRANCH_STOP = "stop"
BRANCH_UNDECIDABLE = "undecidable"
NEEDS_DECISION = "needs_decision"
VERDICT_BRANCH, VERDICT_STOP, VERDICT_UNDECIDABLE = "branch", "stop", "undecidable"
ALTERNATIVE_READING_NOTE = ("branches_alternative_reading (W-1 boundary column, W-3 t_rel <= "
                            "t_S) is not the rev1 reading; the verdict is branch_rev1")


# ------------------------------------------------------------------------------- seals
def seal_problems(sealed=SEALED_FILES) -> list[str]:
    """H-1 (six rules files) and H-D0 (the plan and its ``.sha256``, LF digest)."""
    return rj.sealed_rules_problems(sealed)


def stored_file_problems(l_path: Path, p5r4_path: Path) -> list[str]:
    """The two stored files of plan 0 with their raw sha256."""
    return (judge.reference_problems(l_path, STORED_L_SHA256)
            + judge.reference_problems(p5r4_path, STORED_P5R4_SHA256))


def _single(lines: list[dict], path: Path, candidate_of, name: str) -> dict:
    found = [line for line in lines
             if fb.fb_key(line.get("job") or {}) == KEY and candidate_of(line) == name]
    if len(found) != 1:
        raise ValueError(f"{path.name}: {len(found)} {name} lines of {KEY}")
    return found[0]


@dataclass(frozen=True)
class StoredPairs:
    """The stored L line (``fb_F3.jsonl``) and P5r4 line (revA2 ``revA_RS.jsonl``) of KEY."""

    l_line: dict
    p5r4_line: dict


def load_stored_pairs(l_path: Path = STORED_L_PATH,
                      p5r4_path: Path = STORED_P5R4_PATH) -> StoredPairs:
    """The two stored lines; their command hashes must be the plan's.

    Raises:
        ValueError: A file with another sha256, not one line, or another command hash.
    """
    problems = stored_file_problems(l_path, p5r4_path)
    if problems:
        raise ValueError(f"stored files: {problems}")
    l_line = _single(rj.read_lines(l_path), l_path,
                     lambda line: (line.get("fb") or {}).get("candidate"), "L")
    p5r4_line = _single(rj.read_lines(p5r4_path), p5r4_path,
                        lambda line: rj.rev_of(line).get("candidate"), "P5r4")
    for name, line in (("P0", l_line), ("P5r4", p5r4_line)):
        if line["commands_sha256"] != EXPECTED_HASHES[name]:
            raise ValueError(f"stored {name} pair hash {line['commands_sha256']} is not the "
                             f"plan's {EXPECTED_HASHES[name]}")
    return StoredPairs(l_line, p5r4_line)


# ------------------------------------------------------------------------------- jobs
def base_job() -> dict:
    """The F-3 job of :data:`KEY` (plan 1).

    Raises:
        ValueError: F-3 has not exactly one job of the key.
    """
    jobs = [job for job in fb.bundle_base_jobs("F-3") if fb.fb_key(job) == KEY]
    if len(jobs) != 1:
        raise ValueError(f"F-3 has {len(jobs)} jobs with key {KEY}")
    return jobs[0]


def job_problems(job: dict, stored_l_line: dict) -> list[str]:
    """Plan 6: the job dict equals the stored L line's ``job`` (else exit 2)."""
    import las_rev_targeted as rev

    if rev._comparable_job(job) != rev._comparable_job(stored_l_line["job"]):
        return [f"{KEY}: job dict differs from the stored L line"]
    return []


# ------------------------------------------------------------------------------- recorder
_PERIOD: dict = {}
"""Values of the running period's hooked calls (one controller at a time in a worker)."""
_SCOPE = {"crawler_zone": False}
_INSTALLED: dict = {}
HOOKED_METHODS = ("update", "_is_plateau_period", "_plateau_rise_N", "_update_liftoff_window",
                  "_update_crawler_zone", "_hold_crawler_zone_until_liftoff",
                  "_clearance_estimate_m")


def _soil_log_of(controller) -> list[dict]:
    log = controller.__dict__.get(SOIL_LOG_ATTRIBUTE)
    if log is None:
        log = []
        controller.__dict__[SOIL_LOG_ATTRIBUTE] = log
    return log


def _note_stroke(reading) -> None:
    if "mean_motor_stroke_mm" not in _PERIOD:
        _PERIOD["mean_motor_stroke_mm"] = float(np.mean(reading.motor_stroke_m)) * M_TO_MM


def _window_values(soil) -> dict:
    """Length, mean-stroke span and first sample time of the S-1 window after the call."""
    window = [] if soil is None else list(soil.window)
    if not window:
        return {"window_len": 0, "window_span_mm": None, "window_first_t_s": None}
    span_m = window[-1].mean_motor_stroke_m - window[0].mean_motor_stroke_m
    return {"window_len": len(window), "window_span_mm": span_m * M_TO_MM,
            "window_first_t_s": float(window[0].t_s)}


def _plateau_period_hook(original):
    def is_plateau_period(self):
        result = original(self)
        applied = np.asarray(self._state.applied_output_m_s, dtype=float)
        _PERIOD["plateau_period"] = bool(result)
        _PERIOD["applied_mean_over_vmax"] = (float(np.mean(applied))
                                             / float(self.geometry.max_speed_m_s))
        return result

    return is_plateau_period


def _rise_hook(original):
    def plateau_rise_N(self, tail):
        result = original(self, tail)
        loads_N = np.array([sample.load_sum_N for sample in tail])
        _PERIOD["rise_N"] = float(result)
        _PERIOD["mean_load_over_W"] = float(loads_N.mean()) / self._reference_weight_N()
        return result

    return plateau_rise_N


def _window_hook(original):
    def update_liftoff_window(self, reading):
        _note_stroke(reading)
        soil = self._state.soil  # read, never created here
        loc_before = bool(soil is not None and soil.is_liftoff_confirmed)
        len_before = 0 if soil is None else len(soil.window)
        result = original(self, reading)
        soil = self._state.soil
        is_plateau = _PERIOD.get("plateau_period")
        held = not loc_before and is_plateau is None
        clear_branch = not loc_before and (held or is_plateau is False)
        loc_now = bool(soil is not None and soil.is_liftoff_confirmed and not loc_before)
        _PERIOD.update(
            window_update=True, loc_before=loc_before, held_by_reapproach=held,
            clear_branch=clear_branch, window_len_before=len_before,
            window_cleared=clear_branch and len_before > 0, loc_confirmed_now=loc_now,
            plateau_start_s=soil.plateau_start_s if loc_now else None,
            tail_span_ok=None if is_plateau is not True else "rise_N" in _PERIOD,
            **_window_values(soil))
        return result

    return update_liftoff_window


def _clearance_hook(original):
    def clearance_estimate_m(self, rod_stroke_m):
        result = original(self, rod_stroke_m)
        if _SCOPE["crawler_zone"] and "slow_clearance_m" not in _PERIOD:
            _PERIOD["slow_clearance_m"] = float(result)
        return result

    return clearance_estimate_m


def _crawler_zone_hook(original):
    def update_crawler_zone(self, reading):
        _note_stroke(reading)
        zone_before = bool(self._state.in_crawler_zone)
        _SCOPE["crawler_zone"] = True
        try:
            result = original(self, reading)
        finally:
            _SCOPE["crawler_zone"] = False
        slow_m = _PERIOD.get("slow_clearance_m")
        release_m = self.config.thresholds.crawler_zone_release_m
        _PERIOD["zone_before"] = zone_before
        _PERIOD["latch_release"] = (None if slow_m is None
                                    else zone_before and slow_m >= release_m)
        return result

    return update_crawler_zone


def _hold_hook(original):
    def hold_crawler_zone_until_liftoff(self, reading):
        soil = self._state.soil
        start_before = None if soil is None else soil.soil_mode_start_s
        result = original(self, reading)
        soil = self._state.soil
        _PERIOD["soil_hold_called"] = True
        _PERIOD["soil_mode_started_now"] = bool(
            start_before is None and soil is not None and soil.soil_mode_start_s is not None)
        return result

    return hold_crawler_zone_until_liftoff


SOIL_RECORD_DEFAULTS = {
    "plateau_period": None, "applied_mean_over_vmax": None, "window_update": False,
    "loc_before": None, "held_by_reapproach": None, "clear_branch": False,
    "window_len_before": None, "window_cleared": False, "window_len": None,
    "window_span_mm": None, "window_first_t_s": None, "tail_span_ok": None, "rise_N": None,
    "mean_load_over_W": None, "loc_confirmed_now": False, "plateau_start_s": None,
    "mean_motor_stroke_mm": None, "slow_clearance_mm": None, "zone_before": None,
    "latch_release": None, "soil_hold_called": False, "soil_mode_started_now": False}


def soil_period_record(controller, t_s: float, values: dict) -> dict:
    """One ``diag.periods[].soil`` record from the period's hooked values and the state."""
    record = {"t_s": t_s, **SOIL_RECORD_DEFAULTS}
    record.update({name: value for name, value in values.items() if name in record})
    slow_m = values.get("slow_clearance_m")
    record["slow_clearance_mm"] = None if slow_m is None else slow_m * M_TO_MM
    rise_N = record["rise_N"]
    rise_max_N = controller.config.soil.plateau_rise_max_N
    record["is_flat"] = None if rise_N is None else rise_N <= rise_max_N
    soil = controller._state.soil
    record.update(
        in_crawler_zone=bool(controller._state.in_crawler_zone),
        soil_mode=bool(soil is not None and soil.is_soil_mode),
        loc=bool(soil is not None and soil.is_liftoff_confirmed),
        clearance_target_mm=float(controller._clearance_target_m()) * M_TO_MM)
    return record


def _update_hook(original):
    def update(self, measurements):
        _PERIOD.clear()
        _SCOPE["crawler_zone"] = False
        command = original(self, measurements)
        _soil_log_of(self).append(soil_period_record(self, float(measurements.t_s), _PERIOD))
        return command

    return update


def install_soil_recorder(controller_class=None) -> None:
    """Wrap the S-1 / S-2 / latch methods (module docstring); ``update`` outermost.

    Raises:
        RuntimeError: Installed twice in one process.
    """
    if _INSTALLED:
        raise RuntimeError("las_revA_diag.install_soil_recorder: already installed")
    if controller_class is None:
        from outrigger_sim.control import c2

        controller_class = c2.C2Controller
    cls = controller_class
    originals = {name: getattr(cls, name) for name in HOOKED_METHODS}
    cls._is_plateau_period = _plateau_period_hook(originals["_is_plateau_period"])
    cls._plateau_rise_N = _rise_hook(originals["_plateau_rise_N"])
    cls._update_liftoff_window = _window_hook(originals["_update_liftoff_window"])
    cls._clearance_estimate_m = _clearance_hook(originals["_clearance_estimate_m"])
    cls._update_crawler_zone = _crawler_zone_hook(originals["_update_crawler_zone"])
    cls._hold_crawler_zone_until_liftoff = _hold_hook(
        originals["_hold_crawler_zone_until_liftoff"])
    cls.update = _update_hook(originals["update"])
    _INSTALLED.update(cls=cls, originals=originals)


def uninstall_soil_recorder() -> None:
    """Undo :func:`install_soil_recorder` (tests only)."""
    if not _INSTALLED:
        return
    cls = _INSTALLED["cls"]
    for name, method in _INSTALLED["originals"].items():
        setattr(cls, name, method)
    _INSTALLED.clear()
    _PERIOD.clear()


# ------------------------------------------------------------------------------- summary
def _first(records: list[dict], predicate) -> dict | None:
    return next((record for record in records if predicate(record)), None)


def _time_of(record: dict | None) -> float | None:
    return None if record is None else record["t_s"]


def _stroke_of(record: dict | None) -> float | None:
    return None if record is None else record["mean_motor_stroke_mm"]


def _in_lift_to_loc(t_s: float, t_lift_s: float | None, t_loc_s: float | None) -> bool:
    if t_lift_s is not None and t_s < t_lift_s - TIME_TOLERANCE_S:
        return False
    return t_loc_s is None or t_s < t_loc_s - TIME_TOLERANCE_S


def soil_summary(records: list[dict], t_lift_s: float | None, release_mm: float,
                 rise_max_N: float) -> dict:
    """Plan 2 ``diag.soil_summary`` from the soil records of a whole run."""
    released = _first(records, lambda record: record["slow_clearance_mm"] is not None
                      and record["slow_clearance_mm"] >= release_mm - VALUE_TOLERANCE_MM)
    soil_start = _first(records, lambda record: record["soil_mode_started_now"])
    loc = _first(records, lambda record: record["loc_confirmed_now"])
    t_loc_s = _time_of(loc)
    between = [record for record in records
               if _in_lift_to_loc(record["t_s"], t_lift_s, t_loc_s)]
    clears = [record["t_s"] for record in between if record["window_cleared"]]
    steep = [record["t_s"] for record in between
             if record["tail_span_ok"] and record["rise_N"] is not None
             and record["rise_N"] > rise_max_N]
    branch_clears = [record["t_s"] for record in between if record["clear_branch"]]
    return {"t_lift_s": t_lift_s, "release_mm": release_mm, "rise_max_N": rise_max_N,
            "t_rel_s": _time_of(released), "t_S_s": _time_of(soil_start),
            "t_S_latch_release": None if soil_start is None else soil_start["latch_release"],
            "t_LOC_s": t_loc_s, "t_w0_s": None if loc is None else loc["window_first_t_s"],
            "t_P_s": None if loc is None else loc["plateau_start_s"],
            "n_clear": len(clears), "clear_times_s": clears, "n_steep": len(steep),
            "steep_times_s": steep, "n_clear_branch": len(branch_clears),
            "clear_branch_times_s": branch_clears,
            "s_rel_mm": _stroke_of(released), "s_LOC_mm": _stroke_of(loc)}


def _meta_values(controller) -> dict:
    meta = controller.meta()
    soil = meta.get("soil") or {}
    margin = meta.get("slope_clearance_margin") or {}
    return {"meta_soil_mode_t_s": soil.get("soil_mode_t_s"), "meta_t_loc_s": soil.get("t_loc_s"),
            "meta_t_P_s": soil.get("t_P_s"),
            "flat_soil_margin_applied": margin.get("flat_soil_margin_applied"),
            "flat_soil_margin_t_s": margin.get("flat_soil_margin_t_s"),
            "clearance_target_base_mm": controller.config.thresholds.clearance_target_m * M_TO_MM,
            "clearance_target_final_mm": float(controller._clearance_target_m()) * M_TO_MM}


# ------------------------------------------------------------------------------- diag block
def period_window(periods: list[dict], touch_ends: list[dict]) -> dict:
    """Plan 2 period window: first TOUCH end - 0.5 s .. first READY after it + 1 s."""
    t_end_s = periods[-1]["t_s"] if periods else None
    t_touch_s = las_phase_diag.first_touch_end_s(touch_ends)
    ready = _first(periods, lambda period: period["phase"] == PHASE_READY and (
        t_touch_s is None or period["t_s"] >= t_touch_s - TIME_TOLERANCE_S))
    return {"t0_s": None if t_touch_s is None else t_touch_s - TOUCH_END_LEAD_S,
            "t1_s": t_end_s if ready is None else ready["t_s"] + READY_TAIL_S,
            "rule": "first TOUCH end - 0.5 s .. first READY after it + 1 s"}


def force_rows(rows: np.ndarray, columns: dict[str, int], t_lift_s: float | None,
               t_loc_s: float | None) -> dict | None:
    """Plan 2 1 kHz rows: crawler lift-off - 0.5 s .. LOC + 2 s (no LOC: run end)."""
    if t_lift_s is None or len(rows) == 0:
        return None
    t = rows[:, columns["t"]]
    t0_s = t_lift_s - LIFT_LEAD_S
    t1_s = float(t[-1]) if t_loc_s is None else t_loc_s + LOC_TAIL_S
    selected = (t >= t0_s - TIME_TOLERANCE_S) & (t <= t1_s + TIME_TOLERANCE_S)
    names = las_phase_diag.FORCE_WINDOW_COLUMNS
    kept = rows[selected][:, [columns[name] for name in names]]
    return {"t0_s": t0_s, "t1_s": t1_s, "rule": "crawler lift-off - 0.5 s .. LOC + 2 s",
            "columns": list(names),
            "rows": [las_phase_diag.rounded_list(row, digits=7) for row in kept]}


def _with_soil(periods: list[dict], records: list[dict]) -> list[dict]:
    by_time = {record["t_s"]: record for record in records}
    return [{**period, "soil": by_time.get(period["t_s"])} for period in periods]


def diag_block(entry: dict, line: dict, las: dict, controller, plant, identity: dict) -> dict:
    """The ``diag`` block of a D-A run (module docstring)."""
    from harness_flow import COLUMN

    log = controller.__dict__.get(las_phase_diag.LOG_ATTRIBUTE) or las_phase_diag.RunLog()
    records = controller.__dict__.get(SOIL_LOG_ATTRIBUTE) or []
    t_lift_s = ((line.get("values") or {}).get("forces") or {}).get("t_lift_s")
    summary_soil = {**soil_summary(records, t_lift_s,
                                   controller.config.thresholds.crawler_zone_release_m * M_TO_MM,
                                   controller.config.soil.plateau_rise_max_N),
                    **_meta_values(controller)}
    window = period_window(log.periods, log.touch_ends)
    rows = plant.flow_limiter.rows()
    rl_forces = las_phase_diag.force_window(rows, COLUMN, t_lift_s)
    summary = las_phase_diag._summary(line, las, log, window, rl_forces, None)
    return {"bundle": entry["bundle"], "candidate": entry["label"], "record": True,
            "identity": identity, "summary": summary, "soil_summary": summary_soil,
            "window": window, "touch_ends": log.touch_ends,
            "force_window": force_rows(rows, COLUMN, t_lift_s, summary_soil["t_LOC_s"]),
            "periods": _with_soil(las_phase_diag.periods_in(log.periods, window), records),
            "periods_total": len(log.periods), "soil_records_total": len(records)}


# ------------------------------------------------------------------------------- judge
def _close(value: float | None, expected: float, tolerance: float = TIME_TOLERANCE_S) -> bool:
    return value is not None and abs(value - expected) <= tolerance


def _status(value: bool | None) -> str:
    if value is None:
        return STATUS_UNDECIDABLE
    return STATUS_TRUE if value else STATUS_FALSE


def hash_problem(line: dict) -> str | None:
    """D-0a (P0) / D-0b (P5r4): the command hash is the plan's pair hash."""
    candidate = rj.rev_of(line).get("candidate")
    expected = EXPECTED_HASHES.get(candidate)
    if expected is None or line.get("commands_sha256") == expected:
        return None
    label = "D-0a" if candidate == "P0" else "D-0b"
    return f"{label} {candidate} hash {line.get('commands_sha256')} != {expected}"


def d0c_problems(p5: dict, p5r4: dict) -> list[str]:
    """D-0c: P5 equals P5r4 up to the LAS-b end (K-A1, K-A2 commands before the end, K-A3
    lift-off) and the plan's start / end / reason / periods / lift-off values."""
    try:
        problems = judge._ka1(p5r4, p5)
        t_end_s = rj.need(p5r4, "las", "end_t_s")
        if t_end_s is None:
            return problems + ["D-0c P5r4 LAS-b never ended"]
        problems += judge._ka2(p5r4, p5, t_end_s)
        lifts = (rj.need(p5, "diag", "summary", "t_lift_s"),
                 rj.need(p5r4, "diag", "summary", "t_lift_s"))
    except rj.MissingField as exc:
        return [f"D-0c missing {exc}"]
    if lifts[0] != lifts[1]:
        problems.append(f"K-A3 t_lift_s {lifts[0]} != P5r4 {lifts[1]}")
    las = p5["las"]
    expected = {"start_t_s": PLAN_LAS_START_S, "end_t_s": PLAN_LAS_END_S}
    problems += [f"D-0c P5 las.{name} {las.get(name)!r} != plan {value}"
                 for name, value in expected.items() if not _close(las.get(name), value)]
    if las.get("end_reason") != PLAN_LAS_END_REASON:
        problems.append(f"D-0c P5 end_reason {las.get('end_reason')!r} != plan "
                        f"{PLAN_LAS_END_REASON}")
    if las.get("active_periods") != PLAN_LAS_ACTIVE_PERIODS:
        problems.append(f"D-0c P5 active_periods {las.get('active_periods')!r} != plan "
                        f"{PLAN_LAS_ACTIVE_PERIODS}")
    if not _close(lifts[0], PLAN_T_LIFT_S):
        problems.append(f"D-0c t_lift_s {lifts[0]!r} != plan {PLAN_T_LIFT_S}")
    return [f"D-0c {text}" if not text.startswith("D-0c") else text for text in problems]


def _soil(line: dict) -> dict:
    return rj.need(line, "diag", "soil_summary")


def _has_event(line: dict, name: str) -> bool:
    return bool((line.get("event_names") or {}).get(name))


def r4c30_applied(line: dict) -> bool:
    """R4c30 acted: the flat-soil margin event and a clearance target raised by 30 mm."""
    soil = _soil(line)
    raised_mm = soil["clearance_target_final_mm"] - soil["clearance_target_base_mm"]
    return (_has_event(line, FLAT_SOIL_MARGIN_EVENT) and bool(soil["flat_soil_margin_applied"])
            and abs(raised_mm - R4C30_MARGIN_MM) <= VALUE_TOLERANCE_MM)


def d0d(p0: dict, p5r4: dict, stored: StoredPairs | None) -> dict:
    """D-0d: the P0 / P5r4 summaries are the stored lines' (LOC, soil mode, R4c30)."""
    problems = []
    if stored is None:
        return {"status": STATUS_UNDECIDABLE, "problems": ["no stored lines"]}
    pairs = (("P0", p0, stored.l_line, PLAN_P0_LOC_S), ("P5r4", p5r4, stored.p5r4_line,
                                                        PLAN_P5R4_LOC_S))
    for name, line, stored_line, loc_s in pairs:
        t_loc = line["las"].get("t_loc_s")
        if t_loc != stored_line["las"].get("t_loc_s") or not _close(t_loc, loc_s):
            problems.append(f"{name} las.t_loc_s {t_loc!r} != stored "
                            f"{stored_line['las'].get('t_loc_s')!r} / plan {loc_s}")
        if not _close(_soil(line)["t_LOC_s"], loc_s):
            problems.append(f"{name} soil t_LOC {_soil(line)['t_LOC_s']!r} != plan {loc_s}")
    if _soil(p0)["t_S_s"] is not None or _has_event(stored.l_line, SOIL_MODE_EVENT):
        problems.append(f"P0 soil mode {_soil(p0)['t_S_s']!r} (plan: none)")
    if _soil(p5r4)["t_S_s"] is None or not _has_event(stored.p5r4_line, SOIL_MODE_EVENT):
        problems.append("P5r4 has no soil mode (plan: t_S exists)")
    if not r4c30_applied(p5r4) or not _has_event(stored.p5r4_line, FLAT_SOIL_MARGIN_EVENT):
        problems.append("P5r4 clearance target not raised by 30 mm (plan: R4c30)")
    return {"status": STATUS_FALSE if problems else STATUS_TRUE, "problems": problems}


def w1(p0: dict) -> dict:
    """W-1 on P0: as written (``status``: s_LOC < s_rel, gap <= 5 mm), the rev1 branch reading
    (``status_rev1``: s_LOC < s_rel; false = ``boundary``, DR1-2) and the record W-1b
    (|s_LOC - s_rel| <= :data:`W1B_MAX_ABS_GAP_MM`)."""
    soil = _soil(p0)
    s_rel, s_loc = soil["s_rel_mm"], soil["s_LOC_mm"]
    if s_rel is None or s_loc is None:
        return {"status": STATUS_UNDECIDABLE, "status_rev1": STATUS_UNDECIDABLE,
                "boundary": None, "W1b": STATUS_UNDECIDABLE, "s_rel_mm": s_rel,
                "s_LOC_mm": s_loc, "s_LOC_minus_s_rel_mm": None, "s_rel_minus_s_LOC_mm": None}
    loc_minus_rel_mm = s_loc - s_rel
    is_before = s_loc < s_rel
    return {"status": _status(is_before and -loc_minus_rel_mm <= W1_MAX_GAP_MM),
            "status_rev1": _status(is_before), "boundary": not is_before,
            "W1b": _status(abs(loc_minus_rel_mm) <= W1B_MAX_ABS_GAP_MM),
            "W1b_max_abs_gap_mm": W1B_MAX_ABS_GAP_MM, "s_rel_mm": s_rel, "s_LOC_mm": s_loc,
            "s_LOC_minus_s_rel_mm": loc_minus_rel_mm,
            "s_rel_minus_s_LOC_mm": -loc_minus_rel_mm}


def w2(p5r4: dict) -> dict:
    """W-2 on P5r4: a cleared or steep window between LAS-b start and ramp end + 0.5 s;
    ``rejected`` when the window never failed between lift-off and LOC."""
    soil = _soil(p5r4)
    las = p5r4["las"]
    ramp_end_s = (las.get("ramp") or {}).get("end_t_s")
    start_s = las.get("start_t_s")
    times = sorted(soil["clear_times_s"] + soil["steep_times_s"])
    out = {"n_clear": soil["n_clear"], "n_steep": soil["n_steep"], "times_s": times,
           "range_s": None, "rejected": soil["n_clear"] == 0 and soil["n_steep"] == 0}
    if start_s is None or ramp_end_s is None:
        return {**out, "status": STATUS_UNDECIDABLE}
    low, high = start_s, ramp_end_s + W2_AFTER_RAMP_S
    inside = [t for t in times if low - TIME_TOLERANCE_S <= t <= high + TIME_TOLERANCE_S]
    return {**out, "range_s": [low, high], "times_in_range_s": inside,
            "status": _status(bool(inside))}


def w3(p5r4: dict) -> dict:
    """W-3 on P5r4: as written (t_rel < t_S <= t_LOC = 24.1 s, s_rel < s_LOC), the reading
    with t_rel <= t_S, the rev1 reading (DR1-1: the t_rel <= t_S reading and a latch release in
    the soil-mode period) and the rejection column (the soil-mode period has no latch
    release)."""
    soil = _soil(p5r4)
    t_rel, t_s, t_loc = soil["t_rel_s"], soil["t_S_s"], soil["t_LOC_s"]
    s_rel, s_loc = soil["s_rel_mm"], soil["s_LOC_mm"]
    latch_release = soil["t_S_latch_release"] is True
    out = {"t_rel_s": t_rel, "t_S_s": t_s, "t_LOC_s": t_loc, "s_rel_mm": s_rel,
           "s_LOC_mm": s_loc, "t_S_latch_release": soil["t_S_latch_release"],
           "rejected": t_s is not None and not latch_release}
    if None in (t_rel, t_s, t_loc, s_rel, s_loc):
        return {**out, "status": STATUS_UNDECIDABLE, "status_le": STATUS_UNDECIDABLE,
                "status_rev1": STATUS_UNDECIDABLE if t_s is not None else STATUS_FALSE}
    rest = t_s <= t_loc + TIME_TOLERANCE_S and _close(t_loc, PLAN_P5R4_LOC_S) and s_rel < s_loc
    holds_le = t_rel <= t_s + TIME_TOLERANCE_S and rest
    return {**out, "status": _status(t_rel < t_s - TIME_TOLERANCE_S and rest),
            "status_le": _status(holds_le), "status_rev1": _status(holds_le and latch_release)}


def b1(p0: dict, p5: dict) -> dict:
    """B-1 on P5: soil mode, t_LOC in [23.7, 24.1] s, R4c30, max stroke >= P0's + 25 mm."""
    soil = _soil(p5)
    t_loc = soil["t_LOC_s"]
    gain_mm = (rj.need(p5, "d1", "stroke_max_m") - rj.need(p0, "d1", "stroke_max_m")) * M_TO_MM
    low, high = B1_LOC_RANGE_S
    parts = {"soil_mode": soil["t_S_s"] is not None,
             "loc_in_range": t_loc is not None
             and low - TIME_TOLERANCE_S <= t_loc <= high + TIME_TOLERANCE_S,
             "r4c30": r4c30_applied(p5), "stroke_gain": gain_mm >= B1_MIN_STROKE_GAIN_MM}
    return {"status": _status(all(parts.values())), "parts": parts, "t_LOC_s": t_loc,
            "stroke_gain_mm": gain_mm}


def identity_problems(lines: list[dict]) -> list[str]:
    """H-D3: one commit, empty code diff, allowed dirty files only, the plan, its rev1 and six
    rules digests on every line."""
    import las_rev_targeted as rev

    heads = {rj.rev_of(line).get("identity", {}).get("git_head") for line in lines}
    problems = [] if len(heads) == 1 else [f"H-D3 commits {sorted(map(str, heads))}"]
    for line in lines:
        rev_entry = rj.rev_of(line)
        identity = rev_entry.get("identity") or {}
        name = rev_entry.get("candidate")
        if identity.get("code_diff_sha256") != fb.EMPTY_SHA256:
            problems.append(f"H-D3 {name} code diff not empty")
        dirty = [path for path in identity.get("dirty_files", [])
                 if path not in rev.ALLOWED_DIRTY]
        if dirty:
            problems.append(f"H-D3 {name} dirty {dirty}")
        if rev_entry.get("diag_plan_sha256") != PLAN_SHA256:
            problems.append(f"H-D3 {name} plan sha256 {rev_entry.get('diag_plan_sha256')}")
        if rev_entry.get("diag_plan_rev1_sha256") != PLAN_REV1_SHA256:
            problems.append(f"H-D3 {name} plan rev1 sha256 "
                            f"{rev_entry.get('diag_plan_rev1_sha256')}")
        wrong = [field for field, value in zip(RULES_FIELDS, RULES_VALUES, strict=True)
                 if rev_entry.get(field) != value]
        if wrong:
            problems.append(f"H-D3 {name} rules digests {wrong}")
    return problems


def line_problems(line: dict) -> list[str]:
    """Per-line H-D1 parts: controller tag, the candidate's settings (K-A8), D-0a / D-0b."""
    problems = judge.tag_problems(line)
    try:
        problems += judge.settings_problems(line)
    except rj.MissingField as exc:
        problems.append(f"missing {exc}")
    hash_text = hash_problem(line)
    return problems + ([] if hash_text is None else [hash_text])


def branches_of(d0_pass: bool, w1_out: dict, w2_out: dict, w3_out: dict, b1_out: dict
                ) -> list[str]:
    """Plan 4 rows that hold (W-3 read as written)."""
    w2_true = w2_out["status"] == STATUS_TRUE
    w3_true = w3_out["status"] == STATUS_TRUE
    out = []
    if d0_pass and w2_true and w3_true and b1_out["status"] == STATUS_TRUE:
        out.append(BRANCH_BETA)
    if d0_pass and w2_true and w3_true and b1_out["status"] == STATUS_FALSE:
        out.append(BRANCH_RAMP)
    if w1_out["status"] == STATUS_FALSE:
        out.append(BRANCH_BOUNDARY)
    if w2_out["rejected"]:
        out.append(BRANCH_REJECTED)
    return out


def _alternative_branches(d0_pass: bool, w1_out: dict, w2_out: dict, w3_out: dict,
                          b1_out: dict) -> list[str]:
    """The same rows with W-3 as t_rel <= t_S and W-1 as the boundary column."""
    w3_alt = {**w3_out, "status": w3_out["status_le"]}
    w1_alt = {**w1_out, "status": _status(None if w1_out["boundary"] is None
                                          else not w1_out["boundary"])}
    return branches_of(d0_pass, w1_alt, w2_out, w3_alt, b1_out)


def _d0_statuses(d0: dict) -> list[str]:
    statuses = [d0[name] for name in ("D-0a", "D-0b", "D-0c")]
    return [*statuses, d0["D-0d"]["status"]] if "D-0d" in d0 else statuses


def branch_rev1(d0: dict, w1_out: dict, w2_out: dict, w3_out: dict, p5: dict) -> str:
    """DR1-3: the first row that holds. B-1 as a whole is recorded only, not used here.

    1. a D-0a .. D-0d not true -> stop (H-D1)
    2. W-2 or W-3 rejected -> rejected
    3. W-1 undecidable (no s_rel or s_LOC) -> undecidable
    4. W-1 false (P0 s_LOC >= s_rel) -> boundary_key
    5. P5 has a soil-mode start -> beta, else ramp
    """
    if any(status != STATUS_TRUE for status in _d0_statuses(d0)):
        return BRANCH_STOP
    if w2_out["rejected"] or w3_out["rejected"]:
        return BRANCH_REJECTED
    if w1_out["status_rev1"] == STATUS_UNDECIDABLE:
        return BRANCH_UNDECIDABLE
    if w1_out["boundary"]:
        return BRANCH_BOUNDARY
    return BRANCH_BETA if _soil(p5)["t_S_s"] is not None else BRANCH_RAMP


def verdict_of_rev1(branch: str) -> str:
    """``stop`` / ``undecidable`` / ``branch`` for a :func:`branch_rev1` result."""
    if branch == BRANCH_STOP:
        return VERDICT_STOP
    if branch == BRANCH_UNDECIDABLE:
        return VERDICT_UNDECIDABLE
    return VERDICT_BRANCH


def literal_verdict(branches: list[str], alternative: list[str]) -> str:
    """The verdict of the readings before rev1 (``needs_decision`` when they disagree)."""
    if branches != alternative:
        return NEEDS_DECISION
    if len(branches) == 1:
        return VERDICT_BRANCH
    return "no_branch" if not branches else NEEDS_DECISION


def rev1_asks(branches_literal: list[str], branch: str) -> list[str]:
    """DR1-5: ask the user when the literal reading's branches differ from the rev1 branch
    (not after a stop, where no branch is read)."""
    if branch == BRANCH_STOP or branches_literal == [branch]:
        return []
    return [f"DR1-5: literal reading branches {branches_literal} differ from the rev1 branch "
            f"{branch!r}; the verdict uses the rev1 branch, ask the user about the difference"]


def _by_candidate(lines: list[dict]) -> tuple[dict[str, dict], list[str]]:
    by_name, problems = {}, []
    for line in lines:
        rev_entry = rj.rev_of(line)
        if rev_entry.get("bundle") != BUNDLE or rj.is_error(line):
            continue
        name = rev_entry.get("candidate")
        if name in by_name:
            problems.append(f"two {name} lines")
        by_name[name] = line
    missing = [name for name in CANDIDATE_NAMES if name not in by_name]
    if missing:
        problems.append(f"no line of {missing}")
    return by_name, problems


def judge_diag(lines: list[dict], stored: StoredPairs | None,
               plan_problems: list[str] | None = None) -> dict:
    """Plan 3 .. 5 with rev1 on the D-A lines.

    ``verdict`` = ``verdict_rev1``: ``branch`` / ``stop`` / ``undecidable`` / ``incomplete``;
    ``branch_rev1`` is the DR1-3 branch (``stop`` on H-D1, None before a branch is read).
    ``verdict_literal`` (``branch`` / ``needs_decision`` / ``no_branch``) and ``asks``
    (DR1-5) report the readings before rev1.
    """
    out = {"plan_problems": list(plan_problems or []),
           "errors": sum(1 for line in lines if rj.is_error(line)), "branch_rev1": None}
    by_name, missing = _by_candidate(lines)
    if out["plan_problems"]:
        return {**out, "verdict": VERDICT_STOP, "verdict_rev1": VERDICT_STOP, "stop": "H-D0"}
    if missing:
        return {**out, "verdict": "incomplete", "verdict_rev1": "incomplete",
                "problems": missing}
    per_line = {name: line_problems(by_name[name]) for name in CANDIDATE_NAMES}
    d0c = d0c_problems(by_name["P5"], by_name["P5r4"])
    h_d1 = [text for name in CANDIDATE_NAMES for text in per_line[name]] + d0c
    h_d3 = identity_problems([by_name[name] for name in CANDIDATE_NAMES])
    out.update(h_d1=h_d1, h_d3=h_d3,
               d0={"D-0a": _status(hash_problem(by_name["P0"]) is None),
                   "D-0b": _status(hash_problem(by_name["P5r4"]) is None),
                   "D-0c": _status(not d0c), "D-0c_problems": d0c})
    if h_d1:
        return {**out, "verdict": VERDICT_STOP, "verdict_rev1": VERDICT_STOP, "stop": "H-D1",
                "branch_rev1": BRANCH_STOP}
    if h_d3:
        return {**out, "verdict": VERDICT_STOP, "verdict_rev1": VERDICT_STOP, "stop": "H-D3"}
    out["d0"]["D-0d"] = d0d(by_name["P0"], by_name["P5r4"], stored)
    d0_pass = out["d0"]["D-0d"]["status"] == STATUS_TRUE
    w1_out, w2_out = w1(by_name["P0"]), w2(by_name["P5r4"])
    w3_out, b1_out = w3(by_name["P5r4"]), b1(by_name["P0"], by_name["P5"])
    branches = branches_of(d0_pass, w1_out, w2_out, w3_out, b1_out)
    alternative = _alternative_branches(d0_pass, w1_out, w2_out, w3_out, b1_out)
    branch = branch_rev1(out["d0"], w1_out, w2_out, w3_out, by_name["P5"])
    verdict = verdict_of_rev1(branch)
    out.update(W1=w1_out, W2=w2_out, W3=w3_out, B1=b1_out, branches_literal=branches,
               branches_alternative_reading=alternative,
               alternative_reading_note=ALTERNATIVE_READING_NOTE,
               verdict_literal=literal_verdict(branches, alternative), branch_rev1=branch,
               asks=rev1_asks(branches, branch),
               summaries={name: _soil(by_name[name]) for name in CANDIDATE_NAMES})
    if branch == BRANCH_STOP:
        out["stop"] = "H-D1"
    return {**out, "verdict": verdict, "verdict_rev1": verdict}


# ------------------------------------------------------------------------------- batch check
def make_checker():
    """``check(record, bundle, state, stored, k3_keys, identity)`` of ``rev.run_batch`` for D-A:
    identity, tag, K-A8, D-0a / D-0b per line and D-0c once P5 and P5r4 are both in (H-D1)."""
    seen: dict[str, dict] = {}

    def check(record, bundle, state, stored, k3_keys, current_identity) -> None:
        rev_entry = record["rev"]
        problems = fb.identity_mismatch(rev_entry.get("identity"), current_identity)
        if problems:
            state.stop = f"run identity changed during the batch: {problems[:3]}"
            return
        found = line_problems(record)
        seen[rev_entry["candidate"]] = record
        if not found and "P5" in seen and "P5r4" in seen:
            found = d0c_problems(seen["P5"], seen["P5r4"])
        if found:
            print(f"H-D1 {rev_entry['candidate']}: {found}", flush=True)
            state.stop = f"H-D1 {rev_entry['candidate']}: {found}"

    return check


# ------------------------------------------------------------------------------- report / CLI
def report_markdown(result: dict, source: Path) -> str:
    """A short Markdown report of :func:`judge_diag`."""
    lines = [f"# diagA judge ({source})", "",
             f"- verdict (rev1): **{result['verdict']}**, branch_rev1: "
             f"**{result.get('branch_rev1')}**"]
    for name in ("stop", "asks", "plan_problems", "problems", "h_d1", "h_d3"):
        if result.get(name):
            lines.append(f"- {name}: {result[name]}")
    if "d0" in result:
        lines.append(f"- D-0: {json.dumps(result['d0'], default=str)}")
    for name in ("W1", "W2", "W3", "B1"):
        if name in result:
            lines.append(f"- {name}: {json.dumps(result[name], default=str)}")
    if "branches_literal" in result:
        lines += [f"- branches (as written): {result['branches_literal']}, verdict_literal: "
                  f"{result['verdict_literal']}",
                  f"- branches (W-1 boundary column, W-3 t_rel <= t_S; not the rev1 reading): "
                  f"{result['branches_alternative_reading']}"]
    for name, summary in (result.get("summaries") or {}).items():
        lines.append(f"- {name} soil_summary: {json.dumps(summary, default=str)}")
    return "\n".join(lines) + "\n"


def _json_value(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value.item() if hasattr(value, "item") else str(value)


def _parse_args(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run_judge = sub.add_parser("judge", help="plan 3 .. 5 on a diagA.jsonl")
    run_judge.add_argument("path", type=Path, nargs="?", default=DEFAULT_OUT)
    run_judge.add_argument("--stored-l", type=Path, default=STORED_L_PATH)
    run_judge.add_argument("--stored-p5r4", type=Path, default=STORED_P5R4_PATH,
                           help="revA2 revA_RS.jsonl (main checkout, not in git)")
    run_judge.add_argument("--out", type=Path, default=None, help="new Markdown file")
    run_judge.add_argument("--json-out", type=Path, default=None, help="new JSON file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    for path in (args.out, args.json_out):
        if path is not None and path.exists():
            print(f"input error: {path} exists (new files only)")
            return 2
    try:
        lines = rj.read_lines(args.path)
        stored = load_stored_pairs(args.stored_l, args.stored_p5r4)
    except (OSError, ValueError) as exc:
        print(f"input error: {exc!r}")
        return 2
    result = judge_diag(lines, stored, seal_problems())
    report = report_markdown(result, args.path)
    print(report)
    if args.out is not None:
        with args.out.open("x", encoding="utf-8") as handle:
            handle.write(report)
    if args.json_out is not None:
        with args.json_out.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=1, default=_json_value)
    print(json.dumps({"verdict": result["verdict"], "branch_rev1": result.get("branch_rev1"),
                      "branches_literal": result.get("branches_literal"),
                      "asks": result.get("asks"), "stop": result.get("stop")},
                     default=_json_value))
    return 0 if result["verdict"] == VERDICT_BRANCH else 1


if __name__ == "__main__":
    sys.exit(main())
