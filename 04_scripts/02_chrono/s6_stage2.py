"""S6 stage 2: C2 closed-loop control matrix on the L1 Chrono model (case definitions + job).

``00_docs/04_control/s6_control_spec.md`` 3 (checks 1-8, T, R), 4 (matrix, 31 runs), 6 (G6 pad
record), rev. 2 (K1-K8), rev. 3 (16-20: J/I items, RE1 / RE2), rev. 4 (21-23: RE1b), rev. 5
(26-30: GE1 geometric cue, RE1c). Imported by ``run_S6.py`` (``plan2`` / ``run2`` / ``snaps2``);
summary ``s6_stage2_summary.py``.

Starts: settled on the crawler, one snapshot per (level, floor) built by :func:`job_snapshot`
(``07_results/states/S6_crawler_<level>_<floor>``, batch :data:`SNAPSHOT_BUNDLE`): analytic
``scenarios/crawler_slope`` pose, crawler anchor bushings (Q12) at zero deformation, in-plane
gravity ramp 3 s, settle 65.5 s. All 14 exist; a case refuses to start without its snapshot.

Controller: ``C2Controller.from_params(params, C2Config(...))`` with the C2 defaults of the
installed revision (R5: H5a REANCHOR after the first probe, B1′ CHECK gyro bias with T_b and
the motion condition, GE1′ shadow with the standstill gate; R4.1 parts: trapezoid probe, Q1,
Q2, K1) and per case: ``TargetSettings(slope_limit_mode=VERIFICATION,
crawler_settle_map=CrawlerSettleMap.for_level(level), acceptance=reject, check_time_s,
gyro_noise_std_rad_s=imu_config_for_grade(grade).gyro_noise_std_rad_s)`` (``check_time_s`` 0 in
G1 = no gyro bias removal, recorded; sigma_g recorded as ``settings.gyro_noise_std_*_passed``),
contact judge (pressure only / combined), H4 on / off, the combined probe verdict off only in G1
(reduced-model conditions).

Runner: ``command_delay_periods=1`` (ZOH + 1 control period), ``imu_method="chrono_point"``,
1 ms pad record (``chrono/pad_record.PadRecorder``, also the per-step minimum cylinder force of
each 1 ms). Sensors: IMU grade per case at C1 (``imu_config_for_grade`` incl. gyro errors);
leg sensors with the reduced-model noise (ASSUMPTION), seed 12345.

Scenario events (``on_control`` observer; the controller phase is read from the controller
object, never from the truth):

* ``settle_RR``: RR ground settles 11.5 mm in 2 s at first READY + 5 s (G4);
* ``settle_RR_30``: 30 mm in 5 s at first READY + 5 s (RE1b, spec 23);
* ``target_change``: ``request_target(pitch +3 deg)`` at first READY + 2 s (G5);
* ``retract_RR_25``: from first READY + 5 s the runner forces the command (wrapper
  :class:`ForcedRetract`, the controller keeps being updated so that its shadows run): RR at
  -0.25 v_max until its measured stroke has decreased 25 mm, all other legs 0 (RE1c, spec 30);
* ``drop_RR_30`` (RE1b-F, spec rev. 7 41.2): RR ground 30 mm in 0.05 s at first READY + 5 s
  (cavity collapse, ASSUMPTION): RR lifts off at once;
* ``drop_RR_30_probe`` (RE1b-P, spec rev. 7 41.2): the same drop at the first PROBE start +
  0.1 s (:data:`RE1BP_TIMING` ``"probe_start"``; ``"rr_turn"`` = when the probe round reaches
  RR, the fallback of 41.2 if PROBE does not stop the low-load re-level, see
  :data:`RE1BP_RELEVEL_CHECK`).

Contact-transition dt (RE1b-F / RE1b-P, spec 41.2 and 42.2, CLAUDE.md "접지 전환 1e-5 s"):
``runner.DtSchedule`` switches to YAML ``simulation.dt_transition_s`` (1e-5 s) from 2 s before
the drop (RE1b-P: from the PROBE start, 0.1 s before; the event time is not known earlier) and
keeps it until the drop + 2 s **and** the RR pad has been in contact (true normal force > 0)
for :data:`FINE_HOLD_S` without a break (re-touch included), at most :data:`FINE_MAX_S`; the
pieces are in ``result.json`` ``runner.dt_segments``; the pad record then samples on a 1 ms time
grid (``PadRecorder(sample_s=1e-3)``).

Seeds (spec rev. 7 41.3): ``Stage2Case.seed`` drives the sensor suite (default 12345); the G3
normal nose-down repeat cases ``..._s12346`` / ``..._s12347``. The G3 ``normal_zeroed`` /
``normal_zeroed_repeatability`` pair shares seed 12345 on purpose (zero-offset paired
comparison).

GE1′ series (spec rev. 7 37.3, 38, 42.1-42.2): every control period the controller attribute
``support_geometry`` (dict / dataclass) plus the controller attributes of
:data:`GE1_CONTROLLER_ATTRIBUTES` (``is_geometry_valid``, gate state) when they exist;
:func:`ge1_r5_preflight` checks the R5 names before a batch (``run_S6.py run2`` refuses to
start without them unless ``--no-ge1-check``).

Per case the result JSON records: phases, acceptance (CHECK code, crawler attitude, floor
estimates, A1 usage, settle map, X9 shadow), H4 outcome (``stroke_margin`` skip = "judgement
not possible", K4), stroke maximum and end margin, stroke margin per leg at every probe start,
``probe_skipped`` and other probe events, the controller meta (GE1 shadow keys included), the
floor plane ``{"normal_world", "offset_m"}`` (I4 crawler-box clearance) and, when the
controller exposes it, a 20 ms series of the GE1 shadow (:data:`GE1_ATTRIBUTES`).

Durations (spec 4, 16.2): CHECK 2 s (G1 0) + touchdown 17 s + levelling 18 s (H4 37 s, roll
5.5 deg 40 s) + probe 11 s (trapezoid) + READY 10 s; G4 + 40 s; RE1b + 65 s; RE1c + 30 s; G5
target 95 s (confirmed U38-a, :data:`T_TARGET`), reject 5 s + CHECK; RE1b-F / RE1b-P + 65 s.
Wall estimates: :func:`Stage2Case.wall_estimate_s`.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

LEVELS = ("top", "middle", "bottom")
FLOORS: dict[str, tuple[float, float]] = {
    "flat": (0.0, 0.0),
    "roll5.5": (5.5, 0.0),
    "fdown3.5": (0.0, 3.5),
    "fup3.5": (0.0, -3.5),
    "diag3": (3.0 / math.sqrt(2.0), 3.0 / math.sqrt(2.0)),
    "roll3": (3.0, 0.0),
}
"""Floor slope (roll, pitch) deg as in ``scenarios/slope`` (the attitude it would give a rigid
machine; theta > 0 = nose down, CLAUDE.md D8). The body attitude on the crawler adds the
crawler compliance (``scenarios/crawler_slope``, recorded per snapshot)."""
SNAPSHOTS = (
    [("top", f) for f in ("flat", "fdown3.5", "fup3.5", "roll5.5", "diag3", "roll3")]
    + [(lv, f) for lv in ("middle", "bottom") for f in ("flat", "roll5.5", "fdown3.5", "fup3.5")]
)
"""14 settled crawler snapshots (spec 4)."""
PREREQUISITES = {
    "NO_SNAPSHOT": "settled crawler snapshot missing: run `run_S6.py snaps2`",
}
SNAP_RAMP_S = 3.0
"""In-plane gravity ramp of the snapshot settle (half-cosine, ``scenarios/slope.gravity_ramp``):
the anchor bushings start at zero deformation and take the slope load gradually."""
SNAP_SETTLE_S = 65.5
"""Settle after the ramp: YAML ``simulation.settle_on_crawler_min_s`` 65.47 s rounded up (the
crawler rocking mode decays with about 8 s time constant, smoke run 2026-10-21)."""
CHECK_S = 2.0
T_TOUCH, T_LEVEL, T_LEVEL_H4, T_PROBE, T_READY = 17.0, 18.0, 37.0, 11.0, 10.0
"""T_PROBE 11 s: trapezoid probe about 10.6 s (spec 18.3)."""
T_RE1B_EXTRA, T_RE1C_EXTRA = 65.0, 30.0
"""RE1b: READY + 5 s settlement start, 5 s ramp, re-READY <= 60 s (ASSUMPTION); RE1c: READY +
5 s retract (4.4 s) + 25 s observation."""
RERUN_SETS: dict[str, tuple[str, ...]] = {
    "RE1": (
        "G2-R_top_fdown3.5", "G2-R_top_fup3.5", "G2-R_middle_fdown3.5", "G2-R_middle_fup3.5",
        "G2_top_flat", "G2_top_roll5.5", "G2_middle_flat", "G2_middle_roll5.5",
        "G3_top_fdown3.5_good_zeroed", "G3_top_fdown3.5_normal_zeroed",
        "G3_top_fdown3.5_normal_zeroed_repeatability", "G5_top_flat_change_p3",
        "G4_top_flat_settleRR_pressure", "G4_top_flat_settleRR_combined",
    ),
    "RE2": ("G1_top_flat", "G1_top_diag3", "G1_top_roll3", "G2_top_roll5.5",
            "G2_middle_roll5.5", "G2_bottom_roll5.5"),
    "RE1b": ("RE1b_top_flat_settleRR30",),
    "RE1c": ("RE1c_top_flat_retractRR25",),
}
"""Re-run sets of control spec rev. 3-5 (RE1 14, RE2 6, RE1b 1, RE1c 1; 20 distinct cases) and
rev. 7 42.2 (filled in after :func:`stage2_cases`): ``RE3`` = every stage-2 case (the 31 of the
matrix with the GE1′ record, RE1b, RE1c, RE1b-F, RE1b-P, the two G3 seed cases; the B1′ check
reads the nose-down cases of it), ``RE3new`` = the four new cases only."""
GE1_ATTRIBUTES = ("support_geometry",)
"""Controller attribute sampled every control period for the GE1 series (C2 R4.1 / R5,
python-expert); each sample is stored with the controller phase."""
GE1_CONTROLLER_ATTRIBUTES = ("is_geometry_valid", "stationary_gate")
"""R5 controller attributes merged into each GE1 sample when present (spec 42.1 GE1′-c)."""
GE1_R5_REQUIRED = {
    "is_geometry_valid": "stationary gate flag (spec 38, 42.1 GE1'-c)",
    "heights_delta_above_others_m": "d^Delta_i (spec 37.3)",
    "nonplanarity_m": "absolute r = [(I - P) h]_RR, sign fixed (spec 37.3)",
    "nonplanarity_delta_m": "Delta r = r(t) - r(t_ref) (spec 37.3)",
    "reference_t_s": "t_ref of the stored reference (spec 37.3)",
    "stationary_gate": "gate state attribute (spec 38, R5 StandstillGateState)",
}
"""R5 GE1′ sample names the export needs (C2 R5 final names, python-expert 2026-10-22;
``s6_ge1_export.R5_KEYS`` reads this table, ``run_S6.py check2`` checks them)."""
T_SETTLE_EXTRA, T_REJECT = 40.0, 5.0
T_TARGET = 95.0
"""G5 run length after CHECK: 95 s, run 97 s (control spec rev. 7 41.1, user decision U38-a
2026-10-22): first READY 37.02 + 2 + T3 limit 50 + 5b window 5 + 2 = 96.0 s <= 97 s."""
T_RE1BF_EXTRA = 65.0
"""RE1b-F / RE1b-P: after the event, re-READY <= 60 s (ASSUMPTION, as RE1b) + 5 s."""
RE1B_DROP_DEPTH_M, RE1B_DROP_RAMP_S = 0.030, 0.05
"""RE1b-F / -P: RR floor 30 mm in 0.05 s (cavity collapse, ASSUMPTION, spec 41.2)."""
RE1BP_DELAY_S = 0.1
RE1BP_TIMING = "probe_start"
"""``"probe_start"``: drop at the first PROBE start + 0.1 s (spec 41.2). ``"rr_turn"``: when
the first probe round reaches RR (fallback of 41.2 if PROBE does not stop the re-level)."""
RE1BP_RELEVEL_CHECK = (
    "C2 R5 (final, python-expert 2026-10-22): _needs_relevel applies the low-load trigger only "
    "in READY, so PROBE does not re-level on a load drop; the attitude trigger (completion "
    "deviation > relevel_attitude_rad 0.07 deg) still cuts PROBE. R5 order: the first PROBE "
    "comes before REANCHOR (H5a). Drop time kept at first PROBE + 0.1 s. Shown after the run: "
    "result.json probe_intervals (interrupted_by_relevel = PROBE -> LEVEL with no round "
    "completed) and s6_stage2_summary.probe_relevel_check."
)
FINE_HOLD_S = 2.0
FINE_PRE_S = 2.0
FINE_MAX_S = 30.0
"""Fine-dt window: from FINE_PRE_S before the drop, until drop + 2 s and the RR pad held
contact FINE_HOLD_S; cap FINE_MAX_S (then back to the base dt, flagged in the result)."""
CRAWLER_PART_S = 15.0
WALL_PADS_S_PER_S = 1.5
"""Wall seconds per simulated second on pads, 7 concurrent, chrono_point IMU, dt 2e-4 s: fit of
stage2_20261021_232845 (20 cases, 7 workers, P-cores: 363-462 us/step, 56 s -> 122 s, 123 s ->
223 s wall)."""
WALL_CRAWLER_S_PER_S = 3.0
WALL_START_S = 15.0
WALL_FINE_S_PER_S = 37.0
"""Wall seconds per simulated second at dt 1e-5 s: smoke 2026-10-22 (hold controller, pads, single
process) 186 us/step = 18.6 s/s, x2 for 7 concurrent workers (ASSUMPTION, as stage 2 2e-4 s)."""
FINE_EXPECTED_S = {"drop_RR_30": 10.0, "drop_RR_30_probe": 16.0}
"""Expected fine-dt window length (estimate: lift-off, re-level / guard, re-touch at 0.25 v_max
+ 2 s hold; RE1b-P waits for the RR probe turn and the Q2 re-ground)."""
CASE_TIMEOUT_S = 2400.0
"""Per case (run_cases timeout): RE1b-P with the FINE_MAX_S cap about 1300 s, x 1.8."""
SEED = 12345


@dataclass(frozen=True)
class Stage2Case:
    case_id: str
    group: str
    level: str
    floor: str
    contact: str = "combined"  # "pressure" | "combined"
    grade: str = "ideal"
    h4: bool = True
    check_time_s: float = CHECK_S
    acceptance: str = "reject"
    target_deg: tuple[float, float] = (0.0, 0.0)
    event: str | None = None  # "settle_RR" | "target_change" | "reject"
    pad_record: bool = True
    combined_verdict: bool | None = None
    """``ProbeSettings.use_combined_verdict``; None = the C2 default (on, control-expert rev. 1)."""
    duration_s: float = 0.0
    items: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)
    seed: int = SEED
    """Sensor-suite seed (spec rev. 7 41.3)."""
    pressure_grade: str = "normal"
    """WIKA A-10 pressure error grade (spec 71 E-1, U70; ``sensors.pressure_error``): normal /
    conservative / old_worst / legacy. Default = the judged condition 'normal + calibration'."""
    zero_calibration: bool = True
    """E-3 (U71): CHECK airborne round-trip zero calibration (C2 default on)."""
    head_offset_bar: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    """Deterministic extra head zero offset per leg (PS-4 / PS-7), bar."""
    head_drift_bar: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    """Linear head zero drift per leg over :data:`PS5_DRIFT_S` from the first READY (PS-5), bar."""
    pre_extend_leg: int | None = None
    """PS-7a-c (spec rev. 23 92): leg extended before the controller starts (LEG_ORDER index)."""
    snapshot_override: str | None = None
    """PS-7a: start snapshot other than the (level, floor) one (``S6_crawler_top_flat_RRpre``)."""
    pre_extend_offset_mm: float = 0.0
    """Target stroke = g0 of that leg (pad-to-floor gap at stroke 0, measured on the restored
    state) + this offset, mm; positive = pressed on the floor."""

    @property
    def settles(self) -> bool:
        """Ground-settlement scenario (RR patch moves; runs with L1-R like the other cases)."""
        return self.event in SETTLEMENT_EVENTS

    @property
    def snapshot(self) -> str:
        if self.snapshot_override:  # B2 PS-7a (RRpre)
            return self.snapshot_override
        return snapshot_name(self.level, self.floor)

    @property
    def fine_dt(self) -> bool:
        """Contact-transition dt window around the event (RE1b-F / RE1b-P)."""
        return self.event in FINE_EXPECTED_S

    def blocked_in(self, states_dir: Path) -> str | None:
        return None if (states_dir / f"{self.snapshot}.npz").exists() else "NO_SNAPSHOT"

    def wall_estimate_s(self) -> float:
        pads = max(self.duration_s - CRAWLER_PART_S, 0.0)
        fine = FINE_EXPECTED_S.get(self.event or "", 0.0)
        return (WALL_START_S + WALL_CRAWLER_S_PER_S * min(self.duration_s, CRAWLER_PART_S)
                + WALL_PADS_S_PER_S * (pads - fine) + WALL_FINE_S_PER_S * fine)


T_LEVEL_ROLL55 = 40.0
"""Levelling time on roll 5.5 deg: 29 s measured in batch stage2_20261021_213235 (the
reduced-model 18 s was too short; READY not reached in 53 s), with margin."""


CHECK_EXTRA_FALLBACK_S = 8.0
"""``check_max_s - check_time_s`` = 10 - 2 s when the C2 defaults cannot be read."""


def check_extra_s(case: Stage2Case) -> float:
    """Extra run length for the R5 B1′ CHECK extension (control spec rev. 8 44.6 / 45.2, user
    decision U40-U42 2026-10-22): ``check_max_s - check_time_s`` (8 s) on every case with a
    CHECK, so the last 5 s window (items 2 / 5b) is not cut (reduced plant: READY +9.5 s on the
    3.5 deg pitch floors). No extension without CHECK (G1, ``check_time_s`` 0)."""
    if case.check_time_s <= 0.0:
        return 0.0
    try:
        from outrigger_sim.control.c2 import TargetSettings

        check_max = float(TargetSettings().check_max_s)
    except Exception:  # noqa: BLE001 - plan without the controller package
        return CHECK_EXTRA_FALLBACK_S
    return max(check_max - case.check_time_s, 0.0)


def _length(floor: str, *, h4: bool, check_s: float, extra: float = 0.0) -> float:
    pitch = abs(FLOORS[floor][1])
    level = T_LEVEL_H4 if (h4 and pitch >= 2.5) else T_LEVEL
    if floor == "roll5.5":
        level = T_LEVEL_ROLL55
    return check_s + T_TOUCH + level + T_PROBE + T_READY + extra


def stage2_cases() -> list[Stage2Case]:
    out: list[Stage2Case] = []
    # G1 (item 1): top x {flat, diag 3, roll 3}, pressure only, ideal IMU, check 0
    for f in ("flat", "diag3", "roll3"):
        out.append(Stage2Case(
            f"G1_top_{f}", "G1", "top", f, contact="pressure", check_time_s=0.0,
            combined_verdict=False,
            notes=("reduced-model conditions: pressure-only judge, combined probe verdict off",
                   "check_time_s 0: no CHECK standstill, so no gyro bias removal"),
            acceptance="reject",  # K2: acceptance check on (utilisation 0.976 expected)
            duration_s=_length(f, h4=True, check_s=0.0), items=("1",)))
    # G2 / G2-R (items 2 3 4 5 7 8 (+R)): 3 levels x 4 floors, combined, ideal IMU
    for lv in LEVELS:
        for f in ("flat", "roll5.5", "fdown3.5", "fup3.5"):
            grp = "G2-R" if f in ("fdown3.5", "fup3.5") else "G2"
            items = ("2", "3", "4", "5", "7", "8") + (("R",) if grp == "G2-R" else ())
            out.append(Stage2Case(f"{grp}_{lv}_{f}", grp, lv, f,
                                  duration_s=_length(f, h4=True, check_s=CHECK_S), items=items))
    # G3 (item 2): grades at top flat (4) and top fdown3.5 (3)
    for g in ("good_zeroed", "normal_zeroed", "normal_zeroed_repeatability", "normal_as_shipped"):
        out.append(Stage2Case(f"G3_top_flat_{g}", "G3", "top", "flat", grade=g,
                              duration_s=_length("flat", h4=True, check_s=CHECK_S), items=("2",)))
    # K5: no roll 5.5 deg x non-ideal grade case (the + roll bias would push the utilisation
    # over the boundary); the fdown grades are accepted (x bias + reads less nose-down)
    pair_note = ("zero-offset paired comparison: normal_zeroed vs normal_zeroed_repeatability "
                 "share seed 12345 (same noise sequence), spec rev. 7 41.3",)
    for g in ("good_zeroed", "normal_zeroed", "normal_zeroed_repeatability"):
        out.append(Stage2Case(f"G3_top_fdown3.5_{g}", "G3", "top", "fdown3.5", grade=g,
                              duration_s=_length("fdown3.5", h4=True, check_s=CHECK_S),
                              items=("2", "B1"),
                              notes=pair_note if g.startswith("normal") else ()))
    # rev. 7 41.3: noise scatter of the normal grade (Q1 abstentions, B1' bias estimate)
    for seed in (12346, 12347):
        out.append(Stage2Case(f"G3_top_fdown3.5_normal_zeroed_s{seed}", "G3", "top", "fdown3.5",
                              grade="normal_zeroed", seed=seed,
                              duration_s=_length("fdown3.5", h4=True, check_s=CHECK_S),
                              items=("2", "B1"),
                              notes=(f"seed {seed}: noise-scatter repeat of "
                                     "G3_top_fdown3.5_normal_zeroed (spec rev. 7 41.3)",)))
    # G4 (item 6): top flat, RR settlement 11.5 mm at READY + 5 s, pressure / combined
    for c in ("pressure", "combined"):
        out.append(Stage2Case(f"G4_top_flat_settleRR_{c}", "G4", "top", "flat", contact=c,
                              event="settle_RR",
                              duration_s=_length("flat", h4=True, check_s=CHECK_S,
                                                 extra=T_SETTLE_EXTRA), items=("6",)))
    # G5 (item T): target pitch +3 deg, change 0 -> +3 at READY, start rejected
    out.append(Stage2Case("G5_top_flat_target_p3", "G5", "top", "flat", target_deg=(0.0, 3.0),
                          duration_s=CHECK_S + T_TARGET, items=("T",)))
    out.append(Stage2Case("G5_top_flat_change_p3", "G5", "top", "flat", event="target_change",
                          duration_s=CHECK_S + T_TARGET, items=("T",)))
    # RE1b / RE1c (control spec rev. 4 23, rev. 5 30): top flat, combined, after READY
    base_len = _length("flat", h4=True, check_s=CHECK_S)
    out.append(Stage2Case("RE1b_top_flat_settleRR30", "RE1b", "top", "flat", event="settle_RR_30",
                          duration_s=base_len + T_RE1B_EXTRA, items=("6", "7", "GE1"),
                          notes=("RR ground 30 mm, 5 s ramp at READY + 5 s: RR lift-off "
                                 "intended; re-READY <= 60 s (ASSUMPTION), all pads in contact "
                                 "and >= F_min + 5 kN at the end",)))
    out.append(Stage2Case("RE1c_top_flat_retractRR25", "RE1c", "top", "flat",
                          event="retract_RR_25", duration_s=base_len + T_RE1C_EXTRA,
                          items=("GE1",),
                          notes=("RR forced to retract 25 mm at 0.25 v_max from READY + 5 s, "
                                 "all other legs 0 (controller bypassed, still updated); GE1 "
                                 "check only, not a judged item",)))
    # RE1b-F / RE1b-P (control spec rev. 7 41.2): fast 30 mm drop, fine dt around the event
    for grade, suffix in (("ideal", ""), ("normal_zeroed", "_normal")):
        out.append(Stage2Case(
            f"RE1bF_top_flat_dropRR30{suffix}", "RE1b", "top", "flat", grade=grade,
            event="drop_RR_30", duration_s=base_len + T_RE1BF_EXTRA,
            items=("6", "7", "GE1"),
            notes=("RR ground 30 mm in 0.05 s at READY + 5 s (cavity collapse, ASSUMPTION): RR "
                   "lifts off at once; expect low-load re-level / guard -> re-approach 0.25 v_max "
                   "-> re-touch -> probe -> READY; GE1' RR d^Delta < -5 mm, no false flag on "
                   "the other legs; transition dt 1e-5 s",)
            + (("normal IMU grade: does the noise-corrected stationary gate (spec 38) close "
                "late? (control-expert request, U38 scope)",) if suffix else ())))
    out.append(Stage2Case(
        "RE1bP_top_flat_dropRR30_probe", "RE1b", "top", "flat", event="drop_RR_30_probe",
        duration_s=base_len + T_RE1BF_EXTRA, items=("6", "7", "GE1", "Q2"),
        notes=("RR ground 30 mm in 0.05 s at the first PROBE start + 0.1 s: RR lifted during "
               "its own probe turn -> Q2 re-ground path; check that PROBE does not re-level "
               f"({RE1BP_RELEVEL_CHECK})",)))
    out.append(Stage2Case("G5_top_flat_reject", "G5", "top", "flat", target_deg=(4.0, 3.0),
                          event="reject", duration_s=CHECK_S + T_REJECT, items=("T",),
                          notes=("target (roll 4, pitch 3) deg outside the diamond: expect a "
                                 "reject code and legs stopped",)))
    # G6 (R, 1): top fdown / fup 3.5 x H4 on / off, pressure only
    for f in ("fdown3.5", "fup3.5"):
        for h4 in (True, False):
            out.append(Stage2Case(f"G6_top_{f}_H4{'on' if h4 else 'off'}", "G6", "top", f,
                                  contact="pressure", h4=h4,
                                  duration_s=_length(f, h4=h4, check_s=CHECK_S),
                                  items=("R", "1")))
    return [replace(c, duration_s=c.duration_s + check_extra_s(c)) for c in out]


PS5_DRIFT_S = 600.0
"""PS-5: the head zero drift reaches ``head_drift_bar`` after this time (spec 76.3)."""
PS5_DRIFT_START_AFTER_CHECK_S = 2.0
"""PS-5 drift start after the longest CHECK (calibration done), ASSUMPTION."""
PS5_READY_EXTRA_S = 660.0
"""PS-5: READY kept until the drift has run its 600 s (+ 60 s)."""
PS_SEEDS = (12346, 12347)
"""PS-1 extra seeds; seed 12345 of the normal + calibration condition is the matrix case
itself (G2 / G4 / RE1b-F run with the same default sensors)."""


def ps_cases() -> list[Stage2Case]:
    """Pressure-sensor cases PS-1 ... PS-7 (control spec rev. 14 76.3, U70-U73).

    Base scenarios (76.3 '같은 사례'): top flat, top nose-down 3.5 deg, G4 combined (RR settles
    11.5 mm), RE1b-F (RR drops 30 mm). The settlement scenarios run with the bundle's L1-R
    setting like the others. PS-7's 'RR on the ground during CHECK'
    needs a start state that does not exist (not prepared, see the bundle report)."""
    base_len = _length("flat", h4=True, check_s=CHECK_S)
    scen = {
        "flat": dict(floor="flat", duration_s=base_len),
        "fdown3.5": dict(floor="fdown3.5", duration_s=_length("fdown3.5", h4=True, check_s=CHECK_S)),
        "G4": dict(floor="flat", contact="combined", event="settle_RR",
                   duration_s=_length("flat", h4=True, check_s=CHECK_S, extra=T_SETTLE_EXTRA)),
        "RE1bF": dict(floor="flat", event="drop_RR_30", duration_s=base_len + T_RE1BF_EXTRA),
    }
    out: list[Stage2Case] = []

    def add(cid, sc, note, **kw):
        out.append(Stage2Case(cid, "PS", "top", items=("PS",), notes=(note,),
                              **{**scen[sc], **kw}))

    for seed in PS_SEEDS:
        for sc in scen:
            add(f"PS1_{sc}_normal_cal_s{seed}", sc, "PS-1 normal + calibration (judged condition), "
                f"seed {seed}", seed=seed)
    for grade in ("conservative", "old_worst"):
        for sc in scen:
            add(f"PS2_{sc}_{grade}_nocal", sc, f"PS-2 {grade}, calibration off (record)",
                pressure_grade=grade, zero_calibration=False)
    for sc in scen:
        add(f"PS3_{sc}_old_worst_cal", sc, "PS-3 old_worst + calibration",
            pressure_grade="old_worst")
    for sc in ("G4", "RE1bF"):
        for cal in (False, True):
            add(f"PS4_{sc}_FLp4_RRm4_{'cal' if cal else 'nocal'}", sc,
                "PS-4 deterministic worst sign: FL head +4 bar, RR head -4 bar",
                head_offset_bar=(4.0, 0.0, 0.0, -4.0), zero_calibration=cal)
    out.append(Stage2Case(
        "PS5_flat_drift_FLp2_600s", "PS", "top", "flat", items=("PS",),
        head_drift_bar=(2.0, 0.0, 0.0, 0.0),
        duration_s=base_len + PS5_READY_EXTRA_S,
        notes=("PS-5 zero drift after the calibration: FL head +2 bar linear over 600 s "
               "(about 25 K), long READY; U73 drift warning time and minimum true force",)))
    for sign, path in ((+10.0, "grounded skip (spec 76.4 1')"), (-10.0, "implausible (76.4 1)")):
        add(f"PS7_flat_FL{'p' if sign > 0 else 'm'}10_cal", "flat",
            f"PS-7 calibration failure, FL head {sign:+.0f} bar: {path} -> that leg only gets "
            "the allowance", head_offset_bar=(sign, 0.0, 0.0, 0.0))
    return [replace(c, duration_s=c.duration_s + check_extra_s(c)) for c in out]


RUN_PLACEMENT_ENV = "OUTRIGGER_RUN_PLACEMENT"


def run_placement() -> str | None:
    """``runner.run_closed_loop(placement=...)``: its default ``"pcore"`` re-pins a process that
    a smoke run placed on the E-cores; ``OUTRIGGER_RUN_PLACEMENT`` = ``ecore`` / ``os`` / ``none``
    overrides it (default ``pcore``, unchanged behaviour in the batches)."""
    import os

    value = os.environ.get(RUN_PLACEMENT_ENV, "pcore").strip().lower()
    return None if value in ("none", "") else value


RRPRE_SNAPSHOT = "S6_crawler_top_flat_RRpre"
"""PS-7a start (control spec rev. 23 92.1): S6_crawler_top_flat (L1-R) + RR extended to
g0 + 2 mm (347.72 mm) and settled >= RRPRE_SETTLE_MIN_S and until the gyro motion RMS of the
B1' window is below its limit (built by :func:`job_snapshot_rrpre`)."""
RRPRE_OFFSET_MM = 2.0
RRPRE_SETTLE_MIN_S = 20.0
RRPRE_SETTLE_MAX_S = 120.0
RRPRE_QUIET_FRACTION = 0.5
"""Stop when the window RMS is below this fraction of the B1' limit (margin for the CHECK round
trip, ASSUMPTION; the first build stopped at 0.99 of the limit)."""

PS7_PRE_EXTEND_MM = {"a": +2.0, "b": -1.5, "c": -2.7}
"""PS-7a / b / c (spec rev. 23 92): RR stroke = g0 + this before CHECK (7d / 7e = the bundle-B
cases PS7_flat_FLp10_cal / PS7_flat_FLm10_cal: same conditions, not repeated)."""
PS7_GROUNDED_READING_N = 4707.3
"""F_min / 2 (9414.59 N / 2): 7a needs a CHECK-start RR reading at or above this (else +1 mm)."""
PS7_PRE_SETTLE_S = 1.0
"""Hold after the pre-extension before the controller starts (ASSUMPTION)."""
PS7_MAX_EXTRA_MM = 5.0
"""7a: at most this many +1 mm increments."""


def ps7_cases() -> list[Stage2Case]:
    """PS-7a-c (bundle B2): top flat, L1-R on, R7 default, normal grade, calibration on,
    seed 12345, target 0; RR pre-extended to g0 + offset before the controller starts."""
    base = _length("flat", h4=True, check_s=CHECK_S)
    pre_s = 0.36 / 0.020924 + PS7_PRE_SETTLE_S + 2.0  # about g0 / v_max + hold + margin
    out = []
    for key, off in PS7_PRE_EXTEND_MM.items():
        # 7a (control spec 92.1): start from the settled RRpre snapshot (no pre-extension in the
        # run, so the crawler rocking of the pre-load has decayed before CHECK); 7b / 7c keep the
        # in-run pre-extension (a bias skip is allowed there and only recorded)
        settled = key == "a"
        out.append(Stage2Case(
            f"PS7{key}_flat_RRpre_{'p' if off >= 0.0 else 'm'}{abs(off):.1f}mm", "PS", "top", "flat", items=("PS",),
            pre_extend_leg=None if settled else 3, pre_extend_offset_mm=off,
            snapshot_override=RRPRE_SNAPSHOT if settled else None,
            duration_s=base + (0.0 if settled else pre_s),
            notes=(f"PS-7{key} (spec rev. 23 92): RR at g0 {off:+.1f} mm before CHECK; expected "
                   + {"a": "WARN_PRESSURE_ZERO_SKIPPED:RR:grounded once, RR c = 0, allowance 4.0 kN",
                      "b": "implausible / unsteady / move -> allowance path",
                      "c": "mostly calibrated, bias >= -0.6 kN"}[key],)))
    return [replace(c, duration_s=c.duration_s + check_extra_s(c)) for c in out]


def all_cases() -> list[Stage2Case]:
    """The stage-2 matrix and RE sets (:func:`stage2_cases`) plus the PS cases (B2: PS-7a-c)."""
    return stage2_cases() + ps_cases() + ps7_cases()


def pad_gaps_m(model):
    """Pad-to-floor gap of each leg along the floor normal (L1 contact sphere):
    ``n . (c - p0) - r``; the PS-7 g0 at stroke 0. C-S8-76: a leg on a block
    (``L1Model(pad_blocks=...)``) is measured against the block top (``- h``)."""
    import numpy as np

    probe = model.probe()
    n = np.asarray(probe.floor_normal_world, float)
    c = np.asarray(probe.pad_sphere_centre_world_m, float)
    r = np.asarray(probe.pad_sphere_radius_m, float)
    gaps = (c - np.asarray(model.floor_point_world_m, float)) @ n - r
    if getattr(model, "pad_blocks", None) is not None:
        gaps = gaps - model.pad_block_offsets_m()
    return gaps


def _find_key(tree, key):
    """First value of ``key`` anywhere in a nested dict / list (meta lookup)."""
    if isinstance(tree, dict):
        if key in tree:
            return tree[key]
        for v in tree.values():
            found = _find_key(v, key)
            if found is not None:
                return found
    elif isinstance(tree, list):
        for v in tree:
            found = _find_key(v, key)
            if found is not None:
                return found
    return None


def b1_motion_limit(params) -> dict[str, Any]:
    """B1' window ``T_b`` and motion limit ``omega_th(T_b)`` of the default C2 (the controller's
    own values, read from a fresh controller's meta)."""
    from outrigger_sim.control.c2 import C2Config, C2Controller

    meta = C2Controller.from_params(params, C2Config()).meta()
    gb = _find_key(meta, "gyro_bias") or {}
    return {"window_s": gb.get("window_s"), "motion_limit_rad_s": gb.get("motion_limit_rad_s"),
            "settings": gb.get("settings")}


def gyro_check_record(arr, t0, window_s, limit, start_s, end_s, events) -> dict[str, Any]:
    """Rolling B1'-type motion RMS (RMS about the window mean, per axis, roll / pitch) of the
    recorded IMU rate ``meas.angular_rate`` over ``window_s``, from ``start_s`` to ``end_s``
    (relative to ``t0``), every 20 ms; noise correction omitted (ideal IMU grade). The record is
    the 1 ms truth-time series of the sensor outputs, not the controller's 20 ms averages, so
    this is the cause check, not the controller's value (that is ``controller_gyro_bias``)."""
    import numpy as np

    if "meas.angular_rate" not in arr:
        return {"note": "no meas.angular_rate in the record"}
    t = np.asarray(arr["t"]) - t0
    w = np.asarray(arr["meas.angular_rate"])[:, :2]
    ends = np.arange(start_s + window_s, end_s + 1e-9, 0.02)
    rms = []
    for te in ends:
        m = (t >= te - window_s) & (t <= te)
        if m.sum() < 3:
            rms.append([np.nan, np.nan])
            continue
        x = w[m]
        rms.append(np.sqrt(((x - x.mean(axis=0)) ** 2).mean(axis=0)).tolist())
    rms = np.asarray(rms)
    worst = np.nanmax(rms, axis=1) if len(rms) else np.array([])
    first_quiet = None
    if limit is not None and len(worst):
        q = np.flatnonzero(worst <= limit)
        first_quiet = None if not q.size else float(ends[q[0]])
    return {"window_s": window_s, "motion_limit_rad_s": limit, "start_s": start_s, "end_s": end_s,
            "rms_max_axis_rad_s": {"min": float(np.nanmin(worst)) if len(worst) else None,
                                   "at_end": float(worst[-1]) if len(worst) else None,
                                   "max": float(np.nanmax(worst)) if len(worst) else None},
            "first_quiet_window_end_s": first_quiet,
            "series_t_s": ends[::10].tolist(), "series_rms_rad_s": rms[::10].tolist(),
            "gyro_events": [e for e in events if "GYRO" in e]}


def gyro_check_for(arr, phases, t0, ctl_meta, events, params, start_s) -> dict[str, Any]:
    """PS-7 cause record (control spec 92.1): the controller's B1' result plus the rolling
    motion RMS of the recorded rate over the CHECK phase (from the hand-over when pre-extended)."""
    gb = _find_key(ctl_meta, "gyro_bias") or {}
    window = gb.get("window_s")
    limit = gb.get("motion_limit_rad_s")
    win = None
    for (t1, p), nxt in zip(phases, [*phases[1:], (None, "end")], strict=True):
        if p == "check":
            win = (t1 if start_s is None else max(t1, start_s), nxt[0])
            break
    out = {"controller_gyro_bias": gb, "check_window_s": win}
    if win is None or window is None:
        return out
    end = win[1] if win[1] is not None else win[0] + 20.0
    out["record"] = gyro_check_record(arr, t0, float(window), limit, float(win[0]), float(end), events)
    return out


PREGROUND_LEGS = ("FL", "FR", "RL", "RR")


def preground_snapshot_name(leg: str) -> str:
    """PS-7a start snapshot of a pre-grounded ``leg`` (C-S8-72, spec rev. 67 345.3):
    ``S6_crawler_top_flat_<leg>pre``; RR = :data:`RRPRE_SNAPSHOT` (unchanged name)."""
    if leg not in PREGROUND_LEGS:
        raise ValueError(f"leg {leg!r} not in {PREGROUND_LEGS}")
    return f"{snapshot_name('top', 'flat')}_{leg}pre"


def job_snapshot_rrpre(case_dir: Path, states_dir: Path) -> dict[str, Any]:
    """PS-7a start snapshot :data:`RRPRE_SNAPSHOT` (control spec rev. 23 92.1):
    :func:`job_snapshot_preground` with RR."""
    return job_snapshot_preground(case_dir, states_dir, leg="RR")


def job_snapshot_preground(case_dir: Path, states_dir: Path, *, leg: str = "RR",
                           overwrite: bool = True) -> dict[str, Any]:
    """PS-7a start snapshot :func:`preground_snapshot_name` (control spec rev. 23 92.1; leg
    general since C-S8-72, spec rev. 67 345.3): restore the L1-R S6_crawler_top_flat, extend
    ``leg`` at v_max to g0 + :data:`RRPRE_OFFSET_MM`, hold every leg, and stop once >=
    :data:`RRPRE_SETTLE_MIN_S` after reaching the target and the B1' motion RMS (true body rate,
    window T_b) is below the limit (at most :data:`RRPRE_SETTLE_MAX_S`). RR is the former
    procedure step for step (same names, numbers and stop rule)."""
    import numpy as np

    from outrigger_sim.params import load_params
    from outrigger_sim.record import load_snapshot, save_snapshot

    j = PREGROUND_LEGS.index(leg)
    name = preground_snapshot_name(leg)
    if not overwrite and (states_dir / f"{name}.npz").exists():
        raise FileExistsError(f"{name} exists in {states_dir} (overwrite=False)")
    params = load_params(level="top")
    model, _ = build_crawler_model(params, "flat", attach=False)
    base = snapshot_name("top", "flat")
    t0 = model.restore(load_snapshot(base, params_sha256=params.sha256, directory=states_dir))
    gaps = pad_gaps_m(model)
    target = float(gaps[j]) + RRPRE_OFFSET_MM * 1e-3
    lim = b1_motion_limit(params)
    window, limit = float(lim["window_s"]), float(lim["motion_limit_rad_s"])
    v = float(params.actuator.max_speed_m_s)
    act = model.actuator
    dt = model.dt_s
    t_reach = None
    rows = {"t": [], "omega": [], "s": []}
    wall0 = time.perf_counter()
    k = 0
    reason = "max time"
    while True:
        s = float(model.motors[j].GetMotorPos())
        u = np.zeros(4)
        if t_reach is None and s < target:
            u[j] = v
        elif t_reach is None:
            t_reach = float(model.system.GetChTime())
        model.set_command(u)
        r = model.step(capture=(k % 20 == 19))
        k += 1
        if r.probe is not None:
            rows["t"].append(r.probe.t_s)
            rows["omega"].append(np.asarray(r.probe.body_omega_rad_s, float))
            rows["s"].append(np.asarray(r.probe.motor_pos_m, float))
        t = float(model.system.GetChTime())
        if t_reach is not None and t - t_reach >= RRPRE_SETTLE_MIN_S and k % 100 == 0:
            tt = np.asarray(rows["t"])
            om = np.asarray(rows["omega"])
            m = tt >= t - window
            # body rate in body axes ~ IMU roll / pitch rate for small tilt (ASSUMPTION)
            x = om[m][:, :2]
            rms = float(np.sqrt(((x - x.mean(axis=0)) ** 2).mean(axis=0)).max())
            if rms <= RRPRE_QUIET_FRACTION * limit:
                reason = f"quiet: rms {rms:.3e} <= {RRPRE_QUIET_FRACTION} x {limit:.3e} rad/s"
                break
        if t - t0 > RRPRE_SETTLE_MAX_S + 30.0:
            break
    wall = time.perf_counter() - wall0
    model.set_command(np.zeros(4))
    note = {"stage": "S6 PS-7a start (spec rev. 23 92.1)", "base": base,
            f"{leg}_target_m": target, "g0_m": gaps.tolist(), "t_reach_s": t_reach,
            "stop": reason, "b1_window_s": window, "b1_limit_rad_s": limit}
    if leg != "RR":  # C-S8-72 (spec rev. 67 345.3)
        note.update(stage="S6 PS-7a start, leg general (spec rev. 67 345.3 C-S8-72)", leg=leg)
    save_snapshot(model.snapshot(), name, directory=states_dir, overwrite=True, note=note)
    arr = {k2: np.asarray(v2) for k2, v2 in rows.items()}
    np.savez_compressed(case_dir / "series.npz", **arr)
    contact = np.asarray(model.truth(model.probe()).F_contact_n_N)
    return {"snapshot": name, "leg": leg, "base": base, "g0_m": gaps.tolist(),
            f"{leg}_target_m": target,
            "t_reach_s": None if t_reach is None else t_reach - t0, "t_end_s": float(model.system.GetChTime()) - t0,
            "stop": reason, "b1": lim, "final_stroke_m": arr["s"][-1].tolist(),
            f"final_{leg}_contact_N": float(contact[j]),
            "final_contact_N": contact.tolist(), "wall_s": wall}


def zero_calibration_report(arr, phases, t0, ctl_meta, events, params, *,
                            start_s: float | None = None) -> dict[str, Any]:
    """PS-7 record (spec rev. 23 92): zero-calibration events, per-leg status / c_i / allowance
    from the controller meta, and c_true = mean over CHECK of (measured net force - true
    cylinder force) per leg (the truth identity p_h A_p - p_r A_ann = F_cyl), N."""
    import numpy as np

    from outrigger_sim.sensors.hydraulic import (
        leg_annulus_areas_from_params,
        leg_head_areas_from_params,
    )

    zc_events = [e for e in events if "PRESSURE_ZERO" in e]
    zc_meta = {k: v for k, v in ctl_meta.items() if "zero" in k.lower()}
    out: dict[str, Any] = {"events": zc_events, "controller_meta": zc_meta}
    win = None
    for (t1, p), nxt in zip(phases, [*phases[1:], (None, "end")], strict=True):
        if p == "check":
            # PS-7a-c: the controller only starts at the pre-extension hand-over
            win = (t1 if start_s is None else max(t1, start_s), nxt[0])
            break
    if win is None or "meas.head_pressure" not in arr:
        out["c_true_N"] = None
        out["c_true_note"] = "no CHECK window or no measured pressures in the record"
        return out
    t = np.asarray(arr["t"]) - t0
    mask = (t >= win[0]) & (t <= (win[1] if win[1] is not None else t[-1]))
    a_p = leg_head_areas_from_params(params)
    a_ann = leg_annulus_areas_from_params(params)
    head = np.asarray(arr["meas.head_pressure"])[mask]
    rod = np.asarray(arr["meas.rod_pressure"])[mask] if "meas.rod_pressure" in arr else 0.0 * head
    true_f = np.asarray(arr["F_cyl"])[mask] if "F_cyl" in arr else None
    if true_f is None:
        out["c_true_N"] = None
        out["c_true_note"] = "record has no F_cyl"
        return out
    meas = head * a_p - rod * a_ann
    out["c_true_N"] = (meas - true_f).mean(axis=0).tolist()
    out["c_true_window_s"] = list(win)
    out["c_true_note"] = ("mean over the CHECK phase (pads airborne except a pre-extended leg) of "
                          "measured net force minus true cylinder force; includes noise")
    return out


class PreExtend:
    """Controller wrapper of PS-7a-c: before the inner controller starts, ``leg`` extends at
    ``speed`` to ``target_m`` (measured stroke), holds :data:`PS7_PRE_SETTLE_S`, then (7a) checks
    the leg's net-force reading against :data:`PS7_GROUNDED_READING_N` and adds +1 mm while it is
    below (at most :data:`PS7_MAX_EXTRA_MM`); then hands over. The inner controller is not
    updated before the hand-over, so its CHECK starts with the leg already in place."""

    def __init__(self, inner, *, leg, target_m, speed_m_s, head_area_m2, annulus_area_m2,
                 grounded_check: bool) -> None:
        self.inner = inner
        self.leg = leg
        self.target_m = float(target_m)
        self.target0_m = float(target_m)
        self.speed_m_s = speed_m_s
        self.a_p = head_area_m2
        self.a_ann = annulus_area_m2
        self.grounded_check = grounded_check
        self.hold_since = None
        self.handover_t = None
        self.extra_mm = 0.0
        self.readings: list[dict[str, Any]] = []

    @property
    def period_s(self) -> float:
        return self.inner.period_s

    def reset(self) -> None:
        self.inner.reset()

    def _net_reading_N(self, m) -> float:
        rod = 0.0 if m.rod_pressure_Pa is None else float(m.rod_pressure_Pa[self.leg])
        return float(m.head_pressure_Pa[self.leg]) * self.a_p[self.leg] - rod * self.a_ann[self.leg]

    def update(self, measurements):
        import numpy as np

        from outrigger_sim.signals import Command

        if self.handover_t is not None:
            return self.inner.update(measurements)
        t = measurements.t_s
        s = float(measurements.stroke_m[self.leg])
        u = np.zeros(4)
        if s < self.target_m:
            u[self.leg] = self.speed_m_s
            self.hold_since = None
        elif self.hold_since is None:
            self.hold_since = t
        elif t - self.hold_since >= PS7_PRE_SETTLE_S - 1e-9:
            reading = self._net_reading_N(measurements)
            self.readings.append({"t_s": t, "stroke_m": s, "net_reading_N": reading,
                                  "extra_mm": self.extra_mm})
            if (self.grounded_check and reading < PS7_GROUNDED_READING_N
                    and self.extra_mm < PS7_MAX_EXTRA_MM):
                self.extra_mm += 1.0
                self.target_m = self.target0_m + self.extra_mm * 1e-3
                self.hold_since = None
            else:
                self.handover_t = t
                return self.inner.update(measurements)
        return Command(t_s=t, leg_speed_m_s=u)

    def meta(self) -> dict[str, Any]:
        return {"wrapper": "PreExtend", "leg": self.leg, "target0_m": self.target0_m,
                "target_m": self.target_m, "extra_mm": self.extra_mm,
                "handover_t_s": self.handover_t, "readings": self.readings,
                "inner": self.inner.meta()}


RERUN_SETS["RE3"] = tuple(c.case_id for c in stage2_cases())
RERUN_SETS["RE3new"] = (
    "RE1bF_top_flat_dropRR30", "RE1bF_top_flat_dropRR30_normal", "RE1bP_top_flat_dropRR30_probe",
    "G3_top_fdown3.5_normal_zeroed_s12346", "G3_top_fdown3.5_normal_zeroed_s12347",
)
RERUN_SETS["B1"] = tuple(c.case_id for c in stage2_cases()
                         if c.level == "top" and c.floor == "fdown3.5"
                         and c.group in ("G2-R", "G3"))
"""B1′ check (spec 35, 39, 41.3): top nose-down 3.5 deg, ideal / good / normal x 3 seeds."""


def ge1_r5_preflight() -> dict[str, Any]:
    """Check that the installed C2 exposes the R5 GE1′ names (:data:`GE1_R5_REQUIRED`).

    Looks at the ``SupportGeometry`` sample fields (dataclass) and the controller attributes.
    Returns ``{"ok", "revision", "missing", "found"}``; no physics.
    """
    from dataclasses import fields, is_dataclass

    from outrigger_sim.control import c2

    names: set[str] = set()
    sample = getattr(c2, "SupportGeometry", None)
    if sample is not None and is_dataclass(sample):
        names |= {f.name for f in fields(sample)}
    ctrl = getattr(c2, "C2Controller", None)
    if ctrl is not None:
        names |= {n for n in dir(ctrl) if not n.startswith("__")}
    missing = {k: v for k, v in GE1_R5_REQUIRED.items() if k not in names}
    return {"ok": not missing, "revision": getattr(c2, "C2_REVISION", None),
            "missing": missing, "found": sorted(k for k in GE1_R5_REQUIRED if k in names)}


SETTLEMENT_EVENTS = ("settle_RR", "settle_RR_30", "drop_RR_30", "drop_RR_30_probe")
OFF_SNAPSHOTS: tuple[tuple[str, str], ...] = ()
"""Bundle B: snapshots built with L1-R off for settlement cases. Empty since L1-R supports
settlement legs (``chrono/rod_chamber_link``, 2026-10-22): the settlement cases start from the
L1-R snapshots like the others. The earlier twin was ``(("top", "flat"),)``."""


def snapshot_name(level: str, floor: str, *, off: bool = False) -> str:
    """Settled crawler snapshot of stage 2 (crawler anchor bushings on, Q12); ``off`` = the
    L1-R-off twin of an L1-R bundle (settlement cases)."""
    return f"S6_crawler_{level}_{floor}" + ("_L1Roff" if off else "")


def lpt_makespan_s(walls: list[float], workers: int = 7) -> float:
    """Longest-processing-time-first schedule length of ``walls`` on ``workers`` (estimate)."""
    load = [0.0] * workers
    for w in sorted(walls, reverse=True):
        i = load.index(min(load))
        load[i] += w
    return max(load) if walls else 0.0


def plan_document(states_dir: Path, ids: set[str] | None = None) -> dict[str, Any]:
    cases = [c for c in all_cases() if ids is None or c.case_id in ids]
    c2_meta = default_c2_meta()
    rows = []
    for c in cases:
        rows.append({**asdict(c), "snapshot": c.snapshot, "blocked": c.blocked_in(states_dir),
                     "wall_estimate_s": c.wall_estimate_s(),
                     "reanchor_expected": expected_reanchor(c, c2_meta.get("reanchor_direction"))})
    snaps = []
    for lv, f in SNAPSHOTS:
        name = snapshot_name(lv, f)
        exists = (states_dir / f"{name}.npz").exists()
        snaps.append({"level": lv, "floor": f, "floor_slope_deg": FLOORS[f], "snapshot": name,
                      "exists": exists,
                      "wall_estimate_s": WALL_START_S + (SNAP_RAMP_S + SNAP_SETTLE_S) * WALL_CRAWLER_S_PER_S})
    walls = [r["wall_estimate_s"] for r in rows]
    serial = sum(walls)
    missing = sum(s["wall_estimate_s"] for s in snaps if not s["exists"])
    return {
        "cases": rows, "snapshots": snaps, "prerequisites": PREREQUISITES,
        "counts": {"cases": len(rows), "unblocked": sum(r["blocked"] is None for r in rows),
                   "snapshots": len(snaps), "snapshots_missing": sum(not s["exists"] for s in snaps)},
        "wall_estimate": {"serial_s": serial, "parallel_7_s": serial / 7.0,
                          "lpt_7_workers_s": lpt_makespan_s(walls, 7),
                          "missing_snapshots_serial_s": missing,
                          "longest_case_s": max(walls) if walls else 0.0,
                          "basis": f"{WALL_PADS_S_PER_S} s/s on pads, {WALL_CRAWLER_S_PER_S} s/s on "
                                   f"crawler, {WALL_START_S} s start (estimates)"},
        "runner": {"command_delay_periods": 1, "imu_method": "chrono_point",
                   "pad_record_every_steps": 5, "timeout_s": CASE_TIMEOUT_S, "jobs": 7,
                   "seed": SEED},
        "c2": c2_meta,
        "nose_up_h4_cases": [r["case_id"] for r in rows
                             if r["reanchor_expected"]["expected"] == "reanchor_skipped:nose_up"],
    }


def default_c2_meta() -> dict[str, Any]:
    """:func:`c2_config_meta` of the default ``C2Config`` (what stage 2 runs, spec 86.6); empty
    dict when the controller package cannot be imported (plan without it)."""
    try:
        from outrigger_sim.control.c2 import C2Config
    except Exception:  # noqa: BLE001
        return {}
    return c2_config_meta(C2Config())


# --- settled crawler snapshots (Q12 anchor bushings) ---------------------------------------


def build_crawler_model(params, floor: str, *, attach: bool, settlement_legs=(),
                        tangential: bool = False, **kw):
    """Actuated L1 model on the crawler (legs retracted) on the floor of ``floor``, crawler
    anchor bushings on; ``attach`` = create them now on the analytically loaded spheres."""
    import numpy as np

    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.chrono.model import L1Model
    from outrigger_sim.scenarios.crawler_slope import crawler_slope_pose

    import l1r_variant

    roll, pitch = FLOORS[floor]
    pose = crawler_slope_pose(params, roll, pitch, tangential=tangential)
    kw.setdefault("rod_side_mechanics", l1r_variant.mechanics_for(settlement=bool(settlement_legs)))
    model = L1Model(
        params, pose=BodyPose(pose.origin_m, pose.quat_wxyz), extensions_m=(0.0, 0.0, 0.0, 0.0),
        attach_bushings=False, actuator=True,
        floor_pose=BodyPose(pose.floor_pos_m, pose.floor_quat_wxyz),
        crawler_bushings=True,
        attach_crawler_bushings=[int(i) for i in np.flatnonzero(pose.active)] if attach else False,
        settlement_legs=settlement_legs, **kw,
    )
    return model, pose


def job_snapshot(level: str, floor: str, case_dir: Path, states_dir: Path, *,
                 off: bool = False) -> dict[str, Any]:
    """Settle on the crawler (in-plane gravity ramp + settle) and save the snapshot; ``off``
    builds the L1-R-off twin (:func:`snapshot_name`)."""
    import numpy as np

    from outrigger_sim.chrono.system import set_gravity
    from outrigger_sim.frames import roll_pitch_from_quat
    from outrigger_sim.params import load_params
    from outrigger_sim.record import save_snapshot
    from outrigger_sim.scenarios.slope import floor_normal, floor_rotation, gravity_ramp

    params = load_params(level=level)
    extra = {"rod_side_mechanics": "off"} if off else {}
    (model, start) = build_crawler_model(params, floor, attach=True, **extra)
    from outrigger_sim.scenarios.crawler_slope import crawler_slope_pose

    pose = crawler_slope_pose(params, *FLOORS[floor], tangential=True)  # settled end state
    rf = floor_rotation(floor_normal(*FLOORS[floor]))
    g_floor = rf.T @ np.array([0.0, 0.0, -params.meta.gravity_m_s2])

    def gvec(t):
        k = gravity_ramp(t, SNAP_RAMP_S)
        return rf @ np.array([k * g_floor[0], k * g_floor[1], g_floor[2]])

    cb = model.crawler_bushing
    dt = model.dt_s
    n_ramp = round(SNAP_RAMP_S / dt)
    n_total = n_ramp + round(SNAP_SETTLE_S / dt)
    n_last10 = n_total - round(10.0 / dt)
    rows = {"t": [], "roll_pitch_deg": [], "vel": [], "omega": []}
    yield_ramp = yield_last10 = None
    wall0 = time.perf_counter()
    set_gravity(model.system, tuple(gvec(0.0)))
    for k in range(n_total):
        if k <= n_ramp:
            set_gravity(model.system, tuple(gvec(float(model.system.GetChTime()))))
        r = model.step(capture=(k % 50 == 49))
        if k + 1 == n_ramp:
            yield_ramp = cb.yield_steps.copy()
        if k + 1 == n_last10:
            yield_last10 = cb.yield_steps.copy()
        if r.probe is not None:
            rows["t"].append(r.probe.t_s)
            rows["roll_pitch_deg"].append(np.degrees(roll_pitch_from_quat(r.probe.body_quat_wxyz)))
            rows["vel"].append(r.probe.body_vel_m_s)
            rows["omega"].append(r.probe.body_omega_rad_s)
    wall = time.perf_counter() - wall0
    cb.assert_hold_released(f"snapshot {level}/{floor}")
    arr = {k: np.asarray(v) for k, v in rows.items()}
    np.savez_compressed(case_dir / "series.npz", **arr)
    name = snapshot_name(level, floor, off=off)
    save_snapshot(model.snapshot(), name, directory=states_dir, overwrite=True,
                  note={"stage": "S6 stage 2 start", "level": level, "floor": floor,
                        "floor_slope_deg": FLOORS[floor],
                        "procedure": f"analytic crawler_slope_pose, crawler anchor bushings "
                        f"(Q12) at zero deformation, in-plane gravity ramp {SNAP_RAMP_S} s, "
                        f"settle {SNAP_SETTLE_S} s",
                        "crawler_bushing": model.crawler_bushing_values.meta()})
    normals = np.asarray(model.crawler_normals())
    last = arr["t"] >= arr["t"][-1] - 5.0
    return {
        "level": level, "floor": floor, "snapshot": name, "floor_slope_deg": FLOORS[floor],
        "start_pose_normal_only": {"body_roll_pitch_deg": [start.body_roll_deg,
                                                         start.body_pitch_deg],
                                   "loaded_spheres": [int(i) for i in np.flatnonzero(start.active)]},
        "analytic": {"body_roll_pitch_deg": [pose.body_roll_deg, pose.body_pitch_deg],
                     "rel_roll_pitch_deg": [pose.rel_roll_deg, pose.rel_pitch_deg],
                     "sphere_force_N": pose.sphere_force_N,
                     "tangential_per_active_N": pose.tangential_per_active_N,
                     "residual": pose.residual},
        "chrono_end": {"body_roll_pitch_deg": arr["roll_pitch_deg"][-1],
                       "sphere_normal_N": normals,
                       "sphere_normal_sum_N": float(normals.sum()),
                       "last5s_attitude_span_deg": np.ptp(arr["roll_pitch_deg"][last], axis=0),
                       "last5s_max_speed_m_s": float(np.abs(arr["vel"][last]).max()),
                       "last5s_max_omega_rad_s": float(np.abs(arr["omega"][last]).max())},
        "sphere_normal_minus_analytic_N": normals - pose.sphere_force_N,
        "crawler_bushing": {
            "values": model.crawler_bushing_values.meta(),
            "yield_steps_ramp": yield_ramp, "yield_steps_after_ramp": cb.yield_steps - yield_ramp,
            "yield_steps_last10s": cb.yield_steps - yield_last10,
            "slip_total_mm": np.linalg.norm(cb.slip_total_m, axis=1) * 1e3,
            "events": [[e.t_s, e.leg, e.kind] for e in cb.events],
            "in_contact": cb.in_contact,
        },
        "timing": {"wall_s": wall, "steps": n_total, "us_per_step": wall / n_total * 1e6},
    }


# --- job --------------------------------------------------------------------------------------


SNAPSHOT_BUNDLE = "07_results/S6/snapshots_20261021_195044"
"""Batch that built the 14 settled crawler snapshots (K6: the crawler settle map was fitted
to this set; rebuilding the snapshots needs a map refit)."""


def _settle_map(level: str):
    """K1: ``CrawlerSettleMap.for_level(level)`` (python-expert, control/target.py)."""
    try:
        from outrigger_sim.control.target import CrawlerSettleMap
    except ImportError as error:  # pragma: no cover - until branch B delivers the API
        raise RuntimeError("control.target.CrawlerSettleMap not available yet (K1)") from error
    return CrawlerSettleMap.for_level(level)


class ForcedRetract:
    """Controller wrapper of RE1c: after ``t_start`` RR retracts ``depth`` at ``speed`` (measured
    stroke); the wrapped controller is still updated (Measurements only).

    ``others``:
    * ``"zero"`` (default, RE1c as before): every other leg 0 from the start, and after the
      retraction is done every leg 0 to the run end;
    * ``"controller"`` (ML retract episodes, U-S8-27 / C-S8-25 ①): only the forced leg is
      overridden until the retraction is done; the other legs take the controller command, and
      after ``done`` every leg is back to the controller.
    ``done_t_s``: time of the first period with ``done`` (None while retracting)."""

    OTHERS = ("zero", "controller")

    def __init__(self, inner, *, leg: int, depth_m: float, speed_m_s: float,
                 others: str = "zero") -> None:
        if others not in self.OTHERS:
            raise ValueError(f"others must be one of {self.OTHERS}: {others!r}")
        self.inner = inner
        self.leg = leg
        self.depth_m = depth_m
        self.speed_m_s = speed_m_s
        self.others = others
        self.t_start: float | None = None
        self.s0: float | None = None
        self.done = False
        self.done_t_s: float | None = None

    @property
    def period_s(self) -> float:
        return self.inner.period_s

    def reset(self) -> None:
        self.inner.reset()
        self.s0 = None
        self.done = False
        self.done_t_s = None

    def update(self, measurements):
        import numpy as np

        from outrigger_sim.signals import Command

        cmd = self.inner.update(measurements)
        if self.t_start is None or measurements.t_s < self.t_start:
            return cmd
        s = float(measurements.stroke_m[self.leg])
        if self.s0 is None:
            self.s0 = s
        retracting = not self.done and self.s0 - s < self.depth_m
        if not retracting and not self.done:
            self.done = True
            self.done_t_s = float(measurements.t_s)
        if self.others == "controller":
            if not retracting:
                return cmd
            u = np.array(cmd.leg_speed_m_s, dtype=float, copy=True)
            u[self.leg] = -self.speed_m_s
            return replace(cmd, leg_speed_m_s=u)
        u = np.zeros(4)
        if retracting:
            u[self.leg] = -self.speed_m_s
        return Command(t_s=measurements.t_s, leg_speed_m_s=u)

    def meta(self) -> dict[str, Any]:
        return {"wrapper": "ForcedRetract", "leg": self.leg, "depth_m": self.depth_m,
                "speed_m_s": self.speed_m_s, "t_start_s": self.t_start,
                "others": self.others, "done_t_s": self.done_t_s,
                "inner": self.inner.meta()}


def _settle_map_source() -> str | None:
    from outrigger_sim.control import target

    return getattr(target, "SETTLE_MAP_SOURCE", None)


def _controller(params, case: Stage2Case):
    from outrigger_sim.control.c2 import (
        C2Config,
        C2Controller,
        ContactJudge,
        ReanchorSettings,
        TargetSettings,
    )
    from outrigger_sim.control.target import AttitudeTarget, SlopeLimitMode, TargetAcceptance

    from outrigger_sim.control.zero_calibration import ZeroCalibrationMode

    roll, pitch = (math.radians(a) for a in case.target_deg)
    ramp = params.actuator.command_ramp_s
    base = C2Config(output_ramp_time_s=ramp if ramp > 0.0 else None)
    config = replace(
        base,
        # E-3 (U71): default on (C2 default); PS-2 / PS-4 'cal off' cases switch it off
        zero_calibration=base.zero_calibration if case.zero_calibration
        else replace(base.zero_calibration, mode=ZeroCalibrationMode.OFF),
        contact=ContactJudge(case.contact),
        reanchor=replace(base.reanchor, enable=case.h4),
        probe=base.probe if case.combined_verdict is None
        else replace(base.probe, use_combined_verdict=case.combined_verdict),
        target=replace(
            base.target,
            target=AttitudeTarget(roll_rad=roll, pitch_rad=pitch),
            slope_limit_mode=SlopeLimitMode.VERIFICATION,
            acceptance=TargetAcceptance(case.acceptance),
            check_time_s=case.check_time_s,
            crawler_settle_map=_settle_map(case.level),  # K1 (verification mode)
            # B1′ / GE1′ gate need the grade's per-sample gyro sigma (default 0 = ideal);
            # same ImuErrorConfig as the sensor suite of the case
            gyro_noise_std_rad_s=gyro_noise_std_for(case.grade),
        ),
    )
    _ = ReanchorSettings, TargetSettings  # types documented in the meta
    # U-S8-61 (spec 304 1): L1 runs take the R-5 fallback ratio from the plant meta. The R7
    # config of stage 2 has R-5 off, so this returns it unchanged (bit-identical runs).
    from outrigger_sim.chrono.fallback_ratio import with_engine_fallback_ratio

    config, _fallback_ratio_meta = with_engine_fallback_ratio(config, "L1", plant_params=params)
    return C2Controller.from_params(params, config), config


TARGET_CHANGE_PITCH_DEG = 3.0
"""G5 ``target_change``: the requested pitch after the first READY (``observe`` below)."""
H4_TRIGGER_DEG = 2.5
"""H4 trigger |theta_t - theta_anchor| >= 2.5 deg (control spec 17 / U2); used only to state the
expected REANCHOR outcome of a case (the controller decides by itself)."""


def c2_config_meta(config) -> dict[str, Any]:
    """C2 revision and H4 direction of the running configuration (spec 86.1 / 86.6, dynamics
    return condition 1). The revision is read from the installed ``control.c2`` module (never
    hard-coded: python-expert moves it R6 -> R7)."""
    from outrigger_sim.control import c2 as c2mod

    reanchor = config.reanchor
    return {"c2_revision": getattr(c2mod, "C2_REVISION", None),
            "reanchor_direction": str(getattr(reanchor, "direction", None)),
            "reanchor_enabled": bool(getattr(reanchor, "enable", True))}


def expected_reanchor(case: Stage2Case, direction: str | None) -> dict[str, Any]:
    """Expected REANCHOR outcome (spec 86.6) from the floor and the target of the case.

    Relative pitch = target - floor (theta > 0 nose down); relative nose-up = theta_t - theta_g >
    0 (spec 86.2 / 86.3, the controller uses theta_anchor = crawler attitude, which differs by
    the crawler settle offset 0.17-0.34 deg only, below the 2.5 deg trigger). With
    ``nose_down_only`` a triggering nose-up case is expected to end in exactly one
    ``reanchor_skipped:nose_up``; its REANCHOR rows are "not applicable (nose_up)"."""
    target_pitch = case.target_deg[1]
    if case.event == "target_change":
        target_pitch = TARGET_CHANGE_PITCH_DEG  # H4 re-decided after the change (U3)
    rel = target_pitch - FLOORS[case.floor][1]
    # a rejected start (G5 reject) never levels, so no H4 decision
    triggers = case.h4 and case.event != "reject" and abs(rel) >= H4_TRIGGER_DEG
    nose_up = rel > 0.0
    skipped = triggers and (direction == "off" or (direction == "nose_down_only" and nose_up))
    return {"relative_pitch_deg": rel, "triggers": triggers, "nose_up": nose_up,
            "direction": direction,
            "expected": ("reanchor_skipped:direction_off" if skipped and direction == "off"
                         else "reanchor_skipped:nose_up" if skipped
                         else "reanchor (run)" if triggers else None),
            "reanchor_applicable": bool(triggers and not skipped)}


def _l1r_meta() -> dict[str, Any]:
    import l1r_variant

    return l1r_variant.meta()


def _l1r_fallback(settlement: bool) -> str | None:
    import l1r_variant

    return l1r_variant.fallback_note(settlement=settlement)


BAR_PA = 1.0e5


def leg_sensor_config_for(case: Stage2Case, t0_s: float):
    """WIKA A-10 head / rod sensors of the case (spec 71 E-1 / E-2, U70-U73; bundle B):
    ``sensors.hydraulic.wika_a10_leg_sensor_config(grade)`` + the PS-4 / PS-7 deterministic head
    offsets and the PS-5 linear drift (absolute start time ``t0 + check_max +``
    :data:`PS5_DRIFT_START_AFTER_CHECK_S`)."""
    from outrigger_sim.sensors.hydraulic import wika_a10_leg_sensor_config

    over: dict[str, Any] = {}
    if any(case.head_offset_bar):
        over["head_offset_Pa"] = tuple(v * BAR_PA for v in case.head_offset_bar)
    if any(case.head_drift_bar):
        over["head_zero_drift_Pa_per_s"] = tuple(v * BAR_PA / PS5_DRIFT_S for v in case.head_drift_bar)
        over["zero_drift_start_s"] = (t0_s + case.check_time_s + check_extra_s(case)
                                      + PS5_DRIFT_START_AFTER_CHECK_S)
    return wika_a10_leg_sensor_config(case.pressure_grade, **over)


def gyro_noise_std_for(grade: str) -> float:
    """Per-sample gyro noise sigma_g of an IMU grade (rad/s), as the controller gets it."""
    from outrigger_sim.sensors.imu import imu_config_for_grade

    return float(imu_config_for_grade(grade).gyro_noise_std_rad_s)


SETTLE_VELOCITY_NAME = "settle_velocity.npz"
"""Per-step velocity record of the settlement cases (next to ``record/``, B2 M4 input)."""
SETTLE_VELOCITY_FORMAT = "s6_settle_velocity_v1"


class SettleVelocityRecorder:
    """Per physics step, per leg (LEG_ORDER): floor-normal velocity of the pad patch and of
    the pad ball centre (M4 input, ``dynamics_model.md`` 5.15.2: v_rel per step).

    Read in the runner step hook, i.e. on the final state of step ``n`` after the bushing hook
    and the L1-R machine step of the same step (``chrono/l1_engine`` hook order). Arrays:

    * ``t`` (s), ``dt`` (s, step just taken; variable inside a dt window);
    * ``v_patch_n`` (m/s): ``n . GetPosDt()`` of the leg's settlement patch body (translation
      only: prismatic guide, zero angular velocity, so every point has this velocity); legs on
      the fixed floor body read the floor body (0);
    * ``v_ball_n`` (m/s): ``n . PointSpeedLocalToParent(sphere centre)`` of the leg's pad body
      (same point and call as ``rod_chamber_link.deflection``);
    * ``z_patch_n`` (m): patch displacement along ``n`` from the fixed floor pose (settled = -);
    * ``v_patch_prescribed_n`` (m/s): derivative of the settlement motor function at ``t``
      (NaN on fixed-floor legs; the motor follows it with the one-step input lag, R15);
    * ``mode`` (int8): L1-R machine mode of the same step (EXT 1, RET 2, LOCK 3, FLOOR 4,
      LIFT 5), -1 when the machine did not step at ``t``;
    * ``p_head_Pa``, ``p_rod_Pa`` (Pa, gauge as the machine gives them): machine head / rod
      chamber pressures of the same step (``RodChamberStep.head_pressure_Pa`` /
      ``rod_pressure_Pa``), NaN when the machine did not step.

    ``t`` is ``system.GetChTime()`` read in the same hook as ``PadRecorder`` (this hook runs
    after it), i.e. the clock of ``pads.npz`` and ``record.npz`` (record ``t`` values are
    bit-equal members of this ``t``; checked after the run, summary ``t_record_subset``).

    Sign: ``n`` = floor normal (world, up), so both velocities are positive upwards. The M4
    quantities (downward positive) are ``v_ground = -v_patch_n``, ``v_corner = -v_ball_n`` and
    ``v_rel = v_ground - v_corner = v_ball_n - v_patch_n``.
    """

    _CHUNK = 65536

    def __init__(self, model: Any):
        import numpy as np

        self.model = model
        self.n_world = np.asarray(model.bushing.normal_world(), dtype=float)
        settlement = getattr(model, "settlement", None)
        by_name = {} if settlement is None else dict(zip(settlement.leg_names, settlement.bodies,
                                                         strict=True))
        from outrigger_sim.params import LEG_ORDER  # noqa: PLC0415

        self.leg_names = tuple(LEG_ORDER[: len(model.legs)])
        self.patch_bodies = tuple(by_name.get(name, model.floor) for name in self.leg_names)
        self.settling = np.array([name in by_name for name in self.leg_names])
        self.settlement = settlement
        self.legs = tuple(model.legs)
        self.centres = tuple(model.sphere_centres_local_ch)
        fp = model.floor.GetPos()
        self.floor_pos = np.array([fp.x, fp.y, fp.z], dtype=float)  # GetPos returns a reference
        fv = model.floor.GetPosDt()
        if not (model.floor.IsFixed() and fv.x == 0.0 and fv.y == 0.0 and fv.z == 0.0):
            raise RuntimeError("SettleVelocityRecorder: the floor body must be fixed and at rest")
        self._nxyz = tuple(float(c) for c in self.n_world)
        self._floor_xyz = tuple(float(c) for c in self.floor_pos)
        self._ball_pairs = tuple(zip(self.legs, self.centres, strict=True))
        self._moving = tuple((j, p) for j, p in enumerate(self.patch_bodies) if self.settling[j])
        self._rod_chamber = getattr(model, "rod_chamber", None)
        self._n = 0
        self._t_prev = float(model.system.GetChTime())
        self._alloc(self._CHUNK)

    def _alloc(self, size: int) -> None:
        import numpy as np

        k = len(self.legs)
        old = getattr(self, "_buf", None)
        new = {"t": np.empty(size), "dt": np.empty(size), "v_patch_n": np.empty((size, k)),
               "v_ball_n": np.empty((size, k)), "z_patch_n": np.empty((size, k)),
               "v_patch_prescribed_n": np.empty((size, k)),
               "mode": np.empty((size, k), dtype=np.int8),
               "p_head_Pa": np.empty((size, k)), "p_rod_Pa": np.empty((size, k))}
        if old is not None:
            for key, arr in old.items():
                new[key][: self._n] = arr[: self._n]
        self._buf = new

    def __call__(self, engine: Any) -> None:
        del engine
        import math as _m

        model = self.model
        if self._n == self._buf["t"].shape[0]:
            self._alloc(2 * self._n)
        i = self._n
        b = self._buf
        nx, ny, nz = self._nxyz
        t = float(model.system.GetChTime())
        b["t"][i] = t
        b["dt"][i] = t - self._t_prev
        self._t_prev = t
        v_ball = b["v_ball_n"][i]
        for j, (body, local) in enumerate(self._ball_pairs):
            v = body.PointSpeedLocalToParent(local)
            v_ball[j] = v.x * nx + v.y * ny + v.z * nz
        v_patch = b["v_patch_n"][i]
        z_patch = b["z_patch_n"][i]
        v_patch[:] = 0.0  # fixed-floor legs: the fixed floor body (checked at construction)
        z_patch[:] = 0.0
        fx, fy, fz = self._floor_xyz
        for j, patch in self._moving:
            pv = patch.GetPosDt()
            v_patch[j] = pv.x * nx + pv.y * ny + pv.z * nz
            pp = patch.GetPos()
            z_patch[j] = (pp.x - fx) * nx + (pp.y - fy) * ny + (pp.z - fz) * nz
        presc = b["v_patch_prescribed_n"][i]
        presc[:] = _m.nan
        if self._moving:
            fns = getattr(self.settlement, "_functions", None) if self.settlement.is_scheduled \
                else None
            v_presc = float(fns[0].GetDer(t)) if fns else 0.0
            for j, _patch in self._moving:
                presc[j] = v_presc
        rc = self._rod_chamber
        out = rc.output_at(t) if rc is not None else None
        if out is None:
            b["mode"][i] = -1
            b["p_head_Pa"][i] = _m.nan
            b["p_rod_Pa"][i] = _m.nan
        else:
            b["mode"][i] = out.mode
            b["p_head_Pa"][i] = out.head_pressure_Pa
            b["p_rod_Pa"][i] = out.rod_pressure_Pa
        self._n = i + 1

    def arrays(self) -> dict[str, Any]:
        return {k: v[: self._n].copy() for k, v in self._buf.items()}

    def save(self, path: Path) -> Path:
        import numpy as np

        meta = {
            "format": SETTLE_VELOCITY_FORMAT, "leg_order": list(self.leg_names),
            "settling_legs": [n for n, s in zip(self.leg_names, self.settling, strict=True) if s],
            "n_world": self.n_world.tolist(), "units": "s, m/s, m",
            "sign": "along the floor normal n (up +); M4 v_rel (down +) = v_ball_n - v_patch_n",
            "timing": "runner step hook: final state of each physics step (after the bushing "
                      "hook and the L1-R machine step of that step)",
            "settlement": None if self.settlement is None else self.settlement.meta(),
        }
        np.savez_compressed(path, **self.arrays(), meta_json=np.array(json.dumps(meta)))
        return path


def _chain_hooks(*hooks):
    """One runner ``step_hook`` calling every non-None hook in order (None if there is none)."""
    live = [h for h in hooks if h is not None]
    if not live:
        return None
    if len(live) == 1:
        return live[0]

    def hook(engine):
        for h in live:
            h(engine)

    return hook


M1_BEFORE = "before_M1"
"""L1-R extra force = machine F_x as computed (bundle B and older runs)."""
M1_AFTER = "after_M1"
"""L1-R extra force made one-sided (rod_side_pressure.md 17.1 M1, ``applied_extra_force_N``)."""


def rod_side_m1_status(model) -> dict[str, Any]:
    """Whether the model's L1-R link has M1 (coordinator 2026-10-22: mark B / B2 results)."""
    link = getattr(model, "rod_chamber", None)
    has = link is not None and hasattr(link, "applied_extra_force_N")
    enabled = bool(getattr(link, "enabled", False))
    return {"status": M1_AFTER if has else M1_BEFORE, "mechanics_on": enabled,
            "acts": has and enabled,
            "note": "M1 changes results only with mechanics on (off: no extra force)"}


def job_stage2(case_id: str, case_dir: Path, states_dir: Path, *, duration_s: float | None = None):
    """Run one stage-2 case (``run_S6.py run2``). Returns (summary, run_meta)."""
    import numpy as np

    from outrigger_sim.chrono.l1_engine import L1Engine
    from outrigger_sim.chrono.pad_record import PadRecorder
    from outrigger_sim.control.c2 import C2Phase
    from outrigger_sim.control.target import AttitudeTarget
    from outrigger_sim.params import load_params
    from outrigger_sim.record import load_snapshot, make_run_meta, save_record
    from outrigger_sim.runner import run_closed_loop
    from outrigger_sim.sensors.hydraulic import (
        leg_head_areas_from_params,
        reduced_model_leg_sensor_config,
    )
    from outrigger_sim.sensors.imu import imu_config_for_grade
    from outrigger_sim.sensors.suite import SensorSuite
    from outrigger_sim.verify.reference import load_references

    case = {c.case_id: c for c in all_cases()}[case_id]
    blocked = case.blocked_in(states_dir)
    if blocked:
        raise FileNotFoundError(f"{case_id}: {PREREQUISITES[blocked]}")
    params = load_params(level=case.level)
    settles = case.event in ("settle_RR", "settle_RR_30", "drop_RR_30", "drop_RR_30_probe")
    model, _pose = build_crawler_model(params, case.floor, attach=False,
                                       settlement_legs=("RR",) if settles else ())
    t0 = model.restore(load_snapshot(case.snapshot, params_sha256=params.sha256,
                                     directory=states_dir))
    engine = L1Engine(model, imu_method="chrono_point")
    leg_sensors = leg_sensor_config_for(case, t0)
    _ = reduced_model_leg_sensor_config, leg_head_areas_from_params  # pre-bundle-B sensors (record)
    suite = SensorSuite(imu_config_for_grade(case.grade), leg_sensors, seed=case.seed)
    from outrigger_sim.runner import DtSchedule

    dt_fine = float(params.get("simulation.dt_transition_s"))
    schedule = DtSchedule(model.dt_s, 0.02) if case.fine_dt else None
    c2, config = _controller(params, case)
    controller = c2
    forced = None
    if case.event == "retract_RR_25":
        forced = ForcedRetract(c2, leg=3, depth_m=0.025,
                               speed_m_s=0.25 * params.actuator.max_speed_m_s)
        controller = forced
    pre = None
    pre_info = None
    if case.pre_extend_leg is not None:
        from outrigger_sim.sensors.hydraulic import leg_annulus_areas_from_params

        gaps = pad_gaps_m(model)
        leg = case.pre_extend_leg
        target = float(gaps[leg]) + case.pre_extend_offset_mm * 1e-3
        pre = PreExtend(c2, leg=leg, target_m=target, speed_m_s=params.actuator.max_speed_m_s,
                        head_area_m2=leg_head_areas_from_params(params),
                        annulus_area_m2=leg_annulus_areas_from_params(params),
                        grounded_check=case.pre_extend_offset_mm > 0.0)
        controller = pre
        pre_info = {"g0_m": gaps.tolist(), "leg": leg, "offset_mm": case.pre_extend_offset_mm,
                    "target_m": target, "rule": "g0 = n . (c - p0) - r on the restored state"}
    ge1_attr = next((a for a in GE1_ATTRIBUTES if hasattr(c2, a)), None)
    ge1_series: list[Any] = []
    probe_margins: list[dict[str, Any]] = []
    stroke_hi = float(params.legs[0].extension_range_m[1])
    pads = None
    if case.pad_record:
        pads = (PadRecorder(engine, sample_s=1.0e-3) if case.fine_dt
                else PadRecorder(engine, every_steps=5))
    # B2 M4: per-step floor-normal patch / ball-centre velocities of the settlement cases
    settle_vel = SettleVelocityRecorder(model) if settles else None
    phases: list[tuple[float, str]] = []
    probe_intervals: list[dict[str, Any]] = []
    state = {"ready_t": None, "scheduled": False, "requested": None, "probe_t": None,
             "event_t": None, "fine_open_t": None, "rr_contact_since": None,
             "fine_capped": False, "rr_lifted_seen": False}

    def ge1_sample():
        value = getattr(c2, ge1_attr)
        value = value() if callable(value) else value
        if hasattr(value, "to_meta"):
            value = value.to_meta()
        elif hasattr(value, "__dataclass_fields__"):
            value = asdict(value)
        if isinstance(value, dict):
            value = dict(value)
            for name in GE1_CONTROLLER_ATTRIBUTES:
                if name in value or not hasattr(c2, name):
                    continue
                extra = getattr(c2, name)
                extra = extra() if callable(extra) else extra
                if hasattr(extra, "__dataclass_fields__"):
                    extra = asdict(extra)
                value[name] = extra
        return value

    def drop(t_start):
        model.settlement.schedule(t_start, depth_m=RE1B_DROP_DEPTH_M, ramp_s=RE1B_DROP_RAMP_S,
                                  dt_s=dt_fine)
        state["scheduled"] = True
        state["event_t"] = t_start

    def fine_window(t):
        """Open / close the transition dt window (module docstring), at a control instant."""
        if schedule is None:
            return
        ev = state["event_t"]
        if ev is not None and state["fine_open_t"] is None and not schedule.is_open \
                and t >= ev - FINE_PRE_S - 1e-9 and len(schedule.segments) == 1:
            schedule.open(t, dt_fine, reason="RR drop transition")
            state["fine_open_t"] = t
        if not schedule.is_open:
            return
        n_rr = float(engine.truth().F_contact_n_N[3])
        if n_rr > 0.0:
            if state["rr_contact_since"] is None:
                state["rr_contact_since"] = t
        else:
            state["rr_contact_since"] = None
            state["rr_lifted_seen"] = True
        since = state["rr_contact_since"]
        if (ev is not None and t >= ev + FINE_PRE_S and since is not None
                and t - since >= FINE_HOLD_S - 1e-9):
            schedule.close(t, reason="RR in contact for FINE_HOLD_S after the drop")
        elif t - state["fine_open_t"] >= FINE_MAX_S - 1e-9:
            schedule.close(t, reason="FINE_MAX_S cap (RR not back in contact)")
            state["fine_capped"] = True

    def observe(meas, command):
        del command
        ph = c2.phase
        n_rounds = len(c2.probe_history)
        if not phases or phases[-1][1] != ph.value:
            if phases and phases[-1][1] == "probe" and probe_intervals:
                iv = probe_intervals[-1]
                iv.update(t_end_s=meas.t_s - t0, next_phase=ph.value,
                          rounds_completed=n_rounds - iv["rounds_at_start"])
                # PROBE -> LEVEL with no round completed = cut by a re-level (R5: only the
                # attitude trigger acts in PROBE; a Q2 re-ground ends in LEVEL after a round)
                iv["interrupted_by_relevel"] = ph.value == "level" and iv["rounds_completed"] == 0
            if ph.value == "probe":
                probe_intervals.append({"t_start_s": meas.t_s - t0, "rounds_at_start": n_rounds})
            phases.append((meas.t_s - t0, ph.value))
            if ph.value == "probe":  # stroke margin per leg at every probe start (true stroke)
                s_true = [float(mo.GetMotorPos()) for mo in model.motors]
                probe_margins.append({"t_s": meas.t_s - t0,
                                      "margin_m": [stroke_hi - v for v in s_true],
                                      "stroke_meas_m": [float(v) for v in meas.stroke_m]})
        if ge1_attr is not None:
            ge1_series.append((meas.t_s - t0, ph.value, ge1_sample()))
        if ph is C2Phase.READY and state["ready_t"] is None:
            state["ready_t"] = meas.t_s
        if ph is C2Phase.PROBE and state["probe_t"] is None:
            state["probe_t"] = meas.t_s
        if case.event == "drop_RR_30_probe" and not state["scheduled"]:
            t_ev = None
            if RE1BP_TIMING == "probe_start" and state["probe_t"] is not None:
                t_ev = state["probe_t"] + RE1BP_DELAY_S
            elif RE1BP_TIMING == "rr_turn":
                rnd = getattr(getattr(c2, "_state", None), "probe_round", None)
                if rnd is not None and getattr(rnd, "leg", None) == 3:
                    t_ev = meas.t_s + 0.02  # one control period ahead (settlement lead)
            if t_ev is not None:
                drop(t_ev)
        if case.event == "drop_RR_30" and not state["scheduled"] and state["ready_t"] is not None:
            drop(state["ready_t"] + 5.0)
        fine_window(meas.t_s)
        if state["ready_t"] is None:
            return
        if case.event == "settle_RR" and not state["scheduled"]:
            model.settlement.schedule(state["ready_t"] + 5.0, dt_s=model.dt_s)
            state["scheduled"] = True
        if case.event == "settle_RR_30" and not state["scheduled"]:
            model.settlement.schedule(state["ready_t"] + 5.0, depth_m=0.030, ramp_s=5.0,
                                      dt_s=model.dt_s)
            state["scheduled"] = True
        if forced is not None and forced.t_start is None:
            forced.t_start = state["ready_t"] + 5.0
        if (case.event == "target_change" and state["requested"] is None
                and meas.t_s >= state["ready_t"] + 2.0):
            state["requested"] = str(c2.request_target(
                AttitudeTarget(roll_rad=0.0, pitch_rad=math.radians(TARGET_CHANGE_PITCH_DEG))))

    c2_meta = c2_config_meta(config)
    expect = expected_reanchor(case, c2_meta["reanchor_direction"])
    settings = {**asdict(case), "snapshot": case.snapshot, "start_t_s": t0,
                **c2_meta, "reanchor_expected": expect,
                "l1r": {**_l1r_meta(),
                        "effective_mechanics": str(getattr(model.rod_chamber, "mechanics", None)),
                        "fallback": _l1r_fallback(settles),
                        "m1": rod_side_m1_status(model)},
                "leg_sensors": leg_sensors.to_meta(),
                "gyro_bias_removal": "none (check_time_s 0, CHECK skipped)"
                if case.check_time_s == 0.0 else "CHECK standstill",
                "controller_config": str(config),
                "gyro_noise_std_rad_s_passed": config.target.gyro_noise_std_rad_s,
                "gyro_noise_std_deg_s_passed": math.degrees(config.target.gyro_noise_std_rad_s)}
    run_meta = make_run_meta(params, engine.meta(), scenario=f"S6_stage2_{case_id}",
                             scenario_settings=settings, sensors=suite.setup(),
                             reference_sha256=load_references().sha256_by_file())
    wall0 = time.perf_counter()
    res = run_closed_loop(engine, controller, suite, duration_s or case.duration_s,
                          run_meta=run_meta, on_control=observe, command_delay_periods=1,
                          step_hook=_chain_hooks(pads, settle_vel),
                          capture_every_steps=5 if pads and schedule is None else None,
                          dt_schedule=schedule,
                          capture_every_s=1.0e-3 if pads and schedule is not None else None,
                          placement=run_placement())
    wall = time.perf_counter() - wall0
    save_record(res.record, case_dir / "record")
    if pads is not None:
        pads.save(case_dir / "pads.npz")
    if settle_vel is not None:
        settle_vel.save(case_dir / SETTLE_VELOCITY_NAME)
    events = [str(e) for e in c2.events]
    # item 7: probe results per round and leg (attitude response ratio etc.) next to the
    # 1 ms pad record (true normal force N) for the comparison
    probes = [[asdict(r) if hasattr(r, "__dataclass_fields__") else str(r) for r in rnd]
              for rnd in c2.probe_history]
    (case_dir / "probe_history.json").write_text(
        json.dumps(probes, indent=1, default=str), "utf-8")
    (case_dir / "controller_events.json").write_text(json.dumps(events, indent=1), "utf-8")
    arr = res.record.arrays
    f_crawler = np.asarray(arr["F_crawler"])[:, 2]
    off = np.flatnonzero(f_crawler > 0.0)
    t_off = float(arr["t"][off[-1] + 1]) if off.size and off[-1] + 1 < len(f_crawler) else None
    # K1 / K8 / K4: CHECK code, crawler attitude, floor estimates and utilisation, shadow
    # (X9) floor estimate at the end of TOUCH, H4 outcome, stroke maximum and margin
    s_motor = np.asarray(arr["s_motor"])
    stroke_hi = float(params.legs[0].extension_range_m[1])
    reanchor = c2.reanchor_outcome
    h4_status = None
    nose_up_skips = sum(1 for e in events if "reanchor_skipped:nose_up" in e)
    reanchor_starts = sum(1 for e in events if "reanchor_started" in e)
    if case.h4:
        if reanchor is not None and "stroke_margin" in str(reanchor):
            h4_status = "judgement not possible (condition not met: stroke_margin)"
        elif reanchor is not None and "nose_up" in str(reanchor):
            # spec 86.6: nose-up H4 case under nose_down_only -> REANCHOR rows not applicable
            h4_status = "not applicable (nose_up)"
        else:
            h4_status = str(reanchor)
    ctl_meta = c2.meta()
    acceptance = {
        "target_code": None if c2.target_code is None else str(c2.target_code),
        "crawler_attitude_deg": None if c2.crawler_attitude_rad is None
        else [math.degrees(a) for a in c2.crawler_attitude_rad],
        "target_checks": [str(c) for c in c2.target_checks],
        "last_check": (ctl_meta.get("target", {}).get("checks") or [None])[-1],
        "floor_estimate_rad": ctl_meta.get("target", {}).get("floor_estimate_rad"),
        "crawler_settle_map": ctl_meta.get("target", {}).get("crawler_settle_map"),
        "settle_map_source": _settle_map_source(),
        "floor_estimate_touch": ctl_meta.get("floor_estimate_touch"),
        "floor_true_deg": FLOORS[case.floor],
        "snapshot_bundle": SNAPSHOT_BUNDLE,
        "slope_limit_mode": "verification",
    }
    n_floor = model.bushing.normal_world()
    p_floor = np.asarray(model.floor_point_world_m, dtype=float)
    floor_plane = {"normal_world": n_floor.tolist(), "offset_m": float(n_floor @ p_floor),
                   "note": "fixed floor plane n . x = d (world); a settled pad patch is not in it"}
    if ge1_series:
        (case_dir / "ge1_series.json").write_text(
            json.dumps(ge1_series, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)),
            "utf-8")
    summary = {
        "case": case_id, "settings": settings, "phases": phases, "events_count": len(events),
        "acceptance": acceptance,
        "h4": {"enabled": case.h4, "outcome": None if reanchor is None else str(reanchor),
               "status": h4_status, "expected": expect,
               "direction": ctl_meta.get("reanchor_direction"),
               "n_reanchor_skipped_nose_up": nose_up_skips, "n_reanchor_started": reanchor_starts,
               # judged only for the nose-up skip of spec 86.6 (a nose-down run may still skip
               # on stroke_margin etc., K4)
               "expectation_met": (nose_up_skips == 1 and reanchor_starts == 0)
               if expect["expected"] == "reanchor_skipped:nose_up" else None},
        "c2": c2_meta,
        "stroke": {"max_m": s_motor.max(axis=0), "min_m": s_motor.min(axis=0),
                   "margin_to_end_m": stroke_hi - s_motor.max(axis=0)},
        "controller_meta": ctl_meta,
        "probe_start_stroke_margin": probe_margins,
        "probe_events": [e for e in events if "probe" in e],
        "probe_skipped": [e for e in events if "probe_skipped" in e],
        "ge1": {"attribute": ge1_attr, "n_samples": len(ge1_series),
                "meta_keys": {k: v for k, v in ctl_meta.items() if "geom" in k.lower()},
                "support_geometry": ctl_meta.get("support_geometry"),
                "shadow_events": [e for e in events if "shadow_" in e]},
        "floor_plane": floor_plane,
        "forced_retract": None if forced is None else forced.meta(),
        "pre_extend": None if pre is None else {**pre_info, **pre.meta()},
        "settle_velocity": None if settle_vel is None else {
            "file": SETTLE_VELOCITY_NAME, "n_steps": int(settle_vel._n),
            "keys": list(settle_vel._buf),
            "t_record_subset": bool(np.all(np.isin(np.asarray(arr["t"]),
                                                   settle_vel._buf["t"][: settle_vel._n])))},
        "zero_calibration_report": zero_calibration_report(
            res.record.arrays, phases, t0, ctl_meta, events, params,
            start_s=None if pre is None or pre.handover_t is None else pre.handover_t - t0),
        "gyro_check": gyro_check_for(res.record.arrays, phases, t0, ctl_meta, events, params,
                                     None if pre is None or pre.handover_t is None
                                     else pre.handover_t - t0),
        "ready_t_s": None if state["ready_t"] is None else state["ready_t"] - t0,
        "probe_intervals": probe_intervals,
        "first_probe_t_s": None if state["probe_t"] is None else state["probe_t"] - t0,
        "event_t_s": (None if state["event_t"] is None else state["event_t"] - t0)
        if case.event in FINE_EXPECTED_S
        else (None if state["ready_t"] is None or case.event in (None, "reject")
              else (state["ready_t"] + (2.0 if case.event == "target_change" else 5.0)) - t0),
        "event_definition": {
            "drop_RR_30": "first READY + 5 s, RR floor 30 mm in 0.05 s",
            "drop_RR_30_probe": f"first PROBE start + {RE1BP_DELAY_S} s ({RE1BP_TIMING}), RR "
                                "floor 30 mm in 0.05 s",
        }.get(case.event or "", case.event),
        "fine_dt": None if schedule is None else {
            "dt_transition_s": dt_fine, "opened_t_s": None if state["fine_open_t"] is None
            else state["fine_open_t"] - t0, "capped": state["fine_capped"],
            "rr_lifted_seen_in_window": state["rr_lifted_seen"],
            "rule": f"open {FINE_PRE_S} s before the event (or at scheduling), close at event + "
                    f"{FINE_PRE_S} s once RR held contact {FINE_HOLD_S} s, cap {FINE_MAX_S} s",
            "segments_abs_t": schedule.to_meta()},
        "seed": case.seed,
        "ge1_r5_names": ge1_r5_preflight(),
        "re1bp_relevel_check": RE1BP_RELEVEL_CHECK if case.event == "drop_RR_30_probe" else None,
        "target_request": state["requested"], "crawler_off_t_s": None if t_off is None else t_off - t0,
        "monitor": engine.step_monitor(), "runner": {**res.meta, "wall_s": wall,
                                                     "n_steps": res.n_steps},
    }
    return summary, run_meta


__all__ = ["Stage2Case", "job_stage2", "plan_document", "stage2_cases"]
