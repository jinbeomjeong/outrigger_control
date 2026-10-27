"""S6 Chrono bundle C: C2 R8-D1 (10 Hz, d = 1) closed loop on the L1-R Chrono model.

``00_docs/04_control/s6_control_spec.md`` rev. 31: 148 (cad work R-1 ... R-8), 150 (bundle C,
49 cases), 146 (judgement: absolute criteria + consistency flag). Judge module
``outrigger_sim.verify.s6_bundle_c``.

Usage (Chrono-dev python, project root)::

    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py list
    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py plan
    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py snaps [--jobs 5]   # new start states
    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py check [--jobs 7]   # 0.3 s per case
    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py run --approved [--jobs 7] [--only ...]
    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py judge --batch 07_results/S6/bundleC_L1R_<stamp>

Spec rev. 32 re-run (160 / 163.2 C-R7, 26 cases in groups A-D)::

    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py list --set rerun32
    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py check --set rerun32 [--jobs 7]
    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py run --set rerun32 --approved [--jobs 7]

``run --set rerun32`` also refuses while the installed ``control/c2.py`` lacks the P-R8-9 ... 11
names of :data:`RERUN32_KEYS` (``--allow-incomplete-c2`` overrides). Output folders
``07_results/S6/bundleC_rerun32[_check]_L1R_<stamp>``. G4 phase cases set ``settle_offset_s``
(settlement start = first READY + 5 s + offset, integer multiple of dt).

Spec rev. 33 re-run (169 / 172.2 C-R10, 15 cases in groups E-G)::

    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py list --set rerun33
    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py check --set rerun33 [--jobs 7]
    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py run --set rerun33 --approved [--jobs 7]

``run --set rerun33`` refuses while ``control/c2.py`` lacks P-R8-12 (:data:`RERUN33_KEYS`,
placeholder names). Group G = C-11: front ``k_frame`` (FL / FR) 1.1e8 N/m (gate) / 6.7e7 N/m
(record) through the per-leg L1 pad stiffness (:func:`front_frame_overrides`); the controller is
built from the parameters without that term and the crawler tangential bushing is held at its
no-frame value (:func:`c11_meta`, ``bundle_c.c11`` in result.json).

Spec rev. 34 re-run (177 / 179.2 C-R12, 16 cases in groups E, F, FS, H)::

    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py list --set rerun34
    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py check --set rerun34 [--jobs 7]
    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py run --set rerun34 --approved [--jobs 7]

``run --set rerun34`` refuses while ``control/c2.py`` lacks P-R8-13 (twist-mode re-approach,
spec names :data:`RERUN34_KEYS`) or P-R8-14 (``command_components_m_s``). Group H = beta cases
after the C-R11 leak fix; the judge module compares their D8 minimum force with the pre-fix runs.

Spec rev. 35 re-run (185 / 186 / 188.1 C-R13, 5 cases in groups H2, K)::

    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py list --set rerun35
    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py check --set rerun35 [--jobs 7]
    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py run --set rerun35 --approved [--jobs 7]

H2 = the H4 nose-down beta 0.69 / 1.6 cases (gate: REANCHOR >= 16.41 kN and the 150 D8 rows) and
the optional fup3.5 beta 1.6 / roll5.5 beta 0.69 (record, clears the 181.3 leak mark); the judge
compares them with the 1st batch only. K = ``C1_D8_top_rpB_b1.6_crkt3`` (crawler ``k_t`` x3 on
the beta 1.0 crawler value, U-R8-28 record), compared with the rerun34 x1 run. Same controller
requirement as rerun34.

C-S8-76 (spec rev. 69 360 / 363, non-planar start G8): a rigid block under one pad
(``chrono/pad_block``, height h = g0 - g_start on the restored settled snapshot), set
``g8c76`` = C1 (edge FL g_start 200 / 170 mm) + C2 (flat FL 55 / RR 200 mm), set ``g8c76_p28``
= C3 / C4 (P-S8-28 acceptance, needs ``--allow-p28-cases``), set ``g8c76_p28acc`` = C3 / C4 +
the C1 FL g170 re-run (spec rev. 70 366; FAULT end rule max(FAULT + 10 s, fault_reground_end +
5 s), cap FAULT + 25 s); the edge floor snapshot first::

    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py snaps --jobs 1      # S6_crawler_top_edge
    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py run --set g8c76 --approved --jobs 4 --tag c76
    python -I -X utf8 -u 04_scripts/02_chrono/run_S6C.py judge-g8 --batch 07_results/S6/bundleC_g8c76_c76_L1R_<stamp>

``run`` refuses to start without ``--approved`` (the user approves the bundle separately).
C-9 cases (R-5 on) are conditional: ``run`` leaves them out unless ``--with-c9`` (spec 150:
only when the C-1 G4 cases miss F_min).

Common settings (spec 150): ``C2Config().with_10hz_d1()`` (the installed c2.py; python-expert's
149 P-R8 changes are picked up when present, the meta records which), ``tau_v`` 0.1 s
(``L1SpeedActuator.configure_valve``, the command acceleration limit off), amplifier ramp none,
``d`` = 1 inside the controller (runner ``command_delay_periods`` 0, R-4 guard), IMU 100 Hz
samples (``imu_config_for_grade(grade, sample_period_s=0.01)``), pressures / strokes 10 Hz
instantaneous at the control instants, L1-R on (``OUTRIGGER_ROD_SIDE_MECHANICS``), rigid mast,
beta 1.0 GPa unless the case says otherwise, ideal leg sensors except the G3 / PS cases.

Parameter overrides (run time only, the YAML is not changed):

* beta 0.69 / 1.6 GPa: pad ``contact.rigid_floor.L1.kn_per_pad_N_m`` from the reference
  ``L1_beta_sensitivity_top/<beta>/k_L1_N_m`` and ``actuator.oil_bulk_modulus_eff_Pa`` (the L1-R
  machine recomputes ``k_h`` / ``k_r``; ``run_S4.py`` rule with L1-R on), **plant only**. Pad
  damping and the sensor-truth ``k_oil`` stay at the YAML values (ASSUMPTION). C-R11 (spec
  rev. 34 176.3, user decision U-R8-22 2026-10-24): the controller parameters are built
  without the beta (and C-11 frame) overrides, i.e. at beta 1.0 GPa (``nominal_pad_stiffness_N_m``
  2.2705e7 N/m, ``k_oil(e)`` at 1.0e9 Pa, :func:`controller_param_overrides`), and the crawler
  tangential bushing is held at the beta 1.0 ``(kt/kn)_pad`` ratio (``crawler_bushing_kt_scale``
  = ratio(beta 1.0) / ratio(run), multiplied with the C-11 factor; :func:`crawler_kt_scales`).
  Before rev. 34 both followed the case beta (spec 176.1 leak); ``result.json``
  ``bundle_c.beta_leak_fix`` records the values;
* ``L_0r`` 0.02 / 0.1 m (C-5): ``actuator.rod_side.column_length_m`` = YAML - 0.05 + L_0r and
  ``k_rod_side_N_m`` scaled by the column ratio (beta 1.0).

Start states: the settled crawler snapshots of ``07_results/states_L1R`` (legs unloaded, so
beta / L_0r do not enter; R-6). An override changes ``Params.sha256``: the snapshot is read with
the YAML fingerprint and re-tagged in memory (``bundle_c.snapshot_retagged`` in result.json),
only after the dyn rev. 37 5.24.3 check (four legs ``l1r_state`` LIFT, ``l1r_F_lock_N`` 0, no
pad contact, ``u_applied`` 0; ``bundle_c.snapshot_retag_check``); a failing snapshot (e.g.
``S6_crawler_top_flat_RRpre``, RR locked in contact) refuses the case.
New floors (:data:`NEW_FLOORS`) need ``snaps`` first (same procedure as ``run_S6.py snaps2``).

Records of dyn rev. 37 5.24 (meta only, the simulation is unchanged): ``bundle_c``
``pad_damping_override`` "none", ``leg_zeta_effective`` (one-DOF ``0.03 sqrt(k_1.0 / k_beta)``),
``saturation_stop_s`` 0.002 for every beta, ``expected_warnings`` (beta 1.6: the FL / FR
``t_sat > 2 c_n / k_n`` warning), ``warnings`` (every Python warning of the run, classified by
``verify.s6_bundle_c.classify_warning``) and ``saturation_steps`` (per leg steps, first time,
episodes with the static end value minus the limit; ``<= 0.25 kN`` = mechanism share).

Outputs: ``07_results/S6/bundleC_L1R_<stamp>/<case>/`` = the stage-2 files (``record/``,
``pads.npz``, ``result.json``, events, probe history) + ``r8_series.npz`` (R-7). Check runs go
to ``07_results/S6/bundleC_check_L1R_<stamp>/``. Units SI.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import sys
import time
import warnings
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

os.environ["OUTRIGGER_ROD_SIDE_MECHANICS"] = "one_sided_parallel"  # L1-R on (children inherit)
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(HERE))

import s6_stage2 as st  # noqa: E402
from outrigger_sim.verify.s6_bundle_c import (  # noqa: E402
    SATURATION_MECHANISM_SHARE_N as _SAT_SHARE_N,
)

RESULTS = ROOT / "07_results" / "S6"
STATES = ROOT / "07_results" / "states_L1R"
MAX_WORKERS = 7
"""P-cores for cases (i7-14700: 8 P-cores, 7 workers)."""
CHECK_DURATION_S = 0.3
CASE_TIMEOUT_S = 2400.0
CHECK_TIMEOUT_S = 600.0

NEW_FLOORS: dict[str, tuple[float, float]] = {
    "rp05": (2.7699, 1.7813),
    "rpB": (2.7355, 1.7592),
    "fdown3.2": (0.0, 3.2),
    "roll4.4": (4.4, 0.0),
}
"""Floors not in the stage-2 set (roll, pitch deg; theta > 0 = nose down): D8 upper boundary
point r+p+0.5 (spec 132 / 145 harness value; usage 1.0126, outside the D8 diamond + 0.01, kept
as the A1 rejection function check, U-R8-15), its boundary twin ``rpB`` = rp05 x 0.98759
(usage 2.7355 / 5.5 + 1.7592 / 3.5 = 1.0000, spec rev. 32 158.2, user decision U-R8-15
2026-10-24), operating limits nose down 3.2 deg and roll 4.4 deg (C-5, H4 P)."""
st.FLOORS.update(NEW_FLOORS)
NEW_SNAPSHOTS = (("top", "rp05"), ("middle", "rp05"), ("bottom", "rp05"),
                 ("top", "fdown3.2"), ("top", "roll4.4"),
                 ("top", "rpB"), ("middle", "rpB"), ("bottom", "rpB"))
G8_FLOORS: dict[str, tuple[float, float]] = {"edge": (2.2, 1.6)}
"""C-S8-76 (spec rev. 69 360.1): the operating start-rule edge floor of the G8 harness
(``r69_g8_screen.FLOORS["edge"]``: |roll|/4.4 + |pitch|/3.2 = 1.0, same signs as rpB)."""
st.FLOORS.update(G8_FLOORS)
G8_SNAPSHOTS = (("top", "edge"),)
"""Settled crawler start of the edge floor (built by ``snaps`` like :data:`NEW_SNAPSHOTS`)."""

R8_EXTRA_S = 8.0
"""Run length added to the stage-2 length (spec rev. 26: levelling +5-6 s at 10 Hz, ASSUMPTION
margin)."""
TAU_V_S = 0.1
AMP_RAMP_S = 0.1
BETA_KEYS = {0.69: "beta_6.9e+08", 1.0: "beta_1.0e+09", 1.6: "beta_1.6e+09"}
ROD_DEAD_LENGTH_YAML_M = 0.05
"""``column_length_m = stroke - e_op + rod_dead_length`` with 0.05 m in the YAML (comment of
``actuator.rod_side.column_length_m``)."""
IMU_SAMPLE_PERIOD_S = 0.01
LEGS = ("FL", "FR", "RL", "RR")
R8_SERIES_NAME = "r8_series.npz"


@dataclass(frozen=True)
class BundleCCase:
    """One bundle-C case: a stage-2 scenario plus the R8 variant."""

    case_id: str
    config: str  # "C-1", "C-4", ...
    scenario: st.Stage2Case
    beta_GPa: float = 1.0
    tau_v_s: float = TAU_V_S
    amp_ramp: str = "none"
    L0r_m: float | None = None
    command_offset_s: float = 0.0
    increment: str = "sym0.25"  # "sym0.25" | "sym0.1" | "asym"
    twist_reference: str = "measured_Sii"  # | "k_nom"
    fast_relevel: bool = False
    sensor_model: bool = False
    """Pressure sensors with the WIKA error model (G3 / PS); False = ideal leg sensors."""
    settle_offset_s: float = 0.0
    """G4 settlement start phase offset (spec rev. 32 163.2 C-R7): the RR settlement starts at
    the first READY + 5 s + this offset; an integer multiple of the model dt (checked)."""
    fast_relevel_horizon_periods: int | None = None
    """P-R8-10 ``FastRelevelSettings.horizon_periods`` override (spec name; None = the
    ``with_10hz_d1()`` default). Needs the python-expert change; refused without it."""
    conditional: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)
    front_frame_stiffness_N_m: float | None = None
    """C-11 (spec rev. 33 170): ``k_frame`` of FL / FR in series with the leg (None = YAML
    ``actuator.frame_stiffness_N_m``); applied through the per-leg L1 pad stiffness
    (:func:`front_frame_overrides`), the controller keeps the nominal stiffness."""
    c11_role: str | None = None
    """C-11: "gate" (centre value, judged) or "record" (lower bound, recorded)."""
    crawler_kt_factor: float = 1.0
    """Crawler tangential stiffness sensitivity factor (spec rev. 35 186 / U-R8-28): multiplies
    the ``crawler_bushing_kt_scale`` after the beta / C-11 compensation, so it acts on the beta
    1.0 crawler value. ``chrono/crawler_bushing`` keeps the tangential damping ratio, i.e. ``ct``
    scales with ``sqrt(factor)`` (ASSUMPTION of that module, the earlier x0.3 / x3 runs)."""
    preground_leg: str | None = field(default=None, repr=False)
    """C-S8-72 (spec rev. 67 345.3): the one leg already on the floor in the start snapshot
    (PS-7a ``RRpre`` / ``FLpre``); the snapshot check allows it LOCK / in contact / F_lock > 0
    (``verify.s6_bundle_c.snapshot_retag_check(preground_leg=...)``). None = 5.24.3 as before."""
    end_after_ready_s: float | None = field(default=None, repr=False)
    """C-S8-72: stop the run at the first READY + this (PS-7: READY + 5 s, spec 92); the
    scenario length is then only the upper bound. None = fixed length (as before)."""

    pad_block: tuple[str, float] | None = field(default=None, repr=False)
    """C-S8-76 (spec rev. 69 360.1 / 363): ``(leg, g_start_m)``: after the crawler settle a rigid
    block under that pad makes its zero-stroke gap ``g_start`` (block height h = g0 - g_start,
    g0 measured on the restored start snapshot; ``chrono/pad_block``). None = no block."""

    OPTIONAL_META = ("preground_leg", "end_after_ready_s", "pad_block")
    """Fields left out of :meth:`to_meta` while None and out of ``repr`` (``repr=False``), so
    the earlier cases' definitions (meta and repr hashes) stay as they were."""

    @property
    def snapshot(self) -> str:
        return self.scenario.snapshot

    @property
    def duration_s(self) -> float:
        return self.scenario.duration_s + R8_EXTRA_S

    @property
    def fine_dt(self) -> bool:
        return self.scenario.fine_dt

    def blocked_in(self, states_dir: Path) -> str | None:
        return self.scenario.blocked_in(states_dir)

    def wall_estimate_s(self) -> float:
        sc = replace(self.scenario, duration_s=self.duration_s)
        return sc.wall_estimate_s()

    def to_meta(self) -> dict[str, Any]:
        out = {k: v for k, v in asdict(self).items() if k != "scenario"
               and not (k in self.OPTIONAL_META and v is None)}
        out["scenario"] = asdict(self.scenario)
        out["duration_s"] = self.duration_s
        return out


def _sc(cid: str, group: str, level: str, floor: str, **kw) -> st.Stage2Case:
    """Stage-2 scenario with the stage-2 run length (+ CHECK extension)."""
    extra = kw.pop("extra", 0.0)
    h4 = kw.get("h4", True)
    check = kw.get("check_time_s", st.CHECK_S)
    if "duration_s" not in kw:
        kw["duration_s"] = st._length(floor, h4=h4, check_s=check, extra=extra)
    case = st.Stage2Case(cid, group, level, floor, **kw)
    return replace(case, duration_s=case.duration_s + st.check_extra_s(case))


def _d8(level: str, floor: str) -> st.Stage2Case:
    return _sc(f"D8_{level}_{floor}", "D8", level, floor, items=("R", "3", "8"))


def _g4(contact: str) -> st.Stage2Case:
    return _sc(f"G4_top_flat_settleRR_{contact}", "G4", "top", "flat", contact=contact,
               event="settle_RR", extra=st.T_SETTLE_EXTRA, items=("6",))


def _re1bf() -> st.Stage2Case:
    base = st._length("flat", h4=True, check_s=st.CHECK_S)
    return _sc("RE1bF_top_flat_dropRR30", "RE1b", "top", "flat", event="drop_RR_30",
               duration_s=base + st.T_RE1BF_EXTRA, items=("6", "7", "GE1"))


def _re1bp() -> st.Stage2Case:
    base = st._length("flat", h4=True, check_s=st.CHECK_S)
    return _sc("RE1bP_top_flat_dropRR30_probe", "RE1b", "top", "flat", event="drop_RR_30_probe",
               duration_s=base + st.T_RE1BF_EXTRA, items=("6", "7", "GE1", "Q2"))


def _b(beta: float) -> str:
    return f"b{beta:.2f}".rstrip("0").rstrip(".") if beta != 1.0 else "b1.0"


def bundle_c_cases() -> list[BundleCCase]:
    """The 49 cases of spec 150 (C-9 marked conditional)."""
    out: list[BundleCCase] = []

    def add(cid, cfg, sc, **kw):
        out.append(BundleCCase(cid, cfg, replace(sc, case_id=cid), **kw))

    # C-1 (24)
    for floor in ("roll5.5", "fdown3.5", "fup3.5", "rp05"):
        for beta in (0.69, 1.6):
            add(f"C1_D8_top_{floor}_{_b(beta)}", "C-1", _d8("top", floor), beta_GPa=beta)
    for level in ("middle", "bottom"):
        add(f"C1_D8_{level}_rp05_b1.6", "C-1", _d8(level, "rp05"), beta_GPa=1.6)
    add("C1_H4V_top_fdown3.5", "C-1", _sc("H4V", "G2-R", "top", "fdown3.5",
                                          items=("R", "2", "3", "8")),
        notes=("H4 nose down, verification point pitch +3.5 deg",))
    add("C1_H4P_top_fdown3.2", "C-1", _sc("H4P", "G2-R", "top", "fdown3.2",
                                          items=("R", "2", "3", "8")),
        notes=("H4 nose down, operating point pitch +3.2 deg; start check in VERIFICATION "
               "mode like every stage-2 case (ASSUMPTION)",))
    for floor in ("flat", "roll3"):
        add(f"C1_G1_top_{floor}", "C-1",
            _sc("G1", "G1", "top", floor, contact="pressure", check_time_s=0.0,
                combined_verdict=False, items=("1",)))
    for floor in ("flat", "fdown3.5"):
        add(f"C1_G3_top_{floor}_normal_zeroed", "C-1",
            _sc("G3", "G3", "top", floor, grade="normal_zeroed", items=("2",)),
            sensor_model=True, notes=("IMU normal grade + pressure normal grade + calibration",))
    for contact in ("pressure", "combined"):
        add(f"C1_G4_{contact}", "C-1", _g4(contact))
    base = st._length("flat", h4=True, check_s=st.CHECK_S)
    add("C1_RE1b_top_flat_settleRR30", "C-1",
        _sc("RE1b", "RE1b", "top", "flat", event="settle_RR_30",
            duration_s=base + st.T_RE1B_EXTRA, items=("6", "7", "GE1")))
    add("C1_RE1bF_top_flat_dropRR30", "C-1", _re1bf())
    add("C1_RE1bP_top_flat_dropRR30_probe", "C-1", _re1bp())
    for sign in (+10.0, -10.0):
        add(f"C1_PS7_flat_FL{'p' if sign > 0 else 'm'}10_cal", "C-1",
            _sc("PS7", "PS", "top", "flat", items=("PS",), head_offset_bar=(sign, 0.0, 0.0, 0.0)),
            sensor_model=True)
    add("C1_G5_top_flat_change_p3", "C-1",
        _sc("G5", "G5", "top", "flat", event="target_change",
            duration_s=st.CHECK_S + st.T_TARGET, items=("T",)))
    # C-4 (6): tau_v 0.05 / 0.15
    for tau in (0.05, 0.15):
        tag = f"tv{tau:g}"
        add(f"C4_{tag}_D8_top_roll5.5_b1.6", "C-4", _d8("top", "roll5.5"), beta_GPa=1.6,
            tau_v_s=tau)
        add(f"C4_{tag}_D8_top_fup3.5_b1.6", "C-4", _d8("top", "fup3.5"), beta_GPa=1.6,
            tau_v_s=tau)
        add(f"C4_{tag}_G4_pressure", "C-4", _g4("pressure"), tau_v_s=tau)
    # C-4b (3): amplifier per-step ramp 0.1 s
    add("C4b_D8_top_roll5.5_b1.6", "C-4b", _d8("top", "roll5.5"), beta_GPa=1.6,
        amp_ramp="per_step")
    add("C4b_D8_bottom_rp05_b1.6", "C-4b", _d8("bottom", "rp05"), beta_GPa=1.6,
        amp_ramp="per_step")
    add("C4b_G4_pressure", "C-4b", _g4("pressure"), amp_ramp="per_step")
    # C-5 (6): L_0r 0.02 / 0.1 m at the operating limits
    for l0r in (0.02, 0.1):
        tag = f"L0r{l0r:g}"
        add(f"C5_{tag}_top_fdown3.2", "C-5", _d8("top", "fdown3.2"), L0r_m=l0r)
        add(f"C5_{tag}_top_roll4.4", "C-5", _d8("top", "roll4.4"), L0r_m=l0r)
        add(f"C5_{tag}_G4_pressure", "C-5", _g4("pressure"), L0r_m=l0r)
    # C-6 (2): output +20 ms
    add("C6_G4_pressure", "C-6", _g4("pressure"), command_offset_s=0.02)
    add("C6_D8_top_roll5.5_b1.6", "C-6", _d8("top", "roll5.5"), beta_GPa=1.6,
        command_offset_s=0.02)
    # C-7 (4): increment limit
    add("C7_sym0.1_D8_top_rp05_b1.6", "C-7", _d8("top", "rp05"), beta_GPa=1.6,
        increment="sym0.1")
    add("C7_sym0.1_D8_top_roll5.5_b1.6", "C-7", _d8("top", "roll5.5"), beta_GPa=1.6,
        increment="sym0.1")
    add("C7_asym_G4_pressure", "C-7", _g4("pressure"), increment="asym")
    add("C7_asym_RE1bF_top_flat_dropRR30", "C-7", _re1bf(), increment="asym")
    # C-9 (2, conditional): R-5 fast re-level
    for contact in ("pressure", "combined"):
        add(f"C9_R5_G4_{contact}", "C-9", _g4(contact), fast_relevel=True, conditional=True,
            notes=("only when the C-1 G4 cases miss F_min (spec 150)",))
    # C-10 (2): twist / guard gain reference k_nom
    add("C10_knom_G4_combined", "C-10", _g4("combined"), twist_reference="k_nom")
    add("C10_knom_RE1bP_top_flat_dropRR30_probe", "C-10", _re1bp(), twist_reference="k_nom")
    ids = [c.case_id for c in out]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate bundle-C case id")
    return out


G4_PHASE_OFFSETS_S = (0.0, 0.025, 0.05, 0.075)
"""Spec rev. 32 160 B: G4 settlement start phase offsets inside one 0.1 s control period."""
L0R_G4_PHASE_OFFSETS_S = (0.0, 0.05)


def _ph(cid: str, offset: float) -> str:
    return cid if offset == 0.0 else f"{cid}_ph{offset:g}"


def rerun32_groups() -> dict[str, list[BundleCCase]]:
    """Spec rev. 32 160 / 163.2 C-R7 re-run (26 cases; user decision U-R8-16 2026-10-24: the
    run itself waits for the user's confirmation). Cases with the bundle-C definition keep their
    bundle-C id (direct comparison with ``bundleC_L1R_20261024_100736``); rpB floors and G4
    phase offsets are new ids. Controller = the installed ``with_10hz_d1()`` (P-R8-9 ... 11,
    R-5 default on with the P-R8-10 horizon) — no per-case R-5 switch here."""
    old = {c.case_id: c for c in bundle_c_cases()}
    groups: dict[str, list[BundleCCase]] = {"A": [], "B": [], "C": [], "D": []}

    def add(group, cid, cfg, sc, **kw):
        groups[group].append(BundleCCase(cid, cfg, replace(sc, case_id=cid), **kw))

    # A (7): D8 not judged in bundle C + the CHECK fix (P-R8-9)
    groups["A"].append(old["C1_D8_top_fup3.5_b0.69"])
    for beta in (0.69, 1.6):
        add("A", f"C1_D8_top_rpB_{_b(beta)}", "C-1", _d8("top", "rpB"), beta_GPa=beta)
    for level in ("middle", "bottom"):
        add("A", f"C1_D8_{level}_rpB_b1.6", "C-1", _d8(level, "rpB"), beta_GPa=1.6)
    add("A", "C4b_D8_bottom_rpB_b1.6", "C-4b", _d8("bottom", "rpB"), beta_GPa=1.6,
        amp_ramp="per_step")
    add("A", "C7_sym0.1_D8_top_rpB_b1.6", "C-7", _d8("top", "rpB"), beta_GPa=1.6,
        increment="sym0.1")
    # B (12): G4 R-5 default + horizon (157.2), sample phase spread
    for contact in ("pressure", "combined"):
        for off in G4_PHASE_OFFSETS_S:
            add("B", _ph(f"C1_G4_{contact}", off), "C-1", _g4(contact), settle_offset_s=off)
    for off in L0R_G4_PHASE_OFFSETS_S:
        add("B", _ph("C5_L0r0.1_G4_pressure", off), "C-5", _g4("pressure"), L0r_m=0.1,
            settle_offset_s=off)
    groups["B"].append(old["C4_tv0.15_G4_pressure"])
    groups["B"].append(old["C6_G4_pressure"])
    # C (3): PROBE low-load abort (P-R8-11)
    for cid in ("C1_RE1bP_top_flat_dropRR30_probe", "C10_knom_RE1bP_top_flat_dropRR30_probe",
                "C1_RE1bF_top_flat_dropRR30"):
        groups["C"].append(old[cid])
    # D (4): regression of R-5 / P-R8-9 / P-R8-11
    for cid in ("C1_G1_top_flat", "C1_D8_top_roll5.5_b1.6", "C1_RE1b_top_flat_settleRR30",
                "C1_PS7_flat_FLp10_cal"):
        groups["D"].append(old[cid])
    return groups


def rerun32_cases() -> list[BundleCCase]:
    out = [c for g in rerun32_groups().values() for c in g]
    ids = [c.case_id for c in out]
    if len(ids) != len(set(ids)) or len(ids) != 26:
        raise RuntimeError(f"rerun32: expected 26 distinct cases, got {len(ids)}")
    return out


def _kf_tag(k_frame_N_m: float) -> str:
    """``1.1e8`` / ``6.7e7``."""
    mant, exp = f"{k_frame_N_m:.1e}".split("e")
    return f"{mant}e{int(exp)}"


def rerun33_groups() -> dict[str, list[BundleCCase]]:
    """Spec rev. 33 169 re-run (15 cases; user decisions U-R8-19 / U-R8-20 2026-10-24, the run
    waits for the user's confirmation). E (3): P-R8-12 effect on the RE1b drops; F (4):
    regression (RE1b settle, G4 combined ph0.075, G1 flat, H4V fdown3.5 beta 1.0 = the missing
    H4 nose-down check of rev. 32); G (8): C-11 front ``k_frame`` 1.1e8 (gate) / 6.7e7 (record)
    x {D8 top rpB beta 0.69, H4V fdown3.5 beta 1.0, G4 combined ph0.075, RE1bF}. E / F keep the
    ids of their earlier definition (direct comparison with ``bundleC_rerun32_L1R_20261024_114455``
    and ``bundleC_L1R_20261024_100736``)."""
    old = {c.case_id: c for c in bundle_c_cases()}
    old.update({c.case_id: c for c in rerun32_cases()})
    groups: dict[str, list[BundleCCase]] = {"E": [], "F": [], "G": []}
    for cid in ("C1_RE1bP_top_flat_dropRR30_probe", "C10_knom_RE1bP_top_flat_dropRR30_probe",
                "C1_RE1bF_top_flat_dropRR30"):
        groups["E"].append(old[cid])
    for cid in ("C1_RE1b_top_flat_settleRR30", "C1_G4_combined_ph0.075", "C1_G1_top_flat",
                "C1_H4V_top_fdown3.5"):
        groups["F"].append(old[cid])
    bases = ("C1_D8_top_rpB_b0.69", "C1_H4V_top_fdown3.5", "C1_G4_combined_ph0.075",
             "C1_RE1bF_top_flat_dropRR30")
    for role in ("gate", "record"):
        kf = C11_FRAME_N_M[role]
        for cid in bases:
            b = old[cid]
            new_id = f"C11_kf{_kf_tag(kf)}_{cid.removeprefix('C1_')}"
            groups["G"].append(replace(
                b, case_id=new_id, config="C-11", scenario=replace(b.scenario, case_id=new_id),
                front_frame_stiffness_N_m=kf, c11_role=role,
                notes=(*b.notes, f"C-11 front k_frame {kf:.2g} N/m ({role}), spec rev. 33 170")))
    return groups


def rerun33_cases() -> list[BundleCCase]:
    out = [c for g in rerun33_groups().values() for c in g]
    ids = [c.case_id for c in out]
    if len(ids) != len(set(ids)) or len(ids) != 15:
        raise RuntimeError(f"rerun33: expected 15 distinct cases, got {len(ids)}")
    return out


PS_RERUN34_SEED = 12346
"""Spec rev. 34 177 F (sensor): the existing PS-1 definition "normal grade + calibration, top
flat" (``s6_stage2.ps_cases`` ``PS1_flat_normal_cal_s12346``, the first PS-1 seed; seed 12345 is
the stage-2 matrix itself). ASSUMPTION of the choice: the spec names the condition, not the seed."""

RERUN34_ROLES = {"C7_sym0.1_D8_top_rpB_b1.6": "record", "C11_kf1.1e8_D8_top_rpB_b0.69": "gate"}
"""Spec rev. 34 177 H: "record" = recorded (failures listed apart in the judge meta), "gate" =
judged. The C-11 RE1bF cases of E carry their ``c11_role`` from rev. 33."""


def rerun34_groups() -> dict[str, list[BundleCCase]]:
    """Spec rev. 34 177 re-run (16 cases; user decisions U-R8-21 ... 23 2026-10-24, the run
    waits for the user's confirmation). E (5): P-R8-13 effect (U57); F (4): regression; FS (1):
    one PS case (1-sample R-5 / re-approach false firing); H (6): beta cases after the C-R11
    leak fix (compared with the pre-fix 1st / rerun32 / rerun33 values by the judge module).
    Every id keeps its earlier definition (direct comparison)."""
    old = {c.case_id: c for c in bundle_c_cases()}
    old.update({c.case_id: c for c in rerun32_cases()})
    old.update({c.case_id: c for c in rerun33_cases()})
    groups: dict[str, list[BundleCCase]] = {"E": [], "F": [], "FS": [], "H": []}
    for cid in ("C1_RE1bP_top_flat_dropRR30_probe", "C10_knom_RE1bP_top_flat_dropRR30_probe",
                "C1_RE1bF_top_flat_dropRR30", "C11_kf1.1e8_RE1bF_top_flat_dropRR30",
                "C11_kf6.7e7_RE1bF_top_flat_dropRR30"):
        groups["E"].append(old[cid])
    for cid in ("C1_RE1b_top_flat_settleRR30", "C1_G4_combined_ph0.075", "C1_G1_top_flat",
                "C1_H4V_top_fdown3.5"):
        groups["F"].append(old[cid])
    ps_id = f"C1_PS1_flat_normal_cal_s{PS_RERUN34_SEED}"
    ps = _sc("PS1", "PS", "top", "flat", items=("PS",), seed=PS_RERUN34_SEED)
    groups["FS"].append(BundleCCase(
        ps_id, "C-1", replace(ps, case_id=ps_id), sensor_model=True,
        notes=("PS-1 normal grade + calibration, top flat (spec rev. 34 177 F sensor): "
               "1-sample watch false firing = 0",)))
    for cid in ("C1_D8_top_rpB_b0.69", "C1_D8_top_rpB_b1.6", "C1_D8_top_fup3.5_b0.69",
                "C1_D8_top_roll5.5_b1.6", "C7_sym0.1_D8_top_rpB_b1.6",
                "C11_kf1.1e8_D8_top_rpB_b0.69"):
        groups["H"].append(old[cid])
    return groups


def rerun34_cases() -> list[BundleCCase]:
    out = [c for g in rerun34_groups().values() for c in g]
    ids = [c.case_id for c in out]
    if len(ids) != len(set(ids)) or len(ids) != 16:
        raise RuntimeError(f"rerun34: expected 16 distinct cases, got {len(ids)}")
    return out


CRAWLER_KT_SENS_FACTOR = 3.0
"""Spec rev. 35 186 / U-R8-28 (2026-10-24): crawler ``k_t`` x3 lift-off transient record case;
x3 = the upper end of the assumed range x0.3 ... x3 (``chrono/crawler_bushing.KT_SCALES``)."""
CRAWLER_KT_SENS_BASE = "C1_D8_top_rpB_b1.6"
"""Spec rev. 35 186: "C1 D8 top rpB beta 1.6 x crawler k_t x3" (its minimum sits in the crawler
lift-off transient, 181.1: RL +0.38 s after lift-off, 38.55 kN in rerun34)."""
RERUN35_ROLES = {"C1_D8_top_fdown3.5_b0.69": "gate", "C1_D8_top_fdown3.5_b1.6": "gate",
                 "C1_D8_top_fup3.5_b1.6": "record", "C1_D8_top_roll5.5_b0.69": "record",
                 f"{CRAWLER_KT_SENS_BASE}_crkt3": "record"}
"""Spec rev. 35 185 / U-R8-24: the two H4 nose-down cases are the gate (REANCHOR >= 16.41 kN and
the 150 D8 rows); the optional pair only clears the leak mark; the crawler case is a record
(U-R8-28, S7 item, not a gate)."""

def rerun35_groups() -> dict[str, list[BundleCCase]]:
    """Spec rev. 35 185 (C-R13, user decisions U-R8-24 / U-R8-28 2026-10-24; the run waits for
    the user's confirmation). H2 (4): the H4 nose-down beta cases (gate) and the optional pair
    (record) of the 1st bundle, same ids as the 1st batch (``leak_compare`` against the 1st
    values); K (1): the crawler ``k_t`` x3 lift-off transient record of rpB beta 1.6."""
    old = {c.case_id: c for c in bundle_c_cases()}
    old.update({c.case_id: c for c in rerun32_cases()})
    groups: dict[str, list[BundleCCase]] = {"H2": [], "K": []}
    for cid in ("C1_D8_top_fdown3.5_b0.69", "C1_D8_top_fdown3.5_b1.6",
                "C1_D8_top_fup3.5_b1.6", "C1_D8_top_roll5.5_b0.69"):
        groups["H2"].append(old[cid])
    b = old[CRAWLER_KT_SENS_BASE]
    new_id = f"{CRAWLER_KT_SENS_BASE}_crkt3"
    groups["K"].append(replace(
        b, case_id=new_id, scenario=replace(b.scenario, case_id=new_id),
        crawler_kt_factor=CRAWLER_KT_SENS_FACTOR,
        notes=(*b.notes, "crawler k_t x3 (ct x sqrt 3, same zeta) on the beta 1.0 crawler value; "
               "spec rev. 35 186 / U-R8-28 record")))
    return groups


def rerun35_cases() -> list[BundleCCase]:
    out = [c for g in rerun35_groups().values() for c in g]
    ids = [c.case_id for c in out]
    if len(ids) != len(set(ids)) or len(ids) != 5:
        raise RuntimeError(f"rerun35: expected 5 distinct cases, got {len(ids)}")
    return out


PS7_R8_END_AFTER_READY_S = 5.0
"""Spec 92 / rev. 67 345.1: a PS-7 run ends at READY + 5 s."""
PS7_R8_EXTRA_S = 60.0
"""C-S8-72 upper bound added to the stage-2 PS-7 length (ASSUMPTION: the harness READY of PS7a_RR
proj 63 s vs ref 40 s, spec rev. 67 344.2; the run stops at READY + 5 s)."""
PS7_R8_KEYS = (("PS7a_RR_R8", "a", "RR"), ("PS7a_FL_R8", "a", "FL"),
               ("PS7b_RR_R8", "b", "RR"), ("PS7c_RR_R8", "c", "RR"))
"""Spec rev. 67 345.1 #12-15: (case key, PS-7 variant, leg)."""


def ps7r8_cases() -> list[BundleCCase]:
    """C-S8-72 (spec rev. 67 345.1 #12-15): R8 PS-7 on L1-R. 7a = settled pre-grounded start
    snapshot (``S6_crawler_top_flat_RRpre`` / ``..._FLpre``, leg at g0 + 2 mm); 7b / 7c = the
    stage-2 in-run pre-extension (``PreExtend``) of RR to g0 - 1.5 / - 2.7 mm. Normal-grade
    pressure sensors with the zero calibration on (``sensor_model``), the R8 preset, run end READY
    + 5 s (:data:`PS7_R8_END_AFTER_READY_S`)."""
    by_key = {c.case_id[3]: c for c in st.ps7_cases()}  # "PS7a_flat_..." -> "a"
    out = []
    for cid, key, leg in PS7_R8_KEYS:
        sc = by_key[key]
        if key == "a":
            sc = replace(sc, snapshot_override=st.preground_snapshot_name(leg))
        elif leg != "RR":
            raise ValueError(f"{cid}: PS-7{key} only on RR (stage-2 pre-extension)")
        note = (f"C-S8-72 / spec rev. 67 345.1: PS-7{key} {leg} R8 (with_10hz_d1), "
                + ("settled pre-grounded snapshot g0 + 2 mm" if key == "a"
                   else f"in-run pre-extension g0 {st.PS7_PRE_EXTEND_MM[key]:+.1f} mm"))
        sc = replace(sc, case_id=cid, duration_s=sc.duration_s + PS7_R8_EXTRA_S, notes=(note,))
        out.append(BundleCCase(
            cid, "PS7-R8", sc, sensor_model=True,
            preground_leg=leg if key == "a" else None,
            end_after_ready_s=PS7_R8_END_AFTER_READY_S, notes=(note,)))
    return out


G8_EXTRA_S = 60.0
"""C-S8-76 upper bound added to the stage-2 D8 length (ASSUMPTION, as PS-7: harness READY of the
edge cases 53-57 s; the run stops at READY + 5 s or FAULT + :data:`G8_END_AFTER_FAULT_S`)."""
G8_END_AFTER_READY_S = 5.0
"""Spec 360.1 harness: controller from CHECK to READY + 5 s."""
G8_END_AFTER_FAULT_S = 10.0
"""C-S8-76: stop 10 s after the controller has entered FAULT (ASSUMPTION; enough to see which
legs stay lifted, the harness ran its FAULT cases to about 128 s)."""
G8_END_AFTER_REGROUND_S = 5.0
G8_FAULT_CAP_S = 25.0
"""Spec rev. 70 366 end rule after a FAULT: stop at max(first FAULT-phase entry + 10 s,
``fault_reground_end`` + 5 s), at most first FAULT-phase entry + 25 s (the P-S8-28 / U-S8-79
re-ground takes at most 15 s). A started re-ground without its end runs to the cap."""
G8_REGROUND_EVENT_PREFIXES = ("fault_reground_", "WARN_FAULT_REGROUND_ABORT")


def g8_fault_stop(state: dict) -> bool:
    """End rule of :data:`G8_FAULT_CAP_S` on the runner state (``fault_t`` = first entry into
    a FAULT phase, ``rg_start_t`` / ``rg_end_t`` = re-ground start / end or abort event, ``last_t``
    = the latest control instant; absolute s)."""
    tf, t = state.get("fault_t"), state.get("last_t")
    if tf is None or t is None:
        return False
    eps = 1e-9
    if t >= tf + G8_FAULT_CAP_S - eps:
        return True
    if t < tf + G8_END_AFTER_FAULT_S - eps:
        return False
    started, ended = state.get("rg_start_t"), state.get("rg_end_t")
    if started is None:
        return True
    return ended is not None and t >= ended + G8_END_AFTER_REGROUND_S - eps


def _phase_spans(phases: list[tuple[float, str]], name: str) -> list[tuple[float, float | None]]:
    """(start, end) of every interval in phase ``name`` (relative s; end None = until the run
    end)."""
    out = []
    for (t1, p), nxt in zip(phases, [*phases[1:], (None, "end")], strict=True):
        if p == name:
            out.append((t1, nxt[0]))
    return out


G8_RUN_STEP_EVERY = 50
"""Crawler-gap record every 50 steps (10 ms at the L1 dt 2e-4 s)."""
G8C76_CASES = (
    # (case id, spec 363 row, floor, leg, g_start mm, harness h mm, run now)
    ("G8C1_top_edge_FL_g200", "C1", "edge", "FL", 200.0, 139.258, True),
    ("G8C1_top_edge_FL_g170", "C1", "edge", "FL", 170.0, 169.258, True),
    ("G8C2_top_flat_FL_g55", "C2", "flat", "FL", 55.0, 285.802, True),
    ("G8C2_top_flat_RR_g200", "C2", "flat", "RR", 200.0, 145.718, True),
    ("G8C3_top_edge_RL_g230", "C3", "edge", "RL", 230.0, 119.158, False),
    ("G8C3_top_edge_FL_g20", "C3", "edge", "FL", 20.0, 319.258, False),
    ("G8C4_top_edge_RR_g230", "C4", "edge", "RR", 230.0, 118.101, False),
)
"""Spec rev. 69 363 C1-C4 (C-S8-76). ``g_start`` is the case definition (360.1: zero-stroke gap
of the leg after the block); ``harness h`` = harness g0 - g_start (``r69_g8_slope.json`` /
``r69_g8_top_Fs4.0.json`` ``info.g0_mm``), recorded for comparison only. C3 / C4 are P-S8-28
acceptance cases: defined, refused by ``run`` unless ``--allow-p28-cases``.
Seal friction: the L1-R plant has none (CLAUDE.md: F_s only in L2b); the harness rows are F_s 4
kN (spec 363), the Chrono runs are F_s 0 by construction (recorded ``fs_kN_plant`` 0)."""
G8C76_HARNESS_FS_KN = 4.0


def g8c76_cases(*, run_only: bool | None = None) -> list[BundleCCase]:
    """C-S8-76 cases (spec rev. 69 363): the D8 scenario of the floor (top, ideal leg sensors,
    the R8 preset), a block under one pad (:attr:`BundleCCase.pad_block`), end READY + 5 s.
    ``run_only`` True = C1 / C2, False = C3 / C4, None = all."""
    out = []
    for cid, row, floor, leg, g_mm, h_harness_mm, now in G8C76_CASES:
        if run_only is not None and now is not run_only:
            continue
        note = (f"C-S8-76 / spec rev. 69 363 {row}: {floor} top, block under {leg}, zero-stroke "
                f"gap g_start {g_mm:g} mm (harness h {h_harness_mm:.1f} mm, harness F_s "
                f"{G8C76_HARNESS_FS_KN:g} kN; L1-R plant F_s 0)"
                + ("" if now else "; P-S8-28 acceptance case, not run now"))
        sc = _d8("top", floor)
        sc = replace(sc, case_id=cid, group="G8", items=("G8",),
                     duration_s=sc.duration_s + G8_EXTRA_S, notes=(note,))
        out.append(BundleCCase(cid, f"G8-{row}", sc, conditional=not now, notes=(note,),
                               end_after_ready_s=G8_END_AFTER_READY_S,
                               pad_block=(leg, g_mm * 1e-3)))
    return out


def g8c76_run_cases() -> list[BundleCCase]:
    return g8c76_cases(run_only=True)


def g8c76_def_cases() -> list[BundleCCase]:
    return g8c76_cases(run_only=False)


G8C76_P28_RERUN_IDS = ("G8C1_top_edge_FL_g170",)
"""Spec rev. 70 366: the C1 case that failed the stroke-margin gate on the current controller
(run max 687.98 mm), re-run in the P-S8-28 acceptance (same definition as in ``g8c76``)."""


def g8c76_p28_acceptance_cases() -> list[BundleCCase]:
    """P-S8-28 acceptance set (spec rev. 70 366): C3 / C4 + the C1 FL g170 re-run. The C1 case
    is the very ``g8c76`` definition (one definition per id, :func:`case_table`); the sets
    ``g8c76`` / ``g8c76_p28`` stay as they were."""
    rerun = [c for c in g8c76_run_cases() if c.case_id in G8C76_P28_RERUN_IDS]
    return [*g8c76_def_cases(), *rerun]


G8_P28_SETS = ("g8c76_p28", "g8c76_p28acc")
"""Sets run with every case (no conditional filter); C3 / C4 still need --allow-p28-cases."""

CASE_SETS = {"bundleC": bundle_c_cases, "rerun32": rerun32_cases, "rerun33": rerun33_cases,
             "rerun34": rerun34_cases, "rerun35": rerun35_cases, "ps7r8": ps7r8_cases,
             "g8c76": g8c76_run_cases, "g8c76_p28": g8c76_def_cases,
             "g8c76_p28acc": g8c76_p28_acceptance_cases}
GROUP_SETS = {"rerun32": rerun32_groups, "rerun33": rerun33_groups, "rerun34": rerun34_groups,
              "rerun35": rerun35_groups}
ROLE_SETS = {"rerun34": RERUN34_ROLES, "rerun35": RERUN35_ROLES}


def case_table() -> dict[str, BundleCCase]:
    """Every case id of every set (a shared id has one definition, checked)."""
    table: dict[str, BundleCCase] = {}
    for make in CASE_SETS.values():
        for c in make():
            if c.case_id in table and table[c.case_id] != c:
                raise RuntimeError(f"case id {c.case_id} has two definitions")
            table[c.case_id] = c
    return table


# --- parameters ---------------------------------------------------------------------------


KN_KEY = "contact.rigid_floor.L1.kn_per_pad_N_m"
FRAME_KEY = "actuator.frame_stiffness_N_m"
C11_FRONT_LEGS = ("FL", "FR")
C11_FRAME_N_M = {"gate": 1.1e8, "record": 6.7e7}
"""Spec rev. 33 170 / user decision U-R8-19 (2026-10-24): front ``k_frame`` centre (gate) and
lower bound (record), ``00_docs/00_cad/cad_leg_support_and_closed_length.md`` 2.4 (1.11e8 /
6.69e7 N/m rounded as in the spec). ASSUMPTION: rear legs keep the YAML 1e9 N/m."""


def front_frame_overrides(kn_N_m: dict[str, float], k_frame_yaml_N_m: float,
                          k_frame_N_m: float) -> dict[str, float]:
    """C-11 pad stiffness of FL / FR: ``1/k' = 1/k - 1/k_frame,YAML + 1/k_frame`` (spec rev. 33
    170, cad 2.5) on the run's ``kn`` (YAML or the beta reference). The L1-R machine re-solves
    ``k_out`` from ``kn`` (``chrono/rod_chamber_link.leg_params_from_params``), so its LOCK
    stiffness ``(k_h + k_r) (+) k_out`` gets the same series term; ``k_h``, ``k_r``, ``c_n``,
    ``g_n`` stay (ASSUMPTION, spec 170: damping unchanged, zeta change recorded)."""
    out = {}
    for leg in C11_FRONT_LEGS:
        k = float(kn_N_m[leg])
        out[f"{KN_KEY}.{leg}"] = 1.0 / (1.0 / k - 1.0 / float(k_frame_yaml_N_m)
                                        + 1.0 / float(k_frame_N_m))
    return out


def param_overrides(case: BundleCCase, *, include_frame: bool = True,
                    include_beta: bool = True) -> dict[str, Any]:
    """Run-time YAML overrides of the case (module docstring); ``include_frame`` False leaves
    out the C-11 front frame term, ``include_beta`` False the beta terms (pad ``kn`` and the oil
    bulk modulus). The plant uses both; the controller neither
    (:func:`controller_param_overrides`)."""
    from outrigger_sim.params import load_params
    from outrigger_sim.verify.reference import BETA_K_L1_N_M, load_references

    over: dict[str, Any] = {}
    if include_beta and case.beta_GPa != 1.0:
        key = BETA_KEYS[case.beta_GPa]
        k = load_references().get(BETA_K_L1_N_M, beta=key)
        for leg, value in zip(LEGS, k, strict=True):
            over[f"{KN_KEY}.{leg}"] = float(value)
        over["actuator.oil_bulk_modulus_eff_Pa"] = float(key.removeprefix("beta_"))
    if case.L0r_m is not None:
        base = load_params(level=case.scenario.level)
        for leg in LEGS:
            col = float(base.get(f"actuator.rod_side.column_length_m.{leg}"))
            k_r = float(base.get(f"actuator.rod_side.k_rod_side_N_m.{leg}"))
            new_col = col - ROD_DEAD_LENGTH_YAML_M + case.L0r_m
            over[f"actuator.rod_side.column_length_m.{leg}"] = new_col
            over[f"actuator.rod_side.k_rod_side_N_m.{leg}"] = k_r * col / new_col
    if include_frame and case.front_frame_stiffness_N_m is not None:
        base = load_params(level=case.scenario.level, overrides=over or None)
        kn = {leg: float(v) for leg, v in base.get(KN_KEY).items()}
        over.update(front_frame_overrides(kn, float(base.get(FRAME_KEY)),
                                          case.front_frame_stiffness_N_m))
    return over


def _crawler_kt_ratio(params) -> float:
    """``(kt / kn)_pad`` mean of ``chrono/crawler_bushing.crawler_bushing_values``."""
    kn = params.get(KN_KEY)
    kt = params.get("contact.rigid_floor.L1.kt_per_pad_N_m")
    return sum(float(kt[k]) / float(kn[k]) for k in kn) / len(kn)


CONTROLLER_BETA_GPA = 1.0
"""C-R11 (spec rev. 34 176.3): the controller is built at the YAML beta for every case."""


def controller_param_overrides(case: BundleCCase) -> dict[str, Any]:
    """C-R11: overrides the controller sees = the case overrides without the beta and C-11
    frame terms (only ``L_0r`` remains; C2 reads no rod-side key, spec 176.1)."""
    return param_overrides(case, include_frame=False, include_beta=False)


def crawler_kt_scales(case: BundleCCase, params, params_noframe, params_nominal
                      ) -> dict[str, float]:
    """Crawler tangential bushing factors (``chrono/crawler_bushing`` derives ``kt`` from the
    mean pad ``kt/kn``, which the beta and C-11 overrides change through ``kn``):

    * ``frame`` = ratio(no frame) / ratio(run) (C-11, :func:`c11_meta`; 1 without C-11);
    * ``beta`` = ratio(beta 1.0, YAML) / ratio(no frame) (C-R11; exactly 1 at beta 1.0);
    * ``sensitivity`` = :attr:`BundleCCase.crawler_kt_factor` (spec rev. 35 186, 1 otherwise);
    * ``total`` = frame x beta x sensitivity, the ``crawler_bushing_kt_scale`` of the model.

    ``params_noframe`` = the run's parameters without the frame term, ``params_nominal`` = the
    controller's (beta 1.0, no frame)."""
    frame = (_crawler_kt_ratio(params_noframe) / _crawler_kt_ratio(params)
             if case.front_frame_stiffness_N_m is not None else 1.0)
    beta = (_crawler_kt_ratio(params_nominal) / _crawler_kt_ratio(params_noframe)
            if case.beta_GPa != CONTROLLER_BETA_GPA else 1.0)
    sens = float(case.crawler_kt_factor)
    total = frame * beta if sens == 1.0 else frame * beta * sens
    return {"frame": frame, "beta": beta, "sensitivity": sens, "total": total,
            "ratio_run": _crawler_kt_ratio(params),
            "ratio_beta_1.0": _crawler_kt_ratio(params_nominal)}


def c11_meta(case: BundleCCase, params, params_ctrl) -> dict[str, Any] | None:
    """C-11 record: per-leg ``kn``, the L1-R machine LOCK stiffness and ``k_out`` with and
    without the front frame term, the LOCK-basis zeta change with ``c_n`` fixed
    (``zeta' = zeta sqrt(k_lock / k_lock')``) and the crawler tangential compensation factor.
    ``params_ctrl`` here = the run's parameters without the frame term (beta kept; since C-R11
    the controller itself is built at beta 1.0, :func:`controller_param_overrides`)."""
    if case.front_frame_stiffness_N_m is None:
        return None
    from outrigger_sim.chrono.rod_chamber_link import leg_params_from_params

    def machine(p):
        legs, _rec = leg_params_from_params(p)
        return ([float(lp.pad_stiffness_head_only_N_m) for lp in legs],
                [float(lp.pad_stiffness_locked_N_m) for lp in legs],
                [float(lp.outer_stiffness_N_m) for lp in legs])

    kn0, kl0, ko0 = machine(params_ctrl)
    kn1, kl1, ko1 = machine(params)
    zeta = float(params.get("contact.rigid_floor.L1.derivation.damping_ratio"))
    return {
        "role": case.c11_role,
        "front_legs": list(C11_FRONT_LEGS),
        "front_frame_stiffness_N_m": case.front_frame_stiffness_N_m,
        "frame_stiffness_yaml_N_m": float(params.get(FRAME_KEY)),
        "formula": "1/k' = 1/k - 1/k_frame,YAML + 1/k_frame on kn_per_pad (FL, FR); L1-R k_out "
                   "re-solved from kn -> k_lock' = (k_h + k_r) (+) k_out' (spec rev. 33 170)",
        "override_keys": [f"{KN_KEY}.{leg}" for leg in C11_FRONT_LEGS],
        "kn_yaml_N_m": dict(zip(LEGS, kn0, strict=True)),
        "kn_override_N_m": dict(zip(LEGS, kn1, strict=True)),
        "k_lock_machine_N_m": {"without_frame_term": dict(zip(LEGS, kl0, strict=True)),
                               "with_frame_term": dict(zip(LEGS, kl1, strict=True))},
        "k_out_machine_N_m": {"without_frame_term": dict(zip(LEGS, ko0, strict=True)),
                              "with_frame_term": dict(zip(LEGS, ko1, strict=True))},
        "kn_change_rel": {leg: b / a - 1.0 for leg, a, b in zip(LEGS, kn0, kn1, strict=True)},
        "k_lock_change_rel": {leg: b / a - 1.0 for leg, a, b in zip(LEGS, kl0, kl1, strict=True)},
        "zeta_lock_basis": {leg: zeta * math.sqrt(a / b)
                            for leg, a, b in zip(LEGS, kl0, kl1, strict=True)},
        "zeta_note": "c_n / g_n unchanged (spec 170); one-DOF zeta on the LOCK stiffness, "
                     "relative to the run's beta (record only)",
        "controller_params": "built without the frame term (and, C-R11, without the beta "
                             "terms): geometry nominal_pad_stiffness_N_m, "
                             "support_pad_stiffness_N_m, probe_correction_sensitivity_N_m "
                             "at the YAML values",
        "crawler_kt_scale": _crawler_kt_ratio(params_ctrl) / _crawler_kt_ratio(params),
        "crawler_kt_note": "chrono/crawler_bushing derives the crawler kt from the mean pad "
                           "kt/kn; the scale holds the crawler kt / ct at the run's no-frame "
                           "values (the frame is not in the crawler path)",
    }


def leg_zeta_meta(case: BundleCCase, params) -> dict[str, Any]:
    """dyn rev. 37 5.24.1: one-DOF equivalent leg zeta with the YAML ``c_n`` kept (record)."""
    from outrigger_sim.verify.reference import BETA_K_L1_N_M, load_references
    from outrigger_sim.verify.s6_bundle_c import leg_zeta_effective

    zeta_nom = float(params.get("contact.rigid_floor.L1.derivation.damping_ratio"))
    refs = load_references()
    k_nom = [float(v) for v in refs.get(BETA_K_L1_N_M, beta=BETA_KEYS[1.0])]
    k_b = [float(v) for v in refs.get(BETA_K_L1_N_M, beta=BETA_KEYS[case.beta_GPa])]
    zeta = leg_zeta_effective(k_b, k_nom, zeta_nom)
    return {"beta_GPa": case.beta_GPa, "zeta_by_leg": dict(zip(LEGS, zeta, strict=True)),
            "nominal": case.beta_GPa == 1.0, "zeta_nominal": zeta_nom,
            "k_L1_N_m_beta": k_b, "k_L1_N_m_nominal": k_nom,
            "formula": "zeta_nom * sqrt(k_1.0 / k_beta), c_n fixed (dyn 5.24.1, record only)"}


class SaturationRecorder:
    """Per-step law-C saturation diagnostics (read only, dyn rev. 37 5.24.2).

    Per leg: first saturated time; per episode (consecutive saturated hooks) the direction, the
    peak judged force and the static end value = mean cylinder force the actuator judged over
    ``[t_end + 0.1, t_end + 0.5] s`` after the last saturated hook (ASSUMPTION of the definition;
    an episode is "interrupted" when the leg saturates again or the run ends first). Excess =
    static end - limit in the saturated direction (positive = beyond the limit)."""

    WINDOW_S = (0.1, 0.5)

    def __init__(self, model, t0: float) -> None:
        import numpy as np

        act = model.actuator
        self.act = act
        self.t0 = t0
        limits = act.force_limits_N
        n = act.n_legs
        self.f_ext = None if limits is None else np.broadcast_to(
            np.asarray(limits[0], float), (n,)).copy()
        self.f_ret = None if limits is None else np.broadcast_to(
            np.asarray(limits[1], float), (n,)).copy()
        self.prev = np.zeros(n, dtype=bool)
        self.first_t: list[float | None] = [None] * n
        self.cur: dict[int, dict[str, Any]] = {}
        self.open: list[dict[str, Any]] = []
        self.done: list[dict[str, Any]] = []

    def __call__(self, engine) -> None:
        sat = self.act.saturated
        if not (sat.any() or self.prev.any() or self.open):
            return
        t = float(engine.time_s)
        f = self.act.last_cylinder_force_N
        judged = self.act.last_judged_force_N
        for i in range(sat.size):
            if sat[i]:
                if self.first_t[i] is None:
                    self.first_t[i] = t - self.t0
                for ep in self.open:
                    if ep["leg_i"] == i:
                        ep["status"] = "interrupted (saturated again)"
                ep = self.cur.setdefault(i, {"leg_i": i, "leg": LEGS[i], "t_start_s": t - self.t0,
                                             "direction": "extend" if judged[i] > 0 else "retract",
                                             "steps": 0, "peak_judged_N": float(judged[i])})
                ep["steps"] += 1
                if abs(judged[i]) > abs(ep["peak_judged_N"]):
                    ep["peak_judged_N"] = float(judged[i])
            elif self.prev[i]:
                ep = self.cur.pop(i)
                ep.update(t_end_s=t - self.t0, _t_end=t, _sum=0.0, _n=0, status="open")
                self.open.append(ep)
        keep = []
        for ep in self.open:
            if ep["status"] != "open":
                self._close(ep)
                continue
            dt = t - ep["_t_end"]
            if dt >= self.WINDOW_S[0]:
                ep["_sum"] += float(f[ep["leg_i"]])
                ep["_n"] += 1
            if dt >= self.WINDOW_S[1]:
                ep["status"] = "complete"
                self._close(ep)
            else:
                keep.append(ep)
        self.open = keep
        self.prev = sat

    def _close(self, ep: dict[str, Any]) -> None:
        i = ep["leg_i"]
        static = ep["_sum"] / ep["_n"] if ep["_n"] and ep["status"] == "complete" else None
        ex = None
        if static is not None and self.f_ext is not None:
            ex = (static - self.f_ext[i] if ep["direction"] == "extend"
                  else -self.f_ret[i] - static)
        out = {k: v for k, v in ep.items() if not k.startswith("_")}
        out.update(static_end_N=static, static_excess_N=ex,
                   mechanism_share=None if ex is None
                   else bool(ex <= _SAT_SHARE_N))
        self.done.append(out)

    def meta(self) -> dict[str, Any]:
        for ep in self.open:
            ep["status"] = "interrupted (run ended)"
            self._close(ep)
        self.open = []
        for ep in self.cur.values():
            ep = dict(ep, status="saturated at run end")
            ep.update(_sum=0.0, _n=0)
            self._close(ep)
        self.cur = {}
        steps = self.act.saturation_step_count.tolist()
        return {"steps": dict(zip(LEGS, steps, strict=True)),
                "starts": dict(zip(LEGS, self.act.saturation_start_count.tolist(), strict=True)),
                "first_t_s": dict(zip(LEGS, self.first_t, strict=True)),
                "episodes": self.done,
                "static_window_s": list(self.WINDOW_S),
                "mechanism_share_limit_N": _SAT_SHARE_N,
                "rule": "static end - limit <= 0.25 kN = law-C mechanism share (dyn 5.24.2); "
                        "static window ASSUMPTION; t relative to the start state"}


def controller_config(params, case: BundleCCase):
    """``C2Config().with_10hz_d1()`` + the scenario settings of ``s6_stage2._controller`` +
    the R8 variant."""
    from outrigger_sim.control.c2 import C2Config, ContactJudge, IncrementLimit, TwistGainReference
    from outrigger_sim.control.target import AttitudeTarget, SlopeLimitMode, TargetAcceptance
    from outrigger_sim.control.zero_calibration import ZeroCalibrationMode
    from outrigger_sim.sensors.imu import imu_config_for_grade

    sc = case.scenario
    base = C2Config().with_10hz_d1()
    roll, pitch = (math.radians(a) for a in sc.target_deg)
    r8 = base.r8
    if case.increment == "sym0.1":
        r8 = replace(r8, increment_limit=IncrementLimit(0.1, 0.1))
    elif case.increment == "asym":
        r8 = replace(r8, increment_limit=IncrementLimit(fraction_per_period=0.1,
                                                        guard_fraction_per_period=0.25))
    elif case.increment != "sym0.25":
        raise ValueError(case.increment)
    if case.twist_reference == "k_nom":
        r8 = replace(r8, twist_gain_reference=TwistGainReference.NOMINAL)
    if case.fast_relevel:
        from outrigger_sim.control.c2 import FastRelevelSettings

        r8 = replace(r8, fast_relevel=FastRelevelSettings())
    if case.fast_relevel_horizon_periods is not None:
        from outrigger_sim.control.c2 import FastRelevelSettings

        fr = r8.fast_relevel or FastRelevelSettings()
        if "horizon_periods" not in getattr(fr, "__dataclass_fields__", {}):
            raise ValueError(f"{case.case_id}: FastRelevelSettings.horizon_periods missing "
                             "(P-R8-10 not installed)")
        r8 = replace(r8, fast_relevel=replace(fr, horizon_periods=
                                              int(case.fast_relevel_horizon_periods)))
    # sigma_g of one delivered gyro value = mean of the 10 IMU samples of a period
    gyro_sigma = float(imu_config_for_grade(sc.grade, sample_period_s=base.period_s)
                       .gyro_noise_std_rad_s)
    config = replace(
        base,
        zero_calibration=base.zero_calibration if sc.zero_calibration
        else replace(base.zero_calibration, mode=ZeroCalibrationMode.OFF),
        contact=ContactJudge(sc.contact),
        reanchor=replace(base.reanchor, enable=sc.h4),
        probe=base.probe if sc.combined_verdict is None
        else replace(base.probe, use_combined_verdict=sc.combined_verdict),
        target=replace(
            base.target,
            target=AttitudeTarget(roll_rad=roll, pitch_rad=pitch),
            slope_limit_mode=SlopeLimitMode.VERIFICATION,
            acceptance=TargetAcceptance(sc.acceptance),
            check_time_s=sc.check_time_s,
            crawler_settle_map=st._settle_map(sc.level),
            gyro_noise_std_rad_s=gyro_sigma,
        ),
        r8=r8,
    )
    return config


def l1_fallback_ratio(config, model, source: str | None = None):
    """U-S8-61 / spec 304 (1): the L1 / L1-R ``config`` with the R-5 fallback ratio source
    ``plant_meta`` and the ratio of the built plant (``k_r A_p / (k_h A_ann)`` of
    ``model.rod_chamber.leg_params``; :mod:`outrigger_sim.chrono.fallback_ratio`). Applied by
    :func:`job_bundle_c` after :func:`controller_config` (which the L2b paths of run_S7C /
    run_S8C share and keep at the preset ``column_nominal``). A config without R-5 or with
    the ``level`` slope is returned unchanged. Returns (config, meta).

    B(i): the meta has ``fallback_plant_ratio`` and ``fallback_plant_ratio_source`` (plant
    params, the ratio-relevant override keys, ``known_plant_ratio_upper`` when ``L_0h`` /
    ``L_0r`` are overridden). B(iii), comparison runs only: ``source`` (the single-run CLI
    ``--fallback-ratio-source``) or else the environment variable
    :data:`L1_FALLBACK_SOURCE_ENV` chooses ``plant_meta`` / ``column_nominal``; the meta
    records ``fallback_ratio_source_override`` = ``cli`` / ``env`` (None = default) and the env
    case prints a warning. Other values raise."""
    from outrigger_sim.chrono.fallback_ratio import (
        COLUMN_NOMINAL,
        L1_SOURCE_CHOICES,
        PLANT_META,
        env_override_value,
        plant_fallback_ratio_of_model,
        with_engine_fallback_ratio,
    )

    override = None
    wanted = PLANT_META
    if source is not None:
        override, wanted = "cli", str(source)
    else:
        env = env_override_value()
        if env is not None:
            override, wanted = "env", env
    if wanted not in L1_SOURCE_CHOICES:
        raise ValueError(f"L1 fallback ratio source {wanted!r} ({override}): expected one of "
                         f"{L1_SOURCE_CHOICES}")
    if override == "env":
        print(f"WARNING: {L1_FALLBACK_SOURCE_ENV}={wanted!r} overrides the L1 R-5 fallback ratio "
              "source (comparison run; recorded as fallback_ratio_source_override: env)",
              flush=True)
    override_meta = {"fallback_ratio_source_override": override,
                     "override_value": None if override is None else wanted,
                     "override_env_name": L1_FALLBACK_SOURCE_ENV if override == "env" else None}
    if wanted == COLUMN_NOMINAL:
        out, meta = with_engine_fallback_ratio(config, "L2b_NSC")  # preset kept
        return out, {**meta, "engine": "L1R", **override_meta,
                     "reason": "comparison override: L1 kept at the preset"}
    fr = getattr(getattr(config, "r8", None), "fast_relevel", None)
    ratio = (plant_fallback_ratio_of_model(model)
             if fr is not None and getattr(fr, "uses_fallback_slope", False) else None)
    out, meta = with_engine_fallback_ratio(config, "L1R", getattr(model, "params", None),
                                           plant_ratio=ratio)
    if ratio is not None:
        meta["ratio_origin"] = "model.rod_chamber.leg_params (plant)"
    return out, {**meta, **override_meta}


L1_FALLBACK_SOURCE_ENV = "OUTRIGGER_L1_FALLBACK_RATIO_SOURCE"
"""B(iii) comparison switch of :func:`l1_fallback_ratio` (unset = ``plant_meta``, U-S8-61); the
same name as ``outrigger_sim.chrono.fallback_ratio.L1_FALLBACK_SOURCE_ENV`` (unit test)."""


RERUN32_KEYS = {
    "P-R8-9": ("target", "check_quiet_after_motion_s"),
    "P-R8-10": ("r8.fast_relevel", "horizon_periods"),
    "P-R8-11": ("event", "probe_aborted_low_load"),
}
"""Spec rev. 32 163.1 names the re-run needs (placeholders until python-expert's final names
arrive from the main session): CHECK quiet time after the last leg motion, the R-5 prediction
horizon (and R-5 on by default in ``with_10hz_d1()``), the PROBE low-load abort event."""


def rerun32_readiness(config=None) -> dict[str, Any]:
    """Whether the installed ``control/c2.py`` has the P-R8-9 ... 11 items (spec names of
    :data:`RERUN32_KEYS`). ``config`` None = ``C2Config().with_10hz_d1()``."""
    import inspect

    from outrigger_sim.control import c2 as mod

    cfg = config or mod.C2Config().with_10hz_d1()
    target = cfg.target
    fr = cfg.r8.fast_relevel
    quiet = getattr(target, RERUN32_KEYS["P-R8-9"][1], None)
    horizon = None if fr is None else getattr(fr, RERUN32_KEYS["P-R8-10"][1], None)
    try:
        source = inspect.getsource(mod)
    except OSError:
        source = ""
    abort = RERUN32_KEYS["P-R8-11"][1] in source
    out = {"P-R8-9_check_quiet_after_motion_s": quiet,
           "P-R8-10_fast_relevel_on": fr is not None,
           "P-R8-10_horizon_periods": horizon,
           "P-R8-11_probe_abort_event_in_source": abort}
    out["rerun32_ready"] = bool(quiet is not None and fr is not None and horizon is not None
                                and abort)
    return out


RERUN33_KEYS = {
    "P-R8-12": ("r8.lifted_reapproach", "enable"),
    "P-R8-12_event": ("event", "leg_reapproach_start"),
}
"""Spec rev. 33 172.1 names (PLACEHOLDERS until the main session passes python-expert's final
names): ``C2Config().with_10hz_d1().r8.lifted_reapproach`` = ``LiftedReapproachSettings`` with
``enable`` True, and the event ``leg_reapproach_start:<leg>`` in ``control/c2.py``."""


def rerun33_readiness(config=None) -> dict[str, Any]:
    """Whether the installed ``control/c2.py`` has P-R8-12 (:data:`RERUN33_KEYS`) on in
    ``with_10hz_d1()``, plus the rerun32 items."""
    import inspect

    from outrigger_sim.control import c2 as mod

    cfg = config or mod.C2Config().with_10hz_d1()
    attr = RERUN33_KEYS["P-R8-12"][0].split(".", 1)[1]
    settings = getattr(cfg.r8, attr, None)
    enabled = None if settings is None else getattr(settings, RERUN33_KEYS["P-R8-12"][1], None)
    try:
        source = inspect.getsource(mod)
    except OSError:
        source = ""
    event = RERUN33_KEYS["P-R8-12_event"][1] in source
    out = {**rerun32_readiness(cfg),
           "P-R8-12_settings_type": None if settings is None else type(settings).__name__,
           "P-R8-12_enable": enabled,
           "P-R8-12_event_in_source": event,
           "rerun33_keys_are_placeholders": True}
    out["rerun33_ready"] = bool(out["rerun32_ready"] and enabled is True and event)
    return out


RERUN34_KEYS = {
    "P-R8-13_mode": ("r8.lifted_reapproach", "mode", "twist"),
    "P-R8-13_settings": ("samples", "single_leg", "exit_margin_N", "exit_samples",
                         "twist_speed_fraction", "protect_margin_N"),
    "P-R8-14": ("C2Controller", "command_components_m_s"),
}
"""Spec rev. 34 179.1 names (P-R8-13 ``LiftedReapproachSettings`` keys with ``mode`` "twist" on
in ``with_10hz_d1()``; P-R8-14 the per-period command components, :attr:`R8Series.COMPONENT_ATTR`).
Spec defaults (179.1): samples 1, single_leg True, exit_margin_N 5000, exit_samples 3,
twist_speed_fraction 0.25, protect_margin_N 5000 (reported, not required)."""
RERUN34_SPEC_DEFAULTS = {"samples": 1, "single_leg": True, "exit_margin_N": 5000.0,
                         "exit_samples": 3, "twist_speed_fraction": 0.25,
                         "protect_margin_N": 5000.0}


def rerun34_readiness(config=None) -> dict[str, Any]:
    """Whether the installed ``control/c2.py`` has P-R8-13 (twist-mode re-approach on in
    ``with_10hz_d1()``) and P-R8-14 (``command_components_m_s``), plus the rerun33 items except
    the P-R8-12 ``enable`` flag (P-R8-13 replaces P-R8-12; ``enable`` is still read)."""
    from outrigger_sim.control import c2 as mod

    cfg = config or mod.C2Config().with_10hz_d1()
    base = rerun33_readiness(cfg)
    settings = getattr(cfg.r8, "lifted_reapproach", None)
    _path, key, want = RERUN34_KEYS["P-R8-13_mode"]
    mode = None if settings is None else getattr(settings, key, None)
    values = {k: None if settings is None else getattr(settings, k, None)
              for k in RERUN34_KEYS["P-R8-13_settings"]}
    missing = [k for k, v in values.items() if v is None]
    import inspect

    attr = RERUN34_KEYS["P-R8-14"][1]
    try:
        source = inspect.getsource(mod.C2Controller)
    except OSError:
        source = ""
    # class attribute / property / method, or an instance attribute set in the class body
    has_components = hasattr(mod.C2Controller, attr) or f"self.{attr}" in source
    deviations = {k: v for k, v in values.items()
                  if v is not None and RERUN34_SPEC_DEFAULTS.get(k) is not None
                  and v != RERUN34_SPEC_DEFAULTS[k]}
    out = {**base,
           "P-R8-13_mode": mode,
           "P-R8-13_settings": values,
           "P-R8-13_missing_keys": missing,
           "P-R8-13_deviations_from_spec_defaults": deviations,
           "P-R8-14_command_components_attr": has_components,
           "rerun34_keys_are_spec_names": True}
    out["rerun34_ready"] = bool(base["rerun32_ready"] and base["P-R8-12_enable"] is True
                                and mode == want and not missing and has_components)
    return out


REV43_CONTROLLER_KEYS = ("touch_free_air_min_travel_m", "touch_free_air_min_samples",
                         "touch_free_air_cap_excess_N", "touch_hold_dip_samples",
                         "touch_seen_samples")
"""``R8Settings`` names recorded per case under ``bundle_c.rev43_controller`` (C-S8-73: the
same block as ``run_S8C.py``; ``touch_free_air_cap_excess_N`` = P-S8-26, None = no cap;
``touch_hold_dip_samples`` = P-S8-27)."""


def rev43_controller_meta(config) -> dict[str, Any]:
    """U-S8-9 (P-S8-5) / U-S8-11 (P-S8-6) / U-S8-73 (P-S8-26) TOUCH and re-approach settings of
    ``config`` (getattr rule: a name missing from the installed c2.py gives None)."""
    r8 = config.r8
    reapproach = getattr(r8, "lifted_reapproach", None)
    return {"reapproach_load_fraction_of_F_min":
            getattr(reapproach, "load_fraction_of_F_min", None),
            **{k: getattr(r8, k, None) for k in REV43_CONTROLLER_KEYS}}


def c2_implementation_status(c2) -> dict[str, Any]:
    """Which 149 P-R8 items the installed c2.py has (recorded per case; R-7 getattr rule)."""
    from outrigger_sim.control import c2 as mod

    r8 = c2.config.r8
    return {
        **rerun34_readiness(c2.config),
        "c2_revision_meta": c2.meta().get("revision"),
        "P-R8-1_pre_probe_stiffness_scale": getattr(r8, "pre_probe_stiffness_scale", None),
        "P-R8-1_expected": 1.2,
        "P-R8-3_measured_stiffness_scale_max": getattr(r8, "measured_stiffness_scale_max", None),
        "P-R8-6_computed_output_attr": hasattr(c2, "computed_output_m_s"),
        "module_file": str(Path(mod.__file__).resolve()),
    }


# --- R-7 per-period record ----------------------------------------------------------------


class R8Series:
    """Per control instant: valve state, amplifier output, controller command before the
    output delay (P-R8-6 ``computed_output_m_s``), the issued command, the stiffness scale in
    use / raw ratio and the grounded-leg count (P-R8-7, meta ``twist_gain_stiffness``
    ``scale_in_use`` / ``raw_ratio`` / ``grounded_leg_count``), guard activity and the delivered
    IMU 10 ms samples. Names missing from the installed controller give NaN (getattr rule).

    The meta is read again only when the probe history grows (the scale changes only per probe
    round, spec 144.3) or on the first instant, to keep the 10 Hz cost small."""

    COMPONENT_ATTR = "command_components_m_s"
    """C-R9 (spec rev. 33 172.2; spec rev. 34 179.1 P-R8-14 name): a controller attribute (or
    method) giving a mapping ``name -> 4 leg speeds`` of the period's computed command; names
    :data:`COMPONENTS`. Missing = NaN columns."""
    COMPONENTS = ("attitude", "heave", "twist", "guard", "reapproach")
    RAW_ATTRS = ("raw_output_m_s", "raw_u_m_s", "raw_u")
    """P-R8-15 (spec rev. 35 188.2, python-expert): the sum of the components before the speed
    scaling / increment limit. Read with getattr under these candidate names, or as the key
    ``raw_u`` of a mapping returned by ``computed_output_m_s``; missing = NaN."""
    LIMIT_ATTRS = ("output_limit_flags", "limit_flags", "command_limit_flags")
    """P-R8-15 limit marks (increment / scale), any mapping or sequence; stored as JSON text per
    period (also taken from the non-array keys of a ``computed_output_m_s`` mapping)."""

    def __init__(self, model, c2) -> None:
        self.model = model
        self.c2 = c2
        self.rows: dict[str, list[Any]] = {k: [] for k in (
            "t", "valve_u", "amp_u", "computed_u", "raw_u", "limit_flags", "issued_u",
            "scale_used", "scale_raw", "grounded_leg_count", "guard_active", "guard_u",
            "imu_samples", "imu_gyro_samples", "phase", "probed_leg", "touched",
            *(f"cmp_{n}_u" for n in self.COMPONENTS))}
        self.raw_source: str | None = None
        self.limit_source: str | None = None
        self.component_source: str | None = None
        self._tgs_key: int | None = None
        self._tgs: dict[str, Any] = {}
        self.denominator: Any = None

    def _stiffness(self) -> dict[str, Any]:
        key = len(self.c2.probe_history)
        if key != self._tgs_key:
            self._tgs = dict(self.c2.meta().get("twist_gain_stiffness") or {})
            self._tgs_key = key
            self.denominator = {k: self._tgs.get(k) for k in ("denominator", "denominator_N_m")}
        return self._tgs

    @staticmethod
    def _num(value) -> float:
        try:
            return math.nan if value is None else float(value)
        except (TypeError, ValueError):
            return math.nan

    def __call__(self, meas, command) -> None:
        import numpy as np

        act = self.model.actuator
        r = self.rows
        r["t"].append(meas.t_s)
        r["valve_u"].append(act.valve_state_m_s)
        r["amp_u"].append(act.amp_output_m_s)
        comp = getattr(self.c2, "computed_output_m_s", None)
        comp = comp() if callable(comp) else comp
        raw, flags = None, None
        if isinstance(comp, Mapping):  # P-R8-15 may return a record instead of the array
            detail = dict(comp)
            comp = detail.pop("computed_u", detail.pop("u", None))
            raw = detail.pop("raw_u", None)
            if raw is not None:
                self.raw_source = "computed_output_m_s['raw_u']"
            if detail:
                flags = detail
                self.limit_source = "computed_output_m_s (other keys)"
        if raw is None:
            for name in self.RAW_ATTRS:
                v = getattr(self.c2, name, None)
                v = v() if callable(v) else v
                if v is not None:
                    raw, self.raw_source = v, f"controller.{name}"
                    break
        if flags is None:
            for name in self.LIMIT_ATTRS:
                v = getattr(self.c2, name, None)
                v = v() if callable(v) else v
                if v is not None:
                    flags, self.limit_source = v, f"controller.{name}"
                    break
        r["computed_u"].append(np.full(4, np.nan) if comp is None else np.asarray(comp, float))
        r["raw_u"].append(np.full(4, np.nan) if raw is None else np.asarray(raw, float))
        r["limit_flags"].append("" if flags is None
                                else json.dumps(_plain(flags), default=str))
        r["issued_u"].append(np.asarray(command.leg_speed_m_s, float))
        tgs = self._stiffness()
        r["scale_used"].append(self._num(tgs.get("scale_in_use")))
        r["scale_raw"].append(self._num(tgs.get("raw_ratio")))
        r["grounded_leg_count"].append(self._num(tgs.get("grounded_leg_count")))
        state = getattr(self.c2, "_state", None)
        guard = getattr(state, "guard_m_s", None)
        r["guard_active"].append(guard is not None)
        r["guard_u"].append(np.full(4, np.nan) if guard is None else np.asarray(guard, float))
        # C-S8-72 (spec rev. 67 345.2 T-2): TOUCH latch per leg (controller _state.touched,
        # 1 / 0; NaN = not available)
        touched = getattr(state, "touched", None)
        r["touched"].append(np.full(4, np.nan) if touched is None
                            else np.asarray(touched, bool).astype(float))
        comps = getattr(self.c2, self.COMPONENT_ATTR, None)
        comps = comps() if callable(comps) else comps
        if isinstance(comps, dict):
            self.component_source = f"controller.{self.COMPONENT_ATTR}"
        else:
            comps = {}
        for n in self.COMPONENTS:
            v = comps.get(n)
            r[f"cmp_{n}_u"].append(np.full(4, np.nan) if v is None else np.asarray(v, float))
        samples = meas.imu_specific_force_samples_m_s2
        r["imu_samples"].append(np.full((10, 3), np.nan) if samples is None
                                else np.asarray(samples, float))
        # C-S8-31 (spec rev. 49 219.11): the delivered gyro 10 ms partial means of the same
        # IMU-rate intervals (body axes, rad/s) that C2 hands to the D1'' lever term
        gyro = getattr(meas, "imu_angular_rate_samples_rad_s", None)
        r["imu_gyro_samples"].append(np.full((10, 3), np.nan) if gyro is None
                                     else np.asarray(gyro, float))
        r["phase"].append(str(getattr(self.c2.phase, "value", self.c2.phase)))
        # (가) control 2026-10-26: the leg the probe moves after this call (record only)
        from outrigger_sim.chrono.run_rows import probed_leg_code

        r["probed_leg"].append(probed_leg_code(self.c2))

    def save(self, path: Path) -> dict[str, Any]:
        import numpy as np

        from outrigger_sim.chrono.run_rows import PROBED_LEG_NONE, PROBED_LEG_SOURCE

        arr = {k: np.asarray(v) for k, v in self.rows.items()
               if k not in ("phase", "limit_flags", "probed_leg")}
        arr["phase"] = np.asarray(self.rows["phase"], dtype="U16")
        arr["probed_leg"] = np.asarray(self.rows["probed_leg"], dtype=np.int8)
        arr["limit_flags"] = np.asarray(self.rows["limit_flags"], dtype=str)
        np.savez_compressed(path, **arr)
        return {"file": path.name, "samples": len(self.rows["t"]),
                "computed_u_available": bool(np.isfinite(arr["computed_u"]).any())
                if arr["computed_u"].size else False,
                "scale_used_available": bool(np.isfinite(arr["scale_used"]).any())
                if arr["scale_used"].size else False,
                "scale_raw_available": bool(np.isfinite(arr["scale_raw"]).any())
                if arr["scale_raw"].size else False,
                "raw_u_source": self.raw_source,
                "raw_u_available": bool(np.isfinite(arr["raw_u"]).any())
                if arr["raw_u"].size else False,
                "limit_flags_source": self.limit_source,
                "p_r8_15_names_searched": {"raw": list(self.RAW_ATTRS),
                                           "limits": list(self.LIMIT_ATTRS)},
                "stiffness_denominator": self.denominator,
                "guard_u": "controller _state.guard_m_s (twist-vector share of the F_min "
                           "guard, before the speed scaling / increment limit; NaN = no guard)",
                "command_components_source": self.component_source,
                "command_components_available": [
                    n for n in self.COMPONENTS if np.isfinite(arr[f"cmp_{n}_u"]).any()]
                if arr["t"].size else [],
                "warn_probe_stiffness_out_of_range": [
                    str(e) for e in self.c2.events
                    if "WARN_PROBE_STIFFNESS_OUT_OF_RANGE" in str(e)],
                "imu_gyro_samples": "C-S8-31: delivered gyro 10 ms partial means per period "
                                    "(periods x 10 x 3, rad/s, body axes, oldest first, the "
                                    "last ends at t); NaN = no IMU-rate samples",
                "imu_gyro_available": bool(np.isfinite(arr["imu_gyro_samples"]).any())
                if arr["imu_gyro_samples"].size else False,
                "probed_leg": f"(가): leg index 0..3 (FL, FR, RL, RR) the probe moves, "
                              f"{PROBED_LEG_NONE} = none (not PROBE / round not started); "
                              f"{PROBED_LEG_SOURCE}",
                "touched": "C-S8-72: controller _state.touched per leg (1 latched / 0; NaN = "
                           "not available), the TOUCH latch of spec rev. 67 345.2 T-2",
                "units": "m/s, -, m/s^2, rad/s (imu_gyro_samples); t absolute s"}


# --- job ----------------------------------------------------------------------------------


def check_settle_offset(case: BundleCCase, dt_s: float) -> None:
    """C-R7: ``settle_offset_s`` only on a ``settle_RR`` case, >= 0 and an integer multiple of
    ``dt_s`` (1e-9 relative)."""
    off = float(case.settle_offset_s)
    if off == 0.0:
        return
    if case.scenario.event != "settle_RR":
        raise ValueError(f"{case.case_id}: settle_offset_s only for settle_RR (G4)")
    n = off / dt_s
    if off < 0.0 or abs(n - round(n)) > 1e-6:
        raise ValueError(f"{case.case_id}: settle_offset_s {off} s is not a non-negative "
                         f"integer multiple of dt {dt_s} s")


G8_GAP_NAME = "crawler_gap.npz"


class CrawlerGapRecorder:
    """C-S8-76 (spec rev. 69 360.2): true crawler clearance = gap of EVERY crawler contact sphere
    above the base floor plane, ``n . (c_k - p0) - r`` (all 24 spheres of
    ``L1Model.crawler_layout``, the Chrono crawler collision shapes), every
    :data:`G8_RUN_STEP_EVERY` steps in the runner step hook (final state of the step).
    Arrays: ``t`` (absolute s), ``min_gap_m``, ``argmin`` (sphere index), ``gaps_m`` (n, 24)."""

    def __init__(self, model: Any, every_steps: int = G8_RUN_STEP_EVERY):
        import numpy as np

        from outrigger_sim.chrono.probes import chvec

        self.model = model
        self.every = int(every_steps)
        self.sup = model.superstructure
        self.locals = tuple(chvec(c) for c in model.crawler_centres_local_m)
        self.radius = float(model.crawler_layout.sphere_radius_m)
        n = np.asarray(model.bushing.normal_world(), float)
        self.n = n
        self.d0 = float(n @ np.asarray(model.floor_point_world_m, float))
        self._k = 0
        self.rows: dict[str, list] = {"t": [], "gaps_m": []}

    def gaps_m(self):
        import numpy as np

        nx, ny, nz = (float(c) for c in self.n)
        out = np.empty(len(self.locals))
        for i, c in enumerate(self.locals):
            p = self.sup.TransformPointLocalToParent(c)
            out[i] = p.x * nx + p.y * ny + p.z * nz - self.d0 - self.radius
        return out

    def __call__(self, engine: Any) -> None:
        del engine
        self._k += 1
        if self._k % self.every:
            return
        self.rows["t"].append(float(self.model.system.GetChTime()))
        self.rows["gaps_m"].append(self.gaps_m())

    def arrays(self) -> dict[str, Any]:
        import numpy as np

        g = np.asarray(self.rows["gaps_m"], float).reshape(-1, len(self.locals))
        return {"t": np.asarray(self.rows["t"], float), "gaps_m": g,
                "min_gap_m": g.min(axis=1) if g.size else np.zeros(0),
                "argmin": g.argmin(axis=1) if g.size else np.zeros(0, int)}

    def save(self, path: Path) -> dict[str, Any]:
        import numpy as np

        arr = self.arrays()
        np.savez_compressed(path, **arr)
        return {"file": path.name, "samples": int(arr["t"].size), "every_steps": self.every,
                "spheres": len(self.locals), "sphere_radius_m": self.radius,
                "rule": "n . (c_k - p0) - r over every crawler sphere, base floor plane"}


def g8_block_height(case: BundleCCase, params, base_params, states: Path, model_kw: dict
                    ) -> dict[str, Any]:
    """C-S8-76: block height ``h = g0 - g_start`` of ``case.pad_block``; g0 = the zero-stroke
    pad gap (``s6_stage2.pad_gaps_m``) on the restored start snapshot of a model without the
    block (same build arguments). Raises when g_start is not inside (0, g0)."""
    from outrigger_sim.record import load_snapshot
    from outrigger_sim.verify.s6_bundle_c import retag_snapshot

    leg, g_start = case.pad_block
    j = LEGS.index(leg)
    probe_model, _ = st.build_crawler_model(params, case.scenario.floor, attach=False, **model_kw)
    snap = load_snapshot(case.snapshot, params_sha256=base_params.sha256, directory=states)
    snap, _ = retag_snapshot(snap, params.sha256, name=case.snapshot)
    probe_model.restore(snap)
    g0 = st.pad_gaps_m(probe_model)
    s0 = [float(m.GetMotorPos()) for m in probe_model.motors]
    del probe_model
    h = float(g0[j]) - float(g_start)
    if not (0.0 < g_start < float(g0[j])):
        raise ValueError(f"{case.case_id}: g_start {g_start} m not inside (0, g0 {g0[j]} m)")
    return {"leg": leg, "g_start_target_m": float(g_start), "g0_m": [float(v) for v in g0],
            "h_m": h, "stroke_at_start_m": s0,
            "rule": "spec rev. 69 360.1: block height h = g0 - g_start, g0 = n . (c - p0) - r at "
                    "zero stroke on the restored settled crawler snapshot (s6_stage2.pad_gaps_m)"}


def _snapshot_dir(name: str, batch_states: Path | None) -> Path:
    if batch_states is not None and (batch_states / f"{name}.npz").exists():
        return batch_states
    return STATES


def job_bundle_c(case: BundleCCase, case_dir: Path, *, duration_s: float | None = None,
                 states_dir: Path | None = None, fallback_ratio_source: str | None = None):
    """Run one bundle-C case. Returns (summary, run_meta). ``fallback_ratio_source``: B(iii)
    single-run override of the L1 R-5 ratio source (:func:`l1_fallback_ratio`; None = the
    environment variable, else ``plant_meta``)."""
    import numpy as np

    from outrigger_sim.chrono.l1_engine import L1Engine
    from outrigger_sim.chrono.pad_record import PadRecorder
    from outrigger_sim.control.c2 import C2Controller, C2Phase
    from outrigger_sim.control.target import AttitudeTarget
    from outrigger_sim.params import load_params
    from outrigger_sim.record import load_snapshot, make_run_meta, save_record
    from outrigger_sim.runner import DtSchedule, run_closed_loop
    from outrigger_sim.sensors.hydraulic import LegSensorConfig
    from outrigger_sim.sensors.imu import imu_config_for_grade
    from outrigger_sim.sensors.suite import SensorSuite
    from outrigger_sim.verify.reference import load_references
    from outrigger_sim.verify.s6_bundle_c import (
        EXPECTED_SATURATION_WARNING,
        EXPECTED_WARNING_BETA_GPA,
        PAD_DAMPING_OVERRIDE,
        classify_warning,
        retag_snapshot,
    )

    sc = case.scenario
    states = _snapshot_dir(case.snapshot, states_dir)
    if not (states / f"{case.snapshot}.npz").exists():
        raise FileNotFoundError(f"{case.case_id}: snapshot {case.snapshot} missing: run `snaps`")
    base_params = load_params(level=sc.level)
    overrides = param_overrides(case)
    params = load_params(level=sc.level, overrides=overrides) if overrides else base_params
    # C-11: the crawler path sees the parameters without the frame term; C-R11: the controller
    # and the crawler path see beta 1.0 (spec rev. 34 176.3)
    noframe_overrides = param_overrides(case, include_frame=False)
    params_noframe = (params if noframe_overrides == overrides else
                      load_params(level=sc.level, overrides=noframe_overrides or None))
    ctrl_overrides = controller_param_overrides(case)
    params_ctrl = (params if ctrl_overrides == overrides else
                   params_noframe if ctrl_overrides == noframe_overrides else
                   load_params(level=sc.level, overrides=ctrl_overrides or None))
    c11 = c11_meta(case, params, params_noframe)
    kt_scales = crawler_kt_scales(case, params, params_noframe, params_ctrl)
    if c11 is not None and c11["crawler_kt_scale"] != kt_scales["frame"]:
        raise RuntimeError(f"{case.case_id}: C-11 crawler scale mismatch")
    model_kw = ({} if c11 is None and case.beta_GPa == CONTROLLER_BETA_GPA
                and case.crawler_kt_factor == 1.0
                else {"crawler_bushing_kt_scale": kt_scales["total"]})
    settles = sc.event in ("settle_RR", "settle_RR_30", "drop_RR_30", "drop_RR_30_probe")
    g8 = None
    if case.pad_block is not None:  # C-S8-76: block under one pad (spec rev. 69 360.1)
        if settles:
            raise ValueError(f"{case.case_id}: pad_block with a settlement event")
        g8 = g8_block_height(case, params, base_params, states, dict(model_kw))
        model_kw = {**model_kw, "pad_blocks": {g8["leg"]: g8["h_m"]}}
    model, _pose = st.build_crawler_model(params, sc.floor, attach=False,
                                          settlement_legs=("RR",) if settles else (),
                                          **model_kw)
    check_settle_offset(case, model.dt_s)
    snap = load_snapshot(case.snapshot, params_sha256=base_params.sha256, directory=states)
    # dyn rev. 37 5.24.3: refuse to re-tag a snapshot that is not "legs unloaded"
    snap, retag_check = retag_snapshot(snap, params.sha256, name=case.snapshot,
                                       preground_leg=case.preground_leg)  # C-S8-72
    retagged = retag_check["required"]
    model.actuator.configure_valve(tau_s=case.tau_v_s, amp_ramp=case.amp_ramp,
                                   amp_ramp_s=AMP_RAMP_S)
    t0 = model.restore(snap)
    gap_rec = None
    if g8 is not None:
        jb = LEGS.index(g8["leg"])
        gaps_blk = st.pad_gaps_m(model)
        g8["g_start_measured_m"] = float(gaps_blk[jb])
        g8["gaps_with_block_m"] = [float(v) for v in gaps_blk]
        g8["block"] = model.pad_blocks.meta()
        if abs(g8["g_start_measured_m"] - g8["g_start_target_m"]) > 1e-9 or not all(
                abs(gaps_blk[i] - g8["g0_m"][i]) < 1e-12 for i in range(4) if i != jb):
            raise RuntimeError(f"{case.case_id}: block geometry check failed {g8}")
        gap_rec = CrawlerGapRecorder(model)
        g8["crawler_gap_at_start_m"] = [float(v) for v in gap_rec.gaps_m()]
    sat_rec = SaturationRecorder(model, t0)
    engine = L1Engine(model, imu_method="chrono_point")
    if case.sensor_model:
        leg_sensors = st.leg_sensor_config_for(sc, t0)
    else:
        leg_sensors = LegSensorConfig()
    suite = SensorSuite(imu_config_for_grade(sc.grade, sample_period_s=IMU_SAMPLE_PERIOD_S),
                        leg_sensors, seed=sc.seed)
    config = controller_config(params_ctrl, case)
    # U-S8-61 (spec 304 1): L1 / L1-R runs take the R-5 fallback ratio from the plant meta
    config, fallback_ratio_meta = l1_fallback_ratio(config, model, fallback_ratio_source)
    c2 = C2Controller.from_params(params_ctrl, config)
    controller = c2
    pre, pre_info = None, None
    if sc.pre_extend_leg is not None:  # C-S8-72: PS-7b / 7c in-run pre-extension (stage 2)
        from outrigger_sim.sensors.hydraulic import (
            leg_annulus_areas_from_params,
            leg_head_areas_from_params,
        )

        gaps = st.pad_gaps_m(model)
        leg = sc.pre_extend_leg
        target = float(gaps[leg]) + sc.pre_extend_offset_mm * 1e-3
        pre = st.PreExtend(c2, leg=leg, target_m=target, speed_m_s=params.actuator.max_speed_m_s,
                           head_area_m2=leg_head_areas_from_params(params),
                           annulus_area_m2=leg_annulus_areas_from_params(params),
                           grounded_check=sc.pre_extend_offset_mm > 0.0)
        controller = pre
        pre_info = {"g0_m": gaps.tolist(), "leg": leg, "offset_mm": sc.pre_extend_offset_mm,
                    "target_m": target, "rule": "g0 = n . (c - p0) - r on the restored state "
                                                "(s6_stage2.PreExtend)"}
    dt_fine = float(params.get("simulation.dt_transition_s"))
    schedule = DtSchedule(model.dt_s, config.period_s) if sc.fine_dt else None
    pads = None
    if sc.pad_record:
        pads = (PadRecorder(engine, sample_s=1.0e-3) if sc.fine_dt
                else PadRecorder(engine, every_steps=5))
    settle_vel = st.SettleVelocityRecorder(model) if settles else None
    series = R8Series(model, c2)
    phases: list[tuple[float, str]] = []
    probe_intervals: list[dict[str, Any]] = []
    probe_margins: list[dict[str, Any]] = []
    stroke_hi = float(params.legs[0].extension_range_m[1])
    state = {"ready_t": None, "scheduled": False, "requested": None, "probe_t": None,
             "event_t": None, "fine_open_t": None, "rr_contact_since": None,
             "fine_capped": False, "rr_lifted_seen": False}

    def drop(t_start):
        model.settlement.schedule(t_start, depth_m=st.RE1B_DROP_DEPTH_M,
                                  ramp_s=st.RE1B_DROP_RAMP_S, dt_s=dt_fine)
        state["scheduled"] = True
        state["event_t"] = t_start

    def fine_window(t):
        if schedule is None:
            return
        ev = state["event_t"]
        if ev is not None and state["fine_open_t"] is None and not schedule.is_open \
                and t >= ev - st.FINE_PRE_S - 1e-9 and len(schedule.segments) == 1:
            schedule.open(t, dt_fine, reason="RR drop transition")
            state["fine_open_t"] = t
        if not schedule.is_open:
            return
        n_rr = float(engine.truth().F_contact_n_N[3])
        if n_rr > 0.0:
            if state["rr_contact_since"] is None:
                state["rr_contact_since"] = t
        else:
            state["rr_contact_since"] = None
            state["rr_lifted_seen"] = True
        since = state["rr_contact_since"]
        if (ev is not None and t >= ev + st.FINE_PRE_S and since is not None
                and t - since >= st.FINE_HOLD_S - 1e-9):
            schedule.close(t, reason="RR in contact for FINE_HOLD_S after the drop")
        elif t - state["fine_open_t"] >= st.FINE_MAX_S - 1e-9:
            schedule.close(t, reason="FINE_MAX_S cap (RR not back in contact)")
            state["fine_capped"] = True

    def observe(meas, command):
        series(meas, command)
        state["last_t"] = meas.t_s  # C-S8-72 end rule
        ph = c2.phase
        n_rounds = len(c2.probe_history)
        if not phases or phases[-1][1] != ph.value:
            if phases and phases[-1][1] == "probe" and probe_intervals:
                iv = probe_intervals[-1]
                iv.update(t_end_s=meas.t_s - t0, next_phase=ph.value,
                          rounds_completed=n_rounds - iv["rounds_at_start"])
                iv["interrupted_by_relevel"] = ph.value == "level" and iv["rounds_completed"] == 0
            if ph.value == "probe":
                probe_intervals.append({"t_start_s": meas.t_s - t0, "rounds_at_start": n_rounds})
                s_true = [float(mo.GetMotorPos()) for mo in model.motors]
                probe_margins.append({"t_s": meas.t_s - t0,
                                      "margin_m": [stroke_hi - v for v in s_true],
                                      "stroke_meas_m": [float(v) for v in meas.stroke_m]})
            phases.append((meas.t_s - t0, ph.value))
        if ph is C2Phase.READY and state["ready_t"] is None:
            state["ready_t"] = meas.t_s
        if g8 is not None:  # C-S8-76: state-based FAULT (also the unnamed stroke-end FAULT)
            if ph.value in ("fault", "fault_reground") and state.get("fault_t") is None:
                state["fault_t"] = meas.t_s  # first entry into a FAULT phase
            if ph.value == "fault" and state.get("fault_hold_t") is None:
                state["fault_hold_t"] = meas.t_s
            # U-S8-79 re-ground record (spec rev. 70 366): events since the last instant
            evs = c2.events
            k0 = state.get("ev_seen", 0)
            for e in list(evs)[k0:]:
                name = str(e.name)
                if name.startswith(G8_REGROUND_EVENT_PREFIXES):
                    state.setdefault("reground", []).append((float(e.t_s), name))
                    if name.startswith("fault_reground_start") and state.get("rg_start_t") is None:
                        state["rg_start_t"] = float(e.t_s)
                    if name.startswith(("fault_reground_end", "WARN_FAULT_REGROUND_ABORT")):
                        state["rg_end_t"] = float(e.t_s)
            state["ev_seen"] = len(evs)
        if ph is C2Phase.PROBE and state["probe_t"] is None:
            state["probe_t"] = meas.t_s
        if sc.event == "drop_RR_30_probe" and not state["scheduled"] \
                and state["probe_t"] is not None:
            drop(state["probe_t"] + st.RE1BP_DELAY_S)
        if sc.event == "drop_RR_30" and not state["scheduled"] and state["ready_t"] is not None:
            drop(state["ready_t"] + 5.0)
        fine_window(meas.t_s)
        if state["ready_t"] is None:
            return
        if sc.event == "settle_RR" and not state["scheduled"]:
            model.settlement.schedule(state["ready_t"] + 5.0 + case.settle_offset_s,
                                      dt_s=model.dt_s)
            state["scheduled"] = True
        if sc.event == "settle_RR_30" and not state["scheduled"]:
            model.settlement.schedule(state["ready_t"] + 5.0, depth_m=0.030, ramp_s=5.0,
                                      dt_s=model.dt_s)
            state["scheduled"] = True
        if (sc.event == "target_change" and state["requested"] is None
                and meas.t_s >= state["ready_t"] + 2.0):
            state["requested"] = str(c2.request_target(
                AttitudeTarget(roll_rad=0.0,
                               pitch_rad=math.radians(st.TARGET_CHANGE_PITCH_DEG))))

    c2_meta = st.c2_config_meta(config)
    expect = st.expected_reanchor(sc, c2_meta["reanchor_direction"])
    impl = c2_implementation_status(c2)
    bundle = {
        **case.to_meta(),
        "param_overrides": overrides,
        "controller_param_overrides": ctrl_overrides,
        "controller_params_beta_GPa": CONTROLLER_BETA_GPA,
        "fallback_ratio": fallback_ratio_meta,
        "crawler_kt_scale_beta": kt_scales["beta"],
        "beta_leak_fix": {
            "rule": "C-R11 (spec rev. 34 176.3): controller built without the beta / frame "
                    "overrides; crawler kt / ct held at the beta 1.0 (kt/kn)_pad ratio",
            "plant_beta_GPa": case.beta_GPa,
            "controller_nominal_pad_stiffness_N_m": float(c2.geometry.nominal_pad_stiffness_N_m),
            "controller_load_sensitivity_diag_N_m":
                [float(v) for v in c2.geometry.load_sensitivity_diag_N_m],
            "controller_oil_bulk_modulus_Pa": float(c2.geometry.oil_bulk_modulus_Pa),
            "plant_kn_per_pad_N_m": {k: float(v) for k, v in params.get(KN_KEY).items()},
            "crawler_kt_scale": kt_scales,
            "crawler_kt_N_m": None if model.crawler_bushing_values is None
            else float(model.crawler_bushing_values.kt_N_m),
            "crawler_ct_N_s_m": None if model.crawler_bushing_values is None
            else float(model.crawler_bushing_values.ct_N_s_m),
        },
        "c11": c11,
        "crawler_bushing": None if model.crawler_bushing_values is None
        else model.crawler_bushing_values.meta(),
        "params_sha256": params.sha256,
        "params_sha256_yaml": base_params.sha256,
        "snapshot_dir": str(states.relative_to(ROOT)).replace("\\", "/")
        if states.is_relative_to(ROOT) else str(states),
        "snapshot_retagged": retagged,
        "snapshot_retag_note": "legs unloaded crawler settle: beta / L_0r do not enter (R-6)"
        if retagged else None,
        "snapshot_retag_check": retag_check,
        "pad_damping_override": PAD_DAMPING_OVERRIDE,
        "leg_zeta_effective": leg_zeta_meta(case, params),
        "saturation_stop_s": model.actuator.saturation_stop_s,
        "expected_warnings": [EXPECTED_SATURATION_WARNING]
        if abs(case.beta_GPa - EXPECTED_WARNING_BETA_GPA) < 1e-9 else [],
        "valve": model.actuator.valve_meta(),
        "imu_sample_period_s": IMU_SAMPLE_PERIOD_S,
        "leg_sensors": "WIKA error model" if case.sensor_model else "ideal (LegSensorConfig())",
        "c2_implementation": impl,
        "rev43_controller": rev43_controller_meta(config),  # C-S8-73, as run_S8C bundle_c
        "controller_timing": c2.meta().get("timing"),
        "gyro_noise_std_rad_s_passed": config.target.gyro_noise_std_rad_s,
    }
    settings = {**asdict(sc), "snapshot": case.snapshot, "start_t_s": t0, **c2_meta,
                "reanchor_expected": expect, "bundle_c": bundle,
                "l1r": {**st._l1r_meta(),
                        "effective_mechanics": str(getattr(model.rod_chamber, "mechanics", None)),
                        "fallback": None, "m1": st.rod_side_m1_status(model)},
                "leg_sensors": leg_sensors.to_meta(), "controller_config": str(config),
                "gyro_bias_removal": "none (check_time_s 0, CHECK skipped)"
                if sc.check_time_s == 0.0 else "CHECK standstill"}
    run_meta = make_run_meta(params, engine.meta(), scenario=f"S6_bundleC_{case.case_id}",
                             scenario_settings=settings, sensors=suite.setup(),
                             reference_sha256=load_references().sha256_by_file())
    # C-S8-72: READY + end_after_ready_s end rule (fixed-length check runs keep their length)
    use_end_rule = case.end_after_ready_s is not None and duration_s is None

    def stop_now() -> bool:
        if g8 is not None and g8_fault_stop(state):  # C-S8-76 FAULT end (spec rev. 70 366)
            return True
        return (state["ready_t"] is not None and state.get("last_t") is not None
                and state["last_t"] >= state["ready_t"] + case.end_after_ready_s - 1e-9)

    wall0 = time.perf_counter()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")  # every occurrence (also after a dt change)
        res = run_closed_loop(engine, controller, suite, duration_s or case.duration_s,
                              run_meta=run_meta, on_control=observe, command_delay_periods=0,
                              command_offset_s=case.command_offset_s,
                              step_hook=st._chain_hooks(pads, settle_vel, sat_rec, gap_rec),
                              capture_every_steps=5 if pads and schedule is None else None,
                              dt_schedule=schedule,
                              capture_every_s=1.0e-3 if pads and schedule is not None else None,
                              placement=st.run_placement(),
                              **({"stop_when": stop_now} if use_end_rule else {}))
    wall = time.perf_counter() - wall0
    observed = []
    for w in caught:
        cls = classify_warning(str(w.message), w.category.__name__, case.beta_GPa)
        cls.update(filename=Path(str(w.filename)).name, lineno=w.lineno)
        observed.append(cls)
        if not cls["expected"]:
            print(f"{case.case_id}: unexpected warning {w.category.__name__}: {w.message}",
                  file=sys.stderr, flush=True)
    bundle["warnings"] = observed
    bundle["warnings_unexpected_count"] = sum(1 for w in observed if not w["expected"])
    bundle["saturation_steps"] = sat_rec.meta()
    save_record(res.record, case_dir / "record")
    if pads is not None:
        pads.save(case_dir / "pads.npz")
    if settle_vel is not None:
        settle_vel.save(case_dir / st.SETTLE_VELOCITY_NAME)
    series_info = series.save(case_dir / R8_SERIES_NAME)
    events = [str(e) for e in c2.events]
    probes = [[asdict(r) if hasattr(r, "__dataclass_fields__") else str(r) for r in rnd]
              for rnd in c2.probe_history]
    (case_dir / "probe_history.json").write_text(json.dumps(probes, indent=1, default=str),
                                                 "utf-8")
    (case_dir / "controller_events.json").write_text(json.dumps(events, indent=1), "utf-8")
    arr = res.record.arrays
    s_motor = np.asarray(arr["s_motor"])
    if g8 is not None:  # C-S8-76 end-state record (spec rev. 69 360.2)
        g8["crawler_gap"] = gap_rec.save(case_dir / G8_GAP_NAME)
        gaps_end = gap_rec.gaps_m()
        stroke_rod = np.asarray(engine.truth().stroke_true_m, float)
        est = np.asarray(c2.geometry.clearance_corners_m(stroke_rod), float)
        g8.update(
            crawler_gap_end_m={"min": float(gaps_end.min()), "argmin": int(gaps_end.argmin()),
                               "all": [float(v) for v in gaps_end]},
            controller_clearance_estimate_end_m={"corners": est.tolist(), "min": float(est.min()),
                                                 "from": "C2Geometry.clearance_corners_m("
                                                         "truth stroke_true_m) at the run end"},
            clearance_target_m=float(c2.config.thresholds.clearance_target_m),
            fault_first_t_s=None if state.get("fault_t") is None else state["fault_t"] - t0,
            fault_hold_t_s=None if state.get("fault_hold_t") is None
            else state["fault_hold_t"] - t0,
            fault_end_rule_s=G8_END_AFTER_FAULT_S,
            fault_end_rule={"after_fault_s": G8_END_AFTER_FAULT_S,
                            "after_reground_end_s": G8_END_AFTER_REGROUND_S,
                            "cap_after_fault_s": G8_FAULT_CAP_S,
                            "stopped_by_fault_rule": bool(g8_fault_stop(state)),
                            "rule": "spec rev. 70 366: max(FAULT + 10 s, fault_reground_end + "
                                    "5 s), cap FAULT + 25 s; FAULT = first fault / "
                                    "fault_reground phase"},
            fault_reground={
                "events": [[t - t0, n] for t, n in state.get("reground", [])],
                "start_t_s": None if state.get("rg_start_t") is None
                else state["rg_start_t"] - t0,
                "end_t_s": None if state.get("rg_end_t") is None else state["rg_end_t"] - t0,
                "phase_span_s": [[a, b] for a, b in _phase_spans(phases, "fault_reground")]},
            fault_event_names=[e for e in events if "FAULT" in e],
            s_ref_end_m=[float(v) for v in model.s_ref_m],
            fs_kN_plant=0.0, fs_kN_harness=G8C76_HARNESS_FS_KN,
            fs_note="L1-R has no seal friction (CLAUDE.md: F_s only in L2b); the spec 363 / "
                    "harness rows are F_s 4 kN")
    reanchor = c2.reanchor_outcome
    ctl_meta = c2.meta()
    # B(i) / B(iii): runner-added keys of r8.fast_relevel (ratio provenance, override)
    from outrigger_sim.chrono.fallback_ratio import add_to_controller_meta

    add_to_controller_meta(ctl_meta, fallback_ratio_meta)
    n_floor = model.bushing.normal_world()
    p_floor = np.asarray(model.floor_point_world_m, dtype=float)
    acceptance = {
        "target_code": None if c2.target_code is None else str(c2.target_code),
        "crawler_attitude_deg": None if c2.crawler_attitude_rad is None
        else [math.degrees(a) for a in c2.crawler_attitude_rad],
        "target_checks": [str(c) for c in c2.target_checks],
        "last_check": (ctl_meta.get("target", {}).get("checks") or [None])[-1],
        "floor_estimate_rad": ctl_meta.get("target", {}).get("floor_estimate_rad"),
        "floor_estimate_touch": ctl_meta.get("floor_estimate_touch"),
        "floor_true_deg": st.FLOORS[sc.floor],
        "slope_limit_mode": "verification",
    }
    nose_up_skips = sum(1 for e in events if "reanchor_skipped:nose_up" in e)
    reanchor_starts = sum(1 for e in events if "reanchor_started" in e)
    summary = {
        "case": case.case_id, "settings": settings, "phases": phases,
        "events_count": len(events), "acceptance": acceptance,
        "h4": {"enabled": sc.h4, "outcome": None if reanchor is None else str(reanchor),
               "expected": expect, "direction": ctl_meta.get("reanchor_direction"),
               "n_reanchor_skipped_nose_up": nose_up_skips,
               "n_reanchor_started": reanchor_starts},
        "c2": c2_meta,
        "stroke": {"max_m": s_motor.max(axis=0), "min_m": s_motor.min(axis=0),
                   "margin_to_end_m": stroke_hi - s_motor.max(axis=0)},
        "controller_meta": ctl_meta,
        "probe_start_stroke_margin": probe_margins,
        "probe_events": [e for e in events if "probe" in e],
        "probe_skipped": [e for e in events if "probe_skipped" in e],
        "floor_plane": {"normal_world": n_floor.tolist(), "offset_m": float(n_floor @ p_floor)},
        "zero_calibration_report": st.zero_calibration_report(
            arr, phases, t0, ctl_meta, events, params,
            start_s=None if pre is None or pre.handover_t is None else pre.handover_t - t0),
        # C-S8-72: PS-7b / 7c pre-extension, PS-7 end rule
        **({} if pre is None else {"pre_extend": {**pre_info, **{
            k: v for k, v in pre.meta().items() if k != "inner"}},
            "pre_extend_handover_t_s": None if pre.handover_t is None
            else pre.handover_t - t0}),
        **({} if case.end_after_ready_s is None else {"end_rule": {
            "after_ready_s": case.end_after_ready_s, "applied": use_end_rule,
            "stopped_early": bool(res.meta.get("stopped_early", False)),
            "end_t_s": float(engine.time_s) - t0,
            "upper_s": duration_s or case.duration_s,
            "timeout": bool(use_end_rule and not res.meta.get("stopped_early", False)),
            "rule": "C-S8-72 / spec 92: READY + 5 s, the case length only as the upper "
                    "bound"}}),
        **({} if g8 is None else {"g8": g8}),
        "ready_t_s": None if state["ready_t"] is None else state["ready_t"] - t0,
        "probe_intervals": probe_intervals,
        "first_probe_t_s": None if state["probe_t"] is None else state["probe_t"] - t0,
        "event_t_s": (None if state["event_t"] is None else state["event_t"] - t0)
        if sc.event in st.FINE_EXPECTED_S
        else (None if state["ready_t"] is None or sc.event in (None, "reject")
              else (state["ready_t"] + (2.0 if sc.event == "target_change" else 5.0)
                    + (case.settle_offset_s if sc.event == "settle_RR" else 0.0)) - t0),
        "fine_dt": None if schedule is None else {
            "dt_transition_s": dt_fine, "opened_t_s": None if state["fine_open_t"] is None
            else state["fine_open_t"] - t0, "capped": state["fine_capped"],
            "rr_lifted_seen_in_window": state["rr_lifted_seen"],
            "segments_abs_t": schedule.to_meta()},
        "seed": sc.seed, "target_request": state["requested"],
        "r8_series": series_info,
        "monitor": engine.step_monitor(),
        "runner": {**res.meta, "wall_s": wall, "n_steps": res.n_steps,
                   "n_control": res.n_control,
                   "us_per_step": wall / max(res.n_steps, 1) * 1e6},
    }
    engine.close()
    return summary, run_meta


def _plain(value):
    import numpy as np

    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return _plain(value.tolist())
    if isinstance(value, np.generic):
        return _plain(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def job_case(case, case_dir):
    """Batch job (module level for spawn)."""
    from outrigger_sim.batch import CaseResult

    s = case.settings
    c = case_table()[case.case_id]
    states = None if s.get("batch_states") is None else Path(s["batch_states"])
    summary, run_meta = job_bundle_c(c, Path(case_dir), duration_s=s.get("duration_s"),
                                     states_dir=states)
    (Path(case_dir) / "result.json").write_text(
        json.dumps(_plain(summary), indent=1, ensure_ascii=False), encoding="utf-8")
    return CaseResult(summary=_plain({k: summary[k] for k in ("case", "phases", "runner")}),
                      run_meta=run_meta)


def job_snapshot_case(case, case_dir):
    from outrigger_sim.batch import CaseResult

    s = case.settings
    summary = st.job_snapshot(s["level"], s["floor"], Path(case_dir), STATES)
    (Path(case_dir) / "result.json").write_text(
        json.dumps(_plain(summary), indent=1, ensure_ascii=False), encoding="utf-8")
    return CaseResult(summary=_plain({"snapshot": summary["snapshot"],
                                      "timing": summary["timing"]}), run_meta=None)


# --- actions ------------------------------------------------------------------------------


def plan(ids=None, case_set: str = "bundleC") -> dict[str, Any]:
    pool = CASE_SETS[case_set]() if ids is None else list(case_table().values())
    cases = [c for c in pool if ids is None or c.case_id in ids]
    rows = [{"case_id": c.case_id, "config": c.config, "snapshot": c.snapshot,
             "duration_s": c.duration_s, "fine_dt": c.fine_dt, "conditional": c.conditional,
             "wall_estimate_s": c.wall_estimate_s(),
             "blocked": c.blocked_in(STATES)} for c in cases]
    walls = [r["wall_estimate_s"] for r in rows]
    uncond = [r["wall_estimate_s"] for r in rows if not r["conditional"]]
    return {"cases": rows, "count": len(rows),
            "count_unconditional": sum(1 for r in rows if not r["conditional"]),
            "serial_wall_s": sum(walls),
            "makespan_7_s_all": st.lpt_makespan_s(sorted(walls, reverse=True), MAX_WORKERS),
            "makespan_7_s_unconditional": st.lpt_makespan_s(sorted(uncond, reverse=True),
                                                            MAX_WORKERS),
            "estimate_basis": "s6_stage2.Stage2Case.wall_estimate_s (stage-2 7-worker fit) on the "
                              "bundle-C run lengths"}


def build_snapshots(jobs: int):
    from outrigger_sim.batch import Case, run_cases

    todo = [(lv, f) for lv, f in (*NEW_SNAPSHOTS, *G8_SNAPSHOTS)
            if not (STATES / f"{st.snapshot_name(lv, f)}.npz").exists()]
    if not todo:
        print("all bundle-C snapshots exist")
        return None
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS / f"snapshots_bundleC_L1R_{stamp}"
    cases = [Case(st.snapshot_name(lv, f), {"level": lv, "floor": f}) for lv, f in todo]
    report = run_cases(cases, job_snapshot_case, out, max_workers=min(jobs, MAX_WORKERS),
                       placement="pcore", timeout_s=1800.0)
    for o in report.outcomes:
        print(f"{o.case_id}: {o.status} {o.wall_s:.1f}s" + ("" if o.status == "ok"
              else "\n" + (o.error or "")[-2000:]), flush=True)
    print(f"-> {out}")
    return report


def build_preground_snapshot(leg: str, *, overwrite: bool = False,
                             placement: str = "pcore") -> dict[str, Any]:
    """C-S8-72 (spec rev. 67 345.3): the PS-7a start snapshot of ``leg``
    (``s6_stage2.job_snapshot_preground``, the RRpre procedure with that leg) into
    :data:`STATES`, in this process (L1-R on); the build record goes to
    ``07_results/S6/snapshot_<leg>pre_L1R_<stamp>/result.json``."""
    from outrigger_sim.hostcpu import place_process

    placed = place_process(placement)
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS / f"snapshot_{leg}pre_L1R_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    summary = st.job_snapshot_preground(out, STATES, leg=leg, overwrite=overwrite)
    summary.update(placement=placed, wall_total_s=time.perf_counter() - t0,
                   env={k: os.environ.get(k) for k in ("OUTRIGGER_ROD_SIDE_MECHANICS",
                                                       "OPENBLAS_NUM_THREADS")})
    (out / "result.json").write_text(json.dumps(_plain(summary), indent=1, ensure_ascii=False),
                                     encoding="utf-8")
    print(json.dumps(_plain({k: summary[k] for k in ("snapshot", "leg", "t_reach_s", "t_end_s",
                                                     "stop", "wall_s")}), indent=1), flush=True)
    print(f"-> {out}", flush=True)
    return summary


def run_batch(ids, jobs: int, *, check: bool, check_duration_s: float = CHECK_DURATION_S,
              case_set: str = "bundleC", run_tag: str | None = None):
    from outrigger_sim.batch import Case, run_cases

    table = case_table()
    bad = [c for c in ids if c not in table]
    if bad:
        raise SystemExit(f"unknown cases: {bad}")
    blocked = [c for c in ids if table[c].blocked_in(STATES)]
    if blocked:
        raise SystemExit(f"cases without a start snapshot (run `snaps`): {blocked}")
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    tag = "bundleC" if case_set == "bundleC" else f"bundleC_{case_set}"
    if run_tag:  # C-S8-73: e.g. bundleC_ps7r8_c73_L1R_<stamp>
        tag = f"{tag}_{run_tag}"
    batch_dir = RESULTS / (f"{tag}_check_L1R_{stamp}" if check else f"{tag}_L1R_{stamp}")
    batch_dir.mkdir(parents=True, exist_ok=True)
    groups = ({g: [c.case_id for c in v] for g, v in GROUP_SETS[case_set]().items()}
              if case_set in GROUP_SETS else None)
    c11_roles = {c: table[c].c11_role for c in ids if table[c].c11_role is not None}
    roles = {c: r for c, r in ROLE_SETS.get(case_set, {}).items() if c in ids}
    meta = {"mode": "check" if check else "run", "case_set": case_set, "run_tag": run_tag,
            "groups": groups,
            "c11_roles": c11_roles or None, "roles": roles or None,
            "check_duration_s": check_duration_s if check
            else None, "cases": ids, "jobs": jobs,
            "c2_readiness": rerun34_readiness(),
            "env": {k: os.environ.get(k) for k in ("OUTRIGGER_ROD_SIDE_MECHANICS",
                                                    "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")},
            "plan": plan(set(ids))}
    (batch_dir / "batch_meta.json").write_text(json.dumps(_plain(meta), indent=1), "utf-8")
    order = sorted(ids, key=lambda c: -table[c].wall_estimate_s())  # longest first
    cases = [Case(c, {"duration_s": check_duration_s if check else None}) for c in order]
    t0 = time.perf_counter()
    report = run_cases(cases, job_case, batch_dir, max_workers=jobs, placement="pcore",
                       timeout_s=CHECK_TIMEOUT_S if check else CASE_TIMEOUT_S)
    wall = time.perf_counter() - t0
    for o in report.outcomes:
        msg = f"{o.case_id}: {o.status} {o.wall_s:.1f}s"
        if o.status != "ok":
            msg += "\n" + (o.error or "")[-2500:]
        print(msg, flush=True)
    print(f"batch wall {wall:.1f} s, jobs {jobs} -> {batch_dir}", flush=True)
    return report, batch_dir


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("list", "plan", "snaps", "snaps-pre", "check", "run",
                                       "judge", "judge-ps7", "judge-g8"))
    ap.add_argument("--leg", choices=st.PREGROUND_LEGS, default="FL",
                    help="snaps-pre (C-S8-72): leg of the pre-grounded PS-7a start snapshot")
    ap.add_argument("--overwrite", action="store_true",
                    help="snaps-pre: replace an existing snapshot of that leg")
    ap.add_argument("--placement", choices=("pcore", "ecore", "os"), default="pcore",
                    help="snaps-pre: CPU placement of the snapshot process")
    ap.add_argument("--touch-ref", dest="touch_ref",
                    help="judge-ps7: case folder of the TOUCH-length reference (T-1)")
    ap.add_argument("--jobs", type=int, default=MAX_WORKERS)
    ap.add_argument("--tag", default=None,
                    help="run / check: label added to the batch folder name (C-S8-73)")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--approved", action="store_true",
                    help="run: the user approved the bundle-C run (spec 150)")
    ap.add_argument("--with-c9", action="store_true", help="run: include the conditional C-9")
    ap.add_argument("--batch", help="judge: batch directory")
    ap.add_argument("--out", help="judge: output JSON (default <batch>/verify_S6C.json)")
    ap.add_argument("--consistency-ref", help="judge: JSON of the 142 C harness values")
    ap.add_argument("--duration", type=float, default=CHECK_DURATION_S,
                    help="check: simulated seconds per case (default 0.3)")
    ap.add_argument("--set", dest="case_set", choices=tuple(CASE_SETS), default="bundleC",
                    help="case set: bundleC (spec 150, 49), rerun32 (spec rev. 32 160, 26) or "
                         "rerun33 (spec rev. 33 169, 15), rerun34 (spec rev. 34 177, 16) or "
                         "rerun35 (spec rev. 35 185 / 186, 5)")
    ap.add_argument("--allow-incomplete-c2", action="store_true",
                    help="run --set rerun32 / rerun33: start even when the installed c2.py "
                         "lacks P-R8-9 ... 11 (RERUN32_KEYS) / P-R8-12 (RERUN33_KEYS)")
    ap.add_argument("--allow-p28-cases", action="store_true",
                    help="run: allow the C-S8-76 C3 / C4 cases (set g8c76_p28, P-S8-28 "
                         "acceptance; spec rev. 69 363)")
    ap.add_argument("--allow-env-override", action="store_true",
                    help="run / check: start even with OUTRIGGER_L1_FALLBACK_RATIO_SOURCE set "
                         "(B(iii) comparison batch; every L1 case takes the override)")
    args = ap.parse_args(argv)
    jobs = max(1, min(args.jobs, MAX_WORKERS))
    if args.action in ("run", "check"):
        from outrigger_sim.chrono.fallback_ratio import refuse_env_override

        refuse_env_override(args.allow_env_override, f"run_S6C {args.action}")
    if args.action == "list":
        groups = (GROUP_SETS[args.case_set]() if args.case_set in GROUP_SETS
                  else {"": CASE_SETS[args.case_set]()})
        for g, cases in groups.items():
            for c in cases:
                print(f"{g:1s} {c.case_id:48s} {c.config:5s} {c.snapshot:28s} "
                      f"{c.duration_s:6.1f} s"
                      + (f"  offset {c.settle_offset_s:g} s" if c.settle_offset_s else "")
                      + (f"  k_frame FL/FR {c.front_frame_stiffness_N_m:.2g} ({c.c11_role})"
                         if c.front_frame_stiffness_N_m is not None else "")
                      + (f"  crawler k_t x{c.crawler_kt_factor:g}"
                         if c.crawler_kt_factor != 1.0 else "")
                      + ("  (conditional)" if c.conditional else ""))
        return
    if args.action == "plan":
        doc = plan(set(args.only) if args.only else None, case_set=args.case_set)
        print(json.dumps(_plain({k: v for k, v in doc.items() if k != "cases"}), indent=1))
        return
    if args.action == "snaps":
        build_snapshots(jobs)
        return
    if args.action == "snaps-pre":  # C-S8-72: FLpre (spec rev. 67 345.3)
        build_preground_snapshot(args.leg, overwrite=args.overwrite, placement=args.placement)
        return
    if args.action == "judge-ps7":  # C-S8-72: 345.2 PS-7 D8 / TOUCH rows
        from outrigger_sim.verify.s6_control import judge_ps7_batch

        out = judge_ps7_batch(Path(args.batch), None if not args.out else Path(args.out),
                              touch_ref=None if not args.touch_ref else Path(args.touch_ref))
        print(f"-> {out}")
        return
    if args.action == "judge-g8":  # C-S8-76: spec rev. 69 360.2 rows
        from outrigger_sim.verify.s6_control import judge_g8_batch

        out = judge_g8_batch(Path(args.batch), None if not args.out else Path(args.out))
        print(f"-> {out}")
        return
    if args.action == "judge":
        from outrigger_sim.verify.s6_bundle_c import judge_batch

        out = judge_batch(Path(args.batch), consistency_ref=None if not args.consistency_ref
                          else Path(args.consistency_ref),
                          out_path=None if not args.out else Path(args.out))
        print(f"-> {out}")
        return
    set_ids = [c.case_id for c in CASE_SETS[args.case_set]()]
    if args.action == "check":
        ids = args.only or set_ids
        run_batch(ids, jobs, check=True, check_duration_s=args.duration, case_set=args.case_set,
                  run_tag=args.tag)
        return
    if not args.approved:
        raise SystemExit("bundle C needs the user's approval: add --approved (spec 150; "
                         "rerun32: user decision U-R8-16)")
    p28 = {c.case_id for c in g8c76_def_cases()}
    asked = set(args.only or set_ids)
    if asked & p28 and not args.allow_p28_cases:
        raise SystemExit(f"C-S8-76 C3 / C4 {sorted(asked & p28)} are P-S8-28 acceptance cases "
                         "(spec rev. 69 363): add --allow-p28-cases")
    if args.case_set in G8_P28_SETS:
        ids = args.only or set_ids
        run_batch(ids, jobs, check=False, case_set=args.case_set, run_tag=args.tag)
        return
    if args.case_set in ("rerun32", "rerun33", "rerun34", "rerun35"):
        ready = rerun34_readiness()
        # rerun35 needs the same controller as rerun34 (spec rev. 35 185: no c2 change required)
        key = "rerun34_ready" if args.case_set == "rerun35" else f"{args.case_set}_ready"
        need = {"rerun32": "P-R8-9 ... 11", "rerun33": "P-R8-9 ... 12",
                "rerun34": "P-R8-9 ... 14 (P-R8-13 twist mode, P-R8-14 components)",
                "rerun35": "P-R8-9 ... 14 (as rerun34)"}
        if not ready[key] and not args.allow_incomplete_c2:
            raise SystemExit(f"{args.case_set} needs {need[args.case_set]} in control/c2.py: "
                             f"{ready}")
        ids = args.only or set_ids
    else:
        table = case_table()
        ids = args.only or [c for c in set_ids if args.with_c9 or not table[c].conditional]
    run_batch(ids, jobs, check=False, case_set=args.case_set, run_tag=args.tag)


if __name__ == "__main__":
    main(sys.argv[1:])
