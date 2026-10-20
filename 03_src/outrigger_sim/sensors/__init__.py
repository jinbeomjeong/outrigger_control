"""Sensor models: ideal measurements from truth state and engine-independent sensor errors.

Modules (00_docs/03_chrono/chrono_build_plan.md 3.1, S6):

* ``imu`` - IMU truth at the mounting point (default C1) and the IMU error model, 5 grades.
* ``averaging`` - control-period (20 ms) time average of the IMU truth, the IMU input.
* ``attitude`` - tilt from the specific force and the 2nd-order attitude low-pass.
* ``hydraulic`` - pressure and stroke sensor noise, 350 bar locked-pressure indicator.
* ``suite`` - all sensor errors applied to ``SimEngine.measure()`` output.
* ``truth`` (planned, Chrono side) - ideal values read from the engine.
"""
