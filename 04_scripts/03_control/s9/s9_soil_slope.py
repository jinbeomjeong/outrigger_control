"""Study 1 "soft soil x floor slope": reduced closed-loop screen of the project C2 on the S9 soil
harness (control-expert design 2026-10-28, user decisions applied).

Harness: ``s9_soil_closed_loop.py`` (imported; settle-table cases use its settle hook "harness"): reduced 6-DoF FlexPlant, L1-R rod-side
law, Coulomb seal friction (F_s 4 kN front, rear 0.833 x), valve lag 0.1 s, IMU 10 ms, one
Chrono-type SCM element per pad, floor tilted by ``slope = (roll, pitch)`` [deg] plus the P0 soil
settle pitch. Run limit 240 s (``S9_RUN_LIMIT_S``), hold 10 s after READY.
Controller: the project preset of the harness (``c2py_r8d1_closed_loop.preset_config(COMBINED)``
= ``C2Config.with_10hz_d1()`` without CHECK / zero calibration / REANCHOR / target check), as the
r72 G6 screen. H4 turns REANCHOR on: ``replace(cfg, reanchor=replace(cfg.reanchor, enable=True))``.

Case sets (177):
  H1 main grid      soil {G1, J1, J2, S1} x pad {B, A} x 8 slopes x top                     = 64
  H2 auger bottom   soil 4 x pad B x 8 slopes x bottom                                       = 32
  H3 feasibility    soil {J1, J2, S1} x pad {B, A} x {nose_down, roll_pos, edge_nd}
                    x k {0.5, 0.75, 0.875} (slope = k x the direction at k = 1)             = 54
  H4 REANCHOR on    soil 4 x pad {B, A} x {(0, 3.2), (0, 2.8)} top + rigid 2 + J1 B (0, -3.2) = 19
  H5 rigid ref      rigid x 8 slopes x top (project controller)                              = 8
  H6 (spec 422, decision Q-B, only with --groups H6) J1 B operating-weight sensitivity, flat:
                    J1 B x {top, middle, bottom} x F_s {0, 4} x mass {1.0, 1.1, 1.2} = 18,
                    J1 A x {top, bottom} x 4 kN x {1.0, 1.1, 1.2} = 6, J2 B x {top, bottom} x
                    4 kN x {1.0, 1.1} = 4, G1 B x {top, bottom} x 4 kN x 1.2 = 2, rigid B top x
                    F_s {0, 4} x 1.2 = 2                                                     = 32
                    Plant mass / inertia x scale only (controller YAML mass, W_ref unchanged;
                    crawler settle at the nominal weight); records probe rounds (probe and
                    re-level time per round), weight ratios, WARN_WEIGHT_MISMATCH, rear sink.
  H8 (spec 426.6 study D, only with --groups H8) non-planar start on soil: {G1, J2, rigid} x
                    pad B top F_s 4 flat x (reference + leg {FL, RR} x start gap {20, 55, 110 mm;
                    settle gap + 60, + 150 mm}) = 33. After the crawler settle the floor under
                    the leg is moved (``s9_soil_closed_loop`` key ``pad_start_gap``); the settle
                    check takes the start gap as that pad's gap target; TOUCH record (``touch``:
                    T-3' > 40 mm, T-4 > 1.0 deg, T-2' > 3.0 s FLAGs, per-leg contact / latch,
                    phase segments, true vs controller clearance at the end) and ``sample``
                    (reference "in", start-gap runs "out").
Judgement rows per run (spec 284 P3 rows with rev. 60 and the 377 demotion, plus SL / RA):
  P3-1 crawler 0 from READY to the run end, no re-contact after the first lift-off
  P3-2 LOC before the first DONE, t_LOC - t_off <= 2.9 s
  P3-3 min true F_cyl after the crawler lift-off >= F_min (record: F_min + 5 kN)
  P3-4 end attitude |roll|, |pitch| <= 0.2 deg
  P3-5 rut clearance at READY and at the end >= 25 mm, motor stroke <= 684.8 mm; rut clearance =
       lowest height of ALL crawler nodes above the harness floor plane (``RUT_DEFINITION``, as
       the G8 screen after r69; the first form, the rise of the settle-contact nodes, missed the
       uphill end shoes on slopes and is kept as ``rut_settle_nodes_mm``)
  P3-6 READY <= 120 s slope / 100 s flat pad B on J1, J2, S1 (spec 421.1) / 90 s other flat
       (ASSUMPTION, record)
  P3-7 not computed by this harness (needs the soil-rule rise log, record None)
  P3-8 no re-approach start / probe abort before the LOC; a re-approach start is demoted to a
       FLAG when the started leg keeps true F_cyl >= F_min up to LOC + 1 s and no FAULT (377)
  SL-1 stroke gate: FAULT_STROKE_END / FAULT_LIFT_STROKE_LIMIT 0, motor stroke <= 684.8 mm;
       WARN_LIFT_STROKE_LIMITED = class "stroke limited" (user decision, corrected: passes with
       FAULT 0, no leg lift and P3-1, P3-3, P3-4 passed; only P3-5 is relaxed)
  SL-2 start condition R_c = |phi|/4.4 + |theta|/3.2 of the crawler settle attitude, FLAG > 1
  SL-3 clearance bias: c_min(t_P), b_k, anchor, true minus estimate after the LOC, under-lift
       FLAG (true < estimate - 20 mm)
  SL-4 sink asymmetry: final sink per pad, downhill minus uphill mean, crawler settle tilt
  RA-1 REANCHOR only at a relative nose-down pitch >= 2.5 deg, skip reasons recorded
  RA-2 min true F_cyl of the four legs during REANCHOR >= F_min + 5 kN (judged)
  RA-3 attitude aborts, re-levels, end attitude <= 0.2 deg after REANCHOR (judged)
  RA-4 sink increase of the non-target legs during REANCHOR (record)
  RA-5 pad tangential utilisation (Chrono only, None here)
  RA-6 step-stroke (8 mm) aborts (record)
k*: per soil / pad / direction the largest slope ratio k of an unbroken run of feasible points
  from k = 0 (feasible = verdict pass, no stroke-guard event, motor stroke <= 682.8 mm), plus the
  linear stroke interpolation at 682.8 mm and the difference to the additive prediction.
Known approximations (every result carries them in ``approximations``):
  A1 crawler settle = flat P0 soil settle plus the floor tilt (no slope asymmetry). A settle
     correction (dz [m] deeper, droll / dpitch [deg]) per case can be injected with
     ``--settle-corrections`` (dynamics-expert table); without it the flag says "not corrected".
     Recommended: ``--settle-table 06_analysis/00_dynamics/slope_crawler_settle.json``
     (block ``hook_harness``, key soil|level|roll|pitch): the table floor add REPLACES the flat
     P0 pitch add of make_plant (that add is biased: harness rigid crawler 0.179 deg vs P0 rigid
     0.289 deg) and SoilPads.h = pad_h_m. Every soil case with a row gets it (flat included);
     a soil case without a row runs uncorrected and is marked "no_table_row"; rigid cases are
     the table reference (a non-zero rigid row is an error). After the settle the run is
     checked (pad penetration at the settle instant within 1 mm of -gap_target_mm; settle
     attitude in the original-floor axes, mean over the first 5 s of the closed loop cut at the
     first pad contact as the table's 5 s means, within 0.005 deg of target_q_floor; an
     instant sample is not usable: the settle leaves the crawler rocking up to 0.08 deg
     peak to peak on 3.2 deg nose down); a miss gives the verdict
     "settle_check_fail" (not judged, rows kept, k* point missing).
  A2 pad tangential = rigid harness bushing (no SCM shear capacity): REANCHOR results qualitative.
  A3 crawler load tail faster than Chrono (J1: harness optimistic, spec 391).

Usage (project root, dynamics-dev, MKL_THREADING_LAYER=TBB, OMP_NUM_THREADS=1):
  python -I s9_soil_slope.py [--out JSON] [--workers N] [--affinity ecore|pcore|0xMASK]
                             [--groups H1,H2] [--filter SUBSTR,...] [--settle-corrections JSON]
                             [--settle-table JSON [--settle-key hook_harness]]
                             [--plateau-rise-max-n N] [--mass-scale X] [--fs-kn X]
                             [--level top|middle|bottom] [--list] [--from-json JSON]
  --fs-kn / --level (spec 426.4 study B): applied to every selected case after --filter (as
               --mass-scale); --level attaches the settle-table rows of the new level.
  --from-json: re-judge the stored rows with the current verdict rules and rewrite the summary
               (no runs; the stored rut clearance keeps its definition).
  --plateau-rise-max-n: LOC plateau rise threshold for every case (U-S9-C2 sensitivity).
  --affinity defaults to the environment variable OUTRIGGER_PLACEMENT (unset: no change).
Units SI unless the key says otherwise (deg, mm, kN, s).
"""

from __future__ import annotations

import argparse
import csv
import ctypes
import hashlib
import json
import math
import os
import sys
import time
import traceback
from collections import Counter
from dataclasses import asdict, dataclass, field, replace
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(HERE) not in sys.path:  # -I drops the script folder; the shared judge rule lives here
    sys.path.insert(0, str(HERE))

import late_loc_rule  # noqa: E402

DEFAULT_OUT = ROOT / "06_analysis" / "02_control" / "s9" / "rev78" / "s9_soil_slope.json"

SOILS = ("G1", "J1", "J2", "S1")
BOUNDARY_SOILS = ("J1", "J2", "S1")
PADS = ("B", "A")
LEVEL_TOP = "top"
LEVEL_MIDDLE = "middle"
LEVEL_BOTTOM = "bottom"
FS_KN = 4.0
RIGID = "rigid"
SLOPES_DEG: dict[str, tuple[float, float]] = {
    "flat": (0.0, 0.0),
    "nose_down": (0.0, 3.2),
    "nose_up": (0.0, -3.2),
    "roll_pos": (4.4, 0.0),
    "roll_neg": (-4.4, 0.0),
    "edge_nd": (2.2, 1.6),
    "edge_nu": (2.2, -1.6),
    "rpB": (2.7355, 1.7592),
}
"""(floor roll, floor pitch) [deg]; pitch > 0 = nose down, roll > 0 = left side up."""
BOUNDARY_DIRECTIONS = ("nose_down", "roll_pos", "edge_nd")
BOUNDARY_K = (0.5, 0.75, 0.875)
REANCHOR_SLOPES_DEG: dict[str, tuple[float, float]] = {
    "nose_down": (0.0, 3.2),
    "nose_down_2p8": (0.0, 2.8),
}
REANCHOR_EXTRA = (("J1", "B", "nose_up"),)
GROUP_SIZES = {"H1": 64, "H2": 32, "H3": 54, "H4": 19, "H5": 8}
"""Default groups (study 1, 177); H6 (spec 422, 32) runs only when named in ``--groups``."""
H6_SIZE = 32
H8_SOILS = ("G1", "J2", "rigid")
H8_LEGS = ("FL", "RR")
START_GAP_GAP = "gap"
START_GAP_DELTA = "delta"
START_GAP_ID_LETTER = {START_GAP_GAP: "g", START_GAP_DELTA: "d"}
H8_START_GAPS = ((START_GAP_GAP, 20.0), (START_GAP_GAP, 55.0), (START_GAP_GAP, 110.0),
                 (START_GAP_DELTA, 60.0), (START_GAP_DELTA, 150.0))
"""Spec 426.6: bump = target gap 20 / 55 / 110 mm, dip = settle gap + 60 / 150 mm (the TOUCH
boundaries of the r69 G8 grid: free-air windows 52 / 105 mm, R-2 40 mm)."""
H8_SIZE = 33
"""3 soils x (1 reference without a start gap + 2 legs x 5 start gaps)."""
H8_GROUP = "H8"
TOUCH_FLAG_LIMITS = {"T3_mm": 40.0, "T4_deg": 1.0, "T2_s": 3.0}
"""Spec 426.6 TOUCH records (FLAG, r69 thresholds): stroke of leg k from its first contact to its
latch, attitude change in TOUCH, latch delay after the first contact."""

PRIOR_K_PREDICTION = {
    ("J1", "B"): {"nose_down": 0.84, "roll_pos": 0.94, "edge_nd": 0.90},
    ("J2", "B"): {"nose_down": 0.72, "roll_pos": 0.81, "edge_nd": 0.77},
    ("S1", "A"): {"nose_down": 0.62, "roll_pos": 0.70, "edge_nd": 0.66},
}
"""Additive (pre-run) prediction of k* from the design note."""

STROKE_OK_MM = 684.8
STROKE_GUARD_MM = 682.8
LOC_DELAY_MAX_S = 2.9
RUT_MIN_MM = 25.0
ATTITUDE_TOL_DEG = 0.2
D8_MARGIN_KN = 5.0
READY_FLAT_MAX_S = 90.0
READY_SLOPE_MAX_S = 120.0
READY_SOFT_PAD_B_MAX_S = 100.0
"""Spec 421.1 (decision Q-A): flat, pad B, J1 / J2 / S1 under both rear pads (study 1 is uniform)."""
SOFT_SOILS = ("J1", "J2", "S1")
PERIOD_LOG_S = 0.1
"""Control period of the per-period log (a run of n log rows lasts n x 0.1 s)."""
MASS_SCALE_NOTE = ("spec 422.2: plant mass / inertia scaled, controller YAML mass and W_ref "
                   "unchanged; crawler settle (pad gaps, settle tilt) at the nominal weight")
START_ROLL_LIMIT_DEG = 4.4
START_PITCH_LIMIT_DEG = 3.2
UNDER_LIFT_MM = 20.0
REANCHOR_THETA_MIN_DEG = 2.5
PRELOC_WINDOW_AFTER_LOC_S = 1.0
PRELOC_WINDOW_BEFORE_START_S = 0.1
REANCHOR_WINDOW_TAIL_S = 0.2
"""Two control periods after the last REANCHOR period: the output delay d = 1 plus the valve lag."""
TIME_MATCH_S = 1e-6
REANCHOR_TARGET_LEGS = ("RR", "RL")

FAULT_PHASES = ("fault", "fault_reground")
PRE_LEVEL_PHASES = ("idle", "check", "touch")
STROKE_FAULT_EVENTS = ("FAULT_STROKE_END", "FAULT_LIFT_STROKE_LIMIT")
STROKE_GUARD_WARNING = "WARN_LIFT_STROKE_LIMITED"
LOC_EVENT = "crawler_liftoff_confirmed"
LOC_ANCHOR_EVENT = "INFO_LOC_CLEARANCE_ANCHOR"
STORED_EVENT_SKIP_PREFIXES = ("INFO_PRESSURE", "shadow", "INFO_D1")
LEGS = ("FL", "FR", "RL", "RR")

PLACEMENT_ENV = "OUTRIGGER_PLACEMENT"
E_CORE_MASK = 0x0FFF0000
P_CORE_MASK = 0x0000FFFF
"""i7-14700: logical processors 0-15 = 8 P-cores with HT, 16-27 = 12 E-cores."""

APPROXIMATION_NOTES = {
    "A1": "crawler settle = flat P0 soil settle + floor tilt (no slope asymmetry)",
    "A2": "pad tangential = rigid harness bushing (no SCM shear capacity); REANCHOR qualitative",
    "A3": "crawler load tail faster than Chrono (J1 harness optimistic, spec 391)",
}

VERDICT_PASS = "pass"
VERDICT_FAIL = "fail"
VERDICT_STROKE_LIMITED_PASS = "stroke_limited_pass"
VERDICT_STROKE_LIMITED_FAIL = "stroke_limited_fail"
VERDICT_ERROR = "error"
VERDICT_SETTLE_CHECK_FAIL = "settle_check_fail"
STROKE_LIMITED_REQUIRED_ROWS = ("P3-1", "P3-3", "P3-4")
"""Rows a "stroke limited" run must still pass (P3-5 is the relaxed one)."""
RUT_DEFINITION = "all_nodes_floor_gap"
"""Rut clearance = lowest height of ALL crawler nodes above the harness floor plane (as the G8
screen after the r69 correction). The first definition (rise of the settle-contact nodes only)
missed the uphill end shoes on a slope: 74..152 mm on rigid slopes for a 50 mm target."""
RUT_DEFINITION_OLD = "settle_contact_nodes"

SETTLE_TABLE_KEY = "hook_harness"
SETTLE_GAP_TOL_MM = 1.0
SETTLE_ATTITUDE_TOL_DEG = 0.005
SETTLE_MEAN_WINDOW_S = 5.0
"""Attitude check window after the settle (the table targets are 5 s means)."""

_CAP: dict = {}
"""Per-worker capture of the plant, controller and per-period log of the running case."""
_ORIGINALS: dict = {}


# ------------------------------------------------------------------------------------ cases
@dataclass(frozen=True)
class SettleCorrection:
    """Crawler settle correction on a slope (A1): extra sink and extra crawler tilt.

    ``dz_m`` > 0 = the crawler sits deeper; ``droll_deg`` > 0 = left side up; ``dpitch_deg``
    > 0 = nose down. The floor of the harness is tilted by (droll, dpitch) and the pad soil
    surfaces are moved back to the original ground: h_i += dz + x_i tan(dpitch) - y_i tan(droll).
    """

    dz_m: float = 0.0
    droll_deg: float = 0.0
    dpitch_deg: float = 0.0

    @property
    def is_zero(self) -> bool:
        return self.dz_m == 0.0 and self.droll_deg == 0.0 and self.dpitch_deg == 0.0


@dataclass(frozen=True)
class SettleTableRow:
    """One ``hook_harness`` row of the dynamics slope settle table (A1, replaces the flat P0 add).

    The harness floor is tilted by (roll + ``floor_roll_add_deg``, pitch + ``floor_pitch_add_deg``)
    INSTEAD of the flat P0 pitch that ``make_plant`` adds; the pad soil surface heights are
    ``SoilPads.h = pad_h_m`` (FL, FR, RL, RR; goff = -h). Check values: ``target_q_floor`` =
    [uz m, phi rad, theta rad] of the settle in the original-floor axes, ``gap_target_mm`` = pad
    bottom to the original soil surface after the settle.
    """

    floor_roll_add_deg: float
    floor_pitch_add_deg: float
    pad_h_m: tuple[float, float, float, float]
    target_q_floor: tuple[float, float, float]
    gap_target_mm: tuple[float, float, float, float]
    settle_pitch_pp_deg: float | None = None

    @classmethod
    def from_table(cls, row: dict) -> SettleTableRow:
        return cls(floor_roll_add_deg=float(row["floor_roll_add_deg"]),
                   floor_pitch_add_deg=float(row["floor_pitch_add_deg"]),
                   pad_h_m=tuple(float(v) for v in row["pad_h_m"]),
                   target_q_floor=tuple(float(v) for v in row["target_q_floor"]),
                   gap_target_mm=tuple(float(v) for v in row["gap_target_mm"]),
                   settle_pitch_pp_deg=row.get("harness_settle_pitch_pp_deg"))

    @property
    def is_zero(self) -> bool:
        return (self.floor_roll_add_deg == 0.0 and self.floor_pitch_add_deg == 0.0
                and not any(self.pad_h_m))


@dataclass(frozen=True)
class SlopeCase:
    """One reduced closed-loop run of the soil x slope study."""

    group: str
    soil: str
    pad: str
    level: str
    slope_name: str
    roll_deg: float
    pitch_deg: float
    reanchor: bool = False
    direction: str | None = None
    k: float | None = None
    settle: SettleCorrection | None = field(default=None)
    settle_table: SettleTableRow | None = field(default=None)
    settle_table_status: str | None = None
    """None (no table given), "applied", "no_table_row" (run uncorrected) or "rigid_reference"."""
    plateau_rise_max_N: float | None = None
    """LOC plateau rise threshold of the soil response (U-S9-C2 sensitivity); None = preset."""
    fs_kN: float = FS_KN
    """Front seal friction F_s [kN] (rear 0.833 x); the study-1 groups use 4 kN."""
    mass_scale: float = 1.0
    """Spec 422 (decision Q-B): plant superstructure mass / inertia factor (controller unchanged)."""
    start_gap: tuple[str, str, float] | None = None
    """Spec 426.6 (H8): (leg, "gap" | "delta", mm) = zero-stroke start gap of one pad after the
    settle (``s9_soil_closed_loop`` key ``pad_start_gap``); None = the settle gap (no change)."""

    @property
    def case_id(self) -> str:
        """``group|soil|pad|level|slope``; ``|Fs<f>`` when F_s is not 4 kN, ``|m<scale>`` when
        the mass is scaled and ``|<leg>:g<mm>`` / ``|<leg>:d<mm>`` with a start gap (the ids of
        the H1 .. H6 cases are unchanged)."""
        case_id = f"{self.group}|{self.soil}|{self.pad}|{self.level}|{self.slope_name}"
        if self.fs_kN != FS_KN:
            case_id += f"|Fs{self.fs_kN:g}"
        if self.mass_scale != 1.0:
            case_id += f"|m{self.mass_scale:g}"
        if self.start_gap is not None:
            leg, kind, value_mm = self.start_gap
            case_id += f"|{leg}:{START_GAP_ID_LETTER[kind]}{value_mm:g}"
        return case_id

    @property
    def settle_key(self) -> str:
        """Key of the settle-correction table: soil|pad|level|roll,pitch (deg, %g)."""
        return f"{self.soil}|{self.pad}|{self.level}|{self.roll_deg:g},{self.pitch_deg:g}"

    @property
    def harness_settle_key(self) -> str:
        """Key of the dynamics settle table: soil|level|roll|pitch (deg, %g); no pad (the pads
        are off the ground in the settle, A and B give the same row)."""
        return f"{self.soil}|{self.level}|{self.roll_deg:g}|{self.pitch_deg:g}"

    def to_dict(self) -> dict:
        out = asdict(self)
        if self.start_gap is None:  # the dicts of the cases before spec 426 keep their keys
            del out["start_gap"]
        out["id"] = self.case_id
        out["settle_key"] = self.settle_key
        out["harness_settle_key"] = self.harness_settle_key
        return out


def _scaled_slope(direction: str, k: float) -> tuple[float, float]:
    roll, pitch = SLOPES_DEG[direction]
    return round(k * roll, 4), round(k * pitch, 4)


def _grid_cases(group: str, soils, pads, level: str) -> list[SlopeCase]:
    cases = []
    for soil in soils:
        for pad in pads:
            for name, (roll, pitch) in SLOPES_DEG.items():
                cases.append(SlopeCase(group, soil, pad, level, name, roll, pitch))
    return cases


def _boundary_cases() -> list[SlopeCase]:
    cases = []
    for soil in BOUNDARY_SOILS:
        for pad in PADS:
            for direction in BOUNDARY_DIRECTIONS:
                for k in BOUNDARY_K:
                    roll, pitch = _scaled_slope(direction, k)
                    name = f"{direction}@k{k:g}"
                    cases.append(SlopeCase("H3", soil, pad, LEVEL_TOP, name, roll, pitch,
                                           direction=direction, k=k))
    return cases


def _reanchor_cases() -> list[SlopeCase]:
    cases = []
    for soil in SOILS:
        for pad in PADS:
            for name, (roll, pitch) in REANCHOR_SLOPES_DEG.items():
                cases.append(SlopeCase("H4", soil, pad, LEVEL_TOP, name, roll, pitch,
                                       reanchor=True))
    for name, (roll, pitch) in REANCHOR_SLOPES_DEG.items():
        cases.append(SlopeCase("H4", RIGID, "B", LEVEL_TOP, name, roll, pitch, reanchor=True))
    for soil, pad, name in REANCHOR_EXTRA:
        roll, pitch = SLOPES_DEG[name]
        cases.append(SlopeCase("H4", soil, pad, LEVEL_TOP, name, roll, pitch, reanchor=True))
    return cases


H6_BLOCKS = (
    # (soil, pad, levels, F_s [kN], mass scales): spec 422.3, flat floor
    ("J1", "B", (LEVEL_TOP, LEVEL_MIDDLE, LEVEL_BOTTOM), (0.0, 4.0), (1.0, 1.1, 1.2)),
    ("J1", "A", (LEVEL_TOP, LEVEL_BOTTOM), (4.0,), (1.0, 1.1, 1.2)),
    ("J2", "B", (LEVEL_TOP, LEVEL_BOTTOM), (4.0,), (1.0, 1.1)),
    ("G1", "B", (LEVEL_TOP, LEVEL_BOTTOM), (4.0,), (1.2,)),
    (RIGID, "B", (LEVEL_TOP,), (0.0, 4.0), (1.2,)),
)
"""Spec 422.3 (decision Q-B): J1 B operating-weight sensitivity, 18 + 6 + 4 + 2 + 2 = 32 runs."""


def _mass_scale_cases() -> list[SlopeCase]:
    cases = []
    for soil, pad, levels, fs_values, scales in H6_BLOCKS:
        for level in levels:
            for fs_kN in fs_values:
                for scale in scales:
                    cases.append(SlopeCase("H6", soil, pad, level, "flat", 0.0, 0.0,
                                           fs_kN=fs_kN, mass_scale=scale))
    return cases


def _start_gap_cases() -> list[SlopeCase]:
    """Spec 426.6 (study D): pad B, top, F_s 4, flat; per soil the reference (no start gap) and
    leg FL / RR x the five start gaps."""
    cases = []
    for soil in H8_SOILS:
        cases.append(SlopeCase(H8_GROUP, soil, "B", LEVEL_TOP, "flat", 0.0, 0.0))
        for leg in H8_LEGS:
            for kind, value_mm in H8_START_GAPS:
                cases.append(SlopeCase(H8_GROUP, soil, "B", LEVEL_TOP, "flat", 0.0, 0.0,
                                       start_gap=(leg, kind, value_mm)))
    return cases


def pad_start_gap_spec(start_gap) -> dict:
    """``s9_soil_closed_loop`` key ``pad_start_gap`` of a case start gap (leg, kind, mm)."""
    leg, kind, value_mm = start_gap
    unit_key = {START_GAP_GAP: "gap_m", START_GAP_DELTA: "delta_m"}[kind]
    return {"leg": leg, unit_key: float(value_mm) * 1e-3}


def build_cases(groups=tuple(GROUP_SIZES)) -> list[SlopeCase]:
    """All cases of the named groups (default H1..H5 = 177; H6 = spec 422 and H8 = spec 426.6
    only on request), in group order."""
    builders = {
        "H1": lambda: _grid_cases("H1", SOILS, PADS, LEVEL_TOP),
        "H2": lambda: _grid_cases("H2", SOILS, ("B",), LEVEL_BOTTOM),
        "H3": _boundary_cases,
        "H4": _reanchor_cases,
        "H5": lambda: _grid_cases("H5", (RIGID,), ("B",), LEVEL_TOP),
        "H6": _mass_scale_cases,
        H8_GROUP: _start_gap_cases,
    }
    unknown = [g for g in groups if g not in builders]
    if unknown:
        raise ValueError(f"unknown case groups {unknown}, expected {list(builders)}")
    cases: list[SlopeCase] = []
    for group in groups:
        cases += builders[group]()
    return cases


def attach_settle_corrections(cases: list[SlopeCase], table: dict) -> list[SlopeCase]:
    """Attach the A1 settle corrections of ``table`` ({settle_key: {dz_m, droll_deg,
    dpitch_deg}}) to the matching cases.

    Raises:
        ValueError: a table key matches no case, or a non-zero correction hits a rigid case.
    """
    known = {case.settle_key for case in cases}
    unknown = sorted(set(table) - known)
    if unknown:
        raise ValueError(f"settle corrections for unknown cases: {unknown[:5]}")
    out = []
    for case in cases:
        entry = table.get(case.settle_key)
        if entry is None:
            out.append(case)
            continue
        correction = SettleCorrection(**entry)
        if case.soil == RIGID and not correction.is_zero:
            raise ValueError(f"settle correction on a rigid floor: {case.settle_key}")
        out.append(replace(case, settle=correction))
    return out


def attach_settle_table(cases: list[SlopeCase], rows: dict) -> list[SlopeCase]:
    """Attach the dynamics settle-table rows ({harness_settle_key: row}) to every soil case.

    Soil cases without a row run uncorrected and say so (``settle_table_status`` "no_table_row").
    Rigid cases are the reference of the table: a rigid row must be all zero.

    Raises:
        ValueError: a case also carries a ``SettleCorrection``, or a rigid row is not zero.
    """
    out = []
    for case in cases:
        row = rows.get(case.harness_settle_key)
        if case.settle is not None:
            raise ValueError(f"{case.case_id}: settle correction and settle table both given")
        if case.soil == RIGID:
            if row is not None and not SettleTableRow.from_table(row).is_zero:
                raise ValueError(
                    f"settle table has a non-zero rigid row: {case.harness_settle_key}")
            out.append(replace(case, settle_table_status="rigid_reference"))
        elif row is None:
            out.append(replace(case, settle_table_status="no_table_row"))
        else:
            out.append(replace(case, settle_table=SettleTableRow.from_table(row),
                               settle_table_status="applied"))
    return out


def run_case_input(case: dict) -> dict:
    """The ``s9_soil_closed_loop.run_case`` dict of one case."""
    run_input = {
        "id": case["id"], "soil": case["soil"], "pad": case["pad"], "level": case["level"],
        "fs_kN": case.get("fs_kN", FS_KN), "slope": (case["roll_deg"], case["pitch_deg"]),
        "variant": {"reanchor": bool(case["reanchor"])}, "trace": False,
    }
    if case.get("mass_scale", 1.0) != 1.0:  # spec 422: only scaled cases carry the key
        run_input["mass_scale"] = float(case["mass_scale"])
    if case.get("start_gap") is not None:  # spec 426.6: only start-gap cases carry the key
        run_input["pad_start_gap"] = pad_start_gap_spec(case["start_gap"])
    return run_input


# ------------------------------------------------------------------------------- judgement
def _events_named(events, prefix: str) -> list[tuple[float, str]]:
    return [(t, name) for t, name in events if name.startswith(prefix)]


def _first_time(events, prefix: str) -> float | None:
    hits = _events_named(events, prefix)
    return hits[0][0] if hits else None


def _has_fault(run: dict, events) -> bool:
    return run.get("final_phase") in FAULT_PHASES or bool(_events_named(events, "FAULT"))


def _log_window(log: dict, t_start: float, t_end: float) -> np.ndarray:
    t = np.asarray(log["t_s"], float)
    return (t >= t_start - TIME_MATCH_S) & (t <= t_end + TIME_MATCH_S)


def _level_mask(log: dict) -> np.ndarray:
    return np.array([phase not in PRE_LEVEL_PHASES for phase in log["phase"]], bool)


def _is_flat(case: dict) -> bool:
    return case["roll_deg"] == 0.0 and case["pitch_deg"] == 0.0


def ready_limit_s(case: dict) -> float:
    """P3-6 READY limit (spec 421.1, first matching row): slope 120 s; flat with pad B on a
    J1 / J2 / S1 soil (uniform: both rear pads soft) 100 s; any other flat case 90 s."""
    if not _is_flat(case):
        return READY_SLOPE_MAX_S
    if case["pad"] == "B" and case["soil"] in SOFT_SOILS:
        return READY_SOFT_PAD_B_MAX_S
    return READY_FLAT_MAX_S


def _preloc_rows(rec: dict, t_loc: float | None, has_fault: bool) -> dict:
    """P3-8 with the spec 377 demotion of pre-LOC re-approach starts."""
    events, log, f_min = rec["events"], rec["log"], rec["F_min_kN"]
    before_loc = [(t, n) for t, n in events if t_loc is None or t < t_loc]
    pre_loc = [n for _, n in before_loc if n.startswith(("leg_reapproach_start", "probe_aborted"))]
    t_end = (t_loc if t_loc is not None else log["t_s"][-1]) + PRELOC_WINDOW_AFTER_LOC_S
    fmin = np.asarray(log["fmin_kN"], float)
    starts = []
    for t, name in _events_named(before_loc, "leg_reapproach_start"):
        leg = LEGS.index(name.split(":")[1])
        mask = _log_window(log, t - PRELOC_WINDOW_BEFORE_START_S, t_end)
        true_min = float(fmin[mask, leg].min()) if mask.any() else None
        starts.append({"t_s": round(t, 2), "leg": LEGS[leg], "true_min_kN": true_min})
    is_demoted = (bool(starts) and len(starts) == len(pre_loc) and not has_fault
                  and all(s["true_min_kN"] is not None and s["true_min_kN"] >= f_min
                          for s in starts))
    return {"pass": not pre_loc or is_demoted, "flag": is_demoted, "events": pre_loc[:6],
            "starts": starts}


def _crawler_row(rec: dict, t_loc: float | None, t_ready: float | None) -> dict:
    """P3-1 (spec 420.2b, U-S9-G6d (가) + 423.3 Q-G): crawler load 0 after READY, READY reached,
    and no ``strict_fail`` recontact after the departure confirmation (run_S9
    ``recontact_events`` on the 1 ms crawler force); ``transient_flag`` / ``threshold_chatter``
    recontacts pass with the FLAGs ``P3-1_transient_recontact`` / ``P3-1_threshold_chatter``.
    Records without the 1 ms series keep the old rule (no recontact after the first
    crawler-free period)."""
    run = rec["run"]
    recontact = late_loc_rule.crawler_recontact_record(rec.get("crawler_series"),
                                                       rec.get("weight_N"), t_loc, t_ready)
    is_crawler_ok, flags = late_loc_rule.crawler_gate(
        run.get("crawler_N_max_after_ready") == 0.0, recontact, run.get("n_crawler_recontact", 1))
    is_pass = bool(is_crawler_ok and t_ready is not None)
    events = None if recontact is None else recontact["recontact_events"]
    return {"pass": is_pass, "flag": bool(is_pass and flags),
            "flag_name": flags[0] if is_pass and flags else None,
            "flag_names": flags if is_pass else [],
            "crawler_N_max_after_ready": run.get("crawler_N_max_after_ready"),
            "n_recontact": run.get("n_crawler_recontact"),
            "recontact_events": events,
            "departure": None if recontact is None else recontact["departure"]}


def _revoked_loc_block(rec: dict, timeline: dict, late_loc: dict, t_done: float | None,
                       t_off: float | None, min_off_kN: float | None, has_fault: bool) -> dict:
    """Spec 424.8.1 FLAG record ``late_loc_revoked`` at t_LOC^fin (runs with a revocation)."""
    t_loc = timeline["t_loc_final_s"]
    conditions = late_loc.get("conditions") or {}
    return late_loc_rule.late_loc_revoked(
        t_off_s=t_off, t_loc_final_s=t_loc, t_done_s=t_done,
        revoke_times_s=timeline["revoke_times_s"],
        crawler_loc_period_max_N=late_loc_rule.loc_period_crawler_max_N(
            rec.get("crawler_series") or [], t_loc),
        weight_N=rec.get("weight_N"), min_force_after_off_kN=min_off_kN,
        f_min_kN=rec["F_min_kN"], has_fault=has_fault,
        reapproach_restart=bool(conditions.get("1_restart")),
        t_reapproach_end_s=late_loc.get("t_reapproach_end_s"))


def _loc_row(rec: dict, timeline: dict, t_done: float | None, t_off: float | None,
             min_off_kN: float | None, has_fault: bool) -> dict:
    """P3-2 on t_LOC^fin (spec 424.8.1) with the FLAGs of a late LOC: spec 419.8 (LWa window
    restart) and spec 424.8.1 (LOC revoked); both are recorded when both hold. A run without a
    revocation gives the former row bit for bit."""
    t_loc = timeline["t_loc_final_s"]
    t_revoke_last = timeline["t_revoke_last_s"]
    loc_delay = None if t_loc is None or t_off is None else t_loc - t_off
    is_raw_pass = bool(t_loc is not None and (t_done is None or t_loc <= t_done + 1e-9)
                       and loc_delay is not None and loc_delay <= LOC_DELAY_MAX_S + 1e-9)
    log = rec["log"]
    phases = list(zip(log["t_s"], log["phase"], strict=True))
    if has_fault:  # a FAULT the phase log missed (run status) still counts (419.8.1 (4))
        phases.append((math.inf, "fault"))
    # records without the 1 ms crawler series (older / synthetic) cannot show condition 3: no flag
    late_loc = late_loc_rule.late_loc_reapproach(
        rec["events"], phases, rec.get("crawler_series") or [], rec.get("weight_N"),
        t_off_s=t_off, t_loc_s=t_loc, t_done_s=t_done, min_force_after_off_kN=min_off_kN,
        f_min_kN=rec["F_min_kN"], t_revoke_last_s=t_revoke_last)
    flag_names = [late_loc_rule.P32_FLAG] if late_loc["is_flag"] else []
    revoked = None
    if timeline["revoke_times_s"]:
        revoked = _revoked_loc_block(rec, timeline, late_loc, t_done, t_off, min_off_kN,
                                     has_fault)
        if revoked["is_flag"]:
            flag_names.append(late_loc_rule.P32_REVOKED_FLAG)
    is_flag = not is_raw_pass and bool(flag_names)
    row = {"pass": is_raw_pass or is_flag, "flag": is_flag,
           "flag_name": flag_names[0] if is_flag else None,
           "t_loc_s": t_loc, "t_off_s": t_off, "loc_delay_s": loc_delay,
           "late_loc_reapproach": late_loc}
    if revoked is not None:  # spec 424.8.1 records (only with a revocation)
        row.update(flag_names=flag_names if is_flag else [], late_loc_revoked=revoked,
                   t_loc_first_s=timeline["t_loc_first_s"], t_loc_final_s=t_loc,
                   loc_revokes=timeline["revoke_times_s"])
    return row


def p3_rows(rec: dict) -> dict:
    """P3-1 .. P3-8 of one run (harness form, as the r72 G6 screen). P3-1 and P3-2 use the
    judged LOC t_LOC^fin (spec 424.8.1: the last confirmed one after a LOC revocation; without
    one the first LOC event as before)."""
    run, events, case, f_min = rec["run"], rec["events"], rec["case"], rec["F_min_kN"]
    timeline = late_loc_rule.loc_timeline(events)
    t_loc = timeline["t_loc_final_s"]
    t_done = run.get("t_done_s")
    t_off = run.get("t_crawler_off_first_s")
    t_ready = run.get("t_ready_s")
    has_fault = _has_fault(run, events)
    min_off = run.get("min_true_Fcyl_after_off_kN")
    att_end = run.get("att_end_deg") or [math.nan, math.nan]
    # records without "rut_ready_mm" (synthetic / older) fall back to the harness READY value
    rut_ready = rec.get("rut_ready_mm", run.get("clear_true_ready_mm"))
    rut_end = rec.get("rut_end_mm")
    ready_limit = ready_limit_s(case)
    return {
        "P3-1": _crawler_row(rec, t_loc, t_ready),
        "P3-2": _loc_row(rec, timeline, t_done, t_off, min_off, has_fault),
        "P3-3": {"pass": bool(min_off is not None and min_off >= f_min),
                 "min_true_Fcyl_after_off_kN": min_off,
                 "D8_margin_kN": None if min_off is None else min_off - f_min - D8_MARGIN_KN},
        "P3-4": {"pass": bool(np.all(np.abs(att_end) <= ATTITUDE_TOL_DEG)), "att_end_deg": att_end},
        "P3-5": {"pass": bool((rut_ready if rut_ready is not None else -1.0) >= RUT_MIN_MM
                              and (rut_end is None or rut_end >= RUT_MIN_MM)
                              and run.get("max_motor_stroke_mm", math.inf) <= STROKE_OK_MM),
                 "rut_ready_mm": rut_ready, "rut_end_mm": rut_end,
                 "max_motor_stroke_mm": run.get("max_motor_stroke_mm")},
        "P3-6": {"kind": "record", "t_ready_s": t_ready, "limit_s": ready_limit,
                 "flag": t_ready is None or t_ready > ready_limit},
        "P3-7": {"kind": "record", "value": None, "note": "not computed by the reduced harness"},
        # spec 424.8.1 names P3-1 / P3-2 / P3-7 only: P3-8 keeps the first LOC
        "P3-8": _preloc_rows(rec, timeline["t_loc_first_s"], has_fault),
        "fault_ready": {"pass": not has_fault and t_ready is not None, "has_fault": has_fault,
                        "final_phase": run.get("final_phase")},
    }


def _lifted_legs(rec: dict) -> list[str]:
    """Legs whose pad contact force (true F_cyl + rod weight) reached 0 after the LEVEL start."""
    log = rec["log"]
    contact = np.asarray(log["fmin_kN"], float) + np.asarray(rec["rod_weight_kN"], float)
    level = _level_mask(log)
    if not level.any():
        return []
    return [LEGS[i] for i in range(4) if contact[level, i].min() <= 0.0]


def _min_true_force_kN(rec: dict) -> float | None:
    """Min true F_cyl after the crawler lift-off, or after the LEVEL start without a lift-off."""
    after_off = rec["run"].get("min_true_Fcyl_after_off_kN")
    if after_off is not None:
        return after_off
    level = _level_mask(rec["log"])
    if not level.any():
        return None
    return float(np.asarray(rec["log"]["fmin_kN"], float)[level].min())


def stroke_row(rec: dict) -> dict:
    """SL-1 stroke gate and the "stroke limited" class (user decision 2026-10-28)."""
    run, events, case = rec["run"], rec["events"], rec["case"]
    stroke_faults = [n for _, n in events if n.startswith(STROKE_FAULT_EVENTS)]
    is_guarded = bool(_events_named(events, STROKE_GUARD_WARNING))
    max_stroke = run.get("max_motor_stroke_mm", math.inf)
    lifted = _lifted_legs(rec)
    min_force = _min_true_force_kN(rec)
    row = {"pass": not stroke_faults and max_stroke <= STROKE_OK_MM,
           "stroke_faults": stroke_faults, "max_motor_stroke_mm": max_stroke,
           "guard_warning": is_guarded, "lifted_legs": lifted, "min_true_Fcyl_kN": min_force,
           "att_end_deg": run.get("att_end_deg"), "rut_end_mm": rec.get("rut_end_mm")}
    prediction = _k_prediction_difference(case)
    if prediction is not None:
        row["k_minus_prediction"] = prediction
    return row


def _k_prediction_difference(case: dict) -> float | None:
    """Slope ratio of an H1 / H3 boundary-direction case minus the additive prediction."""
    prior = PRIOR_K_PREDICTION.get((case["soil"], case["pad"]), {})
    if case["group"] == "H3":
        direction, k = case["direction"], case["k"]
    elif case["group"] == "H1":
        direction, k = case["slope_name"], 1.0
    else:
        return None
    return None if direction not in prior else k - prior[direction]


def start_condition_row(rec: dict) -> dict:
    """SL-2: operating start rule on the crawler settle attitude (controller reading first)."""
    settle = rec["settle"]
    att = settle.get("att_ctrl_deg") or settle["att_true_deg"]
    ratio = abs(att[0]) / START_ROLL_LIMIT_DEG + abs(att[1]) / START_PITCH_LIMIT_DEG
    return {"kind": "record", "R_c": ratio, "att_deg": att, "source":
            "controller" if settle.get("att_ctrl_deg") else "plant",
            "flag": ratio > 1.0, "note": "operating rule rejects the start" if ratio > 1.0 else ""}


def _row_after(log: dict, t_s: float) -> int | None:
    t = np.asarray(log["t_s"], float)
    later = np.nonzero(t > t_s + TIME_MATCH_S)[0]
    return int(later[0]) if later.size else None


def _row_at(log: dict, t_s: float) -> int | None:
    t = np.asarray(log["t_s"], float)
    if t.size == 0:
        return None
    index = int(np.argmin(np.abs(t - t_s)))
    return index if abs(t[index] - t_s) <= 0.05 + TIME_MATCH_S else None


def clearance_row(rec: dict) -> dict:
    """SL-3: LOC clearance bias and the true clearance at the LOC."""
    soil, log = rec["soil_state"], rec["log"]
    t_loc = _first_time(rec["events"], LOC_EVENT)
    row = {"kind": "record", "t_P_s": soil.get("t_P_s"), "c_min_tP_mm": soil.get("c_min_tP_mm"),
           "corner_bias_mm": soil.get("corner_bias_mm"),
           "anchor_applied": bool(soil.get("anchor_applied"))
           or bool(_events_named(rec["events"], LOC_ANCHOR_EVENT)),
           "true_at_loc_mm": None, "estimate_after_loc_mm": None, "true_minus_estimate_mm": None,
           "flag": False}
    if t_loc is None:
        return row
    at, after = _row_at(log, t_loc), _row_after(log, t_loc)
    if at is None or after is None:
        return row
    true_mm = log["rut_clear_mm"][at]
    estimate_mm = log["clear_est_mm"][after]
    if true_mm is None or estimate_mm is None:
        return row
    row.update(true_at_loc_mm=true_mm, estimate_after_loc_mm=estimate_mm,
               true_minus_estimate_mm=true_mm - estimate_mm,
               flag=true_mm < estimate_mm - UNDER_LIFT_MM)
    return row


def downhill_minus_uphill(values, pad_xy, roll_deg: float, pitch_deg: float) -> float | None:
    """Mean of the two downhill pads minus mean of the two uphill pads (None on a flat floor).

    Floor height of pad i: -x_i tan(pitch) + y_i tan(roll) (pitch > 0 nose down, roll > 0 left
    side up)."""
    if roll_deg == 0.0 and pitch_deg == 0.0:
        return None
    xy = np.asarray(pad_xy, float)
    height = -xy[:, 0] * math.tan(math.radians(pitch_deg)) + xy[:, 1] * math.tan(
        math.radians(roll_deg))
    order = np.argsort(height)
    vals = np.asarray(values, float)
    return float(vals[order[:2]].mean() - vals[order[2:]].mean())


def sink_row(rec: dict) -> dict:
    """SL-4: sink asymmetry and the crawler settle tilt (A1 flag)."""
    case, run, settle = rec["case"], rec["run"], rec["settle"]
    sink = run.get("sink_final_mm")
    asym = None if sink is None else downhill_minus_uphill(sink, rec["pad_xy"], case["roll_deg"],
                                                           case["pitch_deg"])
    return {"kind": "record", "sink_final_mm": sink, "downhill_minus_uphill_mm": asym,
            "settle_att_true_deg": settle["att_true_deg"],
            "settle_correction": case.get("settle"), "A1": approximation_flags(case)["A1"]}


def reanchor_rows(rec: dict) -> dict | None:
    """RA-1 .. RA-6 of a REANCHOR-on run (None for the others)."""
    case, events, log, f_min = rec["case"], rec["events"], rec["log"], rec["F_min_kN"]
    if not case["reanchor"]:
        return None
    started = _events_named(events, "reanchor_started")
    skipped = [n.split(":", 1)[1] for _, n in _events_named(events, "reanchor_skipped")]
    aborted = [n.split(":", 1)[1] for _, n in _events_named(events, "reanchor_aborted")]
    anchor = rec["settle"].get("anchor_pitch_deg")
    ra1_ok = not started or (anchor is not None and anchor >= REANCHOR_THETA_MIN_DEG - 1e-9)
    rows = {"RA-1": {"pass": ra1_ok, "started": bool(started), "anchor_pitch_deg": anchor,
                     "skip_reasons": skipped,
                     "completed": bool(_events_named(events, "reanchor_completed"))},
            "RA-5": {"kind": "record", "value": None, "note": "Chrono only"},
            "RA-6": {"kind": "record", "n_stroke_cap_aborts": aborted.count("stroke_cap")}}
    if not started:
        rows["RA-2"] = {"pass": None, "note": "no REANCHOR"}
        rows["RA-3"] = {"pass": None, "note": "no REANCHOR"}
        rows["RA-4"] = {"kind": "record", "value": None}
        return rows
    t_start = started[0][0]
    in_reanchor = [t for t, phase in zip(log["t_s"], log["phase"], strict=True)
                   if phase == "reanchor"]
    t_end = (max(in_reanchor) if in_reanchor else t_start) + REANCHOR_WINDOW_TAIL_S
    window = _log_window(log, t_start, t_end)
    fmin = np.asarray(log["fmin_kN"], float)[window]
    min_force = float(fmin.min()) if fmin.size else None
    att_end = rec["run"].get("att_end_deg") or [math.nan, math.nan]
    rows["RA-2"] = {"pass": min_force is not None and min_force >= f_min + D8_MARGIN_KN,
                    "min_true_Fcyl_kN": min_force, "window_s": [t_start, t_end]}
    rows["RA-3"] = {"pass": bool(np.all(np.abs(att_end) <= ATTITUDE_TOL_DEG)),
                    "n_attitude_aborts": sum(1 for a in aborted if a.startswith("attitude")),
                    "n_relevel_after": sum(1 for t, n in events if t >= t_start and "relevel" in n),
                    "aborts": aborted, "att_end_deg": att_end}
    rows["RA-4"] = {"kind": "record", "sink_increase_mm": _non_target_sink_increase(log, window)}
    return rows


def _non_target_sink_increase(log: dict, window: np.ndarray) -> dict | None:
    sink = log.get("sink_mm")
    if sink is None or not window.any():
        return None
    rows = np.asarray(sink, float)[window]
    return {LEGS[i]: float(rows[-1, i] - rows[0, i]) for i in range(4)
            if LEGS[i] not in REANCHOR_TARGET_LEGS}


def approximation_flags(case: dict) -> dict:
    """A1..A3 notes of one case; A1 says whether a settle correction was applied."""
    flags = dict(APPROXIMATION_NOTES)
    status = case.get("settle_table_status")
    if case["soil"] == RIGID:
        flags["A1"] = "rigid floor: no soil settle"
    elif status == "applied":
        flags["A1"] = "settle table hook_harness applied (slope settle, flat P0 bias corrected)"
    elif status == "no_table_row":
        flags["A1"] = APPROXIMATION_NOTES["A1"] + " - not corrected (no settle-table row)"
    elif case.get("settle"):
        flags["A1"] = f"settle corrected (dz/droll/dpitch): {case['settle']}"
    else:
        flags["A1"] = APPROXIMATION_NOTES["A1"] + " - not corrected"
    return flags


def settle_check(target_q_floor, gap_target_mm, settle_q_floor_rad, pen_mm) -> dict:
    """Post-settle check of a settle-table case: pad penetration of the original soil surface
    within 1 mm of -gap_target and the settle attitude in the original-floor axes within
    0.005 deg of the table target (phi, theta)."""
    pen_error = np.asarray(pen_mm, float) + np.asarray(gap_target_mm, float)
    attitude_error = np.degrees(np.asarray(settle_q_floor_rad, float)
                                - np.asarray(target_q_floor[1:3], float))
    is_gap_ok = bool(np.all(np.abs(pen_error) <= SETTLE_GAP_TOL_MM))
    is_attitude_ok = bool(np.all(np.abs(attitude_error) <= SETTLE_ATTITUDE_TOL_DEG))
    return {"ok": is_gap_ok and is_attitude_ok, "gap_ok": is_gap_ok,
            "attitude_ok": is_attitude_ok, "pen_plus_gap_mm": pen_error.tolist(),
            "attitude_error_deg": attitude_error.tolist()}


def is_stroke_limited_pass(p3: dict, stroke: dict) -> bool:
    """"Stroke limited" pass (user decision 2026-10-28, corrected after the rev. 78 run): FAULT 0,
    no leg lift and P3-1 (crawler 0 after READY, no re-contact), P3-3 and P3-4 all pass; only P3-5
    (rut clearance 25 mm) is relaxed. The first form let crawler re-contact / burden through."""
    return bool(not p3["fault_ready"]["has_fault"] and not stroke["lifted_legs"]
                and all(p3[row]["pass"] for row in STROKE_LIMITED_REQUIRED_ROWS))


def classify(p3: dict, stroke: dict, reanchor: dict | None) -> str:
    """Run verdict: stroke-limited class first (user decision), then every judged row."""
    if stroke["stroke_faults"]:
        return VERDICT_FAIL
    if stroke["guard_warning"]:
        stroke["stroke_limited_pass"] = is_stroke_limited_pass(p3, stroke)
        return (VERDICT_STROKE_LIMITED_PASS if stroke["stroke_limited_pass"]
                else VERDICT_STROKE_LIMITED_FAIL)
    judged = [row["pass"] for row in p3.values() if "pass" in row]
    judged.append(stroke["pass"])
    if reanchor is not None:
        judged += [row["pass"] for row in reanchor.values() if row.get("pass") is not None]
    return VERDICT_PASS if all(judged) else VERDICT_FAIL


def judge_case(rec: dict) -> dict:
    """All judgement rows and the verdict of one collected run record."""
    p3 = p3_rows(rec)
    stroke = stroke_row(rec)
    reanchor = reanchor_rows(rec)
    rows = {**p3, "SL-1": stroke, "SL-2": start_condition_row(rec), "SL-3": clearance_row(rec),
            "SL-4": sink_row(rec)}
    if reanchor is not None:
        rows.update(reanchor)
    verdict = classify(p3, stroke, reanchor)
    mass_scale = rec["case"].get("mass_scale", 1.0)
    return {"rows": rows,
            "verdict": _final_verdict(verdict, rec["settle"].get("check"), mass_scale),
            "verdict_rows": verdict,
            "failed_rows": sorted(k for k, v in rows.items() if v.get("pass") is False)}


def _final_verdict(verdict_rows: str, settle_check: dict | None, mass_scale: float = 1.0) -> str:
    if mass_scale != 1.0:
        # spec 422.2: the table settle is the nominal-weight one; a scaled plant sinks the crawler
        # springs further (about 1.6 mm, 0.03 deg at 1.2), so the check is a record only
        return verdict_rows
    if settle_check is not None and not settle_check["ok"]:
        # the start state is not the tabled settle: the run is not judged (rows kept)
        return VERDICT_SETTLE_CHECK_FAIL
    return verdict_rows


def rejudge_stored(result: dict) -> dict:
    """Verdict of a stored result recomputed from its rows with the current rules (``--from-json``).

    The rows are kept as stored: their rut clearance keeps the definition of the run that wrote
    them (``rut_definition``; results without the key used the settle-contact nodes)."""
    if "error" in result:
        return result
    rows = result["rows"]
    p3 = {k: v for k, v in rows.items() if k.startswith("P3-") or k == "fault_ready"}
    reanchor = {k: v for k, v in rows.items() if k.startswith("RA-")} or None
    stroke = dict(rows["SL-1"])  # classify writes stroke_limited_pass into it
    verdict = classify(p3, stroke, reanchor)
    check = (result.get("settle") or {}).get("check")
    return {**result, "rows": {**rows, "SL-1": stroke}, "verdict_stored": result["verdict"],
            "verdict_rows": verdict,
            "verdict": _final_verdict(verdict, check,
                                      (result.get("case") or {}).get("mass_scale", 1.0)),
            "rut_definition": result.get("rut_definition", RUT_DEFINITION_OLD)}


def _leg_touch_record(log: dict, leg: int, contact_kN: np.ndarray, t_touch_start: float) -> dict:
    """First contact, latch and the stroke between them of one leg (10 Hz log).

    First contact = start of the first control period whose minimum pad contact force is > 0
    (contact held over a whole 0.1 s period; the r69 1 ms definition lies at most one period
    earlier). Latch = end of the first period with the leg latched (``touched``)."""
    t = np.asarray(log["t_s"], float)
    stroke = np.asarray(log["stroke_mm"], float)[:, leg]
    latched = np.nonzero(np.asarray(log["touched"], bool)[:, leg])[0]
    in_contact = np.nonzero(contact_kN[:, leg] > 0.0)[0]
    record = {"first_contact_s": None, "latch_s": None, "latch_rel_touch_s": None,
              "post_contact_stroke_mm": None, "latch_after_contact_s": None,
              "stroke_at_latch_mm": None}
    if latched.size:
        k_latch = int(latched[0])
        record.update(latch_s=round(float(t[k_latch]), 2),
                      latch_rel_touch_s=round(float(t[k_latch]) - t_touch_start, 2),
                      stroke_at_latch_mm=round(float(stroke[k_latch]), 1))
    if in_contact.size:
        k_contact = int(in_contact[0])
        k_start = max(k_contact - 1, 0)  # the previous period end = this period's start
        t_contact = float(t[k_contact]) - PERIOD_LOG_S
        record["first_contact_s"] = round(t_contact, 2)
        if latched.size:
            record["post_contact_stroke_mm"] = round(float(stroke[latched[0]] - stroke[k_start]), 1)
            record["latch_after_contact_s"] = round(float(t[latched[0]]) - t_contact, 2)
    return record


def _phase_segment_states(log: dict) -> list[dict]:
    """Phase runs with their length and the motor stroke and attitude at their end."""
    segments = []
    for phase, start, end in phase_segments(log):
        index = _row_at(log, end)
        segments.append({"phase": phase, "start_s": round(start, 2),
                         "duration_s": round(end - start + PERIOD_LOG_S, 2),
                         "stroke_end_mm": [round(v, 1) for v in log["stroke_mm"][index]],
                         "att_end_deg": [round(v, 4) for v in log["att_deg"][index]]})
    return segments


def touch_record(record: dict) -> dict | None:
    """Spec 426.6 TOUCH record of an H8 run (None for the other groups).

    FLAGs (r69 thresholds): T-3' stroke of the start-gap leg from its first contact to its latch
    > 40 mm, T-4 largest |roll| / |pitch| change from the TOUCH start > 1.0 deg (every run),
    T-2' latch later than 3.0 s after the first contact. Per leg values are kept for all four
    legs (the reference runs are the comparison)."""
    log = record["log"]
    if "touched" not in log:
        return None
    phases = np.array(log["phase"])
    is_touch = phases == "touch"
    start_gap = record["case"].get("start_gap")
    leg_k = None if start_gap is None else start_gap[0]
    out = {"leg_k": leg_k, "has_touch": bool(is_touch.any()), "flags": []}
    if not is_touch.any():
        return out
    t = np.asarray(log["t_s"], float)
    k0, k1 = (int(i) for i in np.nonzero(is_touch)[0][[0, -1]])
    contact = np.asarray(log["fmin_kN"], float) + np.asarray(record["rod_weight_kN"], float)
    att = np.asarray(log["att_deg"], float)
    att_change = np.abs(att[is_touch] - att[k0]).max(axis=0)
    legs = {LEGS[i]: _leg_touch_record(log, i, contact, float(t[k0])) for i in range(4)}
    out.update(start_s=round(float(t[k0]), 2), duration_s=round(float(t[k1] - t[k0]), 2),
               max_abs_att_change_deg=att_change.round(4).tolist(), legs=legs,
               segments=_phase_segment_states(log),
               clearance_end_mm={"true": record["rut_end_mm"],
                                 "controller_estimate": log["clear_est_mm"][-1],
                                 "true_minus_estimate": record["rut_end_mm"]
                                 - log["clear_est_mm"][-1]})
    if att_change.max() > TOUCH_FLAG_LIMITS["T4_deg"]:
        out["flags"].append("T-4")
    if leg_k is not None:
        leg = legs[leg_k]
        if (leg["post_contact_stroke_mm"] or 0.0) > TOUCH_FLAG_LIMITS["T3_mm"]:
            out["flags"].append("T-3'")
        if (leg["latch_after_contact_s"] or 0.0) > TOUCH_FLAG_LIMITS["T2_s"]:
            out["flags"].append("T-2'")
    return out


# --------------------------------------------------------------------------------- summary
def _is_feasible(result: dict) -> bool:
    rows = result["rows"]
    return (result["verdict"] == VERDICT_PASS and not rows["SL-1"]["guard_warning"]
            and rows["SL-1"]["max_motor_stroke_mm"] <= STROKE_GUARD_MM)


def _direction_points(results: list[dict], soil: str, pad: str, direction: str) -> list[dict]:
    """(k, feasible, stroke) points of one direction: H1 / H5 flat (k 0), H3 grid, H1 / H5 slope
    (k 1)."""
    points = []
    for res in results:
        case = res["case"]
        # an unjudged run leaves its grid point missing (k* incomplete)
        if res.get("verdict") in (None, VERDICT_ERROR, VERDICT_SETTLE_CHECK_FAIL):
            continue
        if case["soil"] != soil:
            continue
        if case["pad"] != pad or case["level"] != LEVEL_TOP or case["reanchor"]:
            continue
        is_grid = case["group"] in ("H1", "H5")
        if is_grid and case["slope_name"] == "flat":
            k = 0.0
        elif is_grid and case["slope_name"] == direction:
            k = 1.0
        elif case["group"] == "H3" and case["direction"] == direction:
            k = case["k"]
        else:
            continue
        points.append({"k": k, "feasible": _is_feasible(res), "verdict": res["verdict"],
                       "max_stroke_mm": res["rows"]["SL-1"]["max_motor_stroke_mm"]})
    return sorted(points, key=lambda p: p["k"])


def _stroke_interpolated_k(points: list[dict]) -> float | None:
    """k where the run-maximum motor stroke crosses the 682.8 mm guard (linear, None if not
    bracketed)."""
    for low, high in zip(points, points[1:], strict=False):
        s_low, s_high = low["max_stroke_mm"], high["max_stroke_mm"]
        if s_low <= STROKE_GUARD_MM < s_high:
            return low["k"] + (high["k"] - low["k"]) * (STROKE_GUARD_MM - s_low) / (s_high - s_low)
    return None


def _expected_k(soil: str) -> tuple[float, ...]:
    """Slope ratios of a complete direction: the H3 grid only on the boundary soils."""
    if soil in BOUNDARY_SOILS:
        return (0.0, *BOUNDARY_K, 1.0)
    return (0.0, 1.0)


def _largest_feasible_k(points: list[dict]) -> float | None:
    """Last k of the unbroken feasible run from k = 0 (None when k = 0 is not feasible)."""
    k_star = None
    for point in points:
        if not point["feasible"]:
            break
        k_star = point["k"]
    return k_star


def k_star_rows(results: list[dict]) -> list[dict]:
    """Largest feasible slope ratio per soil / pad / direction.

    ``k_star`` is None when a grid point is missing (``is_complete`` False, e.g. a filtered run)
    or when the flat run (k = 0) is not feasible."""
    rows = []
    for soil in (*SOILS, RIGID):
        for pad in (PADS if soil != RIGID else ("B",)):
            for direction in BOUNDARY_DIRECTIONS:
                points = _direction_points(results, soil, pad, direction)
                if not points:
                    continue
                expected = _expected_k(soil)
                is_complete = [p["k"] for p in points] == list(expected)
                k_star = _largest_feasible_k(points) if is_complete else None
                prediction = PRIOR_K_PREDICTION.get((soil, pad), {}).get(direction)
                rows.append({"soil": soil, "pad": pad, "direction": direction,
                             "is_complete": is_complete, "k_star": k_star,
                             "k_stroke_interp": _stroke_interpolated_k(points),
                             "k_prediction": prediction,
                             "k_star_minus_prediction": None if k_star is None
                             or prediction is None else k_star - prediction,
                             "points": points})
    return rows


def case_table_row(result: dict) -> dict:
    case = result["case"]
    if "error" in result:
        return {"id": case["id"], "verdict": VERDICT_ERROR, "error": result["error"]}
    rows = result["rows"]
    warnings = sorted({n.split(":")[0] for n in result["warnings"] if n.startswith("WARN")})
    faults = sorted({n.split(":")[0] for n in result["warnings"] if n.startswith("FAULT")})
    return {"id": case["id"], "group": case["group"], "soil": case["soil"], "pad": case["pad"],
            "level": case["level"], "roll_deg": case["roll_deg"], "pitch_deg": case["pitch_deg"],
            "reanchor": case["reanchor"], "verdict": result["verdict"],
            "failed_rows": ",".join(result["failed_rows"]),
            "max_stroke_mm": rows["SL-1"]["max_motor_stroke_mm"], "faults": ",".join(faults),
            "warnings": ",".join(warnings), "lifted_legs": ",".join(rows["SL-1"]["lifted_legs"]),
            "min_Fcyl_kN": rows["SL-1"]["min_true_Fcyl_kN"],
            "att_end_roll_deg": rows["P3-4"]["att_end_deg"][0],
            "att_end_pitch_deg": rows["P3-4"]["att_end_deg"][1],
            "t_ready_s": rows["P3-6"]["t_ready_s"], "R_c": rows["SL-2"]["R_c"],
            "under_lift": rows["SL-3"]["flag"], "A1": rows["SL-4"]["A1"],
            "rut_ready_mm": rows["P3-5"]["rut_ready_mm"], "rut_end_mm": rows["P3-5"]["rut_end_mm"],
            "rut_definition": result.get("rut_definition", RUT_DEFINITION_OLD),
            "verdict_stored": result.get("verdict_stored"),
            **_settle_columns(result), "wall_s": result.get("wall_s")}


def _settle_columns(result: dict) -> dict:
    """Settle-table status, check and settle geometry columns of the case table."""
    settle, case = result.get("settle", {}), result["case"]
    check = settle.get("check")
    pen = settle.get("pen_mm")
    q_floor = settle.get("q_floor_deg") or [None, None]
    return {"verdict_rows": result.get("verdict_rows", result["verdict"]),
            "settle_table": case.get("settle_table_status"),
            "settle_check_ok": None if check is None else check["ok"],
            "settle_pitch_floor_deg": q_floor[1],
            "front_gap_mm": None if pen is None else -0.5 * (pen[0] + pen[1]),
            "first_contact_s": ",".join("" if t is None else f"{t:.1f}"
                                        for t in settle.get("first_contact_s") or [])}


def summarize(results: list[dict]) -> dict:
    table = [case_table_row(r) for r in results]
    counts: dict[str, int] = {}
    for row in table:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    return {"counts": counts, "k_star": k_star_rows([r for r in results if "error" not in r]),
            "cases": table}


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(out_path: Path, results: list[dict], meta: dict) -> dict:
    """Results JSON plus the case and k* CSV tables next to it."""
    summary = summarize(results)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"meta": meta, "summary": {k: v for k, v in summary.items() if k != "cases"},
               "cases_table": summary["cases"], "results": results}
    out_path.write_text(json.dumps(payload, indent=1, default=float), encoding="utf-8")
    _write_csv(out_path.with_name(out_path.stem + "_cases.csv"), summary["cases"])
    k_rows = [{k: v for k, v in row.items() if k != "points"} for row in summary["k_star"]]
    _write_csv(out_path.with_name(out_path.stem + "_kstar.csv"), k_rows)
    return summary


# ---------------------------------------------------------------------------- worker side
def _ensure_harness_path() -> None:
    for path in (HERE, ROOT / "03_src"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def _make_plant_with_settle(cl, level, soil, pad_type, fs_kN, beta=1.0e9, soil_kscale=1.0,
                            slope=(0.0, 0.0)):
    """s9 ``make_plant`` with the optional A1 settle correction of the running case.

    The s9 settle hook is set per case ("harness" with the case's table row, else "p0"), so a
    ``S9_SETTLE_HOOK`` left in the environment does not change an uncorrected case."""
    import dyn_model as dm

    sl = sys.modules["s9_soil_closed_loop"]
    make_plant = _ORIGINALS["make_plant"]
    correction: SettleCorrection | None = _CAP.get("settle")
    table_row: SettleTableRow | None = _CAP.get("settle_table")
    if table_row is not None:
        plant = _make_plant_from_table(make_plant, table_row, cl, level, soil, pad_type, fs_kN,
                                       beta, soil_kscale, slope)
    elif correction is None or correction.is_zero:
        plant = make_plant(cl, level, soil, pad_type, fs_kN, beta, soil_kscale, slope,
                           settle_hook=sl.SETTLE_HOOK_P0)
    else:
        tilted = (slope[0] + correction.droll_deg, slope[1] + correction.dpitch_deg)
        plant = make_plant(cl, level, soil, pad_type, fs_kN, beta, soil_kscale, tilted,
                           settle_hook=sl.SETTLE_HOOK_P0)
        pad_xy = np.asarray(dm.geometry_from_params(dm.load_params()).pad_xy, float)
        shift = (correction.dz_m + pad_xy[:, 0] * math.tan(math.radians(correction.dpitch_deg))
                 - pad_xy[:, 1] * math.tan(math.radians(correction.droll_deg)))
        plant.soil.h = plant.soil.h + shift
        plant.goff[:] = -plant.soil.h
    _CAP["plant"] = plant
    return plant


def _make_plant_from_table(make_plant, row: SettleTableRow, cl, level, soil, pad_type, fs_kN,
                           beta, soil_kscale, slope):
    """Plant of a settle-table case: the s9 settle hook "harness" with the case's table row (the
    table floor add replaces the flat P0 pitch add, ``SoilPads.h = pad_h_m``)."""
    sl = sys.modules["s9_soil_closed_loop"]
    return make_plant(cl, level, soil, pad_type, fs_kN, beta, soil_kscale, slope,
                      settle_hook=sl.SETTLE_HOOK_HARNESS, settle_row=asdict(row))


def _pad_penetration_mm(cl, plant) -> list[float] | None:
    """Rod penetration of the original soil surface per pad [mm] (``soil_floor`` geometry;
    negative = gap); None on a rigid floor."""
    soil = plant.soil
    if soil is None:
        return None
    rotation = cl.rcc._R(plant.q)
    a_n = float(plant.nrm @ rotation[:, 2])
    pen = []
    for i in range(4):
        pad_point = plant.r + rotation @ plant.pad_rel[i]
        g0 = float(plant.nrm @ pad_point) / a_n
        pen.append(((plant.x[i] - g0) * a_n + soil.h[i]) * 1e3)
    return pen


def floor_axes_attitude_rad(body_rotation, roll_deg: float, pitch_deg: float) -> list[float]:
    """(phi, theta) of the body in the axes of the original floor R_f = Ry(pitch) Rx(roll)
    (ZYX of R_f^T R; theta > 0 nose down, phi > 0 left up)."""
    roll, pitch = math.radians(roll_deg), math.radians(pitch_deg)
    rot_x = np.array([[1.0, 0.0, 0.0], [0.0, math.cos(roll), -math.sin(roll)],
                      [0.0, math.sin(roll), math.cos(roll)]])
    rot_y = np.array([[math.cos(pitch), 0.0, math.sin(pitch)], [0.0, 1.0, 0.0],
                      [-math.sin(pitch), 0.0, math.cos(pitch)]])
    relative = (rot_y @ rot_x).T @ np.asarray(body_rotation, float)
    return [math.atan2(relative[2, 1], relative[2, 2]), -math.asin(relative[2, 0])]


def _floor_attitude_of(cl, plant) -> list[float]:
    case = _CAP["case"]
    return floor_axes_attitude_rad(cl.rcc._R(plant.q), case["roll_deg"], case["pitch_deg"])


def _settle_state(cl, plant) -> dict:
    """Settle geometry at the start of the closed loop (before any leg moves)."""
    return {"q_floor_deg": np.degrees(_floor_attitude_of(cl, plant)).tolist(),
            "pen_mm": _pad_penetration_mm(cl, plant), "check": None}


def settle_window_attitude_rad(log: dict, first_contact_s) -> tuple[list[float], float]:
    """Mean floor-axes attitude over the first 5 s of the closed loop, cut at the first pad
    contact (the table targets are 5 s means: the settle leaves the crawler rocking)."""
    contacts = [t for t in first_contact_s if t is not None]
    t_end = min([SETTLE_MEAN_WINDOW_S, *contacts])
    t = np.asarray(log["t_s"], float)
    mask = t <= t_end + TIME_MATCH_S
    q_floor = np.radians(np.asarray(log["q_floor_deg"], float)[mask])
    return q_floor.mean(axis=0).tolist(), float(t[mask][-1]) if mask.any() else 0.0


def _settle_table_check(settle: dict, log: dict) -> dict | None:
    """Settle-table check: pad gap at the settle instant, attitude as the window mean."""
    row: SettleTableRow | None = _CAP.get("settle_table")
    if row is None:
        return None
    q_mean, t_end = settle_window_attitude_rad(log, settle["first_contact_s"])
    start_gap = _CAP["case"].get("start_gap")
    gap_target_mm = start_gap_targets_mm(row.gap_target_mm, start_gap)
    check = settle_check(row.target_q_floor, gap_target_mm, q_mean, settle["pen_mm"])
    check.update(window_end_s=t_end, q_floor_mean_deg=np.degrees(q_mean).tolist(),
                 table_settle_pitch_pp_deg=row.settle_pitch_pp_deg)
    if start_gap is not None:  # spec 426.6: the moved pad is checked against its start gap
        check["gap_target_mm"] = gap_target_mm
    return check


def start_gap_targets_mm(gap_target_mm, start_gap) -> list[float]:
    """Settle-check gap targets: the table values, the start-gap pad replaced by its start gap
    (target gap, or table gap + delta)."""
    targets = [float(v) for v in gap_target_mm]
    if start_gap is None:
        return targets
    leg, kind, value_mm = start_gap
    i = LEGS.index(leg)
    targets[i] = float(value_mm) if kind == START_GAP_GAP else targets[i] + float(value_mm)
    return targets


def _make_project_controller(cl, c2, variant: dict):
    """Harness project preset (as r72), REANCHOR on when the variant asks for it."""
    sl = sys.modules["s9_soil_closed_loop"]
    config = cl.preset_config(c2.ContactJudge.COMBINED, with_imu_samples=True,
                              with_reapproach=True)
    if variant.get("reanchor"):
        config = replace(config, reanchor=replace(config.reanchor, enable=True))
    rise_max_N = _CAP["case"].get("plateau_rise_max_N")
    if rise_max_N is not None:
        config = replace(config, soil=replace(config.soil, plateau_rise_max_N=float(rise_max_N)))
    controller = c2.C2Controller.from_params(cl.PARAMS, config)
    controller.reset()
    _CAP["ctrl"] = controller
    plant = _CAP["plant"]
    # run_case builds the controller right after the crawler settle (same plant state)
    _CAP["node_d0"] = sl.crawler_node_heights(cl, plant)
    _CAP["settle_att_true_deg"] = np.degrees(plant.attitude()).tolist()
    _CAP["settle_state"] = _settle_state(cl, plant)
    _CAP["log"] = {"t_s": [], "phase": [], "fmin_kN": [], "rut_clear_mm": [],
                   "rut_settle_nodes_mm": [], "clear_est_mm": [], "q_floor_deg": [],
                   "sink_mm": [] if plant.soil is not None else None}
    if _CAP["case"].get("group") == H8_GROUP:  # spec 426.6 TOUCH record (H8 only)
        _CAP["log"].update(touched=[], stroke_mm=[], att_deg=[])
    return controller


def _control_period_logged(cl, Measurements, plant, cmd, valve, ha, period_s, rec, sens=None):
    """s9 ``control_period`` plus a per-period log (logging only, same arithmetic)."""
    sl = sys.modules["s9_soil_closed_loop"]
    measurements = _ORIGINALS["control_period"](cl, Measurements, plant, cmd, valve, ha,
                                                period_s, rec, sens)
    ctrl, log, node_d0 = _CAP["ctrl"], _CAP["log"], _CAP["node_d0"]
    node_in = node_d0 < 0.0
    log["t_s"].append(float(plant.t))
    log["phase"].append(str(ctrl.phase))
    log["fmin_kN"].append((np.asarray(rec["fmin"], float) / 1e3).tolist())
    log["rut_clear_mm"].append(crawler_floor_clearance_mm(sl, cl, plant))
    old_rut = sl.rut_clearance(cl, plant, node_d0, node_in) * 1e3 if node_in.any() else None
    log["rut_settle_nodes_mm"].append(old_rut)
    log["clear_est_mm"].append(ctrl._clearance_estimate_m(np.asarray(plant.x, float)) * 1e3)
    log["q_floor_deg"].append(np.degrees(_floor_attitude_of(cl, plant)).tolist())
    if log["sink_mm"] is not None:
        log["sink_mm"].append((np.asarray(plant.soil.z, float) * 1e3).tolist())
    if "touched" in log:  # spec 426.6 (H8): latch state, motor stroke and true deck attitude
        log["touched"].append([bool(v) for v in ctrl._state.touched])
        log["stroke_mm"].append((np.asarray(plant.sref, float) * 1e3).tolist())
        log["att_deg"].append(np.degrees(plant.attitude()).tolist())
    anchor = ctrl._state.reanchor_anchor_pitch_rad
    if "anchor_pitch_deg" not in _CAP and anchor is not None:
        _CAP["anchor_pitch_deg"] = math.degrees(anchor)
    return measurements


def _install_patches():
    _ensure_harness_path()
    import s9_soil_closed_loop as sl

    if not _ORIGINALS:
        _ORIGINALS.update(make_plant=sl.make_plant, control_period=sl.control_period)
    sl.make_plant = _make_plant_with_settle
    sl.make_controller = _make_project_controller
    sl.control_period = _control_period_logged
    late_loc_rule.install_crawler_recorder(sl._imports()[0], lambda: _CAP.get("crawler_series"))
    return sl


def _soil_state_record(ctrl) -> dict:
    soil = ctrl._soil_state()
    c_min = soil.clearance_at_plateau_start_m
    return {"t_P_s": soil.plateau_start_s,
            "c_min_tP_mm": None if c_min is None else c_min * 1e3,
            "corner_bias_mm": (np.asarray(soil.corner_bias_m) * 1e3).tolist(),
            "anchor_applied": bool(soil.is_loc_anchor_applied),
            "weight_ratio": soil.weight_ratio,
            "settle_attitude_deg": None if soil.settle_attitude_rad is None
            else np.degrees(soil.settle_attitude_rad).tolist()}


def crawler_floor_clearance_mm(sl, cl, plant) -> float:
    """Rut clearance (``RUT_DEFINITION``): lowest height of all crawler nodes above the harness
    floor plane [mm] (the crawler's settle contact sits on that plane, elastic sink a few mm)."""
    return float(np.min(sl.crawler_node_heights(cl, plant))) * 1e3


def _rut_ready_mm(log: dict, t_ready_s: float | None) -> float | None:
    """Logged rut clearance of the control period that ended at READY."""
    if t_ready_s is None:
        return None
    index = _row_at(log, t_ready_s)
    return None if index is None else log["rut_clear_mm"][index]


RUN_KEYS = ("t_level_s", "t_done_s", "t_ready_s", "final_phase", "t_crawler_off_first_s",
            "n_crawler_recontact", "crawler_N_max_after_ready", "clear_true_ready_mm",
            "clear_est_ready_mm", "min_true_Fcyl_after_off_kN", "min_true_Fcyl_after_ready_kN",
            "att_end_deg", "att_max_after_off_deg", "max_motor_stroke_mm", "sink_final_mm",
            "sink_rate_max_mm_s", "n_reapproach", "n_relevel", "n_probe_rounds", "n_warn",
            "phase_path", "commands_sha256", "wall_s")


def first_contact_times(log: dict, rod_weight_kN) -> list[float | None]:
    """First logged period end per leg whose minimum pad contact force (true F_cyl + rod
    weight) is above 0 (10 Hz resolution)."""
    contact = np.asarray(log["fmin_kN"], float) + np.asarray(rod_weight_kN, float)
    times: list[float | None] = []
    for i in range(4):
        hits = np.nonzero(contact[:, i] > 0.0)[0] if contact.size else np.array([], int)
        times.append(float(log["t_s"][hits[0]]) if hits.size else None)
    return times


def collect_record(case: dict, out: dict, sl, cl) -> dict:
    """Plain record of one finished run (the input of :func:`judge_case`)."""
    import dyn_model as dm

    ctrl, plant = _CAP["ctrl"], _CAP["plant"]
    soil_state = _soil_state_record(ctrl)
    settle = {**_CAP["settle_state"],
              "first_contact_s": first_contact_times(_CAP["log"], plant.Wr / 1e3)}
    settle["check"] = _settle_table_check(settle, _CAP["log"])
    return {
        "case": case,
        "F_min_kN": ctrl.geometry.F_min_N / 1e3,
        "weight_N": float(plant.m * plant.g) if hasattr(plant, "m") else None,
        "controller_weight_ref_N": float(ctrl._reference_weight_N()),
        "crawler_series": _CAP.get("crawler_series") or [],
        "rod_weight_kN": (np.asarray(plant.Wr, float) / 1e3).tolist(),
        "run": {key: out.get(key) for key in RUN_KEYS},
        "events": [(float(e.t_s), e.name) for e in ctrl.events],
        "log": _CAP["log"],
        "settle": {"att_true_deg": _CAP["settle_att_true_deg"],
                   "att_ctrl_deg": soil_state.pop("settle_attitude_deg"),
                   "anchor_pitch_deg": _CAP.get("anchor_pitch_deg"), **settle},
        "soil_state": soil_state,
        "rut_definition": RUT_DEFINITION,
        "rut_ready_mm": _rut_ready_mm(_CAP["log"], out.get("t_ready_s")),
        "rut_end_mm": crawler_floor_clearance_mm(sl, cl, plant),
        # first definition kept for comparison (harness READY value, last logged period)
        "rut_settle_nodes_mm": {"ready": out.get("clear_true_ready_mm"),
                                "end": (_CAP["log"]["rut_settle_nodes_mm"] or [None])[-1]},
        "pad_xy": np.asarray(dm.geometry_from_params(dm.load_params()).pad_xy, float).tolist(),
    }


def phase_segments(log: dict) -> list[tuple[str, float, float]]:
    """(phase, start, end) of the unbroken runs of the 10 Hz phase log [s]."""
    segments: list[list] = []
    for t_s, phase in zip(log["t_s"], log["phase"], strict=True):
        if segments and segments[-1][0] == phase:
            segments[-1][2] = t_s
        else:
            segments.append([phase, t_s, t_s])
    return [(phase, start, end) for phase, start, end in segments]


def probe_round_record(log: dict) -> dict:
    """Spec 422.3: probe rounds (PROBE entries) with each probe's duration and the re-level
    (LEVEL run) that follows it [s]."""
    segments = phase_segments(log)
    rounds = []
    for index, (phase, start, end) in enumerate(segments):
        if phase != "probe":
            continue
        following = segments[index + 1] if index + 1 < len(segments) else None
        relevel_s = None
        if following is not None and following[0] == "level":
            relevel_s = round(following[2] - following[1] + PERIOD_LOG_S, 2)
        rounds.append({"probe_start_s": round(start, 2),
                       "probe_s": round(end - start + PERIOD_LOG_S, 2), "relevel_s": relevel_s})
    return {"n_probe_rounds": len(rounds), "n_probe_rounds_ge_3": len(rounds) >= 3,
            "rounds": rounds}


def _weight_record(record: dict) -> dict:
    """Spec 422.3: plant weight against the controller W_ref and the LOC W_hat / W_ref."""
    run = record["run"]
    return {"mass_scale": record["case"].get("mass_scale", 1.0),
            "plant_weight_N": record.get("weight_N"),
            "controller_weight_ref_N": record.get("controller_weight_ref_N"),
            "plant_over_controller_W": (None if not record.get("controller_weight_ref_N")
                                        or record.get("weight_N") is None
                                        else record["weight_N"] / record["controller_weight_ref_N"]),
            "loc_weight_ratio": record["soil_state"].get("weight_ratio"),
            "warn_weight_mismatch": [n for _, n in record["events"]
                                     if n.startswith("WARN_WEIGHT_MISMATCH")],
            "rear_sink_final_mm": (None if run.get("sink_final_mm") is None
                                   else run["sink_final_mm"][2:]),
            "note": MASS_SCALE_NOTE if record["case"].get("mass_scale", 1.0) != 1.0 else None}


def _compact(record: dict, verdict: dict) -> dict:
    """Stored result: the record without the per-period log, events filtered."""
    events = [(round(t, 2), n) for t, n in record["events"]
              if not n.startswith(STORED_EVENT_SKIP_PREFIXES)]
    return {"id": record["case"]["id"], "case": record["case"], **verdict,
            "approximations": approximation_flags(record["case"]),
            "F_min_kN": record["F_min_kN"], "run": record["run"], "settle": record["settle"],
            "soil_state": record["soil_state"], "rut_definition": record["rut_definition"],
            "rut_ready_mm": record["rut_ready_mm"], "rut_end_mm": record["rut_end_mm"],
            "rut_settle_nodes_mm": record["rut_settle_nodes_mm"],
            # spec 422.3 records (every run; H6 reads them)
            "probe_rounds": probe_round_record(record["log"]), "weight": _weight_record(record),
            "warnings": sorted({n for _, n in record["events"]
                                if n.startswith(("WARN", "FAULT"))}),
            "events": events[:200], "wall_s": record["run"].get("wall_s")}


def run_one(case: dict) -> dict:
    """Worker entry: run one case on the patched s9 harness and judge it."""
    t0 = time.perf_counter()
    try:
        sl = _install_patches()
        cl = sl._imports()[0]
        _CAP.clear()
        _CAP["crawler_series"] = []  # 1 ms true crawler force (spec 419.8 condition 3)
        settle = case.get("settle")
        _CAP["settle"] = SettleCorrection(**settle) if settle else None
        table_row = case.get("settle_table")
        _CAP["settle_table"] = SettleTableRow(**table_row) if table_row else None
        _CAP["case"] = case
        out = sl.run_case(run_case_input(case))
        record = collect_record(case, out, sl, cl)
        result = _compact(record, judge_case(record))
        if case.get("group") == H8_GROUP:  # spec 426.6 records (the other groups unchanged)
            result.update(touch=touch_record(record), pad_start_gap=out.get("pad_start_gap"),
                          sample="in" if case.get("start_gap") is None else "out")
    except Exception as exc:  # keep the batch going, record the failure
        return {"id": case["id"], "case": case, "error": repr(exc),
                "tb": traceback.format_exc()[-3000:], "wall_s": time.perf_counter() - t0}
    result["wall_s_total"] = round(time.perf_counter() - t0, 1)
    return result


# ------------------------------------------------------------------------------ placement
def parse_affinity(spec: str | None) -> int | None:
    """'ecore' / 'pcore' / hex mask ('0x0FFF0000') -> mask; None or '' or 'os' -> None."""
    if not spec or spec.lower() == "os":
        return None
    named = {"ecore": E_CORE_MASK, "pcore": P_CORE_MASK}
    if spec.lower() in named:
        return named[spec.lower()]
    try:
        mask = int(spec, 16)
    except ValueError as exc:
        raise ValueError(f"affinity must be ecore, pcore, os or a hex mask, got {spec!r}") from exc
    if mask <= 0:
        raise ValueError(f"affinity mask must be positive, got {spec!r}")
    return mask


def set_parent_affinity(mask: int | None) -> dict:
    """Pin this process (the pool workers inherit it) and read the mask back (Windows)."""
    info: dict = {"requested_mask": None if mask is None else hex(mask)}
    if mask is None or sys.platform != "win32":
        return info
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    k32.GetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t),
                                           ctypes.POINTER(ctypes.c_size_t)]
    handle = k32.GetCurrentProcess()
    info["set_ok"] = bool(k32.SetProcessAffinityMask(handle, mask))
    process_mask, system_mask = ctypes.c_size_t(), ctypes.c_size_t()
    k32.GetProcessAffinityMask(handle, ctypes.byref(process_mask), ctypes.byref(system_mask))
    info["process_mask"] = hex(process_mask.value)
    info["system_mask"] = hex(system_mask.value)
    if not info["set_ok"] or process_mask.value != mask:
        raise RuntimeError(f"affinity not applied: {info}")
    return info


# ------------------------------------------------------------------------------------ main
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="S9 soft soil x floor slope screen (study 1)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--affinity", default=os.environ.get(PLACEMENT_ENV),
                        help=f"ecore | pcore | os | hex mask (default ${PLACEMENT_ENV})")
    parser.add_argument("--groups", default=",".join(GROUP_SIZES))
    parser.add_argument("--filter", default="", help="comma list of case-id substrings")
    parser.add_argument("--settle-corrections", type=Path, default=None,
                        help="JSON {soil|pad|level|roll,pitch: {dz_m, droll_deg, dpitch_deg}}")
    parser.add_argument("--settle-table", type=Path, default=None,
                        help="dynamics slope settle table (slope_crawler_settle.json)")
    parser.add_argument("--settle-key", default=SETTLE_TABLE_KEY,
                        help=f"block of the settle table (default {SETTLE_TABLE_KEY})")
    parser.add_argument("--plateau-rise-max-n", type=float, default=None,
                        help="LOC plateau rise threshold [N] for every case (U-S9-C2 sensitivity; "
                             "default: preset 2000)")
    parser.add_argument("--mass-scale", type=float, default=None,
                        help="spec 422: plant mass / inertia factor for every selected case "
                             "(controller unchanged; id suffix |m<scale>); H6 sets its own")
    parser.add_argument("--fs-kn", type=float, default=None,
                        help="spec 426.4: front seal friction F_s [kN] for every selected case "
                             "(applied after --filter; id suffix |Fs<f> unless 4)")
    parser.add_argument("--level", choices=(LEVEL_TOP, LEVEL_MIDDLE, LEVEL_BOTTOM), default=None,
                        help="spec 426.4: auger level for every selected case (applied after "
                             "--filter; the settle-table rows are attached again for that level)")
    parser.add_argument("--list", action="store_true", help="print the case ids and stop")
    parser.add_argument("--from-json", type=Path, default=None,
                        help="rebuild the summary of an existing result file (no runs)")
    return parser


def _file_sha256(path: Path | None) -> str | None:
    return None if path is None else hashlib.sha256(path.read_bytes()).hexdigest()


def select_cases(args) -> list[SlopeCase]:
    cases = build_cases(tuple(g for g in args.groups.split(",") if g))
    if args.settle_corrections is not None and args.settle_table is not None:
        raise SystemExit("--settle-corrections and --settle-table are exclusive")
    if args.settle_corrections is not None:
        table = json.loads(args.settle_corrections.read_text(encoding="utf-8"))
        cases = attach_settle_corrections(cases, table)
    if args.settle_table is not None:
        table = json.loads(args.settle_table.read_text(encoding="utf-8"))
        cases = attach_settle_table(cases, table[args.settle_key])
    needles = [n for n in args.filter.split(",") if n]
    if needles:
        cases = [c for c in cases if any(n in c.case_id for n in needles)]
    if args.plateau_rise_max_n is not None:
        cases = [replace(c, plateau_rise_max_N=args.plateau_rise_max_n) for c in cases]
    if args.mass_scale is not None:  # spec 422: every selected case (H6 carries its own scales)
        cases = [replace(c, mass_scale=args.mass_scale) for c in cases]
    # spec 426.4 (study B); getattr: callers may pass a namespace without the newer options
    fs_kn = getattr(args, "fs_kn", None)
    if fs_kn is not None:
        cases = [replace(c, fs_kN=fs_kn) for c in cases]
    level = getattr(args, "level", None)
    if level is not None:
        cases = _with_level(cases, level, args)
    return cases


def _with_level(cases: list[SlopeCase], level: str, args) -> list[SlopeCase]:
    """Cases moved to another auger level, the settle-table rows attached again for it.

    Raises:
        SystemExit: with ``--settle-corrections`` (those are keyed per level).
    """
    if args.settle_corrections is not None:
        raise SystemExit("--level and --settle-corrections are exclusive (corrections are keyed "
                         "per level)")
    cases = [replace(c, level=level, settle_table=None, settle_table_status=None) for c in cases]
    if args.settle_table is not None:
        table = json.loads(args.settle_table.read_text(encoding="utf-8"))
        cases = attach_settle_table(cases, table[args.settle_key])
    return cases


def _script_sha256() -> str:
    # LF line ends: a CRLF checkout gives the same digest
    return hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _print_result(result: dict) -> None:
    if "error" in result:
        print(result["id"], "ERROR", result["error"])
        return
    row = case_table_row(result)
    print(row["id"], row["verdict"], "settle", row["settle_table"], row["settle_check_ok"],
          "pitch_floor", row["settle_pitch_floor_deg"], "front_gap", row["front_gap_mm"],
          "contact", row["first_contact_s"], "failed", row["failed_rows"] or "-", "stroke",
          f"{row['max_stroke_mm']:.1f}", "minF", row["min_Fcyl_kN"], "att",
          [round(row["att_end_roll_deg"], 3), round(row["att_end_pitch_deg"], 3)], "ready",
          row["t_ready_s"], "warn", row["warnings"] or "-", "fault", row["faults"] or "-",
          "lift", row["lifted_legs"] or "-", "R_c", round(row["R_c"], 3), "wall", row["wall_s"])


def main() -> None:
    args = build_parser().parse_args()
    if args.from_json is not None:
        payload = json.loads(args.from_json.read_text(encoding="utf-8"))
        results = [rejudge_stored(result) for result in payload["results"]]
        meta = {**payload["meta"], "rejudged": {
            "from": str(args.from_json), "sha256": _file_sha256(args.from_json),
            "script_sha256": _script_sha256(),
            "rules": "verdict recomputed from the stored rows (stroke-limited pass needs P3-1, "
                     "P3-3, P3-4); rut clearance as stored (rut_definition per result)"}}
        summary = write_outputs(args.out, results, meta)
        print(json.dumps(summary["counts"]))
        return
    cases = select_cases(args)
    if args.list:
        for case in cases:
            print(case.case_id, case.settle_table_status or "")
        print(len(cases), "cases", dict(Counter(c.settle_table_status for c in cases)))
        return
    placement = set_parent_affinity(parse_affinity(args.affinity))
    workers = max(1, min(args.workers, len(cases)))
    t0 = time.perf_counter()
    with Pool(workers) as pool:
        results = pool.map(run_one, [c.to_dict() for c in cases], chunksize=1)
    meta = {"script": "04_scripts/03_control/s9/s9_soil_slope.py",
            "script_sha256": _script_sha256(), "design": "extra studies 1 (control 2026-10-28)",
            "n_cases": len(cases), "groups": args.groups, "filter": args.filter,
            "workers": workers, "placement": placement,
            "run_limit_s": float(os.environ.get("S9_RUN_LIMIT_S", "240")),
            "settle_corrections": None if args.settle_corrections is None
            else str(args.settle_corrections),
            "settle_table": None if args.settle_table is None else {
                "path": str(args.settle_table), "key": args.settle_key,
                "sha256": _file_sha256(args.settle_table),
                "status_counts": dict(Counter(c.settle_table_status for c in cases))},
            "fs_kN": FS_KN, "plateau_rise_max_N": args.plateau_rise_max_n,
            "fs_kN_note": "H6 cases carry their own F_s (case fs_kN, id suffix |Fs<f>)",
            "mass_scale": args.mass_scale,
            "mass_scale_note": MASS_SCALE_NOTE if args.mass_scale is not None or any(
                c.mass_scale != 1.0 for c in cases) else None,
            "approximations": APPROXIMATION_NOTES, "wall_s": round(time.perf_counter() - t0, 1)}
    # spec 426.4 overrides: written only when given (the meta of former runs is unchanged)
    if args.fs_kn is not None:
        meta["fs_kN_override"] = args.fs_kn
    if args.level is not None:
        meta["level_override"] = args.level
    summary = write_outputs(args.out, results, meta)
    for result in results:
        _print_result(result)
    print("counts", json.dumps(summary["counts"]), "wall", meta["wall_s"], "s ->", args.out)


if __name__ == "__main__":
    main()
