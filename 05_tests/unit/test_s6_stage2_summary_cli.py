"""``04_scripts/02_chrono/s6_stage2_summary``: command line (``--tag``, ``--jobs``,
``--placement``) and the picklable pool job of the parallel path."""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "04_scripts" / "02_chrono"))

import s6_stage2_summary as sm  # noqa: E402


def test_defaults_are_serial_without_placement() -> None:
    assert sm._parse_args(["b"]) == (["b"], "", 1, "os")


def test_tag_jobs_placement_both_spellings() -> None:
    got = sm._parse_args(["b", "o", "--tag", "re3b", "--jobs", "8", "--placement", "ecore"])
    assert got == (["b", "o"], "re3b", 8, "ecore")
    got = sm._parse_args(["--jobs=4", "b", "--placement=pcore", "--tag=x"])
    assert got == (["b"], "x", 4, "pcore")


@pytest.mark.parametrize("argv", [
    ["b", "--jobs"], ["b", "--jobs", "0"], ["b", "--jobs", "two"],
    ["b", "--placement", "efficiency"], ["b", "--threads", "2"], ["--jobs", "2"],
])
def test_bad_arguments_stop(argv: list[str]) -> None:
    with pytest.raises(SystemExit):
        sm._parse_args(argv)


def test_pool_job_is_a_module_function() -> None:
    """ProcessPoolExecutor (spawn on Windows) pickles the job by reference."""
    assert pickle.loads(pickle.dumps(sm._case_metrics_job)) is sm._case_metrics_job
    assert set(sm.PLACEMENTS) == {"os", "ecore", "pcore"}
