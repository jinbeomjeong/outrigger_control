"""436.8 rev18 R18-2 / R18-5: ``resume4368_judge.py fmin-time`` t_D by rev6 R6-B4 (100 samples)
and times as samples x 1 ms (rev2 R2-5). Synthetic inputs only."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "06_analysis" / "02_control" / "verif_matrix" / \
    "scripts"


@pytest.fixture(scope="module")
def judge():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    return importlib.import_module("resume4368_judge")


def write_case(folder: Path, t: np.ndarray, force: np.ndarray, crawler: np.ndarray) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    np.savez(folder / "step_series.npz", t_s=t, F_cyl_N=force, scm_crawler_normal_N=crawler)
    (folder / "result.json").write_text(json.dumps({"p3b": {"weight_N": 400_000.0}}),
                                        encoding="utf-8")
    return folder


def test_departure_needs_100_samples_not_101(judge):
    t = np.round(np.arange(0.0, 2.0, 0.001), 6)
    crawler = np.full(t.size, 100_000.0)
    crawler[500:600] = 0.0  # exactly 100 samples below 0.01 W: t_D by R6-B4
    assert judge.departure_time(t, crawler, 400_000.0) == pytest.approx(0.5)
    crawler[599] = 100_000.0  # 99 samples: no departure
    assert judge.departure_time(t, crawler, 400_000.0) is None


def test_times_are_samples_times_1ms(judge, tmp_path):
    t = np.arange(0, 12_000) * 0.001  # float steps off 1 ms by rounding
    force = np.full((t.size, 4), 30_000.0)
    force[3000:3158, 2] = judge.F_MIN_N - 1.0  # 158 samples below F_min (RL)
    crawler = np.where(t < 2.0, 100_000.0, 0.0)
    case = write_case(tmp_path / "case", t, force, crawler)
    out = tmp_path / "f.json"
    assert judge.main(["fmin-time", "--case", str(case), "--out", str(out)]) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["F_below_F_min"]["ms"] == [0.0, 0.0, 158.0, 0.0]  # exact, not step-scaled
    assert report["F_below_F_min"]["samples"][2] == 158
    assert "R6-B4" in report["definition"]


def test_series_not_1ms_is_not_judgeable(judge, tmp_path):
    t = np.arange(0, 2000) * 0.002
    force = np.full((t.size, 4), 30_000.0)
    case = write_case(tmp_path / "case", t, force, np.zeros(t.size))
    out = tmp_path / "f.json"
    assert judge.main(["fmin-time", "--case", str(case), "--out", str(out)]) == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["status"].startswith("판정 불가") and report["series_step_s"] == pytest.approx(
        0.002)
