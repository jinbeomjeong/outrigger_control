"""Episode schema (outrigger_sim.contact_episode): validation, npz round trip, case-folder build."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.contact_episode import (
    UNRECORDED_CRAWLER,
    Episode,
    EpisodeError,
    MachineConstants,
    build_episode,
    count_by_crawler_contact,
    load_episode,
    normalize_sensor_meta,
    save_episode,
)
from outrigger_sim.ml.synthetic import synthetic_cases, synthetic_episode

CASE = (Path(__file__).resolve().parents[2] / "07_results" / "S6"
        / "bundleC_rerun34_L1R_20261024_141040" / "C1_G4_combined_ph0.075")
S8_CASE = (Path(__file__).resolve().parents[2] / "07_results" / "S8"
           / "p1r_20261024_222013" / "E_G4_Fs0")


@pytest.fixture(scope="module")
def episode() -> Episode:
    return synthetic_episode(synthetic_cases(1, 1, seed=7)[0], duration_s=30.0)


def test_round_trip_keeps_arrays_and_meta(episode, tmp_path):
    path = save_episode(episode, tmp_path / "ep.npz")
    again = load_episode(path)
    assert set(again.arrays) == set(episode.arrays)
    for name, value in episode.arrays.items():
        np.testing.assert_array_equal(again[name], value)
    assert again.meta["base_id"] == episode.meta["base_id"]
    assert again.meta["controller"]["r8"]["confirmation"]["relevel_samples"] == 2


def test_missing_or_misshaped_fields_are_rejected(episode):
    arrays = dict(episode.arrays)
    arrays.pop("seal_band_N")
    with pytest.raises(EpisodeError, match="seal_band_N"):
        Episode(arrays, episode.meta)
    arrays = dict(episode.arrays, touched=np.ones((3, 4), dtype=bool))
    with pytest.raises(EpisodeError, match="touched: shape"):
        Episode(arrays, episode.meta)
    arrays = dict(episode.arrays, probe_round_end=episode["probe_round_end"].astype(float))
    with pytest.raises(EpisodeError, match="dtype"):
        Episode(arrays, episode.meta)


def test_wrong_format_is_rejected(episode, tmp_path):
    path = tmp_path / "bad.npz"
    np.savez(path, **episode.arrays, meta_json=np.array(json.dumps({"format": "other"})))
    with pytest.raises(EpisodeError, match="format"):
        load_episode(path)


@pytest.mark.parametrize(
    ("meta", "expected"),
    [
        # Legacy S8 runner meta: one combined string (spec rev. 44 214.5 question 3-5).
        ({"sensor_grade": "normal_no_cal"}, ("normal", False, "normal_no_cal")),
        ({"sensor_grade": "old_worst_no_cal"}, ("old_worst", False, "old_worst_no_cal")),
        # New runner meta: two fields plus the display string.
        ({"sensor_grade": "conservative", "zero_calibration": True,
          "sensor_condition": "conservative"}, ("conservative", True, "conservative")),
        ({"sensor_grade": "normal", "zero_calibration": False},
         ("normal", False, "normal_no_cal")),
        # No flag: the controller meta tells; nothing at all stays unknown.
        ({"sensor_grade": "normal", "controller": {"zero_calibration": {"is_active": True}}},
         ("normal", True, "normal")),
        ({"sensor_grade": "normal"}, ("normal", None, "normal")),
        ({}, (None, None, None)),
    ],
)
def test_sensor_meta_is_split_into_grade_and_calibration(meta, expected):
    normalized = normalize_sensor_meta(meta)
    got = tuple(normalized.get(key)
                for key in ("sensor_grade", "zero_calibration", "sensor_condition"))
    assert got == expected


def test_sensor_meta_rejects_a_no_cal_grade_with_calibration_on():
    with pytest.raises(EpisodeError, match="zero_calibration"):
        normalize_sensor_meta({"sensor_grade": "normal_no_cal", "zero_calibration": True})


def test_legacy_combined_grade_reads_as_two_fields(episode, tmp_path):
    legacy_meta = {key: value for key, value in episode.meta.items()
                   if key not in ("zero_calibration", "sensor_condition")}
    legacy = Episode(episode.arrays, {**legacy_meta, "sensor_grade": "normal_no_cal"})
    again = load_episode(save_episode(legacy, tmp_path / "legacy.npz"))
    assert again.meta["sensor_grade"] == "normal"
    assert again.meta["zero_calibration"] is False
    assert again.meta["sensor_condition"] == "normal_no_cal"


def test_build_from_a_bundle_c_case_reproduces_the_controller_band():
    if not (CASE / "record" / "record.npz").is_file():
        pytest.skip(f"record not present: {CASE}")
    from outrigger_sim.control.c2 import C2Geometry
    from outrigger_sim.params import load_params

    geometry = C2Geometry.from_params(load_params(level="top"))
    episode = build_episode(CASE, MachineConstants.from_geometry(geometry))
    result = json.loads((CASE / "result.json").read_text(encoding="utf-8"))
    final_band = result["controller_meta"]["seal_band_N"]
    assert episode["seal_band_N"][-1] == pytest.approx(np.full(4, final_band))
    assert episode["seal_band_N"][0] == pytest.approx(np.full(4, 13000.0))
    assert episode["is_lifted"][-1] and not episode["is_lifted"][0]
    offsets = np.asarray(result["controller_meta"]["zero_calibration"]["offsets_N"])
    np.testing.assert_allclose(episode["net_force_N"][-1] - episode["lower_reading_N"][-1],
                               offsets)
    assert np.isfinite(episode["true_force_min_N"][-1]).all()
    assert "seal_band_N" in episode.meta["reconstructed"]
    # Bundle C predates the S8 crawler meta (spec rev. 45 215.8): both stay unknown.
    assert episode.meta["crawler_contact"] is None
    assert episode.meta["crawler_check_passed"] is None


def test_build_from_an_s8_case_keeps_the_crawler_meta(tmp_path):
    if not (S8_CASE / "record" / "record.npz").is_file():
        pytest.skip(f"record not present: {S8_CASE}")
    from outrigger_sim.control.c2 import C2Geometry
    from outrigger_sim.params import load_params

    geometry = C2Geometry.from_params(load_params(level="top"))
    episode = build_episode(S8_CASE, MachineConstants.from_geometry(geometry))
    assert episode.meta["crawler_contact"] == "nsc_rigid"
    assert episode.meta["crawler_check_passed"] is False
    again = load_episode(save_episode(episode, tmp_path / "s8.npz"))
    assert again.meta["crawler_contact"] == "nsc_rigid"
    assert again.meta["crawler_check_passed"] is False


def test_crawler_counts_name_the_unrecorded_episodes():
    metas = [
        {"crawler_contact": "nsc_rigid", "crawler_check_passed": False},
        {"crawler_contact": "nsc_rigid", "crawler_check_passed": False},
        {"crawler_contact": "nsc_compliant", "crawler_check_passed": True},
        {"crawler_contact": None},
        {},
    ]
    assert count_by_crawler_contact(metas) == {
        "nsc_compliant": 1, "nsc_rigid": 2, UNRECORDED_CRAWLER: 2,
    }
