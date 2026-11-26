"""d09: provenance of the D-1..D-3 outputs (column definitions, run identity, key numbers).

Writes ``provenance.json`` in this folder: inputs (worktree commit, d00 scratch folder), the
``columns`` table of every metric CSV (definition, code line, unit, window, sign), and the
headline numbers read back from the d01 / d05 / d06 / d08 outputs.

Usage: conda run -n dynamics-dev python -I -B d09_provenance.py <d00 scratch dir>
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed7-impl")

COLUMNS = {
    "d05_d1_k1_decomposition.csv": {
        "f0_before_kN": ("seal force f of the probed leg one read before its first extend command "
                         "(plant ``f``; + = holds against retraction, - = against extension)",
                         "d05_d1_k1_decomposition.py:105", "kN", "1 read", "plant sign"),
        "band_to_cross_kN": ("F_s + f0: seal force change before the piston can slide in the "
                             "extend direction", "d05:111", "kN", "-", "-"),
        "f_mid_kN": ("seal force at the controller's K1 mid read (|f| < F_s = stuck)", "d05:112",
                     "kN", "1 read", "plant sign"),
        "x_moved_by_mid_mm": ("plant piston x at the mid read minus x one read before the leg's first "
                              "command (FL round 1: the probe-phase start, includes the approach)",
                              "d05:114", "mm", "-", "+ = extension"),
        "dF_kN": ("controller force reading change, extended read minus mid read (cue log)",
                  "d05:95", "kN", "mid -> ext", "+ = more load"),
        "dx_mm": ("piston (rod_stroke) reading change mid -> ext = plant x (d04: read_piston == x)",
                  "d05:96", "mm", "mid -> ext", "+ = extension"),
        "dseal_kN": ("seal force change mid -> ext (plant f)", "d05:98", "kN", "mid -> ext",
                     "plant sign"),
        "K1_MN_m": ("controller K1 = dF / dx (ground_contact._stiffness_cue SECOND_HALF)",
                    "ground_contact.py:605-610 (ed7-impl)", "MN/m", "mid -> ext", "-"),
        "Kpad_MN_m": ("pad-load slope (dF + dseal) / dx; F_cyl = F_el - W_r - f so this is dF_el/dx",
                      "d05:103", "MN/m", "mid -> ext", "-"),
        "Kband_MN_m": ("-dseal / dx; K1 = Kpad + Kband (seal breakaway inside the window)",
                       "d05:118", "MN/m", "mid -> ext", "-"),
        "Km_MN_m": ("oil-coordinate slope dF / ds_ref (plant s_ref = motor stroke)", "d05:104",
                    "MN/m", "mid -> ext", "-"),
        "K1_from_Km_MN_m": ("1 / (1/Km - 1/k_o), check of the series identity", "d05:120", "MN/m",
                            "-", "-"),
        "amplification_dK1_dKm": ("(dK1/K1) / (dKm/Km) = 1 / (1 - Km/k_o)", "d05:121", "-", "-", "-"),
        "ratio_K1": ("K1 / S_ii,nom (the controller's per-leg ratio; round median = raw ratio of "
                     "c2.py:9891-9908)", "d05:122", "-", "-", "-"),
        "ratio_Kpad": ("Kpad / S_ii,nom (window artefact removed)", "d05:122", "-", "-", "-"),
    },
    "d06_d2_s7_relevel_summary.csv": {
        "relevel_len_s": ("length of the LEVEL segment right after PROBE 1", "d06_d2_s7_relevel.py:73",
                          "s", "-", "-"),
        "probe_net_<leg>_mm": ("motor stroke after PROBE 1 minus before it", "d06:76", "mm", "PROBE 1",
                               "+ = extension"),
        "probe_dsp_<leg>_mm": ("soil plastic sinkage sp added during PROBE 1 (plant soil.sp)", "d06:77",
                               "mm", "PROBE 1", "+ = deeper"),
        "roll0_mrad / pitch0_mrad": ("controller filtered roll / pitch at the re-level start",
                                     "d06:80", "mrad", "1 read", "roll x, pitch y (pitch + = nose down)"),
        "subhold_leg_periods": ("leg-periods with 0 < |u| <= u_hold (0.209 mm/s)", "d06:86", "count",
                                "re-level", "-"),
        "sign_changes": ("command sign changes per leg, summed", "d06:89", "count", "re-level", "-"),
        "ib_on_leg_periods": ("A(i)-b floor periods (T4h lsb_ib_on)", "d06:95", "count", "re-level", "-"),
        "D_start_kN / D_end_kN": ("twist load D = nu^T F (T4h lsb_ib_twist_load_N)", "d06:96",
                                  "kN", "first / last read", "nu = (+FL, -FR, -RL, +RR) unit"),
        "t_first_on_target_after_start_s": ("first read with completion is_on_target", "d06:100", "s",
                                            "re-level", "-"),
    },
    "d07_d2_gate_kick.csv": {
        "in_mm_s / out_mm_s": ("lock-start component input / output command (T4h lsb_input/output)",
                               "d07_d2_gate_kick.py:43", "mm/s", "1 read", "+ = extend"),
        "a1_floor_mm_s": ("A(i) floor (T4h lsb_a1_floor_m_s), ramps by a1_step 0.2 mm/s per period",
                          "d07:47", "mm/s", "1 read", "-"),
        "plant_fill_x_mm": ("P1 line-fill state of the plant gate (line_fill_gate.x)", "d07:55", "mm",
                            "1 read", "-"),
    },
    "d08_d3_tail_twist_windows.csv": {
        "dD_kN_per_10s": ("D(last) - D(first) in the 10 s window", "d08_d3_tail_twist.py:119", "kN",
                          "10 s", "nu sign as d06"),
        "mean_nu_vx_mm_s / mean_nu_vs_mm_s": ("mean twist component of the executed piston / oil-volume "
                                              "rate (plant dx/dt, ds_ref/dt)", "d08:120-121", "mm/s",
                                              "10 s", "-"),
        "mean_nu_u_mm_s": ("mean twist component of the command", "d08:122", "mm/s", "10 s", "-"),
        "mean_nu_missing_mm_s": ("mean twist component of the commands on locked legs (not executed)",
                                 "d08:123", "mm/s", "10 s", "-"),
        "k_tw_eff_MN_m": ("mean dD/dt over mean nu^T v_x (piston-coordinate twist stiffness; ~k_s when "
                          "the oil columns carry the twist)", "d08:124", "MN/m", "10 s", "-"),
        "held_leg_periods": ("periods a leg is locked with a nonzero command", "d08:126", "count",
                             "10 s", "-"),
    },
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    scratch = Path(sys.argv[1])
    head = subprocess.run(["git", "-C", str(WT), "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(WT), "status", "--porcelain"], capture_output=True,
                           text=True).stdout.strip()
    rp = json.loads((OUT / "d01_repro_check.json").read_text(encoding="utf-8"))
    d05 = json.loads((OUT / "d05_d1_k1_decomposition.json").read_text(encoding="utf-8"))
    d06 = json.loads((OUT / "d06_d2_s7_relevel.json").read_text(encoding="utf-8"))
    d08 = json.loads((OUT / "d08_d3_tail_twist.json").read_text(encoding="utf-8"))
    tl = json.loads((OUT / "d02_timelines.json").read_text(encoding="utf-8"))
    prov = {
        "inputs": {"worktree": str(WT), "worktree_head": head, "worktree_clean": dirty == "",
                   "d00_scratch": str(scratch),
                   "runs_jsonl_sha256": sha(scratch / "runs.jsonl"),
                   "env": "conda dynamics-dev (python -I -B), NUMBA_CACHE_DIR in scratch"},
        "repro": [{"setting": r["setting"], "job": r["job"], "same_commands": r.get("same_commands"),
                   "stored_setting": r.get("stored_setting"),
                   "events": r["rerun"]["events"]} for r in rp],
        "t_first_ready_s": {k: v["t_first_ready_s"] for k, v in tl.items()},
        "k1_round_medians": d05["round_medians"],
        "s7_relevel": d06["summary"],
        "tail_segments": d08["segments"],
        "columns": COLUMNS,
        "sign_conventions": {"legs": "FL FR RL RR (index 0..3)", "stroke": "+ = extension",
                             "seal_f": "plant f: F_cyl = F_el - W_r - f; + holds against retraction",
                             "D": "nu^T F, nu = C2Geometry.twist_vector = (0.4761, -0.4761, -0.5228, "
                                  "0.5228)", "units": "SI in the plant; tables kN, mm, mm/s, MN/m, mrad"},
    }
    (OUT / "provenance.json").write_text(json.dumps(prov, indent=1), encoding="utf-8")
    print("worktree", head, "clean", dirty == "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
