"""U-S9-G6d = (가) (2026-10-28, spec rev. 75 393): P3-1 recontact events on the S9 runner
(``run_S9.recontact_events``): a recontact after the departure confirmation lasting <= 0.5 s, ended
before the LOC and peaking <= 0.15 W is a FLAG (``P3-1_transient_recontact``); longer, after the LOC
or without LOC fails."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

import run_S9  # noqa: E402

W = 380_000.0


def _crawler(bumps):
    """Crawler normal: loaded until 10 s, off after it, plus (start, duration, peak / W) bumps."""
    t = np.arange(0.0, 40.0, 1e-3)
    cn = np.where(t < 10.0, 0.5 * W, 0.0)
    for t0, d, f in bumps:
        cn[(t >= t0) & (t < t0 + d)] = f * W
    return t, cn


def _run(bumps, t_loc):
    t, cn = _crawler(bumps)
    dep = run_S9.crawler_departure(t, cn, W)
    assert dep["departed"] and dep["t_departure_s"] == pytest.approx(10.0)
    return run_S9.recontact_events(t, cn, W, dep, t_loc)


def test_transient_before_loc_is_a_flag() -> None:
    r = _run([(12.0, 0.3, 0.13)], t_loc=14.0)
    (e,) = r["events"]
    assert e["t_start_s"] == pytest.approx(12.0) and e["t_end_s"] == pytest.approx(12.3)
    assert e["duration_s"] == pytest.approx(0.3, abs=1e-6) and e["max_over_W"] == pytest.approx(0.13)
    assert e["ended_before_loc"] and e["class"] == "transient_flag"
    assert r["pass"] and r["flags"] == ["P3-1_transient_recontact"]


@pytest.mark.parametrize(("bumps", "t_loc"), [
    ([(12.0, 0.6, 0.13)], 14.0),   # 0.6 s > 0.5 s
    ([(15.0, 0.3, 0.13)], 14.0),   # after the LOC
    ([(12.0, 0.3, 0.16)], 14.0),   # 0.16 W > 0.15 W
    ([(12.0, 0.3, 0.13)], None),   # no LOC
    ([(12.0, 0.3, 0.13)], 12.2),   # LOC during the recontact (not ended before it)
])
def test_strict_failures(bumps, t_loc) -> None:
    r = _run(bumps, t_loc)
    assert [e["class"] for e in r["events"]] == ["strict_fail"] and not r["pass"] and r["flags"] == []


def test_mixed_events_and_checks() -> None:
    r = _run([(12.0, 0.3, 0.13), (20.0, 0.2, 0.05)], t_loc=14.0)
    assert [e["class"] for e in r["events"]] == ["transient_flag", "strict_fail"] and not r["pass"]
    assert r["flags"] == ["P3-1_transient_recontact"]
    none = _run([], t_loc=14.0)
    assert none["events"] == [] and none["pass"] and none["flags"] == []


def test_existing_p3b_definitions_untouched() -> None:
    assert len(run_S9.p3b_cases()) == 24 and all("soil_patch" not in c for c in run_S9.p3b_cases())
