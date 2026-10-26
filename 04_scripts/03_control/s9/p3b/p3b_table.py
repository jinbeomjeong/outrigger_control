"""S9 P3b compact control tables from ``p3b_collect.json`` (spec rev. 60, 306 / 315).

Prints five plain-text tables per case: READY timing and P3-1 .. P3-4; P3-5 rut clearance
and stroke; P3-7 .. P3-9, W61 and warnings; track utilisation and end attitude; the phase
sequence relative to the loop start.

Input: ``06_analysis/02_control/s9/p3b/p3b_collect.json`` (from ``p3b_collect.py``).
Output: standard output only.

Usage (dynamics-dev):
  conda run -n dynamics-dev python -I 04_scripts/03_control/s9/p3b/p3b_table.py [<collect_json>]
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_COLLECT = ROOT / "06_analysis" / "02_control" / "s9" / "p3b" / "p3b_collect.json"
LEG_NAMES = ["FL", "FR", "RL", "RR"]


def f(x, n=2, s=1.0):
    """Format x * s with n decimals, '-' for None."""
    return "-" if x is None else f"{x * s:.{n}f}"


def _print_attitude_table(d):
    print("case | ready_loop | ready_touch | nDONE nPROBE | P3-1 zero/win/recon | dep | LOC-dep | "
          "soilmode | P3-3 min/Fmin leg | pre-lift min kN | P3-4 max deg | win len | "
          "resid<=.04 | db.03 | post-lift max")
    for k, v in d.items():
        p1, p2, p4 = v["P3-1"], v["P3-2"], v["P3-4"]
        pre_lift_min_kN = min(leg["F_min_N"] for leg in v["pre_liftoff"]["legs"]) / 1e3
        print(f"{k[4:]} | {f(v['P3-6']['t_ready_after_loop_start_s'],1)} | "
              f"{f(v['ready_from_touch_s'],1)} | "
              f"{v['n_done']} {v['n_probe']} | "
              f"{p1['crawler_zero']}/{p1['window_complete']}/{p1['recontact_count']} | "
              f"{f(v['departure']['t_departure_s'],2)} | {f(p2['loc_minus_departure_s'],2)} | "
              f"{p2['soil_mode_used']} | "
              f"{v['P3-3_min_ratio']:.2f} {LEG_NAMES[v['P3-3_min_leg']]} | "
              f"{pre_lift_min_kN:.2f} | "
              f"{p4['p34_absmax_overall_deg']:.4f} | {p4['p34_window_length_s']:.1f} | "
              f"{p4['budget_residual_le_0p04']} | "
              f"{p4['within_deadband_0p03_record']} | {max(p4['post_liftoff_absmax_deg']):.3f}")


def _print_clearance_table(d):
    print("case | P3-5 within | rut min after dep (summ) | rut min rows dep | dep+1s | "
          "after 1st READY | after last READY | at LOC | end | s_motor max | probe sink max mm")
    for k, v in d.items():
        p5 = v["P3-5"]
        ps = max((max(x["d_sinkage_m"]) for x in p5["probe_sinkage"]), default=None)
        print(f"{k[4:]} | {p5['within']} | {f(p5['rut_min_after_departure_m'],1,1e3)} | "
              f"{f(p5['rut_min_dep_rows'][0],1,1e3)}@{f(p5['rut_min_dep_rows'][1],1)} | "
              f"{f(p5['rut_min_dep_plus1s'][0],1,1e3)} | "
              f"{f(p5['rut_min_after_first_ready'][0],1,1e3)} | "
              f"{f(p5['rut_min_after_last_ready'][0],1,1e3)} | "
              f"{f(p5['rut_at_loc_m'],1,1e3)} | {f(p5['rut_end_m'],1,1e3)} | "
              f"{p5['s_motor_max_m']*1e3:.1f} | {f(ps,1,1e3)}")


def _print_plateau_table(d):
    print("case | P3-7 nwin nloaded | rise min loaded read kN | true kN | rise at LOC | W_ratio | "
          "c(P) mm | bias mm | P3-8 | P3-9 | W61 | reapp | warnings")
    for k, v in d.items():
        p7 = v["P3-7"]
        s = v["soil"]
        w61 = len(v["W61"].get("warnings", [])) if isinstance(v["W61"], dict) else v["W61"]
        print(f"{k[4:]} | {p7['n_windows']} {p7['n_loaded_windows']} | "
              f"{f(p7['rise_min_loaded_read_N'],2,1e-3)} | "
              f"{f(p7['rise_min_loaded_true_N'],2,1e-3)} | {f(p7['rise_at_loc_N'],2,1e-3)} | "
              f"{f(s['W_ratio'],3)} | "
              f"{f(s['clearance_at_P_m'],1,1e3)} | "
              f"{[round(b*1e3,1) for b in s['bias_corner_m']]} | "
              f"{v['P3-8']} | "
              f"{v['P3-9']['n_windows']}/{v['P3-9']['flag']} | {w61} | "
              f"{v['reapproach_limit']['fired']} | {[w['name'] for w in v['warnings']]}")


def _print_end_state_table(d):
    print("track util max, end mean roll/pitch, end-settle, DONE shift")
    for k, v in d.items():
        p4 = v["P3-4"]
        print(k[4:], [round(x, 4) for x in v["track_utilisation_max"]],
              [round(x, 4) for x in p4["end_mean_roll_pitch_deg"]],
              p4["done"].get("shift_5s_end_minus_done_deg"), p4["creep_stop_basis"],
              f(p4["t_creep_stop_final_two_sided_s"], 1), f(p4["t_ready_last_entry_s"], 1))


def _print_phase_sequences(d):
    for k, v in d.items():
        print(k[4:], [(p['t_s'] - v['t_loop_start_s']).__round__(1) for p in v['phases']],
              [p['phase'][:2] for p in v['phases']])


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("collect_json", nargs="?", type=Path, default=DEFAULT_COLLECT)
    return parser.parse_args()


def main():
    d = json.loads(_parse_args().collect_json.read_text(encoding="utf-8"))
    _print_attitude_table(d)
    print()
    _print_clearance_table(d)
    print()
    _print_plateau_table(d)
    print()
    _print_end_state_table(d)
    print()
    _print_phase_sequences(d)


if __name__ == "__main__":
    main()
