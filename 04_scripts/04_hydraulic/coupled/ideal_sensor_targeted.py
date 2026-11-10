"""Ideal-sensor diagnosis stage 1 on the reduced harness: bundles I-0, I-1, I-1k, I-1p.

Plan: ``06_analysis/03_hydraulic/coupled/v5/las/ideal/ideal_stage1_plan.md`` (registered,
:data:`PLAN_SHA256`) and its revision ``ideal_stage1_plan_rev1.md`` (:data:`PLAN_REV1_SHA256`,
it replaces or adds to the sections it names). The plan text wins where this code differs.
This is a diagnosis, not a judgement: the lines carry the values, ``ideal_stage1_judge.py``
counts the metrics.

What runs: the K1 Y line of a key (``run_v5`` line + ``las`` / ``rev`` / ``done_trace`` of
``las_revA_targeted``, LAS-b P0 = preset or P5r4 by ``las_revA_targeted``'s install) with the
project controller replaced by :class:`IdealSensorC2` (one variant per run):

  SHD  shadow: every override returns the parent result, the ideal values are recorded only
  IGA  ideal crawler contact / gap (plan 3, rev1 R1-3): soil mode needs crawler contact,
       LOC = no contact for :data:`LOC_DEBOUNCE_PERIODS` periods and the node gap above
       :data:`LOC_GAP_M` (hysteresis :data:`LOC_GAP_HYST_M`), LOC revocation after
       :data:`REVOKE_CONTACT_PERIODS` contact periods, clearance ``c_k := g_box_k``
  IGB  IGA with the R4c30 and E3c10 margins off (target = true box gap 50 mm)
  IZ   ideal pad sinkage: the clearance plane through ``z_retr - s + z`` and the DSb75 residual
       from the 1 s least-squares slope of ``z`` (rev1 R1-4)
  S4   pressure readings = the mean of the period's 100 one-millisecond chunk-end readings

The truth reaches the controller only through :class:`IdealSource`, filled per period from
the plant by the 1 ms chunk hook (:class:`ChunkAccumulator` on ``c2py_r8d1_closed_loop
._lagged_step``) and read at the start of :meth:`IdealSensorC2.update`; the controller keeps
its nominal parameters. The K1-off arm installs ``flat_soil_margin_order_gate = False``
explicitly; a run whose requested and effective gate differ ends as an error line.

Tags (plan 6 V-1): ``controller_tag`` = ``<base_tag>_IDEAL-<variant>``, ``base_tag`` =
``v5_options.controller_tag(options, config)``; the replay tools refuse such records.

Usage (dynamics-dev python.exe, project root, PowerShell, threads 1):
  python -I -B 04_scripts/04_hydraulic/coupled/ideal_sensor_targeted.py list --bundle I-1
      [--stored-root <main checkout>] [--keys-file ..] [--plan-file <plan> <rev1>]
  python -I -B 04_scripts/04_hydraulic/coupled/ideal_sensor_targeted.py run --bundle I-0
      [--variant SHD,IGA,...] [--stored-root <main checkout>] [--out-dir <folder>]
      [--workers 16] [--affinity HEX] [--pool P|E|mixed] [--resume]
      [--keys-file ..] [--plan-file ..] [--trial-out <folder> [--keys K1,K2] [--limit N]]
The stored lines (S-C, revA2, las_T1 / T2, K1 Y) are read from ``<stored-root>/06_analysis/
03_hydraulic/coupled/v5`` (read only; in a worktree: the main checkout, no junction needed).
Output ``<out-dir>/ideal_<bundle>_<variant>.jsonl`` (default this checkout's ``v5/las/ideal``;
new files only; ``--resume`` writes ``..._resume.jsonl`` with the keys whose only line is an
error line), plus ``ideal_<bundle>_run.run.json`` (start / end: commit, clean state, stored
inputs and their sha256) and ``ideal_<bundle>_run.sha256`` (sha256sum lines of the outputs).
Exit codes: 0 done, 1 a batch stop or run errors (run) / a count or reference mismatch (list),
2 input error (keys file, plan files, stored files, gates, identity, existing output).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import queue
import subprocess
import sys
import time
import traceback
from collections import deque
from dataclasses import dataclass, field, replace
from enum import StrEnum
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import k1_judge as kj  # noqa: E402  (stdlib only)
import k1_targeted as kt  # noqa: E402  (imports fb_targeted: thread variables before numpy)
import numpy as np  # noqa: E402

revA = kt.revA
rev = kt.rev
fb = kt.fb
s2t = kt.s2t
rj = kj.rj
ROOT = fb.ROOT
if str(ROOT / "03_src") not in sys.path:
    sys.path.insert(0, str(ROOT / "03_src"))

# ------------------------------------------------------------------------------- constants
IDEAL_DIR = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "las" / "ideal"
IDEAL_DIR_RELATIVE = Path("las") / "ideal"
PLAN_PATH = IDEAL_DIR / "ideal_stage1_plan.md"
PLAN_REV1_PATH = IDEAL_DIR / "ideal_stage1_plan_rev1.md"
KEYS_PATH = IDEAL_DIR / "ideal_stage1_keys.json"
PLAN_SHA256 = "06c9c6b0e90db290b84a96523cbe0570ddcb1bb82d0d5277bb6037f06f260455"
PLAN_REV1_SHA256 = "0d3bb1b80a357eeb2bf0a90382ca92f6674322517d721a149ca43f667598a189"
PLAN_SHA256_LIST = (PLAN_SHA256, PLAN_REV1_SHA256)
"""rev1 R1-6: ``plan_sha256`` is recorded as [registered, rev1]."""
KEYS_SHA256 = "fa313763afda066929317fdc32a58996eaf58601bc364869f6c2c41a689d8766"

SET_SHA256 = {
    "A_P0": "4cdc9bfe100a4b7d7504df8621eff2fd32660604ab423a61a070ca7a634c5da6",
    "A_boundary_P0": "f7952299c05840ab8cbc914a3ff75b0d3d21e320b67e14f68ce62230f5a2672a",
    "A_P5r4": "56177ba0a566a28b3fb8422872118b8392f4b1bcb06e7b01065ac6bce061c8a5",
    "B": "454661b3875f581e0ec85964adb9d332858132cac8c4611fd76bc7b2956bb6bc",
    "C": "78fae79813e3c4cfffb7724468a5008055e6b263327fe9c3129ccd8ffb2efe91",
    "E": "fb48215aef3ed7967df027ca600c60004c41d5d9a13dcf8f9536c86d13d976da",
    "F": "38ee1c5585b620e84888a4852a96816334fc3fdf7dbde03524d7bc139fd49c8f",
}
"""Plan 4 table: list sha256 per set (``sha256(LF.join(sorted(ids)) + LF)``)."""
SET_COUNTS = {"A_P0": 5, "A_boundary_P0": 1, "A_P5r4": 2, "B": 8, "C": 67, "E": 40, "F": 40}
UNION_P0_SETS = ("A_P0", "A_boundary_P0", "B", "C", "E", "F")
UNION_P0_SHA256 = "ea5de7ed68694ccaf7715111bf2106da24d6ddac15c107a1a7bd86308b116e2f"
UNION_P0_COUNT = 161

# Ideal-information rule constants (plan 3 / Q-5 assumptions, rev1 R1-3 / R1-7).
LOC_GAP_M = 0.002
LOC_GAP_HYST_M = 0.001
LOC_DEBOUNCE_PERIODS = 2
REVOKE_CONTACT_PERIODS = 1
LOC_GAP_REFERENCE = "node"
"""rev1 R1-3 ②: the LOC gap condition on ``g_node_min`` ("node") or ``g_box_min`` ("box")."""
LOC_GAP_REFERENCES = ("node", "box")
IZ_CORRECTS_LOC_SAMPLES = True
"""IZ: the S-1 window samples (``c_min(t_P)``, S-3 bias) also use the corrected plane."""
PERIOD_S = 0.1
CHUNKS_PER_PERIOD = 100
IDEAL_TAG_INFIX = "_IDEAL-"

PRESSURE_EVENT_PREFIXES = ("FAULT_HEAD_PRESSURE", "WARN_ROD_PRESSURE_FALLBACK",
                           "INFO_PRESSURE_STEP", "WARN_CRAWLER_RECONTACT_SUSPECTED",
                           "INFO_HEAD_PRESSURE_FAULT_REASON")
"""M-11 events, counted from the controller (``verdict_runs`` drops ``INFO_PRESSURE*``)."""

K1_ARM_ON, K1_ARM_OFF = "on", "off"
LAS_P0, LAS_P5R4 = "P0", "P5r4"


class Variant(StrEnum):
    """Plan 3 variants (codes without hyphens, plan 6 V-1)."""

    SHD = "SHD"
    IGA = "IGA"
    IGB = "IGB"
    IZ = "IZ"
    S4 = "S4"


@dataclass(frozen=True)
class BundleSpec:
    """One row of plan 5 (sets in plan 4 order, arms, LAS-b candidate)."""

    name: str
    variants: tuple[str, ...]
    sets: tuple[str, ...]
    arms: tuple[str, ...]
    las: str
    first_of_set: dict | None = None
    """I-0: how many keys of each set, from the front of the list (plan 8.4)."""


BUNDLES = {
    "I-0": BundleSpec("I-0", ("SHD",), ("A_P0", "A_boundary_P0", "F", "E"), (K1_ARM_ON,),
                      LAS_P0, {"A_P0": 5, "A_boundary_P0": 1, "F": 4, "E": 4}),
    "I-1": BundleSpec("I-1", ("SHD", "IGA", "IGB", "IZ", "S4"), UNION_P0_SETS, (K1_ARM_ON,),
                      LAS_P0),
    "I-1k": BundleSpec("I-1k", ("SHD", "IGA", "IGB", "IZ"), ("A_P0", "A_boundary_P0"),
                       (K1_ARM_OFF,), LAS_P0),
    "I-1p": BundleSpec("I-1p", ("SHD", "IGA", "IGB", "IZ"), ("A_P5r4",),
                       (K1_ARM_ON, K1_ARM_OFF), LAS_P5R4),
}
BUNDLE_COUNTS = {"I-0": 14, "I-1": 805, "I-1k": 24, "I-1p": 16}
"""Plan 5 (873 with H-F 144 = ``r64_g4_ideal_s4.py``)."""

JOB_SOURCE = {"A_P0": "SC", "A_boundary_P0": "SC", "B": "SC", "C": "SC", "E": "SC",
              "A_P5r4": "RS", "F": "RT"}
"""Where the job dict of a key comes from (the tool that made the stored line)."""
RECORD_DONE = {"SC": False, "RS": True, "RT": True}
"""As ``k1_targeted``: S-C lines without the DONE record, revA / L lines with it."""
SHD_REFERENCE = {("A_P0", K1_ARM_ON): ("k1", "Y-Pa"), ("A_P0", K1_ARM_OFF): ("SC", None),
                 ("A_boundary_P0", K1_ARM_ON): ("SC", None),
                 ("A_boundary_P0", K1_ARM_OFF): ("SC", None),
                 ("B", K1_ARM_ON): ("SC", None), ("C", K1_ARM_ON): ("SC", None),
                 ("E", K1_ARM_ON): ("SC", None), ("F", K1_ARM_ON): ("L", None),
                 ("A_P5r4", K1_ARM_ON): ("k1", "Y-Sb"), ("A_P5r4", K1_ARM_OFF): ("k1", "Y-0b")}
"""Plan 6 V-3: the stored line whose ``commands_sha256`` an SHD line must reproduce."""


# ------------------------------------------------------------------------------- small helpers
def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def list_sha256(keys) -> str:
    """Plan 4 list rule: ``sha256(LF.join(sorted(ids)) + LF)``."""
    return kj.key_list_sha256(keys)


def ideal_tag(base_tag: str | None, variant: str) -> str:
    """Plan 6 V-1: ``<base_tag>_IDEAL-<variant>``."""
    if not base_tag:
        raise ValueError("an IDEAL tag needs a base tag")
    return f"{base_tag}{IDEAL_TAG_INFIX}{Variant(variant).value}"


def is_ideal_tag(tag: str | None) -> bool:
    return tag is not None and IDEAL_TAG_INFIX in tag


def window_lsq_slopes(times_s, values) -> np.ndarray:
    """Least-squares slope per column of ``values`` over ``times_s`` (the DSb75 formula of
    ``C2Controller._diff_sink_rates_m_s``)."""
    times = np.asarray(times_s, float)
    data = np.asarray(values, float)
    centred_t = times - times.mean()
    return centred_t @ (data - data.mean(axis=0)) / (centred_t @ centred_t)


def axis_differences(per_leg) -> np.ndarray:
    """(FL - FR, RL - RR) of a per-leg (4,) array (DSb75 axes, left sinking = +)."""
    values = np.asarray(per_leg, float)
    return np.array([values[0] - values[1], values[2] - values[3]])


def period_mean(chunk_values) -> np.ndarray:
    """S4: box mean of the period's chunk-end readings (rows = chunks)."""
    return np.mean(np.asarray(chunk_values, float), axis=0)


# ------------------------------------------------------------------------------- LOC rule
@dataclass
class IdealLocRule:
    """Plan 3 IGA ② with rev1 R1-3: LOC after ``debounce`` periods without crawler contact
    while the gap latch is on (on above ``gap_m``, off below ``gap_m - hysteresis_m``).

    :meth:`step` returns the first sample of the contact-free run (``t_P``) when the LOC is
    due, else None.
    """

    gap_m: float = LOC_GAP_M
    hysteresis_m: float = LOC_GAP_HYST_M
    debounce: int = LOC_DEBOUNCE_PERIODS
    is_gap_ok: bool = False
    free_periods: int = 0
    run_start: object = None

    def step(self, has_contact: bool, gap_m: float, sample: object) -> object:
        if self.is_gap_ok and gap_m < self.gap_m - self.hysteresis_m:
            self.is_gap_ok = False
        elif not self.is_gap_ok and gap_m > self.gap_m:
            self.is_gap_ok = True
        if has_contact:
            self.free_periods = 0
            self.run_start = None
            return None
        if self.free_periods == 0:
            self.run_start = sample
        self.free_periods += 1
        if self.free_periods >= self.debounce and self.is_gap_ok:
            return self.run_start
        return None


@dataclass
class ContactRun:
    """Plan 3 IGA ③: consecutive contact periods; due at ``needed`` (then counted anew)."""

    needed: int = REVOKE_CONTACT_PERIODS
    periods: int = 0

    def step(self, has_contact: bool) -> bool:
        self.periods = self.periods + 1 if has_contact else 0
        if self.periods >= self.needed:
            self.periods = 0
            return True
        return False


def loc_gap_m(source: IdealSource, reference: str = LOC_GAP_REFERENCE) -> float:
    """The LOC gap input of rev1 R1-3 ②."""
    if reference not in LOC_GAP_REFERENCES:
        raise ValueError(f"LOC_GAP_REFERENCE must be one of {LOC_GAP_REFERENCES}")
    if reference == "node":
        return source.g_node_min_m
    return float(np.min(source.g_box_m))


# ------------------------------------------------------------------------------- truth
@dataclass
class IdealSource:
    """The ideal values of one control period (read only for the controller, plan 8.1)."""

    t_s: float
    chunks: int
    cr_max_N: float
    has_crawler_contact: bool
    """rev1 R1-2: any of the period's 1 ms chunk-end crawler forces > 0 (no threshold)."""
    g_box_m: np.ndarray
    g_node_min_m: float
    z_m: np.ndarray
    sp_m: np.ndarray | None
    corner_h_plane_m: np.ndarray | None
    p_bar_head_Pa: np.ndarray
    p_bar_rod_Pa: np.ndarray | None
    f_z_bar_m_s2: float | None
    is_last_chunk_equal: bool


@dataclass
class _Chunk:
    net_N: np.ndarray
    rod_Pa: np.ndarray | None


class ChunkAccumulator:
    """1 ms chunk-end values since the last controller update (plan 8.2)."""

    def __init__(self) -> None:
        self.plant = None
        self.cr_max_N = 0.0
        self.count = 0
        self.chunks: deque[_Chunk] = deque(maxlen=CHUNKS_PER_PERIOD)

    def on_chunk(self, plant, accumulated) -> None:
        self.plant = plant
        self.count += 1
        self.cr_max_N = max(self.cr_max_N, float(accumulated[15]))
        rod = None
        if all(hasattr(plant, name) for name in ("p_r0", "Gr", "A_ann")):
            rod = (np.asarray(plant.p_r0, float)
                   - np.asarray(plant.Gr, float) / np.asarray(plant.A_ann, float))
        self.chunks.append(_Chunk(np.array(plant.pressure(), float), rod))

    def take(self) -> tuple[int, float, list[_Chunk]]:
        values = (self.count, self.cr_max_N, list(self.chunks))
        self.count, self.cr_max_N = 0, 0.0
        self.chunks.clear()
        return values


ACCUMULATOR = ChunkAccumulator()
_GEOMETRY_FUNCTIONS: dict = {}
"""``rotation`` (quaternion -> matrix) and ``node_heights`` (plant -> heights) of the harness."""


def underlying_plant(plant):
    """The harness plant behind a step-only view: the VB / LS settings wrap ``_lagged_step``
    with ``harness_hydraulics.install_overlap_cut``, which passes a ``_CutPlant`` (only
    ``step`` and ``dt``, the plant in ``_plant``) to the functions it wraps."""
    while hasattr(plant, "_plant"):
        plant = plant._plant
    return plant


def install_chunk_hook(closed_loop) -> None:
    """Wrap ``closed_loop._lagged_step`` once (read only: the chunk result is returned as is)."""
    import functools

    inner = closed_loop._lagged_step
    if getattr(inner, "is_ideal_chunk_hook", False):
        return

    @functools.wraps(inner)
    def lagged_step(plant, command, valve, steps):
        accumulated = inner(plant, command, valve, steps)
        ACCUMULATOR.on_chunk(underlying_plant(plant), accumulated)
        return accumulated

    lagged_step.is_ideal_chunk_hook = True
    closed_loop._lagged_step = lagged_step


def crawler_box_gaps_m(plant, rotation) -> np.ndarray:
    """``g_box_k``: crawler box corners (order of ``C2Geometry.crawler_corners_xy_m``) above
    the harness floor plane ``n . (r + R (c_k - com))`` (as ``Plant.crawler_clearance``)."""
    matrix = rotation(plant.q)
    com = plant.body.com
    (x0, x1), (y0, y1) = plant.geo.crawler_xy_box
    bottom_z = plant.geo.crawler_bottom_z
    corners = np.array([[x0, y0, bottom_z], [x0, y1, bottom_z], [x1, y0, bottom_z],
                        [x1, y1, bottom_z]], float)
    return np.array([float((plant.r + matrix @ (corner - com)) @ plant.nrm)
                     for corner in corners])


def crawler_node_gaps_m(plant, rotation) -> np.ndarray:
    """Crawler node heights above the floor plane (``s9_soil_closed_loop.crawler_node_heights``,
    P3-5 ``RUT_DEFINITION``)."""
    matrix = rotation(plant.q)
    return np.array([float(plant.nrm @ (plant.r + matrix @ node)) for node in plant.cr_rel])


def corner_h_plane_m(geometry, plant) -> np.ndarray | None:
    """rev1 R1-6: the plane through the pads' soil reference heights ``soil.h`` at the four
    crawler corners (None on a plant without soil)."""
    soil = getattr(plant, "soil", None)
    if soil is None:
        return None
    plane = geometry._plane_fit @ np.asarray(soil.h, float)
    return plane[0] + geometry.crawler_corners_xy_m @ plane[1:]


def _plant_sinkage_m(plant) -> tuple[np.ndarray, np.ndarray | None]:
    soil = getattr(plant, "soil", None)
    if soil is None:
        return np.zeros(4), None
    return np.array(soil.z, float), np.array(soil.sp, float)


def _chunk_pressures(chunks: list[_Chunk], head_area, annulus_area, has_rod: bool):
    """Chunk-end (head, rod) readings in the arithmetic of the harness readings."""
    nets = np.array([chunk.net_N for chunk in chunks], float)
    if not has_rod:
        return nets / head_area, None
    rods = np.array([chunk.rod_Pa for chunk in chunks], float)
    return (nets + rods * annulus_area) / head_area, rods


def build_source(measurements, geometry) -> IdealSource | None:
    """The :class:`IdealSource` of the period that just ended (None without chunks)."""
    count, cr_max, chunks = ACCUMULATOR.take()
    plant = ACCUMULATOR.plant
    if plant is None or not chunks:
        return None
    rotation = _GEOMETRY_FUNCTIONS["rotation"]
    has_rod = measurements.rod_pressure_Pa is not None
    if has_rod and any(chunk.rod_Pa is None for chunk in chunks):
        raise RuntimeError("rod readings without the plant's rod-side law")
    annulus = getattr(plant, "A_ann", None)
    heads, rods = _chunk_pressures(chunks, geometry.head_area_m2, annulus, has_rod)
    is_equal = bool(np.array_equal(heads[-1], np.asarray(measurements.head_pressure_Pa, float)))
    if has_rod:
        is_equal &= bool(np.array_equal(rods[-1], np.asarray(measurements.rod_pressure_Pa,
                                                             float)))
    samples = measurements.imu_specific_force_samples_m_s2
    f_z = None if samples is None else float(np.mean(np.asarray(samples, float)[:, 2]))
    z, sp = _plant_sinkage_m(plant)
    return IdealSource(
        t_s=float(measurements.t_s), chunks=count, cr_max_N=cr_max,
        has_crawler_contact=cr_max > 0.0, g_box_m=crawler_box_gaps_m(plant, rotation),
        g_node_min_m=float(np.min(crawler_node_gaps_m(plant, rotation))), z_m=z, sp_m=sp,
        corner_h_plane_m=corner_h_plane_m(geometry, plant),
        p_bar_head_Pa=period_mean(heads), p_bar_rod_Pa=None if rods is None else period_mean(rods),
        f_z_bar_m_s2=f_z, is_last_chunk_equal=is_equal)


# ------------------------------------------------------------------------------- controller
@dataclass(frozen=True)
class IdealSettings:
    """What one worker's controllers run (bound to the class by :func:`ideal_controller_class`)."""

    variant: str
    k1_arm: str = K1_ARM_ON


@dataclass
class _IdealState:
    """Per-run state of :class:`IdealSensorMixin` (deep-copied with the controller)."""

    source: IdealSource | None = None
    loc_rule: IdealLocRule = field(default_factory=IdealLocRule)
    shadow_rule: IdealLocRule = field(default_factory=IdealLocRule)
    revoke_run: ContactRun = field(default_factory=ContactRun)
    z_by_t: dict = field(default_factory=dict)
    corrected_by_t: dict = field(default_factory=dict)
    is_s1_record_only: bool = False
    s1_would_loc_s: float | None = None
    ideal_loc_s: list = field(default_factory=list)
    shadow_loc_s: float | None = None
    soil_starts_seen: int = 0
    soil_starts: list = field(default_factory=list)
    loc_onsets: list = field(default_factory=list)
    was_loc: bool = False
    chunk_anomalies: list = field(default_factory=list)
    last_chunk_mismatches: int = 0
    periods: dict = field(default_factory=lambda: {name: [] for name in PERIOD_FIELDS})


PERIOD_FIELDS = ("t_s", "chi_cr", "cr_max_N", "g_box", "g_min", "g_node_min", "c_min",
                 "c_corr_min", "z", "r_dsb", "r_dsb_ideal", "r_bar_aligned", "r_inst",
                 "p_bar_h", "p_bar_r", "corner_h_plane")
"""Plan 8.3 and rev1 R1-6 per-period arrays (``g_min`` = min of ``g_box``)."""


class IdealSensorMixin:
    """The plan 3 overrides (mixed in before the harness controller class)."""

    _ideal_settings: IdealSettings = IdealSettings(Variant.SHD.value)

    # --- set-up -------------------------------------------------------------------------
    def __init__(self, geometry, config=None, *args, **kwargs):
        self._ideal_disabled = {}
        self._ideal = _IdealState()
        if config is not None:
            config = self._ideal_config(config)
        super().__init__(geometry, config, *args, **kwargs)
        self._ideal = _IdealState()
        self.check_k1_arm()

    def _ideal_config(self, config):
        variant = self._ideal_settings.variant
        margin = config.slope_clearance_margin
        if variant == Variant.IGB.value:
            self._ideal_disabled = {"slope_clearance_margin.enable": margin.enable,
                                    "slope_clearance_margin.flat_soil_margin_m":
                                        margin.flat_soil_margin_m}
            margin = replace(margin, enable=False, flat_soil_margin_m=0.0)
        if self._ideal_settings.k1_arm == K1_ARM_OFF:
            margin = replace(margin, flat_soil_margin_order_gate=False)
        return replace(config, slope_clearance_margin=margin)

    def check_k1_arm(self) -> None:
        """Plan 8.1: the effective order gate is the requested one.

        Raises:
            RuntimeError: They differ (the run must end as an error line).
        """
        requested = self._ideal_settings.k1_arm == K1_ARM_ON
        effective = bool(self.config.slope_clearance_margin.flat_soil_margin_order_gate)
        if requested != effective:
            raise RuntimeError(f"K1 order gate requested {self._ideal_settings.k1_arm} but "
                               f"effective {effective}")

    def reset(self) -> None:
        super().reset()
        self._ideal = _IdealState()

    def _variant_is(self, *variants: Variant) -> bool:
        return self._ideal_settings.variant in {variant.value for variant in variants}

    def _uses_ideal_contact(self) -> bool:
        return self._variant_is(Variant.IGA, Variant.IGB) and self._ideal.source is not None

    # --- period -------------------------------------------------------------------------
    def update(self, measurements):
        source = build_source(measurements, self.geometry)
        ideal = self._ideal
        ideal.source = source
        if source is not None:
            self._note_chunks(source)
            ideal.z_by_t[source.t_s] = source.z_m.copy()
            if self._variant_is(Variant.S4):
                measurements = replace(measurements, head_pressure_Pa=source.p_bar_head_Pa,
                                       rod_pressure_Pa=source.p_bar_rod_Pa)
        phase_before = str(self._state.phase)
        output = super().update(measurements)
        if source is not None:
            self._record_period(source, measurements, phase_before)
        return output

    def _note_chunks(self, source: IdealSource) -> None:
        ideal = self._ideal
        if source.chunks != CHUNKS_PER_PERIOD:
            ideal.chunk_anomalies.append((source.t_s, source.chunks))
        if not source.is_last_chunk_equal:
            ideal.last_chunk_mismatches += 1
            if self._variant_is(Variant.S4):
                raise RuntimeError(f"S4 chunk readings do not end at the run's reading "
                                   f"(t {source.t_s})")

    # --- overrides (plan 3 list) --------------------------------------------------------
    def _hold_crawler_zone_until_liftoff(self, reading) -> None:
        """IGA ①: a released latch starts the soil mode only with crawler contact."""
        if self._uses_ideal_contact():
            soil = self._soil_state()
            is_released = not self._state.in_crawler_zone
            if (not soil.is_liftoff_confirmed and is_released and not soil.is_soil_mode
                    and not self._ideal.source.has_crawler_contact):
                return
        super()._hold_crawler_zone_until_liftoff(reading)

    def _update_liftoff_window(self, reading) -> None:
        if self._variant_is(Variant.IZ) and IZ_CORRECTS_LOC_SAMPLES and self._ideal.source:
            corrected = self.geometry.clearance_corners_m(
                np.asarray(reading.rod_stroke_m, float) - self._ideal.source.z_m)
            self._ideal.corrected_by_t[float(reading.t_s)] = corrected
        if not self._uses_ideal_contact():
            super()._update_liftoff_window(reading)
            return
        if self._soil_state().is_liftoff_confirmed:
            return
        self._ideal.is_s1_record_only = True
        try:
            super()._update_liftoff_window(reading)  # S-1 window, record only
        finally:
            self._ideal.is_s1_record_only = False
        self._ideal_loc_step(reading)

    def _ideal_loc_step(self, reading) -> None:
        """IGA ②: the ideal LOC; ``t_P`` and ``W_hat`` of the first contact-free period."""
        from outrigger_sim.control.c2 import _PlateauSample

        source = self._ideal.source
        sample = _PlateauSample(
            t_s=float(reading.t_s), mean_motor_stroke_m=float(np.mean(reading.motor_stroke_m)),
            load_sum_N=float(np.sum(reading.cylinder_force_N)),
            corner_clearance_m=np.array(source.g_box_m, float),
            raw_attitude_rad=self._period_raw_attitude_rad())
        start = self._ideal.loc_rule.step(source.has_crawler_contact, loc_gap_m(source), sample)
        if start is None:
            return
        tail = [start] if start is sample else [start, sample]
        self._ideal.ideal_loc_s.append(float(reading.t_s))
        self._confirm_liftoff(reading.t_s, tail, start.load_sum_N)

    def _confirm_liftoff(self, t_s, tail, mean_load_N) -> None:
        ideal = self._ideal
        if ideal.is_s1_record_only:
            if ideal.s1_would_loc_s is None:
                ideal.s1_would_loc_s = float(t_s)
            return
        if self._variant_is(Variant.IZ) and IZ_CORRECTS_LOC_SAMPLES:
            tail = [self._corrected_sample(sample) for sample in tail]
        super()._confirm_liftoff(t_s, tail, mean_load_N)

    def _corrected_sample(self, sample):
        corrected = self._ideal.corrected_by_t.get(float(sample.t_s))
        return sample if corrected is None else replace(sample, corner_clearance_m=corrected)

    def _corner_bias_m(self, sample):
        if self._variant_is(Variant.IGA, Variant.IGB):
            return np.zeros(4)  # ④: no S-3 bias on the true gap
        return super()._corner_bias_m(sample)

    def _loc_anchor_bias_m(self, raw_bias_m, c_min_m):
        if self._variant_is(Variant.IGA, Variant.IGB):
            return None  # ④: no LOC anchor on the true gap
        return super()._loc_anchor_bias_m(raw_bias_m, c_min_m)

    def _watch_loc_revoke(self) -> None:
        """IGA ③: the P-S8-33 watch with the trigger "crawler contact for
        :data:`REVOKE_CONTACT_PERIODS` periods" (lifecycle, gate and stroke guard kept)."""
        if not self._uses_ideal_contact():
            super()._watch_loc_revoke()
            return
        from outrigger_sim.control.c2 import C2Phase

        state = self._state
        watch = state.loc_revoke_watch
        if watch is None:
            self._ideal.revoke_run.periods = 0
            return
        settings = self.config.loc_revoke
        reading = state.last_reading
        mean_stroke_m = float(np.mean(reading.motor_stroke_m))
        if (not self._soil_state().is_liftoff_confirmed or state.phase is not C2Phase.LEVEL
                or mean_stroke_m - watch.stroke_loc_m >= settings.watch_m):
            state.loc_revoke_watch = None
            return
        t_s = float(reading.t_s)
        load_N = float(np.sum(reading.cylinder_force_N))
        watch.loads.append((t_s, load_N))
        if not self._ideal.revoke_run.step(self._ideal.source.has_crawler_contact):
            return
        if settings.stroke_guard and self._is_revoke_stroke_guarded(reading):
            from outrigger_sim.control.c2 import LOC_REVOKE_SKIPPED_EVENT

            state.loc_revoke_watch = None
            state.loc_revoke_skips = (*state.loc_revoke_skips, t_s)
            self._add_event(t_s, f"{LOC_REVOKE_SKIPPED_EVENT}:stroke")
            return
        self._revoke_loc(t_s, load_N - watch.weight_estimate_N)

    def _clearance_corners_m(self, rod_stroke_m):
        source = self._ideal.source
        if self._uses_ideal_contact():
            return np.array(source.g_box_m, float)  # ④ c_k := g_box_k
        if self._variant_is(Variant.IZ) and source is not None:
            corners = self.geometry.clearance_corners_m(
                np.asarray(rod_stroke_m, dtype=float) - source.z_m)
            bias = self._active_corner_bias_m()
            return corners if bias is None else corners - bias
        return super()._clearance_corners_m(rod_stroke_m)

    def _diff_sink_rates_m_s(self):
        if not self._variant_is(Variant.IZ) or self._ideal.source is None:
            return super()._diff_sink_rates_m_s()
        if super()._diff_sink_rates_m_s() is None:
            return None
        return self._ideal_sink_rates_m_s()

    def _ideal_sink_rates_m_s(self):
        """rev1 R1-4: axis differences of the 1 s least-squares ``z`` slopes over the DSb75
        window (no gyro term); None before the window is full."""
        sink = self._state.diff_sink
        if sink is None or len(sink.strokes) < 2:
            return None
        times = [t_s for t_s, _ in sink.strokes]
        missing = [t_s for t_s in times if t_s not in self._ideal.z_by_t]
        if missing:
            raise RuntimeError(f"IZ: no sinkage for the DSb75 window times {missing[:3]}")
        z = [self._ideal.z_by_t[t_s] for t_s in times]
        return axis_differences(window_lsq_slopes(times, z))

    # --- records ------------------------------------------------------------------------
    def _stroke_corners_m(self, rod_stroke_m, sink_m=None):
        rod = np.asarray(rod_stroke_m, float)
        corners = self.geometry.clearance_corners_m(rod if sink_m is None else rod - sink_m)
        soil = self._state.soil
        if self.config.soil.enable and soil is not None and soil.has_corner_bias:
            corners = corners - soil.corner_bias_m
        return corners

    def _residuals_N(self, source: IdealSource, measurements) -> tuple[float, float]:
        mass = self._pressures.d1_imu_mass_kg()
        samples = measurements.imu_specific_force_samples_m_s2
        if mass is None or samples is None or source.f_z_bar_m_s2 is None:
            return math.nan, math.nan
        head_area, annulus = self.geometry.head_area_m2, self.geometry.annulus_area_m2

        def force_sum(head, rod):
            forces = np.asarray(head, float) * head_area
            return float(np.sum(forces if rod is None else forces - np.asarray(rod) * annulus))

        aligned = force_sum(source.p_bar_head_Pa, source.p_bar_rod_Pa) - mass * source.f_z_bar_m_s2
        instant = (force_sum(measurements.head_pressure_Pa, measurements.rod_pressure_Pa)
                   - mass * float(np.asarray(samples, float)[-1, 2]))
        return aligned, instant

    def _record_period(self, source: IdealSource, measurements, phase_before: str) -> None:
        ideal = self._ideal
        reading = self._state.last_reading
        rod = reading.rod_stroke_m
        r_parent = None
        r_ideal = None
        if self._state.diff_sink is not None:
            from outrigger_sim.control.c2 import C2Controller

            r_parent = C2Controller._diff_sink_rates_m_s(self)
            r_ideal = self._ideal_sink_rates_m_s() if r_parent is not None else None
        aligned, instant = self._residuals_N(source, measurements)
        values = {
            "t_s": source.t_s, "chi_cr": source.has_crawler_contact,
            "cr_max_N": round(source.cr_max_N, 3),
            "g_box": np.round(source.g_box_m, 7).tolist(),
            "g_min": round(float(np.min(source.g_box_m)), 7),
            "g_node_min": round(source.g_node_min_m, 7),
            "c_min": round(float(np.min(self._stroke_corners_m(rod))), 7),
            "c_corr_min": round(float(np.min(self._stroke_corners_m(rod, source.z_m))), 7),
            "z": np.round(source.z_m, 7).tolist(),
            "r_dsb": None if r_parent is None else np.round(r_parent, 7).tolist(),
            "r_dsb_ideal": None if r_ideal is None else np.round(r_ideal, 7).tolist(),
            "r_bar_aligned": _rounded(aligned, 1), "r_inst": _rounded(instant, 1),
            "p_bar_h": np.round(source.p_bar_head_Pa, 1).tolist(),
            "p_bar_r": (None if source.p_bar_rod_Pa is None
                        else np.round(source.p_bar_rod_Pa, 1).tolist()),
            "corner_h_plane": (None if source.corner_h_plane_m is None
                               else np.round(source.corner_h_plane_m, 7).tolist())}
        for name in PERIOD_FIELDS:
            ideal.periods[name].append(values[name])
        self._note_soil_and_loc(source)
        if not self._variant_is(Variant.IGA, Variant.IGB):
            self._shadow_loc_step(source, phase_before)


    def _note_soil_and_loc(self, source: IdealSource) -> None:
        ideal = self._ideal
        starts = list(self._state.soil_mode_starts)
        for start in starts[ideal.soil_starts_seen:]:
            ideal.soil_starts.append({**start, "chi_cr": source.has_crawler_contact})
        ideal.soil_starts_seen = len(starts)
        soil = self._state.soil
        is_loc = bool(soil is not None and soil.is_liftoff_confirmed)
        if is_loc and not ideal.was_loc:
            ideal.loc_onsets.append({"t_s": source.t_s, "chi_cr": source.has_crawler_contact,
                                     "g_box_min": float(np.min(source.g_box_m)),
                                     "g_node_min": source.g_node_min_m})
        ideal.was_loc = is_loc

    def _shadow_loc_step(self, source: IdealSource, phase_before: str) -> None:
        """SHD / IZ / S4: the IGA ② decision "would have been" (record only)."""
        ideal = self._ideal
        if ideal.shadow_loc_s is not None or phase_before != "level":
            return
        start = ideal.shadow_rule.step(source.has_crawler_contact, loc_gap_m(source),
                                       source.t_s)
        if start is not None:
            ideal.shadow_loc_s = source.t_s
            ideal.shadow_t_P_s = start

    def ideal_record(self) -> dict:
        """The controller part of the line's ``ideal`` block (plan 8.3)."""
        ideal = self._ideal
        first_loc = ideal.loc_onsets[0] if ideal.loc_onsets else None
        names = [event.name for event in self.events]
        pressure_counts: dict[str, int] = {}
        for name in names:
            if name.startswith(PRESSURE_EVENT_PREFIXES):
                key = name if name.startswith("INFO_PRESSURE_STEP") else name.split(":")[0]
                if key.startswith("INFO_PRESSURE_STEP"):
                    key = "INFO_PRESSURE_STEP:" + key.rsplit(":", 1)[-1]
                pressure_counts[key] = pressure_counts.get(key, 0) + 1
        margin = self.controller_margin_meta()
        return {
            "variant": self._ideal_settings.variant, "k1_arm": self._ideal_settings.k1_arm,
            "k1_order_gate_effective": bool(
                self.config.slope_clearance_margin.flat_soil_margin_order_gate),
            "disabled_margins": dict(self._ideal_disabled),
            "soil_mode_starts": ideal.soil_starts,
            "false_soil_mode": any(not start["chi_cr"] for start in ideal.soil_starts),
            "loc_onsets": ideal.loc_onsets,
            "t_loc_first_s": None if first_loc is None else first_loc["t_s"],
            "false_loc": bool(first_loc is not None and first_loc["chi_cr"]),
            "ideal_loc_s": list(ideal.ideal_loc_s),
            "shadow_ideal_loc_s": ideal.shadow_loc_s,
            "shadow_ideal_t_P_s": getattr(ideal, "shadow_t_P_s", None),
            "s1_would_loc_s": ideal.s1_would_loc_s,
            "loc_revokes": [list(entry) for entry in self._state.loc_revokes],
            "order_gate_decisions": margin["order_gate"]["decisions"],
            "flat_soil_margin_applied": bool(margin["flat_soil_margin_applied"]),
            "slope_margin_applied": bool(margin["is_applied"]),
            "pressure_event_counts": pressure_counts,
            "chunk_anomalies": ideal.chunk_anomalies[:20],
            "chunk_anomaly_count": len(ideal.chunk_anomalies),
            "last_chunk_mismatches": ideal.last_chunk_mismatches,
            "periods": ideal.periods}

    def controller_margin_meta(self) -> dict:
        return self.meta()["slope_clearance_margin"]


def _rounded(value: float, digits: int) -> float | None:
    return None if not math.isfinite(value) else round(value, digits)


def ideal_controller_class(base, settings: IdealSettings):
    """``IdealSensorC2``: the mixin over ``base`` (the harness's logged C2 controller)."""
    return type("IdealSensorC2", (IdealSensorMixin, base), {"_ideal_settings": settings})


def _project_class():
    from outrigger_sim.control import c2

    return c2.C2Controller


IdealSensorC2 = ideal_controller_class(_project_class(), IdealSettings(Variant.SHD.value))
"""The mixin over the project ``C2Controller`` (SHD; runs bind their own settings)."""


# ------------------------------------------------------------------------------- worker installs
_INSTALLED: dict = {}


def install_ideal(settings: IdealSettings) -> None:
    """Chunk hook and the ideal controller over ``verdict_runs``' logged controller.

    Raises:
        RuntimeError: Installed twice in one process.
    """
    if _INSTALLED:
        raise RuntimeError("ideal_sensor_targeted.install_ideal: already installed")
    import s9_soil_closed_loop as soil_loop
    import verdict_runs

    closed_loop = soil_loop._imports()[0]
    install_chunk_hook(closed_loop)
    _GEOMETRY_FUNCTIONS["rotation"] = closed_loop.rcc._R
    original = verdict_runs.install_logged_controller

    def install_logged_controller():
        c2 = original()
        c2.C2Controller = ideal_controller_class(c2.C2Controller, settings)
        _INSTALLED["class"] = c2.C2Controller
        return c2

    verdict_runs.install_logged_controller = install_logged_controller
    _INSTALLED["settings"] = settings


# ------------------------------------------------------------------------------- inputs
@dataclass
class KeySets:
    """The registered key lists (plan 4)."""

    sets: dict[str, list[str]]
    sha256: str


def load_key_sets(path: Path) -> tuple[KeySets | None, list[str]]:
    """Keys file sha256 and every set's list sha256 / count (plan 8.4)."""
    problems = []
    digest = file_sha256(path)
    if digest != KEYS_SHA256:
        problems.append(f"{Path(path).name} sha256 {digest} != {KEYS_SHA256}")
        return None, problems
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    sets = {}
    for name, expected in SET_SHA256.items():
        keys = list((data.get("sets") or {}).get(name, {}).get("keys") or [])
        is_unique = len(set(keys)) == len(keys)
        if list_sha256(keys) != expected or len(keys) != SET_COUNTS[name] or not is_unique:
            problems.append(f"set {name}: {len(keys)} keys, list sha256 {list_sha256(keys)}")
        sets[name] = keys
    union = sorted({key for name in UNION_P0_SETS for key in sets.get(name, [])})
    if len(union) != UNION_P0_COUNT or list_sha256(union) != UNION_P0_SHA256:
        problems.append(f"union P0: {len(union)} keys, sha256 {list_sha256(union)}")
    return KeySets(sets, digest), problems


def plan_problems(paths: list[Path]) -> list[str]:
    """Plan 8.4 with rev1: the registered plan and rev1, each against its ``.sha256``."""
    if len(paths) != len(PLAN_SHA256_LIST):
        return [f"--plan-file needs {len(PLAN_SHA256_LIST)} files (plan, rev1)"]
    problems = []
    for path, expected in zip(paths, PLAN_SHA256_LIST, strict=True):
        path = Path(path)
        sha_path = path.with_suffix(".sha256")
        if not path.exists() or not sha_path.exists():
            problems.append(f"missing {path} or {sha_path.name}")
            continue
        tokens = sha_path.read_text(encoding="utf-8").split()
        digest = file_sha256(path)
        if not tokens or tokens[0].lower() != expected or digest != expected:
            problems.append(f"{path.name} sha256 {digest}, .sha256 "
                            f"{tokens[0] if tokens else None}, expected {expected}")
    return problems


@dataclass
class References:
    """Stored lines: base files of K1 (``k1_judge.Bases``) and the K1 run lines."""

    bases: kj.Bases
    k1_lines: dict[str, dict[str, dict]]
    """sub-bundle -> key -> finished K1 line."""


def load_references(v5_dir: Path) -> tuple[References, list[str]]:
    """The stored lines of ``v5_dir`` (read only; the main checkout's when the run is in a
    worktree, ``--stored-root``)."""
    bases, problems = kj.load_bases(v5_dir)
    k1_lines: dict[str, dict[str, dict]] = {}
    k1_dir = v5_dir / kj.K1_DIR_RELATIVE
    lines = kj.read_run_lines(k1_dir) if k1_dir.exists() else []
    for path in sorted(k1_dir.glob("k1_*.jsonl")) if k1_dir.exists() else []:
        bases.paths[path.stem] = path
        bases.sha256[path.stem] = file_sha256(path)
    if not lines:
        problems.append(f"no K1 run lines in {k1_dir}")
    for line in lines:
        if rj.is_error(line):
            continue
        block = kj.k1_of(line)
        k1_lines.setdefault(block.get("sub_bundle"), {})[kj.key_of(line)] = line
    return References(bases, k1_lines), problems


def stored_reference(refs: References, set_name: str, arm: str, key: str) -> dict | None:
    """The stored line an SHD line of (set, arm, key) must reproduce (plan 6 V-3)."""
    kind, sub_bundle = SHD_REFERENCE[(set_name, arm)]
    if kind == "SC":
        return refs.bases.by_file.get("SC", {}).get(key)
    if kind == "L":
        return rj.stored_line(refs.bases.stored_l, key) if refs.bases.stored_l else None
    return refs.k1_lines.get(sub_bundle, {}).get(key)


def job_reference(refs: References, source: str, key: str) -> dict | None:
    if source == "RT":
        return rj.stored_line(refs.bases.stored_l, key) if refs.bases.stored_l else None
    return refs.bases.by_file.get(source, {}).get(key)


def base_jobs(source: str) -> list[dict]:
    return kt.base_jobs(source)


# ------------------------------------------------------------------------------- jobs
def bundle_keys(spec: BundleSpec, key_sets: KeySets) -> list[tuple[str, str]]:
    """(set, key) of a bundle in plan 4 order (I-0: the front of each list)."""
    out = []
    for set_name in spec.sets:
        keys = key_sets.sets[set_name]
        if spec.first_of_set is not None:
            keys = keys[: spec.first_of_set[set_name]]
        out += [(set_name, key) for key in keys]
    return out


def _entry(spec: BundleSpec, set_name: str, variant: str, arm: str, key: str,
           stored: dict | None, options: dict) -> dict:
    source = JOB_SOURCE[set_name]
    label = f"{variant}-{arm}"
    entry = rev._entry(spec.name, spec.las, label, record_done=RECORD_DONE[source])
    entry.update(attempt=2 if options.get("resume") else 1, resumed=bool(options.get("resume")))
    entry["ideal"] = {"bundle": spec.name, "set": set_name, "variant": variant, "k1_arm": arm,
                      "las_candidate": spec.las, "key": key, "job_source": source,
                      "stored_reference": list(SHD_REFERENCE[(set_name, arm)]),
                      "stored_commands_sha256": None if stored is None
                      else stored.get("commands_sha256"),
                      "trial": bool(options.get("trial")), "runner_mask": options.get("affinity"),
                      "runner_pool": options.get("pool"), "runner_workers": options.get("workers"),
                      "keys_sha256": KEYS_SHA256, "plan_sha256": list(PLAN_SHA256_LIST)}
    return entry


def bundle_jobs(spec: BundleSpec, variants: list[str], key_sets: KeySets, refs: References,
                options: dict, wanted: set[tuple[str, str, str]] | None = None) -> list[dict]:
    """Jobs of a bundle: SHD first (G-1 stops early), then the variants; arms of a key next to
    each other; VB rows first inside a variant (the longer runs start early)."""
    by_source = {}
    jobs = []
    for variant in variants:
        rows = []
        for set_name, key in bundle_keys(spec, key_sets):
            source = JOB_SOURCE[set_name]
            if source not in by_source:
                by_source[source] = {fb.fb_key(job): job for job in base_jobs(source)}
            job = by_source[source].get(key)
            if job is None:
                raise KeyError(f"{set_name} {key}: no job in source {source}")
            for arm in spec.arms:
                if wanted is not None and (variant, arm, key) not in wanted:
                    continue
                rows.append((job["setting"] != "VB", set_name, arm, key, job))
        rows.sort(key=lambda row: row[0])
        for _, set_name, arm, key, job in rows:
            stored = stored_reference(refs, set_name, arm, key)
            entry = _entry(spec, set_name, variant, arm, key, stored, options)
            jobs.append(rev._with_entry(job, entry, options.get("mask")))
    for index, job in enumerate(jobs):
        job["rev"]["id"] = index
    return jobs


def job_dict_problems(jobs: list[dict], refs: References) -> list[str]:
    """Every job dict = the job of the stored line its source tool wrote."""
    problems = []
    for job in jobs:
        ideal = job["rev"]["ideal"]
        line = job_reference(refs, ideal["job_source"], ideal["key"])
        if line is None:
            problems.append(f"{ideal['key']}: no stored {ideal['job_source']} line")
        elif rev._comparable_job(job) != rev._comparable_job(line["job"]):
            problems.append(f"{ideal['key']}: job dict differs from the stored line")
        if ideal["stored_commands_sha256"] is None:
            problems.append(f"{ideal['set']} {ideal['k1_arm']} {ideal['key']}: no stored hash")
    return problems


# ------------------------------------------------------------------------------- worker
IDENTITY_FILES = {**kt.IDENTITY_FILES,
                  "ideal_sensor_targeted.py": HERE / "ideal_sensor_targeted.py"}


def run_identity() -> dict:
    return fb.run_identity(files=IDENTITY_FILES)


def identity_problems(identity: dict) -> list[str]:
    """Run identity (plan 6: recorded like K1 Y; gated for a real run)."""
    problems = [f"dirty {name}" for name in identity["dirty_files"]]
    if identity["code_diff_sha256"] != fb.EMPTY_SHA256:
        problems.append(f"code_diff_sha256 {identity['code_diff_sha256']} is not empty")
    problems += fb.thread_problems(identity["threads"])
    if identity["threads"].get("MKL_THREADING_LAYER") != kj.THREAD_LAYER:
        problems.append(f"MKL_THREADING_LAYER {identity['threads'].get('MKL_THREADING_LAYER')}")
    return problems


def base_tag_of(job: dict, controller) -> str | None:
    import run_v5

    from outrigger_sim.hydraulics.v5_options import controller_tag

    _, options = run_v5.options_of(job["setting"], job.get("eta_v"))
    return controller_tag(options, controller.config)


def final_attitude_deg(plant) -> list[float]:
    return [math.degrees(value) for value in plant.attitude()]


def ideal_block(entry: dict, job: dict, plant, controller, line: dict) -> dict:
    """The line's ``ideal`` block (plan 8.3, rev1 R1-6)."""
    controller.check_k1_arm()
    ideal = entry["ideal"]
    base = base_tag_of(job, controller)
    record = controller.ideal_record()
    stored = ideal["stored_commands_sha256"]
    sp = getattr(getattr(plant, "soil", None), "sp", None)
    return {**ideal, "base_tag": base, "controller_tag": ideal_tag(base, ideal["variant"]),
            "line_tag_before": line.get("controller_tag"),
            "base_tag_matches_line": base == line.get("controller_tag"),
            "matches_stored": stored is not None and line["commands_sha256"] == stored,
            "thresholds": {"LOC_GAP_M": LOC_GAP_M, "LOC_GAP_HYST_M": LOC_GAP_HYST_M,
                           "LOC_DEBOUNCE_PERIODS": LOC_DEBOUNCE_PERIODS,
                           "REVOKE_CONTACT_PERIODS": REVOKE_CONTACT_PERIODS,
                           "LOC_GAP_REFERENCE": LOC_GAP_REFERENCE,
                           "IZ_CORRECTS_LOC_SAMPLES": IZ_CORRECTS_LOC_SAMPLES,
                           "crawler_contact": "F_cr > 0 (any 1 ms chunk end)"},
            "superstructure_weight_N": float(controller._reference_weight_N()),
            "final_attitude_deg": final_attitude_deg(plant),
            "soil_sp_final_m": None if sp is None else np.asarray(sp, float).tolist(),
            **record}


def run_ideal_job(job: dict) -> dict:
    """Worker: the K1 Y installs (``las_revA_targeted``) and the ideal controller, run, blocks."""
    t_start = time.perf_counter()
    entry = job.pop("rev")
    head = {"job": job, "rev": {**entry, "key": fb.fb_key(job)}}
    try:
        import run_v5  # noqa: F401  (sys.path and thread variables first)

        identity = run_identity()
        revA._install_all(entry)
        install_ideal(IdealSettings(entry["ideal"]["variant"], entry["ideal"]["k1_arm"]))
    except Exception as exc:  # recorded as an error line; the batch decides
        return {**head, "error": f"install: {exc!r}", "tb": traceback.format_exc()[-3000:],
                "wall_s": round(time.perf_counter() - t_start, 1)}
    import run_v5

    line = run_v5.run_one(job)
    if "error" in line:
        return {**line, "rev": head["rev"]}
    try:
        revA._add_blocks(line, entry, job, identity)
        plant, controller = fb._run_objects(job)
        block = ideal_block(entry, job, plant, controller, line)
    except Exception as exc:
        return {**head, "error": f"metrics: {exc!r}", "tb": traceback.format_exc()[-3000:],
                "wall_s": round(time.perf_counter() - t_start, 1)}
    line["controller_tag"] = block["controller_tag"]
    line["rev"].update(id=entry["id"], attempt=entry["attempt"], resumed=entry["resumed"],
                       controller_tag=block["controller_tag"], ideal=entry["ideal"])
    line["ideal"] = {**block, "identity": identity}
    return line


# ------------------------------------------------------------------------------- batch
@dataclass
class BatchState:
    stop: str | None = None
    runs: int = 0
    errors: int = 0
    skipped: int = 0
    attempts: dict = field(default_factory=dict)


def line_problems(record: dict, identity: dict) -> tuple[str | None, list[str]]:
    """(stop reason, notes) of a finished line: identity or tag change stops (as K1 SK-1),
    an SHD hash different from the stored one stops (plan 6 G-1)."""
    ideal = record.get("ideal") or {}
    problems = fb.identity_mismatch(ideal.get("identity"), identity)
    if problems:
        return f"run identity changed during the batch: {problems[:3]}", []
    tag = record.get("controller_tag")
    if tag != ideal_tag(ideal.get("base_tag"), ideal.get("variant")):
        return f"{ideal.get('key')}: controller_tag {tag!r} is not the IDEAL tag", []
    notes = []
    if not ideal.get("base_tag_matches_line"):
        notes.append(f"base tag {ideal.get('base_tag')} != line {ideal.get('line_tag_before')}")
    if ideal.get("variant") == Variant.SHD.value and not ideal.get("matches_stored"):
        return (f"G-1 {ideal.get('k1_arm')} {ideal.get('key')}: SHD hash "
                f"{record['commands_sha256'][:12]} != stored "
                f"{str(ideal.get('stored_commands_sha256'))[:12]}"), notes
    return None, notes


def _variant_of(job_or_record: dict) -> str:
    return job_or_record["rev"]["ideal"]["variant"]


def run_batch(jobs: list[dict], paths: dict[str, Path], workers: int, identity: dict,
              worker=None) -> BatchState:
    """Spawned workers (one run each); every line into its variant's new file; an error line
    runs once more, a second error stops; :func:`line_problems` stops."""
    import verdict_runs

    worker = worker or run_ideal_job
    verdict_runs.warm_numba_cache()
    state = BatchState()
    jobs_by_id = {job["rev"]["id"]: job for job in jobs}
    pending = list(jobs)
    results: queue.Queue = queue.Queue()
    in_flight = 0
    handles = {}
    try:
        for variant, path in paths.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            handles[variant] = path.open("x", encoding="utf-8")
        with get_context("spawn").Pool(workers, maxtasksperchild=1) as pool:

            def submit(job: dict) -> None:
                nonlocal in_flight
                in_flight += 1
                pool.apply_async(worker, (json.loads(json.dumps(job)),), callback=results.put,
                                 error_callback=lambda exc, job=job: results.put(
                                     {"job": {k: v for k, v in job.items() if k != "rev"},
                                      "rev": job["rev"], "error": f"pool: {exc!r}",
                                      "wall_s": 0.0}))

            while state.stop is None and (pending or in_flight):
                while pending and in_flight < workers:
                    submit(pending.pop(0))
                if not in_flight:
                    break
                record = results.get()
                in_flight -= 1
                record.setdefault("job", {}).pop("mask", None)
                handle = handles[record["rev"]["ideal"]["variant"]]
                handle.write(json.dumps(record, default=rev._json_default) + "\n")
                handle.flush()
                state.runs += 1
                _handle(record, jobs_by_id, state, identity, pending, len(jobs))
            if state.stop is not None:
                pool.terminate()
    finally:
        for handle in handles.values():
            handle.close()
    state.skipped += len(pending)
    return state


def _handle(record, jobs_by_id, state: BatchState, identity, pending, total) -> None:
    rev_entry = record.get("rev") or {}
    ideal = rev_entry.get("ideal") or {}
    label = f"{state.runs}/{total} {ideal.get('variant')} {ideal.get('k1_arm')} {ideal.get('key')}"
    if "error" in record:
        state.errors += 1
        job_id = rev_entry.get("id")
        print(f"{label}: ERROR {record['error'][:200]}", flush=True)
        if state.attempts.get(job_id, 1) >= 2:
            state.stop = f"second error of {ideal.get('key')} ({ideal.get('variant')})"
        else:
            state.attempts[job_id] = 2
            job = jobs_by_id[job_id]
            job["rev"]["attempt"] = 2
            pending.insert(0, job)
        return
    stop, notes = line_problems(record, identity)
    block = record.get("ideal") or {}
    print(f"{label}: {(record.get('d1') or {}).get('verdict')} "
          f"{record['commands_sha256'][:12]} stored-match {block.get('matches_stored')} "
          f"{record.get('wall_s')}s{' NOTE ' + str(notes) if notes else ''}", flush=True)
    if stop:
        state.stop = stop


# ------------------------------------------------------------------------------- gates, CLI
def out_name(bundle: str, variant: str, is_resume: bool = False) -> str:
    return f"ideal_{bundle.replace('-', '')}_{variant}{'_resume' if is_resume else ''}.jsonl"


def read_lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(text) for text in path.read_text(encoding="utf-8").splitlines() if text]


def g1_gate_problems(ideal_dir: Path) -> list[str]:
    """Plan 5 / 6 G-1: I-0 has 14 finished SHD lines matching their stored hashes."""
    lines = read_lines(ideal_dir / out_name("I-0", "SHD"))
    lines += read_lines(ideal_dir / out_name("I-0", "SHD", True))
    finished = {}
    for line in lines:
        if "error" not in line:
            finished[(line.get("ideal") or {}).get("key")] = line
    problems = []
    if len(finished) != BUNDLE_COUNTS["I-0"]:
        problems.append(f"I-0: {len(finished)} finished lines, {BUNDLE_COUNTS['I-0']} needed")
    problems += [f"I-0 {key}: SHD hash differs from the stored one"
                 for key, line in finished.items() if not line["ideal"].get("matches_stored")]
    return problems


def resume_wanted(spec: BundleSpec, variants: list[str], ideal_dir: Path
                  ) -> set[tuple[str, str, str]]:
    """(variant, arm, key) whose bundle file holds an error line and no finished line."""
    wanted = set()
    for variant in variants:
        lines = read_lines(ideal_dir / out_name(spec.name, variant))
        errors, finished = set(), set()
        for line in lines:
            ideal = (line.get("rev") or {}).get("ideal") or line.get("ideal") or {}
            item = (variant, ideal.get("k1_arm"), ideal.get("key"))
            (errors if "error" in line else finished).add(item)
        wanted |= errors - finished
    return wanted


def parse_variants(spec: BundleSpec, text: str | None) -> list[str]:
    variants = list(spec.variants) if not text else [value.strip() for value in text.split(",")]
    unknown = [value for value in variants if value not in spec.variants]
    if unknown:
        raise ValueError(f"{spec.name} has no variants {unknown} (allowed {spec.variants})")
    return sorted(variants, key=list(Variant.__members__).index)


V5_RELATIVE = Path("06_analysis") / "03_hydraulic" / "coupled" / "v5"
"""The v5 folder below a checkout root (``--stored-root``)."""


@dataclass
class Prepared:
    """What a run needs after the gates."""

    jobs: list[dict]
    paths: dict[str, Path]
    identity: dict
    refs: References
    out_dir: Path
    record_stem: str


def stored_v5_dir(args) -> Path:
    return Path(args.stored_root) / V5_RELATIVE


def _selected(spec: BundleSpec, variants: list[str], key_sets: KeySets, args,
              out_dir: Path) -> set[tuple[str, str, str]] | None:
    wanted = None
    if args.resume:
        wanted = resume_wanted(spec, variants, out_dir)
        print(f"resume keys: {sorted(wanted)}", flush=True)
    if args.keys:
        keys = set(args.keys.split(","))
        wanted = {(variant, arm, key) for variant in variants for arm in spec.arms
                  for _, key in bundle_keys(spec, key_sets) if key in keys}
    return wanted


def _output_problems(paths: dict[str, Path], bundle: str, out_dir: Path, args) -> list[str]:
    problems = [f"output exists (new files only): {path}" for path in paths.values()
                if path.exists()]
    if not args.resume and args.trial_out is None:
        problems += [f"bundle file exists (use --resume): {out_dir / out_name(bundle, variant)}"
                     for variant in paths if (out_dir / out_name(bundle, variant)).exists()]
    return problems


def _prepare(args) -> Prepared:
    """Jobs, output paths, identity and references (ValueError / KeyError on input errors)."""
    is_trial = args.trial_out is not None
    if (args.keys or args.limit is not None) and not is_trial:
        raise ValueError("--keys / --limit only with --trial-out")
    spec = BUNDLES[args.bundle]
    variants = parse_variants(spec, args.variant)
    key_sets, problems = load_key_sets(args.keys_file)
    problems += plan_problems(args.plan_file)
    if problems:
        raise ValueError(f"keys / plan files: {problems}")
    refs, problems = load_references(stored_v5_dir(args))
    if problems:
        raise ValueError(f"stored files: {problems[:5]}")
    import run_v5  # noqa: F401  (puts 03_src on sys.path before the preset check)

    fb.check_preset_las()
    identity = run_identity()
    out_dir = Path(args.trial_out if is_trial else args.out_dir)
    if is_trial and out_dir.resolve().is_relative_to(Path(args.out_dir).resolve()):
        raise ValueError("--trial-out must lie outside the ideal output folder")
    if not is_trial:
        problems = identity_problems(identity)
        if args.bundle == "I-1":
            problems += g1_gate_problems(out_dir)
        if problems:
            raise ValueError(f"gates before {args.bundle}: {problems}")
    options = {"mask": None if args.affinity is None else int(args.affinity, 16),
               "affinity": args.affinity, "pool": args.pool, "workers": args.workers,
               "resume": args.resume, "trial": is_trial}
    wanted = _selected(spec, variants, key_sets, args, out_dir)
    jobs = bundle_jobs(spec, variants, key_sets, refs, options, wanted)
    problems = job_dict_problems(jobs, refs)
    if problems:
        raise ValueError(f"job dicts / stored hashes: {problems[:5]}")
    jobs = jobs if args.limit is None else jobs[: args.limit]
    if not jobs:
        raise ValueError("no runs selected")
    present = sorted({_variant_of(job) for job in jobs}, key=list(Variant.__members__).index)
    paths = {variant: out_dir / out_name(args.bundle, variant, args.resume)
             for variant in present}
    problems = _output_problems(paths, args.bundle, out_dir, args)
    if problems:
        raise ValueError(str(problems))
    stem = out_name(args.bundle, "run", args.resume).removesuffix(".jsonl")
    return Prepared(jobs, paths, identity, refs, out_dir, stem)


def run_record(prepared: Prepared, args, moment: str, state: BatchState | None = None) -> dict:
    """The run meta (start / end): commit and clean state, stored inputs and their sha256,
    the outputs' sha256 at the end (to compare after moving them to the main checkout)."""
    identity = run_identity()
    record = {"moment": moment, "time": time.strftime("%Y-%m-%d %H:%M:%S %z"),
              "bundle": args.bundle, "argv": sys.argv[1:], "git_head": identity["git_head"],
              "git_clean": not identity["git_dirty"] and
              identity["code_diff_sha256"] == fb.EMPTY_SHA256,
              "identity": identity, "stored_root": str(args.stored_root),
              "stored_files": {name: {"path": str(prepared.refs.bases.paths.get(name)),
                                      "sha256": sha}
                               for name, sha in sorted(prepared.refs.bases.sha256.items())},
              "keys_sha256": KEYS_SHA256, "plan_sha256": list(PLAN_SHA256_LIST),
              "pool": args.pool, "affinity": args.affinity, "workers": args.workers,
              "runs_planned": len(prepared.jobs)}
    if state is not None:
        record.update(runs=state.runs, errors=state.errors, skipped=state.skipped,
                      stop=state.stop,
                      outputs={path.name: file_sha256(path)
                               for path in prepared.paths.values() if path.exists()})
    return record


def write_run_records(prepared: Prepared, args, state: BatchState | None) -> None:
    """``<stem>.run.json`` (start, then end) and, at the end, ``<stem>.sha256`` (sha256sum
    lines of the output files)."""
    meta_path = prepared.out_dir / f"{prepared.record_stem}.run.json"
    stored = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    moment = "start" if state is None else "end"
    stored[moment] = run_record(prepared, args, moment, state)
    prepared.out_dir.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(stored, indent=1), encoding="utf-8")
    if state is not None:
        lines = [f"{sha}  {name}" for name, sha in stored[moment]["outputs"].items()]
        (prepared.out_dir / f"{prepared.record_stem}.sha256").write_text(
            "\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _run_command(args) -> int:
    try:
        prepared = _prepare(args)
    except (KeyError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"input error: {exc!r}")
        print(json.dumps({"bundle": args.bundle, "stop": "input", "reason": str(exc)}))
        return 2
    identity = prepared.identity
    print(f"run identity: {identity['git_head']} dirty {identity['git_dirty']} code_diff "
          f"{identity['code_diff_sha256'][:12]}; {args.bundle}: {len(prepared.jobs)} runs -> "
          f"{[str(path) for path in prepared.paths.values()]}", flush=True)
    write_run_records(prepared, args, None)
    state = run_batch(prepared.jobs, prepared.paths, args.workers, identity)
    write_run_records(prepared, args, state)
    summary = {"bundle": args.bundle, "out": [str(path) for path in prepared.paths.values()],
               "runs": state.runs, "errors": state.errors, "skipped": state.skipped,
               "stop": state.stop}
    print(json.dumps(summary))
    return 1 if state.stop or state.skipped else 0


def _list_command(args) -> int:
    key_sets, problems = load_key_sets(args.keys_file)
    problems += plan_problems(args.plan_file)
    if problems:
        print(f"input error: {problems}")
        print(json.dumps({"stop": "input", "reasons": problems}))
        return 2
    refs, problems = load_references(stored_v5_dir(args))
    if problems:
        print(f"input error: {problems[:5]}")
        print(json.dumps({"stop": "input", "reasons": problems[:5]}))
        return 2
    mismatches = []
    for name in args.bundle:
        spec = BUNDLES[name]
        jobs = bundle_jobs(spec, list(spec.variants), key_sets, refs, {})
        print(f"{name}: {len(jobs)} runs ({len(spec.variants)} variants x "
              f"{len(bundle_keys(spec, key_sets))} keys x {len(spec.arms)} arms)")
        if len(jobs) != BUNDLE_COUNTS[name]:
            mismatches.append(f"{name}: {len(jobs)} runs, expected {BUNDLE_COUNTS[name]}")
        mismatches += job_dict_problems(jobs, refs)
    for problem in mismatches:
        print(f"MISMATCH {problem}")
    print(json.dumps({"bundles": args.bundle, "problems": len(mismatches)}))
    return 1 if mismatches else 0


def _parse_args(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("list", "run"):
        command = sub.add_parser(name)
        if name == "list":
            command.add_argument("--bundle", nargs="+", choices=tuple(BUNDLES),
                                 default=list(BUNDLES))
        else:
            command.add_argument("--bundle", required=True, choices=tuple(BUNDLES))
            command.add_argument("--variant", default=None,
                                 help="comma-separated codes (default: the bundle's)")
            command.add_argument("--workers", type=int, default=4)
            command.add_argument("--affinity", default=None, help="hex mask of every worker")
            command.add_argument("--pool", default=None, choices=("P", "E", "mixed"),
                                 help="core pool label of the mask (recorded only)")
            command.add_argument("--resume", action="store_true",
                                 help="re-run the keys whose only line is an error line")
            command.add_argument("--out-dir", type=Path, default=IDEAL_DIR,
                                 help="result folder (default: this checkout's v5/las/ideal)")
            command.add_argument("--trial-out", type=Path, default=None,
                                 help="trial folder outside --out-dir (never judged)")
            command.add_argument("--keys", default=None, help="trial only: comma-separated")
            command.add_argument("--limit", type=int, default=None, help="trial only")
        command.add_argument("--stored-root", type=Path, default=ROOT,
                             help="checkout root whose v5 folder holds the stored lines "
                                  "(the main checkout when running in a worktree)")
        command.add_argument("--keys-file", type=Path, default=KEYS_PATH)
        command.add_argument("--plan-file", type=Path, nargs=2,
                             default=[PLAN_PATH, PLAN_REV1_PATH],
                             help="registered plan and rev1 (each checked with its .sha256)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command == "run":
        return _run_command(args)
    try:
        return _list_command(args)
    except (KeyError, OSError, ValueError) as exc:
        print(f"input error: {exc!r}")
        print(json.dumps({"stop": "input", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
