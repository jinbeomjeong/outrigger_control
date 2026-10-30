"""Out-of-sample cases of the B5 baseline comparison (control-expert design 2026-10-30).

100 cases outside study 1 (``s9_soil_slope.build_cases``, 177) and the G6 screen
(``r72_g6_screen``, 116), in ten batches T1 .. T10 (pad B and F_s 4 kN unless the batch says
otherwise; angles are ``s9_soil_slope.SLOPES_DEG`` x k):

  T1  middle  x {G1, J1, J2, S1} x 7 directions                                   28
  T2  middle  x {J1, J2, S1} x {nose_down, roll_pos, edge_nd} @ k 0.75             9
  T3  top F_s 8 x {J1, J2, S1} x {nose_up, roll_neg, edge_nu, rpB}               12
  T4  pad A bottom x {J1, J2} x {nose_down, roll_pos, edge_nd, rpB}                8
  T5  top x {J1, J2} x {nose_down, roll_pos, edge_nd} x k 0.625 / 0.9375          12
  T6  top x {J1, J2} x {roll_neg, nose_up, edge_nu} @ k 0.75                       6
  T7  g6x G1 + {J1, J2, S1} @ {FL, FR, RL, RR}, middle, F_s 4                     12
  T8  g6x G1 + {J1, J2} @ {FR, RL}, top, F_s 8                                     4
  T9  g6x rigid + {J1, J2} @ {FL, RR}, middle, F_s 4                               4
  T10 rigid middle x {flat, nose_down, nose_up, roll_pos, edge_nd}                 5

Case ids: slope harness ``X|<soil>|<pad>|<level>|<roll>,<pitch>|Fs<f>`` (deg, %g), one weak
pad on the r72 harness ``G|g6x|<base>+<weak>@<leg>|<level>|Fs<f>``.
"""

from __future__ import annotations

from dataclasses import dataclass

import s9_soil_slope as slope

OOS_SLOPE_TAG = "X"
OOS_SLOPE_PREFIX = f"{OOS_SLOPE_TAG}|"
OOS_G6_TAG = "g6x"
OOS_G6_PREFIX = f"G|{OOS_G6_TAG}|"
SLOPE_HARNESS = "slope"
G6_HARNESS = "g6"
G6_PAD = "B"
"""The r72 harness runs pad B only."""
LEGS = ("FL", "FR", "RL", "RR")
LEVELS = (slope.LEVEL_TOP, slope.LEVEL_MIDDLE, slope.LEVEL_BOTTOM)
SLOPE_SOILS = (*slope.SOILS, slope.RIGID)
ANGLE_DIGITS = 4
"""Rounding of k x direction angle (as ``s9_soil_slope._scaled_slope``)."""
SEVEN_DIRECTIONS = ("nose_down", "nose_up", "roll_pos", "roll_neg", "edge_nd", "edge_nu", "rpB")
NO_SETTLE_ROW = "no_table_row"


class NoSettleRowError(ValueError):
    """A soil case of the slope harness has no row in the dynamics settle table."""


@dataclass(frozen=True)
class SlopeBatch:
    """Slope-harness batch: every soil x direction x k at one level, pad and F_s."""

    name: str
    level: str
    soils: tuple[str, ...]
    directions: tuple[str, ...]
    ks: tuple[float, ...] = (1.0,)
    pad: str = "B"
    fs_kN: float = slope.FS_KN


@dataclass(frozen=True)
class WeakPadBatch:
    """r72 batch: one weak soil under one pad of a base soil (pad B)."""

    name: str
    base: str
    weak_soils: tuple[str, ...]
    legs: tuple[str, ...]
    level: str
    fs_kN: float = slope.FS_KN


SLOPE_BATCHES = (
    SlopeBatch("T1", slope.LEVEL_MIDDLE, ("G1", "J1", "J2", "S1"), SEVEN_DIRECTIONS),
    SlopeBatch("T2", slope.LEVEL_MIDDLE, ("J1", "J2", "S1"), ("nose_down", "roll_pos", "edge_nd"),
               ks=(0.75,)),
    SlopeBatch("T3", slope.LEVEL_TOP, ("J1", "J2", "S1"), ("nose_up", "roll_neg", "edge_nu", "rpB"),
               fs_kN=8.0),
    SlopeBatch("T4", slope.LEVEL_BOTTOM, ("J1", "J2"),
               ("nose_down", "roll_pos", "edge_nd", "rpB"), pad="A"),
    SlopeBatch("T5", slope.LEVEL_TOP, ("J1", "J2"), ("nose_down", "roll_pos", "edge_nd"),
               ks=(0.625, 0.9375)),
    SlopeBatch("T6", slope.LEVEL_TOP, ("J1", "J2"), ("roll_neg", "nose_up", "edge_nu"),
               ks=(0.75,)),
    SlopeBatch("T10", slope.LEVEL_MIDDLE, (slope.RIGID,),
               ("flat", "nose_down", "nose_up", "roll_pos", "edge_nd")),
)
WEAK_PAD_BATCHES = (
    WeakPadBatch("T7", "G1", ("J1", "J2", "S1"), LEGS, slope.LEVEL_MIDDLE),
    WeakPadBatch("T8", "G1", ("J1", "J2"), ("FR", "RL"), slope.LEVEL_TOP, fs_kN=8.0),
    WeakPadBatch("T9", slope.RIGID, ("J1", "J2"), ("FL", "RR"), slope.LEVEL_MIDDLE),
)
BATCH_ORDER = ("T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10")


# ------------------------------------------------------------------------------------ ids
def slope_case_id(soil: str, pad: str, level: str, roll_deg: float, pitch_deg: float,
                  fs_kN: float) -> str:
    """``X|<soil>|<pad>|<level>|<roll>,<pitch>|Fs<f>`` (deg and kN as %g)."""
    return f"{OOS_SLOPE_PREFIX}{soil}|{pad}|{level}|{roll_deg:g},{pitch_deg:g}|Fs{fs_kN:g}"


def weak_pad_case_id(base: str, weak: str, leg: str, level: str, fs_kN: float) -> str:
    """``G|g6x|<base>+<weak>@<leg>|<level>|Fs<f>`` (the b5 g6 harness id)."""
    return f"{OOS_G6_PREFIX}{base}+{weak}@{leg}|{level}|Fs{fs_kN:g}"


def _scaled_angles_deg(direction: str, k: float) -> tuple[float, float]:
    roll_deg, pitch_deg = slope.SLOPES_DEG[direction]
    return round(k * roll_deg, ANGLE_DIGITS), round(k * pitch_deg, ANGLE_DIGITS)


def _slope_batch_ids(batch: SlopeBatch) -> list[str]:
    ids = []
    for soil in batch.soils:
        for direction in batch.directions:
            for k in batch.ks:
                roll_deg, pitch_deg = _scaled_angles_deg(direction, k)
                ids.append(slope_case_id(soil, batch.pad, batch.level, roll_deg, pitch_deg,
                                         batch.fs_kN))
    return ids


def _weak_pad_batch_ids(batch: WeakPadBatch) -> list[str]:
    return [weak_pad_case_id(batch.base, weak, leg, batch.level, batch.fs_kN)
            for weak in batch.weak_soils for leg in batch.legs]


def _build_oos_batches() -> dict[str, tuple[str, ...]]:
    ids_by_batch = {batch.name: tuple(_slope_batch_ids(batch)) for batch in SLOPE_BATCHES}
    ids_by_batch.update({batch.name: tuple(_weak_pad_batch_ids(batch))
                         for batch in WEAK_PAD_BATCHES})
    return {name: ids_by_batch[name] for name in BATCH_ORDER}


OOS_BATCH_IDS: dict[str, tuple[str, ...]] = _build_oos_batches()
"""Case ids per batch, T1 .. T10."""
OOS_CASES: tuple[str, ...] = tuple(case_id for ids in OOS_BATCH_IDS.values() for case_id in ids)
"""The 100 out-of-sample case ids (``--cases oos``), batch order."""


def is_oos_id(case_id: str) -> bool:
    """An out-of-sample id (slope ``X|...`` or weak pad ``G|g6x|...``)."""
    return case_id.startswith((OOS_SLOPE_PREFIX, OOS_G6_PREFIX))


def oos_batch(case_id: str) -> str | None:
    """Batch name (``"T1"`` .. ``"T10"``) of a listed out-of-sample id, None otherwise."""
    for name, ids in OOS_BATCH_IDS.items():
        if case_id in ids:
            return name
    return None


# -------------------------------------------------------------------------------- parsing
def parse_slope_case(case_id: str) -> slope.SlopeCase:
    """``SlopeCase(group="X", ...)`` of a ``X|<soil>|<pad>|<level>|<roll>,<pitch>|Fs<f>`` id.

    Raises:
        ValueError: The id does not have that form or names an unknown soil, pad or level.
    """
    parts = case_id.split("|")
    if len(parts) != 6 or parts[0] != OOS_SLOPE_TAG or not parts[5].startswith("Fs"):
        raise ValueError(f"{case_id}: expected X|<soil>|<pad>|<level>|<roll>,<pitch>|Fs<f>")
    _, soil, pad, level, angles, fs_text = parts
    angle_texts = angles.split(",")
    if len(angle_texts) != 2:
        raise ValueError(f"{case_id}: angles must be '<roll>,<pitch>' in deg, got {angles!r}")
    if soil not in SLOPE_SOILS or pad not in slope.PADS or level not in LEVELS:
        raise ValueError(f"{case_id}: soil {soil!r} / pad {pad!r} / level {level!r} unknown "
                         f"(soils {SLOPE_SOILS}, pads {slope.PADS}, levels {LEVELS})")
    roll_deg, pitch_deg = (float(text) for text in angle_texts)
    return slope.SlopeCase(group=OOS_SLOPE_TAG, soil=soil, pad=pad, level=level,
                           slope_name=angles, roll_deg=roll_deg, pitch_deg=pitch_deg,
                           fs_kN=float(fs_text[2:]))


def slope_case_payload(case_id: str, settle_rows: dict, *,
                       allow_no_settle_row: bool = False) -> dict:
    """``SlopeCase.to_dict()`` of an ``X|...`` id with its settle-table row attached.

    Args:
        case_id: ``X|...`` id; it also becomes the payload ``id``.
        settle_rows: ``hook_harness`` rows of the dynamics settle table.
        allow_no_settle_row: Run a soil case without a row uncorrected (flat P0 settle).

    Raises:
        NoSettleRowError: A soil case has no row and ``allow_no_settle_row`` is False.
        ValueError: Malformed id (:func:`parse_slope_case`).
    """
    (case,) = slope.attach_settle_table([parse_slope_case(case_id)], settle_rows)
    if case.settle_table_status == NO_SETTLE_ROW and not allow_no_settle_row:
        raise NoSettleRowError(f"{case_id}: no settle-table row {case.harness_settle_key!r} "
                               "(--allow-no-settle-row runs it uncorrected, "
                               "--skip-no-settle-row leaves it out)")
    payload = case.to_dict()
    payload["id"] = case_id
    return payload


# ------------------------------------------------------------------------------- overlap
def _rounded_key(harness: str, soil: str, pad: str, level: str, roll_deg: float,
                 pitch_deg: float, fs_kN: float) -> tuple:
    return (harness, soil, pad, level, round(roll_deg, ANGLE_DIGITS),
            round(pitch_deg, ANGLE_DIGITS), round(fs_kN, ANGLE_DIGITS))


def g6_harness_key(g6_key: str) -> tuple:
    """(harness, soil, pad, level, roll, pitch, F_s) of an r72 key
    ``<tag>|<soil>|<level>|Fs<f>``."""
    _tag, soil, level, fs_text = g6_key.split("|")
    return _rounded_key(G6_HARNESS, soil, G6_PAD, level, 0.0, 0.0, float(fs_text[2:]))


def slope_harness_key(case: slope.SlopeCase) -> tuple:
    """(harness, soil, pad, level, roll, pitch, F_s) of a slope-harness case."""
    return _rounded_key(SLOPE_HARNESS, case.soil, case.pad, case.level, case.roll_deg,
                        case.pitch_deg, case.fs_kN)


def oos_harness_key(case_id: str) -> tuple:
    """Harness key of an out-of-sample id.

    Raises:
        ValueError: Not an out-of-sample id.
    """
    if case_id.startswith(OOS_SLOPE_PREFIX):
        return slope_harness_key(parse_slope_case(case_id))
    if case_id.startswith(OOS_G6_PREFIX):
        return g6_harness_key(case_id[len("G|"):])
    raise ValueError(f"{case_id}: not an out-of-sample id")


def in_sample_keys(slope_cases: list[slope.SlopeCase], g6_keys: list[str]) -> set[tuple]:
    """Harness keys of study 1 (slope cases) and the G6 screen (r72 keys)."""
    keys = {slope_harness_key(case) for case in slope_cases}
    keys |= {g6_harness_key(key) for key in g6_keys}
    return keys


def check_no_overlap(case_ids: list[str], in_sample: set[tuple]) -> None:
    """Reject out-of-sample ids that repeat an in-sample harness key or each other.

    Raises:
        ValueError: An id hits ``in_sample`` or two ids share a key.
    """
    seen: dict[tuple, str] = {}
    problems = []
    for case_id in case_ids:
        key = oos_harness_key(case_id)
        if key in in_sample:
            problems.append(f"{case_id} repeats in-sample {key}")
        elif key in seen:
            problems.append(f"{case_id} repeats {seen[key]}")
        seen.setdefault(key, case_id)
    if problems:
        raise ValueError("out-of-sample overlap: " + "; ".join(problems))
