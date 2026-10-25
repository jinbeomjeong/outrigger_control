"""Engine-independent hydraulic models of the leg cylinders.

Modules:

* ``rod_chamber`` - L1-R rod-side chamber state machine (EXT / RET / LOCK / FLOOR / LIFT), the
  one-sided nonlinear parallel spring of the locked rod chamber
  (``00_docs/02_hydraulic/rod_side_pressure.md`` 14, user decision 2026-10-22).
* ``l2b_rod_side`` - the same law inside the L2b force law (also oil-only, ``k_out = inf``).
* ``seal_friction`` - S8 Coulomb seal friction of the L2b legs (spec
  ``00_docs/02_hydraulic/s8_seal_friction_counterbalance.md`` 2, U-S8-H1..H4).
* ``counterbalance`` - S8 counterbalance lock-valve option (same spec 4, U-S8-H5/H6).
"""
