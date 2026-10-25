"""S8 control ③ re-judgement on L2b-NSC with seal friction (R8 C2, 10 Hz, d = 1).

``00_docs/04_control/s6_control_spec.md`` rev. 39 (199-209: case matrix 202, item 9 203, ML data
205, cad delegation C-S8-1 ... C-S8-6) and rev. 40 210 (C-S8-7 / C-S8-8: 8 s lift-off window,
crawler contact meta); ``dynamics_model.md`` 5.25.5 (S8-L1 / L2); hydraulics plant spec
``00_docs/02_hydraulic/s8_seal_friction_counterbalance.md``. Judge module
``outrigger_sim.verify.s8_control``.

Usage (Chrono-dev python, project root)::

    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py list --set p1
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py plan --set p1 [--workers p7e8]
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py check --set p1 [--duration 0.3]
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py run --set p1 --approved [--workers p7e8]
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py run --set rest --approved   # 49 cases
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py ml --approved [--workers p7e8]  # 24 + 192
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py judge --batch 07_results/S8/p1_<stamp>
        [--ref-batch 07_results/S8/<earlier batch>]   # 213.6 TOUCH regression row
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py snaps          # L1 twin start states
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py smoke-branch   # C-S8-4 continuity
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py ml-plan --stage main   # 768 plan
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py ml --stage main --approved  # 768 + MLJ 6
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py ml --resume 07_results/S8/ml_pilot_<stamp>
        --only ML00_ep5 ML08_ep4 ML10_ep4 ML11_ep4 ML17_ep4 ML18_ep6 ML21_ep1 --approved  # C-S8-28
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py run --set mlj_c29 --approved  # C-S8-29
    # U-S8-40 (spec rev. 49 219.9): C-S8-28 -> MLJ 6 alone -> main 768 reusing the MLJ batch
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py run --set mlj --approved   # MLJ 6
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py ml --stage main
        --mlj-from 07_results/S8/mlj_<stamp> --approved     # 768, MLJ copied to judged/
    (``--skip-judged``: 768 without MLJ; ``--dry-run`` on ml / run / check prints the plan)
    # C-S8-36 (spec rev. 52 230, U-S8-50): A 55 (RT + F1) + B 2 (F1 only) + C RE1bF / RE1bP
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py c36 --dry-run
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py c36 --approved [--workers p7e8]
        -> 07_results/S8/c36_<stamp>/{A_rt/episodes, B_f1only/episodes, C_gate}
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py c36 --smoke ML78_ep0 --episode-s 6
        --out <scratch dir>   # one shortened episode, single process
    # C-S8-36 bundle D (spec rev. 54 250, U-S8-55): MLJ_FS24_Fs0 / Fs8, P-S8-16 + F1
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py c36 --bundle D
        --batch 07_results/S8/c36_<stamp> [--dry-run | --approved] [--workers p7]
        -> 07_results/S8/c36_<stamp>/D_fs24   (without --batch: c36d_<stamp>/D_fs24)
    # C-S8-41 (U-S8-56 (a)): 17 rod-fallback episodes, RT + F1 + P-S8-21, + regression C / D
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py c36 --bundle E [--no-regression]
        [--extra-ids ML.._ep..,...] [--dry-run | --approved] [--workers p7e8]
        -> 07_results/S8/c37_<stamp>/{E_drain/episodes, C_gate, D_fs24}
        (--extra-ids, C-S8-42 / spec rev. 55 269.1: bundle-A episodes outside the 17 whose
        replayed controller output differs from the record)
    # C-S8-40 judge (rev. 54): A / B with the 768 reference for the FLAG row
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py judge --batch <c36>/A_rt
        [--ref-batch 07_results/S8/ml_main_20261025_090131]
    # C-S8-42 judge (rev. 56): bundle D with the original MLJ as the deferred-leg reference
    python -I -X utf8 -u 04_scripts/02_chrono/run_S8C.py judge --batch <c37>/D_fs24
        --lookup-batch 07_results/S8/p1r_20261024_222013
        --deferred-ref 07_results/S8/mlj_20261025_080212

Rev. 52 (C-S8-36): ``ml_episode`` jobs take ``variant`` (``rt`` = R8 preset with the P-S8-16
rule RT, ``f1only`` = RT keys None, :func:`with_reapproach_variant`); episodes can read their
``branch.pkl`` from another batch (``base_dir``, read only). ``settings_refreshed`` lists the
changed nested setting fields (``replaced[].changed_fields``) and the re-approach settings
(``lifted_reapproach``: pickled / in use / fresh); the whole repr stays cut at 4000 characters.

Rev. 49 (219.11, C-S8-31): ``r8_series.npz`` also records ``imu_gyro_samples`` (periods x 10 x
3, rad/s, body axes), the delivered gyro 10 ms partial means that C2 passes to the D1'' lever
term (``Measurements.imu_angular_rate_samples_rad_s`` from ``SensorSuite``).

Rev. 48 (218.13 / 218.15, C-S8-27 ... 30, U-S8-32 ... 35): ``ml --stage main`` = 96 bases x 8
episodes with the retract speed U(0.5, 1.0) v_max (``speed_fraction``, separate generator,
:func:`ml_episodes` design ``main``) and the six ``MLJ`` judged cases (front fast settlement
FS24, C-S8-24 SS9P + ``request_probe``, C-S8-29 G4RF rod-sensor dropout) in the base-phase pool
(``judged/``); the P-S8-13 lock window gets the case valve lag (:func:`with_lock_window_tau`).

Rev. 43 (213.8 C-S8-17 / C-S8-18): every L2b run ends by :func:`end_rule` (D8 READY + 10 s,
event + 45 s, HOLD READY + 120 s; upper bound duration + 60 s, else ``timeout`` in
``result.json s8_end`` with the phase lengths); ``p1r`` = ``p1`` + N_D8 rpB pressure-only (37).
``s8_series.npz`` also carries ``F_nominal_N`` / ``F_lower_est_N`` (C-S8-16 ①).

Rev. 44 (214.10 C-S8-19): ``result.json twist_stiffness_history`` (scale after every probe
round, :class:`TwistScaleHistory`); the planner uses the p1r full-pool costs (P 5.3 s/s for
F_s > 0, E/P 1.7); ML meta ``sensor_grade`` (grade) + ``zero_calibration`` (bool) +
``sensor_condition`` (former combined string).

Sets (``--set``): ``p1`` = priority 1 (K0 4, K0V 5, K8 9, S 2, E 16 = 36), ``p2`` (K24 18, A 8,
B 4), ``p3`` (N 15, L 4), ``rest`` = p2 + p3 (49), ``all`` (85), ``cb`` (6 placeholders, needs the
counterbalance plant), ``smoke`` (2 short F_s 0 cases). ``run`` / ``ml`` refuse without
``--approved`` (the main session starts the batches after the user's confirmation).

Rev. 41 (``s6_control_spec.md`` 211.3, C-S8-11, U-S8-8): K0V = the verification boundary 5 points
(flat, fdown3.5 (H4V), fup3.5, roll5.5, rpB) x F_s 0 in the same batch; they are the ``pair_fs0``
of the K8 / K24 verification cases (R41-2). The S7 L2b runs are regression references
(``ref_s7``, R41-3 record rows), no longer twins. One batch = one crawler contact (R41-5).

Workers (``--workers``, U-S8-1): ``p7`` = 7 processes on the P-cores; ``p7e8`` = 7 on the P-cores
+ 8 on the E-cores (each process ``hostcpu.place_process("ecore")``, EcoQoS off); the P pool
takes the longest pending case, the E pool the shortest (spec 202: short D8 cases on the
E-cores). This placement is not a cost measurement (wall times of one batch are not compared).

Plant (C-S8-1): the case friction level ``fs_kN`` (front-leg Coulomb limit, rear = x 0.833 inside
the plant, U-S8-H1 / H2) and ``lock_valve`` go through ``chrono/s8_plant_adapter``; level 0 +
pilot check is the S7 plant and always runs. A ``counterbalance`` case also gives the controller
the CB diagnosis (U-S8-23, P-S8-11: ``C2Config.with_lock_valve`` with the plant's
``l2b.counterbalance``, :func:`_controller`); pilot-check cases keep the config untouched.
Records (C-S8-2): ``pads.npz`` from
``chrono/l2b_pad_record_s8`` (1 ms on time, rod axial force = truth, pressure force, seal state),
``s8_series.npz`` (per 10 Hz period: ``F_band``, per-leg bands, the controller's lower load
estimate, the reading ``F_hat`` = ``p_h A_p - p_r A_ann``) + the R8 series. Floor events
(C-S8-3): ``chrono/l2b_ground_patch`` (G4 11.5 mm / 2 s, SS 11.5 mm / 20 s, SS9 9 mm / 20 s at
first READY + 5 s (+ phase offset), RE1bF 30 mm / 0.05 s at READY + 5 s, RE1bP at the first
PROBE + 0.1 s with the 1e-5 s window of bundle C), RE1c = ``s6_stage2.ForcedRetract`` (RR -25 mm
at 0.25 v_max from READY + 5 s, other legs 0, as the stage-2 RE1c). Episode branch (C-S8-4):
``ml`` runs a base case to first READY + :data:`ML_BRANCH_AFTER_READY_S` in 1 s chunks
(``runner.run_closed_loop(resume_command=...)``) and stores ``branch.pkl`` (model snapshot with
the actuator part = s_ref, rod side, friction state; deep copies of the controller and the sensor
suite; held command; engine contact window); every episode restores it, then brings the
unpickled controller to the current code's settings (:func:`refresh_restored_controller`, meta
``settings.settings_refreshed``) and compares the first period with the unrefreshed copy
(:class:`FirstPeriodCompare`, ``first_period_compare``) (C-S8-25 ③). Retract episodes use
``ForcedRetract(others="controller")`` (U-S8-27); ``ml --resume <batch> --all-episodes`` re-runs
all planned episodes from the kept bases (U-S8-29).

Crawler meta (C-S8-8, R40-6): ``result.json settings.s8.crawler_contact`` ("nsc_rigid" /
"nsc_compliant", from ``L2bModel.crawler_contact`` when the S8-L4 work adds it, else rigid) and
``crawler_check_passed`` (``L2bModel.crawler_check_passed`` or :data:`CRAWLER_CHECK_PASSED`).

Outputs ``07_results/S8/<set>[_check]_<stamp>/<case>/``. Units SI (kN only in names / tables).
"""

from __future__ import annotations

import argparse
import copy
import datetime as _dt
import json
import math
import os
import pickle
import sys
import time
import warnings
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(HERE))

import run_S7C as s7c  # noqa: E402  (imports run_S6C: L1-R env for the L1 twins)

s6c = s7c.s6c
st = s6c.st
RESULTS = ROOT / "07_results" / "S8"
P_WORKERS, E_WORKERS = 7, 8
CASE_TIMEOUT_S = 5400.0
CHECK_TIMEOUT_S = 900.0
CHECK_DURATION_S = 0.3

NEW_FLOORS = {"rpBop": (2.3351, 1.5017), "fup3.2": (0.0, -3.2)}
"""Spec rev. 39 202: operating boundary points (rpB direction scaled to |phi|/4.4 + |theta|/3.2 =
1.000; nose up 3.2 deg, H4 skipped)."""
st.FLOORS.update(NEW_FLOORS)
VERIFY_FLOORS = ("fdown3.5", "fup3.5", "roll5.5", "rpB")
OPERATING_FLOORS = ("fdown3.2", "fup3.2", "roll4.4", "rpBop")

FS_LEVELS_KN = (0.0, 2.0, 4.0, 8.0)
G4_DEPTH_M, G4_RAMP_S = 0.0115, 2.0
SS_DEPTH_M, SS_RAMP_S = 0.0115, 20.0
SS9_DEPTH_M = 0.009
SS_EXTRA_S = st.T_SETTLE_EXTRA + 18.0
"""SS / SS9: the G4 extra (40 s) + the longer ramp (20 - 2 s)."""
HOLD_READY_S = 120.0
RE1C_DEPTH_M, RE1C_SPEED_FRACTION = 0.025, 0.25
FS24_DEPTH_M, FS24_RAMP_S = 0.024, 0.3
"""U-S8-32 (spec rev. 48 218.5): front fast settlement judged case, FR 24 mm / 0.3 s (the
ML00_ep5 settlement 23.93 mm / 0.3048 s rounded), top level, flat floor (ASSUMPTION: the
E-group G4 context; ML00's own floor -1.79 / +1.28 deg is not used)."""
FS24_FINE_EXPECTED_S = 10.0
"""ASSUMPTION (cost only): fine-dt window length of FS24, as ``drop_RR_30``."""
SS9P_END_AFTER_S = 60.0
"""C-S8-24: SS9 (20 s ramp) + re-READY + the requested probe; run end = event + 60 s
(ASSUMPTION; the 45 s of the other events leave about 25 s after the ramp for the probe)."""
G4RF_FAULT_AFTER_S = 2.0
"""C-S8-29 (spec rev. 48 218.10): rod-sensor dropout (NaN reading, D1) on FR from first READY
+ 2 s, before the G4 at READY + 5 s (ASSUMPTION: fault kind and time not given by the spec)."""
ML_FORCED_OTHERS = "controller"
"""U-S8-27 / C-S8-25 ①: ML retract episodes override only the forced leg until the retraction is
done, then hand every leg back to the controller (RE1c keeps ``"zero"``)."""
FINE_DT_EXTRA_STEPS_FACTOR = 9.0
"""1e-4 -> 1e-5 s: 10x the steps inside the window (+9x)."""

END_D8_AFTER_READY_S = 10.0
END_EVENT_AFTER_S = 45.0
END_HOLD_AFTER_READY_S = HOLD_READY_S
END_CAP_EXTRA_S = 60.0
"""C-S8-17 (``s6_control_spec.md`` rev. 43 213.8): a run ends at first READY + 10 s (D8, no
event), event + 45 s (floor / retract events; the event time is the scheduled start) or first
READY + 120 s (HOLD). Upper bound = the scenario duration + 60 s; a run that reaches it before
its end time is a ``timeout`` (``result.json s8_end``, R43-4)."""
EXPECTED_READY_TOP_S = {"flat": 42.8, "fdown3.5": 78.9, "fup3.5": 59.1, "roll5.5": 59.2,
                        "rpB": 57.8, "fdown3.2": 77.5, "fup3.2": 58.0, "roll4.4": 56.7,
                        "rpBop": 56.1}
"""First READY [s after the start] of the F_s 0 top cases of batch ``p1_20261024_204911`` (cost
estimate of the end rule only; ASSUMPTION: F_s > 0 cases reach READY at the same time once the
TOUCH fix P-S8-6 is in, spec rev. 43 213.6 'TOUCH length within F_s 0 + 1 s')."""
EXPECTED_FIRST_PROBE_FLAT_S = 30.9
"""First PROBE of the flat top case (RE1bP event = probe + 0.1 s), same batch."""


def end_rule(case: "S8Case") -> dict[str, Any]:
    """C-S8-17 end rule of a case: anchor (``ready`` / ``event``), offset, upper bound."""
    if case.event is None:
        anchor, after = "ready", END_D8_AFTER_READY_S
    elif case.event == "HOLD":
        anchor, after = "ready", END_HOLD_AFTER_READY_S
    else:
        anchor = "event"
        after = float((case.event_spec() or {}).get("end_after_s", END_EVENT_AFTER_S))
    return {"anchor": anchor, "after_s": after,
            "upper_s": case.duration_s + END_CAP_EXTRA_S,
            "rule": "C-S8-17 (spec rev. 43 213.8): D8 READY + 10 s, event + 45 s, HOLD READY + "
                    "120 s; upper bound duration + 60 s, else timeout"}


def expected_run_s(case: "S8Case") -> float:
    """Expected simulated run length under :func:`end_rule` (cost estimate; falls back to the
    scenario duration where no reference time is known)."""
    rule = end_rule(case)
    ready = EXPECTED_READY_TOP_S.get(case.floor) if case.scenario.level == "top" else None
    if ready is None:
        return case.duration_s
    if rule["anchor"] == "ready":
        t = ready + rule["after_s"]
    elif case.event == "RE1bP":
        t = EXPECTED_FIRST_PROBE_FLAT_S + st.RE1BP_DELAY_S + rule["after_s"]
    else:
        t = ready + 5.0 + case.phase_offset_s + rule["after_s"]
    return min(t, rule["upper_s"])


def phase_lengths(phases: list[tuple[float, str]], end_s: float) -> dict[str, Any]:
    """C-S8-17 meta: total time per phase and the first TOUCH / LEVEL lengths [s]."""
    total: dict[str, float] = {}
    first: dict[str, float] = {}
    for i, (t, p) in enumerate(phases):
        t1 = phases[i + 1][0] if i + 1 < len(phases) else end_s
        total[p] = total.get(p, 0.0) + (t1 - t)
        first.setdefault(p, t1 - t)
    return {"total_s": total, "first_touch_s": first.get("touch"),
            "first_level_s": first.get("level")}

L2B_US_PER_STEP = 300.0
"""Wall per L2b step with 7 workers on the P-cores (S7 ctrl3 261-291 us, run_S7C)."""
FRICTION_US_PER_STEP = 37.0
"""C-S8-1 / C-10 single-process P-core measurement 2026-10-24 (``L2bModel.step`` on the pads,
4 legs moving / locked, min of 3 x 4000 steps): seal friction 4 kN adds +37 us/step to the S7
path. Added to :data:`L2B_US_PER_STEP` for F_s > 0 (ASSUMPTION: the same increment under 7 / 15
parallel workers). Replaces the earlier x1.3 factor (5 s check runs with other jobs on the
host, x1.17-1.52)."""
CB_US_PER_STEP = 72.0
"""Same measurement: seal friction + counterbalance = +72 us/step over the S7 path (CB cases,
used instead of :data:`FRICTION_US_PER_STEP`)."""
P_FULL_US_PER_STEP_FS = 530.0
"""C-S8-19 ⑥ (spec rev. 44 214.6, ``06_analysis/02_control/s8/s8_p1r_rev44_wall.json``): P-core
wall per L2b step of an F_s > 0 case while the p7e8 pool is full (p1r median 5.34 s wall per
simulated second, 1e-4 s steps; the batch case wall over the record time incl. the crawler
settle). Replaces :data:`L2B_US_PER_STEP` + :data:`FRICTION_US_PER_STEP` (3.4 s/s, close to a
lone process, 1.5x low under a full pool)."""
FS0_COST_RATIO = 1.23
"""ASSUMPTION (spec rev. 44 214.6): F_s > 0 / F_s 0 wall ratio, from the p1r E-core K group
(median 9.11 vs 7.40 s/s); no F_s 0 P-core case ran with the pool full."""
P_FULL_US_PER_STEP_FS0 = P_FULL_US_PER_STEP_FS / FS0_COST_RATIO
P_FULL_US_PER_STEP_CB = P_FULL_US_PER_STEP_FS * (L2B_US_PER_STEP + CB_US_PER_STEP) / (
    L2B_US_PER_STEP + FRICTION_US_PER_STEP)
"""ASSUMPTION: the counterbalance case scales with the single-process increments (+72 vs +37 us
over 300 us)."""
E_CORE_FACTOR = 1.7
"""C-S8-19 ⑥ (spec rev. 44 214.6): E-core / P-core wall ratio with EcoQoS off and the pool full
(p1r 1.71; all cases 1.60; same-case pairs 1.1-2.0, median 1.63). Was 2.45 (before EcoQoS off)."""
L1_WALL_S_PER_S = 3.5
CRAWLER_ENV = "OUTRIGGER_S8_CRAWLER"
"""``--crawler`` (``yaml`` default = ``contact.crawler.L2b_NSC.model``; ``rigid`` / ``compliant``
force ``L2bModel(crawler_contact=...)``); an environment variable so the case processes inherit
it."""
CRAWLER_CHECK_PASSED: bool | None = None
"""S8-L4 result (R40-6); filled by the crawler check work, None = not checked."""

S7_FS0_REFS = {
    "rpB": ("07_results/S7/ctrl3_20261024_154939", "L2b_D8_top_rpB_b1.0"),
    "fdown3.5": ("07_results/S7/ctrl3_20261024_154939", "L2b_H4V_top_fdown3.5"),
    "fup3.5": ("07_results/S7/ctrl3_rerun_20261024_162807", "L2b_D8_top_fup3.5_b1.0"),
    "roll5.5": ("07_results/S7/ctrl3_rerun_20261024_162807", "L2b_D8_top_roll5.5_b1.0"),
    "flat": ("07_results/S7/ctrl3_20261024_154939", "L2b_smoke_top_flat"),
}
"""S7 L2b runs of the verification points and flat (rigid crawler). Rev. 41 (R41-2 / R41-3):
no longer the F_s 0 twins; the K0V cases run in the same batch and are compared with these as a
regression record (``ref_s7``)."""
K0V_FLOORS = ("flat", *("fdown3.5", "fup3.5", "roll5.5", "rpB"))
"""Rev. 41 R41-1: verification boundary 5 points x F_s 0 (priority 1, U-S8-8)."""

ML_BASES = 24
ML_EPISODES_PER_BASE = 8
ML_EPISODE_S = 30.0
ML_BASE_MAX_S = 100.0
ML_BRANCH_AFTER_READY_S = 2.0
ML_CHUNK_S = 1.0
ML_SEED = 20261024
ML_EVENT_WEIGHTS = {"hold": 2, "settle": 5, "retract": 2, "probe_repeat": 1}
"""Spec 205.3 (ASSUMPTION ratio). ``probe_repeat`` = ``C2Controller.request_probe()`` (P-S8-2)
from the event time, retried every update until accepted (``busy`` in the READY / lock tail);
attempts and rejections go to ``result.json probe_request``."""


# --- cases ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class S8Case:
    """One S8 case: a bundle-C base case + friction level, event, judge, engine, pairs."""

    case_id: str
    group: str  # K0 K8 K24 A B S E N L CB smoke
    priority: int
    engine: str  # "L2b_NSC" | "L1R"
    base: Any  # s6c.BundleCCase
    fs_kN: float = 0.0
    event: str | None = None  # G4 SS SS9 RE1bF RE1bP RE1c HOLD
    phase_offset_s: float = 0.0
    lock_valve: str = "pilot_check"
    condition: str = "judged"  # "judged" | "sensitivity"
    pair_fs0: str | None = None
    pair_fs0_external: tuple[str, str] | None = None
    """Kept for old batches; no case sets it since rev. 41 (R41-2: same-batch K0V twins)."""
    ref_s7: tuple[str, str] | None = None
    """R41-3: S7 L2b run (batch dir, case) a K0V case is compared with (regression record)."""
    pair_l1: str | None = None
    pair_judge: str | None = None
    """N group: the combined twin (E / K case) of a pressure-only case, or vice versa."""
    notes: tuple[str, ...] = field(default_factory=tuple)
    extra_overrides: tuple[tuple[str, Any], ...] = field(default_factory=tuple)
    """Further plant overrides (ML bases: ``leg_scale``, ``rod_dead_length_m``)."""

    @property
    def scenario(self):
        return self.base.scenario

    @property
    def duration_s(self) -> float:
        return self.base.duration_s

    @property
    def floor(self) -> str:
        return self.scenario.floor

    @property
    def contact(self) -> str:
        return self.scenario.contact

    def event_spec(self) -> dict[str, Any] | None:
        return EVENTS.get(self.event or "")

    def fine_s(self) -> float:
        ev = self.event_spec()
        if not ev or not ev.get("fine"):
            return 0.0
        return float(ev.get("fine_expected_s", st.FINE_EXPECTED_S.get(ev["stage2"], 0.0)))

    def wall_estimate_s(self, core: str = "p") -> float:
        if self.engine == "L1R":
            w = 20.0 + L1_WALL_S_PER_S * self.duration_s
        else:  # C-S8-17: the expected end-rule length, not the scenario duration
            steps = (expected_run_s(self) + s7c.CRAWLER_SETTLE_S) / 1.0e-4
            steps += self.fine_s() / 1.0e-4 * FINE_DT_EXTRA_STEPS_FACTOR
            w = 20.0 + steps * step_us(self.fs_kN, self.lock_valve) * 1e-6
        return w * (E_CORE_FACTOR if core == "e" else 1.0)

    def to_meta(self) -> dict[str, Any]:
        return {"case_id": self.case_id, "group": self.group, "priority": self.priority,
                "engine": self.engine, "fs_kN": self.fs_kN, "event": self.event,
                "event_spec": self.event_spec(), "phase_offset_s": self.phase_offset_s,
                "lock_valve": self.lock_valve, "condition": self.condition,
                "pair_fs0": self.pair_fs0,
                "pair_fs0_external": None if self.pair_fs0_external is None
                else list(self.pair_fs0_external),
                "ref_s7": None if self.ref_s7 is None else list(self.ref_s7),
                "pair_l1": self.pair_l1, "pair_judge": self.pair_judge,
                "contact": self.contact, "floor": self.floor, "level": self.scenario.level,
                "duration_s": self.duration_s, "notes": list(self.notes),
                "base": self.base.to_meta()}


EVENTS: dict[str, dict[str, Any]] = {
    "G4": {"kind": "settle", "leg": "RR", "depth_m": G4_DEPTH_M, "ramp_s": G4_RAMP_S,
           "at": "ready+5", "stage2": "settle_RR", "fine": False},
    "SS": {"kind": "settle", "leg": "RR", "depth_m": SS_DEPTH_M, "ramp_s": SS_RAMP_S,
           "at": "ready+5", "stage2": "settle_RR", "fine": False},
    "SS9": {"kind": "settle", "leg": "RR", "depth_m": SS9_DEPTH_M, "ramp_s": SS_RAMP_S,
            "at": "ready+5", "stage2": "settle_RR", "fine": False},
    "RE1bF": {"kind": "settle", "leg": "RR", "depth_m": st.RE1B_DROP_DEPTH_M,
              "ramp_s": st.RE1B_DROP_RAMP_S, "at": "ready+5", "stage2": "drop_RR_30",
              "fine": True},
    "RE1bP": {"kind": "settle", "leg": "RR", "depth_m": st.RE1B_DROP_DEPTH_M,
              "ramp_s": st.RE1B_DROP_RAMP_S, "at": "probe+0.1", "stage2": "drop_RR_30_probe",
              "fine": True},
    "RE1c": {"kind": "retract", "leg": "RR", "depth_m": RE1C_DEPTH_M,
             "speed_fraction": RE1C_SPEED_FRACTION, "at": "ready+5", "stage2": "retract_RR_25",
             "fine": False},
    "HOLD": {"kind": "hold", "at": None, "stage2": None, "fine": False,
             "ready_hold_s": HOLD_READY_S},
    # --- judged cases of the main ML batch (C-S8-30, spec rev. 48 218.5 / 218.10 / 216.6) ---
    "FS24": {"kind": "settle", "leg": "FR", "depth_m": FS24_DEPTH_M, "ramp_s": FS24_RAMP_S,
             "at": "ready+5", "stage2": "settle_FR_24", "fine": True,
             "fine_expected_s": FS24_FINE_EXPECTED_S, "fine_watch": "all"},
    "SS9P": {"kind": "settle", "leg": "RR", "depth_m": SS9_DEPTH_M, "ramp_s": SS_RAMP_S,
             "at": "ready+5", "stage2": "settle_RR", "fine": False,
             "probe_after": "settled_ready", "end_after_s": SS9P_END_AFTER_S},
    "G4RF": {"kind": "settle", "leg": "RR", "depth_m": G4_DEPTH_M, "ramp_s": G4_RAMP_S,
             "at": "ready+5", "stage2": "settle_RR", "fine": False,
             "rod_fault": {"leg": "FR", "fault": "dropout", "after_ready_s": G4RF_FAULT_AFTER_S}},
}
"""Spec rev. 39 202 E / 203.4 events (depth, ramp, start rule). ``FS24`` / ``SS9P`` / ``G4RF``:
the judged cases of the main ML batch (group ``MLJ``, :data:`MLJ_CASES`)."""


def step_us(fs_kN: float, lock_valve: str = "pilot_check") -> float:
    """Estimated P-core wall per L2b step [us] with the p7e8 pool full (C-S8-19 ⑥, p1r)."""
    if lock_valve == "counterbalance":
        return P_FULL_US_PER_STEP_CB
    return P_FULL_US_PER_STEP_FS if fs_kN > 0.0 else P_FULL_US_PER_STEP_FS0


def _fs_tag(fs: float) -> str:
    return f"Fs{fs:g}"


def _d8_scenario(level: str, floor: str):
    if floor == "fdown3.5":
        return s6c._sc("H4V", "G2-R", level, floor, items=("R", "2", "3", "8"))
    if floor == "fdown3.2":
        return s6c._sc("H4P", "G2-R", level, floor, items=("R", "2", "3", "8"))
    return s6c._d8(level, floor)


def _event_scenario(event: str, contact: str):
    ev = EVENTS[event]
    base = st._length("flat", h4=True, check_s=st.CHECK_S)
    if event == "G4":
        return s6c._sc(f"G4_{contact}", "G4", "top", "flat", contact=contact, event="settle_RR",
                       extra=st.T_SETTLE_EXTRA, items=("6",))
    if event in ("SS", "SS9"):
        return s6c._sc(f"{event}_{contact}", "SS", "top", "flat", contact=contact,
                       event="settle_RR", extra=SS_EXTRA_S, items=("6",))
    if event == "RE1bF":
        return s6c._sc("RE1bF", "RE1b", "top", "flat", contact=contact, event="drop_RR_30",
                       duration_s=base + st.T_RE1BF_EXTRA, items=("6", "7", "GE1"))
    if event == "RE1bP":
        return s6c._sc("RE1bP", "RE1b", "top", "flat", contact=contact,
                       event="drop_RR_30_probe", duration_s=base + st.T_RE1BF_EXTRA,
                       items=("6", "7", "GE1", "Q2"))
    if event == "RE1c":
        return s6c._sc("RE1c", "RE1c", "top", "flat", contact=contact, event="retract_RR_25",
                       duration_s=base + st.T_RE1C_EXTRA, items=("GE1",))
    if event == "HOLD":
        return s6c._sc("HOLD", "HOLD", "top", "flat", contact=contact,
                       extra=ev["ready_hold_s"] + 5.0, items=("R", "3", "8"))
    if event == "FS24":
        # no stage-2 event name: the s6 settlement items assume RR; the FR event is judged by
        # the U-S8-32 rows (verify.s8_control.mlj_rows)
        return s6c._sc(f"FS24_{contact}", "FS", "top", "flat", contact=contact,
                       extra=st.T_SETTLE_EXTRA, items=())
    if event == "SS9P":
        return s6c._sc(f"SS9P_{contact}", "SS", "top", "flat", contact=contact,
                       event="settle_RR", extra=SS_EXTRA_S + SS9P_END_AFTER_S
                       - END_EVENT_AFTER_S, items=("6",))
    if event == "G4RF":
        return s6c._sc(f"H4V_G4RF_{contact}", "G4", "top", "fdown3.5", contact=contact,
                       event="settle_RR", extra=st.T_SETTLE_EXTRA, items=("R", "6"))
    raise ValueError(event)


def _bc(cid: str, sc, **kw):
    return s6c.BundleCCase(cid, "S8", replace(sc, case_id=cid), **kw)


def s8_cases() -> list[S8Case]:
    """The 80 cases of spec rev. 39 202 + 6 CB placeholders + 2 smoke cases."""
    out: list[S8Case] = []

    def add(cid, group, prio, sc, *, engine="L2b_NSC", bkw=None, **kw):
        out.append(S8Case(cid, group, prio, engine, _bc(cid, sc, **(bkw or {})), **kw))

    nine = ("flat", *VERIFY_FLOORS, *OPERATING_FLOORS)
    # K0: operating 4 x F_s 0
    for f in OPERATING_FLOORS:
        add(f"K0_top_{f}_Fs0", "K0", 1, _d8_scenario("top", f), fs_kN=0.0,
            pair_l1=f"L_top_{f}_Fs0")
    # K0V (rev. 41 R41-1, U-S8-8): verification boundary 5 x F_s 0 in the same batch; the S7
    # L2b run is a regression reference (R41-3), not the twin
    for f in K0V_FLOORS:
        add(f"K0V_top_{f}_Fs0", "K0V", 1, _d8_scenario("top", f), fs_kN=0.0,
            ref_s7=S7_FS0_REFS[f])
    # K8 / K24
    for fs, grp, prio in ((8.0, "K8", 1), (2.0, "K24", 2), (4.0, "K24", 2)):
        for f in nine:
            pair = f"K0_top_{f}_Fs0" if f in OPERATING_FLOORS else f"K0V_top_{f}_Fs0"
            add(f"{grp}_top_{f}_{_fs_tag(fs)}", grp, prio, _d8_scenario("top", f), fs_kN=fs,
                pair_fs0=pair,
                pair_judge=f"N_D8_top_{f}_{_fs_tag(fs)}_pressure"
                if fs == 8.0 and f in ("rpB", "fdown3.5") else None)
    # A: middle / bottom
    for lv in ("middle", "bottom"):
        for f in ("rpB", "fdown3.5"):
            for fs in (0.0, 8.0):
                add(f"A_{lv}_{f}_{_fs_tag(fs)}", "A", 2, _d8_scenario(lv, f), fs_kN=fs,
                    pair_fs0=None if fs == 0.0 else f"A_{lv}_{f}_Fs0")
    # B: beta (sensitivity)
    for beta in (0.69, 1.6):
        for f in ("rpB", "fdown3.5"):
            add(f"B_top_{f}_b{beta:g}_Fs8", "B", 2, _d8_scenario("top", f), fs_kN=8.0,
                bkw={"beta_GPa": beta}, condition="sensitivity", pair_fs0=None,
                notes=("beta plant only; controller at beta 1.0 (C-R11)",))
    # S: WIKA normal + calibration
    for f in ("rpB", "fdown3.5"):
        add(f"S_top_{f}_wika_Fs8", "S", 1, _d8_scenario("top", f), fs_kN=8.0,
            bkw={"sensor_model": True}, notes=("WIKA normal grade + zero calibration (U71)",))
    # E: events, combined judge
    for fs in FS_LEVELS_KN:
        for off in (0.0, 0.05):
            cid = f"E_G4_{_fs_tag(fs)}" + ("" if off == 0.0 else f"_ph{off:g}")
            add(cid, "E", 1, _event_scenario("G4", "combined"), fs_kN=fs, event="G4",
                phase_offset_s=off, bkw={"settle_offset_s": off},
                pair_fs0=None if fs == 0.0 else cid.replace(_fs_tag(fs), "Fs0"),
                pair_judge=f"N_G4_{_fs_tag(fs)}_pressure" if off == 0.0 and fs != 2.0 else None)
    for fs in (0.0, 4.0, 8.0):
        add(f"E_SS_{_fs_tag(fs)}", "E", 1, _event_scenario("SS", "combined"), fs_kN=fs,
            event="SS", pair_fs0=None if fs == 0.0 else "E_SS_Fs0",
            pair_judge=f"N_SS_{_fs_tag(fs)}_pressure")
    for ev in ("RE1bF", "RE1bP"):
        for fs in (0.0, 8.0):
            add(f"E_{ev}_{_fs_tag(fs)}", "E", 1, _event_scenario(ev, "combined"), fs_kN=fs,
                event=ev, pair_fs0=None if fs == 0.0 else f"E_{ev}_Fs0",
                pair_judge=f"N_{ev}_{_fs_tag(fs)}_pressure" if ev == "RE1bF" else None)
    add("E_HOLD120_Fs8", "E", 1, _event_scenario("HOLD", "combined"), fs_kN=8.0, event="HOLD",
        pair_judge="N_HOLD120_Fs8_pressure")
    # N: item 9 (pressure-only + combined additions), 203.4
    for fs in (0.0, 4.0, 8.0):
        add(f"N_SS_{_fs_tag(fs)}_pressure", "N", 3, _event_scenario("SS", "pressure"), fs_kN=fs,
            event="SS", pair_judge=f"E_SS_{_fs_tag(fs)}")
    add("N_SS9_Fs8_pressure", "N", 3, _event_scenario("SS9", "pressure"), fs_kN=8.0,
        event="SS9", pair_judge="N_SS9_Fs8_combined")
    add("N_SS9_Fs8_combined", "N", 3, _event_scenario("SS9", "combined"), fs_kN=8.0,
        event="SS9", pair_judge="N_SS9_Fs8_pressure")
    for fs in (0.0, 4.0, 8.0):
        add(f"N_G4_{_fs_tag(fs)}_pressure", "N", 3, _event_scenario("G4", "pressure"), fs_kN=fs,
            event="G4", pair_judge=f"E_G4_{_fs_tag(fs)}")
    for fs in (0.0, 8.0):
        add(f"N_RE1bF_{_fs_tag(fs)}_pressure", "N", 3, _event_scenario("RE1bF", "pressure"),
            fs_kN=fs, event="RE1bF", pair_judge=f"E_RE1bF_{_fs_tag(fs)}")
    for fs in (0.0, 8.0):
        add(f"N_RE1c_{_fs_tag(fs)}_combined", "N", 3, _event_scenario("RE1c", "combined"),
            fs_kN=fs, event="RE1c", notes=("offline J_P / J_C only (203.4)",))
    add("N_HOLD120_Fs8_pressure", "N", 3, _event_scenario("HOLD", "pressure"), fs_kN=8.0,
        event="HOLD", pair_judge="E_HOLD120_Fs8")
    for f in ("rpB", "fdown3.5"):
        add(f"N_D8_top_{f}_Fs8_pressure", "N", 3,
            replace(_d8_scenario("top", f), contact="pressure"), fs_kN=8.0,
            pair_judge=f"K8_top_{f}_Fs8")
    # L: L1-R twins of K0 (F_s 0)
    for f in OPERATING_FLOORS:
        add(f"L_top_{f}_Fs0", "L", 3, _d8_scenario("top", f), engine="L1R", fs_kN=0.0,
            notes=("L1-R twin (bundle-C job, beta 1.0); needs the L1 snapshot (snaps)",))
    # CB placeholders (206)
    for name, sc, ev in (("H4V_fdown3.5", _d8_scenario("top", "fdown3.5"), None),
                         ("G4", _event_scenario("G4", "combined"), "G4"),
                         ("RE1bF", _event_scenario("RE1bF", "combined"), "RE1bF")):
        for fs in (0.0, 8.0):
            add(f"CB_{name}_{_fs_tag(fs)}", "CB", 4, sc, fs_kN=fs, event=ev,
                lock_valve="counterbalance", notes=("spec 206 placeholder",))
    # MLJ: judged cases of the main ML batch (C-S8-30; U-S8-32 / 35, C-S8-24, C-S8-29)
    for fs in (0.0, 8.0):
        add(f"MLJ_FS24_{_fs_tag(fs)}", MLJ_GROUP, 5, _event_scenario("FS24", "combined"),
            fs_kN=fs, event="FS24",
            notes=("U-S8-32 front fast settlement FR 24 mm / 0.3 s (ML00_ep5), event legs "
                   "FR + RL vs adjacent FL / RR",))
        add(f"MLJ_SS9P_{_fs_tag(fs)}", MLJ_GROUP, 5, _event_scenario("SS9P", "combined"),
            fs_kN=fs, event="SS9P",
            notes=("C-S8-24 R45-4: SS9 RR 9 mm / 20 s, then request_probe at READY after "
                   "the ramp",))
        add(f"MLJ_K0V_fdown3.5_G4RF_{_fs_tag(fs)}", MLJ_GROUP, 5,
            _event_scenario("G4RF", "combined"), fs_kN=fs, event="G4RF",
            notes=("C-S8-29 / U-S8-33: FR rod-sensor dropout at READY + 2 s + G4 RR at "
                   "READY + 5 s, nose down 3.5 deg top (K0V point)",))
    # smoke (F_s 0, short)
    add("smoke_E_G4_Fs0", "smoke", 0, _event_scenario("G4", "combined"), fs_kN=0.0, event="G4")
    add("smoke_K0_top_rpBop_Fs0", "smoke", 0, _d8_scenario("top", "rpBop"), fs_kN=0.0)
    ids = [c.case_id for c in out]
    if len(ids) != len(set(ids)):
        dup = sorted({i for i in ids if ids.count(i) > 1})
        raise RuntimeError(f"duplicate S8 case ids {dup}")
    return out


def case_table() -> dict[str, S8Case]:
    return {c.case_id: c for c in s8_cases()}


MAIN_GROUPS = ("K0", "K0V", "K8", "K24", "A", "B", "S", "E", "N", "L")


def case_set(name: str) -> list[S8Case]:
    cases = s8_cases()
    main = [c for c in cases if c.group in MAIN_GROUPS]
    p1 = [c for c in main if c.priority == 1]
    sets = {
        "p1": p1,
        # C-S8-18 (spec rev. 43 213.6 / U-S8-12): priority 1 again + the pressure-only D8 twin of
        # K8 rpB (37 cases)
        "p1r": p1 + [c for c in main if c.case_id in P1R_EXTRA],
        "p2": [c for c in main if c.priority == 2],
        "p3": [c for c in main if c.priority == 3],
        "rest": [c for c in main if c.priority in (2, 3)],
        "all": main,
        "cb": [c for c in cases if c.group == "CB"],
        "smoke": [c for c in cases if c.group == "smoke"],
        "mlj": [c for c in cases if c.group == MLJ_GROUP],
        "mlj_c29": [c for c in cases if c.group == MLJ_GROUP and c.event == "G4RF"],
    }
    if name not in sets:
        raise KeyError(f"unknown set {name!r}; sets {tuple(sets)}")
    return sets[name]


SET_NAMES = ("p1", "p1r", "p2", "p3", "rest", "all", "cb", "smoke", "mlj", "mlj_c29")
MLJ_GROUP = "MLJ"
"""Judged cases of the main ML batch (6): U-S8-32 front fast settlement (FS24) x F_s 0 / 8,
C-S8-24 R45-4 (SS9P) x F_s 0 / 8, C-S8-29 rod-sensor fault + G4 (G4RF) x F_s 0 / 8.
``mlj_c29`` = the two C-S8-29 cases alone (they need P-S8-13)."""
P1R_EXTRA = ("N_D8_top_rpB_Fs8_pressure",)
"""Spec rev. 43 213.6 step 3: the 1st-priority re-run = 36 + N_D8 rpB pressure-only = 37."""


# --- plant parameters ------------------------------------------------------------------------


def l2b_beta_overrides(level: str, beta_GPa: float) -> dict[str, Any]:
    """L2b plant at another beta: ``actuator.oil_bulk_modulus_eff_Pa`` and the derived check key
    ``actuator.L2b_NSC.axial_stiffness.operating_point_N_m`` (recomputed with the same formula,
    ``params._read_l2b_nsc``). Damping stays at the YAML values (ASSUMPTION, as bundle C)."""
    if beta_GPa == 1.0:
        return {}
    from outrigger_sim.params import LEG_ORDER, axial_stiffness_N_m, load_params

    p = load_params(level=level, model="L2b_NSC")
    a = p.l2b.actuator
    e_op = p.contact.rigid_floor.L1.operating_extension_m
    beta = float(beta_GPa) * 1e9
    op = {name: axial_stiffness_N_m(e_op[i], bulk_modulus_Pa=beta, head_area_m2=a.head_area_m2[i],
                                    dead_length_m=a.oil_dead_length_m, k_rod_N_m=a.k_rod_N_m[i],
                                    k_frame_N_m=a.frame_stiffness_N_m,
                                    k_concrete_N_m=a.k_concrete_N_m)
          for i, name in enumerate(LEG_ORDER)}
    return {"actuator.oil_bulk_modulus_eff_Pa": beta,
            "actuator.L2b_NSC.axial_stiffness.operating_point_N_m": op}


def l2b_params(case: S8Case):
    """(plant params, controller params, overrides, plant meta)."""
    from outrigger_sim.chrono import s8_plant_adapter as plant
    from outrigger_sim.params import load_params

    level = case.scenario.level
    yaml = load_params(level=level, model="L2b_NSC")
    over: dict[str, Any] = {}
    over.update(plant.seal_friction_overrides(yaml, case.fs_kN * 1e3))
    over.update(plant.lock_valve_overrides(yaml, case.lock_valve))
    over.update(l2b_beta_overrides(level, case.base.beta_GPa))
    over.update(dict(case.extra_overrides))
    params = load_params(level=level, model="L2b_NSC", overrides=over or None) if over else yaml
    params_ctrl = load_params(level=level)  # C-R11: controller at the YAML beta 1.0
    return params, params_ctrl, over


# --- per-period S8 record ----------------------------------------------------------------------


class S8Series(s6c.R8Series):
    """R8 series + the combined-judge context of each 10 Hz period (C-S8-2 / P-S8-1 input):
    ``F_band_N`` (``C2Controller.seal_band_N``), ``leg_band_N`` (per-leg bands, private
    ``_leg_seal_bands_N`` when present), ``F_lower_N`` (the controller's lower load estimate
    ``_state.last_forces.lower``, NaN when absent), ``F_hat_N`` = delivered ``p_h A_p - p_r
    A_ann`` (reading after the sensor model)."""

    FIELDS = ("F_band_N", "leg_band_N", "F_lower_N", "F_hat_N", "F_nominal_N", "F_lower_est_N")

    def __init__(self, model, c2, head_area_m2, annulus_area_m2) -> None:
        super().__init__(model, c2)
        import numpy as np

        self.ctrl = c2
        for k in self.FIELDS:
            self.rows[k] = []
        self._ap = np.asarray(head_area_m2, float)
        self._aa = np.asarray(annulus_area_m2, float)

    def __call__(self, meas, command) -> None:
        import numpy as np

        super().__call__(meas, command)
        c2 = getattr(self.ctrl, "inner", self.ctrl)
        r = self.rows
        r["F_band_N"].append(self._num(getattr(c2, "seal_band_N", None)))
        bands = getattr(c2, "_leg_seal_bands_N", None)
        try:
            bands = None if bands is None else np.asarray(bands(), float).reshape(4)
        except Exception:  # noqa: BLE001 - controller without per-leg bands
            bands = None
        r["leg_band_N"].append(np.full(4, np.nan) if bands is None else bands)
        forces = getattr(getattr(c2, "_state", None), "last_forces", None)
        lf = getattr(forces, "lower", None)
        nan4 = np.full(4, np.nan)
        r["F_lower_N"].append(nan4 if lf is None else np.asarray(lf, float))
        nom = getattr(forces, "nominal", None)
        r["F_nominal_N"].append(nan4 if nom is None else np.asarray(nom, float))
        est = nan4
        if lf is not None and callable(getattr(c2, "_load_estimate_N", None)):
            est = np.asarray(c2._load_estimate_N(np.asarray(lf, float)), float)
        r["F_lower_est_N"].append(est)
        p_r = meas.rod_pressure_Pa
        p_r = np.zeros(4) if p_r is None else np.asarray(p_r, float)
        r["F_hat_N"].append(np.asarray(meas.head_pressure_Pa, float) * self._ap - p_r * self._aa)

    def save(self, path: Path) -> dict[str, Any]:
        import numpy as np

        info = super().save(path.with_name(s6c.R8_SERIES_NAME))
        fields = [*self.FIELDS, "issued_u"]
        np.savez_compressed(path, t=np.asarray(self.rows["t"]),
                            phase=np.asarray(self.rows["phase"], dtype="U16"),
                            **{k: np.asarray(self.rows[k]) for k in fields})
        info["s8_series"] = {
            "file": path.name, "fields": fields,
            "F_hat": "delivered p_h A_p - p_r A_ann (sensor model applied, before the zero "
                     "calibration)",
            "F_lower": "reading lower bound = controller _state.last_forces.lower (calibrated, "
                       "E-6 deduction, NO seal band; NaN = absent)",
            "F_nominal": "calibrated reading = controller last_forces.nominal (C-S8-16 ①)",
            "F_lower_est": "spec-199 lower bound F_hat_cal - F_band,i = controller "
                           "_load_estimate_N(last_forces.lower) (C-S8-16 ①)"}
        return info


S8_SERIES_NAME = "s8_series.npz"


class TwistScaleHistory:
    """C-S8-19 ⑤ (spec rev. 44 214.5 question 3-3): the twist / guard gain stiffness scale after
    every finished probe round. Called once per control period after the controller update; when
    ``c2.probe_history`` has grown, the ``twist_gain_stiffness`` block of ``c2.meta()`` (public)
    is stored with the control time relative to ``t0`` (``result.json
    twist_stiffness_history``, read by ``verify.s8_control.twist_history``)."""

    def __init__(self, c2, t0: float) -> None:
        self.c2 = c2
        self.t0 = float(t0)
        self.seen = len(getattr(c2, "probe_history", ()) or ())
        self.rows: list[dict[str, Any]] = []

    def __call__(self, t_s: float) -> None:
        n = len(getattr(self.c2, "probe_history", ()) or ())
        if n == self.seen:
            return
        self.seen = n
        tw = (self.c2.meta() or {}).get("twist_gain_stiffness") or {}
        self.rows.append({"round": n - 1, "t_s": float(t_s) - self.t0,
                          "scale_in_use": tw.get("scale_in_use"),
                          "measured_scale": tw.get("measured_scale"),
                          "raw_ratio": tw.get("raw_ratio"),
                          "grounded_leg_count": tw.get("grounded_leg_count"),
                          "source": "runner (c2.meta() twist_gain_stiffness at the round end)"})


# --- L2b job ----------------------------------------------------------------------------------


def crawler_meta(model) -> dict[str, Any]:
    """R40-6 / C-S8-8."""
    raw = getattr(model, "crawler_contact", None)
    mode = raw.get("model") if isinstance(raw, dict) else raw
    contact = {"rigid": "nsc_rigid", "compliant": "nsc_compliant"}.get(str(mode), "nsc_rigid")
    passed = getattr(model, "crawler_check_passed", CRAWLER_CHECK_PASSED)
    return {"crawler_contact": contact, "crawler_check_passed": passed,
            "crawler_contact_model": raw,
            "source": "L2bModel.crawler_contact['model'] (rigid / compliant, U-S8-L3) and "
                      "crawler_check_passed (S8-L4) or CRAWLER_CHECK_PASSED; absent = nsc_rigid"}


def build_l2b(case: S8Case, *, patch_legs: tuple[str, ...] = ()):
    """Model + engine + start (crawler settle) of an L2b S8 case."""
    from outrigger_sim.chrono import s8_plant_adapter as plant
    from outrigger_sim.chrono.l2b_engine import L2bEngine
    from outrigger_sim.chrono.l2b_ground_patch import attach_ground_patches
    from outrigger_sim.chrono.l2b_model import L2bModel

    sc = case.scenario
    params, params_ctrl, over = l2b_params(case)
    pose, floor_pose, normal = s7c.l2b_crawler_start(params, sc.floor)
    mode = os.environ.get(CRAWLER_ENV, "yaml").strip().lower()
    kw = {} if mode in ("", "yaml") else {"crawler_contact": mode}
    model = L2bModel(params, pose=pose, extensions_m=(0.0,) * 4, start="hanging", crawler=True,
                     floor_pose=floor_pose, **kw)
    patches = attach_ground_patches(model, patch_legs) if patch_legs else None
    plant_meta = plant.check_model(model, case.fs_kN * 1e3, case.lock_valve)
    model.actuator.configure_valve(tau_s=case.base.tau_v_s, amp_ramp=case.base.amp_ramp,
                                   amp_ramp_s=s6c.AMP_RAMP_S)
    return model, patches, params, params_ctrl, over, plant_meta, (pose, floor_pose, normal)


SETTLE_SUPPORT_MIN = 0.5
"""Start guard: after the crawler settle the crawler normal force (0.1 s mean) must carry at
least this share of the weight; otherwise the start is refused (2026-10-24 smoke: the compliant
crawler of the YAML at that time let the machine fall through the floor)."""


def check_settle(start: dict[str, Any]) -> None:
    cn, w = start.get("crawler_normal_mean_N"), start.get("weight_along_normal_N")
    if cn is None or w is None or not cn >= SETTLE_SUPPORT_MIN * w:
        raise RuntimeError(f"crawler settle does not carry the machine: crawler normal {cn} N, "
                           f"weight {w} N, body speed {start.get('max_speed_m_s')} m/s "
                           f"(crawler mode {os.environ.get(CRAWLER_ENV, 'yaml')})")


LEG_NAMES = ("FL", "FR", "RL", "RR")


class RodFaultInjection:
    """C-S8-29 controller wrapper: from ``t_start_s`` on (set by :meth:`arm`) the controller
    reads the measurements through ``sensors.hydraulic.FaultyRodSensor`` (one leg's rod-side
    reading stuck / offset / NaN); the run records (``observe``) keep the unfaulted delivery.
    Delegates ``period_s`` / ``reset`` / ``meta`` like ``s6_stage2.ForcedRetract``."""

    def __init__(self, inner, *, leg: int, fault: str, value_Pa: float = 0.0) -> None:
        from outrigger_sim.sensors.hydraulic import RodSensorFault

        self.inner = inner
        self.leg = int(leg)
        self.fault = RodSensorFault(fault)
        self.value_Pa = float(value_Pa)
        self.t_start_s: float | None = None
        self._sensor = None
        self.applied = 0
        self.no_rod_reading = 0

    @property
    def period_s(self) -> float:
        return self.inner.period_s

    def arm(self, t_start_s: float) -> None:
        from outrigger_sim.sensors.hydraulic import FaultyRodSensor

        self.t_start_s = float(t_start_s)
        self._sensor = FaultyRodSensor(self.leg, self.fault, self.value_Pa, self.t_start_s)

    def reset(self) -> None:
        self.inner.reset()

    def update(self, measurements):
        if self._sensor is not None and measurements.t_s >= self.t_start_s:
            if measurements.rod_pressure_Pa is None:
                self.no_rod_reading += 1
            else:
                self.applied += 1
            measurements = self._sensor.apply(measurements)
        return self.inner.update(measurements)

    def meta(self) -> dict[str, Any]:
        return {"wrapper": "RodFaultInjection", "leg": LEG_NAMES[self.leg],
                "fault": str(self.fault), "value_Pa": self.value_Pa,
                "t_start_s": self.t_start_s, "applied_periods": self.applied,
                "periods_without_rod_reading": self.no_rod_reading,
                "source": "sensors.hydraulic.FaultyRodSensor on the controller input"}


REAPPROACH_VARIANTS = ("rt", "f1only")
"""C-S8-36 (spec rev. 52 230, U-S8-50): ``rt`` = the code's R8 preset (P-S8-16 rule RT on) +
the F1 plant reading fix; ``f1only`` = the same with the RT keys of
``LiftedReapproachSettings`` at their "off" values (``retrigger_window_s`` and
``opposite_window_s`` None; bundle B). The F1 fix is in the plant code
(``hydraulics/l2b_rod_side.py``) and has no switch."""
RT_KEYS = ("retrigger_window_s", "retrigger_speed_factor", "opposite_window_s",
           "opposite_strong_level_N", "opposite_strong_samples")


def with_reapproach_variant(config, variant: str | None):
    """C-S8-36: the controller config of a re-approach variant (:data:`REAPPROACH_VARIANTS`;
    None / ``rt`` = unchanged). ``rt`` checks that the preset has RT on."""
    if variant is None:
        return config
    if variant not in REAPPROACH_VARIANTS:
        raise ValueError(f"unknown re-approach variant {variant!r}; {REAPPROACH_VARIANTS}")
    lr = config.r8.lifted_reapproach
    if variant == "rt":
        if lr.retrigger_window_s is None or lr.opposite_window_s is None:
            raise RuntimeError(f"variant rt but the controller preset has RT off: {lr!r}")
        return config
    # every RT key at its class default ("off", P-S8-16 229 #1): the windows None make the rule
    # inert; the factor / level / samples defaults make the settings equal to the pickled ones
    cls = type(lr)
    off = replace(lr, **{k: getattr(cls, k) for k in RT_KEYS})
    return replace(config, r8=replace(config.r8, lifted_reapproach=off))


def reapproach_settings_meta(controller) -> dict[str, Any] | None:
    """The lifted re-approach settings of a controller (all fields, plain values)."""
    import dataclasses

    c2 = getattr(controller, "inner", controller)
    lr = getattr(getattr(getattr(c2, "config", None), "r8", None), "lifted_reapproach", None)
    if lr is None:
        return None
    return {f.name: (getattr(lr, f.name).value if hasattr(getattr(lr, f.name), "value")
                     else getattr(lr, f.name)) for f in dataclasses.fields(lr)}


def _controller(case: S8Case, params_ctrl, params_plant, variant: str | None = None):
    """C2 controller of an L2b S8 case.

    ``params_ctrl`` is the L1 YAML (C-R11: controller at beta 1.0) and has no
    ``l2b.counterbalance``; the CB law of the lock-valve diagnosis (P-S8-11, U-S8-23) therefore
    comes from the L2b plant params ``params_plant`` (from :func:`build_l2b`). Pilot-check cases
    do not touch the config (bit-identical to the S7 / pre-P-S8-11 path). ``variant``: C-S8-36
    re-approach variant (:func:`with_reapproach_variant`; None = the preset)."""
    from outrigger_sim.control.c2 import C2Controller

    config, settle_meta = s7c.apply_settle_map(s6c.controller_config(params_ctrl, case.base),
                                               "L2b_NSC", case.scenario.level)
    if case.lock_valve == "counterbalance":
        l2b = params_plant.l2b
        if l2b is None or l2b.lock_valve != "counterbalance" or l2b.counterbalance is None:
            raise RuntimeError(f"{case.case_id}: CB case but the plant params have lock_valve "
                               f"{getattr(l2b, 'lock_valve', None)!r} / no actuator.counterbalance")
        config = config.with_lock_valve("counterbalance", l2b.counterbalance)
    config = with_lock_window_tau(config, case.base.tau_v_s)
    config = with_reapproach_variant(config, variant)
    return C2Controller.from_params(params_ctrl, config), config, settle_meta


LOCK_WINDOW_TAU_KEY = "lock_window_valve_tau_s"


def with_lock_window_tau(config, tau_v_s: float):
    """Spec rev. 48 218.12 / U-R8-9 ③: the P-S8-13 lock window uses the plant valve lag of the
    case (``case.base.tau_v_s``, the value ``build_l2b`` gives ``configure_valve``) instead of
    the ``TwoPressureSettings`` default (0.1 s; equal values leave the config unchanged, so the
    0.1 s cases stay bit-identical). Config without the key (pre-P-S8-13 code): unchanged."""
    import dataclasses

    tp = config.two_pressure
    names = {f.name for f in dataclasses.fields(tp)}
    if LOCK_WINDOW_TAU_KEY not in names or getattr(tp, LOCK_WINDOW_TAU_KEY) == float(tau_v_s):
        return config
    return replace(config, two_pressure=replace(tp, **{LOCK_WINDOW_TAU_KEY: float(tau_v_s)}))


def job_l2b_s8(case: S8Case, case_dir: Path, *, duration_s: float | None = None):
    """Run one L2b S8 case (module docstring). Returns (summary, run_meta)."""
    import numpy as np

    from outrigger_sim.chrono.l2b_pad_record_s8 import L2bPadRecorderS8
    from outrigger_sim.control.c2 import C2Phase
    from outrigger_sim.record import make_run_meta, save_record
    from outrigger_sim.runner import DtSchedule, run_closed_loop
    from outrigger_sim.sensors.hydraulic import LegSensorConfig
    from outrigger_sim.sensors.imu import imu_config_for_grade
    from outrigger_sim.sensors.suite import SensorSuite
    from outrigger_sim.verify.reference import load_references
    from outrigger_sim.verify.s6_bundle_c import classify_warning

    bcase = case.base
    sc = bcase.scenario
    ev = case.event_spec()
    patch_legs = (ev["leg"],) if ev and ev["kind"] == "settle" else ()
    model, patches, params, params_ctrl, over, plant_meta, (pose, floor_pose, normal) = \
        build_l2b(case, patch_legs=patch_legs)
    start = s7c.settle_l2b(model, s7c.CRAWLER_SETTLE_S)
    check_settle(start)
    from outrigger_sim.chrono.l2b_engine import L2bEngine

    t0 = float(model.system.GetChTime())
    engine = L2bEngine(model, imu_method="chrono_point")
    leg_sensors = st.leg_sensor_config_for(sc, t0) if bcase.sensor_model else LegSensorConfig()
    suite = SensorSuite(imu_config_for_grade(sc.grade, sample_period_s=s6c.IMU_SAMPLE_PERIOD_S),
                        leg_sensors, seed=sc.seed)
    c2, config, settle_meta = _controller(case, params_ctrl, params)
    controller = c2
    forced = None
    if ev and ev["kind"] == "retract":
        forced = st.ForcedRetract(c2, leg=3, depth_m=ev["depth_m"],
                                  speed_m_s=ev["speed_fraction"] * params.actuator.max_speed_m_s)
        controller = forced
    rod_fault = None
    if ev and ev.get("rod_fault"):  # C-S8-29: armed at first READY + after_ready_s
        rf = ev["rod_fault"]
        rod_fault = RodFaultInjection(controller, leg=LEG_NAMES.index(rf["leg"]),
                                      fault=rf["fault"], value_Pa=float(rf.get("value_Pa", 0.0)))
        controller = rod_fault
    probe_req = {"attempts": 0, "rejected": [], "accepted_t_s": None, "rule": None} \
        if ev and ev.get("probe_after") else None
    dt_fine = float(params.get("simulation.dt_transition_s"))
    schedule = DtSchedule(model.dt_s, config.period_s) if ev and ev.get("fine") else None
    pads = L2bPadRecorderS8(engine, sample_s=s7c.PAD_RECORD_S)
    sat_rec = s6c.SaturationRecorder(model, t0)
    series = S8Series(model, c2, model.actuator.head_area_m2,
                      params.l2b.rod_side.annulus_area_m2)
    twist_hist = TwistScaleHistory(c2, t0)
    phases: list[tuple[float, str]] = []
    probe_intervals: list[dict[str, Any]] = []
    state: dict[str, Any] = {"ready_t": None, "probe_t": None, "event_t": None,
                             "fine_open_t": None, "contact_since": None, "fine_capped": False,
                             "lifted_seen": False, "scheduled": False}
    leg_i = 3 if not ev or ev.get("leg") not in LEG_NAMES else LEG_NAMES.index(ev["leg"])
    watch_all = bool(ev and ev.get("fine_watch") == "all")

    def schedule_event(t_start: float, dt_lead: float) -> None:
        patches.schedule(t_start, ev["depth_m"], ev["ramp_s"], dt_s=dt_lead)
        state["scheduled"] = True
        state["event_t"] = t_start

    def fine_window(t: float) -> None:
        if schedule is None:
            return
        evt = state["event_t"]
        if evt is not None and state["fine_open_t"] is None and not schedule.is_open \
                and t >= evt - st.FINE_PRE_S - 1e-9 and len(schedule.segments) == 1:
            schedule.open(t, dt_fine, reason=f"{case.event} transition")
            state["fine_open_t"] = t
        if not schedule.is_open:
            return
        fn = engine.truth().F_contact_n_N
        n_leg = float(np.min(fn)) if watch_all else float(fn[leg_i])
        if n_leg > 0.0:
            if state["contact_since"] is None:
                state["contact_since"] = t
        else:
            state["contact_since"] = None
            state["lifted_seen"] = True
        since = state["contact_since"]
        if evt is not None and t >= evt + st.FINE_PRE_S and since is not None \
                and t - since >= st.FINE_HOLD_S - 1e-9:
            schedule.close(t, reason="leg in contact for FINE_HOLD_S after the event")
        elif t - state["fine_open_t"] >= st.FINE_MAX_S - 1e-9:
            schedule.close(t, reason="FINE_MAX_S cap")
            state["fine_capped"] = True

    def observe(meas, command):
        series(meas, command)
        twist_hist(meas.t_s)
        ph = c2.phase
        if not phases or phases[-1][1] != ph.value:
            if phases and phases[-1][1] == "probe" and probe_intervals:
                probe_intervals[-1].update(t_end_s=meas.t_s - t0, next_phase=ph.value)
            if ph.value == "probe":
                probe_intervals.append({"t_start_s": meas.t_s - t0})
            phases.append((meas.t_s - t0, ph.value))
        if ph is C2Phase.READY and state["ready_t"] is None:
            state["ready_t"] = meas.t_s
        if ph is C2Phase.PROBE and state["probe_t"] is None:
            state["probe_t"] = meas.t_s
        if ev and not state["scheduled"]:
            if ev["at"] == "probe+0.1" and state["probe_t"] is not None:
                schedule_event(state["probe_t"] + st.RE1BP_DELAY_S, dt_fine)
            elif ev["at"] == "ready+5" and state["ready_t"] is not None:
                t_ev = state["ready_t"] + 5.0 + case.phase_offset_s
                if ev["kind"] == "settle":
                    schedule_event(t_ev, dt_fine if ev.get("fine") else model.dt_s)
                elif ev["kind"] == "retract":
                    forced.t_start = t_ev
                    state["scheduled"] = True
                    state["event_t"] = t_ev
        if rod_fault is not None and rod_fault.t_start_s is None \
                and state["ready_t"] is not None:
            rod_fault.arm(state["ready_t"] + float(ev["rod_fault"]["after_ready_s"]))
        if probe_req is not None:
            request_probe_after_settlement(meas.t_s, ph)
        fine_window(meas.t_s)

    def request_probe_after_settlement(t: float, ph) -> None:
        """C-S8-24: ``C2Controller.request_probe()`` once the settlement ramp is over and the
        controller is in READY again, retried every update until accepted (as the ML
        ``probe_repeat`` episodes)."""
        evt = state["event_t"]
        if probe_req["accepted_t_s"] is not None or evt is None \
                or t < evt + float(ev["ramp_s"]) - 1e-9 or ph is not C2Phase.READY:
            return
        probe_req["rule"] = ("request_probe from the first READY update after the settlement "
                             "ramp end, every update until accepted")
        probe_req["attempts"] += 1
        if c2.request_probe():
            probe_req["accepted_t_s"] = t - t0
        else:
            reason = next((str(e) for e in reversed(c2.events)
                           if "probe_request_rejected" in str(e)), "rejected")
            probe_req["rejected"].append({"t_s": t - t0, "event": reason})

    # C-S8-17 end rule (check runs with an explicit short duration keep the fixed length)
    rule = end_rule(case)
    use_rule = duration_s is None
    run_upper_s = rule["upper_s"] if use_rule else duration_s
    state["last_t"] = None

    def end_target_abs() -> float | None:
        anchor = state["ready_t"] if rule["anchor"] == "ready" else state["event_t"]
        return None if anchor is None else anchor + rule["after_s"]

    def stop_now() -> bool:
        target = end_target_abs()
        return target is not None and state["last_t"] is not None \
            and state["last_t"] >= target - 1e-9

    def observe_end(meas, command):
        observe(meas, command)
        state["last_t"] = meas.t_s

    c2_meta = st.c2_config_meta(config)
    expect = st.expected_reanchor(sc, c2_meta["reanchor_direction"])
    bundle = {**bcase.to_meta(), "param_overrides": {k: v for k, v in over.items()},
              "controller_param_overrides": {},
              "controller_params_beta_GPa": s6c.CONTROLLER_BETA_GPA,
              "valve": model.actuator.valve_meta(),
              "imu_sample_period_s": s6c.IMU_SAMPLE_PERIOD_S,
              "leg_sensors": "WIKA error model" if bcase.sensor_model
              else "ideal (LegSensorConfig())",
              "c2_implementation": s6c.c2_implementation_status(c2),
              "rev43_controller": {  # U-S8-9 (P-S8-5) / U-S8-11 (P-S8-6), from the R8 preset
                  "reapproach_load_fraction_of_F_min":
                      config.r8.lifted_reapproach.load_fraction_of_F_min,
                  **{k: getattr(config.r8, k, None) for k in (
                      "touch_free_air_min_travel_m", "touch_free_air_min_samples",
                      "touch_seen_samples")}},
              "controller_timing": c2.meta().get("timing"),
              "params_sha256": params.sha256, "params_sha256_controller": params_ctrl.sha256,
              "saturation_stop_s": model.actuator.saturation_stop_s}
    s8_meta = {**case.to_meta(), **crawler_meta(model), "plant": plant_meta,
               "ground_patches": None if patches is None else patches.meta(),
               "controller_settle_map_meta": settle_meta,
               "lifted_reapproach": reapproach_settings_meta(c2)}  # C-S8-36
    settings = {**asdict(sc), "snapshot": None, "start_t_s": t0, **c2_meta,
                "reanchor_expected": expect, "bundle_c": bundle,
                "s7c": {"engine": "L2b_NSC", "case_id": case.case_id,
                        "controller_settle_map": "identity"},
                "s8": s8_meta,
                "l2b_start": {"floor_normal_world": normal.tolist(),
                              "floor_pose": asdict(floor_pose), "body_pose": asdict(pose),
                              "settle": start},
                "leg_sensors": leg_sensors.to_meta(), "controller_config": str(config)}
    run_meta = make_run_meta(params, engine.meta(), scenario=f"S8C_{case.case_id}",
                             scenario_settings=s6c._plain(settings), sensors=suite.setup(),
                             reference_sha256=load_references().sha256_by_file())
    wall0 = time.perf_counter()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        res = run_closed_loop(engine, controller, suite, run_upper_s,
                              run_meta=run_meta, on_control=observe_end,
                              command_delay_periods=0,
                              command_offset_s=bcase.command_offset_s,
                              step_hook=st._chain_hooks(pads, sat_rec),
                              dt_schedule=schedule,
                              placement=st.run_placement(),
                              stop_when=stop_now if use_rule else None)
    wall = time.perf_counter() - wall0
    t_end_rel = float(engine.time_s) - t0
    target = end_target_abs()
    stopped = bool(res.meta.get("stopped_early", False))
    s8_end = {**rule, "applied": use_rule, "upper_used_s": run_upper_s,
              "anchor_t_s": None if target is None else target - rule["after_s"] - t0,
              "target_t_s": None if target is None else target - t0,
              "end_t_s": t_end_rel, "stopped_at_target": stopped,
              "timeout": bool(use_rule and not stopped),
              "final_phase": phases[-1][1] if phases else None,
              "phase_lengths": phase_lengths(phases, t_end_rel)}
    observed = []
    for w in caught:
        cls = classify_warning(str(w.message), w.category.__name__, bcase.beta_GPa)
        cls.update(filename=Path(str(w.filename)).name, lineno=w.lineno)
        observed.append(cls)
    bundle["warnings"] = observed
    bundle["warnings_unexpected_count"] = sum(1 for w in observed if not w["expected"])
    bundle["saturation_steps"] = sat_rec.meta()
    save_record(res.record, case_dir / "record")
    pads.save(case_dir / "pads.npz")
    series_info = series.save(case_dir / S8_SERIES_NAME)
    events = [str(e) for e in c2.events]
    probes = [[asdict(r) if hasattr(r, "__dataclass_fields__") else str(r) for r in rnd]
              for rnd in c2.probe_history]
    (case_dir / "probe_history.json").write_text(json.dumps(probes, indent=1, default=str),
                                                 "utf-8")
    (case_dir / "controller_events.json").write_text(json.dumps(events, indent=1), "utf-8")
    s_motor = np.asarray(res.record.arrays["s_motor"])
    stroke_hi = float(params.legs[0].extension_range_m[1])
    ctl_meta = c2.meta()
    reanchor = c2.reanchor_outcome
    p_floor = np.asarray(model.floor_point_world_m, dtype=float)
    summary = {
        "case": case.case_id, "settings": settings, "phases": phases,
        "events_count": len(events),
        "acceptance": {"target_code": None if c2.target_code is None else str(c2.target_code),
                       "crawler_attitude_deg": None if c2.crawler_attitude_rad is None
                       else [math.degrees(a) for a in c2.crawler_attitude_rad],
                       "floor_true_deg": st.FLOORS[sc.floor],
                       "controller_settle_map": settle_meta},
        "h4": {"enabled": sc.h4, "outcome": None if reanchor is None else str(reanchor),
               "expected": expect, "direction": ctl_meta.get("reanchor_direction")},
        "c2": c2_meta,
        "stroke": {"max_m": s_motor.max(axis=0), "min_m": s_motor.min(axis=0),
                   "margin_to_end_m": stroke_hi - s_motor.max(axis=0)},
        "controller_meta": ctl_meta,
        "twist_stiffness_history": twist_hist.rows,
        "floor_plane": {"normal_world": normal.tolist(), "offset_m": float(normal @ p_floor)},
        "ready_t_s": None if state["ready_t"] is None else state["ready_t"] - t0,
        "probe_intervals": probe_intervals,
        "first_probe_t_s": None if state["probe_t"] is None else state["probe_t"] - t0,
        "event_t_s": None if state["event_t"] is None else state["event_t"] - t0,
        "event": {"name": case.event, "spec": ev, "scheduled": state["scheduled"],
                  "forced_retract": None if forced is None else forced.meta()},
        "probe_request": probe_req,
        "rod_fault": None if rod_fault is None else rod_fault.meta(),
        "rod_fault_t_s": None if rod_fault is None or rod_fault.t_start_s is None
        else rod_fault.t_start_s - t0,
        "fine_dt": None if schedule is None else {
            "dt_transition_s": dt_fine, "opened_t_s": None if state["fine_open_t"] is None
            else state["fine_open_t"] - t0, "capped": state["fine_capped"],
            "lifted_seen_in_window": state["lifted_seen"],
            "segments_abs_t": schedule.to_meta()},
        "s8_end": s8_end,
        "seed": sc.seed, "r8_series": series_info, "pad_record": pads.meta(),
        "piston_monitor": model.actuator.piston_monitor(),
        "s8_plant_record": model.actuator.s8_record()
        if hasattr(model.actuator, "s8_record") else None,
        "monitor": engine.step_monitor(),
        "runner": {**res.meta, "wall_s": wall, "n_steps": res.n_steps,
                   "n_control": res.n_control,
                   "us_per_step": wall / max(res.n_steps, 1) * 1e6},
    }
    engine.close()
    return summary, run_meta


# --- ML episodes (C-S8-4, spec 205) ----------------------------------------------------------------


@dataclass(frozen=True)
class MLBase:
    base_id: str
    seed: int
    level: str
    floor_deg: tuple[float, float]
    fs_kN: float
    beta_GPa: float
    pressure_grade: str
    zero_calibration: bool
    imu_grade: str
    not_applied: tuple[str, ...]
    leg_scale: tuple[float, ...] = (1.0, 1.0, 1.0, 1.0)
    """Per-leg F_s factor U(0.8, 1.2) (``actuator.seal_friction.leg_scale``)."""
    rod_dead_length_m: float = 0.05
    """``L_0r`` U(0.02, 0.10) m, one value for the four legs (``actuator.rod_dead_length_m``)."""

    def overrides(self) -> dict[str, Any]:
        """Plant overrides of the ML inputs (python-expert spec 2026-10-24)."""
        return {"actuator.seal_friction.leg_scale": [float(v) for v in self.leg_scale],
                "actuator.rod_dead_length_m": float(self.rod_dead_length_m)}


ML_INPUT_SEED_OFFSET = 7919
"""The per-leg F_s factors and L_0r come from a second generator (seed + this) so the spec 205.3
draws of the earlier bases stay the same."""
ML_LEG_SCALE_RANGE = (0.8, 1.2)
ML_ROD_DEAD_LENGTH_RANGE_M = (0.02, 0.10)


def ml_bases(n: int = ML_BASES, seed: int = ML_SEED) -> list[MLBase]:
    """Spec 205.3 draws (seeded): F_s uniform 0-8 kN with the grid 0/2/4/8 on the first four,
    beta log-uniform 0.69-1.6 GPa, floor area-uniform in the verification diamond (10 % on its
    edge), auger 1:1:1, pressure grade 70/20/10 % (normal+cal / normal no cal / conservative),
    IMU 1:1; per-leg F_s factor U(0.8, 1.2) (``leg_scale``) and one L_0r U(0.02, 0.10) m per base
    from a second generator (:data:`ML_INPUT_SEED_OFFSET`)."""
    import numpy as np

    rng = np.random.default_rng(seed)
    rng_in = np.random.default_rng(seed + ML_INPUT_SEED_OFFSET)
    out = []
    levels = ("top", "middle", "bottom")
    for k in range(n):
        fs = (0.0, 2.0, 4.0, 8.0)[k] if k < 4 else float(rng.uniform(0.0, 8.0))
        beta = float(np.exp(rng.uniform(np.log(0.69), np.log(1.6))))
        if rng.uniform() < 0.1:
            u = rng.uniform(-1.0, 1.0)
            sx = 1.0 if rng.uniform() < 0.5 else -1.0
            phi, theta = 5.5 * abs(u) * sx, 3.5 * (1.0 - abs(u)) * (1 if rng.uniform() < .5 else -1)
        else:
            while True:
                phi, theta = rng.uniform(-5.5, 5.5), rng.uniform(-3.5, 3.5)
                if abs(phi) / 5.5 + abs(theta) / 3.5 <= 1.0:
                    break
        r = rng.uniform()
        grade = ("normal", True) if r < 0.7 else ("normal", False) if r < 0.9 \
            else ("conservative", True)
        scale = tuple(round(float(v), 4) for v in rng_in.uniform(*ML_LEG_SCALE_RANGE, size=4))
        l0r = round(float(rng_in.uniform(*ML_ROD_DEAD_LENGTH_RANGE_M)), 4)
        out.append(MLBase(f"ML{k:02d}", int(rng.integers(1, 2**31 - 1)), levels[k % 3],
                          (round(float(phi), 4), round(float(theta), 4)), round(fs, 3),
                          round(beta, 4), grade[0], grade[1],
                          "ideal" if k % 2 == 0 else "normal_zeroed", (), scale, l0r))
    return out


C_S8_28_EPISODES = ("ML00_ep5", "ML08_ep4", "ML10_ep4", "ML11_ep4", "ML17_ep4", "ML18_ep6",
                    "ML21_ep1")
"""C-S8-28 (spec rev. 48 218.7 condition 2 / 218.15): the pilot episodes with a head step
> 100 bar, re-run after P-S8-14 (D1'') with ``ml --resume <pilot> --only <these>``."""
ML_DESIGNS = ("pilot", "main")
"""``pilot``: the 192-episode design (retract at the fixed 0.25 v_max, no ``speed_fraction``
key, so pilot plans and resumes stay as written); ``main`` (U-S8-34): retract speed
U(0.5, 1.0) v_max per retract episode from a separate generator."""
ML_MAIN_BASES = 96
"""Spec 205.4: main stage 96 bases x 8 episodes = 768 (the first 24 bases equal the pilot draws:
``ml_bases`` draws sequentially)."""
ML_RETRACT_SPEED_RANGE = (0.5, 1.0)
ML_RETRACT_SPEED_SEED_OFFSET = 104729
"""U-S8-34: the retract speed fraction comes from ``default_rng(base.seed + 1 + this)``, one
draw per episode index (whatever its kind), so the spec 205.3 draws (kind, leg, depth, ramp) of
every episode are the same as the pilot design's."""


def ml_episodes(base: MLBase, n: int = ML_EPISODES_PER_BASE, *,
                design: str = "pilot") -> list[dict[str, Any]]:
    """Spec 205.3 events of one base (seeded by the base seed); ``design`` (:data:`ML_DESIGNS`):
    ``main`` adds ``speed_fraction`` U(0.5, 1.0) to the retract episodes (U-S8-34)."""
    import numpy as np

    if design not in ML_DESIGNS:
        raise ValueError(f"design must be one of {ML_DESIGNS}: {design!r}")
    rng = np.random.default_rng(base.seed + 1)
    rng_v = np.random.default_rng(base.seed + 1 + ML_RETRACT_SPEED_SEED_OFFSET)
    kinds = [k for k, w in ML_EVENT_WEIGHTS.items() for _ in range(w)]
    out = []
    for j in range(n):
        kind = kinds[int(rng.integers(len(kinds)))]
        v_frac = float(rng_v.uniform(*ML_RETRACT_SPEED_RANGE))
        ep = {"episode_id": f"{base.base_id}_ep{j}", "kind": kind, "t_after_branch_s": 2.0}
        if kind == "settle":
            ep.update(leg=("FL", "FR", "RL", "RR")[int(rng.integers(4))],
                      depth_m=round(float(rng.uniform(0.002, 0.030)), 5),
                      ramp_s=round(float(np.exp(rng.uniform(np.log(0.05), np.log(20.0)))), 4))
        elif kind == "retract":
            ep.update(leg=("FL", "FR", "RL", "RR")[int(rng.integers(4))],
                      depth_m=round(float(rng.uniform(0.005, 0.025)), 5))
            if design == "main":
                ep["speed_fraction"] = round(v_frac, 4)
        elif kind == "probe_repeat":
            ep["note"] = ("C2Controller.request_probe() from the event time, retried every "
                          "update until accepted (rejections recorded)")
        out.append(ep)
    return out


def _ml_case(base: MLBase) -> S8Case:
    floor_name = f"ml_{base.base_id}"
    st.FLOORS[floor_name] = base.floor_deg
    sc = s6c._sc(floor_name, "ML", base.level, floor_name, grade=base.imu_grade,
                 pressure_grade=base.pressure_grade, zero_calibration=base.zero_calibration,
                 seed=base.seed, items=())
    return S8Case(base.base_id, "ML", 5, "L2b_NSC",
                  _bc(base.base_id, sc, beta_GPa=base.beta_GPa, sensor_model=True),
                  fs_kN=base.fs_kN, condition="sensitivity",
                  extra_overrides=tuple(base.overrides().items()))


def sensor_condition(grade: str, zero_calibration: bool) -> str:
    """Display string of the pressure-sensor condition (the pre-P-S8-9 ``sensor_grade`` value):
    the grade, with ``_no_cal`` when the zero calibration is off."""
    return grade if zero_calibration else f"{grade}_no_cal"


def ml_meta(base: MLBase, model, *, event: str | None, branch_seal_f_N=None,
            episode_id: str | None = None) -> dict[str, Any]:
    """``result.json settings.ml_meta`` (``contact_episode.RUNNER_META_KEY``; keys of
    ``contact_episode.META_KEYS``). ``sensor_grade`` = pressure grade only (ideal / normal /
    conservative / old_worst), ``zero_calibration`` = bool, ``sensor_condition`` = the former
    combined string (``normal`` / ``normal_no_cal``; P-S8-9 reads both, old npz meta keep
    the combined value under ``sensor_grade``). ``seal_friction_N`` = per-leg limits in use (level x rear
    0.833 x leg_scale; 0 on the S7 path), ``initial_seal_state_N`` = seal friction ``f`` at the
    branch (None for a base run before its branch)."""
    import numpy as np

    act = model.actuator
    sf = getattr(act, "seal_friction", None)
    limits = np.zeros(4) if sf is None else np.asarray(sf.limits_N, float)
    rs = model.params.l2b.rod_side
    out = {"base_id": base.base_id, "case_id": episode_id or base.base_id,
           "seal_friction_N": limits.tolist(),
           "rod_dead_length_m": [float(v) for v in rs.rod_dead_length_m],
           "initial_seal_state_N": None if branch_seal_f_N is None
           else [float(v) for v in branch_seal_f_N],
           "floor": f"ml_{base.base_id}",
           "floor_roll_deg": float(base.floor_deg[0]), "floor_pitch_deg": float(base.floor_deg[1]),
           "level": base.level, "beta_Pa": float(base.beta_GPa) * 1e9,
           # P-S8-9 / spec rev. 44 214.5 question 3-5: grade and zero calibration apart; the
           # former combined string stays as the display key ``sensor_condition``
           "sensor_grade": base.pressure_grade,
           "zero_calibration": bool(base.zero_calibration),
           "sensor_condition": sensor_condition(base.pressure_grade, base.zero_calibration),
           "event": event, "seed": int(base.seed)}
    if episode_id is not None:
        out["episode_id"] = episode_id
    return out


def _write_controller_files(case_dir: Path, c2) -> None:
    """``controller_events.json`` / ``probe_history.json`` (episode builder inputs)."""
    events = [str(e) for e in c2.events]
    probes = [[asdict(r) if hasattr(r, "__dataclass_fields__") else str(r) for r in rnd]
              for rnd in c2.probe_history]
    (case_dir / "probe_history.json").write_text(json.dumps(probes, indent=1, default=str),
                                                 "utf-8")
    (case_dir / "controller_events.json").write_text(json.dumps(events, indent=1), "utf-8")


def run_chunked(engine, controller, suite, total_s, *, stop, recorder=None, **kw):
    """``run_closed_loop`` in :data:`ML_CHUNK_S` pieces (resume after the first) until ``stop()``
    at a chunk end or ``total_s``; returns the list of results."""
    from outrigger_sim.runner import run_closed_loop

    out, t_run = [], 0.0
    while t_run < total_s - 1e-9:
        resume = None if not out else engine.held_command
        res = run_closed_loop(engine, controller, suite, ML_CHUNK_S, recorder=recorder,
                              resume_command=resume, **kw)
        out.append(res)
        t_run += ML_CHUNK_S
        if stop():
            break
    return out


def job_ml_base(base: MLBase, case_dir: Path) -> dict[str, Any]:
    """Crawler start -> first READY + :data:`ML_BRANCH_AFTER_READY_S` (chunked), then
    ``branch.pkl`` (module docstring). Patches on all four legs (any episode leg)."""
    from outrigger_sim.chrono.l2b_pad_record_s8 import L2bPadRecorderS8
    from outrigger_sim.control.c2 import C2Phase
    from outrigger_sim.record import Recorder, make_run_meta, save_record
    from outrigger_sim.sensors.hydraulic import LegSensorConfig
    from outrigger_sim.sensors.imu import imu_config_for_grade
    from outrigger_sim.sensors.suite import SensorSuite
    from outrigger_sim.chrono.l2b_engine import L2bEngine
    from outrigger_sim.verify.reference import load_references

    case = _ml_case(base)
    sc = case.scenario
    model, patches, params, params_ctrl, over, plant_meta, start_poses = \
        build_l2b(case, patch_legs=("FL", "FR", "RL", "RR"))
    start = s7c.settle_l2b(model, s7c.CRAWLER_SETTLE_S)
    check_settle(start)
    t0 = float(model.system.GetChTime())
    engine = L2bEngine(model, imu_method="chrono_point")
    suite = SensorSuite(imu_config_for_grade(sc.grade, sample_period_s=s6c.IMU_SAMPLE_PERIOD_S),
                        st.leg_sensor_config_for(sc, t0) if case.base.sensor_model
                        else LegSensorConfig(), seed=sc.seed)
    c2, config, settle_meta = _controller(case, params_ctrl, params)
    pads = L2bPadRecorderS8(engine, sample_s=s7c.PAD_RECORD_S)
    series = S8Series(model, c2, model.actuator.head_area_m2, params.l2b.rod_side.annulus_area_m2)
    twist_hist = TwistScaleHistory(c2, t0)
    state = {"ready_t": None}

    def observe(meas, command):
        series(meas, command)
        twist_hist(meas.t_s)
        if c2.phase is C2Phase.READY and state["ready_t"] is None:
            state["ready_t"] = meas.t_s

    def stop():
        return state["ready_t"] is not None and \
            engine.time_s >= state["ready_t"] + ML_BRANCH_AFTER_READY_S - 1e-9

    settings = {"ml_base": asdict(base), "s8": {**case.to_meta(), **crawler_meta(model),
                                                 "plant": plant_meta},
                "param_overrides": s6c._plain(over), "start": start, "start_t_s": t0,
                "case_id": base.base_id, "floor": sc.floor, "level": sc.level,
                "pressure_grade": base.pressure_grade, "event": None, "seed": base.seed,
                "contact": sc.contact,
                "ml_meta": ml_meta(base, model, event=None)}
    run_meta = make_run_meta(params, engine.meta(), scenario=f"S8ML_{base.base_id}",
                             scenario_settings=s6c._plain(settings), sensors=suite.setup(),
                             reference_sha256=load_references().sha256_by_file())
    recorder = Recorder(run_meta)
    results = run_chunked(engine, c2, suite, ML_BASE_MAX_S, stop=stop, recorder=recorder,
                          on_control=observe, step_hook=pads, placement=st.run_placement())
    save_record(recorder.finish(), case_dir / "record")
    pads.save(case_dir / "pads.npz")
    series.save(case_dir / S8_SERIES_NAME)
    _write_controller_files(case_dir, c2)
    branched = stop()
    seal_f = model.actuator.acting_friction_N
    if branched:
        save_branch(case_dir / "branch.pkl", engine, c2, suite,
                    extra={"base": asdict(base), "seal_f_N": seal_f.tolist(), "start_t_s": t0})
    settings["ml_meta"]["initial_seal_state_N"] = seal_f.tolist() if branched else None
    summary = {"case": base.base_id, "base": asdict(base),
               "ready_t_s": None if state["ready_t"] is None
               else state["ready_t"] - t0, "branched": branched,
               "branch_t_s": engine.time_s - t0, "chunks": len(results),
               "wall_s": sum(r.wall_s for r in results), "settings": settings,
               "controller_meta": c2.meta(), "twist_stiffness_history": twist_hist.rows,
               "s8_plant_record": model.actuator.s8_record(),
               "monitor": engine.step_monitor(), "pad_record": pads.meta()}
    engine.close()
    return summary


def save_branch(path: Path, engine, controller, suite, *, extra=None) -> None:
    """C-S8-4 branch state at a control instant (after a run returned)."""
    import numpy as np

    snap = engine.snapshot()
    snap_fields = {"engine": snap.engine, "params_sha256": snap.params_sha256,
                   "time_s": snap.time_s, "held_command": snap.held_command,
                   "payload": {k: np.array(v) for k, v in snap.payload.items()}}
    blob = {"snapshot": snap_fields, "controller": copy.deepcopy(controller),
            "suite": copy.deepcopy(suite), "held_command": engine.held_command,
            "contact_window": {"cbuf": engine._cbuf.copy(), "cn": engine._cn, "ci": engine._ci},
            "t_s": engine.time_s, "extra": extra or {}}
    with open(path, "wb") as fh:
        pickle.dump(blob, fh, protocol=pickle.HIGHEST_PROTOCOL)


def restore_branch(blob: dict[str, Any], engine):
    """Restore ``blob`` (from :func:`save_branch`) into ``engine`` (same model build); returns
    (controller, suite, held command) ready for ``run_closed_loop(resume_command=held)``."""
    from outrigger_sim.engine import Snapshot

    engine.restore(Snapshot(**blob["snapshot"]))
    cw = blob["contact_window"]
    engine._cbuf[:] = cw["cbuf"]
    engine._cn, engine._ci = cw["cn"], cw["ci"]
    held = blob["held_command"]
    engine.apply_command(held)
    return copy.deepcopy(blob["controller"]), copy.deepcopy(blob["suite"]), held


REFRESH_NAMES = ("settings", "config")
"""C-S8-25 ③: attribute names (or ``*_settings`` / ``*_config``) whose frozen-dataclass value is
a setting, replaced by the current code's value after a branch restore."""
REFRESH_STATE_ATTRS = ("_state",)
"""Run-state containers: only missing attributes are added (no scalar comparison)."""
REFRESH_MAX_DEPTH = 4
REFRESH_REPR_CHARS = 4000
"""Length of the whole-setting repr kept in ``replaced`` (the changed fields are listed apart,
:func:`dataclass_diff`)."""
DIFF_REPR_CHARS = 600
DIFF_MAX_FIELDS = 200


def dataclass_diff(old, new, path: str, depth: int = 0) -> list[dict[str, Any]]:
    """Leaf fields that differ between two instances of the same dataclass, recursing into
    nested dataclasses (C-S8-36: e.g. ``c2.config.r8.lifted_reapproach.retrigger_window_s``).
    A field missing on ``old`` (older pickle) reads its class default."""
    import dataclasses

    out: list[dict[str, Any]] = []
    if type(old) is not type(new) or not dataclasses.is_dataclass(new) or depth > 8:
        return [{"path": path, "old": repr(old)[:DIFF_REPR_CHARS],
                 "new": repr(new)[:DIFF_REPR_CHARS]}]
    for f in dataclasses.fields(new):
        a, b = getattr(old, f.name, None), getattr(new, f.name)
        p = f"{path}.{f.name}"
        if dataclasses.is_dataclass(b) and not isinstance(b, type) and type(a) is type(b):
            if repr(a) != repr(b):
                out += dataclass_diff(a, b, p, depth + 1)
        elif repr(a) != repr(b):
            out.append({"path": p, "old": repr(a)[:DIFF_REPR_CHARS],
                        "new": repr(b)[:DIFF_REPR_CHARS]})
        if len(out) >= DIFF_MAX_FIELDS:
            break
    return out[:DIFF_MAX_FIELDS]


def _is_setting_name(name: str) -> bool:
    return name in REFRESH_NAMES or name.endswith(("_settings", "_config"))


def _is_project_object(v: Any) -> bool:
    return hasattr(v, "__dict__") and type(v).__module__.startswith("outrigger_sim")


def refresh_restored_controller(restored, fresh) -> dict[str, Any]:
    """C-S8-25 ③ (U-S8-28 / 29): bring a controller unpickled from ``branch.pkl`` to the
    settings of the current code, in place (other objects keep the reference).

    Walks the controller and its ``outrigger_sim`` sub-objects (same type in ``fresh``, depth
    <= :data:`REFRESH_MAX_DEPTH`):

    * a frozen-dataclass value under a setting name (:func:`_is_setting_name`) is replaced by
      the fresh one (recorded when it differs);
    * an attribute present in ``fresh`` but missing after unpickling (new state of the current
      code) is added from ``fresh`` (deep copy);
    * a ``deque`` whose ``maxlen`` differs (window derived from a setting) is rebuilt with the
      fresh ``maxlen`` keeping the newest items;
    * scalar attributes (int / float / bool / str / enum) that differ outside the run state
      are only recorded (derived constants, e.g. filter coefficients; not changed).

    Returns the meta (paths are attribute paths from the controller)."""
    import collections
    import dataclasses
    import enum

    out: dict[str, Any] = {"replaced": [], "replaced_equal": [], "added": [],
                           "deque_maxlen": [], "scalar_differs": [], "type_mismatch": []}

    def walk(a, b, path: str, depth: int, in_state: bool) -> None:
        if type(a) is not type(b):
            out["type_mismatch"].append(path)
            return
        da, db = vars(a), vars(b)
        for name, vb in db.items():
            p = f"{path}.{name}"
            if name not in da:
                da[name] = copy.deepcopy(vb)
                out["added"].append(p)
                continue
            va = da[name]
            if _is_setting_name(name) and dataclasses.is_dataclass(vb) \
                    and not isinstance(vb, type):
                if repr(va) == repr(vb):
                    out["replaced_equal"].append(p)
                else:
                    # C-S8-36: the whole repr is cut at REFRESH_REPR_CHARS, so the changed
                    # nested fields are listed apart (full paths, e.g. ``config.r8.
                    # lifted_reapproach.retrigger_window_s``)
                    out["replaced"].append({"path": p, "old": repr(va)[:REFRESH_REPR_CHARS],
                                            "new": repr(vb)[:REFRESH_REPR_CHARS],
                                            "changed_fields": dataclass_diff(va, vb, p)})
                da[name] = vb
                continue
            if isinstance(vb, collections.deque) and isinstance(va, collections.deque):
                if va.maxlen != vb.maxlen:
                    da[name] = collections.deque(va, maxlen=vb.maxlen)
                    out["deque_maxlen"].append({"path": p, "old": va.maxlen, "new": vb.maxlen})
                continue
            if not in_state and isinstance(vb, (bool, int, float, str, enum.Enum)) \
                    and isinstance(va, type(vb)) and va != vb:
                out["scalar_differs"].append({"path": p, "restored": repr(va),
                                              "fresh": repr(vb)})
                continue
            if depth < REFRESH_MAX_DEPTH and _is_project_object(vb) and _is_project_object(va):
                walk(va, vb, p, depth + 1, in_state or name in REFRESH_STATE_ATTRS)

    pickled_lr = reapproach_settings_meta(restored)
    walk(restored, fresh, "c2", 0, False)
    out["scalar_differs"] = out["scalar_differs"][:100]
    # C-S8-36 (spec rev. 52 229): the P-S8-16 re-approach settings now in use, and those the
    # branch was pickled with (old pickles lack the RT keys: class defaults = off)
    out["lifted_reapproach"] = {"pickled": pickled_lr,
                                "in_use": reapproach_settings_meta(restored),
                                "fresh": reapproach_settings_meta(fresh),
                                "rt_keys": list(RT_KEYS)}
    tp = getattr(getattr(restored, "_pressures", None), "settings", None)
    out["two_pressure_settings"] = None if tp is None else (
        tp.to_meta() if hasattr(tp, "to_meta") else repr(tp))
    # spec rev. 48 218.12: the lock-window valve lag comes with the fresh settings (the case
    # tau_v, :func:`with_lock_window_tau`); recorded apart for the C-S8-28 / main-batch meta
    out[LOCK_WINDOW_TAU_KEY] = None if tp is None else getattr(tp, LOCK_WINDOW_TAU_KEY, None)
    fresh_tp = getattr(getattr(fresh, "_pressures", None), "settings", None)
    out[f"{LOCK_WINDOW_TAU_KEY}_fresh"] = None if fresh_tp is None else getattr(
        fresh_tp, LOCK_WINDOW_TAU_KEY, None)
    out["rule"] = ("C-S8-25 ③: setting dataclasses replaced by the current code's values, "
                   "missing attributes added, window deques re-sized; scalars recorded only")
    return out


class FirstPeriodCompare:
    """C-S8-25 ③: controller wrapper of an ML episode. On the first update (branch instant) the
    unrefreshed copy ``old`` (settings as pickled) is updated with the same measurements and
    its command / phase / events are compared with the refreshed controller; then only the
    refreshed controller runs (``old`` is dropped). Delegates everything else."""

    def __init__(self, ctrl, old) -> None:
        self.ctrl = ctrl
        self.old = old
        self.result: dict[str, Any] | None = None

    @property
    def period_s(self) -> float:
        return self.ctrl.period_s

    def reset(self) -> None:
        self.ctrl.reset()

    def update(self, measurements):
        import numpy as np

        if self.old is None:
            return self.ctrl.update(measurements)
        n_ev_new, n_ev_old = len(self.ctrl.events), len(self.old.events)
        cmd_old = self.old.update(measurements)
        cmd = self.ctrl.update(measurements)
        u_new = np.asarray(cmd.leg_speed_m_s, float)
        u_old = np.asarray(cmd_old.leg_speed_m_s, float)
        self.result = {
            "t_s": float(measurements.t_s),
            "command_new_m_s": u_new.tolist(), "command_old_m_s": u_old.tolist(),
            "max_abs_command_diff_m_s": float(np.abs(u_new - u_old).max()),
            "phase_new": str(self.ctrl.phase), "phase_old": str(self.old.phase),
            "events_new": [str(e) for e in self.ctrl.events[n_ev_new:]],
            "events_old": [str(e) for e in self.old.events[n_ev_old:]]}
        self.result["identical"] = (self.result["max_abs_command_diff_m_s"] == 0.0
                                    and self.result["phase_new"] == self.result["phase_old"]
                                    and self.result["events_new"] == self.result["events_old"])
        self.old = None
        return cmd

    def meta(self) -> dict[str, Any]:
        return self.ctrl.meta()


def job_ml_episode(base: MLBase, ep: dict[str, Any], base_dir: Path, case_dir: Path,
                   episode_s: float | None = None, variant: str | None = None):
    """One 30 s episode from the base's ``branch.pkl`` (``episode_s``: shorter run for the
    resume smoke test only; None = :data:`ML_EPISODE_S`). ``variant``: C-S8-36 re-approach
    variant of the refreshed controller (:func:`with_reapproach_variant`; None = preset).
    ``base_dir`` is only read (C-S8-36 writes the episodes to a new batch)."""
    episode_s = ML_EPISODE_S if episode_s is None else float(episode_s)
    import numpy as np

    from outrigger_sim.chrono.l2b_engine import L2bEngine
    from outrigger_sim.chrono.l2b_pad_record_s8 import L2bPadRecorderS8
    from outrigger_sim.record import make_run_meta, save_record
    from outrigger_sim.runner import DtSchedule, run_closed_loop
    from outrigger_sim.verify.reference import load_references

    with open(base_dir / "branch.pkl", "rb") as fh:
        blob = pickle.load(fh)  # noqa: S301 - own file of the same batch
    case = _ml_case(base)
    model, patches, params, params_ctrl, over, plant_meta, _ = \
        build_l2b(case, patch_legs=("FL", "FR", "RL", "RR"))
    engine = L2bEngine(model, imu_method="chrono_point")
    c2, suite, held = restore_branch(blob, engine)
    # C-S8-25 ③: settings of the current code on the unpickled controller (+ 1-period compare)
    old_c2 = copy.deepcopy(c2)
    fresh_c2, *_ = _controller(case, params_ctrl, params, variant=variant)
    refresh = refresh_restored_controller(c2, fresh_c2)
    refresh["lock_window_tau_case_s"] = float(case.base.tau_v_s)  # spec rev. 48 218.12
    refresh["reapproach_variant"] = variant  # C-S8-36 (None = preset)
    compare = FirstPeriodCompare(c2, old_c2)
    t_b = engine.time_s
    controller = compare
    forced = None
    schedule = None
    t_ev = t_b + float(ep["t_after_branch_s"])
    if ep["kind"] == "settle":
        legs = ("FL", "FR", "RL", "RR")
        # only the chosen patch moves: schedule its own GroundSettlement motor
        i = legs.index(ep["leg"])
        _schedule_single_patch(patches, i, t_ev, ep["depth_m"], ep["ramp_s"], model.dt_s)
    elif ep["kind"] == "retract":
        # U-S8-27 / C-S8-25 ①: only the forced leg until done, then all legs to the controller
        # U-S8-34: main design speed U(0.5, 1.0) v_max (``speed_fraction``); pilot 0.25
        frac = float(ep.get("speed_fraction", RE1C_SPEED_FRACTION))
        forced = st.ForcedRetract(compare, leg=("FL", "FR", "RL", "RR").index(ep["leg"]),
                                  depth_m=ep["depth_m"],
                                  speed_m_s=frac * params.actuator.max_speed_m_s,
                                  others=ML_FORCED_OTHERS)
        forced.t_start = t_ev
        controller = forced
    pads = L2bPadRecorderS8(engine, sample_s=s7c.PAD_RECORD_S)
    series = S8Series(model, c2, model.actuator.head_area_m2, params.l2b.rod_side.annulus_area_m2)
    extra = blob.get("extra") if isinstance(blob.get("extra"), dict) else {}
    twist_hist = TwistScaleHistory(c2, float(extra.get("start_t_s", t_b)))
    fine = {"open": None}
    dt_fine = float(params.get("simulation.dt_transition_s"))
    if ep["kind"] == "settle" and ep["ramp_s"] < 1.0:
        schedule = DtSchedule(model.dt_s, c2.period_s)
    seal_f_branch = model.actuator.acting_friction_N
    probe = {"attempts": 0, "rejected": [], "accepted_t_s": None}

    def request_probe(t: float) -> None:
        """``probe_repeat`` (python-expert P-S8-2): ``C2Controller.request_probe()`` from the
        event time on, once per update until accepted (READY tail / lock tail answer ``busy``);
        every rejection is recorded."""
        if ep["kind"] != "probe_repeat" or probe["accepted_t_s"] is not None \
                or t < t_ev - 1e-9:
            return
        probe["attempts"] += 1
        if c2.request_probe():
            probe["accepted_t_s"] = t - t_b
        else:
            reason = next((str(e) for e in reversed(c2.events)
                           if "probe_request_rejected" in str(e)), "rejected")
            probe["rejected"].append({"t_s": t - t_b, "event": reason})

    def observe(meas, command):
        series(meas, command)
        twist_hist(meas.t_s)
        request_probe(meas.t_s)
        if schedule is None:
            return
        t = meas.t_s
        if fine["open"] is None and t >= t_ev - 0.5 - 1e-9:
            schedule.open(t, dt_fine, reason="episode fast settlement")
            fine["open"] = t
        elif fine["open"] is not None and schedule.is_open and \
                t >= t_ev + ep["ramp_s"] + 3.0 - 1e-9:
            schedule.close(t, reason="ramp + 3 s")

    sc = case.scenario
    settings = {"ml_base": asdict(base), "episode": ep, "branch_t_s": t_b,
                "s8": {**case.to_meta(), **crawler_meta(model)},
                "start_t_s": float(blob["extra"].get("start_t_s", t_b))
                if isinstance(blob.get("extra"), dict) else t_b,
                "case_id": ep["episode_id"], "floor": sc.floor, "level": sc.level,
                "pressure_grade": base.pressure_grade, "event": ep["kind"], "seed": base.seed,
                "contact": sc.contact, "param_overrides": s6c._plain(over),
                "ml_meta": ml_meta(base, model, event=ep["kind"],
                                   branch_seal_f_N=seal_f_branch,
                                   episode_id=ep["episode_id"]),
                "settings_refreshed": refresh,
                "reapproach_variant": variant, "branch_source": str(base_dir)}
    run_meta = make_run_meta(params, engine.meta(), scenario=f"S8ML_{ep['episode_id']}",
                             scenario_settings=s6c._plain(settings),
                             sensors=suite.setup(),
                             reference_sha256=load_references().sha256_by_file())
    res = run_closed_loop(engine, controller, suite, episode_s, run_meta=run_meta,
                          on_control=observe, step_hook=pads, dt_schedule=schedule,
                          resume_command=held, placement=st.run_placement())
    save_record(res.record, case_dir / "record")
    pads.save(case_dir / "pads.npz")
    series.save(case_dir / S8_SERIES_NAME)
    _write_controller_files(case_dir, c2)
    out = {"case": ep["episode_id"], "episode": ep, "base": base.base_id, "branch_t_s": t_b,
           "event_t_s": t_ev, "wall_s": res.wall_s, "n_steps": res.n_steps,
           "f_min_kN": float(np.min(pads.arrays()["F_cyl_min_interval"])) / 1e3,
           "settings": settings, "controller_meta": c2.meta(),
           "twist_stiffness_history": twist_hist.rows,
           "probe_request": probe if ep["kind"] == "probe_repeat" else None,
           "s8_plant_record": model.actuator.s8_record(), "monitor": engine.step_monitor(),
           "pad_record": pads.meta(),
           "fine_dt": None if schedule is None else schedule.to_meta(),
           "episode_s": episode_s,
           "first_period_compare": compare.result,
           "forced_retract": None if forced is None else
           {k: v for k, v in forced.meta().items() if k != "inner"}}
    engine.close()
    return out


def _schedule_single_patch(patches, leg_index: int, t_start, depth, ramp, dt) -> None:
    """Move one patch of a four-patch model (the others stay at 0)."""
    import pychrono as ch

    gs = patches.settlement
    j = patches.leg_names.index(("FL", "FR", "RL", "RR")[leg_index])
    seq = ch.ChFunctionSequence()
    seq.InsertFunct(ch.ChFunctionConst(0.0), float(t_start))
    seq.InsertFunct(ch.ChFunctionPoly345(-float(depth), float(ramp)), float(ramp))
    seq.InsertFunct(ch.ChFunctionConst(-float(depth)), 1.0e7)
    seq.Setup()
    gs.motors[j].SetMotionFunction(seq)
    gs._functions[j] = seq
    patches.single_patch = {"leg": patches.leg_names[j], "t_start_s": float(t_start),
                            "depth_m": float(depth), "ramp_s": float(ramp)}


# --- batch jobs -----------------------------------------------------------------------------------


def job_case(case, case_dir):
    """Batch job (module level for spawn)."""
    from outrigger_sim.batch import CaseResult

    s = case.settings
    d = Path(case_dir)
    kind = s.get("kind", "case")
    if kind == "ml_base":
        summary = job_ml_base(MLBase(**_tuples(s["base"])), d)
        run_meta = None
    elif kind == "ml_episode":
        summary = job_ml_episode(MLBase(**_tuples(s["base"])), s["episode"], Path(s["base_dir"]),
                                 d, episode_s=s.get("episode_s"), variant=s.get("variant"))
        run_meta = None
    else:
        c = case_table()[case.case_id]
        if c.engine == "L2b_NSC":
            summary, run_meta = job_l2b_s8(c, d, duration_s=s.get("duration_s"))
        else:
            summary, run_meta = s6c.job_bundle_c(c.base, d, duration_s=s.get("duration_s"))
            summary["settings"]["s8"] = {**c.to_meta(), "crawler_contact": "l1r_flexible",
                                         "crawler_check_passed": None}
            summary["settings"]["s7c"] = {"engine": "L1R", "case_id": c.case_id}
    (d / "result.json").write_text(json.dumps(s6c._plain(summary), indent=1, ensure_ascii=False),
                                   encoding="utf-8")
    keep = {k: summary[k] for k in ("case", "phases", "runner") if k in summary}
    return CaseResult(summary=s6c._plain(keep or {"done": True}),
                      run_meta=None if run_meta is None else s6c._plain(run_meta))


def _tuples(d: dict[str, Any]) -> dict[str, Any]:
    return {k: tuple(v) if isinstance(v, list) else v for k, v in d.items()}


# --- mixed P / E scheduler (U-S8-1) -------------------------------------------------------------


WORKER_LAYOUTS = {"p7": {"pcore": P_WORKERS}, "p7e8": {"pcore": P_WORKERS, "ecore": E_WORKERS}}


def simulate_makespan(walls_p: list[float], layout: str) -> dict[str, Any]:
    """Greedy schedule of :func:`run_cases_mixed` on estimated P-core walls (E = x E_CORE_FACTOR):
    a free P slot takes the longest pending, a free E slot the shortest."""
    pools = WORKER_LAYOUTS[layout]
    pending = sorted(walls_p, reverse=True)
    slots = [(0.0, "pcore")] * pools.get("pcore", 0) + [(0.0, "ecore")] * pools.get("ecore", 0)
    import heapq

    heap = [(0.0, i, kind) for i, (_t, kind) in enumerate(slots)]
    heapq.heapify(heap)
    end = 0.0
    counts = {"pcore": 0, "ecore": 0}
    while pending:
        t, i, kind = heapq.heappop(heap)
        w = pending.pop(0) if kind == "pcore" else pending.pop(-1) * E_CORE_FACTOR
        counts[kind] += 1
        heapq.heappush(heap, (t + w, i, kind))
        end = max(end, t + w)
    return {"makespan_s": end, "cases_per_pool": counts, "layout": layout,
            "serial_p_s": sum(walls_p)}


def run_cases_mixed(cases, job, output_dir: Path, *, layout: str, timeout_s: float,
                    wall_of, dir_of=None) -> list[Any]:
    """``outrigger_sim.batch`` with two placement pools (one process per case, failure isolation,
    timeout, ``case.json``; uses the batch module's case-process helpers). ``wall_of(case)`` =
    estimated P-core wall for the order. ``dir_of(case)`` (optional): output directory per case
    (main ML batch: the judged cases go to ``judged/``); ``batch.json`` is written to
    ``output_dir``."""
    import multiprocessing
    from collections import deque
    from multiprocessing.connection import wait

    from outrigger_sim import batch as B

    pools = WORKER_LAYOUTS[layout]
    if set(pools) == {"pcore"} and dir_of is None:
        rep = B.run_cases(cases, job, output_dir, max_workers=pools["pcore"], placement="pcore",
                          timeout_s=timeout_s)
        return list(rep.outcomes)
    case_list = sorted(cases, key=lambda c: -wall_of(c))
    output_dir = Path(output_dir)
    out_of = (lambda c: output_dir) if dir_of is None else (lambda c: Path(dir_of(c)))
    B._check_timeout(timeout_s)
    for d in sorted({out_of(c) for c in case_list}, key=str):
        B._check_inputs([c for c in case_list if out_of(c) == d], job, d,
                        sum(pools.values()))
        d.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    ctx = multiprocessing.get_context("spawn")
    pending = deque(case_list)
    running: dict[int, Any] = {}
    kind_of: dict[int, str] = {}
    busy = {k: 0 for k in pools}
    outcomes = {}
    started_utc = B._utc_now_text()
    t0 = time.perf_counter()
    while pending or running:
        for kind in ("pcore", "ecore"):
            while pending and busy.get(kind, 0) < pools.get(kind, 0):
                case = pending.popleft() if kind == "pcore" else pending.pop()
                # the runner re-pins its process (st.run_placement, default "pcore"): hand the
                # pool down through the environment of the spawned process, otherwise the E
                # pool runs on the P-cores too (p1_20261024_204911: all 15 on P, 633-884 us)
                prev = os.environ.get(st.RUN_PLACEMENT_ENV)
                os.environ[st.RUN_PLACEMENT_ENV] = kind
                try:
                    rc = B._start_case(ctx, job, case, out_of(case), B.Placement(kind),
                                       timeout_s)
                finally:
                    if prev is None:
                        os.environ.pop(st.RUN_PLACEMENT_ENV, None)
                    else:
                        os.environ[st.RUN_PLACEMENT_ENV] = prev
                running[rc.process.sentinel] = rc
                kind_of[rc.process.sentinel] = kind
                busy[kind] += 1
        ended = wait(list(running), timeout=B._wait_timeout_s(running))
        for sentinel in {*ended, *B._terminate_timed_out(running)}:
            rc = running.pop(sentinel)
            busy[kind_of.pop(sentinel)] -= 1
            # keyed by the job object: the same case id may run into two output directories
            # (C-S8-36 bundles A and B both run ML78_ep0 / ML88_ep0)
            outcomes[id(rc.case)] = B._finish_case(rc)
    ordered = [outcomes[id(c)] for c in case_list]
    doc = B._batch_document(ordered, job, started_utc, time.perf_counter() - t0,
                            sum(pools.values()), B.Placement.PCORE)
    doc["placement"] = f"mixed {pools}"
    B._write_text_atomically(output_dir / B.BATCH_META_NAME, B._json_text(doc))
    return ordered


# --- actions --------------------------------------------------------------------------------------


def plan(cases: list[S8Case], layout: str) -> dict[str, Any]:
    rows = [{"case_id": c.case_id, "group": c.group, "priority": c.priority, "engine": c.engine,
             "fs_kN": c.fs_kN, "event": c.event, "duration_s": c.duration_s,
             "expected_run_s": expected_run_s(c) if c.engine == "L2b_NSC" else c.duration_s,
             "upper_s": end_rule(c)["upper_s"],
             "wall_p_s": c.wall_estimate_s("p"), "wall_e_s": c.wall_estimate_s("e")}
            for c in cases]
    walls = [r["wall_p_s"] for r in rows]
    return {"cases": rows, "count": len(rows),
            "by_group": {g: sum(1 for r in rows if r["group"] == g)
                         for g in dict.fromkeys(r["group"] for r in rows)},
            "p7": simulate_makespan(walls, "p7"), "p7e8": simulate_makespan(walls, "p7e8"),
            "layout": layout,
            "basis": f"C-S8-19 ⑥ (p1r, pool full): L2b P-core {P_FULL_US_PER_STEP_FS:g} us/step "
                     f"at 1e-4 s for F_s > 0, {P_FULL_US_PER_STEP_FS0:.0f} for F_s 0 (/ "
                     f"{FS0_COST_RATIO:g}, ASSUMPTION), CB {P_FULL_US_PER_STEP_CB:.0f} "
                     f"(ASSUMPTION), fine window x{1 + FINE_DT_EXTRA_STEPS_FACTOR:g} steps, "
                     f"crawler settle {s7c.CRAWLER_SETTLE_S:g} s, L1 {L1_WALL_S_PER_S:g} s/s, "
                     f"E-core x{E_CORE_FACTOR:g}"}


ML_BASE_SIM_S = 75.0
"""ASSUMPTION: simulated time of a base (crawler start -> first READY + 2 s)."""
ML_FINE_PRE_S, ML_FINE_POST_S = 0.5, 3.0
"""Episode fine window (``job_ml_episode``): opens at event - 0.5 s, closes at event + ramp + 3 s."""


ML_STAGES = {"pilot": {"bases": ML_BASES, "design": "pilot", "tag": "ml_pilot", "judged": False},
             "main": {"bases": ML_MAIN_BASES, "design": "main", "tag": "ml_main",
                      "judged": True}}
"""``ml --stage``: pilot (24 x 8, retract 0.25 v_max) or main (96 x 8 = 768, U-S8-34 retract
speed, the six ``MLJ`` judged cases in the base phase, U-S8-35 / C-S8-30)."""
ML_PILOT_MEASURED_S = {"bases": 1109.5, "episodes": 2960.4}
"""Measured p7e8 makespans of the pilot ``ml_pilot_20261025_002044`` (``bases/batch.json``,
``episodes/batch_rerun_20261025_015059.json``: 192 episodes after U-S8-29); with the pilot
model makespans they give the calibration factors of :func:`ml_plan`."""
ML_EPISODE_MB, ML_BASE_MB, MLJ_CASE_MB = 23.8, 44.1, 70.0
"""Disk per run folder [MB]: pilot episodes mean 23.8 (max 26.7), bases mean 44.1 (incl.
``branch.pkl``), S8 event cases of p1r 69-71 (E_G4 / E_SS / E_RE1bF / K0V fdown3.5)."""


JUDGED_MODES = ("run", "reuse", "skip")
"""U-S8-40 (spec rev. 49 219.9): the six ``MLJ`` judged cases of ``ml --stage main`` are run in
the base phase (``run``, the rev. 48 plan), copied from a separate ``run --set mlj`` batch
(``reuse``, ``--mlj-from``; not run again) or left out (``skip``)."""


def _judged_mode(stage: str, mlj_from: Path | None, skip: bool) -> str:
    if not ML_STAGES[stage]["judged"]:
        return "skip"
    if skip and mlj_from is not None:
        raise SystemExit("--skip-judged and --mlj-from exclude each other")
    return "skip" if skip else ("reuse" if mlj_from is not None else "run")


def check_mlj_batch(mlj_from: Path) -> dict[str, Any]:
    """U-S8-40: a separate MLJ batch (``run --set mlj``) to reuse in the main ML batch. Every
    case of ``case_set('mlj')`` must have a finished folder (``result.json``, ``case.log``
    without ``failed``; ``verify.s8_control.ml_run_status`` ok). Returns the check record;
    raises SystemExit on a missing / failed case."""
    from outrigger_sim.verify.s8_control import ml_run_status

    mlj_from = Path(mlj_from)
    if not mlj_from.is_absolute():
        mlj_from = ROOT / mlj_from
    want = [c.case_id for c in case_set("mlj")]
    status = {cid: ml_run_status(mlj_from / cid)["status"] if (mlj_from / cid).is_dir()
              else "missing" for cid in want}
    bad = {k: v for k, v in status.items() if v != "ok"}
    meta_p = mlj_from / "batch_meta.json"
    meta = json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else {}
    out = {"mlj_from": str(mlj_from), "cases": want, "status": status,
           "batch_set": meta.get("set"), "batch_mode": meta.get("mode"),
           "step_rule": {cid: _result_step_rule(mlj_from / cid) for cid in want
                         if status[cid] == "ok"}}
    if bad:
        raise SystemExit(f"--mlj-from {mlj_from}: cases not finished ok: {bad}")
    if meta.get("mode") == "check":
        raise SystemExit(f"--mlj-from {mlj_from} is a check batch (short runs), not a run")
    return out


def _result_step_rule(case_dir: Path) -> Any:
    try:
        res = json.loads((Path(case_dir) / "result.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    from outrigger_sim.verify.s8_control import _step_rule_of

    return _step_rule_of(res)


def _ml_walls(stage: str, judged_mode: str | None = None
              ) -> tuple[list[float], list[float], list[float]]:
    """P-core wall estimates (bases, episodes, judged cases) of an ML stage (``judged_mode``
    :data:`JUDGED_MODES`; None = the stage default: run when the stage has judged cases)."""
    cfg = ML_STAGES[stage]
    run_judged = cfg["judged"] if judged_mode is None else judged_mode == "run"
    bases = ml_bases(cfg["bases"])
    base_walls, ep_walls = [], []
    for b in bases:
        us = step_us(b.fs_kN)
        base_walls.append(20.0 + (ML_BASE_SIM_S + s7c.CRAWLER_SETTLE_S) / 1e-4 * us * 1e-6)
        for ep in ml_episodes(b, design=cfg["design"]):
            steps = ML_EPISODE_S / 1e-4
            if ep["kind"] == "settle" and ep["ramp_s"] < 1.0:
                fine = min(ML_FINE_PRE_S + ep["ramp_s"] + ML_FINE_POST_S,
                           ML_EPISODE_S - ep["t_after_branch_s"] + ML_FINE_PRE_S)
                steps += fine / 1e-4 * FINE_DT_EXTRA_STEPS_FACTOR
            ep_walls.append(20.0 + steps * us * 1e-6)
    judged = [c.wall_estimate_s("p") for c in case_set("mlj")] if run_judged else []
    return base_walls, ep_walls, judged


def ml_plan(stage: str = "pilot", judged_mode: str | None = None) -> dict[str, Any]:
    """ML wall / disk estimate of a stage from the seeded draws (F_s per base, fine window per
    settle episode with ramp < 1 s); the main stage puts the judged cases into the base phase
    (``judged_mode`` ``run``; ``reuse`` / ``skip``: not in the pool, U-S8-40).
    ``calibrated``: the model makespans x (pilot measured / pilot model) per phase."""
    cfg = ML_STAGES[stage]
    judged_mode = ("run" if cfg["judged"] else "skip") if judged_mode is None else judged_mode
    base_walls, ep_walls, judged = _ml_walls(stage, judged_mode)
    pb, pe, _ = _ml_walls("pilot")
    cal = {"bases": ML_PILOT_MEASURED_S["bases"] / simulate_makespan(pb, "p7e8")["makespan_s"],
           "episodes": ML_PILOT_MEASURED_S["episodes"]
           / simulate_makespan(pe, "p7e8")["makespan_s"]}
    out = {}
    for lay in WORKER_LAYOUTS:
        a = simulate_makespan(base_walls + judged, lay)
        b = simulate_makespan(ep_walls, lay)
        out[lay] = {"bases_s": a["makespan_s"], "episodes_s": b["makespan_s"],
                    "total_s": a["makespan_s"] + b["makespan_s"],
                    "total_h": (a["makespan_s"] + b["makespan_s"]) / 3600.0,
                    "calibrated_total_s": a["makespan_s"] * cal["bases"]
                    + b["makespan_s"] * cal["episodes"],
                    "calibrated_total_h": (a["makespan_s"] * cal["bases"]
                                           + b["makespan_s"] * cal["episodes"]) / 3600.0}
    kinds: dict[str, int] = {}
    speeds = []
    for b in ml_bases(cfg["bases"]):
        for ep in ml_episodes(b, design=cfg["design"]):
            kinds[ep["kind"]] = kinds.get(ep["kind"], 0) + 1
            if "speed_fraction" in ep:
                speeds.append(ep["speed_fraction"])
    n_judged_disk = len(case_set("mlj")) if judged_mode in ("run", "reuse") else 0
    disk_gb = (len(ep_walls) * ML_EPISODE_MB + len(base_walls) * ML_BASE_MB
               + n_judged_disk * MLJ_CASE_MB) / 1024.0
    return {"stage": stage, "design": cfg["design"], "bases": len(base_walls),
            "episodes": len(ep_walls), "judged_cases": [c.case_id for c in case_set("mlj")]
            if judged_mode != "skip" else [], "judged_mode": judged_mode,
            "judged_mode_note": {"run": "MLJ cases run in the base-phase pool",
                                 "reuse": "MLJ folders copied from --mlj-from into judged/ "
                                          "(not run again, U-S8-40)",
                                 "skip": "no MLJ cases in this batch"}[judged_mode],
            "episodes_by_kind": kinds,
            "retract_speed_fraction": None if not speeds else
            {"min": min(speeds), "max": max(speeds), "mean": sum(speeds) / len(speeds)},
            "base_wall_p_s_mean": sum(base_walls) / len(base_walls),
            "episode_wall_p_s_mean": sum(ep_walls) / len(ep_walls),
            "judged_wall_p_s": judged,
            "serial_p_s": sum(base_walls) + sum(ep_walls) + sum(judged), "makespan": out,
            "calibration": {**cal, "source": "ML_PILOT_MEASURED_S / pilot model (p7e8)"},
            "disk_GB": disk_gb,
            "disk_basis": f"episode {ML_EPISODE_MB:g} MB, base {ML_BASE_MB:g} MB, judged case "
                          f"{MLJ_CASE_MB:g} MB (pilot / p1r folders)",
            "basis": f"base = {ML_BASE_SIM_S:g} s to READY + 2 s (ASSUMPTION) + crawler settle; "
                     f"episode {ML_EPISODE_S:g} s, settle episodes with ramp < 1 s add the fine "
                     f"window (event - {ML_FINE_PRE_S:g} s .. + ramp + {ML_FINE_POST_S:g} s at "
                     f"1e-5 s); step cost {P_FULL_US_PER_STEP_FS:g} (F_s > 0) / "
                     f"{P_FULL_US_PER_STEP_FS0:.0f} (F_s 0) us on a full P pool, E-core x"
                     f"{E_CORE_FACTOR:g} (C-S8-19 ⑥); judged cases (main): {judged_mode}"}


def _batch_dir(tag: str) -> Path:
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    d = RESULTS / f"{tag}_{stamp}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def run_batch(cases: list[S8Case], *, tag: str, layout: str, check: bool, duration_s: float):
    from outrigger_sim.batch import Case

    l1 = [c for c in cases if c.engine == "L1R" and c.base.blocked_in(s6c.STATES)]
    if l1:
        raise SystemExit(f"L1 twins without a start snapshot (run `snaps`): "
                         f"{[c.case_id for c in l1]}")
    batch_dir = _batch_dir(f"{tag}_check" if check else tag)
    from outrigger_sim.chrono import s8_plant_adapter as plant

    meta = {"mode": "check" if check else "run", "set": tag, "layout": layout,
            "cases": [c.case_id for c in cases], "plan": plan(cases, layout),
            "plant_adapter": plant.adapter_meta(),
            "crawler_mode": os.environ.get(CRAWLER_ENV, "yaml"),
            "c2_readiness": s6c.rerun34_readiness(),
            "env": {k: os.environ.get(k) for k in ("OUTRIGGER_ROD_SIDE_MECHANICS",
                                                    "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}}
    (batch_dir / "batch_meta.json").write_text(json.dumps(s6c._plain(meta), indent=1), "utf-8")
    table = {c.case_id: c for c in cases}
    jobs = [Case(c.case_id, {"duration_s": duration_s if check else None}) for c in cases]
    t0 = time.perf_counter()
    outs = run_cases_mixed(jobs, job_case, batch_dir, layout=layout,
                           timeout_s=CHECK_TIMEOUT_S if check else CASE_TIMEOUT_S,
                           wall_of=lambda j: table[j.case_id].wall_estimate_s("p"))
    for o in outs:
        msg = f"{o.case_id}: {o.status} {o.wall_s:.1f}s"
        if o.status != "ok":
            msg += "\n" + (o.error or "")[-2500:]
        print(msg, flush=True)
    print(f"batch wall {time.perf_counter() - t0:.1f} s -> {batch_dir}", flush=True)
    return batch_dir


def reuse_mlj(judged_dir: Path, check: dict[str, Any]) -> dict[str, Any]:
    """U-S8-40: copy the finished MLJ case folders of ``check['mlj_from']`` into ``judged_dir``
    (the source batch is not changed) and write ``judged/batch_meta.json`` naming the source."""
    import shutil

    src = Path(check["mlj_from"])
    judged_dir.mkdir(parents=True, exist_ok=True)
    for cid in check["cases"]:
        shutil.copytree(src / cid, judged_dir / cid)
    meta = {"mode": "reuse", "set": "mlj", "cases": check["cases"], "reused_from": str(src),
            "source_batch_meta": check.get("batch_set"), "step_rule": check.get("step_rule"),
            "note": "U-S8-40: judged cases of the main ML batch copied from the separate MLJ "
                    "batch (not run again)"}
    (judged_dir / "batch_meta.json").write_text(json.dumps(s6c._plain(meta), indent=1), "utf-8")
    return meta


def run_ml(layout: str, stage: str = "pilot", *, mlj_from: Path | None = None,
           skip_judged: bool = False):
    """ML batch of a stage (:data:`ML_STAGES`): bases (+ the judged ``MLJ`` cases of the main
    stage, written to ``judged/`` and scheduled in the same pool, longest first; U-S8-40:
    ``mlj_from`` copies them from a separate ``run --set mlj`` batch instead, ``skip_judged``
    leaves them out), then the episodes."""
    from outrigger_sim.batch import Case

    cfg = ML_STAGES[stage]
    mode = _judged_mode(stage, mlj_from, skip_judged)
    mlj_check = check_mlj_batch(mlj_from) if mode == "reuse" else None
    batch_dir = _batch_dir(cfg["tag"])
    bases = ml_bases(cfg["bases"])
    (batch_dir / "ml_plan.json").write_text(json.dumps(s6c._plain(
        {"stage": stage, "ml_design": cfg["design"], "bases": [asdict(b) for b in bases],
         "episodes": {b.base_id: ml_episodes(b, design=cfg["design"]) for b in bases},
         "judged_cases": [c.case_id for c in case_set("mlj")] if mode != "skip" else [],
         "judged_mode": mode, "mlj_reuse": mlj_check,
         "plan": ml_plan(stage, mode)}),
        indent=1), "utf-8")
    base_dir = batch_dir / "bases"
    jobs = [Case(b.base_id, {"kind": "ml_base", "base": asdict(b)}) for b in bases]
    base_wall = {b.base_id: w for b, w in zip(bases, _ml_walls(stage, mode)[0])}
    judged_dir = batch_dir / "judged"
    dir_of = None
    if mode == "reuse":
        reuse_mlj(judged_dir, mlj_check)
    if mode == "run":
        table = case_table()
        jc = case_set("mlj")
        jobs += [Case(c.case_id, {"duration_s": None}) for c in jc]
        base_wall.update({c.case_id: c.wall_estimate_s("p") for c in jc})
        judged_ids = {c.case_id for c in jc}
        meta = {"mode": "run", "set": "mlj", "layout": layout,
                "cases": sorted(judged_ids), "plan": plan(jc, layout),
                "crawler_mode": os.environ.get(CRAWLER_ENV, "yaml"),
                "note": "judged cases of the main ML batch, run in the base phase pool"}
        judged_dir.mkdir(parents=True, exist_ok=True)
        (judged_dir / "batch_meta.json").write_text(json.dumps(s6c._plain(meta), indent=1),
                                                    "utf-8")
        assert all(c in table for c in judged_ids)

        def dir_of(job):  # noqa: E306 - closure over judged_ids
            return judged_dir if job.case_id in judged_ids else base_dir
    run_cases_mixed(jobs, job_case, base_dir, layout=layout, timeout_s=CASE_TIMEOUT_S,
                    wall_of=lambda j: base_wall.get(j.case_id, 1.0), dir_of=dir_of)
    eps = []
    for b in bases:
        if not (base_dir / b.base_id / "branch.pkl").exists():
            print(f"{b.base_id}: no branch (READY not reached?)", flush=True)
            continue
        for ep in ml_episodes(b, design=cfg["design"]):
            eps.append(Case(ep["episode_id"], {"kind": "ml_episode", "base": asdict(b),
                                               "episode": ep,
                                               "base_dir": str(base_dir / b.base_id)}))
    run_cases_mixed(eps, job_case, batch_dir / "episodes", layout=layout,
                    timeout_s=CASE_TIMEOUT_S, wall_of=lambda j: 1.0)
    print(f"-> {batch_dir}", flush=True)
    return batch_dir


def ml_episode_failed(case_dir: Path) -> bool:
    """Resume rule (main session 2026-10-25): an episode folder failed when it has no
    ``result.json`` or its ``case.log`` contains ``failed``."""
    d = Path(case_dir)
    if not (d / "result.json").exists():
        return True
    log = d / "case.log"
    return log.exists() and "failed" in log.read_text(encoding="utf-8", errors="replace")


def _plain_json(x: Any) -> Any:
    return json.loads(json.dumps(s6c._plain(x)))


def ml_resume_plan(batch_dir: Path, *, failed_only: bool = True,
                   only: list[str] | None = None) -> dict[str, Any]:
    """Episodes of an existing ML batch to run again. The bases and episode definitions come from
    the batch ``ml_plan.json`` and must equal the seeded draws of this code (:func:`ml_bases`,
    :func:`ml_episodes`), so the re-run episodes keep their ``ml_meta``, seed and event; every
    base used needs its ``branch.pkl``. ``failed_only``: the failed episodes
    (:func:`ml_episode_failed`, a planned episode without a folder counts as failed); ``only``:
    restrict to these episode ids."""
    batch_dir = Path(batch_dir)
    plan_doc = json.loads((batch_dir / "ml_plan.json").read_text(encoding="utf-8"))
    bases = {b["base_id"]: b for b in plan_doc["bases"]}
    design = plan_doc.get("ml_design", "pilot")  # pilot plans carry no design key
    code_bases = {b.base_id: b for b in ml_bases(len(bases))}
    mismatch = []
    for bid, b in bases.items():
        cb = code_bases.get(bid)
        if cb is None or _plain_json(asdict(cb)) != b:
            mismatch.append(f"base {bid}")
            continue
        if _plain_json(ml_episodes(cb, design=design)) != plan_doc["episodes"][bid]:
            mismatch.append(f"episodes of {bid}")
    ep_root = batch_dir / "episodes"
    todo, ok, missing_branch = [], [], []
    for bid, eps in plan_doc["episodes"].items():
        for ep in eps:
            eid = ep["episode_id"]
            if only and eid not in only:
                continue
            d = ep_root / eid
            failed = (not d.exists()) or ml_episode_failed(d)
            if failed_only and not failed:
                ok.append(eid)
                continue
            if not (batch_dir / "bases" / bid / "branch.pkl").exists():
                missing_branch.append(eid)
                continue
            todo.append({"episode_id": eid, "base_id": bid, "kind": ep["kind"],
                         "folder_exists": d.exists(), "failed": failed})
    unknown = sorted(set(only or ()) - {e["episode_id"] for v in plan_doc["episodes"].values()
                                         for e in v})
    return {"batch": str(batch_dir), "plan_matches_code": not mismatch, "mismatch": mismatch,
            "design": design, "unknown_only_ids": unknown,
            "rerun": todo, "kept": len(ok), "missing_branch": missing_branch,
            "episodes_planned": sum(len(v) for v in plan_doc["episodes"].values()),
            "bases": bases, "episodes": plan_doc["episodes"]}


def run_ml_resume(batch_dir: Path, layout: str, *, failed_only: bool = True,
                  only: list[str] | None = None, dry_run: bool = False,
                  episode_s: float | None = None) -> dict[str, Any]:
    """Re-run episodes of an existing ML batch (bases and ``branch.pkl`` reused). Steps: check
    the plan against the code (:func:`ml_resume_plan`; abort on a mismatch); move the folders to
    re-run to ``episodes/_failed_<stamp>/``; run them into ``episodes/_rerun_<stamp>/``
    (``outrigger_sim.batch`` refuses an existing ``batch_meta.json``) and move every case folder
    into ``episodes/``; the run's batch meta is kept as ``episodes/batch_meta_rerun_<stamp>.json``.
    Successful episodes are not touched. ``dry_run``: print the plan only."""
    import shutil

    from outrigger_sim.batch import Case

    batch_dir = Path(batch_dir)
    rp = ml_resume_plan(batch_dir, failed_only=failed_only, only=only)
    show = {k: v for k, v in rp.items() if k not in ("bases", "episodes")}
    kinds: dict[str, int] = {}
    for e in rp["rerun"]:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    show["rerun_count"] = len(rp["rerun"])
    show["rerun_by_kind"] = kinds
    show["rerun"] = [e["episode_id"] for e in rp["rerun"]]
    show["episode_s"] = ML_EPISODE_S if episode_s is None else episode_s
    print(json.dumps(show, indent=1), flush=True)
    if not rp["plan_matches_code"]:
        raise SystemExit(f"ml_plan.json differs from the seeded draws of this code: "
                         f"{rp['mismatch']} (ml_meta / seed / events would change)")
    if rp["unknown_only_ids"]:
        raise SystemExit(f"--only ids not in the batch plan: {rp['unknown_only_ids']}")
    if dry_run or not rp["rerun"]:
        return show
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    ep_root = batch_dir / "episodes"
    keep = ep_root / (f"_failed_{stamp}" if failed_only else f"_replaced_{stamp}")
    stage = ep_root / f"_rerun_{stamp}"
    for e in rp["rerun"]:
        src = ep_root / e["episode_id"]
        if src.exists():
            keep.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(keep / e["episode_id"]))
    jobs = []
    for e in rp["rerun"]:
        b = rp["bases"][e["base_id"]]
        ep = next(x for x in rp["episodes"][e["base_id"]] if x["episode_id"] == e["episode_id"])
        settings = {"kind": "ml_episode", "base": b, "episode": ep,
                    "base_dir": str(batch_dir / "bases" / e["base_id"])}
        if episode_s is not None:
            settings["episode_s"] = float(episode_s)
        jobs.append(Case(e["episode_id"], settings))
    outcomes = run_cases_mixed(jobs, job_case, stage, layout=layout, timeout_s=CASE_TIMEOUT_S,
                               wall_of=lambda j: 1.0)
    for e in rp["rerun"]:
        src = stage / e["episode_id"]
        if src.exists():
            shutil.move(str(src), str(ep_root / e["episode_id"]))
    from outrigger_sim import batch as B

    meta = stage / B.BATCH_META_NAME
    if meta.exists():
        shutil.move(str(meta), str(ep_root / f"batch_rerun_{stamp}.json"))
    if stage.exists() and not any(stage.iterdir()):
        stage.rmdir()
    status = {str(getattr(o, "case_id", o)): str(getattr(o, "status", "?"))
              for o in list(outcomes or [])}
    if not status:  # fall back to the folders (case.log rule)
        status = {e["episode_id"]: ("failed" if ml_episode_failed(ep_root / e["episode_id"])
                                    else "ok") for e in rp["rerun"]}
    show["moved_failed_to"] = str(keep) if keep.exists() else None
    show["status"] = status
    print(json.dumps({"moved_failed_to": show["moved_failed_to"], "status": status}, indent=1),
          flush=True)
    return show


# --- C-S8-36 (spec rev. 52 230, U-S8-49 / 50) ------------------------------------------------

C36_SOURCE = Path("07_results/S8/ml_main_20261025_090131")
"""The 768 batch whose bases (``branch.pkl``) and plan the C-S8-36 episodes re-use (read only)."""
C36_AFFECTED = Path("06_analysis/02_control/s8/s8_rev52_r51_affected.json")
"""Spec rev. 52 230: the 55 episodes of the 768 with a re-approach start within 2.0 s of the
previous end (``affected``)."""
C36_F1ONLY = ("ML78_ep0", "ML88_ep0")
"""Bundle B: F1 alone (RT off) - the ML78_ep0 ping-pong and the ML88_ep0 rod fallback."""
C36_GATE = ("E_RE1bF_Fs0", "E_RE1bP_Fs0")
"""Bundle C: control-3 gate cases RE1bF / RE1bP, top level, F_s 0 (U57 regression)."""
C36_DIRS = {"A": "A_rt", "B": "B_f1only", "C": "C_gate"}
C36_GATE_REF = Path("07_results/S8/p1r_20261024_222013")
"""Measured walls of the bundle C cases (p1r batch)."""


def _root_path(p: Path | str) -> Path:
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


def c36_affected_ids(path: Path | str = C36_AFFECTED) -> list[str]:
    doc = json.loads(_root_path(path).read_text(encoding="utf-8"))
    ids = list(doc["affected"])
    if len(ids) != len(set(ids)):
        raise SystemExit(f"{path}: duplicate affected ids")
    return ids


def _measured_wall_s(case_dir: Path) -> float | None:
    try:
        res = json.loads((case_dir / "result.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    w = res.get("wall_s")
    return float(w) if isinstance(w, int | float) else None


def c36_jobs(source: Path | str = C36_SOURCE, affected: Path | str = C36_AFFECTED,
             *, episode_s: float | None = None, ids_a: Sequence[str] | None = None,
             ids_b: Sequence[str] = C36_F1ONLY, gate: Sequence[str] = C36_GATE
             ) -> dict[str, Any]:
    """Jobs and plan of the three C-S8-36 bundles. A / B come from the source ML batch plan
    (:func:`ml_resume_plan`: the plan must equal this code's seeded draws, every base needs its
    ``branch.pkl``); C from :func:`case_table`. C-S8-41: ``ids_a`` replaces the ``affected``
    list (bundle E of :func:`run_c37`), ``ids_b`` / ``gate`` may be empty."""
    from outrigger_sim.batch import Case

    src = _root_path(source)
    ids_a = c36_affected_ids(affected) if ids_a is None else list(ids_a)
    ids_b = list(ids_b)
    rp = ml_resume_plan(src, failed_only=False, only=sorted(set(ids_a) | set(ids_b)))
    problems = []
    if not rp["plan_matches_code"]:
        problems.append(f"ml_plan.json differs from the seeded draws: {rp['mismatch']}")
    if rp["unknown_only_ids"]:
        problems.append(f"ids not in the source plan: {rp['unknown_only_ids']}")
    if rp["missing_branch"]:
        problems.append(f"bases without branch.pkl: {rp['missing_branch']}")
    by_id = {e["episode_id"]: e for e in rp["rerun"]}
    jobs: dict[str, list[Any]] = {"A": [], "B": [], "C": []}
    rows: list[dict[str, Any]] = []
    sub_plans: dict[str, dict[str, Any]] = {}
    for bundle, ids, variant in (("A", ids_a, "rt"), ("B", ids_b, "f1only")):
        bases_used: dict[str, Any] = {}
        eps_used: dict[str, list[Any]] = {}
        for eid in ids:
            e = by_id.get(eid)
            if e is None:
                continue
            b = rp["bases"][e["base_id"]]
            ep = next(x for x in rp["episodes"][e["base_id"]] if x["episode_id"] == eid)
            settings = {"kind": "ml_episode", "base": b, "episode": ep,
                        "base_dir": str(src / "bases" / e["base_id"]), "variant": variant}
            if episode_s is not None:
                settings["episode_s"] = float(episode_s)
            jobs[bundle].append(Case(eid, settings))
            bases_used[e["base_id"]] = b
            eps_used.setdefault(e["base_id"], []).append(ep)
            w = _measured_wall_s(src / "episodes" / eid)
            rows.append({"bundle": bundle, "id": eid, "variant": variant, "kind": ep["kind"],
                         "leg": ep.get("leg"), "wall_measured_s": w})
        sub_plans[bundle] = {"stage": "c36", "ml_design": rp["design"],
                             "bases": list(bases_used.values()), "episodes": eps_used,
                             "variant": variant, "rerun_from": str(src),
                             "rule": "C-S8-36 (spec rev. 52 230): episodes re-run from the "
                                     "source batch branch.pkl (bases read only, not copied)"}
    table = case_table()
    for cid in gate:
        c = table[cid]
        jobs["C"].append(Case(cid, {"duration_s": None}))
        rows.append({"bundle": "C", "id": cid, "variant": "rt", "kind": c.event,
                     "wall_measured_s": _measured_wall_s(_root_path(C36_GATE_REF) / cid),
                     "wall_estimate_s": c.wall_estimate_s("p")})
    return {"source": str(src), "affected": str(_root_path(affected)), "jobs": jobs,
            "rows": rows, "sub_plans": sub_plans, "problems": problems,
            "counts": {k: len(v) for k, v in jobs.items()}}


def c36_plan(info: dict[str, Any]) -> dict[str, Any]:
    """Wall estimate: measured ``wall_s`` of the source runs (768 batch, p7e8 pool; bundle C:
    p1r) else the step-cost model; makespan by :func:`simulate_makespan` (E-core x factor)."""
    walls = []
    missing = []
    for r in info["rows"]:
        w = r.get("wall_measured_s") or r.get("wall_estimate_s")
        if w is None:
            missing.append(r["id"])
            w = 600.0  # ASSUMPTION: upper end of the 768 job walls (290-580 s)
        walls.append(float(w))
    out = {"counts": info["counts"], "total": len(walls),
           "wall_s": {"min": min(walls), "max": max(walls), "sum": sum(walls)},
           "missing_wall": missing,
           "p7": simulate_makespan(walls, "p7"), "p7e8": simulate_makespan(walls, "p7e8"),
           "basis": "measured result.json wall_s of the same episode in the source batch "
                    "(p7e8 pool, F1 / RT change the trajectory after the event only) and of "
                    "the p1r gate cases; E-core x" f"{E_CORE_FACTOR:g}"}
    for k in ("p7", "p7e8"):
        out[k]["makespan_min"] = out[k]["makespan_s"] / 60.0
    return out


def run_c36(layout: str, *, source: Path | str = C36_SOURCE, affected: Path | str = C36_AFFECTED,
            dry_run: bool = False, approved: bool = False) -> dict[str, Any]:
    """C-S8-36: bundles A (affected 55, RT + F1), B (F1 alone, 2) and C (gate RE1bF / RE1bP,
    RT + F1) in one pool into a new batch ``07_results/S8/c36_<stamp>/`` with ``A_rt/episodes``,
    ``B_f1only/episodes`` (each with an ``ml_plan.json`` for ``judge``) and ``C_gate/``. The
    source batch is not changed."""
    info = c36_jobs(source, affected)
    doc = {"plan": c36_plan(info), "problems": info["problems"], "source": info["source"],
           "affected": info["affected"],
           "ids": {k: [c.case_id for c in v] for k, v in info["jobs"].items()},
           "out": "07_results/S8/c36_<stamp>/{A_rt/episodes, B_f1only/episodes, C_gate}"}
    print(json.dumps(s6c._plain(doc), indent=1), flush=True)
    if info["problems"]:
        raise SystemExit(f"C-S8-36 plan problems: {info['problems']}")
    if dry_run:
        return doc
    if not approved:
        raise SystemExit("C-S8-36 needs the user's confirmation: --approved (or --dry-run)")
    batch_dir = _batch_dir("c36")
    from outrigger_sim.chrono import s8_plant_adapter as plant

    dirs = {k: batch_dir / v for k, v in C36_DIRS.items()}
    for k in ("A", "B"):
        dirs[k].mkdir(parents=True, exist_ok=True)
        (dirs[k] / "ml_plan.json").write_text(
            json.dumps(s6c._plain(info["sub_plans"][k]), indent=1), "utf-8")
    dirs["C"].mkdir(parents=True, exist_ok=True)
    table = case_table()
    gate = [table[c] for c in C36_GATE]
    (dirs["C"] / "batch_meta.json").write_text(json.dumps(s6c._plain(
        {"mode": "run", "set": "c36_gate", "layout": layout,
         "cases": list(C36_GATE), "plan": plan(gate, layout),
         "plant_adapter": plant.adapter_meta(),
         "crawler_mode": os.environ.get(CRAWLER_ENV, "yaml"),
         "note": "C-S8-36 bundle C (RT + F1)"}), indent=1), "utf-8")
    (batch_dir / "c36_meta.json").write_text(json.dumps(s6c._plain(
        {**doc, "batch": str(batch_dir), "layout": layout,
         "env": {k: os.environ.get(k) for k in ("OUTRIGGER_ROD_SIDE_MECHANICS",
                                                 "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}}),
        indent=1), "utf-8")
    where: dict[int, Path] = {}
    walls: dict[int, float] = {}
    all_jobs = []
    for k in ("A", "B", "C"):
        out_dir = dirs[k] / "episodes" if k in ("A", "B") else dirs[k]
        for j in info["jobs"][k]:
            where[id(j)] = out_dir
            r = next(x for x in info["rows"] if x["bundle"] == k and x["id"] == j.case_id)
            walls[id(j)] = float(r.get("wall_measured_s") or r.get("wall_estimate_s") or 600.0)
            all_jobs.append(j)
    t0 = time.perf_counter()
    outs = run_cases_mixed(all_jobs, job_case, batch_dir, layout=layout,
                           timeout_s=CASE_TIMEOUT_S, wall_of=lambda j: walls[id(j)],
                           dir_of=lambda j: where[id(j)])
    status = {}
    for j, o in zip(sorted(all_jobs, key=lambda j: -walls[id(j)]), outs):
        status[f"{where[id(j)].relative_to(batch_dir)}/{o.case_id}"] = o.status
        if o.status != "ok":
            print(f"{o.case_id}: {o.status}\n{(o.error or '')[-2500:]}", flush=True)
    print(json.dumps({"batch": str(batch_dir), "wall_s": time.perf_counter() - t0,
                      "failed": {k: v for k, v in status.items() if v != "ok"}}, indent=1),
          flush=True)
    return {"batch": str(batch_dir), "status": status}


C36_D_CASES = ("MLJ_FS24_Fs0", "MLJ_FS24_Fs8")
"""C-S8-36 bundle D (spec rev. 54 250, U-S8-55 (a)): the U-S8-32 designated front fast
settlement cases, P-S8-16 (RT, the R8 preset) + F1 (plant code); judged as bundle A."""
C36_D_DIR = "D_fs24"
C36_D_REF = Path("07_results/S8/mlj_20261025_080212")
"""The MLJ batch that ran these cases before P-S8-16 / F1 (copied to the 768 ``judged/``); read
only, its ``batch.json`` gives the measured walls."""


def _batch_json_walls(batch: Path) -> dict[str, float]:
    try:
        doc = json.loads((_root_path(batch) / "batch.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {c["case_id"]: float(c["wall_s"]) for c in doc.get("cases") or []
            if isinstance(c.get("wall_s"), int | float)}


def c36_bundle_d_plan(layout: str) -> dict[str, Any]:
    """Bundle D plan: the two cases, their controller variant (R8 preset = RT on, checked on the
    preset config without building a model), measured walls of :data:`C36_D_REF` (p7e8 pool of
    six) and the makespan."""
    from outrigger_sim.control.c2 import C2Config

    table = case_table()
    cases = [table[c] for c in C36_D_CASES]
    lr = C2Config().with_10hz_d1().r8.lifted_reapproach
    rt_on = lr.retrigger_window_s is not None and lr.opposite_window_s is not None
    measured = _batch_json_walls(C36_D_REF)
    rows = []
    for c in cases:
        w = measured.get(c.case_id)
        rows.append({"case_id": c.case_id, "group": c.group, "engine": c.engine,
                     "fs_kN": c.fs_kN, "event": c.event,
                     "wall_measured_s": w, "wall_estimate_s": c.wall_estimate_s("p"),
                     "expected_run_s": expected_run_s(c), "upper_s": end_rule(c)["upper_s"]})
    walls = [r["wall_measured_s"] or r["wall_estimate_s"] for r in rows]
    p_or = "p7" if layout == "p7" else "p7e8"
    out = {"bundle": "D", "cases": rows, "layout": layout,
           "variant": "rt (R8 preset C2Config.with_10hz_d1, with_reapproach_variant(None)); F1 = "
                      "plant code (hydraulics/l2b_rod_side.py, no switch)",
           "preset_rt_on": rt_on,
           "preset_lifted_reapproach": {k: getattr(lr, k) for k in RT_KEYS},
           "settings_refresh": "not applicable: run from the start (job_l2b_s8), no branch.pkl",
           "reference_batch": str(_root_path(C36_D_REF)),
           p_or: simulate_makespan(walls, p_or),
           "basis": "measured batch.json wall_s of the MLJ batch (15 workers busy); 2 cases "
                    "on 2 P-cores alone should be shorter (ASSUMPTION)"}
    out[p_or]["makespan_min"] = out[p_or]["makespan_s"] / 60.0
    return out


def run_c36_bundle_d(layout: str, *, batch: Path | None = None, dry_run: bool = False,
                     approved: bool = False) -> dict[str, Any]:
    """C-S8-36 bundle D (U-S8-55): :data:`C36_D_CASES` through :func:`job_case` (as bundle C)
    into ``<batch>/D_fs24`` (an existing ``c36_<stamp>`` batch, never its A / B / C folders) or a
    new ``07_results/S8/c36d_<stamp>/D_fs24``. The reference MLJ batch is read only."""
    from outrigger_sim.batch import Case

    doc = c36_bundle_d_plan(layout)
    if batch is not None:
        bdir = _root_path(batch)
        if not bdir.is_dir() or not (bdir / "c36_meta.json").exists():
            raise SystemExit(f"--batch {bdir}: not a c36 batch (no c36_meta.json)")
        d_dir = bdir / C36_D_DIR
        if d_dir.exists() and any(d_dir.iterdir()):
            raise SystemExit(f"{d_dir} exists and is not empty")
        doc["out"] = str(d_dir)
    else:
        doc["out"] = f"07_results/S8/c36d_<stamp>/{C36_D_DIR}"
    print(json.dumps(s6c._plain(doc), indent=1), flush=True)
    if not doc["preset_rt_on"]:
        raise SystemExit("bundle D: the R8 preset has RT off (P-S8-16 missing)")
    if dry_run:
        return doc
    if not approved:
        raise SystemExit("bundle D needs the user's confirmation (U-S8-55): --approved "
                         "(or --dry-run)")
    if batch is None:
        d_dir = _batch_dir("c36d") / C36_D_DIR
    d_dir.mkdir(parents=True, exist_ok=True)
    from outrigger_sim.chrono import s8_plant_adapter as plant

    table = case_table()
    cases = [table[c] for c in C36_D_CASES]
    (d_dir / "batch_meta.json").write_text(json.dumps(s6c._plain(
        {"mode": "run", "set": "c36_bundle_D", "layout": layout, "cases": list(C36_D_CASES),
         "plan": plan(cases, layout), "bundle_d": doc, "plant_adapter": plant.adapter_meta(),
         "crawler_mode": os.environ.get(CRAWLER_ENV, "yaml"),
         "env": {k: os.environ.get(k) for k in ("OUTRIGGER_ROD_SIDE_MECHANICS",
                                                 "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")},
         "note": "C-S8-36 bundle D (U-S8-55, spec rev. 54 250): MLJ_FS24 Fs0 / Fs8, RT + F1"}),
        indent=1), "utf-8")
    walls = {r["case_id"]: float(r["wall_measured_s"] or r["wall_estimate_s"])
             for r in doc["cases"]}
    jobs = [Case(cid, {"duration_s": None}) for cid in C36_D_CASES]
    t0 = time.perf_counter()
    outs = run_cases_mixed(jobs, job_case, d_dir, layout=layout, timeout_s=CASE_TIMEOUT_S,
                           wall_of=lambda j: walls[j.case_id])
    status = {o.case_id: o.status for o in outs}
    for o in outs:
        if o.status != "ok":
            print(f"{o.case_id}: {o.status}\n{(o.error or '')[-2500:]}", flush=True)
    print(json.dumps({"bundle_d": str(d_dir), "wall_s": time.perf_counter() - t0,
                      "status": status}, indent=1), flush=True)
    return {"bundle_d": str(d_dir), "status": status}


# --- C-S8-41 (spec rev. 54 260 / 262.1 / 264, U-S8-56 (a)) ---------------------------------------

C37_IDS = ("ML00_ep5", "ML10_ep0", "ML21_ep1", "ML24_ep6", "ML25_ep7", "ML33_ep4", "ML34_ep7",
           "ML39_ep5", "ML42_ep6", "ML51_ep4", "ML54_ep0", "ML59_ep7", "ML71_ep6", "ML81_ep5",
           "ML87_ep1", "ML87_ep5", "ML89_ep0")
"""Spec rev. 54 260.1: the 17 bundle-A episodes with the D1 rod fallback after F1 (bundle E =
these, RT + F1 + P-S8-21, re-run from the 768 ``branch.pkl``)."""
C36_BATCH = Path("07_results/S8/c36_20261025_155317")
"""The C-S8-36 batch (read only): its ``A_rt/verify_S8ML.json`` gives the fallback list check,
its ``A_rt/episodes/*/result.json`` and ``D_fs24/batch.json`` the measured walls."""
C37_DIRS = {"E": "E_drain", "C": "C_gate", "D": "D_fs24"}


def p_s8_21_status() -> dict[str, Any]:
    """P-S8-21 (spec rev. 54 260.5) present in the controller code: ``StepReason.CHECK_DRAINING``
    and the ``TwoPressureSettings.rod_drain_hold_ratio`` default (rho, None = hold off)."""
    from outrigger_sim.control import two_pressure as tp

    member = getattr(tp.StepReason, "CHECK_DRAINING", None)
    f = getattr(tp.TwoPressureSettings, "__dataclass_fields__", {}).get("rod_drain_hold_ratio")
    rho = None if f is None else f.default
    return {"present": member is not None and isinstance(rho, int | float),
            "step_reason": None if member is None else str(member),
            "rod_drain_hold_ratio_default": rho, "module": tp.__file__}


def c37_fallback_ids(batch: Path | str = C36_BATCH) -> list[str] | None:
    """Runs of the C-S8-36 bundle A with a rod fallback warning (``ml_metrics`` of its
    ``verify_S8ML.json``); None without the file."""
    p = _root_path(batch) / "A_rt" / "verify_S8ML.json"
    if not p.exists():
        return None
    doc = json.loads(p.read_text(encoding="utf-8"))
    return sorted(c for c, m in (doc.get("ml_metrics") or {}).items()
                  if (m.get("rod_fallback") or {}).get("events"))


def c37_extra_problems(extra_ids: Sequence[str], affected: Path | str = C36_AFFECTED
                       ) -> list[str]:
    """C-S8-42 (spec rev. 55 268.3 #6 / 269.1): ``--extra-ids`` must be bundle-A episodes of
    C-S8-36 (the ``affected`` 55), outside :data:`C37_IDS` and without duplicates."""
    out = []
    a = set(c36_affected_ids(affected))
    bad = [c for c in extra_ids if c not in a]
    if bad:
        out.append(f"--extra-ids not in the C-S8-36 bundle A (affected 55): {bad}")
    dup = sorted({c for c in extra_ids if c in C37_IDS})
    if dup:
        out.append(f"--extra-ids already in the 17 (C37_IDS): {dup}")
    if len(set(extra_ids)) != len(extra_ids):
        out.append(f"--extra-ids has duplicates: {list(extra_ids)}")
    return out


def c37_jobs(layout: str, *, source: Path | str = C36_SOURCE, regression: bool = True,
             extra_ids: Sequence[str] = ()) -> dict[str, Any]:
    """Jobs and plan of the C-S8-41 re-run: bundle E (:data:`C37_IDS`, RT + F1 + P-S8-21, from
    the 768 ``branch.pkl``) and, with ``regression``, the C-S8-36 gate cases C (RE1bF / RE1bP)
    and D (MLJ_FS24 Fs0 / Fs8) run from the start. ``extra_ids`` (C-S8-42, spec rev. 55 269.1):
    bundle-A episodes outside the 17 whose replayed controller output differs from the record
    (268.3 #6), added to bundle E. Walls: measured C-S8-36 runs (same RT + F1 trajectory up to
    the first fallback), else the source / step-cost estimate."""
    from outrigger_sim.batch import Case

    extra = tuple(extra_ids)
    info = c36_jobs(source, ids_a=C37_IDS + extra, ids_b=(),
                    gate=C36_GATE if regression else ())
    problems = list(info["problems"]) + c37_extra_problems(extra)
    got = c37_fallback_ids()
    if got is None:
        problems.append(f"{C36_BATCH}/A_rt/verify_S8ML.json missing: fallback list not checked")
    elif set(got) != set(C37_IDS):
        problems.append(f"C-S8-36 A fallback runs {got} differ from spec 260.1 {list(C37_IDS)}")
    jobs = {"E": info["jobs"]["A"], "C": info["jobs"]["C"], "D": []}
    rows = []
    for r in info["rows"]:
        if r["bundle"] == "B":
            continue
        r = {**r, "bundle": "E" if r["bundle"] == "A" else r["bundle"]}
        if r["bundle"] == "E":
            # the 768 wall stays the P-core basis (as C-S8-36: its plan 37.6 min vs 28.0 min
            # measured); the C-S8-36 wall (P / E pool unknown per case) is a record column
            r["wall_c36_s"] = _measured_wall_s(_root_path(C36_BATCH) / "A_rt" / "episodes"
                                               / r["id"])
            r["variant"] = "rt + P-S8-21"
        else:  # C: process walls of the C-S8-36 pool (its result.json has no wall_s)
            w = _batch_json_walls(C36_BATCH).get(r["id"])
            if w:
                r["wall_p1r_s"], r["wall_measured_s"] = r["wall_measured_s"], w
        rows.append(r)
    if regression:
        d_walls = _batch_json_walls(C36_BATCH / C36_D_DIR) or _batch_json_walls(C36_D_REF)
        table = case_table()
        for cid in C36_D_CASES:
            c = table[cid]
            jobs["D"].append(Case(cid, {"duration_s": None}))
            rows.append({"bundle": "D", "id": cid, "variant": "rt + P-S8-21", "kind": c.event,
                         "wall_measured_s": d_walls.get(cid),
                         "wall_estimate_s": c.wall_estimate_s("p")})
    walls = [float(r.get("wall_measured_s") or r.get("wall_estimate_s") or 600.0) for r in rows]
    plan_ = {"counts": {k: len(v) for k, v in jobs.items()}, "total": len(walls),
             "wall_s": {"min": min(walls), "max": max(walls), "sum": sum(walls)},
             "basis": "E: measured result.json wall_s of the same episode in the 768 batch "
                      "(C-S8-36 basis: plan 37.6 min, measured 28.0 min for 59 jobs on p7e8); "
                      "C: C-S8-36 batch.json process walls (p7e8 pool); D: C-S8-36 D_fs24 "
                      "batch.json "
                      "(2 cases alone on p7); else the step-cost model; "
                      f"E-core x{E_CORE_FACTOR:g}"}
    for k in ("p7", "p7e8"):
        plan_[k] = simulate_makespan(walls, k)
        plan_[k]["makespan_min"] = plan_[k]["makespan_s"] / 60.0
    return {"info": info, "jobs": jobs, "rows": rows, "plan": plan_, "problems": problems,
            "fallback_ids_c36": got, "regression": regression, "layout": layout,
            "extra_ids": list(extra), "p_s8_21": p_s8_21_status()}


C37_D_DEFERRED_REF = Path("07_results/S8/mlj_20261025_080212")
"""C-S8-42 (spec rev. 55 269.3 #2): reference runs of bundle D (the original MLJ_FS24 cases)
for the per-leg deferred comparison (``judge --deferred-ref``)."""


def run_c37(layout: str, *, source: Path | str = C36_SOURCE, regression: bool = True,
            dry_run: bool = False, approved: bool = False,
            extra_ids: Sequence[str] = ()) -> dict[str, Any]:
    """C-S8-41 (U-S8-56 (a), spec rev. 54 262.1): bundle E (17 episodes, RT + F1 + P-S8-21)
    + regression C / D into a new batch ``07_results/S8/c37_<stamp>/`` with
    ``E_drain/{ml_plan.json, episodes/}``, ``C_gate/`` and ``D_fs24/``. The 768 source and the
    C-S8-36 batch are read only. Refuses to run (not to plan) without P-S8-21. ``extra_ids``
    (C-S8-42, spec rev. 55 269.1): further bundle-A episodes added to bundle E."""
    p = c37_jobs(layout, source=source, regression=regression, extra_ids=extra_ids)
    doc = {"plan": p["plan"], "rows": p["rows"], "problems": p["problems"],
           "p_s8_21": p["p_s8_21"], "source": p["info"]["source"],
           "fallback_ids_c36": p["fallback_ids_c36"], "regression": regression,
           "extra_ids": p["extra_ids"],
           "ids": {k: [c.case_id for c in v] for k, v in p["jobs"].items()},
           "out": "07_results/S8/c37_<stamp>/{E_drain/episodes, C_gate, D_fs24}",
           "judge": ["judge --batch <c37>/E_drain --ref-batch 07_results/S8/"
                     "ml_main_20261025_090131",
                     "judge --batch <c37>/C_gate --ref-batch 07_results/S8/p1r_20261024_222013 "
                     "--lookup-batch 07_results/S8/p1r_20261024_222013 "
                     "07_results/S8/rest_20261024_233615",
                     "judge --batch <c37>/D_fs24 --lookup-batch 07_results/S8/"
                     f"p1r_20261024_222013 --deferred-ref {C37_D_DEFERRED_REF.as_posix()}"]}
    print(json.dumps(s6c._plain(doc), indent=1), flush=True)
    if p["problems"]:
        raise SystemExit(f"C-S8-41 plan problems: {p['problems']}")
    if dry_run:
        return doc
    if not p["p_s8_21"]["present"]:
        raise SystemExit("C-S8-41 re-run needs P-S8-21 in two_pressure.py (CHECK_DRAINING + "
                         "rod_drain_hold_ratio); not run")
    if not approved:
        raise SystemExit("C-S8-41 re-run needs the user's confirmation: --approved (or --dry-run)")
    from outrigger_sim.chrono import s8_plant_adapter as plant

    batch_dir = _batch_dir("c37")
    dirs = {k: batch_dir / v for k, v in C37_DIRS.items()}
    env = {k: os.environ.get(k) for k in ("OUTRIGGER_ROD_SIDE_MECHANICS", "OPENBLAS_NUM_THREADS",
                                          "MKL_NUM_THREADS")}
    dirs["E"].mkdir(parents=True, exist_ok=True)
    sub = {**p["info"]["sub_plans"]["A"], "stage": "c37", "variant": "rt + P-S8-21",
           "rule": "C-S8-41 (spec rev. 54 262.1): the 17 rod-fallback episodes of C-S8-36 A "
                   "re-run from the source batch branch.pkl (bases read only, not copied), "
                   "RT + F1 + P-S8-21",
           "extra_ids": p["extra_ids"]}  # C-S8-42 (spec rev. 55 269.1)
    (dirs["E"] / "ml_plan.json").write_text(json.dumps(s6c._plain(sub), indent=1), "utf-8")
    table = case_table()
    for k, ids, note in (("C", C36_GATE, "C-S8-41 regression C (RT + F1 + P-S8-21)"),
                         ("D", C36_D_CASES, "C-S8-41 regression D (RT + F1 + P-S8-21)")):
        if not p["jobs"][k]:
            continue
        dirs[k].mkdir(parents=True, exist_ok=True)
        cs = [table[c] for c in ids]
        (dirs[k] / "batch_meta.json").write_text(json.dumps(s6c._plain(
            {"mode": "run", "set": f"c37_{k}", "layout": layout, "cases": list(ids),
             "plan": plan(cs, layout), "plant_adapter": plant.adapter_meta(),
             "crawler_mode": os.environ.get(CRAWLER_ENV, "yaml"), "env": env,
             "p_s8_21": p["p_s8_21"], "note": note}), indent=1), "utf-8")
    (batch_dir / "c37_meta.json").write_text(json.dumps(s6c._plain(
        {**doc, "batch": str(batch_dir), "layout": layout, "env": env}), indent=1), "utf-8")
    where: dict[int, Path] = {}
    walls: dict[int, float] = {}
    all_jobs = []
    for k in ("E", "C", "D"):
        out_dir = dirs[k] / "episodes" if k == "E" else dirs[k]
        for j in p["jobs"][k]:
            r = next(x for x in p["rows"] if x["bundle"] == k and x["id"] == j.case_id)
            where[id(j)] = out_dir
            walls[id(j)] = float(r.get("wall_measured_s") or r.get("wall_estimate_s") or 600.0)
            all_jobs.append(j)
    t0 = time.perf_counter()
    outs = run_cases_mixed(all_jobs, job_case, batch_dir, layout=layout,
                           timeout_s=CASE_TIMEOUT_S, wall_of=lambda j: walls[id(j)],
                           dir_of=lambda j: where[id(j)])
    status = {}
    for j, o in zip(sorted(all_jobs, key=lambda j: -walls[id(j)]), outs):
        status[f"{where[id(j)].relative_to(batch_dir)}/{o.case_id}"] = o.status
        if o.status != "ok":
            print(f"{o.case_id}: {o.status}\n{(o.error or '')[-2500:]}", flush=True)
    print(json.dumps({"batch": str(batch_dir), "wall_s": time.perf_counter() - t0,
                      "failed": {k: v for k, v in status.items() if v != "ok"}}, indent=1),
          flush=True)
    return {"batch": str(batch_dir), "status": status}


def smoke_c36(episode_id: str, out_dir: Path, *, episode_s: float, variant: str = "rt",
              source: Path | str = C36_SOURCE) -> dict[str, Any]:
    """C-S8-36 smoke (single process): one episode of the source batch, shortened, written to
    ``out_dir/<id>``; returns the RT evidence (re-approach events, ``is_retrigger`` meta, the
    refreshed settings and the first-period compare)."""
    src = _root_path(source)
    rp = ml_resume_plan(src, failed_only=False, only=[episode_id])
    if not rp["rerun"] or not rp["plan_matches_code"]:
        raise SystemExit(f"smoke: {episode_id} not runnable from {src}: {rp['mismatch']}")
    e = rp["rerun"][0]
    b = rp["bases"][e["base_id"]]
    ep = next(x for x in rp["episodes"][e["base_id"]] if x["episode_id"] == episode_id)
    case_dir = Path(out_dir) / episode_id
    if case_dir.exists():
        raise SystemExit(f"smoke: {case_dir} exists")
    case_dir.mkdir(parents=True)
    t0 = time.perf_counter()
    summary = job_ml_episode(MLBase(**_tuples(b)), ep, src / "bases" / e["base_id"], case_dir,
                             episode_s=episode_s, variant=variant)
    (case_dir / "result.json").write_text(json.dumps(s6c._plain(summary), indent=1), "utf-8")
    cm = summary["controller_meta"]
    names = json.loads((case_dir / "controller_events.json").read_text(encoding="utf-8"))
    t_ev = float(summary["event_t_s"])
    reapp = [n for n in names if "reapproach" in n]
    refresh = summary["settings"]["settings_refreshed"]
    return {"case_dir": str(case_dir), "wall_s": time.perf_counter() - t0,
            "episode": ep, "event_t_s": t_ev, "episode_s": episode_s, "variant": variant,
            "reapproach_events": reapp,
            "deferred_events": [n for n in reapp if "deferred" in n],
            # C-S8-41: P-S8-21 evidence (D1 rod fallback vs the check_draining explanation)
            "rod_pressure_events": [n for n in names if "ROD_PRESSURE" in n
                                    or "check_draining" in n or ":rod:" in n],
            "p_s8_21": p_s8_21_status(),
            "lifted_reapproach_meta": cm.get("lifted_reapproach"),
            "first_period_compare": summary["first_period_compare"],
            "refresh_lifted_reapproach": refresh.get("lifted_reapproach"),
            "refresh_changed_rt_fields": [f for r in refresh.get("replaced", [])
                                          for f in r.get("changed_fields", [])
                                          if "lifted_reapproach" in f["path"]],
            "refresh_added": refresh.get("added")}


def smoke_branch(seconds_before: float = 0.5, seconds_after: float = 1.0, *,
                 work_dir: Path | None = None, case_id: str = "smoke_E_G4_Fs0"
                 ) -> dict[str, Any]:
    """C-S8-4 continuity check (single process): run an F_s 0 smoke case ``seconds_before``,
    branch, continue ``seconds_after`` (reference, chunked); restore into a fresh build and
    resume the same time; max body position difference (criterion <= 1e-9 m)."""
    import numpy as np

    from outrigger_sim.chrono.l2b_engine import L2bEngine
    from outrigger_sim.runner import run_closed_loop
    from outrigger_sim.sensors.hydraulic import LegSensorConfig
    from outrigger_sim.sensors.imu import imu_config_for_grade
    from outrigger_sim.sensors.suite import SensorSuite

    case = case_table()[case_id]
    sc = case.scenario

    def build():
        model, patches, params, params_ctrl, *_ = build_l2b(case, patch_legs=("RR",))
        return model, params_ctrl, params

    model, params_ctrl, params_plant = build()
    s7c.settle_l2b(model, 0.2)
    eng = L2bEngine(model, imu_method="chrono_point")
    suite = SensorSuite(imu_config_for_grade(sc.grade, sample_period_s=s6c.IMU_SAMPLE_PERIOD_S),
                        LegSensorConfig(), seed=sc.seed)
    c2, *_ = _controller(case, params_ctrl, params_plant)
    run_closed_loop(eng, c2, suite, seconds_before, placement=None)
    work = RESULTS if work_dir is None else Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    path = work / "_smoke_branch.pkl"
    save_branch(path, eng, c2, suite)
    run_closed_loop(eng, c2, suite, seconds_after, placement=None,
                    resume_command=eng.held_command)
    ref = np.array([[b.GetPos().x, b.GetPos().y, b.GetPos().z] for b in model.bodies])
    ref_f = model.actuator.force_N
    model2, *_ = build()
    eng2 = L2bEngine(model2, imu_method="chrono_point")
    with open(path, "rb") as fh:
        blob = pickle.load(fh)  # noqa: S301
    c2b, suite_b, held = restore_branch(blob, eng2)
    run_closed_loop(eng2, c2b, suite_b, seconds_after, placement=None, resume_command=held)
    got = np.array([[b.GetPos().x, b.GetPos().y, b.GetPos().z] for b in model2.bodies])
    path.unlink(missing_ok=True)
    out = {"max_pos_diff_m": float(np.abs(got - ref).max()),
           "max_force_diff_N": float(np.abs(model2.actuator.force_N - ref_f).max()),
           "criterion_m": 1e-9, "t_branch_s": blob["t_s"], "after_s": seconds_after}
    # unsplit reference: one run_closed_loop over the whole time (resume == uninterrupted)
    model3, params_ctrl3, params_plant3 = build()
    s7c.settle_l2b(model3, 0.2)
    eng3 = L2bEngine(model3, imu_method="chrono_point")
    suite3 = SensorSuite(imu_config_for_grade(sc.grade, sample_period_s=s6c.IMU_SAMPLE_PERIOD_S),
                         LegSensorConfig(), seed=sc.seed)
    c3, *_ = _controller(case, params_ctrl3, params_plant3)
    run_closed_loop(eng3, c3, suite3, seconds_before + seconds_after, placement=None)
    one = np.array([[b.GetPos().x, b.GetPos().y, b.GetPos().z] for b in model3.bodies])
    out["max_pos_diff_split_vs_unsplit_m"] = float(np.abs(one - ref).max())
    out["passed"] = out["max_pos_diff_m"] <= 1e-9 and \
        out["max_pos_diff_split_vs_unsplit_m"] <= 1e-9
    eng.close()
    eng2.close()
    eng3.close()
    return out


def build_snapshots(jobs: int) -> None:
    """L1 start states of the L group floors (s6c snapshot job)."""
    from outrigger_sim.batch import Case, run_cases

    todo = [f for f in OPERATING_FLOORS
            if not (s6c.STATES / f"{st.snapshot_name('top', f)}.npz").exists()]
    if not todo:
        print("all L-group snapshots exist")
        return
    out = _batch_dir("snapshots_L1R")
    rep = run_cases([Case(st.snapshot_name("top", f), {"level": "top", "floor": f}) for f in todo],
                    s6c.job_snapshot_case, out, max_workers=min(jobs, P_WORKERS),
                    placement="pcore", timeout_s=1800.0)
    for o in rep.outcomes:
        print(f"{o.case_id}: {o.status} {o.wall_s:.1f}s", flush=True)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("list", "plan", "check", "run", "ml", "ml-plan", "judge",
                                       "snaps", "smoke-branch", "c36"))
    ap.add_argument("--rerun-from", dest="rerun_from", default=str(C36_SOURCE),
                    help="c36: source ML batch (bases / branch.pkl / plan, read only)")
    ap.add_argument("--affected", default=str(C36_AFFECTED),
                    help="c36: JSON with the 'affected' episode list (bundle A)")
    ap.add_argument("--smoke", help="c36: run this one episode shortened (--episode-s) into "
                                    "--out (single process, no batch)")
    ap.add_argument("--variant", choices=REAPPROACH_VARIANTS, default="rt",
                    help="c36 --smoke: re-approach variant")
    ap.add_argument("--set", dest="case_set", choices=SET_NAMES, default="p1")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--workers", choices=tuple(WORKER_LAYOUTS), default="p7e8")
    ap.add_argument("--approved", action="store_true")
    ap.add_argument("--duration", type=float, default=CHECK_DURATION_S)
    ap.add_argument("--batch")
    ap.add_argument("--out")
    ap.add_argument("--ref-batch", dest="ref_batch",
                    help="judge: earlier batch for the 213.6 TOUCH regression row (C-S8-19 ⑦); "
                         "ML batch: reference of the twist-work FLAG row (C-S8-40)")
    ap.add_argument("--bundle", choices=("D", "E"),
                    help="c36: C-S8-36 bundle D alone (U-S8-55: MLJ_FS24_Fs0 / Fs8, P-S8-16 + "
                         "F1) into <--batch>/D_fs24 (an existing c36 batch) or a new "
                         "07_results/S8/c36d_<stamp>/D_fs24; E = C-S8-41 re-run (U-S8-56 (a)): "
                         "the 17 rod-fallback episodes, RT + F1 + P-S8-21, + regression C / D, "
                         "into a new 07_results/S8/c37_<stamp>/")
    ap.add_argument("--no-regression", dest="regression", action="store_false",
                    help="c36 --bundle E: only the 17 episodes (no C / D regression cases)")
    ap.add_argument("--extra-ids", dest="extra_ids", default="",
                    help="c36 --bundle E (C-S8-42, spec rev. 55 269.1): comma-separated bundle-A "
                         "episodes outside the 17 to add to bundle E (replayed controller output "
                         "differs from the record, 268.3 #6)")
    ap.add_argument("--deferred-ref", dest="deferred_ref",
                    help="judge (run_S8C batch, C-S8-42): folder with the reference run of each "
                         "case for the per-leg deferred comparison (bundle D: "
                         "07_results/S8/mlj_20261025_080212); ML batches use --ref-batch / "
                         "rerun_from")
    ap.add_argument("--lookup-batch", dest="lookup_batch", nargs="*", action="extend",
                    default=[],
                    help="judge: batches used only to look up twins (C11 L1, CB pilot-check, "
                         "auger levels), never as the regression reference (C-S8-26 ①, "
                         "spec 217.8); repeatable")
    ap.add_argument("--crawler", choices=("yaml", "rigid", "compliant"), default="yaml",
                    help="L2b crawler contact (U-S8-L3); yaml = contact.crawler.L2b_NSC.model")
    ap.add_argument("--resume", help="ml: existing ML batch folder to re-run episodes of "
                                     "(bases / branch.pkl reused)")
    ap.add_argument("--failed-only", dest="failed_only", action="store_true",
                    help="ml --resume: only the failed episodes (case.log 'failed' or no "
                         "result.json)")
    ap.add_argument("--all-episodes", dest="all_episodes", action="store_true",
                    help="ml --resume: every planned episode (U-S8-29, C-S8-25 ④); the old "
                         "folders are kept in episodes/_replaced_<stamp>/")
    ap.add_argument("--dry-run", dest="dry_run", action="store_true",
                    help="print the plan, change nothing (ml --resume: the re-run plan; ml: "
                         "the stage plan; run / check: the set plan)")
    ap.add_argument("--episode-s", dest="episode_s", type=float,
                    help="ml --resume: shorter episode (smoke test only)")
    ap.add_argument("--stage", choices=tuple(ML_STAGES), default="pilot",
                    help="ml / ml-plan: pilot (24 x 8) or main (96 x 8 = 768, U-S8-34 retract "
                         "speed, the six MLJ judged cases in the base phase; U-S8-35)")
    ap.add_argument("--mlj-from", dest="mlj_from",
                    help="ml --stage main: reuse the MLJ cases of this separate `run --set mlj` "
                         "batch (copied to judged/, not run again; U-S8-40)")
    ap.add_argument("--skip-judged", dest="skip_judged", action="store_true",
                    help="ml --stage main: no MLJ judged cases in the batch (U-S8-40)")
    args = ap.parse_args(argv)
    os.environ[CRAWLER_ENV] = args.crawler
    if args.action == "smoke-branch":
        print(json.dumps(smoke_branch(case_id=(args.only or ["smoke_E_G4_Fs0"])[0]), indent=1))
        return
    if args.action == "snaps":
        build_snapshots(P_WORKERS)
        return
    if args.action == "c36":
        if args.smoke:
            if not args.out or args.episode_s is None:
                raise SystemExit("c36 --smoke needs --out <dir> and --episode-s <s>")
            print(json.dumps(s6c._plain(smoke_c36(args.smoke, Path(args.out),
                                                  episode_s=args.episode_s,
                                                  variant=args.variant,
                                                  source=args.rerun_from)), indent=1))
            return
        if args.bundle == "D":
            run_c36_bundle_d(args.workers, batch=None if not args.batch else Path(args.batch),
                             dry_run=args.dry_run, approved=args.approved)
            return
        if args.bundle == "E":  # C-S8-41
            run_c37(args.workers, source=args.rerun_from, regression=args.regression,
                    dry_run=args.dry_run, approved=args.approved,
                    extra_ids=[c.strip() for c in args.extra_ids.split(",") if c.strip()])
            return
        if args.extra_ids:
            raise SystemExit("--extra-ids only with c36 --bundle E")
        run_c36(args.workers, source=args.rerun_from, affected=args.affected,
                dry_run=args.dry_run, approved=args.approved)
        return
    mlj_from = None if not args.mlj_from else Path(args.mlj_from)
    if (mlj_from is not None or args.skip_judged) and args.action not in ("ml", "ml-plan"):
        raise SystemExit("--mlj-from / --skip-judged only with ml / ml-plan")
    if args.action == "ml-plan":
        mode = _judged_mode(args.stage, mlj_from, args.skip_judged)
        doc = ml_plan(args.stage, mode)
        if mode == "reuse":
            doc["mlj_reuse"] = check_mlj_batch(mlj_from)
        print(json.dumps(s6c._plain(doc), indent=1))
        return
    if args.action == "judge":
        from outrigger_sim.verify.s8_control import judge_batch, judge_ml_batch

        batch = Path(args.batch)
        out = None if not args.out else Path(args.out)
        if (batch / "ml_plan.json").exists():  # ML batch: ML-0 ... ML-3 (+ rev. 47 / 48 rows)
            # C-S8-40: --ref-batch = reference of the twist-work FLAG row (default: the
            # C-S8-36 sub-plan rerun_from)
            p = judge_ml_batch(batch, out, ref_batch=None if not args.ref_batch
                               else Path(args.ref_batch))
            print("->", p)
            # C-S8-41: summary incl. the ML-0 rod fallback gate and the ML-1 count
            print(json.dumps(json.loads(p.read_text(encoding="utf-8"))["meta"]["summary"],
                             indent=1, ensure_ascii=False), flush=True)
            judged = batch / "judged"
            if judged.exists() and any((p / "result.json").exists() for p in judged.iterdir()
                                       if p.is_dir()):  # main stage: the MLJ cases
                print("->", judge_batch(judged, None if out is None
                                        else out.with_name(out.stem + "_judged.json"),
                                        lookup_batches=[Path(b) for b in args.lookup_batch]))
            return
        p = judge_batch(batch, out,
                        ref_batch=None if not args.ref_batch else Path(args.ref_batch),
                        lookup_batches=[Path(b) for b in args.lookup_batch],
                        deferred_ref=None if not args.deferred_ref else Path(args.deferred_ref))
        print("->", p)
        print(json.dumps(json.loads(p.read_text(encoding="utf-8"))["meta"]["summary"],
                         indent=1, ensure_ascii=False), flush=True)  # C-S8-41
        return
    if args.action == "ml" and args.resume:
        modes = sum(bool(x) for x in (args.failed_only, args.all_episodes, args.only))
        if modes != 1:
            raise SystemExit("ml --resume needs exactly one of --failed-only, --all-episodes, "
                             "--only <episode ids>")
        if not args.approved and not args.dry_run:
            raise SystemExit("ML re-run needs the user's confirmation: --approved (or --dry-run)")
        run_ml_resume(Path(args.resume), args.workers, failed_only=args.failed_only,
                      only=args.only, dry_run=args.dry_run, episode_s=args.episode_s)
        return
    if args.action == "ml":
        mode = _judged_mode(args.stage, mlj_from, args.skip_judged)
        if args.dry_run:  # plan only, nothing runs
            doc = ml_plan(args.stage, mode)
            if mode == "reuse":
                doc["mlj_reuse"] = check_mlj_batch(mlj_from)
            print(json.dumps(s6c._plain(doc), indent=1))
            return
        if not args.approved:
            raise SystemExit(f"ML {args.stage} batch needs the user's confirmation: --approved")
        run_ml(args.workers, args.stage, mlj_from=mlj_from, skip_judged=args.skip_judged)
        return
    cases = case_set(args.case_set)
    if args.only:
        table = case_table()
        cases = [table[c] for c in args.only]
    if args.action == "list":
        for c in cases:
            print(f"{c.group:5s} p{c.priority} {c.case_id:34s} {c.engine:8s} Fs {c.fs_kN:3g} kN "
                  f"{c.contact:8s} {c.event or '-':6s} {c.duration_s:6.1f} s "
                  f"~{c.wall_estimate_s():5.0f} s")
        print(f"{len(cases)} cases")
        return
    if args.action == "plan" or (args.action in ("run", "check") and args.dry_run):
        doc = plan(cases, args.workers)
        print(json.dumps(s6c._plain({k: v for k, v in doc.items() if k != "cases"}), indent=1))
        if args.dry_run:
            print(json.dumps({"dry_run": args.action, "set": args.case_set,
                              "cases": [c.case_id for c in cases],
                              "out": f"07_results/S8/{args.case_set}_<stamp>"}, indent=1))
        return
    if args.action == "check":
        run_batch(cases, tag=args.case_set, layout=args.workers, check=True,
                  duration_s=args.duration)
        return
    if not args.approved:
        raise SystemExit("S8 main run needs the user's confirmation: add --approved")
    run_batch(cases, tag=args.case_set, layout=args.workers, check=False, duration_s=0.0)


if __name__ == "__main__":
    main(sys.argv[1:])
