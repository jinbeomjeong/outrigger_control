"""436.9 edition 8 records and probe plan (``ed7_j9fail_8a2a52ce/cause_analysis.md`` 8 P-1 .. P-3),
no harness run.

* P-2 A(i)-b block reasons (``lock_start_b.BlindBlock``): the first failing test of spec 3.1 per
  leg and LEVEL period, the per-leg and per-stretch counts, the per-read codes; the commands are
  those of the code without the record (the reason is read from the same tests).
* P-1 probe stiffness rounds (``C2Controller.probe_stiffness_record``): K1, ``k_nom``, the ratio
  per leg, the median, the warning and the scale of every round.
* ``verdict_runs`` record switch: off by default, the record keys only with it on.
* P-3 ``ed8_probe`` plan: arms (a2w = a2 without the retract target), plants (LSM1 .. LSM4),
  sources (j9main 388 rows, a jobs file), the option dicts of the sealed settings, refusals.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
for _path in (COUPLED_DIR, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from outrigger_sim.control.lock_start_b import (  # noqa: E402
    BLIND_BLOCK_CODES,
    NO_BLOCK_CODE,
    BlindBlock,
    CompletionFlags,
    CylinderGeometry,
    FloorInputs,
    LockStartB,
    LockStartBSettings,
)

V_MAX = 20.924e-3
T = 0.1
GEOMETRY = CylinderGeometry(head_area_m2=np.full(4, 0.0133), annulus_area_m2=np.full(4, 0.0038),
                            stroke_max_m=0.70, max_speed_m_s=V_MAX, period_s=T,
                            increment_limit_m_s=0.25 * V_MAX)
TWIST = np.array([0.4761, -0.4761, -0.5228, 0.5228])
F_MIN = 9.415e3
SAFE_LOADS = np.full(4, 80.0e3)
DEAD_BAND = 0.1e-3
"""A command inside the dead band (u_hold = 0.209 mm/s)."""
REASONS = tuple(str(reason) for reason in BlindBlock)


def _inputs(t_s: float, command: np.ndarray, stroke: np.ndarray, *, is_level: bool = True,
            completion: CompletionFlags | None = None, twist_N: float = 0.0,
            loads: np.ndarray = SAFE_LOADS, protected: np.ndarray | None = None) -> FloorInputs:
    return FloorInputs(t_s=t_s, is_level=is_level, is_fill_phase=True, is_fault=False,
                       requested_m_s=command, acting_m_s=command, previous_output_m_s=command,
                       stroke_m=stroke, head_Pa=np.full(4, 80e5), rod_Pa=np.full(4, 5e5),
                       protected=np.zeros(4, bool) if protected is None else protected,
                       fallback_legs=frozenset(), completion=completion, twist_load_N=twist_N,
                       twist_limit_N=15.0e3, lower_load_N=loads, force_N=loads + 5e3,
                       F_min_N=F_MIN, twist_vector=TWIST)


def _blind(components: tuple[str, ...] = ("A_ib",), **parameters) -> LockStartB:
    return LockStartB(LockStartBSettings(components=components, **parameters), GEOMETRY)


def _run(rule: LockStartB, periods: int, *, leg: int = 0, speed: float = DEAD_BAND,
         start_k: int = 0, strokes=None, **keywords) -> list[np.ndarray]:
    outputs = []
    for k in range(start_k, start_k + periods):
        command = np.zeros(4)
        command[leg] = speed
        stroke = np.full(4, 0.4) if strokes is None else np.full(4, 0.4) + strokes(k)
        outputs.append(rule.apply_floors(_inputs(k * T, command, stroke, **keywords)))
    return outputs


def _codes(rule: LockStartB, leg: int = 0) -> list[str]:
    """The reason of every logged period of ``leg`` (``"-"`` outside LEVEL)."""
    names = {code: name for name, code in BLIND_BLOCK_CODES.items()}
    arrays = rule.blind_block_arrays_at(np.asarray(rule._trace_t_s))
    return [names.get(int(code), "-") for code in arrays["lsb_ib_block"][:, leg]]


# ------------------------------------------------------------------------ P-2 block reasons
def test_codes_are_the_reason_order_and_off_level_is_minus_one() -> None:
    assert list(BLIND_BLOCK_CODES) == list(REASONS)
    assert list(BLIND_BLOCK_CODES.values()) == list(range(len(REASONS)))
    assert NO_BLOCK_CODE == -1


def test_short_stretch_then_trigger_then_floor_on() -> None:
    rule = _blind()
    _run(rule, 27)
    codes = _codes(rule)
    assert codes[:24] == ["condition_1_short"] * 24
    assert codes[24] == "trigger" and codes[25:] == ["floor_on", "floor_on"]
    assert _codes(rule, leg=1) == ["condition_1_none"] * 27  # zero command
    record = rule.blind_block_record()
    assert record["level_periods"] == 27
    assert record["legs"]["FL"] == {**dict.fromkeys(REASONS, 0), "condition_1_short": 24,
                                    "trigger": 1, "floor_on": 2}
    assert record["legs"]["FR"]["condition_1_none"] == 27


@pytest.mark.parametrize(("keywords", "reason"), [
    ({"strokes": lambda k: np.array([k * 0.15e-3 * T, 0, 0, 0])}, "condition_2"),
    ({"completion": CompletionFlags(True, True, False), "twist_N": 10.0e3}, "condition_3"),
    ({"loads": np.array([12.0e3, 80.0e3, 80.0e3, 80.0e3]), "leg": 3, "speed": -DEAD_BAND},
     "protect"),
    ({"protected": np.array([True, False, False, False])}, "priority"),
])
def test_the_first_failing_test_after_the_stretch(keywords, reason) -> None:
    leg = keywords.get("leg", 0)
    rule = _blind()
    _run(rule, 30, **keywords)
    codes = _codes(rule, leg)
    assert codes[24:] == [reason] * 6, codes
    counts = rule.blind_block_record()["legs"]["FL" if leg == 0 else "RR"]
    assert counts[reason] == 6 and sum(counts.values()) == 30
    if reason == "protect":  # the same periods the edition 7 counter holds back
        assert rule.blind_counts[leg].protect_blocked_periods == 6


def test_latch_period_and_the_latched_stretch() -> None:
    rule = _blind()
    t = 0
    for cycle in range(5):
        _run(rule, 27, speed=DEAD_BAND if cycle % 2 == 0 else -DEAD_BAND, start_k=t)
        t += 27
        _run(rule, 1, speed=0.0, start_k=t)  # a zero ends the floor
        t += 1
    codes = _codes(rule)
    assert codes.count("trigger") == 3 and codes.count("latch") == 1
    after = codes[codes.index("latch") + 1:]
    assert after and set(after) == {"latched"}
    assert rule.blind_counts[0].latches == 1


def test_stretches_end_outside_level_and_codes_are_minus_one_there() -> None:
    rule = _blind()
    _run(rule, 3)
    _run(rule, 2, start_k=3, is_level=False)
    _run(rule, 4, start_k=5)
    record = rule.blind_block_record()
    first, second = record["stretches"]
    assert (first["start_t_s"], first["end_t_s"], first["periods"]) == (
        0.0, pytest.approx(0.3), 3)
    assert (second["start_t_s"], second["end_t_s"], second["periods"]) == (
        pytest.approx(0.5), None, 4)
    assert second["legs"]["FL"]["condition_1_short"] == 4
    assert set(second["legs"]["RR"]) == set(REASONS)
    arrays = rule.blind_block_arrays_at(np.arange(9) * T)
    assert arrays["lsb_ib_block"][3:5].tolist() == [[NO_BLOCK_CODE] * 4] * 2
    assert arrays["lsb_ib_block"].dtype == np.int8
    missing = rule.blind_block_arrays_at(np.array([99.0]))
    assert missing["lsb_ib_block"].tolist() == [[NO_BLOCK_CODE] * 4]


def test_the_record_leaves_the_commands_of_edition_7() -> None:
    """The reasons are read from the tests the trigger already makes (no extra state): two
    rules with one more record read between their periods give the same outputs."""
    plain, read = _blind(), _blind()
    for k in range(80):
        speed = DEAD_BAND if k % 40 < 30 else -DEAD_BAND
        command = np.array([speed, 0.0, -DEAD_BAND, 0.0])
        stroke = np.full(4, 0.4)
        first = plain.apply_floors(_inputs(k * T, command, stroke))
        second = read.apply_floors(_inputs(k * T, command, stroke))
        read.blind_block_record()
        read.blind_block_arrays_at(np.array([k * T]))
        assert np.array_equal(first, second)
    assert plain.record() == read.record()


def test_edition_6_rules_keep_no_block_record() -> None:
    rule = _blind(("A_i", "A_ii", "B3"))
    _run(rule, 5)
    assert rule.blind_block_record() is None
    assert rule.blind_block_arrays_at(np.zeros(1)) == {}


# ------------------------------------------------------------------- P-1 probe stiffness
@pytest.fixture(scope="module")
def controller_parts():
    from outrigger_sim.control.c2 import C2Config, C2Controller, C2Geometry
    from outrigger_sim.control.ground_contact import ProbeResult
    from outrigger_sim.params import load_params

    geometry = C2Geometry.from_params(load_params())
    return SimpleNamespace(C2Config=C2Config, C2Controller=C2Controller, geometry=geometry,
                           ProbeResult=ProbeResult)


def _results(parts, ratios: list[float], changes: dict[int, dict] | None = None) -> tuple:
    """Probe results with K1 = ratio x ``k_nom`` per leg; ``changes``: leg -> field values."""
    nominal = parts.geometry.load_sensitivity_diag_N_m
    results = []
    for leg, ratio in enumerate(ratios):
        fields = {"is_grounded_by_stiffness": True, **(changes or {}).get(leg, {})}
        results.append(parts.ProbeResult(leg, 50e3, 0.0, ratio * nominal[leg], True, **fields))
    return tuple(results)


def _probe_round(controller, results, t_s: float) -> list[dict]:
    """``_finish_probe_round``'s order: the scale update, then the record."""
    controller._state.probe_round_count += 1
    controller._update_twist_stiffness_scale(results, t_s)
    controller._record_probe_stiffness(results, t_s)
    return controller.probe_stiffness_record()


def test_round_record_has_k1_ratio_median_warning_and_scale(controller_parts) -> None:
    parts = controller_parts
    controller = parts.C2Controller(parts.geometry, parts.C2Config().with_10hz_d1())
    assert controller.probe_stiffness_record() == []
    nan_leg = {3: {"is_skipped": True}}
    rounds = _probe_round(controller, _results(parts, [2.6, 2.7, 2.9, math.nan], nan_leg), 42.0)
    (entry,) = rounds
    nominal = parts.geometry.load_sensitivity_diag_N_m
    assert entry["round"] == 1 and entry["t_s"] == 42.0
    assert entry["legs"]["FL"]["k1_N_m"] == pytest.approx(2.6 * nominal[0])
    assert entry["legs"]["FL"]["k_nom_N_m"] == pytest.approx(nominal[0])
    assert entry["legs"]["FR"]["ratio"] == pytest.approx(2.7)
    assert entry["legs"]["RR"] == {**entry["legs"]["RR"], "k1_N_m": None, "ratio": None,
                                   "is_scale_leg": False, "is_skipped": True}
    assert entry["scale_leg_count"] == 3 and entry["raw_ratio"] == pytest.approx(2.7)
    assert entry["is_warned"] is True and entry["warning_range"] == [0.8, 2.3]
    assert entry["twist_stiffness_scale"] == pytest.approx(1.5)
    assert entry["scale_in_use"] == pytest.approx(1.5)
    warnings = [event.name for event in controller.events
                if event.name.startswith("WARN_PROBE_STIFFNESS_OUT_OF_RANGE")]
    assert warnings == [f"WARN_PROBE_STIFFNESS_OUT_OF_RANGE:{entry['raw_ratio']:.3f}"]
    json.dumps(rounds, allow_nan=False)  # plain JSON (no NaN)


def test_a_round_under_three_legs_keeps_the_scale_and_records_none(controller_parts) -> None:
    parts = controller_parts
    controller = parts.C2Controller(parts.geometry, parts.C2Config().with_10hz_d1())
    _probe_round(controller, _results(parts, [1.3] * 4), 10.0)
    two = {leg: {"is_grounded_by_stiffness": leg < 2} for leg in range(4)}
    rounds = _probe_round(controller, _results(parts, [2.0] * 4, two), 20.0)
    assert [entry["round"] for entry in rounds] == [1, 2]
    second = rounds[1]
    assert second["raw_ratio"] is None and second["is_warned"] is False
    assert second["scale_leg_count"] == 2
    assert second["twist_stiffness_scale"] == pytest.approx(1.3)  # the previous round's
    assert [second["legs"][name]["is_scale_leg"] for name in ("FL", "FR", "RL", "RR")] == [
        True, True, False, False]


def test_the_record_does_not_change_the_scale_update(controller_parts) -> None:
    parts = controller_parts
    plain = parts.C2Controller(parts.geometry, parts.C2Config().with_10hz_d1())
    recorded = parts.C2Controller(parts.geometry, parts.C2Config().with_10hz_d1())
    results = _results(parts, [1.2, 1.4, 2.5, 1.1])
    plain._update_twist_stiffness_scale(results, 5.0)
    _probe_round(recorded, results, 5.0)
    assert plain._state.twist_stiffness_scale == recorded._state.twist_stiffness_scale
    assert plain._twist_gain_scale() == recorded._twist_gain_scale()
    assert [e.name for e in plain.events] == [e.name for e in recorded.events]


# ------------------------------------------------------------------- verdict_runs switch
def test_record_switch_is_off_and_gives_no_keys(monkeypatch) -> None:
    import verdict_runs

    assert verdict_runs.is_ed8_record_on() is False
    controller = SimpleNamespace(probe_stiffness_record=lambda: [{"round": 1}],
                                 blind_block_record=lambda: {"level_periods": 0},
                                 blind_block_trace_arrays=lambda t_s: {"lsb_ib_block": t_s})
    assert verdict_runs.ed8_record_meta(controller) == {}
    assert verdict_runs.ed8_record_arrays(controller, np.zeros(1)) == {}
    monkeypatch.setattr(verdict_runs, "_ED8_RECORD", [True])
    assert verdict_runs.ed8_record_meta(controller) == {
        "probe_stiffness_record": [{"round": 1}], "ib_block_record": {"level_periods": 0}}
    assert set(verdict_runs.ed8_record_arrays(controller, np.zeros(1))) == {"lsb_ib_block"}
    without_a_ib = SimpleNamespace(probe_stiffness_record=lambda: [],
                                   blind_block_record=lambda: None,
                                   blind_block_trace_arrays=lambda t_s: {})
    assert verdict_runs.ed8_record_meta(without_a_ib) == {"probe_stiffness_record": []}


def test_run_one_copies_the_record_keys() -> None:
    import run_v5
    import verdict_runs

    assert {verdict_runs.PROBE_STIFFNESS_RECORD_KEY, verdict_runs.IB_BLOCK_RECORD_KEY} <= set(
        run_v5.LINE_RECORD_KEYS)


# ------------------------------------------------------------------- P-3 ed8_probe plan
@pytest.fixture(scope="module")
def probe():
    import ed8_probe

    return ed8_probe


def test_importing_the_probe_switches_nothing(probe) -> None:
    import harness_hydraulics
    import verdict_runs

    assert not any(name.startswith("P8-") for name in probe.run_v5.ALL_SETTINGS)
    assert harness_hydraulics.is_p1_read_record_on() is False
    assert verdict_runs.is_ed8_record_on() is False


def test_probe_settings_equal_the_sealed_settings(probe) -> None:
    """a2 on M / LSM<n> / M<key> has the options of VBM / LSM<n> / VBM<key>, so the probe
    lines of a2 command as the stored edition 7 lines."""
    from outrigger_sim.hydraulics.v5_options import HydraulicOptions

    settings = probe.probe_settings()
    run_v5 = probe.run_v5
    pairs = {"M": "VBM", "LSM1": "LSM1", "LSM4": "LSM4", "Mslow": "VBMslow", "Mh15": "VBMh15"}
    for plant, sealed in pairs.items():
        ours = HydraulicOptions.from_dict(settings[probe.setting_name(plant, "a2")][1])
        theirs = HydraulicOptions.from_dict(run_v5.ED7_SETTINGS[sealed][1])
        assert ours.to_dict() == theirs.to_dict(), plant
    edition_7 = probe.ed7_probe.probe_settings()
    for plant in probe.ed7_probe.PLANTS:
        for arm in probe.ed7_probe.ARMS:
            assert (settings[probe.setting_name(plant, arm)]
                    == edition_7[probe.ed7_probe.setting_name(plant, arm)]), (plant, arm)


def test_arm_a2w_is_a2_without_the_retract_target(probe) -> None:
    from outrigger_sim.hydraulics.v5_options import HydraulicOptions

    settings = probe.probe_settings()
    a2 = settings["P8-M-a2"][1]
    a2w = settings["P8-M-a2w"][1]
    assert a2w["probe_d6_settings"] == {"witness": True, "retract_position_target": False}
    assert {k: v for k, v in a2w.items() if k != "probe_d6_settings"} == {
        k: v for k, v in a2.items() if k != "probe_d6_settings"}
    options = HydraulicOptions.from_dict(a2w)
    assert dict(options.probe_d6_settings) == {"retract_position_target": False,
                                               "witness": True}
    assert "probe_d6_settings" not in settings["P8-M-c2"][1]


def test_plan_counts_of_the_sources(probe) -> None:
    j9main = probe.probe_jobs(("j9main",), probe.PLANTS, ("a2", "a2w"))
    assert len(j9main) == 2 * 388
    by_plant = {}
    for job in j9main:
        plant, _ = probe.split_setting_name(job["setting"])
        by_plant[plant] = by_plant.get(plant, 0) + 1
    assert by_plant == {"M": 200, "LSM1": 144, "LSM2": 144, "LSM3": 144, "LSM4": 144}
    main = probe.probe_jobs(("main",), ("M", "LSM4"), ("a2w",))
    assert len(main) == 2 * 15
    d = probe.probe_jobs(("d",), probe.PLANTS, ("a2", "a2w"))
    assert len(d) == 2 * 2 * 12
    keyed = probe.probe_jobs(("j9main",), ("LSM4",), ("a2",), keys=("R12_top-FR-Fs0-o0.05",))
    assert [(job["setting"], job["twin"]["leg"], job["offset_s"]) for job in keyed] == [
        ("P8-LSM4-a2", "FR", 0.05)]
    union = probe.probe_jobs(("main", "j9main"), ("M",), ("a2",))
    assert len(union) == len({probe.run_v5.job_key(probe._without_part(j)) for j in union})


def test_jobs_file_shapes_and_refusals(probe, tmp_path: Path) -> None:
    rows = [{"case": "S7", "eps": 0.002, "setting": "VBMslow"},
            {"case": "R12", "eps": 0.0, "offset_s": 0.0, "setting": "LSM3"}]
    listed = tmp_path / "list.json"
    listed.write_text(json.dumps(rows), encoding="utf-8")
    sealed = tmp_path / "sealed.json"
    sealed.write_text(json.dumps({"expected_lines": 2, "lines": [{"job": row} for row in rows]}),
                      encoding="utf-8")
    for path in (listed, sealed):
        jobs, sha = probe.read_jobs_file(path)
        planned = probe.probe_jobs(("file",), probe.PLANTS, ("a2w",), file_jobs=jobs)
        assert [job["setting"] for job in planned] == ["P8-Mslow-a2w", "P8-LSM3-a2w"]
        assert len(sha) == 64
    other = tmp_path / "other.json"
    other.write_text(json.dumps([{"case": "S7", "eps": 0.0, "setting": "V0"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="not one of"):
        probe.probe_jobs(("file",), probe.PLANTS, ("a2",), file_jobs=probe.read_jobs_file(other)[0])
    with pytest.raises(ValueError, match="jobs-file"):
        probe.read_jobs_file(tmp_path / "missing.json")
    with pytest.raises(ValueError, match="needs --jobs-file"):
        probe.probe_jobs(("file",), probe.PLANTS, ("a2",))


def _main(probe, tmp_path: Path, *arguments: str, capsys) -> tuple[int, dict]:
    code = probe.main(["--out", str(tmp_path / "p.jsonl"), *arguments])
    return code, json.loads(capsys.readouterr().out.strip().splitlines()[-1])


@pytest.mark.parametrize("bad", [("--plants", "X"), ("--arms", "a9"), ("--part", "z"),
                                 ("--keys", "R99_o0"), ("--part", "file"),
                                 ("--mask", "zz"), ("--part", "d", "--plants", "LSM1")])
def test_cli_refusals_exit_2(probe, tmp_path: Path, capsys, bad) -> None:
    code, last = _main(probe, tmp_path, *bad, capsys=capsys)
    assert code == 2 and last["status"] == "input_error"
    assert not (tmp_path / "p.jsonl").exists()


def test_cli_list_and_the_existing_output_rule(probe, tmp_path: Path, capsys) -> None:
    code, last = _main(probe, tmp_path, "--part", "main,d", "--list", capsys=capsys)
    assert code == 0 and last["status"] == "listed"
    # the default plants leave out the ③-off r79 plant KM0 (part p816 only, edition 8 P8-16)
    default_plants = [plant for plant in probe.PLANTS if plant not in probe.P3_OFF_PLANTS]
    assert last["planned"] == len(default_plants) * 15 * 2 + 2 * 12 * 2
    out = tmp_path / "p.jsonl"
    out.write_text("", encoding="utf-8")
    code, last = _main(probe, tmp_path, "--keys", "S7_e0.001", "--plants", "M", capsys=capsys)
    assert code == 2 and "exists" in last["reason"]
    code, last = _main(probe, tmp_path, "--keys", "S7_e0.001", "--plants", "M", "--resume",
                       capsys=capsys)
    assert code == 2 and "selection" in last["reason"]  # no stored selection to resume
    jobs, selection = probe._selection(probe._parser().parse_args(
        ["--out", str(out), "--keys", "S7_e0.001", "--plants", "M"]))
    probe._selection_path(out).write_text(json.dumps({**selection, "plan_sha256": "x"}),
                                          encoding="utf-8")
    code, last = _main(probe, tmp_path, "--keys", "S7_e0.001", "--plants", "M", "--resume",
                       capsys=capsys)
    assert code == 2 and "another plan" in last["reason"]
    assert out.read_text(encoding="utf-8") == ""
