"""PyChrono implementation of the SimEngine protocol.

Present: system (S0 system factory), ground_bushing (S0 L1 ground tangential model, R15),
snapshot (S0 Chrono side of the R16 snapshot), bodies, contact, probes, model (S1),
actuators (S2b L1SpeedActuator, S3 guards), runs (S2a-S3 run loops, Δt windows),
energy (S3 mechanical energy meter for V8(a)).
Planned modules (00_docs/03_chrono/chrono_build_plan.md 3.1): lateral_bushing, loads, scm.
"""
