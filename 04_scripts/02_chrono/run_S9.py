"""S9 SCM soft-soil runner: single-pad (P1 / V16), machine settle and lift (P2 / P3a), C2 levelling (P3b).

``00_docs/03_chrono/chrono_build_plan.md`` S9; ``dynamics_model.md`` 5.32.7 #3, 5.33.7 items 1-9,
5.33.9 (P1-L1 ... L6), 5.33.11; ``s6_control_spec.md`` 284 (P3 keys), 287 (cad row). Model
``outrigger_sim.chrono.scm_model`` (machine) and :func:`build_single_pad` here (P1).

Usage (Chrono-dev python, project root)::

    python -I -X utf8 -u 04_scripts/02_chrono/run_S9.py plan
    python -I -X utf8 -u 04_scripts/02_chrono/run_S9.py single-pad --soil G1 --pad-variant dwg_rear250 \
        --leg RL --force 4450 --t-settle 2 --t-end 5 [--scm-shear bprime|native] [--joint spherical|fixed]
    python -I -X utf8 -u 04_scripts/02_chrono/run_S9.py machine --soil G1 [--gravity-ramp 3 --gravity-hold 2] [--lift-s 0]
        [--crawler-grid 0.04]   # dual terrain (U-S9G-1 M14s: pads on --grid, crawler on --crawler-grid)
    python -I -X utf8 -u 04_scripts/02_chrono/run_S9.py level --soil G1 --approved ...   # P3b, gated
    python -I -X utf8 -u 04_scripts/02_chrono/run_S9.py rejudge <batch or case folder> [--dry-run]
        # spec rev. 60 P3-2 / 5 / 7 re-judgement of finished level cases (no Chrono run)

2026-10-29 (spec 414 / 416 / 419.8 / 420): ``p3b.P3-2_loc.late_loc_reapproach`` (:func:`p32_late_loc_block`,
FLAG ``P3-2_late_loc_reapproach`` and ``checks.P3-2_verdict``), ``code_state`` (C2 meta rules + controller
file SHA-256 at the start), zero calibration variant D keys in ``sensors.zero_calibration``, and the rule
events counted in ``p3b_ext.event_counts`` / listed in ``p3b_ext.rule_event_times_rel_s``.

Options common to the SCM runs: ``--soil {J1,J2,G1,S1}`` (``02_params/scm_soil_sets.json``),
``--pad-variant {cad330,dwg_rear250}``, ``--scm-shear {bprime,native}`` (U-S9L-1: bprime =
judgement, native = comparison only), ``--stiffness-mode {series,l1_kt,janosi}`` (U-S9L-2),
``--interface`` (U-S9L-3 sensitivity), ``--k-sw`` (U-S9L-4, 0 = off), ``--grid``, ``--dt``,
``--soil-override KEY=VALUE`` (sensitivities of 5.32.4, e.g. ``elastic_K=7e8``), ``--ray-shape
{mesh,convex}`` (SCM ray targets; mesh = default, P1-V0 5.34.10), ``--crawler-grid`` (dual terrain).

Machine settle (``machine`` and ``level``; dynamics 5.35.4 (a), user decision U-S9P-1 2026-10-26):
gravity magnitude Poly345 over ``--gravity-ramp`` 3 s and hold ``--gravity-hold`` (default 5 s,
settle 8 s, judged on the last 1 s = 7-8 s) with the **settle dashpot** (``--settle-dashpot zrp``,
default): ground-fixed damper on the superstructure COG, heave ``--dashpot-c-z`` 2e6 N s/m along
the SCM plane normal, pitch ``--dashpot-c-pitch`` 3.4e6 and roll ``--dashpot-c-roll`` 2.2e6
N m s/rad about the plane y / x axes (ASSUMPTION, trial values), in-plane translation and yaw
free, full until 3 s, linear to 0 at 5 s (``--dashpot-fade 3 5``), :class:`~outrigger_sim.chrono.
scm_model.SettleDashpot`. ``--settle-dashpot none`` = the former procedure (Poly345 3 s + hold
2 s, dynamics 5.34.2; default hold 2 s then); ``--gravity-ramp-shape step`` = the former sudden
gravity. ``single-pad`` ramps the vertical load (gravity on pad + share body)
Poly345 over ``--load-ramp`` 1 s. Single pad records the SCM nodes inside the pad bottom polygon
(``GetNodeInfo``: contact nodes, node mean sinkage, node - geometric) every 0.1 s and the P1-L6
diagnostics in ``hold.p1_l6``; ``level`` adds the P3 record values (``p3_records``, 5.34.6).
``machine`` with ``--lift-s`` > 0 adds the P3a block (``p3a``: lift-off time, force peaks, end
equilibrium, max s_motor, loaded pad tilt, first-touch SCM rise, minimum cylinder force, sinkage,
attitude, rut clearance, track utilisation; dynamics 5.36.5) and the series keys ``pad_tilt_deg``,
``rut_clearance_m``, ``track_utilisation``, ``node_sinkage_mean_contact_m`` (0.1 s);
``--abort-on-limit`` exits 3 after writing when a force limit or the stroke end margin is exceeded.

``level`` (P3b, control spec 284) needs ``--approved`` (the user confirms the main runs). The
controller is the R8 preset ``C2Config().with_10hz_d1()``, which has the soil response on since
U-S9-C1 (spec rev. 57-59 285, P-S9-8): the runner refuses a config with ``soil.enable`` False
(``--allow-current-c2`` overrides that for a deliberate soil-off comparison; expected to fail on
J1 B, J2 B, S1, 281) and writes the C2 meta ``soil`` block (``c2_soil``, P-S9-7 / 282.4 S-5) and
the lifted re-approach settings (``c2_lifted_reapproach``, P-S9-10 ``max_duration_s``) to the
result. ``--fs-kN`` sets the seal friction level of the plant (front legs; rear x 0.8333,
``actuator.seal_friction.level_N``; 0 = no override, the P3a plant). Records (spec 284 / 287 /
301, dynamics 5.37.5 #2): ``step_series.npz`` (1 ms: crawler / pad SCM normals, track normals,
F_cyl, s_motor, pad sinkage, roll / pitch), the 10 Hz ``s9_rows`` (SCM crawler patch force sum,
pad node sinkage, rut clearance), and ``p3b`` (P3-1 ... P3-9 values, crawler departure by the
P3a-2 rule, creep stop, pre-lift-off minimum F_cyl, track utilisation with the 5 % rule, the
W-61-1 ... 4 watch, the P3-4 judgement window of control D-3 and the re-approach limit FLAG of D-4).
Sensors (control D-1): ``--pressure-grade`` (default WIKA A-10 ``normal``, CHECK zero calibration on)
and ``--imu-grade`` (default ``ideal``); ``record/`` keeps the 10 Hz readings and the applied output,
``controller_commands.npz`` the issued commands. P3b loop length 120 s fixed (D-2). ``plan`` lists the approved P3b set (U-S9P-6 (가): 24 cases) and the two
S8 re-approach limit cases run with it (``s9_batch.py run P3b``).

Study ③ / ① (control design 2026-10-28): :func:`p3b_aug_cases` = J2 / S1 x A / B x auger middle / bottom with the
P3b settings (``s9_batch.py run p3b_aug``); ``level --start-limit verification`` = the run_S8C verification slope
limits (5.5 / 3.5 deg) for the slope rows :func:`s9sl_cases` (``s9_batch.py run S9SL``, C-1 / C-2 confirmed, C-3 /
C-4 drafts). Every ``level`` run also writes ``p3b_ext.reanchor`` (RA-1 .. RA-6: events, per stair step true
minimum F_cyl, pad bushing utilisation, sinkage change), ``p3b_ext.start_condition`` (SL-2 R_c) and
``settle_slope`` (P2-c / P2-d on the slope, plane / gravity / rut basis).

Outputs ``07_results/S9/<action>_<tag>_<stamp>/`` (``result.json`` + ``series.npz``). Units SI;
world = body axes at the start, x forward, y left, z up; gravity (0, 0, -9.80665).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))

import numpy as np  # noqa: E402

RESULTS = ROOT / "07_results" / "S9"
G = 9.80665
RECORD_S = 1.0e-3
"""Series sampling (every step is too much for the SCM node queries)."""
NODE_SINKAGE_EVERY_S = 0.1
CRAWLER_SETTLE_S = 8.0
"""Machine crawler settle before a lift: gravity Poly345 3 s + hold 5 s with the settle dashpot
(dynamics 5.35.4 (a), U-S9P-1; ``--gravity-ramp`` / ``--gravity-hold``). Former values: 5 s
(Poly345 3 s + hold 2 s, 5.34.2, ``--settle-dashpot none``), before that 3 s of sudden gravity."""
GRAVITY_HOLD_DASHPOT_S = 5.0
GRAVITY_HOLD_FORMER_S = 2.0

# --- P1 ... P3 case plan (dynamics 5.33.9, 3.11.4; control spec 284) ---------------------------------

P1_COST_US_PER_STEP = 600.0
"""Single pad on SCM, 2 cm (smoke 2026-10-26: 511-626 us/step, P-cores shared with R1-R3)."""
MACHINE_COST_US_PER_STEP = 15500.0
"""Machine on SCM, 2 cm grid, 4 SCM threads (smoke 2026-10-26, P-cores shared: 15.5 ms/step =
ray testing 4.1 + contact-patch flood fill 9.4 (serial) + rest; 1 thread 18.6 ms). The 3.11.4 #4
estimate (4 ms) did not count the patch search. 4 cm grid: 3.2 ms/step. Triangle-mesh ray targets
(2026-10-26, same load, P-cores shared with the main-tree regression): 4 cm 3.81 ms/step against
4.38 ms with the former convex shapes; 2 cm 18.9 ms/step (crawler only, 1 s settle)."""
MACHINE_COST_4CM_US_PER_STEP = 3200.0
SCM_THREADS_FIXED = 4
"""SCM ray-casting threads for every action (machine, single pad, level). Fixed (not the Chrono
default = all processors) because the OpenMP hit-merge order may depend on the thread count and
P3b layouts are compared by judgement values only (dynamics 5.34.12); = scm_model.SCM_THREADS.
Before 2026-10-26 (batch P1/P2) the single-pad action used the Chrono default."""


def case_plan() -> list[dict[str, Any]]:
    """P1 (5.33.9), P2 (5.32.7 #5), P3a / P3b (284) rows with simulated time and wall estimate."""
    rows: list[dict[str, Any]] = []

    def add(group, name, sim_s, kind, note=""):
        us = P1_COST_US_PER_STEP if kind == "single" else MACHINE_COST_US_PER_STEP
        us4 = P1_COST_US_PER_STEP if kind == "single" else MACHINE_COST_4CM_US_PER_STEP
        rows.append({"group": group, "case": name, "sim_s": sim_s, "kind": kind,
                     "wall_est_s": sim_s / 1e-4 * us * 1e-6,
                     "wall_est_4cm_grid_s": sim_s / 1e-4 * us4 * 1e-6, "note": note})

    for soil in ("J1", "G1"):
        for shear in ("native", "bprime_c0phi0"):
            add("P1-L1", f"L1_{soil}_fixed_F0_{shear}", 3.0, "single", "|F_t| = 0, settle diff <= 0.1 %")
    for soil in ("J1", "G1"):
        for F in (4450.0, 6980.0, 20000.0):
            add("P1-L2", f"L2_{soil}_B_RL_F{F:.0f}", 12.5, "single", "drift <= 0.01 mm, F_t = F +-0.5 %")
    for soil in ("J1", "J2"):
        add("P1-L3", f"L3_{soil}_B_RL_1.2limit", 7.5, "single", "F_t / limit = 1 +-2 %")
    for case in ("J1_B_RL", "J1_A_FL", "G1_B_RL", "J1_B_RL_ksw0"):
        add("P1-L4", f"L4_{case}_ramp20s", 22.0, "single", "tilt <= 0.5 deg (ksw0: instability record)")
    for soil in ("J1", "G1"):
        add("P1-L5", f"L5_{soil}_crawler_slope3.5", 13.0, "machine", "10 s drift <= 0.1 mm")
    for dt in ("1e-4", "5e-5"):
        add("P1-L6", f"L6_J1_B_native_dt{dt}", 7.5 * (2 if dt == "5e-5" else 1), "single",
            "drift F dt / M +-5 % (record)")
    for soil in ("J1", "J2", "G1", "S1"):
        add("P2", f"P2prime_{soil}_crawler_settle", 8.0, "machine", "P2prime-a..d, dashpot settle 8 s (5.35.4)")
    for soil in ("J1", "G1"):
        for pad in ("A", "B"):
            add("P3a", f"P3a_{soil}_{pad}_lift_open_loop", 28.0, "machine", "lift V4-type, ~20 s")
    for c in p3b_cases():
        add(c["group"], c["case"], P3B_SIM_S, "machine",
            f"C2 levelling (284), {c['soil']} {c['pad']} {c['level']} F_s {c['fs_kN']:g} kN, pad grid {c['grid_m']:g} m; "
            "wall = P3B_EST_S (dynamics 5.37.6, M14s, contended P3a cost)")
        rows[-1]["wall_est_s"] = rows[-1]["wall_est_4cm_grid_s"] = c["est_s"]
    for c in g6_open_loop_cases():
        sp = c["soil_patch"]
        add(c["group"], c["case"], c["sim_s"], "machine",
            f"G6 open loop: P3a G1 B lift with {sp['set']} under {sp['leg']}"
            + (" (optional)" if c["optional"] else f"; compared with {G6_P3A_REFERENCE}"))
        rows[-1]["wall_est_s"] = rows[-1]["wall_est_4cm_grid_s"] = c["est_s"]
    for c in g6_cases():
        sp = c["soil_patch"]
        add(c["group"], c["case"], c["sim_s"], "machine",
            f"G6 soil patch: {c['soil']} base, {sp['set']} under {sp['leg']} (grid {sp['grid_m']:g} m), "
            f"{c['pad']} {c['level']} F_s {c['fs_kN']:g} kN; triple terrain; wall = G6_US_PER_STEP_UPPER (ASSUMPTION)")
        rows[-1]["wall_est_s"] = rows[-1]["wall_est_4cm_grid_s"] = c["est_s"]
    for c in g6p_cases():
        sp = c["soil_patch"]
        add(c["group"], c["case"], c["sim_s"], "machine",
            f"G6P paper set: {c['soil']} base, {sp['set']} under {sp['leg']} (grid {sp['grid_m']:g} m), "
            f"{c['pad']} {c['level']} F_s {c['fs_kN']:g} kN, P-S8-29 {c.get('twist_relax', TWIST_RELAX_PRESET)}; "
            "wall = G6P_EST_S" + (f"; {c['note']}" if c.get("note") else ""))
        rows[-1]["wall_est_s"] = rows[-1]["wall_est_4cm_grid_s"] = c["est_s"]
    for c in p3b_aug_cases():
        add(c["group"], c["case"], P3B_SIM_S, "machine",
            f"study ③: {c['soil']} {c['pad']} {c['level']} F_s {c['fs_kN']:g} kN, P3b settings; paired with "
            f"{c['pair_case']}; wall = P3B_EST_S")
        rows[-1]["wall_est_s"] = rows[-1]["wall_est_4cm_grid_s"] = c["est_s"]
    for c in s9sl_cases(include_draft=True):
        add(c["group"], c["case"], c["sim_s"], "machine",
            f"study ① {c['cid']}{'' if c['confirmed'] else ' (draft, not in the batch)'}: {c['soil']} {c['pad']} "
            f"floor (roll, pitch) {c['floor_deg']} deg, start-limit {c['start_limit']}, {c['purpose']}; "
            "wall = S9SL_WALL_S_PER_SIM_S (ASSUMPTION)")
        rows[-1]["wall_est_s"] = rows[-1]["wall_est_4cm_grid_s"] = c["est_s"]
    for cid, est in P3B_S8C_CASES.items():
        rows.append({"group": "P3b-RE1c", "case": cid, "sim_s": 104.0, "kind": "s8c_L2b_rigid",
                     "wall_est_s": est, "wall_est_4cm_grid_s": est,
                     "note": "run_S8C.py run --only (L2b-NSC rigid floor, R8 preset with_10hz_d1): positive test of "
                             "the re-approach limit max_duration_s 10 s (P-S9-10, U-S9-C4); wall = run_S8C list estimate"})
    return rows


# --- P3b set (control spec 284 / U-S9P-6 (가); dynamics 5.37.6) -------------------------------------

P3B_PAD = {"A": "cad330", "B": "dwg_rear250"}
P3B_PAD_GRID_M = {"G1": 0.02, "J1": 0.01, "J2": 0.01, "S1": 0.02}
"""M14s pad terrain grid per soil (dynamics 5.37.6: G1 / S1 2 cm, J1 / J2 1 cm); crawler 4 cm."""
P3B_CRAWLER_GRID_M = 0.04
P3B_DURATION_S = 120.0
"""Closed-loop time after the 8 s settle, fixed (user decision 2026-10-26, control D-2: 90 -> 120 s, no end
rule; READY <= 90 s ASSUMPTION P3-6 from the closed-loop start leaves >= 30 s after READY)."""
P3B_SIM_S = CRAWLER_SETTLE_S + P3B_DURATION_S
P3B_US_PER_STEP_UPPER = {"G1": 5500.0, "S1": 5500.0, "J1": 9000.0, "J2": 9000.0}
"""Upper per-step cost [us] at dt 1e-4 s for the P3b 4-parallel (contended) runs. G1 / S1 raised 4500 -> 5500
(2026-10-27): the measured 128 s means of ``batch_P3b_20261026_122444`` (pad B, top, F_s 4 kN) are G1 5.10,
S1 4.98, J1 8.69, J2 8.48 ms/step (dynamics 5.37.10 check 4 table; ``contended_P3b_reference`` in
``06_analysis/01_chrono/01_cost/S9_P3b_solo_step_cost.json``; case range G1 4.0-5.3, S1 5.0-5.3, J1 / J2
8.5-11.2), above the old 5.37.6 estimate (G1 / S1 3-4.5, J1 / J2 5-9 ms/step, contended P3a). Solo cost is
about half (full load G1 2.64, S1 2.66, J1 4.55, J2 4.62 ms/step). J1 / J2 stay at 9000 (above the B-top
means). The loaded phase dominates the 120 s loop, so the upper per-step value is used for the whole run."""
P3B_EST_S = {soil: round(P3B_SIM_S / 1.0e-4 * us * 1e-6, -2) for soil, us in P3B_US_PER_STEP_UPPER.items()}
"""Wall estimate per case [s] = P3B_SIM_S (128 s) / 1e-4 x upper us/step: G1 / S1 7000, J1 / J2 11500 (G1 / S1
at 4500 us: 5800; before D-2, 98 s: 4300 / 8600)."""
P3B_S8C_CASES = {"N_RE1c_Fs0_combined": 433.0, "N_RE1c_Fs8_combined": 528.0}
"""Re-approach 10 s limit positive tests added to the P3b set (user decision 2026-10-26): run_S8C
L2b-NSC (rigid floor) cases with the R8 preset; P-core wall estimates of ``run_S8C.py list``."""


def p3b_case(group: str, soil: str, pad: str, level: str, fs: float) -> dict[str, Any]:
    """One P3b-type ``level`` row (the P3b settings, :func:`p3b_level_argv`)."""
    return {"group": group, "case": f"P3b_{soil}_{pad}_{level}_Fs{fs:g}", "soil": soil, "pad": pad,
            "pad_variant": P3B_PAD[pad], "level": level, "fs_kN": fs, "grid_m": P3B_PAD_GRID_M[soil],
            "crawler_grid_m": P3B_CRAWLER_GRID_M, "est_s": P3B_EST_S[soil]}


def p3b_cases() -> list[dict[str, Any]]:
    """The 24 approved P3b cases in run order (U-S9P-6 (가)): P3b-1 G1 10 (A / B x auger 3 x F_s
    4 kN + top F_s 0 / 8 kN x A / B), P3b-2 J1 10 (same), P3b-3 J2 / S1 x A / B, top, 4 kN."""
    out = []

    def add(group, soil, pad, level, fs):
        out.append(p3b_case(group, soil, pad, level, fs))

    for group, soil in (("P3b-1", "G1"), ("P3b-2", "J1")):
        for pad in ("A", "B"):
            for level in ("top", "middle", "bottom"):
                add(group, soil, pad, level, 4.0)
        for pad in ("A", "B"):
            for fs in (0.0, 8.0):
                add(group, soil, pad, "top", fs)
    for soil in ("J2", "S1"):
        for pad in ("A", "B"):
            add("P3b-3", soil, pad, "top", 4.0)
    return out


P3B_AUG_ROWS = (("J2", "B"), ("J2", "A"), ("S1", "A"), ("S1", "B"))
P3B_AUG_LEVELS = ("middle", "bottom")


def p3b_aug_cases() -> list[dict[str, Any]]:
    """Study ③ (control 2026-10-28, user decision: 8 cases): J2 B, J2 A, S1 A, S1 B x auger middle / bottom,
    the P3b settings unchanged (:func:`p3b_level_argv`: F_s 4 kN, pad grid J2 0.01 / S1 0.02 m, crawler 0.04 m,
    zrp, threads 4, loop 120 s, pressure normal, IMU ideal, seed 20261026). ``pair_case`` = the P3b top case of the
    same soil / pad / seed (P3b-3) the record checks of the design compare with. ``est_s`` = :data:`P3B_EST_S`
    (J2 11500, S1 7000 s)."""
    out = []
    for soil, pad in P3B_AUG_ROWS:
        for level in P3B_AUG_LEVELS:
            c = p3b_case("P3b-aug", soil, pad, level, 4.0)
            c["pair_case"] = f"P3b_{soil}_{pad}_top_Fs4"
            out.append(c)
    return out


def p3b_level_argv(c: dict[str, Any]) -> list[str]:
    """``run_S9.py level`` arguments of a :func:`p3b_cases` / :func:`g6_cases` row (without the
    interpreter). A row with ``soil_patch`` adds ``--soil-patch LEG:SET --soil-patch-grid``; an S9SL
    row (:func:`s9sl_cases`) adds ``--floor-roll`` / ``--floor-pitch`` and ``--start-limit``."""
    out = ["level", "--soil", c["soil"], "--pad-variant", c["pad_variant"], "--level", c["level"],
           "--fs-kN", f"{c['fs_kN']:g}", "--grid", f"{c['grid_m']:g}", "--crawler-grid", f"{c['crawler_grid_m']:g}",
           "--settle-dashpot", "zrp", "--threads", str(SCM_THREADS_FIXED), "--duration", f"{P3B_DURATION_S:g}",
           "--pressure-grade", P3B_PRESSURE_GRADE, "--imu-grade", P3B_IMU_GRADE, "--seed", str(P3B_SEED),
           "--approved"]
    if "duration_s" in c:  # G6 rows only (the P3b rows keep the fixed P3B_DURATION_S, D-2)
        out[out.index("--duration") + 1] = f"{c['duration_s']:g}"
    sp = c.get("soil_patch")
    if sp is not None:
        out[-1:-1] = ["--soil-patch", f"{sp['leg']}:{sp['set']}", "--soil-patch-grid", f"{sp['grid_m']:g}"]
    # G6P rows only (2026-10-28): the P-S8-29 counterfactual and a case note recorded in result.json args
    if c.get("twist_relax", TWIST_RELAX_PRESET) != TWIST_RELAX_PRESET:
        out[-1:-1] = ["--twist-relax", c["twist_relax"]]
    if c.get("note"):
        out[-1:-1] = ["--note", c["note"]]
    # S9SL rows only (study ①, 2026-10-28): floor slope and the start-limit mode
    if "floor_deg" in c:
        roll, pitch = c["floor_deg"]
        out[-1:-1] = ["--floor-roll", f"{roll:g}", "--floor-pitch", f"{pitch:g}"]
    if c.get("start_limit", START_LIMIT_PRESET) != START_LIMIT_PRESET:
        out[-1:-1] = ["--start-limit", c["start_limit"]]
    # MS1 rows only (Q-D, 2026-10-29): plant superstructure mass scale
    if float(c.get("mass_scale", 1.0)) != 1.0:
        out[-1:-1] = ["--mass-scale", f"{float(c['mass_scale']):g}"]
    return out


# --- G6 soil patch (one soft pad, cad G6 study 2026-10-27; acceptance after P-S8-29) ----------------

G6_US_PER_STEP_UPPER = {"J1": 7000.0, "J2": 7000.0, "G1": 5500.0, "S1": 5500.0}
"""Upper per-step cost [us] of a G1 base with a patch of this set, 4-parallel contended (ASSUMPTION: the G1
base 5.5 ms plus one pad on the patch grid; a 1 cm loaded pad costs about +55 % of its 2 cm value, SCM memory
2026-10-27; the split terrain itself showed no measurable overhead in the G6 probe). To be replaced by the
first run's ``us_per_step``."""


def g6_case(base: str, patch_set: str, leg: str, *, pad: str = "B", level: str = "top", fs: float = 4.0,
            group: str = "G6", duration_s: float = P3B_DURATION_S, twist_relax: str | None = None,
            note: str | None = None, est_s: float | None = None) -> dict[str, Any]:
    """One G6 closed-loop case: the P3b case of ``base`` with the pad ``leg`` on a ``patch_set`` soil patch
    (``soil_patch`` = {leg, set, grid_m}; patch grid = the P3b pad grid of that set); ``duration_s`` = the
    closed-loop time after the 8 s settle (``level --duration``). G6P only: ``twist_relax`` (``off`` = P-S8-29
    counterfactual, case name suffix :data:`TWIST_RELAX_OFF_SUFFIX`), ``note`` (``level --note``, kept in
    result.json args and batch.json) and a measured ``est_s`` instead of the per-step upper bound."""
    sp = {"leg": leg, "set": patch_set, "grid_m": P3B_PAD_GRID_M[patch_set]}
    us = max(G6_US_PER_STEP_UPPER[patch_set], P3B_US_PER_STEP_UPPER[base])
    sim_s = CRAWLER_SETTLE_S + float(duration_s)
    name = f"G6_{base}_{pad}_{level}_Fs{fs:g}_sp{patch_set}{leg}"
    out = {"group": group, "case": name, "soil": base,
           "pad": pad, "pad_variant": P3B_PAD[pad], "level": level, "fs_kN": fs, "grid_m": P3B_PAD_GRID_M[base],
           "crawler_grid_m": P3B_CRAWLER_GRID_M, "est_s": round(sim_s / 1.0e-4 * us * 1e-6, -2),
           "soil_patch": sp, "duration_s": float(duration_s), "sim_s": sim_s}
    if twist_relax is not None:
        if twist_relax not in TWIST_RELAX_MODES:
            raise ValueError(f"twist_relax must be one of {TWIST_RELAX_MODES}, got {twist_relax!r}")
        out["twist_relax"] = twist_relax
        if twist_relax == TWIST_RELAX_OFF:
            out["case"] = name + TWIST_RELAX_OFF_SUFFIX
    if note:
        out["note"] = note
    if est_s is not None:
        out["est_s"] = float(est_s)
    return out


G6_DURATION_S = {"J1RR": 160.0, "J1FL": 200.0, "G1RR": 120.0}
"""Closed-loop time per G6 case (user decision 2026-10-28 with P-S8-29 V2b: J1@RR 160 s, J1@FL 200 s; the G1
control keeps the P3b 120 s)."""


def g6_cases() -> list[dict[str, Any]]:
    """G6 closed-loop set (user decisions 2026-10-27 / 28; acceptance after P-S8-29, not run yet): G1 base,
    pad B, top, F_s 4 kN; J1 patch under RR (160 s) and under FL (200 s), and the layout control (G1 patch
    under RR, 120 s = four G1 pads on the same triple layout; the layout change alone moves bits)."""
    return [g6_case("G1", "J1", "RR", duration_s=G6_DURATION_S["J1RR"]),
            g6_case("G1", "J1", "FL", duration_s=G6_DURATION_S["J1FL"]),
            g6_case("G1", "G1", "RR", group="G6-ref", duration_s=G6_DURATION_S["G1RR"])]


# --- G6P: paper evidence set (user decision 2026-10-28) ------------------------------------------------

TWIST_RELAX_PRESET = "preset"
TWIST_RELAX_OFF = "off"
TWIST_RELAX_MODES = (TWIST_RELAX_PRESET, TWIST_RELAX_OFF)
"""``level --twist-relax``: ``preset`` = the R8 preset P-S8-29 relaxed twist completion as it is
(``C2Config().with_10hz_d1()``), ``off`` = ``twist_completion_relax.enable`` False only (counterfactual
comparison: DONE needs ``|D| < done_twist_N`` again; READY expected late or none)."""
TWIST_RELAX_OFF_SUFFIX = "_noTR"
S1_MODEL_LIMIT_NOTE = ("model-limit stress case: S1 patch under a front pad, p/q_ult about 9.5 = outside the "
                       "Bekker validity range (dynamics_model.md rev. 44); SCM keeps sinking without a bearing "
                       "failure, so a pass or a fail is not a physical prediction")
G6P_EST_S = {"J1RR_noTR": 10800.0, "J1RR": 6950.0, "J1FL": 8540.0, "J2RR": 9500.0, "J2FL": 9500.0, "S1FL": 6600.0}
"""Wall estimates [s] of the G6P rows, P-core 4-parallel contended: the G6 batch of 2026-10-28
(batch_G6_20261028_075108: settle about 280 s, J1 loop 41.3-41.7 s per simulated s, G1 39.0) measured;
J2 +10 % (deeper sinkage) and J1RR_noTR (240 s, deeper sinkage) are ASSUMPTIONS; S1FL = the G1 rate."""


def g6p_cases() -> list[dict[str, Any]]:
    """G6P closed-loop set (paper evidence, user decision 2026-10-28): G1 base, pad B, top, F_s 4 kN, the G6
    settings; current preset (P-S8-29 rise tolerance 0.6 kN, U-S8-80) unless noted. J1@RR with the P-S8-29
    relaxation off 240 s (counterfactual), J1@RR 160 s, J1@FL 200 s, J2@RR 200 s, J2@FL 200 s, S1@FL 160 s
    (patch grid 0.02 m, model-limit stress case :data:`S1_MODEL_LIMIT_NOTE`)."""
    return [g6_case("G1", "J1", "RR", group="G6P", duration_s=240.0, twist_relax=TWIST_RELAX_OFF,
                    note="P-S8-29 counterfactual: twist_completion_relax.enable False (preset otherwise)",
                    est_s=G6P_EST_S["J1RR_noTR"]),
            g6_case("G1", "J1", "RR", group="G6P", duration_s=160.0, est_s=G6P_EST_S["J1RR"]),
            g6_case("G1", "J1", "FL", group="G6P", duration_s=200.0, est_s=G6P_EST_S["J1FL"]),
            g6_case("G1", "J2", "RR", group="G6P", duration_s=200.0, est_s=G6P_EST_S["J2RR"]),
            g6_case("G1", "J2", "FL", group="G6P", duration_s=200.0, est_s=G6P_EST_S["J2FL"]),
            g6_case("G1", "S1", "FL", group="G6P", duration_s=160.0, note=S1_MODEL_LIMIT_NOTE,
                    est_s=G6P_EST_S["S1FL"])]


def apply_twist_relax(config: Any, mode: str) -> tuple[Any, dict[str, Any]]:
    """``level --twist-relax``: the C2 config with the P-S8-29 relaxation as given by ``mode`` and its record
    (mode, overrides, the resulting ``twist_completion_relax`` settings)."""
    from dataclasses import asdict, replace

    if mode not in TWIST_RELAX_MODES:
        raise ValueError(f"--twist-relax must be one of {TWIST_RELAX_MODES}, got {mode!r}")
    overrides: dict[str, Any] = {}
    if mode == TWIST_RELAX_OFF:
        config = replace(config, twist_completion_relax=replace(config.twist_completion_relax, enable=False))
        overrides["twist_completion_relax.enable"] = False
    return config, {"mode": mode, "overrides": overrides,
                    "settings": asdict(config.twist_completion_relax)}


# --- study ①: soft soil x floor slope (control design 2026-10-28) ---------------------------------------

START_LIMIT_PRESET = "preset"
START_LIMIT_VERIFICATION = "verification"
START_LIMIT_VERIFICATION_MAP = "verification_map"
START_LIMIT_RECORD_ONLY = "record_only"
START_LIMIT_MODES = (START_LIMIT_PRESET, START_LIMIT_VERIFICATION, START_LIMIT_VERIFICATION_MAP,
                     START_LIMIT_RECORD_ONLY)
"""``level --start-limit``: ``preset`` = the R8 preset start / target acceptance as it is (operating mode: D8 and
relative diamonds 4.4 / 3.2 deg on the crawler IMU attitude, reject); ``verification`` = the run_S8C / run_S7C L2b
meaning (``target.slope_limit_mode = verification``: D8 / relative diamonds 5.5 / 3.5 deg, usage tolerance 0.01,
the simulation check range of control spec 2.3), nothing else changed (acceptance reject, identity crawler settle
map = the measured crawler attitude, as the L2b rigid-crawler runs of run_S8C). ``verification_map`` = verification
plus the spec 13.1 X5 crawler settle map of the auger level (``CrawlerSettleMap.for_level``, the verification-mode
floor estimate run_S6C L1-R uses): on SCM the crawler settles steeper than the floor (smoke 2026-10-28: G1 B floor
3.2 deg -> crawler 3.54 deg, ``verification`` rejects with REJ_SLOPE_D8), the map takes theta_0 and the extra tilt
off before A1 / A4. The map coefficients are the L1-R Chrono fit (ASSUMPTION for SCM). ``record_only`` (control-expert
decision 2026-10-28, the S9SL rows) = ``target.acceptance = off`` only, as the harness
(``c2py_r8d1_closed_loop.preset_config``: ``TargetAcceptance.OFF``, operating mode, identity settle map): CHECK accepts
the level target whatever the crawler attitude (``target.check_target`` returns ACCEPTED with ``off``) and the A5
stroke check of a READY target change is skipped; the start rule is only recorded (SL-2 ``R_c``, FLAG > 1). The other
target fields (operating mode, identity map, CHECK time / zero calibration) and every LEVEL-path setting (soil response
clearance estimate S-3 / P-S8-28, REANCHOR with its anchor pitch = theta_crawler) stay the preset: none of them reads
``config.target`` (c2.py: the target settings are read only by CHECK, the A1 .. A5 checks, the reference ramp, the
gyro-bias window and the X9 shadow floor estimate)."""


def apply_start_limit(config: Any, mode: str, level: str = "top") -> tuple[Any, dict[str, Any]]:
    """``level --start-limit``: the C2 config with the start / target slope limits of ``mode`` and its record
    (mode, overrides, the resulting mode, diamond half-spans [deg], settle map). ``level`` = auger level of the
    settle map (``verification_map`` only)."""
    from dataclasses import replace

    from outrigger_sim.control.target import CrawlerSettleMap, SlopeLimitMode, TargetAcceptance

    if mode not in START_LIMIT_MODES:
        raise ValueError(f"--start-limit must be one of {START_LIMIT_MODES}, got {mode!r}")
    overrides: dict[str, Any] = {}
    if mode == START_LIMIT_RECORD_ONLY:
        config = replace(config, target=replace(config.target, acceptance=TargetAcceptance.OFF))
        overrides["target.acceptance"] = str(TargetAcceptance.OFF)
    if mode in (START_LIMIT_VERIFICATION, START_LIMIT_VERIFICATION_MAP):
        smap = CrawlerSettleMap.for_level(level) if mode == START_LIMIT_VERIFICATION_MAP else None
        config = replace(config, target=replace(config.target, slope_limit_mode=SlopeLimitMode.VERIFICATION,
                                                crawler_settle_map=smap))
        overrides["target.slope_limit_mode"] = str(SlopeLimitMode.VERIFICATION)
        if smap is not None:
            overrides["target.crawler_settle_map"] = f"CrawlerSettleMap.for_level({level!r})"
    lim = config.target.limits
    return config, {"mode": mode, "overrides": overrides,
                    "slope_limit_mode": str(config.target.slope_limit_mode),
                    "acceptance": str(config.target.acceptance),
                    "relative_span_deg": [math.degrees(lim.relative_roll_span_rad),
                                          math.degrees(lim.relative_pitch_span_rad)],
                    "absolute_span_deg": [math.degrees(lim.absolute_roll_span_rad),
                                          math.degrees(lim.absolute_pitch_span_rad)],
                    "usage_tolerance": lim.usage_tolerance,
                    "crawler_settle_map": config.target.settle_map.to_meta(),
                    "rule": "verification = run_S8C / run_S7C L2b slope_limit_mode (spec 2.3), settle map identity; "
                            "verification_map = verification + CrawlerSettleMap.for_level (spec 13.1 X5); "
                            "record_only = target.acceptance off only (harness preset_config), start rule recorded"}


OPERATING_START_SPAN_DEG = (4.4, 3.2)
"""SL-2 (study ①): operating start rule |phi_c| / 4.4 + |theta_c| / 3.2 <= 1 on the crawler IMU attitude (CHECK end)."""


def start_condition_record(target_meta: dict[str, Any] | None, events: list[tuple[float, str]],
                           t_loop_start_s: float) -> dict[str, Any]:
    """SL-2 record: the CHECK-end crawler attitude ``(phi_c, theta_c)`` of the C2 target meta [deg], the operating
    usage ``R_c = |phi_c| / 4.4 + |theta_c| / 3.2`` (FLAG ``operating_rule_rejects`` when > 1), the slope limit mode
    of the run and the target rejection events (``REJ_*``). Record only."""
    tm = target_meta or {}
    ca = tm.get("crawler_attitude_rad")
    rej = [[float(t) - t_loop_start_s, n] for t, n in events if str(n).startswith("REJ_")]
    out: dict[str, Any] = {"slope_limit_mode": tm.get("slope_limit_mode"), "rejections_rel_s": rej,
                           "crawler_attitude_deg": None, "R_c_operating": None, "operating_rule_rejects": None,
                           "floor_estimate_deg": None if tm.get("floor_estimate_rad") is None
                           else [math.degrees(float(a)) for a in tm["floor_estimate_rad"]],
                           "rule": "SL-2 (study ①): R_c = |phi_c| / 4.4 + |theta_c| / 3.2 on the CHECK-end crawler "
                                   "IMU attitude; > 1 = FLAG 'operating rule rejects'; record only"}
    if ca is not None:
        r, p = (math.degrees(float(a)) for a in ca)
        rc = abs(r) / OPERATING_START_SPAN_DEG[0] + abs(p) / OPERATING_START_SPAN_DEG[1]
        out.update(crawler_attitude_deg=[r, p], R_c_operating=rc, operating_rule_rejects=bool(rc > 1.0))
    return out


S9SL_DURATION_S = 160.0
"""Closed-loop time of the study ① Chrono rows (design: 160 s)."""
S9SL_WALL_S_PER_SIM_S = {"G1": 51.0, "S1": 51.0, "J1": 87.0, "J2": 87.0}
"""Wall per simulated second, P-core 4-parallel contended (ASSUMPTION: the P3b contended means, G1 5.1 / J1 8.7
ms/step at dt 1e-4 s, :data:`P3B_US_PER_STEP_UPPER` note; the design's 4-parallel 4.1 h)."""


def _deg_tag(v: float) -> str:
    return f"{v:g}".replace("-", "m").replace(".", "p")


S9SL_START_LIMIT = START_LIMIT_RECORD_ONLY
"""Start-limit mode of the S9SL rows (control-expert decision 2026-10-28): ``record_only`` = target acceptance off
with the identity settle map, the harness control path; C-1 (Chrono settle smoke R_c 1.107, plain ``verification``
rejected it with REJ_SLOPE_D8 at crawler 3.54 deg) and C-4 must not stop at CHECK; R_c is the SL-2 record only.
``verification_map`` stays available but is not used here."""


def s9sl_case(cid: str, soil: str, pad: str, roll_deg: float, pitch_deg: float, *, purpose: str,
              duration_s: float = S9SL_DURATION_S, confirmed: bool = True) -> dict[str, Any]:
    """One study ① Chrono row: the P3b settings (top, F_s 4 kN, zrp, threads 4, pressure normal, IMU ideal, seed
    20261026, R8 preset incl. REANCHOR on) on a floor of (roll, pitch) [deg] (floor tilted, gravity vertical, as L2b
    run_S7C), closed loop ``duration_s``, ``--start-limit`` :data:`S9SL_START_LIMIT`."""
    c = p3b_case("S9SL", soil, pad, "top", 4.0)
    sim_s = CRAWLER_SETTLE_S + float(duration_s)
    c.update(case=f"S9SL_{cid.replace('-', '')}_{soil}_{pad}_top_Fs4_r{_deg_tag(roll_deg)}_p{_deg_tag(pitch_deg)}",
             cid=cid, floor_deg=(float(roll_deg), float(pitch_deg)), start_limit=S9SL_START_LIMIT,
             duration_s=float(duration_s), sim_s=sim_s, est_s=round(sim_s * S9SL_WALL_S_PER_SIM_S[soil], -2),
             purpose=purpose, confirmed=bool(confirmed))
    return c


def s9sl_cases(include_draft: bool = False) -> list[dict[str, Any]]:
    """Study ① Chrono rows (design 2026-10-28, control-expert confirmation of C-3 / C-4 the same day): C-1 G1 B
    (0, +3.2) soft-soil REANCHOR (RA-1 .. RA-6), 160 s; C-2 J1 A (+4.4, 0) crawler roll settle asymmetry, slope LOC /
    S-3, 160 s; C-3 J1 B (+3.3, 0) inside the operating diamond, false LOC -> re-contact check, 160 s; C-4 J1 A
    (0, +3.2) REANCHOR on (Chrono preset default), 200 s. ``include_draft`` is kept for callers (no drafts left)."""
    return [s9sl_case("C-1", "G1", "B", 0.0, 3.2, purpose="soft-soil REANCHOR (RA-1 .. RA-6)"),
            s9sl_case("C-2", "J1", "A", 4.4, 0.0, purpose="crawler roll settle asymmetry, slope LOC / S-3"),
            s9sl_case("C-3", "J1", "B", 3.3, 0.0, purpose="roll inside the operating diamond: false LOC -> re-contact"),
            s9sl_case("C-4", "J1", "A", 0.0, 3.2, duration_s=200.0, purpose="J1 REANCHOR (preset on), 200 s")]


MASS_SCALE_NOTE = ("spec 422 / decision Q-D (2026-10-29): Chrono plant superstructure body (rigid, crawler included) "
                   "mass and inertia about its COG x mass_scale, COG kept (= s9_soil_closed_loop.scale_plant_mass); leg "
                   "rods / pads unchanged; controller unchanged (YAML nominal mass, W_ref, D1'' mass); the 8 s settle "
                   "runs on the scaled body in Chrono (no A1-m settle approximation); judgement weight p3b.weight_N "
                   "= plant weight (scaled), P3-7 loaded window 0.01 W_plant = 0.01 mass_scale W_ref (spec 422.6)")
MS1_EST_S = 12500.0
"""MS1 wall estimate [s], one E-pool case (ASSUMPTION): J1 B / G1 B cost ratio on the P cores 8.69 / 5.10 ms/step
(P3B_US_PER_STEP_UPPER note) x E-pool G1 B 5.08 ms/step (S9SL C-1, batch_S9SL_20261029_144406, E 2 slots) = 8.7
ms/step x 128 s / 1e-4 = 11,100 s, + about 12 % for the deeper rear-pad sinkage at x1.1 (harness 422.5: about 200
against 90 mm). P-core reference: P3b_J1_B_top_Fs4 7,058 s (5.51 ms/step, batch_P3b_20261027_174330, P 2 slots)."""


def ms1_cases() -> list[dict[str, Any]]:
    """MS1 (decision Q-D, 2026-10-29, spec 422.5): ``P3b_J1_B_top_Fs4`` (P3b settings: J1, pad B, top, F_s 4 kN,
    120 s, pressure normal / IMU ideal / seed 20261026) with the plant superstructure mass x 1.1
    (``level --mass-scale 1.1``, :func:`apply_mass_scale`). ``pair_case`` = the x1.0 P3b run."""
    c = p3b_case("MS1", "J1", "B", "top", 4.0)
    c.update(case=c["case"] + "_m1p1", mass_scale=1.1, pair_case="P3b_J1_B_top_Fs4", est_s=MS1_EST_S,
             note="pair P3b_J1_B_top_Fs4; plant superstructure mass x1.1 (Q-D, harness H6 422.5 J1 B top x1.1 fail)")
    return [c]


def apply_mass_scale(model: Any, params: Any, mass_scale: float) -> dict[str, Any]:
    """``level --mass-scale``: superstructure body mass / inertia (about the COG, body axes) x ``mass_scale`` on the
    built Chrono model, COG position unchanged (:data:`MASS_SCALE_NOTE`). 1.0 leaves the body untouched (bit for
    bit). Returns the record block (values read back from the body)."""
    s = float(mass_scale)
    if not (s > 0.0 and math.isfinite(s)):
        raise ValueError(f"mass_scale must be a finite value > 0, got {mass_scale!r}")
    props = params.superstructure.mass_properties
    body = model.superstructure
    if s != 1.0:
        import pychrono as ch  # noqa: PLC0415

        i = np.asarray(props.inertia_kg_m2, dtype=float) * s
        body.SetMass(float(props.mass_kg) * s)
        body.SetInertiaXX(ch.ChVector3d(i[0, 0], i[1, 1], i[2, 2]))
        body.SetInertiaXY(ch.ChVector3d(i[0, 1], i[0, 2], i[1, 2]))
    xx, xy = body.GetInertiaXX(), body.GetInertiaXY()
    return {"mass_scale": s, "note": MASS_SCALE_NOTE,
            "yaml_superstructure_mass_kg": float(props.mass_kg),
            "plant_superstructure_mass_kg": float(body.GetMass()),
            "plant_superstructure_inertia_cog_body_kg_m2": [[float(xx.x), float(xy.x), float(xy.y)],
                                                             [float(xy.x), float(xx.y), float(xy.z)],
                                                             [float(xy.y), float(xy.z), float(xx.z)]],
            "plant_weight_N": model_weight_N(params, s),
            "plant_superstructure_weight_N": float(body.GetMass()) * G,
            "yaml_weight_N": model_weight_N(params)}


def mass_scale_record(mass_block: dict[str, Any], c2: Any, ctl_meta: dict[str, Any] | None) -> dict[str, Any]:
    """Result block ``mass_scale``: :func:`apply_mass_scale` values + the controller reference weight W_ref (C2,
    unchanged by the scale), the plant / W_ref ratio of the superstructure and the WARN_WEIGHT_MISMATCH events."""
    soil = (ctl_meta or {}).get("soil") or {}
    w_ref = soil.get("W_ref_N")
    if w_ref is None and hasattr(c2, "_reference_weight_N"):
        w_ref = float(c2._reference_weight_N())
    out = dict(mass_block)
    out["controller_weight_ref_N"] = None if w_ref is None else float(w_ref)
    out["plant_over_W_ref"] = (None if not w_ref else out["plant_superstructure_weight_N"] / float(w_ref))
    out["weight_mismatch_events"] = [[float(e.t_s), str(e.name)] for e in getattr(c2, "events", ())
                                     if str(e.name).startswith("WARN_WEIGHT_MISMATCH")]
    return out


def judgement_weights(mass_scale: float, weight_N: float | None, w_ref_N: float | None,
                      f_min_N: float | None) -> dict[str, Any]:
    """Which weight each P3 rule uses (spec 422.6, control 2026-10-29); result and rejudge meta (record only)."""
    s = float(mass_scale)
    w_plant = None if w_ref_N is None else s * float(w_ref_N)
    return {"mass_scale": s,
            "weight_N": weight_N,
            "W_ref_N": w_ref_N,
            "W_plant_N": w_plant,
            "P3-7_loaded_threshold_N": None if w_plant is None else P37_LOADED_FRACTION * w_plant,
            "F_min_N": f_min_N,
            "F_min_x_mass_scale_record_N": None if f_min_N is None else s * float(f_min_N),
            "basis": {"weight_N": "p3b.weight_N = plant weight (superstructure x mass_scale + leg moving parts) x g: "
                                  "departure / re-contact 0.01 W rules, settle normal checks",
                      "W_plant_N": "mass_scale x W_ref (plant superstructure): P3-7 loaded-window threshold (422.6)",
                      "W_ref_N": "C2 meta soil.W_ref_N (YAML nominal, controller): W ratio, WARN_WEIGHT_MISMATCH, S-1 "
                                 "plausibility / reconstruction, P3-7 0.05 W record bucket",
                      "F_min_N": "P3-3 uses the YAML F_min; F_min x mass_scale is a record only"}}


CRAWLER_GAP_STEP_M = 0.1
"""Grid of the crawler bottom sample points (the rut-reference grid of ``S9Model.mark_rut_reference``)."""


def crawler_gap_points_body_m(params: Any, step_m: float = CRAWLER_GAP_STEP_M) -> tuple[np.ndarray, list[str]]:
    """Every crawler contact-shape sample point in body coordinates (m) and its label: the block-bottom grid of
    both tracks over the flat part and both ramps (``mark_rut_reference`` points, NOT filtered by settle contact)
    plus the 8 corners of each of the 6 envelope boxes (``crawler_box_specs`` / ``box_triangles``)."""
    from outrigger_sim.chrono import scm_model as sm

    z_block = float(params.ground.crawler_bottom_z_m) + sm.BLOCK_BOTTOM_ABOVE_CRAWLER_BOTTOM_M
    ys = np.arange(sm.TRACK_Y_RANGE_M[0] + 0.02, sm.TRACK_Y_RANGE_M[1] - 0.02 + 1e-9, step_m)
    xs = np.arange(sm.REAR_RAMP_X_M[0] + 0.02, sm.FRONT_RAMP_X_M[1] - 0.02 + 1e-9, step_m)
    pts, labels = [], []
    for sy, side in ((1.0, "L"), (-1.0, "R")):
        for x in xs:
            if x > sm.FRONT_RAMP_X_M[0]:
                zb = z_block + sm.FRONT_RAMP_SLOPE * (x - sm.FRONT_RAMP_X_M[0])
            elif x < sm.REAR_RAMP_X_M[1]:
                zb = z_block + sm.REAR_RAMP_SLOPE * (sm.REAR_RAMP_X_M[1] - x)
            else:
                zb = z_block
            for y in ys:
                pts.append([x, sy * y, zb])
                labels.append(f"grid_{side}")
    for spec in sm.crawler_box_specs(params):
        verts, _faces = sm.box_triangles(spec["centre"], spec["angle_y_rad"], spec["size"])
        for k, v in enumerate(verts):
            pts.append(list(v))
            labels.append(f"{spec['name']}:v{k}")
    return np.asarray(pts, float), labels


class CrawlerGapProbe:
    """Minimum gap between every crawler contact-shape point (:func:`crawler_gap_points_body_m`) and the crawler
    SCM surface, along the SCM plane normal (control-expert 2026-10-28, the rev. 70 G8 rule 'all crawler nodes vs the
    floor'; the settle-contact rut clearance ``rut_clearance_m`` misses the uphill end shoe on a slope). Surface
    under a point = plane level - node sinkage of the nearest SCM node (``GetNodeInfo(p).sinkage``, the node of the
    point projected along the plane normal; untouched nodes read 0 = the plane). Read-only queries."""

    def __init__(self, model: Any) -> None:
        self.model = model
        pts, self.labels = crawler_gap_points_body_m(model.params)
        self.points_local_m = pts - np.asarray(model.sup_com_body_m, float)  # COG frame (as the rut points)

    def __call__(self) -> tuple[float, str, float, float]:
        """(minimum gap over all points [m], its point label, minimum over the bottom-grid points only [m], nearby
        sinkage of the all-point minimum [m]). The box corners lie exactly on the track edges, where the nearest SCM
        node may be outside the rut (undisturbed, sinkage 0): a settled corner then reads about minus the crawler
        sinkage (flat G1 settle: -3.9 mm). The grid points are 20 mm inside the edges (crawler grid 40 mm), so their
        nearest node is under the track. Nearby sinkage = the largest node sinkage at the minimum point and at
        +-1 crawler grid step along the plane x / y axes (5 nodes), for the judge's corner-bias FLAG."""
        from outrigger_sim.chrono.scm_model import chvec

        m = self.model
        n = np.asarray(m.normal_world, float)
        plane = float(np.asarray(m.plane_point_world_m, float) @ n)
        sup, ter = m.superstructure, m.crawler_terrain
        best, arg, best_grid, w_best = math.inf, "", math.inf, None
        for p, lab in zip(self.points_local_m, self.labels, strict=True):
            w = sup.TransformPointLocalToParent(chvec(p))
            gap = (w.x * n[0] + w.y * n[1] + w.z * n[2]) - (plane - float(ter.GetNodeInfo(w).sinkage))
            if gap < best:
                best, arg, w_best = gap, lab, np.array([w.x, w.y, w.z])
            if lab.startswith("grid_") and gap < best_grid:
                best_grid = gap
        near = math.nan
        if w_best is not None:
            rot = np.asarray(getattr(m, "plane_rot", np.eye(3)), float)
            h = float(getattr(m, "crawler_grid_m", 0.04))
            offs = [np.zeros(3)] + [s * h * rot[:, k] for k in (0, 1) for s in (1.0, -1.0)]
            near = max(float(ter.GetNodeInfo(chvec(w_best + o)).sinkage) for o in offs)
        return float(best), arg, float(best_grid), float(near)


CRAWLER_GAP_CORNER_FLAG_EXTRA_M = 0.005
"""ASSUMPTION (control-expert 2026-10-28): the all-point gap may sit below the grid gap by the nearby crawler sinkage
(corner nearest-node bias) plus this before the corner FLAG."""


def first_ready_time(phases: list[tuple[float, str]]) -> float | None:
    """Time of the first READY phase entry (absolute [s]) or None."""
    return next((float(t) for t, ph in phases if "ready" in str(ph).lower()), None)


def crawler_gap_summary(soil_rows: list[dict[str, Any]], t_loc_s: float | None, t_loop_start_s: float,
                        t_first_ready_s: float | None = None) -> dict:
    """Record of the 10 Hz ``crawler_gap_min_m`` (:class:`CrawlerGapProbe`): value at the loop start, at / after the
    C2 LOC and at the end, the minimum after the LOC and its point label [m, s relative to the loop start]."""
    rows = [r for r in soil_rows if r.get("crawler_gap_min_m") is not None]
    out: dict[str, Any] = {"rule": "min over all crawler contact-shape points (bottom grid 0.1 m incl. ramps + the 48 "
                                   "envelope-box corners) of (point - SCM surface) . plane normal; 10 Hz; record",
                           "n_rows": len(rows)}
    if not rows:
        return out
    g = np.array([r["crawler_gap_min_m"] for r in rows], float)
    gg = np.array([np.nan if r.get("crawler_gap_grid_min_m") is None else r["crawler_gap_grid_min_m"] for r in rows],
                  float)
    t = np.array([r["t_s"] for r in rows], float)
    out.update(start_m=float(g[0]), end_m=float(g[-1]), end_point=rows[-1].get("crawler_gap_point"),
               grid_start_m=float(gg[0]), grid_end_m=float(gg[-1]),
               note="all-point min includes the 48 box corners on the track edges (nearest-node bias about minus "
                    "the crawler sinkage while settled); grid_* = bottom-grid points only (20 mm inside the edges)")
    if t_loc_s is not None:
        m = t >= float(t_loc_s) - 1e-9
        if m.any():
            idx = np.flatnonzero(m)
            k = int(idx[np.argmin(g[m])])
            out.update(at_loc_m=float(g[idx[0]]), min_after_loc_m=float(g[k]),
                       min_after_loc_t_rel_s=float(t[k]) - t_loop_start_s,
                       min_after_loc_point=rows[k].get("crawler_gap_point"),
                       grid_at_loc_m=float(gg[idx[0]]), grid_min_after_loc_m=float(np.nanmin(gg[m]))
                       if np.isfinite(gg[m]).any() else None)
    # P3-5 / SL-3 (control-expert 2026-10-28): judged gap = grid minimum after the first READY, the all-point minimum
    # alongside; FLAG when all < grid - (nearby sinkage + CRAWLER_GAP_CORNER_FLAG_EXTRA_M) (judged by the judge)
    out["after_first_ready"] = None
    if t_first_ready_s is not None:
        m = t >= float(t_first_ready_s) - 1e-9
        if m.any() and np.isfinite(gg[m]).any():
            idx = np.flatnonzero(m)
            kg = int(idx[np.nanargmin(gg[m])])
            ka = int(idx[np.argmin(g[m])])
            near = rows[ka].get("crawler_gap_point_near_sinkage_m")
            near_v = 0.0 if near is None or not math.isfinite(float(near)) else float(near)
            margin = near_v + CRAWLER_GAP_CORNER_FLAG_EXTRA_M
            out["after_first_ready"] = {
                "t_first_ready_rel_s": float(t_first_ready_s) - t_loop_start_s,
                "grid_min_m": float(gg[kg]), "grid_min_t_rel_s": float(t[kg]) - t_loop_start_s,
                "all_min_m": float(g[ka]), "all_min_t_rel_s": float(t[ka]) - t_loop_start_s,
                "all_min_point": rows[ka].get("crawler_gap_point"), "all_min_near_sinkage_m": near,
                "corner_flag_margin_m": margin,
                "corner_flag": bool(float(g[ka]) < float(gg[kg]) - margin),
                "rule": "judged gap (P3-5 / SL-3) = grid_min_m; all_min_m alongside; corner_flag = all_min < grid_min - "
                        "(nearby sinkage of the all-min point + 5 mm, ASSUMPTION); record, judged by the judge"}
    return out


def _record_or_error(fn) -> Any:
    """``fn()`` or ``{"error": "<type>: <message>"}`` (record blocks added after a long run must not lose it)."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 - record only
        return {"error": f"{type(e).__name__}: {e}"}


REANCHOR_EVENT_PREFIX = "reanchor_"
REANCHOR_RA2_MARGIN_N = 5000.0
"""RA-2 (study ①): true minimum F_cyl of all four legs during REANCHOR >= F_min + 5 kN."""
REANCHOR_RA3_ATTITUDE_DEG = 0.2
"""RA-3: end attitude after a REANCHOR <= 0.2 deg (each axis, last 1 s mean of the run)."""
REANCHOR_RA1_THETA_MIN_DEG = 2.5


def reanchor_probe(c2: Any) -> tuple[str | None, int | None]:
    """(REANCHOR sub-stage, stair step index) of the controller now, (None, None) outside REANCHOR or when the
    private members are not there (read-only; ``C2Controller._state.reanchor``)."""
    try:
        if "reanchor" not in str(getattr(c2, "phase", "")).lower():
            return None, None
        run = c2._state.reanchor
        if run is None:
            return None, None
        st = run.stage
        return str(getattr(st, "value", st)), int(run.step)
    except Exception:  # noqa: BLE001 - record only
        return None, None


def _pad_utilisation(row: dict[str, Any], normal: np.ndarray, limit_fn) -> list[float]:
    """|T_plane| / limit per pad of one 10 Hz ``s9_rows`` row (NaN without a limit or a bushing)."""
    ft = row.get("pad_tangential_N")
    if ft is None or limit_fn is None:
        return [math.nan] * 4
    ft = np.asarray(ft, float).reshape(4, 3)
    ft = ft - np.outer(ft @ normal, normal)
    lim = np.asarray(limit_fn(np.asarray(row["scm_pad_normal_N"], float)), float)
    return [float(np.linalg.norm(ft[k]) / lim[k]) if lim[k] > 0.0 else math.nan for k in range(4)]


def reanchor_records(series: dict[str, np.ndarray], soil_rows: list[dict[str, Any]],
                     events: list[tuple[float, str]], phases: list[tuple[float, str]],
                     reanchor_meta: dict[str, Any] | None, target_rad: list[float] | None, *,
                     F_min_N: float, normal_world: np.ndarray, limit_fn, t_loop_start_s: float) -> dict[str, Any]:
    """REANCHOR record of a ``level`` run (study ① RA-1 .. RA-6; records, RA-2 / RA-3 flags for the judgement).

    Events ``reanchor_*`` (relative to the loop start), outcomes, the relative pitch ``theta_anchor - theta_t``
    [deg] (> 0 = relative nose-down, RA-1 applies at >= 2.5 deg), and per stair step (and sub-stage) of the 10 Hz
    ``reanchor_stage`` / ``reanchor_step`` keys of ``s9_rows``: true minimum F_cyl per leg (1 ms ``F_cyl_N``),
    the pad bushing tangential utilisation ``|T| / (mu N + c A min(1, N / N_c))`` (10 Hz, in-plane part of the
    bushing force, ``GroundBushingCoulomb.tangential_limit_N`` on the SCM pad normal), the sinkage change per pad
    during the step (1 ms geometric sinkage, end - start) and the target leg."""
    names = [(float(t), str(n)) for t, n in events if str(n).startswith(REANCHOR_EVENT_PREFIX)]
    rm = reanchor_meta or {}
    tc, anchor = rm.get("theta_crawler_rad"), rm.get("anchor_pitch_rad")
    tp = None if not target_rad else float(target_rad[1])
    rel_deg = None if (tc is None or tp is None) else math.degrees(float(tc) - tp)
    settings = rm.get("settings") or {}
    targets = list(settings.get("targets") or ("RR", "RL"))
    out: dict[str, Any] = {
        "events_rel_s": [[t - t_loop_start_s, n] for t, n in names],
        "outcome": rm.get("outcome"), "outcomes": rm.get("outcomes"),
        "theta_crawler_deg": None if tc is None else math.degrees(float(tc)),
        "anchor_pitch_deg": None if anchor is None else math.degrees(float(anchor)),
        "target_pitch_deg": None if tp is None else math.degrees(tp),
        "relative_pitch_nose_down_deg": rel_deg,
        "started": any(n == "reanchor_started" for _t, n in names),
        "skip_reasons": [n.split(":", 1)[1] for _t, n in names if n.startswith("reanchor_skipped:")],
        "stop_readings_N": rm.get("stop_readings_N"), "stop_force_N": rm.get("stop_force_N"),
        "F_min_N": F_min_N,
        "rule": "study ① RA-1 .. RA-6 (control design 2026-10-28): RA-1 started only at relative nose-down >= 2.5 deg "
                "(skip reason recorded), RA-2 true min F_cyl (4 legs) during REANCHOR >= F_min + 5 kN, RA-3 end "
                "attitude <= 0.2 deg, RA-4 non-target sinkage increase, RA-5 pad utilisation, RA-6 stroke-cap aborts; "
                "times relative to the loop start"}
    out["RA-1_ok"] = (not out["started"]) or (rel_deg is not None and rel_deg >= REANCHOR_RA1_THETA_MIN_DEG - 1e-9)
    out["RA-6_stroke_cap_aborts"] = sum(1 for _t, n in names if n == "reanchor_aborted:stroke_cap")
    out["attitude_aborts"] = sum(1 for _t, n in names if n.startswith("reanchor_aborted:attitude"))
    if not out["started"]:
        return out
    t = np.asarray(series["t_s"], float)
    f = np.asarray(series["F_cyl_N"], float)
    sink = np.asarray(series["pad_sinkage_geometric_m"], float)
    t_all = [float(r["t_s"]) for r in soil_rows]
    segments: list[dict[str, Any]] = []
    for i, r in enumerate(soil_rows):
        if r.get("reanchor_stage") is None:
            continue
        key = (int(r["reanchor_step"]), str(r["reanchor_stage"]))
        if segments and segments[-1]["key"] == key and segments[-1]["i_last"] == i - 1:
            segments[-1]["i_last"] = i
            segments[-1]["rows"].append(r)
        else:
            segments.append({"key": key, "i_last": i, "rows": [r]})
    if not segments:  # started, but no 10 Hz row carries the stage (private members renamed)
        out["stages"] = None
        return out
    rows = [r for s in segments for r in s["rows"]]

    def window(t0: float, t1: float) -> np.ndarray:
        return (t >= t0) & (t < t1)

    def seg_values(t0: float, t1: float, seg_rows: list[dict[str, Any]], target: str | None) -> dict[str, Any]:
        m = window(t0, t1)
        util = np.array([_pad_utilisation(r, normal_world, limit_fn) for r in seg_rows], float).reshape(-1, 4)
        v: dict[str, Any] = {"t_rel_s": [t0 - t_loop_start_s, t1 - t_loop_start_s], "target_leg": target}
        if m.any():
            fmin = f[m].min(axis=0)
            v.update(min_F_cyl_N=dict(zip(LEGS, fmin.tolist())), min_F_cyl_all_N=float(fmin.min()),
                     min_F_cyl_margin_over_F_min_N=float(fmin.min() - F_min_N),
                     sinkage_change_mm=dict(zip(LEGS, ((sink[m][-1] - sink[m][0]) * 1e3).tolist())))
        v["pad_utilisation_max"] = dict(zip(LEGS, [float(np.nanmax(util[:, k])) if np.isfinite(util[:, k]).any()
                                                   else None for k in range(4)]))
        return v

    def seg_end(i_last: int) -> float:
        return t_all[i_last + 1] if i_last + 1 < len(t_all) else float(t[-1]) + 1e-9

    stages = []
    for s in segments:
        step, stage = s["key"]
        tgt = targets[step % len(targets)] if stage not in ("wait",) else None
        t0, t1 = float(s["rows"][0]["t_s"]), seg_end(s["i_last"])
        stages.append({"step": step, "stage": stage, **seg_values(t0, t1, s["rows"], tgt)})
    steps = []
    for step in sorted({s["key"][0] for s in segments}):
        segs = [s for s in segments if s["key"][0] == step and s["key"][1] != "wait"]
        if not segs:
            continue
        t0, t1 = float(segs[0]["rows"][0]["t_s"]), seg_end(segs[-1]["i_last"])
        steps.append({"step": step, "stages": [s["key"][1] for s in segs],
                      **seg_values(t0, t1, [r for s in segs for r in s["rows"]], targets[step % len(targets)])})
    t0 = float(rows[0]["t_s"])
    t1 = seg_end(segments[-1]["i_last"])
    whole = seg_values(t0, t1, rows, None)
    tgt_legs = {targets[s % len(targets)] for s in {x["key"][0] for x in segments}}
    others = [k for k in LEGS if k not in tgt_legs]
    sc = whole.get("sinkage_change_mm") or {}
    out.update(stages=stages, steps=steps, window=whole,
               **{"RA-2_min_F_cyl_all_N": whole.get("min_F_cyl_all_N"),
                  "RA-2_ok": None if whole.get("min_F_cyl_all_N") is None
                  else bool(whole["min_F_cyl_all_N"] >= F_min_N + REANCHOR_RA2_MARGIN_N),
                  "RA-4_non_target_sinkage_increase_mm": {k: sc.get(k) for k in others},
                  "RA-5_pad_utilisation_max": whole.get("pad_utilisation_max")})
    # RA-3: LEVEL entries after the REANCHOR window and the run's end attitude (last 1 s mean, each axis)
    out["relevels_after"] = sum(1 for tt, ph in phases if tt >= t1 and "level" in str(ph).lower()
                                and "ready" not in str(ph).lower())
    if t.size:
        m = t >= t[-1] - P3B_END_WINDOW_S - 1e-12
        rp = np.asarray(series["roll_pitch_deg"], float)[m].mean(axis=0)
        out["end_roll_pitch_deg"] = rp.tolist()
        out["RA-3_ok"] = bool(np.all(np.abs(rp) <= REANCHOR_RA3_ATTITUDE_DEG))
    return out


G6_OPEN_LOOP_LIFT_S = 28.0
G6_OPEN_LOOP_EST_S = {"G1": 1800.0, "J1": 3600.0}
"""Wall estimates of the open-loop rows = the P3a batch estimates of the patch set's own P3a (G1 B 1800 s,
J1 B 3600 s; s9_batch P3a)."""
G6_P3A_REFERENCE = "07_results/S9/batch_P3a_20261026_092653/P3a_G1_B"
"""G6-0a compares with this P3a run (same arguments, dual layout; params / scm_run fingerprints equal to the
tree of 2026-10-28)."""


def g6_open_loop_cases() -> list[dict[str, Any]]:
    """Open-loop G6 rows (dynamics / user 2026-10-28): G6-0a = the P3a G1 B lift with a G1 patch under RR
    (triple layout, physics unchanged; compared with :data:`G6_P3A_REFERENCE` by ``s9_g6_patch_compare.py``),
    G6-0b (optional) = the same lift with a J1 patch under RR."""
    out = []
    for name, key, grid, optional in (("G6-0a", "G1", 0.02, False), ("G6-0b", "J1", 0.01, True)):
        out.append({"group": name, "case": f"{name}_G1_B_lift_sp{key}RR", "optional": optional,
                    "soil_patch": {"leg": "RR", "set": key, "grid_m": grid}, "est_s": G6_OPEN_LOOP_EST_S[key],
                    "sim_s": CRAWLER_SETTLE_S + G6_OPEN_LOOP_LIFT_S})
    return out


def g6_machine_argv(c: dict[str, Any]) -> list[str]:
    """``run_S9.py machine`` arguments of a :func:`g6_open_loop_cases` row: the P3a G1 B arguments (s9_batch
    P3a) plus the soil patch."""
    sp = c["soil_patch"]
    return ["machine", "--soil", "G1", "--pad-variant", "dwg_rear250", "--grid", "0.02", "--crawler-grid", "0.04",
            "--settle-dashpot", "zrp", "--lift-s", f"{G6_OPEN_LOOP_LIFT_S:g}", "--level", "top", "--threads", "4",
            "--abort-on-limit", "--soil-patch", f"{sp['leg']}:{sp['set']}", "--soil-patch-grid", f"{sp['grid_m']:g}"]


def parse_soil_patch(text: str | None) -> tuple[str, str] | None:
    """``--soil-patch LEG:SET`` -> (leg, set); None / '' -> None."""
    if not text:
        return None
    leg, sep, key = text.partition(":")
    if not sep or leg not in ("FL", "FR", "RL", "RR") or key not in P3B_PAD_GRID_M:
        raise ValueError(f"--soil-patch must be LEG:SET with LEG in FL/FR/RL/RR and SET in "
                         f"{sorted(P3B_PAD_GRID_M)}, got {text!r}")
    return leg, key


P3B_PRESSURE_GRADE = "normal"
P3B_IMU_GRADE = "ideal"
P3B_SEED = 20261026
"""Sensors of the P3b set (control D-1, user-confirmed 2026-10-26): WIKA A-10 normal, IMU ideal, one seed."""


def seal_friction_override(fs_kN: float | None) -> dict[str, Any]:
    """Seal friction level override of the plant (front legs, ``actuator.seal_friction.level_N``;
    rear = front x ``rear_scale``). 0 / None = no override (the P3a plant, bit-identical)."""
    fs = 0.0 if fs_kN is None else float(fs_kN)
    if fs < 0.0 or not math.isfinite(fs):
        raise ValueError(f"--fs-kN must be >= 0: {fs_kN!r}")
    return {} if fs == 0.0 else {"actuator.seal_friction.level_N": fs * 1e3}


def plan_summary() -> dict[str, Any]:
    rows = case_plan()
    groups: dict[str, dict[str, float]] = {}
    for r in rows:
        g = groups.setdefault(r["group"], {"cases": 0, "wall_serial_s": 0.0, "wall_max_case_s": 0.0})
        g["cases"] += 1
        g["wall_serial_s"] += r["wall_est_s"]
        g["wall_max_case_s"] = max(g["wall_max_case_s"], r["wall_est_s"])
        g["wall_serial_4cm_s"] = g.get("wall_serial_4cm_s", 0.0) + r["wall_est_4cm_grid_s"]
    return {"rows": rows, "groups": groups,
            "basis": f"single pad {P1_COST_US_PER_STEP:g} us/step, machine "
                     f"{MACHINE_COST_US_PER_STEP:g} us/step at dt 1e-4 s (ASSUMPTION, P-core, shared)"}


# --- common setup -------------------------------------------------------------------------------


def _soil_overrides(items) -> dict[str, float]:
    out = {}
    for item in items or ():
        k, v = item.split("=", 1)
        out[k.strip()] = float(v)
    return out


def load_inputs(args):
    from outrigger_sim.chrono.scm_model import load_soil_set
    from outrigger_sim.pad_variants import apply_pad_variant, pad_variant_meta
    from outrigger_sim.params import load_params

    over = seal_friction_override(getattr(args, "fs_kN", 0.0))
    params = apply_pad_variant(load_params(level=args.level, model="L2b_NSC", overrides=over or None),
                               args.pad_variant)
    pv = pad_variant_meta(args.pad_variant, params=params)
    soil = load_soil_set(args.soil, overrides=_soil_overrides(args.soil_override))
    return params, pv, soil


def load_soil_patch(args):
    """G6: ``(leg, SoilSet)`` of ``--soil-patch`` (no soil overrides on the patch set) or None."""
    from outrigger_sim.chrono.scm_model import load_soil_set

    sp = parse_soil_patch(getattr(args, "soil_patch", None))
    return None if sp is None else (sp[0], load_soil_set(sp[1]))


PLACEMENT_ENV = "OUTRIGGER_PLACEMENT"
"""Core pool of this process (``s9_batch`` E pool): ``pcore`` (default) or ``ecore``."""
PLACEMENT_MODES = ("pcore", "ecore")


def placement_mode(environ=None) -> str:
    """``OUTRIGGER_PLACEMENT`` (unset / empty = ``pcore``); any other value than
    :data:`PLACEMENT_MODES` raises ValueError."""
    env = os.environ if environ is None else environ
    mode = (env.get(PLACEMENT_ENV) or "pcore").strip().lower()
    if mode not in PLACEMENT_MODES:
        raise ValueError(f"{PLACEMENT_ENV}={env.get(PLACEMENT_ENV)!r}: must be one of {PLACEMENT_MODES}")
    return mode


def place():
    """Pin this process to the pool of :func:`placement_mode` with EcoQoS off
    (``outrigger_sim.hostcpu.place_process``; before 2026-10-26 always ``pcore`` through the
    identical ``solver_benchmark/step_cost_S0.place_process``). The returned dict (result meta
    ``placement``) carries the mode, the environment value and the affinity outcome."""
    from outrigger_sim.hostcpu import place_process  # noqa: PLC0415

    mode = placement_mode()
    info = dict(place_process(mode))
    info.update(requested=mode, env_var=PLACEMENT_ENV, env_value=os.environ.get(PLACEMENT_ENV))
    return info


def out_dir(action: str, tag: str, root: str | None = None) -> Path:
    """``07_results/S9/<action>_<tag>_<stamp>/`` or, with ``root`` (batch folder), ``<root>/<tag>/``."""
    if root:
        d = Path(root) / tag
        d.mkdir(parents=True, exist_ok=True)
        return d
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    d = RESULTS / f"{action}_{tag}_{stamp}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _plain(x):
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if isinstance(x, np.ndarray):
        return _plain(x.tolist())
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, Path):
        return x.as_posix()
    return x


# --- single pad (P1) --------------------------------------------------------------------------------


def build_single_pad(params, pv, soil, *, leg: str, shear: str, joint: str, k_sw: float,
                     stiffness_mode: str, interface: bool, grid_m: float, dt_s: float,
                     normal_load_N: float | None = None, ray_shape: str = "mesh", num_threads: int = 4,
                     terrain_size_m: tuple[float, float] = (1.2, 1.2)):
    """Single swivel pad (YAML pad body + pad hull) under a 'share' body (mass N/g - m_pad,
    translation free, rotation locked to the ground) on a level SCM plane z = 0 (the 5.33.2 probe
    layout with the project pad body, anchor bushing and swivel stabiliser)."""
    import pychrono as ch

    from outrigger_sim.chrono.ground_bushing import ADHESION_FULL_NORMAL_N, GroundBushingCoulomb, PadBushingSpec
    from outrigger_sim.chrono.scm_model import (
        PAD_DOMAIN_XY_M, ACTIVE_DOMAIN_HEIGHT_M, PadNormals, ScmForceReader, SwivelStabiliser,
        add_active_domain, add_pad_ray_mesh, initialize_terrain, make_terrain, pad_bottom_outline_local_m,
        pad_tangential_values, split_body_props)
    from outrigger_sim.chrono.sim_shapes import add_pad_hull
    from outrigger_sim.chrono.system import make_system
    from outrigger_sim.params import LEG_ORDER

    i = LEG_ORDER.index(leg)
    bundle = make_system(params, "L1", dt=dt_s, floor_plate=False)
    s, ground = bundle.system, bundle.floor
    if num_threads > 0:  # SCM ray casting = num_threads_chrono (CHANGELOG.md:502); fixed, not the Chrono default
        s.SetNumThreads(int(num_threads), 1, 1)
    m_p, c_p, i_p = split_body_props(params, i, "pad_body")
    above = float(params.get(f"legs.{leg}.pad_body.com_above_pad_bottom_m"))
    h_ball = float(params.legs[i].pad.swivel_center_above_pad_bottom_m)
    z0 = 0.0005  # pad bottom above the SCM plane at the start
    pad = ch.ChBody()
    pad.SetName(f"pad_{leg}")
    pad.SetMass(m_p)
    pad.SetInertiaXX(ch.ChVector3d(i_p[0, 0], i_p[1, 1], i_p[2, 2]))
    pad.SetInertiaXY(ch.ChVector3d(i_p[0, 1], i_p[0, 2], i_p[1, 2]))
    pad.SetPos(ch.ChVector3d(0.0, 0.0, z0 + above))
    pad.EnableCollision(True)
    # OBJ frame = machine body coordinates; pad COG at c_p there -> offset -c_p (pad at x = y = 0)
    if ray_shape == "mesh":
        add_pad_ray_mesh(pad, i, ch.ChContactMaterialSMC(), pad_variant=pv["pad_variant"], offset_m=-c_p)
    else:
        add_pad_hull(pad, params, i, ch.ChContactMaterialSMC(), pad_variant=pv["pad_variant"], offset_m=-c_p)
    s.Add(pad)
    N = soil.design_loads_N[i] if normal_load_N is None else float(normal_load_N)
    share = ch.ChBody()
    share.SetName("share")
    share.SetMass(N / G - m_p)
    share.SetInertiaXX(ch.ChVector3d(1e3, 1e3, 1e3))
    share.SetPos(ch.ChVector3d(0.0, 0.0, z0 + h_ball + 0.3))
    s.Add(share)
    ball = ch.ChVector3d(0.0, 0.0, z0 + h_ball)
    link = ch.ChLinkLockSpherical() if joint == "spherical" else ch.ChLinkLockLock()
    link.Initialize(pad, share, ch.ChFramed(ball, ch.QUNIT))
    s.Add(link)
    mate = ch.ChLinkMateGeneric(False, False, False, True, True, True)
    mate.Initialize(share, ground, ch.ChFramed(share.GetPos(), ch.QUNIT))
    s.Add(mate)
    loads = ch.ChLoadContainer()
    s.Add(loads)
    fload = ch.ChLoadBodyForce(share, ch.ChVector3d(0, 0, 0), False, ch.ChVector3d(0, 0, 0), True)
    loads.Add(fload)
    terrain, tmeta = make_terrain(s, soil, shear, (0.0, 0.0, 0.0), np.eye(3), grid_m=grid_m, size_m=tuple(terrain_size_m))
    # SCM grid indices are bounded by the size (SCMLoader::CheckMeshBounds, SCMTerrain.cpp:747): a sliding
    # pad (P1-L3) needs a long patch
    bottom_local = np.array([0.0, 0.0, -above])
    add_active_domain(terrain, tmeta, pad, bottom_local, (PAD_DOMAIN_XY_M, PAD_DOMAIN_XY_M, ACTIVE_DOMAIN_HEIGHT_M),
                      f"pad_{leg}")
    initialize_terrain(terrain, tmeta)
    reader = ScmForceReader(terrain, [pad], share)
    area = [float(pv["pad_bottom_area_m2"][lg]) for lg in LEG_ORDER]
    values = pad_tangential_values(params, soil, area, stiffness_mode=stiffness_mode, interface=interface)
    bushing = None
    normals = PadNormals(reader, np.array([0.0, 0.0, 1.0]))
    if shear == "bprime":
        spec = PadBushingSpec(name=leg, body=pad, sphere_centre_body_local_m=(0.0, 0.0, h_ball - above),
                              sphere_radius_m=h_ball, stiffness_N_m=values.stiffness_N_m[i],
                              damping_input_N_s_m=values.damping_input_N_s_m[i],
                              adhesion_N=values.adhesion_N[i])
        bushing = GroundBushingCoulomb(
            s, ground, [spec], friction=values.friction,
            slip_damping_reenable_speed_m_s=float(params.contact.rigid_floor.L1.slip_damping_reenable_speed_m_s),
            dt_s=bundle.dt_s, surface_point_floor_local_m=(0.0, 0.0, 0.0), normal_force_source=normals,
            adhesion_full_normal_N=ADHESION_FULL_NORMAL_N)
    swivel = (SwivelStabiliser(s, ground, [pad], np.eye(3), k_sw, [math.degrees(params.legs[i].pad.swivel_tilt_range_rad)])
              if (k_sw > 0.0 and joint == "spherical") else None)
    meta = {"bundle": bundle.meta(), "scm": tmeta, "pad_values": values.meta(), "leg": leg, "leg_index": i,
            "normal_load_N": N, "share_mass_kg": N / G - m_p, "pad_mass_kg": m_p, "joint": joint,
            "k_sw_N_m_rad": k_sw if swivel else 0.0, "pad_bottom_start_z_m": z0,
            "pad_area_m2": area[i], "frame": "world z up, SCM plane z = 0, load along +x", "ray_shape": ray_shape,
            "num_threads_chrono": int(num_threads)}
    outline = pad_bottom_outline_local_m(pv["pad_variant"], i, -c_p)
    obj_offset = float(outline[0, 2] + above)  # OBJ bottom - YAML bottom, pad COG frame z [m]
    meta["obj_bottom_minus_yaml_bottom_m"] = obj_offset
    return {"system": s, "pad": pad, "share": share, "terrain": terrain, "reader": reader, "bushing": bushing,
            "swivel": swivel, "fload": fload, "dt_s": bundle.dt_s, "above": above, "meta": meta,
            "limit_N": None if bushing is None else float(bushing.tangential_limit_N([N])[0]),
            "k_t_N_m": values.stiffness_N_m[i], "outline_local_m": outline, "grid_m": grid_m,
            "bundle": bundle, "obj_bottom_offset_m": obj_offset}


def single_pad_node_stats(m) -> dict[str, Any]:
    """SCM nodes inside the pad bottom polygon (P1-V0 (iii)): contact node count, node mean sinkage,
    geometric sinkage of the pad bottom (``-z_bottom``, YAML pad bottom) and their difference [m].
    ``sinkage_geometric_obj_m`` / ``node_minus_geometric_obj_m`` use the hull OBJ bottom instead
    (type A rear OBJ bottom is 0.044 mm below the YAML bottom, dynamics 5.34.10; type B 0.0 mm)."""
    from outrigger_sim.chrono.scm_model import node_stats_in_outline

    pad = m["pad"]
    import pychrono as ch

    world = np.array([[v.x, v.y, v.z] for v in (pad.TransformPointLocalToParent(ch.ChVector3d(*map(float, p)))
                                                 for p in m["outline_local_m"])])
    st = node_stats_in_outline(m["terrain"], (0.0, 0.0, 0.0), np.eye(3), m["grid_m"], world)
    geo = -(pad.GetPos().z - m["above"])
    geo_obj = geo - m["obj_bottom_offset_m"]
    st["sinkage_geometric_m"] = float(geo)
    st["sinkage_geometric_obj_m"] = float(geo_obj)
    sc = st["sinkage_mean_contact_m"]
    st["node_minus_geometric_m"] = None if sc is None else float(sc - geo)
    st["node_minus_geometric_obj_m"] = None if sc is None else float(sc - geo_obj)
    st["ray_hits"] = int(m["terrain"].GetNumRayHits())
    st["contact_patches"] = int(m["terrain"].GetNumContactPatches())
    return st


def bekker_tau_s(soil, area_m2: float, b_m: float, load_N: float, unloading: bool) -> float:
    """Settle time constant of a pad load level (dynamics 5.31.8): tau = R A / (dF/dz) on the
    virgin branch F = A (Kc/b + Kphi) z^n (dF/dz = n F / z), tau = R / K on unloading (elastic)."""
    c = soil.chrono
    if unloading:
        return c["damping_R"] / c["elastic_K"]
    k = c["Kc"] / b_m + c["Kphi"]
    z = (load_N / (area_m2 * k)) ** (1.0 / c["n"])
    return c["damping_R"] * area_m2 / (c["n"] * load_N / z)


def load_step_schedule(args, soil, area_m2: float, b_m: float, n_full_N: float) -> list[dict[str, Any]]:
    """Vertical load steps (P1-V16a-c): factors ``--load-steps``; the first ramp is ``--load-ramp``
    (Poly345 from 0), later ramps ``--step-ramp`` (Poly345 between levels); hold per level
    ``--step-hold`` [s] or 'auto' = max(1 s, 5 tau) rounded up to 0.1 s (dynamics 5.31.8 / 5.34.3)."""
    levels = [float(v) for v in args.load_steps.split(",")]
    holds_in = args.step_hold.split(",")
    rows, t, prev, peak = [], 0.0, 0.0, 0.0
    for k, f in enumerate(levels):
        ramp = args.load_ramp if k == 0 else args.step_ramp
        unloading = f < peak
        tau = bekker_tau_s(soil, area_m2, b_m, f * n_full_N, unloading)
        h = holds_in[min(k, len(holds_in) - 1)]
        hold = max(1.0, math.ceil(5.0 * tau * 10.0 - 1e-9) / 10.0) if h == "auto" else float(h)
        rows.append({"level": k, "factor": f, "from_factor": prev, "t_ramp_start_s": t, "ramp_s": ramp,
                     "t_hold_start_s": t + ramp, "hold_s": hold, "t_hold_end_s": t + ramp + hold,
                     "tau_est_s": tau, "unloading": unloading})
        t += ramp + hold
        prev, peak = f, max(peak, f)
    return rows


def load_step_factor(t_s: float, schedule: list[dict[str, Any]]) -> float:
    from outrigger_sim.chrono.scm_model import gravity_ramp_factor

    for row in schedule:
        if t_s < row["t_hold_start_s"]:
            u = gravity_ramp_factor(t_s - row["t_ramp_start_s"], row["ramp_s"], "poly345")
            return row["from_factor"] + (row["factor"] - row["from_factor"]) * u
        if t_s < row["t_hold_end_s"]:
            return row["factor"]
    return schedule[-1]["factor"]


def run_single_pad(args) -> Path:
    import pychrono as ch

    placement = place()
    params, pv, soil = load_inputs(args)
    m = build_single_pad(params, pv, soil, leg=args.leg, shear=args.scm_shear, joint=args.joint, k_sw=args.k_sw,
                         stiffness_mode=args.stiffness_mode, interface=args.interface, grid_m=args.grid,
                         dt_s=args.dt, normal_load_N=args.normal_load, ray_shape=args.ray_shape,
                         num_threads=args.threads, terrain_size_m=tuple(args.terrain_size))
    from outrigger_sim.chrono.scm_model import gravity_ramp_factor
    from outrigger_sim.chrono.system import gravity_vector, set_gravity

    s, pad, share, reader, bushing, swivel = (m[k] for k in ("system", "pad", "share", "reader", "bushing", "swivel"))
    dt = m["dt_s"]
    if args.force_limit_factor is not None:  # P1-L3: horizontal load = factor x tangential limit at full load
        if m["limit_N"] is None:
            raise SystemExit("--force-limit-factor needs the anchor bushing (--scm-shear bprime)")
        args.force = float(args.force_limit_factor * m["limit_N"])
    schedule = None
    if args.load_steps:
        outline = m["outline_local_m"][:, :2]
        on = np.roll(outline, -1, axis=0)
        a_out = float(0.5 * abs(np.sum(outline[:, 0] * on[:, 1] - on[:, 0] * outline[:, 1])))
        b_out = 2.0 * a_out / float(np.sum(np.hypot(*(on - outline).T)))
        schedule = load_step_schedule(args, soil, m["meta"]["pad_area_m2"], b_out, m["meta"]["normal_load_N"])
        args.t_end = max(args.t_end, schedule[-1]["t_hold_end_s"])
        args.t_settle = max(args.t_settle, schedule[-1]["t_hold_end_s"])  # no horizontal load in a step run
    level_marks = {} if schedule is None else {round(r["t_hold_end_s"] / dt): ("end", r["level"]) for r in schedule}
    if schedule is not None:
        level_marks.update({round(r["t_hold_start_s"] / dt): ("start", r["level"]) for r in schedule})
    level_rows: dict[int, dict[str, Any]] = {}
    ft_scm_abs_max = 0.0
    n_steps = round(args.t_end / dt)
    every = max(1, round(RECORD_S / dt))
    node_every = max(1, round(NODE_SINKAGE_EVERY_S / dt))
    keys = ("t", "x", "y", "z_bottom", "tilt_deg", "Fx_scm", "Fy_scm", "Fz_scm", "Ft_bush_x", "N_bush", "slip_x",
            "Fx_step_min", "Fx_step_max", "g_factor", "omega_x", "omega_y", "omega_z", "v_t_com", "v_rot_rms")
    rec = {k: [] for k in keys}
    node_rows: list[dict[str, Any]] = []
    g_vec = np.asarray(gravity_vector(params), dtype=float)
    # bottom sample points for the node-velocity rotation share (P1-L6): polygon corners + centre
    r_local = np.vstack([m["outline_local_m"], m["outline_local_m"].mean(axis=0)])
    lo, hi = 1e30, -1e30
    t0 = time.perf_counter()
    for k in range(n_steps):
        t = k * dt
        if t < args.t_settle:
            fh = 0.0
        elif t < args.t_settle + args.t_ramp:
            fh = args.force * (t - args.t_settle) / args.t_ramp
        else:
            fh = args.force
        gf = (gravity_ramp_factor(t, args.load_ramp, args.load_ramp_shape) if schedule is None
              else load_step_factor(t, schedule))
        set_gravity(s, gf * g_vec)
        m["fload"].SetForce(ch.ChVector3d(fh, 0, 0), False)
        s.DoStepDynamics(dt)
        reader.refresh()
        ft_scm_abs_max = max(ft_scm_abs_max, float(np.hypot(reader.pad_force_N[0, 0], reader.pad_force_N[0, 1])))
        mark = level_marks.get(k + 1)
        if mark is not None:
            row = level_rows.setdefault(mark[1], {"level": mark[1]})
            row[mark[0]] = {"t_s": (k + 1) * dt, "factor": gf, "load_N": gf * m["meta"]["normal_load_N"],
                            "Fz_scm_N": float(reader.pad_force_N[0, 2]),
                            "z_bottom_m": float(pad.GetPos().z - m["above"]),
                            "nodes": single_pad_node_stats(m)}
        if bushing is not None:
            bushing.after_step(dt)
        if swivel is not None:
            swivel.update(bushing.in_contact if bushing is not None else np.array([reader.pad_force_N[0, 2] > 100.0]),
                          float(s.GetChTime()))
        ft_tot = reader.pad_force_N[0, 0] + (bushing.tangential_force_world_N()[0, 0] if bushing else 0.0)
        lo, hi = min(lo, ft_tot), max(hi, ft_tot)
        if (k + 1) % every == 0:
            p = share.GetPos()
            zax = pad.GetRot().GetAxisZ()
            rec["t"].append((k + 1) * dt)
            rec["x"].append(p.x)
            rec["y"].append(p.y)
            rec["z_bottom"].append(pad.GetPos().z - m["above"])
            rec["tilt_deg"].append(math.degrees(math.acos(max(-1.0, min(1.0, zax.z)))))
            rec["Fx_scm"].append(reader.pad_force_N[0, 0])
            rec["Fy_scm"].append(reader.pad_force_N[0, 1])
            rec["Fz_scm"].append(reader.pad_force_N[0, 2])
            rec["Ft_bush_x"].append(bushing.tangential_force_world_N()[0, 0] if bushing else 0.0)
            rec["N_bush"].append(float(bushing.normal_force_N[0]) if bushing else float(reader.pad_force_N[0, 2]))
            rec["slip_x"].append(float(bushing.slip_total_m[0, 0]) if bushing else 0.0)
            rec["Fx_step_min"].append(lo)
            rec["Fx_step_max"].append(hi)
            lo, hi = 1e30, -1e30
            rec["g_factor"].append(gf)
            w = pad.GetAngVelParent()
            om = np.array([w.x, w.y, w.z])
            v = pad.GetPosDt()
            rec["omega_x"].append(om[0])
            rec["omega_y"].append(om[1])
            rec["omega_z"].append(om[2])
            rec["v_t_com"].append(math.hypot(v.x, v.y))
            rot = pad.GetRotMat()
            rmat = np.array([[rot.GetAxisX().x, rot.GetAxisY().x, rot.GetAxisZ().x],
                             [rot.GetAxisX().y, rot.GetAxisY().y, rot.GetAxisZ().y],
                             [rot.GetAxisX().z, rot.GetAxisY().z, rot.GetAxisZ().z]])
            vr = np.cross(om, r_local @ rmat.T)[:, :2]  # tangential part of omega x r at the bottom points
            rec["v_rot_rms"].append(float(np.sqrt(np.mean(np.sum(vr ** 2, axis=1)))))
        if (k + 1) % node_every == 0:
            node_rows.append({"t_s": (k + 1) * dt, **single_pad_node_stats(m)})
    wall = time.perf_counter() - t0
    r = {k: np.asarray(v) for k, v in rec.items()}
    hold = r["t"] >= args.t_settle + args.t_ramp + 0.5
    settle = r["t"] <= args.t_settle
    ft_total = -(r["Fx_scm"] + r["Ft_bush_x"])  # ground force on the pad, -x when the load pushes +x
    summary: dict[str, Any] = {
        "action": "single-pad", "args": vars(args), "placement": placement, "wall_s": wall,
        "us_per_step": wall / n_steps * 1e6, "meta": m["meta"], "limit_N": m["limit_N"], "k_t_N_m": m["k_t_N_m"],
        "settle_end": {"z_bottom_mm": float(r["z_bottom"][settle][-1] * 1e3),
                       "sinkage_mm": float(-r["z_bottom"][settle][-1] * 1e3),
                       "Fz_scm_N": float(r["Fz_scm"][settle][-1]),
                       "Fz_over_weight": float(r["Fz_scm"][settle][-1] / m["meta"]["normal_load_N"]),
                       "tilt_deg": float(r["tilt_deg"][settle][-1]),
                       "x_mm": float(r["x"][settle][-1] * 1e3), "y_mm": float(r["y"][settle][-1] * 1e3)},
        "swivel": None if swivel is None else swivel.meta(),
        "bushing_events": None if bushing is None else {k: v.tolist() for k, v in bushing.event_table().items()},
        "load_schedule": {"vertical": {"shape": args.load_ramp_shape, "ramp_s": args.load_ramp,
                                       "how": "gravity factor on pad + share body (load = N x factor)"},
                          "horizontal": {"ramp_s": args.t_ramp, "start_s": args.t_settle, "force_N": args.force}},
        "first_step": {"first_record_t_s": float(r["t"][0]) if len(r["t"]) else None,
                       "first_record_Fz_scm_N": float(r["Fz_scm"][0]) if len(r["Fz_scm"]) else None},
        "node_series": node_rows,
        "force_N": args.force,
        "scm_tangential_abs_max_N": ft_scm_abs_max,
        "scm_tangential_abs_max_note": "max over every step of |(Fx, Fy)| of the SCM resultant on the pad (P1-L1)",
        "tilt_deg_max_all": float(r["tilt_deg"].max()) if len(r["tilt_deg"]) else None,
        "tilt_deg_end": float(r["tilt_deg"][-1]) if len(r["tilt_deg"]) else None,
        "z_bottom_end_mm": float(r["z_bottom"][-1] * 1e3) if len(r["z_bottom"]) else None,
        "Fz_scm_end_N": float(r["Fz_scm"][-1]) if len(r["Fz_scm"]) else None,
        "load_steps": None if schedule is None else {
            "schedule": schedule, "levels": [level_rows.get(row["level"]) for row in schedule]},
    }
    settle_nodes = [n for n in node_rows if n["t_s"] <= args.t_settle + 1e-9]
    if settle_nodes:
        summary["settle_end"]["nodes"] = settle_nodes[-1]
    if hold.any():
        th, xh = r["t"][hold], r["x"][hold]
        summary["hold"] = {
            "window_s": [float(th[0]), float(th[-1])],
            "drift_mm": float((xh[-1] - xh[0]) * 1e3),
            # ringing of the share mass on k_t decays slowly; drift judged on 0.5 s window means
            "drift_window_means_mm": float((xh[th >= th[-1] - 0.5].mean() - xh[th <= th[0] + 0.5].mean()) * 1e3),
            "x_window_means_mm": [float(xh[(th >= a) & (th < a + 0.5)].mean() * 1e3)
                                  for a in np.arange(th[0], th[-1] - 0.49, 0.5)],
            "drift_velocity_m_s": float(np.polyfit(th, xh, 1)[0]) if len(th) > 2 else None,
            "x_mean_mm": float(xh.mean() * 1e3),
            "elastic_expected_mm": None if not m["k_t_N_m"] else float(args.force / m["k_t_N_m"] * 1e3),
            "Ft_total_mean_N": float(ft_total[hold].mean()),
            "Ft_over_F": float(ft_total[hold].mean() / args.force) if args.force else None,
            "Ft_over_limit": float(ft_total[hold].mean() / m["limit_N"]) if m["limit_N"] else None,
            "Ft_over_limit_last_1s": (float(ft_total[hold & (r["t"] >= r["t"][-1] - 1.0)].mean() / m["limit_N"])
                                      if m["limit_N"] else None),
            "Ft_step_range_N": [float(-r["Fx_step_max"][hold].max()), float(-r["Fx_step_min"][hold].min())],
            "Fx_scm_abs_max_N": float(np.abs(r["Fx_scm"][hold]).max()),
            "tilt_deg_max": float(r["tilt_deg"][hold].max()),
            "sinkage_change_mm": float(-(r["z_bottom"][hold][-1] - r["z_bottom"][hold][0]) * 1e3),
            "slip_total_x_mm": float(r["slip_x"][-1] * 1e3),
            # P1-L6 diagnostics (dynamics 5.34.4 (ii)): pad angular velocity RMS and the rotation share
            # of the bottom-node slip velocity (|omega x r| tangential RMS over the polygon corners + centre)
            # against the translational (COM tangential) speed RMS; hypothesis: ratio >= 1 with drift
            "p1_l6": {
                "omega_rms_rad_s": [float(np.sqrt(np.mean(r[c][hold] ** 2))) for c in ("omega_x", "omega_y", "omega_z")],
                "v_rot_rms_m_s": float(np.sqrt(np.mean(r["v_rot_rms"][hold] ** 2))),
                "v_trans_rms_m_s": float(np.sqrt(np.mean(r["v_t_com"][hold] ** 2))),
                "rot_over_trans": (float(np.sqrt(np.mean(r["v_rot_rms"][hold] ** 2)) / np.sqrt(np.mean(r["v_t_com"][hold] ** 2)))
                                   if np.any(r["v_t_com"][hold] > 0) else None),
                "Fx_total_step_range_N": [float(r["Fx_step_min"][hold].min()), float(r["Fx_step_max"][hold].max())],
                "sampling": f"every {RECORD_S:g} s (record rate), hold window"},
        }
    tag = args.case or f"{args.soil}_{args.pad_variant}_{args.leg}_{args.scm_shear}_F{args.force:.0f}"
    d = out_dir("single", tag, args.out_root)
    np.savez(d / "series.npz", **r)
    (d / "result.json").write_text(json.dumps(_plain(summary), indent=1, ensure_ascii=False), "utf-8")
    print(json.dumps(_plain({k: summary.get(k) for k in ("settle_end", "first_step", "hold", "us_per_step",
                                                         "limit_N")}),
                     indent=1), flush=True)
    print("->", d, flush=True)
    return d


# --- machine (P2 / P3a) -------------------------------------------------------------------------------


def build_machine(args, params, pv, soil):
    from outrigger_sim.chrono.scm_model import S9Model
    from outrigger_sim.scenarios.slope import floor_normal

    normal = None if (args.floor_roll == 0.0 and args.floor_pitch == 0.0) else floor_normal(
        args.floor_roll, args.floor_pitch)
    patch = load_soil_patch(args)
    extra = {} if patch is None else {"soil_patch": patch,
                                      "soil_patch_grid_m": getattr(args, "soil_patch_grid", None)}
    return S9Model(params, soil, pv, shear=args.scm_shear, floor_normal=normal, dt_s=args.dt,
                   stiffness_mode=args.stiffness_mode, interface=args.interface,
                   swivel_stiffness_N_m_rad=args.k_sw, grid_m=args.grid, num_threads=args.threads,
                   ray_shape=args.ray_shape, crawler_grid_m=args.crawler_grid, **extra)


def gravity_hold_s(args) -> float:
    """``--gravity-hold`` or its default: 5 s with the settle dashpot (5.35.4 (a)), 2 s without (5.34.2)."""
    if args.gravity_hold is not None:
        return float(args.gravity_hold)
    return GRAVITY_HOLD_DASHPOT_S if args.settle_dashpot != "none" else GRAVITY_HOLD_FORMER_S


def settle_time_s(args) -> float:
    """Machine settle time: ``--t-settle`` or gravity ramp + hold (3 + 5 s dashpot, 3 + 2 s former)."""
    if args.t_settle is not None:
        return float(args.t_settle)
    ramp = 0.0 if args.gravity_ramp_shape == "step" else args.gravity_ramp
    return ramp + gravity_hold_s(args)


def add_settle_dashpot(args, model):
    """Settle dashpot of ``--settle-dashpot`` on the S9 model (None for ``none``)."""
    if args.settle_dashpot == "none":
        return None
    from outrigger_sim.chrono.scm_model import SettleDashpot

    return SettleDashpot(model, c_z_N_s_m=args.dashpot_c_z, c_pitch_N_m_s_rad=args.dashpot_c_pitch,
                         c_roll_N_m_s_rad=args.dashpot_c_roll, fade_s=tuple(args.dashpot_fade))


def gravity_schedule_meta(args, dashpot=None) -> dict[str, Any]:
    if args.gravity_ramp_shape != "poly345":
        rule = "sensitivity / former sudden gravity"
    elif args.settle_dashpot != "none":
        rule = ("dynamics_model.md 5.35.4 (a), U-S9P-1: |g| Poly345 3 s + hold 5 s with the heave / roll / pitch "
                "settle dashpot (full until 3 s, linear to 0 at 5 s), judge the last 1 s (7-8 s) mean")
    else:
        rule = "dynamics_model.md 5.34.2 P2 (former): |g| Poly345 3 s + hold 2 s, judge last 1 s mean"
    return {"shape": args.gravity_ramp_shape, "ramp_s": args.gravity_ramp, "hold_s": gravity_hold_s(args),
            "settle_s": settle_time_s(args), "rule": rule, "settle_dashpot_mode": args.settle_dashpot,
            "settle_dashpot": None if dashpot is None else dashpot.meta()}


def settle_judgement(rows: list[dict[str, Any]], w_total: float, window_s: float = 1.0) -> dict[str, Any]:
    """P2 settle values over the last ``window_s`` (5.34.2): pitch / roll mean and p-p, origin z
    mean, SCM normal sum / weight (crawler + pads, along the plane normal)."""
    t_end = rows[-1]["t_s"]
    win = [r for r in rows if r["t_s"] >= t_end - window_s - 1e-12]
    pitch = np.array([r["roll_pitch_deg"][1] for r in win])
    roll = np.array([r["roll_pitch_deg"][0] for r in win])
    z = np.array([r["body_pos_m"][2] for r in win])
    x = np.array([r["body_pos_m"][0] for r in win])
    n_sum = np.array([r["scm_crawler_normal_N"] + float(np.sum(r["scm_pad_normal_N"])) for r in win])
    return {"window_s": [float(win[0]["t_s"]), float(t_end)], "pitch_mean_deg": float(pitch.mean()),
            "pitch_pp_deg": float(np.ptp(pitch)), "roll_mean_deg": float(roll.mean()), "roll_pp_deg": float(np.ptp(roll)),
            "z_origin_mean_mm": float(z.mean() * 1e3), "x_origin_pp_mm": float(np.ptp(x) * 1e3),
            "normal_over_weight": float(n_sum.mean() / w_total)}


def run_machine(args) -> Path:
    from outrigger_sim.chrono.scm_model import gravity_ramp_factor
    from outrigger_sim.frames import roll_pitch_from_quat

    placement = place()
    params, pv, soil = load_inputs(args)
    tb = time.perf_counter()
    model = build_machine(args, params, pv, soil)
    dashpot = add_settle_dashpot(args, model)
    build_s = time.perf_counter() - tb
    dt = model.dt_s
    every = max(1, round(RECORD_S / dt))
    node_every = max(1, round(NODE_SINKAGE_EVERY_S / dt))
    w_total = (params.superstructure.mass_properties.mass_kg
               + sum(leg.moving_part.mass_kg for leg in params.legs)) * G
    rows: list[dict[str, Any]] = []
    node_rows: list[dict[str, Any]] = []
    t_settle = settle_time_s(args)
    t_settle_steps = round(t_settle / dt)
    t_lift_steps = round(args.lift_s / dt)
    v_lift = float(params.actuator.max_speed_m_s) * args.lift_speed_fraction
    rut = None
    first_step = None
    t0 = time.perf_counter()
    for k in range(t_settle_steps + t_lift_steps):
        if k == t_settle_steps:
            rut = model.mark_rut_reference()
            if t_lift_steps:
                model.set_command([v_lift] * 4)
        model.set_gravity_factor(gravity_ramp_factor(k * dt, args.gravity_ramp, args.gravity_ramp_shape))
        p = model.step(capture=((k + 1) % every == 0))
        if k == 0:
            first_step = {"gravity_factor": model.gravity_factor,
                          "scm_crawler_force_N": model.forces.sup_force_N.tolist(),
                          "scm_pad_force_N": model.forces.pad_force_N.tolist(),
                          "force_norm_max_N": float(np.linalg.norm(np.vstack([model.forces.sup_force_N,
                                                                              model.forces.pad_force_N]),
                                                                   axis=1).max())}
        if p is not None:
            row = model.s9_record()
            rp = roll_pitch_from_quat(p.body_quat_wxyz)
            row.update(body_pos_m=p.body_pos_m.tolist(), roll_pitch_deg=[math.degrees(a) for a in rp],
                       s_motor_m=p.motor_pos_m.tolist(), F_cyl_N=p.motor_force_N.tolist())
            rows.append(row)
        if (k + 1) % node_every == 0:
            node_rows.append({"t_s": float(model.system.GetChTime()), "pad_nodes": model.pad_node_stats()})
    wall = time.perf_counter() - t0
    if rut is None:  # settle only: reference at the end (clearance 0 by definition)
        rut = model.mark_rut_reference()
        rows[-1]["rut_clearance_m"] = model.rut_clearance_m()
    n_steps = t_settle_steps + t_lift_steps
    last = rows[-1]
    win = [r for r in rows if r["t_s"] >= rows[-1]["t_s"] - 0.1]
    crawler_n = float(np.mean([r["scm_crawler_normal_N"] for r in win]))
    pads_n = np.mean([r["scm_pad_normal_N"] for r in win], axis=0)
    total_n = crawler_n + float(np.sum(pads_n))
    summary = {
        "action": "machine", "args": vars(args), "placement": placement, "build_s": build_s, "wall_s": wall,
        "n_steps": n_steps, "us_per_step": wall / max(n_steps, 1) * 1e6,
        "meta": model.meta(), "rut_reference": rut,
        "end": {"t_s": last["t_s"], "roll_pitch_deg": last["roll_pitch_deg"], "body_pos_m": last["body_pos_m"],
                "window_s": 0.1, "scm_crawler_normal_mean_N": crawler_n, "scm_pad_normal_mean_N": pads_n.tolist(),
                "total_normal_N": total_n, "weight_N": w_total,
                "equilibrium_rel_error": (total_n - w_total) / w_total,
                "contact_patches": last["scm_contact_patches"], "track_normal_raw_N": last["scm_track_normal_raw_N"],
                "pad_sinkage_geometric_m": last["pad_sinkage_geometric_m"], "rut_clearance_m": last["rut_clearance_m"],
                "pad_tilt_deg": last["pad_tilt_deg"], "track_utilisation": last.get("track_utilisation"),
                "s_motor_m": last["s_motor_m"], "F_cyl_N": last["F_cyl_N"]},
        "node_sinkage": node_rows[-3:],
        "gravity_schedule": gravity_schedule_meta(args, dashpot),
        "first_step": first_step,
        "start_rise": {"z_origin_max_mm": float(max(r["body_pos_m"][2] for r in rows) * 1e3),
                       "z_origin_start_mm": float(rows[0]["body_pos_m"][2] * 1e3)},
        "settle_last_1s": settle_judgement([r for r in rows if r["t_s"] <= t_settle + 1e-9], w_total)
        if t_settle >= 1.0 else None,
        "swivel": None if model.swivel is None else model.swivel.meta(),
        "pad_bushing_events": None if model.pad_bushing is None else {
            k: v.tolist() for k, v in model.pad_bushing.event_table().items()},
        "crawler_bushing_events": None if model.crawler_bushing is None else {
            k: v.tolist() for k, v in model.crawler_bushing.event_table().items()},
    }
    # P1-L5: origin drift over the last args.drift_window seconds of the settle (in the plane and
    # along the plane normal, world frame), and the track anchor slip
    settle_rows = [r for r in rows if r["t_s"] <= t_settle + 1e-9]
    if settle_rows and args.drift_window > 0.0 and settle_rows[-1]["t_s"] - settle_rows[0]["t_s"] >= args.drift_window:
        t_a = settle_rows[-1]["t_s"] - args.drift_window
        ra = min(settle_rows, key=lambda r: abs(r["t_s"] - t_a))
        rb = settle_rows[-1]
        dp = np.asarray(rb["body_pos_m"]) - np.asarray(ra["body_pos_m"])
        nrm = model.floor_normal_world()
        dn = float(dp @ nrm)
        dpl = dp - dn * nrm
        summary["settle_drift"] = {
            "window_s": [float(ra["t_s"]), float(rb["t_s"])], "d_origin_world_m": dp.tolist(),
            "d_in_plane_mm": float(np.linalg.norm(dpl) * 1e3), "d_normal_mm": float(dn * 1e3),
            "d_pitch_deg": float(rb["roll_pitch_deg"][1] - ra["roll_pitch_deg"][1]),
            "d_roll_deg": float(rb["roll_pitch_deg"][0] - ra["roll_pitch_deg"][0]),
            "criterion_mm": 0.1, "note": "P1-L5 (dynamics 5.33.9): 10 s drift <= 0.1 mm (in plane)"}
    summary["num_threads_chrono"] = model.num_threads
    limits = p3a_limits(params)
    if t_lift_steps:
        summary["p3a"] = p3a_lift_records(rows, node_rows, t_lift_start_s=t_settle_steps * dt, weight_N=w_total,
                                          design_loads_N=list(soil.design_loads_N), limits=limits)
    grids = f"{args.grid * 100:g}cm" + ("" if args.crawler_grid is None else f"_c{args.crawler_grid * 100:g}cm")
    tag = args.case or (f"{args.soil}_{args.pad_variant}_{args.scm_shear}_{grids}_{args.gravity_ramp_shape}"
                        f"{args.gravity_ramp:g}_lift{args.lift_s:g}")
    d = out_dir("machine", tag, args.out_root)
    series = {key: np.asarray([r[key] for r in rows], dtype=float) for key in
              ("t_s", "scm_crawler_normal_N", "scm_pad_normal_N", "pad_sinkage_geometric_m", "body_pos_m",
               "roll_pitch_deg", "s_motor_m", "F_cyl_N", "scm_contact_patches", "body_omega_world_rad_s",
               "gravity_factor", "scm_ray_hits")}
    # P3a record series (dynamics 5.36.5): None -> NaN (no swivel / no rut reference / no track limit)
    series.update({key: _nan_array(rows, key, width) for key, width in
                   (("pad_tilt_deg", 4), ("rut_clearance_m", None), ("track_utilisation", 2))})
    series.update(node_t_s=np.asarray([n["t_s"] for n in node_rows], dtype=float),
                  node_sinkage_mean_contact_m=np.asarray(
                      [[np.nan if s["sinkage_mean_contact_m"] is None else s["sinkage_mean_contact_m"]
                        for s in n["pad_nodes"]] for n in node_rows], dtype=float).reshape(-1, 4),
                  node_n_contact=np.asarray([[s["n_contact"] for s in n["pad_nodes"]] for n in node_rows],
                                            dtype=float).reshape(-1, 4))
    np.savez(d / "series.npz", **series)
    (d / "result.json").write_text(json.dumps(_plain(summary), indent=1, ensure_ascii=False), "utf-8")
    print(json.dumps(_plain({k: summary[k] for k in ("end", "first_step", "start_rise", "settle_last_1s",
                                                     "us_per_step", "build_s")}), indent=1), flush=True)
    if "p3a" in summary:
        print(json.dumps(_plain(summary["p3a"]["checks"]), indent=1), flush=True)
    print("->", d, flush=True)
    if args.abort_on_limit and "p3a" in summary and summary["p3a"]["checks"]["abort"]:
        print("P3a limit exceeded (force or stroke end margin): exit 3 so the batch stops new launches", flush=True)
        sys.exit(3)
    return d


def _nan_array(rows: list[dict[str, Any]], key: str, width: int | None) -> np.ndarray:
    def one(v):
        if width is None:
            return np.nan if v is None else float(v)
        if v is None:
            return [np.nan] * width
        return [np.nan if x is None else float(x) for x in v]

    return np.asarray([one(r.get(key)) for r in rows], dtype=float)


# --- P3a open-loop lift records (dynamics 5.36.5, U-S9P-5) ------------------------------------------------

P3A_OFF_FRACTION = 0.01
"""P3a-2: crawler departed when the crawler SCM normal sum < 1 % W ..."""
P3A_OFF_HOLD_S = 0.1
"""... for 0.1 s without a break (dynamics 5.36.5)."""
P3A_LOADED_FRACTION = 0.01
"""P3a-5: pad tilt judged while the pad SCM normal > 1 % of that leg's design load N (L4 rule, 5.35.2)."""
P3A_TOUCH_WINDOW_S = 0.2
STROKE_END_MARGIN_M = 0.01
"""Stroke end margin below the measurable maximum (YAML sensors.stroke: 0.6948 - 0.01 = 0.6848 m)."""


def p3a_limits(params) -> dict[str, Any]:
    from outrigger_sim.params import LEG_ORDER

    f_ext = [float(params.get(f"legs.{leg}.cylinder.max_force_extend_N")) for leg in LEG_ORDER]
    s_meas = float(params.get("sensors.stroke.measurable_max_m"))
    return {"F_extend_limit_N": f_ext, "F_basis": "legs.<leg>.cylinder.max_force_extend_N (210 bar extension)",
            "s_motor_limit_m": s_meas - STROKE_END_MARGIN_M,
            "s_basis": f"sensors.stroke.measurable_max_m {s_meas:g} - end margin {STROKE_END_MARGIN_M:g} m",
            "F_min_cylinder_N": float(params.get("control.F_min_cylinder_N"))}


def _first_run(t: np.ndarray, flag: np.ndarray, hold_s: float) -> tuple[int | None, int | None]:
    """First index where ``flag`` holds without a break for ``hold_s`` (start index, index where the
    hold is reached); (None, None) if never."""
    start = None
    for k in range(len(t)):
        if flag[k]:
            if start is None:
                start = k
            if t[k] - t[start] >= hold_s - 1e-9:
                return start, k
        else:
            start = None
    return None, None


# --- shared P3 record rules (dynamics 5.37.5 #2, control spec 284) ----------------------------------

TRACK_UTIL_MIN_NORMAL_FRACTION = 0.05
"""Track utilisation is NaN while that track's normal force is below 5 % of its settle value
(dynamics 5.37.5 #2: the ratio N -> 0 before lift-off is an artefact, P3a-10 11.2)."""
CREEP_RATE_WINDOW_S = 0.2
CREEP_RATE_LIMIT_M_S = 1.0e-4
"""Creep stop: every pad's sinkage rate over 0.2 s < 0.1 mm/s (dynamics 5.37.2 / 5.37.6, 284 J1-J2 ②)."""
PRE_LIFTOFF_FMIN_FACTOR = 1.4
"""Pre-lift-off trough window starts when the leg force first exceeds 1.4 F_min (284 J1-J2 ③, 5.37.4)."""


def mask_track_utilisation(util: np.ndarray, track_normal_N: np.ndarray, settle_normal_N,
                           fraction: float = TRACK_UTIL_MIN_NORMAL_FRACTION) -> np.ndarray:
    """``util`` (n, 2) with NaN where the track normal (n, 2) is below ``fraction`` x the settle
    value of that track (a track with settle value <= 0 is NaN throughout)."""
    u = np.array(util, dtype=float, copy=True).reshape(-1, 2)
    n = np.asarray(track_normal_N, dtype=float).reshape(-1, 2)
    ref = np.asarray(settle_normal_N, dtype=float).reshape(2)
    low = (n < fraction * ref[None, :]) | (ref[None, :] <= 0.0)
    u[low] = np.nan
    return u


def _nan_stats(u: np.ndarray, t: np.ndarray) -> dict[str, Any]:
    out: dict[str, Any] = {"max": [], "t_max_s": []}
    for j in range(u.shape[1]):
        col = u[:, j]
        if np.isfinite(col).any():
            k = int(np.nanargmax(col))
            out["max"].append(float(col[k]))
            out["t_max_s"].append(float(t[k]))
        else:
            out["max"].append(None)
            out["t_max_s"].append(None)
    return out


def crawler_departure(t: np.ndarray, crawler_n: np.ndarray, weight_N: float, *, t_from_s: float | None = None,
                      fraction: float = P3A_OFF_FRACTION, hold_s: float = P3A_OFF_HOLD_S) -> dict[str, Any]:
    """Crawler departure by the P3a-2 rule (crawler SCM normal < ``fraction`` W for ``hold_s``
    without a break), searched from ``t_from_s``: start time (= departure), confirmation time,
    the first recontact (normal >= ``fraction`` W) after the confirmation and the crawler normal
    maximum after it."""
    t = np.asarray(t, dtype=float)
    cn = np.asarray(crawler_n, dtype=float)
    lim = fraction * weight_N
    sel = np.ones(len(t), bool) if t_from_s is None else t >= t_from_s - 1e-12
    idx = np.nonzero(sel)[0]
    out: dict[str, Any] = {"rule": f"crawler SCM normal < {fraction:g} W ({lim:.0f} N) for {hold_s:g} s "
                                   "(P3a-2, dynamics 5.36.5)", "departed": False}
    if not idx.size:
        return out
    k0, k1 = _first_run(t[idx], cn[idx] < lim, hold_s)
    if k0 is None:
        return out
    ks, kc = int(idx[k0]), int(idx[k1])
    after = t >= t[kc] - 1e-12
    back = np.nonzero(after & (cn >= lim))[0]
    out.update(departed=True, t_departure_s=float(t[ks]), t_confirmed_s=float(t[kc]),
               recontact_t_s=float(t[back[0]]) if back.size else None,
               # rising edges of "loaded" after the confirmation row (that row is below the limit)
               recontact_count=int(np.count_nonzero(np.diff((after & (cn >= lim)).astype(np.int8)) == 1)),
               crawler_normal_max_after_confirm_N=float(cn[after].max()))
    return out


P31_TRANSIENT_MAX_S = 0.5
P31_TRANSIENT_MAX_W = 0.15
P31_TRANSIENT_FLAG = "P3-1_transient_recontact"
"""User decision U-S9-G6d = (가) (2026-10-28, spec rev. 75 393): a recontact after the crawler departure
confirmation that lasts <= 0.5 s, ends before the LOC and peaks <= 0.15 W is a FLAG; any other recontact
(after the LOC, longer, larger, or not ended before the LOC / no LOC) fails P3-1. W = the P3-1 / P3a-2 W."""


P31_CHATTER_FLAG = "P3-1_threshold_chatter"
"""User decision Q-G (2026-10-29, spec 423.3): a recontact after the LOC that starts within
``CHATTER_AFTER_LOC_S`` of it, lasts <= ``CHATTER_MAX_DURATION_S`` and peaks <= ``CHATTER_MAX_OVER_THRESHOLD`` x the
departure limit (0.01 W, the same W) is class ``threshold_chatter`` = FLAG; anything else after the LOC stays
``strict_fail``. The READY-window crawler-zero clause is unchanged (strict)."""
_CHATTER_DEFAULTS = {"CHATTER_AFTER_LOC_S": 1.0, "CHATTER_MAX_DURATION_S": 0.1, "CHATTER_MAX_OVER_THRESHOLD": 1.2,
                     "TIME_TOLERANCE_S": 1e-9}
"""Spec 423.4 values; the shared module ``04_scripts/03_control/s9/late_loc_rule.py`` (python) is the source once it
defines them (:func:`chatter_constants`); these defaults carry the same names until then."""
_LATE_LOC_RULE = ROOT / "04_scripts" / "03_control" / "s9" / "late_loc_rule.py"


def chatter_constants() -> dict[str, Any]:
    """Q-G constants from ``late_loc_rule`` (loaded by file path, no sys.path change) when it defines all three,
    else :data:`_CHATTER_DEFAULTS`; ``source`` names which (recorded in the rule block)."""
    cached = getattr(chatter_constants, "_cache", None)
    if cached is not None:
        return cached
    vals, source = dict(_CHATTER_DEFAULTS), "run_S9 defaults (late_loc_rule.py has no CHATTER_* constants)"
    try:
        import importlib.util  # noqa: PLC0415

        mod = sys.modules.get("late_loc_rule")
        if mod is None or not all(hasattr(mod, k) for k in vals):
            spec = importlib.util.spec_from_file_location("_late_loc_rule_constants", _LATE_LOC_RULE)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # light module: numpy / sys / pathlib at import (run_S9 lazily)
        if all(hasattr(mod, k) for k in vals):
            vals = {k: float(getattr(mod, k)) for k in vals}
            source = "04_scripts/03_control/s9/late_loc_rule.py"
    except Exception as e:  # noqa: BLE001 - fall back to the spec values
        source = f"run_S9 defaults (late_loc_rule import failed: {type(e).__name__})"
    out = {**vals, "source": source}
    chatter_constants._cache = out
    return out


def recontact_events(t: np.ndarray, crawler_n: np.ndarray, weight_N: float, departure: dict[str, Any],
                     t_loc_s: float | None, *, fraction: float = P3A_OFF_FRACTION,
                     t_ready_s: float | None = None) -> dict[str, Any]:
    """Every recontact after the departure confirmation (crawler SCM normal >= ``fraction`` W, the P3-1 /
    P3a-2 limit): start, end (first row back below the limit; None = still loaded at the run end),
    duration, maximum normal [N] and / W, ended before the LOC, class ``transient_flag`` /
    ``threshold_chatter`` / ``strict_fail`` (:data:`P31_TRANSIENT_FLAG`, :data:`P31_CHATTER_FLAG` rules). ``pass``
    = no strict-fail event; ``flags`` = the FLAG of each class present. Absolute times [s]."""
    cc = chatter_constants()
    after_s, dur_max, over = cc["CHATTER_AFTER_LOC_S"], cc["CHATTER_MAX_DURATION_S"], cc["CHATTER_MAX_OVER_THRESHOLD"]
    tol = cc["TIME_TOLERANCE_S"]
    limit = fraction * weight_N
    out: dict[str, Any] = {"rule": f"U-S9-G6d + Q-G chatter: before the LOC, duration <= {P31_TRANSIENT_MAX_S:g} s, "
                                   f"ended before the LOC, max <= {P31_TRANSIENT_MAX_W:g} W -> transient FLAG; after "
                                   f"the LOC, start <= t_LOC + {after_s:g} s, duration <= {dur_max:g} s, max <= "
                                   f"{over:g} x limit, start < READY -> threshold_chatter FLAG (spec 423.3, = "
                                   "late_loc_rule.is_threshold_chatter); else strict fail",
                           "limit_N": limit, "weight_N": weight_N, "t_loc_s": t_loc_s, "t_ready_s": t_ready_s,
                           "chatter": {"after_loc_s": after_s, "max_duration_s": dur_max, "max_over_limit": over,
                                       "max_normal_N": over * limit, "time_tolerance_s": tol,
                                       "constants_source": cc["source"]},
                           "events": [], "pass": True, "flags": []}
    t_c = departure.get("t_confirmed_s")
    if not departure.get("departed") or t_c is None:
        return out
    t = np.asarray(t, float)
    cn = np.asarray(crawler_n, float)
    on = (t >= t_c - 1e-12) & (cn >= fraction * weight_N)
    k = 0
    n = len(t)
    while k < n:
        if not on[k]:
            k += 1
            continue
        k1 = k
        while k1 < n and on[k1]:
            k1 += 1
        t_start = float(t[k])
        t_end = float(t[k1]) if k1 < n else None
        dur = (t_end if t_end is not None else float(t[-1])) - t_start
        peak = float(cn[k:k1].max())
        before_loc = bool(t_loc_s is not None and t_end is not None and t_end <= t_loc_s + 1e-12)
        transient = bool(t_end is not None and dur <= P31_TRANSIENT_MAX_S + 1e-12 and before_loc
                         and peak <= P31_TRANSIENT_MAX_W * weight_N)
        # Q-G (spec 423.3): after the LOC, early, short and small
        chatter = bool(not transient and t_loc_s is not None and t_end is not None
                       and t_loc_s + tol < t_start <= t_loc_s + after_s + tol
                       and dur <= dur_max + tol and peak <= over * limit
                       and (t_ready_s is None or t_start < t_ready_s))
        out["events"].append({"t_start_s": t_start, "t_end_s": t_end, "duration_s": dur, "max_normal_N": peak,
                              "max_over_W": peak / weight_N, "max_over_limit": peak / limit,
                              "ended_before_loc": before_loc,
                              "start_after_loc_s": None if t_loc_s is None else t_start - t_loc_s,
                              "class": "transient_flag" if transient else ("threshold_chatter" if chatter
                                                                           else "strict_fail")})
        k = k1
    classes = [e["class"] for e in out["events"]]
    out["pass"] = "strict_fail" not in classes
    out["flags"] = ([P31_TRANSIENT_FLAG] if "transient_flag" in classes else []) + (
        [P31_CHATTER_FLAG] if "threshold_chatter" in classes else [])
    return out


def sinkage_rate(t: np.ndarray, sinkage_m: np.ndarray, window_s: float = CREEP_RATE_WINDOW_S) -> np.ndarray:
    """Backward-difference sinkage rate over ``window_s`` [m/s] (+ = deeper), (n, legs); NaN for
    the first ``window_s`` of the series."""
    t = np.asarray(t, dtype=float)
    s = np.asarray(sinkage_m, dtype=float).reshape(len(t), -1)
    j = np.searchsorted(t, t - window_s + 1e-9, side="right") - 1  # last row at least window_s back
    valid = j >= 0
    j = np.maximum(j, 0)
    rate = np.full_like(s, np.nan)
    rate[valid] = (s[valid] - s[j[valid]]) / (t[valid, None] - t[j[valid], None])
    return rate


def creep_stop(t: np.ndarray, sinkage_m: np.ndarray, t_from_s: float | None, *,
               window_s: float = CREEP_RATE_WINDOW_S, limit_m_s: float = CREEP_RATE_LIMIT_M_S) -> dict[str, Any]:
    """Creep stop after ``t_from_s`` (lift-off): pad sinkage rate over ``window_s`` (backward
    difference, + = deeper) of every pad < ``limit_m_s``. ``t_first_s`` = first such time,
    ``t_final_s`` = start of the last stretch that holds to the end of the series (the P3-4 end
    window starts there). Also the rate maxima and the rates at lift-off + 1 / 2 / 4 s."""
    t = np.asarray(t, dtype=float)
    out: dict[str, Any] = {"rule": f"all pads: sinkage rate over {window_s:g} s < {limit_m_s * 1e3:g} mm/s "
                                   "(+ = deeper; t_*_two_sided_s: |rate|), after the crawler departure",
                           "t_from_s": t_from_s, "t_first_s": None, "t_final_s": None,
                           "t_first_two_sided_s": None, "t_final_two_sided_s": None}
    if t_from_s is None or len(t) < 2:
        return out
    rate = sinkage_rate(t, sinkage_m, window_s)
    valid = np.all(np.isfinite(rate), axis=1)
    after = (t >= t_from_s - 1e-12) & valid

    def first_final(ok: np.ndarray) -> tuple[float | None, float | None]:
        k = np.nonzero(ok)[0]
        if not k.size:
            return None, None
        if not ok[-1]:
            return float(t[k[0]]), None
        bad = np.nonzero(after & ~ok)[0]
        return float(t[k[0]]), (float(t[k[0]]) if not bad.size else float(t[bad[-1] + 1]))

    out["t_first_s"], out["t_final_s"] = first_final(after & np.all(rate < limit_m_s, axis=1))
    # two-sided (control D-3, 2026-10-26): |rate| < limit, so a rebound or a rocking pad also counts
    out["t_first_two_sided_s"], out["t_final_two_sided_s"] = first_final(
        after & np.all(np.abs(rate) < limit_m_s, axis=1))
    if after.any():
        out["rate_max_after_m_s"] = np.nanmax(rate[after], axis=0).tolist()

        def at(dt):
            m = int(np.searchsorted(t, t_from_s + dt - 1e-9))
            return None if m >= len(t) or not valid[m] else rate[m].tolist()

        out["rate_at_m_s"] = {"+1": at(1.0), "+2": at(2.0), "+4": at(4.0)}
    return out


def pre_liftoff_min_force(t: np.ndarray, f_cyl: np.ndarray, f_min_N: float, t_liftoff_s: float | None, *,
                          factor: float = PRE_LIFTOFF_FMIN_FACTOR, legs=("FL", "FR", "RL", "RR")) -> dict[str, Any]:
    """Per leg: minimum F_cyl from the first time it exceeds ``factor`` F_min to the crawler
    departure (284 J1-J2 ③; dynamics 5.37.4). FLAG when < F_min (record, not a failure).
    Without a departure the window runs to the end of the series."""
    t = np.asarray(t, dtype=float)
    f = np.asarray(f_cyl, dtype=float).reshape(len(t), -1)
    end = np.ones(len(t), bool) if t_liftoff_s is None else t <= t_liftoff_s + 1e-12
    rows = []
    for i in range(f.shape[1]):
        above = np.nonzero(f[:, i] > factor * f_min_N)[0]
        if not above.size or not end[above[0]]:
            rows.append({"leg": legs[i], "t_first_above_s": None, "F_min_N": None, "t_min_s": None, "flag": False})
            continue
        w = (np.arange(len(t)) >= above[0]) & end
        k = int(np.argmin(np.where(w, f[:, i], np.inf)))
        rows.append({"leg": legs[i], "t_first_above_s": float(t[above[0]]), "F_min_N": float(f[k, i]),
                     "t_min_s": float(t[k]), "flag": bool(f[k, i] < f_min_N)})
    return {"rule": f"min F_cyl from first > {factor:g} F_min to the crawler departure; FLAG < F_min "
                    f"({f_min_N:.0f} N), record only", "window_end_s": t_liftoff_s,
            "legs": rows, "any_flag": any(r["flag"] for r in rows)}


def p3a_lift_records(rows: list[dict[str, Any]], node_rows: list[dict[str, Any]], *, t_lift_start_s: float,
                     weight_N: float, design_loads_N: list[float], limits: dict[str, Any]) -> dict[str, Any]:
    """P3a values of an open-loop lift (dynamics 5.36.5 P3a-1 ... 10) from the 1 ms machine rows.
    Values and criterion comparisons only; the pass / fail decisions are dynamics-expert's.
    Forces: SCM normals along the plane normal; F_cyl = L2b acting force (+ = extension push).
    Angles: deg, pitch > 0 nose down; changes relative to the settle end (lift start)."""
    from outrigger_sim.params import LEG_ORDER

    t = np.array([r["t_s"] for r in rows])
    crawler_n = np.array([r["scm_crawler_normal_N"] for r in rows])
    pad_n = np.array([r["scm_pad_normal_N"] for r in rows])
    f_cyl = np.array([r["F_cyl_N"] for r in rows])
    s_mot = np.array([r["s_motor_m"] for r in rows])
    rp = np.array([r["roll_pitch_deg"] for r in rows])
    z0 = np.array([r["body_pos_m"][2] for r in rows])
    sink = np.array([r["pad_sinkage_geometric_m"] for r in rows])
    tilt = _nan_array(rows, "pad_tilt_deg", 4)
    rut = _nan_array(rows, "rut_clearance_m", None)
    util = _nan_array(rows, "track_utilisation", 2)
    lift = t > t_lift_start_s + 1e-9
    i0 = int(np.argmax(lift)) - 1 if lift.any() else len(t) - 1  # last settle row = reference
    ref_rp, ref_z = rp[max(i0, 0)], z0[max(i0, 0)]
    out: dict[str, Any] = {"t_lift_start_s": t_lift_start_s, "weight_N": weight_N, "limits": limits,
                           "basis": "1 ms rows; SI, deg for angles; changes vs the last settle row "
                                    f"(t = {float(t[max(i0, 0)]):.4f} s)"}
    tl = t[lift]
    # P3a-2 crawler lift-off
    k_start, k_hold = _first_run(tl, crawler_n[lift] < P3A_OFF_FRACTION * weight_N, P3A_OFF_HOLD_S)
    lo: dict[str, Any] = {"rule": f"crawler SCM normal < {P3A_OFF_FRACTION:g} W ({P3A_OFF_FRACTION * weight_N:.0f} N) "
                                  f"for {P3A_OFF_HOLD_S:g} s", "lifted": k_start is not None}
    k_lo = None
    if k_start is not None:
        k_lo = int(np.nonzero(lift)[0][k_start])
        t_lo = float(t[k_lo])
        after = t >= float(tl[k_hold]) - 1e-12
        back = np.nonzero(after & (crawler_n >= P3A_OFF_FRACTION * weight_N))[0]
        lo.update(t_liftoff_s=t_lo, t_confirmed_s=float(tl[k_hold]), t_after_lift_start_s=t_lo - t_lift_start_s,
                  s_motor_at_liftoff_m=s_mot[k_lo].tolist(), pad_normal_at_liftoff_N=pad_n[k_lo].tolist(),
                  crawler_normal_max_after_confirm_N=float(crawler_n[after].max()),
                  recontact_after_confirm_t_s=float(t[back[0]]) if back.size else None)
    out["P3a-2_liftoff"] = lo
    # P3a-1 cylinder force peaks (lift phase) and whole-run peaks
    f_lim = np.asarray(limits["F_extend_limit_N"])
    fl = f_cyl[lift]
    kpk = np.argmax(fl, axis=0)
    out["P3a-1_force_peak"] = {
        "F_peak_N": fl.max(axis=0).tolist(), "t_peak_s": [float(tl[k]) for k in kpk],
        "pad_sinkage_at_peak_m": [float(sink[lift][k, i]) for i, k in enumerate(kpk)],
        "F_peak_whole_run_N": f_cyl.max(axis=0).tolist(), "limit_N": f_lim.tolist(),
        "peak_over_limit": (fl.max(axis=0) / f_lim).tolist(),
        "within": bool(np.all(fl.max(axis=0) <= f_lim)), "legs": list(LEG_ORDER)}
    # P3a-3 end equilibrium (last 1 s, only if entirely after the confirmed lift-off)
    eq: dict[str, Any] = {"rule": "last 1 s pad SCM normal sum / W, 1 +- 0.002, after lift-off"}
    win = t >= t[-1] - 1.0 + 1e-9
    eq.update(window_s=[float(t[win][0]), float(t[-1])], pad_normal_sum_over_weight=float(pad_n[win].sum(axis=1).mean() / weight_N),
              crawler_normal_mean_N=float(crawler_n[win].mean()),
              total_normal_over_weight=float((pad_n[win].sum(axis=1) + crawler_n[win]).mean() / weight_N),
              pad_normal_mean_N=pad_n[win].mean(axis=0).tolist())
    eq["window_after_liftoff"] = bool(lo["lifted"] and t[win][0] >= lo["t_confirmed_s"])
    eq["within"] = bool(eq["window_after_liftoff"] and abs(eq["pad_normal_sum_over_weight"] - 1.0) <= 0.002)
    out["P3a-3_end_equilibrium"] = eq
    # P3a-4 stroke
    smax = s_mot.max(axis=0)
    out["P3a-4_stroke"] = {"s_motor_max_m": smax.tolist(), "s_motor_max_all_m": float(smax.max()),
                           "s_motor_end_m": s_mot[-1].tolist(), "limit_m": limits["s_motor_limit_m"],
                           "margin_m": float(limits["s_motor_limit_m"] - smax.max()),
                           "within": bool(smax.max() <= limits["s_motor_limit_m"])}
    # P3a-5 pad tilt while loaded
    loaded = pad_n > P3A_LOADED_FRACTION * np.asarray(design_loads_N)[None, :]
    tl_max, tl_t = [], []
    for i in range(4):
        m = loaded[:, i] & np.isfinite(tilt[:, i])
        if m.any():
            k = int(np.nanargmax(np.where(m, tilt[:, i], -np.inf)))
            tl_max.append(float(tilt[k, i]))
            tl_t.append(float(t[k]))
        else:
            tl_max.append(None)
            tl_t.append(None)
    vals = [v for v in tl_max if v is not None]
    out["P3a-5_pad_tilt"] = {"rule": f"pad tilt while pad SCM normal > {P3A_LOADED_FRACTION:g} x design load N",
                             "design_loads_N": list(design_loads_N), "tilt_max_loaded_deg": tl_max,
                             "t_tilt_max_loaded_s": tl_t, "tilt_end_deg": tilt[-1].tolist(),
                             "tilt_max_all_deg": np.nanmax(tilt, axis=0).tolist(), "criterion_deg": 0.5,
                             "within": bool(vals and max(vals) <= 0.5)}
    # P3a-8 first touch SCM force rise, P3a-9 minimum cylinder force after touch
    touch, ftm = [], []
    for i in range(4):
        idx = np.nonzero(lift & (pad_n[:, i] > 0.0))[0]
        if not idx.size:
            touch.append(None)
            ftm.append(None)
            continue
        k = int(idx[0])
        tt = float(t[k])

        def at(dt_s, k=k, i=i, tt=tt):
            j = int(np.searchsorted(t, tt + dt_s - 1e-9))
            return None if j >= len(t) else float(pad_n[j, i])

        w2 = (t >= tt - 1e-12) & (t <= tt + P3A_TOUCH_WINDOW_S + 1e-9)
        touch.append({"t_touch_s": tt, "t_after_lift_start_s": tt - t_lift_start_s, "s_motor_m": float(s_mot[k, i]),
                      "F_scm_at_N": {"0.05": at(0.05), "0.1": at(0.1), "0.2": at(0.2)},
                      "F_scm_max_0p2s_N": float(pad_n[w2, i].max()), "F_cyl_at_0p2s_N": float(f_cyl[w2, i][-1]),
                      "sinkage_geometric_at_0p2s_m": float(sink[w2, i][-1])})
        after = t >= tt - 1e-12
        kmin = int(np.argmin(np.where(after, f_cyl[:, i], np.inf)))
        rec = {"F_cyl_min_after_touch_N": float(f_cyl[kmin, i]), "t_s": float(t[kmin])}
        if k_lo is not None:
            a2 = t >= t[k_lo] - 1e-12
            kk = int(np.argmin(np.where(a2, f_cyl[:, i], np.inf)))
            rec.update(F_cyl_min_after_liftoff_N=float(f_cyl[kk, i]), t_min_after_liftoff_s=float(t[kk]))
        ftm.append(rec)
    out["P3a-8_first_touch"] = {"rule": "first lift row with pad SCM normal > 0; values at +0.05 / 0.1 / 0.2 s",
                                "legs": touch}
    out["P3a-9_min_cylinder_force"] = {
        "F_min_cylinder_N": limits["F_min_cylinder_N"], "legs": ftm,
        "before_liftoff": pre_liftoff_min_force(t, f_cyl, limits["F_min_cylinder_N"],
                                                None if k_lo is None else float(t[k_lo])),
        "note": "open loop: record only (not an F_min judgement)"}
    out["creep_stop"] = creep_stop(t, sink, None if k_lo is None else float(t[k_lo]))
    # P3a-6 sinkage history (series in npz), P3a-7 attitude
    nt = np.array([n["t_s"] for n in node_rows]) if node_rows else np.array([])

    def node_at(tq):
        if not nt.size:
            return None
        j = int(np.argmin(abs(nt - tq)))
        return {"t_s": float(nt[j]), "sinkage_mean_contact_m": [s["sinkage_mean_contact_m"] for s in node_rows[j]["pad_nodes"]],
                "n_contact": [s["n_contact"] for s in node_rows[j]["pad_nodes"]]}

    out["P3a-6_sinkage"] = {"geometric_at_liftoff_m": None if k_lo is None else sink[k_lo].tolist(),
                            "geometric_end_m": sink[-1].tolist(), "geometric_max_m": sink.max(axis=0).tolist(),
                            "node_at_liftoff": None if k_lo is None else node_at(float(t[k_lo])),
                            "node_end": node_at(float(t[-1])),
                            "series": "series.npz: pad_sinkage_geometric_m (1 ms), node_sinkage_mean_contact_m (0.1 s)"}
    d_rp = rp[lift] - ref_rp
    out["P3a-7_attitude"] = {
        "settle_end_roll_pitch_deg": ref_rp.tolist(), "settle_end_z0_m": float(ref_z),
        "d_roll_range_deg": [float(d_rp[:, 0].min()), float(d_rp[:, 0].max())],
        "d_pitch_range_deg": [float(d_rp[:, 1].min()), float(d_rp[:, 1].max())],
        "t_d_pitch_min_max_s": [float(tl[int(np.argmin(d_rp[:, 1]))]), float(tl[int(np.argmax(d_rp[:, 1]))])],
        "d_roll_pitch_at_liftoff_deg": None if k_lo is None else (rp[k_lo] - ref_rp).tolist(),
        "d_roll_pitch_end_deg": (rp[-1] - ref_rp).tolist(), "end_roll_pitch_deg": rp[-1].tolist(),
        "d_z0_end_m": float(z0[-1] - ref_z),
        "end_last_1s_pitch_pp_deg": float(np.ptp(rp[win, 1])), "end_last_1s_roll_pp_deg": float(np.ptp(rp[win, 0]))}
    # P3a-10 rut clearance and track utilisation
    rc: dict[str, Any] = {"rut_clearance_end_m": None if not np.isfinite(rut[-1]) else float(rut[-1])}
    if k_lo is not None:
        a2 = (t >= t[k_lo] - 1e-12) & np.isfinite(rut)
        rc.update(rut_clearance_at_liftoff_m=float(rut[k_lo]) if np.isfinite(rut[k_lo]) else None,
                  rut_clearance_min_after_liftoff_m=float(rut[a2].min()) if a2.any() else None)
    ul = util[lift]
    track_n = np.array([r.get("scm_track_normal_raw_N", [np.nan, np.nan]) for r in rows], dtype=float)
    settle_win = (t <= t_lift_start_s + 1e-9) & (t >= t_lift_start_s - 1.0 - 1e-9)
    settle_track = track_n[settle_win].mean(axis=0) if settle_win.any() else track_n[max(i0, 0)]
    um = mask_track_utilisation(util, track_n, settle_track)[lift]
    st_unmasked, st_masked = _nan_stats(ul, tl), _nan_stats(um, tl)
    rc.update(track_utilisation_settle_end=util[max(i0, 0)].tolist(),
              track_normal_settle_N=settle_track.tolist(),
              track_utilisation_max_lift=st_masked["max"], t_track_utilisation_max_s=st_masked["t_max_s"],
              track_utilisation_max_lift_unmasked=st_unmasked["max"],
              t_track_utilisation_max_unmasked_s=st_unmasked["t_max_s"],
              track_utilisation_rule=f"NaN while the track normal < {TRACK_UTIL_MIN_NORMAL_FRACTION:g} x its settle "
                                     "value (mean of the last 1 s of the settle; dynamics 5.37.5 #2)",
              track_order="track_normals order (2 tracks)")
    out["P3a-10_rut_track"] = rc
    out["checks"] = {
        "P3a-1_within": out["P3a-1_force_peak"]["within"], "P3a-2_lifted": lo["lifted"],
        "P3a-3_within": eq["within"], "P3a-4_within": out["P3a-4_stroke"]["within"],
        "P3a-5_within": out["P3a-5_pad_tilt"]["within"],
        "abort": bool((not out["P3a-1_force_peak"]["within"]) or (not out["P3a-4_stroke"]["within"])),
        "note": "values vs criteria; decisions are dynamics-expert's"}
    return out


# --- P3 record keys (dynamics 5.34.6) -------------------------------------------------------------------


def model_weight_N(params, mass_scale: float = 1.0) -> float:
    """Superstructure (x ``mass_scale``, :func:`apply_mass_scale`) + leg moving parts, times g [N]."""
    return (params.superstructure.mass_properties.mass_kg * float(mass_scale)
            + sum(leg.moving_part.mass_kg for leg in params.legs)) * G


P3_HOLD_WINDOW_S = 10.0
TOUCH_TILT_ROWS = 10


def p3_records(rows: list[dict[str, Any]], weight_N: float, t_departure_s: float | None = None) -> dict[str, Any]:
    """P3 record values from the 10 Hz S9 rows (dynamics 5.34.6 P3-S1 ... S4, crawler rocking, pad
    tilt). Records only: the Bekker prediction of P3-S1 (node formula of P1 V16a) and every pass /
    fail decision are dynamics-expert's. Node sinkage = mean of the contact nodes inside the pad
    polygon (``pad_node_stats``). ``t_departure_s``: crawler departure by the P3a-2 rule from the
    1 ms series (:func:`crawler_departure`); None = the same rule on the 10 Hz rows."""
    if not rows:
        return {"rows": 0}
    t = np.array([r["t_s"] for r in rows])
    phase = [str(r.get("c2_phase")) for r in rows]
    rp = np.array([r["roll_pitch_deg"] for r in rows])
    crawler_n = np.array([r["scm_crawler_normal_N"] for r in rows])
    pad_n = np.array([r["scm_pad_normal_N"] for r in rows])

    def node_sink(r):
        return [np.nan if s["sinkage_mean_contact_m"] is None else s["sinkage_mean_contact_m"] for s in r["pad_nodes"]]

    sink = np.array([node_sink(r) for r in rows])
    out: dict[str, Any] = {"rows": len(rows), "basis": "10 Hz rows of run_S9 level; SI, deg for angles"}
    # crawler rocking at TOUCH: first 10 control periods of raw (truth) tilt
    touch = [k for k, p in enumerate(phase) if p == "touch"]
    if touch:
        k0 = touch[0]
        seg = rp[k0:k0 + TOUCH_TILT_ROWS]
        settle = rp[max(k0 - 1, 0)]
        out["touch_rocking"] = {"t_start_s": float(t[k0]), "roll_pp_deg": float(np.ptp(seg[:, 0])),
                                "pitch_pp_deg": float(np.ptp(seg[:, 1])),
                                "mean_minus_settle_deg": (seg.mean(axis=0) - settle).tolist(),
                                "note": "dynamics 5.34.6: ignore when <= 0.02 deg"}
    if t_departure_s is None:
        d = crawler_departure(t, crawler_n, weight_N)
        t_departure_s = d.get("t_departure_s")
    kd = None
    if t_departure_s is not None:
        later = np.nonzero(t >= t_departure_s - 1e-9)[0]
        kd = int(later[0]) if later.size else None
    out["departure_rule"] = "P3a-2 rule (crawler SCM normal < 1 % W for 0.1 s), first 10 Hz row at / after it"
    if kd is not None:
        f_loc = pad_n[kd]
        f_max = pad_n[kd:].max(axis=0)
        out["S1_after_departure"] = {"t_departure_s": float(t[kd]), "F_LOC_N": f_loc.tolist(), "F_max_N": f_max.tolist(),
                                     "dF_N": (f_max - f_loc).tolist(),
                                     "node_sinkage_departure_m": sink[kd].tolist(), "node_sinkage_end_m": sink[-1].tolist(),
                                     "dz_node_m": (sink[-1] - sink[kd]).tolist()}
        clear = [r["rut_clearance_m"] for r in rows[kd:] if r.get("rut_clearance_m") is not None]
        out["S4_rut_clearance"] = {"min_after_departure_m": float(min(clear)) if clear else None,
                                   "end_m": rows[-1].get("rut_clearance_m"),
                                   "pad_node_sinkage_end_m": sink[-1].tolist(), "criterion_m": 0.025}
    done = [k for k, p in enumerate(phase) if p == "done"]
    if done:
        kq = done[0]
        out["S3_attitude_after_done"] = {"t_done_s": float(t[kq]), "d_roll_deg": float(rp[-1, 0] - rp[kq, 0]),
                                         "d_pitch_deg": float(rp[-1, 1] - rp[kq, 1]), "criterion_deg": 0.03}
        hold = t >= t[-1] - P3_HOLD_WINDOW_S
        if t[-1] - t[kq] >= P3_HOLD_WINDOW_S:
            before = pad_n[:np.argmax(hold)].max(axis=0) if np.argmax(hold) > 0 else pad_n[0]
            out["S2_hold_settlement"] = {"window_s": [float(t[hold][0]), float(t[-1])],
                                         "dz_node_m": (sink[-1] - sink[hold][0]).tolist(),
                                         "F_max_in_window_N": pad_n[hold].max(axis=0).tolist(),
                                         "F_max_before_window_N": before.tolist(), "criterion_m_per_10s": 1e-4}
        else:
            out["S2_hold_settlement"] = {"note": f"less than {P3_HOLD_WINDOW_S:g} s after DONE"}
    tilt = [r.get("pad_tilt_max_deg") for r in rows if r.get("pad_tilt_max_deg") is not None]
    out["pad_tilt_max_deg"] = tilt[-1] if tilt else None
    out["pad_tilt_criterion_deg"] = 0.5
    return out


# --- C2 levelling (P3b), gated ------------------------------------------------------------------------

IMU_SAMPLE_PERIOD_S = 0.01
"""R8 IMU sample period (10 ms; run_S6C.IMU_SAMPLE_PERIOD_S)."""
STEP_SERIES_S = 1.0e-3
"""Closed-loop truth series rate: P3-3 '1 ms' F_cyl minimum, P3a-2 departure rule, creep stop."""
LEGS = ("FL", "FR", "RL", "RR")
P3B_ATTITUDE_LIMIT_DEG = 0.2
"""P3-4 main judgement: steady end attitude +-0.2 deg (CLAUDE.md accuracy row, spec 284 rev. 61 suppl.)."""
P3B_DEADBAND_DEG = 0.03
"""Completion dead band 0.03 deg: record only (spec 284)."""
P3B_MIN_WINDOW_S = 5.0
"""P3-4 judgement window shorter than this -> ``window_short`` FLAG (control D-3)."""
P3B_MOUNT_SHARE_DEG = 0.02
"""IMU mounting share of the 0.2 deg budget (CLAUDE.md accuracy row)."""
P3B_BUDGET_RESIDUAL_DEG = 0.04
"""0.2 - 0.02 mount - 0.14 IMU zero error = 0.04 deg left for control (``budget_residual_le_0p04``, record only)."""
P3B_END_WINDOW_S = 1.0
P3B_DONE_SHIFT_S = 5.0
P3B_READY_LIMIT_S = 90.0
"""P3-6 READY limit of a flat case outside the soft-soil pad-B row (spec 421.1; former single limit)."""
P3B_READY_SLOPE_LIMIT_S = 120.0
P3B_READY_SOFT_PAD_B_LIMIT_S = 100.0
P3B_READY_SOFT_SOILS = ("J1", "J2", "S1")
P3B_READY_PAD_B_VARIANT = "dwg_rear250"


def p36_ready_limit(case: dict[str, Any] | None) -> dict[str, Any]:
    """P3-6 READY limit of spec 421.1 (decision Q-A; first matching row, = the harness ``s9_soil_slope.ready_limit_s``):
    floor slope (roll or pitch != 0) 120 s; flat with pad B (``dwg_rear250``) and both rear pads (RL, RR) on J1 / J2 /
    S1 100 s; any other flat case 90 s. ``case``: the level args (``soil``, ``pad_variant``, ``floor_roll`` /
    ``floor_pitch`` [deg], ``soil_patch`` ``LEG:SET``); None or missing keys = flat G1-type (90 s)."""
    c = case or {}
    roll, pitch = float(c.get("floor_roll") or 0.0), float(c.get("floor_pitch") or 0.0)
    patch = parse_soil_patch(c.get("soil_patch"))
    base = c.get("soil")
    rear = [patch[1] if patch is not None and patch[0] == leg else base for leg in ("RL", "RR")]
    if roll != 0.0 or pitch != 0.0:
        limit, row = P3B_READY_SLOPE_LIMIT_S, "slope"
    elif c.get("pad_variant") == P3B_READY_PAD_B_VARIANT and all(s in P3B_READY_SOFT_SOILS for s in rear):
        limit, row = P3B_READY_SOFT_PAD_B_LIMIT_S, "flat, pad B, both rear pads on J1 / J2 / S1"
    else:
        limit, row = P3B_READY_LIMIT_S, "flat, other"
    return {"limit_s": limit, "row": row, "rear_pad_soils": rear, "floor_deg": [roll, pitch],
            "pad_variant": c.get("pad_variant"),
            "rule": "spec 421.1 (Q-A): slope 120 s / flat pad B both rear pads J1-J2-S1 100 s / other flat 90 s"}


P3B_RUT_CLEARANCE_MIN_M = 0.025
P3B_LOC_AFTER_DEPARTURE_S = 2.0
P3B_LIFTOFF_TRANSIENT_S = 8.0
P3B_GUARD_MARGIN_N = 5000.0
P3B_POST_LIFTOFF_ATTITUDE_DEG = 1.0
P3B_READY_CRAWLER_WINDOW_S = 10.0
P3B_TOUCH_ANNOTATE_S = 0.2
W61_FALSE_RELEVEL_FACTOR = 3.0
W61_REAL_LOW_MARGIN_N = 5000.0


def level_c2_config(allow_soil_off: bool, config: Any = None) -> tuple[Any, dict[str, Any]]:
    """C2 config of ``level`` (R8 preset ``C2Config().with_10hz_d1()`` unless ``config`` is given)
    and the soil-response guard: ``soil.enable`` False raises SystemExit unless ``allow_soil_off``
    (``--allow-current-c2``). Since U-S9-C1 / P-S9-8 the preset has the soil response on, so the
    guard only stops a preset that lost it (or a deliberate soil-off comparison config)."""
    if config is None:
        from outrigger_sim.control.c2 import C2Config

        config = C2Config().with_10hz_d1()
    soil = getattr(config, "soil", None)
    enabled = bool(getattr(soil, "enable", False))
    if not enabled and not allow_soil_off:
        raise SystemExit("C2 config has the soil response off (soil.enable False; control spec rev. 57-59 285, "
                         "U-S9-C1: the R8 preset C2Config().with_10hz_d1() has it on). A soil-off C2 is expected to "
                         "fail on J1 B, J2 B, S1 (281); --allow-current-c2 runs it anyway (comparison only)")
    return config, {"preset": "C2Config().with_10hz_d1()", "soil_enable": enabled,
                    "soil_settings": soil.to_meta() if hasattr(soil, "to_meta") else None,
                    "allow_soil_off": bool(allow_soil_off)}


PRESSURE_GRADES = ("ideal", "normal", "conservative", "old_worst")
IMU_GRADES = ("ideal", "good_zeroed", "normal_zeroed", "normal_zeroed_repeatability", "normal_as_shipped")


def level_sensor_setup(pressure_grade: str, imu_grade: str, config: Any) -> tuple[Any, Any, Any, dict[str, Any]]:
    """Sensors of ``level`` (control D-1, 2026-10-26): IMU of ``imu_grade`` at 10 ms samples;
    pressure / stroke sensors ``LegSensorConfig()`` for ``ideal``, else
    ``wika_a10_leg_sensor_config(grade)`` (WIKA A-10 grade errors, stroke noise 0.1 mm). The
    CHECK zero calibration stays as the preset. A non-ideal IMU sets the C2 target
    ``gyro_noise_std_rad_s`` to the grade value at the control period (run_S6C.controller_config).
    Returns (imu config, leg config, C2 config, meta)."""
    from dataclasses import replace

    from outrigger_sim.sensors.hydraulic import LegSensorConfig, wika_a10_leg_sensor_config
    from outrigger_sim.sensors.imu import imu_config_for_grade

    if pressure_grade not in PRESSURE_GRADES:
        raise ValueError(f"pressure grade must be one of {PRESSURE_GRADES}: {pressure_grade!r}")
    imu = imu_config_for_grade(imu_grade, sample_period_s=IMU_SAMPLE_PERIOD_S)
    legs = LegSensorConfig() if pressure_grade == "ideal" else wika_a10_leg_sensor_config(pressure_grade)
    gyro_sigma = None
    if imu_grade != "ideal":
        # sigma_g of one delivered gyro value = mean of the IMU samples of a period (run_S6C 878)
        gyro_sigma = float(imu_config_for_grade(imu_grade, sample_period_s=config.period_s).gyro_noise_std_rad_s)
        config = replace(config, target=replace(config.target, gyro_noise_std_rad_s=gyro_sigma))
    zc = getattr(config, "zero_calibration", None)
    meta = {"pressure_grade": pressure_grade, "imu_grade": imu_grade,
            "leg_sensors": legs.to_meta(), "leg_sensor_source": "LegSensorConfig()" if pressure_grade == "ideal"
            else f"wika_a10_leg_sensor_config({pressure_grade!r})",
            "imu_sample_period_s": IMU_SAMPLE_PERIOD_S,
            "c2_target_gyro_noise_std_rad_s": float(config.target.gyro_noise_std_rad_s),
            "c2_target_gyro_noise_set_from_grade": gyro_sigma is not None,
            "zero_calibration_mode": None if zc is None else str(zc.mode)}
    return imu, legs, config, meta


def zero_calibration_outcome(controller_meta: dict[str, Any]) -> dict[str, Any]:
    """Per-leg CHECK zero calibration result of a run (C2 meta ``zero_calibration``): status,
    success (``calibrated``), offsets in use; ``all_calibrated`` over the four legs. Spec 416.3 variant D
    (2026-10-29): ``return_timeout_tolerance_m`` (C2 meta ``zero_calibration.settings``; None = key absent =
    the old rule or a pre-416 run), ``return_within_tolerance_m`` (legs accepted at the retract time-out
    -> smallest displacement [m]; None = not recorded by the code of the run) and ``move_skipped_legs``."""
    zc = controller_meta.get("zero_calibration") or {}
    res = zc.get("result") or {}
    legs = res.get("legs") or {}
    rows = {leg: {"status": (legs.get(leg) or {}).get("status"), "reason": (legs.get(leg) or {}).get("reason"),
                  "success": (legs.get(leg) or {}).get("status") == "calibrated"} for leg in LEGS}
    return {"is_active": zc.get("is_active"), "legs": rows, "all_calibrated": all(r["success"] for r in rows.values()),
            "offsets_N": zc.get("offsets_N"), "t_start_s": res.get("t_start_s"),
            "t_end_s": res.get("t_end_s"),
            "return_timeout_tolerance_m": (zc.get("settings") or {}).get("return_timeout_tolerance_m"),
            "return_within_tolerance_m": res.get("return_within_tolerance_m"),
            "move_skipped_legs": [leg for leg in LEGS if rows[leg]["status"] == "skipped"
                                  and rows[leg]["reason"] == "move"]}


CODE_STATE_MODULES = ("outrigger_sim.control.c2", "outrigger_sim.control.zero_calibration")
"""Controller modules whose file SHA-256 a ``level`` run records at its start (spec 420.4 code state)."""
CODE_STATE_RULES = ("slope_clearance_margin", "liftoff_window_reapproach", "zero_calibration_return_tol")
"""Spec 420.1 rules 1-3 (2026-10-29): P-S8-31 E3c10, P-S8-32 LWa, zero calibration variant D."""


def code_state_files(modules: tuple[str, ...] = CODE_STATE_MODULES) -> dict[str, Any]:
    """SHA-256, size and modification time (UTC ISO) of the imported controller module files
    (``module.__file__``), taken right after the import at the run start (spec 420.4 (1): runs of
    uncommitted code are told apart by these hashes)."""
    import importlib  # noqa: PLC0415

    out: dict[str, Any] = {}
    for name in modules:
        p = Path(importlib.import_module(name).__file__)
        st = p.stat()
        parts = p.parts
        rel = "/".join(parts[parts.index("03_src"):]) if "03_src" in parts else str(p)
        out[name] = {"path": rel, "sha256": _file_sha256(p), "size": st.st_size,
                     "mtime_utc": _dt.datetime.fromtimestamp(st.st_mtime, _dt.timezone.utc).isoformat(timespec="seconds")}
    out["taken_utc"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    return out


def lwa_on_from_meta(controller_meta: dict[str, Any] | None) -> bool | None:
    """P-S8-32 LWa on in the run's C2 meta (``liftoff_window_reapproach.mode == "restart"``); None when
    the meta has no such key (code before P-S8-32)."""
    lw = (controller_meta or {}).get("liftoff_window_reapproach")
    return None if lw is None else lw.get("mode") == "restart"


def code_state_from_meta(controller_meta: dict[str, Any] | None) -> dict[str, Any]:
    """Which of the spec 420.1 rules the run's controller had, from its C2 meta alone (works on
    results written before this record existed): ``slope_clearance_margin`` key (P-S8-31) and its
    ``settings.enable``, ``liftoff_window_reapproach`` key (P-S8-32) and its ``mode``, the zero
    calibration ``settings.return_timeout_tolerance_m`` (416.3, present only when set). ``state``:
    ``pre_impl`` (none of the three present, f062051 controller), ``impl_final_rules`` (all three on:
    E3c10 enabled, LWa ``restart``, tolerance set), else ``impl_partial`` (``missing`` lists the rules
    that are absent or off). The meta cannot tell committed from uncommitted code; the file hashes
    of :func:`code_state_files` (``files_at_start``) do."""
    cm = controller_meta or {}
    scm = cm.get("slope_clearance_margin")
    lw = cm.get("liftoff_window_reapproach")
    zc_set = (cm.get("zero_calibration") or {}).get("settings") or {}
    tol = zc_set.get("return_timeout_tolerance_m")
    present = {"slope_clearance_margin": scm is not None, "liftoff_window_reapproach": lw is not None,
               "zero_calibration_return_tol": "return_timeout_tolerance_m" in zc_set}
    on = {"slope_clearance_margin": bool(scm and (scm.get("settings") or {}).get("enable")),
          "liftoff_window_reapproach": bool(lw and lw.get("mode") == "restart"),
          "zero_calibration_return_tol": tol is not None}
    if not any(present.values()):
        state = "pre_impl"
    elif all(on.values()):
        state = "impl_final_rules"
    else:
        state = "impl_partial"
    return {"state": state, "rules_present": present, "rules_on": on,
            "missing": [k for k in CODE_STATE_RULES if not on[k]],
            "slope_clearance_margin": scm, "liftoff_window_reapproach": lw,
            "zero_calibration_return_timeout_tolerance_m": tol,
            "basis": "C2 meta keys (spec 420.4 (1)); committed vs uncommitted only by files_at_start SHA-256"}


def lifted_reapproach_meta(config: Any) -> dict[str, Any] | None:
    """All fields of ``config.r8.lifted_reapproach`` (P-S9-10 ``max_duration_s`` included)."""
    import dataclasses

    lr = getattr(getattr(config, "r8", None), "lifted_reapproach", None)
    if lr is None or not dataclasses.is_dataclass(lr):
        return None
    return {f.name: (getattr(lr, f.name).value if hasattr(getattr(lr, f.name), "value") else getattr(lr, f.name))
            for f in dataclasses.fields(lr)}


class StepSeries:
    """Truth series of the S9 model every ``every_steps`` physics steps (a ``run_closed_loop``
    ``step_hook``; :meth:`record` also works alone). Forces along the SCM plane normal [N],
    F_cyl = L2b acting force (+ = extension push), sinkage + = pad bottom centre below the
    plane [m], roll / pitch of the superstructure [deg] (pitch > 0 nose down), z of the body
    origin [m]; track utilisation = |anchor tangential| / Coulomb limit (raw, unmasked)."""

    def __init__(self, model: Any, every_steps: int, capacity: int) -> None:
        self.model = model
        self.every = max(1, int(every_steps))
        self._k = 0
        self.n = 0
        cap = max(16, int(capacity))
        self.data = {"t_s": np.empty(cap), "scm_crawler_normal_N": np.empty(cap),
                     "scm_crawler_patches": np.empty(cap), "scm_track_normal_raw_N": np.empty((cap, 2)),
                     "track_utilisation": np.empty((cap, 2)), "scm_pad_normal_N": np.empty((cap, 4)),
                     "F_cyl_N": np.empty((cap, 4)), "s_motor_m": np.empty((cap, 4)),
                     "pad_sinkage_geometric_m": np.empty((cap, 4)), "roll_pitch_deg": np.empty((cap, 2)),
                     "z_origin_m": np.empty(cap)}

    def __call__(self, engine: Any = None) -> None:
        self._k += 1
        if self._k % self.every == 0:
            self.record()

    def record(self) -> None:
        from outrigger_sim.frames import roll_pitch_from_quat

        m = self.model
        if self.n >= len(self.data["t_s"]):
            self.data = {k: np.concatenate([v, np.empty_like(v)]) for k, v in self.data.items()}
        i, d, nrm = self.n, self.data, m.normal_world
        d["t_s"][i] = float(m.system.GetChTime())
        d["scm_crawler_normal_N"][i] = float(m.forces.sup_force_N @ nrm)
        d["scm_crawler_patches"][i] = float(m.crawler_terrain.GetNumContactPatches())
        tn = np.asarray(m.track_normals.last_raw_N, dtype=float)
        d["scm_track_normal_raw_N"][i] = tn
        if m.crawler_bushing is not None:
            ft = m.crawler_bushing.tangential_force_world_N()
            lim = m.crawler_bushing.tangential_limit_N(tn)
            d["track_utilisation"][i] = [float(np.linalg.norm(ft[k]) / lim[k]) if lim[k] > 0 else np.nan
                                         for k in range(2)]
        else:
            d["track_utilisation"][i] = np.nan
        d["scm_pad_normal_N"][i] = m.forces.pad_force_N @ nrm
        d["F_cyl_N"][i] = np.asarray(m.actuator.acting_force_N, dtype=float)
        d["s_motor_m"][i] = [float(mo.GetMotorPos()) for mo in m.motors]
        d["pad_sinkage_geometric_m"][i] = m.pad_sinkage_m()
        q = m.superstructure.GetRot()
        d["roll_pitch_deg"][i] = np.degrees(np.asarray(roll_pitch_from_quat(np.array([q.e0, q.e1, q.e2, q.e3])),
                                                       dtype=float))
        d["z_origin_m"][i] = float(m.superstructure.TransformPointLocalToParent(m.origin_in_cog_frame_ch).z)
        self.n += 1

    def arrays(self) -> dict[str, np.ndarray]:
        return {k: v[: self.n].copy() for k, v in self.data.items()}


COMPLETION_SERIES_NAME = "completion_series.npz"
P3B_EXT_EVENTS = ("INFO_LOC_CLEARANCE_ANCHOR", "INFO_TWIST_UNSETTLED", "WARN_LIFT_STROKE_LIMITED",
                  "FAULT_STROKE_END", "FAULT_LIFT_STROKE_LIMIT", "fault_reground_start", "fault_reground_end",
                  "INFO_LIFT_PAUSED", "INFO_LOC_CLEARANCE_MARGIN", "INFO_LOC_WINDOW_RESTART",
                  "INFO_PRESSURE_ZERO_RETURN_TOL", "WARN_PRESSURE_ZERO_SKIPPED", "leg_reapproach_start")
"""Controller events counted by :func:`p3b_ext_records` (name or ``name:<suffix>``). ``INFO_TWIST_UNSETTLED``
is the P-S8-29 V2b event, ``INFO_LIFT_PAUSED:<leg>`` the P-S8-30 pre-LOC lift slowdown (bee0693).
2026-10-29 (spec 414 / 416 / 419 / 420): ``INFO_LOC_CLEARANCE_MARGIN:<mm>`` (P-S8-31 E3c10),
``INFO_LOC_WINDOW_RESTART:<legs>`` (P-S8-32 LWa), ``INFO_PRESSURE_ZERO_RETURN_TOL:<leg>:<mm>`` (zero
calibration variant D), ``WARN_PRESSURE_ZERO_SKIPPED:<leg>:<reason>`` and ``leg_reapproach_start:<leg>``
(420.4 equivalence checks)."""
P3B_EXT_EVENT_TIMES = ("INFO_LIFT_PAUSED",)
"""Events whose times (relative to the loop start) and names are listed too."""
P3B_EXT_RULE_EVENT_TIMES = ("INFO_LOC_CLEARANCE_MARGIN", "INFO_LOC_WINDOW_RESTART", "INFO_PRESSURE_ZERO_RETURN_TOL",
                            "WARN_PRESSURE_ZERO_SKIPPED")
"""Spec 420 rule events listed with their times in ``p3b_ext.rule_event_times_rel_s`` (kept apart from
``event_times_rel_s`` so the former block keeps its keys)."""
COMPLETION_REASONS = ("attitude", "clearance", "twist", "loc")


class CompletionProbe:
    """Per control instant (``on_control``, after the controller update), read-only: the twist load
    ``D = n^T F`` of the controller's last reading (raw, and the twist-loop low-pass output when the
    preset has one), the completion-filtered attitude deviation, the filtered clearance and the
    controller's own clearance verdict, the LOC flag, and the completion conditions of
    ``C2Controller._update_completion`` (spec rev. 70 / P-S8-29 V2b; mirrored, not changed): attitude
    (reference on target and deviation < ``done_attitude_rad``), clearance (``_is_clearance_done``, pure),
    twist (``|D| < done_twist_N`` = ``ok_twist_strict``, or the V2b relaxation accepted this period =
    ``twist_relaxed``, read from ``_state.twist_relaxed_load_N``; the stateful check is never called), LOC
    (soil response on and lift-off not confirmed). A value the
    controller does not expose reads NaN (private members; the record stays usable when P-S8-29
    renames them). Arrays: ``t_s`` absolute, ``phase``, ``D_raw_N``, ``D_loop_N``, ``deviation_rad``,
    ``on_target``, ``clearance_filtered_m``, ``ok_<reason>`` (1 / 0 / -1 unknown),
    ``complete_since_s``."""

    def __init__(self, c2: Any):
        self.c2 = c2
        self.rows: list[dict[str, Any]] = []

    @staticmethod
    def _try(fn, default=math.nan):
        try:
            v = fn()
        except Exception:  # noqa: BLE001 - private controller members, record only
            return default
        return default if v is None else v

    def __call__(self, meas: Any, command: Any = None) -> None:
        c2 = self.c2
        st = getattr(c2, "_state", None)
        rd = getattr(st, "last_reading", None)
        th = c2.config.thresholds
        d_raw = self._try(lambda: float(c2.geometry.twist_vector @ np.asarray(rd.cylinder_force_N, float)))
        flt = getattr(c2, "_twist_load_filter", None)
        d_loop = self._try(lambda: float(np.asarray(flt._stages[-1]).reshape(-1)[0])) if flt is not None else d_raw
        dev = self._try(lambda: float(c2._completion_deviation_rad()))
        on_t = self._try(lambda: bool(c2._is_reference_on_target()), None)
        cf = getattr(c2, "_clearance_filter", None)
        clr = self._try(lambda: float(np.asarray(cf._stages[-1]).reshape(-1)[0]))
        clr_ok = self._try(lambda: bool(c2._is_clearance_done(clr)), None) if math.isfinite(clr) else None
        soil_on = bool(getattr(getattr(c2.config, "soil", None), "enable", False))
        loc = self._try(lambda: bool(c2._is_liftoff_confirmed()), None) if soil_on else True

        def flag(v):
            return -1 if v is None else int(bool(v))

        att_ok = None if (on_t is None or not math.isfinite(dev)) else (on_t and dev < th.done_attitude_rad)
        tw_strict = None if not math.isfinite(d_raw) else abs(d_raw) < th.done_twist_N
        # P-S8-29 V2b (3131552): the relaxed twist path is stateful (_is_twist_condition_met); the probe only
        # reads what this period's update left: twist_relaxed_load_N is set when the relaxation accepted |D|
        relaxed = getattr(st, "twist_relaxed_load_N", None) is not None
        tw_ok = None if tw_strict is None else (tw_strict or relaxed)
        self.rows.append({"t_s": float(meas.t_s), "phase": str(getattr(c2, "phase", "")),
                          "D_raw_N": d_raw, "D_loop_N": d_loop, "deviation_rad": dev,
                          "on_target": flag(on_t), "clearance_filtered_m": clr,
                          "ok_attitude": flag(att_ok), "ok_clearance": flag(clr_ok), "ok_twist": flag(tw_ok),
                          "ok_loc": flag(loc), "ok_twist_strict": flag(tw_strict), "twist_relaxed": int(relaxed),
                          "twist_relax_settled_since_s": self._try(lambda: float(st.twist_relax_settled_since_s)),
                          "complete_since_s": self._try(lambda: float(st.complete_since_s))})

    def arrays(self) -> dict[str, np.ndarray]:
        keys = ("t_s", "D_raw_N", "D_loop_N", "deviation_rad", "on_target", "clearance_filtered_m",
                "ok_attitude", "ok_clearance", "ok_twist", "ok_loc", "ok_twist_strict", "twist_relaxed",
                "twist_relax_settled_since_s", "complete_since_s")
        out = {k: np.asarray([r.get(k, math.nan) for r in self.rows], float) for k in keys}
        out["phase"] = np.asarray([r["phase"] for r in self.rows], dtype="U32")
        return out

    def save(self, path: Path) -> dict[str, Any]:
        arr = self.arrays()
        np.savez(path, **arr)
        return {"file": path.name, "rows": int(arr["t_s"].size),
                "rule": "runner mirror of C2Controller._update_completion (spec rev. 70), read-only; -1 = unknown"}


def completion_block_summary(arr: dict[str, np.ndarray], done_twist_N: float) -> dict[str, Any]:
    """LEVEL samples of :class:`CompletionProbe`: share of samples blocked by each reason, the reasons at the
    last LEVEL sample, and the D range in LEVEL [N]."""
    ph = arr["phase"]
    lv = np.array(["level" in str(p).lower() for p in ph])
    out: dict[str, Any] = {"level_samples": int(lv.sum()), "done_twist_N": done_twist_N}
    if not lv.any():
        return out
    out["blocked_share"] = {r: float(np.mean(arr[f"ok_{r}"][lv] == 0)) for r in COMPLETION_REASONS}
    out["unknown_share"] = {r: float(np.mean(arr[f"ok_{r}"][lv] < 0)) for r in COMPLETION_REASONS}
    k = int(np.flatnonzero(lv)[-1])
    out["last_level_t_s"] = float(arr["t_s"][k])
    out["last_level_blocking"] = [r for r in COMPLETION_REASONS if arr[f"ok_{r}"][k] == 0]
    d = arr["D_raw_N"][lv]
    d = d[np.isfinite(d)]
    if d.size:
        out["D_level_N"] = {"min": float(d.min()), "max": float(d.max()), "abs_last": float(abs(d[-1]))}
    return out


VIRGIN_UNCERTAINTY = {"stroke_mm": 2.5, "force_fraction": 0.20}
"""Dynamics 2026-10-28: a C2 decision on the soft leg taken while its pad load is still below F_x (elastic
branch, before the virgin Bekker branch) carries stroke +-2.5 mm and force +20 % uncertainty."""
_PAD_TYPE = {"cad330": "A", "dwg_rear250": "B"}


def virgin_crossover_force_N(set_key: str, pad_variant: str, leg: str, path: Path | None = None) -> float | None:
    """``F_x = K A s_x``: elastic stiffness of the set x pad bottom area of the leg (pad variant) x virgin
    crossover sinkage ``K_checks.<type>.<leg>.virgin_crossover_mm`` of ``02_params/scm_soil_sets.json``
    [N]; None when the set has no crossover (linear sets, e.g. G1). J1: B rear 49.0 / front 85.1 kN,
    J2: 34.8 / 60.2 kN (dynamics 2026-10-28)."""
    from outrigger_sim.chrono.scm_model import SOIL_SETS_JSON
    from outrigger_sim.pad_variants import pad_variant_meta

    data = json.loads(Path(path or SOIL_SETS_JSON).read_text("utf-8"))
    entry = data["sets"][set_key]
    sx = ((entry.get("K_checks") or {}).get(_PAD_TYPE[pad_variant]) or {}).get(leg, {}).get("virgin_crossover_mm")
    if sx is None:
        return None
    area = float(pad_variant_meta(pad_variant)["pad_bottom_area_m2"][leg])
    return float(entry["chrono"]["elastic_K"]) * area * float(sx) * 1e-3


def virgin_branch_record(series: dict[str, np.ndarray], soil_rows: list[dict[str, Any]], soil_meta: dict | None,
                         phases: list[tuple[float, str]], *, leg: str, fx_N: float | None,
                         t_loop_start_s: float) -> dict[str, Any]:
    """Soft-leg virgin-branch record (dynamics / user 2026-10-28): first time the soft pad's SCM normal
    exceeds ``F_x``; the C2 decisions about that leg (t_P, LOC, the first probe of the leg) taken before it
    are marked "virgin-branch window" with :data:`VIRGIN_UNCERTAINTY`. TOUCH values of the soft pad are a
    record, not judged. Times relative to the loop start [s]."""
    j = ("FL", "FR", "RL", "RR").index(leg)
    t = np.asarray(series["t_s"], float)
    n = np.asarray(series["scm_pad_normal_N"], float)[:, j]
    over = np.flatnonzero(n > fx_N) if fx_N is not None else np.zeros(0, int)
    t_x = None if not over.size else float(t[over[0]])
    sm = soil_meta or {}
    first_probe = next((float(r["t_s"]) for r in soil_rows if r.get("probed_leg") == j), None)
    decisions = {"t_P_s": sm.get("t_P_s"), "t_L_s": sm.get("t_loc_s"), "first_probe_s": first_probe}

    def rel(v):
        return None if v is None else float(v) - t_loop_start_s

    window = {k: (v is not None and (t_x is None or v < t_x)) for k, v in decisions.items()} if fx_N is not None \
        else {k: False for k in decisions}
    touch = []
    for (t1, ph), nxt in zip(phases, [*phases[1:], (float(t[-1]) if t.size else 0.0, "end")], strict=True):
        if "touch" in str(ph).lower():
            m = (t >= t1) & (t <= nxt[0])
            if m.any():
                touch.append({"t_rel_s": [rel(t1), rel(nxt[0])], "pad_normal_max_N": float(n[m].max()),
                              "sinkage_end_mm": float(np.asarray(series["pad_sinkage_geometric_m"])[m, j][-1] * 1e3)})
    return {"leg": leg, "F_x_N": fx_N, "t_first_over_F_x_rel_s": rel(t_x),
            "decisions_rel_s": {k: rel(v) for k, v in decisions.items()},
            "virgin_branch_window": window, "any_in_window": bool(any(window.values())),
            "uncertainty_if_in_window": dict(VIRGIN_UNCERTAINTY),
            "touch_record": touch,
            "rule": "dynamics / user 2026-10-28: C2 decisions on the soft leg before its pad normal first exceeds "
                    "F_x = K A s_x are in the virgin-branch window (stroke +-2.5 mm, force +20 %); TOUCH values of "
                    "the soft pad are a record, not judged; F_x None (linear set) = no window"}


def p3b_ext_records(series: dict[str, np.ndarray], events: list[tuple[float, str]], soil_meta: dict | None,
                    completion: dict[str, np.ndarray], *, done_twist_N: float, soil_patch_leg: str | None,
                    t_loop_start_s: float, t_departure_s: float | None = None) -> dict[str, Any]:
    """G6 / P-S8-29 record block (user decision 2026-10-27): controller event counts
    (:data:`P3B_EXT_EVENTS`), t_P / t_L / c_min(t_P) of the C2 soil meta (``t_P_s``, ``t_loc_s``,
    ``clearance_at_P_m``; relative to the loop start), the completion block summary and the pad sinkage
    summary (1 ms geometric sinkage; soft leg = the G6 patch leg, None without a patch)."""
    names = [n for _t, n in events]
    counts = {k: sum(1 for n in names if n == k or n.startswith(k + ":")) for k in P3B_EXT_EVENTS}
    sm = soil_meta or {}

    def rel(v):
        return None if v is None else float(v) - t_loop_start_s

    sink = np.asarray(series.get("pad_sinkage_geometric_m", np.zeros((0, 4))), float)
    legs = ("FL", "FR", "RL", "RR")
    sink_sum: dict[str, Any] = {}
    if sink.size:
        sink_sum = {"end_mm": dict(zip(legs, (sink[-1] * 1e3).tolist())),
                    "max_mm": dict(zip(legs, (np.nanmax(sink, axis=0) * 1e3).tolist()))}
        if soil_patch_leg is not None:
            j = legs.index(soil_patch_leg)
            others = [i for i in range(4) if i != j]
            sink_sum["soft_leg"] = soil_patch_leg
            sink_sum["soft_minus_others_mean_end_mm"] = float((sink[-1, j] - np.mean(sink[-1, others])) * 1e3)
    times = {k: [[rel(t), n] for t, n in events if n == k or n.startswith(k + ":")] for k in P3B_EXT_EVENT_TIMES}
    rule_times = {k: [[rel(t), n] for t, n in events if n == k or n.startswith(k + ":")]
                  for k in P3B_EXT_RULE_EVENT_TIMES}
    t_loc = sm.get("t_loc_s")
    return {"event_counts": counts, "event_times_rel_s": times, "rule_event_times_rel_s": rule_times,
            "t_crawler_departure_rel_s": rel(t_departure_s),
            "loc_minus_crawler_departure_s": None if t_loc is None or t_departure_s is None
            else float(t_loc) - float(t_departure_s),
            "loc_minus_crawler_departure_rule": "t_loc (C2 soil meta t_loc_s) - first crawler departure (P3a-2 rule "
                                                "of p3b.departure, t_departure_s); > 0 = LOC after the departure",
            "soil_times_rel_s": {"t_P_s": rel(sm.get("t_P_s")), "t_L_s": rel(sm.get("t_loc_s"))},
            "c_min_at_P_m": sm.get("clearance_at_P_m"), "loc": sm.get("loc"),
            "loc_anchor_applied": sm.get("loc_anchor_applied"),
            "completion": completion_block_summary(completion, done_twist_N),
            "pad_sinkage": sink_sum,
            "rule": "G6 / P-S8-29 record (2026-10-27): records only, no judgement"}


P2C_PITCH_PP_LIMIT_DEG = 0.02
"""P2-c (dynamics 5.35.4 table): last 1 s pitch p-p <= 0.02 deg."""
P2D_NORMAL_TOL = 0.002
"""P2-d: SCM normal sum / (weight cos(tilt)) = 1 +- 0.002 (on a slope the normal sum is W cos(tilt), P1-L5 note)."""


def settle_slope_record(s: dict[str, np.ndarray], weight_N: float, plane_normal_world: np.ndarray,
                        requested_floor_normal: np.ndarray | None, gravity_world: tuple[float, float, float],
                        rut: dict[str, Any] | None) -> dict[str, Any]:
    """Settle checks of a ``level`` run on a (sloped) floor, last 1 s of the settle (:class:`StepSeries`): P2-c
    pitch / roll p-p [deg], P2-d SCM normal sum (crawler + 4 pads, along the plane normal) over ``W cos(tilt)``, the
    plane tilt [deg], the SCM plane normal against the requested floor normal (``--floor-roll`` / ``--floor-pitch``,
    ``scenarios.slope.floor_normal``), the gravity direction (world -z) and the rut reference basis (heights along the
    plane normal, ``S9Model.mark_rut_reference`` / ``rut_clearance_m``). Record; P2-c / P2-d flags."""
    n = np.asarray(plane_normal_world, float)
    tilt = math.degrees(math.acos(max(-1.0, min(1.0, float(n[2]) / float(np.linalg.norm(n))))))
    g = np.asarray(gravity_world, float)
    req = np.array([0.0, 0.0, 1.0]) if requested_floor_normal is None else np.asarray(requested_floor_normal, float)

    def angle_deg(a: np.ndarray, b: np.ndarray) -> float | None:
        na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
        if na == 0.0 or nb == 0.0:
            return None
        return math.degrees(math.acos(max(-1.0, min(1.0, float(a @ b) / (na * nb)))))

    out: dict[str, Any] = {
        "plane_normal_world": n.tolist(), "plane_tilt_deg": tilt, "requested_floor_normal": req.tolist(),
        "plane_vs_requested_angle_deg": angle_deg(n, req),
        "gravity_world_m_s2": g.tolist(), "gravity_vs_minus_z_angle_deg": angle_deg(g, np.array([0.0, 0.0, -1.0])),
        "rut_basis": "rut reference heights and clearance = point . plane normal (S9Model.mark_rut_reference / "
                     "rut_clearance_m): clearance measured along the slope normal",
        "rut_reference": rut,
        "rule": "P2-c last 1 s pitch p-p <= 0.02 deg; P2-d normal sum / (W cos tilt) = 1 +- 0.002 (dynamics 5.35.4); "
                "settle window = the last 1 s of the settle"}
    if not len(s.get("t_s", ())):
        return out
    rp = np.asarray(s["roll_pitch_deg"], float)
    nsum = np.asarray(s["scm_crawler_normal_N"], float) + np.asarray(s["scm_pad_normal_N"], float).sum(axis=1)
    ratio = float(nsum.mean() / (weight_N * math.cos(math.radians(tilt))))
    out.update(window_s=[float(s["t_s"][0]), float(s["t_s"][-1])],
               pitch_pp_deg=float(np.ptp(rp[:, 1])), roll_pp_deg=float(np.ptp(rp[:, 0])),
               roll_pitch_mean_deg=rp.mean(axis=0).tolist(),
               normal_over_weight=float(nsum.mean() / weight_N), normal_over_weight_cos_tilt=ratio)
    out["P2-c_ok"] = bool(out["pitch_pp_deg"] <= P2C_PITCH_PP_LIMIT_DEG)
    out["P2-d_ok"] = bool(abs(ratio - 1.0) <= P2D_NORMAL_TOL)
    return out


def settle_reference(s: dict[str, np.ndarray]) -> dict[str, Any]:
    """Settle reference of a ``level`` run from the last 1 s of the settle (:class:`StepSeries`):
    means of the track normals (5 % utilisation rule), roll / pitch, origin z, pad sinkage, crawler
    normal, plus the last row (the P3 origin of each run, 284 J1-J2 ①)."""
    if not len(s.get("t_s", ())):
        return {"rows": 0}
    return {"window_s": [float(s["t_s"][0]), float(s["t_s"][-1])], "rows": int(len(s["t_s"])),
            "track_normal_N": s["scm_track_normal_raw_N"].mean(axis=0).tolist(),
            "crawler_normal_N": float(s["scm_crawler_normal_N"].mean()),
            "roll_pitch_deg": s["roll_pitch_deg"].mean(axis=0).tolist(),
            "z_origin_m": float(s["z_origin_m"].mean()),
            "pad_sinkage_geometric_m": s["pad_sinkage_geometric_m"].mean(axis=0).tolist(),
            "end_roll_pitch_deg": s["roll_pitch_deg"][-1].tolist(), "end_z_origin_m": float(s["z_origin_m"][-1]),
            "end_pad_sinkage_geometric_m": s["pad_sinkage_geometric_m"][-1].tolist()}


def _at(t: np.ndarray, tq: float) -> int:
    """Index of the first series row at / after ``tq`` (last row if beyond)."""
    return min(int(np.searchsorted(t, tq - 1e-9)), len(t) - 1)


def _event_leg(name: str) -> tuple[str, str | None]:
    head, _, leg = name.partition(":")
    return head, (leg.split(":")[0] if leg else None)


def w61_watch(events: list[tuple[float, str]], phases: list[tuple[float, str]], s: dict[str, np.ndarray],
              ctx: dict[str, Any], t_loc_s: float | None) -> dict[str, Any]:
    """Spec 301 W-61-1 ... 4 record rows (rod-pressure fallback, R-5): after each
    ``WARN_ROD_PRESSURE_FALLBACK:<leg>``, the same leg's ``relevel_predicted`` /
    ``probe_aborted_low_load`` events with the true 1 ms F_cyl and the P5 level (W-61-1), the
    first DONE -> READY time and probe rounds after it (W-61-2), the class of a repeat (W-61-3:
    >= 2 R-5 with true force >= 3 P5 = false re-level; < P5 + 5 kN = real low load) and, inside
    the soil mode after the LOC, the leg's sinkage rate and the other legs' force (W-61-4).
    Records and warnings only, never a pass / fail."""
    t, f = s["t_s"], s["F_cyl_N"]
    rate = s.get("sinkage_rate_0p2s_m_s")
    if rate is None:
        rate = sinkage_rate(t, s["pad_sinkage_geometric_m"])
    p5 = float(ctx["P5_N"])
    rows, warnings = [], []
    fallbacks = [(te, _event_leg(n)[1]) for te, n in events if n.startswith("WARN_ROD_PRESSURE_FALLBACK:")]
    for t_fb, leg in fallbacks:
        i = LEGS.index(leg)
        hits = []
        for te, n in events:
            kind, lg = _event_leg(n)
            if lg != leg or te < t_fb - 1e-9 or kind not in ("relevel_predicted", "probe_aborted_low_load"):
                continue
            k = _at(t, te)
            hit = {"t_s": te, "event": kind, "F_true_N": float(f[k, i]), "P5_N": p5,
                   "F_over_P5": float(f[k, i] / p5)}
            if t_loc_s is not None and te >= t_loc_s - 1e-9:  # W-61-4: inside the soil-mode / post-LOC stretch
                hit["W-61-4"] = {"sinkage_rate_leg_mm_s": float(rate[k, i] * 1e3) if np.isfinite(rate[k, i]) else None,
                                 "F_true_other_legs_N": {LEGS[j]: float(f[k, j]) for j in range(4) if j != i}}
            hits.append(hit)
        r5 = [h for h in hits if h["event"] == "relevel_predicted"]
        cls = None
        if len(r5) >= 2:
            if all(h["F_true_N"] >= W61_FALSE_RELEVEL_FACTOR * p5 for h in r5):
                cls = "false_relevel (rev. 61 mechanism)"
            elif any(h["F_true_N"] < p5 + W61_REAL_LOW_MARGIN_N for h in r5):
                cls = "real_low_load"
            else:
                cls = "between (neither rule)"
        t_done = next((tp for tp, ph in phases if ph == "done" and tp >= t_fb - 1e-9), None)
        t_ready = None if t_done is None else next((tp for tp, ph in phases if ph == "ready" and tp > t_done), None)
        probes = sum(1 for tp, ph in phases if ph == "probe" and tp >= t_fb - 1e-9
                     and (t_ready is None or tp <= t_ready + 1e-9))
        row = {"leg": leg, "t_fallback_s": t_fb, "W-61-1_hits": hits,
               "W-61-1_counts": {"relevel_predicted": len(r5),
                                 "probe_aborted_low_load": len(hits) - len(r5)},
               "W-61-2": {"t_first_done_after_s": t_done, "t_ready_after_s": t_ready,
                          "done_to_ready_s": None if (t_done is None or t_ready is None) else t_ready - t_done,
                          "probe_rounds": probes,
                          "note": "pair comparison (fallback-free twin / locked_ratio_rule fixed) is the judge's"},
               "W-61-3_class": cls, "after_loc": bool(t_loc_s is not None and t_fb >= t_loc_s - 1e-9)}
        rows.append(row)
        if hits:
            warnings.append(f"W-61-1 {leg}: rod-pressure fallback at {t_fb:.2f} s, then {len(r5)} relevel_predicted / "
                            f"{len(hits) - len(r5)} probe_aborted_low_load on the same leg")
        if len(r5) >= 2:
            warnings.append(f"W-61-3 {leg}: R-5 repeated {len(r5)} times ({cls})")
        if t_done is not None and t_ready is None:
            warnings.append(f"W-61-2 {leg}: no READY after the DONE at {t_done:.2f} s (fallback at {t_fb:.2f} s)")
    return {"rule": "spec 301 W-61-1 ... 4 (record rows, not judgements)", "P5_N": p5,
            "fallback_events": len(fallbacks), "rows": rows, "warnings": warnings,
            "fallback_meta": ctx.get("fallback_meta")}


def p34_judgement_window(t: np.ndarray, rp_deg: np.ndarray, creep: dict[str, Any],
                         phases: list[tuple[float, str]]) -> dict[str, Any]:
    """P3-4 main judgement (control D-3, user-confirmed 2026-10-26): window from max(two-sided
    creep stop, last READY entry) to the run end; value = max |roll|, |pitch| of the true attitude
    in it (absolute, target 0) <= 0.2 deg. Without a two-sided creep stop the signed one sets the
    window and ``creep_vibration_suspect`` is raised; a window < 5 s raises ``window_short``.
    ``sensor_allowance_left_deg`` = 0.2 - 0.02 (mount) - absmax; ``budget_residual_le_0p04`` =
    absmax <= 0.04 deg (= allowance >= the 0.14 deg IMU zero error budget; record only)."""
    t = np.asarray(t, dtype=float)
    rp = np.asarray(rp_deg, dtype=float)
    t_end = float(t[-1])
    readies = [tp for k, (tp, ph) in enumerate(phases) if ph == "ready" and (k == 0 or phases[k - 1][1] != "ready")]
    t_ready_last = readies[-1] if readies else None
    two = creep.get("t_final_two_sided_s")
    signed = creep.get("t_final_s")
    suspect = two is None and signed is not None
    t_creep = two if two is not None else signed
    out: dict[str, Any] = {"t_ready_last_entry_s": t_ready_last,
                           "ready_at_end": bool(phases and phases[-1][1] == "ready"),
                           "creep_stop_used_s": t_creep,
                           "creep_stop_basis": "two_sided" if two is not None else ("signed" if signed is not None
                                                                                    else None),
                           "creep_vibration_suspect": bool(suspect)}
    flags = []
    if t_ready_last is None:
        flags.append("no_ready")
    if t_creep is None:
        flags.append("no_creep_stop")
    if suspect:
        flags.append("creep_vibration_suspect")
    if "no_ready" in flags or "no_creep_stop" in flags:
        out.update(p34_window_s=None, p34_absmax_deg=None, p34_absmax_overall_deg=None, window_short=True,
                   sensor_allowance_left_deg=None, budget_residual_le_0p04=None, within_0p2=False,
                   flags=flags + ["window_short"])
        return out
    t0w = max(t_ready_last, t_creep)
    w = t >= t0w - 1e-9
    short = (t_end - t0w) < P3B_MIN_WINDOW_S - 1e-9 or not w.any()
    if short:
        flags.append("window_short")
    absmax = np.abs(rp[w]).max(axis=0) if w.any() else np.array([np.nan, np.nan])
    overall = float(np.max(absmax))
    allowance = P3B_ATTITUDE_LIMIT_DEG - P3B_MOUNT_SHARE_DEG - overall
    out.update(p34_window_s=[float(t0w), t_end], p34_window_length_s=float(t_end - t0w),
               p34_absmax_deg=absmax.tolist(), p34_absmax_overall_deg=overall, window_short=bool(short),
               sensor_allowance_left_deg=float(allowance),
               budget_residual_le_0p04=bool(overall <= P3B_BUDGET_RESIDUAL_DEG + 1e-12),
               within_0p2=bool(w.any() and overall <= P3B_ATTITUDE_LIMIT_DEG), flags=flags)
    return out


def reapproach_limit_records(history: list[dict[str, Any]] | None, settings: dict[str, Any] | None) -> dict[str, Any]:
    """C2 lifted re-approach intervals (meta ``lifted_reapproach``) ended by the P-S9-10 limits
    (control D-4): ``no_contact`` runs with their cause ``travel`` (travel > ``max_travel_m``,
    checked first as in C2) or ``time`` (end - start >= ``max_duration_s``), duration and
    ``protected_periods``. On SCM a firing is a FLAG, not a pass / fail."""
    settings = settings or {}
    max_d, max_tr = settings.get("max_duration_s"), settings.get("max_travel_m")
    rows = []
    for run in history or []:
        if run.get("outcome") != "no_contact":
            continue
        dur = None if run.get("end_s") is None else float(run["end_s"]) - float(run["start_s"])
        travel = float(run.get("travel_m") or 0.0)
        if max_tr is not None and travel > float(max_tr):
            cause = "travel"
        elif max_d is not None and dur is not None and dur >= float(max_d) - 0.05:
            cause = "time"
        else:
            cause = "unknown"
        rows.append({"leg": run.get("leg"), "start_s": run.get("start_s"), "end_s": run.get("end_s"),
                     "duration_s": dur, "travel_m": travel, "cause": cause,
                     "protected_periods": run.get("protected_periods")})
    return {"fired": len(rows), "by_cause": {c: sum(1 for r in rows if r["cause"] == c) for c in ("time", "travel",
                                                                                                    "unknown")},
            "rows": rows, "intervals_total": len(history or []), "open_at_end": sum(1 for r in history or []
                                                                                   if r.get("end_s") is None),
            "max_duration_s": max_d, "max_travel_m": max_tr,
            "note": "SCM: FLAG (record), not a pass / fail (control D-4)"}


# --- P3-2 / P3-5 / P3-7 judgement definitions of spec rev. 60 (U-S9P-13 / 14 / 15 (가), C-S9-60) --------

P32_TAIL_ALLOWANCE_S = 1.0
"""P3-2 time clause T_lim = plateau_window_m / (push_speed_fraction v_max) + this (spec rev. 60 308,
U-S9P-13 (가)). ASSUMPTION (spec 308): crawler load-tail share; observed tail max t_P - t_D 1.01 s,
set to 1.0 s (slightly below the observed max, not rounded up)."""
P37_RISE_MIN_N = 4000.0
"""P3-7: minimum S-1 window rise per plateau_window_m on the crawler-loaded windows (spec 284 / 310)."""
P37_LOADED_FRACTION = 0.01
"""P3-7 loaded window: crawler true normal at the window end > this x W_plant (spec rev. 60 310, U-S9P-15
(가): "0.01 W = 3.77 kN"; spec 422.6: W_plant = mass_scale x W_ref, W_ref = C2 meta ``soil.W_ref_N`` = YAML
superstructure mass x g, 376.58 kN, so W_plant = W_ref at mass_scale 1).
The departure rule's 0.01 W uses ``p3b.weight_N`` (+ leg moving parts, 380.1 kN, 3.80 kN); the spec
number and control's p3b_loc_detail.json window counts follow W_ref."""
P37_RECORD_GT_N = 1000.0
"""P3-7 record: the former loaded-window definition (crawler > 1 kN)."""
P37_RECORD_FRACTION_HI = 0.05
"""P3-7 record: crawler > 0.05 W_ref windows."""
P37_GATE_TOL_S = 1.0e-6
"""P3-7 reconstruction gate: |t_P, t_loc (reconstructed) - C2 meta soil| <= this."""
REJUDGE_FILE = "result_rejudge_rev60.json"
"""Per-case re-judgement file of :func:`rejudge_case` (the run's ``result.json`` stays untouched)."""


def p32_time_limit_s(settings: dict[str, Any], v_max_m_s: float) -> float:
    """P3-2 time clause [s]: ``plateau_window_m / (push_speed_fraction v_max) + P32_TAIL_ALLOWANCE_S``
    (10 mm / (0.25 x 20.924 mm/s) + 1.0 = 2.9117 s; spec rev. 60 308)."""
    return float(settings["plateau_window_m"]) / (float(settings["push_speed_fraction"]) * float(v_max_m_s)) \
        + P32_TAIL_ALLOWANCE_S


def p32_loc_block(t: np.ndarray, cn: np.ndarray, w_n: float, *, t_loc: float | None, t_dep: float | None,
                  t_done: float | None, t_soil_mode: float | None, soil_meta: dict[str, Any] | None,
                  v_max_m_s: float | None) -> dict[str, Any]:
    """P3-2 LOC (spec 284, rev. 60 U-S9P-13 (가)): ``within`` = LOC before the first DONE, the
    crawler not loaded at the LOC (1 ms crawler normal < 0.01 W) and 0 <= t_L - t_D <= T_lim
    (:func:`p32_time_limit_s`); ``within_2s_record`` = the former 2 s clause. Absolute times [s]."""
    soil_meta = soil_meta or {}
    settings = soil_meta.get("settings") or {}
    t_lim = None if v_max_m_s is None or not settings else p32_time_limit_s(settings, v_max_m_s)
    p32: dict[str, Any] = {
        "criterion": "spec rev. 60, U-S9P-13 (가): crawler_liftoff_confirmed before the first DONE; no LOC while the "
                     "crawler is loaded (normal >= 0.01 W at the LOC); LOC - departure <= T_lim = plateau_window_m / "
                     f"(push_speed_fraction v_max) + {P32_TAIL_ALLOWANCE_S:g} s (ASSUMPTION tail share); the former "
                     f"<= {P3B_LOC_AFTER_DEPARTURE_S:g} s clause is within_2s_record",
        "t_loc_s": t_loc, "t_departure_s": t_dep, "t_first_done_s": t_done,
        "soil_mode_start_t_s": t_soil_mode, "soil_mode_used": t_soil_mode is not None,
        "limit_s": t_lim, "limit_basis": {"plateau_window_m": settings.get("plateau_window_m"),
                                          "push_speed_fraction": settings.get("push_speed_fraction"),
                                          "v_max_m_s": v_max_m_s, "tail_allowance_s": P32_TAIL_ALLOWANCE_S}}
    t_p = soil_meta.get("t_P_s")
    p32["tP_minus_departure_s"] = None if (t_p is None or t_dep is None) else float(t_p) - t_dep
    p32["window_s"] = None if (t_p is None or t_loc is None) else t_loc - float(t_p)
    if t_loc is None:
        p32.update(within=False, within_2s_record=False, reason="no LOC")
        return p32
    k = _at(t, t_loc)
    d = None if t_dep is None else t_loc - t_dep
    p32.update(loc_before_first_done=bool(t_done is None or t_loc <= t_done + 1e-9), loc_minus_departure_s=d,
               crawler_normal_at_loc_N=float(cn[k]), crawler_loaded_at_loc=bool(cn[k] >= P3A_OFF_FRACTION * w_n))
    base = p32["loc_before_first_done"] and d is not None and not p32["crawler_loaded_at_loc"] and d >= 0.0
    p32["within_2s_record"] = bool(base and d <= P3B_LOC_AFTER_DEPARTURE_S + 1e-9)
    if t_lim is None:
        p32.update(within=None, reason="no soil settings / v_max: T_lim unknown")
    else:
        p32["within"] = bool(base and d <= t_lim + 1e-9)
    return p32


P32_LATE_LOC_FLAG = "P3-2_late_loc_reapproach"
"""FLAG name of the spec 419.8 rule (decision 13, 2026-10-29)."""
LOC_WINDOW_RESTART_EVENTS = ("INFO_LOC_WINDOW_RESTART", "FIX_LW_RESTART")
"""S-1 window clear by an active re-approach: project P-S8-32 event, s9_slope_fix_candidates wrapper event."""
REAPPROACH_END_EVENTS = ("leg_reapproach_contact", "WARN_LEG_REAPPROACH_NO_CONTACT")
"""C2 lifted re-approach end events (``<name>:<leg>``; c2.py ``_update_lifted_reapproach``)."""
REAPPROACH_START_EVENT = "leg_reapproach_start"
"""C2 lifted re-approach start event (``leg_reapproach_start:<leg>``)."""
FAULT_PHASES = ("fault", "fault_reground")
"""C2 phases that count as FAULT for spec 419.8 condition 4 (419.8.1)."""
CONTROL_PERIOD_DEFAULT_S = 0.1
"""C2 R8 control period [s] (10 Hz) when the C2 meta ``period_s`` is not at hand."""


def _event_kind_legs(name: str, kinds: tuple[str, ...]) -> tuple[str, list[str]] | None:
    """``(kind, legs)`` of ``<kind>`` / ``<kind>:<leg>[,<leg>...]`` for a kind in ``kinds``, else None."""
    for kind in kinds:
        if name == kind:
            return kind, []
        if name.startswith(kind + ":"):
            return kind, [g for g in name[len(kind) + 1:].split(":")[0].split(",") if g]
    return None


def p32_late_loc_block(t: np.ndarray, cn: np.ndarray, w_n: float, events: list[tuple[float, str]],
                       phases: list[tuple[float, str]], p32: dict[str, Any], p33: dict[str, Any], *,
                       period_s: float | None = None, lwa_on: bool | None = None) -> dict[str, Any]:
    """Spec 419.8 (decision 13, 2026-10-29): a P3-2 time-clause violation (LOC - departure > T_lim)
    is the FLAG ``P3-2_late_loc_reapproach`` instead of a failure when all five conditions hold:

    Re-approach interval (spec 419.8.1): ``leg_reapproach_start:<leg>`` to that leg's next
    :data:`REAPPROACH_END_EVENTS` event (open without one); legs come from these events, not from
    the window-restart event string (a re-approach started while the window was empty is not named
    there).

    1. ``restart``: at least one re-approach interval overlaps [t_off, t_LOC] (both ends included;
       t_off = crawler departure ``p32.t_departure_s``) and has an S-1 window restart event
       (:data:`LOC_WINDOW_RESTART_EVENTS`) during it (before the departure allowed: LWa writes the
       event only when it clears a non-empty window).
    2. ``delay_by_reapproach``: t_LOC - max(t_off, t_re_end) <= T_lim, t_re_end = latest end of the
       intervals overlapping [t_off, t_LOC]; an open overlapping interval or t_re_end > t_LOC makes
       it false. With LWa on (``lwa_on``; None = restart events present) such a record is reported
       in ``judgement_error`` (no re-approach can be active at an LWa LOC).
    3. ``not_false_loc``: SCM crawler true normal < 0.01 W (strict) over the LOC control period =
       the 1 ms samples in (t_LOC - period, t_LOC] and the sample at t_LOC (period max; ASSUMPTION:
       the period that ends with the reading confirming the LOC; the at-LOC sample and the next
       period max are records).
    4. ``load_strict``: P3-3 ``within`` True (true F_cyl after the departure >= F_min) and no FAULT
       over the whole run (no ``FAULT*`` event, no :data:`FAULT_PHASES` phase; ``WARN_*`` is not a FAULT).
    5. ``loc_before_first_done``: P3-2 order clause.

    ``late_loc_reapproach_s`` = t_LOC - t_off. ``verdict``: ``pass`` (P3-2 ``within`` True),
    ``flag`` (time clause violated and 1-5 true), ``fail`` (otherwise), None (``within`` None).
    Times absolute [s], forces [N]."""
    period = CONTROL_PERIOD_DEFAULT_S if period_s is None else float(period_s)
    t_loc, t_off, t_lim = p32.get("t_loc_s"), p32.get("t_departure_s"), p32.get("limit_s")
    d = p32.get("loc_minus_departure_s")
    out: dict[str, Any] = {
        "rule": "spec 419.8 (decision 13, 2026-10-29): LOC - departure > T_lim is the FLAG "
                f"{P32_LATE_LOC_FLAG} when 1 a re-approach interval overlapping [t_off, t_LOC] had an LWa window "
                "restart (419.8.1), 2 t_LOC - max(t_off, t_re_end) <= T_lim (t_re_end = latest end of the overlapping "
                "intervals), 3 crawler true normal < 0.01 W over the LOC period, 4 P3-3 within and no FAULT, 5 LOC "
                "before the first DONE; else a failure",
        "t_off_s": t_off, "t_loc_s": t_loc, "limit_s": t_lim, "control_period_s": period,
        "late_loc_reapproach_s": None if (t_loc is None or t_off is None) else float(t_loc) - float(t_off),
        "t_reapproach_end_s": None, "loc_minus_reapproach_end_s": None}
    eps = 1e-9
    ev = sorted((float(te), str(n)) for te, n in events)
    rs = [te for te, n in ev if _event_kind_legs(n, LOC_WINDOW_RESTART_EVENTS)]
    out.update(restart_events_before_loc=0 if t_loc is None else sum(1 for x in rs if x <= float(t_loc) + eps),
               restart_events_off_to_loc=0 if (t_loc is None or t_off is None)
               else sum(1 for x in rs if float(t_off) - eps <= x <= float(t_loc) + eps))
    # spec 419.8.1: re-approach intervals = leg_reapproach_start:<leg> .. that leg's next end event
    intervals = []
    for ts, n in ev:
        k = _event_kind_legs(n, (REAPPROACH_START_EVENT,))
        if not k:
            continue
        for g in k[1]:
            te = next((x for x, m in ev if x >= ts - eps and (e := _event_kind_legs(m, REAPPROACH_END_EVENTS))
                       and g in e[1]), None)
            hi = np.inf if te is None else te
            overlaps = bool(t_loc is not None and t_off is not None and ts <= float(t_loc) + eps
                            and hi >= float(t_off) - eps)
            intervals.append({"leg": g, "start_s": ts, "end_s": te, "overlaps_off_to_loc": overlaps,
                              "window_restarts_s": [x for x in rs if ts - eps <= x <= hi + eps]})
    ov = [iv for iv in intervals if iv["overlaps_off_to_loc"]]
    out["reapproach_intervals"] = intervals
    out["overlapping_reapproach_legs"] = sorted({iv["leg"] for iv in ov})
    t_re_end = None
    if ov and all(iv["end_s"] is not None for iv in ov):
        t_re_end = max(iv["end_s"] for iv in ov)
    out["t_reapproach_end_s"] = t_re_end
    out["open_overlapping_interval"] = any(iv["end_s"] is None for iv in ov)
    if t_loc is not None and t_off is not None and t_re_end is not None:
        out["loc_minus_reapproach_end_s"] = float(t_loc) - max(float(t_off), t_re_end)
    # LWa on: no re-approach can be active at the LOC -> an interval ending after it (or open) is a judgement error
    lwa = bool(rs) if lwa_on is None else bool(lwa_on)
    err = None
    if lwa and t_loc is not None:
        if out["open_overlapping_interval"]:
            err = "LWa on: an overlapping re-approach interval has no end event"
        elif t_re_end is not None and t_re_end > float(t_loc) + eps:
            err = f"LWa on: t_re_end {t_re_end:.4f} s after t_LOC {float(t_loc):.4f} s"
    out.update(lwa_on=lwa, lwa_on_source="controller meta" if lwa_on is not None else "restart events present",
               judgement_error=err)
    # condition 3: crawler normal over the LOC period
    c3 = False
    if t_loc is not None and len(t):
        k = _at(t, float(t_loc))
        sel = (t > float(t_loc) - period + 1e-9) & (t <= float(t_loc) + 1e-9)
        vals = cn[sel]
        vmax = float(max(vals.max() if vals.size else -np.inf, cn[min(k, len(cn) - 1)]))
        nxt = (t >= float(t_loc) - 1e-9) & (t < float(t_loc) + period - 1e-9)
        out.update(crawler_normal_loc_period_max_N=vmax, crawler_normal_at_loc_N=float(cn[min(k, len(cn) - 1)]),
                   crawler_normal_next_period_max_N=float(cn[nxt].max()) if nxt.any() else None,
                   crawler_threshold_N=P3A_OFF_FRACTION * float(w_n))
        c3 = bool(vmax < P3A_OFF_FRACTION * float(w_n))
    faults = [(float(te), n) for te, n in events if n.startswith("FAULT")]
    fault_phase = any(ph in FAULT_PHASES for _tp, ph in phases)
    out.update(fault_events=faults, fault_phase=fault_phase)
    cond = {"1_restart": any(iv["window_restarts_s"] for iv in ov),
            "2_delay_by_reapproach": bool(out["loc_minus_reapproach_end_s"] is not None and t_lim is not None
                                          and t_re_end <= float(t_loc) + eps
                                          and out["loc_minus_reapproach_end_s"] <= float(t_lim) + eps),
            "3_not_false_loc": c3,
            "4_load_strict": bool(p33.get("within") is True and not faults and not fault_phase),
            "5_loc_before_first_done": bool(p32.get("loc_before_first_done") is True)}
    out["conditions"] = cond
    viol = bool(d is not None and t_lim is not None and float(d) > float(t_lim) + 1e-9)
    out["time_clause_violated"] = viol
    out["flag"] = bool(p32.get("within") is False and viol and all(cond.values()))
    within = p32.get("within")
    out["verdict"] = None if within is None else ("pass" if within else ("flag" if out["flag"] else "fail"))
    return out


def p35_clearance_block(rows: list[dict[str, Any]], phases: list[tuple[float, str]], *, t_dep: float | None,
                        t_loc: float | None, s_motor_max_m: list[float], s_motor_limit_m: float,
                        probe_sinkage: list[dict[str, Any]]) -> dict[str, Any]:
    """P3-5 (spec 284, rev. 60 U-S9P-14 (가)): judgement value = minimum 10 Hz ``rut_clearance_m``
    from the first READY entry (``phases``) to the run end >= 25 mm (ASSUMPTION U-S9-C3), and
    s_motor <= the end-margin stroke. Without READY: ``within`` None (reason). The former value
    (minimum after the crawler departure, ~0 by definition) is kept as a record."""
    rt = np.array([float(r["t_s"]) for r in rows]) if rows else np.array([])
    rc = np.array([np.nan if r.get("rut_clearance_m") is None else float(r["rut_clearance_m"]) for r in rows])
    after_dep = (rt >= t_dep - 1e-9) & np.isfinite(rc) if t_dep is not None else np.zeros(len(rt), bool)
    min_dep = float(rc[after_dep].min()) if after_dep.any() else None
    stroke_ok = bool(max(s_motor_max_m) <= s_motor_limit_m) if s_motor_max_m else False
    t_ready = next((tp for tp, ph in phases if ph == "ready"), None)
    out: dict[str, Any] = {
        "criterion": f"spec rev. 60, U-S9P-14 (가): min rut clearance (10 Hz) from the first READY entry to the run end "
                     f">= {P3B_RUT_CLEARANCE_MIN_M * 1e3:g} mm (ASSUMPTION U-S9-C3); s_motor <= {s_motor_limit_m:g} m; "
                     "the minimum after the departure is within_after_departure_record",
        "t_first_ready_s": t_ready, "rut_clearance_min_after_first_ready_m": None, "t_at_min_s": None,
        "rut_clearance_min_after_departure_m": min_dep,
        "rut_clearance_end_m": None if not len(rc) or not np.isfinite(rc[-1]) else float(rc[-1]),
        "s_motor_max_m": list(s_motor_max_m), "s_motor_limit_m": s_motor_limit_m, "stroke_within": stroke_ok,
        "within_after_departure_record": bool(min_dep is not None and min_dep >= P3B_RUT_CLEARANCE_MIN_M and stroke_ok),
        "probe_sinkage": probe_sinkage}
    if t_loc is not None and len(rt):
        k = int(np.searchsorted(rt, t_loc - 1e-9))
        out["rut_clearance_at_loc_m"] = float(rc[k]) if k < len(rt) and np.isfinite(rc[k]) else None
    else:
        out["rut_clearance_at_loc_m"] = None
    if t_ready is None:
        out.update(within=None, reason="no READY entry: not judgeable")
        return out
    sel = (rt >= t_ready - 1e-9) & np.isfinite(rc)
    if not sel.any():
        out.update(within=None, reason="no rut clearance row after the first READY")
        return out
    k = int(np.nonzero(sel)[0][np.argmin(rc[sel])])
    out.update(rut_clearance_min_after_first_ready_m=float(rc[k]), t_at_min_s=float(rt[k]),
               within=bool(rc[k] >= P3B_RUT_CLEARANCE_MIN_M and stroke_ok))
    return out


def s1_window_reconstruct(t: np.ndarray, in_level: np.ndarray, u_applied: np.ndarray, stroke_m: np.ndarray,
                          load_N: np.ndarray, settings: dict[str, Any], v_max_m_s: float, w_ref_N: float,
                          stop_at_loc: bool = True) -> dict[str, Any]:
    """Offline replica of the C2 S-1 plateau window (spec 285 P-S9-2, ``c2._update_liftoff_window``):
    LEVEL samples only; a sample whose applied output (same 10 Hz sample, ``u_applied``) has a
    retracting leg or a mean < ``plateau_mean_speed_fraction v_max`` clears the window, else it is
    appended as (mean stroke, load sum). Every sample with >= ``plateau_window_m`` of stroke in the
    window evaluates the shortest such tail: rise = ``polyfit(e - e_mean, F, 1)`` slope x
    ``plateau_window_m`` (end-point difference below 3 samples). Rise <= ``plateau_rise_max_N`` and
    tail mean >= ``plausibility_fraction W_ref`` = LOC (stops when ``stop_at_loc``). Returns the
    reconstructed t_P / t_loc and every evaluated window (t_start, t_end, rise, mean load)."""
    span = float(settings["plateau_window_m"])
    min_mean = float(settings["plateau_mean_speed_fraction"]) * float(v_max_m_s)
    rise_max = float(settings["plateau_rise_max_N"])
    plaus = float(settings["plausibility_fraction"]) * float(w_ref_N)
    win: list[tuple[float, float, float]] = []
    windows: list[dict[str, Any]] = []
    t_p = t_l = None
    for k in range(len(t)):
        if not in_level[k]:
            continue  # C2 only updates the window in LEVEL periods (no clearing outside them)
        u = u_applied[k]
        if not (np.all(u >= 0.0) and float(np.mean(u)) >= min_mean):
            win.clear()
            continue
        win.append((float(t[k]), float(np.mean(stroke_m[k])), float(np.sum(load_N[k]))))
        last = win[-1][1]
        if last - win[0][1] < span:
            continue
        s = len(win) - 1
        while s > 0 and last - win[s][1] < span:
            s -= 1
        tail = win[s:]
        e = np.array([x[1] for x in tail])
        f = np.array([x[2] for x in tail])
        if len(tail) >= 3:
            slope = float(np.polyfit(e - e.mean(), f, 1)[0])
        else:
            slope = (f[-1] - f[0]) / max(e[-1] - e[0], 1e-9)
        rise = slope * span
        mean_f = float(f.mean())
        windows.append({"t_start_s": tail[0][0], "t_end_s": tail[-1][0], "rise_N": rise, "mean_load_N": mean_f,
                        "n": len(tail)})
        if rise <= rise_max and mean_f >= plaus:
            t_p, t_l = tail[0][0], tail[-1][0]
            if stop_at_loc:
                break
    return {"t_P_s": t_p, "t_loc_s": t_l, "windows": windows}


def _rise_bucket(windows: list[dict[str, Any]], t: np.ndarray, cn: np.ndarray, threshold_N: float) -> dict[str, Any]:
    """Minimum rise of the windows whose crawler true normal at the window end (first 1 ms sample
    at / after it) exceeds ``threshold_N``; ``n`` = number of such windows."""
    sel = []
    for w in windows:
        c = float(cn[_at(t, w["t_end_s"])])
        if c > threshold_N:
            sel.append((w["rise_N"], w["t_end_s"], c, w["t_start_s"]))
    if not sel:
        return {"n": 0, "threshold_N": threshold_N, "rise_min_N": None}
    rise, t_end, c_end, t_start = min(sel)
    return {"n": len(sel), "threshold_N": threshold_N, "rise_min_N": rise, "t_end_s": t_end, "t_start_s": t_start,
            "crawler_at_end_N": c_end, "crawler_at_start_N": float(cn[_at(t, t_start)])}


def p37_plateau_block(t: np.ndarray, cn: np.ndarray, phases: list[tuple[float, str]],
                      rec: dict[str, np.ndarray] | None, areas: dict[str, list[float]] | None,
                      soil_meta: dict[str, Any] | None, v_max_m_s: float | None,
                      mass_scale: float = 1.0) -> dict[str, Any]:
    """P3-7 plateau margin (spec 284, rev. 60 U-S9P-15 (가), C-S9-60-3): reconstruct the S-1 windows
    (:func:`s1_window_reconstruct`) from the 10 Hz readings of ``record.npz`` (load = sum of
    ``p_h A_p - p_r A_ann``, mean ``meas.stroke``, same-sample ``u_applied``; zero offsets drop
    out of the slope), gate: reconstructed t_P / t_loc = C2 meta ``soil`` within 1e-6 s. Judgement:
    the windows ending with the crawler true normal (1 ms) > 0.01 W_plant rise >= 4 kN; none = pass
    (``no_loaded_window``). Records: > 1 kN and > 0.05 W_ref minima, and the same on the truth
    (``F_cyl`` sum, mean ``s_motor``, own LOC). ``t`` / ``cn`` = 1 ms series [s] / [N]; W_ref =
    C2 meta ``soil.W_ref_N`` (:data:`P37_LOADED_FRACTION`).

    Spec 422.6 (control, 2026-10-29): the loaded-window threshold is ``0.01 W_plant``, ``W_plant = mass_scale x W_ref``
    (plant superstructure weight, the W_ref basis; = W_ref at scale 1, bit for bit). W_ref stays the controller value
    for the S-1 reconstruction (plausibility) and the 0.05 W record bucket."""
    soil_meta = soil_meta or {}
    w_ref = soil_meta.get("W_ref_N")
    s = float(mass_scale)
    w_plant = None if w_ref is None else s * float(w_ref)
    thr = None if w_plant is None else P37_LOADED_FRACTION * w_plant
    out: dict[str, Any] = {
        "criterion": "spec rev. 60, U-S9P-15 (가): S-1 window rise per plateau_window_m >= "
                     f"{P37_RISE_MIN_N / 1e3:g} kN on the windows whose end crawler true normal > {P37_LOADED_FRACTION:g}"
                     f" W_plant (422.6: mass_scale x W_ref); none = pass; > {P37_RECORD_GT_N / 1e3:g} kN (former "
                     "definition) and > "
                     f"{P37_RECORD_FRACTION_HI:g} W_ref are records; gate: reconstructed t_P / t_loc = C2 meta within "
                     f"{P37_GATE_TOL_S:g} s",
        "loaded_threshold_N": thr, "W_ref_N": w_ref, "reconstruct_ok": False, "within": None,
        "mass_scale": s, "W_plant_N": w_plant,
        "loaded_threshold_basis": ("spec 422.6: 0.01 W_plant, W_plant = mass_scale x W_ref (plant superstructure "
                                   "weight; = W_ref at mass_scale 1); W_ref (C2) for the S-1 reconstruction and the "
                                   "0.05 W record bucket")}
    settings = soil_meta.get("settings") or {}
    if rec is None or areas is None or v_max_m_s is None or not settings or w_ref is None:
        out["reason"] = "inputs missing (record arrays, cylinder areas, v_max, C2 soil settings or W_ref)"
        return out
    if not soil_meta.get("loc"):
        out["reason"] = "no LOC in the C2 meta soil block"
        return out
    w_ref = float(w_ref)
    rt = np.asarray(rec["t"], dtype=float)
    lev = np.zeros(len(rt), bool)
    k = 0
    cur = None
    for i, ti in enumerate(rt):  # phase in force at the sample = last phases entry at / before it
        while k < len(phases) and phases[k][0] <= ti + 1e-9:
            cur = phases[k][1]
            k += 1
        lev[i] = cur == "level"
    a_p = np.asarray(areas["head_area_m2"], dtype=float)
    a_a = np.asarray(areas["annulus_area_m2"], dtype=float)
    load_read = np.asarray(rec["meas.head_pressure"], float) * a_p - np.asarray(rec["meas.rod_pressure"], float) * a_a
    u = np.asarray(rec["u_applied"], dtype=float)
    read = s1_window_reconstruct(rt, lev, u, np.asarray(rec["meas.stroke"], float), load_read, settings, v_max_m_s,
                                 w_ref)
    true = s1_window_reconstruct(rt, lev, u, np.asarray(rec["s_motor"], float), np.asarray(rec["F_cyl"], float),
                                 settings, v_max_m_s, w_ref)
    t_p_m, t_l_m = soil_meta.get("t_P_s"), soil_meta.get("t_loc_s")
    gate = (read["t_P_s"] is not None and t_p_m is not None and abs(read["t_P_s"] - float(t_p_m)) <= P37_GATE_TOL_S
            and read["t_loc_s"] is not None and t_l_m is not None
            and abs(read["t_loc_s"] - float(t_l_m)) <= P37_GATE_TOL_S)
    loaded = _rise_bucket(read["windows"], t, cn, thr)
    out.update(reconstruct_ok=bool(gate), t_P_rec_s=read["t_P_s"], t_loc_rec_s=read["t_loc_s"],
               t_P_meta_s=t_p_m, t_loc_meta_s=t_l_m, n_windows=len(read["windows"]),
               n_loaded_windows=loaded["n"], rise_min_loaded_N=loaded["rise_min_N"],
               t_end_at_min_s=loaded.get("t_end_s"), crawler_at_end_N=loaded.get("crawler_at_end_N"),
               no_loaded_window=loaded["n"] == 0,
               rise_min_gt1kN_N=_rise_bucket(read["windows"], t, cn, P37_RECORD_GT_N)["rise_min_N"],
               rise_min_gt0p05W_N=_rise_bucket(read["windows"], t, cn, P37_RECORD_FRACTION_HI * w_ref)["rise_min_N"],
               buckets_read={"gt1kN": _rise_bucket(read["windows"], t, cn, P37_RECORD_GT_N), "gt0p01W": loaded,
                             "gt0p05W": _rise_bucket(read["windows"], t, cn, P37_RECORD_FRACTION_HI * w_ref)},
               truth={"t_P_s": true["t_P_s"], "t_loc_s": true["t_loc_s"], "n_windows": len(true["windows"]),
                      "basis": "record.npz F_cyl sum, mean s_motor, same u_applied gate, own LOC"},
               rise_min_loaded_true_N=_rise_bucket(true["windows"], t, cn, thr)["rise_min_N"])
    if not gate:
        out["reason"] = (f"reconstruction gate failed: t_P {read['t_P_s']} vs meta {t_p_m}, t_loc {read['t_loc_s']} "
                         f"vs meta {t_l_m}")
        return out
    out["within"] = bool(loaded["n"] == 0 or loaded["rise_min_N"] >= P37_RISE_MIN_N)
    return out


def p3b_checks(out: dict[str, Any]) -> dict[str, Any]:
    """``p3b.checks`` from the p3b blocks (shared by the run and :func:`rejudge_case`)."""
    p31, p32, p33, p34 = out["P3-1_crawler"], out["P3-2_loc"], out["P3-3_leg_force"], out["P3-4_attitude"]
    p35, p37 = out["P3-5_clearance_stroke"], out["P3-7_plateau"]
    windows = out["P3-9_deferred"]["windows"]
    rc = p31.get("recontact_events") or {}
    return {"P3-1_crawler_zero_after_ready": p31.get("crawler_zero"),
            "P3-1_recontact": out["departure"].get("recontact_t_s"),
            "P3-1_recontact_pass": rc.get("pass"), "P3-1_flags": rc.get("flags"),
            "P3-1_recontact_classes": [e["class"] for e in rc.get("events", [])],
            "P3-2_within": p32.get("within"), "P3-2_within_2s_record": p32.get("within_2s_record"),
            "P3-2_loc_minus_departure_s": p32.get("loc_minus_departure_s"), "P3-2_limit_s": p32.get("limit_s"),
            # spec 419.8 (decision 13, 2026-10-29); None on a stored block without the rule
            P32_LATE_LOC_FLAG: (p32.get("late_loc_reapproach") or {}).get("flag"),
            "P3-2_verdict": (p32.get("late_loc_reapproach") or {}).get("verdict"),
            "P3-3_within": p33.get("within"),
            "P3-4_within_0p2": p34["within_0p2"], "P3-4_absmax_deg": p34.get("p34_absmax_overall_deg"),
            "P3-4_window_s": p34.get("p34_window_s"), "P3-4_flags": p34.get("flags"),
            "P3-4_window_short": p34.get("window_short"),
            "P3-4_creep_vibration_suspect": p34.get("creep_vibration_suspect"),
            "P3-4_sensor_allowance_left_deg": p34.get("sensor_allowance_left_deg"),
            "P3-4_budget_residual_le_0p04_record": p34.get("budget_residual_le_0p04"),
            "reapproach_limit_fired_FLAG": out["reapproach_limit"]["fired"],
            "reapproach_limit_by_cause": out["reapproach_limit"]["by_cause"],
            "P3-5_within": p35.get("within"),
            "P3-5_within_after_departure_record": p35.get("within_after_departure_record"),
            "P3-5_rut_clearance_min_after_first_ready_m": p35.get("rut_clearance_min_after_first_ready_m"),
            "P3-6_within": out["P3-6_ready"]["within"],
            "P3-7_within": p37.get("within"), "P3-7_rise_min_loaded_N": p37.get("rise_min_loaded_N"),
            "P3-7_reconstruct_ok": p37.get("reconstruct_ok"),
            "P3-8_within": out["P3-8_false_triggers"]["within"],
            "P3-9_flags": sum(1 for w in windows if w.get("below_F_min")),
            "pre_liftoff_flag": out["pre_liftoff_min_F_cyl"]["any_flag"],
            "W61_warnings": len(out["W61_watch"]["warnings"]),
            "criteria_rev": "spec rev. 60 (U-S9P-13/14/15 (가)): P3-2 T_lim, P3-5 after the first READY, P3-7 > 0.01 W",
            "note": "values vs criteria; decisions are control's (284) / dynamics' (physics)"}


def p37_record_arrays(record_dir: Path) -> dict[str, np.ndarray]:
    """The ``record.npz`` fields P3-7 reads (10 Hz)."""
    keys = ("t", "u_applied", "meas.head_pressure", "meas.rod_pressure", "meas.stroke", "F_cyl", "s_motor")
    with np.load(Path(record_dir) / "record.npz", allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in keys}


def p37_plant_inputs(params) -> dict[str, Any]:
    """Cylinder areas per leg (YAML ``legs.<leg>.cylinder``) and ``actuator.max_speed_m_s``."""
    return {"cyl_areas": {key: [float(params.get(f"legs.{leg}.cylinder.{key}")) for leg in LEGS]
                          for key in ("head_area_m2", "annulus_area_m2")},
            "v_max_m_s": float(params.get("actuator.max_speed_m_s"))}


def p3b_records(s: dict[str, np.ndarray], rows: list[dict[str, Any]], events: list[tuple[float, str]],
                phases: list[tuple[float, str]], ctx: dict[str, Any]) -> dict[str, Any]:
    """P3b values of one ``level`` run (control spec 284 P3-1 ... P3-9 with the J1 / J2
    supplements, 287 keys, 301 watch; dynamics 5.37.5 #2). ``s`` = 1 ms :class:`StepSeries`
    arrays, ``rows`` = 10 Hz S9 rows, ``events`` / ``phases`` = (t [s], name) of the C2 run
    (absolute simulation time), ``ctx``: ``weight_N``, ``F_min_N``, ``P5_N``,
    ``s_motor_limit_m``, ``t_loop_start_s``, ``settle`` (:func:`settle_reference`),
    ``fallback_meta``, ``T_o_s`` (re-approach opposite window, P3-9 deferral window; None = the S8
    judge default 0.8 s), and for P3-2 / P3-7 (spec rev. 60): ``soil_meta`` (C2 meta ``soil``),
    ``v_max_m_s``, ``cyl_areas`` and ``record`` (:func:`p37_plant_inputs`, :func:`p37_record_arrays`).
    Values and criterion comparisons only; decisions are control's / dynamics'. Angles deg (pitch >
    0 nose down), forces N, lengths m."""
    t = np.asarray(s["t_s"], dtype=float)
    cn, pn, f = s["scm_crawler_normal_N"], s["scm_pad_normal_N"], s["F_cyl_N"]
    sm, sink, rp = s["s_motor_m"], s["pad_sinkage_geometric_m"], s["roll_pitch_deg"]
    w_n, f_min, t0 = float(ctx["weight_N"]), float(ctx["F_min_N"]), float(ctx["t_loop_start_s"])
    settle = ctx.get("settle") or {}
    out: dict[str, Any] = {"basis": "1 ms truth series (step_series.npz) + 10 Hz rows; absolute simulation time; "
                                    "pitch > 0 nose down; forces along the SCM plane normal; F_cyl = acting force",
                           "t_loop_start_s": t0, "weight_N": w_n, "F_min_N": f_min}

    def first_event(name: str) -> float | None:
        return next((te for te, n in events if n == name), None)

    def first_phase(name: str) -> float | None:
        return next((tp for tp, ph in phases if ph == name), None)

    dep = crawler_departure(t, cn, w_n)
    out["departure"] = dep
    t_dep = dep.get("t_departure_s")
    t_ready, t_done = first_phase("ready"), first_phase("done")
    t_loc = first_event(SOIL_LOC_EVENT)
    # P3-1 crawler load after READY, recontact after the departure
    p31: dict[str, Any] = {"criterion": f"SCM crawler normal sum = 0 in READY .. READY + {P3B_READY_CRAWLER_WINDOW_S:g} s; "
                                        "no recontact after the first departure", "t_ready_s": t_ready}
    if t_ready is not None:
        w = (t >= t_ready - 1e-9) & (t <= t_ready + P3B_READY_CRAWLER_WINDOW_S + 1e-9)
        p31.update(window_complete=bool(t[-1] >= t_ready + P3B_READY_CRAWLER_WINDOW_S - 1e-9),
                   crawler_normal_max_N=float(cn[w].max()) if w.any() else None,
                   crawler_patches_max=float(s["scm_crawler_patches"][w].max()) if w.any() else None)
        p31["crawler_zero"] = bool(w.any() and cn[w].max() <= 0.0)
    p31.update(recontact_t_s=dep.get("recontact_t_s"), recontact_count=dep.get("recontact_count"))
    # U-S9-G6d (가): recontact events with their class (transient FLAG / strict fail)
    p31["recontact_events"] = recontact_events(t, cn, w_n, dep, t_loc, t_ready_s=t_ready)
    out["P3-1_crawler"] = p31
    # P3-2 LOC (spec rev. 60 T_lim)
    p32 = p32_loc_block(t, cn, w_n, t_loc=t_loc, t_dep=t_dep, t_done=t_done,
                        t_soil_mode=first_event(SOIL_MODE_EVENT), soil_meta=ctx.get("soil_meta"),
                        v_max_m_s=ctx.get("v_max_m_s"))
    out["P3-2_loc"] = p32
    # P3-3 leg force after the departure
    p33: dict[str, Any] = {"criterion": f"true F_cyl min after the departure >= F_min ({f_min:.0f} N); guard + "
                                        f"{P3B_GUARD_MARGIN_N / 1e3:g} kN recorded; split at departure + "
                                        f"{P3B_LIFTOFF_TRANSIENT_S:g} s (rev. 40 lift-off transient)"}
    if t_dep is not None:
        a = t >= t_dep - 1e-9
        tr = a & (t < t_dep + P3B_LIFTOFF_TRANSIENT_S)
        la = t >= t_dep + P3B_LIFTOFF_TRANSIENT_S
        mins = np.where(a[:, None], f, np.inf).min(axis=0)
        kmin = np.argmin(np.where(a[:, None], f, np.inf), axis=0)
        p33.update(F_min_after_N=mins.tolist(), t_min_after_s=[float(t[k]) for k in kmin],
                   F_min_transient_N=np.where(tr[:, None], f, np.inf).min(axis=0).tolist() if tr.any() else None,
                   F_min_late_N=np.where(la[:, None], f, np.inf).min(axis=0).tolist() if la.any() else None,
                   margin_over_F_min_N=(mins - f_min).tolist(),
                   below_F_min_plus_guard=(mins < f_min + P3B_GUARD_MARGIN_N).tolist(),
                   within=bool(np.all(mins >= f_min)))
    out["P3-3_leg_force"] = p33
    # spec 419.8 (decision 13): late LOC because of a window restart by a re-approach -> FLAG, inside P3-2
    p32["late_loc_reapproach"] = _record_or_error(lambda: p32_late_loc_block(
        t, cn, w_n, events, phases, p32, p33, period_s=ctx.get("control_period_s"), lwa_on=ctx.get("lwa_on")))
    out["pre_liftoff_min_F_cyl"] = pre_liftoff_min_force(t, f, f_min, t_dep)
    # P3-4 attitude (main judgement), creep stop
    cs = creep_stop(t, sink, t_dep)
    out["creep_stop"] = cs
    t_end = float(t[-1])
    w_end = t >= t_end - P3B_END_WINDOW_S - 1e-9
    end_mean = rp[w_end].mean(axis=0)
    end_absmax = np.abs(rp[w_end]).max(axis=0)
    ref_rp = np.asarray(settle.get("end_roll_pitch_deg", [np.nan, np.nan]), dtype=float)
    p34: dict[str, Any] = {
        "criterion": f"main judgement (control D-3, 2026-10-26): window [max(two-sided creep stop, last READY entry), "
                     f"t_end]; true attitude (quaternion roll / pitch, absolute, target 0) max |roll|, |pitch| <= "
                     f"{P3B_ATTITUDE_LIMIT_DEG:g} deg; window < {P3B_MIN_WINDOW_S:g} s -> window_short FLAG; no two-sided "
                     "creep stop -> signed creep stop + creep_vibration_suspect FLAG; end 1 s values, dead band "
                     f"{P3B_DEADBAND_DEG:g} deg, post-lift-off max <= {P3B_POST_LIFTOFF_ATTITUDE_DEG:g} deg recorded",
        "end_window_s": [float(t[w_end][0]), t_end], "end_mean_roll_pitch_deg": end_mean.tolist(),
        "end_absmax_roll_pitch_deg": end_absmax.tolist(),
        "end_mean_minus_settle_deg": (end_mean - ref_rp).tolist(),
        "t_creep_stop_final_s": cs.get("t_final_s"),
        "t_creep_stop_final_two_sided_s": cs.get("t_final_two_sided_s"),
        "window_after_creep_stop": bool(cs.get("t_final_s") is not None and float(t[w_end][0]) >= cs["t_final_s"] - 1e-9),
        "end_1s_within_0p2_record": bool(np.all(end_absmax <= P3B_ATTITUDE_LIMIT_DEG)),
        "within_deadband_0p03_record": bool(np.all(np.abs(end_mean) <= P3B_DEADBAND_DEG))}
    p34.update(p34_judgement_window(t, rp, cs, phases))
    if t_dep is not None:
        a = t >= t_dep - 1e-9
        p34["post_liftoff_absmax_deg"] = np.abs(rp[a]).max(axis=0).tolist()
    if t_done is not None:
        kd = _at(t, t_done)
        wd = (t >= t_done - 1e-9) & (t <= t_done + P3B_DONE_SHIFT_S + 1e-9)
        p34["done"] = {"t_first_done_s": t_done,
                       "before_creep_stop": bool(cs.get("t_final_s") is None or t_done < cs["t_final_s"]),
                       "shift_5s_end_minus_done_deg": (rp[wd][-1] - rp[kd]).tolist(),
                       "shift_5s_range_deg": [np.ptp(rp[wd][:, 0]).item(), np.ptp(rp[wd][:, 1]).item()]}
    out["P3-4_attitude"] = p34
    # P3-5 rut clearance (spec rev. 60: minimum after the first READY), stroke, sinkage around probes
    probe_iv = []
    for k, (tp, ph) in enumerate(phases):
        if ph != "probe":
            continue
        te = phases[k + 1][0] if k + 1 < len(phases) else t_end
        ka, kb = _at(t, tp), _at(t, te)
        probe_iv.append({"t_start_s": tp, "t_end_s": te, "d_sinkage_m": (sink[kb] - sink[ka]).tolist()})
    out["P3-5_clearance_stroke"] = p35_clearance_block(rows, phases, t_dep=t_dep, t_loc=t_loc,
                                                       s_motor_max_m=sm.max(axis=0).tolist(),
                                                       s_motor_limit_m=ctx["s_motor_limit_m"], probe_sinkage=probe_iv)
    # P3-6 READY time
    p36 = p36_ready_limit(ctx.get("case_args"))
    out["P3-6_ready"] = {"t_ready_after_loop_start_s": None if t_ready is None else t_ready - t0,
                         "limit_s": p36["limit_s"], "limit_rule": p36,
                         "within": bool(t_ready is not None and t_ready - t0 <= p36["limit_s"] + 1e-9)}
    # P3-7 plateau margin (spec rev. 60: S-1 window reconstruction, loaded window > 0.01 W)
    out["P3-7_plateau"] = p37_plateau_block(t, cn, phases, ctx.get("record"), ctx.get("cyl_areas"),
                                            ctx.get("soil_meta"), ctx.get("v_max_m_s"),
                                            mass_scale=float(ctx.get("mass_scale", 1.0)))
    # P3-8 false triggers before the LOC, first-touch annotation (J1 note 4)
    t_lim = np.inf if t_loc is None else t_loc
    kinds = ("leg_reapproach_start", "relevel_predicted", "probe_aborted_low_load")
    touch = {}
    for i, lg in enumerate(LEGS):
        k = np.nonzero((t >= t0 - 1e-9) & (pn[:, i] > 0.0))[0]
        touch[lg] = float(t[k[0]]) if k.size else None
    early = []
    for te, n in events:
        kind, lg = _event_leg(n)
        if kind in kinds and te < t_lim:
            ann = [g for g, tt in touch.items() if tt is not None and tt - 1e-9 <= te <= tt + P3B_TOUCH_ANNOTATE_S]
            early.append({"t_s": te, "event": n, "within_first_touch_0p2s_of": ann})
    out["P3-8_false_triggers"] = {
        "criterion": "0 re-approach starts / P5 / probe_aborted_low_load before the LOC (soil mode included)",
        "counts": {kd_: sum(1 for e in early if e["event"].startswith(kd_)) for kd_ in kinds},
        "events": early, "first_touch_t_s": touch,
        "first_touch_note": "J1: the SCM virgin branch stiffens the first 0.2 s (5.35.5 ①); events in that "
                            "window carry the annotation", "within": not early}
    # P3-9 deferred re-approach (U-S8-57)
    # S8 judge rule (spec rev. 55 267, C-S8-42): window t_def .. min(t_next, t_def + T_o) + 0.3 s, merged per leg;
    # here on the raw 1 ms acting force (no S8-A2 interval minimum in the S9 series)
    from outrigger_sim.verify.s8_control import deferred_leg_minimum

    rel = [(te - t0, n) for te, n in events]
    dm = deferred_leg_minimum(rel, 0.0, t0, {"t": t, "F_cyl": f}, f_min, t_o_s=ctx.get("T_o_s"))
    windows = [] if dm is None else dm["windows"]
    for w in windows:
        i = LEGS.index(w["leg"])
        sel = (t - t0 >= w["window_s"][0] - 1e-9) & (t - t0 <= w["window_s"][1] + 1e-9)
        w["d_sinkage_mm"] = float((sink[sel][-1, i] - sink[sel][0, i]) * 1e3) if sel.any() else None
    out["P3-9_deferred"] = {"rule": None if dm is None else dm["rule"], "windows": windows,
                            "flag": bool(dm and dm["flag"]), "t_o_s": None if dm is None else dm["t_o_s"],
                            "times": "window_s relative to the closed-loop start t_loop_start_s",
                            "note": "deferrals 0" if not windows else None}
    # 287 keys / track utilisation (5 % rule)
    um = mask_track_utilisation(s["track_utilisation"], s["scm_track_normal_raw_N"],
                                settle.get("track_normal_N", [np.nan, np.nan]))
    out["track_utilisation"] = {**_nan_stats(um, t), "rule": f"NaN while the track normal < "
                                f"{TRACK_UTIL_MIN_NORMAL_FRACTION:g} x its settle value", "settle_track_normal_N":
                                settle.get("track_normal_N"), "unmasked": _nan_stats(np.asarray(s["track_utilisation"],
                                                                                                float), t)}
    out["W61_watch"] = w61_watch(events, phases, s, ctx, t_loc)
    out["reapproach_limit"] = reapproach_limit_records(ctx.get("reapproach_history"), ctx.get("reapproach_settings"))
    out["checks"] = p3b_checks(out)
    return out


SOIL_LOC_EVENT = "crawler_liftoff_confirmed"
SOIL_MODE_EVENT = "soil_mode_start"
REJUDGED_BLOCKS = ("P3-1_crawler", "P3-2_loc", "P3-5_clearance_stroke", "P3-6_ready", "P3-7_plateau", "checks")
"""p3b blocks whose definition changed (spec rev. 60 C-S9-60; P3-1_crawler: Q-G threshold chatter class, spec 423.3;
P3-6_ready: spec 421.1 limit rows); every other block must come out equal."""
REJUDGE_ADDED_KEYS = {"P3-1_crawler": ("recontact_events",)}
"""Keys added to a block after a run (U-S9-G6d, 2026-10-28): left out of the "unchanged block" comparison when the
stored block lacks them (the other keys of the block must still be equal)."""


def _without_added(name: str, new: Any, old: Any) -> Any:
    keys = REJUDGE_ADDED_KEYS.get(name, ())
    if not keys or not isinstance(new, dict) or not isinstance(old, dict):
        return new
    return {k: v for k, v in new.items() if not (k in keys and k not in old)}


def _file_sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical(x: Any) -> str:
    return json.dumps(json.loads(json.dumps(_plain(x), ensure_ascii=False)), sort_keys=True, ensure_ascii=False)


def rejudge_case(case_dir: Path, write: bool = True) -> dict[str, Any]:
    """Re-judge one finished ``level`` case with the spec rev. 60 definitions (C-S9-60), no Chrono
    re-run: rebuild the :func:`p3b_records` context from ``result.json`` (phases, events, 10 Hz
    rows, settle reference, C2 soil / re-approach meta, W-61 P5 and fallback meta),
    ``step_series.npz``, ``record/record.npz`` and the YAML cylinder areas / v_max, recompute the
    whole ``p3b`` and require every block outside :data:`REJUDGED_BLOCKS` to equal the stored one.
    Writes ``<case>/result_rejudge_rev60.json`` (the run's ``result.json`` is never modified) with
    the new ``p3b``, the former ``checks``, input SHA-256 and the YAML fingerprint match."""
    from outrigger_sim.params import load_params

    case_dir = Path(case_dir)
    r = json.loads((case_dir / "result.json").read_text("utf-8"))
    if r.get("action") != "level" or "p3b" not in r:
        raise ValueError(f"{case_dir}: not a run_S9 level result")
    old = r["p3b"]
    with np.load(case_dir / "step_series.npz", allow_pickle=False) as z:
        series = {k: np.asarray(z[k]) for k in z.files}
    rec = p37_record_arrays(case_dir / "record")
    rec_meta = json.loads((case_dir / "record" / "meta.json").read_text("utf-8"))
    params = load_params()
    run_sha = (rec_meta.get("run") or {}).get("params_file_sha256")
    phases = [(float(p["t_s"]), str(p["phase"])) for p in r["phases"]]
    events = [(float(e["t_s"]), str(e["name"])) for e in r["events"]]
    w61 = old.get("W61_watch") or {}
    lr = r.get("c2_lifted_reapproach")
    ctx = {"weight_N": old["weight_N"], "F_min_N": old["F_min_N"], "P5_N": w61["P5_N"],
           "s_motor_limit_m": old["P3-5_clearance_stroke"]["s_motor_limit_m"], "t_loop_start_s": old["t_loop_start_s"],
           "settle": r.get("settle_reference"), "T_o_s": (lr or {}).get("opposite_window_s"),
           "fallback_meta": w61.get("fallback_meta"), "reapproach_history": r.get("c2_lifted_reapproach_history"),
           "reapproach_settings": lr, "soil_meta": r.get("c2_soil"), "record": rec, **p37_plant_inputs(params),
           "control_period_s": (r.get("controller_meta") or {}).get("period_s"),
           "lwa_on": lwa_on_from_meta(r.get("controller_meta")),
           "mass_scale": rejudge_mass_scale(r), "case_args": r.get("args")}
    new = _plain(p3b_records(series, r["s9_rows"], events, phases, ctx))
    diffs = sorted(k for k in set(old) | set(new)
                   if k not in REJUDGED_BLOCKS
                   and _canonical(old.get(k)) != _canonical(_without_added(k, new.get(k), old.get(k))))
    out = {"rule": "spec rev. 60 C-S9-60 (U-S9P-13/14/15 (가)): P3-2 T_lim, P3-5 after the first READY, P3-7 S-1 "
                   "window > 0.01 W_plant (422.6); P3-1 recontact classes U-S9-G6d + Q-G chatter (423.3); re-judged "
                   "from the stored records, no Chrono re-run",
           "generator": "04_scripts/02_chrono/run_S9.py rejudge", "case": case_dir.name,
           "created_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
           "inputs_sha256": {n: _file_sha256(case_dir / n) for n in ("result.json", "step_series.npz",
                                                                    "record/record.npz")},
           "params_file_sha256": params.file_sha256, "params_file_sha256_run": run_sha,
           "params_file_match": bool(run_sha == params.file_sha256),
           "rejudged_blocks": list(REJUDGED_BLOCKS), "unchanged_blocks_equal": not diffs, "unchanged_block_diffs": diffs,
           "checks_before": old.get("checks"),
           "judgement_weights": judgement_weights(ctx["mass_scale"], old["weight_N"],
                                                  (r.get("c2_soil") or {}).get("W_ref_N"), old["F_min_N"]),
           "p3b": new}
    if write:
        (case_dir / REJUDGE_FILE).write_text(json.dumps(_plain(out), indent=1, ensure_ascii=False), "utf-8")
    return out


def rejudge_mass_scale(r: dict[str, Any]) -> float:
    """Plant mass scale of a stored ``level`` result: ``mass_scale.mass_scale``, else ``args.mass_scale``, else 1.0
    (results before the Q-D option)."""
    blk = r.get("mass_scale")
    if isinstance(blk, dict) and blk.get("mass_scale") is not None:
        return float(blk["mass_scale"])
    v = (r.get("args") or {}).get("mass_scale")
    return 1.0 if v is None else float(v)


def rejudge_targets(paths: list[str]) -> list[Path]:
    """Case folders of ``rejudge``: a case folder (``result.json`` of action ``level``) or a batch
    folder (its ``P3b_*`` case folders)."""
    out = []
    for p in map(Path, paths):
        if (p / "result.json").exists():
            out.append(p)
        else:
            out += sorted(d for d in p.glob("P3b_*") if d.is_dir() and (d / "result.json").exists())
    return out


def run_rejudge(args) -> None:
    rows = {}
    for d in rejudge_targets(args.paths):
        res = rejudge_case(d, write=not args.dry_run)
        c, p = res["p3b"]["checks"], res["p3b"]
        rows[d.name] = {"P3-1": [c["P3-1_crawler_zero_after_ready"], c["P3-1_recontact_pass"], c["P3-1_flags"],
                                 c["P3-1_recontact_classes"]],
                        "P3-2": [c["P3-2_within"], c["P3-2_within_2s_record"], c["P3-2_loc_minus_departure_s"]],
                        "P3-2_verdict": c.get("P3-2_verdict"),
                        "P3-5": [c["P3-5_within"], c["P3-5_rut_clearance_min_after_first_ready_m"]],
                        "P3-7": [c["P3-7_within"], c["P3-7_reconstruct_ok"], c["P3-7_rise_min_loaded_N"],
                                 p["P3-7_plateau"].get("rise_min_gt1kN_N")],
                        "unchanged_blocks_equal": res["unchanged_blocks_equal"],
                        "params_file_match": res["params_file_match"]}
    print(json.dumps(_plain(rows), indent=1), flush=True)


def run_level(args) -> Path:
    """C2 closed loop on the S9 model (P3b, control spec 284). Not run without ``--approved``."""
    if not args.approved:
        raise SystemExit("P3b C2 levelling is a main run: the user confirms it first (--approved)")
    if args.threads != SCM_THREADS_FIXED and not args.allow_other_threads:
        raise SystemExit(f"P3b runs use --threads {SCM_THREADS_FIXED} (dynamics 5.34.12 / 5.35.5 #4: one OpenMP "
                         "thread count for every P3b case); --allow-other-threads for a comparison run")
    from outrigger_sim.control.c2 import C2Controller

    # spec 420.4 (1): hashes of the controller files as imported by this process (record only)
    code_files = _record_or_error(code_state_files)
    config, c2_meta = level_c2_config(args.allow_current_c2)
    # G6P (2026-10-28): P-S8-29 relaxation preset / off, recorded in c2_setup
    config, c2_meta["twist_relax"] = apply_twist_relax(config, getattr(args, "twist_relax", TWIST_RELAX_PRESET))
    # study ① (2026-10-28): start / target slope limits preset or verification, recorded in c2_setup
    config, c2_meta["start_limit"] = apply_start_limit(config, getattr(args, "start_limit", START_LIMIT_PRESET),
                                                       getattr(args, "level", "top"))
    # U-S8-61 (spec 304 1): SCM keeps the preset R-5 fallback ratio (column_nominal); the L1 rigid
    # cases of S9 (P3-10, s9_merge/m3_run.py) take plant_meta in run_S6C.job_bundle_c
    from outrigger_sim.chrono.fallback_ratio import with_engine_fallback_ratio

    config, c2_meta["fallback_ratio"] = with_engine_fallback_ratio(config, "SCM")
    imu_cfg, leg_cfg, config, sensor_meta = level_sensor_setup(args.pressure_grade, args.imu_grade, config)
    from outrigger_sim.chrono.scm_engine import S9Engine
    from outrigger_sim.params import load_params
    from outrigger_sim.record import make_run_meta, save_record
    from outrigger_sim.runner import run_closed_loop
    from outrigger_sim.sensors.suite import SensorSuite

    placement = place()
    params, pv, soil = load_inputs(args)
    params_ctrl = load_params(level=args.level)
    from outrigger_sim.chrono.scm_model import gravity_ramp_factor

    tb = time.perf_counter()
    model = build_machine(args, params, pv, soil)
    if model.actuator.friction_path != (args.fs_kN > 0.0):
        raise RuntimeError(f"--fs-kN {args.fs_kN:g}: the plant friction path is {model.actuator.friction_path} "
                           "(seal friction override not applied)")
    # Q-D (2026-10-29): plant superstructure mass / inertia x --mass-scale before the settle (1.0 = untouched)
    mass_scale = float(getattr(args, "mass_scale", 1.0))
    mass_block = apply_mass_scale(model, params, mass_scale)
    dashpot = add_settle_dashpot(args, model)
    build_s = time.perf_counter() - tb
    n_settle = round(settle_time_s(args) / model.dt_s)
    every = max(1, round(STEP_SERIES_S / model.dt_s))
    settle_rec = StepSeries(model, every, round(1.0 / STEP_SERIES_S) + 2)
    t_settle0 = time.perf_counter()
    for k in range(n_settle):
        model.set_gravity_factor(gravity_ramp_factor(k * model.dt_s, args.gravity_ramp, args.gravity_ramp_shape))
        model.step()
        if (k + 1) * model.dt_s >= settle_time_s(args) - 1.0 - 1e-9 and (k + 1) % every == 0:
            settle_rec.record()
    settle_wall = time.perf_counter() - t_settle0
    model.set_gravity_factor(1.0)
    rut = model.mark_rut_reference()
    settle = settle_reference(settle_rec.arrays())
    # study ① (2026-10-28): settle checks on the (sloped) floor, P2-c / P2-d, plane / gravity / rut basis
    from outrigger_sim.scenarios.slope import floor_normal as _floor_normal

    settle_slope = _record_or_error(lambda: settle_slope_record(
        settle_rec.arrays(), model_weight_N(params, mass_scale), np.asarray(model.normal_world, float),
        None if (args.floor_roll == 0.0 and args.floor_pitch == 0.0) else _floor_normal(args.floor_roll,
                                                                                      args.floor_pitch),
        model.system_gravity(), rut))
    engine = S9Engine(model, imu_method="chrono_point")
    c2 = C2Controller.from_params(params_ctrl, config)
    # control D-1: IMU --imu-grade (10 ms samples), pressure / stroke --pressure-grade (WIKA A-10 normal default)
    suite = SensorSuite(imu_cfg, leg_cfg, seed=args.seed)
    soil_rows: list[dict[str, Any]] = []
    phases: list[tuple[float, str]] = []
    t_loop0 = float(model.system.GetChTime())
    step_rec = StepSeries(model, every, round(args.duration / STEP_SERIES_S) + 16)

    from outrigger_sim.chrono.run_rows import MinimalR8Series, R8_SERIES_NAME, probed_leg

    r8_rows = MinimalR8Series(c2)  # (가): r8_series.npz probed_leg, same key / meaning as run_S6C
    gap_probe = CrawlerGapProbe(model)
    completion = CompletionProbe(c2)  # G6 / P-S8-29 record (read-only)

    def observe(meas, command):  # 10 Hz S9 keys (287: crawler patch force sum, pad node sinkage, rut clearance)
        from outrigger_sim.frames import roll_pitch_from_quat

        r8_rows(meas, command)
        completion(meas, command)
        row = model.s9_record()
        ph = str(getattr(c2, "phase", None))
        row["c2_phase"] = ph
        row["probed_leg"] = probed_leg(c2)  # (가) control 2026-10-26: record only (None = not PROBE)
        row["reanchor_stage"], row["reanchor_step"] = reanchor_probe(c2)  # study ① RA record (read-only)
        # control-expert 2026-10-28: all-crawler-point gap to the SCM surface along the plane normal (new keys;
        # rut_clearance_m unchanged)
        try:
            (row["crawler_gap_min_m"], row["crawler_gap_point"], row["crawler_gap_grid_min_m"],
             row["crawler_gap_point_near_sinkage_m"]) = gap_probe()
        except Exception as e:  # noqa: BLE001 - record only
            row["crawler_gap_min_m"] = row["crawler_gap_grid_min_m"] = row["crawler_gap_point_near_sinkage_m"] = None
            row["crawler_gap_point"] = f"error: {type(e).__name__}: {e}"
        if not phases or phases[-1][1] != ph:
            phases.append((float(meas.t_s), ph))
        q = model.superstructure.GetRot()
        row["roll_pitch_deg"] = [math.degrees(a) for a in roll_pitch_from_quat(np.array([q.e0, q.e1, q.e2, q.e3]))]
        row["pad_nodes"] = model.pad_node_stats()
        row["scm_crawler_patches"] = int(model.crawler_terrain.GetNumContactPatches())
        soil_rows.append(row)

    c2_setup = {**c2_meta, "lifted_reapproach": lifted_reapproach_meta(config), "sensors": sensor_meta}
    run_meta = make_run_meta(params, engine.meta(), scenario=f"S9_P3b_{args.soil}_{args.pad_variant}",
                             scenario_settings={"args": vars(args), "rut_reference": rut, "c2_setup": c2_setup},
                             sensors=suite.setup())
    t_run0 = time.perf_counter()
    res = run_closed_loop(engine, c2, suite, args.duration, run_meta=run_meta, on_control=observe,
                          command_delay_periods=0, placement=None, step_hook=step_rec)
    loop_wall = time.perf_counter() - t_run0
    tag = args.case or (f"{args.soil}_{args.pad_variant}_{args.level}_Fs{args.fs_kN:g}"
                        + ("" if not args.soil_patch else "_sp" + args.soil_patch.replace(":", "")))
    d = out_dir("level", tag, args.out_root)
    save_record(res.record, d / "record")  # 10 Hz: meas.head_pressure / rod_pressure / stroke, u_cmd (applied)
    np.savez(d / "controller_commands.npz", t_s=res.command_t_s, issued_u_m_s=res.command_m_s)
    r8_series_info = r8_rows.save(d / R8_SERIES_NAME)
    series = step_rec.arrays()
    series["sinkage_rate_0p2s_m_s"] = sinkage_rate(series["t_s"], series["pad_sinkage_geometric_m"])
    np.savez(d / "step_series.npz", **series)
    ctl_meta = c2.meta()
    events = [(float(e.t_s), str(e.name)) for e in c2.events]
    limits = p3a_limits(params)
    tp_meta = ctl_meta.get("two_pressure") or {}
    ctx = {"weight_N": model_weight_N(params, mass_scale), "F_min_N": limits["F_min_cylinder_N"],
           "P5_N": float(c2.geometry.F_min_N + c2.config.thresholds.relevel_load_margin_N),
           "s_motor_limit_m": limits["s_motor_limit_m"], "t_loop_start_s": t_loop0, "settle": settle,
           "T_o_s": (c2_setup["lifted_reapproach"] or {}).get("opposite_window_s"),
           "fallback_meta": {k: tp_meta.get(k) for k in ("fallback_lock_current", "fallback_lock_log")},
           "reapproach_history": ctl_meta.get("lifted_reapproach"),
           "reapproach_settings": c2_setup["lifted_reapproach"],
           "soil_meta": ctl_meta.get("soil"), "record": p37_record_arrays(d / "record"), **p37_plant_inputs(params),
           "control_period_s": float(c2.config.period_s), "lwa_on": lwa_on_from_meta(ctl_meta),
           "mass_scale": mass_scale, "case_args": vars(args)}
    p3b = p3b_records(series, soil_rows, events, phases, ctx)
    completion_info = completion.save(d / COMPLETION_SERIES_NAME)
    p3b_ext = p3b_ext_records(series, events, ctl_meta.get("soil"), completion.arrays(),
                              done_twist_N=float(c2.config.thresholds.done_twist_N),
                              soil_patch_leg=model.soil_patch_leg, t_loop_start_s=t_loop0,
                              t_departure_s=p3b["departure"].get("t_departure_s"))
    p3b_ext["completion_series"] = completion_info
    # study ① (2026-10-28): REANCHOR record (RA-1 .. RA-6) and the SL-2 start-condition record; records only, a
    # failure here is written into the block instead of losing the run
    p3b_ext["reanchor"] = _record_or_error(lambda: reanchor_records(
        series, soil_rows, events, phases, ctl_meta.get("reanchor"), (ctl_meta.get("target") or {}).get("target_rad"),
        F_min_N=ctx["F_min_N"], normal_world=np.asarray(model.normal_world, float),
        limit_fn=None if model.pad_bushing is None else model.pad_bushing.tangential_limit_N, t_loop_start_s=t_loop0))
    p3b_ext["start_condition"] = _record_or_error(
        lambda: start_condition_record(ctl_meta.get("target"), events, t_loop0))
    p3b_ext["crawler_gap"] = _record_or_error(
        lambda: crawler_gap_summary(soil_rows, (ctl_meta.get("soil") or {}).get("t_loc_s"), t_loop0,
                                    first_ready_time(phases)))
    if model.soil_patch_leg is not None:  # G6: virgin-branch window of the soft leg (dynamics 2026-10-28)
        p3b_ext["virgin_branch"] = virgin_branch_record(
            series, soil_rows, ctl_meta.get("soil"), phases, leg=model.soil_patch_leg,
            fx_N=virgin_crossover_force_N(model.soil_patch_set.key, args.pad_variant, model.soil_patch_leg),
            t_loop_start_s=t_loop0)
    sensors_end = {**sensor_meta, "suite_setup": dict(suite.setup().config), "noise_seed": args.seed,
                   "zero_calibration": zero_calibration_outcome(ctl_meta),
                   "record_10hz": "record/record.npz: meas.head_pressure, meas.rod_pressure, meas.stroke, u_cmd "
                                  "(applied), u_applied; controller_commands.npz: issued commands"}
    n_steps = n_settle + res.n_steps
    wall = settle_wall + loop_wall
    run_meta_end = engine.meta()
    run_meta_end["c2_soil"] = ctl_meta.get("soil")  # S9Model.meta() placeholder -> the C2 meta soil block (P-S9-7)
    summary = {"action": "level", "args": vars(args), "placement": placement, "meta": run_meta_end,
               "runner_meta": res.meta, "build_s": build_s, "wall_s": wall, "settle_wall_s": settle_wall, "loop_wall_s": loop_wall,
               "n_steps": n_steps, "us_per_step": wall / max(n_steps, 1) * 1e6,
               "num_threads_chrono": model.num_threads, "fs_kN": args.fs_kN,
               "plant_s8": model.actuator.s8_meta(), "plant_s8_record": model.actuator.s8_record(),
               "c2_setup": c2_setup, "sensors": sensors_end, "c2_soil": ctl_meta.get("soil"),
               "c2_lifted_reapproach_history": ctl_meta.get("lifted_reapproach"),
               "c2_lifted_reapproach": c2_setup["lifted_reapproach"], "c2_timing": ctl_meta.get("timing"),
               "settle_reference": settle, "settle_slope": settle_slope, "rut_reference": rut,
               "t_loop_start_s": t_loop0,
               "phases": [{"t_s": t, "phase": p} for t, p in phases],
               "events": [{"t_s": t, "name": n} for t, n in events],
               "s9_rows": soil_rows, "r8_series": r8_series_info,
               "controller_meta": ctl_meta,  # same key as the run_S6C / S7C / S8C result.json (replay tools)
               # spec 420.4 (1): controller rules in the meta + file hashes at the start (record only)
               "code_state": _record_or_error(lambda: {**code_state_from_meta(ctl_meta),
                                                        "files_at_start": code_files}),
               "monitor": engine.step_monitor(),
               "gravity_schedule": gravity_schedule_meta(args, dashpot),
               "p3_records": p3_records(soil_rows, ctx["weight_N"], p3b["departure"].get("t_departure_s")),
               "p3b": p3b, "p3b_ext": p3b_ext,
               "mass_scale": _record_or_error(lambda: {
                   **mass_scale_record(mass_block, c2, ctl_meta),
                   "judgement_weights": judgement_weights(mass_scale, ctx["weight_N"],
                                                          (ctl_meta.get("soil") or {}).get("W_ref_N"), ctx["F_min_N"])}),
               "step_series": {"file": "step_series.npz", "rate_s": STEP_SERIES_S,
                                           "keys": sorted(series), "rows": int(len(series["t_s"]))}}
    (d / "result.json").write_text(json.dumps(_plain(summary), indent=1, ensure_ascii=False), "utf-8")
    engine.close()
    for w in p3b["W61_watch"]["warnings"]:
        print("WARNING", w, flush=True)
    print(json.dumps(_plain({"c2_soil": summary["c2_soil"], "checks": p3b["checks"],
                             "us_per_step": summary["us_per_step"]}), indent=1), flush=True)
    print("->", d, flush=True)
    return d


# --- CLI ------------------------------------------------------------------------------------------------


def _common(p: argparse.ArgumentParser) -> None:
    from outrigger_sim.pad_variants import add_pad_variant_argument

    p.add_argument("--soil", choices=("J1", "J2", "G1", "S1"), default="G1")
    add_pad_variant_argument(p)
    p.add_argument("--level", choices=("top", "middle", "bottom"), default="top")
    p.add_argument("--scm-shear", choices=("bprime", "native"), default="bprime")
    p.add_argument("--stiffness-mode", choices=("series", "l1_kt", "janosi"), default="series")
    p.add_argument("--interface", action="store_true")
    p.add_argument("--k-sw", type=float, default=1.5e4)
    p.add_argument("--grid", type=float, default=0.02)
    p.add_argument("--dt", type=float, default=1.0e-4)
    p.add_argument("--soil-override", nargs="*")
    p.add_argument("--threads", type=int, default=SCM_THREADS_FIXED,
                   help=f"SCM ray-casting OpenMP threads (num_threads_chrono), fixed default {SCM_THREADS_FIXED} "
                        "for every S9 action (dynamics 5.34.12: P3b with one thread count); 0 = Chrono default "
                        "(all processors, comparison only)")
    p.add_argument("--case", default=None, help="case name (output folder name; batch runs)")
    p.add_argument("--out-root", default=None, help="batch folder: write to <out-root>/<case>/ instead of a stamp")
    p.add_argument("--ray-shape", choices=("mesh", "convex"), default="mesh",
                   help="SCM ray targets: static triangle meshes (default, P1-V0) or the former convex box / hull")
    p.add_argument("--crawler-grid", type=float, default=None,
                   help="dual terrain: crawler terrain grid [m] (pads on --grid); default one terrain")


def _soil_patch_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--soil-patch", default=None, metavar="LEG:SET",
                   help="G6: that pad on a third SCM terrain with soil SET (needs --crawler-grid), e.g. RR:J1")
    p.add_argument("--soil-patch-grid", type=float, default=None,
                   help="G6: grid of the soil-patch terrain [m] (default --grid)")


def _gravity_ramp_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--t-settle", type=float, default=None,
                   help="settle time [s]; default gravity ramp + hold (P2 rule 3 + 2 s)")
    p.add_argument("--gravity-ramp", type=float, default=3.0, help="gravity ramp time [s] (5.34.2 P2)")
    p.add_argument("--gravity-hold", type=float, default=None,
                   help=f"hold after the ramp [s]; default {GRAVITY_HOLD_DASHPOT_S:g} s with the settle dashpot "
                        f"(5.35.4 (a)), {GRAVITY_HOLD_FORMER_S:g} s with --settle-dashpot none (5.34.2)")
    p.add_argument("--gravity-ramp-shape", choices=("poly345", "linear", "step"), default="poly345",
                   help="step = the former sudden gravity (comparison only)")
    from outrigger_sim.chrono.scm_model import (  # noqa: PLC0415
        SETTLE_DASHPOT_C_PITCH_N_M_S_RAD, SETTLE_DASHPOT_C_ROLL_N_M_S_RAD, SETTLE_DASHPOT_C_Z_N_S_M,
        SETTLE_DASHPOT_FADE_S)

    p.add_argument("--settle-dashpot", choices=("zrp", "none"), default="zrp",
                   help="zrp = ground-fixed heave + roll + pitch settle dashpot (default, U-S9P-1, 5.35.4 (a)); "
                        "none = the former settle (Poly345 3 s + hold 2 s)")
    p.add_argument("--dashpot-c-z", type=float, default=SETTLE_DASHPOT_C_Z_N_S_M, help="heave damping [N s/m]")
    p.add_argument("--dashpot-c-pitch", type=float, default=SETTLE_DASHPOT_C_PITCH_N_M_S_RAD,
                   help="pitch damping about the plane y axis [N m s/rad]")
    p.add_argument("--dashpot-c-roll", type=float, default=SETTLE_DASHPOT_C_ROLL_N_M_S_RAD,
                   help="roll damping about the plane x axis [N m s/rad]")
    p.add_argument("--dashpot-fade", type=float, nargs=2, default=SETTLE_DASHPOT_FADE_S, metavar=("T0", "T1"),
                   help="full damping until T0, linear to 0 at T1 [s]")


def main(argv) -> None:
    args = build_parser().parse_args(argv)
    if args.action == "plan":
        print(json.dumps(_plain(plan_summary()), indent=1))
    elif args.action == "single-pad":
        run_single_pad(args)
    elif args.action == "machine":
        run_machine(args)
    elif args.action == "rejudge":
        run_rejudge(args)
    else:
        run_level(args)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="action", required=True)
    sub.add_parser("plan")
    sp = sub.add_parser("single-pad")
    _common(sp)
    sp.add_argument("--leg", choices=("FL", "FR", "RL", "RR"), default="RL")
    sp.add_argument("--joint", choices=("spherical", "fixed"), default="spherical")
    sp.add_argument("--force", type=float, default=0.0, help="horizontal load +x on the share body [N]")
    sp.add_argument("--normal-load", type=float, default=None, help="default: design load of the leg")
    sp.add_argument("--t-settle", type=float, default=2.0, help="vertical load ramp + hold before the horizontal load")
    sp.add_argument("--t-ramp", type=float, default=0.5, help="horizontal load ramp [s]")
    sp.add_argument("--t-end", type=float, default=5.0)
    sp.add_argument("--load-ramp", type=float, default=1.0, help="vertical load (gravity) ramp [s] (5.34.3 P1-V0)")
    sp.add_argument("--load-ramp-shape", choices=("poly345", "linear", "step"), default="poly345",
                    help="step = the former sudden load (P1-V16d record only)")
    sp.add_argument("--load-steps", default=None,
                    help="vertical load factors, e.g. 0.25,0.5,0.75,1.0,0.5 (P1-V16a-c); replaces --load-ramp-shape")
    sp.add_argument("--step-ramp", type=float, default=0.5, help="Poly345 ramp between load steps [s]")
    sp.add_argument("--step-hold", default="auto",
                    help="hold per step [s], comma list or 'auto' = max(1 s, 5 tau) (dynamics 5.31.8)")
    sp.add_argument("--terrain-size", type=float, nargs=2, default=(1.2, 1.2),
                    help="SCM patch size x y [m] centred on the pad start (P1-L3 sliding: 6 1.2)")
    sp.add_argument("--force-limit-factor", type=float, default=None,
                    help="horizontal load = factor x anchor tangential limit at the full normal load (P1-L3)")
    mp = sub.add_parser("machine")
    _common(mp)
    _gravity_ramp_args(mp)
    _soil_patch_args(mp)
    mp.add_argument("--drift-window", type=float, default=10.0,
                    help="settle drift record over the last window [s] (P1-L5), when the settle is long enough")
    mp.add_argument("--lift-s", type=float, default=0.0, help="open-loop extension time after the settle")
    mp.add_argument("--lift-speed-fraction", type=float, default=1.0)
    mp.add_argument("--abort-on-limit", action="store_true",
                    help="P3a batch: exit 3 after writing the result when a cylinder force peak exceeds the 210 bar "
                         "extension limit or s_motor exceeds the end-margin stroke (the batch stops new launches)")
    mp.add_argument("--floor-roll", type=float, default=0.0)
    mp.add_argument("--floor-pitch", type=float, default=0.0)
    lp = sub.add_parser("level")
    _common(lp)
    _gravity_ramp_args(lp)
    _soil_patch_args(lp)
    lp.add_argument("--duration", type=float, default=P3B_DURATION_S,
                    help=f"closed-loop time after the settle [s], fixed (P3b {P3B_DURATION_S:g} s, control D-2; no end "
                         "rule; READY <= 90 s ASSUMPTION P3-6)")
    lp.add_argument("--fs-kN", type=float, default=0.0,
                    help="plant seal friction level of the front legs [kN] (rear x 0.8333, "
                         "actuator.seal_friction.level_N); 0 = no override (P3a plant). P3b: 4 (0 / 8 at top)")
    lp.add_argument("--imu-grade", default="ideal", choices=IMU_GRADES,
                    help="IMU error grade (sensors.imu.ImuGradeName), 10 ms samples; default ideal (control D-1). "
                         "A non-ideal grade sets the C2 target gyro_noise_std_rad_s to the grade value")
    lp.add_argument("--pressure-grade", default="normal", choices=PRESSURE_GRADES,
                    help="head / rod pressure and stroke sensors (control D-1): ideal = LegSensorConfig(), else "
                         "wika_a10_leg_sensor_config(grade) (WIKA A-10 errors, stroke noise 0.1 mm); default normal. "
                         "The CHECK zero calibration stays on (preset)")
    lp.add_argument("--floor-roll", type=float, default=0.0)
    lp.add_argument("--floor-pitch", type=float, default=0.0)
    lp.add_argument("--seed", type=int, default=P3B_SEED, help="sensor-suite noise seed")
    lp.add_argument("--approved", action="store_true")
    lp.add_argument("--allow-current-c2", action="store_true",
                    help="run a C2 config whose soil response is off (soil.enable False). The R8 preset "
                         "C2Config().with_10hz_d1() has it on (U-S9-C1, P-S9-8), so the guard only stops a preset "
                         "that lost it; soil-off comparison only (expected to fail on J1 B, J2 B, S1, spec 281)")
    lp.add_argument("--twist-relax", choices=TWIST_RELAX_MODES, default=TWIST_RELAX_PRESET,
                    help="P-S8-29 relaxed twist completion: preset = the R8 preset as it is (default), off = "
                         "twist_completion_relax.enable False only (counterfactual comparison; READY expected late "
                         "or none). Recorded in result.json c2_setup.twist_relax")
    lp.add_argument("--start-limit", choices=START_LIMIT_MODES, default=START_LIMIT_PRESET,
                    help="start / target slope limits: preset = the R8 preset as it is (operating D8 4.4 / 3.2 deg on "
                         "the crawler IMU attitude, default), verification = target.slope_limit_mode verification "
                         "(5.5 / 3.5 deg, the run_S8C meaning), verification_map = verification + the spec 13.1 "
                         "crawler settle map of --level, record_only = target acceptance off (the harness path; start "
                         "rule only recorded, study ① S9SL rows). Recorded in c2_setup.start_limit")
    lp.add_argument("--note", default=None, help="free case note, kept in result.json args (G6P batch rows)")
    lp.add_argument("--mass-scale", type=float, default=1.0,
                    help="plant superstructure mass / inertia factor, COG kept, controller unchanged (Q-D, spec 422; "
                         "1.0 = unchanged, bit for bit)")
    lp.add_argument("--allow-other-threads", action="store_true",
                    help=f"allow --threads != {SCM_THREADS_FIXED} (comparison only)")
    rj = sub.add_parser("rejudge", help="re-judge finished level cases with the spec rev. 60 P3-2 / 5 / 7 definitions "
                                        f"(no Chrono run; writes <case>/{REJUDGE_FILE}, result.json untouched)")
    rj.add_argument("paths", nargs="+", help="case folders or batch folders (their P3b_* cases)")
    rj.add_argument("--dry-run", action="store_true", help="print only, write nothing")
    return ap


if __name__ == "__main__":
    main(sys.argv[1:])
