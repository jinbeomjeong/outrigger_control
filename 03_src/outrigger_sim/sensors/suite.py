"""All sensor error models at the engine / controller boundary (engine independent).

``SimEngine.measure()`` returns ideal :class:`Measurements` at the sensor locations (plan 3.3);
:class:`SensorSuite` turns them into what the controller sees and describes itself for the
run meta (:class:`outrigger_sim.record.SensorSetup`). One seed drives every noise source:
it is split with ``numpy.random.SeedSequence.spawn`` into independent IMU and leg-sensor
streams, so changing one model's settings never shifts the other's noise.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import ArrayLike

from outrigger_sim.record import SensorSetup
from outrigger_sim.sensors.hydraulic import LegSensorConfig, LegSensorModel
from outrigger_sim.sensors.imu import IMU_MOUNT_C1_BODY_M, ImuErrorConfig, ImuModel
from outrigger_sim.signals import Measurements

SENSOR_SUITE_MODEL_NAME = "outrigger_sim.sensors.suite"


class SensorSuite:
    """IMU and leg sensors applied to ideal measurements.

    Args:
        imu_config: IMU error parameters.
        leg_config: Pressure and stroke sensor noise and resolution.
        seed: Noise seed; ``None`` draws fresh entropy, kept in :attr:`seed` for the meta.
        imu_mount_point_body_m: Where the engine evaluates the IMU truth (meta only; the
            engine computes the truth, this class only records the point).
    """

    def __init__(
        self,
        imu_config: ImuErrorConfig,
        leg_config: LegSensorConfig,
        seed: int | None,
        imu_mount_point_body_m: ArrayLike = IMU_MOUNT_C1_BODY_M,
    ) -> None:
        seed_sequence = np.random.SeedSequence(seed)
        self.seed: int = int(seed_sequence.entropy)  # type: ignore[arg-type]
        imu_seed, leg_seed = seed_sequence.spawn(2)
        self.imu = ImuModel(imu_config, imu_seed)
        self.legs = LegSensorModel(leg_config, leg_seed)
        self.imu_mount_point_body_m = tuple(float(value) for value in imu_mount_point_body_m)

    def reset(self) -> None:
        """Restart every noise stream and empty the IMU delay line."""
        self.imu.reset()
        self.legs.reset()

    def apply(self, ideal: Measurements, imu_samples: Any = None) -> Measurements:
        """Delivered measurements for one control-period sample of ideal values.

        Args:
            ideal: Ideal measurements at the control instant.
            imu_samples: IMU-rate true values of the period (R8, ``s6_control_spec.md`` 148
                R-1): an object with ``sample_t_s`` (n,), ``sample_specific_force_m_s2``
                (n, 3) and ``sample_angular_rate_rad_s`` (n, 3), e.g. the runner's
                :class:`~outrigger_sim.sensors.averaging.PeriodAverage`. The IMU error model
                then runs once per sample (its ``sample_period_s`` must be the sample
                interval, noise ``density sqrt(1 / (2 T_imu))``); the delivered specific
                force and angular rate are the means of the delivered samples and
                ``imu_specific_force_samples_m_s2`` carries the samples. None (default) = one
                IMU reading on the period mean (R7 path, unchanged).
        """
        if imu_samples is not None and getattr(imu_samples, "sample_t_s", None) is not None:
            return self._apply_imu_rate(ideal, imu_samples)
        imu_reading = self.imu.measure(
            ideal.t_s, ideal.specific_force_m_s2, ideal.angular_rate_rad_s
        )
        leg_reading = self.legs.measure(
            ideal.head_pressure_Pa,
            ideal.stroke_m,
            ideal.stroke_corrected_m,
            ideal.rod_pressure_Pa,
            t_s=ideal.t_s,
        )
        return Measurements(
            t_s=ideal.t_s,
            specific_force_m_s2=imu_reading.specific_force_m_s2,
            angular_rate_rad_s=imu_reading.angular_rate_rad_s,
            head_pressure_Pa=leg_reading.head_pressure_Pa,
            stroke_m=leg_reading.stroke_m,
            stroke_corrected_m=leg_reading.stroke_corrected_m,
            rod_pressure_Pa=leg_reading.rod_pressure_Pa,
            oil_temperature_C=ideal.oil_temperature_C,
        )

    def _apply_imu_rate(self, ideal: Measurements, samples: Any) -> Measurements:
        times = np.asarray(samples.sample_t_s, dtype=float)
        forces = np.asarray(samples.sample_specific_force_m_s2, dtype=float)
        rates = np.asarray(samples.sample_angular_rate_rad_s, dtype=float)
        if forces.shape != (times.size, 3) or rates.shape != (times.size, 3):
            raise ValueError(
                f"IMU samples: shapes {forces.shape} / {rates.shape} for {times.size} times"
            )
        delivered_force = np.empty_like(forces)
        delivered_rate = np.empty_like(rates)
        for i in range(times.size):
            reading = self.imu.measure(float(times[i]), forces[i], rates[i])
            delivered_force[i] = reading.specific_force_m_s2
            delivered_rate[i] = reading.angular_rate_rad_s
        leg_reading = self.legs.measure(
            ideal.head_pressure_Pa,
            ideal.stroke_m,
            ideal.stroke_corrected_m,
            ideal.rod_pressure_Pa,
            t_s=ideal.t_s,
        )
        return Measurements(
            t_s=ideal.t_s,
            specific_force_m_s2=delivered_force.mean(axis=0),
            angular_rate_rad_s=delivered_rate.mean(axis=0),
            head_pressure_Pa=leg_reading.head_pressure_Pa,
            stroke_m=leg_reading.stroke_m,
            stroke_corrected_m=leg_reading.stroke_corrected_m,
            rod_pressure_Pa=leg_reading.rod_pressure_Pa,
            oil_temperature_C=ideal.oil_temperature_C,
            imu_specific_force_samples_m_s2=delivered_force,
        )

    def setup(self) -> SensorSetup:
        """Settings and seed for :func:`outrigger_sim.record.make_run_meta`."""
        config = {
            "model": SENSOR_SUITE_MODEL_NAME,
            "imu_mount_point_body_m": list(self.imu_mount_point_body_m),
            "imu": self.imu.config.to_meta(),
            "legs": self.legs.config.to_meta(),
        }
        error_meta = self.legs.error_meta()
        if error_meta is not None:
            config["pressure_error_terms"] = error_meta
        return SensorSetup(config=config, noise_seed=self.seed)
