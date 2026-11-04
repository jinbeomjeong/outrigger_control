"""The 24 evaluation cases and the run table of the coupling verdict (criteria 8.1, 8.3, 8.4).

Each case names its reduced-harness twin. ``twin_status`` says how far the twin is established:
  stored        same-definition row with a stored final-controller command hash
  stored_gap    stored row, with a definition difference named in ``note``
  no_final_row  the harness defines the row (key in ``note``), no stored final-controller hash
  decision      no row that can be used without a choice: skipped until ``--decide`` names one

Bundle ``OFF`` (flow limit off, the pair base of criteria sec. 1 and V-5) is added to the 60 runs
of criteria 8.4. It does not depend on eta_v.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from harness_flow import LAW_PROPORTIONAL, FlowSetting

PATH_STEADY = "steady"
PATH_EVENT = "event"
STATUS_STORED = "stored"
STATUS_STORED_GAP = "stored_gap"
STATUS_NO_FINAL_ROW = "no_final_row"
STATUS_DECISION = "decision"

ROLL_DOWN_RIGHT_DEG = 5.5
PITCH_VERIFY_DEG = 3.5
RPB_ROLL_DEG = 2.7355
RPB_PITCH_DEG = 1.7592
ETA_MAIN = 0.85
ETA_MIDDLE = 0.90
ETA_NO_EFFECT = 0.95
DP_LOW_PA = (6e5, 12e5)
DP_HIGH_PA = (20e5, 30e5)
WIDTH_HALF_PA = 0.5e5
WIDTH_DOUBLE_PA = 2e5
REANCHOR_ON = "reanchor_on"
DECISION_OPTIONS = {
    "R13": ("ss_fs4",),
    "S6": ("alias_s5", "run_180s"),
    "R2": ("reanchor_off", REANCHOR_ON),
}
"""Choices of ``--decide <case>=<option>``. R2 runs with ``reanchor_off`` when not decided."""


@dataclass(frozen=True)
class SteadyTwin:
    """A run of ``s9_soil_slope.run_one``; ``stored_id`` is its id in the stored harness file."""

    stored_id: str
    stored_file: str
    soil: str = "rigid"
    pad: str = "B"
    level: str = "top"
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    fs_kN: float = 4.0


@dataclass(frozen=True)
class EventTwin:
    """One ``r67_g1_screen`` branch: floor event on a leg, READY + 5 s or mid LEVEL."""

    stored_key: str | None
    stored_file: str | None
    event: str
    leg: str
    timing: str
    offset_s: float
    fs_kN: float
    level: str = "top"


@dataclass(frozen=True)
class VerdictCase:
    case_id: str
    chrono_name: str
    twin: SteadyTwin | EventTwin | None
    twin_status: str = STATUS_STORED
    note: str = ""

    @property
    def path(self) -> str:
        return PATH_EVENT if isinstance(self.twin, EventTwin) else PATH_STEADY


@dataclass(frozen=True)
class VerdictRun:
    """One run of the table: a case with a flow setting."""

    run_id: str
    bundle: str
    case_id: str
    setting: FlowSetting = field(default_factory=FlowSetting)


P0_FILE = "finB2_p0"
SLOPE_FILE = "finB2_harness"
H9_FILE = "finB2_h9"
R67_FILE = "finB2_r67_main"


def _rigid(stored_id: str, level: str, roll: float, pitch: float, fs_kN: float) -> SteadyTwin:
    return SteadyTwin(stored_id, P0_FILE, level=level, roll_deg=roll, pitch_deg=pitch, fs_kN=fs_kN)


def _rigid_row(level: str, roll: float, pitch: float, fs_kN: float) -> SteadyTwin:
    stored_id = f"base|rigid|{roll:g},{pitch:g}|{level}|Fs{fs_kN:g}|b1"
    return _rigid(stored_id, level, roll, pitch, fs_kN)


_H6_NOTE_J2 = ("S5 and S6 have one harness id: the harness stops at READY + 10 s, the 120 s / "
               "180 s length of the Chrono rows does not exist there")
CASES = {
    case.case_id: case for case in (
        VerdictCase("S1", "P3b_J1_B_top_Fs4", SteadyTwin("base|J1|B|top|Fs4", P0_FILE, "J1")),
        VerdictCase("S2", "P3b_J2_B_top_Fs4", SteadyTwin("base|J2|B|top|Fs4", P0_FILE, "J2")),
        VerdictCase("S3", "P3b_J2_B_middle_Fs4",
                    SteadyTwin("base|J2|B|middle|Fs4", P0_FILE, "J2", level="middle")),
        VerdictCase("S4", "P3b_J1_B_top_Fs4_m1p1",
                    SteadyTwin("H6|J1|B|top|flat|m1.1", SLOPE_FILE, "J1")),
        VerdictCase("S5", "P3b_J2_B_top_Fs4_m1p1",
                    SteadyTwin("H6|J2|B|top|flat|m1.1", SLOPE_FILE, "J2"), note=_H6_NOTE_J2),
        VerdictCase("S6", "P3b_J2_B_top_Fs4_m1p1_t180",
                    SteadyTwin("H6|J2|B|top|flat|m1.1", SLOPE_FILE, "J2"), STATUS_DECISION,
                    _H6_NOTE_J2),
        VerdictCase("S7", "S9SL_X6rb_J1_B_top_Fs4_rm2p86_p0",
                    SteadyTwin("H9|J1|B|top|roll_neg@k0.65", H9_FILE, "J1")),
        VerdictCase("S8", "S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0",
                    SteadyTwin("H3|J1|B|top|roll_pos@k0.875", SLOPE_FILE, "J1")),
        VerdictCase("R1", "K24_top_flat_Fs4", _rigid_row("top", 0.0, 0.0, 4.0)),
        VerdictCase("R2", "K24_top_fdown3.5_Fs4", _rigid_row("top", 0.0, PITCH_VERIFY_DEG, 4.0),
                    STATUS_STORED_GAP,
                    "Chrono runs REANCHOR here; the stored harness row has REANCHOR off"),
        VerdictCase("R3", "K24_top_fup3.5_Fs4", _rigid_row("top", 0.0, -PITCH_VERIFY_DEG, 4.0)),
        VerdictCase("R4", "K24_top_roll5.5_Fs4", _rigid_row("top", ROLL_DOWN_RIGHT_DEG, 0.0, 4.0)),
        VerdictCase("R5", "K24_top_rpB_Fs4", _rigid_row("top", RPB_ROLL_DEG, RPB_PITCH_DEG, 4.0)),
        VerdictCase("R6", "K0V_top_rpB_Fs0", _rigid_row("top", RPB_ROLL_DEG, RPB_PITCH_DEG, 0.0)),
        VerdictCase("R7", "K8_top_rpB_Fs8", _rigid_row("top", RPB_ROLL_DEG, RPB_PITCH_DEG, 8.0)),
        VerdictCase("R8", "A_middle_rpB_Fs0",
                    _rigid_row("middle", RPB_ROLL_DEG, RPB_PITCH_DEG, 0.0)),
        VerdictCase("R9", "A_bottom_rpB_Fs0",
                    _rigid_row("bottom", RPB_ROLL_DEG, RPB_PITCH_DEG, 0.0)),
        VerdictCase("R10", "JA_middle_flat_Fs4", _rigid_row("middle", 0.0, 0.0, 4.0)),
        VerdictCase("R11", "JA_bottom_flat_Fs4", _rigid_row("bottom", 0.0, 0.0, 4.0)),
        VerdictCase("R12", "E_G4_Fs4",
                    EventTwin(None, None, "G4", "RR", "ready", 0.0, 4.0), STATUS_NO_FINAL_ROW,
                    "r69_g5_screen key screen|top|4.0|ready|RR, G4 + 0 s; stored only in "
                    "rev69/r69_g5_top.json (older controller, no command hash)"),
        VerdictCase("R13", "E_SS_Fs4", None, STATUS_DECISION,
                    "no r67 / r69 row has SS (they run G4, RE1bF, FS24). Nearest: study A "
                    "A|rigid|RR|Fs{0,8}|two (SS, other F_s), r51 flat_Fs4|SS (12 s run, shorter "
                    "than the 20 s ramp, older controller)"),
        VerdictCase("R14", "E_RE1bF_Fs8",
                    EventTwin("screen|top|8.0|ready|RR", R67_FILE, "RE1bF", "RR", "ready", 0.0,
                              8.0)),
        VerdictCase("R15", "G1L_RE1bF_FL_top_Fs0",
                    EventTwin("screen|top|0.0|level|FL", R67_FILE, "RE1bF", "FL", "level", 0.05,
                              0.0),
                    note="harness event time = mid LEVEL, Chrono LOC + 3.0 s (r68_c72_judge pair)"),
        VerdictCase("R16", "G1L_RE1bF_FL_top_o050_Fs4",
                    EventTwin(None, None, "RE1bF", "FL", "level", 0.05, 4.0), STATUS_NO_FINAL_ROW,
                    "r69_g5_screen key screen|top|4.0|level|FL, RE1bF + 0.05 s; stored only in "
                    "rev69/r69_g5_top.json (older controller, no command hash); event time as R15"),
    )
}
SS_FS4_TWIN = EventTwin(None, None, "SS", "RR", "ready", 0.0, 4.0)
"""``--decide R13=ss_fs4``: r67 branch with SS, run to at least ramp end + 3 s (study A rule)."""
ALL_CASE_IDS = tuple(CASES)


def _eta_tag(eta_v: float) -> str:
    return f"eta{eta_v:.2f}"


def _main_setting(eta_v: float, **overrides) -> FlowSetting:
    return FlowSetting(is_enabled=True, eta_v=eta_v, **overrides)


def _sensitivity_runs() -> list[VerdictRun]:
    """Bundles D and E: R4 and S1 at eta 0.85 (criteria 8.3, 8.4)."""
    variants = (
        ("D", "dplow", {"dp_comp_Pa": DP_LOW_PA[0], "dp_unload_Pa": DP_LOW_PA[1]}),
        ("D", "dphigh", {"dp_comp_Pa": DP_HIGH_PA[0], "dp_unload_Pa": DP_HIGH_PA[1]}),
        ("D", "proportional", {"law": LAW_PROPORTIONAL}),
        ("E", "widthhalf", {"width_Pa": WIDTH_HALF_PA}),
        ("E", "widthdouble", {"width_Pa": WIDTH_DOUBLE_PA}),
    )
    return [VerdictRun(f"{bundle}_{case_id}_{_eta_tag(ETA_MAIN)}_{tag}", bundle, case_id,
                       _main_setting(ETA_MAIN, **overrides))
            for bundle, tag, overrides in variants for case_id in ("R4", "S1")]


def build_runs() -> list[VerdictRun]:
    """OFF (24) + the 60 runs of criteria 8.4."""
    runs = [VerdictRun(f"OFF_{case_id}", "OFF", case_id, FlowSetting(is_enabled=False))
            for case_id in ALL_CASE_IDS]
    for bundle, eta_v in (("A", ETA_MAIN), ("B", ETA_MIDDLE)):
        runs += [VerdictRun(f"{bundle}_{case_id}_{_eta_tag(eta_v)}", bundle, case_id,
                            _main_setting(eta_v)) for case_id in ALL_CASE_IDS]
    # every chunk through flow_share.share: the V-2 path and a check of the fast path
    runs += [VerdictRun(f"C_{case_id}_{_eta_tag(ETA_NO_EFFECT)}", "C", case_id,
                        _main_setting(ETA_NO_EFFECT, always_solve=True))
             for case_id in ("R1", "S1")]
    return runs + _sensitivity_runs()


def resolve_case(case_id: str, decisions: dict[str, str]) -> VerdictCase | None:
    """The case with its decision applied; None while a ``decision`` case has no choice yet.

    Raises:
        ValueError: a decision that ``DECISION_OPTIONS`` does not list.
    """
    case = CASES[case_id]
    choice = decisions.get(case_id)
    if choice is not None and choice not in DECISION_OPTIONS.get(case_id, ()):
        raise ValueError(f"{case_id}: unknown decision {choice!r}, "
                         f"expected {DECISION_OPTIONS.get(case_id, ())}")
    if case.twin_status != STATUS_DECISION:
        return case
    if choice is None:
        return None
    if case_id == "R13":
        return VerdictCase(case_id, case.chrono_name, SS_FS4_TWIN, STATUS_NO_FINAL_ROW, case.note)
    return VerdictCase(case_id, case.chrono_name, case.twin, STATUS_STORED_GAP, case.note)
