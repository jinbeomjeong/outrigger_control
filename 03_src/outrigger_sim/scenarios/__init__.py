"""Simulation scenarios driven through the SimEngine protocol.

Present: settle (S1 analytic static pose, settle windows), slope (S2a V12 sloped floor),
impulse (S2a V7 initial-velocity excitation), crawler_settle (S2b crawler contact layout D and
settled pose), stroke (S2b airborne pose, V11 schedule, touchdown/lift-off events), lift (S3 V4
lift plan, ``LegStep`` for V5/V6/V9 - the planned ``leg_step`` lives here, ``crossing``).
Planned modules (00_docs/03_chrono/chrono_build_plan.md 3.1): single_leg, disturbance_d2.
"""
