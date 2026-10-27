"""S8 control ③ re-judgement: rows C1-C11, F1-F10, item 9 (M1-M5, I1-I5), rev. 40 rules.

``00_docs/04_control/s6_control_spec.md`` rev. 39 201 (C / F rows), 203 (item 9), rev. 40 210.2
(R40-1 ... R40-6, C-S8-7); ``dynamics_model.md`` 5.25.5 (S8-L1 / L2: 8 s after the crawler
lift-off). Inputs: the case directories of ``04_scripts/02_chrono/run_S8C.py`` (``record/``,
``pads.npz`` from ``chrono/l2b_pad_record_s8``, ``s8_series.npz``, ``r8_series.npz``,
``result.json`` with ``settings.s8``). ``verify/s7_control.py`` is not changed (C-S8-9); its
loader and slow-component helpers are reused.

Rows (``passed`` True / False judged, None = record; ``kind`` judged / record / hold / report):

* bundle-C rows of every case (``verify.s6_bundle_c.judge``), except its D8 minimum row, which
  the C1 row below replaces;
* **C1** (R40-1 / R40-2): D8 minimum of the 1 ms true rod axial force ``pads.F_cyl_min_interval``
  after the crawler lift-off, outside REANCHOR, before a floor event; judged raw against
  ``F_min + 5 kN``. Record columns: the 1 s centred-mean (slow) minimum, its leg and time, the
  raw minimum's time after lift-off. **Hold** (``kind`` "hold", ``passed`` None, rigid crawler
  runs only, R40-6 meta ``crawler_contact`` absent = rigid): raw below the limit, its time within
  :data:`LIFTOFF_WINDOW_S` of the lift-off, slow minimum over the same span >= the limit;
* **C10 / C11 / F5 / F6 / F9** pair rows against the F_s 0 twin (``s8.pair_fs0`` in the batch, or
  ``s8.pair_fs0_external`` = an S7 run) or the L1 twin (C11, F_s 0 only), computed after
  lift-off + 8 s or in the READY window (R40-4); C11 keeps the C-R18 slow flag (1.84 kN) and adds
  the raw difference, half-amplitudes 0-3 s / 3-8 s per leg and the lift-off + 8 s .. READY
  minimum difference (R40-3);
* **F1** reading error ``eps = F_hat - F`` per phase, ``|eps| <= F_s,leg + sensor share``;
  **F2** lower-bound soundness ``F_lower - F <= sensor share`` after lift-off (combined cases);
  **F3** ``F_band >= max F_s`` after the first probe; **F4** CHECK ``F_s,air`` (record);
  **F7** first re-approach after an RE1b event <= 0.3 s (combined, judged);
  **F8** event-free READY: no READY exit, R-5, probe abort, re-approach (judged);
  **F10** periods with ``F_lower < F_min + 7.5 kN`` and a retract command (record);
* **item 9** (203): per case the truth classification of every 10 Hz window (L: ``min F + m g <=
  0.5 kN``, U: ``min F < F_min``, G), episodes, the offline judgements J_P (``F_hat``) and J_C
  (``F_lower``) at judgement level (``< F_min``) and action level (``< F_min + 7.5 kN``,
  re-approach ``< F_min / 2``), M1 / M1' / M2 / M3 / M4 / M5; episodes that start within 8 s
  of a rigid-crawler lift-off carry ``crawler_transient`` (R40-5: counted in the gates, shown
  apart). R-5, GE2 and probe verdicts are not replayed here: the replay judge is python-expert's
  P-S8-1 (``control/contact_replay``, ``contact_episode``, ``verify/contact_metrics``; continuous
  watch, :func:`replay_item9`); when it cannot run, this module's level-only fallback is used
  and the rows say so;
* **I1 ... I5** and the conclusion row over the item-9 cases (N group + their E / K pairs).

Rev. 41 (``s6_control_spec.md`` 211, C-S8-10 ... 13) and dynamics 5.26.10 (S8-A2 / A3):

* **I4** per case against ``06_analysis/02_control/s8/s8_i4_expected.json`` (``p_miss``,
  ``item6``, ``reapproach``; ``n/a`` / ``if_lift`` rules, :func:`i4_classify`,
  :func:`i4_compare`) + batch summary (gate);
* **R41-3** K0V against its S7 L2b run (``s8.ref_s7``, record with a flag); the K8 / K24
  verification cases pair with K0V in the same batch (R41-2);
* **R41-4**: F_s pair rows of twins with another crawler contact give ``passed`` /
  ``report_cause`` None;
* **I1** lists ``sampling_only`` episodes (missed at judgement level, action level within
  ``t_on + tau_d``), still counted in the gate (U-S8-7 pending);
* **S8-A2**: airborne samples (20 ms pad normal <= 0) use the 20 ms mean rod force instead of
  the 1 ms minimum in C1, the pair windows and I4 ``item6`` (:func:`judged_force_min`); the 203.1
  window classes stay on the 1 ms minimum (airborne = L anyway); air values are recorded;
* **S8-A3**: band-edge chatter counts and S8-A1 head-floor hits (record);
* **C-S8-14** (rev. 42 212): RR summary of the E-group G4 runs (:func:`g4_rr_summary`, one
  batch record row with every case); **S8-L5** batch crawler label row.

Rev. 43 (``s6_control_spec.md`` 213.5 / 213.8 C-S8-16, U-S8-13):

* ① F2, the J_C fallback judgement, M4 and F10 use the spec-199 lower bound
  ``F_hat_cal - F_band,i`` (:func:`lower_estimate_series`: ``F_lower_est_N`` of the run, else
  ``F_lower_N - leg_band_N``); ``F_lower_N`` is the controller's reading lower bound
  ``last_forces.lower`` (calibrated, E-6 deduction, no band);
* ② F1 on the calibrated reading outside CHECK with the share 0.6 kN + 0.025 |F| (R43-1); the
  raw reading and the near-F_min share (0.85 kN) are record rows;
* ③ L2b-NSC floor events: floor point = contact point (:func:`l2b_floor_point_metrics`);
* ④ I4 ``p_miss`` counts ``crawler_transient`` episodes (R40-5);
* ⑤ :func:`apply_rev43_rows`: 7c of F_s > 0 cases a record + F5 pair row (R43-2), H4 one-sided
  tolerance (R43-3) + F6 reduction record, ``run`` rows with ``end_cause`` (R43-4).

Rev. 44 (``s6_control_spec.md`` 214.10 C-S8-19, U-S8-15 ... 17):

* ① F1 WIKA constant share 0.6 -> 0.85 kN (:data:`F1_CONST_SHARE_N`); ② airborne residual
  record row ``|F_hat_cal - F + f|`` (F < 0.5 kN, no contact, flag 1.3 kN, :func:`air_residual`);
* ③ 7c split record rows ``E - T2`` (estimator bias) and ``T2 - T0`` (probe round-trip
  hysteresis) (:func:`probe_7c_split`, ``s8p1r_7c.py`` definitions; ``T2`` =
  ``s6_control`` ``truth_end_kN``), also in the F5 pair row;
* ④ ``score_ex_transient`` per R42-3 (:func:`score_ex_transient`: ``scored = ~window``);
* ⑤ G4 summary: scale in use / raw ratio at the event, per-round scale history (runner
  ``result.json twist_stiffness_history``, else :func:`reconstruct_twist_history`), RR lower
  bound at the re-approach start beside 1.4 F_min;
* ⑦ 213.6 rerun acceptance rows (:func:`r44_gate_rows`, ``s8p1r_gate.py`` definitions; the
  TOUCH regression row needs ``ref_batch``).

Rev. 45 (``s6_control_spec.md`` 215, C-S8-21, U-S8-18 / 19; replaces C-S8-19 ① / ②):

* **F1** (R45-1) judges the reading law on the raw reading: ``r = F_hat - (F - f + E_s)`` with
  the static sensor error ``E_s = e_h(p_h) A_p - e_r(p_r) A_ann`` of the drawn terms
  (``runner.sensors.pressure_error_terms``, :func:`sensor_static_error_N`) at the 1 ms pad
  pressures of the same instant; max row ``|r| <= 6 sigma_F + 0.1 kN`` (front 1.76 / rear
  1.30 kN, ideal sensor sigma 0 -> 0.1 kN) and, for a noisy sensor, the per-leg statistics row
  ``|mean r| <= 0.1 kN``, ``std r / sigma_F`` in [0.85, 1.15] (:func:`f1_law_metrics`). Records
  without the law terms use the fallback (b) 1.3 kN (:data:`F1_FALLBACK_CONST_N`), marked;
  the rev. 44 calibrated-reading rule stays as a record row;
* **R45-2** near-F_min record rows (WIKA): static part ``max |E_s - c_sens|`` (flag 0.65 kN),
  zero-calibration friction ``c_fric = c_i - c_sens - c_noise`` (flag ``max(0.1 kN, 0.065
  F_s,leg)``, + = reads low), noise ``std / sigma_F`` and ``max |n| / sigma_F``, total
  ``max |F_hat_cal - F + f|`` (flag 1.6 kN) (:func:`calibration_split`, :func:`error_split`);
* **R45-3** airborne residual flag 1.3 -> 1.7 kN with the same three parts;
* **R45-4** low-load probe F2 record (:func:`low_load_probe_records`): probes whose round-start
  lower bound ``F_hat_cal - F_band`` is below ``F_min + 15 kN``; over 2 s from the leg's second
  hold end the F2 margin, the true margin, ``T2 - T0``, ``E - T2`` and the reconstructed
  ``_leg_to_reground`` decision.

Rev. 46 (``s6_control_spec.md`` 216.7 ①-⑦, C-S8-22, U-S8-21 / 22 / 24 / 25):

* ① pressure-only cases (``contact`` = pressure, item-9 N group): the closed-loop F_min rows
  (:data:`PRESSURE_COMPARISON_PREFIXES`) are item-9 M5 comparison rows (``kind``
  "comparison", ``passed`` None, ``passed_raw`` kept); I4 judges the expected classes;
* ② auger level trend (J4) grouped by (floor, F_s, combined judge, beta 1.0, ideal sensor,
  engine, lock valve) with the missing levels taken from the reference / lookup batches
  (:func:`level_trend_rows_s8`); the s6 rows that mixed the groups are ``superseded``;
* ③ the forced (open-loop) window of RE1c / ML retract episodes (:func:`forced_window`: forced
  start .. run end, ``ForcedRetract`` holds every leg after the start) is left out of F2 and the
  I1 F2 count and recorded apart (U-S8-24);
* ④ ``WARN_ROD_PRESSURE_FALLBACK`` outside the forced window of a case without a rod-sensor
  fault injection is an unexpected warning: counted in the 5.24.2 row and failing the 72.1 (6)
  row (:func:`rod_fallback_events`); inside the forced window it is a record;
* ⑤ C11 ``pair_l1`` twins are looked up in the reference / lookup batches too;
* ⑥ R46-1 calibration-friction flag: 0.1 kN at ``F_s,leg`` = 0, 0.75 kN at ``F_s,leg`` > 0
  (:func:`friction_flag_limit_N`), also for the ideal-sensor "F1 near F_min" row (U-S8-25);
* ⑦ ML pilot judge :func:`judge_ml_batch` (ML-0 data health, ML-1 forced-window mask and
  fallback record, ML-2 fallback cause report, ML-3 R45-4);
* control 216.6 (1): the WIKA residual standard deviation is checked per side pooled over the
  WIKA runs of the batch (record, +-3 %, :func:`pooled_side_std`); per leg the R45-1 ② band.

C-S8-27 (spec rev. 48 218.13, U-S8-32 / 34): ① every settlement episode with a lift is split
into event legs (settled + diagonal: cumulative lift <= 1.8 s, last re-contact <= event + 3.0 s
(U-S8-37, rev. 49 219.3; the former 2.5 s gate is a nominal-damping flag column only),
FAULT 0; ASSUMPTION) and adjacent legs (U57 physical window gate), :func:`settle_lift_split`;
② FAULT rows carry ``INFO_HEAD_PRESSURE_FAULT_REASON``; ③ forced-retract events (true F < F_min
/ lift inside and after the window, :func:`forced_event_record`); ④ ``ml_masks`` = FAULT entry
.. run end (:func:`ml_episode_mask`); the ``ForcedRetract(others='controller')`` window is not
masked any more (U-S8-34), its products stay record rows. Judged cases of the main ML batch
(group ``MLJ``: front fast settlement, C-S8-24 R45-4, C-S8-29 rod fault) get
:func:`mlj_rows` in :func:`judge_batch`.

C-S8-33 (spec rev. 50 220.6, U-S8-41..43): ① / ② in ``s6_control`` (fast ``result.event``
settlement = floor-event case with the U-S8-32 window of :func:`settle_lift_split`; item 4
moving threshold 1e-6 m/s); ③ a rod fallback warning of the injected leg within [fault time,
+ 2 periods] is expected and left out of the 5.24.2 FLAG (:func:`mark_expected_rod_fallback`);
④ C-S8-29 record: ``guard_cap_s`` from ``r8_series`` ``cmp_guard_u`` (the former ``issued_u``
count is ``push_cap_s``), ``h*`` / ``h_a`` / ``R_ub`` per lock window
(:func:`lock_window_h_star`), the F1 calibrated record row without the faulty leg after the
fault; ⑤ C-S8-24 record: round-start lower bounds of the requested probe against
``F_min + 15 kN`` (:func:`requested_probe_round_lower`); ⑥ ``judge_revision``.

C-S8-34 (spec rev. 51 225, U-S8-44 / 47), ML judge only: ① the un-injected FAULT entries are
split by cause (:func:`classify_fault`: P-S8-17 ``FAULT_STROKE_END`` event, sensor fault events,
else the 10 Hz stroke record); a stroke-end FAULT is a protective stop judged per run by U-S8-44
(:func:`stroke_end_protective`), the other FAULTs keep the 0 gate; ② the U-S8-32 event-leg row
records such a FAULT without failing on it (``settle_lift_split(fault_gate=False)``); ③ the ML-2
rod fallback report gives the commands applied in the period (d = 1) and the plant lock state
(:func:`rod_fallback_command_context`); ④ ML tags ``fault_tail``, ``plant_rod_collapse``
(:func:`plant_rod_collapse`) and ``reapproach_pingpong`` (:func:`reapproach_pingpong`) per run in
``ml_metrics`` and in ``ml_tags``, with record rows. H-S8-4 (hydraulics 12.6) addition: the
collapse windows of an overlap / boundary release end at re-contact + 0.1 s, and the other F1
release reading steps get ``plant_release_rod_step`` (:func:`plant_release_steps`,
:func:`link_collapse_releases`).

C-S8-37 (spec rev. 52 230 / 232, U-S8-49 / 51): ① the item-9 replay (:func:`replay_item9`)
judges on the corrected reading (``lower_reading_N`` / ``net_force_N`` + 0.5 kN on the 10 Hz
samples whose pad normal force, ``pads.N_raw`` interpolated at the sample time, is < 1.5 kN;
:func:`reading_variants`) - this is the default the M1 / M1' / M4 rows and I1 / I3 use; the
raw reading is kept as record rows (``replay.raw``) and the ``F_seal_limit,i - m_i g`` ceiling
on lifted legs as sensitivity rows (``replay.upper_sensitivity``); ② the RT record of every
event run (:func:`reapproach_rt_record`: re-approach runs after the event, ``is_retrigger``
count, ``leg_reapproach_deferred`` starts) and the twist-mode actuator work per 0.5 s bin
(:func:`twist_work_bins`, judged <= +20 J after event + 1.5 s for the runs of the C-S8-36 RT
variant, record otherwise; :func:`rt_rows`), in the ML judge and in :func:`judge_batch`.

C-S8-40 (spec rev. 54 248.3 / 249 / 251): ① the twist-work row becomes the recurrence ban
(:func:`twist_work_bins`: power 0 in the forced window [start, ``done_s`` + 0.1 s],
:func:`work_clusters` of judged bins > +20 J after event + 1.5 s, judged ``n_clusters`` <= 1 for
RT-variant runs; records: rev. 52 unmasked bin max, masked bin max / largest cluster, and with a
reference batch (``judge_ml_batch(ref_batch=...)`` or the C-S8-36 sub-plan ``rerun_from``) the
FLAG row RT - reference > +20 J); ② the item-9 default reading adds ``delta_i = min(0.5 kN,
2 F_s,i)`` only on L2b-NSC legs with ``F_s,i`` > 0 (:func:`reading_bias_delta_N`); the rev. 52
all-apply +0.5 kN is a sensitivity variant (``replay.all_apply``) with a difference row.

C-S8-41 (spec rev. 54 260.5 / 261 / 264, U-S8-56 (a) / U-S8-57 (a)): ① ML-0 gate row "no
rod-pressure fallback without a sensor-fault injection" (:func:`rod_fallback_gate`; the ML-1
record and ML-2 cause rows stay); ② record row over the RT-variant runs: true minimum of each
deferred leg from the deferral to its next re-approach start + 0.3 s, FLAG below F_min
(:func:`deferred_leg_minimum`, :func:`deferred_min_rows`), in the ML judge and in
:func:`judge_batch`; ③ ``meta.summary`` (:func:`judge_summary`) with the ML-1 count.

C-S8-42 (spec rev. 55 267 / 269.3, judge rev. 56): ① deferred-leg window end = min(next start,
deferral + T_o) + 0.3 s, cut at the run end, overlapping windows of a leg merged
(:func:`deferred_leg_minimum`, ``window_rule``); ② per deferred leg, event + 0 .. 4 s judged
minimum / time below F_min / airborne time vs the same episode of the reference batch (768 /
original MLJ; ML judge: ``ref_batch`` or ``rerun_from``, :func:`judge_batch`: ``deferred_ref``),
FLAG text > 0.5 kN or > 0.1 s (:func:`attach_deferred_reference`); ③ record rows PROBE -> LEVEL
returns and re-READY vs the reference (:func:`availability_rows`, = control ``c55_avail.py``).

C-S8-68 (spec rev. 64 323, U-S8-68): ① the FAULT entry is the first of the P-S8-24 phase
``fault_reground`` (:data:`FAULT_REGROUND_PHASE`) and ``fault`` (:func:`fault_entry_s`; records
without the new phase are unchanged); :func:`classify_fault` gives ``head_sensor_reground`` when
a ``fault_reground_start`` event names target legs; the G4 rows G4-1 ... G4-8 of 323.7 for the
runs with a ``head_fault`` injection (``run_S8C`` ``mlj_c68``; :func:`g4_metrics`,
:func:`g4_rows`), and the "MLJ FAULT 0" row skips those runs.

C-S8-70 (spec rev. 65 333): ① G4-3 zero output from FAULT + d T_s (d = 1), the FAULT-sample
output recorded; ② G4-4 records (:func:`g4_4_records`: 0.5 s moving-mean minimum, last 2 s mean /
peak-to-peak); ③ G4-7 judged only on runs with the controller ``end_reason`` ``no_target``; ④ F2
of a head-fault run without the fault leg from the arm time (record row
``F2_faulty_leg_after_injection``); ⑥ the delivered head reading (``head_fault_delivered.npz``,
:func:`head_delivered_summary`); ⑦ ``WARN_FAULT_REGROUND_ABORT`` / ``INFO_D1_STEP_SUSPENDED``
counts, ``hold_count`` and ``max_filtered_attitude_change_rad`` in the G4-8 record row. Runs
without a head-fault injection give the same rows as before.

C-S8-71 (spec rev. 66 338, U-S8-72 (a)): ① G4-4 judged = 0.5 s moving-mean minimum >= F_min and
instantaneous minimum > 0 over [FAULT + 1 s, end] (:data:`G4_4_RULE`), the instantaneous minimum
vs F_min a record; ② G4-7 output check from t_f + d T_s (C-S8-70, unchanged); ③ the general rows
:data:`G4_NA_ITEMS` of a head-fault run are "not applicable" (:func:`apply_head_fault_na_rows`)
and the G4-E record row gives the end attitude change after FAULT; ④ the delivered head
reading's row alignment with ``record.npz`` (:func:`head_delivered_alignment`).

U-S8-74 (a) (spec rev. 68 354, 2026-10-27): the C-S8-72 fast-event F_min row judges per leg the
0.5 s moving-mean minimum (windows ending at >= W end + 0.5 s) >= F_min and no pad lift after the
window end (:func:`g1_fmin_after_window`, :data:`G1_FMIN_RULE`); the 1 ms instantaneous minimum
is a record row, FLAG when < F_min (:func:`g1_fmin_fast_rows`); the slow-event row is unchanged.
G4-4 (b) "instantaneous minimum > 0" becomes "no pad lift-off (airborne 0)"; old records without
``airborne`` fall back to judged force > 0 (``airborne_source`` ``force_sign_fallback``).

U-S8-75 = (b) (spec rev. 68 357.3, 2026-10-27): for a fast event on a front leg at the top auger
level with case F_s < 2 kN, the U57 "0 outside the window" part and the U-S8-74 F_min (b) "no pad
lift after the window end" pass when the adjacent-leg lift after the window sums to <= 0.1 s with
a gap <= 0.5 mm; both rows then carry the FLAG ``U-S8-75 (b) exception``
(:func:`g1_u75_scope`, :func:`g1_u75_u57_exception`, :func:`g1_u75_fmin_exception`). Outside
that scope the definitions are unchanged.

Sensitivity cases (``s8.condition`` = sensitivity, groups B / ML) report C1 / C2 (C-R19).

Units SI internally; kN / s / deg in the rows.
"""

from __future__ import annotations

import json
import math
import re
import warnings
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from outrigger_sim.verify.s7_control import centred_mean

LEGS = ("FL", "FR", "RL", "RR")
TWIST_N = np.array([0.476, -0.476, -0.523, 0.523])
"""CLAUDE.md C2: n = (0.476, -0.476, -0.523, 0.523)."""
LIFTOFF_WINDOW_S = 8.0
"""Rev. 40 210.2 / dynamics 5.25.4: lift-off transient window of the rigid NSC crawler."""
SLOW_WINDOW_S = 1.0
OSC_WINDOWS_S = ((0.0, 3.0), (3.0, 8.0))
D8_MARGIN_N = 5000.0
REANCHOR_EXTRA_N = 2000.0
P5_MARGIN_N = 7500.0
FALSE_FLAG_EXTRA_N = 2000.0
FALSE_FLAG_HOLD_S = 2.0
LIFT_THRESHOLD_N = 500.0
"""203.1 ASSUMPTION: lift-off when ``min F + m g <= 0.5 kN`` in the window."""
TAU_D_S = 0.3
"""203.3 M1' ASSUMPTION."""
NEAR_FMIN_BAND_N = (-5000.0, 10000.0)
PAIR_FLAG_N = 1840.0
F9_FLAG_N = 5000.0
C10_FLAG_S = 10.0
F5_FLAG_N = 2000.0
F7_LIMIT_S = 0.3
S7_REG_D8_KN = 0.1
S7_REG_READY_S = 0.1
"""R41-3 S7 regression flag sizes (ASSUMPTION, control rev. 41 211.6)."""
NUMERIC_TOL_N = 50.0
"""ASSUMPTION: sample-alignment / round-off allowance on F1 / F2."""
SENSOR_SHARE_N = {"ideal": 100.0, "wika": 600.0}
"""201.2 F2, 203.5 I3: sensor share of the reading error (ideal +0.1 kN, normal grade +
calibration 0.6 kN). F1 uses :func:`f1_share_N` (R43-1 / U-S8-15)."""
F1_CONST_SHARE_N = {"ideal": 100.0, "wika": 850.0}
"""U-S8-15 (spec rev. 44 214.5 question 2-a, ASSUMPTION until D-S8-5 ①): constant term of the F1
share of the calibrated WIKA reading, 0.6 -> 0.85 kN (sensor 0.6 kN + zero-calibration friction
residual; observed worst need 0.722 kN). The ideal sensor keeps 0.1 kN."""
F1_SPAN_SHARE = 0.025
"""R43-1 (spec rev. 43 213.5, ASSUMPTION): span / non-linearity share ``kappa`` of the
calibrated normal-grade reading, F1 share = 0.85 kN + kappa |F| (covers 2.7 kN at about 120 kN)."""
AIR_RESIDUAL_FLAG_N = 1700.0
"""U-S8-19 R45-3 (spec rev. 45 215.4, ASSUMPTION; rev. 44 1.3 kN): flag of the airborne
calibrated-reading residual ``|F_hat_cal - F + f|`` (true rod force < :data:`AIR_FORCE_MAX_N`, no
pad contact); Monte Carlo p99 maximum 1.68 kN, about 1 % of the runs flagged."""
F1_LAW_SIGMA_MULT = 6.0
F1_LAW_ABS_N = 100.0
"""U-S8-18 R45-1 (spec rev. 45 215.2, ASSUMPTION): F1 max row ``|r| <= 6 sigma_F + 0.1 kN``
(front 1.76 / rear 1.30 kN at sigma_p 0.20 bar; ideal sensor 0.1 kN)."""
F1_LAW_MEAN_N = 100.0
F1_LAW_STD_RATIO = (0.85, 1.15)
"""U-S8-18 R45-1 ②: per-leg statistics row of a noisy sensor (outside CHECK): ``|mean r| <=
0.1 kN`` and ``std r / sigma_F`` in [0.85, 1.15] (9.5 / 5.6 standard errors, Gaussian noise U70)."""
F1_FALLBACK_CONST_N = 1300.0
"""U-S8-18 (b): constant term of the calibrated-reading rule for records without the law terms
(``pressure_error_terms`` / ``f_seal``); rule ``F_s,leg + 1.3 kN + 0.025 |F|``."""
NEAR_STATIC_FLAG_N = 650.0
NEAR_FRICTION_FLAG_MIN_N = 100.0
NEAR_FRICTION_FLAG_FS_N = 750.0
NEAR_TOTAL_FLAG_N = 1600.0
"""U-S8-19 R45-2 (spec rev. 45 215.3, ASSUMPTION): flags of the near-F_min split: static part
0.65 kN (4-leg run p95), total 1.6 kN. Calibration friction: U-S8-25 R46-1 (spec rev. 46 216.6
(2), ASSUMPTION: observed maximum 0.68 kN + 10 %) 0.1 kN at ``F_s,leg`` = 0 and 0.75 kN at
``F_s,leg`` > 0 (``c_i`` is not proportional to F_s); rev. 45 had ``max(0.1, 0.065 F_s,leg)``."""
PRESSURE_COMPARISON_PREFIXES = ("3 F_min", "6 min after settlement", "6 final >= F_min",
                                "G4 item 6 (1)")
"""C-S8-22 ① (spec rev. 46 216.7): closed-loop F_min rows of a pressure-only case (item-9 N
group, not an operating candidate) are M5 comparison rows, not gates."""
FORCED_EVENTS = ("RE1c",)
ML_FORCED_KIND = "retract"
ML_MASK_EXTRA_S = 3.0
"""C-S8-22 ③ / ML-1 (spec rev. 46 216.3 / 216.8, U-S8-24): ``ForcedRetract`` (RE1c, ML retract
episodes) overrides every leg from its start to the run end, so the forced window is start ..
run end; the ML mask adds the window H = 3 s (ASSUMPTION, spec 205.2) after its end."""
HEAD_FAULT_EVENT = "FAULT_HEAD_PRESSURE"
PRESSURE_STEP_INFO = "INFO_PRESSURE_STEP"
"""C-S8-26 ② / ③ / ④ (spec rev. 47 217.9 #6): head-sensor fault and the D1' explained step
(U-S8-26, ``INFO_PRESSURE_STEP:<leg>:<head|rod>:<reason>``)."""
SENSOR_FAULT_INJECTION_KEYS = ("rod_sensor_fault", "rod_fault", "faulty_rod_sensor",
                               "head_sensor_fault", "head_fault", "faulty_head_sensor")
"""C-S8-26 ②: settings keys of a pressure-sensor fault injection (ASSUMPTION: none of the S8 / ML
runners injects one)."""
ML_DEEP_SETTLE_M = 0.015
ML_FAST_SETTLE_S = 0.5
ML_LIFT_FLAG_S = 0.5
"""U-S8-30 (spec rev. 47 217.10): deep fast settlement episodes (ASSUMPTION: depth >= 15 mm and
ramp <= 0.5 s; ML00_ep5 23.9 mm / 0.305 s) get a lift-time record row; a lift interval longer
than 0.5 s (U57) is flagged."""
ROD_FALLBACK_WARNING = "WARN_ROD_PRESSURE_FALLBACK"
ROD_FAULT_REASON_INFO = "INFO_ROD_PRESSURE_FAULT_REASON"
ROD_FAULT_INJECTION_KEYS = ("rod_sensor_fault", "rod_fault", "faulty_rod_sensor")
"""C-S8-22 ④: settings keys that would mark a rod-sensor fault injection (ASSUMPTION: no S8 /
ML runner injects one; ``sensors.hydraulic.FaultyRodSensor`` is a unit-test wrapper)."""
TREND_GROUPS = ("G2", "G2-R", "D8")
"""C-S8-22 ②: case groups of the S8 level trend (D8 floors incl. rpB, spec 216.2)."""
WIKA_POOLED_STD_TOL = 0.03
"""Control rev. 46 216.6 (1): WIKA residual std per side pooled over the WIKA runs within +-3 %
of sigma_F (record; 2.2 standard errors at n ~ 2,760)."""
DIAG_ITEM = "72.1 (6) no false pressure diagnosis"
WARN_ITEM = "5.24.2 unexpected warnings"
TREND_ITEMS_S6 = ("8 level trend min force (excl. REANCHOR)", "8 REANCHOR min force",
                  "8 level trend time")
CB_PAIRS = {"CB_H4V_fdown3.5_Fs0": "K0V_top_fdown3.5_Fs0",
            "CB_H4V_fdown3.5_Fs8": "K8_top_fdown3.5_Fs8",
            "CB_G4_Fs0": "E_G4_Fs0", "CB_G4_Fs8": "E_G4_Fs8",
            "CB_RE1bF_Fs0": "E_RE1bF_Fs0", "CB_RE1bF_Fs8": "E_RE1bF_Fs8"}
"""Spec rev. 46 216.5 / 216.8: pilot-check twin of each CB case (``s8cb_regress.py`` pairs; the
twins are in the p1r batch, found through ``--ref-batch`` / ``--lookup-batch``)."""
CB_REG_FORCE_KN = 0.2
CB_REG_READY_S = 0.1
"""Spec rev. 46 216.8 (ASSUMPTION): CB vs pilot-check twin D8 / event min difference <= 0.2 kN
(0.1 kN relaxed: H4V F_s 8 -0.13 kN is a friction-stick path difference), READY <= 0.1 s."""
CB_G4_FS0_FLOOR_KN = 11.99
"""Spec rev. 46 216.8: C8 of CB_G4_Fs0 >= pilot-check twin - 0.2 kN (11.99 kN), used when the
twin row is not found."""
CB_EVENT_ITEMS = ("6 min after settlement", "3 F_min (1 ms)")
CB_PREMISE_ITEM = "216.8 CB premise: controller lock_valve = counterbalance (P-S8-11, U-S8-23)"
CB_NO_FALLBACK_ITEM = "216.8 CB rod-pressure fallback warnings = 0 (no fault injection)"
CB_REG_ITEM = ("216.8 CB vs pilot-check twin: D8 / REANCHOR / event min diff <= 0.2 kN, "
               "READY diff <= 0.1 s")
CB_F2_ITEM = "216.8 CB F2 violations = 0"
CB_G4_ITEM = "216.8 CB_G4_Fs0 C8 min after settlement >= pilot-check twin - 0.2 kN"
CB_ACCEPT_ITEM = "216.8 CB rerun acceptance (all CB rows + no other failed row of the CB cases)"
CB_UNAWARE = "CB-unaware controller"
CHECK_HOLD_S = 1.0
"""Spec 215.3 / dynamics 5.27.2: CHECK extend / retract hold = 1.0 s of zero ``computed_u``."""
LOW_PROBE_MARGIN_N = 15000.0
LOW_PROBE_WINDOW_S = 2.0
"""U-S8-19 R45-4 (spec rev. 45 215.5, ASSUMPTION): low-load probe = round-start lower bound below
``F_min + 15 kN`` (``reground_load_margin_N``); watched 2 s from the second hold end."""
GUARD_MARGIN_DEFAULT_N = 5000.0
MAX_ROUNDS_DEFAULT = 3
"""``ThresholdSettings.guard_margin_N`` / ``ProbeSettings.max_rounds`` when the run config text
lacks them (``_leg_to_reground`` reconstruction only)."""
AIR_FORCE_MAX_N = 500.0
"""C-S8-19 ②: airborne sample = true rod force below 0.5 kN and pad normal force 0."""
REAPPROACH_FRACTION_DEFAULT = 1.4
"""U-S8-9 (P-S8-5): re-approach start threshold as a multiple of F_min when the run meta lacks
``rev43_controller.reapproach_load_fraction_of_F_min``."""
NEAR_FMIN_SHARE_N = {"ideal": 100.0, "wika": 850.0}
"""R43-1 record row: sensor share of the calibrated reading near F_min (-5 .. +10 kN), 0.85 kN
for the normal grade + calibration (observed 0.81 kN, ASSUMPTION until D-S8-5)."""
H4_ONE_SIDED_ABS_N = 500.0
H4_ONE_SIDED_REL = 0.03
"""R43-3: H4 one-sided row ``T_READY <= T_DONE + max(0.5 kN, 3 % T_DONE)`` (ratio <= 1.1 kept)."""
F7C_ITEM = "7c load estimate error"
SPLIT_EST_ITEM = "7c split E - T2: estimator bias [kN] (U-S8-16, record)"
SPLIT_HYST_ITEM = "7c split T2 - T0: probe round-trip hysteresis [kN] (U-S8-16, record)"
H4_ONE_SIDED_ITEM = "R H4 mechanism one-sided T_READY / mu(P_stop + m_rod g)"
RUN_ITEM = "run"
REAR_FS_SCALE = 0.8333
"""U-S8-H2 (used only when the pad record has no ``F_seal_limit``)."""
FAST_EVENTS = ("G4", "RE1bF", "RE1bP", "RE1c")
EVENT_FREE = ("HOLD", None)
ROW_SOURCE = "s8_control"


def _row(item, case, value, limit, passed, note="", kind="judged", **extra) -> dict[str, Any]:
    out = {"item": item, "case": case, "value": value, "limit": limit, "passed": passed,
           "note": note, "kind": kind, "source": ROW_SOURCE}
    out.update(extra)
    return out


# --- pure helpers (unit tested) ---------------------------------------------------------------


def clopper_pearson_upper(x: int, n: int, conf: float = 0.95) -> float | None:
    """One-sided upper Clopper-Pearson bound of a binomial rate (x of n)."""
    if n <= 0:
        return None
    if x >= n:
        return 1.0
    from scipy.stats import beta

    return float(beta.ppf(conf, x + 1, n - x))


def classify_windows(t_pad: np.ndarray, fmin_pad: np.ndarray, t_ctrl: np.ndarray,
                     f_min_N: float, rod_weight_N: Sequence[float]) -> tuple[np.ndarray,
                                                                             np.ndarray]:
    """203.1 truth class per control window ``(t_{k-1}, t_k]`` and leg: 2 = L, 1 = U, 0 = G.
    Returns (labels (k, 4) int, window minimum (k, 4) N). The first window starts one period
    before ``t_ctrl[0]``."""
    t_pad = np.asarray(t_pad, float)
    f = np.asarray(fmin_pad, float)
    tc = np.asarray(t_ctrl, float)
    period = float(np.median(np.diff(tc))) if tc.size > 1 else 0.1
    edges = np.concatenate([[tc[0] - period], tc]) if tc.size else tc
    idx = np.searchsorted(t_pad, edges, side="right")
    labels = np.zeros((tc.size, f.shape[1]), dtype=int)
    wmin = np.full((tc.size, f.shape[1]), np.nan)
    w = np.asarray(rod_weight_N, float)
    for k in range(tc.size):
        a, b = idx[k], idx[k + 1]
        if b <= a:
            continue
        m = f[a:b].min(axis=0)
        wmin[k] = m
        lift = m + w <= LIFT_THRESHOLD_N
        under = (~lift) & (m < f_min_N)
        labels[k] = np.where(lift, 2, np.where(under, 1, 0))
    return labels, wmin


def episodes(labels: np.ndarray) -> list[tuple[int, int, int]]:
    """Per leg the runs of U or L windows: (leg, k_on, k_off) inclusive."""
    out = []
    bad = np.asarray(labels) > 0
    for leg in range(bad.shape[1]):
        k = 0
        while k < bad.shape[0]:
            if bad[k, leg]:
                k0 = k
                while k + 1 < bad.shape[0] and bad[k + 1, leg]:
                    k += 1
                out.append((leg, k0, k))
            k += 1
    return out


def boundary_mask(labels: np.ndarray) -> np.ndarray:
    """203.1: one sample before and after a class change (excluded from rate metrics)."""
    lab = np.asarray(labels)
    change = np.zeros_like(lab, dtype=bool)
    if lab.shape[0] > 1:
        d = lab[1:] != lab[:-1]
        change[1:] |= d
        change[:-1] |= d
    return change


def detection_metrics(eps: Sequence[tuple[int, int, int]], level_flag: np.ndarray,
                      action_flag: np.ndarray, t_ctrl: np.ndarray, *, tau_d_s: float = TAU_D_S,
                      transient: Sequence[bool] | None = None) -> dict[str, Any]:
    """M1 / M1' / M3 of one judge over the episodes (flags (k, 4) bool)."""
    t = np.asarray(t_ctrl, float)
    rows = []
    for j, (leg, a, b) in enumerate(eps):
        lv = np.flatnonzero(level_flag[a:b + 1, leg])
        first_level = None if lv.size == 0 else float(t[a + lv[0]] - t[a])
        delay = action_delay_s(action_flag[:, leg], a, b, t)
        rows.append({"leg": LEGS[leg], "k_on": int(a), "k_off": int(b),
                     "t_on_s": float(t[a]), "duration_s": float(t[b] - t[a]) + float(
                         np.median(np.diff(t)) if t.size > 1 else 0.1),
                     "missed": first_level is None,
                     "late": first_level is not None and first_level > tau_d_s,
                     "first_level_s": first_level, "action_delay_s": delay,
                     # C-S8-13 (211.2): missed at judgement level, action level within tau_d
                     "sampling_only": first_level is None and delay is not None
                     and delay <= tau_d_s,
                     "crawler_transient": bool(transient[j]) if transient is not None else False})
    n = len(rows)
    miss = sum(r["missed"] for r in rows)
    late = sum(r["late"] for r in rows)
    delays = [r["action_delay_s"] for r in rows if r["action_delay_s"] is not None]
    return {"episodes": rows, "n": n, "M1_missed": miss,
            "M1_upper95": clopper_pearson_upper(miss, n),
            "M1p_late": late, "M3_delays_s": delays,
            "M3_median_s": float(np.median(delays)) if delays else None,
            "transient_episodes": sum(r["crawler_transient"] for r in rows)}


def action_delay_s(flags: np.ndarray, a: int, b: int, t: np.ndarray) -> float | None:
    """M3: start of the action-flag run that first covers a window of the episode ``[a, b]``
    minus ``t_on`` (negative = flagged before the episode, expected for slow settlements);
    None when no flag in ``[a, b]``."""
    f = np.asarray(flags, bool)
    inside = np.flatnonzero(f[a:b + 1])
    if inside.size == 0:
        return None
    k = a + int(inside[0])
    while k > 0 and f[k - 1]:
        k -= 1
    return float(t[k] - t[a])


def false_flags(action_flag: np.ndarray, truth_min: np.ndarray, t_ctrl: np.ndarray,
                f_min_N: float, valid: np.ndarray | None = None) -> int:
    """M2: action flags after which the true force stays >= F_min + 9.5 kN for 2 s."""
    t = np.asarray(t_ctrl, float)
    lim = f_min_N + P5_MARGIN_N + FALSE_FLAG_EXTRA_N
    n = 0
    for k, leg in zip(*np.nonzero(action_flag), strict=True):
        if valid is not None and not valid[k]:
            continue
        w = (t > t[k]) & (t <= t[k] + FALSE_FLAG_HOLD_S)
        if w.any() and np.all(truth_min[w, leg] >= lim):
            n += 1
    return n


def near_fmin_errors(est: np.ndarray, truth: np.ndarray, f_min_N: float) -> dict[str, Any]:
    """M4: estimate - truth on samples with truth in [F_min - 5, F_min + 10] kN."""
    lo, hi = f_min_N + NEAR_FMIN_BAND_N[0], f_min_N + NEAR_FMIN_BAND_N[1]
    sel = np.isfinite(est) & np.isfinite(truth) & (truth >= lo) & (truth <= hi)
    if not sel.any():
        return {"n": 0, "max_kN": None, "p5_kN": None, "p50_kN": None, "p95_kN": None}
    e = (est[sel] - truth[sel]) / 1e3
    return {"n": int(sel.sum()), "max_kN": float(e.max()),
            "p5_kN": float(np.percentile(e, 5)), "p50_kN": float(np.percentile(e, 50)),
            "p95_kN": float(np.percentile(e, 95))}


def c1_metrics(t_rel: np.ndarray, fmin_pad: np.ndarray, liftoff_s: float | None,
               mask: np.ndarray | None = None) -> dict[str, Any]:
    """R40-1: raw minimum after lift-off (``mask`` = allowed samples), its time / leg, the slow
    (1 s centred mean) minimum over the same samples, and both over the first 8 s."""
    if liftoff_s is None:
        return {}
    t = np.asarray(t_rel, float)
    f = np.asarray(fmin_pad, float)
    after = t >= liftoff_s
    if mask is not None:
        after &= np.asarray(mask, bool)
    if not after.any():
        return {}
    dt = float(np.median(np.diff(t))) if t.size > 1 else SLOW_WINDOW_S
    slow = centred_mean(f, int(round(SLOW_WINDOW_S / dt)) | 1)
    fa, sa = f[after], slow[after]
    k = np.unravel_index(int(np.argmin(fa)), fa.shape)
    ks = np.unravel_index(int(np.argmin(sa)), sa.shape)
    ta = t[after]
    early = ta <= liftoff_s + LIFTOFF_WINDOW_S
    out = {"raw_min_kN": float(fa[k]) / 1e3, "raw_leg": LEGS[k[1]], "raw_t_s": float(ta[k[0]]),
           "raw_after_liftoff_s": float(ta[k[0]] - liftoff_s),
           "slow_min_kN": float(sa[ks]) / 1e3, "slow_leg": LEGS[ks[1]],
           "slow_t_s": float(ta[ks[0]]), "slow_window_s": SLOW_WINDOW_S}
    if early.any():
        out["slow_min_first8_kN"] = float(sa[early].min()) / 1e3
        out["raw_min_first8_kN"] = float(fa[early].min()) / 1e3
    return out


def c1_row(cid: str, c1: Mapping[str, Any], limit_kN: float, *, rigid: bool,
           condition: str = "judged") -> dict[str, Any]:
    """R40-1 / R40-2 row (``kind`` "hold" when the three hold conditions meet, rigid crawler)."""
    item = "C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN"
    if not c1:
        return _row(item, cid, None, limit_kN, None, "no crawler lift-off / no pad record",
                    kind="record")
    v = c1["raw_min_kN"]
    passed: bool | None = bool(v >= limit_kN)
    kind, note = "judged", ""
    cols = {k: c1.get(k) for k in ("raw_leg", "raw_t_s", "raw_after_liftoff_s", "slow_min_kN",
                                   "slow_leg", "slow_t_s", "slow_min_first8_kN")}
    if not passed and rigid and c1["raw_after_liftoff_s"] <= LIFTOFF_WINDOW_S \
            and c1.get("slow_min_first8_kN") is not None \
            and c1["slow_min_first8_kN"] >= limit_kN:
        passed, kind = None, "hold"
        note = ("hold (rigid crawler upper bound, R40-2): raw below the limit within "
                f"{LIFTOFF_WINDOW_S:g} s of lift-off, slow component >= limit; resolve before "
                "priority 2 with the L1 twin (F_s 0) or a compliant-crawler rerun")
    if condition == "sensitivity" and passed is not None:
        cols["passed_raw"] = passed
        passed, kind = None, "report"
        note = "sensitivity condition: reported (C-R19)"
    return _row(item, cid, v, limit_kN, passed, note, kind=kind, **cols)


# --- I4 (rev. 41 211.2, C-S8-10) -----------------------------------------------------------------

I4_EXPECTED_PATH = Path("06_analysis") / "02_control" / "s8" / "s8_i4_expected.json"
I4_LIFT_MIN_S = 0.3
"""211.2 ``if_lift``: a lift episode (203.1 L) of at least this long after ``t_ev``
(ASSUMPTION of control rev. 41: P-R8-13 two samples + one)."""
I4_KEYS = ("p_miss", "item6", "reapproach")
I4_EVENT_AT_READY5 = ("G4", "SS", "SS9", "RE1bF", "RE1bP", "RE1c")


def i4_event_start(event: str | None, event_t_s: float | None,
                   times: Mapping[str, Any]) -> float | None:
    """211.2 ``t_ev`` (relative to the run start): the scheduled event time (G4 / SS / SS9 /
    RE1bF / RE1c = READY + 5 s, RE1bP = probe start + 0.1 s), READY entry for HOLD, crawler
    lift-off + 8 s for the D8 cases (no event)."""
    if event in I4_EVENT_AT_READY5:
        return None if event_t_s is None else float(event_t_s)
    if event == "HOLD":
        return None if times.get("ready") is None else float(times["ready"])
    if event is None:
        lo = times.get("liftoff")
        return None if lo is None else float(lo) + LIFTOFF_WINDOW_S
    return None


def _lift_runs_s(labels: np.ndarray, tc: np.ndarray, t_ev: float) -> float:
    """Longest run of L windows (label 2) of any leg that starts at or after ``t_ev`` [s]."""
    period = _period(tc)
    best = 0.0
    lift = np.asarray(labels) == 2
    for leg in range(lift.shape[1]):
        k = 0
        while k < lift.shape[0]:
            if lift[k, leg]:
                k0 = k
                while k + 1 < lift.shape[0] and lift[k + 1, leg]:
                    k += 1
                if tc[k0] >= t_ev - 1e-9:
                    best = max(best, (k - k0 + 1) * period)
            k += 1
    return best


def i4_classify(*, t_ev: float, t_end: float, tc: np.ndarray, labels: np.ndarray,
                episode_list: Sequence[tuple[int, int, int]], transient: Sequence[bool],
                level_flag: np.ndarray, t_pad: np.ndarray, f_judged: np.ndarray, f_min: float,
                reapproach_times: Sequence[float]) -> dict[str, Any]:
    """211.2 observed classes of one run (times relative to the run start).

    * ``p_miss``: offline J_P judgement-level flags (``level_flag`` (k, 4)) over the 203.1
      episodes with ``t_on >= t_ev``: ``miss`` (an episode never flagged), ``detect`` (all
      flagged), ``none`` (no episode). ``crawler_transient`` episodes are **counted** (R40-5,
      C-S8-16 ④, spec rev. 43 213.2 #7) and listed apart (``transient_episodes_after_t_ev``);
    * ``item6``: minimum of the judged 1 ms rod force (S8-A2) of the four legs over
      ``[t_ev, t_end]`` >= ``F_min`` -> ``pass`` else ``fail``;
    * ``reapproach``: a ``leg_reapproach_start`` at ``t >= t_ev`` -> ``yes`` / ``no``;
    * ``lift_long_s``: longest lift run starting at ``t >= t_ev`` (``if_lift`` rule)."""
    tc = np.asarray(tc, float)
    sel = [j for j, (_leg, a, _b) in enumerate(episode_list) if tc[a] >= t_ev - 1e-9]
    flagged = [bool(np.any(np.asarray(level_flag)[episode_list[j][1]:episode_list[j][2] + 1,
                                                  episode_list[j][0]])) for j in sel]
    p_miss = "none" if not sel else ("miss" if not all(flagged) else "detect")
    n_trans = int(sum(bool(transient[j]) for j in sel))
    p_miss_ex = [f for j, f in zip(sel, flagged, strict=True) if not bool(transient[j])]
    p_miss_ex_transient = ("none" if not p_miss_ex
                           else ("miss" if not all(p_miss_ex) else "detect"))
    tp = np.asarray(t_pad, float)
    w = (tp >= t_ev - 1e-9) & (tp <= t_end + 1e-9)
    fmin_w = float(np.min(np.asarray(f_judged, float)[w])) if w.any() else None
    item6 = None if fmin_w is None else ("pass" if fmin_w >= f_min else "fail")
    reap = [float(t) for t in reapproach_times if float(t) >= t_ev - 1e-9]
    return {"t_ev_s": float(t_ev), "p_miss": p_miss, "item6": item6,
            "reapproach": "yes" if reap else "no",
            "episodes_after_t_ev": len(sel), "episodes_flagged": int(sum(flagged)),
            "transient_episodes_after_t_ev": n_trans,
            "p_miss_ex_transient": p_miss_ex_transient,
            "min_judged_force_kN": None if fmin_w is None else fmin_w / 1e3,
            "first_reapproach_s": reap[0] if reap else None,
            "lift_long_s": _lift_runs_s(labels, tc, t_ev)}


def i4_compare(expected: Mapping[str, str], observed: Mapping[str, Any]) -> dict[str, Any]:
    """Cells of one case: ``n/a`` not compared; ``if_lift`` compared with ``yes`` only when a
    lift of at least :data:`I4_LIFT_MIN_S` follows ``t_ev``. Returns cells, mismatches and the
    case verdict (``passed`` None when nothing is compared)."""
    cells, mismatch = {}, []
    for key in I4_KEYS:
        exp = expected.get(key, "n/a")
        obs = observed.get(key)
        if exp == "n/a":
            cells[key] = {"expected": exp, "observed": obs, "compared": False}
            continue
        if exp == "if_lift":
            if (observed.get("lift_long_s") or 0.0) < I4_LIFT_MIN_S - 1e-9:
                cells[key] = {"expected": exp, "observed": obs, "compared": False,
                              "note": f"no lift >= {I4_LIFT_MIN_S:g} s after t_ev"}
                continue
            exp = "yes"
        ok = obs == exp
        cells[key] = {"expected": exp, "observed": obs, "compared": True, "match": ok}
        if not ok:
            mismatch.append(key)
    compared = [k for k, c in cells.items() if c["compared"]]
    return {"cells": cells, "mismatches": mismatch,
            "passed": None if not compared else not mismatch}


def load_i4_expected(root: Path) -> dict[str, Any] | None:
    p = Path(root) / I4_EXPECTED_PATH
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def i4_rows(sms: Mapping[str, Mapping[str, Any]], expected: Mapping[str, Any] | None
            ) -> list[dict[str, Any]]:
    """Per-case I4 rows (gate) for the cases of the expected table that are in the batch, and
    the batch summary row (replaces the rev. 39 placeholder)."""
    item = "I4 classification vs control rev. 41 expected table (211.2)"
    if expected is None:
        return [_row(item, "*", None, None, None, f"{I4_EXPECTED_PATH} missing", kind="record")]
    rows, n_ok, n_bad, n_none, missing = [], 0, 0, 0, []
    for cid, spec in (expected.get("cases") or {}).items():
        sm = sms.get(cid)
        if sm is None:
            continue
        obs = sm.get("i4")
        if obs is None:
            rows.append(_row(item, cid, None, spec.get("expected"), False,
                             "no observed classes (event time / lift-off missing)"))
            n_bad += 1
            missing.append(cid)
            continue
        cmp_ = i4_compare(spec.get("expected") or {}, obs)
        p = cmp_["passed"]
        n_ok += p is True
        n_bad += p is False
        n_none += p is None
        rows.append(_row(item, cid, {k: obs.get(k) for k in I4_KEYS}, spec.get("expected"), p,
                         ("mismatch " + ", ".join(cmp_["mismatches"])) if cmp_["mismatches"]
                         else ("nothing compared" if p is None else "all compared cells match"),
                         kind="judged" if p is not None else "record",
                         cells=cmp_["cells"], observed=obs,
                         reduced_ref=spec.get("reduced_ref"), basis=spec.get("basis")))
    rows.append(_row("I4 summary (gate: every compared case matches)", "*",
                     {"match": n_ok, "mismatch": n_bad, "not_compared": n_none},
                     0, (n_bad == 0) if (n_ok + n_bad) else None,
                     f"{len(rows)} of {len(expected.get('cases') or {})} table cases in the batch"
                     + (f"; no observation: {missing}" if missing else ""),
                     kind="judged" if (n_ok + n_bad) else "record"))
    return rows


G4_SUMMARY_LEG = 3  # RR (the settling patch)


def g4_rr_summary(*, t_ev: float, events: Sequence[tuple[float, str]], tc: np.ndarray,
                  issued_u: np.ndarray, band: np.ndarray | None, t_pad: np.ndarray,
                  f_judged: np.ndarray, controller_meta: Mapping[str, Any] | None,
                  leg: int = G4_SUMMARY_LEG) -> dict[str, Any]:
    """C-S8-14 (control rev. 42 212): RR summary of a G4 run after ``t_ev`` (times relative to
    the run start): first ``relevel_predicted`` and ``leg_reapproach_start`` at or after
    ``t_ev``, the mean RR command between them (or from the first of them to the next 1 s when
    the other is absent), the minimum judged rod force of RR after ``t_ev`` and its time, the
    measured ``F_band`` (per-leg band of RR, else the common band) at the first of the two
    events (or ``t_ev``), and the twist stiffness scale (controller meta at the run end)."""
    def first(prefix: str) -> float | None:
        ts = [t for t, n in events if n.split(":")[0] == prefix and t >= t_ev - 1e-9]
        return min(ts) if ts else None

    t_rel, t_rea = first("relevel_predicted"), first("leg_reapproach_start")
    tc = np.asarray(tc, float)
    u = np.asarray(issued_u, float)
    starts = [t for t in (t_rel, t_rea) if t is not None]
    t_a = min(starts) if starts else None
    t_b = (max(starts) if len(starts) == 2 else (None if t_a is None else t_a + 1.0))
    u_mean = None
    if t_a is not None:
        sel = (tc >= t_a - 1e-9) & (tc <= t_b + 1e-9)
        u_mean = float(u[sel, leg].mean()) if sel.any() else None
    tp = np.asarray(t_pad, float)
    w = tp >= t_ev - 1e-9
    f = np.asarray(f_judged, float)[:, leg]
    k = int(np.argmin(np.where(w, f, np.inf))) if w.any() else None
    f_band = None
    if band is not None:
        b = np.asarray(band, float)
        kk = int(np.clip(np.searchsorted(tc, (t_a if t_a is not None else t_ev) - 1e-9), 0,
                         tc.size - 1))
        v = b[kk, leg] if b.ndim == 2 else b[kk]
        f_band = None if not np.isfinite(v) else float(v) / 1e3
    tw = _find_key(controller_meta or {}, "measured_scale")
    tw_used = _find_key(controller_meta or {}, "scale_in_use")
    return {"leg": LEGS[leg], "t_ev_s": float(t_ev), "relevel_predicted_s": t_rel,
            "reapproach_start_s": t_rea,
            "u_rr_mean_mm_s": None if u_mean is None else u_mean * 1e3,
            "u_window_s": None if t_a is None else [t_a, t_b],
            "min_true_kN": None if k is None else float(f[k]) / 1e3,
            "min_true_t_s": None if k is None else float(tp[k]),
            "F_band_kN": f_band, "twist_stiffness_scale": tw,
            "twist_stiffness_scale_in_use": tw_used,
            "note": "twist stiffness scale = controller meta at the run end"}


TWIST_HISTORY_KEY = "twist_stiffness_history"
"""``result.json`` key of the runner's per-probe-round twist stiffness scale history
(``run_S8C.TwistScaleHistory``, C-S8-19 ⑤)."""
MIN_STIFFNESS_SCALE_LEGS_DEFAULT = 3
"""``control.c2.MIN_STIFFNESS_SCALE_LEGS`` (used by the offline reconstruction only)."""


def _config_float(config_text: str, key: str, default: float | None) -> float | None:
    import re

    m = re.search(rf"{key}=([-+0-9.eE]+|None)", config_text or "")
    if m is None:
        return default
    return None if m.group(1) == "None" else float(m.group(1))


def reconstruct_twist_history(probes: Sequence[Sequence[Mapping[str, Any]]],
                              twist_meta: Mapping[str, Any] | None, config_text: str,
                              t0: float) -> list[dict[str, Any]]:
    """C-S8-19 ⑤ fallback for runs without the runner history: the scale of every probe round
    as ``C2Controller._update_twist_stiffness_scale`` sets it (median of measured / nominal
    ``S_ii`` over the legs grounded by stiffness, not skipped, finite; fewer than 3 legs keep the
    previous scale; bounded to ``[measured_stiffness_scale_min, ..._max]``). Round time = the
    latest second hold end of the round (the controller finishes the round at the next reading,
    within one period). Times relative to the run start ``t0`` (record time - ``t0``)."""
    nominal = (twist_meta or {}).get("denominator_N_m")
    if not nominal:
        return []
    lo = _config_float(config_text, "measured_stiffness_scale_min", 1.0)
    hi = _config_float(config_text, "measured_stiffness_scale_max", 1.5)
    scale = _config_float(config_text, "pre_probe_stiffness_scale", 1.2)
    out = []
    for i, rnd in enumerate(probes):
        rows = [r for r in rnd if isinstance(r, Mapping)]
        ratios = [float(r["incremental_stiffness_N_m"]) / float(nominal[int(r["leg_index"])])
                  for r in rows if r.get("is_grounded_by_stiffness") and not r.get("is_skipped")
                  and r.get("incremental_stiffness_N_m") is not None
                  and math.isfinite(float(r["incremental_stiffness_N_m"]))]
        raw = float(np.median(ratios)) if len(ratios) >= MIN_STIFFNESS_SCALE_LEGS_DEFAULT \
            else None
        if raw is not None:
            scale = raw if lo is None else max(lo, raw)
            scale = scale if hi is None else min(hi, scale)
        ends = [float(r["t_second_hold_end_s"]) for r in rows
                if isinstance(r.get("t_second_hold_end_s"), int | float)]
        out.append({"round": i, "t_s": None if not ends else max(ends) - t0,
                    "raw_ratio": raw, "scale_in_use": scale, "grounded_leg_count": len(ratios),
                    "source": "reconstructed from probe_history.json"})
    return out


def twist_history(case: Mapping[str, Any], t0: float) -> tuple[list[dict[str, Any]], str]:
    """Runner history (``result.json`` :data:`TWIST_HISTORY_KEY`, times relative to the run
    start) when recorded, else :func:`reconstruct_twist_history`."""
    res = case["result"]
    hist = res.get(TWIST_HISTORY_KEY)
    if hist:
        return list(hist), "runner"
    cm = res.get("controller_meta") or {}
    rec = reconstruct_twist_history(case.get("probes") or [], cm.get("twist_gain_stiffness"),
                                    str(res["settings"].get("controller_config") or ""), t0)
    return rec, "reconstructed (probe_history.json, run without the runner history)"


def scale_at(history: Sequence[Mapping[str, Any]], t_s: float, pre_probe: float | None
             ) -> dict[str, Any]:
    """Scale in use at ``t_s``: the last history entry at or before ``t_s`` (else the pre-probe
    scale)."""
    before = [h for h in history if h.get("t_s") is not None and h["t_s"] <= t_s + 1e-9]
    if not before:
        return {"scale_in_use": pre_probe, "raw_ratio": None, "round": None,
                "note": "no probe round before t (pre-probe scale)"}
    h = before[-1]
    return {"scale_in_use": h.get("scale_in_use"), "raw_ratio": h.get("raw_ratio"),
            "round": h.get("round"), "t_round_s": h.get("t_s")}


def sampling_only_episodes(sm: Mapping[str, Any], name: str = "J_C") -> list[dict[str, Any]]:
    """211.2 observation / C-S8-13: episodes the judge missed at judgement level while its
    action-level flag starts within ``t_on + tau_d`` (``action_delay_s <= TAU_D_S``)."""
    i9 = sm.get("item9") or {}
    rep = (i9.get("replay") or {}).get(name)
    out = []
    if rep is not None:
        for e in rep.get("episodes", []):
            if e.get("first_decision_s") is None and e.get("action_delay_s") is not None \
                    and e["action_delay_s"] <= TAU_D_S:
                out.append({"case": sm["case"], "leg": e["leg"], "t_on_s": e["t_on_s"],
                            "action_delay_s": e["action_delay_s"], "source": "P-S8-1 replay"})
        return out
    d = i9.get(name) or {}
    for e in d.get("episodes", []):
        if e.get("sampling_only"):
            out.append({"case": sm["case"], "leg": e["leg"], "t_on_s": e["t_on_s"],
                        "action_delay_s": e["action_delay_s"], "source": "fallback"})
    return out


# --- case loading -----------------------------------------------------------------------------


def _s8(case) -> dict[str, Any]:
    return case["result"]["settings"].get("s8") or {}


def is_rigid_crawler(s8: Mapping[str, Any]) -> bool:
    """R40-6: absent meta = rigid (conservative)."""
    return str(s8.get("crawler_contact") or "nsc_rigid") == "nsc_rigid"


def lift_transient_rules_apply(s8: Mapping[str, Any]) -> bool:
    """R40-2 hold / R40-5 ``crawler_transient`` / R40-4 ML exclusion apply: rigid crawler, or a
    compliant crawler whose S8-L4 check has not passed (``crawler_check_passed`` not True;
    S8-L5 'rigid crawler upper bound' label, ASSUMPTION of this module)."""
    return is_rigid_crawler(s8) or s8.get("crawler_check_passed") is not True


RIGID_LABEL = "rigid crawler upper bound (S8-L5)"


def crawler_label(sm: Mapping[str, Any]) -> str:
    """S8-L5 tag of a case: the rigid-crawler label while the R40 lift-off rules apply (rigid NSC
    crawler, or a compliant one whose S8-L4 check has not passed), else the contact name."""
    s8 = sm.get("s8") or {}
    contact = str(sm.get("crawler_contact") or s8.get("crawler_contact") or "nsc_rigid")
    if lift_transient_rules_apply({**s8, "crawler_contact": contact}):
        return f"{contact}: {RIGID_LABEL}"
    return contact


def load_series(case_dir: Path) -> dict[str, np.ndarray] | None:
    p = Path(case_dir) / "s8_series.npz"
    if not p.exists():
        return None
    with np.load(p, allow_pickle=False) as d:
        return {k: d[k] for k in d.files}


def _rod_weight_N(params) -> np.ndarray:
    g = float(params.meta.gravity_m_s2)
    return np.array([leg.moving_part.mass_kg * g for leg in params.legs])


def _fs_leg_N(case, pads) -> np.ndarray:
    if pads is not None and "F_seal_limit" in pads and np.any(pads["F_seal_limit"] > 0):
        return np.nanmax(pads["F_seal_limit"], axis=0)
    fs = float(_s8(case).get("fs_kN") or 0.0) * 1e3
    return np.array([fs, fs, REAR_FS_SCALE * fs, REAR_FS_SCALE * fs])


def _is_wika(case) -> bool:
    return bool((case["result"]["settings"].get("bundle_c") or {}).get("sensor_model"))


def _sensor_share_N(case) -> float:
    return SENSOR_SHARE_N["wika" if _is_wika(case) else "ideal"]


def f1_share_N(force_N: np.ndarray, *, wika: bool) -> np.ndarray:
    """R43-1 / U-S8-15: sensor share of the calibrated reading error at the true force
    ``force_N``: ideal 0.1 kN, normal grade + calibration 0.85 kN + :data:`F1_SPAN_SHARE`
    ``|F|``."""
    f = np.abs(np.asarray(force_N, float))
    if not wika:
        return np.full(f.shape, F1_CONST_SHARE_N["ideal"])
    return F1_CONST_SHARE_N["wika"] + F1_SPAN_SHARE * f


def air_mask(true_force_N: np.ndarray, pad_normal_N: np.ndarray, use: np.ndarray) -> np.ndarray:
    """C-S8-19 ②: airborne samples (true rod force < :data:`AIR_FORCE_MAX_N`, pad normal <= 0) of
    the periods ``use``; (k, 4) bool."""
    return (np.asarray(use, bool)[:, None] & (np.asarray(true_force_N, float) < AIR_FORCE_MAX_N)
            & ~(np.asarray(pad_normal_N, float) > 0.0))


def air_residual(sensor_part_N: np.ndarray, true_force_N: np.ndarray, pad_normal_N: np.ndarray,
                 use: np.ndarray, phases: Sequence[str],
                 split: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """C-S8-19 ② / R45-3 (spec rev. 45 215.4): the calibrated-reading residual
    ``|F_hat_cal - F + f|`` (``sensor_part_N``, (k, 4)) on airborne samples (:func:`air_mask`) of
    the periods ``use`` (phases other than CHECK); maximum, its leg / phase, per leg maxima and
    the :data:`AIR_RESIDUAL_FLAG_N` flag; ``split`` (:func:`error_split` over the same samples)
    is attached as the three parts (static / calibration friction / noise)."""
    s = np.asarray(sensor_part_N, float)
    air = air_mask(true_force_N, pad_normal_N, use) & np.isfinite(s)
    out: dict[str, Any] = {"n": int(air.sum()), "limit_kN": AIR_RESIDUAL_FLAG_N / 1e3,
                           "max_abs_kN": None, "leg": None, "phase": None,
                           "per_leg_max_abs_kN": [None] * s.shape[1], "flag": None,
                           "split": None if split is None else dict(split)}
    if not air.any():
        return out
    a = np.where(air, np.abs(s), -np.inf)
    k, j = np.unravel_index(int(np.argmax(a)), a.shape)
    out.update(max_abs_kN=float(a[k, j]) / 1e3, leg=LEGS[j], phase=str(phases[k]),
               per_leg_max_abs_kN=[float(a[air[:, i], i].max()) / 1e3 if air[:, i].any()
                                   else None for i in range(s.shape[1])])
    out["flag"] = bool(out["max_abs_kN"] > AIR_RESIDUAL_FLAG_N / 1e3)
    return out


# --- rev. 45 (C-S8-21, U-S8-18 / 19) ------------------------------------------------------------

AREA_SOURCE_YAML = "params.raw legs.<leg>.cylinder.{head,annulus}_area_m2"


def cylinder_areas_m2(params, pads: Mapping[str, Any] | None = None
                      ) -> tuple[np.ndarray, np.ndarray, str]:
    """(head areas ``A_p``, annulus areas ``A_ann``, source) per leg [m^2]: the YAML per-leg
    cylinder keys (REXOME35), else a least-squares fit of the pad record
    ``F_pressure = p_h A_p - p_r A_ann``."""
    try:
        legs = params.raw["legs"]
        a_p = np.array([float(legs[n]["cylinder"]["head_area_m2"]) for n in LEGS])
        a_a = np.array([float(legs[n]["cylinder"]["annulus_area_m2"]) for n in LEGS])
        return a_p, a_a, AREA_SOURCE_YAML
    except (AttributeError, KeyError, TypeError):
        pass
    if pads is None or "F_pressure" not in pads:
        raise KeyError("no cylinder areas (YAML keys absent, no F_pressure in the pad record)")
    a_p, a_a = np.zeros(4), np.zeros(4)
    for j in range(4):
        x = np.c_[np.asarray(pads["head_pressure"], float)[:, j],
                  -np.asarray(pads["rod_pressure"], float)[:, j]]
        a_p[j], a_a[j] = np.linalg.lstsq(x, np.asarray(pads["F_pressure"], float)[:, j],
                                         rcond=None)[0]
    return a_p, a_a, "least-squares fit of pads F_pressure = p_h A_p - p_r A_ann"


TERM_KEYS = ("offset_Pa", "gain", "nonlinearity_Pa", "temperature_offset_Pa", "temperature_gain")


def sensor_static_error_N(terms_meta: Mapping[str, Any] | None, grade: str | None,
                          p_head_Pa: np.ndarray, p_rod_Pa: np.ndarray, a_head_m2: np.ndarray,
                          a_ann_m2: np.ndarray, legs_cfg: Mapping[str, Any] | None = None,
                          t_s: np.ndarray | None = None) -> np.ndarray:
    """R45-1: static error of the net force reading ``E_s = e_h(p_h) A_p - e_r(p_r) A_ann``
    [N], (k, 4), from the run's drawn terms (``terms_to_meta`` layout ``"<side>:<leg>"``) with
    the grade's +-4 bar non-temperature clip (``PressureErrorTerms.error_Pa``), plus the extra
    configured offsets / head zero drift of ``LegSensorModel._with_static_error`` (zero in the S8
    runs). ``terms_meta`` None (ideal or legacy sensor): only the extra offsets. The 4-20 mA
    saturation and the 0.025 bar quantisation are not modelled (noise side)."""
    from outrigger_sim.sensors.pressure_error import (
        PRESSURE_ERROR_BOUNDS,
        PressureErrorGrade,
        PressureErrorTerms,
    )

    ph = np.asarray(p_head_Pa, float)
    pr = np.asarray(p_rod_Pa, float)
    a_p = np.asarray(a_head_m2, float)
    a_a = np.asarray(a_ann_m2, float)
    es = np.zeros(np.broadcast_shapes(ph.shape, pr.shape))
    if terms_meta:
        clip = PRESSURE_ERROR_BOUNDS[PressureErrorGrade(grade or "normal")].nontemperature_clip_Pa
        for side, p, a, sign in (("head", ph, a_p, 1.0), ("rod", pr, a_a, -1.0)):
            arr = {k: np.array([float(terms_meta[f"{side}:{leg}"][k]) for leg in LEGS])
                   for k in TERM_KEYS}
            terms = PressureErrorTerms(arr["offset_Pa"], arr["gain"], arr["nonlinearity_Pa"],
                                       arr["temperature_offset_Pa"], arr["temperature_gain"],
                                       clip)
            es = es + sign * terms.error_Pa(p) * a
    cfg = legs_cfg or {}
    head_extra = np.asarray(cfg.get("head_offset_Pa") or [0.0] * 4, float)
    rod_extra = np.asarray(cfg.get("rod_offset_Pa") or [0.0] * 4, float)
    drift = np.asarray(cfg.get("head_zero_drift_Pa_per_s") or [0.0] * 4, float)
    extra = np.broadcast_to(head_extra * a_p - rod_extra * a_a, es.shape).copy()
    if t_s is not None and np.any(drift != 0.0):
        dt = np.maximum(0.0, np.asarray(t_s, float) - float(cfg.get("zero_drift_start_s") or 0.0))
        extra = extra + dt[:, None] * drift[None, :] * a_p[None, :]
    return es + extra


def f1_law_limit_N(sigma_F_N: np.ndarray) -> np.ndarray:
    """R45-1 ①: per-leg max-row limit ``6 sigma_F + 0.1 kN`` [N]."""
    return F1_LAW_SIGMA_MULT * np.asarray(sigma_F_N, float) + F1_LAW_ABS_N


def f1_law_metrics(r_N: np.ndarray, sigma_F_N: np.ndarray, use: np.ndarray) -> dict[str, Any]:
    """R45-1 (spec rev. 45 215.2): reading-law residual ``r`` (k, 4) on the samples ``use`` ((k,)
    or (k, 4), finite only). ① per leg ``max |r|`` against :func:`f1_law_limit_N`; ② for legs
    with ``sigma_F > 0`` the mean (``<= 0.1 kN``) and the sample standard deviation ratio
    ``std / sigma_F`` in :data:`F1_LAW_STD_RATIO`. ``stats_passed`` None when no leg has noise
    (ideal sensor: ② left out)."""
    r = np.asarray(r_N, float)
    sig = np.asarray(sigma_F_N, float)
    sel = np.asarray(use, bool)
    if sel.ndim == 1:
        sel = np.repeat(sel[:, None], r.shape[1], axis=1)
    sel = sel & np.isfinite(r)
    lim = f1_law_limit_N(sig)
    out: dict[str, Any] = {"limit_N": lim.tolist(), "sigma_F_N": sig.tolist(),
                           "n": sel.sum(axis=0).tolist(), "max_abs_N": [], "t_index": [],
                           "violations_per_leg": [], "mean_N": [], "std_N": [],
                           "std_ratio": [], "stats_ok": []}
    for j in range(r.shape[1]):
        x = r[sel[:, j], j]
        if x.size == 0:
            for key in ("max_abs_N", "t_index", "mean_N", "std_N", "std_ratio", "stats_ok"):
                out[key].append(None)
            out["violations_per_leg"].append(0)
            continue
        k = int(np.flatnonzero(sel[:, j])[int(np.argmax(np.abs(x)))])
        out["max_abs_N"].append(float(np.abs(x).max()))
        out["t_index"].append(k)
        out["violations_per_leg"].append(int(np.sum(np.abs(x) > lim[j])))
        mean = float(x.mean())
        std = float(x.std(ddof=1)) if x.size > 1 else None
        out["mean_N"].append(mean)
        out["std_N"].append(std)
        if sig[j] > 0.0 and std is not None:
            ratio = std / sig[j]
            out["std_ratio"].append(ratio)
            out["stats_ok"].append(bool(abs(mean) <= F1_LAW_MEAN_N
                                        and F1_LAW_STD_RATIO[0] <= ratio <= F1_LAW_STD_RATIO[1]))
        else:
            out["std_ratio"].append(None)
            out["stats_ok"].append(None)
    out["violations"] = int(sum(out["violations_per_leg"]))
    exc = [m - lim[j] for j, m in enumerate(out["max_abs_N"]) if m is not None]
    out["max_excess_N"] = max(exc) if exc else None
    judged = [ok for ok in out["stats_ok"] if ok is not None]
    out["stats_passed"] = None if not judged else bool(all(judged))
    return out


def check_hold_rows(phases: Sequence[str], computed_u: np.ndarray, t_s: np.ndarray,
                    hold_s: float = CHECK_HOLD_S) -> list[list[np.ndarray]]:
    """Spec 215.3 / dynamics 5.27.2: per leg the 10 Hz rows of the two CHECK calibration holds,
    by the ``control.zero_calibration.ZeroCalibration`` rule: a hold stage starts at the period
    where the last moving leg reaches (its first zero ``computed_u`` after a move inside CHECK,
    common to the moving legs) and takes the readings of the following periods up to
    ``hold_s`` (``(t_start, t_start + hold_s]``, 10 samples at 10 Hz). Legs without a move
    (skipped / reused) get no hold."""
    ph = np.asarray(phases).astype(str)
    u = np.asarray(computed_u, float)
    t = np.asarray(t_s, float)
    k_chk = np.flatnonzero(ph == "check")
    starts: list[list[int]] = []
    for leg in range(u.shape[1]):
        seg: list[list[float]] = []
        for k in k_chk:
            s = float(np.sign(round(u[k, leg] * 1e6)))
            if not seg or seg[-1][0] != s:
                seg.append([s, int(k)])
        starts.append([int(k) for s, k in seg[1:] if s == 0.0][:2])
    moving = [x for x in starts if len(x) == 2]
    if not moving:
        return [[] for _ in range(u.shape[1])]
    common = [max(x[i] for x in moving) for i in range(2)]
    holds = [np.array([k for k in k_chk if t[k0] + 1e-9 < t[k] <= t[k0] + hold_s + 1e-9],
                      dtype=int) for k0 in common]
    return [holds if len(x) == 2 else [] for x in starts]


def calibration_split(f_hat_N: np.ndarray, law_force_N: np.ndarray, e_s_N: np.ndarray,
                      rod_weight_N: Sequence[float], c_i_N: Sequence[float | None],
                      holds: Sequence[Sequence[np.ndarray]]) -> list[dict[str, Any] | None]:
    """Spec 215.3 / dynamics 5.27.2: per leg the zero-calibration offset ``c_i`` split into the
    sensor part ``c_sens`` (mean ``E_s`` over the two CHECK holds), the noise part ``c_noise``
    (mean ``r = F_hat - (F - f) - E_s`` over the holds) and the friction part ``c_fric = c_i -
    c_sens - c_noise`` (+ = the calibrated reading reads low, safe side).
    ``law_force_N`` = ``F - f``. ``c_rebuilt = (F_hat_e + F_hat_r) / 2 + m_rod g`` is the
    controller formula on the record (reconstruction check: with the :func:`check_hold_rows`
    windows it reproduces the controller ``c_i`` to the rod-weight rounding, < 1 N); ``c_fric_law``
    = ``((F - f)_e + (F - f)_r) / 2 + m_rod g`` (the ideal-sensor offset). None for a leg
    without two holds or without ``c_i``."""
    f_hat = np.asarray(f_hat_N, float)
    law = np.asarray(law_force_N, float)
    es = np.asarray(e_s_N, float)
    r = f_hat - law - es
    w = np.asarray(rod_weight_N, float)
    out: list[dict[str, Any] | None] = []
    for j in range(f_hat.shape[1]):
        h = holds[j] if j < len(holds) else []
        c_i = None if c_i_N is None or c_i_N[j] is None else float(c_i_N[j])
        if len(h) < 2 or min(len(h[0]), len(h[1])) == 0 or c_i is None:
            out.append(None)
            continue
        he, hr = h[0], h[1]

        def mean2(x: np.ndarray, he=he, hr=hr, j=j) -> float:
            return 0.5 * (float(x[he, j].mean()) + float(x[hr, j].mean()))

        c_sens, c_noise = mean2(es), mean2(r)
        c_rebuilt = mean2(f_hat) + float(w[j])
        out.append({"c_i_N": c_i, "c_sens_N": c_sens, "c_noise_N": c_noise,
                    "c_fric_N": c_i - c_sens - c_noise, "c_rebuilt_N": c_rebuilt,
                    "c_rebuild_error_N": c_i - c_rebuilt,
                    "c_fric_law_N": mean2(law) + float(w[j]),
                    "hold_rows": [len(he), len(hr)]})
    return out


def friction_flag_limit_N(fs_leg_N: Sequence[float]) -> np.ndarray:
    """R45-2 / R46-1 (U-S8-25): calibration-friction flag per leg [N]: 0.1 kN when
    ``F_s,leg`` = 0, 0.75 kN when ``F_s,leg`` > 0."""
    fs = np.asarray(fs_leg_N, float)
    return np.where(fs > 0.0, NEAR_FRICTION_FLAG_FS_N, NEAR_FRICTION_FLAG_MIN_N)


def error_split(mask: np.ndarray, r_N: np.ndarray, e_s_N: np.ndarray, r_cal_N: np.ndarray,
                split: Sequence[Mapping[str, Any] | None], sigma_F_N: np.ndarray,
                fs_leg_N: Sequence[float]) -> dict[str, Any]:
    """R45-2 / R45-3: the calibrated-reading residual ``r_cal = F_hat_cal - (F - f)`` of the
    samples ``mask`` (k, 4) split per leg into the static part ``E_s - c_sens``, the
    calibration friction ``-c_fric`` and the noise ``r - c_noise`` (``r_cal = (E_s - c_sens) -
    c_fric + (r - c_noise)`` when ``F_hat_cal = F_hat - c_i``). Per leg: samples, ``max |E_s -
    c_sens|``, ``c_fric`` (signed) and its flag limit, ``std r / sigma_F``, ``max |r - c_noise| /
    sigma_F``, ``max |r_cal|``; 4-leg maxima and the three flags (static 0.65 kN, friction,
    total 1.6 kN; noise has no flag, R45-1 ② judges it)."""
    m = np.asarray(mask, bool) & np.isfinite(np.asarray(r_cal_N, float))
    r = np.asarray(r_N, float)
    es = np.asarray(e_s_N, float)
    rc = np.asarray(r_cal_N, float)
    sig = np.asarray(sigma_F_N, float)
    fr_lim = friction_flag_limit_N(fs_leg_N)
    legs: list[dict[str, Any]] = []
    for j in range(rc.shape[1]):
        sp = split[j] if j < len(split) else None
        sel = m[:, j]
        row: dict[str, Any] = {"leg": LEGS[j], "n": int(sel.sum()),
                               "c_fric_kN": None if sp is None else sp["c_fric_N"] / 1e3,
                               "fric_limit_kN": float(fr_lim[j]) / 1e3,
                               "static_max_kN": None, "noise_std_ratio": None,
                               "noise_max_sigma": None, "total_max_kN": None}
        if sp is not None:
            row["fric_flag"] = bool(abs(sp["c_fric_N"]) > fr_lim[j])
        if sel.any():
            row["total_max_kN"] = float(np.abs(rc[sel, j]).max()) / 1e3
            if sp is not None:
                row["static_max_kN"] = float(np.abs(es[sel, j] - sp["c_sens_N"]).max()) / 1e3
                n = r[sel, j] - sp["c_noise_N"]
                if sig[j] > 0.0:
                    row["noise_max_sigma"] = float(np.abs(n).max() / sig[j])
                    if n.size > 1:
                        row["noise_std_ratio"] = float(r[sel, j].std(ddof=1) / sig[j])
        legs.append(row)

    def mx(key: str) -> float | None:
        v = [x[key] for x in legs if x[key] is not None]
        return max(v) if v else None

    fr = [x["c_fric_kN"] for x in legs if x["c_fric_kN"] is not None]
    st, tot = mx("static_max_kN"), mx("total_max_kN")
    return {"n": int(m.sum()), "legs": legs, "static_max_kN": st, "total_max_kN": tot,
            "c_fric_max_abs_kN": max((abs(x) for x in fr), default=None),
            "noise_max_sigma": mx("noise_max_sigma"),
            "static_flag": None if st is None else bool(st > NEAR_STATIC_FLAG_N / 1e3),
            "fric_flag": None if not fr else bool(any(x.get("fric_flag") for x in legs)),
            "total_flag": None if tot is None else bool(tot > NEAR_TOTAL_FLAG_N / 1e3),
            "limits_kN": {"static": NEAR_STATIC_FLAG_N / 1e3,
                          "friction": [float(v) / 1e3 for v in fr_lim],
                          "total": NEAR_TOTAL_FLAG_N / 1e3}}


def reconstruct_reground_leg(results: Sequence[Mapping[str, Any]], f_nominal_N: np.ndarray,
                             f_min_N: float, guard_margin_N: float, round_index: int,
                             max_rounds: int, *, use_combined_verdict: bool = True
                             ) -> dict[str, Any]:
    """R45-4: ``C2Controller._leg_to_reground`` (LOAD_FIRST) of one probe round from the
    recorded ``probe_history.json`` results: weak = not skipped and (judged ungrounded or load
    estimate below ``F_min + guard_margin``); a light weak leg first (lowest estimate); else
    (combined verdict) the ungrounded weak leg with the smallest reading ``f_nominal_N`` at the
    round end, nothing when all four are ungrounded. ``acted`` False when the round count has
    reached ``max_rounds`` (``_finish_probe_round`` leaves the probe). The U65 rod-side fallback
    replacement is not reconstructed."""
    guard = float(f_min_N) + float(guard_margin_N)
    res = [r for r in results if isinstance(r, Mapping)]
    weak = [r for r in res if not r.get("is_skipped")
            and (not r.get("is_grounded") or float(r["load_estimate_N"]) < guard)]
    leg = None
    rule = "no weak leg"
    if weak:
        light = [r for r in weak if float(r["load_estimate_N"]) < guard]
        if light:
            leg = int(min(light, key=lambda r: float(r["load_estimate_N"]))["leg_index"])
            rule = "light (load estimate < F_min + guard margin)"
        elif not use_combined_verdict:
            leg, rule = int(weak[0]["leg_index"]), "first weak leg (stiffness verdict)"
        else:
            ungrounded = [r for r in res if not r.get("is_grounded")]
            if len(ungrounded) == len(LEGS):
                rule = "probe_unresolved (all four ungrounded)"
            else:
                cand = [r for r in weak if not r.get("is_grounded")] or weak
                fn = np.asarray(f_nominal_N, float)
                leg = int(min(cand, key=lambda r: fn[int(r["leg_index"])])["leg_index"])
                rule = "combined: smallest reading among the weak / ungrounded legs"
    acted = leg is not None and round_index + 1 < int(max_rounds)
    return {"leg": None if leg is None else LEGS[leg], "leg_index": leg, "acted": acted,
            "rule": rule, "guard_level_kN": guard / 1e3}


def low_load_probe_records(probes: Sequence[Sequence[Mapping[str, Any]]],
                           pr_legs: Sequence[Mapping[str, Any]], tc: np.ndarray,
                           lower_N: np.ndarray, f_nominal_N: np.ndarray, t_pad: np.ndarray,
                           f_judged_N: np.ndarray, f_min_N: float, t0: float, *,
                           guard_margin_N: float = GUARD_MARGIN_DEFAULT_N,
                           max_rounds: int = MAX_ROUNDS_DEFAULT,
                           margin_N: float = LOW_PROBE_MARGIN_N,
                           window_s: float = LOW_PROBE_WINDOW_S) -> list[dict[str, Any]]:
    """R45-4 (spec rev. 45 215.5): probes whose lower bound ``F_hat_cal - F_band`` (``lower_N``,
    10 Hz) at the round start (last row at or before the first move start of the round) is below
    ``F_min + margin_N``. Over ``[t_2, t_2 + window_s]`` (``t_2`` = the leg's second hold end):
    F2 margin ``min lower - F_min`` (10 Hz), true margin ``min F - F_min`` (judged 1 ms force),
    ``T_2 - T_0`` and ``E - T_2`` (s6 probe rows ``pr_legs``, same round / leg) and the
    reconstructed re-ground decision of the round (:func:`reconstruct_reground_leg`). Probe
    history times are record times; ``tc`` / ``t_pad`` are relative to the run start ``t0``."""
    tc = np.asarray(tc, float)
    low = np.asarray(lower_N, float)
    tp = np.asarray(t_pad, float)
    fj = np.asarray(f_judged_N, float)
    by = {(r.get("round"), r.get("leg")): r for r in pr_legs or []}
    out = []
    for i, rnd in enumerate(probes or []):
        rows = [r for r in rnd if isinstance(r, Mapping)]
        starts = [float(r["t_move_start_s"]) - t0 for r in rows
                  if isinstance(r.get("t_move_start_s"), int | float)]
        ends = [float(r["t_second_hold_end_s"]) - t0 for r in rows
                if isinstance(r.get("t_second_hold_end_s"), int | float)]
        if not starts or not ends or tc.size == 0:
            continue
        if min(starts) < tc[0] - 1e-9:
            continue  # round before this record (ML episode: rounds of the base run)
        k0 = int(np.clip(np.searchsorted(tc, min(starts) + 1e-9, side="right") - 1, 0,
                         tc.size - 1))
        k_end = int(np.clip(np.searchsorted(tc, max(ends) - 1e-9), 0, tc.size - 1))
        decision = None
        for r in rows:
            leg = int(r["leg_index"])
            lo0 = low[k0, leg]
            if r.get("is_skipped") or not np.isfinite(lo0) or lo0 >= f_min_N + margin_N:
                continue
            if not isinstance(r.get("t_second_hold_end_s"), int | float):
                continue
            if decision is None:
                decision = reconstruct_reground_leg(rows, np.asarray(f_nominal_N)[k_end],
                                                    f_min_N, guard_margin_N, i, max_rounds)
            t2 = float(r["t_second_hold_end_s"]) - t0
            w = (tc >= t2 - 1e-9) & (tc <= t2 + window_s + 1e-9) & np.isfinite(low[:, leg])
            wp = (tp >= t2 - 1e-9) & (tp <= t2 + window_s + 1e-9)
            p = by.get((i, LEGS[leg])) or {}
            e, t_0, t_2 = (p.get("load_estimate_kN"), p.get("truth_cyl_kN"),
                           p.get("truth_end_kN"))
            out.append({
                "round": i, "leg": LEGS[leg], "t_round_start_s": min(starts),
                "lower_at_round_start_kN": float(lo0) / 1e3,
                "threshold_kN": (f_min_N + margin_N) / 1e3, "t_second_hold_end_s": t2,
                "window_s": [t2, t2 + window_s],
                "F2_margin_min_kN": None if not w.any()
                else float(low[w, leg].min() - f_min_N) / 1e3,
                "true_margin_min_kN": None if not wp.any()
                else float(fj[wp, leg].min() - f_min_N) / 1e3,
                "T2_minus_T0_kN": None if t_0 is None or t_2 is None else float(t_2) - float(t_0),
                "E_minus_T2_kN": None if e is None or t_2 is None else float(e) - float(t_2),
                "load_estimate_kN": float(r["load_estimate_N"]) / 1e3,
                "is_grounded": r.get("is_grounded"),
                "reground": decision,
                "reground_this_leg": decision["leg"] == LEGS[leg] and decision["acted"]})
    return out


def lower_estimate_series(series: Mapping[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray,
                                                                     dict[str, str]]:
    """C-S8-16 ① (spec rev. 43 213.3.3): the spec-199 lower bound ``F_hat_cal - F_band,i`` and
    the calibrated reading of every 10 Hz period, with their sources.

    * ``F_lower_est_N`` (controller ``_load_estimate_N(forces.lower)``) when recorded, else the
      reading lower bound ``F_lower_N`` (= ``last_forces.lower``, calibrated, E-6 deduction, **no**
      band) minus the per-leg band ``leg_band_N`` (common ``F_band_N`` when absent), else
      ``F_hat_N`` minus the band (the reading is then not calibrated);
    * ``F_nominal_N`` (``last_forces.nominal``) when recorded, else ``F_lower_N`` (equal except on
      an E-6 deduction leg), else ``F_hat_N``.

    Returns (lower estimate, calibrated reading, sources)."""
    f_hat = np.asarray(series["F_hat_N"], float)
    band = np.asarray(series["leg_band_N"], float) if "leg_band_N" in series else None
    if band is None or not np.isfinite(band).any():
        band = np.repeat(np.asarray(series["F_band_N"], float)[:, None], f_hat.shape[1], axis=1)
    reading_low = (np.asarray(series["F_lower_N"], float) if "F_lower_N" in series
                   else np.full_like(f_hat, np.nan))
    has_low = np.isfinite(reading_low).any()
    src: dict[str, str] = {}
    est = np.asarray(series["F_lower_est_N"], float) if "F_lower_est_N" in series else None
    if est is not None and np.isfinite(est).any():
        src["lower"] = "F_lower_est_N (controller _load_estimate_N(forces.lower))"
    elif has_low:
        est = reading_low - band
        src["lower"] = "F_lower_N - leg_band_N (reconstructed _load_estimate_N)"
    else:
        est = f_hat - band
        src["lower"] = "F_hat_N - band (not calibrated)"
    nom = np.asarray(series["F_nominal_N"], float) if "F_nominal_N" in series else None
    if nom is not None and np.isfinite(nom).any():
        src["nominal"] = "F_nominal_N (controller last_forces.nominal)"
    elif has_low:
        nom = reading_low
        src["nominal"] = "F_lower_N (calibrated; = nominal except E-6 deduction legs)"
    else:
        nom = f_hat
        src["nominal"] = "F_hat_N (raw reading, not calibrated)"
    return est, nom, src


# --- rev. 46 (C-S8-22) helpers ------------------------------------------------------------------


def forced_window(result: Mapping[str, Any], t_end_rel_s: float,
                  series: Mapping[str, np.ndarray] | None = None) -> dict[str, Any] | None:
    """C-S8-22 ③ / ML-1: the forced (open-loop) window of a ``ForcedRetract`` run, times
    relative to the run start ``settings.start_t_s``. RE1c cases: ``result.event_t_s`` is
    relative; ML retract episodes: ``result.event_t_s`` is the engine time (``job_ml_episode``).
    The wrapper overrides every leg from its start to the run end (``s6_stage2.ForcedRetract``:
    the forced leg retracts, every other leg 0, then all 0), so the window ends at the run end;
    ``done_s`` = the last 10 Hz period with the forced retract command (record). None for any
    other run."""
    s = result.get("settings") or {}
    s8 = s.get("s8") or {}
    ep = s.get("episode") or {}
    ev = result.get("event_t_s")
    if ev is None:
        return None
    t0 = float(s.get("start_t_s") or 0.0)
    if s8.get("event") in FORCED_EVENTS:
        start = float(ev)
        leg = (s8.get("event_spec") or {}).get("leg")
        source = "RE1c (settings.s8.event), event_t_s relative"
    elif ep.get("kind") == ML_FORCED_KIND:
        start = float(ev) - t0
        leg = ep.get("leg")
        source = "ML retract episode (settings.episode.kind), event_t_s engine time - start_t_s"
    else:
        return None
    fr = result.get("forced_retract") or (result.get("event") or {}).get("forced_retract") or {}
    if fr.get("others") == "controller":
        # U-S8-27 / C-S8-25 ②: only the forced leg until done, then the controller
        done = fr.get("done_t_s")
        done_rel = None if done is None else float(done) - t0
        return {"start_s": start, "end_s": float(t_end_rel_s) if done_rel is None else done_rel,
                "leg": leg, "done_s": done_rel, "source": source, "others": "controller",
                "rule": "ForcedRetract(others='controller'): forced leg only, start .. done "
                        "(U-S8-27); run end when the retraction never finished"}
    out: dict[str, Any] = {"start_s": start, "end_s": float(t_end_rel_s), "leg": leg,
                           "done_s": None, "source": source, "others": "zero",
                           "rule": "ForcedRetract overrides every leg from its start to the run "
                                   "end (U-S8-24)"}
    if series is not None and leg in LEGS and "issued_u" in series:
        tc = np.asarray(series["t"], float) - t0
        u = np.asarray(series["issued_u"], float)[:, LEGS.index(leg)]
        k = np.flatnonzero((tc >= start - 1e-9) & (u < 0.0))
        out["done_s"] = None if k.size == 0 else float(tc[k[-1]])
    return out


def forced_mask(t_rel_s: np.ndarray, window: Mapping[str, Any] | None,
                extra_s: float = 0.0) -> np.ndarray:
    """Samples inside the forced window ``[start, end + extra_s]`` (relative times)."""
    t = np.asarray(t_rel_s, float)
    if window is None:
        return np.zeros(t.shape, bool)
    return (t >= float(window["start_s"]) - 1e-9) & \
        (t <= float(window["end_s"]) + float(extra_s) + 1e-9)


def rod_fault_injected(settings: Mapping[str, Any]) -> bool:
    """C-S8-22 ④: whether the run injects a rod-sensor fault (:data:`ROD_FAULT_INJECTION_KEYS`
    anywhere in the settings tree with a truthy value)."""
    return any(bool(_find_key(settings, k)) for k in ROD_FAULT_INJECTION_KEYS)


ROD_FAULT_EXPECTED_PERIODS = 2
"""Spec rev. 50 220.6 ③ (U-S8-43): a rod fallback warning of the injected leg within
``[fault time, + 2 control periods]`` is expected (injection), not a FLAG (ASSUMPTION: 0-period
detection delay seen, 10 Hz sample phase margin)."""


def rod_fault_of(res: Mapping[str, Any]) -> tuple[str | None, float | None]:
    """(injected rod-sensor fault leg, fault time relative to ``t0``) of a run: the
    ``rod_fault`` of ``settings.s8.event_spec`` or ``result.event.spec`` and
    ``result.rod_fault_t_s``; ``(None, None)`` without an injection."""
    s8 = ((res.get("settings") or {}).get("s8") or {})
    ev = res.get("event") if isinstance(res.get("event"), Mapping) else {}
    leg = None
    for spec in (s8.get("event_spec"), (ev or {}).get("spec")):
        rf = spec.get("rod_fault") if isinstance(spec, Mapping) else None
        if isinstance(rf, Mapping) and rf.get("leg") in LEGS:
            leg = rf["leg"]
            break
    t_f = res.get("rod_fault_t_s")
    return leg, None if t_f is None else float(t_f)


def mark_expected_rod_fallback(events: list[dict[str, Any]], leg: str | None,
                               t_fault_s: float | None, period_s: float) -> None:
    """Spec rev. 50 220.6 ③: set ``expected_injected`` on each rod fallback event (in place):
    True for the injected leg within ``[t_fault, t_fault + 2 T]`` (+-1e-6 s), else False."""
    hi = None if t_fault_s is None else t_fault_s + ROD_FAULT_EXPECTED_PERIODS * period_s
    for e in events:
        e["expected_injected"] = bool(
            leg is not None and hi is not None and e.get("leg") == leg
            and t_fault_s - 1e-6 <= float(e["t_s"]) <= hi + 1e-6)


def rod_fallback_events(events: Sequence[tuple[float, str]],
                        window: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """C-S8-22 ④: ``WARN_ROD_PRESSURE_FALLBACK:<leg>`` events (relative times) with the
    ``INFO_ROD_PRESSURE_FAULT_REASON:<leg>:<reason>`` of the same leg and instant and whether
    they fall in the forced window."""
    reasons = {}
    for t, name in events:
        parts = name.split(":")
        if parts[0] == ROD_FAULT_REASON_INFO and len(parts) >= 3:
            reasons[(round(t, 6), parts[1])] = ":".join(parts[2:])
    out = []
    for t, name in events:
        parts = name.split(":")
        if parts[0] != ROD_FALLBACK_WARNING:
            continue
        leg = parts[1] if len(parts) > 1 else None
        inside = window is not None and float(t) >= float(window["start_s"]) - 1e-9
        out.append({"t_s": float(t), "leg": leg, "reason": reasons.get((round(t, 6), leg)),
                    "in_forced_window": bool(inside)})
    return out


def pooled_side_std(laws: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    """Control rev. 46 216.6 (1): per side (front FL + FR, rear RL + RR) the residual standard
    deviation pooled over the legs and runs of ``laws`` (``F1_law`` dicts with ``metrics`` of
    noisy sensors), from the per-leg ``n`` / mean / std (exact pooling of the sample variance
    about the pooled mean); ratio to sigma_F and its relative standard error ``1 / sqrt(2 (n -
    1))``; flag outside +-:data:`WIKA_POOLED_STD_TOL`."""
    sides = {"front": (0, 1), "rear": (2, 3)}
    acc = {k: [] for k in sides}
    for law in laws:
        lm = (law or {}).get("metrics")
        if not lm:
            continue
        for side, legs in sides.items():
            for j in legs:
                n, mu, sd = lm["n"][j], lm["mean_N"][j], lm["std_N"][j]
                sig = lm["sigma_F_N"][j]
                if n and mu is not None and sd is not None and sig > 0.0:
                    acc[side].append((int(n), float(mu), float(sd), float(sig)))
    if not any(acc.values()):
        return None
    out: dict[str, Any] = {}
    for side, parts in acc.items():
        if not parts:
            out[side] = None
            continue
        n = sum(p[0] for p in parts)
        mean = sum(p[0] * p[1] for p in parts) / n
        ss = sum((p[0] - 1) * p[2] ** 2 + p[0] * (p[1] - mean) ** 2 for p in parts)
        std = math.sqrt(ss / (n - 1))
        sig = parts[0][3]
        ratio = std / sig
        out[side] = {"n": n, "legs_runs": len(parts), "std_N": std, "sigma_F_N": sig,
                     "ratio": ratio, "rel_std_error": 1.0 / math.sqrt(2.0 * (n - 1)),
                     "flag": bool(abs(ratio - 1.0) > WIKA_POOLED_STD_TOL)}
    return out


def _pad_at(pads, t_abs: np.ndarray, key: str) -> np.ndarray:
    """Pad-record value at the control instants (sample with the nearest time)."""
    tp = np.asarray(pads["t"], float)
    i = np.clip(np.searchsorted(tp, t_abs - 1e-9), 0, tp.size - 1)
    j = np.clip(i - 1, 0, tp.size - 1)
    pick = np.where(np.abs(tp[j] - t_abs) < np.abs(tp[i] - t_abs), j, i)
    return np.asarray(pads[key], float)[pick]


def _phase_of(series, k: int) -> str:
    return str(series["phase"][k])


def judged_force_min(pads) -> np.ndarray:
    """S8-A2 (``dynamics_model.md`` 5.26.10): the 1 ms rod-force minimum
    ``F_cyl_min_interval``, except on airborne samples (``airborne``, 20 ms pad normal <= 0),
    which use the 20 ms mean ``F_cyl_mean_20ms`` (the airborne 1 ms minimum is rod ringing).
    Records without the S8-A2 fields (S7, older S8) return the 1 ms minimum unchanged."""
    f = np.asarray(pads["F_cyl_min_interval"], float)
    if "airborne" not in pads or "F_cyl_mean_20ms" not in pads:
        return f
    air = np.asarray(pads["airborne"], bool)
    return np.where(air, np.asarray(pads["F_cyl_mean_20ms"], float), f)


def air_record(pads, rod_weight_N: Sequence[float]) -> dict[str, Any] | None:
    """S8-A2 record: per leg, airborne samples, their 1 ms minimum of ``F + m g`` and the
    range of the 20 ms mean ``F + m g`` (expected within +-0.3 kN)."""
    if pads is None or "airborne" not in pads or "F_cyl_mean_20ms" not in pads:
        return None
    air = np.asarray(pads["airborne"], bool)
    w = np.asarray(rod_weight_N, float)
    f1 = np.asarray(pads["F_cyl_min_interval"], float) + w[None, :]
    f20 = np.asarray(pads["F_cyl_mean_20ms"], float) + w[None, :]
    out: dict[str, Any] = {"samples": air.sum(axis=0).tolist(), "min_1ms_kN": [],
                           "mean20_min_kN": [], "mean20_max_kN": []}
    for j in range(air.shape[1]):
        sel = air[:, j]
        out["min_1ms_kN"].append(float(f1[sel, j].min()) / 1e3 if sel.any() else None)
        out["mean20_min_kN"].append(float(f20[sel, j].min()) / 1e3 if sel.any() else None)
        out["mean20_max_kN"].append(float(f20[sel, j].max()) / 1e3 if sel.any() else None)
    return out


def _per_leg_value(v: Any, default: float = 0.0) -> np.ndarray:
    if v is None:
        return np.full(4, default)
    return np.broadcast_to(np.asarray(v, float), (4,)).astype(float)


def _reading_law(case, pads, t_abs: np.ndarray, params, *, wika: bool) -> dict[str, Any]:
    """R45-1 inputs of one case: ``E_s`` at the 10 Hz rows (pad pressures of the same instant),
    ``sigma_F = sqrt((sigma_h A_p)^2 + (sigma_r A_ann)^2)`` from the run's sensor meta, the area
    source and two record checks (``F - f`` vs the pad ``F_pressure``; ``F_pressure`` vs ``p_h A_p
    - p_r A_ann``). ``available`` False (fallback (b)) when the pad record has no ``f_seal`` /
    pressures, or a WIKA run has no drawn terms (and is not the legacy grade)."""
    sensors = (case["result"].get("runner") or {}).get("sensors") or {}
    cfg = sensors.get("legs") or {}
    grade = cfg.get("pressure_error_grade")
    terms = sensors.get("pressure_error_terms")
    missing = [k for k in ("f_seal", "head_pressure", "rod_pressure") if k not in pads]
    if wika and not terms and grade != "legacy":
        missing.append("runner.sensors.pressure_error_terms")
    out: dict[str, Any] = {"available": not missing, "missing": missing, "grade": grade,
                           "has_terms": bool(terms)}
    if missing:
        out["note"] = "fallback (b): law terms missing " + ", ".join(missing)
        return out
    a_p, a_a, src = cylinder_areas_m2(params, pads)
    sig_h = _per_leg_value(cfg.get("pressure_noise_std_Pa"))
    sig_r = _per_leg_value(cfg.get("rod_pressure_noise_std_Pa", cfg.get("pressure_noise_std_Pa")))
    p_h = _pad_at(pads, t_abs, "head_pressure")
    p_r = _pad_at(pads, t_abs, "rod_pressure")
    out["E_s"] = sensor_static_error_N(terms, grade, p_h, p_r, a_p, a_a, cfg, t_abs)
    out["sigma_F_N"] = np.hypot(sig_h * a_p, sig_r * a_a).tolist()
    out["limit_N"] = f1_law_limit_N(np.asarray(out["sigma_F_N"])).tolist()
    out["areas_m2"] = {"head": a_p.tolist(), "annulus": a_a.tolist(), "source": src}
    if "F_pressure" in pads:
        fp = np.asarray(pads["F_pressure"], float)
        law_rec = np.asarray(pads["F_cyl"], float) - np.asarray(pads["f_seal"], float)
        area_rec = (np.asarray(pads["head_pressure"], float) * a_p
                    - np.asarray(pads["rod_pressure"], float) * a_a)
        out["check_F_minus_f_vs_F_pressure_N"] = float(np.nanmax(np.abs(law_rec - fp)))
        out["check_area_law_N"] = float(np.nanmax(np.abs(area_rec - fp)))
    out["rule"] = ("|F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18), raw reading "
                   "F_hat_N, phases other than CHECK" + ("; mean <= 0.1 kN, std / sigma_F in "
                                                         "[0.85, 1.15] per leg"
                                                         if np.any(sig_h > 0) else ""))
    return out


def _calibration_split_of_case(case, series, phases, tc, f_hat, law_force, e_s, params,
                               cal_off, post) -> list[dict[str, Any] | None] | None:
    """:func:`calibration_split` of one case: holds from ``r8_series.npz`` ``computed_u``
    (:func:`check_hold_rows`), ``c_i`` from ``controller_meta.zero_calibration.offsets_N``
    (else the median ``F_hat - F_hat_cal`` outside CHECK). None without ``computed_u``."""
    p = Path(case["dir"]) / "r8_series.npz"
    if not p.exists():
        return None
    with np.load(p, allow_pickle=False) as r8:
        if "computed_u" not in r8.files:
            return None
        t8 = np.asarray(r8["t"], float)
        u8 = np.asarray(r8["computed_u"], float)
    t_abs = np.asarray(series["t"], float)
    idx = np.clip(np.searchsorted(t8, t_abs - 1e-9), 0, t8.size - 1)
    u = u8[idx]
    zc = (case["result"].get("controller_meta") or {}).get("zero_calibration") or {}
    c_i = zc.get("offsets_N")
    if c_i is None or len(c_i) != 4:
        c_i = [float(np.nanmedian(cal_off[post, j])) if post.any() else None for j in range(4)]
    holds = check_hold_rows(phases, u, tc)
    return calibration_split(f_hat, law_force, e_s, _rod_weight_N(params), c_i, holds)


# --- per-case S8 metrics ------------------------------------------------------------------------


def s8_case_metrics(case, m, params, pr: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Everything the F / M rows need for one case (module docstring). ``pr``: the s6 probe
    metrics of the case (R45-4 ``T2 - T0`` / ``E - T2``; None leaves them out)."""
    pads = case.get("pads")
    s8 = _s8(case)
    series = load_series(Path(case["dir"]))
    tm = m["times_s"]
    t0 = float(tm["t0"])
    f_min = float(m["F_min_N"])
    out: dict[str, Any] = {"case": m["case"], "s8": s8, "rigid": lift_transient_rules_apply(s8),
                           "crawler_contact": s8.get("crawler_contact") or "nsc_rigid",
                           "crawler_check_passed": s8.get("crawler_check_passed"),
                           "liftoff_s": tm.get("liftoff"), "ready_s": tm.get("ready"),
                           "F_min_N": f_min, "h4_mechanism": m.get("h4_mechanism"),
                           "end": case["result"].get("s8_end")}
    out["lock_valve"] = lock_valve_premise(s8, case["result"].get("controller_meta"))
    if pads is None:
        return out
    t_rel = np.asarray(pads["t"], float) - t0
    mask = np.ones(t_rel.size, bool)
    ev_t = case["result"].get("event_t_s")
    if ev_t is not None:
        mask &= t_rel < float(ev_t)
    for a, b in _windows(case, "reanchor", tm["end"]):
        mask &= ~((t_rel >= a) & (t_rel <= b))
    f_judged = judged_force_min(pads)  # S8-A2: airborne samples on the 20 ms mean
    out["c1"] = c1_metrics(t_rel, f_judged, tm.get("liftoff"), mask)
    out["air"] = air_record(pads, _rod_weight_N(params))
    out["fs_leg_N"] = _fs_leg_N(case, pads).tolist()
    plant_rec = case["result"].get("s8_plant_record") or {}
    sf_rec = plant_rec.get("seal_friction") or {}
    out["chatter"] = {"band_edge_chatter": sf_rec.get("band_edge_chatter"),
                      "window_s": sf_rec.get("band_edge_chatter_window_s"),
                      "slip_starts": sf_rec.get("slip_starts"),
                      "pressure_floor": plant_rec.get("pressure_floor"),
                      "pressure_floor_measurements": (case["result"].get("monitor") or {}).get(
                          "pressure_floor_measurements")}
    # pair-window values (R40-4) need only the pad record: L1 twins (L group, no s8_series.npz)
    # give them too (C-S8-22 ⑤)
    out["pair_window"] = _pair_window_values(case, m, pads, t_rel)
    if series is None:
        out["series"] = None
        return out
    t_abs = np.asarray(series["t"], float)
    tc = t_abs - t0
    f_true = _pad_at(pads, t_abs, "F_cyl")
    f_seal = (_pad_at(pads, t_abs, "f_seal") if "f_seal" in pads
              else np.zeros_like(f_true))
    f_hat = np.asarray(series["F_hat_N"], float)
    band_s = np.asarray(series["leg_band_N"], float)
    if not np.isfinite(band_s).any():
        band_s = np.repeat(np.asarray(series["F_band_N"], float)[:, None], 4, axis=1)
    # C-S8-16 ①: lower bound = F_hat_cal - F_band,i (spec 199), calibrated reading F_hat_cal
    lower, f_cal, lower_src = lower_estimate_series(series)
    contact = case["result"]["settings"].get("contact", "combined")
    if contact == "pressure":
        lower_j = f_hat.copy()
    else:
        lower_j = lower
    eps = f_hat - f_true
    phases = np.array([_phase_of(series, k) for k in range(tc.size)])
    lo = tm.get("liftoff")
    after = tc >= (lo if lo is not None else np.inf)
    share = _sensor_share_N(case)
    wika = _is_wika(case)
    fs = np.asarray(out["fs_leg_N"])
    # F1 (R43-1): calibrated reading outside CHECK, share 0.6 kN + kappa |F| (WIKA)
    raw_by_phase = {}
    for ph in sorted(set(phases.tolist())):
        sel = phases == ph
        raw_by_phase[ph] = {"max_kN": float(eps[sel].max()) / 1e3,
                            "min_kN": float(eps[sel].min()) / 1e3}
    post = phases != "check"
    eps_cal = f_cal - f_true
    share_f = f1_share_N(f_true, wika=wika)
    excess_cal = np.abs(eps_cal) - fs[None, :] - share_f
    raw_excess = np.abs(eps) - fs[None, :] - share
    # judged basis: WIKA = calibrated reading (R43-1); ideal sensor = the reading itself (it is
    # the pressure truth F - f; the zero-calibration offset c_i of an ideal sensor is the
    # friction residual of the CHECK round trip, recorded below, not a sensor error)
    excess1 = excess_cal if wika else raw_excess
    ok1 = post[:, None] & np.isfinite(excess1)
    raw_viol = int(np.sum(raw_excess > NUMERIC_TOL_N))
    cal_off = f_hat - f_cal  # = zero-calibration offset c_i (+ E-6 deduction legs)
    # R45-1 (U-S8-18): reading law on the raw reading, r = F_hat - (F - f + E_s)
    law = _reading_law(case, pads, t_abs, params, wika=wika)
    out["F1_law"] = law
    e_s = law.pop("E_s", None)  # (k, 4) array, not written to the JSON
    r_law = None
    if law["available"]:
        r_law = f_hat - (f_true - f_seal + e_s)
        lm = f1_law_metrics(r_law, np.asarray(law["sigma_F_N"]), post)
        lm["t_s"] = [None if k is None else float(tc[k]) for k in lm["t_index"]]
        lm["phase"] = [None if k is None else str(phases[k]) for k in lm["t_index"]]
        law["metrics"] = lm
    else:
        # fallback (b): calibrated reading (WIKA) with 1.3 kN, ideal: the raw rule
        fb_share = (F1_FALLBACK_CONST_N + F1_SPAN_SHARE * np.abs(f_true) if wika
                    else np.full(f_true.shape, F1_CONST_SHARE_N["ideal"]))
        fb_exc = (np.abs(eps_cal if wika else eps) - fs[None, :] - fb_share)
        okf = post[:, None] & np.isfinite(fb_exc)
        law["fallback"] = {
            "violations": int(np.sum(fb_exc[okf] > NUMERIC_TOL_N)),
            "max_excess_kN": float(fb_exc[okf].max()) / 1e3 if okf.any() else None,
            "n_samples": int(okf.sum()),
            "rule": ("fallback (b): |F_hat_cal - F| <= F_s,leg + 1.3 kN + 0.025 |F|" if wika
                     else "fallback: |F_hat - F| <= F_s,leg + 0.1 kN (ideal sensor)")}
    # spec rev. 50 220.6 ④: the calibrated-reading record leaves out the faulty leg after an
    # injected rod-sensor fault (its raw two-sensor reading; the controller uses the fallback)
    f_leg, f_t = rod_fault_of(case["result"])
    fault_cut = np.zeros(excess_cal.shape, bool)
    if f_leg is not None and f_t is not None:
        fault_cut[tc >= f_t - 1e-9, LEGS.index(f_leg)] = True
    cal_post = np.broadcast_to(post[:, None], excess_cal.shape) & ~fault_cut
    cal_use = cal_post & np.isfinite(excess_cal)
    n_fault_excl = int((np.broadcast_to(post[:, None], excess_cal.shape)
                        & np.isfinite(excess_cal) & fault_cut).sum())
    out["F1"] = {"violations": int(np.sum(excess1[ok1] > NUMERIC_TOL_N)),
                 "max_excess_kN": float(excess1[ok1].max()) / 1e3 if ok1.any() else None,
                 "n_samples": int(ok1.sum()),
                 "reading": lower_src["nominal"] if wika else "F_hat_N (ideal sensor)",
                 "rule": (f"|F_hat_cal - F| <= F_s,leg + {F1_CONST_SHARE_N['wika'] / 1e3:g} kN + "
                          f"{F1_SPAN_SHARE:g} |F| (R43-1, U-S8-15)" if wika
                          else "|F_hat - F| <= F_s,leg + 0.1 kN (ideal sensor)")
                         + ", phases other than CHECK",
                 "calibrated": {
                     "violations": int(np.sum(excess_cal[cal_use] > NUMERIC_TOL_N)),
                     "max_excess_kN": float(np.nanmax(np.where(cal_post, excess_cal, np.nan)))
                     / 1e3 if cal_post.any() else None,
                     "offset_kN_per_leg": [float(np.nanmedian(cal_off[cal_post[:, j], j])) / 1e3
                                           if cal_post[:, j].any() else None for j in range(4)],
                     "fault_leg_samples_excluded": n_fault_excl,
                     "fault_exclusion": None if not fault_cut.any() else
                     f"{f_leg} from {f_t:.2f} s (injected rod-sensor fault, spec rev. 50 "
                     "220.6 ④)"},
                 "raw": {"by_phase": raw_by_phase, "violations": raw_viol,
                         "max_excess_kN": float(raw_excess.max()) / 1e3,
                         "share_kN": share / 1e3,
                         "note": "raw reading before the zero calibration (record, R43-1)"}}
    sens = eps_cal + f_seal  # sensor part of the calibrated reading error (friction removed)
    lo_b, hi_b = f_min + NEAR_FMIN_BAND_N[0], f_min + NEAR_FMIN_BAND_N[1]
    near = post[:, None] & (f_true >= lo_b) & (f_true <= hi_b) & np.isfinite(sens)
    # R46-1 (U-S8-25, C-S8-22 ⑥): the ideal-sensor value is the calibration offset c_i (the
    # CHECK friction residual), flagged with the calibration-friction limit per leg
    near_lim = (friction_flag_limit_N(fs) if not wika
                else np.full(4, NEAR_FMIN_SHARE_N["wika"]))
    out["F1_near_fmin"] = {
        "n": int(near.sum()),
        "max_abs_kN": float(np.abs(sens[near]).max()) / 1e3 if near.any() else None,
        "limit_kN": float(near_lim.max()) / 1e3,
        "per_leg_limit_kN": (near_lim / 1e3).tolist(),
        "limit_rule": ("R46-1: 0.1 kN at F_s,leg = 0, 0.75 kN at F_s,leg > 0 (U-S8-25)"
                       if not wika else "R43-1 WIKA share 0.85 kN (no law terms)"),
        "per_leg_max_abs_kN": [float(np.abs(sens[near[:, j], j]).max()) / 1e3
                               if near[:, j].any() else None for j in range(4)]}
    out["F1_near_fmin"]["flag"] = (None if not near.any() else bool(any(
        v is not None and v > lim + 1e-12 for v, lim in
        zip(out["F1_near_fmin"]["per_leg_max_abs_kN"], out["F1_near_fmin"]["per_leg_limit_kN"],
            strict=True))))
    # R45-2 / R45-3 (U-S8-19): split of the calibrated residual into static / calibration
    # friction / noise (c_i from the CHECK holds, spec 215.3)
    split = None
    if law["available"]:
        split = _calibration_split_of_case(case, series, phases, tc, f_hat, f_true - f_seal,
                                           e_s, params, cal_off, post)
        out["calibration_split"] = split
    n_pad = _pad_at(pads, t_abs, "N")
    if split is not None:
        sig = np.asarray(law["sigma_F_N"])
        out["R45_2"] = error_split(near, r_law, e_s, sens, split, sig, fs)
        air_split = error_split(air_mask(f_true, n_pad, post), r_law, e_s, sens, split, sig, fs)
    else:
        air_split = None
    # C-S8-19 ② / R45-3: airborne calibrated-reading residual (record, flag 1.7 kN)
    out["F1_air"] = air_residual(sens, f_true, n_pad, post, [str(p) for p in phases],
                                 split=air_split)
    # R45-4 (U-S8-19): low-load probe F2 record
    if contact != "pressure" and case.get("probes"):
        cfg = str(case["result"]["settings"].get("controller_config") or "")
        gm = _config_float(cfg, "guard_margin_N", GUARD_MARGIN_DEFAULT_N)
        mr = _config_float(cfg, "max_rounds", MAX_ROUNDS_DEFAULT)
        out["R45_4"] = low_load_probe_records(
            case["probes"], (pr or {}).get("legs") or [], tc, lower, f_cal,
            t_rel, judged_force_min(pads), f_min, t0,
            guard_margin_N=GUARD_MARGIN_DEFAULT_N if gm is None else gm,
            max_rounds=MAX_ROUNDS_DEFAULT if mr is None else int(mr))
    # C-S8-22 ③ / ④ (U-S8-24): forced (open-loop) window and rod-pressure fallback warnings
    fw = forced_window(case["result"], float(tm["end"]), series)
    in_forced = forced_mask(tc, fw)
    out["forced_window"] = fw
    fb_events = rod_fallback_events(_event_names(case), fw)
    mark_expected_rod_fallback(fb_events, f_leg, f_t, _period(tc))  # rev. 50 220.6 ③
    out["rod_fallback"] = {
        "events": fb_events,
        "injected": rod_fault_injected(case["result"]["settings"]),
        "fault_leg": f_leg, "fault_t_s": f_t,
        "expected_window_s": None if f_t is None else
        [f_t, f_t + ROD_FAULT_EXPECTED_PERIODS * _period(tc)]}
    # F2 (combined only): F_hat_cal - F_band,i - F <= sensor share after lift-off, outside the
    # forced window (C-S8-22 ③)
    if contact != "pressure":
        # C-S8-70 ④ (spec rev. 65 333): a head-fault run leaves out the fault leg from the
        # injection arm time (its reading carries the injected jump); recorded apart
        hf_cut, hf_spec, hf_arm = head_fault_leg_cut(case["result"], tc)
        if fw is not None:
            fsel = (after & in_forced)[:, None] & ~hf_cut
            fex = (lower - f_true)[fsel]
            okf = np.isfinite(fex)
            out["F2_forced"] = {
                "window_s": [fw["start_s"], fw["end_s"]], "done_s": fw["done_s"],
                "samples": int(okf.sum()),
                "violations": int((fex[okf] > share + NUMERIC_TOL_N).sum()),
                "max_kN": None if not okf.any() else float(fex[okf].max()) / 1e3}
        gate_1d = after & ~in_forced
        gate = gate_1d[:, None] & ~hf_cut
        excess = (lower - f_true)[gate]
        ok = np.isfinite(excess)
        cross = (f_hat - band_s - f_true)[gate]
        okc = np.isfinite(cross)
        reading = (np.asarray(series["F_lower_N"], float) - f_true)[gate]
        okr = np.isfinite(reading)
        if hf_cut.any():
            cut_sel = gate_1d[:, None] & hf_cut
            cex = (lower - f_true)[cut_sel]
            okx = np.isfinite(cex)
            out["F2_faulty_leg_after_injection"] = {
                "leg": hf_spec["leg"], "from_s": hf_arm, "samples": int(okx.sum()),
                "violations": int((cex[okx] > share + NUMERIC_TOL_N).sum()),
                "max_kN": None if not okx.any() else float(cex[okx].max()) / 1e3,
                "rule": "C-S8-70 ④: fault leg from the head-fault arm time, record only"}
        out["F2"] = {"violations": int((excess[ok] > share + NUMERIC_TOL_N).sum()),
                     "forced_window_excluded": fw is not None,
                     "max_kN": None if not ok.any() else float(excess[ok].max()) / 1e3,
                     "lower_source": lower_src["lower"],
                     "max_raw_minus_band_kN": None if not okc.any()
                     else float(cross[okc].max()) / 1e3,
                     "max_reading_lower_kN": None if not okr.any()
                     else float(reading[okr].max()) / 1e3,
                     "band_min_after_kN": float(np.nanmin(band_s[after])) / 1e3
                     if after.any() else None,
                     "note": "max_raw_minus_band = F_hat - F_band - F (control rev. 43 recheck "
                             "basis); max_reading_lower = F_lower_N - F (rev. 42 judge, no band)"}
    # F3 / F5 (band after the first probe)
    band = np.asarray(series["F_band_N"], float)
    ready_k = np.flatnonzero(phases == "ready")
    probe_k = np.flatnonzero(phases == "probe")
    if probe_k.size:
        k_end = probe_k[-1] if not ready_k.size else max(probe_k[probe_k < ready_k[0]],
                                                         default=probe_k[0])
        k_after = min(k_end + 1, band.size - 1)
        out["F3"] = {"F_band_kN": float(band[k_after]) / 1e3, "F_s_max_kN": float(fs.max()) / 1e3,
                     "excess_kN": float(band[k_after] - fs.max()) / 1e3}
    # F4
    out["F4"] = _find_key(case["result"].get("controller_meta") or {}, "air_seal_friction_N")
    # F9 at READY entry
    if ready_k.size:
        k = ready_k[0]
        out["F9"] = {"nF_true_kN": float(TWIST_N @ f_true[k]) / 1e3,
                     "nF_hat_kN": float(TWIST_N @ f_hat[k]) / 1e3,
                     "n_eps_kN": float(TWIST_N @ eps[k]) / 1e3}
    # F10
    u = np.asarray(series["issued_u"], float)
    low = lower_j < f_min + P5_MARGIN_N
    out["F10"] = int(np.sum(low & (u < 0.0) & after[:, None]))
    # item 9 classes and judgements
    labels, wmin = classify_windows(np.asarray(pads["t"], float) - t0,
                                    pads["F_cyl_min_interval"], tc, f_min, _rod_weight_N(params))
    labels[~after] = 0
    eps_list = episodes(labels)
    trans = [bool(out["rigid"] and lo is not None and tc[a] <= lo + LIFTOFF_WINDOW_S)
             for _leg, a, _b in eps_list]
    judges = {"J_P": (f_hat < f_min, (f_hat < f_min + P5_MARGIN_N) | (f_hat < f_min / 2)),
              "J_C": (lower < f_min, (lower < f_min + P5_MARGIN_N) | (lower < f_min / 2))}
    valid = after & ~boundary_mask(labels).any(axis=1)
    ev_free = np.ones(tc.size, bool) if ev_t is None else tc < float(ev_t)
    item9 = {}
    for name, (lvl, act) in judges.items():
        d = detection_metrics(eps_list, lvl & after[:, None], act & after[:, None], tc,
                              transient=trans)
        d["M2_false_actions"] = false_flags(act & after[:, None], wmin, tc, f_min,
                                            valid & ev_free & (phases == "ready"))
        est = f_hat if name == "J_P" else lower
        d["M4"] = near_fmin_errors(est[after], f_true[after], f_min)
        item9[name] = d
    item9["M5"] = {"min_true_kN": float(np.nanmin(wmin[after])) / 1e3 if after.any() else None,
                   "under_fmin_s": float(np.sum(labels == 1) * _period(tc)),
                   "lifted_s": float(np.sum(labels == 2) * _period(tc))}
    item9["fallback_note"] = ("level judgements on F_hat / F_lower only (no R-5, GE2, probe); "
                              "the P-S8-1 replay rows below supersede them when present")
    try:
        item9["replay"] = replay_item9(Path(case["dir"]), params, lo,
                                       float(t0), out["rigid"], engine=case_engine(case))
    except Exception as exc:  # noqa: BLE001 - recorded, the fallback values stay
        item9["replay"] = {"status": f"replay failed: {exc!r}"}
    out["item9"] = item9
    # F8: event-free READY windows
    events = _event_names(case)
    first_ready = tm.get("ready")
    if first_ready is not None:
        end_free = float(ev_t) if ev_t is not None else tm["end"]
        bad = [n for t, n in events if first_ready < t < end_free and n.split(":")[0] in (
            "relevel_predicted", "probe_aborted_low_load", "leg_reapproach_start")]
        exits = [t for t, p in case["result"]["phases"]
                 if first_ready < float(t) < end_free and p not in ("ready", "probe")]
        out["F8"] = {"events": bad, "ready_exits": len(exits), "window_s": [first_ready, end_free]}
    # F7
    if ev_t is not None and str(s8.get("event")) in ("RE1bF", "RE1bP"):
        ra = [t for t, n in events if n.split(":")[0] == "leg_reapproach_start" and t >= ev_t]
        out["F7"] = None if not ra else float(ra[0] - float(ev_t))
    # I4 (rev. 41 211.2, C-S8-10): observed classes of this run
    t_ev = i4_event_start(s8.get("event"), ev_t, tm)
    if t_ev is not None:
        out["i4"] = i4_classify(
            t_ev=t_ev, t_end=float(tm["end"]), tc=tc, labels=labels, episode_list=eps_list,
            transient=trans, level_flag=judges["J_P"][0] & after[:, None], t_pad=t_rel,
            f_judged=f_judged, f_min=f_min,
            reapproach_times=[t for t, n in events if n.split(":")[0] == "leg_reapproach_start"])
    if s8.get("event") == "G4" and t_ev is not None:  # C-S8-14 (rev. 42 212)
        band = np.asarray(series["leg_band_N"], float)
        if not np.isfinite(band).any():
            band = np.asarray(series["F_band_N"], float)
        out["g4_rr"] = g4_rr_summary(
            t_ev=t_ev, events=events, tc=tc, issued_u=np.asarray(series["issued_u"], float),
            band=band, t_pad=t_rel, f_judged=f_judged,
            controller_meta=case["result"].get("controller_meta"))
        # C-S8-19 ⑤ (spec rev. 44 214.5 question 3-3): scale at the event, round history, RR
        # lower bound at the re-approach start beside the 1.4 F_min threshold
        hist, src = twist_history(case, t0)
        cfg = str(case["result"]["settings"].get("controller_config") or "")
        pre = _config_float(cfg, "pre_probe_stiffness_scale", None)
        rev43 = (case["result"]["settings"].get("bundle_c") or {}).get("rev43_controller") or {}
        frac = rev43.get("reapproach_load_fraction_of_F_min") or REAPPROACH_FRACTION_DEFAULT
        g = out["g4_rr"]
        g["scale_at_event"] = scale_at(hist, t_ev, pre)
        g["scale_history"] = hist
        g["scale_history_source"] = src
        t_rea = g.get("reapproach_start_s")
        if t_rea is not None:
            k = int(np.clip(np.searchsorted(tc, t_rea - 1e-9), 0, tc.size - 1))
            g["rr_lower_at_reapproach_kN"] = float(lower[k, G4_SUMMARY_LEG]) / 1e3
            g["rr_lower_t_s"] = float(tc[k])
        g["reapproach_threshold_kN"] = float(frac) * f_min / 1e3
        g["note"] = ("twist_stiffness_scale = controller meta at the run end; scale_at_event = "
                     "scale in use at t_ev (last probe round before it); rr_lower_at_reapproach "
                     "= F_hat_cal - F_band of RR at the first leg_reapproach_start sample")
    # C-S8-19 ⑦: 213.6 rerun acceptance inputs
    out["r44"] = _r44_values(case, m, pads, t0, float(params.actuator.max_speed_m_s), events,
                             ev_t)
    return out


def _r44_values(case, m, pads, t0: float, v_max: float, events, ev_t) -> dict[str, Any]:
    tm = m["times_s"]
    phases = case["result"]["phases"]
    tl, te = first_phase_length(phases, "touch", tm["end"])
    out: dict[str, Any] = {"touch_len_s": tl, "touch_end_s": te, "ready_s": tm.get("ready"),
                           "d8_kN": m.get("min_cyl_excl_reanchor_kN"),
                           "reapproach": reapproach_outside_events(phases, tm["end"], events,
                                                                   ev_t)}
    p = Path(case["dir"]) / "r8_series.npz"
    if p.exists() and pads is not None:
        with np.load(p, allow_pickle=False) as r8:
            if "raw_u" in r8.files and "phase" in r8.files:
                key = "N_raw" if "N_raw" in pads else "N"
                out["touch_air"] = touch_air_commands(
                    np.asarray(r8["t"], float) - t0, r8["phase"], r8["raw_u"],
                    np.asarray(pads["t"], float) - t0, pads[key], v_max)
    return out


def replay_item9(case_dir: Path, params, liftoff_s: float | None, t0: float,
                 transient_rules: bool, engine: str | None = None) -> dict[str, Any]:
    """203.2 / 203.3 with python-expert's P-S8-1 modules (``contact_episode.build_episode``,
    ``control.contact_replay.replay_both`` in :attr:`WatchMode.CONTINUOUS`,
    ``verify.contact_metrics.score_judge``). Two scores per judge: all watched samples (gate,
    R40-5) and without the first :data:`LIFTOFF_WINDOW_S` after lift-off (``ex_transient``,
    shown apart when the R40 rules apply); plus the episode list with ``crawler_transient``."""
    from dataclasses import replace as dc_replace

    from outrigger_sim.contact_episode import MachineConstants, build_episode
    from outrigger_sim.control.c2 import C2Geometry
    from outrigger_sim.control.contact_replay import (
        Judge,
        WatchMode,
        record_judgement,
        replay_both,
    )
    from outrigger_sim.verify.contact_metrics import (
        ContactClass,
        contact_episodes,
        detect_episodes,
        score_judge,
    )

    from outrigger_sim.contact_episode import Episode

    machine = MachineConstants.from_geometry(C2Geometry.from_params(params))
    ep_raw = build_episode(case_dir, machine)
    t_rel = np.asarray(ep_raw["t_s"], float) - t0
    early = np.zeros(t_rel.size, bool)
    if liftoff_s is not None and transient_rules:
        early = (t_rel >= liftoff_s) & (t_rel <= liftoff_s + LIFTOFF_WINDOW_S)
    # C-S8-37 (spec rev. 52 232, U-S8-51): the default judgement reads + 0.5 kN where the pad
    # normal force is below 1.5 kN; the raw reading is a record, the F_s - m g ceiling of a
    # lifted leg a sensitivity
    pads_p = Path(case_dir) / "pads.npz"
    with np.load(pads_p, allow_pickle=False) as z:
        pads = {k: np.asarray(z[k]) for k in ("t", "N_raw", "N", "F_seal_limit") if k in z.files}
    # C-S8-40 (spec rev. 54 249): + delta_i only on L2b-NSC legs with F_s,i > 0
    variants = reading_variants(np.asarray(ep_raw["t_s"], float), pads,
                                np.asarray(ep_raw["lower_reading_N"], float),
                                np.asarray(ep_raw["net_force_N"], float),
                                np.asarray(machine.rod_weight_N, float), engine=engine)

    def run(arrs) -> dict[str, Any]:
        ep = ep_raw if arrs is None else Episode({**ep_raw.arrays, **arrs}, ep_raw.meta)
        reps = replay_both(ep, watch=WatchMode.CONTINUOUS)
        res: dict[str, Any] = {}
        for judge in (Judge.PRESSURE, Judge.COMBINED):
            rj = record_judgement(ep, reps[judge])
            score = score_judge([rj], machine.F_min_N).to_dict()
            # U-S8-17 (R42-3, spec rev. 44 214.5 question 3-2): episodes are built on the full
            # watched samples; an episode counts when its t_on is outside the lift-off window
            # (``scored``); the sample metrics (M2, M4) use the scored samples only
            score_ex = score_ex_transient(rj, early, machine.F_min_N, dc_replace, score_judge)
            classes = np.where(rj.watched[:, None], rj.classes, ContactClass.UNKNOWN)
            dets = detect_episodes(rj.t_s, contact_episodes(classes), rj.decision_flags,
                                   rj.action_flags)
            eps = [{"leg": LEGS[d.episode.leg], "t_on_s": float(t_rel[d.episode.on_row]),
                    "t_off_s": float(t_rel[d.episode.off_row]), "is_lift": d.episode.is_lift,
                    "first_decision_s": None if d.first_decision_s is None
                    else d.first_decision_s - t0,
                    "action_delay_s": d.action_delay_s,
                    "sampling_only": d.first_decision_s is None
                    and d.action_delay_s is not None and d.action_delay_s <= TAU_D_S,
                    "crawler_transient": bool(early[d.episode.on_row])} for d in dets]
            res[judge.value] = {"score": score, "score_ex_transient": score_ex, "episodes": eps,
                                "events": [{"t_s": e.t_s - t0, "leg": LEGS[e.leg],
                                            "kind": str(e.kind)}
                                           for e in reps[judge].events][:200]}
        return res

    out: dict[str, Any] = {"status": "P-S8-1 replay (continuous watch)",
                           "transient_window_rows": int(early.sum()),
                           "reading": "corrected" if variants["corrected"] is not None
                           else "raw (no pad normal record)",
                           "reading_rule": READING_BIAS_RULE,
                           "reading_stats": variants["stats"],
                           "engine": engine, "reading_delta_N": variants["stats"]["delta_N"]}
    corr, allp = variants["corrected"], variants.get("all_apply")
    delta = np.asarray(list(variants["stats"]["delta_N"].values()), float)
    raw = run(None)  # record rows
    # default judgement (top-level J_P / J_C keys, read by every row): corrected reading; with
    # every delta_i = 0 it equals the raw reading (same replay, not run twice)
    out.update(raw if corr is None or not (delta > 0.0).any() else run(corr))
    out["raw"] = raw
    out["upper_sensitivity"] = None if variants["upper"] is None else run(variants["upper"])
    # C-S8-40: rev. 52 all-apply (+0.5 kN regardless of engine / F_s) as sensitivity rows
    same = corr is not None and allp is not None and all(
        np.array_equal(corr[k], allp[k]) for k in allp)
    out["all_apply"] = None if allp is None else (
        {k: out[k] for k in ("J_P", "J_C") if k in out} if same else run(allp))
    return out


READING_BIAS_ADD_N = 500.0
"""Spec rev. 52 232 (U-S8-51, dynamics 5.29.2 / 5.29.9): the L2b-NSC + seal friction reading of
a leg whose pad normal force is below :data:`READING_BIAS_BELOW_N` reads 0.43-0.49 kN low (NSC
contact chatter ratchets the seal into the band, independent of F_s); the judgement adds this."""
READING_BIAS_BELOW_N = 1500.0
READING_BIAS_ENGINE = "L2b_NSC"
"""C-S8-40 (spec rev. 54 249): the ratchet needs NSC contact chatter (L2b-NSC) and a seal
element (F_s,i > 0); elsewhere the default correction is 0."""
READING_BIAS_RULE = ("C-S8-40 / spec rev. 54 249 (C-S8-37 / rev. 52 232 corrected): default = "
                     "corrected reading lower_reading + delta_i (and net_force + delta_i) on the "
                     "10 Hz samples whose pad normal force (pads N_raw, 1 ms record, linear "
                     "interpolation at the sample time) is < 1.5 kN, delta_i = min(0.5 kN, "
                     "2 F_s,i), F_s,i = median of pads F_seal_limit[:, i], only for engine "
                     "L2b_NSC (settings.s8.engine), else 0; 'raw' = the reading as recorded "
                     "(record rows); 'upper_sensitivity' = lifted samples (N <= 0) read at least "
                     "F_seal_limit,i - m_i g (sensitivity rows); 'all_apply' = + 0.5 kN where "
                     "N < 1.5 kN regardless of engine / F_s (rev. 52 rule, sensitivity rows)")


def reading_bias_delta_N(pads: Mapping[str, Any], engine: str | None) -> np.ndarray:
    """C-S8-40 (spec rev. 54 249): per-leg reading correction ``delta_i = min(500, 2 F_s,i)`` N,
    ``F_s,i`` = median of ``pads.F_seal_limit[:, i]``; zeros for another engine than
    :data:`READING_BIAS_ENGINE` or without the seal record."""
    if engine != READING_BIAS_ENGINE or "F_seal_limit" not in pads:
        return np.zeros(len(LEGS))
    fs = np.median(np.asarray(pads["F_seal_limit"], float), axis=0)
    return np.where(fs > 0.0, np.minimum(READING_BIAS_ADD_N, 2.0 * fs), 0.0)


def pad_normal_at(t_s: np.ndarray, pads: Mapping[str, Any]) -> tuple[np.ndarray | None, str]:
    """Pad normal force [N] per leg at the times ``t_s`` (linear interpolation of the 1 ms
    record ``N_raw``, else ``N``); (None, reason) without a pad normal record."""
    key = "N_raw" if "N_raw" in pads else ("N" if "N" in pads else None)
    if key is None or "t" not in pads:
        return None, "no pad normal record"
    tp = np.asarray(pads["t"], float)
    n = np.asarray(pads[key], float)
    t = np.asarray(t_s, float)
    return np.column_stack([np.interp(t, tp, n[:, i]) for i in range(n.shape[1])]), key


def reading_variants(t_s: np.ndarray, pads: Mapping[str, Any], lower_N: np.ndarray,
                     net_N: np.ndarray, rod_weight_N: np.ndarray,
                     engine: str | None = None) -> dict[str, Any]:
    """C-S8-37 / C-S8-40 reading variants of one run (spec rev. 54 249): ``corrected`` (pad N <
    1.5 kN: + ``delta_i``, :func:`reading_bias_delta_N` of ``engine``), ``all_apply`` (pad N <
    1.5 kN: + 0.5 kN, the rev. 52 rule, sensitivity) and ``upper`` (pad N <= 0: at least
    ``F_seal_limit,i - m_i g``), each as the replacement arrays ``lower_reading_N`` /
    ``net_force_N`` of the episode; ``stats``: corrected sample counts per leg, ``delta_N`` per
    leg and the engine. ``corrected`` / ``all_apply`` / ``upper`` None without a pad normal
    record."""
    n10, key = pad_normal_at(t_s, pads)
    delta = reading_bias_delta_N(pads, engine)
    if n10 is None:
        return {"corrected": None, "upper": None, "all_apply": None,
                "stats": {"source": key, "engine": engine,
                          "delta_N": {LEGS[i]: float(delta[i]) for i in range(len(LEGS))}}}
    low = n10 < READING_BIAS_BELOW_N
    add = np.where(low, delta[None, :], 0.0)
    corrected = {"lower_reading_N": lower_N + add, "net_force_N": net_N + add}
    add_all = np.where(low, READING_BIAS_ADD_N, 0.0)
    all_apply = {"lower_reading_N": lower_N + add_all, "net_force_N": net_N + add_all}
    upper = None
    if "F_seal_limit" in pads:
        tp = np.asarray(pads["t"], float)
        fs = np.asarray(pads["F_seal_limit"], float)
        fs10 = np.column_stack([np.interp(np.asarray(t_s, float), tp, fs[:, i])
                                for i in range(fs.shape[1])])
        ceil = fs10 - np.asarray(rod_weight_N, float)[None, :]
        lifted = ~(n10 > 0.0)
        upper = {"lower_reading_N": np.where(lifted, np.maximum(lower_N, ceil), lower_N),
                 "net_force_N": np.where(lifted, np.maximum(net_N, ceil), net_N)}
    stats = {"source": key, "samples": int(low.shape[0]), "engine": engine,
             "delta_N": {LEGS[i]: float(delta[i]) for i in range(low.shape[1])},
             "corrected_per_leg": {LEGS[i]: int((low[:, i] & (delta[i] > 0.0)).sum())
                                   for i in range(low.shape[1])},
             "below_1p5kN_per_leg": {LEGS[i]: int(low[:, i].sum())
                                     for i in range(low.shape[1])},
             "lifted_per_leg": {LEGS[i]: int((~(n10[:, i] > 0.0)).sum())
                                for i in range(n10.shape[1])}}
    return {"corrected": corrected, "upper": upper, "all_apply": all_apply, "stats": stats}


def score_ex_transient(rj, early: np.ndarray, f_min_N: float, replace_fn, score_fn
                       ) -> dict[str, Any]:
    """U-S8-17 / R42-3: the ``ex_transient`` score of one record judgement ``rj``
    (``contact_metrics.RecordJudgement``): ``scored = ~early`` (episodes still found on all
    watched samples and counted only when ``t_on`` is scored; M2 / M4 on scored samples)."""
    rj_ex = replace_fn(rj, scored=~np.asarray(early, bool))
    out = score_fn([rj_ex], f_min_N).to_dict()
    out["rule"] = ("R42-3: episodes on all watched samples, crawler_transient (t_on in the "
                   "lift-off window) left out; M2 / M4 on the samples outside the window")
    return out


def _period(tc) -> float:
    return float(np.median(np.diff(tc))) if np.size(tc) > 1 else 0.1


def _windows(case, phase: str, end_s: float) -> list[tuple[float, float]]:
    ph = [(float(t), p) for t, p in case["result"]["phases"]]
    out = []
    for i, (t, p) in enumerate(ph):
        if p == phase:
            out.append((t, ph[i + 1][0] if i + 1 < len(ph) else end_s))
    return out


def _event_names(case) -> list[tuple[float, str]]:
    t0 = float(case["result"]["settings"]["start_t_s"])
    out = []
    for e in case.get("events") or []:
        s = str(e)
        try:
            t = float(s.split("t_s=")[1].split(",")[0])
            name = s.split("name='")[1].rstrip("')")
        except (IndexError, ValueError):
            continue
        out.append((t - t0, name))
    return out


def _find_key(tree: Any, key: str) -> Any:
    if isinstance(tree, Mapping):
        if key in tree:
            return tree[key]
        for v in tree.values():
            r = _find_key(v, key)
            if r is not None:
                return r
    elif isinstance(tree, list):
        for v in tree:
            r = _find_key(v, key)
            if r is not None:
                return r
    return None


def _pair_window_values(case, m, pads, t_rel) -> dict[str, Any]:
    """R40-3 / R40-4 values of one run (compared with its twin by :func:`pair_rows_s8`)."""
    tm = m["times_s"]
    lo, ready = tm.get("liftoff"), tm.get("ready")
    out: dict[str, Any] = {"t_ready_minus_touch_s": m.get("t_ready_minus_touch_s"),
                           "min_cyl_reanchor_kN": m.get("min_cyl_reanchor_kN")}
    if lo is None:
        return out
    f = judged_force_min(pads)  # S8-A2
    dt = float(np.median(np.diff(t_rel)))
    slow = centred_mean(f, int(round(SLOW_WINDOW_S / dt)) | 1)
    after = t_rel >= lo
    out["min_raw_after_liftoff_kN"] = float(f[after].min()) / 1e3
    out["min_slow_after_liftoff_kN"] = float(slow[after].min()) / 1e3
    for a, b in OSC_WINDOWS_S:
        w = (t_rel >= lo + a) & (t_rel <= lo + b)
        if w.any():
            osc = f[w] - slow[w]
            out[f"osc_half_amp_{a:g}_{b:g}_kN"] = ((osc.max(0) - osc.min(0)) / 2e3).tolist()
    if ready is not None:
        w = (t_rel >= lo + LIFTOFF_WINDOW_S) & (t_rel <= ready)
        if w.any():
            out["min_late8_to_ready_kN"] = float(f[w].min()) / 1e3
        k = np.searchsorted(t_rel, ready)
        if k < len(t_rel):
            out["nF_true_ready_kN"] = float(TWIST_N @ np.asarray(pads["F_cyl"])[k]) / 1e3
    return out


# --- rows ------------------------------------------------------------------------------------------


def _fmt(v: float | None, spec: str = "+.3f") -> str:
    return "-" if v is None else format(float(v), spec)


def _is_noisy(sm: Mapping[str, Any]) -> bool:
    law = sm.get("F1_law") or {}
    return any(float(s) > 0.0 for s in law.get("sigma_F_N") or [])


F1_LAW_ITEM = "F1 reading law max |F_hat - (F - f + E_s)| <= 6 sigma_F + 0.1 kN (R45-1, U-S8-18)"
F1_STATS_ITEM = ("F1 reading law per leg: |mean r| <= 0.1 kN, std r / sigma_F in [0.85, 1.15] "
                 "(R45-1 ②, U-S8-18)")
F1_FALLBACK_ITEM = ("F1 fallback (b): |F_hat_cal - F| <= F_s,leg + 1.3 kN + 0.025 |F| (law terms "
                    "missing, U-S8-18)")
F2_FORCED_ITEM = "F2 in forced (open-loop) window (record, C-S8-22 ③, U-S8-24)"


def f1_law_rows(cid: str, law: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """R45-1 judged rows of one case: the max row and (noisy sensor) the statistics row, or the
    marked fallback (b) row when the record lacks the law terms."""
    if not law:
        return []
    if not law.get("available"):
        fb = law.get("fallback") or {}
        v = fb.get("violations")
        return [_row(F1_FALLBACK_ITEM, cid, v, 0, None if v is None else v == 0,
                     f"fallback (b): {law.get('note')}; {fb.get('rule')}; max excess "
                     f"{_fmt(fb.get('max_excess_kN'))} kN over {fb.get('n_samples')} leg samples",
                     fallback="b")]
    lm = law["metrics"]
    per = [f"{LEGS[j]} {_fmt(None if m is None else m / 1e3, '.3f')}/"
           f"{lm['limit_N'][j] / 1e3:.3f} kN"
           + ("" if lm["t_s"][j] is None else f" @ {lm['t_s'][j]:.1f} s {lm['phase'][j]}")
           for j, m in enumerate(lm["max_abs_N"])]
    rows = [_row(F1_LAW_ITEM, cid, lm["violations"], [x / 1e3 for x in lm["limit_N"]],
                 lm["violations"] == 0,
                 f"max |r| / limit per leg: {'; '.join(per)}; samples {lm['n']}; grade "
                 f"{law.get('grade')}, terms {law.get('has_terms')}; areas "
                 f"{law['areas_m2']['source']}; F - f vs F_pressure "
                 f"{_fmt(law.get('check_F_minus_f_vs_F_pressure_N'), '.2e')} N",
                 max_abs_kN=[None if m is None else m / 1e3 for m in lm["max_abs_N"]],
                 sigma_F_N=lm["sigma_F_N"])]
    if lm["stats_passed"] is not None:
        val = {"mean_kN": [None if x is None else x / 1e3 for x in lm["mean_N"]],
               "std_ratio": lm["std_ratio"]}
        rows.append(_row(F1_STATS_ITEM, cid, val,
                         {"mean_kN": F1_LAW_MEAN_N / 1e3, "std_ratio": list(F1_LAW_STD_RATIO)},
                         lm["stats_passed"],
                         "per leg mean [N] " + str([_fmt(x, '+.1f') for x in lm["mean_N"]])
                         + ", std [N] " + str([_fmt(x, '.1f') for x in lm["std_N"]])
                         + f" vs sigma_F {[round(s, 1) for s in lm['sigma_F_N']]} N",
                         std_N=lm["std_N"]))
    return rows


def r45_2_rows(cid: str, sp: Mapping[str, Any], split: Sequence[Mapping[str, Any] | None] | None
               ) -> list[dict[str, Any]]:
    """R45-2 (spec rev. 45 215.3) record rows of a WIKA run: static part, calibration friction,
    noise and total of the calibrated residual near F_min (-5 .. +10 kN, outside CHECK)."""
    legs = sp["legs"]
    lim = sp["limits_kN"]
    rebuild = [None if s is None else round(s["c_rebuild_error_N"], 1) for s in (split or [])]
    out = [
        _row("R45-2 near F_min: static part max |E_s - c_sens| (record, flag 0.65 kN)", cid,
             sp["static_max_kN"], lim["static"], None,
             f"{sp['n']} leg samples; per leg {[_fmt(x['static_max_kN']) for x in legs]} kN"
             + (" FLAG" if sp["static_flag"] else ""), kind="record", flag=sp["static_flag"]),
        _row("R45-2 calibration friction c_fric = c_i - c_sens - c_noise per leg [kN] (+ = reads "
             "low; record, flag R46-1 0.1 kN at F_s,leg 0 / 0.75 kN at F_s,leg > 0)", cid,
             [x["c_fric_kN"] for x in legs], lim["friction"], None,
             f"flags {[x.get('fric_flag') for x in legs]}; c_i - c_rebuilt [N] {rebuild}"
             + (" FLAG" if sp["fric_flag"] else ""), kind="record", flag=sp["fric_flag"],
             split=list(split or [])),
        _row("R45-2 near F_min: noise std r / sigma_F and max |r - c_noise| / sigma_F per leg "
             "(record; R45-1 ② judges)", cid,
             {"std_ratio": [x["noise_std_ratio"] for x in legs],
              "max_sigma": [x["noise_max_sigma"] for x in legs]}, None, None,
             f"{sp['n']} leg samples", kind="record"),
        _row("R45-2 near F_min: total max |F_hat_cal - F + f| (record, flag 1.6 kN)", cid,
             sp["total_max_kN"], lim["total"], None,
             f"per leg {[_fmt(x['total_max_kN']) for x in legs]} kN"
             + (" FLAG" if sp["total_flag"] else ""), kind="record", flag=sp["total_flag"]),
    ]
    return out


def case_rows(sm: Mapping[str, Any], m: Mapping[str, Any]) -> list[dict[str, Any]]:
    cid = sm["case"]
    s8 = sm["s8"]
    f_min = sm["F_min_N"]
    cond = s8.get("condition", "judged")
    rows = [c1_row(cid, sm.get("c1") or {}, (f_min + D8_MARGIN_N) / 1e3, rigid=sm["rigid"],
                   condition=cond)]
    rmin = m.get("min_cyl_reanchor_kN")
    if rmin is not None:
        lim = (f_min + D8_MARGIN_N + REANCHOR_EXTRA_N) / 1e3
        p = rmin >= lim
        rows.append(_row("C2 REANCHOR min >= F_min + 7 kN", cid, rmin, lim,
                         None if cond == "sensitivity" else p,
                         "" if cond != "sensitivity" else "sensitivity: reported",
                         kind="judged" if cond != "sensitivity" else "report"))
    rows.extend(f1_law_rows(cid, sm.get("F1_law")))
    f1 = sm.get("F1")
    if f1 is not None:
        mx = f1["max_excess_kN"]
        rows.append(_row("F1 rev. 44 rule: reading error <= F_s,leg + sensor share (R43-1 / "
                         "U-S8-15; record, replaced by R45-1)", cid, f1["violations"], 0, None,
                         f"max excess {'-' if mx is None else f'{mx:+.3f}'} kN over "
                         f"{f1['n_samples']} leg samples; {f1['rule']}; reading {f1['reading']}",
                         kind="record", passed_rev44=f1["violations"] == 0))
        raw, cal = f1["raw"], f1["calibrated"]
        rows.append(_row("F1 raw reading |F_hat - F| <= F_s,leg + constant share (record)", cid,
                         raw["violations"], 0, None,
                         f"max excess {raw['max_excess_kN']:+.3f} kN (share "
                         f"{raw['share_kN']:g} kN); {raw['note']}; by phase {raw['by_phase']}",
                         kind="record"))
        rows.append(_row("F1 calibrated reading |F_hat_cal - F| <= F_s,leg + R43-1 share "
                         "(record; zero-calibration offset c_i per leg [kN])", cid,
                         cal["violations"], 0, None,
                         f"max excess {cal['max_excess_kN']} kN; c_i = F_hat - F_hat_cal "
                         f"{cal['offset_kN_per_leg']}"
                         + ("" if not cal.get("fault_exclusion") else
                            f"; excluded {cal['fault_leg_samples_excluded']} leg samples: "
                            f"{cal['fault_exclusion']}"), kind="record",
                         offset_kN=cal["offset_kN_per_leg"],
                         fault_leg_samples_excluded=cal.get("fault_leg_samples_excluded", 0)))
    nf = sm.get("F1_near_fmin")
    wika_split = sm.get("R45_2") is not None and _is_noisy(sm)
    if wika_split:
        rows.extend(r45_2_rows(cid, sm["R45_2"], sm.get("calibration_split")))
    elif nf is not None:
        v = nf["max_abs_kN"]
        lim = nf.get("per_leg_limit_kN") or [nf["limit_kN"]] * 4
        flag = nf.get("flag")
        if flag is None and v is not None:
            flag = bool(v > nf["limit_kN"])
        rows.append(_row("F1 near F_min (-5 .. +10 kN): |F_hat_cal - F + f| (sensor share, "
                         "record)", cid, v, lim, None,
                         f"{nf['n']} leg samples; per leg {nf['per_leg_max_abs_kN']} vs "
                         f"{lim} kN ({nf.get('limit_rule', '')}); above the limit -> D-S8-6"
                         + (" FLAG" if flag else ""), kind="record", flag=flag))
    sp = sm.get("probe_7c_split")
    if sp is not None:
        w = sp["worst_7c"]
        rows.append(_row(SPLIT_EST_ITEM, cid, sp["est_bias"]["value_kN"], None, None,
                         f"largest |E - T2| at {sp['est_bias']['leg']} round "
                         f"{sp['est_bias']['round']}; max signed {sp['est_bias_max_kN']:+.2f} kN; "
                         f"worst 7c row {w['leg']} r{w['round']}: E - T0 {w['err_kN']:+.2f} = "
                         f"{w['est_bias_kN']:+.2f} + {w['hyst_kN']:+.2f} kN",
                         kind="record", split_rows=sp["rows"], worst_7c=w))
        rows.append(_row(SPLIT_HYST_ITEM, cid, sp["hyst"]["value_kN"], None, None,
                         f"largest |T2 - T0| at {sp['hyst']['leg']} round {sp['hyst']['round']} "
                         "(load the probe moved and did not give back; not an estimator error, "
                         "spec rev. 44 214.4 ②)", kind="record"))
    fa = sm.get("F1_air")
    if fa is not None:
        v = fa["max_abs_kN"]
        spl = fa.get("split")
        parts = ""
        if spl is not None:
            parts = (f"; parts: static max {_fmt(spl['static_max_kN'])} kN, calibration friction "
                     f"c_fric {[_fmt(x['c_fric_kN']) for x in spl['legs']]} kN, noise max "
                     f"{_fmt(spl['noise_max_sigma'], '.2f')} sigma")
        rows.append(_row("F1 airborne residual |F_hat_cal - F + f| (F < 0.5 kN, no contact; "
                         "record, flag 1.7 kN, R45-3 / U-S8-19)", cid, v, fa["limit_kN"], None,
                         f"{fa['n']} leg samples outside CHECK; worst {fa['leg']} in "
                         f"{fa['phase']}; per leg {fa['per_leg_max_abs_kN']}{parts}"
                         + (" FLAG" if fa["flag"] else ""), kind="record", flag=fa["flag"],
                         split=spl))
    if "R45_4" in sm:
        recs = sm["R45_4"]
        worst = min((x for x in recs if x["F2_margin_min_kN"] is not None),
                    key=lambda x: x["F2_margin_min_kN"], default=None)
        rows.append(_row("R45-4 low-load probe: F2 margin / true margin / T2 - T0 / E - T2 over "
                         "2 s after the second hold (lower bound < F_min + 15 kN at the round "
                         "start; record, U-S8-19)", cid, len(recs), None, None,
                         "no probe below F_min + 15 kN at the round start" if not recs else
                         f"worst F2 margin {worst['leg'] if worst else '-'} r"
                         f"{worst['round'] if worst else '-'}: "
                         f"{_fmt(worst['F2_margin_min_kN'] if worst else None)} kN, true "
                         f"{_fmt(worst['true_margin_min_kN'] if worst else None)} kN, E - T2 "
                         f"{_fmt(worst['E_minus_T2_kN'] if worst else None)} kN, re-ground "
                         f"{(worst or {}).get('reground')}", kind="record", probes=recs))
    f2 = sm.get("F2")
    f2f = sm.get("F2_forced")
    if f2f is not None:
        rows.append(_row(F2_FORCED_ITEM, cid, f2f["violations"], 0, None,
                         f"forced window {f2f['window_s']} s (retract done {f2f['done_s']} s), "
                         f"{f2f['samples']} leg samples, max F_lower - F {f2f['max_kN']} kN; "
                         "ForcedRetract holds the other legs at 0, the controller's D2 / fallback "
                         "state is open loop (spec rev. 46 216.3, U-S8-24)", kind="record",
                         max_kN=f2f["max_kN"]))
    fb = sm.get("rod_fallback") or {}
    inside = [e for e in fb.get("events") or [] if e["in_forced_window"]]
    if inside:
        rows.append(_row("C-S8-22 ④ rod-pressure fallback in the forced (open-loop) window "
                         "(record, U-S8-24)", cid, len(inside), None, None,
                         "; ".join(f"{e['leg']} {e['t_s']:.2f} s {e['reason']}" for e in inside),
                         kind="record", events=inside))
    f2x = sm.get("F2_faulty_leg_after_injection")
    if f2 is not None:
        rows.append(_row("F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share "
                         "(after lift-off)", cid, f2["violations"], 0, f2["violations"] == 0,
                         ("forced window excluded (C-S8-22 ③); " if f2.get(
                             "forced_window_excluded") else "")
                         + ("" if f2x is None else f"head-fault leg {f2x['leg']} excluded from "
                            f"{f2x['from_s']:.3f} s (C-S8-70 ④); ")
                         + f"max {f2['max_kN']} kN; source {f2['lower_source']}; cross-check "
                         f"F_hat - F_band - F max {f2['max_raw_minus_band_kN']} kN; rev. 42 "
                         f"reading lower (no band) max {f2['max_reading_lower_kN']} kN",
                         max_kN=f2["max_kN"],
                         max_raw_minus_band_kN=f2["max_raw_minus_band_kN"]))
    if f2x is not None:
        rows.append(_row("F2 head-fault leg after the injection arm time (record, C-S8-70 ④, "
                         "F2_faulty_leg_after_injection)", cid, f2x["violations"], None, None,
                         f"leg {f2x['leg']} from {f2x['from_s']:.3f} s: {f2x['samples']} "
                         f"samples, max F_lower - F {f2x['max_kN']} kN (injected +jump in the "
                         "reading)", kind="record", max_kN=f2x["max_kN"]))
    f3 = sm.get("F3")
    if f3 is not None:
        rows.append(_row("F3 F_band >= F_s after the first probe", cid, f3["F_band_kN"],
                         f3["F_s_max_kN"], f3["excess_kN"] >= 0.0,
                         f"F_band - F_s {f3['excess_kN']:+.2f} kN (record)"))
    rows.append(_row("F4 CHECK air seal friction F_s,air (record)", cid, sm.get("F4"),
                     sm.get("fs_leg_N"), None, "per leg [N] vs F_s,leg [N]", kind="record"))
    air = sm.get("air")
    if air is not None:
        rows.append(_row("S8-A2 airborne F + m g: 1 ms min / 20 ms mean range per leg [kN] "
                         "(record; not judged on the 1 ms minimum)", cid,
                         {"min_1ms": air["min_1ms_kN"], "mean20_min": air["mean20_min_kN"],
                          "mean20_max": air["mean20_max_kN"]}, None, None,
                         f"airborne samples {air['samples']} (20 ms pad normal <= 0); 20 ms mean "
                         "expected within +-0.3 kN", kind="record"))
    ch = sm.get("chatter") or {}
    if ch.get("band_edge_chatter") is not None or ch.get("pressure_floor") is not None:
        rows.append(_row("S8-A3 seal band-edge chatter (stick <-> slip round trip < 1 ms) per "
                         "leg / S8-A1 head-floor hits (record)", cid,
                         ch.get("band_edge_chatter"), None, None,
                         f"slip starts {ch.get('slip_starts')}; head floor hook steps "
                         f"{(ch.get('pressure_floor') or {}).get('hook_hit_steps')}, "
                         f"measurements {ch.get('pressure_floor_measurements')}",
                         kind="record"))
    if "F7" in sm:
        combined = (m.get("contact") or "combined") != "pressure"
        v = sm["F7"]
        rows.append(_row("F7 first re-approach after the RE1b event <= 0.3 s", cid, v,
                         F7_LIMIT_S, (v is not None and v <= F7_LIMIT_S) if combined else None,
                         "" if combined else "pressure-only: record (199 (3))",
                         kind="judged" if combined else "record"))
    f8 = sm.get("F8")
    if f8 is not None:
        n = len(f8["events"]) + f8["ready_exits"]
        rows.append(_row("F8 no false re-level in event-free READY", cid, n, 0, n == 0,
                         f"events {f8['events'][:6]}, READY exits {f8['ready_exits']}"))
    if "F9" in sm:
        rows.append(_row("F9 twist at READY entry n^T F / n^T F_hat / n^T eps [kN] (record)",
                         cid, [sm["F9"][k] for k in ("nF_true_kN", "nF_hat_kN", "n_eps_kN")],
                         None, None, kind="record"))
    if "F10" in sm:
        rows.append(_row("F10 retract commands on low-load legs (periods, record)", cid,
                         sm["F10"], None, None, kind="record"))
    i9 = sm.get("item9")
    if i9:
        for name in ("J_P", "J_C"):
            d = judge_score(sm, name)
            rows.append(_row(f"item 9 {name} M1 missed / M1' late / M3 median / M2 / M4 max "
                             "(record)", cid,
                             [d["M1_missed"], d["M1p_late"], d["M3_median_s"], d["M2"],
                              d["M4_max_kN"]], None, None,
                             f"episodes {d['n']} (crawler_transient {d['transient']}), "
                             f"upper95 {d['M1_upper95']}; ex-transient {d['ex_transient']}; "
                             f"source {d['source']}", kind="record", judge=name))
        # C-S8-37 (spec rev. 52 232): the rows above use the corrected reading; raw reading
        # (record) and the F_s - m g ceiling (sensitivity) beside them
        for variant, label, kind in (("raw", "raw reading (record)", "record"),
                                     ("upper_sensitivity", "F_s - m g ceiling on lifted legs "
                                      "(sensitivity)", "sensitivity"),
                                     ("all_apply", "all-apply +0.5 kN reading (rev. 52 rule, "
                                      "sensitivity)", "sensitivity")):
            if not ((i9.get("replay") or {}).get(variant)):
                continue
            for name in ("J_P", "J_C"):
                d = judge_score(sm, name, variant=variant)
                rows.append(_row(f"item 9 {name} {label}: M1 missed / M1' late / M3 median / "
                                 "M2 / M4 max", cid,
                                 [d["M1_missed"], d["M1p_late"], d["M3_median_s"], d["M2"],
                                  d["M4_max_kN"]], None, None,
                                 f"episodes {d['n']}; ex-transient {d['ex_transient']}",
                                 kind=kind, judge=name, reading=variant))
        rows.append(_row("item 9 M5 closed loop: min true / under F_min [s] / lifted [s]", cid,
                         [i9["M5"]["min_true_kN"], i9["M5"]["under_fmin_s"],
                          i9["M5"]["lifted_s"]], None, None, kind="record"))
    return rows


def judge_score(sm: Mapping[str, Any], name: str, variant: str | None = None
                ) -> dict[str, Any]:
    """M1 / M1' / M2 / M3 / M4 of judge ``name`` on one case: the P-S8-1 replay when it ran,
    else this module's level-only fallback. ``variant`` (C-S8-37): None = the default
    judgement (corrected reading since rev. 52 232), ``raw`` / ``upper_sensitivity`` = the
    replay of that reading variant."""
    i9 = sm["item9"]
    rep = i9.get("replay") or {}
    if variant is not None:
        rep = rep.get(variant) or {}
    if name in rep:
        s, sx = rep[name]["score"], rep[name]["score_ex_transient"]
        return {"source": "P-S8-1 replay", "n": s["episodes"], "M1_missed": s["M1_missed"],
                "M1_upper95": s["M1_missed_upper_95"], "M1p_late": s["M1p_late"],
                "M2": s["M2_false_action_flags"], "M3_median_s": s["M3_median_delay_s"],
                "M4_max_kN": None if s["M4_max_N"] is None else s["M4_max_N"] / 1e3,
                "transient": sum(e["crawler_transient"] for e in rep[name]["episodes"]),
                "ex_transient": {"n": sx["episodes"], "M1_missed": sx["M1_missed"],
                                 "M1p_late": sx["M1p_late"]}}
    d = i9[name]
    return {"source": "fallback (level only)", "n": d["n"], "M1_missed": d["M1_missed"],
            "M1_upper95": d["M1_upper95"], "M1p_late": d["M1p_late"],
            "M2": d["M2_false_actions"], "M3_median_s": d["M3_median_s"],
            "M4_max_kN": d["M4"]["max_kN"], "transient": d["transient_episodes"],
            "ex_transient": None}


def pair_rows_s8(sm: Mapping[str, Any], twin: Mapping[str, Any] | None, *, source: str,
                 kind_pair: str) -> list[dict[str, Any]]:
    """C10 / F6 / F9 (F_s twin, ``kind_pair`` "fs0") or C11 (L1 twin, "l1"), R40-3 / R40-4."""
    cid = sm["case"]
    a = sm.get("pair_window") or {}
    b = (twin or {}).get("pair_window") or {}
    out = []

    def diff(key):
        va, vb = a.get(key), b.get(key)
        return None if va is None or vb is None else float(va) - float(vb)

    def add(item, key, flag=None, unit_note=""):
        d = diff(key)
        row = _row(item, cid, d, None if flag is None else f"|diff| <= {flag:g} (flag only)",
                   None, f"this {a.get(key)}, twin {b.get(key)} ({source}){unit_note}",
                   kind="pair")
        if flag is not None and d is not None:
            row["pair_flag"] = bool(abs(d) > flag)
        out.append(row)

    if kind_pair == "l1":
        add("C11 L2b - L1: min slow (1 s) after lift-off [kN]", "min_slow_after_liftoff_kN",
            PAIR_FLAG_N / 1e3)
        add("C11 L2b - L1: min raw after lift-off [kN]", "min_raw_after_liftoff_kN")
        add("C11 L2b - L1: min lift-off + 8 s .. READY [kN]", "min_late8_to_ready_kN")
        for lo_hi in OSC_WINDOWS_S:
            key = f"osc_half_amp_{lo_hi[0]:g}_{lo_hi[1]:g}_kN"
            va, vb = a.get(key), b.get(key)
            for j, leg in enumerate(LEGS):
                d = None if va is None or vb is None else va[j] - vb[j]
                out.append(_row(f"C11 L2b - L1: half-amplitude {lo_hi[0]:g}-{lo_hi[1]:g} s, "
                                f"{leg} [kN]", cid, d, None, None,
                                f"this {None if va is None else va[j]}, twin "
                                f"{None if vb is None else vb[j]}; ratio "
                                f"{(va[j] / vb[j]) if va and vb and vb[j] else None}",
                                kind="pair"))
    else:
        d = diff("t_ready_minus_touch_s")
        r = _row("C10 READY - TOUCH end vs F_s 0 [s]", cid, d, f"+{C10_FLAG_S:g} s report",
                 None, f"({source})", kind="pair")
        if d is not None:
            r["report_cause"] = bool(d > C10_FLAG_S)
        out.append(r)
        add("F6 REANCHOR min vs F_s 0 [kN]", "min_cyl_reanchor_kN")
        d = diff("nF_true_ready_kN")
        r = _row("F9 |n^T F| at READY vs F_s 0 [kN]", cid, d, f"+{F9_FLAG_N / 1e3:g} kN report",
                 None, f"({source})", kind="pair")
        if d is not None:
            r["report_cause"] = abs(a.get("nF_true_ready_kN")) - abs(b.get("nF_true_ready_kN")) \
                > F9_FLAG_N / 1e3
        out.append(r)
        add("D8 min lift-off + 8 s .. READY vs F_s 0 [kN] (R40-4)", "min_late8_to_ready_kN")
    if twin is not None and sm.get("crawler_contact") != twin.get("crawler_contact"):
        if kind_pair == "fs0":
            # R41-4 (C-S8-12): a crawler-model difference cannot be told from the F_s share
            for r in out:
                r["passed"] = None
                if "report_cause" in r:
                    r["report_cause"] = None
                if "pair_flag" in r:
                    r["pair_flag"] = None
                r["note"] += "; crawler model differs: not attributable to F_s (R41-4)"
        else:
            for r in out:
                r["note"] += "; crawler contact differs from the twin"
    return out


def s7_regression_rows(sm: Mapping[str, Any], ref: Mapping[str, Any] | None, *,
                       ref_label: str, settings_this: Mapping[str, Any] | None = None,
                       settings_ref: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """R41-3 (C-S8-11): K0V against its S7 L2b run (record rows). Same crawler: flag when the
    D8 minimum (C1 raw, judged 1 ms force) differs by more than 0.1 kN or the READY time by
    more than 0.1 s (ASSUMPTION, 206 CB regression size). Other crawler: record only. Different
    run settings (duration / items): one row 'settings differ', no values."""
    cid = sm["case"]
    item = "R41-3 K0V vs S7 L2b record (F_s 0 neutrality / code difference)"
    if ref is None:
        return [_row(item, cid, None, None, None, f"S7 reference {ref_label} not found",
                     kind="record")]
    keys = ("duration_s", "items")
    if settings_this is not None and settings_ref is not None:
        diff = {k: (settings_this.get(k), settings_ref.get(k)) for k in keys
                if settings_this.get(k) != settings_ref.get(k)}
        if diff:
            return [_row(item, cid, None, None, None,
                         f"settings differ from {ref_label}: {diff} (R41-3: row not computed)",
                         kind="record")]
    a, b = (sm.get("c1") or {}).get("raw_min_kN"), (ref.get("c1") or {}).get("raw_min_kN")
    ra, rb = sm.get("ready_s"), ref.get("ready_s")
    d_min = None if a is None or b is None else float(a) - float(b)
    d_ready = None if ra is None or rb is None else float(ra) - float(rb)
    same = sm.get("crawler_contact") == ref.get("crawler_contact")
    flag = None
    if same and d_min is not None and d_ready is not None:
        flag = bool(abs(d_min) > S7_REG_D8_KN or abs(d_ready) > S7_REG_READY_S)
    note = (f"this {a} kN / READY {ra} s, S7 {b} kN / {rb} s ({ref_label}); "
            + (f"same crawler ({sm.get('crawler_contact')}): flag |dD8| > {S7_REG_D8_KN:g} kN "
               f"or |dREADY| > {S7_REG_READY_S:g} s" if same else
               f"crawler model differs ({sm.get('crawler_contact')} vs "
               f"{ref.get('crawler_contact')}): record only (S8-L4 / R40-2 data)"))
    if flag:
        note += "; FLAG: F_s 0 path not neutral or a code difference - report the cause"
    return [_row(item, cid, [d_min, d_ready], [S7_REG_D8_KN, S7_REG_READY_S], None, note,
                 kind="record", regression_flag=flag, same_crawler=same)]


def run_end_cause(final_phase: str | None, end: Mapping[str, Any] | None) -> str:
    """R43-4 (spec rev. 43 213.5): why a run ended where it did. ``ready``: last phase READY;
    ``timeout``: the C-S8-17 end time was not reached before the cap (``result.json``
    ``s8_end.timeout``); ``timeout (fixed duration, pre-C-S8-17)``: a batch run before the end
    rule (fixed duration) that ended outside READY / FAULT / IDLE; ``controller``: FAULT / IDLE
    or not READY at the end-rule time."""
    if final_phase == "ready":
        return "ready"
    if final_phase in ("fault", "idle"):
        return "controller"
    if end is None:
        return "timeout (fixed duration, pre-C-S8-17)"
    if end.get("timeout"):
        return "timeout"
    return "controller"


def probe_7c_split(pr: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """U-S8-16 (spec rev. 44 214.4): 7c error ``E - T_0`` of every judged probe row (non-overlap,
    not skipped, truth defined; the rows of the 7c margin) split into the estimator bias
    ``E - T_2`` and the probe round-trip hysteresis ``T_2 - T_0`` (``T_2`` = mean true rod force
    at the return hold end, ``truth_end_kN``). Returns per-row values, the signed extreme of
    each part (largest magnitude) and the split of the worst 7c row; None without rows."""
    legs = (pr or {}).get("legs") or []
    rows = []
    for r in legs:
        if r.get("event_class") == "overlap" or r.get("is_skipped") \
                or r.get("truth_undefined") or r.get("truth_cyl_kN") is None \
                or r.get("truth_end_kN") is None:
            continue
        e, t0, t2 = (float(r["load_estimate_kN"]), float(r["truth_cyl_kN"]),
                     float(r["truth_end_kN"]))
        limit = max(5.0, 0.1 * abs(t0))
        err = e - t0
        rows.append({"round": r.get("round"), "leg": r["leg"], "E_kN": e, "T0_kN": t0,
                     "T2_kN": t2, "err_kN": err, "est_bias_kN": e - t2, "hyst_kN": t2 - t0,
                     "margin_kN": (err - limit) if r.get("zero_cal_deduction")
                     else (abs(err) - limit)})
    if not rows:
        return None

    def extreme(key: str) -> dict[str, Any]:
        w = max(rows, key=lambda x: abs(x[key]))
        return {"value_kN": w[key], "leg": w["leg"], "round": w["round"]}

    worst = max(rows, key=lambda x: x["margin_kN"])
    return {"rows": rows, "est_bias": extreme("est_bias_kN"), "hyst": extreme("hyst_kN"),
            "est_bias_max_kN": max(x["est_bias_kN"] for x in rows),
            "worst_7c": {k: worst[k] for k in ("round", "leg", "margin_kN", "err_kN",
                                               "est_bias_kN", "hyst_kN")}}


def h4_one_sided_ok(mech: Mapping[str, Any]) -> tuple[bool, list[float]]:
    """R43-3: ratio <= 1.1 and ``T_READY <= T_DONE + max(0.5 kN, 3 % T_DONE)`` per rear leg;
    returns (verdict, per-leg slack ``T_DONE + tol - T_READY`` [kN])."""
    slack = [float(td) + max(H4_ONE_SIDED_ABS_N / 1e3, H4_ONE_SIDED_REL * float(td)) - float(tr)
             for tr, td in zip(mech["T_ready_kN"], mech["T_done_kN"], strict=True)]
    ok = all(float(r) <= 1.1 for r in mech["ratio"]) and all(s >= 0.0 for s in slack)
    return ok, slack


def h4_reduction(mech: Mapping[str, Any] | None) -> list[float] | None:
    """F6 record (R43-3): H4 tangential-force reduction ``1 - T_READY / T_DONE`` per rear leg."""
    if not mech:
        return None
    return [1.0 - float(tr) / float(td) if td else None
            for tr, td in zip(mech["T_ready_kN"], mech["T_done_kN"], strict=True)]


def apply_rev43_rows(rows: list[dict[str, Any]], sms: Mapping[str, Mapping[str, Any]]
                     ) -> list[dict[str, Any]]:
    """R43-2 / R43-3 / R43-4 on the s6 / bundle-C rows of the S8 cases (in place) and the new
    F5 (7c pair) and F6 (H4 reduction) record rows (returned).

    * R43-4: every ``run`` row gets ``end_cause`` (:func:`run_end_cause`); the verdict stays;
    * R43-2: the 7c row of an F_s > 0 case is a record (``passed_raw`` kept); a pair row
      "F5 7c margin vs F_s 0 twin" gives the change (``report_cause`` above +2 kN);
    * R43-3: the H4 one-sided row is re-judged with :func:`h4_one_sided_ok`; a row "F6 H4
      reduction" records ``1 - T_READY / T_DONE`` with the twin's."""
    by_case_7c = {r["case"]: r for r in rows if r["item"] == F7C_ITEM}
    extra: list[dict[str, Any]] = []
    for r in rows:
        sm = sms.get(r.get("case"))
        if sm is None:
            continue
        if r["item"] == RUN_ITEM:
            cause = run_end_cause(r["value"], sm.get("end"))
            r["end_cause"] = cause
            if cause != "ready":
                r["note"] = f"{r.get('note') or ''}; end cause {cause} (R43-4)".lstrip("; ")
        elif r["item"] == F7C_ITEM and float(sm["s8"].get("fs_kN") or 0.0) > 0.0:
            if r["passed"] is not None:
                r["passed_raw"] = r["passed"]
                r["passed"] = None
            r["kind"] = "record"
            r["note"] = (f"R43-2: 7c of an F_s > 0 case is a record (C7), see the F5 7c pair "
                         f"row; {r.get('note') or ''}")
        elif r["item"] == H4_ONE_SIDED_ITEM and isinstance(r.get("value"), Mapping):
            ok, slack = h4_one_sided_ok(r["value"])
            if r["passed"] is not None:
                r["passed_rev42"], r["passed"] = r["passed"], ok
            elif "passed_raw" in r:
                r["passed_rev42"], r["passed_raw"] = r["passed_raw"], ok
            else:
                r["passed_rev43_rule"] = ok
            r["limit"] = ("<= 1.1 and T_READY <= T_DONE + max(0.5 kN, 3 % T_DONE) (rear legs, "
                          "R43-3)")
            r["slack_kN"] = slack
    for cid, sm in sms.items():
        fs = float(sm["s8"].get("fs_kN") or 0.0)
        twin = sm["s8"].get("pair_fs0")
        r7 = by_case_7c.get(cid)
        if fs > 0.0 and r7 is not None and twin:
            t7 = by_case_7c.get(twin)
            a, b = r7.get("value"), None if t7 is None else t7.get("value")
            d = None if a is None or b is None else float(a) - float(b)
            row = _row("F5 7c margin vs F_s 0 twin [kN] (R43-2, record)", cid, d,
                       f"+{F5_FLAG_N / 1e3:g} kN report", None,
                       f"this {a}, twin {b} ({twin}); margin = error - max(5 kN, 10 %)",
                       kind="pair")
            row["report_cause"] = None if d is None else bool(d > F5_FLAG_N / 1e3)
            # U-S8-16: split of the worst 7c row of this case and of the twin
            sp_a = (sm.get("probe_7c_split") or {}).get("worst_7c")
            sp_b = ((sms.get(twin) or {}).get("probe_7c_split") or {}).get("worst_7c")
            row["split_this"], row["split_twin"] = sp_a, sp_b
            if sp_a is not None:
                row["note"] += (f"; split E - T2 / T2 - T0: this {sp_a['est_bias_kN']:+.2f} / "
                                f"{sp_a['hyst_kN']:+.2f} kN ({sp_a['leg']})")
                if sp_b is not None:
                    row["note"] += (f", twin {sp_b['est_bias_kN']:+.2f} / "
                                    f"{sp_b['hyst_kN']:+.2f} kN ({sp_b['leg']})")
            extra.append(row)
        mech = (sm.get("h4_mechanism") or None)
        red = h4_reduction(mech)
        if red is not None:
            tw = sms.get(twin) if twin else None
            red_t = h4_reduction((tw or {}).get("h4_mechanism"))
            extra.append(_row("F6 H4 reduction 1 - T_READY / T_DONE per rear leg (R43-3, "
                              "record)", cid, red, None, None,
                              f"legs {mech.get('legs')}; F_s 0 twin {twin}: {red_t}; P_stop last "
                              f"{mech.get('P_stop_last_kN')} kN", kind="record"))
    return extra


# --- rev. 46 rows (C-S8-22 ①, ②, ④) --------------------------------------------------------------


def _is_pressure_case(sm: Mapping[str, Any] | None) -> bool:
    return (sm or {}).get("s8", {}).get("contact") == "pressure"


def apply_rev46_rows(rows: list[dict[str, Any]], sms: Mapping[str, Mapping[str, Any]]
                     ) -> list[dict[str, Any]]:
    """C-S8-22 ① / ② / ④ on the rows (in place); returns the extra judged rows.

    * ①: rows of a pressure-only case whose item starts with
      :data:`PRESSURE_COMPARISON_PREFIXES` become ``kind`` "comparison" (``passed`` None,
      ``passed_raw`` kept): item-9 M5 comparison of the operating rule's reference;
    * ②: the s6 level-trend rows (:data:`TREND_ITEMS_S6`, groups mixed) become ``superseded``;
      :func:`level_trend_rows_s8` gives the grouped rows;
    * ④: rod-pressure fallback warnings outside the forced window of a case without a rod-sensor
      fault injection are unexpected warnings: added to the 5.24.2 row (value, FLAG note) and
      failing the 72.1 (6) row when that row is a gate (``kind`` function); otherwise one judged
      row of its own."""
    extra: list[dict[str, Any]] = []
    diag_gate: dict[str, bool] = {}
    for r in rows:
        cid = r.get("case")
        sm = sms.get(cid)
        if r["item"] in TREND_ITEMS_S6 and r.get("source") == "s6":
            r["passed_raw"], r["passed"] = r["passed"], None
            r["kind"] = "superseded"
            r["note"] = ("C-S8-22 ②: mixed judges / F_s / beta and no reference batch; see the "
                         f"'{TREND_ITEM_S8}' rows; " + str(r.get("note") or ""))
            continue
        if sm is None:
            continue
        if _is_pressure_case(sm) and r["item"].startswith(PRESSURE_COMPARISON_PREFIXES):
            if r["passed"] is not None or "passed_raw" not in r:
                r["passed_raw"] = r["passed"]
            r["passed"] = None
            r["kind"] = "comparison"
            r["note"] = ("C-S8-22 ①: pressure-only closed loop = item-9 M5 comparison row, not a "
                         "gate (I4 judges the expected classes); " + str(r.get("note") or ""))
            continue
        fb = sm.get("rod_fallback") or {}
        outside = [e for e in fb.get("events") or [] if not e["in_forced_window"]]
        if not outside:
            continue
        summary = "; ".join(f"{e['leg']} {e['t_s']:.2f} s {e['reason']}" for e in outside)
        if r["item"] == WARN_ITEM:
            # spec rev. 50 220.6 ③ (U-S8-43): the injected leg's fallback within [fault time,
            # + 2 periods] is expected (injection); everything else stays a FLAG
            expected = [e for e in outside if e.get("expected_injected")]
            flagged = [e for e in outside if not e.get("expected_injected")]
            if expected:
                r["note"] = (f"{r.get('note') or ''}; expected (injected rod fault "
                             f"{fb.get('fault_leg')} at {fb.get('fault_t_s')} s, window "
                             f"{fb.get('expected_window_s')} s): {ROD_FALLBACK_WARNING} "
                             f"x{len(expected)} ("
                             + "; ".join(f"{e['leg']} {e['t_s']:.2f} s {e['reason']}"
                                         for e in expected)
                             + ") not counted (spec rev. 50 220.6 ③)").lstrip("; ")
                r["rod_fallback_expected"] = expected
            if flagged:
                fl_summary = "; ".join(f"{e['leg']} {e['t_s']:.2f} s {e['reason']}"
                                       for e in flagged)
                v = r.get("value") or 0
                r["value"] = int(v) + len(flagged)
                r["passed"] = None
                r["note"] = (f"{r.get('note') or ''}; FLAG: {ROD_FALLBACK_WARNING} "
                             f"x{len(flagged)} ({fl_summary}) (C-S8-22 ④)").lstrip("; ")
                r["rod_fallback"] = flagged
        elif r["item"] == DIAG_ITEM:
            val = dict(r["value"]) if isinstance(r.get("value"), Mapping) else {}
            val[ROD_FALLBACK_WARNING] = len(outside)
            r["value"] = val
            r["rod_fallback"] = outside
            if fb.get("injected"):
                r["note"] = f"{r.get('note') or ''}; rod fault injected: fallback recorded"
                diag_gate[cid] = True
            elif r.get("kind") == "function":
                if r["passed"] is not None:
                    r["passed_rev45"] = r["passed"]
                r["passed"] = False
                r["note"] = (f"{r.get('note') or ''}; FAIL: unexpected {ROD_FALLBACK_WARNING} "
                             f"({summary}) without a rod-sensor fault injection (C-S8-22 ④)")
                diag_gate[cid] = True
    for cid, sm in sms.items():
        fb = sm.get("rod_fallback") or {}
        outside = [e for e in fb.get("events") or [] if not e["in_forced_window"]]
        if outside and not diag_gate.get(cid) and not fb.get("injected"):
            extra.append(_row("C-S8-22 ④ no rod-pressure fallback outside the forced window "
                              "(unexpected warning)", cid, len(outside), 0, False,
                              "; ".join(f"{e['leg']} {e['t_s']:.2f} s {e['reason']}"
                                        for e in outside), events=outside))
    return extra


# --- CB rerun acceptance (U-S8-23, spec rev. 46 216.8) -----------------------------------------


def lock_valve_premise(s8: Mapping[str, Any], controller_meta: Mapping[str, Any] | None
                       ) -> dict[str, Any]:
    """Lock valve of the plant (``s8.lock_valve``) and of the controller
    (``controller_meta.two_pressure.settings.lock_valve``; absent = pilot check, since
    ``TwoPressureSettings.to_meta`` drops the key on the pilot-check path). ``cb_aware``: the
    controller of a CB case runs the CB diagnosis (P-S8-11); None for a pilot-check case."""
    plant = str(s8.get("lock_valve") or "pilot_check")
    settings = (((controller_meta or {}).get("two_pressure") or {}).get("settings") or {})
    ctrl = settings.get("lock_valve")
    return {"plant": plant, "controller": ctrl,
            "cb_aware": None if plant != "counterbalance" else ctrl == "counterbalance",
            "moving_stroke_check": settings.get("moving_stroke_check"),
            "source": "settings.s8.lock_valve / controller_meta.two_pressure.settings.lock_valve"}


def _cb_lookup(cid: str, metrics_by_id: Mapping[str, Mapping[str, Any]],
               rows: Sequence[Mapping[str, Any]], ref_docs: Sequence[tuple[str, Mapping]]
               ) -> tuple[Mapping[str, Any] | None, dict[str, Mapping[str, Any]], str | None]:
    """(metrics, rows by item, label) of a case from this batch, else the first reference /
    lookup batch that has it."""
    if cid in metrics_by_id:
        return metrics_by_id[cid], {r["item"]: r for r in rows if r.get("case") == cid}, \
            f"batch {cid}"
    for label, doc in ref_docs:
        mm = {m["case"]: m for m in doc.get("metrics") or []}
        if cid in mm:
            return mm[cid], {r["item"]: r for r in doc.get("rows") or []
                             if r.get("case") == cid}, f"{label} {cid}"
    return None, {}, None


def _event_min(case_rows_: Mapping[str, Mapping[str, Any]]) -> float | None:
    for item in CB_EVENT_ITEMS:
        r = case_rows_.get(item)
        if r is not None and isinstance(r.get("value"), (int, float)):
            return float(r["value"])
    return None


def cb_rerun_rows(sms: Mapping[str, Mapping[str, Any]],
                  metrics_by_id: Mapping[str, Mapping[str, Any]],
                  rows: Sequence[Mapping[str, Any]],
                  ref_docs: Sequence[tuple[str, Mapping]] = ()) -> list[dict[str, Any]]:
    """U-S8-23 / spec rev. 46 216.8 CB rerun rows of the CB cases (``s8.lock_valve`` =
    counterbalance) of the batch; empty without CB cases.

    Per CB case: premise (controller ``lock_valve`` = counterbalance, else
    :data:`CB_UNAWARE`), no rod-pressure fallback warning (no fault injection), pilot-check
    twin regression (:data:`CB_PAIRS`, twins from this batch or ``ref_docs``: D8 outside
    REANCHOR / REANCHOR / event min within 0.2 kN, READY within 0.1 s), F2 violations 0, and
    for CB_G4_Fs0 C8 >= twin - 0.2 kN. One acceptance row over all CB cases: every CB row
    passed and no other row of a CB case failed (206: remaining C / F rows as before)."""
    cb = sorted(c for c, sm in sms.items()
                if str((sm.get("s8") or {}).get("lock_valve") or "") == "counterbalance")
    if not cb:
        return []
    out: list[dict[str, Any]] = []
    for cid in cb:
        sm = sms[cid]
        lv = sm.get("lock_valve") or lock_valve_premise(sm["s8"], None)
        aware = bool(lv.get("cb_aware"))
        out.append(_row(CB_PREMISE_ITEM, cid, lv.get("controller"), "counterbalance", aware,
                        "" if aware else f"{CB_UNAWARE}: controller_meta.two_pressure.settings "
                        "has no lock_valve = counterbalance (D2 upper bound / fallback estimate "
                        "of the pilot check; result not valid for the CB rerun)",
                        lock_valve=lv, cb_unaware=not aware))
        fb = sm.get("rod_fallback") or {}
        ev = list(fb.get("events") or [])
        if fb.get("injected"):
            out.append(_row(CB_NO_FALLBACK_ITEM, cid, len(ev), 0, None,
                            "rod-sensor fault injected: record", kind="record", events=ev))
        else:
            out.append(_row(CB_NO_FALLBACK_ITEM, cid, len(ev), 0, len(ev) == 0,
                            "; ".join(f"{e['leg']} {e['t_s']:.2f} s {e['reason']}" for e in ev),
                            events=ev))
        f2 = sm.get("F2")
        out.append(_row(CB_F2_ITEM, cid, None if f2 is None else f2.get("violations"), 0,
                        None if f2 is None else f2.get("violations") == 0,
                        "" if f2 is not None else "no F2 (no series / pressure-only)",
                        kind="judged" if f2 is not None else "record"))
        twin = CB_PAIRS.get(cid)
        m_cb, r_cb, _ = _cb_lookup(cid, metrics_by_id, rows, ())
        m_tw, r_tw, src = (None, {}, None) if twin is None else \
            _cb_lookup(twin, metrics_by_id, rows, ref_docs)
        ev_cb = _event_min(r_cb)
        ev_tw = _event_min(r_tw)
        if m_cb is None or m_tw is None:
            out.append(_row(CB_REG_ITEM, cid, None, [CB_REG_FORCE_KN, CB_REG_READY_S], None,
                            f"pilot-check twin {twin} not found (give the p1r batch with "
                            "--ref-batch / --lookup-batch)", kind="hold", twin=twin))
        else:
            def diff(key):
                a, b = m_cb.get(key), m_tw.get(key)
                return None if a is None or b is None else float(a) - float(b)
            ra, rb = (m_cb.get("times_s") or {}).get("ready"), \
                (m_tw.get("times_s") or {}).get("ready")
            d = {"d8_excl_reanchor_kN": diff("min_cyl_excl_reanchor_kN"),
                 "reanchor_kN": diff("min_cyl_reanchor_kN"),
                 "event_min_kN": None if ev_cb is None or ev_tw is None else ev_cb - ev_tw,
                 "ready_s": None if ra is None or rb is None else float(ra) - float(rb)}
            forces = [v for k, v in d.items() if k != "ready_s" and v is not None]
            ok = (bool(forces) and d["ready_s"] is not None
                  and all(abs(v) <= CB_REG_FORCE_KN + 1e-9 for v in forces)
                  and abs(d["ready_s"]) <= CB_REG_READY_S + 1e-9)
            out.append(_row(CB_REG_ITEM, cid, d, [CB_REG_FORCE_KN, CB_REG_READY_S], bool(ok),
                            f"twin {src} (diff = CB - pilot check)", twin=twin, twin_source=src))
        if cid == "CB_G4_Fs0":
            floor = CB_G4_FS0_FLOOR_KN if ev_tw is None else ev_tw - CB_REG_FORCE_KN
            out.append(_row(CB_G4_ITEM, cid, ev_cb, round(floor, 4),
                            None if ev_cb is None else bool(ev_cb >= floor - 1e-9),
                            f"twin {twin} {ev_tw} kN" if ev_tw is not None
                            else f"twin row not found: spec value {CB_G4_FS0_FLOOR_KN} kN",
                            kind="judged" if ev_cb is not None else "hold"))
    cb_set = set(cb)
    own = [r for r in out if r.get("kind") in ("judged", "hold")]
    other_fail = [f"{r['case']}: {r['item']}" for r in rows
                  if r.get("case") in cb_set and r.get("passed") is False]
    n_fail = sum(1 for r in own if r["passed"] is False) + len(other_fail)
    n_open = sum(1 for r in own if r["passed"] is None)
    unaware = [r["case"] for r in out if r.get("cb_unaware")]
    passed = False if n_fail else (None if n_open else True)
    note = (f"{len(cb)} CB cases; CB rows failed {sum(1 for r in own if r['passed'] is False)}, "
            f"open {n_open}; other failed rows of CB cases {len(other_fail)}")
    if unaware:
        note += f"; {CB_UNAWARE}: {unaware}"
    out.append(_row(CB_ACCEPT_ITEM, "*", {"failed": n_fail, "open": n_open,
                                          "cb_unaware": unaware}, 0, passed, note,
                    kind="judged" if passed is not None else "hold",
                    other_failed_rows=other_fail[:200]))
    return out


TREND_ITEM_S8 ="8 level trend min force (excl. REANCHOR), S8 grouped (C-S8-22 ②)"
TREND_REANCHOR_ITEM_S8 = "8 REANCHOR min force, S8 grouped (C-S8-22 ②)"
TREND_TIME_ITEM_S8 = "8 level trend time READY - TOUCH, S8 grouped (record)"
LEVELS = ("top", "middle", "bottom")


def trend_key(m: Mapping[str, Any], s8: Mapping[str, Any]) -> tuple | None:
    """C-S8-22 ② group key (floor, F_s, engine, lock valve) of an eligible case: group in
    :data:`TREND_GROUPS`, judged condition, combined judge, beta 1.0 GPa, ideal sensor; else
    None."""
    base = s8.get("base") or {}
    if m.get("group") not in TREND_GROUPS or s8.get("condition", "judged") != "judged":
        return None
    if (s8.get("contact") or m.get("contact") or "combined") == "pressure":
        return None
    if abs(float(base.get("beta_GPa") or 1.0) - 1.0) > 1e-9 or base.get("sensor_model"):
        return None
    return (m.get("floor"), float(s8.get("fs_kN") or 0.0), s8.get("engine") or "L2b_NSC",
            s8.get("lock_valve") or "pilot_check")


def level_trend_rows_s8(metrics: Sequence[Mapping[str, Any]],
                        sms: Mapping[str, Mapping[str, Any]],
                        ref_docs: Sequence[tuple[str, Mapping[str, Any]]] = ()
                        ) -> list[dict[str, Any]]:
    """C-S8-22 ② (spec rev. 46 216.7 ②): item 8 per group :func:`trend_key`. Levels of the
    batch first, missing levels from the reference / lookup batches (``ref_docs`` = (label,
    ``verify_S8C.json`` document)). A group gets rows when at least one of its levels is in this
    batch and two or more levels are known; the ordering row (``top <= middle + 1.25 kN <=
    bottom + 2.5 kN``, s6 U54 tolerance) is judged with all three levels, else a record. Several
    cases on one level: the smallest value (listed)."""
    from outrigger_sim.verify import s6_control as s6

    groups: dict[tuple, dict[str, list[dict[str, Any]]]] = {}
    here: set[tuple] = set()

    def add(m, s8, label):
        key = trend_key(m, s8)
        if key is None or m.get("level") not in LEVELS:
            return
        groups.setdefault(key, {}).setdefault(m["level"], []).append({
            "case": m["case"], "batch": label,
            "excl_kN": m.get("min_cyl_excl_reanchor_kN", m.get("min_cyl_after_liftoff_kN")),
            "reanchor_kN": m.get("min_cyl_reanchor_kN"),
            "time_s": m.get("t_ready_minus_touch_s"), "F_min_N": m.get("F_min_N")})
        if label == "this batch":
            here.add(key)

    for m in metrics:
        add(m, (sms.get(m["case"]) or {}).get("s8") or {}, "this batch")
    for label, doc in ref_docs:
        known = {(k, lv) for k, d in groups.items() for lv in d}
        ref_sms = doc.get("s8_metrics") or {}
        for m in doc.get("metrics") or []:
            key = trend_key(m, (ref_sms.get(m["case"]) or {}).get("s8") or {})
            if key is None or (key, m.get("level")) in known:
                continue
            add(m, (ref_sms.get(m["case"]) or {}).get("s8") or {}, label)
    tol = s6.TREND_TOLERANCE_N / 1e3
    rows = []
    for key in sorted(k for k in groups if k in here):
        lv = groups[key]
        if len(lv) < 2:
            continue
        name = f"{key[0]} F_s {key[1]:g} {key[2]} {key[3]}"

        def pick(field, lv=lv):
            out = {}
            for level, entries in lv.items():
                vals = [e[field] for e in entries if e[field] is not None]
                out[level] = min(vals) if vals else None
            return out

        excl = pick("excl_kN")
        src = {level: [f"{e['case']} ({e['batch']})" for e in entries]
               for level, entries in lv.items()}
        full = set(excl) == set(LEVELS) and None not in excl.values()
        ok = None
        if full:
            ok = bool(excl["top"] <= excl["middle"] + tol and excl["middle"] <= excl["bottom"]
                      + tol)
        rows.append(_row(TREND_ITEM_S8, name, excl,
                         f"top <= middle + {tol:g} kN, middle <= bottom + {tol:g} kN", ok,
                         ("group (floor, F_s, combined, beta 1.0, ideal sensor, engine, lock "
                          f"valve); sources {src}") + ("" if full else
                                                      "; incomplete group: record"),
                         kind="judged" if full else "record", sources=src,
                         group=list(key)))
        rea = pick("reanchor_kN")
        if any(v is not None for v in rea.values()):
            fmin = max(float(e["F_min_N"]) for es in lv.values() for e in es
                       if e["F_min_N"] is not None)
            lim = (fmin + D8_MARGIN_N) / 1e3
            rows.append(_row(TREND_REANCHOR_ITEM_S8, name, rea, lim,
                             all(v is None or v >= lim for v in rea.values()),
                             f"sources {src}", sources=src, group=list(key)))
        rows.append(_row(TREND_TIME_ITEM_S8, name, pick("time_s"), None, None,
                         "no reduced per-level times (J4 / I3)", kind="record", sources=src,
                         group=list(key)))
    return rows


def wika_pooled_rows(sms: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Control rev. 46 216.6 (1): batch record row of :func:`pooled_side_std` over the noisy
    (WIKA) runs; the per-leg values with their standard error are listed."""
    laws = {c: sm.get("F1_law") for c, sm in sms.items() if _is_noisy(sm)
            and (sm.get("F1_law") or {}).get("metrics")}
    if not laws:
        return []
    pooled = pooled_side_std(list(laws.values()))
    per_leg = {}
    for c, law in laws.items():
        lm = law["metrics"]
        per_leg[c] = [None if lm["std_ratio"][j] is None else
                      {"std_ratio": lm["std_ratio"][j], "n": lm["n"][j],
                       "rel_std_error": 1.0 / math.sqrt(2.0 * (lm["n"][j] - 1))}
                      for j in range(4)]
    flag = None if pooled is None else any(v and v["flag"] for v in pooled.values())
    note = "; ".join(f"{side} std {v['std_N']:.1f} N / sigma {v['sigma_F_N']:.1f} N = "
                     f"{v['ratio']:.4f} (n {v['n']}, rel. s.e. {v['rel_std_error']:.4f})"
                     for side, v in (pooled or {}).items() if v)
    return [_row("F1 WIKA residual std per side pooled over the WIKA runs (record, +-3 %; "
                 "control rev. 46 216.6 (1); per leg: R45-1 ② band)", "*",
                 {s: None if v is None else v["ratio"] for s, v in (pooled or {}).items()},
                 WIKA_POOLED_STD_TOL, None, note + (" FLAG" if flag else ""), kind="record",
                 flag=flag, pooled=pooled, per_leg=per_leg, runs=sorted(laws))]


# --- 213.6 rerun acceptance rows (C-S8-19 ⑦, control script s8p1r_gate.py) -------------------

R44_TOUCH_REG_S = 0.3
R44_D8_REG_KN = 1.0
R44_READY_REG_S = 1.0
"""213.6 TOUCH regression: F_s 0 cases against a reference batch (ASSUMPTION of rev. 43 213.9)."""
R44_TOUCH_FIX_S = 1.0
"""213.6 TOUCH fix: TOUCH length of an F_s > 0 case <= the same-floor F_s 0 twin + 1 s."""
R44_REREADY_S = 40.0
R44_SLOW_FRACTION = 0.5
"""Path 1 of ``s8p1r_gate.py``: a TOUCH command below 0.5 v_max (0.25 v_max approach) or 0."""


def first_phase_length(phases: Sequence[Sequence[Any]], name: str, end_s: float
                       ) -> tuple[float | None, float | None]:
    """(length, end time) of the first ``name`` phase."""
    ph = [(float(t), str(p)) for t, p in phases]
    for i, (t, p) in enumerate(ph):
        if p == name:
            t1 = ph[i + 1][0] if i + 1 < len(ph) else float(end_s)
            return t1 - t, t1
    return None, None


def touch_air_commands(t_ctrl: np.ndarray, phase: np.ndarray, raw_u: np.ndarray,
                       t_pad: np.ndarray, n_pad: np.ndarray, v_max: float,
                       period_s: float = 0.1) -> list[list[float]]:
    """213.6 free-air ``touch_seen``, path 1 of ``s8p1r_gate.py``: per leg the TOUCH control
    instants whose command is the slow approach (``0 < u < 0.5 v_max``) or 0 while the 1 ms pad
    record has no contact (``N > 0``) over the reading period ``(t_k - T, t_k]``. Same time base
    for ``t_ctrl`` and ``t_pad``."""
    tc = np.asarray(t_ctrl, float)
    tp = np.asarray(t_pad, float)
    n = np.asarray(n_pad, float)
    u = np.asarray(raw_u, float)
    out: list[list[float]] = [[] for _ in range(u.shape[1])]
    for k in np.flatnonzero(np.asarray(phase).astype(str) == "touch"):
        a = int(np.searchsorted(tp, tc[k] - period_s + 1e-9, side="left"))
        b = int(np.searchsorted(tp, tc[k] + 1e-9, side="right"))
        for leg in range(u.shape[1]):
            slow = (0.0 < u[k, leg] < R44_SLOW_FRACTION * v_max - 1e-9) or u[k, leg] == 0.0
            if slow and not bool((n[a:b, leg] > 0.0).any()):
                out[leg].append(round(float(tc[k]), 3))
    return out


def reapproach_outside_events(phases: Sequence[Sequence[Any]], end_s: float,
                              events: Sequence[tuple[float, str]], t_event: float | None
                              ) -> dict[str, list[float]]:
    """213.6 1.4 side effect: ``leg_reapproach_start`` inside PROBE windows and inside READY
    windows, both before the floor event (or anywhere when the run has none)."""
    ph = [(float(t), str(p)) for t, p in phases]
    out: dict[str, list[float]] = {"probe": [], "ready": []}
    for t, name in events:
        if name.split(":")[0] != "leg_reapproach_start":
            continue
        if t_event is not None and t >= float(t_event) - 1e-9:
            continue
        for i, (a, p) in enumerate(ph):
            b = ph[i + 1][0] if i + 1 < len(ph) else float(end_s)
            if a - 1e-9 <= t < b - 1e-9 and p in out:
                out[p].append(round(float(t), 3))
    return out


def _twin_of(cid: str, s8: Mapping[str, Any], sms: Mapping[str, Any]) -> str | None:
    if s8.get("pair_fs0") and s8["pair_fs0"] in sms:
        return s8["pair_fs0"]
    floor = s8.get("floor")
    for cand in (f"K0V_top_{floor}_Fs0", f"K0_top_{floor}_Fs0"):
        if s8.get("level") == "top" and cand in sms:
            return cand
    return None


def r44_gate_rows(sms: Mapping[str, Mapping[str, Any]], rows: Sequence[Mapping[str, Any]],
                  ref_metrics: Mapping[str, Mapping[str, Any]] | None = None,
                  ref_label: str | None = None) -> list[dict[str, Any]]:
    """C-S8-19 ⑦: the five 213.6 rerun acceptance rows (``s8p1r_gate.py`` definitions).

    * TOUCH regression (needs ``ref_metrics``, the ``metrics`` of a reference
      ``verify_S8C.json``): F_s 0 cases, TOUCH end +-0.3 s, D8 (outside REANCHOR) +-1.0 kN,
      READY +-1.0 s;
    * TOUCH fix: F_s > 0 TOUCH length <= same-floor F_s 0 twin + 1 s (twin in the batch);
    * free-air ``touch_seen`` = 0 (path 1, controller command vs 1 ms pad contact);
    * U-S8-9: E-group G4 rows '6 min after settlement' >= F_min and '6 re-READY <= 40 s';
    * 1.4 side effect: no ``leg_reapproach_start`` in PROBE / event-free READY.
    Rows are judged where computable, else records."""
    out: list[dict[str, Any]] = []
    # TOUCH regression
    item = "R44-213.6 TOUCH regression F_s 0 vs reference batch (TOUCH end 0.3 s, D8 1 kN, READY 1 s)"
    if ref_metrics is None:
        out.append(_row(item, "*", None, None, None, "no reference batch (--ref-batch)",
                        kind="record"))
    else:
        for cid, sm in sms.items():
            r = sm.get("r44") or {}
            ref = ref_metrics.get(cid)
            if float(sm["s8"].get("fs_kN") or 0.0) != 0.0 or ref is None or not r:
                continue
            _, te_ref = first_phase_length(ref.get("phases") or [], "touch",
                                           ref["times_s"]["end"])
            d = {"touch_end_s": None if r.get("touch_end_s") is None or te_ref is None
                 else r["touch_end_s"] - te_ref,
                 "d8_kN": None if r.get("d8_kN") is None or ref.get(
                     "min_cyl_excl_reanchor_kN") is None
                 else r["d8_kN"] - ref["min_cyl_excl_reanchor_kN"],
                 "ready_s": None if r.get("ready_s") is None or ref.get("ready_s") is None
                 else r["ready_s"] - ref["ready_s"]}
            ok = (d["touch_end_s"] is not None and abs(d["touch_end_s"]) <= R44_TOUCH_REG_S + 1e-9
                  and (d["d8_kN"] is None or abs(d["d8_kN"]) <= R44_D8_REG_KN)
                  and (d["ready_s"] is None or abs(d["ready_s"]) <= R44_READY_REG_S))
            out.append(_row(item, cid, d, [R44_TOUCH_REG_S, R44_D8_REG_KN, R44_READY_REG_S],
                            bool(ok), f"reference {ref_label}", kind="judged"))
    # TOUCH fix
    item = "R44-213.6 TOUCH fix: TOUCH length <= F_s 0 twin + 1 s"
    for cid, sm in sms.items():
        if float(sm["s8"].get("fs_kN") or 0.0) <= 0.0 or not sm.get("r44"):
            continue
        tw = _twin_of(cid, sm["s8"], sms)
        a = sm["r44"].get("touch_len_s")
        b = None if tw is None else (sms[tw].get("r44") or {}).get("touch_len_s")
        d = None if a is None or b is None else a - b
        out.append(_row(item, cid, d, R44_TOUCH_FIX_S,
                        None if d is None else bool(d <= R44_TOUCH_FIX_S + 1e-9),
                        f"this {a} s, twin {tw} {b} s",
                        kind="judged" if d is not None else "record"))
    # free-air touch_seen
    item = "R44-213.6 free-air touch_seen = 0 (TOUCH slow / zero command without pad contact)"
    for cid, sm in sms.items():
        air = (sm.get("r44") or {}).get("touch_air")
        if air is None:
            continue
        n = sum(1 for a in air if a)
        out.append(_row(item, cid, n, 0, n == 0, f"per leg instants {air}"[:400]))
    # U-S8-9
    g4 = [c for c, sm in sms.items() if sm["s8"].get("event") == "G4"
          and sm["s8"].get("group") == "E"]
    if g4:
        by = {(r["case"], r["item"]): r for r in rows}
        vals = {}
        ok = True
        for c in g4:
            mn = (by.get((c, "6 min after settlement")) or {}).get("value")
            rr = (by.get((c, "6 re-READY <= 40 s")) or {}).get("value")
            f_min = sms[c]["F_min_N"] / 1e3
            vals[c] = [mn, rr]
            ok &= mn is not None and rr is not None and mn >= f_min and rr <= R44_REREADY_S
        out.append(_row("R44-213.6 U-S8-9: E-group G4 C8 min >= F_min and re-READY <= 40 s", "*",
                        vals, [round(sms[g4[0]]["F_min_N"] / 1e3, 4), R44_REREADY_S], bool(ok),
                        f"{len(g4)} G4 cases"))
    # 1.4 side effect
    item = "R44-213.6 1.4 side effect: no leg_reapproach_start in PROBE / event-free READY"
    for cid, sm in sms.items():
        ra = (sm.get("r44") or {}).get("reapproach")
        if ra is None:
            continue
        n = len(ra["probe"]) + len(ra["ready"])
        out.append(_row(item, cid, n, 0, n == 0, f"PROBE {ra['probe']}, READY {ra['ready']}"))
    return out


def item9_summary(sms: Mapping[str, Mapping[str, Any]],
                  item9_cases: Sequence[str]) -> list[dict[str, Any]]:
    """I1 / I2 / I3 / I5 and the conclusion over the item-9 cases (I4: :func:`i4_rows`)."""
    rows = []
    sel = [sms[c] for c in item9_cases if c in sms and sms[c].get("item9")]
    if not sel:
        return [_row("item 9 I1-I5", "*", None, None, None, "no item-9 case in the batch",
                     kind="record")]
    comb = [s for s in sel if (s["s8"].get("contact") or "combined") != "pressure"]
    jc = {s["case"]: judge_score(s, "J_C") for s in sel}
    jp = {s["case"]: judge_score(s, "J_P") for s in sel}
    miss = sum(jc[s["case"]]["M1_missed"] for s in comb)
    late = sum(jc[s["case"]]["M1p_late"] for s in comb
               if s["s8"].get("event") in FAST_EVENTS)
    f2 = sum((s.get("F2") or {}).get("violations", 0) for s in comb)
    n = sum(jc[s["case"]]["n"] for s in comb)
    so = [e for s in comb for e in sampling_only_episodes(s, "J_C")]
    rows.append(_row("I1 J_C: M1 = 0, M1' = 0 (fast events), F2 = 0", "*", [miss, late, f2], 0,
                     miss == 0 and late == 0 and f2 == 0,
                     f"{len(comb)} combined cases, {n} episodes, upper95 "
                     f"{clopper_pearson_upper(miss, n)}; sampling_only {len(so)} of the {miss} "
                     "missed (211.2: judgement level missed between 10 Hz samples, action level "
                     "within t_on + tau_d; still counted in the gate until U-S8-7)",
                     sampling_only=so, sampling_only_count=len(so)))
    # C-S8-37 (spec rev. 52 232): I1 above = corrected reading; raw (record) and the
    # F_s - m g ceiling (sensitivity) of both judges beside it
    for variant, kind in (("raw", "record"), ("upper_sensitivity", "sensitivity"),
                          ("all_apply", "sensitivity")):
        vals = {}
        for name in ("J_C", "J_P"):
            sc = [(s, judge_score(s, name, variant=variant)) for s in sel
                  if ((s.get("item9") or {}).get("replay") or {}).get(variant)]
            vals[name] = {"cases": len(sc),
                          "M1_missed_combined": sum(
                              d["M1_missed"] for s, d in sc
                              if (s["s8"].get("contact") or "combined") != "pressure"),
                          "M1_missed_all": sum(d["M1_missed"] for _s, d in sc),
                          "M1p_late_all": sum(d["M1p_late"] for _s, d in sc)}
        rows.append(_row(f"I1 {variant} reading: J_C / J_P M1 missed, M1' late ({kind})", "*",
                         vals, None, None, "default judgement (I1 row) = corrected reading "
                         "(+delta_i = min(0.5 kN, 2 F_s,i) on L2b-NSC legs with F_s,i > 0 where "
                         "pad N < 1.5 kN, spec rev. 54 249)", kind=kind, reading=variant))
    # C-S8-40 (spec rev. 54 249): cases whose all-apply counts differ from the default
    diff = {}
    for s in sms.values():
        if not ((s.get("item9") or {}).get("replay") or {}).get("all_apply"):
            continue
        for name in ("J_C", "J_P"):
            a, b = judge_score(s, name), judge_score(s, name, variant="all_apply")
            keys = ("M1_missed", "M1p_late", "M2", "n")
            if any(a[k] != b[k] for k in keys):
                diff.setdefault(s["case"], {})[name] = {k: [a[k], b[k]] for k in keys}
    rows.append(_row("C-S8-40 all-apply +0.5 kN vs default reading: cases with other J_P / J_C "
                     "M1 missed / M1' late / M2 flags / episodes [default, all-apply] "
                     "(sensitivity, spec rev. 54 249)", "*", len(diff), None, None,
                     "; ".join(f"{c}: {v}" for c, v in sorted(diff.items()))[:3000]
                     or "no difference", kind="sensitivity", reading="all_apply",
                     per_case=diff))
    act = sum(len((s.get("F8") or {}).get("events", [])) + (s.get("F8") or {}).get(
        "ready_exits", 0) for s in comb if s["s8"].get("event") in EVENT_FREE)
    rows.append(_row("I2 J_C: no actual control action in event-free windows", "*", act, 0,
                     act == 0))
    m4 = [jc[s["case"]]["M4_max_kN"] for s in comb if jc[s["case"]]["M4_max_kN"] is not None]
    rows.append(_row("I3 J_C: M4 max <= sensor share", "*", max(m4) if m4 else None,
                     "0.1 (ideal) / 0.6 (WIKA) kN",
                     None if not m4 else all(
                         (jc[s["case"]]["M4_max_kN"] if jc[s["case"]]["M4_max_kN"] is not None
                          else -1e9) <= _share_kN(s) for s in comb),
                     "" if m4 else "no sample near F_min"))
    press =[s for s in sel if s["s8"].get("contact") == "pressure"]
    i5 = [(s["case"], jp[s["case"]]["M4_max_kN"], max(s["fs_leg_N"]) / 1e3) for s in press]
    rows.append(_row("I5 J_P M4 max ~ F_s +- 0.5 kN (record)", "*", i5, None, None,
                     kind="record"))
    missed_p = sorted({s["s8"].get("fs_kN") for s in sel if jp[s["case"]]["M1_missed"] > 0})
    rows.append(_row("conclusion: pressure-only misses at F_s [kN]", "*", missed_p, None, None,
                     "non-empty: 'do not judge contact / F_min from the pressure alone' (U-S8-2)"
                     if missed_p else "no pressure-only miss", kind="report"))
    return rows


def _share_kN(s) -> float:
    return (SENSOR_SHARE_N["wika"] if s["s8"].get("base", {}).get("sensor_model")
            else SENSOR_SHARE_N["ideal"]) / 1e3


# --- batch -------------------------------------------------------------------------------------------


def _load(d: Path):
    from outrigger_sim.params import load_params
    from outrigger_sim.verify import s7_control as s7

    case, m, pr = s7._load_case_metrics(d)
    s = case["result"]["settings"]
    m["contact"] = s.get("contact")
    params = load_params(level=s["level"])
    if case_engine(case) == "L2b_NSC":
        l2b_floor_point_metrics(case, m)
    return case, m, pr, params


def _rt_of_case(case, d: Path, forced: Mapping[str, Any] | None = None, *,
                f_min_N: float | None = None) -> dict[str, Any]:
    """C-S8-37: ``rt`` (:func:`reapproach_rt_record`) of an S8C case with a floor / retract
    event (``result.event_t_s`` relative to ``settings.start_t_s``) and its variant tag: ``rt``
    when the run's ``settings.s8.lifted_reapproach`` has the RT window on (run_S8C rev. 52).
    ``forced`` (C-S8-40): the case's :func:`forced_window` (RE1c), masked in the twist work.
    ``f_min_N`` (C-S8-41): F_min of the deferred-leg minimum FLAG."""
    res = case["result"]
    s = res.get("settings") or {}
    lr = (s.get("s8") or {}).get("lifted_reapproach") or {}
    out: dict[str, Any] = {"reapproach_variant": "rt" if lr.get("retrigger_window_s")
                           is not None else None, "rt": None}
    ev = res.get("event_t_s")
    if ev is None or not (Path(d) / "pads.npz").exists():
        return out
    with np.load(Path(d) / "pads.npz", allow_pickle=False) as z:
        pads = {k: np.asarray(z[k]) for k in ("t", "F_cyl", "F_cyl_min_interval",
                                              "F_cyl_mean_20ms", "airborne") if k in z.files}
    out["rt"] = reapproach_rt_record(_event_names(case), float(ev),
                                     float(s.get("start_t_s") or 0.0),
                                     res.get("controller_meta"), pads,
                                     _load_record(Path(d), ("u_applied",)), forced=forced,
                                     f_min_N=f_min_N)
    return out


def ml_twist_work_of_dir(d: Path) -> dict[str, Any] | None:
    """C-S8-40: the twist work (:func:`twist_work_bins`, forced window masked) of one ML episode
    folder (``job_ml_episode``: ``result.event_t_s`` engine time), for the reference-batch FLAG
    row; None without an event or the records."""
    d = Path(d)
    if not (d / "result.json").exists() or not (d / "pads.npz").exists():
        return None
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    s = res.get("settings") or {}
    t0 = float(s.get("start_t_s") or 0.0)
    t_ev = res.get("event_t_s") or res.get("branch_t_s")
    if t_ev is None:
        return None
    with np.load(d / "pads.npz", allow_pickle=False) as z:
        pads = {k: np.asarray(z[k]) for k in ("t", "F_cyl") if k in z.files}
    series = load_series(d)
    t_end = float(np.asarray(series["t"], float)[-1]) - t0 if series is not None \
        else float(np.asarray(pads["t"], float)[-1]) - t0
    fw = forced_window(res, t_end, series)
    te = float(t_ev) - t0
    return twist_work_bins(pads, _load_record(d, ("u_applied",)), float(t_ev),
                           forced=forced_rel_to_event(fw, te))


def case_engine(case) -> str | None:
    s = case["result"]["settings"]
    return (s.get("s8") or {}).get("engine") or (s.get("s7c") or {}).get("engine")


class _RigidPadParams:
    """Parameter stand-in whose L1 pad stiffness is infinite (no ``N / k_n`` term)."""

    def get(self, key: str):
        from outrigger_sim.verify import s6_control as s6

        if key == s6.KN_PER_PAD_KEY:
            return {leg: math.inf for leg in LEGS}
        raise KeyError(key)


def l2b_pads_view(pads: Mapping[str, Any]) -> dict[str, Any]:
    """C-S8-16 ③: the L2b-NSC pad record seen by the s6 item-3 helpers. The floor point is the
    contact point (rigid NSC floor, no penetration term) and, without a ground bushing (anchor
    rows NaN), the anchor is the contact point while the pad is in contact (``N > 0``), so the
    "anchor move" rows give the in-plane contact-point move."""
    out = dict(pads)
    anchor = np.asarray(pads["anchor_world"], float)
    if not np.isfinite(anchor).any():
        cp = np.array(pads["contact_point_world"], dtype=float, copy=True)
        cp[~(np.asarray(pads["N"], float) > 0.0)] = np.nan
        out["anchor_world"] = cp
    return out


def l2b_floor_point_metrics(case, m) -> None:
    """C-S8-16 ③ (spec rev. 43 213.2 #6): recompute the item-3 other-leg transient block
    (``event3``) and the C-R8 lift intervals of an L2b-NSC floor-event case with the floor point
    = contact point (``s6_control._floor_point_heights_m`` with ``k_n`` = inf; the L1
    ``N / k_n`` penetration term of the s6 judge gave 4.4-6.1 mm on the rigid NSC floor) and the
    anchor move = contact-point in-plane move. Same window and settings as the s6 block; the
    replaced values are kept under ``*_l1_formula``."""
    from outrigger_sim.verify import s6_bundle_c as bc
    from outrigger_sim.verify import s6_control as s6

    e = m.get("event3")
    pads = case.get("pads")
    if not e or "status" in e or pads is None or "transient_window" not in e:
        return
    if m.get("floor_event") is not None:  # rev. 50 fast settlement: no s6 other-leg block
        return
    view = {**case, "pads": l2b_pads_view(pads)}
    kn = np.full(4, math.inf)
    with warnings.catch_warnings():  # a leg without contact before the event: NaN anchor mean
        warnings.simplefilter("ignore", RuntimeWarning)
        new = s6.event_force_metrics(view, m["times_s"], e["transient_window"],
                                     s6.EVENT_TRANSIENT, kn)
    new["floor_point_rule"] = ("L2b-NSC: floor point = contact point, anchor = contact point "
                               "in contact (C-S8-16 ③)")
    new["rise_l1_formula_m"] = e.get("other_legs_rise_max_m")
    new["anchor_move_l1_formula_m"] = e.get("other_slip_net_window_end_m")
    m["event3"] = new
    t_ev = m.get("floor_event_t_s")
    if t_ev is not None and m.get("lift_intervals") is not None:
        m["lift_intervals"] = bc.lift_interval_metrics(view, m["times_s"], _RigidPadParams(),
                                                       t_ev)


def _external(root: Path, ext) -> dict[str, Any] | None:
    if not ext:
        return None
    d = root / ext[0] / ext[1]
    if not (d / "result.json").exists():
        return None
    case, m, pr, params = _load(d)
    sm = s8_case_metrics(case, m, params, pr)
    return sm


def _load_ref_docs(paths: Sequence[Path | None]) -> list[tuple[str, dict[str, Any]]]:
    out, seen = [], set()
    for p in paths:
        if p is None:
            continue
        f = Path(p) / "verify_S8C.json"
        if not f.exists() or str(f.resolve()) in seen:
            continue
        seen.add(str(f.resolve()))
        out.append((f"batch {Path(p).name}", json.loads(f.read_text(encoding="utf-8"))))
    return out


def _lookup_sm(cid: str, sms: Mapping[str, Any], ref_docs: Sequence[tuple[str, Mapping]]
               ) -> tuple[Mapping[str, Any] | None, str]:
    """C-S8-22 ⑤: a case's s8 metrics from this batch, else the first reference / lookup batch
    that has it."""
    if cid in sms:
        return sms[cid], f"batch {cid}"
    for label, doc in ref_docs:
        sm = (doc.get("s8_metrics") or {}).get(cid)
        if sm is not None:
            return sm, f"{label} {cid}"
    return None, f"{cid} (not found in this batch or the reference batches)"


JUDGE_REVISION_REV50 = (
    "spec rev. 50 220.6 (C-S8-33, U-S8-41..43: ① s6 floor event also = result.event settle "
    "faster than v_max (event legs settled + diagonal, U-S8-32 window), ② item 4 moving = "
    "|u_applied| > 1e-6 m/s, ③ injected-leg rod fallback within [fault, +2 T] expected, ④ "
    "C-S8-29 guard_cap_s from cmp_guard_u (push_cap_s = former issued_u count), h* / h_a / R_ub "
    "per lock window, F1 calibrated record without the faulty leg after the fault, ⑤ C-S8-24 "
    "round-start lower bounds vs 24.41 kN)")
JUDGE_REVISION_REV51 = (
    "spec rev. 51 225 (C-S8-34, U-S8-44 / 47: ① ML-0 FAULT split by cause, stroke-end FAULT = "
    "U-S8-44 protective stop row, ② event-leg row does not repeat an ML-0 FAULT, ③ ML-2 rod "
    "fallback with the applied commands and plant lock, ④ ML tags fault_tail / "
    "plant_rod_collapse / reapproach_pingpong + H-S8-4 12.6 plant_release_rod_step and "
    "collapse windows to re-contact + 0.1 s)")
JUDGE_REVISION_REV52 = (
    "spec rev. 52 232 / 230 (C-S8-37, U-S8-51: item 9 default = corrected reading + 0.5 kN "
    "where pad N < 1.5 kN, raw reading record rows, F_s - m g ceiling sensitivity rows; "
    "RT record rows (runs / re-triggers / deferred) and the twist-work row <= +20 J per 0.5 s "
    "bin after event + 1.5 s, judged for RT-variant runs)")
JUDGE_REVISION_REV54 = (
    "spec rev. 54 248.3 / 249 / 251 (C-S8-40: twist-work row = recurrence ban, forced window "
    "[start, done_s + 0.1 s] masked, clusters of 0.5 s bins > +20 J after event + 1.5 s <= 1, "
    "judged for RT-variant runs, records: rev. 52 bin max / masked bin max / largest cluster, "
    "reference-batch FLAG > +20 J; item 9 default reading + delta_i = min(0.5 kN, 2 F_s,i) on "
    "L2b-NSC legs with F_s,i > 0 where pad N < 1.5 kN, all-apply +0.5 kN = sensitivity rows)")
JUDGE_REVISION_REV55 = (
    "spec rev. 54 260.5 / 261 / 264 for rev. 55 (C-S8-41, U-S8-56 (a) / U-S8-57 (a): ML-0 gate "
    "row 'no rod-pressure fallback without a sensor-fault injection' = 0; RT record row 'true "
    "minimum of the deferred leg, deferral .. next start + 0.3 s, < F_min = FLAG'; the summary "
    "carries the ML-1 rod fallback run count)")
JUDGE_REVISION_REV56 = (
    "spec rev. 55 267 / 269.3 for rev. 56 (C-S8-42: deferred-leg window end = min(next start, "
    "deferral + T_o) + 0.3 s cut at the run end, T_o from the controller meta (0.8 s default), "
    "overlapping windows of a leg merged, window_rule 'spec rev. 55 267'; per deferred leg the "
    "event + 0..4 s judged minimum / time below F_min / airborne time vs the reference batch "
    "(768 / original MLJ), FLAG text > 0.5 kN or > 0.1 s; record rows PROBE -> LEVEL returns and "
    "re-READY vs the reference (269.2 #2 / #3, criterion_met, control judges))")
MLJ_GROUP = "MLJ"
"""``run_S8C.py`` judged cases of the main ML batch (U-S8-32 / 35, C-S8-24, C-S8-29)."""
GUARD_CAP_M_S = 2.5e-3
"""Guard command cap (spec rev. 48 218.10; ASSUMPTION used only for the C-S8-29 record)."""
FALLBACK_BAND_DEFAULT_N = 13000.0
"""``F_band`` of the h* formula when the controller meta has no
``two_pressure.settings.fallback_min_band_N`` (spec 218.10)."""
LOCK_LOG_KEYS = ("two_pressure.fallback_lock_log", "two_pressure.fallback_lock_current")


def bc_load_r8_series(case_dir: Path) -> dict[str, np.ndarray] | None:
    """``r8_series.npz`` of a case (``s6_bundle_c.load_r8_series``)."""
    from outrigger_sim.verify import s6_bundle_c as bc

    return bc.load_r8_series(Path(case_dir))


def h_star_Pa(f_min_N: float, f_band_N: float, start_Pa: float, ratio_bound: float,
              anchor_head_Pa: float, a_p_m2: float, a_ann_m2: float,
              guard_margin_N: float = D8_MARGIN_N) -> float:
    """Spec 218.10 / 219.4: head pressure at which the fallback lower bound of a locked window
    reaches ``F_min + 5 kN`` (the guard / re-approach stop):
    ``h* = (F_min + 5 kN + F_band + M A_ann + R_ub h_a A_ann) / (A_p + R_ub A_ann)``
    (``M`` = window start rod estimate, ``R_ub`` = rod-to-head ratio bound, ``h_a`` = anchor
    head). Pa."""
    return ((f_min_N + guard_margin_N + f_band_N + start_Pa * a_ann_m2
             + ratio_bound * anchor_head_Pa * a_ann_m2) / (a_p_m2 + ratio_bound * a_ann_m2))


def requested_probe_round_lower(probes: Sequence[Sequence[Mapping[str, Any]]],
                                series: Mapping[str, np.ndarray], t0: float,
                                accepted_t_s: float, f_min_N: float,
                                margin_N: float = LOW_PROBE_MARGIN_N) -> dict[str, Any]:
    """Spec rev. 50 220.6 ⑤ (C-S8-24 record, U-S8-41): per probe round that starts at or after
    the accepted probe request, the lower bound ``F_hat_cal - F_band,i``
    (:func:`lower_estimate_series`) of every leg at the round start (last 10 Hz row at or before
    the first move start, the R45-4 rule of :func:`low_load_probe_records`) against the R45-4
    threshold ``F_min + 15 kN``. Times relative to ``t0``; kN."""
    lower, _nom, src = lower_estimate_series(series)
    tc = np.asarray(series["t"], float) - t0
    rounds = []
    for i, rnd in enumerate(probes or []):
        starts = [float(r["t_move_start_s"]) - t0 for r in rnd
                  if isinstance(r, Mapping) and isinstance(r.get("t_move_start_s"), int | float)]
        if not starts or tc.size == 0 or min(starts) < accepted_t_s - 1e-6:
            continue
        k0 = int(np.clip(np.searchsorted(tc, min(starts) + 1e-9, side="right") - 1, 0,
                         tc.size - 1))
        rounds.append({"round": i, "t_round_start_s": min(starts), "t_row_s": float(tc[k0]),
                       "lower_kN": {LEGS[j]: float(lower[k0, j]) / 1e3 for j in range(4)}})
    thr = (f_min_N + margin_N) / 1e3
    mins = [min(r["lower_kN"].values()) for r in rounds]
    return {"accepted_t_s": accepted_t_s, "threshold_kN": thr, "rounds": rounds,
            "min_lower_kN": None if not mins else min(mins),
            "below_threshold": bool(mins) and min(mins) < thr, "lower_source": src["lower"]}


def lock_window_h_star(fallback_meta: Mapping[str, Any], leg: str, params,
                       pads: Mapping[str, Any] | None, tp_rel_s: np.ndarray, f_min_N: float,
                       t0: float) -> list[dict[str, Any]]:
    """Spec rev. 50 220.6 ④ (C-S8-29 record): per P-S8-13 lock window of the faulty leg
    (controller meta :data:`LOCK_LOG_KEYS`) ``h*`` (:func:`h_star_Pa`), ``h_a``, ``R_ub``, the
    lower bound at ``h_a`` (``h_a A_p - M A_ann - F_band``) and the true head at the window start
    (the end of the push that locked) minus ``h*``. Window times are taken as relative to ``t0``
    (minus ``t0`` when beyond the pad record). Areas: :func:`cylinder_areas_m2`. bar / kN."""
    wins = []
    for key in LOCK_LOG_KEYS:
        wins.extend(w for w in (fallback_meta.get(key) or []) if isinstance(w, Mapping))
    wins = [w for w in wins if w.get("leg") == leg]
    if not wins:
        return []
    a_p, a_a, _src = cylinder_areas_m2(params, pads)
    j = LEGS.index(leg)
    band = fallback_meta.get("two_pressure.settings.fallback_min_band_N")
    band = FALLBACK_BAND_DEFAULT_N if band is None else float(band)
    tp = np.asarray(tp_rel_s, float)
    hp = None if pads is None else np.asarray(pads["head_pressure"], float)[:, j]
    out = []
    for w in sorted(wins, key=lambda x: float(x.get("t_start_s") or 0.0)):
        t_s = float(w["t_start_s"])
        if tp.size and t_s > tp[-1] + 1e-6:
            t_s -= t0
        r, ha, m0 = float(w["ratio_bound"]), float(w["anchor_head_Pa"]), float(w["start_Pa"])
        hs = h_star_Pa(f_min_N, band, m0, r, ha, a_p[j], a_a[j])
        rec = {"t_start_s": t_s, "window_end_s": None if w.get("window_end_s") is None
               else float(w["window_end_s"]) - (float(w["t_start_s"]) - t_s),
               "stroke_m": w.get("stroke_window_max_m"), "R_ub": r,
               "h_a_bar": ha / 1e5, "M_bar": m0 / 1e5, "h_star_bar": hs / 1e5,
               "h_star_below_h_a": bool(hs < ha),
               "lower_at_h_a_kN": (ha * a_p[j] - m0 * a_a[j] - band) / 1e3,
               "F_band_kN": band / 1e3, "source": w.get("source")}
        if hp is not None and tp.size:
            i = int(np.clip(np.searchsorted(tp, t_s), 0, tp.size - 1))
            rec["head_at_start_bar"] = float(hp[i]) / 1e5
            rec["head_at_start_minus_h_star_bar"] = rec["head_at_start_bar"] - hs / 1e5
        out.append(rec)
    return out



def mlj_case_metrics(case: Mapping[str, Any], sm: Mapping[str, Any], params) -> dict[str, Any]:
    """Values of a judged case of the main ML batch (group :data:`MLJ_GROUP`):

    * settlement event: :func:`settle_lift_split` (U-S8-32 rows; FAULT from the phases);
    * rod-sensor fault (C-S8-29, spec rev. 48 218.10 record): rod fallback events of the
      faulty leg, its pushing / guard-cap time after the fallback, its true head maximum and
      the head at the end of its last pushing stretch, the minimum true force of the other legs
      after the fault, the controller meta entries on the fallback;
    * probe request (C-S8-24): the ``probe_request`` record and the R45-4 rows of the run."""
    res = case["result"]
    s = res["settings"]
    s8 = s.get("s8") or {}
    ev = s8.get("event_spec") or {}
    t0 = float(s.get("start_t_s") or 0.0)
    pads = case.get("pads")
    out: dict[str, Any] = {"event": s8.get("event"), "event_spec": ev}
    phases = res.get("phases") or []
    fault_t = fault_entry_s(phases)  # C-S8-68 ①: FAULT_REGROUND or FAULT, the first
    out["fault_t_s"] = fault_t
    t_ev = res.get("event_t_s")
    if pads is not None and t_ev is not None and ev.get("kind") == "settle" \
            and "airborne" in pads and "ball_centre_world" in pads:
        t3, t3_top = _t3_of_level(s.get("level"))
        sp = settle_lift_split(np.asarray(pads["t"], float) - t0, pads["airborne"],
                               np.asarray(pads["ball_centre_world"], float)[:, :, 2],
                               float(t_ev), ev["leg"], float(ev["depth_m"]),
                               float(ev["ramp_s"]), t3_s=t3, fault_t_s=fault_t)
        sp["T3_from_top_level"] = t3_top
        out["u_s8_32"] = sp
    rf = ev.get("rod_fault")
    if rf and pads is not None:
        names = _event_names(case)
        leg = rf["leg"]
        j = LEGS.index(leg)
        fb = [e for e in rod_fallback_events(names, None) if e["leg"] == leg]
        t_f = res.get("rod_fault_t_s")
        series = load_series(Path(case["dir"])) if case.get("dir") else None
        rec: dict[str, Any] = {"leg": leg, "fault": rf.get("fault"), "fault_t_s": t_f,
                               "fallback_events": fb}
        tp = np.asarray(pads["t"], float) - t0
        if t_f is not None:
            after = tp >= float(t_f) - 1e-9
            fmin = judged_force_min(pads)
            others = [k for k in range(4) if k != j]
            sel = fmin[after][:, others]
            rec["others_min_true_kN"] = None if not sel.size else float(sel.min()) / 1e3
            hp = np.asarray(pads["head_pressure"], float)[after, j]
            rec["head_max_bar"] = None if not hp.size else float(hp.max()) / 1e5
        if series is not None and fb:
            tc = np.asarray(series["t"], float) - t0
            u = np.asarray(series["issued_u"], float)[:, j]
            post = tc >= fb[0]["t_s"] - 1e-9
            dt = float(np.median(np.diff(tc))) if tc.size > 1 else 0.1
            push = post & (u > 1e-4)
            rec["pushing_s"] = float(push.sum() * dt)
            # spec rev. 50 220.6 ④: the former ``issued_u`` count is the push-at-cap time
            rec["push_cap_s"] = float((post & (u >= 0.95 * GUARD_CAP_M_S)).sum() * dt)
            r8 = bc_load_r8_series(Path(case["dir"]))
            if r8 is not None and "cmp_guard_u" in r8:
                g = np.asarray(r8["cmp_guard_u"], float)
                tg = np.asarray(r8["t"], float) - t0
                gpost = tg >= fb[0]["t_s"] - 1e-9
                dtg = float(np.median(np.diff(tg))) if tg.size > 1 else 0.1
                cap = gpost[:, None] & (g >= 0.95 * GUARD_CAP_M_S)
                rec["guard_cap_s"] = float(cap[:, j].sum() * dtg)
                rec["guard_cap_s_per_leg"] = {LEGS[i]: float(cap[:, i].sum() * dtg)
                                              for i in range(4)}
                rec["guard_nonzero_s_per_leg"] = {
                    LEGS[i]: float((gpost & (np.abs(g[:, i]) > 1e-9)).sum() * dtg)
                    for i in range(4)}
                rec["guard_cap_rule"] = ("r8_series cmp_guard_u >= 0.95 x 2.5 mm/s after the "
                                         "fallback (spec rev. 50 220.6 ④); push_cap_s = the "
                                         "former issued_u count")
            else:
                rec["guard_cap_s"] = None
                rec["guard_cap_rule"] = "no r8_series cmp_guard_u: not measured"
            runs = _runs(push)
            if runs:
                k_end = runs[-1][1]
                hp_all = np.asarray(pads["head_pressure"], float)[:, j]
                i = int(np.clip(np.searchsorted(tp, tc[k_end]), 0, tp.size - 1))
                rec["head_at_last_push_end_bar"] = float(hp_all[i]) / 1e5
                rec["last_push_end_s"] = float(tc[k_end])
        meta = res.get("controller_meta") or {}
        rec["controller_fallback_meta"] = {k: v for k, v in _flat_items(meta)
                                           if "fallback" in k or "h_star" in k}
        rec["lock_windows"] = lock_window_h_star(rec["controller_fallback_meta"], leg, params,
                                                 pads, tp, float(sm["F_min_N"]), t0)
        if rec["lock_windows"] and rec.get("last_push_end_s") is not None:
            near = min(rec["lock_windows"],
                       key=lambda w: abs(w["t_start_s"] - rec["last_push_end_s"]))
            rec["head_at_last_push_end_minus_h_star_bar"] = (
                rec["head_at_last_push_end_bar"] - near["h_star_bar"])
            rec["last_push_lock_window_t_s"] = near["t_start_s"]
        out["rod_fault"] = rec
    if ev.get("probe_after"):
        out["probe_request"] = res.get("probe_request")
        out["R45_4_count"] = len(sm.get("R45_4") or [])
        # spec rev. 50 220.6 ⑤ (U-S8-41): round-start lower bounds of the requested probe
        series8 = load_series(Path(case["dir"])) if case.get("dir") else None
        acc = (res.get("probe_request") or {}).get("accepted_t_s")
        out["requested_probe_rounds"] = None if series8 is None or acc is None else \
            requested_probe_round_lower(case.get("probes") or [], series8, t0, float(acc),
                                        float(sm["F_min_N"]))
    if case.get("dir") is not None:  # C-S8-32: D1'' ratios (FS24_Fs0 = the D1'' worst side)
        out["fs_mean_kN"] = run_fs_mean_kN(pads, s)
        out["d1pp"] = d1pp_step_ratios(Path(case["dir"]), params, settings=s, pads=pads)
    if ev.get(HEAD_FAULT_KEY):  # C-S8-68: G4 head fault + lifted leg (323.7)
        out["g4h"] = g4_of_case(case, float(sm["F_min_N"]), params)
    return out


def _flat_items(tree: Any, prefix: str = "", depth: int = 0) -> list[tuple[str, Any]]:
    """``(dotted key, scalar or short list)`` items of a nested meta (depth <= 5)."""
    out: list[tuple[str, Any]] = []
    if depth > 5:
        return out
    if isinstance(tree, Mapping):
        for k, v in tree.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, Mapping):
                out.extend(_flat_items(v, p, depth + 1))
            else:
                out.append((p, v if not isinstance(v, list) or len(v) <= 8 else v[:8]))
    return out


def mlj_rows(sms: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Rows of the judged cases of the main ML batch (:func:`mlj_case_metrics` in
    ``sm['mlj']``): U-S8-32 adjacent / event-leg rows (front fast settlement), C-S8-24 R45-4
    record, C-S8-29 rod-fault record (spec rev. 48 218.10)."""
    rows: list[dict[str, Any]] = []
    for cid, sm in sorted(sms.items()):
        mj = sm.get("mlj")
        if not mj:
            continue
        if mj.get("u_s8_32") is not None and mj["event"] == "FS24":
            rows.extend(u_s8_32_rows(cid, mj["u_s8_32"], label="MLJ"))
        elif mj.get("u_s8_32") is not None:
            rows.extend(r | {"kind": "record", "passed": None}
                        for r in u_s8_32_rows(cid, mj["u_s8_32"], label="MLJ (record)"))
        if mj.get("g4h") is not None:  # C-S8-68: a head fault must FAULT; G4 rows instead
            rows.extend(g4_rows(cid, mj["g4h"]))
        else:
            rows.append(_row("MLJ FAULT 0 (a rod-sensor fault falls back, it does not FAULT)",
                             cid, mj.get("fault_t_s"), None, mj.get("fault_t_s") is None,
                             "FAULT entry time [s] or None"))
        if "probe_request" in mj:
            pr = mj.get("probe_request") or {}
            rq = mj.get("requested_probe_rounds") or {}
            rnds = rq.get("rounds") or []
            lows = "; ".join(
                f"r{r['round']} {r['t_round_start_s']:.2f} s "
                + "/".join(f"{v:.1f}" for v in r["lower_kN"].values()) for r in rnds)
            why = ("no round started after the accepted request" if not rnds else
                   (f"round-start lower bound FL/FR/RL/RR {lows} kN; minimum "
                    f"{rq['min_lower_kN']:.2f} kN "
                    + ("< " if rq["below_threshold"] else ">= ")
                    + f"R45-4 threshold F_min + 15 kN = {rq['threshold_kN']:.2f} kN"))
            rows.append(_row("C-S8-24 R45-4 dedicated case: probe requested after the re-READY "
                             "and R45-4 low-load probes (record; U-S8-41: dedicated search "
                             "closed, record row kept)", cid,
                             {"accepted_t_s": pr.get("accepted_t_s"),
                              "attempts": pr.get("attempts"), "R45_4": mj.get("R45_4_count"),
                              "round_start_lower_min_kN": rq.get("min_lower_kN"),
                              "threshold_kN": rq.get("threshold_kN")},
                             None, None,
                             f"R45-4 rows of the run carry the F2 values; {why} (spec rev. 50 "
                             "220.4 / 220.6 ⑤: a closed-loop READY probe does not start at a "
                             "low load)", kind="record", probe_request=pr,
                             requested_probe_rounds=rq))
        if mj.get("rod_fault"):
            rf = mj["rod_fault"]
            lw = rf.get("lock_windows") or []
            lw_txt = "; ".join(
                f"{w['t_start_s']:.2f} s h* {w['h_star_bar']:.1f} / h_a {w['h_a_bar']:.1f} bar, "
                f"R_ub {w['R_ub']:.2f}, head at start - h* "
                + _fmt(w.get("head_at_start_minus_h_star_bar"), "+.1f") + " bar" for w in lw)
            rows.append(_row("C-S8-29 rod-sensor fault + G4 (spec rev. 48 218.10 / rev. 50 220.6 "
                             "④, record): fallback, guard-cap time (cmp_guard_u), push-at-cap "
                             "time, stopped head vs h* per lock window, other legs' min true "
                             "force, head max", cid,
                             {k: rf.get(k) for k in ("pushing_s", "guard_cap_s", "push_cap_s",
                                                     "head_at_last_push_end_bar",
                                                     "head_at_last_push_end_minus_h_star_bar",
                                                     "head_max_bar", "others_min_true_kN")},
                             None, None,
                             f"leg {rf['leg']} {rf.get('fault')} from {rf.get('fault_t_s')} s; "
                             f"fallback {[(e['t_s'], e['reason']) for e in rf['fallback_events']]}"
                             f"; FAULT {mj.get('fault_t_s')}; guard cap per leg "
                             f"{rf.get('guard_cap_s_per_leg')} s ({rf.get('guard_cap_rule')}); "
                             f"lock windows {len(lw)}: {lw_txt or '-'}; "
                             f"all h* < h_a: {all(w['h_star_below_h_a'] for w in lw) if lw else None}",
                             kind="record", rod_fault=rf, lock_windows=lw))
            n_fb = len(rf["fallback_events"])
            rows.append(_row("C-S8-29 the injected rod fault is caught (fallback on the faulty "
                             "leg)", cid, n_fb, ">= 1", n_fb >= 1,
                             "U-S8-33: no deficit cap; guard / re-approach stop by themselves"))
    d1 = {cid: sm["mlj"] for cid, sm in sms.items() if (sm.get("mlj") or {}).get("d1pp")}
    if d1:
        rows.extend(d1pp_ratio_rows(d1, label="MLJ"))
    return rows


# --- C-S8-72 (spec rev. 67 345.2): floor events on any leg, LEVEL time or READY + 5 s --------

G1_GROUP = "G1"
G1_END_ATT_WINDOW_S = 1.0
G1_ATT_TOL_DEG = 0.2
"""345.2 end attitude: READY and the last-1 s mean true deck |roll|, |pitch| <= 0.2 deg (342.3;
target 0 on the flat floor)."""
G1_U58_WINDOW_BAR = 350.0
G1_U58_OUTSIDE_BAR = 180.0
"""345.2 U58 (existing definition, spec 62.2): head ``F_cyl / A_p`` in any state inside the
physical window <= 350 bar; extension samples (``u_applied`` > 1e-6 m/s) outside it <= 180 bar.
A slow event (no window) judges every extension sample and the whole-run any-state peak."""
G1_TWIST_SIGN = {"FL": 1, "FR": -1, "RL": -1, "RR": 1}
"""Twist sign of a re-approach leg (``RT_TWIST_N``) for the sign-change record."""
G1_HARNESS_FILES = ("r67_screen_P.json", "r67_screen_E.json", "r67_screen_top_phase4.json")
G1_HARNESS_DIR = Path("06_analysis/02_control/s8/rev67")
G1_FMIN_MEAN_S = 0.5
"""U-S8-74 (a) (spec rev. 68 354.1): length of the trailing moving mean of the fast-event F_min
row; only full windows ending at >= W + 0.5 s count (the same computation as G4-4, 340.2)."""
G1_FMIN_TOL_KN = 1e-6
"""354.2: the fast-event mean passes at mean05 minimum >= F_min - 1e-6 kN."""
U75_FLAG = "U-S8-75 (b) exception"
U75_LIFT_MAX_S = 0.1
U75_GAP_MAX_M = 0.0005
"""U-S8-75 = (b) (spec rev. 68 357.3, ASSUMPTION 353.3): inside the scope the adjacent-leg lift
after the window end passes when its sum <= 0.1 s and its gap <= 0.5 mm."""
U75_FS_BELOW_KN = 2.0
U75_EVENT_LEGS = ("FL", "FR")
U75_LEVEL = "top"
"""357.3 scope: fast event (settle speed > v_max) on a front leg, top level, case F_s < 2 kN."""
U75_RULE = ("U-S8-75 = (b) (spec rev. 68 357.3): fast event (settle speed > v_max) on a front "
            "leg (FL / FR), top level, case F_s < 2 kN: the U57 adjacent lift outside the "
            "window and the U-S8-74 F_min (b) lift after the window end pass when the "
            "adjacent-leg lift after the window sums to <= 0.1 s with a gap <= 0.5 mm (FLAG "
            "'U-S8-75 (b) exception'); event legs must not lift after the window end; the "
            "0.5 s mean (a) is unchanged; outside the scope unchanged")
G1_FMIN_RULE = ("U-S8-74 (a) (spec rev. 68 354.1, replaces the 345.2 fast-event F_min row): "
                "over [W end, run end] every leg (a) the minimum of the trailing 0.5 s moving "
                "mean of the S8-A2 judged force (full windows ending at >= W end + 0.5 s) >= "
                "F_min AND (b) no pad lift (airborne = 20 ms pad normal <= 0: 0 samples; old "
                "records without airborne: judged force > 0, airborne_source "
                "force_sign_fallback; " + U75_RULE + "); not judgeable when the run ends "
                "before W end + 0.5 s; the "
                "1 ms instantaneous minimum is a record row (FLAG when < F_min) with the time "
                "below F_min, the longest run below F_min, the time below 0 and the lift time; "
                "slow event (G4, #10): 1 ms minimum after the event >= F_min (unchanged)")
G1_RULE = ("C-S8-72 (spec rev. 67 345.2): U-S8-32 event legs (settled + diagonal) cumulative "
           "lift <= 1.8 s, last re-contact <= event + 3.0 s, FAULT 0 and U57 adjacent (#1-9, 11; "
           "outside-window part with the U-S8-75 (b) exception); "
           "U58 window <= 350 / outside extension <= 180 bar (#1-11); F_min per "
           + G1_FMIN_RULE + "; end READY + last "
           "1 s mean |att| <= 0.2 deg; recurrence ban 248.3 (twist work clusters <= 1); "
           "phase_mismatch (controller phase at the event start other than the expected one) = "
           "not judgeable")
G1_FMIN_ITEM = ("C-S8-72 F_min U-S8-74: 0.5 s moving mean >= F_min and no pad lift after the "
                "window end (fast); 1 ms min >= F_min (slow)")
G1_FMIN_RECORD_ITEM = "C-S8-72 F_min 1 ms instantaneous (record, U-S8-74)"


def _g1_harness_runs(root: Path, harness_dir: Path | None) -> list[dict[str, Any]]:
    """Every run of the rev. 67 screen JSONs (``results[].runs[]`` + the parent's level / F_s /
    timing / leg); empty when the files are absent."""
    d = Path(harness_dir) if harness_dir is not None else Path(root) / G1_HARNESS_DIR
    out: list[dict[str, Any]] = []
    for name in G1_HARNESS_FILES:
        p = d / name
        if not p.exists():
            continue
        doc = json.loads(p.read_text(encoding="utf-8"))
        for res in doc.get("results") or []:
            for r in res.get("runs") or []:
                out.append({**r, "level": res.get("level"), "fs_kN": res.get("fs_kN"),
                            "timing": res.get("timing"), "leg": res.get("leg"),
                            "file": name})
    return out


def g1_harness_match(runs: Sequence[Mapping[str, Any]], *, base: str, leg: str, level: str,
                     fs_kN: float, timing: str, offset_s: float) -> dict[str, Any] | None:
    """The harness run of the same event / leg / level / F_s / timing / phase offset (first file
    holding it), with the values of the 228.5-style comparison."""
    for r in runs:
        if (r.get("event") == base and r.get("leg") == leg and r.get("level") == level
                and abs(float(r.get("fs_kN") or 0.0) - fs_kN) < 1e-9
                and r.get("timing") == timing
                and abs(float(r.get("offset_s") or 0.0) - offset_s) < 1e-9):
            keys = ("pair_union_s", "pair_last_touch_s", "W_end_s", "adj_lift_sum_W_s",
                    "adj_max_gap_W_mm", "adj_lift_outside_W_s", "min_F_after_W_kN",
                    "min_F_after_event_kN", "max_att_change_deg", "n_late_starts",
                    "sign_changes", "t_ready_back_s", "pass", "gates")
            return {"file": r["file"], **{k: r.get(k) for k in keys},
                    "reapproach_starts": (r.get("reapproach_starts") or [])[:30],
                    "n_bundles": (r.get("twist") or {}).get("n_bundles")}
    return None


def _longest_true_run_s(mask: np.ndarray, dt_s: float) -> float:
    """Length [s] of the longest run of consecutive True samples of a 1-D mask."""
    edges = np.diff(np.concatenate(([0], np.asarray(mask, np.int8), [0])))
    starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    return float((ends - starts).max() * dt_s) if starts.size else 0.0


def g1_u75_scope(*, is_fast: bool, settle_speed_mm_s: float | None, v_max_m_s: float,
                 event_leg: str | None, level: str | None, fs_kN: float) -> bool:
    """Whether a C-S8-72 case lies inside the U-S8-75 (b) exception scope (:data:`U75_RULE`).

    Args:
        is_fast: the case is a fast event (``event_spec.fine``).
        settle_speed_mm_s: settlement depth / ramp time [mm/s]; None for a step settlement.
        v_max_m_s: actuator maximum speed v_max [m/s].
        event_leg: settled leg.
        level: auger level of the case.
        fs_kN: case seal friction F_s (front value) [kN].

    Returns:
        True when every scope condition of spec 357.3 holds.
    """
    settles_faster_than_v_max = (settle_speed_mm_s is None
                                 or settle_speed_mm_s > v_max_m_s * 1e3)
    return bool(is_fast and settles_faster_than_v_max and event_leg in U75_EVENT_LEGS
                and level == U75_LEVEL and fs_kN < U75_FS_BELOW_KN)


def adjacent_lifts_after_window(tp: np.ndarray, airborne: np.ndarray, ball_z_m: np.ndarray,
                                w_end_s: float,
                                adjacent_legs: Sequence[str]) -> list[dict[str, Any]]:
    """Pad lifts of the adjacent legs that reach the window end W or start after it.

    Args:
        tp: 1 ms pad record times [s] (same clock as ``w_end_s``).
        airborne: pad lift flags per leg, shape (n, 4).
        ball_z_m: pad ball-centre world z per leg, shape (n, 4) [m].
        w_end_s: end of the U-S8-32 window W [s].
        adjacent_legs: the two adjacent legs of the settlement.

    Returns:
        One dict per lift: ``leg``, ``start_s``, ``duration_s`` (whole lift, as
        :func:`settle_lift_split`), ``after_window_s`` (samples at >= W),
        ``starts_after_window`` (a U57 "outside" lift) and ``gap_m`` (pad ball rise since the
        lift start; adjacent legs stand on the fixed floor).
    """
    t = np.asarray(tp, float)
    dt = float(np.median(np.diff(t))) if t.size > 1 else 0.0
    lifted = np.asarray(airborne, bool)
    ball_z = np.asarray(ball_z_m, float)
    lifts: list[dict[str, Any]] = []
    for leg in adjacent_legs:
        j = LEGS.index(leg)
        for first, last in _runs(lifted[:, j]):
            if t[last] < w_end_s - 1e-9:
                continue
            span = slice(first, last + 1)
            lifts.append({
                "leg": leg, "start_s": float(t[first]),
                "duration_s": float(t[last] - t[first] + dt),
                "after_window_s": float((t[span] >= w_end_s - 1e-9).sum() * dt),
                "starts_after_window": bool(t[first] > w_end_s + 1e-12),
                "gap_m": float((ball_z[span, j] - ball_z[first, j]).max())})
    return lifts


def _u75_within_limits(lift_s: float, gap_m: float) -> bool:
    return bool(lift_s <= U75_LIFT_MAX_S + 1e-9 and gap_m <= U75_GAP_MAX_M + 1e-12)


def g1_u75_u57_exception(split: Mapping[str, Any], lifts: Sequence[Mapping[str, Any]],
                         in_scope: bool) -> dict[str, Any]:
    """U-S8-75 (b) for the U57 row: the adjacent lift outside the window passes inside the scope
    when it sums to <= 0.1 s with a gap <= 0.5 mm and the in-window part passes.

    Args:
        split: :func:`settle_lift_split` result of the case.
        lifts: :func:`adjacent_lifts_after_window` result of the case.
        in_scope: :func:`g1_u75_scope` result of the case.

    Returns:
        Record dict; ``applied`` True when the exception turns the U57 row into a pass.
    """
    outside = [lift for lift in lifts if lift["starts_after_window"]]
    outside_s = float(split["adjacent_outside_window_s"])
    gap_m = max((lift["gap_m"] for lift in outside), default=0.0)
    inside_ok = bool(split["adjacent_sum_s"] <= U57_LIFT_SUM_S + 1e-9
                     and split["adjacent_gap_max_m"] <= U57_GAP_M + 1e-12)
    within = _u75_within_limits(outside_s, gap_m)
    return {"in_scope": bool(in_scope), "outside_s": outside_s, "outside_gap_max_m": gap_m,
            "within_limits": within, "inside_window_ok": inside_ok,
            "applied": bool(in_scope and inside_ok and within and outside_s > 0.0),
            "lifts": outside, "rule": U75_RULE}


def g1_u75_fmin_exception(fmin: Mapping[str, Any], lifts: Sequence[Mapping[str, Any]],
                          event_legs: Sequence[str], in_scope: bool) -> dict[str, Any]:
    """U-S8-75 (b) for the U-S8-74 F_min (b) part: the pad lift after the window end passes
    inside the scope when only adjacent legs lift, for <= 0.1 s in sum with a gap <= 0.5 mm,
    and the 0.5 s mean part (a) passes.

    Args:
        fmin: :func:`g1_fmin_after_window` result (status ``judged``).
        lifts: :func:`adjacent_lifts_after_window` result of the case.
        event_legs: settled leg and its diagonal.
        in_scope: :func:`g1_u75_scope` result of the case.

    Returns:
        Record dict; ``applied`` True when the exception turns the F_min row into a pass.
    """
    lift_per_leg = fmin["airborne_s"]
    event_lift_s = float(sum(lift_per_leg[leg] for leg in event_legs))
    adjacent_lift_s = float(fmin["airborne_total_s"]) - event_lift_s
    gap_m = max((lift["gap_m"] for lift in lifts if lift["after_window_s"] > 0.0),
                default=0.0)
    mean_ok = bool(fmin["mean05_min_all_kN"] >= fmin["F_min_kN"] - G1_FMIN_TOL_KN)
    within = bool(event_lift_s == 0.0 and _u75_within_limits(adjacent_lift_s, gap_m))
    return {"in_scope": bool(in_scope), "event_leg_lift_s": event_lift_s,
            "adjacent_lift_s": adjacent_lift_s, "gap_max_m": gap_m, "mean_ok": mean_ok,
            "within_limits": within,
            "applied": bool(in_scope and mean_ok and within and adjacent_lift_s > 0.0),
            "rule": U75_RULE}


def _g1_apply_u75(split: dict[str, Any], fmin: dict[str, Any],
                  lifts: Sequence[Mapping[str, Any]], in_scope: bool) -> None:
    """Attach the U-S8-75 (b) records to a fast case with an adjacent lift outside / after the
    window and flip the U57 / F_min verdicts where the exception applies. Cases without such a
    lift are left untouched."""
    if split["adjacent_outside_window_s"] > 0.0:
        exception = g1_u75_u57_exception(split, lifts, in_scope)
        split["u75_exception"] = exception
        if exception["applied"]:
            split["u57_pass_without_u75"] = split["u57_pass"]
            split["u57_pass"] = True
    if fmin.get("status") == "judged" and not fmin["no_lift"]:
        exception = g1_u75_fmin_exception(fmin, lifts, split["event_legs"], in_scope)
        fmin["u75_exception"] = exception
        if exception["applied"]:
            fmin["passed_without_u75"] = fmin["passed"]
            fmin["passed"] = True


def g1_fmin_after_window(tp: np.ndarray, judged_force_N: np.ndarray,
                         airborne: np.ndarray | None, w_end_s: float,
                         f_min_N: float) -> dict[str, Any]:
    """U-S8-74 (a) fast-event F_min values over [``w_end_s``, run end] (:data:`G1_FMIN_RULE`).

    Args:
        tp: 1 ms pad record times relative to the run start [s].
        judged_force_N: S8-A2 judged force per leg, shape (n, 4) [N].
        airborne: pad lift flags per leg, shape (n, 4); None for old records without the
            field (lift is then taken as judged force <= 0, ``force_sign_fallback``).
        w_end_s: end of the U-S8-32 window W [s].
        f_min_N: F_min [N].

    Returns:
        Per-leg 0.5 s moving-mean minimum, lift time, the 1 ms instantaneous record columns,
        ``status`` (judged / not_judgeable) and ``passed`` (None when not judgeable). kN out.
    """
    tp = np.asarray(tp, float)
    force = np.asarray(judged_force_N, float)
    if airborne is None:
        lifted, source = force <= 0.0, "force_sign_fallback"
    else:
        lifted, source = np.asarray(airborne, bool), "pads.airborne"
    after = tp >= w_end_s - 1e-9
    f_min_kN = f_min_N / 1e3
    out: dict[str, Any] = {"from_s": w_end_s, "mean05_from_s": w_end_s + G1_FMIN_MEAN_S,
                           "F_min_kN": f_min_kN, "airborne_source": source,
                           "rule": G1_FMIN_RULE, "status": "not_judgeable", "passed": None}
    if not after.any():
        out["reason"] = "no 1 ms sample after the window end"
        return out
    dt = _period(tp)
    sel = force[after]
    k, j = np.unravel_index(int(np.argmin(sel)), sel.shape)
    below = sel < f_min_N
    out.update(
        instant_min_kN=float(sel[k, j]) / 1e3, instant_leg=LEGS[j],
        instant_t_s=float(tp[after][k]),
        instant_per_leg_kN={LEGS[i]: float(sel[:, i].min()) / 1e3 for i in range(4)},
        instant_below_F_min=bool(sel[k, j] < f_min_N),
        below_F_min_s={LEGS[i]: float(below[:, i].sum() * dt) for i in range(4)},
        longest_below_s={LEGS[i]: _longest_true_run_s(below[:, i], dt) for i in range(4)},
        below_zero_s={LEGS[i]: float((sel[:, i] < 0.0).sum() * dt) for i in range(4)},
        airborne_s={LEGS[i]: float(lifted[after, i].sum() * dt) for i in range(4)})
    out["airborne_total_s"] = float(sum(out["airborne_s"].values()))
    decidable = bool(tp[-1] >= w_end_s + G1_FMIN_MEAN_S - 1e-9)
    rec = g4_4_records(tp, force, w_end_s + G1_FMIN_MEAN_S, f_min_N, decidable)
    out["mean05_min_kN"] = rec["mean05_min_kN"]
    if not decidable or rec["mean05_min_kN"] is None:
        out["reason"] = f"run ends before the window end + {G1_FMIN_MEAN_S:g} s"
        return out
    mean_min_kN = min(rec["mean05_min_kN"].values())
    no_lift = not lifted[after].any()
    out.update(mean05_min_all_kN=mean_min_kN, no_lift=bool(no_lift), status="judged",
               passed=bool(mean_min_kN >= f_min_kN - G1_FMIN_TOL_KN and no_lift))
    return out


def g1_case_metrics(case: Mapping[str, Any], sm: Mapping[str, Any], m: Mapping[str, Any],
                    params, harness_runs: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """Values of one C-S8-72 case (group :data:`G1_GROUP`, :data:`G1_RULE`). Times relative to
    the run start [s], forces kN, pressures bar, angles deg."""
    from outrigger_sim.verify import s6_control as s6

    res = case["result"]
    s = res["settings"]
    s8 = s.get("s8") or {}
    ev = s8.get("event_spec") or {}
    t0 = float(s.get("start_t_s") or 0.0)
    pads = case.get("pads")
    phases = [(float(t), p) for t, p in res.get("phases") or []]
    es = res.get("event_state") or {}
    t_ev = res.get("event_t_s")
    fault_t = fault_entry_s(res.get("phases") or [])
    fast = bool(ev.get("fine"))
    out: dict[str, Any] = {
        "event": s8.get("event"), "base": ev.get("g1_base"), "leg": ev.get("leg"),
        "anchor": ev.get("at"), "fast": fast, "level": s.get("level"),
        "fs_kN": s8.get("fs_kN"), "phase_offset_s": s8.get("phase_offset_s"),
        "event_state": es, "phase_at_event": es.get("phase_at_event"),
        "expected_phase": es.get("expected_phase"),
        "phase_mismatch": es.get("phase_mismatch"), "event_t_s": t_ev,
        "fault_t_s": fault_t, "final_phase": phases[-1][1] if phases else None,
        "s8_end": res.get("s8_end"), "rule": G1_RULE}
    if t_ev is None or pads is None or "airborne" not in pads:
        out["status"] = "no event time or no 1 ms pad record"
        return out
    t_ev = float(t_ev)
    tp = np.asarray(pads["t"], float) - t0
    t3, t3_top = _t3_of_level(s.get("level"))
    ball_z = np.asarray(pads["ball_centre_world"], float)[:, :, 2]
    sp = settle_lift_split(tp, pads["airborne"], ball_z, t_ev,
                           ev["leg"], float(ev["depth_m"]), float(ev["ramp_s"]), t3_s=t3,
                           fault_t_s=fault_t)
    sp["T3_from_top_level"] = t3_top
    out["u_s8_32"] = sp
    # record: union lift of the event pair after the event (the harness "pair" quantity)
    air = np.asarray(pads["airborne"], bool)
    ja, jb = (LEGS.index(x) for x in sp["event_legs"])
    dtp = float(np.median(np.diff(tp))) if tp.size > 1 else 0.0
    out["event_pair_union_s"] = float(((air[:, ja] | air[:, jb])
                                       & (tp >= t_ev - 1e-9)).sum() * dtp)
    w_end = t_ev + float(sp["window_end_rel_s"])
    out["window_s"] = [t_ev, w_end] if fast else None
    # F_min: fast event = U-S8-74 (a) (0.5 s mean + no pad lift after the window end), slow
    # event = S8-A2 judged 1 ms minimum after the event (unchanged)
    fj = judged_force_min(pads)
    f_min = float(sm.get("F_min_N") or params.control.F_min_cylinder_N)
    after = tp >= t_ev - 1e-9
    if fast:
        out["F_min_after"] = g1_fmin_after_window(tp, fj, air, w_end, f_min)
        in_scope = g1_u75_scope(
            is_fast=fast, settle_speed_mm_s=sp["settle_speed_mm_s"],
            v_max_m_s=float(params.actuator.max_speed_m_s), event_leg=ev.get("leg"),
            level=s.get("level"), fs_kN=float(s8.get("fs_kN") or 0.0))
        lifts = adjacent_lifts_after_window(tp, air, ball_z, w_end, sp["adjacent_legs"])
        _g1_apply_u75(sp, out["F_min_after"], lifts, in_scope)
    elif after.any():
        sel = fj[after]
        k, j = np.unravel_index(int(np.argmin(sel)), sel.shape)
        out["F_min_after"] = {"from_s": t_ev, "min_kN": float(sel[k, j]) / 1e3,
                              "leg": LEGS[j], "t_s": float(tp[after][k]),
                              "per_leg_kN": {LEGS[i]: float(sel[:, i].min()) / 1e3
                                             for i in range(4)},
                              "F_min_kN": f_min / 1e3}
    # U58 (existing definition): window any-state peak, outside extension samples
    area = np.asarray(s6._head_areas_m2(params), float)
    p_pad = np.asarray(pads["F_cyl"], float) / area / 1e5
    rec = case.get("rec") or {}
    u58: dict[str, Any] = {"area_m2": area.tolist()}
    if fast:
        inside = (tp >= t_ev - 1e-9) & (tp <= w_end + 1e-9)
        u58["window_peak_bar"] = float(p_pad[inside].max()) if inside.any() else None
    else:
        u58["window_peak_bar"] = None
        u58["run_peak_any_state_bar"] = float(p_pad.max())
    if "u_applied" in rec and "F_cyl" in rec:
        tr = np.asarray(rec["t"], float) - t0
        ext = np.asarray(rec["u_applied"], float) > s6.MOVING_EPS_M_S
        out_w = ~((tr >= t_ev - 1e-9) & (tr <= w_end + 1e-9)) if fast else np.ones(tr.size, bool)
        judged = ext & out_w[:, None]
        p_rec = np.asarray(rec["F_cyl"], float) / area / 1e5
        u58["outside_extension_max_bar"] = float(p_rec[judged].max()) if judged.any() else None
        u58["outside_extension_samples"] = int(judged.sum())
    u58["s6_metrics"] = {k: m.get(k) for k in ("max_pressure_transient_bar",
                                               "max_moving_pressure_excl_transient_bar",
                                               "max_moving_pressure_bar",
                                               "max_pressure_any_step_bar")}
    win_ok = u58.get("window_peak_bar") is None or u58["window_peak_bar"] <= G1_U58_WINDOW_BAR
    run_ok = u58.get("run_peak_any_state_bar") is None \
        or u58["run_peak_any_state_bar"] <= G1_U58_WINDOW_BAR
    ext_ok = u58.get("outside_extension_max_bar") is None \
        or u58["outside_extension_max_bar"] <= G1_U58_OUTSIDE_BAR
    u58["passed"] = bool(win_ok and run_ok and ext_ok)
    out["u58"] = u58
    # end attitude: last 1 s mean of the true deck attitude (1 ms pad record body quaternion)
    if "body_quat_wxyz" in pads:
        q = np.asarray(pads["body_quat_wxyz"], float)
        last = tp >= tp[-1] - G1_END_ATT_WINDOW_S
        rp = np.degrees(np.array([s6.roll_pitch_from_quat(x) for x in q[last]]))
        out["end_att_deg"] = rp.mean(axis=0).tolist()
    out["att_err_last5_maxabs_deg"] = m.get("att_err_last5_maxabs_deg")
    # records: re-approach starts, sign changes, READY return, crawler re-contact
    rt = sm.get("rt") or {}
    runs = rt.get("runs") or []
    signs = [G1_TWIST_SIGN.get(r.get("leg"), 0) for r in runs]
    out["reapproach"] = {"starts": [[r["start_s"], r["leg"]] for r in runs],
                         "n_starts": len(runs),
                         "starts_after_1.5_s": rt.get("starts_after_1.5_s"),
                         "sign_changes": int(sum(1 for a, b in zip(signs, signs[1:], strict=False)
                                                 if a and b and a != b)),
                         "retriggers": rt.get("retriggers"), "deferred": rt.get("deferred")}
    out["work"] = rt.get("work")
    ready_back = next((t for t, p in phases if t > t_ev + 1e-9 and p == "ready"), None)
    out["ready_back_rel_s"] = None if ready_back is None else ready_back - t_ev
    if "F_crawler" in rec:
        tr = np.asarray(rec["t"], float) - t0
        fz = np.asarray(rec["F_crawler"], float)[:, 2]
        a = tr >= t_ev - 1e-9
        dt = float(np.median(np.diff(tr))) if tr.size > 1 else 0.0
        out["crawler_contact_after_event_s"] = float((fz[a] > 0.0).sum() * dt)
        out["crawler_record_dt_s"] = dt
    # harness comparison (228.5 form): harness / Chrono pair cumulative lift, re-contact diff
    timing = "level" if ev.get("at") == "loc+3.0" else "ready"
    hm = g1_harness_match(harness_runs, base=str(ev.get("g1_base")), leg=str(ev.get("leg")),
                          level=str(s.get("level")), fs_kN=float(s8.get("fs_kN") or 0.0),
                          timing=timing, offset_s=float(s8.get("phase_offset_s") or 0.0))
    if hm is not None:
        cum = sp["event_cum_max_s"]
        uni = out["event_pair_union_s"]
        rc = sp["event_recontact_max_rel_s"]
        hp = hm.get("pair_union_s")
        hm["harness_over_chrono_pair"] = None if not uni or hp is None else float(hp) / uni
        hm["harness_over_chrono_cum_max"] = None if not cum or hp is None else float(hp) / cum
        hm["harness_minus_chrono_recontact_s"] = None if rc is None or \
            hm.get("pair_last_touch_s") is None else float(hm["pair_last_touch_s"]) - rc
        hm["note"] = ("harness pair = union lift of the event pair (r67 screen); "
                      "harness_over_chrono_pair uses the Chrono union (same quantity), "
                      "harness_over_chrono_cum_max the U-S8-32 row value (largest per-leg "
                      "cumulative lift)")
    out["harness"] = hm
    return out


def _round_legs(values: Mapping[str, float] | None, ndigits: int = 3) -> dict[str, float] | None:
    return None if values is None else {k: round(v, ndigits) for k, v in values.items()}


def _u75_note(exception: Mapping[str, Any], *, lift_s: float, gap_m: float) -> str:
    """Note suffix of a row that carries a U-S8-75 (b) exception record."""
    values = f"adjacent lift {lift_s:.3f} s, gap {gap_m * 1e3:.2f} mm"
    if exception["applied"]:
        return (f"; FLAG {U75_FLAG}: {values} <= {U75_LIFT_MAX_S:g} s / "
                f"{U75_GAP_MAX_M * 1e3:g} mm")
    reason = "out of scope" if not exception["in_scope"] else "limits or other parts not met"
    return f"; {U75_FLAG} not applied ({reason}): {values}"


def g1_u_s8_32_fast_rows(cid: str, sp: Mapping[str, Any]) -> list[dict[str, Any]]:
    """U-S8-32 rows of a fast C-S8-72 case; the U57 row carries the U-S8-75 (b) exception note
    (and FLAG when it applies) when ``sp`` holds an exception record."""
    rows = u_s8_32_rows(cid, sp, label="C-S8-72")
    exception = sp.get("u75_exception")
    if not rows or exception is None:
        return rows
    u57_row = rows[0]
    u57_row["note"] += _u75_note(exception, lift_s=exception["outside_s"],
                                 gap_m=exception["outside_gap_max_m"])
    if exception["applied"]:
        u57_row["flag"] = True
    return rows


def g1_fmin_fast_rows(cid: str, fm: Mapping[str, Any]) -> list[dict[str, Any]]:
    """U-S8-74 (a) rows of a fast-event case (``fm`` from :func:`g1_fmin_after_window`): the
    judged row (0.5 s mean + no pad lift) and the 1 ms instantaneous record row (FLAG when the
    instantaneous minimum is below F_min)."""
    if not fm:
        return [_row(G1_FMIN_ITEM, cid, None, None, None, "no F_min values",
                     kind="not_judgeable")]
    mean05 = fm.get("mean05_min_kN")
    judged = fm.get("status") == "judged"
    exception = fm.get("u75_exception")
    exception_note = "" if exception is None else _u75_note(
        exception, lift_s=exception["adjacent_lift_s"], gap_m=exception["gap_max_m"])
    exception_flag = {} if not (exception and exception["applied"]) else {"flag": True}
    rows = [_row(G1_FMIN_ITEM, cid,
                 [fm.get("mean05_min_all_kN"), fm.get("airborne_total_s")],
                 [fm["F_min_kN"], 0.0], fm.get("passed"),
                 f"from {fm['from_s']} s (mean windows ending >= {fm['mean05_from_s']} s); "
                 f"0.5 s mean min per leg {_round_legs(mean05, 2)} kN; lift per leg "
                 f"{_round_legs(fm.get('airborne_s'))} s ({fm.get('airborne_source')})"
                 + ("" if judged else f"; not judgeable: {fm.get('reason')}")
                 + exception_note,
                 kind="judged" if judged else "not_judgeable", F_min_after=dict(fm),
                 **exception_flag)]
    if fm.get("instant_min_kN") is None:
        return rows
    flag = bool(fm.get("instant_below_F_min"))
    rows.append(_row(
        G1_FMIN_RECORD_ITEM, cid,
        {"instant_min_kN": fm["instant_min_kN"], "leg": fm["instant_leg"],
         "t_s": fm["instant_t_s"], "below_F_min_s": fm["below_F_min_s"],
         "longest_below_s": fm["longest_below_s"], "below_zero_s": fm["below_zero_s"],
         "airborne_s": fm["airborne_s"]},
        fm["F_min_kN"], None,
        ("FLAG: " if flag else "")
        + f"1 ms min {fm['instant_min_kN']:.2f} kN ({fm['instant_leg']} at "
        f"{fm['instant_t_s']:.3f} s) vs F_min {fm['F_min_kN']:.3f} kN; per leg "
        f"{_round_legs(fm.get('instant_per_leg_kN'), 2)} kN",
        kind="record", flag=flag))
    return rows


def g1_rows(sms: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """345.2 rows of the C-S8-72 cases (``sm['g1']`` from :func:`g1_case_metrics`)."""
    rows: list[dict[str, Any]] = []
    for cid, sm in sorted(sms.items()):
        g = sm.get("g1")
        if not g:
            continue
        mismatch = bool(g.get("phase_mismatch"))
        na = "phase_mismatch: not judgeable (spec rev. 67 345.1)"

        def add(r: dict[str, Any]) -> None:
            if mismatch and r.get("kind") == "judged":
                r.update(passed=None, kind="not_judgeable", note=f"{na}; {r.get('note', '')}")
            rows.append(r)

        es = g.get("event_state") or {}
        add(_row("C-S8-72 event state: controller phase at the event start vs expected "
                 "(LEVEL for LOC + 3.0 s, READY for READY + 5 s)", cid,
                 {"phase_at_event": g.get("phase_at_event"),
                  "expected": g.get("expected_phase"), "event_t_s": g.get("event_t_s"),
                  "reference_t_s": es.get("reference_t_s"), "loc_t_s": es.get("loc_t_s"),
                  "phase_offset_s": g.get("phase_offset_s")},
                 g.get("expected_phase"), None if g.get("phase_mismatch") is None
                 else not mismatch, "phase_mismatch = not judgeable (345.1)",
                 kind="record" if not mismatch else "record_flag"))
        if g.get("status"):
            rows.append(_row("C-S8-72 case not judgeable", cid, g["status"], None, None,
                             kind="not_judgeable"))
            continue
        sp = g["u_s8_32"]
        if g["fast"]:
            for r in g1_u_s8_32_fast_rows(cid, sp):
                add(r)
        else:
            for r in u_s8_32_rows(cid, sp, label="C-S8-72 (slow event, record)"):
                rows.append(r | {"kind": "record", "passed": None})
            lifted = sp["any_lift"]
            add(_row("C-S8-72 slow event (G4): no lift on any leg, FAULT 0 (342.3)", cid,
                     {"cum_lift_s": sp["cum_lift_s"], "fault_t_s": g.get("fault_t_s")},
                     "0 / None", (not lifted) and g.get("fault_t_s") is None,
                     "record next to the 345.2 rows (U-S8-32 row is for 1-9, 11)",
                     kind="record"))
        u = g["u58"]
        add(_row("C-S8-72 U58: head F/A_p in the window <= 350 bar, outside extension samples "
                 "<= 180 bar (slow event: whole-run any-state peak <= 350)", cid,
                 [u.get("window_peak_bar"), u.get("outside_extension_max_bar"),
                  u.get("run_peak_any_state_bar")],
                 [G1_U58_WINDOW_BAR, G1_U58_OUTSIDE_BAR, G1_U58_WINDOW_BAR], u["passed"],
                 f"window {g.get('window_s')}; s6 metrics {u['s6_metrics']}", u58=u))
        fm = g.get("F_min_after") or {}
        if g["fast"]:
            for r in g1_fmin_fast_rows(cid, fm):
                add(r)
        else:
            add(_row(G1_FMIN_ITEM, cid, fm.get("min_kN"), fm.get("F_min_kN"),
                     None if not fm else bool(fm["min_kN"] >= fm["F_min_kN"] - 1e-9),
                     f"from {fm.get('from_s')} s; min {fm.get('leg')} at {fm.get('t_s')} s; "
                     f"per leg "
                     f"{ {k: round(v, 2) for k, v in (fm.get('per_leg_kN') or {}).items()} } kN",
                     F_min_after=fm))
        att = g.get("end_att_deg")
        ok_att = None if att is None else bool(
            g.get("final_phase") == "ready"
            and max(abs(a) for a in att) <= G1_ATT_TOL_DEG + 1e-12)
        add(_row("C-S8-72 end: READY and last 1 s mean true |roll|, |pitch| <= 0.2 deg", cid,
                 {"final_phase": g.get("final_phase"),
                  "end_att_deg": None if att is None else [round(a, 4) for a in att],
                  "last5_maxabs_deg": g.get("att_err_last5_maxabs_deg")},
                 G1_ATT_TOL_DEG, ok_att,
                 f"run end {((g.get('s8_end') or {}).get('end_t_s'))} s, timeout "
                 f"{(g.get('s8_end') or {}).get('timeout')}"))
        w = g.get("work") or {}
        add(_row("C-S8-72 recurrence ban (248.3): twist-work clusters of 0.5 s bins > +20 J "
                 "after event + 1.5 s <= 1", cid,
                 {"n_clusters": w.get("n_clusters"), "clusters": w.get("clusters"),
                  "max_bin_after_J": w.get("max_bin_after_J")},
                 RT_WORK_MAX_CLUSTERS, w.get("passed"), str(w.get("status"))))
        rp = g.get("reapproach") or {}
        hm = g.get("harness") or {}
        rows.append(_row("C-S8-72 record: re-approach starts / after 1.5 s / sign changes, "
                         "READY return, crawler re-contact, harness / Chrono (228.5 form)", cid,
                         {"n_starts": rp.get("n_starts"),
                          "starts_after_1.5_s": rp.get("starts_after_1.5_s"),
                          "sign_changes": rp.get("sign_changes"),
                          "ready_back_rel_s": g.get("ready_back_rel_s"),
                          "event_pair_union_s": g.get("event_pair_union_s"),
                          "crawler_contact_after_event_s": g.get(
                              "crawler_contact_after_event_s"),
                          "harness_over_chrono_pair": hm.get("harness_over_chrono_pair"),
                          "harness_minus_chrono_recontact_s": hm.get(
                              "harness_minus_chrono_recontact_s")},
                         None, None,
                         f"starts {rp.get('starts')}; harness {hm.get('file')} pair "
                         f"{hm.get('pair_union_s')} s, last touch {hm.get('pair_last_touch_s')} "
                         f"s, pass {hm.get('pass')}", kind="record", reapproach=rp,
                         harness=hm))
    return rows


def g1_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Per case: judged rows passed / failed / not judgeable (C-S8-72 rows only)."""
    out: dict[str, Any] = {}
    for r in rows:
        if not str(r.get("item", "")).startswith("C-S8-72"):
            continue
        c = out.setdefault(r["case"], {"passed": 0, "failed": [], "not_judgeable": 0,
                                       "records": 0})
        if r.get("kind") == "judged":
            if r.get("passed") is True:
                c["passed"] += 1
            elif r.get("passed") is False:
                c["failed"].append(r["item"])
        elif r.get("kind") == "not_judgeable":
            c["not_judgeable"] += 1
        else:
            c["records"] += 1
    return out


# --- C-S8-68 (spec rev. 64 323, U-S8-68): G4 head fault + lifted leg = FAULT_REGROUND --------

FAULT_REGROUND_PHASE = "fault_reground"
"""P-S8-24 phase ``C2Phase.FAULT_REGROUND`` as recorded in ``phases`` / ``s8_series.phase``
(ASSUMPTION: the enum value is the lower-case name like the other phases)."""
FAULT_ENTRY_PHASES = (FAULT_REGROUND_PHASE, "fault")
"""C-S8-68 ①: the FAULT entry is the first of these phases."""
REGROUND_START_EVENT = "fault_reground_start"
REGROUND_CONTACT_EVENT = "fault_reground_contact"
REGROUND_LIMIT_WARNING = "WARN_FAULT_REGROUND_LIMIT"
REGROUND_END_EVENT = "fault_reground_end"
"""Spec 323.2 events: ``fault_reground_start:<legs>``, ``fault_reground_contact:<leg>``,
``WARN_FAULT_REGROUND_LIMIT:<leg>:<travel|time>``, ``fault_reground_end:<n_contact>/<n>``."""
HEAD_FAULT_KEY = "head_fault"
"""``run_S8C`` event-spec key of the head-sensor fault injection (C-S8-68 ②)."""
G4_TRUTH_HALF_WINDOW_S = 0.2
"""Record window of ``airborne_ms_in_window`` (t_f +- 0.2 s)."""
G4_TRUTH_SAMPLE_OFFSETS_S = (-0.2, -0.1, 0.0)
G4_TRUTH_MIN_SAMPLES = 2
"""323.9 ①: true target = airborne at >= 2 of the controller sample times t_f - 0.2, - 0.1, t_f."""
G4_LATE_WINDOW_S = 0.5
G4_LATE_MIN_S = 0.020
"""323.9 ① record ``late_airborne``: non-target legs airborne > 20 ms in (t_f, t_f + 0.5] s."""
G4_FAULT_WITHIN_S = 15.0
G4_SETTLED_AFTER_S = 1.0
G4_MIN_JUDGE_WINDOW_S = 3.0
"""323.9 ② (ASSUMPTION): G4-4 is undecidable when run end - (FAULT + 1 s) < 3 s."""
G4_HEALTHY_DIP_MAX_S = 0.5
"""323.9 ③ (ASSUMPTION, U57 adjacent lift limit): a healthy leg may stay below F_min <= 0.5 s."""
G4_HEAD_LIMIT_PA = 345e5
G4_FAULTY_RISE_LIMIT_N = 120e3
"""Rev. 64 323.7 value, kept as a record column only (323.9 ③: judged on the extend limit)."""
G4_PRE_EVENT_MEDIAN_S = 2.0
"""Record column: faulty-leg F_cyl rise against the median over [event - 2 s, event) (ASSUMPTION:
323.9 ③ 'pre-event median' without a window length)."""
G4_ATT_LIMIT_DEG = 0.5
G4_ATT_MEAN_S = 0.5
"""323.9 ④ (ASSUMPTION): trailing 0.5 s mean attitude vs the mean over [t_f - 0.5, t_f]."""
G4_TRAVEL_CAP_M = 0.030
G4_LEG_TIME_LIMIT_S = 8.0
G4_TOTAL_TIME_LIMIT_S = 15.0
G4_ZERO_U_M_S = 1e-12
G4_TIME_TOL_S = 1e-6
G4_OUTPUT_DELAY_PERIODS = 1
"""C-S8-70 ① (spec rev. 65 333, 331.1 #4): controller output delay d = 1. The output issued on
the FAULT sample is the previous period's command, so the G4-3 (and G4-7) zero-output check
starts at FAULT + d T_s; the FAULT-sample value is a record column."""
G4_MEAN05_S = 0.5
G4_TAIL_S = 2.0
"""C-S8-70 ② (spec rev. 65 333, 330.1): G4-4 record columns = per-leg minimum of the trailing
0.5 s moving mean (window end >= FAULT + 1 s, full windows only) and the mean / peak-to-peak over
the last 2 s of the run (control ``r64_g4_closed_loop.py`` ``G4_4_mean05_min_kN``,
``last2s_mean_kN``, ``last2s_ptp_kN``)."""
G4_INSTANT_FLOOR_N = 0.0
G4_4_RULE = ("C-S8-71 / U-S8-72 (a) (spec rev. 66 337 / 338), (b) per U-S8-74 (a) (spec rev. 68 "
             "354.1): over [FAULT + 1 s, run end] every "
             "leg's trailing 0.5 s moving mean of the judged true force (S8-A2; windows ending "
             "at >= FAULT + 1 s, full windows only, as control r64_g4_closed_loop.py) >= F_min "
             "AND no pad lift-off (airborne samples 0; old records without airborne: judged "
             "force > 0, airborne_source force_sign_fallback); undecidable when the window "
             "< 3 s; records: instantaneous minimum > 0 (instant_min_positive) and vs F_min "
             "(rev. 64 strict rule: instant_min_ge_F_min, below_F_min_s)")
"""C-S8-71 ① (U-S8-72 (a), 2026-10-27) with (b) = no pad lift-off (U-S8-74 (a), 2026-10-27):
G4-4 judged quantity. :data:`G4_INSTANT_FLOOR_N` is the instantaneous floor of the
``instant_min_positive`` record (strictly above, N)."""
JUDGE_REVISION_U75 = (
    "U-S8-75 = (b) (spec rev. 68 357.3: fast event on a front leg, top level, case F_s < 2 kN: "
    "U57 outside-window lift and U-S8-74 F_min (b) lift after the window end pass at <= 0.1 s "
    "and gap <= 0.5 mm with the FLAG 'U-S8-75 (b) exception'; outside the scope unchanged)")
JUDGE_REVISION_U74 = (
    "U-S8-74 (a) (spec rev. 68 354: C-S8-72 fast-event F_min = 0.5 s moving mean minimum >= "
    "F_min and no pad lift after the window end, the 1 ms instantaneous minimum a record row "
    "(FLAG when < F_min), slow event unchanged; G4-4 (b) = no pad lift-off (airborne 0), the "
    "instantaneous minimum > 0 a record)")
G4_END_MEAN_S = 0.5
"""C-S8-71 ③ record: the end attitude change after FAULT = mean true roll / pitch over the last
0.5 s of the run minus the mean over [FAULT - 0.5 s, FAULT] (ASSUMPTION: 0.5 s means as G4-6)."""
G4_NA_ITEMS = (RUN_ITEM, "2 attitude +-0.2 (+mount)", "RE1b re-READY <= 60 s",
               "6 re-READY <= 40 s")
G4_NA_EXPECTS = ("reground", "negative", "record")
G4_NA_KIND = "not_applicable"
"""C-S8-71 ③ (spec rev. 66 338): the general rows that ask a READY return / end attitude are not
applicable to a head-fault injection run (expected FAULT): ``passed`` None, ``passed_raw`` kept,
``kind`` :data:`G4_NA_KIND` (as the "comparison" / "superseded" rows of C-S8-22)."""
G4_NO_TARGET_REASON = "no_target"
"""C-S8-70 ③: G4-7 is judged only on runs whose controller meta ``fault_reground.run.end_reason``
is this value (spec rev. 65 333, python assumption ⑦)."""
REGROUND_ABORT_WARNING = "WARN_FAULT_REGROUND_ABORT"
D1_STEP_SUSPENDED_INFO = "INFO_D1_STEP_SUSPENDED"
"""C-S8-70 ⑦ (spec rev. 65 329 ⑧, 332.4): ``WARN_FAULT_REGROUND_ABORT:<end_reason>`` (aborts 1 /
3 / 4 / 5 and the total time limit) and ``INFO_D1_STEP_SUSPENDED:<fault leg>``; counted in the
G4-8 record row."""
HEAD_DELIVERED_FILE = "head_fault_delivered.npz"
HEAD_DELIVERED_KEY = "meas.head_pressure_delivered"
"""C-S8-70 ⑥ (spec rev. 65 333 last row): ``run_S8C`` head-fault runs store the head reading
the controller really received (after the injection) next to the record, because
``record/meas.head_pressure`` holds the reading before the injection."""
G4_RULE = (
    "C-S8-68 / spec rev. 64 323.7 (times relative to the run start; t_f = first controller sample "
    "with the injected head fault): G4-1 the first FAULT_REGROUND-or-FAULT entry is at t_f and "
    "FAULT_HEAD_PRESSURE:<fault leg> is recorded there; G4-2 (rev. 64 323.9 ①) every leg "
    "airborne (1 ms pads) at >= 2 of the controller sample times t_f - 0.2, t_f - 0.1, t_f is a "
    "re-ground target (fault_reground_start legs); records: false targets, airborne ms in "
    "t_f +- 0.2 s, airborne at t_f, late_airborne (non-target > 20 ms in (t_f, t_f + 0.5] s); "
    "G4-3 FAULT (phase 'fault') <= t_f + 15 s and issued_u = 0 from FAULT + d T_s on (d = 1, "
    "C-S8-70 ① / rev. 65 333; the FAULT-sample issued_u is recorded); G4-4 (main, C-S8-71 / "
    "U-S8-72 (a), rev. 66 337) from FAULT + 1 s to the run end every leg's trailing 0.5 s moving "
    "mean of the judged true force (S8-A2; window end >= FAULT + 1 s) >= F_min and no pad "
    "lift-off (airborne samples 0, U-S8-74 (a) / rev. 68 354), undecidable when that window < 3 s "
    "(323.9 ②); records: instantaneous minimum > 0 and vs F_min (rev. 64 strict rule), time below "
    "F_min, airborne ms, mean and peak-to-peak over the last 2 s (C-S8-70 ②); "
    "G4-5 (323.9 ③) window [entry, FAULT + 1 s): healthy legs "
    "(neither the fault leg nor a target) never below F_min for more than 0.5 s in a row "
    "(shorter dips recorded), faulty-leg F_cyl max <= its extend force limit (YAML "
    "legs.<leg>.cylinder.max_force_extend_N; rises vs the entry sample and the pre-event median "
    "recorded), every leg's true head <= 345 bar; G4-6 (323.9 ④) trailing 0.5 s mean true roll / "
    "pitch minus the [t_f - 0.5, t_f] mean <= 0.5 deg over [t_f, FAULT + 1 s] (instant change "
    "recorded); G4-7 judged only when the controller meta end_reason is 'no_target' (C-S8-70 ③; "
    "without a meta: no fault_reground_start target leg), a record otherwise: no "
    "FAULT_REGROUND, FAULT at t_f, issued_u = 0 from t_f + d T_s (the t_f-sample issued_u "
    "recorded; ASSUMPTION: the d = 1 shift of G4-3 applies alike); G4-8 (record) per-leg travel "
    "<= max_travel (controller meta, else 30 mm), moving time <= 8 s, window <= 15 s, "
    "hold_count of the meta targets, max_filtered_attitude_change_rad, counts of "
    "WARN_FAULT_REGROUND_ABORT:<reason> and INFO_D1_STEP_SUSPENDED:<leg> (C-S8-70 ⑦); G4-E "
    "(record, C-S8-71 ③) end attitude change after FAULT (last 0.5 s mean true roll / pitch "
    "minus the [FAULT - 0.5 s, FAULT] mean); the general rows run / 2 attitude / RE1b re-READY "
    "/ 6 re-READY of a head-fault run (expect reground / negative / record) are not applicable "
    "(expected FAULT). F2 of a "
    "head-fault run leaves out the fault leg from the injection arm time (C-S8-70 ④, violations "
    "of that leg recorded as F2_faulty_leg_after_injection)")


def fault_entry_s(phases: Sequence[Sequence[Any]], after_s: float | None = None
                  ) -> float | None:
    """C-S8-68 ①: time of the first ``fault_reground`` or ``fault`` phase entry (optionally at
    or after ``after_s``); None without one."""
    lo = -math.inf if after_s is None else float(after_s) - G4_TIME_TOL_S
    return next((float(t) for t, p in phases if p in FAULT_ENTRY_PHASES and float(t) >= lo),
                None)


def legs_in(text: str | None) -> list[str]:
    """Leg names in an event field (``"RL"``, ``"RL,FR"``, ``"FR+RL"`` ...), leg order."""
    found = set(re.findall(r"FL|FR|RL|RR", text or ""))
    return [leg for leg in LEGS if leg in found]


def head_fault_of(res: Mapping[str, Any]) -> tuple[dict[str, Any] | None, float | None,
                                                   float | None]:
    """C-S8-68 ②: ``(spec, arm time, first faulted sample)`` of a run's head-fault injection
    (``settings.s8.event_spec.head_fault`` or ``result.event.spec.head_fault``; times relative)."""
    s8 = (res.get("settings") or {}).get("s8") or {}
    spec = None
    for ev in (s8.get("event_spec"), (res.get("event") or {}).get("spec")):
        if isinstance(ev, Mapping) and ev.get(HEAD_FAULT_KEY):
            spec = dict(ev[HEAD_FAULT_KEY])
            break
    t_arm, t_first = res.get("head_fault_t_s"), res.get("head_fault_first_applied_t_s")
    return (spec, None if t_arm is None else float(t_arm),
            None if t_first is None else float(t_first))


def head_fault_leg_cut(res: Mapping[str, Any], tc: np.ndarray
                       ) -> tuple[np.ndarray, dict[str, Any] | None, float | None]:
    """C-S8-70 ④: ``(mask (n, 4), spec, arm time)``; the mask is True on the head-fault leg from
    the injection arm time on (``tc`` relative times as ``head_fault_t_s``); all False without
    a head-fault injection."""
    tc = np.asarray(tc, float)
    spec, t_arm, _t_first = head_fault_of(res)
    cut = np.zeros(tc.shape + (4,), bool)
    if spec and t_arm is not None and spec.get("leg") in LEGS:
        cut[tc >= t_arm - 1e-9, LEGS.index(spec["leg"])] = True
    return cut, spec, t_arm


def g4_4_records(tp: np.ndarray, f_N: np.ndarray, t_from_s: float, f_min_N: float,
                 decidable: bool) -> dict[str, Any]:
    """C-S8-70 ② record columns of G4-4 (:data:`G4_MEAN05_S`, :data:`G4_TAIL_S`): per-leg minimum
    of the trailing 0.5 s moving mean of ``f_N`` over the windows (full ones only) ending at or
    after ``t_from_s``, its pass flag against ``f_min_N`` (record, None when G4-4 is
    undecidable), and the mean / peak-to-peak over the last 2 s of the record. kN out."""
    tp = np.asarray(tp, float)
    f = np.asarray(f_N, float)
    out: dict[str, Any] = {"mean05_min_kN": None, "mean05_passed": None,
                           "last2s_mean_kN": None, "last2s_ptp_kN": None,
                           "mean05_rule": f"trailing {G4_MEAN05_S:g} s moving mean, window end "
                                          ">= FAULT + 1 s (record, C-S8-70 ②)"}
    if tp.size < 2:
        return out
    n = max(int(round(G4_MEAN05_S / _period(tp))), 1)
    if tp.size >= n:
        cs = np.vstack([np.zeros((1, 4)), np.cumsum(f, axis=0)])
        mov = (cs[n:] - cs[:-n]) / n  # row k = mean of samples k .. k + n - 1
        t_end = tp[n - 1:]
        w = t_end >= t_from_s - 1e-9
        if w.any():
            mm = mov[w].min(axis=0)
            out["mean05_min_kN"] = {LEGS[i]: float(mm[i]) / 1e3 for i in range(4)}
            out["mean05_passed"] = None if not decidable else bool(mm.min() >= f_min_N - 1e-6)
    tail = tp >= tp[-1] - G4_TAIL_S - 1e-9
    out["last2s_mean_kN"] = {LEGS[i]: float(f[tail, i].mean()) / 1e3 for i in range(4)}
    out["last2s_ptp_kN"] = {LEGS[i]: float(np.ptp(f[tail, i])) / 1e3 for i in range(4)}
    return out


def g4_metrics(*, t_f: float | None, fault_leg: str, expect: str | None,
               phases: Sequence[Sequence[Any]], names: Sequence[tuple[float, str]],
               tc: np.ndarray, phase_series: np.ndarray, issued_u: np.ndarray,
               tp: np.ndarray, airborne: np.ndarray | None, judged_force_N: np.ndarray,
               f_cyl_N: np.ndarray, head_true_Pa: np.ndarray, roll_pitch_rad: np.ndarray | None,
               s_motor_m: np.ndarray, f_min_N: float,
               reground_meta: Mapping[str, Any] | None = None,
               extend_limit_N: Sequence[float] | None = None,
               t_event_s: float | None = None) -> dict[str, Any]:
    """C-S8-68 values of one head-fault run (:data:`G4_RULE`). Times relative to the run start:
    ``tc`` / ``phase_series`` / ``issued_u`` = 10 Hz ``s8_series``, ``tp`` ... = 1 ms pads
    (``roll_pitch_rad`` (n, 2) from ``body_quat_wxyz``). ``extend_limit_N``: per-leg extend
    force limit (YAML); ``t_event_s``: the case event time (pre-event median record column).
    ``airborne`` None = old record without the field: G4-4 (b) falls back to judged force > 0
    (``airborne_source`` ``force_sign_fallback``, spec rev. 68 354.1) and G4-2 sees no lift.
    SI inputs; kN / bar / mm / deg out."""
    j = LEGS.index(fault_leg)
    tc, tp = np.asarray(tc, float), np.asarray(tp, float)
    ph = np.asarray(phase_series).astype(str)
    u = np.asarray(issued_u, float)
    has_airborne = airborne is not None
    air = np.asarray(airborne, bool) if has_airborne else np.zeros((tp.size, 4), bool)
    out: dict[str, Any] = {"fault_leg": fault_leg, "expect": expect, "t_f_s": t_f,
                           "rule": G4_RULE}
    if t_f is None:
        out["error"] = "no faulted controller sample (head_fault_first_applied_t_s None)"
        return out
    period = _period(tc)
    pre = fault_entry_s(phases)
    entry = fault_entry_s(phases, t_f)
    t_fault = None if entry is None else next(
        (float(t) for t, p in phases if p == "fault" and float(t) >= entry - G4_TIME_TOL_S), None)
    rg_seen = any(p == FAULT_REGROUND_PHASE for _t, p in phases)
    end_s = float(max(tc[-1] if tc.size else t_f, tp[-1] if tp.size else t_f))
    out.update(entry_s=entry, fault_s=t_fault, run_end_s=end_s, reground_phase_seen=rg_seen,
               entry_before_fault=None if pre is None or pre >= t_f - G4_TIME_TOL_S else pre)
    # G4-1
    hf = [e for e in named_events(names, HEAD_FAULT_EVENT)
          if abs(e["t_s"] - t_f) <= G4_TIME_TOL_S]
    reasons = [e for e in named_events(names, HEAD_FAULT_REASON_INFO)
               if abs(e["t_s"] - t_f) <= G4_TIME_TOL_S]
    out["g4_1"] = {"entry_delay_s": None if entry is None else entry - t_f,
                   "head_fault_events": [[e["t_s"], e["leg"]] for e in hf],
                   "reason_events": [[e["t_s"], e["leg"], e["detail"]] for e in reasons],
                   "passed": bool(entry is not None and abs(entry - t_f) <= G4_TIME_TOL_S
                                  and out["entry_before_fault"] is None
                                  and any(e["leg"] == fault_leg for e in hf))}
    # G4-2
    starts = [e for e in named_events(names, REGROUND_START_EVENT)
              if entry is not None and e["t_s"] >= entry - G4_TIME_TOL_S]
    targets = legs_in(starts[0]["leg"]) if starts else []
    win = (tp >= t_f - G4_TRUTH_HALF_WINDOW_S - 1e-9) & (tp <= t_f + G4_TRUTH_HALF_WINDOW_S + 1e-9)
    dtp = _period(tp)
    air_ms = {LEGS[i]: float(air[win, i].sum() * dtp * 1e3) for i in range(4)}

    def k_at(t: float) -> int:  # 1 ms pad row at a controller sample time
        return int(np.clip(np.searchsorted(tp, t - 1e-9), 0, max(tp.size - 1, 0)))

    k_f = k_at(t_f)
    sample_t = [t_f + o for o in G4_TRUTH_SAMPLE_OFFSETS_S]
    at_samples = {LEGS[i]: [bool(tp.size and air[k_at(t), i]) for t in sample_t]
                  for i in range(4)}
    truth = [leg for leg in LEGS if sum(at_samples[leg]) >= G4_TRUTH_MIN_SAMPLES]
    missed = [leg for leg in truth if leg not in targets]
    late_w = (tp > t_f + 1e-9) & (tp <= t_f + G4_LATE_WINDOW_S + 1e-9)
    late_ms = {LEGS[i]: float(air[late_w, i].sum() * dtp * 1e3) for i in range(4)}
    late = [g for g in LEGS if g not in truth and late_ms[g] > G4_LATE_MIN_S * 1e3 + 1e-9]
    out["g4_2"] = {"targets": targets, "truth_airborne": truth,
                   "airborne_at_samples": at_samples, "sample_t_s": sample_t,
                   "airborne_ms_in_window": air_ms,
                   "airborne_at_t_f": [LEGS[i] for i in range(4) if tp.size and air[k_f, i]],
                   "late_airborne": late, "late_airborne_ms": late_ms,
                   "missed": missed, "false_targets": [g for g in targets if g not in truth],
                   "start_events": [[e["t_s"], e["leg"]] for e in starts],
                   "passed": not missed}
    # G4-3 (C-S8-70 ①: zero output from FAULT + d T_s; the FAULT-sample output recorded)
    delay_s = G4_OUTPUT_DELAY_PERIODS * period
    t_zero = (t_fault if t_fault is not None else math.inf) + delay_s
    after = tc >= t_zero - G4_TIME_TOL_S
    u_after = float(np.abs(u[after]).max()) if after.any() else None
    at_fault = ((tc >= (t_fault if t_fault is not None else math.inf) - G4_TIME_TOL_S)
                & (tc < t_zero - G4_TIME_TOL_S))
    out["g4_3"] = {"fault_minus_t_f_s": None if t_fault is None else t_fault - t_f,
                   "zero_check_from_s": None if t_fault is None else t_zero,
                   "output_delay_periods": G4_OUTPUT_DELAY_PERIODS,
                   "max_abs_u_after_fault_mm_s": None if u_after is None else u_after * 1e3,
                   "issued_u_at_fault_sample_mm_s": None if not at_fault.any()
                   else {LEGS[i]: float(np.abs(u[at_fault, i]).max()) * 1e3 for i in range(4)},
                   "passed": bool(t_fault is not None and t_fault - t_f
                                  <= G4_FAULT_WITHIN_S + G4_TIME_TOL_S
                                  and u_after is not None and u_after <= G4_ZERO_U_M_S)}
    # G4-4 (main; C-S8-71 / U-S8-72 (a), (b) per U-S8-74 (a)): 0.5 s moving-mean minimum >=
    # F_min and no pad lift-off over [FAULT + 1 s, end]; the instantaneous minimum (> 0, vs
    # F_min) is a record
    f = np.asarray(judged_force_N, float)
    if t_fault is not None:
        sel = tp >= t_fault + G4_SETTLED_AFTER_S - 1e-9
        k1 = int(np.clip(np.searchsorted(tp, t_fault + G4_SETTLED_AFTER_S - 1e-9), 0,
                         max(tp.size - 1, 0)))
        mins = None if not sel.any() else {LEGS[i]: float(f[sel, i].min()) / 1e3
                                           for i in range(4)}
        span = end_s - (t_fault + G4_SETTLED_AFTER_S)
        decidable = span >= G4_MIN_JUDGE_WINDOW_S - 1e-9
        rec4 = g4_4_records(tp, f, t_fault + G4_SETTLED_AFTER_S, f_min_N, decidable)
        inst_ge_fmin = None if mins is None else bool(min(mins.values()) >= f_min_N / 1e3 - 1e-9)
        inst_pos = None if mins is None else bool(min(mins.values()) > G4_INSTANT_FLOOR_N / 1e3)
        if not sel.any():
            no_lift = None
        elif has_airborne:
            no_lift = not bool(air[sel].any())
        else:
            no_lift = inst_pos
        mean_ok = rec4["mean05_min_kN"] is not None and bool(
            min(rec4["mean05_min_kN"].values()) >= f_min_N / 1e3 - 1e-9)
        below = {LEGS[i]: float(np.sum(sel & (f[:, i] < f_min_N)) * dtp) for i in range(4)}
        last_below = {LEGS[i]: (float(tp[sel & (f[:, i] < f_min_N)][-1])
                                if np.any(sel & (f[:, i] < f_min_N)) else None)
                      for i in range(4)}
        out["g4_4"] = {"min_from_fault_plus_1s_kN": mins,
                       "at_fault_plus_1s_kN": None if not sel.any()
                       else {LEGS[i]: float(f[k1, i]) / 1e3 for i in range(4)},
                       "window_s": None if not sel.any() else [float(tp[sel][0]),
                                                               float(tp[sel][-1])],
                       "window_length_s": span, "F_min_kN": f_min_N / 1e3,
                       "status": "judged" if decidable else "undecidable",
                       "rule": G4_4_RULE,
                       "passed": None if not decidable else bool(
                           mean_ok and no_lift is True),
                       "no_lift": no_lift,
                       "airborne_source": ("pads.airborne" if has_airborne
                                           else "force_sign_fallback"),
                       # U-S8-74 (a) record column (the C-S8-71 (b) quantity)
                       "instant_min_positive": inst_pos,
                       # C-S8-71 record columns: the rev. 64 strict rule and its extent
                       "instant_min_ge_F_min": inst_ge_fmin,
                       "below_F_min_s": below, "last_below_F_min_t_s": last_below,
                       "airborne_ms_in_window": {LEGS[i]: float(air[sel, i].sum() * dtp * 1e3)
                                                 for i in range(4)},
                       **rec4}
    else:
        out["g4_4"] = {"min_from_fault_plus_1s_kN": None, "F_min_kN": f_min_N / 1e3,
                       "passed": False, "note": "no FAULT"}
    # G4-5 (323.9 ③): re-ground window [entry, FAULT + 1 s)
    if entry is not None and t_fault is not None and t_fault > entry + G4_TIME_TOL_S:
        t_hi5 = t_fault + G4_SETTLED_AFTER_S
        w = (tp >= entry - 1e-9) & (tp < t_hi5 - 1e-9)
        k0 = int(np.clip(np.searchsorted(tp, entry - 1e-9), 0, max(tp.size - 1, 0)))
        healthy = [i for i in range(4) if i != j and LEGS[i] not in targets]
        dips: dict[str, dict[str, Any]] = {}
        for i in healthy:
            runs = _runs(w & (f[:, i] < f_min_N))
            lens = [(b - a + 1) * dtp for a, b in runs]  # inclusive (first, last)
            dips[LEGS[i]] = {"count": len(runs),
                             "longest_s": max(lens, default=0.0),
                             "min_kN": float(f[w, i].min()) / 1e3 if w.any() else None,
                             "dips_s": [[float(tp[a]), float(lng)]
                                        for (a, _b), lng in zip(runs, lens)][:20]}
        dip_ok = all(d["longest_s"] <= G4_HEALTHY_DIP_MAX_S + 1e-9 for d in dips.values())
        head_max = (float(np.asarray(head_true_Pa, float)[w].max()) / 1e5 if w.any() else None)
        fc = np.asarray(f_cyl_N, float)
        fmax = float(fc[w, j].max()) if w.any() else None
        lim = None if extend_limit_N is None else float(extend_limit_N[j])
        rise = None if fmax is None else (fmax - fc[k0, j]) / 1e3
        rise_pre = None
        if fmax is not None and t_event_s is not None:
            pw = (tp >= t_event_s - G4_PRE_EVENT_MEDIAN_S - 1e-9) & (tp < t_event_s - 1e-9)
            if pw.any():
                rise_pre = (fmax - float(np.median(fc[pw, j]))) / 1e3
        ok = (dip_ok and head_max is not None and head_max <= G4_HEAD_LIMIT_PA / 1e5 + 1e-9
              and fmax is not None and lim is not None and fmax <= lim + 1e-6)
        out["g4_5"] = {"window_s": [entry, t_hi5],
                       "healthy_legs": [LEGS[i] for i in healthy], "healthy_dips": dips,
                       "dip_limit_s": G4_HEALTHY_DIP_MAX_S, "head_true_max_bar": head_max,
                       "faulty_F_cyl_max_kN": None if fmax is None else fmax / 1e3,
                       "faulty_extend_limit_kN": None if lim is None else lim / 1e3,
                       "faulty_rise_vs_entry_kN": rise,
                       "faulty_rise_vs_pre_event_median_kN": rise_pre,
                       "passed": bool(ok)}
        if lim is None:
            out["g4_5"]["note"] = "no extend force limit given: faulty-leg criterion fails"
    else:
        out["g4_5"] = {"window_s": None, "passed": None,
                       "note": "no FAULT_REGROUND window (direct FAULT or no FAULT)"}
    # G4-6 (323.9 ④): trailing 0.5 s mean attitude vs the [t_f - 0.5, t_f] mean
    if roll_pitch_rad is not None and tp.size:
        rp = np.asarray(roll_pitch_rad, float)
        t_hi = (t_fault + G4_SETTLED_AFTER_S) if t_fault is not None else end_s
        w6 = (tp >= t_f - 1e-9) & (tp <= t_hi + 1e-9)
        n = max(int(round(G4_ATT_MEAN_S / dtp)), 1)
        cs = np.vstack([np.zeros((1, 2)), np.cumsum(rp, axis=0)])
        idx = np.flatnonzero(w6)
        lo = np.maximum(idx + 1 - n, 0)
        mov = (cs[idx + 1] - cs[lo]) / (idx + 1 - lo)[:, None]
        bw = (tp >= t_f - G4_ATT_MEAN_S - 1e-9) & (tp <= t_f + 1e-9)
        base = rp[bw].mean(axis=0) if bw.any() else rp[k_f]
        d = np.degrees(np.abs(mov - base)) if idx.size else np.zeros((0, 2))
        di = np.degrees(np.abs(rp[w6] - rp[k_f])) if idx.size else np.zeros((0, 2))
        mx = None if not d.size else [float(x) for x in d.max(axis=0)]
        out["g4_6"] = {"max_change_deg": mx, "window_s": [t_f, t_hi],
                       "mean_window_s": G4_ATT_MEAN_S,
                       "instant_max_change_deg": None if not di.size
                       else [float(x) for x in di.max(axis=0)],
                       "passed": bool(mx is not None and max(mx) <= G4_ATT_LIMIT_DEG + 1e-12)}
    else:
        out["g4_6"] = {"max_change_deg": None, "passed": None, "note": "no body_quat_wxyz"}
    # C-S8-71 ③ (record): end attitude change after FAULT (replaces the general attitude row)
    if roll_pitch_rad is not None and tp.size and t_fault is not None:
        rp = np.asarray(roll_pitch_rad, float)
        bw = (tp >= t_fault - G4_END_MEAN_S - 1e-9) & (tp <= t_fault + 1e-9)
        ew = tp >= tp[-1] - G4_END_MEAN_S - 1e-9
        aw = tp >= t_fault - 1e-9
        a_f = rp[bw].mean(axis=0) if bw.any() else rp[k_at(t_fault)]
        a_e = rp[ew].mean(axis=0)
        out["g4_end"] = {"attitude_at_fault_deg": [float(x) for x in np.degrees(a_f)],
                         "attitude_end_deg": [float(x) for x in np.degrees(a_e)],
                         "change_deg": [float(x) for x in np.degrees(a_e - a_f)],
                         "instant_max_abs_change_deg": None if not aw.any() else
                         [float(x) for x in np.degrees(np.abs(rp[aw] - a_f).max(axis=0))],
                         "fault_mean_window_s": [t_fault - G4_END_MEAN_S, t_fault],
                         "end_mean_window_s": [float(tp[-1]) - G4_END_MEAN_S, float(tp[-1])],
                         "axes": ["roll", "pitch"], "passed": None}
    else:
        out["g4_end"] = {"passed": None,
                         "note": "no body_quat_wxyz" if roll_pitch_rad is None else "no FAULT"}
    meta = dict(reground_meta or {})
    settings = meta.get("settings") if isinstance(meta.get("settings"), Mapping) else {}
    run = meta.get("run") if isinstance(meta.get("run"), Mapping) else {}
    tgt_meta = {t.get("leg"): t for t in (run.get("targets") or []) if isinstance(t, Mapping)}
    # G4-7 (C-S8-70 ③): judged only on a no-target run; zero output from t_f + d T_s
    k_tc = tc >= t_f - G4_TIME_TOL_S
    k_u = tc >= t_f + delay_s - G4_TIME_TOL_S
    k_tf = k_tc & ~k_u
    first_phase = str(ph[k_tc][0]) if k_tc.any() else None
    u_from = float(np.abs(u[k_u]).max()) if k_u.any() else None
    neg_ok = bool(not np.any(ph[k_tc] == FAULT_REGROUND_PHASE) and first_phase == "fault"
                  and u_from is not None and u_from <= G4_ZERO_U_M_S)
    end_reason = run.get("end_reason")
    if end_reason is not None:
        no_target, nt_src = str(end_reason) == G4_NO_TARGET_REASON, "controller meta end_reason"
    else:
        no_target, nt_src = not targets, "no meta: fault_reground_start target legs"
    out["g4_7"] = {"phase_at_t_f": first_phase,
                   "reground_rows_after_t_f": int(np.sum(ph[k_tc] == FAULT_REGROUND_PHASE)),
                   "zero_check_from_s": t_f + delay_s,
                   "max_abs_u_from_t_f_mm_s": None if u_from is None else u_from * 1e3,
                   "issued_u_at_t_f_sample_mm_s": None if not k_tf.any()
                   else {LEGS[i]: float(np.abs(u[k_tf, i]).max()) * 1e3 for i in range(4)},
                   "same_as_direct_fault": neg_ok, "end_reason": end_reason,
                   "no_target": no_target, "no_target_source": nt_src, "expect": expect,
                   "passed": neg_ok if no_target else None}
    # G4-8 (record)
    if entry is not None and t_fault is not None and t_fault > entry + G4_TIME_TOL_S:
        w = (tp >= entry - 1e-9) & (tp <= t_fault + 1e-9)
        k0 = int(np.clip(np.searchsorted(tp, entry - 1e-9), 0, max(tp.size - 1, 0)))
        s = np.asarray(s_motor_m, float)
        travel = {LEGS[i]: float(s[w, i].max() - s[k0, i]) * 1e3 for i in range(4)}
        wc = (tc >= entry - G4_TIME_TOL_S) & (tc < t_fault - G4_TIME_TOL_S)
        moving = {LEGS[i]: float(np.sum(wc & (u[:, i] > G4_ZERO_U_M_S)) * period)
                  for i in range(4)}
        # per-leg limit: the target's max_travel_m (P-S8-24 meta run.targets), else the
        # settings value, else 30 mm (323.5)
        cap_set = settings.get("max_travel_m")
        caps, srcs = {}, {}
        for g in LEGS:
            v = (tgt_meta.get(g) or {}).get("max_travel_m")
            if isinstance(v, int | float):
                caps[g], srcs[g] = float(v), "run.targets"
            elif isinstance(cap_set, int | float):
                caps[g], srcs[g] = float(cap_set), "settings"
            else:
                caps[g], srcs[g] = G4_TRAVEL_CAP_M, "323.5 cap 30 mm"
        leg_lim = settings.get("max_leg_duration_s")
        leg_lim = float(leg_lim) if isinstance(leg_lim, int | float) else G4_LEG_TIME_LIMIT_S
        tot_lim = settings.get("max_total_duration_s")
        tot_lim = float(tot_lim) if isinstance(tot_lim, int | float) else G4_TOTAL_TIME_LIMIT_S
        within = (all(travel[g] <= caps[g] * 1e3 + 1e-6 for g in LEGS)
                  and all(v <= leg_lim + 1e-9 for v in moving.values())
                  and t_fault - entry <= tot_lim + 1e-9)
        out["g4_8"] = {"travel_mm": travel, "moving_s": moving, "window_s": t_fault - entry,
                       "max_travel_mm": {g: caps[g] * 1e3 for g in LEGS},
                       "max_travel_source": srcs, "leg_time_limit_s": leg_lim,
                       "total_time_limit_s": tot_lim,
                       "controller_targets": {g: {k: t.get(k) for k in (
                           "sensor", "cues", "gap_m", "travel_m", "duration_s", "outcome",
                           "hold_count")}
                           for g, t in tgt_meta.items()},
                       "within_limits": bool(within), "passed": None}
    else:
        out["g4_8"] = {"passed": None, "within_limits": None,
                       "note": "no FAULT_REGROUND window"}
    # C-S8-70 ⑦: abort / D1 step-suspend events and the rev. 65 meta records
    aborts = named_events(names, REGROUND_ABORT_WARNING)
    susp = named_events(names, D1_STEP_SUSPENDED_INFO)
    out["g4_8"].update(
        abort_count=len(aborts),
        abort_events=[[e["t_s"], e["leg"], e["detail"]] for e in aborts],  # [t, reason, rest]
        step_suspended_count=len(susp),
        step_suspended_events=[[e["t_s"], e["leg"]] for e in susp],
        hold_count={g: t.get("hold_count") for g, t in tgt_meta.items()},
        max_filtered_attitude_change_rad=run.get("max_filtered_attitude_change_rad"),
        end_reason=end_reason)
    out["contacts"] = [[e["t_s"], e["leg"]] for e in named_events(names, REGROUND_CONTACT_EVENT)]
    out["limit_warnings"] = [[e["t_s"], e["leg"], e["detail"]]
                             for e in named_events(names, REGROUND_LIMIT_WARNING)]
    out["end_events"] = [[e["t_s"], e["leg"]] for e in named_events(names, REGROUND_END_EVENT)]
    out["controller_end_reason"] = run.get("end_reason")
    out["controller_meta"] = meta or None
    return out


def extend_force_limits_N(params) -> np.ndarray | None:
    """Per-leg extend force limit [N] (YAML ``legs.<leg>.cylinder.max_force_extend_N``, 210 bar
    relief; front 278.7 / rear 199.6 kN); None when the keys are absent."""
    try:
        legs = params.raw["legs"]
        return np.array([float(legs[n]["cylinder"]["max_force_extend_N"]) for n in LEGS])
    except (AttributeError, KeyError, TypeError):
        return None


def g4_of_case(case: Mapping[str, Any], f_min_N: float, params=None) -> dict[str, Any] | None:
    """:func:`g4_metrics` of a loaded ``run_S8C`` case (``s8_series.npz``, ``pads.npz``,
    controller events and meta; ``params`` for the extend force limits). None without a
    head-fault injection."""
    from outrigger_sim.frames import roll_pitch_from_quat

    extend_limit_N = None if params is None else extend_force_limits_N(params)

    res = case["result"]
    spec, _t_arm, t_first = head_fault_of(res)
    if not spec:
        return None
    t0 = float(res["settings"]["start_t_s"])
    series = load_series(Path(case["dir"])) if case.get("dir") else None
    pads = case.get("pads")
    if series is None or pads is None:
        return {"fault_leg": spec.get("leg"), "error": "missing s8_series.npz / pads.npz"}
    tp = np.asarray(pads["t"], float) - t0
    rp = None
    if "body_quat_wxyz" in pads:
        r, p = roll_pitch_from_quat(np.asarray(pads["body_quat_wxyz"], float))
        rp = np.column_stack([r, p])
    cm = res.get("controller_meta") or {}
    meta = cm.get("fault_reground") if isinstance(cm.get("fault_reground"), Mapping) else None
    # U-S8-74 (a): None tells g4_metrics to fall back to the force sign for G4-4 (b)
    air = np.asarray(pads["airborne"], bool) if "airborne" in pads else None
    out = g4_metrics(t_f=t_first, fault_leg=str(spec["leg"]), expect=spec.get("expect"),
                     phases=res.get("phases") or [], names=_event_names(case),
                     tc=np.asarray(series["t"], float) - t0, phase_series=series["phase"],
                     issued_u=series["issued_u"], tp=tp, airborne=air,
                     judged_force_N=judged_force_min(pads), f_cyl_N=pads["F_cyl"],
                     head_true_Pa=pads["head_pressure"], roll_pitch_rad=rp,
                     s_motor_m=pads["s_motor"], f_min_N=f_min_N, reground_meta=meta,
                     extend_limit_N=extend_limit_N, t_event_s=res.get("event_t_s"))
    out["injection"] = {"spec": spec, "arm_t_s": _t_arm, "first_applied_t_s": t_first,
                        "wrapper": res.get("head_fault"),
                        "delivered": head_delivered_summary(
                            None if not case.get("dir") else Path(case["dir"]),
                            str(spec["leg"]), t0)}
    return out


def load_head_delivered(case_dir: Path | None) -> dict[str, np.ndarray] | None:
    """C-S8-70 ⑥: arrays of ``<case>/head_fault_delivered.npz`` (``t`` absolute engine time,
    ``meas.head_pressure`` = reading before the injection, ``meas.head_pressure_delivered`` =
    reading the controller received, ``applied``); None without the file (runs before C-S8-70)."""
    if case_dir is None or not (Path(case_dir) / HEAD_DELIVERED_FILE).exists():
        return None
    with np.load(Path(case_dir) / HEAD_DELIVERED_FILE, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def head_delivered_alignment(case_dir: Path | None, z: Mapping[str, np.ndarray]
                             ) -> dict[str, Any]:
    """C-S8-71 ④: is ``head_fault_delivered.npz`` row-aligned with ``record/record.npz``
    (same row count, same ``t``, its ``meas.head_pressure`` bit-equal to the record's)? The record
    keeps the reading before the injection (its field schema is fixed, ``outrigger_sim.record``);
    the delivered reading lives only in the side file under :data:`HEAD_DELIVERED_KEY`."""
    p = None if case_dir is None else Path(case_dir) / "record" / "record.npz"
    if p is None or not p.exists():
        return {"record_npz": False}
    with np.load(p, allow_pickle=False) as rec:
        if "t" not in rec.files or "meas.head_pressure" not in rec.files:
            return {"record_npz": True, "aligned": False, "note": "record lacks t / head"}
        tr = np.asarray(rec["t"], float)
        hr = np.asarray(rec["meas.head_pressure"], float)
        has_key = HEAD_DELIVERED_KEY in rec.files
    td = np.asarray(z["t"], float)
    same_n = tr.size == td.size
    same_t = bool(same_n and np.array_equal(tr, td))
    same_h = bool(same_n and np.array_equal(hr, np.asarray(z["meas.head_pressure"], float),
                                            equal_nan=True))
    return {"record_npz": True, "record_rows": int(tr.size), "file_rows": int(td.size),
            "same_t": same_t, "record_head_equals_before": same_h,
            "aligned": bool(same_t and same_h),
            "record_has_delivered_key": bool(has_key),
            "note": "record/meas.head_pressure = reading before the injection; the delivered "
                    f"reading is {HEAD_DELIVERED_FILE}:{HEAD_DELIVERED_KEY} (row k = record "
                    "row k when aligned)"}


def head_delivered_summary(case_dir: Path | None, fault_leg: str, t0: float
                           ) -> dict[str, Any]:
    """Record of the delivered head reading (C-S8-70 ⑥): samples, applied samples, first applied
    time (relative), and the delivered - recorded difference on the fault leg (bar) / on the
    other legs (max |.|, bar; 0 expected)."""
    z = load_head_delivered(case_dir)
    if z is None:
        return {"available": False,
                "note": f"no {HEAD_DELIVERED_FILE}: record/meas.head_pressure is the reading "
                        "before the injection (spec rev. 65 333); re-insert from the wrapper meta"}
    j = LEGS.index(fault_leg)
    d = (np.asarray(z[HEAD_DELIVERED_KEY], float) - np.asarray(z["meas.head_pressure"], float))
    app = np.asarray(z["applied"], bool)
    t = np.asarray(z["t"], float) - t0
    others = [i for i in range(4) if i != j]
    fin = np.isfinite(d[:, j])
    return {"available": True, "file": HEAD_DELIVERED_FILE, "samples": int(t.size),
            "record_alignment": head_delivered_alignment(case_dir, z),  # C-S8-71 ④
            "applied_samples": int(app.sum()),
            "first_applied_t_s": float(t[app][0]) if app.any() else None,
            "fault_leg_delta_bar": None if not (app & fin).any()
            else [float(d[app & fin, j].min()) / 1e5, float(d[app & fin, j].max()) / 1e5],
            "fault_leg_nan_samples": int((app & ~fin).sum()),
            "other_legs_max_abs_delta_bar": float(np.nanmax(np.abs(d[:, others]))) / 1e5
            if t.size else None,
            "before_arm_max_abs_delta_bar": float(np.nanmax(np.abs(d[~app]))) / 1e5
            if (~app).any() else None}


G4_ROWS = (("g4_1", "G4-1 FAULT_REGROUND entry at the fault sample + head fault event", "judged"),
           ("g4_2", "G4-2 legs airborne at >= 2 of the samples t_f - 0.2 / - 0.1 / t_f are "
                    "re-ground targets (missed 0; false targets, late_airborne recorded)",
            "judged"),
           ("g4_3", "G4-3 FAULT within fault + 15 s, output 0 from FAULT + d T_s (d = 1; "
                    "FAULT-sample output recorded)", "judged"),
           ("g4_4", "G4-4 (main, U-S8-72 (a) / U-S8-74 (a)) from FAULT + 1 s to the run end every "
                    "leg's 0.5 s moving mean of the judged true force >= F_min and no pad "
                    "lift-off (airborne samples 0) (instantaneous minimum > 0 and vs F_min "
                    "recorded; undecidable when < 3 s)",
            "judged"),
           ("g4_5", "G4-5 re-ground [entry, FAULT + 1 s): healthy legs below F_min <= 0.5 s in "
                    "a row, faulty-leg F_cyl <= extend limit, true head <= 345 bar", "judged"),
           ("g4_6", "G4-6 0.5 s mean true roll / pitch vs the [t_f - 0.5, t_f] mean <= 0.5 deg",
            "judged"),
           ("g4_7", "G4-7 no-target run (end_reason no_target): FAULT at the fault sample, "
                    "output 0 from t_f + d T_s (as the direct FAULT; a record when targeted)",
            "judged"),
           ("g4_8", "G4-8 re-ground travel / time within the limits, hold counts, abort / D1 "
                    "step-suspend events (record)", "record"),
           ("g4_end", "G4-E end attitude change after FAULT: true roll / pitch mean over the "
                      "last 0.5 s minus the mean over [FAULT - 0.5 s, FAULT] (record; the general "
                      "READY / attitude rows are not applicable, C-S8-71)", "record"))
"""C-S8-68 row items (``C-S8-68 `` + text; G4-3 / G4-7 / G4-8 texts C-S8-70, G4-4 / G4-E
C-S8-71)."""


def g4_rows(cid: str, g: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Rows G4-1 ... G4-8 of one head-fault run (:func:`g4_metrics`). A row whose ``passed`` is
    None (G4-5 without a re-ground window, G4-7 outside the negative case, G4-8) is a record."""
    if g.get("error"):
        return [_row("C-S8-68 G4 head-fault run", cid, None, None, False, g["error"])]
    rows = []
    for key, text, kind in G4_ROWS:
        v = dict(g.get(key) or {})
        passed = v.pop("passed", None)
        k = kind if passed is not None else "record"
        if v.get("status") == "undecidable":  # 323.9 ②: G4-4 window < 3 s
            k = "hold"
        if key == "g4_2" and passed is not None:
            note = (f"targets {v.get('targets')}, airborne {v.get('truth_airborne')} "
                    f"(ms {v.get('airborne_ms_in_window')}), false targets "
                    f"{v.get('false_targets')} (record)")
        elif key == "g4_4" and v.get("mean05_min_kN") is not None:
            mn = v.get("min_from_fault_plus_1s_kN") or {}
            note = (f"fault leg {g.get('fault_leg')}, FAULT {g.get('fault_s')} s; 0.5 s mean "
                    f"min {min(v['mean05_min_kN'].values()):.2f} kN, no pad lift-off "
                    f"{v.get('no_lift')} ({v.get('airborne_source')}); instantaneous min "
                    f"{min(mn.values()):.2f} kN (> 0: {v.get('instant_min_positive')}; >= F_min "
                    f"{v.get('F_min_kN'):.3f} kN: {v.get('instant_min_ge_F_min')}, record)"
                    if mn else f"fault leg {g.get('fault_leg')}, FAULT {g.get('fault_s')} s")
        else:
            note = f"fault leg {g.get('fault_leg')}, t_f {g.get('t_f_s')} s, entry " \
                   f"{g.get('entry_s')} s, FAULT {g.get('fault_s')} s"
        rows.append(_row(f"C-S8-68 {text}", cid, v, None, passed, note, kind=k,
                         expect=g.get("expect")))
    return rows


def head_fault_expect(sm: Mapping[str, Any] | None) -> str | None:
    """``expect`` of the case's head-fault injection (``s8.event_spec.head_fault``), None
    without one."""
    hf = (((sm or {}).get("s8") or {}).get("event_spec") or {}).get(HEAD_FAULT_KEY)
    return None if not isinstance(hf, Mapping) else str(hf.get("expect"))


def apply_head_fault_na_rows(rows: list[dict[str, Any]],
                             sms: Mapping[str, Mapping[str, Any]]) -> int:
    """C-S8-71 ③ (spec rev. 66 338): the general rows :data:`G4_NA_ITEMS` of a head-fault
    injection run whose ``expect`` is in :data:`G4_NA_EXPECTS` become "not applicable (expected
    FAULT)" in place (``passed`` None, ``passed_raw`` kept, ``kind`` :data:`G4_NA_KIND`); the
    G4 rows (incl. the G4-E end attitude record) judge such a run. Returns the row count."""
    n = 0
    for r in rows:
        if r.get("item") not in G4_NA_ITEMS:
            continue
        exp = head_fault_expect(sms.get(r.get("case")))
        if exp is None or exp not in G4_NA_EXPECTS:
            continue
        if "passed_raw" not in r:
            r["passed_raw"] = r["passed"]
        r["passed"] = None
        r["kind_raw"], r["kind"] = r.get("kind"), G4_NA_KIND
        r["note"] = (f"C-S8-71: not applicable (expected FAULT, head-fault injection expect "
                     f"'{exp}'; see the C-S8-68 G4 rows and G4-E); " + str(r.get("note") or ""))
        n += 1
    return n


def judge_batch(batch_dir: Path, out_path: Path | None = None, *,
                root: Path | None = None, ref_batch: Path | None = None,
                lookup_batches: Sequence[Path] = (),
                deferred_ref: Path | None = None,
                harness_dir: Path | None = None) -> Path:
    """Judge a ``run_S8C.py`` batch; writes ``verify_S8C.json``. ``ref_batch``: an earlier batch
    whose ``verify_S8C.json`` metrics give the 213.6 TOUCH regression row (C-S8-19 ⑦);
    ``ref_batch`` and ``lookup_batches`` (their ``verify_S8C.json``) also give the C11 L1 twins
    and the missing auger levels of the trend groups (C-S8-22 ② / ⑤). ``deferred_ref``
    (C-S8-42, spec rev. 55 269.3 #2): folder holding the reference run of each case
    (``<deferred_ref>/<case id>``, e.g. the original MLJ batch for bundle D) for the per-leg
    deferred-leg comparison; relative paths from the project root; None = no reference columns."""
    from outrigger_sim.verify import s6_bundle_c as bc

    root = root or bc.PROJECT_ROOT
    ref_docs = _load_ref_docs([ref_batch, *lookup_batches])
    metrics, probes, sms, dirs = [], {}, {}, {}
    harness_runs: list[dict[str, Any]] | None = None  # C-S8-72, read on the first G1 case
    for d in sorted(p for p in Path(batch_dir).iterdir() if (p / "result.json").exists()):
        case, m, pr, params = _load(d)
        metrics.append(m)
        probes[m["case"]] = pr
        sms[m["case"]] = s8_case_metrics(case, m, params, pr)
        sms[m["case"]]["probe_7c_split"] = probe_7c_split(pr)  # U-S8-16
        if sms[m["case"]]["s8"].get("group") == MLJ_GROUP:  # U-S8-32 / 35, C-S8-24 / 29
            sms[m["case"]]["mlj"] = mlj_case_metrics(case, sms[m["case"]], params)
        sms[m["case"]].update(_rt_of_case(  # C-S8-37, C-S8-40 forced window masked
            case, d, forced=sms[m["case"]].get("forced_window"),
            f_min_N=float(params.control.F_min_cylinder_N)))  # C-S8-41
        if sms[m["case"]]["s8"].get("group") == G1_GROUP:  # C-S8-72 (spec rev. 67 345.2)
            if harness_runs is None:
                harness_runs = _g1_harness_runs(Path(root), harness_dir)
            sms[m["case"]]["g1"] = g1_case_metrics(case, sms[m["case"]], m, params,
                                                   harness_runs)
        dirs[m["case"]] = d
    d8_item = "D8 min true cylinder force >= F_min + 5 kN"
    rows = [r for r in bc.judge(metrics, probes, None) if r["item"] != d8_item]
    by_id = {m["case"]: m for m in metrics}
    for cid, sm in sms.items():
        rows.extend(case_rows(sm, by_id[cid]))
        s8 = sm["s8"]
        twin, src = None, None
        if s8.get("pair_fs0"):
            twin, src = sms.get(s8["pair_fs0"]), f"batch {s8['pair_fs0']}"
        elif s8.get("pair_fs0_external"):
            twin, src = _external(Path(root), s8["pair_fs0_external"]), \
                "/".join(s8["pair_fs0_external"])
        if src is not None:
            rows.extend(pair_rows_s8(sm, twin, source=src, kind_pair="fs0"))
        if s8.get("pair_l1") and float(s8.get("fs_kN") or 0.0) == 0.0:
            twin_l1, src_l1 = _lookup_sm(s8["pair_l1"], sms, ref_docs)  # C-S8-22 ⑤
            rows.extend(pair_rows_s8(sm, twin_l1, source=src_l1, kind_pair="l1"))
        if s8.get("ref_s7"):
            ref_dir = Path(root) / s8["ref_s7"][0] / s8["ref_s7"][1]
            ref_sm = _external(Path(root), s8["ref_s7"])
            ref_settings = None
            if (ref_dir / "result.json").exists():
                ref_settings = json.loads((ref_dir / "result.json").read_text(
                    encoding="utf-8")).get("settings")
            this_settings = json.loads((dirs[cid] / "result.json").read_text(
                encoding="utf-8")).get("settings")
            rows.extend(s7_regression_rows(sm, ref_sm, ref_label="/".join(s8["ref_s7"]),
                                           settings_this=this_settings,
                                           settings_ref=ref_settings))
    rows.extend(apply_rev43_rows(rows, sms))
    rows.extend(apply_rev46_rows(rows, sms))  # C-S8-22 ① ② ④
    rows.extend(level_trend_rows_s8(metrics, sms, ref_docs))  # C-S8-22 ②
    rows.extend(wika_pooled_rows(sms))  # control rev. 46 216.6 (1)
    item9 = [c for c, sm in sms.items() if sm["s8"].get("group") in ("N", "E")
             or sm["s8"].get("pair_judge")]
    rows.extend(item9_summary(sms, item9))
    rows.extend(i4_rows(sms, load_i4_expected(Path(root))))
    g4 = {cid: sm["g4_rr"] for cid, sm in sms.items()
          if sm.get("g4_rr") is not None and sm["s8"].get("group") == "E"}
    rows.append(_row("C-S8-14 E-group G4 RR summary (record, control rev. 42 212.4 check)", "*",
                     len(g4), 8, None,
                     "per case: relevel_predicted / reapproach start [s], mean RR command "
                     "[mm/s] between them, min true RR force [kN] and time, F_band [kN], twist "
                     "stiffness scale (run end) + C-S8-19 ⑤: scale_in_use / raw_ratio at the "
                     "event, per-round scale history, RR F_hat_cal - F_band at the re-approach "
                     "start vs 1.4 F_min", kind="record", g4_rr=g4,
                     scale_at_event={c: v.get("scale_at_event") for c, v in g4.items()}))
    ref_metrics = None
    if ref_batch is not None and (Path(ref_batch) / "verify_S8C.json").exists():
        ref_doc = json.loads((Path(ref_batch) / "verify_S8C.json").read_text(encoding="utf-8"))
        ref_metrics = {mm["case"]: mm for mm in ref_doc.get("metrics") or []}
    rows.extend(r44_gate_rows(sms, rows, ref_metrics,
                              None if ref_batch is None else str(ref_batch)))
    rows.extend(cb_rerun_rows(sms, by_id, rows, ref_docs))  # U-S8-23, spec rev. 46 216.8
    rows.extend(mlj_rows(sms))  # C-S8-27 / 30: judged cases of the main ML batch
    g1 = g1_rows(sms)  # C-S8-72 (spec rev. 67 345.2); empty without G1 cases
    rows.extend(g1)
    dref = None
    if deferred_ref is not None:  # C-S8-42: deferred legs vs the reference run of the case
        dref = Path(deferred_ref)
        if not dref.is_absolute():
            dref = Path(root) / dref
        for cid, sm in sms.items():
            attach_deferred_reference((sm.get("rt") or {}).get("deferred_min"), dref / cid,
                                      ref_label=str(deferred_ref))
    rows.extend(rt_rows(sms))  # C-S8-37: RT record + twist work (event cases)
    labels ={cid: crawler_label(sm) for cid, sm in sms.items()}
    rows.append(_row("S8-L5 crawler label of the batch (R41-5: one crawler contact per batch)",
                     "*", sorted(set(labels.values())), None, None,
                     "; ".join(f"{c}: {v}" for c, v in labels.items())[:2000], kind="record",
                     labels=labels))
    n_na = apply_head_fault_na_rows(rows, sms)  # C-S8-71 ③
    n_fail = sum(1 for r in rows if r["passed"] is False)
    n_hold = sum(1 for r in rows if r.get("kind") == "hold")
    out = out_path or Path(batch_dir) / "verify_S8C.json"
    doc = {"meta": {"batch": str(batch_dir), "module": __name__, "rows": len(rows),
                    "failed": n_fail, "hold": n_hold,
                    **({"not_applicable": n_na} if n_na else {}),  # C-S8-71 ③
                    "liftoff_window_s": LIFTOFF_WINDOW_S,
                    "sensor_share_N": SENSOR_SHARE_N,
                    "summary": judge_summary(rows),  # C-S8-41
                    **({"c_s8_72": {"rule": G1_RULE, "f_min_rule": G1_FMIN_RULE,
                                    "u75_rule": U75_RULE,
                                    "per_case": g1_summary(g1),
                                    "harness_runs": len(harness_runs or [])}}
                       if g1 else {}),
                    "judge_revision": JUDGE_REVISION_U75 + " on "
                                      + JUDGE_REVISION_U74 + " on "
                                      "C-S8-71 (spec rev. 66 338, U-S8-72 (a): G4-4 = 0.5 s "
                                      "mean min >= F_min and instantaneous min > 0, the "
                                      "instantaneous min vs F_min a record; general run / "
                                      "attitude / re-READY rows of head-fault runs not "
                                      "applicable, G4-E end attitude record) on "
                                      "C-S8-70 (spec rev. 65 333: G4-3 zero output from "
                                      "FAULT + d T_s, G4-4 0.5 s mean / last 2 s records, "
                                      "G4-7 on no-target runs only, F2 head-fault leg out "
                                      "from the arm time, G4-8 abort / step-suspend events, "
                                      "delivered head reading record) on "
                                      "C-S8-68 (spec rev. 64 323.7: FAULT entry = "
                                      "FAULT_REGROUND or FAULT, G4-1..8 rows of head-fault "
                                      "runs) on " + JUDGE_REVISION_REV56 + " on "
                                      + JUDGE_REVISION_REV55 + " on " + JUDGE_REVISION_REV54
                                      + " on " + JUDGE_REVISION_REV52
                                      + " on " + JUDGE_REVISION_REV50
                                      + " on rev. 49 (C-S8-27 / 29 / 32) and "
                                      "rev. 46 (C-S8-22: ① pressure-only F_min rows = M5 "
                                      "comparison, ② level trend grouped + reference levels, ③ "
                                      "forced window out of F2 / I1 (U-S8-24), ④ rod-pressure "
                                      "fallback = unexpected warning, ⑤ C11 twins from the "
                                      "reference batches, ⑥ R46-1 friction flag 0.1 / 0.75 kN "
                                      "(U-S8-25), WIKA std pooled per side; 216.8 CB rerun rows "
                                      "with the controller lock_valve premise (U-S8-23)) on "
                                      "rev. 45 (C-S8-21: "
                                      "F1 reading law, R45-2..4), rev. 44 (C-S8-19) and rev. 43 "
                                      "(C-S8-16)",
                    "lookup_batches": [label for label, _ in ref_docs],
                    "f1_law": {"sigma_mult": F1_LAW_SIGMA_MULT, "abs_N": F1_LAW_ABS_N,
                               "mean_N": F1_LAW_MEAN_N, "std_ratio": list(F1_LAW_STD_RATIO),
                               "fallback_b_const_N": F1_FALLBACK_CONST_N,
                               "span_share": F1_SPAN_SHARE},
                    "r45_flags_N": {"static": NEAR_STATIC_FLAG_N,
                                    "friction": f"{NEAR_FRICTION_FLAG_MIN_N:g} (F_s,leg = 0) / "
                                                f"{NEAR_FRICTION_FLAG_FS_N:g} (F_s,leg > 0), "
                                                "R46-1",
                                    "total": NEAR_TOTAL_FLAG_N, "air": AIR_RESIDUAL_FLAG_N,
                                    "low_probe_margin": LOW_PROBE_MARGIN_N,
                                    "low_probe_window_s": LOW_PROBE_WINDOW_S},
                    "f1_share": {"ideal_N": F1_CONST_SHARE_N["ideal"],
                                 "wika": f"{F1_CONST_SHARE_N['wika']:g} N + {F1_SPAN_SHARE:g} |F|"
                                         " (rev. 44 record row)",
                                 "near_fmin_N": NEAR_FMIN_SHARE_N,
                                 "air_residual_flag_N": AIR_RESIDUAL_FLAG_N},
                    "ref_batch": None if ref_batch is None else str(ref_batch),
                    "deferred_reference": None if dref is None else str(dref),  # C-S8-42
                    "replay_status": {c: (sm.get("item9") or {}).get("replay", {}).get("status")
                                      for c, sm in sms.items()},
                    # C-S8-40 (spec rev. 54 249): engine and per-leg delta_i of the default
                    "reading_delta": {c: {"engine": rp.get("engine"),
                                          "delta_N": rp.get("reading_delta_N")}
                                      for c, sm in sms.items()
                                      if (rp := (sm.get("item9") or {}).get("replay") or {})
                                      and "reading_delta_N" in rp},
                    "reading_rule": READING_BIAS_RULE, "twist_work_rule": RT_WORK_RULE},
           "rows": rows, "s8_metrics": sms, "metrics": metrics}
    out.write_text(json.dumps(doc, indent=1, default=bc._json_default, ensure_ascii=False),
                   encoding="utf-8")
    return out


# --- ML pilot judge (C-S8-22 ⑦, spec rev. 46 216.8 ML-0 ... ML-3) ---------------------------------

ML_VERIFY_NAME = "verify_S8ML.json"
ML_SENSOR_GRADES = ("ideal", "normal", "conservative", "old_worst", "legacy")
"""``contact_episode.normalize_sensor_meta``: pressure grade alone (P-S8-9)."""
PRE_LIFT_PHASES = ("idle", "check", "touch")


def ml_run_status(d: Path) -> dict[str, Any]:
    """ML-0 (C-S8-22 ⑦): status of one ML run folder from ``case.log`` (``outrigger_sim.batch``
    lines ``case <id> finished: <status>`` / ``case <id> failed``) and ``result.json``: ``ok``
    (finished ok with a result), ``failed`` (failed line, or finished without a result; the last
    exception line is kept) or ``running`` (no finish line yet)."""
    d = Path(d)
    log = d / "case.log"
    text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    has_res = (d / "result.json").exists()
    fin = [ln for ln in text.splitlines() if " finished: " in ln]
    err = [ln.strip() for ln in text.splitlines()
           if "Error" in ln and not ln.startswith(("20", " "))]
    if " failed" in text and ("finished: failed" in text or f"case {d.name} failed" in text):
        return {"status": "failed", "error": err[-1] if err else "failed (case.log)"}
    if fin:
        status = fin[-1].rsplit("finished: ", 1)[1].strip()
        if status == "ok" and has_res:
            return {"status": "ok"}
        return {"status": "failed", "error": f"finished: {status}, result.json {has_res}"}
    if has_res and not log.exists():
        return {"status": "ok"}  # folder without a batch log (copied / hand-made run)
    return {"status": "running"}


def _load_ml_case(d: Path) -> dict[str, Any]:
    d = Path(d)
    out: dict[str, Any] = {"dir": d,
                           "result": json.loads((d / "result.json").read_text(encoding="utf-8"))}
    ev = d / "controller_events.json"
    out["events"] = json.loads(ev.read_text(encoding="utf-8")) if ev.exists() else []
    ph = d / "probe_history.json"
    out["probes"] = json.loads(ph.read_text(encoding="utf-8")) if ph.exists() else []
    pads = d / "pads.npz"
    if pads.exists():
        with np.load(pads, allow_pickle=False) as z:
            out["pads"] = {k: z[k] for k in z.files}
    else:
        out["pads"] = None
    return out


def ml_probe_truth_rows(probes: Sequence[Sequence[Mapping[str, Any]]], pads: Mapping[str, Any],
                        t0: float) -> list[dict[str, Any]]:
    """R45-4 inputs of a run without the s6 probe metrics (ML): per stored probe result the
    load estimate ``E``, ``T_0`` (mean true rod force over 0.5 s before the leg's move start) and
    ``T_2`` (mean true rod force at the second hold end +- 0.1 s), ``s6_control._leg_truth``."""
    from outrigger_sim.verify import s6_control as s6

    tp = np.asarray(pads["t"], float) - t0
    out = []
    for i, rnd in enumerate(probes or []):
        for r in rnd:
            if not isinstance(r, Mapping):
                continue
            names = ("t_move_start_s", "t_first_hold_end_s", "t_second_hold_end_s")
            vals = [r.get(n) for n in names]
            times = (tuple(float(v) - t0 for v in vals)
                     if all(isinstance(v, int | float) and math.isfinite(v) for v in vals)
                     else None)
            if times is None or times[0] < tp[0]:
                continue
            truth = s6._leg_truth(pads, tp, int(r["leg_index"]), times, (times[0], times[2]))
            out.append({"round": i, "leg": LEGS[int(r["leg_index"])],
                        "load_estimate_kN": float(r["load_estimate_N"]) / 1e3,
                        "truth_cyl_kN": None if truth.start_load_N is None
                        else truth.start_load_N / 1e3,
                        "truth_end_kN": None if truth.end_load_N is None
                        else truth.end_load_N / 1e3})
    return out


def sensor_fault_injected(settings: Mapping[str, Any]) -> bool:
    """C-S8-26 ②: any pressure-sensor fault injection key (rod or head) in the settings."""
    return any(bool(_find_key(settings, k)) for k in SENSOR_FAULT_INJECTION_KEYS)


def named_events(events: Sequence[tuple[float, str]], prefix: str) -> list[dict[str, Any]]:
    """Events ``<prefix>:<leg>[:...]`` (relative times) split into leg and the rest."""
    out = []
    for t, name in events:
        parts = name.split(":")
        if parts[0] != prefix:
            continue
        out.append({"t_s": float(t), "leg": parts[1] if len(parts) > 1 else None,
                    "detail": ":".join(parts[2:]) or None})
    return out


def lift_intervals(t_s: np.ndarray, airborne: np.ndarray, t_from_s: float
                   ) -> dict[str, list[list[float]]]:
    """U-S8-30: per leg the contiguous airborne intervals ``[start, end]`` (times of ``t_s``)
    starting at or after ``t_from_s``; an interval open at the record end ends there. The
    interval length counts one sample period per airborne sample (1 ms pad record)."""
    t = np.asarray(t_s, float)
    a = np.asarray(airborne).astype(bool)
    dt = float(np.median(np.diff(t))) if t.size > 1 else 0.0
    out: dict[str, list[list[float]]] = {}
    for j, leg in enumerate(LEGS):
        x = a[:, j] & (t >= t_from_s - 1e-9)
        edges = np.flatnonzero(np.diff(np.concatenate(([0], x.astype(int), [0]))))
        out[leg] = [[float(t[s]), float(t[e - 1] + dt)] for s, e in zip(edges[::2], edges[1::2])]
    return out


# --- U-S8-32 / C-S8-27 ①: event legs vs adjacent legs of a settlement (spec rev. 48 218.5) ---

DIAGONAL_LEG = {"FL": "RR", "RR": "FL", "FR": "RL", "RL": "FR"}
U57_LIFT_SUM_S = 0.5
U57_GAP_M = 0.002
U57_CAP_S = 5.0
"""U57 (spec 62, U-S8-32): physical window ``[t_ev, min(primary last re-contact + T_3, t_ev +
5 s)]``; the summed lift of the two adjacent legs inside it <= 0.5 s, their pad rise <= 2 mm,
no adjacent lift after the window (``s8ml2_u57.py pair``, the rev. 48 numbers)."""
EVENT_LEG_CUM_S = 1.8
EVENT_LEG_RECONTACT_S = 3.0
"""U-S8-32 / U-S8-37 (spec rev. 49 219.3, ASSUMPTION): per event leg (settled leg + its
diagonal) the cumulative lift after the event <= 1.8 s, the last re-contact <= event + 3.0 s
(gate; covers the leg-damping sensitivity floor x 1/3, 2.93 s of D-S8-7 5.28.4), no FAULT in
the run."""
EVENT_LEG_RECONTACT_NOMINAL_S = 2.5
"""U-S8-37: 'nominal damping expectation' column of the event-leg row (flag only, not a gate;
the rev. 48 gate). 219.8: two or more nominal-damping runs above it re-open the damping check."""


def poly345(x: np.ndarray) -> np.ndarray:
    """``ChFunctionPoly345`` shape on [0, 1] (the ground-patch profile of a settlement)."""
    x = np.clip(np.asarray(x, float), 0.0, 1.0)
    return 10.0 * x ** 3 - 15.0 * x ** 4 + 6.0 * x ** 5


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """``(first, last)`` sample indices of the True runs of ``mask``."""
    e = np.diff(np.concatenate(([0], np.asarray(mask).astype(int), [0])))
    return list(zip(np.flatnonzero(e == 1), np.flatnonzero(e == -1) - 1))


def settle_lift_split(t_s: np.ndarray, airborne: np.ndarray, ball_z_m: np.ndarray,
                      t_ev_s: float, settle_leg: str, depth_m: float, ramp_s: float, *,
                      t3_s: float, fault_t_s: float | None = None,
                      cap_s: float = U57_CAP_S, fault_gate: bool = True,
                      fault_cause: str | None = None) -> dict[str, Any]:
    """U-S8-32 / C-S8-27 ① split of the pad lift after a settlement (1 ms pad record; times
    ``t_s`` and ``t_ev_s`` on the same clock).

    * event legs = the settled leg and its diagonal (spec rev. 48 218.5: a rear settlement
      lifts the settled pad, a front one tips the body and lifts the diagonal rear pad);
      adjacent legs = the other two (U57);
    * primary = the event leg with the longest cumulative lift; window end = min(its last
      re-contact + ``t3_s``, ``t_ev + cap_s``) (``t_ev + t3_s`` when no event leg lifted, as
      ``s6_control.event_transient_window`` when RR never lifted);
    * gap of a lift = rise of the pad ball centre (world z) since the lift start minus the
      ground-patch drop since then (settled leg, Poly345 profile; other legs on the fixed floor);
    * a last re-contact is ``None`` when the leg is still lifted at the record end.
    Adjacent lift time is summed over both adjacent legs (the rev. 48 numbers).

    ``fault_gate`` False (C-S8-34 ②, ML judge): the FAULT is judged in its own ML-0 row by cause
    (``fault_cause``), so the event-leg row records it but does not fail on it (no duplicate
    failure); the MLJ rows keep the default (FAULT 0 in the event-leg row)."""
    t = np.asarray(t_s, float)
    air = np.asarray(airborne, bool) & (t >= t_ev_s - 1e-9)[:, None]
    dt = float(np.median(np.diff(t))) if t.size > 1 else 0.0
    zb = np.asarray(ball_z_m, float)
    sl = LEGS.index(settle_leg)
    zg = np.zeros_like(zb)
    if ramp_s and ramp_s > 0.0:
        zg[:, sl] = -float(depth_m) * poly345((t - t_ev_s) / float(ramp_s))
    else:
        zg[:, sl] = np.where(t >= t_ev_s, -float(depth_m), 0.0)

    def gap(j: int, a: int, b: int) -> float:
        return float(((zb[a:b + 1, j] - zb[a, j]) - (zg[a:b + 1, j] - zg[a, j])).max())

    runs = {leg: _runs(air[:, j]) for j, leg in enumerate(LEGS)}
    cum = {leg: float(sum(t[b] - t[a] + dt for a, b in runs[leg])) for leg in LEGS}
    event_legs = (settle_leg, DIAGONAL_LEG[settle_leg])
    adjacent = tuple(leg for leg in LEGS if leg not in event_legs)
    end_open = t.size - 1

    def last_recontact(leg: str) -> float | None:
        r = runs[leg]
        if not r:
            return None
        return None if r[-1][1] >= end_open else float(t[r[-1][1]] + dt)

    ev = {}
    for leg in event_legs:
        j = LEGS.index(leg)
        rc = last_recontact(leg)
        ev[leg] = {"cum_s": cum[leg], "lifts": len(runs[leg]),
                   "first_lift_rel_s": None if not runs[leg] else float(t[runs[leg][0][0]] - t_ev_s),
                   "last_recontact_rel_s": None if rc is None else rc - t_ev_s,
                   "lifted_at_end": bool(runs[leg]) and rc is None,
                   "gap_max_m": max((gap(j, a, b) for a, b in runs[leg]), default=0.0)}
    primary = max(event_legs, key=lambda leg: cum[leg])
    if cum[primary] <= 0.0:
        w_end = min(t_ev_s + t3_s, t_ev_s + cap_s)
        primary = None
    else:
        rc = last_recontact(primary)
        w_end = t_ev_s + cap_s if rc is None else min(rc + t3_s, t_ev_s + cap_s)
    adj_sum, adj_gap, outside, per_leg = 0.0, 0.0, 0.0, {}
    for leg in adjacent:
        j = LEGS.index(leg)
        for a, b in runs[leg]:
            dur = float(t[b] - t[a] + dt)
            if t[a] <= w_end + 1e-12:
                adj_sum += dur
                adj_gap = max(adj_gap, gap(j, a, b))
                per_leg[leg] = per_leg.get(leg, 0.0) + dur
            else:
                outside += dur
    u57_pass = bool(adj_sum <= U57_LIFT_SUM_S + 1e-9 and adj_gap <= U57_GAP_M + 1e-12
                    and outside == 0.0)
    lifted = [leg for leg in event_legs if cum[leg] > 0.0]
    cum_max = max((cum[leg] for leg in event_legs), default=0.0)
    rcs = [ev[leg]["last_recontact_rel_s"] for leg in lifted]
    rc_max = None if any(r is None for r in rcs) else max(rcs, default=0.0)
    fault_after = fault_t_s is not None and fault_t_s >= t_ev_s - 1e-9
    event_pass = bool(cum_max <= EVENT_LEG_CUM_S + 1e-9 and rc_max is not None
                      and rc_max <= EVENT_LEG_RECONTACT_S + 1e-9
                      and (fault_t_s is None or not fault_gate))
    # U-S8-37: the former 2.5 s gate stays as a flag column (nominal damping expectation)
    nominal_ok = None if rc_max is None else bool(rc_max <= EVENT_LEG_RECONTACT_NOMINAL_S + 1e-9)
    return {"settle_leg": settle_leg, "depth_m": float(depth_m), "ramp_s": float(ramp_s),
            "settle_speed_mm_s": None if not ramp_s else float(depth_m) / float(ramp_s) * 1e3,
            "event_legs": list(event_legs), "adjacent_legs": list(adjacent),
            "cum_lift_s": cum, "any_lift": any(v > 0.0 for v in cum.values()),
            "event": ev, "primary": primary,
            "event_cum_max_s": cum_max, "event_recontact_max_rel_s": rc_max,
            "fault_t_s": fault_t_s, "fault_after_event": bool(fault_after),
            "fault_gate": bool(fault_gate), "fault_cause": fault_cause,
            "event_pass": event_pass,
            "event_recontact_gate_s": EVENT_LEG_RECONTACT_S,
            "event_recontact_nominal_s": EVENT_LEG_RECONTACT_NOMINAL_S,
            "event_recontact_within_nominal": nominal_ok,
            "window_end_rel_s": float(w_end - t_ev_s), "t3_s": float(t3_s),
            "window_capped": bool(w_end >= t_ev_s + cap_s - 1e-9),
            "adjacent_sum_s": adj_sum, "adjacent_per_leg_s": per_leg,
            "adjacent_gap_max_m": adj_gap, "adjacent_outside_window_s": outside,
            "u57_pass": u57_pass,
            "rule": "U-S8-32 (spec rev. 48 218.5) / U-S8-37 (rev. 49 219.3): event legs = "
                    "settled + diagonal, adjacent = the other two; U57 physical window (spec 62) "
                    "on the adjacent legs; event legs: cumulative lift <= 1.8 s, last "
                    "re-contact <= event + 3.0 s (gate; <= 2.5 s nominal-damping flag column), "
                    "FAULT 0 (ASSUMPTION)"}


def _t3_of_level(level: str | None) -> tuple[float, bool]:
    """``T_3`` of the auger level (``s6_control.THREE_POINT_ROCKING_PERIOD_S``) and whether
    it is the top value used for another level (note ``T3_from_top_level``)."""
    from outrigger_sim.verify import s6_control as s6

    table = s6.THREE_POINT_ROCKING_PERIOD_S
    lv = level if level in table else "top"
    return float(table[lv]), lv != "top"


def u_s8_32_rows(case_id: str, sp: Mapping[str, Any] | None, *, kind_event: str = "judged",
                 label: str = "") -> list[dict[str, Any]]:
    """The two U-S8-32 rows of one settlement (``settle_lift_split`` result ``sp``): adjacent
    legs U57 (gate) and event legs (separate row, ASSUMPTION thresholds)."""
    if not sp:
        return []
    ev = sp["event"]
    pre = f"{label} " if label else ""
    note = (f"settle {sp['settle_leg']} {sp['depth_m'] * 1e3:.1f} mm / {sp['ramp_s']:g} s"
            + ("" if sp["settle_speed_mm_s"] is None
               else f" ({sp['settle_speed_mm_s']:.0f} mm/s)")
            + f"; window event .. +{sp['window_end_rel_s']:.2f} s (T3 {sp['t3_s']:g} s"
            + (", capped" if sp["window_capped"] else "") + ")")
    rows = [_row(f"{pre}U-S8-32 adjacent legs U57: lift sum <= {U57_LIFT_SUM_S:g} s, gap <= "
                 f"{U57_GAP_M * 1e3:g} mm in the physical window, 0 outside", case_id,
                 [round(sp["adjacent_sum_s"], 4), round(sp["adjacent_gap_max_m"] * 1e3, 3),
                  round(sp["adjacent_outside_window_s"], 4)],
                 [U57_LIFT_SUM_S, U57_GAP_M * 1e3, 0.0], sp["u57_pass"],
                 f"{note}; adjacent {sp['adjacent_legs']} per leg "
                 f"{ {k: round(v, 3) for k, v in sp['adjacent_per_leg_s'].items()} }",
                 split=sp)]
    rc = sp["event_recontact_max_rel_s"]
    nominal_s = sp.get("event_recontact_nominal_s", EVENT_LEG_RECONTACT_NOMINAL_S)
    within = sp.get("event_recontact_within_nominal")
    if within is None and rc is not None:  # split computed before U-S8-37
        within = bool(rc <= nominal_s + 1e-9)
    flag = ("" if within is not False else
            f"; FLAG re-contact {rc:.3f} s > {nominal_s:g} s (nominal damping expectation, "
            "U-S8-37 display only)")
    rows.append(_row(f"{pre}U-S8-32 event legs (settled + diagonal): cumulative lift <= "
                     f"{EVENT_LEG_CUM_S:g} s, last re-contact <= event + "
                     f"{EVENT_LEG_RECONTACT_S:g} s (U-S8-37; column <= {nominal_s:g} s nominal "
                     "damping, display), FAULT 0 (ASSUMPTION)", case_id,
                     [round(sp["event_cum_max_s"], 4), None if rc is None else round(rc, 4),
                      sp["fault_t_s"], within],
                     [EVENT_LEG_CUM_S, EVENT_LEG_RECONTACT_S, None, f"<= {nominal_s:g} s (flag)"],
                     sp["event_pass"],
                     f"{note}{flag}; primary {sp['primary']}; per event leg "
                     + "; ".join(f"{leg} cum {v['cum_s']:.3f} s, lifts {v['lifts']}, "
                                 f"re-contact {v['last_recontact_rel_s']}, gap "
                                 f"{v['gap_max_m'] * 1e3:.1f} mm" for leg, v in ev.items())
                     + ("" if sp["fault_t_s"] is None
                        else f"; FAULT at {sp['fault_t_s']:.2f} s"
                        + ("" if sp.get("fault_gate", True) else
                           f" (cause {sp.get('fault_cause')}: judged in the ML-0 FAULT rows, "
                           "not counted here, C-S8-34 ②)")),
                     kind=kind_event, split=sp, recontact_within_nominal=within))
    return rows


HEAD_FAULT_REASON_INFO = "INFO_HEAD_PRESSURE_FAULT_REASON"
"""P-S8-14 ③ (spec rev. 48 218.4): ``INFO_HEAD_PRESSURE_FAULT_REASON:<leg>:<D1 step|range|
current|stuck>`` (C-S8-27 ②: the FAULT rows carry it; absent before P-S8-14)."""


def _step_rule_of(res: Mapping[str, Any]) -> str | None:
    """C-S8-28: the D1 step rule the run used (``settings.settings_refreshed.
    two_pressure_settings.step_rule`` of an episode, else ``controller_meta`` keys)."""
    tp = ((res.get("settings") or {}).get("settings_refreshed") or {}).get(
        "two_pressure_settings")
    if isinstance(tp, Mapping) and tp.get("step_rule") is not None:
        return str(tp["step_rule"])
    v = _find_key(res.get("controller_meta") or {}, "step_rule")
    return None if v is None else str(v)


def forced_event_record(res: Mapping[str, Any], fw: Mapping[str, Any], pads: Mapping[str, Any],
                        t0: float, t_end_rel_s: float, f_min_N: float, *,
                        t_sample_rel_s: np.ndarray | None = None,
                        rod_weight_N: Sequence[float] | None = None,
                        f_sample_N: np.ndarray | None = None) -> dict[str, Any]:
    """C-S8-27 ③ (U-S8-34): the forced-retract event of an ML episode, from the 1 ms truth:
    speed, depth, window (start .. done), true F < F_min and lift inside the window and after
    it (any leg; ``judged_force_min``), minimum true force after the window. With the 10 Hz
    sample times ``t_sample_rel_s`` also the 203.1 event (U-S8-39,
    :func:`forced_event_203_1`)."""
    fr = res.get("forced_retract") or {}
    ep = (res.get("settings") or {}).get("episode") or {}
    tp = np.asarray(pads["t"], float) - t0
    fmin = judged_force_min(pads)
    air = np.asarray(pads["airborne"], bool) if "airborne" in pads else np.zeros(fmin.shape,
                                                                                 bool)
    a, b = float(fw["start_s"]), float(fw["end_s"])
    c = b + ML_MASK_EXTRA_S
    win = (tp >= a - 1e-9) & (tp <= b + 1e-9)
    tail = (tp > b + 1e-9) & (tp <= c + 1e-9)
    post = tp > c + 1e-9
    out: dict[str, Any] = {"leg": fw.get("leg"), "depth_m": ep.get("depth_m"),
                           "speed_fraction": ep.get("speed_fraction"),
                           "speed_m_s": fr.get("speed_m_s"), "window_s": [a, b],
                           "done_s": fw.get("done_s"), "others": fw.get("others"),
                           "periods": {"window": "start .. done", "tail": "done .. done + 3 s "
                                       "(the former mask tail)", "after": "done + 3 s .. end"},
                           "force": "1 ms judged_force_min, any leg"}
    for name, sel in (("window", win), ("tail", tail), ("after", post)):
        f = fmin[sel]
        out[f"{name}_below_F_min"] = bool(f.size and (f < f_min_N).any())
        out[f"{name}_below_F_min_legs"] = [LEGS[j] for j in range(4)
                                           if f.size and (f[:, j] < f_min_N).any()]
        out[f"{name}_lift"] = bool(air[sel].any())
        out[f"{name}_min_kN"] = None if not f.size else float(f.min()) / 1e3
        out[f"{name}_lift_legs"] = [LEGS[j] for j in range(4) if air[sel][:, j].any()] \
            if f.size else []
    if t_sample_rel_s is not None:
        out["event_203_1"] = forced_event_203_1(pads, tp, np.asarray(t_sample_rel_s, float),
                                                a, b, f_min_N, rod_weight_N, fw.get("leg"),
                                                f_sample_N)
    return out


def _record_truth_at(case_dir: Path, t_abs: np.ndarray, key: str) -> np.ndarray | None:
    """Runner record (``record/record.npz``) values of ``key`` at the times ``t_abs`` (the
    control instants; nearest earlier-or-equal record row). None without the record / key."""
    p = Path(case_dir) / "record" / "record.npz"
    if not p.exists():
        return None
    with np.load(p, allow_pickle=False) as z:
        if key not in z.files:
            return None
        tr, v = np.asarray(z["t"], float), np.asarray(z[key], float)
    idx = np.clip(np.searchsorted(tr, np.asarray(t_abs, float) - 1e-9), 0, tr.size - 1)
    return v[idx]


LIFT_TRUE_LIMIT_N = 500.0
"""203.1 lift L: window minimum of ``F_i + m_i g`` <= 0.5 kN (ASSUMPTION of 203.1)."""


def forced_event_203_1(pads: Mapping[str, Any], tp_rel_s: np.ndarray, t_sample_rel_s: np.ndarray,
                       start_s: float, end_s: float, f_min_N: float,
                       rod_weight_N: Sequence[float] | None, forced_leg: str | None,
                       f_sample_N: np.ndarray | None = None) -> dict[str, Any]:
    """U-S8-39 (spec rev. 49 219.5): the forced-retract event in the 203.1 definition. Every
    10 Hz sample ``k`` with ``t_k`` in the forced window ``[start, done]`` classifies its window
    ``(t_{k-1}, t_k]`` per leg from the 1 ms record ``F_cyl_min_interval`` (the ML label rule):
    lift L when ``min F + m g <= 0.5 kN``, low load U when not L and ``min F < F_min``. The
    episode counts as U-or-L when any leg has such a window (``forced_leg_*``: the forced leg
    only). ``f_sample_N`` (10 Hz instantaneous true rod force at the sample instants, the
    rev. 48 count) gives the reference column ``inst_10hz_below_F_min``."""
    f1 = np.asarray(pads["F_cyl_min_interval"], float)
    w = np.zeros(f1.shape[1]) if rod_weight_N is None else np.asarray(rod_weight_N, float)
    t = np.asarray(t_sample_rel_s, float)
    ks = np.flatnonzero((t >= start_s - 1e-9) & (t <= end_s + 1e-9))
    u_any = np.zeros(4, bool)
    l_any = np.zeros(4, bool)
    n_win, first = 0, None
    for k in ks:
        if k == 0:
            continue
        sel = (tp_rel_s > t[k - 1] + 1e-9) & (tp_rel_s <= t[k] + 1e-9)
        if not sel.any():
            continue
        n_win += 1
        m = f1[sel].min(axis=0)
        is_l = m + w <= LIFT_TRUE_LIMIT_N
        is_u = ~is_l & (m < f_min_N)
        if (is_l | is_u).any() and first is None:
            first = float(t[k])
        l_any |= is_l
        u_any |= is_u
    j = LEGS.index(forced_leg) if forced_leg in LEGS else None
    out: dict[str, Any] = {
        "windows": n_win, "U_or_L": bool((u_any | l_any).any()), "L": bool(l_any.any()),
        "U_legs": [LEGS[i] for i in range(4) if u_any[i]],
        "L_legs": [LEGS[i] for i in range(4) if l_any[i]],
        "forced_leg_U_or_L": None if j is None else bool(u_any[j] or l_any[j]),
        "forced_leg_L": None if j is None else bool(l_any[j]),
        "first_window_end_s": first,
        "rule": "U-S8-39 / 203.1: 10 Hz windows (t_k-1, t_k] with t_k in [start, done], 1 ms "
                "F_cyl_min_interval per leg; L: min F + m g <= 0.5 kN, U: not L and min F < "
                "F_min; any leg (forced_leg_*: forced leg only)"}
    if f_sample_N is not None:
        fs = np.asarray(f_sample_N, float)[ks]
        out["inst_10hz_below_F_min"] = bool(fs.size and (fs < f_min_N).any())
        out["inst_10hz_below_F_min_legs"] = [LEGS[i] for i in range(4)
                                             if fs.size and (fs[:, i] < f_min_N).any()]
        out["inst_10hz_rule"] = ("reference column (rev. 48 count): true rod force of the "
                                 "runner record at the 10 Hz control instants")
    return out


ML_MASK_RULE = ("C-S8-27 ④ / U-S8-34 (spec rev. 48 218.13): mask = FAULT entry .. run end "
                "(fault_t_s); the forced-retract window is no longer masked for "
                "ForcedRetract(others='controller') (U-S8-34, in-window products recorded only); "
                "pre-U-S8-27 episodes (every leg held to the run end) keep start .. end + 3 s")


def ml_episode_mask(fw: Mapping[str, Any] | None, fault_t_s: float | None, t_end_s: float,
                    t0: float) -> dict[str, Any] | None:
    """C-S8-27 ④ / U-S8-34: the ML exclusion mask of one run (relative times; one interval,
    the union of the reasons, each running to the run end): FAULT entry .. run end; a
    pre-U-S8-27 ``ForcedRetract(others='zero')`` window start .. run end. A
    ``ForcedRetract(others='controller')`` window is not masked any more (U-S8-34). None when
    nothing is masked."""
    parts = []
    if fault_t_s is not None:
        parts.append(("fault", float(fault_t_s)))
    if fw is not None and fw.get("others") != "controller":
        parts.append(("forced_hold_all_legs", float(fw["start_s"])))
    if not parts:
        return None
    start = min(p[1] for p in parts)
    end = max(float(t_end_s), start + 1e-6)
    return {"start_s": start, "end_s": end, "start_engine_s": start + t0,
            "end_engine_s": end + t0, "reasons": [p[0] for p in parts],
            "fault_t_s": None if fault_t_s is None else float(fault_t_s), "rule": ML_MASK_RULE}


# --- C-S8-32: D1'' actual head-step ratio (spec rev. 49 219.2 (c)) ----------------------------

D1PP_STEP_BAR = 100.0
"""D1'' candidate: a one-period head-reading change above 100 bar (``s6_control_spec`` 218.4)."""
D1PP_RATIO_FLAG = 0.4
"""C-S8-32: flag of the record row (219.12 ASSUMPTION; the D1'' threshold stays 0.5)."""
D1PP_FS_GRADES_KN = (0.0, 2.5, 5.0)
"""F_s grades of the run mean (219.2 table): 0 / <= 2.5 / <= 5 / > 5 kN."""
D1PP_READY_WINDOW_S = 60.0
D1PP_READY_MIN_SAMPLES = 3
"""``M_eff`` = median of ``sum F_hat / f_z`` over the last READY stay (last 60 s, >= 3 samples),
spec 219.2 R41-1 (the controller's ``median`` calibration)."""
D1PP_RULE = ("C-S8-32 (spec rev. 49 219.2 (c), 219.11): offline recomputation from the record "
             "(not the monitor's INFO events, which carry no ratio). Candidate = 10 Hz head "
             "reading step |dp_h,i| > 100 bar (record meas.head_pressure) with the crawler "
             "lifted in the period before (phase not idle / check / touch / fault, the run "
             "without a pressure-sensor fault injection); r_k = sum F_hat_cal - M_eff (f_z - "
             "(alpha x r_C1)_z), F_hat_cal = s8_series F_nominal_N (F_hat_N where NaN), f_z = "
             "r8 imu_samples[k, -1, 2], alpha = (gyro[k, -1] - gyro[k, -2]) / T_imu from r8 "
             "imu_gyro_samples (C-S8-31; absent in older records -> uncorrected), r_C1 = IMU C1 "
             "- superstructure COM of the run's level; M_eff = READY median (last stay, 60 s, "
             ">= 3 samples), else the YAML superstructure mass; ratio = |r_k - r_k-1| / "
             "(|dp_h,i| A_p,i). F_s grade = run mean of the per-leg pads F_seal_limit maximum.")


def _fs_grade(fs_kN: float | None) -> str:
    if fs_kN is None or not math.isfinite(fs_kN):
        return "unknown"
    if fs_kN <= 1e-6:
        return "0"
    if fs_kN <= D1PP_FS_GRADES_KN[1] + 1e-9:
        return "<=2.5"
    if fs_kN <= D1PP_FS_GRADES_KN[2] + 1e-9:
        return "<=5"
    return ">5"


def run_fs_mean_kN(pads: Mapping[str, Any] | None, settings: Mapping[str, Any]) -> float | None:
    """Run-mean seal friction level [kN]: mean over the legs of the pads ``F_seal_limit``
    maximum, else the case ``fs_kN`` (front) with the rear x 0.833 (plant rule)."""
    if pads is not None and "F_seal_limit" in pads:
        lim = np.asarray(pads["F_seal_limit"], float)
        if lim.size and np.isfinite(lim).any():
            return float(np.nanmean(np.nanmax(lim, axis=0))) / 1e3
    fs = (settings.get("s8") or {}).get("fs_kN")
    if fs is None:
        fs = (settings.get("ml_base") or {}).get("fs_kN")
    if fs is None:
        return None
    fs = float(fs)
    return float(np.mean([fs, fs, REAR_FS_SCALE * fs, REAR_FS_SCALE * fs]))


def d1pp_step_ratios(case_dir: Path, params, *, settings: Mapping[str, Any],
                     pads: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    """C-S8-32: the D1'' ratio ``|dr| / J`` of every actual head step > 100 bar of one run
    (:data:`D1PP_RULE`). None without ``r8_series`` / ``s8_series`` / record."""
    from outrigger_sim.sensors.imu import IMU_MOUNT_C1_BODY_M

    d = Path(case_dir)
    r8p, s8p, recp = d / "r8_series.npz", d / "s8_series.npz", d / "record" / "record.npz"
    if not (r8p.exists() and s8p.exists() and recp.exists()):
        return None
    with np.load(r8p, allow_pickle=False) as z:
        t = np.asarray(z["t"], float)
        phase = np.char.lower(np.asarray(z["phase"]).astype(str))
        imu = np.asarray(z["imu_samples"], float) if "imu_samples" in z.files else None
        gyro = (np.asarray(z["imu_gyro_samples"], float) if "imu_gyro_samples" in z.files
                else None)
    if imu is None:
        return {"steps": [], "note": "no imu_samples in r8_series"}
    with np.load(s8p, allow_pickle=False) as z:
        f_cal = np.asarray(z["F_nominal_N"], float) if "F_nominal_N" in z.files else None
        f_hat = np.asarray(z["F_hat_N"], float)
    f_sum_src = f_hat if f_cal is None else np.where(np.isfinite(f_cal), f_cal, f_hat)
    f_sum = f_sum_src.sum(axis=1)
    head = _record_truth_at(d, t, "meas.head_pressure")
    if head is None:
        return {"steps": [], "note": "no meas.head_pressure in the record"}
    a_p, _, _ = cylinder_areas_m2(params, pads)
    fz = imu[:, -1, 2]
    arm = np.asarray(IMU_MOUNT_C1_BODY_M, float) - np.asarray(
        params.superstructure.mass_properties.com_m, float)
    t_imu = float(np.median(np.diff(t))) / imu.shape[1] if t.size > 1 else 0.01
    lever = np.zeros(t.size)
    has_gyro = gyro is not None and gyro.shape[1] >= 2
    if has_gyro:
        alpha = (gyro[:, -1, :] - gyro[:, -2, :]) / t_imu
        lever = alpha[:, 0] * arm[1] - alpha[:, 1] * arm[0]
        has_gyro = bool(np.isfinite(lever).any())
        lever = np.where(np.isfinite(lever), lever, 0.0)
    m_nom = float(params.superstructure.mass_properties.mass_kg)
    lifted = ~np.isin(phase, ("idle", "check", "touch", *FAULT_ENTRY_PHASES))
    ready = phase == "ready"
    injected = sensor_fault_injected(settings)
    steps: list[dict[str, Any]] = []
    for k in range(1, t.size):
        if injected or not lifted[k - 1] or phase[k] in FAULT_ENTRY_PHASES:
            continue
        dp = head[k] - head[k - 1]
        legs = np.flatnonzero(np.isfinite(dp) & (np.abs(dp) > D1PP_STEP_BAR * 1e5))
        if legs.size == 0:
            continue
        # M_eff: the last READY stay before k (contiguous), its last 60 s, >= 3 samples
        idx = np.flatnonzero(ready[:k])
        m_eff, m_src = m_nom, "yaml_superstructure_mass"
        if idx.size:
            end = idx[-1]
            start = end
            while start > 0 and ready[start - 1]:
                start -= 1
            stay = np.arange(start, end + 1)
            stay = stay[t[stay] >= t[end] - D1PP_READY_WINDOW_S - 1e-9]
            ratios = f_sum[stay] / fz[stay]
            ratios = ratios[np.isfinite(ratios)]
            if ratios.size >= D1PP_READY_MIN_SAMPLES:
                m_eff, m_src = float(np.median(ratios)), "ready_median"
        r_now = f_sum[k] - m_eff * (fz[k] - lever[k])
        r_prev = f_sum[k - 1] - m_eff * (fz[k - 1] - lever[k - 1])
        r_now0 = f_sum[k] - m_eff * fz[k]
        r_prev0 = f_sum[k - 1] - m_eff * fz[k - 1]
        for j in legs:
            jf = abs(float(dp[j])) * float(a_p[j])
            steps.append({"t_s": float(t[k]), "leg": LEGS[j], "dp_bar": float(dp[j]) / 1e5,
                          "J_kN": jf / 1e3, "dr_kN": float(r_now - r_prev) / 1e3,
                          "ratio": float(abs(r_now - r_prev) / jf),
                          "ratio_uncorrected": float(abs(r_now0 - r_prev0) / jf),
                          "lever_used": has_gyro, "M_eff_kg": m_eff, "M_eff_source": m_src,
                          "phase_before": str(phase[k - 1])})
    finite = [s["ratio"] for s in steps if math.isfinite(s["ratio"])]
    return {"steps": steps, "ratio_max": max(finite, default=None),
            "lever_correction_available": has_gyro, "fault_injected_run_skipped": injected,
            "lever_arm_m": arm.tolist(), "t_imu_s": t_imu}


def d1pp_ratio_rows(per_run: Mapping[str, Mapping[str, Any]], *, label: str = "ML"
                    ) -> list[dict[str, Any]]:
    """C-S8-32 record row: per F_s grade the number of actual head steps > 100 bar and the
    maximum D1'' ratio ``|dr| / J``; grades with a ratio >= 0.4 are flagged."""
    grades: dict[str, dict[str, Any]] = {g: {"steps": 0, "ratio_max": None, "case": None,
                                             "ratio_uncorrected_max": None, "flag": False,
                                             "runs": 0}
                                         for g in ("0", "<=2.5", "<=5", ">5", "unknown")}
    over: list[tuple[str, float, str, float]] = []
    lever_runs, plain_runs = 0, 0
    for c, v in sorted(per_run.items()):
        d1 = v.get("d1pp")
        if not d1:
            continue
        g = grades[_fs_grade(v.get("fs_mean_kN"))]
        g["runs"] += 1
        if d1.get("lever_correction_available"):
            lever_runs += 1
        else:
            plain_runs += 1
        for s in d1["steps"]:
            g["steps"] += 1
            if g["ratio_max"] is None or s["ratio"] > g["ratio_max"]:
                g["ratio_max"], g["case"] = s["ratio"], f"{c} {s['leg']} {s['t_s']:.2f} s"
            if g["ratio_uncorrected_max"] is None or \
                    s["ratio_uncorrected"] > g["ratio_uncorrected_max"]:
                g["ratio_uncorrected_max"] = s["ratio_uncorrected"]
            if s["ratio"] >= D1PP_RATIO_FLAG - 1e-12:
                g["flag"] = True
                over.append((c, round(s["ratio"], 3), s["leg"], round(s["t_s"], 2)))
    value = {k: {"steps": g["steps"], "ratio_max": None if g["ratio_max"] is None
                 else round(g["ratio_max"], 4)} for k, g in grades.items() if g["runs"]}
    flagged = [k for k, g in grades.items() if g["flag"]]
    note = ("; ".join(f"F_s {k}: {g['steps']} steps in {g['runs']} runs, max "
                      f"{None if g['ratio_max'] is None else round(g['ratio_max'], 3)} "
                      f"({g['case']}), uncorrected max "
                      f"{None if g['ratio_uncorrected_max'] is None else round(g['ratio_uncorrected_max'], 3)}"
                      for k, g in grades.items() if g["runs"])
            + f"; lever-corrected runs {lever_runs}, uncorrected (no gyro record) {plain_runs}"
            + (f"; FLAG ratio >= {D1PP_RATIO_FLAG:g}: {over[:40]}" if over else ""))
    return [_row(f"{label} C-S8-32 D1'' actual head steps > {D1PP_STEP_BAR:g} bar: count and "
                 f"max |dr| / J per F_s grade (record; flag >= {D1PP_RATIO_FLAG:g}, threshold "
                 "0.5)", "*", value, f"flag >= {D1PP_RATIO_FLAG:g}", None, note, kind="record",
                 flagged_grades=flagged, over_flag=over, grades=grades, rule=D1PP_RULE)]


def ml_case_metrics(d: Path, params, machine) -> dict[str, Any]:
    """ML-0 ... ML-3 values of one ML base / episode folder (``run_S8C.job_ml_base`` /
    ``job_ml_episode``): episode meta (``contact_episode.build_episode``), forced window and the
    ML mask ``[start, end + 3 s]`` (engine times too), rod-pressure fallback events with their
    context, F2 outside / inside the forced window (record), R45-4."""
    from outrigger_sim.contact_episode import build_episode

    case = _load_ml_case(d)
    res = case["result"]
    s = res.get("settings") or {}
    ep = s.get("episode") or {}
    t0 = float(s.get("start_t_s") or 0.0)
    out: dict[str, Any] = {"case": Path(d).name, "kind": ep.get("kind") or "base",
                           "base": res.get("base") if isinstance(res.get("base"), str)
                           else (s.get("ml_base") or {}).get("base_id"),
                           "ready_t_s": res.get("ready_t_s"), "branched": res.get("branched"),
                           "lock_valve": (s.get("s8") or {}).get("lock_valve")}
    try:
        meta = build_episode(Path(d), machine).meta
        out["meta"] = {k: meta.get(k) for k in ("crawler_contact", "crawler_check_passed",
                                                 "sensor_grade", "zero_calibration",
                                                 "sensor_condition", "engine", "event")}
    except Exception as exc:  # noqa: BLE001 - recorded in the ML-0 row
        out["meta_error"] = repr(exc)
    # C-S8-25 ③: settings refresh after the branch restore and the 1-period compare
    out["settings_refreshed"] = s.get("settings_refreshed") is not None
    out["first_period_compare"] = res.get("first_period_compare")
    # C-S8-26 ② ③ ④: FAULT entry, head faults, explained pressure steps
    names = _event_names(case)
    out["fault_injected"] = sensor_fault_injected(s)
    out["head_faults"] = named_events(names, HEAD_FAULT_EVENT)
    out["head_fault_reasons"] = named_events(names, HEAD_FAULT_REASON_INFO)
    out["rod_fault_reasons"] = named_events(names, ROD_FAULT_REASON_INFO)
    out["pressure_steps"] = named_events(names, PRESSURE_STEP_INFO)
    out["step_rule"] = _step_rule_of(res)
    series = load_series(Path(d))
    pads = case["pads"]
    if series is not None:
        ph = np.asarray(series["phase"]).astype(str)
        k = np.flatnonzero(np.isin(ph, FAULT_ENTRY_PHASES))  # C-S8-68 ①
        out["fault_entry_s"] = None if k.size == 0 else float(np.asarray(series["t"], float)[k[0]]
                                                            - t0)
    # C-S8-34 ① FAULT cause (P-S8-17 event, else the record) and U-S8-44 values
    rec = _load_record(Path(d), ("meas.stroke", "u_applied"))
    cm = res.get("controller_meta") or {}
    soft = _find_key(cm.get("geometry") or {}, "stroke_soft_max_m")
    soft = float(soft) if isinstance(soft, int | float) else STROKE_SOFT_MAX_DEFAULT_M
    margin = _find_key(cm, "stroke_end_fault_margin_m")
    if not isinstance(margin, int | float):
        margin = _config_float(str(cm.get("config") or ""), "stroke_end_fault_margin_m",
                               STROKE_END_FAULT_MARGIN_DEFAULT_M)
    margin = float(margin or STROKE_END_FAULT_MARGIN_DEFAULT_M)
    fc = classify_fault(out.get("fault_entry_s"), names,
                        None if rec is None or "meas.stroke" not in rec
                        else np.asarray(rec["t"], float) - t0,
                        None if rec is None else rec.get("meas.stroke"),
                        soft_max_m=soft, margin_m=margin)
    floor = (s.get("ml_base") or {}).get("floor_deg")
    if fc is not None:
        fc["floor_deg"] = floor
        fc["operating_index"] = operating_index(floor)
        if fc["cause"] == "stroke_end" and pads is not None:
            fc["protective"] = stroke_end_protective(
                pads, t0, float(out["fault_entry_s"]), floor,
                float(params.control.F_min_cylinder_N),
                (cm.get("target") or {}).get("target_rad"))
    out["fault_cause"] = fc
    # U-S8-30 (record kept) and U-S8-32 / C-S8-27 ①: lift after a settlement (1 ms pad record)
    ev_t = res.get("event_t_s")
    if ep.get("kind") == "settle" and pads is not None and ev_t is not None \
            and "airborne" in pads:
        tp_rel = np.asarray(pads["t"], float) - t0
        li = lift_intervals(tp_rel, pads["airborne"], float(ev_t) - t0)
        longest = {leg: max((b - a for a, b in v), default=0.0) for leg, v in li.items()}
        lifted = sorted(leg for leg, v in longest.items() if v > 0.0)
        out["lift"] = {"intervals_s": li, "longest_s": longest, "lifted_legs": lifted,
                       "max_s": max(longest.values()),
                       "diagonal": {"FL", "RR"} <= set(lifted) or {"FR", "RL"} <= set(lifted),
                       "deep_fast": float(ep.get("depth_m") or 0.0) >= ML_DEEP_SETTLE_M - 1e-12
                       and float(ep.get("ramp_s") or 1e9) <= ML_FAST_SETTLE_S + 1e-12,
                       "depth_m": ep.get("depth_m"), "ramp_s": ep.get("ramp_s"),
                       "leg": ep.get("leg")}
        if "ball_centre_world" in pads and ep.get("leg") in LEGS:
            t3, t3_top = _t3_of_level(s.get("level"))
            sp = settle_lift_split(tp_rel, pads["airborne"],
                                   np.asarray(pads["ball_centre_world"], float)[:, :, 2],
                                   float(ev_t) - t0, ep["leg"], float(ep["depth_m"]),
                                   float(ep["ramp_s"]), t3_s=t3,
                                   fault_t_s=out.get("fault_entry_s"),
                                   # C-S8-34 ②: an un-injected FAULT is judged in ML-0 by cause
                                   fault_gate=not (fc is not None and not out["fault_injected"]),
                                   fault_cause=None if fc is None else fc["cause"])
            sp["T3_from_top_level"] = t3_top
            out["u_s8_32"] = sp
    # C-S8-32: D1'' actual head-step ratios (record)
    out["fs_mean_kN"] = run_fs_mean_kN(pads, s)
    out["d1pp"] = d1pp_step_ratios(Path(d), params, settings=s, pads=pads)
    if series is None or pads is None:
        out["missing"] = [n for n, v in (("s8_series.npz", series), ("pads.npz", pads))
                          if v is None]
        return out
    t_abs = np.asarray(series["t"], float)
    tc = t_abs - t0
    fw = forced_window(res, float(tc[-1]), series)
    out["forced_window"] = fw
    out["run_end_s"] = float(tc[-1])
    if fw is not None:
        f_inst = _record_truth_at(Path(d), t_abs, "F_cyl")
        out["forced_event"] = forced_event_record(res, fw, pads, t0, float(tc[-1]),
                                                  float(params.control.F_min_cylinder_N),
                                                  t_sample_rel_s=tc,
                                                  rod_weight_N=_rod_weight_N(params),
                                                  f_sample_N=f_inst)
    out["ml_mask"] = ml_episode_mask(fw, out.get("fault_entry_s"), float(tc[-1]), t0)
    mk = out["ml_mask"]
    out["fault_tail"] = None if mk is None or "fault" not in mk["reasons"] else {
        "start_s": float(out["fault_entry_s"]), "end_s": mk["end_s"],
        "start_engine_s": float(out["fault_entry_s"]) + t0, "end_engine_s": mk["end_engine_s"],
        "cause": None if out.get("fault_cause") is None else out["fault_cause"]["cause"],
        "rule": ML_TAG_RULES["fault_tail"]}  # C-S8-34 ④
    phases =np.asarray(series["phase"]).astype(str)
    fb = rod_fallback_events(_event_names(case), fw)
    for e in fb:
        k = int(np.clip(np.searchsorted(tc, e["t_s"] - 1e-9), 0, tc.size - 1))
        j = LEGS.index(e["leg"]) if e["leg"] in LEGS else None
        e["phase"] = str(phases[k])
        if j is not None:
            e["issued_u_mm_s"] = float(np.asarray(series["issued_u"], float)[k, j]) * 1e3
            ta = np.array([e["t_s"] + t0])
            e["head_bar"] = float(_pad_at(pads, ta, "head_pressure")[0, j]) / 1e5
            e["rod_bar"] = float(_pad_at(pads, ta, "rod_pressure")[0, j]) / 1e5
            e["F_cyl_kN"] = float(_pad_at(pads, ta, "F_cyl")[0, j]) / 1e3
            rod_fallback_command_context(e, tc, np.asarray(series["issued_u"], float), rec,
                                         pads, t0)  # C-S8-34 ③
    out["rod_fallback"] = {"events": fb, "injected": rod_fault_injected(s)}
    # C-S8-34 ④ (U-S8-47): the three ML tags of spec rev. 51 223.2
    ev_rel = None
    t_ev_abs = res.get("event_t_s") or res.get("branch_t_s")
    if out["kind"] != "base" and t_ev_abs is not None:
        ev_rel = float(t_ev_abs) - t0
    out["reapproach"] = reapproach_pingpong(names, ev_rel, float(tc[-1]), t0)
    out["reapproach_pingpong"] = None if out["reapproach"] is None \
        else out["reapproach"]["window"]
    # C-S8-37 (spec rev. 52 230): RT runs / deferred starts / twist work bins
    # C-S8-40 (spec rev. 54 248.3): the forced window is masked in the twist work
    out["rt"] = reapproach_rt_record(names, ev_rel, t0, cm, pads, rec, forced=fw,
                                     f_min_N=float(params.control.F_min_cylinder_N))
    out["reapproach_variant"] = s.get("reapproach_variant")
    out["plant_rod_collapse"] = plant_rod_collapse(pads, rec, t0)
    # H-S8-4 F1 (hydraulics 12.6): release reading steps, collapse windows to re-contact
    r8p = Path(d) / "r8_series.npz"
    out["plant_release_rod_step"] = []
    if r8p.exists() and "airborne" in pads:
        with np.load(r8p, allow_pickle=False) as z:
            r8 = {k: np.asarray(z[k]) for k in ("t", "valve_u", "issued_u") if k in z.files}
        meta_p = Path(d) / "record" / "meta.json"
        rmeta = json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else {}
        tau = _find_key(s, "tau_v_s")
        tau = float(tau) if isinstance(tau, int | float) else float(_find_key(rmeta, "tau_v_s")
                                                                    or 0.1)
        eps = _find_key(rmeta, "lock_eps_m_s")
        eps = float(eps) if isinstance(eps, int | float) else LOCKED_U_M_S
        vmax = _find_key(cm.get("geometry") or {}, "max_speed_m_s")
        vmax = float(vmax) if isinstance(vmax, int | float) else 0.020924
        rel = plant_release_steps(pads, r8, tau, eps, t0)
        out["plant_release_rod_step"] = link_collapse_releases(out["plant_rod_collapse"], rel,
                                                               pads, t0, vmax)
        out["release_rule"] = {"tau_v_s": tau, "lock_eps_m_s": eps, "v_max_m_s": vmax}
    lower, f_cal, src = lower_estimate_series(series)
    f_true = _pad_at(pads, t_abs, "F_cyl")
    lifted = ~np.isin(phases, PRE_LIFT_PHASES)
    in_forced = forced_mask(tc, fw)
    share = SENSOR_SHARE_N["wika"]  # ML runs: sensor model on (spec 205.3)
    exc = lower - f_true
    f2 = {}
    for name, sel in (("outside", lifted & ~in_forced), ("forced", lifted & in_forced)):
        x = exc[sel]
        ok = np.isfinite(x)
        f2[name] = {"samples": int(ok.sum()),
                    "violations": int((x[ok] > share + NUMERIC_TOL_N).sum()),
                    "max_kN": None if not ok.any() else float(x[ok].max()) / 1e3}
    out["F2"] = {**f2, "lower_source": src["lower"], "share_kN": share / 1e3}
    f_min = float(params.control.F_min_cylinder_N)
    if case["probes"] and (s.get("contact") or "combined") != "pressure":
        cfg = str((res.get("controller_meta") or {}).get("config") or "")
        out["R45_4"] = low_load_probe_records(
            case["probes"], ml_probe_truth_rows(case["probes"], pads, t0), tc, lower, f_cal,
            np.asarray(pads["t"], float) - t0, judged_force_min(pads), f_min, t0,
            guard_margin_N=_config_float(cfg, "guard_margin_N", GUARD_MARGIN_DEFAULT_N)
            or GUARD_MARGIN_DEFAULT_N,
            max_rounds=int(_config_float(cfg, "max_rounds", MAX_ROUNDS_DEFAULT)
                           or MAX_ROUNDS_DEFAULT))
    return out


# --- C-S8-34 (spec rev. 51 225, U-S8-44 / 46 / 47) -------------------------------------------

STROKE_END_FAULT_EVENT = "FAULT_STROKE_END"
"""P-S8-17 (spec rev. 51 225): ``FAULT_STROKE_END:<leg>`` of the controller's stroke-end FAULT
(``c2._update_stroke_end_fault``); absent in the runs before P-S8-17."""
STROKE_SOFT_MAX_DEFAULT_M = 0.6948
"""Soft stroke end (CLAUDE.md: sensor range 0.6948 m) when ``controller_meta.geometry`` lacks
``stroke_soft_max_m``."""
STROKE_END_FAULT_MARGIN_DEFAULT_M = 1e-3
STROKE_END_LOOKBACK_S = 2.0
"""C-S8-34 ① record rule (runs without the P-S8-17 event): stroke-end FAULT when, over the
2 s before the first ``fault`` phase sample, every 10 Hz ``meas.stroke`` sample of a leg is at or
above ``stroke_soft_max_m - stroke_end_fault_margin_m`` (the controller's 2 s rule)."""
OPERATING_DIAMOND_DEG = (4.4, 3.2)
"""CLAUDE.md '경사 운용 한계': operating diamond ``|phi_g| / 4.4 + |theta_g| / 3.2 <= 1``
(floor angles)."""
STROKE_END_ATT_TOL_DEG = 0.2
"""U-S8-44: after a stroke-end FAULT the true attitude error stays <= 0.2 deg (CLAUDE.md +-0.2)."""
STROKE_END_RULE = (
    "U-S8-44 (spec rev. 51 222.2 / 224): a stroke-end FAULT is a protective stop; it passes when "
    "the floor is outside the operating diamond |phi_g|/4.4 + |theta_g|/3.2 > 1 and, from the "
    "FAULT entry to the run end, every leg's 1 ms judged force >= F_min + 5 kN, no pad lift and "
    "the true attitude error (pads body_quat_wxyz vs controller target) <= 0.2 deg; inside the "
    "operating diamond it fails. Cause: P-S8-17 event FAULT_STROKE_END:<leg>, else the record "
    "(every meas.stroke sample of a leg over the 2 s before the FAULT >= soft end - margin)")
PINGPONG_AFTER_S = 1.5
PINGPONG_MIN_STARTS = 3
PINGPONG_TAIL_S = 1.0
"""U-S8-47 / spec rev. 51 223.2 / 226 (ASSUMPTION): ``reapproach_pingpong`` = at least 3
``leg_reapproach_start`` later than event + 1.5 s; tag window event + 1.5 s .. last re-approach
end (``leg_reapproach_contact``, else its start) + 1 s, capped at the run end."""
ROD_COLLAPSE_DROP_PA = 50e5
ROD_COLLAPSE_BEFORE_SAMPLES = 5
ROD_COLLAPSE_AFTER_SAMPLES = 10
ROD_COLLAPSE_HALF_WINDOW_S = 0.3
LOCKED_U_M_S = 1e-6
"""U-S8-47 / spec rev. 51 222.4 / 223.2 / 226 (ASSUMPTION): ``plant_rod_collapse`` = pad
lift-off (1 ms ``airborne`` onset) with the plant valve locked (record ``u_applied`` of the
period, ``|u| <= 1e-6 m/s``) whose rod pressure falls by more than 50 bar from 5 samples before
to 10 samples after the onset (1 ms pads); tag window lift-off +- 0.3 s."""
ML_TAG_RULES = {
    "fault_tail": "ml_mask with reason 'fault' (FAULT entry .. run end); excluded from training "
                  "and E1..E4 (already masked)",
    "plant_rod_collapse": "locked lift-off with a rod-pressure fall > 50 bar within 10 ms "
                          "(rev. 51 222.4), window lift-off +- 0.3 s; training weight 0, kept in "
                          "the test metrics and shown apart",
    "reapproach_pingpong": ">= 3 re-approach starts later than event + 1.5 s (rev. 51 222.3), "
                           "window event + 1.5 s .. last re-approach end + 1 s; training as is, "
                           "E1 / E3 reported apart",
    "plant_release_rod_step": "H-S8-4 F1 reading step: plant release (valve |u| > lock_eps) "
                              "with a 1 ms rod-pressure change > 20 bar, not a "
                              "plant_rod_collapse; window [t_b, t_b + 0.3 s]; weight 0 on that "
                              "leg's head / rod pressure features only (net force, stroke, IMU "
                              "and labels kept); none after the F1 fix"}
"""C-S8-34 ④: the three ML tags of spec rev. 51 223.2 (times relative to ``start_t_s``; each
window also carries the engine times)."""


def operating_index(floor_deg: Sequence[float] | None) -> float | None:
    """``|phi_g| / 4.4 + |theta_g| / 3.2`` of the floor (deg); None without a floor."""
    if floor_deg is None or len(floor_deg) < 2:
        return None
    return (abs(float(floor_deg[0])) / OPERATING_DIAMOND_DEG[0]
            + abs(float(floor_deg[1])) / OPERATING_DIAMOND_DEG[1])


def _load_record(case_dir: Path, keys: Sequence[str]) -> dict[str, np.ndarray] | None:
    p = Path(case_dir) / "record" / "record.npz"
    if not p.exists():
        return None
    with np.load(p, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in ("t", *keys) if k in z.files}


def classify_fault(fault_entry_s: float | None, names: Sequence[tuple[float, str]],
                   t_rec_rel_s: np.ndarray | None, meas_stroke_m: np.ndarray | None, *,
                   soft_max_m: float, margin_m: float,
                   lookback_s: float = STROKE_END_LOOKBACK_S) -> dict[str, Any] | None:
    """C-S8-34 ①: cause of the first FAULT entry (relative times). ``stroke_end`` from the
    P-S8-17 event ``FAULT_STROKE_END:<leg>`` at or before the entry, else
    ``head_sensor_reground`` (C-S8-68 ①) when such a sensor event and a ``fault_reground_start``
    event with target legs are recorded, else ``sensor`` when a
    head-pressure fault event / reason or a rod fault reason is recorded, else ``stroke_end``
    from the record (every ``meas.stroke`` sample of a leg in ``[entry - lookback, entry)`` >=
    ``soft_max - margin``), else ``unknown``. None without a FAULT."""
    if fault_entry_s is None:
        return None
    tf = float(fault_entry_s)
    out: dict[str, Any] = {"fault_t_s": tf, "threshold_m": soft_max_m - margin_m,
                           "lookback_s": lookback_s}
    se = named_events(names, STROKE_END_FAULT_EVENT)
    se = [e for e in se if e["t_s"] <= tf + 1e-6]
    if se:
        out.update(cause="stroke_end", source="event",
                   legs=sorted({e["leg"] for e in se if e["leg"]}))
        return out
    sensor = [e for p in (HEAD_FAULT_EVENT, HEAD_FAULT_REASON_INFO, ROD_FAULT_REASON_INFO)
              for e in named_events(names, p) if e["t_s"] <= tf + 1e-6]
    # C-S8-68 ①: a head fault that started a re-ground (target legs named) is told apart
    rg = [e for e in named_events(names, REGROUND_START_EVENT) if e["t_s"] <= tf + 1e-6
          and legs_in(e["leg"])]
    if sensor and rg:
        out.update(cause="head_sensor_reground", source="event",
                   legs=sorted({e["leg"] for e in sensor if e["leg"]}),
                   reground_targets=legs_in(rg[0]["leg"]))
        return out
    if sensor:
        out.update(cause="sensor", source="event",
                   legs=sorted({e["leg"] for e in sensor if e["leg"]}))
        return out
    if t_rec_rel_s is not None and meas_stroke_m is not None:
        t = np.asarray(t_rec_rel_s, float)
        s = np.asarray(meas_stroke_m, float)
        sel = (t >= tf - lookback_s - 1e-9) & (t < tf - 1e-9)
        if sel.any():
            at = s[sel] >= soft_max_m - margin_m - 1e-12
            legs = [LEGS[j] for j in range(s.shape[1]) if at[:, j].all()]
            out["stroke_max_before_m"] = [float(x) for x in s[sel].max(axis=0)]
            if legs:
                out.update(cause="stroke_end", source="record", legs=legs)
                return out
    out.update(cause="unknown", source="none", legs=[])
    return out


def stroke_end_protective(pads: Mapping[str, Any], t0: float, fault_entry_s: float,
                          floor_deg: Sequence[float] | None, f_min_N: float,
                          target_rad: Sequence[float] | None) -> dict[str, Any]:
    """U-S8-44 values of a stroke-end FAULT (1 ms pads from the FAULT entry to the run end):
    operating-diamond index of the floor, minimum judged force per leg, lifted legs, maximum
    true attitude error against the target; ``passed`` per :data:`STROKE_END_RULE`."""
    from outrigger_sim.frames import roll_pitch_from_quat

    tp = np.asarray(pads["t"], float) - t0
    sel = tp >= float(fault_entry_s) - 1e-9
    fmin = judged_force_min(pads)[sel]
    air = (np.asarray(pads["airborne"], bool)[sel] if "airborne" in pads
           else np.zeros(fmin.shape, bool))
    tgt = np.zeros(2) if target_rad is None else np.asarray(target_rad, float)[:2]
    att = None
    if "body_quat_wxyz" in pads and sel.any():
        r, p = roll_pitch_from_quat(np.asarray(pads["body_quat_wxyz"], float)[sel])
        err = np.degrees(np.abs(np.column_stack([r, p]) - tgt))
        att = [float(x) for x in err.max(axis=0)]
    op = operating_index(floor_deg)
    min_leg = [float(x) / 1e3 for x in fmin.min(axis=0)] if fmin.size else None
    lifted = [LEGS[j] for j in range(air.shape[1]) if air[:, j].any()] if air.size else []
    limit_kN = (f_min_N + D8_MARGIN_N) / 1e3
    outside = op is not None and op > 1.0 + 1e-12
    ok_force = min_leg is not None and min(min_leg) >= limit_kN - 1e-9
    ok_att = att is not None and max(att) <= STROKE_END_ATT_TOL_DEG + 1e-12
    return {"floor_deg": None if floor_deg is None else [float(x) for x in floor_deg],
            "operating_index": op, "outside_operating": bool(outside),
            "min_force_kN": min_leg, "limit_kN": limit_kN, "lifted_legs": lifted,
            "att_err_max_deg": att, "att_tol_deg": STROKE_END_ATT_TOL_DEG,
            "post_fault_s": None if not sel.any() else float(tp[sel][-1] - tp[sel][0]),
            "passed": bool(outside and ok_force and not lifted and ok_att),
            "rule": STROKE_END_RULE}


def reapproach_pingpong(names: Sequence[tuple[float, str]], t_ev_s: float | None,
                        t_end_s: float, t0: float) -> dict[str, Any] | None:
    """C-S8-34 ④ (spec rev. 51 222.3 / 223.2): re-approach starts after the event (relative
    times) and the ``reapproach_pingpong`` tag window (None in ``window`` when fewer than
    :data:`PINGPONG_MIN_STARTS` start later than event + 1.5 s). None without an event time."""
    if t_ev_s is None:
        return None
    te = float(t_ev_s)
    starts = [(e["t_s"], e["leg"]) for e in named_events(names, "leg_reapproach_start")
              if e["t_s"] >= te - 1e-6]
    ends = [e["t_s"] for e in named_events(names, "leg_reapproach_contact")
            if e["t_s"] >= te - 1e-6]
    late = [(t, leg) for t, leg in starts if t - te > PINGPONG_AFTER_S + 1e-9]
    out: dict[str, Any] = {"starts_rel_s": [[round(t - te, 3), leg] for t, leg in starts],
                           "late_starts": len(late),
                           "leg_changes": sum(1 for a, b in zip(starts, starts[1:],
                                                                strict=False)
                                              if a[1] != b[1]),
                           "window": None}
    if len(late) >= PINGPONG_MIN_STARTS:
        last = max([t for t, _ in starts] + ends)
        a = te + PINGPONG_AFTER_S
        b = min(max(last + PINGPONG_TAIL_S, a + 1e-6), float(t_end_s))
        out["window"] = {"start_s": a, "end_s": b, "start_engine_s": a + t0,
                         "end_engine_s": b + t0, "late_starts": len(late),
                         "rule": ML_TAG_RULES["reapproach_pingpong"]}
    return out


RT_WORK_AFTER_S = 1.5
RT_WORK_BIN_S = 0.5
RT_WORK_SPAN_S = 8.0
RT_WORK_LIMIT_J = 20.0
"""C-S8-36 / 37 (spec rev. 52 230 / 236, kept by rev. 54 248.3, ASSUMPTION): bin threshold of
the actuator twist-mode work (768 recurrence plateau 15-20 J, rev. 54 248.2)."""
RT_WORK_MAX_CLUSTERS = 1
"""C-S8-40 (spec rev. 54 248.3, ASSUMPTION 254): at most one cluster of consecutive judged bins
> :data:`RT_WORK_LIMIT_J` after event + 1.5 s (a single overshoot is allowed, a recurring energy
injection fails)."""
RT_WORK_FORCED_TAIL_S = 0.1
"""C-S8-40 (spec rev. 54 248.3): the forced window is masked up to ``done_s`` + 0.1 s (one valve
lag tau_v)."""
RT_TWIST_N = np.array([0.5, -0.5, -0.5, 0.5])
RT_WORK_RULE = ("C-S8-40 (spec rev. 54 248.3): W = sum over the 1 ms pad record of D/2 "
                "(n . u_applied) dt per 0.5 s bin from the event, 8 s, D = (F_FL + F_RR) - "
                "(F_FR + F_RL) - D0 (true rod forces pads F_cyl, D0 = median over event - 0.5 .. "
                "0 s), n = (+,-,-,+)/2, u_applied from record.npz held between samples; power 0 "
                "in the forced window [forced start, done_s + 0.1 s] (to the run end when "
                "done_s is None); judged bins = bins starting >= event + 1.5 s with an unmasked "
                "sample; cluster = consecutive judged bins > +20 J; judged: clusters <= 1 "
                "(recurrence ban; ASSUMPTION 254). Records: the rev. 52 unmasked bin max "
                "(raw_max_bin_after_J), the masked bin max and the largest cluster work")


def forced_rel_to_event(fw: Mapping[str, Any] | None, t_ev_rel: float
                        ) -> dict[str, Any] | None:
    """C-S8-40: a :func:`forced_window` (times relative to the run start) as event-relative
    ``{"start_s", "done_s"}`` for :func:`twist_work_bins` (``done_s`` None = never finished)."""
    if not fw:
        return None
    done = fw.get("done_s")
    return {"start_s": float(fw["start_s"]) - float(t_ev_rel),
            "done_s": None if done is None else float(done) - float(t_ev_rel),
            "others": fw.get("others")}


def work_clusters(edges: Sequence[float], bins: Sequence[float], judged: Sequence[bool],
                  limit_J: float = RT_WORK_LIMIT_J) -> list[list[float]]:
    """C-S8-40: ``[[start_s, work_J], ...]`` of the runs of consecutive judged bins whose work
    is > ``limit_J`` (an unjudged or non-exceeding bin ends a run)."""
    out: list[list[float]] = []
    cur: list[float] | None = None
    for a, w, ok in zip(edges, bins, judged, strict=True):
        if ok and w > limit_J:
            if cur is None:
                cur = [float(a), 0.0]
                out.append(cur)
            cur[1] += float(w)
        else:
            cur = None
    return [[round(a, 3), round(w, 2)] for a, w in out]


def twist_work_bins(pads: Mapping[str, Any], rec: Mapping[str, np.ndarray] | None,
                    t_ev_abs: float, span_s: float = RT_WORK_SPAN_S,
                    forced: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    """Actuator twist-mode work per :data:`RT_WORK_BIN_S` bin after the event (engine time
    ``t_ev_abs``; :data:`RT_WORK_RULE`). ``forced``: event-relative forced window
    (:func:`forced_rel_to_event`), masked to ``done_s`` + :data:`RT_WORK_FORCED_TAIL_S`. None
    without the pad force or the applied command."""
    if rec is None or "u_applied" not in rec or "F_cyl" not in pads:
        return None
    tp = np.asarray(pads["t"], float)
    m = (tp >= t_ev_abs - 0.5) & (tp <= t_ev_abs + span_s + 1e-9)
    if m.sum() < 10:
        return None
    t = tp[m] - t_ev_abs
    f = np.asarray(pads["F_cyl"], float)[m]
    d = (f[:, 0] + f[:, 3]) - (f[:, 1] + f[:, 2])
    pre = t < 0.0
    d0 = float(np.median(d[pre])) if pre.any() else 0.0
    tr = np.asarray(rec["t"], float) - t_ev_abs
    utw = np.asarray(rec["u_applied"], float) @ RT_TWIST_N
    j = np.clip(np.searchsorted(tr, t, side="right") - 1, 0, tr.size - 1)
    dt = np.diff(t, append=t[-1] + float(np.median(np.diff(t))))
    p_raw = 0.5 * (d - d0) * utw[j]
    t_last = float(t[-1])
    masked_s = None
    hide = np.zeros(t.size, bool)
    if forced:
        a = float(forced["start_s"])
        b = None if forced.get("done_s") is None \
            else float(forced["done_s"]) + RT_WORK_FORCED_TAIL_S
        hide = (t >= a - 1e-9) & ((t <= b + 1e-9) if b is not None else True)
        masked_s = [round(a, 4), None if b is None else round(b, 4)]
    p = np.where(hide, 0.0, p_raw)
    # bins that start after the record end (short run) are left out
    edges = np.arange(0.0, min(span_s, t_last) - 1e-9, RT_WORK_BIN_S)
    sel = [(t >= a) & (t < a + RT_WORK_BIN_S) for a in edges]
    bins = [float(np.sum((p * dt)[s])) for s in sel]
    raw_bins = [float(np.sum((p_raw * dt)[s])) for s in sel]
    late = [a >= RT_WORK_AFTER_S - 1e-9 for a in edges]
    judged = [lt and bool((s & ~hide).any()) for lt, s in zip(late, sel, strict=True)]
    jw = [w for w, ok in zip(bins, judged, strict=True) if ok]
    raw_late = [w for w, lt in zip(raw_bins, late, strict=True) if lt]
    clusters = work_clusters(edges, bins, judged)
    passed = None if not jw else bool(len(clusters) <= RT_WORK_MAX_CLUSTERS)
    return {"bins_J": [round(w, 2) for w in bins], "raw_bins_J": [round(w, 2) for w in raw_bins],
            "bin_s": RT_WORK_BIN_S, "covered_s": t_last, "D0_kN": d0 / 1e3,
            "masked_s": masked_s, "judged_bins": int(sum(judged)),
            "max_bin_after_J": max(jw) if jw else None,
            "raw_max_bin_after_J": max(raw_late) if raw_late else None,
            "pos_sum_after_J": float(sum(w for w in jw if w > 0.0)),
            "clusters": clusters, "n_clusters": len(clusters),
            "max_cluster_J": max((w for _a, w in clusters), default=0.0) if jw else None,
            "limit_J": RT_WORK_LIMIT_J, "max_clusters": RT_WORK_MAX_CLUSTERS,
            "passed_rev52": None if not raw_late else bool(max(raw_late) <= RT_WORK_LIMIT_J),
            "passed": passed,
            "status": "judged" if jw else (
                "not judgeable: the forced window covers every bin after event + 1.5 s"
                if any(late) else "no bin after event + 1.5 s")}


DEFERRED_TAIL_S = 0.3
"""C-S8-41 / C-S8-42 (spec rev. 55 267): tail added to the deferred-leg window end (valve lag
0.1 s and the load recovery of the first re-approach period)."""
DEFERRED_T_O_DEFAULT_S = 0.8
"""C-S8-42 (spec rev. 55 267): opposite-diagonal window ``T_o`` when the controller meta has no
``r8.lifted_reapproach.opposite_window_s`` (R8 value)."""
DEFERRED_WINDOW_RULE = "spec rev. 55 267"
"""C-S8-42 (spec rev. 55 269.3 #1): ``window_rule`` string of :func:`deferred_leg_minimum`."""
DEFERRED_MIN_RULE = (
    "C-S8-41 / C-S8-42 (spec rev. 54 261, rev. 55 267, U-S8-57 (a)): per "
    "leg_reapproach_deferred:<leg> after the event, window = deferral t_def .. min(t_next, t_def + "
    "T_o) + 0.3 s, cut at the run end (t_next = the same leg's next leg_reapproach_start, T_o = "
    "controller meta r8.lifted_reapproach.opposite_window_s, 0.8 s when missing); overlapping "
    "windows of the same leg are merged (first deferral .. last end); value = minimum of the "
    "S8-A2 judged true rod force (pads F_cyl_min_interval, 20 ms mean F_cyl_mean_20ms on airborne "
    "samples) of that leg over the window; the raw 1 ms minimum and the lift are records too; "
    "FLAG (record, not a gate) when the judged minimum < F_min")
DEFERRED_REF_WINDOW_S = (0.0, 4.0)
"""C-S8-42 (spec rev. 55 269.3 #2, 273): per-leg comparison window, event + 0 .. 4 s."""
DEFERRED_REF_FLAG_KN = 0.5
"""C-S8-42 (spec rev. 55 269.2 #4, ASSUMPTION): FLAG text when the leg minimum is deeper than
the reference by more than this [kN]."""
DEFERRED_REF_FLAG_S = 0.1
"""C-S8-42 (spec rev. 55 269.2 #4, ASSUMPTION): FLAG text when the time below F_min or the
airborne time exceeds the reference by more than this [s] (one control period)."""
DEFERRED_REF_RULE = (
    "C-S8-42 (spec rev. 55 269.3 #2): per deferred leg, over event + 0 .. 4 s (both ends "
    "included): minimum of the S8-A2 judged force, time with the judged force < F_min and "
    "airborne time (1 ms samples x the median pad period), in this run and in the same episode "
    "of the reference batch (768 / original MLJ); FLAG text (record, not a judgement) when the "
    "run is deeper by > 0.5 kN or longer by > 0.1 s (ASSUMPTION thresholds)")


def deferred_t_o_s(controller_meta: Mapping[str, Any] | None) -> float:
    """C-S8-42: ``T_o`` of the run (controller meta ``r8.lifted_reapproach.opposite_window_s``),
    :data:`DEFERRED_T_O_DEFAULT_S` when missing or not a number."""
    lr = ((controller_meta or {}).get("r8") or {}).get("lifted_reapproach")
    v = lr.get("opposite_window_s") if isinstance(lr, Mapping) else None
    return float(v) if isinstance(v, int | float) and not isinstance(v, bool) \
        else DEFERRED_T_O_DEFAULT_S


def leg_window_stats(tp: np.ndarray, judged: np.ndarray, air: np.ndarray | None, j: int,
                     a: float, b: float, f_min_N: float | None) -> dict[str, Any] | None:
    """C-S8-42: leg ``j`` over ``[a, b]`` (times of ``tp``, both ends included): judged-force
    minimum [kN] and its time, time below F_min and airborne time [s] (sample count x the median
    sample period). None when no sample lies in the window."""
    sel = (tp >= a - 1e-9) & (tp <= b + 1e-9)
    if not sel.any():
        return None
    dt = float(np.median(np.diff(tp))) if tp.size > 1 else 0.0
    k = np.flatnonzero(sel)
    kj = k[int(np.argmin(judged[k, j]))]
    return {"min_kN": round(float(judged[kj, j]) / 1e3, 3), "min_t_s": round(float(tp[kj]), 3),
            "below_F_min_s": None if f_min_N is None
            else round(float(np.sum(judged[k, j] < float(f_min_N))) * dt, 3),
            "air_s": None if air is None else round(float(np.sum(air[k, j])) * dt, 3)}


def deferred_leg_minimum(names: Sequence[tuple[float, str]], t_ev_rel: float, t0: float,
                         pads: Mapping[str, Any] | None, f_min_N: float | None, *,
                         t_o_s: float | None = None) -> dict[str, Any] | None:
    """C-S8-41 / C-S8-42 (spec rev. 54 261, rev. 55 267): true minimum of each deferred leg
    (:data:`DEFERRED_MIN_RULE`). ``names``: relative event names (:func:`_event_names`),
    ``t_ev_rel``: event time relative to the run start ``t0``; pad times are engine times;
    ``t_o_s``: ``T_o`` (None = :data:`DEFERRED_T_O_DEFAULT_S`). Window times in the output are
    relative to the event. Each window also carries ``leg_0_4s`` (:func:`leg_window_stats` of the
    leg over event + 0 .. 4 s, C-S8-42 #2; the reference side is added by
    :func:`attach_deferred_reference`). None without the pad force record."""
    if pads is None or "t" not in pads or not ("F_cyl_min_interval" in pads or "F_cyl" in pads):
        return None
    t_o = DEFERRED_T_O_DEFAULT_S if t_o_s is None else float(t_o_s)
    te = float(t_ev_rel)
    tp = np.asarray(pads["t"], float) - float(t0)
    raw = np.asarray(pads["F_cyl_min_interval"] if "F_cyl_min_interval" in pads
                     else pads["F_cyl"], float)
    judged = judged_force_min(pads) if "F_cyl_min_interval" in pads else raw
    air = np.asarray(pads["airborne"], bool) if "airborne" in pads else None
    starts = [e for e in named_events(names, "leg_reapproach_start") if e["leg"] in LEGS]
    deferred = [e for e in named_events(names, "leg_reapproach_deferred")
                if e["leg"] in LEGS and e["t_s"] >= te - 1e-6]
    t_last = float(tp[-1])
    raw_w = []
    for e in deferred:
        nxt = min((s["t_s"] for s in starts if s["leg"] == e["leg"]
                   and s["t_s"] > e["t_s"] + 1e-6), default=None)
        stop = e["t_s"] + t_o if nxt is None else min(nxt, e["t_s"] + t_o)
        raw_w.append({"leg": e["leg"], "a": e["t_s"], "b": min(stop + DEFERRED_TAIL_S, t_last),
                      "next": nxt})
    # merge overlapping windows of the same leg (first deferral .. last end)
    wins: list[dict[str, Any]] = []
    for w in sorted(raw_w, key=lambda x: (LEGS.index(x["leg"]), x["a"])):
        cur = wins[-1] if wins and wins[-1]["leg"] == w["leg"] else None
        if cur is not None and w["a"] <= cur["b"] + 1e-9:
            cur["deferred_s"].append(round(w["a"] - te, 3))
            if w["b"] >= cur["b"]:
                cur["b"], cur["next"] = w["b"], w["next"]
            continue
        wins.append({"leg": w["leg"], "deferred_s": [round(w["a"] - te, 3)], "a": w["a"],
                     "b": w["b"], "next": w["next"]})
    ra, rb = DEFERRED_REF_WINDOW_S
    out_w = []
    for w in sorted(wins, key=lambda x: x["a"]):  # first-deferral order (as rev. 55)
        j = LEGS.index(w["leg"])
        sel = (tp >= w["a"] - 1e-9) & (tp <= w["b"] + 1e-9)
        if not sel.any():
            continue
        k = np.flatnonzero(sel)
        kj = k[int(np.argmin(judged[k, j]))]
        kr = k[int(np.argmin(raw[k, j]))]
        mn = float(judged[kj, j])
        ctx = leg_window_stats(tp - te, judged, air, j, ra, rb, f_min_N)
        out_w.append({"leg": w["leg"], "deferred_s": w["deferred_s"],
                      "next_start_s": None if w["next"] is None else round(w["next"] - te, 3),
                      "window_s": [round(w["a"] - te, 3), round(w["b"] - te, 3)],
                      "min_kN": round(mn / 1e3, 3), "min_t_s": round(float(tp[kj]) - te, 3),
                      "raw_min_kN": round(float(raw[kr, j]) / 1e3, 3),
                      "lift": None if air is None else bool(air[k, j].any()),
                      "below_F_min": None if f_min_N is None else bool(mn < float(f_min_N)),
                      "leg_0_4s": ctx})
    worst = min(out_w, key=lambda x: x["min_kN"], default=None)
    return {"windows": out_w, "n_windows": len(out_w),
            "min_kN": None if worst is None else worst["min_kN"],
            "worst": worst, "f_min_kN": None if f_min_N is None else float(f_min_N) / 1e3,
            "flag": any(x["below_F_min"] for x in out_w),
            "t_o_s": t_o, "window_rule": DEFERRED_WINDOW_RULE,
            "rule": DEFERRED_MIN_RULE}


def _pads_force_of_dir(d: Path) -> dict[str, np.ndarray] | None:
    p = Path(d) / "pads.npz"
    if not p.exists():
        return None
    with np.load(p, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in ("t", "F_cyl", "F_cyl_min_interval",
                                              "F_cyl_mean_20ms", "airborne") if k in z.files}


def deferred_reference_stats(ref_dir: Path, legs: Sequence[str], *,
                             event_engine_time: bool | None = None,
                             f_min_N: float | None) -> dict[str, Any] | None:
    """C-S8-42 (spec rev. 55 269.3 #2): :func:`leg_window_stats` over event + 0 .. 4 s of
    ``legs`` in a reference run folder (``result.json`` + ``pads.npz``). ``event_engine_time``:
    ``result.event_t_s`` is an engine time (ML episodes, ``job_ml_episode``) rather than relative
    to ``settings.start_t_s`` (``run_S8C.py run`` cases, e.g. the original MLJ); None = from the
    file (ML episode = ``episode`` and ``branch_t_s`` keys). Event-relative times. None without
    the records or an event time."""
    d = Path(ref_dir)
    if not (d / "result.json").exists():
        return None
    pads = _pads_force_of_dir(d)
    if pads is None or "t" not in pads or "F_cyl_min_interval" not in pads:
        return None
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    if event_engine_time is None:
        event_engine_time = "episode" in res and "branch_t_s" in res
    t0 = float((res.get("settings") or {}).get("start_t_s") or 0.0)
    ev = res.get("event_t_s")
    if ev is None and event_engine_time:
        ev = res.get("branch_t_s")
    if ev is None:
        return None
    te = float(ev) - t0 if event_engine_time else float(ev)
    tp = np.asarray(pads["t"], float) - t0 - te
    judged = judged_force_min(pads)
    air = np.asarray(pads["airborne"], bool) if "airborne" in pads else None
    ra, rb = DEFERRED_REF_WINDOW_S
    return {leg: leg_window_stats(tp, judged, air, LEGS.index(leg), ra, rb, f_min_N)
            for leg in legs if leg in LEGS}


def deferred_ref_flags(run: Mapping[str, Any] | None, ref: Mapping[str, Any] | None
                       ) -> list[str]:
    """C-S8-42: FLAG reasons of one leg (run vs reference, :data:`DEFERRED_REF_FLAG_KN` /
    :data:`DEFERRED_REF_FLAG_S`); empty when either side is missing or within the thresholds."""
    if not run or not ref:
        return []
    out = []
    if run["min_kN"] < ref["min_kN"] - DEFERRED_REF_FLAG_KN - 1e-9:
        out.append(f"min {run['min_kN']:.2f} vs {ref['min_kN']:.2f} kN")
    for k, lab in (("below_F_min_s", "below F_min"), ("air_s", "airborne")):
        if run.get(k) is not None and ref.get(k) is not None \
                and run[k] > ref[k] + DEFERRED_REF_FLAG_S + 1e-9:
            out.append(f"{lab} {run[k]:.3f} vs {ref[k]:.3f} s")
    return out


def attach_deferred_reference(dm: dict[str, Any] | None, ref_dir: Path | None, *,
                              event_engine_time: bool | None = None,
                              f_min_N: float | None = None,
                              ref_label: str | None = None) -> None:
    """C-S8-42 (spec rev. 55 269.3 #2): add to each window of :func:`deferred_leg_minimum` the
    reference columns ``ref_0_4s`` (:func:`deferred_reference_stats`, same episode in the
    reference batch) and ``ref_flag`` (:func:`deferred_ref_flags`); ``dm["reference"]`` records
    the folder (None = no reference: the columns stay None). In place."""
    if not dm or not dm.get("windows"):
        return
    if f_min_N is None and dm.get("f_min_kN") is not None:
        f_min_N = float(dm["f_min_kN"]) * 1e3
    ref = None
    if ref_dir is not None:
        ref = deferred_reference_stats(ref_dir, sorted({w["leg"] for w in dm["windows"]}),
                                       event_engine_time=event_engine_time, f_min_N=f_min_N)
    dm["reference"] = None if ref is None else {"dir": str(ref_dir), "label": ref_label}
    for w in dm["windows"]:
        r = None if ref is None else ref.get(w["leg"])
        w["ref_0_4s"] = r
        w["ref_flag"] = deferred_ref_flags(w.get("leg_0_4s"), r)
    dm["ref_flag"] = any(w["ref_flag"] for w in dm["windows"])
    dm["ref_rule"] = DEFERRED_REF_RULE


AVAIL_TOL_S = 0.1
"""C-S8-42 (spec rev. 55 269.2 #3, 273): re-READY non-worsening tolerance, median of
(new - reference) over the runs reaching it in both (one control period)."""
AVAIL_RULE = (
    "C-S8-42 (spec rev. 55 269.2 #2 / #3, 269.3 #3; = control c55_avail.py): after the event "
    "(result.event_t_s, engine time): probe return = a 10 Hz r8_series phase change 'probe' -> "
    "'level' (count per run, times rounded to 0.1 s), causes = controller events "
    "probe_aborted_*; re-READY = the first 'ready' sample after a 'done' sample (None = not "
    "reached in the record); rod fallback = WARN_ROD_PRESSURE_FALLBACK events after the event. "
    "Criteria (record rows, control judges): probe-return runs <= the reference on the same ids; "
    "median (re-READY - reference) <= +0.1 s over runs reaching it in both; a run reaching "
    "re-READY only in the reference fails with a probe return or a rod fallback, else it is a "
    "DONE-tail record (spec 257.2)")
_AVAIL_EVENT = re.compile(r"t_s=([-0-9.e]+), name='([^']+)'")


def availability_record(d: Path) -> dict[str, Any] | None:
    """C-S8-42 (:data:`AVAIL_RULE`) of one ML episode folder (``result.json`` event engine time,
    ``r8_series.npz`` phase, ``controller_events.json``); None without the records or an
    event time."""
    d = Path(d)
    if not (d / "result.json").exists() or not (d / "r8_series.npz").exists():
        return None
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    if res.get("event_t_s") is None:
        return None
    te = float(res["event_t_s"])
    with np.load(d / "r8_series.npz", allow_pickle=True) as z:
        if "phase" not in z.files:
            return None
        t = np.asarray(z["t"], float) - te
        ph = [str(x) for x in z["phase"]]
    ret, rr, seen_done = [], None, False
    for i in range(1, len(t)):
        if t[i] < 0:
            continue
        if ph[i - 1] == "probe" and ph[i] == "level":
            ret.append(round(float(t[i]), 1))
        if ph[i] == "done":
            seen_done = True
        if rr is None and seen_done and ph[i] == "ready":
            rr = round(float(t[i]), 1)
    aborts, fb = [], []
    ev_p = d / "controller_events.json"
    for e in (json.loads(ev_p.read_text(encoding="utf-8")) if ev_p.exists() else []):
        m = _AVAIL_EVENT.search(str(e))
        if not m or float(m.group(1)) < te - 1e-6:
            continue
        if m.group(2).startswith("probe_aborted"):
            aborts.append([round(float(m.group(1)) - te, 1), m.group(2)])
        if m.group(2).startswith("WARN_ROD_PRESSURE_FALLBACK"):
            fb.append([round(float(m.group(1)) - te, 1), m.group(2)])
    return {"probe_returns_s": ret, "probe_aborts": aborts, "rod_fallback": fb,
            "re_ready_s": rr, "t_end_s": round(float(t[-1]), 1)}


def availability_compare(new: Mapping[str, Mapping[str, Any] | None],
                         ref: Mapping[str, Mapping[str, Any] | None]) -> dict[str, Any]:
    """C-S8-42: :data:`AVAIL_RULE` summary over the run ids present in both (= control
    ``c55_avail.py`` ``summary``); ``missing_in_reference``: ids without a reference record."""
    ids = [c for c in new if new[c] is not None and ref.get(c) is not None]
    missing = sorted(c for c in new if new[c] is not None and ref.get(c) is None)
    deltas, only_ref, only_new = [], [], []
    for c in ids:
        a, b = new[c]["re_ready_s"], ref[c]["re_ready_s"]
        if a is not None and b is not None:
            deltas.append((c, round(a - b, 1)))
        elif b is not None:
            only_ref.append(c)
        elif a is not None:
            only_new.append(c)
    med = float(np.median([x for _, x in deltas])) if deltas else None
    pr_new = sorted(c for c in ids if new[c]["probe_returns_s"])
    pr_ref = sorted(c for c in ids if ref[c]["probe_returns_s"])
    bad = [c for c in only_ref if new[c]["probe_returns_s"] or new[c]["rod_fallback"]]
    return {"ids": len(ids), "missing_in_reference": missing,
            "probe_return_runs_new": pr_new, "probe_return_runs_ref": pr_ref,
            "probe_return_ok": len(pr_new) <= len(pr_ref),
            "re_ready_both": len(deltas), "median_delta_s": med,
            "later_runs": [c for c, x in deltas if x > AVAIL_TOL_S],
            "worst": max(deltas, key=lambda z: z[1]) if deltas else None,
            "reached_only_in_ref": only_ref, "reached_only_in_new": only_new,
            "reached_only_in_ref_with_probe_return_or_fallback": bad,
            "reached_only_in_ref_done_tail_record": [c for c in only_ref if c not in bad],
            # as c55_avail.py: no run reaching re-READY in both = criterion not met (NaN median)
            "re_ready_ok": med is not None and med <= AVAIL_TOL_S and not bad,
            "passed": bool(len(pr_new) <= len(pr_ref) and med is not None
                           and med <= AVAIL_TOL_S and not bad)}


def availability_rows(new: Mapping[str, Mapping[str, Any] | None],
                      ref: Mapping[str, Mapping[str, Any] | None] | None,
                      ref_label: str | None) -> list[dict[str, Any]]:
    """C-S8-42 (spec rev. 55 269.3 #3): two record rows (PROBE -> LEVEL returns, re-READY vs the
    reference batch); ``criterion_met`` carries the 269.2 criterion, ``passed`` stays None (control
    judges). No row without a reference or an episode."""
    if ref is None or not new:
        return []
    s = availability_compare(new, ref)
    per = {c: {"new": new[c], "ref": ref.get(c)} for c in sorted(new) if new[c] is not None}
    return [_row("C-S8-42 PROBE -> LEVEL returns after the event: runs, this batch <= reference "
                 f"(record, spec rev. 55 269.2 #2; reference {ref_label})", "*",
                 {"runs_new": len(s["probe_return_runs_new"]),
                  "runs_ref": len(s["probe_return_runs_ref"]), "ids": s["ids"]},
                 len(s["probe_return_runs_ref"]), None,
                 "; ".join(f"{c}: {per[c]['new']['probe_returns_s']} s ("
                           + ", ".join(x[1] for x in per[c]["new"]["probe_aborts"]) + ")"
                           for c in s["probe_return_runs_new"])[:3000] or "no probe return",
                 kind="record", criterion_met=s["probe_return_ok"],
                 runs_new=s["probe_return_runs_new"], runs_ref=s["probe_return_runs_ref"],
                 missing_in_reference=s["missing_in_reference"], rule=AVAIL_RULE),
            _row("C-S8-42 re-READY after the event vs reference: median (new - ref) <= +"
                 f"{AVAIL_TOL_S:g} s over runs reaching it in both; reference-only runs with a "
                 "probe return or a rod fallback = fail (record, spec rev. 55 269.2 #3; "
                 f"reference {ref_label})", "*",
                 {"both": s["re_ready_both"], "median_delta_s": s["median_delta_s"],
                  "only_ref": len(s["reached_only_in_ref"]),
                  "only_ref_with_probe_return_or_fallback":
                      len(s["reached_only_in_ref_with_probe_return_or_fallback"]),
                  "only_new": len(s["reached_only_in_new"])},
                 AVAIL_TOL_S, None,
                 f"later > {AVAIL_TOL_S:g} s: {s['later_runs']}; worst {s['worst']}; only in "
                 f"reference with probe return / fallback: "
                 f"{s['reached_only_in_ref_with_probe_return_or_fallback']}; DONE-tail record: "
                 f"{s['reached_only_in_ref_done_tail_record']}",
                 kind="record", criterion_met=s["re_ready_ok"], c55_summary=s,
                 per_run=per, rule=AVAIL_RULE)]


def reapproach_rt_record(names: Sequence[tuple[float, str]], t_ev_rel: float | None, t0: float,
                         controller_meta: Mapping[str, Any] | None, pads: Mapping[str, Any] | None,
                         rec: Mapping[str, np.ndarray] | None,
                         forced: Mapping[str, Any] | None = None, *,
                         f_min_N: float | None = None) -> dict[str, Any] | None:
    """C-S8-37 (spec rev. 52 230 / 235): re-approach runs after the event (count, re-triggers
    from the controller meta ``lifted_reapproach[].is_retrigger``), deferred starts
    (``leg_reapproach_deferred:<leg>``) and the twist work bins (:func:`twist_work_bins`).
    Times relative to the run start ``t0``; None without an event time. ``forced`` (C-S8-40):
    the run's :func:`forced_window` (run-start relative), masked in the work bins. C-S8-41:
    ``deferred_min`` = :func:`deferred_leg_minimum` (``f_min_N`` gives its FLAG)."""
    if t_ev_rel is None:
        return None
    te = float(t_ev_rel)
    runs = []
    for r in (controller_meta or {}).get("lifted_reapproach") or []:
        s = r.get("start_s")
        if not isinstance(s, int | float) or s - t0 < te - 1e-6:
            continue
        runs.append({"start_s": round(float(s) - t0 - te, 3), "leg": r.get("leg"),
                     "is_retrigger": r.get("is_retrigger"), "outcome": r.get("outcome"),
                     "end_s": None if r.get("end_s") is None
                     else round(float(r["end_s"]) - t0 - te, 3)})
    deferred = [e for e in named_events(names, "leg_reapproach_deferred")
                if e["t_s"] >= te - 1e-6]
    has_flag = any(r["is_retrigger"] is not None for r in runs)
    out = {"runs_after_event": len(runs),
           "retriggers": sum(1 for r in runs if r["is_retrigger"]) if has_flag else None,
           "starts_after_1.5_s": sum(1 for r in runs if r["start_s"] > RT_WORK_AFTER_S + 1e-9),
           "deferred": len(deferred),
           "deferred_rel_s": [[round(e["t_s"] - te, 3), e["leg"]] for e in deferred][:30],
           "runs": runs[:30],
           "is_retrigger_recorded": has_flag,
           "work": None if pads is None else twist_work_bins(
               pads, rec, te + t0, forced=forced_rel_to_event(forced, te)),
           "deferred_min": deferred_leg_minimum(names, te, t0, pads, f_min_N,
                                                t_o_s=deferred_t_o_s(controller_meta))
           if deferred else None,
           "rule": RT_WORK_RULE}
    return out


RT_WORK_REF_FLAG_J = 20.0
"""C-S8-40 (spec rev. 54 248.3 record row 3): FLAG when the largest cluster work of an RT run
exceeds that of the same episode in the reference (768) batch by more than this."""


def deferred_min_rows(cms: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """C-S8-41 (spec rev. 54 261, U-S8-57 (a)): record row over the RT-variant runs with a
    deferred re-approach start: the true minimum of the deferred leg
    (:func:`deferred_leg_minimum`), FLAG when below F_min. No row without an RT-variant run."""
    rt = {c: m for c, m in cms.items() if m.get("reapproach_variant") == "rt"}
    if not rt:
        return []
    per = {c: (m.get("rt") or {}).get("deferred_min") for c, m in rt.items()}
    per = {c: v for c, v in per.items() if v and v["windows"]}
    flagged = {c: [x for x in v["windows"] if x["below_F_min"]] for c, v in per.items()}
    flagged = {c: v for c, v in flagged.items() if v}
    worst = min(((c, v["worst"]) for c, v in per.items()), key=lambda kv: kv[1]["min_kN"],
                default=None)
    fmin = next((v["f_min_kN"] for v in per.values() if v.get("f_min_kN") is not None), None)

    # C-S8-42 #2: reference columns (attach_deferred_reference), FLAG text only
    ref_flagged = {c: [x for x in v["windows"] if x.get("ref_flag")] for c, v in per.items()}
    ref_flagged = {c: v for c, v in ref_flagged.items() if v}
    compared = sum(1 for v in per.values() for x in v["windows"] if x.get("ref_0_4s"))
    no_ref = sorted(c for c, v in per.items() if not v.get("reference"))

    def txt(c: str, x: Mapping[str, Any]) -> str:
        return (f"{c} {x['leg']} deferred {x['deferred_s']} s, next start {x['next_start_s']} s: "
                f"{x['min_kN']:.2f} kN at {x['min_t_s']:+.2f} s (raw 1 ms {x['raw_min_kN']:.2f} "
                f"kN{', lift' if x['lift'] else ''})")

    note = "; ".join(txt(c, x) for c, v in sorted(flagged.items()) for x in v)[:3000] \
        or "no deferred leg below F_min"
    if ref_flagged:
        note += " | reference FLAG (event + 0..4 s): " + "; ".join(
            f"{c} {x['leg']}: " + ", ".join(x["ref_flag"])
            for c, v in sorted(ref_flagged.items()) for x in v)[:2000]
    return [_row("C-S8-41 RT deferral: true minimum of the deferred leg (deferral .. "
                 f"min(next start, deferral + T_o) + {DEFERRED_TAIL_S:g} s, spec rev. 55 267), "
                 "< F_min = FLAG (record, U-S8-57 (a); C-S8-42 reference columns event + 0..4 s)",
                 "*",
                 {"rt_runs": len(rt), "runs_with_deferral": len(per),
                  "windows": sum(v["n_windows"] for v in per.values()),
                  "flagged_runs": len(flagged),
                  "worst": None if worst is None else [worst[0], worst[1]["leg"],
                                                       worst[1]["min_kN"]]},
                 fmin, None, note,
                 kind="record", flag=bool(flagged) or bool(ref_flagged), flagged=sorted(flagged),
                 ref_flagged=sorted(ref_flagged), ref_compared_windows=compared,
                 runs_without_reference=no_ref,
                 ref_thresholds={"min_kN": DEFERRED_REF_FLAG_KN, "time_s": DEFERRED_REF_FLAG_S},
                 window_rule=DEFERRED_WINDOW_RULE,
                 per_run={c: v["windows"] for c, v in per.items()}, rule=DEFERRED_MIN_RULE,
                 ref_rule=DEFERRED_REF_RULE)]


def rt_rows(cms: Mapping[str, Mapping[str, Any]],
            ref_work: Mapping[str, Mapping[str, Any] | None] | None = None,
            ref_label: str | None = None) -> list[dict[str, Any]]:
    """C-S8-37 / C-S8-40 rows over runs with an ``rt`` record (:func:`reapproach_rt_record`):
    the RT record (runs, re-triggers, deferred starts per run); the twist-work recurrence row
    (spec rev. 54 248.3: clusters <= :data:`RT_WORK_MAX_CLUSTERS`), judged for the runs of the
    RT variant (``settings.reapproach_variant`` = ``rt``, C-S8-36 bundles A / C / D), record for
    the others (the 768 before P-S8-16, F1-only runs); record rows (i) rev. 52 unmasked bin max,
    (ii) masked bin max and largest cluster work; with ``ref_work`` (run id -> the work of the
    same episode in the reference batch, ``--ref-batch``) the FLAG record row 3."""
    rows: list[dict[str, Any]] = []
    rec = {c: m["rt"] for c, m in cms.items() if m.get("rt") and m["rt"]["runs_after_event"]}
    if not cms:
        return rows
    tot = {"runs_with_reapproach": len(rec),
           "runs_after_event": sum(v["runs_after_event"] for v in rec.values()),
           "retriggers": sum(v["retriggers"] or 0 for v in rec.values()),
           "deferred": sum(v["deferred"] for v in rec.values()),
           "starts_after_1.5_s": sum(v["starts_after_1.5_s"] for v in rec.values()),
           "runs_with_deferred": sorted(c for c, v in rec.items() if v["deferred"])}
    rows.append(_row("C-S8-37 re-approach record after the event: runs / re-triggers / deferred "
                     "starts (P-S8-16 RT; record)", "*", tot, None, None,
                     "; ".join(f"{c}: {v['runs_after_event']} runs, {v['retriggers']} re-trig, "
                               f"{v['deferred']} deferred, {v['starts_after_1.5_s']} after 1.5 s"
                               for c, v in sorted(rec.items()))[:3000] or "none",
                     kind="record", per_run={c: {k: v[k] for k in (
                         "runs_after_event", "retriggers", "deferred", "starts_after_1.5_s",
                         "deferred_rel_s", "runs")} for c, v in rec.items()}))
    judged, recorded = {}, {}
    for c, m in cms.items():
        w = (m.get("rt") or {}).get("work")
        if not w:
            continue
        (judged if m.get("reapproach_variant") == "rt" else recorded)[c] = w
    for label, sel, kind in (("judged (RT variant runs)", judged, "judged"),
                             ("record (runs without the RT variant tag)", recorded, "record")):
        if not sel:
            continue
        ok = {c: w for c, w in sel.items() if w.get("passed") is not None}
        nj = sorted(c for c, w in sel.items() if w.get("passed") is None)
        bad = {c: w["clusters"] for c, w in ok.items() if not w["passed"]}
        worst = max(ok.items(), key=lambda kv: (kv[1]["n_clusters"], kv[1]["max_cluster_J"]),
                    default=None)
        rows.append(_row(
            f"C-S8-36 twist-mode work recurrence: clusters of 0.5 s bins > "
            f"+{RT_WORK_LIMIT_J:g} J after event + 1.5 s (forced window masked) <= "
            f"{RT_WORK_MAX_CLUSTERS} (spec rev. 54 248.3, ASSUMPTION) - {label}", "*",
            {"runs": len(ok), "failed": len(bad), "not_judgeable": nj,
             "worst": None if worst is None else [worst[0], worst[1]["n_clusters"],
                                                  worst[1]["max_cluster_J"]]},
            RT_WORK_MAX_CLUSTERS, ((not bad) if ok else None) if kind == "judged" else None,
            "; ".join(f"{c}: {len(v)} clusters " + ", ".join(f"{a:g} s {w:+.1f} J"
                                                              for a, w in v)
                      for c, v in sorted(bad.items()))[:3000] or "no recurrence",
            kind=kind, over=bad, not_judgeable=nj, rule=RT_WORK_RULE))
        raw = {c: w["raw_max_bin_after_J"] for c, w in sel.items()
               if w.get("raw_max_bin_after_J") is not None}
        over = {c: v for c, v in raw.items() if v > RT_WORK_LIMIT_J}
        wr = max(raw.items(), key=lambda kv: kv[1], default=None)
        rows.append(_row(f"C-S8-36 twist-mode actuator work, every 0.5 s bin after event + 1.5 s "
                         f"<= +{RT_WORK_LIMIT_J:g} J (ASSUMPTION) (record, rev. 52) - {label}",
                         "*",
                         {"runs": len(raw), "over_limit": len(over),
                          "worst": None if wr is None else [wr[0], round(wr[1], 2)]},
                         RT_WORK_LIMIT_J, None,
                         "; ".join(f"{c}: {v:.1f} J" for c, v in sorted(
                             over.items(), key=lambda kv: -kv[1]))[:2000] or "none over",
                         kind="record", over=over))
        per = {c: {"max_bin_after_J": None if w["max_bin_after_J"] is None
                   else round(w["max_bin_after_J"], 2), "max_cluster_J": w["max_cluster_J"],
                   "n_clusters": w["n_clusters"], "masked_s": w.get("masked_s")}
               for c, w in ok.items()}
        wm = max(per.items(), key=lambda kv: kv[1]["max_cluster_J"] or 0.0, default=None)
        rows.append(_row(f"C-S8-36 twist-mode work after event + 1.5 s, forced window masked: max "
                         f"bin / largest cluster [J] (record, rev. 54) - {label}", "*",
                         {"runs": len(per), "masked_runs": sum(
                             1 for v in per.values() if v["masked_s"] is not None),
                          "worst_cluster": None if wm is None
                          else [wm[0], wm[1]["max_cluster_J"]]},
                         None, None, kind="record", per_run=per))
    if ref_work is not None and judged:
        cmp_, flag, missing = {}, {}, []
        for c, w in judged.items():
            r = ref_work.get(c)
            if w.get("max_cluster_J") is None:
                continue
            if not r or r.get("max_cluster_J") is None:
                missing.append(c)
                continue
            dlt = float(w["max_cluster_J"]) - float(r["max_cluster_J"])
            cmp_[c] = {"run_J": w["max_cluster_J"], "ref_J": r["max_cluster_J"],
                       "diff_J": round(dlt, 2)}
            if dlt > RT_WORK_REF_FLAG_J:
                flag[c] = cmp_[c]
        rows.append(_row(f"C-S8-36 twist-mode work: largest cluster RT - reference > "
                         f"+{RT_WORK_REF_FLAG_J:g} J = FLAG (record, spec rev. 54 248.3 row 3; "
                         f"reference {ref_label})", "*",
                         {"compared": len(cmp_), "flagged": len(flag),
                          "missing_in_reference": sorted(missing)},
                         RT_WORK_REF_FLAG_J, None,
                         "; ".join(f"{c}: {v['run_J']:.1f} vs {v['ref_J']:.1f} J"
                                   for c, v in sorted(flag.items()))[:2000] or "no FLAG",
                         kind="record", flag=bool(flag), flagged=flag, per_run=cmp_))
    rows.extend(deferred_min_rows(cms))  # C-S8-41 (spec rev. 54 261, U-S8-57 (a))
    return rows


def plant_rod_collapse(pads: Mapping[str, Any], rec: Mapping[str, np.ndarray] | None,
                       t0: float) -> list[dict[str, Any]]:
    """C-S8-34 ④ (spec rev. 51 222.4): locked lift-offs with a rod-pressure collapse, one tag
    window each (relative and engine times). Lift-off = 1 ms ``airborne`` onset; locked = the
    record ``u_applied`` of the period holding the onset ``|u| <= 1e-6 m/s``; collapse = rod
    pressure 5 samples before minus 10 samples after > 50 bar."""
    if rec is None or "u_applied" not in rec or "airborne" not in pads \
            or "rod_pressure" not in pads:
        return []
    tp = np.asarray(pads["t"], float)
    air = np.asarray(pads["airborne"], bool)
    rp = np.asarray(pads["rod_pressure"], float)
    hp = np.asarray(pads["head_pressure"], float) if "head_pressure" in pads else None
    tr = np.asarray(rec["t"], float)
    ua = np.asarray(rec["u_applied"], float)
    nb, na = ROD_COLLAPSE_BEFORE_SAMPLES, ROD_COLLAPSE_AFTER_SAMPLES
    out = []
    for j, leg in enumerate(LEGS):
        on = np.flatnonzero(np.diff(air[:, j].astype(int)) == 1) + 1
        for i in on:
            if i < nb + 1 or i + na >= tp.size:
                continue
            k = int(np.searchsorted(tr, tp[i], side="right")) - 1
            if k < 0 or abs(float(ua[k, j])) > LOCKED_U_M_S:
                continue
            drop = float(rp[i - nb, j] - rp[i + na, j])
            if drop <= ROD_COLLAPSE_DROP_PA:
                continue
            t_rel = float(tp[i]) - t0
            a, b = t_rel - ROD_COLLAPSE_HALF_WINDOW_S, t_rel + ROD_COLLAPSE_HALF_WINDOW_S
            period = float(np.median(np.diff(tr))) if tr.size > 1 else 0.1
            phase_s = float(tp[i] - tr[k])
            out.append({"leg": leg, "liftoff_s": t_rel, "liftoff_engine_s": float(tp[i]),
                        "rod_before_bar": float(rp[i - nb, j]) / 1e5,
                        "rod_after_bar": float(rp[i + na, j]) / 1e5,
                        "head_before_bar": None if hp is None else float(hp[i - nb, j]) / 1e5,
                        "head_after_bar": None if hp is None else float(hp[i + na, j]) / 1e5,
                        "u_applied_m_s": float(ua[k, j]),
                        "from_10hz_boundary_ms": 1e3 * min(phase_s, phase_s - period,
                                                            key=abs),
                        "start_s": a, "end_s": b, "start_engine_s": a + t0,
                        "end_engine_s": b + t0, "rule": ML_TAG_RULES["plant_rod_collapse"]})
    return out


RELEASE_STEP_PA = 20e5
RELEASE_TAG_S = 0.3
RELEASE_MATCH_S = 0.010
OVERLAP_SPEED_FRACTION = 0.05
COLLAPSE_RECONTACT_EXTRA_S = 0.1
"""H-S8-4 (``02_hydraulic/s8_seal_friction_counterbalance.md`` 12.3 / 12.6, ASSUMPTION): a plant
release (valve ``|u|`` crossing ``lock_eps`` upward, exact exponential valve between the 10 Hz
rows, ``h_s8_4_scan.valve_events``) whose 1 ms rod pressure changes by more than 20 bar from the
last sample at or before the release to two samples later is the F1 reading step
(``plant_release_rod_step``, window ``[t_b, t_b + 0.3 s]`` on that leg's p_h / p_r features).
A ``plant_rod_collapse`` lift-off is matched to a release of the same leg within 10 ms; when the
new command is inside the spool overlap or at its boundary (``|u_new| < 5 % v_max``, 12.9) the
window end is ``max(lift-off + 0.3 s, re-contact + 0.1 s)`` (ML28_ep6 RL, ML81_ep5 RR, ML88_ep0
RR)."""


def valve_release_events(t10: np.ndarray, valve: np.ndarray, issued: np.ndarray, tau_s: float,
                         eps_m_s: float, t_end: float) -> list[tuple[float, str, float, float]]:
    """Lock / release instants of one leg (``h_s8_4_scan.valve_events``, hydraulics 12.3): between
    rows ``k`` and ``k + 1`` the valve relaxes from ``valve[k]`` towards ``issued[k]`` with
    ``tau_s``; returns ``(time, 'lock' | 'release', u_target, row time)`` (engine times)."""
    events = []
    locked = abs(valve[0]) <= eps_m_s
    for k in range(len(t10)):
        t0 = float(t10[k])
        t1 = float(t10[k + 1]) if k + 1 < len(t10) else float(t_end)
        u0, ut = float(valve[k]), float(issued[k])
        if locked and abs(u0) > eps_m_s:
            events.append((t0, "release", ut, t0))
            locked = False
        elif not locked and abs(u0) <= eps_m_s:
            events.append((t0, "lock", ut, t0))
            locked = True
        if locked and abs(ut) > eps_m_s:
            frac = (abs(ut) - eps_m_s) / abs(ut - u0)
            if 0.0 < frac < 1.0:
                x = -tau_s * math.log(frac)
                if t0 + x < t1:
                    events.append((t0 + x, "release", ut, t0))
                    locked = False
        elif not locked and abs(ut) <= eps_m_s and abs(u0) > eps_m_s and abs(ut - u0) > 0:
            frac = (math.copysign(eps_m_s, u0) - ut) / (u0 - ut)
            if 0.0 < frac < 1.0:
                x = -tau_s * math.log(frac)
                if t0 + x < t1:
                    events.append((t0 + x, "lock", ut, t0))
                    locked = True
    return events


def plant_release_steps(pads: Mapping[str, Any], r8: Mapping[str, np.ndarray], tau_s: float,
                        eps_m_s: float, t0: float) -> list[dict[str, Any]]:
    """H-S8-4 F1 record: the plant releases with a 1 ms rod-pressure change > 20 bar
    (:data:`RELEASE_STEP_PA`), one ``[t_b, t_b + 0.3 s]`` window each (relative and engine)."""
    if "rod_pressure" not in pads or "valve_u" not in r8 or "issued_u" not in r8:
        return []
    t = np.asarray(pads["t"], float)
    rod = np.asarray(pads["rod_pressure"], float)
    head = np.asarray(pads["head_pressure"], float) if "head_pressure" in pads else None
    air = np.asarray(pads["airborne"], bool) if "airborne" in pads else None
    t10 = np.asarray(r8["t"], float)
    valve = np.asarray(r8["valve_u"], float)
    issued = np.asarray(r8["issued_u"], float)
    out = []
    for j, leg in enumerate(LEGS):
        for te, kind, ut, tb in valve_release_events(t10, valve[:, j], issued[:, j], tau_s,
                                                     eps_m_s, float(t[-1])):
            if kind != "release" or te < t[0] + 0.01 or te > t[-1] - 0.02:
                continue
            ib = int(np.searchsorted(t, te, side="right")) - 1
            ia = ib + 2
            if ib < 1 or ia + 3 >= t.size:
                continue
            jump = float(rod[ia, j] - rod[ib, j])
            if abs(jump) <= RELEASE_STEP_PA:
                continue
            a, b = tb - t0, tb - t0 + RELEASE_TAG_S
            out.append({"leg": leg, "t_release_s": te - t0, "t_boundary_s": tb - t0,
                        "t_x_ms": (te - tb) * 1e3, "u_new_m_s": ut,
                        "rod_before_bar": float(rod[ib, j]) / 1e5,
                        "rod_after_bar": float(rod[ia, j]) / 1e5, "rod_jump_bar": jump / 1e5,
                        "head_before_bar": None if head is None else float(head[ib, j]) / 1e5,
                        "head_after_bar": None if head is None else float(head[ia, j]) / 1e5,
                        "airborne_before": None if air is None else bool(air[ib, j]),
                        "features": ["head_pressure", "rod_pressure"],
                        "start_s": a, "end_s": b, "start_engine_s": a + t0,
                        "end_engine_s": b + t0})
    return out


def link_collapse_releases(collapse: list[dict[str, Any]], releases: list[dict[str, Any]],
                           pads: Mapping[str, Any], t0: float, v_max_m_s: float
                           ) -> list[dict[str, Any]]:
    """Match each ``plant_rod_collapse`` lift-off to its release (same leg, within 10 ms; in
    place) and extend the window end of an overlap / boundary command to re-contact + 0.1 s;
    returns the releases not matched (the ``plant_release_rod_step`` tag)."""
    t = np.asarray(pads["t"], float)
    air = np.asarray(pads["airborne"], bool)
    used = set()
    for x in collapse:
        cand = [(abs(r["t_release_s"] - x["liftoff_s"]), i) for i, r in enumerate(releases)
                if r["leg"] == x["leg"]
                and abs(r["t_release_s"] - x["liftoff_s"]) <= RELEASE_MATCH_S + 1e-9]
        if not cand:
            x["release"] = None
            continue
        i = min(cand)[1]
        used.add(i)
        r = releases[i]
        x["release"] = {k: r[k] for k in ("t_release_s", "t_boundary_s", "t_x_ms", "u_new_m_s",
                                          "rod_jump_bar")}
        frac = abs(r["u_new_m_s"]) / v_max_m_s if v_max_m_s > 0 else math.inf
        x["release"]["u_new_fraction_v_max"] = frac
        j = LEGS.index(x["leg"])
        k = int(np.searchsorted(t, x["liftoff_engine_s"] - 1e-9))
        off = np.flatnonzero(~air[k:, j])
        rc = None if off.size == 0 else float(t[k + off[0]]) - t0
        x["recontact_s"] = rc
        if frac < OVERLAP_SPEED_FRACTION and rc is not None:
            end = max(x["end_s"], rc + COLLAPSE_RECONTACT_EXTRA_S)
            if end > x["end_s"]:
                x["end_s"], x["end_engine_s"] = end, end + t0
                x["window_extended"] = "re-contact + 0.1 s (overlap / boundary command, H-S8-4)"
    return [r for i, r in enumerate(releases) if i not in used]


def rod_fallback_command_context(e: dict[str, Any], tc: np.ndarray, issued: np.ndarray,
                                 rec: Mapping[str, np.ndarray] | None,
                                 pads: Mapping[str, Any] | None, t0: float) -> None:
    """C-S8-34 ③ (spec rev. 51 222.5): commands around a rod fallback at the 10 Hz sample
    ``k`` (``e['t_s']`` relative), in place: issued this sample (out from the next boundary,
    d = 1), the command applied from this boundary (issued at ``k - 1``) and over the past period
    (issued at ``k - 2``), the plant ``u_applied`` at ``t_k-1`` / ``t_k`` and whether the plant
    valve was locked over the past period (``|u_applied(t_k-1)| <= 1e-6 m/s``); the 1 ms
    ``s_motor`` range over the past period is recorded beside it."""
    j = LEGS.index(e["leg"]) if e.get("leg") in LEGS else None
    if j is None:
        return
    k = int(np.clip(np.searchsorted(tc, e["t_s"] - 1e-9), 0, tc.size - 1))

    def iss(i: int) -> float | None:
        return None if i < 0 else float(issued[i, j]) * 1e3

    e["issued_this_sample_mm_s"] = iss(k)
    e["applied_this_period_issued_mm_s"] = iss(k - 1)
    e["applied_past_period_issued_mm_s"] = iss(k - 2)
    if rec is None or "u_applied" not in rec:
        return
    tr = np.asarray(rec["t"], float) - t0
    kr = int(np.clip(np.searchsorted(tr, e["t_s"] - 1e-9), 0, tr.size - 1))
    ua = np.asarray(rec["u_applied"], float)
    e["plant_u_applied_now_mm_s"] = float(ua[kr, j]) * 1e3
    e["plant_u_applied_past_mm_s"] = None if kr < 1 else float(ua[kr - 1, j]) * 1e3
    e["plant_locked_past_period"] = None if kr < 1 else bool(abs(float(ua[kr - 1, j]))
                                                             <= LOCKED_U_M_S)
    if kr >= 1 and pads is not None and "s_motor" in pads:  # record value, not part of the rule
        tp = np.asarray(pads["t"], float) - t0
        sel = (tp > tr[kr - 1] + 1e-9) & (tp <= tr[kr] + 1e-9)
        if sel.any():
            e["plant_s_motor_ptp_past_um"] = float(
                np.ptp(np.asarray(pads["s_motor"], float)[sel, j])) * 1e6


def _rod_fallback_text(e: Mapping[str, Any]) -> str:
    """ML-2 rod fallback cause text (C-S8-34 ③: the applied commands, not only the issued)."""
    def f(v: Any, spec: str = "+.4g") -> str:
        return "None" if v is None else format(v, spec)

    return (f"{e['leg']} {e['t_s']:.2f} s reason {e['reason']}, phase {e.get('phase')}; "
            f"applied this period (issued t_k-1) {f(e.get('applied_this_period_issued_mm_s'))} "
            f"mm/s, plant u_applied t_k {f(e.get('plant_u_applied_now_mm_s'))} mm/s; past period "
            f"(issued t_k-2) {f(e.get('applied_past_period_issued_mm_s'))} mm/s, plant "
            f"u_applied t_k-1 {f(e.get('plant_u_applied_past_mm_s'))} mm/s, plant valve locked "
            f"{e.get('plant_locked_past_period')} (s_motor range "
            f"{f(e.get('plant_s_motor_ptp_past_um'), '.3g')} um); issued this sample (out at "
            f"t_k+1) {f(e.get('issued_this_sample_mm_s'))} mm/s; head {e.get('head_bar')} bar, rod "
            f"{e.get('rod_bar')} bar, F {e.get('F_cyl_kN')} kN")


def _fault_reasons(m: Mapping[str, Any]) -> list[tuple[str | None, float, str | None]]:
    """C-S8-27 ②: ``(leg, t, reason)`` of the head-sensor fault reasons (P-S8-14 ③) of a run."""
    return [(e["leg"], round(e["t_s"], 2), e["detail"]) for e in m.get("head_fault_reasons")
            or []]


def _meta_ok(meta: Mapping[str, Any] | None) -> tuple[bool, list[str]]:
    """ML-0 meta check: crawler fields recorded (P-S8-10), sensor grade and zero calibration
    split (P-S8-9)."""
    if meta is None:
        return False, ["no episode meta"]
    bad = []
    if meta.get("crawler_contact") is None:
        bad.append("crawler_contact None")
    if not isinstance(meta.get("crawler_check_passed"), bool):
        bad.append(f"crawler_check_passed {meta.get('crawler_check_passed')!r}")
    if meta.get("sensor_grade") not in ML_SENSOR_GRADES:
        bad.append(f"sensor_grade {meta.get('sensor_grade')!r}")
    if not isinstance(meta.get("zero_calibration"), bool):
        bad.append(f"zero_calibration {meta.get('zero_calibration')!r}")
    return not bad, bad


ROD_FALLBACK_GATE_RULE = (
    "C-S8-41 (spec rev. 54 260.5, U-S8-56 (a)): every base / episode run without a pressure-"
    "sensor fault injection (settings keys SENSOR_FAULT_INJECTION_KEYS) has no "
    "WARN_ROD_PRESSURE_FALLBACK, inside or outside a forced retract window; gate 0. The ML-1 "
    "record row and the ML-2 cause reports stay")


def rod_fallback_gate(cms: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """C-S8-41: runs without a fault injection that have a rod fallback warning
    (:data:`ROD_FALLBACK_GATE_RULE`): ``{"checked": n, "runs": {run: [(leg, t_s, reason,
    in_forced_window), ...]}}`` (relative times)."""
    checked, runs = 0, {}
    for c, m in cms.items():
        fb = m.get("rod_fallback") or {}
        if m.get("fault_injected") or fb.get("injected"):
            continue
        checked += 1
        ev = fb.get("events") or []
        if ev:
            runs[c] = [(e["leg"], round(float(e["t_s"]), 3), e.get("reason"),
                        bool(e.get("in_forced_window"))) for e in ev]
    return {"checked": checked, "runs": runs}


def judge_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """C-S8-41 (spec rev. 54 256.2 / 260.5): one-glance summary of a verify file - failed judged
    rows, the ML-0 rod fallback gate, the ML-1 rod fallback run count (record, it was missing in
    the C-S8-36 summary), the C-S8-41 deferred-leg FLAG and the FLAG record rows."""
    def first(prefix: str) -> Mapping[str, Any] | None:
        return next((r for r in rows if str(r.get("item", "")).startswith(prefix)), None)

    gate = first("ML-0 no rod-pressure fallback")
    ml1 = first("ML-1 runs with a rod-pressure fallback warning")
    dm = first("C-S8-41 RT deferral")
    return {"rows": len(rows),
            "failed": [[str(r["item"])[:110], r.get("case")] for r in rows
                       if r.get("passed") is False],
            "ml0_rod_fallback_gate": None if gate is None
            else {"runs": gate["value"], "passed": gate["passed"]},
            "ml1_rod_fallback_runs": None if ml1 is None else ml1["value"],
            "deferred_leg_below_F_min": None if dm is None
            else {"flagged_runs": dm["value"]["flagged_runs"], "runs": dm.get("flagged")},
            "flag_rows": [str(r["item"])[:110] for r in rows if r.get("flag")]}


def ml_rows(cms: Mapping[str, Mapping[str, Any]], n_bases_plan: int | None,
            n_episodes_plan: int | None, *,
            ref_work: Mapping[str, Mapping[str, Any] | None] | None = None,
            ref_label: str | None = None) -> list[dict[str, Any]]:
    """ML-0 ... ML-3 rows (spec rev. 46 216.8) over the base / episode metrics ``cms``;
    ``ref_work`` / ``ref_label``: reference-batch twist work for :func:`rt_rows` (C-S8-40)."""
    rows: list[dict[str, Any]] = []
    bases = {c: m for c, m in cms.items() if m["kind"] == "base"}
    eps = {c: m for c, m in cms.items() if m["kind"] != "base"}
    ready = [c for c, m in bases.items() if m.get("ready_t_s") is not None and m.get("branched")]
    complete = n_bases_plan is not None and len(bases) == n_bases_plan
    rows.append(_row("ML-0 base runs reach READY (and branch)", "*",
                     [len(ready), len(bases), n_bases_plan], n_bases_plan,
                     (len(ready) == n_bases_plan) if complete else None,
                     f"ready {len(ready)} of {len(bases)} recorded bases (plan {n_bases_plan}); "
                     + ("" if complete else "batch incomplete: not judged; ")
                     + "not ready: " + str(sorted(set(bases) - set(ready))),
                     kind="judged" if complete else "record"))
    bad = {}
    for c, m in cms.items():
        ok, why = _meta_ok(m.get("meta"))
        if not ok:
            bad[c] = why + ([m["meta_error"]] if m.get("meta_error") else [])
    rows.append(_row("ML-0 episode meta: crawler_contact / crawler_check_passed (P-S8-10), "
                     "sensor_grade / zero_calibration split (P-S8-9)", "*", len(bad), 0,
                     not bad, f"{len(cms)} runs checked; " + str(bad)[:1500], bad=bad))
    contacts: dict[str, int] = {}
    for m in cms.values():
        k = str((m.get("meta") or {}).get("crawler_contact"))
        contacts[k] = contacts.get(k, 0) + 1
    rows.append(_row("ML-0 runs per crawler contact (record)", "*", contacts, None, None,
                     f"episodes recorded {len(eps)} (plan {n_episodes_plan})", kind="record"))
    # C-S8-26 ②: FAULT entry without a sensor-fault injection (gate), C-S8-34 ①: split by cause;
    # the stroke-end FAULT is judged per run by U-S8-44 (protective stop)
    fault = {c: {"t_s": m.get("fault_entry_s"),
                 "head_faults": [(e["leg"], round(e["t_s"], 2)) for e in m.get("head_faults", [])],
                 "reasons": _fault_reasons(m),
                 "cause": (m.get("fault_cause") or {}).get("cause"),
                 "cause_source": (m.get("fault_cause") or {}).get("source"),
                 "cause_legs": (m.get("fault_cause") or {}).get("legs")}
             for c, m in cms.items()
             if m.get("fault_entry_s") is not None and not m.get("fault_injected")}
    stroke = {c: v for c, v in fault.items() if v["cause"] == "stroke_end"}
    other = {c: v for c, v in fault.items() if v["cause"] != "stroke_end"}
    rows.append(_row("ML-0 no FAULT entry without a sensor-fault injection, stroke-end FAULT "
                     "apart (C-S8-26 ②; reason from INFO_HEAD_PRESSURE_FAULT_REASON, C-S8-27 ②; "
                     "cause split C-S8-34 ①)", "*",
                     len(other), 0, not other,
                     (str(other)[:1500] if other else "none")
                     + f"; stroke-end FAULT judged by U-S8-44 below: {sorted(stroke)}",
                     fault=other, stroke_end=sorted(stroke)))
    for c in sorted(stroke):
        fc = cms[c]["fault_cause"]
        pr = fc.get("protective") or {}
        att = pr.get("att_err_max_deg")
        mn = pr.get("min_force_kN")
        rows.append(_row("ML-0 stroke-end FAULT = protective stop (U-S8-44): floor outside the "
                         "operating diamond, after the FAULT every leg >= F_min + 5 kN, lift 0, "
                         f"attitude <= {STROKE_END_ATT_TOL_DEG:g} deg", c,
                         [None if fc.get("operating_index") is None
                          else round(fc["operating_index"], 4),
                          None if mn is None else round(min(mn), 2), pr.get("lifted_legs"),
                          None if att is None else round(max(att), 4)],
                         ["> 1", pr.get("limit_kN"), [], STROKE_END_ATT_TOL_DEG],
                         bool(pr.get("passed")),
                         f"FAULT {fc['fault_t_s']:.2f} s, legs {fc.get('legs')} from the "
                         f"{fc.get('source')} (stroke >= {fc['threshold_m']:.4f} m over the last "
                         f"{fc['lookback_s']:g} s); floor {fc.get('floor_deg')} deg, operating "
                         f"index {fc.get('operating_index')}; per-leg min after the FAULT {mn} kN; "
                         f"attitude error max {att} deg over {pr.get('post_fault_s')} s",
                         fault_cause=fc, rule=STROKE_END_RULE))
    by_cause: dict[str, list[str]] = {}
    for c, m in cms.items():
        fc = m.get("fault_cause")
        if fc is not None:
            key = fc["cause"] + (" (injected)" if m.get("fault_injected") else "")
            by_cause.setdefault(key, []).append(c)
    rows.append(_row("ML-0 FAULT entries by cause (C-S8-34 ①, record)", "*",
                     {k: len(v) for k, v in by_cause.items()}, None, None,
                     "; ".join(f"{k}: {sorted(v)}" for k, v in by_cause.items()) or "none",
                     kind="record", by_cause={k: sorted(v) for k, v in by_cause.items()}))
    # C-S8-41 (spec rev. 54 260.5, U-S8-56 (a)): rod fallback without a fault injection = gate
    gate = rod_fallback_gate(cms)
    rows.append(_row("ML-0 no rod-pressure fallback without a sensor-fault injection (gate; "
                     "C-S8-41, spec rev. 54 260.5 / U-S8-56 (a))", "*",
                     len(gate["runs"]), 0, not gate["runs"],
                     (f"{len(gate['runs'])} of {gate['checked']} un-injected runs: "
                      + "; ".join(f"{c}: " + ", ".join(
                          f"{e[0]} {e[1]:.2f} s {e[2]}" + (" (forced window)" if e[3] else "")
                          for e in v) for c, v in sorted(gate["runs"].items())))[:3000]
                     if gate["runs"] else f"none in {gate['checked']} un-injected runs",
                     runs=gate["runs"], rule=ROD_FALLBACK_GATE_RULE))
    rules = {}
    for c, m in cms.items():
        rules.setdefault(str(m.get("step_rule")), []).append(c)
    rows.append(_row("ML-0 D1 step rule per run (C-S8-28 meta, record)", "*",
                     {k: len(v) for k, v in rules.items()}, None, None,
                     "; ".join(f"{k}: {len(v)}" for k, v in rules.items()), kind="record",
                     step_rules={k: sorted(v) for k, v in rules.items()}))
    # C-S8-25 ③: settings refresh + 1-period compare at the branch instant (record)
    ref = [c for c, m in eps.items() if m.get("settings_refreshed")]
    cmp_ = {c: m["first_period_compare"] for c, m in eps.items()
            if m.get("first_period_compare") is not None}
    diff = {c: {"max_du_m_s": v.get("max_abs_command_diff_m_s"),
                "phase": [v.get("phase_old"), v.get("phase_new")],
                "events": [v.get("events_old"), v.get("events_new")]}
            for c, v in cmp_.items() if not v.get("identical")}
    rows.append(_row("ML-0 episode settings refreshed after the branch restore and 1-period "
                     "compare old vs refreshed (C-S8-25 ③, record)", "*",
                     {"refreshed": len(ref), "compared": len(cmp_), "differ": len(diff)},
                     None, None, f"episodes {len(eps)}; differ {str(diff)[:1200]}",
                     kind="record", differ=diff))
    # ML-1 (U-S8-34: the forced window is recorded, no longer masked)
    forced = {c: m for c, m in cms.items() if m.get("forced_window")}
    for c, m in sorted(forced.items()):
        fw, f2 = m["forced_window"], (m.get("F2") or {}).get("forced") or {}
        ins = [e for e in (m.get("rod_fallback") or {}).get("events", []) if e["in_forced_window"]]
        fe = m.get("forced_event") or {}
        rows.append(_row("ML-1 forced retract episode: products inside the forced window (F2, "
                         "rod fallback) and the event (record; U-S8-34: not masked)", c,
                         {"F2_violations": f2.get("violations"), "fallback": len(ins),
                          "speed_fraction": fe.get("speed_fraction")}, None, None,
                         f"leg {fw['leg']}, retract done {fw['done_s']} s, speed "
                         f"{fe.get('speed_fraction')} v_max; F2 in window "
                         f"{f2.get('violations')} of {f2.get('samples')} (max {f2.get('max_kN')} "
                         f"kN); fallback {[(e['leg'], round(e['t_s'], 2), e['reason']) for e in ins]}"
                         f"; window F<F_min {fe.get('window_below_F_min')} lift "
                         f"{fe.get('window_lift_legs')}, after F<F_min {fe.get('after_below_F_min')}"
                         f" lift {fe.get('after_lift_legs')} (min {fe.get('after_min_kN')} kN)"
                         + ("" if fw.get("others") == "controller" else
                            "; ForcedRetract holds every leg to the episode end: masked "
                            "(pre-U-S8-27 episode)"),
                         kind="record", forced_window=fw, fallback=ins, forced_event=fe,
                         ml_mask=m.get("ml_mask")))
    fev = {c: m["forced_event"] for c, m in forced.items() if m.get("forced_event")}
    if fev:
        def count(key: str) -> int:
            return sum(1 for v in fev.values() if v.get(key))

        after_min = [v["after_min_kN"] for v in fev.values() if v.get("after_min_kN") is not None]
        tail_min = [v["tail_min_kN"] for v in fev.values() if v.get("tail_min_kN") is not None]
        speeds = [v["speed_fraction"] for v in fev.values() if v.get("speed_fraction") is not None]
        rows.append(_row("ML-1 forced retract events: episodes with true F < F_min / lift inside "
                         "the window (start .. done), the tail (done .. + 3 s) and after it "
                         "(record, C-S8-27 ③; 1 ms, any leg)", "*",
                         {k: count(k) for k in ("window_below_F_min", "window_lift",
                                                "tail_below_F_min", "tail_lift",
                                                "after_below_F_min", "after_lift")}, None, None,
                         f"{len(fev)} forced episodes; min true force in the tail "
                         f"{min(tail_min) if tail_min else None} kN, after it "
                         f"{min(after_min) if after_min else None} kN; speed fraction "
                         + (f"{min(speeds):.3f}..{max(speeds):.3f}" if speeds
                            else "0.25 (pre-U-S8-34 fixed)"),
                         kind="record", events=fev))
        e2 = {c: v["event_203_1"] for c, v in fev.items() if v.get("event_203_1")}
        ul = sorted(c for c, v in e2.items() if v["U_or_L"])
        ll = sorted(c for c, v in e2.items() if v["L"])
        inst = sorted(c for c, v in e2.items() if v.get("inst_10hz_below_F_min"))
        own = sorted(c for c, v in e2.items() if v.get("forced_leg_U_or_L"))
        rows.append(_row("ML-1 forced retract events, 203.1 definition (U-S8-39: 10 Hz windows "
                         "inside start .. done, 1 ms minimum; any leg): episodes U-or-L / L "
                         "(record; reference column: 10 Hz instantaneous true F < F_min)", "*",
                         [len(ul), len(ll)], None, None,
                         f"{len(e2)} forced episodes; U-or-L {ul}; L {ll}; forced leg only "
                         f"{len(own)} {own}; reference 10 Hz instantaneous {len(inst)} {inst}",
                         kind="record", u_or_l=ul, lift=ll, forced_leg_u_or_l=own,
                         inst_10hz=inst, rule="203.1 (spec rev. 49 219.5)"))
    with_fb = {c: [e for e in (m.get("rod_fallback") or {}).get("events", [])]
               for c, m in cms.items() if (m.get("rod_fallback") or {}).get("events")}
    rows.append(_row("ML-1 runs with a rod-pressure fallback warning (record)", "*",
                     len(with_fb), None, None,
                     "; ".join(f"{c}: " + ", ".join(f"{e['leg']} {e['t_s']:.2f} s"
                                                    for e in v) for c, v in with_fb.items())
                     or "none", kind="record"))
    # C-S8-26 ④: D1' explained pressure steps (record, ML-1 / ML-2)
    steps = {c: [(e["leg"], round(e["t_s"], 2), e["detail"]) for e in m["pressure_steps"]]
             for c, m in cms.items() if m.get("pressure_steps")}
    rows.append(_row(f"ML-1 / ML-2 {PRESSURE_STEP_INFO} explained pressure steps (D1', "
                     "U-S8-26; record)", "*", sum(len(v) for v in steps.values()), None, None,
                     f"{len(steps)} runs; " + (str(steps)[:1500] if steps else "none"),
                     kind="record", steps=steps))
    # C-S8-26 ③: head-sensor faults (cause report, every run incl. forced episodes)
    for c, m in sorted(cms.items()):
        hf = m.get("head_faults") or []
        if not hf or m.get("fault_injected"):
            continue
        reasons = _fault_reasons(m)
        rows.append(_row("ML-2 head-pressure fault without a fault injection (cause report)", c,
                         len(hf), 0, None,
                         "; ".join(f"{e['leg']} {e['t_s']:.2f} s" for e in hf)
                         + f"; reason {reasons or 'not recorded (pre-P-S8-14 run)'}"
                         + f"; FAULT entry {m.get('fault_entry_s')} s; lock valve "
                           f"{m.get('lock_valve')}", kind="report", events=hf, reasons=reasons))
    # U-S8-30 (record): every settlement episode with a lift (C-S8-27 ①: was deep fast only)
    lifted_eps = {c: m for c, m in cms.items() if (m.get("lift") or {}).get("lifted_legs")}
    longest = {c: round(m["lift"]["max_s"], 4) for c, m in lifted_eps.items()}
    rows.append(_row("U-S8-30 settlement episodes with a pad lift: longest lift per episode "
                     f"(record, every settlement; flag > {ML_LIFT_FLAG_S:g} s)", "*",
                     {"episodes": len(lifted_eps),
                      "over_flag": sum(1 for v in longest.values() if v > ML_LIFT_FLAG_S)},
                     None, None, str(dict(sorted(longest.items(), key=lambda kv: -kv[1])))[:1500],
                     kind="record", longest=longest))
    # U-S8-32 / C-S8-27 ①: adjacent legs U57 (gate) + event legs (separate row) per settlement
    # episode with any lift
    n_adj_fail, n_ev_fail, n_split = 0, 0, 0
    over_nominal = []
    for c, m in sorted(cms.items()):
        sp = m.get("u_s8_32")
        if not sp or not sp["any_lift"]:
            continue
        n_split += 1
        rr = u_s8_32_rows(c, sp)
        n_adj_fail += rr[0]["passed"] is False
        n_ev_fail += rr[1]["passed"] is False
        if rr[1].get("recontact_within_nominal") is False:
            over_nominal.append(c)
        rows.extend(rr)
    worst = max(((c, m["u_s8_32"]) for c, m in cms.items() if m.get("u_s8_32")),
                key=lambda kv: kv[1]["adjacent_sum_s"], default=(None, None))
    rows.append(_row("U-S8-32 summary: settlement episodes with a lift, adjacent U57 failures, "
                     "event-leg failures (record)", "*",
                     {"episodes": n_split, "adjacent_fail": n_adj_fail,
                      "event_fail": n_ev_fail,
                      "event_recontact_over_nominal": len(over_nominal)}, None, None,
                     "worst adjacent " + ("none" if worst[0] is None else
                                          f"{worst[0]} {worst[1]['adjacent_sum_s']:.3f} s / "
                                          f"{worst[1]['adjacent_gap_max_m'] * 1e3:.2f} mm")
                     + f"; event-leg re-contact > {EVENT_LEG_RECONTACT_NOMINAL_S:g} s (nominal "
                       f"damping flag, 219.8 re-open at >= 2 nominal-damping runs): "
                       f"{over_nominal}",
                     kind="record", over_nominal=over_nominal))
    # ML-2
    for c, m in sorted(cms.items()):
        if m.get("forced_window"):
            continue
        out_ev = [e for e in (m.get("rod_fallback") or {}).get("events", [])
                  if not e["in_forced_window"]]
        if not out_ev:
            continue
        rows.append(_row("ML-2 rod-pressure fallback outside a forced retract (cause report; "
                         "C-S8-34 ③ applied commands and plant lock)",
                         c, len(out_ev), 0, None,
                         "; ".join(_rod_fallback_text(e) for e in out_ev)
                         + f"; lock valve {m.get('lock_valve')}", kind="report", events=out_ev))
    # C-S8-34 ④ (U-S8-47): ML tags, record rows
    pp = {c: m["reapproach_pingpong"] for c, m in cms.items() if m.get("reapproach_pingpong")}
    rows.append(_row("ML tag reapproach_pingpong: episodes with >= 3 re-approach starts later than "
                     "event + 1.5 s (C-S8-34 ④, spec rev. 51 222.3 / 223.2; record)", "*",
                     len(pp), None, None,
                     "; ".join(f"{c}: {v['late_starts']} late starts, window "
                               f"{v['start_s']:.2f}..{v['end_s']:.2f} s"
                               for c, v in sorted(pp.items())) or "none",
                     kind="record", episodes=sorted(pp)))
    rows.extend(rt_rows(cms, ref_work, ref_label))
    rc = {c: m["plant_rod_collapse"] for c, m in cms.items() if m.get("plant_rod_collapse")}
    rows.append(_row("ML tag plant_rod_collapse: locked lift-offs with a rod-pressure fall > 50 "
                     "bar within 10 ms (C-S8-34 ④, spec rev. 51 222.4 / 223.2; record)", "*",
                     sum(len(v) for v in rc.values()), None, None,
                     "; ".join(f"{c} {x['leg']} {x['liftoff_s']:.3f} s rod "
                               f"{x['rod_before_bar']:.1f}->{x['rod_after_bar']:.1f} bar, "
                               f"{x['from_10hz_boundary_ms']:+.0f} ms from the 10 Hz boundary, "
                               f"window {x['start_s']:.3f}..{x['end_s']:.3f} s"
                               + (" (to re-contact + 0.1 s)" if x.get("window_extended") else "")
                               for c, v in sorted(rc.items()) for x in v) or "none",
                     kind="record", runs=sorted(rc)))
    rs_ = {c: m["plant_release_rod_step"] for c, m in cms.items()
           if m.get("plant_release_rod_step")}
    n_air = sum(1 for v in rs_.values() for x in v if x.get("airborne_before"))
    rows.append(_row("ML tag plant_release_rod_step: plant releases with a 1 ms rod-pressure "
                     "step > 20 bar outside plant_rod_collapse (H-S8-4 F1, hydraulics 12.6; "
                     "record, 0 after the fix)", "*",
                     sum(len(v) for v in rs_.values()), None, None,
                     f"{len(rs_)} runs; airborne before the release {n_air}; first "
                     + "; ".join(f"{c} {x['leg']} {x['t_release_s']:.4f} s rod "
                                 f"{x['rod_before_bar']:.1f}->{x['rod_after_bar']:.1f} bar"
                                 for c, v in sorted(rs_.items())[:10] for x in v[:1]),
                     kind="record", runs=sorted(rs_)))
    ft = {c: m["fault_tail"] for c, m in cms.items() if m.get("fault_tail")}
    rows.append(_row("ML tag fault_tail: FAULT entry .. run end (C-S8-34 ④; record, = ml_masks "
                     "reason fault)", "*", len(ft), None, None,
                     "; ".join(f"{c}: {v['start_s']:.2f}..{v['end_s']:.2f} s ({v['cause']})"
                               for c, v in sorted(ft.items())) or "none",
                     kind="record", runs=sorted(ft)))
    # ML-3
    recs = {c: m["R45_4"] for c, m in cms.items() if m.get("R45_4")}
    n = sum(len(v) for v in recs.values())
    rows.append(_row("ML-3 R45-4 low-load probes (lower bound < F_min + 15 kN at the round "
                     "start; record)", "*", n, None, None,
                     f"{len(recs)} runs; " + ("none: C-S8-24 dedicated cases if still 0 after the "
                                              "pilot" if not n else str(
                                                  {c: [(x['leg'], x['round'],
                                                        x['F2_margin_min_kN'],
                                                        x['E_minus_T2_kN']) for x in v]
                                                   for c, v in recs.items()})[:1500]),
                     kind="record", probes=recs))
    rows.extend(d1pp_ratio_rows(cms, label="ML"))  # C-S8-32 (spec rev. 49 219.2 (c))
    # F2 outside the forced window (record of data quality)
    f2 = {c: (m.get("F2") or {}).get("outside") for c, m in cms.items() if m.get("F2")}
    bad_f2 = {c: v for c, v in f2.items() if v and v["violations"]}
    rows.append(_row("ML F2 F_hat_cal - F_band - F <= 0.6 kN outside the forced window, after "
                     "lift-off (record)", "*", len(bad_f2), None, None,
                     str({c: (v["violations"], v["max_kN"]) for c, v in bad_f2.items()})[:1500]
                     or "none", kind="record"))
    return rows


def ref_episode_root(batch_dir: Path, plan: Mapping[str, Any], ref_batch: Path | None
                     ) -> tuple[Path | None, str | None]:
    """C-S8-40: the ``episodes/`` folder of the reference (768) batch for the twist-work FLAG
    row: ``ref_batch`` (a batch folder or its ``episodes/``), else the C-S8-36 sub-plan
    ``rerun_from`` (``ml_plan.json`` of ``A_rt`` / ``B_f1only``); relative paths from the project
    root. (None, None) when neither exists."""
    from outrigger_sim.verify import s6_bundle_c as bc

    for p, src in ((ref_batch, "--ref-batch"), (plan.get("rerun_from"), "ml_plan rerun_from")):
        if not p:
            continue
        p = Path(p)
        if not p.is_absolute():
            p = Path(bc.PROJECT_ROOT) / p
        if p.resolve() == Path(batch_dir).resolve():
            continue
        ep = p if p.name == "episodes" else p / "episodes"
        if ep.is_dir():
            return ep, src
    return None, None


def judge_ml_batch(batch_dir: Path, out_path: Path | None = None, *,
                   ref_batch: Path | None = None) -> Path:
    """C-S8-22 ⑦: ML pilot batch (``run_S8C.py ml``: ``bases/`` + ``episodes/``) ML-0 ... ML-3;
    writes :data:`ML_VERIFY_NAME` with the rows, the per-run metrics and ``ml_masks`` (episode
    id -> forced-window mask, for ``ml/evaluate.py``). Works on an incomplete batch (rows that
    need the whole batch are records then). ``ref_batch`` (C-S8-40): reference batch of the
    twist-work FLAG row (default: the sub-plan ``rerun_from`` of a C-S8-36 bundle)."""
    from outrigger_sim.contact_episode import MachineConstants
    from outrigger_sim.control.c2 import C2Geometry
    from outrigger_sim.params import load_params
    from outrigger_sim.verify import s6_bundle_c as bc

    batch_dir = Path(batch_dir)
    plan_p = batch_dir / "ml_plan.json"
    plan = json.loads(plan_p.read_text(encoding="utf-8")) if plan_p.exists() else {}
    n_b = len(plan.get("bases") or []) or None
    n_e = sum(len(v) for v in (plan.get("episodes") or {}).values()) or None
    cache: dict[str, tuple[Any, Any]] = {}
    cms: dict[str, dict[str, Any]] = {}
    failed: dict[str, dict[str, Any]] = {}
    for sub in ("bases", "episodes"):
        root = batch_dir / sub
        if not root.exists():
            continue
        # ``_failed_<stamp>`` / ``_rerun_<stamp>``: kept folders of a resume (run_S8C ml --resume)
        for d in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("_")):
            st = ml_run_status(d)
            if st["status"] != "ok":
                failed[d.name] = {"set": sub, **st}
                continue
            res = json.loads((d / "result.json").read_text(encoding="utf-8"))
            level = (res.get("settings") or {}).get("level") or "top"
            if level not in cache:
                params = load_params(level=level)
                cache[level] = (params, MachineConstants.from_geometry(
                    C2Geometry.from_params(params)))
            cms[d.name] = ml_case_metrics(d, *cache[level])
    running = {c: v for c, v in failed.items() if v["status"] == "running"}
    bad = {c: v for c, v in failed.items() if v["status"] != "running"}
    rows = [_row("ML-0 failed runs (case.log 'failed' / no result.json; excluded from every ML "
                 "row and mask)", "*", len(bad), 0, not bad,
                 f"{len(bad)} excluded, {len(running)} still running / not finished; "
                 + str({c: v.get("error") for c, v in bad.items()})[:1500],
                 failed=bad, running=sorted(running))]
    ref_root, ref_src = ref_episode_root(batch_dir, plan, ref_batch)
    ref_work = None
    if ref_root is not None:
        ref_work = {c: ml_twist_work_of_dir(ref_root / c) for c, m in cms.items()
                    if m.get("reapproach_variant") == "rt" and (m.get("rt") or {}).get("work")}
    ref_label = None if ref_root is None else f"{ref_root} ({ref_src})"
    # C-S8-42 (spec rev. 55 269.3 #2): deferred legs vs the same episode of the reference
    for c, m in cms.items():
        attach_deferred_reference((m.get("rt") or {}).get("deferred_min"),
                                  None if ref_root is None else ref_root / c,
                                  event_engine_time=True, ref_label=ref_label)
    rows += ml_rows(cms, n_b, n_e, ref_work=ref_work, ref_label=ref_label)
    # C-S8-42 (spec rev. 55 269.3 #3): PROBE -> LEVEL returns and re-READY vs the reference
    if ref_root is not None:
        eps = sorted(c for c, m in cms.items() if m["kind"] != "base")
        av_new = {c: availability_record(batch_dir / "episodes" / c) for c in eps}
        av_ref = {c: availability_record(ref_root / c) if (ref_root / c).is_dir() else None
                  for c in eps}
        rows += availability_rows(av_new, av_ref, ref_label)
    out = out_path or batch_dir / ML_VERIFY_NAME
    doc = {"meta": {"batch": str(batch_dir), "module": __name__, "rows": len(rows),
                    "failed": sum(1 for r in rows if r["passed"] is False),
                    "bases_recorded": sum(1 for m in cms.values() if m["kind"] == "base"),
                    "episodes_recorded": sum(1 for m in cms.values() if m["kind"] != "base"),
                    "plan": {"bases": n_b, "episodes": n_e},
                    "ref_twist_work": None if ref_root is None else {"episodes": str(ref_root),
                                                                     "source": ref_src},
                    "summary": judge_summary(rows),  # C-S8-41: incl. the ML-1 count
                    "deferred_reference": None if ref_root is None
                    else {"episodes": str(ref_root), "source": ref_src},  # C-S8-42
                    "judge_revision": JUDGE_REVISION_REV56 + " on "
                                      + JUDGE_REVISION_REV55 + " on " + JUDGE_REVISION_REV54
                                      + " on " + JUDGE_REVISION_REV52
                                      + " on " + JUDGE_REVISION_REV51
                                      + " on " + JUDGE_REVISION_REV50
                                      + " on spec rev. 49 219.11 (C-S8-27 "
                                      "update: U-S8-37 event-leg "
                                      "re-contact gate 3.0 s + 2.5 s flag column, U-S8-39 "
                                      "forced retract 203.1 row; C-S8-32 D1'' step ratio row) "
                                      "on rev. 48 218.13 (C-S8-27 ① U-S8-32 adjacent / "
                                      "event legs, ② FAULT reason, ③ forced retract events, ④ "
                                      "FAULT mask; U-S8-34 forced window not masked), rev. 47 "
                                      "217.9 and rev. 46 216.8 ML-0 ... ML-3",
                    "mask_rule": ML_MASK_RULE,
                    "u_s8_32": {"u57_lift_sum_s": U57_LIFT_SUM_S, "u57_gap_m": U57_GAP_M,
                                "u57_cap_s": U57_CAP_S, "event_leg_cum_s": EVENT_LEG_CUM_S,
                                "event_leg_recontact_s": EVENT_LEG_RECONTACT_S,
                                "event_leg_recontact_nominal_s": EVENT_LEG_RECONTACT_NOMINAL_S},
                    "d1pp_step_ratio": {"flag": D1PP_RATIO_FLAG, "step_bar": D1PP_STEP_BAR,
                                        "grades_kN": list(D1PP_FS_GRADES_KN)},
                    "stroke_end_rule": STROKE_END_RULE, "ml_tag_rules": ML_TAG_RULES},
           "rows": rows,
           "ml_masks": {c: m["ml_mask"] for c, m in cms.items() if m.get("ml_mask")},
           # C-S8-34 ④: run -> tag windows (also per run in ml_metrics under the same keys)
           "ml_tags": {"fault_tail": {c: m["fault_tail"] for c, m in cms.items()
                                      if m.get("fault_tail")},
                       "plant_rod_collapse": {c: m["plant_rod_collapse"] for c, m in cms.items()
                                              if m.get("plant_rod_collapse")},
                       "reapproach_pingpong": {c: m["reapproach_pingpong"]
                                               for c, m in cms.items()
                                               if m.get("reapproach_pingpong")},
                       "plant_release_rod_step": {c: m["plant_release_rod_step"]
                                                  for c, m in cms.items()
                                                  if m.get("plant_release_rod_step")}},
           "ml_metrics": cms}
    out.write_text(json.dumps(doc, indent=1, default=bc._json_default, ensure_ascii=False),
                   encoding="utf-8")
    return out


__all__ = ["LIFTOFF_WINDOW_S", "c1_metrics", "c1_row", "classify_windows",
           "clopper_pearson_upper", "detection_metrics", "episodes", "false_flags",
           "is_rigid_crawler", "item9_summary", "judge_batch", "near_fmin_errors",
           "pair_rows_s8", "s8_case_metrics", "air_record", "i4_classify", "i4_compare",
           "i4_event_start", "i4_rows", "judged_force_min", "load_i4_expected",
           "s7_regression_rows", "sampling_only_episodes", "g4_rr_summary", "crawler_label",
           "apply_rev43_rows", "f1_share_N", "h4_one_sided_ok", "h4_reduction",
           "l2b_floor_point_metrics", "l2b_pads_view", "lower_estimate_series", "run_end_cause",
           "air_residual", "probe_7c_split", "score_ex_transient", "reconstruct_twist_history",
           "twist_history", "scale_at", "touch_air_commands", "reapproach_outside_events",
           "first_phase_length", "r44_gate_rows", "air_mask", "cylinder_areas_m2",
           "sensor_static_error_N", "f1_law_limit_N", "f1_law_metrics", "check_hold_rows",
           "calibration_split", "friction_flag_limit_N", "error_split",
           "reconstruct_reground_leg", "low_load_probe_records", "f1_law_rows", "r45_2_rows",
           "forced_window", "forced_mask", "rod_fault_injected", "rod_fallback_events",
           "pooled_side_std", "apply_rev46_rows", "trend_key", "level_trend_rows_s8",
           "wika_pooled_rows", "ml_probe_truth_rows", "ml_case_metrics", "ml_rows",
           "judge_ml_batch", "settle_lift_split", "u_s8_32_rows", "forced_event_record",
           "ml_episode_mask", "mlj_case_metrics", "mlj_rows", "poly345", "operating_index",
           "classify_fault", "stroke_end_protective", "reapproach_pingpong", "plant_rod_collapse",
           "rod_fallback_command_context", "valve_release_events", "plant_release_steps",
           "link_collapse_releases", "pad_normal_at", "reading_variants", "twist_work_bins",
           "reapproach_rt_record", "rt_rows", "deferred_leg_minimum", "deferred_min_rows",
           "rod_fallback_gate", "judge_summary", "deferred_t_o_s", "leg_window_stats",
           "deferred_reference_stats", "deferred_ref_flags", "attach_deferred_reference",
           "availability_record", "availability_compare", "availability_rows",
           "fault_entry_s", "legs_in", "head_fault_of", "g4_metrics", "g4_of_case", "g4_rows",
           "extend_force_limits_N", "g4_4_records", "load_head_delivered",
           "head_delivered_summary", "head_fault_leg_cut"]
