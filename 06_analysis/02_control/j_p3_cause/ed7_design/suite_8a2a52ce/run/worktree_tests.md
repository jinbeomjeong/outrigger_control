# worktree_tests — worktree 코드 + 메인 checkout 저장 자료 시험

- worktree `C:\workspace\outrigger_control\.claude\worktrees\ed7-impl`, 데이터 root `C:\workspace\outrigger_control`, 바꾼 폴더 07_results
- pytest 종료 1(실패한 시험 있음), 4191.3 s · 시험 8695: 통과 8678, 실패 2, 오류 0, 건너뜀 15, 예상 실패 0, XPASS 0
- probe: `outrigger_sim` worktree
- 실행 중 바뀐 데이터 경로 47회, 원본 불변 True, 실행 폴더 삭제 False
- 오류 2 · 경고 44 · 참고 272

## 복사본

| 파일 | 시험 | `__file__` | 감싼 경로 | 감싸지 않은 글자 |
|---|---|---|---|---|
| `05_tests/unit/test_426_identity.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_426_soil_event.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_426_start_gap_and_sets.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_427_p36.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_427_p36s.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_427_p36sa.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_427_stop_records.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_428_p37_p38.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_actuation.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_affinity_mask.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_attitude.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_auger_composition.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_averaging.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_b1_creep_chrono_rows.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_b1_harness.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_b5_baseline_compare.py` | 예 | 3 | - | 0 |
| `05_tests/unit/test_b5_ind_las.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_batch.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_batch_launch_env.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_build_doc_index.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_c2.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_c2_closed_loop.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_c2_fault_reground.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c2_k1.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c2_las.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c2_las_end_ramp.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c2_las_min_active.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c2_load_reference.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c2_p28.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c2_p29.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c2_p30.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c2_p31.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_c2_p32.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_c2_p33_p34.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_c2_p35.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_c2_p36.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c2_p37r4.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_c2_r5.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c2_r5_closed_loop.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_c2_r5_fallback_slope.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c2_r6.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c2_r8d1.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_c2_r8d1_closed_loop.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_c2_reanchor_direction_closed_loop.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_c2_reapproach_retrigger.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c2_request_probe.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c2_retrigger_two_samples.py` | 예 | 0 | - | 1 |
| `05_tests/unit/test_c2_returned_clip.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_c2_s2d.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c2_soil.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c2_target.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c2_touch_creep.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c2_touch_twist_hold.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_c2_zero_calibration.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c8.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_c_s8_72.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_chrono_bundle_grade_4368.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_chrono_rows_judge_4368.py` | 예 | 1 | 680: `MAIN_CHECKOUT / "07_results"`<br>688: `MAIN_CHECKOUT / "07_results"`<br>702: `tmp_path / "07_results"`<br>800: `MAIN_CHECKOUT / "07_results"`<br>811: `MAIN_CHECKOUT / "07_results"` | 1 |
| `05_tests/unit/test_chrono_t45_replay.py` | 예 | 1 | 25: `PROJECT_ROOT / "07_results"`<br>28: `PROJECT_ROOT / "07_results"`<br>31: `PROJECT_ROOT / "07_results"`<br>35: `PROJECT_ROOT / "07_results"`<br>38: `PROJECT_ROOT / "07_results"` | 0 |
| `05_tests/unit/test_contact_episode.py` | 예 | 2 | 24: `Path(__file__).resolve().parents[2] / "07_results"`<br>26: `Path(__file__).resolve().parents[2] / "07_results"` | 0 |
| `05_tests/unit/test_contact_metrics.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_contact_replay.py` | 예 | 1 | 31: `Path(__file__).resolve().parents[2] / "07_results"` | 0 |
| `05_tests/unit/test_contact_replay_fallback_slope.py` | 예 | 1 | 40: `Path(__file__).resolve().parents[2] / "07_results"` | 0 |
| `05_tests/unit/test_counterbalance.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_crawler_settle.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_d0_plant_split.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_d1_chrono_rows.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_d1_harness.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_d1_harness_paths.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_d1_ready_limits_rev1.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_d1_select.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_d8x_chrono_rows.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_d8x_diag.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_d8x_judge.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_d8x_runners.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_ed6_erratum2.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_ed6_erratum3.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_ed6_harness.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_ed6_judges.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_ed6_lock_start_b.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_ed6_prelock.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_ed6_tjr_12a.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_ed7_adoption.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_ed7_harness.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_ed7_run_commit.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_ed7_units.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_engine.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_extend_start_bound.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_fallback_ratio_engine.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_final_b1b2_identity.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_final_ctrl_offline.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_floor_estimate.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_frames.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_ground_contact.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_hull_hook.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_hydraulic_sensors.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_hydraulics_check_open_delay.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_hydraulics_flow_limit_run.py` | 예 | 1 | 199: `Path(s9_batch.ROOT) / "07_results"` | 0 |
| `05_tests/unit/test_hydraulics_flow_share.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_hydraulics_rod_release.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_hydraulics_v5_options.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_imu.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_jp3_12b_erratum8.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_jp3_12b_tools.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_addendum_4a2.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_addendum_4a3.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_addendum_4a4.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_addendum_4a4_erratum1.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_addendum_4a5.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_addendum_4a7_erratum1.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_addendum_4a8.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_ckdrop.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_dry_scan_exclusion.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_ed5_erratum1.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_jp3_ed5_erratum2.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_ed5_erratum6.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_ed5_erratum7.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_ed5_prelaunch_fix.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_ed5_s1_stored.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_edition4.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_jp3_harness_units.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_j9main.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_judge_main_e2e.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_p51_compare.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_p5_fixed_values.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_prelaunch_audit.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_prelaunch_audit2.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_remedy.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_rerun_match.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_rev5_property.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_jp3_rev6.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_judges_4368.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_judges_4368_h6_h8.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_k1_forced_block.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_k2_chrono_runner.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_k2_harness.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_k2_hashes.py` | 예 | 3 | - | 0 |
| `05_tests/unit/test_k2_path1_rev2.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_k2_post_audit_fixes.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_k2_prelaunch_fix.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_k2_recount.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_k2_run_s9.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_l1_scope.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_l1r_checks.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_l2b_l1r_expect_controller.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_l2b_r5_extend_anchor.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_l2b_rod_side.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_l2b_rod_side_release.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_las_chrono_rows.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_las_k1_adopt_judge.py` | 예 | 1 | 450: `tmp_path / "07_results"`<br>456: `tmp_path / "07_results"`<br>473: `tmp_path / "07_results"`<br>479: `tmp_path / "07_results"` | 0 |
| `05_tests/unit/test_las_k1_chrono_rows.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_las_k1_rem_chrono_rows.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_las_k1_rem_judge.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_las_off_chrono.py` | 예 | 1 | 22: `PROJECT_ROOT / "07_results"` | 0 |
| `05_tests/unit/test_las_p5r4_k1_chrono_rows.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_late_loc_rule.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_leg_extension_peaks.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_lift.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_lock_stiffness_l1r.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_m2_flow_law_paths.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_mast_bending_inputs.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_mast_flex_r8c2.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_mesh_zbuffer.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_metrics.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_metrics_era.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_ml_masks.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_ml_pipeline.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_p3_chrono_check_rev10.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_pad_variants.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_params.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_params_l2b.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_preset_runners_gate_off.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_pressure_sensor_error.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_r5_fallback_replay.py` | 예 | 2 | 56: `Path(__file__).resolve().parents[2] / "07_results"`<br>487: `Path(__file__).resolve().parents[2] / "07_results"` | 0 |
| `05_tests/unit/test_r76_g6_chrono_judge.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_r79_controller_tag.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_r79_sensor_screen.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_record.py` | 예 | 0 | 577: `project_root / "07_results"` | 0 |
| `05_tests/unit/test_reference.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_rep_evidence.py` | 예 | 1 | - | 2 |
| `05_tests/unit/test_resume4368.py` | 예 | 1 | 348: `root / "07_results"`<br>404: `tmp_path / "07_results"`<br>413: `tmp_path / "07_results"` | 1 |
| `05_tests/unit/test_resume4368_rev1.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_resume4368_rev10.py` | 예 | 1 | - | 4 |
| `05_tests/unit/test_resume4368_rev11.py` | 예 | 1 | - | 1 |
| `05_tests/unit/test_resume4368_rev12.py` | 예 | 1 | 219: `tmp_path / "07_results"` | 0 |
| `05_tests/unit/test_resume4368_rev16.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_resume4368_rev18.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_resume4368_rev7.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_resume4368_rev8.py` | 예 | 1 | - | 1 |
| `05_tests/unit/test_resume4368_rev9.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_resume4368_supplement4.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_resume4368_supplement5.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_rigid_base.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_rod_chamber.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_rod_chamber_statics.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_rod_side.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_run_rows_probed_leg.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_run_S2a_v12_vs_pdelta.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_runner_dt_schedule.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_runner_fake_engine.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_runner_r8.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_runner_stop_when.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_s3_checks.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_s4_checks.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_s4_energy.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_s5_checks.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s6_b1_check.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s6_bundle_c.py` | 예 | 1 | 172: `Path(__file__).resolve().parents[2] / "07_results"` | 1 |
| `05_tests/unit/test_s6_bundle_c_r8_meta.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_s6_bundle_c_rev32.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s6_bundle_c_rev33.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s6_bundle_c_rev34.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s6_bundle_c_rev35.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s6_c_s8_76.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s6_control_judge.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_s6_ge1_export.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s6_judge_rev10.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_s6_stage2_summary_cli.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s7_checks.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s7_control.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_s7_control_rev37.py` | 예 | 1 | 208: `ROOT / "07_results"` | 0 |
| `05_tests/unit/test_s8_c_s8_33.py` | 예 | 1 | 18: `ROOT / "07_results"` | 0 |
| `05_tests/unit/test_s8_c_s8_34.py` | 예 | 1 | 17: `ROOT / "07_results"` | 0 |
| `05_tests/unit/test_s8_c_s8_67.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s8_c_s8_68.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s8_cb_rerun.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_s8_control.py` | 예 | 1 | 95: `ROOT / "07_results/S7/ctrl3_20261024_154939/L2b_D8_top_rpB_b1.0"`<br>414: `ROOT / "07_results/S8/p1_20261024_204911"` | 0 |
| `05_tests/unit/test_s8_control_rev45.py` | 예 | 1 | 18: `ROOT / "07_results"` | 0 |
| `05_tests/unit/test_s8_control_rev46.py` | 예 | 1 | 16: `ROOT / "07_results"` | 0 |
| `05_tests/unit/test_s8_ml_main.py` | 예 | 1 | 22: `ROOT / "07_results"` | 0 |
| `05_tests/unit/test_s8_ml_rerun.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s8_rev49_cad.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s8_rev52_cad.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s8_rev54_cad.py` | 예 | 1 | 16: `ROOT / "07_results"` | 0 |
| `05_tests/unit/test_s8_rev55_cad.py` | 예 | 1 | 17: `ROOT / "07_results"` | 0 |
| `05_tests/unit/test_s8_rev56_cad.py` | 예 | 1 | 18: `ROOT / "07_results"`<br>19: `ROOT / "07_results"`<br>20: `ROOT / "07_results"` | 1 |
| `05_tests/unit/test_s8_soil_restore.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s8_u74.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_s8_u75.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_s8_v15.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_batch_code_at_launch.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_batch_hull_mode.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_batch_inputs_exit.py` | 예 | 1 | 63: `tmp_path / "07_results"`<br>117: `tmp_path / "07_results"`<br>119: `tmp_path / "07_results"`<br>155: `tmp_path / "07_results"`<br>156: `tmp_path / "07_results"`<br>207: `tmp_path / "07_results"`<br>208: `tmp_path / "07_results"` | 0 |
| `05_tests/unit/test_s9_creep_rule.py` | 예 | 1 | 28: `Path("07_results")` | 1 |
| `05_tests/unit/test_s9_ds.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_extra_studies.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_final.py` | 예 | 1 | 24: `ROOT / "07_results"` | 1 |
| `05_tests/unit/test_s9_g6_patch_compare.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_g6_soil_patch.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_g6p_batch.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_journal_auger.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_loc_revoke.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_mass_scale.py` | 예 | 1 | 162: `ROOT / "07_results"`<br>280: `ROOT / "07_results"` | 0 |
| `05_tests/unit/test_s9_p31_chatter.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_p31_recontact.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_p3b_records.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_p3b_rev60.py` | 예 | 1 | 24: `ROOT / "07_results"` | 0 |
| `05_tests/unit/test_s9_qd_gated.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_rev420_records.py` | 예 | 2 | 21: `ROOT / "07_results"` | 0 |
| `05_tests/unit/test_s9_rv1.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_rv2.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_rv3.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_rv4.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_rv5.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_scm_nodes.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_settle_hook.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_settle_rejudge.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_settle_rejudge_order.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_slope_fix_candidates.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_s9_soil_slope.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_sample_period_copies.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_seal_friction.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_sensor_suite_and_control.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_settle.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_signals.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_slope.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_stable_ready_compare.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_stage3_las_compare.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_step_cost_S9_hull.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_support_geometry.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_target.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_target_verification_ext.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_two_pressure.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_two_pressure_cb_moving.py` | 예 | 1 | 272: `Path(__file__).resolve().parents[2] / "07_results"` | 1 |
| `05_tests/unit/test_two_pressure_d1_drain.py` | 예 | 1 | 241: `Path(__file__).resolve().parents[2] / "07_results"` | 1 |
| `05_tests/unit/test_two_pressure_d1_imu.py` | 예 | 2 | 429: `Path(__file__).resolve().parents[2] / "07_results"` | 5 |
| `05_tests/unit/test_two_pressure_d1_steps.py` | 예 | 1 | 266: `Path(__file__).resolve().parents[2] / "07_results"` | 2 |
| `05_tests/unit/test_two_pressure_extend_start.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_two_pressure_lock_bound.py` | 예 | 1 | 52: `Path(__file__).resolve().parents[2] / "07_results"` | 1 |
| `05_tests/unit/test_two_pressure_lock_valve.py` | 예 | 1 | 47: `Path(__file__).resolve().parents[2] / "07_results"` | 4 |
| `05_tests/unit/test_two_pressure_rev64.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_v5_chrono_options.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_v5_harness_units.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_v5_lock_window.py` | 예 | 0 | - | 0 |
| `05_tests/unit/test_v5_paper_rows.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_v5_rerun.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_v5_resume_4368_chrono_rows.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_v5_resume_4368_manifest_oc5.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_v5_rev9_j_p3.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_v5_setting_records.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_v5_stage3_las_rows.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_v5_stage3_rows.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_v5_switch_tags.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_x10_rod_fault.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_zero_calibration.py` | 예 | 0 | - | 0 |
| `05_tests/conftest.py` | - | 1 | - | 0 |

## 발견 사항

### 오류 (error) — 2건

| 분류 | 위치 | 대상 | 내용 |
|---|---|---|---|
| test_failed | 05_tests/unit/test_d8x_diag.py | 05_tests.unit.test_d8x_diag::test_rerun_gives_the_stored_command_hash | 05_tests.unit.test_d8x_diag::test_rerun_gives_the_stored_command_hash: failed (AssertionError: assert 'c0b626b9d8ed...4ad4093a8c758' == '4700d690fb09...c802b1e591729' - 4700d690fb098a3760f40dde032feb49461c081aa97453156d5c802b1e591729 + c0b626b9d8ed1fabcc647701e802a567fcae0b69784) |
| test_failed | 05_tests/unit/test_record.py | 05_tests.unit.test_record::test_default_snapshot_directory_is_results_states | 05_tests.unit.test_record::test_default_snapshot_directory_is_results_states: failed (AssertionError: assert WindowsPath('C:/workspace/outrigger_control/.claude/worktrees/ed7-impl/07_results/states') == (WindowsPath('C:/workspace/outrigger_control/07_results') / 'states') + where Windo) |

### 경고 (warning) — 44건

| 분류 | 위치 | 대상 | 내용 |
|---|---|---|---|
| data_literal_not_rebased | 05_tests/unit/test_c2_retrigger_two_samples.py:59 |  | 감싸지 않은 데이터 경로 글자 'C:\\workspace\\outrigger_control\\07_results\\S8': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_chrono_rows_judge_4368.py:750 |  | 감싸지 않은 데이터 경로 글자 'C:/gone/worktree/07_results/S6': 여기는 worktree를 읽는다 |
| skipped | 05_tests/unit/test_d8x_chrono_rows.py | 05_tests.unit.test_d8x_chrono_rows::test_refuses_without_verification_ext | 05_tests.unit.test_d8x_chrono_rows::test_refuses_without_verification_ext: 건너뜀 (pytest.skip: VERIFICATION_EXT installed) |
| skipped | 05_tests/unit/test_las_chrono_rows.py | 05_tests.unit.test_las_chrono_rows::test_run_refuses_blocked_rows | 05_tests.unit.test_las_chrono_rows::test_run_refuses_blocked_rows: 건너뜀 (pytest.skip: LAS-b merged: no blocked row) |
| skipped | 05_tests/unit/test_ml_pipeline.py | 05_tests.unit.test_ml_pipeline::test_gru_onnx_dynamo_export_matches_torch | 05_tests.unit.test_ml_pipeline::test_gru_onnx_dynamo_export_matches_torch: 건너뜀 (pytest.skip: could not import 'torch': No module named 'torch') |
| skipped | 05_tests/unit/test_ml_pipeline.py | 05_tests.unit.test_ml_pipeline::test_gru_onnx_falls_back_to_torchscript | 05_tests.unit.test_ml_pipeline::test_gru_onnx_falls_back_to_torchscript: 건너뜀 (pytest.skip: could not import 'torch': No module named 'torch') |
| skipped | 05_tests/unit/test_ml_pipeline.py | 05_tests.unit.test_ml_pipeline::test_float32_thresholds_keep_every_booster_decision | 05_tests.unit.test_ml_pipeline::test_float32_thresholds_keep_every_booster_decision: 건너뜀 (pytest.skip: could not import 'torch': No module named 'torch') |
| skipped | 05_tests/unit/test_ml_pipeline.py | 05_tests.unit.test_ml_pipeline::test_lightgbm_onnx_export_matches_booster | 05_tests.unit.test_ml_pipeline::test_lightgbm_onnx_export_matches_booster: 건너뜀 (pytest.skip: could not import 'torch': No module named 'torch') |
| skipped | 05_tests/unit/test_ml_pipeline.py | 05_tests.unit.test_ml_pipeline::test_training_export_and_scoring_run_end_to_end | 05_tests.unit.test_ml_pipeline::test_training_export_and_scoring_run_end_to_end: 건너뜀 (pytest.skip: could not import 'torch': No module named 'torch') |
| skipped | 05_tests/unit/test_params_l2b.py | 05_tests.unit.test_params_l2b::test_l1_default_is_unchanged | 05_tests.unit.test_params_l2b::test_l1_default_is_unchanged: 건너뜀 (pytest.skip: YAML regenerated since S7; L1 fingerprint baseline no longer applies) |
| data_literal_not_rebased | 05_tests/unit/test_rep_evidence.py:103 |  | 감싸지 않은 데이터 경로 글자 '07_results/S9/': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_rep_evidence.py:323 |  | 감싸지 않은 데이터 경로 글자 '07_results/S9/batch_P3b_test': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_resume4368.py:417 |  | 감싸지 않은 데이터 경로 글자 'D:/elsewhere/07_results/S8/v5jp_VB/caseA/result.json': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_resume4368_rev10.py:66 |  | 감싸지 않은 데이터 경로 글자 '07_results/S9/batch_': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_resume4368_rev10.py:79 |  | 감싸지 않은 데이터 경로 글자 '07_results/S9/some_folder': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_resume4368_rev10.py:80 |  | 감싸지 않은 데이터 경로 글자 '07_results/S9/batch_V5-RESUME-K1-ZZ_20261113_120000': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_resume4368_rev10.py:81 |  | 감싸지 않은 데이터 경로 글자 '07_results/S9/some_folder': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_resume4368_rev11.py:479 |  | 감싸지 않은 데이터 경로 글자 'C:\\workspace\\outrigger_control\\07_results\\S9': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_resume4368_rev8.py:459 |  | 감싸지 않은 데이터 경로 글자 '07_results/S9/batch_': 여기는 worktree를 읽는다 |
| skipped | 05_tests/unit/test_rod_chamber.py | 05_tests.unit.test_rod_chamber::test_h6_gas_separation | 05_tests.unit.test_rod_chamber::test_h6_gas_separation: 건너뜀 (pytest.skip: gas separation after FLOOR (14.3 optional) is not implemented) |
| data_literal_not_rebased | 05_tests/unit/test_s6_bundle_c.py:276 |  | 감싸지 않은 데이터 경로 글자 '07_results/states_L1R snapshots not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_s8_rev56_cad.py:247 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8/mlj_20261025_080212': 여기는 worktree를 읽는다 |
| skipped | 05_tests/unit/test_s8_soil_restore.py | 05_tests.unit.test_s8_soil_restore::test_soil_restore_check_reads_the_plan_of_this_tree | 05_tests.unit.test_s8_soil_restore::test_soil_restore_check_reads_the_plan_of_this_tree: 건너뜀 (pytest.skip: S8 ML plan not present (07_results is not tracked): C:\workspace\outrigger_control\.claude\worktrees\ed7-impl\07_results\S8\ml_main_20261025_090131\ml_plan.json) |
| data_literal_not_rebased | 05_tests/unit/test_s9_creep_rule.py:145 |  | 감싸지 않은 데이터 경로 글자 '07_results/S9 is not here (not in git)': 여기는 worktree를 읽는다 |
| skipped | 05_tests/unit/test_s9_final.py | 05_tests.unit.test_s9_final::test_source_args_check_on_the_former_runs | 05_tests.unit.test_s9_final::test_source_args_check_on_the_former_runs: 건너뜀 (pytest.skip: no former run folders under 07_results/S9) |
| skipped | 05_tests/unit/test_s9_final.py | 05_tests.unit.test_s9_final::test_final_r_s6_rows_match_their_former_batch | 05_tests.unit.test_s9_final::test_final_r_s6_rows_match_their_former_batch: 건너뜀 (pytest.skip: former S6 batch not here) |
| skipped | 05_tests/unit/test_s9_final.py | 05_tests.unit.test_s9_final::test_final_rep_x_check_sources | 05_tests.unit.test_s9_final::test_final_rep_x_check_sources: 건너뜀 (pytest.skip: source run folder absent (07_results is not in git)) |
| data_literal_not_rebased | 05_tests/unit/test_s9_final.py:369 |  | 감싸지 않은 데이터 경로 글자 '07_results/S6/bundleC_g8c76_p28acc_p28_L1R_20261027_222426/': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_cb_moving.py:334 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 CB batches not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_d1_drain.py:415 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 records absent': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_d1_imu.py:592 |  | 감싸지 않은 데이터 경로 글자 "07_results/S8 D1' ML records not present": 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_d1_imu.py:604 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 ML pilot not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_d1_imu.py:617 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 old ML episodes not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_d1_imu.py:636 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 ML pilot not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_d1_imu.py:720 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 ML pilot not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_d1_steps.py:318 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 old ML episodes absent': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_d1_steps.py:339 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 ML pilot bases not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_lock_bound.py:371 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 ML pilot bases not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_lock_valve.py:286 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 CB batch not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_lock_valve.py:293 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 p1r batch not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_lock_valve.py:304 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 p1r batch not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_lock_valve.py:315 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 ML pilot bases not present': 여기는 worktree를 읽는다 |
| skipped | 05_tests/unit/test_x10_rod_fault.py | 05_tests.unit.test_x10_rod_fault::test_i_without_a_plan_the_rows_are_the_commit_before_x10[VBJ5-VBJ] | 05_tests.unit.test_x10_rod_fault::test_i_without_a_plan_the_rows_are_the_commit_before_x10[VBJ5-VBJ]: 건너뜀 (pytest.skip: X10_BASE_ROOT not set (a checkout of the commit before X-10)) |
| skipped | 05_tests/unit/test_x10_rod_fault.py | 05_tests.unit.test_x10_rod_fault::test_i_without_a_plan_the_rows_are_the_commit_before_x10[VBJ0-VBJ0] | 05_tests.unit.test_x10_rod_fault::test_i_without_a_plan_the_rows_are_the_commit_before_x10[VBJ0-VBJ0]: 건너뜀 (pytest.skip: X10_BASE_ROOT not set (a checkout of the commit before X-10)) |

### 참고 (info) — 272건

| 분류 | 위치 | 대상 | 내용 |
|---|---|---|---|
| no_data_paths | 05_tests/unit/test_426_identity.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_426_soil_event.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_426_start_gap_and_sets.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_427_p36.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_427_p36s.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_427_p36sa.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_427_stop_records.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_428_p37_p38.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_actuation.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_affinity_mask.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_attitude.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_auger_composition.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_averaging.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_b1_creep_chrono_rows.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_b1_harness.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_b5_baseline_compare.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_b5_ind_las.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_batch.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_batch_launch_env.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_build_doc_index.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_closed_loop.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_fault_reground.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_k1.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_las.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_las_end_ramp.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_las_min_active.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_load_reference.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_p28.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_p29.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_p30.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_p31.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_p32.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_p33_p34.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_p35.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_p36.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_p37r4.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_r5.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_r5_closed_loop.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_r5_fallback_slope.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_r6.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_r8d1.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_r8d1_closed_loop.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_reanchor_direction_closed_loop.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_reapproach_retrigger.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_request_probe.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_retrigger_two_samples.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_returned_clip.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_s2d.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_soil.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_target.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_touch_creep.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_touch_twist_hold.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c2_zero_calibration.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c8.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_c_s8_72.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_chrono_bundle_grade_4368.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_contact_metrics.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_counterbalance.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_crawler_settle.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_d0_plant_split.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_d1_chrono_rows.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_d1_harness.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_d1_harness_paths.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_d1_ready_limits_rev1.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_d1_select.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_d8x_chrono_rows.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_d8x_diag.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_d8x_judge.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_d8x_runners.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed6_erratum2.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed6_erratum3.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed6_harness.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed6_judges.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed6_lock_start_b.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed6_prelock.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed6_tjr_12a.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed7_adoption.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed7_harness.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed7_run_commit.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed7_units.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_engine.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_extend_start_bound.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_fallback_ratio_engine.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_final_b1b2_identity.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_final_ctrl_offline.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_floor_estimate.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_frames.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ground_contact.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_hull_hook.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_hydraulic_sensors.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_hydraulics_check_open_delay.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_hydraulics_flow_share.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_hydraulics_rod_release.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_hydraulics_v5_options.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_imu.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_12b_erratum8.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_12b_tools.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_addendum_4a2.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_addendum_4a3.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_addendum_4a4.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_addendum_4a4_erratum1.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_addendum_4a5.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_addendum_4a7_erratum1.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_addendum_4a8.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_ckdrop.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_dry_scan_exclusion.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_ed5_erratum1.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_ed5_erratum2.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_ed5_erratum6.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_ed5_erratum7.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_ed5_prelaunch_fix.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_ed5_s1_stored.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_edition4.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_harness_units.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_j9main.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_judge_main_e2e.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_p51_compare.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_p5_fixed_values.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_prelaunch_audit.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_prelaunch_audit2.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_remedy.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_rerun_match.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_rev5_property.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_rev6.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_judges_4368.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_judges_4368_h6_h8.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_k1_forced_block.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_k2_chrono_runner.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_k2_harness.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_k2_hashes.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_k2_path1_rev2.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_k2_post_audit_fixes.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_k2_prelaunch_fix.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_k2_recount.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_k2_run_s9.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_l1_scope.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_l1r_checks.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_l2b_l1r_expect_controller.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_l2b_r5_extend_anchor.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_l2b_rod_side.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_l2b_rod_side_release.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_las_chrono_rows.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_las_k1_chrono_rows.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_las_k1_rem_chrono_rows.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_las_k1_rem_judge.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_las_p5r4_k1_chrono_rows.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_late_loc_rule.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_leg_extension_peaks.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_lift.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_lock_stiffness_l1r.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_m2_flow_law_paths.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_mast_bending_inputs.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_mast_flex_r8c2.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_mesh_zbuffer.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_metrics.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_metrics_era.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ml_masks.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ml_pipeline.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_p3_chrono_check_rev10.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_pad_variants.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_params.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_params_l2b.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_preset_runners_gate_off.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_pressure_sensor_error.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_r76_g6_chrono_judge.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_r79_controller_tag.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_r79_sensor_screen.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_reference.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_rep_evidence.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_resume4368_rev1.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_resume4368_rev10.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_resume4368_rev11.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_resume4368_rev16.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_resume4368_rev18.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_resume4368_rev7.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_resume4368_rev8.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_resume4368_rev9.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_resume4368_supplement4.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_resume4368_supplement5.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_rigid_base.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_rod_chamber.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_rod_chamber_statics.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_rod_side.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_run_S2a_v12_vs_pdelta.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_run_rows_probed_leg.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_runner_dt_schedule.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_runner_fake_engine.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_runner_r8.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_runner_stop_when.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s3_checks.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s4_checks.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s4_energy.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s5_checks.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s6_b1_check.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s6_bundle_c_r8_meta.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s6_bundle_c_rev32.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s6_bundle_c_rev33.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s6_bundle_c_rev34.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s6_bundle_c_rev35.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s6_c_s8_76.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s6_control_judge.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s6_ge1_export.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s6_judge_rev10.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s6_stage2_summary_cli.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s7_checks.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s7_control.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s8_c_s8_67.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s8_c_s8_68.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s8_cb_rerun.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s8_ml_rerun.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s8_rev49_cad.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s8_rev52_cad.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s8_soil_restore.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s8_u74.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s8_u75.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s8_v15.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_batch_code_at_launch.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_batch_hull_mode.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_ds.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_extra_studies.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_g6_patch_compare.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_g6_soil_patch.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_g6p_batch.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_journal_auger.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_loc_revoke.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_p31_chatter.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_p31_recontact.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_p3b_records.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_qd_gated.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_rv1.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_rv2.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_rv3.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_rv4.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_rv5.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_scm_nodes.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_settle_hook.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_settle_rejudge.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_settle_rejudge_order.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_slope_fix_candidates.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_s9_soil_slope.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_sample_period_copies.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_seal_friction.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_sensor_suite_and_control.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_settle.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_signals.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_slope.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_stable_ready_compare.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_stage3_las_compare.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_step_cost_S9_hull.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_support_geometry.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_target.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_target_verification_ext.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_two_pressure.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_two_pressure_extend_start.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_two_pressure_rev64.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_v5_chrono_options.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_v5_harness_units.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_v5_lock_window.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_v5_paper_rows.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_v5_rerun.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_v5_resume_4368_chrono_rows.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_v5_resume_4368_manifest_oc5.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_v5_rev9_j_p3.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_v5_setting_records.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_v5_stage3_las_rows.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_v5_stage3_rows.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_v5_switch_tags.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_x10_rod_fault.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_zero_calibration.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| probe_worktree | probe | outrigger_sim | worktree에서 import됨: C:\workspace\outrigger_control\.claude\worktrees\ed7-impl\03_src\outrigger_sim\__init__.py (main) |
| rebase_unmatched | probe |  | worktree·데이터 root 밖이라 그대로 둔 값 31회: ['C:\\Users\\jinbeom\\AppData\\Local\\Temp\\pytest-of-jinbeom\\pytest-3343\\test_check_inputs_cli0\\07_results', 'C:\\Users\\jinbeom\\AppData\\Local\\Temp\\pytest-of-jinbeom\\pytest-3343\\test_jp_reuse_all_silent_is_re0\\07_results', 'C:\\Users\\jinbeom\\AppData\\Local\\Temp\\pytest-of-jinbeom\\pytest-3343\\test_jp_reuse_cli0\\07_results', 'C:\\Users\\jinbeom\\AppData\\Local\\Temp\\pytest-of-jinbeom\\pytest-3343\\test_jp_reuse_dict_events_are_0\\07_results', 'C:\\Users\\jinbeom\\AppData\\Local\\Temp\\pytest-of-jinbeom\\pytest-3343\\test_jp_reuse_input_problems_a0\\07_results', 'C:\\Users\\jinbeom\\AppData\\Local\\Temp\\pytest-of-jinbeom\\pytest-3343\\test_jp_reuse_input_problems_a0\\other\\07_results', 'C:\\Users\\jinbeom\\AppData\\Local\\Temp\\pytest-of-jinbeom\\pytest-3343\\test_jp_row_folder_from_the_re0\\07_results', 'C:\\Users\\jinbeom\\AppData\\Local\\Temp\\pytest-of-jinbeom\\pytest-3343\\test_judge_on_a_synthetic_tree0\\07_results', 'C:\\Users\\jinbeom\\AppData\\Local\\Temp\\pytest-of-jinbeom\\pytest-3343\\test_judge_row_without_window_0\\07_results', 'C:\\Users\\jinbeom\\AppData\\Local\\Temp\\pytest-of-jinbeom\\pytest-3343\\test_list_on_a_synthetic_tree_0\\07_results'] |


## pytest 로그 끝

```text
        diag = rerun["diag"]
>       assert diag["commands_sha256"] == stored["commands_sha256"]
E       AssertionError: assert 'c0b626b9d8ed...4ad4093a8c758' == '4700d690fb09...c802b1e591729'
E         
E         - 4700d690fb098a3760f40dde032feb49461c081aa97453156d5c802b1e591729
E         + c0b626b9d8ed1fabcc647701e802a567fcae0b697840f881c9c4ad4093a8c758

C:\Users\jinbeom\.claude\runners\outrigger-ed7-suite-c\run\scratch\wt_tests_20261125_164500_120856\tree\05_tests\unit\test_d8x_diag.py:109: AssertionError
______________ test_default_snapshot_directory_is_results_states ______________

project_root = WindowsPath('C:/workspace/outrigger_control/.claude/worktrees/ed7-impl')

    def test_default_snapshot_directory_is_results_states(project_root: Path) -> None:
>       assert DEFAULT_STATES_DIR == __import__("_wt_probe").rebase_data(project_root / "07_results") / "states"
E       AssertionError: assert WindowsPath('C:/workspace/outrigger_control/.claude/worktrees/ed7-impl/07_results/states') == (WindowsPath('C:/workspace/outrigger_control/07_results') / 'states')
E        +  where WindowsPath('C:/workspace/outrigger_control/07_results') = <function rebase_data at 0x0000028B8EE000E0>((WindowsPath('C:/workspace/outrigger_control/.claude/worktrees/ed7-impl') / '07_results'))
E        +    where <function rebase_data at 0x0000028B8EE000E0> = <module '_wt_probe' from 'C:\\Users\\jinbeom\\.claude\\runners\\outrigger-ed7-suite-c\\run\\scratch\\wt_tests_20261125_164500_120856\\_wt_probe.py'>.rebase_data
E        +      where <module '_wt_probe' from 'C:\\Users\\jinbeom\\.claude\\runners\\outrigger-ed7-suite-c\\run\\scratch\\wt_tests_20261125_164500_120856\\_wt_probe.py'> = __import__('_wt_probe')

C:\Users\jinbeom\.claude\runners\outrigger-ed7-suite-c\run\scratch\wt_tests_20261125_164500_120856\tree\05_tests\unit\test_record.py:577: AssertionError
============================== warnings summary ===============================
05_tests/unit/test_jp3_rev5_property.py::test_t_jr_04_case_11b_p4_6_soundness_of_the_opening_rows[14800.0-0.001-0.1-55.35--31.06-5.05]
05_tests/unit/test_jp3_rev5_property.py::test_t_jr_04_case_11b_p4_6_soundness_of_the_opening_rows[14800.0-0.001-0.2-50.95--27.14-9.45]
  05_tests\unit\test_jp3_rev5_property.py:576: PytestWarning: record_property is incompatible with junit_family 'xunit2' (use 'legacy' or 'xunit1')
    @pytest.mark.parametrize(P4_6_COLUMNS, P4_6_OPENING_ROWS)

05_tests/unit/test_jp3_rev5_property.py::test_t_jr_04_case_11b_p4_6_slow_rows_have_no_exposure[14800.0-0.0003-0.1-58.52--33.88-1.88]
05_tests/unit/test_jp3_rev5_property.py::test_t_jr_04_case_11b_p4_6_slow_rows_have_no_exposure[14800.0-0.0003-0.2-57.15--32.66-3.25]
05_tests/unit/test_jp3_rev5_property.py::test_t_jr_04_case_11b_p4_6_slow_rows_have_no_exposure[14800.0-0.0003-0.5-53.13--29.08-7.27]
05_tests/unit/test_jp3_rev5_property.py::test_t_jr_04_case_11b_p4_6_slow_rows_have_no_exposure[5000.0-0.0003-0.2-57.92--36.78-2.58]
  05_tests\unit\test_jp3_rev5_property.py:597: PytestWarning: record_property is incompatible with junit_family 'xunit2' (use 'legacy' or 'xunit1')
    @pytest.mark.parametrize(P4_6_COLUMNS, P4_6_SLOW_ROWS)

05_tests/unit/test_jp3_rev5_property.py::test_t_jr_04_case_11b_p1_p4_7
  05_tests\unit\test_jp3_rev5_property.py:707: PytestWarning: record_property is incompatible with junit_family 'xunit2' (use 'legacy' or 'xunit1')
    def test_t_jr_04_case_11b_p1_p4_7(monkeypatch, record_property, tmp_path) -> None:

05_tests/unit/test_s8_control.py::test_rev43_on_the_p1_re1bf_fs8_case
  C:\workspace\outrigger_control\.claude\worktrees\ed7-impl\03_src\outrigger_sim\verify\s6_control.py:1011: RuntimeWarning: Mean of empty slice
    reference = np.nanmean(anchors[before], axis=0)  # (4, 3)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED ..\..\..\..\..\Users\jinbeom\.claude\runners\outrigger-ed7-suite-c\run\scratch\wt_tests_20261125_164500_120856\tree\05_tests\unit\test_d8x_diag.py::test_rerun_gives_the_stored_command_hash
FAILED ..\..\..\..\..\Users\jinbeom\.claude\runners\outrigger-ed7-suite-c\run\scratch\wt_tests_20261125_164500_120856\tree\05_tests\unit\test_record.py::test_default_snapshot_directory_is_results_states
SKIPPED [1] ..\..\..\..\..\Users\jinbeom\.claude\runners\outrigger-ed7-suite-c\run\scratch\wt_tests_20261125_164500_120856\tree\05_tests\unit\test_d8x_chrono_rows.py:276: VERIFICATION_EXT installed
SKIPPED [1] ..\..\..\..\..\Users\jinbeom\.claude\runners\outrigger-ed7-suite-c\run\scratch\wt_tests_20261125_164500_120856\tree\05_tests\unit\test_las_chrono_rows.py:92: LAS-b merged: no blocked row
SKIPPED [1] ..\..\..\..\..\Users\jinbeom\.claude\runners\outrigger-ed7-suite-c\run\scratch\wt_tests_20261125_164500_120856\tree\05_tests\unit\test_ml_pipeline.py:276: could not import 'torch': No module named 'torch'
SKIPPED [1] ..\..\..\..\..\Users\jinbeom\.claude\runners\outrigger-ed7-suite-c\run\scratch\wt_tests_20261125_164500_120856\tree\05_tests\unit\test_ml_pipeline.py:286: could not import 'torch': No module named 'torch'
SKIPPED [1] ..\..\..\..\..\Users\jinbeom\.claude\runners\outrigger-ed7-suite-c\run\scratch\wt_tests_20261125_164500_120856\tree\05_tests\unit\test_ml_pipeline.py:299: could not import 'torch': No module named 'torch'
SKIPPED [1] ..\..\..\..\..\Users\jinbeom\.claude\runners\outrigger-ed7-suite-c\run\scratch\wt_tests_20261125_164500_120856\tree\05_tests\unit\test_ml_pipeline.py:308: could not import 'torch': No module named 'torch'
SKIPPED [1] ..\..\..\..\..\Users\jinbeom\.claude\runners\outrigger-ed7-suite-c\run\scratch\wt_tests_20261125_164500_120856\tree\05_tests\unit\test_ml_pipeline.py:329: could not import 'torch': No module named 'torch'
SKIPPED [1] ..\..\..\..\..\Users\jinbeom\.claude\runners\outrigger-ed7-suite-c\run\scratch\wt_tests_20261125_164500_120856\tree\05_tests\unit\test_params_l2b.py:37: YAML regenerated since S7; L1 fingerprint baseline no longer applies
SKIPPED [1] ..\..\..\..\..\Users\jinbeom\.claude\runners\outrigger-ed7-suite-c\run\scratch\wt_tests_20261125_164500_120856\tree\05_tests\unit\test_rod_chamber.py:441: gas separation after FLOOR (14.3 optional) is not implemented
SKIPPED [1] ..\..\..\..\..\Users\jinbeom\.claude\runners\outrigger-ed7-suite-c\run\scratch\wt_tests_20261125_164500_120856\tree\05_tests\unit\test_s8_soil_restore.py:432: S8 ML plan not present (07_results is not tracked): C:\workspace\outrigger_control\.claude\worktrees\ed7-impl\07_results\S8\ml_main_20261025_090131\ml_plan.json
SKIPPED [1] ..\..\..\..\..\Users\jinbeom\.claude\runners\outrigger-ed7-suite-c\run\scratch\wt_tests_20261125_164500_120856\tree\05_tests\unit\test_s9_final.py:163: no former run folders under 07_results/S9
SKIPPED [1] ..\..\..\..\..\Users\jinbeom\.claude\runners\outrigger-ed7-suite-c\run\scratch\wt_tests_20261125_164500_120856\tree\05_tests\unit\test_s9_final.py:383: former S6 batch not here
SKIPPED [1] ..\..\..\..\..\Users\jinbeom\.claude\runners\outrigger-ed7-suite-c\run\scratch\wt_tests_20261125_164500_120856\tree\05_tests\unit\test_s9_final.py:556: source run folder absent (07_results is not in git)
SKIPPED [2] ..\..\..\..\..\Users\jinbeom\.claude\runners\outrigger-ed7-suite-c\run\scratch\wt_tests_20261125_164500_120856\tree\05_tests\unit\test_x10_rod_fault.py:747: X10_BASE_ROOT not set (a checkout of the commit before X-10)
2 failed, 8678 passed, 15 skipped, 8 warnings in 4189.62s (1:09:49)
```
