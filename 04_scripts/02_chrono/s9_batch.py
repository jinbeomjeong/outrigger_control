"""S9 P1 / P2 batch driver (dynamics_model.md 5.34.13, rev. 49; user decision 2026-10-26).

Runs the cases of one batch as separate Chrono-dev processes (each pins itself to the P-cores,
``run_S9.place``), at most ``--parallel`` at a time (default 2: the main-tree regression shares the
P-cores). Writes ``07_results/S9/<batch>_<stamp>/``: one folder per case (``result.json`` +
``series.npz`` of run_S9), ``<case>.log`` (stdout / stderr), ``progress.log`` (one START and one
END line per case, read by the periodic monitor) and ``batch.json`` (argv, return code, wall time).
A failed case (return code != 0) stops new launches; running ones finish.

Usage (project root)::

    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py list
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run P1_V0p [--parallel 2]
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run P3b --parallel 4   # 2 S8C + 24 level (approved)
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run P3b --parallel-p 3 --parallel-e 2 \
        --e-cases P3b_G1_A_top_Fs4 ... --order lpt      # or --schedule plan.json
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run P3-10 --parallel 2   # rigid L1 soil on / off
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run p3b_aug --parallel 4 --order lpt   # study ③, 8 cases
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run S9SL --parallel 2   # study ① C-1 / C-2 (slope)
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run MS1 --parallel 0 --parallel-e 1 \
        --e-cases P3b_J1_B_top_Fs4_m1p1                 # Q-D: J1 B top, plant mass x1.1 (E pool)
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run D424 --parallel 2   # 424.6 A-8: MS1 re-run + x1.2
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run D424R --parallel 1 --parallel-e 2 \
        --e-cases P3b_J2_B_middle_Fs4,P3b_J2_B_bottom_Fs4   # 424.11.2: DSb75 re-check (J1 x1.1 P alone, J2 B on E)
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run RV1 --parallel 2 --parallel-e 2 \
        --e-cases S9SL_X4ed_J1_B_top_Fs4_r1p925_p1p4,P3b_J2_B_top_Fs4_m1p1   # paper review S2 / S3: X4 x3 + X5
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run RV2 --parallel 4   # P3b J1 B top F_s 0/4/8 + J2 B (DSb75)
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run RV3 --parallel 1 --parallel-e 1 \
        --e-cases S9SL_RV3B_S1_B_top_Fs0_r3p3_p0     # spec 426: study B S1 slope F_s 0 + study C G1+S1@FL pad A
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run RV4 --parallel 1 --parallel-e 1 \
        --e-cases P3b_J2_B_top_Fs4_sgFLg20           # study D (D2): J2 B top RR dip 150 mm + FL bump to gap 20 mm
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run RV5 --parallel 2   # study A (A1): 2 base -> event chains
    # final controller (spec 430.5 / 431.3; after the 03_src acceptance, rows refuse another preset):
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py list FINAL1            # rows, P / E estimates, sources
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py check-sources FINAL2   # rows reproduce the former run args
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run RV6 --rv6-k 0.65 --rv6-dir roll_neg --parallel 2 \
        --parallel-e 2 --only S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0 ...  # X6-rb = roll_neg k 0.65 (spec 430.3.1)
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run FINAL-R --parallel 5 --only-file final_r_acting.json
    # minimum representative set (user decision 2026-10-30 ~18 h, spec 432): soil 7 rows first, then rigid 16 + 2
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py list FINAL-REP         # rep_variable / r4_x11 per row
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run FINAL-R-REP --parallel 5 --row-filter optional=None
    # journal table soil 4 x auger 3 (cad 2026-10-31): 6 soil + 2 rigid rows (rigid s8c rows on the P pool)
    python -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run JOURNAL-AUGER --schedule <plan.json>

Pools (2026-10-26): ``--parallel`` (= ``--parallel-p``) P-pool slots, ``--parallel-e`` E-pool slots;
each case process gets ``OUTRIGGER_PLACEMENT`` = ``pcore`` / ``ecore`` (``run_S9.place``). Cases go to
the E pool only when named (``--e-cases`` or the ``--schedule`` JSON); ``--order given|lpt`` and
``--order-cases`` set the queue order. ``s8c`` rows stay on the P pool. ``--e-cases`` / ``--order-cases``
take names separated by spaces or commas (2026-10-30).

``s8c`` rows run ``run_S8C.py run --only <case>`` unchanged (no ``--case`` / ``--out-root``): the
S8 runner writes ``07_results/S8/<tag>_<stamp>/`` and prints it at the end of ``<case>.log``.
run_S8C exits 0 even when its case failed, so an ``s8c`` row with return code 0 is checked from its
log (:func:`s8c_case_check`: outcome line ``ok``, batch folder line, ``result.json``); a failed check
is recorded as rc 4 (``batch.json`` ``s8c_check``) and stops new launches like any failure.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PY = sys.executable
RUN = [PY, "-I", "-X", "utf8", "-u", str(HERE / "run_S9.py")]
EQ = [PY, "-I", "-X", "utf8", "-u", str(HERE / "s9_dual_terrain_equivalence.py")]
S8C = [PY, "-I", "-X", "utf8", "-u", str(HERE / "run_S8C.py")]

B = ["--pad-variant", "dwg_rear250"]
FORMER = ["--settle-dashpot", "none"]
"""Batches run before 2026-10-26 U-S9P-1 used the former settle (no dashpot, hold 2 s / given hold)."""
STEPS = ["--load-steps", "0.25,0.5,0.75,1.0,0.5", "--load-ramp", "1.0", "--step-ramp", "0.5", "--step-hold", "auto"]


def _g(h: float) -> str:
    return f"{h * 100:g}cm".replace(".", "p")


def batches(rv6_k: float | None = None, rv6_dir: str | None = None) -> dict[str, list[dict]]:
    """All batch definitions; ``rv6_k`` / ``rv6_dir`` = the X6-rb roll ratio / direction of RV6 (None =
    ``run_S9.RV6_K_DEFAULT`` 0.65 / ``RV6_DIR_DEFAULT`` roll_neg)."""
    out: dict[str, list[dict]] = {}
    # prep 1: dual-terrain equivalence E1-E4 (5.34.12)
    out["E_dual"] = [{"case": f"E_{lay}_rep{r}", "argv": EQ + ["run", "--layout", lay, "--rep", str(r)],
                      "eq_out": True, "est_s": 300} for lay in ("single", "dual") for r in (1, 2)]
    # P1-V0': single pad G1 RL fixed, Poly345 1 s + 1 s hold, 1 / 0.5 cm
    out["P1_V0p"] = [{"case": f"V0p_G1_B_RL_{_g(h)}", "est_s": 120,
                      "argv": RUN + ["single-pad", "--soil", "G1", *B, "--leg", "RL", "--joint", "fixed",
                                     "--grid", str(h), "--force", "0", "--t-settle", "2", "--t-end", "2"]}
                     for h in (0.01, 0.005)]
    v16 = []
    for soil in ("G1", "J1"):
        for leg in ("RL", "FL"):
            for h in (0.02, 0.01, 0.005):
                v16.append({"case": f"V16_{soil}_B_{leg}_{_g(h)}", "est_s": 300,
                            "argv": RUN + ["single-pad", "--soil", soil, *B, "--leg", leg, "--joint", "fixed",
                                           "--grid", str(h), "--force", "0", *STEPS]})
    for h in (0.02, 0.01):
        v16.append({"case": f"V16bp_J2_B_RL_{_g(h)}", "est_s": 150,
                    "argv": RUN + ["single-pad", "--soil", "J2", *B, "--leg", "RL", "--joint", "fixed",
                                   "--grid", str(h), "--force", "0", *STEPS]})
    v16.append({"case": "V16d_G1_B_RL_2cm_step", "est_s": 60,
                "argv": RUN + ["single-pad", "--soil", "G1", *B, "--leg", "RL", "--joint", "fixed", "--grid", "0.02",
                               "--force", "0", "--load-ramp-shape", "step", "--t-settle", "2", "--t-end", "2"]})
    out["P1_V16"] = v16
    lc = []
    for soil, h in (("J1", 0.01), ("G1", 0.02)):
        for shear in ("native", "bprime"):
            lc.append({"case": f"L1_{soil}_fixed_F0_{shear}_{_g(h)}", "est_s": 75,
                       "argv": RUN + ["single-pad", "--soil", soil, *B, "--leg", "RL", "--joint", "fixed",
                                      "--scm-shear", shear, "--grid", str(h), "--force", "0",
                                      "--t-settle", "3", "--t-end", "3"]})
    for F in (4450, 6980, 20000):
        lc.append({"case": f"L2_J1_B_RL_F{F}_1cm", "est_s": 320,
                   "argv": RUN + ["single-pad", "--soil", "J1", *B, "--leg", "RL", "--grid", "0.01",
                                  "--force", str(F), "--t-settle", "3", "--t-ramp", "0.5", "--t-end", "13.5"]})
    for soil in ("J1", "J2"):
        lc.append({"case": f"L3_{soil}_B_RL_1.2limit_1cm", "est_s": 150,
                   "argv": RUN + ["single-pad", "--soil", soil, *B, "--leg", "RL", "--grid", "0.01",
                                  "--force-limit-factor", "1.2", "--terrain-size", "6", "1.2",
                                  "--t-settle", "3", "--t-ramp", "0.5", "--t-end", "5.0"]})
    l4 = [("L4_J1_B_RL_1cm", ["--soil", "J1", *B, "--leg", "RL", "--grid", "0.01"]),
          ("L4_J1_A_FL_1cm", ["--soil", "J1", "--pad-variant", "cad330", "--leg", "FL", "--grid", "0.01"]),
          ("L4_G1_B_RL_2cm", ["--soil", "G1", *B, "--leg", "RL", "--grid", "0.02"]),
          ("L4_J1_B_RL_1cm_ksw0", ["--soil", "J1", *B, "--leg", "RL", "--grid", "0.01", "--k-sw", "0"])]
    for name, a in l4:
        lc.append({"case": name, "est_s": 450,
                   "argv": RUN + ["single-pad", *a, "--force", "0", "--load-ramp", "20", "--load-ramp-shape", "linear",
                                  "--t-settle", "22", "--t-end", "22"]})
    for soil, h in (("J1", 0.01), ("G1", 0.02)):
        lc.append({"case": f"L5_{soil}_M14s_pitch3.5", "est_s": 600,
                   "argv": RUN + ["machine", "--soil", soil, *B, "--grid", str(h), "--crawler-grid", "0.04",
                                  "--floor-pitch", "3.5", "--gravity-ramp", "3", "--gravity-hold", "12",
                                  "--drift-window", "10", *FORMER]})
    for joint in ("fixed", "spherical"):
        for dt in ("1e-4", "5e-5"):
            lc.append({"case": f"L6_J1_B_RL_native_{joint}_dt{dt}_1cm", "est_s": 180 * (2 if dt == "5e-5" else 1),
                       "argv": RUN + ["single-pad", "--soil", "J1", *B, "--leg", "RL", "--grid", "0.01",
                                      "--scm-shear", "native", "--joint", joint, "--dt", dt, "--force", "4450",
                                      "--t-settle", "3", "--t-ramp", "0.5", "--t-end", "7.5"]})
    out["P1_L"] = lc
    p2 = []
    for soil, h in (("J1", 0.01), ("J2", 0.01), ("S1", 0.02)):
        p2.append({"case": f"P2-1_{soil}_top_M14s", "est_s": 240,
                   "argv": RUN + ["machine", "--soil", soil, *B, "--grid", str(h), "--crawler-grid", "0.04", *FORMER]})
    for soil in ("J1", "S1"):
        p2.append({"case": f"P2-2_{soil}_top_single2cm", "est_s": 600,
                   "argv": RUN + ["machine", "--soil", soil, *B, "--grid", "0.02", *FORMER]})
    for lvl in ("middle", "bottom"):
        p2.append({"case": f"P2-3_G1_{lvl}_M14s", "est_s": 150,
                   "argv": RUN + ["machine", "--soil", "G1", *B, "--level", lvl, "--grid", "0.02",
                                  "--crawler-grid", "0.04", *FORMER]})
    out["P2"] = p2
    # P2prime (dynamics 5.35.4 / 5.35.5 #2, U-S9P-1): settle dashpot (runner default), t_end 8 s, M14s, top
    out["P2prime"] = [{"case": f"P2prime_{soil}_top_M14s_dashpot8s", "est_s": 420 if soil in ("J1", "J2") else 300,
                        "argv": RUN + ["machine", "--soil", soil, *B, "--grid", str(h), "--crawler-grid", "0.04",
                                       "--settle-dashpot", "zrp"]}
                       for soil, h in (("J1", 0.01), ("J2", 0.01), ("G1", 0.02), ("S1", 0.02))]
    # P3a (dynamics 5.36.5, U-S9P-5 (a) 2026-10-26): open-loop lift 28 s after the 8 s dashpot settle,
    # J1 / G1 x type B / A, top auger; --abort-on-limit = exit 3 on a force-limit or stroke-margin excess.
    # Order B J1, B G1, A J1, A G1: with 2 slots the two long J1 runs overlap the G1 pair (about 1.5 h)
    p3a = []
    for soil, pad, pv, h, est in (("J1", "B", "dwg_rear250", 0.01, 3600), ("G1", "B", "dwg_rear250", 0.02, 1800),
                                  ("J1", "A", "cad330", 0.01, 3600), ("G1", "A", "cad330", 0.02, 1800)):
        p3a.append({"case": f"P3a_{soil}_{pad}", "est_s": est,
                    "argv": RUN + ["machine", "--soil", soil, "--pad-variant", pv, "--grid", str(h),
                                   "--crawler-grid", "0.04", "--settle-dashpot", "zrp", "--lift-s", "28",
                                   "--level", "top", "--threads", "4", "--abort-on-limit"]})
    out["P3a"] = p3a
    out["P3b"] = p3b_batch()
    out["P3-10"] = p3_10_batch()
    out["G6"] = g6_batch()
    out["G6_opt"] = g6_batch(optional=True)
    out["G6P"] = g6p_batch()
    out["p3b_aug"] = level_rows("p3b_aug_cases")
    out["S9SL"] = level_rows("s9sl_cases")
    out["MS1"] = level_rows("ms1_cases")  # Q-D (2026-10-29): P3b J1 B top F_s 4 with plant mass x1.1
    out["D424"] = level_rows("d424_cases")  # spec 424.6 A-8: MS1 re-run + optional x1.2 (after the final controller)
    # spec 424.11.2 'Chrono 3건' (2026-10-30): DSb75 re-check, J1 B top x1.1 (P pool alone) + study ③ J2 B middle /
    # bottom (E pool): run D424R --parallel 1 --parallel-e 2 --e-cases P3b_J2_B_middle_Fs4 P3b_J2_B_bottom_Fs4
    out["D424R"] = level_rows("d424r_cases")
    # paper review S2 / S3 (user approval 2026-10-30): X4 J1 B slope k 0.875 x 3 directions (S9SL form) + X5 J2 B top
    # x1.1 (MS1 form); pools from the compute-scheduler-expert plan, e.g. run RV1 --parallel 2 --parallel-e 2
    # --e-cases S9SL_X4ed_J1_B_top_Fs4_r1p925_p1p4,P3b_J2_B_top_Fs4_m1p1
    out["RV1"] = level_rows("rv1_cases")
    # RV2 (user approval 2026-10-30): P3b J1 B top F_s 0 / 4 / 8 + J2 B top F_s 4 on the final controller (DSb75 fires
    # ~1 s after LOC in the offline replay of batch_P3b_20261026_122444); argv = the P3b rows. P pool, e.g.
    # run RV2 --parallel 4 (= run P3b --only <the 4 names>, but folder batch_RV2_*, batch_note, RV2 est_s)
    out["RV2"] = level_rows("rv2_cases")
    # RV3 (spec 426 gap studies, user decision 2026-10-30): B = S1 B roll_pos k0.75 F_s 0 (S9SL form), C = G1 + S1@FL
    # pad A (G6P form); pools from the compute-scheduler-expert plan, e.g. run RV3 --parallel 1 --parallel-e 1
    # --e-cases S9SL_RV3B_S1_B_top_Fs0_r3p3_p0 (or run RV3 --parallel 2)
    out["RV3"] = level_rows("rv3_cases")
    # RV4 (study D on Chrono, user decision 2026-10-30): P3b J2 B top F_s 4 + --pad-start-gap RR:d150 / FL:g20 (D2),
    # e.g. run RV4 --parallel 1 --parallel-e 1 --e-cases P3b_J2_B_top_Fs4_sgFLg20 (or run RV4 --parallel 2)
    out["RV4"] = level_rows("rv4_cases")
    # RV5 (study A on Chrono, user decision 2026-10-30; run after P-S8-37): J2 B top, triple layout, base + event rows
    # (FL RE1bF F_s 0, RR FS24 F_s 8 at mid(LOC, DONE) of the base); the event rows wait for their base (depends_on),
    # e.g. run RV5 --parallel 2 (one base -> event chain per P slot)
    out["RV5"] = level_rows("rv5_cases")
    # Final-controller re-runs (spec 430.5 / 431.3, user decision 2026-10-30; run after the 03_src acceptance, 431.1
    # step 6): every row runs the run-time preset C2Config().with_10hz_d1() and refuses to start unless it has the final
    # rules (run_S9 --expect-controller FINAL_CONTROLLER, spec 433). RV6 = X6-rp-sa, J2 B SGS checks k 0.75 / 0.875 (optional),
    # X6-rb at --rv6-dir / --rv6-k (default roll_neg k 0.65, spec 430.3.1) + the other direction (optional); FINAL1 .. FINAL5 = spec 431.3; FINAL6 = studies D / A (the
    # stopped RV4 / RV5) on the final controller; FINAL-R = rigid S8 L2b / S6 L1-R candidates (run only the rows whose
    # harness pair acts: --only / --only-file / --row-filter). Pools: compute-scheduler-expert plan (est_pool_s)
    sys.path.insert(0, str(HERE))
    try:
        import run_S9 as _r9  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    out["RV6"] = level_rows("rv6_cases", _r9.RV6_K_DEFAULT if rv6_k is None else float(rv6_k),
                            _r9.RV6_DIR_DEFAULT if rv6_dir is None else str(rv6_dir))
    for name in ("FINAL1", "FINAL2", "FINAL3", "FINAL4", "FINAL5", "FINAL6"):
        out[name] = level_rows("final_cases", name)
    out["FINAL-R"] = final_r_rows()
    # Minimum representative re-runs (user decision 2026-10-30 ~18 h, control spec 432): FINAL-REP = 7 soil rows
    # (priority 1, rows of RV6 / FINAL2 / FINAL1 unchanged + rep_variable / r4_x11_check); FINAL-R-REP = 18 FINAL-R rows
    # (16 required + 2 optional, priority 2). Drop rows whose harness pair does not act with --only / --only-file /
    # --row-filter (e.g. --row-filter optional=None keeps the 16 required rows). FINAL1 .. FINAL6 / FINAL-R stay.
    out["FINAL-REP"] = level_rows("final_rep_cases")
    out["FINAL-R-REP"] = final_r_rep_rows(out["FINAL-R"])
    # FINAL-REP-X (user approval 2026-10-31, spec 432.5.1): FINAL-REP P3b_J2_B_top_Fs4_m1p1 with a 180 s closed loop
    # (row ..._t180, argv = the FINAL-REP row with --duration 180); check-sources accepts only that difference
    out["FINAL-REP-X"] = level_rows("final_rep_x_cases")
    # JOURNAL-AUGER (cad 2026-10-31, journal table soil 4 x auger 3 on the final controller): the 6 missing soil cells
    # (FINAL1 / FINAL2 / FINAL5 rows unchanged) + 2 rigid flat F_s 4 cells (run_S8C set jaug, K24_top_flat_Fs4 form)
    out["JOURNAL-AUGER"] = journal_auger_rows()
    # COUPLED_eta085 (user decision 2026-11-04, criteria 9.1 revision 5): the 10 re-judgement rows, stored final-controller
    # runs + the shared-pump flow limit at eta_v 0.85, nominal compensator; run --resume <folder> continues a stopped batch
    out[COUPLED_BATCH] = coupled_rows(out["FINAL-REP"], out["FINAL-REP-X"], out["FINAL-R-REP"])
    # V5-VB (v5 spec 2.0, 3.3; definition only, rows and timing wait for D-3): the coupled soil rows with the v5
    # reference configuration VB (flow 0.85 + M2 + LC + controller window, valve 0.1 s on the soil rows)
    out[V5_VB_BATCH] = v5_vb_rows(out[COUPLED_BATCH])
    # V5-S6SEED (v5 criteria 13.6 / X-7; definition only, run after D-3): S6 with the noise seed changed, flow off x 4
    # seeds + flow on (COUPLED_eta085 S6 argv) x the stored seed
    out[V5_S6_SEED_BATCH] = v5_s6_seed_rows(out["FINAL-REP-X"], out[COUPLED_BATCH])
    # v5 stage 3 (criteria rev. 6 3, user decision D-3 2026-11-07): rigid T4 / T5 (VB 12, LS 6), R12 (3), family F
    # (2), soil V0v (3); V5-STAGE3 = these + V5-VB (3) + V5-S6SEED (5) = 34 rows (a run convenience)
    out[V5_T45_BATCH] = v5_t45_rows(out["FINAL-R"])
    out[V5_T45LS_BATCH] = v5_t45_rows(out["FINAL-R"], settings=tuple(V5_LS_ARGS), ids=V5_T45LS_IDS,
                                      group=V5_T45LS_BATCH)
    out[V5_R12_BATCH] = v5_r12_rows(out["FINAL-R"])
    out[V5_REC_BATCH] = v5_rec_rows()
    out[V5_V0V_BATCH] = v5_v0v_rows(out[V5_VB_BATCH])
    out[V5_STAGE3_BATCH] = v5_stage3_rows(out)
    # paper v5 (user decision 2026-11-08; definitions only): 2.8 open-loop lift SCM J1 B / G1 B on VB (+ optional V0
    # re-runs of the stored argv), 3.5.2 J_P run_S8C G4 / SS x F_s 0 / 4 / 8 on VB (+ optional V0 = final_C4G2)
    out[V5_OPENLOOP_BATCH] = v5_openloop_rows(out["P3a"])
    out[V5_OPENLOOP_V0_BATCH] = v5_openloop_rows(out["P3a"], setting="V0")
    # user decision 2026-11-08 H-1: J1 B VB with the proportional (flow-sharing) law instead of priority
    out[V5_OPENLOOP_PROP_BATCH] = v5_openloop_prop_rows(out[V5_OPENLOOP_BATCH])
    # F-6 (fb_targeted_rules.md 3.3, user decision 2026-11-08): J1 B VB (+ optional V0) at the budget speed, same stroke
    out[V5_OPENLOOP_FB_BATCH] = v5_openloop_fb_rows(out[V5_OPENLOOP_BATCH], out[V5_OPENLOOP_V0_BATCH])
    out[V5_JP_BATCH] = v5_jp_rows()
    out[V5_JP_V0_BATCH] = v5_jp_rows(setting="V0")
    # D-1 verification matrix Chrono rows (cad 2026-11-08, d1_chrono_rows.py): D1-CHRONO (16 required rows + roll /
    # slope candidates), D1-PSC (optional PS-c); built with this module's live VB argument functions
    out.update(_d1_batches())
    return out


def _d1_batches() -> dict[str, list[dict]]:
    sys.path.insert(0, str(HERE))
    try:
        import d1_chrono_rows  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    return d1_chrono_rows.d1_batches(sys.modules[__name__])


COUPLED_BATCH = "COUPLED_eta085"
COUPLED_FLOW_ARGS = {"flow_eta_v": 0.85, "flow_dp_comp_bar": 10.0, "flow_dp_unload_bar": 20.0, "flow_width_bar": 1.0,
                     "flow_law": "priority"}
"""Criteria 9.1 revision 5: eta_v 0.85, nominal compensator (8.3)."""
COUPLED_SOIL_ROWS: tuple[tuple[str, str, str, float, dict[str, float]], ...] = (
    ("S1", "batch_FINAL-REP_20261030_223359", "P3b_J1_B_top_Fs4", 13691.0, {"pcore": 11000.0, "ecore": 13700.0}),
    ("S6", "batch_FINAL-REP-X_20261031_020716", "P3b_J2_B_top_Fs4_m1p1_t180", 11954.0,
     {"pcore": 12000.0, "ecore": 15000.0}),
    ("S8", "batch_FINAL-REP_20261030_223359", "S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0", 14880.0,
     {"pcore": 15000.0, "ecore": 18700.0}),
)
"""(criteria id, stored batch, case, stored wall [s], pool estimates [s]). Stored walls: batch.json; S1 ran on the E pool
(P estimate = its FINAL-REP est_s), S6 and S8 on the P pool (E estimate = P x 1.25, the est_pool_s ratio of FINAL-REP)."""
COUPLED_RIGID_ROWS: tuple[tuple[str, str, str, float], ...] = (
    ("R2", "final_K24_top_fdown3.5_Fs4_20261030_224211", "K24_top_fdown3.5_Fs4", 691.0),
    ("R4", "final_K24_top_roll5.5_Fs4_20261030_230357", "K24_top_roll5.5_Fs4", 627.0),
    ("R16", "final_G1L_RE1bF_FL_top_o050_Fs4_20261031_004637", "G1L_RE1bF_FL_top_o050_Fs4", 1037.0),
    ("R12", "final_E_G4_Fs4_20261030_233941", "E_G4_Fs4", 881.0),
    ("R6", "final_K0V_top_rpB_Fs0_20261031_010357", "K0V_top_rpB_Fs0", 470.0),
    ("R8", "final_A_middle_rpB_Fs0_20261031_011149", "A_middle_rpB_Fs0", 464.0),
    ("R9", "final_A_bottom_rpB_Fs0_20261031_011936", "A_bottom_rpB_Fs0", 499.0),
)
"""(criteria id, stored folder under 07_results/S8, case, stored batch.json wall [s])."""
COUPLED_FLOW_EXTRA_S = 180.0
"""Added to the stored wall (estimate; measured 2026-11-04 on 26 s short rows, 8 processes at once: R4 +167 s, R6 +180 s,
soil coarse grid +95 s, about 1 ms per solved step, 16 s of the run saturated, 1e4 steps/s)."""


def coupled_flow_argv() -> list[str]:
    a = COUPLED_FLOW_ARGS
    return ["--flow-eta-v", f"{a['flow_eta_v']:g}", "--flow-dp-comp-bar", f"{a['flow_dp_comp_bar']:g}",
            "--flow-dp-unload-bar", f"{a['flow_dp_unload_bar']:g}", "--flow-width-bar", f"{a['flow_width_bar']:g}",
            "--flow-law", a["flow_law"]]


V5_VB_BATCH = "V5-VB"
V5_VB_ARGS = {**COUPLED_FLOW_ARGS, "valve_tau_s": 0.1, "rod_release_force": True, "lock_overlap_ratio": 0.02,
              "lock_closing_delay_s": 0.05, "lock_window_follows_plant": True, "extend_start_tracked": True}
"""v5 spec 3.3 VB (all ASSUMPTION values; delta_ol 2 %, t_c 50 ms, tau_v 0.1 s, eta_v 0.85) with the controller
``final_C4G2_P3`` (③ start bound, criteria revision 8 3.1, user decision 2026-11-08)."""
V5_P3_CONTROLLER = "final_C4G2_P3"
"""Controller tag of the VB / LS rows (run_S9 ``FINAL_P3_CONTROLLER``, ``v5_options.EXTEND_START_CONTROLLER_TAG``)."""
V5_P3_LAS_CONTROLLER = "final_C4G2_P3_LAS"
V5_LAS_CONTROLLER = "final_C4G2_LAS"
"""Tags of a row re-run after the LAS-b switch (2026-11-08; run_S9 ``FINAL_P3_LAS_CONTROLLER`` /
``FINAL_LAS_CONTROLLER``): the rows above keep the tags of their stored results, which the switched preset refuses
(``--expect-controller``); a re-run row takes these through :func:`with_expected_controller`, a reproduction of the
stored result runs through ``05_tests/unit/pre_las_preset_runner.py``."""


def v5_vb_argv() -> list[str]:
    a = V5_VB_ARGS
    return coupled_flow_argv() + ["--valve-tau-s", f"{a['valve_tau_s']:g}", "--rod-release-force",
                                  "--lock-overlap-ratio", f"{a['lock_overlap_ratio']:g}",
                                  "--lock-closing-delay-s", f"{a['lock_closing_delay_s']:g}",
                                  "--lock-window-follows-plant", "--extend-start-tracked"]


def with_expected_controller(argv: list[str], controller: str) -> list[str]:
    """``argv`` with the value of its ``--expect-controller`` replaced (unchanged without one)."""
    out = list(argv)
    if "--expect-controller" in out:
        out[out.index("--expect-controller") + 1] = controller
    return out


def v5_vb_rows(coupled: list[dict]) -> list[dict]:
    """The soil rows of :func:`coupled_rows` with the VB options instead of the flow options alone (controller
    ``final_C4G2_P3``: ``--expect-controller`` and ``controller`` follow). Not run here: the Chrono rows and their
    timing are decided after the harness verdict (D-3). ``check-sources V5-VB`` accepts exactly the VB arguments
    as the difference from the stored ``result.json`` args."""
    rows = []
    for row in coupled:
        if row.get("source_expected_diffs") != COUPLED_FLOW_ARGS:
            continue
        argv = row["argv"][:len(row["argv"]) - len(coupled_flow_argv())] + v5_vb_argv()
        if row.get("controller"):
            argv = with_expected_controller(argv, V5_P3_CONTROLLER)
        rows.append({**row, "argv": argv, "source_expected_diffs": dict(V5_VB_ARGS), "group": V5_VB_BATCH,
                     **({"controller": V5_P3_CONTROLLER, "p3_base_controller": row["controller"]}
                        if row.get("controller") else {}),
                     "rep_bundle": V5_VB_BATCH, "note": row["note"].replace(COUPLED_BATCH, V5_VB_BATCH)
                     .replace("flow limit on", "v5 VB (flow 0.85, M2, LC, controller window, valve 0.1 s)")})
    return rows


V5_S6_SEED_BATCH = "V5-S6SEED"
V5_S6_SEED_CRITERIA_ID = "S6"
V5_S6_SEEDS_FLOW_OFF = (20261026, 20261027, 20261028, 20261029)
"""v5 criteria 13.6: the stored seed (run_S9 ``P3B_SEED``) and three more (ASSUMPTION, user decision)."""
V5_S6_SEEDS_FLOW_ON = (20261026,)
P3B_SEED_STORED = 20261026
"""run_S9 ``P3B_SEED``, the seed of the stored S6 run: a row with it has no seed difference to accept."""


def _seed_argv(argv: list[str], seed: int) -> list[str]:
    out = list(argv)
    out[out.index("--seed") + 1] = str(seed)
    return out


def v5_s6_seed_rows(final_rep_x: list[dict], coupled: list[dict]) -> list[dict]:
    """v5 criteria 13.6 (⑤, X-7): the S6 row (``P3b_J2_B_top_Fs4_m1p1_t180``, same plant as the stored S6 pair: valve
    path = command ramp, LC and M2 off) with only ``--seed`` changed. Flow off: the FINAL-REP-X argv x
    :data:`V5_S6_SEEDS_FLOW_OFF`; flow on: the COUPLED_eta085 S6 argv x :data:`V5_S6_SEEDS_FLOW_ON`. The case name
    carries the seed (``<case>_seed<seed>[_flow]``, the output folder; ``--case`` is not compared). Not run here (D-3).
    ``check-sources V5-S6SEED`` accepts exactly the seed (and the flow arguments on the flow row) as the difference."""
    _, batch, case, wall, pools = next(r for r in COUPLED_SOIL_ROWS if r[0] == V5_S6_SEED_CRITERIA_ID)
    base_off = next(r for r in final_rep_x if r["case"] == case)
    base_on = next(r for r in coupled if r["case"] == case and r.get("criteria_id") == V5_S6_SEED_CRITERIA_ID)
    rows = []
    for seed, base, flow_args, tag in ([(s, base_off, {}, "") for s in V5_S6_SEEDS_FLOW_OFF]
                                       + [(s, base_on, dict(COUPLED_FLOW_ARGS), "_flow")
                                          for s in V5_S6_SEEDS_FLOW_ON]):
        expected = dict(flow_args)
        if seed != P3B_SEED_STORED:
            expected["seed"] = seed
        flow_text = "flow limit on (eta_v 0.85)" if flow_args else "flow off"
        rows.append({**base, "case": f"{case}_seed{seed}{tag}", "argv": _seed_argv(base["argv"], seed),
                     "est_s": pools["pcore"] + (COUPLED_FLOW_EXTRA_S if flow_args else 0.0),
                     "source_run": f"{batch}/{case}", "source_expected_diffs": expected or None,
                     "criteria_id": V5_S6_SEED_CRITERIA_ID, "stored_wall_s": wall, "group": V5_S6_SEED_BATCH,
                     "rep_bundle": V5_S6_SEED_BATCH,
                     "note": f"{V5_S6_SEED_BATCH} (v5 criteria 13.6): S6 {flow_text}, seed {seed}; "
                             f"pair 07_results/S9/{batch}/{case}"})
    return rows


# --- v5 stage 3 (criteria rev. 6 3, stage3_plan.md 2, stage3_impl_spec.md 3; user decision D-3 2026-11-07) -------------

V5_VB_RIGID_ARGS = {k: v for k, v in V5_VB_ARGS.items() if k != "valve_tau_s"}
"""VB on the rigid run_S8C rows: the row definition turns the valve lag 0.1 s on (``run_S8C.py`` S8 case), so the
argument set is V5_VB_ARGS without ``valve_tau_s`` (stage3_plan.md 1)."""
V5_LS_ARGS = {"LS1": (0.01, 0.05), "LS4": (0.02, 0.1)}
"""T4 sensitivity (criteria rev. 6 3 #13-18): (overlap ratio, closing delay [s]) instead of VB's (0.02, 0.05)."""
V5_STAGE3_CONTROLLER = "final_C4G2"
V5_T45_BATCH, V5_T45LS_BATCH, V5_R12_BATCH, V5_REC_BATCH, V5_V0V_BATCH, V5_STAGE3_BATCH = (
    "V5-T45", "V5-T45LS", "V5-R12", "V5-REC", "V5-V0V", "V5-STAGE3")
V5_T45_IDS = ("K0V_top_fup3.5_Fs0", "K0_top_fup3.2_Fs0", "K0V_top_roll5.5_Fs0", "K0_top_fdown3.2_Fs0",
              "K0V_top_fdown3.5_Fs0", "E_G4_Fs8", "K0_top_rpBop_Fs0", "E_RE1bF_Fs0", "E_RE1bF_Fs8",
              "K8_top_rpB_Fs8", "S_top_fdown3.5_wika_Fs8", "K8_top_fdown3.5_Fs8")
"""Criteria rev. 6 3 #1-12 (set p1r)."""
V5_T45LS_IDS = ("K0V_top_fup3.5_Fs0", "E_G4_Fs8", "E_RE1bF_Fs8")
"""Criteria rev. 6 3 #13-18 (x LS1, LS4)."""
V5_REC_ID = "G1R_FS24_FL_top_o050_Fs0"
V5_REC_SET = "v5rec"
V5_FINAL_R_C4G2 = "07_results/S9/batch_FINAL-R-C4G2_20261105"
"""The stored V0 C4G2 rigid runs (FINAL-R-C4G2): per-case wall and the V0 pair of E_G4_Fs4 (stage3_plan.md 2.2)."""
V5_RIGID_EXTRA_S = 180.0
V5_RIGID_VB_FACTOR = 1.08
"""stage3_plan.md 7.3 (ASSUMPTION): VB rigid wall = (V0 + 180 s) x 1.08."""
V5_REC_V0_PROXY_S = 1022.0
"""stage3_plan.md 7.3: family F V0 wall proxy = FINAL-R-C4G2 G1L_RE1bF_FL_top_Fs0 1,022 s."""
V5_SOIL_VB_FACTOR, V5_SOIL_V0V_FACTOR = 1.2, 1.0
"""stage3_plan.md 7.3 (ASSUMPTION): soil VB / V0v wall over the stored flow-limit (COUPLED) wall."""


def v5_rigid_setting_args(setting: str) -> dict:
    """The v5 arguments of a rigid row (``dest -> value``, run_S8C ``vars(args)`` form): VB, LS1, LS4 or V0 ({})."""
    if setting == "V0":
        return {}
    args = dict(V5_VB_RIGID_ARGS)
    if setting in V5_LS_ARGS:
        args["lock_overlap_ratio"], args["lock_closing_delay_s"] = V5_LS_ARGS[setting]
    elif setting != "VB":
        raise KeyError(f"unknown v5 rigid setting {setting!r}")
    return args


def v5_rigid_controller(setting: str) -> str:
    """Controller tag of a rigid row: ``final_C4G2_P3`` for VB and LS (criteria revision 8 3.1), else
    :data:`V5_STAGE3_CONTROLLER`."""
    return V5_P3_CONTROLLER if v5_rigid_setting_args(setting).get("extend_start_tracked") else V5_STAGE3_CONTROLLER


def v5_rigid_argv(setting: str) -> list[str]:
    """CLI form of :func:`v5_rigid_setting_args` (order of :func:`v5_vb_argv`)."""
    a = v5_rigid_setting_args(setting)
    if not a:
        return []
    return coupled_flow_argv() + ["--rod-release-force", "--lock-overlap-ratio", f"{a['lock_overlap_ratio']:g}",
                                  "--lock-closing-delay-s", f"{a['lock_closing_delay_s']:g}",
                                  "--lock-window-follows-plant"] + (
        ["--extend-start-tracked"] if a.get("extend_start_tracked") else [])


def _final_r_c4g2_walls() -> dict[str, float]:
    p = ROOT / V5_FINAL_R_C4G2 / "batch.json"
    if not p.is_file():
        return {}
    return {c["case"]: float(c["wall_s"]) for c in json.loads(p.read_text("utf-8")).get("cases", [])
            if c.get("wall_s") is not None}


def v5_rigid_row(case_id: str, set_name: str, setting: str, *, criteria_id: str, group: str, v0_wall_s: float,
                 source_run: str | None, pair_case: str | None, note: str, name: str | None = None) -> dict:
    """One rigid v5 stage 3 row (stage3_impl_spec.md 3.1): ``run_S8C run --set <set> --only <id> --tag
    v5s3_<setting>_<id> --approved --workers p7`` + the setting arguments. ``case`` is the batch name (folder / log);
    ``s8c_case_id`` the run_S8C id (outcome check). ``controller`` records ``code_at_launch`` (FINAL-R precedent)."""
    est = v0_wall_s if setting == "V0" else (v0_wall_s + V5_RIGID_EXTRA_S) * V5_RIGID_VB_FACTOR
    return {"case": name or case_id, "s8c_case_id": case_id, "est_s": round(est), "s8c": True,
            "argv": S8C + ["run", "--set", set_name, "--only", case_id, "--tag", f"v5s3_{setting}_{case_id}",
                           "--approved", "--workers", "p7"] + v5_rigid_argv(setting),
            "family": set_name, "engine": "L2b_NSC", "controller": v5_rigid_controller(setting),
            "criteria_id": criteria_id,
            "v5_setting": setting, "group": group, "rep_bundle": group, "source_run": source_run,
            "pair_case": pair_case, "note": note}


def v5_t45_rows(final_r: list[dict], *, settings: tuple[str, ...] = ("VB",), ids: tuple[str, ...] = V5_T45_IDS,
                group: str = V5_T45_BATCH) -> list[dict]:
    """V5-T45 (criteria rev. 6 3 #1-12, VB) or V5-T45LS (#13-18, LS1 / LS4: case ``<id>_<LS>``). ``source_run`` = the
    FINAL-R source of the id; the V0 wall = FINAL-R-C4G2 measured when there, else the FINAL-R estimate."""
    by_id = {r["case"]: r for r in final_r if r.get("s8c")}
    walls = _final_r_c4g2_walls()
    rows = []
    first_no = 13 if group == V5_T45LS_BATCH else 1
    k = 0
    for setting in settings:
        for cid in ids:
            base = by_id[cid]
            name = cid if setting == "VB" else f"{cid}_{setting}"
            rows.append(v5_rigid_row(
                cid, base["family"], setting, criteria_id=f"T45#{first_no + k}", group=group,
                v0_wall_s=walls.get(cid, float(base["est_s"])), source_run=base["source_run"], pair_case=None,
                name=name, note=f"{group} (v5 criteria rev. 6 3 #{first_no + k}): {cid} {setting}; T4 / T5 judge "
                                f"(4); V0 wall {'FINAL-R-C4G2' if cid in walls else 'FINAL-R estimate'}"))
            k += 1
    return rows


def v5_r12_rows(final_r: list[dict]) -> list[dict]:
    """V5-R12 (criteria rev. 6 3 #19 / 20 / 31): E_G4_Fs4 VB, E_G4_Fs4_ph0.05 VB and V0 (record, 8.3)."""
    by_id = {r["case"]: r for r in final_r if r.get("s8c")}
    walls = _final_r_c4g2_walls()
    v0 = walls.get("E_G4_Fs4", float(by_id["E_G4_Fs4"]["est_s"]))
    stored = f"{V5_FINAL_R_C4G2}/final_E_G4_Fs4/E_G4_Fs4"
    ph = "E_G4_Fs4_ph0.05"
    return [
        v5_rigid_row("E_G4_Fs4", by_id["E_G4_Fs4"]["family"], "VB", criteria_id="R12#19", group=V5_R12_BATCH,
                     v0_wall_s=v0, source_run=stored, pair_case=stored,
                     note="V5-R12 #19: E_G4_Fs4 VB; V0 pair = FINAL-R-C4G2 stored run (8.3)"),
        v5_rigid_row(ph, by_id[ph]["family"], "VB", criteria_id="R12#20", group=V5_R12_BATCH, v0_wall_s=v0,
                     source_run=by_id[ph]["source_run"], pair_case=f"{ph}_V0",
                     note="V5-R12 #20: E_G4_Fs4_ph0.05 VB; V0 pair = row #31"),
        v5_rigid_row(ph, by_id[ph]["family"], "V0", criteria_id="R12#31", group=V5_R12_BATCH, v0_wall_s=v0,
                     source_run=by_id[ph]["source_run"], pair_case=ph, name=f"{ph}_V0",
                     note="V5-R12 #31: E_G4_Fs4_ph0.05 V0 (final_C4G2, no v5 argument); VB pair = row #20")]


def v5_rec_rows() -> list[dict]:
    """V5-REC (criteria rev. 6 3 #29 / 30, family F): G1R_FS24_FL_top_o050_Fs0 VB and V0 (set v5rec)."""
    v0 = V5_REC_V0_PROXY_S
    return [
        v5_rigid_row(V5_REC_ID, V5_REC_SET, "VB", criteria_id="F#29", group=V5_REC_BATCH, v0_wall_s=v0,
                     source_run=None, pair_case=f"{V5_REC_ID}_V0",
                     note="V5-REC #29: family F (FS24 FL F_s 0 READY + 5 s + 0.050 s) VB; record (8.2)"),
        v5_rigid_row(V5_REC_ID, V5_REC_SET, "V0", criteria_id="F#30", group=V5_REC_BATCH, v0_wall_s=v0,
                     source_run=None, pair_case=V5_REC_ID, name=f"{V5_REC_ID}_V0",
                     note="V5-REC #30: family F V0 pair (final_C4G2, no v5 argument)")]


def v5_v0v_rows(v5_vb: list[dict]) -> list[dict]:
    """V5-V0V (criteria rev. 6 3 #32-34): the V5-VB soil rows with the stored argv + ``--valve-tau-s 0.1`` only
    (case ``<case>_v0v``); ``check-sources`` accepts exactly ``valve_tau_s`` as the difference."""
    vb_tail = len(v5_vb_argv())
    rows = []
    for vb_row in v5_vb:
        # V0v keeps the controller of the stored run (final_C4G2 family, no ③ bound)
        row = {k: v for k, v in vb_row.items() if k != "p3_base_controller"}
        argv = row["argv"][:len(row["argv"]) - vb_tail]
        if vb_row.get("p3_base_controller"):
            row["controller"] = vb_row["p3_base_controller"]
            argv = with_expected_controller(argv, vb_row["p3_base_controller"])
        stored_flow_wall = float(row["est_s"]) - COUPLED_FLOW_EXTRA_S
        rows.append({**row, "case": f"{row['case']}_v0v",
                     "argv": argv + ["--valve-tau-s", "0.1"],
                     "source_expected_diffs": {"valve_tau_s": 0.1}, "group": V5_V0V_BATCH, "rep_bundle": V5_V0V_BATCH,
                     "v5_setting": "V0v", "pair_case": row["case"],
                     "est_s": round((stored_flow_wall + COUPLED_FLOW_EXTRA_S) * V5_SOIL_V0V_FACTOR),
                     "est_pool_s": {k: round(v * V5_SOIL_V0V_FACTOR) for k, v in (row.get("est_pool_s") or {}).items()},
                     "note": f"V5-V0V (v5 criteria rev. 6 3 #32-34): {row['case']} stored argv + valve 0.1 s only; "
                             f"VB pair {row['case']}"})
    return rows


def v5_stage3_rows(out: dict[str, list[dict]]) -> list[dict]:
    """V5-STAGE3: the 34 rows of the seven stage 3 bundles (criteria rev. 6 3); names must be unique."""
    vb = [{**r, "v5_setting": "VB", "pair_case": f"{r['case']}_v0v"} for r in out[V5_VB_BATCH]]
    seed = [{**r, "v5_setting": r.get("v5_setting") or "S6SEED"} for r in out[V5_S6_SEED_BATCH]]
    rows = [*out[V5_T45_BATCH], *out[V5_T45LS_BATCH], *out[V5_R12_BATCH], *seed, *vb, *out[V5_REC_BATCH],
            *out[V5_V0V_BATCH]]
    names = [r["case"] for r in rows]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup or len(rows) != 34:
        raise RuntimeError(f"V5-STAGE3: {len(rows)} rows (34 expected), duplicate names {dup}")
    return rows


# --- paper v5 (user decision 2026-11-08): 2.8 open-loop lift and 3.5.2 J_P on VB (definitions only) ------------------

V5_OPENLOOP_BATCH, V5_OPENLOOP_V0_BATCH = "V5-OPENLOOP-VB", "V5-OPENLOOP-V0"
V5_OPENLOOP_SOURCE = "batch_P3a_20261026_092653"
"""v4 paper 2.7 / table 7 / figure 5 open-loop lift runs (07_results/S9, P3a rows, run_S9 ``machine --lift-s 28``)."""
V5_OPENLOOP_CASES: tuple[tuple[str, float, dict[str, float]], ...] = (
    ("P3a_J1_B", 1838.0, {"pcore": 2500.0, "ecore": 3100.0}),
    ("P3a_G1_B", 1312.0, {"pcore": 1800.0, "ecore": 2300.0}),
)
"""(case, stored batch.json wall [s], VB pool estimates [s]). Estimates (ASSUMPTION): the VB / V0 cost per step of the
build check (2026-11-08, 1 s settle + 1 s lift, alone on P: J1 2,891 / 2,543 us = 1.14, G1 2,457 / 2,075 us = 1.18) on
the stored wall (2 slots, 2026-10-26), + about 20 % for a loaded batch, rounded up; E = P x 1.25 (FINAL-REP ratio)."""
V5_JP_BATCH, V5_JP_V0_BATCH = "V5-JP-VB", "V5-JP-V0"
V5_JP_SOURCE = "07_results/S8/final_v4recheck_20261104_202815"
"""v4 paper 3.5.2 table 10 J_P (pressure-only) values: final-controller re-run of 2026-11-04 (controller before C4G2),
4 workers on the P pool; ``06_analysis/03_hydraulic/coupled/verdict/judgement_chrono/v4_recheck/recheck_values.json``."""
V5_JP_IDS = ("N_G4_Fs0_pressure", "N_G4_Fs4_pressure", "N_G4_Fs8_pressure",
             "N_SS_Fs0_pressure", "N_SS_Fs4_pressure", "N_SS_Fs8_pressure")
V5_JP_SET = "rest"
"""run_S8C set holding the N group (priority 3)."""
V5_JP_EST_S = {"VB": 1350.0, "V0": 870.0}
"""Per-row estimate [s] (ASSUMPTION): the measured walls of the same-event rigid rows of batch_V5-STAGE3_20261107_184341
(P pool, full batch): E_G4_Fs4 VB 1,348 s, E_G4_Fs8 VB 1,342 s, E_G4_Fs4_ph0.05 V0 862 s. The stage 3 rule
(V0 + 180 s) x 1.08 under-read those rows by 1.2-1.8 x, so it is not used here."""


def _batch_walls(folder: Path, key: str = "case") -> dict[str, float]:
    p = folder / ("batch.json" if (folder / "batch.json").is_file() else "batch_meta.json")
    if not p.is_file():
        return {}
    return {c.get(key) or c.get("case_id"): float(c["wall_s"]) for c in json.loads(p.read_text("utf-8")).get("cases", [])
            if c.get("wall_s") is not None}


def v5_openloop_rows(p3a: list[dict], *, setting: str = "VB") -> list[dict]:
    """Paper v5 2.8 (v4 2.7): the stored P3a open-loop lift rows J1 B / G1 B (``machine --lift-s 28``, top, dashpot
    settle, ``--abort-on-limit``) with argv unchanged + :func:`v5_vb_argv` (VB) or unchanged (V0 re-run on the current
    code, the code-drift pair). The plant options act (flow 0.85, valve 0.1 s, M2, LC); the controller window and the
    ③ bound have no consumer in an open loop (run_S9 records them as not applied), so no ``--expect-controller``.
    ``check-sources`` accepts exactly the VB arguments (V0: none) as the difference from the stored ``result.json``."""
    by_case = {r["case"]: r for r in p3a}
    rows = []
    for case, wall, pools in V5_OPENLOOP_CASES:
        base = by_case[case]
        vb = setting == "VB"
        est = pools if vb else {"pcore": wall, "ecore": round(wall * 1.25)}
        group = V5_OPENLOOP_BATCH if vb else V5_OPENLOOP_V0_BATCH
        rows.append({"case": f"{case}_{setting}", "argv": base["argv"] + (v5_vb_argv() if vb else []),
                     "est_s": est["pcore"], "est_pool_s": dict(est), "planned_pool": "pcore",
                     "source_run": f"{V5_OPENLOOP_SOURCE}/{case}",
                     "source_expected_diffs": dict(V5_VB_ARGS) if vb else None,
                     "v5_setting": setting, "stored_wall_s": wall, "group": group, "rep_bundle": group,
                     "pair_case": f"{case}_{'V0' if vb else 'VB'}",
                     "note": f"{group} (paper v5 2.8 open-loop lift, v4 2.7 table 7 / figure 5): {case} "
                             + ("v5 VB plant (flow 0.85, valve 0.1 s, M2, LC; controller options not applied)"
                                if vb else "stored argv re-run on the current code (V0, code-drift pair)")
                             + f"; stored 07_results/S9/{V5_OPENLOOP_SOURCE}/{case}"})
    return rows


V5_OPENLOOP_PROP_BATCH = "V5-OPENLOOP-VB-PROP"
V5_OPENLOOP_PROP_CASES = ("P3a_J1_B_VB",)
"""User decision 2026-11-08 H-1: the open-loop J1 B VB row with ``--flow-law proportional`` (flow sharing, same spool
drop on every section) instead of the VB ``priority`` (pre-compensated); all other arguments unchanged (ASSUMPTION law,
Q-M5 unanswered)."""


def v5_openloop_prop_rows(vb_rows: list[dict]) -> list[dict]:
    """:data:`V5_OPENLOOP_PROP_CASES` of ``V5-OPENLOOP-VB`` with the flow law value replaced by ``proportional``
    (case ``<case>_prop``, pair = the VB row). ``check-sources`` accepts exactly the VB arguments with
    ``flow_law = proportional`` as the difference from the stored P3a ``result.json``."""
    by_case = {r["case"]: r for r in vb_rows}
    rows = []
    for case in V5_OPENLOOP_PROP_CASES:
        base = by_case[case]
        argv = list(base["argv"])
        k = argv.index("--flow-law")
        if argv[k + 1] != "priority":
            raise RuntimeError(f"{case}: VB flow law {argv[k + 1]!r}, priority expected")
        argv[k + 1] = "proportional"
        rows.append({**base, "case": f"{case}_prop", "argv": argv,
                     "source_expected_diffs": {**base["source_expected_diffs"], "flow_law": "proportional"},
                     "v5_setting": "VB_prop", "group": V5_OPENLOOP_PROP_BATCH, "rep_bundle": V5_OPENLOOP_PROP_BATCH,
                     "pair_case": case,
                     "note": base["note"].replace(V5_OPENLOOP_BATCH, V5_OPENLOOP_PROP_BATCH)
                     .replace("flow 0.85", "flow 0.85 proportional law") + f"; priority pair {case}"})
    return rows


V5_OPENLOOP_FB_BATCH = "V5-OPENLOOP-FB"
V5_OPENLOOP_FB_CASES = ("P3a_J1_B",)
V5_OPENLOOP_FB_SPEED_FRACTION = 0.87684
"""fb_targeted_rules.md 3.3 (F-6, sealed 2026-11-08): budget speed Q_nom / sum(A_h v_max) = 50.1466 / 57.1902 L/min
(18.347 mm/s)."""
V5_OPENLOOP_FB_LIFT_S = 31.93
"""fb_targeted_rules.md 3.3: the same commanded stroke as the stored 28 s at v_max (585.9 mm)."""


def _fb_argv(argv: list[str]) -> list[str]:
    """``argv`` with ``--lift-s`` set to :data:`V5_OPENLOOP_FB_LIFT_S` and ``--lift-speed-fraction``
    :data:`V5_OPENLOOP_FB_SPEED_FRACTION` inserted after it (the stored P3a argv has no fraction)."""
    out = list(argv)
    if "--lift-speed-fraction" in out:
        raise RuntimeError("stored argv already has --lift-speed-fraction")
    k = out.index("--lift-s")
    out[k + 1] = f"{V5_OPENLOOP_FB_LIFT_S:g}"
    out[k + 2:k + 2] = ["--lift-speed-fraction", f"{V5_OPENLOOP_FB_SPEED_FRACTION:g}"]
    return out


def v5_openloop_fb_rows(vb_rows: list[dict], v0_rows: list[dict]) -> list[dict]:
    """F-6 (``fb_targeted_rules.md`` 3.3): ``P3a_J1_B_VB_FB`` = the ``V5-OPENLOOP-VB`` J1 row (stored P3a argv +
    :func:`v5_vb_argv`, priority law) with the budget speed and the same commanded stroke (:func:`_fb_argv`), and the
    optional pair ``P3a_J1_B_V0_FB`` (stored argv, same two changes). ``--abort-on-limit`` stays. ``check-sources``
    accepts exactly the VB arguments (V0: none) plus ``lift_s`` / ``lift_speed_fraction`` as the difference. The run
    ends at settle + 31.93 s (39.93 s), not 36 s."""
    fb = {"lift_s": V5_OPENLOOP_FB_LIFT_S, "lift_speed_fraction": V5_OPENLOOP_FB_SPEED_FRACTION}
    rows = []
    for setting, src in (("VB", vb_rows), ("V0", v0_rows)):
        by_case = {r["case"]: r for r in src}
        for case in V5_OPENLOOP_FB_CASES:
            base = by_case[f"{case}_{setting}"]
            vb = setting == "VB"
            rows.append({**base, "case": f"{case}_{setting}_FB", "argv": _fb_argv(base["argv"]),
                         "source_expected_diffs": {**(base["source_expected_diffs"] or {}), **fb},
                         "v5_setting": f"{setting}_FB", "group": V5_OPENLOOP_FB_BATCH,
                         "rep_bundle": V5_OPENLOOP_FB_BATCH, "optional": not vb,
                         "pair_case": f"{case}_{setting}",
                         "est_s": round(base["est_s"] * V5_OPENLOOP_FB_LIFT_S / 28.0 * 1.1),
                         "est_pool_s": {k: round(v * V5_OPENLOOP_FB_LIFT_S / 28.0 * 1.1)
                                        for k, v in base["est_pool_s"].items()},
                         "note": f"{V5_OPENLOOP_FB_BATCH} (fb_targeted_rules.md 3.3 F-6, record for paper 2.8): {case} "
                                 f"{setting} + --lift-speed-fraction {V5_OPENLOOP_FB_SPEED_FRACTION:g} + --lift-s "
                                 f"{V5_OPENLOOP_FB_LIFT_S:g}; pair {case}_{setting}"
                                 + ("" if vb else " (optional pair)")})
    return rows


def v5_jp_rows(*, setting: str = "VB") -> list[dict]:
    """Paper v5 3.5.2 (v4 table 10 pressure-only column, S8 item 9): run_S8C ``N_{G4,SS}_Fs{0,4,8}_pressure`` (L2b-NSC,
    rigid, top, pressure-only contact judge) with :func:`v5_rigid_argv` of ``setting`` (VB: controller
    ``final_C4G2_P3``; V0: current ``final_C4G2``, the controller-change pair of the 2026-11-04 source). ``source_run`` =
    the v4 re-run case folder; ``check-sources`` checks the set / id and the v5 arguments (:func:`v5_rigid_source_check`).
    ``est_s`` = :data:`V5_JP_EST_S` (or the stage 3 rule when larger); ``stored_wall_s`` = the v4 re-run wall (4 workers
    on P)."""
    walls = _batch_walls(ROOT / V5_JP_SOURCE)
    group = V5_JP_BATCH if setting == "VB" else V5_JP_V0_BATCH
    rows = []
    for k, cid in enumerate(V5_JP_IDS, 1):
        name = cid if setting == "VB" else f"{cid}_V0"
        r = v5_rigid_row(cid, V5_JP_SET, setting, criteria_id=f"JP#{k}", group=group,
                         v0_wall_s=walls.get(cid, 500.0), source_run=f"{V5_JP_SOURCE}/{cid}",
                         pair_case=f"{cid}_V0" if setting == "VB" else cid, name=name,
                         note=f"{group} (paper v5 3.5.2, v4 table 10 J_P): {cid} {setting}; pair "
                              f"{V5_JP_SOURCE}/{cid} (v4 value, controller before C4G2)"
                              + ("" if setting == "VB" else "; separates the controller change from VB"))
        argv = r["argv"]
        argv[argv.index("--tag") + 1] = f"v5jp_{setting}_{cid}"
        r["stored_wall_s"] = walls.get(cid)
        r["est_s"] = round(max(float(r["est_s"]), V5_JP_EST_S[setting]))
        rows.append(r)
    return rows


def coupled_rows(final_rep: list[dict], final_rep_x: list[dict], final_r_rep: list[dict]) -> list[dict]:
    """The rows of the stored runs, argv unchanged + :func:`coupled_flow_argv`; rigid rows in their own folder
    ``07_results/S8/coupled_eta085_<case>_<stamp>``. ``s9_batch check-sources COUPLED_eta085`` accepts exactly the flow
    arguments as the difference from the stored ``result.json`` args of the soil rows."""
    soil_rows = {c["case"]: c for c in [*final_rep, *final_rep_x]}
    rigid_rows = {c["case"]: c for c in final_r_rep}
    rows: list[dict] = []
    for rid, batch, case, wall, pools in COUPLED_SOIL_ROWS:
        rows.append({**soil_rows[case], "argv": soil_rows[case]["argv"] + coupled_flow_argv(),
                     "est_s": pools["pcore"] + COUPLED_FLOW_EXTRA_S,
                     "est_pool_s": {k: v + COUPLED_FLOW_EXTRA_S for k, v in pools.items()},
                     "source_run": f"{batch}/{case}", "source_expected_diffs": dict(COUPLED_FLOW_ARGS),
                     "criteria_id": rid, "stored_wall_s": wall, "group": COUPLED_BATCH, "rep_bundle": COUPLED_BATCH,
                     "note": f"{COUPLED_BATCH} {rid} (criteria 9.1): flow limit on; pair 07_results/S9/{batch}/{case}"})
    for rid, folder, case, wall in COUPLED_RIGID_ROWS:
        row = rigid_rows[case]
        argv = list(row["argv"])
        argv[argv.index("--tag") + 1] = f"coupled_eta085_{case}"
        rows.append({**row, "argv": argv + coupled_flow_argv(), "est_s": wall + COUPLED_FLOW_EXTRA_S,
                     "fixed_pcore": True, "criteria_id": rid, "stored_wall_s": wall, "group": COUPLED_BATCH,
                     "rep_bundle": COUPLED_BATCH, "controller": "final_SGS_R4",
                     "source_run": f"{folder}/{case}",
                     "note": f"{COUPLED_BATCH} {rid} (criteria 9.1): flow limit on; pair 07_results/S8/{folder}/{case}"})
    return rows


FINAL_ROW_KEYS = ("controller", "source_run", "priority", "pair_case", "pair_run", "optional", "requires",
                  "harness_case", "cid", "group", "k", "direction", "h9_result",
                  "rep_bundle", "rep_source", "rep_variable", "r4_x11_check", "expected_note", "rep_role",
                  "source_expected_diffs")
"""Row keys of the RV6 / FINAL rows (rows with ``controller``) copied into the batch row and batch.json."""


def level_rows(fn_name: str, *fargs) -> list[dict]:
    """``run_S9.py level`` rows of ``run_S9.<fn_name>(*fargs)`` (study ③ ``p3b_aug_cases``: J2 / S1 x A / B x auger
    middle / bottom, P3b settings; study ① ``s9sl_cases``: the confirmed slope rows C-1 / C-2, drafts excluded).
    ``est_s`` from the case; ``note`` (``pair_case`` / ``purpose``) copied into batch.json; RV6 / FINAL rows (with
    ``controller``) also carry :data:`FINAL_ROW_KEYS`."""
    sys.path.insert(0, str(HERE))
    try:
        import run_S9 as r9  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    rows = []
    for c in getattr(r9, fn_name)(*fargs):
        note = (c.get("batch_note") or c.get("note")
                or (f"pair {c['pair_case']}" if c.get("pair_case") else c.get("purpose")))
        row = {"case": c["case"], "est_s": c["est_s"], "argv": RUN + r9.p3b_level_argv(c)}
        if note:
            row["note"] = note
        if c.get("planned_pool"):  # D424R (2026-10-30): intended pool, informative (--e-cases sets the pool)
            row["planned_pool"] = c["planned_pool"]
        if c.get("est_pool_s"):  # RV1 (2026-10-30): estimate per pool, informative (est_s = the planned pool)
            row["est_pool_s"] = dict(c["est_pool_s"])
        if c.get("depends_on"):  # RV5 (2026-10-30): start only after that row ended with rc 0
            row["depends_on"] = c["depends_on"]
        if c.get("controller"):  # RV6 / FINAL (2026-10-30)
            row.update({k: c[k] for k in FINAL_ROW_KEYS if k in c})
        rows.append(row)
    return rows


S6C = [PY, "-I", "-X", "utf8", "-u", str(HERE / "run_S6C.py")]
FINAL_R_S8_SOURCES = {"p1r": "07_results/S8/p1r_20261024_222013", "rest": "07_results/S8/rest_20261024_233615",
                      "g1": "07_results/S8/c72_20261027_155426", "c74": "07_results/S8/c74_20261027_164128"}
"""FINAL-R S8 L2b sets (run_S8C ``--set``; p1r 37, rest 49, C-S8-72 ``g1`` 11, C-S8-74 ``c74`` 16) and their former
batch folders (wall per case from ``batch.json``)."""
FINAL_R_S6_SET = "g8c76_p28acc"
FINAL_R_S6_SOURCE = "07_results/S6/bundleC_g8c76_p28acc_p28_L1R_20261027_222426"
FINAL_R_S6_CASES = ("G8C1_top_edge_FL_g170", "G8C3_top_edge_FL_g20", "G8C3_top_edge_RL_g230", "G8C4_top_edge_RR_g230")
"""Spec 431.5 (control 2026-10-30): the four table-14 rows ('반영') = run_S6C set ``g8c76_p28acc`` (C3 / C4 + the C1
FL g170 re-run, P-S8-28 acceptance; needs ``--allow-p28-cases``), former run :data:`FINAL_R_S6_SOURCE`. The older
``g8c76`` run (bundleC_g8c76_c76_L1R_20261027_211309) is not re-run."""
FINAL_R_EST_S = 330.0
"""Wall per S8 L2b case without a measured value [s] (spec 431.2: about 330 s, 07_results/S8/p1r_*)."""


def _source_walls(folder: str) -> dict[str, float]:
    """``case_id`` -> ``wall_s`` of a run_S8C / run_S6C ``batch.json`` (empty when absent)."""
    p = ROOT / folder / "batch.json"
    if not p.is_file():
        return {}
    doc = json.loads(p.read_text("utf-8"))
    return {c.get("case_id") or c.get("case"): float(c["wall_s"]) for c in doc.get("cases", [])
            if (c.get("case_id") or c.get("case")) and c.get("wall_s") is not None}


def final_r_rows() -> list[dict]:
    """FINAL-R candidates (spec 431.2 / 431.3: rigid S8 L2b paper cases + S6 bundle-C L1-R G8, on the final controller
    only where the harness pair acts; that decision comes later, so this is the full list). One process per case:
    ``run_S8C.py run --set <set> --only <id>`` (``s8c`` row, P pool, own folder ``07_results/S8/final_<id>_<stamp>``,
    checked by :func:`s8c_case_check`) or ``run_S6C.py run --set g8c76_p28acc --only <id> --allow-p28-cases --jobs 1``
    (``s6c`` row, :data:`FINAL_R_S6_CASES`, P pool, own folder ``07_results/S6/bundleC_g8c76_p28acc_final_<id>_*``,
    return code only). An id in two S8 sets is kept once (first
    set, ``also_in``). ``est_s`` = the former wall of the case (mixed P / E, 15 workers) or :data:`FINAL_R_EST_S`.
    These runners take the run-time preset as they are (no ``--expect-controller``); s9_batch records the controller
    file hashes and the commit at each launch (``code_at_launch``)."""
    sys.path.insert(0, str(HERE))
    try:
        import run_S6C as s6  # noqa: PLC0415
        import run_S8C as s8  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    rows: list[dict] = []
    seen: dict[str, dict] = {}
    for set_name, src in FINAL_R_S8_SOURCES.items():
        walls = _source_walls(src)
        for c in s8.case_set(set_name):
            if c.case_id in seen:
                seen[c.case_id].setdefault("also_in", []).append(set_name)
                continue
            row = {"case": c.case_id, "est_s": round(walls.get(c.case_id, FINAL_R_EST_S)), "s8c": True,
                   "argv": S8C + ["run", "--set", set_name, "--only", c.case_id, "--tag", f"final_{c.case_id}",
                                  "--approved", "--workers", "p7"],
                   "family": set_name, "s8_group": c.group, "engine": c.engine, "source_run": f"{src}/{c.case_id}",
                   "priority": 2, "group": "FINAL-R",
                   "note": f"FINAL-R (spec 431.3): S8 {set_name} {c.case_id} on the run-time preset; source {src}"}
            seen[c.case_id] = row
            rows.append(row)
    walls = _source_walls(FINAL_R_S6_SOURCE)
    s6_cases = {c.case_id: c for c in s6.CASE_SETS[FINAL_R_S6_SET]()}
    missing = sorted(set(FINAL_R_S6_CASES) - set(s6_cases))
    if missing:
        raise KeyError(f"run_S6C set {FINAL_R_S6_SET} lacks {missing}")
    for cid in FINAL_R_S6_CASES:
        c = s6_cases[cid]
        rows.append({"case": c.case_id, "est_s": round(walls.get(c.case_id, FINAL_R_EST_S)), "s6c": True,
                     "fixed_pcore": True, "family": FINAL_R_S6_SET, "engine": "L1R", "group": "FINAL-R",
                     "argv": S6C + ["run", "--set", FINAL_R_S6_SET, "--only", c.case_id, "--approved",
                                    "--allow-p28-cases", "--jobs", "1", "--tag", f"final_{c.case_id}"],
                     "source_run": f"{FINAL_R_S6_SOURCE}/{c.case_id}", "priority": 2,
                     "note": f"FINAL-R (spec 431.3): S6 bundle C {c.case_id} on the run-time preset; source "
                             f"{FINAL_R_S6_SOURCE}"})
    return rows


FINAL_R_REP_ROWS: tuple[tuple[str, str, bool], ...] = (
    ("A1", "K24_top_flat_Fs4", False),
    ("A2", "K24_top_fdown3.5_Fs4", False),
    ("A2", "K24_top_fup3.5_Fs4", False),
    ("A2", "K24_top_roll5.5_Fs4", False),
    ("A2", "K24_top_rpB_Fs4", False),
    ("A3", "G8C1_top_edge_FL_g170", False),
    ("A3", "G8C3_top_edge_RL_g230", False),
    ("A3", "G8C3_top_edge_FL_g20", True),
    ("A3", "G8C4_top_edge_RR_g230", True),
    ("A4", "E_G4_Fs4", False),
    ("A4", "E_SS_Fs4", False),
    ("A4", "E_RE1bF_Fs8", False),
    ("A4", "G1L_RE1bF_FL_top_Fs0", False),
    ("A4", "G1L_RE1bF_FL_top_o050_Fs4", False),
    ("B1", "K0V_top_rpB_Fs0", False),
    ("B1", "A_middle_rpB_Fs0", False),
    ("B1", "A_bottom_rpB_Fs0", False),
    ("B2", "K8_top_rpB_Fs8", False),
)
"""(``rep_variable``, FINAL-R case, ``optional``) of FINAL-R-REP (user list 2026-10-30, spec 432): A1 flat, A2 slope /
twist, A3 non-planar start (G8), A4 events, B1 auger level, B2 F_s. 18 rows = 16 required + 2 optional (A3 C3 FL g20,
C4 RR g230)."""
FINAL_R_REP_PRIORITY = 2


def final_r_rep_rows(final_r: list[dict] | None = None) -> list[dict]:
    """FINAL-R-REP: copies of the :data:`FINAL_R_REP_ROWS` rows of :func:`final_r_rows` (argv / est_s / source_run /
    group unchanged, so ``code_at_launch`` is recorded as for FINAL-R) + ``rep_bundle`` / ``rep_variable`` /
    ``optional`` / ``priority``. A name absent from FINAL-R raises KeyError (no invented names)."""
    by = {c["case"]: c for c in (final_r if final_r is not None else final_r_rows())}
    missing = [n for _, n, _ in FINAL_R_REP_ROWS if n not in by]
    if missing:
        raise KeyError(f"FINAL-R-REP: not FINAL-R rows: {missing}")
    out = []
    for var, name, optional in FINAL_R_REP_ROWS:
        r = dict(by[name])
        r["argv"] = list(r["argv"])
        r.update(rep_bundle="FINAL-R-REP", rep_source="FINAL-R", rep_variable=var, priority=FINAL_R_REP_PRIORITY,
                 note=f"FINAL-R-REP {var}{' (optional)' if optional else ''}: " + str(r.get("note") or name))
        if optional:
            r["optional"] = True
        out.append(r)
    return out


JOURNAL_AUGER_SOIL_ROWS: tuple[tuple[str, str, str], ...] = (
    ("FINAL2", "P3b_J1_B_middle_Fs4", "B1"),
    ("FINAL2", "P3b_J1_B_bottom_Fs4", "B1"),
    ("FINAL2", "P3b_J2_B_bottom_Fs4", "B1"),
    ("FINAL1", "P3b_G1_B_top_Fs4", "기준"),
    ("FINAL5", "P3b_G1_B_middle_Fs4", "B1"),
    ("FINAL5", "P3b_G1_B_bottom_Fs4", "B1"),
)
"""(source bundle, case, ``rep_variable``) of the JOURNAL-AUGER soil rows: pad B, F_s 4 kN, flat, mass x1.0, P3b
settings, final controller (``--expect-controller`` = ``run_S9.FINAL_CONTROLLER``); rows copied from :func:`level_rows` of the bundle
(argv / ``source_run`` / ``est_pool_s`` unchanged). The cells J1 top, J2 top, J2 middle are FINAL-REP rows."""
JOURNAL_AUGER_RIGID_CASES = ("JA_middle_flat_Fs4", "JA_bottom_flat_Fs4")
JOURNAL_AUGER_RIGID_EST_S = 600.0
"""ASSUMPTION: wall per rigid row [s] (FINAL-R-REP K24_top_flat_Fs4 464 s, A_middle / A_bottom rpB 466 / 500 s on the
P pool with 7 SCM runs concurrent, rounded up)."""
JOURNAL_AUGER_PRIORITY = 1


def journal_auger_rows() -> list[dict]:
    """JOURNAL-AUGER (8 rows): :data:`JOURNAL_AUGER_SOIL_ROWS` (``run_S9.py level``) + the run_S8C ``jaug`` set (one
    ``s8c`` row per case, the FINAL-R form: ``run --set jaug --only <id> --tag final_<id> --approved --workers p7``,
    group FINAL-R so that ``code_at_launch`` is recorded, P pool). Tags ``rep_bundle`` JOURNAL-AUGER, ``rep_source``,
    ``rep_variable``, ``priority``. A missing source row raises KeyError."""
    out: list[dict] = []
    by_bundle: dict[str, dict[str, dict]] = {}
    for bundle, case, var in JOURNAL_AUGER_SOIL_ROWS:
        if bundle not in by_bundle:
            by_bundle[bundle] = {c["case"]: c for c in level_rows("final_cases", bundle)}
        if case not in by_bundle[bundle]:
            raise KeyError(f"JOURNAL-AUGER: {case} is not a {bundle} row")
        r = dict(by_bundle[bundle][case])
        r["argv"] = list(r["argv"])
        r.update(rep_bundle="JOURNAL-AUGER", rep_source=bundle, rep_variable=var, priority=JOURNAL_AUGER_PRIORITY,
                 rep_role="journal auger table (soil x auger level)",
                 note=f"JOURNAL-AUGER {var} (row of {bundle}): " + str(r.get("note") or case))
        out.append(r)
    sys.path.insert(0, str(HERE))
    try:
        import run_S8C as s8  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    ids = [c.case_id for c in s8.case_set("jaug")]
    if tuple(ids) != JOURNAL_AUGER_RIGID_CASES:
        raise KeyError(f"JOURNAL-AUGER: run_S8C set jaug is {ids}, expected {list(JOURNAL_AUGER_RIGID_CASES)}")
    for cid in ids:
        out.append({"case": cid, "est_s": JOURNAL_AUGER_RIGID_EST_S, "s8c": True,
                    "argv": S8C + ["run", "--set", "jaug", "--only", cid, "--tag", f"final_{cid}", "--approved",
                                   "--workers", "p7"],
                    "family": "jaug", "s8_group": s8.JAUG_GROUP, "engine": "L2b_NSC", "group": "FINAL-R",
                    "priority": JOURNAL_AUGER_PRIORITY, "rep_bundle": "JOURNAL-AUGER", "rep_source": "FINAL-R-REP A1",
                    "rep_variable": "B1", "rep_role": "journal auger table (rigid flat, K24_top_flat_Fs4 form)",
                    "note": f"JOURNAL-AUGER B1 rigid: {cid} = K24_top_flat_Fs4 with the auger level changed "
                            "(run_S8C set jaug, run-time preset)"})
    return out


def g6p_batch() -> list[dict]:
    """G6P paper evidence set (user decision 2026-10-28): the ``run_S9.g6p_cases`` closed-loop rows (G1 base,
    pad B, top, F_s 4 kN): J1@RR P-S8-29 off 240 s (``_noTR``), J1@RR 160 s, J1@FL 200 s, J2@RR 200 s, J2@FL
    200 s, S1@FL 160 s (model-limit stress case, outside the Bekker validity range). ``est_s`` = run_S9.G6P_EST_S
    (``--order lpt`` sorts on it); a row ``note`` is copied into batch.json."""
    sys.path.insert(0, str(HERE))
    try:
        import run_S9 as r9  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    rows = []
    for c in r9.g6p_cases():
        row = {"case": c["case"], "est_s": c["est_s"], "argv": RUN + r9.p3b_level_argv(c)}
        if c.get("note"):
            row["note"] = c["note"]
        rows.append(row)
    return rows


def g6_batch(optional: bool = False) -> list[dict]:
    """G6 soil patch (cad G6 study, user decisions 2026-10-27 / 28; acceptance after P-S8-29). ``G6``: the
    open-loop layout control G6-0a (``run_S9.py machine``, P3a G1 B arguments + G1 patch under RR; compare
    afterwards with ``s9_g6_patch_compare.py``) and the ``run_S9.g6_cases`` closed-loop runs (J1 under RR 160 s
    / FL 200 s, G1-patch control 120 s). ``G6_opt``: G6-0b (open loop, J1 under RR)."""
    sys.path.insert(0, str(HERE))
    try:
        import run_S9 as r9  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    rows = [{"case": c["case"], "est_s": c["est_s"], "argv": RUN + r9.g6_machine_argv(c)}
            for c in r9.g6_open_loop_cases() if c["optional"] is optional]
    if not optional:
        rows += [{"case": c["case"], "est_s": c["est_s"], "argv": RUN + r9.p3b_level_argv(c)} for c in r9.g6_cases()]
    return rows


M3 = [PY, "-I", "-X", "utf8", "-u", str(HERE / "s9_merge" / "m3_run.py")]
P3_10_KEYS = ("flat", "rpB")
"""Control spec 284 P3-10: L1 rigid floor, top auger, D8 on the flat floor and on rpB (beta 1.0),
``s9_merge/m3_run.py`` keys (the M-3 runner of spec 295 / 297.3, 089bfd5)."""
P3_10_EST_S = 600.0
"""ASSUMPTION: 'a few minutes per case' (spec 284 P3-10 note); one L1 bundle-C D8 run."""


def p3_10_batch() -> list[dict]:
    """P3-10 (control spec 284, outside the P3b set, before the rev. 60 judgement): the two L1 rigid
    cases with the C2 soil response on (R8 preset) and off (soil.enable False, re-approach limit None),
    4 runs of ``m3_run.py <key> <on|off> <batch folder>``; compared by ``s9_batch_summary.py P3-10``
    (issued-command and event SHA-256). m3_run pins itself to the P-cores (P pool only)."""
    return [{"case": f"P3-10_{key}__{variant}", "est_s": P3_10_EST_S, "m3": True, "fixed_pcore": True,
             "argv": M3 + [key, variant]} for key in P3_10_KEYS for variant in ("on", "off")]


def p3b_batch() -> list[dict]:
    """P3b (control spec 284, U-S9P-6 (가); dynamics 5.37.6): the two re-approach 10 s limit positive
    tests first (run_S8C L2b-NSC rigid floor, R8 preset ``with_10hz_d1``, one case per process, own
    folder ``07_results/S8/p3b_<case>_<stamp>``; user decision 2026-10-26), then the 24 ``run_S9.py
    level`` cases in the 5.37.6 order (G1 10, J1 10, J2 / S1 4). Run with ``--parallel 4`` (4 SCM
    threads each = 16 P-core logical processors)."""
    sys.path.insert(0, str(HERE))
    try:
        import run_S9 as r9  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    rows = [{"case": cid, "est_s": est, "s8c": True,
             "argv": S8C + ["run", "--set", "rest", "--only", cid, "--tag", f"p3b_{cid}", "--approved",
                            "--workers", "p7"]}  # S8 'rest' set member; S8 sensors (ideal) unchanged
            for cid, est in r9.P3B_S8C_CASES.items()]
    rows += [{"case": c["case"], "est_s": c["est_s"], "argv": RUN + r9.p3b_level_argv(c)} for c in r9.p3b_cases()]
    return rows


S8C_FAILED_RC = 4
"""Return code recorded for an ``s8c`` row whose run_S8C process exited 0 but whose case failed
(run_S8C ``run`` prints the case outcome and returns 0 either way; its behaviour is unchanged)."""


def s8c_case_check(log_text: str, case_id: str, root: Path = ROOT) -> dict:
    """Outcome of one ``run_S8C.py run --only <case_id>`` from its log: the outcome line
    ``<case_id>: ok <wall>s`` (``run_batch``), the batch folder of the last ``batch wall ... -> <dir>``
    line and ``<dir>/<case_id>/result.json``. ``ok`` only when all three hold."""
    lines = log_text.splitlines()
    status = next((ln.split(":", 1)[1].split()[0] for ln in reversed(lines)
                   if ln.startswith(f"{case_id}:") and len(ln.split(":", 1)[1].split()) >= 1), None)
    batch_dir = next((ln.split("->", 1)[1].strip() for ln in reversed(lines)
                      if ln.startswith("batch wall") and "->" in ln), None)
    result = None
    if batch_dir:
        d = Path(batch_dir)
        result = (d if d.is_absolute() else root / d) / case_id / "result.json"
    out = {"case": case_id, "status": status, "batch_dir": batch_dir,
           "result_json": None if result is None else result.as_posix(),
           "result_exists": bool(result is not None and result.is_file())}
    reasons = []
    if status != "ok":
        reasons.append(f"case outcome {status!r} (expected 'ok')")
    if batch_dir is None:
        reasons.append("no 'batch wall ... -> <dir>' line")
    elif not out["result_exists"]:
        reasons.append("result.json missing")
    out.update(ok=not reasons, reason="; ".join(reasons) or None)
    return out


def _log(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


PLACEMENT_ENV = "OUTRIGGER_PLACEMENT"
"""Read by ``run_S9.place`` (``pcore`` / ``ecore``); set per case from its pool."""
POOLS = ("pcore", "ecore")
ORDERS = ("given", "lpt")


def schedule_cases(cases: list[dict], *, e_cases: list[str] | None = None, order: str = "given",
                   order_cases: list[str] | None = None, parallel_e: int = 0) -> dict[str, list[dict]]:
    """Split ``cases`` into the P and E pool queues (no effect on any judgement).

    ``e_cases``: case names sent to the E pool (``OUTRIGGER_PLACEMENT=ecore``); every other case
    goes to the P pool. ``order``: ``given`` (batch definition order) or ``lpt`` (longest
    ``est_s`` first, stable). ``order_cases``: explicit order; the listed cases come first in
    that order, the rest follow by ``order``. Raises ValueError on unknown names, an E case
    without E slots or an ``s8c`` row on the E pool (run_S8C places its own processes)."""
    names = [c["case"] for c in cases]
    e_set = set(e_cases or ())
    unknown = sorted((e_set | set(order_cases or ())) - set(names))
    if unknown:
        raise ValueError(f"unknown case names: {unknown}")
    if order not in ORDERS:
        raise ValueError(f"order must be one of {ORDERS}: {order!r}")
    if e_set and parallel_e < 1:
        raise ValueError(f"E-pool cases {sorted(e_set)} but --parallel-e {parallel_e}")
    bad = sorted(c["case"] for c in cases if c["case"] in e_set and (c.get("s8c") or c.get("fixed_pcore")))
    if bad:
        raise ValueError(f"s8c / fixed-P rows cannot go to the E pool (they pin their own process): {bad}")
    missing = sorted(f"{c['case']} -> {c['depends_on']}" for c in cases
                     if c.get("depends_on") and c["depends_on"] not in names)
    if missing:
        raise ValueError(f"rows depend on cases outside the run (add them to --only): {missing}")
    rest = list(cases) if order == "given" else sorted(cases, key=lambda c: -float(c["est_s"]))
    if order_cases:
        first = [next(c for c in cases if c["case"] == n) for n in order_cases]
        rest = first + [c for c in rest if c["case"] not in set(order_cases)]
    return {"pcore": [c for c in rest if c["case"] not in e_set], "ecore": [c for c in rest if c["case"] in e_set]}


def next_runnable(queue: list[dict], finished_ok: set[str]) -> int | None:
    """Index of the first queued row whose ``depends_on`` (RV5, 2026-10-30) has ended with rc 0; rows without it are
    runnable at once, so a queue without dependencies keeps its order (index 0)."""
    for k, c in enumerate(queue):
        if not c.get("depends_on") or c["depends_on"] in finished_ok:
            return k
    return None


def _case_env(pool: str) -> dict[str, str]:
    env = dict(os.environ)
    env[PLACEMENT_ENV] = pool
    return env


CODE_HASH_FILES = ("03_src/outrigger_sim/control/c2.py", "03_src/outrigger_sim/control/zero_calibration.py")
"""Controller files hashed at every case launch (``code_at_launch``; FINAL 2026-10-30)."""
ENTRY_META_KEYS = ("note", "priority", "controller", "source_run", "pair_case", "pair_run", "optional", "requires",
                   "harness_case", "family", "s8_group", "also_in", "planned_pool", "est_pool_s", "depends_on", "k",
                   "direction", "h9_result", "rep_bundle", "rep_source", "rep_variable", "r4_x11_check",
                   "expected_note", "rep_role", "source_expected_diffs", "criteria_id", "stored_wall_s",
                   "s8c_case_id", "v5_setting",
                   "d1_id", "d1_role", "d1_select", "d1_tag", "d1_slope", "d1_flag", "d1_source")
"""Row keys copied into the batch.json case entries (when present)."""


def launch_code_state(root: Path = ROOT) -> dict:
    """SHA-256 of :data:`CODE_HASH_FILES` and the commit / controller-tree status (``run_S9.git_state``) at a case
    launch: the provenance of rows whose runner does not record it (run_S8C / run_S6C), and a cross-check of
    run_S9 ``code_state`` (record only; errors are recorded, not raised)."""
    import hashlib  # noqa: PLC0415

    out: dict = {"files": {}}
    for rel in CODE_HASH_FILES:
        p = root / rel
        out["files"][rel] = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    sys.path.insert(0, str(HERE))
    try:
        import run_S9 as r9  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    try:
        out["git"] = r9.git_state(root)
    except Exception as e:  # noqa: BLE001 - record only
        out["git"] = {"error": f"{type(e).__name__}: {e}"}
    return out


def strip_controller_check(argv: list[str]) -> list[str]:
    """``argv`` without ``--expect-controller <name>`` (``run --no-controller-check``)."""
    out, skip = [], False
    for tok in argv:
        if skip:
            skip = False
            continue
        if tok == "--expect-controller":
            skip = True
            continue
        out.append(tok)
    return out


def parse_row_filter(items: list[str] | None) -> dict[str, set[str]]:
    """``--row-filter KEY=V1,V2`` (repeatable) -> {KEY: {V1, V2}}; a row passes when every KEY's value (``str``; a
    list value passes when any element matches) is in the set."""
    out: dict[str, set[str]] = {}
    for it in items or ():
        if "=" not in it:
            raise SystemExit(f"--row-filter {it!r}: expected KEY=V1[,V2...]")
        k, v = it.split("=", 1)
        out.setdefault(k.strip(), set()).update(x for x in v.split(",") if x)
    return out


def row_passes(row: dict, flt: dict[str, set[str]]) -> bool:
    for k, allowed in flt.items():
        v = row.get(k)
        vals = [str(x) for x in v] if isinstance(v, (list, tuple)) else [str(v)]
        if not set(vals) & allowed:
            return False
    return True


def read_only_file(path: str | None) -> list[str] | None:
    """``--only-file``: JSON list, JSON {"cases": [...]} or text (one name per line, '#' comments)."""
    if not path:
        return None
    text = Path(path).read_text("utf-8")
    try:
        doc = json.loads(text)
    except json.JSONDecodeError:
        return [ln.split("#", 1)[0].strip() for ln in text.splitlines() if ln.split("#", 1)[0].strip()]
    names = doc.get("cases") if isinstance(doc, dict) else doc
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        raise SystemExit(f"--only-file {path}: expected a list of case names or {{'cases': [...]}}")
    return names


def select_rows(rows: list[dict], only: list[str] | None = None, row_filter: dict[str, set[str]] | None = None
                ) -> list[dict]:
    """Rows of a batch kept by ``--only`` / ``--only-file`` (names; unknown names raise) and ``--row-filter``."""
    if only:
        unknown = sorted(set(only) - {c["case"] for c in rows})
        if unknown:
            raise ValueError(f"unknown case names: {unknown}")
    return [c for c in rows if (not only or c["case"] in only) and row_passes(c, row_filter or {})]


def row_finished(row: dict, folder: Path) -> bool:
    """Whether a row of an earlier launch into ``folder`` ended well (``--resume``): an ``s8c`` row by its log
    (:func:`s8c_case_check`), any other row by ``<folder>/<case>/result.json``, the last file run_S9 writes."""
    if row.get("s8c"):
        log = folder / f"{row['case']}.log"
        return log.is_file() and s8c_case_check(log.read_text("utf-8", errors="replace"),
                                                row.get("s8c_case_id", row["case"]))["ok"]
    return (folder / row["case"] / "result.json").is_file()


def run_batch(name: str, parallel: int = 2, only: list[str] | None = None, *, parallel_e: int = 0,
              e_cases: list[str] | None = None, order: str = "given",
              order_cases: list[str] | None = None, rv6_k: float | None = None, rv6_dir: str | None = None,
              row_filter: dict[str, set[str]] | None = None, controller_check: bool = True,
              resume: str | None = None) -> Path:
    """Run the batch ``name`` with ``parallel`` P-pool slots and ``parallel_e`` E-pool slots
    (:func:`schedule_cases`). Each case process gets ``OUTRIGGER_PLACEMENT`` of its pool. ``rv6_k``: X6-rb ratio of
    RV6; ``row_filter`` / ``only``: :func:`select_rows`; ``controller_check`` False drops ``--expect-controller``.
    ``resume``: an earlier batch folder; finished rows (:func:`row_finished`) are skipped, the others start from the
    beginning in the same folder (a case has no mid-run checkpoint) and ``batch.json`` is rewritten."""
    rv6 = {k: v for k, v in (("rv6_k", rv6_k), ("rv6_dir", rv6_dir)) if v is not None}
    cases = select_rows((batches(**rv6) if rv6 else batches())[name], only, row_filter)
    if not cases:
        raise SystemExit(f"batch {name}: no rows left after --only / --row-filter")
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = Path(resume) if resume else ROOT / "07_results" / "S9" / f"batch_{name}_{stamp}"
    if resume and not folder.is_dir():
        raise SystemExit(f"--resume {resume}: no such batch folder")
    finished = [c for c in cases if resume and row_finished(c, folder)]
    former = {}
    if finished and (folder / "batch.json").is_file():
        former = {e["case"]: e for e in json.loads((folder / "batch.json").read_text("utf-8")).get("cases", [])}
    done_names = {c["case"] for c in finished}
    cases = [c for c in cases if c["case"] not in done_names]
    e_cases = None if e_cases is None else [n for n in e_cases if n not in done_names]
    order_cases = None if order_cases is None else [n for n in order_cases if n not in done_names]
    queues = schedule_cases(cases, e_cases=e_cases, order=order, order_cases=order_cases, parallel_e=parallel_e)
    slots = {"pcore": int(parallel), "ecore": int(parallel_e)}
    folder.mkdir(parents=True, exist_ok=True)
    progress = folder / "progress.log"
    _log(progress, f"# batch {name} {len(cases)} cases, parallel P {slots['pcore']} / E {slots['ecore']}, order {order}"
                   f"{' (explicit list first)' if order_cases else ''}, started "
                   f"{_dt.datetime.now().isoformat(timespec='seconds')}")
    for c in finished:
        _log(progress, f"RESUME_SKIP {c['case']} (finished in an earlier launch)")
    for pool in POOLS:
        if queues[pool]:
            _log(progress, f"# queue {pool}: {' '.join(c['case'] for c in queues[pool])}")
    running: list[tuple[dict, subprocess.Popen, float, object, str]] = []
    done: list[dict] = [former.get(c["case"]) or {"case": c["case"], "argv": c["argv"], "rc": 0, "wall_s": 0.0,
                                                  "est_s": c["est_s"], "pool": "earlier_launch"} for c in finished]
    code_at_launch: dict[str, dict | None] = {}
    failed = False
    finished_ok: set[str] = set()
    while any(queues.values()) or running:
        for pool in POOLS:
            while queues[pool] and sum(1 for r in running if r[4] == pool) < slots[pool] and not failed:
                k = next_runnable(queues[pool], finished_ok)
                if k is None:  # RV5: every queued row waits for its base row
                    break
                c = queues[pool].pop(k)
                if c.get("s8c") or c.get("s6c"):  # run_S8C / run_S6C write their own batch folder (case log)
                    argv = list(c["argv"])
                elif c.get("m3"):  # m3_run.py <key> <variant> <out_root> -> <out_root>/<key>__<variant>/
                    argv = list(c["argv"]) + [str(folder)]
                else:
                    argv = list(c["argv"]) + (["--out", str(folder / "E")] if c.get("eq_out")
                                              else ["--case", c["case"], "--out-root", str(folder)])
                if not controller_check:
                    argv = strip_controller_check(argv)
                code_at_launch[c["case"]] = launch_code_state() if c.get("controller") or c.get("group") == "FINAL-R" \
                    else None
                logf = (folder / f"{c['case']}.log").open("w", encoding="utf-8")
                p = subprocess.Popen(argv, cwd=str(ROOT), stdout=logf, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, env=_case_env(pool))
                _log(progress, f"START {c['case']} {_dt.datetime.now().isoformat(timespec='seconds')} pid={p.pid} "
                               f"est_s={c['est_s']} pool={pool}")
                running.append((c, p, time.perf_counter(), logf, pool))
        time.sleep(2.0)
        for item in list(running):
            c, p, t0, logf, pool = item
            rc = p.poll()
            if rc is None:
                continue
            logf.close()
            wall = time.perf_counter() - t0
            running.remove(item)
            entry = {"case": c["case"], "argv": c["argv"], "rc": rc, "wall_s": wall, "est_s": c["est_s"], "pool": pool}
            entry.update({k: c[k] for k in ENTRY_META_KEYS if c.get(k) is not None})  # note: G6P rows (2026-10-28)
            if code_at_launch.get(c["case"]) is not None:  # RV6 / FINAL (2026-10-30)
                entry["code_at_launch"] = code_at_launch[c["case"]]
                entry["controller_check"] = bool(controller_check)
            note = ""
            if c.get("s8c") and rc == 0:  # run_S8C returns 0 even when its case failed: read the outcome
                chk = s8c_case_check((folder / f"{c['case']}.log").read_text("utf-8", errors="replace"),
                                     c.get("s8c_case_id", c["case"]))  # v5 stage 3: batch name != run_S8C id
                entry["s8c_check"] = chk
                if not chk["ok"]:
                    rc = entry["rc"] = S8C_FAILED_RC
                    entry["process_rc"] = 0
                    note = f" s8c_check=FAILED ({chk['reason']})"
                else:
                    note = f" s8c_check=ok {chk['batch_dir']}"
            done.append(entry)
            if rc == 0:
                finished_ok.add(c["case"])
            _log(progress, f"END {c['case']} {_dt.datetime.now().isoformat(timespec='seconds')} rc={rc} "
                           f"wall_s={wall:.0f}{note}")
            if rc != 0:
                failed = True
        if failed and any(queues.values()):
            for pool in POOLS:
                for c in queues[pool]:
                    _log(progress, f"SKIP {c['case']} (earlier failure)")
                    done.append({"case": c["case"], "argv": c["argv"], "rc": None, "wall_s": 0.0, "est_s": c["est_s"],
                                 "pool": pool, **{k: c[k] for k in ENTRY_META_KEYS if c.get(k) is not None}})
                queues[pool] = []
    status = {"batch": name, "folder": folder.as_posix(), "parallel": parallel, "parallel_e": parallel_e,
              "order": order, "order_cases": order_cases, "e_cases": sorted(e_cases or ()),
              **({"rv6_k": rv6_k, "rv6_dir": rv6_dir} if name == "RV6" else {}),
              **({"row_filter": {k: sorted(v) for k, v in row_filter.items()}} if row_filter else {}),
              **({} if controller_check else {"controller_check": False}),
              "cases": done, "failed": failed,
              "wall_serial_s": sum(d["wall_s"] for d in done), "est_serial_s": sum(d["est_s"] for d in done)}
    (folder / "batch.json").write_text(json.dumps(status, indent=1), "utf-8")
    _log(progress, f"# batch {name} finished {_dt.datetime.now().isoformat(timespec='seconds')} failed={failed}")
    print(folder)
    return folder


def describe_rows(name: str, rows: list[dict]) -> list[str]:
    """Lines of ``list <batch>``: one per row (case, est_s, est_pool_s P / E, priority, depends_on, source, controller)
    and the serial sums."""
    out = [f"{name} {len(rows)} rows"]
    for c in rows:
        ep = c.get("est_pool_s") or {}
        extra = [f"prio={c['priority']}" if c.get("priority") is not None else "",
                 f"after={c['depends_on']}" if c.get("depends_on") else "",
                 "optional" if c.get("optional") else "",
                 f"rep={c['rep_variable']}" if c.get("rep_variable") else "",
                 "r4_x11" if c.get("r4_x11_check") else "",
                 f"family={c['family']}" if c.get("family") else "",
                 f"ctrl={c['controller']}" if c.get("controller") else "",
                 f"src={c['source_run']}" if c.get("source_run") else ""]
        pe = f" P={ep['pcore']:.0f} E={ep['ecore']:.0f}" if ep else ""
        out.append(f"  {c['case']} est_s={float(c['est_s']):.0f}{pe} " + " ".join(x for x in extra if x))
    p = sum(float((c.get("est_pool_s") or {}).get("pcore", c["est_s"])) for c in rows)
    out.append(f"  serial sum P {p:.0f} s ({p / 3600:.1f} h)")
    return out


S6C_PLAN_KEYS = ("case_id", "config", "snapshot", "duration_s", "fine_dt", "conditional")


def s6c_source_check(c: dict, root: Path = ROOT) -> dict:
    """An ``s6c`` row against its former run_S6C batch (``<source batch>/batch_meta.json``): same ``--set`` as the
    batch ``case_set``, the case in its ``cases``, and the ``run_S6C.plan`` row of the case (:data:`S6C_PLAN_KEYS`) =
    the former plan row (run_S6C keeps no per-case CLI args). ``status`` ok / differs / no_source."""
    src = root / c["source_run"]
    meta_p = src.parent / "batch_meta.json"
    if not meta_p.is_file():
        return {"source": src.as_posix(), "status": "no_source", "diffs": []}
    meta = json.loads(meta_p.read_text("utf-8"))
    argv = c["argv"]
    set_name = argv[argv.index("--set") + 1]
    sys.path.insert(0, str(HERE))
    try:
        import run_S6C as s6  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    now = next(r for r in s6.plan([c["case"]], case_set=set_name)["cases"] if r["case_id"] == c["case"])
    old = next((r for r in (meta.get("plan") or {}).get("cases", []) if r.get("case_id") == c["case"]), None)
    diffs = []
    if meta.get("case_set") != set_name:
        diffs.append({"key": "case_set", "former": meta.get("case_set"), "row": set_name})
    if c["case"] not in (meta.get("cases") or []):
        diffs.append({"key": "cases", "former": meta.get("cases"), "row": c["case"]})
    if old is None:
        diffs.append({"key": "plan", "former": "<absent>", "row": c["case"]})
    else:
        diffs += [{"key": k, "former": old.get(k), "row": now.get(k)} for k in S6C_PLAN_KEYS if old.get(k) != now.get(k)]
    if "--allow-p28-cases" not in argv and meta.get("case_set") in ("g8c76_p28", "g8c76_p28acc"):
        diffs.append({"key": "--allow-p28-cases", "former": True, "row": False})
    return {"source": src.as_posix(), "status": "differs" if diffs else "ok", "diffs": diffs}


def check_sources(name: str, rows: list[dict]) -> dict:
    """``check-sources <batch>``: run_S9 :func:`source_args_check` of every level row with a ``source_run``
    (``07_results/S9/<source_run>``); rows without it are ``no_source_defined``. ``ok`` = no ``differs``."""
    sys.path.insert(0, str(HERE))
    try:
        import run_S9 as r9  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    res = []
    for c in rows:
        if c.get("s6c") and c.get("source_run"):
            res.append({"case": c["case"], **s6c_source_check(c)})
            continue
        if c.get("s8c") and c.get("v5_setting"):
            res.append({"case": c["case"], **v5_rigid_source_check(c)})
            continue
        if c.get("s8c") or not c.get("source_run"):
            res.append({"case": c["case"], "status": "no_source_defined" if not c.get("source_run") else "not_level",
                        "source": c.get("source_run")})
            continue
        chk = r9.source_args_check(c["argv"][len(RUN):], ROOT / "07_results" / "S9" / c["source_run"])
        chk = expected_diff_check(chk, c.get("source_expected_diffs"))
        res.append({"case": c["case"], **chk})
    ok = not any(r["status"] == "differs" for r in res)
    if name == V5_STAGE3_BATCH:  # stage3_impl_spec.md 4: 34 rows, no duplicate name
        names = [c["case"] for c in rows]
        if len(rows) != 34 or len(set(names)) != len(names):
            res.append({"case": "<batch>", "status": "differs", "source": None,
                        "diffs": [{"key": "rows", "former": 34, "row": len(rows)},
                                  {"key": "unique_names", "former": len(rows), "row": len(set(names))}]})
            ok = False
    return {"batch": name, "rows": res, "ok": ok}


def v5_rigid_source_check(c: dict, root: Path = ROOT) -> dict:
    """stage3_impl_spec.md 4 for a rigid v5 row: (a) the id is in the ``--set`` of its argv, (b) the v5 / flow
    arguments after ``--workers p7`` parse (run_S8C parser parts: ``add_flow_limit_arguments`` +
    ``add_hydraulic_arguments(with_valve_tau=False)``, then ``flow_setting_from_args`` / ``hydraulic_options_from_args``)
    to exactly :func:`v5_rigid_setting_args` of the row setting, (c) a V0 row has none of them. ``ok`` / ``differs``;
    ``no_source`` when no stored run to compare is defined or present (not a failure)."""
    import argparse as _ap  # noqa: PLC0415

    src = str(root / "03_src")
    added = src not in sys.path
    if added:
        sys.path.insert(0, src)
    sys.path.insert(0, str(HERE))
    try:
        import run_S8C as s8  # noqa: PLC0415
        from outrigger_sim.hydraulics.flow_limit_run import (  # noqa: PLC0415
            add_flow_limit_arguments,
            flow_setting_from_args,
        )
        from outrigger_sim.hydraulics.v5_options import (  # noqa: PLC0415
            add_hydraulic_arguments,
            hydraulic_options_from_args,
        )
    finally:
        sys.path.remove(str(HERE))
        if added:
            sys.path.remove(src)
    argv = c["argv"]
    set_name = argv[argv.index("--set") + 1]
    case_id = argv[argv.index("--only") + 1]
    diffs = []
    if case_id != c.get("s8c_case_id", c["case"]):
        diffs.append({"key": "--only", "former": c.get("s8c_case_id"), "row": case_id})
    if case_id not in {k.case_id for k in s8.case_set(set_name)}:
        diffs.append({"key": "case_set", "former": set_name, "row": case_id})
    tail = argv[argv.index("--workers") + 2:]
    parser = _ap.ArgumentParser(add_help=False)
    add_flow_limit_arguments(parser)
    add_hydraulic_arguments(parser, with_valve_tau=False)
    try:
        parsed = parser.parse_args(tail)
        flow_setting_from_args(parsed)
        hydraulic_options_from_args(parsed)
        got = vars(parsed)
    except SystemExit as e:
        got = {"<parse error>": str(e)}
    want = v5_rigid_setting_args(c["v5_setting"])
    for key in sorted(set(got) | set(want)):
        if got.get(key) != want.get(key):
            diffs.append({"key": key, "former": want.get(key), "row": got.get(key)})
    status = "differs" if diffs else "ok"
    source = c.get("source_run")
    if status == "ok" and (not source or not (root / source).exists()):
        status = "no_source"
    return {"source": source, "status": status, "diffs": diffs, "v5_setting": c["v5_setting"]}


def expected_diff_check(chk: dict, expected: dict | None) -> dict:
    """A row with ``source_expected_diffs`` {arg: row value} (FINAL-REP-X, 2026-10-31): ``ok_expected_diff`` when the
    argument differences against the former run are exactly those keys with those row values, else ``differs`` (an
    expected difference that is absent also differs). Rows without it are returned unchanged."""
    if not expected or chk["status"] == "no_source":
        return chk
    got = {d["key"]: d["row"] for d in chk["diffs"]}
    ok = set(got) == set(expected) and all(got[k] == v for k, v in expected.items())
    return {**chk, "status": "ok_expected_diff" if ok else "differs", "expected_diffs": dict(expected)}


def main(argv) -> None:
    a = build_parser().parse_args(argv)
    if a.action == "list":
        b = batches(rv6_k=a.rv6_k, rv6_dir=a.rv6_dir)
        if a.batch:
            print("\n".join(describe_rows(a.batch, select_rows(b[a.batch], None, parse_row_filter(a.row_filter)))))
        else:
            for k, v in b.items():
                print(k, len(v), [c["case"] for c in v])
    elif a.action == "check-sources":
        doc = check_sources(a.batch, batches(rv6_k=a.rv6_k, rv6_dir=a.rv6_dir)[a.batch])
        for r in doc["rows"]:
            print(r["case"], r["status"], r.get("source") or "", r.get("diffs") or "")
        print("ok" if doc["ok"] else "DIFFERS")
        if not doc["ok"]:
            raise SystemExit(1)
    else:
        env_override_guard(a.allow_env_override, a.batch)
        only = (a.only or []) + (read_only_file(a.only_file) or [])
        run_batch(a.batch, only=only or None, rv6_k=a.rv6_k, rv6_dir=a.rv6_dir,
                  row_filter=parse_row_filter(a.row_filter), controller_check=not a.no_controller_check,
                  resume=a.resume, **schedule_args(a, argv))


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="action", required=True)
    names = sorted(batches())
    ls = sub.add_parser("list", help="all batches (names), or one batch's rows with estimates")
    ls.add_argument("batch", nargs="?", choices=names)
    cs = sub.add_parser("check-sources", help="RV6 / FINAL: do the level rows reproduce their former run args?")
    cs.add_argument("batch", choices=names)
    ls.add_argument("--row-filter", action="append", default=None, metavar="KEY=V1[,V2]")
    r = sub.add_parser("run")
    r.add_argument("batch", choices=names)
    for p in (ls, cs, r):
        p.add_argument("--rv6-k", type=float, default=None,
                       help="RV6: X6-rb floor roll = k_b x 4.4 deg, sign by --rv6-dir (default 0.65; spec 430.3.1)")
        p.add_argument("--rv6-dir", choices=("roll_neg", "roll_pos"), default=None,
                       help="RV6: X6-rb direction (default roll_neg; the other direction is the optional row)")
    r.add_argument("--only-file", default=None, help="case names (JSON list / {'cases': [...]} / one per line), added "
                                                     "to --only (FINAL-R: the rows whose harness pair acts)")
    r.add_argument("--row-filter", action="append", default=None, metavar="KEY=V1[,V2]",
                   help="keep rows whose KEY is one of the values, e.g. family=p1r,g1 (FINAL-R) or s8_group=K0,K8; a "
                        "missing key reads 'None' (repeatable)")
    r.add_argument("--no-controller-check", action="store_true",
                   help="RV6 / FINAL: drop run_S9 --expect-controller (run whatever preset is installed; recorded)")
    r.add_argument("--parallel", "--parallel-p", dest="parallel", type=int, default=2,
                   help="P-pool slots (OUTRIGGER_PLACEMENT=pcore); --parallel keeps its former meaning")
    r.add_argument("--parallel-e", type=int, default=0, help="E-pool slots (OUTRIGGER_PLACEMENT=ecore)")
    r.add_argument("--e-cases", nargs="*", default=None, help="cases sent to the E pool (others: P pool)")
    r.add_argument("--order", choices=ORDERS, default="given",
                   help="queue order: batch definition order or LPT (longest est_s first)")
    r.add_argument("--order-cases", nargs="*", default=None, help="explicit order (listed cases first)")
    r.add_argument("--schedule", default=None,
                   help='JSON file {"e_cases": [...], "order": "given"|"lpt", "order_cases": [...], '
                        '"parallel_p": N, "parallel_e": M} (e.g. the compute-scheduler-expert LPT plan); '
                        "command-line values given explicitly win")
    r.add_argument("--only", nargs="*")
    r.add_argument("--resume", default=None, metavar="BATCH_FOLDER",
                   help="continue in this earlier batch folder: finished rows are skipped, the others start again")
    r.add_argument("--allow-env-override", action="store_true",
                   help="start even with OUTRIGGER_L1_FALLBACK_RATIO_SOURCE set (B(iii) comparison batch; "
                        "the L1 cases of the batch, e.g. P3-10 m3_run, take the override)")
    return ap


def env_override_guard(allow: bool, batch: str) -> str | None:
    """B(iii) (control 2026-10-26): refuse a batch while ``OUTRIGGER_L1_FALLBACK_RATIO_SOURCE``
    is set (the child processes inherit it) unless ``--allow-env-override``."""
    src = str(ROOT / "03_src")
    added = src not in sys.path
    if added:
        sys.path.insert(0, src)
    try:
        from outrigger_sim.chrono.fallback_ratio import refuse_env_override
    finally:
        if added:
            sys.path.remove(src)
    return refuse_env_override(allow, f"s9_batch run {batch}")


def split_names(tokens: list[str] | None) -> list[str] | None:
    """Case names of ``--e-cases`` / ``--order-cases``: space- or comma-separated (empty parts dropped);
    ``None`` stays ``None``."""
    if tokens is None:
        return None
    return [n for t in tokens for n in str(t).split(",") if n]


def schedule_args(a: argparse.Namespace, argv: list[str]) -> dict:
    """``run_batch`` keywords from the CLI and an optional ``--schedule`` JSON file; an option
    written on the command line wins over the file."""
    given = {tok.split("=", 1)[0] for tok in argv if tok.startswith("--")}
    out = {"parallel": a.parallel, "parallel_e": a.parallel_e, "e_cases": split_names(a.e_cases), "order": a.order,
           "order_cases": split_names(a.order_cases)}
    if a.schedule:
        doc = json.loads(Path(a.schedule).read_text("utf-8"))
        unknown = sorted(set(doc) - {"e_cases", "order", "order_cases", "parallel_p", "parallel_e", "note", "source"})
        if unknown:
            raise SystemExit(f"--schedule {a.schedule}: unknown keys {unknown}")
        file_map = {"e_cases": ("e_cases", "--e-cases"), "order": ("order", "--order"),
                    "order_cases": ("order_cases", "--order-cases"), "parallel_p": ("parallel", "--parallel-p"),
                    "parallel_e": ("parallel_e", "--parallel-e")}
        for key, (dest, flag) in file_map.items():
            if key in doc and flag not in given and not (dest == "parallel" and "--parallel" in given):
                out[dest] = doc[key]
    return out


if __name__ == "__main__":
    main(sys.argv[1:])
