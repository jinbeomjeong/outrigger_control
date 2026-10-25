"""S8 rev. 43 runner changes on a real L2b-NSC job (``run_S8C.job_l2b_s8``):

* C-S8-17: with the end rule on (``duration_s`` None) a run that does not reach its end time
  before the upper bound ends there and is marked ``timeout`` (``result.json s8_end``) with the
  phase lengths;
* C-S8-16 ①: ``s8_series.npz`` carries ``F_nominal_N`` / ``F_lower_est_N`` and
  ``F_lower_est_N = F_lower_N - leg_band_N`` (the controller's ``_load_estimate_N``)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("pychrono")

pytestmark = pytest.mark.chrono

ROOT = Path(__file__).resolve().parents[2]


def test_end_rule_timeout_and_series_fields(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OUTRIGGER_S8_CRAWLER", "rigid")
    monkeypatch.setenv("OUTRIGGER_RUN_PLACEMENT", "none")
    sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))
    import run_S8C

    original = run_S8C.end_rule

    def short_rule(case):
        return {**original(case), "upper_s": 0.5}

    monkeypatch.setattr(run_S8C, "end_rule", short_rule)
    case = run_S8C.case_table()["smoke_K0_top_rpBop_Fs0"]
    summary, _meta = run_S8C.job_l2b_s8(case, tmp_path, duration_s=None)
    end = summary["s8_end"]
    assert end["applied"] is True and end["timeout"] is True
    assert end["stopped_at_target"] is False and end["target_t_s"] is None
    assert end["end_t_s"] == pytest.approx(0.5, abs=1e-6)
    assert end["anchor"] == "ready" and end["after_s"] == 10.0
    assert end["phase_lengths"]["total_s"]  # at least CHECK
    with np.load(tmp_path / run_S8C.S8_SERIES_NAME) as s:
        for k in ("F_nominal_N", "F_lower_est_N", "F_lower_N", "leg_band_N"):
            assert k in s.files and s[k].shape == (5, 4)
        low, est, band = s["F_lower_N"], s["F_lower_est_N"], s["leg_band_N"]
        ok = np.isfinite(low) & np.isfinite(est) & np.isfinite(band)
        assert ok.any()
        np.testing.assert_allclose(est[ok], (low - band)[ok], rtol=0, atol=1e-6)
