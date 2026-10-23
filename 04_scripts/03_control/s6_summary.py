"""Print a compact table of target_sim.json."""
import json
import sys

d = json.load(open(sys.argv[1]))
for r in d["runs"]:
    if "error" in r:
        print(r["id"], "ERROR", r["error"], r.get("tb", "")[-600:])
        continue
    ra = r["ra"]
    print(f"{r['id']:<34} fails={r['fails']} Tready={r.get('t_level_after_touch_s')} "
          f"smax={max(r['s_max_seen_mm']):.1f} sfin={max(r['s_final_mm']):.1f} osh={r['s_overshoot_mm']} "
          f"oshAny={r['s_overshoot_any_leg_mm']} lim={r['stroke_limit_steps']} minF={r['min_true_cyl_force_kN']} "
          f"ss={r['ss_err_vs_target_deg']} clr_min={r['min_true_crawler_clearance_post_lift_mm']} "
          f"fclr={r['final_clearance_mm']} Pmax={r['max_pressure_bar']}")
    print(f"    RA {ra['outcome']} thc_rel={ra['theta_ground_deg']} thc_abs={ra['theta_crawler_abs_deg']} "
          f"Ft_done={ra.get('Ft_at_done_kN')} Ft_fin={ra.get('Ft_final_kN')} red={ra.get('Ft_maxleg_reduction')} "
          f"minsub={ra.get('min_true_cyl_post_liftoff_substep_kN')} minDur={ra.get('min_true_cyl_during_kN')} "
          f"dev={ra.get('max_att_dev_deg')} dur={ra.get('duration_s')} stops={ra.get('stop_readings_kN')} "
          f"t={r.get('t_done_s')},{ra.get('t_start_s')},{ra.get('t_end_s')},{r.get('t_ready_s')}")
    if r.get("changed_at_s") is not None:
        print(f"    CHANGE at {r['changed_at_s']} ready_times={r['ready_times_s']} t_to_ready={r.get('t_change_to_ready_s')} "
              f"smax_after={r.get('s_max_after_change_mm')} sfin={r['s_final_mm']} clr_min_after={r.get('min_true_crawler_clearance_after_change_mm')} "
              f"minF_after={r.get('min_true_cyl_after_change_kN')} att_osh={r.get('att_overshoot_after_change_deg')}")
