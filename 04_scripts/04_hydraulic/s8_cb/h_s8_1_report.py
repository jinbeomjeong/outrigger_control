"""H-S8-1: print compact tables from h_s8_1_cb_ranges.json (read only).

Usage: python -I h_s8_1_report.py <h_s8_1_cb_ranges.json>
"""
import json
import sys
from pathlib import Path

r = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
A = r["A"]
print("== A extend upper (p_r slide / stick-worst / envelope) [bar g]")
for row in A["extend_upper"]:
    print(f"{row['side']:5s} Fs{row['Fs_level_kN']:g} {row['load']:7s} F {row['F_kN']:7.2f} "
          f"slide {row['p_r_slide_bar']:7.2f} (p_h {row['p_h_slide_bar']:6.2f}) "
          f"stick {row['p_r_stick_worst_bar']:7.2f} env {row['p_r_envelope_bar']:7.2f}")
print("== A lock p_r0 [bar g]")
for row in A["lock_p_r0"]:
    print(f"{row['side']:5s} Fs{row['Fs_level_kN']:g} {row['load']:7s} ext {row['after_extend_nominal_bar']:7.2f} "
          f"stick {row['after_extend_stick_range_bar'][0]:6.2f}..{row['after_extend_stick_range_bar'][1]:6.2f} "
          f"env {row['after_extend_envelope_bar'][0]:6.2f}..{row['after_extend_envelope_bar'][1]:6.2f} | "
          f"ret {row['after_retract_nominal_bar']:7.2f} stick {row['after_retract_stick_range_bar'][0]:6.2f}.."
          f"{row['after_retract_stick_range_bar'][1]:6.2f} env {row['after_retract_envelope_bar'][0]:6.2f}.."
          f"{row['after_retract_envelope_bar'][1]:6.2f}")
print("== A regulation end F_p [kN]")
for k, v in A["regulation_end_Fp_N"].items():
    print(f"  {k:24s} {v/1e3:8.2f}")
print("== A speed")
for row in A["speed"]:
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()})
print("== B locks (CB batch): max |rec - formula(k-1)|, |rec - formula(k)|")
for case, res in r["B_cb_batch"].items():
    for leg, x in res.items():
        L = [l for l in x["locks"] if l["grounded"]]
        if not L:
            continue
        e1 = max(abs(l["p_r0_rec_bar"] - l["p_r0_formula_bar"]) for l in L)
        e2 = max(abs(l["p_r0_rec_bar"] - l["p_r0_formula_now_bar"]) for l in L)
        mx = max(L, key=lambda l: l["p_r0_rec_bar"])
        print(f"  {case:22s} {leg} n {len(L):3d} err {e1:6.3f} {e2:6.3f} max p_r0 rec {mx['p_r0_rec_bar']:7.2f} "
              f"formula {mx['p_r0_formula_bar']:7.2f} Fp {mx['Fp_kN']:7.2f} t {mx['t']:.2f} {mx['dir']}")
        lm = x["locked_max"]
        if lm:
            print(f"      locked seg {lm['t0']:.2f}-{lm['t1']:.2f} p_r0 {lm['p_r0_bar']:.2f} max {lm['p_r_max_rec_bar']:.2f}"
                  f" at {lm['t_at_max']:.2f} pred {lm['p_r_at_max_pred_bar']:.2f} share {lm['share']:.3f} "
                  f"maxres {lm['max_abs_resid_bar']:.2f}")
print("== C rows with held poc12 > 0 (needed margin over 12 bar POC bound)")
for row in r["C_rows"]:
    if row["held_poc12_bar"] > 0:
        print(f"  {row['batch'][:4]} {row['case']:30s} {row['leg']} Fp {row['Fp_min_kN']:6.2f}..{row['Fp_max_kN']:6.2f}"
              f" p_r {row['p_r_min_bar']:6.2f}..{row['p_r_max_bar']:6.2f} held poc12 {row['held_poc12_bar']:6.2f}"
              f" id {row['held_identity_bar']:6.2f} ho {row['held_Fp_head_only_bar']:6.2f}"
              f" 2s {row['held_Fp_two_sensor_bar']:6.2f}")
