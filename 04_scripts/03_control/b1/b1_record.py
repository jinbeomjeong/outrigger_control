"""B1 creep basis (``V5-B1-CREEP``): record-only controller hooks of the harness runs.

Rules: ``06_analysis/02_control/b1/b1_creep_rules.md`` (sealed, ``b1_harness.RULES_SHA256``)
2.2 / 2.4 / 6 R-C1.

Two things live here:

* :func:`install_period_record` wraps ``C2Controller.update`` once per process. After the
  original update it appends what the controller saw and used in that period: the R-C1 fields
  (nominal load reading, period-mean raw tilt, clearance estimate per corner and its minimum,
  run clearance target) plus time, phase, reading stroke and the filtered attitude.
  It only reads controller state (no method that creates state is called), so the commands
  stay bit for bit; the runner checks this with the command hash of the shadow-off pairs.
* :func:`make_margin_zero_class` is the H-M0 research subclass (rules 2.4, U-5 (a)): the R8
  preset as it is, P-S8-31 (E3c10) ``enable`` kept and ``margin_m`` set to 0, so E3c10 still
  sets the run target (+0 mm, event ``INFO_LOC_CLEARANCE_MARGIN:50``) and R4c30 stays blocked.

The per-period arrays (:func:`period_record_arrays`) are the controller half of the run record
``b1-run-record/2`` (``b1_harness.py`` adds the pad sinkage of the plant).
"""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

import numpy as np

PERIOD_RECORD_ATTRIBUTE = "_b1_period_record"
INSTALLED_MARK = "_b1_period_record_installed"
MARGIN_ZERO_CLASS_NAME = "B1MarginZeroC2Controller"
MARGIN_ZERO_M = 0.0
LEG_COUNT = 4


# ----------------------------------------------------------------------------- helpers
def _clearance_corners_m(controller, rod_stroke_m) -> np.ndarray:
    """``C2Controller._clearance_corners_m`` (``c_k`` or ``c_k - b_k``) without creating the
    soil state; corners in ``geometry.crawler_corners_xy_m`` order."""
    corners_m = np.asarray(controller.geometry.clearance_corners_m(rod_stroke_m), dtype=float)
    soil = controller._state.soil
    if controller.config.soil.enable and soil is not None and soil.has_corner_bias:
        corners_m = corners_m - np.asarray(soil.corner_bias_m, dtype=float)
    return corners_m


def _clearance_estimate_m(controller, rod_stroke_m) -> float:
    """``C2Controller._clearance_estimate_m`` without creating the soil state."""
    return float(np.min(_clearance_corners_m(controller, rod_stroke_m)))


def _period_entry(controller, measurements) -> tuple:
    state = controller._state
    reading = state.last_reading
    load_N = state.last_cylinder_force_N
    corners_m = (np.full(LEG_COUNT, np.nan) if reading is None
                 else _clearance_corners_m(controller, reading.rod_stroke_m))
    return (float(measurements.t_s),
            str(controller.phase),
            np.array(measurements.stroke_m, dtype=float),
            np.full(LEG_COUNT, np.nan) if load_N is None else np.array(load_N, dtype=float),
            np.array(controller._period_raw_attitude_rad(), dtype=float),
            float(np.min(corners_m)) if reading is not None else math.nan,
            corners_m,
            float(controller._clearance_target_m()),
            np.array(controller.filtered_attitude_rad, dtype=float))


def _wrap_update(original):
    def update(self, measurements):
        command = original(self, measurements)
        self.__dict__.setdefault(PERIOD_RECORD_ATTRIBUTE, []).append(
            _period_entry(self, measurements))
        return command

    return update


# ----------------------------------------------------------------------------- public API
def install_period_record(controller_class=None) -> bool:
    """Wrap ``update`` of ``controller_class`` (default ``c2.C2Controller``) once.

    Returns:
        True when this call installed the wrapper, False when it was already in place.
    """
    if controller_class is None:
        from outrigger_sim.control import c2

        controller_class = c2.C2Controller
    if controller_class.__dict__.get(INSTALLED_MARK, False):
        return False
    controller_class.update = _wrap_update(controller_class.update)
    setattr(controller_class, INSTALLED_MARK, True)
    return True


def period_record_arrays(controller) -> dict[str, np.ndarray]:
    """The recorded periods as arrays (empty arrays without a record).

    Rules 6 R-C1 names: ``n`` (period index ``round(t / 0.1)``), ``load_read_N`` (N, 4,
    ``PressureForces.nominal``), ``att_raw_rad`` (N, 2: period-mean raw tilt roll, pitch =
    ``_period_raw_attitude_rad``), ``c_hat_m`` (N,), ``c_hat_corner_m`` (N, 4, corners in
    ``crawler_corners_xy_m`` order), ``c_target_m`` (N,). Also ``t_s``, ``phase``,
    ``stroke_read_m`` (N, 4) and the record-only ``att_filt_rad`` (N, 2).
    """
    rows = controller.__dict__.get(PERIOD_RECORD_ATTRIBUTE, [])
    period_s = float(controller.config.period_s)
    t_s = np.array([row[0] for row in rows], dtype=float)

    def column(index: int, width: int | None = None) -> np.ndarray:
        values = np.array([row[index] for row in rows], dtype=float)
        return values if width is None else values.reshape(-1, width)

    return {
        "n": np.rint(t_s / period_s).astype(np.int64),
        "t_s": t_s,
        "phase": np.array([row[1] for row in rows], dtype=str),
        "stroke_read_m": column(2, LEG_COUNT),
        "load_read_N": column(3, LEG_COUNT),
        "att_raw_rad": column(4, 2),
        "c_hat_m": column(5),
        "c_hat_corner_m": column(6, LEG_COUNT),
        "c_target_m": column(7),
        "att_filt_rad": column(8, 2),
    }


def make_margin_zero_class(base):
    """H-M0 research subclass of ``base`` (rules 2.4): E3c10 ``enable`` kept, ``margin_m`` 0.

    Raises (at construction):
        ValueError: The config is missing or has E3c10 off (H-M0 needs the preset's
            ``enable``; turning it off would let R4c30 add +30 mm instead).
    """

    def __init__(self, geometry, config=None, *args, **kwargs):
        if config is None or not config.slope_clearance_margin.enable:
            raise ValueError(f"{MARGIN_ZERO_CLASS_NAME} needs a config with "
                             "slope_clearance_margin.enable (the R8 preset)")
        margin = replace(config.slope_clearance_margin, margin_m=MARGIN_ZERO_M)
        base.__init__(self, geometry, replace(config, slope_clearance_margin=margin),
                      *args, **kwargs)

    return type(MARGIN_ZERO_CLASS_NAME, (base,), {
        "__init__": __init__,
        "__doc__": "B1 H-M0: the R8 preset with P-S8-31 margin_m = 0 (enable kept).",
        "__module__": __name__,
    })


def controller_record(controller) -> dict[str, Any]:
    """Identity of the controller of a run (rules I-9): class names along the MRO and the
    P-S8-31 / R4 settings in force."""
    margin = controller.config.slope_clearance_margin
    return {
        "class_mro": [cls.__name__ for cls in type(controller).__mro__
                      if cls.__name__ != "object"],
        "is_margin_zero_class": any(cls.__name__ == MARGIN_ZERO_CLASS_NAME
                                    for cls in type(controller).__mro__),
        "slope_margin_enable": bool(margin.enable),
        "slope_margin_m": float(margin.margin_m),
        "flat_soil_margin_m": float(margin.flat_soil_margin_m),
        "flat_soil_margin_order_gate": bool(margin.flat_soil_margin_order_gate),
        "clearance_target_config_m": float(controller.config.thresholds.clearance_target_m),
        "clearance_target_final_m": float(controller._clearance_target_m()),
    }
