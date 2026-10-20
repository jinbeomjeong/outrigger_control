"""Controller protocol and leveling controllers (engine-independent).

Modules (00_docs/03_chrono/chrono_build_plan.md 3.1, 3.3, S6):

* ``protocol`` - :class:`Controller` (Measurements -> Command every control period).
* ``hold`` - :class:`HoldController`, the empty controller (all legs stopped).
* ``c2`` - :class:`C2Controller`, the C2 levelling controller (``00_docs/04_control/c2_design.md``
  section 14).
* C8 leveling controller: alternative, not implemented.
"""
