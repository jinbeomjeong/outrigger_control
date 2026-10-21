"""S4 branch A V7 check (chrono_build_plan.md S4): one 2 s initial-velocity case.

``sim``: the yaw excitation from the S1 snapshot at the YAML dt (2 s simulated, about 5 s
wall) through the job function of ``04_scripts/02_chrono/run_S4.py``; modes 3 and 6 (the
yaw run is their judged run) must pass the V7 frequency / zeta rule by projection and agree
with the 6-channel ERA. The judging run with every case is ``run_S4.py all`` (summary
``06_analysis/01_chrono/14_S4/verify_S4_L1_modes.json``).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("pychrono")

from outrigger_sim.batch import Case  # noqa: E402
from outrigger_sim.verify.s4 import ModeRow, v7_six_mode_checks  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def _script():
    path = ROOT / "04_scripts" / "02_chrono" / "run_S4.py"
    spec = importlib.util.spec_from_file_location("run_S4_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_S4_under_test"] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.sim
def test_v7_yaw_case_modes_3_and_6(tmp_path: Path) -> None:
    m = _script()
    out = m.job_modes(Case("modes_yaw", m.case_settings("modes_yaw")), tmp_path)
    s = out.summary
    assert s["all_passed"], [c for c in s["checks"] if not c["passed"]]
    rows = []
    for i in (2, 5):
        r = s["modes"][i]
        rows.append(ModeRow(mode=r["mode"], run="yaw", f_proj_Hz=r["f_proj_Hz"],
                            zeta_proj=r["zeta_proj"],
                            fit_residual_rms_rel=r["fit_residual_rms_rel"],
                            f_era_Hz=r["era"]["f_Hz"], zeta_era=r["era"]["zeta"],
                            leakage=r["era"]["leakage"], zeta_num=r["zeta_num"],
                            f_ref_Hz=r["f_ref_Hz"], zeta_ref=r["zeta_ref"]))
        assert r["era"]["mac_vs_phi"] > 0.99
    checks = v7_six_mode_checks(rows, ref_key_f="f", ref_key_zeta="z")
    assert all(c.passed for c in checks), [c for c in checks if not c.passed]
