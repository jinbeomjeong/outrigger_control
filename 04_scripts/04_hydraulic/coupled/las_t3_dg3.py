"""One Dg-3 record of T-3 (sealed ``las_targeted_rules_rev3.md`` 2.1 R-0 / T-3b): the r79 noise
runner ``04_scripts/03_control/s8/r79_L3L4_final.py`` unchanged, under the run condition of the
stored folder and of the bundle, set from two environment variables at import (so the spawned
pool workers, which re-import this file as ``__mp_main__``, get the same condition):

  LAS_T3_DG3_LAS  ``on``: the R8 preset as it is (LAS-b b0 on, T-3b). ``off``: the preset with
                  ``liftoff_approach_slow=False`` by ``05_tests/unit/pre_las_preset_runner.py``
                  (R-0; the same switch as that runner, which is imported for it).
  LAS_T3_DG3_P3   ``on``: setting ``VB`` as it is now (③ start bound on, the ``v4_on`` folder).
                  ``off``: ``VB`` without ``extend_start_tracked`` (the ``off`` folder: the stored
                  run was made at d1ec93f, when ``VB`` had no ③ option and the preset kept the
                  constant start rule; ``hydraulic_options`` of that record has no ③ key either).
Every run records ``two_pressure.extend_start_rule`` and ``liftoff_approach_slow.enable`` in its
``controller_settings``, plus the whole controller config (``full_config`` and its sha256, rev4a
4 #2); the record's ``hydraulic_options`` are the options the plant used. ``las_t3.py`` compares
both with the stored record and checks the ③ rule (rev4a 4). One job = one new process
(``las_t3.py`` worker -> this file -> one r79 pool worker): off and v4_on never share a process.
The parent refuses to start when the preset's LAS-b state is not the one asked for.

Usage (by ``las_t3.py``; dynamics-dev, env R79_V5_SETTING / R79_T4H_DIR / R72_PATH set):
  python -I -B las_t3_dg3.py <project_root> run <out_json> --levels L2,L3 --keys <plain key>
      --workers 1 [--affinity 0x...]
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
S8_DIR = ROOT / "04_scripts" / "03_control" / "s8"
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
PRE_LAS_RUNNER = ROOT / "05_tests" / "unit" / "pre_las_preset_runner.py"
LAS_ENV = "LAS_T3_DG3_LAS"
P3_ENV = "LAS_T3_DG3_P3"
SWITCH_VALUES = ("on", "off")
P3_OPTION = "extend_start_tracked"
VB_SETTING = "VB"
for _path in (S8_DIR, COUPLED_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


def _switch(name: str) -> str:
    value = os.environ.get(name, "")
    if value not in SWITCH_VALUES:
        raise SystemExit(f"{name} must be one of {SWITCH_VALUES}, got {value!r}")
    return value


def _turn_las_off() -> None:
    """Run ``pre_las_preset_runner.py`` as a module: it patches the preset at import."""
    spec = importlib.util.spec_from_file_location("pre_las_preset_runner", PRE_LAS_RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def _turn_p3_off() -> None:
    import run_v5

    has_flow_limit, plant = run_v5.SETTINGS[VB_SETTING]
    run_v5.SETTINGS[VB_SETTING] = (has_flow_limit,
                                   {k: v for k, v in plant.items() if k != P3_OPTION})


def apply_run_condition() -> tuple[str, str]:
    """The LAS-b and ③ condition of this process from the environment; returns both."""
    las, p3 = _switch(LAS_ENV), _switch(P3_ENV)
    if las == "off":
        _turn_las_off()
    if p3 == "off":
        _turn_p3_off()
    return las, p3


LAS_STATE, P3_STATE = apply_run_condition()

import r79_L3L4_final as final  # noqa: E402  (after the condition: it reads the preset)

final.RECORDED_SETTINGS = (*final.RECORDED_SETTINGS, "two_pressure.extend_start_rule",
                           "liftoff_approach_slow.enable")
FULL_CONFIG_KEY = "full_config"
FULL_CONFIG_SHA_KEY = "full_config_sha256"
_recorded_settings = final.controller_settings


def controller_settings_with_full_config(config) -> dict:
    """The r79 settings plus the whole controller config of the run (rev4a 4 #2: every
    setting is recorded; the stored records hold the r79 subset, which is what is compared)."""
    import dataclasses
    import hashlib
    import json

    text = json.dumps(dataclasses.asdict(config), default=str, sort_keys=True)
    return {**_recorded_settings(config), FULL_CONFIG_KEY: json.loads(text),
            FULL_CONFIG_SHA_KEY: hashlib.sha256(text.encode("utf-8")).hexdigest()}


final.controller_settings = controller_settings_with_full_config


def main() -> None:
    from outrigger_sim.control import c2

    is_las_on = bool(c2.C2Config().with_10hz_d1().liftoff_approach_slow.enable)
    print(f"T-3 Dg-3 condition: LAS-b {LAS_STATE} (preset {is_las_on}), ③ {P3_STATE}",
          flush=True)
    if is_las_on != (LAS_STATE == "on"):
        raise SystemExit(f"the preset has LAS-b {is_las_on}, {LAS_ENV}={LAS_STATE}")
    final.main()


if __name__ == "__main__":
    main()
