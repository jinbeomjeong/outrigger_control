"""436.8 Q-2: ``--expect-controller`` on the L2b (``run_S8C``) and L1-R (``run_S6C``) runners (no Chrono run)."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

pytest.importorskip("pychrono")

import run_S6C as s6c  # noqa: E402
import run_S8C as s8c  # noqa: E402

from outrigger_sim.control.c2 import C2Config  # noqa: E402
from outrigger_sim.hydraulics.v5_options import HydraulicOptions  # noqa: E402


def test_record_of_the_preset_and_the_vb_bound() -> None:
    preset = C2Config().with_10hz_d1()
    assert s6c.run_controller_record(preset) == {"controller_tag": "final_C4G2_LAS_K1"}
    vb = HydraulicOptions(extend_start_tracked=True)
    record = s6c.run_controller_record(preset, vb, "final_C4G2_P3_LAS_K1")
    assert record == {"controller_tag": "final_C4G2_P3_LAS_K1",
                      "expect_controller": {"name": "final_C4G2_P3_LAS_K1",
                                            "controller_tag": "final_C4G2_P3_LAS_K1", "ok": True}}
    s6c.check_run_controller("x", record)


def test_class_default_and_mismatch_stop() -> None:
    assert s6c.run_controller_record(C2Config())["controller_tag"] == "final_C4G2"
    record = s6c.run_controller_record(C2Config().with_10hz_d1(), None, "final_C4G2_P3_LAS_K1")
    assert record["expect_controller"]["ok"] is False
    with pytest.raises(SystemExit, match="!= --expect-controller final_C4G2_P3_LAS_K1"):
        s6c.check_run_controller("D1C2_x", record)


def test_check_runs_before_the_simulation() -> None:
    """The stop comes after the controller is built and before the closed loop starts."""
    for function, loop in ((s8c.job_l2b_s8, "run_closed_loop("), (s6c.job_bundle_c, "run_closed_loop(")):
        source = inspect.getsource(function)
        assert source.index("check_run_controller(") < source.index(loop), function.__name__
        assert "**run_ctrl" in source


def test_option_default_off_and_accepted_outside_d8x() -> None:
    for module in (s6c, s8c):
        source = inspect.getsource(module.main)
        assert '"--expect-controller", dest="expect_controller", default=None' in source
        assert "--expect-controller only with" not in source  # the D8x / K-2-only refusal is gone
    assert "expect_controller" in inspect.signature(s6c.run_batch).parameters
    assert "expect_controller" in inspect.signature(s8c.run_batch).parameters
