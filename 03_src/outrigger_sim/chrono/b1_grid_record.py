"""B1 creep-basis grid record of the ``run_S9.py level`` rows (read-only; cad 2026-11-12).

Rules ``06_analysis/02_control/b1/b1_creep_rules.md`` (sealed 2026-11-12, sha256 ``6b99702c...``) section 6, option ``--b1-grid-record {full,window}`` (absent = no attribute, nothing here runs):

* R-G1 (every 10 Hz control instant): per pad ``n_inside``, ``n_contact``, ``n_sigma_negative``,
  ``contact_hull_area_m2``, ``contact_hull_perimeter_m``, ``sinkage_geometric_m``, ``sigma_sum_area_N``,
  ``sinkage_mean_contact_m``. The values are the ones ``S9Model.pad_node_stats`` (``node_stats_in_outline``,
  ``SCMTerrain::GetNodeInfo``, a const hash-map lookup, SCMTerrain.cpp:751) already returns for result.json
  ``s9_rows[].pad_nodes`` on every level run since f1efed7 (2026-10-26); this record copies them into arrays.
* R-G2 (10 Hz): pad bottom centre (world and SCM-plane xy) and pad body position, pad yaw about the plane normal.
* R-G3 (start): pad grid per leg, SCM plane point / rotation, pad bottom polygons (pad body frame) and their
  area / perimeter / ``b_poly = 2A/P``.
* R-G4 (IMU rate, 100 Hz): the controller's own unfiltered accelerometer tilt of every IMU sample of the period
  (``C2Controller._state.period_raw_tilts``, read after the update) and the delivered specific-force samples.
* R-C1 (every control instant, sealed rules ``b1_creep_rules.md`` 6 names): ``n``, ``load_read_N`` (n, 4),
  ``att_raw_rad`` (n, 2), ``c_hat_m`` (n,), ``c_hat_corner_m`` (n, 4), ``c_target_m`` (n,)
  (:func:`controller_cycle_record`).

File ``record/b1_grid_record.npz`` of the case folder (sealed rules 6). The R-G1 values must equal
``result.json s9_rows[].pad_nodes`` (:func:`pad_nodes_consistency`).

``window`` (rules 6 fallback clause): the stored cycles are ``[n_L1 - 10, n_up + 20]`` (first LOC - 1 s, last
stroke increase after the first LOC + 2 s), ``[n_R - 10, n_R + 10]`` (first READY +- 1 s) and every
``n % 10 == 0`` cycle (1 s grid). Online, ``pad_node_stats`` is skipped only where no stored cycle can still
need it: after the first LOC, after ``n_up + 20`` and after ``n_R + 10`` (READY must have been seen), and off the
1 s grid. Before READY every cycle is computed (READY - 1 s is not known in advance). A stroke increase after a
skipped stretch moves ``n_up`` and can make skipped cycles part of the window: those stored rows carry
``computed = False`` (rules 6: "기록 없음"). In ``window`` mode a skipped cycle has ``s9_rows[].pad_nodes = None``.
``full`` never skips: ``pad_node_stats`` is called exactly as without the option.

Nothing here writes to Chrono: body poses are read with ``GetPos`` / ``TransformPointLocalToParent`` /
``TransformDirectionLocalToParent``, the controller state is only read.
"""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Any

import numpy as np

B1_GRID_RECORD_NAME = "b1_grid_record.npz"
B1_GRID_RECORD_REL = "record/b1_grid_record.npz"
"""Path inside the case folder (sealed rules b1_creep_rules.md 6)."""
B1_GRID_RECORD_MODES = ("full", "window")
B1_GRID_RECORD_SCHEMA = "b1-grid-record/1"
B1_RULES = ("06_analysis/02_control/b1/b1_creep_rules.md (sealed, sha256 6b99702c) 6 R-G1 .. R-G4, R-C1")
CONTROL_PERIOD_S = 0.1
LOC_EVENT = "crawler_liftoff_confirmed"
WINDOW_BEFORE_LOC_CYCLES = 10
WINDOW_AFTER_UP_CYCLES = 20
WINDOW_READY_CYCLES = 10
GRID_EVERY_CYCLES = 10
STROKE_INCREASE_EPS_M = 1.0e-9
"""A cycle counts as a stroke increase when any leg's read stroke exceeds the previous cycle's by more than this
(rules 4.4 epsilon_th)."""
INT_FIELDS = ("n_inside", "n_contact", "n_sigma_negative")
FLOAT_FIELDS = ("contact_hull_area_m2", "contact_hull_perimeter_m", "sinkage_geometric_m", "sigma_sum_area_N",
                "sinkage_mean_contact_m")
N_LEGS = 4


def cycle_of(t_s: float, period_s: float = CONTROL_PERIOD_S) -> int:
    """Rules 4.5: integer cycle ``round(t / 0.1)``."""
    return int(round(float(t_s) / period_s))


def in_rule_window(n: int, n_loc1: int | None, n_up: int | None, n_ready: int | None) -> bool:
    """True when cycle ``n`` belongs to the rules 6 fallback window set (final event cycles)."""
    if n % GRID_EVERY_CYCLES == 0:
        return True
    if n_loc1 is not None:
        end = (n_up if n_up is not None else n_loc1) + WINDOW_AFTER_UP_CYCLES
        if n_loc1 - WINDOW_BEFORE_LOC_CYCLES <= n <= end:
            return True
    if n_ready is not None and n_ready - WINDOW_READY_CYCLES <= n <= n_ready + WINDOW_READY_CYCLES:
        return True
    return False


def may_skip(n: int, n_loc1: int | None, n_up: int | None, n_ready: int | None) -> bool:
    """Online rule of ``window``: True only when no later information can put cycle ``n`` into the window except a
    new stroke increase (then the stored row says ``computed = False``)."""
    if n % GRID_EVERY_CYCLES == 0 or n_loc1 is None or n_ready is None:
        return False
    up_end = (n_up if n_up is not None else n_loc1) + WINDOW_AFTER_UP_CYCLES
    return n > up_end and n > n_ready + WINDOW_READY_CYCLES and n >= n_loc1 - WINDOW_BEFORE_LOC_CYCLES


def polygon_area_perimeter(xy: np.ndarray) -> tuple[float, float]:
    """Shoelace area and perimeter of an ordered polygon (k, 2)."""
    p = np.asarray(xy, float)
    q = np.roll(p, -1, axis=0)
    area = 0.5 * abs(float(np.sum(p[:, 0] * q[:, 1] - q[:, 0] * p[:, 1])))
    return area, float(np.sum(np.hypot(*(q - p).T)))


class B1GridRecorder:
    """10 Hz R-G1 / R-G2 and 100 Hz R-G4 record of one level run (see module doc)."""

    def __init__(self, model: Any, controller: Any, mode: str) -> None:
        if mode not in B1_GRID_RECORD_MODES:
            raise ValueError(f"--b1-grid-record must be one of {B1_GRID_RECORD_MODES}, got {mode!r}")
        self.model, self.controller, self.mode = model, controller, mode
        self.n_loc1: int | None = None
        self.n_up: int | None = None
        self.n_ready: int | None = None
        self._prev_stroke: np.ndarray | None = None
        self._n_events = 0
        self.rows: list[dict[str, Any]] = []
        self.imu: list[tuple[int, float, float, float, float, float, float]] = []
        self.ctl: list[dict[str, Any]] = []
        self._imu_last_t = -math.inf
        self.stats_wall_s = 0.0
        self.stats_calls = 0
        self.record_wall_s = 0.0
        self.skipped = 0

    # ------------------------------------------------------------------ online state
    def _update_state(self, n: int, meas: Any) -> None:
        events = getattr(self.controller, "events", ())
        for e in list(events)[self._n_events:]:
            if str(e.name) == LOC_EVENT and self.n_loc1 is None:
                self.n_loc1 = cycle_of(e.t_s)
        self._n_events = len(events)
        stroke = np.asarray(meas.stroke_m, float).copy()
        if self.n_loc1 is not None and self._prev_stroke is not None and n >= self.n_loc1:
            if bool(np.any(stroke - self._prev_stroke > STROKE_INCREASE_EPS_M)):
                self.n_up = n
        self._prev_stroke = stroke
        if self.n_ready is None and "ready" in str(getattr(self.controller, "phase", "")).lower():
            self.n_ready = n

    def pad_nodes(self, meas: Any) -> list[dict[str, Any]] | None:
        """The ``s9_rows[].pad_nodes`` value of this control instant (``model.pad_node_stats()``; ``window`` may
        return None) and its R-G1 / R-G2 / R-G4 record."""
        n = cycle_of(meas.t_s)
        self._update_state(n, meas)
        stats = None
        if self.mode == "full" or not may_skip(n, self.n_loc1, self.n_up, self.n_ready):
            tw = time.perf_counter()
            stats = self.model.pad_node_stats()
            self.stats_wall_s += time.perf_counter() - tw
            self.stats_calls += 1
        else:
            self.skipped += 1
        tw = time.perf_counter()
        self._record(n, float(meas.t_s), stats, meas)
        self.record_wall_s += time.perf_counter() - tw
        return stats

    def _record(self, n: int, t_s: float, stats: list[dict[str, Any]] | None, meas: Any) -> None:
        m = self.model
        p0 = np.asarray(m.plane_point_world_m, float)
        r = np.asarray(m.plane_rot, float)
        centre_w, centre_xy, body_w, yaw = [], [], [], []
        for i, pad in enumerate(m.pads):
            c = pad.TransformPointLocalToParent(_chvec(m.pad_bottom_local_pad_m[i]))
            cw = np.array([c.x, c.y, c.z], float)
            centre_w.append(cw)
            centre_xy.append(((cw - p0) @ r)[:2])
            bp = pad.GetPos()
            body_w.append([float(bp.x), float(bp.y), float(bp.z)])
            ax = pad.TransformDirectionLocalToParent(_chvec((1.0, 0.0, 0.0)))
            a = np.array([ax.x, ax.y, ax.z], float) @ r
            yaw.append(math.atan2(float(a[1]), float(a[0])))
        self.rows.append({"n": n, "t_s": t_s, "stats": stats, "centre_w": centre_w, "centre_xy": centre_xy,
                          "body_w": body_w, "yaw": yaw})
        self.ctl.append(controller_cycle_record(self.controller, n))
        tilts = getattr(getattr(self.controller, "_state", None), "period_raw_tilts", None) or ()
        forces = getattr(meas, "imu_specific_force_samples_m_s2", None)
        forces = None if forces is None else np.asarray(forces, float)
        for k, tl in enumerate(tilts):
            if float(tl.t_s) <= self._imu_last_t + 1e-9:
                continue
            f = (math.nan,) * 3 if forces is None or forces.shape[0] != len(tilts) else tuple(map(float, forces[k]))
            self.imu.append((n, float(tl.t_s), float(tl.roll_rad), float(tl.pitch_rad), *f))
            self._imu_last_t = float(tl.t_s)

    # ------------------------------------------------------------------ output
    def static_meta(self) -> dict[str, Any]:
        """R-G3."""
        m = self.model
        pads = []
        for i in range(len(m.pads)):
            poly = np.asarray(m.pad_outline_local_m[i], float)
            area, per = polygon_area_perimeter(poly[:, :2])
            pads.append({"leg": ("FL", "FR", "RL", "RR")[i], "grid_m": float(m.pad_grid_by_leg_m[i]),
                         "outline_local_pad_m": poly.tolist(),
                         "bottom_centre_local_pad_m": np.asarray(m.pad_bottom_local_pad_m[i], float).tolist(),
                         "outline_area_m2": area, "outline_perimeter_m": per,
                         "b_poly_m": 2.0 * area / per if per > 0 else None,
                         "scm_terrain": m.pad_terrain_by_leg[i] is not None})
        return {"plane_point_world_m": np.asarray(m.plane_point_world_m, float).tolist(),
                "plane_rot": np.asarray(m.plane_rot, float).tolist(), "pads": pads,
                "grid_origin": "SCM node (i, j) at plane_point + plane_rot @ (i grid, j grid, 0) "
                               "(scm_model.node_stats_in_outline)"}

    def save(self, path: Path) -> dict[str, Any]:
        rows = self.rows
        if self.mode == "window":
            rows = [r for r in rows if in_rule_window(r["n"], self.n_loc1, self.n_up, self.n_ready)]
        k = len(rows)
        arr: dict[str, np.ndarray] = {
            "n_cycle": np.array([r["n"] for r in rows], np.int64),
            "t_s": np.array([r["t_s"] for r in rows], float),
            "computed": np.array([r["stats"] is not None for r in rows], bool),
            "pad_bottom_centre_world_m": np.array([r["centre_w"] for r in rows], float).reshape(k, N_LEGS, 3),
            "pad_bottom_centre_plane_xy_m": np.array([r["centre_xy"] for r in rows], float).reshape(k, N_LEGS, 2),
            "pad_body_pos_world_m": np.array([r["body_w"] for r in rows], float).reshape(k, N_LEGS, 3),
            "pad_yaw_plane_rad": np.array([r["yaw"] for r in rows], float).reshape(k, N_LEGS),
        }
        for name in INT_FIELDS:
            arr[name] = np.array([[-1 if r["stats"] is None else int(r["stats"][i][name]) for i in range(N_LEGS)]
                                  for r in rows], np.int64).reshape(k, N_LEGS)
        for name in FLOAT_FIELDS:
            arr[name] = np.array([[math.nan if r["stats"] is None or r["stats"][i][name] is None
                                   else float(r["stats"][i][name]) for i in range(N_LEGS)] for r in rows],
                                 float).reshape(k, N_LEGS)
        imu = np.array(self.imu, float).reshape(-1, 7)
        arr["imu_n_cycle"] = imu[:, 0].astype(np.int64)
        arr["imu_t_s"] = imu[:, 1]
        arr["imu_raw_roll_rad"] = imu[:, 2]
        arr["imu_raw_pitch_rad"] = imu[:, 3]
        arr["imu_specific_force_m_s2"] = imu[:, 4:7]
        kc = len(self.ctl)  # R-C1: every control instant (never window-filtered)
        arr["n"] = np.array([r["n"] for r in self.ctl], np.int64).reshape(kc)
        arr["load_read_N"] = np.array([r["load_read_N"] for r in self.ctl], float).reshape(kc, N_LEGS)
        arr["att_raw_rad"] = np.array([r["att_raw_rad"] for r in self.ctl], float).reshape(kc, 2)
        arr["c_hat_m"] = np.array([r["c_hat_m"] for r in self.ctl], float).reshape(kc)
        arr["c_hat_corner_m"] = np.array([r["c_hat_corner_m"] for r in self.ctl], float).reshape(kc, N_LEGS)
        arr["c_target_m"] = np.array([r["c_target_m"] for r in self.ctl], float).reshape(kc)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, **arr)
        rel = B1_GRID_RECORD_REL if Path(path).parent.name == "record" else Path(path).name
        return {"schema": B1_GRID_RECORD_SCHEMA, "file": rel, "mode": self.mode, "rules": B1_RULES,
                "rows": k, "rows_seen": len(self.rows), "imu_samples": int(imu.shape[0]),
                "pad_node_stats_calls": self.stats_calls, "pad_node_stats_skipped": self.skipped,
                "pad_node_stats_wall_s": self.stats_wall_s, "record_wall_s": self.record_wall_s,
                "window_cycles": {"n_loc1": self.n_loc1, "n_up": self.n_up, "n_ready": self.n_ready},
                "keys": sorted(arr), "r_c1_rows": kc,
                "key_shapes": {name: [*v.shape] for name, v in sorted(arr.items())},
                "key_dtypes": {name: str(v.dtype) for name, v in sorted(arr.items())}, "static": self.static_meta(),
                "basis": ("R-G1 = S9Model.pad_node_stats() of the control instant (same call as s9_rows[].pad_nodes); "
                          "missing value: int -1, float NaN, computed False; R-G2 pad bottom centre / body position "
                          "(world, SCM-plane xy) and yaw of the pad body x axis about the plane normal; R-G4 = "
                          "C2Controller._state.period_raw_tilts after the update (controller's own raw tilt) and "
                          "Measurements.imu_specific_force_samples_m_s2; n_cycle = round(t / 0.1); R-C1 (rules 6, "
                          "every control instant): n, load_read_N = PressureForces.nominal, att_raw_rad = "
                          "_period_raw_attitude_rad(), c_hat_corner_m = geometry.clearance_corners_m(rod stroke of "
                          "the reading) - S-3 bias b_k in force (= _clearance_corners_m), c_hat_m = its minimum, "
                          "c_target_m = _clearance_target_m(); NaN before the first reading")}


def controller_cycle_record(controller: Any, n: int) -> dict[str, Any]:
    """R-C1 of one control instant, read after the update without side effects: the S-3 bias is taken from
    ``_state.soil`` directly (``_soil_state()`` would create the soil state)."""
    nan4 = [math.nan] * N_LEGS
    st = controller._state
    out: dict[str, Any] = {"n": int(n), "load_read_N": nan4, "att_raw_rad": [math.nan, math.nan], "c_hat_m": math.nan,
                           "c_hat_corner_m": nan4, "c_target_m": float(controller._clearance_target_m())}
    forces = getattr(st, "last_forces", None)
    if forces is not None:
        out["load_read_N"] = [float(v) for v in np.asarray(forces.nominal, float)]
    reading = getattr(st, "last_reading", None)
    if reading is not None:
        out["att_raw_rad"] = [float(v) for v in controller._period_raw_attitude_rad()]
        corners = np.asarray(controller.geometry.clearance_corners_m(reading.rod_stroke_m), float)
        soil = getattr(st, "soil", None)
        if controller.config.soil.enable and soil is not None and soil.has_corner_bias:
            corners = corners - np.asarray(soil.corner_bias_m, float)
        out["c_hat_corner_m"] = [float(v) for v in corners]
        out["c_hat_m"] = float(np.min(corners))
    return out


R_G1_PAD_NODE_FIELDS = ("n_inside", "n_contact", "contact_hull_area_m2", "contact_hull_perimeter_m",
                        "sinkage_geometric_m", "sigma_sum_area_N")
"""Fields of ``s9_rows[].pad_nodes`` the rules 6 sentence compares with the npz."""


def pad_nodes_consistency(npz_path: Path, result: dict[str, Any]) -> dict[str, Any]:
    """Rules 6: the R-G1 fields of ``b1_grid_record.npz`` against ``result.json s9_rows[].pad_nodes`` of the same
    cycles (exact equality; None = NaN / -1). Returns counts and the first differing (cycle, leg, field) only."""
    rows = {cycle_of(r["t_s"]): r.get("pad_nodes") for r in result.get("s9_rows", [])}
    out: dict[str, Any] = {"fields": list(R_G1_PAD_NODE_FIELDS), "cycles": 0, "cycles_missing_in_result": 0,
                           "values": 0, "differ": 0, "first_differ": None}
    with np.load(npz_path, allow_pickle=False) as z:
        for k, n in enumerate(z["n_cycle"].tolist()):
            if not bool(z["computed"][k]):
                continue
            pn = rows.get(int(n))
            if pn is None:
                out["cycles_missing_in_result"] += 1
                continue
            out["cycles"] += 1
            for i in range(N_LEGS):
                for f in R_G1_PAD_NODE_FIELDS:
                    a, b = z[f][k, i], pn[i][f]
                    out["values"] += 1
                    if f in INT_FIELDS:
                        same = int(a) == (-1 if b is None else int(b))
                    else:
                        same = (math.isnan(float(a)) and b is None) or (b is not None and float(a) == float(b))
                    if not same:
                        out["differ"] += 1
                        if out["first_differ"] is None:
                            out["first_differ"] = {"cycle": int(n), "leg": i, "field": f}
    out["ok"] = out["differ"] == 0 and out["cycles_missing_in_result"] == 0 and out["cycles"] > 0
    return out


def _chvec(v: Any) -> Any:
    import pychrono as ch  # noqa: PLC0415

    return ch.ChVector3d(float(v[0]), float(v[1]), float(v[2]))
