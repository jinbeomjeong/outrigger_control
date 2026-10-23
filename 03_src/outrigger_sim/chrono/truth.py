"""Sensor truth read from the L1 Chrono model (plan S6 ``sensors/truth``, Chrono side).

``00_docs/03_chrono/chrono_build_plan.md`` S6 (cad: ``sensors/truth``), 3.3; risk 2 (IMU
point as an argument) and risk 3 (both strokes). The engine-independent kinematics and error
models live in :mod:`outrigger_sim.sensors`; this module only reads Chrono and calls them.

Ideal values (no sensor error; :class:`outrigger_sim.sensors.suite.SensorSuite` adds errors):

* **IMU** (:func:`imu_truth`): specific force and angular rate at a body point (default C1
  :data:`outrigger_sim.sensors.imu.IMU_MOUNT_C1_BODY_M` = (0.31, 0.88, 0.040) m, body axes),
  in sensor (= body) axes, from the superstructure state at the end of the step just taken:
  orientation, origin acceleration ``PointAccelerationLocalToParent`` (world), angular
  velocity / acceleration (world) -> :func:`outrigger_sim.sensors.imu.specific_force_at_point`
  and :func:`~outrigger_sim.sensors.imu.angular_rate_in_body`. Gravity is the system's own
  vector (R1; must be along world -z). Chrono's accelerations after a step are those of the
  implicit step (``(v_{n+1} - v_n) / dt``), so the control-period average of the per-step values
  is the velocity change over the period (``ControlPeriodAverager``).
* **Pressures and stroke truth from the L1-R machine** (``dynamics_model.md`` 5.12.4 '센서
  일관성', 5.12.8 Q-D4; ``chrono/rod_chamber_link``): the model steps the rod-chamber machine
  every engine step before the closed-loop callback, so at a control instant the head
  pressure, the rod-side pressure and ``stroke_corrected_m`` are the machine's
  ``head_pressure_Pa``, ``rod_pressure_Pa`` and ``stroke_true_m`` of the **same** step (one
  state for the plant force and the sensor). With ``actuator.rod_side.mechanics = off`` the
  machine's legacy output is ``F_cyl / A_head`` and ``s_motor - F_cyl / k_oil`` with the same
  ``A_head`` and ``k_oil`` as below, bit-identical to the formulas, and ``rod_pressure_Pa``
  stays None (no rod-side sensor in the net-equivalent path).
* **Head pressure** (formula, mechanics off) ``p = F_cyl / A_head`` (Pa), ``A_head`` per leg
  (``sensors.hydraulic.leg_head_areas_from_params``: ``legs.<leg>.cylinder.*`` or the common
  ``actuator.bore_diameter_m``); ``F_cyl`` = ``GetMotorForce()`` (+ pushes the pad down, R4).
  Without the rod side a pulling cylinder reads a negative head pressure.
* **Strokes** (risk 3, both): ``stroke_m`` = motor position (the L1 rigid stroke) and
  ``stroke_corrected_m`` = ``stroke_true`` = ``s_motor - F_cyl / k_oil`` (CLAUDE.md '센서',
  cylinder-internal sensor, user decision 2026-10-20; mechanics off). ``k_oil`` defaults to
  the per-leg operating-point value ``contact.rigid_floor.L1.derivation.k_oil_N_m``, the same
  value :class:`~outrigger_sim.signals.TruthState` uses (``chrono/probes``) and the one lumped
  into the L1 pad stiffness. :func:`k_oil_at_extension_N_m` gives the extension-dependent
  ``beta A_head / (L0 + e)`` for comparison (``stroke_model="extension"``, mechanics off
  only); it equals the YAML value at the operating extension.

Units SI; per-leg arrays in LEG_ORDER.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.params import LEG_ORDER, Params
from outrigger_sim.sensors.averaging import PeriodAverage
from outrigger_sim.sensors.hydraulic import leg_head_areas_from_params
from outrigger_sim.sensors.imu import (
    IMU_MOUNT_C1_BODY_M,
    angular_rate_in_body,
    specific_force_at_point,
)
from outrigger_sim.signals import Measurements

IMU_METHODS = ("sensors_imu", "chrono_point")
"""How :class:`L1SensorTruth` computes the per-step IMU truth (class docstring)."""

STROKE_MODELS = ("operating_point", "extension")
"""``k_oil`` used for ``stroke_true``: the YAML operating-point value (default, = TruthState)
or ``beta A_head / (L0 + e)`` at the current motor position."""


def _v(v: Any) -> NDArray[np.float64]:
    return np.array([v.x, v.y, v.z], dtype=float)


@dataclass(frozen=True, eq=False)
class ImuTruthSample:
    """IMU truth at one instant (sensor = body axes).

    Attributes:
        t_s: Simulation time (s).
        specific_force_m_s2: ``R^T (a_P - g)`` at the mounting point (m/s^2).
        angular_rate_rad_s: Body angular velocity in body axes (rad/s).
    """

    t_s: float
    specific_force_m_s2: NDArray[np.float64]
    angular_rate_rad_s: NDArray[np.float64]


def system_gravity_m_s2(system: Any) -> float:
    """Gravity magnitude of a Chrono system whose gravity points along world -z.

    Raises:
        ValueError: Gravity with a horizontal component or pointing up.
    """
    g = system.GetGravitationalAcceleration()
    if g.x != 0.0 or g.y != 0.0 or not g.z < 0.0:
        raise ValueError(f"IMU truth needs gravity along world -z, got ({g.x}, {g.y}, {g.z})")
    return -float(g.z)


def imu_truth(
    model: Any,
    mount_point_body_m: ArrayLike = IMU_MOUNT_C1_BODY_M,
    *,
    gravity_m_s2: float | None = None,
) -> ImuTruthSample:
    """IMU truth of an :class:`~outrigger_sim.chrono.model.L1Model` at the current state.

    Args:
        model: The L1 model (superstructure body ``model.superstructure``).
        mount_point_body_m: Sensor point in body coordinates (m), default C1.
        gravity_m_s2: Gravity magnitude; None = read from the system (:func:`system_gravity_m_s2`).
    """
    sup = model.superstructure
    q = sup.GetRot()
    quat = np.array([q.e0, q.e1, q.e2, q.e3], dtype=float)
    origin_accel = _v(sup.PointAccelerationLocalToParent(model.origin_in_cog_frame_ch))
    omega = _v(sup.GetAngVelParent())
    alpha = _v(sup.GetAngAccParent())
    g = system_gravity_m_s2(model.system) if gravity_m_s2 is None else float(gravity_m_s2)
    force = specific_force_at_point(quat, origin_accel, omega, alpha, mount_point_body_m, g)
    rate = angular_rate_in_body(quat, omega)
    return ImuTruthSample(float(model.system.GetChTime()), force, rate)


def imu_truth_direct(model: Any, mount_point_body_m: ArrayLike = IMU_MOUNT_C1_BODY_M):
    """Independent check path: Chrono's own acceleration of the mounting point
    (``PointAccelerationLocalToParent`` at the point) and body-frame angular velocity
    (``GetAngVelLocal``), ``f = R^T (a_P - g_vec)``. For tests and the S6 sensor-truth check.

    Returns:
        ``(specific_force_m_s2, angular_rate_rad_s)``, body axes.
    """
    import pychrono as ch

    sup = model.superstructure
    p = np.asarray(mount_point_body_m, dtype=float) - np.asarray(model.sup_com_body_m, dtype=float)
    a_p = _v(sup.PointAccelerationLocalToParent(ch.ChVector3d(*(float(c) for c in p))))
    g = _v(model.system.GetGravitationalAcceleration())
    f_world = a_p - g
    f_local = _v(sup.TransformDirectionParentToLocal(ch.ChVector3d(*(float(c) for c in f_world))))
    return f_local, _v(sup.GetAngVelLocal())


def head_pressure_Pa(
    cylinder_force_N: ArrayLike, head_area_m2: float | ArrayLike
) -> NDArray[np.float64]:
    """``p = F_cyl / A_head`` (Pa); one area or one per leg."""
    area = np.asarray(head_area_m2, dtype=float)
    divisor = float(area) if area.ndim == 0 else area
    return np.asarray(cylinder_force_N, dtype=float) / divisor


def k_oil_at_extension_N_m(params: Params, extension_m: ArrayLike) -> NDArray[np.float64]:
    """Head-side oil column stiffness ``beta A_head / (L0 + e)`` (N/m) per leg (YAML
    ``actuator.oil_bulk_modulus_eff_Pa``, ``actuator.oil_dead_length_m``)."""
    beta = float(params.get("actuator.oil_bulk_modulus_eff_Pa"))
    dead = float(params.get("actuator.oil_dead_length_m"))
    return beta * leg_head_areas_from_params(params) / (dead + np.asarray(extension_m, dtype=float))


class L1SensorTruth:
    """Ideal :class:`Measurements` of an L1 model (module docstring).

    Args:
        model: The L1 model.
        mount_point_body_m: IMU point (body coordinates, m); default C1 (plan S6 risk 2).
        stroke_model: :data:`STROKE_MODELS` entry for ``stroke_corrected_m``.
        imu_method: :data:`IMU_METHODS` entry: ``"sensors_imu"`` (default; the
            engine-independent kinematics of ``sensors/imu``) or ``"chrono_point"`` (Chrono's
            own point acceleration, :func:`imu_truth_direct`; same values within 1e-13 relative,
            about 10x cheaper per step).
    """

    def __init__(
        self,
        model: Any,
        mount_point_body_m: ArrayLike = IMU_MOUNT_C1_BODY_M,
        *,
        stroke_model: str = "operating_point",
        imu_method: str = "sensors_imu",
    ) -> None:
        if imu_method not in IMU_METHODS:
            raise ValueError(f"imu_method must be one of {IMU_METHODS}, got {imu_method!r}")
        self.imu_method = imu_method
        if stroke_model not in STROKE_MODELS:
            raise ValueError(f"stroke_model must be one of {STROKE_MODELS}, got {stroke_model!r}")
        point = np.array(mount_point_body_m, dtype=float).reshape(-1)
        if point.shape != (3,) or not np.all(np.isfinite(point)):
            raise ValueError(f"mount point: expected 3 finite values, got {mount_point_body_m!r}")
        self.model = model
        self.mount_point_body_m = tuple(float(c) for c in point)
        self.stroke_model = stroke_model
        areas = leg_head_areas_from_params(model.params)
        # one scalar while the legs share the area (the value of the pre-REXOME35 truth)
        self.head_area_m2: float | NDArray[np.float64] = (
            float(areas[0]) if bool(np.all(areas == areas[0])) else areas
        )
        self.k_oil_N_m = np.asarray(model.k_oil_N_m, dtype=float)
        self.rod_chamber = getattr(model, "rod_chamber", None)
        """The model's ``L1RodChamber`` (None for models without it, e.g. test doubles)."""
        self.l1r_enabled = bool(self.rod_chamber is not None and self.rod_chamber.enabled)
        if self.l1r_enabled and stroke_model != "operating_point":
            raise ValueError(
                "L1-R (actuator.rod_side.mechanics on) gives stroke_true from the rod-chamber "
                "machine (k_oil at e_op); stroke_model='extension' is not available"
            )
        self.gravity_m_s2 = system_gravity_m_s2(model.system)
        import pychrono as ch

        self._ch = ch
        local = point - np.asarray(model.sup_com_body_m, dtype=float)
        self._mount_local_ch = ch.ChVector3d(*(float(c) for c in local))
        gv = model.system.GetGravitationalAcceleration()
        self._gravity_vec = (float(gv.x), float(gv.y), float(gv.z))

    def imu(self) -> ImuTruthSample:
        """IMU truth at the current state (one call per physics step for the averager)."""
        if self.imu_method == "sensors_imu":
            return imu_truth(self.model, self.mount_point_body_m, gravity_m_s2=self.gravity_m_s2)
        sup = self.model.superstructure
        a = sup.PointAccelerationLocalToParent(self._mount_local_ch)
        g = self._gravity_vec
        f_world = self._ch.ChVector3d(a.x - g[0], a.y - g[1], a.z - g[2])
        f = sup.TransformDirectionParentToLocal(f_world)
        w = sup.GetAngVelLocal()
        return ImuTruthSample(
            float(self.model.system.GetChTime()),
            np.array([f.x, f.y, f.z], dtype=float),
            np.array([w.x, w.y, w.z], dtype=float),
        )

    def cylinder_forces_N(self) -> NDArray[np.float64]:
        return np.array([m.GetMotorForce() for m in self.model.motors], dtype=float)

    def motor_positions_m(self) -> NDArray[np.float64]:
        return np.array([m.GetMotorPos() for m in self.model.motors], dtype=float)

    def stroke_true_m(self, s_motor_m: ArrayLike, cylinder_force_N: ArrayLike) -> NDArray:
        """``s_motor - F_cyl / k_oil`` with the configured ``k_oil``."""
        s = np.asarray(s_motor_m, dtype=float)
        k = (
            self.k_oil_N_m
            if self.stroke_model == "operating_point"
            else k_oil_at_extension_N_m(self.model.params, s)
        )
        return s - np.asarray(cylinder_force_N, dtype=float) / k

    def ideal_measurements(
        self,
        imu_average: PeriodAverage,
        *,
        cylinder_force_N: Sequence[float] | None = None,
        s_motor_m: Sequence[float] | None = None,
    ) -> Measurements:
        """Ideal measurements at the period end ``imu_average.t_s``: control-period average
        IMU, instantaneous pressures and both strokes at that instant (read now unless given;
        the caller must be at ``imu_average.t_s``).

        Pressures and ``stroke_corrected_m`` come from the rod-chamber machine output of the
        current step (module docstring) unless forces or motor positions are given (then the
        formulas; refused with L1-R mechanics on).
        """
        t_now = float(self.model.system.GetChTime())
        if abs(t_now - imu_average.t_s) > 1e-9 * max(1.0, abs(t_now)):
            raise ValueError(
                f"measurement at {imu_average.t_s!r} s but the model is at {t_now!r} s"
            )
        overridden = cylinder_force_N is not None or s_motor_m is not None
        out = None
        if self.rod_chamber is not None and not overridden:
            out = self.rod_chamber.output_at(t_now)
        if self.l1r_enabled and out is None:
            raise RuntimeError(
                "L1-R sensor truth needs the rod-chamber machine output of the current step "
                f"(t = {t_now!r} s; forces / positions given: {overridden})"
            )
        s = self.motor_positions_m() if s_motor_m is None else np.asarray(s_motor_m)
        if out is None:
            f = (
                self.cylinder_forces_N()
                if cylinder_force_N is None
                else np.asarray(cylinder_force_N)
            )
            head = head_pressure_Pa(f, self.head_area_m2)
            corrected = self.stroke_true_m(s, f)
            rod = None
        else:
            head = np.array(out.head_pressure_Pa, dtype=float)
            corrected = (
                np.array(out.stroke_true_m, dtype=float)
                if self.stroke_model == "operating_point"
                else self.stroke_true_m(s, np.array(out.cylinder_force_N, dtype=float))
            )
            rod = np.array(out.rod_pressure_Pa, dtype=float) if self.l1r_enabled else None
        return Measurements(
            t_s=imu_average.t_s,
            specific_force_m_s2=imu_average.specific_force_m_s2,
            angular_rate_rad_s=imu_average.angular_rate_rad_s,
            head_pressure_Pa=head,
            stroke_m=s,
            stroke_corrected_m=corrected,
            rod_pressure_Pa=rod,
        )

    def meta(self) -> dict[str, Any]:
        """JSON-ready description for the run meta."""
        return {
            "module": "outrigger_sim.chrono.truth",
            "imu_mount_point_body_m": list(self.mount_point_body_m),
            "imu_truth": "superstructure state at the step end; specific_force_at_point, "
            "angular_rate_in_body (sensors/imu); control-period average (sensors/averaging)",
            "gravity_m_s2": self.gravity_m_s2,
            "head_area_m2": np.asarray(self.head_area_m2, dtype=float).tolist(),
            "pressure": (
                "L1-R machine head_pressure_Pa / rod_pressure_Pa of the same engine step"
                if self.l1r_enabled
                else "p = F_cyl / A_head (instantaneous at the control instant; machine "
                "legacy output, mechanics off), no rod-side pressure"
            ),
            "stroke_m": "motor position (L1 rigid stroke)",
            "stroke_corrected_m": (
                "L1-R machine stroke_true_m (lock-anchored increment, Q-D4)"
                if self.l1r_enabled
                else "stroke_true = s_motor - F_cyl / k_oil"
            ),
            "rod_chamber_mechanics": None
            if self.rod_chamber is None
            else str(self.rod_chamber.mechanics),
            "stroke_model": self.stroke_model,
            "imu_method": self.imu_method,
            "k_oil_N_m": dict(zip(LEG_ORDER, self.k_oil_N_m.tolist(), strict=True)),
        }


__all__ = [
    "IMU_METHODS",
    "STROKE_MODELS",
    "ImuTruthSample",
    "L1SensorTruth",
    "head_pressure_Pa",
    "imu_truth",
    "imu_truth_direct",
    "k_oil_at_extension_N_m",
    "system_gravity_m_s2",
]

