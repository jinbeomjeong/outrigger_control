"""``04_scripts/02_chrono/s6_ge1_export``: R5 name check, the true-path pad height and the
``--tag`` output names."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "04_scripts" / "02_chrono"))

import s6_ge1_export as ex  # noqa: E402
import s6_stage2  # noqa: E402


def _sample(**drop):
    v = {"heights_delta_above_others_m": [0.0] * 4, "nonplanarity_m": -0.008,
         "nonplanarity_delta_m": 0.0, "reference_t_s": 1.0, "is_geometry_valid": True,
         "stationary_gate": {"is_open": True, "motion_rms_rad_s": [1e-4, 2e-4]}}
    for k in drop:
        v.pop(k)
    return v


def test_missing_r5_name_fails_clearly() -> None:
    ex.check_keys([(0.0, "touch", None), (0.02, "ready", _sample())], "c")
    with pytest.raises(ex.GE1KeyError, match="is_geometry_valid"):
        ex.check_keys([(0.02, "ready", _sample(is_geometry_valid=None))], "c")
    assert ex.check_keys([(0.0, "touch", None)], "c") is False  # never touched down
    assert set(ex.R5_KEYS) == set(s6_stage2.GE1_R5_REQUIRED)
    cols = ex._scalars("gate_", _sample()["stationary_gate"])
    assert cols == {"gate_is_open": True, "gate_motion_rms_rad_s_roll": 1e-4,
                    "gate_motion_rms_rad_s_pitch": 2e-4}


def test_true_pad_height_is_the_floor_point_not_the_ball() -> None:
    """Pad bottom = contact point + N / k_n along n: a load change moves the ball by dF / k_n,
    the floor point stays (dynamics-expert 2026-10-22)."""
    kn = np.full(4, 2.1e7)
    n = np.tile([0.0, 0.0, 1.0], (2, 4, 1))
    load = np.array([[119e3, 117e3, 74e3, 72e3], [67e3, 156e3, 74e3, 72e3]])
    floor_z = 0.0
    cp = np.zeros((2, 4, 3))
    cp[..., 2] = floor_z - load / kn  # ball bottom sits N / k_n into the floor
    h = ex.true_pad_heights({"n_world": n, "contact_point_world": cp, "N": load}, kn)
    np.testing.assert_allclose(h, floor_z, atol=1e-12)
    lifted = {"n_world": n, "contact_point_world": cp + [0, 0, 0.01], "N": -load}
    np.testing.assert_allclose(ex.true_pad_heights(lifted, kn), cp[..., 2] + 0.01)


def test_median_rule_one_leg_down() -> None:
    d = ex._median_rule(np.array([[0.0, 0.0, 0.0, -0.006]]))
    np.testing.assert_allclose(d[0], [0.0, 0.0, 0.0, -0.006], atol=1e-15)


def test_re3_sets() -> None:
    sets = s6_stage2.RERUN_SETS
    assert len(sets["RE3"]) == len(set(sets["RE3"])) == 38
    assert set(sets["RE3new"]) <= set(sets["RE3"])
    cases = {c.case_id: c for c in s6_stage2.stage2_cases()}
    assert cases["RE1bF_top_flat_dropRR30_normal"].grade == "normal_zeroed"
    assert cases["G3_top_fdown3.5_normal_zeroed_s12347"].seed == 12347
    assert all(cases[c].fine_dt for c in sets["RE3new"] if c.startswith("RE1b"))
    # spec rev. 8 44.6: check_max_s - check_time_s = 8 s on every case with CHECK, none without
    assert s6_stage2.check_extra_s(cases["G3_top_fdown3.5_normal_zeroed_s12346"]) == 8.0
    assert s6_stage2.check_extra_s(cases["G3_top_flat_good_zeroed"]) == 8.0
    assert cases["G5_top_flat_change_p3"].duration_s == pytest.approx(97.0 + 8.0)
    assert s6_stage2.check_extra_s(cases["G1_top_flat"]) == 0.0
    assert s6_stage2.gyro_noise_std_for("ideal") == 0.0
    sigma = s6_stage2.gyro_noise_std_for
    assert sigma("normal_zeroed") > sigma("good_zeroed") > 0


def test_true_delta_uses_the_case_relative_reference_time() -> None:
    """reference_t_s is absolute controller time: the export subtracts the case start t0."""
    tp = np.arange(0.0, 10.0, 1e-3)  # case-relative pad record
    h = np.zeros((tp.size, 4))
    h[tp >= 5.0, 3] = -0.006  # RR 6 mm down from 5 s on
    t0 = 68.5
    j = int(np.searchsorted(tp, 8.0))
    ref_abs = t0 + 6.0  # reference after the drop -> no change since then
    assert ex.true_delta_heights(h, tp, j, ref_abs - t0) == pytest.approx([0.0] * 4)
    ref_abs = t0 + 2.0  # reference before the drop -> RR -6 mm
    d = ex.true_delta_heights(h, tp, j, ref_abs - t0)
    assert d[3] == pytest.approx(-0.006) and d[:3] == pytest.approx([0.0] * 3)
    assert ex.true_delta_heights(h, tp, j, None) == [None] * 4


def test_touch_only_reference_is_reported_not_judged() -> None:
    """U59 / J-6 (spec 55.7): (1') of a pressure-judge case (touch_only reference) is info."""
    gate = {"n": 10, "grounded_dD_maxabs_mm": 2.80, "dr_maxabs_mm": 0.3}
    case = {"group": "G6", "t_event_s": None, "gate_open": gate, "gate_before_event": gate,
            "rows": [], "event": None, "reference_source": "touch_only"}
    combined = {**case, "reference_source": "ready"}
    rows = ex.promotion_checks({"p": case, "c": combined}, None, None)
    first = {r["case"]: r for r in rows if r["check"].startswith("(1')")}
    assert first["p"]["passed"] is None and first["p"]["kind"] == "info"
    assert first["p"]["passed_raw"] is False
    assert first["c"]["passed"] is False


def test_tag_names_the_export_and_the_check4_summary() -> None:
    """``--tag X`` -> ``verify_S6_L1_ge1_X.json`` and check (4) against
    ``verify_S6_L1_closed_loop_X.json``; no tag keeps the RE3 names."""
    out, summary = ex.output_paths("re3b")
    assert (out.name, summary.name) == ("verify_S6_L1_ge1_re3b.json",
                                        "verify_S6_L1_closed_loop_re3b.json")
    assert out.parent == summary.parent == ex.OUT_DIR
    default = ex.output_paths()
    assert [p.name for p in default] == ["verify_S6_L1_ge1_re3.json",
                                         "verify_S6_L1_closed_loop_re3.json"]
    assert ex.OUT == default[0]
    for bad in ("", "a/b", "a\\b", " x", "c:", "a\tb"):
        with pytest.raises(ValueError, match="bad tag"):
            ex.output_paths(bad)


def test_parse_args_tag_and_overrides(tmp_path: Path) -> None:
    b, prev, o1, o2 = (tmp_path / n for n in ("batch", "prev.json", "o1", "o2"))
    batch, p, over, tag = ex.parse_args([str(b), str(prev), "--override", str(o1),
                                         "--tag", "re3b", f"--override={o2}"])
    assert (batch, p, over, tag) == (b.resolve(), prev.resolve(),
                                     (o1.resolve(), o2.resolve()), "re3b")
    assert ex.parse_args([str(b), "--tag=x"])[1:] == (None, (), "x")
    assert ex.parse_args([str(b)])[3] == ex.DEFAULT_TAG
    for argv in ([str(b), "--tag"], [str(b), "--jobs", "2"], [], [str(b), "p", "q"],
                 [str(b), "--tag", "a/b"]):
        with pytest.raises(SystemExit):
            ex.parse_args(argv)


def test_main_writes_the_tagged_file_only(tmp_path: Path, monkeypatch) -> None:
    """main(tag=...) writes ``<OUT_DIR>/verify_S6_L1_ge1_<tag>.json`` and records the tag and
    the check (4) summary of the same tag in the meta."""
    import json

    monkeypatch.setattr(ex, "OUT_DIR", tmp_path / "out")
    batch = tmp_path / "batch"
    (batch / "c1").mkdir(parents=True)  # no result.json: skipped
    path = ex.main(batch, None, (), tag="t1")
    assert path == tmp_path / "out" / "verify_S6_L1_ge1_t1.json"
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == [path.name]
    meta = json.loads(path.read_text(encoding="utf-8"))["meta"]
    assert meta["tag"] == "t1"
    assert meta["check4_new_summary"].endswith("verify_S6_L1_closed_loop_t1.json")
