"""R8 C2 on the equivalent flexible mast (``04_scripts/03_control/r8d1/mast_flex_r8c2.py``).

T1  the driver loop is the c2py flat run bit for bit (commands SHA-256, top / level / rigid,
    tau_v 0.1 s, ideal sensors, no REANCHOR, 120 s limit, READY + 5 s);
T2  ``r8_config(False)`` equals ``c2py_r8d1_closed_loop.preset_config(COMBINED, True)``;
T3  the preset values the judgement rests on;
T4  the plant flex flag follows the case and a mismatch raises;
T5  rmf ``figures()`` with its default arguments draws what the R7 literals drew;
T6  the ``verification`` block of the stored result JSON (frozen kernel, linearisation,
    half-dt convergence, run counts).

The driver imports rmf, which patches ``run_control_comparison.Plant`` in its process, and c2py
patches the harness, so T1..T5 run in two subprocesses. The reduced plant kernel needs numba
(dynamics-dev); the module is skipped elsewhere. About 3 min on the E-cores:
  conda run -n dynamics-dev python -I -B -m pytest -p no:cacheprovider \
      05_tests/unit/test_mast_flex_r8c2.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("numba", reason="the reduced plant kernel needs numba (dynamics-dev)")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DRIVER_DIR = PROJECT_ROOT / "04_scripts" / "03_control" / "r8d1"
RESULT_JSON = PROJECT_ROOT / "06_analysis" / "00_dynamics" / "mast_flex_c2_check_r8.json"
SCRIPT_TIMEOUT_S = 900
R7_CTRL_LABEL = "C2 proposal (delay 1, ramp 0.1 s)"
R7_XLIM = (12, 45)
LINEARISATION_REL_TOL = 0.01
"""Kernel vs linear-equivalent frequencies; the R7 JSON has at most 9.3e-4 (unchanged code)."""
SPEC_PRESET = {  # spec section 3 (R8 C2 preset values; tau_v is the driver ASSUMPTION)
    "period_s": 0.1,
    "imu_sample_period_s": 0.01,
    "output_delay_periods": 1,
    "attitude_kp_1_s": 0.2,
    "attitude_ki_1_s2": 0.01,
    "twist_ktw_1_s": 0.5,
    "guard_kg_1_s": 0.15,
    "attitude_time_constant_s": 0.8,
    "attitude_stage_count": 2,
    "twist_load_time_constant_s": 0.2,
    "increment_fraction_per_period": 0.25,
    "valve_lag_s": 0.1,
}

DRIVER_PROBE = r"""
import inspect, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, sys.argv[1])
import mast_flex_r8c2 as drv
rmf = drv.rmf
out_dir = Path(sys.argv[2])
facts = {}
t1 = drv.run_one(drv.t1_case())
facts["t1"] = {"commands_sha256": t1["commands_sha256"], "phase_final": t1["phase_final"]}
facts["t3"] = drv.preset_constants(drv.r8_config(False))
_, eqs = drv.load_equivalent_masts()
flex = {}
for mast in ("rigid", "upper"):
    eq = rmf.eq_case(eqs, "top", mast)
    rmf.CONFIG.clear(); rmf.CONFIG["mast_eq"] = eq
    plant = rmf.FlexPlant("top")
    flex[mast] = drv.check_plant_flex(plant, eq)
    try:
        drv.check_plant_flex(plant, None if eq is not None else {"mast": "x"})
        flex[mast + "_mismatch_raises"] = False
    except RuntimeError:
        flex[mast + "_mismatch_raises"] = True
facts["t4"] = flex
signature = inspect.signature(rmf.figures).parameters
facts["t5_defaults"] = {"ctrl_label": signature["ctrl_label"].default,
                        "xlim": list(signature["xlim"].default)}
t = np.arange(0.0, 60.0, 0.02)
series = {("top", "diag3", mast): {"t": t, "Ftrue": np.full((t.size, 4), 50e3) + 1e3 * i,
                                   "phi": 0.01 * np.sin(t), "theta": 0.01 * np.cos(t),
                                   "alpha": np.full((t.size, 2), 1e-3 * i)}
          for i, mast in enumerate(("rigid", "upper"))}
images = {}
for name, kwargs in (("default", {}), ("explicit", {"ctrl_label": sys.argv[3], "xlim": (12, 45)})):
    rmf.OUT_DIR = out_dir / name
    rmf.OUT_DIR.mkdir()
    paths = rmf.figures(series, [], "probe", **kwargs)
    images[name] = {p.name: p.read_bytes().hex() for p in paths}
facts["t5_images_equal"] = images["default"] == images["explicit"]
facts["t5_image_names"] = sorted(images["default"])
print(json.dumps(facts))
"""

REFERENCE_PROBE = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
import c2py_r8d1_closed_loop as c2py
import mast_flex_r8c2 as drv
from outrigger_sim.control.c2 import ContactJudge
facts = {
    "t2_config_equal": drv.r8_config(False) == c2py.preset_config(ContactJudge.COMBINED, True),
    "t1_commands_sha256": c2py.run_imu_100hz_flat()["commands_sha256"],
}
print(json.dumps(facts))
"""


def _run_probe(code: str, *args: str) -> dict:
    environment = dict(os.environ, MKL_THREADING_LAYER="TBB", PYTHONDONTWRITEBYTECODE="1")
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", code, str(DRIVER_DIR), *args],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=SCRIPT_TIMEOUT_S,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr[-3000:]
    return json.loads(completed.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def driver_facts(tmp_path_factory) -> dict:
    out_dir = tmp_path_factory.mktemp("mast_r8_figures")
    return _run_probe(DRIVER_PROBE, str(out_dir), R7_CTRL_LABEL)


@pytest.fixture(scope="module")
def reference_facts() -> dict:
    return _run_probe(REFERENCE_PROBE)


def test_t1_driver_loop_reproduces_the_c2py_flat_run(driver_facts, reference_facts) -> None:
    assert driver_facts["t1"]["phase_final"] == "ready"
    assert driver_facts["t1"]["commands_sha256"] == reference_facts["t1_commands_sha256"]


def test_t2_config_is_the_c2py_preset(reference_facts) -> None:
    assert reference_facts["t2_config_equal"] is True


def test_t3_preset_values(driver_facts) -> None:
    assert driver_facts["t3"] == SPEC_PRESET


def test_t4_plant_flex_follows_the_case(driver_facts) -> None:
    assert driver_facts["t4"] == {
        "rigid": 0,
        "rigid_mismatch_raises": True,
        "upper": 1,
        "upper_mismatch_raises": True,
    }


def test_t5_figures_defaults_are_the_r7_literals(driver_facts) -> None:
    assert driver_facts["t5_defaults"] == {"ctrl_label": R7_CTRL_LABEL, "xlim": list(R7_XLIM)}
    assert driver_facts["t5_images_equal"] is True
    assert driver_facts["t5_image_names"] == ["probe_slope_map.png", "probe_timeseries.png"]


@pytest.fixture(scope="module")
def verification() -> dict:
    if not RESULT_JSON.exists():
        pytest.skip(f"{RESULT_JSON.name} not written yet (run the driver --stage main)")
    return json.loads(RESULT_JSON.read_text(encoding="utf-8"))["verification"]


def test_t6_stored_t1_and_frozen_kernel(verification) -> None:
    assert verification["t1_bit_regression"]["is_bit_identical"] is True
    assert verification["frozen_kernel_identity"]["max_abs_state_diff"] == 0.0


def test_t6_kernel_linearisation(verification) -> None:
    for level, entry in verification["kernel_linearisation_vs_linear_equivalent"].items():
        for mast, row in entry.items():
            assert row["max_rel_f_diff"] < LINEARISATION_REL_TOL, (level, mast)


def test_t6_half_dt_convergence(verification) -> None:
    convergence = verification["convergence_half_dt"]
    assert convergence["passes"] is True, convergence["cases"]


def test_t6_run_counts(verification) -> None:
    runs = verification["runs"]
    assert runs["errors"] == 0
    assert runs["plant_flex_mismatch"] == 0
