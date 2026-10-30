"""B5 baseline comparison (paper v4 review B5, paper section 4.10): C2 vs. ablation vs. IND.

Runs the project C2 (R8 preset of the reduced S9 harness), an ablation of it and an
"industry-style" baseline on the reduced closed-loop harness (``s9_soil_closed_loop.run_case``,
no Chrono), with one set of truth metrics for every controller. Moved from the control-expert
prototype (scratchpad ``b5_run.py``, 2026-10-30); same CLI, same cases, same command hashes.

Controllers (``--controllers``):
  C2    project preset ``cl.preset_config(COMBINED, imu, reapproach)`` = ``with_10hz_d1`` minus
        CHECK / zero calibration / REANCHOR / target check (the harness preset of every S9
        study).
  ABL   C2 with the soil response (U-S9-C1, incl. the P-S8-28 LOC anchor) and P-S8-28..35 off:
        lift_stroke_guard, stroke-end re-ground entry, twist_completion_relax,
        pre_loc_lift_pause, slope_clearance_margin, liftoff_window_reapproach, loc_revoke,
        diff_sink back to their (off) defaults. Config switches only. The final-controller
        switches of spec 429.11 are set off explicitly (``lift_stroke_guard.soil_stop`` False =
        no P-S8-36 SGS, ``slope_clearance_margin.flat_soil_margin_m`` 0 = no R4), so ABL stays
        the soil-response-off baseline whatever the preset defaults are.
  ABL28 attribution run: ABL with the soil response back on (LOC anchor off).
  IND   industry-style baseline on ``control/c8.py`` (C8 skeleton, comparison doc 7.2 alt. 1):
        pressure-threshold touchdown (1.5 F_min), four legs extended together to the
        stroke-based crawler clearance 50 mm, highest-leg attitude trim (P on the height
        deficit), pressure-threshold re-ground (1.5 F_min). No load distribution, no probe,
        no combined judge, no soil response. Harness parity with C2: 10 Hz, output one period
        late (d = 1), increment limit 0.25 v_max per period (ramp 0.4 s), attitude low-pass
        0.8 s x 2 on the 10 ms IMU samples (:class:`IndustryC8`, :class:`HarnessIndustry`).
        SGS and R4 are C2 config switches; IND has neither (meta ``controller_settings``
        None).
The C2 / ABL / IND values of these switches go into every record and the result meta
(``controller_settings``).

Cases (``--cases``): ids of ``CASES`` below, ``all`` (= ``CASES``), ``wide`` (every slope-suite
id as ``S|<id>`` and every g6-suite key as ``G|<key>``, harness defaults) or ``oos`` (the 100
out-of-sample cases ``b5_oos_cases.OOS_CASES``: ``X|<soil>|<pad>|<level>|<roll>,<pitch>|Fs<f>``
on the slope harness, ``G|g6x|...`` on the g6 harness), comma separated. An ``X|`` id is built
as ``SlopeCase(group="X")`` with its settle-table row; a soil case without a row is rejected
unless ``--allow-no-settle-row`` (run uncorrected) or ``--skip-no-settle-row`` (left out).
Out-of-sample ids must not repeat a study-1 (177) or G6 (116) harness key (ValueError).
``--official`` adds the official judgement of the same run (``b5_official.py``): the R2DS path
(slope: judge_case + settle check v2; g6: r72 gates + the G6-7 demotion), the C2 event rows NA
for IND; fields ``official_verdict``, ``official_verdict_strict`` (NA = failed),
``official_failed_rows``, ``official_flags``, ``official_na_rows``.
Harness paths:
  slope  s9_soil_slope cases (settle table hook_harness attached), as the slope suite
  g6     r72 per-pad soil (one weak pad), as the g6 suite
  Extra keys: ``fs_kN`` override, ``event`` = (leg, depth m, duration s, delay after READY s)
  floor drop injected through ``plant.goff`` (rigid floor of the slope harness only; a soil
  case with an event is rejected), ``hold_s`` READY hold.

Truth metrics (identical for every controller): READY, FAULT, end attitude, min true F_cyl
after the crawler lift-off and after READY with the time below F_min (10 Hz windows of the
1 ms minimum), crawler load at / after READY, false LOC (LOC period crawler >= 0.01 W),
all-node crawler floor clearance at READY, max head-equivalent pressure (oil-column force /
A_head, 1 ms, moving and locked), max motor stroke.

Usage (dynamics-dev, numba; PowerShell):
  conda run -n dynamics-dev python -I b5_baseline_compare.py run --cases A1-rigid \
      --controllers C2 --workers 1 --affinity 0x00000002 --out smoke.json
  python -I b5_baseline_compare.py run --cases oos --controllers C2,ABL,IND --official \
      --workers 4 --affinity 0x0F000000 --out 06_analysis/02_control/s9/rev84/b5_oos.json
  python -I b5_baseline_compare.py list
``--out`` defaults to ``06_analysis/02_control/s9/rev84/b5_<main|wide|oos|cases>.json``. Table and
figure: ``b5_baseline_table.py`` and ``b5_baseline_figure.py``. Units SI unless the key says
otherwise (mm, kN, bar, deg, s).
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import sys
import time
import traceback
from dataclasses import dataclass, replace
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("MKL_THREADING_LAYER", "TBB")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
S9_DIR = ROOT / "04_scripts" / "03_control" / "s9"
S8_DIR = ROOT / "04_scripts" / "03_control" / "s8"
for _path in (ROOT / "03_src", S9_DIR, S8_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import b5_oos_cases as oos  # noqa: E402

from outrigger_sim.control import c8  # noqa: E402
from outrigger_sim.control.c2 import C2Phase, _SoilState  # noqa: E402
from outrigger_sim.control.two_pressure import BODY_MASS_WITHOUT_YAML_KG  # noqa: E402
from outrigger_sim.sensors.attitude import AttitudeEstimator, CascadedLowPass  # noqa: E402
from outrigger_sim.sensors.imu import STANDARD_GRAVITY_M_S2  # noqa: E402
from outrigger_sim.signals import Command  # noqa: E402

SETTLE_TABLE_PATH = ROOT / "06_analysis" / "00_dynamics" / "slope_crawler_settle.json"
DEFAULT_OUT_DIR = ROOT / "06_analysis" / "02_control" / "s9" / "rev84"
CONTROLLERS = ("C2", "ABL", "IND", "ABL28")
LEGS = ("FL", "FR", "RL", "RR")
RIGID_SOIL = "rigid"
LOC_EVENT = "crawler_liftoff_confirmed"
FALSE_LOC_WEIGHT_FRACTION = 0.01
RUT_MIN_MM = 25.0
ATT_TOL_DEG = 0.2
STROKE_GATE_MM = 684.8
PA_PER_BAR = 1e5
MOVING_SPEED_EPS = 1e-6
"""Command or valve magnitude above which a 1 ms chunk counts as moving (pressure split)."""
TIME_EPS_S = 1e-9

# IND harness parity with the C2 preset (module docstring)
IND_PERIOD_S = 0.1
IND_OUTPUT_RAMP_S = 0.4
"""0 -> v_max in 0.4 s at 10 Hz = increment limit 0.25 v_max per period."""
IND_ATTITUDE_TIME_CONSTANT_S = 0.8
IND_ATTITUDE_STAGES = 2
IMU_SAMPLE_PERIOD_S = 0.01

CASES: dict[str, dict] = {
    # A1 ground type (flat, top, pad B, F_s 4 kN)
    "A1-rigid": {"harness": "slope", "src": "H5|rigid|B|top|flat"},
    "A1-G1": {"harness": "slope", "src": "H1|G1|B|top|flat"},
    "A1-J1": {"harness": "slope", "src": "H1|J1|B|top|flat"},
    "A1-J2": {"harness": "slope", "src": "H1|J2|B|top|flat"},
    # A2 slope
    "A2-rigid-roll4.4": {"harness": "slope", "src": "H5|rigid|B|top|roll_pos"},
    "A2-J1B-roll0.75": {"harness": "slope", "src": "H3|J1|B|top|roll_pos@k0.75"},
    "A2-J1B-nd0.75": {"harness": "slope", "src": "H3|J1|B|top|nose_down@k0.75"},
    "A2-J1B-edge0.75": {"harness": "slope", "src": "H3|J1|B|top|edge_nd@k0.75"},
    # A3 one weak pad (G6)
    "A3-G1+J1@RR": {"harness": "g6", "src": "g6|G1+J1@RR|top|Fs4"},
    "A3-G1+J1@FL": {"harness": "g6", "src": "g6|G1+J1@FL|top|Fs4"},
    # A4 floor drop under RR after READY (G4-like: 11.5 mm in 2 s), rigid flat
    "A4-G4RR-Fs0": {"harness": "slope", "src": "H5|rigid|B|top|flat", "fs_kN": 0.0,
                    "event": ("RR", 0.0115, 2.0, 2.0), "hold_s": 30.0},
    "A4-G4RR-Fs8": {"harness": "slope", "src": "H5|rigid|B|top|flat", "fs_kN": 8.0,
                    "event": ("RR", 0.0115, 2.0, 2.0), "hold_s": 30.0},
    # B1 auger (pair with A1-J2)
    "B1-J2B-bottom": {"harness": "slope", "src": "H2|J2|B|bottom|flat"},
    # B2 seal friction (pair with A1-rigid F_s 4)
    "B2-rigid-Fs0": {"harness": "slope", "src": "H5|rigid|B|top|flat", "fs_kN": 0.0},
    "B2-rigid-Fs8": {"harness": "slope", "src": "H5|rigid|B|top|flat", "fs_kN": 8.0},
    # B3 pad (pair with A1-J1)
    "B3-J1A": {"harness": "slope", "src": "H1|J1|A|top|flat"},
}
CASE_DISPLAY_NAMES: dict[str, str] = {
    "A1-rigid": "강체 평지",
    "A1-G1": "G1 평지",
    "A1-J1": "J1 평지",
    "A1-J2": "J2 평지",
    "A2-rigid-roll4.4": "강체 좌우 4.4°",
    # floor angles of the src, k x direction limit of s9_soil_slope.SLOPES_DEG (k = 0.75)
    "A2-J1B-roll0.75": "J1 좌우 3.3°",
    "A2-J1B-nd0.75": "J1 앞내림 2.4°",
    "A2-J1B-edge0.75": "J1 모서리 1.65°·1.2°",
    "A3-G1+J1@RR": "G1+J1 연약부 RR",
    "A3-G1+J1@FL": "G1+J1 연약부 FL",
    "A4-G4RR-Fs0": "RR 침하 사건 F_s 0",
    "A4-G4RR-Fs8": "RR 침하 사건 F_s 8",
    "B1-J2B-bottom": "J2 오거 하단",
    "B2-rigid-Fs0": "강체 F_s 0",
    "B2-rigid-Fs8": "강체 F_s 8",
    "B3-J1A": "J1 패드 A",
}
"""Short display names of the table cases for the paper table and figure (user decision
2026-10-30). Slopes are floor angles (edge: roll·pitch); F_s is the seal friction in kN.
Plain text: :func:`case_display_name` writes F_s as math for LaTeX and matplotlib. The table
and the figure list the cases in ``CASES`` order."""
SEAL_FRICTION_TEXT = "F_s"
SEAL_FRICTION_MATH = "$F_s$"
WIDE_PREFIX = {"S|": "slope", "G|": "g6"}
"""Wide set (``--cases wide``): every slope-suite id as ``S|<id>`` (177) and every g6-suite key
as ``G|<key>`` (116), harness defaults (no override, no event)."""
OOS_FIELDS_BEFORE_PITCH = 4
"""``|`` count of an ``X|`` id cut at the comma of its angles
(``X|<soil>|<pad>|<level>|<roll>``)."""

_RUN: dict = {}
"""Per-worker state of the running case (controller, hooks, logs); one job per process."""


# ------------------------------------------------------------------------------------- cases
def case_display_name(case_id: str, *, as_math: bool = False) -> str:
    """Display name of a table case, F_s as ``$F_s$`` when ``as_math`` (LaTeX, matplotlib).

    Raises:
        KeyError: ``case_id`` is not a table case.
    """
    name = CASE_DISPLAY_NAMES[case_id]
    if as_math:
        return name.replace(SEAL_FRICTION_TEXT, SEAL_FRICTION_MATH)
    return name


def case_group(case_id: str) -> str:
    """Independent-variable symbol of a table case (``"A2-J1B-nd0.75"`` -> ``"A2"``)."""
    return case_id.split("-")[0]


def check_event_allowed(case_id: str, spec: dict) -> None:
    """Reject a floor-drop event outside the rigid floor of the slope harness.

    The event moves ``plant.goff``, the offset of the rigid floor; a soil floor ignores it, so
    the run would silently have no event.

    Raises:
        ValueError: ``spec`` has an ``event`` and is not a rigid slope-harness case.
    """
    if "event" not in spec:
        return
    soil = spec["src"].split("|")[1] if spec["harness"] == "slope" else None
    if soil != RIGID_SOIL:
        raise ValueError(f"{case_id}: a floor-drop event needs the rigid floor of the slope "
                         f"harness, got harness {spec['harness']!r} src {spec['src']!r}")


def case_spec(case_id: str) -> dict:
    """Case spec of a table id, a wide-set id (``S|...`` / ``G|...``) or an out-of-sample
    slope id (``X|...``, src = the id itself, parsed).

    Raises:
        KeyError: Unknown case id.
        ValueError: The case has a floor-drop event on a soil floor, or a malformed ``X|`` id.
    """
    if case_id in CASES:
        spec = CASES[case_id]
    elif case_id.startswith(oos.OOS_SLOPE_PREFIX):
        oos.parse_slope_case(case_id)
        spec = {"harness": "slope", "src": case_id}
    else:
        spec = _wide_case_spec(case_id)
    check_event_allowed(case_id, spec)
    return spec


def settle_row_problems(case_ids: list[str], settle_rows: dict, *,
                        allow_no_settle_row: bool) -> dict[str, str]:
    """``{case id: reason}`` of the ``X|`` soil ids without a settle-table row."""
    problems = {}
    for case_id in case_ids:
        if not case_id.startswith(oos.OOS_SLOPE_PREFIX):
            continue
        try:
            oos.slope_case_payload(case_id, settle_rows, allow_no_settle_row=allow_no_settle_row)
        except oos.NoSettleRowError as exc:
            problems[case_id] = str(exc)
    return problems


def check_oos_overlap(case_ids: list[str]) -> None:
    """Out-of-sample ids against study 1 (177) and the G6 screen (116).

    Raises:
        ValueError: An out-of-sample id repeats an in-sample harness key or another id.
    """
    oos_ids = [case_id for case_id in case_ids if oos.is_oos_id(case_id)]
    if not oos_ids:
        return
    import s9_soil_slope as slope

    with _argv_as_root():
        import r72_g6_screen as g6
    g6_keys = g6.all_jobs("all") + g6.all_jobs("rigid_all")
    oos.check_no_overlap(oos_ids, oos.in_sample_keys(slope.build_cases(), g6_keys))


def load_settle_rows() -> dict:
    """``hook_harness`` rows of the dynamics settle table."""
    return json.loads(SETTLE_TABLE_PATH.read_text(encoding="utf-8"))["hook_harness"]


def _wide_case_spec(case_id: str) -> dict:
    for prefix, harness in WIDE_PREFIX.items():
        if case_id.startswith(prefix):
            return {"harness": harness, "src": case_id[len(prefix):]}
    raise KeyError(case_id)


def wide_ids() -> list[str]:
    """Every slope-suite id (``S|``) and every g6-suite key (``G|``)."""
    import s9_soil_slope as slope

    ids = [f"S|{case.to_dict()['id']}" for case in slope.build_cases()]
    with _argv_as_root():
        import r72_g6_screen as g6
    ids += [f"G|{key}" for key in g6.all_jobs("all") + g6.all_jobs("rigid_all")]
    return ids


@contextlib.contextmanager
def _argv_as_root():
    """``r72_g6_screen`` reads the project root from ``sys.argv[1]`` at import time."""
    saved = sys.argv
    sys.argv = [saved[0] if saved else "", str(ROOT)]
    try:
        yield
    finally:
        sys.argv = saved


# ------------------------------------------------------------------------------- controllers
def ablation_config(c2, config):
    """C2 config with the soil response and P-S8-28 .. P-S8-35 off (switches only).

    The final-controller switches (spec 429.11: SGS ``soil_stop``, R4 ``flat_soil_margin_m``)
    are set off by value, not left to the settings defaults: the R8 preset turns them on.
    """
    return replace(
        config,
        soil=c2.SoilResponseSettings(),
        lift_stroke_guard=c2.LiftStrokeGuardSettings(soil_stop=False),
        fault_reground=replace(config.fault_reground, stroke_end_entry=False),
        twist_completion_relax=c2.TwistCompletionRelaxSettings(),
        pre_loc_lift_pause=c2.PreLocLiftPauseSettings(),
        slope_clearance_margin=c2.SlopeClearanceMarginSettings(flat_soil_margin_m=0.0),
        liftoff_window_reapproach=c2.LiftoffWindowReapproachSettings(),
        loc_revoke=c2.LocRevokeSettings(),
        diff_sink=c2.DiffSinkSettings(),
    )


@dataclass(frozen=True)
class PhaseEvent:
    """Controller event in the shape ``run_case`` reads from ``ctrl.events``."""

    t_s: float
    name: str


class IndustryC8(c8.C8Controller):
    """C8 skeleton with the C2 harness parity: 10 Hz, ramp 0.4 s, 100 Hz attitude filter on
    the 10 ms IMU samples and the command output one period late (d = 1)."""

    def __init__(self, geometry, settings: c8.C8Settings | None = None) -> None:
        settings = settings or c8.C8Settings(period_s=IND_PERIOD_S,
                                             output_ramp_time_s=IND_OUTPUT_RAMP_S)
        super().__init__(geometry, settings)
        self._attitude = AttitudeEstimator(CascadedLowPass(
            IND_ATTITUDE_TIME_CONSTANT_S, IND_ATTITUDE_STAGES, IMU_SAMPLE_PERIOD_S))
        self.reset()

    def reset(self) -> None:
        super().reset()
        self._delayed_speeds_m_s = np.zeros(4)

    def _update_filters(self, measurements) -> None:
        """Run the attitude filter on every IMU sample of the period (C2 parity)."""
        samples = measurements.imu_specific_force_samples_m_s2
        if samples is None:
            samples = [measurements.specific_force_m_s2]
        for sample in samples:
            estimate = self._attitude.update(measurements.t_s, sample)
        self._roll_rad, self._pitch_rad = estimate.roll_rad, estimate.pitch_rad
        slow = self._completion_filter.update([estimate.roll_rad, estimate.pitch_rad])
        self._slow_roll_rad, self._slow_pitch_rad = float(slow[0]), float(slow[1])

    def update(self, measurements) -> Command:
        """Return the C8 command of the previous period (output delay d = 1)."""
        command = super().update(measurements)
        delayed = self._delayed_speeds_m_s
        self._delayed_speeds_m_s = np.array(command.leg_speed_m_s, float)
        return Command(t_s=measurements.t_s, leg_speed_m_s=delayed)


IND_PHASE_AS_C2 = {
    "touch": C2Phase.TOUCH, "attitude": C2Phase.LEVEL, "lift": C2Phase.LEVEL,
    "reground": C2Phase.LEVEL, "trim": C2Phase.LEVEL, "done": C2Phase.DONE,
    "ready": C2Phase.READY,
}
"""C8 phase -> the C2 phase that ``run_case`` keys its READY / DONE bookkeeping on."""


@dataclass
class IndustryRunState:
    """The part of the C2 run state the slope judge log reads (IND never re-anchors)."""

    reanchor_anchor_pitch_rad: float | None = None


class HarnessIndustry:
    """IND in the C2 surface that ``run_case`` reads (``phase`` as ``C2Phase``, ``events``,
    ``probe_history``); every C8 phase change is an ``ind_phase:<phase>`` event.

    The official judges (``b5_official``) also read C2 internals; IND answers them neutrally:
    a default (empty) soil state, ``W_ref`` as C2 computes it, no clearance estimate (nan) and
    no REANCHOR anchor. The rows built on them are NA for IND."""

    name = "IND"

    def __init__(self, inner: IndustryC8) -> None:
        self.inner = inner
        self.geometry = inner.geometry
        self.period_s = inner.period_s
        self.events: list[PhaseEvent] = []
        self.probe_history: list = []
        self._last_phase = str(inner.phase)
        self._state = IndustryRunState()
        self._neutral_soil_state = _SoilState()

    @property
    def phase(self) -> C2Phase:
        return IND_PHASE_AS_C2[str(self.inner.phase)]

    def _soil_state(self) -> _SoilState:
        return self._neutral_soil_state

    def _reference_weight_N(self) -> float:
        """``W_ref`` as ``C2Controller._reference_weight_N``: YAML superstructure mass x g."""
        mass_kg = self.geometry.superstructure_mass_kg
        if mass_kg is None:
            mass_kg = BODY_MASS_WITHOUT_YAML_KG
        return mass_kg * STANDARD_GRAVITY_M_S2

    def _clearance_estimate_m(self, rod_stroke_m) -> float:
        del rod_stroke_m  # IND keeps no crawler clearance estimate of its own
        return math.nan

    def reset(self) -> None:
        self.inner.reset()
        self.events.clear()
        self._last_phase = str(self.inner.phase)

    def update(self, measurements) -> Command:
        command = self.inner.update(measurements)
        phase = str(self.inner.phase)
        if phase != self._last_phase:
            self.events.append(PhaseEvent(float(measurements.t_s), f"ind_phase:{phase}"))
            self._last_phase = phase
        return command


def _c2_config(cl, c2, name: str, variant: dict):
    config = cl.preset_config(c2.ContactJudge.COMBINED, with_imu_samples=True,
                              with_reapproach=True)
    if variant.get("reanchor"):
        config = replace(config, reanchor=replace(config.reanchor, enable=True))
    if name == "ABL":
        return ablation_config(c2, config)
    if name == "ABL28":  # attribution: soil response on, P-S8-28 .. 35 off
        soil = replace(config.soil, loc_anchor_enable=False)
        return replace(ablation_config(c2, config), soil=soil)
    return config


def make_factory(name: str):
    """``make_controller(cl, c2, variant)`` replacement for the harness, controller ``name``."""

    def factory(cl, c2, variant):
        if name == "IND":
            ctrl = HarnessIndustry(IndustryC8.from_params(cl.PARAMS))
        else:
            ctrl = c2.C2Controller.from_params(cl.PARAMS, _c2_config(cl, c2, name, variant))
        ctrl.reset()
        _RUN["ctrl"] = ctrl
        on_created = _RUN.get("on_controller_created")
        if on_created is not None:  # --official: the judge's capture of the settle state
            on_created(cl, ctrl)
        return ctrl

    return factory


IND_CONTROLLER_SETTINGS = {"soil_stop": None, "soil_stop_scope": None,
                           "flat_soil_margin_m": None}
"""IND (C8 skeleton) has no SGS and no R4: the C2 switches do not exist there."""


def controller_settings(ctrl) -> dict:
    """Final-controller switches (spec 429.11) of a built controller, for the result meta.

    Returns:
        ``soil_stop`` (P-S8-36 SGS), ``soil_stop_scope`` and ``flat_soil_margin_m`` (R4, m);
        all None for IND.
    """
    if isinstance(ctrl, HarnessIndustry):
        return dict(IND_CONTROLLER_SETTINGS)
    guard = ctrl.config.lift_stroke_guard
    return {"soil_stop": bool(guard.soil_stop), "soil_stop_scope": guard.soil_stop_scope,
            "flat_soil_margin_m": float(ctrl.config.slope_clearance_margin.flat_soil_margin_m)}


def settings_meta(records: list[dict]) -> dict:
    """``{controller: settings}`` from the records; a controller whose records disagree gets
    the list of its distinct settings (a mixed batch shows up in the meta)."""
    distinct: dict[str, list[dict]] = {}
    for record in records:
        settings = record.get("controller_settings")
        if settings is None:
            continue
        seen = distinct.setdefault(record["controller"], [])
        if settings not in seen:
            seen.append(settings)
    return {name: values[0] if len(values) == 1 else values
            for name, values in distinct.items()}


# ------------------------------------------------------------------------------------- hooks
def _apply_floor_drop(plant) -> None:
    """Lower the rigid floor under the event leg linearly from READY + delay."""
    event = _RUN.get("event")
    if event is None or _RUN.get("t_ready_s") is None:
        return
    leg, depth_m, duration_s, delay_s = event
    t_start_s = _RUN["t_ready_s"] + delay_s
    if plant.t < t_start_s - 1e-12:
        return
    fraction = min(max((plant.t - t_start_s) / duration_s, 0.0), 1.0)
    plant.goff[LEGS.index(leg)] = depth_m * fraction
    _RUN.setdefault("t_event_s", t_start_s)


def _install_step_hook(cl) -> None:
    """Wrap ``cl._lagged_step`` once: per 1 ms chunk crawler force, max oil-column force per leg
    split moving / locked, and the optional floor-drop event (rigid floor ``plant.goff``)."""
    if getattr(cl._lagged_step, "is_b5_hook", False):
        return
    inner = cl._lagged_step

    def hooked(plant, command, valve, steps):
        _apply_floor_drop(plant)
        is_moving = ((np.abs(np.asarray(command, float)) > MOVING_SPEED_EPS)
                     | (np.abs(valve) > MOVING_SPEED_EPS))
        accumulated = inner(plant, command, valve, steps)
        peak_N = np.asarray(accumulated[16:20], float).copy()
        _RUN["pmax_move_N"] = np.maximum(_RUN["pmax_move_N"],
                                         np.where(is_moving, peak_N, -np.inf))
        _RUN["pmax_lock_N"] = np.maximum(_RUN["pmax_lock_N"],
                                         np.where(is_moving, -np.inf, peak_N))
        _RUN["crawler"].append((float(plant.t), float(accumulated[15])))
        return accumulated

    # keep the marker attributes of the hooks already in the chain (late_loc_rule and others)
    markers = {key: value for key, value in getattr(inner, "__dict__", {}).items()
               if key.startswith("is_")}
    hooked.__dict__.update(markers)
    hooked.is_b5_hook = True
    cl._lagged_step = hooked


def _wrap_control_period(sl, base_period):
    """Record READY time, the all-node crawler clearance at READY and a per-period log row
    ``(t, phase, true minimum F_cyl per leg, crawler max)``."""

    def period(cl, Measurements, plant, cmd, valve, ha, period_s, rec, sens=None):
        measurements = base_period(cl, Measurements, plant, cmd, valve, ha, period_s, rec, sens)
        ctrl = _RUN.get("ctrl")
        phase = str(ctrl.phase) if ctrl is not None else "?"
        if phase == "ready" and _RUN.get("t_ready_s") is None:
            _RUN["t_ready_s"] = float(plant.t)
            _RUN["rut_all_ready_mm"] = float(np.min(sl.crawler_node_heights(cl, plant))) * 1e3
        _RUN["log"].append((float(plant.t), phase, np.asarray(rec["fmin"], float).copy(),
                            float(rec["crmax"])))
        return measurements

    return period


# ----------------------------------------------------------------------------------- one job
def _slope_case(src: str, *, allow_no_settle_row: bool = False) -> dict:
    """Slope case payload with its settle-table row: a study-1 id or an ``X|`` id."""
    import s9_soil_slope as slope

    table = load_settle_rows()
    if src.startswith(oos.OOS_SLOPE_PREFIX):
        return oos.slope_case_payload(src, table, allow_no_settle_row=allow_no_settle_row)
    for case in slope.attach_settle_table(slope.build_cases(), table):
        payload = case.to_dict()
        if payload["id"] == src:
            return payload
    raise KeyError(src)


def _prepare_slope_run(spec: dict, job: dict):
    """Install the slope-suite patches; return the patched harness module, its input and the
    case payload. ``--official`` logs through ``s9_soil_slope._control_period_logged`` and
    captures the settle state as ``_make_project_controller`` does."""
    import s9_soil_slope as slope

    sl = slope._install_patches()
    case = _slope_case(spec["src"], allow_no_settle_row=job.get("allow_no_settle_row", False))
    if "fs_kN" in spec:
        case["fs_kN"] = spec["fs_kN"]
    slope._CAP.clear()
    slope._CAP["crawler_series"] = []
    slope._CAP["settle"] = None
    row = case.get("settle_table")
    slope._CAP["settle_table"] = slope.SettleTableRow(**row) if row else None
    slope._CAP["case"] = case
    if job.get("official"):
        import b5_official

        # spec 427.9 SL-1 soil-guard stop reads the moving pressure record (as run_one)
        slope._CAP["moving_pressure"] = slope.soil_guard_stop_rule.MovingPressureRecord()
        base_period = slope._control_period_logged
        _RUN["on_controller_created"] = b5_official.capture_slope_start
    else:
        base_period = slope._ORIGINALS["control_period"]
    sl.control_period = _wrap_control_period(sl, base_period)
    run_input = slope.run_case_input(case)
    if "fs_kN" in spec:
        run_input["fs_kN"] = spec["fs_kN"]
    return sl, run_input, case


def _import_g6():
    with _argv_as_root():
        import r72_g6_screen as g6
    return g6


def _prepare_g6_run(sl, spec: dict) -> dict:
    """Install the g6-suite patches on ``sl``; return the run input."""
    g6 = _import_g6()
    g6._install()
    g6._CAP.clear()
    g6._CAP["crawler_series"] = []
    sl.control_period = _wrap_control_period(sl, g6._ORIG_CONTROL_PERIOD)
    _tag, soil, level, fs = spec["src"].split("|")
    return {"id": spec["src"], "soil": soil, "pad": "B", "level": level,
            "fs_kN": float(fs[2:]), "variant": {}}


def _run_g6_job_official(sl, controller: str, src: str) -> tuple[dict, dict]:
    """Run ``r72_g6_screen.job(src)`` with the b5 controller and hooks; return the r72 record
    and the ``run_case`` output.

    ``job`` re-installs its patches through the module names, so the b5 factory replaces
    ``make_controller_preset`` (filling the r72 capture) and the b5 period wrapper sits on
    ``control_period_logged`` (keeping the r72 F_cyl log)."""
    g6 = _import_g6()
    factory = make_factory(controller)

    def factory_with_r72_capture(cl, c2, variant):
        ctrl = factory(cl, c2, variant)
        g6._CAP["ctrl"] = ctrl
        if "plant" in g6._CAP:  # as make_controller_preset: right after the settle
            g6._CAP["node_d0"] = sl.crawler_node_heights(cl, g6._CAP["plant"])
        return ctrl

    original_logged = g6.control_period_logged
    original_run_case = sl.run_case

    def run_case_recorded(case: dict) -> dict:
        _RUN["out"] = original_run_case(case)
        return _RUN["out"]

    g6.make_controller_preset = factory_with_r72_capture
    g6.control_period_logged = _wrap_control_period(sl, original_logged)
    sl.run_case = run_case_recorded
    rec = g6.job(src)
    return rec, _RUN.get("out")


def _new_run_state(spec: dict) -> None:
    _RUN.clear()
    _RUN.update(pmax_move_N=np.full(4, -np.inf), pmax_lock_N=np.full(4, -np.inf),
                crawler=[], log=[], event=spec.get("event"))


def run_job(job: dict) -> dict:
    """Run one (case, controller) job; errors go into the record (the batch keeps going)."""
    t0 = time.perf_counter()
    case_id, controller = job["case"], job["controller"]
    is_official = bool(job.get("official"))
    record = {"case": case_id, "src": None, "controller": controller}
    if oos.is_oos_id(case_id):
        record["oos_batch"] = oos.oos_batch(case_id)
    try:
        spec = case_spec(case_id)
        record["src"] = spec["src"]
        import late_loc_rule
        import s9_soil_closed_loop as sl

        _new_run_state(spec)
        if spec["harness"] == "slope":
            sl, run_input, slope_case = _prepare_slope_run(spec, job)
        else:
            run_input = _prepare_g6_run(sl, spec)
        cl = sl._imports()[0]
        late_loc_rule.install_crawler_recorder(cl, lambda: None)  # keep the marker chain
        _install_step_hook(cl)
        sl.make_controller = make_factory(controller)
        if "hold_s" in spec:
            sl.HOLD_AFTER_READY_S = float(spec["hold_s"])
        official = {}
        if is_official and spec["harness"] == "g6":
            rec, out = _run_g6_job_official(sl, controller, spec["src"])
            official = _judge_g6_official(rec, controller)
        elif is_official:
            out = sl.run_case(run_input)
            official = _judge_slope_official(slope_case, out, sl, cl, controller)
        else:
            out = sl.run_case(run_input)
        record.update(metrics(out, _RUN["ctrl"]))
        record.update(official)
    except Exception as exc:  # noqa: BLE001  keep the batch going; the record carries it
        record.update(error=repr(exc), tb=traceback.format_exc()[-3000:])
    if _RUN.get("ctrl") is not None:
        record["controller_settings"] = controller_settings(_RUN["ctrl"])
    record["wall_s"] = round(time.perf_counter() - t0, 1)
    return record


def _judge_slope_official(case: dict, out: dict, sl, cl, controller: str) -> dict:
    import b5_official

    settle_table = json.loads(SETTLE_TABLE_PATH.read_text(encoding="utf-8"))
    return b5_official.judge_slope(case, out, sl, cl, settle_table,
                                   is_industry=controller == "IND")


def _judge_g6_official(rec: dict, controller: str) -> dict:
    import b5_official

    return b5_official.judge_g6(rec, is_industry=controller == "IND")


# ----------------------------------------------------------------------------------- metrics
def _time_below_fmin_s(rows, t_from_s, F_min_N: float, period_s: float) -> float | None:
    """Time after ``t_from_s`` with a period minimum F_cyl below F_min (s)."""
    if t_from_s is None:
        return None
    return round(sum(period_s for t, _, fmin, _ in rows
                     if t > t_from_s + TIME_EPS_S and float(np.min(fmin)) < F_min_N), 2)


def _false_locs(loc_times_s, crawler: np.ndarray, period_s: float, weight_N: float) -> list:
    """LOC events whose period still had a crawler force >= 0.01 W."""
    false_loc = []
    for t in loc_times_s:
        in_period = (crawler[:, 0] > t - period_s - TIME_EPS_S) & (crawler[:, 0] <= t + TIME_EPS_S)
        window = crawler[in_period, 1]
        peak_N = float(window.max()) if window.size else 0.0
        if peak_N >= FALSE_LOC_WEIGHT_FRACTION * weight_N:
            false_loc.append({"t_s": round(t, 2), "crawler_kN": round(peak_N / 1e3, 2)})
    return false_loc


def _min_force_after_event_kN(rows) -> float | None:
    t_event_s = _RUN.get("t_event_s")
    if t_event_s is None:
        return None
    values = [float(np.min(fmin)) for t, _, fmin, _ in rows if t > t_event_s + TIME_EPS_S]
    return round(min(values) / 1e3, 2) if values else None


def _lite_gates(out: dict, is_fault: bool, is_crawler_fail: bool, att_end, F_min_N) -> dict:
    """B5 lite gate: the same truth rows for every controller (no controller events)."""
    t_ready = out.get("t_ready_s")
    min_off = out.get("min_true_Fcyl_after_off_kN")
    rut_all = _RUN.get("rut_all_ready_mm")
    return {
        "ready_no_fault": bool(t_ready is not None and not is_fault),
        "crawler": bool(t_ready is not None and not is_crawler_fail
                        and (out.get("n_crawler_recontact") or 0) == 0),
        "Fmin": bool(min_off is not None and min_off >= F_min_N / 1e3),
        "att": bool(np.all(np.abs(att_end) <= ATT_TOL_DEG)),
        "rut": bool(rut_all is not None and rut_all >= RUT_MIN_MM),
        "stroke": bool(out.get("max_motor_stroke_mm", 1e9) <= STROKE_GATE_MM),
    }


def _pressure_fields(head_area_m2: np.ndarray) -> dict:
    p_move_bar = _RUN["pmax_move_N"] / head_area_m2 / PA_PER_BAR
    p_lock_bar = _RUN["pmax_lock_N"] / head_area_m2 / PA_PER_BAR
    has_move = np.isfinite(p_move_bar).any()
    return {
        "p_max_move_bar": round(float(np.max(p_move_bar)), 2) if has_move else None,
        "p_max_lock_bar": (round(float(np.max(p_lock_bar)), 2)
                           if np.isfinite(p_lock_bar).any() else None),
        "p_max_move_leg": LEGS[int(np.argmax(p_move_bar))] if has_move else None,
    }


def metrics(out: dict, ctrl) -> dict:
    """Truth metrics of one run from the ``run_case`` output and the hook logs."""
    geometry = ctrl.geometry
    F_min_N = float(geometry.F_min_N)
    period_s = float(ctrl.period_s)
    rows = _RUN["log"]
    # cylinder share of the weight: a conservative scale for the 0.01 W rule (rods left out)
    weight_N = out["W_cyl_N"]
    crawler = np.array(_RUN["crawler"], float) if _RUN["crawler"] else np.zeros((0, 2))
    t_ready = out.get("t_ready_s")
    events = [(float(e.t_s), e.name) for e in ctrl.events]
    loc_times = [t for t, name in events if name.startswith(LOC_EVENT)]
    cr_ready = out.get("crawler_N_at_ready")
    cr_after = out.get("crawler_N_max_after_ready")
    is_crawler_fail = bool(t_ready is not None
                           and ((cr_ready or 0.0) > 0.0 or (cr_after or 0.0) > 0.0))
    att_end = out.get("att_end_deg") or [math.nan, math.nan]
    is_fault = str(out.get("final_phase")) in ("fault", "fault_reground") or any(
        name.startswith("FAULT") for _, name in events)
    t_off = out.get("t_crawler_off_first_s")
    gates = _lite_gates(out, is_fault, is_crawler_fail, att_end, F_min_N)
    rut_all = _RUN.get("rut_all_ready_mm")
    return {
        "lite_pass": all(gates.values()), "lite_gates": gates,
        "t_ready_s": t_ready, "final_phase": out.get("final_phase"), "fault": is_fault,
        "att_end_deg": [round(float(a), 4) for a in att_end],
        "att_end_absmax_deg": round(float(np.max(np.abs(att_end))), 4),
        "att_ok": bool(np.all(np.abs(att_end) <= ATT_TOL_DEG)),
        "F_min_kN": round(F_min_N / 1e3, 3),
        "min_Fcyl_after_off_kN": out.get("min_true_Fcyl_after_off_kN"),
        "below_Fmin_after_off_s": _time_below_fmin_s(rows, t_off, F_min_N, period_s),
        "min_Fcyl_after_ready_kN": out.get("min_true_Fcyl_after_ready_kN"),
        "below_Fmin_after_ready_s": _time_below_fmin_s(rows, t_ready, F_min_N, period_s),
        "t_event_s": _RUN.get("t_event_s"),
        "min_Fcyl_after_event_kN": _min_force_after_event_kN(rows),
        "crawler_N_at_ready": cr_ready, "crawler_N_max_after_ready": cr_after,
        "n_crawler_recontact": out.get("n_crawler_recontact"),
        "crawler_liftoff_fail": is_crawler_fail,
        "n_loc": len(loc_times),
        "false_loc": _false_locs(loc_times, crawler, period_s, weight_N),
        "rut_all_ready_mm": None if rut_all is None else round(rut_all, 2),
        "rut_settle_ready_mm": out.get("clear_true_ready_mm"),
        "clear_est_ready_mm": out.get("clear_est_ready_mm"),
        **_pressure_fields(np.asarray(geometry.head_area_m2, float)),
        "max_motor_stroke_mm": round(out.get("max_motor_stroke_mm"), 2),
        "commands_sha256": out.get("commands_sha256"),
        "warnings": sorted({name.split(":")[0] for _, name in events
                            if name.startswith(("WARN", "FAULT"))}),
        "phase_path": out.get("phase_path", [])[:20],
        "sim_end_s": rows[-1][0] if rows else None,
    }


# -------------------------------------------------------------------------------------- main
def set_affinity(mask_text: str | None) -> dict:
    """Pin this process (and the pool workers it spawns) to the hex mask ``mask_text``.

    Raises:
        RuntimeError: Windows did not apply the mask.
    """
    if not mask_text:
        return {}
    import ctypes

    mask = int(mask_text, 16)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    kernel32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    kernel32.GetProcessAffinityMask.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]
    handle = kernel32.GetCurrentProcess()
    is_set = bool(kernel32.SetProcessAffinityMask(handle, mask))
    process_mask, system_mask = ctypes.c_size_t(), ctypes.c_size_t()
    kernel32.GetProcessAffinityMask(handle, ctypes.byref(process_mask), ctypes.byref(system_mask))
    if not is_set or process_mask.value != mask:
        raise RuntimeError(f"affinity not applied: requested {hex(mask)}, "
                           f"got {hex(process_mask.value)}")
    return {"affinity": hex(process_mask.value)}


def resolve_case_ids(cases_arg: str) -> list[str]:
    """``all``, ``wide``, ``oos`` or a comma-separated id list."""
    if cases_arg == "all":
        return list(CASES)
    if cases_arg == "wide":
        return wide_ids()
    if cases_arg == "oos":
        return list(oos.OOS_CASES)
    return split_case_list(cases_arg)


def split_case_list(cases_arg: str) -> list[str]:
    """Comma-separated ids; the comma inside the ``<roll>,<pitch>`` field of an ``X|`` id
    stays in the id (``X|J1|B|top|0,2|Fs4,A1-rigid`` -> two ids)."""
    ids: list[str] = []
    for token in cases_arg.split(","):
        is_open_slope_id = (bool(ids) and ids[-1].startswith(oos.OOS_SLOPE_PREFIX)
                            and ids[-1].count("|") == OOS_FIELDS_BEFORE_PITCH)
        if is_open_slope_id:
            ids[-1] += f",{token}"
        else:
            ids.append(token)
    return ids


def default_out_path(cases_arg: str) -> Path:
    label = {"all": "main", "wide": "wide", "oos": "oos"}.get(cases_arg, "cases")
    return DEFAULT_OUT_DIR / f"b5_{label}.json"


def _invalid_arguments(case_ids: list[str], controllers: list[str]) -> list[str]:
    invalid = []
    for case_id in case_ids:
        try:
            case_spec(case_id)
        except KeyError:
            invalid.append(f"unknown case {case_id}")
        except ValueError as exc:
            invalid.append(str(exc))
    invalid += [f"unknown controller {name}" for name in controllers if name not in CONTROLLERS]
    return invalid


def _print_records(records: list[dict]) -> None:
    for record in records:
        if "error" in record:
            print(record["case"], record["controller"], "ERROR", record["error"])
            continue
        print(record["case"], record["controller"], {key: record.get(key) for key in (
            "t_ready_s", "final_phase", "att_end_absmax_deg", "min_Fcyl_after_off_kN",
            "below_Fmin_after_off_s", "crawler_liftoff_fail", "false_loc", "rut_all_ready_mm",
            "p_max_move_bar", "p_max_lock_bar", "official_verdict", "official_failed_rows",
            "wall_s") if key in record})


@dataclass(frozen=True)
class BatchOptions:
    """Per-job switches of a batch run."""

    is_official: bool = False
    allow_no_settle_row: bool = False


def run_batch(case_ids: list[str], controllers: list[str], workers: int,
              affinity: str | None, out_path: Path,
              options: BatchOptions | None = None) -> list[dict]:
    """Run every (case, controller) job and write ``{"meta", "records"}`` to ``out_path``."""
    options = options or BatchOptions()
    placement = set_affinity(affinity)
    jobs = [{"case": case_id, "controller": name, "official": options.is_official,
             "allow_no_settle_row": options.allow_no_settle_row}
            for case_id in case_ids for name in controllers]
    t0 = time.perf_counter()
    # one process per job: the harness patches (make_plant, control_period, hold time) and the
    # numba state never leak from one case into the next
    with Pool(max(1, workers), maxtasksperchild=1) as pool:
        records = pool.map(run_job, jobs, chunksize=1)
    meta = {"script": str(Path(__file__)), "jobs": len(jobs), "workers": workers,
            "official": options.is_official,
            "allow_no_settle_row": options.allow_no_settle_row,
            "settle_table_sha256": hashlib.sha256(SETTLE_TABLE_PATH.read_bytes()).hexdigest(),
            "controller_settings": settings_meta(records),
            "wall_s": round(time.perf_counter() - t0, 1), **placement}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"meta": meta, "records": records}, indent=1, default=float),
                        encoding="utf-8")
    return records


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="run the cases and write the result JSON")
    run.add_argument("--cases", default="all", help="all, wide, oos or comma-separated ids")
    run.add_argument("--controllers", default=",".join(CONTROLLERS))
    run.add_argument("--workers", type=int, default=1)
    run.add_argument("--affinity", default=None, help="hex mask, e.g. 0x00000002")
    run.add_argument("--out", type=Path, default=None,
                     help="result JSON (default rev84/b5_<main|wide|oos|cases>.json)")
    run.add_argument("--official", action="store_true",
                     help="add the official (R2DS) judgement of the same run")
    no_row = run.add_mutually_exclusive_group()
    no_row.add_argument("--allow-no-settle-row", action="store_true",
                        help="run X| soil cases without a settle-table row uncorrected")
    no_row.add_argument("--skip-no-settle-row", action="store_true",
                        help="leave out X| soil cases without a settle-table row")
    sub.add_parser("list", help="print the table cases and the out-of-sample cases")
    return parser.parse_args(argv)


def _without_unsettled_cases(case_ids: list[str], args: argparse.Namespace) -> list[str]:
    """Drop (``--skip-no-settle-row``) or reject the ``X|`` soil ids without a settle row.

    Raises:
        SystemExit: A soil id has no row and neither option was given.
    """
    problems = settle_row_problems(case_ids, load_settle_rows(),
                                   allow_no_settle_row=args.allow_no_settle_row)
    if not problems:
        return case_ids
    if not args.skip_no_settle_row:
        raise SystemExit("no settle-table row: " + "; ".join(problems.values()))
    print(f"skipped {len(problems)} case(s) without a settle-table row:", ", ".join(problems))
    return [case_id for case_id in case_ids if case_id not in problems]


def _print_case_list() -> None:
    for key, spec in CASES.items():
        print(key, spec)
    for batch, ids in oos.OOS_BATCH_IDS.items():
        for case_id in ids:
            print(batch, case_id)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.cmd == "list":
        _print_case_list()
        return
    case_ids = resolve_case_ids(args.cases)
    controllers = args.controllers.split(",")
    invalid = _invalid_arguments(case_ids, controllers)
    if invalid:
        raise SystemExit("invalid arguments: " + "; ".join(invalid))
    check_oos_overlap(case_ids)
    case_ids = _without_unsettled_cases(case_ids, args)
    out_path = args.out if args.out is not None else default_out_path(args.cases)
    options = BatchOptions(is_official=args.official,
                           allow_no_settle_row=args.allow_no_settle_row)
    records = run_batch(case_ids, controllers, args.workers, args.affinity, out_path, options)
    _print_records(records)


if __name__ == "__main__":
    main()
