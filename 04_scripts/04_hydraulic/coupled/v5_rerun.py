"""V0 / VB settings of the paper v5 U-3 / U-6 reruns on the reduced-harness screens.

Source: ``06_analysis/02_control/verif_matrix/u3_u6_rerun_rules.md`` (sealed 2026-11-08) 1-3
and 7. The screens (``s9_slope_fix_candidates``, ``r72_g6_screen``, ``s9_soil_slope``,
``b5_baseline_compare``) take ``--v5-setting {V0,VB}``; without it nothing here is imported and
their runs stay bit for bit as before.

Settings (``run_v5.SETTINGS``, the definition of ``run_v5.py`` and ``d1_runs``):
  V0  flow limit off, no v5 plant option; controller ``final_C4G2`` (preset ``with_10hz_d1``).
  VB  flow limit eta_v 0.85 (priority) + M2 ``flow_limited_r5`` + LC 0.02 / 0.05 s + the
      controller lock window following the plant; the harness valve lag is fixed at
      ``harness_hydraulics.HARNESS_VALVE_TAU_S`` (0.1 s, the ``s9_batch.v5_vb_argv`` soil-row
      value). Controller ``final_C4G2_P3`` (``extend_start_tracked``, ③ revision 4).
  U-6 ABL / IND under VB: the VB plant without the ③ bound (:func:`options_of`
  ``extend_start=False``); tags ``ABL`` / ``IND``.
Since the LAS-b switch the built C2 config adds ``_LAS`` (:func:`controller_tag`); the judge
expects the rules rev2 1 tags (:data:`SETTING_TAGS_LAS`, IND unchanged).

The parent sets :data:`SETTING_ENV` (:func:`activate`); every spawned worker inherits it and
installs the setting once (:func:`install_in_worker`). Each run record gets a ``v5`` block
(:func:`run_record`), each output file a ``v5`` meta (:func:`file_meta`).

Outputs (rules rev2 1 #9 / #10): the default file of a rerun is in ``v5_rerun/las/``
(:func:`default_out_path`); :func:`check_out_path` refuses an existing file without
``--overwrite`` and never writes a file directly in ``v5_rerun/`` (the pre-switch outputs).
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
S9_DIR = ROOT / "04_scripts" / "03_control" / "s9"

SETTINGS = ("V0", "VB")
SETTING_ENV = "V5_RERUN_SETTING"
SETTING_OPTION = "--v5-setting"
IDS_FROM_OPTION = "--ids-from"
PAD_OPTION = "--pad"
REUSE_OPTION = "--reuse-d1"
OVERWRITE_OPTION = "--overwrite"
TAG_V0 = "final_C4G2"
TAG_VB = "final_C4G2_P3"
TAG_ABL = "ABL"
TAG_IND = "IND"
TAG_V0_LAS = "final_C4G2_LAS"
TAG_VB_LAS = "final_C4G2_P3_LAS"
TAG_ABL_LAS = "ABL_LAS"
"""Tags since the LAS-b switch (``u3_u6_rerun_rules_rev2.md`` 1): V0, VB / U-6 C2 and ABL
with LAS-b; IND keeps ``IND`` (no LAS-b, user decision Q1 = I-2)."""
TAG_IND_LAS = "IND_LAS"
"""U-6 record-only column (rules rev2 3): IND + the head-force slowdown; its own name, not
``IND`` + the ``_LAS`` suffix rule (the C8 skeleton has no C2 config)."""
INDUSTRY_NAMES = (TAG_IND, TAG_IND_LAS)
"""C8-skeleton controllers: no ③, no C2 lock window or preset check, J-P3 not applicable."""
SETTING_TAGS_LAS = {"V0": TAG_V0_LAS, "VB": TAG_VB_LAS}
"""Rules rev2 1 #1 / #2: the U-3 (and D-1 reuse) tag of each setting."""
PRE_SWITCH_TAGS = (TAG_V0, TAG_VB, TAG_ABL)
"""Tags of runs before the LAS-b switch: rev2 1 #4 stops a bundle that has one (G-2)."""
J_P3_NOT_APPLICABLE = "not_applicable"
RULES_PATH = ROOT / "06_analysis" / "02_control" / "verif_matrix" / "u3_u6_rerun_rules.md"
OUT_DIR = ROOT / "06_analysis" / "02_control" / "v5_rerun"
LAS_OUT_DIR = OUT_DIR / "las"
"""Rules rev2 1 #9: the LAS-tag outputs (the judge reads this folder only)."""
PRE_SWITCH_OUT_DIR = OUT_DIR
"""Folder of the pre-switch outputs (e.g. ``u3_slope_V0.json``, untracked): rules rev2 1 #9 /
#10 keep them unmoved and unchanged for the command-hash comparison, so
:func:`check_out_path` refuses to write a file directly in it (``--overwrite`` included)."""
PAD_A_KEY_FIELD = "PA"
WIDE_PREFIXES = ("S|", "G|")
"""``b5_baseline_compare`` wide ids: ``S|<slope id>`` / ``G|<g6 key>``."""

_STATE: dict = {}
"""Per-worker state: the installed setting and options (one setting per process)."""


@dataclasses.dataclass(frozen=True)
class RerunOptions:
    """The rerun options of one screen invocation (all None: the screen as before)."""

    setting: str | None = None
    ids_from: Path | None = None
    pad: str | None = None
    reuse_d1: Path | None = None
    overwrite: bool = False
    """``--overwrite``: a rerun may replace its existing output file (:func:`check_out_path`)."""

    @property
    def is_active(self) -> bool:
        return self.setting is not None


# ------------------------------------------------------------------------------------ options
def add_arguments(parser: argparse.ArgumentParser, *, with_reuse: bool = False) -> None:
    """Add ``--v5-setting``, ``--ids-from``, ``--pad`` (and ``--reuse-d1``) to ``parser``."""
    group = parser.add_argument_group("paper v5 U-3 / U-6 rerun (u3_u6_rerun_rules.md)")
    group.add_argument(SETTING_OPTION, dest="v5_setting", choices=SETTINGS, default=None,
                       help="V0 (final_C4G2, plant options off) or VB (v5 VB plant + "
                            "final_C4G2_P3); default: the screen as before")
    group.add_argument(IDS_FROM_OPTION, dest="ids_from", type=Path, default=None,
                       help="run exactly the keys of this v4 result file (records[].id, "
                            "results[].key / .id, records[].case)")
    group.add_argument(PAD_OPTION, dest="pad", choices=("A", "B"), default=None,
                       help="with --ids-from: keep the keys of this pad (rigid p3b keys and "
                            "keys without a pad field count as pad B)")
    group.add_argument(OVERWRITE_OPTION, dest="overwrite", action="store_true",
                       help="with --v5-setting: replace an existing output file (refused "
                            "without it). A file directly in v5_rerun/ (pre-switch outputs, "
                            "rules rev2 1 #9 / #10) is never written, even with this option")
    if with_reuse:
        group.add_argument(REUSE_OPTION, dest="reuse_d1", type=Path, default=None,
                           help="reuse D-1 runs (run_v5 v5/d1_las.jsonl, LAS tags only, "
                                "rules rev2 1 #6) under rules 6 Q-1 .. Q-5")


def options_from_args(args: argparse.Namespace) -> RerunOptions:
    """The :class:`RerunOptions` of parsed arguments (checked).

    Raises:
        SystemExit: ``--reuse-d1`` without ``--v5-setting``, or ``--pad`` without
            ``--ids-from``.
    """
    options = RerunOptions(setting=getattr(args, "v5_setting", None),
                           ids_from=getattr(args, "ids_from", None),
                           pad=getattr(args, "pad", None),
                           reuse_d1=getattr(args, "reuse_d1", None),
                           overwrite=bool(getattr(args, "overwrite", False)))
    _check_options(options)
    return options


def split_argv(argv: list[str]) -> tuple[list[str], RerunOptions]:
    """``argv`` without the rerun options and the options (positional CLIs, ``r72``).

    Raises:
        SystemExit: An option without its value, an unknown setting or an invalid combination.
    """
    values: dict[str, str] = {}
    rest = []
    index = 0
    names = (SETTING_OPTION, IDS_FROM_OPTION, PAD_OPTION)
    overwrite = False
    while index < len(argv):
        if argv[index] == OVERWRITE_OPTION:
            overwrite = True
            index += 1
            continue
        if argv[index] in names:
            if index + 1 >= len(argv):
                raise SystemExit(f"{argv[index]} needs a value")
            values[argv[index]] = argv[index + 1]
            index += 2
            continue
        rest.append(argv[index])
        index += 1
    setting = values.get(SETTING_OPTION)
    if setting is not None and setting not in SETTINGS:
        raise SystemExit(f"{SETTING_OPTION} must be one of {SETTINGS}, got {setting!r}")
    pad = values.get(PAD_OPTION)
    if pad is not None and pad not in ("A", "B"):
        raise SystemExit(f"{PAD_OPTION} must be A or B, got {pad!r}")
    ids_from = values.get(IDS_FROM_OPTION)
    options = RerunOptions(setting=setting, ids_from=None if ids_from is None else Path(ids_from),
                           pad=pad, overwrite=overwrite)
    _check_options(options)
    return rest, options


def _check_options(options: RerunOptions) -> None:
    if options.reuse_d1 is not None and options.setting is None:
        raise SystemExit(f"{REUSE_OPTION} needs {SETTING_OPTION}")
    if options.pad is not None and options.ids_from is None:
        raise SystemExit(f"{PAD_OPTION} needs {IDS_FROM_OPTION}")


def default_out_path(bundle: str, setting: str, *, study: str = "u3") -> Path:
    """``06_analysis/02_control/v5_rerun/las/<study>_<bundle>_<setting>.json`` (rules 3.1 4,
    folder rules rev2 1 #9).

    Every ``--v5-setting`` run since the LAS-b switch is a LAS-tag run (the screens build the
    switched preset and have no LAS-off option), so its file goes to :data:`LAS_OUT_DIR`, the
    folder ``u3_judge`` reads. The file name is the one of the sealed rules.
    """
    return LAS_OUT_DIR / f"{study}_{bundle}_{setting}.json"


def _is_in_pre_switch_folder(path: Path) -> bool:
    return Path(path).resolve().parent == PRE_SWITCH_OUT_DIR.resolve()


def refuse_pre_switch_file(path: Path) -> None:
    """Refuse to write over an existing file directly in ``v5_rerun/`` (rules rev2 1 #9 / #10).

    Raises:
        SystemExit: ``path`` is an existing file directly in :data:`PRE_SWITCH_OUT_DIR`.
    """
    if _is_in_pre_switch_folder(path) and Path(path).exists():
        raise SystemExit(f"{path} is a pre-switch output in {PRE_SWITCH_OUT_DIR.name}/ (kept for "
                         "the command-hash comparison, rules rev2 1 #9 / #10); not overwritten, "
                         f"{OVERWRITE_OPTION} included. Write LAS-tag runs to "
                         f"{LAS_OUT_DIR.relative_to(ROOT).as_posix()}/")


def check_out_path(path: Path, options: RerunOptions) -> None:
    """Check the output file of a screen run before the runs start.

    Any run: an existing file directly in ``v5_rerun/`` is refused
    (:func:`refuse_pre_switch_file`). A rerun (``--v5-setting``) also refuses a new file
    there (its LAS-tag output belongs in ``v5_rerun/las/``) and an existing file anywhere
    unless ``--overwrite``. Without ``--v5-setting`` other paths behave as before.

    Raises:
        SystemExit: One of the refusals above.
    """
    refuse_pre_switch_file(path)
    if not options.is_active:
        return
    if _is_in_pre_switch_folder(path):
        raise SystemExit(f"{path}: a --v5-setting run is a LAS-tag run; write it to "
                         f"{LAS_OUT_DIR.relative_to(ROOT).as_posix()}/, not directly in "
                         f"{PRE_SWITCH_OUT_DIR.name}/ (rules rev2 1 #9)")
    if Path(path).exists() and not options.overwrite:
        raise SystemExit(f"{path} exists; pass {OVERWRITE_OPTION} to replace it")


# ---------------------------------------------------------------------------------- key lists
def pad_of_key(key: str) -> str:
    """Pad of a stored v4 key: ``|PA`` suffix A, a third field ``A`` / ``B``, otherwise B
    (g6 / g8 keys and the rigid p3b keys carry no pad field; their screens run pad B)."""
    for prefix in WIDE_PREFIXES:
        if key.startswith(prefix):
            key = key[len(prefix):]
            break
    fields = key.split("|")
    if fields[-1] == PAD_A_KEY_FIELD:
        return "A"
    if len(fields) >= 3 and fields[2] in ("A", "B"):
        return fields[2]
    return "B"


def stored_entries(path: Path) -> list[dict]:
    """``records`` (fix candidates, b5) or ``results`` (r72, s9_soil_slope) of a v4 file."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload.get("records") or payload.get("results") or []


def entry_key(entry: dict) -> str:
    """Key of a stored entry: ``id`` (fix candidates, s9_soil_slope), ``key`` (r72),
    ``case`` (b5)."""
    for name in ("id", "key", "case"):
        if entry.get(name) is not None:
            return str(entry[name])
    raise KeyError(f"stored entry without id / key / case: {sorted(entry)[:8]}")


def ids_from(path: Path, pad: str | None = None, suites: tuple[str, ...] | None = None
             ) -> list[str]:
    """Keys of a stored v4 file in file order (unique), filtered by pad and suite.

    Args:
        path: v4 result file.
        pad: Keep only the keys of this pad (None: all).
        suites: Keep only the records of these fix-candidates suites (None: all).
    """
    keys: list[str] = []
    for entry in stored_entries(path):
        if suites is not None and entry.get("suite") is not None and entry["suite"] not in suites:
            continue
        key = entry_key(entry)
        if (pad is None or pad_of_key(key) == pad) and key not in keys:
            keys.append(key)
    return keys


def select_known(keys: list[str], known: list[str]) -> list[str]:
    """``keys`` in their order.

    Raises:
        SystemExit: A key that the screen does not have (rules 7 G-1: every key is a v4 key).
    """
    unknown = sorted(set(keys) - set(known))
    if unknown:
        raise SystemExit(f"{len(unknown)} --ids-from keys are no job of this screen: "
                         f"{unknown[:5]}")
    return list(keys)


# --------------------------------------------------------------------------------- the setting
def activate(setting: str | None) -> None:
    """Parent: name the setting for the workers (spawned children inherit the environment)."""
    if setting is not None:
        os.environ[SETTING_ENV] = setting


def setting_name() -> str | None:
    return os.environ.get(SETTING_ENV) or None


def _coupled_modules():
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    if str(S9_DIR) not in sys.path:
        sys.path.insert(0, str(S9_DIR))
    import run_v5
    import verdict_runs

    return run_v5, verdict_runs


def options_of(setting: str, *, extend_start: bool = True):
    """(``FlowSetting``, ``HydraulicOptions`` or None) of a setting; ``extend_start`` False
    drops the ③ bound (U-6 ABL / IND: the VB plant only)."""
    run_v5, _ = _coupled_modules()
    flow, options = run_v5.options_of(setting)
    if options is not None and not extend_start and options.extend_start_tracked:
        options = dataclasses.replace(options, extend_start_tracked=False)
    return flow, options


def install_in_worker(*, extend_start: bool = True):
    """Install the named setting in this worker once (plant options and the record-only 10 Hz
    controller log of ``verdict_runs``); returns its ``HydraulicOptions`` (None: no setting or
    no plant option).

    Raises:
        RuntimeError: Another setting or ③ choice is installed in this process already.
    """
    name = setting_name()
    if name is None:
        return None
    wanted = (name, extend_start)
    if _STATE.get("installed") is not None:
        if _STATE["installed"] != wanted:
            raise RuntimeError(f"v5 rerun setting {_STATE['installed']} installed, {wanted} asked")
        return _STATE["options"]
    _, verdict_runs = _coupled_modules()
    flow, options = options_of(name, extend_start=extend_start)
    verdict_runs.install_plant_options(flow, options)
    verdict_runs.install_logged_controller()
    _STATE.update(installed=wanted, options=options, flow=flow)
    return options


def installed_options():
    return _STATE.get("options")


# ------------------------------------------------------------------------------------ records
def extend_start_record(controller) -> dict:
    """③ rule and revision of the run's two-pressure settings (None for a non-C2 controller)."""
    meta = getattr(controller, "meta", None)
    if meta is None:
        return {"rule": None, "revision": None}
    settings = (meta().get("two_pressure") or {}).get("settings") or {}
    return {"rule": settings.get("extend_start_rule"),
            "revision": (settings.get("extend_start_bound") or {}).get("revision")}


def controller_tag(options, controller_name: str = "C2", config=None) -> str:
    """Rules 1 / 7 G-2 tag: V0 ``final_C4G2``, VB C2 ``final_C4G2_P3``, U-6 ``ABL`` / ``IND``.

    ``config`` = the C2 config the run built: with LAS-b on (switch 2026-11-08) the tag gets
    ``_LAS`` (``final_C4G2_LAS``, ``final_C4G2_P3_LAS``, ``ABL_LAS``), with the K1 order gate on
    (K1 switch, ``las_k1_rules_adopt.md`` 9.2) then ``_K1`` (``final_C4G2_P3_LAS_K1``,
    ``ABL_LAS_K1``). The setting definition (:func:`definition`, its sealed digest) is built
    without it and keeps the tag before them.
    """
    from outrigger_sim.hydraulics.v5_options import with_switch_tags

    if controller_name in (TAG_ABL, *INDUSTRY_NAMES):
        tag = controller_name
    elif options is not None and options.extend_start_tracked:
        tag = TAG_VB
    else:
        tag = TAG_V0
    return with_switch_tags(tag, config)


def has_rod_reading(controller) -> bool:
    """A rod-side pressure reached the controller (logged C2 period log, or the observer of
    :func:`observe_rod_readings`)."""
    if getattr(controller, "_v5_rod_seen", None) is not None:
        return bool(controller._v5_rod_seen)
    log = controller.__dict__.get("period_log") if hasattr(controller, "__dict__") else None
    if not log:
        return False
    return any(any(math.isfinite(float(v)) for v in row[7][2]) for row in log)


def observe_rod_readings(controller) -> None:
    """Record on ``controller`` whether its updates ever get a rod-side pressure (instance
    wrapper of ``update``; record only, the output is unchanged)."""
    controller._v5_rod_seen = False
    inner = controller.update

    def update(measurements):
        rod_Pa = getattr(measurements, "rod_pressure_Pa", None)
        if rod_Pa is not None and any(math.isfinite(float(v)) for v in rod_Pa):
            controller._v5_rod_seen = True
        return inner(measurements)

    controller.update = update


def j_p3_status(tag: str, bound_check: dict | None, rod_reading: bool,
                head_only_declared: bool) -> str:
    """J-P3 of one run (v5 criteria revision 8 / 9): ``pass`` / ``H-7`` / ``no_rod_reading`` /
    ``setting_defect`` with the ③ bound (``v5_options.is_extend_start_tag``: base tag
    ``final_C4G2_P3`` with any LAS-b / K1 suffixes), else ``not_applicable``."""
    from outrigger_sim.hydraulics.v5_options import is_extend_start_tag

    if not is_extend_start_tag(tag):
        return J_P3_NOT_APPLICABLE
    from outrigger_sim.control.extend_start_bound import (
        J_P3_JUDGED,
        J_P3_NO_ROD_READING,
        j_p3_run_case,
    )

    case = j_p3_run_case(bound_check, rod_reading, head_only_declared)
    if case == J_P3_JUDGED:
        return "H-7" if sum((bound_check or {}).get("breach_reads") or []) else "pass"
    return "no_rod_reading" if case == J_P3_NO_ROD_READING else "setting_defect"


FALLBACK_EVENT_PREFIX = "WARN_ROD_PRESSURE_FALLBACK"
"""Rod-pressure fallback of the two-pressure monitor (rules rev1 G-6: 0 in every g8 VB run)."""


def fallback_event_count(controller) -> int:
    """Number of ``WARN_ROD_PRESSURE_FALLBACK:<leg>`` events of the run's controller."""
    events = getattr(controller, "events", None) or []
    return sum(1 for event in events if event.name.startswith(FALLBACK_EVENT_PREFIX))


LAS_EVENTS_KEY = "las_events"
"""LAS rules rev4b 3: record-only LAS-b events and FAULT names of the run (``las_h7``)."""


def las_events_of(controller) -> dict:
    """``las_h7.las_events_record`` of the run's controller events (read after the run; the
    commands and their hash are the screen's, so this record cannot change them)."""
    import las_h7

    return las_h7.las_events_record(getattr(controller, "events", None) or [])


def _lift_time_s(plant, period: dict) -> float | None:
    limiter = getattr(plant, "flow_limiter", None)
    if limiter is None or len(period["t"]) == 0:
        return None
    import verdict_metrics

    return verdict_metrics.first_lift_time_s(limiter.rows(), period["t"], period["phase"])


def run_record(plant, controller, *, harness_commands_sha256: str | None,
               controller_name: str = "C2", head_only_declared: bool = True) -> dict:
    """The ``v5`` block of one run (empty without a setting).

    Args:
        plant: The run's harness plant (None if the screen did not keep it).
        controller: The run's controller.
        harness_commands_sha256: The screen's own command hash of the run.
        controller_name: ``C2`` (U-3, U-6 C2), ``ABL`` or ``IND``.
        head_only_declared: The run was set up without rod readings (criteria revision 9 3.1;
            every U-3 / U-6 screen reads head pressures only, rules 1).
    """
    name = setting_name()
    if name is None:
        return {}
    _, verdict_runs = _coupled_modules()
    import harness_hydraulics

    options = installed_options()
    period = verdict_runs.period_arrays(controller) if hasattr(controller, "__dict__") else None
    t_lift_s = None if plant is None or period is None else _lift_time_s(plant, period)
    tag = controller_tag(options, controller_name, getattr(controller, "config", None))
    hydraulics = harness_hydraulics.plant_record(plant, t_lift_s) if options is not None else {}
    bound_check = hydraulics.get("extend_bound_check")
    rod_reading = has_rod_reading(controller)
    record = {"v5_setting": name, "controller_tag": tag,
              "extend_start": extend_start_record(controller),
              "hydraulic_options": None if options is None else options.to_dict(),
              "definition_sha256": definition_sha256(name, controller_name),
              "code": _worker_code_commit(),
              "head_only_declared": head_only_declared, "has_rod_reading": rod_reading,
              "j_p3": j_p3_status(tag, bound_check, rod_reading, head_only_declared),
              "commands_sha256": harness_commands_sha256,
              "logged_commands_sha256": (
                  None if not period or not len(period["t"])
                  else verdict_runs._command_digest(period["command"])),
              "t_lift_s": t_lift_s,
              "rod_pressure_fallback_events": fallback_event_count(controller),
              LAS_EVENTS_KEY: las_events_of(controller)}
    if bound_check is not None:
        record["extend_bound_check"] = bound_check
    if hydraulics:
        record["hydraulics_record"] = hydraulics
    has_lock_record = plant is not None and getattr(plant, "lock_events", None) is not None
    if has_lock_record and controller_name not in INDUSTRY_NAMES:  # J11 reads the C2 window
        record["lock_window_alignment"] = verdict_runs.lock_window_record(plant, controller,
                                                                          period)
    _check_built_preset(options, controller_name)
    return record


def _worker_code_commit() -> dict:
    """:func:`code_commit` once per worker process (the code a process runs does not change)."""
    if "code" not in _STATE:
        _STATE["code"] = code_commit()
    return _STATE["code"]


def _check_built_preset(options, controller_name: str) -> None:
    """Criteria P-4 / revision 8 3.1 checks of a C2 run (``verdict_runs.plant_options_record``)."""
    if options is None or controller_name in INDUSTRY_NAMES:
        return
    import harness_hydraulics
    from params import load_params

    if options.lock_window_follows_plant:
        harness_hydraulics.check_last_lock_window(options, load_params().v_max)
    harness_hydraulics.check_last_extend_start(options)


# --------------------------------------------------------------------------------------- meta
def definition(setting: str, controller_name: str = "C2") -> dict:
    """The setting definition a run used (flow setting, plant options, controller tag)."""
    flow, options = options_of(setting,
                               extend_start=controller_name not in (TAG_ABL, *INDUSTRY_NAMES))
    return {"setting": setting, "flow_setting": flow.to_dict(),
            "hydraulic_options": None if options is None else options.to_dict(),
            "controller_tag": controller_tag(options, controller_name)}


def definition_sha256(setting: str, controller_name: str = "C2") -> str:
    text = json.dumps(definition(setting, controller_name), sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def code_commit() -> dict:
    """``git rev-parse HEAD`` of the project and whether ``03_src`` / ``04_scripts`` differ
    from it (None when git is not available)."""
    try:
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], check=True,
                              capture_output=True, text=True).stdout.strip()
        status = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--",
                                 "03_src", "04_scripts"], check=True, capture_output=True,
                                text=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}
    return {"commit": head, "dirty": bool(status.strip())}


def text_sha256(path: Path) -> str | None:
    """SHA-256 of a text file with LF line ends (None without the file)."""
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def file_meta(options: RerunOptions, keys: list[str] | None = None,
              controllers: tuple[str, ...] = ("C2",)) -> dict:
    """The ``v5`` meta of an output file (empty without a setting)."""
    if options.setting is None:
        return {}
    return {"v5_setting": options.setting,
            "controller_tags": {name: definition(options.setting, name)["controller_tag"]
                                for name in controllers},
            "definitions": {name: definition(options.setting, name) for name in controllers},
            "definition_sha256": {name: definition_sha256(options.setting, name)
                                  for name in controllers},
            "code": code_commit(), "rules": RULES_PATH.name,
            "rules_sha256": text_sha256(RULES_PATH), "head_only_declared": True,
            "ids_from": None if options.ids_from is None else str(options.ids_from),
            "ids_from_sha256": (None if options.ids_from is None
                                else text_sha256(Path(options.ids_from))),
            "pad": options.pad, "n_keys": None if keys is None else len(keys),
            "commands_sha256": "per run: v5.commands_sha256 (screen hash) and "
                               "v5.logged_commands_sha256 (verdict_runs log)"}
