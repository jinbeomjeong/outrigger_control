"""``run_S9 level --k2 {preset,off,on}`` (K-2 TOUCH creep latch) and the registered tags refusing K-2.

No Chrono run: the ``level`` arguments are parsed and the run-time C2 config is built as ``run_S9 level`` builds
it before the model (the ``test_las_k1_chrono_rows.py`` way).
"""

from __future__ import annotations

import pickle
import sys
from dataclasses import replace
from pathlib import Path

import pytest

CHRONO_SCRIPTS = Path(__file__).resolve().parents[2] / "04_scripts" / "02_chrono"


@pytest.fixture(scope="module")
def run_s9():
    pytest.importorskip("pychrono")
    sys.path.insert(0, str(CHRONO_SCRIPTS))
    try:
        return __import__("run_S9")
    finally:
        sys.path.remove(str(CHRONO_SCRIPTS))


def _config_of(run_s9, tokens: list[str]):
    args = run_s9.build_parser().parse_args(["level", "--soil", "G1", *tokens, "--case", "x", "--out-root", "x"])
    return args, *run_s9.level_c2_config_of_args(args)


def _preset():
    from outrigger_sim.control.c2 import C2Config

    return C2Config().with_10hz_d1()


def test_absent_option_keeps_the_preset_bits(run_s9) -> None:
    args, config, meta = _config_of(run_s9, [])
    assert not hasattr(args, "k2")
    assert config == _preset() and pickle.dumps(config, protocol=4) == pickle.dumps(_preset(), protocol=4)
    assert meta["touch_creep"] == "preset" and meta["touch_creep_effective"] is False


@pytest.mark.parametrize("value", ["off", "on"])
def test_explicit_request_sets_only_the_latch(run_s9, value) -> None:
    from outrigger_sim.control.c2 import TouchCreepLatchSettings

    _, config, meta = _config_of(run_s9, ["--k2", value])
    assert config.touch_creep_latch.enable is (value == "on")
    assert replace(config, touch_creep_latch=TouchCreepLatchSettings()) == _preset()
    assert meta["touch_creep"] == value and meta["touch_creep_effective"] is (value == "on")


def test_registered_tags_refuse_a_k2_config(run_s9) -> None:
    from outrigger_sim.control.c2 import C2Config

    on = C2Config().with_10hz_d1(touch_creep_latch=True)
    for tag in run_s9.CONTROLLER_EXPECTATIONS:
        if tag.endswith("_TCL"):  # the K-2 tag itself (V-7, cad 2026-11-10)
            continue
        record = run_s9.controller_expectation(on, tag)
        assert "touch_creep_latch.enable" in {c["path"] for c in record["checks"] if not c["ok"]}, tag
    assert run_s9.controller_expectation(C2Config().with_10hz_d1(), run_s9.FINAL_LAS_K1_CONTROLLER)["ok"]
