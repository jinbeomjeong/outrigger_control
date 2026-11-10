"""P1 V16 single-pad level table (read-only) + discrete Bekker reference per grid.

z_ref = (F / (N_c h^2 (Kc / b_hull + Kphi)))^(1/n), b_hull = 2 A_hull / P_hull (SCMTerrain.cpp:1366-1377).
Sinkage = node mean sinkage of the contact nodes (+ = deeper)."""
import json
from pathlib import Path

root = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_P1_V16_20261026_032113")
cases = ["V16bp_J2_B_RL_2cm", "V16bp_J2_B_RL_1cm",
         "V16_J1_B_RL_2cm", "V16_J1_B_RL_1cm", "V16_J1_B_RL_0p5cm",
         "V16_J1_B_FL_2cm", "V16_J1_B_FL_1cm", "V16_J1_B_FL_0p5cm"]
for c in cases:
    r = json.loads((root / c / "result.json").read_text(encoding="utf-8"))
    s = r["meta"]["scm"]["SetSoilParameters"]
    h = r["meta"]["scm"]["grid_m"]
    A = r["meta"]["pad_area_m2"]
    print(f"== {c}  h={h} A_poly={A} Kc={s['Kc']} Kphi={s['Kphi']} n={s['n']}")
    print("  lvl factor   load_kN  Fz_kN   Nc  A_eff/A   b_hull   z_node_mm  z_ref_mm  z/ref-1")
    for lv in r["load_steps"]["levels"]:
        e = lv["end"]
        nd = e["nodes"]
        Nc = nd["n_contact"]
        ha, hp = nd["contact_hull_area_m2"], nd["contact_hull_perimeter_m"]
        b = 2 * ha / hp if ha else float("nan")
        F = e["Fz_scm_N"]
        z = nd["sinkage_mean_contact_m"] or 0.0
        zr = (F / (Nc * h * h * (s["Kc"] / b + s["Kphi"]))) ** (1 / s["n"]) if Nc else float("nan")
        print(f"  {lv['level']:3d} {e['factor']:.3f} {e['load_N']/1e3:8.2f} {F/1e3:7.2f} {Nc:4d}  {Nc*h*h/A:.4f}  {b:.4f}  {z*1e3:9.3f} {zr*1e3:9.3f}  {z/zr-1 if zr else 0:+.4f}")
    print(f"  origin offset: pad start xy {r.get('settle_end', {}).get('x_mm')}, {r.get('settle_end', {}).get('y_mm')} mm; plane {r['meta']['scm']['plane_point_world_m']}")
