"""K-2 run-side records of the reduced harness (``k2_touch_creep_rules.md`` 9.1-3, I-9, SH-1, SH-2, 5.3).

``acc_d8.py`` imports this module only when a run names a K-2 arm (``--k2``) or a dissipation arm
(``--aug``); a run without them does not load it and stays as before. The recorders copy plant
and controller state after each call and change nothing (the ``d8x_diag.py`` way of ``6f2f7cb``).

Block ``k2`` of a row (:func:`k2_fields`, raw floats; the top-level row keys ``touch_creep_latch``,
``series_file``, ``aug_arm`` and ``is_kplant`` are written by ``acc_d8.py``, names of the path-2
field map ``k2_recount.DEFAULT_FIELDS["harness_row"]``):

    touch_creep_latch            bool, the effective switch of the controller config
    touch_start_s                first controller period in TOUCH
    touch_length_s               t_touch - touch_start_s
    latches                      controller_meta.touch_creep_latch.latches (leg, t_s, reason,
                                 window_mean_N, window_min_N, creep_travel_m)
    SH1_lift_chunks_after_latch  per leg, 1 ms chunks with pad normal <= 0 strictly after the leg's
                                 own INFO_TOUCH_CREEP_LATCH and strictly before t_touch (None per
                                 leg without a latch)
    SH2_rate_amp_deg_s           max |rate - mean| of the roll / pitch body rate over the chunks of
                                 [t_touch - 0.3 s, t_touch) (two at least)
    J3_from_first_all4           pad-lift chunks from the first chunk with all four pad normals > 0
    t_first_all4_s

The series file (``<series dir>/<series_file>``) holds ``t_s``, ``pad_normal_min_N`` (the J3 pad normal
per 1 ms chunk) and ``body_rate_rad_s`` (``FlexPlant.w`` after the chunk), the keys of
``k2_recount.DEFAULT_FIELDS["series"]``.

More keys of the ``k2`` block:

    event_counts                 INFO_TOUCH_CREEP_LATCH / _CAP, INFO_TOUCH_DIP_HELD,
                                 INFO_TOUCH_TWIST_HOLD, INFO_LIFT_PAUSED, INFO_LIFTOFF_SLOW
    dhat_N                       C4G2 D_hat (``controller_meta.touch_twist_hold.twist_load_estimate_N``,
                                 the mean n^T F of the last 3 TOUCH samples); None without it
    dhat_window_open_legs        legs whose valve output |u| > 1e-6 m/s on a 1 ms chunk of the D_hat
                                 window (t_touch - 0.3 s, t_touch] (rules rev1 4 (a))
    dhat_window_stroke_mm        per leg, motor stroke gained over that window [mm] for an open leg,
                                 None for the others
    aug                          (with --aug) arm, preset, KPlant identity, options, the valve-open
                                 share per leg over [t_touch, t_lift] (I-9)
"""

from __future__ import annotations

import re
from collections.abc import Sequence

import numpy as np

AUG_ARMS = {
    "H0": "none",
    "L1eq": "l1eq",
    "L1eq_fs": "l1eq_fs",
    "L1eq_zm": "l1eq_zm",
    "AUG": "aug",
    "AUG_crc2": "aug_crc2",
    "AUG_eps": "aug_eps",
}
"""``acc_d8.py --aug`` arm -> ``KPlant`` ``diss_preset`` (``k2_dyn_spec.md`` 2, rules 3.3)."""
K2_CHOICES = ("off", "on")
RATE_WINDOW_S = 0.3
"""SH-2 window before ``t_touch`` (rules 5.2)."""
HIST_PAD_MIN = slice(13, 17)
"""``FlexPlant.hist`` record columns (``d8x_diag``): minimum pad axial force per chunk."""
COUNTED_EVENT_PREFIXES = (
    "INFO_TOUCH_CREEP_LATCH",
    "INFO_TOUCH_CREEP_CAP",
    "INFO_TOUCH_DIP_HELD",
    "INFO_TOUCH_TWIST_HOLD",
    "INFO_LIFT_PAUSED",
    "INFO_LIFTOFF_SLOW",
)
LEG_NAMES = ("FL", "FR", "RL", "RR")
TIME_TOLERANCE_S = 1e-9
DHAT_WINDOW_S = 0.3
"""C4G2 D_hat window: the last 3 TOUCH samples at 10 Hz (``TouchTwistHoldSettings.estimate_samples``)."""
VALVE_OPEN_EPS_M_S = 1.0e-6
"""Valve open above this output (YAML ``actuator.rod_side.lock_eps_m_s``, ``k2_dyn_spec.md`` 1)."""

_RATES: list[np.ndarray] = []
_VALVES: list[np.ndarray] = []
_MOTOR_STROKES: list[np.ndarray] = []
_TOUCH_START: dict = {}
_INSTALLED: dict = {}


def aug_preset(arm: str) -> str:
    """The ``diss_preset`` of an ``--aug`` arm.

    Raises:
        ValueError: An unknown arm.
    """
    if arm not in AUG_ARMS:
        raise ValueError(f"--aug {arm!r}: expected one of {tuple(AUG_ARMS)}")
    return AUG_ARMS[arm]


def k2_arm_is_on(k2: str | None) -> bool:
    """``on`` / ``off`` of a K-2 arm.

    Raises:
        ValueError: Anything else.
    """
    if k2 not in K2_CHOICES:
        raise ValueError(f"K-2 arm {k2!r}: expected one of {K2_CHOICES}")
    return k2 == "on"


# ------------------------------------------------------------------------------ recorders
def install_recorders(plant_class, adapter_class) -> None:
    """Read-only recorders after ``plant_class.step`` and ``adapter_class.update`` (once)."""
    if _INSTALLED:
        return
    previous_step = plant_class.step
    previous_update = adapter_class.update

    def step(self, u, nsteps):
        out = previous_step(self, u, nsteps)
        if nsteps > 1000:  # the crawler settle before the run: the plant drops its history too
            reset_chunk_records()
        else:
            _RATES.append(np.array(self.w, float))
            # valve state after the chunk (r8d1_td tau_v lag); the command without a lag
            valve = getattr(self, "_uf", None)
            source = u if valve is None else valve
            _VALVES.append(np.broadcast_to(np.asarray(source, float), (4,)).copy())
            _MOTOR_STROKES.append(np.array(self.sref, float))
        return out

    def update(self, m, t):
        speeds = previous_update(self, m, t)
        if "t" not in _TOUCH_START and str(self.controller.phase) == "TOUCH":
            _TOUCH_START["t"] = float(t)
        return speeds

    plant_class.step = step
    adapter_class.update = update
    _INSTALLED.update(step=previous_step, update=previous_update)


def reset_chunk_records() -> None:
    _RATES.clear()
    _VALVES.clear()
    _MOTOR_STROKES.clear()


def reset_recorders() -> None:
    reset_chunk_records()
    _TOUCH_START.clear()


# ------------------------------------------------------------------------------- metrics
def dhat_window_record(
    t_s: np.ndarray, valves_m_s: np.ndarray, motor_strokes_m: np.ndarray, t_touch_s: float | None
) -> tuple[list[str] | None, list[float | None] | None]:
    """Rules rev1 4 (a): legs with an open valve on a chunk of (t_touch - 0.3 s, t_touch] and, per
    open leg, the motor stroke gained over that window [mm] (the last chunk at or before the window
    start to the last chunk at or before ``t_touch``). ``(None, None)`` without ``t_touch``."""
    if t_touch_s is None or len(t_s) == 0:
        return None, None
    window_start_s = t_touch_s - DHAT_WINDOW_S
    inside = (t_s > window_start_s + TIME_TOLERANCE_S) & (t_s <= t_touch_s + TIME_TOLERANCE_S)
    if not inside.any():
        return None, None
    is_open = np.any(np.abs(valves_m_s[inside]) > VALVE_OPEN_EPS_M_S, axis=0)
    end = int(np.flatnonzero(inside)[-1])
    before = np.flatnonzero(t_s <= window_start_s + TIME_TOLERANCE_S)
    start_strokes_m = motor_strokes_m[int(before[-1])] if len(before) else motor_strokes_m[0]
    gained_mm = (motor_strokes_m[end] - start_strokes_m) * 1e3
    open_legs = [name for leg, name in enumerate(LEG_NAMES) if is_open[leg]]
    strokes = [float(gained_mm[leg]) if is_open[leg] else None for leg in range(len(LEG_NAMES))]
    return open_legs, strokes


def dhat_N(controller) -> float | None:
    """C4G2 D_hat of the run (None when no TOUCH -> LEVEL estimate was made)."""
    value = (controller.meta().get("touch_twist_hold") or {}).get("twist_load_estimate_N")
    return None if value is None else float(value)
def _first_latch_times(events: Sequence[Sequence]) -> dict[str, float]:
    times: dict[str, float] = {}
    for t, name in events:
        name = str(name)
        if name.startswith("INFO_TOUCH_CREEP_LATCH:"):
            times.setdefault(name.split(":", 1)[1], float(t))
    return times


def sh1_lift_chunks_after_latch(
    t_s: np.ndarray, pad_min_N: np.ndarray, events: Sequence[Sequence], t_touch_s: float | None
) -> list[int | None]:
    """SH-1 per leg (rules 5.2): chunks with pad normal <= 0 strictly after the leg's latch and strictly
    before ``t_touch`` (the window of the path-2 recount, ``k2_recount.series_metrics``)."""
    latch_times = _first_latch_times(events)
    counts: list[int | None] = []
    for leg, name in enumerate(LEG_NAMES):
        t_latch = latch_times.get(name)
        if t_latch is None or t_touch_s is None:
            counts.append(None)
            continue
        window = (t_s > t_latch + TIME_TOLERANCE_S) & (t_s < t_touch_s - TIME_TOLERANCE_S)
        counts.append(int(np.sum(window & (pad_min_N[:, leg] <= 0.0))))
    return counts


def sh2_rate_amplitude_deg_s(
    t_s: np.ndarray, rates_rad_s: np.ndarray, t_touch_s: float | None
) -> float | None:
    """SH-2 (rules 5.2): max |rate - mean| of the roll / pitch body rate over the chunks of
    [t_touch - 0.3 s, t_touch) (two chunks at least; the screen's 300 chunks before ``t_touch``)."""
    if t_touch_s is None or len(rates_rad_s) == 0:
        return None
    segment = (t_s >= t_touch_s - RATE_WINDOW_S - TIME_TOLERANCE_S) & (
        t_s < t_touch_s - TIME_TOLERANCE_S
    )
    if segment.sum() < 2:
        return None
    rates = rates_rad_s[segment, :2]
    return float(np.degrees(np.max(np.abs(rates - rates.mean(axis=0)))))


def j3_from_first_all4(t_s: np.ndarray, pad_min_N: np.ndarray) -> tuple[int | None, float | None]:
    """5.3: pad-lift chunks from the first chunk with all four pad normals > 0, and its time."""
    all_in_contact = np.all(pad_min_N > 0.0, axis=1)
    if not all_in_contact.any():
        return None, None
    first = int(np.argmax(all_in_contact))
    lifted = np.any(pad_min_N <= 0.0, axis=1)
    return int(np.sum(lifted[first:])), float(t_s[first])


def series_file_name(run_id: str) -> str:
    """File name of a run's series (``d8x_diag.id_slug`` + ``.npz``: ``|`` -> ``__``, ``+`` -> ``P``)."""
    text = run_id.replace("|", "__").replace("+", "P")
    return re.sub(r"[^A-Za-z0-9._-]", "_", text) + ".npz"


def save_series(path, t_s: np.ndarray, pad_min_N: np.ndarray, rates_rad_s: np.ndarray) -> None:
    """The 1 ms series of a row (E-8): ``t_s``, ``pad_normal_min_N`` (4), ``body_rate_rad_s`` (3)."""
    np.savez_compressed(
        path,
        t_s=np.asarray(t_s, float),
        pad_normal_min_N=np.asarray(pad_min_N, float),
        body_rate_rad_s=np.asarray(rates_rad_s, float),
    )


def event_counts(events: Sequence[Sequence]) -> dict[str, int]:
    return {
        prefix: sum(str(name).startswith(prefix) for _, name in events)
        for prefix in COUNTED_EVENT_PREFIXES
    }


def pad_normal_N(plant) -> np.ndarray:
    """Pad normal per chunk with the J3 arithmetic of ``d8x_record.run_metrics`` (``(F + W) - W + W``)."""
    rod_weight = np.asarray(plant.Wr, float).reshape(1, 4)
    pad_min = np.asarray(plant.hist, float)[:, HIST_PAD_MIN]
    return (pad_min - rod_weight) + rod_weight


def k2_fields(
    plant, controller, d8x: dict, *, aug_arm: str | None, kplant_class, series_path=None
) -> dict:
    """The K-2 row fields of the run just finished in this process (module docstring); with
    ``series_path`` the 1 ms series are saved there (:func:`save_series`) and named in ``series_file``."""
    t_s = np.asarray(plant.hist_t, float)
    pad_N = pad_normal_N(plant)
    rates = np.asarray(_RATES, float).reshape(-1, 3)
    valves = np.asarray(_VALVES, float).reshape(-1, 4)
    motor_strokes = np.asarray(_MOTOR_STROKES, float).reshape(-1, 4)
    if not len(rates) == len(valves) == len(motor_strokes) == len(t_s):
        raise RuntimeError(f"K-2 chunk recorder {len(rates)} rows, plant history {len(t_s)}")
    events = d8x["events"]
    t_touch = d8x["t_touch_s"]
    open_legs, window_strokes_mm = dhat_window_record(t_s, valves, motor_strokes, t_touch)
    j3_all4, t_all4 = j3_from_first_all4(t_s, pad_N)
    touch_start = _TOUCH_START.get("t")
    meta = controller.meta().get("touch_creep_latch") or {}
    fields = {
        "touch_creep_latch": bool(getattr(controller.config.touch_creep_latch, "enable", False)),
        "touch_start_s": touch_start,
        "touch_length_s": (
            None if touch_start is None or t_touch is None else float(t_touch) - touch_start
        ),
        "latches": meta.get("latches", []),
        "SH1_lift_chunks_after_latch": sh1_lift_chunks_after_latch(t_s, pad_N, events, t_touch),
        "SH2_rate_amp_deg_s": sh2_rate_amplitude_deg_s(t_s, rates, t_touch),
        "J3_from_first_all4": j3_all4,
        "t_first_all4_s": t_all4,
        "event_counts": event_counts(events),
        "dhat_N": dhat_N(controller),
        "dhat_window_open_legs": open_legs,
        "dhat_window_stroke_mm": window_strokes_mm,
    }
    if aug_arm is not None:
        fields["aug"] = {
            "arm": aug_arm,
            "preset": aug_preset(aug_arm),
            "is_kplant": isinstance(plant, kplant_class),
            "case_id": getattr(plant, "case_id", None),
            "plant_aug": plant.aug_record() if hasattr(plant, "aug_record") else None,
            "valve_open_fraction_touch_to_lift": (
                plant.valve_open_fraction(t_touch, d8x.get("t_lift_s"))
                if hasattr(plant, "valve_open_fraction")
                else None
            ),
        }
    if series_path is not None:
        save_series(series_path, t_s, pad_N, rates)
    return fields
