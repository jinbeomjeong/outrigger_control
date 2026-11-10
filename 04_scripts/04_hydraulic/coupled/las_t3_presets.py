"""Preset switch of the R-0K bundle of T-3 (sealed ``las_targeted_rules_rev5.md`` 2.2).

R-0K runs the R8 preset with LAS-b off and the K1 order gate as the preset has it (on since
the K1 switch): the LAS-b single-variable pair of T-3K (tags ``final_C4G2_K1`` /
``final_C4G2_P3_K1``). :func:`install_las_off_gate_on` gives ``C2Config.with_10hz_d1`` the
default ``liftoff_approach_slow=False`` and nothing else; a caller that passes the keyword
explicitly still gets what it asks for (as ``05_tests/unit/pre_las_preset_runner.py``, which
turns the gate off as well and is the R-0 switch).

``las_t3.py`` allows this module's ``with_10hz_d1`` on the config class of an R-0K worker only
(``wrapper_problems``), so nothing else may be added here.
"""
from __future__ import annotations

R0K_LIFTOFF_APPROACH_SLOW = False

_installed: dict[str, bool] = {}


def install_las_off_gate_on() -> None:
    """Patch ``C2Config.with_10hz_d1`` of this process to default LAS-b off (once).

    A second call is a no-op: wrapping the wrapper would change nothing but would hide which
    function the preset is.
    """
    if _installed:
        return
    from outrigger_sim.control import c2

    switched_preset = c2.C2Config.with_10hz_d1

    def with_10hz_d1(self, *, liftoff_approach_slow: bool = R0K_LIFTOFF_APPROACH_SLOW,
                     **keywords):
        return switched_preset(self, liftoff_approach_slow=liftoff_approach_slow, **keywords)

    c2.C2Config.with_10hz_d1 = with_10hz_d1
    _installed["with_10hz_d1"] = True
