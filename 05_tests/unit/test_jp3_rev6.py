"""③ revision 6 (436.9 edition 5, ``jp3_remedy_spec_v5.md`` 4, 7.2): R5-8 release witness,
R5-9 retract relief bound, R5-10 hold candidate, the re-lock ``M_j``, the rev 6 tag and options,
the hydraulics checks (가) .. (마) and the inherited judgement tools on revision 6 records.

No harness run: the monitor and the tracker are driven with synthetic readings; the grid of
R5-9 against the P3 plant law (``flow_limited_rod_pressure_r6``) is a reduced form of
``ed5_design/hyd/h2_r59_bound.py`` (checked at the controller reads).
"""

from __future__ import annotations

import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
S8_DIR = ROOT / "04_scripts" / "03_control" / "s8"
for _path in (COUPLED_DIR, S8_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from outrigger_sim.control import extend_start_bound as esb  # noqa: E402
from outrigger_sim.control.c2 import C2Config  # noqa: E402
from outrigger_sim.control.extend_start_bound import (  # noqa: E402
    BoundGeometry,
    ExtendStartBound,
    ExtendStartTracker,
    PeriodClass,
    ReleaseReliefParams,
)
from outrigger_sim.control.two_pressure import (  # noqa: E402
    LockStartSource,
    RodSensorState,
    TwoPressureMonitor,
)
from outrigger_sim.hydraulics import v5_options  # noqa: E402
from outrigger_sim.hydraulics.rod_chamber import RodChamberLegParams, RodChamberMode  # noqa: E402
from outrigger_sim.hydraulics.rod_release import flow_limited_rod_pressure_r6  # noqa: E402

BAR = 1e5
PERIOD_S = 0.1
HEAD_AREA = np.array([1.3273229e-2, 1.3273229e-2, 9.50331778e-3, 9.50331778e-3])
ANNULUS = np.array([3.76991118e-3, 3.76991118e-3, 3.14159265e-3, 3.14159265e-3])
V_MAX = 0.020924
U_HOLD = 0.01 * V_MAX
F_MIN_N = 9414.59
FR, RL = 1, 2
GEOMETRY = BoundGeometry(head_area_m2=tuple(HEAD_AREA), annulus_area_m2=tuple(ANNULUS),
                         stroke_max_m=0.70, max_speed_m_s=V_MAX, valve_tau_s=0.1)
LOCK = PeriodClass.LOCK


# ------------------------------------------------------------------------------- helpers
def rev6_settings(revision: int = 6):
    return replace(C2Config().with_10hz_d1().two_pressure, extend_start_rule="tracked_bound",
                   extend_start_bound=ExtendStartBound(revision=revision))


def monitor(revision: int = 6) -> TwoPressureMonitor:
    return TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN_N, PERIOD_S,
                              settings=rev6_settings(revision), stroke_max_m=0.70)


def read(mon: TwoPressureMonitor, k: int, command_fr: float, stroke: np.ndarray,
         rod_fr_Pa: float = 45 * BAR, head_Pa: float = 100 * BAR) -> dict:
    command = np.zeros(4)
    command[FR] = command_fr
    rod = np.full(4, 45 * BAR)
    rod[FR] = rod_fr_Pa
    mon.read(k * PERIOD_S, np.full(4, head_Pa), rod, command, False, 2e3,
             stroke_m=stroke.copy())
    return mon.extend_bound_trace_row()


def carry_commands(lock_reads: int = 10, carry_reads: int = 7, hold_reads: int = 3,
                   tail_reads: int = 6) -> list[float]:
    """FR: lock, a retract carry at -5 mm/s, a retracting hold (-0.1 mm/s), lock again."""
    return ([0.0] * lock_reads + [-5e-3] * carry_reads + [-1e-4] * hold_reads
            + [0.0] * tail_reads)


def run_carry(drop_m: list[float], fault_from: int | None = None, fall_back_first=False,
              commands: list[float] | None = None, revision: int = 6):
    """Drive FR through :func:`carry_commands`; ``drop_m[k]`` is the stroke change before read
    k. Returns the monitor, the trace rows and a per-read snapshot of the rev 6 state."""
    mon = monitor(revision)
    if fall_back_first:
        mon._fall_back(FR, "D1")
    stroke = np.full(4, 0.40)
    rows, snapshots = [], []
    for k, command in enumerate(commands or carry_commands()):
        stroke[FR] += drop_m[k] if k < len(drop_m) else 0.0
        rod = -100 * BAR if fault_from is not None and k >= fault_from else 45 * BAR
        rows.append(read(mon, k, command, stroke, rod_fr_Pa=rod))
        snapshots.append(state_snapshot(mon))
    return mon, rows, snapshots


def state_snapshot(mon: TwoPressureMonitor) -> dict:
    """The rev 6 state of FR (stretch, carry candidates, witness, p_hat, gate, evidence)."""
    tracker = mon._extend_tracker
    stretch = mon._stretch_states()[FR]
    carry = mon._carry_state_list()[FR]
    evidence = tracker.__dict__.get("release_evidence")  # none on a revision 5 tracker
    ran = tracker.__dict__.get("release_relief_ran")
    return {"p_hat": float(tracker.pressure_Pa[FR]), "gate_open": bool(tracker.gate.is_open[FR]),
            "gate_fill": float(tracker.gate.fill_m[FR]),
            "evidence": None if evidence is None else bool(evidence[FR]),
            "relief_ran": None if ran is None else bool(ran[FR]),
            "stretch_open": stretch.is_open, "candidates": list(stretch.candidates),
            "sources": tuple(stretch.candidate_sources),
            "carry": None if carry is None else (list(carry.candidates), carry.witness_t_s,
                                                 carry.witness_ref_m)}


WITNESS_DROPS = [0.0] * 11 + [-0.6e-3] * 6
"""FR moves 0.6 mm per read from read 11: s_ref = read 9, witness at read 12 (1.2 mm)."""
WITNESS_READ = 12


# ------------------------------------------------------------------------------- tag, options
@pytest.mark.parametrize("suffix", ["", "_LAS", "_K1", "_LAS_K1", "_LAS_K1_TCL"])
def test_rev6_tag_forms_are_revision_6_never_4_or_5(suffix) -> None:
    """4.6 / audit W4: the four suffix forms (and a K-2 suffix) of the rev 6 base tag."""
    tag = v5_options.EXTEND_WITNESS_CONTROLLER_TAG + suffix
    assert v5_options.extend_start_revision_of_tag(tag) == 6
    assert v5_options.switch_base_tag(tag) == "final_C4G2_P3W"
    assert v5_options.is_extend_start_tag(tag)
    assert v5_options.extend_start_revision_of_tag("final_C4G2_P3H" + suffix) == 5
    assert v5_options.extend_start_revision_of_tag("final_C4G2_P3" + suffix) == 4


def test_rev6_tag_list_and_controller_tag() -> None:
    assert v5_options.EXTEND_WITNESS_TAGS == (
        "final_C4G2_P3W", "final_C4G2_P3W_LAS", "final_C4G2_P3W_K1", "final_C4G2_P3W_LAS_K1")
    options = v5_options.HydraulicOptions(extend_start_tracked=True, extend_start_hold=True,
                                          extend_start_witness=True)
    config = C2Config().with_10hz_d1()
    assert v5_options.controller_tag(options) == "final_C4G2_P3W"
    assert v5_options.controller_tag(options, config) == "final_C4G2_P3W_LAS_K1"
    rev5 = replace(options, extend_start_witness=False)
    assert v5_options.controller_tag(rev5, config) == "final_C4G2_P3H_LAS_K1"


def test_rev6_option_needs_the_hold_and_builds_revision_6() -> None:
    with pytest.raises(ValueError, match="needs extend_start_hold"):
        v5_options.HydraulicOptions(extend_start_tracked=True, extend_start_witness=True)
    options = v5_options.HydraulicOptions(extend_start_tracked=True, extend_start_hold=True,
                                          extend_start_witness=True)
    assert options.extend_start_revision == 6
    assert v5_options.HydraulicOptions.from_dict(options.to_dict()) == options
    config = v5_options.apply_controller_options(C2Config().with_10hz_d1(), options, V_MAX, 0.1)
    bound = config.two_pressure.extend_start_bound
    assert bound.revision == 6 and bound.release_relief == ReleaseReliefParams()
    rev5 = replace(options, extend_start_witness=False)
    assert "extend_start_witness" not in rev5.to_dict()  # rev 5 digests unchanged
    rev5_bound = v5_options.apply_controller_options(C2Config().with_10hz_d1(), rev5, V_MAX,
                                                     0.1).two_pressure.extend_start_bound
    assert rev5_bound.revision == 5 and "release_relief" not in rev5_bound.to_meta()
    assert bound.to_meta()["release_relief"]["witness_stroke_m"] == 1.0e-3


def test_rev6_meta_identity_and_refusals() -> None:
    bound = ExtendStartBound(revision=6)
    assert bound.identity() == {"spec_edition": "fe6f5844",
                                "carry_end_rule": "inherit_when_gate_shut",
                                "retract_start_rule": "with_tracker", "rule_revision": 6}
    assert ExtendStartBound(revision=5).identity()["spec_edition"] == "8be9de22"
    assert "rule_revision" not in ExtendStartBound(revision=5).identity()
    assert set(ExtendStartBound(revision=4).to_meta()) == set(
        ExtendStartBound(revision=5).to_meta()) - set(esb.REVISION_5_FIELDS)
    with pytest.raises(ValueError, match="revision 6 field"):
        ExtendStartBound(revision=5, release_relief=ReleaseReliefParams())
    assert esb.check_extend_start_meta({"extend_start_rule": "tracked_bound",
                                        "extend_start_bound": bound.to_meta()}) == 6


def test_spec_edition_is_the_sealed_v5_sha_prefix() -> None:
    import hashlib

    spec = ROOT / "06_analysis" / "02_control" / "j_p3_cause" / "jp3_remedy_spec_v5.md"
    assert hashlib.sha256(spec.read_bytes()).hexdigest()[:8] == esb.JP3_SPEC_EDITION_V5


# ------------------------------------------------------------------------------- settings
def test_settings_vbk_and_the_rev6_jp3_settings() -> None:
    import run_v5

    vbk = run_v5.options_of("VBK")[1]
    assert vbk.extend_start_revision == 6 and vbk.rod_reading_truth and vbk.line_fill_gate
    for name in ("VBH", "VBJ", "LSH1", "LSH4", "LSJ1", "LSJ4"):
        assert run_v5.options_of(name)[1].extend_start_revision == 6, name
    assert run_v5.JP3_SETTINGS["VBK"] == run_v5.JP3_SETTINGS["VBJ"]
    assert run_v5.JP3_SETTINGS["VBK0"] == run_v5.JP3_SETTINGS["VBJ0"]
    for name in ("VBJ0", "VBK0"):
        assert run_v5.options_of(name)[1].extend_start_revision is None
    assert run_v5.options_of("VB")[1].extend_start_revision == 4
    rev5 = run_v5.JP3_REV5_SETTINGS["VBJ"][1]
    assert v5_options.HydraulicOptions.from_dict(rev5).extend_start_revision == 5
    # LSJ4: the rev 5 options of the X11 arm (control review of 8a3c48c7 B-1)
    assert set(run_v5.JP3_REV5_SETTINGS) & set(run_v5.ALL_SETTINGS) == {"VBH", "VBJ", "LSJ4"}
    assert v5_options.HydraulicOptions.from_dict(
        run_v5.JP3_REV5_SETTINGS["LSJ4"][1]).extend_start_revision == 5
    assert run_v5.options_of("LSJ4")[1].extend_start_revision == 6
    assert run_v5.ALL_SETTINGS["VBJ"] != run_v5.JP3_REV5_SETTINGS["VBJ"]


def test_guard_list_and_prefix_agree() -> None:
    """Audit W15: the guard judges by ``run_v5.ROD_FAULT_SETTINGS``; the ``VBK`` prefix gives
    the same answer for every setting name."""
    import r79_sensor_screen as screen
    import run_v5

    # edition 6 (jp3_remedy_spec_v6.md 3.4) adds VBKL / VBKL0 with the same prefix, edition 7
    # (jp3_remedy_spec_v7.md 3.6) VBKM / VBKM0
    assert run_v5.ROD_FAULT_SETTINGS == ("VBK", "VBK0", "VBKL", "VBKL0", "VBKM", "VBKM0")
    for name in run_v5.ALL_SETTINGS:
        assert screen.is_rod_fault_setting(name) == name.startswith(
            screen.ROD_FAULT_SETTING_PREFIX), name
    assert not screen.is_rod_fault_setting("VBKX")  # a prefix match is no rod-fault setting


def test_jp3_line_settings_and_hold_revision_constants_agree() -> None:
    import j_p3_inputs
    import jp3_baseline_compare as compare
    import jp3_tjr_judge as tj
    import lock_window_alignment
    import run_v5

    assert set(run_v5.JP3_SETTINGS) == set(tj.JP3_LINE_SETTINGS)
    assert "VBK" in j_p3_inputs.REV5_JUDGED_SETTINGS
    for constant in (j_p3_inputs.HOLD_REVISIONS, compare.HOLD_REVISIONS, tj.HOLD_REVISIONS,
                     lock_window_alignment.HOLD_REVISIONS):
        assert tuple(constant) == esb.HOLD_REVISIONS
    assert j_p3_inputs.is_p3_expected(None, "VBK")
    assert not j_p3_inputs.is_p3_expected(None, "VBK0")


# ------------------------------------------------------------------------------- R5-8 witness
def test_witness_on_a_retract_carry_and_the_witness_record() -> None:
    mon, rows, _ = run_carry(WITNESS_DROPS)
    classes = [row["class"][FR] for row in rows]
    assert classes[10:13] == ["carry_ret"] * 3
    assert classes[13] == "ret"  # from the next read on, as an opened gate
    assert [row["r58_witness"][FR] for row in rows].index(True) == WITNESS_READ
    log = mon.meta()["extend_start_record"]["witness_log"]
    assert len(log) == 1 and log[0]["leg"] == "FR"
    assert log[0]["witness_t_s"] == pytest.approx(1.2)
    assert log[0]["witness_ref_m"] == pytest.approx(0.40)
    assert log[0]["witness_ds_m"] == pytest.approx(1.2e-3)
    carry_rows = mon.meta()["extend_start_record"]["carry_log"]
    assert carry_rows[0]["witness_t_s"] == pytest.approx(1.2)
    assert not any(row["gate_open"][FR] for row in rows)  # the witness, not the gate


@pytest.mark.parametrize(("drop_mm", "is_witness"), [(0.99, False), (1.0, True), (1.01, True)])
def test_witness_threshold_is_1_mm(drop_mm, is_witness) -> None:
    """0.99 mm is no witness (4.1: ``>= 1.0 mm``)."""
    drops = [0.0] * 11 + [-drop_mm * 1e-3] + [0.0] * 5
    _, rows, _ = run_carry(drops)
    assert any(row["r58_witness"][FR] for row in rows) is is_witness


def test_no_witness_in_lock_or_hold_reads_or_against_the_command() -> None:
    lock_and_hold = [0.0] * 10 + [-1e-4] * 6 + [0.0] * 4
    drops = [0.0] * 3 + [-3e-3] * 14  # large moves during lock and hold
    _, rows, _ = run_carry(drops, commands=lock_and_hold)
    assert not any(row["r58_witness"][FR] for row in rows)
    against = [0.0] * 11 + [+2e-3] * 6  # the stroke moves out on a retract carry
    _, rows, _ = run_carry(against)
    assert not any(row["r58_witness"][FR] for row in rows)


def test_extension_carry_witness_counts_relief_from_the_next_read() -> None:
    commands = [0.0] * 10 + [5e-3] * 6 + [0.0] * 4
    drops = [0.0] * 11 + [0.6e-3] * 5
    mon, rows, _ = run_carry(drops, commands=commands)
    assert [row["r58_witness"][FR] for row in rows].index(True) == WITNESS_READ
    assert rows[WITNESS_READ + 1]["class"][FR] == "ext"
    assert mon._extend_tracker.release_evidence_runs[FR] == 0  # R5-9 is retract only


def test_witnessed_carry_hands_no_candidates_to_the_next_stretch() -> None:
    """4.1: a witnessed carry ending in a lock is not inherited (R5-6 off)."""
    commands = [0.0] * 10 + [-5e-3] * 3 + [0.0] * 5
    drops = [0.0] * 11 + [-0.6e-3, -0.6e-3]
    mon6, rows6, _ = run_carry(drops, commands=commands)
    mon5, _, _ = run_carry(drops, commands=commands, revision=5)
    assert rows6[WITNESS_READ]["r58_witness"][FR]
    assert mon6._stretch_states()[FR].inherited_candidates == 0
    assert mon5._stretch_states()[FR].inherited_candidates > 0  # rev 5 inherits (gate shut)


def test_witness_noise_1e6_draws_no_false_witness() -> None:
    """P5-3 / 7.2: white reading noise sigma 0.1 mm on both reads, 10^6 carry reads of a leg
    that does not move: no witness at 1.0 mm (7.07 sigma of the difference)."""
    rng = np.random.default_rng(20261122)
    reference = 0.40 + rng.normal(0.0, 1e-4, 1_000_000)
    reading = 0.40 + rng.normal(0.0, 1e-4, 1_000_000)
    threshold = ReleaseReliefParams().witness_stroke_m
    witnesses = sum(esb.release_witness_moved_m(-5e-3, float(s), float(r)) >= threshold
                    for s, r in zip(reading, reference, strict=True))
    assert witnesses == 0


def test_witness_noise_through_the_monitor_path() -> None:
    """The same noise through the monitor: 40 carries of 10 reads (no witness)."""
    rng = np.random.default_rng(7)
    mon = monitor()
    stroke = np.full(4, 0.40)
    k, witnesses = 0, 0
    for _ in range(40):
        for command in [0.0] * 3 + [-5e-3] * 10:
            noisy = stroke + rng.normal(0.0, 1e-4, 4)
            row = read(mon, k, command, noisy)
            witnesses += row["r58_witness"][FR]
            k += 1
    assert witnesses == 0


# ------------------------------------------------------------------------------- R5-9 relief
def tracker(start_bar: float = 60.0) -> ExtendStartTracker:
    return ExtendStartTracker(ExtendStartBound(revision=6), GEOMETRY, np.full(4, start_bar * BAR))


def advance(tr: ExtendStartTracker, classes, command_fr: float, head_bar: float = 80.0,
            stroke_m: float = 0.40, period_s: float = PERIOD_S, floor_bar: float = 0.0,
            others_command: float = 0.0) -> None:
    command = np.full(4, others_command)
    command[FR] = command_fr
    stroke = np.full(4, 0.40)
    stroke[FR] = stroke_m
    tr.advance(command, stroke, np.full(4, floor_bar * BAR), period_s,
               head_Pa=np.full(4, head_bar * BAR), period_class=classes,
               carry_bound_Pa=np.full(4, np.nan), release_floor_Pa=np.full(4, floor_bar * BAR))


def ret_classes(fr: PeriodClass = PeriodClass.RET, others: PeriodClass = LOCK) -> list:
    classes = [others] * 4
    classes[FR] = fr
    return classes


def test_r59_one_substep_formula() -> None:
    """4.2 formula for one 1 ms sub-step at a steady valve (no lag), head 80 bar."""
    tr = tracker(60.0)
    speed = 1e-3
    tr.valve_m_s[FR] = -speed
    advance(tr, ret_classes(), -speed, period_s=1e-3)  # the run starts; previous head 80 bar
    assert tr.pressure_Pa[FR] == 60e5
    tr.note_release_evidence(FR)
    advance(tr, ret_classes(), -speed, period_s=1e-3, floor_bar=13 + 89 / 3)
    params = ReleaseReliefParams()
    lower, upper = 80e5 - 9e5, 80e5 + 9e5
    flow = max(math.sqrt((lower - 2e5) / 3e5) - 1.0, 0.0)
    compliance = tr.compliance_m3_Pa(FR, 0.40)
    drop = ANNULUS[FR] * 0.8 * speed * flow * 1e-3 / compliance
    target = esb.retract_target_rod_pressure_Pa(upper * HEAD_AREA[FR] - params.rod_floor_Pa
                                                * ANNULUS[FR], HEAD_AREA[FR], ANNULUS[FR], params)
    lag = target + (60e5 - target) * math.exp(-1e-3 / 0.05)
    expected = max(60e5 - drop, lag, (13 + 89 / 3) * BAR)
    assert tr.pressure_Pa[FR] == pytest.approx(expected, rel=1e-12)
    assert tr.release_relief_substeps[FR] == 1


def test_r59_matches_the_plant_retract_target() -> None:
    """``p*_ret`` of the tracker = ``RodChamberLegParams`` RET target (same values)."""
    params = ReleaseReliefParams()
    leg = RodChamberLegParams(head_area_m2=HEAD_AREA[0], annulus_area_m2=ANNULUS[0],
                              head_stiffness_N_m=2.9e7, rod_stiffness_N_m=1.1e7,
                              outer_stiffness_N_m=1e12, rod_weight_N=0.0)
    for force_N in (-30e3, 0.0, 5e3, 50e3, 150e3, 400e3):
        assert esb.retract_target_rod_pressure_Pa(force_N, HEAD_AREA[0], ANNULUS[0], params) == (
            pytest.approx(leg.moving_target_rod_pressure_Pa(RodChamberMode.RET, force_N),
                          rel=1e-12))


def test_r59_only_after_evidence_and_only_on_retract_classes() -> None:
    tr = tracker(60.0)
    advance(tr, ret_classes(LOCK), 0.0)
    advance(tr, ret_classes(), -5e-3)
    assert tr.release_relief_substeps[FR] == 0 and tr.pressure_Pa[FR] == 60e5  # A2
    tr.note_release_evidence(FR)
    advance(tr, ret_classes(), -5e-3)
    assert tr.release_relief_substeps[FR] == 100 and tr.pressure_Pa[FR] < 60e5


@pytest.mark.parametrize("stop", ["hold", "lock", "sign", "new_carry"])
def test_r59_stops_and_resets(stop) -> None:
    """4.2 stop / reset: a hold or lock period, a sign change, a new carry."""
    tr = tracker(60.0)
    advance(tr, ret_classes(LOCK), 0.0)
    advance(tr, ret_classes(), -5e-3)
    tr.note_release_evidence(FR)
    advance(tr, ret_classes(), -5e-3)
    before = tr.release_relief_substeps[FR]
    if stop == "hold":
        advance(tr, ret_classes(PeriodClass.HOLD), -1e-4)
    elif stop == "lock":
        advance(tr, ret_classes(LOCK), 0.0)
    elif stop == "sign":
        advance(tr, ret_classes(PeriodClass.EXT), 5e-3)
    else:
        advance(tr, ret_classes(PeriodClass.CARRY_RET), -5e-3)  # after a ret: a new carry
    assert not tr.release_evidence[FR]
    advance(tr, ret_classes(), -5e-3)
    assert tr.release_relief_substeps[FR] == before


def test_r59_gate_opening_is_evidence_from_the_next_substep() -> None:
    tr = tracker(60.0)
    advance(tr, ret_classes(LOCK), 0.0, head_bar=20.0)
    for _ in range(60):
        advance(tr, ret_classes(PeriodClass.CARRY_RET), -5e-3, head_bar=20.0)
        if tr.gate.is_open[FR]:
            break
    assert tr.gate.is_open[FR] and tr.release_evidence[FR]
    assert tr.release_evidence_runs[FR] == 1


@pytest.mark.parametrize(("guard", "kwargs"), [
    ("end", {"stroke_m": 0.0152}),
    ("end_nan", {"stroke_m": math.nan}),
    ("head_200", {"head_bar": 200.0}),
    ("head_nan", {"head_bar": math.nan}),
    ("tail_cut", {}),
    ("saturation", {"others_command": 1.5 * V_MAX}),
])
def test_r59_guards_take_the_floor_only(guard, kwargs) -> None:
    tr = tracker(60.0)
    command = 0.0 if guard == "tail_cut" else -V_MAX
    others = PeriodClass.EXT if guard == "saturation" else LOCK
    if guard == "saturation":  # sum A |u_v| above 0.85 Q_pump, the valves settled
        tr.valve_m_s[:] = 1.5 * V_MAX
        tr.valve_m_s[FR] = -V_MAX
    advance(tr, ret_classes(others=others), command, floor_bar=20.0, **kwargs)  # run start
    tr.note_release_evidence(FR)
    advance(tr, ret_classes(others=others), command, floor_bar=20.0, **kwargs)
    assert tr.release_relief_substeps[FR] == 0
    assert tr.release_uncounted_substeps[FR] == 100
    assert tr.pressure_Pa[FR] == 60e5  # max(p, floor) with p above the floor
    # control review item 6: a NaN stroke is counted apart from the end guard
    assert bool(tr.release_end_guard_substeps[FR] == 100) is (guard == "end")
    assert bool(tr.release_nan_stroke_substeps[FR] == 100) is (guard == "end_nan")
    record = tr.record()
    assert record["r59_end_guard_substeps"][FR] == (100 if guard == "end" else 0)
    assert record["r59_nan_stroke_substeps"][FR] == (100 if guard == "end_nan" else 0)


def test_r59_end_guard_raises_to_the_floor() -> None:
    tr = tracker(10.0)
    advance(tr, ret_classes(), -5e-3, stroke_m=0.010)  # run start, floor term 0
    tr.note_release_evidence(FR)
    advance(tr, ret_classes(), -5e-3, stroke_m=0.010, floor_bar=40.0)
    assert tr.pressure_Pa[FR] == 40e5 and tr.release_end_guard_substeps[FR] == 100
    assert tr.record()["r59_end_guard_substeps"][FR] == 100


def _r59_grid_case(leg: int, force_N: float, p0_Pa: float, speed: float, error_Pa: float,
                   duration_s: float = 2.0) -> float:
    """Smallest ``p_hat - p_tr`` at the reads: P3 plant (r6 law, plant ``C_r``) against the
    tracker with release evidence from t = 0 (``h2_r59_bound.py`` reduced)."""
    stiffness = {0: (2.9424e7, 1.0805e7, 1.7983e-12), 2: (2.1554e7, 8.7485e6, 1.5860e-12)}
    head_k, rod_k, plant_c = stiffness[leg]
    params = RodChamberLegParams(head_area_m2=HEAD_AREA[leg], annulus_area_m2=ANNULUS[leg],
                                 head_stiffness_N_m=head_k, rod_stiffness_N_m=rod_k,
                                 outer_stiffness_N_m=1e12, rod_weight_N=0.0)
    target_Pa = params.moving_target_rod_pressure_Pa(RodChamberMode.RET, force_N)
    if p0_Pa <= target_Pa + 1e3:
        return math.inf, 0, 0.0
    tr = ExtendStartTracker(ExtendStartBound(revision=6), GEOMETRY, np.full(4, p0_Pa))
    pressure = p0_Pa

    def head_reading(p_tr: float) -> np.ndarray:
        heads = np.full(4, 80 * BAR)
        heads[leg] = (force_N + ANNULUS[leg] * p_tr) / HEAD_AREA[leg] + error_Pa
        return heads

    classes = [LOCK] * 4
    classes[leg] = PeriodClass.RET
    command = np.zeros(4)
    command[leg] = -speed
    # the run's first period (1 ms, before the evidence): keeps the t = 0 head as the previous
    # reading, as h2 does; p_hat(0) = p_tr(0) is the least start A1 allows
    tr.advance(command, np.full(4, 0.40), np.zeros(4), 1e-3, head_Pa=head_reading(pressure),
               period_class=classes, carry_bound_Pa=np.full(4, np.nan),
               release_floor_Pa=np.full(4, np.nan))
    tr.note_release_evidence(leg)
    margin = math.inf
    for _ in range(round(duration_s / PERIOD_S)):
        for _ in range(200):
            pressure = flow_limited_rod_pressure_r6(pressure, target_Pa, speed, 5e-4, 0.05,
                                                    plant_c, HEAD_AREA[leg], ANNULUS[leg],
                                                    True, force_N, 5e5)
        heads = head_reading(pressure)
        upper = max(heads[leg], tr.previous_head_Pa[leg]) + 9e5
        floor = np.full(4, np.nan)
        floor[leg] = 13e5 + upper / 3.0
        tr.advance(command, np.full(4, 0.40), np.full(4, 13e5) + heads / 3.0, PERIOD_S,
                   head_Pa=heads, period_class=classes, carry_bound_Pa=np.full(4, np.nan),
                   release_floor_Pa=floor)
        margin = min(margin, float(tr.pressure_Pa[leg]) - pressure)
    return margin, int(tr.release_relief_substeps[leg]), p0_Pa - float(tr.pressure_Pa[leg])


@pytest.mark.parametrize("leg", [0, 2], ids=["front", "rear"])
def test_r59_grid_margin_is_never_negative(leg) -> None:
    """7.2 R5 unit "격자 최소 여유 >= 0" on a reduced h2 grid (forces incl. tension and light
    load, start pressures, speeds, head reading errors +-b_read); the relief must have counted
    and lowered ``p_hat`` in most cases (no vacuous pass)."""
    cases = [_r59_grid_case(leg, force_kN * 1e3, p0_bar * BAR, speed_mm * 1e-3, error_bar * BAR)
             for force_kN in (-30.0, 5.0, 15.0, 50.0, 150.0)
             for p0_bar in (60.0, 100.0)
             for speed_mm in (1.0, 4.71, 20.92)
             for error_bar in (-4.62, 4.62)]
    run = [case for case in cases if math.isfinite(case[0])]
    assert len(run) >= 30
    assert min(margin for margin, _, _ in run) >= 0.0
    assert all(substeps > 0 for _, substeps, _ in run)
    assert sum(lowered > 1e5 for _, _, lowered in run) >= len(run) // 2


# ------------------------------------------------------------------------------- R5-10, M_j
def test_r510_hold_candidate_after_r59() -> None:
    mon, rows, _ = run_carry(WITNESS_DROPS)
    hold_rows = [k for k, row in enumerate(rows) if row["class"][FR] == "hold"]
    assert hold_rows and all(rows[k]["r510_candidates"][FR] == 1 for k in hold_rows)
    stretch = mon._stretch_states()[FR]
    tracker_bound = mon._extend_tracker.bound_Pa(FR)
    hold_starts = [start for (start, _), source in zip(stretch.candidates,
                                                       stretch.candidate_sources, strict=True)
                   if source in (LockStartSource.RETRACT_HOLD.value,
                                 LockStartSource.RETRACT_TRACKER.value)]
    model = mon._lock_start_model_Pa(FR, -1.0, 100 * BAR)
    assert hold_starts and all(start == pytest.approx(max(model, tracker_bound))
                               for start in hold_starts)
    _, rows5, _ = run_carry(WITNESS_DROPS, revision=5)
    assert "r510_candidates" not in rows5[0]


def test_r510_not_without_r59() -> None:
    """No release evidence (no witness, gate shut): a later hold has R5-2 only."""
    _, rows, _ = run_carry([0.0] * 17)
    assert not any(row["r510_candidates"][FR] for row in rows)


def test_relock_mj_takes_p_hat_of_each_window_sample() -> None:
    """4.4: ``M_j = max(13 + p_h,j / 3, p_ret, p_hat(t_j) + delta_m)`` with the window
    sample's own ``p_hat`` (never the witness time's), or the lookback start (10.4 ③)."""
    commands = [0.0] * 10 + [-5e-3] * 7 + [0.0] * 6
    mon = monitor()
    stroke = np.full(4, 0.40)
    bounds, starts = [], []
    for k, command in enumerate(commands):
        stroke[FR] += WITNESS_DROPS[k] if k < len(WITNESS_DROPS) else 0.0
        head = 100.0 if k < 17 else 100.0 + 6.0 * (k - 16)  # load rises after the re-lock
        read(mon, k, command, stroke, head_Pa=head * BAR)
        bounds.append(mon._extend_tracker.bound_Pa(FR))
        stretch = mon._stretch_states()[FR]
        if command == 0.0 and k >= 17:
            starts.append((k, stretch.candidates[-1][0], stretch.previous_moving_max_Pa, head))
    witness_bound = bounds[WITNESS_READ]
    for k, start, lookback, head in starts:
        model = mon._lock_start_model_Pa(FR, -1.0, head * BAR)
        assert start == pytest.approx(max(model, bounds[k], lookback))
    assert any(bounds[k] != witness_bound for k, *_ in starts)


# ------------------------------------------------------------------------------- 7.2 (가)-(마)
def test_ga_latch_read_is_never_the_last_valid_reading_rev6() -> None:
    """(가) on revision 6: the -100 bar latch read is not kept by ⑤."""
    mon = monitor()
    head, rod, stroke = np.full(4, 100 * BAR), np.full(4, 120 * BAR), np.full(4, 0.40)
    mon.read(0.0, head, rod, np.full(4, 0.5 * V_MAX), False, 2e3, stroke_m=stroke)
    for k in range(1, 15):
        mon.read(k * PERIOD_S, head, rod, np.zeros(4), False, 2e3, stroke_m=stroke)
    faulty = rod.copy()
    faulty[FR] = -100 * BAR
    mon.read(1.5, head, faulty, np.zeros(4), False, 2e3, stroke_m=stroke)
    assert mon.rod_state[FR] is RodSensorState.FALLBACK
    assert mon._stretch_states()[FR].valid_rod_Pa == 120 * BAR


def test_na_first_stretch_after_the_latch_uses_reading_and_inherited_candidates() -> None:
    """(나): a carry with the gate shut and no witness hands its candidates to the stretch
    (R5-6); the latch comes inside that stretch, which keeps ⑤ and the inherited ones."""
    commands = [0.0] * 10 + [-5e-3] * 2 + [0.0] * 8
    mon, _, _ = run_carry([0.0] * 20, fault_from=15, commands=commands)
    stretch = mon._stretch_states()[FR]
    assert mon.rod_state[FR] is RodSensorState.FALLBACK
    assert stretch.inherited_candidates > 0 and any(stretch.candidate_inherited)
    assert stretch.valid_rod_Pa == 45 * BAR  # the last reading before the latch
    estimate = mon._legs[FR].rod_estimate_Pa
    assert estimate >= stretch.model_bound_Pa and estimate >= stretch.valid_rod_Pa


def test_da_rev6_state_runs_whatever_the_rod_sensor_state() -> None:
    """(다): the same rev 6 state with FR fallen back from the start and with FR OK."""
    _, rows_ok, snaps_ok = run_carry(WITNESS_DROPS)
    _, rows_fb, snaps_fb = run_carry(WITNESS_DROPS, fall_back_first=True)
    assert snaps_ok == snaps_fb
    for name in ("class", "r58_witness", "r59_substeps", "r510_candidates", "ext_bound_Pa"):
        assert [row[name] for row in rows_ok] == [row[name] for row in rows_fb], name


def test_ra_ma_fault_after_the_witness_read_keeps_the_witnessed_carry() -> None:
    """(라)/(마): a witness at read n, the -100 bar fault from n + 1 (TRw). Through read n + 1
    the rev 6 state equals the run without the fault; no R5-6 candidate on the fallback
    path; R5-9 counts in the n -> n + 1 period; the following u < 0 hold has R5-10."""
    fault_read = WITNESS_READ + 1
    mon_fault, rows_fault, snaps_fault = run_carry(WITNESS_DROPS, fault_from=fault_read)
    _, _, snaps_clean = run_carry(WITNESS_DROPS)
    assert snaps_fault[:fault_read + 1] == snaps_clean[:fault_read + 1]
    assert rows_fault[WITNESS_READ]["r58_witness"][FR]
    assert mon_fault.rod_state[FR] is RodSensorState.FALLBACK
    names = [name for name, _ in mon_fault.pop_events()]
    assert "INFO_ROD_PRESSURE_FAULT_REASON:FR:D1" in names
    assert rows_fault[fault_read]["r59_substeps"][FR] > 0
    holds = [row for row in rows_fault if row["class"][FR] == "hold"]
    assert holds and all(row["r510_candidates"][FR] > 0 for row in holds)
    stretch = mon_fault._stretch_states()[FR]
    assert stretch.inherited_candidates == 0 and not any(stretch.candidate_inherited)
    for row in mon_fault.meta()["fallback_lock_log"]:
        assert row.get("inherited_candidates", 0) == 0


# ------------------------------------------------------------------------------- records
def test_rev6_trace_arrays_and_record_totals() -> None:
    check = esb.ExtendBoundCheckRev5(np.full(4, 600.0) / ANNULUS, "normal")
    mon, rows, _ = run_carry(WITNESS_DROPS)
    for row in rows:
        check.add(row["t_s"], row["class"], row["used_bound_Pa"], np.full(4, 40 * BAR),
                  ["locked_ret"] * 4, row)
    record = check.record()
    assert record["rule_revision"] == 6 and record["spec_edition"] == "fe6f5844"
    assert record["jp3_r58_witness_carries"][FR] == 1
    assert record["jp3_r59_substeps"][FR] == sum(row["r59_substeps"][FR] for row in rows) > 0
    assert record["jp3_r510_candidates"][FR] == 3
    arrays = check.trace.arrays()
    assert arrays["jp3_r58_witness"].dtype == bool and arrays["jp3_r58_witness"][WITNESS_READ, FR]
    assert arrays["jp3_r59_substeps"].shape == (len(rows), 4)
    rev5 = esb.ExtendBoundCheckRev5(np.full(4, 600.0) / ANNULUS, "normal")
    _, rows5, _ = run_carry(WITNESS_DROPS, revision=5)
    for row in rows5:
        rev5.add(row["t_s"], row["class"], row["used_bound_Pa"], np.full(4, 40 * BAR),
                 ["locked_ret"] * 4, row)
    assert rev5.record()["rule_revision"] == 5
    assert "jp3_r59_substeps" not in rev5.record()
    assert not any(name.startswith("jp3_r5") for name in rev5.trace.arrays())


def test_tracker_record_rev6_keys() -> None:
    mon, _, _ = run_carry(WITNESS_DROPS)
    record = mon.meta()["extend_start_record"]
    assert record["rule_revision"] == 6
    assert record["release_evidence_runs"][FR] == 1 and record["r59_substeps"][FR] > 0
    assert record["witness_log_columns"][0] == "leg"
    mon5, _, _ = run_carry(WITNESS_DROPS, revision=5)
    assert "witness_log" not in mon5.meta()["extend_start_record"]
    assert mon5.meta()["extend_start_record"]["rule_revision"] == 5


# ------------------------------------------------------------------------------- inherited tools
def _record(revision: int, edition: str | None = None, breaches: int = 0) -> dict:
    edition = edition or esb.JP3_SPEC_EDITION_OF_REVISION[revision]
    return {"rule_revision": revision, "spec_edition": edition,
            "carry_end_rule": "inherit_when_gate_shut", "retract_start_rule": "with_tracker",
            "identity_consistent": True, "sensor_grade": "normal",
            "jp3a_breach_reads": [breaches, 0, 0, 0], "jp3b_breach_over_tol_reads": [0] * 4,
            "jp3c_breach_reads": [0] * 4}


def test_j_p3_judgement_takes_rev6_records() -> None:
    assert esb.j_p3_judgement_rev5([_record(6)])["status"] == "pass"
    assert esb.j_p3_judgement_rev5([_record(6, breaches=1)])["status"] == "H-7"
    wrong = esb.j_p3_judgement_rev5([_record(6, edition="8be9de22")])
    assert wrong["status"] == "setting_defect"
    assert wrong["runs_by_case"][esb.J_P3_DEFECT_IDENTITY] == 1
    mixed = esb.j_p3_judgement_rev5([_record(5), _record(6)])
    assert mixed["status"] == "setting_defect" and mixed["rule_revisions"] == [5, 6]
    assert esb.j_p3_judgement([_record(6)])["status"] == "setting_defect"  # never rev 4


def test_j_p3_over_rows_judges_rev6_apart() -> None:
    import j_p3_inputs

    def row(revision, setting="VBJ"):
        return {"p3_expected": True, "run_extend_start_rule": "tracked_bound",
                "run_extend_start_revision": revision, "setting": setting,
                "extend_bound_check": _record(revision)}

    out = j_p3_inputs.j_p3_over_rows([row(6), row(6, "VBK")])
    assert out["status_by_revision"] == {"4": "no_p3_runs", "6": "pass"}
    assert out["rev6"]["runs_judged"] == 2
    both = j_p3_inputs.j_p3_over_rows([row(5), row(6)])
    assert both["status_by_revision"]["5"] == both["status_by_revision"]["6"] == "pass"
    mismatched = {**row(6), "run_extend_start_revision": 5}
    assert j_p3_inputs.j_p3_over_rows([mismatched])["status"] == "setting_defect"
    unkeyed = {key: value for key, value in row(6).items() if key != "run_extend_start_revision"}
    assert j_p3_inputs.j_p3_over_rows([unkeyed])["revision_key_missing_runs"] == 1


def test_t8_line_and_identity_checks_take_rev6() -> None:
    import jp3_baseline_compare as compare
    import jp3_tjr_judge as tj

    record = {"hydraulics_record": {"extend_bound_check": _record(6),
                                    "rod_reading_truth_calls": 0, "two_pressure_reads": 3},
              "job": {"setting": "VBH"}}
    assert tj.t8_line_problems("VBH", record, False) == []
    record["hydraulics_record"]["extend_bound_check"] = _record(6, edition="8be9de22")
    assert tj.t8_line_problems("VBH", record, False) != []
    assert compare.identity_problems(record) != []
    record["hydraulics_record"]["extend_bound_check"] = {"rule_revision": 4}
    # edition 7 adds the hold revision 7 (jp3_remedy_spec_v7.md 3.5)
    assert "not one of (5, 6, 7)" in tj.t8_line_problems("VBH", record, False)[0]
    assert tj._dg3_identity({"hydraulics_record": {"extend_bound_check": _record(6)}}) == []


def test_lock_window_and_replay_helpers_take_rev6() -> None:
    import lock_window_alignment
    import t4h_replay

    meta = {"extend_start_record": {"rule_revision": 6, "hold_speed_m_s": U_HOLD}}
    assert lock_window_alignment.monitor_hold_speed_m_s(meta) == U_HOLD
    assert t4h_replay._run_hold_revision({"extend_start_bound": {"revision": 6}}) == {
        "run_extend_start_revision": 6}
    assert t4h_replay._run_hold_revision({"extend_start_bound": {"revision": 4}}) == {}


def test_r79_line_revision_keys() -> None:
    import r79_sensor_screen as screen

    config = replace(C2Config().with_10hz_d1(), two_pressure=rev6_settings())
    assert screen.run_extend_start_record(config) == {"run_extend_start_rule": "tracked_bound",
                                                      "run_extend_start_revision": 6}
    assert screen.run_extend_start_record(C2Config().with_10hz_d1()) == {}


def test_x6_closure_takes_several_entries_and_the_run_tools() -> None:
    import jp3_import_closure as closure

    entries = [ROOT / name for name in closure.RUN_TOOL_ENTRIES]
    assert all(path.is_file() for path in entries)
    found = closure.import_closure(ROOT, entries).files
    assert set(closure.RUN_TOOL_ENTRIES) <= set(found)
    single = closure.import_closure(ROOT, entries[0]).files
    assert set(single) <= set(found) and closure.RUN_TOOL_ENTRIES[1] not in single


def test_x3_r79_key_level_names() -> None:
    import jp3_baseline_compare as compare
    import jp3_dryrun_evidence as dry

    for level in ("L2", "L2nocal", "L2imuideal", "L3"):
        line = {"key": f"cand=current#{level}|s0|g8|3|x|y"}
        assert compare.evidence_multiplier(line) == 2, level
        text = f'{{"key": "{level}|s7|g6|0|a"}}'.encode()
        assert dry.R79_KEY_PATTERN.findall(text)[0][1] == b"7", level
    assert compare.evidence_multiplier({"key": "LX|s0|g8|3"}) == 1
