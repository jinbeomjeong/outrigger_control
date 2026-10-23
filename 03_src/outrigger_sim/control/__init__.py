"""Controller protocol and leveling controllers (engine-independent).

Modules (00_docs/03_chrono/chrono_build_plan.md 3.1, 3.3, S6):

* ``protocol`` - :class:`Controller` (Measurements -> Command every control period).
* ``hold`` - :class:`HoldController`, the empty controller (all legs stopped).
* ``c2`` - :class:`C2Controller`, the C2 levelling controller (``00_docs/04_control/c2_design.md``
  section 14).
* ``target`` - roll / pitch target acceptance: axis limits and rule A
  (``00_docs/01_dynamics/dynamics_model.md`` 3.12.6).
* ``ground_contact`` - physics-based combined contact judge and the leg probe.
* ``standstill`` - C2 R5 gyro standstill pieces: CHECK bias estimate (B1') and the GE1'
  standstill gate.
* ``c8`` - :class:`C8Controller`, the alternative C8 (two-phase), skeleton only.
"""
