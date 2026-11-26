"""v5 acceptance runs on the reduced harness (spec ``v5_hydraulic_impl_spec.md`` 3.3).

Batches: ``main`` (required 72 rows x 15 settings + L2 8 rows + regression 28 rows x 4 = 1,200),
``smoke`` (V0 R12 phase 0, compared with the golden hash), ``w2`` (spec W-2: L1 and L2 on the 8
rows), ``item8`` (criteria 13.1 (1): R6 / R8 / R9 x V0, VB x eps 1e-3, 3e-3 = 12; the eps 0 and
2e-3 phases are the regression rows of ``main``), ``overlap`` (criteria 13.3 (③): R12 G4 at the
VB reference time t_a + 0 / 0.025 / 0.05 / 0.075 s x V0, V3, VB = 12; t_a comes from one VB base
run first, stored in ``overlap_t_a.json`` and used by every setting; lines carry
``overlap_found``), ``pressure_only`` (criteria 13.4 (⑥): R12 4 offsets + G4 width grid 28 x V0,
V4, V5 with the pressure-only judge = 96; lines carry ``contact_judge`` and ``unit_status``, the
event output ``lower_bound_miss``; the combined pairs are the same rows of ``main``),
``p3_hash`` (criteria revision 8 7.2: the first VB line per case of ``main.jsonl`` = 22 jobs
with the revision 8 VB definition, ③ on; ``p3_hash_check.py`` compares them with the stored
lines), ``d1`` (D-1 verification matrix, ``d1_rows.py`` / ``d1_runs.py``: 217 rows x VB / V0
x eps {0, 2e-3} = 868; ``--list`` also prints rows per group, missing settle-table keys and a
cost estimate; lines carry the ``d1`` record of ``d1_selection_rules.md`` 3), ``u9_targeted``
(U-9 targeted runs, ``u9_targeted_rules_rev1.md`` 2 / 3.2: 14 keys x V0, VB eta_v 0.85, VB eta_v
0.80 = 42; lines carry ``values["U9"]``), and the 436.9 batches ``j9_main``, ``j9_cases``,
``j9_case_f`` (case F, 15), ``j9_case_f_path`` (4a-3 5.2, 3) and ``j9_t8`` (T-JR-10 / 11,
88).
A job may carry ``eta_v`` (pump volumetric efficiency of a flow-limited setting, default
:data:`ETA_V`) and ``u9_metrics`` (add ``values["U9"]``), and a ``d1`` job ``mass_scale`` (plant
mass factor of a steady row, B1 H-W runs); jobs without them are as before.
One JSON line per run in ``06_analysis/03_hydraulic/coupled/v5/<batch>.jsonl`` (appended; runs
already in the file are skipped). Each run has its own spawned worker (``maxtasksperchild=1``): the
harness patches stay in the process. Deterministic (no noise). Values only; the verdict is
``v5_criteria.md``.

Usage (dynamics-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/run_v5.py <batch> [--workers N] [--mask HEX] [--list]
      [--out <jsonl>] [--settings A,B] [--one-per-setting] [--overlap-reference <t_a json>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import traceback
from dataclasses import replace
from multiprocessing import get_context
from pathlib import Path

for _name in ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_name, "1")
os.environ.setdefault("MKL_THREADING_LAYER", "TBB")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT_DIR = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5"
GOLDEN_DIR = OUT_DIR / "golden_off"
S9_DIR = ROOT / "04_scripts" / "03_control" / "s9"
M1_DIR = ROOT / "04_scripts" / "03_control" / "m1_check"
for _path in (HERE, S9_DIR, M1_DIR, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

ETA_V = 0.85
OVERLAP_RATIO, CLOSING_DELAY_S = 0.02, 0.05
EPS_ALL = (0.0, 1e-3, 2e-3, 3e-3)
EPS_TWO = (0.0, 2e-3)
OFFSETS = {"R12": (0.0, 0.025, 0.05, 0.075), "R14": (0.0, 0.05), "R15": (0.05, 0.0),
           "R16": (0.05, 0.0, 0.025, 0.075)}
"""``run_m1.OFFSETS`` (spec 3.3 rows)."""
G4_TWINS = ([("top", leg, fs) for leg in ("FL", "FR", "RL", "RR") for fs in (0.0, 4.0, 8.0)]
            + [("bottom", leg, 4.0) for leg in ("FL", "RR")])
G4_OFFSETS = (0.0, 0.05)
REQUIRED_STEADY_FOUR = ("S1", "S4", "S5", "S7", "S8", "R2", "R2ra", "R7")
REGRESSION_TWO = ("R1", "R5", "R6", "R8", "R9", "R10", "R11", "S3")
REGRESSION_FOUR = ("R3", "R4", "S2")
L2_ROWS = ("R12", "R14", "R16", "S1", "S7", "R2", "R7", "S8")
"""Spec 3.3 L2 (W-2): these rows at their first phase."""
REQUIRED_SETTINGS = ("V0", "V1", "V2", "V3", "L1", "VB", "V4", "V5", "V6", "V7", "V8",
                     "LS1", "LS2", "LS3", "LS4")
REGRESSION_SETTINGS = ("V0", "VB", "V4", "V5")
ITEM8_ROWS = ("R6", "R8", "R9")
"""Criteria 13.1 (1): item 8 rows top / middle / bottom (rpB, F_s 0)."""
ITEM8_EXTRA_EPS = (1e-3, 3e-3)
"""Criteria 13.1: the phases the regression batch (eps 0, 2e-3) does not run."""
ITEM8_SETTINGS = ("V0", "VB")
OVERLAP_CASE = "R12"
"""Criteria 13.3 (③): the R12 G4 event (RR 11.5 mm / 2 s, F_s 4, top)."""
OVERLAP_SETTINGS = ("V0", "V3", "VB")
OVERLAP_OFFSETS = (0.0, 0.025, 0.05, 0.075)
OVERLAP_REFERENCE_SETTING = "VB"
OVERLAP_TIMING = "flow_saturation"
OVERLAP_REFERENCE_PATH = OUT_DIR / "overlap_t_a.json"
"""t_a of the VB reference run, written before the 12 runs and read by every worker (one
absolute time for V0, V3 and VB)."""
OVERLAP_REFERENCE_ENV = "RUN_V5_OVERLAP_REFERENCE"
"""436.8 rules rev1 RV1-4: the t_a record of this run (``--overlap-reference``). The parent sets
it before the pool, so the spawned workers read the same file; unset = the stored
:data:`OVERLAP_REFERENCE_PATH`."""
PRESSURE_ONLY_SETTINGS = ("V0", "V4", "V5")
"""Criteria 13.4 (⑥): V0, M1c VN x1, M1c BL x1; the combined pairs are the same rows of
``main``."""
PRESSURE_ONLY_ROW_COUNT = 32
"""R12 4 phases + G4 width grid 28: the first rows of :func:`required_rows`."""
PRESSURE_ONLY_JUDGE = "PRESSURE"
UNIT_STATUS = "below_criteria_reference_only"
"""Criteria 13.4: every ⑥ table carries this (M1c below its unit criteria, reference only)."""


def _lc(ratio: float = OVERLAP_RATIO, delay_s: float = CLOSING_DELAY_S) -> dict:
    return {"overlap_ratio": ratio, "closing_delay_s": delay_s}


def _vn(scale: float) -> dict:
    return {"kind": "VN", "volume_scale": scale, "c_v": 0.02}


def _bl(scale: float) -> dict:
    return {"kind": "BL", "volume_scale": scale, "c_v": 0.02}


_M2 = {"rod_release_force": True}
_VB_PLANT = {**_M2, "lock_closure": _lc(), "lock_window_follows_plant": True}
_P3 = {"extend_start_tracked": True}
"""Criteria revision 8 3.1: the VB / LS controller ``final_C4G2_P3`` (③ start bound on)."""
SETTINGS: dict[str, tuple[bool, dict]] = {
    "V0": (False, {}),
    "V1": (False, _M2),
    "V2": (True, {}),
    "V3": (True, _M2),
    "L1": (False, {"lock_closure": _lc()}),
    "L2": (False, {"lock_closure": _lc(), "lock_window_follows_plant": True}),
    "VB": (True, {**_VB_PLANT, **_P3}),
    "V4": (True, {**_M2, "check_delay": _vn(1.0)}),
    "V5": (True, {**_M2, "check_delay": _bl(1.0)}),
    "V6": (True, {**_M2, "check_delay": _vn(0.5)}),
    "V7": (True, {**_M2, "check_delay": _bl(0.5)}),
    "V8": (True, {**_VB_PLANT, "check_delay": _vn(1.0)}),
    "LS1": (True, {**_VB_PLANT, "lock_closure": _lc(0.01, 0.05), **_P3}),
    "LS2": (True, {**_VB_PLANT, "lock_closure": _lc(0.05, 0.05), **_P3}),
    "LS3": (True, {**_VB_PLANT, "lock_closure": _lc(0.02, 0.02), **_P3}),
    "LS4": (True, {**_VB_PLANT, "lock_closure": _lc(0.02, 0.10), **_P3}),
}
"""Spec 3.3: (flow limit at eta_v 0.85, plant options as ``HydraulicOptions.to_dict`` keys).
Criteria revision 8: VB and LS1 .. LS4 run the controller with the ③ start bound
(``extend_start_tracked``); V0 .. V3, L1, L2 keep ``final_C4G2``; V4 .. V8 carry M1c, which
refuses the bound, so they keep it off."""

_P3H = {**_P3, "extend_start_hold": True}
"""436.9 (``jp3_remedy_spec.md`` 4.2): ③ revision 5, tag ``final_C4G2_P3H``."""
_P3W = {**_P3H, "extend_start_witness": True}
"""Edition 5 (``jp3_remedy_spec_v5.md`` 4.6, 6.2): ③ revision 6, tag ``final_C4G2_P3W``; the
436.9 settings that ran ③ revision 5 run it from edition 5 on."""
_PLANT_J = {"line_fill_gate": _vn(1.0), "lock_anchor_continuous": True,
            "rod_flow_cap_all": True, "rod_reading_truth": True}
"""P1 (VN, 1.0, 0.02) + P2 + P3 + P4."""
_VB_PLANT_J = {**_VB_PLANT, **_PLANT_J}
LS_CLOSURES = {"1": (0.01, 0.05), "2": (0.05, 0.05), "3": (0.02, 0.02), "4": (0.02, 0.10)}
"""LS1 .. LS4 lock closure (overlap ratio, closing delay)."""
JP3_SETTINGS: dict[str, tuple[bool, dict]] = {
    "VBH": (True, {**_VB_PLANT, **_P3W}),
    **{f"LSH{n}": (True, {**_VB_PLANT, "lock_closure": _lc(*closure), **_P3W})
       for n, closure in LS_CLOSURES.items()},
    "VBJ": (True, {**_VB_PLANT_J, **_P3W}),
    **{f"LSJ{n}": (True, {**_VB_PLANT_J, "lock_closure": _lc(*closure), **_P3W})
       for n, closure in LS_CLOSURES.items()},
    "VBJ0": (True, _VB_PLANT_J),
    "VBK": (True, {**_VB_PLANT_J, **_P3W}),
    "VBK0": (True, _VB_PLANT_J),
}
"""436.9 settings (spec 4.2), from edition 5 on with ③ revision 6 (``jp3_remedy_spec_v5.md``
6.2: VBH and VBJ of T-JR-12a run revision 6): VBJ / LSJ1 .. LSJ4 judged (P1 .. P4 + ③), VBJ0
the same plant with ③ off (T8, H-7 pair), VBH / LSH1 .. LSH4 the old VB / LS plant with ③
(controller effect alone, T8 on the old plant). Edition 5 6.3.1: VBK = the VBJ options and
VBK0 = the VBJ0 options, each with a rod sensor fault plan (``R79_ROD_FAULT_PLAN``, X-10).
:data:`SETTINGS` stays as it is (its names and digests are pinned); :data:`ALL_SETTINGS`
resolves both. The revision 5 options of edition 4a stay in :data:`JP3_REV5_SETTINGS`."""
JP3_REV5_SETTINGS: dict[str, tuple[bool, dict]] = {
    "VBH": (True, {**_VB_PLANT, **_P3H}),
    "VBJ": (True, {**_VB_PLANT_J, **_P3H}),
    "LSJ4": (True, {**_VB_PLANT_J, "lock_closure": _lc(*LS_CLOSURES["4"]), **_P3H}),
}
"""The edition 4a revision 5 options of VBH, VBJ and LSJ4 (no runnable setting of this list:
the X-10 bit-for-bit test runs VBJ under a test alias, and the X11 counterexample arm
``jp3_x11_replay.py`` builds ``LSJ4_X11`` on LSJ4 of revision 5, P4-5a as in edition 4a,
control review of 8a3c48c7 B-1)."""
LSB_COMPONENTS_SEALED = ("A_i", "A_ii", "B3")
"""Edition 6 sealed range (spec revision 6, Q6-14, user decision 2026-11-24): A(i), A(ii) and
B3; B1 is out (no activation in the 320 probe lines of 1bd405c8). The VBL family runs these; a
run's own list is its ``lsb_components``."""
_LSB = {"lsb_components": list(LSB_COMPONENTS_SEALED)}


def _gate(volume_scale: float, c_v: float) -> dict:
    return {"kind": "VN", "volume_scale": volume_scale, "c_v": c_v}


ED6_P1_SENSITIVITY: dict[str, dict] = {"c005": _gate(1.0, 0.005), "c04": _gate(1.0, 0.04),
                                       "v05": _gate(0.5, 0.02), "v15": _gate(1.5, 0.02)}
"""Spec 3.4 sensitivity rows: the VBJ plant with the P1 ``c_v`` 0.005 / 0.04 or the P1
``volume_scale`` 0.5 / 1.5 (one at a time; names ``VBL<key>``)."""


def ed6_plant(sensitivity: str | None = None) -> dict:
    """The VBJ plant (P1 .. P4 + LC), with the P1 gate of :data:`ED6_P1_SENSITIVITY` when
    ``sensitivity`` names one (None = the nominal P1)."""
    if sensitivity is None:
        return dict(_VB_PLANT_J)
    return {**_VB_PLANT_J, "line_fill_gate": dict(ED6_P1_SENSITIVITY[sensitivity])}


ED6_SETTINGS: dict[str, tuple[bool, dict]] = {
    "VBL": (True, {**ed6_plant(), **_P3W, **_LSB}),
    **{f"LSL{n}": (True, {**ed6_plant(), "lock_closure": _lc(*closure), **_P3W, **_LSB})
       for n, closure in LS_CLOSURES.items()},
    "VBL0": (True, {**ed6_plant(), **_LSB}),
    **{f"VBL{key}": (True, {**ed6_plant(key), **_P3W, **_LSB}) for key in ED6_P1_SENSITIVITY},
    "VBKL": (True, {**ed6_plant(), **_P3W, **_LSB}),
    "VBKL0": (True, {**ed6_plant(), **_LSB}),
}
"""Edition 6 settings (spec 3.4, user decision Q6-1 2026-11-23): VBL / LSL1 .. LSL4 = VBJ /
LSJ1 .. LSJ4 with the components (judged), VBL0 = VBJ0 with them (③ off, the T8 pair and the
12b reference arm), VBLc005 / VBLc04 / VBLv05 / VBLv15 the sensitivity rows, VBKL / VBKL0 =
VBK / VBK0 with them (rod fault plan, T-JR-12b). Every other setting keeps the components
off (P6-0)."""
ED6_JUDGED_SETTINGS = ("VBL", "LSL1", "LSL2", "LSL3", "LSL4")
ED6_SENSITIVITY_SETTINGS = tuple(f"VBL{key}" for key in ED6_P1_SENSITIVITY)

LSB_COMPONENTS_ED7 = ("A_i", "A_ib", "A_ii", "B3")
"""Edition 7 judged components (``jp3_remedy_spec_v7.md`` 3.6): the edition 6 sealed range plus
A(i)-b (condition 3 (다), latch and protection at their ``LockStartBSettings`` defaults)."""
PROBE_D6_ED7 = {"witness": True, "retract_position_target": True}
"""Edition 7 3.2 (meta ``probe_d6_settings``): the D6 E3 witness 0.3 mm and the (i-b) retract
position target at their ``ProbeD6Settings`` defaults."""
_LSB7 = {"lsb_components": list(LSB_COMPONENTS_ED7)}
_D67 = {"probe_d6_settings": dict(PROBE_D6_ED7)}
_P3X = {**_P3W, "extend_start_rev7": True}
"""③ rev 7 (base tag ``final_C4G2_P3X``)."""
ED7_P1_PATCH_NOMINAL = {"line_scale": 1.0, "dead_scale": 1.0, "bulk_modulus_Pa": 1.0e9,
                        "k_ext_form": "b0"}
ED7_SENSITIVITY: dict[str, tuple[dict, float]] = {
    "slow": ({"bulk_modulus_Pa": 0.69e9, "line_scale": 1.5, "dead_scale": 1.5}, 0.02),
    "fast": ({"bulk_modulus_Pa": 1.6e9, "line_scale": 0.5, "dead_scale": 0.5}, 0.02),
    "c005": ({}, 0.005),
    "c04": ({}, 0.04),
    "b069": ({"bulk_modulus_Pa": 0.69e9}, 0.02),
    "b16": ({"bulk_modulus_Pa": 1.6e9}, 0.02),
    "h05": ({"line_scale": 0.5}, 0.02),
    "h15": ({"line_scale": 1.5}, 0.02),
    "d05": ({"dead_scale": 0.5}, 0.02),
    "d15": ({"dead_scale": 1.5}, 0.02),
}
"""Spec 3.3 sensitivity (hydraulics H4, user decision): key -> (P1 supplement changes, P1
``c_v``); names ``VBM<key>``. Judged: slow, fast, c005, c04; recorded: the other six."""
ED7_SENSITIVITY_JUDGED = ("slow", "fast", "c005", "c04")


def ed7_plant(sensitivity: str | None = None) -> dict:
    """The VBJ plant (P1 .. P4 + LC) with the edition 7 P1 supplement (a)(c)(d), ``k_ext``
    b0; ``sensitivity`` = an :data:`ED7_SENSITIVITY` key (None = nominal)."""
    changes, c_v = ({}, 0.02) if sensitivity is None else ED7_SENSITIVITY[sensitivity]
    return {**_VB_PLANT_J, "line_fill_gate": _gate(1.0, c_v),
            "p1_patch": {**ED7_P1_PATCH_NOMINAL, **changes}}


_ED7_CONTROLLER = {**_P3X, **_LSB7, **_D67}
_ED7_CONTROLLER_P3_OFF = {**_LSB7, **_D67}
ED7_SETTINGS: dict[str, tuple[bool, dict]] = {
    "VBM": (True, {**ed7_plant(), **_ED7_CONTROLLER}),
    **{f"LSM{n}": (True, {**ed7_plant(), "lock_closure": _lc(*closure), **_ED7_CONTROLLER})
       for n, closure in LS_CLOSURES.items()},
    "VBM0": (True, {**ed7_plant(), **_ED7_CONTROLLER_P3_OFF}),
    **{f"VBM{key}": (True, {**ed7_plant(key), **_ED7_CONTROLLER}) for key in ED7_SENSITIVITY},
    "VBKM": (True, {**ed7_plant(), **_ED7_CONTROLLER}),
    "VBKM0": (True, {**ed7_plant(), **_ED7_CONTROLLER_P3_OFF}),
}
"""Edition 7 settings (spec 3.6, names Q7-C3): VBM / LSM1 .. LSM4 judged (VBJ / LSJ plant + P1
supplement, ③ rev 7, A_i + A_ib + A_ii + B3, D6 witness and probe retract target), VBM0 the
same with ③ off (T8, 12a reference arm), ``VBM<key>`` the ten sensitivity settings, VBKM /
VBKM0 = VBM / VBM0 with the rod fault plan (T-JR-12b). Every older setting keeps its options
(+ the record key ``stale_seed_release`` on the P1 plant; P7-0)."""
ED7_JUDGED_SETTINGS = ("VBM", "LSM1", "LSM2", "LSM3", "LSM4")
ED7_SENSITIVITY_SETTINGS = tuple(f"VBM{key}" for key in ED7_SENSITIVITY_JUDGED)
ED7_SENSITIVITY_RECORD_SETTINGS = tuple(f"VBM{key}" for key in ED7_SENSITIVITY
                                        if key not in ED7_SENSITIVITY_JUDGED)
PROBE_D6_ED8 = {"witness": True, "retract_position_target": False, "witness_mode": "record"}
"""Edition 8 3.1 / 3.2 (meta ``probe_d6_settings``): (i-b) off, the D6 witness as a record only
(R2: D6 judges as in edition 6, no witness event)."""
ED8_CONTROLLER_CHANGES = {"locked_drift_waiver": True, "psw_min_travel_m": 0.05e-3,
                          "short_run_exit_samples": 4, "short_run_s": 0.5,
                          "stiffness_warning_range": [0.8, 3.6]}
"""Edition 8 3.3, 3.4, 3.7, 3.8 (v5 option ``ed8_settings`` = ``c2.ED8_CONTROLLER_SETTINGS`` in
JSON form; a unit test keeps the two equal): PSW 0.05 mm, warning (0.8, 3.6), H3' 0.5 s / 4,
L-2 at its class limits."""
_ED8_CONTROLLER_P3_OFF = {**_LSB7, "probe_d6_settings": dict(PROBE_D6_ED8),
                          "ed8_settings": dict(ED8_CONTROLLER_CHANGES)}
_ED8_CONTROLLER = {**_P3X, **_ED8_CONTROLLER_P3_OFF}
ED8_SETTINGS: dict[str, tuple[bool, dict]] = {
    "VBN": (True, {**ed7_plant(), **_ED8_CONTROLLER}),
    **{f"LSN{n}": (True, {**ed7_plant(), "lock_closure": _lc(*closure), **_ED8_CONTROLLER})
       for n, closure in LS_CLOSURES.items()},
    "VBN0": (True, {**ed7_plant(), **_ED8_CONTROLLER_P3_OFF}),
    **{f"VBN{key}": (True, {**ed7_plant(key), **_ED8_CONTROLLER}) for key in ED7_SENSITIVITY},
    "VBKN": (True, {**ed7_plant(), **_ED8_CONTROLLER}),
    "VBKN0": (True, {**ed7_plant(), **_ED8_CONTROLLER_P3_OFF}),
}
"""Edition 8 settings (``jp3_remedy_spec_v8_rules.md`` 3.6): the VBM family plants with the
edition 8 controller (3.1 .. 3.8); VBN0 = VBN with ③ off (T8, 12a), ``VBN<key>`` the ten
sensitivity settings, VBKN / VBKN0 = VBN / VBN0 with the rod fault plan (12b). Every older
setting keeps its options (P8-0)."""
ED8_JUDGED_SETTINGS = ("VBN", "LSN1", "LSN2", "LSN3", "LSN4")
ED8_SENSITIVITY_SETTINGS = tuple(f"VBN{key}" for key in ED7_SENSITIVITY_JUDGED)
ED8_SENSITIVITY_RECORD_SETTINGS = tuple(f"VBN{key}" for key in ED7_SENSITIVITY
                                        if key not in ED7_SENSITIVITY_JUDGED)
ED8_SETTING_OF_ED7 = {"VBM": "VBN", **{f"LSM{n}": f"LSN{n}" for n in LS_CLOSURES},
                      "VBM0": "VBN0", **{f"VBM{key}": f"VBN{key}" for key in ED7_SENSITIVITY},
                      "VBKM": "VBKN", "VBKM0": "VBKN0"}
"""Spec v8 5.1 / 3.6 name map: the edition 7 setting -> the edition 8 setting of its plant."""
ROD_FAULT_SETTINGS = ("VBK", "VBK0", "VBKL", "VBKL0", "VBKM", "VBKM0", "VBKN", "VBKN0")
"""Edition 5 6.3.1: the settings that run with a rod fault plan (``r79_sensor_screen`` refuses
one without the other by this list, audit W15); edition 6 adds VBKL / VBKL0 (spec 3.4),
edition 7 VBKM / VBKM0 (spec v7 3.6), edition 8 VBKN / VBKN0 (spec v8 3.6)."""
ALL_SETTINGS: dict[str, tuple[bool, dict]] = {**SETTINGS, **JP3_SETTINGS, **ED6_SETTINGS,
                                              **ED7_SETTINGS, **ED8_SETTINGS}
JP3_JUDGED_SETTINGS = ("VBJ", "LSJ1", "LSJ2", "LSJ3", "LSJ4")
JP3_DIAG_SETTINGS = ("VBH", "LSH1", "LSH2", "LSH3", "LSH4", "VBJ0")


def _phase_jobs(case: str, *, two: bool = False) -> list[dict]:
    base = {"case": "R2", "decision": "reanchor_on"} if case == "R2ra" else {"case": case}
    if case in OFFSETS:
        return [{**base, "eps": 0.0, "offset_s": offset} for offset in OFFSETS[case]]
    return [{**base, "eps": eps} for eps in (EPS_TWO if two else EPS_ALL)]


def required_rows() -> list[dict]:
    rows = _phase_jobs("R12")
    rows += [{"case": "R12", "eps": 0.0, "offset_s": offset,
              "twin": {"level": level, "leg": leg, "fs_kN": fs}}
             for level, leg, fs in G4_TWINS for offset in G4_OFFSETS]
    for case in ("R14", "R15", "R16", *REQUIRED_STEADY_FOUR):
        rows += _phase_jobs(case)
    return rows


def regression_rows() -> list[dict]:
    rows = [job for case in REGRESSION_TWO for job in _phase_jobs(case, two=True)]
    return rows + [job for case in REGRESSION_FOUR for job in _phase_jobs(case)]


def l2_rows() -> list[dict]:
    return [_phase_jobs(case)[0] for case in L2_ROWS]


def pressure_only_rows() -> list[dict]:
    """Criteria 13.4 rows: R12 at its 4 offsets and the G4 width grid (28)."""
    rows = required_rows()[:PRESSURE_ONLY_ROW_COUNT]
    if any(row["case"] != "R12" for row in rows):
        raise RuntimeError("the first required rows are no longer the R12 / G4 rows")
    return rows


def batch_jobs(name: str) -> list[dict]:
    if name == "main":
        jobs = [{**row, "setting": s} for s in REQUIRED_SETTINGS for row in required_rows()]
        jobs += [{**row, "setting": "L2"} for row in l2_rows()]
        return jobs + [{**row, "setting": s} for s in REGRESSION_SETTINGS
                       for row in regression_rows()]
    if name == "smoke":
        return [{**_phase_jobs("R12")[0], "setting": "V0"}]
    if name == "w2":
        return [{**row, "setting": s} for s in ("L1", "L2") for row in l2_rows()]
    if name == "item8":
        return [{"case": case, "eps": eps, "setting": s}
                for s in ITEM8_SETTINGS for case in ITEM8_ROWS for eps in ITEM8_EXTRA_EPS]
    if name == "overlap":
        return [{"case": OVERLAP_CASE, "eps": 0.0, "offset_s": offset, "timing": OVERLAP_TIMING,
                 "setting": s} for s in OVERLAP_SETTINGS for offset in OVERLAP_OFFSETS]
    if name == "pressure_only":
        return [{**row, "contact": PRESSURE_ONLY_JUDGE, "setting": s}
                for s in PRESSURE_ONLY_SETTINGS for row in pressure_only_rows()]
    if name == P3_HASH_BATCH:
        return [job for _, job in p3_hash_jobs()]
    if name == D1_BATCH:
        import d1_rows

        return d1_rows.jobs()
    if name == U9_BATCH:
        return u9_targeted_jobs()
    if name == J9_MAIN_BATCH:
        return j9_main_jobs()
    if name == ED6_J9_MAIN_BATCH:
        return ed6_j9_main_jobs()
    if name == ED6_KEYS_BATCH:
        return ed6_key_jobs(J9_V0_SAMPLE_FILE[0])
    if name == J9_V0_SAMPLE_BATCH:
        return j9_v0_sample_jobs(J9_V0_SAMPLE_FILE[0])
    if name == J9_CASES_BATCH:
        return j9_case_jobs()
    if name == J9_CASE_F_BATCH:
        return j9_case_f_jobs()
    if name == J9_CASE_F_PATH_BATCH:
        return j9_case_f_path_jobs()
    if name == J9_T8_BATCH:
        return j9_t8_jobs(P3_HASH_SOURCE_OVERRIDE[0])
    if name == ED6_T8_BATCH:
        return ed6_t8_jobs(P3_HASH_SOURCE_OVERRIDE[0])
    if name == ED6_CASES_BATCH:
        return ed6_case_jobs()
    if name in ED7_BATCHES:
        return ed7_batch_jobs(name)
    if name in ED8_BATCHES:
        return ed8_batch_jobs(name)
    raise ValueError(f"unknown batch {name!r}")


ED7_J9_MAIN_BATCH = "ed7_j9_main"
"""Edition 7 j9_main (``jp3_remedy_spec_v7.md`` 6.2): the ``j9_main`` layout with VBM /
LSM1 .. LSM4 (VBM 100 + LSM 4 x 72 = 388 lines)."""
ED7_T8_BATCH = "ed7_t8"
"""Edition 7 T8 = P7-1: the 22 jobs of :func:`p3_hash_jobs` x VBM, VBM0 = 44 runs
(``--p3-hash-source`` = the stored ``main.jsonl``)."""
ED7_CASES_BATCH = "ed7_cases"
"""Edition 7 P7-2 case replay E and F (the ed6_cases rows) x VBM, LSM1 .. LSM4 = 10 runs."""
ED7_KEYS_BATCH = "ed7_keys"
"""Edition 7 key-file rows (``--jobs-file``, sealed edition 7 key files of
:data:`ED7_KEY_FILE_SHA256`; refused until the seal fills it)."""
ED7_BATCHES = (ED7_J9_MAIN_BATCH, ED7_T8_BATCH, ED7_CASES_BATCH, ED7_KEYS_BATCH)
ED7_KEY_FILE_SHA256: dict[str, str] = {
    "sens_keys_ed7.json": "be930b75a375877d07fc84fa98a9f8b0ee463f5b592319cfd6869fcc62a05b1b",
    "confirm_g1_grid171.json": "684054abb1ad05d8f82141f58eafdfa3c096edae1c05c9a4b9e8ae9ffe5b5dec",
}
"""Edition 7 sealed key files (name -> sha256; spec v7 5.1, revision 6: the files of
``ed7_design/keys_seal_b46bdf8f/``, made at b46bdf8f clean). ``ed7_keys`` refuses any other
file."""
ED7_KEYS_FILE: list[Path | None] = [None]


def ed7_batch_jobs(name: str) -> list[dict]:
    """The jobs of an edition 7 batch (:data:`ED7_BATCHES`)."""
    if name == ED7_J9_MAIN_BATCH:
        jobs = [{**row, "setting": s} for s in ED7_JUDGED_SETTINGS for row in required_rows()]
        return jobs + [{**row, "setting": "VBM"} for row in regression_rows()]
    if name == ED7_T8_BATCH:
        source = P3_HASH_SOURCE_OVERRIDE[0]
        jobs = p3_hash_jobs() if source is None else p3_hash_jobs(source)
        return [{**job, "setting": setting} for setting in ("VBM", "VBM0") for _, job in jobs]
    if name == ED7_CASES_BATCH:
        return [{**job, "setting": setting} for job in _case_rows_e_f()
                for setting in ED7_JUDGED_SETTINGS]
    return sealed_key_jobs(ED7_KEYS_FILE[0], ED7_KEY_FILE_SHA256, ED7_KEYS_BATCH)


ED8_T8_BATCH = "ed8_t8"
"""Edition 8 T8 = P8-1: the 22 jobs of :func:`p3_hash_jobs` x VBN, VBN0 = 44 runs."""
ED8_CASES_BATCH = "ed8_cases"
"""Edition 8 P8-2 case replay E and F x VBN, LSN1 .. LSN4 = 10 runs."""
ED8_KEYS_BATCH = "ed8_keys"
"""Edition 8 key-file rows (``--jobs-file``): the ``lines[*].job`` of a sealed edition 8 key
file of :data:`ED8_KEY_FILE_SHA256` (``census_keys_ed8.json`` 1043, ``heldout_g_ed8.json``
339 VBN); refused until C8 fills the table (spec v8 11.1, P8-10)."""
ED8_HELDOUT_V0_BATCH = "ed8_heldout_v0"
"""Edition 8 stage 5 (spec v8 7.3, 7.4): per held-out slot the V0 job of its condition and the
V0 job of its first A/A candidate (``aa_order[0]``), 678 runs."""
ED8_HELDOUT_AA_BATCHES = {"ed8_heldout_aa2": 1, "ed8_heldout_aa3": 2}
"""Edition 8 7.4: the V0 jobs of every slot's second / third A/A candidate (339 each; a slot
uses them only when the earlier candidate fell in the other layer)."""
ED8_BATCHES = (ED8_T8_BATCH, ED8_CASES_BATCH, ED8_KEYS_BATCH, ED8_HELDOUT_V0_BATCH,
               *ED8_HELDOUT_AA_BATCHES)
ED8_KEY_FILE_SHA256: dict[str, str] = {}
"""Edition 8 sealed key files (name -> sha256), filled by the run commit C8 (spec v8 11.1);
every edition 8 key batch refuses a file not in it."""
ED8_KEYS_FILE: list[Path | None] = [None]


def ed8_batch_jobs(name: str) -> list[dict]:
    """The jobs of an edition 8 batch (:data:`ED8_BATCHES`)."""
    if name == ED8_T8_BATCH:
        source = P3_HASH_SOURCE_OVERRIDE[0]
        jobs = p3_hash_jobs() if source is None else p3_hash_jobs(source)
        return [{**job, "setting": setting} for setting in ("VBN", "VBN0") for _, job in jobs]
    if name == ED8_CASES_BATCH:
        return [{**job, "setting": setting} for job in _case_rows_e_f()
                for setting in ED8_JUDGED_SETTINGS]
    if name == ED8_KEYS_BATCH:
        return sealed_key_jobs(ED8_KEYS_FILE[0], ED8_KEY_FILE_SHA256, ED8_KEYS_BATCH)
    return heldout_v0_jobs(ED8_KEYS_FILE[0], name)


def heldout_v0_jobs(path: Path | None, batch: str) -> list[dict]:
    """The V0 jobs of a sealed held-out key file for a stage 5 batch (slot order; the condition
    and the first A/A candidate for :data:`ED8_HELDOUT_V0_BATCH`, else the A/A candidate of
    :data:`ED8_HELDOUT_AA_BATCHES`).

    Raises:
        SystemExit: As :func:`sealed_key_jobs`, a file that is no held-out file, or a slot
            without that A/A candidate.
    """
    sealed_key_jobs(path, ED8_KEY_FILE_SHA256, batch)  # the name, sha256 and line checks
    document = json.loads(Path(path).read_bytes())
    lines = document["lines"]
    if not all("v0_pair" in line and "aa_order" in line for line in lines):
        raise SystemExit(f"--jobs-file {path} is no held-out key file")
    if batch == ED8_HELDOUT_V0_BATCH:
        jobs = []
        for line in lines:
            jobs.append(dict(line["v0_pair"]["job"]))
            jobs.append(dict(line["aa_order"][0]))
        return jobs
    index = ED8_HELDOUT_AA_BATCHES[batch]
    if any(len(line["aa_order"]) <= index for line in lines):
        raise SystemExit(f"--jobs-file {path}: a slot has no A/A candidate {index + 1}")
    return [dict(line["aa_order"][index]) for line in lines]


def _case_rows_e_f() -> list[dict]:
    case_e = {"case": "R12", "eps": 0.0, "offset_s": 0.0, "twin": dict(J9_CASE_TWIN)}
    case_f = {"case": "R12", "eps": 0.0, "offset_s": J9_CASE_F_OFFSET_S,
              "twin": dict(J9_CASE_F_TWIN)}
    return [case_e, case_f]


def sealed_key_jobs(path: Path | None, sealed: dict[str, str], batch: str) -> list[dict]:
    """The jobs of a sealed key file (``{"expected_lines": n, "lines": [{"job": ...}]}``).

    Raises:
        SystemExit: No file, a file whose name and sha256 are not in ``sealed``, an unknown
            setting, or another line count.
    """
    if path is None:
        raise SystemExit(f"{batch} needs --jobs-file")
    data = Path(path).read_bytes()
    expected = sealed.get(Path(path).name)
    if expected is None or hashlib.sha256(data).hexdigest() != expected:
        raise SystemExit(f"--jobs-file {path} is not a sealed {batch} key file")
    document = json.loads(data)
    jobs = [dict(line["job"]) for line in document["lines"]]
    unknown = sorted({job["setting"] for job in jobs} - set(ALL_SETTINGS))
    if unknown or len(jobs) != document["expected_lines"]:
        raise SystemExit(f"--jobs-file {path}: settings {unknown} / line count")
    return jobs


J9_MAIN_BATCH = "j9_main"
"""436.9 (``jp3_remedy_spec.md`` 7, H-10 main part): the required rows x VBJ, LSJ1 .. LSJ4 and
the regression rows x VBJ (the ``main`` layout with VB / LS replaced; V0 rows are reused)."""
J9_CASES_BATCH = "j9_cases"
"""436.9 case replay A, B, E (spec 5.3): R12 bottom-FL-Fs4 offset 0.0 x VB, LS1 .. LS4, VBH,
LSH1 .. LSH4, VBJ, LSJ1 .. LSJ4 (15 runs). C and D are test-only plants
(``jp3_case_replay.py``)."""
J9_CASE_TWIN = {"level": "bottom", "leg": "FL", "fs_kN": 4.0}
J9_CASE_SETTINGS = ("VB", "LS1", "LS2", "LS3", "LS4", "VBH", "LSH1", "LSH2", "LSH3", "LSH4",
                    *JP3_JUDGED_SETTINGS)


def j9_main_jobs() -> list[dict]:
    jobs = [{**row, "setting": s} for s in JP3_JUDGED_SETTINGS for row in required_rows()]
    return jobs + [{**row, "setting": "VBJ"} for row in regression_rows()]


ED6_J9_MAIN_BATCH = "ed6_j9_main"
"""Edition 6 j9_main (``jp3_remedy_spec_v6.md`` 4 step 7, 6.2): the ``j9_main`` layout with
VBJ / LSJ1 .. LSJ4 replaced by VBL / LSL1 .. LSL4 (VBL 100 + LSL 4 x 72 = 388 lines)."""
ED6_KEYS_BATCH = "ed6_keys"
"""Edition 6 sensitivity / confirmation rows (spec 6.2 / 6.3): the jobs of one sealed key file
(``--jobs-file``: ``sens_keys_v2.json``, ``confirm_a_keys_v2.json`` or
``confirm_b_grid192.json``, refused unless its sha256 is one of :data:`ED6_KEY_FILE_SHA256`)."""
ED6_KEY_FILE_SHA256 = {
    "sens_keys_v2.json": "70f4bb6d7afaa3f8b7ac3437db3ce5d2e4d9cca05e74b9a5c38f3b0269b77f74",
    "confirm_a_keys_v2.json": "75413549fa9a9127744df1bc4cc92f0e99ee5881e1542726bd5d4f7b09869721",
    "confirm_b_grid192.json": "4e80e69bd2233b994853ae3f60ed0749f2c39c7dbb6390bc012b016efa5cf85b",
}
"""Spec v6 6.2 / 6.3 (revision 14): the sealed key files."""


def ed6_j9_main_jobs() -> list[dict]:
    jobs = [{**row, "setting": s} for s in ED6_JUDGED_SETTINGS for row in required_rows()]
    return jobs + [{**row, "setting": "VBL"} for row in regression_rows()]


def ed6_key_jobs(path: Path | None) -> list[dict]:
    """The jobs of a sealed edition 6 key file (:data:`ED6_KEYS_BATCH`)."""
    if path is None:
        raise SystemExit(f"{ED6_KEYS_BATCH} needs --jobs-file")
    data = Path(path).read_bytes()
    expected = ED6_KEY_FILE_SHA256.get(Path(path).name)
    if expected is None or hashlib.sha256(data).hexdigest() != expected:
        raise SystemExit(f"--jobs-file {path} is not a sealed edition 6 key file")
    lines = json.loads(data)["lines"]
    jobs = [dict(line["job"]) for line in lines]
    unknown = sorted({job["setting"] for job in jobs} - set(ALL_SETTINGS))
    if unknown or len(jobs) != json.loads(data)["expected_lines"]:
        raise SystemExit(f"--jobs-file {path}: settings {unknown} / line count")
    return jobs


J9_V0_SAMPLE_BATCH = "j9_v0_sample"
"""436.9 edition 5 erratum 2 2-7.1: the fixed V0 sample of the j9_main reference (``--jobs-file``,
each job a V0 job of the ``main`` batch), run again to compare its command hashes with the
stored V0 lines (``jp3_j9main_judge.py v0-sample``)."""
J9_V0_SAMPLE_FILE: list[Path | None] = [None]


def j9_v0_sample_jobs(path: Path | None) -> list[dict]:
    """The jobs of the V0 sample key file (JSON list or ``{"jobs": [...]}``).

    Raises:
        SystemExit: No file, or a job that is not a V0 job of the ``main`` batch.
    """
    if path is None:
        raise SystemExit(f"{J9_V0_SAMPLE_BATCH} needs --jobs-file")
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    jobs = document["jobs"] if isinstance(document, dict) else document
    main_keys = {job_key(job) for job in batch_jobs("main") if job["setting"] == "V0"}
    outside = [job for job in jobs if job_key(job) not in main_keys]
    if not jobs or outside:
        raise SystemExit(f"--jobs-file {path}: {len(outside)} jobs are no V0 job of the main "
                         f"batch (of {len(jobs)})")
    return [dict(job) for job in jobs]


def j9_case_jobs() -> list[dict]:
    row = {"case": "R12", "eps": 0.0, "offset_s": 0.0, "twin": dict(J9_CASE_TWIN)}
    return [{**row, "setting": setting} for setting in J9_CASE_SETTINGS]


J9_CASE_F_BATCH = "j9_case_f"
"""436.9 case F (``jp3_remedy_spec.md`` 13.8, J4a-14; addendum 4a-2 R8): the ``grid_r67_top``
FR row (``r67_g1_screen`` key ``screen|top|8.0|ready|FR``, its G4 branch at offset 0.075 s,
stored as ``results[13].runs[3]``) on the event path of ``verdict_runs`` (the P4 install path)
x A (VB, LS1 .. LS4), B (VBH, LSH1 .. LSH4), E (VBJ, LSJ1 .. LSJ4) = 15 runs. The R12 case is
the G4 event of the screen (ready + 5 s, branch 0.5 s before), with the twin replaced by this
row. ``jp3_case_judge.py case-f`` judges F-A / F-B / F-E."""
J9_CASE_F_TWIN = {"level": "top", "leg": "FR", "fs_kN": 8.0}
J9_CASE_F_OFFSET_S = 0.075
J9_CASE_F_GROUPS = {"A": ("VB", "LS1", "LS2", "LS3", "LS4"),
                    "B": ("VBH", "LSH1", "LSH2", "LSH3", "LSH4"),
                    "E": JP3_JUDGED_SETTINGS}


def j9_case_f_jobs() -> list[dict]:
    row = {"case": "R12", "eps": 0.0, "offset_s": J9_CASE_F_OFFSET_S,
           "twin": dict(J9_CASE_F_TWIN)}
    return [{**row, "setting": setting} for settings in J9_CASE_F_GROUPS.values()
            for setting in settings]


J9_CASE_F_PATH_BATCH = "j9_case_f_path"
"""Addendum 4a-3 5.2 (F-A path equivalence, before case F): the same FR row at the other three
G4 offsets of the stored grid (``results[13].runs[0..2]``: 0.0, 0.025, 0.05 s) x VB on the
case F event path; ``jp3_case_judge.py case-f-path`` compares them with the stored runs. The
judged offset 0.075 s (``runs[3]``) is not in this batch."""
J9_CASE_F_PATH_OFFSETS_S = (0.0, 0.025, 0.05)


def j9_case_f_path_jobs() -> list[dict]:
    return [{"case": "R12", "eps": 0.0, "offset_s": offset, "twin": dict(J9_CASE_F_TWIN),
             "setting": "VB"} for offset in J9_CASE_F_PATH_OFFSETS_S]


J9_T8_BATCH = "j9_t8"
"""436.9 T-JR-10 / T-JR-11 (spec 5.5, addendum 4a-3 2 and 5.3): the 22 jobs of the revision 8
7.2 hash rule (:func:`p3_hash_jobs`, the first VB line per case of the stored ``main.jsonl``;
they replace the T-P3-5 20 rows, which have no list) x VBH, VBJ, VBJ0, VB = 88 runs. T-JR-10
compares VBH with the stored h10 VB lines of the same jobs, T-JR-11 VBJ with VBJ0
(``jp3_tjr_judge.py t8``); the VB lines are a record (the current code against the stored
hash). ``--p3-hash-source`` names the stored ``main.jsonl`` (a worktree has none)."""
J9_T8_SETTINGS = ("VBH", "VBJ", "VBJ0", "VB")


def j9_t8_jobs(source: Path | None = None) -> list[dict]:
    """The :data:`J9_T8_BATCH` jobs (``source`` = the stored ``main.jsonl``, None = default)."""
    jobs = p3_hash_jobs() if source is None else p3_hash_jobs(source)
    return [{**job, "setting": setting} for setting in J9_T8_SETTINGS for _, job in jobs]


ED6_T8_BATCH = "ed6_t8"
"""Edition 6 T8 = P6-1 (``jp3_remedy_spec_v6_erratum2.md`` 2-1 (ii)): the 22 jobs of
:func:`p3_hash_jobs` x VBL, VBL0 = 44 runs (``--p3-hash-source`` = the stored ``main.jsonl``);
``jp3_ed6_judge.py t8`` compares each VBL line with its VBL0 line."""
ED6_T8_SETTINGS = ("VBL", "VBL0")
ED6_CASES_BATCH = "ed6_cases"
"""Edition 6 P6-2 (erratum 2 2-1 (iii)): case E (R12 bottom-FL-Fs4 offset 0.0, the j9_cases row)
and case F (the j9_case_f FR row) x VBL, LSL1 .. LSL4 = 10 runs, all on the event path
(``jp3_ed6_judge.py cases``)."""


def ed6_t8_jobs(source: Path | None = None) -> list[dict]:
    """The :data:`ED6_T8_BATCH` jobs (``source`` = the stored ``main.jsonl``, None = default)."""
    jobs = p3_hash_jobs() if source is None else p3_hash_jobs(source)
    return [{**job, "setting": setting} for setting in ED6_T8_SETTINGS for _, job in jobs]


def ed6_case_jobs() -> list[dict]:
    case_e = {"case": "R12", "eps": 0.0, "offset_s": 0.0, "twin": dict(J9_CASE_TWIN)}
    case_f = {"case": "R12", "eps": 0.0, "offset_s": J9_CASE_F_OFFSET_S,
              "twin": dict(J9_CASE_F_TWIN)}
    return [{**row, "setting": setting} for row in (case_e, case_f)
            for setting in ED6_JUDGED_SETTINGS]


U9_BATCH = "u9_targeted"
U9_PHASES = {"S2": EPS_ALL, "S3": EPS_TWO, "R3": EPS_ALL, "S5": EPS_ALL}
"""``u9_targeted_rules_rev1.md`` 2: groups A (S2, S3), B (R3) and C (S5) with their eps."""
U9_SETTINGS = ({"setting": "V0"}, {"setting": "VB", "eta_v": 0.85},
               {"setting": "VB", "eta_v": 0.80})
"""Rules 2 / 3.2 P-2: the J pair, the VB reference and VB with the supply cut to eta_v 0.80."""


def u9_targeted_jobs() -> list[dict]:
    """Rules 3.2 P-2: 14 (case, eps) keys x :data:`U9_SETTINGS` = 42 jobs, all with
    ``u9_metrics`` (the metric is empty on the flow-off V0 runs)."""
    return [{"case": case, "eps": eps, **setting, "u9_metrics": True}
            for case, phases in U9_PHASES.items() for eps in phases for setting in U9_SETTINGS]


D1_BATCH = "d1"
"""D-1 verification matrix harness rows (``d1_rows.py``: H-R 105 + H-S 112 rows x VB / V0 x
eps {0, 2e-3} = 868 runs; output ``d1.jsonl``, a new file: the VB lines are ③ on)."""


P3_HASH_BATCH = "p3_hash"
P3_HASH_SOURCE = OUT_DIR / "main.jsonl"
P3_HASH_SOURCE_OVERRIDE: list[Path | None] = [None]
"""``--p3-hash-source`` of this run: the stored ``main.jsonl`` the ``j9_t8`` batch reads its 22
jobs from (None = :data:`P3_HASH_SOURCE`)."""
P3_HASH_CASES = 22
"""Criteria revision 8 7.2: per case the first VB line of ``main.jsonl`` (r5, ③ off), rerun
with the VB definition of revision 8 (③ on); ``p3_hash_check.py`` compares the two."""


def p3_hash_jobs(source: Path = P3_HASH_SOURCE) -> list[tuple[int, dict]]:
    """(1-based line number, job) of the first VB line per case of ``source``.

    Raises:
        RuntimeError: Not :data:`P3_HASH_CASES` cases.
    """
    jobs: dict[str, tuple[int, dict]] = {}
    for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        record = json.loads(line)
        job = record["job"]
        if "error" in record or job["setting"] != "VB" or job["case"] in jobs:
            continue
        jobs[job["case"]] = (number, {k: v for k, v in job.items()
                                      if k not in RUNTIME_JOB_KEYS})
    if len(jobs) != P3_HASH_CASES:
        raise RuntimeError(f"{source.name}: {len(jobs)} VB cases, {P3_HASH_CASES} expected")
    return list(jobs.values())


GRID_TWIN_FIELDS = ("event", "timing", "depth_m", "ramp_s")
"""Twin fields of a stored-grid row (edition 6 confirmation grid, spec 6.3 (나): the r67 event
name and timing of ``EventTwin``; edition 8 Y8-9: the event depth and ramp of a held-out shape
variant); a job twin with them gets them in its T4h file name, so the FS24 / G4 / RE1bF rows
(and the 25 mm / 30 mm RE1bF variants) of one (level, leg, F_s, offset) do not share a file."""
GRID_TWIN_FIELD_PREFIX = {"depth_m": "d", "ramp_s": "r"}
"""File-name prefix of the edition 8 twin fields (``-d0.025-r0.05``); the older fields have
none."""
RUNTIME_JOB_KEYS = ("mask", "t4h_dir")
"""Job entries ``main`` adds for the worker only (not part of the job identity)."""
T4H_SETTINGS = ("VB", "LS1", "LS2", "LS3", "LS4", *JP3_JUDGED_SETTINGS, *JP3_DIAG_SETTINGS,
                *ED6_SETTINGS, *ED7_SETTINGS, *ED8_SETTINGS)
"""Criteria 9 T4h (control-expert B): the runs that write a T4h record (436.9: the VBJ, LSJ,
VBJ0, VBH and LSH settings too, spec 6.3; edition 6: every :data:`ED6_SETTINGS` run; edition 7:
every :data:`ED7_SETTINGS` run; edition 8: every :data:`ED8_SETTINGS` run)."""


def job_key(job: dict) -> str:
    return json.dumps({k: job[k] for k in sorted(job) if k not in RUNTIME_JOB_KEYS},
                      sort_keys=True)


def t4h_file_name(job: dict) -> str:
    """``<row>_<phase>_<setting>.npz`` of a job (phase as in ``aggregate_v5``, file-safe); a job
    with ``eta_v`` ends in ``<setting>-eta<eta_v>`` (the two VB supplies of ``u9_targeted``)."""
    row = "R2ra" if job.get("decision") == "reanchor_on" else job["case"]
    if job.get("twin"):
        twin = job["twin"]
        phase = f"{twin['level']}-{twin['leg']}-Fs{twin['fs_kN']:g}-o{job.get('offset_s')}"
        for field in GRID_TWIN_FIELDS:  # edition 6 grid rows (6.3 (나)); absent elsewhere
            if field in twin:
                phase += f"-{GRID_TWIN_FIELD_PREFIX.get(field, '')}{twin[field]}"
    elif job.get("offset_s") is not None:
        phase = f"o{job['offset_s']}"
    else:
        phase = f"e{job.get('eps', 0.0)}"
    if job.get("timing"):
        phase += f"-{job['timing']}"
    setting = job["setting"]
    if job.get("eta_v") is not None:
        setting += f"-eta{job['eta_v']:g}"
    return f"{row}_{phase}_{setting}.npz"


def _t4h_request(job: dict, flow, options) -> dict | None:
    """The T4h path and meta of a VB / LS job of a batch run (None otherwise)."""
    if job.get("t4h_dir") is None or job["setting"] not in T4H_SETTINGS:
        return None
    from outrigger_sim.hydraulics.v5_options import controller_tag

    meta = {"job": {k: v for k, v in job.items() if k not in RUNTIME_JOB_KEYS},
            "flow_setting": flow.to_dict(),
            "hydraulic_options": None if options is None else options.to_dict()}
    # No controller exists yet: the request carries the options' tag only. The record is
    # written by verdict_runs._finish, which adds _LAS from the run's own config
    # (_meta_with_controller_tag), so a LAS-b run's T4h never keeps the pre-switch tag.
    tag = controller_tag(options)
    if tag is not None:  # criteria revision 8 (key only with ③ on)
        meta["controller_tag"] = tag
    return {"path": Path(job["t4h_dir"]) / t4h_file_name(job), "meta": meta}


def _install_approach_scale(eps: float) -> None:
    """``run_m1``: approach speed scale until the first touch (the phase of the steady rows)."""
    import harness_flow
    import numpy as np

    original_limit = harness_flow.FlowLimiter.limit

    def limit(self, t_s, u, oil_force_N):
        delivered = original_limit(self, t_s, u, oil_force_N)
        touched = self.__dict__.setdefault("_touched", np.zeros(4, bool))
        touched |= np.asarray(oil_force_N) > 3000.0
        return delivered * (1.0 - eps) if not touched.any() else delivered

    harness_flow.FlowLimiter.limit = limit


def _case_of(job: dict):
    import verdict_cases

    decision = job.get("decision")
    decisions = {"R13": "ss_fs4"} | ({job["case"]: decision} if decision else {})
    case = verdict_cases.resolve_case(job["case"], decisions)
    if job.get("offset_s") is not None:
        case = replace(case, twin=replace(case.twin, offset_s=float(job["offset_s"])))
    if job.get("twin"):
        case = replace(case, twin=replace(case.twin, **job["twin"]))
    if job.get("timing") == OVERLAP_TIMING:
        t_a = overlap_reference()["t_a_s"]
        case = replace(case, twin=replace(case.twin, timing=OVERLAP_TIMING, event_time_s=t_a))
    return case, decision


def overlap_reference_path() -> Path:
    """The t_a record of this process: :data:`OVERLAP_REFERENCE_ENV`, else the stored file."""
    value = os.environ.get(OVERLAP_REFERENCE_ENV)
    return Path(value) if value else OVERLAP_REFERENCE_PATH


def overlap_reference() -> dict:
    """The t_a record of the ``overlap`` batch (:func:`overlap_reference_path`).

    Raises:
        RuntimeError: No reference yet, or it has no t_a.
    """
    path = overlap_reference_path()
    if not path.exists():
        raise RuntimeError(f"no t_a reference {path} (run_v5 overlap writes it)")
    reference = json.loads(path.read_text(encoding="utf-8"))
    if reference.get("t_a_s") is None:
        raise RuntimeError(f"t_a reference without a time: {reference.get('basis')}")
    return reference


def run_overlap_reference(job: dict) -> dict:
    """Worker: t_a of the VB base run of the overlap case (criteria 13.3)."""
    import verdict_cases
    import verdict_runs

    flow, options = options_of(job["setting"])
    case = verdict_cases.resolve_case(job["case"], {"R13": "ss_fs4"})
    return verdict_runs.flow_saturation_reference(case, flow, options)


def write_overlap_reference() -> dict:
    """Run the VB reference in one spawned worker (its plant patches stay there) and store t_a."""
    job = {"case": OVERLAP_CASE, "setting": OVERLAP_REFERENCE_SETTING}
    with get_context("spawn").Pool(1, maxtasksperchild=1) as pool:
        reference = pool.apply(run_overlap_reference, (job,))
    path = overlap_reference_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reference, indent=1), encoding="utf-8")
    return reference


def options_of(setting: str, eta_v: float | None = None):
    """(``FlowSetting``, ``HydraulicOptions`` or None) of a setting name.

    Args:
        setting: A :data:`SETTINGS` name.
        eta_v: Pump volumetric efficiency of a flow-limited setting (job key ``eta_v``,
            ``u9_targeted_rules_rev1.md`` 3.2 P-1); None = :data:`ETA_V`.

    Raises:
        ValueError: ``eta_v`` given for a setting without the flow limit.
    """
    from harness_flow import FlowSetting

    from outrigger_sim.hydraulics.v5_options import HydraulicOptions

    is_flow_on, plant = ALL_SETTINGS[setting]
    if eta_v is not None and not is_flow_on:
        raise ValueError(f"setting {setting!r} has no flow limit: eta_v {eta_v} is meaningless")
    if is_flow_on:
        flow = FlowSetting(is_enabled=True, eta_v=ETA_V if eta_v is None else float(eta_v))
    else:
        flow = FlowSetting(is_enabled=False)
    return flow, (HydraulicOptions.from_dict(plant) if plant else None)


def run_one(job: dict) -> dict:
    """One run in this worker; the record line."""
    t_start = time.perf_counter()
    try:
        import verdict_runs
        from run_m1 import command_stats, event_names

        if job.get("mask") is not None:
            import s9_soil_slope as slope

            slope.set_parent_affinity(int(job["mask"]))
        if job.get("eps"):
            _install_approach_scale(float(job["eps"]))
        flow, options = options_of(job["setting"], job.get("eta_v"))
        contact = job.get("contact")
        if job.get("d1") is not None:  # D-1 row (no T4h record: criteria 9 is not its judge)
            import d1_runs

            t4h = None
            # mass_scale: B1 H-W jobs only (B1 rules R-4); a job without the key runs at 1.0
            result, series = d1_runs.execute(job["d1"], flow, options,
                                             setting_name=job["setting"],
                                             eps=float(job.get("eps", 0.0)), k1=job.get("k1"),
                                             mass_scale=float(job.get("mass_scale", 1.0)))
        else:
            case, decision = _case_of(job)
            t4h = _t4h_request(job, flow, options)
            result, series = verdict_runs.execute(case, flow, decision, hydraulics=options,
                                                  contact=contact, t4h=t4h,
                                                  u9_metrics=bool(job.get("u9_metrics")))
        if "error" in result:
            return {"job": job, "error": result["error"], "tb": result.get("tb"),
                    "wall_s": round(time.perf_counter() - t_start, 1)}
        events = result["events"]
        judge_record = {} if contact is None else {"contact_judge": result.get("contact_judge"),
                                                   "unit_status": UNIT_STATUS}
        return {"job": job, "wall_s": round(time.perf_counter() - t_start, 1),
                **judge_record,
                "commands_sha256": result["commands_sha256"],
                "final_phase": result["final_phase"], "values": result["values"],
                "t_event_s": result.get("t_event_s"), "event_output": {
                    k: v for k, v in (result.get("event_output") or {}).items() if k != "twist"},
                "event_names": event_names(events),
                "events": [e for e in events
                           if e[1].startswith(("WARN", "FAULT", "INFO_ROD"))][:200],
                "command_stats": command_stats(series),
                "harness_class": result.get("harness_class"),
                "hydraulic_options": result.get("hydraulic_options"),
                "hydraulics_record": result.get("hydraulics_record"),
                "review_record": result.get("review_record"),
                **{key: result[key] for key in LINE_RECORD_KEYS if key in result},
                **({} if t4h is None else {"t4h_file": t4h["path"].name})}
    except Exception as exc:  # the batch goes on; the line records the failure
        return {"job": job, "error": repr(exc), "tb": traceback.format_exc()[-3000:],
                "wall_s": round(time.perf_counter() - t_start, 1)}


def _check_stored_definition(path: Path, record: dict) -> None:
    """A finished line counts as done only with the options its setting has now.

    Raises:
        RuntimeError: The stored options differ (criteria revision 8: VB / LS lines written
            before the ③ start bound joined their definition). Archive the file first; the
            stored lines stay valid as ``final_C4G2_P3`` results once the 7.2 hash check
            (``p3_hash_check.py``) passed.
    """
    _, options = options_of(record["job"]["setting"])
    current = None if options is None else options.to_dict()
    if record.get("hydraulic_options") != current:
        raise RuntimeError(f"{path.name}: {record['job']} was run with other options "
                           f"({record.get('hydraulic_options')} != {current}); archive the "
                           "file before running this definition")


def _done_keys(path: Path) -> set[str]:
    """Job keys of the finished runs in ``path``.

    Raises:
        RuntimeError: The file holds an M2 run of another M2 law (the job key has no law: it
            would count as done). Archive the file first (``*_m2r3`` precedent).
    """
    from outrigger_sim.hydraulics.rod_release import FLOW_LIMITED_LAW, RERUNNABLE_LAWS

    if not path.exists():
        return set()
    done = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        stored_law = (record.get("hydraulic_options") or {}).get("m2_law", FLOW_LIMITED_LAW)
        if stored_law not in RERUNNABLE_LAWS:  # r6 = 436.9 P3; the options check pairs it
            raise RuntimeError(f"{path.name}: M2 law {stored_law!r} is not one of "
                               f"{RERUNNABLE_LAWS}; archive the file before running this law")
        if "error" not in record:
            _check_stored_definition(path, record)
            done.add(job_key(record["job"]))
    return done


D8X_OUT_DIR = ROOT / "06_analysis" / "02_control" / "d8x" / "rc"
"""D8x R-c output folder (``d8x_rules.md`` 9.2 item 2): ``hrx_<k1>.jsonl``."""
RESUME_K1_KEY = "resume_k1"
"""``resume_k1_record.RECORD_KEY``: the 436.8 record block a line copies from the result."""
HARNESS_HASH_KEY = "harness_commands_sha256"
"""The harness' own command hash (the r67 screen hash of a stored grid row, prefix + branch;
addendum 4a-2 R7 F-A compares it with ``grid_r67_top``). Record only."""
LINE_RECORD_KEYS = ("overlap_found", "soil_stop_crawler", "lock_window_alignment",
                    "controller_tag", "head_only_declared", "d1", RESUME_K1_KEY,
                    HARNESS_HASH_KEY, "lsb_components", "lsb_settings", "lsb_record",
                    "probe_d6_settings", "probe_d6_record", "probe_stiffness_record",
                    "ib_block_record", "ed8_settings", "ed8_record")
"""Result keys a line copies when the run has them (in this order); the last four are the
edition 8 records (``verdict_runs.enable_ed8_record`` or an edition 8 controller, record
only)."""


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("batch")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--mask", default=None, help="hex affinity mask, inherited by the workers")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--group", default=None, choices=("H-R-X",),
                        help="d1 only: the D8x H-R-X rows (d8x_rules.md 3 R-c) instead of the d1 batch")
    parser.add_argument("--k1", default=None, choices=("off", "on"),
                        help="with --group H-R-X: R4c30 order gate of this arm, required")
    parser.add_argument("--out", type=Path, default=None,
                        help="output jsonl (default v5/<batch>.jsonl; with --group H-R-X "
                             "d8x/rc/hrx_<k1>.jsonl); a run identity <stem>.identity.json is written "
                             "next to it at the start and the end, the T4h records go to "
                             "<stem>_t4h/ (436.8 rules 4.3)")
    parser.add_argument("--settings", default=None,
                        help="comma list: run only the jobs of these settings (e.g. VB,LS1,LS2,LS3,LS4)")
    parser.add_argument("--one-per-setting", action="store_true",
                        help="G-S dry run (436.8 rules 11.2): the first job of each setting only")
    parser.add_argument("--overlap-reference", type=Path, default=None,
                        help="overlap only: t_a record of this run (436.8 rules rev1 RV1-4); "
                             "written by the VB reference run when missing, read by every "
                             "worker; never the stored v5/overlap_t_a.json")
    parser.add_argument("--p3-hash-source", type=Path, default=None,
                        help="j9_t8 only: the stored v5/main.jsonl of the 22-job rule "
                             "(addendum 4a-3 2; a worktree has none)")
    parser.add_argument("--jobs-file", type=Path, default=None,
                        help=f"{J9_V0_SAMPLE_BATCH}: the fixed V0 sample key file (erratum 2 "
                             f"2-7.1); {ED6_KEYS_BATCH}: a sealed edition 6 key file")
    args = parser.parse_args(argv)
    jobs_file_batches = (J9_V0_SAMPLE_BATCH, ED6_KEYS_BATCH, ED7_KEYS_BATCH, ED8_KEYS_BATCH,
                         ED8_HELDOUT_V0_BATCH, *ED8_HELDOUT_AA_BATCHES)
    if (args.jobs_file is not None) != (args.batch in jobs_file_batches):
        parser.error(f"--jobs-file belongs to the {jobs_file_batches} batches (and they need it)")
    J9_V0_SAMPLE_FILE[0] = args.jobs_file
    ED7_KEYS_FILE[0] = args.jobs_file
    ED8_KEYS_FILE[0] = args.jobs_file
    if args.p3_hash_source is not None:
        if args.batch not in (J9_T8_BATCH, ED6_T8_BATCH, ED7_T8_BATCH, ED8_T8_BATCH):
            parser.error("--p3-hash-source belongs to the j9_t8 / ed6_t8 / ed7_t8 / ed8_t8 "
                         "batches")
        import jp3_fixed_inputs

        problem = jp3_fixed_inputs.sha_problem(args.p3_hash_source,
                                               jp3_fixed_inputs.MAIN_JSONL_SHA256,
                                               "--p3-hash-source (addendum 4a-4 5)")
        if problem is not None:
            parser.error(problem)
        P3_HASH_SOURCE_OVERRIDE[0] = args.p3_hash_source
    _check_overlap_reference(parser, args)
    if args.group is None and args.k1 is not None:
        parser.error("--k1 belongs to --group H-R-X")
    if args.group is not None and args.batch != D1_BATCH:
        parser.error("--group is a d1 option")
    if args.group is not None:
        if args.k1 is None:  # D8x rev3 2: the K1 request is explicit on every H-R-X run
            parser.error("--group H-R-X needs --k1 off|on (d8x_rules_rev3.md 2)")
        args.out = args.out or D8X_OUT_DIR / f"hrx_{args.k1}.jsonl"
    if args.settings is not None:
        names = [name for name in args.settings.split(",") if name]
        unknown = sorted(set(names) - set(ALL_SETTINGS))
        if not names or unknown:
            parser.error(f"--settings needs setting names of {sorted(ALL_SETTINGS)}, "
                         f"got {unknown or names}")
        args.settings = tuple(names)
    return args


def _check_overlap_reference(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """RV1-4: an ``overlap`` run under a new name needs its own t_a record, and that record is
    never the stored one (a rerun would otherwise read the pre-③ t_a)."""
    if args.overlap_reference is None:
        if args.batch == "overlap" and args.out is not None:
            parser.error("overlap with --out needs --overlap-reference (436.8 rules rev1 RV1-4)")
        return
    if args.batch != "overlap":
        parser.error("--overlap-reference belongs to the overlap batch")
    if args.overlap_reference.resolve() == OVERLAP_REFERENCE_PATH.resolve():
        parser.error(f"--overlap-reference must not be the stored {OVERLAP_REFERENCE_PATH.name}")


def select_settings(jobs: list[dict], settings: tuple[str, ...] | None) -> list[dict]:
    """The jobs of ``settings`` (all jobs for None).

    Raises:
        SystemExit: No job of the batch has one of these settings.
    """
    if settings is None:
        return jobs
    picked = [job for job in jobs if job["setting"] in settings]
    if not picked:
        raise SystemExit(f"no job of the batch has a setting in {settings}")
    return picked


def first_job_per_setting(jobs: list[dict]) -> list[dict]:
    """The first job of each setting, in batch order (the G-S dry run of 436.8 rules 11.2)."""
    picked: dict[str, dict] = {}
    for job in jobs:
        picked.setdefault(job["setting"], job)
    return list(picked.values())


def output_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    """(output jsonl, T4h folder) of a run: the stored ``v5/<batch>.jsonl`` and ``v5/<batch>/t4h``
    without ``--out``; with it ``<out>`` and ``<out folder>/<out stem>_t4h`` (a rerun under a new
    name never writes into the stored T4h folder)."""
    if args.out is None:
        return OUT_DIR / f"{args.batch}.jsonl", OUT_DIR / args.batch / "t4h"
    out = Path(args.out)
    return out, out.with_name(f"{out.stem}_t4h")


def _write_identity(path: Path, moment: str) -> None:
    """D8x rules I-1: run identity at the start / end, next to the output."""
    import d1_rows

    record = d1_rows._d8x_record_module()
    sidecar = path.with_name(path.stem + ".identity.json")
    stored = json.loads(sidecar.read_text(encoding="utf-8")) if sidecar.exists() else {}
    stored.setdefault(moment, []).append({"time": time.strftime("%Y-%m-%d %H:%M:%S %z"),
                                          **record.run_identity(ROOT)})
    sidecar.write_text(json.dumps(stored, indent=1), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.group is not None:
        import d1_rows

        jobs = d1_rows.d8x_jobs(args.k1)
    else:
        jobs = batch_jobs(args.batch)
    jobs = select_settings(jobs, args.settings)
    if args.one_per_setting:
        if args.out is None:  # a G-S line must never land in a stored or 436.8 output file
            raise SystemExit("--one-per-setting needs --out (a G-S folder)")
        jobs = first_job_per_setting(jobs)
    path, t4h_dir = output_paths(args)
    done = _done_keys(path)
    todo = [job for job in jobs if job_key(job) not in done]
    print(f"{args.batch}: {len(jobs)} runs, {len(todo)} to do", flush=True)
    if args.list:
        if args.batch == D1_BATCH:
            import d1_rows

            print(d1_rows.list_report(jobs), flush=True)
        return
    mask = None if args.mask is None else int(args.mask, 16)
    for job in todo:
        job["mask"] = mask
        job["t4h_dir"] = str(t4h_dir)
    if args.overlap_reference is not None:  # before the pool: the spawned workers inherit it
        os.environ[OVERLAP_REFERENCE_ENV] = str(args.overlap_reference.resolve())
    import verdict_runs

    verdict_runs.warm_numba_cache()
    if args.batch == "overlap" and not overlap_reference_path().exists():
        reference = write_overlap_reference()
        print(f"overlap t_a {reference['t_a_s']} s ({reference['basis']}) -> "
              f"{overlap_reference_path()}", flush=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    has_identity = args.group is not None or args.out is not None
    if has_identity:
        _write_identity(path, "start")
    _run_pool(args, todo, path)
    if has_identity:
        _write_identity(path, "end")


def _run_pool(args: argparse.Namespace, todo: list[dict], path: Path) -> None:
    with get_context("spawn").Pool(args.workers, maxtasksperchild=1) as pool, \
            path.open("a", encoding="utf-8") as handle:
        for count, record in enumerate(pool.imap_unordered(run_one, todo), 1):
            for key in RUNTIME_JOB_KEYS:
                record["job"].pop(key, None)
            handle.write(json.dumps(record, default=lambda v: v.item() if hasattr(v, "item")
                                    else str(v)) + "\n")
            handle.flush()
            state = record.get("error", "")[:200] or (
                f"{record['final_phase']} {record['commands_sha256'][:8]} {record['wall_s']}s")
            print(f"{count}/{len(todo)} {record['job']}: {state}", flush=True)


if __name__ == "__main__":
    main()
